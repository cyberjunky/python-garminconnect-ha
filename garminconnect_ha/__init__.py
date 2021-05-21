"""Garmin Connect Python 3 API wrapper for Home Assistant."""
import logging
import re

import requests

URL_BASE = "https://connect.garmin.com/modern/"
URL_BASE_PROXY = "https://connect.garmin.com/proxy/"
URL_LOGIN = "https://sso.garmin.com/sso/login"


class Garmin:
    """Garmin Connect's API wrapper."""

    def __init__(self, email, password):
        """Initialize module."""

        self._session = None
        self._email = email
        self._password = password
        self._username = None
        self._display_name = None
        self._logger = logging.getLogger(__name__)

    def login(self):
        """Return a requests session, loaded with precious cookies."""

        self._logger.debug("Login started")

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/50.0"
        }

        # Define a valid user agent
        self._session = requests.Session()
        self._session.headers.update(headers)

        # Request sso hostname
        sso_hostname = (
            self._fetch_data(URL_BASE + "auth/hostname", headers=headers)
            .json()
            .get("host")
        )

        self._logger.debug("Login ticket")

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

        response = self._fetch_data(URL_LOGIN, headers=headers, params=params)

        self._logger.debug("CSRF token")
        # Lookup for csrf token
        csrf = re.search(
            r'<input type="hidden" name="_csrf" value="(\w+)" />',
            response.content.decode("utf-8"),
        )
        if csrf is None:
            raise Exception("No CSRF token found")
        csrf_token = csrf.group(1)

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

        self._logger.debug("Login using ticket")
        response = self._fetch_data(
            URL_LOGIN, headers=headers, params=params, data=data
        )

        # Check we have sso guid in cookies
        if "GARMIN-SSO-GUID" not in self._session.cookies:
            raise GarminConnectAuthenticationError("Authentication error")

        # Needs a service ticket from previous response
        headers = {
            "Host": "connect.garmin.com",
        }

        self._logger.debug("Service ticket")

        try:
            response = self._session.get(url=URL_BASE, params=params, headers=headers)
            response.raise_for_status()

        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError(
                    "Too many requests in service ticket"
                ) from err

            if not response.history:
                raise GarminConnectConnectionError(
                    "Error connecting in service ticket status code %s"
                    % response.status_code
                ) from err

        self._logger.debug("Get user infomation")

        response = self._fetch_data(URL_BASE + "currentuser-service/user/info")

        self._display_name = response.json().get("displayName")
        self._username = response.json().get("username")
        self._logger.debug("Logged in with %s", self._username)

        return self._username

    def _fetch_data(self, url, headers=None, params=None, data=None):
        """Fetch and return received data."""

        self._logger.debug("Fetch data from URL: %s", url)

        try:
            if data:
                response = self._session.post(
                    url, headers=headers, params=params, data=data
                )
            else:
                response = self._session.get(url, headers=headers, params=params)
            self._logger.debug(
                "Fetch received status code %s in fetch_data", response.status_code
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError(
                    "Too many requests in fetch_data"
                ) from err

            self._logger.debug(
                "Session expired in fetch_data trying login",
            )
            self.login()

            try:
                if data:
                    response = self._session.post(
                        url, headers=headers, params=params, data=data
                    )
                else:
                    response = self._session.get(url, headers=headers, params=params)
                self._logger.debug(
                    "Fetch received status code %s in fetch_data relogin",
                    response.status_code,
                )
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                if response.status_code == 429:
                    raise GarminConnectTooManyRequestsError(
                        "Too many requests in fetch_data 2nd"
                    ) from err

                raise GarminConnectConnectionError(
                    "Error connecting status %s in fetch_data relogin"
                    + response.status_code
                ) from err

        # self._logger.debug("Fetch received reponse: %s", response.text)

        return response

    def get_devices(self):
        """Return available devices for the current user account."""

        return self._fetch_data(
            URL_BASE_PROXY + "device-service/deviceregistration/devices"
        ).json()

    def get_device_settings(self, device_id):
        """Return device settings for specific device."""

        return self._fetch_data(
            URL_BASE_PROXY
            + "device-service/deviceservice/device-info/settings/"
            + str(device_id)
        ).json()

    def _get_user_summary(self, cdate):
        """Return user activity summary for 'cDate' format 'YYYY-mm-dd'."""

        url = (
            URL_BASE_PROXY
            + "usersummary-service/usersummary/daily/"
            + self._display_name
            + "?"
            + "calendarDate="
            + cdate
        )

        response_json = self._fetch_data(url).json()

        if response_json["privacyProtected"] is True:
            self._logger.debug("Session expired - trying relogin")
            self.login()

            response_json = self._fetch_data(url).json()

        return response_json

    def _get_body_composition(self, cdate):
        """Return available body composition data for 'cDate' format 'YYYY-mm-dd'."""
        url = (
            URL_BASE_PROXY
            + "weight-service/weight/daterangesnapshot"
            + "?startDate="
            + cdate
            + "&endDate="
            + cdate
        )

        return self._fetch_data(url).json()

    def get_user_data(self, cdate):
        """Return user activity and body composition data for 'cDate' format 'YYYY-mm-dd'."""
        return {
            **self._get_user_summary(cdate),
            **self._get_body_composition(cdate)["totalAverage"],
        }


class GarminConnectConnectionError(Exception):
    """Raised when communication ended in error."""


class GarminConnectTooManyRequestsError(Exception):
    """Raised when rate limit is exceeded."""


class GarminConnectAuthenticationError(Exception):
    """Raised when authentication is failed."""
