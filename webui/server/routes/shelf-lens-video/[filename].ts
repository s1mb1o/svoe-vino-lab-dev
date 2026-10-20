import { videoRange } from '../../utils/video-range'

const filenames = new Set(['hero-loop.mp4', 'shelf-lens-demo.mp4'])

export default defineEventHandler(async event => {
  if (event.method !== 'GET' && event.method !== 'HEAD') {
    setHeader(event, 'Allow', 'GET, HEAD')
    throw createError({ statusCode: 405, statusMessage: 'Method Not Allowed' })
  }
  const filename = getRouterParam(event, 'filename') || ''
  if (!filenames.has(filename)) throw createError({ statusCode: 404 })
  // These are two fixed, compressed assets. No uploaded or user-selected path is read.
  const data = await useStorage('assets:server').getItemRaw<Buffer>(`shelf-lens/${filename}`)
  if (!data) throw createError({ statusCode: 404 })
  const body = Buffer.from(data)
  setHeaders(event, { 'Content-Type': 'video/mp4', 'Accept-Ranges': 'bytes', 'X-Content-Type-Options': 'nosniff' })
  // Ignore a conditional range when no matching validator is supplied by this route.
  const range = videoRange(getHeader(event, 'if-range') ? undefined : getHeader(event, 'range'), body.length)
  if (range === false) {
    setResponseStatus(event, 416)
    setHeader(event, 'Content-Range', `bytes */${body.length}`)
    return ''
  }
  if (range) {
    setResponseStatus(event, 206)
    setHeaders(event, { 'Content-Range': `bytes ${range.start}-${range.end}/${body.length}`, 'Content-Length': String(range.end - range.start + 1) })
    return event.method === 'HEAD' ? '' : body.subarray(range.start, range.end + 1)
  }
  setHeader(event, 'Content-Length', body.length)
  return event.method === 'HEAD' ? '' : body
})
