"""Internal HTTP API. Only the Nuxt server and the bots call it, on the LAN.

Every route except the health checks needs an allowed client network and the bearer token of
a consumer. The Nuxt server sends the session in X-Session-Token and the browser address in
X-Client-IP.

This module does not use postponed annotations: FastAPI must resolve the dependency
functions that create_app defines locally.
"""

import asyncio
import contextlib
import ipaddress
import logging
import re
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from .config import Settings
from .db import Database
from .mailer import Dispatcher, Mailer, ThreadDispatcher, build_mailer
from .service import (
    AccountError,
    AccountService,
    AuthResult,
    Linked,
    Session,
    SessionIssued,
    SignupRequired,
    iso,
    normalize_ip,
)
from .tokens import equal
from .yandex import YandexClient

LOG = logging.getLogger("chto_za_vino_account")
MAX_BODY_BYTES = 16 * 1024
PURGE_INTERVAL = 600
OPEN_PATHS = frozenset({"/healthz", "/readyz"})
SAFE_FIELD = re.compile(r"[a-z_]{1,40}(\.[a-z_]{1,40})?")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmailStart(Strict):
    email: str = Field(min_length=3, max_length=254, repr=False)
    purpose: Literal["login", "link"] = "login"


class EmailVerify(Strict):
    challenge_id: str = Field(min_length=20, max_length=128, repr=False)
    code: str = Field(pattern=r"^\d{6}$", repr=False)


class YandexStart(Strict):
    redirect_uri: str = Field(min_length=8, max_length=512)
    purpose: Literal["login", "link"] = "login"


class YandexFinish(Strict):
    flow_id: str = Field(min_length=20, max_length=128, repr=False)
    state: str = Field(min_length=1, max_length=1024, repr=False)
    code: str = Field(min_length=1, max_length=512, repr=False)


class Signup(Strict):
    signup_ticket: str = Field(min_length=20, max_length=128, repr=False)
    username: str = Field(min_length=1, max_length=64)
    consent_version: str = Field(min_length=1, max_length=64)
    terms_version: str = Field(min_length=1, max_length=64)


class MaxLaunch(Strict):
    init_data: str = Field(min_length=1, max_length=8192, repr=False)


class TelegramCode(Strict):
    code: str = Field(pattern=r"^[A-Za-z0-9_-]{16,64}$", repr=False)
    telegram_user_id: int = Field(gt=0, lt=2**53)


class TelegramUser(Strict):
    telegram_user_id: int = Field(gt=0, lt=2**53)


