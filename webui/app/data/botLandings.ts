// Content of the /telegram-bot and /max-bot landing pages (BotLanding.vue).
// Sources: telegram-bot/README.md, max-bot/README.md, both bots' profile.py, docs/account.md,
// and plan 07. /max is the MAX mini app of «Винный дневник», so the MAX page uses /max-bot.
export interface BotLanding {
  path: string
  platform: 'Telegram' | 'MAX'
  icon: string
  handle: string
  url: string
  title: string
  description: string
  privacyAnchor: string
  start: string
  benefits: { icon: string; title: string; copy: string }[]
  steps: { number: string; icon: string; title: string; copy: string }[]
  diaryCopy: string
  diaryFacts: { term: string; value: string }[]
  diarySteps: string[]
  diaryNote: string
  commands: { name: string; copy: string }[]
}

function benefits(platform: BotLanding['platform']) {
  return [
    { icon: 'image', title: 'Фото или файл', copy: 'Отправьте снимок как фотографию или как файл JPEG, PNG, WebP, HEIC или HEIF. Файл HEIC бот переведёт в JPEG без данных EXIF.' },
    { icon: 'shelf', title: 'Целый альбом', copy: `Пришлите несколько фотографий одним альбомом ${platform}. Бот ответит на каждую фотографию отдельно.` },
    { icon: 'wine-red', title: 'Карточка вина', copy: 'Фото бутылки, название, винодельня, цвет, сахар, сорта винограда и кнопка «Открыть страницу вина» на vino-svoe.ru.' },
    { icon: 'history', title: 'Понятная очередь', copy: 'Бот сразу сообщит позицию в очереди и примерное время ожидания. Каждое фото получит свой ответ.' },
    { icon: 'check', title: 'Совпало или нет', copy: 'Оцените ответ на одиночное фото: «✅ Совпало» или «❌ Не совпало». Во втором случае бот покажет ещё три варианта.' },
    { icon: 'info', title: 'Честный ответ', copy: 'Если уверенности мало, бот скажет об этом, покажет самый вероятный вариант и попросит ещё одно фото.' },
    { icon: 'book', title: 'Винный дневник', copy: `Привяжите ${platform} к аккаунту на сайте. При включённой записи новые находки из чата и веб-сканера появятся в общей истории «Винного дневника».` },
    { icon: 'shield', title: 'Проверка и сроки', copy: 'Каждое фото проходит автоматическую проверку безопасности. Фото и данные запроса бот удаляет через 30 дней.' },
  ]
}

function steps(platform: BotLanding['platform'], icon: string, start: string) {
  return [
    { number: '01', icon, title: 'Начните чат', copy: `${start} Подтвердите, что вам есть 18 лет. Фото, отправленное раньше, повторять не нужно.` },
    { number: '02', icon: 'camera', title: 'Отправьте фото', copy: 'Снимите бутылку или этикетку крупно, ровно и без бликов. Название на этикетке должно читаться.' },
    { number: '03', icon: 'history', title: 'Дождитесь ответа', copy: `Квитанция покажет позицию в очереди. Карточка вина придёт в этот же чат ${platform}.` },
    { number: '04', icon: 'check', title: 'Проверьте вино', copy: 'Сравните карточку с этикеткой. Откройте страницу вина или оцените ответ кнопкой.' },
  ]
}

const commonCommands = [
  { name: '/start', copy: 'Приглашение, сведения о данных и подтверждение возраста' },
  { name: '/help', copy: 'Советы для хорошего фото и лимит: 50 фотографий за час' },
  { name: '/stats', copy: 'Ваша статистика распознавания' },
]

