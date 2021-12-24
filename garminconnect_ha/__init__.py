# -*- coding: utf-8 -*-
"""Python 3 API wrapper for Garmin Connect to get your statistics."""
import json
import logging
import re
from typing import Any, Dict

import cloudscraper

logger = logging.getLogger(__file__)


class ApiClient:
    """Class for a single API endpoint."""

    default_headers = {
        'User-Agent'    : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:66.0) Gecko/20100101 Firefox/66.0'
    }

    def __init__(
        self,
        session,
        baseurl,
        headers=None,
        aditional_headers=None,
    ):
        """Return a new Client instance."""
        self.session = session
        self.baseurl = baseurl
        if headers:
            self.headers = headers
        else:
            self.headers = self.default_headers.copy()
        self.headers.update(aditional_headers)

    def url(self, addurl=None):
        """Return the url for the API endpoint."""

        path = f"https://{self.baseurl}"
        if addurl is not None:
            path += f"/{addurl}"

        return path

    def get(self, addurl, aditional_headers=None, params=None):
        """Make an API call using the GET method."""
        total_headers = self.headers.copy()
        if aditional_headers:
            total_headers.update(aditional_headers)
        url = self.url(addurl)
        try:
            response = self.session.get(url, headers=total_headers, params=params)
            response.raise_for_status()
            return response
        except Exception as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests") from err
            if response.status_code == 401:
                raise GarminConnectAuthenticationError("Authentication error") from err
            if response.status_code == 403:
                raise GarminConnectConnectionError("Forbidden url") from err
            if response.status_code == 500:
                raise GarminConnectConnectionError("Server error") from err
            if response.status_code == 404:
                raise GarminConnectConnectionError("Not found") from err
            try:
                resp = response.json()
                error = resp["message"].json()
            except AttributeError:
                error = "Unknown"

            raise GarminConnectConnectionError(
                f"Unknown error {response.status_code} - {error}"
            ) from err

    def post(self, addurl, aditional_headers, params, data):
        """Make an API call using the POST method."""
        total_headers = self.headers.copy()
        if aditional_headers:
            total_headers.update(aditional_headers)
        url = self.url(addurl)
        try:
            response = self.session.post(
                url, headers=total_headers, params=params, data=data
            )
            response.raise_for_status()
            return response
        except Exception as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests") from err
            if response.status_code == 401:
                raise GarminConnectAuthenticationError("Authentication error") from err
            if response.status_code == 403:
                raise GarminConnectConnectionError("Forbidden url") from err
            if response.status_code == 500:
                raise GarminConnectConnectionError("Server error") from err
            if response.status_code == 404:
                raise GarminConnectConnectionError("Not found") from err
            try:
                resp = response.json()
                error = resp["message"].json()
            except AttributeError:
                error = "Unknown"

            raise GarminConnectConnectionError(
                f"Unknown error {response.status_code} - {error}"
            ) from err


