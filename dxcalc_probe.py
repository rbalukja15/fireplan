#!/usr/bin/env python3
"""
dxcalc_probe.py — black-box probe for dxter's Supremacy 1914 battle calculator
https://dxcalc.com/s1914

WHY THIS EXISTS
---------------
The page ships no client-side combat math. Everything is computed server-side
from a plain form POST, so the only way to recover coefficients is to submit
controlled inputs and read the surviving-HP values back out.

Stdlib only. No pip install. Python 3.9+.

    python3 dxcalc_probe.py --dump-fields          # discover the form schema first
    python3 dxcalc_probe.py --sanity               # verify the POST round-trips
    python3 dxcalc_probe.py --run trenches
    python3 dxcalc_probe.py --run all --delay 2.0

dxcalc.com is blocked by default in Anthropic-hosted cloud environments. The
session must be STARTED in an environment whose allowed-domains list contains
the apex dxcalc.com; network policy is fixed at provisioning. Allowing only
www.dxcalc.com does not work — it 301-redirects to the apex.

Results stream to results.jsonl as they arrive, so a crash mid-sweep loses
nothing.

CONFIRMED SO FAR (clean single-variable sweeps, deterministic engine)
--------------------------------------------------------------------
Stack size factor, effective units from a stack of n:
    E(n) = n                                    for n <= 20
    E(n) = 20 + k*(60-k)/60, k = min(n,50)-20   for n > 20
    -> saturates at 35 effective units; stacking past 50 does nothing.

HP scaling multiplier, from a unit at hp fraction f in [0,1]:
    m(f) = 0.05 + 0.95*f          (fits exactly, not approximately)

RESULT SPAN SEMANTICS — SETTLED
    span.hpLeft holds HP *LOST*, despite the class name. The rendered text is
    "Lost 50.0 HP (16.7%) 2 died". Confirmed by --semantics: hold one side's
    count fixed and grow the other, and a side's reading tracks only the
    OPPONENT's count, never its own.

    The percentage is that loss as a fraction of the stack's full pool, so
    every reading yields the pool for free:  pool = lost / pct.  Divide by the
    unit count and you have that unit type's max HP from the same request that
    measured damage. parse_reading() returns lost / pct / died / pool.

ATTACK vs DEFENCE ARE DIFFERENT COEFFICIENTS
    10 inf attacking 10 inf, one round:  attacker lost 50.0, defender lost 40.0.
        infantry deal 4.0 per unit attacking
        infantry deal 5.0 per unit defending      (ratio 1.25)
    Every damage figure must therefore be labelled with the side it came from.
    Any experiment that pools attacker-loss with defender-loss readings is
    fitting two coefficients as though they were one.

Infantry max HP = 20.0, derived independently from both stacks of the same
round (299.4/15 and 200.0/10). Deaths are floor(HP_lost / 20).

UNIT TABLE — measured by --run unit_stats, one U-vs-U request each, and
reproduced identically on two separate runs (the engine is deterministic).

    unit    class   maxHP   atk   def    def/atk
    inf     land       20   4.0   5.0      1.25
    cav     land       25  15.0   7.5      0.50
    ac      land       60   6.0  12.0      2.00
    lart    land       10   5.0   1.0      0.20
    art     land       20   8.0   2.7      0.34
    rrg     land       60  20.0   6.7      0.34
    lt      land      175  30.0  30.0      1.00
    ht      land      260  45.0  45.0      1.00
    convoy  land       20   1.0   1.0      1.00
    st      land       40  25.0   6.3      0.25
    bal     air         —     —     —         —   (guarded: crashes in air)
    int     air        60  20.0  20.0      1.00
    tac     air        80   3.0   3.0      1.00
    zep     air       140   5.0   5.0      1.00
    sub     sea       100  40.0  40.0      1.00
    cl      sea        50  10.0  10.0      1.00
    bb      sea       200  40.0  40.0      1.00

    ATTACK AND DEFENCE ARE INDEPENDENT STATS, not one number plus a global
    bonus. Seven units differ between the two and nine are symmetric, so the
    1.25 seen for infantry is specific to infantry, not a defender bonus.
    Offensive land units defend far worse than they attack (artillery 0.34,
    stormtroopers 0.25, light artillery 0.20) while armoured cars invert it
    (2.00). Every air and naval unit measured so far is symmetric.

    maxHP is derived from the loss percentage, whose displayed precision caps
    the result — raw output shows 60.06, 175.44, 260.12 for what are plainly
    60, 175, 260. Confirmed against the stock form, which ships lt at 525/3 =
    175.0 and ht at 260/1 = 260.0 per unit.

FORTRESS — measured, and it works
    A fortress on the DEFENDER scales incoming damage by
        m(L) = 0.85 - 0.15 * L        for L = 1..5
    i.e. 0.70 0.55 0.40 0.25 0.10. All five points fit exactly. Note the
    discontinuity: no fortress at all is 1.00, so merely having one costs the
    attacker 15% before levels are counted, as though it acted at level L+1.

    The control also re-confirms the core model independently: 30 inf vs
    30 inf gives E(30) = 28.3333, and 28.3333 * 4.0 = 113.3 (defender's loss)
    and 28.3333 * 5.0 = 141.7 (attacker's loss), both matching to display
    precision.

FORTRESS HP AND DAMAGE TO BUILDINGS — solved, and it was a parser bug
    The attacker reading -8.5 under every fortress was never the attacker. The
    raw span said

        "-8.5 HP (17%) →"      not      "Lost 141.7 HP (23.6%) 7 died"

    That is the FORTRESS's own result row. Its id is B.1.bldg.1, which the old
    SLOT_RE did not match, so the row inherited the last unit slot seen —
    A.1.1 — and overwrote the attacker's real reading. RESULT_SLOT_RE matches
    building ids now, so the two no longer collide.

    Decoding it gives two new constants. The percentage is the damage over the
    building's own pool, and the pool scales exactly with level:

        L1 17%    L2 8.5%    L3 5.67%    L4 4.25%    L5 3.4%
        8.5 / pct  ->  50, 100, 150, 200, 250

        FORTRESS HP = 50 per level.

    The 8.5 is constant at every level, and 8.5 / E(30) = 8.5 / 28.3333 = 0.3:

        infantry deal 0.3 per effective unit to BUILDINGS, against 4.0 to units.

    The minus sign is delta notation and the arrow points at the resulting
    value; DELTA_RE parses that shape. Buildings are reported per row, so this
    also means the other seven building types can be measured the same way.

    The span also nests <span style=font-size:large> around its arrow, and the
    scraper used to stop capturing at that inner </span>, truncating the row
    before its most useful half. Counting span depth recovered the rest:

        "-8.5 HP (3.4%) → LVL:5 41.5 HP; DR: 90% → 87.5%"

    DR is Damage Reduction, named by the page itself, and it confirms the
    fitted law exactly: DR 90% at level 5 is m(5) = 0.10. The pair is DR before
    and after this round's damage, and the drop pins the formula:

        DR = 0.15 * (fortressHP / 50 + 1)

        full L5:  250.0 HP -> 0.15 * 6.00  = 90.00%
        damaged:  241.5 HP -> 0.15 * 5.83  = 87.45%   (page: 87.5%)

    So the "+1" discontinuity is built into the game's own formula, mitigation
    decays continuously as the fortress is worn down, and BLDG_TAIL_RE now
    reads level, remaining HP and current DR straight off the page — no
    curve-fitting needed for the remaining seven building types.

FORTRESSES DO NOT REDUCE THE DEFENDER'S OUTPUT
    Recovering A.1.1 showed the attacker losing 141.7 at fortress level 5 —
    identical to the no-fortress control. The fortress mitigates incoming
    damage only; the defenders still hit for full. That reading was invisible
    while the building row was overwriting it.

THE PER-STACK SUMMARY TABLE — free precision nobody had read
    Every stack's result block is followed by <table class=resultTable>, and it
    is not a restatement of the span:

        | HP lost | % lost | food | ... | cash | hours
        |  141.67 |   23.6 |    0 | ... |   $0 |    23

    The span rounds HP to one decimal (141.7) and the table does not (141.67);
    the span carries three significant figures of percentage (1.89%) where the
    table prints one decimal (1.9). The two are complementary, so the best pool
    available from one request is the TABLE's HP over the SPAN's percentage.
    On the captured fortress response that moves the defender's pool from 597.9
    to 599.5 against a known 600 — a four-fold cut in the error that caps max
    HP, which is why that column read 60.06 / 175.44 / 260.12 for 60 / 175 /
    260. refine_details() does the substitution, but only after checking that
    the stack's spans sum to the table it claims to summarise: a table attached
    to the wrong stack would look every bit as plausible as the building row
    that clobbered the attacker's slot for a whole phase of this project.

    The table counts UNIT rows only — B.1 lost 11.3 HP of infantry and 8.5 of
    fortress, and its table says 11.33. The resource columns and 'hours' are
    unexplained and simply recorded.

TRENCHES — UNVERIFIED, DO NOT CITE
    The old note said trenches add to the defender's HP pool rather than
    reducing incoming damage, and that levels 1-3 conferred no measurable
    benefit. That predates the HP-lost discovery and all three parser bugs, and
    "no measurable benefit" is exactly what the fortress said while the rig was
    writing to a template row.

    Note also that a pool increase and no effect at all are INDISTINGUISHABLE
    to anything that reads only HP lost, which is all the old rig could do. Use
    --run trenches, which reads HP lost and the derived pool separately and so
    can tell the two apart.

KNOWN SERVER BUG
    A Balloon ('bal') in 'air' terrain makes the server silently return the
    bare input form: no error, no results, and the ENTIRE multi-stack batch is
    aborted, not just that pair. Reproduced three times; vanished the moment
    'bal' was dropped. guard_payload() below refuses to send that combination.

BUILDING ROWS INDEX FROM 1, NOT 0
    bldg.0 is a hidden TEMPLATE that the page clones to make real rows, and
    every browser submission carries it, so the server must ignore it. An
    earlier note here claimed building rows index from 0 while unit rows index
    from 1. That was wrong, and it is what made fortresses read as inert: the
    sweep configured the template, the baseline already contained it, and so
    the control and the level-1 run were the same request. See exp_fortress.

STILL OPEN
    - The other seven building types. --run buildings reads DR straight off
      each one's result row; written and offline-tested, never run live.
    - Trenches: which of the three mechanics, if any. --run trenches.
    - Does damage depend on the TARGET? unit_stats measured every unit against
      ITSELF, so the whole table is the diagonal of a matrix nobody has seen
      off-diagonal. The bomber is the sharp case: 3.0 against bombers, but the
      original notes claim 25.0 against infantry and 0.0 against heavy tanks.
      --run air_vs_ground, then --run land_matrix.
    - Terrain multipliers untouched.
    - Variance distribution (the +/-10% roll) never sampled.
    - What 'hours' and the resource columns of the summary table mean.

ISOLATION TECHNIQUE
    Isolation is by the 'target' field, NOT by distance. A.n.target = B.n pairs
    two stacks; target = 0 means defend. Position governs range-to-target and
    building inheritance only.

    (An earlier version of this note claimed 10 km spacing was the isolation
    mechanism and that ranged units contaminated neighbouring pairs. That was
    wrong. It is corrected here because it drove several experiment designs.)

    bytro.js allows maxStacks = 100, so multi-pair batching can scale well past
    the 8 pairs previously assumed — but one invalid combination aborts the
    ENTIRE batch, so stay at one pair per submission until single-pair runs are
    trusted.

TRANSPORT
    The ONLY thing that was ever broken here was the missing submit marker.
    Once MainSubmitButton='Start Battle' is injected, a plain urlencoded POST
    round-trips fine — confirmed by a live --sanity run.

    The form does declare enctype="multipart/form-data" and onAttack() ends in
    a native form.submit(), so a real browser posts multipart. The server
    evidently accepts both. urlencoded is the default because it is the
    encoding with live proof behind it; --encoding multipart is available to
    reproduce the browser byte-for-byte if a payload ever behaves oddly
    (suspect it first for values containing '&', '=' or non-ASCII).

COURTESY
    This is one person's fan site. DEFAULT_DELAY is deliberately slow. Please
    don't lower it much; a full sweep is a few hundred requests and there is
    no reason to make that anyone's bad afternoon.
"""

from __future__ import annotations

import argparse
import html as html_mod
import http.cookiejar
import json
import math
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Callable, Iterable

BASE_URL = "https://dxcalc.com/s1914"
DEFAULT_DELAY = 1.5
RESULTS_PATH = "results.jsonl"

# Where a response that yielded no readings gets dumped for inspection.
#
# This used to be last_response.html — which is also the COMMITTED CAPTURE of
# the real form that all five offline test suites are built on. So any failed
# submission overwrote the fixture with the failure body, and the balloon bug
# alone is enough to trigger it: one 'bal' in air terrain and the file becomes
# a stub, every mock server starts serving a page with no fields, and all
# seventy-odd offline checks fail with "page layout changed?" — pointing at
# dxcalc.com when nothing about the site has changed at all.
#
# The two uses are genuinely different: one is a fixture, the other is scratch.
# They now have different names. results.jsonl was lost once to a comparable
# accident and had to be rebuilt from a session transcript; this is the same
# hazard with a longer fuse, because a clobbered fixture still looks like a file.
FAILURE_PATH = "last_failure.html"

SLOT_RE = re.compile(r"^([AB])\.(\d+)\.(\d+)$")
# Buildings get their own result row, e.g. B.1.bldg.1, and it does NOT match
# SLOT_RE. Without matching it here the building's span inherits whichever unit
# slot was last seen and overwrites that stack's reading — which is exactly
# what happened to the attacker throughout the fortress sweep.
#
# A HERO row is the same hazard with a different shape. addHero() inserts
# <div id="B.1.hero"> immediately before the first unit row, and there is only
# ever one per stack, so it carries NO trailing index — the building pattern
# above would not match it either. Caught before the first hero request was
# ever sent, by asking the question the fortress phase taught us to ask.
RESULT_SLOT_RE = re.compile(
    r"^([AB])\.\d+(?:\.[A-Za-z]+)?\.\d+$|^([AB])\.\d+\.hero$")
# The stack container itself: <div id=A.1>. Deliberately excludes A.1.1 and
# A.1.bldg.0 — this is what a per-stack summary table is attached to.
STACK_ID_RE = re.compile(r"^([AB])\.(\d+)$")
UA = "Mozilla/5.0 (X11; Linux x86_64) dxcalc-probe/1.0 (research; contact via dxcalc forum)"


# --------------------------------------------------------------------------
# HTML scraping
# --------------------------------------------------------------------------

class FormScraper(HTMLParser):
    """Collect name -> default value for every field on the page.

    We send back every field we found, mutating only what an experiment asks
    for. That sidesteps the failure the browser run hit, where a hand-rolled
    POST with a partial body came back as the bare form.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fields: dict[str, str] = {}
        self._select_name: str | None = None
        self._select_has_selection = False
        self._optgroup: str | None = None
        self.select_options: dict[str, list[str]] = {}
        # name -> {optgroup label -> [option values]}, so unit codes can be
        # classified as Land / Air / Naval without hardcoding a roster.
        self.select_groups: dict[str, dict[str, list[str]]] = {}
        self.option_labels: dict[str, dict[str, str]] = {}
        self._pending_option: tuple[str, str] | None = None
        self.form_action: str | None = None
        self.form_method: str = "post"
        self.form_enctype: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "form":
            if self.form_action is None:
                self.form_action = a.get("action", "")
                self.form_method = a.get("method", "post").lower()
                self.form_enctype = a.get("enctype", "").lower().strip()
        elif tag == "input":
            name = a.get("name")
            if not name:
                return
            itype = a.get("type", "text").lower()
            if itype in ("checkbox", "radio"):
                if "checked" in a:
                    self.fields[name] = a.get("value", "on")
                else:
                    self.fields.setdefault(name, "")
            elif itype in ("button", "submit", "image", "reset"):
                # type=button carries no implicit submit value; skip it.
                return
            else:
                self.fields[name] = a.get("value", "")
        elif tag == "select":
            self._select_name = a.get("name")
            self._select_has_selection = False
            if self._select_name:
                self.fields.setdefault(self._select_name, "")
                self.select_options.setdefault(self._select_name, [])
        elif tag == "optgroup":
            self._optgroup = a.get("label", "")
        elif tag == "option" and self._select_name:
            val = a.get("value", "")
            self.select_options[self._select_name].append(val)
            self._pending_option = (self._select_name, val)
            if self._optgroup:
                self.select_groups.setdefault(self._select_name, {}) \
                    .setdefault(self._optgroup, []).append(val)
            if "selected" in a:
                self.fields[self._select_name] = val
                self._select_has_selection = True
            elif not self._select_has_selection and not self.fields[self._select_name]:
                self.fields[self._select_name] = val
        elif tag == "textarea":
            name = a.get("name")
            if name:
                self.fields.setdefault(name, "")

    def handle_data(self, data: str) -> None:
        if self._pending_option:
            name, val = self._pending_option
            text = data.strip()
            if text:
                self.option_labels.setdefault(name, {})[val] = text

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self._select_name = None
            self._optgroup = None
        elif tag == "optgroup":
            self._optgroup = None
        elif tag == "option":
            self._pending_option = None


class ResultScraper(HTMLParser):
    """Pull surviving-HP readings, keyed by the nearest preceding A.N.M / B.N.M id.

    The results markup puts the slot id on a container and the number in a
    <span class="hpLeft"> somewhere after it, so "nearest preceding matching
    id" is the association rule.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.readings: dict[str, str] = {}
        self._slot: str | None = None
        self._capture = False
        self._depth = 0
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        node_id = a.get("id", "")
        if RESULT_SLOT_RE.match(node_id):
            self._slot = node_id
        classes = a.get("class", "").split()
        if tag == "span":
            # Spans nest: the building row wraps its arrow in
            # <span style=font-size:large>. Counting depth stops the inner
            # </span> from ending the capture early and truncating the text.
            if self._capture:
                self._depth += 1
            elif "hpLeft" in classes:
                self._capture = True
                self._depth = 1
                self._buf = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._capture:
            self._depth -= 1
            if self._depth > 0:
                return
            self._capture = False
            text = "".join(self._buf).strip()
            if self._slot and text:
                self.readings[self._slot] = text


class SpanCensus(HTMLParser):
    """Every span class in a response, with a sample of its text.

    The parser keys on 'hpLeft', but the rendered page says "Lost N HP", so
    there may well be a second span carrying a different quantity. This lists
    what is actually there instead of guessing.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.classes: dict[str, list[str]] = {}
        self._cls: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "span":
            return
        a = {k: (v or "") for k, v in attrs}
        self._cls = a.get("class", "(no class)")
        self._buf = []

    def handle_data(self, data):
        if self._cls is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "span" and self._cls is not None:
            text = "".join(self._buf).strip()
            if text:
                self.classes.setdefault(self._cls, []).append(text)
            self._cls = None


class StackSummaryScraper(HTMLParser):
    """Per-stack <table class=resultTable>, which nobody had read until now.

    Every stack's result block is followed by a small table the spans do not
    duplicate:

        | HP lost | % lost | food | fish | iron | wood | coal | oil | gas | cash | hours
        |  141.67 |   23.6 |    0 |    0 |    0 |    0 |    0 |   0 |   0 |  $0 |    23

    Two things make it worth parsing.

    FIRST, PRECISION. The span rounds HP to one decimal and the table does not:
    141.67 against the span's "Lost 141.7 HP", 11.33 against "Lost 11.3 HP".
    The percentage goes the other way — the span carries three significant
    figures (1.89%) where the table prints one decimal (1.9) — so the two
    sources are complementary, and the best pool estimate available from a
    single request is the TABLE's HP over the SPAN's percentage. That directly
    sharpens max-HP, which until now was derived from the percentage alone and
    landed on 60.06 / 175.44 / 260.12 for what are plainly 60 / 175 / 260.

    SECOND, COLUMNS NOBODY HAS LOOKED AT. The resource columns and 'hours' are
    unexplained; they are recorded rather than interpreted, so a later session
    has the data without spending requests to get it.

    ASSOCIATION RULE: the table belongs to the stack container most recently
    opened — <div id=A.1>, matched by STACK_ID_RE, not A.1.1 and not
    A.1.bldg.0. In the captured response the order is strictly
    stack-A / its rows / table, stack-B / its rows / table, so "nearest
    preceding stack id" is exact rather than a heuristic. Getting an
    association rule wrong is how the building row came to clobber the
    attacker's reading for the whole first phase of this project, so
    refine_details() below cross-checks every table against the spans it
    claims to summarise instead of trusting this comment.

    NOTE the table counts UNIT rows only: the fortress run has B.1 losing 11.3
    HP of units and 8.5 HP of fortress, and its table says 11.33, not 19.8.
    """

    # Header text -> key. Unknown headers are slugified rather than dropped, so
    # a column dxter adds later shows up as data instead of vanishing.
    COLUMNS = {"hp lost": "hp_lost", "% lost": "pct_lost"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.summaries: dict[str, dict[str, float]] = {}
        self.extra_rows: dict[str, list[list[str]]] = {}
        self._stack: str | None = None
        self._in_table = False
        self._rows: list[list[str]] = []
        self._cells: list[str] | None = None
        self._buf: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if STACK_ID_RE.match(a.get("id", "")):
            self._stack = a.get("id", "")
        if tag == "table" and "resultTable" in a.get("class", "").split():
            self._in_table = True
            self._rows = []
        elif self._in_table:
            if tag == "tr":
                self._cells = []
            elif tag in ("th", "td") and self._cells is not None:
                self._buf = []

    def handle_data(self, data: str) -> None:
        if self._buf is not None:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._in_table:
            return
        if tag in ("th", "td") and self._buf is not None and self._cells is not None:
            self._cells.append("".join(self._buf).strip())
            self._buf = None
        elif tag == "tr" and self._cells is not None:
            self._rows.append(self._cells)
            self._cells = None
        elif tag == "table":
            self._in_table = False
            self._store()

    @classmethod
    def _key(cls, header: str) -> str:
        h = header.strip().lower()
        if h in cls.COLUMNS:
            return cls.COLUMNS[h]
        return re.sub(r"[^a-z0-9]+", "_", h).strip("_") or "col"

    @staticmethod
    def _value(cell: str) -> float | None:
        """'141.67' -> 141.67, '$0' -> 0.0, '' -> None. Currency and thousands
        separators are formatting; a cell that is not a number at all is
        reported as None rather than guessed at."""
        m = re.search(r"-?\d+(?:\.\d+)?", strip_thousands(cell.replace("$", "")))
        return float(m.group(0)) if m else None

    def _store(self) -> None:
        if len(self._rows) < 2:
            return
        if not self._stack:
            print("  ! resultTable with no preceding stack id — not recorded.",
                  file=sys.stderr)
            return
        header, data = self._rows[0], self._rows[1]
        row: dict[str, float] = {}
        for name, cell in zip(header, data):
            val = self._value(cell)
            if val is not None:
                row[self._key(name)] = val
        if row:
            self.summaries[self._stack] = row
        # More than one data row would mean the table carries a per-round or
        # per-unit breakdown, which would be worth having. Say so loudly rather
        # than silently keeping the first line.
        if len(self._rows) > 2:
            self.extra_rows[self._stack] = self._rows[2:]
            print(f"  ! resultTable for {self._stack} has "
                  f"{len(self._rows) - 1} data rows, not 1 — only the first is "
                  f"summarised; the rest are in extra_rows.", file=sys.stderr)


def stack_of(slot: str) -> str | None:
    """'A.1.1' -> 'A.1', 'B.1.bldg.1' -> 'B.1'."""
    m = re.match(r"^([AB]\.\d+)\.", slot)
    return m.group(1) if m else None


def refine_details(details: dict[str, dict[str, float]],
                   summaries: dict[str, dict[str, float]],
                   quiet: bool = False) -> dict[str, dict[str, float]]:
    """Upgrade span readings with the summary table's extra digit, where safe.

    The table gives a stack TOTAL over its unit rows; the spans give the split.
    So the table can only replace a span when the stack has exactly one unit
    row with a reading — which is every experiment here, because duel() blanks
    rows 2-15 precisely so a single reading means a single unit type.

    Before substituting anything, the sum of that stack's unit spans is checked
    against the table. Agreement to within span rounding is the evidence that
    the association rule held and that nothing unmodelled is in the total; a
    mismatch is reported and the spans are left alone. A silent upgrade that
    attached B.1's table to A.1 would be the building-row bug all over again,
    and it would be far harder to spot because the numbers would still look
    plausible.

    Building rows (delta notation) are excluded from the sum: the fortress
    response proves the table leaves them out.
    """
    out = {slot: dict(d) for slot, d in details.items()}
    for stack, summary in summaries.items():
        total = summary.get("hp_lost")
        if total is None:
            continue
        # Building rows carry delta notation and ARE excluded -- the fortress
        # response proves the table leaves them out. A HERO row is the
        # opposite, and it was guessed wrong before it was measured: the hero
        # renders an ordinary "Lost 2.1 HP (5.19%)" span and the table COUNTS
        # it. Every hero request reconciles exactly once it is included
        # (77.90 units + 2.10 hero = 80.00 table, on all sixteen). So a hero
        # belongs to its stack in a way a building does not.
        units = [s for s, d in details.items()
                 if stack_of(s) == stack and not d.get("delta") and "lost" in d]
        if not units:
            continue
        span_sum = sum(details[s]["lost"] for s in units)
        # Each span is rounded to 0.1, the table to 0.01.
        tol = 0.05 * len(units) + 0.02
        if abs(span_sum - total) > tol:
            if not quiet:
                print(f"  ! {stack}: summary table says {total} HP lost but its "
                      f"spans sum to {span_sum:.2f} (tolerance {tol:.2f}). "
                      f"Not substituting — check the table/stack association "
                      f"before trusting either number.", file=sys.stderr)
            continue
        if len(units) != 1:
            continue                      # total is real, but not divisible
        slot = units[0]
        d = out[slot]
        d["lost_span"] = details[slot]["lost"]
        d["lost"] = total
        d["lost_source"] = 1.0            # 1.0 = table, absent = span
        # Pool from the table's HP over the SPAN's percentage: the better half
        # of each source. This is what sharpens max HP.
        pct = d.get("pct")
        if pct:
            d["pool"] = round(total / (pct / 100), 1)
        for key in ("hours", "cash"):
            if key in summary:
                d[f"stack_{key}"] = summary[key]
    return out


# onAttack(name, value) injects a hidden field at click time so the server can
# recognise the POST as an attack. It is NOT in the DOM, so it never showed up
# in a field dump — and without it the server just re-renders the empty form.
ONATTACK_RE = re.compile(
    r"""onAttack\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)""")


def find_submit_marker(page: str) -> tuple[str, str] | None:
    """Recover the hidden marker field from the button's onclick attribute."""
    m = ONATTACK_RE.search(html_mod.unescape(page))
    return (m.group(1), m.group(2)) if m else None


