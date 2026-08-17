# Handover: reverse-engineering dxcalc.com/s1914

Black-box recovery of the combat formulas behind dxter's *Supremacy 1914* battle
calculator. Read this before touching `dxcalc_probe.py`.

**Status: the four queued experiments have now run live.** The POST
round-trips, the result semantics are settled, the whole unit roster is
measured three times over, fortresses are solved, and as of 2026-08-17
`buildings`, `trenches`, `air_vs_ground` and `hp_scaling` have all produced
results. `land_matrix` (~100 requests) is the main experiment still unrun.

What that session established, in one place:

- **Only the fortress mitigates damage.** The other seven building types
  render a row, take damage, and confer no DR at all.
- **Trenches enlarge the pool; they do not reduce damage.** The old
  "levels 1–3 conferred no benefit" was half right and half a reading error.
- **No air unit is immune to anything.** The Bomber deals 30.0 to every ground
  unit measured, heavy tanks included.
- **Attack values are per target class.** The Bomber is 3.0 against air and
  30.0 against ground; `MEASURED_UNITS` only ever saw the diagonal.
- **A stack's output scales with what survives the round's incoming fire** —
  in air-to-ground. This one is new, it is not present in land-to-land, and
  it explains a target-dependence that does not exist.
- **`m(f) = 0.05 + 0.95f` confirmed exactly**, and a wiped stack still deals
  its full damage.
- **Patrol is a different attack from a direct air strike**, measured after the
  question was raised: the same base stat, but a much lighter attrition charge
  (c ~ 0.36-0.43 against 1.000), so patrol beats a direct attack by up to 22%
  against a target with real anti-air. And `maxRounds` scales patrol damage
  linearly while being **ignored entirely** in `air`.

**Read §1 before anything else: the next session needs to start in the right
environment, and that cannot be fixed once it is running.**

---

## 0. The single most important lesson

**Every "the calculator does nothing" result so far has turned out to be a bug in
our rig, not a fact about the game.**

- Fortresses "produced zero effect in every configuration tried" for the whole
  first phase of this project. Cause: we were writing to `bldg.0`, a hidden
  template row. Real buildings are `bldg.1..N`. Once corrected, fortresses show
  a clean linear damage-reduction law.
- The attacker's reading was `-8.5` at every fortress level. Cause: the
  building's own result row was overwriting the attacker's slot.
- The most informative text on the page — `DR: 90% → 87.5%` — was invisible
  because the scraper stopped capturing at a nested `</span>`.

Treat a null result as a defect report against the probe until proven otherwise.
Three separate ones were, and each hid the next.

**The 2026-08-17 session made it six, in four different disguises.** The rule
generalises past null results: *any* confident verdict from this rig is worth
one look at how it was computed.

- The `buildings` sweep asked for level 3 on all eight types. Only the fortress
  goes that high, so five types were rejected with `oops: max level for X is 1`
  and reported as untested. **Not a null result — a rejected request.** The
  server states each cap; the sweep now reads it and retries.
- A level-1 Recruiting Office has 5 HP and dies to the 8.5 damage 30 infantry
  deal. The page then prints `- 5.0 HP (100%) destroyed`, with no arrow and no
  LVL tail, which the parser did not match — so it printed `NO ROW`, **the same
  output it gives for a type the server ignored entirely**, which is the one
  distinction that experiment exists to make.
- The `trenches` sweep proved trenches enlarge the defender's pool, then
  checked the attacker by comparing absolute HP lost — 50.0 with a trench, 50.0
  without — and concluded "no effect while attacking". The percentage had moved
  25% → 18.5%. **The blunt test that produced the original wrong conclusion,
  reproduced one function further down the same file**, in an experiment
  written specifically to avoid it.
- `air_vs_ground` reported all three aircraft TARGET-DEPENDENT from a 34%
  spread that is entirely return fire. **This one would have gone into the
  model as a game mechanic**; it is an artifact of what the attacker was
  shooting at. See §4.
- `unit_stats` was re-run because §9 promised the summary table would sharpen
  max HP into clean integers. It did not, and could not: the binding constraint
  is the percentage's significant figures, not the HP's. **The handover itself
  was the defective instrument that time.**

- `patrol` had never been run at all, so every air figure in this document
  described a direct attack. When it did run it produced **two more wrong
  verdicts in one sweep**: a single changed attrition coefficient read as
  "differs, and depends on the target", and `maxRounds` being ignored in `air`
  read as "worn down between ticks" because the per-round rate fell. A falling
  rate is what dividing a constant by a growing number looks like.

Seven of those eight were the rig reporting something false with confidence,
not reporting nothing. "Treat a null result as a defect report" is too narrow.

**And note how the patrol gap was found: someone asked whether it had been
tested.** Nothing in the rig flagged it. `results.jsonl` had 150 rows and not
one of them carried `terrain=patrol`; the coverage hole was invisible because
nothing counts what was never attempted. Worth asking of any dimension of the
form: not "what did we measure" but "what has never once been submitted".

---

## 1. Environment (read this first)

`dxcalc.com` is **blocked by default** in Anthropic-hosted cloud environments —
the egress gateway returns `403` with `x-deny-reason: host_not_allowed`. DNS,
`/etc/hosts` entries and IP pinning make no difference; the block is on the
hostname at the proxy, applied after resolution.

A cloud environment named **`dxcalc`** has been created with:

- **Network access**: `Custom`
- **Allowed domains**: `dxcalc.com` (plus the Artifact content domains)
- **Also include default list of common package managers**: ticked

**You must select that environment when the session starts.** A new environment
is not used automatically, and network policy is read once at provisioning — it
cannot be changed for a session already running.

