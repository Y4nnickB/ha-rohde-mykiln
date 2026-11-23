## What's new in 0.5.0

This release is about troubleshooting: when a sensor does not do what you expect during a firing, you can now record what myKiln reports and share it. No change in how the existing entities behave.

### Added
- **Record raw data** (option, off by default). Every update writes the raw myKiln response, what the integration made of it, re-logins and failed updates to a file in the `rohde_mykiln_capture` folder of your Home Assistant configuration. No password or session cookie is stored. See **Recording a firing** (`docs/recording-a-firing.md`) for a checklist.
- **Download diagnostics** on the integration entry and on each kiln's device page, with the latest raw myKiln response and the parsed values. Email, serial numbers and IDs are removed, so it can be attached to an issue.
- `tools/replay_capture.py` replays a recording as a timeline of changes or as a CSV file.
- Parser tests (`pytest`), also run by GitHub Actions on every change.

### Changed
- Response parsing moved to its own module (`parser.py`). No change in behaviour.

### Upgrading
Update through HACS and restart Home Assistant. No reconfiguration is needed.

To record a firing: *Settings → Devices & services → ROHDE myKiln → Configure*, set the update interval to 30 and turn on *Record raw data*. Turn it off again when the firing is done; a day of recording is a few MB.

**Full changelog:** see `CHANGELOG.md`.
