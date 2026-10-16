from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx
import uvicorn

from .config import Settings
from .data_lifecycle import purge_expired_data
from .delivery import Poller, UpdateDispatcher, create_webhook_app
from .fingerprints import difference_hash, perceptual_hash
from .http_api import (
    HttpQueueFull,
    HttpQueueUnavailable,
    HttpRecognitionResult,
    create_http_api_app,
)
from .matcher import Matcher, RecognitionResult, RecognitionUnavailable, is_confident
from .max_api import (
    UPDATE_TYPES,
    MaxApi,
    MediaTooLarge,
    MediaUnavailable,
    callback_button,
    create_ssl_context,
    image_attachment,
    inline_keyboard,
    link_button,
)
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
    AGE_GATE_TEXT,
    COMMANDS,
    HELP_TEXT,
    MINOR_TEXT,
    START_CONFIRMED_TEXT,
    privacy_text,
)
from .quality import QualityInspector, QualityThresholds, QualityUnavailable
from .result_card import (
    CatalogImageLoader,
    CatalogImageUnavailable,
    format_result_caption,
    normalize_result_photo,
)
from .storage import (
    SQLITE_MAX_INTEGER,
    AdminRequestRecord,
    ArtifactStore,
    CandidateRecord,
    ImageStore,
    Repository,
    UserIdentity,
    UserSummary,
)
from .updates import (
    BotStarted,
    CallbackEvent,
    IncomingMessage,
    MaxUser,
    Update,
    is_synthetic_message_id,
    parse_command,
    parse_message,
)
from .wine import Wine, unknown_wine, wine_card, wine_from_card
from .work_queue import QueueCapacityError, QueueClosedError, WorkQueue

LOG = logging.getLogger("chto_za_vino_max_bot")
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
HTML = "html"


class EmbeddedServer(uvicorn.Server):
    """A uvicorn server inside the bot process. The bot handles SIGTERM and SIGINT itself.

    uvicorn replaces the process signal handlers while it serves and raises the signal again
    when it stops. With two servers and the bot loop, that order is not predictable.
    """

    @contextlib.contextmanager
    def capture_signals(self) -> Iterator[None]:
        yield


class SecretRedactingFormatter(logging.Formatter):
    """Remove secret values from the formatted record, including the traceback text."""

    def __init__(self, fmt: str, secrets: tuple[str, ...]) -> None:
        super().__init__(fmt)
        self._secrets = tuple(secret for secret in secrets if secret)

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        for secret in self._secrets:
            text = text.replace(secret, "[REDACTED]")
        return text


AGE_CONFIRMATION_KEYBOARD = inline_keyboard(
    [
        [
            callback_button("Мне есть 18 лет", "age:adult"),
            callback_button("Мне нет 18 лет", "age:minor"),
        ]
    ]
)

CONTENT_REJECTED_TEXT = (
    "Контент признан неподходящим и не передан в распознавание.\n\n"
    "Если фильтр ошибся, сообщите об этом кнопкой ниже."
)
QUEUE_FULL_TEXT = "Сейчас очередь заполнена. Фотография не учтена в лимите. Попробуйте позже."
FALLBACK_TEXT = "Пришлите фотографию бутылки или этикетки. Помощь: /help"
ALTERNATIVES_TEXT = "Возможные варианты:"


def confidence_note(
    result: RecognitionResult,
    *,
    min_score: float,
    min_margin: float,
) -> str:
    if not result.candidates:
        return "Оценка: нет кандидатов"
    return (
        f"Оценка: {result.top.score:.4f} (порог {min_score:g}) · "
        f"отрыв: {result.margin:.4f} (порог {min_margin:g})"
    )


def result_link_keyboard(page_url: str) -> dict[str, object]:
    return inline_keyboard([[link_button("Открыть страницу вина", page_url)]])


def result_feedback_keyboard(request_id: str, page_url: str) -> dict[str, object]:
    return inline_keyboard(
        [
            [link_button("Открыть страницу вина", page_url)],
            [
                callback_button("✅ Совпало", f"feedback:yes:{request_id}"),
                callback_button("❌ Не совпало", f"feedback:no:{request_id}"),
            ],
        ]
    )


def moderation_appeal_keyboard(request_id: str) -> dict[str, object]:
    return inline_keyboard(
        [[callback_button("Сообщить об ошибке фильтра", f"moderation_error:{request_id}")]]
    )


def alternative_keyboard(request_id: str, wines: list[tuple[int, Wine]]) -> dict[str, object]:
    rows = [
        [callback_button(f"{rank}. {wine.name[:48]}", f"alternative:{rank}:{request_id}")]
        for rank, wine in wines
    ]
    rows.append([callback_button("Ничего из этого", f"alternative:0:{request_id}")])
    return inline_keyboard(rows)


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
    source_message_id: str
    received_at: int
    photo_url: str
    status_message_id: str | None = None
    chat_type: str = "dialog"
    user_id: int = 0
    photo_index: int = 0
    photo_id: int | None = None
    photo_source: str = "body"
    feedback_enabled: bool = True
    status_enabled: bool = True
    keep_status: bool = False
    image_body: bytes | None = None
    # An administration retry reads the accepted local copy and moderates it again.
    # The path is taken when the retry enters the queue: processing clears the moderation
    # fields that `Repository.safe_source` needs.
    local_path: str | None = None
    # The first receipt time of the request. A retry keeps the date directory of its files, so
    # retention and user deletion find every copy. None means `received_at`.
    stored_at: int | None = None
    delivery_enabled: bool = True
    completion: asyncio.Future[None] | None = None


