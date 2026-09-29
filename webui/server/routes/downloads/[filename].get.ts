import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import { ANDROID_RELEASE } from '#shared/android'

export default defineEventHandler(async event => {
  const filename = getRouterParam(event, 'filename')
  if (filename !== ANDROID_RELEASE.apkFileName) {
    throw createError({ statusCode: 404, statusMessage: 'APK not found' })
  }

  const config = useRuntimeConfig(event)
  const apkPath = String(config.androidApkPath || '')
  let apkStat
  try {
    apkStat = await stat(apkPath)
  } catch {
    throw createError({ statusCode: 404, statusMessage: 'APK is not available' })
  }
  if (!apkStat.isFile()) {
    throw createError({ statusCode: 404, statusMessage: 'APK is not available' })
  }

  setHeaders(event, {
    'Content-Type': 'application/vnd.android.package-archive',
    'Content-Length': String(apkStat.size),
    'Content-Disposition': `attachment; filename="${ANDROID_RELEASE.apkFileName}"`,
    'Cache-Control': 'public, max-age=3600, must-revalidate',
    'X-Content-Type-Options': 'nosniff',
  })
  return sendStream(event, createReadStream(apkPath))
})
