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
RESULT_SLOT_RE = re.compile(r"^([AB])\.\d+(?:\.[A-Za-z]+)?\.\d+$")
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
    rows 2-8 precisely so a single reading means a single unit type.

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
                # what duel() does to rows 2-8. SETTING one is a silent bug:
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
    for side in ("A", "B"):
        for row in range(2, 9):
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
    print(f"  {'atk':7} {'target':7} {'defN':>5} {'dmg/atk':>9} {'dmg/def':>9} "
          f"{'targetHP':>9}  note")

    matrix: dict[str, dict[str, float]] = {}
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
                    print(f"  {x:7} {y:7} {'-':>5} {'-':>9} {'-':>9} {'-':>9}"
                          f"  SKIPPED: {e}")
                    record(tag, {"atk": x, "target": y, "skipped": str(e)}, {})
                    r = None
                    break
                except BareFormReturned as e:
                    print(f"  {x:7} {y:7} {def_n:>5} {'-':>9} {'-':>9} {'-':>9}"
                          f"  FAILED: {e}")
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

            matrix.setdefault(x, {})[y] = dmg_atk if dmg_atk is not None else float("nan")
            cell = lambda v: f"{v:9.3f}" if isinstance(v, float) else f"{'?':>9}"
            print(f"  {x:7} {y:7} {def_n:>5} {cell(dmg_atk)} {cell(dmg_def)} "
                  f"{cell(target_hp)}  {note}".rstrip())
            record(tag, {"atk": x, "target": y, "atk_n": atk_n, "def_n": def_n,
                         "atk_terrain": atk_terrain, "def_terrain": def_terrain,
                         "dmg_attacking": dmg_atk, "dmg_defending": dmg_def,
                         "target_max_hp": target_hp, "note": note,
                         "atk_label": label_of(p, x),
                         "target_label": label_of(p, y),
                         "detail": d, "summary": dict(p.last_summary)},
                   {"A.1.1": a.get("lost"), "B.1.1": b.get("lost")})

    report_matchups(matrix)


def report_matchups(matrix: dict[str, dict[str, float]]) -> None:
    """Is damage a property of the attacker alone, or of the pairing?"""
    usable = {x: {y: v for y, v in row.items() if v == v}      # drop NaN
              for x, row in matrix.items()}
    usable = {x: row for x, row in usable.items() if row}
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
            print(f"    {x:7} TARGET-DEPENDENT: {lo:.2f} vs {worst} up to "
                  f"{hi:.2f} vs {best} (x{hi / lo:.2f}).")
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


def exp_patrol(p: Probe) -> None:
    """Patrol terrain does 4 ticks of 1/4 damage per round.

    Max Rounds accepts 0.25 / 0.5 / 0.75, which is a finer measuring
    instrument than maxRounds=1 — it isolates a single tick.
    """
    air = roster(p, "air")
    land = roster(p, "land")
    target = land[0] if land else "inf"
    for unit in air:
        for rounds in ("0.25", "0.5", "1"):
            ov = settings(rounds)
            ov.update(duel(1, unit, 1, target, 20,
                           atk_terrain="patrol", def_terrain="land"))
            try:
                record("patrol", {"unit": unit, "rounds": rounds}, p.submit(ov))
            except (BareFormReturned, ValueError) as e:
                print(f"  ! patrol {unit} @{rounds}: {e}", file=sys.stderr)


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
    if levels:
        top = levels[-1]
        got = one(f"attacker trench {top}, defender 0", atk_trench=top)
        if got:
            a = (got["detail"].get("A.1.1") or {}).get("lost")
            if a is not None and atk0:
                same = abs(a / atk0 - 1) <= MOVED_LOST
                print(f"\n  attacker trench L{top}: attacker lost {a:.2f} vs "
                      f"{atk0:.2f} with no trench — "
                      + ("no effect while attacking."
                         if same else "it protects the attacker too."))


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
    for pct in range(10, 101, 10):
        ov = settings()
        ov.update(duel(1, "inf", 10, "inf", 50, atk_hp=f"{pct}%"))
        try:
            record("hp_scaling", {"hp_pct": pct}, p.submit(ov))
        except BareFormReturned as e:
            print(f"  ! hp={pct}%: {e}", file=sys.stderr)


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
    print(f"  {'unit':8} {'terrain':8} {'maxHP':>8} {'atk/unit':>9} "
          f"{'def/unit':>9} {'ratio':>7}  note")

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
        except ValueError as e:                 # guard_payload refused it
            print(f"  {code:8} {terrain:8} {'-':>8} {'-':>9} {'-':>9} {'-':>7}"
                  f"  SKIPPED: {e}".rstrip())
            record("unit_stats", {"unit": code, "terrain": terrain}, {})
            continue
        except BareFormReturned as e:
            print(f"  {code:8} {terrain:8} {'-':>8} {'-':>9} {'-':>9} {'-':>7}"
                  f"  FAILED: {e}")
            record("unit_stats", {"unit": code, "terrain": terrain,
                                  "error": str(e)}, {})
            continue

        hp = r.get("hp_from_def") or r.get("hp_from_atk")
        atk, dfn = r.get("dmg_attacking"), r.get("dmg_defending")
        ratio = (dfn / atk) if (atk and dfn) else None
        def cell(v: Any, width: int, places: int = 2) -> str:
            return (f"{v:{width}.{places}f}" if isinstance(v, float)
                    else f"{'?':>{width}}")

        print(f"  {code:8} {terrain:8} {cell(hp, 8)} {cell(atk, 9)} "
              f"{cell(dfn, 9)} {cell(ratio, 7, 3)}  {note}".rstrip())
        record("unit_stats", {"unit": code, "terrain": terrain,
                              "max_hp": hp, "dmg_attacking": atk,
                              "dmg_defending": dfn, "note": note},
               {"A.1.1": (r.get("detail", {}).get("A.1.1") or {}).get("lost"),
                "B.1.1": (r.get("detail", {}).get("B.1.1") or {}).get("lost")})


EXPERIMENTS: dict[str, Callable[[Probe], None]] = {
    "unit_stats": exp_unit_stats,
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
    "unit_stats": 17, "buildings": 14, "trenches": 10, "air_vs_ground": 30,
    "land_matrix": 100, "size_factor": 33, "hp_scaling": 10, "patrol": 12,
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