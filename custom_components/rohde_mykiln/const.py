"""Constants for the ROHDE myKiln integration."""

DOMAIN = "rohde_mykiln"
BASE_URL = "https://www.mykiln.eu"

DEFAULT_SCAN_INTERVAL = 60  # seconds; the controller reports roughly once a minute
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 600
