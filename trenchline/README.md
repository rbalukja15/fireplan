# Trenchline

A Supremacy 1914 combat calculator that runs everywhere from one codebase:
an installable PWA and a Chrome/Firefox extension. All combat math executes
client-side in a pure engine whose coefficients come from this repo's
black-box probing of [dxter's calculator](https://dxcalc.com/s1914)
(`../dxcalc_probe.py`); a **Send to dxCalc** button opens any battle
pre-filled on dxcalc.com for an authoritative cross-check.

Fan-made tool. Not affiliated with Bytro Labs, dxcalc, or NoxiaZ.

## Use it

**Web / phone:** the Pages deploy lives at
`https://rbalukja15.github.io/dxcalc/`. On a phone, open it and use
"Add to Home Screen" (Android: browser menu → *Install app*; iOS Safari:
Share → *Add to Home Screen*). It works offline after the first visit.

One-time repo setup for the deploy: Settings → Pages → Source =
**GitHub Actions**. The workflow (`.github/workflows/deploy.yml`) tests,
builds, deploys Pages, and uploads the extension zips as a build artifact.

**Extension (unpacked):**

```
npm ci && npm run build:ext
```

- Chrome: `chrome://extensions` → Developer mode → *Load unpacked* → `dist/ext`
- Firefox: `about:debugging#/runtime/this-firefox` → *Load Temporary Add-on* →
  any file inside `dist/ext`

`npm run zip:ext` produces `dist/trenchline-{chrome,firefox}.zip` for store
uploads (the Chrome zip strips `browser_specific_settings`).

## Develop

```
npm ci
npm run dev        # vite dev server (web mode)
npm test           # vitest: engine invariants + payload golden tests
npm run build      # dist/web (base /dxcalc/, + sw.js) and dist/ext (+ manifest)
```

Icons are generated, not drawn: `python3 scripts/gen-icons.py`.

## How the engine relates to reality

Every coefficient in `src/engine/data/coefficients.ts` is tagged
`confirmed` (probe sweep), `observed` (live game / help page / a captured
dxcalc response), or `unknown` (placeholder). The **Engine data** panel in
the app edits any value and persists overrides locally — battle reports
list a warning for every unmeasured value they relied on.

Confirmed by the probe: stack scaling `E(n)` (cap 35 effective units),
damaged-unit multiplier `m(f) = 0.05 + 0.95f`, base attack damage for
infantry/cavalry/artillery/heavy tank, patrol's 4×¼ ticks. Documented
assumptions (simultaneous exchange, HP-proportional damage spread,
return-fire splitting) are listed at the top of `src/engine/simulate.ts` —
each is a thing a future probe sweep could falsify.

`calibration/` holds captured dxcalc responses. The first one already paid
for itself: it proved the export payload works, pinned infantry at
20 HP/unit, and showed dxcalc gives defenders different strength than
attackers (12 defending inf beat 10 inf + 2 art). The engine therefore
carries separate attack/defense tables; defense values are `unknown` until
swept.

## Roadmap

- **Probe the defense table** — fixed duels against defending stacks,
  reading attacker HP loss (the biggest accuracy gap, see `calibration/`).
- **Live army import** — `src/import/armyImport.ts` is the seam: a content
  script on supremacy1914.com can register an `ArmyImportSource` and the UI
  grows an Import menu with no core changes. Needs a live game session to
  reverse-engineer selectors.
- Heroes and buildings (dxcalc models both; coefficients unmeasured).
- Air/naval damage matrices, terrain multipliers (probe experiments exist:
  `damage_air`, `damage_sea`, `terrain`).