class Garmin:
    """Class for fetching data from Garmin Connect."""

    garmin_connect_base_url = "https://connect.garmin.com"
    garmin_connect_login_url = garmin_connect_base_url + "/en-US/signin"
    garmin_connect_css_url = "https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css"
    garmin_connect_sso_login = "signin"
    garmin_connect_devices_url = "proxy/device-service/deviceregistration/devices"
    garmin_connect_device_url = (
        "proxy/device-service/deviceservice/device-info/settings"
    )
    garmin_connect_weight_url = "proxy/weight-service/weight/dateRange"
    garmin_connect_daily_summary_url = "proxy/usersummary-service/usersummary/daily"
    garmin_connect_metrics_url = "proxy/metrics-service/metrics/maxmet/latest"
    garmin_connect_daily_hydration_url = (
        "proxy/usersummary-service/usersummary/hydration/daily"
    )
    garmin_connect_personal_record_url = (
        "proxy/personalrecord-service/personalrecord/prs"
    )
    garmin_connect_sleep_daily_url = "proxy/wellness-service/wellness/dailySleepData"
    garmin_connect_rhr = "proxy/userstats-service/wellness/daily"

    garmin_headers = {"NK": "NT"}

    def __init__(self, email, password):
        """Create a new class instance."""
        self.username = email
        self.password = password
        self.session = cloudscraper.CloudScraper()
        self.sso_rest_client = ApiClient(
            self.session, "sso.garmin.com/sso", aditional_headers=self.garmin_headers
        )
        self.modern_rest_client = ApiClient(
            self.session,
            "connect.garmin.com/modern",
            aditional_headers=self.garmin_headers,
        )

        self.display_name = None

    @staticmethod
    def __get_json(page_html, key):
        found = re.search(key + r" = (\{.*\});", page_html, re.M)
        if found:
            json_text = found.group(1).replace('\\"', '"')
            return json.loads(json_text)

        return None

    def login(self):
        """Login to Garmin Connect."""

        logger.debug("login: %s %s", self.username, self.password)
        get_headers = {"Referer": self.garmin_connect_login_url}
        params = {
            "service": self.modern_rest_client.url(),
            "webhost": self.garmin_connect_base_url,
            "source": self.garmin_connect_login_url,
            "redirectAfterAccountLoginUrl": self.modern_rest_client.url(),
            "redirectAfterAccountCreationUrl": self.modern_rest_client.url(),
            "gauthHost": self.sso_rest_client.url(),
            "locale": "en_US",
            "id": "gauth-widget",
            "cssUrl": self.garmin_connect_css_url,
            "privacyStatementUrl": "//connect.garmin.com/en-US/privacy/",
            "clientId": "GarminConnect",
            "rememberMeShown": "true",
            "rememberMeChecked": "false",
            "createAccountShown": "true",
            "openCreateAccount": "false",
            "displayNameShown": "false",
            "consumeServiceTicket": "false",
            "initialFocus": "true",
            "embedWidget": "false",
            "generateExtraServiceTicket": "true",
            "generateTwoExtraServiceTickets": "false",
            "generateNoServiceTicket": "false",
            "globalOptInShown": "true",
            "globalOptInChecked": "false",
            "mobile": "false",
            "connectLegalTerms": "true",
            "locationPromptShown": "true",
            "showPassword": "true",
        }

        response = self.sso_rest_client.get(
            self.garmin_connect_sso_login, get_headers, params
        )

        found = re.search(r"name=\"_csrf\" value=\"(\w*)", response.text, re.M)
        if not found:
            logger.error("_csrf not found: %s", response.status_code)
            return False
        logger.debug("_csrf found (%s).", found.group(1))

        data = {
            "username": self.username,
            "password": self.password,
            "embed": "false",
            "_csrf": found.group(1),
        }
        post_headers = {
            "Referer": response.url,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = self.sso_rest_client.post(
            self.garmin_connect_sso_login, post_headers, params, data
        )

        found = re.search(r"\?ticket=([\w-]*)", response.text, re.M)
        if not found:
            logger.error("Login ticket not found (%d).", response.status_code)
            return False
        params = {"ticket": found.group(1)}

        response = self.modern_rest_client.get("", params=params)

        user_prefs = self.__get_json(response.text, "VIEWER_USERPREFERENCES")
        self.display_name = user_prefs["displayName"]

        logger.debug("Display name is %s", self.display_name)

        return True

    def get_user_summary(self, cdate: str) -> Dict[str, Any]:
        """Return user activity summary for 'cdate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_daily_summary_url}/{self.display_name}"
        params = {
            "calendarDate": str(cdate),
        }
        logger.debug("Requesting user summary with URL: %s", url)

        response = self.modern_rest_client.get(url, params=params).json()

        if response["privacyProtected"] is True:
            raise GarminConnectAuthenticationError("Authentication error")

        return response

    def get_body_composition(self, cdate: str) -> Dict[str, Any]:
        """Return available body composition data for 'cdate' format 'YYYY-mm-dd'."""

        url = self.garmin_connect_weight_url
        params = {"startDate": str(cdate), "endDate": str(cdate)}
        logger.debug("Requesting body composition with URL: %s", url)

        return self.modern_rest_client.get(url, params=params).json()

    def get_max_metrics(self, cdate: str) -> Dict[str, Any]:
        """Return available max metric data for 'cdate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_metrics_url}/{cdate}"
        logger.debug("Requestng max metrics with URL: %s", url)

        return self.modern_rest_client.get(url).json()

    def get_hydration(self, cdate: str) -> Dict[str, Any]:
        """Return available hydration data 'cdate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_daily_hydration_url}/{cdate}"
        logger.debug("Requesting hydration data with URL: %s", url)

        return self.modern_rest_client.get(url).json()

    def get_personal_records(self) -> Dict[str, Any]:
        """Return personal records for current user."""

        url = f"{self.garmin_connect_personal_record_url}/{self.display_name}"
        logger.debug("Requesting personal records for user with URL: %s", url)

        return self.modern_rest_client.get(url).json()

    def get_sleep_day(self, cdate: str) -> Dict[str, Any]:
        """Return sleep data for current user."""

        params = {"date": str(cdate), "nonSleepBufferMinutes": 60}

        url = f"{self.garmin_connect_sleep_daily_url}/{self.display_name}"

        return self.modern_rest_client.get(url, params=params).json()

    def get_rhr_day(self, cdate: str) -> Dict[str, Any]:
        """Return resting heartrate data for current user."""

        params = {"fromDate": str(cdate), "untilDate": str(cdate), "metricId": 60}
        url = f"{self.garmin_connect_rhr}/{self.display_name}"

        return self.modern_rest_client.get(url, params=params).json()

    def get_devices(self) -> Dict[str, Any]:
        """Return available devices for the current user account."""

        url = self.garmin_connect_devices_url
        logger.debug("Requesting devices with URL: %s", url)

        return self.modern_rest_client.get(url).json()

    def get_device_settings(self, device_id: str) -> Dict[str, Any]:
        """Return device settings for device with 'device_id'."""

        url = f"{self.garmin_connect_device_url}/{device_id}"
        logger.debug("Requesting device settings with URL: %s", url)

        return self.modern_rest_client.get(url).json()

    def get_device_alarms(self) -> Dict[str, Any]:
        """Get list of active alarms from all devices."""

        logger.debug("Requesting device alarms")

        alarms = []
        devices = self.get_devices()
        for device in devices:
            device_settings = self.get_device_settings(device["deviceId"])
            alarms += device_settings["alarms"]
        return alarms


class GarminConnectConnectionError(Exception):
    """Raised when communication ended in error."""


class GarminConnectTooManyRequestsError(Exception):
    """Raised when rate limit is exceeded."""


class GarminConnectAuthenticationError(Exception):
    """Raised when authentication is failed."""
