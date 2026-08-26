# Fireplan

A Supremacy 1914 combat calculator that runs everywhere from one codebase:
an installable PWA and a Chrome/Firefox extension. All combat math executes
client-side in a pure engine whose coefficients come from this repo's
black-box probing of [dxter's calculator](https://dxcalc.com/s1914)
(`../dxcalc_probe.py`); a **Send to dxCalc** button opens any battle
pre-filled on dxcalc.com for an authoritative cross-check.

Fan-made tool. Not affiliated with Bytro Labs, dxcalc, or NoxiaZ.

## Use it

**Web / phone:** the Pages deploy lives at
`https://rbalukja15.github.io/fireplan/`. On a phone, open it and use
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

`npm run zip:ext` produces `dist/fireplan-{chrome,firefox}.zip` for store
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

Fireplan has no combat model of its own: `src/engine/research.ts` is a
typed adapter over the research calculator's engine (`../web/engine.js` +
`../web/data.js`), whose test suite replays every constant against
`../results.jsonl` — 168+ recorded dxcalc responses. That is where the
heroes (both hero tables, buffs, bombardment), buildings (fortress damage
reduction, per-building pools), the trench staircase (measured to level
20), cross-class attack/defence matrices, patrol, embarkation and the
E(n)/m(f) closed forms all come from. Every battle report carries the
engine's own coverage verdict (measured / estimated / unknown), its
caveats, and a step-by-step derivation.

`calibration/` holds captured dxcalc responses. The first one already paid
for itself during development: it proved the export payload works
end-to-end, and the engine reproduces it to print precision — the golden
test asserts the attacker wipe (−240.0) and the defender's 175.9 HP loss
straight against that response.

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