Verify before doing anything else:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://dxcalc.com/s1914     # want 200
```

If that returns `000`/`403`, you are in the wrong environment. Say so and stop;
do not try to route around the proxy.

### The apex is the host that matters (2026-08-17)

A session ran in an environment where the allowlist covered the **subdomain but
not the apex**, which fails in a way worth recognising because it looks half
working:

```
https://dxcalc.com/s1914        curl: (56) CONNECT tunnel failed, response 403
https://www.dxcalc.com/s1914    301  ->  location: https://dxcalc.com/s1914
```

`www` resolves, connects and answers — and then redirects straight into the
blocked apex, so following the redirect fails anyway.

The cause was confirmed from the environment's own settings. Its allowed-domains
list read:

```
*.dxcalc.com
*.frame.claudeusercontent.com
*.frame.staging.claudeusercontent.com
```

**A wildcard covers subdomains but not the apex.** `*.dxcalc.com` matches
`www.dxcalc.com` and nothing else useful; the form lives at `dxcalc.com`. The
list has to name the bare host explicitly:

```
dxcalc.com
*.dxcalc.com
```

Keep the wildcard alongside it — harmless, and it covers the `www` hop.

Two further traps around this, both real:

- **Editing the environment does not affect a running session.** The settings
  dialog says so outright ("Changes to your environment will apply to new
  sessions"), and it was tried: a session provisioned at 12:45 was still being
  denied at 15:16 after the allowlist was changed. Save, then start a NEW
  session.
- **There may be several environments named `Default`.** The picker shows the
  name only, so it is easy to edit one and then start the session in the other.
  There was no environment named `dxcalc` at all, despite the note above
  describing one.

Two ways to tell this apart from the site being down, neither of which requires
guessing:

```bash
curl -sS "$HTTPS_PROXY/__agentproxy/status"     # recentRelayFailures names the host
curl -sS -o /dev/null -w '%{http_code}\n' https://example.com/   # 403 too => allowlist
```

`dxcalc_probe.py` now prints this diagnosis itself when a request dies on a
tunnel/403 rather than leaving you to read it as a TLS or DNS problem.

Local setup notes for the macOS checkout (pyenv 3.11.9): the script passes
certifi's CA bundle explicitly because pyenv builds against an OpenSSL whose
default cert path macOS doesn't populate. There is also a stale
`107.180.232.60  dxcalc.com` line in that machine's `/etc/hosts`, added to work
around a wedged `mDNSResponder`. **It should be removed when this project ends**
— it will go stale if dxter changes hosting.

---

## 2. Corrections to the original handover

The document that started this project contained four errors. They are listed
here because two of them actively drove experiment designs.

| Claim | Reality |
|---|---|
| "Building rows index from 0. Unit rows index from 1. This asymmetry is real." | **Wrong, and it cost the whole fortress phase.** `bldg.0` is a `<div hidden>` template that the page clones; `addBuilding()` starts at `newId = 1` and `renumberBuildings()` walks `1..maxBuildings`. Real buildings are `bldg.1..N`. |
| "Isolation is by 10 km spacing; ranged units contaminate neighbours." | Wrong. Isolation is by the `target` field. `A.n.target = B.n` pairs them, `target = 0` defends. Position governs range-to-target and building inheritance only. |
| Per-unit damage: infantry 4.0, cavalry 15, artillery 8, heavy tank 45 | Only infantry 4.0 survived, and only as the *attacking* value. See §4 — attack and defence are separate stats, and those figures carried no side label. |
| "Trenches add to the defender's HP pool rather than reducing damage. Levels 1–3 conferred no benefit." | **Half right, verified 2026-08-17.** The pool claim is correct. "No benefit at 1–3" is the pool-only reading: levels 1–3 leave the pool alone but already raise the defender's damage output by 25–35%. See §4. |

---

## 3. Form schema

POST `https://dxcalc.com/s1914`. A fresh GET yields **33 fields** — stacks `A.1`
and `B.1` only. Everything else is injected client-side by the page's own JS.

```
{side}.{stack}.target        "0" = defend, else "B.1" / "A.1"
{side}.{stack}.terrain       land | sea | air | patrol | debark
{side}.{stack}.position      0 1 2 3 10 20 30 40 50 75 150   (km)
{side}.{stack}.trench        0..20
{side}.{stack}.bldg.{i}.abb  fortress recruiting railway workshop
                             factory barracks aerodrome harbor
{side}.{stack}.bldg.{i}.lvl  1..5
{side}.{stack}.bldg.{i}.hp   "100%" or absolute
{side}.{stack}.{row}.unit    17 codes
{side}.{stack}.{row}.count
{side}.{stack}.{row}.hp      "100%" or absolute (stack TOTAL, not per unit)
maxRounds                    accepts decimals: 0.25 / 0.5 / 0.75
simulateVariance             "on" | ""
updateCounts                 "on" | ""
newWindow                    "on" | ""
```

**Building rows: `bldg.0` is a hidden template, real rows are `bldg.1..N`.**
Unit rows index from 1. The browser submits `bldg.0` on every request carrying
`fortress / 1 / 100%`, and the server ignores it — leave it exactly as the form
supplies it, since it cancels between control and treatment.

### The submit marker

The Start Battle control is `<input type="button">`. It calls
`onAttack('MainSubmitButton','Start Battle')`, which creates a hidden input with
that name/value, appends it to the form, and only then submits. **The field does
not exist in the DOM until the button is clicked.** Without it the server
re-renders the empty form with no results and no `oops` — silent, and easily
misread as a malformed payload. `Probe.load_form()` scrapes it out of the
onclick attribute and injects it into every POST, printing
`Submit marker: MainSubmitButton = 'Start Battle'` on load. **If that line is
missing, stop.**

This was the *only* thing ever broken about the transport. The form declares
`enctype="multipart/form-data"` and a browser does post multipart, but the server
accepts plain urlencoded too — confirmed live. `--encoding multipart` exists as a
byte-faithful fallback; reach for it only if a value containing `&`, `=` or
non-ASCII misbehaves.

### Unit codes

| Class | Codes |
|---|---|
| Land | `inf` `cav` `ac` `lart` `art` `rrg` `lt` `ht` `convoy` `st` |
| Air | `bal` `int` `tac` `zep` |
| Naval | `sub` `cl` `bb` |

`lart` = Light Artillery, `rrg` = Railgun, `lt` = **Tank** (not Light Tank),
`convoy` = Airplane Convoy, `st` = Stormtrooper, `int` = Fighter,
`tac` = Bomber, `cl` = Light Cruiser.

---

## 4. Confirmed model

### Result span semantics — settled

`span.hpLeft` holds **HP LOST**, despite the class name. The rendered text is
`Lost 50.0 HP (16.7%) 2 died`. Proven by `--semantics`: hold one side's count
fixed and grow the other, and each side's reading tracks only the *opponent's*
count, never its own.

The percentage is that loss as a fraction of the stack's full pool, so every
reading yields the pool for free: `pool = lost / pct`. Divide by the unit count
and you have that unit's max HP **from the same request that measured damage**.
`parse_reading()` returns `lost / pct / died / pool`.

Deaths are `floor(HP_lost / unit_max_hp)`.

### The per-stack summary table — free precision, previously unread

Every stack's result block is followed by a `<table class=resultTable>` that
the spans do not duplicate:

```
| HP lost | % lost | food | fish | iron | wood | coal | oil | gas | cash | hours
|  141.67 |   23.6 |    0 |    0 |    0 |    0 |    0 |   0 |   0 |  $0 |    23
```

The two sources are complementary, and neither dominates:

| | HP lost | % lost |
|---|---|---|
| span | `141.7` (1 dp) | `1.89%` (3 s.f.) |
| table | `141.67` (2 dp) | `1.9` (1 dp) |

So the best pool available from a single request is the **table's HP over the
span's percentage**. On the captured fortress response that moves the
defender's pool from `597.9` to `599.5` against a known `600` — the error drops
by a factor of four. That is the cap on `maxHP`, which is why the unit table
reads `60.06 / 175.44 / 260.12` for what are plainly `60 / 175 / 260`. **Worth
re-running `unit_stats` for this reason alone: same requests, sharper table.**

