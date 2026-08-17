# Handover: reverse-engineering dxcalc.com/s1914

Black-box recovery of the combat formulas behind dxter's *Supremacy 1914* battle
calculator. Read this before touching `dxcalc_probe.py`.

**Status: unblocked and productive.** The POST round-trips, the result semantics
are settled, the whole unit roster is measured, and fortresses are solved. The
next experiment (`buildings`) is written and tested but has never been run
against the live site.

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
do not try to route around the proxy. If it fails only on a redirect to
`www.dxcalc.com`, add `*.dxcalc.com` to the allowlist.

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
| "Trenches add to the defender's HP pool rather than reducing damage. Levels 1–3 conferred no benefit." | **Unverified.** Predates the HP-lost discovery and all three parser bugs. This has exactly the shape of the fortress null result. Re-run before citing. |

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

### Stack size factor

```
E(n) = n                                    n <= 20
E(n) = 20 + k*(60-k)/60,  k = min(n,50)-20  n > 20
```

Saturates at 35 effective units; stacking past 50 does nothing. Independently
re-confirmed at n=30: `E(30) = 28.3333`, and `28.3333 × 4.0 = 113.3` matched the
fortress control exactly.

### HP scaling

```
m(f) = 0.05 + 0.95*f
```

Fitted exactly, but **fitted through the truncating parser and never
re-verified**. Lower confidence than the rest of this section.

### Attack and defence are independent stats

Not one number plus a global defender bonus. Seven units differ between the two,
nine are symmetric. Infantry's 1.25 ratio is specific to infantry.

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
two runs an hour apart (the engine is deterministic with variance off). `maxHP`
is derived from the displayed percentage, so its precision is capped by that —
raw output shows `60.06`, `175.44`, `260.12` for what are plainly 60, 175, 260.
Two are confirmed independently by the stock form, which ships `lt` at
`525/3 = 175.0` and `ht` at `260/1 = 260.0` per unit.

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

`BLDG_TAIL_RE` reads level, remaining HP and current DR straight off the page,
so the remaining seven building types need no curve-fitting at all.

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
- **Courtesy.** This is one person's fan site, ad-supported, no API. Default
  delay is 1.5 s and should not be lowered much. Bugs found are worth mailing to
  dxcalc@gmail.com rather than just cataloguing.

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
line cost a live request against someone else's server. 43 rows: 3 `semantics`,
34 `unit_stats` (the roster twice, which is the determinism evidence), 6
`fortress`.

The `semantics` and `unit_stats` rows were once lost — the file was committed
containing only the last fortress run — and had to be reconstructed from a
session transcript. Commit the file after every sweep. Re-deriving 37 rows
means spending someone else's bandwidth twice for the same numbers.

Experiments registered: `unit_stats`, `buildings`, `size_factor`, `hp_scaling`,
`damage_land`, `damage_air`, `damage_sea`, `patrol`, `fortress`, `terrain`,
`variance`.

`damage_land`, `damage_air` and `damage_sea` predate `unit_stats` and are
largely superseded by it. They also do not record which side a reading came
from, so they will merge attack and defence coefficients into one meaningless
average. Rewrite or retire them rather than running them as they stand.

### Tests — 75 checks, no network needed

```bash
python3 test_probe_offline.py       # 36  transport, parsing, slot association
python3 test_semantics_design.py    #  9  proves the experiment can discriminate
python3 test_unit_stats.py          # 15  recovers known constants from battle output
python3 test_fortress_row.py        # 15  bldg.1 vs the bldg.0 template
```

These serve the site's courtesy budget as much as correctness: they run against
mock servers built from the real captured markup, so iteration costs dxter
nothing. `test_semantics_design.py` is worth reading as a pattern — it stands up
two servers whose physics differ only in what the span means, tunes both to
reproduce the real observation, and requires the right verdict against each. An
experiment that cannot distinguish its candidates returns a confident answer
either way.

---

## 9. Next steps, in order

1. **`--run buildings`** — 9 requests. Written and offline-tested, never run
   live. Reads DR off the page for all eight types and distinguishes "renders a
   row with DR 0%" from "renders no row at all", which a bare ratio of 1.0
   cannot. Settles whether the other seven types are combat-relevant.
2. **Re-run trenches.** The old conclusion predates the HP-lost discovery and
   all three parser bugs. `duel()` already takes a `trench` argument.
3. **Air-vs-ground matrix.** The standing question: does the Bomber deal 25.0 to
   infantry but 0.0 to heavy tanks? `unit_stats` only measured `tac` against
   `tac`. If it is 0 against all armour, that is a target-class rule; if 0
   against heavy tanks *specifically* while other armour takes damage, that is a
   bug worth reporting.
4. **Re-verify `hp_scaling`** — the one confirmed law never re-checked since the
   parser fixes.
5. **`terrain`**, then **`variance`** (60+ samples, `simulateVariance=on`) to
   characterise whether the ±10% roll is per unit or per unit type per round.

---

## 10. Open questions

- Are the eight buildings other than fortress combat-relevant at all, or purely
  cosmetic in the calculator? (Step 1 answers this.)
- Every asymmetric unit is a land unit; every air and naval unit is symmetric.
  Real rule, or an artifact of same-terrain U-vs-U pairings?
- Does `debark` terrain take normal rather than naval damage, as the help page
  implies? Only balloons and ferriable units may appear in debark stacks — which
  makes the balloon/air crash look like a bug in exactly that special-casing.
- Do other units have a separate building-damage stat like infantry's 0.3? One
  `buildings`-style run per unit would give the whole column.
- Heroes exist as a per-stack toggle and buff units. Every experiment leaves them
  off; if any reading looks inflated, check that first.
- `firestorm` appears throughout `bytro.js` but is not exposed on the S1914 form
  — likely shared code with dxter's Call of War calculator. Probably irrelevant,
  but it explains otherwise-confusing function names.
- Do `hpLeft` spans elsewhere carry tails like the building row's? The unit
  numbers all reconcile cleanly, so probably not — but they were only ever seen
  through the truncating parser.
