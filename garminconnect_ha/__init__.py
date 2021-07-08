"""Garmin Connect Python 3 API wrapper for Home Assistant."""
import json
import logging
import re
from typing import Any, Dict

import cloudscraper
import requests

logger = logging.getLogger(__name__)

URL_BASE = "https://connect.garmin.com"
URL_BASE_PROXY = "https://connect.garmin.com/proxy/"
URL_SSO = "https://sso.garmin.com/sso"
URL_SIGNIN = "https://sso.garmin.com/sso/signin"


def check_response(resp: requests.Response) -> None:
    """Check the response and throw the appropriate exception if needed."""

    logger.debug("Response status code: %s", resp.status_code)
    logger.debug("Response: %s", resp.text)

    if resp.status_code != 200:
        try:
            response = resp.json()
            error = response["message"]
        except Exception:
            error = None

        if resp.status_code == 401:
            raise GarminConnectAuthenticationError("Authentication error")

        if resp.status_code == 403:
            raise GarminConnectConnectionError("Connection error")

        if resp.status_code == 429:
            raise GarminConnectTooManyRequestsError("Too many requests")

        raise ApiException(f"Unknown API response [{resp.status_code}] - {error}")


def parse_json(html, key):
    """Find and return JSON data."""
    found = re.search(key + r" = JSON.parse\(\"(.*)\"\);", html, re.M)
    if found:
        text = found.group(1).replace('\\"', '"')
        return json.loads(text)
    return None


class Garmin:
    """Garmin Connect main class."""

    def __init__(self, email, password):
        """Init Garmin class."""
        self._email = email
        self._password = password

        self._cf_req = cloudscraper.CloudScraper()
        self._req = requests.session()
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
            "origin": "https://sso.garmin.com",
        }
        self._display_name = None

    def login(self):
        """Login to portal using user credentials."""
        params = {
            "webhost": URL_BASE,
            "service": URL_BASE,
            "source": URL_SIGNIN,
            "redirectAfterAccountLoginUrl": URL_BASE,
            "redirectAfterAccountCreationUrl": URL_BASE,
            "gauthHost": URL_SSO,
            "locale": "en_US",
            "id": "gauth-widget",
            "cssUrl": "https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css",
            "clientId": "GarminConnect",
            "rememberMeShown": "true",
            "rememberMeChecked": "false",
            "createAccountShown": "true",
            "openCreateAccount": "false",
            "usernameShown": "false",
            "displayNameShown": "false",
            "consumeServiceTicket": "false",
            "initialFocus": "true",
            "embedWidget": "false",
            "generateExtraServiceTicket": "false",
        }

        data = {
            "username": self._email,
            "password": self._password,
            "embed": "true",
            "lt": "e1s1",
            "_eventId": "submit",
            "displayNameRequired": "false",
        }

        logger.debug("Login to Garmin Connect with GET URL: %s", URL_SIGNIN)
        response = self._cf_req.get(URL_SIGNIN, headers=self._headers, params=params)
        check_response(response)

        logger.debug("Login to Garmin Connect with POST URL: %s", URL_SIGNIN)
        response = self._cf_req.post(
            URL_SIGNIN, headers=self._headers, params=params, data=data
        )
        check_response(response)

        self._req.cookies = self._cf_req.cookies

        response_url = re.search(r'"(https:[^"]+?ticket=[^"]+)"', response.text)

        if not response_url:
            raise GarminConnectAuthenticationError("Authentication error")

        response_url = re.sub(r"\\", "", response_url.group(1))

        logger.debug("Fetching profile info using found response URL: %s", response_url)
        response = self._req.get(response_url)
        check_response(response)

        social_profile = parse_json(response.text, "VIEWER_SOCIAL_PROFILE")

        logger.debug("Social Profile: %s", social_profile)
        self._display_name = social_profile["displayName"]
        user_name = social_profile["userName"]

        logger.debug("Display name: %s", self._display_name)
        logger.debug("Username: %s", user_name)

        return user_name

    def _get_data(self, url):
        """Fetch and return API data."""
        response = self._req.get(url, headers=self._headers)
        check_response(response)

        return response

    def get_devices(self) -> Dict[str, Any]:
        """Return available devices for the current user account."""

        url = URL_BASE_PROXY + "device-service/deviceregistration/devices"
        logger.debug("Requesting devices with URL: %s", url)

        return self._get_data(url).json()

    def get_device_settings(self, device_id: str) -> Dict[str, Any]:
        """Return device settings for device with 'device_id'."""

        url = (
            URL_BASE_PROXY
            + "device-service/deviceservice/device-info/settings/"
            + str(device_id)
        )
        logger.debug("Requesting device settings with URL: %s", url)

        return self._get_data(url).json()

    def get_user_summary(self, cdate: str) -> Dict[str, Any]:
        """Return user activity summary for 'cdate' format 'YYYY-mm-dd'."""

        url = (
            URL_BASE_PROXY
            + "usersummary-service/usersummary/daily/"
            + self._display_name
            + "?"
            + "calendarDate="
            + cdate
        )

        logger.debug("Requesting user summary with URL: %s", url)
        response = self._get_data(url).json()

        if response["privacyProtected"] is True:
            raise GarminConnectAuthenticationError("Authentication error")

        return response

    def get_body_composition(self, cdate: str) -> Dict[str, Any]:
        """Return available body composition data for 'cdate' format 'YYYY-mm-dd'."""
        url = (
            URL_BASE_PROXY
            + "weight-service/weight/daterangesnapshot"
            + "?startDate="
            + cdate
            + "&endDate="
            + cdate
        )
        logger.debug("Requesting body composition with URL: %s", url)

        return self._get_data(url).json()

    def get_max_metrics(self, cdate: str) -> Dict[str, Any]:
        """Return available max metric data for 'cdate' format 'YYYY-mm-dd'."""
        url = URL_BASE_PROXY + "metrics-service/metrics/maxmet/latest/" + cdate
        logger.debug("Requestng max metrics with URL: %s", url)

        return self._get_data(url).json()

    def get_hydration(self, cdate: str) -> Dict[str, Any]:
        """Return available hydration data 'cdate' format 'YYYY-mm-dd'."""
        url = (
            URL_BASE_PROXY + "usersummary-service/usersummary/hydration/daily/" + cdate
        )
        logger.debug("Requesting hydration data with URL: %s", url)

        return self._get_data(url).json()

    def get_personal_records(self) -> Dict[str, Any]:
        """Return personal records for current user."""
        url = (
            URL_BASE_PROXY
            + "personalrecord-service/personalrecord/prs/"
            + self._display_name
        )
        logger.debug("Requesting personal records for user")

        return self._get_data(url).json()

    def get_device_alarms(self) -> Dict[str, Any]:
        """Combine the list of active alarms from all garmin devices."""

        logger.debug("Requesting device alarms")

        alarms = []
        devices = self.get_devices()
        for device in devices:
            device_settings = self.get_device_settings(device["deviceId"])
            alarms += device_settings["alarms"]
        return alarms


class ApiException(Exception):
    """Exception for API calls."""

    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    def __str__(self):
        return f"API Error: {self.msg}"


class GarminConnectConnectionError(Exception):
    """Raised when communication ended in error."""


class GarminConnectTooManyRequestsError(Exception):
    """Raised when rate limit is exceeded."""


class GarminConnectAuthenticationError(Exception):
    """Raised when authentication is failed."""
