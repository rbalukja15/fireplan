import type { SideKey } from '../engine/research.ts'
import { useAppDispatch, useAppState } from '../state/context.ts'
import { SidePanel } from './SidePanel.tsx'

const SIDES: Array<{ key: SideKey; label: string }> = [
  { key: 'attacker', label: 'Attacking army' },
  { key: 'defender', label: 'Defending army' },
]

/** One DOM, two layouts: tabs on a phone, both panels side by side on a
 * desk-width screen (the tab strip hides itself via CSS). */
export function ArmyTabs() {
  const { activeSide } = useAppState()
  const dispatch = useAppDispatch()
  return (
    <div className="board">
      <div className="tabstrip" role="tablist">
        {SIDES.map(({ key, label }) => (
          <button
            key={key}
            role="tab"
            aria-selected={activeSide === key}
            className={activeSide === key ? 'tab active' : 'tab'}
            onClick={() => dispatch({ type: 'setActiveSide', side: key })}
          >
            {label.split(' ')[0]}
          </button>
        ))}
      </div>
      <div className="board-grid">
        {SIDES.map(({ key, label }) => (
          <section key={key} className={'board-col' + (activeSide === key ? ' active' : ' inactive')}>
            <SidePanel side={key} label={label} />
          </section>
        ))}
      </div>
    </div>
  )
}
