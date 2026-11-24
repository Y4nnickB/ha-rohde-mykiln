"""Serve the dashboard card and load it in every browser, so no manual resource is needed."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILE = Path(__file__).parent / "rohde-mykiln-card.js"
CARD_URL = f"/{DOMAIN}/rohde-mykiln-card.js"
_DATA_KEY = f"{DOMAIN}_frontend"


async def async_register_card(hass: HomeAssistant) -> None:
    """Register the card once per Home Assistant run.

    The URL carries a hash of the file, so browsers pick up a new card version
    after an update without clearing their cache.
    """
    if hass.data.get(_DATA_KEY):
        return
    hass.data[_DATA_KEY] = True
    try:
        content = await hass.async_add_executor_job(CARD_FILE.read_bytes)
    except OSError as err:
        _LOGGER.warning("Dashboard card not available: %s", err)
        return
    version = hashlib.sha1(content).hexdigest()[:8]  # noqa: S324  cache key only
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_FILE), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={version}")
