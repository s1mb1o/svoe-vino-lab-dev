import { describe, expect, it } from 'vitest'
import { videoRange } from '../server/utils/video-range'

describe('Shelf Lens video byte ranges', () => {
  it('supports full responses, bounded ranges, open ranges, and suffixes', () => {
    expect(videoRange(undefined, 100)).toBeNull()
    expect(videoRange('bytes=20-29', 100)).toEqual({ start: 20, end: 29 })
    expect(videoRange('bytes=80-', 100)).toEqual({ start: 80, end: 99 })
    expect(videoRange('bytes=-10', 100)).toEqual({ start: 90, end: 99 })
    expect(videoRange('bytes=80-150', 100)).toEqual({ start: 80, end: 99 })
    expect(videoRange('bytes=-150', 100)).toEqual({ start: 0, end: 99 })
  })
  it.each(['bytes=100-', 'bytes=20-10', 'bytes=-0', 'bytes=-', 'bytes=0-1,4-5', 'items=0-1', 'bytes=1.2-9', 'bytes=9007199254740992-'])('rejects an invalid or unsatisfiable range: %s', header => {
    expect(videoRange(header, 100)).toBe(false)
  })
})
