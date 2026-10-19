from aiogram.types import BotCommand
from chto_za_vino_core.texts import LEGAL_NOTICE

SHORT_DESCRIPTION = (
    "Распознаю российское вино по фотографии. Пришлите снимок — покажу название и страницу вина."
)

DESCRIPTION = """Сфотографируйте бутылку или этикетку — бот попробует определить вино и даст ссылку на его страницу в каталоге vino-svoe.ru.

Лучше всего работают резкие фотографии без бликов, где этикетка занимает большую часть кадра. Результат может быть неточным.

Фотографии и данные запроса сохраняются для проверки и улучшения распознавания. Не отправляйте личные или конфиденциальные изображения.

Команда ALOLA 1 · @s1mb1o"""

COMMANDS = [
    BotCommand(command="start", description="Как пользоваться ботом"),
    BotCommand(command="help", description="Советы для хорошего фото"),
    BotCommand(command="stats", description="Статистика распознавания"),
    BotCommand(command="privacy", description="Как обрабатываются данные"),
]

ADMIN_ONLY_COMMANDS = [
    BotCommand(command="users", description="Список пользователей"),
    BotCommand(command="reset_limit", description="Сбросить лимит пользователя"),
]

ADMIN_COMMANDS = [*COMMANDS, *ADMIN_ONLY_COMMANDS]

# «Винный дневник» link (issue #51). The menu shows /unlink only when the link is on.
UNLINK_COMMAND = BotCommand(command="unlink", description="Отвязать от «Винного дневника»")


def menu_commands(account_link: bool) -> tuple[list[BotCommand], list[BotCommand]]:
    """Return the command menu of every user and of the administrator."""
    commands = [*COMMANDS, UNLINK_COMMAND] if account_link else list(COMMANDS)
    return commands, [*commands, *ADMIN_ONLY_COMMANDS]


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

Бот сохраняет отправленную фотографию, Telegram user ID, доступные имя и username, выбор в подтверждении возраста, дату, результат проверки безопасности, результат распознавания и выбранную оценку совпадения. Данные нужны для работы сервиса и улучшения качества распознавания.

В рабочей версии сервиса проверка безопасности всегда включена. Фотографии с потенциально недопустимым содержимым хранятся отдельно и не передаются в распознавание. Автоматическая проверка может ошибаться.

Бот автоматически удаляет фотографии, артефакты обработки и данные запроса через 30 дней.

Чтобы запросить удаление своих данных, напишите @s1mb1o и укажите Telegram user ID."""
