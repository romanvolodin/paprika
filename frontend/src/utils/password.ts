// No 0/O, 1/l/I: a temporary password gets read out and typed by hand.
const ALPHABET = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'

/** A random password for a new account, to be passed on to the person. */
export function generatePassword(length = 14): string {
  const values = new Uint32Array(length)
  crypto.getRandomValues(values)
  return Array.from(values, (value) => ALPHABET[value % ALPHABET.length]).join('')
}