class PhotoProcessor:
    def __init__(self, services: Services, api: Any) -> None:
        self._services = services
        self._api = api
        self._rejection_payload: dict[str, object] | None = None
        self._rejection_token: str | None = None

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
            body = await self._read_source(job)
        except InvalidImage:
            self._services.repository.update(
                job.request_id, status="invalid_image", error_code="invalid_size"
            )
            await self._set_terminal_status(
                job, "Не удалось прочитать фотографию. Отправьте другое изображение."
            )
            return
        except Exception:
            LOG.exception("MAX image download failed", extra={"request_id": job.request_id})
            self._services.repository.update(
                job.request_id, status="download_failed", error_code="max"
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
                job.request_id, _storage_time(job), body, moderation.accepted
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
            # An earlier safe attempt of an admin retry left accepted and full-fidelity copies.
            try:
                self._services.store.delete_accepted(job.request_id)
                self._services.artifact_store.delete_request(job.request_id)
            except Exception:
                LOG.exception(
                    "Earlier safe copy removal failed request_id=%s",
                    job.request_id,
                )
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
        admin_note = self._admin_confidence_note(job, result)
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
            text = (
                "Не уверен, что правильно распознал вино.\n\n"
                "Сфотографируйте бутылку целиком и сделайте отдельный чёткий снимок этикетки."
            )
            if admin_note:
                text = f"{text}\n\n{admin_note}"
            await self._set_terminal_status(job, text)
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
            await self._send_result(job, wine, body, admin_note=admin_note)

    async def _read_source(self, job: PhotoJob) -> bytes:
        """Return the image bytes of the job. The job keeps no bytes while it waits."""
        max_bytes = self._services.settings.max_image_bytes
        if job.image_body is not None:
            with self._timed_step(job, "http_input"):
                body = job.image_body
                if not body or len(body) > max_bytes:
                    raise InvalidImage("image size is invalid")
                return body
        if job.local_path is not None:
            try:
                with self._timed_step(job, "accepted_source"):
                    body = self._services.store.read_accepted(job.local_path)
            except (OSError, ValueError):
                LOG.warning(
                    "Accepted copy is unavailable; the image is downloaded again",
                    extra={"request_id": job.request_id},
                )
            else:
                if not body or len(body) > max_bytes:
                    raise InvalidImage("image size is invalid")
                return body
        with self._timed_step(job, "max_download"):
            try:
                body = await self._download(job)
            except MediaTooLarge as exc:
                raise InvalidImage("image size is invalid") from exc
            if not body or len(body) > max_bytes:
                raise InvalidImage("image size is invalid")
            return body

    async def _download(self, job: PhotoJob) -> bytes:
        max_bytes = self._services.settings.max_image_bytes
        try:
            return await self._api.download(job.photo_url, max_bytes=max_bytes)
        except MediaTooLarge:
            raise
        except MediaUnavailable:
            LOG.warning(
                "MAX image download failed; the message is read again",
                extra={"request_id": job.request_id},
            )
        # MAX does not document the lifetime of an attachment URL. Read the message again.
        if is_synthetic_message_id(job.source_message_id):
            raise MediaUnavailable("a forwarded message without its own ID cannot be read again")
        message = parse_message(await self._api.get_message(job.source_message_id))
        if message is None or job.photo_index >= len(message.images):
            raise MediaUnavailable("the source message has no such image")
        image = message.images[job.photo_index]
        if job.photo_id is not None and image.photo_id not in {None, job.photo_id}:
            matches = [item for item in message.images if item.photo_id == job.photo_id]
            if not matches:
                raise MediaUnavailable("the source message has no such image")
            image = matches[0]
        job.photo_url = image.url
        self._services.repository.set_photo_url(job.request_id, image.url)
        return await self._api.download(image.url, max_bytes=max_bytes)

    def _admin_confidence_note(self, job: PhotoJob, result: RecognitionResult) -> str | None:
        """Return the confidence line only for the dialog of the administrator."""
        settings = self._services.settings
        # In MAX, the dialog ID is not the user ID. Check the user and the chat type.
        if job.user_id != settings.admin_user_id or job.chat_type != "dialog":
            return None
        return confidence_note(
            result,
            min_score=settings.match_min_score,
            min_margin=settings.match_min_margin,
        )

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
            received_at=_storage_time(job),
            artifacts=artifacts,
        )
        now = int(time.time())
        if replace:
            self._services.repository.replace_artifacts(job.request_id, rows, now)
        else:
            self._services.repository.upsert_artifacts(job.request_id, rows, now)

    def _remember_message(
        self,
        job: PhotoJob,
        message: dict[str, Any],
        *,
        text: str | None,
        text_format: str | None,
        photo_token: str | None,
    ) -> None:
        """Keep the body of a message with a callback keyboard. A failure is not fatal."""
        message_id = _message_id(message)
        if message_id is None:
            return
        try:
            self._services.repository.record_sent_message(
                message_id=message_id,
                request_id=job.request_id,
                chat_id=job.chat_id,
                text=text,
                text_format=text_format,
                photo_token=photo_token,
                now=int(time.time()),
            )
        except Exception:
            LOG.exception("Sent message storage failed", extra={"request_id": job.request_id})

    async def _rejection_image(self) -> tuple[dict[str, object], str | None]:
        if self._rejection_payload is None:
            self._rejection_payload, self._rejection_token = await self._api.upload_image(
                self._services.rejection_image,
                filename="content-rejected.png",
                content_type="image/png",
            )
        return self._rejection_payload, self._rejection_token

    async def _send_rejection(self, job: PhotoJob) -> None:
        if not job.delivery_enabled:
            return
        keyboard = moderation_appeal_keyboard(job.request_id)
        try:
            payload, token = await self._rejection_image()
            message = await self._api.send_message(
                job.chat_id,
                text=CONTENT_REJECTED_TEXT,
                attachments=[image_attachment(payload), keyboard],
                reply_to=_reply_target(job.source_message_id),
                text_format=HTML,
            )
        except Exception:
            # The cached upload can be invalid. The next rejection uploads the image again.
            self._rejection_payload = None
            self._rejection_token = None
            LOG.exception(
                "MAX rejection illustration failed",
                extra={"request_id": job.request_id},
            )
            await self._set_terminal_status(
                job,
                CONTENT_REJECTED_TEXT,
                reply_markup=keyboard,
            )
            return
        self._remember_message(
            job, message, text=CONTENT_REJECTED_TEXT, text_format=HTML, photo_token=token
        )
        await self._finish_status(job)

    async def _send_result(
        self,
        job: PhotoJob,
        wine: Wine,
        submitted_body: bytes,
        *,
        admin_note: str | None = None,
    ) -> None:
        caption = format_result_caption(wine)
        if admin_note:
            caption = f"{caption}\n\n{admin_note}"
        feedback_markup = (
            result_feedback_keyboard(job.request_id, wine.page_url)
            if job.feedback_enabled
            else result_link_keyboard(wine.page_url)
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
            # A job without a status message replies to the source message instead.
            await self._set_terminal_status(
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
            payload, token = await self._api.upload_image(
                image, filename="wine-result.jpg", content_type="image/jpeg"
            )
            message = await self._api.send_message(
                job.chat_id,
                text=caption,
                attachments=[image_attachment(payload), feedback_markup],
                reply_to=_reply_target(job.source_message_id),
                text_format=HTML,
            )
        except Exception:
            LOG.exception("MAX result photo failed", extra={"request_id": job.request_id})
            await self._set_terminal_status(
                job,
                caption,
                disable_link_preview=True,
                reply_markup=feedback_markup,
            )
            return

        self._remember_message(job, message, text=caption, text_format=HTML, photo_token=token)
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
            await self._api.delete_message(job.chat_id, job.status_message_id)
            job.status_message_id = None
        except Exception:
            LOG.exception("MAX status removal failed", extra={"request_id": job.request_id})
            await self._set_status(job, "Готово.")

    async def _set_terminal_status(
        self,
        job: PhotoJob,
        text: str,
        *,
        disable_link_preview: bool = False,
        reply_markup: dict[str, object] | None = None,
    ) -> None:
        if not job.delivery_enabled:
            return
        if job.status_enabled:
            await self._set_status(
                job,
                text,
                disable_link_preview=disable_link_preview,
                reply_markup=reply_markup,
            )
            return
        try:
            message = await self._api.send_message(
                job.chat_id,
                text=text,
                attachments=[reply_markup] if reply_markup else None,
                reply_to=_reply_target(job.source_message_id),
                text_format=HTML,
                disable_link_preview=disable_link_preview,
            )
        except Exception:
            LOG.exception(
                "MAX terminal status failed",
                extra={"request_id": job.request_id},
            )
            return
        if reply_markup:
            self._remember_message(job, message, text=text, text_format=HTML, photo_token=None)

    async def _set_status(
        self,
        job: PhotoJob,
        text: str,
        *,
        disable_link_preview: bool = False,
        reply_markup: dict[str, object] | None = None,
    ) -> None:
        if not job.delivery_enabled:
            return
        if not job.status_enabled:
            return
        try:
            if job.status_message_id is None:
                message = await self._api.send_message(
                    job.chat_id,
                    text=text,
                    attachments=[reply_markup] if reply_markup else None,
                    text_format=HTML,
                    disable_link_preview=disable_link_preview,
                )
                job.status_message_id = _message_id(message)
            else:
                # The full attachment list replaces the old one. An empty list removes a keyboard.
                await self._api.edit_message(
                    job.chat_id,
                    job.status_message_id,
                    text=text,
                    attachments=[reply_markup] if reply_markup else [],
                    text_format=HTML,
                )
                message = {"body": {"mid": job.status_message_id}}
        except Exception:
            LOG.exception("MAX status update failed", extra={"request_id": job.request_id})
            return
        if reply_markup:
            self._remember_message(job, message, text=text, text_format=HTML, photo_token=None)


def _storage_time(job: PhotoJob) -> int:
    return job.stored_at if job.stored_at is not None else job.received_at


def _reply_target(message_id: str | None) -> str | None:
    """Return the reply target. A synthetic forward ID is not a MAX message."""
    if not message_id or is_synthetic_message_id(message_id):
        return None
    return message_id


def _message_id(message: object) -> str | None:
    if not isinstance(message, dict):
        return None
    body = message.get("body")
    mid = body.get("mid") if isinstance(body, dict) else None
    return mid if isinstance(mid, str) and mid else None


def _minutes(seconds: int) -> int:
    return max(1, (seconds + 59) // 60)


def _queue_receipt_text(*, album: bool, position: int, wait_seconds: int) -> str:
    subject = (
        "Фотографии приняты и поставлены"
        if album
        else "Фотография принята и поставлена"
    )
    # The abbreviation point of "сек." and "мин." also ends the sentence.
    if wait_seconds <= 0:
        wait = "обработка начнётся сразу."
    elif wait_seconds < 60:
        wait = f"примерное ожидание: около {wait_seconds} сек."
    else:
        wait = f"примерное ожидание: около {_minutes(wait_seconds)} мин."
    return f"{subject} в очередь.\nПозиция: {position}; {wait}"


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
MAX_TEXT_LIMIT = 3900


def _is_admin(user: MaxUser | None, chat_type: str, services: Services) -> bool:
    """The administrator commands work only in the dialog of the administrator."""
    return bool(
        user is not None
        and user.user_id == services.settings.admin_user_id
        and chat_type == "dialog"
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
        f"<b>{index}. MAX:</b> {_display_username(user.username)}\n"
        f"<b>Имя:</b> {_display_name(user.first_name, user.last_name)}\n"
        f"<b>User ID:</b> <code>{user.user_id}</code>\n"
        f"<b>Запросов:</b> {user.total_requests} · за час: "
        f"{user.window_requests}/{rate_limit}\n"
        f"<b>Последний запрос:</b> {_format_timestamp(user.last_request_at)}"
    )


class Chat:
    """Answers in one MAX chat. It replaces the aiogram `message.answer` and `message.reply`."""

    def __init__(self, api: Any, chat_id: int, *, message_id: str | None = None) -> None:
        self._api = api
        self.chat_id = chat_id
        self._message_id = message_id

    async def answer(
        self,
        text: str,
        *,
        keyboard: dict[str, object] | None = None,
        disable_link_preview: bool = False,
    ) -> dict[str, Any]:
        return await self._api.send_message(
            self.chat_id,
            text=text,
            attachments=[keyboard] if keyboard else None,
            text_format=HTML,
            disable_link_preview=disable_link_preview,
        )

    async def reply(
        self,
        text: str,
        *,
        keyboard: dict[str, object] | None = None,
        disable_link_preview: bool = False,
    ) -> dict[str, Any]:
        return await self._api.send_message(
            self.chat_id,
            text=text,
            attachments=[keyboard] if keyboard else None,
            reply_to=_reply_target(self._message_id),
            text_format=HTML,
            disable_link_preview=disable_link_preview,
        )


async def _answer_user_blocks(chat: Chat, header: str, blocks: list[str]) -> None:
    current = header
    for block in blocks:
        candidate = f"{current}\n\n{block}"
        if len(candidate) > MAX_TEXT_LIMIT and current != header:
            await chat.answer(current)
            current = f"{header}\n\n{block}"
        else:
            current = candidate
    await chat.answer(current)


async def handle_start(
    chat: Chat,
    user: MaxUser | None,
    args: str | None,
    services: Services,
) -> None:
    if args == "privacy":
        await chat.answer(privacy_text(user.user_id if user else None))
        return
    if user is None:
        return
    if services.repository.age_status(user.user_id) != "adult":
        await chat.answer(
            AGE_GATE_TEXT,
            keyboard=AGE_CONFIRMATION_KEYBOARD,
            disable_link_preview=True,
        )
        return
    await chat.answer(START_CONFIRMED_TEXT, disable_link_preview=True)


async def handle_stats_command(
    chat: Chat,
    message: IncomingMessage,
    services: Services,
    work_queue: WorkQueue[PhotoJob],
    *,
    now: int | None = None,
) -> None:
    if message.sender is None:
        return
    current_time = int(time.time()) if now is None else now
    is_admin = _is_admin(message.sender, message.chat_type, services)
    value = services.repository.stats(
        message.sender.user_id,
        current_time,
        services.settings.rate_window_seconds,
        include_all=is_admin,
    )
    remaining = max(0, services.settings.rate_limit - value.user_window)
    if not is_admin:
        await chat.answer(
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
    await chat.answer(
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
    chat: Chat,
    message: IncomingMessage,
    args: str | None,
    services: Services,
    *,
    now: int | None = None,
) -> None:
    if not _is_admin(message.sender, message.chat_type, services):
        await chat.answer("Команда доступна только администратору.")
        return
    raw_page = (args or "").strip()
    if raw_page:
        try:
            page = int(raw_page)
        except ValueError:
            page = 0
    else:
        page = 1
    if page <= 0:
        await chat.answer("Использование: /users [номер страницы]")
        return
    current_time = int(time.time()) if now is None else now
    try:
        users, total = services.repository.list_users(
            page=page,
            page_size=USERS_PAGE_SIZE,
            now=current_time,
            window_seconds=services.settings.rate_window_seconds,
        )
    except ValueError:
        # The page offset exceeds the SQLite integer range, so the page cannot exist.
        users, total = services.repository.list_users(
            page=1,
            page_size=USERS_PAGE_SIZE,
            now=current_time,
            window_seconds=services.settings.rate_window_seconds,
        )
    page_count = max(1, (total + USERS_PAGE_SIZE - 1) // USERS_PAGE_SIZE)
    if page > page_count:
        await chat.answer(f"Страница не найдена. Доступно страниц: {page_count}.")
        return
    if not users:
        await chat.answer("Пользователей пока нет.")
        return
    header = f"<b>Пользователи</b> · страница {page}/{page_count} · всего {total}"
    offset = (page - 1) * USERS_PAGE_SIZE
    blocks = [
        _format_user_summary(offset + index, user, services.settings.rate_limit)
        for index, user in enumerate(users, start=1)
    ]
    await _answer_user_blocks(chat, header, blocks)


def _user_identity(user: MaxUser | None) -> UserIdentity | None:
    if user is None:
        return None
    return UserIdentity(
        user_id=user.user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )


async def handle_reset_limit_command(
    chat: Chat,
    message: IncomingMessage,
    args: str | None,
    services: Services,
    *,
    now: int | None = None,
) -> None:
    if not _is_admin(message.sender, message.chat_type, services):
        await chat.answer("Команда доступна только администратору.")
        return
    raw_target = (args or "").strip()
    target: UserIdentity | None
    if not raw_target:
        target = services.repository.user_by_id(services.settings.admin_user_id)
        if target is None:
            target = _user_identity(message.sender)
    elif raw_target.startswith("@") and len(raw_target) > 1 and " " not in raw_target:
        target = services.repository.user_by_username(raw_target[1:])
    elif raw_target.isdecimal() and int(raw_target) > 0:
        target_id = int(raw_target)
        # SQLite stores 64-bit integers. A larger ID cannot belong to a stored user.
        target = (
            services.repository.user_by_id(target_id)
            if target_id <= SQLITE_MAX_INTEGER
            else None
        )
        if target is None and target_id == services.settings.admin_user_id:
            target = _user_identity(message.sender)
    else:
        await chat.answer("Использование: /reset_limit [user_id или @username]")
        return
    if target is None:
        await chat.answer("Пользователь не найден.")
        return
    current_time = int(time.time()) if now is None else now
    reset_count = services.repository.reset_rate_limit(
        target.user_id,
        current_time,
        services.settings.rate_window_seconds,
    )
    await chat.answer(
        f"Лимит пользователя {_display_username(target.username)} "
        f"(ID <code>{target.user_id}</code>) сброшен.\n"
        f"Исключено из текущего окна: {reset_count}."
    )


async def enqueue_photo_message(
    message: IncomingMessage,
    services: Services,
    api: Any,
    work_queue: WorkQueue[PhotoJob],
) -> None:
    """Add each image of one message to the queue as a separate request.

    A MAX album is one message with two or more images or videos. The first admitted image
    owns the album receipt. A rejection gives one reply for the message.
    """
    sender = message.sender
    if sender is None or not message.images:
        return
    chat = Chat(api, message.chat_id, message_id=message.message_id)
    if services.repository.age_status(sender.user_id) != "adult":
        await chat.reply(
            AGE_GATE_TEXT,
            keyboard=AGE_CONFIRMATION_KEYBOARD,
            disable_link_preview=True,
        )
        return
    if work_queue.at_capacity:
        await chat.reply(QUEUE_FULL_TEXT)
        return
    album = message.is_album
    now = int(time.time())
    status_message_id: str | None = None
    receipt_claimed = False
    for photo_index, image in enumerate(message.images):
        reservation = services.repository.reserve(
            chat_id=message.chat_id,
            chat_type=message.chat_type,
            message_id=message.message_id,
            photo_index=photo_index,
            user_id=sender.user_id,
            username=sender.username,
            first_name=sender.first_name,
            last_name=sender.last_name,
            photo_id=image.photo_id,
            photo_url=image.url,
            photo_token=image.token,
            photo_source=message.photo_source,
            now=now,
            limit=services.settings.rate_limit,
            window_seconds=services.settings.rate_window_seconds,
            feedback_enabled=not album,
        )
        if reservation.duplicate:
            continue
        if not reservation.allowed or reservation.request_id is None:
            await chat.reply(
                f"Лимит — {services.settings.rate_limit} фотографий за один час. "
                f"Попробуйте снова примерно через {_minutes(reservation.retry_after_seconds)} мин."
            )
            return

        request_id = reservation.request_id
        claims_receipt = not receipt_claimed
        position = work_queue.next_position
        wait_seconds = work_queue.estimate_wait_seconds(position)
        try:
            services.repository.update(request_id, status="queued", error_code=None)
            if claims_receipt:
                status = await chat.reply(
                    _queue_receipt_text(
                        album=album,
                        position=position,
                        wait_seconds=wait_seconds,
                    )
                )
                status_message_id = _message_id(status)
                receipt_claimed = True
        except Exception:
            # The Telegram bot loses only this photo and releases the album receipt claim.
            # The next image of the album claims the receipt again.
            LOG.exception("MAX queue receipt failed", extra={"request_id": request_id})
            services.repository.update(
                request_id, status="queue_rejected", error_code="max_status"
            )
            continue

        job = PhotoJob(
            request_id=request_id,
            chat_id=message.chat_id,
            chat_type=message.chat_type,
            user_id=sender.user_id,
            source_message_id=message.message_id,
            photo_index=photo_index,
            received_at=now,
            photo_id=image.photo_id,
            photo_url=image.url,
            photo_source=message.photo_source,
            status_message_id=status_message_id if claims_receipt else None,
            feedback_enabled=not album,
            status_enabled=not album or claims_receipt,
            keep_status=album and claims_receipt,
        )
        try:
            work_queue.submit(job)
        except (QueueCapacityError, QueueClosedError):
            services.repository.update(
                request_id, status="queue_rejected", error_code="queue_capacity"
            )
            if claims_receipt and status_message_id is not None:
                await api.edit_message(
                    message.chat_id,
                    status_message_id,
                    text=QUEUE_FULL_TEXT,
                    attachments=[],
                    text_format=HTML,
                )
            else:
                await chat.reply(QUEUE_FULL_TEXT)
            return


def candidate_wine(candidate: CandidateRecord) -> Wine:
    """Return the stored card of a candidate, or a minimal card for an old request."""
    if candidate.card is not None:
        try:
            return wine_from_card(candidate.slug, candidate.card)
        except (TypeError, ValueError):
            LOG.warning("Stored wine card is invalid slug=%s", candidate.slug)
    return unknown_wine(candidate.slug)


class CallbackReplies:
    """Answers to one button press. They replace aiogram `callback.answer` and the edits."""

    def __init__(self, api: Any, services: Services, callback: CallbackEvent) -> None:
        self._api = api
        self._services = services
        self._callback = callback

    async def answer(self, notification: str | None = None) -> None:
        # MAX has no alert dialog. `show_alert` notifications are ordinary notifications.
        await self._api.answer_callback(
            self._callback.chat_id,
            self._callback.callback_id,
            notification=notification,
        )

    def _body(
        self,
        keyboard: dict[str, object] | None,
    ) -> tuple[str | None, list[dict[str, object]], str | None]:
        """Rebuild the clicked message with a new keyboard, or without a keyboard."""
        message = self._callback.message
        assert message is not None
        stored = None
        try:
            stored = self._services.repository.sent_message(message.message_id)
        except Exception:
            LOG.exception("Sent message lookup failed")
        if stored is not None:
            text, text_format = stored.text, stored.text_format
            images = (
                [image_attachment({"token": stored.photo_token})] if stored.photo_token else []
            )
        else:
            # The stored body is not available. Keep the plain text and the images.
            text, text_format = message.text, None
            images = [
                image_attachment({"token": image.token}) for image in message.images if image.token
            ]
        return text, images + ([keyboard] if keyboard else []), text_format

    async def edit_keyboard(self, keyboard: dict[str, object] | None) -> None:
        message = self._callback.message
        if message is None:
            return
        text, attachments, text_format = self._body(keyboard)
        await self._api.edit_message(
            message.chat_id,
            message.message_id,
            text=text,
            attachments=attachments,
            text_format=text_format,
        )

    async def send_to_chat(
        self,
        text: str,
        keyboard: dict[str, object],
        *,
        request_id: str,
    ) -> None:
        message = self._callback.message
        if message is None:
            return
        sent = await self._api.send_message(
            message.chat_id,
            text=text,
            attachments=[keyboard],
            text_format=HTML,
        )
        message_id = _message_id(sent)
        if message_id is None:
            return
        try:
            self._services.repository.record_sent_message(
                message_id=message_id,
                request_id=request_id,
                chat_id=message.chat_id,
                text=text,
                text_format=HTML,
                photo_token=None,
                now=int(time.time()),
            )
        except Exception:
            LOG.exception("Sent message storage failed", extra={"request_id": request_id})


async def handle_age_confirmation(
    callback: CallbackEvent,
    services: Services,
    api: Any,
) -> None:
    replies = CallbackReplies(api, services, callback)
    if callback.payload not in {"age:adult", "age:minor"}:
        await replies.answer()
        return
    status = callback.payload.removeprefix("age:")
    user = callback.user
    services.repository.set_age_status(
        user_id=user.user_id,
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
    if callback.message is None:
        await replies.answer(notification)
        return
    # One answer shows the notification and replaces the age gate without its keyboard.
    await api.answer_callback(
        callback.chat_id,
        callback.callback_id,
        notification=notification,
        message={"text": response, "attachments": [], "format": HTML},
        disable_link_preview=True,
    )


async def handle_result_feedback(
    callback: CallbackEvent,
    services: Services,
    api: Any,
) -> None:
    replies = CallbackReplies(api, services, callback)
    parts = callback.payload.split(":", 2)
    if len(parts) != 3 or parts[0] != "feedback" or parts[1] not in {"yes", "no"}:
        await replies.answer("Некорректная оценка.")
        return
    request_id = parts[2]
    result = services.repository.save_feedback(
        request_id=request_id,
        user_id=callback.user.user_id,
        matched=parts[1] == "yes",
        now=int(time.time()),
    )
    if result == "unavailable":
        await replies.answer("Эта оценка недоступна.")
        return
    already_saved = result == "already_saved"
    negative = parts[1] == "no"
    if already_saved:
        # A stale keyboard can show the other button. Restore the keyboard of the stored value.
        record = services.repository.admin_request(request_id)
        if record is not None and record.feedback_match is not None:
            negative = not record.feedback_match
    if negative:
        alternatives = [
            (candidate.rank, candidate_wine(candidate))
            for candidate in services.repository.candidates(request_id)
            if 2 <= candidate.rank <= 4
        ]
        if not alternatives:
            await replies.answer(
                "Оценка сохранена, но альтернативы для этого результата недоступны."
            )
            return
        await replies.answer(
            "Оценка уже сохранена. Показываю варианты."
            if already_saved
            else "Спасибо! Выберите возможный вариант.",
        )
        if callback.message is not None:
            markup = alternative_keyboard(request_id, alternatives)
            try:
                await replies.edit_keyboard(markup)
            except Exception:
                LOG.exception(
                    "Alternative keyboard update failed",
                    extra={"request_id": request_id},
                )
                try:
                    await replies.send_to_chat(ALTERNATIVES_TEXT, markup, request_id=request_id)
                except Exception:
                    LOG.exception(
                        "Alternative keyboard fallback failed",
                        extra={"request_id": request_id},
                    )
        return

    await replies.answer(
        "Оценка уже сохранена." if already_saved else "Спасибо! Оценка сохранена."
    )
    if callback.message is not None:
        try:
            await replies.edit_keyboard(None)
        except Exception:
            LOG.exception(
                "Feedback keyboard removal failed",
                extra={"request_id": request_id},
            )


async def handle_alternative_feedback(
    callback: CallbackEvent,
    services: Services,
    api: Any,
) -> None:
    replies = CallbackReplies(api, services, callback)
    parts = callback.payload.split(":", 2)
    if len(parts) != 3 or parts[0] != "alternative" or not parts[1].isdigit():
        await replies.answer("Некорректный вариант.")
        return
    rank = int(parts[1])
    request_id = parts[2]
    result = services.repository.save_alternative_feedback(
        request_id=request_id,
        user_id=callback.user.user_id,
        rank=rank,
        now=int(time.time()),
    )
    if result == "unavailable":
        await replies.answer("Этот вариант недоступен.")
        return
    await replies.answer(
        "Ответ уже сохранён." if result == "already_saved" else "Спасибо! Ответ сохранён."
    )
    if callback.message is not None:
        try:
            await replies.edit_keyboard(None)
        except Exception:
            LOG.exception(
                "Alternative keyboard removal failed",
                extra={"request_id": request_id},
            )


async def handle_moderation_appeal(
    callback: CallbackEvent,
    services: Services,
    api: Any,
) -> None:
    replies = CallbackReplies(api, services, callback)
    prefix = "moderation_error:"
    if not callback.payload.startswith(prefix) or not callback.payload.removeprefix(prefix):
        await replies.answer("Некорректное обращение.")
        return
    request_id = callback.payload.removeprefix(prefix)
    result = services.repository.save_moderation_appeal(
        request_id=request_id,
        user_id=callback.user.user_id,
        now=int(time.time()),
    )
    if result == "unavailable":
        await replies.answer("Это обращение недоступно.")
        return
    # A repeated press removes the keyboard again, in case an earlier edit failed.
    await replies.answer(
        "Обращение уже сохранено."
        if result == "already_saved"
        else "Спасибо! Проверим срабатывание фильтра."
    )
    if callback.message is not None:
        try:
            await replies.edit_keyboard(None)
        except Exception:
            LOG.exception(
                "Moderation appeal keyboard removal failed",
                extra={"request_id": request_id},
            )


class BotHandlers:
    """The update router. It replaces the aiogram router of the Telegram bot."""

    def __init__(self, services: Services, api: Any, work_queue: WorkQueue[PhotoJob]) -> None:
        self._services = services
        self._api = api
        self._work_queue = work_queue

    async def handle(self, update: Update) -> None:
        if isinstance(update, CallbackEvent):
            await self.on_callback(update)
        elif isinstance(update, BotStarted):
            chat = Chat(self._api, update.chat_id)
            await handle_start(chat, update.user, update.payload, self._services)
        elif isinstance(update, IncomingMessage):
            await self.on_message(update)

    async def on_callback(self, callback: CallbackEvent) -> None:
        payload = callback.payload
        if payload.startswith("age:"):
            await handle_age_confirmation(callback, self._services, self._api)
        elif payload.startswith("feedback:"):
            await handle_result_feedback(callback, self._services, self._api)
        elif payload.startswith("alternative:"):
            await handle_alternative_feedback(callback, self._services, self._api)
        elif payload.startswith("moderation_error:"):
            await handle_moderation_appeal(callback, self._services, self._api)
        else:
            await CallbackReplies(self._api, self._services, callback).answer()

    async def on_message(self, message: IncomingMessage) -> None:
        if message.sender is not None and message.sender.is_bot:
            return
        chat = Chat(self._api, message.chat_id, message_id=message.message_id)
        if message.images:
            await enqueue_photo_message(message, self._services, self._api, self._work_queue)
            return
        command = parse_command(message.text)
        name = command.name if command else None
        args = command.args if command else None
        services = self._services
        if name == "start":
            await handle_start(chat, message.sender, args, services)
        elif name == "help":
            await chat.answer(HELP_TEXT)
        elif name == "privacy":
            sender = message.sender
            await chat.answer(privacy_text(sender.user_id if sender else None))
        elif name == "stats":
            await handle_stats_command(chat, message, services, self._work_queue)
        elif name == "users":
            await handle_users_command(chat, message, args, services)
        elif name == "reset_limit":
            await handle_reset_limit_command(chat, message, args, services)
        else:
            await chat.answer(FALLBACK_TEXT)


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
        chat_type="api",
        source_message_id="",
        received_at=now,
        photo_url="",
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
    now = int(time.time())
    cutoff = now - settings.data_retention_days * 86400
    result = purge_expired_data(repository, settings.data_root, cutoff=cutoff)
    # A processed update stays one day, so a repeated webhook delivery is dropped.
    updates = repository.purge_processed_updates(now - 86400)
    LOG.info(
        "Data retention completed requests=%s users=%s files=%s updates=%s",
        result.requests,
        result.users,
        result.files,
        updates,
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
            chat_type=request.chat_type,
            user_id=request.user_id,
            source_message_id=request.message_id,
            photo_index=request.photo_index,
            received_at=request.received_at,
            photo_id=request.photo_id,
            photo_url=request.photo_url,
            photo_source=request.photo_source,
            status_message_id=None,
            feedback_enabled=request.feedback_enabled,
            status_enabled=True,
            local_path=request.local_path,
            stored_at=request.stored_at,
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


def restore_pending_jobs(repository: Repository, work_queue: WorkQueue[PhotoJob]) -> int:
    pending = repository.pending_requests()
    for request in pending:
        work_queue.submit(
            PhotoJob(
                request_id=request.request_id,
                chat_id=request.chat_id,
                chat_type=request.chat_type,
                user_id=request.user_id,
                source_message_id=request.message_id,
                photo_index=request.photo_index,
                received_at=request.received_at,
                photo_id=request.photo_id,
                photo_url=request.photo_url,
                photo_source=request.photo_source,
                status_message_id=None,
                feedback_enabled=request.feedback_enabled,
                status_enabled=request.feedback_enabled,
                local_path=request.local_path,
                stored_at=request.stored_at,
            ),
            restore=True,
        )
    return len(pending)


async def sync_profile(api: Any) -> None:
    """Set the command menu. MAX has no API for the bot description."""
    await api.set_commands(COMMANDS)


def configure_logging(settings: Settings) -> None:
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(
        SecretRedactingFormatter(
            LOG_FORMAT,
            (
                settings.max_token,
                settings.http_api_token,
                settings.webhook.secret if settings.webhook else "",
            ),
        )
    )
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        handlers=[log_handler],
    )
    # httpx logs each request URL at INFO. An attachment URL gives access to a user photo.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def run() -> None:
    settings = Settings.from_env()
    configure_logging(settings)
    rejection_image = settings.rejection_image_file.read_bytes()
    if not rejection_image:
        raise RuntimeError("BOT_REJECTION_IMAGE is empty")
    repository = Repository(settings.database_file)
    store = ImageStore(settings.data_root)
    artifact_store = ArtifactStore(settings.data_root)
    client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
    )
    max_client = httpx.AsyncClient(
        verify=create_ssl_context(settings.max_api_ca_file),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    api = MaxApi(
        settings.max_token,
        max_client,
        base_url=settings.max_api_base_url,
        media_allowed_hosts=settings.media_allowed_hosts,
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

    processor = PhotoProcessor(services, api)
    work_queue = WorkQueue(
        processor.process,
        worker_count=settings.queue_workers,
        capacity=settings.queue_capacity,
        initial_job_seconds=settings.queue_estimate_seconds,
    )
    handlers = BotHandlers(services, api, work_queue)
    dispatcher = UpdateDispatcher(repository, handlers.handle)
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
    servers = [
        EmbeddedServer(
            uvicorn.Config(
                http_api,
                host=settings.http_api_host,
                port=settings.http_api_port,
                log_level=settings.log_level.lower(),
                proxy_headers=False,
                lifespan="off",
            )
        )
    ]
    if settings.webhook is not None:
        servers.append(
            EmbeddedServer(
                uvicorn.Config(
                    create_webhook_app(
                        path=settings.webhook.path,
                        secret=settings.webhook.secret,
                        dispatcher=dispatcher,
                    ),
                    host=settings.webhook.host,
                    port=settings.webhook.port,
                    log_level=settings.log_level.lower(),
                    proxy_headers=False,
                    lifespan="off",
                )
            )
        )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_number in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(signal_number, stop.set)
        except (NotImplementedError, RuntimeError):
            pass

    tasks: dict[str, asyncio.Task[Any]] = {}
    try:
        me = await api.get_me()
        LOG.info("MAX bot connected bot_user_id=%s", me.get("user_id"))
        if settings.sync_profile:
            await sync_profile(api)
        await work_queue.start()
        interrupted_api_requests = repository.fail_interrupted_api_requests()
        restored_jobs = restore_pending_jobs(repository, work_queue)
        if settings.webhook is not None:
            if settings.webhook.subscribe:
                await api.subscribe(
                    settings.webhook.url,
                    secret=settings.webhook.secret,
                    update_types=UPDATE_TYPES,
                )
        else:
            poller = Poller(
                api,
                dispatcher,
                repository,
                timeout_seconds=settings.poll_timeout_seconds,
            )
            await poller.check_no_webhook()
            tasks["max-polling"] = asyncio.create_task(poller.run(), name="max-polling")
        tasks["max-dispatcher"] = asyncio.create_task(dispatcher.run(), name="max-dispatcher")
        tasks["admin-retry-watcher"] = asyncio.create_task(
            watch_admin_retries(repository, work_queue),
            name="admin-retry-watcher",
        )
        tasks["data-retention"] = asyncio.create_task(
            data_retention_loop(settings, repository),
            name="data-retention",
        )
        for index, server in enumerate(servers):
            tasks[f"http-server-{index}"] = asyncio.create_task(
                server.serve(), name=f"http-server-{index}"
            )
        stop_task = asyncio.create_task(stop.wait(), name="stop-signal")
        LOG.info(
            "MAX bot and HTTP API started",
            extra={
                "matcher_endpoint": settings.matcher_endpoint,
                "moderation_enabled": settings.moderation_enabled,
                "update_mode": settings.update_mode,
                "queue_workers": settings.queue_workers,
                "queue_capacity": settings.queue_capacity,
                "restored_jobs": restored_jobs,
                "interrupted_api_requests": interrupted_api_requests,
                "http_api_host": settings.http_api_host,
                "http_api_port": settings.http_api_port,
            },
        )
        done, _ = await asyncio.wait(
            {stop_task, *tasks.values()},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if stop_task not in done:
            for task in done:
                task.result()
            raise RuntimeError("A MAX bot task stopped unexpectedly")
        LOG.info("Stop signal received; the bot stops")
    finally:
        for server in servers:
            server.should_exit = True
        for name, task in tasks.items():
            if not name.startswith("http-server-") and not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)
        await work_queue.stop()
        await client.aclose()
        await max_client.aclose()
        repository.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
