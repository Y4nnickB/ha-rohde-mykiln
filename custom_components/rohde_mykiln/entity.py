"""Base entity for ROHDE myKiln."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import KilnData
from .const import BASE_URL, DOMAIN
from .coordinator import MyKilnCoordinator


class MyKilnEntity(CoordinatorEntity[MyKilnCoordinator]):
    """One entity belonging to one kiln device."""

    _attr_has_entity_name = True
    # When the controller is offline myKiln keeps returning the last known values.
    # Entities that depend on live data go "unavailable" instead of showing stale data.
    _requires_online = True

    def __init__(self, coordinator: MyKilnCoordinator, kiln_id: int) -> None:
        super().__init__(coordinator)
        self._kiln_id = kiln_id
        kiln = coordinator.data[kiln_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(kiln_id))},
            name=kiln.name,
            manufacturer="ROHDE",
            model=kiln.model or "Kiln",
            model_id=kiln.controller,
            serial_number=kiln.serial,
            configuration_url=f"{BASE_URL}/kiln_edit/{kiln_id}/",
        )

    @property
    def kiln(self) -> KilnData | None:
        return self.coordinator.data.get(self._kiln_id)

    @property
    def available(self) -> bool:
        kiln = self.kiln
        return (
            super().available
            and kiln is not None
            and (kiln.online or not self._requires_online)
        )
