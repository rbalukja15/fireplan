# supremacy.noxiaz.dk — evaluation vs dxcalc

*Investigated 2026-08-25. Question: what is this tool, and is it better than
dxcalc.com/s1914?*

## What it is

**Supremacy Utilities** — a Chrome & Firefox browser extension by NoxiaZ, an
unofficial companion for Supremacy 1914 (not affiliated with Bytro Labs).
supremacy.noxiaz.dk is only its marketing site plus a Discord-gated admin
console; the tool itself lives in the extension:

- Chrome: `chromewebstore.google.com/detail/supremacy-utilities/phkhjfplpeiadkhdalmejbeddkoflgjo`
- Firefox: `addons.mozilla.org/en-US/firefox/addon/supremacy-utilities/`

Nineteen in-game HUD dialogs: Combat Calculator suite (attack sim,
unit-vs-unit damage, engagement range), Battle Report, Empire/Coalition
overview, Diplomacy panel, AI Relation Manager, Distance & Time, Production
Overview, live alliance drawing overlay (SignalR), a community player
reputation system, and a mobile-web rebuild of the combat calculator.

The site is an Angular SPA that renders nothing without JS — WebFetch sees
only the `<title>`. Everything below came from pulling its lazy chunks
directly and reading the string literals out of the minified components
(`chunk-CYZBKOHY` home, `chunk-UX4ON3OS` features, `chunk-JL4RPM6O` terms,
`chunk-OQIRUDNL` privacy).

## The load-bearing findings

1. **The combat math runs client-side.** The privacy policy is explicit: the
   content script reads armies/provinces/diplomacy off the game's own pages
   and "that reading happens locally in your browser"; only drawings,
   reputation ratings, and menu-pin layout touch their backend. So the
   extension bundle *contains the combat engine* — coefficients readable from
   source, no black-box probing needed.

2. **It is built on dxcalc's data model — literally.** The calculator UI
   mirrors dxcalc's form schema field-for-field: `Pos / Target: Stack 1 (B) /
   land / Trench: 0`, target "Defend" (dxcalc's `target=0`). The mobile
   screenshots show `Hero: georg (Lvl 13, HP 40)` and `Hero: marco (Lvl 10,
   HP 60)` — **`georg` and `marco` are dxcalc's internal `hero.abb` option
   values** (Georg Bruchmüller, Fiero "Marco" Martello), not in-game display
   names. And every calculator screen carries a **"Go to dxCalc"** button
   next to "Validate Combat": it exports the assembled battle into dxcalc.
   NoxiaZ treats dxter's engine as the authority to cross-check against.

3. **What it adds is data entry, not math.** "Add Army" imports a live stack
   with exact fractional HP (`310× Infantry (4598.9 HP)`), hero, level,
   trench, position — the single most error-prone part of using dxcalc by
   hand. Battle report shows per-unit died/damaged, HP before→after,
   resources/cash/hours lost per side, "Army A Won in round 9".

4. **dxcalc remains deeper and is actively maintained.** Its `bytro.js`
   carries cache-buster `1784577104` = **2026-07-20**. It models 22 heroes ×
   20 levels (with gas/bombardment/homeland variants), 8 building types × 5
   levels with progressive building damage, firestorms (up to 15), up to 100
   stacks, fractional rounds (0.25/0.5/0.75), variance simulation, and
   rebuild-cost output. The extension's calculator surface shows none of
   the building/firestorm/multi-stack depth.

## Verdict

"Which is better" splits by purpose:

- **As a combat engine / source of truth: dxcalc.** Ten years old (© 2015),
  updated a month ago, deterministic, and deep enough that our probe could
  recover exact closed forms (`E(n)`, `m(f) = 0.05 + 0.95f`). The strongest
  evidence is NoxiaZ's own UI: it speaks dxcalc's field codes and ships a
  "Go to dxCalc" button. The satellite does not outrank the thing it orbits.

- **As a day-to-day player tool: Supremacy Utilities.** One-click import of
  real armies (exact HP, hero, trench) removes the transcription errors that
  dominate practical dxcalc use, works on mobile, and bundles 18 other
  tools. Its local sim is good for quick in-game answers; for a battle that
  matters you'd still export to dxcalc — which is exactly the workflow its
  own buttons encode.

- **For this repo's goal (recovering the combat coefficients): the extension
  is the better target.** Its engine ships as inspectable client-side
  JavaScript, versus dxcalc's server-side black box at ~1.5 s/request.
  Caveat: both extension stores are egress-blocked from this sandbox
  (`addons.mozilla.org`, `chromewebstore.google.com` → 403), so the package
  couldn't be pulled here. From an unrestricted machine:
  `addons.mozilla.org/firefox/downloads/latest/supremacy-utilities/latest.xpi`
  is a plain zip. Two things to mine from it:
    - the full damage/coefficient tables of its local engine (then diff
      against `results.jsonl` — where they agree, both are probably right;
      where they disagree, one of them is wrong in a checkable way);
    - the "Go to dxCalc" export code, which necessarily contains the exact
      dxcalc form-field mapping — including the `bldg` and `hero` row
      wiring that the fortress experiment (`exp_fortress`) is still
      guessing at.

## Loose ends

- `supremacy.noxiaz.dk/api/*` returns the SPA shell to anonymous GETs; the
  backend (Discord-auth admin, SignalR drawing hub, reputation store) is not
  reachable for inspection, and doesn't need to be — no combat math there.
- Extension version couldn't be confirmed (`/api/version` unreachable,
  stores blocked); the site's homepage fetches and displays it at runtime.
- Not compared here: supremacy1914simulator.com (third-party web simulator,
  surfaced in search); unknown pedigree, likely another satellite.
