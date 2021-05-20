# -*- coding: utf-8 -*-
"""Minimal Garmin Connect Python 3 API wrapper for Home Assistant."""
import logging
import re

import requests

logger = logging.getLogger(__name__)

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
        self._common_headers = {"NK": "NT"}
        self._display_name = None
        self._email_address = None

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
        response = session.get(URL_HOSTNAME)
        if not response.ok:
            raise Exception(
                "Invalid SSO first request status code {}".format(response.status_code)
            )
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
        response = session.get(URL_LOGIN, params=params)
        if response.status_code != 200:
            raise Exception("No login form")

        # Lookup for csrf token
        csrf = re.search(
            r'<input type="hidden" name="_csrf" value="(\w+)" />',
            response.content.decode("utf-8"),
        )
        if csrf is None:
            raise Exception("No CSRF token")
        csrf_token = csrf.group(1)
        logger.debug("Found CSRF token %s", csrf_token)

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

        response = session.post(URL_LOGIN, params=params, data=data, headers=headers)

        # Too many requests made, blocked for 1 hour
        if not response.ok:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests")
            raise GarminConnectConnectionError("Authentication error")

        # Check we have sso guid in cookies
        if "GARMIN-SSO-GUID" not in session.cookies:
            raise GarminConnectAuthenticationError("Authentication error")

        # Needs a service ticket from previous response
        headers = {
            "Host": "connect.garmin.com",
        }
        response = session.get(URL_POST_LOGIN, params=params, headers=headers)
        if response.status_code != 200 and not response.history:
            raise GarminConnectAuthenticationError("Authentication error")

        # Check login
        response = session.get(URL_USER_PROFILE)
        if not response.ok:
            raise Exception("Login check failed.")

        garmin_user = response.json()

        self._session = session
        self._email_address = garmin_user["username"]
        self._display_name = garmin_user["displayName"]

        logger.debug("Logged in with %s", self._email_address)

        return garmin_user

    def _fetch_data(self, url):
        """Fetch and return received data."""

        logger.debug("Fetching data with URL: %s", url)

        try:
            response = self._session.get(url, headers=self._common_headers)
            logger.debug("Fetch response code %s", response.status_code)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests") from err

            logger.debug(
                "Exception occurred possibly session expired, retry to login: %s", err
            )
            self.login()

            try:
                response = self._session.get(url, headers=self._common_headers)
                logger.debug("Fetch response code %s", response.status_code)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                logger.debug(
                    "Exception occurred during data retrieval, relogin without effect: %s",
                    err,
                )
                if response.status_code == 429:
                    raise GarminConnectTooManyRequestsError(
                        "Too many requests"
                    ) from err

                raise GarminConnectConnectionError("Error connecting") from err

        response_json = response.json()
        logger.debug("Fetch response json %s", response_json)

        return response_json

    def get_email_address(self):
        """Return email address."""

        return self._email_address

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
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests")

            logger.debug("User statistics status code: %s", response.status_code)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise GarminConnectConnectionError("Error connecting") from err

        response_json = response.json()

        if response_json["privacyProtected"] is True:
            logger.debug("Session expired - trying relogin")
            self.login()
            try:
                response = self._session.get(statisticsurl)
                if response.status_code == 429:
                    raise GarminConnectTooManyRequestsError("Too many requests")

                logger.debug("User statistics status code %s", response.status_code)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                logger.debug(
                    "Exception occurred during, relogin without effect: %s", err
                )
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
