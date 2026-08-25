import { DXCALC_URL } from './dxcalcPayload.ts'

/** Opens dxcalc.com in a new tab with the battle pre-filled, via a hidden
 * form POST. Must be called synchronously from a click handler — a
 * user-gesture-synchronous submit to target="_blank" is the one shape every
 * popup blocker allows. */
export function submitToDxcalc(payload: Record<string, string>): void {
  const form = document.createElement('form')
  form.method = 'post'
  form.action = DXCALC_URL
  form.target = '_blank'
  form.style.display = 'none'
  for (const [name, value] of Object.entries(payload)) {
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = name
    input.value = value
    form.appendChild(input)
  }
  document.body.appendChild(form)
  form.submit()
  form.remove()
}
