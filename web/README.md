# Battle Calculator — a local implementation of the recovered S1914 model

A single-page battle calculator for *Supremacy 1914*. It runs entirely in the
browser, has no build step, no dependencies and no backend, and it **never
makes a network request to dxcalc.com** — or to anywhere else.

That last point is the reason this directory exists in this form. dxcalc.com is
one person's ad-supported fan site with no API. Deploying a proxy in front of it
would put every one of this app's users onto dxter's bandwidth without asking.
So instead of forwarding requests, the app carries a clean-room implementation
of the mechanics that were measured against that site, and answers locally.
`engine.js` and `data.js` contain no `fetch`, no `XMLHttpRequest`, no
`WebSocket`, no `new URL`, no dynamic import of a remote module — and the test
suite asserts all of that, so it stays true.

---

## What it is

| | |
|---|---|
| **Files** | `index.html`, `styles.css`, `app.js`, `engine.js`, `data.js` |
| **Build step** | none — the files are shipped as written |
| **Dependencies** | none |
| **Backend** | none |
| **Network requests at runtime** | none |
| **State** | in the URL fragment, so a link reproduces a battle exactly |

- `data.js` — measured constants only. Every constant carries a provenance key
  and one of four confidence tags: `measured`, `derived`, `assumed`,
  `unmeasured`. A constant without one is a defect.
- `engine.js` — pure functions implementing the model. Two invariants:
  `simulate()` never throws for any roster combination, and a number the record
  cannot support is flagged or withheld, never emitted as though it were
  measured.
- `app.js` — the UI. It renders the engine's `derivation[]` array, so every
  number on screen can be traced back to the law and the reading it came from.
