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

from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)

from datetime import date


"""
Enable debug logging
"""
import logging
logging.basicConfig(level=logging.DEBUG)

today = date.today()


"""
Initialize Garmin Connect client with credentials
"""
print("Garmin(email, password)")
print("----------------------------------------------------------------------------------------")
try:
    client = Garmin(YOUR_EMAIL, YOUR_PASSWORD)
except (
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
) as err:
    print("Error occurred during Garmin Connect Client init: %s" % err)
    quit()
except Exception:  # pylint: disable=broad-except
    print("Unknown error occurred during Garmin Connect Client init")
    quit()


"""
Login to Garmin Connect portal
"""
print("client.login()")
print("----------------------------------------------------------------------------------------")
try:
    client.login()
except (
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
) as err:
    print("Error occurred during Garmin Connect Client login: %s" % err)
    quit()
except Exception:  # pylint: disable=broad-except
    print("Unknown error occurred during Garmin Connect Client login")
    quit()


"""
Get email address from users profile
"""
print("client.get_email_address()")
print("----------------------------------------------------------------------------------------")
try:
    print(client.get_full_name())
except (
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
) as err:
    print("Error occurred during Garmin Connect Client get email_address: %s" % err)
    quit()
except Exception:  # pylint: disable=broad-except
    print("Unknown error occurred during Garmin Connect Client get email_address")
    quit()



"""
Get user data
"""
print("client.get_user_data(%s)", today.isoformat())
print("----------------------------------------------------------------------------------------")
try:
    print(client.get_user_data(today.isoformat()))
except (
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
) as err:
    print("Error occurred during Garmin Connect Client get user data: %s" % err)
    quit()
except Exception:  # pylint: disable=broad-except
    print("Unknown error occurred during Garmin Connect Client get user data")
    quit()


"""
Get devices
"""
print("client.get_devices()")
print("----------------------------------------------------------------------------------------")
try:
    devices = client.get_devices()
    print(devices)
except (
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
) as err:
    print("Error occurred during Garmin Connect Client get devices: %s" % err)
    quit()
except Exception:  # pylint: disable=broad-except
    print("Unknown error occurred during Garmin Connect Client get devices")
    quit()


"""
Get device settings
"""
try:
    for device in devices:
        device_id = device["deviceId"]
        print("client.get_device_settings(%s)", device_id)
        print("----------------------------------------------------------------------------------------")

        print(client.get_device_settings(device_id))
except (
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
) as err:
    print("Error occurred during Garmin Connect Client get device settings: %s" % err)
    quit()
except Exception:  # pylint: disable=broad-except
    print("Unknown error occurred during Garmin Connect Client get device settings")
    quit()