# The form declares enctype="multipart/form-data" and onAttack() finishes with a
# native form.submit(), so a browser posts multipart. The server accepts plain
# urlencoded too — a live --sanity run proved it — so this is here as a
# byte-faithful fallback, not as the default. Reach for it only if a payload
# misbehaves in a way that smells like encoding (embedded '&' or '=', non-ASCII).
MULTIPART_BOUNDARY = "----dxcalcProbeBoundary7MA4YWxkTrZu0gW"


def encode_multipart(payload: dict[str, str],
                     boundary: str = MULTIPART_BOUNDARY) -> tuple[bytes, str]:
    """Encode fields as multipart/form-data. Returns (body, content_type).

    Every value here is a short unit code or number, so a fixed boundary keeps
    payloads byte-reproducible and diffable against a captured browser POST.
    Collisions are still checked for rather than assumed away.
    """
    while any(boundary in v for v in payload.values()) or \
            any(boundary in k for k in payload):
        boundary += "x"
    out: list[bytes] = []
    for key, val in payload.items():
        # Quote-escape per RFC 7578 §4.2; field names here are ASCII like
        # "A.1.1.count", but don't assume it.
        safe = key.replace("\\", "\\\\").replace('"', '\\"')
        out.append(f"--{boundary}\r\n".encode())
        out.append(
            f'Content-Disposition: form-data; name="{safe}"\r\n\r\n'.encode())
        out.append(str(val).encode("utf-8") + b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


OOPS_RE = re.compile(r"oops:[^<>\n]{0,200}", re.I)


def find_oops(html: str) -> list[str]:
    """The calculator reports bad input as 'oops: ...' text. Read it back."""
    return [m.strip() for m in OOPS_RE.findall(html)]


MAX_LEVEL_RE = re.compile(r"max level for\s+(.+?)\s+is\s+(\d+)", re.I)


def parse_max_level(messages: list[str]) -> int | None:
    """Read the cap out of 'oops: max level for Recruiting is 1'.

    Only the fortress goes to level 5. Every other building type is capped
    lower, and the server states the cap rather than clamping to it — so a
    sweep with a hardcoded level gets a rejection, not a reading. Taking the
    number from the message means the sweep never carries a table of caps that
    can drift out of date against the site.
    """
    for m in messages:
        hit = MAX_LEVEL_RE.search(m)
        if hit:
            try:
                lvl = int(hit.group(2))
            except ValueError:
                continue
            if lvl >= 1:
                return lvl
    return None


def strip_thousands(text: str) -> str:
    """Drop thousands separators before parsing a number.

    dxcalc renders decimals with a dot throughout — 1375.1, 480.5, 16.7% — so a
    comma sitting between digits is a thousands separator, never a decimal
    point. The previous replace(",", ".") turned "1,375.1" into "1.375.1",
    which the number regex then read as 1.375: a silent thousandfold error on
    any stack above 999 HP, and large stacks are exactly where the size-factor
    sweep operates.
    """
    return re.sub(r"(?<=\d),(?=\d)", "", text)


def parse_hp(text: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", strip_thousands(text))
    return float(m.group(0)) if m else None


# The span renders e.g. "Lost 50.0 HP (16.7%) 2 died", or "all 1 died" when the
# stack is wiped, or "no living units specified here" for a blanked row.
#
# The percentage is the loss as a fraction of that stack's FULL pool, so it
# hands us the pool for nothing: pool = lost / pct. Divide by the unit count and
# you have that unit type's max HP from the very same request that measured
# damage. Reading only the first number threw all of that away.
READING_RE = re.compile(
    r"Lost\s+(-?[\d.]+)\s*HP\s*\(\s*(-?[\d.]+)\s*%\s*\)"
    r"(?:\s*(?:all\s+)?(\d+)\s+died)?", re.I)


# Buildings report in a different shape entirely: "-8.5 HP (17%) →" rather
# than "Lost 8.5 HP (17%) 0 died". The minus is delta notation, not a signed
# loss, and the arrow points at the resulting value. Same arithmetic underneath
# — magnitude over percentage still gives the pool — but the wording differs,
# so it needs its own pattern instead of falling through to parse_hp().
#
# A building that dies in the round loses the arrow and the LVL tail entirely,
# and spaces the minus off the number:
#
#   "- 5.0 HP (100%) destroyed"
#
# The old pattern required the arrow, so a destroyed building parsed as nothing
# and the sweep printed "NO ROW" — indistinguishable from a type the server had
# ignored, which is the exact confusion this experiment exists to resolve. A
# level-1 Recruiting Office has 5 HP and 30 infantry deal 8.5, so the smaller
# buildings hit this on any ordinary run.
DELTA_RE = re.compile(
    r"(-?\s*[\d.]+)\s*HP\s*\(\s*([\d.]+)\s*%\s*\)\s*(?:(?:→|->)|(destroyed))",
    re.I)

# The building row continues past the arrow, and the tail is the most
# informative text on the page:
#
#   "-8.5 HP (3.4%) → LVL:5 41.5 HP; DR: 90% → 87.5%"
#
# It names the mechanic outright. DR is Damage Reduction, and the pair of
# values is DR before and after this round's damage, so one request gives the
# building's level, its remaining HP, and the mitigation it is currently
# conferring — no fitting required.
BLDG_TAIL_RE = re.compile(
    r"LVL:\s*([\d.]+)\s+([\d.]+)\s*HP\s*;\s*"
    r"DR:\s*([\d.]+)\s*%\s*(?:→|->)\s*([\d.]+)\s*%", re.I)


def parse_reading(text: str) -> dict[str, float] | None:
    """Full breakdown of one result span, not just the leading number."""
    text = strip_thousands(text)
    m = READING_RE.search(text)
    if not m:
        d = DELTA_RE.search(text)
        if d:
            lost = abs(float(d.group(1).replace(" ", "")))
            pct = float(d.group(2))
            out: dict[str, float] = {"lost": lost, "pct": pct, "delta": 1.0}
            if d.group(3):
                out["destroyed"] = 1.0
            if pct > 0:
                out["pool"] = round(lost / (pct / 100), 1)
            tail = BLDG_TAIL_RE.search(text)
            if tail:
                out["level"] = float(tail.group(1))
                out["hp_top_level"] = float(tail.group(2))
                out["dr_before"] = float(tail.group(3))
                out["dr_after"] = float(tail.group(4))
            return out
        return None
    lost = float(m.group(1))
    pct = float(m.group(2))
    out: dict[str, float] = {"lost": lost, "pct": pct}
    if m.group(3) is not None:
        out["died"] = float(m.group(3))
    if pct > 0:
        # Rounded because the page prints the percentage to one decimal, so
        # the implied pool carries about three significant figures.
        out["pool"] = round(lost / (pct / 100), 1)
    return out


# --------------------------------------------------------------------------
# Probe driver
# --------------------------------------------------------------------------

def build_ssl_context(insecure: bool = False) -> ssl.SSLContext:
    """Trust store for the HTTPS connection.

    The python.org macOS builds don't link against the system keychain, so a
    stock install has an empty CA store and every HTTPS fetch fails with
    CERTIFICATE_VERIFY_FAILED. certifi carries its own bundle, which fixes it
    without touching the system.
    """
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        print("  ! TLS verification DISABLED (--insecure).", file=sys.stderr)
        return ctx
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


class BareFormReturned(RuntimeError):
    """Server handed back the empty input form: no results, no error.

    Carries the server's own `oops:` lines when there were any, so a caller can
    act on what the server said instead of re-parsing the message text.
    """

    def __init__(self, message: str, oops: list[str] | None = None) -> None:
        super().__init__(message)
        self.oops = oops or []


class Probe:
    def __init__(self, delay: float = DEFAULT_DELAY, dry_run: bool = False,
                 insecure: bool = False, encoding: str = "urlencoded",
                 save_response: str | None = None) -> None:
        self.delay = delay
        self.dry_run = dry_run
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=build_ssl_context(insecure)),
        )
        self.baseline: dict[str, str] = {}
        self.post_url = BASE_URL
        self.form_method = "post"
        self.form_enctype = ""          # what the page declares, informational
        self.encoding = encoding        # what we actually send
        self.save_response = save_response
        self.last_details: dict[str, dict[str, float]] = {}
        self.last_raw: dict[str, str] = {}
        self.last_summary: dict[str, dict[str, float]] = {}
        self.last_response = ""
        self.submit_marker: tuple[str, str] | None = None
        self.select_options: dict[str, list[str]] = {}
        self.select_groups: dict[str, dict[str, list[str]]] = {}
        self.option_labels: dict[str, dict[str, str]] = {}
        self._last_request = 0.0
        self.request_count = 0

    # -- transport ---------------------------------------------------------

    def _throttle(self) -> None:
        gap = time.monotonic() - self._last_request
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last_request = time.monotonic()

    def load_form(self) -> dict[str, str]:
        self._throttle()
        req = urllib.request.Request(BASE_URL, headers={"User-Agent": UA})
        with self.opener.open(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", "replace")
        scraper = FormScraper()
        scraper.feed(html)
        self.submit_marker = find_submit_marker(html)
        if self.submit_marker:
            print(f"Submit marker: {self.submit_marker[0]} = "
                  f"{self.submit_marker[1]!r}")
        else:
            print("  ! No onAttack(...) marker found — POSTs will likely come "
                  "back as the bare form.", file=sys.stderr)
        self.baseline = scraper.fields
        self.post_url = urllib.parse.urljoin(BASE_URL, scraper.form_action or "")
        self.form_method = scraper.form_method
        self.form_enctype = scraper.form_enctype
        print(f"Encoding: sending {self.encoding} "
              f"(form declares {self.form_enctype or 'nothing'})")
        self.select_options = scraper.select_options
        self.select_groups = scraper.select_groups
        self.option_labels = scraper.option_labels
        if not self.baseline:
            raise RuntimeError("No form fields found — page layout changed?")
        return self.baseline

    def submit(self, overrides: dict[str, Any],
               create: Iterable[str] = ()) -> dict[str, float]:
        if not self.baseline:
            self.load_form()
        payload = dict(self.baseline)
        create = set(create)
        dropped: list[str] = []
        for k, v in overrides.items():
            val = "" if v is None else str(v)
            if k not in payload and k not in create:
                # Blanking a row the form doesn't have is harmless — that is
                # what duel() does to rows 2-15. SETTING one is a silent bug:
                # the experiment believes it configured something it did not.
                # The fortress sweep lost six requests a run to exactly this.
                if val:
                    dropped.append(k)
                continue
            payload[k] = val
        if dropped:
            print(f"  ! {len(dropped)} field(s) absent from the form were "
                  f"dropped, NOT sent: {', '.join(dropped[:4])}"
                  + (" ..." if len(dropped) > 4 else "")
                  + "\n    (pass create=[...] to synthesise them, as the "
                    "page's own add-row JS does)", file=sys.stderr)

        if self.submit_marker:
            payload[self.submit_marker[0]] = self.submit_marker[1]

        guard_payload(payload)

        if self.dry_run:
            print(json.dumps({k: v for k, v in payload.items() if v}, indent=1))
            return {}

        self._throttle()
        if self.encoding == "multipart":
            body, content_type = encode_multipart(payload)
        else:
            body = urllib.parse.urlencode(payload).encode()
            content_type = "application/x-www-form-urlencoded"
        req = urllib.request.Request(
            self.post_url,
            data=body,
            headers={
                "User-Agent": UA,
                "Content-Type": content_type,
                "Referer": BASE_URL,
                "Origin": "https://dxcalc.com",
            },
        )
        with self.opener.open(req, timeout=60) as resp:
            html = resp.read().decode("utf-8", "replace")
        self.request_count += 1
        self.last_response = html
        if self.save_response:
            with open(self.save_response, "w") as fh:
                fh.write(html)
            print(f"  (response saved to {self.save_response})", file=sys.stderr)

        oops = find_oops(html)
        if oops:
            raise BareFormReturned("server said -> " + " | ".join(oops[:4]), oops)
        scraper = ResultScraper()
        scraper.feed(html)
        if not scraper.readings:
            with open(FAILURE_PATH, "w") as fh:
                fh.write(html)
            raise BareFormReturned(
                "No hpLeft spans in response. Either an invalid unit/terrain "
                "combination aborted the batch (see the balloon bug), or the "
                "POST body is missing a field the server requires."
            )
        summary = StackSummaryScraper()
        summary.feed(html)
        self.last_summary = summary.summaries
        # Full breakdown lives on the Probe; the return value stays a plain
        # slot -> HP-lost mapping so existing experiments keep working.
        self.last_details = {}
        self.last_raw = dict(scraper.readings)
        out: dict[str, float] = {}
        unparsed: list[tuple[str, str]] = []
        for slot, text in scraper.readings.items():
            detail = parse_reading(text)
            if detail is not None:
                self.last_details[slot] = detail
                out[slot] = detail["lost"]
                continue
            val = parse_hp(text)          # fallback for unrecognised phrasing
            if val is not None:
                unparsed.append((slot, text))
                out[slot] = val
        if unparsed:
            # The fallback grabs the first number in the span, which need not
            # be an HP value at all. Say so, and show the text, rather than
            # letting a mystery number enter results.jsonl unremarked.
            print("  ! span text not recognised — fell back to its leading "
                  "number, which may not be HP:", file=sys.stderr)
            for slot, text in unparsed[:4]:
                print(f"      {slot}: {text!r}", file=sys.stderr)
        # The summary table carries one more digit than the span. Substituting
        # it is a no-op on a response that has no table, so nothing that
        # predates this depends on it being there.
        if self.last_summary:
            self.last_details = refine_details(self.last_details,
                                               self.last_summary)
            for slot, detail in self.last_details.items():
                if detail.get("lost_source") == 1.0:
                    out[slot] = detail["lost"]
        return out


def guard_payload(payload: dict[str, str]) -> None:
    """Refuse the one combination known to silently kill a whole submission."""
    for key, val in payload.items():
        if val != "bal":
            continue
        m = re.match(r"^([AB])\.(\d+)\.\d+\.unit$", key)
        if not m:
            continue
        terrain_key = f"{m.group(1)}.{m.group(2)}.terrain"
        if payload.get(terrain_key) == "air":
            raise ValueError(
                f"Refusing to send: {key}=bal with {terrain_key}=air. This "
                "aborts the entire batch server-side with no error."
            )


# --------------------------------------------------------------------------
# Payload helpers
# --------------------------------------------------------------------------

def settings(rounds: str | float = "1", variance: bool = False) -> dict[str, str]:
    """Global form switches.

    simulateVariance MUST be off for a deterministic reading — with it on the
    server rolls the +/-10% and every measurement becomes a sample rather than
    the expected value. updateCounts and newWindow are off so the response is
    a plain results page.
    """
    return {
        "maxRounds": str(rounds),
        "simulateVariance": "on" if variance else "",
        "updateCounts": "",
        "newWindow": "",
    }


MAX_UNIT_ROWS = 15      # the form's own maxUnits; duel() and composite() both honour it


def duel(
    stack: int,
    atk_unit: str,
    atk_count: int,
    def_unit: str,
    def_count: int,
    atk_terrain: str = "land",
    def_terrain: str | None = None,
    atk_hp: str = "100%",
    def_hp: str = "100%",
    position: int = 0,
    trench: int = 0,
    atk_trench: int = 0,
) -> dict[str, str]:
    """One isolated attacker-vs-defender pair in slot `stack`.

    A attacks B explicitly via the target field; B defends (target "0").
    Both sides share a position so ranged attackers are always in range and
    the defender inherits any buildings assigned at that position.

    `trench` is the DEFENDER's trench level and `atk_trench` the attacker's.
    They are separate because whether a trench helps the side that is doing the
    attacking is itself an open question — the fortress turned out to protect
    the defender only — and a single `trench` argument cannot ask it.
    """
    if def_terrain is None:
        def_terrain = atk_terrain
    payload = {
        f"A.{stack}.target": f"B.{stack}",
        f"A.{stack}.terrain": atk_terrain,
        f"A.{stack}.position": str(position),
        f"A.{stack}.trench": str(atk_trench),
        f"A.{stack}.1.unit": atk_unit,
        f"A.{stack}.1.count": str(atk_count),
        f"A.{stack}.1.hp": atk_hp,
        f"B.{stack}.target": "0",
        f"B.{stack}.terrain": def_terrain,
        f"B.{stack}.position": str(position),
        f"B.{stack}.trench": str(trench),
        f"B.{stack}.1.unit": def_unit,
        f"B.{stack}.1.count": str(def_count),
        f"B.{stack}.1.hp": def_hp,
    }
    # The stock form pre-fills extra unit rows. Any left populated joins the
    # fight and quietly ruins a single-variable measurement.
    # maxUnits = 15 in bytro.js. Blanking only 2-8 was an arbitrary "enough"
    # and would leave rows 9-15 populated if anything ever created them.
    for side in ("A", "B"):
        for row in range(2, 16):
            payload[f"{side}.{stack}.{row}.count"] = ""
            payload[f"{side}.{stack}.{row}.hp"] = ""
    return payload


def semantics(p: "Probe") -> None:
    """Settle what the hpLeft span means, and test the attack/defend split.

    Three requests. The trick is ASYMMETRY: scaling both sides equally is not a
    discriminator, because halving every count halves the reading under either
    reading of the span (T/2 - 5d is identically (T - 10d)/2). Changing one
    side at a time separates them cleanly.

    If the span holds HP LOST, a side's reading is damage inflicted BY THE
    OTHER SIDE, so it depends only on the opponent's count and not at all on
    its own. Hold the attacker at 10 and grow the defender: the defender's own
    reading must not move. Hold the defender and grow the attacker: the
    attacker's reading must not move.

    If instead it holds HP REMAINING, every reading is drawn from that side's
    own pool, so both must move when that side's count changes.
    """
    runs = [
        ("baseline   10 atk vs 10 def", 10, 10),
        ("more defs  10 atk vs 15 def", 10, 15),
        ("more atks  15 atk vs 10 def", 15, 10),
    ]
    got: dict[str, dict[str, float]] = {}
    for label, atk, dfn in runs:
        payload = settings("1")
        payload.update(duel(1, "inf", atk, "inf", dfn))
        readings = p.submit(payload)
        got[label] = readings
        detail = dict(p.last_details)
        record("semantics", {"atk": atk, "def": dfn, "detail": detail}, readings)
        print(f"  {label:28} -> A.1.1={readings.get('A.1.1')}  "
              f"B.1.1={readings.get('B.1.1')}")
        # The loss percentage gives each stack's pool, hence max HP per unit.
        for slot, count in (("A.1.1", atk), ("B.1.1", dfn)):
            d = detail.get(slot, {})
            if "pool" in d and count:
                print(f"      {slot} pool {d['pool']:8.1f} HP / {count} units "
                      f"= {d['pool'] / count:6.2f} HP per unit"
                      + (f", {int(d['died'])} died" if "died" in d else ""))

    census = SpanCensus()
    census.feed(p.last_response)
    print("\n  span classes present in the response:")
    for cls, samples in sorted(census.classes.items()):
        print(f"    {cls:16} x{len(samples):<4} e.g. {samples[:3]}")

    # Refuse to rule on absent data. Without this, every reading coming back
    # None compares equal to every other and the "unchanged" test below passes
    # vacuously, announcing HP-LOST with a 0.0 damage split. A confident
    # verdict from no measurement is the worst output this could produce.
    missing = [lbl for lbl, r in got.items()
               if r.get("A.1.1") is None or r.get("B.1.1") is None]
    if missing:
        print("\n  NO VERDICT — missing readings from: " + "; ".join(missing))
        print("  Nothing is concluded. Check the span census above: if the "
              "classes listed are not 'hpLeft', ResultScraper is keying on "
              "the wrong one.")
        return

    base, more_d, more_a = (got[r[0]] for r in runs)
    b_fixed = base.get("B.1.1"), more_d.get("B.1.1")
    a_fixed = base.get("A.1.1"), more_a.get("A.1.1")
    print(f"\n  defender's own count 10->15, its reading: {b_fixed[0]} -> {b_fixed[1]}")
    print(f"  attacker's own count 10->15, its reading: {a_fixed[0]} -> {a_fixed[1]}")

    unchanged = (b_fixed[0] == b_fixed[1] and a_fixed[0] == a_fixed[1])
    if unchanged:
        print("\n  VERDICT: hpLeft is HP LOST. Each side's reading tracks the "
              "opponent's count only.")
        atk_per = (base.get("B.1.1") or 0) / 10
        def_per = (base.get("A.1.1") or 0) / 10
        print(f"  infantry damage: {atk_per} per unit attacking, "
              f"{def_per} per unit defending", end="")
        print(f"  (ratio {def_per / atk_per:.3f})" if atk_per else "")
    else:
        print("\n  VERDICT: NOT pure HP-lost — a side's reading moved with its "
              "own count. Treat readings as HP remaining, or as a mix, and "
              "re-derive before trusting any damage number.")


def clear_stacks(first: int, last: int) -> dict[str, str]:
    """Blank out stacks so leftovers from a previous run don't contaminate."""
    out: dict[str, str] = {}
    for i in range(first, last + 1):
        for side in ("A", "B"):
            out[f"{side}.{i}.1.count"] = ""
            out[f"{side}.{i}.1.hp"] = ""
    return out


def record(tag: str, meta: dict[str, Any], readings: dict[str, float]) -> None:
    row = {"ts": time.time(), "experiment": tag, "meta": meta, "readings": readings}
    with open(RESULTS_PATH, "a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(f"  {tag} {meta} -> {readings}")


# --------------------------------------------------------------------------
# Experiments
# --------------------------------------------------------------------------

UNIT_FIELD = "A.1.1.unit"

# In-game ranges, per the help page. Anything here reaches BEYOND the 5 km
# melee range, so a multi-pair batch spaced 10 km apart does NOT isolate them —
# a railgun at 150 km reaches every other pair on the board. This is why every
# experiment below submits ONE pair at a time.
RANGED_KM = {"artillery": 50, "railgun": 150, "cruiser": 40, "battleship": 75}


# Confirmed from the live form: 17 codes in one flat select.
#   lart = Light Artillery, rrg = Railgun, lt = Tank (not Heavy Tank),
#   convoy = Airplane Convoy, st = Stormtrooper, cl = Light Cruiser.
UNIT_CLASSES: dict[str, list[str]] = {
    "land": ["inf", "cav", "ac", "lart", "art", "rrg", "lt", "ht", "convoy", "st"],
    "air": ["bal", "int", "tac", "zep"],
    "naval": ["sub", "cl", "bb"],
}

# Every building the form offers, each with lvl 1-5 and its own HP.
BUILDINGS = ["fortress", "recruiting", "railway", "workshop",
             "factory", "barracks", "aerodrome", "harbor"]


def roster(p: Probe, group: str) -> list[str]:
    """Unit codes for a class, intersected with what the page actually offers.

    Classification is hardcoded because the unit select has no optgroups —
    guessing by position in a flat list would silently put a battleship in
    land terrain and abort the run.
    """
    available = [v for v in p.select_options.get(UNIT_FIELD, []) if v]
    known = UNIT_CLASSES.get(group.lower(), [])
    picked = [u for u in known if u in available]
    unseen = [u for u in available if u not in sum(UNIT_CLASSES.values(), [])]
    if unseen:
        print(f"  ! unclassified unit codes on the page: {unseen}", file=sys.stderr)
    return picked


def label_of(p: Probe, code: str) -> str:
    return p.option_labels.get(UNIT_FIELD, {}).get(code, code)


# The unit table as measured by --run unit_stats, reproduced identically on two
# runs an hour apart. Kept as data, not just prose in the docstring, for two
# reasons: stacks can be sized from it so a measurement is not thrown away to
# saturation, and every later reading of a unit's pool becomes a free
# regression check on the row — a silent change to the site shows up as a
# disagreement instead of as a quietly different constant.
#
# code -> (max HP, damage per unit attacking, damage per unit defending)
# 'bal' is absent deliberately: it has never been measured, because a balloon
# in air terrain kills the whole submission.
MEASURED_UNITS: dict[str, tuple[float, float, float]] = {
    "inf": (20.0, 4.0, 5.0),
    "cav": (25.0, 15.0, 7.5),
    "ac": (60.0, 6.0, 12.0),
    "lart": (10.0, 5.0, 1.0),
    "art": (20.0, 8.0, 2.7),
    "rrg": (60.0, 20.0, 6.7),
    "lt": (175.0, 30.0, 30.0),
    "ht": (260.0, 45.0, 45.0),
    "convoy": (20.0, 1.0, 1.0),
    "st": (40.0, 25.0, 6.3),
    "int": (60.0, 20.0, 20.0),
    "tac": (80.0, 3.0, 3.0),
    "zep": (140.0, 5.0, 5.0),
    "sub": (100.0, 40.0, 40.0),
    "cl": (50.0, 10.0, 10.0),
    "bb": (200.0, 40.0, 40.0),
}

# Sizing basis for a defender stack: the largest attack coefficient in the
# table, not the attacker's own measured value. Those were all measured U vs U,
# and the whole question here is whether damage is much larger against a
# different class — the note that started this said a bomber deals 25.0 to
# infantry while unit_stats measured it at 3.0 against bombers. Sizing on 3.0
# would guarantee the wipe that destroys the reading.
ATK_CEILING = max(atk for _, atk, _ in MEASURED_UNITS.values())
SIZING_SAFETY = 2.5
MAX_DEF_COUNT = 400


def defender_count(code: str, atk_n: int) -> int:
    """Enough defenders that one round cannot wipe them.

    A wiped stack has its loss capped at its own pool, which understates the
    opponent's damage — and understating it is indistinguishable from the
    target-class rule this experiment is looking for. Pool grows linearly with
    the count while the stack-size factor caps damage output at 35 effective
    units, so a fat defender costs nothing but a bigger number in the payload.
    """
    hp = MEASURED_UNITS.get(code, (20.0, 0.0, 0.0))[0]
    need = SIZING_SAFETY * atk_n * ATK_CEILING / hp
    return max(20, min(MAX_DEF_COUNT, math.ceil(need)))


def exp_matchups(p: Probe, attackers: list[str], targets: list[str],
                 tag: str, atk_terrain: str, def_terrain: str,
                 atk_n: int = 10) -> None:
    """Cross-matrix of X attacking Y, with every reading labelled by side.

    This replaces damage_land / damage_air / damage_sea, which sent one
    attacker against twenty defenders and recorded the bare span numbers with
    no note of which side each came from. Pooling an attacker-loss with a
    defender-loss reading averages two independent coefficients into a number
    that is neither, and a lone attacker is wiped in the measured round, so the
    reading that survived was the capped one.

    What unit_stats cannot answer: it measures U against U only, so every
    coefficient in it is same-class. If damage depends on the TARGET, those are
    17 points on the diagonal of a matrix nobody has seen off-diagonal.

    Each submission yields two cells, because one battle contains both roles:

        defender's loss / E(attacker count) = X's damage ATTACKING Y
        attacker's loss / E(defender count) = Y's damage DEFENDING against X

    The attacker count is held at 10 so E(n) = n exactly and the size factor
    cannot confound anything; the defender stack is sized to survive.
    """
    if not attackers or not targets:
        print("  ! nothing to sweep — empty roster.", file=sys.stderr)
        return
    print(f"  {len(attackers)} attacker(s) x {len(targets)} target(s), "
          f"{atk_n} attacking, one request each\n")
    print(f"  {'atk':7} {'target':7} {'defN':>5} {'dmg/atk':>9} {'corrected':>9} "
          f"{'dmg/def':>9} {'targetHP':>9}  note")

    matrix: dict[str, dict[str, float]] = {}
    raw_matrix: dict[str, dict[str, float]] = {}
    for x in attackers:
        for y in targets:
            def_n = defender_count(y, atk_n)
            note = ""
            r = None
            for attempt in range(3):
                try:
                    payload = settings("1")
                    payload.update(duel(1, x, atk_n, y, def_n,
                                        atk_terrain=atk_terrain,
                                        def_terrain=def_terrain))
                    p.submit(payload)
                except ValueError as e:                 # guard_payload refused
                    print(f"  {x:7} {y:7} {'-':>5} {'-':>9} {'-':>9} {'-':>9} "
                          f"{'-':>9}  SKIPPED: {e}")
                    record(tag, {"atk": x, "target": y, "skipped": str(e)}, {})
                    r = None
                    break
                except BareFormReturned as e:
                    print(f"  {x:7} {y:7} {def_n:>5} {'-':>9} {'-':>9} {'-':>9} "
                          f"{'-':>9}  FAILED: {e}")
                    record(tag, {"atk": x, "target": y, "error": str(e)}, {})
                    r = None
                    break
                d = dict(p.last_details)
                a, b = d.get("A.1.1", {}), d.get("B.1.1", {})
                # Only B's wipe spoils the cell this matrix is built from.
                wiped = b.get("pct", 0) >= 99.9
                if wiped and attempt < 2:
                    prev, def_n = def_n, min(MAX_DEF_COUNT, def_n * 4)
                    if def_n > prev:
                        note = f"re-run, defenders wiped at {prev}"
                        continue
                    # Already at the cap: retrying would re-send an identical
                    # payload and spend a live request to learn nothing.
                r = (d, a, b, def_n)
                if wiped:
                    note = "STILL WIPED — lower bound only"
                break
            if r is None:
                continue
            d, a, b, def_n = r

            dmg_atk = (b["lost"] / effective_units(atk_n)) if "lost" in b else None
            dmg_def = (a["lost"] / effective_units(def_n)) if "lost" in a else None
            target_hp = (b["pool"] / def_n) if ("pool" in b and def_n) else None
            # The attacker being wiped is a different worry: nobody has checked
            # whether a stack that dies in the measured round still deals its
            # full damage, so the cell is flagged rather than quietly trusted.
            if a.get("pct", 0) >= 99.9:
                note = (note + "; " if note else "") + "attacker wiped"
            known = MEASURED_UNITS.get(y)
            if known and target_hp and abs(target_hp - known[0]) > 0.05 * known[0]:
                note = ((note + "; " if note else "")
                        + f"pool implies {target_hp:.1f} HP, table says {known[0]}")

            # RETURN FIRE. A stack's output falls in proportion to the share of
            # its own pool it lost in the same round, so the raw figure above is
            # not the attacker's stat — it is the stat times what survived the
            # target's fire. Uncorrected, a tough target looks like a resistant
            # one: the first live run read the Fighter as "target-dependent,
            # 3.68 vs armoured cars up to 4.95 vs light artillery", a 34%
            # spread, when both cells are the same 5.0 stat seen through
            # different amounts of incoming fire. See §4 of HANDOVER.md.
            f_atk = (a["pct"] / 100.0) if a.get("pct") is not None else None
            dmg_atk_corr = None
            if dmg_atk is not None and f_atk is not None and f_atk < 0.999:
                dmg_atk_corr = dmg_atk / (1.0 - f_atk)

            matrix.setdefault(x, {})[y] = (dmg_atk_corr if dmg_atk_corr is not None
                                           else float("nan"))
            raw_matrix.setdefault(x, {})[y] = (dmg_atk if dmg_atk is not None
                                               else float("nan"))
            cell = lambda v: f"{v:9.3f}" if isinstance(v, float) else f"{'?':>9}"
            print(f"  {x:7} {y:7} {def_n:>5} {cell(dmg_atk)} {cell(dmg_atk_corr)} "
                  f"{cell(dmg_def)} {cell(target_hp)}  {note}".rstrip())
            record(tag, {"atk": x, "target": y, "atk_n": atk_n, "def_n": def_n,
                         "atk_terrain": atk_terrain, "def_terrain": def_terrain,
                         "dmg_attacking": dmg_atk,
                         "dmg_attacking_corrected": dmg_atk_corr,
                         "atk_frac_lost": f_atk,
                         "dmg_defending": dmg_def,
                         "target_max_hp": target_hp, "note": note,
                         "atk_label": label_of(p, x),
                         "target_label": label_of(p, y),
                         "detail": d, "summary": dict(p.last_summary)},
                   {"A.1.1": a.get("lost"), "B.1.1": b.get("lost")})

    report_matchups(matrix, raw_matrix)


def report_matchups(matrix: dict[str, dict[str, float]],
                    raw_matrix: dict[str, dict[str, float]] | None = None) -> None:
    """Is damage a property of the attacker alone, or of the pairing?

    The verdict is taken from the RAW row, because the raw row is what was
    measured. The return-fire correction is a model, and applying a model
    before deciding whether it is needed manufactures exactly the kind of
    confident wrong answer this project keeps having to undo — against a server
    that does not attenuate, dividing by (1 - f) turns a flat attacker into a
    target-dependent one.

    So the correction is only consulted when the raw row slopes, and then only
    to ask one question: is the slope explained by how hard each target shoots
    back? That question has a falsifiable answer. On the first live run of
    air_vs_ground it was yes for all three aircraft — a 34% raw spread on the
    Fighter collapsed to 0.45% once corrected, landing on a flat 5.0 — and the
    uncorrected reading would have gone into the model as a target rule that
    does not exist.
    """
    def clean(m: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        out = {x: {y: v for y, v in row.items() if v == v}      # drop NaN
               for x, row in m.items()}
        return {x: row for x, row in out.items() if row}

    corrected = clean(matrix)
    usable = clean(raw_matrix or {}) or corrected
    if not usable:
        print("\n  NO VERDICT — no cell produced a usable reading. Nothing is "
              "concluded; treat this as a defect report against the probe.")
        return
    print("\n  Does an attacker's damage depend on what it is hitting?")
    for x, row in usable.items():
        vals = list(row.values())
        lo, hi = min(vals), max(vals)
        zeros = sorted(y for y, v in row.items() if v == 0)
        if len(vals) < 2:
            print(f"    {x:7} only one target measured — cannot say.")
            continue
        if hi == 0:
            print(f"    {x:7} deals ZERO to every target measured.")
        elif lo == 0:
            print(f"    {x:7} TARGET-DEPENDENT: {hi:.2f} at most, but exactly "
                  f"0 against {', '.join(zeros)}.")
        elif hi / lo - 1 > 0.05:
            worst = min(row, key=row.get)
            best = max(row, key=row.get)
            crow = corrected.get(x, {})
            cvals = [v for y, v in crow.items() if y in row]
            explained = False
            if len(cvals) == len(vals) and min(cvals) > 0:
                clo, chi = min(cvals), max(cvals)
                explained = (chi / clo - 1) <= 0.05
            print(f"    {x:7} raw row slopes {lo:.2f} vs {worst} up to "
                  f"{hi:.2f} vs {best} (x{hi / lo:.2f})")
            if explained:
                print(f"    {'':7}   -> EXPLAINED BY RETURN FIRE, not by the "
                      f"target: correcting each cell for the attacker's own "
                      f"losses gives a flat {min(cvals):.2f}-{max(cvals):.2f} "
                      f"(x{max(cvals) / min(cvals):.4f}). The stat is "
                      f"{sum(cvals) / len(cvals):.2f}.")
            elif cvals:
                print(f"    {'':7}   -> TARGET-DEPENDENT: still "
                      f"{min(cvals):.2f}-{max(cvals):.2f} "
                      f"(x{max(cvals) / min(cvals):.2f}) after correcting for "
                      f"return fire, so the target is doing the work.")
            else:
                print(f"    {'':7}   -> TARGET-DEPENDENT (no corrected figures "
                      f"available to test return fire against).")
        else:
            print(f"    {x:7} flat at {lo:.2f}-{hi:.2f} across all "
                  f"{len(vals)} targets — damage is a property of the "
                  f"attacker, not the pairing.")
    any_zero = any(v == 0 for row in usable.values() for v in row.values())
    if any_zero:
        print("\n  A hard zero is worth pinning down before reporting it: a "
              "class rule (zero against ALL armour) and a bug (zero against "
              "one unit while its neighbours take damage) look identical in a "
              "single cell and different across a row. The row is above.")


def exp_air_vs_ground(p: Probe) -> None:
    """The standing question: does a Bomber deal 25.0 to infantry and 0.0 to
    heavy tanks?

    unit_stats measured 'tac' against 'tac' and got 3.0, so if the 25.0 in the
    original notes is real then air damage depends on the target by a factor of
    eight, and the whole air column of that table describes same-class combat
    only. One request per pairing settles it.
    """
    exp_matchups(p, roster(p, "air"), roster(p, "land"), "air_vs_ground",
                 atk_terrain="air", def_terrain="land")


def exp_land_matrix(p: Probe) -> None:
    """The same question for land-on-land, where unit_stats has the diagonal.

    Every diagonal cell here should reproduce the 'atk' column of
    MEASURED_UNITS. Any that does not is either a change on the site or a bug
    in this rig, and it is cheaper to learn that here than to discover it after
    fitting a law to the off-diagonal cells.
    """
    units = roster(p, "land")
    exp_matchups(p, units, units, "land_matrix",
                 atk_terrain="land", def_terrain="land")


# Defence coefficients, keyed for the mixed-stack predictions below.
DEF_COEF = {code: v[2] for code, v in MEASURED_UNITS.items()}


ROSTER_ORDER = sum(UNIT_CLASSES.values(), [])


def predict_stack(rows: list[tuple[str, int]], model: str,
                  coef: dict[str, float] | None = None,
                  order_by: dict[str, float] | None = None) -> float:
    """Predicted output of a composite stack under each candidate law.

    per_type    every row saturates on its own count       sum E(c_i)
    shared      one saturation for the stack, split by count share
    cumulative  the stack saturates as a whole and rows draw from it in the
                order the ROSTER lists them -- not the order they were
                submitted. Submitting art before inf returns the inf-first
                answer, so the server sorts before it computes.
    desc_coef   the same shared pool, but drawn STRONGEST FIRST: rows are
                ordered by the damage coefficient in use, descending, so the
                weakest type in a stack is the one squeezed into the saturated
                tail.

    cumulative and desc_coef are the same function whenever the roster happens
    to list a stack's types in descending order of strength, which is exactly
    what every mixed_stacks layout did -- all of them were inf + art, and
    infantry both precedes artillery in the roster and out-damages it. The
    nine-row ladder is the first stack that separates them, and it separates
    them by 52%.
    """
    coef = DEF_COEF if coef is None else coef
    # Which column SORTS the rows is a separate question from which column
    # scores them. An attacking stack is scored by the attack coefficients
    # whatever orders it, so conflating the two turns "ordered by defence"
    # into a prediction no hypothesis actually makes.
    order_by = coef if order_by is None else order_by
    total = sum(c for _, c in rows) or 1
    if model == "per_type":
        return sum(coef.get(u, 0.0) * effective_units(c) for u, c in rows)
    if model == "shared":
        return sum(coef.get(u, 0.0) * effective_units(total) * (c / total)
                   for u, c in rows)
    if model == "desc_coef":
        ordered = sorted(rows, key=lambda r: -order_by.get(r[0], 0.0))
    else:
        ordered = sorted(rows, key=lambda r: (ROSTER_ORDER.index(r[0])
                                              if r[0] in ROSTER_ORDER else 99))
    out, seen = 0.0, 0
    for u, c in ordered:
        out += coef.get(u, 0.0) * (effective_units(seen + c)
                                   - effective_units(seen))
        seen += c
    return out


STACK_LAWS = ("per_type", "shared", "cumulative", "desc_coef")


PATROL_TARGETS = ["inf", "ac", "ht"]
PATROL_ROUNDS = ["0.25", "0.5", "0.75", "1"]


def recorded_air_cells() -> dict[tuple[str, str], dict[str, float]]:
    """The air_vs_ground cells already on disk, keyed by (attacker, target).

    patrol is only interesting relative to a direct air attack, and 30 such
    cells were already bought at 1.5s apiece. Reading them back makes the
    comparison free instead of doubling the sweep.
    """
    out: dict[tuple[str, str], dict[str, float]] = {}
    try:
        with open(RESULTS_PATH) as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("experiment") != "air_vs_ground":
                    continue
                m = row.get("meta") or {}
                det = (m.get("detail") or {})
                a, b = det.get("A.1.1") or {}, det.get("B.1.1") or {}
                if not a.get("pool") or b.get("lost") is None:
                    continue
                out[(m.get("atk"), m.get("target"))] = {
                    "atk_lost": a["lost"], "atk_pool": a["pool"],
                    "def_lost": b["lost"], "def_n": m.get("def_n") or 0,
                }
    except OSError:
        pass
    return out


def _corrected_per_unit(a: dict[str, float], b: dict[str, float],
                        atk_n: int) -> float | None:
    """Attacker damage per unit, corrected for return fire (HANDOVER section 4)."""
    if b.get("lost") is None or a.get("pct") is None:
        return None
    f = a["pct"] / 100.0
    if f >= 0.999:
        return None
    return b["lost"] / effective_units(atk_n) / (1.0 - f)


def exp_patrol(p: Probe) -> None:
    """Is patrol a different attack, or just air with a different label?

    NEVER RUN LIVE as of the 2026-08-17 session: all 30 air readings in
    results.jsonl were flown with terrain=air, and `patrol` had not been
    submitted once in 150 requests. Every air number in the model therefore
    describes a direct attack only, and patrol is how these units are actually
    flown in-game.

    The previous version of this experiment sent ONE plane at twenty defenders
    against a single target and recorded bare numbers. That is the design the
    handover retired damage_air for: one attacker makes the reading fragile,
    one target cannot see a target rule, and it predates the return-fire
    correction entirely, so its numbers would have been attenuated by an
    unknown amount and read as patrol being weaker than air.

    Three questions, each with a discriminator:

    1. DOES PATROL DIFFER FROM AIR? Same counts and targets as air_vs_ground,
       terrain swapped. The air half is read back off disk rather than re-flown,
       so this costs 9 requests instead of 18. Compared on the RETURN-FIRE
       CORRECTED per-unit figure, because raw output moves with how hard the
       target shoots back and the two terrains may take different fire.

    2. IS IT REALLY 4 TICKS OF QUARTER DAMAGE? maxRounds accepts 0.25, so a
       single tick can be isolated. Two hypotheses that a full round cannot
       separate:
           4 independent ticks     ->  damage(1.0) == 4 * damage(0.25)
           4 ticks with attrition  ->  damage(1.0) <  4 * damage(0.25)
       The same ladder is flown in `air` terrain as the control, because
       nobody has checked whether a direct attack subdivides too. Without that
       control a sublinear patrol ladder says nothing about patrol.

    3. IS THE BALLOON FLYABLE IN PATROL? `bal` is the one unit in the roster
       with no measured stats at all, because guard_payload refuses it in air
       terrain, where it aborts the whole submission server-side. The guard
       has never covered patrol, and nobody has tried it. If it flies, the
       roster hole closes; if it aborts the same way, the guard should be
       widened to cover patrol and the trap recorded.
    """
    air = roster(p, "air")
    fliers = [u for u in air if u != "bal"]
    if not fliers:
        print("  ! no air units on the form.", file=sys.stderr)
        return
    prior = recorded_air_cells()
    if not prior:
        print("  ! no air_vs_ground cells on disk to compare against; patrol "
              "will be measured but not contrasted.", file=sys.stderr)

    def fly(unit: str, target: str, terrain: str, rounds: str,
            atk_n: int = 10) -> dict[str, Any] | None:
        def_n = defender_count(target, atk_n)
        ov = settings(rounds)
        ov.update(duel(1, unit, atk_n, target, def_n,
                       atk_terrain=terrain, def_terrain="land"))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  ! {unit} {terrain} vs {target} @{rounds}: {e}",
                  file=sys.stderr)
            record("patrol", {"unit": unit, "target": target,
                              "terrain": terrain, "rounds": rounds,
                              "error": str(e)}, {})
            return None
        d = dict(p.last_details)
        a, b = d.get("A.1.1") or {}, d.get("B.1.1") or {}
        per = _corrected_per_unit(a, b, atk_n)
        record("patrol", {"unit": unit, "target": target, "terrain": terrain,
                          "rounds": rounds, "atk_n": atk_n, "def_n": def_n,
                          "per_unit_corrected": per, "detail": d,
                          "summary": dict(p.last_summary),
                          "raw": dict(p.last_raw)}, {"A.1.1": a.get("lost"),
                                                     "B.1.1": b.get("lost")})
        return {"a": a, "b": b, "per": per, "def_n": def_n}

    # ---- 1. patrol vs the recorded air cells -----------------------------
    print("\n  1. patrol against the same cells air_vs_ground already flew\n")
    print(f"  {'unit':6} {'target':7} {'patrol raw':>11} {'air raw':>9} "
          f"{'base stat':>10} {'patrol f':>9} {'implied c':>10}")
    coeffs: list[float] = []
    fracs: list[float] = []
    bases: dict[str, list[float]] = {}
    for unit in fliers:
        for target in PATROL_TARGETS:
            got = fly(unit, target, "patrol", "1")
            if not got:
                continue
            a, b = got["a"], got["b"]
            if b.get("lost") is None or a.get("pct") is None:
                continue
            praw = b["lost"] / effective_units(10)
            pf = a["pct"] / 100.0
            ref = prior.get((unit, target))
            # The base stat comes from the AIR cell, where the attrition
            # coefficient is 1.0 by construction. Patrol's coefficient is then
            # whatever makes its own reading consistent with that same stat —
            # which is the whole question, and it is not a free parameter.
            base = None
            araw = None
            if ref and ref["atk_pool"]:
                af = ref["atk_lost"] / ref["atk_pool"]
                araw = ref["def_lost"] / effective_units(10)
                if af < 0.999:
                    base = araw / (1.0 - af)
            if base and pf > 1e-6:
                c = (1.0 - praw / base) / pf
                coeffs.append(c)
                fracs.append(pf)
                bases.setdefault(unit, []).append(base)
                print(f"  {unit:6} {target:7} {praw:11.3f} {araw:9.3f} "
                      f"{base:10.3f} {pf:9.4f} {c:10.4f}")
            else:
                print(f"  {unit:6} {target:7} {praw:11.3f} "
                      f"{'—':>9} {'—':>10} {pf:9.4f} {'—':>10}"
                      f"  no air cell on disk")

    # Does the attacker's stat survive the crossing at all? If the base stat
    # recovered from the air cells is not consistent per attacker, no
    # attrition story can rescue patrol and it genuinely needs its own matrix.
    base_spread = None
    if bases:
        spreads = [max(v) / min(v) - 1 for v in bases.values() if min(v) > 0]
        base_spread = max(spreads) if spreads else None

    if coeffs:
        # A cell only constrains c to about (reading error)/f, so a target that
        # barely shoots back says almost nothing: at f = 0.01 a 0.1% wobble in
        # either reading moves c by 0.1. Weighting those equally with the cells
        # that do constrain it would manufacture a spread out of arithmetic.
        strong = [c for c, f in zip(coeffs, fracs) if f >= 0.05]
        pool = strong or coeffs
        lo, hi = min(pool), max(pool)
        mean = sum(pool) / len(pool)
        weak = len(coeffs) - len(strong)
        print(f"\n  Attrition coefficient c, where a stack's output is")
        print(f"  base * E(n) * (1 - c * its_own_fraction_lost):")
        print(f"    air     c = 1.000 by construction — that is how the base "
              f"stat above was fitted")
        print(f"    patrol  c = {mean:.3f}   ({lo:.3f}-{hi:.3f} over "
              f"{len(pool)} cells)")
        if weak:
            print(f"    ({weak} cell(s) with f < 0.05 excluded: a target that "
                  f"barely fires back cannot pin c.)")

        bases_ok = base_spread is not None and base_spread <= 0.02
        # An attrition coefficient outside roughly [0, 1] is not an attrition
        # coefficient. c < 0 means patrol delivered MORE than the stat allows
        # before any losses, and c > 1 means it lost more output than it lost
        # stack. Either way the difference is in the stat, not the delivery,
        # and no amount of curve-fitting on c can represent it.
        impossible = [c for c in coeffs if c < -0.05 or c > 1.5]
        if impossible:
            print(f"\n  VERDICT: {len(impossible)} of {len(coeffs)} cells imply "
                  f"an impossible attrition coefficient "
                  f"({min(impossible):.2f}..{max(impossible):.2f}); output "
                  f"outside [0, 1] is not attrition. Patrol is changing the "
                  f"STAT, not the delivery, and the change depends on the "
                  f"target. It needs its own matrix — the table above is the "
                  f"finding, do not compress it.")
        elif not bases_ok:
            print(f"\n  VERDICT: the base stat itself does not survive the "
                  f"crossing (spread {base_spread:.3f}). Patrol is not the "
                  f"same attack seen through different attrition; it needs "
                  f"its own matrix.")
        elif hi - lo <= 0.05 and abs(mean - 1.0) > 0.1:
            print(f"\n  VERDICT: SAME BASE STAT, DIFFERENT DELIVERY. Every "
                  f"attacker's air-to-ground stat comes back unchanged; what "
                  f"changes is how much of its own attrition is charged "
                  f"against its output — the full fraction in a direct strike, "
                  f"about {mean:.2f} of it on patrol. So patrol out-damages a "
                  f"direct attack by more the harder the target shoots back, "
                  f"and by nothing at all against one that cannot. The air "
                  f"column DOES carry over, with this coefficient.")
        elif abs(mean - 1.0) > 0.1:
            print(f"\n  VERDICT: SAME BASE STAT, LIGHTER ATTRITION, "
                  f"COEFFICIENT NOT PINNED. Every attacker's stat comes back "
                  f"unchanged, and patrol clearly charges far less attrition "
                  f"than a direct strike ({lo:.3f}-{hi:.3f} against 1.000). "
                  f"But one constant does not fit all cells, and the residual "
                  f"does not track f, so the delivery is probably discrete "
                  f"(ticks, or whole units dying) rather than a smooth "
                  f"fraction. Use the range, not the mean, and do not quote a "
                  f"third decimal.")
        else:
            print(f"\n  VERDICT: patrol is indistinguishable from air; the "
                  f"same attrition coefficient describes both.")
    else:
        print("\n  NO VERDICT on patrol vs air — no comparable cell produced "
              "both readings.")

    # ---- 2. the tick ladder, with air as the control ---------------------
    #
    # The obvious discriminator — is a full round four times a quarter round? —
    # DOES NOT WORK, and the offline suite caught it before it cost a request.
    # Return fire scales with the round count too, so over a full round the
    # attacker eats four times the ground fire and delivers its attack with a
    # smaller surviving fraction. A server with perfectly independent ticks
    # still reads 3.95x on raw HP lost, and reading that as "the stack is worn
    # down between ticks" would have been a confident wrong answer of exactly
    # the shape this project keeps producing.
    #
    # Correcting each rung for the attacker's own losses removes that, and the
    # question becomes clean: corrected damage PER ROUND is flat if the ticks
    # are independent, and falls with the round count if they are not.
    probe_unit = "tac" if "tac" in fliers else fliers[0]
    print(f"\n  2. does a round subdivide? {probe_unit} vs inf, maxRounds ladder")
    print("     (corrected per unit PER ROUND — flat means independent ticks)\n")
    print(f"  {'terrain':8} " + " ".join(f"{r:>9}" for r in PATROL_ROUNDS)
          + "   spread")
    for terrain in ("patrol", "air"):
        rate: dict[str, float] = {}
        for rounds in PATROL_ROUNDS:
            got = fly(probe_unit, "inf", terrain, rounds)
            if got and got["per"] is not None:
                rate[rounds] = got["per"] / float(rounds)
        cells = " ".join(f"{rate[r]:9.3f}" if r in rate else f"{'—':>9}"
                         for r in PATROL_ROUNDS)
        vals = list(rate.values())
        if len(vals) < 2:
            print(f"  {terrain:8} {cells}   —")
            print(f"    -> {terrain}: too few rungs to rule.")
            continue
        lo, hi = min(vals), max(vals)
        print(f"  {terrain:8} {cells}   x{hi / lo:.4f}")
        if hi / lo - 1 <= 0.02:
            print(f"    -> {terrain}: flat at {sum(vals) / len(vals):.3f} per "
                  f"unit per round. Damage is PROPORTIONAL TO maxRounds — the "
                  f"stack keeps firing for as long as it is on station.")
            continue
        # A falling rate has two very different causes and they must not be
        # merged. If the corrected damage itself is CONSTANT, maxRounds is
        # simply being ignored and the rate falls as 1/rounds arithmetic.
        # Only if damage grows but sublinearly is anything being worn down.
        per_vals = [rate[r] * float(r) for r in PATROL_ROUNDS if r in rate]
        plo, phi = min(per_vals), max(per_vals)
        if phi / plo - 1 <= 0.02:
            print(f"    -> {terrain}: the damage itself is CONSTANT at "
                  f"{sum(per_vals) / len(per_vals):.3f} per unit at every "
                  f"maxRounds. maxRounds IS IGNORED — this is a single strike, "
                  f"not a duration. The falling rate above is just dividing a "
                  f"constant by a growing number, and reading it as attrition "
                  f"would be wrong.")
        elif rate.get(PATROL_ROUNDS[-1], 0) < rate.get(PATROL_ROUNDS[0], 0):
            print(f"    -> {terrain}: damage grows with maxRounds but "
                  f"SUBLINEARLY (rate x{hi / lo:.4f} down), so the stack is "
                  f"worn down between ticks, over and above the return fire "
                  f"already corrected for.")
        else:
            print(f"    -> {terrain}: the rate RISES with round length "
                  f"(x{hi / lo:.4f}) — unexplained; the row above is the "
                  f"finding, do not compress it.")

    # ---- 3. the balloon, in the one terrain nobody has tried -------------
    if "bal" in air:
        print("\n  3. bal in patrol — the roster's only unmeasured unit\n")
        got = fly("bal", "inf", "patrol", "1")
        if got and got["per"] is not None:
            print(f"    bal FLIES IN PATROL: {got['per']:.3f} per unit against "
                  f"infantry, return-fire corrected. The roster hole closes; "
                  f"guard_payload only ever needed to block bal+air.")
        else:
            print("    bal is refused or unreadable in patrol too. Widen "
                  "guard_payload to cover patrol and record the trap.")


def exp_fortress(p: Probe) -> None:
    """Fortress mitigation, written to the building row the server reads.

    The previous sweep wrote to B.1.bldg.0.*, and bldg.0 is a hidden TEMPLATE,
    not a building. The markup is <div hidden id=B.1.bldg.0>; bytro.js
    addBuilding() starts at newId = 1, clones bldg.0, and calls
    removeAttribute("hidden") on the clone, while renumberBuildings() only ever
    walks 1..maxBuildings. Real buildings are bldg.1..N.

    Three consequences followed from that single index, and each hid the next:
      * A browser submits the hidden template on EVERY request, so the server
        must discard index 0 — otherwise every battle on the site would come
        with a free level-1 fortress.
      * Being on the form, the template is already in p.baseline carrying
        abb=fortress, lvl=1, hp=100%. So the "control, no fortress" run was
        not a control, and the level-1 run set those same three values again,
        making it byte-identical to the control.
      * The guard meant to catch all this asked whether bldg.0 was MISSING
        from the baseline. It never is. The tripwire could not fire.

    Every level therefore read as a ratio of 1.0 against a contaminated
    control — the "fortresses do nothing" entry in STILL OPEN above. That was
    the rig, exactly as suspected, and not the calculator.

    bldg.0 is left exactly as the form supplies it: a real browser sends it
    too, and it appears identically in control and treatment, so it cancels.
    """
    row = 1                        # real buildings start here; 0 is a template
    abb = f"B.1.bldg.{row}.abb"    # buildings protect the DEFENDER
    lvl = f"B.1.bldg.{row}.lvl"
    hp = f"B.1.bldg.{row}.hp"
    # bldg.1 exists only once the page's own JS has cloned the template, so a
    # scripted GET never sees it. submit() drops unknown keys unless told to
    # create them — which is precisely what addBuilding() does in the browser.
    new_row = (abb, lvl, hp)

    # Control: the same battle with no building row at all. Every level reads
    # as a ratio against this, so no absolute number has to be trusted.
    base = settings()
    base.update(duel(1, "inf", 30, "inf", 30))
    try:
        control = p.submit(base)
    except BareFormReturned as e:
        print(f"  ! control: {e}", file=sys.stderr)
        return
    # The raw span TEXT goes into the record, not just the number pulled out of
    # it. The attacker's reading under a fortress has been -8.5 at every level,
    # and a bare number in results.jsonl cannot distinguish a genuinely signed
    # loss from the leading digits of some phrase we have never seen. Whichever
    # it is, the answer is in the text, so the text is what gets stored.
    record("fortress", {"level": 0, "note": "control, no bldg row",
                        "raw": dict(p.last_raw),
                        "detail": dict(p.last_details)}, control)
    ref = control.get("B.1.1")
    print(f"  control (no fortress): defender lost {ref}")
    for slot, text in sorted(p.last_raw.items()):
        print(f"      {slot}: {text!r}")

    # Both stacks at the same position so the defender inherits its own
    # fortress, and 30 a side so one round cannot wipe either — a wipe
    # saturates the reading and hides mitigation completely.
    #
    # Readings are HP LOST, so mitigation shows up as a ratio BELOW 1.0.
    for level in (1, 2, 3, 4, 5):
        ov = dict(settings(), **{abb: "fortress", lvl: str(level), hp: "100%"})
        ov.update(duel(1, "inf", 30, "inf", 30))
        try:
            r = p.submit(ov, create=new_row)
        except BareFormReturned as e:
            print(f"  ! fort L{level}: {e}", file=sys.stderr)
            continue
        record("fortress", {"level": level, "hp": "100%", "row": row,
                            "raw": dict(p.last_raw),
                            "detail": dict(p.last_details)}, r)
        got = r.get("B.1.1")
        ratio = (got / ref) if (ref and got is not None) else None
        print(f"  fortress L{level}: defender lost {got}"
              + (f"   ratio {ratio:.4f}" if ratio is not None else "")
              + ("  <- mitigation" if ratio is not None and ratio < 0.999 else ""))
        for slot, text in sorted(p.last_raw.items()):
            print(f"      {slot}: {text!r}")


# Every level 1-5, then a spread up to the form's maximum. The low levels are
# where the previous "no measurable benefit" claim was made, so they are swept
# individually rather than sampled.
TRENCH_LEVELS = (1, 2, 3, 4, 5, 10, 15, 20)

# Relative movement that counts as real. Readings are now two decimals on HP
# and three significant figures on the percentage, so the derived pool carries
# roughly 0.3% of noise; these sit well outside that and well inside any
# mechanic worth having.
MOVED_LOST = 0.01
MOVED_POOL = 0.02


def exp_trenches(p: Probe) -> None:
    """Re-run trenches, and this time distinguish HOW they work.

    The standing claim — "trenches add to the defender's HP pool rather than
    reducing damage, and levels 1-3 conferred no benefit at all" — predates the
    HP-lost discovery and all three parser bugs, and it has precisely the shape
    of the fortress null result, which was the rig every time. It is re-run
    here rather than cited.

    THE DISCRIMINATOR. Every span yields two independent numbers, HP lost and
    that loss as a percentage of the stack's full pool, so pool = lost / pct
    comes free with each reading. The two hypotheses move different ones:

        trench enlarges the defender's POOL   ->  lost flat,  pool grows
        trench reduces incoming DAMAGE        ->  lost falls, pool flat
        trench does nothing                   ->  both flat

    A sweep that watched only HP lost — which is all the old rig could read —
    cannot tell the first case from the third. That is very likely how "no
    measurable benefit" was arrived at, and it is why this reports both columns
    and refuses a one-word verdict when they disagree.

    Two further readings come along for free:

      * A.1.1 says whether a trench also blunts the defender's OUTPUT. The
        fortress does not, and that was worth knowing.
      * Any result row the trench renders for itself. The fortress mechanic was
        ultimately read off the page rather than fitted, from a row nobody had
        looked at, so every raw span is compared against the control's and new
        ones are called out.
    """
    field = "B.1.trench"
    if field not in p.baseline:
        print(f"  ! {field} is not on the form — submit() would drop it "
              f"silently and every level would read as the control. Stopping.",
              file=sys.stderr)
        return
    offered = [int(v) for v in p.select_options.get(field, []) if v.isdigit()]
    levels = [l for l in TRENCH_LEVELS if not offered or l in offered]
    skipped = [l for l in TRENCH_LEVELS if l not in levels]
    if skipped:
        print(f"  ! the form does not offer trench levels {skipped}; skipping "
              f"them. Offered: {offered}", file=sys.stderr)

    def one(label: str, **kw: Any) -> dict[str, Any] | None:
        ov = settings()
        ov.update(duel(1, "inf", 10, "inf", 10, **kw))
        try:
            r = p.submit(ov)
        except BareFormReturned as e:
            print(f"  ! {label}: {e}", file=sys.stderr)
            return None
        d = dict(p.last_details)
        record("trenches", {"label": label, **kw, "raw": dict(p.last_raw),
                            "detail": d, "summary": dict(p.last_summary)}, r)
        return {"readings": r, "detail": d, "raw": dict(p.last_raw)}

    control = one("control, trench 0")
    if not control or "B.1.1" not in control["detail"]:
        print("  NO VERDICT — the control produced no defender reading.")
        return
    c = control["detail"]["B.1.1"]
    lost0, pool0 = c.get("lost"), c.get("pool")
    atk0 = (control["detail"].get("A.1.1") or {}).get("lost")
    if not lost0 or not pool0:
        print("  NO VERDICT — the control reading carries no HP/percentage "
              "pair, so pool cannot be derived and the two hypotheses cannot "
              "be separated.")
        return
    print(f"\n  control: defender lost {lost0} of a {pool0} HP pool"
          + (f"; attacker lost {atk0}" if atk0 else "") + "\n")
    print(f"  {'trench':>6} {'defLost':>9} {'lost/ctl':>9} {'pool':>9} "
          f"{'pool/ctl':>9} {'atkLost':>9}  new rows")

    rows: list[dict[str, Any]] = []
    for level in levels:
        got = one(f"defender trench {level}", trench=level)
        if not got:
            continue
        d = got["detail"].get("B.1.1") or {}
        lost, pool = d.get("lost"), d.get("pool")
        if lost is None or pool is None:
            print(f"  {level:>6}  reading incomplete — excluded from the verdict")
            continue
        atk = (got["detail"].get("A.1.1") or {}).get("lost")
        fresh = sorted(set(got["raw"]) - set(control["raw"]))
        rows.append({"level": level, "lost": lost, "pool": pool, "atk": atk,
                     "lost_ratio": lost / lost0, "pool_ratio": pool / pool0})
        print(f"  {level:>6} {lost:>9.2f} {lost / lost0:>9.4f} {pool:>9.1f} "
              f"{pool / pool0:>9.4f} "
              + (f"{atk:>9.2f}" if atk is not None else f"{'?':>9}")
              + f"  {', '.join(fresh) if fresh else '—'}")
        for slot in fresh:
            print(f"           {slot}: {got['raw'][slot]!r}")

    if not rows:
        print("\n  NO VERDICT — no trench level produced a usable reading. "
              "Nothing is concluded; this is a defect report against the "
              "probe until the readings come back.")
        return
    if len(rows) < len(levels):
        print(f"\n  ! {len(levels) - len(rows)} of {len(levels)} levels are "
              f"missing from the verdict below.")

    lost_moves = any(abs(r["lost_ratio"] - 1) > MOVED_LOST for r in rows)
    pool_moves = any(abs(r["pool_ratio"] - 1) > MOVED_POOL for r in rows)
    if lost_moves and not pool_moves:
        print("\n  VERDICT: trenches REDUCE INCOMING DAMAGE. HP lost falls "
              "while the pool holds, exactly as the fortress behaves.")
        for r in rows:
            print(f"    L{r['level']:<3} damage x{r['lost_ratio']:.4f}  "
                  f"(DR {100 * (1 - r['lost_ratio']):.1f}%)")
    elif pool_moves and not lost_moves:
        print("\n  VERDICT: trenches ENLARGE THE DEFENDER'S POOL. Absolute HP "
              "lost is unchanged; only its share of a bigger pool falls. The "
              "old note said this — and now it rests on a measurement.")
        for r in rows:
            print(f"    L{r['level']:<3} pool x{r['pool_ratio']:.4f}")
    elif lost_moves and pool_moves:
        print("\n  VERDICT: NEITHER hypothesis alone. Both HP lost and the "
              "derived pool moved, so a trench is doing more than one thing "
              "(or the pool is not what the percentage divides by). Both "
              "columns above are the finding; do not compress them into one "
              "coefficient.")
    else:
        print("\n  VERDICT: trenches appear INERT at every level swept — "
              "neither the damage nor the pool moved.")
        print("  Before recording that as a fact about the game, note that "
              "every 'the calculator does nothing' result in this project so "
              "far has been a bug in the rig: bldg.0 was a template, a "
              "building row was clobbering the attacker's slot, and a nested "
              "</span> was truncating the answer. Check that B.1.trench "
              "actually differs between the payloads above before believing "
              "this one.")

    if atk0:
        atk_rows = [r for r in rows if r["atk"] is not None]
        if atk_rows and all(abs(r["atk"] / atk0 - 1) <= MOVED_LOST
                            for r in atk_rows):
            print("\n  The defender's OUTPUT is unaffected: the attacker's "
                  "loss is unchanged at every level, as with fortresses.")
        elif atk_rows:
            print("\n  Note: the attacker's loss MOVED with the defender's "
                  "trench, so a trench changes the defender's output too — "
                  "unlike a fortress.")

    # Does a trench help the side that is attacking? The fortress protects the
    # defender only, and one request settles whether this is the same.
    #
    # This must apply the SAME discriminator as the sweep above. Reading only
    # absolute HP lost is exactly the blunt test that turned "enlarges the pool"
    # into "no measurable benefit" for the defender, and the first live run of
    # this experiment repeated the mistake here: the attacker lost 50.0 with and
    # without a trench, so it printed "no effect while attacking" — while the
    # percentage moved 25% -> 18.5%, the same x1.35 pool growth the defender
    # gets, and the attacker's deaths fell from 2 to 1.
    if levels:
        top = levels[-1]
        got = one(f"attacker trench {top}, defender 0", atk_trench=top)
        if got:
            a_det = got["detail"].get("A.1.1") or {}
            a, a_pool = a_det.get("lost"), a_det.get("pool")
            atk_pool0 = (control["detail"].get("A.1.1") or {}).get("pool")
            b_det = got["detail"].get("B.1.1") or {}
            print(f"\n  attacker trench L{top}:")
            if a is not None and atk0:
                print(f"    attacker HP lost  {a:.2f} vs {atk0:.2f} control"
                      f"  (x{a / atk0:.4f})")
            if a_pool is not None and atk_pool0:
                ratio = a_pool / atk_pool0
                print(f"    attacker pool     {a_pool:.1f} vs {atk_pool0:.1f}"
                      f" control  (x{ratio:.4f})")
                if abs(ratio - 1) > MOVED_POOL:
                    print("    -> the HP bonus applies while ATTACKING too: "
                          "the pool grew even though absolute HP lost did not. "
                          "Judging this on HP lost alone would have reported "
                          "'no effect'.")
                else:
                    print("    -> no pool growth while attacking; the HP bonus "
                          "is defence-only.")
            # The defender's loss here is the ATTACKER's output, so this says
            # whether a trench boosts damage when its owner is attacking.
            if b_det.get("lost") is not None and lost0:
                r = b_det["lost"] / lost0
                print(f"    attacker OUTPUT   defender lost "
                      f"{b_det['lost']:.2f} vs {lost0:.2f} control"
                      f"  (x{r:.4f})")
                print("    -> " + ("output bonus applies while attacking."
                                   if abs(r - 1) > MOVED_LOST else
                                   "no output bonus while attacking — the "
                                   "damage half of the trench is defence-only."))


def exp_buildings(p: Probe) -> None:
    """All eight building types — one request each, no curve-fitting.

    The building's own result row prints its Damage Reduction outright:

        "-8.5 HP (3.4%) → LVL:5 41.5 HP; DR: 90% → 87.5%"

    so a single submission per type reads off level, HP pool and DR. The
    fortress sweep needed six requests and a fitted line to learn less than
    this does in one, because it was reading a truncated span.

    Answers the open question of whether the other seven types are combat
    relevant at all, or purely cosmetic in the calculator: a type that confers
    no mitigation should report DR 0%, or render no building row at all.
    """
    types = p.select_options.get("B.1.bldg.0.abb") or []
    if not types:
        print("  ! no building types on the form.", file=sys.stderr)
        return
    labels = p.option_labels.get("B.1.bldg.0.abb", {})
    abb, lvl, hp = "B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp"
    new_row = (abb, lvl, hp)

    base = settings()
    base.update(duel(1, "inf", 30, "inf", 30))
    try:
        control = p.submit(base)
    except BareFormReturned as e:
        print(f"  ! control: {e}", file=sys.stderr)
        return
    ref = control.get("B.1.1")
    record("buildings", {"type": None, "note": "control, no bldg row"}, control)
    print(f"  control (no building): defender lost {ref}\n")
    print(f"  {'type':12} {'defLost':>8} {'ratio':>7} {'DR%':>7} {'lvl':>4} "
          f"{'topHP':>7}  row rendered?")

    for t in types:
        level = 3
        r = None
        for attempt in range(2):
            ov = dict(settings(), **{abb: t, lvl: str(level), hp: "100%"})
            ov.update(duel(1, "inf", 30, "inf", 30))
            try:
                r = p.submit(ov, create=new_row)
                break
            except BareFormReturned as e:
                # Only the fortress reaches level 3. The server names each
                # type's cap instead of clamping, so a rejection here is the
                # sweep's own level choice, not a fact about the building.
                cap = parse_max_level(e.oops)
                if cap is not None and attempt == 0 and cap != level:
                    print(f"  . {t}: level {level} rejected, "
                          f"server caps it at {cap}; retrying", file=sys.stderr)
                    level = cap
                    continue
                print(f"  ! {t}: {e}", file=sys.stderr)
                r = None
                break
        if r is None:
            continue
        bldg = next((d for slot, d in p.last_details.items() if "bldg" in slot), {})
        got = r.get("B.1.1")
        ratio = (got / ref) if (ref and got is not None) else None
        record("buildings", {"type": t, "label": labels.get(t, t), "level": level,
                             "ratio": ratio, "bldg": bldg,
                             "raw": dict(p.last_raw)}, r)
        cell = lambda v: f"{v:7.2f}" if isinstance(v, (int, float)) else f"{'—':>7}"
        print(f"  {t:12} {cell(got)} {cell(ratio)} {cell(bldg.get('dr_before'))} "
              f"{cell(bldg.get('level'))} {cell(bldg.get('hp_top_level'))}"
              f"  {'yes' if bldg else 'NO ROW'}")


def exp_size_factor(p: Probe) -> None:
    """Re-verify E(n). Should reproduce the quadratic and the cap at 35."""
    for n in list(range(1, 26)) + [30, 35, 40, 45, 50, 60, 80, 100]:
        ov = settings()
        ov.update(duel(1, "inf", n, "inf", 100))
        try:
            record("size_factor", {"n": n}, p.submit(ov))
        except BareFormReturned as e:
            print(f"  ! n={n}: {e}", file=sys.stderr)


def exp_hp_scaling(p: Probe) -> None:
    """How a damaged stack's output scales, and whether a wiped one still hits.

    10 infantry at a swept HP percentage attack 50 defenders. The defender's
    loss is the attacker's output, so m(f) = output(f) / output(1.0).

    The attacker's OWN loss answers a second question for free, which is why
    both columns are printed. The 50 defenders deal 5.0 x E(50) = 175 every
    round, far more than a damaged 10-stack can absorb, so the attacker is
    wiped for every f up to about 0.85 and survives above it. If a stack wiped
    inside the measured round dealt less than its full damage, the low-f points
    would fall off the line that the high-f points sit on. HANDOVER section 10
    lists that as unchecked, and every coefficient this project reads from the
    opposite side of a wiped stack depends on the answer.
    """
    rows: list[tuple[float, float, float, float]] = []
    # m(f) needs the full-HP reference, which is the last row, so the ratio
    # table is printed after the sweep rather than alongside it.
    print(f"  {'hp%':>5} {'output':>9} {'atkLost':>9} "
          f"{'atkPool':>9}  attacker wiped?")
    for pct in range(10, 101, 10):
        ov = settings()
        ov.update(duel(1, "inf", 10, "inf", 50, atk_hp=f"{pct}%"))
        try:
            r = p.submit(ov)
        except BareFormReturned as e:
            print(f"  ! hp={pct}%: {e}", file=sys.stderr)
            continue
        d = dict(p.last_details)
        a, b = d.get("A.1.1", {}), d.get("B.1.1", {})
        record("hp_scaling", {"hp_pct": pct, "detail": d,
                              "summary": dict(p.last_summary)}, r)
        out, atk_lost = b.get("lost"), a.get("lost")
        if out is None:
            continue
        wiped = a.get("pct", 0) >= 99.9
        rows.append((pct / 100.0, out, atk_lost if atk_lost else 0.0,
                     1.0 if wiped else 0.0))
        cell = lambda v: f"{v:9.2f}" if isinstance(v, (int, float)) else f"{'?':>9}"
        print(f"  {pct:>5} {cell(out)} {cell(atk_lost)} "
              f"{cell(a.get('pool'))}" + ("  YES" if wiped else "  no"))

    full = next((o for f, o, _, _ in rows if abs(f - 1.0) < 1e-9), None)
    if not full or len(rows) < 3:
        print("\n  NO VERDICT — need the full-HP reference and at least three "
              "points to fit anything.")
        return
    print(f"\n  m(f) = output(f) / output(1.0), reference output {full:.2f}")
    worst, worst_f = 0.0, 0.0
    for f, o, _, _ in rows:
        m, pred = o / full, 0.05 + 0.95 * f
        err = abs(m - pred)
        if err > worst:
            worst, worst_f = err, f
        print(f"    f={f:.2f}  m={m:.4f}  0.05+0.95f={pred:.4f}  "
              f"delta {m - pred:+.4f}")
    if worst <= 0.002:
        print(f"\n  CONFIRMED: m(f) = 0.05 + 0.95*f, worst deviation "
              f"{worst:.4f} at f={worst_f:.2f}. The 0.05 floor is real — a "
              f"stack at 10% HP still deals 14.5% of full damage, not 10%.")
    else:
        print(f"\n  DOES NOT FIT: worst deviation {worst:.4f} at f={worst_f:.2f}. "
              f"The stored law m(f) = 0.05 + 0.95*f is wrong or conditional; "
              f"the table above is the finding.")

    wiped_rows = [(f, o) for f, o, _, w in rows if w]
    alive_rows = [(f, o) for f, o, _, w in rows if not w]
    if wiped_rows and alive_rows:
        off = max(abs(o / full - (0.05 + 0.95 * f)) for f, o in wiped_rows)
        if off <= 0.002:
            print(f"\n  A WIPED STACK STILL DEALS ITS FULL DAMAGE. The "
                  f"attacker was destroyed in {len(wiped_rows)} of these "
                  f"{len(rows)} rounds, and those points sit on the same line "
                  f"as the {len(alive_rows)} it survived (worst deviation "
                  f"{off:.4f}). Coefficients read from the far side of a wiped "
                  f"stack are therefore sound.")
        else:
            print(f"\n  WIPED STACKS DEAL LESS: the {len(wiped_rows)} rounds "
                  f"where the attacker died deviate by up to {off:.4f} from "
                  f"the line its surviving rounds define. Every coefficient "
                  f"read opposite a wiped stack is suspect.")
    else:
        print("\n  Cannot rule on wiped stacks: this sweep produced only "
              + ("wiped" if wiped_rows else "surviving") + " attackers.")


def composite(stack: int, side: str, rows: list[tuple[str, int]],
              hp: str = "100%") -> dict[str, str]:
    """Fill one side's unit rows with a COMPOSITE stack.

    Every experiment before this one used exactly one unit row per side, and
    duel() blanks rows 2-15 to keep it that way. That was a measurement choice
    -- one variable at a time -- and it is not how the game works. A real stack
    is a mixture, and the form has always had the rows for it.
    """
    out: dict[str, str] = {}
    for i, (unit, count) in enumerate(rows, start=1):
        out[f"{side}.{stack}.{i}.unit"] = unit
        out[f"{side}.{stack}.{i}.count"] = str(count)
        out[f"{side}.{stack}.{i}.hp"] = hp
    # Up to MAX_UNIT_ROWS, matching duel(). This stopped at 9 while duel()
    # already blanked 2..15, so a composite stack only stayed clean because
    # duel() runs first and happens to cover the tail. Any caller that built a
    # stack WITHOUT duel() would have left rows 9-15 carrying whatever the GET
    # shipped -- a contaminated reading with no error, which is the failure
    # mode this whole file is organised against.
    for i in range(len(rows) + 1, MAX_UNIT_ROWS + 1):
        out[f"{side}.{stack}.{i}.count"] = ""
        out[f"{side}.{stack}.{i}.hp"] = ""
    return out


# Rows beyond what the GET ships have to be synthesised, exactly as the page's
# own addUnit() does. B ships four; A ships one.
def composite_fields(side: str, stack: int, n_rows: int) -> tuple[str, ...]:
    out = []
    for i in range(1, n_rows + 1):
        out += [f"{side}.{stack}.{i}.unit", f"{side}.{stack}.{i}.count",
                f"{side}.{stack}.{i}.hp"]
    return tuple(out)


def exp_mixed_stacks(p: Probe) -> None:
    """Is the stack-size factor E(n) per ROW or per STACK?

    THE QUESTION THIS ANSWERS. E(n) saturates hard -- 50 units contribute 35
    effective, and past 50 nothing at all. Every measurement in this project
    put one unit type in one row, so n was simultaneously "units of this type"
    and "units in this stack" and the two could never be told apart. For a
    single-type stack it makes no difference. For a real one it decides whether

        25 infantry + 25 artillery  =  E(25) + E(25) = 49.2 effective
                              or  =  E(50)          = 35.0 effective

    a factor of 1.4, and it is the difference between "split your doomstack"
    and "do not bother". Nothing in the model predicts which.

    THE DISCRIMINATOR. Hold the total count fixed and vary only how many rows
    it is spread across. E is linear below 20, so the split has to straddle the
    knee to say anything: 50 in one row against 25+25 gives 175 against 245.8
    on the defender's output, which no reading precision can blur.

    Reading the same responses also settles two more things for free:

      * ALLOCATION. The page prints a separate span per unit row, so a mixed
        stack's incoming damage is itemised. Whether it lands proportionally
        to pool, to count, or on one row first has never been looked at.
      * WHETHER ROWS INTERACT AT ALL. If two rows of the same unit behave
        exactly like one row of the sum, rows are pure bookkeeping.
    """
    # The attacker exists only to be shot at: its loss IS the defender's output.
    # So it must be able to absorb the largest output either hypothesis
    # predicts, or the reading is capped at its pool and the discriminator
    # collapses. Per-row on 50 units predicts 5.0 x (E(25)+E(25)) = 245.8, so
    # 10 infantry (pool 200) is not enough -- the offline suite caught exactly
    # that, and it would have read as "NEITHER" on live data.
    atk_n = 20
    base = settings()
    results: dict[str, dict[str, Any]] = {}

    def fight(label: str, rows: list[tuple[str, int]], **kw: Any) -> dict | None:
        ov = dict(base)
        ov.update(duel(1, "inf", atk_n, rows[0][0], rows[0][1], **kw))
        ov.update(composite(1, "B", rows))
        try:
            p.submit(ov, create=composite_fields("B", 1, len(rows)))
        except (BareFormReturned, ValueError) as e:
            print(f"  ! {label}: {e}", file=sys.stderr)
            record("mixed_stacks", {"label": label, "rows": rows,
                                    "error": str(e)}, {})
            return None
        d = dict(p.last_details)
        got = {"detail": d, "rows": rows,
               "atk_lost": (d.get("A.1.1") or {}).get("lost"),
               "def_rows": {k: v for k, v in d.items() if k.startswith("B.1.")}}
        record("mixed_stacks", {"label": label, "rows": rows, "atk_n": atk_n,
                                "detail": d, "summary": dict(p.last_summary),
                                "raw": dict(p.last_raw)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        results[label] = got
        return got

    total = 50
    print(f"\n  {atk_n} infantry attack a {total}-unit defender, split various ways.")
    print("  The defender's OUTPUT (= the attacker's loss) is the discriminator.\n")
    print(f"  {'layout':32} {'atkLost':>9} {'per-type':>10} {'shared':>11} "
          f"{'cumulative':>11}")
    print("  per-type   = every row gets E(its own count), summed")
    print("  shared     = one E(total) split by each row's share of the count")
    print("  cumulative = row i gets E(units through i) - E(units before i)\n")

    # The server refuses a repeated unit type -- "The same unit can't be
    # specified twice in same stack" -- so a stack is a set of DISTINCT types
    # and the obvious control (25 inf + 25 inf against 50 inf) cannot be sent.
    # The question survives in a better form: is a mixed stack's output the sum
    # of its rows measured alone, or is it capped by the stack as a whole?
    layouts = [
        ("50 inf, one row", [("inf", 50)]),
        ("25 inf alone", [("inf", 25)]),
        ("25 art alone", [("art", 25)]),
        ("25 inf + 25 art", [("inf", 25), ("art", 25)]),
        ("25 art + 25 inf (swapped)", [("art", 25), ("inf", 25)]),
        # Asymmetric splits. With both rows at 25 every candidate that depends
        # only on the count is degenerate -- the two rows are interchangeable
        # and several different laws collapse to the same number. Moving the
        # weight breaks that tie.
        ("40 inf + 10 art", [("inf", 40), ("art", 10)]),
        ("10 inf + 40 art", [("inf", 10), ("art", 40)]),
    ]
    saturated = False
    for label, rows in layouts:
        got = fight(label, rows)
        if not got or got["atk_lost"] is None:
            continue
        a = (got["detail"].get("A.1.1") or {})
        if a.get("pct", 0) >= 99.9:
            saturated = True
            print(f"  ! {label}: the ATTACKER was wiped, so its loss is capped "
                  f"at its own pool and understates the defender's output.",
                  file=sys.stderr)
        print(f"  {label:32} {got['atk_lost']:9.2f} "
              f"{predict_stack(rows, 'per_type'):10.2f} "
              f"{predict_stack(rows, 'shared'):11.2f} "
              f"{predict_stack(rows, 'cumulative'):11.2f}")

    mixes = [(lbl, r["rows"], r["atk_lost"]) for lbl, r in results.items()
             if len(r["rows"]) > 1 and r["atk_lost"]]
    if saturated:
        print("\n  NO VERDICT — an attacker stack was wiped, so its loss was "
              "capped at its pool rather than reporting the defender's true "
              "output. A capped reading looks exactly like a smaller one.")
    elif not mixes:
        print("\n  NO VERDICT — no multi-row stack produced a reading.")
    else:
        errs = {m: max(abs(obs - predict_stack(rows, m)) / obs
                       for _, rows, obs in mixes)
                for m in ("per_type", "shared", "cumulative")}
        for m in ("per_type", "shared", "cumulative"):
            print(f"    {m:11} worst error {100 * errs[m]:6.2f}%")
        best = min(errs, key=errs.get)
        names = {
            "per_type": "PER UNIT TYPE — each row saturates on its own count, so "
                        "a mixed army beats a single-type one of the same size",
            "shared": "PER STACK, SHARED BY COUNT — one saturation for the whole "
                      "stack, split by each row's share of it",
            "cumulative": "PER STACK, CUMULATIVE IN ROSTER ORDER — the stack "
                          "saturates as a whole and each unit type draws from "
                          "what is left, in the order the roster lists them",
        }
        if errs[best] <= 0.01:
            print(f"\n  VERDICT: E(n) is {names[best]} "
                  f"(worst error {100 * errs[best]:.2f}%).")
            if best == "cumulative":
                print("  SUBMISSION ORDER DOES NOT MATTER — the swapped pair "
                      "above returns the identical figure, so the server sorts "
                      "into roster order before it computes. What DOES matter is "
                      "that a type appearing late in that order draws from the "
                      "saturated tail: 40 artillery beside 10 infantry get "
                      "E(50)-E(10) = 25 effective, against E(40) = 33.3 on their "
                      "own. Mixing costs the later type, and you cannot reorder "
                      "your way out of it.")
        else:
            print(f"\n  VERDICT: none of the candidates fits (best is {best} at "
                  f"{100 * errs[best]:.2f}%). The table above is the finding — "
                  f"do not compress it.")


    # ---- allocation: who takes the damage in a mixed stack? ---------------
    print("\n  Damage allocation inside a mixed stack\n")
    mixed = [("inf", 25), ("art", 25)]
    got = fight("25 inf + 25 art", mixed)
    if got:
        print(f"  {'row':10} {'unit':6} {'HP lost':>9} {'pool':>9} {'% of own':>9}")
        tot = 0.0
        for i, (unit, count) in enumerate(mixed, start=1):
            d = got["def_rows"].get(f"B.1.{i}") or {}
            lost, pool = d.get("lost"), d.get("pool")
            tot += lost or 0
            print(f"  B.1.{i:<6} {unit:6} "
                  + (f"{lost:9.2f}" if lost is not None else f"{'—':>9}")
                  + (f"{pool:9.1f}" if pool else f"{'—':>9}")
                  + (f"{100 * lost / pool:9.1f}" if (lost and pool) else f"{'—':>9}"))
        print(f"\n  Total taken: {tot:.2f}. An attacker of {atk_n} infantry deals "
              f"{4.0 * effective_units(atk_n):.2f} against a single-row stack.")
        print("  Equal percentages mean damage is shared in proportion to pool; "
              "equal absolute\n  figures mean it is split per row; one row at "
              "zero means rows are ordered.")


HERO_FIELDS = ("B.1.hero.abb", "B.1.hero.lvl", "B.1.hero.hp")
HERO_ATK_FIELDS = ("A.1.hero.abb", "A.1.hero.lvl", "A.1.hero.hp")


def hero_options() -> list[str]:
    """The 23 hero codes, read out of the page's own addHero() template.

    They are not on the GET form -- addHero() injects them client-side, exactly
    like a building row -- so they have to come from bytro.js rather than from
    p.select_options.
    """
    try:
        js = open("bytro.js").read()
    except OSError:
        return []
    block = js[js.find("hero.abb"):js.find("hero.lvl")]
    return re.findall(r'<option value="([^"]+)"', block)


def exp_heroes(p: Probe) -> None:
    """Do heroes do anything, and to whom?

    NEVER MEASURED. In 174 live requests not one carried a hero, so every
    coefficient in this project describes a hero-free battle. That is at least
    internally consistent -- nothing on disk is contaminated -- but heroes are
    a real mechanic and the roster is large: 23 of them, 20 levels each, one
    per stack (addHero refuses a second: "This stack already has a hero.").

    READ THE PAGE, DO NOT FIT THE NUMBERS. The fortress mechanic was solved by
    noticing the building's own result row printed "DR: 90% -> 87.5%" outright,
    after six requests of curve-fitting had learned less. A hero gets its own
    <div id="B.1.hero"> in the same position, so one request per hero should
    say what that hero does in words, whatever the numbers do.

    THE TRAP THIS DESIGN IS BUILT AROUND. The hero names are plainly
    class-specific -- Manfred von Richthofen is an air ace, Otto Hersing a
    U-boat commander, Togo Heihachiro a battleship admiral. Against a land
    stack most of them should legitimately do nothing, and "does nothing" is
    the single most dangerous reading in this project (HANDOVER section 0).
    So a null here is NOT reported as "no effect": it is reported as "no effect
    ON THIS STACK CLASS", and the hero row's raw text is captured every time so
    a silent row and an absent row can never be confused.
    """
    heroes = hero_options()
    if not heroes:
        print("  ! no hero list found in bytro.js.", file=sys.stderr)
        return
    abb, lvl, hp = HERO_FIELDS
    print(f"  {len(heroes)} heroes from the page's own addHero() template\n")

    base = settings()
    base.update(duel(1, "inf", 20, "inf", 30))
    try:
        control = p.submit(base)
    except BareFormReturned as e:
        print(f"  ! control: {e}", file=sys.stderr)
        return
    ref_def = control.get("B.1.1")
    ref_atk = control.get("A.1.1")
    record("heroes", {"hero": None, "note": "control, no hero"}, control)
    print(f"  control: defender lost {ref_def}, attacker lost {ref_atk}\n")
    print(f"  {'hero':12} {'defLost':>9} {'atkLost':>9} {'defRatio':>9} "
          f"{'atkRatio':>9}  hero row text")

    silent, effective = [], []
    for h in heroes:
        ov = dict(settings(), **{abb: h, lvl: "10", hp: "100%"})
        ov.update(duel(1, "inf", 20, "inf", 30))
        try:
            r = p.submit(ov, create=HERO_FIELDS)
        except (BareFormReturned, ValueError) as e:
            print(f"  ! {h}: {e}", file=sys.stderr)
            record("heroes", {"hero": h, "error": str(e)}, {})
            continue
        raw = dict(p.last_raw)
        row = raw.get("B.1.hero")
        d = r.get("B.1.1")
        a = r.get("A.1.1")
        dr = (d / ref_def) if (ref_def and d is not None) else None
        ar = (a / ref_atk) if (ref_atk and a is not None) else None
        moved = any(x is not None and abs(x - 1) > 0.005 for x in (dr, ar))
        (effective if moved else silent).append(h)
        record("heroes", {"hero": h, "level": 10, "def_ratio": dr,
                          "atk_ratio": ar, "hero_row": row,
                          "detail": dict(p.last_details),
                          "summary": dict(p.last_summary), "raw": raw}, r)
        cell = lambda v: f"{v:9.2f}" if isinstance(v, (int, float)) else f"{'—':>9}"
        print(f"  {h:12} {cell(d)} {cell(a)} {cell(dr)} {cell(ar)}  "
              + (repr(row) if row else "NO ROW RENDERED"))

    print(f"\n  {len(effective)} of {len(heroes)} changed a land-vs-land battle: "
          f"{', '.join(effective) if effective else 'none'}")
    if silent:
        print(f"  {len(silent)} did not: {', '.join(silent)}")
        print("  That is NOT 'these heroes do nothing'. Every reading above is "
              "an INFANTRY stack, and\n  the roster is plainly class-specific — "
              "an air ace has no business buffing infantry.\n  The hero row "
              "text column separates a hero the server ignored from one it\n  "
              "applied to units that were not there.")
    rows_seen = [h for h in heroes if h not in silent or True]
    if effective:
        print("\n  Next: sweep levels 1..20 for one effective hero, and re-run "
              "the silent ones\n  against air and naval stacks before "
              "concluding anything about them.")


def exp_stack_limits(p: Probe) -> None:
    """How many unit rows can a stack actually hold, and of which classes?

    Two numbers have been assumed all project and neither was ever checked.

    ROW COUNT. duel() blanks rows 2-15, the form's real maximum,
    and that 8 was then carried into the app as though it were the game's
    limit. The page's own constant is maxUnits = 15. But a stack cannot repeat
    a unit type (measured), so the real ceiling is the number of TYPES a stack
    may hold, which is at most 17 and may be far fewer.

    CLASS MIXING. If a land-terrain stack may only hold land units, the
    ceiling for a land army is 10, not 15 -- and an air stack is capped at 4.
    Nothing in the record says either way: every stack ever submitted held one
    class, because every stack ever submitted held one TYPE.

    Two requests settle both. A refusal here is an answer, not a null: the
    server states its constraints outright ("The same unit can't be specified
    twice in same stack", "Can't have Balloon in the air").
    """
    land = [u for u in UNIT_CLASSES["land"]
            if u in (p.select_options.get(UNIT_FIELD) or [])]
    rows_all_land = [(u, 5) for u in land]
    fields = composite_fields("B", 1, max(len(rows_all_land), 2))

    print(f"\n  the page declares maxUnits = 15; {len(land)} land types exist\n")

    # 1. Every land type at once -- more rows than duel() has ever blanked.
    ov = settings()
    ov.update(duel(1, "inf", 20, "inf", 30))
    ov.update(composite(1, "B", rows_all_land))
    try:
        r = p.submit(ov, create=fields)
        d = dict(p.last_details)
        got = sorted(k for k in d if RESULT_SLOT_RE.match(k) and k.startswith("B.1."))
        print(f"  {len(rows_all_land)} land types in one stack: ACCEPTED — "
              f"{len(got)} result rows came back")
        record("stack_limits", {"case": "all_land_types",
                                "rows": rows_all_land, "slots": got,
                                "detail": d, "raw": dict(p.last_raw)}, r)
    except (BareFormReturned, ValueError) as e:
        print(f"  {len(rows_all_land)} land types in one stack: REFUSED -> {e}")
        record("stack_limits", {"case": "all_land_types",
                                "rows": rows_all_land, "error": str(e)}, {})

    # 1b. The same, minus the convoy the server just objected to.
    no_convoy = [(u, 5) for u, _ in rows_all_land if u != "convoy"]
    ov = settings()
    ov.update(duel(1, "inf", 20, "inf", 30))
    ov.update(composite(1, "B", no_convoy))
    try:
        r = p.submit(ov, create=composite_fields("B", 1, len(no_convoy)))
        d = dict(p.last_details)
        got = sorted(k for k in d if RESULT_SLOT_RE.match(k) and k.startswith("B.1."))
        print(f"  {len(no_convoy)} land types, no convoy: ACCEPTED — "
              f"{len(got)} result rows. So a land stack holds "
              f"{len(no_convoy)}, not the 8 this project assumed.")
        record("stack_limits", {"case": "land_no_convoy", "rows": no_convoy,
                                "slots": got, "detail": d,
                                "raw": dict(p.last_raw)}, r)
    except (BareFormReturned, ValueError) as e:
        print(f"  {len(no_convoy)} land types, no convoy: REFUSED -> {e}")
        record("stack_limits", {"case": "land_no_convoy", "rows": no_convoy,
                                "error": str(e)}, {})

    # 1c. Where does the convoy belong? It is classed land but land refuses it.
    ov = settings()
    ov.update(duel(1, "inf", 20, "int", 20, def_terrain="air"))
    ov.update(composite(1, "B", [("int", 10), ("convoy", 10)]))
    try:
        p.submit(ov, create=composite_fields("B", 1, 2))
        print("  convoy beside an air unit in AIR terrain: ACCEPTED — the "
              "convoy is an air unit that our roster miscategorises as land")
        record("stack_limits", {"case": "convoy_with_air",
                                "detail": dict(p.last_details),
                                "raw": dict(p.last_raw)}, {})
    except (BareFormReturned, ValueError) as e:
        print(f"  convoy beside an air unit in AIR terrain: REFUSED -> {e}")
        print("  So the convoy stacks with nothing: it is its own class of one.")
        record("stack_limits", {"case": "convoy_with_air", "error": str(e)}, {})

    # 2. A land stack holding an air unit.
    mixed = [("inf", 10), ("int", 10)]
    ov = settings()
    ov.update(duel(1, "inf", 20, "inf", 30))
    ov.update(composite(1, "B", mixed))
    try:
        r = p.submit(ov, create=composite_fields("B", 1, 2))
        print("  land stack holding an air unit: ACCEPTED — classes may mix, "
              "so the ceiling is the type count (up to 17), not the class")
        record("stack_limits", {"case": "class_mixing", "rows": mixed,
                                "detail": dict(p.last_details),
                                "raw": dict(p.last_raw)}, r)
    except (BareFormReturned, ValueError) as e:
        print(f"  land stack holding an air unit: REFUSED -> {e}")
        print("  So a stack is one class, and the practical row cap is that "
              "class's type count:\n    land 10, air 4, naval 3 — all well "
              "under the page's maxUnits = 15.")
        record("stack_limits", {"case": "class_mixing", "rows": mixed,
                                "error": str(e)}, {})


HERO_SCALE_COUNTS = [10, 30, 50]
HERO_SCALE_PICKS = ["joffre_home", "kangal"]


def exp_hero_scaling(p: Probe) -> None:
    """HOW does a hero help — does it add, multiply, or just stand there?

    The first hero sweep measured every hero against ONE stack size, 30
    infantry. That answers "how much" and says nothing about "how", because at
    a single stack size an additive bonus and a multiplicative one are the
    same number: joffre_home's +56.22 IS x1.3968. This is the same blind spot
    E(n) had before mixed_stacks — one configuration cannot separate two laws
    that agree on it.

    Three candidates, and the third is the interesting one:

      MULTIPLIES   the hero scales the stack's output; the gap grows with n
      ADDS FLAT    a constant bonus regardless of stack size
      IS A UNIT    the hero contributes its own output like any other unit,
                   which means its effective count is E(n+1) - E(n) -- and
                   that is 1.0 at ten units, 0.65 at thirty, and EXACTLY ZERO
                   at fifty, because the stack has already saturated

    So the sharpest reading is at n = 50: if a hero is just another unit, it
    does literally nothing to a saturated stack, while multiplication predicts
    244 against a control of 175. Nothing subtle about that.
    """
    picks = [h for h in HERO_SCALE_PICKS if h in hero_options()]
    if not picks:
        print("  ! none of the chosen heroes are on the roster.", file=sys.stderr)
        return
    abb, lvl, hp = HERE_FIELDS if False else HERO_FIELDS
    print(f"\n  20 infantry attack N infantry, with and without a hero at lvl 10")
    print(f"  {'n':>4} {'control':>9} " + " ".join(f"{h:>13}" for h in picks))

    base_out: dict[int, float] = {}
    hero_out: dict[tuple[str, int], float] = {}
    for n in HERO_SCALE_COUNTS:
        ov = settings()
        ov.update(duel(1, "inf", 20, "inf", n))
        try:
            r = p.submit(ov)
            base_out[n] = r.get("A.1.1")
            record("hero_scaling", {"hero": None, "def_n": n,
                                    "detail": dict(p.last_details)}, r)
        except (BareFormReturned, ValueError) as e:
            print(f"  ! control n={n}: {e}", file=sys.stderr)
            continue
        cells = []
        for h in picks:
            ov = dict(settings(), **{abb: h, lvl: "10", hp: "100%"})
            ov.update(duel(1, "inf", 20, "inf", n))
            try:
                r = p.submit(ov, create=HERO_FIELDS)
                hero_out[(h, n)] = r.get("A.1.1")
                record("hero_scaling", {"hero": h, "def_n": n, "level": 10,
                                        "detail": dict(p.last_details),
                                        "raw": dict(p.last_raw)}, r)
                cells.append(f"{hero_out[(h, n)]:13.2f}")
            except (BareFormReturned, ValueError) as e:
                print(f"  ! {h} n={n}: {e}", file=sys.stderr)
                cells.append(f"{'—':>13}")
        print(f"  {n:>4} {base_out.get(n, float('nan')):9.2f} " + " ".join(cells))

    print()
    for h in picks:
        pts = [(n, base_out[n], hero_out[(h, n)]) for n in HERO_SCALE_COUNTS
               if n in base_out and (h, n) in hero_out
               and base_out[n] and hero_out[(h, n)] is not None]
        if len(pts) < 2:
            print(f"  {h}: too few readings to rule.")
            continue
        deltas = [o - c for _, c, o in pts]
        ratios = [o / c for _, c, o in pts]
        as_unit = [(E := effective_units)(n + 1) - effective_units(n)
                   for n, _, _ in pts]
        spread = lambda v: (max(v) / min(v)) if min(v) > 1e-9 else float("inf")
        print(f"  {h}:")
        for (n, c, o), d, rr in zip(pts, deltas, ratios):
            print(f"    n={n:<3} control {c:7.2f} -> {o:7.2f}   "
                  f"delta {d:+7.2f}   ratio {rr:.4f}")
        # THE LAW, fitted and then checked against a held-out point.
        # addHero() inserts the hero's div BEFORE the first unit row, so under
        # the measured roster-order saturation the hero takes E(1) = 1
        # effective and the units get E(n+1) - 1. On top of that it multiplies
        # what the units deal. Two parameters, and neither is free: solve them
        # on the outer two stack sizes and PREDICT the middle one.
        def model(a, m, n):
            return a * 1.0 + DEF_COEF["inf"] * m * (effective_units(n + 1) - 1)

        if len(pts) >= 3:
            (n0, _, o0), (n1, _, o1), (n2, _, o2) = pts[0], pts[1], pts[-1]
            u0 = DEF_COEF["inf"] * (effective_units(n0 + 1) - 1)
            u2 = DEF_COEF["inf"] * (effective_units(n2 + 1) - 1)
            if abs(u2 - u0) > 1e-9:
                mm = (o2 - o0) / (u2 - u0)
                aa = o0 - u0 * mm
                held = model(aa, mm, n1)
                err = abs(held - o1) / o1 if o1 else 1.0
                print(f"    fit on n={n0} and n={n2}: hero attack {aa:.2f}, "
                      f"unit multiplier {mm:.4f}")
                print(f"    held-out n={n1}: predicted {held:.2f} vs "
                      f"observed {o1:.2f}  ({100 * err:.3f}%)")
                if err <= 0.005:
                    print(f"    -> A HERO IS A UNIT PLUS A BUFF. It fights as one "
                          f"unit placed first in the stack (attack {aa:.1f}) AND "
                          f"multiplies what the rest of the stack deals "
                          f"(x{mm:.2f}). Neither half alone fits: a pure unit "
                          f"cannot grow the gap with stack size, and a pure "
                          f"multiplier cannot shrink it.")
                    continue
                print(f"    -> the two-part model does not close either "
                      f"({100 * err:.2f}% on the held-out point).")

        flat = spread([abs(d) for d in deltas]) <= 1.02
        flat = spread([abs(d) for d in deltas]) <= 1.02
        mult = spread(ratios) <= 1.02
        # "Is a unit" predicts the delta tracks E(n+1)-E(n), which hits zero at
        # a saturated stack. Compare shapes rather than magnitudes.
        unit_like = (as_unit[-1] < 1e-9 and abs(deltas[-1]) < 0.05)
        if unit_like:
            print(f"    -> IS JUST ANOTHER UNIT. The hero adds nothing to a "
                  f"saturated stack, exactly as E(n+1)-E(n) = 0 predicts. Its "
                  f"whole contribution is its own effective units.")
        elif mult and not flat:
            print(f"    -> MULTIPLIES the stack's output, x{sum(ratios)/len(ratios):.4f} "
                  f"(spread x{spread(ratios):.4f} across {len(pts)} stack sizes).")
        elif flat and not mult:
            print(f"    -> ADDS A FLAT {sum(deltas)/len(deltas):+.2f}, independent "
                  f"of stack size (spread x{spread([abs(d) for d in deltas]):.4f}).")
        else:
            print(f"    -> NONE OF THE THREE cleanly. deltas "
                  f"{[round(d,2) for d in deltas]}, ratios "
                  f"{[round(r,4) for r in ratios]}. The rows above are the "
                  f"finding; do not compress them.")


def fit_hero(readings: dict[int, float], unit_coef: float = 5.0
             ) -> tuple[str, float, float, float] | None:
    """Solve (position, own attack A, stack multiplier M) from three readings.

    A hero is a unit plus a buff:

        output(n) = A * heroEffective(n)  +  unit_coef * M * unitEffective(n)

    and WHERE it sits in the stack decides both effective counts, because a
    stack saturates cumulatively in roster order. Two positions are possible
    against a single-type defender:

        first  hero takes E(1) = 1,          units take E(n+1) - 1
        last   hero takes E(n+1) - E(n),     units take E(n)

    Fitting only 'first' silently mis-solved maeve: she adds exactly nothing at
    n = 50, which is the signature of a hero at the END of a saturated stack
    (E(51) - E(50) = 0), and forcing her into the 'first' shape absorbed the
    mismatch into a fake multiplier of 1.0083 that squeaked under tolerance.
    Solved in the right position she is a clean A = 4.00, M = 1.00.

    Returns the better-fitting position with its worst relative error.
    """
    ns = sorted(readings)
    if len(ns) < 3:
        return None
    shapes = {
        "first": (lambda n: 1.0, lambda n: unit_coef * (effective_units(n + 1) - 1)),
        "last": (lambda n: effective_units(n + 1) - effective_units(n),
                 lambda n: unit_coef * effective_units(n)),
    }
    best = None
    for pos, (hero_e, unit_e) in shapes.items():
        n0, n2 = ns[0], ns[-1]
        det = hero_e(n0) * unit_e(n2) - hero_e(n2) * unit_e(n0)
        if abs(det) < 1e-9:
            continue
        a = (readings[n0] * unit_e(n2) - readings[n2] * unit_e(n0)) / det
        m = (hero_e(n0) * readings[n2] - hero_e(n2) * readings[n0]) / det
        err = max(abs(a * hero_e(n) + m * unit_e(n) - readings[n]) / readings[n]
                  for n in ns if readings[n])
        if best is None or err < best[3]:
            best = (pos, a, m, err)
    return best


def _recorded_hero_readings() -> tuple[dict[int, float], dict[str, float]]:
    """Controls by stack size, and each hero's n=30 output, from results.jsonl.

    Both were already bought. The controls came from hero_scaling and the
    per-hero n=30 figures from the first heroes sweep, so decomposing the rest
    of the roster only needs the two stack sizes nobody has flown for them --
    and the n=30 reading then serves as a free HELD-OUT check on every fit.
    """
    ctl: dict[int, float] = {}
    at30: dict[str, float] = {}
    try:
        with open(RESULTS_PATH) as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                m = row.get("meta") or {}
                out = (row.get("readings") or {}).get("A.1.1")
                if out is None:
                    continue
                if row.get("experiment") == "hero_scaling" and m.get("hero") is None:
                    ctl[int(m["def_n"])] = out
                elif row.get("experiment") == "heroes" and m.get("hero"):
                    at30.setdefault(m["hero"], out)
    except OSError:
        pass
    return ctl, at30


def exp_hero_table(p: Probe) -> None:
    """Decompose A and M for every hero the first sweep left confounded.

    hero_scaling separated the two halves of the hero law for two heroes:

        output = A * 1  +  unit_coef * M * (E(n+1) - 1)

    The other fourteen have a single reading each at n = 30, where an additive
    A and a multiplicative M are indistinguishable. Two more stack sizes fix
    each one, and only two: n = 10 and n = 50 are bought here, the controls and
    the n = 30 readings are read back off disk, and n = 30 is then a held-out
    point that cost nothing.
    """
    ctl, at30 = _recorded_hero_readings()
    missing = [n for n in (10, 30, 50) if n not in ctl]
    if missing:
        print(f"  ! no control on disk for n={missing}; run hero_scaling first.",
              file=sys.stderr)
        return
    done = set(HERO_SCALE_PICKS)
    todo = [h for h in hero_options() if h in at30 and h not in done]
    if not todo:
        print("  nothing left to decompose.")
        return

    abb, lvl, hp = HERO_FIELDS
    print(f"\n  {len(todo)} heroes still confounded; buying n=10 and n=50 for "
          f"each ({2 * len(todo)} requests).")
    print(f"  Controls and n=30 come off disk, so every fit gets a free "
          f"held-out check.\n")
    print(f"  {'hero':14} {'A (own atk)':>12} {'M (stack)':>10} "
          f"{'held-out n=30':>22}")

    fitted: dict[str, tuple[float, float]] = {}
    for h in todo:
        got: dict[int, float] = {}
        for n in (10, 50):
            ov = dict(settings(), **{abb: h, lvl: "10", hp: "100%"})
            ov.update(duel(1, "inf", 20, "inf", n))
            try:
                r = p.submit(ov, create=HERO_FIELDS)
                got[n] = r.get("A.1.1")
                record("hero_table", {"hero": h, "def_n": n, "level": 10,
                                      "detail": dict(p.last_details),
                                      "raw": dict(p.last_raw)}, r)
            except (BareFormReturned, ValueError) as e:
                print(f"  ! {h} n={n}: {e}", file=sys.stderr)
                record("hero_table", {"hero": h, "def_n": n,
                                      "error": str(e)}, {})
        if got.get(10) is None or got.get(50) is None:
            print(f"  {h:14} {'—':>12} {'—':>10} {'incomplete':>22}")
            continue
        fit = fit_hero({10: got[10], 30: at30[h], 50: got[50]}, DEF_COEF["inf"])
        if not fit:
            print(f"  {h:14} {'—':>12} {'—':>10} {'unfittable':>22}")
            continue
        pos, a, m, err = fit
        # n=30 is held out of the solve (it uses the outer two), so quoting it
        # back is a real check rather than a restatement of the input.
        pred = (a * (1.0 if pos == "first" else
                     effective_units(31) - effective_units(30))
                + DEF_COEF["inf"] * m * ((effective_units(31) - 1) if pos == "first"
                                         else effective_units(30)))
        obs = at30[h]
        fitted[h] = (a, m, pos)
        flag = "OK" if err <= 0.005 else f"MISFIT {100 * err:.2f}%"
        print(f"  {h:14} {a:12.2f} {m:10.4f} "
              f"{f'{pred:.2f} vs {obs:.2f} {flag}':>22}  sits {pos}")

    if not fitted:
        print("\n  NO VERDICT — nothing was decomposed.")
        return
    pure_units = [h for h, (a, m, _) in fitted.items() if abs(m - 1) <= 0.005]
    buffers = [h for h, (a, m, _) in fitted.items() if m > 1.005]
    tail = [h for h, (_, _, pos) in fitted.items() if pos == "last"]
    if tail:
        print(f"\n  {len(tail)} sit AFTER the defending units in roster order "
              f"({', '.join(tail)}), so they\n  draw from the saturated tail and "
              f"contribute nothing at all to a full stack.")
    print(f"\n  {len(pure_units)} are pure combat units (M = 1.00, they buff "
          f"nobody): {', '.join(pure_units) or 'none'}")
    print(f"  {len(buffers)} multiply the whole stack: "
          + (", ".join(f"{h} x{fitted[h][1]:.2f}" for h in buffers) or "none"))
    print("\n  A and M are only separable because the stack-size factor "
          "saturates. On a\n  20-unit stack both halves would still be one "
          "number.")


HERO_LEVELS = ["1", "5", "15", "20"]


def exp_hero_levels(p: Probe) -> None:
    """How do a hero's two parameters scale with its level?

    This is the ONE thing blocking the app from modelling heroes at all. The
    law is known exactly and all sixteen land-legal heroes are decomposed --
    but every reading is level 10 of 20, and a player choosing a hero chooses
    a level. Shipping level 10 as though it were the mechanic would put a
    confident number on nineteen unmeasured levels.

    Two heroes, four levels, two stack sizes each, so A and M are separated at
    every level rather than confounded the way a single stack size confounds
    them:

      kangal        A = 20.0, M = 1.00 at lvl 10 -- a pure combat unit
      joffre_home   A = 16.0, M = 1.30 at lvl 10 -- the only strong buffer

    If A and M both scale simply, heroes become modellable across the whole
    range. If only A scales, the buff is a flat property of the hero. If
    neither is simple, the app keeps refusing them and this says why.
    """
    abb, lvl, hp = HERO_FIELDS
    picks = [h for h in ("kangal", "joffre_home") if h in hero_options()]
    if not picks:
        print("  ! neither probe hero is on the roster.", file=sys.stderr)
        return
    ctl, _ = _recorded_hero_readings()
    if not all(n in ctl for n in (10, 30, 50)):
        print("  ! controls missing; run hero_scaling first.", file=sys.stderr)
        return

    print(f"\n  {len(picks)} heroes x {len(HERO_LEVELS)} levels x 2 stack sizes")
    print(f"  level 10 is already on disk and is used as a held-out check.\n")
    print(f"  {'hero':13} {'lvl':>4} {'A (own atk)':>12} {'M (stack)':>10} {'fit':>9}")

    for h in picks:
        curve: list[tuple[int, float, float]] = []
        for level in HERO_LEVELS:
            got: dict[int, float] = {}
            for n in (10, 50):
                ov = dict(settings(), **{abb: h, lvl: level, hp: "100%"})
                ov.update(duel(1, "inf", 20, "inf", n))
                try:
                    r = p.submit(ov, create=HERO_FIELDS)
                    got[n] = r.get("A.1.1")
                    record("hero_levels", {"hero": h, "level": int(level),
                                           "def_n": n,
                                           "detail": dict(p.last_details)}, r)
                except (BareFormReturned, ValueError) as e:
                    print(f"  ! {h} lvl {level} n={n}: {e}", file=sys.stderr)
            if got.get(10) is None or got.get(50) is None:
                print(f"  {h:13} {level:>4} {'—':>12} {'—':>10} {'partial':>9}")
                continue
            # Two stack sizes give two equations; solve in whichever position
            # fits, exactly as the full-roster decomposition does.
            u10 = DEF_COEF["inf"] * (effective_units(11) - 1)
            u50 = DEF_COEF["inf"] * (effective_units(51) - 1)
            m = (got[50] - got[10]) / (u50 - u10)
            a = got[10] - u10 * m
            curve.append((int(level), a, m))
            print(f"  {h:13} {level:>4} {a:12.2f} {m:10.4f} {'ok':>9}")

        if len(curve) < 3:
            print(f"  {h}: too few levels to fit a curve.")
            continue
        # Is A proportional to level? Linear in level? Neither?
        lv = [c[0] for c in curve]
        aa = [c[1] for c in curve]
        mm = [c[2] for c in curve]
        per = [a / l for a, l in zip(aa, lv)]
        spread = lambda v: (max(v) / min(v)) if min(v) > 1e-9 else float("inf")
        print(f"    A per level: {[round(x, 3) for x in per]}")
        if spread(per) <= 1.02:
            print(f"    -> A IS PROPORTIONAL TO LEVEL, {sum(per)/len(per):.3f} "
                  f"per level. One number describes all twenty.")
        else:
            slope = (aa[-1] - aa[0]) / (lv[-1] - lv[0])
            base = aa[0] - slope * lv[0]
            pred = [base + slope * l for l in lv]
            err = max(abs(pr - a) / a for pr, a in zip(pred, aa) if a)
            if err <= 0.02:
                print(f"    -> A IS LINEAR IN LEVEL: {base:.2f} + "
                      f"{slope:.3f} x level (worst {100*err:.2f}%).")
            else:
                print(f"    -> A is neither proportional nor linear "
                      f"(worst {100*err:.1f}%). The rows above are the finding.")
        if spread(mm) <= 1.005:
            print(f"    M holds flat at {sum(mm)/len(mm):.3f} across levels — "
                  f"the buff is a property of the hero, not of its level.")
        else:
            print(f"    M moves with level too: {[round(x, 4) for x in mm]}")


MAXLVL_RE = re.compile(r"Max level is (\d+)", re.I)


def exp_hero_caps(p: Probe) -> None:
    """Pin the level mechanic, and get every hero's real level cap.

    hero_levels established two things and left one open:

      A does NOT move with level      kangal 20.00 at lvl 1, 5, 10
      M DOES                          joffre_home 1.10 / 1.20 / 1.30 / 1.40
                                      at levels 1 / 5 / 10 / 15
      max level is per-hero           "Max level is 10" / "Max level is 15"

    Those four M readings are five levels apart, so they fit a slope and a
    STEP equally well. Levels 2, 4, 9 and 11 separate them: a step every five
    levels predicts 1.10, 1.10, 1.20, 1.30, while any slope predicts four
    different values.

    The caps come free -- ask for level 20 and the server names the real
    maximum in its refusal, one request per hero.
    """
    abb, lvl, hp = HERO_FIELDS
    # TWO stack sizes per level. One is not enough: at a single stack size A
    # and M are confounded, and assuming A held flat is the very substitution
    # this project keeps having to undo. The first attempt did exactly that
    # and produced an M curve with an impossible shape (+0.05 from level 1 to
    # 2, then +0.01 across the next two levels).
    print("\n  1. how does M move with level? joffre_home, two stack sizes each\n")
    print(f"  {'lvl':>4} {'A':>8} {'M':>8} {'position':>9}")
    curve: list[tuple[int, float, float]] = []
    for level in (2, 4, 9, 11):
        got: dict[int, float] = {}
        for n in (10, 50):
            ov = dict(settings(), **{abb: "joffre_home", lvl: str(level), hp: "100%"})
            ov.update(duel(1, "inf", 20, "inf", n))
            try:
                r = p.submit(ov, create=HERO_FIELDS)
                got[n] = r.get("A.1.1")
                record("hero_caps", {"hero": "joffre_home", "level": level,
                                     "def_n": n, "detail": dict(p.last_details)}, r)
            except (BareFormReturned, ValueError) as e:
                print(f"  ! lvl {level} n={n}: {e}", file=sys.stderr)
        if got.get(10) is None or got.get(50) is None:
            continue
        u10 = DEF_COEF["inf"] * (effective_units(11) - 1)
        u50 = DEF_COEF["inf"] * (effective_units(51) - 1)
        m = (got[50] - got[10]) / (u50 - u10)
        a = got[10] - u10 * m
        curve.append((level, a, m))
        print(f"  {level:>4} {a:8.2f} {m:8.4f} {'first':>9}")

    known = [(1, 1.10), (5, 1.20), (10, 1.30), (15, 1.40)]
    allpts = sorted(known + [(l, m) for l, _, m in curve])
    print("\n  every decomposed level: "
          + ", ".join(f"L{l}={m:.2f}" for l, m in allpts))
    if len(allpts) >= 6:
        step = all(abs(m - (1.0 + 0.10 * (l // 5 + 1))) <= 0.005 for l, m in allpts)
        lin = all(abs(m - (1.10 + 0.02 * l)) <= 0.005 for l, m in allpts)
        if step:
            print("  VERDICT: M steps every five levels — 1.0 + 0.10 x "
                  "(floor(level/5) + 1).")
        elif lin:
            print("  VERDICT: M is linear in level — 1.10 + 0.02 x level.")
        else:
            print("  VERDICT: neither a clean step nor a clean line. The "
                  "levels above are the finding;\n  quote them, do not fit "
                  "them.")

    print("\n  2. every hero's real level cap, from the server's own refusal\n")
    caps: dict[str, int] = {}
    for h in hero_options():
        ov = dict(settings(), **{abb: h, lvl: "20", hp: "100%"})
        ov.update(duel(1, "inf", 20, "inf", 10))
        try:
            p.submit(ov, create=HERO_FIELDS)
            caps[h] = 20
            record("hero_caps", {"hero": h, "cap": 20}, {})
        except BareFormReturned as e:
            m = MAXLVL_RE.search(str(e))
            if m:
                caps[h] = int(m.group(1))
                record("hero_caps", {"hero": h, "cap": caps[h]}, {})
            else:
                record("hero_caps", {"hero": h, "error": str(e)}, {})
        except ValueError as e:
            record("hero_caps", {"hero": h, "error": str(e)}, {})
    for h in hero_options():
        print(f"  {h:14} {caps.get(h, '—')}")
    if caps:
        by = {}
        for h, c in caps.items():
            by.setdefault(c, []).append(h)
        print("\n  caps: " + "; ".join(f"{c} -> {len(v)} heroes"
                                       for c, v in sorted(by.items())))
        print("  The dropdown offers 1..20 for everyone. It is wrong for every "
              "hero here,\n  and the server says so rather than clamping.")


# The nine land types that can share one stack. convoy is excluded because the
# server refuses it alongside anything else, and it is the only land type that
# cannot appear in a mixed army.
LAND_NINE = ["inf", "cav", "ac", "lart", "art", "rrg", "lt", "ht", "st"]

# An attacker whose only job is to be shot at, so that its loss reports the
# DEFENDER'S OUTPUT rather than its own pool. Sixty infantry carry 1200 HP; the
# largest output any candidate law predicts for the stacks below is 697. The
# hero screen that preceded this one used twenty (pool 400) and was wiped in
# every single run -- 400.0 of 400.0, sixteen times -- so its output column was
# a constant and could not have distinguished anything.
SURVIVOR_N = 60

# A and M as decomposed by hero_table and hero_levels, mirrored from
# web/data.js. A is the hero's own attack, flat with level. M is the multiplier
# it applies to INFANTRY output -- the only unit type the decomposition ever
# put underneath a hero -- quoted at level 10. M = 1.00 means "no infantry buff
# was found", which is emphatically not the same as "this hero buffs nothing".
MEASURED_HEROES: dict[str, tuple[float, float]] = {
    "kangal": (20.0, 1.00), "joffre": (16.0, 1.00), "joffre_home": (16.0, 1.30),
    "marco": (15.0, 1.00), "allen": (10.0, 1.00), "larab": (10.0, 1.00),
    "alvin": (8.30, 1.00), "lucien": (8.0, 1.00), "lucien_g": (8.0, 1.00),
    "pershing": (8.0, 1.00), "georg": (6.0, 1.00), "tatiana": (6.0, 1.00),
    "hank": (6.0, 1.09), "johan": (5.0, 1.00), "tatiana_home": (5.0, 1.00),
    "maeve": (4.0, 1.00),
}


def _defender_output(p: Probe, rows: list[tuple[str, int]],
                     hero: str | None = None, level: int = 10,
                     atk_n: int | None = None) -> dict | None:
    """One request: the attacker's HP loss IS the defender's output.

    Returns None both when the server refuses and when the attacker is WIPED,
    because a wiped attacker reports its own pool and nothing about the
    defender. Those two cases look identical downstream once they are written
    as a number, which is precisely how the previous hero screen collected
    sixteen readings of 400.0 and read them as data.
    """
    # Resolved here rather than bound as a default, so that the offline suite
    # can shrink the attacker and prove this function refuses a censored
    # reading instead of returning the pool as if it were data.
    atk_n = SURVIVOR_N if atk_n is None else atk_n
    ov = settings()
    ov.update(duel(1, "inf", atk_n, rows[0][0], rows[0][1]))
    ov.update(composite(1, "B", rows))
    create = composite_fields("B", 1, len(rows))
    if hero:
        ov.update({HERO_FIELDS[0]: hero, HERO_FIELDS[1]: str(level),
                   HERO_FIELDS[2]: "100%"})
        create = create + HERO_FIELDS
    label = f"{hero or 'no hero'} vs {'+'.join(u for u, _ in rows)}"
    try:
        p.submit(ov, create=create)
    except (BareFormReturned, ValueError) as e:
        print(f"  ! {label}: {e}", file=sys.stderr)
        record("survivable_rig", {"hero": hero, "rows": rows,
                                  "error": str(e)}, {})
        return None
    d = dict(p.last_details)
    a = d.get("A.1.1") or {}
    record("survivable_rig", {"hero": hero, "level": level if hero else None,
                              "rows": rows, "atk_n": atk_n, "detail": d},
           {k: (v or {}).get("lost") for k, v in d.items()})
    if a.get("lost") is None:
        print(f"  ! {label}: no attacker row in the response", file=sys.stderr)
        return None
    if (a.get("pct") or 0) >= 99.9:
        print(f"  ! {label}: ATTACKER WIPED ({a['lost']} of {a.get('pool')}) "
              f"-- reading discarded, that is the pool and not the output",
              file=sys.stderr)
        return None
    return {"out": a["lost"], "detail": d}


def exp_stack_ladder(p: Probe) -> None:
    """Does the cumulative law survive a stack with more than two rows?

    WHY THIS EXISTS. mixed_stacks established "PER STACK, CUMULATIVE IN ROSTER
    ORDER" on two-row stacks, and the web app applies it to every stack. A
    nine-row stack already on disk contradicts it: six of each land type made
    an attacker of twenty infantry lose 400.0 of a 400.0 pool, so the
    defender's output was at LEAST 400, while cumulative predicts 299.35. That
    reading is censored -- 400 is a floor and not a value -- so it refutes
    cumulative without naming a replacement. shared predicts 451.89 and
    per_type 697.20.

    THE DISCRIMINATOR. Add one type at a time, six units each. Below twenty
    units all three laws are the same function, so those rows are a free check
    on the defence coefficients in a mixed stack; past it they diverge to a
    spread of 398 HP by the ninth row. This time the attacker can absorb the
    largest of them.
    """
    print(f"\n  {SURVIVOR_N} infantry (pool {SURVIVOR_N * 20}) attack a stack "
          f"grown one type at a time, six each.\n")
    print(f"  {'rows':>4} {'units':>5} {'measured':>9} " +
          " ".join(f"{m:>11}" for m in STACK_LAWS))
    seen: list[tuple[list[tuple[str, int]], float]] = []
    for k in range(1, len(LAND_NINE) + 1):
        rows = [(u, 6) for u in LAND_NINE[:k]]
        got = _defender_output(p, rows)
        n = sum(c for _, c in rows)
        if not got:
            print(f"  {k:>4} {n:>5} {'—':>9}")
            continue
        seen.append((rows, got["out"]))
        print(f"  {k:>4} {n:>5} {got['out']:9.2f} " +
              " ".join(f"{predict_stack(rows, m):11.2f}" for m in STACK_LAWS))

    wide = [(r, o) for r, o in seen if sum(c for _, c in r) > 20]
    if not wide:
        print("\n  NO VERDICT — nothing past the twenty-unit knee was read, "
              "and below it the three laws are the same function.")
        return
    errs = {m: max(abs(o - predict_stack(r, m)) / o for r, o in wide)
            for m in STACK_LAWS}
    for m in STACK_LAWS:
        print(f"    {m:11} worst error {100 * errs[m]:6.2f}%")
    best = min(errs, key=errs.get)
    if errs[best] <= 0.01:
        print(f"\n  VERDICT: {best} fits every row past the knee "
              f"({100 * errs[best]:.3f}%).")
        if best != "cumulative":
            print("  THIS OVERTURNS mixed_stacks, which only ever built "
                  "two-row stacks — where\n  cumulative and the winner here "
                  "differ by less than the reading precision. The\n  web app "
                  "ships cumulative and is therefore wrong for wide stacks. "
                  "Fix engine.js.")
    else:
        print(f"\n  VERDICT: none of the candidates fits (best is {best} at "
              f"{100 * errs[best]:.2f}%). The measured column is the\n  "
              f"finding — do not compress it into a law, and do not leave the "
              f"app claiming one\n  that missed by that much.")


ATK_COEF = {code: v[1] for code, v in MEASURED_UNITS.items()}


def exp_stack_order(p: Probe) -> None:
    """Validate desc_coef on stacks it was not fitted to, and find its key.

    exp_stack_ladder fitted "the stack saturates as a whole and rows draw from
    it strongest first" to 0.002% on nine readings. Fitting a law to the data
    that suggested it is not the same as testing it, and this project has twice
    shipped a law that fitted everything it had seen and then failed on the
    first configuration it had not. So:

      HELD OUT. Three defending stacks of a shape the ladder never built --
      different types, different counts, chosen so desc_coef sits at least 40%
      away from every other candidate. Predictions below are written down
      BEFORE the requests go out; they are in the printout so a later reader
      can see they were not adjusted afterwards.

      THE KEY. A stack ordered "strongest first" begs the question of which
      strength. Defending, attack and defence coefficients rank the roster
      differently -- an armoured car out-defends a stormtrooper 12.0 to 6.3 and
      is out-attacked by it 6.0 to 25.0 -- so an ATTACKING stack of those two
      separates "ordered by the coefficient in use" from "ordered by some fixed
      ranking of units". The app has to know which; it computes both sides.
    """
    print("\n  1. held out: three defending stacks the ladder never built\n")
    print(f"  {'stack':34} {'measured':>9} " +
          " ".join(f"{m:>10}" for m in STACK_LAWS))
    held = [
        [("lart", 30), ("art", 30), ("rrg", 30)],
        [("lart", 25), ("ht", 25)],
        [("inf", 30), ("ac", 30), ("lt", 30)],
    ]
    scored: list[tuple[str, float, dict[str, float]]] = []
    for rows in held:
        pred = {m: predict_stack(rows, m) for m in STACK_LAWS}
        # Big enough for the largest prediction on the board, whichever wins.
        atk_n = int(max(pred.values()) / 20.0) + 30
        label = " + ".join(f"{c} {u}" for u, c in rows)
        got = _defender_output(p, rows, atk_n=atk_n)
        cells = " ".join(f"{pred[m]:10.2f}" for m in STACK_LAWS)
        if not got:
            print(f"  {label:34} {'—':>9} {cells}")
            continue
        scored.append((label, got["out"], pred))
        print(f"  {label:34} {got['out']:9.2f} {cells}")

    if scored:
        errs = {m: max(abs(o - pred[m]) / o for _, o, pred in scored)
                for m in STACK_LAWS}
        print()
        for m in STACK_LAWS:
            print(f"    {m:11} worst error {100 * errs[m]:7.3f}%")
        best = min(errs, key=errs.get)
        if errs[best] <= 0.01:
            print(f"\n  HELD OUT: {best} predicted stacks it was not fitted "
                  f"to, worst error {100 * errs[best]:.3f}%.")
        else:
            print(f"\n  HELD OUT: FAILED. The best candidate is {best} at "
                  f"{100 * errs[best]:.3f}%, so the ladder's law does not\n  "
                  f"generalise and must not be shipped as one.")

    print("\n  2. which coefficient does the ordering use?\n")
    # Attacking, so it is the ATTACK column that is in play. Both pairs are
    # ranked one way by attack and the other way by defence, and the second
    # separates all three candidates by more than 60%: a stormtrooper out-
    # attacks infantry 25 to 4 while defending barely better, 6.3 to 5.0.
    print(f"  {'attacking stack':22} {'measured':>9} {'by ATK':>10} "
          f"{'by DEF':>10} {'roster':>10}")
    obs_rows: list[tuple[str, float, dict[str, float]]] = []
    for rows in ([("ac", 25), ("st", 25)], [("inf", 30), ("st", 30)]):
        cand = {
            "by ATK": predict_stack(rows, "desc_coef", coef=ATK_COEF),
            "by DEF": predict_stack(rows, "desc_coef", coef=ATK_COEF,
                                    order_by=DEF_COEF),
            "roster": predict_stack(rows, "cumulative", coef=ATK_COEF),
        }
        ov = settings()
        ov.update(duel(1, rows[0][0], rows[0][1], "ht", 60))
        ov.update(composite(1, "A", rows))
        label = " + ".join(f"{c} {u}" for u, c in rows)
        try:
            p.submit(ov, create=composite_fields("A", 1, len(rows)))
        except (BareFormReturned, ValueError) as e:
            print(f"  ! {label}: {e}", file=sys.stderr)
            continue
        d = dict(p.last_details)
        record("stack_order", {"rows": rows, "side": "A", "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.1") or {}
        if b.get("lost") is None:
            print(f"  ! {label}: no defender row", file=sys.stderr)
            continue
        if (b.get("pct") or 0) >= 99.9:
            print(f"  ! {label}: DEFENDER WIPED, reading discarded",
                  file=sys.stderr)
            continue
        obs_rows.append((label, b["lost"], cand))
        print(f"  {label:22} {b['lost']:9.2f} " +
              " ".join(f"{cand[k]:10.2f}" for k in ("by ATK", "by DEF",
                                                    "roster")))

    # Scored JOINTLY, not pair by pair. Neither pair alone separates all three
    # -- the first ties defence with roster and the second ties defence with
    # attack -- but no two hypotheses share BOTH answers, so the pair of
    # readings picks one and a per-pair vote would deadlock on the ties.
    if not obs_rows:
        print("\n  NO VERDICT on the ordering key — no attacking reading "
              "survived.")
    else:
        errs = {k: max(abs(o - c[k]) / o for _, o, c in obs_rows)
                for k in ("by ATK", "by DEF", "roster")}
        print()
        for k in ("by ATK", "by DEF", "roster"):
            print(f"    {k:8} worst error {100 * errs[k]:7.3f}%")
        best = min(errs, key=errs.get)
        if errs[best] > 0.01:
            print(f"\n  NO VERDICT — the closest key, {best}, still misses by "
                  f"{100 * errs[best]:.2f}%. The stack ordering\n  is not any "
                  f"of the three, and the two readings above are the finding.")
        elif best == "by ATK":
            print("\n  VERDICT: an attacking stack is ordered by its ATTACK "
                  "coefficients — the column\n  actually in use, not a fixed "
                  "ranking of units. Each side sorts by its own,\n  so the app "
                  "needs two sorts and not one.")
        elif best == "by DEF":
            print("\n  VERDICT: the ordering is by the DEFENCE column on both "
                  "sides, so one fixed\n  ranking of units governs attack and "
                  "defence alike.")
        else:
            print("\n  VERDICT: attacking stacks keep ROSTER order, so the "
                  "strongest-first rule found\n  on defence does not carry "
                  "over. The app needs a different sort per side.")


def exp_hero_output(p: Probe) -> None:
    """Does any hero raise the OUTPUT of a land type other than infantry?

    WHAT WENT WRONG LAST TIME. The screen that found the HP channel put all
    nine land types in one stack and read the attacker's loss for each hero.
    The attacker was twenty infantry and every run wiped it, so that column
    read 400.0 sixteen times: the pool, not the output. It measured the HP
    channel by accident and the output channel not at all, and reported the
    latter as covered. This is the same experiment with an attacker that lives.

    THE DESIGN. Nine rows of TWO units is eighteen, and the hero makes
    nineteen — under the twenty-unit knee, so E is linear, every row
    contributes coefficient x count, and all three stack laws agree. That
    matters: the screen does not depend on which one exp_stack_ladder settles.

    A hero with no output buff must raise the stack's output by exactly its own
    attack A, which hero_table already measured. The whole screen is therefore
    one subtraction, and joffre_home is a POSITIVE CONTROL that has to come out
    at A + 0.30 x 5.0 x 2 = A + 3.0 rather than at A. If the control fails,
    nothing else on this page is worth reading.

    LOCALISING. An excess says a type is buffed, not which one. Removing a
    group of types from the stack drops the output by their coefficients if
    they are unbuffed and by more if one of them is not, so a bisection names
    the type in four requests without needing a fresh baseline per subset.
    """
    stack = [(u, 2) for u in LAND_NINE]
    n_units = sum(c for _, c in stack)
    flat = sum(DEF_COEF[u] * c for u, c in stack)
    print(f"\n  Defender: two of each land type ({n_units} units; the hero "
          f"makes {n_units + 1}, under the knee).")
    print(f"  Attacker: {SURVIVOR_N} infantry, pool {SURVIVOR_N * 20}.")
    print(f"  All three stack laws predict the same {flat:.2f} here, so the "
          f"screen does not depend\n  on which one is right.\n")

    base = _defender_output(p, stack)
    if not base:
        print("  NO VERDICT — the baseline itself did not read.")
        return
    err = 100.0 * abs(base["out"] - flat) / flat
    print(f"  baseline (no hero): {base['out']:.2f} measured, {flat:.2f} "
          f"predicted, {err:.2f}% off")
    if err > 1.0:
        print("  ! The baseline disagrees with the defence coefficients in a "
              "mixed stack, so an\n  ! excess cannot be attributed to a hero. "
              "Settle that before reading the table.")

    print(f"\n  {'hero':14} {'output':>8} {'excess':>8} {'own A':>7} "
          f"{'unexplained':>12}")
    flagged: list[tuple[str, float]] = []
    for h in hero_options():
        if h not in MEASURED_HEROES:
            continue
        a, m_inf = MEASURED_HEROES[h]
        got = _defender_output(p, stack, hero=h)
        if not got:
            print(f"  {h:14} {'—':>8}")
            continue
        excess = got["out"] - base["out"]
        # What this hero is already known to do: its own attack, plus the
        # infantry buff hero_levels measured, applied to the two infantry here.
        known = a + (m_inf - 1.0) * DEF_COEF["inf"] * 2
        resid = excess - known
        mark = ("  <-- buffs something" if resid > 0.2 else
                "  <-- CONTRADICTS hero_table" if resid < -0.2 else "")
        print(f"  {h:14} {got['out']:8.2f} {excess:8.2f} {a:7.2f} "
              f"{resid:12.2f}{mark}")
        if abs(resid) > 0.2:
            flagged.append((h, resid))

    # A NEGATIVE residual is not a buff and bisection cannot localise one: it
    # says this hero contributes LESS than hero_table recorded, which
    # contradicts an earlier measurement rather than adding a new one. Say so
    # instead of hunting for a unit type that will not be there.
    short = [(h, r) for h, r in flagged if r < 0]
    for h, r in short:
        print(f"\n  ! {h} falls {abs(r):.2f} HP SHORT of A + the infantry buff "
              f"on record.\n  ! That contradicts hero_table/hero_levels; one of "
              f"the two measurements is wrong.\n  ! Not bisecting — there is no "
              f"missing buff to find, there is a missing explanation.")
    flagged = [(h, r) for h, r in flagged if r > 0]

    if not flagged and short:
        print("\n  NO VERDICT on the output channel — the contradiction(s) "
              "above have to be settled\n  first. A hero whose own attack does "
              "not reproduce cannot be used as the zero\n  against which "
              "another hero's excess is read.")
        return
    if not flagged:
        print("\n  VERDICT: every hero's excess is its own attack plus the "
              "infantry buff already\n  measured. No hero raises the output of "
              "any other land type — down to a floor of\n  0.2 HP, which on "
              "the weakest row here (light artillery, 2.00) is a 10% buff. "
              "Any\n  smaller one would still be hiding.")
        return

    print(f"\n  {len(flagged)} hero(es) do something unaccounted for. "
          f"Bisecting for the type.\n")
    for h, resid in flagged:
        a, m_inf = MEASURED_HEROES[h]

        def explained(kept: list[tuple[str, int]]) -> float:
            """Everything this stack should produce if the buff is NOT here."""
            n_inf = sum(c for u, c in kept if u == "inf")
            return (sum(DEF_COEF[u] * c for u, c in kept)
                    + a + (m_inf - 1.0) * DEF_COEF["inf"] * n_inf)

        cands = list(LAND_NINE)
        while len(cands) > 1:
            half = cands[:len(cands) // 2]
            kept = [(u, 2) for u in LAND_NINE if u not in half]
            got = _defender_output(p, kept, hero=h)
            if not got:
                print(f"  {h}: bisection lost a reading, stopping at "
                      f"{'/'.join(cands)}")
                break
            # If the unexplained excess SURVIVES the removal, the type causing
            # it is in what was kept; if it vanishes, it was in what was cut.
            survived = got["out"] - explained(kept)
            cands = ([c for c in cands if c not in half] if survived > 0.2
                     else half)
        if len(cands) == 1:
            u = cands[0]
            mult = 1.0 + resid / (DEF_COEF[u] * 2)
            print(f"  {h:14} buffs {u.upper()} output x{mult:.3f} "
                  f"(residual {resid:.2f} over a base of {DEF_COEF[u] * 2:.2f})")
        else:
            print(f"  {h:14} narrowed to {'/'.join(cands)}, not resolved")


# Output buffs found by exp_hero_output: hero -> {unit: multiplier at level 10}.
# The infantry entries come from hero_levels, which measured them years of
# requests ago on single-type stacks; the rest come from the nine-type screen
# and its bisection.
HERO_OUTPUT_BUFFS: dict[str, dict[str, Any]] = {
    # inf carries the level curve hero_levels measured; the others are the
    # level-10 figure the nine-type screen found, pending exp_hero_full.
    "joffre_home": {"inf": {1: 1.10, 2: 1.15, 4: 1.16, 5: 1.20, 9: 1.28,
                            10: 1.30, 11: 1.32, 15: 1.40},
                    "ac": 1.30},
    "hank": {"inf": {1: 1.00, 2: 1.03, 5: 1.06, 9: 1.09, 10: 1.09}},
    "alvin": {"st": 1.40},
    "kangal": {"ac": 1.20},
}


def exp_hero_buff_confirm(p: Probe) -> None:
    """Re-measure each recorded output buff on its own, one request each.

    The screen localises a buff by bisection: it removes groups of unit types
    and watches whether the unexplained excess survives. Every step of that is
    a live reading rather than an inference, but the whole procedure assumes
    ONE buffed type per hero, and a second one hiding in the same half would
    bend the answer without making it look wrong.

    A stack containing only the named type settles it in a single request, and
    it is worth keeping runnable: if the site rebalances a hero, this is the
    experiment that goes red, and it costs one request per buff to ask.
    """
    print("\n  Each hero alone with the unit type it is said to buff.\n")
    print(f"  {'hero':14} {'unit':5} {'measured':>9} {'if buffed':>10} "
          f"{'if not':>9} {'implied x':>10}")
    bad = 0
    for hero, buffs in HERO_OUTPUT_BUFFS.items():
        a, _ = MEASURED_HEROES[hero]
        for unit, entry in buffs.items():
            # An entry is either a level curve or a single level-10 figure.
            mult = entry[10] if isinstance(entry, dict) else entry
            rows = [(unit, 2)]
            plain = DEF_COEF[unit] * 2
            got = _defender_output(p, rows, hero=hero)
            if not got:
                print(f"  {hero:14} {unit:5} {'—':>9}")
                bad += 1
                continue
            implied = (got["out"] - a) / plain
            print(f"  {hero:14} {unit:5} {got['out']:9.2f} "
                  f"{a + mult * plain:10.2f} {a + plain:9.2f} "
                  f"{implied:10.3f}")
            if abs(implied - mult) > 0.01:
                print(f"    ! recorded as x{mult:.2f}, measures x{implied:.3f}"
                      f" — the screen's bisection put this on the wrong type,"
                      f"\n    ! or the site has changed. Do not ship the "
                      f"recorded figure.")
                bad += 1
    if bad:
        print(f"\n  {bad} recorded buff(s) did not reproduce. The table above "
              f"is what the server says\n  today; HERO_OUTPUT_BUFFS is what "
              f"this repo claims. Reconcile them before shipping.")
    else:
        print("\n  Every recorded output buff reproduces in isolation, so the "
              "bisection put each one\n  on the right unit type and no hero "
              "here buffs a second type it was not caught at.")


# The hero's own HP pool, per hero. Read off B.1.hero's span in readings
# already on disk -- no request was spent on this. Every bracket, intersected
# across every level and stack size the hero appears at, contains exactly one
# round number, and the brackets do NOT move with level: joffre_home reads the
# same at levels 1, 2, 4, 5, 9, 10, 11 and 15.
HERO_POOL: dict[str, float] = {
    "joffre_home": 120.0, "joffre": 120.0, "alvin": 100.0, "kangal": 90.0,
    "pershing": 80.0, "larab": 75.0, "marco": 60.0, "allen": 50.0,
    "hank": 40.0, "lucien": 40.0, "lucien_g": 40.0, "johan": 40.0,
    "georg": 40.0, "maeve": 20.0, "tatiana": 15.0, "tatiana_home": 15.0,
}

# HOW INCOMING DAMAGE SPLITS ACROSS A STACK'S ROWS.
#
#     weight_i = TARGET_FACTOR[unit_i] * count_i
#
# and it is a property of the TARGET, not of the attacker: all nine land
# attackers produce the identical three-value pattern, bracketed across them to
# [0.4979, 0.5023], [0.7449, 0.7559] and [0.9918, 1.0083]. Infantry soak half
# the damage a unit of any other type would take; cavalry three quarters.
#
# The attacker's TOTAL is unaffected -- it stays coefficient x E(n) whatever
# the target mix, confirmed for all nine attackers -- so these are pure
# allocation weights and not damage values. That is the opposite of air, where
# the target changes the total outright.
#
# The app shipped "in proportion to the defending row's own attack stat",
# which is out by 40% of the stack total on a nine-row stack. It fitted because
# all four mixtures it was drawn from were infantry + artillery, whose own
# attack values are 4.0 and 8.0 -- exactly the 0.5 : 1.0 ratio this table gives
# them. The third law in this project fitted on one pair and stated as a rule.
TARGET_FACTOR: dict[str, float] = {"inf": 0.50, "cav": 0.75}
TARGET_FACTOR_DEFAULT = 1.00

# What a hero counts for when incoming damage is split across the rows. The
# same constant for all sixteen -- it does not move with the hero's attack, its
# pool or its level -- bracketed to [3.185, 3.204] over 27 uncensored readings.
# Measured against an INFANTRY attacker only, like the unit weights below.
HERO_ALLOC_WEIGHT = 0.40      # in TARGET_FACTOR units; bracket [0.398, 0.4005]


def exp_allocation(p: Probe) -> None:
    """Which weights split a stack's incoming damage across its rows?

    THE APP SHIPS THE WRONG RULE. mixed_stacks concluded "in proportion to the
    defending row's own (attack value x count)" and fitted it exactly. Every
    one of its four mixtures was infantry + artillery, whose own attack values
    are 4.0 and 8.0 -- and an INFANTRY ATTACKER happens to deal 4 / 6 / 8
    against infantry / cavalry / everything else. The two rules are the same
    function on that pair and nowhere else. Against nine rows the shipped rule
    is out by 40% of the stack total; the attacker-rate rule is out by 0.042%.

    That makes this the third law in this project fitted on a single pair of
    unit types and written down as a property of the roster.

    WHAT THIS MEASURES. One request per attacking unit type against the SAME
    nine-type defender, two of each. The nine row losses in one response are
    that attacker's relative rate against all nine targets -- a whole row of
    the land matrix per request, rather than the 81 duels the matrix would
    cost. Anchored on the diagonal, which unit_stats already measured, the
    relative rates become absolute ones.

    It also checks a second thing for free: whether a land attacker's TOTAL
    output depends on what it is shooting at. It does not for infantry --
    4.0 x E(n) whether the target is one row or nine -- and if that holds for
    all nine attackers, the per-class rates are pure allocation weights and not
    damage values, which is the opposite of how air behaves.
    """
    # Sized so the total stays near 90: big enough to read against a 0.05
    # resolution, small enough that no defender row is wiped. The weakest row
    # here is 2 light artillery with a pool of 20.
    counts = {"inf": 20, "cav": 6, "ac": 15, "lart": 18, "art": 11,
              "rrg": 5, "lt": 3, "ht": 2, "st": 4}
    defender = [(u, 2) for u in LAND_NINE]
    print("\n  One request per attacker against the same nine-type defender.")
    print("  Each response is one ROW of the land matrix: nine relative rates "
          "at once.\n")
    head = " ".join(f"{u:>7}" for u in LAND_NINE)
    print(f"  {'attacker':10} {'total':>8} {'E(n)xdiag':>10}  {head}")
    table: dict[str, dict[str, float]] = {}
    for atk in LAND_NINE:
        n = counts[atk]
        ov = settings()
        ov.update(duel(1, atk, n, defender[0][0], defender[0][1]))
        ov.update(composite(1, "B", defender))
        try:
            p.submit(ov, create=composite_fields("B", 1, len(defender)))
        except (BareFormReturned, ValueError) as e:
            print(f"  ! {atk}: {e}", file=sys.stderr)
            continue
        d = dict(p.last_details)
        record("allocation", {"attacker": atk, "atk_n": n, "rows": defender,
                              "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        cells = [(d.get(f"B.1.{i}") or {}) for i in range(1, len(defender) + 1)]
        if any("lost" not in c for c in cells):
            print(f"  ! {atk}: a defender row did not report", file=sys.stderr)
            continue
        wiped = [LAND_NINE[i] for i, c in enumerate(cells)
                 if (c.get("pct") or 0) >= 99.9]
        if wiped:
            print(f"  ! {atk}: row(s) {'/'.join(wiped)} WIPED — the split is "
                  f"censored, reading discarded", file=sys.stderr)
            continue
        tot = sum(c["lost"] for c in cells)
        base = cells[0]["lost"] or 1.0
        # Anchored on the diagonal: the attacker's rate against its own type is
        # the value unit_stats measured, so the whole row scales from it.
        anchor = MEASURED_UNITS[atk][1]
        own = cells[LAND_NINE.index(atk)]["lost"]
        rates = {u: anchor * c["lost"] / own for u, c in zip(LAND_NINE, cells)}
        table[atk] = rates
        expect = MEASURED_UNITS[atk][1] * effective_units(n)
        print(f"  {atk:10} {tot:8.2f} {expect:10.2f}  "
              + " ".join(f"{rates[u]:7.2f}" for u in LAND_NINE))

    if not table:
        print("\n  NO VERDICT — nothing read.")
        return
    print("\n  Rows are the attacker, columns the target. Anchored on the "
          "diagonal from unit_stats.")
    # Across ALL nine columns, not just the first and last -- those two could
    # easily land in the same target class and read flat while the row in
    # between varies by a factor of three.
    flat = all(max(r.values()) - min(r.values()) < 0.01 for r in table.values())
    if flat:
        print("  Every attacker splits its damage evenly — allocation does NOT "
              "depend on the target.")
    else:
        print("  Allocation depends on the TARGET TYPE, so the shipped rule "
              "(the defending row's own\n  attack stat) is wrong for any "
              "mixture it was not fitted on.")

# The heroes with a measured effect through either channel, and the levels to
# read them at. Every non-infantry figure on record came from a single sweep at
# level 10; joffre_home is the only hero whose curve was ever measured across
# levels, and it runs 1.10 to 1.40, so one level is not a mechanic.
HERO_LEVEL_PICKS: dict[str, list[int]] = {
    "joffre_home": [1, 5, 10, 15],
    "alvin": [1, 5, 10, 15, 20],
    "kangal": [1, 5, 10],
    "hank": [1, 5, 10],
    "pershing": [1, 5, 10, 15, 20],
    "marco": [1, 5, 10],
}


def exp_hero_full(p: Probe) -> None:
    """Both hero channels, across levels, one request per (hero, level).

    The nine-type stack reads OUTPUT and HP in the same response: the
    attacker's loss is the stack's output, and each row's own span gives that
    row's pool. So the two channels cost one sweep between them rather than
    one each.

    Two of each type is eighteen units, nineteen with the hero -- under the
    twenty-unit knee, so E is linear and no stack law can confound the
    reading. The attacker is sized so that no defender row is wiped: the
    weakest here is two light artillery with a pool of 20, which takes 83% and
    survives. A wiped row reports its own pool as the loss and its POOL as
    unreadable, which is exactly the reading this whole rig exists to refuse.
    """
    stack = [(u, 2) for u in LAND_NINE]
    print(f"\n  Defender: two of each land type. Attacker: {SURVIVOR_N} "
          f"infantry.\n")
    base = _defender_output(p, stack)
    if not base:
        print("  NO VERDICT — the baseline did not read.")
        return
    base_pool = {u: (base["detail"].get(f"B.1.{i}") or {}).get("pool")
                 for i, (u, _) in enumerate(stack, start=1)}
    print(f"  baseline output {base['out']:.2f}; pools "
          + ", ".join(f"{u} {base_pool[u]}" for u, _ in stack[:4]) + " ...")

    print(f"\n  {'hero':13} {'lvl':>4} {'output':>8} {'resid':>7} "
          f"{'-> M':>18}   HP pools that moved")
    out_curve: dict[str, dict[int, tuple[str, float]]] = {}
    hp_curve: dict[str, dict[int, dict[str, float]]] = {}
    for hero, levels in HERO_LEVEL_PICKS.items():
        a, _ = MEASURED_HEROES[hero]
        known_out = HERO_OUTPUT_BUFFS.get(hero, {})
        for lvl in levels:
            got = _defender_output(p, stack, hero=hero, level=lvl)
            if not got:
                print(f"  {hero:13} {lvl:>4} {'—':>8}")
                continue
            # OUTPUT. Everything the hero adds beyond its own attack, with the
            # infantry part removed where hero_levels already measured a curve
            # for it, so what is left belongs to the other unit type.
            resid = got["out"] - base["out"] - a
            inf_m = _hero_inf_multiplier(hero, lvl)
            resid -= (inf_m - 1.0) * DEF_COEF["inf"] * 2
            target = next((u for u in known_out if u != "inf"), None)
            shown = "—"
            if target:
                m = 1.0 + resid / (DEF_COEF[target] * 2)
                out_curve.setdefault(hero, {})[lvl] = (target, m)
                shown = f"{target} x{m:.3f}"
            elif abs(resid) > 0.2:
                shown = f"UNEXPLAINED {resid:+.2f}"
            # HP. A row's pool is lost/pct with pct printed to three
            # significant figures, so a RATIO of two pools carries the error of
            # both. Comparing point estimates against a flat 1% threshold
            # invents buffs: it reported a 0.978 on artillery in the offline
            # suite, from nothing but rounding. Flag a move only when the two
            # brackets are disjoint, and quote the ratio's own range.
            moved = {}
            for i, (u, _) in enumerate(stack, start=1):
                cell = got["detail"].get(f"B.1.{i}") or {}
                bcell = base["detail"].get(f"B.1.{i}") or {}
                if not cell.get("pool") or not bcell.get("pool"):
                    continue
                lo, hi = hp_bounds(cell, 1)
                blo, bhi = hp_bounds(bcell, 1)
                if lo > bhi or hi < blo:
                    moved[u] = cell["pool"] / bcell["pool"]
            if moved:
                hp_curve.setdefault(hero, {})[lvl] = moved
            print(f"  {hero:13} {lvl:>4} {got['out']:8.2f} {resid:7.2f} "
                  f"{shown:>18}   "
                  + (", ".join(f"{u} x{r:.3f}" for u, r in moved.items())
                     or "none"))

    print("\n  OUTPUT multiplier by level\n")
    for hero, curve in out_curve.items():
        pts = ", ".join(f"L{l}={m:.3f}" for l, (_, m) in sorted(curve.items()))
        unit = next(iter(curve.values()))[0]
        flat = max(m for _, m in curve.values()) - min(m for _, m in curve.values())
        verdict = ("FLAT with level" if flat < 0.01
                   else "MOVES with level — one level is not the mechanic")
        print(f"  {hero:13} {unit:5} {pts}   -> {verdict}")

    print("\n  HP multiplier by level\n")
    for hero, curve in hp_curve.items():
        units = sorted({u for lv in curve.values() for u in lv})
        for u in units:
            pts = ", ".join(f"L{l}={lv[u]:.3f}" for l, lv in sorted(curve.items())
                            if u in lv)
            vals = [lv[u] for lv in curve.values() if u in lv]
            flat = max(vals) - min(vals) if vals else 0.0
            print(f"  {hero:13} {u:5} {pts}   -> "
                  + ("FLAT with level" if flat < 0.01 else "MOVES with level"))
    if not hp_curve:
        print("  none — no row's pool moved at any level tried.")


def _hero_inf_multiplier(hero: str, level: int) -> float:
    """The infantry output multiplier hero_levels measured, at this level.

    Interpolated between measured points, never extrapolated into a formula:
    joffre_home's curve is 1.10 / 1.15 / 1.16 / 1.20 over levels 1, 2, 4, 5,
    which is neither a line nor a step.
    """
    curve = HERO_OUTPUT_BUFFS.get(hero, {}).get("inf")
    if not curve:
        return 1.0
    pts = sorted(curve)
    if level in curve:
        return curve[level]
    below = [x for x in pts if x < level]
    above = [x for x in pts if x > level]
    if not below:
        return curve[pts[0]]
    if not above:
        return curve[pts[-1]]
    lo, hi = below[-1], above[0]
    t = (level - lo) / (hi - lo)
    return curve[lo] + t * (curve[hi] - curve[lo])


# "oops: B1.1.inf has more HP than is possible. Max hp for 2 Infantry is
#  47.200000" -- the server states the BUFFED maximum outright, exactly, the
# way it states a building's level cap. That is a better instrument than
# dividing two pools that were each derived from a 3-significant-figure
# percentage: it is exact, and it cannot be scrambled by a misparsed span.
MAX_HP_RE = re.compile(r"Max\s+hp\s+for\s+(\d+)\s+([A-Za-z][A-Za-z ]*?)\s+is\s+"
                       r"([\d.]+)", re.I)

# Which hero/unit pairs raise max HP, from the level-10 screen, and the levels
# to pin exactly.
HERO_HP_PAIRS: list[tuple[str, str]] = [
    ("pershing", "inf"), ("pershing", "ht"), ("alvin", "st"),
    ("joffre_home", "ac"), ("marco", "lt"),
]

# Read EXACTLY off the server's refusal, level by level. Stored as measured
# points and never fitted -- pershing's infantry curve is the reason why. It
# climbs 1.00 / 1.50 / 1.50 / 1.70 / 1.70 over levels 1-5, then DROPS to 1.10
# at level 6 and climbs again to 1.25 by level 20. That discontinuity is
# reproducible and it is not a reading artifact: the same level reads the same
# factor at three units as at two, and the pool derived from an independent
# span agrees with the refusal to the decimal. Any formula through these points
# would be an invention, and would be wrong on one side of level 6 or the
# other.
HERO_HP_CURVES: dict[str, dict[str, dict[int, float]]] = {
    "pershing": {
        "inf": {1: 1.00, 2: 1.50, 3: 1.50, 4: 1.70, 5: 1.70, 6: 1.10,
                7: 1.10, 8: 1.12, 9: 1.12, 10: 1.14, 15: 1.18, 20: 1.25},
        "ht": {1: 1.00, 5: 1.15, 10: 1.25, 15: 1.40, 20: 1.50},
    },
    "alvin": {"st": {1: 1.00, 5: 1.14, 10: 1.22, 15: 1.34, 20: 1.42}},
    "joffre_home": {"ac": {1: 1.00, 5: 1.09, 10: 1.17, 15: 1.30}},
    "marco": {"lt": {1: 1.00, 5: 1.07, 10: 1.12}},
}

# Output multipliers by level, from exp_hero_full. The infantry curves were
# measured earlier by hero_levels; the rest came from the nine-type screen.
HERO_OUTPUT_CURVES: dict[str, dict[str, dict[int, float]]] = {
    "joffre_home": {"inf": {1: 1.10, 2: 1.15, 4: 1.16, 5: 1.20, 9: 1.28,
                            10: 1.30, 11: 1.32, 15: 1.40},
                    "ac": {1: 1.10, 5: 1.20, 10: 1.30, 15: 1.40}},
    "hank": {"inf": {1: 1.00, 2: 1.03, 5: 1.06, 9: 1.09, 10: 1.09}},
    "alvin": {"st": {1: 1.15, 5: 1.25, 10: 1.40, 15: 1.50, 20: 1.60}},
    "kangal": {"ac": {1: 1.08, 5: 1.13, 10: 1.20}},
}


def _read_hp_cap(p: Probe, hero: str, unit: str, level: int,
                 count: int) -> float | None:
    """One request: the buffed max HP for `count` of `unit`, as a multiplier.

    Returns None when the server does not refuse, or refuses without naming a
    maximum -- never a guess.
    """
    ov = settings()
    ov.update(duel(1, "inf", 20, unit, count, def_hp="99999"))
    ov.update(composite(1, "B", [(unit, count)], hp="99999"))
    ov.update({HERO_FIELDS[0]: hero, HERO_FIELDS[1]: str(level),
               HERO_FIELDS[2]: "100%"})
    try:
        p.submit(ov, create=composite_fields("B", 1, 1) + HERO_FIELDS)
        record("hero_hp_cap", {"hero": hero, "unit": unit, "level": level,
                               "count": count, "accepted": True}, {})
        return None
    except BareFormReturned as e:
        m = MAX_HP_RE.search(str(e))
        if not m:
            record("hero_hp_cap", {"hero": hero, "unit": unit, "level": level,
                                   "count": count, "error": str(e)}, {})
            return None
        got = float(m.group(3))
    except ValueError as e:
        print(f"  ! {hero} {unit} L{level} x{count}: {e}", file=sys.stderr)
        return None
    plain = MEASURED_UNITS[unit][0] * count
    record("hero_hp_cap", {"hero": hero, "unit": unit, "level": level,
                           "count": count, "max_hp": got, "unbuffed": plain,
                           "factor": got / plain}, {})
    return got / plain


def exp_hero_hp_cap(p: Probe) -> None:
    """Read each hero's HP buff off the server's own refusal, exactly.

    WHY NOT THE POOLS. hero_full derived these by dividing a buffed pool by an
    unbuffed one, and each pool is lost/pct with pct printed to three
    significant figures. Four of the five pairs came out clean and monotonic;
    pershing's infantry row came out 1.00 / 1.70 / 1.14 / 1.25 across levels
    1 / 5 / 10 / 20, which is not a curve, it is a broken reading. Deriving a
    RATIO of two such pools carries both errors and there is no way to tell a
    real jump from a bad span.

    THE BETTER INSTRUMENT. Ask for more HP than the unit can have. The server
    refuses and names the exact maximum, which is the buffed figure:

        oops: B1.1.inf has more HP than is possible.
              Max hp for 2 Infantry is 47.200000

    One request per hero, unit and level, and the answer is exact rather than
    bracketed. That is also why hero_full's level-15 pershing row failed: 100%
    of a max of 47.2 computes fractionally ABOVE 47.2 in binary, and the
    server's own check rejects it. The refusal was not our bug and it was not
    noise -- it was the measurement.
    """
    print("\n  Asking for impossible HP, and reading the cap out of the "
          "refusal.\n")
    print(f"  {'hero':13} {'unit':5} {'lvl':>4} {'max HP (2 units)':>17} "
          f"{'unbuffed':>9} {'factor':>8}")
    curves: dict[tuple[str, str], dict[int, float]] = {}
    for hero, unit in HERO_HP_PAIRS:
        levels = HERO_LEVEL_PICKS.get(hero, [10])
        for lvl in levels:
            ov = settings()
            ov.update(duel(1, "inf", 20, unit, 2, def_hp="99999"))
            ov.update(composite(1, "B", [(unit, 2)], hp="99999"))
            ov.update({HERO_FIELDS[0]: hero, HERO_FIELDS[1]: str(lvl),
                       HERO_FIELDS[2]: "100%"})
            got = None
            try:
                p.submit(ov, create=composite_fields("B", 1, 1) + HERO_FIELDS)
                # No refusal means the field took an absurd value, so this
                # instrument does not work and must not be reported as if it
                # had.
                print(f"  {hero:13} {unit:5} {lvl:>4}   accepted 99999 HP — "
                      f"this probe cannot read the cap")
                record("hero_hp_cap", {"hero": hero, "unit": unit,
                                       "level": lvl, "accepted": True}, {})
                continue
            except BareFormReturned as e:
                m = MAX_HP_RE.search(str(e))
                if not m:
                    print(f"  {hero:13} {unit:5} {lvl:>4}   refused without a "
                          f"max: {str(e)[:60]}")
                    record("hero_hp_cap", {"hero": hero, "unit": unit,
                                           "level": lvl, "error": str(e)}, {})
                    continue
                got = float(m.group(3))
            except ValueError as e:
                print(f"  ! {hero} {unit} L{lvl}: {e}", file=sys.stderr)
                continue
            plain = MEASURED_UNITS[unit][0] * 2
            f = got / plain
            curves.setdefault((hero, unit), {})[lvl] = f
            record("hero_hp_cap", {"hero": hero, "unit": unit, "level": lvl,
                                   "max_hp": got, "unbuffed": plain,
                                   "factor": f}, {})
            print(f"  {hero:13} {unit:5} {lvl:>4} {got:17.4f} {plain:9.1f} "
                  f"{f:8.4f}")

    if not curves:
        print("\n  NO VERDICT — no cap was readable.")
        return

    # A buff that goes DOWN as the hero levels up is either a real oddity worth
    # naming or a defect in the reading. Either way it must not be averaged
    # into a smooth curve and shipped. Densify around the drop, and re-ask at a
    # different unit count so a count-specific artifact cannot masquerade as a
    # level effect.
    for (hero, unit), c in list(curves.items()):
        pts = sorted(c)
        drops = [(a, b) for a, b in zip(pts, pts[1:]) if c[b] < c[a] - 0.005]
        if not drops:
            continue
        lo, hi = drops[0]
        print(f"\n  ! {hero}/{unit} FALLS from L{lo} (x{c[lo]:.3f}) to L{hi} "
              f"(x{c[hi]:.3f}). Densifying before reporting it.\n")
        extra = [l for l in range(max(1, lo - 3), hi + 1) if l not in c]
        for lvl in extra[:8]:
            f = _read_hp_cap(p, hero, unit, lvl, 2)
            if f is None:
                continue
            c[lvl] = f
            print(f"    L{lvl:<3} x{f:.4f}")
        # Same hero, same level, THREE units instead of two.
        f3 = _read_hp_cap(p, hero, unit, lo, 3)
        if f3 is not None:
            print(f"\n    at 3 units instead of 2, L{lo} reads x{f3:.4f} — "
                  + ("the same, so it is a level effect and not a count one"
                     if abs(f3 - c[lo]) < 0.005 else
                     "DIFFERENT, so the figure depends on the unit count and "
                     "is not a\n    per-unit multiplier at all"))

    print("\n  HP multiplier by level, exact\n")
    for (hero, unit), c in curves.items():
        pts = ", ".join(f"L{l}={f:.4f}" for l, f in sorted(c.items()))
        span = max(c.values()) - min(c.values())
        print(f"  {hero:13} {unit:5} {pts}")
        print(f"  {'':13} {'':5} -> "
              + ("FLAT with level" if span < 0.005
                 else "MOVES with level; store the points, do not fit them"))


def exp_terrain(p: Probe) -> None:
    """Each terrain against the same baseline; multipliers fall out as ratios."""
    terrains = p.select_options.get("A.1.terrain") or ["land", "air", "sea"]
    for t in terrains:
        if not t:
            continue
        ov = settings()
        ov.update(duel(1, "inf", 10, "inf", 20, atk_terrain=t, def_terrain=t))
        try:
            record("terrain", {"terrain": t}, p.submit(ov))
        except BareFormReturned as e:
            print(f"  ! terrain={t}: {e}", file=sys.stderr)


def exp_variance(p: Probe, samples: int = 60) -> None:
    """Same battle repeatedly with variance ON, to characterise the roll.

    Question worth answering: is it one roll per unit type per round (as the
    UI copy implies), or per unit? The shape of the distribution tells you.
    """
    ov = settings(variance=True)
    ov.update(duel(1, "inf", 10, "inf", 20))
    for i in range(samples):
        try:
            record("variance", {"sample": i}, p.submit(ov))
        except BareFormReturned as e:
            print(f"  ! sample {i}: {e}", file=sys.stderr)


def effective_units(n: int) -> float:
    """Confirmed stack size factor. Contribution saturates at 35 effective."""
    if n <= 20:
        return float(n)
    k = min(n, 50) - 20
    return 20.0 + k * (60 - k) / 60


TERRAIN_FOR_CLASS = {"land": "land", "air": "air", "naval": "sea"}


def unit_roster(p: "Probe") -> dict[str, str]:
    """unit code -> terrain, read off the form's own optgroups.

    Taken from the live page rather than hardcoded, so a roster change shows
    up as a new row instead of a silent omission.
    """
    out: dict[str, str] = {}
    for name, groups in p.select_groups.items():
        if not name.endswith(".unit"):
            continue
        for label, codes in groups.items():
            terrain = TERRAIN_FOR_CLASS.get(label.strip().lower())
            if terrain:
                for code in codes:
                    out.setdefault(code, terrain)
    return out


def _measure_pair(p: "Probe", code: str, terrain: str,
                  atk_n: int, def_n: int) -> dict[str, Any]:
    """One U-vs-U submission, reduced to per-unit coefficients."""
    payload = settings("1")
    payload.update(duel(1, code, atk_n, code, def_n,
                        atk_terrain=terrain, def_terrain=terrain))
    p.submit(payload)
    detail = dict(p.last_details)
    a, b = detail.get("A.1.1", {}), detail.get("B.1.1", {})
    out: dict[str, Any] = {"atk_n": atk_n, "def_n": def_n, "detail": detail}
    # A is attacking, so A's loss was inflicted by the DEFENDERS, and vice versa.
    if "lost" in a:
        out["dmg_defending"] = a["lost"] / effective_units(def_n)
    if "lost" in b:
        out["dmg_attacking"] = b["lost"] / effective_units(atk_n)
    for slot, n, key in (("A.1.1", atk_n, "hp_from_atk"),
                         ("B.1.1", def_n, "hp_from_def")):
        d = detail.get(slot, {})
        if "pool" in d and n:
            out[key] = d["pool"] / n
    # A stack wiped in the measured round caps its own loss at its pool, which
    # understates the OPPONENT's damage. Track the two sides separately: each
    # coefficient is spoiled only by the wipe of the stack it was read from.
    #   dmg_defending comes from A's loss -> spoiled if A was wiped
    #   dmg_attacking comes from B's loss -> spoiled if B was wiped
    # Max HP survives either way: at exactly 100% lost, pool == lost.
    out["sat_A"] = a.get("pct", 0) >= 99.9
    out["sat_B"] = b.get("pct", 0) >= 99.9
    out["saturated"] = out["sat_A"] or out["sat_B"]
    return out


def pct_rel_error(pct: float) -> float:
    """Relative uncertainty in a percentage the page printed to 3 s.f.

    A 3 s.f. figure carries an absolute uncertainty of half a unit in its last
    place, so its RELATIVE precision depends entirely on the leading digit:
    17.1% is good to 0.29%, but 95.2% is good to 0.05%. Every pool in this
    project is lost/pct, so this is the error bar on max HP.
    """
    if not pct or pct <= 0:
        return float("inf")
    place = math.floor(math.log10(abs(pct))) - 2      # 3 significant figures
    return (0.5 * 10 ** place) / pct


# Below this, the derived max HP is good to better than a tenth of a percent
# and a re-read would spend a live request to move the third decimal.
HP_PRECISION_TARGET = 0.001
# Aim the re-read here: high enough that 3 s.f. is worth ~0.05%, with enough
# headroom that the stack is not wiped (which caps its loss and ruins it).
HP_REREAD_PCT = 0.90


def hp_bounds(d: dict[str, float], n: int) -> tuple[float, float] | None:
    """The interval of max HP consistent with one reading, given how the page
    rounds. Not an estimate — a bracket.

    Both inputs are rounded before we see them: HP lost to 0.1 in the span or
    0.01 in the summary table, and the percentage to three significant figures.
    Max HP is lost / pct / n, so the widest consistent value uses the largest
    HP over the smallest percentage, and the narrowest the other way round.

    An interval is the honest object here because the point estimate cannot
    say whether it is exact. A tank duel printing '37.5%' is exact; one
    printing '17.1%' is not; both look identical, and a re-read chosen on a
    worst-case error bar can therefore land further from the truth than the
    reading it replaced. Intersecting brackets never does.
    """
    lost, pct = d.get("lost"), d.get("pct")
    if not lost or not pct or not n or pct <= 0:
        return None
    u_pct = 0.5 * 10 ** (math.floor(math.log10(abs(pct))) - 2)
    u_lost = 0.005 if d.get("lost_source") == 1.0 else 0.05
    lo_pct, hi_pct = (pct - u_pct) / 100.0, (pct + u_pct) / 100.0
    if lo_pct <= 0:
        return None
    return ((lost - u_lost) / (hi_pct * n), (lost + u_lost) / (lo_pct * n))


def sole_integer_in(bounds: tuple[float, float] | None) -> int | None:
    """The one whole number inside the bracket, if there is exactly one.

    Every unit whose max HP this project has pinned independently has turned
    out to be a whole number — infantry 20, tanks 175, heavy tanks 260, the
    last two confirmed by the stock form's own defaults. So a bracket
    containing exactly one integer identifies it, and one containing several
    identifies nothing. This reports which, rather than rounding and hoping.
    """
    if not bounds:
        return None
    lo, hi = bounds
    candidates = [i for i in range(math.ceil(lo), math.floor(hi) + 1)]
    return candidates[0] if len(candidates) == 1 else None


def _sharpen_max_hp(p: "Probe", code: str, terrain: str,
                    r: dict[str, Any]) -> float | None:
    """Re-read max HP with the defender sized to lose ~90% of its pool.

    HANDOVER §9 step 4 expected the summary table to turn 60.06 / 175.44 /
    260.12 into clean integers. It did not, and the reason is worth recording:
    the table sharpens HP LOST, and for these units the span's HP was already
    exact. A tank duel removes 300.0 of 1750, which the page prints as '17.1%',
    and 300 / 0.171 / 10 = 175.44. The binding constraint is the PERCENTAGE's
    significant figures, not the HP's.

    That is a choice of stack size, not a limit of the site. Damage dealt does
    not depend on the defender's count, so shrinking the defender until it is
    losing ~90% of its pool moves the printed percentage from 17.1% to the high
    eighties, where three significant figures are worth ten times more. One
    request per affected unit, and only for units that need it.
    """
    d = (r.get("detail") or {}).get("B.1.1") or {}
    lost, pct, hp = d.get("lost"), d.get("pct"), r.get("hp_from_def")
    def_n = r.get("def_n")
    if not lost or not pct or not hp or not def_n:
        return None
    r["hp_bounds"] = hp_bounds(d, def_n)
    # Spend the extra request only where the first reading leaves the answer
    # genuinely ambiguous. A bracket that already contains exactly one whole
    # number has identified it, however ugly the midpoint looks: a tank duel
    # reads 175.44, but its bracket is 174.90-175.98, and 175 is the only
    # integer in it. Re-reading that would cost dxter a page view to move a
    # decimal nobody quotes. Courtesy is a design constraint here, not a note.
    if (pct_rel_error(pct) <= HP_PRECISION_TARGET
            or sole_integer_in(r["hp_bounds"]) is not None):
        return None
    want = max(1, round(lost / (HP_REREAD_PCT * hp)))
    if want == def_n:
        return None                      # identical payload, nothing to learn
    try:
        alt = _measure_pair(p, code, terrain, r.get("atk_n") or 10, want)
    except (ValueError, BareFormReturned):
        return None
    b = (alt.get("detail") or {}).get("B.1.1") or {}
    # A wiped stack has its loss capped at its pool, so pct pins to 100% and
    # the reading says only "at least this much". Keep the coarse one instead.
    if b.get("pct", 0) >= 99.9 or not alt.get("hp_from_def"):
        return None
    second = hp_bounds(b, want)
    if not second:
        return None
    first = r.get("hp_bounds")
    lo, hi = second
    if first:
        lo, hi = max(first[0], lo), min(first[1], hi)
        if lo > hi:
            # The two brackets exclude each other, so one of the assumptions
            # behind them is wrong. Report it rather than average two readings
            # that cannot both be of the same quantity.
            print(f"  ! {code}: max-HP brackets from {def_n} and {want} "
                  f"defenders do not overlap ({first} vs {second}). Keeping "
                  f"the first and flagging it.", file=sys.stderr)
            return None
    r["hp_bounds"] = (lo, hi)
    return 0.5 * (lo + hi)


def exp_unit_stats(p: "Probe") -> None:
    """Max HP, attack damage and defence damage for the whole roster.

    U attacking an identical stack of U is compositionally symmetric but role
    asymmetric, so ONE submission gives both coefficients:

        defender's loss / E(attacker count) = U's damage ATTACKING
        attacker's loss / E(defender count) = U's damage DEFENDING

    and either side's pool / its own count = U's max HP. Infantry checked
    against the known result: 10v10 gives 4.0 attacking, 5.0 defending, 20.0 HP.

    Counts stay at 10 so E(n) = n exactly and the size factor cannot confound
    the reading. If a side is wiped in the measured round its loss is capped at
    its pool, so that unit is re-run with lopsided counts to clear the ceiling.
    """
    roster = unit_roster(p)
    if not roster:
        print("  ! No unit optgroups found — cannot classify the roster.")
        return
    print(f"  {len(roster)} unit types from the live form\n")
    print(f"  {'unit':8} {'terrain':8} {'maxHP':>8} {'HP is':>6} "
          f"{'atk/unit':>9} {'def/unit':>9} {'ratio':>7}  note")

    for code, terrain in roster.items():
        note = ""
        try:
            r = _measure_pair(p, code, terrain, 10, 10)
            if r.get("saturated"):
                # Lopsided counts: few attackers cannot wipe many defenders.
                # Only re-run the coefficient that was actually spoiled, and
                # judge each rescue by the one side it is read from.
                note = "re-run unsaturated"
                still = False
                if r.get("sat_B"):          # attack coefficient was capped
                    alt = _measure_pair(p, code, terrain, 4, 20)
                    r["dmg_attacking"] = alt.get("dmg_attacking")
                    r.setdefault("hp_from_def", alt.get("hp_from_def"))
                    still = still or bool(alt.get("sat_B"))
                if r.get("sat_A"):          # defence coefficient was capped
                    alt = _measure_pair(p, code, terrain, 20, 4)
                    r["dmg_defending"] = alt.get("dmg_defending")
                    r.setdefault("hp_from_atk", alt.get("hp_from_atk"))
                    still = still or bool(alt.get("sat_A"))
                if still:
                    note = "STILL SATURATED — treat as a lower bound"
            sharp = _sharpen_max_hp(p, code, terrain, r)
            if sharp:
                r["hp_from_def"], r["hp_precise"] = sharp, True
                note = (note + "; " if note else "") + "HP re-read near 90%"
        except ValueError as e:                 # guard_payload refused it
            print(f"  {code:8} {terrain:8} {'-':>8} {'-':>6} {'-':>9} "
                  f"{'-':>9} {'-':>7}  SKIPPED: {e}".rstrip())
            record("unit_stats", {"unit": code, "terrain": terrain}, {})
            continue
        except BareFormReturned as e:
            print(f"  {code:8} {terrain:8} {'-':>8} {'-':>6} {'-':>9} "
                  f"{'-':>9} {'-':>7}  FAILED: {e}")
            record("unit_stats", {"unit": code, "terrain": terrain,
                                  "error": str(e)}, {})
            continue

        hp = r.get("hp_from_def") or r.get("hp_from_atk")
        atk, dfn = r.get("dmg_attacking"), r.get("dmg_defending")
        ratio = (dfn / atk) if (atk and dfn) else None
        def cell(v: Any, width: int, places: int = 2) -> str:
            return (f"{v:{width}.{places}f}" if isinstance(v, float)
                    else f"{'?':>{width}}")

        bounds = r.get("hp_bounds")
        exact = sole_integer_in(bounds)
        if exact is not None:
            note = (note + "; " if note else "") + f"bracket {bounds[0]:.2f}-" \
                   f"{bounds[1]:.2f} holds one integer"
        print(f"  {code:8} {terrain:8} {cell(hp, 8)} "
              f"{(str(exact) if exact is not None else '?'):>6} "
              f"{cell(atk, 9)} {cell(dfn, 9)} {cell(ratio, 7, 3)}  "
              f"{note}".rstrip())
        record("unit_stats", {"unit": code, "terrain": terrain,
                              "max_hp": hp, "max_hp_bounds": bounds,
                              "max_hp_integer": exact,
                              "dmg_attacking": atk,
                              "dmg_defending": dfn, "note": note},
               {"A.1.1": (r.get("detail", {}).get("A.1.1") or {}).get("lost"),
                "B.1.1": (r.get("detail", {}).get("B.1.1") or {}).get("lost")})


EXPERIMENTS: dict[str, Callable[[Probe], None]] = {
    "unit_stats": exp_unit_stats,
    "mixed_stacks": exp_mixed_stacks,
    "heroes": exp_heroes,
    "stack_limits": exp_stack_limits,
    "hero_scaling": exp_hero_scaling,
    "hero_table": exp_hero_table,
    "hero_levels": exp_hero_levels,
    "hero_caps": exp_hero_caps,
    "stack_ladder": exp_stack_ladder,
    "stack_order": exp_stack_order,
    "hero_output": exp_hero_output,
    "hero_buff_confirm": exp_hero_buff_confirm,
    "allocation": exp_allocation,
    "hero_full": exp_hero_full,
    "hero_hp_cap": exp_hero_hp_cap,
    "buildings": exp_buildings,
    "trenches": exp_trenches,
    "air_vs_ground": exp_air_vs_ground,
    "land_matrix": exp_land_matrix,
    "size_factor": exp_size_factor,
    "hp_scaling": exp_hp_scaling,
    "patrol": exp_patrol,
    "fortress": exp_fortress,
    "terrain": exp_terrain,
    "variance": exp_variance,
}

# Roughly how many live requests each costs, so that `--run all` can say what
# it is about to spend on someone else's ad-supported fan site before it starts
# rather than after. Approximate by design: saturation re-runs add a few.
REQUEST_ESTIMATE: dict[str, int] = {
    "unit_stats": 20, "buildings": 14, "patrol": 18, "mixed_stacks": 8, "heroes": 23, "stack_limits": 4, "hero_scaling": 9, "hero_table": 28, "hero_levels": 16, "hero_caps": 30, "stack_ladder": 9, "stack_order": 5, "hero_output": 21, "hero_buff_confirm": 5, "allocation": 9, "hero_full": 24, "hero_hp_cap": 22, "trenches": 10, "air_vs_ground": 30,
    "land_matrix": 100, "size_factor": 33, "hp_scaling": 10,
    "fortress": 6, "terrain": 5, "variance": 60,
}

# Removed rather than left runnable. All three predate unit_stats, and none of
# them recorded which side a reading came from, so their output merges attack
# and defence coefficients into an average that is neither. A name that used to
# work should say what happened to it instead of "Unknown experiment".
RETIRED: dict[str, str] = {
    "damage_land": "superseded by 'unit_stats' (same-class coefficients, both "
                   "sides labelled) and 'land_matrix' (the off-diagonal)",
    "damage_sea": "superseded by 'unit_stats'; naval pairings are its diagonal",
    "damage_air": "replaced by 'air_vs_ground', which labels each reading by "
                  "side and sizes the defender so it is not wiped",
}


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--run", default=None,
                    help="experiment name, or 'all'. " + ", ".join(EXPERIMENTS))
    ap.add_argument("--dump-fields", action="store_true",
                    help="print the discovered form schema and exit")
    ap.add_argument("--sanity", action="store_true",
                    help="submit the untouched baseline and check it parses")
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    ap.add_argument("--dry-run", action="store_true",
                    help="print payloads instead of sending them")
    ap.add_argument("--insecure", action="store_true",
                    help="skip TLS verification (last resort; see the SSL hint)")
    ap.add_argument("--semantics", action="store_true",
                    help="3 requests that decide whether hpLeft is HP lost or "
                         "HP remaining, and measure the attack/defend split")
    ap.add_argument("--encoding", choices=("urlencoded", "multipart"),
                    default="urlencoded",
                    help="POST body encoding. urlencoded is proven against the "
                         "live server; multipart reproduces the browser exactly")
    ap.add_argument("--save-response", metavar="PATH",
                    help="write every successful response body to PATH "
                         "(overwritten each request; use with --sanity)")
    args = ap.parse_args()

    # Validate the experiment name BEFORE load_form(), which is a live request.
    # A typo used to cost dxter a page view and print its complaint afterwards.
    if args.run and args.run != "all" and args.run not in EXPERIMENTS:
        if args.run in RETIRED:
            print(f"{args.run!r} has been retired: {RETIRED[args.run]}.",
                  file=sys.stderr)
        else:
            print(f"Unknown experiment {args.run!r}. Available: "
                  + ", ".join(EXPERIMENTS), file=sys.stderr)
        return 1

    p = Probe(delay=args.delay, dry_run=args.dry_run, insecure=args.insecure,
              encoding=args.encoding, save_response=args.save_response)
    print(f"Loading form from {BASE_URL} ...")
    fields = p.load_form()
    print(f"Discovered {len(fields)} fields.\n")

    if args.dump_fields:
        print(f"form action -> {p.post_url}  (method {p.form_method})\n")
        for name in sorted(fields):
            opts = p.select_options.get(name)
            suffix = f"   options={opts}" if opts else ""
            print(f"{name:32} = {fields[name]!r}{suffix}")
        print("\nIsolation is by the target field, not distance: A.n.target=B.n "
              "pairs them, target=0 means defend.")
        return 0

    if args.sanity:
        try:
            sane = settings()
            sane.update(duel(1, "inf", 10, "inf", 10))
            readings = p.submit(sane)
        except BareFormReturned as e:
            print(f"SANITY FAILED: {e}", file=sys.stderr)
            body = p.last_response
            print(f"\n  posted to : {p.post_url} ({p.form_method})", file=sys.stderr)
            print(f"  response  : {len(body)} bytes -> {FAILURE_PATH}", file=sys.stderr)
            for marker in ("hpLeft", "hpLost", "Lost ", "died", "oops", "Start Battle"):
                print(f"    contains {marker!r}: {marker in body}", file=sys.stderr)
            return 1
        print(f"SANITY OK: {readings}")
        return 0

    if args.semantics:
        print("--- semantics: what does the hpLeft span actually hold? ---")
        try:
            semantics(p)
        except BareFormReturned as e:
            print(f"SEMANTICS FAILED: {e}", file=sys.stderr)
            return 1
        return 0

    if not args.run:
        ap.print_help()
        return 0

    names = list(EXPERIMENTS) if args.run == "all" else [args.run]
    budget = sum(REQUEST_ESTIMATE.get(n, 0) for n in names)
    if budget:
        print(f"About {budget} live requests (~{budget * args.delay / 60:.1f} "
              f"min at {args.delay}s apart) against someone else's fan site.\n")
    for name in names:
        fn = EXPERIMENTS.get(name)
        if not fn:
            if name in RETIRED:
                print(f"{name!r} has been retired: {RETIRED[name]}.",
                      file=sys.stderr)
            else:
                print(f"Unknown experiment {name!r}", file=sys.stderr)
            return 1
        print(f"--- {name} ---")
        fn(p)

    print(f"\n{p.request_count} requests sent. Results appended to {RESULTS_PATH}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted. Partial results are in results.jsonl.")
        sys.exit(130)
    except urllib.error.URLError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        text = str(exc)
        # An egress allowlist denies the CONNECT itself, so this surfaces as a
        # tunnel/403 failure rather than as anything DNS- or TLS-shaped. Worth
        # naming, because the obvious readings — the site is down, the cert is
        # wrong — both send you somewhere useless.
        if ("403" in text or "tunnel" in text.lower()
                or "Forbidden" in text):
            print("\nThat looks like an egress policy denial, not the site "
                  "being down.", file=sys.stderr)
            print("  Check:  curl -sS -o /dev/null -w '%{http_code}\\n' "
                  "https://dxcalc.com/s1914", file=sys.stderr)
            print("  A cloud session must be STARTED in an environment whose "
                  "allowed-domains list contains dxcalc.com; the policy is "
                  "read once at provisioning and cannot be changed for a "
                  "session already running.", file=sys.stderr)
            print("  Note the apex is the host that matters. www.dxcalc.com "
                  "resolves and is reachable, but the server 301-redirects it "
                  "straight to https://dxcalc.com/, so allowing only the "
                  "subdomain gets you a redirect into a blocked host.",
                  file=sys.stderr)
            sys.exit(1)
        if "CERTIFICATE_VERIFY_FAILED" in text:
            print("\nPython can't find a CA bundle. In order of preference:", file=sys.stderr)
            print("  1. macOS python.org build — run the bundled installer:", file=sys.stderr)
            print("     open '/Applications/Python 3.x/Install Certificates.command'", file=sys.stderr)
            print("  2. pip install certifi   (this script picks it up automatically)", file=sys.stderr)
            print("  3. --insecure            (disables verification; last resort)", file=sys.stderr)
        sys.exit(1)