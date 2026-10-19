import { METRIKA_COUNTER_ID } from '../../shared/metrika'
import { isAccountPath } from '../../shared/account'

type MetrikaWindow = Window & {
  ym?: (counterId: number, method: string, url: string, options: { referer: string }) => void
}

export default defineNuxtPlugin((nuxtApp) => {
  const router = useRouter()
  // Metrika reads document.title when it sends a hit. Nuxt calls page:loading:end once for each
  // navigation. For a new page, the call comes after page:finish, which queues the head render
  // that sets the new title. The timer below runs after that render.
  const pendingHits: Array<() => void> = []

  nuxtApp.hook('page:loading:end', () => {
    setTimeout(() => pendingHits.splice(0).forEach(send => send()), 0)
  })
  nuxtApp.hook('app:mounted', () => {
    router.afterEach((to, from, failure) => {
      if (failure || to.fullPath === from.fullPath) return
      // No hits for the account pages of «Винный дневник».
      if (isAccountPath(to.path)) return
      const url = new URL(to.fullPath, location.origin).href
      const referer = new URL(from.fullPath, location.origin).href
      pendingHits.push(() => (window as MetrikaWindow).ym?.(METRIKA_COUNTER_ID, 'hit', url, { referer }))
    })
  })
})
