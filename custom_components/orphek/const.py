"""Constants for the Orphek integration."""

DOMAIN = "orphek"

CONF_DEVICE_ID = "device_id"
CONF_HOST = "host"
CONF_LOCAL_KEY = "local_key"
CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_API_REGION = "api_region"
CONF_CLOUD_CREDENTIALS = "cloud_credentials"

TUYA_VERSION = 3.4

# Tuya DP mappings for Orphek OR4-iCon LED Bar
DP_SWITCH = 20  # bool: on/off
DP_BRIGHTNESS = 22  # int: 10-1000

BRIGHTNESS_MIN = 10
BRIGHTNESS_MAX = 1000
