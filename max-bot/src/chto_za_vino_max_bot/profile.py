from html import escape

from chto_za_vino_core.texts import LEGAL_NOTICE

# MAX has no API for the bot description. The owner sets the description in the bot card on
# business.max.ru, and the card passes the platform moderation. The card description has a
# limit of 200 characters, so the card uses SHORT_DESCRIPTION.
SHORT_DESCRIPTION = (
    "Распознаю российское вино по фотографии. Пришлите снимок — покажу название и страницу вина."
)

DESCRIPTION = """Сфотографируйте бутылку или этикетку — бот попробует определить вино и даст ссылку на его страницу в каталоге vino-svoe.ru.

Лучше всего работают резкие фотографии без бликов, где этикетка занимает большую часть кадра. Результат может быть неточным.

Фотографии и данные запроса сохраняются для проверки и улучшения распознавания. Не отправляйте личные или конфиденциальные изображения.

Команда ALOLA 1 · @s1mb1o"""

# PATCH /me/commands sets one list for all chats. MAX has no command scope, so the
# administrator commands are not in the menu. They work in the administrator's dialog.
COMMANDS = [
    {"name": "start", "description": "Как пользоваться ботом"},
    {"name": "help", "description": "Советы для хорошего фото"},
    {"name": "stats", "description": "Статистика распознавания"},
    {"name": "privacy", "description": "Как обрабатываются данные"},
]

ADMIN_COMMANDS = [
    *COMMANDS,
    {"name": "users", "description": "Список пользователей"},
    {"name": "reset_limit", "description": "Сбросить лимит пользователя"},
]


START_TEXT = """<b>Что за вино?</b> 🍷

Пришлите фотографию бутылки или этикетки. Я попробую определить вино и дам ссылку на его страницу на <a href="https://vino-svoe.ru/">vino-svoe.ru</a>.

Фотографии и данные запроса сохраняются для проверки и улучшения распознавания. Не отправляйте личные или конфиденциальные изображения. Подробнее: /privacy

Команда <b>ALOLA 1</b>
Связь: @s1mb1o"""

AGE_GATE_TEXT = f"""{START_TEXT}

{LEGAL_NOTICE}

Подтвердите, что вам уже исполнилось 18 лет."""

START_CONFIRMED_TEXT = f"""{START_TEXT}

✅ Возраст подтверждён.

{LEGAL_NOTICE}"""

MINOR_TEXT = f"""Бот предназначен только для пользователей старше 18 лет.

{LEGAL_NOTICE}"""

HELP_TEXT = """<b>Как получить лучший результат</b>

• Снимите бутылку или этикетку крупно.
• Держите камеру ровно.
• Избегайте бликов и сильных теней.
• Проверьте, что название на этикетке читается.
• Можно отправить одно фото или альбом. Каждая фотография обрабатывается отдельно.

Лимит: 50 фотографий за один час."""

PRIVACY_TEXT = """<b>Обработка данных</b>

Бот сохраняет отправленную фотографию, MAX user ID, доступные имя и username, выбор в подтверждении возраста, дату, результат проверки безопасности, результат распознавания и выбранную оценку совпадения. Данные нужны для работы сервиса и улучшения качества распознавания.

В рабочей версии сервиса проверка безопасности всегда включена. Фотографии с потенциально недопустимым содержимым хранятся отдельно и не передаются в распознавание. Автоматическая проверка может ошибаться.

Бот автоматически удаляет фотографии, артефакты обработки и данные запроса через 30 дней.

Чтобы запросить удаление своих данных, напишите @s1mb1o и укажите MAX user ID."""


def privacy_text(user_id: int | None) -> str:
    """Return the privacy notice. A MAX user has no simple way to see the own user ID."""
    if user_id is None:
        return PRIVACY_TEXT
    return f"{PRIVACY_TEXT}\n\nВаш MAX user ID: <code>{escape(str(user_id))}</code>"
