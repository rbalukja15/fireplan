// web/data.js — measured constants for the dxcalc/s1914 clean-room model.
//
// PURE DATA. No logic, no network, no DOM. Every constant here carries a
// provenance key into PROVENANCE, and every provenance note carries one of
// four confidence tags:
//
//   'measured'  read directly off a live response in results.jsonl
//   'derived'   arithmetic over measured readings, no free parameters
//   'assumed'   plausible, consistent with the data, NOT pinned by it
//   'unmeasured' no reading exists; the app must refuse or flag loudly
//
// A constant without one of those tags is a defect. See HANDOVER.md §0.
//
// Readings referenced below are in ../results.jsonl (168 rows at the time of
// writing; HANDOVER.md's "150 rows" is stale). Print precision of the source
// page: HP lost to 0.1 in the unit spans and to 0.01 in the summary table;
// percentages to 3 significant figures. Every pool figure is therefore a
// BRACKET (pool = lost / pct), never a point — see PROVENANCE.precision.

// ---------------------------------------------------------------------------
// UNITS
// ---------------------------------------------------------------------------
// atk / def are SAME-CLASS (diagonal) coefficients ONLY: the unit fighting its
// own kind. Attack is known to be per-target-class (`tac` is 3.0 against air
// and 30.0 against ground), so these must NOT be generalised to other targets.
// The engine treats an off-diagonal use of them as 'estimated', never measured.
//
// maxHP is an INTEGER INFERENCE from a measured bracket, not a reading. Do not
// render maxHPBracket midpoints such as 175.44 — that is a measurement of
// nothing. Where the bracket is null the quantity was never measured.

