/* Fireplan content script (isolated world).
 *
 * Runs only on *.supremacy1914.com. It does exactly two things:
 *   1. injects page-probe.js into the PAGE context (content scripts live in
 *      an isolated world and cannot see the game's own JS state);
 *   2. relays request/response messages between the popup and that probe.
 * Nothing here talks to any network; everything stays in the browser. */

;(() => {
  const PROBE_FLAG = '__fireplanProbeInjected'

  function injectProbe() {
    if (document.documentElement.dataset[PROBE_FLAG]) return
    // The extension id is not a secret; stamping it makes "is Fireplan
    // attached to this tab?" checkable from devtools when debugging.
    document.documentElement.dataset[PROBE_FLAG] = chrome.runtime.id || '1'
    const s = document.createElement('script')
    s.src = chrome.runtime.getURL('page-probe.js')
    s.onload = () => s.remove()
    ;(document.head || document.documentElement).appendChild(s)
  }

  injectProbe()

  const pending = new Map()
  let nextId = 1

  window.addEventListener('message', (event) => {
    if (event.source !== window) return
    const msg = event.data
    if (!msg || msg.source !== 'fireplan-page' || typeof msg.id !== 'number') return
    const respond = pending.get(msg.id)
    if (!respond) return
    pending.delete(msg.id)
    respond(msg.result)
  })

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (!msg || typeof msg.action !== 'string') return false
    if (msg.action === 'fireplan:ping') {
      sendResponse({ ok: true, frame: window === top ? 'top' : 'sub', path: location.pathname })
      return false
    }
    injectProbe()
    const id = nextId++
    pending.set(id, sendResponse)
    window.postMessage({ source: 'fireplan-content', id, action: msg.action }, '*')
    // Belt and braces: never leave the popup hanging on a dead frame.
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id)
        sendResponse({ error: 'The game page did not answer (probe timeout).' })
      }
    }, 4000)
    return true // async sendResponse
  })
})()
