import { isAxiosError } from 'axios'

function firstDetailMessage(error: unknown, status?: number): string | null {
  if (!isAxiosError(error) || !error.response) return null
  if (status !== undefined && error.response.status !== status) return null
  const detail = error.response.data?.detail
  if (!Array.isArray(detail)) return null
  return typeof detail[0]?.msg === 'string' ? detail[0].msg : null
}

/**
 * Pulls a field-level validation message out of a 400 response
 * (`{ detail: [{ msg, loc, type }] }`), or null for anything else.
 */
export function firstValidationMessage(error: unknown): string | null {
  return firstDetailMessage(error, 400)
}

/**
 * A Russian message for a failed version upload, chosen by the status
 * the backend answered with.
 */
export function describeVersionUploadError(error: unknown): string {
  if (!isAxiosError(error)) return 'Не удалось загрузить версию.'
  switch (error.response?.status) {
    case 409:
      return 'Версия с таким именем уже есть в проекте.'
    case 413: {
      const limit = /Max size is (\d+) MB/.exec(firstDetailMessage(error) ?? '')
      return limit
        ? `Файл слишком большой. Максимальный размер — ${limit[1]} МБ.`
        : 'Файл слишком большой.'
    }
    case 400:
      return 'Не удалось обработать файл. Поддерживаются mp4 (h264), jpg и png.'
    case 403:
      return 'У вас нет прав загружать версии в этот проект.'
    default:
      return 'Не удалось загрузить версию.'
  }
}
