import type { Row, UnitCode } from '../engine/research.ts'
import { TRENCH_MAX_LEVEL, UNITS } from '../engine/research.ts'

/* Army import from a live game tab (extension only).
 *
 * The popup talks to the content script on *.supremacy1914.com, which relays
 * to a probe injected into the game page's own JS context. Everything stays
 * in the browser; nothing is sent anywhere.
 *
 * The probe's extractor is an adapter seam: until a real game session's
 * structure has been mapped (via the discovery report below), read-armies
 * reports 'unmapped' instead of guessing at numbers. */

const GAME_URL_PATTERN = '*://*.supremacy1914.com/*'

// Minimal typings for the WebExtension APIs this file touches — enough to
// stay honest without pulling in @types/chrome.
interface ExtTab {
  id?: number
  title?: string
}
interface ChromeLike {
  tabs?: {
    query: (q: { url: string }) => Promise<ExtTab[]>
    sendMessage: (tabId: number, msg: unknown) => Promise<unknown>
  }
}

function ext(): ChromeLike['tabs'] | null {
  const c = (globalThis as { chrome?: ChromeLike }).chrome
  return c?.tabs && typeof c.tabs.query === 'function' ? c.tabs : null
}

/** True when running inside the extension with tab access. */
export function importCapable(): boolean {
  return ext() !== null
}

export type ImportStatus =
  | { available: true; tabId: number; tabTitle: string }
  | { available: false; reason: string }

export async function gameImportStatus(): Promise<ImportStatus> {
  const tabs = ext()
  if (!tabs) return { available: false, reason: 'Army import runs from the browser extension.' }
  try {
    const found = await tabs.query({ url: GAME_URL_PATTERN })
    const tab = found.find((t) => typeof t.id === 'number')
    if (!tab || tab.id === undefined) {
      return { available: false, reason: 'No open supremacy1914.com tab found — open the game first.' }
    }
    return { available: true, tabId: tab.id, tabTitle: tab.title ?? 'Supremacy 1914' }
  } catch (e) {
    return { available: false, reason: e instanceof Error ? e.message : String(e) }
  }
}

async function send(tabId: number, action: string): Promise<Record<string, unknown>> {
  const tabs = ext()
  if (!tabs) return { error: 'extension APIs unavailable' }
  try {
    const res = await tabs.sendMessage(tabId, { action })
    return (res ?? { error: 'The game tab did not answer — reload it and try again.' }) as Record<
      string,
      unknown
    >
  } catch (e) {
    return {
      error:
        'Could not reach the game tab (was it open before the extension was installed? Reload it): ' +
        (e instanceof Error ? e.message : String(e)),
    }
  }
}

export interface ImportedArmy {
  name: string
  rows: Row[]
  trench: number
  dropped: string[]
}

export interface ReadArmiesResult {
  armies?: ImportedArmy[]
  error?: string
  unmapped?: boolean
}

interface RawRow {
  unit?: unknown
  count?: unknown
  hpPct?: unknown
}
interface RawArmy {
  name?: unknown
  trench?: unknown
  rows?: RawRow[]
}

/** Validate whatever the page adapter produced into engine-safe rows. */
function sanitizeArmy(raw: RawArmy, index: number): ImportedArmy {
  const dropped: string[] = []
  const rows: Row[] = []
  for (const r of raw.rows ?? []) {
    const unit = String(r.unit ?? '')
    const count = Math.round(Number(r.count))
    if (!(unit in UNITS)) {
      if (unit) dropped.push(`${unit} ×${Number.isFinite(count) ? count : '?'}`)
      continue
    }
    if (!Number.isFinite(count) || count <= 0) continue
    const hp = Number(r.hpPct)
    rows.push({
      unit: unit as UnitCode,
      count: Math.min(5000, count),
      hpPct: Number.isFinite(hp) ? Math.min(100, Math.max(0.1, Math.round(hp * 100) / 100)) : 100,
    })
  }
  const trench = Math.round(Number(raw.trench))
  return {
    name: typeof raw.name === 'string' && raw.name ? raw.name : `Army ${index + 1}`,
    rows,
    trench: Number.isFinite(trench) ? Math.min(TRENCH_MAX_LEVEL, Math.max(0, trench)) : 0,
    dropped,
  }
}

export async function readArmies(tabId: number): Promise<ReadArmiesResult> {
  const res = await send(tabId, 'fireplan:read-armies')
  if (typeof res.error === 'string') {
    return { error: res.error, unmapped: Boolean(res.unmapped) }
  }
  if (!Array.isArray(res.armies)) return { error: 'The game tab returned no armies.' }
  const armies = (res.armies as RawArmy[]).map(sanitizeArmy).filter((a) => a.rows.length > 0)
  if (!armies.length) return { error: 'No armies with recognisable units were found.' }
  return { armies }
}

/** Bounded structural report of the game page, for mapping the real state. */
export async function runDiscovery(tabId: number): Promise<string> {
  const res = await send(tabId, 'fireplan:discover')
  return JSON.stringify(res, null, 1)
}
