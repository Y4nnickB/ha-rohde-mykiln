# Changelog

## 0.6.0
- **Added** dashboard card `custom:rohde-mykiln-card` (`custom_components/rohde_mykiln/frontend/rohde-mykiln-card.js`): kiln drawing that glows in the colour of its temperature, firing progress, temperature chart, heating rate and estimated time left. The integration loads it automatically (no resource to add) and it can be set up from the card picker with a visual editor.

## 0.5.0
- **Added** option *Record raw data*: writes every myKiln response, re-login and failed poll to `rohde_mykiln_capture/` in the Home Assistant config folder, to troubleshoot a firing. See `docs/recording-a-firing.md`.
- **Added** diagnostics download (integration entry and per kiln) with the latest raw response and the parsed values; email, serial numbers and IDs are removed.
- **Added** `tools/replay_capture.py` to replay a recording as a timeline or CSV, and parser tests (`pytest`), also run by GitHub Actions.
- **Changed** (no change in behaviour) response parsing moved to `parser.py`, which has no Home Assistant dependencies.

## 0.4.2
- **Changed** the integration icon is now the myKiln app icon and the logo is the ROHDE logo, used with permission of Helmut ROHDE GmbH (see `docs/rohde-statement.md`). Light logo plus a white variant for dark mode.
- **Removed** the original artwork and `tools/make_brand.py`.
- **Docs** added a statement from ROHDE and updated the disclaimer: this is an independent project, not developed or officially supported by ROHDE.

## 0.4.1
- **Fixed** the documentation and issue tracker links in the integration manifest now point to this repository.
- **Added** (repository only, no change in behaviour) GitHub Actions that validate the integration with hassfest and HACS, issue forms for bug reports and kiln compatibility reports, and badges in the README.

## 0.4.0
- **Added** integration icon and logo, with light/dark and @2x variants (shown by Home Assistant 2026.3 or newer). Original artwork, not the ROHDE logo.
- **Added** `tools/make_brand.py` to regenerate the images.

## 0.3.0
- **Added** diagnostic sensor *Time since last update*, based on the "last updated" text myKiln reports. It stays available while the kiln is offline. The reported text is available as the attribute `reported_text`.

## 0.2.1
- **Changed** when the controller is offline, all entities except *Online* become unavailable instead of showing the last known values (myKiln keeps returning those, including a stale "Cooling down" and Wi-Fi signal).

## 0.2.0
- **Added** the kiln name from the myKiln kiln list is used as device name; the controller type and serial number are filled in on the device, and the model is derived from the kiln image.
- **Added** a name set in Home Assistant is kept; a kiln renamed in the myKiln app is picked up automatically.
- **Changed** the kiln list is read at startup, hourly and when an unknown kiln appears, not on every update.

## 0.1.0
- First release: sign in through the UI, one device per kiln, temperature, status, program, progress, firing duration and online/firing/heating/cooling binary sensors, automatic re-login, reauthentication and an update-interval option.
