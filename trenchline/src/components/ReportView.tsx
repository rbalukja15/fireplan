import type { BattleResult, SideResult } from '../engine/research.ts'
import { VARIANCE_BAND } from '../engine/research.ts'

const fmt = (n: number | null | undefined): string =>
  n === null || n === undefined || !Number.isFinite(n)
    ? '—'
    : n.toLocaleString('en-US', { maximumFractionDigits: 1 })

function headline(r: BattleResult): string {
  const rounds = r.rounds?.fought
  const at = rounds !== undefined ? ` — round ${fmt(rounds)}` : ''
  if (r.attacker.wiped && r.defender.wiped) return `Mutual annihilation${at}`
  if (r.defender.wiped) return `Attacker prevails${at}`
  if (r.attacker.wiped) return `Defender prevails${at}`
  if (r.rounds?.decided === false) return `No decision${at}`
  return `Exchange resolved${at}`
}

function SideColumn({
  title,
  r,
  showBldgDamage,
}: {
  title: string
  r: SideResult
  showBldgDamage: boolean
}) {
  return (
    <div className="dispatch-side">
      <h4>{title}</h4>
      <table>
        <tbody>
          <tr>
            <td className="u-name">HP pool</td>
            <td className="u-hp">
              {fmt(r.pool)} → <b>{r.pool !== null && r.hpLost !== null ? fmt(r.pool - r.hpLost) : '—'}</b>
            </td>
          </tr>
          <tr>
            <td className="u-name">HP lost</td>
            <td className={'u-hp' + (r.wiped ? ' u-died' : '')}>
              {fmt(r.hpLost)}
              {r.pctLost !== null && <> ({fmt(r.pctLost)}%)</>}
              {r.wiped && ' — wiped'}
            </td>
          </tr>
          <tr>
            <td className="u-name">Units died</td>
            <td className={'u-hp' + ((r.deaths ?? 0) > 0 ? ' u-died' : '')}>{fmt(r.deaths)}</td>
          </tr>
          <tr>
            <td className="u-name">Units left</td>
            <td className="u-hp">{fmt(r.unitsLeft)}</td>
          </tr>
          <tr>
            <td className="u-name">Damage dealt</td>
            <td className="u-hp">{fmt(r.damageDealt)}</td>
          </tr>
          {showBldgDamage && (r.damageToBuildings ?? 0) > 0 && (
            <tr>
              <td className="u-name">Dealt to enemy buildings</td>
              <td className="u-hp">{fmt(r.damageToBuildings)}</td>
            </tr>
          )}
        </tbody>
      </table>
      {r.buildings.length > 0 && (
        <table className="bldg-table">
          <tbody>
            {r.buildings.map((b, i) => (
              <tr key={i}>
                <td className="u-name">
                  {String(b.label ?? b.code)}
                  {b.level !== undefined && <span className="u-class">lvl {String(b.level)}</span>}
                </td>
                <td className={'u-hp' + (b.destroyed ? ' u-died' : '')}>
                  {fmt(b.hpFull as number)} → <b>{fmt(b.hp as number)}</b>
                  {Boolean(b.destroyed) && ' — destroyed'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export function ReportView({ result }: { result: BattleResult }) {
  const cov = result.coverage
  return (
    <section className="dispatch">
      <header className="dispatch-head">
        <span className="stamp">Battle report</span>
        <h3>{headline(result)}</h3>
      </header>

      <p className={`coverage coverage-${cov.level}`}>
        <b>{cov.level}</b> — {cov.reason}
      </p>

      <div className="dispatch-grid">
        <SideColumn title="Attacking" r={result.attacker} showBldgDamage={result.defender.buildings.length > 0} />
        <SideColumn title="Defending" r={result.defender} showBldgDamage={result.attacker.buildings.length > 0} />
      </div>

      {cov.caveats.length > 0 && (
        <ul className="dispatch-warnings">
          {cov.caveats.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      )}

      {result.derivation.length > 0 && (
        <details className="derivation">
          <summary>How this was computed ({result.derivation.length} steps)</summary>
          <ol>
            {result.derivation.map((d, i) => (
              <li key={i}>
                <b>{d.label}.</b> {d.formula}
                {d.value !== null && <span className="mono"> = {fmt(d.value)}</span>}
              </li>
            ))}
          </ol>
        </details>
      )}

      <p className="fineprint">
        The live server rolls ×{VARIANCE_BAND.lo.toFixed(2)}–×{VARIANCE_BAND.hi.toFixed(2)} damage
        variance ({VARIANCE_BAND.rolls}); figures here are the expected values.
      </p>
    </section>
  )
}
