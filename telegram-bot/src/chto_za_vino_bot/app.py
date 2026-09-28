from __future__ import annotations

import asyncio
import io
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from html import escape
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx
import uvicorn
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BotCommandScopeChat,
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
    ReplyParameters,
)

from .config import Settings
from .data_lifecycle import purge_expired_data
from .fingerprints import difference_hash, perceptual_hash
from .http_api import (
    HttpQueueFull,
    HttpQueueUnavailable,
    HttpRecognitionResult,
    create_http_api_app,
)
from .matcher import Matcher, RecognitionUnavailable, is_confident
from .moderation import (
    DisabledModerator,
    InvalidImage,
    ModerationUnavailable,
    Moderator,
    make_moderation_jpeg,
    make_moderator,
)
from .pipeline_artifacts import (
    GeneratedArtifact,
    base_artifacts,
    censored_artifact,
    persist_artifacts,
    quality_artifacts,
    result_artifact,
)
from .profile import (
    ADMIN_COMMANDS,
    AGE_GATE_TEXT,
    COMMANDS,
    DESCRIPTION,
    HELP_TEXT,
    MINOR_TEXT,
    PRIVACY_TEXT,
    SHORT_DESCRIPTION,
    START_CONFIRMED_TEXT,
)
from .quality import QualityInspector, QualityThresholds, QualityUnavailable
from .result_card import (
    CatalogImageLoader,
    CatalogImageUnavailable,
    format_result_caption,
    normalize_result_photo,
)
from .storage import (
    AdminRequestRecord,
    ArtifactStore,
    CandidateRecord,
    ImageStore,
    Repository,
    UserIdentity,
    UserSummary,
)
from .wine import Wine, unknown_wine, wine_card, wine_from_card
from .work_queue import QueueCapacityError, QueueClosedError, WorkQueue

LOG = logging.getLogger("chto_za_vino_bot")

AGE_CONFIRMATION_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Мне есть 18 лет", callback_data="age:adult"),
            InlineKeyboardButton(text="Мне нет 18 лет", callback_data="age:minor"),
        ]
    ]
)

CONTENT_REJECTED_TEXT = (
    "Контент признан неподходящим и не передан в распознавание.\n\n"
    "Если фильтр ошибся, сообщите об этом кнопкой ниже."
)

def result_feedback_keyboard(
    request_id: str,
    page_url: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть страницу вина", url=page_url)],
            [
                InlineKeyboardButton(
                    text="✅ Совпало",
                    callback_data=f"feedback:yes:{request_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Не совпало",
                    callback_data=f"feedback:no:{request_id}",
                ),
            ]
        ]
    )


def moderation_appeal_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сообщить об ошибке фильтра",
                    callback_data=f"moderation_error:{request_id}",
                )
            ]
        ]
    )


def alternative_keyboard(
    request_id: str,
    wines: list[tuple[int, Wine]],
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{rank}. {wine.name[:48]}",
                callback_data=f"alternative:{rank}:{request_id}",
            )
        ]
        for rank, wine in wines
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="Ничего из этого",
                callback_data=f"alternative:0:{request_id}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


