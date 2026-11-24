## What's new in 0.6.0

A dashboard card for your kiln, installed and loaded together with the integration.

### Added
- **ROHDE myKiln card** (`custom:rohde-mykiln-card`):
  - A drawing of the kiln, top loader or front loader depending on the model, that glows in the colour of its temperature: dark red around 600 °C, orange around 1000 °C, yellow-white near 1250 °C.
  - Heating, cooling, idle, delayed start and offline states, each with its own colour.
  - Firing progress, firing time, heating rate (°/h), estimated time left and when myKiln last heard from the kiln.
  - A temperature chart since the start of the firing.
  - Light and dark themes; English, Dutch and German.
- The card is **loaded automatically** by the integration: no file to copy, no resource to add.
- A **visual editor**: *Edit dashboard → Add card → ROHDE myKiln*.

### Upgrading
1. Update through HACS and restart Home Assistant. No reconfiguration is needed.
2. Refresh your browser once.
3. If you added the card by hand before this release, remove that resource (*Settings → Dashboards → ⋮ → Resources*) and the copied file in `www`, so only one version is loaded.

**Full changelog:** see `CHANGELOG.md`.
