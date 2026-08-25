import type { Side } from '../engine/types.ts'
import { useAppDispatch, useAppState } from '../state/context.ts'
import { ArmyPanel } from './ArmyPanel.tsx'

const SIDE_LABEL: Record<Side, string> = { A: 'Attacking', B: 'Defending' }

/** One DOM, two layouts: tabs on a phone, both panels side by side on a
 * desk-width screen (the tab strip hides itself via CSS). */
export function ArmyTabs() {
  const { activeSide } = useAppState()
  const dispatch = useAppDispatch()
  return (
    <div className="board">
      <div className="tabstrip" role="tablist">
        {(['A', 'B'] as const).map((side) => (
          <button
            key={side}
            role="tab"
            aria-selected={activeSide === side}
            className={activeSide === side ? 'tab active' : 'tab'}
            onClick={() => dispatch({ type: 'setActiveSide', side })}
          >
            {SIDE_LABEL[side]}
          </button>
        ))}
      </div>
      <div className="board-grid">
        {(['A', 'B'] as const).map((side) => (
          <section
            key={side}
            className={
              'board-col' + (activeSide === side ? ' active' : ' inactive')
            }
          >
            <ArmyPanel side={side} label={SIDE_LABEL[side]} />
          </section>
        ))}
      </div>
    </div>
  )
}
