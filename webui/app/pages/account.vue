<script setup lang="ts">
import { ACCOUNT_PATH, EMAIL_CODE_PATTERN, USERNAME_PATTERN, accountErrorMessage, safeNextPath } from '#shared/account'
import { AccountRequestError, useAccountApi, type AccountSiteConfig, type AccountUser } from '~/composables/useAccountApi'

const title = 'Винный дневник — Что за вино?'
useSeoMeta({ title, robots: 'noindex, nofollow, noarchive' })

type Phase = 'loading' | 'disabled' | 'unavailable' | 'email' | 'code' | 'signup' | 'account' | 'deleted'

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
const confirmDelete = ref(false)
// Account deletion needs a login in the last 15 minutes (service rule). After reauth_required the
// confirmation panel offers a fresh login by the account's own email code or Yandex ID.
const reauthNeeded = ref(false)
const reauthSent = ref(false)
const reauthCode = ref('')
const resendAt = ref(0)
const now = ref(Date.now())
const heading = ref<HTMLElement>()
let clock: ReturnType<typeof setInterval> | undefined

const next = computed(() => safeNextPath(route.query.next))
const yandexEnabled = computed(() => Boolean(config.value?.providers?.yandex))
const yandexHref = computed(() => `/api/account/yandex/start?next=${encodeURIComponent(next.value)}`)
const usernameValid = computed(() => USERNAME_PATTERN.test(username.value))
const canSignup = computed(() => usernameValid.value && acceptTerms.value && acceptConsent.value && !busy.value)
const accountEmail = computed(() => user.value?.identities.find(item => item.provider === 'email')?.email ?? '')
const hasYandex = computed(() => Boolean(user.value?.identities.some(item => item.provider === 'yandex')))
const reauthYandexHref = computed(() => `/api/account/yandex/start?intent=reauth&next=${encodeURIComponent('/account?confirm=delete')}`)
const resendIn = computed(() => Math.max(0, Math.ceil((resendAt.value - now.value) / 1000)))
const identities = computed(() => (user.value?.identities ?? []).map(item => item.provider === 'email'
  ? { key: 'email', label: 'Почта', value: item.email ?? '' }
  : item.provider === 'yandex'
    ? { key: 'yandex', label: 'Яндекс ID', value: 'привязан' }
    : { key: item.provider, label: item.provider, value: 'привязан' }))

function show(nextPhase: Phase) {
  phase.value = nextPhase
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
  const error = typeof route.query.error === 'string' ? route.query.error : ''
  const step = route.query.step
  const confirmAfterLogin = route.query.confirm === 'delete'
  if (error || step || confirmAfterLogin) await router.replace({ query: next.value === ACCOUNT_PATH ? {} : { next: next.value } })
  if (error) message.value = accountErrorMessage({ error })
  try {
    const me = await api.me()
    user.value = me.user
    if (next.value !== ACCOUNT_PATH) {
      await navigateTo(next.value)
      return
    }
    confirmDelete.value = confirmAfterLogin
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
    reauthNeeded.value = false
    show('deleted')
  } catch (error) {
    if (error instanceof AccountRequestError && error.body.error === 'reauth_required') {
      reauthNeeded.value = true
      reauthSent.value = false
    } else {
      fail(error)
    }
  } finally {
    busy.value = false
  }
}

