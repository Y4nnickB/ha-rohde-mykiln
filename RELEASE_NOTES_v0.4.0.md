## What's new in 0.4.0

### Added
- **Icon and logo** for the integration, with light and dark variants. They show up in *Settings → Devices & services* and in the add-integration dialog on **Home Assistant 2026.3 or newer**. The artwork is original and does not use the ROHDE logo.
- **Time since last update** (diagnostic sensor): shows how long ago myKiln last heard from the controller, in hours by default (changeable in the entity settings). It stays available while the kiln is offline. The text myKiln reported is available as the attribute `reported_text`.

### Changed
- **Offline kilns are no longer shown with stale values.** When the controller is offline, all entities except *Online* are *unavailable* instead of keeping the last known status, firing state and Wi-Fi signal.

### Upgrading
1. Update through HACS and restart Home Assistant. No reconfiguration is needed.
2. Hard-refresh your browser (Ctrl+F5) afterwards; Home Assistant may cache the brand images.

If you build automations on the status, note that a kiln going offline now turns its entities *unavailable*. Use `not_to: unavailable` (and `not_from: unavailable`) on state triggers, or check the *Online* sensor.

### Notes
- Unofficial integration; it uses the same web endpoints as the myKiln website and can break if ROHDE changes them.
- Developed and tested against one kiln with an ST 310 controller. Status texts for states other than "cooling down" and "offline" have not been verified yet; reports are welcome in the issue tracker.

**Full changelog:** see `CHANGELOG.md`.
