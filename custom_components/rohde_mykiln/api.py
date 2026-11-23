"""Minimal async client for the ROHDE myKiln web app (unofficial, reverse engineered)."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
import re
import time
from typing import Any

import aiohttp
from yarl import URL

from .const import BASE_URL
from .parser import (  # noqa: F401  (re-exported for the other modules)
    KilnData,
    KilnInfo,
    parse_age,
    parse_duration,
    parse_kiln,
    parse_kiln_list,
    parse_temperature,
    to_int,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
INFO_REFRESH_SECONDS = 3600  # kiln names/models rarely change
INFO_RETRY_SECONDS = 300  # do not hammer the kiln list page when it fails

_REDIRECTS = (301, 302, 303, 307, 308)
_CSRF_PATTERNS = (
    re.compile(r"name=[\"']csrfmiddlewaretoken[\"'][^>]*?value=[\"']([^\"']+)"),
    re.compile(r"value=[\"']([^\"']+)[\"'][^>]*?name=[\"']csrfmiddlewaretoken"),
)

# Called with (kind, payload) for every response worth recording; see capture.py.
EventHook = Callable[[str, dict[str, Any]], None]


class MyKilnError(Exception):
    """Base error."""


class CannotConnect(MyKilnError):
    """The service could not be reached or answered unexpectedly."""


class InvalidAuth(MyKilnError):
    """The credentials were refused."""


class SessionExpired(MyKilnError):
    """The session cookie is missing or no longer valid."""


class MyKilnClient:
    """Session-cookie based client. The aiohttp session must keep cookies."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        base_url: str = BASE_URL,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._base = base_url.rstrip("/")
        self._lock = asyncio.Lock()
        self._info: dict[int, KilnInfo] = {}
        self._info_time = 0.0
        self._info_retry_at = 0.0
        # Last raw /kilns_get_status/ response, for diagnostics.
        self.last_status: list[Any] | None = None
        self.on_event: EventHook | None = None

    @property
    def kiln_info(self) -> dict[int, KilnInfo]:
        return self._info

    def _emit(self, kind: str, **payload: Any) -> None:
        if self.on_event is None:
            return
        try:
            self.on_event(kind, payload)
        except Exception:  # noqa: BLE001  recording must never break polling
            _LOGGER.exception("Could not record myKiln %s event", kind)

    def _cookie(self, name: str) -> str | None:
        morsel = self._session.cookie_jar.filter_cookies(URL(self._base)).get(name)
        return morsel.value if morsel else None

    async def async_login(self) -> None:
        async with self._lock:
            await self._login()

    async def _login(self) -> None:
        login_url = f"{self._base}/login/"
        try:
            async with self._session.get(login_url, timeout=REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                page = await resp.text()
            token = next(
                (m.group(1) for p in _CSRF_PATTERNS if (m := p.search(page))),
                None,
            ) or self._cookie("csrftoken")
            if not token:
                self._emit("login", result="no_csrf_token")
                raise CannotConnect("No CSRF token found on the login page")
            async with self._session.post(
                login_url,
                data={
                    "csrfmiddlewaretoken": token,
                    "email": self._email,
                    "password": self._password,
                },
                headers={"Referer": login_url},  # Django requires this over HTTPS
                allow_redirects=False,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                status = resp.status
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            self._emit("login", result="error", error=repr(err))
            raise CannotConnect(str(err)) from err

        self._emit("login", result="http", http_status=status)
        if status in (301, 302, 303):
            return  # success is verified by the next status call
        if status == 200:
            # Either the login form was shown again (bad credentials) or the
            # site logged us in without redirect. Decide by asking for the status.
            try:
                await self._fetch_status()
            except SessionExpired:
                raise InvalidAuth("Credentials refused") from None
            return
        raise CannotConnect(f"Unexpected HTTP {status} during login")

    async def _fetch_status(self) -> list[dict[str, Any]]:
        started = time.monotonic()
        try:
            async with self._session.get(
                f"{self._base}/kilns_get_status/",
                headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{self._base}/"},
                allow_redirects=False,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status in (*_REDIRECTS, 401, 403):
                    self._emit("session_expired", http_status=resp.status)
                    raise SessionExpired(f"HTTP {resp.status}")
                resp.raise_for_status()
                if "json" not in resp.headers.get("Content-Type", ""):
                    self._emit(
                        "session_expired",
                        http_status=resp.status,
                        content_type=resp.headers.get("Content-Type"),
                    )
                    raise SessionExpired("Not a JSON response")
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise CannotConnect(str(err)) from err
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            self._emit("status", raw=data, error="unexpected format")
            raise CannotConnect("Unexpected response format")
        self.last_status = data
        self._emit("status", raw=data, seconds=round(time.monotonic() - started, 2))
        return data

    async def _get_text(self, path: str) -> str:
        try:
            async with self._session.get(
                f"{self._base}{path}",
                headers={"Referer": f"{self._base}/"},
                allow_redirects=False,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status in (*_REDIRECTS, 401, 403):
                    raise SessionExpired(f"HTTP {resp.status}")
                resp.raise_for_status()
                return await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect(str(err)) from err

    async def _async_refresh_info(self, kiln_ids: list[int]) -> None:
        """Refresh names/models when a kiln is unknown or the cache is old."""
        now = time.monotonic()
        missing = any(kiln_id not in self._info for kiln_id in kiln_ids)
        if now < self._info_retry_at or not (
            missing or now - self._info_time > INFO_REFRESH_SECONDS
        ):
            return
        self._info_retry_at = now + INFO_RETRY_SECONDS
        try:
            page = await self._get_text("/kiln_list/")
        except MyKilnError as err:
            _LOGGER.debug("Could not read the kiln list: %s", err)
            self._emit("kiln_list", error=repr(err))
            return
        info = parse_kiln_list(page)
        # The page header may show the account email; keep it out of recordings.
        self._emit(
            "kiln_list",
            html=re.sub(re.escape(self._email), "<email>", page, flags=re.I),
            parsed={str(k): v.__dict__ for k, v in info.items()},
        )
        if info:
            self._info = info
            self._info_time = now
        else:
            _LOGGER.debug("No kilns found on the kiln list page; its layout may have changed")

    async def async_get_kilns(self) -> dict[int, KilnData]:
        """Return all kilns by id, logging in again when the session expired."""
        try:
            raw = await self._fetch_status()
        except SessionExpired:
            await self.async_login()
            try:
                raw = await self._fetch_status()
            except SessionExpired as err:
                raise InvalidAuth("Login did not produce a valid session") from err
        items = [item for item in raw if isinstance(item, dict)]
        ids = [kiln_id for item in items if (kiln_id := to_int(item.get("id"))) is not None]
        await self._async_refresh_info(ids)
        kilns = (parse_kiln(item, self._info.get(to_int(item.get("id")))) for item in items)
        return {k.kiln_id: k for k in kilns if k}
