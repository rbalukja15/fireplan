/* Fireplan page probe. Runs in the GAME PAGE's own JS context (injected by
 * content.js) so it can see the state the game keeps in globals.
 *
 * Read-only by design: it never calls into game code with arguments, never
 * mutates anything, and never touches the network. Two actions:
 *
 *   fireplan:discover     — a bounded, redacted structural summary of the
 *                           page's non-standard globals, so the army
 *                           extractor can be written against the real game
 *                           without guessing. Strings are truncated, depth
 *                           and size are capped, and the URL query (which
 *                           can carry session tokens) is never included.
 *
 *   fireplan:read-armies  — returns armies in Fireplan's row format. Until
 *                           the live game's state shape has been mapped via
 *                           a discovery report, only the documented adapter
 *                           hook (window.__fireplanGame.getArmies()) is
 *                           consulted; without it this reports 'unmapped'
 *                           rather than guessing at numbers. */

;(() => {
  const MAX_STRING = 80
  const MAX_KEYS = 40
  const MAX_REPORT_BYTES = 90_000
  const INTERESTING = /game|army|armies|unit|province|player|nation|state|hup|bytro|ultshared|s1914|supremacy/i

  function baselineGlobals() {
    // Diff against a pristine window so only the page's own globals remain.
    try {
      const iframe = document.createElement('iframe')
      iframe.style.display = 'none'
      document.documentElement.appendChild(iframe)
      const names = new Set(Object.getOwnPropertyNames(iframe.contentWindow))
      iframe.remove()
      return names
    } catch {
      return new Set()
    }
  }

  function describe(value, depth) {
    const t = typeof value
    if (value === null) return null
    if (t === 'string') return value.length > MAX_STRING ? value.slice(0, MAX_STRING) + '…' : value
    if (t === 'number' || t === 'boolean') return value
    if (t === 'function') return `ƒ(${value.length})`
    if (t !== 'object') return t
    if (depth <= 0) return Array.isArray(value) ? `array(${value.length})` : 'object'
    try {
      if (Array.isArray(value)) {
        return { '[array]': value.length, sample: value.length ? describe(value[0], depth - 1) : undefined }
      }
      const out = {}
      const keys = Object.keys(value)
      for (const k of keys.slice(0, MAX_KEYS)) {
        try {
          out[k] = describe(value[k], depth - 1)
        } catch {
          out[k] = '«threw»'
        }
      }
      if (keys.length > MAX_KEYS) out['…'] = `${keys.length - MAX_KEYS} more keys`
      return out
    } catch {
      return '«unreadable»'
    }
  }

  function discover() {
    const baseline = baselineGlobals()
    const report = {
      fireplanProbe: 1,
      page: { host: location.host, path: location.pathname, frame: window === top ? 'top' : 'sub' },
      globals: {},
    }
    let names = []
    try {
      names = Object.getOwnPropertyNames(window).filter((n) => !baseline.has(n))
    } catch {
      /* keep going with nothing */
    }
    const ranked = names.sort((a, b) => Number(INTERESTING.test(b)) - Number(INTERESTING.test(a)))
    for (const name of ranked) {
      const depth = INTERESTING.test(name) ? 4 : 1
      try {
        report.globals[name] = describe(window[name], depth)
      } catch {
        report.globals[name] = '«threw»'
      }
      if (JSON.stringify(report).length > MAX_REPORT_BYTES) {
        report.truncated = true
        break
      }
    }
    return report
  }

  function readArmies() {
    // The adapter seam: once a discovery report has mapped the live game,
    // the extractor lands here (and this hook doubles as the test seam).
    try {
      const hook = window.__fireplanGame
      if (hook && typeof hook.getArmies === 'function') {
        const armies = hook.getArmies()
        if (Array.isArray(armies)) return { armies }
      }
    } catch (err) {
      return { error: 'The page adapter threw: ' + (err && err.message) }
    }
    return {
      error:
        'This game page has not been mapped yet — run “Copy game structure report” ' +
        'and share it so the extractor can be written against the real state.',
      unmapped: true,
    }
  }

  window.addEventListener('message', (event) => {
    if (event.source !== window) return
    const msg = event.data
    if (!msg || msg.source !== 'fireplan-content' || typeof msg.id !== 'number') return
    let result
    try {
      if (msg.action === 'fireplan:discover') result = discover()
      else if (msg.action === 'fireplan:read-armies') result = readArmies()
      else result = { error: 'unknown action' }
    } catch (err) {
      result = { error: 'probe failed: ' + (err && err.message) }
    }
    window.postMessage({ source: 'fireplan-page', id: msg.id, result }, '*')
  })
})()