export const UNITS = {
  inf: {
    code: 'inf', label: 'Infantry', cls: 'land',
    maxHP: 20, maxHPBracket: [19.9476, 20.0526],
    atk: 4.0, def: 5.0,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  cav: {
    code: 'cav', label: 'Cavalry', cls: 'land',
    maxHP: 25, maxHPBracket: [24.9784, 25.0217],
    atk: 15.0, def: 7.5,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  ac: {
    code: 'ac', label: 'Armored Car', cls: 'land',
    maxHP: 60, maxHPBracket: [59.6965, 60.3065],
    atk: 6.0, def: 12.0,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  lart: {
    code: 'lart', label: 'Light Artillery', cls: 'land',
    maxHP: 10, maxHPBracket: [9.9890, 10.0110],
    atk: 5.0, def: 1.0,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  art: {
    code: 'art', label: 'Artillery', cls: 'land',
    maxHP: 20, maxHPBracket: [19.9738, 20.0263],
    atk: 8.0, def: 2.7,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  rrg: {
    code: 'rrg', label: 'Railgun', cls: 'land',
    maxHP: 60, maxHPBracket: [59.9685, 60.1519],
    atk: 20.0, def: 6.7,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  lt: {
    code: 'lt', label: 'Tank', cls: 'land',
    maxHP: 175, maxHPBracket: [174.9242, 175.9560],
    atk: 30.0, def: 30.0,
    provenance: { maxHP: 'UNITS.maxHP.formDefault', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  ht: {
    code: 'ht', label: 'Heavy Tank', cls: 'land',
    maxHP: 260, maxHPBracket: [259.3631, 260.8725],
    atk: 45.0, def: 45.0,
    provenance: { maxHP: 'UNITS.maxHP.formDefault', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  convoy: {
    code: 'convoy', label: 'Airplane Convoy', cls: 'land',
    maxHP: 20, maxHPBracket: [19.9700, 20.0300],
    atk: 1.0, def: 1.0,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  st: {
    code: 'st', label: 'Stormtrooper', cls: 'land',
    maxHP: 40, maxHPBracket: [39.9672, 40.0328],
    atk: 25.0, def: 6.3,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },

  bal: {
    // Measured at last, in LAND terrain. Every earlier attempt sent it in AIR
    // terrain, where the batch aborts with no error, so this read as "not one
    // quantity ever measured" for the whole project. Four requests: 10
    // balloons deal 30.00 to infantry and to heavy tanks alike, 20 infantry
    // take 30.00 back from them, and the balloons' pool reads 200.0 for ten.
    code: 'bal', label: 'Balloon', cls: 'air',
    maxHP: 20, maxHPBracket: [19.98, 20.02],
    atk: 3.0, def: 3.0,
    provenance: { maxHP: 'UNITS.balloon', atk: 'UNITS.balloon', def: 'UNITS.balloon' },
  },
  int: {
    code: 'int', label: 'Fighter', cls: 'air',
    maxHP: 60, maxHPBracket: [59.9685, 60.1519],
    atk: 20.0, def: 20.0,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  tac: {
    code: 'tac', label: 'Bomber', cls: 'air',
    maxHP: 80, maxHPBracket: [79.8802, 80.1202],
    atk: 3.0, def: 3.0,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  zep: {
    code: 'zep', label: 'Zeppelin', cls: 'air',
    maxHP: 140, maxHPBracket: [139.8462, 140.2665],
    atk: 5.0, def: 5.0,
    provenance: { maxHP: 'UNITS.maxHP', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },

  sub: {
    code: 'sub', label: 'Submarine', cls: 'sea',
    maxHP: 100, maxHPBracket: [99.8739, 100.1264],
    atk: 40.0, def: 40.0,
    provenance: { maxHP: 'UNITS.maxHP.noIndependentCheck', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  cl: {
    code: 'cl', label: 'Light Cruiser', cls: 'sea',
    maxHP: 50, maxHPBracket: [49.8728, 50.1278],
    atk: 10.0, def: 10.0,
    provenance: { maxHP: 'UNITS.maxHP.noIndependentCheck', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
  bb: {
    code: 'bb', label: 'Battleship', cls: 'sea',
    maxHP: 200, maxHPBracket: [199.4988, 200.5038],
    atk: 40.0, def: 40.0,
    provenance: { maxHP: 'UNITS.maxHP.noIndependentCheck', atk: 'UNITS.diagonal', def: 'UNITS.diagonal' },
  },
};

// ---------------------------------------------------------------------------
// CROSS-CLASS COEFFICIENTS
// ---------------------------------------------------------------------------
// The only cross-class pairing anyone has ever measured is AIR attacking
// GROUND. Both halves of it are here. Everything else is absent by design:
// see NOT_MEASURED.

// An air unit's attack against ANY ground unit. Flat across all ten ground
// targets once the post-fire evaluation of §RETURN FIRE is applied.
export const AIR_ATTACK_VS_GROUND = {
  int: 5.0,
  tac: 30.0,
  zep: 5.0,
  bal: 3.0,   // measured in land terrain; flat against infantry and heavy tanks alike
};

// A ground unit's defence output while an air stack attacks it.
// NOT the same as a ground unit attacking air, which is unmeasured.
// THE DEFENDING SIDE'S COEFFICIENT TABLE, the mirror of CLASS_ATTACK. For a
// long time this did not exist, and the consequence was not a rough number but
// no number at all: a cross-class pairing had a measured attack coefficient and
// an unmeasured defence one, so the engine withheld the whole result. Land
// attacking air -- one of the commonest things a player would type in -- came
// back blank for exactly that reason.
//
// Read off the ATTACKER's losses, which works in one request because the
// defending side is not attenuated even when it is losing badly:
//
//     attacker_lost = coef x E(defender count) x m(1)
//
// TWO attackers of each class against every defender, 102 requests, and every
// single cell agreed between them -- so the defending side has the same shape
// as the attacking one: flat within an attacker class, changing between them.
// That was a hypothesis from four cells before this sweep, not a law.
//
// Two independent checks came out of it for free. Every same-class cell
// reproduces that unit's measured defence diagonal exactly, all seventeen of
// them. And the air column reproduces all ten values of GROUND_DEFENCE_VS_AIR
// below, which was read by different attackers in a different sweep.
//
// The naval-vs-air cells are read as sea/LAND. TERRAIN_PAIR sends that pairing
// as sea/air, which aborts the batch -- the same trap that produced three
// separate "the server will not run it" findings. sea/land is also the terrain
// the attack table's air column was read in, so the two halves match.
export const CLASS_DEFENCE = {
  inf:    { land: 5.0,  air: 0.4,  naval: 2.5 },
  cav:    { land: 7.5,  air: 1.0,  naval: 4.0 },
  ac:     { land: 12.0, air: 8.0,  naval: 6.0 },
  lart:   { land: 1.0,  air: 0.2,  naval: 0.2 },
  art:    { land: 2.7,  air: 0.3,  naval: 2.7 },
  rrg:    { land: 6.7,  air: 0.7,  naval: 6.7 },
  lt:     { land: 30.0, air: 3.0,  naval: 15.0 },
  ht:     { land: 45.0, air: 4.0,  naval: 23.0 },
  convoy: { land: 1.0,  air: 0.5,  naval: 0.5 },
  st:     { land: 6.3,  air: 1.0,  naval: 0.8 },
  bal:    { land: 3.0,  air: 10.0, naval: 3.0 },
  int:    { land: 5.0,  air: 20.0, naval: 5.0 },
  tac:    { land: 30.0, air: 3.0,  naval: 30.0 },
  zep:    { land: 5.0,  air: 5.0,  naval: 5.0 },
  sub:    { land: 2.0,  air: 1.0,  naval: 40.0 },
  cl:     { land: 10.0, air: 12.5, naval: 10.0 },
  bb:     { land: 40.0, air: 6.0,  naval: 40.0 },
};

// Superseded by CLASS_DEFENCE's air column, which reproduces every one of
// these from different attackers. Kept because it is an independent reading of
// the same ten numbers, and a second source that agrees is worth more than a
// tidy file.
export const GROUND_DEFENCE_VS_AIR = {
  inf: 0.4, cav: 1.0, ac: 8.0, lart: 0.2, art: 0.3,
  rrg: 0.7, lt: 3.0, ht: 4.0, convoy: 0.5, st: 1.0,
};

// Damage a stack deals to BUILDINGS, per effective unit. Its own column:
// nothing in the unit table predicts it, and the ratio to a unit's attack
// value runs from 0.04 to 0.20. Absence from this table means "no reading
// exists" -- which now applies only to the heavy tank, whose reading is
// CENSORED: it dealt exactly 250.00 against a fortress holding 250.00, so 8.82
// is a floor and not a value.
export const BUILDING_DAMAGE_PER_EFFECTIVE_UNIT = {
  inf: 0.30, lart: 0.30, ac: 1.00, st: 1.00, art: 1.50,
  cav: 2.00, rrg: 4.00, lt: 6.00,
  // The nine that had no entry at all, because the original sweep only ever
  // flew LAND attackers. Read against a level-5 fortress with a five-unit
  // stack, which is small enough that the building survives.
  ht: 9.00,                       // was a censored FLOOR of 8.82
  convoy: 0.00, sub: 0.00,        // measured zero: these cannot hurt a building
  bal: 0.50,
  // The three fliers are read on an ATTENUATED path, so the raw figures --
  // 0.96, 5.80, 29.44 -- are the post-fire law applied to building damage as
  // well. Corrected by the same factor the unit damage uses, they are round:
  // 1.0045, 5.9995, 30.0102.
  int: 1.00, tac: 6.00, zep: 30.00,
  cl: 2.00, bb: 8.00,
};

// A UNIT'S ATTACK COEFFICIENT AGAINST EACH TARGET CLASS. This is the whole
// matrix, and it is 16 x 3 rather than 17 x 17 because a unit's coefficient is
// FLAT across targets within a class -- the naval and air matrices reproduce
// their diagonals exactly, and eight single-type land duels off the diagonal
// are exact too. Only the target's CLASS changes it.
//
// Air-attacking-land cells are corrected for the post-fire attenuation before
// being quoted; every other cell is read raw. Naval attackers have no air
// column: the server will not run that pairing.
//
// The land column reproduces UNITS[].atk, which is how we know the two agree.
// HOW WELL EACH COLUMN OF CLASS_ATTACK IS CORROBORATED, by (attacker class,
// target class). This is a fact about the RECORD, not about the game, and it
// lives here so nothing has to infer it from a unit's class at the call site.
//
//   land x land   the diagonal from unit_stats (four byte-identical runs),
//                 eight off-diagonal duels, and the nine-attacker allocation
//                 sweep -- three independent corroborations.
//   air  x land   thirty cells: three fliers against all ten ground units,
//                 each ground value confirmed by three independent attackers.
//   air  x air    the diagonal, flown four times.
//   naval x naval the diagonal, flown four times.
//
// Every OTHER cell used to rest on a single reading from the class sweep, and
// a single reading is not a corroboration. A second target was then sent for
// every air and naval column -- a bomber where the first sweep used a fighter,
// a cruiser where it used a battleship -- and 25 of the 26 readable cells came
// back identical to four decimal places. So the whole matrix is corroborated
// now and every pair is listed here.
//
// The twenty-sixth is why the sweep was worth 37 requests. The BALLOON read
// 10.0 against a bomber where its row said 3.0: that row was one land reading
// copied across three columns on the assumption the row was flat. It is not.
//
// A blanket "air attackers are estimated" was tried before any of this and was
// wrong in both directions at once: it understated the fliers' thirty-cell
// land column and their four-run diagonal, and said nothing at all about the
// single-cell columns that genuinely did rest on one reading each.
export const CLASS_ATTACK_CORROBORATED = [
  ['land', 'land'], ['land', 'air'], ['land', 'naval'],
  ['air', 'land'], ['air', 'air'], ['air', 'naval'],
  ['naval', 'land'], ['naval', 'air'], ['naval', 'naval'],
];

export const CLASS_ATTACK = {
  inf:  { land: 4.0,  air: 0.3,  naval: 2.0 },
  cav:  { land: 15.0, air: 2.0,  naval: 8.0 },
  ac:   { land: 6.0,  air: 4.0,  naval: 3.0 },
  lart: { land: 5.0,  air: 1.0,  naval: 1.0 },
  art:  { land: 8.0,  air: 1.0,  naval: 8.0 },
  rrg:  { land: 20.0, air: 2.0,  naval: 20.0 },
  lt:   { land: 30.0, air: 3.0,  naval: 15.0 },
  ht:   { land: 45.0, air: 4.0,  naval: 23.0 },
  convoy: { land: 1.0, air: 0.5, naval: 0.5 },
  st:   { land: 25.0, air: 4.0,  naval: 3.0 },
  // The balloon's row used to read 3.0 in all three columns. Only the land
  // figure was ever measured -- ten balloons deal 30.00 to twenty infantry and
  // 30.00 to twenty heavy tanks -- and the other two were filled by assuming
  // the row was flat, which is precisely what a single cell cannot tell you.
  // Against air it is 10.0, read from a fighter and a bomber which agreed, and
  // that is more than triple the number it replaced. Land and naval are
  // confirmed at 3.0 by two targets each.
  bal:  { land: 3.0,  air: 10.0, naval: 3.0 },
  // The land column for fliers comes from AIR_ATTACK_VS_GROUND, which was
  // fitted over THIRTY cells; the single corrected cells here read 5.01,
  // 30.03 and 5.00, so they agree, and the better-measured figure wins.
  // The fliers' naval column read 3.6 / 23.64 / 4.4 until a second target was
  // sent. Those were the raw per-effective-unit figures against a battleship,
  // and air attacking a SURFACE target is a post-fire law -- the stack fires
  // with what survives the round, not with what it started with. Applying the
  // law the engine already implements, both targets agree to four decimals:
  //
  //     int   vs bb 4.9998   vs cl 4.9997
  //     tac   vs bb 30.0003  vs cl 29.9999
  //     zep   vs bb 4.9998   vs cl 4.9998
  //
  // and each lands exactly on that flier's LAND column. An air unit deals the
  // same to a ship as to a tank; only the attenuation differed, and mistaking
  // attenuation for a coefficient is what produced three numbers that looked
  // like measurements and were arithmetic.
  int:  { land: 5.0,  air: 20.0, naval: 5.0 },
  tac:  { land: 30.0, air: 3.0,  naval: 30.0 },
  zep:  { land: 5.0,  air: 5.0,  naval: 5.0 },
  // The air column for the ships was blank because a naval stack against an
  // air one was recorded as something the server refuses. It does not: sea/air
  // aborts the batch and sea/land runs, which is the fourth time a terrain
  // pair was mistaken for a rule about the game. Read against fighters on
  // land, the same terrain the attack table's air column uses everywhere else.
  sub:  { land: 2.0,  air: 1.0,  naval: 40.0 },
  cl:   { land: 10.0, air: 12.5, naval: 10.0 },
  bb:   { land: 40.0, air: 6.0,  naval: 40.0 },
};

// Which terrain pair the server will actually run, per (attacker class, target
// class). Found the hard way: a land attacker against an AIR-terrain defender
// aborts the batch with NO error at all, which is why "ground attacking air"
// was recorded as never submitted when it had only ever been submitted wrongly.
// In LAND terrain the same battle runs and infantry deal 0.30 to a fighter.
export const TERRAIN_PAIR = {
  'land/land': ['land', 'land'], 'land/air': ['land', 'land'],
  'land/naval': ['land', 'sea'],
  'air/land': ['air', 'land'], 'air/air': ['air', 'air'],
  'air/naval': ['air', 'sea'],
  'naval/land': ['sea', 'land'], 'naval/naval': ['sea', 'sea'],
  // naval/air: the server will not run it.
};

// ---------------------------------------------------------------------------
// BUILDINGS
// ---------------------------------------------------------------------------
// maxLevel === null means the server's cap was never established (the sweep
// asked for 3, was not rejected, and never probed higher). The form's own
// select offers 1-5 for every type, which is a UI cap, not a server cap.
// hpPerLevel === null means HP does not divide evenly by the levels tested.

export const BUILDINGS = {
  fortress: {
    code: 'fortress', label: 'Fortress',
    maxLevel: 5, hpPerLevel: 50, mitigates: true,
    poolAtLevel: { 1: 50, 2: 100, 3: 150, 4: 200, 5: 250 },
    provenance: { maxLevel: 'BUILDINGS.maxLevel.server', hp: 'BUILDINGS.fortressHP', mitigates: 'FORTRESS.dr' },
  },
  recruiting: {
    code: 'recruiting', label: 'Recruiting Office',
    maxLevel: 1, hpPerLevel: 5, mitigates: false,
    poolAtLevel: { 1: 5 },
    provenance: { maxLevel: 'BUILDINGS.levels', hp: 'BUILDINGS.levels', mitigates: 'BUILDINGS.inert' },
  },
  railway: {
    code: 'railway', label: 'Railway',
    maxLevel: 1, hpPerLevel: 60, mitigates: false,
    poolAtLevel: { 1: 60 },
    provenance: { maxLevel: 'BUILDINGS.levels', hp: 'BUILDINGS.levels', mitigates: 'BUILDINGS.inert' },
  },
  workshop: {
    code: 'workshop', label: 'Workshop',
    maxLevel: 3, hpPerLevel: null, mitigates: false,
    poolAtLevel: { 1: 5, 2: 15, 3: 35 },
    provenance: { maxLevel: 'BUILDINGS.levels', hp: 'BUILDINGS.levels', mitigates: 'BUILDINGS.inert' },
  },
  factory: {
    code: 'factory', label: 'Factory',
    maxLevel: 4, hpPerLevel: 40, mitigates: false,
    poolAtLevel: { 1: 40, 2: 80, 3: 120, 4: 160 },
    provenance: { maxLevel: 'BUILDINGS.levels', hp: 'BUILDINGS.levels', mitigates: 'BUILDINGS.inert' },
  },
  barracks: {
    code: 'barracks', label: 'Barracks',
    maxLevel: 2, hpPerLevel: 40, mitigates: false,
    poolAtLevel: { 1: 40, 2: 80 },
    provenance: { maxLevel: 'BUILDINGS.levels', hp: 'BUILDINGS.levels', mitigates: 'BUILDINGS.inert' },
  },
  aerodrome: {
    code: 'aerodrome', label: 'Aerodrome',
    maxLevel: 1, hpPerLevel: 60, mitigates: false,
    poolAtLevel: { 1: 60 },
    provenance: { maxLevel: 'BUILDINGS.levels', hp: 'BUILDINGS.levels', mitigates: 'BUILDINGS.inert' },
  },
  harbor: {
    code: 'harbor', label: 'Harbor',
    maxLevel: 1, hpPerLevel: 60, mitigates: false,
    poolAtLevel: { 1: 60 },
    provenance: { maxLevel: 'BUILDINGS.levels', hp: 'BUILDINGS.levels', mitigates: 'BUILDINGS.inert' },
  },
};

// ---------------------------------------------------------------------------
// FORTRESS
// ---------------------------------------------------------------------------
// THE CURVE HAS TWO SEGMENTS, and for most of this project it had one.
//
//   hp <  10   DR = 0            the fortress confers NOTHING
//   hp <= 50   DR = 0.05 + 0.005 x hp
//   hp >  50   DR = 0.15 + 0.003 x hp,  capped at 0.90
//
// The two lines meet exactly at 50 HP and 30%, so the join is invisible from
// above and the old single formula was right for every full fortress at every
// level: 0.30, 0.45, 0.60, 0.75, 0.90 at levels 1-5. It is wrong for anything
// under 50, by up to eight points.
//
// A pool below 50 only happens to a fortress that is being ground down, and
// every fortress this project ever SUBMITTED was full. So the second segment
// showed up nowhere except in the last rounds of a long battle -- which is
// precisely where the engine's numbers went wrong, and it was chased for two
// sweeps as a mysterious "late-round output drift" in the attacker.
//
// The site had been printing the answer on every fortress row since the first
// request. dr_before and dr_after were parsed, recorded and never read: 73
// distinct (HP, DR) pairs were on disk before a single request was spent on
// this, and they fit the segment above 50 for all 58 points and refuse the
// other 13. The twelve requests that followed were only to pin the floor.
export const FORTRESS = {
  drSlopePer50HP: 0.15,   // DR = 0.15 * (fortressHP / 50 + 1), hp >= 50 only
  drOffset: 0.15,         // the "+1" term: any fortress at all costs 15%
  hpPerLevel: 50,
  maxMeasuredLevel: 5,
  // The low segment, measured directly off the site's own DR column.
  lowSegmentBelowHP: 50,
  lowIntercept: 0.05,
  lowSlopePerHP: 0.005,
  // Below this the row carries no "DR:" clause at all -- the same signature a
  // building that confers nothing gives. 9.5 HP prints none, 10 prints 10.0%,
  // so the cut is at 10 and the drop is a step, not a taper.
  inertBelowHP: 10,
  maxDR: 0.90,
  provenance: { dr: 'FORTRESS.dr', lowSegment: 'FORTRESS.dr.lowSegment',
    hp: 'BUILDINGS.fortressHP' },
};

// ---------------------------------------------------------------------------
// TRENCHES
// ---------------------------------------------------------------------------
// Two independent effects on two different schedules, from ten rows of
// 10 infantry vs 10 infantry. ONLY these nine levels were ever sampled;
// levels 6-9, 11-14 and 16-19 (12 of 21) have never been submitted.
//
// TRENCH_POOL enlarges the stack's HP pool AND its per-unit max HP (which is
// what changes the death count). It applies while attacking as well as
// defending. TRENCH_OUTPUT raises the DEFENDER's damage output only — an
// attacker's trench 20 left the defender's loss at exactly 40.0.

export const TRENCH_POOL = {
  0: 1.00, 1: 1.00, 2: 1.00, 3: 1.00, 4: 1.15, 5: 1.20,
  6: 1.20, 7: 1.22, 8: 1.22, 9: 1.24, 10: 1.24, 11: 1.26, 12: 1.26,
  13: 1.28, 14: 1.28, 15: 1.30, 16: 1.30, 17: 1.32, 18: 1.32,
  19: 1.35, 20: 1.35,
};

// The brackets these point values came from. pool = lost / pct, and pct is
// printed to 3 significant figures, so each is an interval, not a reading.
// Note level 10: [1.2382, 1.2463] EXCLUDES 1.25. Do not "tidy" it to 1.25 —
// the measurement forbids it.
export const TRENCH_POOL_BRACKET = {
  0: [0.9974, 1.0026], 1: [0.9974, 1.0026], 2: [0.9974, 1.0026], 3: [0.9974, 1.0026],
  4: [1.1460, 1.1529], 5: [1.1939, 1.2014],
  // Level 10 re-read on a 200-unit stack: [1.23977, 1.24162], intersected with
  // the 50-unit and 10-unit readings to [1.23977, 1.24047]. Still excludes the
  // tidy 1.25, and now pins the value at 1.240.
  10: [1.23977, 1.24047],
  15: [1.2943, 1.3031], 20: [1.3466, 1.3561],
};

// All 21 levels are now measured. Both curves are STAIRCASES, stepping in
// pairs rather than sliding: output holds at 1.45 for two levels, then 1.50
// for two, and so on. That is why interpolating them was flagged as risky
// before the gaps were filled.
export const TRENCH_OUTPUT = {
  0: 1.00, 1: 1.25, 2: 1.30, 3: 1.35, 4: 1.40, 5: 1.40,
  6: 1.45, 7: 1.45, 8: 1.50, 9: 1.50, 10: 1.54, 11: 1.54, 12: 1.58,
  13: 1.58, 14: 1.62, 15: 1.62, 16: 1.66, 17: 1.66, 18: 1.70, 19: 1.70,
  20: 1.75,
};

// TRENCHES ARE INFANTRY-ONLY. Measured with 200 attacking infantry so nothing
// is censored: heavy tanks, artillery and cavalry read the IDENTICAL output
// and the IDENTICAL pool at trench 0 and at trench 10, while infantry go from
// 50.00 to 77.00 output and 200.0 to 247.8 pool. The first attempt at this was
// censored - the attacker was wiped at 400.0 of 400.0 - and said nothing.
export const TRENCH_APPLIES_TO = ['inf'];

export const TRENCH_SAMPLED_LEVELS = [
  0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
];
export const TRENCH_MAX_LEVEL = 20;

// ---------------------------------------------------------------------------
// FORM INPUT DOMAINS (read off the committed form capture, last_response.html)
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// PATROL
// ---------------------------------------------------------------------------
// An air stack can be flown as a direct STRIKE (terrain=air) or on PATROL
// (terrain=patrol). Both were measured, 18 rows, and they are different
// attacks. Two findings, with very different confidence:
//
//   SOLID -- maxRounds. Patrol damage is proportional to maxRounds; a direct
//   strike IGNORES maxRounds entirely. Four rungs each (0.25/0.5/0.75/1), and
//   the strike returns byte-identical damage at all four: 30.03 per unit every
//   time. This one is not in doubt.
//
//   SOFT -- attrition. A stack's output is reduced by its own losses, but a
//   strike pays the full fraction while patrol pays only a part of it:
//
//       dealt = coefficient * E(survivors of c * own losses) * m(f of the rest)
//
//   c = 1.000 for a strike (that is the return-fire law, fitted to 0.005 HP
//   across 30 cells) and c = 0.3772 for patrol across 33. BOTH SIDES pay it,
//   so each side's losses are the other's output and the pair is solved as a
//   FIXED POINT rather than in sequence.
//
//   This used to read "c = 0.36..0.43, it does NOT close to a single value,
//   and the scatter does not track f, so the real mechanism is probably
//   discrete". The scatter was the superseded survivor rule -- count minus
//   floor(cumulative damage / max HP) -- and refitting the same nine cells
//   with the corrected one collapses the range by a factor of ten. The app
//   must still show the range and must never present a patrol number as
//   measured, because 0.3772 is a fit and not a printed constant.
//
// The base attack stat is UNCHANGED between the two modes: every attacker's
// air-to-ground value comes back through patrol (int 5.006/5.024/5.008,
// tac 30.026/30.000/30.000, zep 5.003/5.002/5.015). So patrol is the same
// weapon delivered differently, not a different weapon.
export const PATROL = {
  // Fitted on BOTH channels as a fixed point -- each side fires with what
  // survives this fraction of its own losses, and each side's losses are the
  // other's output. Worst error 0.47% over 33 cells.
  attritionCoefficient: 0.3772,
  // A tenth as wide as the band this app shipped. The old 0.360-0.427 was an
  // artifact of the superseded survivor rule, not evidence of discreteness.
  attritionRange: [0.3750, 0.3810],
  cellsMeasured: 33,
  roundsScale: true,                  // damage is proportional to maxRounds
  strikeIgnoresRounds: true,          // a direct strike delivers once, always
  // Measured advantage of patrol over a direct strike at maxRounds=1: the RAW
  // ratio of defender HP lost, which is what a player actually sees. Ordered by
  // how hard the target shoots back, which is the whole mechanism.
  observedAdvantage: {
    int: { inf: 1.0143, ht: 1.097, ac: 1.2294 },
    tac: { inf: 1.0106, ht: 1.0719, ac: 1.1646 },
    zep: { inf: 1.0059, ht: 1.0357, ac: 1.0826 },
  },
  provenance: 'PATROL.attrition',
};

// ---------------------------------------------------------------------------
// STACK COMPOSITION
// ---------------------------------------------------------------------------
// A stack is a MIXTURE of distinct unit types, and it saturates as a whole.
//
//     effective_i = E(units through row i) - E(units before row i)
//     output      = sum over rows of  coefficient_i * effective_i
//
// with rows taken STRONGEST FIRST, ordered by the damage coefficient the side
// is actually using -- the defence column when defending, the attack column
// when attacking. Not the order they were submitted: the swapped pair returns
// the identical figure, which is how we know the server sorts before it
// computes.
//
// THIS FILE SAID "ROSTER ORDER" UNTIL 2026-08-19, AND THE APP COMPUTED IT.
// The claim came from four mixtures that were all infantry + artillery, where
// roster order and strongest-first are the same ordering -- infantry both
// precedes artillery in the roster and out-damages it. A nine-type ladder
// separated them and roster order was wrong by 52.6%. See STACK.saturation.
//
// The consequence a player actually feels is unchanged in shape and different
// in who it hits: the WEAKEST type in a stack draws from the SATURATED TAIL.
// Forty artillery beside ten infantry get E(50)-E(10) = 25 effective units
// against E(40) = 33.3 alone, and no reordering can recover it -- but light
// artillery beside heavy tanks is squeezed because it is weak, not because of
// where the roster happens to list it.
export const ROSTER_ORDER = [
  'inf', 'cav', 'ac', 'lart', 'art', 'rrg', 'lt', 'ht', 'convoy', 'st',
  'bal', 'int', 'tac', 'zep',
  'sub', 'cl', 'bb',
];

// The server refuses a repeated unit type in one stack:
//     "oops: The same unit can't be specified twice in same stack."
// So a stack is a SET of types, each with a count. This is a hard constraint
// on the input model, not a validation nicety.
// bytro.js declares maxUnits = 15. The 8 this app shipped with was inherited
// from duel()'s arbitrary row-blanking range and was never a fact about the
// game -- a land stack accepts 9 types, which 8 could not express.
export const MAX_UNIT_ROWS = 15;
export const DUPLICATE_UNITS_ALLOWED = false;

// WHICH TYPES MAY SHARE A STACK. Measured 2026-08-17, 4 requests, every answer
// stated outright by the server:
//
//   "Can't have ground and air units in same stack."
//   "Convoys don't stack with land units."
//   "Can't have Airplane Convoy in the air."
//
// So classes never mix, and the Airplane Convoy -- which this project's roster
// files under land -- stacks with nothing at all. It is a class of one. The
// practical row cap is therefore the size of the group, not maxUnits:
//   land 9, air 4, sea 3, convoy 1.
export const STACK_GROUP = {
  inf: 'land', cav: 'land', ac: 'land', lart: 'land', art: 'land',
  rrg: 'land', lt: 'land', ht: 'land', st: 'land',
  convoy: 'convoy',
  bal: 'air', int: 'air', tac: 'air', zep: 'air',
  sub: 'sea', cl: 'sea', bb: 'sea',
};
export const STACK_GROUP_LABEL = {
  land: 'land', convoy: 'Airplane Convoy (stacks with nothing)',
  air: 'air', sea: 'naval',
};

// Incoming damage is split across rows in proportion to (attack value x unit
// count) -- each row's raw offensive weight, ignoring saturation entirely.
// Exact across all four measured mixtures, including both asymmetric ones,
// where allocation by pool, by count, or by attack-value-alone all fail badly:
//
//   40 inf + 10 art, 80.0 incoming -> observed 53.3 / 26.7
//       by pool           64.0 / 16.0     off by 10.7
//       by attack alone   26.7 / 53.3     off by 26.6   (inverted!)
//       by attack x count 53.3 / 26.7     exact
export const DAMAGE_ALLOCATION = 'attack_times_count';

// ---------------------------------------------------------------------------
// HEROES
// ---------------------------------------------------------------------------
// A hero is a UNIT PLUS A BUFF, at most one per stack:
//
//     output = A * heroEffective  +  unit_coef * M * unitEffective
//
// A is the hero's own attack, fighting as one unit; M multiplies what the
// stack deals -- but only for the unit types that hero actually buffs. WHERE
// it sits decides both effective counts, because a stack saturates
// cumulatively, strongest first (see STACK.saturation).
//
// A DOES NOT MOVE WITH LEVEL -- verified across levels 1, 2, 4, 5, 9, 10, 11
// and 15, always the same figure.
//
// M IS NOT A WHOLE-STACK MULTIPLIER, and an earlier version of this file said
// it was. dxcalc's own help page states "the hero buffs will be applied to the
// APPROPRIATE units in the stack", and every hero reading here defends with
// INFANTRY. So an M of 1.00 below means "does not buff infantry" -- it does
// NOT mean the hero buffs nobody, and the app must not say that it does.
//
// Measured proof: Fiero "Marco" Martello reads M = 1.00 against infantry, yet
// a stack of ten Tanks goes from a pool of 1750.5 without him to 1961.7 with
// him -- x1.121. His buff is real, it lands on a unit type never tested, and
// it is on the HP POOL rather than on output, which is a channel this model
// does not represent at all.
//
// ALL NINE LAND TYPES HAVE BEEN SCREENED, one request per hero, against
// an attacker big enough to survive the answer. `buffs` below is therefore
// per unit type and no longer infantry-only:
//
//     joffre_home   infantry x1.30 AND armoured car x1.30
//     alvin         stormtrooper x1.40
//     kangal        armoured car x1.20
//     hank          infantry x1.09
//
// The other twelve raised a nine-type stack by exactly their own attack value
// and nothing more, so they buff no land type's OUTPUT at all. That is now a
// measurement rather than an absence of one -- down to a floor of 0.2 HP,
// which on the weakest row in the screen is a 10% buff; anything smaller
// would still be hiding.
//
// EVERY BUFF MOVES WITH LEVEL, in both channels, so every curve below is
// stored as MEASURED POINTS and interpolated between them -- never fitted. pershing's
// infantry HP curve is why: it climbs to 1.70 by level 5, DROPS to 1.10 at
// level 6 and climbs again to 1.25 by level 20. Reproduced at three units as
// well as two, and confirmed by an independently derived pool.
//
// A BUFF ALSO HAS A SIDE. alvin's and hank's apply attacking and defending
// alike; joffre_home's and kangal's measure exactly 0.00 on an attacking
// stack, so they are defence-only.
//
// A SECOND CHANNEL raises a unit type's MAX HP. Read off the server's own
// refusal -- "Max hp for 2 Infantry is 47.200000" -- so these are exact
// rather than derived from a 3-significant-figure percentage.
//
// Every value below is a MEASUREMENT, decomposed from two stack sizes so that
// A and M are separated rather than confounded. `maxLevel` is the server's own
// refusal ("Max level is 10"), not the 1..20 the dropdown offers for everyone.

// EMBARKED LAND UNITS. In sea or debark terrain a land unit's own attack and
// defence are REPLACED by a flat 1.0 -- not scaled. Infantry (4.0/5.0) and
// cavalry (15.0/7.5) deal the identical 20 and 10 against the same target,
// which no scaling of two different stats can produce. An embarked land unit
// fights exactly as well as a convoy, which is 1.0/1.0 in the unit table.
// Infantry are refused in air terrain outright.
// Applies to any NON-NAVAL unit, not just land ones: ten fighters in sea
// terrain deal exactly 1.0 x E(20) = 20.00, the same flat figure infantry and
// cavalry give. A battleship in sea terrain deals its full 40. Debark refuses
// a battleship outright ("Only balloons and ferriable units...").
export const EMBARKED_COEF = 1.0;

// EMBARKATION IS A CLASS CHANGE, not a pair of stat overrides. A non-naval
// unit in sea or debark terrain:
//   attacks at a flat 1.0                (EMBARKED_COEF, measured earlier)
//   holds a flat 10 HP, whatever it is   (this constant)
//   is hit on the attacker's NAVAL column
//
// The HP is read straight off the pools and is the same for everything: 20
// infantry, 20 cavalry, 20 heavy tanks, 20 fighters and 20 bombers all report
// a pool of exactly 200.0 in sea terrain and in debark terrain, against 398.9,
// 500.0, 5194.8, 1200.0 and 1599.1 on land. Naval units keep their own -- a
// cruiser reads 50 and a battleship 200.
//
// The class change is measured six ways for six, using the three attackers
// whose land and naval columns differ: cavalry deals 8.0 per effective unit to
// embarked infantry AND to embarked fighters (land column 15.0, naval 8.0),
// light artillery 1.0 (against 5.0), a heavy tank 23.0 (against 45.0). Every
// one lands on the naval column exactly.
//
// This is also what censored the naval-vs-air reading that stood for a week as
// "30.0 per effective unit". It was a 100% wipe: lost exactly equalled a pool
// six times smaller than the unit table implies. Sized properly the cell reads
// 40.0, which is the battleship's plain attack value.
export const EMBARKED_MAXHP = 10;

// An embarked unit's own coefficients, in BOTH directions. The flat 1.0 that
// EMBARKED_COEF records is the land column and only the land column: against
// AIR the figure is 0.5, measured both ways round.
//
//   attacking  40 embarked infantry deal 1.0 per effective unit to infantry,
//              0.5 to fighters, 1.0 to a battleship
//   defending  40 embarked fighters answer infantry at 1.0, 100 embarked
//              infantry answer a fighter at 0.5 and a battleship at 1.0
//
// The obvious guess was that an embarked unit simply IS a convoy -- that is
// where the flat 1.0 came from, and the convoy's land and air columns are
// exactly 1.0 and 0.5. It is wrong in the third cell: a convoy reads 0.5
// against naval targets and an embarked unit reads 1.0. Two cells out of three
// agreeing is what a wrong law looks like from the inside, which is why the
// naval cell was sent rather than inferred.
export const EMBARKED_ATTACK = { land: 1.0, air: 0.5, naval: 1.0 };
export const EMBARKED_DEFENCE = { land: 1.0, air: 0.5, naval: 1.0 };
export const EMBARKED_TERRAIN = ['sea', 'debark'];

// DEBARK IS NOT SEA, and the difference is asymmetric. A unit in debark
// attacks and defends on the embarked column and holds the flat 10 HP, exactly
// as at sea -- 40 embarked infantry in debark deal 0.9999 to infantry, 0.5001
// to fighters and 0.9999 to a battleship, which is the sea column to four
// decimals. But a TARGET in debark is hit on the attacker's LAND column, not
// its naval one:
//
//              land col   naval col   at sea   in debark
//   cavalry       15.0        8.0       8.00     15.00
//   light art      5.0        1.0       1.00      5.00
//   heavy tank    45.0       23.0      23.00     45.00
//
// The two terrains were treated as one because they sit in the same list, and
// only the HP half had ever been measured in debark. For a light artillery
// attacker that assumption was 5x wrong.
export const EMBARKED_CLASS_CHANGE_TERRAIN = ['sea'];

// RANGE IS A BINARY GATE, measured by moving one side's position while the
// other stays at 0. Inside range the figure is identical to zero distance --
// there is no falloff -- and outside it the server returns no result rows at
// all. Every entry below was found by BISECTION: the largest distance that
// fights and the smallest that does not, one apart.
//
// This table used to read { art: 50, rrg: 150, inf: 1 } and the infantry
// figure was wrong. It came from a three-value ladder (0, 1, 25) which never
// bisected, so 1 was the largest distance anyone had TRIED, not the largest
// that works. Infantry reach 5, like every other melee unit in the roster.
// A number that only looks measured is worse than a gap: a gap is flagged
// downstream and a wrong number is not.
//
// cl 40 and bb 75 match the in-game help page exactly, which is a check on
// the method rather than a source for it. lart 30 is on no help page.
export const UNIT_RANGE = {
  inf: 5, cav: 5, ac: 5, lart: 30, art: 50, rrg: 150, lt: 5, ht: 5,
  convoy: 5, st: 5, bal: 5, int: 5, tac: 5, zep: 5, sub: 5, cl: 40, bb: 75,
};

// A BOMBARDED DEFENDER DOES NOT SHOOT BACK. Beyond 5 km the attacker takes
// exactly zero while still dealing its full figure: light artillery at 6, 7
// and 8 km deals 100.00 and loses nothing, where at 4 and 5 km it deals the
// same 100.00 and loses 20.00.
//
// The cut-off is a property of the DISTANCE, not of the defender. Three
// defenders that could easily shoot back -- lart reaching 30, cl 40, bb 75 --
// are all silent at 8 km, and a mixed inf+lart defender at 6 km is silent too.
// Nor does a long-reaching defender ever start a fight: infantry attacking
// light artillery from 20 km produces no battle at all, though the artillery
// could reach twenty kilometres past its attacker.
export const MELEE_RANGE = 5;

// simulateVariance: ONE uniform +/-10% roll per side per round, NOT per unit.
// 60 samples give sd 5.285 where a single roll predicts 5.774 and a per-unit
// roll would predict 1.291. The whole stack moves together, so a big stack
// cannot average its luck away. Observed range [0.9025, 1.0992] of the
// variance-off figure.
export const VARIANCE_BAND = { lo: 0.90, hi: 1.10, rolls: 'one per side per round' };

// Damage to a BUILDING, per effective attacking unit. Its own column: nothing
// in the unit table predicts it, and the ratio to the unit's attack value
// ranges from 0.04 to 0.20. ht is a FLOOR, not a value -- it dealt exactly
// 250.00 against a fortress holding 250.00, so the reading is censored.
// The censored one, kept separate so it can never be mistaken for a value.
// EMPTY NOW. The heavy tank was the only censored reading -- it dealt exactly
// 250.00 against a fortress holding 250.00, so 8.82 was a lower bound and not
// a value. Read again with five tanks instead, which the fortress survives, it
// is 9.00. Kept as an exported constant rather than deleted so that any future
// censored reading has an obvious place to go, and so the engine's withholding
// path stays exercised by the tests.
export const BUILDING_DAMAGE_FLOOR = {};

// The fortress caps at level 5 -- the server refuses 6 and says so. That is
// why the DR formula's value at level 6 (1.05, more than total immunity) never
// arises. A fortress on the ATTACKING side works identically: 30% at level 1
// either way.
export const FORTRESS_MAX_LEVEL = 5;

export const HEROES = {
  //  atkDefending / atkAttacking : a hero has TWO attack columns, exactly as a
  //    unit does. Thirteen of sixteen differ, pershing by a factor of eight.
  //    Every "A" measured before 2026-08-19 is the DEFENDING one.
  //  pool : the hero's own HP, read off its result row. Does NOT move with
  //    level -- joffre_home is identical at 1, 2, 4, 5, 9, 10, 11 and 15.
  //  buffs : output multiplier, PER UNIT TYPE, with the side it acts on.
  //    'both' applies attacking and defending; 'defence' measured at exactly
  //    0.00 attacking. Curves are measured points, never fitted.
  //  hpBuffs : a separate channel that raises a unit type's MAX HP. Read off
  //    the server's own refusal ("Max hp for 2 Infantry is 47.200000"), so
  //    these are exact rather than bracketed.
  kangal:       { label: 'Orhan “Kangal” Demir', atkDefending: 20.0, atkAttacking: 10.0,
                  atkByTargetClass: { land: 10, air: 5, naval: 3 },
                  defByAttackerClass: { land: 20, air: 10, naval: 6 },
                  pool: 90, sits: 'first', maxLevel: 10,
                  buffs: { ac: { channel: 'defence', curve: { 1: 1.08, 2: 1.10, 3: 1.12, 4: 1.12, 5: 1.13, 6: 1.14, 7: 1.16, 8: 1.18, 9: 1.20, 10: 1.20 } } } },
  joffre:       { label: 'Joseph Joffre (Non Homeland)', atkDefending: 16.0, atkAttacking: 4.0,
                  atkByTargetClass: { land: 4, air: 3, naval: 2 },
                  defByAttackerClass: { land: 16, air: 12, naval: 8 },
                  pool: 120, sits: 'first', maxLevel: 15 },
  joffre_home:  { label: 'Joseph Joffre (Homeland)', atkDefending: 16.0, atkAttacking: 4.0,
                  atkByTargetClass: { land: 4, air: 3, naval: 2 },
                  defByAttackerClass: { land: 16, air: 12, naval: 8 },
                  pool: 120, sits: 'first', maxLevel: 15,
                  buffs: { inf: { channel: 'defence', curve: { 1: 1.10, 2: 1.15, 3: 1.15, 4: 1.16, 5: 1.20, 6: 1.22, 7: 1.24, 8: 1.26, 9: 1.28, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40 } },
                           ac:  { channel: 'defence', curve: { 1: 1.10, 2: 1.15, 3: 1.15, 4: 1.16, 5: 1.20, 6: 1.22, 7: 1.24, 8: 1.26, 9: 1.28, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40 } } },
                  hpBuffs: { ac: { 1: 1.00, 2: 1.00, 3: 1.05, 4: 1.05, 5: 1.09, 6: 1.09, 7: 1.13, 8: 1.13, 9: 1.17, 10: 1.17, 11: 1.21, 12: 1.21, 13: 1.25, 14: 1.25, 15: 1.30 } } },
  // atkAttacking was 24.6 and is 15.0. The old figure was an own attack and
  // an ATTACK-ONLY light-tank buff added together, read off a stack the hero
  // buffs. Same defect in allen, georg and pershing; see HEROES.attackOnly.
  marco:        { label: 'Fiero “Marco” Martello', atkDefending: 15.0, atkAttacking: 15.0,
                  atkByTargetClass: { land: 15, air: 2, naval: 5 },
                  defByAttackerClass: { land: 15, air: 2, naval: 5 },
                  pool: 60, sits: 'first', maxLevel: 10,
                  buffs: { lt: { channel: 'attack', curve: { 1: 1.05, 2: 1.08, 3: 1.08, 4: 1.09, 5: 1.10, 6: 1.11, 7: 1.12, 8: 1.13, 9: 1.14, 10: 1.16 } } },
                  hpBuffs: { lt: { 1: 1.00, 2: 1.00, 3: 1.05, 4: 1.06, 5: 1.07, 6: 1.08, 7: 1.09, 8: 1.10, 9: 1.11, 10: 1.12 } } },
  allen:        { label: 'Viscount Allenby', atkDefending: 10.0, atkAttacking: 20.0,
                  atkByTargetClass: { land: 20, air: 3, naval: 10 },
                  defByAttackerClass: { land: 10, air: 1.5, naval: 5 },
                  pool: 50, sits: 'first', maxLevel: 15,
                  buffs: { cav: { channel: 'attack', curve: { 1: 1.10, 2: 1.15, 3: 1.20, 4: 1.20, 5: 1.24, 6: 1.24, 7: 1.27, 8: 1.27, 9: 1.30, 10: 1.32, 11: 1.34, 12: 1.36, 13: 1.38, 14: 1.40, 15: 1.40 } } } },
  larab:        { label: 'Lawrence of Arabia', atkDefending: 10.0, atkAttacking: 45.0,
                  atkByTargetClass: { land: 45, air: 4.5, naval: 11.25 },
                  defByAttackerClass: { land: 10, air: 1, naval: 2.5 },
                  pool: 75, sits: 'first', maxLevel: 20 },
  alvin:        { label: 'Alvin C. York', atkDefending: 8.30, atkAttacking: 25.0,
                  atkByTargetClass: { land: 25, air: 4, naval: 3 },
                  defByAttackerClass: { land: 8.3, air: 1.3, naval: 1 },
                  pool: 100, sits: 'first', maxLevel: 20,
                  buffs: { st: { channel: 'both', curve: { 1: 1.15, 2: 1.15, 3: 1.20, 4: 1.25, 5: 1.25, 6: 1.30, 7: 1.30, 8: 1.35, 9: 1.35, 10: 1.40, 11: 1.40, 12: 1.45, 13: 1.45, 14: 1.50, 15: 1.50, 16: 1.55, 17: 1.55, 18: 1.60, 19: 1.60, 20: 1.60 } } },
                  hpBuffs: { st: { 1: 1.00, 2: 1.05, 3: 1.10, 4: 1.10, 5: 1.14, 6: 1.14, 7: 1.18, 8: 1.18, 9: 1.22, 10: 1.22, 11: 1.26, 12: 1.26, 13: 1.30, 14: 1.30, 15: 1.34, 16: 1.34, 17: 1.38, 18: 1.38, 19: 1.42, 20: 1.42 } } },
  lucien:       { label: 'Lucien Laroche', atkDefending: 8.0, atkAttacking: 8.0,
                  atkByTargetClass: { land: 8, air: 2, naval: 6 },
                  defByAttackerClass: { land: 8, air: 2, naval: 6 },
                  pool: 40, sits: 'first', maxLevel: 15 },
  // The second unstable hero, and the second "w/" variant. Attacking, its own
  // contribution reads 37.94 against light artillery, 37.79 against infantry
  // and 37.49 against cavalry -- a 1.2% spread where plain Lucien is 8.00
  // flat, and where the table said 8.00 for this one too. Tōgō-with-
  // bombardment behaves the same way and much more strongly. Both are "with
  // something" variants and neither is explained, so both report a band.
  // The second anomalous hero, and the second "w/" variant. On a SIX-TYPE
  // stack it contributes exactly 8.00 -- the same as plain Lucien, which is
  // what this table has always said. On a SINGLE-TYPE stack it contributes
  // 36.44 to 37.94, and the extra is close to a flat 29 whatever the stack's
  // coefficient is: 29.94 on light artillery whose rows total 50, and 28.44 on
  // heavy tanks whose rows total 450. That is not a multiplier and not an own
  // attack, and it vanishes on the mixed stack entirely.
  //
  // 8.00 is what goes in the table, because it is the figure the six-type
  // reading and plain Lucien agree on. The band records the rest, and the
  // engine says so rather than quoting either end as though it were settled.
  // Tōgō-with-bombardment is the same family and much stronger.
  lucien_g:     { label: 'Lucien Laroche w/gas', atkDefending: 8.0, atkAttacking: 8.0,
                  // The land cell reads 37.94 on a single-type stack and 8.00 on a
                  // six-type one. 8.00 is what the table uses, for the reason above,
                  // so the column is scaled to match it rather than contradict it.
                  atkByTargetClass: { land: 8.0, air: 6.74, naval: 1.27 },
                  defByAttackerClass: { land: 8, air: 2, naval: 6 },
                  pool: 40, sits: 'first', maxLevel: 15 },
  // atkAttacking was 62.0 and is 8.0. The old figure was this hero's own
  // attack plus an ATTACK-ONLY buff, added together because the stack it was
  // read on is one Pershing buffs. The app quoted 102.00 against ten infantry
  // where the server prints 60.00. It buffs FIVE types -- infantry, cavalry,
  // armoured cars, light and heavy tanks -- and none of artillery, railguns or
  // stormtroopers, all at the same curve, read on heavy tanks and confirmed at
  // level 10 on all five.
  pershing:     { label: 'John J. Pershing “Black Jack”', atkDefending: 8.0, atkAttacking: 8.0,
                  atkByTargetClass: { land: 8, air: 4, naval: 8 },
                  defByAttackerClass: { land: 8, air: 4, naval: 8 },
                  pool: 80, sits: 'first', maxLevel: 20,
                  buffs: { inf: { channel: 'attack', curve: { 1: 1.10, 2: 1.12, 3: 1.14, 4: 1.17, 5: 1.20, 6: 1.22, 7: 1.24, 8: 1.26, 9: 1.28, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40, 16: 1.42, 17: 1.44, 18: 1.46, 19: 1.48, 20: 1.50 } },
                           cav: { channel: 'attack', curve: { 1: 1.10, 2: 1.12, 3: 1.14, 4: 1.17, 5: 1.20, 6: 1.22, 7: 1.24, 8: 1.26, 9: 1.28, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40, 16: 1.42, 17: 1.44, 18: 1.46, 19: 1.48, 20: 1.50 } },
                           ac:  { channel: 'attack', curve: { 1: 1.10, 2: 1.12, 3: 1.14, 4: 1.17, 5: 1.20, 6: 1.22, 7: 1.24, 8: 1.26, 9: 1.28, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40, 16: 1.42, 17: 1.44, 18: 1.46, 19: 1.48, 20: 1.50 } },
                           lt:  { channel: 'attack', curve: { 1: 1.10, 2: 1.12, 3: 1.14, 4: 1.17, 5: 1.20, 6: 1.22, 7: 1.24, 8: 1.26, 9: 1.28, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40, 16: 1.42, 17: 1.44, 18: 1.46, 19: 1.48, 20: 1.50 } },
                           ht:  { channel: 'attack', curve: { 1: 1.10, 2: 1.12, 3: 1.14, 4: 1.17, 5: 1.20, 6: 1.22, 7: 1.24, 8: 1.26, 9: 1.28, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40, 16: 1.42, 17: 1.44, 18: 1.46, 19: 1.48, 20: 1.50 } } },
                  // The infantry curve DROPS at level 6, from 1.70 to 1.10, and
                  // climbs again. Measured exactly, reproduced at three units as
                  // well as two, and confirmed by an independently derived pool.
                  // No formula fits both sides of that step.
                  hpBuffs: { inf: { 1: 1.00, 2: 1.50, 3: 1.50, 4: 1.70, 5: 1.70, 6: 1.10, 7: 1.10, 8: 1.12, 9: 1.12, 10: 1.14, 11: 1.14, 12: 1.16, 13: 1.16, 14: 1.18, 15: 1.18, 16: 1.20, 17: 1.20, 18: 1.22, 19: 1.22, 20: 1.25 },
                             ht:  { 1: 1.00, 2: 1.00, 3: 1.10, 4: 1.10, 5: 1.15, 6: 1.15, 7: 1.20, 8: 1.20, 9: 1.25, 10: 1.25, 11: 1.30, 12: 1.30, 13: 1.35, 14: 1.35, 15: 1.40, 16: 1.40, 17: 1.45, 18: 1.45, 19: 1.50, 20: 1.50 } } },
  georg:        { label: 'Georg Bruchmüller', atkDefending: 6.0, atkAttacking: 12.0,
                  atkByTargetClass: { land: 12, air: 2, naval: 8 },
                  defByAttackerClass: { land: 6, air: 1, naval: 4 },
                  pool: 40, sits: 'first', maxLevel: 20,
                  buffs: { art: { channel: 'attack', curve: { 1: 1.15, 2: 1.20, 3: 1.20, 4: 1.22, 5: 1.22, 6: 1.24, 7: 1.26, 8: 1.28, 9: 1.30, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40, 16: 1.42, 17: 1.44, 18: 1.46, 19: 1.48, 20: 1.50 } } } },
  tatiana:      { label: 'Tatiana Minchakievich (Enemy Land)', atkDefending: 6.0, atkAttacking: 45.6,
                  atkByTargetClass: { land: 45.6, air: 7.6, naval: 3.8 },
                  defByAttackerClass: { land: 6, air: 1, naval: 0.5 },
                  pool: 15, sits: 'first', maxLevel: 20 },
  hank:         { label: 'Henry “Hank” Callahan', atkDefending: 6.0, atkAttacking: 5.0,
                  atkByTargetClass: { land: 5, air: 1, naval: 3 },
                  defByAttackerClass: { land: 6, air: 1.2, naval: 3.6 },
                  pool: 40, sits: 'first', maxLevel: 10,
                  // The two sides agree exactly at levels 1 through 9 and part
                  // at the cap: 1.10 attacking, 1.09 defending. Read on both
                  // sides at every level, because one point cannot tell a
                  // per-side curve from a single bad cell. The curve here came
                  // from a DEFENDING screen, so the attacking cap was 0.4 low.
                  buffs: { inf: { channel: 'both',
                           curve:          { 1: 1.00, 2: 1.03, 3: 1.03, 4: 1.05, 5: 1.06, 6: 1.06, 7: 1.07, 8: 1.08, 9: 1.09, 10: 1.10 },
                           curveDefending: { 1: 1.00, 2: 1.03, 3: 1.03, 4: 1.05, 5: 1.06, 6: 1.06, 7: 1.07, 8: 1.08, 9: 1.09, 10: 1.09 } } } },
  johan:        { label: 'Johan “Aardvark” Maes', atkDefending: 5.0, atkAttacking: 4.0,
                  atkByTargetClass: { land: 4, air: 0.5, naval: 2 },
                  defByAttackerClass: { land: 5, air: 0.5, naval: 2.5 },
                  pool: 40, sits: 'first', maxLevel: 20 },
  tatiana_home: { label: 'Tatiana Minchakievich (Friendly Land)', atkDefending: 5.0, atkAttacking: 10.0,
                  atkByTargetClass: { land: 10, air: 2, naval: 1 },
                  defByAttackerClass: { land: 5, air: 1, naval: 0.5 },
                  pool: 15, sits: 'first', maxLevel: 20 },
  maeve:        { label: 'Fiona “Maeve” Porter', atkDefending: 4.0, atkAttacking: 4.0,
                  atkByTargetClass: { land: 4, air: 1, naval: 1 },
                  defByAttackerClass: { land: 4, air: 1, naval: 1 },
                  pool: 20, sits: 'last', maxLevel: 15 },
};

// A hero counts 0.40 in the damage split, the same constant for all sixteen --
// independent of its attack, its pool and its level. Bracketed to
// [0.398, 0.4005] over 27 uncensored readings.
export const HERO_ALLOC_WEIGHT = 0.40;

// How incoming damage splits across a stack's rows:
//     weight_i = TARGET_FACTOR[unit_i] * count_i
// A property of the TARGET, not the attacker: all nine land attackers give the
// identical three-value pattern. Infantry soak half of what anything else
// takes; cavalry three quarters.
export const TARGET_FACTOR = { inf: 0.50, cav: 0.75 };
export const TARGET_FACTOR_DEFAULT = 1.00;

// Accepted by the form but refused on land by the server, so nothing about
// them is measured. Named so the app can offer them and say why it cannot
// compute them, rather than pretending they do not exist.
// The six the server refuses on a LAND stack. They are not inert: all six work
// on their own terrain and all six change the battle, decomposed 2026-08-19
// with two attacker types apiece so the hero's own attack is separated from
// its multiplier. Attacking values at level 10; the defending column and the
// level curves are untested, so the engine applies these only to an attacking
// air or naval stack and says so.
//
// Each one buffs the thing its namesake actually commanded: Hersing the
// U-boat captain buffs submarines, von Thaden the airship man buffs
// zeppelins, Richthofen the fighter ace buffs fighters, Togo the admiral
// buffs battleships. All of them at x1.30 except Togo-with-bombardment at
// x1.28 -- the same figure the land heroes' curves reach at their caps.
//
// Each hero's own attack is the MIDPOINT of the readings that isolate it, not
// the smallest: it shows up as an excess on every unit type the hero does not
// buff, and those readings differ by up to 0.14 because each is a difference
// of two spans printed to one decimal. Togo-with-bombardment is x1.2785 and
// NOT the tidy 1.28 -- the bracket is about +/-0.0004 and excludes it.
//
// The multiplier acts on the side's OUTPUT as the engine computes it, which
// for air attacking ground is the ATTENUATED, post-fire figure. Dividing the
// excess by the un-attenuated coefficient instead gives Richthofen a bogus
// x1.07; against the real baseline he is x1.30 like the rest.
// THE SIX HEROES THE SERVER REFUSES ON LAND. They are not unmodelled any more.
// Each is decomposed on ITS OWN terrain, attacking and defending, across its
// whole level range -- own attack separated from multiplier with a control
// stack of a type the hero does not buff.
//
// READ WHERE NOTHING IS ATTENUATED. The attacking figures used to be read
// against a GROUND target, and air attacking ground is a post-fire law, so
// those readings confounded the hero's own attack with the attenuation of the
// whole stack. It showed: the four naval heroes decomposed to 40.00, 15.00,
// 64.32 and 1.00 and the two air heroes to 16.80 and 10.07 -- round numbers
// and unround ones, split exactly along the line of which readings were
// attenuated. Re-read air-against-air, Richthofen's own attack at level 10 is
// 70.0, not 16.80. A factor of four, hiding in a decimal that looked precise.
//
// AND CORRECT FOR THE STACK THE HERO JOINS. A hero is a unit: adding it to a
// stack of twenty changes what those twenty contribute, because the stack
// saturates. Subtracting the plain reading gives 39.83, 24.95, 14.83, 9.83,
// 0.98 -- all just under a round number. Allowing for the shift gives exactly
// 40, 25, 15, 10, 1.
//
// TWO THINGS HERE THAT NO LAND HERO DOES. Richthofen's and Tōgō-with-
// bombardment's OWN ATTACK moves with level (25 to 125 for Richthofen), where
// every land hero's is a constant. And Hersing's POOL moves with level, 100 to
// 200.7, where the land heroes' are flat across every level tested. Both were
// found by artifacts rather than by looking: subtracting a level-10 own-attack
// constant at level 1 produced multipliers of 0.775, and a multiplier below
// one would mean a hero makes its own stack worse.
// A HERO'S OWN OUTPUT IS NOT ATTENUATED. Air attacking a surface target fires
// with what survives the round, and the hero does not: von Thaden adds exactly
// 10.00 to a stack that lost 13.50 HP, to one that lost 168.30, and to one that
// lost 201.90. Three attenuation factors from 0.98 to 0.74, one constant
// contribution. So the post-fire law applies to the UNITS and the hero is added
// on top of the attenuated total.
export const HEROES_OTHER_TERRAIN = {
  otto:   { label: 'Otto Hersing', terrain: 'sea', maxLevel: 15, sits: 'first',
            atkAttacking: 40.0, atkDefending: 40.0,
            pool: 100, poolCurve: { 1: 100.0, 2: 100.0, 3: 110.0, 4: 120.1, 5: 120.1, 6: 130.3, 7: 135.5, 8: 140.3, 9: 145.5, 10: 150.3, 11: 159.9, 12: 170.8, 13: 179.7, 14: 191.0, 15: 200.7 },
            buffs: { sub: { channel: 'attack', curve: { 1: 1.05, 2: 1.10, 3: 1.10, 4: 1.15, 5: 1.15, 6: 1.20, 7: 1.20, 8: 1.25, 9: 1.25, 10: 1.30, 11: 1.30, 12: 1.35, 13: 1.35, 14: 1.40, 15: 1.40 } } },
            why: "Can't have Otto Hersing on land." },
  togo:   { label: 'Tōgō Heihachirō', terrain: 'sea', maxLevel: 20, sits: 'first',
            atkAttacking: 15.0, atkDefending: 15.0, pool: 120.6,
            buffs: { bb: { channel: 'both', curve: { 1: 1.00, 2: 1.00, 3: 1.15, 4: 1.15, 5: 1.20, 6: 1.20, 7: 1.25, 8: 1.25, 9: 1.30, 10: 1.30, 11: 1.34, 12: 1.34, 13: 1.38, 14: 1.38, 15: 1.42, 16: 1.42, 17: 1.46, 18: 1.46, 19: 1.50, 20: 1.50 } } },
            why: "Can't have Tōgō Heihachirō on land." },
  togo_b: { label: 'Tōgō Heihachirō w/bombardment', terrain: 'sea', maxLevel: 20, sits: 'first',
            // CORRECTED. This read 64.90, and 64.90 was never this hero's own
            // attack: it is 15.00 plus the whole of its bombardment, measured
            // at a pool ratio where the target absorbed all of it. Plain Tōgō
            // -- same hull, same pool, same cap, differing only in the ability
            // -- reads 15.00, and so does this hero once the ability expires
            // in round 7. The ladders that used to sit here as evidence of an
            // "unstable coefficient" were the ability's total being divided
            // among everything standing in its blast, which is why they moved
            // with the counts on BOTH sides. See BOMBARDMENT.
            //
            // Those ladders are NOT reproduced cell-by-cell by the new law and
            // are not asserted to be: every one of them was taken in melee, so
            // each figure is a subtraction of a no-hero baseline from a total
            // that also contains the stack's own damage -- and a hero takes a
            // slot in the saturating stack, so the two sides of that
            // subtraction do not have the same E(n). The BAND's endpoints do
            // come out exactly: pool share 0.46 gives 37.99 and share 1.00
            // gives 64.90.
            atkAttacking: 15.0, atkDefending: 15.0, pool: 120.6,
            // Kept as DATA under a name that says what it is. These were
            // real readings; they were labelled an own-attack curve. Each is
            // 15.00 plus the ability at that level, seen through one pool
            // ratio, and reading them at 50 km against a lone target recovers
            // the ability outright: 10, 15, 15, 20, 25 ... 5 x level.
            supersededSumCurve: { 1: 24.98, 2: 29.97, 3: 29.97, 4: 34.96, 5: 39.95, 6: 44.94, 7: 49.93, 8: 54.92, 9: 59.91, 10: 64.90, 11: 69.89, 12: 74.88, 13: 79.87, 14: 84.86, 15: 89.85, 16: 94.84, 17: 99.83, 18: 104.82, 19: 109.81, 20: 114.80 },
            // THIS USED TO CARRY TWO CURVES, one per side: an attacking
            // battleship buff of 1.2944 at level 10 against a defending 1.30 —
            // identical to plain Tōgō — and a note saying no other hero in
            // either table needed such a thing. It was the same artifact as
            // the 64.90. The attacking curve was fitted to readings that had
            // the ability folded into them, so it absorbed the ability's
            // shortfall as a slightly smaller multiplier.
            //
            // The clean cell settles it. A battleship reaches 75 km and the
            // ability's radius is 40, so at 50 km the stack still fires while
            // the attacker sits OUTSIDE its own blast and the target absorbs
            // the ability whole. Then the togo_b reading minus the plain-Tōgō
            // reading is the ability and nothing else, and it comes out at
            // 10.00, 25.00, 50.00, 75.00 and 100.00 at levels 1, 5, 10, 15 and
            // 20 — exactly 5 x level, to the printed decimal, five times.
            // The buffs are the same buff. One curve, both sides.
            buffs: { bb: { channel: 'both',
                     curve: { 1: 1.00, 2: 1.00, 3: 1.15, 4: 1.15, 5: 1.20, 6: 1.20, 7: 1.25, 8: 1.25, 9: 1.30, 10: 1.30, 11: 1.34, 12: 1.34, 13: 1.38, 14: 1.38, 15: 1.42, 16: 1.42, 17: 1.46, 18: 1.46, 19: 1.50, 20: 1.50 } } },
            why: "Can't have Tōgō Heihachirō w/bombardment on land." },
  ivan:   { label: 'Ivan “Vedmid” Kovalenko', terrain: 'sea', maxLevel: 10, sits: 'first',
            atkAttacking: 1.0, atkDefending: 1.0, pool: 10,
            buffs: {},
            why: "Can't have Ivan “Vedmid” Kovalenko on land." },
  // A HERO HAS TARGET-CLASS COLUMNS TOO, at least this one does. Richthofen
  // adds 70.00 to a stack shooting at aircraft and 16.85 shooting at infantry
  // — a factor of four, from the same hero at the same level. That is why the
  // older figure of 16.80 and the air-vs-air figure of 70.0 are both correct,
  // and why calling the first an attenuation artifact was wrong: the stack in
  // that reading was attenuated by 1.6%, which turns 70.0 into 68.9, not 16.85.
  //
  // von Thaden has no such column — 10.00 exactly against infantry, a
  // battleship and a zeppelin — which is the same pattern the unit table has,
  // where artillery reads 8.0 against land and naval alike and a light tank
  // reads 30.0 and 15.0.
  //
  // The land and naval cells here are measured on an ATTENUATED path and the
  // hero's presence shifts the stack's own losses slightly, so they carry a
  // second-order uncertainty the air cell does not. They are recorded as the
  // raw excess, which is what the server printed.
  rbaron: { label: 'Manfred Von Richthofen', terrain: 'air', maxLevel: 20, sits: 'first',
            atkAttacking: 70.0, atkDefending: 25.0, pool: 61.2,
            // Its scalar and its curve were both read AIR against AIR, so the
            // class columns scale relative to the air cell, not the land one.
            atkColumnBase: 'air',
            // 16.85 and 17.53 are the RAW excesses. The hero also absorbs a
            // share of the incoming round (weight 0.40), which leaves the
            // units slightly less damaged and so slightly less attenuated, so
            // the excess is the hero PLUS a second-order shift. Solving the
            // post-fire law for the constant that reproduces the readings puts
            // land at 16.66 -- and it lands BOTH measured cells, a bomber
            // stack and a fighter stack, to within 0.007. Two independent
            // readings agreeing on one constant is a decomposition; matching
            // one of them would have been a fit.
            atkByTargetClass: { air: 70.0, land: 16.66, naval: 17.34 },
            atkAttackingCurve: { 1: 25.0, 2: 35.0, 3: 40.0, 4: 40.0, 5: 50.0, 6: 50.0, 7: 60.0, 8: 60.0, 9: 70.0, 10: 70.0, 11: 80.0, 12: 80.0, 13: 90.0, 14: 90.0, 15: 100.0, 16: 100.0, 17: 110.0, 18: 110.0, 19: 120.0, 20: 125.0 },
            buffs: { int: { channel: 'attack', curve: { 1: 1.00, 2: 1.00, 3: 1.00, 4: 1.15, 5: 1.15, 6: 1.20, 7: 1.20, 8: 1.25, 9: 1.25, 10: 1.30, 11: 1.30, 12: 1.34, 13: 1.34, 14: 1.38, 15: 1.38, 16: 1.42, 17: 1.42, 18: 1.46, 19: 1.46, 20: 1.50 } } },
            why: "Can't have Manfred Von Richthofen on land." },
  thaden: { label: 'Wilhelm von Thaden', terrain: 'air', maxLevel: 15, sits: 'first',
            atkAttacking: 10.0, atkDefending: 10.0, pool: 121.0,
            atkByTargetClass: { air: 10.0, land: 10.0, naval: 10.0 },
            buffs: { zep: { channel: 'attack', curve: { 1: 1.00, 2: 1.10, 3: 1.10, 4: 1.15, 5: 1.15, 6: 1.20, 7: 1.20, 8: 1.25, 9: 1.25, 10: 1.30, 11: 1.30, 12: 1.35, 13: 1.35, 14: 1.40, 15: 1.40 } } },
            why: "Can't have Wilhelm von Thaden on land." },
};

// The old name, kept because it is what the app imported for months. Same
// object -- these heroes ARE refused on land, that part was never wrong.
export const HEROES_LAND_REFUSED = HEROES_OTHER_TERRAIN;

export const FORM_DOMAINS = {
  terrain: ['land', 'sea', 'air', 'patrol', 'debark'],
  positionKm: [0, 1, 2, 3, 10, 20, 30, 40, 50, 75, 150],
  trench: { min: 0, max: 20 },
  buildingLevelSelect: [1, 2, 3, 4, 5],
  maxRounds: { min: 0.25, max: 1000, step: 0.25 },
  provenance: { all: 'FORM.domains' },
};

// ---------------------------------------------------------------------------
// WHAT IS NOT MEASURED
// ---------------------------------------------------------------------------
// The app must surface the relevant entries at the point of use, not in a
// footnote. Ranked roughly by how likely a user is to hit it.

// ---------------------------------------------------------------------------
// THE RECOVERY BILL -- the nine summary columns nobody had read back
// ---------------------------------------------------------------------------
// Every stack's result block carries a table with eleven columns. Two of them,
// HP lost and % lost, are the whole of what this project ever consumed. The
// other nine
//
//     food | fish | iron | wood | coal | oil | gas | cash | hours
//
// are the bill to put the stack back together: resources and cash to replace
// what was destroyed, and hours to do it in. The scraper was written to
// slugify unrecognised headers "so a column dxter adds later shows up as data
// instead of vanishing", and it worked -- 2,719 hours readings and 256
// complete resource rows were already sitting in results.jsonl, paid for by
// sweeps aimed at something else, and never once read back. The probe's own
// module docstring listed them as open; the gap list here had lost the entry.
//
// THE QUANTITY IS NOT HP LOST. Both the bill and the time are linear in
//
//     ue  =  HP lost / current per-unit HP  =  (pct lost / 100) x count
//
// -- unit equivalents, how many whole units' worth of the stack is gone.
// Against a full-HP stack that equals lost/maxHP, so a constant times HP lost
// fits every full-HP reading in the corpus and looks like the entire law. It
// is not, and two independent readings separate them:
//
//   * The trench sweep. The defender loses exactly 40.0 HP at every trench
//     level, and its hours fall 6, 6, 6, 6, 5, 5, 5, 5, 4 as the trench
//     enlarges the pool and the same 40 HP destroys fewer whole units. HP lost
//     never moves; the bill does.
//   * Twenty artillery at 10% HP, wiped, lose 40.00 HP where twenty at full HP
//     lose 400.00 -- and both print iron 60000, oil 40000, cash 200000,
//     hours 432. Ten times the HP, identical bill. A destroyed unit is
//     replaced whole, however little was left of it.
//
//     cost_r  =  round( SUM over rows of  REPAIR_COST[unit][r] x ue_row )
//     hours   =  floor( SUM over rows of  REPAIR_HOURS[unit]   x ue_row )
//
// FLOOR, and floored ONCE over the stack total rather than per row. Both halves
// are measured, not assumed. Against every reading in the corpus whose ue is
// exactly recoverable, floor is consistent for 16 of 16 units where ceil
// manages 1 and round 3; and the two-row 62-hour reading in mixed_stacks pins
// the single flooring (4.41 + 57.60 -> 62, where per-row flooring gives 61).
//
// SCOPE -- all eleven columns share one rule. A fortress that lost 180 HP moved
// neither a resource cell nor the hours; a hero that lost 66.7 HP took the same
// stack from 33 hours to 81. That is exactly the inclusion rule the HP column
// already followed: unit rows and hero rows count, building rows do not.
//
// HOW THE CONSTANTS WERE READ. On a wipe. Every other sweep in this project
// refuses a >=99.9% reading because a wiped stack's DAMAGE is censored, but
// nothing about that applies here: a wiped stack has lost exactly its whole
// count, so ue is the integer `count` with no rounding error at all, where any
// unwiped reading inherits the 3 significant figures of the printed
// percentage. n = 100 pins each constant to 0.01 in one request.
//
// The brackets below are honest. Several constants are NOT the clean number
// they sit next to -- int excludes 32.40 exactly, zep sits in [40.79, 40.80),
// lart in [9.97, 9.98) -- so no integer inference is claimed and the engine
// uses the bracket midpoint.

export const REPAIR_COST = {
  inf: { /* free */ },
  cav: { food: 1200, fish: 1200, cash: 6000 },
  ac: { iron: 2000, oil: 1000, cash: 8500 },
  lart: { food: 1000, iron: 1000, wood: 1000, cash: 10000 },
  art: { iron: 3000, oil: 2000, cash: 10000 },
  rrg: { iron: 10000, wood: 5000, coal: 5000, oil: 10000, cash: 50000 },
  lt: { iron: 5000, oil: 3000, cash: 20000 },
  ht: { iron: 7000, oil: 4000, cash: 30000 },
  convoy: { iron: 5000, wood: 7500, oil: 10000, cash: 50000 },
  st: { fish: 1500, iron: 1500, oil: 1500, cash: 12500 },
  bal: { wood: 1000, gas: 1000, cash: 5000 },
  int: { iron: 2000, wood: 5000, oil: 4000, cash: 20000 },
  tac: { iron: 5000, wood: 7500, oil: 10000, cash: 50000 },
  zep: { iron: 5000, wood: 5000, gas: 25000, cash: 50000 },
  sub: { iron: 3000, wood: 2000, oil: 3000, cash: 20000 },
  cl: { iron: 3000, coal: 2000, oil: 2000, cash: 15000 },
  bb: { iron: 15000, wood: 5000, coal: 10000, oil: 5000, cash: 50000 },
};

export const REPAIR_HOURS = {
  inf: { hours: 3.325, bracket: [3.32, 3.33], readings: 1 },
  cav: { hours: 1.665, bracket: [1.66, 1.67], readings: 4 },
  ac: { hours: 3.325, bracket: [3.32, 3.33], readings: 7 },
  lart: { hours: 9.975, bracket: [9.97, 9.98], readings: 4 },
  art: { hours: 21.6014, bracket: [21.6, 21.60279], readings: 12 },
  rrg: { hours: 65.005, bracket: [65.0, 65.01], readings: 4 },
  lt: { hours: 32.005, bracket: [32.0, 32.01], readings: 4 },
  ht: { hours: 43.00142, bracket: [43.0, 43.00285], readings: 23 },
  convoy: { hours: 54.005, bracket: [54.0, 54.01], readings: 4 },
  st: { hours: 2.705, bracket: [2.7, 2.71], readings: 4 },
  bal: { hours: 3.325, bracket: [3.32, 3.33], readings: 1 },
  int: { hours: 32.40383, bracket: [32.4013, 32.40636], readings: 26 },
  tac: { hours: 54.005, bracket: [54.0, 54.01], readings: 31 },
  zep: { hours: 40.795, bracket: [40.79, 40.8], readings: 23 },
  sub: { hours: 32.405, bracket: [32.4, 32.41], readings: 12 },
  cl: { hours: 21.605, bracket: [21.6, 21.61], readings: 12 },
  bb: { hours: 64.80345, bracket: [64.8, 64.80691], readings: 12 },
};

// The hero's rate, measured on ALL TWENTY-TWO heroes: two attack strengths
// each, sea and air heroes in their own terrain against a screen of their own
// class. Proportional to the hero's OWN ue, exactly like a unit row -- a flat
// charge is refuted by every hero whose two readings actually differ (alvin
// 52 then 81 hours as its share of the loss rises, kangal 46 then 86).
//
// Four heroes -- tatiana, tatiana_home, maeve, ivan -- read "flat survives",
// and that is a test with no power rather than evidence: their pools are small
// enough that both attack strengths wiped the hero outright, so ue_hero was
// 1.0 in both readings and the two hypotheses predict the same number. §0's
// thirteenth lesson, showing up again.
//
// ONE SHARED RATE covers all 22, bracket [71.87, 72.41) -- genuinely unusual
// here, where every other hero coefficient differs per hero, often by a factor
// of ten. That is why this was measured across the whole table rather than
// generalised from the two heroes that first agreed.
//
// Heroes cost NO resources: the cells stayed at zero throughout, against free
// infantry, while the hero bled.
export const HERO_REPAIR = { hours: 72.14, bracket: [71.87, 72.41], heroesMeasured: 'all 22' };

// ---------------------------------------------------------------------------
// BOMBARDMENT -- the "unstable hero" that was never a hero coefficient
// ---------------------------------------------------------------------------
// This project recorded two heroes whose own contribution would not settle:
// Togo-with-bombardment read anywhere from 37.99 to 64.90 "depending on how
// many units are on each side", and Lucien-with-gas 8.00 on a mixed stack but
// 36-38 on a single-type one. Thirty-four requests failed to find a rule, and
// it went into NOT_MEASURED as needing "a mechanism nobody has proposed yet".
//
// The mechanism was written down by the site's author the whole time. Every
// control on the form links to share/s1914.info.html, and two of that page's
// section anchors are #togo and #lucien:
//
//     "the bombardment ability will be in effect for 6 rounds. This is in
//      additional to the normal damage that the stack inflicts. Any stack
//      (enemy or your own) within 40 km of the target stack will take
//      bombardment damage."
//
// So it is not an own-attack coefficient at all. It is a SECOND damage source,
// centred on the target, and the "instability" was its total being divided
// among everything standing in the blast -- which is exactly why it moved with
// the unit counts on BOTH sides.
//
// Nothing here is recorded because the page says it; the page is prose written
// by a person about software that changes. Every line below is a number the
// server was made to produce, using the isolation the page suggested:
// submarines are melee, so at 10-50 km the stack cannot reach and every point
// of damage the target takes is the ability alone.
//
//   OWN ATTACK. Plain Togo reads 15.00 at every level from 1 to 20, and plain
//   Lucien 8.00 at every level from 1 to 15 -- flat. The recorded
//   atkAttackingCurve (24.98, 29.97, 29.97, 34.96 ...) was never the hero: it
//   is 15.00 plus a bombardment share, and it climbed because the ABILITY
//   climbs. The old atkAttacking of 64.90 was the top of that sum.
//
//   THE SPLIT. Five attacker sizes against a fixed defender, all at 10 km:
//   1/share is linear in the attacker's pool with slope 0.00020005 where
//   1/poolB is 0.00020000 -- a 0.025% match. So each stack in the blast takes
//   the ability in proportion to its share of the HP pool standing in it. The
//   intercept says there is one more participant worth ~39 HP; the hero's own
//   row is it, and its printed losses track that share at all five sizes.
//
//   THE RADIUS is centred on the TARGET, not the attacker, and the target is
//   always hit however far away it is. What the radius decides is who ELSE is
//   caught -- including the attacker's own stack, which is why moving the
//   target from 40 km to 50 km RAISES its losses from 56.39 to 65.00: past 40
//   the attacker steps out of its own blast and the target absorbs the lot.
//
//   FRIENDLY FIRE is real. A second stack of ours, 20 km from the target, 25
//   km outside any melee range and attacked by nobody, lost 12.40 HP against
//   a predicted 12.50. With plain Togo aboard instead it lost exactly zero.
//
//   DURATION. Togo's ability contributes for 6 rounds and Lucien's for 9,
//   exactly as the page says: round 7 of a Togo strike drops from 56.39 to
//   14.77, and rounds 10 and 11 of a Lucien strike deliver 8.00 -- the hero's
//   own attack and nothing else.
export const BOMBARDMENT = {
  togo_b: {
    label: 'Togo Heihachiro w/bombardment',
    ownAttack: 15.00,
    rounds: 6,
    radius: 40,
    radiusMeasuredAt: 'level 10 only',
    // RANGE is not RADIUS. Range is how far the ability can be aimed; radius
    // is how far it splashes once it lands. Measured floor only: it strikes at
    // 50 km and nothing beyond that was submitted for Tōgō.
    range: 50,
    rangeNote: 'measured floor — it fires at 50 km; no upper bound submitted',
    // The extra pool standing in the blast besides the two unit stacks. From
    // the intercept of 1/share against attacker pool over five sizes.
    extraPool: 39.2,
    // Measured directly at 50 km, where the target is alone in the blast and
    // the reading is the whole ability. 5 x level from level 3 up; levels 1
    // and 2 sit above that line and are quoted as read.
    totalByLevel: {
      1: 10, 2: 15, 3: 15, 4: 20, 5: 25, 6: 30, 7: 35, 8: 40, 9: 45, 10: 50,
      15: 75, 20: 100,
    },
    rule: '5 x level for level >= 3',
  },
  lucien_g: {
    label: 'Lucien Laroche w/gas',
    ownAttack: 8.00,
    rounds: 9,
    // The page says Lucien's radius varies with level and it does: every rung
    // below was read off the distance at which the attacker stops sharing its
    // own blast.
    radiusByLevel: { 1: 20, 5: 30, 10: 40, 15: 50 },
    radiusBracketAtCap: [50, 75],
    // And its RANGE grows too, which is the second half of the page's "ranges
    // and radii are different for Lucien depending on the level". At level 15
    // it strikes a target 75 km away for the full 40.00; at levels 4 through
    // 12 the same request returns no result rows at all. Levels 13 and 14 were
    // never sent, so the table steps at the measured rungs and says so.
    rangeByLevel: { 1: 50, 12: 50, 15: 75 },
    // Lucien's extra participant is a different size from Tōgō's, which is
    // itself the evidence that it is the HERO's row and not a constant of the
    // ability: 16.1 here against 39.2 there. Fitted twice independently and
    // agreeing to 0.05 — level 10 inside its 40 km radius gives 16.05, level
    // 15 inside its 50 km radius gives 16.2. Lucien's recorded pool is 40 and
    // Tōgō's 120.6, so neither extra is the pool itself; Lucien's is 0.40 of
    // it, which is exactly the weight a hero row carries in this game's damage
    // allocation, and Tōgō's is 0.33 of it, which is not. Recorded as fitted
    // numbers rather than dressed up as a rule.
    extraPool: 16.1,
    rangeNote: 'floors: 50 km measured up to level 12, 75 km at level 15, silent at 150',
    // All fifteen levels measured. Steps every three levels; the cap takes an
    // extra step.
    totalByLevel: {
      1: 15, 2: 15, 3: 15, 4: 20, 5: 20, 6: 20, 7: 25, 8: 25, 9: 25,
      10: 30, 11: 30, 12: 30, 13: 35, 14: 35, 15: 40,
    },
    rule: '5 x (floor((level-1)/3) + 3), except the level-15 cap which is 40',
  },
};

// The blast is shared in proportion to pool, over every stack inside it plus
// one more participant of about this size -- the hero's own row.
export const BOMBARDMENT_SPLIT = {
  by: 'HP pool share',
  extraPool: 39.2,
  extraPoolNote: 'From the intercept of 1/share against the attacker pool over five sizes. It is NOT the hero pool this project recorded for Togo (120.6), and that disagreement is unexplained; the hero row is nonetheless the only other participant present, and its own printed losses match this share at all five sizes to within the 0.1 the spans print.',
  fortressDR: 'NOT MEASURED against bombardment. The engine does not reduce it, by analogy with building damage, which IS measured as unreduced by fortress DR. Flagged wherever both appear.',
};

// A HERO FIRES WHEN ITS STACK CANNOT. Measured, and it overturns a claim this
// file used to make flatly. Ten submarines at 0 km against a target at 10-50
// km produce NO result rows at all -- until a hero is aboard, and then the
// target loses 15.00 a round. So "out of range means no battle" is true only
// of a stack with no hero in it. Heroes have their own reach: plain Lucien
// still fires at 50 km and is silent at 75.
export const HERO_REACH = {
  togo: { reach: 50, bound: 'at least 50 km; no upper bound measured' },
  togo_b: { reach: 50, bound: 'at least 50 km; no upper bound measured' },
  lucien: { reach: 50, bound: 'fires at 50 km, silent at 75' },
  lucien_g: { reach: 50, bound: 'fires at 50 km, silent at 75' },
};

// ---------------------------------------------------------------------------
// MUTUAL ATTACKS -- the half of the form this project never submitted
// ---------------------------------------------------------------------------
// Every one of the ~2,400 readings on disk before this was one stack attacking
// a stack that was only defending. duel() is the only thing in the rig that
// ever set a B-side target and it always set "0". The form has offered the
// other configuration since the first request, and the site's help page says
// it is not cosmetic:
//
//     "There are always two armies or sides, A and B ... If two stacks are
//      each attacking the other it makes a difference which side they are on.
//      Army A will always attack first in such a scenario ... this only
//      applies if both stacks are attacking each other. If, for example, a
//      stack in one army is attacking a stack that is just defending, it will
//      make no difference which side they are on."
//
// Both claims are true, and the first one is much stronger than it sounds.
//
// A MUTUAL ATTACK IS TWO ENGAGEMENTS, NOT ONE.
//
//   1. A attacks. Ordinary battle: A's ATTACK column against B's DEFENCE
//      column, both from the pre-round state. This is the model the app
//      already had.
//   2. The stacks are updated -- deaths, pools, effective counts.
//   3. B attacks, with what survived, using ITS attack column against A's
//      DEFENCE column.
//
// So each side fires twice per round in a mutual battle: once with its attack
// stat and once with its defence stat. That is why a mutual round costs both
// sides far more than a one-sided one -- ten infantry against ten lose 50.00
// defending and 82.00 mutually.
//
// SIXTEEN CELLS PREDICTED IN ADVANCE. The law was written down from four
// readings and then used to predict every cell of a roster whose attack and
// defence columns disagree by up to four times AND IN BOTH DIRECTIONS -- a
// stormtrooper attacks land at 25.0 and defends at 6.3, an armoured car
// attacks at 6.0 and defends at 12.0 -- before those cells were submitted.
// Every one came back to the printed decimal. A rule that inflated everything
// would have failed the armoured car immediately.
//
// WHAT THE SIDE LETTER IS WORTH. A stack destroyed in engagement 1 never
// fights engagement 2. Ten light artillery facing a hundred infantry lose
// their whole 100 HP pool in the first engagement and deal nothing at all --
// where a DEFENDING stack that is wiped still deals its full figure, which
// this project measured long ago and which is unchanged. Short of death the
// advantage is smaller but real: a hundred infantry against ten stormtroopers
// lose 226.12 holding the A slot and 285.56 holding the B slot, a fifth of
// their losses decided by nothing but which army they are in.
//
// AND THE PAGE'S OWN CONTROL HOLDS. With only one side attacking, moving both
// stacks to the other army changes nothing: 63.00 and 40.00 either way, to the
// printed decimal. The side letter is inert unless both stacks are attacking.
export const MUTUAL = {
  engagements: 2,
  order: 'A attacks first, then B with the survivors',
  secondEngagementUses: "the attacker's attack column against the defender's defence column, roles swapped",
  destroyedNeverFires: true,
  aSlotAdvantageExample: { pair: '100 inf vs 10 st', onA: 226.12, onB: 285.56 },
  cellsPredictedInAdvance: 16,
  notModelledInEngagement2: ['fortress', 'buildings', 'heroes'],
};

// ---------------------------------------------------------------------------
// MULTI-STACK BATTLES -- more than one stack an army, which this app does not model
// ---------------------------------------------------------------------------
// Every reading this project took for its first 2,585 was one stack a side.
// The form has always accepted more, and the site's help page makes three
// claims about what happens when you use them. All three were submitted, in
// seven requests, and all three hold. They are recorded here because a player
// reading a one-stack answer off this app needs to know which of them the
// number quietly assumes.
//
// THE HEADLINE FINDING IS ABOUT THE RECORD, NOT THE GAME. There is exactly ONE
// <table class=resultTable> per ARMY, not one per stack -- the site says so in
// a title attribute it has always served and nobody had read: "The total hit
// points lost by all the stacks during the battle." With one stack an army an
// army total and a stack total are the same number, so 2,585 readings could
// not tell them apart, and the parser's association rule handed the army total
// to whichever stack happened to precede it. It was right by coincidence for
// the whole project. See test_result_table.py sections 9-11.
//
// 1. CO-LOCATED DEFENDERS ALL JOIN IN. One stack attacking one of two enemy
//    stacks parked together fights both. A.1 attacks B.1 with B.2 idle
//    alongside it: A.1's 40.0 of output is SPLIT 20.0/20.0 across both, and
//    A.1 takes 100.0 back -- 50.00 from each, both defending at full strength.
//    Attacking one stack of a pile is attacking the pile.
//
// 2. CONCENTRATED ATTACKS ARE ADDITIVE, AND THE DEFENDER WEAKENS BETWEEN THEM.
//    A.1 and A.2 both target B.1. B.1 loses 80.0, exactly 40.0 + 40.0. But the
//    two attackers do not take the same beating: A.1 loses 50.0 and A.2 loses
//    40.0, because B.1 answers A.1 at full strength and answers A.2 with what
//    is left -- 50.00 x 0.8 = 40.00 on a stack already down to 160 of 200. The
//    defender replies to each attacker IN SEQUENCE, weakening as it goes, so
//    the last stack to pile on pays the least. The same arithmetic predicts
//    the four-stack baseline before it was submitted: A.1 takes 50 + 50 = 100
//    and A.2 takes 45 + 45 = 90, against 100.0 and 90.0 printed.
//
// 3. A BUILDING IS INHERITED BY EVERY LAND STACK STANDING ON IT. A level-5
//    fortress belongs to B.1; B.2 is a separate stack at 0 km with no building
//    of its own. Both lose 4.2 where an unprotected stack loses 40.0. B.2 is
//    getting the full 90% damage reduction off a building it does not own.
//
// 4. AND 1 KM IS THE ESCAPE HATCH, EXACTLY AS DOCUMENTED. Move B.2 to 1 km and
//    it loses 38.9 while B.1 still loses 4.3. One kilometre is the whole
//    difference between 90% protection and none. This is the mechanic the help
//    page describes for keeping a stack out of a fortress it does not want to
//    be in, and it is not approximate.
//
// 5. THE AIRCRAFT-TRANSPORT EXCEPTION IS EXACT. An Airplane Convoy at 0 km
//    does not inherit. Without the fortress the two defenders lose 27.6 and
//    52.4; with it, 2.9 and 52.4. The convoy's figure does not move by a
//    hundredth. It is the same unit the roster already flags as stacking with
//    nothing, and this is the first measurement of what that costs it.
//
// WHAT THIS APP DOES. It models ONE stack a side and says so in the interface.
// Nothing above is implemented, because implementing it means asking the user
// for a position in kilometres per stack and a target per stack, and the two
// laws that matter most to a player -- co-located defenders join in, and the
// defender weakens between concentrated attackers -- are both things a player
// can apply to a one-stack answer by hand once they know them. They are here
// to be known.
export const MULTI_STACK = {
  modelledByThisApp: false,
  stacksPerSideModelled: 1,
  oneResultTablePerArmy: true,
  coLocatedDefendersAllFight: true,
  attackerOutputSplitAcrossCoLocatedDefenders: true,
  concentratedAttacksAdditive: true,
  defenderAnswersEachAttackerInSequence: true,
  buildingsInheritedAtZeroKm: true,
  escapeDistanceKm: 1,
  buildingInheritanceExceptions: ['convoy'],
  readings: {
    idle: { 'A.1': 100.0, 'A.2': 0.0, 'B.1': 20.0, 'B.2': 20.0 },
    concentrated: { 'A.1': 50.0, 'A.2': 40.0, 'B.1': 80.0 },
    baseline: { 'A.1': 100.0, 'A.2': 90.0, 'B.1': 40.0, 'B.2': 40.0 },
    fortressAt0km: { 'B.1': 4.2, 'B.2': 4.2 },
    fortressAt1km: { 'B.1': 4.3, 'B.2': 38.9 },
    convoyNoFortress: { 'B.1': 27.6, 'B.2': 52.4 },
    convoyWithFortress: { 'B.1': 2.9, 'B.2': 52.4 },
  },
};

// ---------------------------------------------------------------------------
// SCOPE LIMITS -- measured, understood, and deliberately NOT modelled
// ---------------------------------------------------------------------------
// A different list from NOT_MEASURED and it has to be. NOT_MEASURED is where
// the record is silent; this is where the record SPEAKS and the app declines to
// listen, because implementing it would need inputs this form does not ask for.
// Filing these under "not measured" would be a lie in the flattering direction
// -- it makes an unmodelled law look like an open question rather than a known
// one the reader is now responsible for applying themselves. So each entry says
// what the player should do about it instead.
export const SCOPE_LIMITS = [
  {
    key: 'multi_stack',
    what: 'One stack a side. A real battle can have several stacks in each army, and this page models exactly one.',
    why: 'The laws are measured and they are in MULTI_STACK: co-located defenders all join in and split the attacker\u2019s output between them; concentrated attacks add up, with the defender answering each attacker in turn and weakening as it goes; a building at 0 km is inherited by every land stack standing on it, an Airplane Convoy excepted; and moving a stack 1 km away takes it out of the building entirely. Modelling them means asking for a position in kilometres and a target for every stack, which is a different form from this one.',
    whatToDoInstead: 'Attacking a pile: add the defenders\u2019 stacks together to see what comes back at you, since all of them answer. Piling on: the figures add, and each attacker after the first takes less return fire in proportion to how much of the defender\u2019s pool is already gone. Defending near a fortress you do not want: 1 km is enough to leave it.',
  },
  {
    key: 'mutual_second_engagement_extras',
    what: 'In a mutual attack, the second engagement is fought without the fortress, buildings or hero effects that the first engagement applies.',
    why: 'The two-engagement law itself was predicted in advance and confirmed on sixteen cells, but every one of those cells was bare stacks. What a fortress does to the return engagement has not been measured, and guessing it would put an unmeasured number inside a measured law.',
    whatToDoInstead: 'Read a mutual result with a fortress or a hero on the board as a LOWER bound on the defended side\u2019s advantage, not as a figure.',
  },
];

export const NOT_MEASURED = [
    { key: 'bombardment_melee_split', what: 'How a HERO\u2019s bombardment ability divides its total when the attacker is standing ON its target, at 0 km.', why: 'Everything else about the ability is measured hard. Its total is 5 x level for T\u014dg\u014d and a three-level staircase for Lucien, read at a distance where the target is alone in the blast; it lasts 6 rounds and 9 rounds respectively; its radius is centred on the target, 40 km for T\u014dg\u014d and 20/30/40/50 km by level for Lucien; and from 10 km out to the radius it is divided by HP POOL SHARE, which reproduces every reading exactly \u2014 41.39 predicted against 41.39 printed, and a friendly stack 20 km away losing 12.40 against a predicted 12.50. At 0 km it is NOT pool share. A hundred submarines attacking fifty give the defender 0.2918 of the total where pool share says 0.3325, and a battleship stack against light cruisers goes the other way. Post-round pools, an attenuation term and a power law were each tried against both cells and each fits one and misses the other.', closedBy: 'a melee cell where the attacker cannot be hit back, which would separate "the split changed" from "the attacker\u2019s output attenuated". Nothing on the form provides one \u2014 melee is exactly where return fire exists \u2014 so the likelier route is a third stack: put a friendly stack of known pool inside the blast at 0 km and read its share directly, the way the friendly-fire cell did at 10 km.' },


    { key: 'air_to_air_mechanism', what: 'WHY an air stack is attenuated against surface targets and not against other aircraft.', why: 'The scope is measured hard and modelled. Attacking land or naval, an air stack fires with what survives the round; attacking air it does not \u2014 twenty fighters lose 58% of their pool to two hundred fighters and still deal the full 20.0 x E(20) = 400.00. Embarkation is seen by every attacker including air, which is what the discriminating cell showed: against two hundred EMBARKED fighters the same stack deals 98.61, the naval column attenuated. What no black-box reading can reach is the mechanism \u2014 whether air-to-air resolves simultaneously or whether something else exempts it.', closedBy: 'nothing available. The obvious experiment is an air stack whose target cannot shoot back, and there is no such configuration: every air unit bisects to a range of 5 km and 5 km is exactly where return fire stops, so an aircraft is never out of reach of what it is attacking' },
    { key: 'return_fire_generality', what: 'Whether the 5 km return-fire cut-off is a constant or every unit\u2019s own melee reach.', why: 'Past 5 km a bombarded defender deals exactly zero while still taking the attacker\u2019s full figure. That is measured hard \u2014 lart at 4 and 5 km loses 20.00, at 6, 7 and 8 km loses nothing, and three defenders that could easily shoot back (lart reaching 30, cruiser 40, battleship 75) are all silent at 8 km, as is a mixed inf+lart defender at 6. But every unit in the roster ALSO bisected to a melee attack range of exactly 5, so "the cut-off is the constant 5" and "the cut-off is the defender\u2019s own melee reach" predict the identical number everywhere. The two are indistinguishable in this game and the engine uses the constant.', closedBy: 'nothing available \u2014 it would need a unit whose melee reach is not 5, and there is none' },

  ];

// ---------------------------------------------------------------------------
// PROVENANCE
// ---------------------------------------------------------------------------
// Free-form notes keyed by constant name. Every note says where the number was
// measured, how well, and what it is NOT evidence for.

export const PROVENANCE = {
  'FORTRESS.dr.lowSegment': {
    confidence: 'measured',
    source: 'results.jsonl \u2014 73 distinct (fortress HP, DR) pairs already on disk from every sweep that ever put a fortress on the board, plus experiment=fortress_dr_low, twelve requests to pin the floor.',
    method: 'The site PRINTS its own damage reduction on the building row, dr_before and dr_after. This project has been parsing and recording those two fields since the first fortress request and had never read them. DR = 0.15 x (hp/50 + 1) is exact for all 58 archived readings at 50 HP and above and wrong for all 13 below it, by up to eight points. Below 50 the site is on a second straight line, DR% = 5 + 0.5 x hp, which meets the first exactly at 50 HP and 30%. The ladder read seven fresh points from 10 to 48 HP off the DR column directly \u2014 10.0, 10.5, 12.5, 17.5, 22.5, 27.5, 29.0 \u2014 every one exact, no inference through a damage figure at all.',
    tolerance: 'Exact at every point, on both segments. The floor is a STEP, not a taper: 9.5 HP renders no DR clause at all (the same signature a building that confers nothing gives) and 10 HP renders 10.0%.',
    notEvidenceFor: 'Any building but the fortress \u2014 the other seven mitigate nothing at any HP. Nor a fortress above 250: the 0.90 ceiling is read at 250.4 and 251.3 HP, where the formula would want 90.1 and 90.4, and nothing was submitted higher.',
  },
  'FORTRESS.dr.blindSpot': {
    confidence: 'measured',
    note: 'Every fortress this project ever SUBMITTED was at 100% of a whole level, so a pool below 50 arose only as the last gasp of one being ground down \u2014 which is to say, only in the closing rounds of a long battle, and only in the handful of runs that lasted that long. The single-formula DR was therefore right for every number anyone had checked and wrong for the ones nobody could. That is the fifth time in this project a law survived only because the data had never varied the axis that would break it, and the third time the axis was \u201cthe thing is damaged\u201d. The others: a building\u2019s HP bar read as a fraction of the whole pool, a damaged row\u2019s HP fraction multiplied in twice, and a hero\u2019s output frozen at its opening HP.',
  },
  'FORTRESS.dr.foundBy': {
    confidence: 'measured',
    note: 'Chased for two sweeps as a \u201clate-round output drift\u201d in the ATTACKER \u2014 2.2%, 5.6%, 8.3% from round seven \u2014 because the attacker\u2019s state matched the site exactly at the start of every one of those rounds, so the error had to be in the output term. It was not: the output was right and the DEFENDER\u2019s mitigation was wrong. What settled it was reading the site\u2019s own DR column instead of solving for it. The lesson is cheap and worth writing down: when a quantity will not reproduce, check whether the source PRINTS the intermediate before deriving it from the total. Seventy-three readings of the answer were already in results.jsonl.',
  },
  'DAMAGE.perRowCapOnly': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=fort_drift round 9.',
    method: 'A round\u2019s full swing goes to the allocation and each ROW is capped against what it has left; the side total falls out of the split. Capping the total at the side\u2019s remaining pool FIRST shrinks every row\u2019s share, the hero\u2019s included: with 10.5 HP of armoured cars and a hero on 42.4, a 74.2 swing was cut to 52.9 before being divided, giving the hero 15.1 where the site takes 21.2. The side-level cap is redundant once each row is capped \u2014 the shares cannot sum past the pool by construction \u2014 and it was doing harm on its way to being redundant.',
    tolerance: 'Exact. With this and the DR segment, every real-army row reproduces: worst relative error 0.0034% across all round counts, both hero levels and three fortress pools.',
    notEvidenceFor: 'The allocation WEIGHTS, which are unchanged, or the discard rule, which was measured separately in the same round.',
  },
  'DAMAGE.surplusDiscarded': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=fort_drift \u2014 the site\u2019s own per-round form readback, rounds 1-9, plus an isolated reproduction away from the real army.',
    method: 'A row that cannot absorb its share of a round DISCARDS the surplus; it is not passed to the other rows. The defender enters round 9 with 10.5 HP of armoured cars and Kangal on 42.4, the attacker swings about 74, and the site\u2019s readback has the cars at 0 and the hero at 21.2 afterwards \u2014 31.7 applied, the rest dropped. Splitting 74 by the measured weights (one armoured car at 1.00 against a hero at 0.40) puts 0.2857 of the swing on the hero, which is the 21.2, and caps the cars at the 10.5 they had.',
    tolerance: 'Exact in the isolated cell, which is the one that matters because it is free of the late-round residual: six heavy tanks against five infantry, a hero and a level-5 fortress take the fortress to 208.31 here against 208.3 printed. The engine said 157.78 before the fix \u2014 a 50 HP miss \u2014 because the hero soaked a round\u2019s worth of surplus and died with the troops instead of buying a fourth round.',
    notEvidenceFor: 'What happens when the SIDE as a whole cannot absorb a round while individual rows still can, which is a different cap and is unchanged. Nor for any redistribution rule at all \u2014 the finding is that there is none.',
  },
  'FORTRESS.residual.closed': {
    confidence: 'measured',
    note: 'For as long as the real-army rows had been on file this suite printed \u201cthe site finishes the fortress; this model leaves it at 97-100%\u201d. The fortress was never the defect. Everything about the building was already right \u2014 the per-round rate matched the site at every round it had been asked for, and exp_bughunt had settled the stop condition directly \u2014 and the missing 6.17 HP was the visible end of a surplus-damage rule one row away. Ten rows at three different pools now reproduce exactly, and the check is an assertion instead of a report. Recorded because the shape recurs: the number that will not reproduce is often the READOUT of a defect rather than the defect, and the cheapest move was reading what the archive already said before spending a request.',
  },
  'FORTRESS.residual.remaining': {
    confidence: 'superseded',
    note: 'SUPERSEDED. This recorded that fixing the surplus rule had made the worst fought-out attacker total WORSE as a percentage \u2014 1.37% where the bound had been 1% \u2014 because the battles now ran the extra round the site runs and carried more of the late-round residual with them. That reading was right and the residual is now closed: it was the fortress DR curve below 50 HP, not anything in the attacker. The bound is 0.05 HP, and the worst relative error across every real-army row is 0.0034%. Kept rather than deleted because the entry did its job \u2014 it said plainly that a bound had gone up, which is what made the residual worth another sweep instead of a shrug.',
  },
  'BATTLE.stopCondition': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=bughunt, prongs fortress_after_garrison (6) and building_grind_no_deaths (4).',
    method: 'A battle ends when a side has no UNIT pool left, and nothing else ends it. Six heavy tanks kill five infantry behind a level-5 fortress by round 3, leaving 90.2 HP of fortress standing; asking for 5 rounds, 8 rounds and 100 returns the byte-identical result. The converse was read in the same sweep: ten heavy tanks destroy a level-5 fortress at round 3 with the garrison alive and round 4 goes ahead and wipes them, so a destroyed building does not end a battle either.',
    tolerance: 'Exact, and the 100-round cell is what makes it exact rather than suggestive \u2014 a stop condition that were merely LATE would show somewhere between 5 and 100 rounds, and one that never fired would grind a 90 HP fortress to nothing many times over.',
    notEvidenceFor: 'A garrison that includes a HERO. Both prongs fielded bare units, so \u201cno unit pool left\u201d and \u201cno HP left at all\u201d were the same condition and nothing here could separate them. exp_fort_drift later fielded the same shape with a hero and they are NOT the same: the site ends round 9 with the units at 0 and the hero on 21.2, and fights round 10. A hero is part of the garrison for this rule, which is what the engine\u2019s pool test already said and what this prong could not confirm. Nor is it evidence about the real-army residual it was built to test \u2014 that suspect is cleared, and the cause turned out to be one row away, in what happens to damage a saturated row cannot absorb.',
  },
  'BUGHUNT.sweep': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=bughunt \u2014 eighteen cells, predictions computed from web/engine.js and written to disk before the first request.',
    method: 'Cells chosen where the ENGINE was most likely to be wrong rather than where a law is cleanest. Counting the rounds column by experiment shows nearly every sweep in this archive is maxRounds=1 \u2014 trenches, buildings, allocation, saturation, terrain, heroes \u2014 so a law that is right for one round and applied wrongly on the second is invisible in the record. That is the class of defect the real-army run turned up six of. Three prongs: a fortress outliving its garrison, a trench over five round counts at two levels, and a building ground down with the garrison intact.',
    tolerance: 'Eighteen of eighteen to the printed decimal, attacker, defender and building alike.',
    notEvidenceFor: 'The engine being free of defects. It means these eighteen cells did not reach one. What it does establish is that two axes that had never been exercised at all \u2014 a trench past round one, and a building ground down over rounds \u2014 are now assertions rather than hopes.',
  },
  'RIG.dryRunPollution': {
    confidence: 'measured',
    note: 'Found while dry-running this sweep, before a request was sent: --dry-run appended eighteen rows of NOTHING to results.jsonl. record() is called unconditionally by every experiment, and a dry run has no readings to record. They are not wrong measurements, they are not measurements \u2014 and a reader replaying the archive could not tell "the site returned no reading" from "nobody asked the site". The eighteen were removed and record() now refuses while a dry run is in progress. The guard cannot key on the readings being empty, because they legitimately are in hero_hp_cap and hero_caps, whose 152 blank rows record server REFUSALS; it keys on whether a request was actually sent.',
  },
  'MULTI_STACK.laws': {
    confidence: 'measured',
    source: 'results.jsonl, experiments=multi_stack (5), multi_stack_idle (1), multi_stack_focus (1) \u2014 seven requests, all ten-infantry stacks so every figure is a clean multiple of a known one.',
    method: 'Each of the help page\u2019s three multi-stack claims was turned into a pair of configurations differing in ONE thing, and the prediction was written down first. Co-location: A.1 attacks B.1 with B.2 idle beside it \u2014 A.1\u2019s 40.0 comes back as 20.0/20.0 and A.1 takes 50.00 + 50.00. Concentration: A.1 and A.2 both on B.1 \u2014 80.0 taken, 50.0 and 40.0 dealt back, the second attacker paying 0.8 of the first because the defender has lost a fifth of its pool answering the first. Inheritance: the same level-5 fortress with B.2 at 0 km and at 1 km \u2014 4.2/4.2 against 4.3/38.9.',
    tolerance: 'Exact to the printed decimal on the two laws with independent arithmetic. A.1 takes 100.0 against a predicted 50 + 50; A.2 takes 90.0 against a predicted 45 + 45; B.1 loses 80.0 against a predicted 40 + 40. The convoy exception is exact in the strongest available sense \u2014 adding the fortress moves B.1 from 27.6 to 2.9 and moves the convoy from 52.4 to 52.4.',
    notEvidenceFor: 'Any of it at three or more stacks, at distances other than 0 and 1 km, or with the two co-located defenders differing in unit type from each other \u2014 the split across co-located defenders was read on identical stacks, where an even 20.0/20.0 cannot distinguish \u201chalf each\u201d from \u201cby pool share\u201d from \u201cby target factor\u201d. The convoy run is the one cell with unlike defenders and it splits 27.6/52.4, which is not even; that is a real observation and it is not enough to fix a rule.',
  },
  'MULTI_STACK.armyTable': {
    confidence: 'measured',
    source: 'multi_stack_response.html \u2014 a captured two-stack-a-side response, committed as an offline fixture.',
    method: 'Document order is A.1, A.2, TABLE, B.1, B.2, TABLE. The table after A.2 reads 190.0, which is A.1\u2019s 100.0 plus A.2\u2019s 90.0, not A.2\u2019s 90.0. Its \u201cHP final\u201d column reads 210.0 and 210 + 190 = 400, the two stacks\u2019 pools together. The site had also been saying it in a tooltip since the first request: \u201cThe total hit points lost by all the stacks during the battle.\u201d',
    tolerance: 'Exact, and now asserted offline against the fixture rather than inferred.',
    notEvidenceFor: 'Any reading already on disk being wrong. Every one of the 2,585 single-stack readings had exactly one stack an army, so its army total IS its stack total; the parser keeps the stack-keyed alias for that case precisely so nothing already recorded has to be re-read.',
  },
  'RESULTS.staleAssertion': {
    confidence: 'measured',
    note: 'test_result_table.py asserted \u201cone summary per stack\u201d for 2,585 readings and it passed every time. It was wrong from the first line: the table is an ARMY total and every army had one stack. This is the same failure the file was written to catch, one level up \u2014 a hand-written claim about what is known goes stale in exactly the way a hand-written constant does, and passes right up until the day the data varies the axis it was never tested on. The assertion was not deleted; its label changed with it, so the diff shows a claim being overturned rather than a list being widened.',
  },
  'RESULTS.headerSpelling': {
    confidence: 'measured',
    note: 'The site changed its own summary header mid-project: fortress_result.html carries \u201c% lost\u201d and the later multi_stack_response.html carries \u201c%lost\u201d, with a new \u201cHP final\u201d column added in between. A literal header match filed one quantity under two keys \u2014 pct_lost on 128 stored rows, lost on 284 \u2014 and \u201clost\u201d is already the span reading\u2019s name for HP, so a percentage and a hit-point count were one key collision apart. Nothing downstream had read the column yet, so nothing on disk is wrong. The lookup now ignores internal whitespace; rows already captured keep the key they were captured with and summary_pct_lost() reads either, because a measurement archive that gets edited after the fact stops being evidence. The provision that saved the new column was the slugify-don\u2019t-drop rule for unknown headers, written two thousand readings before there was a column to save.',
  },
  'ALLOCATION.survivors': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=update_counts_army \u2014 the site\u2019s own post-round counts, read back through updateCounts.',
    method: 'At round two the site splits incoming damage 0.4572 / 0.1887 / 0.3542 across 29 infantry, 6 armoured cars and 15 cavalry. Weighting by survivors predicts 0.4567 / 0.1890 / 0.3543; weighting by the opening counts of 35 / 6 / 17 predicts 0.4828 / 0.1655 / 0.3517. There is nothing to argue about.',
    tolerance: 'Exact: with survivor weighting the engine reproduces every row\u2019s count AND remaining HP for four consecutive rounds.',
    notEvidenceFor: 'The target factors themselves, which are unchanged \u2014 infantry 0.50, cavalry 0.75, a hero 0.40, everything else 1.00. Only the count they multiply was wrong. Invisible in the record twice over: in round one nothing has died yet, and a single-type stack takes everything however it is weighted \u2014 and every mixed-stack reading on file is a single round.',
  },
  'HEROES.ownHpDecays': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=update_counts_army.',
    method: 'The form comes back with the hero\u2019s own HP in it. Kangal enters round two on 79.5 of 90 and contributes 20 x m(0.8833) = 17.78; this engine was charging 20 x m(83.1/90) = 18.54, its opening figure.',
    tolerance: 'Exact. The engine now tracks the hero\u2019s HP against the server\u2019s readback to the printed 0.1 for four rounds running.',
    notEvidenceFor: 'The BUFF, which does not scale with the hero\u2019s HP and is unchanged. That a hero\u2019s own output scales with its HP at all was measured earlier; what was wrong was applying it once at setup instead of every round.',
  },

  'BUILDINGS.hpBar': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=fortress_hp_scale \u2014 four settings of the same level-4 fortress, one round each.',
    method: "Ask the field what it counts. '5' and '10%' produce the byte-identical battle, and so do '50' and '100%', so the bar is 0-50 WHATEVER the level and a percentage is a percentage of that band, not of the pool. The site prints its own damage reduction on the building row, which converts straight back to a pool through DR = 0.15 x (hp/50 + 1): 75.0% is 200 HP and 61.5% is 155.",
    tolerance: 'Exact. pool = (level - 1) x 50 + top-band HP reproduces all four settings, and it is the same arithmetic the site uses to REPORT a battered fortress \u2014 one reading on file has a 250 HP fortress emerge from a round as \u201clevel 5, 41.5\u201d, which is 4 x 50 + 41.5 = 241.5.',
    notEvidenceFor: 'Buildings whose levels are not uniform. One of them holds 35 HP at level 3 with 20 in the top level, so it has no 50-HP band to take a percentage on; for those the engine keeps the old proportional reading and says so.',
  },
  'BUILDINGS.hpBar.correction': {
    confidence: 'measured',
    note: 'This engine read a building\u2019s HP percentage as a fraction of the WHOLE pool, which is the same number at 100% and wrong at every other value. Every fortress ever measured here was entered at 100%, so nothing in the record could separate the two readings \u2014 the third time in this project that a law was right only because the data had never varied the axis that would break it. A level-4 fortress at 5/50 came out as 20 HP and 21% damage reduction where the site gives 155 and 61.5%.',
  },
  'RESULTS.relabelled': {
    confidence: 'measured',
    note: 'Five real_army rows carried meta.fortress = "lvl4 hp5" while their payload had actually sent 100%: the edit meant to set the fortress HP had landed in a different experiment, and the metadata was written from the variable rather than from what was submitted. The readings themselves are sound and duplicate the earlier full-fortress runs exactly, so they were RELABELLED from the building row rather than deleted \u2014 a fortress pool of 200 is full, 155 is 5/50 \u2014 and each carries a `relabelled` field saying so. Recorded because a mislabelled row is worse than a missing one: it replays silently against the wrong configuration and blames the model.',
  },

  'REAL_ARMY.validation': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=real_army \u2014 two armies read off a player\u2019s own screen, submitted to the live site at 1, 2, 3, 5, 6, 7, 8, 10, 20 and 100 rounds.',
    method: 'End-to-end rather than isolating: 35 infantry at 453.6/700 plus 6 armoured cars and 17 cavalry, all damaged, attacking 12 armoured cars with Orhan \u201cKangal\u201d Demir behind a full level-4 fortress. Every other measurement in this project isolates ONE law, which is exactly what makes a law that is individually right and wrongly COMBINED invisible.',
    tolerance: 'Round 1 exact to the printed 0.01 on both sides, both hero levels, and on the fortress, at BOTH fortress levels submitted. Agreement holds while both sides are healthy and decays as the loser nears death \u2014 which is a better predictor than the round number, since a level-3 fortress falls sooner and its round 5 sits as deep into the battle as a level-4\u2019s round 7. At the corrected level 3 the model is exact at round 1, 0.5% out at round 3, 1.4% at round 5, and 1.6% on the attacker\u2019s total in a battle fought to the end \u2014 with the defender\u2019s total and the fortress both exact.',
    notEvidenceFor: 'Anything about the live GAME beyond one striking agreement. The player\u2019s in-game panel reads 62% fortification; the fortress turned out to be level 4 at 5/50 on its bar, and the site gives that exactly 61.5%, which this engine reproduces. Two earlier readings of the same fortress \u2014 level 4 full (75%) and level 3 full (60%) \u2014 were both wrong, and each briefly looked like a site-versus-game divergence. It was neither; it was the building being specified wrongly, twice.',
  },
  'REAL_ARMY.endgameDrift': {
    confidence: 'measured',
    source: 'results.jsonl, experiments real_army and update_counts_army.',
    note: 'LARGELY CLOSED, and by the switch nobody had ever flipped. The attacker\u2019s cumulative loss used to run 0.8% out by round 5 and 5% by round 10; it is now 0.30% on a battle fought to the end. Turning updateCounts on makes the site rewrite the returned FORM with its own post-battle counts and HP, which turned an argument about compounding into a per-round comparison and found two causes at once. Incoming damage is split across rows by (target factor x SURVIVING count) and this engine weighted by the count the battle STARTED with; and a hero\u2019s own output scales with its own HP, which was baked in once from its opening HP so the hero fired at full strength all battle. With both fixed the engine reproduces the site row by row and the hero too, exactly, through round four; round five \u2014 where the defender drops from five units to two \u2014 still parts by about 8% on that one stack, and what remains of the drift is there.',
  },
  'BUILDING_DAMAGE.perRow': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=real_army, round 1.',
    method: 'Every building sweep before this used a SINGLE-TYPE stack, where \u201cone rate times the stack\u2019s effective units\u201d and \u201ceach row\u2019s rate times its own effective units, summed\u201d are the same number, so nothing in the record could separate them. A mixed army separates them at once: 35 infantry at 0.30 (12.15 effective), 6 armoured cars at 1.00 (5.85) and 17 cavalry at 2.00 (17) give 38.06 by the row sum against 10.41 for a single infantry rate, and the site prints 38.1.',
    tolerance: 'Exact to the 0.1 the building row prints.',
    notEvidenceFor: 'A mixture containing a unit whose rate was never read. One unmeasured row makes the whole total unknown and it is withheld, not summed over the rest.',
  },

  'MUTUAL.law': {
    confidence: 'measured',
    source: 'results.jsonl, experiments mutual / mutual_law / mutual_order / mutual_control / mutual_rounds \u2014 34 requests.',
    method: 'Two-configuration decomposition, then prediction. The law was written from four readings and used to predict eight more BEFORE they were submitted, across units whose attack and defence columns differ by up to four times and in both directions \u2014 st is 25.0/6.3 and ac is 6.0/12.0, so a rule that merely inflated everything fails the armoured car on the first cell. All sixteen came back to the printed decimal, as did the two-round and three-round ladders.',
    tolerance: 'Exact to the 0.01 the summary table prints.',
    notEvidenceFor: 'Mutual attacks involving a fortress, a building or a hero. No mutual reading on record carries one, so engagement 2 applies none of them and says so.',
  },
  'MUTUAL.sideLetter': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=mutual_order.',
    method: 'The mirror keeps the ROLES and moves the stacks between armies: A=inf attacking / B=st defending against A=st defending / B=inf attacking. Both print 63.00 and 40.00.',
    tolerance: 'Identical to the printed decimal, so the page\u2019s claim that the side letter is inert one-sided is confirmed rather than assumed.',
    notEvidenceFor: 'Mutual battles, where the side letter is worth up to a whole stack. An earlier version of this experiment compared A=inf-attacking against A=inf-DEFENDING, which are two different battles rather than a mirror, and reported that the page was wrong. That verdict was a defect in the rig, and it is recorded here because the rig produced a confident false finding from a control that did not control for anything.',
  },

  'BOMBARDMENT.mechanism': {
    confidence: 'measured',
    source: 'results.jsonl, experiments bombardment / bombardment_law / bombardment_own / bombardment_finish / bombardment_lucien2 / bombardment_melee / bombardment_friendly / togo_buff_clean \u2014 about 100 requests.',
    method: 'Isolation by RANGE. Submarines are melee, so with the target at 10-50 km the stack cannot reach it and every point of damage the target takes is the hero and its ability, with no subtraction of a baseline. That is what the earlier sweeps could not do: all 191 T\u014dg\u014d and Lucien readings on file were taken in melee, so each was a subtraction of a no-hero control from a total that also contained the stack\u2019s own damage \u2014 and a hero takes a slot in the saturating stack, so the two sides of that subtraction do not even have the same E(n).',
    tolerance: 'Exact. The radius sweep reproduces to 0.01 (56.39 and 65.00), the split across five attacker sizes to 0.06, the twelve-rung level ladder to the printed decimal, and the buff cell returns the ability total to 0.00 at five levels.',
    notEvidenceFor: 'The melee split at 0 km, which is measurably NOT pool share and is declared in NOT_MEASURED. Nor for any hero outside these two.',
  },
  'BOMBARDMENT.discovery': {
    confidence: 'measured',
    source: 'share/s1914.info.html \u2014 the site author\u2019s own help page, linked from every control on the form under thirteen distinct anchors, two of which are #togo and #lucien.',
    method: 'Read it. Five audits had gone by on the premise that the server authors two inventories \u2014 the fields it accepts and the columns it prints \u2014 and that both were now swept. There is a third, and it is the only one that describes INTENT rather than shape.',
    tolerance: 'The page is prose written by a person about software that changes, so nothing here is recorded because the page says it. Every claim it makes was turned into a number the server had to produce, and the page\u2019s own suggestion \u2014 "put its position more than 5 km from the target and within 40 km" \u2014 is what made the isolation possible.',
    notEvidenceFor: 'Anything the page says that was not then measured. It also documents an "Army A attacks first" ordering rule for mutual attacks, and NO mutual attack has ever been submitted by this project: duel() is the only thing that ever sets a B-side target and it always sets 0.',
  },
  'BOMBARDMENT.corrections': {
    confidence: 'measured',
    source: 'The same sweeps.',
    note: 'Two constants that were in this file and wrong, both artifacts of the same conflation. T\u014dg\u014d-with-bombardment\u2019s own attack was 64.90; it is 15.00, and 64.90 was 15.00 plus the whole ability at a pool ratio where the target absorbed all of it. And it carried TWO battleship buff curves, one per side \u2014 1.2944 attacking against 1.30 defending \u2014 with a note saying no other hero in either table needed such a thing. It does not either: the attacking curve had been fitted to readings with the ability folded in, so it absorbed the shortfall as a smaller multiplier. Measured at 50 km, where battleships still reach 75 but the attacker sits outside the 40 km blast, the togo_b minus togo difference is 10.00, 25.00, 50.00, 75.00 and 100.00 at levels 1, 5, 10, 15 and 20 \u2014 the ability exactly, five times, so the buffs are the same buff.',
  },
  'HERO_REACH': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=bombardment and bombardment_lucien2.',
    method: 'Ten submarines at 0 km against a target at 10-50 km return NO result rows at all with no hero aboard \u2014 the server does not fight an out-of-range battle. Put a hero in the same stack and the target loses 15.00 a round at every one of those distances.',
    tolerance: 'Floors, not values. T\u014dg\u014d fires at 50 km and nothing further was submitted. Lucien fires at 50 and is SILENT at 75, which is what proved the ability has a range of its own: at level 15 the ability lands its full 40.00 at 75 km where the hero itself contributes nothing.',
    notEvidenceFor: 'Any other hero. Only these four were put out of range.',
  },

  'REPAIR.law': {
    confidence: 'measured',
    source: "results.jsonl, experiment=repair_cost (17 wipes, one per unit, n=100) and repair_damaged (2). Plus 256 complete resource rows and 2,719 'hours' readings already in the corpus from sweeps aimed at other things -- the scraper stored them from the start and nothing ever read them back.",
    method: "A WIPE, deliberately. Every other sweep here refuses a >=99.9% reading because a wiped stack's damage is censored; nothing about that applies to unit equivalents, which on a wipe are exactly the integer count with no rounding at all. n=100 pins each hours constant to 0.01 in a single request, where an unwiped reading inherits only the 3 significant figures of the printed percentage.",
    tolerance: 'Resources are exact: predicted and printed agree to the integer over 187 readings whose ue is exactly recoverable (from cash / cash-cost). Hours are floored, so each constant is an interval of width <=0.01 and the midpoint is quoted; several constants are NOT the clean number beside them -- int excludes 32.40 exactly, zep lies in [40.79, 40.80), lart in [9.97, 9.98).',
    notEvidenceFor: "That the bill tracks HP LOST. It does not, and every full-HP reading in the corpus is consistent with both, which is why this went unnoticed. Two readings separate them: the trench sweep (40.0 HP lost at every level, hours falling 6->4 as the pool grows) and twenty artillery at 10% HP, which lose a tenth of the HP and are billed identically. Also not evidence about buildings, which are excluded, or about heroes beyond the two measured.",
  },
  'REPAIR.rounding': {
    confidence: 'measured',
    source: 'results.jsonl, all readings with an exactly recoverable ue.',
    method: 'Three candidate rules fitted per unit as interval intersections. floor is consistent for 16 of 16 units; ceil for 1; round for 3. Separately, 34 readings whose predicted fractional part exceeds 0.55 print the floor and 1 prints the round.',
    tolerance: 'The stack total is floored ONCE, not per row. The discriminating reading is the two-row 62-hour stack in mixed_stacks: 4.41 + 57.60 floors to 62, where flooring each row gives 61.',
    notEvidenceFor: 'The resource columns, which are rounded to the nearest integer rather than floored.',
  },
  'REPAIR.scope': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=repair_building (2) and repair_hero (2).',
    method: 'Self-contained rather than controlled: each request is compared against the bill predicted from its OWN unit rows, so the fortress changing the infantry losses is not a confound. A fortress that lost 180 HP moved neither a resource cell nor the hours (predicted 14.89 from the infantry alone, printed 14). A hero that lost 66.7 HP took the same stack from 33 hours to 81.',
    tolerance: 'Exact -- both are presence/absence, not magnitudes.',
    notEvidenceFor: 'Anything about buildings other than the fortress, though the HP column already excludes every building type and the bill follows the HP column exactly.',
  },
  'REPAIR.hero': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=hero_repair (2 heroes x 3 strengths) and hero_repair_all (22 heroes x 2 strengths).',
    method: "Vary how hard the hero is hit and the two candidate shapes diverge at once. A first pass took two heroes at three strengths each; the whole table was then swept at two strengths each -- 44 requests, sea and air heroes in their own terrain against a screen of their own class -- rather than generalising from two agreeing heroes. Proportional-to-own-ue survives for all 22 and the intersection of their brackets is [71.87, 72.41).",
    tolerance: 'One shared constant covers all 22, which is unusual in this game -- every other hero coefficient measured here differs per hero, sometimes by a factor of ten. Four heroes (tatiana, tatiana_home, maeve, ivan) report "flat charge survives", but that is a test with no power rather than support: both their readings wiped the hero, so ue_hero was 1.0 twice and the two hypotheses predict the same number.',
    notEvidenceFor: 'Hero RESOURCE cost. There is none: the cells stayed at zero against free infantry while the hero bled.',
  },
  'FIELD.outputCoverage': {
    confidence: 'measured',
    source: 'The response fixture and results.jsonl.',
    note: "The fourth audit checked that every field the server ACCEPTS had been exercised. This is its mirror: every column the server PRINTS. The result table has eleven; the project consumed two. The other nine had been parsed and stored since StackSummaryScraper was written -- its COLUMNS comment says unknown headers are slugified 'so a column dxter adds later shows up as data instead of vanishing' -- and never read back once. The probe's module docstring listed them as open and the gap list in this file had dropped the entry entirely, so no inventory this project wrote could have surfaced it.",
  },

  precision: {
    confidence: 'measured',
    note: 'The source page prints HP lost to 0.1 in each unit span and to 0.01 in the summary table, and percentages to 3 significant figures. A stack POOL is never printed: it is pool = lost / pct, so every pool is an interval whose width is set by the percentage. Quoting a derived pool to 2 decimal places is a documented failure mode of this project (HANDOVER.md), committed by HANDOVER.md itself in its trench section.',
  },

  'UNITS.diagonal': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=unit_stats: 68 rows = the 17-unit roster flown FOUR times (timestamps 1786960631 / 1786963878 / 1786981063 / 1786981460), byte-identical readings every time. HANDOVER.md says three runs; the file holds four.',
    method: 'Each row is a 10 v 10 duel of a unit against itself, so E(10) = 10 and m(1) = 1 and the coefficient is simply reading / 10.',
    tolerance: '±0.005 per unit (the span prints HP lost to 0.1, divided by E = 10). art 2.7, rrg 6.7 and st 6.3 sit at that limit and should carry it.',
    notEvidenceFor: 'ANY off-diagonal pairing. Attack is per-target-class — tac is 3.0 against air and 30.0 against ground — so a diagonal value says nothing about a different target.',
  },
  'UNITS.maxHP': {
    confidence: 'derived',
    source: 'results.jsonl, experiment=unit_stats, meta.max_hp_bounds (fourth run).',
    method: 'The reading is the BRACKET (lost/pct/n, widened by both print precisions). The integer is an inference from "the bracket holds exactly one whole number", which is true for 16 of 16 units that have any reading at all.',
    crossCheck: 'For 13 of those 16 the air_vs_ground pools give a second, independent bracket around the same integer.',
    note: 'DERIVED, and it cannot be anything else. A stack\'s POOL is never printed: the page gives '
      + 'HP lost and a percentage to three significant figures, so pool = lost/pct is an INTERVAL and '
      + 'max HP is that interval over the count. Every value in the table is the unique integer inside '
      + 'its interval. More requests do not sharpen it — the binding constraint is the percentage\'s '
      + 'significant figures, not the number of readings, which is a distinction this project got wrong '
      + 'once already: unit_stats was re-run on the promise that the summary table would sharpen these '
      + 'into clean integers, and it could not.',
    caution: 'results.jsonl does not store the pool and percentage that produced meta.max_hp_bounds for unit_stats, so those brackets cannot be re-derived from the file — the conclusion is on disk, the evidence is not. Do not display bracket midpoints (175.44, 260.12, 60.06): they are measurements of nothing.',
  },
  'UNITS.maxHP.formDefault': {
    confidence: 'derived',
    source: 'As UNITS.maxHP, plus independent confirmation: 175 and 260 are the stock form\'s own default HP values in last_response.html.',
  },
  'UNITS.maxHP.noIndependentCheck': {
    confidence: 'derived',
    source: 'As UNITS.maxHP, but weaker: sub, cl and bb appear only in unit_stats. No row anywhere else in results.jsonl constrains their max HP, so the integer rests on a single bracket whose own inputs were not recorded.',
  },
  'UNITS.balloon': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=balloon: four requests in LAND terrain.',
    note: 'maxHP 20.0, attack 3.0, defence 3.0. Unmeasured for the whole project not because '
      + 'the unit is special but because every attempt sent it in AIR terrain, where the batch '
      + 'aborts server-side with no error at all and the probe now refuses to send it. In LAND '
      + 'terrain it runs perfectly: 10 balloons deal 30.00 to 20 infantry AND to 20 heavy tanks '
      + '(flat across targets, like every other unit within a class), 20 infantry deal 30.00 '
      + 'back, and the balloons\' pool reads 200.0 for ten. A null result was a rig fault for '
      + 'the eleventh time in this project.',
  },

  'AIR_ATTACK_VS_GROUND': {
    confidence: 'derived',
    source: 'results.jsonl, experiment=air_vs_ground: 30 cells (3 fliers x 10 ground targets), one session.',
    method: 'Invert the post-fire output law (see RETURN_FIRE) on each cell. All ten targets return the same value for a given flier, exactly.',
    residual: 'Worst 0.005 HP across all 30 cells, which is exactly half a print unit of the summary table\'s 2-decimal figure. Re-derived in this session from the raw readings, not copied from prose.',
    supersedes: 'HANDOVER.md §4 reports these as ranges (5.000-5.022 / 30.000-30.121 / 5.001-5.016) because it uses an approximate return-fire law. Under the correct law the spread is zero. The headline numbers 5 / 30 / 5 were right; the formula that produced them was not.',
    note: 'Flat across every ground target. The "Bomber does 0 damage to heavy tanks" report that motivated the experiment is not reproducible.',
  },
  'GROUND_DEFENCE_VS_AIR': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=air_vs_ground: attacker-side HP lost / E(defender count).',
    method: 'Each of the ten values is confirmed by THREE independent attackers (int, tac, zep). Spread across the three is 0.00e+00 in every case.',
    note: 'This is a ground unit DEFENDING against air. A ground unit ATTACKING air is unmeasured. Note the spread: ac at 8.0 is 20x lart at 0.2, which is exactly what made uncorrected readings look like target dependence.',
    tolerance: '±0.005 or better.',
  },
  'BUILDING_DAMAGE_PER_EFFECTIVE_UNIT': {
    confidence: 'measured',
    source: 'results.jsonl, experiments=fortress and buildings: 30 infantry take 8.5 HP off a building, and 8.5 / E(30) = 8.5 / 28.3333 = 0.3 exactly.',
    note: 'ONE unit type, at full HP, in every row. 0.3 is a data point, not a law — every buildings request used the same 30-infantry attacker. Nothing in the model predicts the 0.3 : 4.0 ratio against units, so it cannot be extrapolated. Building damage is additive: it is NOT carved out of the damage dealt to units, and it is NOT reduced by fortress DR.',
  },

  'E_n': {
    confidence: 'measured',
    source: 'Independently confirmed at n = 10, 15, 20, 29, 30, 45, 50, 57 and 113, all exact to print precision. The non-trivial fits are E(29) = 27.65 (st dealt exactly 27.65), E(45) = 34.5833 (cav dealt exactly 34.58), E(30) = 28.3333, E(50) = 35.',
    formula: 'E(n) = n for n <= 20; else 20 + k(60-k)/60 with k = min(n,50) - 20. Saturates at 35 effective units, so stacking past 50 does nothing.',
    note: 'The min(n,50) cap does real work: uncapped, n=57 predicts 13.67 where 14.0 was measured. EVERY RUNG IS MEASURED NOW. This used to list n in 21-28, 31-44, 46-49 and above 113 as untested, interpolated on the grounds that the curve is smooth and every gap is bracketed \u2014 a fair reason to interpolate and not a reason to call it measured, especially with the knee at 20 and the cap at 50 both sitting inside the untested ranges. All 22 were submitted: worst error 0.0032%, which is rounding of the second printed decimal. The cap holds out to n = 400.',
  },
  'm_f': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=hp_scaling: 10 points at 10% intervals, 10 infantry attacking 50 infantry.',
    formula: 'm(f) = 0.05 + 0.95f, f = current HP / full HP for the whole stack.',
    residual: 'ZERO deviation at all ten points.',
    note: 'The 0.05 floor is real: a stack at 10% HP deals 14.5% of full damage. The POOL scales linearly with f with no floor. BOTH AXES ARE MEASURED NOW. This used to say only the ATTACKER\'s HP had been swept, and only for infantry, so applying m(f) to a defender or to any other unit type was an assumption \u2014 the same shape as the four hero defects found the same week. Five unit types spanning per-unit HP from 10 to 260 and coefficients from 1.0 to 45.0, each swept at 100, 75, 50, 25 and 10 per cent on the attacking side AND the defending side: fifty cells, every one fitting to the printed precision. The two that look worst in relative terms, 0.174% and 0.055%, are half a printed decimal on figures of 2.88 and 18.11.',
  },
  'wiped_stack': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=hp_scaling: 8 of the 10 points have attacker_lost == attacker_pool, and all 8 sit exactly on the line set by the two survivors.',
    note: 'A land stack wiped inside the round still deals its full damage. The equivalent for an air attacker is unmeasured, and the post-fire law has no branch at zero survivors.',
  },
  'deaths': {
    confidence: 'measured',
    source: '81 of 81 stack readings across air_vs_ground, fortress and trenches agree.',
    formula: 'deaths = floor(HP lost / effective per-unit max HP), where "effective" means the TRENCH-INFLATED figure. At trench 4, 40.0 HP lost kills 1 infantry rather than 2, because per-unit HP has grown to about 23.',
    note: 'READ NOW, and it does clamp. The hp_scaling rows carry no death figure, which is why this stood open; the five-type rounds ladder does, and it contains wipes \u2014 light artillery and stormtroopers both lose their whole stack by round three and the server reports 50 dead of 50. The division alone gives 49, because the last round\'s floor leaves one standing, so the clamp is a rule rather than an artifact of the arithmetic.',
  },
  'RETURN_FIRE': {
    confidence: 'derived',
    source: 'results.jsonl, experiment=air_vs_ground: all 30 cells with readings.',
    formula: 'For an AIR attacker against a GROUND defender only, the attacker\'s output is evaluated on its state AFTER that round\'s incoming fire: deaths = floor(lost/maxHP); n_alive = n - deaths; f_after = (pool - lost) / (n_alive * maxHP); dealt = base * E(n_alive) * m(f_after).',
    residual: 'Worst 0.005 HP over all 30 cells — half a print unit, i.e. exact to the available precision. Re-derived from the raw readings in this session.',
    supersedes: 'HANDOVER.md §4 gives dealt = base * E(n) * (1 - own_fraction_lost). That law is refuted by the 30 cells it was fitted to: worst residual 1.12 HP against a display resolution of 0.005, wrong in 26 of 30 cells and always in the same direction. It coincides with the correct law only when the attacker\'s loss is an exact multiple of its max HP, which is why the two "clean" cells looked like confirmation.',
    note: 'This ADDS NO MECHANIC. There is no separate return-fire attenuation: it is the ordinary m(f) output law, evaluated post-fire instead of pre-fire. The pre/post asymmetry is the whole of the phenomenon. An equivalent form, dealt = base * sum over surviving units of m(f_i), fits identically — the two are algebraically the same whenever E(n_alive) = n_alive, i.e. for stacks of 20 or fewer, which is every stack ever measured. They diverge above 20 and nothing decides between them.',
  },
  'attenuation_scope': {
    confidence: 'mixed — see below',
    ground_defender: 'measured: the ground defender is never attenuated, even losing 26% of its pool in the round. Checked against the tac row on all 10 cells: every one dealt exactly stat * E(n_full). Post-fire evaluation would have predicted up to 20% less.',
    air_and_sea_duels: 'derived: air-vs-air and sea-vs-sea are NOT attenuated. Solving the 10v10 diagonals under attenuation forces int 29.925, tac 3.111, zep 5.176, sub 66.667, cl 12.5, bb 50; without it they are exactly 20 / 3 / 5 / 40 / 10 / 40. Every one of the 19 distinct stats measured in this project is a round number, so the unattenuated reading is right. This is an argument from roundness, not a reading — but it is strong enough to lift HANDOVER.md\'s "suspect" flag on the air rows.',
    cause: 'assumed: the consistent reading is that incoming fire resolves first against an air attacker only. The BEHAVIOUR is measured; the mechanism is a story.',
  },
  'FORTRESS.scope': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=close_out probe=fortress_class: land, air and naval '
      + 'attackers against a level-5 fortress, with a defender big enough not to be wiped.',
    note: 'The DR is UNIVERSAL across attacker classes: a level-5 fortress reduces a land, an '
      + 'air and a naval attacker\'s damage by exactly 90.00% each. An earlier attempt appeared '
      + 'to show 90 / 85 / 80 and that was entirely an artifact of CENSORED baselines - the '
      + 'fortress-0 defender was wiped at 400.0 of 400.0 in all three, so every "reduction" was '
      + 'measured against the same ceiling. It stacks with a trench (80.00 -> 8.00 at trench 10 '
      + 'and fortress 5), and it caps at level 5, which the server states outright.',
  },
  'FORTRESS.dr': {
    confidence: 'measured',
    source: 'results.jsonl, experiments=fortress (levels 1-5) and buildings (the L3 cell), reproduced on three separate runs.',
    formula: 'DR = 0.15 * (fortressHP / 50 + 1) FOR hp >= 50, continuous in CURRENT HP. At full HP that is 0.15 * (level + 1). Below 50 HP the curve is a second line \u2014 see FORTRESS.dr.lowSegment \u2014 and below 10 HP the fortress confers nothing.',
    residual: 'Observed defender loss ratios 0.6999 / 0.5499 / 0.3998 / 0.2498 / 0.0997 against 0.70 / 0.55 / 0.40 / 0.25 / 0.10 — every level within 0.002.',
    note: 'The "+1" discontinuity is in the game: having ANY fortress costs the attacker 15% before levels count. The page prints the decay directly — "DR: 60% -> 57.5%" for a level-3 fortress that has taken 8.5 damage, and 0.15*(141.5/50+1) = 57.45%. The round\'s damage uses the START-OF-ROUND value. Only the defender\'s UNITS are protected: the fortress\'s own damage is not reduced, and the fortress does not reduce the defender\'s output.',
    limits: 'Levels 1-5 only, and only against a land (infantry) attacker on the defending side. THE CEILING IS MEASURED NOW and it is 0.90, not the 1.0 this engine used to clamp to: the site prints 90.0% at 250.4 and 251.3 HP where the formula wants 90.1 and 90.4. The clamp at 1 had been chosen for being unarguable \u2014 a damage reduction above 100% is nonsense \u2014 which is two-thirds of the way to a measurement and was never worth stopping at, since the number was printed on the row.',
  },
  'BUILDINGS.inert': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=buildings: one request per type against 30 infantry.',
    note: 'The defender\'s loss ratio versus control is EXACTLY 1.00000 for all seven non-fortress types. This is a positive reading, not a silence: each type renders a result row and takes the same 8.5 HP, so the field demonstrably reached the server, and what is absent is the "DR:" clause.',
  },
  'BUILDINGS.fortressHP': {
    confidence: 'measured',
    source: 'Fortress pool read from its own result row at every level: exactly 50 / 100 / 150 / 200 / 250 at L1-L5. Damage comes off the top level.',
  },
  'BUILDINGS.hp.oneLevel': {
    confidence: 'superseded',
    source: 'One observation per type (railway/aerodrome/harbor L1 = 60, barracks L2 = 80, factory L3 = 120, recruiting L1 = 5.0 and destroyed outright by the 8.5 damage).',
    note: 'SUPERSEDED by BUILDINGS.levels, which measured every building at every level it has. The factory figure was 120/3 from a single reading and is now four: 40, 80, 120, 160. Only the fortress has HP per level confirmed at more than one level. "40 per level" for the factory is 120/3 from a single reading.',
  },
  'BUILDINGS.hp.workshop': {
    confidence: 'superseded',
    source: '35 HP total at level 3, with 20 in the top level.',
    note: 'SUPERSEDED by BUILDINGS.levels. The assumed series was right \u2014 the workshop reads 5, 15, 35 at levels 1, 2 and 3 \u2014 but it is a measurement now rather than a plausible guess. Workshop HP is NOT uniform per level. 5 + 10 + 20 = 35 is a plausible doubling series and is assumed, not measured — only L3 was ever flown. Two requests would settle it.',
  },
  'BUILDINGS.maxLevel.server': {
    confidence: 'measured',
    source: 'The server states each cap itself: "oops: max level for X is N", read by parse_max_level(). Fortress 5, barracks 2, recruiting / railway / aerodrome / harbor 1.',
  },
  'BUILDINGS.maxLevel.unknown': {
    confidence: 'superseded',
    note: 'SUPERSEDED by BUILDINGS.levels. Both caps came back the moment anyone pressed the button: the server states max level 3 for the workshop and 4 for the factory. The factory null had reached the UI as unbounded. The sweep asked workshop and factory for level 3, was not rejected, and never probed higher. The form\'s lvl select offers 1-5 for every type, which is a UI cap and not a server cap. The true cap is at least 3 and otherwise unknown.',
  },

  'TRENCH_POOL': {
    confidence: 'derived',
    source: 'results.jsonl, experiment=trenches: 10 rows, 10 infantry vs 10 infantry, one session.',
    method: 'pool = lost / pct with the attacker\'s output invariant at exactly 40.0, so each multiplier is a BRACKET, not a reading. See TRENCH_POOL_BRACKET.',
    note: 'Levels 4, 5, 15 and 20 each bracket a clean 2-decimal value. Level 10 is pinned too, now. This said its bracket was [1.2382, 1.2463] and that 1.24 was therefore not pinned to two decimals; a later sweep narrowed it to [1.23977, 1.24047], which is 0.0007 wide and contains exactly one two-decimal value. The note simply did not catch up with the bracket sitting beside it in TRENCH_POOL_BRACKET. The pool bonus applies while ATTACKING as well as defending (attacker trench 20 gave pool x1.35 and turned 2 deaths into 1). Levels 1-3 confer no pool bonus at all.',
    limits: 'Infantry only. That the multiplier is unit-independent and purely multiplicative is assumed.',
  },
  'TRENCH_OUTPUT': {
    confidence: 'measured',
    source: 'Same 10 rows. These come from an absolute HP-lost figure rather than a ratio of rounded numbers, so they are precise to ±0.001 — much better than the pool multipliers.',
    note: 'DEFENDER only: an attacker at trench 20 left the defender\'s loss at exactly 40.0, the control value. The curve is not smooth — it plateaus at x1.40 across levels 4 AND 5 — so both schedules are probably table lookups rather than formulas (assumed; bytro.js contains no trench logic at all, only form handling).',
    limits: 'Measured only at n = 10, where E(n) = n. Whether the bonus multiplies the base stat or the effective unit count is therefore undetermined, and the two diverge above 20 units.',
  },
  'TRENCH.gaps': {
    confidence: 'measured',
    note: 'CLOSED. This described 12 of 21 trench levels as never submitted; the trench_gaps sweep filled every one and the note did not catch up. All 21 are measured points now and trenchFactors() reports exact:true at each. Interpolation is assumed and, given the x1.40 plateau, demonstrably risky. Both sampled sequences are non-decreasing, so a value at an unsampled level can be BRACKETED by its sampled neighbours — that bracketing is what the engine reports, and it rests on an assumption of monotonicity, not on a reading.',
  },

  'resolution_order': {
    confidence: 'measured',
    note: '1. The defender\'s fortress DR is computed from the fortress HP at ROUND START. 2. Both sides\' outputs come from the PRE-round state, except an AIR attacker against GROUND, which uses its post-fire state. 3. Damage is applied; building damage is additive and unmitigated. 4. deaths = floor(this round\'s damage / the AVERAGE HP of the units entering the round), which is the remaining pool over the survivors -- not over a full unit. A stack whose pool reaches zero loses every unit, which the division alone does not give. 5. Survivors are count minus deaths, and the next round fires with those. THIS IS MEASURED ACROSS ROUNDS NOW. It used to end \'every measurement used maxRounds=1, so this is a description of ONE round and multi-round iteration is unmeasured\', and step 4 read \'floor(HP lost / trench-inflated per-unit max HP)\', which is a different and wrong rule. A ladder of five unit types spanning per-unit HP from 10 to 260, eight rounds each, fixed both: worst error 0.0032% with every death count exact.',
  },
  'result_semantics': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=semantics: 3 rows with asymmetric counts.',
    note: 'The page\'s span reports HP LOST, not HP left, and pool = lost / pct. This is why every constant above can be trusted at all.',
  },
  'FORM.domains': {
    confidence: 'measured',
    source: 'Read directly from the committed form capture last_response.html this session — a single flat <select name=A.1.1.unit> with <optgroup label=Land|Air|Naval>.',
    note: 'Not physics. Listed so the app does not invent options the game does not have. RANGED_KM values (artillery 50, railgun 150, cruiser 40, battleship 75) come from the help page, not from this rig.',
  },
  'PATROL.attrition': {
    confidence: 'estimated',
    source: 'results.jsonl, experiment=patrol: 9 matchup cells at maxRounds=1, each compared '
      + 'against the corresponding air_vs_ground cell already on disk.',
    note: 'The base stat is measured and unchanged between modes. THE LAW IS SYMMETRIC AND THE '
      + 'COEFFICIENT IS NEARLY PINNED: both sides fire with what survives a fraction c of their '
      + 'OWN losses — the ordinary post-fire law a strike pays in full, charged at a discount — '
      + 'and because each side\'s losses are the other\'s output, the pair is a FIXED POINT '
      + 'rather than a sequence. c = 0.3772 fits BOTH channels across 33 cells to 0.47% worst, '
      + 'most under 0.1%. THE OLD BAND WAS AN ARTIFACT: this note read 0.360-0.427 over nine '
      + 'cells with the scatter blamed on the delivery being discrete rather than smooth. That '
      + 'fit used the superseded survivor rule — count minus floor(cumulative damage / max HP) — '
      + 'which the five-type rounds ladder overturned, and refitting the same nine cells with the '
      + 'corrected rule collapses the range by a factor of ten. What is left is 0.3-0.5% and it '
      + 'is confined to one family, an air stack against armoured cars, where the defender\'s own '
      + 'attenuation is largest. AND THE APP MODELLED HALF OF IT: the defender was not attenuated '
      + 'at all, so a patrolling stack was told it would lose 160.00 where the server prints '
      + '110.46 — 45% out, in the direction that makes patrol look worse than it is. Patrol '
      + 'results stay labelled estimated, because c is not pinned to the printed decimal.',
  },
  'PATROL.rounds': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=patrol: a maxRounds ladder of 0.25/0.5/0.75/1 flown in '
      + 'BOTH terrains, tac vs inf.',
    note: 'Patrol damage is proportional to maxRounds (rate flat at 30.13-30.33 per unit per '
      + 'round). A direct strike IGNORES maxRounds: 30.03 per unit at every rung. This is why the '
      + 'app offers fractional rounds for patrol and not for a strike.',
  },
  'RANGE.roster': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=range_roster (109 requests, one bisection per unit) '
      + 'plus return_fire (20) and mixed_range (4). Each unit fights ITSELF, 20 a side, in '
      + 'the terrain pair its own class needs -- the one matchup guaranteed to run, so a '
      + 'silent response during the search is attributable to distance and nothing else.',
    note: 'MEASURED FOR ALL SEVENTEEN UNITS, by bisection: the largest distance that fights '
      + 'and the smallest that does not, one apart. Ten melee types reach exactly 5; lart 30, '
      + 'art 50, rrg 150, cl 40, bb 75. cl and bb match the in-game help page exactly, which '
      + 'is a check on the method rather than a source for it; lart 30 is on no help page. '
      + 'THE TABLE USED TO SAY INFANTRY REACH 1, AND THAT WAS NEVER A MEASUREMENT -- it came '
      + 'from a three-value ladder (0, 1, 25), so 1 was the largest distance anyone had TRIED '
      + 'rather than the largest that works. Infantry reach 5 like everything else. A number '
      + 'that only looks measured is worse than a gap, because nothing downstream flags it. '
      + 'Inside range the figure is identical to zero distance -- a gate, not a falloff.',
  },
  'RANGE.returnFire': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=return_fire: the boundary walked one kilometre at a '
      + 'time from 4 to 8 km, lart against lart; plus every ranged reading in range_roster '
      + 'and one mixed defender in mixed_range.',
    note: 'A BOMBARDED DEFENDER DOES NOT SHOOT BACK. At 4 and 5 km light artillery deals '
      + '100.00 and loses 20.00; at 6, 7 and 8 km it deals the same 100.00 and loses exactly '
      + 'nothing. The cut-off is a property of the DISTANCE, not of the defender: lart '
      + 'reaching 30 km, a cruiser reaching 40 and a battleship reaching 75 are all silent at '
      + '8 km, and a mixed inf+lart defender at 6 km is silent too. Nor does a long-reaching '
      + 'defender ever START a fight -- infantry attacking light artillery from 20 km '
      + 'produces no battle at all, though the artillery reaches twenty kilometres past its '
      + 'attacker. The attacker\'s reach alone decides whether anything happens. See the '
      + 'return_fire_generality gap for the one thing this cannot separate.',
  },
  'RANGE.mixedStack': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=mixed_range: three attacking stacks at 20 km.',
    note: 'A ROW THAT CANNOT REACH IS INERT -- it neither fires nor counts toward the '
      + 'stack-size factor for the rows that do. 20 infantry + 20 light artillery firing from '
      + '20 km deals 100.00, the identical figure the artillery deals alone; 20 infantry '
      + 'alone at 20 km produces no battle. So the battle happens if ANY attacking row '
      + 'reaches, and E() counts only the rows that do. The alternative -- counting the '
      + 'unreachable units toward E() -- would let a stack gain output by adding units that '
      + 'cannot shoot, which is why it was worth four requests rather than an assumption.',
  },
  'CLASS_DEFENCE.matrix': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=defence_matrix (92 requests: two attackers of each class '
      + 'against all seventeen defenders) plus defence_gaps (10, refilling the cells TERRAIN_PAIR '
      + 'refused) and balloon_class (3).',
    note: 'THE DEFENDING SIDE\'S WHOLE TABLE, which did not exist before. Read off the ATTACKER\'s '
      + 'losses -- attacker_lost = coef x E(defender count) x m(1) -- which works in one request '
      + 'because a defending stack is not attenuated even when it is losing badly. Every cell was '
      + 'read by TWO independent attackers of the same class and every pair agreed, so the '
      + 'defending side has the same shape as the attacking one: flat within an attacker class, '
      + 'changing between them. That was a guess from four cells before this sweep. Two free '
      + 'corroborations came with it: all seventeen same-class cells reproduce that unit\'s '
      + 'measured defence diagonal, and the air column reproduces all ten values of '
      + 'GROUND_DEFENCE_VS_AIR, read by different attackers in a different sweep. WHAT THIS '
      + 'CHANGED: a cross-class pairing used to have a measured attack coefficient and no defence '
      + 'one, so the engine withheld the ENTIRE battle. Land attacking air -- one of the commonest '
      + 'things a player would enter -- came back blank for exactly that reason. 0 of 289 pairings '
      + 'are unknown now, against 243 before.',
  },
  'CLASS_DEFENCE.balloon': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=balloon_class: three requests.',
    note: 'A BALLOON IN LAND TERRAIN ATTACKS AS A LAND UNIT. This began as an apparent '
      + 'contradiction: the sweep read a balloon defending at 10.0 against a fighter and a bomber, '
      + 'which agreed exactly, while the balloon\'s own diagonal reads 3.0 -- its LAND figure. '
      + 'Either its air column was not flat or the attacking balloon was never in the air. A '
      + 'balloon attacking forty infantry loses 166.67, which is 5.0 x E(40), the land column; the '
      + 'air column would have given 13.33. Stated for the ATTACKING side only, which is the side '
      + 'that was measured. What a balloon counts as when it is the TARGET has not been tested and '
      + 'does not arise, because CLASS_ATTACK.bal is 3.0 in all three columns.',
  },
  'EMBARKED.rule': {
    confidence: 'measured',
    source: 'results.jsonl, experiments embarked_hp (20 requests), embarked_class (6), '
      + 'embarked_convoy (6) and target_terrain (8).',
    note: 'EMBARKATION IS A CLASS CHANGE WITH THREE CONSEQUENCES, and the app modelled one of '
      + 'them. A non-naval unit in sea or debark terrain (1) attacks and defends on its own flat '
      + 'column, 1.0 against land and naval targets and 0.5 against air, (2) holds a flat 10 HP '
      + 'whatever it is, and (3) is hit on the attacker\'s NAVAL column. The HP is read straight '
      + 'off the pools: 20 infantry, 20 cavalry, 20 heavy tanks, 20 fighters and 20 bombers all '
      + 'report exactly 200.0 at sea against 398.9, 500.0, 5194.8, 1200.0 and 1599.1 on land. The '
      + 'class change is six readings for six, from the three attackers whose land and naval '
      + 'columns differ. THE NEAR-MISS WORTH RECORDING: an embarked unit looked like it simply WAS '
      + 'a convoy -- that is where the flat 1.0 came from, and the convoy\'s land and air columns '
      + 'are exactly 1.0 and 0.5. It is wrong in the third cell, where a convoy reads 0.5 against '
      + 'naval targets and an embarked unit reads 1.0. Two cells of three agreeing is what a wrong '
      + 'law looks like from the inside. AND THE COST OF NOT KNOWING IT: the naval-vs-air cell '
      + 'stood for a week as \'30.0 per effective unit\'. It was a 100% wipe against a pool six '
      + 'times smaller than the unit table implies. Sized properly it reads 40.0.',
  },
  'CLASS_ATTACK.corroboration': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=class_matrix_2 (32 requests: a second target for every air '
      + 'and naval column) and balloon_columns (5).',
    note: 'EVERY COLUMN NOW HAS TWO INDEPENDENT TARGETS. The matrix\'s shape -- a coefficient flat '
      + 'across targets WITHIN a class -- was measured on the land column and inherited by the '
      + 'other two, which had one cell apiece. A bomber was sent where the first sweep used a '
      + 'fighter and a cruiser where it used a battleship: 25 of the 26 readable cells came back '
      + 'identical to four decimal places. TWO CORRECTIONS CAME OUT OF THE TWENTY-SIXTH AND ITS '
      + 'NEIGHBOURS. The Balloon\'s row was one land reading copied across three columns on the '
      + 'assumption the row was flat; against air it is 10.0, not 3.0. And the fliers\' naval '
      + 'column read 3.6 / 23.64 / 4.4, which were raw figures against a battleship with the '
      + 'post-fire law never applied -- corrected, both targets agree on 5.0 / 30.0 / 5.0, each '
      + 'exactly that flier\'s land column. Mistaking attenuation for a coefficient is what '
      + 'produced three numbers that looked like measurements and were arithmetic.',
  },
  'ATTENUATION.scope': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=attenuation_scope (2 requests) plus every air cell in '
      + 'class_matrix, class_matrix_2 and air_vs_ground.',
    note: 'AN AIR STACK IS ATTENUATED AGAINST SURFACE TARGETS, land and naval alike, and NOT '
      + 'against other aircraft. The air-to-air reading is emphatic rather than marginal: twenty '
      + 'fighters lose 58% of their pool to two hundred fighters and still deal the full 20.0 x '
      + 'E(20) = 400.00, where the attenuated figure would be 167.33. THE CORRECTION WORTH '
      + 'RECORDING: an exemption saying air attackers are blind to embarkation was nearly written '
      + 'into the model, on the strength of a fighter dealing 98.89 to infantry on land and 98.61 '
      + 'to the same infantry at sea. The two columns that pair was meant to distinguish are '
      + 'int.land = 5.0 and int.naval = 5.0 -- the same number, so the test had no power and "no '
      + 'difference" was read as "blind to the difference". The cell that discriminates is an air '
      + 'stack against EMBARKED FIGHTERS, where the columns are 20.0 and 5.0: it deals 98.61, '
      + 'which is 5.0 x E(20) x m(0.98542), the naval column attenuated. Everyone sees '
      + 'embarkation. The rule is uniform and the exemption was an artifact.',
  },
  'ROUNDS.law': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=multi_round (an 8-rung infantry ladder) and '
      + 'multi_round_types (40 more: five unit types spanning per-unit HP from 10 to 260, eight '
      + 'rounds each, 50 a side).',
    note: 'EACH ROUND FIGHTS WITH WHAT IS LEFT: output = coefficient x E(survivors) x m(f), where '
      + 'survivors are COUNT MINUS DEATHS and f is the remaining pool over what those survivors '
      + 'could hold. Exact to 0.0032% across all 48 cells, with every death count reproduced '
      + 'exactly. TWO THINGS WERE WRONG BEFORE THE LADDER. First, survivors were recomputed as '
      + 'count - floor(cumulative damage / max HP), which is a different number: solving each '
      + 'measured round\'s output for the survivor count it implies lands on count-minus-deaths '
      + 'in 20 of 21 cells and on the floor rule in 8. Second, a round\'s casualties are counted '
      + 'against what the survivors HAVE LEFT -- the remaining pool divided between them -- not '
      + 'against a full unit, so a battered stack loses units faster than its paper HP suggests. '
      + 'THE EXPLANATION THAT WAS WRONG: the residual drift used to be attributed to high '
      + 'per-unit HP making the survivor count coarse, which was written from ONE unit type at '
      + 'the far end of the range. The ladder disproves it -- the stormtrooper at 40 HP is exact '
      + 'through eight rounds while the armoured car at 60 was the worst in the roster at 0.970% '
      + 'and infantry at 20 drifted to 0.340%. The error tracked how many rounds both sides '
      + 'survived, never what they were made of. The two anomalous infantry death counts that '
      + '"nothing explained" were this rule all along.',
  },
  'HP.affine': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=last_edges probe=air_E_above_20: attenuated air stacks at '
      + '10, 25, 40 and 50 units. Plus one line of algebra.',
    note: 'OUTPUT IS E(survivors) x m(f), and above the knee that is exact to 0.001% at all four '
      + 'sizes. This was recorded as a gap on the grounds that the rival hypothesis -- a PER-UNIT '
      + 'sum of m(f) rather than one stack-level term -- had never been separated. It cannot be, '
      + 'and not because the sizes were unlucky: m is AFFINE, so sum_i m(f_i) = 0.05s + 0.95 '
      + 'sum_i f_i, and sum_i f_i is the remaining pool over the per-unit HP, which is s x f. The '
      + 'two expressions are identically equal for every stack and every distribution of damage. '
      + 'That was the same hypothesis written twice, and no measurement at any size could have '
      + 'told them apart. The rivals that DO differ put m somewhere else: inside E, which misses '
      + 'by 0.33% at fifty units, or against the raw count instead of the saturated one, which '
      + 'misses by 42.9%. Both are rejected by these four cells, so the discrimination the gap '
      + 'asked for exists -- it was just aimed at the wrong pair.',
  },
  'HEROES.hpScaling': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=hero_hp_scaling (16 requests: four heroes at 100, 75, 50 and '
      + '25 per cent) plus togo_b_kind, which found it.',
    note: 'A HERO\'S OWN OUTPUT SCALES WITH ITS OWN HP, by the same m(f) = 0.05 + 0.95f every unit '
      + 'obeys. Every hero reading in this project set the hero to 100% and never varied it, so the '
      + 'question was never asked and the app applied a hero\'s full contribution however battered '
      + 'it was. Tōgō contributes 15.00 at full health, 7.88 at 50% and 2.17 at 10% -- which is '
      + '15.0 x 0.525 and 15.0 x 0.145 to the printed decimal. Lawrence and Kangal reproduce it '
      + 'exactly. THE BUFF DOES NOT SCALE: Pershing\'s constant 12.00 on an infantry stack is the '
      + 'same at 25% as at 100%, which is what let the two channels be separated at all -- the '
      + 'HP ladder is a decomposition, not just a check.',
  },
  'HEROES.attackOnly': {
    confidence: 'measured',
    source: 'results.jsonl, experiments land_hero_attacking (48 requests, three types per hero), '
      + 'land_hero_screen (96, the remaining six land types), hero_new_buffs (85: channel, '
      + 'own-attack flatness and the full curve for each) and hank_sides (20).',
    note: 'BUFFS THAT ACT ONLY WHEN ATTACKING, which no screen had ever looked for. Every buff in '
      + 'this table was found on a DEFENDING stack, and a buff that measures zero there is recorded '
      + 'as absent -- the exact mirror of the defence-only buffs Joffre and Kangal have. Four '
      + 'heroes carry them: Pershing on infantry, cavalry, armoured cars, light and heavy tanks '
      + '(not artillery, railguns or stormtroopers); Allenby on cavalry; Georg on artillery; Marco '
      + 'on light tanks. All four measure exactly 1.0000 on a defending stack. AND THE SAME SWEEP '
      + 'CORRECTED FOUR OWN-ATTACK VALUES, because an own attack read off a stack the hero buffs is '
      + 'an own attack and a buff added together: Pershing 62.0 -> 8.0, Allenby 29.6 -> 20.0, Georg '
      + '16.8 -> 12.0, Marco 24.6 -> 15.0. The app quoted 102.00 against ten infantry with Pershing '
      + 'where the server prints 60.00. The six-type stack that produced the original 62.0 now '
      + 'reproduces at 308.00 exactly, from 8.0 plus buffs on the three types it contains. Hank\'s '
      + 'infantry buff also turned out to differ by side at its cap alone -- 1.10 attacking, 1.09 '
      + 'defending, with levels 1 to 9 identical on both.',
  },
  'HEROES.classColumns': {
    confidence: 'measured',
    source: 'results.jsonl, experiments land_hero_target_class (48 requests: all sixteen land '
      + 'heroes against one target of each class) and land_hero_def_class (48, the same sweep on '
      + 'the defending side). Control stack is light artillery, which no hero buffs, so the excess '
      + 'is the hero\'s own contribution and nothing else.',
    note: 'A HERO HAS A COLUMN PER CLASS, on BOTH sides, and all twenty-two do. Every land-hero '
      + 'reading in this project fired at INFANTRY, so one number per side looked like the whole '
      + 'story -- it is the LAND column. Lawrence contributes 45.0 attacking land, 4.5 attacking '
      + 'air and 11.25 attacking naval, a factor of ten from the same hero at the same level, and '
      + 'defends at 10.0 / 1.0 / 2.5. Every one of the sixteen differs across the three. '
      + 'Richthofen was the first case found and it read as a quirk of one air hero. WHY THE OLD '
      + 'SINGLE NUMBER LOOKED RIGHT: for every hero measured, the land column equals the scalar it '
      + 'replaced, exactly. A battle on land computes as it always did; every other pairing was '
      + 'wrong. The column is applied as a RATIO to whichever class the scalar was read in, not as '
      + 'a replacement, because two heroes have an own attack that moves with level and '
      + 'overwriting it with a level-10 column threw the curve away.',
  },
  'BUILDINGS.levels': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=building_levels: every level of every building, plus the '
      + 'first level each server refuses.',
    note: 'EVERY BUILDING\'S HP IS MEASURED AT EVERY LEVEL IT HAS, and every cap is the server\'s '
      + 'own words. Seven of the eight used to have HP confirmed at exactly one level with the rest '
      + 'extrapolated from it. THE WORKSHOP CARRIED AN OUTRIGHT ASSUMPTION -- 35 HP at level 3, '
      + 'with a note saying "5 + 10 + 20 = 35 is a plausible doubling series and is assumed, not '
      + 'measured". It is 5, 15, 35: the series was right, and it is a reading now instead of a '
      + 'guess. It is also NOT linear, so hpPerLevel stays null for it rather than carrying 11.67. '
      + 'THE FACTORY CAP WAS WRONG IN A WAY THAT REACHED THE UI: maxLevel was null, meaning '
      + 'unbounded, because the sweep asked for level 3, was not rejected, and never pressed '
      + 'higher. The server says "max level for Factory is 4". The workshop caps at 3. Everything '
      + 'else confirms what was recorded: barracks 40 per level to 2, railway, aerodrome and '
      + 'harbor 60 at their single level, recruiting 5.',
  },
  'BUILDING_DAMAGE.rest': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=building_damage_rest: nine units against a level-5 '
      + 'fortress with a five-unit stack, small enough that the building survives.',
    note: 'THE NINE UNITS THAT HAD NO FIGURE AT ALL. The original sweep only ever flew LAND '
      + 'attackers, so convoys, the Balloon and every air and naval unit had no entry -- not a '
      + 'bracket, not a floor, nothing -- and the heavy tank had a FLOOR, 8.82, because its one '
      + 'reading was censored against a fortress it destroyed outright. Read with five tanks it '
      + 'is 9.00, so nothing in the table is censored any more. TWO UNITS DEAL EXACTLY ZERO: a '
      + 'convoy and a submarine cannot hurt a building, which is a reading rather than an '
      + 'absence and is reported as 0.00 rather than withheld. AND BUILDING DAMAGE IS ATTENUATED '
      + 'on the same paths the unit damage is, which the engine did not do: five zeppelins read '
      + '147.20 where an unattenuated 30.00 per effective unit gives 150.00. The fliers\' raw '
      + 'figures -- 0.96, 5.80, 29.44 -- are the post-fire law applied to buildings; corrected by '
      + 'the same factor the unit damage uses they are 1.0045, 5.9995 and 30.0102, which is how a '
      + 'derived correction announces that it is right.',
  },
  'VARIANCE.band': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=variance: 60 samples with simulateVariance on, against the '
      + 'deterministic figure for the same battle.',
    note: 'ONE UNIFORM ROLL PER SIDE PER ROUND, not per unit. 60 samples give a standard deviation '
      + 'of 5.285 where a single whole-stack roll predicts 5.774 and a per-unit roll would predict '
      + '1.291 — so the whole stack moves together and a big stack cannot average its luck away. '
      + 'Observed range [0.9025, 1.0992] of the variance-off figure. THE ENGINE HAS ALWAYS '
      + 'COMPUTED THIS BAND AND THE PAGE NEVER SHOWED IT: every figure on screen was the '
      + 'variance-off value, presented alone, which invites a reader to treat a coin-flip as a '
      + 'prediction. A ±10% swing is the difference between an attack working and not. It is '
      + 'rendered under the lead figure now. The band is NOT replayed cell by cell — a '
      + 'deterministic engine cannot reproduce a roll — so what the suite asserts is that the '
      + 'band exists, straddles the figure, and is the full ±10% at every stack size.',
  },
  'FIELD.coverage': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=field_coverage (0 requests — it reads the form this rig '
      + 'already loads and compares it against everything ever sent), then debark_class (6) and '
      + 'long_rounds (8) for what it found.',
    note: 'THE ONE INVENTORY NOBODY AUTHORED. Every audit before this worked from something this '
      + 'project wrote down — the gap list, this table, the engine\'s outputs — and each could '
      + 'only find holes someone had thought to describe. The FORM is discovered rather than '
      + 'declared, so checking all 33 of its fields against every field ever sent is the one audit '
      + 'that does not beg its own question. All 33 have been exercised. Varying them turned up '
      + 'two live defects no note mentioned: debark treated as sea for the target class, and '
      + 'patrol multiplying one round by the duration instead of iterating it. maxRounds accepts '
      + 'up to 1000 and 100 is now the highest submitted; nothing suggests a further change of '
      + 'behaviour above it, but nothing has been sent there either.',
  },
  'DEBARK.asymmetry': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=debark_class: the three attackers whose land and naval '
      + 'columns differ, fired at a target in sea and in debark, plus an embarked attacker in '
      + 'debark against one target of each class.',
    note: 'DEBARK IS NOT SEA, and the difference is asymmetric. A unit in debark attacks and '
      + 'defends on the embarked column and holds the flat 10 HP exactly as at sea — 40 embarked '
      + 'infantry in debark deal 0.9999 to infantry, 0.5001 to fighters and 0.9999 to a '
      + 'battleship. But a TARGET in debark is hit on the attacker\'s LAND column: cavalry 15.00 '
      + 'where at sea it is 8.00, light artillery 5.00 against 1.00, a heavy tank 45.00 against '
      + '23.00. The two were treated as one because they sit in the same list and only the HP half '
      + 'had ever been measured in debark. For a light artillery attacker that was 5x wrong.',
  },
  'PATROL.duration': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=long_rounds: 1, 4, 20 and 100 rounds, flown as a strike '
      + 'and as a patrol.',
    note: 'PATROL ITERATES ROUNDS; it does not multiply one. The app computed a single round and '
      + 'scaled it by the duration, which is right below one round — the 0.25/0.5/0.75/1 ladder '
      + 'gives a flat per-round rate, and that is still measured and still modelled — and badly '
      + 'wrong above it. At 100 rounds multiplying gives 29811.90 where the server prints '
      + '9108.46, a factor of 3.3, because both sides wear each other down and a stack that has '
      + 'lost most of its pool does not keep dealing its opening figure. Iterating reproduces the '
      + 'ladder to 0.01% at four rounds and 0.05% at twenty; the 1.16% at a hundred is the '
      + 'per-round residual accumulating. The app used to warn that scaling past four rounds '
      + '"assumes the proportionality holds indefinitely, which nobody has checked" — it has been '
      + 'checked now, and it did not hold.',
  },
  'STACK.composition': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=mixed_stacks (8 rows) plus survivable_rig (a 1-to-9 '
      + 'type ladder and three held-out stacks) and stack_order (2 attacking stacks).',
    note: 'A REAL STACK IS A MIXTURE, and the app models one. A stack saturates as a whole '
      + 'and each unit type draws from what is left, STRONGEST FIRST -- effective_i = '
      + 'E(units through i) - E(units before i), ordered by the coefficient in use. Fits '
      + 'every rung of the ladder to 0.002% and predicted three stacks it was not fitted to '
      + 'at the same figure. Submission order is irrelevant (the server sorts first). The '
      + 'server also refuses a repeated unit type in one stack, so a stack is a SET of '
      + 'types. See STACK.saturation and STACK.allocation.',
  },
  'STACK.saturation': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=survivable_rig: a ladder from one to nine unit types '
      + '(6 each) against 60 infantry, plus three held-out stacks whose predictions were '
      + 'written down before the requests went out; experiment=stack_order for the attack '
      + 'side; experiment=mixed_stacks for the original four mixtures.',
    note: 'effective_i = E(units through row i) - E(units before it), rows ordered STRONGEST '
      + 'FIRST by the damage coefficient in use -- the defence column when defending, the '
      + 'attack column when attacking (25 armoured cars + 25 stormtroopers attack for 677.08, '
      + 'which is by-attack exactly and by-defence 407.92). Worst error 0.002% across all '
      + 'nine rungs, against 43.2% for per-type saturation, 41.6% for one saturation split by '
      + 'count share, and 77.7% for ROSTER order -- which is what this app shipped until '
      + '2026-08-19. Roster order fitted the original four mixtures only because every one of '
      + 'them was infantry + artillery, an ordering the two laws agree on.',
  },
  'ROUNDS.multi': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=multi_round: the same 50-vs-50 infantry battle read '
      + 'at maxRounds 1, 2, 3, 4, 5, 6, 8 and 10.',
    note: 'Each round\'s output is coefficient x E(survivors) x m(f), where survivors are '
      + 'WHOLE units - count minus floor(HP lost / per-unit HP) - and f is what those '
      + 'survivors have left of their own maximum. Fits the ladder to 0.042%, against '
      + '0.221% for fractional survivors without m(f), 1.063% for whole survivors without '
      + 'it, and 6.0% for evaluating post-fire as air does. This reconciles with '
      + 'HP.scaling rather than contradicting it: m(f) is the same law, applied to the '
      + 'survivors. THE APP USED TO RECOMPUTE NOTHING between rounds, which is 13.66% out '
      + 'by round six - it declared a wipe that does not happen. '
      + 'SCOPE, corrected after the fact: the 0.042% was measured on INFANTRY only. Re-read '
      + 'with cavalry and heavy tanks, infantry and cavalry reproduce exactly and heavy tanks '
      + 'drift to 0.5% by round four - a unit with 260 HP each makes the whole-unit survivor '
      + 'count coarse, and the model is more sensitive there. The DEATH count reproduces in 10 '
      + 'of 12 cells: it is the sum of per-round floor(round damage / per-unit HP), not '
      + 'floor(cumulative / per-unit HP), and infantry rounds 3 and 4 are one short of that. '
      + 'Multi-round results stay labelled ESTIMATED.',
  },
  'STACK.allocation': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=allocation: one request per attacking land type '
      + 'against the same nine-type defender, nine rows of the land matrix; plus the '
      + 'asymmetric mixed_stacks splits as held-out points.',
    note: 'weight_i = TARGET_FACTOR[unit_i] x count_i, with infantry 0.50, cavalry 0.75 and '
      + 'everything else 1.00. It is a property of the TARGET, not the attacker: all nine '
      + 'land attackers give the identical pattern, bracketed across them to [0.4979,0.5023], '
      + '[0.7449,0.7559] and [0.9918,1.0083]. A hero counts 0.40. '
      + 'THIS APP SHIPPED THE WRONG RULE until 2026-08-19 - "the defending row\'s own attack '
      + 'value x count" - which is out by 40% of the stack total on a nine-row stack. It '
      + 'fitted because all four mixtures it came from were infantry + artillery, whose own '
      + 'attack values are 4.0 and 8.0, exactly the 0.5:1.0 ratio this table gives that pair. '
      + 'The attacker\'s TOTAL is unaffected - still coefficient x E(n) whatever the mix - so '
      + 'these are allocation weights, not damage values. Allocation uses RAW count, not the '
      + 'saturated effective count that output obeys.',
  },
  'HEROES.measured': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=heroes: a control plus 22 hero types at level 10 '
      + 'against 30 infantry.',
    note: 'MEASURED BUT DELIBERATELY NOT MODELLED. 16 of 22 heroes change a land battle, '
      + 'from x1.02 to x1.40, so the effect is large. But every reading is level 10, and the '
      + 'level 1-20 curve is completely untouched -- implementing a single level as though it '
      + 'were the mechanic would put a confident number on 19 unmeasured levels. Six naval '
      + 'heroes are refused on land outright ("Can\'t have Otto Hersing on land"), so their '
      + 'silence is a server refusal rather than a null. A hero is a UNIT: it renders an '
      + 'ordinary Lost-HP span and the stack summary table counts it, unlike a building. It '
      + 'does not mitigate -- total incoming damage is unchanged, the hero just absorbs a '
      + 'share of it. Every figure this app produces assumes NO hero. '
      + 'The LAW is now known exactly: output = A * heroEffective + unit_coef * M * '
      + 'unitEffective, where A is the hero fighting as one unit and M multiplies the rest '
      + 'of the stack; all 16 land-legal heroes are decomposed to 0.002% against a held-out '
      + 'stack size. 14 are pure combat units (M = 1.00) at attack 5 to 20; only joffre_home '
      + '(x1.30) and hank (x1.09) buff. What is still missing is the LEVEL curve -- every '
      + 'reading is level 10 of 20 -- and attacking heroes, so the app models none.',
  },
  'STACK.grouping': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=stack_limits: 4 requests.',
    note: 'Classes never share a stack, and the Airplane Convoy shares one with nothing. Nine '
      + 'land types in a single stack were ACCEPTED and returned nine result rows, so the cap '
      + 'is the group size (land 9, air 4, sea 3, convoy 1), not the page maxUnits of 15 and '
      + 'certainly not the 8 this app first shipped. Every refusal was stated by the server, '
      + 'not inferred from a null reading.',
  },
  'HEROES.hpChannel': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=hero_hp_cap: 52 rows, each one the server\'s own '
      + 'refusal naming the exact buffed maximum.',
    note: 'MODELLED. Five hero/unit pairs raise a unit type\'s MAX HP, on a curve of their '
      + 'own that is NOT the output curve. Read by asking for more HP than the unit can '
      + 'have: the server answers "Max hp for 2 Infantry is 47.200000", which is exact '
      + 'rather than a ratio of two pools each derived from a 3-significant-figure '
      + 'percentage. That mattered - the pool method produced pershing/infantry as '
      + '1.00/1.70/1.14/1.25, which reads like a broken instrument. It is not: the refusal '
      + 'gives the same numbers, and densifying shows a real DISCONTINUITY at level 6, '
      + 'where the factor drops from 1.70 to 1.10 before climbing again. Same factor at '
      + 'three units as at two, so it is a level effect and not a count artifact. Stored as '
      + 'points; any formula through them is wrong on one side of level 6.',
  },
  'HEROES.law': {
    confidence: 'measured',
    source: 'results.jsonl, experiments heroes / hero_scaling / hero_table / hero_levels / '
      + 'hero_caps / survivable_rig / hero_buff_confirm / hero_full / hero_hp_cap / '
      + 'hero_sides: 230+ requests.',
    note: 'output = A(side) * heroEffective + unit_coef * M(unit type, level, side) * '
      + 'unitEffective, plus a separate MAX-HP channel and the hero\'s own pool. '
      + 'TWO ATTACK COLUMNS: a hero attacks at one value and defends at another, exactly '
      + 'as a unit does, and thirteen of sixteen differ - pershing 62.00 attacking against '
      + '8.00 defending. Every "A" measured before 2026-08-19 is the defending one. '
      + 'M IS PER UNIT TYPE, PER LEVEL AND PER SIDE. All nine land types screened together: '
      + 'joffre_home buffs infantry and armoured cars, alvin stormtroopers, kangal armoured '
      + 'cars, hank infantry; the other twelve raise a nine-type stack by exactly their own '
      + 'attack and nothing more. alvin and hank apply their multiplier attacking and '
      + 'defending alike; joffre_home and kangal measure exactly 0.00 attacking, so theirs '
      + 'is DEFENCE-ONLY. '
      + 'CURVES ARE MEASURED POINTS, interpolated and never fitted. '
      + 'DETECTION FLOOR 0.2 HP on the output screen, a 10% buff on its weakest row. '
      + 'THE HERO ITSELF has its own HP pool (level-independent, one round number each), '
      + 'counts 0.40 in the damage split, and never reports a death count.',
  },
  'HEROES.levels': {
    confidence: 'measured',
    source: 'joffre_home at levels 1,2,4,5,9,10,11,15; hank at 1,2,5,9,10; kangal at 1,5,10.',
    note: 'NO LONGER ONLY THE BUFF. For the sixteen land heroes it still holds \u2014 their own attack and their pool are flat at every level tested. Three of the six air/naval heroes break it: Richthofen\'s and T\u014dg\u014d-with-bombardment\'s OWN ATTACK moves with level (25 to 125 for Richthofen) and Hersing\'s POOL does (100 to 200.7). Each is stored as measured points like every other curve. Its measured points are '
      + 'stored verbatim; a level between them is INTERPOLATED and the app says so. From level '
      + '5 up joffre_home is exactly 1.10 + 0.02*level, but levels 1-4 (1.10, 1.15, -, 1.16) '
      + 'do not fit that or any step, so no formula is used.',
  },
  'integrity': {
    confidence: 'measured',
    note: 'results.jsonl grew from 150 to 168 rows during the session that produced these tables, when a concurrent session flew the patrol experiment. The 18 patrol rows are single-sample and their multi-tick GROUND law does not close (predicted tick 3/4 defender output 3.5/3.5 against observed 3.4/3.3), so the patrol ATTRITION is implemented as an explicitly estimated band (see PATROL.attritionRange), never as a measured value; its maxRounds behaviour IS measured and is implemented as such. Two patrol findings do bear on the app: maxRounds is ignored entirely for terrain=air (0.25/0.5/0.75/1 return byte-identical results), and patrol out-damages a direct air strike in all 9 cells measured.',
  },
};
