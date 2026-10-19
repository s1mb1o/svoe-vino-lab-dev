// Shared rules of the «Винный дневник» account pages and the /api/account/* server routes.

export const ACCOUNT_PATH = '/account'
// The MAX mini app of the diary (plan 05). It is the account page in MAX mode.
export const MAX_APP_PATH = '/max'
// The fixed deep link of the mini app: https://max.ru/<bot>?startapp=account. It holds no code.
export const MAX_APP_LINK_PATTERN = /^https:\/\/max\.ru\/[A-Za-z0-9_]{1,64}\?startapp=account$/

// The account service accepts 3 to 32 characters: lower-case Latin letters, digits, ".", "_", "-".
// The first and the last character are a letter or a digit.
export const USERNAME_PATTERN = /^[a-z0-9][a-z0-9_.-]{1,30}[a-z0-9]$/

export const EMAIL_CODE_PATTERN = /^\d{6}$/

/** Returns a same-site path for a redirect after login, or the account page. */
export function safeNextPath(value: unknown): string {
  if (typeof value !== 'string') return ACCOUNT_PATH
  if (value.length > 512 || !value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) return ACCOUNT_PATH
  if (/[\u0000-\u001f\u007f\\]/.test(value)) return ACCOUNT_PATH
  if (value === '/api' || value.startsWith('/api/') || value.startsWith('/v1/')) return ACCOUNT_PATH
  return value
}

/** True for the account pages and the MAX mini app. Metrika and the Workbox page cache skip these paths. */
export function isAccountPath(pathname: string): boolean {
  return [ACCOUNT_PATH, MAX_APP_PATH].some(base => pathname === base || pathname.startsWith(`${base}/`))
}

export function isMaxAppPath(pathname: string): boolean {
  return pathname === MAX_APP_PATH || pathname.startsWith(`${MAX_APP_PATH}/`)
}

export interface AccountErrorBody {
  error: string
  attemptsLeft?: number
  retryAfter?: number
}

export function accountErrorMessage(body: Partial<AccountErrorBody> | undefined): string {
  const minutes = body?.retryAfter ? Math.max(1, Math.ceil(body.retryAfter / 60)) : 0
  switch (body?.error) {
    case 'invalid_email':
      return 'Проверьте адрес почты.'
    case 'rate_limited':
      return minutes ? `Слишком много попыток. Попробуйте через ${minutes} мин.` : 'Слишком много попыток. Попробуйте позже.'
    case 'invalid_code':
      return typeof body.attemptsLeft === 'number' ? `Неверный код. Осталось попыток: ${body.attemptsLeft}.` : 'Неверный код.'
    case 'invalid_challenge':
    case 'too_many_attempts':
      return 'Этот код больше не действует. Запросите новый.'
    case 'invalid_username':
      return 'Имя: от 3 до 32 символов — строчные латинские буквы, цифры, точка, дефис или подчёркивание. Первый и последний символ — буква или цифра.'
    case 'username_taken':
      return 'Это имя уже занято.'
    case 'username_reserved':
      return 'Это имя зарезервировано. Выберите другое.'
    case 'invalid_ticket':
      return 'Время на регистрацию истекло. Войдите ещё раз.'
    case 'consent_outdated':
    case 'terms_outdated':
      return 'Тексты условий обновились. Обновите страницу и примите их ещё раз.'
    case 'consent_required':
      return 'Отметьте оба пункта, чтобы создать дневник.'
    case 'provider_disabled':
    case 'provider_unavailable':
    case 'provider_rejected':
    case 'invalid_flow':
    case 'yandex_cancelled':
      return 'Вход с Яндекс ID не завершён. Попробуйте ещё раз.'
    case 'session_required':
    case 'session_invalid':
      return 'Сеанс завершён. Войдите ещё раз.'
    case 'provider_already_linked':
      return 'Этот мессенджер уже привязан. Обновите страницу.'
    case 'too_many_tokens':
      return 'Можно иметь не больше 5 активных токенов. Отзовите ненужный токен.'
    case 'invalid_name':
      return 'Назовите токен: от 1 до 64 символов.'
    case 'identity_in_use':
      return 'Этот аккаунт мессенджера уже привязан к другому дневнику.'
    case 'invalid_launch':
    case 'launch_expired':
    case 'launch_reused':
    case 'launch_ip_mismatch':
      return 'Данные запуска MAX устарели. Закройте дневник и откройте его в MAX снова.'
    case 'account_unavailable':
      return 'Дневник временно недоступен. Поиск вина по фото работает.'
    default:
      return 'Что-то пошло не так. Попробуйте ещё раз.'
  }
}

/** The MCP client configuration for a new application token (mcp/README.md). */
export function mcpClientConfig(token: string): string {
  return JSON.stringify({
    mcpServers: {
      'svoe-vino': {
        command: '/absolute/path/to/node',
        args: ['/absolute/path/to/mcp/src/cli.mjs'],
        env: { CHTOZAVINO_ACCOUNT_TOKEN: token },
      },
    },
  }, null, 2)
}

export interface IdentityRow { key: string; label: string; value: string }

/**
 * Splits the linked identities of an account. Only email and Yandex ID are login methods.
 * Telegram and MAX are linked messengers: they save finds but never open a session
 * (149-FZ art. 8 p. 10 for Telegram; MAX login is off, issue #50).
 */
export function splitIdentities(items: Array<{ provider: string; email?: string }>): { login: IdentityRow[]; linked: IdentityRow[] } {
  const login: IdentityRow[] = []
  const linked: IdentityRow[] = []
  for (const item of items) {
    if (item.provider === 'email') login.push({ key: 'email', label: 'Почта', value: item.email ?? '' })
    else if (item.provider === 'yandex') login.push({ key: 'yandex', label: 'Яндекс ID', value: 'привязан' })
    else if (item.provider === 'telegram') linked.push({ key: 'telegram', label: 'Telegram', value: 'привязан' })
    else if (item.provider === 'max') linked.push({ key: 'max', label: 'MAX', value: 'привязан' })
  }
  return { login, linked }
}