def create_app(
    settings: Settings,
    *,
    mailer: Mailer | None = None,
    dispatcher: Dispatcher | None = None,
    http: httpx.Client | None = None,
    clock: Callable[[], float] = time.time,
) -> FastAPI:
    db = Database(settings.database)
    dispatcher = dispatcher or ThreadDispatcher(mailer or build_mailer(settings))
    http = http or httpx.Client(follow_redirects=False)
    yandex = YandexClient(settings.yandex, http) if settings.yandex else None
    service = AccountService(settings, db, dispatcher, yandex, clock)
    networks = tuple(ipaddress.ip_network(item, strict=False) for item in settings.allowed_networks)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async def purge_loop() -> None:
            while True:
                try:
                    await asyncio.to_thread(service.purge)
                except Exception:  # noqa: BLE001 - maintenance never stops the service
                    LOG.exception("Purge failed")
                await asyncio.sleep(PURGE_INTERVAL)

        task = asyncio.create_task(purge_loop())
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            dispatcher.close()
            http.close()
            db.close()

    app = FastAPI(
        title="«Винный дневник» account service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.service = service

    @app.middleware("http")
    async def guard(request: Request, call_next: Callable[[Request], Any]) -> Response:
        if request.url.path not in OPEN_PATHS:
            host = request.client.host if request.client else ""
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                address = None
            if address is None or not any(address in network for network in networks):
                return _error(AccountError("forbidden", 403, "Client network is not allowed"))
            length = request.headers.get("content-length")
            if length is not None and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
                return _error(AccountError("body_too_large", 413, "The request body is too large"))
            if length is None and "chunked" in request.headers.get("transfer-encoding", ""):
                return _error(AccountError("length_required", 411, "Send Content-Length"))
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(AccountError)
    async def account_error(_: Request, error: AccountError) -> Response:
        return _error(error)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, error: RequestValidationError) -> Response:
        fields = sorted({_field_label(item) for item in error.errors()})
        return JSONResponse({"error": "invalid_request", "fields": fields}, status_code=422)

    # --------------------------------------------------------- dependencies

    def consumer(authorization: Annotated[str, Header()] = "") -> str:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            for name, secret in settings.consumers.items():
                if equal(token, secret):
                    return name
        raise AccountError("unauthorized", 401, "A consumer bearer token is required")

    def only(*names: str) -> Callable[[str], str]:
        def check(name: Annotated[str, Depends(consumer)]) -> str:
            if name not in names:
                raise AccountError("forbidden", 403, "This consumer cannot call this route")
            return name

        return check

    web = Depends(only("web"))
    telegram_bot = Depends(only("telegram-bot"))

    def session_token(x_session_token: Annotated[str, Header()] = "") -> str:
        if not x_session_token or len(x_session_token) > 128:
            raise AccountError("session_invalid", 401, "Log in again")
        return x_session_token

    def current_session(token: Annotated[str, Depends(session_token)]) -> Session:
        session = service.authenticate(token)
        if session is None:
            raise AccountError("session_invalid", 401, "Log in again")
        return session

    def optional_session(x_session_token: Annotated[str, Header()] = "") -> Session | None:
        if not x_session_token:
            return None
        return current_session(session_token(x_session_token))

    def client_ip(x_client_ip: Annotated[str, Header()] = "") -> str:
        if not x_client_ip:
            raise AccountError("client_ip_required", 400, "X-Client-IP is required")
        return normalize_ip(x_client_ip)

    def auth_response(result: AuthResult | Linked) -> dict[str, Any]:
        if isinstance(result, SessionIssued):
            return {
                "status": "session",
                "session": {
                    "token": result.token,
                    "expires_at": iso(result.expires_at),
                    "auth_method": result.auth_method,
                },
                "user": service.user_view(result.user_id),
            }
        if isinstance(result, SignupRequired):
            body: dict[str, Any] = {
                "status": "signup_required",
                "signup_ticket": result.ticket,
                "provider": result.provider,
            }
            if result.email:
                body["email"] = result.email
            return body
        return {"status": "linked", "user": service.user_view(result.user_id)}

    # --------------------------------------------------------------- health

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> Response:
        try:
            ready = db.ping()
        except Exception:  # noqa: BLE001 - readiness reports any database failure
            ready = False
        status = 200 if ready else 503
        return JSONResponse({"status": "ok" if ready else "unavailable"}, status_code=status)

    # ---------------------------------------------------------------- login

    @app.get("/v1/config", dependencies=[web])
    def config() -> dict[str, Any]:
        return service.provider_config()

    @app.post("/v1/auth/email/start", dependencies=[web])
    def email_start(
        body: EmailStart,
        ip: Annotated[str, Depends(client_ip)],
        session: Annotated[Session | None, Depends(optional_session)],
    ) -> dict[str, Any]:
        challenge_id, ttl = service.email_start(body.email, body.purpose, ip, session)
        return {"challenge_id": challenge_id, "expires_in": ttl}

    @app.post("/v1/auth/email/verify", dependencies=[web])
    def email_verify(
        body: EmailVerify, session: Annotated[Session | None, Depends(optional_session)]
    ) -> dict[str, Any]:
        return auth_response(service.email_verify(body.challenge_id, body.code, session))

    @app.post("/v1/auth/yandex/start", dependencies=[web])
    def yandex_start(
        body: YandexStart,
        ip: Annotated[str, Depends(client_ip)],
        session: Annotated[Session | None, Depends(optional_session)],
    ) -> dict[str, Any]:
        url, flow_id, ttl = service.yandex_start(body.redirect_uri, body.purpose, ip, session)
        return {"authorize_url": url, "flow_id": flow_id, "expires_in": ttl}

    @app.post("/v1/auth/yandex/finish", dependencies=[web])
    def yandex_finish(
        body: YandexFinish, session: Annotated[Session | None, Depends(optional_session)]
    ) -> dict[str, Any]:
        return auth_response(service.yandex_finish(body.flow_id, body.state, body.code, session))

    @app.post("/v1/auth/signup", dependencies=[web])
    def signup(body: Signup) -> dict[str, Any]:
        return auth_response(
            service.signup(
                body.signup_ticket, body.username, body.consent_version, body.terms_version
            )
        )

    @app.post("/v1/auth/max/session", dependencies=[web])
    def max_session(body: MaxLaunch, ip: Annotated[str, Depends(client_ip)]) -> dict[str, Any]:
        issued = service.max_session(body.init_data, ip)
        if issued is None:
            return {"status": "not_linked"}
        return auth_response(issued)

    # -------------------------------------------------------------- account

    @app.delete("/v1/sessions/current", dependencies=[web], status_code=204)
    def logout(token: Annotated[str, Depends(session_token)]) -> Response:
        service.logout(token)
        return Response(status_code=204)

    @app.get("/v1/me", dependencies=[web])
    def me(session: Annotated[Session, Depends(current_session)]) -> dict[str, Any]:
        return {
            "user": service.user_view(session.user_id),
            "session": {
                "auth_method": session.auth_method,
                "expires_at": iso(session.expires_at),
            },
        }

    @app.delete("/v1/me", dependencies=[web], status_code=204)
    def delete_me(session: Annotated[Session, Depends(current_session)]) -> Response:
        service.delete_account(session)
        return Response(status_code=204)

    @app.post("/v1/me/identities/max", dependencies=[web])
    def link_max(
        body: MaxLaunch,
        ip: Annotated[str, Depends(client_ip)],
        session: Annotated[Session, Depends(current_session)],
    ) -> dict[str, Any]:
        service.max_link(session, body.init_data, ip)
        return auth_response(Linked(session.user_id))

    @app.delete("/v1/me/identities/{provider}", dependencies=[web], status_code=204)
    def unlink(
        provider: Literal["email", "yandex", "max", "telegram"],
        session: Annotated[Session, Depends(current_session)],
    ) -> Response:
        service.unlink(session, provider)
        return Response(status_code=204)

    @app.post("/v1/me/links/telegram", dependencies=[web])
    def telegram_link(session: Annotated[Session, Depends(current_session)]) -> dict[str, Any]:
        code, link, ttl = service.telegram_link_start(session)
        return {"code": code, "deep_link": link, "expires_in": ttl}

    # ------------------------------------------------------------------ bots

    @app.post("/v1/bot/telegram/links/claim", dependencies=[telegram_bot])
    def telegram_claim(body: TelegramCode) -> dict[str, str]:
        return {"username": service.telegram_claim(body.code, body.telegram_user_id)}

    @app.post("/v1/bot/telegram/links/confirm", dependencies=[telegram_bot])
    def telegram_confirm(body: TelegramCode) -> dict[str, str]:
        username = service.telegram_confirm(body.code, body.telegram_user_id)
        return {"status": "linked", "username": username}

    @app.post("/v1/bot/telegram/unlink", dependencies=[telegram_bot])
    def telegram_unlink(body: TelegramUser) -> dict[str, str]:
        removed = service.telegram_unlink(body.telegram_user_id)
        return {"status": "unlinked" if removed else "not_linked"}

    return app


def _field_label(item: Any) -> str:
    """A field name from our schema, never a key or value that the client sent."""
    if item.get("type") == "extra_forbidden":
        return "unknown_field"
    parts = [str(part) for part in item.get("loc", ())[1:]]
    label = ".".join(parts)
    return label if SAFE_FIELD.fullmatch(label) else "invalid_field"


def _error(error: AccountError) -> Response:
    body: dict[str, Any] = {"error": error.code}
    if error.detail:
        body["detail"] = error.detail
    body.update(error.extra)
    headers = {"Cache-Control": "no-store"}
    if error.retry_after is not None:
        headers["Retry-After"] = str(error.retry_after)
    return JSONResponse(body, status_code=error.status, headers=headers)
