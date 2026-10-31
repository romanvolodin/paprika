/** The address a person opens to accept an invitation. */
export function invitationLink(token: string): string {
  return `${window.location.origin}/invite/${token}`
}

/** Put text on the clipboard; false if the browser would not let us. */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}
