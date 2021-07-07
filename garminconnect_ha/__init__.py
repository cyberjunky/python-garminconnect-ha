"""Garmin Connect Python 3 API wrapper for Home Assistant."""
import logging
import re
from typing import Any, Dict

import cloudscraper
import requests

logger = logging.getLogger(__name__)

URL_BASE = "https://connect.garmin.com/modern/"
URL_BASE_PROXY = "https://connect.garmin.com/proxy/"
URL_LOGIN = "https://sso.garmin.com/sso/login"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64;"
    " rv:48.0) Gecko/20100101 Firefox/50.0"
}


def _check_response(resp: requests.Response) -> None:
    """Check the response and throw the appropriate exception if needed."""

    logger.debug("Checking status code: %s", resp.status_code)

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


class Garmin:
    """Garmin Connect's API wrapper."""

    def __init__(self, email: str, password: str):
        """Garmin Connect's API wrapper."""
        self._session = cloudscraper.CloudScraper()
        self._session.headers.update(HEADERS)
        self._email = email
        self._password = password
        self._username = None
        self._display_name = None

    def _get_data(
        self, url: str, headers: dict = None, params: dict = None, data: dict = None
    ) -> Dict[str, Any]:
        """Get and return requests data, relogin if needed."""

        logger.debug("Fetch data with URL: %s", url)

        try:
            if data:
                response = self._session.post(
                    url, headers=headers, params=params, data=data
                )
            else:
                response = self._session.get(url, headers=headers, params=params)

            _check_response(response)
        except (
            GarminConnectConnectionError,
            GarminConnectAuthenticationError,
        ):
            logger.debug("Session expired, trying re-login")
            self.login()

            if data:
                response = self._session.post(
                    url, headers=headers, params=params, data=data
                )
            else:
                response = self._session.get(url, headers=headers, params=params)
            _check_response(response)

        logger.debug("Response: %s", response.content)
        return response

    def login(self) -> Dict[str, Any]:
        """Return a requests session, loaded with precious cookies."""

        logger.debug("Login started")

        url = URL_BASE + "auth/hostname"
        logger.debug("Requesting sso hostname with url: %s", url)

        # Request sso hostname
        sso_hostname = self._get_data(url).json().get("host")

        logger.debug("Requesting login token with url: %s", URL_LOGIN)

        # Load login page to get login ticket
        params = [
            ("service", "https://connect.garmin.com/modern/"),
            ("webhost", "https://connect.garmin.com/modern/"),
            ("source", "https://connect.garmin.com/signin/"),
            ("redirectAfterAccountLoginUrl", "https://connect.garmin.com/modern/"),
            ("redirectAfterAccountCreationUrl", "https://connect.garmin.com/modern/"),
            ("gauthHost", sso_hostname),
            ("locale", "fr_FR"),
            ("id", "gauth-widget"),
            ("cssUrl", "https://connect.garmin.com/gauth-custom-v3.2-min.css"),
            ("privacyStatementUrl", "https://www.garmin.com/fr-FR/privacy/connect/"),
            ("clientId", "GarminConnect"),
            ("rememberMeShown", "true"),
            ("rememberMeChecked", "false"),
            ("createAccountShown", "true"),
            ("openCreateAccount", "false"),
            ("displayNameShown", "false"),
            ("consumeServiceTicket", "false"),
            ("initialFocus", "true"),
            ("embedWidget", "false"),
            ("generateExtraServiceTicket", "true"),
            ("generateTwoExtraServiceTickets", "true"),
            ("generateNoServiceTicket", "false"),
            ("globalOptInShown", "true"),
            ("globalOptInChecked", "false"),
            ("mobile", "false"),
            ("connectLegalTerms", "true"),
            ("showTermsOfUse", "false"),
            ("showPrivacyPolicy", "false"),
            ("showConnectLegalAge", "false"),
            ("locationPromptShown", "true"),
            ("showPassword", "true"),
            ("useCustomHeader", "false"),
            ("mfaRequired", "false"),
            ("performMFACheck", "false"),
            ("rememberMyBrowserShown", "false"),
            ("rememberMyBrowserChecked", "false"),
        ]

        response = self._get_data(URL_LOGIN, params=params)

        # Lookup for csrf token
        csrf = re.search(
            r'<input type="hidden" name="_csrf" value="(\w+)" />',
            response.content.decode("utf-8"),
        )
        if csrf is None:
            raise Exception("No CSRF token found")
        csrf_token = csrf.group(1)

        logger.debug("Got CSRF token: %s", csrf_token)
        logger.debug("Referer: %s", response.url)

        # Login/password with login ticket
        data = {
            "embed": "false",
            "username": self._email,
            "password": self._password,
            "_csrf": csrf_token,
        }

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fr,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://sso.garmin.com",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": response.url,
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "iframe",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "TE": "Trailers",
        }

        logger.debug("Login using ticket")
        response = self._get_data(URL_LOGIN, headers=headers, params=params, data=data)

        # Check we have sso guid in cookies
        if "GARMIN-SSO-GUID" not in self._session.cookies:
            raise GarminConnectAuthenticationError("Authentication error")

        # We need a service ticket from previous response
        headers = {
            "Host": "connect.garmin.com",
        }

        logger.debug("Service ticket")

        try:
            response = self._session.get(url=URL_BASE, params=params, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests") from err

            if not response.history:
                GarminConnectAuthenticationError("Authentication error")

        logger.debug("Get user information")

        response = self._get_data(URL_BASE + "currentuser-service/user/info")

        self._display_name = response.json().get("displayName")
        self._username = response.json().get("username")
        logger.debug("Logged in with %s", self._username)

        return self._username

    def get_devices(self) -> Dict[str, Any]:
        """Return available devices for the current user account."""

        url = URL_BASE_PROXY + "device-service/deviceregistration/devices"
        logger.debug("Requesting devices with url: %s", url)

        return self._get_data(url).json()

    def get_device_settings(self, device_id: str) -> Dict[str, Any]:
        """Return device settings for specific device."""

        url = (
            URL_BASE_PROXY
            + "device-service/deviceservice/device-info/settings/"
            + str(device_id)
        )
        logger.debug("Requesting device settings with url: %s", url)

        return self._get_data(url).json()

    def get_user_summary(self, cdate: str) -> Dict[str, Any]:
        """Return user activity summary for 'cDate' format 'YYYY-mm-dd'."""

        url = (
            URL_BASE_PROXY
            + "usersummary-service/usersummary/daily/"
            + self._display_name
            + "?"
            + "calendarDate="
            + cdate
        )

        logger.debug("Requesting user summary with url: %s", url)
        response = self._get_data(url).json()

        if response["privacyProtected"] is True:
            logger.debug("Session expired - trying relogin")
            self.login()

        return self._get_data(url).json()

    def get_body_composition(self, cdate: str) -> Dict[str, Any]:
        """Return available body composition data for 'cDate' format 'YYYY-mm-dd'."""
        url = (
            URL_BASE_PROXY
            + "weight-service/weight/daterangesnapshot"
            + "?startDate="
            + cdate
            + "&endDate="
            + cdate
        )
        logger.debug("Requesting body composition with url: %s", url)

        return self._get_data(url).json()

    def get_device_alarms(self) -> Dict[str, Any]:
        """Combine the list of active alarms from all garmin devices."""

        logger.debug("Gathering device alarms")

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
