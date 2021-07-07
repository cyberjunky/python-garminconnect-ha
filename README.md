# Python: Garmin Connect for Home Assistant

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
    # Initialize Garmin Connect client with your credentials
    client = Garmin(YOUR_EMAIL, YOUR_PASSWORD)

    ## User

    # Login to Garmin Connect portal
    username = client.login()
    logger.debug("Username = %s", username)


    # Get users activity summary data for 'YYYY-MM-DD'
    logger.debug(client.get_user_summary(today.isoformat()))

    # Get users body composition data for 'YYYY-MM-DD'
    logger.debug(client.get_body_composition(today.isoformat()))

    ## Devices

    # Get users devices data
    devices = client.get_devices()
    logger.debug(devices)

    # Get details of users device with deviceId
    for device in devices:
        device_id = device["deviceId"]
        logger.debug(client.get_device_settings(device_id))

    # Get alarm data from all devices
    logger.debug(client.get_device_alarms())

    # Get users max metrics data for 'YYYY-MM-DD'
    logger.debug(client.get_max_metrics(today.isoformat()))

except (
        GarminConnectConnectionError,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
    ) as err:
    logger.debug("Error occurred during Garmin Connect communication: %s", err)
