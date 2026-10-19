import { AGE_CONFIRMATION_KEY } from '#shared/age'

export { AGE_CONFIRMATION_KEY }

type AgeStorage = Pick<Storage, 'getItem' | 'setItem'>

export function hasAgeConfirmation(storage: AgeStorage): boolean {
  try { return storage.getItem(AGE_CONFIRMATION_KEY) === 'yes' } catch { return false }
}

export function saveAgeConfirmation(storage: AgeStorage): boolean {
  try { storage.setItem(AGE_CONFIRMATION_KEY, 'yes'); return true } catch { return false }
}
