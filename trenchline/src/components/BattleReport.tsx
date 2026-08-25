import type { BattleReport, Side, SideReport } from '../engine/types.ts'
import type { MonteCarloResult } from '../engine/montecarlo.ts'
import { UNIT_LABELS } from '../engine/data/units.ts'

const fmt = (n: number): string =>
  n.toLocaleString('en-US', { maximumFractionDigits: 1 })

const pct = (n: number): string => `${Math.round(n * 100)}%`

function winnerLine(report: BattleReport): string {
  switch (report.winner) {
    case 'A':
      return `Attacking army prevails — round ${fmt(report.rounds)}`
    case 'B':
      return `Defending army prevails — round ${fmt(report.rounds)}`
    case 'draw':
      return `Mutual annihilation — round ${fmt(report.rounds)}`
    case 'stalemate':
      return `No decision after ${fmt(report.rounds)} rounds`
  }
}

function SideColumn({ side, report }: { side: Side; report: SideReport }) {
  return (
    <div className="dispatch-side">
      <h4>{side === 'A' ? 'Attacking' : 'Defending'}</h4>
      {report.stacks.map((stack) => (
        <div className="dispatch-stack" key={stack.id}>
          {report.stacks.length > 1 && <h5>Stack</h5>}
          <table>
            <tbody>
              {stack.units.map((u) => (
                <tr key={u.unit}>
                  <td className="u-name">
                    {UNIT_LABELS[u.unit]} ×{u.countBefore}
                  </td>
                  <td className={u.died > 0 ? 'u-died' : 'u-ok'}>
                    {u.died > 0 ? `${u.died} died` : u.hpAfter < u.hpBefore ? 'damaged' : 'unscathed'}
                  </td>
                  <td className="u-hp">
                    {fmt(u.hpBefore)} → <b>{fmt(u.hpAfter)}</b>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <p className="dispatch-total">
        HP {fmt(report.hpBefore)} → <b>{fmt(report.hpAfter)}</b>
        <span className="loss"> (−{fmt(report.hpLost)})</span>
      </p>
    </div>
  )
}

export function BattleReportView({ report }: { report: BattleReport }) {
  return (
    <section className="dispatch">
      <header className="dispatch-head">
        <span className="stamp">Battle report</span>
        <h3>{winnerLine(report)}</h3>
      </header>
      <div className="dispatch-grid">
        <SideColumn side="A" report={report.sides.A} />
        <SideColumn side="B" report={report.sides.B} />
      </div>
      {report.warnings.length > 0 && (
        <ul className="dispatch-warnings">
          {report.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function VarianceReportView({ mc }: { mc: MonteCarloResult }) {
  const { winProbability: p } = mc
  return (
    <section className="dispatch">
      <header className="dispatch-head">
        <span className="stamp">Variance study · {mc.runs} runs</span>
        <h3>
          Attacker wins {pct(p.A)} · Defender wins {pct(p.B)}
          {p.draw > 0 && <> · draw {pct(p.draw)}</>}
          {p.stalemate > 0 && <> · no decision {pct(p.stalemate)}</>}
        </h3>
      </header>
      <div className="dispatch-grid">
        <div className="dispatch-side">
          <h4>Rounds</h4>
          <p className="mono">
            {fmt(mc.rounds.min)} – {fmt(mc.rounds.max)} (mean {fmt(mc.rounds.mean)})
          </p>
          <h4>Attacker HP lost</h4>
          <p className="mono">
            {fmt(mc.hpLost.A.min)} – {fmt(mc.hpLost.A.max)} (mean {fmt(mc.hpLost.A.mean)})
          </p>
          <h4>Defender HP lost</h4>
          <p className="mono">
            {fmt(mc.hpLost.B.min)} – {fmt(mc.hpLost.B.max)} (mean {fmt(mc.hpLost.B.mean)})
          </p>
          <p className="fineprint">
            The ±10% roll&rsquo;s true distribution has never been sampled by the probe —
            read the spread as indicative, not exact.
          </p>
        </div>
        <div className="dispatch-side">
          <h4>Median run</h4>
          <p className="fineprint">{winnerLine(mc.sample)}</p>
          <p className="mono">
            A −{fmt(mc.sample.sides.A.hpLost)} HP · B −{fmt(mc.sample.sides.B.hpLost)} HP
          </p>
        </div>
      </div>
    </section>
  )
}
