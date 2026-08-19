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
    code: 'bal', label: 'Balloon', cls: 'air',
    maxHP: null, maxHPBracket: null,
    atk: null, def: null,
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
  // bal: absent. Never measured, and cannot be submitted in air terrain.
};

// A ground unit's defence output while an air stack attacks it.
// NOT the same as a ground unit attacking air, which is unmeasured.
export const GROUND_DEFENCE_VS_AIR = {
  inf: 0.4, cav: 1.0, ac: 8.0, lart: 0.2, art: 0.3,
  rrg: 0.7, lt: 3.0, ht: 4.0, convoy: 0.5, st: 1.0,
};

// Damage a stack deals to BUILDINGS, per effective unit. One unit type has
// ever been measured. Absence from this table means "no reading exists".
export const BUILDING_DAMAGE_PER_EFFECTIVE_UNIT = {
  inf: 0.3,
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
  0: 1.00, 1: 1.00, 2: 1.00, 3: 1.00,
  4: 1.15, 5: 1.20, 10: 1.24, 15: 1.30, 20: 1.35,
};

// The brackets these point values came from. pool = lost / pct, and pct is
// printed to 3 significant figures, so each is an interval, not a reading.
// Note level 10: [1.2382, 1.2463] EXCLUDES 1.25. Do not "tidy" it to 1.25 —
// the measurement forbids it.
export const TRENCH_POOL_BRACKET = {
  0: [0.9974, 1.0026], 1: [0.9974, 1.0026], 2: [0.9974, 1.0026], 3: [0.9974, 1.0026],
  4: [1.1460, 1.1529], 5: [1.1939, 1.2014], 10: [1.2382, 1.2463],
  15: [1.2943, 1.3031], 20: [1.3466, 1.3561],
};

export const TRENCH_OUTPUT = {
  0: 1.00, 1: 1.25, 2: 1.30, 3: 1.35,
  4: 1.40, 5: 1.40, 10: 1.54, 15: 1.62, 20: 1.75,
};

