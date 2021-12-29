# Python: Garmin Connect for Home Assistant


# NOTE: Replaced by https://github.com/cyberjunky/python-garminconnect/ v0.1.24 (compatible) so I only have to maintain one code base.

Minimal Garmin Connect Python 3 API wrapper for Home Assistant

## About

This package allows you to request your device, activity and health data from your Garmin Connect account.
See https://connect.garmin.com/

## Installation

```bash
pip install garminconnect-ha
```

## Usage

```python
#!/usr/bin/env python3
"""Example code."""
from datetime import date
import logging

from garminconnect_ha import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)

# Configure debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

today = date.today()

try:
    # Initialize Garmin Connect with your credentials
    api = Garmin(YOUR_EMAIL, YOUR_PASSWORD)

    ## User

    # Login to Garmin Connect portal
    username = api.login()
    logger.debug("Username = %s", username)

    # Get activity summary data for 'YYYY-MM-DD'
    logger.debug(api.get_user_summary(today.isoformat()))

    # Get body composition data for 'YYYY-MM-DD'
    logger.debug(api.get_body_composition(today.isoformat()))

    # Get users max metrics data for 'YYYY-MM-DD'
    logger.debug(api.get_max_metrics(today.isoformat()))

    # Get hydration data for 'YYYY-MM-DD'
    logger.debug(api.get_hydration(today.isoformat()))

    # Get personal records for current user
    logger.debug(api.get_personal_records())
    
    # Get users max metrics data for 'YYYY-MM-DD'
    logger.debug(api.get_max_metrics(today.isoformat()))

    # Get hydration data for 'YYYY-MM-DD'
    logger.debug(api.get_hydration(today.isoformat()))

    # Get personal records for current user
    logger.debug(api.get_personal_records())

    # Get sleep data for 'YYYY-MM-DD'
    logger.debug(api.get_sleep_day(today.isoformat()))

    # Get heartrate data for 'YYYY-MM-DD'
    logger.debug(api.get_rhr_day(today.isoformat()))

    ## Devices

    # Get users devices data
    devices = api.get_devices()
    logger.debug(devices)

    # Get details of users device with deviceId
    for device in devices:
        device_id = device["deviceId"]
        logger.debug(api.get_device_settings(device_id))

    # Get alarm data from all devices
    logger.debug(api.get_device_alarms())

except (
        GarminConnectConnectionError,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
    ) as err:
    logger.debug("Error occurred during Garmin Connect communication: %s", err)
