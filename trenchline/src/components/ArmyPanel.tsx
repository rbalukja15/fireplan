import type { Side } from '../engine/types.ts'
import { useAppDispatch, useAppState } from '../state/context.ts'
import { StackCard } from './StackCard.tsx'

export function ArmyPanel({ side, label }: { side: Side; label: string }) {
  const state = useAppState()
  const dispatch = useAppDispatch()
  const stacks = state.armies[side].stacks
  return (
    <div className="army">
      <div className="army-head">
        <h2>
          <span className="army-letter">{side}</span> {label} army
        </h2>
        <button className="btn small" onClick={() => dispatch({ type: 'addStack', side })}>
          + stack
        </button>
      </div>
      {stacks.length === 0 && <p className="empty">No stacks — add one to field an army.</p>}
      {stacks.map((stack, i) => (
        <StackCard key={stack.id} side={side} index={i} stack={stack} />
      ))}
    </div>
  )
}
