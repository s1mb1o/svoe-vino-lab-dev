import { METRIKA_COUNTER_ID } from '../../shared/metrika'

type MetrikaWindow = Window & {
  ym?: (counterId: number, method: string, url: string, options: { referer: string }) => void
}

export default defineNuxtPlugin((nuxtApp) => {
  const router = useRouter()
  nuxtApp.hook('app:mounted', () => {
    router.afterEach((to, from, failure) => {
      if (failure || to.fullPath === from.fullPath) return
      const metrika = (window as MetrikaWindow).ym
      metrika?.(METRIKA_COUNTER_ID, 'hit', new URL(to.fullPath, location.origin).href, {
        referer: new URL(from.fullPath, location.origin).href,
      })
    })
  })
})
