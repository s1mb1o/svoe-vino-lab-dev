from __future__ import annotations

import base64
import binascii
import ipaddress
import json
import logging
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from html import escape
from urllib.parse import parse_qs, quote, urlencode, urlparse
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

from .config import AdminWebSettings
from .storage import (
    SQLITE_MAX_INTEGER,
    AdminRequestRecord,
    ArtifactRecord,
    ArtifactStore,
    CandidateRecord,
    Repository,
    StepTiming,
    UserSummary,
)

LOG = logging.getLogger("chto_za_vino_bot.admin_web")
MOSCOW_TIME = ZoneInfo("Europe/Moscow")
PAGE_SIZE = 25
MAX_PAGE_NUMBER = SQLITE_MAX_INTEGER // PAGE_SIZE + 1
ACTIVE_STATUSES = {"received", "queued", "processing", "retry_requested"}


def _text(value: object | None, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return escape(str(value))


def _timestamp(value: int | None, *, milliseconds: bool = False) -> str:
    if value is None:
        return "—"
    divisor = 1000 if milliseconds else 1
    moment = datetime.fromtimestamp(value / divisor, tz=MOSCOW_TIME)
    return moment.strftime("%d.%m.%Y %H:%M:%S МСК")


def _duration(value: int | None) -> str:
    if value is None:
        return "—"
    if value < 1000:
        return f"{value} мс"
    return f"{value / 1000:.2f} с"


def _boolean(value: bool | None) -> str:
    if value is None:
        return "—"
    return "да" if value else "нет"


def _moderation_performed(record: AdminRequestRecord) -> bool:
    return record.moderation_category != "disabled" and record.moderation_safe is not None


def _moderation_bypassed(record: AdminRequestRecord) -> bool:
    return record.moderation_category == "disabled"


def _moderation_safe(record: AdminRequestRecord) -> str:
    if _moderation_bypassed(record):
        return "не проверено"
    return _boolean(record.moderation_safe)


def _moderation_accepted(record: AdminRequestRecord) -> bool:
    return record.moderation_safe is True or _moderation_bypassed(record)


def _name(first_name: str | None, last_name: str | None) -> str:
    value = " ".join(part for part in (first_name, last_name) if part).strip()
    return _text(value)


def _username(username: str | None) -> str:
    return f"@{_text(username)}" if username else "—"


def _status(value: str) -> str:
    level = "neutral"
    if value == "recognized":
        level = "good"
    elif value in {"quarantined", "internal_failed", "recognition_failed"}:
        level = "bad"
    elif value in ACTIVE_STATUSES or value == "abstained":
        level = "warn"
    return f'<span class="badge {level}">{escape(value)}</span>'


def _safe_wine_link(url: str | None) -> str:
    if not url:
        return "—"
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"vino-svoe.ru", "www.vino-svoe.ru"}:
        return _text(url)
    safe_url = escape(url, quote=True)
    return f'<a href="{safe_url}" rel="noreferrer">{escape(url)}</a>'