const telegramStart = 'Откройте @ChtoZaVinoBot и отправьте /start.'
export const telegramBot: BotLanding = {
  path: '/telegram-bot',
  platform: 'Telegram',
  icon: 'telegram',
  handle: '@ChtoZaVinoBot',
  url: 'https://t.me/ChtoZaVinoBot',
  title: 'Бот «Что за вино?» в Telegram — вино по фото в чате',
  description: 'Найдите российское вино по фото в Telegram с @ChtoZaVinoBot. Привяжите бота к аккаунту на сайте, чтобы сохранять новые находки в общей истории «Винного дневника».',
  privacyAnchor: 'telegram',
  start: telegramStart,
  benefits: benefits('Telegram'),
  steps: steps('Telegram', 'telegram', telegramStart),
  diaryCopy: 'Привяжите Telegram к своему аккаунту на сайте. При включённой записи новые находки из бота, веб-сканера и MAX, привязанного к тому же аккаунту, появятся в общей истории «Винного дневника». Откройте вкладку «История» на сайте с любого устройства, где вы вошли в этот аккаунт.',
  diaryFacts: [
    { term: 'Привязка', value: 'Ссылка из дневника' },
    { term: 'Источник в истории', value: 'Telegram' },
    { term: 'Общая история', value: 'Сайт · Telegram · MAX' },
    { term: 'Отвязать', value: '/unlink или в дневнике' },
  ],
  diarySteps: [
    'Войдите в свой аккаунт на сайте и откройте «Настройки» в «Винном дневнике».',
    'В разделе «Связанные мессенджеры» нажмите «Привязать мессенджер», затем «Telegram» и «Открыть Telegram».',
    'Нажмите «Привязать» в чате с ботом. На сайте включите «Записывать найденные вина» в «Настройках».',
  ],
  diaryNote: 'Не пересылайте ссылку привязки: её получит первый, кто её откроет. Войти в дневник через Telegram нельзя.',
  commands: [
    ...commonCommands,
    { name: '/privacy', copy: 'Какие данные хранит бот и как их удалить' },
    { name: '/unlink', copy: 'Отвязать Telegram от «Винного дневника»' },
  ],
}

const maxStart = 'Откройте @se14697933_bot и нажмите «Начать».'
export const maxBot: BotLanding = {
  path: '/max-bot',
  platform: 'MAX',
  icon: 'message',
  handle: '@se14697933_bot',
  url: 'https://max.ru/se14697933_bot',
  title: 'Бот «Что за вино?» в MAX — вино по фото в чате',
  description: 'Найдите российское вино по фото с ботом «Что за вино?» в MAX. Привяжите MAX к аккаунту на сайте, чтобы сохранять новые находки в общей истории «Винного дневника».',
  privacyAnchor: 'max',
  start: maxStart,
  benefits: benefits('MAX'),
  steps: steps('MAX', 'message', maxStart),
  diaryCopy: 'Привяжите MAX к своему аккаунту на сайте через мини-приложение. При включённой записи новые находки из бота, веб-сканера и Telegram, привязанного к тому же аккаунту, появятся в общей истории «Винного дневника». Историю смотрите на сайте во вкладке «История».',
  diaryFacts: [
    { term: 'Привязка', value: 'Мини-приложение MAX' },
    { term: 'Источник в истории', value: 'MAX' },
    { term: 'Общая история', value: 'Сайт · Telegram · MAX' },
    { term: 'Отвязать', value: 'В дневнике' },
  ],
  diarySteps: [
    'Войдите в свой аккаунт на сайте и откройте «Настройки» в «Винном дневнике».',
    'В разделе «Связанные мессенджеры» нажмите «Привязать мессенджер», затем «MAX». Откройте ссылку в MAX или отсканируйте QR-код телефоном.',
    'В мини-приложении войдите по коду из письма в тот же аккаунт и нажмите «Привязать». Проверьте, что в «Настройках» включено «Записывать найденные вина».',
  ],
  diaryNote: 'Используйте почту, связанную с вашим аккаунтом на сайте, чтобы привязать MAX к тому же дневнику. В мини-приложении доступны настройки; общая история — на сайте.',
  commands: [
    ...commonCommands,
    { name: '/privacy', copy: 'Какие данные хранит бот, как их удалить и ваш MAX user ID' },
  ],
}
