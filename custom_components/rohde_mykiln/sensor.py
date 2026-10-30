"""Sensors for ROHDE myKiln."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import KilnData
from .coordinator import MyKilnConfigEntry, MyKilnCoordinator
from .entity import MyKilnEntity


@dataclass(frozen=True, kw_only=True)
class MyKilnSensorDescription(SensorEntityDescription):
    value_fn: Callable[[KilnData], StateType]
    exists_fn: Callable[[KilnData], bool] = lambda _kiln: True
    # Sensors that describe the connection itself must stay available while offline.
    requires_online: bool = True
    attrs_fn: Callable[[KilnData], dict[str, Any]] | None = None


def _temperature(index: int) -> MyKilnSensorDescription:
    return MyKilnSensorDescription(
        key=f"temperature_{index + 1}",
        translation_key=f"temperature_{index + 1}",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=0,
        value_fn=lambda kiln: kiln.temperatures[index],
        exists_fn=lambda kiln: kiln.zones > index,
    )


SENSORS: tuple[MyKilnSensorDescription, ...] = (
    _temperature(0),
    _temperature(1),
    _temperature(2),
    MyKilnSensorDescription(
        key="status", translation_key="status", value_fn=lambda k: k.status
    ),
    MyKilnSensorDescription(
        key="program", translation_key="program", value_fn=lambda k: k.program
    ),
    MyKilnSensorDescription(
        key="progress",
        translation_key="progress",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda k: k.percentage,
    ),
    MyKilnSensorDescription(
        key="duration",
        translation_key="duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda k: k.duration_minutes,
    ),
    MyKilnSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_online=False,
        value_fn=lambda k: k.last_update_seconds
        if k.last_update_seconds is not None
        else (0 if k.online else None),
        attrs_fn=lambda k: {"reported_text": k.comms_text},
    ),
    MyKilnSensorDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda k: k.wifi_bars,
    ),
    MyKilnSensorDescription(
        key="firing_id",
        translation_key="firing_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda k: k.firing_id,
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
        new: list[MyKilnSensor] = []
        for kiln_id, kiln in coordinator.data.items():
            if kiln_id in known:
                continue
            known.add(kiln_id)
            new.extend(
                MyKilnSensor(coordinator, description, kiln_id)
                for description in SENSORS
                if description.exists_fn(kiln)
            )
        if new:
            async_add_entities(new)

    _add_new_kilns()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_kilns))


class MyKilnSensor(MyKilnEntity, SensorEntity):
    entity_description: MyKilnSensorDescription

    def __init__(
        self,
        coordinator: MyKilnCoordinator,
        description: MyKilnSensorDescription,
        kiln_id: int,
    ) -> None:
        super().__init__(coordinator, kiln_id)
        self.entity_description = description
        self._attr_unique_id = f"{kiln_id}_{description.key}"
        self._requires_online = description.requires_online

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        kiln = self.kiln
        fn = self.entity_description.attrs_fn
        return fn(kiln) if kiln is not None and fn is not None else None

    @property
    def native_value(self) -> StateType:
        kiln = self.kiln
        return None if kiln is None else self.entity_description.value_fn(kiln)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.device_class is SensorDeviceClass.TEMPERATURE:
            kiln = self.kiln
            if kiln is not None and kiln.unit == "F":
                return UnitOfTemperature.FAHRENHEIT
            return UnitOfTemperature.CELSIUS
        return self.entity_description.native_unit_of_measurement
