// One set of legal pages serves the website, both bots, and the mobile apps (#37).
// The bots store `legalRevision` as the version of the accepted terms.
export const legalRevision = '2026-10-19'
export const legalRevisionLabel = '19 октября 2026 года'

export const operator = {
  name: 'Шмелев Александр Сергеевич',
  status: 'самозанятый, плательщик налога на профессиональный доход',
  inn: '772326685406',
}

export const contactEmail = 'Alexander.Shmelev@gmail.com'

export const contactChannels = [
  { id: 'email', label: 'Электронная почта', value: contactEmail, href: `mailto:${contactEmail}` },
  { id: 'telegram', label: 'Telegram', value: '@s1mb1o', href: 'https://t.me/s1mb1o' },
]

export const legalLinks = [
  { path: '/terms', label: 'Условия использования' },
  { path: '/privacy', label: 'Политика обработки персональных данных' },
  { path: '/contacts', label: 'Контакты' },
]

export const legalPaths = legalLinks.map(link => link.path)
