# Statement from ROHDE

In November 2026 the author of this integration contacted Helmut ROHDE GmbH,
the maker of ROHDE kilns and the myKiln service, to ask whether they had any
objections to this integration, whether an official API exists, and whether the
ROHDE and myKiln names and the ROHDE logo may be used. ROHDE replied positively.

## Summary of the reply

- ROHDE appreciates that the integration is **read-only**, limits the number of
  data requests, and keeps users' credentials within their own Home Assistant
  installation.
- There is **no official myKiln API** at present. ROHDE will discuss the topic
  internally, but its current focus is on myKiln's core functions, so there is
  no commitment to an API or an official integration.
- The **ROHDE and myKiln names and the ROHDE logo** may be used to identify the
  products and the service this integration works with.
- Condition: it must be clear that **myKiln is a ROHDE service**, and that this
  Home Assistant integration is an **independent project** that is *not
  developed or officially supported by ROHDE*.

## How this is applied

- The README states that myKiln is a ROHDE service and that this integration
  is an independent project, not developed or officially supported by ROHDE.
- Since version 0.4.2 the integration uses the myKiln app icon and the ROHDE
  logo in Home Assistant, only to identify the products and service it works
  with.

## What this means for users

- This integration is still **unofficial**. Please do not contact ROHDE support
  about it; open an issue in this repository instead.
- It relies on the same web endpoints as the myKiln website. These are not a
  public API and may change without notice.
- Users' myKiln credentials stay in their own Home Assistant installation and
  are only sent to mykiln.eu.
