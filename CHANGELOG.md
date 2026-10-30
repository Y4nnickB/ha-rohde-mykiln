# Changelog

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