def _layout(title: str, body: str, notice: str | None = None) -> HTMLResponse:
    notice_html = f'<div class="notice">{escape(notice)}</div>' if notice else ""
    content = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{escape(title)} · Что за вино?</title>
  <style>
    :root {{ color-scheme: light dark; --bg:#f5f1eb; --panel:#fffdf9; --text:#231a20;
      --muted:#6d6268; --line:#ded4d8; --accent:#8a1838; --accent-text:#fff;
      --good:#136f46; --warn:#946200; --bad:#a22234; --neutral:#655c61; }}
    @media (prefers-color-scheme: dark) {{ :root {{ --bg:#171215; --panel:#211a1e;
      --text:#f8eff2; --muted:#c0b3b8; --line:#44363d; --accent:#da4167;
      --accent-text:#fff; --good:#45b982; --warn:#e3ac43; --bad:#f06b78; --neutral:#b7abb0; }} }}
    * {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--text);
      font:15px/1.45 system-ui,-apple-system,sans-serif; }}
    header {{ background:#320b1b; color:#fff; padding:16px 0; }}
    .wrap {{ width:min(1180px, calc(100% - 28px)); margin:0 auto; }}
    nav {{ display:flex; flex-wrap:wrap; align-items:center; gap:10px 18px; }}
    nav strong {{ margin-right:auto; font-size:18px; }} nav a {{ color:#fff; text-decoration:none; }}
    main {{ padding:24px 0 48px; }} h1 {{ margin:0 0 20px; font-size:28px; }}
    h2 {{ margin:26px 0 12px; font-size:20px; }}
    .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }}
    .detail-grid {{ display:grid;
      grid-template-columns:repeat(auto-fit,minmax(min(100%,480px),1fr));
      gap:12px; align-items:start; }}
    .card,.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:12px;
      box-shadow:0 2px 10px #0000000d; }} .card {{ padding:16px; }} .card b {{ font-size:25px; display:block; }}
    .card h2 {{ margin:0 0 14px; }}
    .card span,.muted {{ color:var(--muted); }} .panel {{ padding:16px; overflow:auto; }}
    table {{ width:100%; border-collapse:collapse; min-width:760px; }} th,td {{ text-align:left;
      padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
    th {{ color:var(--muted); font-size:13px; }} tr:last-child td {{ border-bottom:0; }}
    a {{ color:var(--accent); }} code {{ overflow-wrap:anywhere; }}
    .badge {{ display:inline-block; border:1px solid currentColor; border-radius:999px; padding:2px 8px;
      font-size:12px; }} .good {{ color:var(--good); }} .warn {{ color:var(--warn); }}
    .bad {{ color:var(--bad); }} .neutral {{ color:var(--neutral); }}
    .notice {{ padding:12px 14px; background:color-mix(in srgb,var(--good) 15%,var(--panel));
      border:1px solid var(--good); border-radius:10px; margin-bottom:18px; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:10px; margin:14px 0; }}
    button,.button {{ border:0; border-radius:8px; padding:9px 13px; background:var(--accent);
      color:var(--accent-text); cursor:pointer; text-decoration:none; font:inherit; }}
    button.danger {{ background:var(--bad); }} select,input {{ padding:8px; border:1px solid var(--line);
      border-radius:8px; background:var(--panel); color:var(--text); }}
    form.inline {{ display:inline-flex; align-items:center; gap:8px; margin:0; }}
    dl {{ display:grid; grid-template-columns:160px minmax(0,1fr); gap:8px 14px; margin:0; }}
    dt {{ color:var(--muted); }} dd {{ margin:0; overflow-wrap:anywhere; word-break:normal; }}
    dd code {{ overflow-wrap:anywhere; word-break:break-all; }}
    .pager {{ display:flex; gap:12px; margin:16px 0; }}
    .artifact-groups {{ display:grid; gap:20px; }}
    .artifact-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }}
    .artifact {{ overflow:hidden; }} .artifact img {{ display:block; width:100%; height:320px;
      object-fit:contain; background:repeating-conic-gradient(#0000000a 0 25%,transparent 0 50%)
      50% / 18px 18px; border-bottom:1px solid var(--line); }}
    .artifact-info {{ padding:14px; }} .artifact-info h3 {{ margin:0 0 6px; font-size:16px; }}
    .artifact-info p {{ margin:5px 0; }} .artifact-info code {{ font-size:12px; }}
    @media (max-width:650px) {{ dl {{ grid-template-columns:1fr; }} dd {{ margin-bottom:8px; }} }}
  </style>
</head>
<body>
<header><div class="wrap"><nav><strong>Что за вино? · Админ</strong>
  <a href="/">Обзор</a><a href="/users">Пользователи</a>
  <a href="/requests">Запросы</a><a href="/appeals">Ошибки фильтра</a>
</nav></div></header>
<main><div class="wrap"><h1>{escape(title)}</h1>{notice_html}{body}</div></main>
</body></html>"""
    return HTMLResponse(content)


def _page_number(raw: int) -> int:
    if raw > MAX_PAGE_NUMBER:
        raise HTTPException(status_code=400, detail="Page number is too large")
    return max(1, raw)


def _pager(path: str, page: int, total: int, extra: dict[str, str] | None = None) -> str:
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    items: list[str] = []
    query = dict(extra or {})
    if page > 1:
        query["page"] = str(page - 1)
        items.append(f'<a class="button" href="{path}?{urlencode(query)}">← Назад</a>')
    items.append(f"<span>Страница {page} из {pages} · всего {total}</span>")
    if page < pages:
        query["page"] = str(page + 1)
        items.append(f'<a class="button" href="{path}?{urlencode(query)}">Далее →</a>')
    return f'<div class="pager">{"".join(items)}</div>'


def _basic_credentials(request: Request) -> tuple[str, str] | None:
    value = request.headers.get("authorization", "")
    if not value.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(value[6:], validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    if ":" not in decoded:
        return None
    return tuple(decoded.split(":", 1))  # type: ignore[return-value]


async def _read_form(request: Request, csrf_token: str) -> dict[str, str]:
    if request.headers.get("content-type", "").split(";", 1)[0] != (
        "application/x-www-form-urlencoded"
    ):
        raise HTTPException(status_code=415, detail="Unsupported form type")
    body = await request.body()
    if len(body) > 8192:
        raise HTTPException(status_code=413, detail="Form is too large")
    try:
        parsed = parse_qs(
            body.decode("utf-8"),
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=10,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid form") from exc
    form = {key: values[-1] for key, values in parsed.items() if values}
    supplied = form.get("csrf", "").encode("utf-8")
    if not secrets.compare_digest(supplied, csrf_token.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return form


def _request_rows(requests: list[AdminRequestRecord]) -> str:
    rows = []
    for item in requests:
        sender = (
            "HTTP API"
            if item.request_source == "api"
            else f'{_username(item.username)}<br><span class="muted">{item.user_id}</span>'
        )
        rows.append(
            "<tr>"
            f'<td><a href="/requests/{quote(item.request_id)}"><code>{escape(item.request_id[:8])}</code></a></td>'
            f"<td>{_timestamp(item.received_at)}</td>"
            f"<td>{sender}</td>"
            f"<td>{_status(item.status)}</td>"
            f"<td>{_text(item.recognition_name)}</td>"
            f"<td>{_duration(item.duration_ms)}</td>"
            f"<td>{'да' if item.moderation_appeal_at else '—'}</td>"
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="7">Нет данных.</td></tr>'
    return "".join(rows)


def _request_table(requests: list[AdminRequestRecord]) -> str:
    return (
        '<div class="panel"><table><thead><tr><th>ID</th><th>Получен</th>'
        '<th>Пользователь</th><th>Статус</th><th>Результат</th>'
        f'<th>Время</th><th>Жалоба</th></tr></thead><tbody>{_request_rows(requests)}</tbody></table></div>'
    )


def _detail_list(items: list[tuple[str, str]]) -> str:
    return "<dl>" + "".join(f"<dt>{escape(key)}</dt><dd>{value}</dd>" for key, value in items) + "</dl>"


def create_app(settings: AdminWebSettings) -> FastAPI:
    networks = tuple(ipaddress.ip_network(item, strict=False) for item in settings.allowed_networks)
    repository = Repository(settings.database_file)
    artifact_store = ArtifactStore(settings.data_root)
    csrf_token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        repository.close()

    app = FastAPI(
        title="Что за вино? Admin",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.repository = repository

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        host = request.client.host if request.client else ""
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            response: Response = PlainTextResponse("Forbidden", status_code=403)
        else:
            if not any(address in network for network in networks):
                response = PlainTextResponse("Forbidden", status_code=403)
            else:
                response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; form-action 'self'; "
            "base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    async def require_authentication(request: Request) -> None:
        credentials = _basic_credentials(request)
        if credentials is not None:
            username, password = credentials
            username_ok = secrets.compare_digest(
                username.encode("utf-8"), settings.username.encode("utf-8")
            )
            password_ok = secrets.compare_digest(
                password.encode("utf-8"), settings.password.encode("utf-8")
            )
            if username_ok and password_ok:
                return
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="ChtoZaVino admin", charset="UTF-8"'},
        )

    authentication = Depends(require_authentication)

    @app.get("/healthz", response_class=PlainTextResponse)
    async def health() -> str:
        return "ok"

    @app.get("/readyz", response_class=PlainTextResponse)
    async def readiness() -> PlainTextResponse:
        ready = repository.is_healthy()
        return PlainTextResponse("ready" if ready else "not ready", status_code=200 if ready else 503)

    @app.get("/", response_class=HTMLResponse, dependencies=[authentication])
    async def overview(request: Request, notice: str | None = None) -> HTMLResponse:
        value = repository.admin_overview(int(time.time()))
        recent, _ = repository.list_admin_requests(page=1, page_size=10)
        cards = [
            ("Всего запросов", value.total),
            ("За 24 часа", value.last_day),
            ("Пользователей", value.users),
            ("Распознано", value.recognized),
            ("Не уверен", value.abstained),
            ("В работе", value.pending),
            ("Ошибок", value.failed),
            ("Карантин", value.quarantined),
            ("Ошибок фильтра", value.moderation_appeals),
            ("Совпало", value.positive_feedback),
            ("Не совпало", value.negative_feedback),
        ]
        body = '<div class="stats-grid">' + "".join(
            f'<div class="card"><b>{number}</b><span>{escape(label)}</span></div>'
            for label, number in cards
        ) + "</div><h2>Последние запросы</h2>" + _request_table(recent)
        return _layout("Обзор", body, notice)

    @app.get("/users", response_class=HTMLResponse, dependencies=[authentication])
    async def users(page: int = 1, notice: str | None = None) -> HTMLResponse:
        page = _page_number(page)
        now = int(time.time())
        values, total = repository.list_users(
            page=page,
            page_size=PAGE_SIZE,
            now=now,
            window_seconds=settings.rate_window_seconds,
        )
        rows = "".join(_user_row(user, settings, csrf_token) for user in values)
        if not rows:
            rows = '<tr><td colspan="7">Нет данных.</td></tr>'
        body = (
            _pager("/users", page, total)
            + '<div class="panel"><table><thead><tr><th>Telegram</th><th>Имя</th>'
            '<th>User ID</th><th>Всего</th><th>За час</th><th>Последний запрос</th>'
            f'<th>Действие</th></tr></thead><tbody>{rows}</tbody></table></div>'
            + _pager("/users", page, total)
        )
        return _layout("Пользователи", body, notice)

    @app.post("/users/{user_id}/reset", dependencies=[authentication])
    async def reset_user_limit(user_id: int, request: Request) -> RedirectResponse:
        await _read_form(request, csrf_token)
        identity = repository.user_by_id(user_id)
        if identity is None:
            raise HTTPException(status_code=404, detail="User not found")
        count = repository.reset_rate_limit(
            user_id,
            int(time.time()),
            settings.rate_window_seconds,
        )
        return RedirectResponse(
            f"/users?{urlencode({'notice': f'Лимит сброшен. Исключено запросов: {count}.'})}",
            status_code=303,
        )

    @app.get("/requests", response_class=HTMLResponse, dependencies=[authentication])
    async def requests_page(
        page: int = 1,
        status: str = "",
        notice: str | None = None,
    ) -> HTMLResponse:
        page = _page_number(page)
        selected_status = status.strip() or None
        values, total = repository.list_admin_requests(
            page=page,
            page_size=PAGE_SIZE,
            status=selected_status,
        )
        filters = (
            '<form class="inline" method="get" action="/requests">'
            '<label for="status">Статус</label>'
            f'<input id="status" name="status" value="{escape(status, quote=True)}" placeholder="recognized">'
            '<button type="submit">Показать</button></form>'
        )
        extra = {"status": status} if status else None
        body = filters + _pager("/requests", page, total, extra) + _request_table(values)
        body += _pager("/requests", page, total, extra)
        return _layout("Запросы", body, notice)

    @app.get("/appeals", response_class=HTMLResponse, dependencies=[authentication])
    async def appeals(page: int = 1) -> HTMLResponse:
        page = _page_number(page)
        values, total = repository.list_admin_requests(
            page=page,
            page_size=PAGE_SIZE,
            appeals_only=True,
        )
        body = _pager("/appeals", page, total) + _request_table(values)
        body += _pager("/appeals", page, total)
        return _layout("Ошибки фильтра", body)

    @app.get(
        "/requests/{request_id}",
        response_class=HTMLResponse,
        dependencies=[authentication],
    )
    async def request_detail(request_id: str, notice: str | None = None) -> HTMLResponse:
        record = repository.admin_request(request_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Request not found")
        timings = repository.step_timings(request_id)
        candidates = repository.candidates(request_id)
        artifacts = repository.visible_artifacts(request_id)
        body = _request_detail(record, timings, candidates, artifacts, csrf_token)
        return _layout(f"Запрос {request_id[:8]}", body, notice)

    @app.get(
        "/requests/{request_id}/artifacts/{artifact_key}",
        dependencies=[authentication],
    )
    async def request_artifact(request_id: str, artifact_key: str) -> FileResponse:
        record = repository.visible_artifact(request_id, artifact_key)
        if record is None or record.mime_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            raise HTTPException(status_code=404, detail="Artifact not found")
        try:
            path = artifact_store.resolve(record.relative_path)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Artifact not found") from exc
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Artifact not found")
        return FileResponse(path, media_type=record.mime_type)

    @app.post("/requests/{request_id}/retry", dependencies=[authentication])
    async def retry_request(request_id: str, request: Request) -> RedirectResponse:
        await _read_form(request, csrf_token)
        result = repository.request_retry(request_id, int(time.time()))
        notices = {
            "requested": "Повторная обработка добавлена в очередь.",
            "already_requested": "Запрос уже находится в очереди или обработке.",
            "unavailable": "Повторная обработка недоступна для этого запроса.",
        }
        return RedirectResponse(
            f"/requests/{quote(request_id)}?{urlencode({'notice': notices[result]})}",
            status_code=303,
        )

    return app


def _user_row(user: UserSummary, settings: AdminWebSettings, csrf_token: str) -> str:
    remaining = max(0, settings.rate_limit - user.window_requests)
    return (
        "<tr>"
        f"<td>{_username(user.username)}</td><td>{_name(user.first_name, user.last_name)}</td>"
        f"<td><code>{user.user_id}</code></td><td>{user.total_requests}</td>"
        f"<td>{user.window_requests}/{settings.rate_limit}<br><span class=\"muted\">осталось {remaining}</span></td>"
        f"<td>{_timestamp(user.last_request_at)}</td>"
        '<td><form class="inline" method="post" '
        f'action="/users/{user.user_id}/reset">'
        f'<input type="hidden" name="csrf" value="{escape(csrf_token, quote=True)}">'
        '<button class="danger" type="submit">Сбросить лимит</button></form></td>'
        "</tr>"
    )


def _request_detail(
    record: AdminRequestRecord,
    timings: list[StepTiming],
    candidates: list[CandidateRecord],
    artifacts: list[ArtifactRecord],
    csrf_token: str,
) -> str:
    retry = ""
    if (
        record.request_source == "telegram"
        and _moderation_accepted(record)
        and record.status not in ACTIVE_STATUSES
    ):
        retry = (
            '<form class="inline" method="post" '
            f'action="/requests/{quote(record.request_id)}/retry">'
            f'<input type="hidden" name="csrf" value="{escape(csrf_token, quote=True)}">'
            '<button class="danger" type="submit">Повторить обработку</button></form>'
        )
    identity = _detail_list(
        [
            ("Request ID", f"<code>{escape(record.request_id)}</code>"),
            ("Источник", "HTTP API" if record.request_source == "api" else "Telegram"),
            ("Получен", _timestamp(record.received_at)),
            ("Статус", _status(record.status)),
            ("Ошибка", _text(record.error_code)),
            ("Полное время", _duration(record.duration_ms)),
            ("Telegram", _username(record.username)),
            ("Имя", _name(record.first_name, record.last_name)),
            ("User ID", f"<code>{record.user_id}</code>"),
            ("Повторов", str(record.retry_count)),
            ("Повтор запрошен", _timestamp(record.retry_requested_at)),
        ]
    )
    moderation = _detail_list(
        [
            ("Проверка выполнена", _boolean(_moderation_performed(record))),
            ("Проверка пропущена", _boolean(_moderation_bypassed(record))),
            ("Безопасно", _moderation_safe(record)),
            ("Категория", _text(record.moderation_category)),
            ("Вероятность", _text(record.moderation_confidence)),
            ("Причина", _text(record.moderation_reason)),
            ("Ошибка фильтра", _timestamp(record.moderation_appeal_at)),
        ]
    )
    image_metadata = _detail_list(
        [
            ("Размер", f"{record.image_bytes} байт" if record.image_bytes is not None else "—"),
            ("SHA-256", f"<code>{_text(record.image_sha256)}</code>"),
            ("pHash", f"<code>{_text(record.image_phash)}</code>"),
            ("dHash", f"<code>{_text(record.image_dhash)}</code>"),
        ]
    )
    quality = _detail_list(
        [
            ("Приемлемо", _boolean(record.quality_acceptable)),
            ("Замечания", _text(record.quality_issues)),
            ("Blur variance", _text(record.quality_blur_variance)),
            ("Glare ratio", _text(record.quality_glare_ratio)),
            ("Bottle area ratio", _text(record.quality_bottle_area_ratio)),
            ("Label area ratio", _text(record.quality_label_area_ratio)),
        ]
    )
    recognition = _detail_list(
        [
            ("Название", _text(record.recognition_name)),
            ("Slug", _text(record.recognition_slug)),
            ("Страница", _safe_wine_link(record.recognition_page_url)),
            ("Score", _text(record.recognition_score)),
            ("Margin", _text(record.recognition_margin)),
            ("Совпало", _boolean(record.feedback_match)),
            ("Оценка получена", _timestamp(record.feedback_at)),
            ("Выбранный вариант", _text(record.feedback_selected_slug)),
            ("Ранг варианта", _text(record.feedback_selected_rank)),
            ("Вариант выбран", _timestamp(record.feedback_alternative_at)),
        ]
    )
    candidate_rows = "".join(
        f"<tr><td>{item.rank}</td><td>{escape(item.slug)}</td><td>{item.score:.6f}</td></tr>"
        for item in candidates
    ) or '<tr><td colspan="3">Нет данных.</td></tr>'
    timing_rows = "".join(
        f"<tr><td>{escape(item.step)}</td><td>{_timestamp(item.started_at_ms, milliseconds=True)}</td>"
        f"<td>{_duration(item.duration_ms)}</td><td>{escape(item.outcome)}</td></tr>"
        for item in timings
    ) or '<tr><td colspan="4">Нет данных.</td></tr>'
    artifact_gallery = _artifact_gallery(record.request_id, artifacts)
    return (
        f'<div class="actions"><a class="button" href="/requests">← К запросам</a>{retry}</div>'
        f'<div class="detail-grid"><section class="card"><h2>Запрос</h2>{identity}</section>'
        f'<section class="card"><h2>Модерация</h2>{moderation}</section>'
        f'<section class="card"><h2>Метаданные изображения</h2>{image_metadata}</section>'
        f'<section class="card"><h2>Качество</h2>{quality}</section>'
        f'<section class="card"><h2>Распознавание</h2>{recognition}</section></div>'
        '<h2>Кандидаты</h2><div class="panel"><table><thead><tr><th>Ранг</th><th>Slug</th>'
        f'<th>Score</th></tr></thead><tbody>{candidate_rows}</tbody></table></div>'
        '<h2>Этапы</h2><div class="panel"><table><thead><tr><th>Этап</th><th>Начало</th>'
        f'<th>Длительность</th><th>Результат</th></tr></thead><tbody>{timing_rows}</tbody></table></div>'
        f'{artifact_gallery}'
    )


def _artifact_gallery(request_id: str, artifacts: list[ArtifactRecord]) -> str:
    if not artifacts:
        return '<h2>Визуальные этапы</h2><p class="muted">Артефакты не сохранены.</p>'
    step_titles = {
        "input": "1. Вход распознавания",
        "moderation": "2. Подготовка и модерация",
        "quality": "3. SAM3 и качество",
        "result": "4. Результат",
        "censored": "Цензурированный preview",
    }
    groups: list[str] = []
    for step in dict.fromkeys(item.step for item in artifacts):
        cards: list[str] = []
        for item in (value for value in artifacts if value.step == step):
            url = (
                f"/requests/{quote(request_id)}/artifacts/{quote(item.artifact_key)}"
            )
            try:
                metadata = json.loads(item.metadata_json)
                metadata_text = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            except (json.JSONDecodeError, TypeError):
                metadata_text = item.metadata_json
            cards.append(
                '<article class="card artifact">'
                f'<a href="{url}"><img src="{url}" loading="lazy" '
                f'alt="{escape(item.title, quote=True)}"></a>'
                '<div class="artifact-info">'
                f'<h3>{escape(item.title)}</h3><p>{escape(item.description)}</p>'
                f'<p class="muted">{item.width} × {item.height} · {escape(item.mime_type)}</p>'
                f'<code>{escape(metadata_text)}</code></div></article>'
            )
        heading = step_titles.get(step, step)
        groups.append(
            f'<section><h3>{escape(heading)}</h3><div class="artifact-grid">'
            f'{"".join(cards)}</div></section>'
        )
    return '<h2>Визуальные этапы</h2><div class="artifact-groups">' + "".join(groups) + "</div>"


def main() -> None:
    settings = AdminWebSettings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        proxy_headers=False,
    )


if __name__ == "__main__":
    main()
