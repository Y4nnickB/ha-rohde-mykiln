"""Diagnostics download for ROHDE myKiln (Settings → Devices & services → ⋮ → Download diagnostics)."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .api import to_int
from .const import DOMAIN
from .coordinator import MyKilnConfigEntry

REDACTED = "**REDACTED**"
# Matched against lower-cased keys, also inside the raw myKiln response whose
# fields are not documented: anything that identifies the account or the hardware.
_SENSITIVE_PARTS = ("email", "password", "serial", "mac", "token", "user", "owner", "address")
_SENSITIVE_KEYS = ("id", "sn")


def _sensitive(key: str) -> bool:
    key = key.lower()
    return (
        key in _SENSITIVE_KEYS
        or key.endswith("_id")
        or any(part in key for part in _SENSITIVE_PARTS)
    )


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if _sensitive(str(key)) and item is not None else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def _common(entry: MyKilnConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "options": dict(entry.options),
        "update_interval_seconds": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
        "last_update_success": coordinator.last_update_success,
        "last_exception": repr(coordinator.last_exception)
        if coordinator.last_exception
        else None,
        "recording_to": str(coordinator.capture.path) if coordinator.capture else None,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MyKilnConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        **_common(entry),
        "raw_status": redact(coordinator.client.last_status),
        "parsed": [redact(kiln.as_dict()) for kiln in (coordinator.data or {}).values()],
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: MyKilnConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    kiln_id = next(
        (to_int(ident) for domain, ident in device.identifiers if domain == DOMAIN), None
    )
    raw = [
        item
        for item in coordinator.client.last_status or []
        if isinstance(item, dict) and to_int(item.get("id")) == kiln_id
    ]
    kiln = (coordinator.data or {}).get(kiln_id) if kiln_id is not None else None
    return {
        **_common(entry),
        "raw_status": redact(raw),
        "parsed": redact(kiln.as_dict()) if kiln else None,
    }
