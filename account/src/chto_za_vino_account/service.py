"""Account operations without HTTP: login, sign-up, sessions, linking, and deletion.

Login methods: an email code and Yandex ID (plans 04 and 05, issue #48). MAX and Telegram
are linked identities. A MAX launch can open a session only when MAX_LOGIN_ENABLED is true
(issue #50 decides this).
"""

from __future__ import annotations

import ipaddress
import logging
import re
import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from . import max_launch
from .config import Settings
from .db import Database
from .limits import SlidingWindow, take_all
from .mailer import Dispatcher, code_mail
from .tokens import code_mac, equal, new_email_code, new_token, pkce_pair, token_hash
from .yandex import ProviderRejected, ProviderUnavailable, YandexClient

LOG = logging.getLogger("chto_za_vino_account")

EMAIL_CODE_TTL = 600
EMAIL_MAX_ATTEMPTS = 5
OAUTH_FLOW_TTL = 600
SIGNUP_TTL = 1800
LINK_CODE_TTL = 600
# Sessions do not expire (owner, 2026-10-19): a session ends at logout or account deletion.
SESSION_TTL = 100 * 365 * 86400
MAX_SESSION_TTL = 86400
SESSION_EXTEND_AFTER = 86400
# Application tokens for MCP clients (issue #65): `cvpat_` and 32 random bytes in base64url.
APP_TOKEN_PATTERN = re.compile(r"cvpat_[A-Za-z0-9_-]{43}")
APP_TOKEN_ID = re.compile(r"[0-9a-f]{16}")
APP_TOKEN_LIFETIMES = (30, 90, 365)
APP_TOKENS_PER_USER = 5
APP_TOKEN_USE_INTERVAL = 60
APP_TOKEN_KEEP_AFTER_END = 30 * 86400
MAX_OPEN_FLOWS = 10_000
LAUNCH_CLOCK_SKEW = 60

# An account keeps at least one of these. MAX login (MAX_LOGIN_ENABLED) does not count.
LOGIN_METHODS = frozenset({"email", "yandex"})

EMAIL_RE = re.compile(r"[^@\s]{1,64}@[^@\s]+\.[^@\s]+")
USERNAME_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{1,30}[a-z0-9]")
RESERVED_USERNAMES = frozenset(
    {
        "admin", "administrator", "root", "support", "help", "system", "account", "accounts",
        "api", "max", "telegram", "yandex", "chtozavino", "moderator", "null", "undefined", "me",
    }
)


