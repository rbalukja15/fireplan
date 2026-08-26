import type { SideConfig, SideKey } from '../engine/research.ts'

/* The seam for pulling armies out of a live game instead of typing them.
 *
 * v1 ships no sources: reading stacks off supremacy1914.com needs a content
 * script whose selectors can only be reverse-engineered against a live game
 * session. When that lands, it registers here (via extension messaging) and
 * the UI grows an Import menu without any core changes. */

export interface ArmyImportSource {
  id: string
  label: string
  available(): boolean
  importSide(side: SideKey): Promise<SideConfig>
}

export const importSources: ArmyImportSource[] = []
