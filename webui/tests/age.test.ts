import { describe, expect, it } from 'vitest'
import { AGE_CONFIRMATION_KEY, hasAgeConfirmation, saveAgeConfirmation } from '../app/utils/age'

describe('age confirmation', () => {
  it('accepts only the explicit saved value', () => {
    expect(hasAgeConfirmation({ getItem: () => 'yes', setItem: () => undefined })).toBe(true)
    expect(hasAgeConfirmation({ getItem: () => 'true', setItem: () => undefined })).toBe(false)
    expect(hasAgeConfirmation({ getItem: () => null, setItem: () => undefined })).toBe(false)
  })

  it('stores the versioned confirmation without personal data', () => {
    const values = new Map<string, string>()
    const storage = { getItem: (key: string) => values.get(key) || null, setItem: (key: string, value: string) => values.set(key, value) }
    expect(saveAgeConfirmation(storage)).toBe(true)
    expect([...values.entries()]).toEqual([[AGE_CONFIRMATION_KEY, 'yes']])
  })

  it('fails closed when storage is unavailable', () => {
    expect(hasAgeConfirmation({ getItem: () => { throw new Error('blocked') }, setItem: () => undefined })).toBe(false)
    expect(saveAgeConfirmation({ getItem: () => null, setItem: () => { throw new Error('blocked') } })).toBe(false)
  })
})