class AccountError(Exception):
    def __init__(
        self,
        code: str,
        status: int = 400,
        detail: str = "",
        *,
        retry_after: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.detail = detail
        self.retry_after = retry_after
        self.extra = extra or {}


@dataclass(frozen=True)
class Session:
    user_id: str
    auth_method: str
    auth_at: int
    expires_at: int


@dataclass(frozen=True)
class SessionIssued:
    token: str = field(repr=False)
    expires_at: int
    auth_method: str
    user_id: str


@dataclass(frozen=True)
class SignupRequired:
    ticket: str = field(repr=False)
    provider: str
    email: str | None = field(repr=False)


@dataclass(frozen=True)
class Linked:
    user_id: str


AuthResult = SessionIssued | SignupRequired


def iso(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, UTC).isoformat().replace("+00:00", "Z")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise AccountError("invalid_email", detail="The email address is not valid")
    return email


def optional_email(value: str | None) -> str | None:
    """Normalize an email from a provider. An invalid or missing value gives None."""
    if value is None:
        return None
    try:
        return normalize_email(value)
    except AccountError:
        return None


def normalize_username(value: str) -> str:
    username = value.strip().lower()
    if not USERNAME_RE.fullmatch(username):
        raise AccountError(
            "invalid_username",
            detail="Use 3-32 characters: a-z, 0-9, '_', '.', '-'; start and end with a letter "
            "or digit",
        )
    if username in RESERVED_USERNAMES:
        raise AccountError("username_reserved", detail="This username is reserved")
    return username


def normalize_ip(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError as error:
        raise AccountError("client_ip_required", detail="X-Client-IP is not valid") from error


def client_key(ip: str) -> str:
    """The limit key of a client: the address, or its /64 network for IPv6."""
    address = ipaddress.ip_address(ip)
    if address.version == 6:
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)


class AccountService:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        dispatcher: Dispatcher,
        yandex: YandexClient | None,
        clock: Callable[[], float],
    ) -> None:
        self.settings = settings
        self.db = db
        self.dispatcher = dispatcher
        self.yandex = yandex
        self.clock = clock
        self.email_resend = SlidingWindow(1, 60, clock)
        self.email_hourly = SlidingWindow(3, 3600, clock)
        self.email_per_ip = SlidingWindow(20, 3600, clock)
        self.yandex_per_ip = SlidingWindow(30, 3600, clock)
        self.link_codes_per_user = SlidingWindow(10, 3600, clock)
        self.app_token_calls = SlidingWindow(60, 60, clock)
        self.app_token_failures = SlidingWindow(20, 60, clock)
        # A budget for all clients: rotating addresses cannot make unlimited failed lookups.
        self.app_token_failures_all = SlidingWindow(600, 60, clock)

    # ----------------------------------------------------------------- helpers

    def _now(self) -> int:
        return int(self.clock())

    def _create_session(
        self,
        db: sqlite3.Connection,
        user_id: str,
        auth_method: str,
        now: int,
        *,
        auth_at: int | None = None,
        ttl: int = SESSION_TTL,
    ) -> SessionIssued:
        token = new_token()
        expires_at = now + ttl
        db.execute(
            "INSERT INTO sessions (token_hash, user_id, auth_method, created_at, auth_at, "
            "expires_at, extended_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (token_hash(token), user_id, auth_method, now, auth_at or now, expires_at, now),
        )
        LOG.info("Session created (%s)", auth_method)
        return SessionIssued(token, expires_at, auth_method, user_id)

    def _login_or_signup(
        self,
        provider: str,
        subject: str,
        *,
        email: str | None = None,
        auth_at: int | None = None,
        ttl: int = SESSION_TTL,
    ) -> AuthResult:
        now = self._now()
        with self.db.transaction() as db:
            row = db.execute(
                "SELECT user_id FROM identities WHERE provider = ? AND subject = ?",
                (provider, subject),
            ).fetchone()
            if row is not None:
                if email is not None and provider != "email":
                    db.execute(
                        "UPDATE identities SET email = ? WHERE provider = ? AND subject = ?",
                        (email, provider, subject),
                    )
                return self._create_session(
                    db, row["user_id"], provider, now, auth_at=auth_at, ttl=ttl
                )
            owner = self._email_owner(db, email, provider)
            if owner is not None:
                db.execute(
                    "INSERT INTO identities (provider, subject, user_id, linked_at, email) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (provider, subject, owner, now, email),
                )
                LOG.info("Identity joined an account by email (%s)", provider)
                return self._create_session(db, owner, provider, now, auth_at=auth_at, ttl=ttl)
            ticket = new_token()
            db.execute(
                "INSERT INTO signup_tickets (token_hash, provider, subject, created_at, "
                "expires_at, email) VALUES (?, ?, ?, ?, ?, ?)",
                (token_hash(ticket), provider, subject, now, now + SIGNUP_TTL, email),
            )
        return SignupRequired(ticket, provider, subject if provider == "email" else None)

    @staticmethod
    def _email_owner(db: sqlite3.Connection, email: str | None, provider: str) -> str | None:
        """The one account with this email and no identity of this provider, or None.

        Two accounts with the same email (made before the join rule) are ambiguous: no join.
        """
        if email is None:
            return None
        owners = {
            row["user_id"]
            for row in db.execute("SELECT user_id FROM identities WHERE email = ?", (email,))
        }
        if len(owners) != 1:
            return None
        owner = owners.pop()
        taken = db.execute(
            "SELECT 1 FROM identities WHERE user_id = ? AND provider = ?", (owner, provider)
        ).fetchone()
        return None if taken is not None else owner

    @staticmethod
    def _link(
        db: sqlite3.Connection,
        user_id: str,
        provider: str,
        subject: str,
        now: int,
        *,
        replace: bool = False,
        email: str | None = None,
    ) -> None:
        owner = db.execute(
            "SELECT user_id FROM identities WHERE provider = ? AND subject = ?",
            (provider, subject),
        ).fetchone()
        if owner is not None:
            if owner["user_id"] == user_id:
                return
            raise AccountError("identity_in_use", 409, "This identity belongs to another account")
        mine = db.execute(
            "SELECT subject FROM identities WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        ).fetchone()
        if mine is not None:
            if not replace:
                raise AccountError(
                    "provider_already_linked", 409, f"Unlink the current {provider} first"
                )
            db.execute(
                "UPDATE identities SET subject = ?, linked_at = ?, email = ? "
                "WHERE user_id = ? AND provider = ?",
                (subject, now, email, user_id, provider),
            )
        else:
            db.execute(
                "INSERT INTO identities (provider, subject, user_id, linked_at, email) "
                "VALUES (?, ?, ?, ?, ?)",
                (provider, subject, user_id, now, email),
            )
        LOG.info("Identity linked (%s)", provider)

    # ------------------------------------------------------------------ views

    def provider_config(self) -> dict[str, Any]:
        settings = self.settings
        return {
            "providers": {
                "email": True,
                "yandex": settings.yandex is not None,
                "max_link": settings.max is not None,
                "max_login": settings.max is not None and settings.max.login_enabled,
                "telegram_link": bool(settings.telegram_bot_username),
            },
            "consent_version": settings.consent_version,
            "terms_version": settings.terms_version,
            "yandex_redirect_uris": list(settings.yandex.redirect_uris) if settings.yandex else [],
        }

    def user_view(self, user_id: str) -> dict[str, Any]:
        with self.db.transaction() as db:
            user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if user is None:
                raise AccountError("session_invalid", 401, "The account no longer exists")
            identities = db.execute(
                "SELECT provider, subject, linked_at FROM identities WHERE user_id = ? "
                "ORDER BY provider",
                (user_id,),
            ).fetchall()
        return {
            "id": user["id"],
            "username": user["username"],
            "created_at": iso(user["created_at"]),
            "identities": [
                {
                    "provider": item["provider"],
                    "linked_at": iso(item["linked_at"]),
                    **({"email": item["subject"]} if item["provider"] == "email" else {}),
                }
                for item in identities
            ],
        }

    # --------------------------------------------------------------- sessions

    def authenticate(self, token: str) -> Session | None:
        now = self._now()
        with self.db.transaction() as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE token_hash = ?", (token_hash(token),)
            ).fetchone()
            if row is None:
                return None
            if row["expires_at"] <= now:
                db.execute("DELETE FROM sessions WHERE token_hash = ?", (row["token_hash"],))
                return None
            expires_at = row["expires_at"]
            if row["auth_method"] != "max" and now - row["extended_at"] >= SESSION_EXTEND_AFTER:
                expires_at = now + SESSION_TTL
                db.execute(
                    "UPDATE sessions SET expires_at = ?, extended_at = ? WHERE token_hash = ?",
                    (expires_at, now, row["token_hash"]),
                )
        return Session(row["user_id"], row["auth_method"], row["auth_at"], expires_at)

    def logout(self, token: str) -> None:
        with self.db.transaction() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))

    # ------------------------------------------------------------------ email

    def email_start(
        self, email: str, purpose: str, client_ip: str, session: Session | None
    ) -> tuple[str, int]:
        email = normalize_email(email)
        if purpose == "link":
            if session is None:
                raise AccountError("session_required", 401, "Log in to link an email address")
        wait = take_all(
            (
                (self.email_resend, email),
                (self.email_hourly, email),
                (self.email_per_ip, client_ip),
            )
        )
        if wait:
            raise AccountError("rate_limited", 429, "Too many codes", retry_after=wait)
        challenge_id = new_token()
        code = new_email_code()
        now = self._now()
        with self.db.transaction() as db:
            db.execute(
                "INSERT INTO email_challenges (id_hash, email, code_mac, purpose, user_id, "
                "created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    token_hash(challenge_id),
                    email,
                    code_mac(self.settings.code_key, challenge_id, code),
                    purpose,
                    session.user_id if session else None,
                    now,
                    now + EMAIL_CODE_TTL,
                ),
            )
        self.dispatcher.submit(code_mail(email, code, purpose, self.settings.site_name))
        LOG.info("Email challenge created (%s)", purpose)
        return challenge_id, EMAIL_CODE_TTL

    def email_verify(
        self, challenge_id: str, code: str, session: Session | None
    ) -> AuthResult | Linked:
        now = self._now()
        error: AccountError | None = None
        with self.db.transaction() as db:
            row = db.execute(
                "SELECT * FROM email_challenges WHERE id_hash = ?", (token_hash(challenge_id),)
            ).fetchone()
            if row is None or row["used_at"] is not None or row["expires_at"] <= now:
                error = AccountError("invalid_challenge", 400, "Request a new code")
            elif row["attempts"] >= EMAIL_MAX_ATTEMPTS:
                error = AccountError("too_many_attempts", 429, "Request a new code")
            elif row["purpose"] == "link" and (
                session is None or session.user_id != row["user_id"]
            ):
                error = AccountError("invalid_challenge", 400, "Request a new code")
            elif not equal(row["code_mac"], code_mac(self.settings.code_key, challenge_id, code)):
                db.execute(
                    "UPDATE email_challenges SET attempts = attempts + 1 WHERE id_hash = ?",
                    (row["id_hash"],),
                )
                remaining = EMAIL_MAX_ATTEMPTS - row["attempts"] - 1
                error = AccountError(
                    "invalid_code", 400, "The code is wrong", extra={"attempts_left": remaining}
                )
            else:
                db.execute(
                    "UPDATE email_challenges SET used_at = ? WHERE id_hash = ?",
                    (now, row["id_hash"]),
                )
        if error is not None:
            raise error
        if row["purpose"] == "login":
            return self._login_or_signup("email", row["email"], email=row["email"])
        with self.db.transaction() as db:
            self._link(
                db, row["user_id"], "email", row["email"], now, replace=True, email=row["email"]
            )
        return Linked(row["user_id"])

    # ----------------------------------------------------------------- yandex

    def yandex_start(
        self, redirect_uri: str, purpose: str, client_ip: str, session: Session | None
    ) -> tuple[str, str, int]:
        if self.yandex is None or self.settings.yandex is None:
            raise AccountError("provider_disabled", 404, "Yandex ID is not configured")
        if redirect_uri not in self.settings.yandex.redirect_uris:
            raise AccountError("invalid_redirect_uri", 400, "The redirect URI is not registered")
        if purpose == "link":
            if session is None:
                raise AccountError("session_required", 401, "Log in to link Yandex ID")
        wait = take_all(((self.yandex_per_ip, client_ip),))
        if wait:
            raise AccountError("rate_limited", 429, "Too many login attempts", retry_after=wait)
        flow_id = new_token()
        state = new_token()
        verifier, challenge = pkce_pair()
        now = self._now()
        with self.db.transaction() as db:
            open_flows = db.execute(
                "SELECT COUNT(*) FROM oauth_flows WHERE used_at IS NULL AND expires_at > ?",
                (now,),
            ).fetchone()[0]
            if open_flows >= MAX_OPEN_FLOWS:
                raise AccountError("busy", 503, "Try again later", retry_after=60)
            db.execute(
                "INSERT INTO oauth_flows (id_hash, provider, state, code_verifier, redirect_uri, "
                "purpose, user_id, created_at, expires_at) "
                "VALUES (?, 'yandex', ?, ?, ?, ?, ?, ?, ?)",
                (
                    token_hash(flow_id),
                    state,
                    verifier,
                    redirect_uri,
                    purpose,
                    session.user_id if session else None,
                    now,
                    now + OAUTH_FLOW_TTL,
                ),
            )
        url = self.yandex.authorize_url(
            state=state, code_challenge=challenge, redirect_uri=redirect_uri
        )
        return url, flow_id, OAUTH_FLOW_TTL

    def yandex_finish(
        self, flow_id: str, state: str, code: str, session: Session | None
    ) -> AuthResult | Linked:
        if self.yandex is None:
            raise AccountError("provider_disabled", 404, "Yandex ID is not configured")
        now = self._now()
        error: AccountError | None = None
        with self.db.transaction() as db:
            row = db.execute(
                "SELECT * FROM oauth_flows WHERE id_hash = ?", (token_hash(flow_id),)
            ).fetchone()
            if row is None or row["used_at"] is not None or row["expires_at"] <= now:
                error = AccountError("invalid_flow", 400, "Start the Yandex login again")
            else:
                db.execute(
                    "UPDATE oauth_flows SET used_at = ? WHERE id_hash = ?", (now, row["id_hash"])
                )
                if not equal(row["state"], state):
                    error = AccountError("invalid_flow", 400, "Start the Yandex login again")
                elif row["purpose"] == "link" and (
                    session is None or session.user_id != row["user_id"]
                ):
                    error = AccountError("invalid_flow", 400, "Start the Yandex login again")
        if error is not None:
            raise error
        try:
            yandex_id, raw_email = self.yandex.user(code=code, code_verifier=row["code_verifier"])
        except ProviderUnavailable as failure:
            LOG.warning("Yandex ID unavailable: %s", failure)
            raise AccountError("provider_unavailable", 502, "Yandex ID did not answer") from None
        except ProviderRejected as failure:
            LOG.info("Yandex ID rejected the login: %s", failure)
            raise AccountError("provider_rejected", 400, "Yandex ID rejected the login") from None
        yandex_email = optional_email(raw_email)
        if row["purpose"] == "login":
            return self._login_or_signup("yandex", yandex_id, email=yandex_email)
        with self.db.transaction() as db:
            self._link(db, row["user_id"], "yandex", yandex_id, self._now(), email=yandex_email)
        return Linked(row["user_id"])

    # ---------------------------------------------------------------- sign-up

    def signup(
        self, ticket: str, username: str, consent_version: str, terms_version: str
    ) -> SessionIssued:
        username = normalize_username(username)
        if consent_version != self.settings.consent_version:
            raise AccountError("consent_outdated", 400, "Accept the current consent text")
        if terms_version != self.settings.terms_version:
            raise AccountError("terms_outdated", 400, "Accept the current terms of use")
        now = self._now()
        with self.db.transaction() as db:
            row = db.execute(
                "SELECT * FROM signup_tickets WHERE token_hash = ?", (token_hash(ticket),)
            ).fetchone()
            if row is None or row["used_at"] is not None or row["expires_at"] <= now:
                raise AccountError("invalid_ticket", 400, "Log in again to sign up")
            taken = db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
            if taken is not None:
                raise AccountError("username_taken", 409, "This username is taken")
            user_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO users (id, username, created_at, consent_version, consent_at, "
                "terms_version, terms_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, username, now, consent_version, now, terms_version, now),
            )
            self._link(db, user_id, row["provider"], row["subject"], now, email=row["email"])
            db.execute(
                "UPDATE signup_tickets SET used_at = ? WHERE token_hash = ?",
                (now, row["token_hash"]),
            )
            issued = self._create_session(db, user_id, row["provider"], now)
        LOG.info("Account created (%s)", row["provider"])
        return issued

    # ---------------------------------------------------------- account state

    def unlink(self, session: Session, provider: str) -> None:
        with self.db.transaction() as db:
            rows = db.execute(
                "SELECT provider FROM identities WHERE user_id = ?", (session.user_id,)
            ).fetchall()
            providers = {row["provider"] for row in rows}
            if provider not in providers:
                raise AccountError("not_linked", 404, f"No {provider} identity is linked")
            remaining_logins = (providers - {provider}) & LOGIN_METHODS
            if provider in LOGIN_METHODS and not remaining_logins:
                raise AccountError(
                    "last_login_method", 409, "Link another login method before this unlink"
                )
            db.execute(
                "DELETE FROM identities WHERE user_id = ? AND provider = ?",
                (session.user_id, provider),
            )
        LOG.info("Identity unlinked (%s)", provider)

    def delete_account(self, session: Session) -> None:
        with self.db.transaction() as db:
            db.execute("DELETE FROM users WHERE id = ?", (session.user_id,))
        LOG.info("Account deleted")

    # --------------------------------------------------------------- telegram

    def telegram_link_start(self, session: Session) -> tuple[str, str, int]:
        bot = self.settings.telegram_bot_username
        if not bot:
            raise AccountError("provider_disabled", 404, "Telegram linking is not configured")
        wait = take_all(((self.link_codes_per_user, session.user_id),))
        if wait:
            raise AccountError("rate_limited", 429, "Too many link codes", retry_after=wait)
        code = new_token(16)
        now = self._now()
        with self.db.transaction() as db:
            linked = db.execute(
                "SELECT 1 FROM identities WHERE user_id = ? AND provider = 'telegram'",
                (session.user_id,),
            ).fetchone()
            if linked is not None:
                raise AccountError("provider_already_linked", 409, "Unlink Telegram first")
            # Only the newest code of an account works.
            db.execute(
                "DELETE FROM link_codes WHERE user_id = ? AND provider = 'telegram' "
                "AND used_at IS NULL",
                (session.user_id,),
            )
            db.execute(
                "INSERT INTO link_codes (code_hash, user_id, provider, created_at, expires_at) "
                "VALUES (?, ?, 'telegram', ?, ?)",
                (token_hash(code), session.user_id, now, now + LINK_CODE_TTL),
            )
        return code, f"https://t.me/{bot}?start=link_{code}", LINK_CODE_TTL

    def _link_code(
        self, db: sqlite3.Connection, code: str, telegram_user_id: int, now: int
    ) -> sqlite3.Row:
        """Returns a valid code for this Telegram user. Another user gets the same refusal."""
        row = db.execute(
            "SELECT link_codes.*, users.username FROM link_codes "
            "JOIN users ON users.id = link_codes.user_id WHERE code_hash = ?",
            (token_hash(code),),
        ).fetchone()
        invalid = AccountError("invalid_link_code", 400, "Create a new link on the site")
        if row is None or row["expires_at"] <= now:
            raise invalid
        if row["claimed_by"] is not None and row["claimed_by"] != str(telegram_user_id):
            raise invalid
        if row["used_at"] is not None and not self._telegram_linked_to(
            db, row["user_id"], telegram_user_id
        ):
            raise invalid
        return row

    @staticmethod
    def _telegram_linked_to(db: sqlite3.Connection, user_id: str, telegram_user_id: int) -> bool:
        return (
            db.execute(
                "SELECT 1 FROM identities WHERE user_id = ? AND provider = 'telegram' "
                "AND subject = ?",
                (user_id, str(telegram_user_id)),
            ).fetchone()
            is not None
        )

    def telegram_claim(self, code: str, telegram_user_id: int) -> str:
        now = self._now()
        with self.db.transaction() as db:
            row = self._link_code(db, code, telegram_user_id, now)
            owner = db.execute(
                "SELECT user_id FROM identities WHERE provider = 'telegram' AND subject = ?",
                (str(telegram_user_id),),
            ).fetchone()
            if owner is not None and owner["user_id"] != row["user_id"]:
                raise AccountError("identity_in_use", 409, "Telegram is linked to another diary")
            db.execute(
                "UPDATE link_codes SET claimed_by = ? WHERE code_hash = ? AND claimed_by IS NULL",
                (str(telegram_user_id), row["code_hash"]),
            )
        return row["username"]

    def telegram_confirm(self, code: str, telegram_user_id: int) -> str:
        now = self._now()
        with self.db.transaction() as db:
            row = self._link_code(db, code, telegram_user_id, now)
            # The bot claims before it shows «Привязать»; a confirm without a claim is refused.
            if row["claimed_by"] != str(telegram_user_id):
                raise AccountError("invalid_link_code", 400, "Create a new link on the site")
            if row["used_at"] is not None:
                return row["username"]
            self._link(db, row["user_id"], "telegram", str(telegram_user_id), now)
            db.execute(
                "UPDATE link_codes SET used_at = ? WHERE code_hash = ?", (now, row["code_hash"])
            )
        return row["username"]

    def telegram_unlink(self, telegram_user_id: int) -> bool:
        with self.db.transaction() as db:
            cursor = db.execute(
                "DELETE FROM identities WHERE provider = 'telegram' AND subject = ?",
                (str(telegram_user_id),),
            )
        return cursor.rowcount > 0

    # ------------------------------------------------------- application tokens

    @staticmethod
    def _app_token_view(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "created_at": iso(row["created_at"]),
            "expires_at": iso(row["expires_at"]),
            "last_used_at": iso(row["last_used_at"]) if row["last_used_at"] else None,
        }

    def app_tokens(self, session: Session) -> list[dict[str, Any]]:
        """The active tokens of the account, without secrets."""
        with self.db.transaction() as db:
            rows = db.execute(
                "SELECT * FROM app_tokens WHERE user_id = ? AND revoked_at IS NULL "
                "AND expires_at > ? ORDER BY created_at DESC",
                (session.user_id, self._now()),
            ).fetchall()
        return [self._app_token_view(row) for row in rows]

    def app_token_create(
        self, session: Session, name: str, lifetime_days: int
    ) -> tuple[dict[str, Any], str]:
        """Create a token. The caller shows the secret once; the service keeps only its hash."""
        clean = " ".join(name.split())
        if (
            not clean
            or len(clean) > 64
            or any(ord(char) < 32 or ord(char) == 127 for char in clean)
        ):
            raise AccountError("invalid_name", 400, "Name the token in 1 to 64 characters")
        if lifetime_days not in APP_TOKEN_LIFETIMES:
            raise AccountError("invalid_lifetime", 400, "Use 30, 90, or 365 days")
        now = self._now()
        token = "cvpat_" + new_token(32)
        with self.db.transaction() as db:
            active = db.execute(
                "SELECT COUNT(*) FROM app_tokens WHERE user_id = ? AND revoked_at IS NULL "
                "AND expires_at > ?",
                (session.user_id, now),
            ).fetchone()[0]
            if active >= APP_TOKENS_PER_USER:
                raise AccountError("too_many_tokens", 409, "Revoke a token first")
            token_id = uuid.uuid4().hex[:16]
            db.execute(
                "INSERT INTO app_tokens (id, user_id, name, token_hash, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    token_id,
                    session.user_id,
                    clean,
                    token_hash(token),
                    now,
                    now + lifetime_days * 86400,
                ),
            )
            row = db.execute("SELECT * FROM app_tokens WHERE id = ?", (token_id,)).fetchone()
        LOG.info("Application token created")
        return self._app_token_view(row), token

    def app_token_revoke(self, session: Session, token_id: str) -> None:
        with self.db.transaction() as db:
            cursor = db.execute(
                "UPDATE app_tokens SET revoked_at = ? WHERE id = ? AND user_id = ? "
                "AND revoked_at IS NULL",
                (self._now(), token_id, session.user_id),
            )
        if cursor.rowcount == 0:
            raise AccountError("not_found", 404, "No such token")
        LOG.info("Application token revoked")

    def app_token_owner(self, token: str, client_ip: str) -> str:
        """Return the user of a valid application token. Every refusal is the same 401."""
        key = client_key(client_ip)
        wait = max(
            self.app_token_failures.retry_after(key), self.app_token_failures_all.retry_after("*")
        )
        if wait:
            raise AccountError(
                "rate_limited", 429, "Too many failed token checks", retry_after=wait
            )
        now = self._now()
        row = None
        if APP_TOKEN_PATTERN.fullmatch(token):
            with self.db.transaction() as db:
                row = db.execute(
                    "SELECT * FROM app_tokens WHERE token_hash = ?", (token_hash(token),)
                ).fetchone()
        if row is None or row["revoked_at"] is not None or row["expires_at"] <= now:
            self.app_token_failures.record(key)
            self.app_token_failures_all.record("*")
            raise AccountError("app_token_invalid", 401, "The application token is not valid")
        wait = take_all(((self.app_token_calls, row["id"]),))
        if wait:
            raise AccountError("rate_limited", 429, "Too many requests", retry_after=wait)
        if row["last_used_at"] is None or now - row["last_used_at"] >= APP_TOKEN_USE_INTERVAL:
            with self.db.transaction() as db:
                db.execute("UPDATE app_tokens SET last_used_at = ? WHERE id = ?", (now, row["id"]))
        return row["user_id"]

    def app_profile(self, user_id: str) -> dict[str, Any]:
        """Profile for an MCP client: no email, identities, sessions, or consent records."""
        with self.db.transaction() as db:
            user = db.execute(
                "SELECT username, created_at FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        if user is None:
            raise AccountError("app_token_invalid", 401, "The application token is not valid")
        # Preferences come with the diary part of #48; until then the field is null.
        return {
            "username": user["username"],
            "created_at": iso(user["created_at"]),
            "preferences": None,
        }

    def app_wines(self, user_id: str, cursor: str | None, limit: int) -> dict[str, Any]:
        """Found and rated wines, newest first. The diary history of #48 does not exist yet."""
        self.app_profile(user_id)
        return {"items": [], "next_cursor": None}

    # -------------------------------------------------------------------- max

    def _check_launch(
        self, db: sqlite3.Connection, init_data: str, client_ip: str, now: int
    ) -> max_launch.Launch:
        settings = self.settings.max
        if settings is None:
            raise AccountError("provider_disabled", 404, "MAX is not configured")
        # The refusal logs give the reason and the age only, never the launch data.
        try:
            launch = max_launch.verify(init_data, settings.webapp_key)
        except max_launch.LaunchInvalid as error:
            LOG.info("MAX launch refused: %s", error)
            raise AccountError("invalid_launch", 400, "Open the diary from MAX again") from None
        age = now - launch.auth_date
        if age > settings.max_age_seconds or age < -LAUNCH_CLOCK_SKEW:
            LOG.info("MAX launch refused: expired, age %s s", age)
            raise AccountError("launch_expired", 400, "Open the diary from MAX again")
        if settings.require_ip_match and launch.ip != client_ip:
            LOG.info("MAX launch refused: ip %s", "missing" if launch.ip is None else "mismatch")
            raise AccountError("launch_ip_mismatch", 403, "Open the diary from MAX again")
        # Keep the launch ID while the launch data itself is still acceptable.
        valid_until = max(now, launch.auth_date) + settings.max_age_seconds + LAUNCH_CLOCK_SKEW
        try:
            db.execute(
                "INSERT INTO used_launches (query_id, expires_at) VALUES (?, ?)",
                (launch.query_id, valid_until),
            )
        except sqlite3.IntegrityError:
            LOG.info("MAX launch refused: reused, age %s s", age)
            raise AccountError("launch_reused", 400, "Open the diary from MAX again") from None
        return launch

    def max_session(self, init_data: str, client_ip: str) -> SessionIssued | None:
        if self.settings.max is None or not self.settings.max.login_enabled:
            raise AccountError("provider_disabled", 404, "MAX login is not enabled")
        now = self._now()
        with self.db.transaction() as db:
            launch = self._check_launch(db, init_data, client_ip, now)
            row = db.execute(
                "SELECT user_id FROM identities WHERE provider = 'max' AND subject = ?",
                (launch.user_id,),
            ).fetchone()
            if row is None:
                return None
            return self._create_session(
                db, row["user_id"], "max", now, auth_at=launch.auth_date, ttl=MAX_SESSION_TTL
            )

    def max_link(self, session: Session, init_data: str, client_ip: str) -> None:
        now = self._now()
        with self.db.transaction() as db:
            launch = self._check_launch(db, init_data, client_ip, now)
            self._link(db, session.user_id, "max", launch.user_id, now)

    # ------------------------------------------------------------ maintenance

    def purge(self) -> None:
        now = self._now()
        with self.db.transaction() as db:
            for table in ("email_challenges", "oauth_flows", "signup_tickets", "link_codes"):
                db.execute(f"DELETE FROM {table} WHERE expires_at <= ?", (now - 3600,))  # noqa: S608
            db.execute("DELETE FROM used_launches WHERE expires_at <= ?", (now,))
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            db.execute(
                "DELETE FROM app_tokens "
                "WHERE MIN(expires_at, COALESCE(revoked_at, expires_at)) <= ?",
                (now - APP_TOKEN_KEEP_AFTER_END,),
            )
