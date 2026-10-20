import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import { SHELF_LENS_ANDROID_RELEASE } from '#shared/shelf-lens-android'

export default defineEventHandler(async event => {
  assertMethod(event, ['GET', 'HEAD'])
  const config = useRuntimeConfig(event)
  const apkPath = String(config.shelfLensApkPath || '')
  const apkStat = await stat(apkPath).catch(() => null)
  if (!apkStat?.isFile() || apkStat.size !== SHELF_LENS_ANDROID_RELEASE.apkBytes) {
    throw createError({ statusCode: 404, statusMessage: 'APK is not available' })
  }

  setHeaders(event, {
    'Content-Type': 'application/vnd.android.package-archive',
    'Content-Length': String(apkStat.size),
    'Content-Disposition': `attachment; filename="${SHELF_LENS_ANDROID_RELEASE.apkFileName}"`,
    'Cache-Control': 'public, max-age=3600, must-revalidate',
    'X-Content-Type-Options': 'nosniff',
  })
  if (event.method === 'HEAD') return ''
  return sendStream(event, createReadStream(apkPath))
})
