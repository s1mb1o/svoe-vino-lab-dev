<script setup lang="ts">
import { ACCOUNT_PATH, EMAIL_CODE_PATTERN, USERNAME_PATTERN, accountErrorMessage, isMaxAppPath, mcpClientConfig, safeNextPath, splitIdentities } from '#shared/account'
import { AccountRequestError, useAccountApi, type AccountSiteConfig, type AccountUser, type AppToken } from '~/composables/useAccountApi'
import { readMaxLaunch } from '~/utils/max-bridge'

// /max is this page in MAX mode: the diary mini app on max.chtozavino.ru (plan 05).
definePageMeta({ alias: ['/max'] })

const title = 'Винный дневник — Что за вино?'
useSeoMeta({ title, robots: 'noindex, nofollow, noarchive' })

type Phase = 'loading' | 'disabled' | 'unavailable' | 'outside' | 'email' | 'code' | 'signup' | 'account' | 'deleted'

const api = useAccountApi()
const route = useRoute()
const router = useRouter()
const phase = ref<Phase>('loading')
const config = ref<AccountSiteConfig | null>(null)
const user = ref<AccountUser | null>(null)
const email = ref('')
const code = ref('')
const username = ref('')
const acceptTerms = ref(false)
const acceptConsent = ref(false)
const signupEmail = ref('')
const busy = ref(false)
const message = ref('')
const notice = ref('')
// Dangerous actions ask for a confirmation on the page; there is no re-login rule (owner, 2026-10-19).
const confirmDelete = ref(false)
const resendAt = ref(0)
const now = ref(Date.now())
const heading = ref<HTMLElement>()
let clock: ReturnType<typeof setInterval> | undefined

const next = computed(() => safeNextPath(route.query.next))
const yandexEnabled = computed(() => Boolean(config.value?.providers?.yandex))
const yandexHref = computed(() => `/api/account/yandex/start?next=${encodeURIComponent(next.value)}`)
const usernameValid = computed(() => USERNAME_PATTERN.test(username.value))
const canSignup = computed(() => usernameValid.value && acceptTerms.value && acceptConsent.value && !busy.value)
const resendIn = computed(() => Math.max(0, Math.ceil((resendAt.value - now.value) / 1000)))
const identities = computed(() => splitIdentities(user.value?.identities ?? []))
// «Привязать мессенджер» (issues #51, #50). A messenger never opens a session: it only saves finds.
type Messenger = 'telegram' | 'max'
const MESSENGER_NAMES: Record<Messenger, string> = { telegram: 'Telegram', max: 'MAX' }
const linkOpen = ref(false)
const linkTarget = ref<Messenger | ''>('')
const telegramLink = ref('')
const telegramLinkExpiresAt = ref(0)
const linkNotice = ref('')
const telegramEnabled = computed(() => Boolean(config.value?.providers?.telegram))
const telegramLinked = computed(() => identities.value.linked.some(item => item.key === 'telegram'))
const maxEnabled = computed(() => Boolean(config.value?.providers?.max && config.value.maxAppLink))
const maxLinked = computed(() => identities.value.linked.some(item => item.key === 'max'))
const canLinkTelegram = computed(() => telegramEnabled.value && !telegramLinked.value)
const canLinkMax = computed(() => maxEnabled.value && !maxLinked.value)
// Inside MAX the page links only MAX itself, from the launch data.
const canLinkMessenger = computed(() => !maxApp.value && (canLinkTelegram.value || canLinkMax.value))
const showMessengers = computed(() => identities.value.linked.length > 0 || canLinkMessenger.value || Boolean(linkNotice.value))
const telegramLinkExpired = computed(() => Boolean(telegramLink.value) && now.value >= telegramLinkExpiresAt.value)
// MAX mode. The launch data is the only MAX identity; the name is shown so a person can spot a foreign launch.
const maxApp = computed(() => isMaxAppPath(route.path))
const maxLaunch = ref('')
const maxName = ref('')
// «Токены приложений» (issue #65): read-only access to this diary for an MCP client.
const appTokens = ref<AppToken[]>([])
const tokenFormOpen = ref(false)
const tokenName = ref('')
const tokenDays = ref(90)
const newToken = ref('')
const tokenNotice = ref('')
// One pending yes/no question for «Отвязать» or «Отозвать», shown in its own section.
const pending = ref<{ section: 'messengers' | 'tokens'; question: string; run: () => Promise<void> } | null>(null)
const newTokenConfig = computed(() => newToken.value ? mcpClientConfig(newToken.value) : '')
// A server route renders the QR code of the fixed mini-app link (no code inside).
const MAX_QR_URL = '/api/account/max/qr.svg'

