## What's new in 0.7.0

Fixes and additions based on a recorded glaze firing (ST310 controller): heating up, a hold ("Soak") at the top temperature and cooling down.

### Fixed
- **Heating up** stayed on while the kiln held its top temperature ("Soak"). It is now off during a hold.
- Before a firing, **Status** and **Program** showed a literal "-". Status now shows myKiln's summary (for example "Inactive") and Program is empty.

### Added
- Sensor **Phase**: idle, delayed start, heating up, holding, cooling down. One entity for automations.
- Binary sensor **Holding**.
- Sensor **Programmed heating rate**: the rate of the current ramp in °C/h, as programmed on the controller.
- The dashboard card shows **Holding** during a soak and the programmed rate next to the measured rate while heating.

### Upgrading
Update through HACS, restart Home Assistant and refresh your browser. No reconfiguration is needed; the new entities appear on the kiln's device.

If you have automations on *Heating up*, note that it now turns off during a hold. Use *Firing active* or the new *Phase* sensor for "the kiln is running a program".

**Full changelog:** see `CHANGELOG.md`.
