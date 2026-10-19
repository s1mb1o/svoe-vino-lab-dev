"""Yandex ID: OAuth 2.0 authorization code flow with PKCE.

Docs: https://yandex.ru/dev/id/doc/ru/codes/code-url and
https://yandex.ru/dev/id/doc/ru/user-information. The service keeps only the Yandex user ID.
It discards the access token after one request.
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from .config import YandexSettings

AUTHORIZE_URL = "https://oauth.yandex.ru/authorize"
TOKEN_URL = "https://oauth.yandex.ru/token"  # noqa: S105 - an endpoint, not a secret
USER_INFO_URL = "https://login.yandex.ru/info"
TIMEOUT = httpx.Timeout(5.0)


class ProviderUnavailable(Exception):
    """Yandex did not answer or answered with a server error."""


class ProviderRejected(Exception):
    """Yandex refused the code or the token."""


class YandexClient:
    def __init__(self, settings: YandexSettings, http: httpx.Client) -> None:
        self._settings = settings
        self._http = http

    def authorize_url(self, *, state: str, code_challenge: str, redirect_uri: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._settings.client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{AUTHORIZE_URL}?{query}"

    def user_id(self, *, code: str, code_verifier: str) -> str:
        return self.user(code=code, code_verifier=code_verifier)[0]

    def user(self, *, code: str, code_verifier: str) -> tuple[str, str | None]:
        """Return the Yandex user ID and the default email (None without the email permission)."""
        token = self._exchange(code, code_verifier)
        try:
            response = self._http.get(
                USER_INFO_URL,
                params={"format": "json"},
                headers={"Authorization": f"OAuth {token}"},
                timeout=TIMEOUT,
            )
        except httpx.HTTPError as error:
            raise ProviderUnavailable("user info request failed") from error
        if response.status_code >= 500:
            raise ProviderUnavailable(f"user info status {response.status_code}")
        if response.status_code != 200:
            raise ProviderRejected(f"user info status {response.status_code}")
        try:
            info = response.json()
            user_id = str(info["id"])
        except (ValueError, KeyError, TypeError) as error:
            raise ProviderRejected("user info has no id") from error
        if not user_id.isdigit():
            raise ProviderRejected("user info id is not numeric")
        email = info.get("default_email") if isinstance(info, dict) else None
        return user_id, email if isinstance(email, str) and email else None

    def _exchange(self, code: str, code_verifier: str) -> str:
        try:
            response = self._http.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "code_verifier": code_verifier,
                },
                auth=(self._settings.client_id, self._settings.client_secret),
                timeout=TIMEOUT,
            )
        except httpx.HTTPError as error:
            raise ProviderUnavailable("token request failed") from error
        if response.status_code >= 500:
            raise ProviderUnavailable(f"token status {response.status_code}")
        if response.status_code != 200:
            raise ProviderRejected(f"token status {response.status_code}")
        try:
            token = response.json()["access_token"]
        except (ValueError, KeyError, TypeError) as error:
            raise ProviderRejected("token response has no access_token") from error
        if not isinstance(token, str) or not token:
            raise ProviderRejected("token response has an empty access_token")
        return token
