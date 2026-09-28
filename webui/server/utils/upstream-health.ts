const PREDICTION_PATH = /\/v1\/eval\/predict\/?$/

export function predictionHealthUrl(predictionEndpoint: unknown): URL {
  if (typeof predictionEndpoint !== 'string' || !predictionEndpoint) throw new Error('Prediction endpoint is missing')
  const url = new URL(predictionEndpoint)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || !PREDICTION_PATH.test(url.pathname)) {
    throw new Error('Prediction endpoint is invalid')
  }
  url.pathname = url.pathname.replace(PREDICTION_PATH, '/healthz')
  return url
}

export async function predictionApiAvailable(predictionEndpoint: unknown, options: { fetch?: typeof fetch; timeoutMs?: number } = {}): Promise<boolean> {
  try {
    const response = await (options.fetch || fetch)(predictionHealthUrl(predictionEndpoint), {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(options.timeoutMs ?? 2000),
      redirect: 'error',
      cache: 'no-store',
    })
    if (!response.ok) return false
    const body = await response.json() as unknown
    return Boolean(body && typeof body === 'object' && !Array.isArray(body) && (body as { status?: unknown }).status === 'ok')
  } catch {
    return false
  }
}
