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
    provenance: { maxLevel: 'BUILDINGS.maxLevel.server', hp: 'BUILDINGS.hp.oneLevel', mitigates: 'BUILDINGS.inert' },
  },
  railway: {
    code: 'railway', label: 'Railway',
    maxLevel: 1, hpPerLevel: 60, mitigates: false,
    poolAtLevel: { 1: 60 },
    provenance: { maxLevel: 'BUILDINGS.maxLevel.server', hp: 'BUILDINGS.hp.oneLevel', mitigates: 'BUILDINGS.inert' },
  },
  workshop: {
    code: 'workshop', label: 'Workshop',
    maxLevel: null, hpPerLevel: null, mitigates: false,
    poolAtLevel: { 3: 35 },
    provenance: { maxLevel: 'BUILDINGS.maxLevel.unknown', hp: 'BUILDINGS.hp.workshop', mitigates: 'BUILDINGS.inert' },
  },
  factory: {
    code: 'factory', label: 'Factory',
    maxLevel: null, hpPerLevel: 40, mitigates: false,
    poolAtLevel: { 3: 120 },
    provenance: { maxLevel: 'BUILDINGS.maxLevel.unknown', hp: 'BUILDINGS.hp.oneLevel', mitigates: 'BUILDINGS.inert' },
  },
  barracks: {
    code: 'barracks', label: 'Barracks',
    maxLevel: 2, hpPerLevel: 40, mitigates: false,
    poolAtLevel: { 2: 80 },
    provenance: { maxLevel: 'BUILDINGS.maxLevel.server', hp: 'BUILDINGS.hp.oneLevel', mitigates: 'BUILDINGS.inert' },
  },
  aerodrome: {
    code: 'aerodrome', label: 'Aerodrome',
    maxLevel: 1, hpPerLevel: 60, mitigates: false,
    poolAtLevel: { 1: 60 },
    provenance: { maxLevel: 'BUILDINGS.maxLevel.server', hp: 'BUILDINGS.hp.oneLevel', mitigates: 'BUILDINGS.inert' },
  },
  harbor: {
    code: 'harbor', label: 'Harbor',
    maxLevel: 1, hpPerLevel: 60, mitigates: false,
    poolAtLevel: { 1: 60 },
    provenance: { maxLevel: 'BUILDINGS.maxLevel.server', hp: 'BUILDINGS.hp.oneLevel', mitigates: 'BUILDINGS.inert' },
  },
};