export const TRENCH_SAMPLED_LEVELS = [0, 1, 2, 3, 4, 5, 10, 15, 20];
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
                  buffs: { ac: { channel: 'defence', curve: { 1: 1.08, 5: 1.13, 10: 1.20 } } } },
  joffre:       { label: 'Joseph Joffre (Non Homeland)', atkDefending: 16.0, atkAttacking: 4.0,
                  pool: 120, sits: 'first', maxLevel: 15 },
  joffre_home:  { label: 'Joseph Joffre (Homeland)', atkDefending: 16.0, atkAttacking: 4.0,
                  pool: 120, sits: 'first', maxLevel: 15,
                  buffs: { inf: { channel: 'defence', curve: { 1: 1.10, 2: 1.15, 4: 1.16, 5: 1.20, 9: 1.28, 10: 1.30, 11: 1.32, 15: 1.40 } },
                           ac:  { channel: 'defence', curve: { 1: 1.10, 5: 1.20, 10: 1.30, 15: 1.40 } } },
                  hpBuffs: { ac: { 1: 1.00, 5: 1.09, 10: 1.17, 15: 1.30 } } },
  marco:        { label: 'Fiero “Marco” Martello', atkDefending: 15.0, atkAttacking: 24.6,
                  pool: 60, sits: 'first', maxLevel: 10,
                  hpBuffs: { lt: { 1: 1.00, 5: 1.07, 10: 1.12 } } },
  allen:        { label: 'Viscount Allenby', atkDefending: 10.0, atkAttacking: 29.6,
                  pool: 50, sits: 'first', maxLevel: 15 },
  larab:        { label: 'Lawrence of Arabia', atkDefending: 10.0, atkAttacking: 45.0,
                  pool: 75, sits: 'first', maxLevel: 20 },
  alvin:        { label: 'Alvin C. York', atkDefending: 8.30, atkAttacking: 25.0,
                  pool: 100, sits: 'first', maxLevel: 20,
                  buffs: { st: { channel: 'both', curve: { 1: 1.15, 5: 1.25, 10: 1.40, 15: 1.50, 20: 1.60 } } },
                  hpBuffs: { st: { 1: 1.00, 5: 1.14, 10: 1.22, 15: 1.34, 20: 1.42 } } },
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
                  hpBuffs: { inf: { 1: 1.00, 2: 1.50, 3: 1.50, 4: 1.70, 5: 1.70, 6: 1.10, 7: 1.10, 8: 1.12, 9: 1.12, 10: 1.14, 15: 1.18, 20: 1.25 },
                             ht:  { 1: 1.00, 5: 1.15, 10: 1.25, 15: 1.40, 20: 1.50 } } },
  georg:        { label: 'Georg Bruchmüller', atkDefending: 6.0, atkAttacking: 16.8,
                  pool: 40, sits: 'first', maxLevel: 20 },
  tatiana:      { label: 'Tatiana Minchakievich (Enemy Land)', atkDefending: 6.0, atkAttacking: 45.6,
                  pool: 15, sits: 'first', maxLevel: 20 },
  hank:         { label: 'Henry “Hank” Callahan', atkDefending: 6.0, atkAttacking: 5.0,
                  pool: 40, sits: 'first', maxLevel: 10,
                  buffs: { inf: { channel: 'both', curve: { 1: 1.00, 2: 1.03, 5: 1.06, 9: 1.09, 10: 1.09 } } } },
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
export const HEROES_LAND_REFUSED = {
  otto:   { label: 'Otto Hersing',                 maxLevel: 15, why: "Can't have Otto Hersing on land. On a NAVAL stack it works and adds 40.00 — measured, not yet decomposed." },
  togo:   { label: 'Tōgō Heihachirō',              maxLevel: null, why: "Can't have Tōgō Heihachirō on land. On a NAVAL stack it works and adds 15.00 — measured, not yet decomposed." },
  togo_b: { label: 'Tōgō Heihachirō w/bombardment', maxLevel: null, why: "Can't have Tōgō Heihachirō w/bombardment on land. On a NAVAL stack it works and adds 64.34 — measured, not yet decomposed." },
  ivan:   { label: 'Ivan “Vedmid” Kovalenko',      maxLevel: 10, why: "Can't have Ivan “Vedmid” Kovalenko on land. On a NAVAL stack it works and adds 1.00 — measured, not yet decomposed." },
  rbaron: { label: 'Manfred Von Richthofen',       maxLevel: null, why: "Can't have Manfred Von Richthofen on land. On an AIR stack it works and adds 16.85 to the attack — measured, but not yet split into own-attack and multiplier." },
  thaden: { label: 'Wilhelm von Thaden',           maxLevel: 15, why: "Can't have Wilhelm von Thaden on land. On an AIR stack it works and adds 10.14 — measured, not yet decomposed." },
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
  {
    key: 'land_off_diagonal',
    what: 'Land vs land: the per-pairing ATTACK coefficient. Largely answered — see why.',
    why: 'A land attacker\u2019s TOTAL output does not depend on what it is shooting at. '
      + 'Its diagonal coefficient x E(n) reproduces every reading on record to 0.23% — nine '
      + 'attackers against a nine-type defender, plus two genuinely non-diagonal cases '
      + '(25 ac + 25 st and 30 inf + 30 st against heavy tanks, both exact). The target '
      + 'dependence that does exist lives entirely in how the damage is SPLIT, and that is '
      + 'measured for all nine targets. So the 100-cell matrix is not 100 unknowns: it is '
      + 'one diagonal plus a three-value target table. What is still untested is a duel '
      + 'between two single types off the diagonal, which would confirm it directly rather '
      + 'than through mixtures, and whether the same holds against AIR or NAVAL targets — '
      + 'it demonstrably does not for an air attacker.',
    closedBy: 'a handful of single-type off-diagonal duels, not the full 100-cell sweep',
  },
  { key: 'naval_off_diagonal', what: 'Naval unit vs a different naval unit (6 of 9 pairings).', why: 'Only the three diagonals were flown.', closedBy: 'a 6-cell naval sweep' },
  { key: 'ground_attacking_air', what: 'A ground stack ATTACKING an air stack.', why: 'Only ground DEFENDING against air was measured. The roles are not interchangeable.', closedBy: 'a ground-attacks-air sweep' },
  { key: 'air_defending', what: 'An air stack DEFENDING against a ground attacker.', why: 'Never submitted.', closedBy: 'the same sweep' },
  { key: 'air_off_diagonal', what: 'Air vs a different air unit.', why: 'Only int/tac/zep diagonals exist; bal not even that.', closedBy: 'a 6-cell air sweep' },
  { key: 'sea_land_air', what: 'Any sea-vs-land or sea-vs-air pairing.', why: 'Entirely absent from the record.', closedBy: 'a cross-class sweep' },
  { key: 'balloon', what: 'The Balloon: max HP, attack, defence, class interactions — every quantity.', why: 'Sending bal in air terrain aborts the whole batch server-side with no error, so it has four rows in results.jsonl and all four are empty.', closedBy: 'unknown; the request itself fails' },
  { key: 'building_damage_per_unit', what: 'Damage to buildings from any unit but infantry.', why: 'Infantry deal 0.3 per effective unit. Nothing else in the model predicts that number, so it cannot be inferred for other units.', closedBy: 'one request per unit type against a building' },
  { key: 'multi_round', what: 'Battles longer than one round.', why: 'EVERY measurement in results.jsonl used maxRounds=1. Round-to-round carry-over, whether m(f) re-evaluates, and whether fortress DR decays across rounds are all unmeasured.', closedBy: 'a maxRounds sweep' },
  { key: 'air_E_above_20', what: 'Which effective-count law an attenuated air stack above 20 units uses.', why: 'All 30 attenuated stacks were 10 units, where E(n) = n, so E(n_alive)·m(f_after) and a per-unit sum of m(f_i) are indistinguishable. They diverge above 20.', closedBy: 'one air_vs_ground cell with a 30-unit air stack' },
  { key: 'E_with_m_above_20', what: 'E(n) combined with m(f) for n > 20.', why: 'Only a 10-unit stack was ever damaged.', closedBy: 'an hp_scaling sweep at n=30' },
  { key: 'air_wiped', what: 'An air attacker reduced to zero survivors.', why: 'The post-fire law divides by the survivor count; at zero survivors it has no measured branch.', closedBy: 'one deliberately lopsided air_vs_ground cell' },
  { key: 'attenuation_scope', what: 'Whether post-fire evaluation applies to sea, or to air defending.', why: 'Only air-attacks-ground was measured; air-vs-air and sea-vs-sea are argued unattenuated from roundness, not read.', closedBy: 'a lopsided sea duel' },
  { key: 'm_f_generality', what: 'Whether m(f) applies to defenders and to units other than infantry.', why: 'The HP sweep varied only an ATTACKING infantry stack.', closedBy: 'an hp_scaling sweep on the defender' },
  { key: 'E_gaps', what: 'E(n) at n in 21-28, 31-44, 46-49, and above 113.', why: 'Interpolation only; the sampled endpoints bracket every gap.', closedBy: 'a few cheap counts' },
  { key: 'terrain', what: 'Terrain modifiers, and debark semantics.', why: 'The terrain experiment has never run and debark has never been submitted once. Patrol IS modelled, but its attrition coefficient is a band (0.360-0.427) rather than a value, so patrol results are estimates.', closedBy: 'a terrain sweep, and a patrol count-sweep at fixed loss fraction to pin the coefficient' },
  { key: 'variance', what: 'simulateVariance (a ±10% roll).', why: 'Never sampled. Unknown whether it rolls per unit or per unit-type per round.', closedBy: 'a repeated-request sweep' },
  { key: 'trench_gaps', what: 'Trench levels 6-9, 11-14, 16-19 (12 of 21).', why: 'Never submitted. Neither trench curve is smooth — output plateaus at x1.40 across levels 4 and 5 — so interpolation is demonstrably risky.', closedBy: '12 requests' },
  { key: 'trench_generality', what: 'Trench multipliers for any unit but infantry, and whether the output bonus multiplies the stat or the effective unit count.', why: 'Only 10v10 infantry was flown, and at n=10 E(n)=n, so the two readings of the output bonus are indistinguishable.', closedBy: 'one trench row with a 30-unit stack' },
  { key: 'trench_10_pool', what: 'The level-10 pool multiplier beyond 2 decimal places.', why: 'Bracketed to [1.2382, 1.2463], which excludes the tidy 1.25.', closedBy: 'a larger stack, which tightens the bracket' },
  { key: 'fortress_edges', what: 'A fortress on the ATTACKING side; a fortress against air or naval attackers; fortress-trench interaction; DR above level 5.', why: 'Only a level 1-5 fortress defending against infantry was measured. At level 6 the formula returns DR = 1.05, so it must saturate or the cap is real.', closedBy: 'a handful of requests' },
  { key: 'building_caps', what: 'Workshop and factory level caps; workshop HP per level.', why: 'The sweep asked for 3, was not rejected, and never probed higher. Workshop shows 35 total at L3 with 20 in the top level, so HP is not uniform per level.', closedBy: 'two requests' },
  { key: 'hero_level_gaps', what: 'Hero buff levels between the ones submitted — typically 2-4, 6-9, 11-14, 16-19.', why: 'Curves were read at 1, 5, 10, 15 and 20 and are INTERPOLATED between those points. Pershing\u2019s infantry HP curve proves interpolation can mislead: it drops from x1.70 to x1.10 between levels 5 and 6, so a gap can hide a step. The engine marks any unmeasured level as interpolated rather than exact.', closedBy: 'filling in the levels, ~15 requests per curve' },
  { key: 'hero_other_terrain', what: 'What the six land-refused heroes DO on an air or naval stack.', why: 'All six work there and all six change the battle — rbaron +16.85 and thaden +10.14 on air, otto +40.00, togo +15.00, togo_b +64.34, ivan +1.00 on sea. That is one reading each, which confounds the hero\u2019s own attack with any multiplier, so nothing is applied. The help page also describes multi-round and positional skills for T\u014dg\u014d and Lucien, and this project has measured neither dimension.', closedBy: 'the two-configuration decomposition already used on land, run on an air stack and a naval one' },
  { key: 'hero_hp_level_gaps', what: 'Whether a hero\u2019s own HP pool or its 0.40 damage weight move with anything.', why: 'Both read constant across every level and stack size on record, but neither was swept deliberately — the readings are a by-product of other experiments.', closedBy: 'a handful of requests at the extremes' },
  { key: 'position', what: 'Position / range effects.', why: 'Every run was at position 0.', closedBy: 'a position sweep' },
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
    confidence: 'unmeasured',
    source: 'results.jsonl: bal has 4 unit_stats rows and 10 air_vs_ground rows, and every one of them has empty readings.',
    note: 'The probe refuses to send bal with terrain=air because doing so aborts the entire batch server-side with no error message. Nothing about this unit is known: not max HP, not attack, not defence. Do not interpolate it from the other fliers.',
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