function show(nextPhase: Phase) {
  phase.value = nextPhase
  if (nextPhase === 'account') loadAppTokens()
  nextTick(() => heading.value?.focus())
}

function fail(error: unknown) {
  const body = error instanceof AccountRequestError ? error.body : { error: 'account_unavailable' }
  message.value = accountErrorMessage(body)
  if (body.error === 'account_unavailable') show('unavailable')
}

async function afterLogin() {
  message.value = ''
  if (next.value !== ACCOUNT_PATH) {
    await navigateTo(next.value)
    return
  }
  const me = await api.me()
  user.value = me.user
  show('account')
}

async function load() {
  phase.value = 'loading'
  try {
    config.value = await api.config()
  } catch {
    config.value = { enabled: true, available: false }
  }
  if (!config.value.enabled) return show('disabled')
  if (!config.value.available) return show('unavailable')
  if (maxApp.value) {
    // The MAX Bridge is a third-party script: it runs only on the mini-app host, never on the main site.
    if (!config.value.maxApp) {
      await navigateTo(ACCOUNT_PATH, { replace: true })
      return
    }
    const launch = await readMaxLaunch()
    maxLaunch.value = launch.initData
    maxName.value = launch.name
    // An ordinary browser: no account data and no forms, only the way into MAX.
    if (!maxLaunch.value) return show('outside')
  }
  const error = typeof route.query.error === 'string' ? route.query.error : ''
  const step = route.query.step
  if (error || step) await router.replace({ query: next.value === ACCOUNT_PATH ? {} : { next: next.value } })
  if (error) message.value = accountErrorMessage({ error })
  try {
    const me = await api.me()
    user.value = me.user
    if (next.value !== ACCOUNT_PATH) {
      await navigateTo(next.value)
      return
    }
    show('account')
  } catch (failure) {
    if (failure instanceof AccountRequestError && failure.status === 401) show(step === 'signup' ? 'signup' : 'email')
    else fail(failure)
  }
}