The table counts **unit rows only** — B.1 lost 11.3 HP of infantry and 8.5 HP
of fortress, and its table says `11.33`.

`refine_details()` performs the substitution, but only after checking that the
stack's spans sum to the table it claims to summarise. A table attached to the
wrong stack would look exactly as plausible as the building row that clobbered
the attacker's slot for the whole first phase of this project, and that is the
one failure mode this codebase should never re-learn by accident.

`hours` (23 for the attacker, 1 for the defender) and the resource columns are
unexplained. They are recorded rather than interpreted.

### Stack size factor

```
E(n) = n                                    n <= 20
E(n) = 20 + k*(60-k)/60,  k = min(n,50)-20  n > 20
```

Saturates at 35 effective units; stacking past 50 does nothing. Independently
re-confirmed at n=30: `E(30) = 28.3333`, and `28.3333 × 4.0 = 113.3` matched the
fortress control exactly.

### HP scaling — re-verified 2026-08-17

```
m(f) = 0.05 + 0.95*f
```

Re-run live after the parser fixes, `--run hp_scaling`, ten points at 10%
intervals. **Zero deviation at every point.** The 0.05 floor is real: a stack
at 10% HP deals 14.5% of full damage, not 10%. This is no longer the
low-confidence entry it was.

The pool scales linearly with no floor (`pool = n * maxHP * f`), so the floor
is specifically on output.

### A wiped stack still deals its full damage — settled

Listed as an open question through the whole project, and answered for free by
the sweep above. Fifty defenders deal `5.0 × E(50) = 175` HP per round, more
than a damaged ten-stack can absorb, so the attacker was **destroyed in 8 of
those 10 rounds** — and those eight points sit exactly on the line the two
surviving rounds define.

So a stack that dies inside the measured round still delivers its full attack.
Every coefficient read from the far side of a wiped stack is sound, which
retroactively validates the lopsided re-runs in `unit_stats` and the
`STILL WIPED` cells in the matrix experiments.

Note this does *not* license ignoring saturation. A wiped stack's own **loss**
is still capped at its pool, so the coefficient read *from* it is still a lower
bound. What is now known is that the reading from the *other* side is clean.

### Return fire: output scales with what survives — air-to-ground

**New, and the most consequential finding of the 2026-08-17 session.** In an
air-attacks-ground battle, a stack's delivered damage is scaled by the share of
its own pool that survived the round:

```
dealt = base_stat * E(n) * (1 - own_fraction_lost)
```

Measured across all 30 cells of `air_vs_ground`. Correcting for it collapses
each aircraft's apparent target dependence onto a single flat stat:

| attacker | raw spread across 10 ground targets | corrected | stat |
|---|---|---|---|
| `int` Fighter | 3.68 – 4.95 (×1.34) | 5.000 – 5.022 | **5.0** |
| `tac` Bomber | 24.00 – 29.75 (×1.24) | 30.000 – 30.121 | **30.0** |
| `zep` Zeppelin | 4.43 – 4.98 (×1.12) | 5.001 – 5.016 | **5.0** |

Two cells come out exact rather than merely close, and they are the ones where
the arithmetic has no rounding slack: `tac` vs `ac` gives `160/800 = 0.2` and
`30 × 0.8 = 24.000`; `tac` vs `ht` gives `80/800 = 0.1` and `30 × 0.9 = 27.000`.

**This is measured for air attacking ground. It is demonstrably absent in
land-vs-land**, and the evidence is a control already in `results.jsonl`: the
trench control has 10 infantry attacking 10 infantry, the attacker loses 25% of
its pool, and the defender still loses exactly `4.0 × 10 = 40.0` — unattenuated.
So either the mechanic is specific to air raids (the natural reading: ground
fire resolves first and the survivors deliver the attack) or something else
distinguishes the two cases. **Untested for sea, and for air defending.**

Consequences worth carrying:

- The air rows of `MEASURED_UNITS` were measured air-vs-air with return fire
  present and are therefore **suspect** — they may be attenuated.
- `report_matchups()` judges on the RAW row and consults the correction only
  when the raw row slopes, because applying it to a non-attenuating server
  turns a flat attacker into a target-dependent one. Do not reverse that order.

### Attack and defence are independent stats

Not one number plus a global defender bonus. Seven units differ between the two,
nine are symmetric. Infantry's 1.25 ratio is specific to infantry.

**These are same-class values.** Every row was measured U-vs-U, and
`air_vs_ground` has since shown that attack depends on the target's class: the
Bomber is 3.0 here and 30.0 against ground. Read the `atk`/`def` columns as
"against its own kind" until the off-diagonal is measured.

| unit | class | maxHP | atk | def | def/atk |
|---|---|---|---|---|---|
| inf | land | 20 | 4.0 | 5.0 | 1.25 |
| cav | land | 25 | 15.0 | 7.5 | 0.50 |
| ac | land | 60 | 6.0 | 12.0 | 2.00 |
| lart | land | 10 | 5.0 | 1.0 | 0.20 |
| art | land | 20 | 8.0 | 2.7 | 0.34 |
| rrg | land | 60 | 20.0 | 6.7 | 0.34 |
| lt | land | 175 | 30.0 | 30.0 | 1.00 |
| ht | land | 260 | 45.0 | 45.0 | 1.00 |
| convoy | land | 20 | 1.0 | 1.0 | 1.00 |
| st | land | 40 | 25.0 | 6.3 | 0.25 |
| bal | air | — | — | — | — (guarded, see traps) |
| int | air | 60 | 20.0 | 20.0 | 1.00 |
| tac | air | 80 | 3.0 | 3.0 | 1.00 |
| zep | air | 140 | 5.0 | 5.0 | 1.00 |
| sub | sea | 100 | 40.0 | 40.0 | 1.00 |
| cl | sea | 50 | 10.0 | 10.0 | 1.00 |
| bb | sea | 200 | 40.0 | 40.0 | 1.00 |

Measured by `--run unit_stats`, one request per type, reproduced identically on
**three** runs (two an hour apart, a third on 2026-08-17) — the engine is
deterministic with variance off.

#### Max HP is a bracket, and every bracket holds one integer

The `60.06 / 175.44 / 260.12` readings are not evidence of non-integral HP, and
§9 was wrong about how to fix them. The summary table sharpens **HP lost**, and
for these units the span's HP was already exact: a tank duel removes `300.0` of
`1750`, the page prints `17.1%`, and `300 / 0.171 / 10 = 175.44`. **The binding
constraint is the percentage's three significant figures.** No extra precision
in the HP column can touch it.

Both inputs are rounded, so max HP is an interval:

```
maxHP ∈ [ (lost - u) / (pct_hi * n),  (lost + u) / (pct_lo * n) ]

  u        = 0.005 from the summary table, 0.05 from a span
  pct_lo/hi = the printed percentage ± half a unit in its last significant place
```

