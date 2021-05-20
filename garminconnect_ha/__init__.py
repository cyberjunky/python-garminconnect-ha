# -*- coding: utf-8 -*-
"""Minimal Garmin Connect Python 3 API wrapper for Home Assistant."""
import logging
import re

import requests

URL_HOSTNAME = "https://connect.garmin.com/modern/auth/hostname"
URL_LOGIN = "https://sso.garmin.com/sso/login"
URL_POST_LOGIN = "https://connect.garmin.com/modern/"
URL_USER_PROFILE = "https://connect.garmin.com/modern/currentuser-service/user/info"
URL_DEVICE_LIST = (
    "https://connect.garmin.com/proxy/device-service/deviceregistration/devices"
)
URL_DEVICE_SETTINGS = "https://connect.garmin.com/proxy/device-service/deviceservice/device-info/settings/"
URL_USER_SUMMARY = (
    "https://connect.garmin.com/proxy/usersummary-service/usersummary/daily/"
)
URL_BODY_COMPOSITION = (
    "https://connect.garmin.com/proxy/weight-service/weight/daterangesnapshot"
)


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

        # Define a valid user agent
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/50.0",
            }
        )

        # Request sso hostname
        sso_hostname = None
        try:
            response = session.get(URL_HOSTNAME)
            response.raise_for_status()

        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests #1") from err

            raise GarminConnectConnectionError("Error connecting #1") from err

        sso_hostname = response.json().get("host")

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
        try:
            response = session.get(URL_LOGIN, params=params)
            response.raise_for_status()

        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests #2") from err

            raise GarminConnectConnectionError("Error connecting #2 status %s", response.status_code) from err

        # Lookup for csrf token
        csrf = re.search(
            r'<input type="hidden" name="_csrf" value="(\w+)" />',
            response.content.decode("utf-8"),
        )
        if csrf is None:
            raise Exception("No CSRF token")
        csrf_token = csrf.group(1)
        self._logger.debug("Found CSRF token %s", csrf_token)

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
        try:
            response = session.post(
                URL_LOGIN, params=params, data=data, headers=headers
            )
            response.raise_for_status()

        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests #3") from err

            raise GarminConnectConnectionError("Error connecting #3 status %s ", response.status_code) from err

        # Check we have sso guid in cookies
        if "GARMIN-SSO-GUID" not in session.cookies:
            raise GarminConnectAuthenticationError("Authentication error #4")

        # Needs a service ticket from previous response
        headers = {
            "Host": "connect.garmin.com",
        }

        try:
            response = session.get(URL_POST_LOGIN, params=params, headers=headers)
            response.raise_for_status()

        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests #5") from err

            if not response.history:
                raise GarminConnectConnectionError("Error connecting #5 status %s ", response.status_code) from err

        # Check login
        try:
            response = session.get(URL_USER_PROFILE)
            response.raise_for_status()

        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests #6") from err

            raise GarminConnectConnectionError("Error connecting #6 status %s ", response.status_code) from err

        self._session = session
        self._display_name = response.json().get("displayName")
        self._username = response.json().get("username")
        self._logger.debug("Logged in with %s", self._username)

        return self._username

    def _fetch_data(self, url):
        """Fetch and return received data."""

        self._logger.debug("Fetching data with URL: %s", url)

        try:
            response = self._session.get(url, headers={"NK": "NT"})
            self._logger.debug("Fetch response code %s", response.status_code)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests #7") from err

            self.login()

            try:
                response = self._session.get(url, headers={"NK": "NT"})
                self._logger.debug("Fetch response code %s", response.status_code)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                if response.status_code == 429:
                    raise GarminConnectTooManyRequestsError(
                        "Too many requests #8"
                    ) from err

                raise GarminConnectConnectionError("Error connecting #8 status " + response.status_code) from err

        response_json = response.json()
        self._logger.debug("Fetch response json %s", response_json)

        return response_json

    def get_devices(self):
        """Return available devices for the current user account."""

        return self._fetch_data(URL_DEVICE_LIST)

    def get_device_settings(self, device_id):
        """Return device settings for specific device."""

        return self._fetch_data(URL_DEVICE_SETTINGS + device_id)

    def _get_user_statistics(self, cdate):  # cDate = 'YYY-mm-dd'
        """Return user activity data for 'cDate'."""

        statisticsurl = (
            URL_USER_SUMMARY + self._display_name + "?" + "calendarDate=" + cdate
        )

        try:
            response = self._session.get(statisticsurl)
            response.raise_for_status()

        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests #9") from err
            raise GarminConnectConnectionError("Error connecting #9 status " + response.status_code) from err

        response_json = response.json()

        if response_json["privacyProtected"] is True:
            self._logger.debug("Session expired - trying relogin")
            self.login()

            try:
                response = self._session.get(statisticsurl)
                response.raise_for_status()

            except requests.exceptions.HTTPError as err:
                if response.status_code == 429:
                    raise GarminConnectTooManyRequestsError(
                        "Too many requests #10"
                    ) from err
                raise GarminConnectConnectionError("Error connecting") from err
            else:
                response_json = response.json()

        return response_json

    def _get_body_composition(self, cdate):  # cDate = 'YYYY-mm-dd'
        """Return available body composition data for 'cDate'."""
        bodycompositionurl = (
            URL_BODY_COMPOSITION + "?startDate=" + cdate + "&endDate=" + cdate
        )

        return self._fetch_data(bodycompositionurl)

    def get_user_data(self, cdate):  # cDate = 'YYYY-mm-dd'
        """Return user activity and body composition data for 'cDate'."""
        return {
            **self._get_user_statistics(cdate),
            **self._get_body_composition(cdate)["totalAverage"],
        }


class GarminConnectConnectionError(Exception):
    """Raised when communication ended in error."""


class GarminConnectTooManyRequestsError(Exception):
    """Raised when rate limit is exceeded."""


class GarminConnectAuthenticationError(Exception):
    """Raised when authentication is failed."""
