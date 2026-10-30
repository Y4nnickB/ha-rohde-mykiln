"""The ROHDE myKiln integration (unofficial)."""
from __future__ import annotations

import aiohttp

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.device_registry import DeviceEntry

from .api import MyKilnClient
from .const import DOMAIN
from .coordinator import MyKilnConfigEntry, MyKilnCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: MyKilnConfigEntry) -> bool:
    # Own session with its own cookie jar: the login lives in the session cookie.
    session = async_create_clientsession(hass, cookie_jar=aiohttp.CookieJar())
    client = MyKilnClient(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    coordinator = MyKilnCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options))
    return True


async def _async_reload_on_options(hass: HomeAssistant, entry: MyKilnConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: MyKilnConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: MyKilnConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Allow deleting a device only when the kiln is gone from the account."""
    current = {str(kiln_id) for kiln_id in entry.runtime_data.data}
    return not any(
        domain == DOMAIN and ident in current
        for domain, ident in device_entry.identifiers
    )