`hp_bounds()` computes it; `sole_integer_in()` reports whether exactly one whole
number lies inside. On the live roster **all 16 measurable units bracket exactly
one integer, and every one is the round number above** — including `lt` at
`174.92–175.96` and `ht` at `259.36–260.87`. `lt` and `ht` are independently
confirmed by the stock form, which ships `525/3 = 175.0` and `260/1 = 260.0`.

Two things follow for anyone extending this:

- **Do not quote the midpoint to two decimals.** `175.44` is not a measurement
  of anything; the measurement is `174.92–175.96`, and it says 175.
- **Integrality is an inference, not a reading.** It is a strong one — 16 of 16,
  two confirmed independently — but a unit with genuinely fractional HP would
  present as a bracket holding no integer, and that is reported rather than
  rounded away.

Where a bracket *is* ambiguous, the sweep re-reads with the defender sized to
lose ~90% of its pool, where 3 s.f. is worth ten times more, and **intersects**
the two brackets rather than replacing one with the other. That ordering is
load-bearing: a percentage that prints exactly (`37.5`) is indistinguishable
from one that was rounded (`17.1`), so a re-read chosen on a worst-case error
bar can land *further* from the truth than the reading it replaces. Intersecting
brackets cannot. The live roster needed no re-reads, so this cost nothing.

Note the pattern worth testing: every asymmetric unit is a land unit, and every
air and naval unit measured is symmetric.

### Fortresses

A fortress on the **defender** scales incoming damage by

```
m(L) = 0.85 - 0.15*L        L = 1..5   ->   0.70  0.55  0.40  0.25  0.10
```

All five points fit exactly, reproduced on two runs. The page states the
mechanic itself in the building's result row:

```
-8.5 HP (3.4%) → LVL:5 41.5 HP; DR: 90% → 87.5%
```

`DR` is Damage Reduction. `DR 90%` at level 5 *is* `m(5) = 0.10`. The
before/after pair pins the underlying formula:

```
DR = 0.15 * (fortressHP / 50 + 1)

  full L5:  250.0 HP -> 0.15 * 6.00 = 90.00%
  damaged:  241.5 HP -> 0.15 * 5.83 = 87.45%    (page prints 87.5%)
```

So the `+1` discontinuity — having a fortress at all costs the attacker 15%
before levels count — is in the game's own formula, and **mitigation decays
continuously as the fortress is worn down**, which no amount of level-sweeping
would have revealed.

Also established:

- **Fortress HP = 50 per level**, damage taken off the top level
  (`50 − 8.5 = 41.5`, exactly as printed).
- **Infantry deal 0.3 per effective unit to buildings**, against 4.0 to units
  (`8.5 / E(30) = 0.3` exactly).
- **Fortresses do not reduce the defender's output.** The attacker loses 141.7
  at fortress level 5, identical to the no-fortress control.

### Patrol — measured 2026-08-17, and it is not air

**Every air number in this document above was flown in `air` terrain.** In 150
requests `patrol` had never been submitted once, so the whole air column
described a DIRECT attack only — which is not how these units are usually
flown. `--run patrol`, 18 requests, changed that and turned up two mechanics.

#### 1. The base stat is the same; the attrition charged against it is not

A stack's output is

```
dealt = base * E(n) * (1 - c * its_own_fraction_lost)

    c = 1.000   direct air attack        (this is the return-fire law in the
                                          section above, restated)
    c ~ 0.36-0.43  patrol
```

Every attacker's air-to-ground stat comes back unchanged when read through
patrol — `int` 5.006/5.024/5.008, `tac` 30.026/30.000/30.000, `zep`
5.003/5.002/5.015. So the air column **does** carry over. What changes is how
much of its own attrition is charged against its output.

The practical consequence is large and one-directional: **patrol beats a direct
attack by more the harder the target shoots back, and by nothing at all against
a target that cannot.** Measured, at maxRounds 1:

| attacker | vs `inf` (AA 0.4) | vs `ht` (AA 4.0) | vs `ac` (AA 8.0) |
|---|---|---|---|
| `int` | +1.4% | +9.7% | **+22.3%** |
| `tac` | +1.0% | +7.0% | **+13.9%** |
| `zep` | +0.6% | +3.6% | **+8.1%** |

**`c` is not pinned to a single value** and should not be quoted to three
decimals. Nine cells give 0.360–0.427, and the scatter does not track `f`, so
it is not simply reading precision — the delivery is probably discrete (ticks,
or whole units dying at tick boundaries) rather than a smooth fraction. The
cells that constrain it best (`f` >= 0.05) cluster at 0.360–0.376, bracketing
3/8. Treat 3/8 as a working value and the range as the honest statement.

#### 2. `maxRounds` means different things in the two terrains

```
patrol   damage is PROPORTIONAL to maxRounds
air      maxRounds is IGNORED — one strike, whatever you ask for
```

`tac` vs `inf`, corrected damage per unit at maxRounds 0.25 / 0.5 / 0.75 / 1:

```
patrol    7.53   15.10   22.70   30.33      (linear in rounds)
air      30.03   30.03   30.03   30.03      (flat: the round setting does nothing)
```

This is why the quarter-round granularity exists and it is worth keeping in
mind for every other experiment: **any sweep that varies `maxRounds` in `air`
terrain is varying nothing.**

#### 3. The balloon hole does not close

`bal` is the only unit with no measured stats, because `guard_payload()`
refuses it in `air` where it kills the whole submission. The guard never
covered `patrol` and nobody had tried it. The server's answer:

```
oops: Can't have Balloon in the air.
```

So patrol counts as the air for that check and the hole is permanent through
this route. Note this came back as a clean `oops` rather than the silent batch
abort the guard was written for — worth knowing, but not worth a request to
chase. **`guard_payload()` should be widened to cover `patrol`** so the next
sweep does not spend a request rediscovering it.

#### Two verdicts this sweep got wrong first

Both are in §5, and both are the same failure as everything else in §0:

- It read the per-target ratio spread (1.006–1.223) as "patrol differs AND the
  difference depends on the target", which is precisely what a **single changed
  coefficient** looks like through a raw ratio.
- It read air's falling per-round rate as "worn down between ticks". The rate
  falls because a constant is being divided by a growing number. `maxRounds` is
  ignored in air; nothing is being worn down.

### Trenches — measured 2026-08-17, two separate effects

`--run trenches`, 10 infantry vs 10 infantry, sweeping `B.1.trench`.

| trench | defender's HP lost | defender's pool | defender's deaths | attacker's HP lost |
|---|---|---|---|---|
| 0 | 40.00 | 200.0 | 2 | 50.0 |
| 1 | 40.00 | 200.0 | 2 | 62.5 (×1.25) |
| 2 | 40.00 | 200.0 | 2 | 65.0 (×1.30) |
| 3 | 40.00 | 200.0 | 2 | 67.5 (×1.35) |
| 4 | 40.00 | 229.9 (×1.15) | 1 | 70.0 (×1.40) |
| 5 | 40.00 | 239.5 (×1.20) | 1 | 70.0 (×1.40) |
| 10 | 40.00 | 248.4 (×1.24) | 1 | 77.0 (×1.54) |
| 15 | 40.00 | 259.7 (×1.30) | 1 | 81.0 (×1.62) |
| 20 | 40.00 | 270.3 (×1.35) | 1 | 87.5 (×1.75) |