async function sendCode() {
  if (busy.value) return
  message.value = ''
  busy.value = true
  try {
    await api.emailStart(email.value.trim())
    code.value = ''
    resendAt.value = Date.now() + 60_000
    notice.value = `Мы отправили код на ${email.value.trim()}. Если письма нет, проверьте папку «Спам».`
    show('code')
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function verifyCode() {
  if (busy.value || !EMAIL_CODE_PATTERN.test(code.value)) return
  message.value = ''
  busy.value = true
  try {
    const result = await api.emailVerify(code.value)
    notice.value = ''
    if (result.status === 'signup_required') {
      signupEmail.value = result.email ?? email.value.trim()
      show('signup')
    } else {
      await afterLogin()
    }
  } catch (error) {
    fail(error)
    if (error instanceof AccountRequestError && ['invalid_challenge', 'too_many_attempts'].includes(error.body.error ?? '')) show('email')
  } finally {
    busy.value = false
  }
}

async function createAccount() {
  if (!canSignup.value) return
  message.value = ''
  busy.value = true
  try {
    await api.signup({
      username: username.value,
      acceptTerms: acceptTerms.value,
      acceptConsent: acceptConsent.value,
      consentVersion: config.value?.consentVersion ?? '',
      termsVersion: config.value?.termsVersion ?? '',
    })
    await afterLogin()
  } catch (error) {
    fail(error)
    if (error instanceof AccountRequestError && error.body.error === 'invalid_ticket') show('email')
  } finally {
    busy.value = false
  }
}

async function logout() {
  busy.value = true
  try {
    await api.logout()
  } catch { /* the server removed the cookie anyway */ }
  busy.value = false
  user.value = null
  cancelDelete()
  closeLink()
  linkNotice.value = ''
  closeNewToken()
  tokenFormOpen.value = false
  pending.value = null
  appTokens.value = []
  notice.value = 'Вы вышли из дневника.'
  show('email')
}

async function deleteAccount() {
  message.value = ''
  busy.value = true
  try {
    await api.deleteAccount()
    user.value = null
    confirmDelete.value = false
    show('deleted')
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

function cancelDelete() {
  confirmDelete.value = false
  message.value = ''
}

function ask(section: 'messengers' | 'tokens', question: string, run: () => Promise<void>) {
  message.value = ''
  pending.value = { section, question, run }
}

async function confirmPending() {
  const action = pending.value
  pending.value = null
  if (action) await action.run()
}

function closeLink() {
  linkOpen.value = false
  linkTarget.value = ''
  telegramLink.value = ''
  message.value = ''
}

// A script opens the one-time link: Metrika link tracking (after an in-site navigation) sees no URL.
function openTelegram() {
  if (telegramLink.value) window.open(telegramLink.value, '_blank', 'noopener,noreferrer')
}

function chooseMax() {
  message.value = ''
  linkNotice.value = ''
  linkTarget.value = 'max'
}

async function startTelegramLink() {
  if (busy.value) return
  message.value = ''
  linkNotice.value = ''
  busy.value = true
  try {
    const result = await api.linkTelegram()
    linkTarget.value = 'telegram'
    telegramLink.value = result.deepLink
    telegramLinkExpiresAt.value = Date.now() + result.expiresIn * 1000
  } catch (error) {
    if (error instanceof AccountRequestError && error.body.error === 'provider_disabled') message.value = 'Привязка Telegram сейчас выключена.'
    else fail(error)
  } finally {
    busy.value = false
  }
}

/** Reads the account again after the person confirmed the link in the bot chat or in MAX. */
async function refreshLinks(quiet = false) {
  const target = linkTarget.value
  if (busy.value || !target) return
  busy.value = true
  try {
    user.value = (await api.me()).user
    if (target === 'telegram' ? telegramLinked.value : maxLinked.value) {
      closeLink()
      linkNotice.value = `${MESSENGER_NAMES[target]} привязан к дневнику.`
    } else if (!quiet) {
      message.value = target === 'telegram'
        ? 'Привязка ещё не подтверждена. Нажмите «Привязать» в чате с ботом.'
        : 'MAX ещё не привязан. Откройте дневник в MAX, войдите и нажмите «Привязать».'
    }
  } catch (error) {
    if (!quiet) fail(error)
  } finally {
    busy.value = false
  }
}

function onVisible() {
  const waiting = (linkTarget.value === 'telegram' && telegramLink.value) || linkTarget.value === 'max'
  if (document.visibilityState === 'visible' && waiting && phase.value === 'account') refreshLinks(true)
}

async function unlinkMessenger(provider: Messenger) {
  if (busy.value) return
  message.value = ''
  linkNotice.value = ''
  busy.value = true
  try {
    await api.unlinkMessenger(provider)
    user.value = (await api.me()).user
    linkNotice.value = `${MESSENGER_NAMES[provider]} отвязан от дневника.`
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

function shortDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString('ru-RU') : ''
}

async function loadAppTokens() {
  if (maxApp.value) return
  try {
    appTokens.value = (await api.appTokens()).tokens
  } catch { /* the list is optional; the rest of the page works */ }
}

async function createAppToken() {
  if (busy.value || !tokenName.value.trim()) return
  message.value = ''
  tokenNotice.value = ''
  busy.value = true
  try {
    const result = await api.createAppToken(tokenName.value.trim(), tokenDays.value)
    newToken.value = result.token
    tokenFormOpen.value = false
    tokenName.value = ''
    await loadAppTokens()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function copyText(text: string, done: string) {
  try {
    await navigator.clipboard.writeText(text)
    tokenNotice.value = done
  } catch {
    tokenNotice.value = 'Не удалось скопировать. Выделите текст и скопируйте вручную.'
  }
}

function closeNewToken() {
  // The page forgets the secret: it is shown once.
  newToken.value = ''
  tokenNotice.value = ''
}

async function revokeAppToken(item: AppToken) {
  if (busy.value) return
  message.value = ''
  busy.value = true
  try {
    await api.revokeAppToken(item.id)
    tokenNotice.value = `Токен «${item.name}» отозван.`
    await loadAppTokens()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

/** Links MAX inside the mini app with the signed launch data of this launch. */
async function linkMax() {
  if (busy.value || !maxLaunch.value) return
  message.value = ''
  linkNotice.value = ''
  busy.value = true
  try {
    await api.linkMax(maxLaunch.value)
    user.value = (await api.me()).user
    linkNotice.value = 'MAX привязан к дневнику.'
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

function changeEmail() {
  message.value = ''
  notice.value = ''
  show('email')
}

onMounted(() => {
  clock = setInterval(() => { now.value = Date.now() }, 1000)
  document.addEventListener('visibilitychange', onVisible)
  load()
})
onBeforeUnmount(() => {
  if (clock) clearInterval(clock)
  document.removeEventListener('visibilitychange', onVisible)
})
</script>

<template>
  <main id="main-content" class="scanner-page account-page">
    <section class="account-card" aria-live="polite">
      <p class="step-label">ВИННЫЙ ДНЕВНИК</p>

      <template v-if="phase === 'loading'">
        <h1 ref="heading" tabindex="-1">Винный дневник</h1>
        <p class="account-lead account-loading"><span class="spinner" aria-hidden="true" />Загрузка…</p>
      </template>

      <template v-else-if="phase === 'disabled'">
        <h1 ref="heading" tabindex="-1">Дневник пока не подключён</h1>
        <p class="account-lead">На этом сайте вход в дневник выключен. Поиск вина по фото работает.</p>
        <NuxtLink class="button primary" to="/">Найти вино по фото</NuxtLink>
      </template>

      <template v-else-if="phase === 'unavailable'">
        <h1 ref="heading" tabindex="-1">Дневник временно недоступен</h1>
        <p class="account-lead">Поиск вина по фото работает как обычно. Попробуйте открыть дневник позже.</p>
        <div class="account-actions">
          <button class="button primary" type="button" @click="message = ''; load()">Повторить</button>
          <NuxtLink class="button secondary" to="/">Найти вино по фото</NuxtLink>
        </div>
      </template>

      <template v-else-if="phase === 'outside'">
        <h1 ref="heading" tabindex="-1">Откройте дневник в MAX</h1>
        <p class="account-lead">Эта страница работает внутри мессенджера MAX.</p>
        <template v-if="config?.maxAppLink">
          <img class="account-qr" :src="MAX_QR_URL" width="200" height="200" alt="QR-код ссылки на дневник в MAX">
          <a class="button primary" :href="config.maxAppLink">Открыть в MAX</a>
        </template>
      </template>

      <template v-else-if="phase === 'email'">
        <h1 ref="heading" tabindex="-1">Вход в дневник</h1>
        <p v-if="maxApp" class="account-lead">Войдите по коду из письма, чтобы привязать MAX к своему дневнику. Аккаунт создаётся при первом входе.</p>
        <p v-else class="account-lead">Личный дневник находок, оценок и предпочтений. Аккаунт создаётся при первом входе.</p>
        <p v-if="notice" class="account-notice">{{ notice }}</p>
        <form class="account-form" @submit.prevent="sendCode">
          <label for="account-email">Электронная почта</label>
          <input id="account-email" v-model="email" type="email" name="email" autocomplete="email" inputmode="email" required maxlength="254" :disabled="busy">
          <button class="button primary" type="submit" :disabled="busy || !email.trim()">Получить код</button>
        </form>
        <template v-if="yandexEnabled && !maxApp">
          <p class="account-divider"><span>или</span></p>
          <a class="button secondary account-yandex" :href="yandexHref"><span class="yandex-mark" aria-hidden="true">Я</span>Войти с Яндекс ID</a>
        </template>
      </template>

      <template v-else-if="phase === 'code'">
        <h1 ref="heading" tabindex="-1">Введите код из письма</h1>
        <p v-if="notice" class="account-notice">{{ notice }}</p>
        <form class="account-form" @submit.prevent="verifyCode">
          <label for="account-code">Код из 6 цифр</label>
          <input id="account-code" v-model="code" class="ym-disable-keys account-code" type="text" name="one-time-code" autocomplete="one-time-code" inputmode="numeric" pattern="\d{6}" maxlength="6" required :disabled="busy">
          <button class="button primary" type="submit" :disabled="busy || code.length !== 6">Войти</button>
        </form>
        <div class="account-links">
          <button type="button" class="account-link" :disabled="busy || resendIn > 0" @click="sendCode">{{ resendIn > 0 ? `Отправить код ещё раз через ${resendIn} с` : 'Отправить код ещё раз' }}</button>
          <button type="button" class="account-link" :disabled="busy" @click="changeEmail">Изменить адрес</button>
        </div>
      </template>

      <template v-else-if="phase === 'signup'">
        <h1 ref="heading" tabindex="-1">Новый дневник</h1>
        <p class="account-lead">{{ signupEmail ? `Почта ${signupEmail} подтверждена.` : 'Вход подтверждён.' }} Выберите имя пользователя.</p>
        <form class="account-form" @submit.prevent="createAccount">
          <label for="account-username">Имя пользователя</label>
          <input id="account-username" v-model="username" type="text" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" minlength="3" maxlength="32" required :disabled="busy" @input="username = username.toLowerCase()">
          <p class="account-hint">От 3 до 32 символов: строчные латинские буквы, цифры, точка, дефис, подчёркивание.</p>
          <label class="account-check"><input v-model="acceptTerms" type="checkbox" :disabled="busy"> <span>Принимаю <a href="/terms" target="_blank" rel="noopener">условия использования</a></span></label>
          <label class="account-check"><input v-model="acceptConsent" type="checkbox" :disabled="busy"> <span>Даю <a href="/privacy" target="_blank" rel="noopener">согласие на обработку персональных данных</a>: имени пользователя и адреса почты или идентификатора Яндекс ID</span></label>
          <button class="button primary" type="submit" :disabled="!canSignup">Создать дневник</button>
        </form>
      </template>

      <template v-else-if="phase === 'account' && user">
        <h1 ref="heading" tabindex="-1">Винный дневник</h1>
        <p class="account-lead">Вы вошли как <strong>{{ user.username }}</strong>.</p>
        <div v-if="maxApp && !maxLinked" class="account-panel" role="group" aria-labelledby="max-link-heading">
          <template v-if="maxEnabled">
            <h2 id="max-link-heading" class="account-subheading">Привязать MAX-аккаунт{{ maxName ? ` «${maxName}»` : '' }} к дневнику {{ user.username }}?</h2>
            <p>Бот MAX сможет сохранять ваши находки в этот дневник. Если имя MAX не ваше, не привязывайте.</p>
            <div class="account-actions">
              <button class="button primary" type="button" :disabled="busy" @click="linkMax">Привязать</button>
            </div>
          </template>
          <p v-else id="max-link-heading">Привязка MAX сейчас выключена.</p>
        </div>
        <p class="account-notice">Скоро здесь появятся история поисков, оценки вин и ваши предпочтения.</p>
        <h2 class="account-subheading">Способы входа</h2>
        <ul class="account-identities">
          <li v-for="item in identities.login" :key="item.key"><span>{{ item.label }}</span><span>{{ item.value }}</span></li>
        </ul>
        <template v-if="showMessengers">
          <h2 class="account-subheading">Связанные мессенджеры</h2>
          <p class="account-hint">Через них нельзя войти в дневник: они только сохраняют находки.</p>
          <ul v-if="identities.linked.length" class="account-identities">
            <li v-for="item in identities.linked" :key="item.key">
              <span>{{ item.label }}</span>
              <span class="account-identity-state">{{ item.value }}<button v-if="!maxApp || item.key === 'max'" type="button" class="account-link" :disabled="busy" @click="ask('messengers', `Отвязать ${item.label} от дневника?`, () => unlinkMessenger(item.key as Messenger))">Отвязать</button></span>
            </li>
          </ul>
          <div v-if="pending?.section === 'messengers'" class="account-confirm" role="group" aria-label="Подтверждение">
            <p>{{ pending.question }}</p>
            <div class="account-actions">
              <button class="button primary account-danger-fill" type="button" :disabled="busy" @click="confirmPending">Да, отвязать</button>
              <button class="button secondary" type="button" :disabled="busy" @click="pending = null">Отмена</button>
            </div>
          </div>
          <p v-if="linkNotice" class="account-notice" role="status">{{ linkNotice }}</p>
          <template v-if="canLinkMessenger">
            <div v-if="!linkOpen" class="account-actions">
              <button class="button secondary" type="button" :disabled="busy" @click="linkOpen = true; linkNotice = ''">Привязать мессенджер</button>
            </div>
            <div v-else class="account-panel" role="group" aria-labelledby="link-heading">
              <h3 id="link-heading" class="account-subheading">Привязать мессенджер</h3>
              <template v-if="linkTarget === 'max'">
                <p>Отсканируйте QR-код телефоном или откройте ссылку в MAX. В дневнике внутри MAX войдите по коду из письма и нажмите «Привязать».</p>
                <img class="account-qr" :src="MAX_QR_URL" width="200" height="200" alt="QR-код ссылки на дневник в MAX">
                <div class="account-actions">
                  <a class="button primary" :href="config?.maxAppLink" target="_blank" rel="noopener noreferrer">Открыть в MAX</a>
                  <button class="button secondary" type="button" :disabled="busy" @click="refreshLinks()">Я привязал</button>
                  <button class="button secondary" type="button" :disabled="busy" @click="closeLink">Отмена</button>
                </div>
              </template>
              <template v-else-if="!telegramLink">
                <p>Выберите мессенджер.</p>
                <div class="account-actions">
                  <button v-if="canLinkTelegram" class="button primary" type="button" :disabled="busy" @click="startTelegramLink">Telegram</button>
                  <button v-if="canLinkMax" class="button primary" type="button" :disabled="busy" @click="chooseMax">MAX</button>
                      <button class="button secondary" type="button" :disabled="busy" @click="closeLink">Отмена</button>
                </div>
              </template>
              <template v-else-if="telegramLinkExpired">
                <p>Ссылка устарела. Создайте новую.</p>
                <div class="account-actions">
                  <button class="button primary" type="button" :disabled="busy" @click="startTelegramLink">Новая ссылка</button>
                  <button class="button secondary" type="button" :disabled="busy" @click="closeLink">Отмена</button>
                </div>
              </template>
              <template v-else>
                <p>Откройте Telegram и нажмите «Привязать» в чате с ботом. Ссылка действует 10 минут и работает один раз. Не пересылайте её: по ней можно привязать чужой Telegram к вашему дневнику.</p>
                <div class="account-actions">
                  <button class="button primary" type="button" @click="openTelegram">Открыть Telegram</button>
                  <button class="button secondary" type="button" :disabled="busy" @click="refreshLinks()">Я привязал</button>
                  <button class="button secondary" type="button" :disabled="busy" @click="closeLink">Отмена</button>
                </div>
              </template>
            </div>
          </template>
        </template>
        <template v-if="!maxApp">
          <h2 class="account-subheading">Токены приложений</h2>
          <p class="account-hint">Токен даёт MCP-клиенту (Claude, Cursor и другим) доступ только на чтение: имя пользователя, предпочтения и найденные вина. Фото, почта и способы входа недоступны.</p>
          <ul v-if="appTokens.length" class="account-identities">
            <li v-for="item in appTokens" :key="item.id">
              <span>{{ item.name }}</span>
              <span class="account-identity-state">до {{ shortDate(item.expiresAt) }}<template v-if="item.lastUsedAt"> · использован {{ shortDate(item.lastUsedAt) }}</template><button type="button" class="account-link" :disabled="busy" @click="ask('tokens', `Отозвать токен «${item.name}»? Приложение потеряет доступ к дневнику.`, () => revokeAppToken(item))">Отозвать</button></span>
            </li>
          </ul>
          <div v-if="pending?.section === 'tokens'" class="account-confirm" role="group" aria-label="Подтверждение">
            <p>{{ pending.question }}</p>
            <div class="account-actions">
              <button class="button primary account-danger-fill" type="button" :disabled="busy" @click="confirmPending">Да, отозвать</button>
              <button class="button secondary" type="button" :disabled="busy" @click="pending = null">Отмена</button>
            </div>
          </div>
          <p v-if="tokenNotice" class="account-notice" role="status">{{ tokenNotice }}</p>
          <div v-if="newToken" class="account-panel" role="group" aria-labelledby="new-token-heading">
            <h3 id="new-token-heading" class="account-subheading">Новый токен</h3>
            <p><strong>Токен показывается один раз.</strong> Любой, у кого он есть, может читать ваш дневник. Данные увидит сервис, которому вы передадите токен.</p>
            <label for="account-new-token" class="account-hint">Токен</label>
            <input id="account-new-token" class="account-secret ym-disable-keys ym-hide-content" type="text" readonly :value="newToken" @focus="($event.target as HTMLInputElement).select()">
            <label for="account-mcp-config" class="account-hint">Настройки MCP-клиента: укажите пути к node и к mcp/src/cli.mjs</label>
            <textarea id="account-mcp-config" class="account-secret account-config ym-disable-keys ym-hide-content" readonly rows="11" :value="newTokenConfig" />
            <div class="account-actions">
              <button class="button primary" type="button" @click="copyText(newToken, 'Токен скопирован.')">Скопировать токен</button>
              <button class="button secondary" type="button" @click="copyText(newTokenConfig, 'Настройки скопированы.')">Скопировать настройки</button>
              <button class="button secondary" type="button" @click="closeNewToken">Готово</button>
            </div>
          </div>
          <form v-else-if="tokenFormOpen" class="account-panel account-form" @submit.prevent="createAppToken">
            <h3 class="account-subheading">Создать токен</h3>
            <p>Любой, у кого есть токен, может читать ваш дневник. Данные увидит сервис, которому вы передадите токен.</p>
            <label for="account-token-name">Название</label>
            <input id="account-token-name" v-model="tokenName" type="text" maxlength="64" placeholder="Claude на ноутбуке" required :disabled="busy">
            <label for="account-token-days">Срок действия</label>
            <select id="account-token-days" v-model.number="tokenDays" class="account-select" :disabled="busy">
              <option :value="30">30 дней</option>
              <option :value="90">90 дней</option>
              <option :value="365">365 дней</option>
            </select>
            <div class="account-actions">
              <button class="button primary" type="submit" :disabled="busy || !tokenName.trim()">Создать</button>
              <button class="button secondary" type="button" :disabled="busy" @click="tokenFormOpen = false; message = ''">Отмена</button>
            </div>
          </form>
          <div v-else class="account-actions">
            <button class="button secondary" type="button" :disabled="busy || appTokens.length >= 5" @click="tokenFormOpen = true; tokenNotice = ''">Создать токен</button>
          </div>
        </template>
        <div class="account-actions">
          <button class="button secondary" type="button" :disabled="busy" @click="logout">Выйти</button>
          <button v-if="!confirmDelete" class="button secondary account-danger" type="button" :disabled="busy" @click="confirmDelete = true">Удалить аккаунт</button>
        </div>
        <div v-if="confirmDelete" class="account-confirm" role="group" aria-labelledby="delete-heading">
          <h2 id="delete-heading" class="account-subheading">Удалить аккаунт {{ user.username }} и все данные?</h2>
          <p>Удалятся имя пользователя, способы входа и все записи дневника. Это действие нельзя отменить.</p>
          <div class="account-actions">
            <button class="button primary account-danger-fill" type="button" :disabled="busy" @click="deleteAccount">Удалить навсегда</button>
            <button class="button secondary" type="button" :disabled="busy" @click="cancelDelete">Отмена</button>
          </div>
        </div>
      </template>

      <template v-else-if="phase === 'deleted'">
        <h1 ref="heading" tabindex="-1">Аккаунт удалён</h1>
        <p class="account-lead">Все данные дневника удалены.</p>
        <NuxtLink class="button primary" to="/">Найти вино по фото</NuxtLink>
      </template>

      <p v-if="message" class="inline-error" role="alert"><AppIcon name="info" />{{ message }}</p>
    </section>
  </main>
</template>
