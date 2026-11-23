"""Data update coordinator for ROHDE myKiln."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, KilnData, MyKilnClient
from .capture import FiringCapture
from .const import CONF_CAPTURE, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type MyKilnConfigEntry = ConfigEntry[MyKilnCoordinator]


class MyKilnCoordinator(DataUpdateCoordinator[dict[int, KilnData]]):
    """Polls the myKiln status endpoint for all kilns of the account."""

    config_entry: MyKilnConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: MyKilnConfigEntry, client: MyKilnClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self.capture: FiringCapture | None = None
        if entry.options.get(CONF_CAPTURE):
            self.capture = FiringCapture(hass)
            client.on_event = self.capture.record
            self.capture.record(
                "start",
                {
                    "home_assistant": HA_VERSION,
                    "scan_interval": self.update_interval.total_seconds(),
                },
            )
            _LOGGER.warning(
                "Recording raw myKiln data to %s. Turn off 'Record raw data' in the "
                "integration options when the firing is done",
                self.capture.path,
            )

    async def _async_update_data(self) -> dict[int, KilnData]:
        try:
            data = await self.client.async_get_kilns()
        except InvalidAuth as err:
            self._record_error(err)
            raise ConfigEntryAuthFailed("myKiln credentials were refused") from err
        except CannotConnect as err:
            self._record_error(err)
            raise UpdateFailed(f"Error talking to myKiln: {err}") from err
        except Exception as err:
            self._record_error(err)
            raise
        else:
            if self.capture:
                self.capture.record(
                    "parsed", {"kilns": {str(k): v.as_dict() for k, v in data.items()}}
                )
        finally:
            if self.capture:
                await self.capture.async_flush()
        self._sync_devices(data)
        return data

    def _record_error(self, err: Exception) -> None:
        if self.capture:
            self.capture.record("error", {"type": type(err).__name__, "message": str(err)})

    def _sync_devices(self, data: dict[int, KilnData]) -> None:
        """Keep device name/model in step with myKiln (e.g. a kiln renamed in the app).

        A name the user set in Home Assistant lives in name_by_user and is never touched.
        """
        registry = dr.async_get(self.hass)
        for kiln_id, kiln in data.items():
            device = registry.async_get_device(identifiers={(DOMAIN, str(kiln_id))})
            if device is None:
                continue
            changes: dict[str, str] = {}
            if device.name != kiln.name:
                changes["name"] = kiln.name
            if kiln.model and device.model != kiln.model:
                changes["model"] = kiln.model
            if kiln.controller and device.model_id != kiln.controller:
                changes["model_id"] = kiln.controller
            if kiln.serial and device.serial_number != kiln.serial:
                changes["serial_number"] = kiln.serial
            if changes:
                registry.async_update_device(device.id, **changes)
