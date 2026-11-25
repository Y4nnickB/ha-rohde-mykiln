"""Parsing of myKiln responses.

Kept free of Home Assistant and aiohttp imports, so the tests and
tools/replay_capture.py can load it on their own.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import html
import re
from typing import Any

_TEMP_RE = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*°?\s*([CFcf])?")
_AGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*([^\W\d_]+)")
_HOURS_RE = re.compile(r"(\d+)\s*(?:hrs?|hours?|uur|u)\b", re.I)
_MINUTES_RE = re.compile(r"(\d+)\s*(?:mins?|minutes?|minuten|m)\b", re.I)
# firing_status while ramping, e.g. "Stoken bij 150 °C/hr" (nl) -> 150 °C per hour.
_RATE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*°?\s*([CF])\s*/\s*(?:hrs?|hours?|h|uur|u|std|stunde)\b", re.I)
# firing_status while holding at temperature; myKiln sends "Soak" (also in a Dutch account).
_HOLD_RE = re.compile(r"\b(?:soak\w*|hold\w*|houd\w*|halte\w*)\b", re.I)
# myKiln sends "-" for fields that have no value (no program, not firing).
_PLACEHOLDERS = frozenset({"-", "--", "–", "—"})

PHASES = ("idle", "delayed_start", "heating", "holding", "cooling")

# /kiln_list/ is HTML. Per kiln: <h3>NAME</h3> directly followed by the /kiln_edit/<id>/ link.
# [^<] keeps a match from spanning over unrelated <h3> elements.
_KILN_RE = re.compile(
    r"<h3[^>]*>(?P<name>[^<]+)</h3>\s*<a[^>]*href=[\"']/kiln_edit/(?P<id>\d+)/[\"']"
)
_CONTROLLER_RE = re.compile(
    r"<h3[^>]*>\s*(?P<type>[^<]+?)\s*</h3>\s*<p[^>]*>\s*(?:SN|S/N)\s*(?P<sn>[^<\s]+)\s*</p>"
)
_KILN_IMAGE_RE = re.compile(r"/media/kiln_images/[^\"'/]+/(?P<stem>[^\"'/]+?)\.[A-Za-z]{3,4}[\"']")


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
    comms_text: str | None  # e.g. "Laatst bijgewerkt: 62 uur geleden"
    last_update_seconds: int | None  # age of the last report, as coarse as myKiln states it
    is_holding: bool = False  # firing, holding at temperature ("Soak")
    ramp_rate: float | None = None  # programmed rate of the current segment, degrees per hour

    @property
    def is_heating(self) -> bool:
        """Firing and still ramping: not holding and not cooling down."""
        return self.is_firing and not self.is_cooling and not self.is_holding

    @property
    def phase(self) -> str:
        if self.is_delayed_start:
            return "delayed_start"
        if self.is_firing and self.is_cooling:
            return "cooling"
        if self.is_holding:
            return "holding"
        if self.is_firing:
            return "heating"
        return "idle"

    def as_dict(self) -> dict[str, Any]:
        """All fields plus derived values, for recordings and diagnostics."""
        data = asdict(self)
        data["temperatures"] = list(self.temperatures)
        data["is_heating"] = self.is_heating
        data["phase"] = self.phase
        return data


def _text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value if value and value not in _PLACEHOLDERS else None


def parse_ramp_rate(value: Any) -> float | None:
    """Parse 'Stoken bij 150 °C/hr' -> 150.0; None when the text has no rate."""
    text = _text(value)
    match = _RATE_RE.search(text) if text else None
    return float(match.group(1).replace(",", ".")) if match else None


def is_hold_text(value: Any) -> bool:
    """True for the firing status myKiln shows while holding at temperature."""
    text = _text(value)
    return bool(text and _HOLD_RE.search(text))


def to_int(value: Any) -> int | None:
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


def parse_age(value: Any) -> int | None:
    """Parse the age in 'Laatst bijgewerkt: 62 uur geleden' -> seconds.

    myKiln writes this in the account language, so the common units of nl/en/de
    are understood. Returns None when no amount and unit can be found.
    """
    text = _text(value)
    if not text:
        return None
    match = _AGE_RE.search(text)
    if not match:
        return None
    amount = float(match.group(1).replace(",", "."))
    unit = match.group(2).lower()
    if unit.startswith(("sec", "sek")):
        factor = 1
    elif unit.startswith(("min",)):
        factor = 60
    elif unit.startswith(("uur", "hour", "hr", "stunde", "std")) or unit in ("h", "u"):
        factor = 3600
    elif unit.startswith(("dag", "day", "tag")):
        factor = 86400
    elif unit.startswith(("week", "woche")):
        factor = 604800
    else:
        return None
    return round(amount * factor)


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
    kiln_id = to_int(raw.get("id"))
    if kiln_id is None:
        return None
    temps: list[float | None] = []
    unit: str | None = None
    for idx in (1, 2, 3):
        value, found_unit = parse_temperature(raw.get(f"temperature_{idx}"))
        temps.append(value)
        unit = unit or found_unit
    is_firing = bool(raw.get("is_firing"))
    is_cooling = bool(raw.get("is_cooling"))
    firing_status = raw.get("firing_status")
    is_holding = is_firing and not is_cooling and is_hold_text(firing_status)
    return KilnData(
        kiln_id=kiln_id,
        name=info.name if info else f"ROHDE oven {kiln_id}",
        model=info.model if info else None,
        controller=info.controller if info else None,
        serial=info.serial if info else None,
        zones=to_int(raw.get("zones")) or 1,
        online=bool(raw.get("is_communicating")),
        temperatures=(temps[0], temps[1], temps[2]),
        unit=unit or "C",
        status=_text(firing_status) or _text(raw.get("kiln_status_summary")),
        summary=_text(raw.get("kiln_status_summary")),
        is_firing=is_firing,
        is_cooling=is_cooling,
        is_delayed_start=bool(raw.get("is_delayed_start")),
        program=_text(raw.get("program_title")),
        percentage=to_int(raw.get("firing_percentage")),
        duration_minutes=parse_duration(raw.get("firing_duration")),
        wifi_bars=to_int(raw.get("wifi_bars")),
        firing_id=to_int(raw.get("firing_id")),
        comms_text=_text(raw.get("comms_status")),
        last_update_seconds=parse_age(raw.get("comms_status")),
        is_holding=is_holding,
        ramp_rate=parse_ramp_rate(firing_status)
        if is_firing and not is_cooling and not is_holding
        else None,
    )
