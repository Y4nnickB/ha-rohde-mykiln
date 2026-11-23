"""Recording of raw myKiln responses, to troubleshoot a firing afterwards.

When the "Record raw data" option is on, every poll appends JSON lines to
<config>/rohde_mykiln_capture/<start time>.jsonl:

  start         once, when the integration is set up
  status        the raw /kilns_get_status/ response
  kiln_list     the /kiln_list/ page (account email replaced) and what was parsed from it
  login         a (re-)login attempt and its HTTP result
  session_expired  myKiln no longer accepted the session
  parsed        what the integration made of the poll (per kiln)
  error         a poll that failed

Every line has "time" (local time with offset). tools/replay_capture.py reads the file.
No password or cookie is ever written.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import CAPTURE_DIR

_LOGGER = logging.getLogger(__name__)


class FiringCapture:
    """Buffers events during a poll and appends them to the file afterwards."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self.path = Path(hass.config.path(CAPTURE_DIR)) / (
            f"{dt_util.now():%Y%m%d-%H%M%S}.jsonl"
        )
        self._buffer: list[str] = []
        self._warned = False

    @callback
    def record(self, kind: str, payload: dict[str, Any]) -> None:
        line = {"time": dt_util.now().isoformat(timespec="seconds"), "kind": kind, **payload}
        self._buffer.append(json.dumps(line, ensure_ascii=False, default=str))

    async def async_flush(self) -> None:
        if not self._buffer:
            return
        lines, self._buffer = self._buffer, []
        try:
            await self._hass.async_add_executor_job(self._write, lines)
        except OSError as err:
            if not self._warned:
                _LOGGER.warning("Could not write myKiln recording to %s: %s", self.path, err)
                self._warned = True

    def _write(self, lines: list[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")
