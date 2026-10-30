"""Minimal async client for the ROHDE myKiln web app (unofficial, reverse engineered)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import html
import logging
import re
import time
from typing import Any

import aiohttp
from yarl import URL

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
INFO_REFRESH_SECONDS = 3600  # kiln names/models rarely change
INFO_RETRY_SECONDS = 300  # do not hammer the kiln list page when it fails

_REDIRECTS = (301, 302, 303, 307, 308)
_CSRF_PATTERNS = (
    re.compile(r"name=[\"']csrfmiddlewaretoken[\"'][^>]*?value=[\"']([^\"']+)"),
    re.compile(r"value=[\"']([^\"']+)[\"'][^>]*?name=[\"']csrfmiddlewaretoken"),
)
_TEMP_RE = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*°?\s*([CFcf])?")
_HOURS_RE = re.compile(r"(\d+)\s*(?:hrs?|hours?|uur|u)\b", re.I)
_MINUTES_RE = re.compile(r"(\d+)\s*(?:mins?|minutes?|minuten|m)\b", re.I)

# /kiln_list/ is HTML. Per kiln: <h3>NAME</h3> directly followed by the /kiln_edit/<id>/ link.
# [^<] keeps a match from spanning over unrelated <h3> elements.
_KILN_RE = re.compile(
    r"<h3[^>]*>(?P<name>[^<]+)</h3>\s*<a[^>]*href=[\"']/kiln_edit/(?P<id>\d+)/[\"']"
)
_CONTROLLER_RE = re.compile(
    r"<h3[^>]*>\s*(?P<type>[^<]+?)\s*</h3>\s*<p[^>]*>\s*(?:SN|S/N)\s*(?P<sn>[^<\s]+)\s*</p>"
)
_KILN_IMAGE_RE = re.compile(r"/media/kiln_images/[^\"'/]+/(?P<stem>[^\"'/]+?)\.[A-Za-z]{3,4}[\"']")


class MyKilnError(Exception):
    """Base error."""


class CannotConnect(MyKilnError):
    """The service could not be reached or answered unexpectedly."""


class InvalidAuth(MyKilnError):
    """The credentials were refused."""


class SessionExpired(MyKilnError):
    """The session cookie is missing or no longer valid."""


@dataclass(frozen=True)
class KilnInfo:
    """Static details of a kiln, scraped from the kiln list page."""

    name: str
    model: str | None = None  # derived from the kiln image file name
    controller: str | None = None  # e.g. "ST310"
    serial: str | None = None


@dataclass(frozen=True)
class KilnData:
    """Parsed state of one kiln."""

    kiln_id: int
    name: str
    model: str | None
    controller: str | None
    serial: str | None
    zones: int
    online: bool
    temperatures: tuple[float | None, float | None, float | None]
    unit: str  # "C" or "F"
    status: str | None
    summary: str | None
    is_firing: bool
    is_cooling: bool
    is_delayed_start: bool
    program: str | None
    percentage: int | None
    duration_minutes: int | None
    wifi_bars: int | None
    firing_id: int | None

    @property
    def is_heating(self) -> bool:
        return self.is_firing and not self.is_cooling


def _text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_temperature(value: Any) -> tuple[float | None, str | None]:
    """Parse '173°C' -> (173.0, 'C'); '-°C' or empty -> (None, None)."""
    text = _text(value)
    if not text:
        return None, None
    match = _TEMP_RE.search(text)
    if not match:
        return None, None
    unit = match.group(2).upper() if match.group(2) else None
    return float(match.group(1).replace(",", ".")), unit


def parse_duration(value: Any) -> int | None:
    """Parse '26 hrs 17 mins' -> 1577."""
    text = _text(value)
    if not text:
        return None
    hours = _HOURS_RE.search(text)
    minutes = _MINUTES_RE.search(text)
    if not (hours or minutes):
        return None
    return (int(hours.group(1)) if hours else 0) * 60 + (
        int(minutes.group(1)) if minutes else 0
    )


def parse_kiln_list(page: str) -> dict[int, KilnInfo]:
    """Extract kiln id -> name/model/controller from the /kiln_list/ HTML."""
    # Controllers that are not linked to a kiln are listed after this marker.
    cut = page.find("Unlinked controller area")
    if cut != -1:
        page = page[:cut]
    matches = list(_KILN_RE.finditer(page))
    result: dict[int, KilnInfo] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(page)
        segment = page[match.end() : end]
        name = html.unescape(match.group("name")).strip()
        if not name:
            continue
        image = _KILN_IMAGE_RE.search(segment)
        controller = _CONTROLLER_RE.search(segment)
        result[int(match.group("id"))] = KilnInfo(
            name=name,
            model=re.sub(r"[-_]+", " ", image.group("stem")).strip() if image else None,
            controller=html.unescape(controller.group("type")).strip() if controller else None,
            serial=html.unescape(controller.group("sn")).strip() if controller else None,
        )
    return result


def parse_kiln(raw: dict[str, Any], info: KilnInfo | None = None) -> KilnData | None:
    kiln_id = _int(raw.get("id"))
    if kiln_id is None:
        return None
    temps: list[float | None] = []
    unit: str | None = None
    for idx in (1, 2, 3):
        value, found_unit = parse_temperature(raw.get(f"temperature_{idx}"))
        temps.append(value)
        unit = unit or found_unit
    return KilnData(
        kiln_id=kiln_id,
        name=info.name if info else f"ROHDE oven {kiln_id}",
        model=info.model if info else None,
        controller=info.controller if info else None,
        serial=info.serial if info else None,
        zones=_int(raw.get("zones")) or 1,
        online=bool(raw.get("is_communicating")),
        temperatures=(temps[0], temps[1], temps[2]),
        unit=unit or "C",
        status=_text(raw.get("firing_status")) or _text(raw.get("kiln_status_summary")),
        summary=_text(raw.get("kiln_status_summary")),
        is_firing=bool(raw.get("is_firing")),
        is_cooling=bool(raw.get("is_cooling")),
        is_delayed_start=bool(raw.get("is_delayed_start")),
        program=_text(raw.get("program_title")),
        percentage=_int(raw.get("firing_percentage")),
        duration_minutes=parse_duration(raw.get("firing_duration")),
        wifi_bars=_int(raw.get("wifi_bars")),
        firing_id=_int(raw.get("firing_id")),
    )


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
            raise CannotConnect(str(err)) from err

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
        try:
            async with self._session.get(
                f"{self._base}/kilns_get_status/",
                headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{self._base}/"},
                allow_redirects=False,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status in (*_REDIRECTS, 401, 403):
                    raise SessionExpired(f"HTTP {resp.status}")
                resp.raise_for_status()
                if "json" not in resp.headers.get("Content-Type", ""):
                    raise SessionExpired("Not a JSON response")
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise CannotConnect(str(err)) from err
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise CannotConnect("Unexpected response format")
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
            info = parse_kiln_list(await self._get_text("/kiln_list/"))
        except MyKilnError as err:
            _LOGGER.debug("Could not read the kiln list: %s", err)
            return
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
        ids = [kiln_id for item in items if (kiln_id := _int(item.get("id"))) is not None]
        await self._async_refresh_info(ids)
        kilns = (parse_kiln(item, self._info.get(_int(item.get("id")))) for item in items)
        return {k.kiln_id: k for k in kilns if k}