class AlbumReceiptTracker:
    def __init__(self, *, ttl_seconds: float = 300, capacity: int = 1000) -> None:
        if ttl_seconds <= 0:
            raise ValueError("album receipt TTL must be positive")
        if capacity <= 0:
            raise ValueError("album receipt capacity must be positive")
        self._ttl_seconds = ttl_seconds
        self._capacity = capacity
        self._seen_at: dict[str, float] = {}

    def claim(self, media_group_id: str, *, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        cutoff = current - self._ttl_seconds
        self._seen_at = {
            group_id: seen_at
            for group_id, seen_at in self._seen_at.items()
            if seen_at > cutoff
        }
        if media_group_id in self._seen_at:
            self._seen_at[media_group_id] = current
            return False
        if len(self._seen_at) >= self._capacity:
            oldest_group = min(self._seen_at, key=self._seen_at.get)
            del self._seen_at[oldest_group]
        self._seen_at[media_group_id] = current
        return True

    def release(self, media_group_id: str) -> None:
        self._seen_at.pop(media_group_id, None)


@dataclass(slots=True)
class Services:
    settings: Settings
    repository: Repository
    store: ImageStore
    artifact_store: ArtifactStore
    moderator: Moderator | DisabledModerator
    quality_inspector: QualityInspector
    matcher: Matcher
    image_loader: CatalogImageLoader
    rejection_image: bytes


@dataclass(slots=True)
class PhotoJob:
    request_id: str
    chat_id: int
    source_message_id: int
    received_at: int
    file_id: str
    status_message_id: int | None
    feedback_enabled: bool = True
    status_enabled: bool = True
    keep_status: bool = False
    image_body: bytes | None = None
    delivery_enabled: bool = True
    completion: asyncio.Future[None] | None = None


class PhotoProcessor:
    def __init__(self, services: Services, bot: Bot) -> None:
        self._services = services
        self._bot = bot

    async def process(self, job: PhotoJob) -> None:
        processing_started = time.monotonic()
        try:
            await self._process(job)
        except asyncio.CancelledError:
            LOG.info("Photo processing interrupted", extra={"request_id": job.request_id})
            if job.image_body is not None:
                self._services.repository.update(
                    job.request_id,
                    status="internal_failed",
                    error_code="interrupted",
                )
            raise
        except Exception:
            LOG.exception("Unexpected photo processing failure", extra={"request_id": job.request_id})
            self._services.repository.update(
                job.request_id,
                status="internal_failed",
                error_code="internal",
            )
            await self._set_terminal_status(
                job,
                "Не удалось обработать фотографию из-за внутренней ошибки. Попробуйте еще раз.",
            )
        finally:
            if job.image_body is not None:
                self._services.repository.update(
                    job.request_id,
                    duration_ms=max(
                        0,
                        int((time.monotonic() - processing_started) * 1000),
                    ),
                )
            if job.completion is not None and not job.completion.done():
                job.completion.set_result(None)

    async def _process(self, job: PhotoJob) -> None:
        started = time.monotonic()
        self._record_step_timing(
            job,
            step="queue_wait",
            started_at_ms=job.received_at * 1000,
            duration_ms=max(0, int(time.time() * 1000) - job.received_at * 1000),
            outcome="ok",
        )
        self._services.repository.update(
            job.request_id,
            status="processing",
            error_code=None,
            moderation_safe=None,
            moderation_category=None,
            moderation_confidence=None,
            moderation_reason=None,
        )
        await self._set_status(job, "Проверяю фотографию…")

        try:
            if job.image_body is not None:
                with self._timed_step(job, "http_input"):
                    body = job.image_body
                    if not body or len(body) > self._services.settings.max_image_bytes:
                        raise InvalidImage("image size is invalid")
            else:
                with self._timed_step(job, "telegram_download"):
                    telegram_file = await self._bot.get_file(job.file_id)
                    buffer = io.BytesIO()
                    await self._bot.download_file(telegram_file.file_path, destination=buffer)
                    body = buffer.getvalue()
                    if not body or len(body) > self._services.settings.max_image_bytes:
                        raise InvalidImage("image size is invalid")
        except InvalidImage:
            self._services.repository.update(
                job.request_id, status="invalid_image", error_code="invalid_size"
            )
            await self._set_terminal_status(
                job, "Не удалось прочитать фотографию. Отправьте другое изображение."
            )
            return
        except Exception:
            LOG.exception(
                "Telegram image download failed", extra={"request_id": job.request_id}
            )
            self._services.repository.update(
                job.request_id, status="download_failed", error_code="telegram"
            )
            await self._set_terminal_status(
                job, "Не удалось загрузить фотографию. Попробуйте еще раз."
            )
            return

        try:
            with self._timed_step(job, "image_prepare"):
                moderation_jpeg = make_moderation_jpeg(body)
        except InvalidImage:
            self._services.repository.update(
                job.request_id, status="invalid_image", error_code="decode"
            )
            await self._set_terminal_status(
                job, "Файл не похож на поддерживаемую фотографию."
            )
            return

        try:
            with self._timed_step(job, "moderation"):
                moderation = await self._services.moderator.classify(moderation_jpeg)
        except ModerationUnavailable:
            LOG.exception("Image moderation failed", extra={"request_id": job.request_id})
            self._services.repository.update(
                job.request_id, status="moderation_failed", error_code="upstream"
            )
            await self._set_terminal_status(
                job,
                "Сейчас не работает проверка безопасности. Фотография не сохранена. "
                "Попробуйте позже.",
            )
            return

        with self._timed_step(job, "fingerprints"):
            image_phash = perceptual_hash(body)
            image_dhash = difference_hash(body)
        with self._timed_step(job, "image_storage"):
            relative_path, digest = self._services.store.save(
                job.request_id, job.received_at, body, moderation.accepted
            )
        self._services.repository.update(
            job.request_id,
            image_bytes=len(body),
            image_sha256=digest,
            image_phash=image_phash,
            image_dhash=image_dhash,
            moderation_safe=moderation.safe,
            moderation_category=moderation.category,
            moderation_confidence=moderation.confidence,
            moderation_reason=moderation.reason,
            storage_path=relative_path,
        )

        if not moderation.accepted:
            try:
                with self._timed_step(job, "artifact_censored"):
                    self._save_artifacts(
                        job,
                        [censored_artifact(moderation_jpeg)],
                        replace=True,
                    )
            except Exception:
                LOG.exception(
                    "Censored artifact generation failed",
                    extra={"request_id": job.request_id},
                )
            self._services.repository.update(
                job.request_id,
                status="quarantined",
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            with self._timed_step(job, "result_delivery"):
                await self._send_rejection(job)
            return

        try:
            with self._timed_step(job, "artifact_base"):
                self._save_artifacts(
                    job,
                    base_artifacts(body, moderation_jpeg),
                    replace=True,
                )
        except Exception:
            LOG.exception(
                "Base artifact generation failed",
                extra={"request_id": job.request_id},
            )

        await self._set_status(job, "Проверяю качество фотографии…")
        try:
            with self._timed_step(job, "quality"):
                quality = await self._services.quality_inspector.inspect(moderation_jpeg)
        except QualityUnavailable:
            LOG.warning(
                "Image quality check unavailable; continuing to recognition",
                exc_info=True,
                extra={"request_id": job.request_id},
            )
            self._services.repository.update(
                job.request_id,
                quality_acceptable=None,
                quality_issues="check_unavailable",
            )
        else:
            self._services.repository.update(
                job.request_id,
                quality_acceptable=int(quality.acceptable),
                quality_issues=",".join(quality.issues),
                quality_blur_variance=quality.blur_variance,
                quality_glare_ratio=quality.glare_ratio,
                quality_bottle_area_ratio=quality.bottle_area_ratio,
                quality_label_area_ratio=quality.label_area_ratio,
            )
            if not quality.acceptable:
                LOG.info(
                    "Image quality advisory request_id=%s issues=%s",
                    job.request_id,
                    ",".join(quality.issues),
                )
            try:
                with self._timed_step(job, "artifact_quality"):
                    self._save_artifacts(
                        job,
                        quality_artifacts(moderation_jpeg, quality),
                    )
            except Exception:
                LOG.exception(
                    "Quality artifact generation failed",
                    extra={"request_id": job.request_id},
                )

        await self._set_status(job, "Ищу вино в каталоге…")
        try:
            with self._timed_step(job, "recognition"):
                result = await self._services.matcher.recognize(body)
        except RecognitionUnavailable:
            LOG.exception("Wine recognition failed", extra={"request_id": job.request_id})
            self._services.repository.update(
                job.request_id,
                status="recognition_failed",
                error_code="upstream",
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            await self._set_terminal_status(
                job,
                "Не удалось распознать вино из-за временной ошибки. "
                "Фотография сохранена для проверки.",
            )
            return

        with self._timed_step(job, "candidate_storage"):
            self._services.repository.replace_candidates(
                job.request_id,
                [
                    CandidateRecord(
                        candidate.rank,
                        candidate.slug,
                        candidate.score,
                        wine_card(candidate.wine),
                    )
                    for candidate in result.candidates
                ],
            )

        confident = is_confident(
            result,
            min_score=self._services.settings.match_min_score,
            min_margin=self._services.settings.match_min_margin,
        )
        if not confident:
            # An empty candidate list means that the matcher found no wine.
            top = result.top if result.candidates else None
            self._services.repository.update(
                job.request_id,
                recognition_slug=top.slug if top else None,
                recognition_name=top.wine.name if top else None,
                recognition_page_url=top.wine.page_url if top else None,
                recognition_score=top.score if top else None,
                recognition_margin=result.margin if top else None,
                matcher_pipeline=result.pipeline,
                status="abstained",
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            await self._set_terminal_status(
                job,
                "Не уверен, что правильно распознал вино.\n\n"
                "Сфотографируйте бутылку целиком и сделайте отдельный чёткий снимок этикетки.",
            )
            return

        wine = result.top.wine
        self._services.repository.update(
            job.request_id,
            recognition_slug=wine.slug,
            recognition_name=wine.name,
            recognition_page_url=wine.page_url,
            recognition_score=result.top.score,
            recognition_margin=result.margin,
            matcher_pipeline=result.pipeline,
            status="recognized",
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        with self._timed_step(job, "result_delivery"):
            await self._send_result(job, wine, body)

    @contextmanager
    def _timed_step(self, job: PhotoJob, step: str):
        started_at_ms = time.time_ns() // 1_000_000
        started = time.monotonic()
        outcome = "ok"
        try:
            yield
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except BaseException:
            outcome = "failed"
            raise
        finally:
            self._record_step_timing(
                job,
                step=step,
                started_at_ms=started_at_ms,
                duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                outcome=outcome,
            )

    def _record_step_timing(
        self,
        job: PhotoJob,
        *,
        step: str,
        started_at_ms: int,
        duration_ms: int,
        outcome: str,
    ) -> None:
        try:
            self._services.repository.record_step_timing(
                request_id=job.request_id,
                step=step,
                started_at_ms=started_at_ms,
                duration_ms=duration_ms,
                outcome=outcome,
            )
        except Exception:
            LOG.exception(
                "Request step timing storage failed request_id=%s step=%s",
                job.request_id,
                step,
            )
            return
        LOG.info(
            "Request step request_id=%s step=%s duration_ms=%s outcome=%s",
            job.request_id,
            step,
            duration_ms,
            outcome,
        )

    def _save_artifacts(
        self,
        job: PhotoJob,
        artifacts: list[GeneratedArtifact],
        *,
        replace: bool = False,
    ) -> None:
        rows = persist_artifacts(
            self._services.artifact_store,
            request_id=job.request_id,
            received_at=job.received_at,
            artifacts=artifacts,
        )
        now = int(time.time())
        if replace:
            self._services.repository.replace_artifacts(job.request_id, rows, now)
        else:
            self._services.repository.upsert_artifacts(job.request_id, rows, now)

    async def _send_rejection(self, job: PhotoJob) -> None:
        if not job.delivery_enabled:
            return
        try:
            await self._bot.send_photo(
                chat_id=job.chat_id,
                photo=BufferedInputFile(
                    self._services.rejection_image,
                    filename="content-rejected.png",
                ),
                caption=CONTENT_REJECTED_TEXT,
                reply_markup=moderation_appeal_keyboard(job.request_id),
                reply_parameters=ReplyParameters(
                    message_id=job.source_message_id,
                    allow_sending_without_reply=True,
                ),
            )
        except Exception:
            LOG.exception(
                "Telegram rejection illustration failed",
                extra={"request_id": job.request_id},
            )
            await self._set_terminal_status(
                job,
                CONTENT_REJECTED_TEXT,
                reply_markup=moderation_appeal_keyboard(job.request_id),
            )
            return

        await self._finish_status(job)

    async def _send_result(self, job: PhotoJob, wine: Wine, submitted_body: bytes) -> None:
        caption = format_result_caption(wine)
        feedback_markup = (
            result_feedback_keyboard(job.request_id, wine.page_url)
            if job.feedback_enabled
            else InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Открыть страницу вина", url=wine.page_url)]
                ]
            )
        )
        image: bytes | None = None
        if wine.image_url:
            try:
                image = await self._services.image_loader.fetch(wine.image_url)
            except CatalogImageUnavailable:
                LOG.warning("Catalog image unavailable", extra={"request_id": job.request_id})
        if image is None:
            try:
                image = normalize_result_photo(submitted_body)
            except CatalogImageUnavailable:
                LOG.exception("Submitted result image is invalid", extra={"request_id": job.request_id})

        if image is None:
            await self._set_status(
                job,
                caption,
                disable_link_preview=True,
                reply_markup=feedback_markup,
            )
            return

        try:
            with self._timed_step(job, "artifact_result"):
                self._save_artifacts(job, [result_artifact(image)])
        except Exception:
            LOG.exception(
                "Result artifact generation failed",
                extra={"request_id": job.request_id},
            )

        if not job.delivery_enabled:
            return

        try:
            await self._bot.send_photo(
                chat_id=job.chat_id,
                photo=BufferedInputFile(image, filename="wine-result.jpg"),
                caption=caption,
                reply_parameters=ReplyParameters(
                    message_id=job.source_message_id,
                    allow_sending_without_reply=True,
                ),
                reply_markup=feedback_markup,
            )
        except Exception:
            LOG.exception("Telegram result photo failed", extra={"request_id": job.request_id})
            await self._set_status(
                job,
                caption,
                disable_link_preview=True,
                reply_markup=feedback_markup,
            )
            return

        await self._finish_status(job, preserve_album=True)

    async def _finish_status(self, job: PhotoJob, *, preserve_album: bool = False) -> None:
        if not job.delivery_enabled:
            return
        if job.status_message_id is None:
            return
        if job.keep_status and preserve_album:
            await self._set_status(job, "Результаты альбома отправляются по мере готовности.")
            return
        try:
            await self._bot.delete_message(job.chat_id, job.status_message_id)
            job.status_message_id = None
        except Exception:
            LOG.exception("Telegram status removal failed", extra={"request_id": job.request_id})
            await self._set_status(job, "Готово.")

    async def _set_terminal_status(
        self,
        job: PhotoJob,
        text: str,
        *,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        if not job.delivery_enabled:
            return
        if job.status_enabled:
            await self._set_status(job, text, reply_markup=reply_markup)
            return
        try:
            await self._bot.send_message(
                job.chat_id,
                text,
                reply_markup=reply_markup,
                reply_parameters=ReplyParameters(
                    message_id=job.source_message_id,
                    allow_sending_without_reply=True,
                ),
            )
        except Exception:
            LOG.exception(
                "Telegram terminal status failed",
                extra={"request_id": job.request_id},
            )

    async def _set_status(
        self,
        job: PhotoJob,
        text: str,
        *,
        disable_link_preview: bool = False,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        if not job.delivery_enabled:
            return
        options = (
            LinkPreviewOptions(is_disabled=True) if disable_link_preview else None
        )
        if not job.status_enabled:
            return
        try:
            if job.status_message_id is None:
                message = await self._bot.send_message(
                    job.chat_id,
                    text,
                    link_preview_options=options,
                    reply_markup=reply_markup,
                )
                job.status_message_id = message.message_id
                return
            await self._bot.edit_message_text(
                text,
                chat_id=job.chat_id,
                message_id=job.status_message_id,
                link_preview_options=options,
                reply_markup=reply_markup,
            )
        except Exception:
            LOG.exception("Telegram status update failed", extra={"request_id": job.request_id})


def _minutes(seconds: int) -> int:
    return max(1, (seconds + 59) // 60)


def _queue_receipt_text(*, album: bool, position: int, wait_seconds: int) -> str:
    subject = (
        "Фотографии приняты и поставлены"
        if album
        else "Фотография принята и поставлена"
    )
    if wait_seconds <= 0:
        wait = "обработка начнётся сразу"
    elif wait_seconds < 60:
        wait = f"примерное ожидание: около {wait_seconds} сек."
    else:
        wait = f"примерное ожидание: около {_minutes(wait_seconds)} мин."
    return f"{subject} в очередь.\nПозиция: {position}; {wait}."


MOSCOW_TIME = ZoneInfo("Europe/Moscow")
RUSSIAN_MONTHS = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)
USERS_PAGE_SIZE = 20
TELEGRAM_TEXT_LIMIT = 3900


def _is_admin(message: Message, services: Services) -> bool:
    return bool(
        message.from_user is not None
        and message.from_user.id == services.settings.admin_user_id
        and message.chat.id == services.settings.admin_user_id
    )


def _format_timestamp(timestamp: int | None) -> str:
    if timestamp is None:
        return "—"
    value = datetime.fromtimestamp(timestamp, tz=MOSCOW_TIME)
    return (
        f"{value.day} {RUSSIAN_MONTHS[value.month]} {value.year}, "
        f"{value:%H:%M:%S} МСК"
    )


def _display_username(username: str | None) -> str:
    return f"@{escape(username)}" if username else "—"


def _display_name(first_name: str | None, last_name: str | None) -> str:
    name = " ".join(part for part in (first_name, last_name) if part).strip()
    if not name:
        return "—"
    if len(name) > 80:
        name = f"{name[:79]}…"
    return escape(name)


def _format_user_summary(index: int, user: UserSummary, rate_limit: int) -> str:
    return (
        f"<b>{index}. Telegram:</b> {_display_username(user.username)}\n"
        f"<b>Имя:</b> {_display_name(user.first_name, user.last_name)}\n"
        f"<b>User ID:</b> <code>{user.user_id}</code>\n"
        f"<b>Запросов:</b> {user.total_requests} · за час: "
        f"{user.window_requests}/{rate_limit}\n"
        f"<b>Последний запрос:</b> {_format_timestamp(user.last_request_at)}"
    )


async def _answer_user_blocks(message: Message, header: str, blocks: list[str]) -> None:
    current = header
    for block in blocks:
        candidate = f"{current}\n\n{block}"
        if len(candidate) > TELEGRAM_TEXT_LIMIT and current != header:
            await message.answer(current)
            current = f"{header}\n\n{block}"
        else:
            current = candidate
    await message.answer(current)


async def handle_stats_command(
    message: Message,
    services: Services,
    work_queue: WorkQueue[PhotoJob],
    *,
    now: int | None = None,
) -> None:
    if message.from_user is None:
        return
    current_time = int(time.time()) if now is None else now
    is_admin = _is_admin(message, services)
    value = services.repository.stats(
        message.from_user.id,
        current_time,
        services.settings.rate_window_seconds,
        include_all=is_admin,
    )
    remaining = max(0, services.settings.rate_limit - value.user_window)
    if not is_admin:
        await message.answer(
            "<b>Ваша статистика</b>\n\n"
            f"Всего фотографий: {value.total}\n"
            f"За последние 24 часа: {value.last_day}\n"
            f"Распознано: {value.recognized}\n"
            f"Не уверен: {value.abstained}\n"
            f"Ошибок обработки: {value.failed}\n"
            f"Отклонено фильтром: {value.quarantined}\n\n"
            f"Запросы за час: {value.user_window}/{services.settings.rate_limit}\n"
            f"Осталось: {remaining}"
        )
        return
    await message.answer(
        "<b>Общая статистика</b>\n\n"
        f"Всего фотографий: {value.total}\n"
        f"За последние 24 часа: {value.last_day}\n"
        f"Участников: {value.users}\n"
        f"Распознано: {value.recognized}\n"
        f"Не уверен: {value.abstained}\n"
        f"Ошибок обработки: {value.failed}\n"
        f"Отклонено фильтром: {value.quarantined}\n\n"
        f"В очереди: {work_queue.waiting}\n"
        f"Обрабатывается: {work_queue.active}\n\n"
        f"Ваши запросы за час: {value.user_window}/{services.settings.rate_limit}\n"
        f"Осталось: {remaining}"
    )


async def handle_users_command(
    message: Message,
    command: CommandObject,
    services: Services,
    *,
    now: int | None = None,
) -> None:
    if not _is_admin(message, services):
        await message.answer("Команда доступна только администратору.")
        return
    raw_page = (command.args or "").strip()
    if raw_page:
        try:
            page = int(raw_page)
        except ValueError:
            page = 0
    else:
        page = 1
    if page <= 0:
        await message.answer("Использование: /users [номер страницы]")
        return
    current_time = int(time.time()) if now is None else now
    users, total = services.repository.list_users(
        page=page,
        page_size=USERS_PAGE_SIZE,
        now=current_time,
        window_seconds=services.settings.rate_window_seconds,
    )
    page_count = max(1, (total + USERS_PAGE_SIZE - 1) // USERS_PAGE_SIZE)
    if page > page_count:
        await message.answer(f"Страница не найдена. Доступно страниц: {page_count}.")
        return
    if not users:
        await message.answer("Пользователей пока нет.")
        return
    header = f"<b>Пользователи</b> · страница {page}/{page_count} · всего {total}"
    offset = (page - 1) * USERS_PAGE_SIZE
    blocks = [
        _format_user_summary(offset + index, user, services.settings.rate_limit)
        for index, user in enumerate(users, start=1)
    ]
    await _answer_user_blocks(message, header, blocks)


def _message_user_identity(message: Message) -> UserIdentity | None:
    if message.from_user is None:
        return None
    return UserIdentity(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )


async def handle_reset_limit_command(
    message: Message,
    command: CommandObject,
    services: Services,
    *,
    now: int | None = None,
) -> None:
    if not _is_admin(message, services):
        await message.answer("Команда доступна только администратору.")
        return
    raw_target = (command.args or "").strip()
    target: UserIdentity | None
    if not raw_target:
        target = services.repository.user_by_id(services.settings.admin_user_id)
        if target is None:
            target = _message_user_identity(message)
    elif raw_target.startswith("@") and len(raw_target) > 1 and " " not in raw_target:
        target = services.repository.user_by_username(raw_target[1:])
    elif raw_target.isdecimal() and int(raw_target) > 0:
        target_id = int(raw_target)
        target = services.repository.user_by_id(target_id)
        if target is None and target_id == services.settings.admin_user_id:
            target = _message_user_identity(message)
    else:
        await message.answer("Использование: /reset_limit [user_id или @username]")
        return
    if target is None:
        await message.answer("Пользователь не найден.")
        return
    current_time = int(time.time()) if now is None else now
    reset_count = services.repository.reset_rate_limit(
        target.user_id,
        current_time,
        services.settings.rate_window_seconds,
    )
    await message.answer(
        f"Лимит пользователя {_display_username(target.username)} "
        f"(ID <code>{target.user_id}</code>) сброшен.\n"
        f"Исключено из текущего окна: {reset_count}."
    )


async def enqueue_photo_message(
    message: Message,
    services: Services,
    work_queue: WorkQueue[PhotoJob],
    album_receipts: AlbumReceiptTracker,
) -> None:
    if message.from_user is None or not message.photo:
        return
    if services.repository.age_status(message.from_user.id) != "adult":
        await message.reply(
            AGE_GATE_TEXT,
            reply_markup=AGE_CONFIRMATION_KEYBOARD,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        return
    if work_queue.at_capacity:
        await message.reply(
            "Сейчас очередь заполнена. Фотография не учтена в лимите. Попробуйте позже."
        )
        return
    photo = message.photo[-1]
    now = int(time.time())
    reservation = services.repository.reserve(
        chat_id=message.chat.id,
        message_id=message.message_id,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        file_id=photo.file_id,
        file_unique_id=photo.file_unique_id,
        now=now,
        limit=services.settings.rate_limit,
        window_seconds=services.settings.rate_window_seconds,
        feedback_enabled=message.media_group_id is None,
    )
    if reservation.duplicate:
        return
    if not reservation.allowed or reservation.request_id is None:
        await message.reply(
            f"Лимит — {services.settings.rate_limit} фотографий за один час. "
            f"Попробуйте снова примерно через {_minutes(reservation.retry_after_seconds)} мин."
        )
        return

    request_id = reservation.request_id
    media_group_id = message.media_group_id
    album_receipt_key = (
        f"{message.chat.id}:{media_group_id}" if media_group_id is not None else None
    )
    claimed_album_receipt = bool(
        album_receipt_key and album_receipts.claim(album_receipt_key)
    )
    position = work_queue.next_position
    wait_seconds = work_queue.estimate_wait_seconds(position)
    status = None
    try:
        services.repository.update(
            request_id,
            status="queued",
            error_code=None,
        )
        if media_group_id is None:
            status = await message.reply(
                _queue_receipt_text(
                    album=False,
                    position=position,
                    wait_seconds=wait_seconds,
                )
            )
        elif claimed_album_receipt:
            status = await message.reply(
                _queue_receipt_text(
                    album=True,
                    position=position,
                    wait_seconds=wait_seconds,
                )
            )
    except Exception:
        if album_receipt_key and claimed_album_receipt:
            album_receipts.release(album_receipt_key)
        services.repository.update(
            request_id, status="queue_rejected", error_code="telegram_status"
        )
        raise

    job = PhotoJob(
        request_id=request_id,
        chat_id=message.chat.id,
        source_message_id=message.message_id,
        received_at=now,
        file_id=photo.file_id,
        status_message_id=status.message_id if status is not None else None,
        feedback_enabled=media_group_id is None,
        status_enabled=media_group_id is None or claimed_album_receipt,
        keep_status=claimed_album_receipt,
    )
    try:
        work_queue.submit(job)
    except (QueueCapacityError, QueueClosedError):
        if album_receipt_key and claimed_album_receipt:
            album_receipts.release(album_receipt_key)
        services.repository.update(
            request_id, status="queue_rejected", error_code="queue_capacity"
        )
        text = "Сейчас очередь заполнена. Фотография не учтена в лимите. Попробуйте позже."
        if status is None:
            await message.reply(text)
        else:
            await status.edit_text(text)


async def handle_age_confirmation(callback: CallbackQuery, services: Services) -> None:
    if callback.data not in {"age:adult", "age:minor"}:
        await callback.answer()
        return
    status = callback.data.removeprefix("age:")
    user = callback.from_user
    services.repository.set_age_status(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        status=status,
        now=int(time.time()),
    )
    if status == "adult":
        response = START_CONFIRMED_TEXT
        notification = "Возраст подтверждён."
    else:
        response = MINOR_TEXT
        notification = "Бот доступен только пользователям старше 18 лет."
    await callback.answer(notification)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            response,
            reply_markup=None,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )


async def handle_result_feedback(callback: CallbackQuery, services: Services) -> None:
    data = callback.data or ""
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "feedback" or parts[1] not in {"yes", "no"}:
        await callback.answer("Некорректная оценка.")
        return
    request_id = parts[2]
    result = services.repository.save_feedback(
        request_id=request_id,
        user_id=callback.from_user.id,
        matched=parts[1] == "yes",
        now=int(time.time()),
    )
    if result == "unavailable":
        await callback.answer(
            "Эта оценка недоступна.",
            show_alert=True,
        )
        return
    already_saved = result == "already_saved"
    if parts[1] == "no":
        alternatives = [
            (candidate.rank, candidate_wine(candidate))
            for candidate in services.repository.candidates(request_id)
            if 2 <= candidate.rank <= 4
        ]
        if not alternatives:
            await callback.answer(
                "Оценка сохранена, но альтернативы для этого результата недоступны.",
                show_alert=True,
            )
            return
        await callback.answer(
            "Оценка уже сохранена. Показываю варианты."
            if already_saved
            else "Спасибо! Выберите возможный вариант.",
        )
        message = callback.message
        if isinstance(message, Message):
            markup = alternative_keyboard(request_id, alternatives)
            try:
                await message.edit_reply_markup(reply_markup=markup)
            except Exception:
                LOG.exception(
                    "Alternative keyboard update failed",
                    extra={"request_id": request_id},
                )
                try:
                    await message.answer("Возможные варианты:", reply_markup=markup)
                except Exception:
                    LOG.exception(
                        "Alternative keyboard fallback failed",
                        extra={"request_id": request_id},
                    )
        return

    await callback.answer(
        "Оценка уже сохранена." if already_saved else "Спасибо! Оценка сохранена."
    )
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            LOG.exception(
                "Feedback keyboard removal failed",
                extra={"request_id": request_id},
            )


async def handle_alternative_feedback(callback: CallbackQuery, services: Services) -> None:
    data = callback.data or ""
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "alternative" or not parts[1].isdigit():
        await callback.answer("Некорректный вариант.")
        return
    rank = int(parts[1])
    request_id = parts[2]
    result = services.repository.save_alternative_feedback(
        request_id=request_id,
        user_id=callback.from_user.id,
        rank=rank,
        now=int(time.time()),
    )
    if result == "unavailable":
        await callback.answer("Этот вариант недоступен.", show_alert=True)
        return
    if result == "already_saved":
        await callback.answer("Ответ уже сохранён.")
        return
    await callback.answer("Спасибо! Ответ сохранён.")
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            LOG.exception(
                "Alternative keyboard removal failed",
                extra={"request_id": request_id},
            )


async def handle_moderation_appeal(callback: CallbackQuery, services: Services) -> None:
    data = callback.data or ""
    prefix = "moderation_error:"
    if not data.startswith(prefix) or not data.removeprefix(prefix):
        await callback.answer("Некорректное обращение.")
        return
    request_id = data.removeprefix(prefix)
    result = services.repository.save_moderation_appeal(
        request_id=request_id,
        user_id=callback.from_user.id,
        now=int(time.time()),
    )
    if result == "unavailable":
        await callback.answer("Это обращение недоступно.", show_alert=True)
        return
    if result == "already_saved":
        await callback.answer("Обращение уже сохранено.")
        return
    await callback.answer("Спасибо! Проверим срабатывание фильтра.")
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            LOG.exception(
                "Moderation appeal keyboard removal failed",
                extra={"request_id": request_id},
            )


def build_router(services: Services, work_queue: WorkQueue[PhotoJob]) -> Router:
    router = Router()
    album_receipts = AlbumReceiptTracker()

    @router.message(CommandStart())
    async def start(message: Message, command: CommandObject) -> None:
        if command.args == "privacy":
            await message.answer(PRIVACY_TEXT)
            return
        if message.from_user is None:
            return
        if services.repository.age_status(message.from_user.id) != "adult":
            await message.answer(
                AGE_GATE_TEXT,
                reply_markup=AGE_CONFIRMATION_KEYBOARD,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
            return
        await message.answer(
            START_CONFIRMED_TEXT,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

    @router.callback_query(F.data.startswith("age:"))
    async def age_confirmation(callback: CallbackQuery) -> None:
        await handle_age_confirmation(callback, services)

    @router.callback_query(F.data.startswith("feedback:"))
    async def result_feedback(callback: CallbackQuery) -> None:
        await handle_result_feedback(callback, services)

    @router.callback_query(F.data.startswith("alternative:"))
    async def alternative_feedback(callback: CallbackQuery) -> None:
        await handle_alternative_feedback(callback, services)

    @router.callback_query(F.data.startswith("moderation_error:"))
    async def moderation_appeal(callback: CallbackQuery) -> None:
        await handle_moderation_appeal(callback, services)

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        await message.answer(HELP_TEXT)

    @router.message(Command("privacy"))
    async def privacy(message: Message) -> None:
        await message.answer(PRIVACY_TEXT)

    @router.message(Command("stats"))
    async def stats(message: Message) -> None:
        await handle_stats_command(message, services, work_queue)

    @router.message(Command("users"))
    async def users(message: Message, command: CommandObject) -> None:
        await handle_users_command(message, command, services)

    @router.message(Command("reset_limit"))
    async def reset_limit(message: Message, command: CommandObject) -> None:
        await handle_reset_limit_command(message, command, services)

    @router.message(F.photo)
    async def photo(message: Message) -> None:
        await enqueue_photo_message(message, services, work_queue, album_receipts)

    @router.message()
    async def fallback(message: Message) -> None:
        await message.answer("Пришлите фотографию бутылки или этикетки. Помощь: /help")

    return router


def candidate_wine(candidate: CandidateRecord) -> Wine:
    """Return the stored card of a candidate, or a minimal card for an old request."""
    if candidate.card is not None:
        try:
            return wine_from_card(candidate.slug, candidate.card)
        except (TypeError, ValueError):
            LOG.warning("Stored wine card is invalid slug=%s", candidate.slug)
    return unknown_wine(candidate.slug)


def _wine_api_payload(wine: Wine) -> dict[str, object]:
    payload: dict[str, object] = {
        "slug": wine.slug,
        "name": wine.name,
        "page_url": wine.page_url,
        "producer": wine.producer,
        "category": wine.category,
        "color": wine.color,
        "sugar": wine.sugar,
        "grapes": wine.grapes,
        "image_url": wine.image_url,
    }
    if wine.qr_urls:
        payload["qr_urls"] = list(wine.qr_urls)
    return payload


def _moderation_api_payload(record: AdminRequestRecord) -> dict[str, object]:
    bypassed = record.moderation_category == "disabled"
    return {
        "performed": not bypassed and record.moderation_safe is not None,
        "bypassed": bypassed,
        "safe": None if bypassed else record.moderation_safe,
        "category": record.moderation_category,
        "confidence": record.moderation_confidence,
        "scores": {} if bypassed else _moderation_scores(record.moderation_reason),
    }


def _moderation_scores(reason: str | None) -> dict[str, float] | None:
    if not reason:
        return None
    scores: dict[str, float] = {}
    try:
        for item in reason.split(","):
            policy, raw_score = item.split("=", 1)
            scores[policy] = float(raw_score)
    except (TypeError, ValueError):
        return None
    return scores


def _http_result_payload(services: Services, request_id: str) -> dict[str, object]:
    record = services.repository.admin_request(request_id)
    if record is None:
        raise RuntimeError("HTTP API request record is missing")
    candidate_wines = [
        (item, candidate_wine(item)) for item in services.repository.candidates(request_id)
    ]
    candidates = [
        {
            "rank": item.rank,
            "slug": item.slug,
            "score": item.score,
            "wine": _wine_api_payload(wine),
        }
        for item, wine in candidate_wines
    ]
    selected_wine = None
    if record.recognition_slug:
        selected_wine = _wine_api_payload(
            next(
                (wine for item, wine in candidate_wines if item.slug == record.recognition_slug),
                unknown_wine(record.recognition_slug),
            )
        )
    timings = [
        {
            "step": item.step,
            "started_at_ms": item.started_at_ms,
            "duration_ms": item.duration_ms,
            "outcome": item.outcome,
        }
        for item in services.repository.step_timings(request_id)
    ]
    return {
        "request_id": request_id,
        "source": record.request_source,
        "status": record.status,
        "error_code": record.error_code,
        "duration_ms": record.duration_ms,
        "matcher_pipeline": record.matcher_pipeline,
        "moderation": _moderation_api_payload(record),
        "quality": {
            "acceptable": record.quality_acceptable,
            "issues": (
                record.quality_issues.split(",")
                if record.quality_issues
                else []
            ),
            "blur_variance": record.quality_blur_variance,
            "glare_ratio": record.quality_glare_ratio,
            "bottle_area_ratio": record.quality_bottle_area_ratio,
            "label_area_ratio": record.quality_label_area_ratio,
        },
        "recognition": {
            "confident": record.status == "recognized",
            "score": record.recognition_score,
            "margin": record.recognition_margin,
            "wine": selected_wine,
            "candidates": candidates,
        },
        "timings": timings,
        "notice": (
            "Справочно · не предложение о продаже. "
            "18+ · Чрезмерное употребление алкоголя вредит вашему здоровью."
        ),
    }


def _http_result_status(status: str) -> int:
    if status in {"recognized", "abstained", "quarantined"}:
        return 200
    if status == "invalid_image":
        return 422
    if status == "moderation_failed":
        return 503
    if status == "recognition_failed":
        return 502
    return 500


async def submit_http_image(
    services: Services,
    work_queue: WorkQueue[PhotoJob],
    body: bytes,
) -> HttpRecognitionResult:
    if work_queue.at_capacity:
        raise HttpQueueFull("The recognition queue is full")
    now = int(time.time())
    request_id = services.repository.create_api_request(now=now)
    completion = asyncio.get_running_loop().create_future()
    job = PhotoJob(
        request_id=request_id,
        chat_id=0,
        source_message_id=0,
        received_at=now,
        file_id="",
        status_message_id=None,
        feedback_enabled=False,
        status_enabled=False,
        image_body=body,
        delivery_enabled=False,
        completion=completion,
    )
    services.repository.update(request_id, status="queued", error_code=None)
    try:
        work_queue.submit(job)
    except QueueCapacityError as exc:
        services.repository.update(
            request_id,
            status="queue_rejected",
            error_code="capacity",
        )
        raise HttpQueueFull("The recognition queue is full") from exc
    except QueueClosedError as exc:
        services.repository.update(
            request_id,
            status="queue_rejected",
            error_code="unavailable",
        )
        raise HttpQueueUnavailable("The recognition queue is unavailable") from exc

    await asyncio.shield(completion)
    started_at_ms = time.time_ns() // 1_000_000
    started = time.monotonic()
    payload = _http_result_payload(services, request_id)
    duration_ms = max(0, int((time.monotonic() - started) * 1000))
    services.repository.record_step_timing(
        request_id=request_id,
        step="http_response_build",
        started_at_ms=started_at_ms,
        duration_ms=duration_ms,
        outcome="ok",
    )
    payload["timings"] = [
        {
            "step": item.step,
            "started_at_ms": item.started_at_ms,
            "duration_ms": item.duration_ms,
            "outcome": item.outcome,
        }
        for item in services.repository.step_timings(request_id)
    ]
    return HttpRecognitionResult(
        status_code=_http_result_status(str(payload["status"])),
        body=payload,
    )


async def _endpoint_reachable(endpoint: str, *, timeout: float = 1.5) -> bool:
    parts = urlsplit(endpoint)
    host = parts.hostname
    if host is None:
        return False
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                host,
                port,
            ),
            timeout=timeout,
        )
    except (OSError, TimeoutError):
        return False
    del reader
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        return False
    return True


async def service_readiness(
    settings: Settings,
    repository: Repository,
    work_queue: WorkQueue[PhotoJob],
) -> dict[str, bool]:
    endpoint_names = ["sam3", "matcher"]
    endpoints = [settings.sam3_endpoint, settings.matcher_endpoint]
    if settings.moderation_endpoint is not None:
        endpoint_names.insert(0, "moderation")
        endpoints.insert(0, settings.moderation_endpoint)
    endpoint_results = await asyncio.gather(
        *(_endpoint_reachable(endpoint) for endpoint in endpoints)
    )
    return {
        "database": repository.is_healthy(),
        "queue": work_queue.accepting,
        **dict(zip(endpoint_names, endpoint_results, strict=True)),
    }


def enforce_data_retention(settings: Settings, repository: Repository) -> None:
    cutoff = int(time.time()) - settings.data_retention_days * 86400
    result = purge_expired_data(repository, settings.data_root, cutoff=cutoff)
    LOG.info(
        "Data retention completed requests=%s users=%s files=%s",
        result.requests,
        result.users,
        result.files,
    )


async def data_retention_loop(
    settings: Settings,
    repository: Repository,
    *,
    interval_seconds: float = 86400,
) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        await asyncio.to_thread(enforce_data_retention, settings, repository)


def enqueue_admin_retries(
    repository: Repository,
    work_queue: WorkQueue[PhotoJob],
) -> int:
    submitted = 0
    for request in repository.retry_requests():
        if work_queue.at_capacity:
            break
        if not repository.claim_retry_request(request.request_id):
            continue
        job = PhotoJob(
            request_id=request.request_id,
            chat_id=request.chat_id,
            source_message_id=request.message_id,
            received_at=request.received_at,
            file_id=request.file_id,
            status_message_id=None,
            feedback_enabled=request.feedback_enabled,
            status_enabled=True,
        )
        try:
            work_queue.submit(job)
        except (QueueCapacityError, QueueClosedError):
            repository.release_retry_request(request.request_id)
            break
        submitted += 1
    return submitted


async def watch_admin_retries(
    repository: Repository,
    work_queue: WorkQueue[PhotoJob],
    *,
    interval_seconds: float = 2.0,
) -> None:
    if interval_seconds <= 0:
        raise ValueError("retry watcher interval must be positive")
    while True:
        submitted = enqueue_admin_retries(repository, work_queue)
        if submitted:
            LOG.info("Submitted administration retries count=%s", submitted)
        await asyncio.sleep(interval_seconds)


async def sync_profile(bot: Bot, admin_user_id: int) -> None:
    await bot.set_my_short_description(short_description=SHORT_DESCRIPTION)
    await bot.set_my_description(description=DESCRIPTION)
    await bot.set_my_commands(COMMANDS)
    await bot.set_my_commands(
        ADMIN_COMMANDS,
        scope=BotCommandScopeChat(chat_id=admin_user_id),
    )


async def run() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    rejection_image = settings.rejection_image_file.read_bytes()
    if not rejection_image:
        raise RuntimeError("BOT_REJECTION_IMAGE is empty")
    repository = Repository(settings.database_file)
    store = ImageStore(settings.data_root)
    artifact_store = ArtifactStore(settings.data_root)
    client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
    )
    moderator = make_moderator(
        settings.moderation_enabled,
        settings.moderation_endpoint,
        client,
    )
    if not settings.moderation_enabled:
        LOG.warning("Image moderation is disabled by configuration")
    quality_inspector = QualityInspector(
        settings.sam3_endpoint,
        client,
        QualityThresholds(
            blur_min_variance=settings.quality_blur_min_variance,
            glare_max_ratio=settings.quality_glare_max_ratio,
            bottle_min_area_ratio=settings.quality_bottle_min_area_ratio,
            label_min_area_ratio=settings.quality_label_min_area_ratio,
        ),
    )
    matcher = Matcher(settings.matcher_endpoint, client)
    image_loader = CatalogImageLoader(client)
    services = Services(
        settings,
        repository,
        store,
        artifact_store,
        moderator,
        quality_inspector,
        matcher,
        image_loader,
        rejection_image,
    )
    enforce_data_retention(settings, repository)

    bot = Bot(
        token=settings.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    processor = PhotoProcessor(services, bot)
    work_queue = WorkQueue(
        processor.process,
        worker_count=settings.queue_workers,
        capacity=settings.queue_capacity,
        initial_job_seconds=settings.queue_estimate_seconds,
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(services, work_queue))
    http_api = create_http_api_app(
        allowed_networks=settings.http_api_allowed_networks,
        max_image_bytes=settings.max_image_bytes,
        api_token=settings.http_api_token,
        rate_limit=settings.http_api_rate_limit,
        rate_window_seconds=settings.http_api_rate_window_seconds,
        max_in_flight=settings.http_api_max_in_flight,
        recognize=lambda body: submit_http_image(services, work_queue, body),
        readiness=lambda: service_readiness(settings, repository, work_queue),
    )
    api_server = uvicorn.Server(
        uvicorn.Config(
            http_api,
            host=settings.http_api_host,
            port=settings.http_api_port,
            log_level=settings.log_level.lower(),
            proxy_headers=False,
            lifespan="off",
        )
    )
    retry_watcher: asyncio.Task[None] | None = None
    api_task: asyncio.Task[None] | None = None
    polling_task: asyncio.Task[None] | None = None
    retention_task: asyncio.Task[None] | None = None
    try:
        if settings.sync_profile:
            await sync_profile(bot, settings.admin_user_id)
        await work_queue.start()
        interrupted_api_requests = repository.fail_interrupted_api_requests()
        pending = repository.pending_requests()
        for request in pending:
            work_queue.submit(
                PhotoJob(
                    request_id=request.request_id,
                    chat_id=request.chat_id,
                    source_message_id=request.message_id,
                    received_at=request.received_at,
                    file_id=request.file_id,
                    status_message_id=None,
                    feedback_enabled=request.feedback_enabled,
                    status_enabled=request.feedback_enabled,
                ),
                restore=True,
            )
        retry_watcher = asyncio.create_task(
            watch_admin_retries(repository, work_queue),
            name="admin-retry-watcher",
        )
        retention_task = asyncio.create_task(
            data_retention_loop(settings, repository),
            name="data-retention",
        )
        api_task = asyncio.create_task(api_server.serve(), name="recognition-http-api")
        polling_task = asyncio.create_task(
            dispatcher.start_polling(
                bot,
                allowed_updates=dispatcher.resolve_used_update_types(),
                handle_as_tasks=False,
                close_bot_session=False,
            ),
            name="telegram-polling",
        )
        LOG.info(
            "Bot polling and HTTP API started",
            extra={
                "matcher_endpoint": settings.matcher_endpoint,
                "moderation_enabled": settings.moderation_enabled,
                "queue_workers": settings.queue_workers,
                "queue_capacity": settings.queue_capacity,
                "restored_jobs": len(pending),
                "interrupted_api_requests": interrupted_api_requests,
                "http_api_host": settings.http_api_host,
                "http_api_port": settings.http_api_port,
            },
        )
        done, _ = await asyncio.wait(
            {api_task, polling_task, retention_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if api_task in done:
            api_task.result()
            if not polling_task.done():
                raise RuntimeError("Recognition HTTP API stopped unexpectedly")
        if polling_task in done:
            await polling_task
        if retention_task in done:
            retention_task.result()
            raise RuntimeError("Data retention task stopped unexpectedly")
    finally:
        api_server.should_exit = True
        if polling_task is not None and not polling_task.done():
            polling_task.cancel()
        if api_task is not None and not api_task.done():
            await asyncio.gather(api_task, return_exceptions=True)
        if polling_task is not None:
            await asyncio.gather(polling_task, return_exceptions=True)
        if retry_watcher is not None:
            retry_watcher.cancel()
            await asyncio.gather(retry_watcher, return_exceptions=True)
        if retention_task is not None:
            retention_task.cancel()
            await asyncio.gather(retention_task, return_exceptions=True)
        await work_queue.stop()
        await client.aclose()
        await bot.session.close()
        repository.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
