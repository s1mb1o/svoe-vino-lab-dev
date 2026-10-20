import { legalLinks } from './legal'

// The /sitemap page and tests/sitemap.test.ts read this list. Keep it equal to public/sitemap.xml.
export interface SitemapPage { path: string; label: string; icon: string; description: string }

const legalDescriptions: Record<string, string> = {
  '/terms': 'Правила для сайта, ботов и приложений: возраст, допустимые фотографии, «Винный дневник», жалобы.',
  '/privacy': 'Какие данные обрабатывает каждый сервис, сколько их хранят и как их удалить.',
  '/contacts': 'Оператор сервиса, способы связи, жалобы и запросы о данных.',
}
const legalIcons: Record<string, string> = { '/contacts': 'info' }
export const sitemapSections: { id: string; title: string; pages: SitemapPage[] }[] = [
  {
    id: 'search', title: 'Поиск вина',
    pages: [
      { path: '/', label: 'Одна бутылка', icon: 'scan', description: 'Сделайте фото бутылки или загрузите изображение, чтобы узнать вино.' },
      { path: '/shelf', label: 'Вся полка', icon: 'shelf', description: 'Найдите вина на общем фото полки. Выберите бутылку, чтобы открыть результат.' },
      { path: '/dish', label: 'Вино к блюду', icon: 'food', description: 'Сфотографируйте блюдо или назовите его. Уточните соус и остроту и получите подборку вин.' },
    ],
  },
  {
    id: 'catalog', title: 'Каталог',
    pages: [
      { path: '/lineup', label: 'Карты линеек производителей', icon: 'map', description: 'Группы и ступени внутри линейки российских производителей вина и их бутылки.' },
    ],
  },
  {
    id: 'applications', title: 'Приложения',
    pages: [
      { path: '/hackaton', label: 'Все приложения', icon: 'scan', description: 'Одно фото — три способа узнать вино: веб-приложение, Android без интернета и бот в Telegram.' },
      { path: '/shelf-lens', label: 'Shelf Lens', icon: 'shelf', description: 'Видео винной полки: распознавание, рейтинг в дополненной реальности и планограмма выкладки.' },
      { path: '/android', label: 'Android', icon: 'android', description: 'Приложение для Android. Распознавание без интернета, QR-коды и штрихкоды.' },
      { path: '/iphone', label: 'iPhone', icon: 'phone', description: 'Нативное приложение для iPhone. Распознавание на устройстве, QR-коды и штрихкоды.' },
      { path: '/telegram-bot', label: 'Бот в Telegram', icon: 'telegram', description: 'Бот @ChtoZaVinoBot. Отправьте фото или альбом в чат и получите карточку вина.' },
      { path: '/max-bot', label: 'Бот в MAX', icon: 'message', description: 'Бот «Что за вино?» в MAX. Отправьте фото или альбом в чат и получите карточку вина.' },
    ],
  },
  {
    id: 'games', title: 'Игры',
    pages: [
      { path: '/game', label: 'Wine&Dine Merge', icon: 'game', description: 'Игра в браузере: собирайте блюда и подбирайте к ним российское вино.' },
      { path: '/crocodile', label: 'Винный крокодил', icon: 'game', description: 'Настольная игра о вине: 30 карточек и правила для печати.' },
    ],
  },
  {
    id: 'project', title: 'О проекте',
    pages: [
      { path: '/ideas', label: 'Больше, чем распознавание', icon: 'book', description: 'Готовые возможности, демонстрации и идеи для знакомства с российским вином.' },
      { path: '/presentation', label: 'Презентация проекта', icon: 'desktop', description: 'Презентация, материалы и ссылки на ресурсы проекта.' },
    ],
  },
  {
    id: 'legal', title: 'Правовая информация',
    pages: legalLinks.map(link => ({ ...link, icon: legalIcons[link.path] || 'shield', description: legalDescriptions[link.path] || '' })),
  },
]
