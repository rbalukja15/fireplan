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

const UNIT_CODES = Object.keys(UNITS);
const BUILDING_CODES = Object.keys(BUILDINGS);

/** A unit whose own stats were never measured cannot be modelled honestly. */
function isUnmeasuredUnit(u) {
  return !u || u.maxHP === null || u.maxHP === undefined ||
         u.atk === null || u.atk === undefined ||
         u.def === null || u.def === undefined;
}

function defaultUnit() {
  if (UNITS.inf) return 'inf';
  const firstMeasured = UNIT_CODES.find((c) => !isUnmeasuredUnit(UNITS[c]));
  return firstMeasured || UNIT_CODES[0] || '';
}

const DEFAULT_STATE = () => ({
  attacker: { unit: defaultUnit(), count: 30, hpPct: 100, trench: 0, buildings: [] },
  defender: { unit: defaultUnit(), count: 30, hpPct: 100, trench: 0, buildings: [] },
  rounds: 1,
  mode: 'strike',
});

let state = DEFAULT_STATE();

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
  $('builders').addEventListener('change', onInput);
  $('rounds').addEventListener('input', onInput);
  $('rounds').addEventListener('change', onInput);
  $('mode').addEventListener('change', onInput);

  $('builders').addEventListener('click', (ev) => {
    const add = ev.target.closest('[data-add-bldg]');
    if (add) { addBuilding(add.dataset.addBldg); return; }
    const rm = ev.target.closest('[data-remove-bldg]');
    if (rm) { removeBuilding(rm.dataset.side, Number(rm.dataset.index)); }
  });

  $('swap').addEventListener('click', swapSides);
  $('reset').addEventListener('click', () => {
    state = DEFAULT_STATE();
    renderBuildings('attacker');
    renderBuildings('defender');
    writeStateToDom();
    recompute();
  });
  $('share').addEventListener('click', copyLink);

  window.addEventListener('hashchange', () => {
    const s = decodeState(location.hash);
    if (!s) return;
    state = s;
    renderBuildings('attacker');
    renderBuildings('defender');
    writeStateToDom();
    recompute();
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

  $('stickybar').hidden = false;
  document.body.classList.add('has-sticky');
  $('app').hidden = false;

  recompute();
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

  fillUnitSelect($(side + '-unit'));
  fillTrenchSelect($(side + '-trench'));

  // Keep the HP number box and its slider in step, both ways.
  const numBox = $(side + '-hp');
  const slider = $(side + '-hp-range');
  numBox.addEventListener('input', () => { slider.value = clampHp(numBox.value); });
  slider.addEventListener('input', () => { numBox.value = slider.value; });
}

function clampHp(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return 100;
  return Math.min(100, Math.max(1, Math.round(n)));
}

function fillUnitSelect(select) {
  const byClass = new Map();
  for (const code of UNIT_CODES) {
    const u = UNITS[code];
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
    hp.min = '1'; hp.max = '100'; hp.step = '1';
    hp.value = String(b.hpPct);
    hp.id = uid + '-hp';
    hp.setAttribute('aria-label', `Building ${i + 1} HP percent`);
    hp.addEventListener('input', () => {
      const n = Number(hp.value);
      b.hpPct = Number.isFinite(n) ? Math.min(100, Math.max(1, n)) : 100;
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
    const s = state[key];
    const unitSel = $(key + '-unit');
    if (UNITS[s.unit]) unitSel.value = s.unit; else s.unit = unitSel.value;
    $(key + '-count').value = String(s.count);
    $(key + '-hp').value = String(s.hpPct);
    $(key + '-hp-range').value = String(s.hpPct);
    $(key + '-trench').value = String(s.trench);
  }
  $('rounds').value = String(state.rounds);
  $('mode').value = state.mode === 'patrol' ? 'patrol' : 'strike';
  renderBuildings('attacker');
  renderBuildings('defender');
}

function readDomToState() {
  for (const { key } of SIDES) {
    const s = state[key];
    s.unit = $(key + '-unit').value;
    const c = Number($(key + '-count').value);
    s.count = Number.isFinite(c) ? Math.min(500, Math.max(1, Math.round(c))) : 1;
    s.hpPct = clampHp($(key + '-hp').value);
    const t = Number($(key + '-trench').value);
    s.trench = Number.isFinite(t) ? Math.min(20, Math.max(0, Math.round(t))) : 0;
  }
  const r = Number($('rounds').value);
  state.rounds = Number.isFinite(r) && r > 0 ? r : 1;
  state.mode = $('mode').value === 'patrol' ? 'patrol' : 'strike';
}

function onInput() {
  readDomToState();
  recompute();
}

function swapSides() {
  readDomToState();
  const a = state.attacker;
  state.attacker = state.defender;
  state.defender = a;
  writeStateToDom();
  recompute();
}

/* --------------------------------------------------------------------------
   7. Compute + render
   -------------------------------------------------------------------------- */

function recompute() {
  const config = {
    attacker: cloneSide(state.attacker),
    defender: cloneSide(state.defender),
    rounds: state.rounds,
    mode: state.mode,
  };

  updateStackNotes();
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
  renderSanity(result, config);
  renderDerivation(result.derivation);
  renderSticky(result);
}

function cloneSide(s) {
  return {
    unit: s.unit,
    count: s.count,
    hpPct: s.hpPct,
    trench: s.trench,
    buildings: s.buildings.map((b) => ({ code: b.code, level: b.level, hpPct: b.hpPct })),
  };
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
  $('verdict').textContent = 'No result.';
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

  const chip = $('result-chip');
  chip.textContent = level;
  chip.className = 'conf-chip conf-' + level;
  $('result').dataset.level = level;

  const stConf = $('st-conf');
  stConf.textContent = level;
  stConf.className = 'sb-conf conf-' + level;
}

/* --- 7b. Scoreboard ------------------------------------------------------ */

function renderScoreboard(result, config) {
  renderSide('a', result.attacker, config.attacker);
  renderSide('d', result.defender, config.defender);
}

function renderSide(prefix, side, cfg) {
  const unit = UNITS[cfg.unit] || {};
  $(`sb-${prefix}-name`).textContent =
    `${fmtInt(cfg.count)} × ${unit.label || cfg.unit}` +
    (cfg.hpPct !== 100 ? ` at ${cfg.hpPct}% HP` : '') +
    (cfg.trench > 0 ? `, TL ${cfg.trench}` : '');

  const s = side || {};
  setFig($(`sb-${prefix}-hplost`), fmt(s.hpLost));
  setFig($(`sb-${prefix}-deaths`), fmtInt(s.deaths));
  setFig($(`sb-${prefix}-dealt`), fmt(s.damageDealt));
  setFig($(`sb-${prefix}-pool`), fmt(s.pool));

  const left = fmtInt(s.unitsLeft);
  const leftEl = $(`sb-${prefix}-left`);
  if (left === null) {
    setFig(leftEl, null);
  } else {
    setFig(leftEl, `${fmtInt(cfg.count)} → ${left}`);
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

function renderVerdict(result, config) {
  const a = result.attacker || {};
  const d = result.defender || {};
  const aUnit = UNITS[config.attacker.unit] || {};
  const dUnit = UNITS[config.defender.unit] || {};

  // With no measurement behind the pairing there is no outcome to narrate.
  // The figures stay on screen, flagged; the sentence that would turn them
  // into a prediction does not get written.
  if (displayedLevel === 'unknown') {
    const blind = [config.attacker.unit, config.defender.unit]
      .filter((c) => isUnmeasuredUnit(UNITS[c]))
      .map((c) => (UNITS[c] || {}).label || c);
    const v0 = $('verdict');
    v0.textContent = 'No outcome can be stated for this matchup.';
    const s0 = el('span', 'vsub');
    s0.textContent = blind.length
      ? `${blind.join(' and ')} ${blind.length > 1 ? 'have' : 'has'} no measured statistics at all — not HP, not attack, not defence. The figures below are what the model emits when asked a question it has no data for. They are not a prediction.`
      : 'This pairing was never submitted to the calculator even once. The figures below are what the model emits when asked a question it has no data for. They are not a prediction.';
    v0.appendChild(s0);
    return;
  }

  let headline;
  const aDead = isDestroyed(a), dDead = isDestroyed(d);
  if (aDead && dDead) {
    headline = 'Both stacks are destroyed.';
  } else if (dDead) {
    headline = `The defending ${dUnit.label || ''} stack is destroyed.`.replace(/\s+/g, ' ');
  } else if (aDead) {
    headline = `The attacking ${aUnit.label || ''} stack is destroyed. The attack fails.`.replace(/\s+/g, ' ');
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
  const r = Number(config.rounds);
  parts.push(r === 1 ? 'One round.' : `${fmtLoose(r)} rounds — extrapolated.`);
  sub.textContent = parts.join(' ');

  const v = $('verdict');
  v.textContent = headline;
  v.appendChild(sub);
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
    const deaths = numOrNull(side.deaths);
    const left = numOrNull(side.unitsLeft);
    const lost = numOrNull(side.hpLost);
    const pool = numOrNull(side.pool);
    if (deaths !== null && deaths > cfg.count) {
      problems.push(`${label}: ${deaths} units killed out of ${cfg.count} in the stack.`);
    }
    if (left !== null && (left < 0 || left > cfg.count)) {
      problems.push(`${label}: ${left} units left out of ${cfg.count}.`);
    }
    if (deaths !== null && left !== null && deaths + left !== cfg.count) {
      problems.push(`${label}: ${deaths} killed plus ${left} surviving does not make ${cfg.count}.`);
    }
    if (lost !== null && pool !== null && lost > pool + 1e-6) {
      problems.push(`${label}: lost ${fmt(lost)} HP from a pool of ${fmt(pool)}.`);
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

function updateStackNotes() {
  for (const { key } of SIDES) {
    const cfg = state[key];
    const u = UNITS[cfg.unit] || {};

    // Unit note: the stats the model will actually use, with their limits.
    const note = $(key + '-unit-note');
    if (isUnmeasuredUnit(u)) {
      note.textContent = 'Nothing about this unit was ever measured — no HP, no attack, no defence.';
      note.className = 'field-note is-danger';
    } else {
      note.textContent =
        `Max HP ${fmtLoose(u.maxHP)} · same-class attack ${fmtStat(u.atk)} · same-class defence ${fmtStat(u.def)}`;
      note.className = 'field-note';
    }

    // Count note: the stack-size factor is where large stacks stop paying.
    const cNote = $(key + '-count-note');
    let eff = null;
    if (ENGINE && typeof ENGINE.effectiveUnits === 'function') {
      try { eff = ENGINE.effectiveUnits(cfg.count); } catch { eff = null; }
    }
    if (eff === null || eff === undefined) {
      cNote.textContent = '';
    } else if (Math.abs(eff - cfg.count) < 1e-9) {
      cNote.textContent = `Counts in full: ${fmtLoose(eff)} effective.`;
    } else {
      cNote.textContent = `Only ${fmtLoose(eff)} effective — the stack-size factor is biting.`;
    }
    cNote.className = 'field-note';

    // HP note: the 0.05 floor is the part people get wrong.
    const hNote = $(key + '-hp-note');
    let m = null;
    if (ENGINE && typeof ENGINE.hpMultiplier === 'function') {
      try { m = ENGINE.hpMultiplier(cfg.hpPct / 100); } catch { m = null; }
    }
    hNote.textContent = (m === null || m === undefined)
      ? ''
      : `Pool ×${(cfg.hpPct / 100).toFixed(2)}, output ×${fmtStat(m, 2)}.`;
    hNote.className = 'field-note';

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
    const bits = [`${cfg.count} × ${u.label || cfg.unit}`];
    if (cfg.hpPct !== 100) bits.push(`${cfg.hpPct}% HP`);
    if (cfg.trench > 0) bits.push(`TL ${cfg.trench}`);
    if (cfg.buildings.length) bits.push(`${cfg.buildings.length} building${cfg.buildings.length === 1 ? '' : 's'}`);
    sum.textContent = bits.join(' · ');
  }

  // Air mode: only offered where both modes were actually measured.
  const modeField = $('mode-field');
  const mNote = $('mode-note');
  const av = UNITS[state.attacker.unit];
  const dv = UNITS[state.defender.unit];
  const eligible = !!(av && dv && av.cls === 'air' && dv.cls === 'land'
                      && state.attacker.unit !== 'bal');
  modeField.hidden = !eligible;
  if (eligible) {
    if (state.mode === 'patrol') {
      const adv = (PATROL.observedAdvantage[state.attacker.unit] || {})[state.defender.unit];
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

function encodeState(cfg) {
  const side = (s) => {
    let out = [s.unit, s.count, s.hpPct, s.trench].join('.');
    for (const b of s.buildings) out += '~' + [b.code, b.level, b.hpPct].join('.');
    return out;
  };
  return `a=${side(cfg.attacker)}&d=${side(cfg.defender)}&r=${cfg.rounds}`
    + (cfg.mode === 'patrol' ? '&m=patrol' : '');
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
      const [unit, count, hp, trench] = chunks[0].split('.');
      if (!UNITS[unit]) return null;
      return {
        unit,
        count: Math.min(500, Math.max(1, Number(count) || 1)),
        hpPct: clampHp(hp),
        trench: Math.min(20, Math.max(0, Number(trench) || 0)),
        buildings: chunks.slice(1).map((c) => {
          const [code, level, hpPct] = c.split('.');
          if (!BUILDINGS[code]) return null;
          return {
            code,
            level: Math.min(maxLevelOf(code), Math.max(1, Number(level) || 1)),
            hpPct: Math.min(100, Math.max(1, Number(hpPct) || 100)),
          };
        }).filter(Boolean),
      };
    };
    const a = side(parts.a);
    const d = side(parts.d);
    if (!a || !d) return null;
    const r = Number(parts.r);
    return {
      attacker: a, defender: d,
      rounds: Number.isFinite(r) && r > 0 ? r : 1,
      mode: parts.m === 'patrol' ? 'patrol' : 'strike',
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