- `test/engine.test.mjs` — 580 checks. See [Verification](#verification).

---

## What it knows, and how well

The model was recovered black-box, by submitting battles to dxcalc.com and
reading the results — 168 live requests, all recorded in `../results.jsonl`.
Full detail is in `../HANDOVER.md`; this is the short version.

**Measured.**

- Stack size factor `E(n)`: `n` for `n <= 20`, else `20 + k(60-k)/60` with
  `k = min(n,50) - 20`. Saturates at 35 effective units.
- HP scaling of output, `m(f) = 0.05 + 0.95f`, confirmed with zero deviation at
  ten points. The pool itself scales linearly with no floor.
- Deaths = `floor(HP_lost / unit_max_hp)`.
- A stack wiped inside the round still deals its full damage.
- Max HP for 16 of the 17 units — each as a bracket that contains exactly one
  integer, which is what the app displays.
- **Same-class** attack and defence for those 16 units. The diagonal only.
- Air attacking ground: Fighter 5.0, Bomber 30.0, Zeppelin 5.0, flat across all
  ten ground targets once return fire is corrected for.
- Ground defending against air, for all ten ground units, each confirmed by
  three independent attackers.
- Return fire, **air-to-ground only**: `dealt = base · E(n) · (1 - own_frac_lost)`.
  Demonstrably absent in land-vs-land.
- Fortress: `DR = 0.15 · (fortressHP/50 + 1)`, fortress HP 50 per level. The
  other seven building types confer no damage reduction at all — a positive
  reading, not a silence.
- Trenches, at the nine sampled levels: they enlarge the defender's pool from
  level 4 (×1.35 at 20) and raise defender output from level 1 (×1.75 at 20).
  The pool bonus applies while attacking; the output bonus does not.

**Not measured — and the app says so, on screen, wherever it matters.**

- **Land off-diagonal** — infantry attacking a heavy tank, and 89 other
  pairings. This is the largest gap in the model. Attack is *known* to be per
  target class (the Bomber is 3.0 against air and 30.0 against ground), so the
  same-class table cannot be assumed to generalise. The app will still compute
  such a matchup, but it labels the result `estimated` and names the
  substitution it made.
- Naval off-diagonal; air off-diagonal; any sea-vs-land or sea-vs-air pairing.
- A ground stack *attacking* air, and an air stack *defending* against ground.
  Only ground-defending-against-air was measured; the roles are not
  interchangeable.
- The Balloon: every quantity. Sending one in air terrain aborts the request
  server-side, so the hole is permanent through that route.
- Battles longer than one round. **Every** measurement used `maxRounds = 1`.
- Terrain modifiers beyond the air strike/patrol pair, `debark` semantics (never
  submitted once), and `simulateVariance`.
- Trench levels 6-9, 11-14 and 16-19 — 12 of 21. Neither trench curve is
  smooth, so interpolating them is demonstrably risky, and the app flags an
  unsampled level rather than smoothing across it.
- Heroes, and position/range effects.

`data.js` exports `NOT_MEASURED`, a list of 24 such gaps, each with what is
missing, why, and what experiment would close it. The app's "What this model
does not know" section is rendered from that list, so it cannot drift away from
the code.

A result is tagged `measured`, `estimated` or `unknown`. `unknown` withholds
the number instead of inventing one. That is the design: **a confident wrong
answer is the failure mode this project keeps hitting** — six separate defects
in the research rig produced plausible wrong numbers, and five of them reported
something false with confidence rather than reporting nothing.

---

## Run it locally

The app uses ES modules, so `file://` will not work — the browser blocks module
loads from the filesystem. (The app detects this and says so rather than
failing blankly.) Serve the directory over HTTP with any one-liner:

```bash
python3 -m http.server 8000 --directory web
```

then open <http://localhost:8000>. Equivalents, if you prefer:

```bash
npx serve web            # Node
php -S localhost:8000 -t web
ruby -run -e httpd web -p 8000
```

Nothing needs installing and nothing needs building. Edit a file, reload.

## Verification

```bash
node web/test/engine.test.mjs
```

580 checks, no network needed. The suite replays `../results.jsonl` row by row
and compares the engine's prediction against what dxcalc.com actually printed;
**no expected value in it is a constant the engine itself carries** — every one
came off the wire. Tolerances follow the source page's print precision: HP lost
to ±0.005 where the summary table gave two decimals and ±0.05 where only a
one-decimal span was recorded, death counts exact, and a stack pool asserted
inside the bracket implied by a three-significant-figure percentage rather than
as a point value.

It also asserts the honesty properties: that no unmeasured matchup is ever
labelled `measured`, that an `unknown` matchup withholds its numbers, that
`derivation[]` is populated for every result, and that no network call appears
anywhere in `engine.js` or `data.js`.

All eight experiments in the record are replayed, `patrol` included. Patrol is
modelled with an important qualification the app states everywhere it matters:
its **attrition coefficient is a band, not a number** — nine cells give
0.360–0.427 and the scatter does not track the loss fraction, so the delivery is
probably discrete rather than a smooth fraction. Every patrol result is
therefore labelled *estimated*, and the derivation prints the range the band
implies alongside the central figure. The nine measured cells are replayed to
within 0.72%.

Patrol's `maxRounds` behaviour, by contrast, **is** measured and is implemented
as such: patrol damage is proportional to the round count, while a direct air
strike ignores `maxRounds` entirely (byte-identical damage at 0.25, 0.5, 0.75
and 1).

The repository's eight Python suites (`python3 test_*.py` from the repo root)
guard the research rig rather than the app, but they are why its constants can
be trusted: each proves that the experiment behind a constant could actually
have distinguished the hypotheses it ruled between. CI runs all nine suites and
will not deploy if any fails.

---

## Deploy to GitHub Pages

`.github/workflows/pages.yml` does this automatically on push. It runs the
engine suite and all eight Python suites first, and **does not deploy if any of
them fail**.

**One step must be done by hand, once — it cannot be automated:**

> **Settings → Pages → Build and deployment → Source: `GitHub Actions`**

(not "Deploy from a branch"). Until that is set, the workflow's `deploy` job
fails with a 404 from the Pages API, because no Pages site exists to deploy to.
Nothing in the Actions API can flip that switch for you.

After that, push to `main` or to the working branch and the site appears at
`https://<owner>.github.io/<repo>/`. The run's deploy job prints the exact URL.
Pull requests get the test gate but are not deployed.

All asset paths in `index.html` are relative (`./styles.css`, `./app.js`), so
the app works unchanged under a project-page subpath — no `base` tag and no
build-time rewriting.

## Deploy anywhere else

`web/` is a plain directory of static files. Any static host will do; there is
nothing to configure, no build command, no output directory transformation, and
no environment variables.

| Host | What to enter |
|---|---|
| **Netlify** | Publish directory `web`, build command *(leave empty)*. Or drag the `web` folder onto the deploy page. |
| **Vercel** | Framework preset "Other", root directory `web`, no build command. |
| **Cloudflare Pages** | Build output directory `web`, build command *(leave empty)*. |
| **S3 / R2 / GCS** | Upload the contents of `web/`, set `index.html` as the index document. |
| **nginx / Apache / Caddy** | Point the document root at `web/`. |
| **A USB stick** | Serve it over HTTP from anywhere. It has no origin requirements. |

Two things to preserve wherever it goes:

- **Serve `.js` as `application/javascript`.** The app is ES modules; a host
  that serves them as `text/plain` will refuse to load them.
- **Do not add analytics, a CDN font, or an embed that phones home.** The claim
  on the page is that it makes no network requests. That claim is checked in
  CI for `engine.js` and `data.js`, but nothing can check it for a script tag
  someone adds to `index.html` later. It is worth keeping true.

`web/test/` ships with the deployment. It is a few KB of inert text that no
page ever loads, and keeping it means the deployed directory is byte-identical
to the tested one, with no staging-copy step to drift out of sync.

---

## Provenance, in one sentence

Every number this app prints is either a value read off a live response
recorded in `../results.jsonl`, arithmetic over such values with no free
parameters, or a clearly-labelled substitution for something nobody has
measured yet — and the app tells you which.
