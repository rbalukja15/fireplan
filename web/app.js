/* ==========================================================================
   app.js — UI layer for the clean-room Supremacy 1914 battle model.

   This file owns the DOM and nothing else. It does not know a single combat
   constant: every number it renders comes out of ./data.js and ./engine.js,
   and every number it renders must be traceable through Result.derivation.

   House rule, from HANDOVER.md §0: a confident wrong answer is the failure
   mode this project keeps hitting. So:
     - a value the engine did not return is drawn as an em dash, never as 0;
     - a matchup the engine flags as estimated/unknown is impossible to miss;
     - if simulate() throws or the modules fail to load, the app says so
       instead of showing a stale or invented figure.
   ========================================================================== */

/* --------------------------------------------------------------------------
   0. Module load. Static imports cannot be caught, so these are dynamic:
      a missing engine should produce an explanation, not a blank page.
   -------------------------------------------------------------------------- */

let DATA = null;
let ENGINE = null;

try {
  [DATA, ENGINE] = await Promise.all([
    import('./data.js'),
    import('./engine.js'),
  ]);
} catch (err) {
  showFatal(err, 'load');
}

/**
 * The stop-everything banner. `phase` matters: saying "the modules failed to
 * load" when in fact the UI threw is itself a confident wrong answer, and this
 * is the one message a reader has no way to check.
 */
function showFatal(err, phase) {
  const box = document.getElementById('fatal');
  const body = document.getElementById('fatal-body');
  const app = document.getElementById('app');
  if (app) app.hidden = true;
  if (!box || !body) return;
  const msg = (err && err.message) ? err.message : String(err);
  const lead = phase === 'load'
    ? 'data.js and engine.js could not be loaded, so nothing can be computed.'
    : 'The model loaded, but the interface failed while starting up, so no result on this page can be trusted.';
  body.textContent =
    lead + ' Rather than show numbers it cannot back, the calculator has stopped. Details: ' + msg +
    (phase === 'load' && location.protocol === 'file:'
      ? ' — note this page is open over file://, where browsers block ES modules. Serve the folder over HTTP instead.'
      : '');
  box.hidden = false;
}

/* boot() is invoked at the very bottom of this file: it depends on consts
   declared below, which are in their temporal dead zone up here. */

/* --------------------------------------------------------------------------
   1. Small helpers
   -------------------------------------------------------------------------- */

const $ = (id) => document.getElementById(id);
const EM_DASH = '—';

const CLASS_LABEL = { land: 'Land', air: 'Air', sea: 'Naval' };
const SIDES = [
  { key: 'attacker', label: 'Attacker' },
  { key: 'defender', label: 'Defender' },
];

/* Note on two contract exports this file deliberately does not touch:
   TRENCH_POOL / TRENCH_OUTPUT are read only through engine.trenchFactors(),
   and matchup coverage only through simulate().coverage, so the UI never
   second-guesses the engine's interpretation of its own tables. */

/** Format an HP-like figure. Returns null when there is nothing to show. */
function fmt(v, dp = 2) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  return n.toFixed(dp);
}

/** Format a count. */
function fmtInt(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  return String(Math.round(n));
}

/**
 * Strict numeric read of an engine field.
 *
 * Number(null) === 0 and Number('') === 0, both of which pass Number.isFinite.
 * Coercing an absent field that way turns "not returned" into a confident
 * zero — which is how a null hpLost came out as "0.0% of the pool". Every
 * read of a Result field goes through here.
 */
function numOrNull(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/**
 * Share of the pool a side lost, as 0..100, or null.
 *
 * Derived from hpLost/pool wherever both exist, because that is unambiguous.
 * `pctLost` is only a fallback: the contract does not fix whether it is a
 * fraction or a percentage, and guessing wrong by 100x is exactly the class
 * of confident-wrong-number this project exists to avoid.
 */
function pctOf(side) {
  if (!side) return null;
  const lost = numOrNull(side.hpLost);
  // No HP figure, no share-of-pool figure. Printing "0.0% of the pool" beside
  // an em dash would invent a loss of zero out of an absent measurement.
  if (lost === null) return null;
  const pool = numOrNull(side.pool);
  if (pool !== null && pool > 0) return (lost / pool) * 100;
  const p = numOrNull(side.pctLost);
  if (p === null) return null;
  return (p > 0 && p <= 1) ? p * 100 : p;
}

function fmtPct(v) {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  return n.toFixed(1) + '%';
}

/**
 * A combat stat or a multiplier. Shown with at least one decimal, because
 * "attack 4" and "×1" read as rounded-off integers when they are exact values.
 */
function fmtStat(v, minDp = 1) {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  const tidy = n.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
  const dp = (tidy.split('.')[1] || '').length;
  return n.toFixed(Math.max(minDp, dp));
}

/**
 * An effective-unit count, to one decimal.
 *
 * E(n) produces thirds — E(30) is 28.3333… — and printing all of them suggests
 * a measurement to four decimals when the quantity is exact arithmetic over a
 * whole number. One decimal is what the source page itself shows.
 */
function fmtEff(v) {
  const n = numOrNull(v);
  return n === null ? null : n.toFixed(1);
}

/** A general-purpose number for the derivation table: tidy, never lossy. */
function fmtLoose(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'string') return v;
  if (typeof v === 'boolean') return v ? 'yes' : 'no';
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  if (Number.isInteger(n)) return String(n);
  const s = n.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
  return s;
}

/** Write text into an element, substituting an em dash for a missing value. */
function setFig(el, text, missingTitle) {
  if (!el) return;
  if (text === null || text === undefined) {
    el.textContent = EM_DASH;
    el.classList.add('figure-none');
    el.title = missingTitle || 'The engine did not return this value.';
  } else {
    el.textContent = text;
    el.classList.remove('figure-none');
    el.removeAttribute('title');
  }
}

