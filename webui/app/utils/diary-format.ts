// Dates of the «Винный дневник» lists. The service gives ISO times in UTC and history days as
// YYYY-MM-DD in Moscow time (plan 07, D6).
const TIME_ZONE = 'Europe/Moscow'

const longDate = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: TIME_ZONE })
const shortDate = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', timeZone: TIME_ZONE })
const yearOf = new Intl.DateTimeFormat('ru-RU', { year: 'numeric', timeZone: TIME_ZONE })

/** «19 октября» in the current year, «3 июня 2025» in another year. */
export function diaryDate(iso: string, now = new Date()): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return yearOf.format(date) === yearOf.format(now) ? shortDate.format(date) : longDate.format(date)
}

/** A history day YYYY-MM-DD as «19 октября 2026». */
export function diaryDay(day: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day)
  if (!match) return day
  // Noon UTC is the same calendar day in Moscow.
  return longDate.format(new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]), 12)))
}

