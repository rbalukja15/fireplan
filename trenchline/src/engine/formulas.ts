/* The two closed forms the probe recovered exactly (see dxcalc_probe.py). */

/** Effective units contributed by a stack of n:
 *   E(n) = n                                   for n ≤ 20
 *   E(n) = 20 + k(60−k)/60, k = min(n,50) − 20 for n > 20
 * Saturates at 35; stacking past 50 adds nothing. */
export function effectiveUnits(n: number): number {
  if (n <= 0) return 0
  if (n <= 20) return n
  const k = Math.min(n, 50) - 20
  return 20 + (k * (60 - k)) / 60
}

/** Damage multiplier of a unit at HP fraction f ∈ [0,1]:
 *   m(f) = 0.05 + 0.95·f   (exact fit, not approximate) */
export function hpMultiplier(f: number): number {
  const clamped = Math.min(1, Math.max(0, f))
  return 0.05 + 0.95 * clamped
}

/** Deterministic mulberry32 PRNG for reproducible variance runs. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
