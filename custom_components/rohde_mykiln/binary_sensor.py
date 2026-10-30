"""Binary sensors for ROHDE myKiln."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import KilnData
from .coordinator import MyKilnConfigEntry, MyKilnCoordinator
from .entity import MyKilnEntity


@dataclass(frozen=True, kw_only=True)
class MyKilnBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[KilnData], bool]


BINARY_SENSORS: tuple[MyKilnBinarySensorDescription, ...] = (
    MyKilnBinarySensorDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda k: k.online,
    ),
    MyKilnBinarySensorDescription(
        key="firing",
        translation_key="firing",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda k: k.is_firing,
    ),
    MyKilnBinarySensorDescription(
        key="heating", translation_key="heating", value_fn=lambda k: k.is_heating
    ),
    MyKilnBinarySensorDescription(
        key="cooling", translation_key="cooling", value_fn=lambda k: k.is_cooling
    ),
    MyKilnBinarySensorDescription(
        key="delayed_start",
        translation_key="delayed_start",
        entity_registry_enabled_default=False,
        value_fn=lambda k: k.is_delayed_start,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyKilnConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    known: set[int] = set()

    @callback
    def _add_new_kilns() -> None:
        new: list[MyKilnBinarySensor] = []
        for kiln_id in coordinator.data:
            if kiln_id in known:
                continue
            known.add(kiln_id)
            new.extend(
                MyKilnBinarySensor(coordinator, description, kiln_id)
                for description in BINARY_SENSORS
            )
        if new:
            async_add_entities(new)

    _add_new_kilns()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_kilns))


class MyKilnBinarySensor(MyKilnEntity, BinarySensorEntity):
    entity_description: MyKilnBinarySensorDescription

    def __init__(
        self,
        coordinator: MyKilnCoordinator,
        description: MyKilnBinarySensorDescription,
        kiln_id: int,
    ) -> None:
        super().__init__(coordinator, kiln_id)
        self.entity_description = description
        self._attr_unique_id = f"{kiln_id}_{description.key}"
        # The "Online" sensor itself must stay available to show that the kiln is offline.
        self._requires_online = description.key != "online"

    @property
    def is_on(self) -> bool | None:
        kiln = self.kiln
        return None if kiln is None else self.entity_description.value_fn(kiln)
