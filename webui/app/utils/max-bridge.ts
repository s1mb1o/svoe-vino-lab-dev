// MAX Bridge of the mini app (plan 05). Load it only on the MAX mini-app page.
export const MAX_BRIDGE_URL = 'https://st.max.ru/js/max-web-app.js'

export interface MaxLaunch {
  // The signed launch string. Only the account service trusts it, after its checks.
  initData: string
  // The MAX name from initDataUnsafe. It is for display only: the person checks it before «Привязать».
  name: string
}

type MaxWebApp = { initData?: unknown; initDataUnsafe?: { user?: { first_name?: unknown; last_name?: unknown } } }

/** Loads the MAX Bridge and reads the launch data. Outside MAX the launch data is empty. */
export async function readMaxLaunch(timeoutMs = 5000): Promise<MaxLaunch> {
  const scope = window as Window & { WebApp?: MaxWebApp }
  if (!scope.WebApp) {
    await new Promise<void>((resolve) => {
      const script = document.createElement('script')
      const timer = setTimeout(resolve, timeoutMs)
      const done = () => {
        clearTimeout(timer)
        resolve()
      }
      script.src = MAX_BRIDGE_URL
      script.async = true
      script.onload = done
      script.onerror = done
      document.head.appendChild(script)
    })
  }
  const app = scope.WebApp
  const initData = typeof app?.initData === 'string' ? app.initData : ''
  const user = app?.initDataUnsafe?.user
  const name = [user?.first_name, user?.last_name].filter(part => typeof part === 'string' && part.trim()).join(' ').trim()
  return { initData, name: name.slice(0, 128) }
}