**A trench does two independent things, on two different schedules.**

1. **It enlarges the pool**, from level 4 up. Absolute HP lost never moves —
   the attacker's `4.0 × 10 = 40.0` arrives in full at every level — so this is
   not damage reduction, and the fortress mechanic is not what is happening.
   The deaths column is an independent confirmation from the same requests:
   `40 / 20 = 2` deaths at 20 HP per unit, falling to 1 once per-unit HP
   exceeds 20.
2. **It raises the defender's damage output**, from level 1 up, reaching ×1.75
   at level 20. This is what the original "levels 1–3 conferred no benefit" note
   missed: at levels 1–3 the pool genuinely does not move, but the defender is
   already hitting 25–35% harder.

The two curves are not proportional to each other and neither is smooth —
output plateaus at ×1.40 across levels 4 and 5 while the pool keeps growing.
Both are probably table lookups rather than formulas. `bytro.js` contains no
trench logic at all (it is form-side only), so this has to come from readings.

**The HP bonus applies while attacking; the damage bonus does not.** With the
trench on the attacker instead, at level 20: the attacker's pool grows by the
same ×1.3515 and its deaths fall 2 → 1, while the defender still loses exactly
40.00, so the attacker's output is unchanged.

That last line is where the first live run got it wrong. It compared the
attacker's *absolute HP lost* — 50.0 with a trench, 50.0 without — and printed
"no effect while attacking". The percentage had moved 25% → 18.5%. The check
now applies the same pool-based discriminator as the sweep above.

`BLDG_TAIL_RE` reads level, remaining HP and current DR straight off the page,
so the remaining seven building types need no curve-fitting at all.

### The other seven buildings — measured 2026-08-17, all combat-inert

`--run buildings`, one request per type against a 30-infantry attack.

| type | level | pool | top-level HP | DR clause? | defender's loss vs control |
|---|---|---|---|---|---|
| fortress | 3 | 150.0 | 50 | `DR: 60% → 57.5%` | **×0.400** |
| recruiting | 1 | 5.0 | — destroyed | none | ×1.000 |
| railway | 1 | 60.0 | 60 | none | ×1.000 |
| workshop | 3 | 35.0 | 20 | none | ×1.000 |
| factory | 3 | 120.0 | 40 | none | ×1.000 |
| barracks | 2 | 80.0 | 40 | none | ×1.000 |
| aerodrome | 1 | 60.0 | 60 | none | ×1.000 |
| harbor | 1 | 60.0 | 60 | none | ×1.000 |

**Only the fortress mitigates.** This is a real result rather than a null one,
and the distinction is exactly what the experiment was built to make: the other
seven *do* render a result row and *do* take the same 8.5 HP of damage, so the
field demonstrably reached the server and had a visible effect. What is absent
is the `DR:` clause, and its absence is a positive reading, not a silence.

The fortress cell independently reproduces `m(3) = 0.40` from §4 on a third
run, and the page prints `DR: 60%`, which is `1 - 0.40`.

Two incidental findings:

- **Level caps vary and the server states them.** Only the fortress reaches
  level 5; barracks caps at 2, and recruiting, railway, aerodrome and harbor at
  1. Asking for more returns `oops: max level for Recruiting is 1` rather than
  clamping. `parse_max_level()` reads the cap out of that message, so the sweep
  carries no table of caps to drift out of date.
- **Buildings are not uniform HP per level.** Fortress is 50/level and factory
  40/level, but a level-3 workshop has a 35 HP pool with 20 in its top level —
  which is not `3 × 20`. Recruiting is 5 HP at level 1. Worth two requests to
  settle if anyone cares; nothing else depends on it.

---

## 5. Bugs fixed in the probe

Listed because several produced plausible-looking wrong answers rather than
errors, and because the same failure modes will recur.

| Bug | Symptom | Status |
|---|---|---|
| Missing submit marker | Bare form, no `oops`, no results | Auto-injected; marker line prints on load |
| `parse_hp` read `,` as a decimal point | `"1,375.1"` parsed as **1.375** — a silent 1000× error, only above 999 HP, exactly where the size sweep operates | `strip_thousands()` |
| `submit()` dropped unknown keys silently | An experiment believes it configured something it did not | Now loud when the dropped key had a *value*; blanking a nonexistent row is still silent (`duel()` does it deliberately) |
| Fortress sweep wrote `bldg.0` | Control identical to the level-1 run; ratio 1.0 by construction; six wasted requests a run | Writes `bldg.1` via `submit(..., create=...)` |
| Guard checked `bldg.0 not in baseline` | Dead branch — the template is always present, so the tripwire could never fire | Removed |
| Building row overwrote a unit slot | `B.1.bldg.1` didn't match `SLOT_RE`, inherited `A.1.1`, and destroyed the attacker's reading in every fortress run | `RESULT_SLOT_RE` |
| Nested `</span>` ended capture early | Truncated `-8.5 HP (3.4%) →` before `LVL:… DR:…`, the most informative text on the page | Span depth counting |
| `--semantics` ruled on absent data | `None == None` passed vacuously, printing "VERDICT: HP LOST" with a 0.0/0.0 split from zero measurements | Refuses; reports `NO VERDICT` |
| **A failed submit ate the test fixture** | `submit()` dumped any response with no readings to `last_response.html` — which is also the *committed capture of the real form* that all offline suites are built on. One balloon-in-air is enough: the fixture becomes a 38-byte stub, all suites fail with "page layout changed?", and the finger points at dxcalc.com when nothing about the site has changed | Failures now go to `last_failure.html` (gitignored); `test_probe_offline.py` asserts the fixture is byte-identical after a deliberate failure |
| A bad `--run` name cost a live request | The experiment name was validated *after* `load_form()`, so a typo spent a page view and printed its complaint afterwards | Validated before the probe is constructed |
| Saturation re-run could re-send an identical payload | At the defender-count cap the retry loop resent the same body and learned nothing | Retries only while the count actually grows |
| `buildings` hardcoded level 3 | Five of eight types rejected with `oops: max level for X is 1` and reported as untested — a rejected request misread as a measurement | `parse_max_level()` reads the cap from the server's own message and retries once |
| A destroyed building parsed as nothing | `- 5.0 HP (100%) destroyed` has no arrow and no LVL tail, so `DELTA_RE` missed it and the sweep printed `NO ROW` — identical to what it prints for a type the server ignored | Arrow or `destroyed` both terminate the pattern; a `destroyed` flag is recorded |
| Attacker's trench judged on absolute HP lost | "No effect while attacking" while the percentage moved 25% → 18.5% — the original wrong conclusion, reproduced inside the experiment written to avoid it | Judges the derived pool, and reports the output effect separately |
| Return fire read as target dependence | All three aircraft reported TARGET-DEPENDENT from a 34% spread caused entirely by how hard each target shoots back | `report_matchups()` judges the raw row, then tests whether return fire explains any slope |
| Max HP quoted as a midpoint | `175.44` presented as a measurement when the reading only supports `174.92–175.96` | `hp_bounds()` / `sole_integer_in()`; the bracket is the result |
| `patrol` never run, and its sweep sent 1 attacker at 1 target | Every air figure silently described a direct attack only; the queued experiment could not have seen a target rule or corrected for return fire | Rewritten: 10 attackers, 3 targets, reads the air half back off disk, corrects attrition |
| Patrol ratio spread read as target dependence | One changed attrition coefficient looks exactly like a target rule through a raw ratio | Fits `c` per cell against the base stat from the air cells; an impossible `c` means it really is the stat |
| Air's falling per-round rate read as attrition | `maxRounds` is ignored in `air`, so damage is constant and the rate falls as 1/rounds | Checks whether the damage itself is constant before calling anything attrition |
| `hp_scaling` printed no fit at all | Ten raw records appended, the law worked out by hand afterwards and easy to skip | Prints the ratio table and rules on it, including the wiped-stack question |