/** Flatten free-form provenance into one readable line. */
function provText(p) {
  if (p === null || p === undefined) return '';
  if (typeof p === 'string') return p;
  if (typeof p === 'number' || typeof p === 'boolean') return String(p);
  if (Array.isArray(p)) return p.map(provText).filter(Boolean).join(' · ');
  if (typeof p === 'object') {
    return Object.entries(p)
      .map(([k, v]) => {
        const t = provText(v);
        return t ? `${k}: ${t}` : '';
      })
      .filter(Boolean)
      .join(' · ');
  }
  return String(p);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

/* --------------------------------------------------------------------------
   2. State
   -------------------------------------------------------------------------- */

const UNITS = DATA ? (DATA.UNITS || {}) : {};
const BUILDINGS = DATA ? (DATA.BUILDINGS || {}) : {};
const PATROL = DATA ? (DATA.PATROL || { observedAdvantage: {} }) : { observedAdvantage: {} };
const HEROES = DATA ? (DATA.HEROES || {}) : {};
const HEROES_REFUSED = DATA ? (DATA.HEROES_LAND_REFUSED || {}) : {};

const UNIT_CODES = Object.keys(UNITS);
const BUILDING_CODES = Object.keys(BUILDINGS);

/**
 * The canonical roster order, used for DISPLAY and for the add-unit menu.
 *
 * It is not the order the server computes in. That was the claim here until a
 * nine-type ladder was measured: a stack draws its effective units STRONGEST
 * FIRST, by the damage coefficient in use, and roster order only looked right
 * because every mixture measured before it was infantry + artillery — an
 * ordering the two rules agree on. Each row's own readout shows what it
 * actually drew.
 */
const ROSTER_ORDER = (DATA && Array.isArray(DATA.ROSTER_ORDER) && DATA.ROSTER_ORDER.length)
  ? DATA.ROSTER_ORDER.filter((c) => UNITS[c])
  : UNIT_CODES.slice();

/** The server refuses a repeated type, so a stack is a SET of at most this many. */
const MAX_ROWS = (DATA && Number(DATA.MAX_UNIT_ROWS) > 0) ? Number(DATA.MAX_UNIT_ROWS) : 8;

function rosterRank(code) {
  const i = ROSTER_ORDER.indexOf(code);
  return i === -1 ? ROSTER_ORDER.length : i;
}

/** A unit whose own stats were never measured cannot be modelled honestly. */
function isUnmeasuredUnit(u) {
  return !u || u.maxHP === null || u.maxHP === undefined ||
         u.atk === null || u.atk === undefined ||
         u.def === null || u.def === undefined;
}

function defaultUnit() {
  if (UNITS.inf) return 'inf';
  const firstMeasured = ROSTER_ORDER.find((c) => !isUnmeasuredUnit(UNITS[c]));
  return firstMeasured || ROSTER_ORDER[0] || UNIT_CODES[0] || '';
}

function newRow(unit, count) {
  return {
    unit: unit || defaultUnit(),
    count: Number.isFinite(count) ? count : 30,
    hpPct: 100,
  };
}

const DEFAULT_STATE = () => ({
  attacker: { rows: [newRow()], trench: 0, buildings: [], hero: null },
  defender: { rows: [newRow()], trench: 0, buildings: [], hero: null },
  rounds: 1,
  mode: 'strike',
  terrain: 'land',
  // Empty means "same as the attacker's", which is what every reading before
  // the terrain sweep assumed. It is a real axis: the target's terrain picks
  // the coefficient column, not just the attacker's.
  defenderTerrain: '',
  distance: 0,
  // Both stacks attacking each other. Measured as TWO engagements, and it is
  // the half of the form this project never submitted until now.
  mutual: false,
  // FIGHT IT OUT BY DEFAULT. Nobody knows the round number in advance -- it is
  // an OUTPUT of the battle, not an input to it -- and asking for one was this
  // research rig leaking into the product, because every MEASUREMENT used
  // exactly one round. The source calculator ships with maxRounds at 100 and
  // its help page says a battle runs "until one side dies" unless you say
  // otherwise, so this is also the faithful default.
  fightToEnd: true,
});

const FIGHT_OUT_ROUNDS = 100;

let state = DEFAULT_STATE();

/* --- stack helpers ------------------------------------------------------- */

function rowsOf(side) {
  const s = state[side];
  if (!s) return [];
  if (!Array.isArray(s.rows) || !s.rows.length) s.rows = [newRow()];
  return s.rows;
}

/** Keep a stack in roster order, which is the order the game computes it in. */
function sortRows(side) {
  rowsOf(side).sort((a, b) => rosterRank(a.unit) - rosterRank(b.unit));
}

/**
 * Unit codes this side may still add, in roster order. `exceptIndex` keeps the
 * row's own current type available to itself — a select that excluded it would
 * have no valid selected option.
 */
function availableUnits(side, exceptIndex) {
  const used = new Set(
    rowsOf(side).map((r, i) => (i === exceptIndex ? null : r.unit)).filter(Boolean)
  );
  return ROSTER_ORDER.filter((c) => !used.has(c));
}

function totalCount(cfgSide) {
  return (cfgSide.rows || []).reduce((n, r) => n + (Number(r.count) || 0), 0);
}

function stackClasses(cfgSide) {
  return new Set((cfgSide.rows || []).map((r) => (UNITS[r.unit] || {}).cls).filter(Boolean));
}

/** "30 x Infantry + 10 x Artillery", or a count once that gets long. */
function stackLabel(cfgSide) {
  const rows = cfgSide.rows || [];
  if (!rows.length) return EM_DASH;
  if (rows.length <= 2) {
    return rows.map((r) => `${fmtInt(r.count)} × ${(UNITS[r.unit] || {}).label || r.unit}`).join(' + ');
  }
  return `${rows.length} types, ${fmtInt(totalCount(cfgSide))} units`;
}

/**
 * Effective units per row.
 *
 * Preferred source is the engine's own effectiveByRow(). The fallback applies
 * the same pinned law using the engine's E(n) — it is not a second model, and
 * if the engine offers neither primitive the row shows an em dash rather than
 * a number this file invented.
 */
function effectiveOf(rows) {
  const plain = rows.map((r) => ({ unit: r.unit, count: Number(r.count) || 0 }));

  if (ENGINE && typeof ENGINE.effectiveByRow === 'function') {
    try {
      const out = ENGINE.effectiveByRow(plain);
      if (Array.isArray(out) && out.length === rows.length) {
        return out.map((o) => numOrNull(o && o.effective));
      }
    } catch { /* fall through to the law below */ }
  }

  if (ENGINE && typeof ENGINE.effectiveUnits === 'function') {
    try {
      const order = plain.map((r, i) => ({ r, i }))
        .sort((a, b) => rosterRank(a.r.unit) - rosterRank(b.r.unit) || a.i - b.i);
      const eff = new Array(rows.length).fill(null);
      let seen = 0;
      for (const { r, i } of order) {
        const c = Math.max(0, r.count);
        eff[i] = ENGINE.effectiveUnits(seen + c) - ENGINE.effectiveUnits(seen);
        seen += c;
      }
      return eff;
    } catch { /* fall through */ }
  }

  return rows.map(() => null);
}

/** E(n) for a count on its own — what the row would get with no stack-mates. */
function soloEffective(count) {
  if (!ENGINE || typeof ENGINE.effectiveUnits !== 'function') return null;
  try { return numOrNull(ENGINE.effectiveUnits(Math.max(0, Number(count) || 0))); }
  catch { return null; }
}

/* --------------------------------------------------------------------------
   3. Boot
   -------------------------------------------------------------------------- */

function boot() {
  if (!UNIT_CODES.length) {
    throw new Error('data.js exported no units, so there is nothing to calculate.');
  }

  buildStack('attacker');
  buildStack('defender');
  buildRoster();

  const fromHash = decodeState(location.hash);
  if (fromHash) state = fromHash;
  writeStateToDom();

  // Live recalculation. `input` covers typing, sliders and select changes.
  $('builders').addEventListener('input', onInput);
  $('builders').addEventListener('change', onCommit);
  $('rounds').addEventListener('input', onInput);
  $('rounds').addEventListener('change', onCommit);
  for (const id of ['terrain', 'def-terrain', 'distance', 'mutual', 'fight-out']) {
    if (!$(id)) continue;
    $(id).addEventListener('input', onInput);
    $(id).addEventListener('change', onCommit);
  }
  $('mode').addEventListener('change', onInput);


  $('builders').addEventListener('click', (ev) => {
    const addRow = ev.target.closest('[data-add-row]');
    if (addRow) { addUnitRow(addRow.dataset.addRow); return; }
    const rmRow = ev.target.closest('[data-remove-row]');
    if (rmRow) { removeUnitRow(rmRow.dataset.side, Number(rmRow.dataset.index)); return; }
    const add = ev.target.closest('[data-add-bldg]');
    if (add) { addBuilding(add.dataset.addBldg); return; }
    const rm = ev.target.closest('[data-remove-bldg]');
    if (rm) { removeBuilding(rm.dataset.side, Number(rm.dataset.index)); }
  });

  $('run').addEventListener('click', runBattle);
  // ENTER IS THE BUTTON. Both halves of this are needed and the first one alone
  // is a trap: a form with several inputs and no submit button does not fire
  // `submit` on Enter at all in Chrome, so a submit listener looks right, reads
  // right, and never runs. Caught by driving it in a real browser rather than
  // by reasoning about it — the keydown handler is what actually works, and the
  // submit listener stays because a browser that DOES submit must not reload
  // the page (there is no action and no handler; it would look like a crash).
  const onEnter = (ev) => {
    if (ev.key !== 'Enter') return;
    if (ev.target.tagName === 'BUTTON' || ev.target.tagName === 'TEXTAREA') return;
    ev.preventDefault();
    onCommit();
    runBattle();
  };
  $('builders').addEventListener('submit', (ev) => { ev.preventDefault(); runBattle(); });
  $('builders').addEventListener('keydown', onEnter);
  $('global-row').addEventListener('keydown', onEnter);
  $('swap').addEventListener('click', swapSides);
  $('reset').addEventListener('click', () => {
    state = DEFAULT_STATE();
    writeStateToDom();
    runBattle();          // Reset: a complete new state, and nobody wants to
                          // press Start Battle to see the default battle.
  });
  $('share').addEventListener('click', copyLink);

  window.addEventListener('hashchange', () => {
    const s = decodeState(location.hash);
    if (!s) {
      // An in-page anchor — the skip link, or the sticky bar — has just
      // replaced the encoded battle in the URL with "#result". Put it back, or
      // Copy link hands out a link to an anchor instead of to this battle.
      syncHash(currentConfig());
      return;
    }
    state = s;
    writeStateToDom();
    runBattle();          // A shared link must show its battle, not a stale
                          // panel and an invitation to press a button.
  });

  // The working panel is the differentiator, so it is open where there is
  // room for it and one tap away where there is not. Cosmetic: never let it
  // take the app down if the environment lacks matchMedia.
  try {
    $('working').open = typeof window.matchMedia === 'function'
      ? window.matchMedia('(min-width: 760px)').matches
      : window.innerWidth >= 760;
  } catch {
    $('working').open = true;
  }

  // Printing. A closed <details> prints nothing whatever the stylesheet says,
  // so the working and the roster are opened for the print and put back after.
  const printables = [$('working'), $('roster')].filter(Boolean);
  let printMemo = null;
  window.addEventListener('beforeprint', () => {
    printMemo = printables.map((d) => d.open);
    for (const d of printables) d.open = true;
  });
  window.addEventListener('afterprint', () => {
    if (printMemo) printables.forEach((d, i) => { d.open = printMemo[i]; });
    printMemo = null;
  });

  // Tells the classic fallback script at the foot of index.html to stand down;
  // it fires only when nothing here ever ran.
  window.__appBooted = true;
  $('fatal').hidden = true;

  $('stickybar').hidden = false;
  document.body.classList.add('has-sticky');
  $('app').hidden = false;

  runBattle();            // First paint: the default battle is computed, so
                          // the page never opens on an empty outcome.
}

/* --------------------------------------------------------------------------
   4. Building the stack forms
   -------------------------------------------------------------------------- */

function buildStack(side) {
  const meta = SIDES.find((s) => s.key === side);
  const tpl = $('stack-tpl').innerHTML
    .replaceAll('{s}', side)
    .replaceAll('{S}', meta.label);
  $('stack-' + side).innerHTML = tpl;

  fillTrenchSelect($(side + '-trench'));
  renderRows(side);
  renderHero(side);
}

/**
 * HP as the source form takes it: "85%" is a percentage, "17.3" is absolute.
 *
 * The game shows you ABSOLUTE hit points -- the Army Details tab gives 17.3,
 * not 86.5% -- so demanding a percentage made the reader do arithmetic the
 * calculator is for. dxcalc's own field is pattern="[\d.]+%?" and accepts
 * either, and so does this one now.
 *
 * `maxHP` is the row's max INCLUDING any hero HP buff, which matters and is
 * documented on the source's help page: with Marco in the stack a light tank's
 * displayed HP is out of the buffed maximum, so an absolute figure has to be
 * divided by the buffed max or it reads low. A percentage is the same number
 * either way, which is exactly why the page recommends it in that case.
 *
 * Returns null for anything unparseable rather than a silent 100: a typo that
 * quietly becomes "undamaged" is the sort of confident wrong answer this whole
 * project is organised against.
 */
function parseHp(text, maxHP) {
  const s = String(text == null ? '' : text).trim();
  if (!s) return null;
  const m = /^([\d]*\.?[\d]+)\s*(%?)$/.exec(s);
  if (!m) return null;
  const n = Number(m[1]);
  if (!Number.isFinite(n) || n <= 0) return null;
  const pct = m[2] === '%'
    ? n
    : (maxHP > 0 ? (n / maxHP) * 100 : null);
  if (pct === null) return null;
  return {
    pct: Math.min(100, Math.max(0.01, Math.round(pct * 1e4) / 1e4)),
    wasPercent: m[2] === '%',
  };
}

/** Clamp a percentage, keeping decimals. This used to Math.round(). */
function clampHp(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return 100;
  return Math.min(100, Math.max(0.01, Math.round(n * 1e4) / 1e4));
}

/** Tidy display of an HP percentage: 100, 86.5, 33.3333 -> 33.33. */
function fmtHpPct(pct) {
  const n = Number(pct);
  if (!Number.isFinite(n)) return '100';
  return String(Math.round(n * 100) / 100);
}

/**
 * A row's maximum HP -- for the WHOLE ROW, not per unit.
 *
 * This is the semantics the game and the source form both use, and getting it
 * per-unit made the app unable to accept the figure a player actually has in
 * front of them. Supremacy's army panel shows "453.6 / 700.0" for 35 infantry,
 * and dxcalc's own field carries "1375.1" against a count of 75 -- which
 * cannot be per unit, since an infantryman caps at 20. Its tooltip agrees:
 * "current hit points of this unit TYPE".
 *
 * Includes a hero HP buff where one applies. Marco raises a Tank's max by 1.12
 * at level 10, and an absolute figure read off the game while Marco is in the
 * stack is out of THAT maximum -- the source's help page documents exactly
 * this trap.
 */
function rowMaxHP(side, row) {
  const unitCode = typeof row === 'string' ? row : (row && row.unit);
  const count = typeof row === 'string' ? 1 : ((row && row.count) || 1);
  const base = (UNITS[unitCode] || {}).maxHP;
  if (!base) return null;
  let per = base;
  const hero = state[side] && state[side].hero;
  if (hero && ENGINE && ENGINE.heroHpBuff) {
    try {
      const b = ENGINE.heroHpBuff(hero.code, hero.level, unitCode);
      if (b && typeof b.m === 'number') per = base * b.m;
    } catch { /* fall back to the base max */ }
  }
  return per * count;
}

/** Both hero tables, at module scope. `defOf` inside renderHero is local. */
function heroDefOf(code) {
  return HEROES[code] || HEROES_REFUSED[code] || null;
}

/** The hero's own maximum HP pool. */
function heroMaxHP(code) {
  const d = heroDefOf(code);
  return d && typeof d.pool === 'number' ? d.pool : null;
}

function clampCount(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return 1;
  return Math.min(500, Math.max(1, Math.round(n)));
}

/**
 * A unit select offering only the codes in `codes`.
 *
 * The exclusion is the point: "The same unit can't be specified twice in same
 * stack" is server-enforced, so a duplicate is not a warning case — it is a
 * stack the game will not field. The types already on this side simply are not
 * in the list, which makes the illegal state unreachable rather than corrected
 * after the fact.
 */
function fillUnitSelect(select, codes) {
  const byClass = new Map();
  for (const code of codes) {
    const u = UNITS[code];
    if (!u) continue;
    const cls = u.cls || 'other';
    if (!byClass.has(cls)) byClass.set(cls, []);
    byClass.get(cls).push(u);
  }
  const order = ['land', 'air', 'sea'];
  const rank = (c) => { const i = order.indexOf(c); return i === -1 ? order.length : i; };
  const classes = [...byClass.keys()].sort((a, b) => rank(a) - rank(b));
  for (const cls of classes) {
    const group = document.createElement('optgroup');
    group.label = CLASS_LABEL[cls] || cls;
    for (const u of byClass.get(cls)) {
      const opt = document.createElement('option');
      opt.value = u.code;
      opt.textContent = isUnmeasuredUnit(u)
        ? `${u.label} — nothing measured`
        : u.label;
      group.appendChild(opt);
    }
    select.appendChild(group);
  }
}

/* --- unit rows ----------------------------------------------------------- */

function addUnitRow(side) {
  const rows = rowsOf(side);
  if (rows.length >= MAX_ROWS) return;
  const free = availableUnits(side, -1);
  if (!free.length) return;
  const pick = free.find((c) => !isUnmeasuredUnit(UNITS[c])) || free[0];
  rows.push(newRow(pick, 10));
  sortRows(side);
  renderRows(side);
  recompute();
  // Land the caret on the type that was just added, wherever roster order put it.
  const at = rowsOf(side).findIndex((r) => r.unit === pick);
  const sel = $(`${side}-r${at}-unit`);
  if (sel) sel.focus();
}

function removeUnitRow(side, index) {
  const rows = rowsOf(side);
  if (rows.length <= 1) return;            // a stack must hold something
  rows.splice(index, 1);
  renderRows(side);
  recompute();
  const btn = $(`${side}-addrow`);
  if (btn && !btn.disabled) btn.focus();
}

/**
 * Rebuild one side's rows. Called on structural change only — adding or
 * removing a row, or changing a type, all of which alter what the OTHER rows
 * may offer. Typing in a count or an HP box does not come through here, so the
 * caret is never yanked out of a field mid-number.
 */
function renderRows(side) {
  const list = $(side + '-rows');
  if (!list) return;
  list.textContent = '';

  const rows = rowsOf(side);
  const meta = SIDES.find((s) => s.key === side);

  rows.forEach((r, i) => {
    const li = el('li', 'urow');
    li.dataset.index = String(i);
    const uid = `${side}-r${i}`;

    const grid = el('div', 'urow-grid');

    // --- type -------------------------------------------------------------
    const unitField = el('div', 'field field-unit');
    const unitLabel = el('label', null, 'Unit');
    unitLabel.htmlFor = uid + '-unit';
    const unitSel = document.createElement('select');
    unitSel.id = uid + '-unit';
    unitSel.setAttribute('aria-describedby', uid + '-stats');
    const offer = availableUnits(side, i);
    if (!offer.includes(r.unit) && UNITS[r.unit]) offer.push(r.unit);
    offer.sort((a, b) => rosterRank(a) - rosterRank(b));
    fillUnitSelect(unitSel, offer);
    unitSel.value = r.unit;
    unitSel.addEventListener('change', () => {
      r.unit = unitSel.value;
      sortRows(side);
      renderRows(side);
      recompute();
      const at = rowsOf(side).findIndex((x) => x.unit === r.unit);
      const again = $(`${side}-r${at}-unit`);
      if (again) again.focus();
    });
    unitField.append(unitLabel, unitSel);

    // --- count ------------------------------------------------------------
    const countField = el('div', 'field field-count');
    const countLabel = el('label', null, 'Count');
    countLabel.htmlFor = uid + '-count';
    const count = document.createElement('input');
    count.type = 'number';
    count.id = uid + '-count';
    count.min = '1'; count.max = '500'; count.step = '1';
    count.inputMode = 'numeric';
    count.value = String(r.count);
    // The count is where saturation is felt, so both readouts describe it: a
    // screen reader hears "25.0 effective of 40" and why, not just the number
    // that was typed in.
    count.setAttribute('aria-describedby', `${uid}-eff ${uid}-note`);
    countField.append(countLabel, count);

    // --- HP % -------------------------------------------------------------
    // HP, in either form the source form accepts: "85%" or an absolute "17.3".
    // A number input with step=1 was rejecting both the decimal and the unit
    // the game actually shows you.
    const hpField = el('div', 'field field-hp');
    const hpLabel = el('label', null, 'HP');
    hpLabel.htmlFor = uid + '-hp';
    const hp = document.createElement('input');
    hp.type = 'text';
    hp.id = uid + '-hp';
    hp.setAttribute('pattern', '[\\d.]+%?');
    hp.inputMode = 'decimal';
    hp.autocomplete = 'off';
    hp.spellcheck = false;
    hp.title = 'Either a percentage (85%) or the absolute hit points the game '
      + 'shows in Army Details (17.3).';
    hp.value = r.hpText === undefined ? `${fmtHpPct(r.hpPct)}%` : r.hpText;
    // The conversion readout lives in the row's stats line below, NOT in this
    // cell: .urow-grid is align-items:end over a 5.4em column, so anything
    // added inside the field made it taller, pushed the input up off the
    // baseline its neighbours sit on, and wrapped mid-phrase.
    hp.setAttribute('aria-describedby', uid + '-stats');
    hpField.append(hpLabel, hp);

    // --- remove -----------------------------------------------------------
    const rm = el('button', 'btn btn-small btn-icon', '×');
    rm.type = 'button';
    rm.dataset.removeRow = '1';
    rm.dataset.side = side;
    rm.dataset.index = String(i);
    const uLabel = (UNITS[r.unit] || {}).label || r.unit;
    if (rows.length <= 1) {
      rm.disabled = true;
      rm.title = 'A stack has to hold at least one unit type.';
    }
    rm.setAttribute('aria-label', `Remove ${uLabel} from the ${meta.label.toLowerCase()} stack`);

    grid.append(unitField, countField, hpField, rm);
    li.appendChild(grid);

    // --- readouts, filled by updateStackNotes() ---------------------------
    const stats = el('p', 'urow-stats', '');
    stats.id = uid + '-stats';
    li.appendChild(stats);

    const effWrap = el('div', 'urow-eff');
    effWrap.id = uid + '-eff';
    const effNum = el('span', 'eff-num', EM_DASH);
    effNum.id = uid + '-effnum';
    const bar = el('span', 'eff-bar');
    bar.id = uid + '-bar';
    bar.setAttribute('aria-hidden', 'true');
    bar.append(el('i'), el('u'));
    effWrap.append(effNum, bar);
    li.appendChild(effWrap);

    const note = el('p', 'urow-note', '');
    note.id = uid + '-note';
    li.appendChild(note);

    list.appendChild(li);
  });

  const addBtn = $(side + '-addrow');
  if (addBtn) {
    const full = rows.length >= MAX_ROWS;
    const noneLeft = !availableUnits(side, -1).length;
    addBtn.disabled = full || noneLeft;
    addBtn.title = full
      ? `A stack holds at most ${MAX_ROWS} unit types.`
      : (noneLeft ? 'Every unit type is already in this stack.' : '');
  }
}

function fillTrenchSelect(select) {
  const levels = [];
  for (let i = 0; i <= 20; i++) levels.push(i);
  for (const lvl of levels) {
    const opt = document.createElement('option');
    opt.value = String(lvl);
    let suffix = '';
    if (lvl > 0) {
      const f = safeTrench(lvl);
      if (f && f.exact === false) suffix = ' · not sampled';
    }
    opt.textContent = (lvl === 0 ? 'None' : 'TL ' + lvl) + suffix;
    select.appendChild(opt);
  }
}

function safeTrench(level) {
  if (!ENGINE || typeof ENGINE.trenchFactors !== 'function') return null;
  try { return ENGINE.trenchFactors(level); } catch { return null; }
}

/* --------------------------------------------------------------------------
   5. Buildings
   -------------------------------------------------------------------------- */

function defaultBuildingCode() {
  return BUILDINGS.fortress ? 'fortress' : (BUILDING_CODES[0] || '');
}

function addBuilding(side) {
  if (!BUILDING_CODES.length) return;
  state[side].buildings.push({ code: defaultBuildingCode(), level: 1, hpPct: 100 });
  renderBuildings(side);
  recompute();
}

function removeBuilding(side, index) {
  state[side].buildings.splice(index, 1);
  renderBuildings(side);
  recompute();
}

function maxLevelOf(code) {
  const b = BUILDINGS[code];
  if (!b) return 5;
  const m = Number(b.maxLevel);
  return Number.isFinite(m) && m > 0 ? m : 5;
}

/**
 * The hero picker. One per stack — the game refuses a second — so this is a
 * select and a level box, not a list.
 *
 * Heroes with nothing measured against a land stack are still OFFERED, in a
 * separate group, because omitting them would imply they do not exist. They
 * are labelled with the server's own refusal and the engine withholds their
 * effect rather than treating the absence as a zero.
 */

/**
 * How the hero's own HP reads back, folded into the clause that already names
 * its pool -- "with 60 HP of its own, currently on 34.2 of them (57%)".
 * Pushed as a separate sentence it collided with the next clause and repeated
 * the pool: "with 60 HP of its own currently 34.2 of 60 HP and multiplies...".
 *
 * A hero's output scales with its own HP by the same m(f) a unit obeys, so
 * this is a figure that changes the answer, not decoration.
 */
function heroHpPhrase(hero, def) {
  if (!hero || !def) return '';
  if (hero.hpBad) return ' — HP not a number, last value kept';
  const pct = hero.hpPct === undefined ? 100 : hero.hpPct;
  if (pct === 100) return '';
  const abs = Math.round((pct / 100) * def.pool * 100) / 100;
  return `, currently on ${fmtLoose(abs)} of them (${fmtHpPct(pct)}%)`;
}

function renderHero(side) {
  const sel = $(side + '-hero');
  const lvlBox = $(side + '-hero-lvl');
  const hpBox = $(side + '-hero-hp');
  const note = $(side + '-hero-note');
  if (!sel || !lvlBox) return;
  // BOTH tables. The six air/naval heroes are fully modelled now -- own attack
  // per side, curves, pools, level ranges -- so the level box has to be live
  // for them too. Looking only in HEROES left it disabled and stuck at 10,
  // which is exactly the state the record was in before they were measured.
  const defOf = (code) => HEROES[code] || HEROES_REFUSED[code] || null;
  const cur = state[side].hero;

  if (!sel.dataset.built) {
    const none = document.createElement('option');
    none.value = '';
    none.textContent = 'No hero';
    sel.appendChild(none);
    const known = document.createElement('optgroup');
    known.label = 'Measured on land';
    for (const [code, h] of Object.entries(HEROES)) {
      const o = document.createElement('option');
      o.value = code;
      const tg = h.buffs ? Object.keys(h.buffs) : [];
      o.textContent = `${h.label} — atk ${h.atk}`
        + (tg.length ? ` — buffs ${tg.map((c) => (UNITS[c] || {}).label || c).join(' + ')}` : '');
      known.appendChild(o);
    }
    sel.appendChild(known);
    const bad = document.createElement('optgroup');
    // These six are fully modelled now -- attacking and defending, across
    // their level ranges. What is still true is where they can fight, which is
    // what the label says.
    bad.label = 'Air and naval stacks only';
    for (const [code, h] of Object.entries(HEROES_REFUSED)) {
      const o = document.createElement('option');
      o.value = code;
      o.textContent = h.label;
      bad.appendChild(o);
    }
    sel.appendChild(bad);
    sel.dataset.built = '1';

    // Bound HERE, not at boot: buildStack() rewrites the panel's innerHTML,
    // so a listener attached before that is attached to a discarded node and
    // the level box silently never enables.
    sel.addEventListener('change', () => {
      const code = sel.value;
      const def = HEROES[code];
      state[side].hero = code
        ? { code, level: def ? Math.min(10, def.maxLevel) : 10 }
        : null;
      renderHero(side);
      recompute();
    });
    lvlBox.addEventListener('input', () => {
      const cur2 = state[side].hero;
      if (!cur2) return;
      const def = defOf(cur2.code);
      cur2.level = Math.max(1, Math.min(def ? def.maxLevel : 20,
        Number(lvlBox.value) || 1));
      renderHero(side);
      recompute();
    });
    // A HERO'S OWN OUTPUT SCALES WITH ITS OWN HP, by the same m(f) a unit
    // obeys, so this box changes the answer. Every hero reading in the record
    // was taken at 100% because nothing had ever varied it.
    if (hpBox) {
      hpBox.addEventListener('input', () => {
        const cur2 = state[side].hero;
        if (!cur2) return;
        // Heroes have hit points like anything else, and the game shows them
        // absolutely. Same field semantics as a unit row: "85%" or "34.2".
        cur2.hpText = hpBox.value;
        const parsed = parseHp(hpBox.value, heroMaxHP(cur2.code));
        if (parsed) cur2.hpPct = parsed.pct;
        cur2.hpBad = !parsed;
        // Re-render the hero block too: its note is where the HP now reads
        // back in both forms, and dropping this call left that line frozen.
        // The box itself is safe -- renderHero skips it while it has focus.
        renderHero(side);
        recompute();
      });
    }
  }

  sel.value = cur ? cur.code : '';
  const def = cur && defOf(cur.code);
  lvlBox.disabled = !def;
  if (hpBox) hpBox.disabled = !def;
  if (def) {
    lvlBox.max = String(def.maxLevel);
    lvlBox.value = String(Math.min(cur.level || 1, def.maxLevel));
    if (hpBox && document.activeElement !== hpBox) {
      hpBox.value = cur.hpText === undefined
        ? `${fmtHpPct(cur.hpPct === undefined ? 100 : cur.hpPct)}%` : cur.hpText;
    }
  }

  if (!cur) {
    note.textContent = 'Every figure on this page assumes no hero unless one is chosen here.';
    note.className = 'field-note';
  } else if (def) {
    const lvl = Number(lvlBox.value);
    // A hero has two attack columns. Show the one this side actually uses,
    // and name the other, because thirteen of sixteen differ and pershing
    // differs by a factor of eight.
    const mine = side === 'attacker' ? def.atkAttacking : def.atkDefending;
    const other = side === 'attacker' ? def.atkDefending : def.atkAttacking;
    const pieces = [`Fights as one unit at attack ${mine} `
      + `(${side === 'attacker' ? 'attacking' : 'defending'}; it is ${other} `
      + `${side === 'attacker' ? 'defending' : 'attacking'})`
      + `, with ${def.pool} HP of its own${heroHpPhrase(cur, def)}`];
    // Per unit type. All nine land types were screened together, so a hero
    // with no entry here buffs no land type's OUTPUT — that is a measurement
    // now, not an untested gap. The HP channel is separate and unmodelled.
    const targets = def.buffs ? Object.keys(def.buffs) : [];
    const shown = targets.map((c) => {
      const b = ENGINE.heroBuff(cur.code, lvl, c, side);
      return { code: c, b, label: (UNITS[c] || {}).label || c,
               channel: def.buffs[c].channel };
    });
    const inexact = shown.concat(
      Object.keys(def.hpBuffs || {}).map((c) => ({
        b: ENGINE.heroHpBuff(cur.code, lvl, c) }))
    ).find((x) => x.b.m !== 1 && !x.b.exact);
    const live = shown.filter((x) => x.b.m !== 1);
    const dead = shown.filter((x) => x.b.m === 1);
    pieces.push(live.length
      ? 'and multiplies ' + live.map((x) => `${x.label} output by ×${x.b.m.toFixed(2)}`)
        .join(' and ')
      : (dead.length
        ? `whose ${dead.map((x) => x.label).join(' and ')} buff is DEFENCE-ONLY `
          + '(measured at exactly zero attacking), so it does nothing here'
        : 'and buffs no land unit type\u2019s output (all nine were screened '
          + 'together)'));
    pieces.push(`(caps at level ${def.maxLevel} — the server refuses higher)`);
    // The HP channel is MODELLED now, so this says what the pools already
    // include rather than warning that they are wrong.
    const hpB = def.hpBuffs || {};
    const hpShown = Object.keys(hpB).map((c) => {
      const b = ENGINE.heroHpBuff(cur.code, lvl, c);
      return { label: (UNITS[c] || {}).label || c, b };
    }).filter((x) => x.b.m !== 1);
    const hpTxt = hpShown.length
      ? ' It also raises the max HP of '
        + hpShown.map((x) => `${x.label} (×${x.b.m.toFixed(3)})`).join(' and ')
        + ' — a separate channel, already included in the pools below.'
      : '';
    note.textContent = pieces.join(' ') + '.'
      + (inexact ? ' ' + inexact.b.note.charAt(0).toUpperCase()
                     + inexact.b.note.slice(1) + '.' : '') + hpTxt;
    // Warn only when a level was never submitted. An HP buff is no longer a
    // defect to flag — it is modelled, and the pools already carry it.
    note.className = inexact ? 'field-note is-warn' : 'field-note';
  } else {
    const r = HEROES_REFUSED[cur.code];
    if (r) {
      const buffed = Object.keys(r.buffs || {});
      const unit = buffed.length ? (UNITS[buffed[0]] || {}).label || buffed[0] : null;
      note.textContent = `${r.why} It fights on `
        + `${r.terrain === 'air' ? 'an AIR' : 'a NAVAL'} stack: `
        + `${r.atkAttacking} attacking, ${r.atkDefending} defending`
        + (unit
          ? `, and multiplies ${unit} output`
          + (Object.values(r.buffs)[0].channel === 'attack'
            ? ' when attacking only (measured at exactly 1.0000 defending).'
            : ' on both sides.')
          : ', and buffs no unit type (measured).')
        + (r.atkAttackingCurve
          ? ' Its own attack MOVES WITH LEVEL, which no land hero\u2019s does.'
          : '')
        + (r.poolCurve ? ' So does its own HP pool.' : '');
      note.className = 'field-note';
    } else {
      note.textContent = 'Unrecognised hero.';
      note.className = 'field-note is-warn';
    }
  }
}

function renderBuildings(side) {
  const list = $(side + '-bldgs');
  if (!list) return;
  list.textContent = '';

  state[side].buildings.forEach((b, i) => {
    const row = el('li', 'bldg-row');
    const uid = `${side}-b${i}`;

    const typeSel = document.createElement('select');
    typeSel.id = uid + '-type';
    typeSel.setAttribute('aria-label', `Building ${i + 1} type`);
    for (const code of BUILDING_CODES) {
      const opt = document.createElement('option');
      opt.value = code;
      opt.textContent = BUILDINGS[code].label || code;
      typeSel.appendChild(opt);
    }
    typeSel.value = b.code;
    typeSel.addEventListener('change', () => {
      b.code = typeSel.value;
      b.level = Math.min(b.level, maxLevelOf(b.code));
      renderBuildings(side);
      renderHero(side);
      recompute();
    });

    const lvlSel = document.createElement('select');
    lvlSel.id = uid + '-lvl';
    lvlSel.setAttribute('aria-label', `Building ${i + 1} level`);
    for (let l = 1; l <= maxLevelOf(b.code); l++) {
      const opt = document.createElement('option');
      opt.value = String(l);
      opt.textContent = 'L' + l;
      lvlSel.appendChild(opt);
    }
    lvlSel.value = String(Math.min(b.level, maxLevelOf(b.code)));
    lvlSel.addEventListener('change', () => { b.level = Number(lvlSel.value); recompute(); });

    const hp = document.createElement('input');
    hp.type = 'number';
    hp.min = '0.1'; hp.max = '100'; hp.step = 'any';
    hp.value = String(b.hpPct);
    hp.id = uid + '-hp';
    // The bar is the TOP LEVEL only, 0-50, exactly as the game shows it: a
    // level-4 fortress reads "5 / 50" when it is battered, not "20 / 200".
    hp.setAttribute('aria-label',
      `Building ${i + 1}: percent of the top level's HP bar`);
    hp.title = 'Percent of the TOP level\u2019s 50-HP bar, which is the bar the '
      + 'game shows. A level-4 fortress at 5/50 is 10% here, and holds '
      + '3x50 + 5 = 155 HP in total.';
    hp.addEventListener('input', () => {
      const n = Number(hp.value);
      b.hpPct = Number.isFinite(n) ? Math.min(100, Math.max(0.1, n)) : 100;
      recompute();
    });

    const rm = el('button', 'btn btn-small btn-icon', '×');
    rm.type = 'button';
    rm.dataset.removeBldg = '1';
    rm.dataset.side = side;
    rm.dataset.index = String(i);
    rm.setAttribute('aria-label', `Remove building ${i + 1}`);

    row.append(typeSel, lvlSel, hp, rm);

    const def = BUILDINGS[b.code] || {};
    const flag = el('p', 'bldg-flag');
    if (def.mitigates) {
      flag.classList.add('is-good');
      flag.textContent = side === 'defender'
        ? 'Reduces damage to the defending units. Measured.'
        : 'Damage reduction on the attacking side was never measured.';
    } else {
      flag.textContent = 'No damage reduction — measured combat-inert. It only soaks damage of its own.';
    }
    row.appendChild(flag);

    list.appendChild(row);
  });
}

/* --------------------------------------------------------------------------
   6. State <-> DOM
   -------------------------------------------------------------------------- */

function writeStateToDom() {
  for (const { key } of SIDES) {
    sortRows(key);
    renderRows(key);
    $(key + '-trench').value = String(state[key].trench);
  }
  $('rounds').value = String(state.rounds);
  if ($('terrain')) $('terrain').value = state.terrain;
  if ($('def-terrain')) $('def-terrain').value = state.defenderTerrain || '';
  if ($('mutual')) $('mutual').checked = !!state.mutual;
  if ($('fight-out')) {
    $('fight-out').checked = !!state.fightToEnd;
    const box = $('rounds');
    const lab = $('rounds-label');
    if (box) { box.disabled = !!state.fightToEnd; box.hidden = !!state.fightToEnd; }
    if (lab) lab.hidden = !!state.fightToEnd;
  }
  if ($('distance')) $('distance').value = String(state.distance);
  $('mode').value = state.mode === 'patrol' ? 'patrol' : 'strike';
  renderBuildings('attacker');
  renderBuildings('defender');
}

function readDomToState() {
  for (const { key } of SIDES) {
    rowsOf(key).forEach((r, i) => {
      const count = $(`${key}-r${i}-count`);
      const hp = $(`${key}-r${i}-hp`);
      if (count) r.count = clampCount(count.value);
      if (hp) {
        // Keep what was typed, so the field does not reformat under the
        // cursor, and derive the percentage the engine wants from it.
        r.hpText = hp.value;
        const parsed = parseHp(hp.value, rowMaxHP(key, r));
        // An unparseable box leaves the last good value in place rather than
        // silently becoming 100%.
        if (parsed) r.hpPct = parsed.pct;
        r.hpBad = !parsed;
      }
      // The type is not read here: it only ever changes through its own
      // handler, which re-sorts and re-renders the whole side.
    });
    const t = Number($(key + '-trench').value);
    state[key].trench = Number.isFinite(t) ? Math.min(20, Math.max(0, Math.round(t))) : 0;
  }
  const r = Number($('rounds').value);
  state.rounds = Number.isFinite(r) && r > 0 ? r : 1;
  state.mode = $('mode').value === 'patrol' ? 'patrol' : 'strike';
  if ($('terrain')) {
    state.terrain = ['land', 'sea', 'debark'].includes($('terrain').value)
      ? $('terrain').value : 'land';
  }
  if ($('def-terrain')) {
    state.defenderTerrain = ['land', 'sea', 'air', 'debark']
      .includes($('def-terrain').value) ? $('def-terrain').value : '';
  }
  if ($('distance')) {
    const dkm = Number($('distance').value);
    state.distance = Number.isFinite(dkm) && dkm > 0 ? Math.round(dkm) : 0;
  }
  if ($('mutual')) state.mutual = !!$('mutual').checked;
  if ($('fight-out')) state.fightToEnd = !!$('fight-out').checked;
}

function onInput() {
  readDomToState();
  recompute();
}

/**
 * A committed edit — blur, Enter, or a spinner click.
 *
 * readDomToState() clamps: count to 1..500, HP to 1..100, rounds to something
 * positive. While typing that is right, but once an entry is committed the box
 * would go on showing 999 (or 0, or nothing) while the result — and the link
 * the Copy button hands out — described a different battle. Write the clamped
 * values back so the form cannot silently disagree with the figures under it.
 */
function onCommit() {
  readDomToState();
  writeNumbersToDom();
  recompute();
}

function writeNumbersToDom() {
  for (const { key } of SIDES) {
    rowsOf(key).forEach((r, i) => {
      const count = $(`${key}-r${i}-count`);
      const hp = $(`${key}-r${i}-hp`);
      if (count) count.value = String(r.count);
      if (hp && document.activeElement !== hp) {
        hp.value = r.hpText === undefined ? `${fmtHpPct(r.hpPct)}%` : r.hpText;
      }
    });
  }
  $('rounds').value = String(state.rounds);
}

function swapSides() {
  readDomToState();
  const a = state.attacker;
  state.attacker = state.defender;
  state.defender = a;
  writeStateToDom();
  runBattle();            // Swap sides: an explicit command on the whole
                          // board, not an edit to one field.
}

/* --------------------------------------------------------------------------
   7. Compute + render
   -------------------------------------------------------------------------- */

function currentConfig() {
  return {
    attacker: cloneSide(state.attacker),
    defender: cloneSide(state.defender),
    // 100 is the source calculator's own default, and the cap this project
    // has measured up to. The engine stops the moment a side is destroyed, so
    // for most battles the number never binds.
    rounds: state.fightToEnd ? FIGHT_OUT_ROUNDS : state.rounds,
    mode: state.mode,
    terrain: state.terrain,
    // Omitted rather than passed empty: the engine defaults it to the
    // attacker's, and passing '' would look like a fourth terrain.
    ...(state.defenderTerrain ? { defenderTerrain: state.defenderTerrain } : {}),
    distance: state.distance,
    ...(state.mutual ? { mutual: true } : {}),
  };
}


/** What the rounds control is currently doing, in words. */
function updateRoundsNote(result) {
  // The box's enabled state belongs here, with the rest of this control's
  // presentation. It was only set in writeStateToDom(), which runs at start-up
  // and not on every edit -- so unticking "fight to the finish" left the rounds
  // box greyed out and unusable, which is precisely the silent-dead-control
  // failure this project has now hit three times.
  // Hidden, not merely greyed out. The point of the default is that the reader
  // does not have to think about rounds at all, and a disabled box labelled
  // "stop after (rounds)" still asks them to.
  const box = $('rounds');
  const lab = $('rounds-label');
  if (box) { box.disabled = !!state.fightToEnd; box.hidden = !!state.fightToEnd; }
  if (lab) lab.hidden = !!state.fightToEnd;
  const note = $('rounds-note');
  if (!note) return;
  const rd = (result && result.rounds) || {};
  if (state.fightToEnd) {
    note.textContent = rd.decided
      ? `Running until one side is destroyed, which happened in round `
        + `${fmtLoose(rd.fought)}. Untick to stop after a fixed number instead.`
      : 'Running until one side is destroyed, or 100 rounds — the source '
        + 'calculator\u2019s own default. Untick to stop after a fixed number.';
  } else {
    note.textContent = 'Stopping after a fixed number of rounds, whether or '
      + 'not the battle is over. Tick "fight to the finish" to let it run.';
  }
}

function runBattle() {
  stale = false;
  paintStale();
  // Wrapped, and the wrapping is the point. updateHpEchoes() only writes a
  // caption under each HP box, and when it threw -- heroMaxHP reached a `defOf`
  // that is local to renderHero -- it took recompute() with it, so every figure
  // on the page silently froze at its last value while the inputs kept
  // accepting edits. A cosmetic helper must not be able to do that.
  const config = currentConfig();

  // Wrapped, and the wrapping is the point. These only write captions, and
  // when one threw -- heroMaxHP reached a `defOf` that is local to renderHero
  // -- it took recompute() with it, so every figure on the page silently froze
  // at its last value while the inputs went on accepting edits. A helper that
  // writes a caption must not be able to stop the calculation.
  try { updateStackNotes(); } catch (err) { console.error('stack notes failed', err); }
  syncHash(config);

  let result = null;
  let error = null;
  try {
    result = ENGINE.simulate(config);
  } catch (err) {
    error = err;
  }

  if (error || !result) {
    // The contract says simulate() never throws. If it did, that is a defect
    // and the honest response is to show nothing rather than something.
    renderEngineError(error);
    return;
  }

  renderCoverage(result.coverage, config);
  renderScoreboard(result, config);
  renderVerdict(result, config);
  updateRoundsNote(result);
  renderSanity(result, config);
  renderDerivation(result.derivation);
  renderSticky(result);
  announceResult(result);
}

/* THE BATTLE IS FOUGHT WHEN THE USER SAYS SO, not on every keystroke.

   It used to recompute live. That reads well in a demo and badly in use: you
   are half way through typing "120" and the page has already fought the battle
   at 1, then at 12, and the figure you are looking at belongs to a stack you
   did not mean. Worse for the reader, an outcome that changes while you type
   invites you to stop reading it.

   So input edits take the LIGHT path -- captions, the shareable link, and a
   mark saying the outcome below is out of date -- and the outcome itself is
   recomputed only by Start Battle, by Enter, or by a whole-state action whose
   intent is not in doubt (Reset, Swap sides, opening a shared link).

   Every existing caller of recompute() was an input edit, so they all keep
   their line and now mean "the inputs moved". The four that are not are named
   at their call sites and say runBattle().

   The stale result is DIMMED AND LABELLED rather than cleared. Blanking it
   would hide the very thing a reader wants while they adjust one number, and
   this page's whole argument is that you should be able to see where a figure
   came from. What it must never do is look current. */
let stale = false;

function paintStale() {
  const result = $('result');
  if (result) result.classList.toggle('is-stale', stale);
  const sticky = $('stickybar');
  if (sticky) sticky.classList.toggle('is-stale', stale);
  const note = $('stale-note');
  if (note) note.hidden = !stale;
  const btn = $('run');
  if (btn) btn.classList.toggle('btn-armed', stale);
}

function recompute() {
  // The link and the captions must NOT go stale with the result: Copy link
  // hands out the inputs as they stand, and a caption that disagreed with the
  // box above it would be a defect whoever pressed what.
  try { updateStackNotes(); } catch (err) { console.error('stack notes failed', err); }
  try { syncHash(currentConfig()); } catch (err) { console.error('hash sync failed', err); }
  // A CONTROL'S OWN STATE IS NOT A RESULT. updateRoundsNote() both writes a
  // sentence about the battle and decides whether the rounds box is visible at
  // all, so leaving it on the fought path meant unticking "fight to the finish"
  // did nothing until you pressed Start battle. That is the silent-dead-control
  // failure this project has now hit FOUR times, and it arrived within minutes
  // of adding a button — the whole point of which was to stop the page acting
  // on half-finished input. It takes a result when there is one and reads the
  // generic sentence when there is not.
  try { updateRoundsNote(null); } catch (err) { console.error('rounds note failed', err); }
  stale = true;
  paintStale();
}

/**
 * A side, in the shape the engine's contract asks for: `rows`, in roster order.
 *
 * A one-row stack also carries the flat {unit, count, hpPct} fields the older
 * single-unit contract used. They describe exactly the same stack, so no
 * reading of the config can disagree with another — this is a compatibility
 * shim for a one-row stack, not a second source of truth, and nothing above
 * one row can be expressed that way at all.
 */
function cloneSide(s) {
  const rows = (s.rows || []).map((r) => ({
    unit: r.unit,
    count: r.count,
    hpPct: r.hpPct,
  }));
  const out = {
    rows,
    trench: s.trench,
    buildings: s.buildings.map((b) => ({ code: b.code, level: b.level, hpPct: b.hpPct })),
    hero: s.hero
      ? { code: s.hero.code, level: s.hero.level,
          hpPct: s.hero.hpPct === undefined ? 100 : s.hero.hpPct }
      : null,
  };
  if (rows.length === 1) {
    out.unit = rows[0].unit;
    out.count = rows[0].count;
    out.hpPct = rows[0].hpPct;
  }
  return out;
}

/** The unit code of a row the ENGINE returned, which may hold a resolved unit. */
function rowCode(r) {
  if (!r) return null;
  const u = r.unit;
  if (typeof u === 'string') return u;
  if (u && typeof u === 'object' && u.code) return String(u.code);
  return null;
}

function renderEngineError(err) {
  const banner = $('coverage');
  banner.className = 'banner banner-unknown';
  $('coverage-headline').textContent = 'The engine could not compute this matchup';
  $('coverage-reason').textContent =
    'simulate() failed, so there is no result to show. No numbers below are current. '
    + (err && err.message ? 'Details: ' + err.message : '');
  $('coverage-caveats').textContent = '';

  const result = $('result');
  result.dataset.level = 'unknown';
  for (const id of ['sb-a-hplost', 'sb-a-deaths', 'sb-a-left', 'sb-a-dealt', 'sb-a-pool',
                    'sb-d-hplost', 'sb-d-deaths', 'sb-d-left', 'sb-d-dealt', 'sb-d-pool']) {
    setFig($(id), null, 'The engine failed on this configuration.');
  }
  $('sb-a-pct').textContent = '';
  $('sb-d-pct').textContent = '';
  for (const p of ['a', 'd']) {
    $(`sb-${p}-rows`).textContent = '';
    $(`sb-${p}-rows-note`).textContent = 'No per-unit figures: the engine failed on this configuration.';
    $(`sb-${p}-rows-note`).className = 'rowsplit-note is-warn';
  }
  $('verdict').textContent = 'No result.';
  lastHeadline = '';
  announce('The engine could not compute this matchup. No result is shown.');
  $('sanity').hidden = true;
  $('deriv-body').textContent = '';
  $('working-count').textContent = '';
  setFig($('st-a'), null);
  setFig($('st-d'), null);
}

/* --- 7a. Confidence banner ---------------------------------------------- */

const BANNER_COPY = {
  measured: {
    cls: 'banner-measured',
    icon: '✓',
    headline: 'Measured matchup',
    fallback: 'Every constant used in this result was read from live measurements of this pairing.',
  },
  estimated: {
    cls: 'banner-estimated',
    icon: '!',
    headline: 'Estimated — part of this matchup was never measured',
    fallback: 'Some constant in this result is an extrapolation from a pairing that was measured, not a reading of this one.',
  },
  unknown: {
    cls: 'banner-unknown',
    icon: '?',
    headline: 'Not measured — do not plan an attack on these numbers',
    fallback: 'No measurement covers this pairing. The figures below are what the model produces when it is asked a question it has no data for.',
  },
};

/** The level actually on screen, after any escalation. Read by renderVerdict. */
let displayedLevel = 'unknown';

/**
 * Caveats that arise from the settings rather than from the matchup: an
 * unsampled trench level, more than one round, a fortress on the attacking
 * side. The engine may or may not speak to these, so they are only added when
 * nothing it returned already covers the same ground.
 */
function uiCaveatsFor(config, engineText) {
  const out = [];
  if (Number(config.rounds) !== 1 && !engineText.includes('round')) {
    out.push(`Set to ${fmtLoose(config.rounds)} rounds. Every measurement behind this model used exactly one round, so multi-round behaviour is extrapolated.`);
  }
  for (const { key, label } of SIDES) {
    const lvl = config[key].trench;
    if (lvl > 0) {
      const f = safeTrench(lvl);
      if (f && f.exact === false && !engineText.includes('trench')) {
        out.push(`${label} trench level ${lvl} was never sampled. Levels 0–5, 10, 15 and 20 were measured; the rest are interpolated, and the measured curve is not smooth.`);
      }
    }
    if (key === 'attacker'
        && config[key].buildings.some((b) => (BUILDINGS[b.code] || {}).mitigates)
        && !engineText.includes('attacking side')) {
      out.push('A damage-reducing building was placed on the attacking side. Only fortresses on the defending side were ever measured.');
    }

    // Composite stacks. The saturation law and the damage split are measured
    // exactly — but on two-type, all-land mixtures. Going past that is
    // arithmetic the record does not witness, and it should say so.
    const rows = config[key].rows || [];
    const classes = stackClasses(config[key]);
    if (classes.size > 1 && !engineText.includes('mixes')) {
      out.push(`The ${label.toLowerCase()} stack mixes ${[...classes]
        .map((c) => (CLASS_LABEL[c] || c).toLowerCase()).join(' and ')} units in one stack. Every `
        + 'mixture ever submitted was all-land, and how a stack spanning classes is treated — one '
        + 'saturation pool or several, which coefficient each row uses — was never read.');
    } else if (rows.length > 2 && !engineText.includes('two types')) {
      out.push(`The ${label.toLowerCase()} stack has ${rows.length} unit types. Every mixture ever `
        + 'submitted had exactly two, both land (infantry with artillery, four layouts). The '
        + 'cumulative law fits all four to 0.002% and extends to more types by arithmetic, but '
        + 'nobody has ever flown a three-type stack.');
    }
  }

  // Both sides mixed. Every mixture in the record was a mixed DEFENDER facing a
  // single-type infantry attacker, so a mixture has never once fought another
  // mixture — a structural gap, and one nothing in the config panel shows.
  const aMixed = (config.attacker.rows || []).length > 1;
  const dMixed = (config.defender.rows || []).length > 1;
  if (aMixed && dMixed && !engineText.includes('both sides')) {
    out.push('Both sides are mixtures. Every composite stack ever submitted was a mixed DEFENDER '
      + 'against a single-type infantry attacker, so a mixture has never once fought another '
      + 'mixture. The saturation law is read off each stack separately, which is the natural '
      + 'reading and is not a measurement of this shape.');
  }
  return out;
}

function renderCoverage(coverage, config) {
  const engineLevel = (coverage && BANNER_COPY[coverage.level]) ? coverage.level : 'unknown';
  const engineCaveats = (coverage && Array.isArray(coverage.caveats)) ? coverage.caveats : [];
  const engineText = engineCaveats.join(' ').toLowerCase();
  const uiCaveats = uiCaveatsFor(config, engineText);

  // Escalate, never downgrade. A quiet green banner over a stack sitting in an
  // unsampled trench for three unmeasured rounds would be a lie of omission.
  const escalated = engineLevel === 'measured' && uiCaveats.length > 0;
  const level = escalated ? 'estimated' : engineLevel;
  displayedLevel = level;

  const copy = BANNER_COPY[level];
  const banner = $('coverage');
  banner.className = 'banner ' + copy.cls;
  banner.querySelector('.banner-icon').textContent = copy.icon;
  $('coverage-headline').textContent = escalated
    ? 'Estimated — the matchup is measured, but some of these settings are not'
    : copy.headline;

  const reason = coverage && coverage.reason ? String(coverage.reason) : '';
  $('coverage-reason').textContent = escalated
    ? (reason ? reason + ' What takes this out of measured territory is listed below.'
              : 'The pairing itself was measured. What takes this result out of measured territory is listed below.')
    : (reason || copy.fallback);

  const list = $('coverage-caveats');
  list.textContent = '';
  const seen = new Set();
  for (const text of [...engineCaveats, ...uiCaveats]) {
    const t = String(text || '').trim();
    if (!t || seen.has(t.toLowerCase())) continue;
    seen.add(t.toLowerCase());
    list.appendChild(el('li', null, t));
  }

  // The chips read as a bare adjective out of context — "estimated" next to
  // "Outcome" tells a screen-reader user nothing about what is estimated. The
  // prefix is hidden from sight and carried in the accessibility tree.
  const chip = $('result-chip');
  chip.textContent = '';
  chip.append(el('span', 'visually-hidden', 'Confidence: '), document.createTextNode(level));
  chip.className = 'conf-chip conf-' + level;
  $('result').dataset.level = level;

  const stConf = $('st-conf');
  stConf.textContent = '';
  stConf.append(el('span', 'visually-hidden', 'Confidence: '), document.createTextNode(level));
  stConf.className = 'sb-conf conf-' + level;
}

/* --- 7b. Scoreboard ------------------------------------------------------ */

function renderScoreboard(result, config) {
  renderSide('a', result.attacker, config.attacker);
  renderSide('d', result.defender, config.defender);
}


/**
 * The recovery bill — the nine summary columns the source page prints and this
 * app modelled none of.
 *
 * Rendered ONLY from what the engine returned. The engine yields null for the
 * whole bill whenever any row's loss or pool is unknown, and this function
 * shows an em dash rather than a partial total: a bill missing one row reads
 * exactly like a complete one, which is the failure mode this project keeps
 * hitting.
 *
 * Zero-valued resources are hidden rather than listed as 0. Infantry genuinely
 * cost nothing to replace, so an all-zero resource list is a real result and
 * the note says so instead of leaving an empty strip.
 */
function renderRepair(prefix, side) {
  const wrap = $(`sb-${prefix}-repair`);
  if (!wrap) return;
  const timeEl = $(`sb-${prefix}-repair-time`);
  const listEl = $(`sb-${prefix}-repair-res`);
  const noteEl = $(`sb-${prefix}-repair-note`);
  listEl.textContent = '';
  const bill = side && side.repair;
  if (!bill) {
    timeEl.textContent = '—';
    noteEl.textContent = side && side.rows
      ? 'Not billed: a row’s loss or pool is unknown, so the total would be short by an unknown amount.'
      : '';
    return;
  }
  const h = bill.hours;
  const days = h >= 24 ? ` (${(h / 24).toFixed(1)} days)` : '';
  timeEl.textContent = `${fmtInt(h)} h${days} to repair`;
  const NAMES = { food: 'food', fish: 'fish', iron: 'iron', wood: 'wood',
                  coal: 'coal', oil: 'oil', gas: 'gas', cash: 'cash' };
  let any = false;
  for (const k of Object.keys(NAMES)) {
    const v = bill[k];
    if (!v) continue;
    any = true;
    const li = el('li');
    li.appendChild(el('b', null, k === 'cash' ? `$${fmtInt(v)}` : fmtInt(v)));
    li.appendChild(document.createTextNode(` ${NAMES[k]}`));
    listEl.appendChild(li);
  }
  const ue = bill.unitEquivalents;
  const ueTxt = (typeof ue === 'number')
    ? `${ue.toFixed(2)} whole units’ worth destroyed` : '';
  noteEl.textContent = any
    ? ueTxt
    : `No resources: ${ueTxt || 'nothing destroyed'} — this stack costs only time to replace.`;
}

function renderSide(prefix, side, cfg) {
  const damaged = (cfg.rows || []).filter((r) => r.hpPct !== 100).length;
  $(`sb-${prefix}-name`).textContent =
    stackLabel(cfg) +
    (damaged ? (damaged === (cfg.rows || []).length ? ', damaged' : ', partly damaged') : '') +
    (cfg.trench > 0 ? `, TL ${cfg.trench}` : '');

  const s = side || {};
  setFig($(`sb-${prefix}-hplost`), fmt(s.hpLost));
  // THE VARIANCE BAND, which the engine has always computed and this page has
  // never shown. The game rolls one uniform +/-10% per side per round — ONE
  // roll for the whole stack, so a big stack cannot average its luck away —
  // and the figure above is the variance-off value. Showing it alone invites
  // the reader to treat a coin-flip as a prediction.
  const bandEl = $(`sb-${prefix}-band`);
  if (bandEl) {
    const b = s.hpLostBand;
    bandEl.textContent = (Array.isArray(b) && b[0] !== null)
      ? `${fmt(b[0])}–${fmt(b[1])} with variance on`
      : '';
  }
  setFig($(`sb-${prefix}-deaths`), fmtInt(s.deaths));
  setFig($(`sb-${prefix}-dealt`), fmt(s.damageDealt));
  setFig($(`sb-${prefix}-pool`), fmt(s.pool));

  const left = fmtInt(s.unitsLeft);
  const leftEl = $(`sb-${prefix}-left`);
  if (left === null) {
    setFig(leftEl, null);
  } else {
    setFig(leftEl, `${fmtInt(totalCount(cfg))} → ${left}`);
  }

  const pct = fmtPct(pctOf(s));
  const pctEl = $(`sb-${prefix}-pct`);
  let tail = '';
  if (s.wiped) {
    // "Destroyed" and "pool gone" are not the same event once a stack starts
    // the round below full HP: the death rule counts whole max-HP units.
    tail = isDestroyed(s) ? ' · stack destroyed' : ' · HP pool exhausted';
  }
  pctEl.textContent = pct === null ? '' : `${pct} of the pool${tail}`;

  renderRowSplit(prefix, s, cfg);
  renderRepair(prefix, s);

  // Buildings: the engine may or may not report per-building damage. Only
  // render what it actually returned.
  const list = $(`sb-${prefix}-bldg`);
  list.textContent = '';
  const reported = Array.isArray(s.buildings) ? s.buildings : null;
  cfg.buildings.forEach((b, i) => {
    const def = BUILDINGS[b.code] || {};
    const li = el('li');
    li.appendChild(el('span', null, `${def.label || b.code} L${b.level}`));
    const r = reported && reported[i];
    const lost = r ? fmt(r.hpLost) : null;
    li.appendChild(el('span', null, lost === null
      ? 'damage not reported'
      : `−${lost} HP${r && r.destroyed ? ' · destroyed' : ''}`));
    list.appendChild(li);
  });
}

/**
 * The per-unit-type breakdown of one side's result.
 *
 * The composition always comes from the config, so the reader can always see
 * WHAT is in the stack. The numbers only ever come from the engine: if it
 * returned no rows[], every numeric cell is an em dash and the note says the
 * itemisation was withheld. Splitting a stack total across rows here — by pool,
 * by count, by anything — would be this file inventing a measurement.
 */
function renderRowSplit(prefix, sideResult, cfg) {
  const body = $(`sb-${prefix}-rows`);
  const note = $(`sb-${prefix}-rows-note`);
  if (!body || !note) return;
  body.textContent = '';

  const cfgRows = cfg.rows || [];
  const engineRows = Array.isArray(sideResult && sideResult.rows) ? sideResult.rows : null;

  // Match on the unit code: the engine sorts a stack into roster order and the
  // config may not be in it, so pairing by index alone could mislabel a row.
  const byCode = new Map();
  if (engineRows) {
    engineRows.forEach((r) => {
      const c = rowCode(r);
      if (c && !byCode.has(c)) byCode.set(c, r);
    });
  }

  // The builder's own figure, used only where the engine returned no rows[]
  // and only for the effective count — which is the engine's own law either
  // way (effectiveByRow, or E(n) applied cumulatively).
  const fallbackEff = effectiveOf(cfgRows);
  let unmatched = 0;

  // The hero is a row of the stack, not an annotation on it: it takes a slot
  // in the saturating order and its output is part of the stack's total. It
  // comes from the ENGINE's rows[], never from the config's unit list, so it
  // is drawn here before them.
  const heroRow = engineRows ? engineRows.find((r) => r && r.isHero) : null;
  if (heroRow) {
    const tr = document.createElement('tr');
    tr.className = 'is-hero';
    // Pool and HP lost are real now: a hero has its own HP and takes a share
    // of every round at a weight of 0.40. Deaths stay blank — no hero row on
    // record has ever carried a death count, and 0 would be a claim.
    const cells = [
      `${heroRow.label} (hero, lvl ${heroRow.level})`,
      (typeof heroRow.effective === 'number' ? fmt(heroRow.effective, 1) : '—'),
      (typeof heroRow.pool === 'number' ? fmt(heroRow.pool) : '—'),
      (typeof heroRow.hpLost === 'number' ? fmt(heroRow.hpLost) : '—'),
      '—',
      (typeof heroRow.damageDealt === 'number' ? fmt(heroRow.damageDealt) : '—'),
    ];
    cells.forEach((text, i) => {
      const td = document.createElement('td');
      if (i > 0) td.className = 'c-val';
      td.textContent = text;
      tr.appendChild(td);
    });
    tr.title = 'A hero fights as one unit with its own HP pool, and takes a '
      + 'share of every round at a weight of 0.40 — the same for all sixteen. '
      + 'It never reports a death count, so that cell is blank, not zero.';
    body.appendChild(tr);
  }

  cfgRows.forEach((r, i) => {
    const u = UNITS[r.unit] || {};
    const er = engineRows ? (byCode.get(r.unit) || null) : null;
    if (engineRows && !er) unmatched += 1;

    const tr = document.createElement('tr');

    const name = el('td', null,
      `${fmtInt(r.count)} × ${u.label || r.unit}${r.hpPct !== 100 ? ` @ ${r.hpPct}%` : ''}`);
    tr.appendChild(name);

    const cell = (text, extraClass) => {
      const td = el('td', 'c-val' + (extraClass ? ' ' + extraClass : ''));
      if (text === null) {
        td.textContent = EM_DASH;
        td.classList.add('row-none');
      } else {
        td.textContent = text;
      }
      return td;
    };

    const eff = er ? numOrNull(er.effective) : fallbackEff[i];
    const solo = soloEffective(r.count);
    const saturated = eff !== null && solo !== null && eff < solo - 1e-6;
    tr.appendChild(cell(fmtEff(eff), saturated ? 'row-sat' : null));

    tr.appendChild(cell(er ? fmt(er.hpLost) : null));
    tr.appendChild(cell(er ? fmtInt(er.deaths) : null));
    const leftTxt = er ? fmtInt(er.unitsLeft) : null;
    tr.appendChild(cell(leftTxt === null ? null : `${fmtInt(r.count)} → ${leftTxt}`));
    tr.appendChild(cell(er ? fmt(er.damageDealt) : null));

    body.appendChild(tr);
  });

  if (!engineRows) {
    note.textContent = cfgRows.length > 1
      ? 'The engine returned this stack\'s totals but no per-row figures, so the columns above are '
        + 'withheld rather than split up here. The effective counts are the engine\'s own size law.'
      : 'The engine returned no per-row figures for this stack. The effective count is the engine\'s '
        + 'own size law; the rest is withheld.';
    note.className = 'rowsplit-note is-warn';
    return;
  }

  if (unmatched) {
    // The engine itemised the stack but not this row. Say which way round that
    // is: the row is in the battle, the figures for it are simply not here.
    note.textContent = `The engine's breakdown does not cover ${unmatched} of the `
      + `${cfgRows.length} rows in this stack, so ${unmatched === 1 ? 'that row is' : 'those rows are'} `
      + 'shown as em dashes. The stack totals above may therefore include damage this table does not.';
    note.className = 'rowsplit-note is-warn';
    return;
  }

  if (cfgRows.length > 1) {
    note.textContent = 'Incoming damage splits by attack × count — the raw count, not the saturated '
      + 'one (measured). Effective units are cumulative down this table.';
    note.className = 'rowsplit-note';
  } else {
    note.textContent = '';
    note.className = 'rowsplit-note';
  }
}

/* --- 7c. Verdict --------------------------------------------------------- */

/**
 * A stack is destroyed when no units are left, which is not the same thing as
 * `wiped` (pool exhausted): below full HP the two come apart, because deaths
 * are counted in whole max-HP units.
 */
function isDestroyed(s) {
  if (!s) return false;
  const left = numOrNull(s.unitsLeft);
  if (left !== null) return left <= 0;
  return s.wiped === true;
}

/** The outcome sentence last written, without its explanatory sub-line. */
let lastHeadline = '';

/* --- 7c-ante. The page's only live region --------------------------------
   The banner and the verdict are both rewritten on every keystroke. If both
   are live regions, a screen reader reads two paragraphs of prose each time a
   digit changes — which is how a confidence warning that matters becomes
   noise the reader tunes out, and this app's whole point is that the warning
   lands. So neither is live, and one short debounced line is posted here
   instead: confidence first, then the outcome, then where the detail is.
   -------------------------------------------------------------------------- */

let announceTimer = null;

function announce(text) {
  const box = $('live');
  if (!box) return;
  clearTimeout(announceTimer);
  announceTimer = setTimeout(() => { box.textContent = text; }, 450);
}

function announceResult(result) {
  const caveats = $('coverage-caveats').children.length;
  const bits = [`${displayedLevel} result.`];
  if (lastHeadline) bits.push(lastHeadline);
  const aHp = fmt((result.attacker || {}).hpLost);
  const dHp = fmt((result.defender || {}).hpLost);
  if (aHp !== null && dHp !== null) {
    bits.push(`Attacker loses ${aHp} HP, defender ${dHp} HP.`);
  }
  if (caveats) {
    bits.push(`${caveats} caveat${caveats === 1 ? '' : 's'} listed above the form.`);
  }
  announce(bits.join(' '));
}

function renderVerdict(result, config) {
  const a = result.attacker || {};
  const d = result.defender || {};

  // With no measurement behind the pairing there is no outcome to narrate.
  // The figures stay on screen, flagged; the sentence that would turn them
  // into a prediction does not get written.
  if (displayedLevel === 'unknown') {
    const blind = [...new Set(
      [...(config.attacker.rows || []), ...(config.defender.rows || [])]
        .map((r) => r.unit)
        .filter((c) => isUnmeasuredUnit(UNITS[c]))
    )].map((c) => (UNITS[c] || {}).label || c);
    const v0 = $('verdict');
    v0.textContent = 'No outcome can be stated for this matchup.';
    const s0 = el('span', 'vsub');
    s0.textContent = blind.length
      ? `${blind.join(' and ')} ${blind.length > 1 ? 'have' : 'has'} no measured statistics at all — not HP, not attack, not defence. The figures below are what the model emits when asked a question it has no data for. They are not a prediction.`
      : 'This pairing was never submitted to the calculator even once. The figures below are what the model emits when asked a question it has no data for. They are not a prediction.';
    v0.appendChild(s0);
    lastHeadline = 'No outcome can be stated for this matchup.';
    return;
  }

  let headline;
  const aDead = isDestroyed(a), dDead = isDestroyed(d);
  if (aDead && dDead) {
    headline = 'Both stacks are destroyed.';
  } else if (dDead) {
    headline = 'The defending stack is destroyed.';
  } else if (aDead) {
    headline = 'The attacking stack is destroyed. The attack fails.';
  } else {
    const ad = numOrNull(a.deaths), dd = numOrNull(d.deaths);
    if (ad !== null && dd !== null) {
      if (ad === 0 && dd === 0) {
        headline = 'Neither side loses a whole unit.';
      } else {
        headline = `You trade ${ad} for ${dd}.`;
      }
    } else {
      headline = 'Neither stack is destroyed.';
    }
    // A pool can empty without the death rule killing a whole unit. Saying
    // only "neither side loses a unit" would hide that the stack is spent.
    const spent = [];
    if (a.wiped) spent.push('attacker');
    if (d.wiped) spent.push('defender');
    if (spent.length) {
      headline += ` The ${spent.join(' and ')} ${spent.length > 1 ? 'have' : 'has'} no HP left.`;
    }
  }

  const sub = el('span', 'vsub');
  const parts = [];
  const an = pctOf(a), dn = pctOf(d);
  if (an !== null && dn !== null) {
    if (Math.abs(an - dn) < 0.05) {
      parts.push('Both sides lose the same share of their pool.');
    } else if (an > dn) {
      parts.push(`The attacker loses the larger share of its pool (${an.toFixed(1)}% against ${dn.toFixed(1)}%) — the exchange favours the defender.`);
    } else {
      parts.push(`The defender loses the larger share of its pool (${dn.toFixed(1)}% against ${an.toFixed(1)}%) — the exchange favours the attacker.`);
    }
  }
  // SAY WHICH ROUND IT ENDED IN, rather than reciting the round count that was
  // typed in. The round number is an OUTPUT of a battle; asking the reader for
  // one was this research rig leaking into the product.
  const rd = result.rounds || {};
  const asked = Number(config.rounds);
  if (rd.decided) {
    const loser = a.wiped && d.wiped ? 'both stacks are'
      : a.wiped ? 'the attacker is' : 'the defender is';
    parts.push(rd.fought === 1
      ? `Decided in the first round — ${loser} destroyed.`
      : `Decided in round ${fmtLoose(rd.fought)} — ${loser} destroyed.`);
  } else if (state.fightToEnd) {
    parts.push(`Still fighting after ${fmtLoose(rd.fought || asked)} rounds — `
      + 'neither stack is destroyed.');
  } else {
    parts.push(asked === 1 ? 'One round.'
      : `${fmtLoose(asked)} rounds, stopped there.`);
  }
  sub.textContent = parts.join(' ');

  const v = $('verdict');
  v.textContent = headline;
  v.appendChild(sub);
  lastHeadline = headline;
}

/* --- 7c-bis. Self-consistency --------------------------------------------
   HANDOVER §10: cheap invariants the app should assert against itself. These
   check the Result against nothing but itself and the config, so they cannot
   be wrong about the game — only about the engine. If one trips, say so
   loudly rather than render a contradiction as though it were a finding.
   -------------------------------------------------------------------------- */

function renderSanity(result, config) {
  const box = $('sanity');

  // Not run when coverage is 'unknown': there the engine is legitimately
  // emitting placeholders for quantities it has no data for, the banner
  // already says the figures are not a prediction, and calling that a defect
  // would be an accusation the app cannot support.
  if (displayedLevel === 'unknown') {
    box.hidden = true;
    box.textContent = '';
    return;
  }

  const problems = [];
  const check = (label, side, cfg) => {
    if (!side) { problems.push(`${label}: the engine returned no figures at all.`); return; }
    const n = totalCount(cfg);
    const deaths = numOrNull(side.deaths);
    const left = numOrNull(side.unitsLeft);
    const lost = numOrNull(side.hpLost);
    const pool = numOrNull(side.pool);
    if (deaths !== null && deaths > n) {
      problems.push(`${label}: ${deaths} units killed out of ${n} in the stack.`);
    }
    if (left !== null && (left < 0 || left > n)) {
      problems.push(`${label}: ${left} units left out of ${n}.`);
    }
    if (deaths !== null && left !== null && deaths + left !== n) {
      problems.push(`${label}: ${deaths} killed plus ${left} surviving does not make ${n}.`);
    }
    if (lost !== null && pool !== null && lost > pool + 1e-6) {
      problems.push(`${label}: lost ${fmt(lost)} HP from a pool of ${fmt(pool)}.`);
    }

    // Per-row, where the engine itemised. A stack total that does not equal the
    // sum of its own rows is the composite equivalent of the building row that
    // clobbered the attacker's slot for a whole phase of this project.
    const rows = Array.isArray(side.rows) ? side.rows : null;
    if (rows) {
      const seen = new Set();
      const sum = { hpLost: 0, deaths: 0, damageDealt: 0, pool: 0 };
      const any = { hpLost: false, deaths: false, damageDealt: false, pool: false };
      rows.forEach((r, i) => {
        const code = rowCode(r) || `row ${i + 1}`;
        if (seen.has(code)) {
          problems.push(`${label}: ${code} appears twice in the result, and the game refuses a `
            + 'repeated unit type in one stack.');
        }
        seen.add(code);
        for (const field of ['hpLost', 'deaths', 'damageDealt', 'pool']) {
          const v = numOrNull(r[field]);
          if (v !== null) { sum[field] += v; any[field] = true; }
        }
        const rd = numOrNull(r.deaths);
        const rleft = numOrNull(r.unitsLeft);
        const rc = numOrNull(r.count);
        if (rd !== null && rleft !== null && rc !== null && rd + rleft !== rc) {
          problems.push(`${label} / ${code}: ${rd} killed plus ${rleft} surviving does not make ${rc}.`);
        }
      });

      // A row total that does not add up to the stack total is the composite
      // version of the building row that clobbered the attacker's slot for a
      // whole phase of this project: both readings look plausible alone. Note
      // a row that reports 0 is CLAIMING zero — a quantity the engine cannot
      // itemise should come back null, and null is excluded from these sums.
      const totals = { hpLost: lost, deaths, damageDealt: numOrNull(side.damageDealt), pool };
      const words = {
        hpLost: 'lose {r} HP between them, but the stack says {t}',
        deaths: 'kill {r} units between them, but the stack says {t}',
        damageDealt: 'deal {r} damage between them, but the stack says {t}',
        pool: 'hold {r} HP of pool between them, but the stack says {t}',
      };
      for (const field of ['hpLost', 'deaths', 'damageDealt', 'pool']) {
        const t = totals[field];
        if (!any[field] || t === null) continue;
        const tol = field === 'deaths' ? 0 : 0.01;
        if (Math.abs(sum[field] - t) > tol) {
          problems.push(`${label}: the rows ` + words[field]
            .replace('{r}', field === 'deaths' ? String(sum[field]) : fmt(sum[field]))
            .replace('{t}', field === 'deaths' ? String(t) : fmt(t)) + '.');
        }
      }
    }
    // Deliberately NOT checked: `wiped` true while unitsLeft > 0. That is not
    // a contradiction — a stack at 40% HP has a pool of 0.4·n·maxHP, and the
    // measured death rule floor(HP_lost / maxHP) kills only 40% of the stack
    // when that whole pool is removed. The tension is in the measured model,
    // not in the engine, and flagging it would be a false accusation.
  };
  check('Attacker', result.attacker, config.attacker);
  check('Defender', result.defender, config.defender);

  if (!problems.length) {
    box.hidden = true;
    box.textContent = '';
    return;
  }
  box.hidden = false;
  box.textContent =
    'These figures contradict each other, which means the engine has a defect — treat the whole result as unreliable. ' +
    problems.join(' ');
}

/* --- 7d. The working ----------------------------------------------------- */

function renderDerivation(derivation) {
  const body = $('deriv-body');
  body.textContent = '';

  const rows = Array.isArray(derivation) ? derivation : [];
  $('working-count').textContent = rows.length
    ? `${rows.length} step${rows.length === 1 ? '' : 's'}`
    : 'nothing to show';

  if (!rows.length) {
    const tr = document.createElement('tr');
    const td = el('td', null, 'The engine returned no derivation for this configuration. Nothing above can be traced, so treat it with suspicion.');
    td.colSpan = 4;
    tr.appendChild(td);
    body.appendChild(tr);
    return;
  }

  rows.forEach((step, i) => {
    const tr = document.createElement('tr');

    const n = el('td', 'c-step', String(i + 1));
    const label = el('td', null, step && step.label ? String(step.label) : EM_DASH);
    const formula = el('td', 'formula', step && step.formula ? String(step.formula) : '');
    const valText = step ? fmtLoose(step.value) : null;
    const value = el('td', 'c-val');
    if (valText === null) {
      value.textContent = EM_DASH;
      value.classList.add('figure-none');
    } else {
      value.textContent = valText;
    }

    tr.append(n, label, formula, value);
    body.appendChild(tr);
  });
}

/* --- 7e. Sticky mobile bar ---------------------------------------------- */

function renderSticky(result) {
  const a = fmtInt((result.attacker || {}).deaths);
  const d = fmtInt((result.defender || {}).deaths);
  setFig($('st-a'), a);
  setFig($('st-d'), d);
}

/* --------------------------------------------------------------------------
   8. Inline notes on the inputs
   -------------------------------------------------------------------------- */

/**
 * The per-row readouts under each unit row, and the stack's saturation line.
 *
 * This is the one thing this app can teach that a per-unit-type calculator
 * cannot: a stack saturates AS A WHOLE, cumulatively, and its types draw from
 * that pool STRONGEST FIRST — so the weakest type in a stack lives on the tail
 * the stronger ones have already eaten. Forty artillery beside ten infantry
 * are worth 25 effective units, not 33.3, and no reordering recovers it,
 * because the order is the units' own strength and not anything the player
 * controls. If the row is paying that penalty, the row says so.
 */
function updateRowNotes(side) {
  const rows = rowsOf(side);
  const eff = effectiveOf(rows);

  rows.forEach((r, i) => {
    const u = UNITS[r.unit] || {};
    const uid = `${side}-r${i}`;

    // What the model knows about this type.
    const stats = $(uid + '-stats');
    if (stats) {
      if (isUnmeasuredUnit(u)) {
        stats.textContent = 'Nothing about this unit was ever measured — no HP, no attack, no defence.';
        stats.className = 'urow-stats is-danger';
      } else {
        let m = null;
        if (ENGINE && typeof ENGINE.hpMultiplier === 'function') {
          try { m = ENGINE.hpMultiplier(r.hpPct / 100); } catch { m = null; }
        }
        const bits = [
          `Max HP ${fmtLoose(u.maxHP)}`,
          `atk ${fmtStat(u.atk)}`,
          `def ${fmtStat(u.def)}`,
        ];
        // Both forms of the HP entry, so typing "17.3" confirms itself as a
        // percentage and typing "85%" confirms itself as hit points.
        // The row total, so it reads back in the same units the game shows.
        const rowMax = rowMaxHP(side, r) || (u.maxHP * r.count);
        const buffed = Math.abs(rowMax - u.maxHP * r.count) > 1e-9;
        if (r.hpBad) {
          bits.push('HP not a number — last value kept');
        } else if (r.hpPct !== 100 && m !== null) {
          const abs = Math.round((r.hpPct / 100) * rowMax * 100) / 100;
          bits.push(`at ${fmtLoose(abs)} of `
            + `${fmtLoose(Math.round(rowMax * 100) / 100)} HP`
            + `${buffed ? ' (hero-buffed)' : ''} `
            + `(${fmtHpPct(r.hpPct)}%): pool ×${(r.hpPct / 100).toFixed(2)}, `
            + `output ×${fmtStat(m, 2)}`);
        }
        stats.textContent = bits.join(' · ');
        stats.className = r.hpBad ? 'urow-stats is-warn' : 'urow-stats';
      }
    }

    const e = eff[i];
    const solo = soloEffective(r.count);
    const numEl = $(uid + '-effnum');
    const bar = $(uid + '-bar');
    const note = $(uid + '-note');

    if (numEl) {
      if (e === null) {
        numEl.textContent = EM_DASH;
        numEl.title = 'The engine did not return an effective-unit count.';
      } else {
        numEl.textContent = `${fmtEff(e)} effective of ${fmtInt(r.count)}`;
        numEl.removeAttribute('title');
      }
    }

    // The bar: filled part is what the row actually fights with, hatched part
    // is what the stack's saturation took off it. Both are stated in words too.
    if (bar) {
      const fill = bar.querySelector('i');
      const lost = bar.querySelector('u');
      if (e === null || !r.count) {
        if (fill) fill.style.width = '0%';
        if (lost) lost.style.width = '0%';
      } else {
        const share = Math.max(0, Math.min(1, e / r.count));
        if (fill) fill.style.width = (share * 100).toFixed(1) + '%';
        if (lost) lost.style.width = ((1 - share) * 100).toFixed(1) + '%';
      }
    }

    if (!note) return;
    if (e === null) {
      note.textContent = '';
      note.className = 'urow-note';
    } else if (solo !== null && e < solo - 1e-6) {
      // The row is behind others in roster order and paying for it.
      const ahead = rows
        .filter((x, j) => j !== i && rosterRank(x.unit) < rosterRank(r.unit) && x.count > 0);
      const aheadText = ahead.length <= 2
        ? ahead.map((x) => `${fmtInt(x.count)} ${(UNITS[x.unit] || {}).label || x.unit}`).join(' and ')
        : `the ${fmtInt(ahead.reduce((t, x) => t + x.count, 0))} units of ${ahead.length} other `
          + 'types above it';
      note.textContent = ahead.length
        ? `Saturated tail: ${fmtEff(solo)} on its own, ${fmtEff(e)} sitting behind `
          + `${aheadText}. That costs ${fmtEff(solo - e)} effective units, and reordering cannot `
          + 'recover it — the game sorts the stack itself.'
        : `Saturated tail: ${fmtEff(solo)} on its own, ${fmtEff(e)} inside this stack.`;
      note.className = 'urow-note is-warn';
    } else if (Math.abs(e - r.count) > 1e-6) {
      note.textContent = `The stack-size factor is biting: ${fmtInt(r.count)} units fight as `
        + `${fmtEff(e)}.`;
      note.className = 'urow-note';
    } else {
      note.textContent = 'Counts in full.';
      note.className = 'urow-note';
    }
  });

  // Stack-wide line.
  const sat = $(side + '-sat');
  if (sat) {
    sat.textContent = '';
    const n = rows.reduce((t, r) => t + (Number(r.count) || 0), 0);
    const total = eff.every((x) => x !== null)
      ? eff.reduce((t, x) => t + x, 0)
      : null;
    if (total === null) {
      sat.append(document.createTextNode('The engine returned no effective-unit counts for this stack.'));
    } else {
      const b = el('b', null, `${fmtInt(n)} units → ${fmtEff(total)} effective`);
      sat.append(b);
      const shortfall = n - total;
      if (shortfall > 1e-6) {
        sat.append(document.createTextNode(' · '));
        sat.append(el('span', 'sat-warn',
          `${fmtEff(shortfall)} lost to the stack-size factor`));
      }
      sat.append(document.createTextNode(
        rows.length > 1
          ? ' · the stack saturates as a whole, cumulatively, in the roster order shown above'
          : ' · saturation starts above 20 units and caps at 35'
      ));
    }
  }

  // Row-block note: how many types are in play, and what limits that.
  const rNote = $(side + '-rows-note');
  if (rNote) {
    const bits = [];
    if (rows.length >= MAX_ROWS) bits.push(`A stack holds at most ${MAX_ROWS} unit types.`);
    else if (!availableUnits(side, -1).length) bits.push('Every unit type is already in this stack.');
    bits.push('A type can appear only once — the game refuses a repeated type outright, so each '
      + 'select offers only what this stack does not already hold. Rows are shown in roster order, '
      + 'which is the order the game sorts them into before it computes.');
    rNote.textContent = bits.join(' ');
    rNote.className = 'field-note';
  }
}

function updateStackNotes() {
  for (const { key } of SIDES) {
    const cfg = state[key];
    updateRowNotes(key);

    // Trench note: two effects, two different schedules, both honest.
    const tNote = $(key + '-trench-note');
    if (cfg.trench === 0) {
      tNote.textContent = '';
      tNote.className = 'field-note';
    } else {
      const f = safeTrench(cfg.trench);
      if (!f) {
        tNote.textContent = '';
        tNote.className = 'field-note';
      } else {
        const bits = [];
        if (f.pool !== null && f.pool !== undefined) bits.push(`pool ×${fmtStat(f.pool, 2)}`);
        if (f.output !== null && f.output !== undefined) bits.push(`output ×${fmtStat(f.output, 2)}`);
        let text = bits.join(', ');
        if (key === 'attacker') {
          text += ' — the pool bonus applies while attacking, the output bonus does not.';
        }
        if (f.exact === false) {
          text += ' Interpolated: this level was never sampled.';
          tNote.className = 'field-note is-warn';
        } else {
          tNote.className = 'field-note';
        }
        tNote.textContent = text;
      }
    }

    // Building block note.
    const bNote = $(key + '-bldg-note');
    const hasMitigator = cfg.buildings.some((b) => (BUILDINGS[b.code] || {}).mitigates);
    if (!cfg.buildings.length) {
      bNote.textContent = 'Only a fortress changes the fighting. The other seven types were measured combat-inert.';
      bNote.className = 'field-note';
    } else if (hasMitigator && key === 'attacker') {
      bNote.textContent = 'A fortress on the attacking side was never measured.';
      bNote.className = 'field-note is-warn';
    } else {
      bNote.textContent = '';
      bNote.className = 'field-note';
    }

    // Header summary line.
    const sum = $(key + '-summary');
    const bits = [stackLabel(cfg)];
    if (cfg.rows.some((r) => r.hpPct !== 100)) bits.push('damaged');
    if (cfg.trench > 0) bits.push(`TL ${cfg.trench}`);
    if (cfg.buildings.length) bits.push(`${cfg.buildings.length} building${cfg.buildings.length === 1 ? '' : 's'}`);
    sum.textContent = bits.join(' · ');
  }

  // Air mode: only offered where both modes were actually measured — an air
  // stack striking a ground one. With mixtures that means EVERY row on each
  // side, not just the first: a stack with one land row in it is not a thing
  // anyone ever flew as a patrol.
  const modeField = $('mode-field');
  const mNote = $('mode-note');
  const aRows = rowsOf('attacker');
  const dRows = rowsOf('defender');
  const allCls = (rows, cls) => rows.length > 0
    && rows.every((r) => (UNITS[r.unit] || {}).cls === cls);
  const eligible = allCls(aRows, 'air') && allCls(dRows, 'land')
    && !aRows.some((r) => r.unit === 'bal');
  modeField.hidden = !eligible;
  if (eligible) {
    if (state.mode === 'patrol') {
      // The measured advantage is a per-pairing figure, so it is only quoted
      // for the one-versus-one case it was actually read from.
      const adv = (aRows.length === 1 && dRows.length === 1)
        ? (PATROL.observedAdvantage[aRows[0].unit] || {})[dRows[0].unit]
        : null;
      mNote.textContent = adv
        ? `Measured at ×${adv.toFixed(3)} of a direct strike against this target. `
          + 'The attrition band makes it an estimate.'
        : 'Patrol charges less of the attacker\'s own losses against its output. '
          + 'The coefficient is a band, so this is an estimate.';
      mNote.className = 'field-note is-warn';
    } else {
      mNote.textContent = 'A direct strike ignores Rounds entirely — measured, '
        + 'byte-identical at 0.25/0.5/0.75/1.';
      mNote.className = 'field-note';
    }
  }

  // Rounds note.
  const rNote = $('rounds-note');
  if (eligible && state.mode === 'patrol') {
    rNote.textContent = 'Patrol damage is proportional to Rounds — measured, on a '
      + '0.25/0.5/0.75/1 ladder. Fractions are meaningful here.';
    rNote.className = 'field-note';
  } else if (eligible) {
    rNote.textContent = 'Ignored for a direct strike: the same ladder returned identical '
      + 'damage at every setting.';
    rNote.className = 'field-note';
  } else if (Number(state.rounds) === 1) {
    rNote.textContent = 'Every measurement behind this model used exactly one round.';
    rNote.className = 'field-note';
  } else {
    rNote.textContent = 'Multi-round behaviour was never measured. This is extrapolation.';
    rNote.className = 'field-note is-warn';
  }
}

/* --------------------------------------------------------------------------
   9. Roster reference
   -------------------------------------------------------------------------- */

const PROV = (DATA && DATA.PROVENANCE && typeof DATA.PROVENANCE === 'object') ? DATA.PROVENANCE : {};

/**
 * A unit's provenance holds references INTO the PROVENANCE ledger
 * (e.g. { maxHP: 'UNITS.maxHP' }), so a value may be a key, an inline note,
 * or an object. Resolve one step, then report the confidence it carries.
 */
function confidenceOfRef(ref) {
  if (typeof ref === 'string' && PROV[ref] && PROV[ref].confidence) return String(PROV[ref].confidence);
  if (ref && typeof ref === 'object' && ref.confidence) return String(ref.confidence);
  return null;
}

/** "max HP derived · attack, defence measured" */
function provSummary(provenance) {
  if (!provenance || typeof provenance !== 'object') return null;
  const FIELD_LABEL = { maxHP: 'max HP', atk: 'attack', def: 'defence' };
  const byConfidence = new Map();
  for (const [field, ref] of Object.entries(provenance)) {
    const conf = confidenceOfRef(ref);
    if (!conf) continue;
    const label = FIELD_LABEL[field] || field;
    if (!byConfidence.has(conf)) byConfidence.set(conf, []);
    byConfidence.get(conf).push(label);
  }
  if (!byConfidence.size) return null;
  return [...byConfidence.entries()]
    .map(([conf, fields]) => `${fields.join(', ')} ${conf}`)
    .join(' · ');
}

/* THE STANDING LIMITS, rendered from data.js rather than written in the HTML.

   The list in index.html used to be prose, and prose does not get re-derived
   when a measurement overturns something. It ended up asserting roster-order
   saturation and attack-x-count allocation -- two laws that were measured,
   found wrong, and replaced in the engine directly above it -- and telling the
   reader that multi-round battles and range had never been exercised, long
   after both were measured and modelled.

   NOT_MEASURED is the one list. Each entry carries what is missing, why it is
   missing, and what would close it, so all three go on the page: "closedBy" is
   the part that makes a gap a piece of work rather than a shrug. */
/** Finish a sentence without doubling a full stop it already has. */
function endStop(text) {
  const t = String(text).trim();
  return /[.!?]$/.test(t) ? t : `${t}.`;
}

function buildLimits() {
  const ul = $('limits-list');
  if (!ul) return;
  ul.textContent = '';
  const gaps = (DATA && Array.isArray(DATA.NOT_MEASURED)) ? DATA.NOT_MEASURED : [];
  if (!gaps.length) {
    // Not a celebration. An empty list here almost certainly means the import
    // failed, and "this model knows everything" is the single worst thing this
    // page could claim.
    const li = el('li', 'tag-none');
    li.textContent = 'The gap list could not be read from data.js. That is a '
      + 'fault in this page, not an absence of gaps — treat every figure above '
      + 'as unverified.';
    ul.appendChild(li);
    return;
  }
  for (const g of gaps) {
    const li = el('li');
    li.appendChild(el('strong', null, String(g.what || g.key || 'unnamed gap')));
    li.appendChild(document.createTextNode(' '));
    li.appendChild(document.createTextNode(String(g.why || '')));
    if (g.closedBy) {
      const span = el('span', 'limits-closedby');
      // These strings are written as prose in data.js and some already end in a
      // full stop. Appending one unconditionally printed "at 10 km.." on the
      // page for as long as that entry has existed.
      span.textContent = ` What would close it: ${endStop(g.closedBy)}`;
      li.appendChild(span);
    }
    ul.appendChild(li);
  }
}

/* SCOPE_LIMITS -- measured, and still not computed here.

   Deliberately a separate renderer from buildLimits() rather than a flag on
   the same list. The two say opposite things about whose problem the gap is:
   an unmeasured law is nobody's answer yet, and an unmodelled one is an answer
   the reader now has to apply by hand. That is why every entry ends with
   whatToDoInstead, and why an entry missing it is rendered as a fault rather
   than skipped -- a scope limit with no advice attached is just an excuse. */
function buildScopeLimits() {
  const ul = $('scope-list');
  if (!ul) return;
  ul.textContent = '';
  const limits = (DATA && Array.isArray(DATA.SCOPE_LIMITS)) ? DATA.SCOPE_LIMITS : [];
  if (!limits.length) {
    const li = el('li', 'tag-none');
    li.textContent = 'The scope list could not be read from data.js. That is a '
      + 'fault in this page: this model does not compute multi-stack battles, '
      + 'and if that sentence is the only place it says so, say it louder.';
    ul.appendChild(li);
    return;
  }
  for (const s of limits) {
    const li = el('li');
    li.appendChild(el('strong', null, String(s.what || s.key || 'unnamed limit')));
    li.appendChild(document.createTextNode(' '));
    li.appendChild(document.createTextNode(String(s.why || '')));
    const span = el('span', 'limits-closedby');
    span.textContent = s.whatToDoInstead
      ? ` What to do instead: ${endStop(s.whatToDoInstead)}`
      : ' No advice is recorded for working around this, which is a gap in this'
        + ' page rather than in the measurements.';
    li.appendChild(span);
    ul.appendChild(li);
  }
}

function buildRoster() {
  const body = $('roster-body');
  body.textContent = '';

  for (const code of UNIT_CODES) {
    const u = UNITS[code];
    const tr = document.createElement('tr');
    tr.appendChild(el('td', null, u.label || code));
    tr.appendChild(el('td', null, CLASS_LABEL[u.cls] || u.cls || EM_DASH));

    const cell = (v, dp) => {
      const td = el('td', 'c-val');
      const t = dp === null ? fmtLoose(v) : fmtStat(v);
      if (t === null) {
        td.textContent = 'not measured';
        td.className = 'c-val tag-none';
      } else {
        td.textContent = t;
      }
      return td;
    };
    tr.appendChild(cell(u.maxHP, null));
    tr.appendChild(cell(u.atk));
    tr.appendChild(cell(u.def));

    const summary = provSummary(u.provenance) || provText(u.provenance);
    const pt = el('td', null, summary || 'no provenance recorded');
    if (!summary) pt.className = 'tag-none';
    tr.appendChild(pt);

    body.appendChild(tr);
  }

  buildLedger();
  buildScopeLimits();
  buildLimits();
}

/** The provenance ledger: one entry per constant, with its confidence. */
function buildLedger() {
  const dl = $('ledger');
  if (!dl) return;
  dl.textContent = '';

  const entries = Object.entries(PROV);
  if (!entries.length) {
    dl.appendChild(el('dd', 'tag-none', 'data.js published no provenance notes.'));
    return;
  }

  for (const [key, entry] of entries) {
    const dt = el('dt');
    dt.appendChild(el('code', null, key));

    const conf = (entry && typeof entry === 'object' && entry.confidence)
      ? String(entry.confidence) : null;
    if (conf) {
      // Anything that is not plainly "measured" reads as a qualification.
      const tone = /^measured$/i.test(conf) ? 'measured'
                 : /unmeasured|unknown/i.test(conf) ? 'unknown'
                 : 'estimated';
      dt.appendChild(el('span', 'ledger-conf conf-' + tone, conf));
    }
    dl.appendChild(dt);

    const dd = el('dd');
    if (entry && typeof entry === 'object') {
      const { confidence, ...rest } = entry;
      void confidence;
      for (const [k, v] of Object.entries(rest)) {
        const line = el('p', 'ledger-line');
        line.appendChild(el('span', 'ledger-key', k));
        line.appendChild(document.createTextNode(' ' + provText(v)));
        dd.appendChild(line);
      }
    } else {
      dd.textContent = provText(entry);
    }
    dl.appendChild(dd);
  }
}

/* --------------------------------------------------------------------------
   10. Shareable state in the URL
   -------------------------------------------------------------------------- */

/**
 * A side is `rows ~ trench ~ buildings`:
 *
 *     a=inf.30.100,art.10.100~5~fortress.3.100
 *
 * with rows and buildings each comma-separated. The two `~` are what tells the
 * decoder this is the composite format; links minted by the single-unit version
 * of this app have the form `inf.30.100.0~fortress.3.100` and are still read,
 * because a link somebody saved should not stop working when the model behind
 * it learns that a stack is a mixture.
 */
// A SHARE LINK HAS TO CARRY THE WHOLE BATTLE. This one carried the two stacks,
// the trenches, the buildings and the rounds, and dropped terrain, distance and
// the hero on the floor -- so "Copy link" handed someone a link that computes a
// DIFFERENT battle from the one on screen, silently. That was survivable while
// terrain and distance were unmodelled and heroes were half-modelled. It is not
// now: terrain is per side and picks the coefficient column, distance gates
// whole rows out and switches off return fire, and a hero carries a level and
// an HP percentage that both change its contribution.
//
// Fields are appended, never reordered, and every one is optional on the way
// back in, so links written before this still decode.
function encodeState(cfg) {
  const side = (s) => [
    (s.rows || []).map((r) => [r.unit, r.count, fmtHpPct(r.hpPct)].join('.')).join(','),
    String(s.trench),
    (s.buildings || []).map((b) => [b.code, b.level, b.hpPct].join('.')).join(','),
    s.hero ? [s.hero.code, s.hero.level,
      s.hero.hpPct === undefined ? 100 : s.hero.hpPct].join('.') : '',
  ].join('~');
  return `a=${side(cfg.attacker)}&d=${side(cfg.defender)}&r=${cfg.rounds}`
    + (cfg.mode === 'patrol' ? '&m=patrol' : '')
    + (cfg.terrain && cfg.terrain !== 'land' ? `&t=${cfg.terrain}` : '')
    + (cfg.defenderTerrain ? `&dt=${cfg.defenderTerrain}` : '')
    + (cfg.distance ? `&km=${cfg.distance}` : '')
    + (cfg.mutual ? '&mu=1' : '')
    + (state.fightToEnd ? '&fo=1' : '');
}

function decodeBuildings(str) {
  return String(str || '').split(',').map((c) => {
    if (!c) return null;
    // '.' separates the fields AND appears inside a decimal HP, so the tail
    // is rejoined rather than taken as one part. Old links still decode.
    const [code, level, ...hpRest] = c.split('.');
    const hpPct = hpRest.join('.');
    if (!BUILDINGS[code]) return null;
    return {
      code,
      level: Math.min(maxLevelOf(code), Math.max(1, Number(level) || 1)),
      hpPct: Math.min(100, Math.max(1, Number(hpPct) || 100)),
    };
  }).filter(Boolean);
}

function decodeState(hash) {
  const raw = String(hash || '').replace(/^#/, '');
  if (!raw) return null;
  try {
    const parts = Object.fromEntries(
      raw.split('&').map((kv) => {
        const i = kv.indexOf('=');
        return [kv.slice(0, i), kv.slice(i + 1)];
      })
    );

    const side = (str) => {
      const chunks = String(str || '').split('~');

      // Legacy single-unit link: unit.count.hp.trench ~ building ~ building
      if (chunks.length < 3) {
        // HP can carry a decimal now, and '.' is also the separator, so the
        // fields are taken from the ends and the middle is rejoined.
        const legacy = chunks[0].split('.');
        const unit = legacy[0];
        const count = legacy[1];
        const trench = legacy.length > 3 ? legacy[legacy.length - 1] : undefined;
        const hp = legacy.slice(2, legacy.length > 3 ? -1 : undefined).join('.');
        if (!UNITS[unit]) return null;
        return {
          rows: [{ unit, count: clampCount(count), hpPct: clampHp(hp) }],
          trench: Math.min(20, Math.max(0, Number(trench) || 0)),
          buildings: chunks.slice(1).map((c) => decodeBuildings(c)).flat(),
        };
      }

      // Composite link. Duplicate types are dropped rather than merged: the
      // server refuses a repeated type outright, so a link carrying one does
      // not describe a stack that can be fielded, and silently adding the
      // counts together would compute a different battle from the one asked for.
      const seen = new Set();
      const rows = [];
      for (const chunk of chunks[0].split(',')) {
        if (!chunk) continue;
        const [unit, count, ...hpRest] = chunk.split('.');
        const hp = hpRest.join('.');
        if (!UNITS[unit] || seen.has(unit)) continue;
        seen.add(unit);
        rows.push({ unit, count: clampCount(count), hpPct: clampHp(hp) });
        if (rows.length >= MAX_ROWS) break;
      }
      if (!rows.length) return null;
      rows.sort((x, y) => rosterRank(x.unit) - rosterRank(y.unit));
      // chunks[3] is absent in every link written before heroes were carried.
      let hero = null;
      if (chunks[3]) {
        const [code, level, ...hpRest2] = chunks[3].split('.');
        const hpPct = hpRest2.join('.');
        const hdef = HEROES[code] || HEROES_REFUSED[code];
        if (hdef) {
          hero = {
            code,
            level: Math.min(hdef.maxLevel || 20, Math.max(1, Number(level) || 1)),
            hpPct: clampHp(hpPct),
          };
        }
      }
      return {
        rows,
        trench: Math.min(20, Math.max(0, Number(chunks[1]) || 0)),
        buildings: decodeBuildings(chunks[2]),
        hero,
      };
    };

    const a = side(parts.a);
    const d = side(parts.d);
    if (!a || !d) return null;
    const r = Number(parts.r);
    const km = Number(parts.km);
    return {
      attacker: a, defender: d,
      rounds: Number.isFinite(r) && r > 0 ? r : 1,
      mode: parts.m === 'patrol' ? 'patrol' : 'strike',
      terrain: ['land', 'sea', 'debark'].includes(parts.t) ? parts.t : 'land',
      defenderTerrain: ['land', 'sea', 'air', 'debark'].includes(parts.dt)
        ? parts.dt : '',
      distance: Number.isFinite(km) && km > 0 ? Math.round(km) : 0,
      mutual: parts.mu === '1',
      fightToEnd: parts.fo === '1',
    };
  } catch {
    return null;
  }
}

function syncHash(cfg) {
  const next = '#' + encodeState(cfg);
  if (location.hash !== next) {
    history.replaceState(null, '', next);
  }
}

function copyLink() {
  const url = location.href;
  const btn = $('share');
  const done = () => {
    const old = btn.textContent;
    btn.textContent = 'Link copied';
    btn.classList.add('is-done');
    // The label change is silent to a screen reader; say it in the live region.
    announce('Link copied to the clipboard.');
    setTimeout(() => { btn.textContent = old; btn.classList.remove('is-done'); }, 1600);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(done, () => { window.prompt('Copy this link:', url); });
  } else {
    window.prompt('Copy this link:', url);
  }
}

/* --------------------------------------------------------------------------
   11. Start. Last statement in the file, so every const above is initialised.
   -------------------------------------------------------------------------- */

if (DATA && ENGINE) {
  try {
    boot();
  } catch (err) {
    showFatal(err, 'boot');
  }
}