async function sendReauthCode() {
  if (busy.value || !accountEmail.value) return
  message.value = ''
  busy.value = true
  try {
    await api.emailStart(accountEmail.value)
    reauthCode.value = ''
    reauthSent.value = true
    resendAt.value = Date.now() + 60_000
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function confirmAndDelete() {
  if (busy.value || !EMAIL_CODE_PATTERN.test(reauthCode.value)) return
  message.value = ''
  busy.value = true
  try {
    const result = await api.emailVerify(reauthCode.value)
    if (result.status !== 'session') throw new AccountRequestError(400, { error: 'invalid_challenge' })
  } catch (error) {
    fail(error)
    busy.value = false
    return
  }
  busy.value = false
  reauthSent.value = false
  await deleteAccount()
}

function cancelDelete() {
  confirmDelete.value = false
  reauthNeeded.value = false
  reauthSent.value = false
  message.value = ''
}

function changeEmail() {
  message.value = ''
  notice.value = ''
  show('email')
}

onMounted(() => {
  clock = setInterval(() => { now.value = Date.now() }, 1000)
  load()
})
onBeforeUnmount(() => clock && clearInterval(clock))
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

      <template v-else-if="phase === 'email'">
        <h1 ref="heading" tabindex="-1">Вход в дневник</h1>
        <p class="account-lead">Личный дневник находок, оценок и предпочтений. Аккаунт создаётся при первом входе.</p>
        <p v-if="notice" class="account-notice">{{ notice }}</p>
        <form class="account-form" @submit.prevent="sendCode">
          <label for="account-email">Электронная почта</label>
          <input id="account-email" v-model="email" type="email" name="email" autocomplete="email" inputmode="email" required maxlength="254" :disabled="busy">
          <button class="button primary" type="submit" :disabled="busy || !email.trim()">Получить код</button>
        </form>
        <template v-if="yandexEnabled">
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
        <p class="account-notice">Скоро здесь появятся история поисков, оценки вин и ваши предпочтения.</p>
        <h2 class="account-subheading">Способы входа</h2>
        <ul class="account-identities">
          <li v-for="item in identities" :key="item.key"><span>{{ item.label }}</span><span>{{ item.value }}</span></li>
        </ul>
        <div class="account-actions">
          <button class="button secondary" type="button" :disabled="busy" @click="logout">Выйти</button>
          <button v-if="!confirmDelete" class="button secondary account-danger" type="button" :disabled="busy" @click="confirmDelete = true; reauthNeeded = false">Удалить аккаунт</button>
        </div>
        <div v-if="confirmDelete" class="account-confirm" role="group" aria-labelledby="delete-heading">
          <h2 id="delete-heading" class="account-subheading">Удалить аккаунт {{ user.username }} и все данные?</h2>
          <p>Удалятся имя пользователя, способы входа и все записи дневника. Это действие нельзя отменить.</p>
          <div v-if="!reauthNeeded" class="account-actions">
            <button class="button primary account-danger-fill" type="button" :disabled="busy" @click="deleteAccount">Удалить навсегда</button>
            <button class="button secondary" type="button" :disabled="busy" @click="cancelDelete">Отмена</button>
          </div>
          <template v-else>
            <p class="account-notice">Чтобы удалить аккаунт, подтвердите, что это вы: нужен вход не раньше чем 15 минут назад.</p>
            <form v-if="accountEmail && reauthSent" class="account-form" @submit.prevent="confirmAndDelete">
              <label for="account-reauth-code">Код из письма на {{ accountEmail }}</label>
              <input id="account-reauth-code" v-model="reauthCode" class="ym-disable-keys account-code" type="text" name="one-time-code" autocomplete="one-time-code" inputmode="numeric" pattern="\d{6}" maxlength="6" required :disabled="busy">
              <button class="button primary account-danger-fill" type="submit" :disabled="busy || reauthCode.length !== 6">Подтвердить и удалить</button>
            </form>
            <div class="account-actions">
              <button v-if="accountEmail && !reauthSent" class="button primary" type="button" :disabled="busy" @click="sendReauthCode">Подтвердить кодом из письма</button>
              <button v-if="accountEmail && reauthSent" class="button secondary" type="button" :disabled="busy || resendIn > 0" @click="sendReauthCode">{{ resendIn > 0 ? `Отправить код ещё раз через ${resendIn} с` : 'Отправить код ещё раз' }}</button>
              <a v-if="hasYandex" class="button secondary account-yandex" :href="reauthYandexHref"><span class="yandex-mark" aria-hidden="true">Я</span>Подтвердить через Яндекс ID</a>
              <button class="button secondary" type="button" :disabled="busy" @click="cancelDelete">Отмена</button>
            </div>
          </template>
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