---

## 6. Methodology rules

- **Isolation is by the `target` field**, not by distance.
- **`simulateVariance` must be off** for coefficient fitting. On, the server
  rolls ±10% and each reading is a sample, not the expected value.
- **One pair per submission** for now. A single invalid combination aborts the
  entire batch, so batching multiplies the cost of one bad cell.
  `bytro.js` allows `maxStacks = 100`, so batching can scale later.
- **Defender terrain must be set explicitly.** `duel()` defaults `def_terrain`
  to `atk_terrain`, which puts a heavy tank in the air for an air-attacker run.
- **`maxRounds` accepts 0.25 / 0.5 / 0.75.** Patrol fires 4 ticks of quarter
  damage per round, so 0.25 isolates a single tick.
- **Keep counts at 10 where possible** so `E(n) = n` exactly and the size factor
  cannot confound a reading.
- **Watch for saturation.** A stack wiped in the measured round has its loss
  capped at its pool, understating the *opponent's* damage — but only for the
  coefficient read from that stack. `unit_stats` re-runs lopsided (4v20, 20v4)
  when that happens, judging each rescue by the one side it is read from.
- **Correct for return fire before comparing damage across targets** — at least
  in air-to-ground, where it is measured. A raw reading is the stat times the
  share of the attacker's pool that survived, and targets vary enormously in how
  hard they hit back, so a perfectly flat attacker still produces a sloping row.
  Equally: do **not** apply the correction before establishing that the slope is
  there, or you will manufacture the opposite error. Both directions have now
  been made in this codebase.
- **`maxRounds` does nothing in `air` terrain.** It scales patrol damage
  linearly and is ignored by a direct air strike, so any sweep that varies it
  against an `air` attacker is varying nothing. Check the terrain first.
- **Ask what has never been submitted, not just what was measured.** `patrol`
  sat unrun through 150 requests because no experiment listed it and nothing
  counts an untried value. `grep` the terrain/field values actually present in
  `results.jsonl` before believing a dimension is covered.
- **Prefer a bracket to a point estimate** for anything derived by dividing two
  rounded numbers. Max HP is the worked example (§4): the interval says 175, the
  midpoint says 175.44, and only one of those is a measurement.
- **Read `results.jsonl` before designing a sweep.** Three of the 2026-08-17
  conclusions came out of records already on disk, at zero cost to dxter. The
  file is committed precisely so this is possible.
- **Courtesy.** This is one person's fan site, ad-supported, no API. Default
  delay is 1.5 s and should not be lowered much. Bugs found are worth mailing to
  dxcalc@gmail.com rather than just cataloguing. Nothing found so far is a bug
  worth mailing: the "Bomber does 0 to heavy tanks" report that motivated
  `air_vs_ground` is **not reproducible** — the Bomber deals 30.0 to every
  ground unit measured.

---

## 7. Known traps

| Trap | Symptom | Handling |
|---|---|---|
| Missing submit marker | Bare form, no `oops` | Auto-injected; verify the marker line prints |
| `bal` in `air` terrain | Whole batch aborts silently | `guard_payload()` refuses to send it |
| Pre-filled defender rows 2–4 | Contaminated readings, no error | `duel()` blanks rows 2–8 |
| Defender inherits attacker terrain | Invalid combination, batch aborts | Pass `def_terrain` explicitly |
| Building row with no HP | Silently ignored | Always send `abb` + `lvl` + `hp` |
| Writing to `bldg.0` | Silent no-op; looks like "buildings do nothing" | Use `bldg.1..N` |
| Fields absent from the GET baseline | Silently dropped | Pass `create=[...]` to synthesise, as the page's JS does |
| Building level above the type's cap | `oops: max level for X is 1`, no reading — easily filed as "type does nothing" | `parse_max_level()` reads the cap and retries |
| Building destroyed in the round | Row text loses its arrow and LVL tail | `DELTA_RE` accepts `destroyed` as a terminator |
| Comparing absolute HP lost across a defensive sweep | Cannot separate "bigger pool" from "no effect"; both hold HP lost constant | Compare the derived pool, and the deaths, not the loss |
| Comparing damage across targets that differ in return fire | A flat attacker reads as target-dependent | Correct by `(1 - own fraction lost)` — but only after checking the raw row slopes |
| Quoting a derived pool or max HP to 2 dp | Implies precision the 3 s.f. percentage does not support | `hp_bounds()`; report the bracket |
| Varying `maxRounds` against an `air` attacker | Every rung reads identically; looks like a flat law | `maxRounds` is ignored in `air`. Use `patrol` if you want duration |
| Fitting a coefficient from a low-`f` cell | `c = (1 - raw/base)/f` divides a tiny difference by a tiny number; error is (reading error)/`f` | Weight or filter by `f`; `exp_patrol` drops cells below 0.05 |
| `bal` in `patrol` | `oops: Can't have Balloon in the air` — patrol counts as the air | Widen `guard_payload()`; the roster hole is permanent by this route |

---

## 8. Running it

```bash
python3 dxcalc_probe.py --dump-fields    # schema + resolved action + marker
python3 dxcalc_probe.py --sanity         # one duel, verifies the round-trip
python3 dxcalc_probe.py --semantics      # 3 requests; what the span means
python3 dxcalc_probe.py --run buildings
python3 dxcalc_probe.py --run all --delay 2.0
```

Useful flags: `--dry-run` prints payloads instead of sending; `--save-response
PATH` writes each successful response body (invaluable — the fortress answer
came out of the raw markup, not the numbers); `--encoding multipart`;
`--delay`.