// ---------------------------------------------------------------------------
// FORTRESS
// ---------------------------------------------------------------------------
export const FORTRESS = {
  drSlopePer50HP: 0.15,   // DR = 0.15 * (fortressHP / 50 + 1)
  drOffset: 0.15,         // the "+1" term: any fortress at all costs 15%
  hpPerLevel: 50,
  maxMeasuredLevel: 5,
  provenance: { dr: 'FORTRESS.dr', hp: 'BUILDINGS.fortressHP' },
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
//       dealt = base * E(n) * (1 - c * own_fraction_lost)
//
//   c = 1.000 for a strike (that is the return-fire law, fitted to 0.005 HP
//   across 30 cells) and c = 0.36..0.43 for patrol across nine cells. It does
//   NOT close to a single value, and the scatter does not track f, so the real
//   mechanism is probably discrete -- ticks, or whole units dying at tick
//   boundaries -- rather than a smooth fraction. 3/8 sits inside the range and
//   is used as the working value, but the app must show the range and must
//   never present a patrol number as measured.
//
// The base attack stat is UNCHANGED between the two modes: every attacker's
// air-to-ground value comes back through patrol (int 5.006/5.024/5.008,
// tac 30.026/30.000/30.000, zep 5.003/5.002/5.015). So patrol is the same
// weapon delivered differently, not a different weapon.
export const PATROL = {
  attritionCoefficient: 0.375,        // working value, = 3/8
  attritionRange: [0.360, 0.427],     // what nine cells actually support
  cellsMeasured: 9,
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
export const BUILDING_DAMAGE_FLOOR = { ht: 8.82 };

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
                  pool: 90, sits: 'first', maxLevel: 10,
                  buffs: { ac: { channel: 'defence', curve: { 1: 1.08, 2: 1.10, 3: 1.12, 4: 1.12, 5: 1.13, 6: 1.14, 7: 1.16, 8: 1.18, 9: 1.20, 10: 1.20 } } } },
  joffre:       { label: 'Joseph Joffre (Non Homeland)', atkDefending: 16.0, atkAttacking: 4.0,
                  pool: 120, sits: 'first', maxLevel: 15 },
  joffre_home:  { label: 'Joseph Joffre (Homeland)', atkDefending: 16.0, atkAttacking: 4.0,
                  pool: 120, sits: 'first', maxLevel: 15,
                  buffs: { inf: { channel: 'defence', curve: { 1: 1.10, 2: 1.15, 3: 1.15, 4: 1.16, 5: 1.20, 6: 1.22, 7: 1.24, 8: 1.26, 9: 1.28, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40 } },
                           ac:  { channel: 'defence', curve: { 1: 1.10, 2: 1.15, 3: 1.15, 4: 1.16, 5: 1.20, 6: 1.22, 7: 1.24, 8: 1.26, 9: 1.28, 10: 1.30, 11: 1.32, 12: 1.34, 13: 1.36, 14: 1.38, 15: 1.40 } } },
                  hpBuffs: { ac: { 1: 1.00, 2: 1.00, 3: 1.05, 4: 1.05, 5: 1.09, 6: 1.09, 7: 1.13, 8: 1.13, 9: 1.17, 10: 1.17, 11: 1.21, 12: 1.21, 13: 1.25, 14: 1.25, 15: 1.30 } } },
  marco:        { label: 'Fiero “Marco” Martello', atkDefending: 15.0, atkAttacking: 24.6,
                  pool: 60, sits: 'first', maxLevel: 10,
                  hpBuffs: { lt: { 1: 1.00, 2: 1.00, 3: 1.05, 4: 1.06, 5: 1.07, 6: 1.08, 7: 1.09, 8: 1.10, 9: 1.11, 10: 1.12 } } },
  allen:        { label: 'Viscount Allenby', atkDefending: 10.0, atkAttacking: 29.6,
                  pool: 50, sits: 'first', maxLevel: 15 },
  larab:        { label: 'Lawrence of Arabia', atkDefending: 10.0, atkAttacking: 45.0,
                  pool: 75, sits: 'first', maxLevel: 20 },
  alvin:        { label: 'Alvin C. York', atkDefending: 8.30, atkAttacking: 25.0,
                  pool: 100, sits: 'first', maxLevel: 20,
                  buffs: { st: { channel: 'both', curve: { 1: 1.15, 2: 1.15, 3: 1.20, 4: 1.25, 5: 1.25, 6: 1.30, 7: 1.30, 8: 1.35, 9: 1.35, 10: 1.40, 11: 1.40, 12: 1.45, 13: 1.45, 14: 1.50, 15: 1.50, 16: 1.55, 17: 1.55, 18: 1.60, 19: 1.60, 20: 1.60 } } },
                  hpBuffs: { st: { 1: 1.00, 2: 1.05, 3: 1.10, 4: 1.10, 5: 1.14, 6: 1.14, 7: 1.18, 8: 1.18, 9: 1.22, 10: 1.22, 11: 1.26, 12: 1.26, 13: 1.30, 14: 1.30, 15: 1.34, 16: 1.34, 17: 1.38, 18: 1.38, 19: 1.42, 20: 1.42 } } },
  lucien:       { label: 'Lucien Laroche', atkDefending: 8.0, atkAttacking: 8.0,
                  pool: 40, sits: 'first', maxLevel: 15 },
  lucien_g:     { label: 'Lucien Laroche w/gas', atkDefending: 8.0, atkAttacking: 8.0,
                  pool: 40, sits: 'first', maxLevel: 15 },
  pershing:     { label: 'John J. Pershing “Black Jack”', atkDefending: 8.0, atkAttacking: 62.0,
                  pool: 80, sits: 'first', maxLevel: 20,
                  // The infantry curve DROPS at level 6, from 1.70 to 1.10, and
                  // climbs again. Measured exactly, reproduced at three units as
                  // well as two, and confirmed by an independently derived pool.
                  // No formula fits both sides of that step.
                  hpBuffs: { inf: { 1: 1.00, 2: 1.50, 3: 1.50, 4: 1.70, 5: 1.70, 6: 1.10, 7: 1.10, 8: 1.12, 9: 1.12, 10: 1.14, 11: 1.14, 12: 1.16, 13: 1.16, 14: 1.18, 15: 1.18, 16: 1.20, 17: 1.20, 18: 1.22, 19: 1.22, 20: 1.25 },
                             ht:  { 1: 1.00, 2: 1.00, 3: 1.10, 4: 1.10, 5: 1.15, 6: 1.15, 7: 1.20, 8: 1.20, 9: 1.25, 10: 1.25, 11: 1.30, 12: 1.30, 13: 1.35, 14: 1.35, 15: 1.40, 16: 1.40, 17: 1.45, 18: 1.45, 19: 1.50, 20: 1.50 } } },
  georg:        { label: 'Georg Bruchmüller', atkDefending: 6.0, atkAttacking: 16.8,
                  pool: 40, sits: 'first', maxLevel: 20 },
  tatiana:      { label: 'Tatiana Minchakievich (Enemy Land)', atkDefending: 6.0, atkAttacking: 45.6,
                  pool: 15, sits: 'first', maxLevel: 20 },
  hank:         { label: 'Henry “Hank” Callahan', atkDefending: 6.0, atkAttacking: 5.0,
                  pool: 40, sits: 'first', maxLevel: 10,
                  buffs: { inf: { channel: 'both', curve: { 1: 1.00, 2: 1.03, 3: 1.03, 4: 1.05, 5: 1.06, 6: 1.06, 7: 1.07, 8: 1.08, 9: 1.09, 10: 1.09 } } } },
  johan:        { label: 'Johan “Aardvark” Maes', atkDefending: 5.0, atkAttacking: 4.0,
                  pool: 40, sits: 'first', maxLevel: 20 },
  tatiana_home: { label: 'Tatiana Minchakievich (Friendly Land)', atkDefending: 5.0, atkAttacking: 10.0,
                  pool: 15, sits: 'first', maxLevel: 20 },
  maeve:        { label: 'Fiona “Maeve” Porter', atkDefending: 4.0, atkAttacking: 4.0,
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
export const HEROES_LAND_REFUSED = {
  otto:   { label: 'Otto Hersing', maxLevel: 15, terrain: 'sea', atkAttacking: 40.0,
            buffs: { sub: 1.30 },
            why: "Can't have Otto Hersing on land." },
  togo:   { label: 'Tōgō Heihachirō', maxLevel: null, terrain: 'sea', atkAttacking: 15.0,
            buffs: { bb: 1.30 },
            why: "Can't have Tōgō Heihachirō on land." },
  togo_b: { label: 'Tōgō Heihachirō w/bombardment', maxLevel: null, terrain: 'sea',
            atkAttacking: 64.32, buffs: { bb: 1.2785 },
            why: "Can't have Tōgō Heihachirō w/bombardment on land." },
  ivan:   { label: 'Ivan “Vedmid” Kovalenko', maxLevel: 10, terrain: 'sea', atkAttacking: 1.0,
            buffs: {},
            why: "Can't have Ivan “Vedmid” Kovalenko on land." },
  rbaron: { label: 'Manfred Von Richthofen', maxLevel: null, terrain: 'air', atkAttacking: 16.80,
            buffs: { int: 1.30 },
            why: "Can't have Manfred Von Richthofen on land." },
  thaden: { label: 'Wilhelm von Thaden', maxLevel: 15, terrain: 'air', atkAttacking: 10.07,
            buffs: { zep: 1.30 },
            why: "Can't have Wilhelm von Thaden on land." },
};

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

export const NOT_MEASURED = [
    { key: 'air_to_air_mechanism', what: 'WHY an air stack is attenuated against surface targets and not against other aircraft.', why: 'The scope is measured hard and modelled. Attacking land or naval, an air stack fires with what survives the round; attacking air it does not \u2014 twenty fighters lose 58% of their pool to two hundred fighters and still deal the full 20.0 x E(20) = 400.00. Embarkation is seen by every attacker including air, which is what the discriminating cell showed: against two hundred EMBARKED fighters the same stack deals 98.61, the naval column attenuated. What no black-box reading can reach is the mechanism \u2014 whether air-to-air resolves simultaneously or whether something else exempts it.', closedBy: 'nothing available. The obvious experiment is an air stack whose target cannot shoot back, and there is no such configuration: every air unit bisects to a range of 5 km and 5 km is exactly where return fire stops, so an aircraft is never out of reach of what it is attacking' },
    { key: 'return_fire_generality', what: 'Whether the 5 km return-fire cut-off is a constant or every unit\u2019s own melee reach.', why: 'Past 5 km a bombarded defender deals exactly zero while still taking the attacker\u2019s full figure. That is measured hard \u2014 lart at 4 and 5 km loses 20.00, at 6, 7 and 8 km loses nothing, and three defenders that could easily shoot back (lart reaching 30, cruiser 40, battleship 75) are all silent at 8 km, as is a mixed inf+lart defender at 6. But every unit in the roster ALSO bisected to a melee attack range of exactly 5, so "the cut-off is the constant 5" and "the cut-off is the defender\u2019s own melee reach" predict the identical number everywhere. The two are indistinguishable in this game and the engine uses the constant.', closedBy: 'nothing available \u2014 it would need a unit whose melee reach is not 5, and there is none' },
    { key: 'multi_round_heavy_units', what: 'Multi-round drift on units with large per-unit HP, and two anomalous death counts.', why: 'The round law was fitted on 50-vs-50 INFANTRY at 0.042%. Cavalry reproduces exactly too, but heavy tanks drift to 0.5% by round four \u2014 260 HP per unit makes the whole-unit survivor count coarse and the model more sensitive to it. Separately, the printed death count is the sum of per-round floor(round damage / per-unit HP), which reproduces 10 of 12 measured cells; infantry rounds 3 and 4 come out one short and nothing explains it.', closedBy: 'a maxRounds ladder on two or three more unit types, chosen for their per-unit HP' },
  { key: 'air_E_above_20_rival', what: 'Whether an attenuated air stack above 20 units uses E(survivors) or a per-unit sum of m(f).', why: 'The post-fire law now reproduces attenuated stacks at 10, 25, 40 and 50 units \u2014 three exactly and 40 units to 0.11% \u2014 so it does hold above the knee, which is what the app needs. But the RIVAL hypothesis was not properly separated: the two formulations I wrote reduce to the same expression for these stack sizes, so this is a confirmation of one law rather than a discrimination between two.', closedBy: 'a rival stated so it actually differs, then one cell where they disagree' },
                { key: 'hero_other_terrain_levels', what: 'The six air/naval heroes DEFENDING, and at any level but 10.', why: 'All six are decomposed ATTACKING at level 10 — own attack separated from multiplier with two attacker types apiece — and each buffs the thing its namesake commanded: Hersing submarines, von Thaden zeppelins, Richthofen fighters, T\u014dg\u014d battleships. Ivan buffs nothing and attacks at 1.00. What none of them has been read at is a DEFENDING stack, or any level but 10, and the land heroes proved both of those matter — thirteen of sixteen have different attack and defence values, and every curve moves with level.', closedBy: 'the same two-configuration decomposition run defending, plus a level sweep' },

  ];

// ---------------------------------------------------------------------------
// PROVENANCE
// ---------------------------------------------------------------------------
// Free-form notes keyed by constant name. Every note says where the number was
// measured, how well, and what it is NOT evidence for.

export const PROVENANCE = {
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
    note: 'The min(n,50) cap does real work: uncapped, n=57 predicts 13.67 where 14.0 was measured. Untested at n in 21-28, 31-44, 46-49 and above 113 — interpolation there is derived, not measured, and the curve is smooth with every gap bracketed.',
  },
  'm_f': {
    confidence: 'measured',
    source: 'results.jsonl, experiment=hp_scaling: 10 points at 10% intervals, 10 infantry attacking 50 infantry.',
    formula: 'm(f) = 0.05 + 0.95f, f = current HP / full HP for the whole stack.',
    residual: 'ZERO deviation at all ten points.',
    note: 'The 0.05 floor is real: a stack at 10% HP deals 14.5% of full damage. The POOL scales linearly with f with no floor. Only the ATTACKER\'s HP was swept, and only for infantry — that m(f) applies to a defender or to any other unit type is assumed.',
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
    note: 'Whether the death count clamps to the stack size when a damaged stack is wiped was never read: the hp_scaling rows record no death figure.',
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
    formula: 'DR = 0.15 * (fortressHP / 50 + 1), continuous in CURRENT HP. At full HP that is 0.15 * (level + 1).',
    residual: 'Observed defender loss ratios 0.6999 / 0.5499 / 0.3998 / 0.2498 / 0.0997 against 0.70 / 0.55 / 0.40 / 0.25 / 0.10 — every level within 0.002.',
    note: 'The "+1" discontinuity is in the game: having ANY fortress costs the attacker 15% before levels count. The page prints the decay directly — "DR: 60% -> 57.5%" for a level-3 fortress that has taken 8.5 damage, and 0.15*(141.5/50+1) = 57.45%. The round\'s damage uses the START-OF-ROUND value. Only the defender\'s UNITS are protected: the fortress\'s own damage is not reduced, and the fortress does not reduce the defender\'s output.',
    limits: 'Levels 1-5 only, and only against a land (infantry) attacker on the defending side. At level 6 the formula returns DR = 1.05, so it must saturate or the cap is real; unmeasured either way.',
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
    confidence: 'derived',
    source: 'One observation per type (railway/aerodrome/harbor L1 = 60, barracks L2 = 80, factory L3 = 120, recruiting L1 = 5.0 and destroyed outright by the 8.5 damage).',
    note: 'Only the fortress has HP per level confirmed at more than one level. "40 per level" for the factory is 120/3 from a single reading.',
  },
  'BUILDINGS.hp.workshop': {
    confidence: 'measured at L3 only',
    source: '35 HP total at level 3, with 20 in the top level.',
    note: 'Workshop HP is NOT uniform per level. 5 + 10 + 20 = 35 is a plausible doubling series and is assumed, not measured — only L3 was ever flown. Two requests would settle it.',
  },
  'BUILDINGS.maxLevel.server': {
    confidence: 'measured',
    source: 'The server states each cap itself: "oops: max level for X is N", read by parse_max_level(). Fortress 5, barracks 2, recruiting / railway / aerodrome / harbor 1.',
  },
  'BUILDINGS.maxLevel.unknown': {
    confidence: 'unmeasured',
    note: 'The sweep asked workshop and factory for level 3, was not rejected, and never probed higher. The form\'s lvl select offers 1-5 for every type, which is a UI cap and not a server cap. The true cap is at least 3 and otherwise unknown.',
  },

  'TRENCH_POOL': {
    confidence: 'derived',
    source: 'results.jsonl, experiment=trenches: 10 rows, 10 infantry vs 10 infantry, one session.',
    method: 'pool = lost / pct with the attacker\'s output invariant at exactly 40.0, so each multiplier is a BRACKET, not a reading. See TRENCH_POOL_BRACKET.',
    note: 'Levels 4, 5, 15 and 20 each bracket a clean 2-decimal value. Level 10 does not: [1.2382, 1.2463] excludes 1.25, and the carried value 1.24 is not pinned to 2 decimals. The pool bonus applies while ATTACKING as well as defending (attacker trench 20 gave pool x1.35 and turned 2 deaths into 1). Levels 1-3 confer no pool bonus at all.',
    limits: 'Infantry only. That the multiplier is unit-independent and purely multiplicative is assumed.',
  },
  'TRENCH_OUTPUT': {
    confidence: 'measured',
    source: 'Same 10 rows. These come from an absolute HP-lost figure rather than a ratio of rounded numbers, so they are precise to ±0.001 — much better than the pool multipliers.',
    note: 'DEFENDER only: an attacker at trench 20 left the defender\'s loss at exactly 40.0, the control value. The curve is not smooth — it plateaus at x1.40 across levels 4 AND 5 — so both schedules are probably table lookups rather than formulas (assumed; bytro.js contains no trench logic at all, only form handling).',
    limits: 'Measured only at n = 10, where E(n) = n. Whether the bonus multiplies the base stat or the effective unit count is therefore undetermined, and the two diverge above 20 units.',
  },
  'TRENCH.gaps': {
    confidence: 'unmeasured',
    note: 'Levels 6-9, 11-14 and 16-19 were never submitted: 12 of 21 levels. Interpolation is assumed and, given the x1.40 plateau, demonstrably risky. Both sampled sequences are non-decreasing, so a value at an unsampled level can be BRACKETED by its sampled neighbours — that bracketing is what the engine reports, and it rests on an assumption of monotonicity, not on a reading.',
  },

  'resolution_order': {
    confidence: 'derived (single round)',
    note: '1. The defender\'s fortress DR is computed from the fortress HP at ROUND START. 2. Both sides\' outputs come from the PRE-round state, except an AIR attacker against GROUND, which uses its post-fire state. 3. Damage is applied; building damage is additive and unmitigated. 4. deaths = floor(HP lost / trench-inflated per-unit max HP). Every measurement used maxRounds=1, so this is a description of ONE round and multi-round iteration is unmeasured.',
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
    note: 'The base stat is measured and unchanged between modes. The ATTRITION COEFFICIENT is '
      + 'not pinned: nine cells give 0.360-0.427 and the residual does not track the loss '
      + 'fraction, so the delivery is probably discrete rather than a smooth fraction. 3/8 is a '
      + 'working value inside the range, not a measurement. Any patrol result is labelled '
      + 'estimated for this reason alone.',
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
    confidence: 'estimated',
    source: 'joffre_home at levels 1,2,4,5,9,10,11,15; hank at 1,2,5,9,10; kangal at 1,5,10.',
    note: 'ONLY the buff varies with level, and only for two heroes. Its measured points are '
      + 'stored verbatim; a level between them is INTERPOLATED and the app says so. From level '
      + '5 up joffre_home is exactly 1.10 + 0.02*level, but levels 1-4 (1.10, 1.15, -, 1.16) '
      + 'do not fit that or any step, so no formula is used.',
  },
  'integrity': {
    confidence: 'measured',
    note: 'results.jsonl grew from 150 to 168 rows during the session that produced these tables, when a concurrent session flew the patrol experiment. The 18 patrol rows are single-sample and their multi-tick GROUND law does not close (predicted tick 3/4 defender output 3.5/3.5 against observed 3.4/3.3), so the patrol ATTRITION is implemented as an explicitly estimated band (see PATROL.attritionRange), never as a measured value; its maxRounds behaviour IS measured and is implemented as such. Two patrol findings do bear on the app: maxRounds is ignored entirely for terrain=air (0.25/0.5/0.75/1 return byte-identical results), and patrol out-damages a direct air strike in all 9 cells measured.',
  },
};
