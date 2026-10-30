<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/rohde_mykiln/brand/dark_logo@2x.png">
    <img src="custom_components/rohde_mykiln/brand/logo@2x.png" alt="Kiln" height="96">
  </picture>
</p>

# ROHDE myKiln for Home Assistant

<p align="center">
  <a href="https://github.com/Y4nnickB/ha-rohde-mykiln/actions/workflows/validate.yml"><img src="https://github.com/Y4nnickB/ha-rohde-mykiln/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=Y4nnickB&repository=ha-rohde-mykiln&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open this repository in HACS"></a>
</p>

Unofficial Home Assistant integration for ROHDE kilns with a Wi-Fi controller
(ST 310 / ST 411 / ST 630 / ST 632) that are visible in the **myKiln** app
(mykiln.eu). Not affiliated with or endorsed by Helmut ROHDE GmbH.

It uses the same web endpoints as the myKiln website, so it needs your
myKiln login and may break if ROHDE changes its site.

## Installation (HACS)

1. HACS → ⋮ → *Custom repositories* → add this repository, category *Integration*.
2. Install **ROHDE myKiln**, restart Home Assistant.
3. *Settings → Devices & services → Add integration → ROHDE myKiln* and sign in with your myKiln email and password.

Every kiln on the account becomes a device named after the kiln in myKiln (for
example "Garage"), with the controller type and serial number filled in. You can
rename a device and assign it to an area; a name you set in Home Assistant is kept
across updates, while a kiln renamed in the myKiln app is picked up automatically.

## Entities per kiln

| Entity | Notes |
| --- | --- |
| Temperature (zone 1, plus 2/3 when the kiln has them) | °C or °F as reported by the kiln |
| Status, Program | Text as reported by myKiln (in your account language) |
| Progress, Firing duration | % and minutes |
| Online, Firing active, Heating up, Cooling down | binary sensors |
| Time since last update | diagnostic; stays available while the kiln is offline. Shown in hours (changeable in the entity settings); myKiln reports the age only as coarsely as "62 hours" |
| Delayed start, Wi-Fi signal, Firing ID | disabled by default |

When the controller is offline (myKiln reports it as not communicating), all entities
except **Online** become *unavailable* instead of showing the last known values.

## Testers wanted

Developed against one kiln with an ST 310 controller. If you have another ROHDE kiln
with a Wi-Fi controller, please open a *Tested with my kiln* issue, even when everything
works. Responses from different kiln states (idle, heating, holding, offline) help most.

## Options

*Update interval* (30–600 s, default 60). The controller reports about once a
minute, so polling faster does not give fresher data.

## Notes

- Credentials are stored in the Home Assistant config entry, like other integrations that need a login. Data is only sent to mykiln.eu.
- If the session expires the integration logs in again by itself. If the password was changed, Home Assistant asks you to sign in again.
- Read-only: this integration cannot start or stop a firing.

## Branding

The icon and logo (`custom_components/rohde_mykiln/brand/`) are original artwork and
not the ROHDE logo; they are shown by Home Assistant 2026.3 or newer. They can be
regenerated with `python3 tools/make_brand.py` (needs Pillow). ROHDE and myKiln are
trademarks of their respective owners.