Results append to `results.jsonl` as JSON lines, one per submission, so a crash
mid-sweep loses nothing. **`results.jsonl` is committed deliberately** — every
line cost a live request against someone else's server. **150 rows** as of
2026-08-17: 68 `unit_stats` (the roster three times, which is the determinism
evidence), 40 `air_vs_ground`, 13 `buildings`, 10 `trenches`, 10 `hp_scaling`,
6 `fortress`, 3 `semantics`.

Several conclusions in §4 were derived by **replaying rows already in this file**
rather than by sending anything — the return-fire law, the wiped-stack answer,
and the corrected recruiting row all came out of records already on disk. That
is the cheapest kind of progress available here, and it is only possible because
the file is complete. Check it before designing a sweep.

The `semantics` and `unit_stats` rows were once lost — the file was committed
containing only the last fortress run — and had to be reconstructed from a
session transcript. Commit the file after every sweep. Re-deriving 37 rows
means spending someone else's bandwidth twice for the same numbers.

Experiments registered: `unit_stats`, `buildings`, `trenches`, `air_vs_ground`,
`land_matrix`, `size_factor`, `hp_scaling`, `patrol`, `fortress`, `terrain`,
`variance`. `--run` now prints the approximate request cost before it starts.

Measured costs, live: `sanity` 1, `buildings` 14 (9 plus up to 5 level-cap
retries), `trenches` 10, `air_vs_ground` 30, `unit_stats` 16–20 depending on how
many max-HP brackets need a second read, `hp_scaling` 10, `patrol` 18. The whole
2026-08-17 session came to about 124 requests including one repeated `buildings`
run.

`exp_patrol` reads the `air_vs_ground` cells back off `results.jsonl` instead of
re-flying them, which halves its cost. That pattern is worth copying: the file
is the cheapest instrument in the project.

`damage_land`, `damage_air` and `damage_sea` have been **retired** — they
predate `unit_stats`, they sent one attacker into twenty defenders (so the
attacker's reading was always the capped one), and they did not record which
side a reading came from, which merges attack and defence coefficients into an
average that is neither. Asking for them by name now prints what replaced them
instead of "Unknown experiment":

| retired | replacement |
|---|---|
| `damage_land` | `unit_stats` for the diagonal, `land_matrix` for the rest |
| `damage_sea` | `unit_stats` |
| `damage_air` | `air_vs_ground` |

### Tests — 211 checks, no network needed

```bash
python3 test_probe_offline.py       # 45  transport, parsing, slot association
python3 test_semantics_design.py    #  9  proves --semantics can discriminate
python3 test_unit_stats.py          # 25  recovers known constants; max-HP brackets
python3 test_fortress_row.py        # 24  bldg.1 vs the bldg.0 template; destroyed rows
python3 test_result_table.py        # 29  the summary table, against real markup
python3 test_trench_design.py       # 27  proves the trench sweep can discriminate
python3 test_matchup_design.py      # 30  proves the matrix can discriminate
python3 test_patrol_design.py       # 22  proves patrol can be told from air
```

These serve the site's courtesy budget as much as correctness: they run against
mock servers built from the real captured markup, so iteration costs dxter
nothing. `test_semantics_design.py` is worth reading as a pattern — it stands up
two servers whose physics differ only in what the span means, tunes both to
reproduce the real observation, and requires the right verdict against each. An
experiment that cannot distinguish its candidates returns a confident answer
either way.

`test_trench_design.py` and `test_matchup_design.py` apply the same discipline
to the two new sweeps, and each also asserts the thing the fortress phase got
wrong: that the server actually *received* the field being varied. The trench
test checks that all nine trench values reach the server and that the attacker's
trench moves independently of the defender's. Configuring a field the server
never sees produces a full sweep of identical readings and a confident "does
nothing" — which is precisely the history here.

Both suites gained servers on 2026-08-17 built from the live mistakes, and they
are the pattern to copy when adding an experiment. Each one is a server the
*old* code passes against and the correct code distinguishes:

- `test_trench_design.py` has a `pool_self` server whose absolute HP lost is
  identical on both sides at every trench level, so a check that reads only HP
  lost cannot pass against it.
- `test_matchup_design.py` has three: a flat stat seen through return fire
  (must be reported as explained), a flat stat with **no** attenuation (the
  correction must *not* be applied to it), and a genuine target-class rule
  (must survive the correction). The middle one exists because the first
  attempt at this fix judged everything on the corrected figure, which turns a
  flat attacker into a target-dependent one against a server that does not
  attenuate — the same error in the opposite direction.
- `test_unit_stats.py` renders percentages to three significant figures, as the
  site does. At one decimal place a tank duel reads a clean `175.0` and the
  whole max-HP precision problem is invisible to the suite.

**`last_response.html` is a fixture, not scratch.** It is the committed capture
of the real form, and every mock server serves it. A failed submission dumps to
`last_failure.html` instead; if you change that, you will silently destroy the
fixture the first time a run hits a bad combination.

---

## 9. Next steps, in order

Step 0 is `curl -sS -o /dev/null -w '%{http_code}\n' https://dxcalc.com/s1914`.

Steps 1–5 of the previous list are **done** (2026-08-17): `buildings`,
`trenches`, `air_vs_ground`, `unit_stats` re-run, `hp_scaling` re-verified.
Results are in §4 and in `results.jsonl`. What remains:

1. **`--run land_matrix`** — ~100 requests, so weigh it, but it is now the
   single highest-value experiment left. `air_vs_ground` proved attack is
   **per target class**, so the whole `atk` column of `MEASURED_UNITS` is a
   diagonal of a matrix nobody has seen. Two things to check before trusting
   any of it:
   - its diagonal must reproduce the `atk` column of `MEASURED_UNITS`;
   - whether land-vs-land shows the return-fire attenuation. The trench control
     says it does not, but that is one data point from a different experiment.
     If it does not, the raw readings are the stats directly and the matrix is
     much easier to read than `air_vs_ground` was.
2. **Re-measure the air roster's own stats.** The `int` / `tac` / `zep` rows of
   `MEASURED_UNITS` were taken air-vs-air with return fire present and are
   therefore probably attenuated — `tac` vs `tac` reads 3.0, and nobody has
   corrected it. One `air_vs_air` matrix, or just applying the §4 correction to
   the readings already in `results.jsonl`, would settle it. **Try the second
   first: it costs nothing.**
3. **Does return fire apply to sea, and to air *defending*?** Both are
   one-experiment questions and both change how existing numbers are read.
4. **`terrain`**, then **`variance`** (60+ samples, `simulateVariance=on`) to
   characterise whether the ±10% roll is per unit or per unit type per round.
5. **Building damage per unit type.** Infantry deal 0.3 per effective unit to
   buildings against 4.0 to units. One `buildings`-style run per attacker gives
   the whole column, and nothing else in the model predicts it.

Cheap and worth doing at some point:

- Two requests settle the workshop's odd HP curve (35 total at level 3 with 20
  in the top level).
- The `hours` and resource columns are no longer entirely unexplained — see
  §10 — but one battle with mixed unit types would confirm the reading.

---

## 11. The app

