import { isAxiosError } from 'axios'

/**
 * Pulls a field-level validation message out of a 400 response
 * (`{ detail: [{ msg, loc, type }] }`), or null for anything else.
 */
export function firstValidationMessage(error: unknown): string | null {
  if (!isAxiosError(error) || error.response?.status !== 400) return null
  const detail = error.response.data?.detail
  if (!Array.isArray(detail)) return null
  return typeof detail[0]?.msg === 'string' ? detail[0].msg : null
}
