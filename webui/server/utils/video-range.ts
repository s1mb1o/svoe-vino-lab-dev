// Only one range is needed by the embedded video player. Bound every range to the asset.
export function videoRange(header: string | undefined, size: number): { start: number; end: number } | null | false {
  if (!header) return null
  const match = /^bytes=(\d*)-(\d*)$/.exec(header)
  if (!match || (!match[1] && !match[2])) return false
  if (!match[1]) {
    const suffix = Number(match[2])
    if (!Number.isSafeInteger(suffix) || suffix <= 0) return false
    return { start: Math.max(0, size - suffix), end: size - 1 }
  }
  const start = Number(match[1])
  const end = match[2] ? Number(match[2]) : size - 1
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start >= size || start > end) return false
  return { start, end: Math.min(end, size - 1) }
}