`web/` is a deployable static battle calculator that implements the model in §4
**locally**. It is five files — `index.html`, `styles.css`, `app.js`,
`engine.js`, `data.js` — with no build step, no dependencies and no backend.
`web/README.md` covers running and deploying it.

**It never contacts dxcalc.com.** That is a design constraint, not an
implementation detail, and it is the reason the app carries a re-implementation
instead of a proxy. dxcalc.com is one person's ad-supported fan site with no
API; the courtesy rule in §6 that keeps this project's own request rate at one
per 1.5 s would be meaningless if the deliverable then pointed an unbounded
number of strangers at the same host. A public proxy would put every user's
traffic on dxter's bandwidth without asking. So the app answers from measured
constants instead, and `test/engine.test.mjs` asserts that `engine.js` and
`data.js` contain no `fetch`, no `XMLHttpRequest`, no `WebSocket`, no `new URL`
and no dynamic import — so the property cannot quietly regress.

**Its engine is verified against `results.jsonl`.** The suite replays the
record row by row and compares the engine's prediction against what the site
actually printed; no expected value in it is a constant the engine itself
carries. Tolerances follow the page's print precision (§4): ±0.005 where the
summary table gave two decimals, ±0.05 from a span alone, deaths exact, and a
stack pool asserted inside its bracket rather than as a point — the midpoint
mistake from §4 is a test failure here, not a style preference. **All eight
experiments in the file are replayed**, and the suite asserts that no experiment
is left out.

Patrol is the interesting case, because the two halves of it have very different
confidence and the app has to carry both:

- Its **`maxRounds` behaviour is measured** and implemented as such — patrol
  damage is proportional to the round count, a direct strike ignores `maxRounds`
  entirely. The UI offers an *Air mode* control (strike / patrol) only for the
  air-versus-ground pairing where both were actually flown, and the Rounds field
  relabels itself to say which of the two you are looking at.
- Its **attrition coefficient is a band, not a number** — 0.360–0.427 over nine
  cells — so every patrol result is labelled `estimated` however clean the
  matchup, and the derivation prints the range beside the central figure
  (`c in 0.36-0.427 gives 274.38-278.4`). The nine cells replay to within 0.72%.

That split is the app working as intended: it would have been easy to quote a
single coefficient to three decimals and be believed.

```bash
node web/test/engine.test.mjs      # 609 checks, no network
```

The app is also where §0 gets enforced rather than merely written down. Every
constant in `data.js` carries a provenance key and one of four tags —
`measured`, `derived`, `assumed`, `unmeasured` — and a constant without one is
a defect. Every result is tagged `measured`, `estimated` or `unknown`;
`unknown` **withholds the number** instead of producing something plausible.
The land off-diagonal is the case that matters most: the app will compute
infantry-against-heavy-tank, but it labels the answer `estimated` and names the
substitution it made, because §4 established that attack is per target class
and the diagonal cannot be assumed to generalise. `data.js` exports
`NOT_MEASURED`, 24 gaps each with what is missing, why, and what would close
it; the UI's "What this model does not know" panel is rendered from that array,
so it cannot drift away from the code. Closing an experiment in §9 should mean
deleting an entry there.

`.github/workflows/pages.yml` deploys `web/` to GitHub Pages, gated on the
engine suite and all eight Python suites — it does not deploy if any fail.
Publishing requires one manual setting that no API can flip: **Settings → Pages
→ Build and deployment → Source: `GitHub Actions`**.

---

## 10. Open questions

- **ANSWERED (2026-08-17): no.** Only the fortress mitigates damage; the other
  seven render a row and take damage but confer no DR. See §4.
- Every asymmetric unit is a land unit; every air and naval unit is symmetric.
  Real rule, or an artifact of same-terrain U-vs-U pairings? **Now suspect for
  a second reason**: those air and naval rows were measured with return fire
  present (§4), so a symmetric-looking pair may be two equally attenuated
  readings rather than two equal stats.
- Does `debark` terrain take normal rather than naval damage, as the help page
  implies? Only balloons and ferriable units may appear in debark stacks — which
  makes the balloon/air crash look like a bug in exactly that special-casing.
- Do other units have a separate building-damage stat like infantry's 0.3? One
  `buildings`-style run per unit would give the whole column. Still open, and
  now the cheapest unmeasured column in the model.
- Heroes exist as a per-stack toggle and buff units. Every experiment leaves them
  off; if any reading looks inflated, check that first.
- `firestorm` appears throughout `bytro.js` but is not exposed on the S1914 form
  — likely shared code with dxter's Call of War calculator. Probably irrelevant,
  but it explains otherwise-confusing function names.
- Do `hpLeft` spans elsewhere carry tails like the building row's? The unit
  numbers all reconcile cleanly, so probably not — but they were only ever seen
  through the truncating parser. (The related question "what else is on the page
  that nothing reads?" has now been answered once, by the summary table in §4.
  It was worth asking; it may be worth asking again.)
- What are the summary table's `hours` and resource columns? `hours` was 23 for
  a stack that lost 141.67 HP and 1 for one that lost 11.33 — not proportional,
  so it is not simply HP/rate. Repair or regeneration time is the obvious guess.
  **The resource columns are no longer always zero**, which was the missing
  clue: a 10-Fighter stack losing 14.0 HP reported `iron 466, wood 1166,
  oil 933, cash 4666`. They are populated by the losing side and look like
  replacement cost, so the guess is now "what it costs to rebuild what died"
  rather than upkeep. Rows are in `results.jsonl` under `air_vs_ground`.
- **Is `patrol`'s attrition coefficient a constant?** Nine cells give
  0.360–0.427 and the scatter does not track `f`, so it is probably discrete —
  ticks, or whole units dying at tick boundaries. A count sweep at fixed `f`
  would separate those. Until then quote the range, not a mean.
- **Does `debark` behave like `patrol` or like `air`?** It is the one terrain
  still never submitted. The same question that found the patrol gap applies
  to it, and the answer costs about 6 requests.
- **Does the lighter patrol attrition apply to naval and land stacks too**, or
  only to aircraft? Patrol is offered for every terrain on the form.
- **ANSWERED (2026-08-17): a wiped stack does still deal its full damage.**
  See §4. Kept here because the reasoning matters — it was answered for free by
  a sweep aimed at something else, because `hp_scaling` happens to wipe its
  attacker in 8 of 10 rounds. Worth asking of any sweep whose readings sit on
  both sides of a threshold.
- Are the two trench curves table lookups? Output plateaus at x1.40 across
  levels 4 and 5 while the pool keeps growing, and neither curve is smooth.
  `bytro.js` has no trench logic to read them off, so it would take a full
  1..20 sweep — 20 requests for something no other result depends on.
- Why does return fire attenuate air-to-ground but not land-to-land? The
  sequential reading (ground fire resolves first, survivors deliver the attack)
  fits every number and matches how an air raid would naturally be modelled,
  but it is an interpretation of two experiments, not a measurement.
