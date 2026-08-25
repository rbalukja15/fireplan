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
    - (CLOSED) What 'hours' and the resource columns of the summary table mean.
      They are the recovery bill: resources and cash to replace what was
      destroyed, and hours to do it in. Both are linear in UNIT EQUIVALENTS,
      ue = HP lost / current per-unit HP, and NOT in HP lost -- the trench
      sweep separates them (40.0 HP lost at every level, hours falling 6 to 4),
      as does a 10%-HP stack that is billed identically to a healthy one.
      Resources round; hours floor, once over the stack. Unit rows and hero
      rows count, building rows do not. See --run repair_cost / hero_repair and
      the REPAIR_COST note in web/data.js. This entry sat here unanswered for
      the whole project while the numbers to answer it accumulated in
      results.jsonl, which is the real lesson.

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
    recorded rather than interpreted, so a later session has the data without
    spending requests to get it. That paid off exactly as intended: they went
    unread for the whole project, and when they were finally looked at, 256
    complete resource rows and 2,719 'hours' readings were already on disk and
    the entire law fell out of them for free. See exp_repair_cost.

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
    # a column dxter adds later shows up as data instead of vanishing. That
    # provision earned itself: the site later added an "HP final" column, and
    # it arrived as data instead of being silently discarded.
    #
    # The lookup IGNORES INTERNAL WHITESPACE, and it has to. The same column is
    # served as "% lost" in fortress_result.html and as "%lost" in
    # multi_stack_response.html, so a literal match slugified the two spellings
    # to DIFFERENT keys -- "pct_lost" on 128 stored rows and "lost" on 284.
    # Worse, that second key collides with the span reading's "lost", which is
    # HP, not a percentage. Nothing downstream had read it yet, so nothing was
    # wrong in results.jsonl beyond a name; but a percentage filed under "lost"
    # beside HP filed under "lost" is precisely the sort of thing that is
    # noticed six months later by the wrong number in a graph. Both spellings
    # now land on pct_lost. Rows already on disk are left exactly as captured
    # -- see summary_pct_lost() for reading either.
    COLUMNS = {"hplost": "hp_lost", "%lost": "pct_lost", "hpfinal": "hp_final"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.summaries: dict[str, dict[str, float]] = {}
        self.extra_rows: dict[str, list[list[str]]] = {}
        # army letter -> the stack ids seen under it, in document order
        self._stacks_seen: dict[str, list[str]] = {}
        self._stack: str | None = None
        self._in_table = False
        self._rows: list[list[str]] = []
        self._cells: list[str] | None = None
        self._buf: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if STACK_ID_RE.match(a.get("id", "")):
            self._stack = a.get("id", "")
            self._stacks_seen.setdefault(self._stack.split(".")[0],
                                         []).append(self._stack)
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
        squashed = re.sub(r"\s+", "", h)
        if squashed in cls.COLUMNS:
            return cls.COLUMNS[squashed]
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
            # THE TABLE IS AN ARMY TOTAL, not a stack total. There is exactly
            # ONE per army, after all of that army's stacks -- and with one
            # stack per army, which is every reading this project took for its
            # first 2,585, "the army total" and "this stack's total" are the
            # same number. Field two stacks and they are not: the table that
            # follows A.2 carries A.1 + A.2, and the nearest-preceding-stack
            # rule hands it to A.2 alone.
            #
            # Nothing here silently changed key. The army total is stored under
            # its ARMY, and ALSO under the stack when that army has exactly one
            # -- where it is literally true -- so every existing reader and
            # every row already in results.jsonl keeps working.
            army = self._stack.split(".")[0]
            self.summaries[army] = row
            if len(self._stacks_seen.get(army, ())) == 1:
                self.summaries[self._stack] = row
            else:
                self.summaries.pop(f"{army}.1", None)
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


ARMY_ID_RE = re.compile(r"^[AB]$")


def army_of(key: str) -> str:
    """'A.1.1' -> 'A', 'B.2' -> 'B', 'A' -> 'A'."""
    return key.split(".")[0]


def summary_pct_lost(row: dict[str, float]) -> float | None:
    """The '% lost' column under either spelling the site has served.

    Rows captured before the header lost its space are filed under 'lost';
    rows captured after are filed under 'pct_lost'. Neither file is rewritten
    -- results.jsonl records what the parser saw at capture time, and editing
    it after the fact is how a measurement archive stops being evidence. Read
    through this instead of reaching for either key directly.
    """
    if "pct_lost" in row:
        return row["pct_lost"]
    return row.get("lost")


def refine_details(details: dict[str, dict[str, float]],
                   summaries: dict[str, dict[str, float]],
                   quiet: bool = False) -> dict[str, dict[str, float]]:
    """Upgrade span readings with the summary table's extra digit, where safe.

    The table gives an ARMY TOTAL over its unit rows; the spans give the split.
    So the table can only replace a span when the army has exactly one unit
    row with a reading — which is every experiment here, because duel() blanks
    rows 2-15 precisely so a single reading means a single unit type, and until
    exp_multi_stack every army fielded exactly one stack. Field two and the
    total is real but no longer divisible, so the spans are left alone: the
    cross-check below still runs, and still proves the association, but there
    is nothing to substitute.

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
    seen: set[str] = set()
    for stack, summary in summaries.items():
        total = summary.get("hp_lost")
        if total is None:
            continue
        # A key may be an ARMY ('A') or a stack ('A.1'). The table is an army
        # total either way; the stack form is only an alias, kept for armies
        # that field exactly one stack. Handle both, and do not process the
        # same army twice when both keys are present -- the substitution is
        # idempotent, but the warning it prints on a mismatch is not, and a
        # doubled warning reads like two independent failures.
        army = army_of(stack)
        if army in seen:
            continue
        seen.add(army)
        is_army_key = ARMY_ID_RE.match(stack) is not None
        # Building rows carry delta notation and ARE excluded -- the fortress
        # response proves the table leaves them out. A HERO row is the
        # opposite, and it was guessed wrong before it was measured: the hero
        # renders an ordinary "Lost 2.1 HP (5.19%)" span and the table COUNTS
        # it. Every hero request reconciles exactly once it is included
        # (77.90 units + 2.10 hero = 80.00 table, on all sixteen). So a hero
        # belongs to its stack in a way a building does not.
        units = [s for s, d in details.items()
                 if (army_of(s) == army if is_army_key else stack_of(s) == stack)
                 and not d.get("delta") and "lost" in d]
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

def settings(rounds: str | float = "1", variance: bool = False,
             update_counts: bool = False) -> dict[str, str]:
    """Global form switches.

    simulateVariance MUST be off for a deterministic reading — with it on the
    server rolls the +/-10% and every measurement becomes a sample rather than
    the expected value. updateCounts and newWindow are off so the response is
    a plain results page.
    """
    return {
        "maxRounds": str(rounds),
        "simulateVariance": "on" if variance else "",
        # UPDATE COUNTS rewrites the returned FORM with the post-battle unit
        # counts and HP instead of echoing what was sent. It is off by default
        # because every experiment here reads the result spans, and it stayed
        # off for the whole project -- so the server's own survivor counts, the
        # one quantity this rig has always INFERRED, were never once read.
        "updateCounts": "on" if update_counts else "",
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


# Set by main() from --dry-run. A dry run sends nothing, so every experiment
# that calls record() unconditionally -- which is all of them -- was appending
# rows of NOTHING to the measurement archive. Eighteen went in on the first dry
# run of exp_bughunt before a single request was sent. They are not wrong
# measurements, they are not measurements at all, and the difference matters
# because the archive is meant to be evidence: a reader replaying it cannot
# tell "the site returned no reading" from "nobody asked the site".
#
# Empty readings ARE meaningful in two experiments -- hero_hp_cap and hero_caps
# measure server REFUSALS, and 152 rows there are legitimately blank -- so the
# guard cannot key on the readings being empty. It keys on whether a request
# was actually sent.
DRY_RUN = False


def record(tag: str, meta: dict[str, Any], readings: dict[str, float]) -> None:
    if DRY_RUN:
        print(f"  [dry run] {tag} NOT recorded -> {readings}")
        return
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


# The 22 hero codes exactly as addHero()'s <option value=...> template lists
# them. The codes are facts about the form's field values; bytro.js itself is
# dxter's copyrighted client JS and is deliberately not in this repo.
HERO_CODES = [
    "rbaron", "thaden", "alvin", "lucien", "lucien_g", "johan", "pershing",
    "otto", "togo", "togo_b", "tatiana", "tatiana_home", "joffre_home",
    "joffre", "marco", "hank", "kangal", "allen", "georg", "larab",
    "maeve", "ivan",
]


def hero_options() -> list[str]:
    """The hero codes, read out of the page's own addHero() template.

    They are not on the GET form -- addHero() injects them client-side, exactly
    like a building row -- so they come from bytro.js when a local copy of it
    sits next to this script (save https://dxcalc.com/js/bytro.js to refresh
    the roster), and from the HERO_CODES transcription otherwise.
    """
    try:
        js = open("bytro.js").read()
    except OSError:
        return list(HERO_CODES)
    block = js[js.find("hero.abb"):js.find("hero.lvl")]
    return re.findall(r'<option value="([^"]+)"', block) or list(HERO_CODES)


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
        print("  ! no hero list: bytro.js is not in the repo (it is dxter's", file=sys.stderr)
        print("    copyrighted client JS). Save https://dxcalc.com/js/bytro.js", file=sys.stderr)
        print("    next to this script to run the hero experiment.", file=sys.stderr)
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
# The hero's attack value when ATTACKING. Different from the defending figure
# for thirteen of sixteen -- a hero has two columns exactly as a unit does, and
# every "A" this project measured before 2026-08-19 is the defending one.
# Each hero's real level cap, from the server's own refusal (exp_hero_caps).
HERO_MAX_LEVEL: dict[str, int] = {
    "kangal": 10, "joffre": 15, "joffre_home": 15, "marco": 10, "allen": 15,
    "larab": 20, "alvin": 20, "lucien": 15, "lucien_g": 15, "pershing": 20,
    "georg": 20, "tatiana": 20, "hank": 10, "johan": 20, "tatiana_home": 20,
    "maeve": 15,
}

HERO_ATK_ATTACKING: dict[str, float] = {
    "alvin": 25.00, "lucien": 8.00, "lucien_g": 8.00, "johan": 4.00,
    "pershing": 62.00, "tatiana": 45.60, "tatiana_home": 10.00,
    "joffre_home": 4.00, "joffre": 4.00, "marco": 24.60, "hank": 5.00,
    "kangal": 10.00, "allen": 29.60, "georg": 16.80, "larab": 45.00,
    "maeve": 4.00,
}

# Which side a hero's OUTPUT multiplier acts on. alvin and hank apply theirs
# attacking and defending alike; joffre_home and kangal only when defending.
HERO_BUFF_CHANNEL: dict[str, str] = {
    "alvin": "both", "hank": "both",
    "joffre_home": "defence", "kangal": "defence",
}

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


# The six the server refuses on a land stack, and the terrain each is presumed
# to belong to. Presumed, not known: that is what the experiment is for.
HERO_OTHER_TERRAIN: dict[str, str] = {
    "rbaron": "air", "thaden": "air",
    "otto": "sea", "togo": "sea", "togo_b": "sea", "ivan": "sea",
}


def exp_hero_sides(p: Probe) -> None:
    """Two holes left in the hero model: attacking, and the other two terrains.

    ATTACKING. Every hero reading in this project put the hero on the DEFENDING
    side. The model applies its own attack A and its per-type multiplier to
    whichever side carries it, which is an assumption nobody has tested -- and
    the attack and defence coefficient columns are different numbers, so the
    prediction is different too. If A or the buff behaved differently on
    attack, every attacking figure in the app would be wrong and nothing would
    say so.

    THE OTHER SIX. rbaron, thaden, otto, togo, togo_b and ivan are refused on a
    land stack. What they do on their own terrain has never been submitted
    once, so the app tells the user "nothing measured" -- accurate, and worth
    only one request each to improve.
    """
    print("\n  1. the same hero, attacking instead of defending\n")
    # TWO attacker configurations, because one cannot separate the hero's own
    # attack from its multiplier -- the identical confound hero_table hit when
    # it read a single stack size, and the reason that experiment uses two.
    #
    #   plain  none of the types any of these heroes buffs, so the excess is
    #          the hero's own attack alone
    #   buffed all nine, so the excess is that plus the multiplier's effect
    #
    # The first draft of this experiment read only the second and reported four
    # heroes as "DIFFERS", which is true and says nothing about which term
    # moved. One of them came out with a NEGATIVE own-attack, which is the
    # signature of a confound rather than a finding.
    PLAIN = ["cav", "lart", "art", "rrg", "lt", "ht"]
    configs = {"plain": [(u, 2) for u in PLAIN],
               "buffed": [(u, 2) for u in LAND_NINE]}
    print(f"  Attacker: {len(PLAIN)} types with no buff between them, then all "
          f"nine. Defender: 60 heavy tanks.\n")

    def attack_once(hero: str | None, stack: list[tuple[str, int]]) -> float | None:
        ov = settings()
        ov.update(duel(1, stack[0][0], stack[0][1], "ht", 60))
        ov.update(composite(1, "A", stack))
        create = composite_fields("A", 1, len(stack))
        if hero:
            ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: "10",
                       HERO_ATK_FIELDS[2]: "100%"})
            create = create + HERO_ATK_FIELDS
        try:
            p.submit(ov, create=create)
        except (BareFormReturned, ValueError) as e:
            print(f"  ! attacking {hero or 'no hero'}: {e}", file=sys.stderr)
            record("hero_sides", {"side": "A", "hero": hero, "rows": stack,
                                  "error": str(e)}, {})
            return None
        d = dict(p.last_details)
        record("hero_sides", {"side": "A", "hero": hero, "level": 10,
                              "rows": stack, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.1") or {}
        if b.get("lost") is None:
            return None
        if (b.get("pct") or 0) >= 99.9:
            print(f"  ! attacking {hero}: DEFENDER WIPED, discarded",
                  file=sys.stderr)
            return None
        return b["lost"]

    bases: dict[str, float] = {}
    for name, stack in configs.items():
        got = attack_once(None, stack)
        want = sum(ATK_COEF[u] * c for u, c in stack)
        if got is None:
            print(f"  baseline {name}: did not read")
            continue
        bases[name] = got
        print(f"  baseline {name:7} {got:9.2f} measured, {want:8.2f} predicted"
              + ("  ok" if abs(got - want) / want < 0.01 else
                 f"  OFF by {100 * abs(got - want) / want:.2f}% — read nothing "
                 f"below until that is explained"))
    print()
    print(f"  {'hero':14} {'A attacking':>12} {'A defending':>12}  same?")
    a_atk: dict[str, float] = {}
    for hero in hero_options():
        if hero not in MEASURED_HEROES:
            continue
        got = attack_once(hero, configs["plain"])
        if got is None or "plain" not in bases:
            print(f"  {hero:14} {'—':>12}")
            continue
        a_atk[hero] = got - bases["plain"]
        a_def, _ = MEASURED_HEROES[hero]
        print(f"  {hero:14} {a_atk[hero]:12.2f} {a_def:12.2f}  "
              + ("yes" if abs(a_atk[hero] - a_def) < 0.05 else "NO"))
    if a_atk and all(abs(v - MEASURED_HEROES[h][0]) < 0.05
                     for h, v in a_atk.items()):
        print("\n  A HERO HAS ONE ATTACK VALUE — the figure decomposed on "
              "defence carries over.")
    elif a_atk:
        print("\n  A HERO HAS TWO VALUES, attack and defence, exactly as a "
              "unit does. Everything\n  this project calls 'A' is the "
              "DEFENDING one; the attacking column is new.")

    print(f"\n  {'hero':14} {'buff term':>10} {'expected':>9}  "
          f"does the multiplier carry over?")
    for hero in sorted(HERO_OUTPUT_CURVES):
        if hero not in a_atk:
            continue
        got = attack_once(hero, configs["buffed"])
        if got is None or "buffed" not in bases:
            print(f"  {hero:14} {'—':>10}")
            continue
        buff_term = (got - bases["buffed"]) - a_atk[hero]
        want = sum((_curve_at(HERO_OUTPUT_CURVES.get(hero, {}).get(u), 10)
                    - 1.0) * ATK_COEF[u] * 2
                   for u in HERO_OUTPUT_CURVES.get(hero, {}))
        print(f"  {hero:14} {buff_term:10.2f} {want:9.2f}  "
              + ("yes — the same multiplier applies attacking"
                 if abs(buff_term - want) <= 0.2 else
                 ("NO — it is a DEFENCE-ONLY buff" if abs(buff_term) <= 0.2
                  else f"differs by {buff_term - want:+.2f}, neither the "
                       f"defending figure nor zero")))

    print("\n  2. the six heroes the server refuses on land\n")
    print(f"  {'hero':13} {'terrain':7} {'output':>9} {'excess':>8}  result")
    for terrain, atk, n, dfn, dn in (("air", "tac", 10, "inf", 40),
                                     ("sea", "cl", 10, "bb", 30)):
        who = [h for h, t in HERO_OTHER_TERRAIN.items() if t == terrain]
        base2 = None
        for hero in [None] + who:
            ov = settings()
            ov.update(duel(1, atk, n, dfn, dn, atk_terrain=terrain,
                           def_terrain="land" if terrain == "air" else "sea"))
            create: tuple[str, ...] = ()
            if hero:
                ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: "10",
                           HERO_ATK_FIELDS[2]: "100%"})
                create = HERO_ATK_FIELDS
            try:
                p.submit(ov, create=create)
            except (BareFormReturned, ValueError) as e:
                print(f"  {str(hero):13} {terrain:7} {'—':>9} {'—':>8}  "
                      f"REFUSED: {str(e)[:44]}")
                record("hero_sides", {"side": "A", "hero": hero,
                                      "terrain": terrain, "error": str(e)}, {})
                continue
            d = dict(p.last_details)
            record("hero_sides", {"side": "A", "hero": hero,
                                  "terrain": terrain, "level": 10,
                                  "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            out = (d.get("B.1.1") or {}).get("lost")
            if out is None:
                print(f"  {str(hero):13} {terrain:7} {'—':>9} {'—':>8}  "
                      f"no defender row")
                continue
            if hero is None:
                base2 = out
                print(f"  {'(none)':13} {terrain:7} {out:9.2f} {'—':>8}  "
                      f"baseline")
                continue
            ex = out - (base2 or 0.0)
            print(f"  {hero:13} {terrain:7} {out:9.2f} {ex:8.2f}  "
                  + ("accepted, and it CHANGES the battle" if abs(ex) > 0.2
                     else "accepted but changed nothing measurable here"))


def _curve_at(curve: dict[int, float] | None, level: int) -> float:
    """A measured curve read at one level, interpolated, never extrapolated."""
    if not curve:
        return 1.0
    if level in curve:
        return curve[level]
    pts = sorted(curve)
    below = [x for x in pts if x < level]
    above = [x for x in pts if x > level]
    if not below:
        return curve[pts[0]]
    if not above:
        return curve[pts[-1]]
    lo, hi = below[-1], above[0]
    return curve[lo] + (level - lo) / (hi - lo) * (curve[hi] - curve[lo])


def exp_multi_round(p: Probe) -> None:
    """What actually happens between rounds. EVERY reading on disk is one round.

    The app iterates: it recomputes each side's output from the survivors, once
    per round, and carries HP across. Not one line of that is measured. Three
    separate things could be wrong and all of them would look plausible:

      * whether E(n) re-evaluates on the SURVIVORS or stays at the opening count
      * whether m(f) re-evaluates as the pool drains, or is fixed at round one
      * whether a wiped side stops contributing, and on which round

    A long battle separates them, because the three predictions diverge further
    with every round. 50 infantry a side lasts six or seven rounds and loses
    units every one of them, so by round 5 "E on survivors" and "E fixed" are
    far apart.
    """
    print("\n  50 infantry a side, the same battle read at increasing "
          "maxRounds.\n")
    print(f"  {'rounds':>6} {'A lost':>9} {'A died':>7} {'B lost':>9} "
          f"{'B died':>7}   per-round delta")
    seen: list[tuple[int, float, float, float, float]] = []
    for rounds in (1, 2, 3, 4, 5, 6, 8, 10):
        ov = settings(rounds=rounds)
        ov.update(duel(1, "inf", 50, "inf", 50))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  ! rounds={rounds}: {e}", file=sys.stderr)
            record("multi_round", {"rounds": rounds, "error": str(e)}, {})
            continue
        d = dict(p.last_details)
        record("multi_round", {"rounds": rounds, "atk": ("inf", 50),
                               "def": ("inf", 50), "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = d.get("A.1.1") or {}
        b = d.get("B.1.1") or {}
        if a.get("lost") is None or b.get("lost") is None:
            print(f"  {rounds:>6} {'—':>9}")
            continue
        prev = seen[-1] if seen else None
        delta = (f"A +{a['lost'] - prev[1]:6.2f}  B +{b['lost'] - prev[3]:6.2f}"
                 if prev else "")
        seen.append((rounds, a["lost"], a.get("died", 0), b["lost"],
                     b.get("died", 0)))
        print(f"  {rounds:>6} {a['lost']:9.2f} {a.get('died', 0):7.0f} "
              f"{b['lost']:9.2f} {b.get('died', 0):7.0f}   {delta}")

    if len(seen) < 3:
        print("\n  NO VERDICT — too few rounds read.")
        return

    # Four candidate laws, each iterated exactly as the app would.
    #
    # The survivor count is the thing that separates them. A stack that has
    # lost 273.43 of 1000 HP has 36.33 units' worth of HP left, not 37 whole
    # units and not 36 -- and the difference compounds every round.
    def run(n: int, mode: str) -> float:
        hp, atk, dfn = MEASURED_UNITS["inf"][0], 4.0, 5.0
        pool = 50 * hp
        a_lost = b_lost = 0.0
        for _ in range(n):
            a_n = ((pool - a_lost) / hp if mode != "integer"
                   else 50 - int(a_lost // hp))
            b_n = ((pool - b_lost) / hp if mode != "integer"
                   else 50 - int(b_lost // hp))
            if a_n <= 0 or b_n <= 0:
                break
            a_out = atk * effective_units(a_n)
            b_out = dfn * effective_units(b_n)
            if mode == "post":
                # Air's law: evaluate on whoever is left AFTER this round.
                a_n2 = max(0.0, (pool - a_lost - b_out) / hp)
                b_n2 = max(0.0, (pool - b_lost - a_out) / hp)
                a_out, b_out = atk * effective_units(a_n2), dfn * effective_units(b_n2)
            elif mode == "m_f":
                a_out *= 0.05 + 0.95 * (pool - a_lost) / pool
                b_out *= 0.05 + 0.95 * (pool - b_lost) / pool
            a_lost = min(pool, a_lost + b_out)
            b_lost = min(pool, b_lost + a_out)
        return a_lost

    models = ("fractional", "integer", "post", "m_f")
    print(f"\n  {'rounds':>6} {'A measured':>11} "
          + " ".join(f"{m:>12}" for m in models))
    errs = {m: 0.0 for m in models}
    for rounds, a_lost, _, _, _ in seen:
        cells = []
        for m in models:
            pred = run(rounds, m)
            cells.append(f"{pred:12.2f}")
            errs[m] = max(errs[m], abs(pred - a_lost) / max(a_lost, 1))
        print(f"  {rounds:>6} {a_lost:11.2f} " + " ".join(cells))
    print()
    for m in models:
        print(f"    {m:12} worst error {100 * errs[m]:7.3f}%")
    best = min(errs, key=errs.get)
    names = {
        "fractional": "each round's output is coefficient x E(pool / maxHP), "
                      "evaluated BEFORE that round's\n  damage lands. The "
                      "survivor count is FRACTIONAL -- a stack holding 726.57 "
                      "HP counts as\n  36.33 units, not 37 and not 36.",
        "integer": "the survivor count is whole units, from the reported death "
                   "count",
        "post": "output is evaluated on whoever is left AFTER the round, as in "
                "air",
        "m_f": "m(f) attenuates each round as the pool drains",
    }
    if errs[best] <= 0.005:
        print(f"\n  VERDICT: {names[best]}")
    elif errs[best] <= 0.01:
        print(f"\n  BEST FIT, NOT EXACT: {names[best]}\n"
              f"  Worst error {100 * errs[best]:.3f}%, against "
              + ", ".join(f"{m} {100 * errs[m]:.2f}%"
                          for m in models if m != best)
              + ".\n  Rounds 1 and 2 are exact and the residual appears from "
              "round 3, growing then\n  shrinking — a small systematic term "
              "this does not capture. Multi-round results\n  must be labelled "
              "ESTIMATED, not measured.")
    else:
        print(f"\n  VERDICT: none of the four fits (best {best} at "
              f"{100 * errs[best]:.2f}%). The measured column is the finding.")


def exp_terrain(p: Probe) -> None:
    """Each terrain against the same baseline, and what sea does to a land unit.

    THE DISCRIMINATOR. Infantry in sea terrain deal 20 and 10 where they deal
    100 and 40 on land -- ratios of 0.20 and 0.25, which are not the same
    number. That kills "sea is a multiplier" unless it is a different
    multiplier per side, and it is exactly what a FLAT coefficient of 1.0 looks
    like: 1.0 x E(20) = 20 and 1.0 x E(10) = 10, with infantry's own 5.0 and
    4.0 discarded.

    A second unit type separates the two outright. Cavalry attack at 15.0 and
    defend at 7.5, so a flat 1.0 predicts the same 20 and 10 as infantry, while
    any multiplier predicts figures three to four times larger.
    """
    terrains = p.select_options.get("A.1.terrain") or ["land", "air", "sea"]
    base: dict[str, tuple[float, float]] = {}
    for t in terrains:
        if not t:
            continue
        ov = settings()
        ov.update(duel(1, "inf", 10, "inf", 20, atk_terrain=t, def_terrain=t))
        try:
            r = record("terrain", {"terrain": t, "unit": "inf"}, p.submit(ov))
        except BareFormReturned as e:
            print(f"  ! terrain={t}: {e}", file=sys.stderr)
            record("terrain", {"terrain": t, "unit": "inf",
                               "error": str(e)}, {})
            continue
        d = dict(p.last_details)
        a = (d.get("A.1.1") or {}).get("lost")
        b = (d.get("B.1.1") or {}).get("lost")
        if a is not None and b is not None:
            base[t] = (a, b)

    print(f"\n  {'terrain':9} {'A lost':>8} {'B lost':>8}   "
          f"(A lost is the DEFENDER's output, B lost the ATTACKER's)")
    for t, (a, b) in base.items():
        print(f"  {t:9} {a:8.2f} {b:8.2f}")

    wet = [t for t in base if t in ("sea", "debark")]
    if not wet:
        print("\n  No sea reading; nothing to separate.")
        return
    print(f"\n  Now cavalry, which attacks at 15.0 and defends at 7.5 against "
          f"infantry's 4.0 and 5.0.\n")
    print(f"  {'terrain':9} {'A lost':>8} {'B lost':>8} {'flat 1.0':>9} "
          f"{'x land ratio':>13}")
    for t in wet:
        ov = settings()
        ov.update(duel(1, "cav", 10, "cav", 20, atk_terrain=t, def_terrain=t))
        try:
            p.submit(ov)
        except BareFormReturned as e:
            print(f"  ! terrain={t} cav: {e}", file=sys.stderr)
            record("terrain", {"terrain": t, "unit": "cav",
                               "error": str(e)}, {})
            continue
        d = dict(p.last_details)
        record("terrain", {"terrain": t, "unit": "cav", "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = (d.get("A.1.1") or {}).get("lost")
        b = (d.get("B.1.1") or {}).get("lost")
        if a is None or b is None:
            continue
        flat = effective_units(20) * 1.0
        ratio = base[t][0] / base["land"][0] if "land" in base else 0
        scaled = MEASURED_UNITS["cav"][2] * effective_units(20) * ratio
        print(f"  {t:9} {a:8.2f} {b:8.2f} {flat:9.2f} {scaled:13.2f}")
        if abs(a - flat) <= 0.05:
            print(f"\n  VERDICT: {t} replaces a land unit's coefficients with "
                  f"a FLAT 1.0 on both sides.\n  It is not a multiplier — "
                  f"cavalry and infantry deal the identical figure, which no\n"
                  f"  scaling of two different stats can produce. An embarked "
                  f"land unit fights exactly\n  as well as a convoy, which is "
                  f"1.0/1.0 in the unit table.")
        elif abs(a - scaled) <= 0.05:
            print(f"\n  VERDICT: {t} SCALES the unit's own coefficients by "
                  f"{ratio:.3f}.")
        else:
            print(f"\n  VERDICT: neither flat nor a scaling of the land "
                  f"figure. The table above is the finding.")


def exp_hero_curves(p: Probe) -> None:
    """Fill in every hero level the curves skipped.

    Curves were read at 1, 5, 10, 15 and 20 and the app interpolates between
    them. pershing's infantry HP curve is the standing proof that a gap can
    hide a step: it drops from 1.70 to 1.10 between levels 5 and 6, which no
    interpolation would ever suggest. Every other curve has the same shape of
    hole in it.

    HP goes through the refusal, which is exact. Output goes through the
    nine-type stack, which is a subtraction against a baseline.
    """
    print("\n  1. HP curves, from the server's refusal (exact)\n")
    for hero, unit in HERO_HP_PAIRS:
        known = HERO_HP_CURVES.get(hero, {}).get(unit, {})
        cap = HERO_MAX_LEVEL.get(hero, 20)
        missing = [l for l in range(1, cap + 1) if l not in known]
        if not missing:
            print(f"  {hero:13} {unit:5} complete")
            continue
        got = dict(known)
        for lvl in missing:
            f = _read_hp_cap(p, hero, unit, lvl, 2)
            if f is not None:
                got[lvl] = f
        pts = ", ".join(f"{l}:{got[l]:.2f}" for l in sorted(got))
        print(f"  {hero:13} {unit:5} {pts}")
        steps = [(a, b) for a, b in zip(sorted(got), sorted(got)[1:])
                 if abs(got[b] - got[a]) > 0.05 and b - a == 1]
        if steps:
            print(f"  {'':13} {'':5} STEPS at "
                  + ", ".join(f"L{a}->L{b}" for a, b in steps))

    print("\n  2. output curves, against the nine-type stack\n")
    stack = [(u, 2) for u in LAND_NINE]
    base = _defender_output(p, stack)
    if not base:
        print("  NO VERDICT — baseline did not read.")
        return
    for hero, curves in HERO_OUTPUT_CURVES.items():
        cap = HERO_MAX_LEVEL.get(hero, 20)
        target = next((u for u in curves if u != "inf"), None) or "inf"
        known = curves[target]
        missing = [l for l in range(1, cap + 1) if l not in known]
        got = dict(known)
        for lvl in missing:
            r = _defender_output(p, stack, hero=hero, level=lvl)
            if not r:
                continue
            a, _ = MEASURED_HEROES[hero]
            resid = r["out"] - base["out"] - a
            if target != "inf":
                resid -= (_curve_at(curves.get("inf"), lvl) - 1.0) * DEF_COEF["inf"] * 2
            got[lvl] = 1.0 + resid / (DEF_COEF[target] * 2)
        record("hero_curves", {"hero": hero, "unit": target, "curve": got}, {})
        print(f"  {hero:13} {target:5} "
              + ", ".join(f"{l}:{got[l]:.2f}" for l in sorted(got)))


def exp_offdiag(p: Probe) -> None:
    """Single-type land duels off the diagonal, to confirm what mixtures imply.

    The allocation sweep showed a land attacker's TOTAL does not depend on its
    target, but every reading behind that was a MIXED defender or a mixed
    attacker. One unit type against one different unit type confirms it
    directly, and it is the cheapest remaining doubt in the land model.
    """
    pairs = [("inf", "ht"), ("ht", "inf"), ("lart", "st"), ("st", "lart"),
             ("cav", "rrg"), ("rrg", "cav"), ("ac", "lt"), ("lt", "ac")]
    print(f"\n  {'attacker':9} {'target':7} {'measured':>9} {'diagonal x E(n)':>16} "
          f"{'err':>7}")
    worst = 0.0
    seen_any = False
    for atk, dfn in pairs:
        n = max(2, int(90 / MEASURED_UNITS[atk][1]) + 1)
        dn = 60
        ov = settings()
        ov.update(duel(1, atk, n, dfn, dn))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  ! {atk} vs {dfn}: {e}", file=sys.stderr)
            continue
        d = dict(p.last_details)
        record("offdiag", {"attacker": atk, "atk_n": n, "target": dfn,
                           "def_n": dn, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.1") or {}
        if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
            print(f"  {atk:9} {dfn:7} {'—':>9}  (wiped or unread)")
            continue
        want = MEASURED_UNITS[atk][1] * effective_units(n)
        e = abs(b["lost"] - want) / want
        worst = max(worst, e)
        seen_any = True
        print(f"  {atk:9} {dfn:7} {b['lost']:9.2f} {want:16.2f} {100 * e:6.2f}%")
    # `if worst:` was falsy at exactly 0.00% -- a perfect result printed no
    # verdict at all, which is the one outcome you most want stated.
    if seen_any:
        print(f"\n  {'CONFIRMED' if worst <= 0.01 else 'REFUTED'}: a land "
              f"attacker's coefficient is target-independent "
              f"(worst {100 * worst:.2f}%).")


def exp_trench_gaps(p: Probe) -> None:
    """The twelve trench levels never submitted."""
    have = {0, 1, 2, 3, 4, 5, 10, 15, 20}
    print(f"\n  {'level':>5} {'A lost':>9} {'B pool':>10} {'output x':>9} "
          f"{'pool x':>8}")
    for lvl in [l for l in range(0, 21) if l not in have]:
        ov = settings()
        ov.update(duel(1, "inf", 10, "inf", 10))
        ov["B.1.trench"] = str(lvl)
        try:
            p.submit(ov, create=("B.1.trench",))
        except (BareFormReturned, ValueError) as e:
            print(f"  ! trench {lvl}: {e}", file=sys.stderr)
            continue
        d = dict(p.last_details)
        record("trench_gaps", {"level": lvl, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = d.get("A.1.1") or {}
        b = d.get("B.1.1") or {}
        if a.get("lost") is None:
            continue
        out_x = a["lost"] / (5.0 * effective_units(10))
        pool_x = (b.get("pool") or 0) / (10 * MEASURED_UNITS["inf"][0])
        print(f"  {lvl:>5} {a['lost']:9.2f} {b.get('pool', 0):10.1f} "
              f"{out_x:9.3f} {pool_x:8.3f}")


def exp_fortress_edges(p: Probe) -> None:
    """Fortress above level 5, and a fortress on the ATTACKING side.

    DR = 0.15 x (hp/50 + 1) was fitted on levels 1-5. At level 6 it returns
    1.05, which is more than total immunity, so either it saturates or the
    level cap is real. Only the server can say which, and it says caps outright.
    """
    print(f"\n  {'side':6} {'level':>5} {'A lost':>9} {'B lost':>9} "
          f"{'DR printed':>11}")
    for side in ("B", "A"):
        for lvl in range(1, 11):
            ov = settings()
            ov.update(duel(1, "inf", 30, "inf", 10))
            ov.update({f"{side}.1.bldg.1.abb": "fortress",
                       f"{side}.1.bldg.1.lvl": str(lvl),
                       f"{side}.1.bldg.1.hp": "100%"})
            fields = (f"{side}.1.bldg.1.abb", f"{side}.1.bldg.1.lvl",
                      f"{side}.1.bldg.1.hp")
            try:
                p.submit(ov, create=fields)
            except BareFormReturned as e:
                m = MAX_LEVEL_RE.search(str(e))
                print(f"  {side:6} {lvl:>5} refused: "
                      + (f"max level is {m.group(2)}" if m else str(e)[:44]))
                record("fortress_edges", {"side": side, "level": lvl,
                                          "error": str(e)}, {})
                break
            d = dict(p.last_details)
            record("fortress_edges", {"side": side, "level": lvl, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            a = (d.get("A.1.1") or {}).get("lost")
            b = (d.get("B.1.1") or {}).get("lost")
            bl = d.get(f"{side}.1.bldg.1") or {}
            dr = bl.get("dr_after")
            print(f"  {side:6} {lvl:>5} "
                  + (f"{a:9.2f}" if a is not None else f"{'—':>9}")
                  + (f" {b:9.2f}" if b is not None else f" {'—':>9}")
                  + (f" {dr:11.1f}" if dr is not None else f" {'—':>11}"))


def exp_building_damage(p: Probe) -> None:
    """Damage to a building from each attacking unit type.

    Infantry deal 0.3 per effective unit to a building against 4.0 to units.
    Nothing in the model predicts 0.3, so it cannot be inferred for anything
    else, and the app currently refuses to compute building damage for any
    attacker but infantry.
    """
    print(f"\n  {'attacker':9} {'n':>4} {'bldg lost':>10} {'per effective':>14} "
          f"{'vs units':>9}")
    for atk in LAND_NINE:
        n = 30
        ov = settings()
        ov.update(duel(1, atk, n, "inf", 10))
        ov.update({"B.1.bldg.1.abb": "fortress", "B.1.bldg.1.lvl": "5",
                   "B.1.bldg.1.hp": "100%"})
        try:
            p.submit(ov, create=("B.1.bldg.1.abb", "B.1.bldg.1.lvl",
                                 "B.1.bldg.1.hp"))
        except (BareFormReturned, ValueError) as e:
            print(f"  ! {atk}: {e}", file=sys.stderr)
            continue
        d = dict(p.last_details)
        record("building_damage", {"attacker": atk, "atk_n": n, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        bl = d.get("B.1.bldg.1") or {}
        if bl.get("lost") is None:
            print(f"  {atk:9} {n:>4} {'—':>10}")
            continue
        per = bl["lost"] / effective_units(n)
        print(f"  {atk:9} {n:>4} {bl['lost']:10.2f} {per:14.4f} "
              f"{MEASURED_UNITS[atk][1]:9.1f}")


def exp_position(p: Probe) -> None:
    """Range and position, never exercised once. Every run was at position 0.

    Artillery reaches 50 km and the railgun 150. If position does anything, a
    short-ranged unit at distance should deal nothing while a long-ranged one
    still fires -- and the whole unit table was measured at zero distance, so
    an effect here would mean every figure describes point-blank only.
    """
    # The form's own field list, as discovered by load_form().
    fields = [f for f in (p.baseline or {})
              if any(k in f.lower() for k in ("pos", "dist", "range"))]
    print(f"\n  position-ish fields on the form: {fields or 'NONE FOUND'}")
    if not fields:
        print("  The form exposes no position field, so range cannot be "
              "submitted at all.\n  That is a finding: the calculator does not "
              "model it, and neither can this app.")
        record("position", {"fields": []}, {})
        return
    # BOTH sides must not move together. The first version set A and B to the
    # same value, so the separation stayed zero at every "distance" and the
    # sweep read a flat line -- a null result manufactured by the rig, which is
    # the exact failure this project's section 0 is about.
    # BOTH sides must not move together. The first version set A and B to the
    # same value, so the separation stayed zero at every "distance" and the
    # sweep read a flat line -- a null result manufactured by the rig, which is
    # the exact failure this project's section 0 is about.
    print(f"\n  {'unit':6} {'range':>6} {'distance':>9} {'defender lost':>14}  "
          f"result")
    for unit, doc_range, probes in (("art", 50, (0, 25, 50, 51, 60, 75, 100)),
                                    ("rrg", 150, (0, 100, 150, 151, 200)),
                                    ("inf", 0, (0, 1, 25))):
        for dist in probes:
            ov = settings()
            ov.update(duel(1, unit, 20, "inf", 20))
            ov["A.1.position"] = "0"
            ov["B.1.position"] = str(dist)
            try:
                p.submit(ov, create=("A.1.position", "B.1.position"))
            except (BareFormReturned, ValueError) as e:
                # An empty response IS the answer here: out of range, no
                # battle. It is not a transport failure and must not be
                # reported as one.
                print(f"  {unit:6} {doc_range:>6} {dist:>9} {'—':>14}  "
                      f"OUT OF RANGE (no result rows)")
                record("position", {"unit": unit, "distance": dist,
                                    "out_of_range": True}, {})
                continue
            d = dict(p.last_details)
            record("position", {"unit": unit, "distance": dist,
                                "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = (d.get("B.1.1") or {}).get("lost")
            want = MEASURED_UNITS[unit][1] * effective_units(20)
            print(f"  {unit:6} {doc_range:>6} {dist:>9} "
                  + (f"{b:14.2f}" if b is not None else f"{'—':>14}")
                  + ("  full damage" if b is not None and abs(b - want) < 0.05
                     else "  in range but ATTENUATED" if b is not None
                     else "  no rows"))
    print("\n  Range is a BINARY gate, not a falloff: inside it the figure is "
          "the same as at zero\n  distance, outside it the server returns no "
          "result rows at all — there is no battle.")



# Units whose range is already on record from exp_position. Everything else in
# the roster has only ever been fired at zero distance, which means every
# coefficient in the table describes point-blank and nothing else.
RANGE_KNOWN = {"art": 50, "rrg": 150, "inf": 1}


def _range_probe(p: Probe, unit: str, dist: int,
                 terrain: tuple[str, str]) -> bool | None:
    """Does `unit` still fight at `dist`? True in range, False out, None refused.

    The three-way return is the whole point. exp_position collapsed "no result
    rows" onto out-of-range, which is right there because the pair was known to
    run at zero distance -- but as a general rule it is the same conflation
    that produced three separate "the server will not run it" findings, all of
    which were terrain. A server that ANSWERS with an oops line is refusing the
    configuration, not reporting a miss, and must never be scored as a range
    boundary.
    """
    ov = settings()
    ov.update(duel(1, unit, 20, unit, 20,
                   atk_terrain=terrain[0], def_terrain=terrain[1]))
    ov["A.1.position"] = "0"
    ov["B.1.position"] = str(dist)
    try:
        p.submit(ov, create=("A.1.position", "B.1.position"))
    except BareFormReturned as e:
        if e.oops:
            print(f"    ! {unit} @ {dist}: server refused -> "
                  f"{' | '.join(e.oops[:2])}", file=sys.stderr)
            return None
        record("range_roster", {"unit": unit, "distance": dist,
                                "terrain": list(terrain), "no_rows": True}, {})
        return False
    except ValueError as e:
        print(f"    ! {unit} @ {dist}: {e}", file=sys.stderr)
        return None
    d = dict(p.last_details)
    lost = (d.get("B.1.1") or {}).get("lost")
    record("range_roster", {"unit": unit, "distance": dist,
                            "terrain": list(terrain), "detail": d},
           {k: (v or {}).get("lost") for k, v in d.items()})
    return lost is not None and lost > 0


def exp_range_roster(p: Probe) -> None:
    """The reach of every unit that has never been fired from a distance.

    Range is already known to be a BINARY gate rather than a falloff, so the
    only unknown per unit is one integer -- and an integer is found by
    bisection, not by a ladder of guessed values. The help page's figures
    (cruiser 40, battleship 75) are deliberately NOT used as starting points:
    they are the thing being checked.

    Each unit fights ITSELF, in the terrain pair its own class requires. A
    self-duel is the one matchup guaranteed to run -- it is how the diagonal of
    MEASURED_UNITS was read -- so a silent empty response during the search is
    attributable to distance and nothing else. That attribution is only safe
    because the d=0 control below proves the pair runs at all.
    """
    cls_of = {u: c for c, us in UNIT_CLASSES.items() for u in us}
    print(f"\n  {'unit':8} {'class':6} {'range':>7} {'requests':>9}  note")
    found: dict[str, int] = {}
    for unit in ROSTER_ORDER:
        if unit in RANGE_KNOWN:
            print(f"  {unit:8} {cls_of.get(unit,''):6} "
                  f"{RANGE_KNOWN[unit]:>7} {'0':>9}  already on record")
            found[unit] = RANGE_KNOWN[unit]
            continue
        acls = cls_of.get(unit)
        if not acls:
            continue
        terrain = RANGE_TERRAIN_OVERRIDE.get(unit) or TERRAIN_PAIR[(acls, acls)]
        n = 0

        # Control. Without it, a pair the server refuses outright reads as
        # "out of range at every distance" and gets written down as range 0.
        n += 1
        base = _range_probe(p, unit, 0, terrain)
        if base is not True:
            print(f"  {unit:8} {acls:6} {'—':>7} {n:>9}  "
                  f"NO BATTLE AT ZERO DISTANCE — not a range reading")
            continue

        # Exponential search for a distance that misses, then bisect. lo is
        # always a distance that hits, hi always one that does not.
        lo, hi = 0, None
        probe = 1
        while probe <= 512:
            n += 1
            r = _range_probe(p, unit, probe, terrain)
            if r is None:
                break
            if r:
                lo = probe
                probe *= 2
            else:
                hi = probe
                break
        if hi is None:
            print(f"  {unit:8} {acls:6} {'>512':>7} {n:>9}  "
                  f"no miss found — unbounded or position ignored")
            record("range_roster", {"unit": unit, "range": None,
                                    "unbounded": True}, {})
            continue
        while hi - lo > 1:
            mid = (lo + hi) // 2
            n += 1
            r = _range_probe(p, unit, mid, terrain)
            if r is None:
                break
            if r:
                lo = mid
            else:
                hi = mid
        found[unit] = lo
        note = "melee" if lo <= 1 else "ranged"
        print(f"  {unit:8} {acls:6} {lo:>7} {n:>9}  {note}")
        record("range_roster", {"unit": unit, "range": lo,
                               "terrain": list(terrain)}, {"range": float(lo)})

    print("\n  RANGE_KM = " + json.dumps(found, sort_keys=True))
    doc = {"cl": 40, "bb": 75}
    for u, claimed in doc.items():
        if u in found:
            verdict = "matches" if found[u] == claimed else "DISAGREES with"
            print(f"  {u}: measured {found[u]}, help page says {claimed} "
                  f"-- {verdict} the help page")


# A Balloon aborts the batch in 'air' terrain (the balloon bug, section 194),
# so its self-duel runs on land like every other balloon reading.
RANGE_TERRAIN_OVERRIDE = {"bal": ("land", "land")}


def exp_return_fire(p: Probe) -> None:
    """Does a bombarded defender shoot back? And where is infantry's boundary?

    The roster sweep turned up something it was not looking for. A light
    artillery attacking from 8 km deals its full 100.00 and takes ZERO in
    return, while at 4 km both sides lose. Three units with three different
    ranges -- lart 30, cl 40, bb 75 -- all take nothing back at 8 km, so the
    silence is not the defender running out of reach of its own. It is a
    separate rule, and the app currently models none of it: range is a gate on
    the attacker only, which makes every bombardment in the app cost the
    attacker losses it would never take.

    The boundary itself was never sampled -- the exponential search jumps 4, 8
    -- so 5, 6 and 7 are unmeasured and the threshold could be anywhere in
    [4, 7]. Melee ATTACK range bisected to exactly 5 for ten separate units,
    which makes 5 the obvious candidate and therefore the one worth checking
    rather than assuming.

    Infantry is here for a different reason. UNIT_RANGE says 1, which came from
    a three-value ladder (0, 1, 25) that never bisected: 1 is the largest
    distance that was TRIED and hit, not the largest that hits. Every other
    melee unit in the roster reads exactly 5. A number that only looks measured
    is worse than a gap, because nothing downstream flags it.
    """
    print("\n  1. infantry and the balloon, bisected rather than laddered\n")
    for unit in ("inf", "bal"):
        terrain = RANGE_TERRAIN_OVERRIDE.get(unit) or ("land", "land")
        if _range_probe(p, unit, 0, terrain) is not True:
            print(f"  {unit}: no battle at zero distance — cannot read")
            continue
        lo, hi, probe = 0, None, 1
        while probe <= 512:
            r = _range_probe(p, unit, probe, terrain)
            if r is None:
                break
            if r:
                lo, probe = probe, probe * 2
            else:
                hi = probe
                break
        while hi is not None and hi - lo > 1:
            mid = (lo + hi) // 2
            r = _range_probe(p, unit, mid, terrain)
            if r is None:
                break
            if r:
                lo = mid
            else:
                hi = mid
        was = RANGE_KNOWN.get(unit)
        note = ("" if was is None else
                f"  (UNIT_RANGE said {was} — "
                + ("confirmed" if was == lo else "WRONG, never bisected") + ")")
        print(f"  {unit:6} range {lo}{note}")
        record("return_fire", {"probe": "bisect", "unit": unit, "range": lo},
               {"range": float(lo)})

    print("\n  2. the return-fire boundary, one kilometre at a time\n")
    print(f"  {'distance':>9} {'defender lost':>14} {'attacker lost':>14}  "
          f"return fire")
    for dist in (4, 5, 6, 7, 8):
        ov = settings()
        ov.update(duel(1, "lart", 20, "lart", 20))
        ov["A.1.position"] = "0"
        ov["B.1.position"] = str(dist)
        try:
            p.submit(ov, create=("A.1.position", "B.1.position"))
        except (BareFormReturned, ValueError) as e:
            print(f"  {dist:>9} {'—':>14} {'—':>14}  no battle ({e})")
            continue
        d = dict(p.last_details)
        a = (d.get("A.1.1") or {}).get("lost")
        b = (d.get("B.1.1") or {}).get("lost")
        record("return_fire", {"probe": "boundary", "distance": dist,
                               "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        print(f"  {dist:>9} {b if b is None else f'{b:.2f}':>14} "
              f"{a if a is None else f'{a:.2f}':>14}  "
              + ("YES" if (a or 0) > 0 else "NONE — free bombardment"))

    print("\n  3. does a ranged DEFENDER ever initiate?\n")
    # Infantry (5) attacking light artillery (30) from 20 km. If the defender's
    # own reach mattered, the artillery would fire and the infantry would die
    # for nothing. If the attacker's reach alone decides, there is no battle.
    ov = settings()
    ov.update(duel(1, "inf", 20, "lart", 20))
    ov["A.1.position"] = "0"
    ov["B.1.position"] = "20"
    try:
        p.submit(ov, create=("A.1.position", "B.1.position"))
        d = dict(p.last_details)
        a = (d.get("A.1.1") or {}).get("lost")
        b = (d.get("B.1.1") or {}).get("lost")
        record("return_fire", {"probe": "defender_initiates", "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        print(f"  inf(5) attacks lart(30) at 20 km -> attacker lost "
              f"{a}, defender lost {b}")
        print("  The defender's reach DOES enter into it — this needs a "
              "model, not a gate.")
    except (BareFormReturned, ValueError):
        record("return_fire", {"probe": "defender_initiates",
                               "no_battle": True}, {})
        print("  inf(5) attacks lart(30) at 20 km -> NO BATTLE.")
        print("  The attacker's reach alone decides whether anything happens; "
              "a defender never\n  initiates, however far it could shoot.")


def exp_mixed_range(p: Probe) -> None:
    """A stack of mixed reach, fired from beyond part of it.

    Every range reading so far used a stack of ONE type, which is the clean way
    to find a boundary and the wrong way to learn what the app has to compute.
    Real stacks are mixtures, and a mixture at 20 km has infantry that cannot
    reach and light artillery that can. Three outcomes are possible and they
    are not close together:

      no battle          the shortest reach in the stack gates the whole thing
      100.00             only the artillery fires, and E() counts only it
      more than 100.00   only the artillery fires, but E() counts the infantry

    The third is the one that would quietly wreck the app, because a stack
    would gain output by adding units that cannot shoot. This is the same
    question the mixed-stack sweep asked about saturation, asked again where
    part of the stack is switched off.
    """
    dist = 20
    print(f"\n  Light artillery reaches 30 km, infantry 5. Firing from "
          f"{dist} km.\n")
    print(f"  {'attacker stack':28} {'defender lost':>14}  reading")
    base = None
    for label, rows in (("lart 20 (alone)", [("lart", 20)]),
                        ("inf 20 + lart 20", [("inf", 20), ("lart", 20)]),
                        ("inf 20 (alone)", [("inf", 20)])):
        ov = settings()
        ov.update(duel(1, "lart", 20, "inf", 20))
        ov.update(composite(1, "A", rows))
        ov["A.1.position"] = "0"
        ov["B.1.position"] = str(dist)
        try:
            p.submit(ov, create=composite_fields("A", 1, len(rows))
                     + ("A.1.position", "B.1.position"))
        except (BareFormReturned, ValueError) as e:
            print(f"  {label:28} {'—':>14}  NO BATTLE ({type(e).__name__})")
            record("mixed_range", {"rows": rows, "distance": dist,
                                   "no_battle": True}, {})
            continue
        d = dict(p.last_details)
        b = (d.get("B.1.1") or {}).get("lost")
        record("mixed_range", {"rows": rows, "distance": dist, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if label.startswith("lart 20 ("):
            base = b
        note = ""
        if base and b is not None:
            if abs(b - base) < 0.05:
                note = "identical to lart alone — the short-reach units are inert"
            else:
                note = (f"DIFFERS from lart alone by {b - base:+.2f} — "
                        f"unreachable units still count")
        print(f"  {label:28} {b if b is None else f'{b:.2f}':>14}  {note}")

    # And the defender's side of the same question: does a stack that CONTAINS
    # a long-reach unit shoot back from beyond 5 km? The single-type reading
    # says a lart defender at 6 km deals nothing despite reaching 30, but a
    # mixture is worth one request rather than an assumption.
    print("\n  Defender stack inf 20 + lart 20 at 6 km, bombarded by lart:\n")
    ov = settings()
    ov.update(duel(1, "lart", 20, "inf", 20))
    ov.update(composite(1, "B", [("inf", 20), ("lart", 20)]))
    ov["A.1.position"] = "0"
    ov["B.1.position"] = "6"
    try:
        p.submit(ov, create=composite_fields("B", 1, 2)
                 + ("A.1.position", "B.1.position"))
        d = dict(p.last_details)
        a = (d.get("A.1.1") or {}).get("lost")
        record("mixed_range", {"probe": "defender_mix", "distance": 6,
                               "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        print(f"  attacker lost {a} -> "
              + ("still no return fire; the 5 km cut-off is a property of the "
                 "DISTANCE,\n  not of what the defender is holding."
                 if not a else
                 "RETURN FIRE from a mixed defender — the cut-off depends on "
                 "the stack."))
    except (BareFormReturned, ValueError) as e:
        print(f"  no battle: {e}")


# Target stacks sized so the reading cannot be censored: each pool comfortably
# exceeds the largest output any attacker below can produce against it.
TERRAIN_TARGETS = {"int": 40, "inf": 100, "cl": 30, "bb": 30, "tac": 40}


def _coef_against(p: Probe, atk: str, atk_terrain: str, tgt: str,
                  tgt_terrain: str, atk_n: int = 20) -> float | None:
    """Damage per effective attacking unit, or None if the reading is censored.

    A wiped defender reports its own pool rather than what it was hit with, so
    that number is not a measurement of the attacker and must be refused rather
    than written down.
    """
    n = TERRAIN_TARGETS.get(tgt, 40)
    ov = settings()
    ov.update(duel(1, atk, atk_n, tgt, n,
                   atk_terrain=atk_terrain, def_terrain=tgt_terrain))
    try:
        p.submit(ov)
    except (BareFormReturned, ValueError) as e:
        print(f"    ! {atk}@{atk_terrain} vs {tgt}@{tgt_terrain}: {e}",
              file=sys.stderr)
        record("target_terrain", {"attacker": atk, "atk_terrain": atk_terrain,
                                  "target": tgt, "tgt_terrain": tgt_terrain,
                                  "refused": True}, {})
        return None
    d = dict(p.last_details)
    b = d.get("B.1.1") or {}
    record("target_terrain", {"attacker": atk, "atk_terrain": atk_terrain,
                              "target": tgt, "tgt_terrain": tgt_terrain,
                              "atk_n": atk_n, "detail": d},
           {k: (v or {}).get("lost") for k, v in d.items()})
    if (b.get("pct") or 0) >= 99.9:
        print(f"    ! {atk} vs {tgt}@{tgt_terrain}: DEFENDER WIPED "
              f"({b.get('pct')}%) — reading discarded", file=sys.stderr)
        return None
    if b.get("lost") is None:
        return None
    return b["lost"] / effective_units(atk_n)


def exp_target_terrain(p: Probe) -> None:
    """Is the coefficient column a target CLASS or a target TERRAIN?

    CLASS_ATTACK holds one column per target class, and every cell in it was
    read through TERRAIN_PAIR -- a table that picks the terrain FROM the class.
    Land targets were read on land, air targets in the air, naval targets at
    sea. So in every cell of that matrix the two moved together, and nothing
    measured so far can tell them apart.

    The close-out sweep is what made this urgent. A battleship deals 30.0 per
    effective unit to fighters in SEA terrain and 6.0 to the same fighters on
    LAND -- a factor of five from the target's terrain alone, with its class
    held fixed. Either that is a naval-specific quirk or the whole air and
    naval columns of CLASS_ATTACK are terrain effects wearing a class label.

    Four cells decide it, because class and terrain are crossed rather than
    varied one at a time:

        target       on LAND      at SEA
        int (air)      a            b
        inf (land)     c            d

      a == c and b == d, a != b   ->  TERRAIN decides; the class column is a
                                      relabelled terrain column
      a == b and c == d, a != c   ->  CLASS decides; the sea reading was a
                                      naval quirk
      all four differ            ->  both matter and the table needs two axes
    """
    print("\n  1. class crossed with terrain, attacker held at battleship\n")
    print(f"  {'target':6} {'class':6} {'terrain':8} {'per eff. unit':>14}")
    grid: dict[tuple[str, str], float] = {}
    for tgt, cls in (("int", "air"), ("inf", "land")):
        for terr in ("land", "sea"):
            v = _coef_against(p, "bb", "sea", tgt, terr)
            if v is not None:
                grid[(tgt, terr)] = v
            print(f"  {tgt:6} {cls:6} {terr:8} "
                  + (f"{v:14.4f}" if v is not None else f"{'refused':>14}"))

    a = grid.get(("int", "land"))
    b = grid.get(("int", "sea"))
    c = grid.get(("inf", "land"))
    d = grid.get(("inf", "sea"))
    print()
    if None in (a, b, c, d):
        print("  A cell is missing, so the question is NOT decided. Nothing "
              "goes into CLASS_ATTACK\n  on a partial grid.")
    else:
        same = lambda x, y: abs(x - y) < 0.02 * max(x, y, 1.0)
        if same(a, c) and same(b, d) and not same(a, b):
            print("  TERRAIN decides. Two different classes read the same "
                  "figure in the same terrain,\n  and the same class reads "
                  "different figures in different terrain. The air and naval\n"
                  "  columns of CLASS_ATTACK are terrain columns with a class "
                  "label on them.")
        elif same(a, b) and same(c, d) and not same(a, c):
            print("  CLASS decides, and the battleship-vs-fighters reading was "
                  "a naval quirk rather\n  than a general rule.")
        elif same(a, b) and same(c, d) and same(a, c):
            print("  NEITHER moves the figure here. That contradicts the "
                  "close-out reading and means\n  the rig, not the game, "
                  "produced one of the two.")
        else:
            print("  BOTH matter: the table needs a target-terrain axis as "
                  "well as a class one.")

    print("\n  2. the same crossing from an AIR attacker, to check it "
          "generalises\n")
    print(f"  {'attacker':8} {'target':6} {'terrain':8} {'per eff. unit':>14}")
    for atk, atk_terr in (("int", "air"), ("inf", "land")):
        for tgt, terr in (("inf", "land"), ("inf", "sea"),
                          ("int", "land"), ("int", "sea")):
            if atk == tgt:
                continue
            v = _coef_against(p, atk, atk_terr, tgt, terr)
            print(f"  {atk:8} {tgt:6} {terr:8} "
                  + (f"{v:14.4f}" if v is not None else f"{'refused':>14}"))


def exp_embarked_hp(p: Probe) -> None:
    """The pools in the terrain grid, which nobody was reading.

    EMBARKED_COEF says a non-naval unit in sea terrain attacks at a flat 1.0.
    That is measured and modelled. What went unnoticed is sitting in the same
    responses: the POOL changes too.

        40 fighters on land   pool 2400   ->  60 HP each, the table value
        40 fighters at sea    pool  400   ->  10 HP each
        100 infantry on land  pool 2000   ->  20 HP each, the table value
        100 infantry at sea   pool 1000   ->  10 HP each

    A flat 10, the same for a fighter as for a rifleman. So embarkation
    replaces BOTH of a unit's numbers, and the app models one of them -- every
    embarked pool it draws is wrong, by 6x for a fighter.

    It also explains a reading this project nearly wrote down as physics. The
    battleship-vs-fighters cell at sea was recorded as 30.0 per effective unit;
    it was a 100% wipe, lost exactly equal to a pool that is six times smaller
    than anyone thought. Sizing a target stack by the table's max HP guarantees
    that wipe in sea terrain.
    """
    print("\n  1. per-unit HP by terrain, read off the pools\n")
    print(f"  {'unit':6} {'terrain':8} {'count':>5} {'pool':>9} "
          f"{'per unit':>9} {'table':>7}")
    for unit in ("inf", "cav", "ht", "int", "tac", "cl", "bb"):
        for terr in ("land", "sea", "debark"):
            n = 20
            # A naval unit is refused on land; a land unit is refused in air.
            # Neither refusal is news, and neither is a reading.
            ov = settings()
            atk = "bb" if terr == "sea" else "inf"
            if unit in ("cl", "bb") and terr != "sea":
                continue
            if atk == unit:
                atk = "cav" if terr != "sea" else "sub"
            ov.update(duel(1, atk, 5, unit, n,
                           atk_terrain="sea" if terr == "sea" else "land",
                           def_terrain=terr))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                print(f"  {unit:6} {terr:8} {n:>5} {'refused':>9}   {e}"[:110])
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("embarked_hp", {"unit": unit, "terrain": terr, "count": n,
                                   "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            pool = b.get("pool")
            if pool is None:
                print(f"  {unit:6} {terr:8} {n:>5} {'—':>9}")
                continue
            per = pool / n
            print(f"  {unit:6} {terr:8} {n:>5} {pool:9.1f} {per:9.2f} "
                  f"{MEASURED_UNITS.get(unit, (0,))[0]:7.1f}")

    print("\n  2. the naval-vs-air cell, with a stack that can survive it\n")
    # int at sea holds 10 HP each, so 200 of them is a 2000-point pool. The
    # attacker is cut to 10 so even a coefficient of 100 could not wipe it.
    print(f"  {'target terrain':14} {'lost':>10} {'pct':>7} {'per eff. unit':>14}")
    for terr in ("land", "sea", "air"):
        ov = settings()
        ov.update(duel(1, "bb", 10, "int", 200,
                       atk_terrain="sea", def_terrain=terr))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {terr:14} {'—':>10}   {e}"[:110])
            record("embarked_hp", {"probe": "bb_vs_air", "terrain": terr,
                                   "refused": True}, {})
            continue
        d = dict(p.last_details)
        b = d.get("B.1.1") or {}
        record("embarked_hp", {"probe": "bb_vs_air", "terrain": terr,
                               "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None:
            print(f"  {terr:14} {'—':>10}")
            continue
        if (b.get("pct") or 0) >= 99.9:
            print(f"  {terr:14} {b['lost']:10.2f} {b['pct']:7.1f}  WIPED — "
                  f"still censored, do not record")
            continue
        print(f"  {terr:14} {b['lost']:10.2f} {b['pct']:7.2f} "
              f"{b['lost'] / effective_units(10):14.4f}")


def exp_embarked_class(p: Probe) -> None:
    """An embarked target: is it hit as LAND, or as NAVAL?

    A battleship deals 40.0 per effective unit to fighters at sea, which is
    also what it deals to infantry and to another battleship -- so it cannot
    tell the three apart and decides nothing. The attackers that CAN are the
    ones whose land and naval columns differ:

        attacker   land column   naval column
        cav           15.0           8.0
        lart           5.0           1.0
        ht            45.0          23.0

    Each is fired at infantry at sea and at fighters at sea. If the figure
    lands on the naval column, embarkation moves a unit into the naval class
    for incoming damage as well as replacing its attack with 1.0 and its HP
    with 10 -- one rule with three consequences. If it lands on the land
    column, the class is unchanged and only the two stats are replaced.

    Targets are 200 strong because an embarked unit holds ten HP whatever it
    is, and a stack sized off the unit table's max HP is the exact mistake
    that censored the last naval-vs-air reading.
    """
    expect = {"cav": (15.0, 8.0), "lart": (5.0, 1.0), "ht": (45.0, 23.0)}
    print(f"\n  {'attacker':8} {'target':10} {'per eff. unit':>14} "
          f"{'land col':>9} {'naval col':>10}  verdict")
    votes = {"land": 0, "naval": 0, "neither": 0}
    for atk, (land_c, naval_c) in expect.items():
        for tgt in ("inf", "int"):
            ov = settings()
            ov.update(duel(1, atk, 10, tgt, 200,
                           atk_terrain="land", def_terrain="sea"))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                print(f"  {atk:8} {tgt + '@sea':10} {'refused':>14}   {e}"[:110])
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("embarked_class", {"attacker": atk, "target": tgt,
                                      "tgt_terrain": "sea", "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None:
                continue
            if (b.get("pct") or 0) >= 99.9:
                print(f"  {atk:8} {tgt + '@sea':10} {'WIPED':>14}  discarded")
                continue
            per = b["lost"] / effective_units(10)
            near = lambda x: abs(per - x) < 0.05 * max(x, 1.0)
            verdict = ("NAVAL column" if near(naval_c)
                       else "land column" if near(land_c) else "NEITHER")
            votes["naval" if near(naval_c) else
                  "land" if near(land_c) else "neither"] += 1
            print(f"  {atk:8} {tgt + '@sea':10} {per:14.4f} {land_c:9.1f} "
                  f"{naval_c:10.1f}  {verdict}")
    print()
    if votes["naval"] and not votes["land"] and not votes["neither"]:
        print("  EMBARKATION IS A CLASS CHANGE. A unit in sea or debark "
              "terrain is hit as a naval\n  unit, attacks at a flat 1.0 and "
              "holds a flat 10 HP — one rule, three consequences.")
    elif votes["land"] and not votes["naval"]:
        print("  The class is UNCHANGED; embarkation replaces the two stats "
              "and nothing else.")
    else:
        print(f"  Split verdict {votes} — not decided, nothing goes in the "
              f"table.")


# One attacker per class, plus a second for the flatness check. Each is sized
# large enough that the DEFENDER's output cannot wipe it, because a wiped
# attacker reports its own pool and that is not a measurement of the defender.
DEF_PROBE_ATTACKERS = {
    "land": [("inf", 200), ("ht", 60)],
    "air": [("int", 100), ("tac", 100)],
    "naval": [("bb", 60), ("cl", 100)],
}
DEF_PROBE_N = 40          # defender count, fixed so E() is one constant


def _defence_cell(p: Probe, defender: str, atk: str, atk_n: int,
                  acls: str, dcls: str) -> float | None:
    """The DEFENDER's coefficient, read off the attacker's losses.

    attacker_lost = coef x E(defender count) x m(1) -- the defending side is
    not attenuated even when it is losing badly, which is what makes this
    readable in one request. A wiped attacker is refused rather than recorded.
    """
    terr = TERRAIN_PAIR[(acls, dcls)]
    ov = settings()
    ov.update(duel(1, atk, atk_n, defender, DEF_PROBE_N,
                   atk_terrain=terr[0], def_terrain=terr[1]))
    try:
        p.submit(ov)
    except (BareFormReturned, ValueError) as e:
        print(f"    ! {atk} vs {defender}: {e}"[:110], file=sys.stderr)
        record("defence_matrix", {"defender": defender, "attacker": atk,
                                  "atk_class": acls, "refused": True}, {})
        return None
    d = dict(p.last_details)
    a = d.get("A.1.1") or {}
    record("defence_matrix", {"defender": defender, "attacker": atk,
                              "atk_class": acls, "def_class": dcls,
                              "atk_n": atk_n, "def_n": DEF_PROBE_N,
                              "terrain": list(terr), "detail": d},
           {k: (v or {}).get("lost") for k, v in d.items()})
    if a.get("lost") is None:
        return None
    if (a.get("pct") or 0) >= 99.9:
        print(f"    ! {atk} vs {defender}: ATTACKER WIPED ({a.get('pct')}%) — "
              f"reading discarded", file=sys.stderr)
        return None
    return a["lost"] / effective_units(DEF_PROBE_N)


def exp_defence_matrix(p: Probe) -> None:
    """The defending side's coefficient table, which has never existed.

    CLASS_ATTACK is a full 17 x 3 table and there is no equivalent for the
    other half of a battle. The consequence is not a rough number, it is no
    number at all: a cross-class pairing has a measured attack coefficient and
    an unmeasured defence one, so the app withholds the entire result. Land
    attacking air -- one of the commonest things a player would type in -- has
    always come back blank for exactly this reason.

    Four cells fell out of the terrain sweep and hinted at the shape. A Fighter
    defends at 5.0 against infantry AND at 5.0 against a battleship; infantry
    defend at 2.5 against a battleship. Flat within an attacker class, which is
    the same shape the attack table has. That is a hint from four cells, not a
    law, so this sweep reads TWO attackers per class for every defender rather
    than one, and says so when they disagree.
    """
    cls_of = {u: c for c, us in UNIT_CLASSES.items() for u in us}
    print(f"\n  {'defender':8} {'class':6} " + " ".join(f"{c:>18}" for c in
                                                        ("vs land", "vs air",
                                                         "vs naval")))
    table: dict[str, dict[str, float]] = {}
    disagreements = 0
    for defender in ROSTER_ORDER:
        dcls = cls_of.get(defender)
        if not dcls:
            continue
        row: dict[str, float] = {}
        cells: list[str] = []
        for acls in ("land", "air", "naval"):
            vals = []
            for atk, atk_n in DEF_PROBE_ATTACKERS[acls]:
                if atk == defender:
                    continue
                v = _defence_cell(p, defender, atk, atk_n, acls, dcls)
                if v is not None:
                    vals.append((atk, v))
            if not vals:
                cells.append(f"{'—':>18}")
                continue
            lo = min(v for _, v in vals)
            hi = max(v for _, v in vals)
            flat = (hi - lo) <= 0.02 * max(hi, 1.0)
            if not flat:
                disagreements += 1
            row[acls] = (lo + hi) / 2
            cells.append(f"{row[acls]:12.3f}" + ("  flat" if flat or len(vals) < 2
                                                 else "  SPLIT"))
        table[defender] = row
        print(f"  {defender:8} {dcls:6} " + " ".join(cells))

    print("\n  CLASS_DEFENCE = " + json.dumps(
        {k: {c: round(v, 4) for c, v in r.items()} for k, r in table.items()},
        sort_keys=True))
    if disagreements:
        print(f"\n  {disagreements} cell(s) where two attackers of the SAME "
              f"class read different figures.\n  The defending side is then "
              f"NOT flat within an attacker class, and a single\n  column per "
              f"class is the wrong shape for it.")
    else:
        print("\n  Every cell agreed across two independent attackers of the "
              "same class. The defending\n  side has the same shape as the "
              "attacking one: flat within a class, changing between.")


def exp_defence_gaps(p: Probe) -> None:
    """The five defence cells TERRAIN_PAIR refused, retried in a terrain that runs.

    Same trap, fourth and fifth time. TERRAIN_PAIR sends a naval attacker
    against an air defender as sea/air, and sea/air aborts the batch -- so
    three air units came back empty and would have been written down as "the
    server will not run it" if this project had not already made that mistake
    three times. It runs perfectly as sea/LAND, which is also the terrain the
    attack table's air column was read in, so the two halves match.

    The Balloon is refused in air terrain outright and is read on land, as
    every other balloon reading is. A naval attacker cannot come ashore, so its
    cell is sea/land like the others.
    """
    print(f"\n  {'defender':8} {'attacker':8} {'terrain':10} "
          f"{'per eff. unit':>14}")
    out: dict[str, dict[str, float]] = {}
    probes = [("int", "bb", 60, "naval"), ("int", "cl", 100, "naval"),
              ("tac", "bb", 60, "naval"), ("tac", "cl", 100, "naval"),
              ("zep", "bb", 60, "naval"), ("zep", "cl", 100, "naval"),
              ("bal", "int", 100, "air"), ("bal", "tac", 100, "air"),
              ("bal", "bb", 60, "naval"), ("bal", "cl", 100, "naval")]
    for defender, atk, atk_n, acls in probes:
        terr = ("sea" if acls == "naval" else "air", "land")
        ov = settings()
        ov.update(duel(1, atk, atk_n, defender, DEF_PROBE_N,
                       atk_terrain=terr[0], def_terrain=terr[1]))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {defender:8} {atk:8} {'/'.join(terr):10} "
                  f"{'refused':>14}  {e}"[:120])
            record("defence_matrix", {"defender": defender, "attacker": atk,
                                      "atk_class": acls, "retry": True,
                                      "refused": True}, {})
            continue
        d = dict(p.last_details)
        a = d.get("A.1.1") or {}
        record("defence_matrix", {"defender": defender, "attacker": atk,
                                  "atk_class": acls, "def_class": "air",
                                  "atk_n": atk_n, "def_n": DEF_PROBE_N,
                                  "terrain": list(terr), "retry": True,
                                  "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if a.get("lost") is None:
            print(f"  {defender:8} {atk:8} {'/'.join(terr):10} {'—':>14}")
            continue
        if (a.get("pct") or 0) >= 99.9:
            print(f"  {defender:8} {atk:8} {'/'.join(terr):10} "
                  f"{'WIPED':>14}  discarded")
            continue
        v = a["lost"] / effective_units(DEF_PROBE_N)
        out.setdefault(defender, {}).setdefault(acls, []).append(v) \
            if False else None
        out.setdefault(defender, {})[f"{acls}:{atk}"] = v
        print(f"  {defender:8} {atk:8} {'/'.join(terr):10} {v:14.4f}")
    print("\n  " + json.dumps(out, sort_keys=True))
    for defender, cells in sorted(out.items()):
        by_cls: dict[str, list[float]] = {}
        for k, v in cells.items():
            by_cls.setdefault(k.split(":")[0], []).append(v)
        for acls, vals in by_cls.items():
            if len(vals) > 1 and max(vals) - min(vals) > 0.02 * max(vals):
                print(f"  ! {defender} vs {acls}: two attackers disagree "
                      f"{vals} — not flat, do not record a single column")


def exp_balloon_class(p: Probe) -> None:
    """What class does a BALLOON attack as? The defence table disagrees with itself.

    CLASS_DEFENCE says a balloon defends at 10.0 against air attackers, read
    from a fighter and a bomber which agreed exactly. It also says 3.0 against
    land attackers, read from infantry and a heavy tank which agreed exactly.
    And the balloon's own diagonal -- balloon attacking balloon, in land
    terrain, the only terrain the server will run it in -- is 3.0.

    3.0 is the LAND column. So either the balloon's air column is not flat, or
    a balloon in land terrain attacks as a land unit, and those two readings of
    the same number mean very different things.

    One request separates them. A balloon attacking infantry loses

        5.0  x E(40) = 166.67   if it counts as a LAND attacker
        0.4  x E(40) =  13.33   if it counts as an AIR attacker

    which is not a distinction that needs a tolerance.
    """
    print(f"\n  {'target':8} {'balloon lost':>13} {'if land':>9} "
          f"{'if air':>8}  verdict")
    verdicts = []
    for tgt in ("inf", "ht", "bal"):
        ov = settings()
        ov.update(duel(1, "bal", 40, tgt, 40,
                       atk_terrain="land", def_terrain="land"))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {tgt:8} {'refused':>13}  {e}"[:100])
            continue
        d = dict(p.last_details)
        a = d.get("A.1.1") or {}
        record("balloon_class", {"target": tgt, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if a.get("lost") is None or (a.get("pct") or 0) >= 99.9:
            print(f"  {tgt:8} {'wiped/none':>13}  discarded")
            continue
        e40 = effective_units(40)
        # The defender's own table entry, both ways round.
        land_c, air_c = {"inf": (5.0, 0.4), "ht": (45.0, 4.0),
                         "bal": (3.0, 10.0)}[tgt]
        per = a["lost"] / e40
        near = lambda x: abs(per - x) < 0.03 * max(x, 1.0)
        v = ("LAND attacker" if near(land_c) else
             "AIR attacker" if near(air_c) else "NEITHER")
        verdicts.append(v)
        print(f"  {tgt:8} {a['lost']:13.2f} {land_c * e40:9.2f} "
              f"{air_c * e40:8.2f}  {v} (read {per:.3f})")
    print()
    if verdicts and all(v == "LAND attacker" for v in verdicts):
        print("  A BALLOON IN LAND TERRAIN ATTACKS AS A LAND UNIT. Its own "
              "diagonal of 3.0 is the\n  LAND column of CLASS_DEFENCE, not a "
              "second and smaller air reading — the table\n  is flat after "
              "all, and the balloon is simply not in the air when it fights.")
    elif verdicts and all(v == "AIR attacker" for v in verdicts):
        print("  It attacks as an AIR unit, so the balloon's air defence "
              "column is NOT flat: 10.0\n  from a fighter or a bomber, 3.0 "
              "from another balloon. One column cannot hold both.")
    else:
        print(f"  Mixed or unreadable: {verdicts}. Nothing goes in the table.")


def exp_embarked_is_convoy(p: Probe) -> None:
    """Two loose ends that look like the same law.

    ONE. CLASS_ATTACK has no air column for sub, cl or bb, because a naval
    stack against an air one was recorded as something the server refuses. It
    does not refuse it; sea/air aborts and sea/land runs. A battleship reads
    6.0 against fighters on land, twice, so the column exists and is simply
    missing.

    TWO. EMBARKED_COEF says an embarked unit attacks at a flat 1.0 and
    EMBARKED_MAXHP says it holds 10 HP. Its DEFENCE was set to that same flat
    1.0, and two readings say otherwise:

        embarked fighters answering infantry   1.0 per effective unit
        embarked infantry answering a fighter  0.5 per effective unit

    1.0 and 0.5 are the land and air columns of the CONVOY. The convoy is also
    where the flat 1.0 attack came from -- an embarked unit was described from
    the start as fighting exactly as well as a convoy. So the rule may not be
    two constants at all: it may be that an embarked unit IS a convoy, in both
    directions and against every class. That predicts an embarked attacker
    deals 0.5 against air and naval targets rather than 1.0, which is the cell
    nobody has ever sent.
    """
    print("\n  1. the naval air column, in the terrain that runs\n")
    print(f"  {'attacker':8} {'per eff. unit':>14}")
    for atk in ("sub", "cl", "bb"):
        ov = settings()
        ov.update(duel(1, atk, 20, "int", 200,
                       atk_terrain="sea", def_terrain="land"))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {atk:8} {'refused':>14}  {e}"[:100])
            continue
        d = dict(p.last_details)
        b = d.get("B.1.1") or {}
        record("naval_air_column", {"attacker": atk, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
            print(f"  {atk:8} {'wiped/none':>14}  discarded")
            continue
        print(f"  {atk:8} {b['lost'] / effective_units(20):14.4f}")

    print("\n  2. does an embarked attacker deal 1.0, or a convoy's column?\n")
    print(f"  {'target':10} {'terrain':8} {'per eff. unit':>14} "
          f"{'flat 1.0':>9} {'convoy':>7}")
    # 40 embarked infantry attacking, so E(40) = 33.33 and the two hypotheses
    # are 33.33 apart from each other at every target.
    for tgt, tterr, convoy_c in (("inf", "land", 1.0), ("int", "land", 0.5),
                                 ("bb", "sea", 0.5)):
        ov = settings()
        ov.update(duel(1, "inf", 40, tgt, 200 if tgt != "bb" else 60,
                       atk_terrain="sea", def_terrain=tterr))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {tgt:10} {tterr:8} {'refused':>14}  {e}"[:100])
            continue
        d = dict(p.last_details)
        b = d.get("B.1.1") or {}
        record("embarked_convoy", {"target": tgt, "tgt_terrain": tterr,
                                   "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
            print(f"  {tgt:10} {tterr:8} {'wiped/none':>14}  discarded")
            continue
        per = b["lost"] / effective_units(40)
        near = lambda x: abs(per - x) < 0.03 * max(x, 1.0)
        verdict = ("CONVOY column" if near(convoy_c) and convoy_c != 1.0
                   else "flat 1.0 (= convoy land)" if near(1.0)
                   else "NEITHER")
        print(f"  {tgt:10} {tterr:8} {per:14.4f} {1.0:9.1f} {convoy_c:7.1f}"
              f"  {verdict}")


# The class sweep read one target per class: CLASS_REP. These are the SECOND,
# a different unit of the same class, so a column that rests on one reading
# gets an independent one to agree or disagree with.
CLASS_REP_2 = {"land": ("ht", 60), "air": ("tac", 60), "naval": ("cl", 40)}


def exp_class_matrix_2(p: Probe) -> None:
    """A second target for every column, because one cell is not a corroboration.

    CLASS_ATTACK's shape -- a coefficient flat across targets WITHIN a class,
    changing between classes -- was established on the land column, which has
    three independent sources. The air and naval columns were then filled one
    cell apiece and inherited the shape by assumption. That assumption is doing
    real work: it is why the engine will quote a figure for a bomber against a
    cruiser having only ever seen a bomber against a battleship.

    The defence sweep did this properly and it paid: reading two attackers per
    class turned a guess from four cells into a law with 102 confirmations, and
    it caught the balloon looking like a non-flat column when it was not. This
    is the same discipline applied to the attacking side.

    Attenuation is NOT corrected here. Air attacking anything is a post-fire
    law and the correction depends on the defender's own return fire, which
    differs between the two targets -- so a hand-correction would be comparing
    two different adjustments and calling the difference physics. Both cells go
    on the record raw, and the engine, which already implements the law and is
    tested against it, has to reproduce both from ONE coefficient. That is a
    stronger check than any arithmetic done here.
    """
    cls_of = {u: c for c, us in UNIT_CLASSES.items() for u in us}
    print(f"\n  {'unit':8} {'class':6} " + " ".join(f"{c:>12}" for c in
                                                    ("vs air", "vs naval")))
    for unit in ROSTER_ORDER:
        acls = cls_of.get(unit)
        if not acls:
            continue
        cells = []
        for tcls in ("air", "naval"):
            tgt, n = CLASS_REP_2[tcls]
            if tgt == unit:
                cells.append(f"{'(self)':>12}")
                continue
            terr = TERRAIN_PAIR[(acls, tcls)]
            # sea/air aborts the batch. The air column is read on land
            # everywhere else in this table, so a naval attacker reads it
            # there too and the two halves stay comparable.
            if acls == "naval" and tcls == "air":
                terr = ("sea", "land")
            if unit == "bal":
                terr = ("land", "land")
            ov = settings()
            ov.update(duel(1, unit, 20, tgt, n,
                           atk_terrain=terr[0], def_terrain=terr[1]))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                cells.append(f"{'refused':>12}")
                record("class_matrix_2", {"unit": unit, "target": tgt,
                                          "target_class": tcls,
                                          "refused": True}, {})
                print(f"    ! {unit} vs {tgt}: {e}"[:105], file=sys.stderr)
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("class_matrix_2", {"unit": unit, "target": tgt,
                                      "target_class": tcls, "atk_n": 20,
                                      "def_n": n, "terrain": list(terr),
                                      "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None:
                cells.append(f"{'—':>12}")
            elif (b.get("pct") or 0) >= 99.9:
                cells.append(f"{'WIPED':>12}")
            else:
                cells.append(f"{b['lost'] / effective_units(20):12.4f}")
        print(f"  {unit:8} {acls:6} " + " ".join(cells))
    print("\n  Raw per-effective-unit figures. Air attackers are attenuated, so "
          "these are NOT\n  directly comparable to CLASS_ATTACK for the fliers "
          "— the engine replay is the test.")


def exp_balloon_columns(p: Probe) -> None:
    """The balloon's own attack row, which was three copies of one reading.

    CLASS_ATTACK.bal is 3.0 against land, air and naval alike. Only the land
    figure was ever measured -- ten balloons deal 30.00 to twenty infantry and
    30.00 to twenty heavy tanks -- and the other two were filled by assuming
    the row was flat, which is the one thing a single cell cannot tell you.

    The second-target sweep read 10.0 against a bomber. That is not a small
    correction to 3.0, it is more than triple, and it is also exactly what the
    balloon DEFENDS at against air. So the row needs its own reading in each
    column rather than a shape borrowed from the units around it.
    """
    print(f"\n  {'target':8} {'class':6} {'terrain':10} {'per eff. unit':>14}")
    probes = [("inf", "land", ("land", "land")),
              ("int", "air", ("land", "land")),
              ("tac", "air", ("land", "land")),
              ("bb", "naval", ("land", "sea")),
              ("cl", "naval", ("land", "sea"))]
    seen: dict[str, list[float]] = {}
    for tgt, tcls, terr in probes:
        n = {"inf": 200, "int": 60, "tac": 60, "bb": 20, "cl": 40}[tgt]
        ov = settings()
        ov.update(duel(1, "bal", 20, tgt, n,
                       atk_terrain=terr[0], def_terrain=terr[1]))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {tgt:8} {tcls:6} {'/'.join(terr):10} {'refused':>14}  "
                  f"{e}"[:110])
            record("balloon_columns", {"target": tgt, "target_class": tcls,
                                       "refused": True}, {})
            continue
        d = dict(p.last_details)
        b = d.get("B.1.1") or {}
        record("balloon_columns", {"target": tgt, "target_class": tcls,
                                   "atk_n": 20, "def_n": n,
                                   "terrain": list(terr), "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
            print(f"  {tgt:8} {tcls:6} {'/'.join(terr):10} "
                  f"{'wiped/none':>14}  discarded")
            continue
        per = b["lost"] / effective_units(20)
        seen.setdefault(tcls, []).append(per)
        print(f"  {tgt:8} {tcls:6} {'/'.join(terr):10} {per:14.4f}")
    print()
    row = {}
    for tcls, vals in seen.items():
        if len(vals) > 1 and max(vals) - min(vals) > 0.02 * max(vals):
            print(f"  ! bal vs {tcls}: two targets disagree {vals} — the "
                  f"column is not flat")
            continue
        row[tcls] = sum(vals) / len(vals)
    print("  CLASS_ATTACK.bal = " + json.dumps(
        {k: round(v, 4) for k, v in row.items()}, sort_keys=True))
    if abs(row.get("air", 0) - 3.0) > 0.05:
        print(f"\n  The 3.0 in the air column was never measured. It reads "
              f"{row.get('air'):.1f}.")


def exp_attenuation_scope(p: Probe) -> None:
    """Which class does attenuation follow -- the target's own, or its terrain's?

    An air stack fires with what survives the round against a LAND or NAVAL
    target and with its full strength against an AIR one. Both halves are
    measured. The engine then has to decide what an air stack attacking
    EMBARKED FIGHTERS does, and the two rules it already holds disagree:

      the coefficient   comes from the target's OWN class, because an air
                        attacker is blind to embarkation (98.89 on land vs
                        98.61 at sea, where the columns are 27% apart)
      attenuation       is keyed on the target being a surface unit, and an
                        embarked fighter IS a surface unit for everyone else

    So the same target is 'air' for one rule and 'naval' for the other. That is
    either a real asymmetry or a seam in the model, and one request tells them
    apart: 20 fighters against 200 embarked fighters deal 20.0 x E(20) = 400.00
    unattenuated, and about 380 attenuated.

    The experiment this gap originally called for -- an air stack bombarding a
    target that cannot shoot back -- cannot be run. Every air unit in the
    roster bisects to a range of 5 km, and 5 km is exactly where return fire
    stops. There is no distance at which an aircraft attacks and is not
    attacked, so 'simultaneous' and 'the target shot first' cannot be separated
    that way at all.
    """
    print(f"\n  {'target':16} {'lost':>9} {'unattenuated':>13} "
          f"{'attenuated':>11}  verdict")
    for label, tterr, n in (("fighters in air", "air", 200),
                            ("fighters at sea", "sea", 200)):
        ov = settings()
        ov.update(duel(1, "int", 20, "int", n,
                       atk_terrain="air", def_terrain=tterr))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {label:16} {'refused':>9}  {e}"[:100])
            continue
        d = dict(p.last_details)
        a = d.get("A.1.1") or {}
        b = d.get("B.1.1") or {}
        record("attenuation_scope", {"target_terrain": tterr, "def_n": n,
                                     "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
            print(f"  {label:16} {'wiped/none':>9}  discarded")
            continue
        plain = 20.0 * effective_units(20)
        # The post-fire law, with the attacker's own losses from this reading.
        lost = a.get("lost") or 0.0
        hp = 60.0
        surv = 20 - int(lost // hp)
        rem = 20 * hp - lost
        att = (20.0 * effective_units(surv)
               * (0.05 + 0.95 * min(1.0, rem / (surv * hp)))) if surv else 0.0
        near = lambda x: abs(b["lost"] - x) < 0.02 * max(x, 1.0)
        verdict = ("UNATTENUATED" if near(plain) else
                   "ATTENUATED" if near(att) else "NEITHER")
        print(f"  {label:16} {b['lost']:9.2f} {plain:13.2f} {att:11.2f}  "
              f"{verdict}  (attacker lost {lost})")


# Chosen to span per-unit HP by a factor of twenty-six, because that is the
# quantity the survivor count is coarse in: lart 10, inf 20, cav 25, st 40,
# ac 60, ht 260. If the round law drifts because whole-unit survivors are a
# coarse grid, the drift has to track this column and nothing else.
MULTI_ROUND_TYPES = ["lart", "inf", "st", "ac", "ht"]


def exp_multi_round_types(p: Probe) -> None:
    """The round law across the whole per-unit-HP range, not just infantry.

    The law -- output = coefficient x E(survivors) x m(f), survivors counted as
    WHOLE units -- was fitted on fifty infantry against fifty infantry and fits
    that ladder to 0.042%. Cavalry reproduces exactly. Heavy tanks drift to
    0.5% by round four, and the standing explanation is that 260 HP per unit
    makes the whole-unit survivor count coarse.

    That explanation has never been tested, because it was written from ONE
    unit type at the far end of the range. If it is right the error should be
    monotone in per-unit HP: light artillery at 10 HP should be the cleanest
    reading in the roster and the heavy tank the worst, with three types in
    between falling in order. If the error does not track that column, the
    coarseness story is wrong and something else is going on.

    Deaths are recorded too. The printed count is the sum of per-round
    floor(round damage / per-unit HP) and reproduces ten of twelve measured
    cells; infantry rounds 3 and 4 come out one short with no explanation. A
    ladder on five types either finds that pattern again somewhere else, which
    makes it a law, or finds it nowhere, which makes it specific to that cell.
    """
    print(f"\n  {'unit':6} {'HP/unit':>8} {'rounds':>7} {'A lost':>10} "
          f"{'A died':>7} {'B lost':>10} {'B died':>7}")
    for unit in MULTI_ROUND_TYPES:
        hp = MEASURED_UNITS[unit][0]
        for rounds in range(1, 9):
            ov = settings(rounds=rounds)
            ov.update(duel(1, unit, 50, unit, 50))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                print(f"  {unit:6} {hp:8.0f} {rounds:>7}  {e}"[:100])
                continue
            d = dict(p.last_details)
            a = d.get("A.1.1") or {}
            b = d.get("B.1.1") or {}
            record("multi_round_types", {"unit": unit, "rounds": rounds,
                                         "n": 50, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            print(f"  {unit:6} {hp:8.0f} {rounds:>7} "
                  f"{a.get('lost', 0) or 0:10.2f} {a.get('died', 0) or 0:7.0f} "
                  f"{b.get('lost', 0) or 0:10.2f} {b.get('died', 0) or 0:7.0f}"
                  + ("   (both sides wiped)"
                     if (a.get('pct') or 0) >= 99.9 and (b.get('pct') or 0) >= 99.9
                     else ""))


# Level caps for the six, from the server's own refusals recorded in
# hero_caps. null in the app's table means "no cap found", which is 20.
HERO_OTHER_MAX_LEVEL: dict[str, int] = {
    "otto": 15, "togo": 20, "togo_b": 20, "ivan": 10,
    "rbaron": 20, "thaden": 15,
}

# The unit each hero buffs, established attacking, plus a control type it does
# not buff. Decomposition needs both: the control isolates the hero's OWN
# contribution and the buffed type then yields the multiplier.
HERO_OTHER_PAIR: dict[str, tuple[str, str]] = {
    "otto":   ("sub", "cl"),
    "togo":   ("bb", "cl"),
    "togo_b": ("bb", "cl"),
    "ivan":   ("bb", "cl"),
    "rbaron": ("int", "tac"),
    "thaden": ("zep", "int"),
}


def _hero_def_reading(p: Probe, hero: str | None, level: int, unit: str,
                      terr: str) -> float | None:
    """The DEFENDING stack's output, with the hero sitting on it.

    Read off the ATTACKER's losses. The defending side is not attenuated, so
    this is one request per cell with nothing to unpick afterwards.
    """
    if terr == "air":
        atk_unit, atk_n, def_terr = "int", 200, "land"
        atk_terr = "air"
    else:
        atk_unit, atk_n, def_terr = "bb", 60, "sea"
        atk_terr = "sea"
    if atk_unit == unit:
        atk_unit = "cl" if terr == "sea" else "tac"
    ov = settings()
    ov.update(duel(1, atk_unit, atk_n, unit, 20,
                   atk_terrain=atk_terr, def_terrain=def_terr))
    create: tuple[str, ...] = ()
    if hero:
        ov.update({HERO_FIELDS[0]: hero, HERO_FIELDS[1]: str(level),
                   HERO_FIELDS[2]: "100%"})
        create = HERO_FIELDS
    try:
        p.submit(ov, create=create)
    except (BareFormReturned, ValueError) as e:
        record("hero_other_defending", {"hero": hero, "level": level,
                                        "unit": unit, "terrain": terr,
                                        "error": str(e)}, {})
        print(f"    ! {hero or 'none'} lvl{level} {unit}: {e}"[:105],
              file=sys.stderr)
        return None
    d = dict(p.last_details)
    a = d.get("A.1.1") or {}
    record("hero_other_defending", {"hero": hero, "level": level, "unit": unit,
                                    "terrain": terr, "atk_unit": atk_unit,
                                    "atk_n": atk_n, "def_n": 20,
                                    "detail": d},
           {k: (v or {}).get("lost") for k, v in d.items()})
    if a.get("lost") is None or (a.get("pct") or 0) >= 99.9:
        return None
    return a["lost"]


def exp_hero_other_defending(p: Probe) -> None:
    """The six air/naval heroes on a DEFENDING stack, and up their level range.

    Every reading of these six put them on the ATTACKING side at level 10. The
    land heroes make both of those look like assumptions rather than defaults:
    thirteen of sixteen have a different attack and defence value -- Pershing
    attacks at 62 and defends at 8 -- and every output curve moves with level.
    Carrying an attacking figure into a defending battle would be inventing a
    number, so the app currently applies no hero effect at all on air and naval
    stacks. That is honest and it is also the last thing on the gap list that
    more requests can fix.

    Decomposition is the same two-configuration trick used everywhere else: a
    stack of the type the hero buffs, and a control stack of a type it does
    not. The control gives the hero's own defence value A, because

        output = coefficient x E(20) x m(1) + A

    with everything but A known; the buffed stack then gives the multiplier M
    from what is left. Reading a single stack would confound the two, which is
    the mistake the first attacking sweep made and had to be redone for.
    """
    print("\n  1. level 10 defending, decomposed\n")
    print(f"  {'hero':10} {'terr':5} {'control':>8} {'own A':>8} "
          f"{'buffed':>9} {'M':>8}")
    own: dict[str, float] = {}
    mult: dict[str, float] = {}
    for hero, terr in HERO_OTHER_TERRAIN.items():
        buffed, control = HERO_OTHER_PAIR[hero]
        base_c = _hero_def_reading(p, None, 10, control, terr)
        with_c = _hero_def_reading(p, hero, 10, control, terr)
        base_b = _hero_def_reading(p, None, 10, buffed, terr)
        with_b = _hero_def_reading(p, hero, 10, buffed, terr)
        if None in (base_c, with_c, base_b, with_b):
            print(f"  {hero:10} {terr:5} {'unreadable':>8}")
            continue
        a_own = with_c - base_c
        # The buffed stack carries the same A plus the multiplier on the rest.
        m = (with_b - a_own) / base_b if base_b else float("nan")
        own[hero] = a_own
        mult[hero] = m
        print(f"  {hero:10} {terr:5} {control:>8} {a_own:8.2f} "
              f"{buffed:>9} {m:8.4f}")
    print("\n  HERO_ATK_DEFENDING = " + json.dumps(
        {k: round(v, 2) for k, v in own.items()}, sort_keys=True))
    print("  buffs (defending)  = " + json.dumps(
        {k: round(v, 4) for k, v in mult.items()}, sort_keys=True))

    print("\n  2. the output curve, level by level, on the buffed type\n")
    curves: dict[str, dict[int, float]] = {}
    for hero, terr in HERO_OTHER_TERRAIN.items():
        buffed, control = HERO_OTHER_PAIR[hero]
        cap = HERO_OTHER_MAX_LEVEL.get(hero, 20)
        base_b = _hero_def_reading(p, None, 1, buffed, terr)
        if base_b is None:
            print(f"  {hero}: baseline unreadable, skipped")
            continue
        row: dict[int, float] = {}
        cells = []
        for lvl in range(1, cap + 1):
            v = _hero_def_reading(p, hero, lvl, buffed, terr)
            if v is None:
                cells.append(f"{lvl}:—")
                continue
            # Subtract the hero's own contribution at THIS level, which is not
            # known yet -- so record the raw figure and let the fit run
            # offline rather than pretending the split is free.
            row[lvl] = v
            cells.append(f"{lvl}:{v:.1f}")
        curves[hero] = row
        print(f"  {hero:10} " + " ".join(cells))
    print("\n  raw defending output by level = " + json.dumps(
        {h: {str(k): round(v, 2) for k, v in r.items()}
         for h, r in curves.items()}, sort_keys=True))


def exp_hero_air_attacking(p: Probe) -> None:
    """Richthofen and von Thaden attacking, read where nothing is attenuated.

    Their attacking values were read against a GROUND target, and air attacking
    ground is a post-fire law -- so the figure on record confounds the hero's
    own attack with the attenuation of the whole stack. It shows: the four
    naval heroes decompose to 40.00, 15.00, 64.32 and 1.00, and these two to
    16.80 and 10.07. Round numbers and unround ones, split exactly along the
    line of which readings were attenuated.

    Air attacking AIR is not attenuated -- twenty fighters lose 58% of their
    pool to two hundred fighters and still deal their full figure -- so the
    same decomposition against an air target has nothing to unpick.
    """
    print(f"\n  {'hero':8} {'control':>8} {'base':>9} {'with':>9} "
          f"{'own A':>8}   recorded")
    recorded = {"rbaron": 16.80, "thaden": 10.07}
    for hero, control, buffed in (("rbaron", "tac", "int"),
                                  ("thaden", "int", "zep")):
        vals = {}
        for label, unit in (("control", control), ("buffed", buffed)):
            for who in (None, hero):
                ov = settings()
                ov.update(duel(1, unit, 10, "tac" if unit != "tac" else "int",
                               200, atk_terrain="air", def_terrain="air"))
                create: tuple[str, ...] = ()
                if who:
                    ov.update({HERO_ATK_FIELDS[0]: who,
                               HERO_ATK_FIELDS[1]: "10",
                               HERO_ATK_FIELDS[2]: "100%"})
                    create = HERO_ATK_FIELDS
                try:
                    p.submit(ov, create=create)
                except (BareFormReturned, ValueError) as e:
                    print(f"    ! {hero} {label} {unit}: {e}"[:100],
                          file=sys.stderr)
                    continue
                d = dict(p.last_details)
                b = d.get("B.1.1") or {}
                record("hero_air_attacking", {"hero": who, "unit": unit,
                                              "role": label, "level": 10,
                                              "atk_n": 10, "detail": d},
                       {k: (v or {}).get("lost") for k, v in d.items()})
                if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                    continue
                vals[(label, bool(who))] = b["lost"]
        base = vals.get(("control", False))
        with_ = vals.get(("control", True))
        if base is None or with_ is None:
            print(f"  {hero:8} {'unreadable':>8}")
            continue
        print(f"  {hero:8} {control:>8} {base:9.2f} {with_:9.2f} "
              f"{with_ - base:8.2f}   {recorded[hero]:8.2f}")
        bb_, bw = vals.get(("buffed", False)), vals.get(("buffed", True))
        if bb_ is not None and bw is not None:
            print(f"           {buffed:>8} {bb_:9.2f} {bw:9.2f} "
                  f"{'excess':>8} {bw - bb_:8.2f}")


def exp_hero_other_curves(p: Probe) -> None:
    """The attacking output curves for the four air/naval heroes that buff.

    Read on a SINGLE-TYPE stack against a target of the hero's own class, so
    nothing is attenuated and nothing has to be subtracted but the hero's own
    attack, which is now known exactly:

        output = coefficient x M x E(10) + A

    Everything but M is known, so one request per level gives the curve
    directly. The defending curve for Tōgō came out a clean staircase in pairs
    of levels -- 1.00, 1.15, 1.20, 1.25, 1.30, 1.34, 1.38, 1.42, 1.46, 1.50 --
    and these are read the same way to see whether the attacking channel moves
    on the same ladder.
    """
    setups = [("rbaron", "int", 20.0, 70.0, 20, "air"),
              ("thaden", "zep", 5.0, 10.0, 15, "air"),
              ("otto", "sub", 40.0, 40.0, 15, "sea"),
              ("togo", "bb", 40.0, 15.0, 20, "sea"),
              ("togo_b", "bb", 40.0, 64.32, 20, "sea")]
    out: dict[str, dict[int, float]] = {}
    for hero, unit, coef, own, cap, terr in setups:
        target = {"air": "tac", "sea": "cl"}[terr]
        if unit == target:
            target = "int" if terr == "air" else "sub"
        cells = []
        row: dict[int, float] = {}
        for lvl in range(1, cap + 1):
            ov = settings()
            ov.update(duel(1, unit, 10, target, 200,
                           atk_terrain=terr, def_terrain=terr))
            ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: str(lvl),
                       HERO_ATK_FIELDS[2]: "100%"})
            try:
                p.submit(ov, create=HERO_ATK_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"    ! {hero} lvl{lvl}: {e}"[:100], file=sys.stderr)
                cells.append(f"{lvl}:—")
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("hero_other_curves", {"hero": hero, "unit": unit,
                                         "level": lvl, "atk_n": 10,
                                         "terrain": terr, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                cells.append(f"{lvl}:—")
                continue
            m = (b["lost"] - own) / (coef * effective_units(10))
            row[lvl] = m
            cells.append(f"{lvl}:{m:.2f}")
        out[hero] = row
        print(f"  {hero:8} {unit:5} " + " ".join(cells))
    print("\n  attacking multipliers by level = " + json.dumps(
        {h: {str(k): round(v, 4) for k, v in r.items()}
         for h, r in out.items()}, sort_keys=True))


def exp_hero_own_curves(p: Probe) -> None:
    """Does the hero's OWN attack move with level, as well as its multiplier?

    The attacking curves were computed by subtracting a level-10 own-attack
    value at every level, and two of the five came out below 1.00 at low levels
    -- Richthofen 0.775 at level 1, Tōgō w/bombardment 0.90. A multiplier below
    one would mean a hero makes its own stack worse, which nothing else in the
    record does. Over-subtracting produces exactly that artifact, so the likely
    reading is that A itself is smaller at level 1 and the constant was wrong.

    This is the same trap the land-hero curves were re-read to escape: a curve
    measured by subtracting a baseline is only as good as the baseline, and a
    baseline measured at one level is not a constant until someone checks.

    The CONTROL type settles it. On a stack the hero does not buff there is no
    multiplier to confound anything, so the excess IS A, level by level.
    """
    setups = [("rbaron", "tac", 3.0, 20, "air"),
              ("togo_b", "cl", 10.0, 20, "sea"),
              ("thaden", "int", 20.0, 15, "air"),
              ("otto", "cl", 10.0, 15, "sea"),
              ("togo", "cl", 10.0, 20, "sea")]
    out: dict[str, dict[int, float]] = {}
    for hero, control, coef, cap, terr in setups:
        # thaden and otto and togo showed no anomaly, so they are spot-checked
        # at the ends rather than swept -- and if an end disagrees with the
        # level-10 value, the whole ladder gets bought.
        levels = (list(range(1, cap + 1)) if hero in ("rbaron", "togo_b")
                  else [1, 10, cap])
        target = {"air": "tac", "sea": "cl"}[terr]
        if control == target:
            target = "int" if terr == "air" else "sub"
        row: dict[int, float] = {}
        cells = []
        for lvl in levels:
            ov = settings()
            ov.update(duel(1, control, 10, target, 200,
                           atk_terrain=terr, def_terrain=terr))
            ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: str(lvl),
                       HERO_ATK_FIELDS[2]: "100%"})
            try:
                p.submit(ov, create=HERO_ATK_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"    ! {hero} lvl{lvl}: {e}"[:100], file=sys.stderr)
                cells.append(f"{lvl}:—")
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("hero_own_curves", {"hero": hero, "control": control,
                                       "level": lvl, "atk_n": 10,
                                       "terrain": terr, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                cells.append(f"{lvl}:—")
                continue
            A = b["lost"] - coef * effective_units(10)
            row[lvl] = A
            cells.append(f"{lvl}:{A:.1f}")
        out[hero] = row
        flat = (len(set(round(v, 2) for v in row.values())) == 1) if row else False
        print(f"  {hero:8} {control:5} " + " ".join(cells)
              + ("   FLAT" if flat else "   MOVES WITH LEVEL"))
    print("\n  own attack by level = " + json.dumps(
        {h: {str(k): round(v, 2) for k, v in r.items()}
         for h, r in out.items()}, sort_keys=True))


def exp_hero_class_columns(p: Probe) -> None:
    """Does a HERO have attack columns by target class, as a unit does?

    Richthofen decomposes to 70.0 against an air target and the older sweep,
    against a GROUND target, read 16.80. I took the second for an attenuation
    artifact of the first. Attenuation cannot explain a factor of four: the
    stack in that reading was attenuated by 1.6%, so 70.0 would have shown as
    68.9, not 16.85. Both numbers are real and the hero has a target-class
    column exactly as every unit does.

    Reading it needs a stack big enough that attenuation is negligible rather
    than corrected, because a correction here would be fitting the law to the
    thing being measured. A hundred bombers hold 8000 HP and two thousand
    infantry deal 0.4 x E(50) = 14.0 to them -- 0.175% of the pool -- so the
    post-fire factor is 0.9983 and the excess IS the hero's own attack.
    """
    print(f"\n  {'hero':8} {'control':>8} {'target':>8} {'base':>10} "
          f"{'with hero':>10} {'own A':>9}")
    setups = [("rbaron", "tac", 30.0), ("thaden", "int", 5.0)]
    targets = [("inf", 2000, "land"), ("bb", 400, "naval"), ("tac", 2000, "air")]
    out: dict[str, dict[str, float]] = {}
    for hero, control, _coef in setups:
        for tgt, tn, tcls in targets:
            if tgt == control:
                tgt, tn = ("int", 2000)
            vals = []
            for who in (None, hero):
                ov = settings()
                ov.update(duel(1, control, 100, tgt, tn, atk_terrain="air",
                               def_terrain="land" if tcls == "land" else
                               ("sea" if tcls == "naval" else "air")))
                create: tuple[str, ...] = ()
                if who:
                    ov.update({HERO_ATK_FIELDS[0]: who,
                               HERO_ATK_FIELDS[1]: "10",
                               HERO_ATK_FIELDS[2]: "100%"})
                    create = HERO_ATK_FIELDS
                try:
                    p.submit(ov, create=create)
                except (BareFormReturned, ValueError) as e:
                    print(f"    ! {hero} vs {tgt}: {e}"[:100], file=sys.stderr)
                    vals.append(None)
                    continue
                d = dict(p.last_details)
                b = d.get("B.1.1") or {}
                a = d.get("A.1.1") or {}
                record("hero_class_columns",
                       {"hero": who, "control": control, "target": tgt,
                        "target_class": tcls, "atk_n": 100, "def_n": tn,
                        "detail": d},
                       {k: (v or {}).get("lost") for k, v in d.items()})
                vals.append(None if (b.get("lost") is None
                                     or (b.get("pct") or 0) >= 99.9)
                            else (b["lost"], (a.get("pct") or 0)))
            if None in vals:
                print(f"  {hero:8} {control:>8} {tgt:>8} {'unreadable':>10}")
                continue
            (base, _), (with_, atk_pct) = vals
            out.setdefault(hero, {})[tcls] = with_ - base
            print(f"  {hero:8} {control:>8} {tgt:>8} {base:10.2f} "
                  f"{with_:10.2f} {with_ - base:9.2f}"
                  f"   (attacker lost {atk_pct}%)")
    print("\n  hero own attack by TARGET class = " + json.dumps(
        {h: {c: round(v, 2) for c, v in r.items()} for h, r in out.items()},
        sort_keys=True))


def exp_hero_columns_small(p: Probe) -> None:
    """The hero class columns again, on a stack of TEN.

    The hundred-unit version of this was unreadable and it is worth saying why
    rather than quietly re-running it. E(n) saturates at 35 by fifty units, so
    a hero joining a stack of a hundred adds E(101) - E(100) = 0 -- or, if it
    sits first, adds its own value and takes E(1) away from the units. Either
    way the reading is a DIFFERENCE of two large numbers that mostly cancel,
    and it came back saying von Thaden's air attack is 20.0 where a clean
    ten-unit stack says 10.0. The stack was chosen to make attenuation
    negligible and it made the decomposition ambiguous instead.

    Ten units is below the knee, where E is linear and adding the hero shifts
    nothing. Attenuation is then real but READABLE: the attacker's own loss is
    printed, so the post-fire factor comes out of the same response.
    """
    print(f"\n  {'hero':8} {'control':>8} {'target':>7} {'base':>9} "
          f"{'with':>9} {'raw':>8} {'atk lost':>9} {'corrected':>10}")
    out: dict[str, dict[str, float]] = {}
    for hero, control, hp in (("rbaron", "tac", 80.0), ("thaden", "int", 60.0)):
        for tgt, tn, tcls in (("inf", 400, "land"), ("bb", 60, "naval"),
                              ("zep", 400, "air")):
            vals = []
            for who in (None, hero):
                ov = settings()
                ov.update(duel(1, control, 10, tgt, tn, atk_terrain="air",
                               def_terrain={"land": "land", "naval": "sea",
                                            "air": "air"}[tcls]))
                create: tuple[str, ...] = ()
                if who:
                    ov.update({HERO_ATK_FIELDS[0]: who,
                               HERO_ATK_FIELDS[1]: "10",
                               HERO_ATK_FIELDS[2]: "100%"})
                    create = HERO_ATK_FIELDS
                try:
                    p.submit(ov, create=create)
                except (BareFormReturned, ValueError) as e:
                    print(f"    ! {hero} vs {tgt}: {e}"[:100], file=sys.stderr)
                    vals.append(None)
                    continue
                d = dict(p.last_details)
                b = d.get("B.1.1") or {}
                a = d.get("A.1.1") or {}
                record("hero_columns_small",
                       {"hero": who, "control": control, "target": tgt,
                        "target_class": tcls, "atk_n": 10, "def_n": tn,
                        "detail": d},
                       {k: (v or {}).get("lost") for k, v in d.items()})
                vals.append(None if (b.get("lost") is None
                                     or (b.get("pct") or 0) >= 99.9)
                            else (b["lost"], a.get("lost") or 0.0))
            if None in vals:
                print(f"  {hero:8} {control:>8} {tgt:>7} {'unreadable':>9}")
                continue
            (base, _), (with_, lost) = vals
            raw = with_ - base
            # The post-fire factor this stack fired at, from its own losses.
            pool = 10 * hp
            surv = 10 - int(lost // hp)
            factor = ((effective_units(surv) / effective_units(10))
                      * (0.05 + 0.95 * min(1.0, (pool - lost) / (surv * hp)))
                      if surv else 0.0)
            corrected = raw / factor if factor else float("nan")
            out.setdefault(hero, {})[tcls] = corrected
            print(f"  {hero:8} {control:>8} {tgt:>7} {base:9.2f} {with_:9.2f} "
                  f"{raw:8.2f} {lost:9.2f} {corrected:10.2f}")
    print("\n  hero own attack by TARGET class (ten-unit stack) = " + json.dumps(
        {h: {c: round(v, 2) for c, v in r.items()} for h, r in out.items()},
        sort_keys=True))


def exp_togo_b_disagreement(p: Probe) -> None:
    """One hero reads two different own-attack values. Which reading moves?

    Tōgō-with-bombardment at level 10, decomposed off a light-cruiser control
    stack, reads 64.34 against a battleship and 64.90 against a submarine. Two
    targets of the same class, where every other hero and every unit in the
    table is flat within a class. Something in one of the two configurations is
    not what it looks like.

    The two sweeps differed in more than the target: one sent 30 defenders and
    the other 200. So the grid crosses TARGET TYPE with TARGET COUNT rather
    than changing both at once, which is the mistake that produced the
    ambiguity in the first place. A third naval target goes in as well, because
    two points cannot show which of them is the odd one.

    Plain Tōgō runs alongside as the control on the control: it shares the
    hull, the pool and the level cap and differs only in the bombardment, so if
    the effect follows the bombardment it should be absent from plain Tōgō and
    present here.
    """
    print(f"\n  {'hero':8} {'target':>7} {'count':>6} {'B lost':>9} "
          f"{'A lost':>9} {'A pct':>7} {'own A':>8}")
    grid: dict[tuple[str, str, int], float] = {}
    for hero in ("togo_b", "togo"):
        for tgt in ("bb", "sub", "cl"):
            for n in (30, 200):
                ov = settings()
                ov.update(duel(1, "cl", 10, tgt, n,
                               atk_terrain="sea", def_terrain="sea"))
                ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: "10",
                           HERO_ATK_FIELDS[2]: "100%"})
                try:
                    p.submit(ov, create=HERO_ATK_FIELDS)
                except (BareFormReturned, ValueError) as e:
                    print(f"  {hero:8} {tgt:>7} {n:>6}  {e}"[:100])
                    continue
                d = dict(p.last_details)
                b = d.get("B.1.1") or {}
                a = d.get("A.1.1") or {}
                record("togo_b_disagreement",
                       {"hero": hero, "target": tgt, "def_n": n, "atk_n": 10,
                        "level": 10, "detail": d},
                       {k: (v or {}).get("lost") for k, v in d.items()})
                if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                    print(f"  {hero:8} {tgt:>7} {n:>6} {'wiped/none':>9}")
                    continue
                own = b["lost"] - 10.0 * effective_units(10)
                grid[(hero, tgt, n)] = own
                print(f"  {hero:8} {tgt:>7} {n:>6} {b['lost']:9.2f} "
                      f"{a.get('lost') or 0:9.2f} {a.get('pct') or 0:7.1f} "
                      f"{own:8.2f}")

    print()
    for hero in ("togo_b", "togo"):
        vals = {k[1:]: v for k, v in grid.items() if k[0] == hero}
        if not vals:
            continue
        by_target = {}
        by_count = {}
        for (tgt, n), v in vals.items():
            by_target.setdefault(tgt, []).append(v)
            by_count.setdefault(n, []).append(v)
        spread = max(vals.values()) - min(vals.values())
        print(f"  {hero}: spread {spread:.3f} over {len(vals)} cells")
        for tgt, vs in sorted(by_target.items()):
            print(f"    by target {tgt:>4}: {[round(x, 2) for x in vs]}")
        for n, vs in sorted(by_count.items()):
            print(f"    by count {n:>5}: {[round(x, 2) for x in vs]}")
        if spread < 0.02:
            print(f"    FLAT — the earlier disagreement was not the target.")


def exp_togo_b_shape(p: Probe) -> None:
    """Tōgō-with-bombardment's contribution is not a constant. What is it?

    The crossed grid ruled out the obvious answer. Plain Tōgō contributes
    exactly 15.00 in all six cells of target-type x target-count; the
    bombardment variant ranges 56.92 to 64.90 over the same six, so the effect
    belongs to this hero and not to the configuration. Target TYPE does not
    move it -- a battleship and a submarine at the same count read 64.34 and
    64.32 -- and target COUNT does, which is the wrong shape for anything the
    rest of the model contains.

    This sweep walks the defender count on one target type, and then the
    attacker count on one defender, so the two axes are separated instead of
    inferred from four scattered cells. Plain Tōgō runs at the ends as the
    control: if the ladder moves for one and not the other, the bombardment is
    the whole difference.
    """
    print(f"\n  {'hero':8} {'atk n':>6} {'def n':>6} {'B lost':>9} "
          f"{'units':>8} {'hero':>8} {'hero lost':>10}")
    def cell(hero: str, an: int, dn: int) -> None:
        ov = settings()
        ov.update(duel(1, "cl", an, "cl", dn,
                       atk_terrain="sea", def_terrain="sea"))
        ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: "10",
                   HERO_ATK_FIELDS[2]: "100%"})
        try:
            p.submit(ov, create=HERO_ATK_FIELDS)
        except (BareFormReturned, ValueError) as e:
            print(f"  {hero:8} {an:>6} {dn:>6}  {e}"[:100])
            return
        d = dict(p.last_details)
        b = d.get("B.1.1") or {}
        h = d.get("A.1.hero") or {}
        record("togo_b_shape", {"hero": hero, "atk_n": an, "def_n": dn,
                                "level": 10, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
            print(f"  {hero:8} {an:>6} {dn:>6} {'wiped/none':>9}")
            return
        units = 10.0 * effective_units(an)
        print(f"  {hero:8} {an:>6} {dn:>6} {b['lost']:9.2f} {units:8.2f} "
              f"{b['lost'] - units:8.2f} {h.get('lost') or 0:10.2f}")

    print("\n  defender count, attacker fixed at 10\n")
    for dn in (10, 20, 30, 50, 100, 200):
        cell("togo_b", 10, dn)
    for dn in (10, 200):
        cell("togo", 10, dn)
    print("\n  attacker count, defender fixed at 200\n")
    for an in (5, 20, 40):
        cell("togo_b", an, 200)
    cell("togo", 20, 200)


def exp_togo_b_kind(p: Probe) -> None:
    """A different KIND of variable, since both count axes are crossed and flat.

    Tōgō-with-bombardment's contribution moves with stack sizes and nothing in
    the model moves with stack sizes that way. The name is the remaining clue:
    a BOMBARDMENT is a ranged attack, and this project has just established
    that past 5 km a defender does not fire back at all. If the hero's
    contribution is really a bombardment resolved separately, distance should
    do something to it that it does not do to plain Tōgō.

    Three axes, one at a time, against a fixed pair that reads 63.91 today:
    distance, rounds, and the hero's own HP percentage -- which every reading
    so far has left at 100 and never varied.
    """
    base_units = 10.0 * (effective_units(11) - 1)

    def cell(label: str, hero: str, **kw) -> None:
        ov = settings(rounds=kw.pop("rounds", 1))
        ov.update(duel(1, "cl", 10, "cl", 200,
                       atk_terrain="sea", def_terrain="sea"))
        ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: "10",
                   HERO_ATK_FIELDS[2]: kw.pop("hero_hp", "100%")})
        create = HERO_ATK_FIELDS
        dist = kw.pop("distance", None)
        if dist is not None:
            ov["A.1.position"] = "0"
            ov["B.1.position"] = str(dist)
            create = create + ("A.1.position", "B.1.position")
        try:
            p.submit(ov, create=create)
        except (BareFormReturned, ValueError) as e:
            print(f"  {label:24} {hero:8} {'no result':>10}   {e}"[:105])
            return
        d = dict(p.last_details)
        b = d.get("B.1.1") or {}
        h = d.get("A.1.hero") or {}
        record("togo_b_kind", {"probe": label, "hero": hero, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
            print(f"  {label:24} {hero:8} {'wiped/none':>10}")
            return
        print(f"  {label:24} {hero:8} {b['lost']:10.2f} "
              f"{b['lost'] - base_units:9.2f}   hero pool "
              f"{h.get('pool')} lost {h.get('lost')}")

    print(f"\n  {'configuration':24} {'hero':8} {'B lost':>10} "
          f"{'contrib':>9}")
    print("\n  baseline\n")
    cell("distance 0", "togo_b")
    cell("distance 0", "togo")
    print("\n  distance — past 5 km the defender cannot answer\n")
    for dist in (4, 6, 20, 40):
        cell(f"distance {dist}", "togo_b", distance=dist)
    cell("distance 20", "togo", distance=20)
    print("\n  rounds\n")
    for r in (2, 3):
        cell(f"rounds {r}", "togo_b", rounds=r)
    print("\n  the hero's own HP, never varied before\n")
    for hp in ("50%", "10%"):
        cell(f"hero hp {hp}", "togo_b", hero_hp=hp)
        cell(f"hero hp {hp}", "togo", hero_hp=hp)


def exp_hero_hp_scaling(p: Probe) -> None:
    """Does a hero's own output scale with its own HP, like a unit's?

    Every hero reading in this project set the hero to 100% and never varied
    it, so the question was never asked. It has an answer and it is the law
    already in the model for units:

        Togo at 100%  contributes 15.00
        Togo at  50%  contributes  7.88   = 15.0 x m(0.50) = 15.0 x 0.525
        Togo at  10%  contributes  2.17   = 15.0 x m(0.10) = 15.0 x 0.145

    Two decimal places, twice. If that holds for the land heroes too it is a
    general law and the engine is missing it for all twenty-two -- a hero on a
    battered stack has been contributing its full value in every result this
    app has ever produced.
    """
    print(f"\n  {'hero':12} {'unit':5} {'hp':>5} {'B lost':>9} "
          f"{'contrib':>9} {'predicted':>10} {'m(f)':>7}")
    for hero, unit, coef in (("pershing", "inf", 4.0), ("larab", "inf", 4.0),
                             ("alvin", "st", 25.0), ("kangal", "ac", 6.0)):
        base = None
        for hp in ("100%", "75%", "50%", "25%"):
            ov = settings()
            ov.update(duel(1, unit, 10, "inf", 400))
            ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: "10",
                       HERO_ATK_FIELDS[2]: hp})
            try:
                p.submit(ov, create=HERO_ATK_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"  {hero:12} {unit:5} {hp:>5}  {e}"[:100])
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            h = d.get("A.1.hero") or {}
            record("hero_hp_scaling", {"hero": hero, "unit": unit,
                                       "hero_hp": hp, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                print(f"  {hero:12} {unit:5} {hp:>5} {'wiped/none':>9}")
                continue
            # The hero outranks these coefficients, so it saturates first and
            # the units take E(11) - E(1) = 10.
            contrib = b["lost"] - coef * (effective_units(11) - 1)
            f = int(hp.rstrip("%")) / 100
            if base is None:
                base = contrib
            m = 0.05 + 0.95 * f
            print(f"  {hero:12} {unit:5} {hp:>5} {b['lost']:9.2f} "
                  f"{contrib:9.2f} {base * m:10.2f} {m:7.4f}"
                  + ("   <-- differs" if abs(contrib - base * m) > 0.05 else ""))


def exp_land_hero_attacking(p: Probe) -> None:
    """Re-decompose every land hero ATTACKING, with a control it does not buff.

    HERO_ATK_ATTACKING says Pershing attacks at 62.00. Against ten infantry it
    contributes 20.00, and that 20.00 decomposes cleanly across an HP ladder
    into an own attack of 8.00 and a constant 12.00 -- which is exactly
    40 x 0.30, an infantry buff of 1.30 on units contributing 40. So 62.00 is
    an own attack and a buff added together, and the app has no infantry buff
    for Pershing at all. It quotes 102.00 where the server says 60.00.

    That is the conflation this project has already had to undo twice, and the
    fix is the same both times: read TWO stack types, one the hero might buff
    and one it cannot. Three go in here -- light artillery and cavalry appear
    in no measured buff list, and infantry is the type most heroes touch.
    Where all three agree the excess is the hero's own attack; where infantry
    disagrees, the difference names the buff.
    """
    probes = [("lart", 5.0), ("cav", 15.0), ("inf", 4.0)]
    print(f"\n  {'hero':12} " + " ".join(f"{u:>9}" for u, _ in probes)
          + "   reading")
    out: dict[str, dict[str, float]] = {}
    for hero in sorted(HERO_ATK_ATTACKING):
        cells = []
        row: dict[str, float] = {}
        for unit, coef in probes:
            ov = settings()
            ov.update(duel(1, unit, 10, "inf", 400))
            ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: "10",
                       HERO_ATK_FIELDS[2]: "100%"})
            try:
                p.submit(ov, create=HERO_ATK_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"    ! {hero} {unit}: {e}"[:100], file=sys.stderr)
                cells.append(f"{'—':>9}")
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("land_hero_attacking",
                   {"hero": hero, "unit": unit, "level": 10, "atk_n": 10,
                    "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                cells.append(f"{'wiped':>9}")
                continue
            # Whether the hero saturates first depends on its own value, which
            # is what is being measured -- so BOTH placements are solved and
            # the one that gives a consistent answer across the three probes
            # wins. Below the knee they coincide: E(11) - E(1) = E(10) = 10.
            excess = b["lost"] - coef * (effective_units(11) - 1)
            row[unit] = excess
            cells.append(f"{excess:9.2f}")
        out[hero] = row
        vals = [v for u, v in row.items() if u != "inf"]
        note = ""
        if len(vals) == 2:
            if abs(vals[0] - vals[1]) < 0.05:
                own = vals[0]
                inf_x = row.get("inf")
                if inf_x is not None and abs(inf_x - own) > 0.05:
                    m = 1 + (inf_x - own) / (4.0 * effective_units(10))
                    note = f"own {own:.2f}, INFANTRY BUFF x{m:.4f}"
                else:
                    note = f"own {own:.2f}, no buff on these three"
            else:
                note = f"controls DISAGREE {vals} — one of them is buffed too"
        recorded = HERO_ATK_ATTACKING.get(hero)
        if note.startswith("own") and recorded is not None:
            own = float(note.split()[1].rstrip(","))
            if abs(own - recorded) > 0.05:
                note += f"  <-- table says {recorded:.2f}"
        print(f"  {hero:12} " + " ".join(cells) + f"   {note}")
    print("\n  raw excesses = " + json.dumps(
        {h: {u: round(v, 2) for u, v in r.items()} for h, r in out.items()},
        sort_keys=True))


# The six land types the lart/cav/inf probe did not cover. Coefficients are the
# land column of the attack table, which is corroborated three ways.
LAND_SCREEN_REST = [("ac", 6.0), ("art", 8.0), ("rrg", 20.0),
                    ("lt", 30.0), ("ht", 45.0), ("st", 25.0)]


def exp_land_hero_screen(p: Probe) -> None:
    """Which land types does each hero buff ATTACKING? Never screened.

    HERO_BUFF_CHANNEL records which SIDE a known buff acts on, and the buffs it
    knows about were found by a screen run on DEFENDING stacks. A buff that
    acts only when attacking is invisible to that screen -- it measures zero
    and gets recorded as absent.

    The air heroes proved that channel has both signs: Richthofen, von Thaden
    and Hersing all read exactly 1.0000 defending. The three-type probe then
    found the mirror on land. Pershing buffs infantry AND cavalry at 1.30 with
    the app holding no buff for it at all, and quoting an own attack of 62.00
    that is 8.00 plus a buff. Allenby buffs cavalry.

    So this fills the screen out: every land hero against the remaining six
    land types, with the light-artillery reading from the previous sweep as the
    unbuffed baseline for each hero.
    """
    print(f"\n  {'hero':12} {'own':>6} " + " ".join(f"{u:>7}" for u, _ in
                                                    LAND_SCREEN_REST))
    own_by_hero: dict[str, float] = {}
    for line in open(RESULTS_PATH):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("experiment") != "land_hero_attacking":
            continue
        m = r.get("meta") or {}
        if m.get("unit") != "lart":
            continue
        b = ((m.get("detail") or {}).get("B.1.1") or {})
        if b.get("lost") is None:
            continue
        own_by_hero[m["hero"]] = b["lost"] - 5.0 * (effective_units(11) - 1)

    found: dict[str, dict[str, float]] = {}
    for hero in sorted(own_by_hero):
        own = own_by_hero[hero]
        cells = []
        for unit, coef in LAND_SCREEN_REST:
            ov = settings()
            ov.update(duel(1, unit, 10, "inf", 400))
            ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: "10",
                       HERO_ATK_FIELDS[2]: "100%"})
            try:
                p.submit(ov, create=HERO_ATK_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"    ! {hero} {unit}: {e}"[:100], file=sys.stderr)
                cells.append(f"{'—':>7}")
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("land_hero_screen",
                   {"hero": hero, "unit": unit, "level": 10, "atk_n": 10,
                    "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                cells.append(f"{'wiped':>7}")
                continue
            excess = b["lost"] - coef * (effective_units(11) - 1)
            if abs(excess - own) < 0.05:
                cells.append(f"{'-':>7}")
            else:
                m_ = 1 + (excess - own) / (coef * effective_units(10))
                found.setdefault(hero, {})[unit] = round(m_, 4)
                cells.append(f"x{m_:6.4f}")
        print(f"  {hero:12} {own:6.2f} " + " ".join(cells))
    print("\n  ATTACKING buffs found on the six new types = " + json.dumps(
        found, sort_keys=True))


# The buffs the attacking screen found that the app has no record of, with the
# type used to read each curve and that type's land coefficient.
NEW_BUFFS = {
    "pershing": ("ht", 45.0, 20),
    "allen":    ("cav", 15.0, 15),
    "georg":    ("art", 8.0, 20),
    "marco":    ("lt", 30.0, 10),
}


def _screen_cell(p: Probe, hero: str | None, level: int, unit: str,
                 side: str) -> float | None:
    """One reading, hero on whichever side, returning that side's output."""
    ov = settings()
    if side == "attack":
        ov.update(duel(1, unit, 10, "inf", 400))
        fields = HERO_ATK_FIELDS
        row = "B.1.1"
    else:
        ov.update(duel(1, "inf", 400, unit, 10))
        fields = HERO_FIELDS
        row = "A.1.1"
    create: tuple[str, ...] = ()
    if hero:
        ov.update({fields[0]: hero, fields[1]: str(level), fields[2]: "100%"})
        create = fields
    try:
        p.submit(ov, create=create)
    except (BareFormReturned, ValueError) as e:
        print(f"    ! {hero or 'none'} {unit} {side}: {e}"[:100], file=sys.stderr)
        return None
    d = dict(p.last_details)
    cell = d.get(row) or {}
    record("hero_new_buffs", {"hero": hero, "level": level, "unit": unit,
                              "side": side, "detail": d},
           {k: (v or {}).get("lost") for k, v in d.items()})
    if cell.get("lost") is None or (cell.get("pct") or 0) >= 99.9:
        return None
    return cell["lost"]


def exp_hero_new_buffs(p: Probe) -> None:
    """The channel and the curve for four buffs the app does not have.

    The attacking screen found five heroes buffing types nobody had recorded,
    and four of them the app holds no buff for at all: Pershing on infantry,
    cavalry, armoured cars, light and heavy tanks; Allenby on cavalry; Georg on
    artillery; Marco on light tanks. Their own attack values are wrong by the
    same amount, because 62.00 for Pershing is 8.00 plus a buff added together.

    Two things are needed before any of it can go in the table. WHICH SIDE the
    buff acts on -- a defending screen found none of these, which is evidence
    it is attack-only but not proof, since that screen may simply not have
    tried these types. And the CURVE, because every hero curve in this project
    moves with level and quoting a level-10 figure as a constant is the error
    that produced this whole sweep.
    """
    print("\n  1. the channel: does the buff act on a DEFENDING stack too?\n")
    print(f"  {'hero':10} {'unit':5} {'base':>9} {'with hero':>10} "
          f"{'implied M':>10}   verdict")
    channels: dict[str, str] = {}
    for hero, (unit, coef, cap) in NEW_BUFFS.items():
        base = _screen_cell(p, None, 10, unit, "defend")
        with_ = _screen_cell(p, hero, 10, unit, "defend")
        if base is None or with_ is None:
            print(f"  {hero:10} {unit:5} {'unreadable':>9}")
            continue
        # The hero's own DEFENDING value is in the table already and is small
        # for all four, so it sits behind these units and takes E(11)-E(10).
        own_def = {"pershing": 8.0, "allen": 10.0, "georg": 6.0,
                   "marco": 15.0}[hero]
        own_part = own_def * (effective_units(11) - effective_units(10))
        m = (with_ - own_part) / base if base else float("nan")
        verdict = "ATTACK-ONLY" if abs(m - 1.0) < 0.01 else f"also defending"
        channels[hero] = "attack" if abs(m - 1.0) < 0.01 else "both"
        print(f"  {hero:10} {unit:5} {base:9.2f} {with_:10.2f} {m:10.4f}   "
              f"{verdict}")

    print("\n  2. is the hero's own attack flat with level?\n")
    own_curves: dict[str, dict[int, float]] = {}
    for hero, (unit, coef, cap) in NEW_BUFFS.items():
        cells = []
        for lvl in (1, 10, cap):
            v = _screen_cell(p, hero, lvl, "lart", "attack")
            if v is None:
                cells.append(f"{lvl}:—")
                continue
            own = v - 5.0 * (effective_units(11) - 1)
            own_curves.setdefault(hero, {})[lvl] = own
            cells.append(f"{lvl}:{own:.2f}")
        vals = list(own_curves.get(hero, {}).values())
        flat = len(set(round(x, 2) for x in vals)) == 1 if vals else False
        print(f"  {hero:10} " + " ".join(cells)
              + ("   FLAT" if flat else "   MOVES WITH LEVEL"))

    print("\n  3. the curve, level by level\n")
    out: dict[str, dict[int, float]] = {}
    for hero, (unit, coef, cap) in NEW_BUFFS.items():
        cells = []
        for lvl in range(1, cap + 1):
            v = _screen_cell(p, hero, lvl, unit, "attack")
            if v is None:
                cells.append(f"{lvl}:—")
                continue
            oc = own_curves.get(hero, {})
            own = oc.get(lvl, oc.get(10))
            if own is None:
                cells.append(f"{lvl}:?")
                continue
            m = (v - own) / (coef * effective_units(10))
            out.setdefault(hero, {})[lvl] = round(m, 4)
            cells.append(f"{lvl}:{m:.2f}")
        print(f"  {hero:10} {unit:5} " + " ".join(cells))
    print("\n  curves = " + json.dumps(out, sort_keys=True))
    print("  channels = " + json.dumps(channels, sort_keys=True))


def exp_hank_sides(p: Probe) -> None:
    """Does hank's infantry buff differ by side, or is one curve point wrong?

    The table has 1.09 at level 10, from a DEFENDING screen. Attacking reads
    1.10: ten infantry contribute 40.00, hank's own attack is 5.00, and the
    server prints 49.00. Either the two sides genuinely differ -- which one
    hero already does, Tōgō-with-bombardment, at 1.2944 attacking and 1.30
    defending -- or one of the two readings is a rounding of the other.

    Both sides at every level, since a single point cannot tell a per-side
    curve from a single bad cell.
    """
    print(f"\n  {'lvl':>3} {'attacking':>10} {'M atk':>7} "
          f"{'defending':>10} {'M def':>7}   same?")
    for lvl in range(1, 11):
        vals = {}
        for side in ("attack", "defend"):
            ov = settings()
            if side == "attack":
                ov.update(duel(1, "inf", 10, "inf", 400))
                fields, row = HERO_ATK_FIELDS, "B.1.1"
            else:
                ov.update(duel(1, "inf", 400, "inf", 10))
                fields, row = HERO_FIELDS, "A.1.1"
            ov.update({fields[0]: "hank", fields[1]: str(lvl),
                       fields[2]: "100%"})
            try:
                p.submit(ov, create=fields)
            except (BareFormReturned, ValueError) as e:
                print(f"  {lvl:>3}  {side}: {e}"[:90])
                continue
            d = dict(p.last_details)
            c = d.get(row) or {}
            record("hank_sides", {"level": lvl, "side": side, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if c.get("lost") is None or (c.get("pct") or 0) >= 99.9:
                continue
            vals[side] = c["lost"]
        a = vals.get("attack")
        dfd = vals.get("defend")
        # attacking: own 5.0 sits behind infantry's 4.0? No -- 5.0 > 4.0, so the
        # hero saturates first and the ten units take E(11) - E(1) = 10.
        m_a = (a - 5.0) / (4.0 * effective_units(10)) if a is not None else None
        # defending: hank defends at 6.0, above infantry's 5.0, so first again.
        m_d = (dfd - 6.0) / (5.0 * effective_units(10)) if dfd is not None else None
        same = (m_a is not None and m_d is not None
                and abs(m_a - m_d) < 0.002)
        print(f"  {lvl:>3} {a if a is None else f'{a:.2f}':>10} "
              f"{m_a if m_a is None else f'{m_a:.4f}':>7} "
              f"{dfd if dfd is None else f'{dfd:.2f}':>10} "
              f"{m_d if m_d is None else f'{m_d:.4f}':>7}   "
              + ("yes" if same else "DIFFER"))


def exp_land_hero_target_class(p: Probe) -> None:
    """Do the LAND heroes have target-class columns, as Richthofen does?

    Every land-hero reading in this project fired at INFANTRY. Richthofen turned
    out to add 70.00 against aircraft and 16.66 against infantry -- a factor of
    four from the same hero at the same level -- so "a hero has one own-attack
    value per side" is an assumption that has already failed once.

    Light artillery is the control stack because no hero buffs it, so the
    excess is the hero's own contribution and nothing else. Three targets, one
    per class: infantry on land, fighters in the air, a battleship at sea. Land
    attacking either of the other two is not attenuated, so all three cells are
    read raw.
    """
    targets = [("inf", 400, "land", "land"), ("int", 400, "air", "land"),
               ("bb", 100, "naval", "sea")]
    print(f"\n  {'hero':12} " + " ".join(f"{c:>10}" for _, _, c, _ in targets)
          + "   reading")
    out: dict[str, dict[str, float]] = {}
    for hero in sorted(HERO_ATK_ATTACKING):
        cells = []
        row: dict[str, float] = {}
        for tgt, tn, tcls, tterr in targets:
            coef = {"land": 5.0, "air": 1.0, "naval": 1.0}[tcls]
            ov = settings()
            ov.update(duel(1, "lart", 10, tgt, tn,
                           atk_terrain="land", def_terrain=tterr))
            ov.update({HERO_ATK_FIELDS[0]: hero, HERO_ATK_FIELDS[1]: "10",
                       HERO_ATK_FIELDS[2]: "100%"})
            try:
                p.submit(ov, create=HERO_ATK_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"    ! {hero} vs {tgt}: {e}"[:100], file=sys.stderr)
                cells.append(f"{'—':>10}")
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("land_hero_target_class",
                   {"hero": hero, "target": tgt, "target_class": tcls,
                    "level": 10, "atk_n": 10, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                cells.append(f"{'wiped':>10}")
                continue
            excess = b["lost"] - coef * (effective_units(11) - 1)
            row[tcls] = excess
            cells.append(f"{excess:10.2f}")
        out[hero] = row
        vals = list(row.values())
        flat = (max(vals) - min(vals) < 0.05) if len(vals) == 3 else False
        print(f"  {hero:12} " + " ".join(cells)
              + ("   flat" if flat else "   COLUMNS DIFFER"))
    print("\n  own attack by target class = " + json.dumps(
        {h: {c: round(v, 2) for c, v in r.items()} for h, r in out.items()},
        sort_keys=True))


def exp_land_hero_def_class(p: Probe) -> None:
    """And the defending side: does a hero's defence depend on the ATTACKER's class?

    All sixteen land heroes have target-class columns attacking -- Lawrence
    reads 45.0 against land, 4.5 against air and 11.25 against naval, a factor
    of ten. Nothing says the defending column is a single number either, and
    the app would be wrong for every defending hero facing anything but a land
    stack if it is not.

    Same control on the other side: a light-artillery stack the hero does not
    buff, so the attacker's losses are the hero's own defence contribution and
    nothing else.
    """
    attackers = [("inf", 400, "land", "land"), ("int", 200, "air", "air"),
                 ("bb", 100, "naval", "sea")]
    print(f"\n  {'hero':12} " + " ".join(f"{c:>10}" for _, _, c, _ in attackers)
          + "   reading")
    out: dict[str, dict[str, float]] = {}
    for hero in sorted(HERO_ATK_ATTACKING):
        cells = []
        row: dict[str, float] = {}
        for atk, an, acls, aterr in attackers:
            # lart defending against each class, from CLASS_DEFENCE.
            coef = {"land": 1.0, "air": 0.2, "naval": 0.2}[acls]
            ov = settings()
            ov.update(duel(1, atk, an, "lart", 10,
                           atk_terrain=aterr, def_terrain="land"))
            ov.update({HERO_FIELDS[0]: hero, HERO_FIELDS[1]: "10",
                       HERO_FIELDS[2]: "100%"})
            try:
                p.submit(ov, create=HERO_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"    ! {hero} vs {atk}: {e}"[:100], file=sys.stderr)
                cells.append(f"{'—':>10}")
                continue
            d = dict(p.last_details)
            a = d.get("A.1.1") or {}
            record("land_hero_def_class",
                   {"hero": hero, "attacker": atk, "atk_class": acls,
                    "level": 10, "def_n": 10, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if a.get("lost") is None or (a.get("pct") or 0) >= 99.9:
                cells.append(f"{'wiped':>10}")
                continue
            excess = a["lost"] - coef * (effective_units(11) - 1)
            row[acls] = excess
            cells.append(f"{excess:10.2f}")
        out[hero] = row
        vals = list(row.values())
        flat = (max(vals) - min(vals) < 0.05) if len(vals) == 3 else False
        print(f"  {hero:12} " + " ".join(cells)
              + ("   flat" if flat else "   COLUMNS DIFFER"))
    print("\n  own defence by attacker class = " + json.dumps(
        {h: {c: round(v, 2) for c, v in r.items()} for h, r in out.items()},
        sort_keys=True))


def exp_m_f_generality(p: Probe) -> None:
    """m(f) = 0.05 + 0.95f, swept on ONE unit type and ONE side. Does it hold?

    This is the most heavily used law in the model -- every output term in the
    engine carries an m(f) -- and the provenance note has always said what it
    rests on: "Only the ATTACKER's HP was swept, and only for infantry; that
    m(f) applies to a defender or to any other unit type is assumed."

    That is the exact shape of the four hero defects found this week: a
    dimension nobody varied, recorded as a dimension that does not exist. So
    both fixed axes move here. Five unit types spanning per-unit HP from 10 to
    260 and coefficients from 1.0 to 45.0, each swept on the ATTACKING side and
    on the DEFENDING side.

    The 0.05 floor is what makes the law falsifiable cheaply: at 10% HP a
    proportional law predicts 10% of full damage and this one predicts 14.5%.
    """
    types = [("lart", 5.0, 1.0), ("inf", 4.0, 5.0), ("st", 25.0, 6.3),
             ("ac", 6.0, 12.0), ("ht", 45.0, 45.0)]
    pcts = [100, 75, 50, 25, 10]
    print(f"\n  {'unit':5} {'side':7} " + " ".join(f"{p:>8}%" for p in pcts)
          + "   worst error vs m(f)")
    worst_all = 0.0
    for unit, atk_c, def_c in types:
        for side in ("attack", "defend"):
            cells = []
            worst = 0.0
            for pct in pcts:
                ov = settings()
                if side == "attack":
                    ov.update(duel(1, unit, 10, "inf", 400,
                                   atk_hp=f"{pct}%"))
                    row, coef = "B.1.1", atk_c
                else:
                    ov.update(duel(1, "inf", 400, unit, 10,
                                   def_hp=f"{pct}%"))
                    row, coef = "A.1.1", def_c
                try:
                    p.submit(ov)
                except (BareFormReturned, ValueError) as e:
                    print(f"    ! {unit} {side} {pct}%: {e}"[:100],
                          file=sys.stderr)
                    cells.append(f"{'—':>9}")
                    continue
                d = dict(p.last_details)
                c = d.get(row) or {}
                record("m_f_generality",
                       {"unit": unit, "side": side, "hp_pct": pct,
                        "detail": d},
                       {k: (v or {}).get("lost") for k, v in d.items()})
                if c.get("lost") is None or (c.get("pct") or 0) >= 99.9:
                    cells.append(f"{'wiped':>9}")
                    continue
                want = coef * effective_units(10) * (0.05 + 0.95 * pct / 100)
                err = abs(c["lost"] - want) / max(want, 1.0) * 100
                worst = max(worst, err)
                cells.append(f"{c['lost']:9.2f}")
            worst_all = max(worst_all, worst)
            print(f"  {unit:5} {side:7} " + " ".join(cells)
                  + f"   {worst:.3f}%"
                  + ("" if worst < 0.05 else "   <-- DOES NOT FIT"))
    print(f"\n  Worst error across every cell: {worst_all:.3f}%")
    if worst_all < 0.05:
        print("  m(f) = 0.05 + 0.95f holds for every unit type tested and on "
              "BOTH sides.\n  The two axes the note said were assumed are now "
              "measured.")


def exp_building_levels(p: Probe) -> None:
    """Building HP per level, and the two max levels nobody ever probed.

    Seven of the eight buildings have HP confirmed at exactly ONE level, and
    the app extrapolates from it. The workshop is worse than that: its table
    entry is 35 HP at level 3 with the comment that "5 + 10 + 20 = 35 is a
    plausible doubling series and is assumed, not measured". An assumed
    quantity sitting in a constants file is the thing this project exists to
    avoid.

    The factory and workshop also carry maxLevel: null, because the sweep asked
    for level 3, was not rejected, and never probed higher -- so "unknown" here
    means "nobody pressed the button", not "the server would not say". It
    states its caps outright when asked.

    One request per level, reading the building's own result row, which prints
    its pool directly.
    """
    abb, lvl, hp = "B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp"
    print(f"\n  {'building':12} {'lvl':>4} {'pool':>9}   note")
    found: dict[str, dict[int, float]] = {}
    caps: dict[str, int] = {}
    for bldg in ("workshop", "factory", "barracks", "railway", "aerodrome",
                 "harbor", "recruiting"):
        for level in range(1, 7):
            ov = settings()
            ov.update(duel(1, "inf", 30, "inf", 30))
            ov.update({abb: bldg, lvl: str(level), hp: "100%"})
            try:
                p.submit(ov, create=(abb, lvl, hp))
            except BareFormReturned as e:
                # The server states its own cap. That IS the reading.
                if e.oops:
                    caps.setdefault(bldg, level - 1)
                    print(f"  {bldg:12} {level:>4} {'refused':>9}   "
                          f"{' | '.join(e.oops[:1])}"[:104])
                    record("building_levels", {"building": bldg, "level": level,
                                               "refused": e.oops[:1]}, {})
                    break
                print(f"  {bldg:12} {level:>4} {'no rows':>9}")
                break
            except ValueError as e:
                print(f"  {bldg:12} {level:>4} {'error':>9}   {e}"[:104])
                break
            d = dict(p.last_details)
            row = d.get("B.1.bldg.1") or {}
            record("building_levels", {"building": bldg, "level": level,
                                       "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            pool = row.get("pool")
            if pool is None:
                print(f"  {bldg:12} {level:>4} {'—':>9}   no building row")
                continue
            found.setdefault(bldg, {})[level] = pool
            print(f"  {bldg:12} {level:>4} {pool:9.1f}")
    print("\n  pool by level = " + json.dumps(
        {b: {str(k): v for k, v in r.items()} for b, r in found.items()},
        sort_keys=True))
    print("  caps stated by the server = " + json.dumps(caps, sort_keys=True))
    for b, r in sorted(found.items()):
        if len(r) < 2:
            continue
        lv = sorted(r)
        per = [round(r[l] / l, 3) for l in lv]
        linear = max(per) - min(per) < 0.05
        print(f"  {b}: {'LINEAR at ' + str(per[0]) + ' per level' if linear else 'NOT linear — ' + str(per)}")


def exp_e_n_gaps(p: Probe) -> None:
    """Every untested rung of E(n), the other law that is in every output term.

    E(n) = n below 20 and 20 + k(60-k)/60 above it, k = min(n,50) - 20. The
    provenance note lists what has never been submitted: n in 21-28, 31-44,
    46-49 and above 113. The curve is smooth and every gap is bracketed, which
    is a fair reason to interpolate and not a reason to call it measured.

    The knee at 20 and the cap at 50 are where a wrong law would show, and
    both are inside the untested ranges. Light artillery is the probe because
    its coefficient is 5.0 and its per-unit HP is 10, so the defender's return
    fire cannot wipe it at any of these sizes.
    """
    untested = ([21, 22, 23, 24, 25, 26, 27, 28] + [31, 33, 36, 39, 41, 43, 44]
                + [46, 47, 48, 49] + [130, 200, 400])
    print(f"\n  {'n':>4} {'dealt':>10} {'E(n) implied':>13} {'E(n) predicted':>15}"
          f"   error")
    worst = 0.0
    for n in untested:
        ov = settings()
        ov.update(duel(1, "lart", n, "inf", 800))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {n:>4}  {e}"[:96])
            continue
        d = dict(p.last_details)
        b = d.get("B.1.1") or {}
        record("e_n_gaps", {"n": n, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
            print(f"  {n:>4} {'wiped/none':>10}")
            continue
        implied = b["lost"] / 5.0
        predicted = effective_units(n)
        err = abs(implied - predicted) / max(predicted, 1.0) * 100
        worst = max(worst, err)
        print(f"  {n:>4} {b['lost']:10.2f} {implied:13.4f} {predicted:15.4f}"
              f"   {err:.4f}%" + ("" if err < 0.05 else "   <-- MISFIT"))
    print(f"\n  Worst error across {len(untested)} previously untested rungs: "
          f"{worst:.4f}%")
    if worst < 0.05:
        print("  E(n) is measured across the knee at 20 and the cap at 50, not "
              "interpolated through them.")


def exp_patrol_pin(p: Probe) -> None:
    """Pin the patrol attrition coefficient, the last estimated number.

    PATROL.attrition has read 'estimated' since it was measured: nine cells
    gave 0.360-0.427 and the note says the residual does not track the loss
    fraction, so the delivery is probably discrete. That fit used the OLD
    survivor rule -- count minus floor(cumulative damage / max HP) -- which
    this week's rounds ladder overturned. Refitting the same nine cells with
    the corrected rule collapses the range to a worst error of 0.283% at
    c = 0.380, so the wide band was an artifact of the wrong survivor count and
    not evidence of discreteness.

    Two things still need buying. The coefficient is not pinned to the printed
    precision, and the sweep only ever used ten attackers -- and c has almost
    no leverage on a stack that barely gets hurt. And the strike-versus-patrol
    comparison shows the DEFENDER's output falls too, which no model in the app
    accounts for: 160.00 against a striking stack and 157.73 against a
    patrolling one, from the same defender.

    So: four attacker sizes against three defenders, each flown as a strike AND
    as a patrol, so every cell has its own unattenuated reference rather than
    borrowing one.
    """
    print(f"\n  {'unit':5} {'n':>3} {'target':6} {'mode':7} "
          f"{'A lost':>9} {'B lost':>9}")
    for unit in ("int", "tac"):
        for n in (5, 10, 20, 40):
            for tgt, tn in (("ac", 20), ("ht", 20), ("inf", 200)):
                for mode in ("air", "patrol"):
                    ov = settings()
                    ov.update(duel(1, unit, n, tgt, tn,
                                   atk_terrain=mode, def_terrain="land"))
                    try:
                        p.submit(ov)
                    except (BareFormReturned, ValueError) as e:
                        print(f"  {unit:5} {n:>3} {tgt:6} {mode:7}  {e}"[:92])
                        continue
                    d = dict(p.last_details)
                    a = d.get("A.1.1") or {}
                    b = d.get("B.1.1") or {}
                    record("patrol_pin",
                           {"unit": unit, "atk_n": n, "target": tgt,
                            "def_n": tn, "mode": mode, "detail": d},
                           {k: (v or {}).get("lost") for k, v in d.items()})
                    wiped = ((a.get("pct") or 0) >= 99.9
                             or (b.get("pct") or 0) >= 99.9)
                    print(f"  {unit:5} {n:>3} {tgt:6} {mode:7} "
                          f"{a.get('lost', 0) or 0:9.2f} "
                          f"{b.get('lost', 0) or 0:9.2f}"
                          + ("   WIPED — discarded" if wiped else ""))


def exp_building_damage_rest(p: Probe) -> None:
    """The eight units with no building-damage figure, and the censored ninth.

    BUILDING_DAMAGE_PER_EFFECTIVE_UNIT holds eight of the ten land types.
    Convoys, the Balloon and every air and naval unit have no entry at all --
    not a bracket, not a floor, nothing -- because the sweep that measured it
    only ever flew land attackers. The heavy tank has a FLOOR rather than a
    value: it dealt exactly 250.00 against a fortress holding 250.00, so the
    reading is censored and 8.82 is a lower bound.

    Both are fixed the same way: a small enough stack that the building
    survives. Five attackers against a level-5 fortress gives E(5) = 5, so any
    per-unit figure under 50 reads clean.
    """
    abb, lvl, hp = "B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp"
    cls_of = {u: c for c, us in UNIT_CLASSES.items() for u in us}
    print(f"\n  {'unit':8} {'class':6} {'n':>3} {'bldg lost':>10} "
          f"{'per eff. unit':>14}")
    out: dict[str, float] = {}
    for unit in ("convoy", "bal", "int", "tac", "zep", "sub", "cl", "bb", "ht"):
        acls = cls_of.get(unit, "land")
        terr = {"land": ("land", "land"), "air": ("air", "land"),
                "naval": ("sea", "land")}[acls]
        if unit == "bal":
            terr = ("land", "land")
        n = 5
        ov = settings()
        ov.update(duel(1, unit, n, "inf", 60,
                       atk_terrain=terr[0], def_terrain=terr[1]))
        ov.update({abb: "fortress", lvl: "5", hp: "100%"})
        try:
            p.submit(ov, create=(abb, lvl, hp))
        except (BareFormReturned, ValueError) as e:
            print(f"  {unit:8} {acls:6} {n:>3} {'refused':>10}   {e}"[:104])
            record("building_damage_rest", {"unit": unit, "refused": True}, {})
            continue
        d = dict(p.last_details)
        b = d.get("B.1.bldg.1") or {}
        record("building_damage_rest",
               {"unit": unit, "atk_n": n, "atk_class": acls,
                "terrain": list(terr), "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None:
            print(f"  {unit:8} {acls:6} {n:>3} {'no row':>10}   "
                  f"the building takes nothing from this attacker")
            out[unit] = 0.0
            continue
        if (b.get("pct") or 0) >= 99.9:
            print(f"  {unit:8} {acls:6} {n:>3} {b['lost']:10.2f}   "
                  f"CENSORED — building destroyed, this is a floor")
            continue
        per = b["lost"] / effective_units(n)
        out[unit] = per
        print(f"  {unit:8} {acls:6} {n:>3} {b['lost']:10.2f} {per:14.4f}")
    print("\n  building damage per effective unit = " + json.dumps(
        {k: round(v, 4) for k, v in out.items()}, sort_keys=True))


def exp_field_coverage(p: Probe) -> None:
    """Which of the server's own input fields has this project NEVER varied?

    Every audit so far has worked from something this project wrote down: the
    gap list, the provenance table, the engine's outputs. Each found real
    holes, and each could only find holes someone had thought to describe.

    The form is the one inventory nobody authored. It is the complete surface
    the server offers, discovered by load_form() rather than declared, so
    comparing it against every field this rig has ever sent answers "did you
    cover all the cases" in the only way that does not beg the question.
    """
    base = dict(p.baseline or {})
    if not base:
        print("  ! no form fields discovered.", file=sys.stderr)
        return
    print(f"\n  The form offers {len(base)} fields.\n")

    # Everything this rig has ever put in a payload, from the record.
    sent: set[str] = set()
    varied: dict[str, set[str]] = {}
    for line in open(RESULTS_PATH):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        blob = json.dumps(row.get("meta") or {})
        for f in re.findall(r'"([A-Za-z][A-Za-z0-9_.]*)"\s*:', blob):
            if f in base:
                sent.add(f)
    # The probe's own helpers name fields directly; scan the source too, since
    # a field set by settings() or duel() never appears in a meta blob.
    src = open(__file__).read()
    for f in base:
        if f"\"{f}\"" in src or f"'{f}'" in src:
            sent.add(f)
        # Fields built by templates: A.1.1.unit is written as f"{side}.{stack}..."
        tail = f.split(".")[-1]
        if re.search(r'\{[a-z_]+\}\.\{?[a-z_0-9]*\}?\.?' + re.escape(tail), src):
            sent.add(f)

    untouched = sorted(f for f in base if f not in sent)
    print(f"  {len(sent)} of {len(base)} have been set by this rig at least once.")
    if not untouched:
        print("  Every field the form offers has been exercised.")
    else:
        print(f"\n  NEVER SET ({len(untouched)}), with the value the form ships:\n")
        for f in untouched:
            opts = p.select_options.get(f)
            print(f"    {f:28} = {base[f]!r:20}"
                  + (f"  choices: {opts[:6]}" if opts else ""))
    record("field_coverage", {"total": len(base), "sent": len(sent),
                              "untouched": untouched}, {})


def exp_debark_and_long_rounds(p: Probe) -> None:
    """Two assumptions the field-coverage audit turned up.

    DEBARK. EMBARKED_TERRAIN lists sea AND debark, and the engine treats them
    identically -- flat 1.0 column, flat 10 HP, hit on the attacker's naval
    column. Only the HP half was ever measured in debark; the class change was
    measured in SEA and extended to debark because they sit in the same list.
    That is precisely the kind of extension this project keeps finding wrong,
    so the three discriminating attackers go again, in debark.

    LONG ROUNDS. The form accepts maxRounds up to 1000 and nothing above 10 has
    been submitted. Patrol scales with duration and the app says outright that
    scaling past 4 "assumes the proportionality holds indefinitely, which
    nobody has checked". Two rungs check it.
    """
    print("\n  1. debark: does the class change apply there too, or only at sea?\n")
    print(f"  {'attacker':8} {'land col':>9} {'naval col':>10} "
          f"{'sea':>8} {'debark':>8}   verdict")
    for atk, land_c, naval_c in (("cav", 15.0, 8.0), ("lart", 5.0, 1.0),
                                 ("ht", 45.0, 23.0)):
        reads = {}
        for terr in ("sea", "debark"):
            ov = settings()
            ov.update(duel(1, atk, 10, "inf", 200,
                           atk_terrain="land", def_terrain=terr))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                print(f"  {atk:8} {terr}: {e}"[:96])
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("debark_class", {"attacker": atk, "tgt_terrain": terr,
                                    "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                continue
            reads[terr] = b["lost"] / effective_units(10)
        if len(reads) == 2:
            same = abs(reads["sea"] - reads["debark"]) < 0.05
            near = lambda v, x: abs(v - x) < 0.05 * max(x, 1.0)
            v = ("NAVAL column, same as sea" if same and near(reads["debark"], naval_c)
                 else "LAND column — debark is NOT sea" if near(reads["debark"], land_c)
                 else "neither")
            print(f"  {atk:8} {land_c:9.1f} {naval_c:10.1f} {reads['sea']:8.2f} "
                  f"{reads['debark']:8.2f}   {v}")

    print("\n  2. an embarked ATTACKER in debark, against all three classes\n")
    print(f"  {'target':8} {'terrain':8} {'per eff. unit':>14}   expected if debark == sea")
    for tgt, tterr, want in (("inf", "land", 1.0), ("int", "land", 0.5),
                             ("bb", "sea", 1.0)):
        ov = settings()
        ov.update(duel(1, "inf", 40, tgt, 200 if tgt != "bb" else 60,
                       atk_terrain="debark", def_terrain=tterr))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {tgt:8} {tterr:8} {'refused':>14}   {e}"[:100])
            continue
        d = dict(p.last_details)
        b = d.get("B.1.1") or {}
        record("debark_class", {"probe": "attacker", "target": tgt,
                                "tgt_terrain": tterr, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
            print(f"  {tgt:8} {tterr:8} {'wiped/none':>14}")
            continue
        per = b["lost"] / effective_units(40)
        print(f"  {tgt:8} {tterr:8} {per:14.4f}   {want}"
              + ("" if abs(per - want) < 0.03 else "   <-- DIFFERS"))

    print("\n  3. maxRounds far past anything submitted before\n")
    print(f"  {'mode':8} {'rounds':>7} {'B lost':>10}   per round")
    for mode in ("air", "patrol"):
        for rounds in (1, 4, 20, 100):
            ov = settings(rounds=rounds)
            ov.update(duel(1, "tac", 10, "inf", 4000,
                           atk_terrain=mode, def_terrain="land"))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                print(f"  {mode:8} {rounds:>7} {'refused':>10}   {e}"[:96])
                continue
            d = dict(p.last_details)
            b = d.get("B.1.1") or {}
            record("long_rounds", {"mode": mode, "rounds": rounds,
                                   "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            if b.get("lost") is None:
                print(f"  {mode:8} {rounds:>7} {'—':>10}")
                continue
            wiped = (b.get("pct") or 0) >= 99.9
            print(f"  {mode:8} {rounds:>7} {b['lost']:10.2f}   "
                  f"{b['lost'] / rounds:8.3f}" + ("   WIPED" if wiped else ""))

# Every (hero, unit) pair with a measured OUTPUT buff, and the level cap to
# sweep to. Read with a SINGLE-TYPE stack, which needs no baseline subtraction
# and cannot be contaminated by another curve.
HERO_OUTPUT_PAIRS: list[tuple[str, str]] = [
    ("joffre_home", "inf"), ("joffre_home", "ac"), ("alvin", "st"),
    ("kangal", "ac"), ("hank", "inf"),
]


def exp_hero_output_curves(p: Probe) -> None:
    """Re-read every output curve cleanly, one unit type at a time.

    WHY NOT THE NINE-TYPE STACK. That screen exists to FIND which types a hero
    buffs. Measuring a curve through it means subtracting a baseline and every
    other buff the hero has, and joffre_home has two -- so its armoured-car
    figure was computed by subtracting an INTERPOLATED infantry value at the
    levels where infantry had never been read. One of them came out 1.1479,
    which is not a number the site would produce; it is an artifact of the
    subtraction.

    A stack of one type has no such problem:

        output = A + coefficient x E(count) x m(f) x M

    with everything but M known, so M falls out of one request. It also dodges
    the server's float refusal, because the stack is small enough to send at
    99% and the m(f) term is carried explicitly rather than assumed away.
    """
    hp_pct = 99          # 100% of a buffed max trips the server's own check
    m_f = 0.05 + 0.95 * (hp_pct / 100)
    print(f"\n  Single-type stacks at {hp_pct}% HP, so m(f) = {m_f:.4f}.\n")
    for hero, unit in HERO_OUTPUT_PAIRS:
        cap = HERO_MAX_LEVEL.get(hero, 20)
        a_def = MEASURED_HEROES[hero][0]
        curve: dict[int, float] = {}
        for lvl in range(1, cap + 1):
            ov = settings()
            ov.update(duel(1, "inf", SURVIVOR_N, unit, 2,
                           def_hp=f"{hp_pct}%"))
            ov.update(composite(1, "B", [(unit, 2)], hp=f"{hp_pct}%"))
            ov.update({HERO_FIELDS[0]: hero, HERO_FIELDS[1]: str(lvl),
                       HERO_FIELDS[2]: "100%"})
            try:
                p.submit(ov, create=composite_fields("B", 1, 1) + HERO_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"  ! {hero} {unit} L{lvl}: {e}", file=sys.stderr)
                record("hero_output_curves", {"hero": hero, "unit": unit,
                                              "level": lvl,
                                              "error": str(e)}, {})
                continue
            d = dict(p.last_details)
            record("hero_output_curves", {"hero": hero, "unit": unit,
                                          "level": lvl, "hp_pct": hp_pct,
                                          "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            a = d.get("A.1.1") or {}
            if a.get("lost") is None or (a.get("pct") or 0) >= 99.9:
                continue
            m = (a["lost"] - a_def) / (DEF_COEF[unit] * effective_units(2) * m_f)
            curve[lvl] = m
        if not curve:
            print(f"  {hero:13} {unit:5} nothing read")
            continue
        print(f"  {hero:13} {unit:5} "
              + ", ".join(f"{l}:{curve[l]:.3f}" for l in sorted(curve)))
        rounded = {l: round(v, 2) for l, v in curve.items()}
        drift = max(abs(curve[l] - rounded[l]) for l in curve)
        print(f"  {'':13} {'':5} rounds to 2dp within {drift:.4f}"
              + ("" if drift < 0.005 else "  <-- NOT clean 2dp, quote as read"))


def exp_hero_other_terrain(p: Probe) -> None:
    """Decompose the six heroes that only work on air and naval stacks.

    hero_sides showed all six work and all six change the battle, but read
    each once -- which confounds the hero's own attack with any multiplier,
    exactly as the first attacking sweep did. The fix is the same: two stack
    configurations, one containing the types the hero might buff and one not.

    Since nobody knows what an air or naval hero buffs, "plain" here is a
    SINGLE unit type and "buffed" is a different one. If the excess is the same
    in both, it is the hero's own attack and there is no multiplier to find. If
    it differs, the difference names the type.
    """
    setups = {
        "air": {"terrain": "air", "def_unit": "inf", "def_n": 40,
                "probe": ["tac", "int", "zep"]},
        "sea": {"terrain": "sea", "def_unit": "bb", "def_n": 30,
                "probe": ["cl", "sub", "bb"]},
    }
    for terr, cfg in setups.items():
        who = [h for h, t in HERO_OTHER_TERRAIN.items() if t == terr]
        print(f"\n  {terr.upper()} — one row per hero, three attacker types "
              f"each\n")
        print(f"  {'hero':10} " + " ".join(f"{u:>10}" for u in cfg["probe"])
              + "   reading")
        base: dict[str, float] = {}
        for hero in [None] + who:
            cells = []
            for unit in cfg["probe"]:
                ov = settings()
                ov.update(duel(1, unit, 10, cfg["def_unit"], cfg["def_n"],
                               atk_terrain=cfg["terrain"],
                               def_terrain="land" if terr == "air" else "sea"))
                create: tuple[str, ...] = ()
                if hero:
                    ov.update({HERO_ATK_FIELDS[0]: hero,
                               HERO_ATK_FIELDS[1]: "10",
                               HERO_ATK_FIELDS[2]: "100%"})
                    create = HERO_ATK_FIELDS
                try:
                    p.submit(ov, create=create)
                except (BareFormReturned, ValueError) as e:
                    record("hero_other_terrain", {"hero": hero, "unit": unit,
                                                  "terrain": terr,
                                                  "error": str(e)}, {})
                    cells.append(None)
                    continue
                d = dict(p.last_details)
                record("hero_other_terrain", {"hero": hero, "unit": unit,
                                              "terrain": terr, "level": 10,
                                              "detail": d},
                       {k: (v or {}).get("lost") for k, v in d.items()})
                b = d.get("B.1.1") or {}
                cells.append(None if (b.get("lost") is None
                                      or (b.get("pct") or 0) >= 99.9)
                             else b["lost"])
            if hero is None:
                for u, c in zip(cfg["probe"], cells):
                    if c is not None:
                        base[u] = c
                print(f"  {'(none)':10} "
                      + " ".join(f"{c:10.2f}" if c is not None else f"{'—':>10}"
                                 for c in cells) + "   baseline")
                continue
            ex = [None if (c is None or u not in base) else c - base[u]
                  for u, c in zip(cfg["probe"], cells)]
            good = [e for e in ex if e is not None]
            same = (len(good) > 1
                    and max(good) - min(good) <= 0.2)
            print(f"  {hero:10} "
                  + " ".join(f"{e:10.2f}" if e is not None else f"{'—':>10}"
                             for e in ex)
                  + ("   flat: own attack " + f"{good[0]:.2f}, no multiplier"
                     if same else
                     "   VARIES by attacker type — there is a multiplier"
                     if good else "   nothing read"))


def exp_cross_class(p: Probe) -> None:
    """Every class pairing nobody has submitted: five declared gaps at once.

    unit_stats measured each class against ITSELF, and air_vs_ground measured
    air attacking land. That leaves the naval off-diagonal, the air
    off-diagonal, ground ATTACKING air, air DEFENDING against ground, and
    every sea-vs-land or sea-vs-air cell -- all of them extrapolation in the
    app, and all of them one request per cell.

    Each battle yields TWO cells, because one submission contains both roles.
    """
    naval = [u for u in roster(p, "naval") if u != "bal"]
    air = [u for u in roster(p, "air") if u != "bal"]
    land = ["inf", "art", "ht"]
    sweeps = [
        ("naval_matrix", naval, naval, "sea", "sea"),
        ("air_matrix", air, air, "air", "air"),
        ("land_attacks_air", land, air, "land", "air"),
        ("air_defends_land", air, land, "air", "land"),
        ("sea_vs_land", naval[:2], land, "sea", "land"),
        ("land_vs_sea", land[:2], naval, "land", "sea"),
    ]
    for tag, atks, tgts, at, dt in sweeps:
        if not atks or not tgts:
            print(f"\n  {tag}: empty roster, skipped")
            continue
        print(f"\n  === {tag}: {at} attacks {dt} ===")
        exp_matchups(p, atks, tgts, tag, atk_terrain=at, def_terrain=dt)


def exp_edges(p: Probe) -> None:
    """The small remaining edges, each one or two requests.

    Every one of these is a named gap in the app that costs almost nothing to
    close, and has stayed open only because none of them was ever the most
    interesting thing to spend a request on.
    """
    print("\n  1. E(n) at the sampled gaps: 21-28, 31-44, 46-49\n")
    print(f"  {'n':>4} {'defender lost':>14} {'E(n) implied':>13} "
          f"{'E(n) predicted':>15}")
    for n in (21, 23, 26, 28, 31, 35, 38, 42, 44, 46, 48, 49, 120, 200):
        ov = settings()
        ov.update(duel(1, "inf", n, "ht", 60))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {n:>4} refused: {str(e)[:50]}")
            continue
        d = dict(p.last_details)
        record("edges", {"probe": "E_n", "n": n, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = (d.get("B.1.1") or {}).get("lost")
        if b is None:
            continue
        implied = b / MEASURED_UNITS["inf"][1]
        print(f"  {n:>4} {b:14.2f} {implied:13.4f} "
              f"{effective_units(n):15.4f}"
              + ("" if abs(implied - effective_units(n)) < 0.01 else "  <-- OFF"))

    print("\n  2. m(f) on a DEFENDER, and on a unit that is not infantry\n")
    print(f"  {'unit':5} {'side':9} {'hp%':>5} {'output':>9} {'x m(f)':>9} "
          f"{'predicted':>10}")
    for unit in ("inf", "ht"):
        for hp in (100, 75, 50, 25):
            ov = settings()
            ov.update(duel(1, "inf", 60, unit, 10, def_hp=f"{hp}%"))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                print(f"  ! {unit} def {hp}%: {e}", file=sys.stderr)
                continue
            d = dict(p.last_details)
            record("edges", {"probe": "m_f_defender", "unit": unit,
                             "hp_pct": hp, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            a = (d.get("A.1.1") or {}).get("lost")
            if a is None:
                continue
            want = (MEASURED_UNITS[unit][2] * effective_units(10)
                    * (0.05 + 0.95 * hp / 100))
            print(f"  {unit:5} {'defending':9} {hp:>5} {a:9.2f} "
                  f"{0.05 + 0.95 * hp / 100:9.4f} {want:10.2f}"
                  + ("" if abs(a - want) < 0.05 else "  <-- OFF"))

    print("\n  3. the trench pool multiplier at level 10, on a bigger stack\n")
    for n in (10, 50):
        ov = settings()
        ov.update(duel(1, "inf", 10, "inf", n))
        ov["B.1.trench"] = "10"
        try:
            p.submit(ov, create=("B.1.trench",))
        except (BareFormReturned, ValueError) as e:
            print(f"  ! trench pool n={n}: {e}", file=sys.stderr)
            continue
        d = dict(p.last_details)
        record("edges", {"probe": "trench_pool", "def_n": n, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.1") or {}
        if not b.get("pool"):
            continue
        lo, hi = hp_bounds(b, 1)
        base = n * MEASURED_UNITS["inf"][0]
        print(f"  n={n:<3} pool {b['pool']:9.1f}  multiplier bracket "
              f"[{lo / base:.4f}, {hi / base:.4f}]")

    print("\n  4. trench multipliers for a unit that is not infantry\n")
    for unit in ("ht", "art"):
        for lvl in (0, 10):
            ov = settings()
            ov.update(duel(1, "inf", 20, unit, 10))
            ov["B.1.trench"] = str(lvl)
            try:
                p.submit(ov, create=("B.1.trench",))
            except (BareFormReturned, ValueError) as e:
                print(f"  ! trench {unit} {lvl}: {e}", file=sys.stderr)
                continue
            d = dict(p.last_details)
            record("edges", {"probe": "trench_unit", "unit": unit,
                             "level": lvl, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            a = (d.get("A.1.1") or {}).get("lost")
            b = d.get("B.1.1") or {}
            print(f"  {unit:4} trench {lvl:>2}: attacker lost "
                  + (f"{a:8.2f}" if a is not None else f"{'—':>8}")
                  + f"  defender pool {b.get('pool', 0):9.1f}")

    print("\n  5. workshop and factory level caps\n")
    for bld in ("workshop", "factory"):
        ov = settings()
        ov.update(duel(1, "inf", 30, "inf", 10))
        ov.update({"B.1.bldg.1.abb": bld, "B.1.bldg.1.lvl": "20",
                   "B.1.bldg.1.hp": "100%"})
        try:
            p.submit(ov, create=("B.1.bldg.1.abb", "B.1.bldg.1.lvl",
                                 "B.1.bldg.1.hp"))
            print(f"  {bld:9} accepted level 20")
            record("edges", {"probe": "bldg_cap", "bldg": bld, "cap": 20}, {})
        except BareFormReturned as e:
            m = MAX_LEVEL_RE.search(str(e))
            cap = m.group(2) if m else "?"
            print(f"  {bld:9} max level {cap}")
            record("edges", {"probe": "bldg_cap", "bldg": bld, "cap": cap}, {})

    print("\n  6. can a LAND stack engage an AIR stack at all?\n")
    # Every land-attacks-air cell came back with no result rows and no `oops`,
    # which is the aborted-batch signature. That could mean "the game has no
    # such battle" or merely "this terrain pair is invalid" -- and those are
    # very different things to tell a user. Vary the terrain pair to separate
    # them.
    for at, dt, label in (("land", "air", "land attacker, air defender"),
                          ("land", "land", "both in land terrain"),
                          ("air", "air", "both in air terrain"),
                          ("air", "land", "air attacker, land defender")):
        ov = settings()
        ov.update(duel(1, "inf", 10, "int", 20, atk_terrain=at,
                       def_terrain=dt))
        try:
            p.submit(ov)
            d = dict(p.last_details)
            record("edges", {"probe": "land_vs_air", "atk_terrain": at,
                             "def_terrain": dt, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = (d.get("B.1.1") or {}).get("lost")
            print(f"  {label:30} " + (f"defender lost {b:.2f}"
                                      if b is not None else "no rows"))
        except (BareFormReturned, ValueError) as e:
            record("edges", {"probe": "land_vs_air", "atk_terrain": at,
                             "def_terrain": dt, "error": str(e)}, {})
            print(f"  {label:30} {str(e)[:64]}")

    print("\n  7. the balloon, one more time, in every terrain\n")
    for terr in ("air", "land", "sea"):
        ov = settings()
        ov.update(duel(1, "bal", 10, "inf", 20, atk_terrain=terr,
                       def_terrain="land"))
        try:
            p.submit(ov)
            d = dict(p.last_details)
            record("edges", {"probe": "balloon", "terrain": terr,
                             "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = (d.get("B.1.1") or {}).get("lost")
            print(f"  bal in {terr:5}: defender lost "
                  + (f"{b:.2f}" if b is not None else "no rows"))
        except (BareFormReturned, ValueError) as e:
            record("edges", {"probe": "balloon", "terrain": terr,
                             "error": str(e)}, {})
            print(f"  bal in {terr:5}: {str(e)[:70]}")


def exp_balloon_and_trench(p: Probe) -> None:
    """The balloon, and whether trenches do anything for a non-infantry stack.

    THE BALLOON has been "not one quantity measured" for the whole project,
    because every attempt sent it in AIR terrain, where the batch aborts. It
    works perfectly well in LAND terrain. Four requests give its attack, its
    defence and its max HP.

    TRENCHES: an artillery stack reads the identical output and the identical
    pool at trench 0 and trench 10 -- no bonus at all. The heavy-tank reading
    that would confirm it was CENSORED (the attacker was wiped), so it is
    repeated here with an attacker that survives.
    """
    print("\n  1. the balloon, in land terrain where it actually runs\n")
    print(f"  {'battle':28} {'A lost':>9} {'B lost':>9} {'B pool':>10}")
    for label, a, an, b, bn in (("10 bal attack 20 inf", "bal", 10, "inf", 20),
                                ("20 inf attack 10 bal", "inf", 20, "bal", 10),
                                ("10 bal attack 10 bal", "bal", 10, "bal", 10),
                                ("10 bal attack 20 ht", "bal", 10, "ht", 20)):
        ov = settings()
        ov.update(duel(1, a, an, b, bn, atk_terrain="land",
                       def_terrain="land"))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {label:28} {str(e)[:50]}")
            record("balloon", {"label": label, "error": str(e)}, {})
            continue
        d = dict(p.last_details)
        record("balloon", {"label": label, "atk": [a, an], "def": [b, bn],
                           "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        av = (d.get("A.1.1") or {}).get("lost")
        bv = d.get("B.1.1") or {}
        print(f"  {label:28} "
              + (f"{av:9.2f}" if av is not None else f"{'—':>9}")
              + (f" {bv['lost']:9.2f}" if bv.get("lost") is not None else f" {'—':>9}")
              + (f" {bv['pool']:10.1f}" if bv.get("pool") else f" {'—':>10}"))

    print("\n  2. trenches on a non-infantry stack, with an attacker that "
          "lives\n")
    print(f"  {'unit':5} {'trench':>7} {'attacker lost':>14} "
          f"{'defender pool':>14}")
    for unit in ("ht", "art", "cav", "inf"):
        for lvl in (0, 10):
            ov = settings()
            ov.update(duel(1, "inf", 200, unit, 10))
            ov["B.1.trench"] = str(lvl)
            try:
                p.submit(ov, create=("B.1.trench",))
            except (BareFormReturned, ValueError) as e:
                print(f"  ! {unit} trench {lvl}: {e}", file=sys.stderr)
                continue
            d = dict(p.last_details)
            record("trench_generality", {"unit": unit, "level": lvl,
                                         "atk_n": 200, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            a = d.get("A.1.1") or {}
            b = d.get("B.1.1") or {}
            flag = "" if (a.get("pct") or 0) < 99.9 else "  <-- ATTACKER WIPED"
            print(f"  {unit:5} {lvl:>7} "
                  + (f"{a.get('lost', 0):14.2f}" if a.get("lost") is not None
                     else f"{'—':>14}")
                  + f" {b.get('pool', 0):14.1f}{flag}")

    print("\n  3. workshop and factory caps, with the server's own words\n")
    for bld in ("workshop", "factory", "barracks"):
        ov = settings()
        ov.update(duel(1, "inf", 30, "inf", 10))
        ov.update({"B.1.bldg.1.abb": bld, "B.1.bldg.1.lvl": "20",
                   "B.1.bldg.1.hp": "100%"})
        try:
            p.submit(ov, create=("B.1.bldg.1.abb", "B.1.bldg.1.lvl",
                                 "B.1.bldg.1.hp"))
            print(f"  {bld:10} accepted level 20")
        except BareFormReturned as e:
            print(f"  {bld:10} {str(e)[:90]}")
            record("balloon", {"probe": "bldg_cap", "bldg": bld,
                               "error": str(e)}, {})


# Which terrain pair actually runs, per (attacker class, target class). Found
# the hard way: a land attacker against an AIR-terrain defender aborts the
# batch with no error at all, which is why "ground attacking air" was recorded
# as never submitted when it had only been submitted wrongly. In LAND terrain
# the same battle runs.
TERRAIN_PAIR = {
    ("land", "land"): ("land", "land"), ("land", "air"): ("land", "land"),
    ("land", "naval"): ("land", "sea"),
    ("air", "land"): ("air", "land"), ("air", "air"): ("air", "air"),
    ("air", "naval"): ("air", "sea"),
    ("naval", "land"): ("sea", "land"), ("naval", "air"): ("sea", "air"),
    ("naval", "naval"): ("sea", "sea"),
}
CLASS_REP = {"land": ("inf", 60), "air": ("int", 40), "naval": ("bb", 30)}


def exp_class_matrix(p: Probe) -> None:
    """Every unit against every target CLASS: the whole coefficient table.

    The cross-class sweep established the SHAPE -- a unit's coefficient is flat
    across targets within a class and changes between classes -- so the table
    is 17 units x 3 classes rather than 17 x 17. This fills it.

    Air attacking land is ATTENUATED (the post-fire law), so those cells are
    corrected for the attacker's own losses before being quoted; every other
    pairing is read raw.
    """
    cls_of = {u: c for c, us in UNIT_CLASSES.items() for u in us}
    print(f"\n  {'unit':8} {'class':6} " + " ".join(f"{c:>10}" for c in
                                                    ("land", "air", "naval")))
    table: dict[str, dict[str, float]] = {}
    for unit in ROSTER_ORDER:
        acls = cls_of.get(unit)
        if not acls:
            continue
        row: dict[str, float] = {}
        for tcls, (tgt, tn) in CLASS_REP.items():
            at, dt = TERRAIN_PAIR[(acls, tcls)]
            n = 10
            ov = settings()
            ov.update(duel(1, unit, n, tgt, tn, atk_terrain=at, def_terrain=dt))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                record("class_matrix", {"unit": unit, "target_class": tcls,
                                        "error": str(e)}, {})
                continue
            d = dict(p.last_details)
            record("class_matrix", {"unit": unit, "atk_n": n,
                                    "target": tgt, "target_class": tcls,
                                    "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = d.get("B.1.1") or {}
            a = d.get("A.1.1") or {}
            if b.get("lost") is None or (b.get("pct") or 0) >= 99.9:
                continue
            raw = b["lost"] / effective_units(n)
            # Air attacking land is evaluated on the survivors of the round's
            # own incoming fire, so the raw figure understates the stat.
            if acls == "air" and tcls == "land" and a.get("pool"):
                lost_frac = (a.get("lost") or 0) / a["pool"]
                if lost_frac < 0.999:
                    raw /= (1 - lost_frac)
            row[tcls] = raw
        if row:
            table[unit] = row
            print(f"  {unit:8} {acls:6} "
                  + " ".join(f"{row[c]:10.2f}" if c in row else f"{'—':>10}"
                             for c in ("land", "air", "naval")))
    print(f"\n  {len(table)} of {len(ROSTER_ORDER)} units have at least one "
          f"cell. A dash is a pairing the server\n  will not run, not a "
          f"reading that failed — every refusal is recorded with its message.")


def exp_last_edges(p: Probe) -> None:
    """The remaining named gaps, each one or two requests.

    air_E_above_20   every attenuated air stack ever measured was 10 units,
                     where E(n) = n, so E(survivors) and a per-unit sum of
                     m(f) are indistinguishable. They diverge above 20.
    air_wiped        the post-fire law divides by the survivor count and has
                     no measured branch at zero survivors.
    attenuation      whether post-fire evaluation applies to sea, and to air
                     DEFENDING rather than attacking.
    death rule       the printed death count in a multi-round battle does not
                     follow floor(cumulative loss / per-unit HP). Varying the
                     per-unit HP over-determines it.
    """
    print("\n  1. an attenuated air stack ABOVE 20 units\n")
    print(f"  {'n':>4} {'atk lost':>9} {'def lost':>9} {'E(surv)':>9} "
          f"{'post-fire':>10} {'per-unit sum':>13}")
    for n in (10, 25, 40, 50):
        ov = settings()
        ov.update(duel(1, "tac", n, "inf", 57, atk_terrain="air",
                       def_terrain="land"))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {n:>4} {str(e)[:56]}")
            continue
        d = dict(p.last_details)
        record("last_edges", {"probe": "air_E_above_20", "n": n, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = d.get("A.1.1") or {}
        b = d.get("B.1.1") or {}
        if a.get("lost") is None or b.get("lost") is None:
            continue
        alive = n - int(a.get("died", 0))
        f_after = ((a["pool"] - a["lost"]) / (alive * MEASURED_UNITS["tac"][0])
                   if alive else 0)
        post = 30.0 * effective_units(alive) * (0.05 + 0.95 * min(1, f_after))
        # The rival: every surviving unit contributes m(its own fraction),
        # which equals the post-fire law only while E(n) = n.
        per_unit = 30.0 * min(alive, effective_units(n)) * (0.05 + 0.95 * min(1, f_after))
        print(f"  {n:>4} {a['lost']:9.2f} {b['lost']:9.2f} "
              f"{effective_units(alive):9.3f} {post:10.2f} {per_unit:13.2f}")

    print("\n  2. an air attacker wiped to ZERO survivors\n")
    ov = settings()
    ov.update(duel(1, "tac", 3, "inf", 113, atk_terrain="air",
                   def_terrain="land"))
    try:
        p.submit(ov)
        d = dict(p.last_details)
        record("last_edges", {"probe": "air_wiped", "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = d.get("A.1.1") or {}
        b = d.get("B.1.1") or {}
        print(f"  3 tac vs 113 inf: attacker lost {a.get('lost')} of "
              f"{a.get('pool')} ({a.get('pct')}%), defender lost "
              f"{b.get('lost')}")
        if (a.get("pct") or 0) >= 99.9 and b.get("lost") is not None:
            print(f"  A WIPED air stack still deals {b['lost']:.2f}. The "
                  f"post-fire law divides by the survivor\n  count, so at zero "
                  f"survivors it is undefined — but the server answers anyway, "
                  f"and\n  this is what it answers.")
    except (BareFormReturned, ValueError) as e:
        print(f"  refused: {str(e)[:70]}")

    print("\n  3. is post-fire evaluation air-only?\n")
    print(f"  {'pairing':22} {'atk lost':>9} {'def lost':>9} {'raw stat':>9} "
          f"{'corrected':>10}")
    for label, a_u, a_n, a_t, d_u, d_n, d_t in (
            ("sea attacks sea", "bb", 10, "sea", "cl", 30, "sea"),
            ("air attacks air", "tac", 10, "air", "int", 30, "air"),
            ("land attacks land", "inf", 10, "land", "ht", 30, "land")):
        ov = settings()
        ov.update(duel(1, a_u, a_n, d_u, d_n, atk_terrain=a_t,
                       def_terrain=d_t))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {label:22} {str(e)[:50]}")
            continue
        d = dict(p.last_details)
        record("last_edges", {"probe": "attenuation_scope", "label": label,
                              "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = d.get("A.1.1") or {}
        b = d.get("B.1.1") or {}
        if b.get("lost") is None or not a.get("pool"):
            continue
        raw = b["lost"] / effective_units(a_n)
        frac = (a.get("lost") or 0) / a["pool"]
        corr = raw / (1 - frac) if frac < 0.999 else float("nan")
        print(f"  {label:22} {a.get('lost', 0):9.2f} {b['lost']:9.2f} "
              f"{raw:9.2f} {corr:10.2f}")

    print("\n  4. the multi-round death rule, with the per-unit HP varied\n")
    print(f"  {'unit':5} {'HP/unit':>8} {'rounds':>7} {'lost':>9} "
          f"{'died':>5} {'floor(lost/hp)':>15}")
    for unit in ("inf", "cav", "ht"):
        for rounds in (1, 2, 3, 4):
            ov = settings(rounds=rounds)
            ov.update(duel(1, unit, 50, unit, 50))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                print(f"  ! {unit} r{rounds}: {e}", file=sys.stderr)
                continue
            d = dict(p.last_details)
            record("last_edges", {"probe": "death_rule", "unit": unit,
                                  "rounds": rounds, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            a = d.get("A.1.1") or {}
            if a.get("lost") is None:
                continue
            hp = MEASURED_UNITS[unit][0]
            print(f"  {unit:5} {hp:8.1f} {rounds:>7} {a['lost']:9.2f} "
                  f"{a.get('died', 0):5.0f} {int(a['lost'] // hp):15}")


def exp_close_out(p: Probe) -> None:
    """The small remaining gaps, each one deliberately re-tried, not assumed.

    naval_vs_air is first and is the reason for the whole experiment: it is
    recorded as "the server will not run it", which is exactly what
    ground-attacks-air said before someone tried a different TERRAIN PAIR and
    it ran perfectly. A refusal under one configuration is not a property of
    the game.
    """
    print("\n  1. naval vs air, under every terrain pair the form allows\n")
    for at, dt in (("sea", "air"), ("sea", "sea"), ("air", "air"),
                   ("land", "land"), ("sea", "land"), ("air", "sea")):
        ov = settings()
        ov.update(duel(1, "bb", 10, "int", 30, atk_terrain=at, def_terrain=dt))
        try:
            p.submit(ov)
            d = dict(p.last_details)
            record("close_out", {"probe": "naval_vs_air", "atk_terrain": at,
                                 "def_terrain": dt, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = (d.get("B.1.1") or {}).get("lost")
            print(f"  bb({at}) vs int({dt}): "
                  + (f"defender lost {b:.2f}  <-- IT RUNS" if b is not None
                     else "no result rows"))
        except (BareFormReturned, ValueError) as e:
            record("close_out", {"probe": "naval_vs_air", "atk_terrain": at,
                                 "def_terrain": dt, "error": str(e)}, {})
            print(f"  bb({at}) vs int({dt}): {str(e)[:60]}")

    print("\n  2. an air attacker actually reduced to zero survivors\n")
    # Ground fire cannot wipe a healthy air stack -- 3 bombers against 113
    # infantry lose 5.83%. A DAMAGED one can be wiped, which reaches the same
    # branch of the post-fire law.
    for hp in ("100%", "10%", "5%", "2%"):
        ov = settings()
        ov.update(duel(1, "tac", 3, "inf", 113, atk_terrain="air",
                       def_terrain="land", atk_hp=hp))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  tac at {hp:5}: {str(e)[:60]}")
            continue
        d = dict(p.last_details)
        record("close_out", {"probe": "air_wiped", "atk_hp": hp, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = d.get("A.1.1") or {}
        b = d.get("B.1.1") or {}
        wiped = (a.get("pct") or 0) >= 99.9
        print(f"  tac at {hp:5}: attacker lost {a.get('lost')} of "
              f"{a.get('pool')} ({a.get('pct')}%), defender lost "
              f"{b.get('lost')}" + ("   <-- WIPED" if wiped else ""))

    print("\n  3. does a trench raise an ATTACKER's output?\n")
    for lvl in (0, 10, 20):
        ov = settings()
        ov.update(duel(1, "inf", 10, "inf", 60))
        ov["A.1.trench"] = str(lvl)
        try:
            p.submit(ov, create=("A.1.trench",))
        except (BareFormReturned, ValueError) as e:
            print(f"  attacker trench {lvl:>2}: {str(e)[:60]}")
            continue
        d = dict(p.last_details)
        record("close_out", {"probe": "trench_attacking", "level": lvl,
                             "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = d.get("A.1.1") or {}
        b = d.get("B.1.1") or {}
        print(f"  attacker trench {lvl:>2}: defender lost "
              f"{b.get('lost')}, attacker pool {a.get('pool')}")

    print("\n  4. the trench level-10 pool multiplier, on a 200-unit stack\n")
    for n in (50, 200):
        ov = settings()
        ov.update(duel(1, "inf", 10, "inf", n))
        ov["B.1.trench"] = "10"
        try:
            p.submit(ov, create=("B.1.trench",))
        except (BareFormReturned, ValueError) as e:
            print(f"  n={n}: {str(e)[:60]}")
            continue
        d = dict(p.last_details)
        record("close_out", {"probe": "trench_pool", "def_n": n, "detail": d},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.1") or {}
        if not b.get("pool"):
            continue
        lo, hi = hp_bounds(b, 1)
        base = n * MEASURED_UNITS["inf"][0]
        print(f"  n={n:<4} bracket [{lo / base:.5f}, {hi / base:.5f}]")

    print("\n  5. E(n) combined with m(f) above the knee\n")
    print(f"  {'n':>4} {'hp%':>5} {'output':>9} {'E(n)xm(f)':>10}")
    for n in (30, 50):
        for hp in (100, 50, 25):
            ov = settings()
            ov.update(duel(1, "inf", n, "ht", 60, atk_hp=f"{hp}%"))
            try:
                p.submit(ov)
            except (BareFormReturned, ValueError) as e:
                print(f"  ! n={n} hp={hp}: {e}", file=sys.stderr)
                continue
            d = dict(p.last_details)
            record("close_out", {"probe": "E_with_m", "n": n, "hp_pct": hp,
                                 "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = (d.get("B.1.1") or {}).get("lost")
            want = 4.0 * effective_units(n) * (0.05 + 0.95 * hp / 100)
            print(f"  {n:>4} {hp:>5} "
                  + (f"{b:9.2f}" if b is not None else f"{'—':>9}")
                  + f" {want:10.2f}"
                  + ("" if b is not None and abs(b - want) < 0.05 else "  <-- OFF"))

    print("\n  6. a fortress against air and naval attackers, and with a "
          "trench\n")
    for label, a_u, a_t, extra in (
            ("air attacker", "tac", "air", {}),
            ("naval attacker", "bb", "sea", {}),
            ("land attacker + trench 10", "inf", "land", {"B.1.trench": "10"})):
        for lvl in (0, 5):
            ov = settings()
            ov.update(duel(1, a_u, 20, "inf", 20, atk_terrain=a_t,
                           def_terrain="land"))
            fields = tuple(extra)
            ov.update(extra)
            if lvl:
                ov.update({"B.1.bldg.1.abb": "fortress",
                           "B.1.bldg.1.lvl": str(lvl),
                           "B.1.bldg.1.hp": "100%"})
                fields = fields + ("B.1.bldg.1.abb", "B.1.bldg.1.lvl",
                                   "B.1.bldg.1.hp")
            try:
                p.submit(ov, create=fields)
            except (BareFormReturned, ValueError) as e:
                print(f"  {label:26} fort {lvl}: {str(e)[:44]}")
                continue
            d = dict(p.last_details)
            record("close_out", {"probe": "fortress_scope", "label": label,
                                 "level": lvl, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = (d.get("B.1.1") or {}).get("lost")
            print(f"  {label:26} fort {lvl}: defender lost "
                  + (f"{b:.2f}" if b is not None else "—"))

    print("\n  7. terrain on AIR and NAVAL stacks\n")
    for unit, terr in (("int", "sea"), ("int", "debark"), ("bb", "debark"),
                       ("bb", "sea")):
        ov = settings()
        ov.update(duel(1, unit, 10, unit, 20, atk_terrain=terr,
                       def_terrain=terr))
        try:
            p.submit(ov)
            d = dict(p.last_details)
            record("close_out", {"probe": "terrain_others", "unit": unit,
                                 "terrain": terr, "detail": d},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            a = (d.get("A.1.1") or {}).get("lost")
            print(f"  {unit} in {terr:7}: attacker lost "
                  + (f"{a:.2f}" if a is not None else "—")
                  + f"   (flat 1.0 would give {effective_units(20):.2f})")
        except (BareFormReturned, ValueError) as e:
            record("close_out", {"probe": "terrain_others", "unit": unit,
                                 "terrain": terr, "error": str(e)}, {})
            print(f"  {unit} in {terr:7}: {str(e)[:56]}")


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


def exp_repair_cost(p: Probe) -> None:
    """The nine columns of the summary table that nobody ever read back.

    THE AUDIT THAT FOUND THIS. Four earlier audits each worked from an
    inventory this project wrote: the declared-gap list, the provenance table,
    the engine's own outputs, and the server's input form. The form was the
    first inventory the SERVER authored, and it found three live defects. Its
    mirror image had never been looked at: the server also authors an OUTPUT
    inventory -- every column it prints -- and StackSummaryScraper.COLUMNS
    deliberately slugifies unknown headers "so a column dxter adds later shows
    up as data instead of vanishing". It worked. Nine columns

        food | fish | iron | wood | coal | oil | gas | cash | hours

    have been accumulating in results.jsonl since the scraper was written --
    2,719 hours readings and 256 complete resource rows -- and not one line of
    code has ever read them back. The old module docstring listed "what 'hours'
    and the resource columns mean" as open, and the gap list in web/data.js
    had lost the entry entirely.

    WHAT THEY ARE. Both are recovery bills for the damage the stack took:
    resources and cash to replace it, and hours to do it in. Both are linear in
    the same quantity, which is NOT HP lost:

        ue  =  HP lost / current per-unit HP  =  (pct lost / 100) * count

    "unit equivalents" -- how many whole units' worth of the stack is gone.
    Against a full-HP stack that is lost/maxHP, which is why a per-unit
    constant times HP lost fits every full-HP reading in the corpus and looks
    like the whole law. It is not. The trench sweep separates them: the
    defender there loses exactly 40.0 HP at every trench level, and its hours
    fall 6, 6, 6, 6, 5, 5, 5, 5, 4 as the trench enlarges the pool, because the
    same 40 HP destroys fewer whole units. HP lost never moves; the bill does.

        cost_r  =  round( sum over rows of  COST[unit][r] * ue_row )
        hours   =  floor( sum over rows of  REPAIR_HOURS[unit] * ue_row )

    Resources are exact to the printed integer; hours is floored ONCE over the
    stack total, not per row (the 62-hour two-row reading in mixed_stacks pins
    that: 4.41 + 57.60 floors to 62, while flooring each row gives 61).

    WHY A WIPE IS THE RIGHT INSTRUMENT HERE, AND NOT CENSORING. Every other
    sweep in this rig refuses a >=99.9% reading, because a wiped stack's DAMAGE
    is censored -- overkill is invisible. Nothing about that applies to ue. A
    wiped stack has lost exactly its whole count, so ue is the integer `count`
    with no rounding error at all, where every unwiped reading inherits the
    3-4 significant figures of the printed percentage. The censoring rule
    protects a quantity this experiment is not measuring; here the wipe is the
    cleanest possible input, and n=100 pins each hours constant to 0.01.

    WHAT THE CORPUS COULD NOT ANSWER, AND THIS SPENDS REQUESTS ON.
      1. Balloon. bal is absent from every resource-bearing experiment,
         because bal in 'air' triggers the known server bug and guard_payload
         refuses it. Measured on land, where a balloon is a land-class target.
      2. Buildings. The table's HP column excludes building rows -- the
         fortress response proves it. Whether the BILL excludes them too is a
         separate question and has never been asked.
      3. Heroes. The opposite of a building: a hero renders an ordinary span
         and the table's HP column counts it. Does it also cost resources?
      4. The discriminating prediction. A stack at 10% HP that is wiped has
         lost a tenth of the HP of a healthy one, but the same number of whole
         units. Under ue it costs the SAME full rebuild; under any law
         proportional to HP lost it costs a tenth. Resources are exact, so
         this separates the two with no rounding argument.
    """
    print("\n  1. cost and repair time per unit, read off a clean wipe\n")

    # A wiper per target class, chosen off CLASS_ATTACK for a column that can
    # actually finish the job inside the round budget.
    WIPER = {"land": ("ht", "land"), "air": ("int", "air"),
             "naval": ("bb", "sea")}
    # The balloon exception: 'air' is the combination that makes the server
    # return a bare form, so the one unit missing from the corpus is measured
    # on land, where balloon_class already established it counts as land.
    TERRAIN_OVERRIDE = {"bal": "land"}

    RES = ("food", "fish", "iron", "wood", "coal", "oil", "gas", "cash")
    N = 100
    cost: dict[str, dict[str, float]] = {}
    hours: dict[str, tuple[float, float]] = {}

    order = [(u, cls) for cls, us in UNIT_CLASSES.items() for u in us]
    print(f"  {'unit':7}{'hours':>7}{'t bracket':>18}   resources per whole unit")
    for unit, cls in order:
        terr = TERRAIN_OVERRIDE.get(unit)
        if terr is None:
            terr = {"land": "land", "air": "air", "naval": "sea"}[cls]
        atk, atk_terr = WIPER["land" if terr == "land" else
                              ("air" if terr == "air" else "naval")]
        ov = settings(rounds=100)
        ov.update(duel(1, atk, 300, unit, N,
                       atk_terrain=atk_terr, def_terrain=terr))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {unit:7} refused: {e}"[:96])
            continue
        s = dict(p.last_summary).get("B.1")
        d = dict(p.last_details)
        record("repair_cost", {"unit": unit, "n": N, "terrain": terr,
                               "attacker": atk, "wiped": True,
                               "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        if not s:
            print(f"  {unit:7} no summary table")
            continue
        b = d.get("B.1.1") or {}
        if (b.get("pct") or 0) < 99.9:
            # Not wiped -> ue is not the count, and this reading cannot carry
            # the exactness the whole method rests on. Refuse it rather than
            # divide by an assumed ue.
            print(f"  {unit:7} NOT wiped ({b.get('pct')}%) — refused, "
                  f"ue is only exact on a wipe")
            continue
        h = s.get("hours")
        cost[unit] = {k: s.get(k, 0.0) / N for k in RES if s.get(k, 0.0)}
        hours[unit] = (h / N, (h + 1) / N)
        shown = ", ".join(f"{k} {v:g}" for k, v in cost[unit].items()) or "none"
        print(f"  {unit:7}{h:>7.0f}   [{h/N:7.4f},{(h+1)/N:7.4f})   {shown}")

    print("\n  2. is the hours total floored once, or once per row?")
    print("     (a wipe cannot answer this; the corpus can, and does: the "
          "two-row\n      62-hour reading floors once — 4.41 + 57.60 -> 62, "
          "per-row -> 61)")

    print("\n  3. a wiped stack at 10% HP: same bill, or a tenth of it?\n")
    print(f"  {'hp':>6}{'lost':>9}{'ue':>7}{'iron':>9}{'oil':>9}"
          f"{'cash':>10}{'hours':>7}")
    damaged: list[tuple[str, dict[str, float]]] = []
    for hp in ("100%", "10%"):
        ov = settings(rounds=100)
        ov.update(duel(1, "ht", 300, "art", 20, def_hp=hp))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {hp}: {e}"[:96]); continue
        s = dict(p.last_summary).get("B.1") or {}
        d = dict(p.last_details)
        record("repair_damaged", {"unit": "art", "n": 20, "def_hp": hp,
                                  "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.1") or {}
        if (b.get("pct") or 0) < 99.9:
            print(f"  {hp:>6} not wiped — cannot compare"); continue
        damaged.append((hp, s))
        print(f"  {hp:>6}{s.get('hp_lost', 0):>9.2f}{20:>7}"
              f"{s.get('iron', 0):>9.0f}{s.get('oil', 0):>9.0f}"
              f"{s.get('cash', 0):>10.0f}{s.get('hours', 0):>7.0f}")
    if len(damaged) == 2:
        (_, full), (_, hurt) = damaged
        same = all(abs(full.get(k, 0) - hurt.get(k, 0)) <= 1
                   for k in ("iron", "oil", "cash", "hours"))
        tenth = abs(hurt.get("cash", 0) - full.get("cash", 0) / 10) <= 1
        if same:
            verdict = ("IDENTICAL bill — the bill is per WHOLE UNIT destroyed, "
                       "not per HP lost.")
        elif tenth:
            verdict = "a tenth of the bill — the bill tracks HP lost."
        else:
            verdict = "neither — investigate before writing anything down."
        print(f"\n  VERDICT: {verdict}")

    print("\n  4. does a damaged BUILDING add to the bill?\n")
    print("     Infantry cost nothing to replace, so a 10-inf stack's bill is")
    print("     entirely hours. Any resource cell that moves is the building.\n")
    abb, lvl, bhp = "B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp"
    print(f"  {'config':22}{'inf lost':>10}{'ue':>7}{'predicted h':>13}"
          f"{'actual h':>10}   resources")
    for label, with_bldg in (("10 inf", False), ("10 inf + fortress 5", True)):
        ov = settings()
        ov.update(duel(1, "ht", 20, "inf", 10))
        fields: tuple[str, ...] = ()
        if with_bldg:
            ov.update({abb: "fortress", lvl: "5", bhp: "100%"})
            fields = (abb, lvl, bhp)
        try:
            p.submit(ov, create=fields) if fields else p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {label:22} refused: {e}"[:96]); continue
        s = dict(p.last_summary).get("B.1") or {}
        d = dict(p.last_details)
        record("repair_building", {"label": label, "building": with_bldg,
                                   "detail": d,
                                   "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.1") or {}
        if b.get("lost") is None or not b.get("pct"):
            print(f"  {label:22} no reading"); continue
        ue = b["pct"] / 100.0 * 10
        res = ", ".join(f"{k} {s.get(k, 0):g}" for k in RES if s.get(k, 0))
        print(f"  {label:22}{b['lost']:>10.2f}{ue:>7.3f}"
              f"{3.31 * ue:>13.2f}{s.get('hours', 0):>10.0f}   {res or 'none'}")

    print("\n  5. does a HERO add to the bill?\n")
    hero_abb, hero_lvl, hero_hp = HERO_FIELDS
    print(f"  {'config':22}{'inf lost':>10}{'hero lost':>11}"
          f"{'ue(inf)':>9}{'predicted h':>13}{'actual h':>10}   resources")
    for label, hero in (("10 inf", None), ("10 inf + alvin 10", "alvin")):
        ov = settings()
        ov.update(duel(1, "ht", 20, "inf", 10))
        fields = ()
        if hero:
            ov.update({hero_abb: hero, hero_lvl: "10", hero_hp: "100%"})
            fields = HERO_FIELDS
        try:
            p.submit(ov, create=fields) if fields else p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {label:22} refused: {e}"[:96]); continue
        s = dict(p.last_summary).get("B.1") or {}
        d = dict(p.last_details)
        record("repair_hero", {"label": label, "hero": hero, "detail": d,
                               "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.1") or {}
        hero_row = next((v for k, v in d.items()
                         if k.startswith("B.1.hero")), None)
        if b.get("lost") is None or not b.get("pct"):
            print(f"  {label:22} no reading"); continue
        ue = b["pct"] / 100.0 * 10
        res = ", ".join(f"{k} {s.get(k, 0):g}" for k in RES if s.get(k, 0))
        hl = (hero_row or {}).get("lost")
        print(f"  {label:22}{b['lost']:>10.2f}"
              f"{('-' if hl is None else f'{hl:.2f}'):>11}{ue:>9.3f}"
              f"{3.31 * ue:>13.2f}{s.get('hours', 0):>10.0f}   {res or 'none'}")

    print("\n  Constants for web/data.js (REPAIR_COST / REPAIR_HOURS):")
    for u in cost:
        lo, hi = hours[u]
        print(f"    {u:8} hours [{lo:.4f}, {hi:.4f})  "
              f"{ {k: round(v) for k, v in cost[u].items()} }")


def exp_hero_repair(p: Probe) -> None:
    """Heroes bill for repair; buildings do not. What is the hero's rate?

    exp_repair_cost established the scope rule the hard way. A fortress that
    lost 180 HP moved neither a resource cell nor the hours (33.10 predicted
    from the infantry alone, 33 printed). A hero that lost 66.7 HP took the
    same stack from 33 hours to 81. That is exactly the inclusion rule the HP
    column already follows -- refine_details() documents that the table counts
    a hero row and excludes a building row -- so the finding is really that
    ALL ELEVEN COLUMNS share one scope: unit rows and hero rows in, building
    rows out. Worth stating once, because it was arrived at twice.

    What the single alvin reading cannot say is the SHAPE of the hero term.
    81 = floor(3.32*10 + X) puts the hero's contribution in (47.7, 48.8], and
    with the hero at ue 0.667 that is a rate near 72 h -- but one point cannot
    separate "proportional to the hero's own ue, like a unit" from "a flat
    charge whenever the hero is scratched at all". Vary how hard the hero is
    hit and the two diverge immediately.

    A second hero says whether the rate is per-hero or shared. Heroes differ in
    every other coefficient this project has measured, so the prior is per-hero
    -- which is precisely why it should be checked rather than assumed.
    """
    hero_abb, hero_lvl, hero_hp = HERO_FIELDS
    print("\n  hours = floor( 3.32 * ue_inf  +  t_hero * ue_hero ) ?\n")
    print(f"  {'hero':8}{'atk':>5}{'inf lost':>10}{'ue_inf':>8}"
          f"{'hero lost':>11}{'ue_hero':>9}{'hours':>7}{'implied t_hero':>16}")
    rows: list[tuple[str, float, float, float]] = []
    for hero in ("alvin", "kangal"):
        for atk_n in (5, 12, 20):
            ov = settings()
            ov.update(duel(1, "ht", atk_n, "inf", 10))
            ov.update({hero_abb: hero, hero_lvl: "10", hero_hp: "100%"})
            try:
                p.submit(ov, create=HERO_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"  {hero:8}{atk_n:>5} refused: {e}"[:96])
                continue
            s = dict(p.last_summary).get("B.1") or {}
            d = dict(p.last_details)
            record("hero_repair", {"hero": hero, "atk_n": atk_n, "detail": d,
                                   "summary": dict(p.last_summary)},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = d.get("B.1.1") or {}
            h_row = d.get("B.1.hero") or {}
            hrs = s.get("hours")
            if b.get("pct") is None or h_row.get("pct") is None or hrs is None:
                print(f"  {hero:8}{atk_n:>5} incomplete reading")
                continue
            ue_inf = b["pct"] / 100.0 * 10
            ue_hero = h_row["pct"] / 100.0
            # floor(a + t*ue) = hrs  ->  t in [ (hrs-a)/ue, (hrs+1-a)/ue )
            lo = (hrs - 3.33 * ue_inf) / ue_hero
            hi = (hrs + 1 - 3.32 * ue_inf) / ue_hero
            rows.append((hero, ue_inf, ue_hero, hrs))
            print(f"  {hero:8}{atk_n:>5}{b['lost']:>10.2f}{ue_inf:>8.3f}"
                  f"{h_row['lost']:>11.2f}{ue_hero:>9.4f}{hrs:>7.0f}"
                  f"   [{lo:6.2f},{hi:6.2f})")

    for hero in ("alvin", "kangal"):
        mine = [r for r in rows if r[0] == hero]
        if len(mine) < 2:
            continue
        lo, hi = 0.0, 1e9
        flat_lo, flat_hi = 0.0, 1e9
        for _, ue_inf, ue_hero, hrs in mine:
            lo = max(lo, (hrs - 3.33 * ue_inf) / ue_hero)
            hi = min(hi, (hrs + 1 - 3.32 * ue_inf) / ue_hero)
            flat_lo = max(flat_lo, hrs - 3.33 * ue_inf)
            flat_hi = min(flat_hi, hrs + 1 - 3.32 * ue_inf)
        prop_ok = lo < hi
        flat_ok = flat_lo < flat_hi
        print(f"\n  {hero}: proportional-to-ue {'SURVIVES' if prop_ok else 'REFUTED'}"
              f"  bracket [{lo:.3f}, {hi:.3f})" if prop_ok else
              f"\n  {hero}: proportional-to-ue REFUTED")
        print(f"  {hero}: flat-charge      "
              f"{'SURVIVES' if flat_ok else 'REFUTED'}"
              + (f"  bracket [{flat_lo:.2f}, {flat_hi:.2f})" if flat_ok else ""))


# Repair hours per whole unit, as measured brackets. Only the three screen
# units this experiment uses; the full table lives in web/data.js.
REPAIR_HOURS_LOCAL = {"inf": (3.32, 3.33), "sub": (32.40, 32.41),
                      "int": (32.4013, 32.40636)}


def exp_hero_repair_all(p: Probe) -> None:
    """Close the hero-repair gap instead of declaring it.

    exp_hero_repair measured two heroes and found one shared rate, bracket
    [71.75, 72.61). That was written into NOT_MEASURED as an open gap, because
    two agreeing heroes is weak evidence for twenty-two and every OTHER hero
    coefficient in this project -- own attack, buffs, HP pools, target-class
    columns -- differs per hero, sometimes by a factor of ten.

    It is also a gap that closes for about forty requests of entirely
    mechanical work, which is a bad reason to leave it open. Two attack
    strengths per hero is enough: two points refute a flat charge and pin a
    bracket, and the shape question is already settled on two heroes.

    Sea and air heroes are run in their own terrain against a screen of their
    own class, because a naval hero on land is a configuration the server has
    refused before.
    """
    hero_abb, hero_lvl, hero_hp = HERO_FIELDS
    LAND = ["kangal", "joffre", "joffre_home", "marco", "allen", "larab",
            "alvin", "lucien", "lucien_g", "pershing", "georg", "tatiana",
            "hank", "johan", "tatiana_home", "maeve"]
    OTHER = {"otto": "sea", "togo": "sea", "togo_b": "sea", "ivan": "sea",
             "rbaron": "air", "thaden": "air"}
    SCREEN = {"land": ("inf", "ht"), "sea": ("sub", "bb"), "air": ("int", "int")}

    print(f"\n  {'hero':14}{'terrain':8}{'atk':>5}{'ue_unit':>9}"
          f"{'ue_hero':>9}{'hours':>7}   t bracket")
    per: dict[str, list[tuple[float, float, float]]] = {}
    plan = [(h, "land") for h in LAND] + list(OTHER.items())
    for hero, terr in plan:
        unit, wiper = SCREEN[terr]
        t_unit = REPAIR_HOURS_LOCAL[unit]
        for atk_n in (8, 20):
            ov = settings()
            ov.update(duel(1, wiper, atk_n, unit, 10,
                           atk_terrain=terr, def_terrain=terr))
            ov.update({hero_abb: hero, hero_lvl: "10", hero_hp: "100%"})
            try:
                p.submit(ov, create=HERO_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"  {hero:14}{terr:8}{atk_n:>5} refused: {e}"[:98])
                continue
            s = dict(p.last_summary).get("B.1") or {}
            d = dict(p.last_details)
            record("hero_repair_all",
                   {"hero": hero, "terrain": terr, "screen": unit,
                    "atk_n": atk_n, "detail": d,
                    "summary": dict(p.last_summary)},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = d.get("B.1.1") or {}
            hr = d.get("B.1.hero") or {}
            hrs = s.get("hours")
            if b.get("pct") is None or hr.get("pct") is None or hrs is None:
                print(f"  {hero:14}{terr:8}{atk_n:>5} incomplete")
                continue
            ue_u = b["pct"] / 100.0 * 10
            ue_h = hr["pct"] / 100.0
            if ue_h <= 0:
                print(f"  {hero:14}{terr:8}{atk_n:>5} hero untouched — no power")
                continue
            lo = (hrs - t_unit[1] * ue_u) / ue_h
            hi = (hrs + 1 - t_unit[0] * ue_u) / ue_h
            per.setdefault(hero, []).append((ue_u, ue_h, hrs))
            print(f"  {hero:14}{terr:8}{atk_n:>5}{ue_u:>9.3f}{ue_h:>9.4f}"
                  f"{hrs:>7.0f}   [{lo:6.2f},{hi:6.2f})")

    print(f"\n  {'hero':14}{'pts':>4}   per-hero bracket        flat charge?")
    shared_lo, shared_hi = 0.0, 1e9
    for hero, pts in per.items():
        terr = OTHER.get(hero, "land")
        unit = SCREEN[terr][0]
        t_unit = REPAIR_HOURS_LOCAL[unit]
        lo, hi, flo, fhi = 0.0, 1e9, 0.0, 1e9
        for ue_u, ue_h, hrs in pts:
            lo = max(lo, (hrs - t_unit[1] * ue_u) / ue_h)
            hi = min(hi, (hrs + 1 - t_unit[0] * ue_u) / ue_h)
            flo = max(flo, hrs - t_unit[1] * ue_u)
            fhi = min(fhi, hrs + 1 - t_unit[0] * ue_u)
        shared_lo, shared_hi = max(shared_lo, lo), min(shared_hi, hi)
        ok = "[%.2f, %.2f)" % (lo, hi) if lo < hi else "INCONSISTENT"
        print(f"  {hero:14}{len(pts):>4}   {ok:22}  "
              f"{'survives' if flo < fhi else 'refuted'}")
    if shared_lo < shared_hi:
        print(f"\n  ONE SHARED RATE SURVIVES all {len(per)} heroes: "
              f"[{shared_lo:.3f}, {shared_hi:.3f})")
    else:
        print(f"\n  NO SINGLE RATE covers every hero — the rate is PER HERO.")


def exp_bombardment(p: Probe) -> None:
    """The togo_b gap, closed by reading the author's own help page.

    HOW THIS WAS FOUND. Five audits in, the claim was that the server authors
    two inventories -- the fields it accepts and the columns it prints -- and
    that both had now been swept. That was wrong by one. Every control on the
    form links to share/s1914.info.html with an anchor, thirteen distinct ones,
    and that page is a THIRD server-authored inventory: the author's own prose
    describing what the calculator is supposed to do. It had never been read.

    Two of its section anchors are #togo and #lucien -- precisely the two
    heroes in this project's togo_b_unstable gap, the one recorded as needing
    "a mechanism nobody has proposed yet".

    WHAT THE PAGE SAYS.

        "If you are using the bombardment version of Togo Heihachiro the
         bombardment ability will be in effect for 6 rounds. This is in
         additional to the normal damage that the stack inflicts. Any stack
         (enemy or your own) within 40 km of the target stack will take
         bombardment damage. If you want an enemy stack to receive bombardment
         damage, but not the main damage from the stack, put its position more
         than 5 km from the target and within 40 km of the target."

        "The gas version of Lucien will last 9 rounds. Comments above for Togo
         also apply to Lucien except that ranges and radii are different for
         Lucien depending on the level."

    So the "unstable own contribution" was never an own contribution at all. It
    is a SECOND DAMAGE SOURCE with its own radius and its own duration, and the
    decomposition that produced the 37.99-64.90 band was subtracting a baseline
    from a total that had two terms in it. The gap note says the next step is
    "a different KIND of variable: rounds, distance, or the hero's own HP
    percentage". It named the right two and nobody ran them: all 191 togo and
    lucien readings in results.jsonl sit at one position with rounds unvaried.

    WHY THE AUTHOR'S PROSE IS A HYPOTHESIS, NOT AN ANSWER. It is documentation,
    written by a person, about software that has changed; it can be stale or
    simply wrong, and this project has already caught its own handover saying
    three things that were false. So nothing here is recorded because the page
    says it. Every claim below is turned into a number the server has to
    produce, and the isolation the page suggests is exactly what makes that
    possible:

      1. RADIUS. Submarines are melee (range 5). Put the target at 10 km and
         the attacking stack cannot reach it at all, so ANY damage the target
         takes is bombardment and nothing else. No subtraction, no baseline.
         Sweep 0, 3, 10, 20, 30, 40, 50 against three attackers -- no hero,
         plain Togo, Togo w/bombardment -- and the plain-Togo row is the
         control that says the effect belongs to the bombardment and not to
         "a hero being present".
      2. DURATION. Same isolation, rounds 1 through 8. If the ability really
         stops after 6, cumulative damage rises to round 6 and is then flat,
         which no ordinary attack does.
      3. FRIENDLY FIRE. "enemy or your own" is the strangest claim on the page
         and the easiest to check: a SECOND FRIENDLY stack, 20 km from the
         target and 30 km from its own flagship, with nothing attacking it.
         Under every model this project has ever held, that stack cannot take
         damage.
      4. LUCIEN, whose radius the page says varies with LEVEL -- the one axis
         that would make a radius look like an unstable coefficient.
    """
    abb, lvl, hhp = HERO_ATK_FIELDS
    POSITIONS = [0, 3, 10, 20, 30, 40, 50]

    def strike(hero: str | None, dist: int, rounds: str | float = 1,
               level: int = 10, atk_unit: str = "sub", tgt_unit: str = "sub",
               terrain: str = "sea", tag: str = "bombardment") -> dict | None:
        ov = settings(rounds)
        ov.update(duel(1, atk_unit, 10, tgt_unit, 50,
                       atk_terrain=terrain, def_terrain=terrain))
        ov["B.1.position"] = str(dist)          # attacker stays at 0
        fields: tuple[str, ...] = ()
        if hero:
            ov.update({abb: hero, lvl: str(level), hhp: "100%"})
            fields = HERO_ATK_FIELDS
        try:
            p.submit(ov, create=fields) if fields else p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"    refused ({hero}, {dist} km): {e}"[:96])
            return None
        d = dict(p.last_details)
        record(tag, {"hero": hero, "level": level, "distance": dist,
                     "rounds": rounds, "atk": atk_unit, "target": tgt_unit,
                     "terrain": terrain, "detail": d,
                     "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        return d

    print("\n  1. RADIUS — target beyond melee, so any damage at all is "
          "bombardment\n")
    header = "  " + f"{'km':>4}" + "".join(f"{h:>14}" for h in
                                           ("no hero", "togo", "togo w/bomb"))
    print(header)
    radius: dict[int, dict[str, float | None]] = {}
    for dist in POSITIONS:
        row: dict[str, float | None] = {}
        for key, hero in (("no hero", None), ("togo", "togo"),
                          ("togo w/bomb", "togo_b")):
            d = strike(hero, dist)
            b = (d or {}).get("B.1.1") or {}
            row[key] = b.get("lost")
        radius[dist] = row
        cells = "".join(("%14s" % ("-" if row[k] is None else f"{row[k]:.2f}"))
                        for k in ("no hero", "togo", "togo w/bomb"))
        print(f"  {dist:>4}{cells}")

    reach = [d for d, r in radius.items()
             if (r.get("togo w/bomb") or 0) > 0 and (r.get("togo") or 0) == 0]
    silent = [d for d, r in radius.items()
              if (r.get("togo w/bomb") or 0) == 0]
    print(f"\n  bombardment reaches: {reach or 'nowhere'} km")
    print(f"  silent at:           {silent or 'nowhere'} km")
    if reach:
        print(f"  VERDICT: a SECOND damage source, not an own-attack "
              f"coefficient. It reaches {max(reach)} km where the stack "
              f"itself stops at 5 km (submarines are melee).")

    print("\n  2. DURATION — does it stop after 6 rounds?\n")
    print(f"  {'rounds':>7}{'cumulative':>13}{'this round':>13}")
    prev = 0.0
    seen: list[tuple[int, float]] = []
    for rounds in range(1, 9):
        d = strike("togo_b", 10, rounds=rounds)
        b = (d or {}).get("B.1.1") or {}
        cum = b.get("lost")
        if cum is None:
            print(f"  {rounds:>7}            -            -"); continue
        seen.append((rounds, cum))
        print(f"  {rounds:>7}{cum:>13.2f}{cum - prev:>13.2f}")
        prev = cum
    if len(seen) >= 7:
        deltas = {r: c - (dict(seen).get(r - 1, 0.0)) for r, c in seen}
        stops = [r for r in range(2, 9) if abs(deltas.get(r, 0.0)) < 0.005]
        first_stop = min(stops) if stops else None
        print(f"\n  first round contributing nothing: {first_stop}")
        if first_stop:
            print(f"  VERDICT: the ability lasts {first_stop - 1} rounds.")

    print("\n  3. FRIENDLY FIRE — a second stack of OURS, nothing attacking "
          "it\n")
    print("     A.1 subs + hero at 0 km, attacking B.1 at 10 km.")
    print("     A.2 subs at 30 km: 20 km from the target, 25 km outside any")
    print("     melee range, and not attacking or attacked by anything.\n")
    A2 = ("A.2.target", "A.2.terrain", "A.2.position", "A.2.trench",
          "A.2.1.unit", "A.2.1.count", "A.2.1.hp")
    print(f"  {'hero':14}{'B.1 (enemy)':>14}{'A.2 (ours)':>14}")
    for hero in ("togo", "togo_b"):
        ov = settings(1)
        ov.update(duel(1, "sub", 10, "sub", 50,
                       atk_terrain="sea", def_terrain="sea"))
        ov["B.1.position"] = "10"
        ov.update({abb: hero, lvl: "10", hhp: "100%"})
        ov.update({"A.2.target": "0", "A.2.terrain": "sea",
                   "A.2.position": "30", "A.2.trench": "0",
                   "A.2.1.unit": "sub", "A.2.1.count": "20",
                   "A.2.1.hp": "100%"})
        try:
            p.submit(ov, create=HERO_ATK_FIELDS + A2)
        except (BareFormReturned, ValueError) as e:
            print(f"  {hero:14} refused: {e}"[:96]); continue
        d = dict(p.last_details)
        record("bombardment_friendly",
               {"hero": hero, "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        enemy = ((d.get("B.1.1") or {}).get("lost"))
        ours = ((d.get("A.2.1") or {}).get("lost"))
        f = lambda v: "-" if v is None else f"{v:.2f}"
        print(f"  {hero:14}{f(enemy):>14}{f(ours):>14}")

    print("\n  4. LUCIEN W/GAS — the page says its radius varies with LEVEL\n")
    print(f"  {'km':>4}" + "".join(f"{('lv ' + str(l)):>12}"
                                   for l in (1, 5, 10, 20)))
    for dist in (0, 3, 10, 20, 30, 40, 50):
        cells = ""
        for level in (1, 5, 10, 20):
            d = strike("lucien_g", dist, level=level, atk_unit="inf",
                       tgt_unit="inf", terrain="land", tag="bombardment_lucien")
            b = (d or {}).get("B.1.1") or {}
            v = b.get("lost")
            cells += "%12s" % ("-" if v is None else f"{v:.2f}")
        print(f"  {dist:>4}{cells}")


def exp_bombardment_law(p: Probe) -> None:
    """Pin the two constants the radius sweep only sketched.

    exp_bombardment established the mechanism: Togo-with-bombardment adds a
    SECOND damage source, centred on the target, lasting 6 rounds, splashing
    every stack within 40 km including friendly ones. Three configurations put
    its total at 50.00 and its split close to each stack's share of the HP pool
    in the blast. Close is not measured, and two things are still guesses:

      SPLIT. Three points, all with the same 10-vs-50 shape, sit 0.3-0.5%
      below a strict pool-proportional split. That is more than the printed
      precision, so either the rule is not exactly pool share or something
      small is also in the blast -- the hero's own row is the obvious
      candidate, and it does take damage (0.3 where its stack takes 8.3).
      Five attacker sizes against a fixed defender separate a pool split from
      a count split from anything with a fixed extra participant.

      LEVEL. The recorded atkAttackingCurve for this hero -- 24.98, 29.97,
      29.97, 34.96, ... -- was read as an own-attack curve. It cannot be: the
      own attack is 15.00 flat, measured after the ability expires. Every one
      of those numbers is 15.00 plus a bombardment SHARE, so the curve is the
      shape of the bombardment as seen through one particular pool ratio.
      Read at 50 km, where the target is the only stack in the blast, the
      share is 1.0 and the reading is the total outright.

    ISOLATION. 50 km, submarines, one round. The stack cannot reach, so the
    only two terms are the hero's flat 15.00 and the whole bombardment.
    """
    abb, lvl, hhp = HERO_ATK_FIELDS
    OWN = 15.00

    def read(level: int, dist: int, atk_n: int, def_n: int) -> float | None:
        ov = settings(1)
        ov.update(duel(1, "sub", atk_n, "sub", def_n,
                       atk_terrain="sea", def_terrain="sea"))
        ov["B.1.position"] = str(dist)
        ov.update({abb: "togo_b", lvl: str(level), hhp: "100%"})
        try:
            p.submit(ov, create=HERO_ATK_FIELDS)
        except (BareFormReturned, ValueError) as e:
            print(f"    refused (lv{level}, {dist} km, {atk_n}v{def_n}): {e}"[:92])
            return None
        d = dict(p.last_details)
        record("bombardment_law",
               {"hero": "togo_b", "level": level, "distance": dist,
                "atk_n": atk_n, "def_n": def_n, "detail": d,
                "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        return d

    print("\n  1. THE SPLIT — fixed defender, five attacker sizes, at 10 km\n")
    print(f"  {'atk':>5}{'poolA':>8}{'B lost':>9}{'bombard':>9}"
          f"{'share':>8}{'pool share':>12}{'diff':>8}")
    pts: list[tuple[float, float]] = []
    for atk_n in (5, 10, 25, 50, 100):
        d = read(10, 10, atk_n, 50)
        if d is None:
            continue
        b = (d.get("B.1.1") or {}).get("lost")
        if b is None:
            print(f"  {atk_n:>5}  no reading"); continue
        bomb = b - OWN
        share = bomb / 50.0
        poolA, poolB = atk_n * 100.0, 5000.0
        expect = poolB / (poolA + poolB)
        pts.append((poolA, share))
        print(f"  {atk_n:>5}{poolA:>8.0f}{b:>9.2f}{bomb:>9.2f}"
              f"{share:>8.4f}{expect:>12.4f}{(share - expect):>8.4f}")
    if len(pts) >= 3:
        # If the split is pool-proportional over a blast that also contains an
        # extra participant of pool X, then 1/share = 1 + (poolA + X)/poolB, so
        # 1/share is LINEAR in poolA and the intercept gives X.
        n = len(pts)
        sx = sum(a for a, _ in pts); sy = sum(1.0 / s for _, s in pts)
        sxx = sum(a * a for a, _ in pts); sxy = sum(a * (1.0 / s) for a, s in pts)
        slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
        icept = (sy - slope * sx) / n
        poolB = 5000.0
        print(f"\n  1/share against poolA:  slope {slope:.8f} "
              f"(1/poolB would be {1/poolB:.8f})")
        extra = (icept - 1.0) * poolB
        print(f"  intercept {icept:.5f} -> an extra {extra:.1f} HP of pool in "
              f"the blast besides the two unit stacks")
        print(f"  (the hero's own row is the candidate; a strict two-stack "
              f"pool split predicts an intercept of exactly 1.0)")

    print("\n  2. THE TOTAL BY LEVEL — read at 50 km, share = 1.0\n")
    print(f"  {'level':>6}{'B lost':>9}{'bombardment total':>20}")
    for level in (1, 2, 3, 5, 10, 15, 20):
        d = read(level, 50, 10, 50)
        if d is None:
            continue
        b = (d.get("B.1.1") or {}).get("lost")
        if b is None:
            print(f"  {level:>6}  no reading"); continue
        print(f"  {level:>6}{b:>9.2f}{b - OWN:>20.2f}")


def exp_bombardment_own(p: Probe) -> None:
    """Separate the hero's own attack from its bombardment, level by level.

    At 50 km with submarines the stack cannot reach, so a togo_b reading is
    exactly (own attack + whole bombardment) and a togo reading is exactly
    (own attack), because the two heroes are the same hull differing only in
    the ability. Subtracting one from the other at matched level is the same
    two-configuration decomposition this project used for the trench and the
    fortress, and it is what the original hero sweep could not do: it never
    moved the target out of melee, so every reading had the STACK's damage in
    it as well and the subtraction had three terms instead of two.

    This is what makes the recorded atkAttackingCurve wrong rather than
    imprecise. 24.98, 29.97, 29.97, 34.96 ... was recorded as an own-attack
    curve. It is the SUM, seen through one pool ratio.
    """
    abb, lvl, hhp = HERO_ATK_FIELDS
    LEVELS = (1, 2, 3, 5, 10, 15, 20)
    got: dict[str, dict[int, float]] = {"togo": {}, "togo_b": {}}
    for hero in ("togo", "togo_b"):
        for level in LEVELS:
            ov = settings(1)
            ov.update(duel(1, "sub", 10, "sub", 50,
                           atk_terrain="sea", def_terrain="sea"))
            ov["B.1.position"] = "50"
            ov.update({abb: hero, lvl: str(level), hhp: "100%"})
            try:
                p.submit(ov, create=HERO_ATK_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"  {hero} lv{level}: {e}"[:92]); continue
            d = dict(p.last_details)
            record("bombardment_own",
                   {"hero": hero, "level": level, "distance": 50,
                    "detail": d, "summary": dict(p.last_summary)},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            b = (d.get("B.1.1") or {}).get("lost")
            if b is not None:
                got[hero][level] = b
    print(f"\n  {'level':>6}{'togo':>9}{'togo w/bomb':>13}"
          f"{'bombardment':>13}{'5 x level':>11}")
    for level in LEVELS:
        a, b = got["togo"].get(level), got["togo_b"].get(level)
        if a is None or b is None:
            print(f"  {level:>6}  incomplete"); continue
        print(f"  {level:>6}{a:>9.2f}{b:>13.2f}{b - a:>13.2f}{5.0 * level:>11.2f}")
    own = sorted(set(round(v, 2) for v in got["togo"].values()))
    print(f"\n  plain Togo's own attack across levels: {own}")
    print("  (flat means the recorded per-level curve was the ABILITY moving, "
          "not the hero)")


def exp_bombardment_finish(p: Probe) -> None:
    """Fill the low levels, and do Lucien the same way.

    Three things left. The togo_b total is 5 x level from level 3 up but reads
    10 and 15 at levels 1 and 2, and level 4 was never sent -- the only
    evidence for it is the old atkAttackingCurve, recorded under the reading
    this experiment just overturned, so it is not evidence at all. Lucien
    w/gas is the same family and has never been decomposed. And the page says
    Lucien lasts NINE rounds where Togo lasts six, which is the cheapest
    possible check of whether the durations are really per-hero.

    All at 50 km, where the stack cannot reach and the target is the only
    thing in the blast, so every reading is (own attack + whole ability) and
    the plain-hero control subtracts to the ability alone.
    """
    abb, lvl, hhp = HERO_ATK_FIELDS

    def read(hero: str, level: int, rounds: str | float = 1,
             unit: str = "sub", terrain: str = "sea") -> float | None:
        ov = settings(rounds)
        ov.update(duel(1, unit, 10, unit, 50,
                       atk_terrain=terrain, def_terrain=terrain))
        ov["B.1.position"] = "50"
        ov.update({abb: hero, lvl: str(level), hhp: "100%"})
        try:
            p.submit(ov, create=HERO_ATK_FIELDS)
        except (BareFormReturned, ValueError) as e:
            print(f"    {hero} lv{level} r{rounds}: {e}"[:92]); return None
        d = dict(p.last_details)
        record("bombardment_finish",
               {"hero": hero, "level": level, "rounds": rounds, "distance": 50,
                "unit": unit, "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        return (d.get("B.1.1") or {}).get("lost")

    print("\n  1. togo_b at the levels never sent (own attack is 15.00 flat)\n")
    print(f"  {'level':>6}{'B lost':>9}{'ability':>10}{'5 x level':>11}")
    for level in (4, 6, 7, 8, 9):
        b = read("togo_b", level)
        if b is None:
            continue
        print(f"  {level:>6}{b:>9.2f}{b - 15.0:>10.2f}{5.0 * level:>11.2f}")

    print("\n  2. LUCIEN W/GAS, decomposed against plain Lucien\n")
    print(f"  {'level':>6}{'lucien':>9}{'lucien w/gas':>14}{'ability':>10}"
          f"{'3 x level':>11}")
    for level in (1, 2, 3, 5, 10, 15):
        a = read("lucien", level, unit="inf", terrain="land")
        b = read("lucien_g", level, unit="inf", terrain="land")
        if a is None or b is None:
            print(f"  {level:>6}  incomplete"); continue
        print(f"  {level:>6}{a:>9.2f}{b:>14.2f}{b - a:>10.2f}{3.0 * level:>11.2f}")

    print("\n  3. DURATION — the page says Lucien lasts 9 rounds, Togo 6\n")
    print(f"  {'rounds':>7}{'cumulative':>13}{'this round':>13}")
    prev = 0.0
    for rounds in range(7, 12):
        b = read("lucien_g", 10, rounds=rounds, unit="inf", terrain="land")
        if b is None:
            continue
        print(f"  {rounds:>7}{b:>13.2f}{b - prev:>13.2f}")
        prev = b
    print("\n  (a round contributing only the hero's own attack is a round "
          "the ability\n   is no longer running)")


def exp_bombardment_lucien(p: Probe) -> None:
    """Two loose ends on Lucien, both of which would otherwise become bad data.

    LEVEL 15 READ 32.89, and this project does not record a number like that
    as a constant without asking why it is not round. Every other reading in
    the family is: 10, 15, 20, 25, 30 ... The suspicion is that the reading is
    not the total at all. The page says Lucien's radius GROWS with level, the
    radius sweep measured it at 20 km (lv 1), 30 (lv 5) and 40 (lv 10), and at
    level 15 it may simply have grown past the 50 km the reading was taken at
    -- which would put the ATTACKER inside its own blast and make 32.89 a
    share rather than a total. Re-reading at 75 and 150 km settles it: if the
    number goes up and turns round, the radius is the explanation.

    LEVELS 4 and 6-9 were never sent for Lucien, and the shape below level 5
    is flat at 15 where the shape above it climbs, so the join is exactly
    where a guess would be worst.
    """
    abb, lvl, hhp = HERO_ATK_FIELDS
    OWN = 8.00

    def read(level: int, dist: int) -> float | None:
        ov = settings(1)
        ov.update(duel(1, "inf", 10, "inf", 50,
                       atk_terrain="land", def_terrain="land"))
        ov["B.1.position"] = str(dist)
        ov.update({abb: "lucien_g", lvl: str(level), hhp: "100%"})
        try:
            p.submit(ov, create=HERO_ATK_FIELDS)
        except (BareFormReturned, ValueError) as e:
            print(f"    lv{level} {dist}km: {e}"[:92]); return None
        d = dict(p.last_details)
        record("bombardment_lucien2",
               {"hero": "lucien_g", "level": level, "distance": dist,
                "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        return d

    print("\n  1. is level 15's 32.89 a total, or a share of a bigger blast?\n")
    print(f"  {'km':>5}{'B lost':>9}{'ability':>10}{'A.1 lost':>11}"
          f"   A.1 inside its own blast?")
    for dist in (50, 75, 150):
        d = read(15, dist)
        if d is None:
            continue
        b = (d.get("B.1.1") or {}).get("lost")
        a = (d.get("A.1.1") or {}).get("lost")
        if b is None:
            print(f"  {dist:>5}  no reading"); continue
        inside = "YES — it is sharing" if (a or 0) > 0 else "no — clean total"
        print(f"  {dist:>5}{b:>9.2f}{b - OWN:>10.2f}"
              f"{('-' if a is None else f'{a:.2f}'):>11}   {inside}")

    # Does the hero's OWN attack even reach 75 km? Togo's reached 50, and the
    # 32.00 above is only a total if the 8.00 is still in it. If plain Lucien
    # is silent at 75 the subtraction is wrong and the total is 40.00.
    print("\n  1b. is plain Lucien's own attack still firing at 75 km?\n")
    ov = settings(1)
    ov.update(duel(1, "inf", 10, "inf", 50,
                   atk_terrain="land", def_terrain="land"))
    ov["B.1.position"] = "75"
    ov.update({abb: "lucien", lvl: "15", hhp: "100%"})
    try:
        p.submit(ov, create=HERO_ATK_FIELDS)
        dd = dict(p.last_details)
        record("bombardment_lucien2",
               {"hero": "lucien", "level": 15, "distance": 75, "detail": dd,
                "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in dd.items()})
        bb = (dd.get("B.1.1") or {}).get("lost")
        print(f"  plain lucien at 75 km: {bb}")
    except (BareFormReturned, ValueError) as e:
        print(f"  plain lucien at 75 km: SILENT — {e}"[:96])
        print("  so the 32.00 above was a subtraction of an own attack that "
              "was not there;\n  the level-15 total is 40.00.")

    print("\n  2. the levels never sent, read at 50 km (75 is out of RANGE "
          "below level 15)\n")
    print(f"  {'level':>6}{'B lost':>9}{'A.1 lost':>10}{'ability':>10}"
          f"{'clean?':>9}")
    for level in (4, 6, 7, 8, 9, 11, 12, 13, 14):
        d = read(level, 50)
        if d is None:
            continue
        b = (d.get("B.1.1") or {}).get("lost")
        a = (d.get("A.1.1") or {}).get("lost")
        if b is None:
            print(f"  {level:>6}  no reading"); continue
        clean = "yes" if not (a or 0) else "SHARED"
        print(f"  {level:>6}{b:>9.2f}{(a or 0):>10.2f}{b - OWN:>10.2f}"
              f"{clean:>9}")


def exp_bombardment_melee(p: Probe) -> None:
    """Is the attacker inside its own blast when it is standing on the target?

    The radius sweep answered this for 10-40 km: yes, and the split is by pool
    share. At 0 km it did NOT answer it, because the attacking stack there was
    ten submarines against fifty and was wiped outright -- pool 1000 of 1000 --
    so whatever share it was owed is invisible.

    That matters because every hero curve this project ever recorded was taken
    in melee. If the defender absorbs the whole ability at 0 km, those curves
    contain a different quantity from the ones at 10 km, and the engine cannot
    be right about both with one rule.

    THE FIX IS AN ATTACKER THAT SURVIVES. A hundred submarines against fifty
    lose a small fraction instead of everything, and submarines carry no Togo
    buff -- his is on battleships -- so the togo/togo_b difference is the
    ability alone with nothing else moving.

        pool share predicts   5000 / (10000 + 5000 + 39.2) = 0.3325 -> 16.63
        whole ability to the defender                              -> 50.00

    Three times apart. Nothing subtle to argue about.
    """
    abb, lvl, hhp = HERO_ATK_FIELDS
    print(f"\n  {'km':>4}{'togo':>10}{'togo w/bomb':>14}{'difference':>13}"
          f"{'A lost':>10}   reading")
    for dist in (0, 3, 10):
        vals = {}
        alost = {}
        for hero in ("togo", "togo_b"):
            ov = settings(1)
            ov.update(duel(1, "sub", 100, "sub", 50,
                           atk_terrain="sea", def_terrain="sea"))
            ov["B.1.position"] = str(dist)
            ov.update({abb: hero, lvl: "10", hhp: "100%"})
            try:
                p.submit(ov, create=HERO_ATK_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"  {dist:>4} {hero}: {e}"[:92]); continue
            d = dict(p.last_details)
            record("bombardment_melee",
                   {"hero": hero, "distance": dist, "atk_n": 100, "def_n": 50,
                    "detail": d, "summary": dict(p.last_summary)},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            vals[hero] = (d.get("B.1.1") or {}).get("lost")
            alost[hero] = (d.get("A.1.1") or {}).get("lost")
        if len(vals) == 2 and None not in vals.values():
            diff = vals["togo_b"] - vals["togo"]
            share = diff / 50.0
            verdict = ("WHOLE ability to the defender" if abs(diff - 50.0) < 1.0
                       else f"SHARED — share {share:.4f} "
                            f"(pool share predicts 0.3325)")
            print(f"  {dist:>4}{vals['togo']:>10.2f}{vals['togo_b']:>14.2f}"
                  f"{diff:>13.2f}{(alost.get('togo_b') or 0):>10.2f}   {verdict}")


def exp_togo_buff_clean(p: Probe) -> None:
    """Does Togo w/bombardment really have a different buff curve, or was that
    the same artifact?

    data.js records something no other hero in either table needs: TWO
    battleship buff curves for togo_b, one attacking (1.2944 at level 10) and
    one defending (1.30, identical to plain Togo). An anomaly that exists on
    one side only, for the one hero whose own attack turned out to be a sum,
    is worth suspecting before it is worth believing.

    THE CLEAN CELL. A battleship reaches 75 km and the ability's radius is 40,
    so at 50 km the stack still fires while the attacker sits OUTSIDE its own
    blast -- the target absorbs the ability whole, with no share to work out.
    Then

        togo_b reading - togo reading  =  T(level)   exactly, if the buffs match

    because everything else on the two sides of that subtraction is identical:
    same hull, same pool, same own attack of 15.00, same stack, same target.
    If the buffs really do differ, the difference comes out wrong by the buff
    gap times the stack's output, which at ten battleships is large and
    obvious rather than a rounding argument.
    """
    abb, lvl, hhp = HERO_ATK_FIELDS
    TOTAL = {1: 10, 5: 25, 10: 50, 15: 75, 20: 100}
    print(f"\n  {'level':>6}{'togo':>10}{'togo w/bomb':>14}{'difference':>13}"
          f"{'ability':>10}   verdict")
    for level in (1, 5, 10, 15, 20):
        vals = {}
        for hero in ("togo", "togo_b"):
            ov = settings(1)
            ov.update(duel(1, "bb", 10, "cl", 200,
                           atk_terrain="sea", def_terrain="sea"))
            ov["B.1.position"] = "50"
            ov.update({abb: hero, lvl: str(level), hhp: "100%"})
            try:
                p.submit(ov, create=HERO_ATK_FIELDS)
            except (BareFormReturned, ValueError) as e:
                print(f"  {level:>6} {hero}: {e}"[:92]); continue
            d = dict(p.last_details)
            record("togo_buff_clean",
                   {"hero": hero, "level": level, "distance": 50,
                    "detail": d, "summary": dict(p.last_summary)},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            vals[hero] = (d.get("B.1.1") or {}).get("lost")
        if len(vals) == 2 and None not in vals.values():
            diff = vals["togo_b"] - vals["togo"]
            want = TOTAL[level]
            ok = abs(diff - want) < 0.6
            print(f"  {level:>6}{vals['togo']:>10.2f}{vals['togo_b']:>14.2f}"
                  f"{diff:>13.2f}{want:>10.0f}   "
                  f"{'buffs MATCH — the second curve was the artifact' if ok else 'buffs really do differ'}")


def exp_mutual(p: Probe) -> None:
    """Both stacks attacking each other -- never once submitted by this rig.

    duel() is the only thing in this file that has ever set a B-side target,
    and it always sets "0". Every one of the 2,400-odd readings on disk is one
    stack attacking a stack that is only defending. The form has always
    offered the other configuration, and the author's help page says it is not
    a cosmetic difference:

        "There are always two armies or sides, A and B ... If two stacks are
         each attacking the other it makes a difference which side they are
         on. Army A will always attack first in such a scenario ... this only
         applies if both stacks are attacking each other. If, for example, a
         stack in one army is attacking a stack that is just defending, it
         will make no difference which side they are on."

    That is two claims, and they are separable.

    CLAIM 1 -- A MUTUAL ATTACKER USES ITS ATTACK STAT. Not stated on the page
    at all, but it is the first thing to check, because this game keeps attack
    and defence as independent numbers and the gap is enormous for some units.
    A stormtrooper attacks land at 25.0 and defends against it at 6.3; an
    armoured car is the other way round, 6.0 attacking and 12.0 defending.
    So the two of them predict opposite movements -- st should roughly
    QUADRUPLE and ac should roughly HALVE -- and a rig artifact that inflated
    everything would show up immediately as both moving the same way.

    CLAIM 2 -- SIDE A GOES FIRST. If resolution is sequential then B fires
    with whatever survives A's blow, and the m(f) this project already measured
    applies. If it is simultaneous, the side letter cannot matter and the
    author is describing something that is not there.

        A = 10 inf vs B = 10 st, mutual
          simultaneous : B deals 25.0 x E(10) = 250.00
          A-first      : B has lost 40 of 400 first, so 250 x m(0.9) = 226.25

    Ten percent apart, on a reading printed to two decimals.

    THE SHARPEST FORM OF CLAIM 2 is the swap, where A's blow is fatal. Ten
    stormtroopers on side A deal 250 into an infantry pool of 200. If A goes
    first, B is dead before it fires. If the two are simultaneous, B still
    deals its full 40.00 -- and this project has ALREADY measured that a wiped
    stack deals full damage when it is defending, so "wiped" alone does not
    silence a stack. Whether it silences one that was attacking is exactly
    what has never been asked.
    """
    def run(tag: str, a_unit: str, a_n: int, b_unit: str, b_n: int,
            mutual: bool, rounds: str | float = 1) -> dict | None:
        ov = settings(rounds)
        ov.update(duel(1, a_unit, a_n, b_unit, b_n))
        if mutual:
            ov["B.1.target"] = "A.1"
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"    refused ({tag}): {e}"[:96])
            return None
        d = dict(p.last_details)
        record("mutual", {"a_unit": a_unit, "a_n": a_n, "b_unit": b_unit,
                          "b_n": b_n, "mutual": mutual, "rounds": rounds,
                          "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        return d

    print("\n  0. does the server accept a mutual target at all?\n")
    d = run("sanity", "inf", 10, "inf", 10, True)
    if d is None:
        print("  The form offers B.1.target = A.1 and the server refused it. "
              "Nothing below can run.")
        return
    print(f"  yes — A lost {(d.get('A.1.1') or {}).get('lost')}, "
          f"B lost {(d.get('B.1.1') or {}).get('lost')}")

    print("\n  1. does a MUTUAL attacker fire with its attack stat or its "
          "defence stat?\n")
    print("     A is ten infantry throughout; only B's role changes.")
    print("     'A lost' is B's output, which is the whole question.\n")
    print(f"  {'B stack':8}{'atk col':>9}{'def col':>9}"
          f"{'A lost (B defends)':>21}{'A lost (B attacks)':>21}   verdict")
    for unit, atk_c, def_c in (("st", 25.0, 6.3), ("rrg", 20.0, 6.7),
                               ("cav", 15.0, 7.5), ("ac", 6.0, 12.0),
                               ("inf", 4.0, 5.0), ("ht", 45.0, 45.0)):
        got = {}
        for mutual in (False, True):
            dd = run(f"{unit} mutual={mutual}", "inf", 10, unit, 10, mutual)
            a = (dd or {}).get("A.1.1") or {}
            if a.get("lost") is not None and (a.get("pct") or 0) < 99.9:
                got[mutual] = a["lost"]
        if len(got) != 2:
            print(f"  {unit:8}{atk_c:>9.1f}{def_c:>9.1f}"
                  f"{'censored or refused':>43}")
            continue
        per_def = got[False] / effective_units(10)
        per_atk = got[True] / effective_units(10)
        near = lambda v, x: abs(v - x) < 0.06 * max(x, 1.0)
        if near(per_atk, atk_c) and near(per_def, def_c):
            verdict = "ATTACK stat when attacking, defence when defending"
        elif abs(got[True] - got[False]) < 0.05:
            verdict = "no change — it fires the same either way"
        else:
            verdict = f"neither column ({per_atk:.2f} per effective unit)"
        print(f"  {unit:8}{atk_c:>9.1f}{def_c:>9.1f}"
              f"{got[False]:>21.2f}{got[True]:>21.2f}   {verdict}")

    print("\n  2. is it sequential (A first) or simultaneous?\n")
    print("     A = 10 inf, B = 10 st, mutual. A deals 40.00 into a pool of "
          "400.")
    print("       simultaneous  B deals 25.0 x E(10)      = 250.00")
    print("       A fires first B deals 250 x m(360/400)  = 226.25\n")
    dd = run("order", "inf", 10, "st", 10, True)
    if dd:
        a = (dd.get("A.1.1") or {}); b = (dd.get("B.1.1") or {})
        print(f"  A lost {a.get('lost')}   B lost {b.get('lost')}")
        if a.get("lost") is not None:
            v = a["lost"]
            if abs(v - 250.0) < 1.0:
                print("  VERDICT: SIMULTANEOUS — B fired at full strength.")
            elif abs(v - 226.25) < 1.5:
                print("  VERDICT: SEQUENTIAL — B fired with what survived A.")
            else:
                print(f"  VERDICT: neither figure ({v}). Investigate before "
                      "writing anything down.")

    print("\n  3. the swap, where A's blow is fatal\n")
    print("     A = 10 st, B = 10 inf, mutual. A deals 250 into a pool of "
          "200.")
    print("       simultaneous  B still deals 4.0 x E(10) = 40.00, exactly as")
    print("                     a WIPED DEFENDER already does (measured)")
    print("       A fires first B is dead before it fires = 0.00\n")
    dd = run("swap", "st", 10, "inf", 10, True)
    if dd:
        a = (dd.get("A.1.1") or {}); b = (dd.get("B.1.1") or {})
        print(f"  A lost {a.get('lost')}   B lost {b.get('lost')} "
              f"({b.get('pct')}%)")
        if a.get("lost") is not None:
            v = a["lost"]
            if abs(v - 40.0) < 0.5:
                print("  VERDICT: SIMULTANEOUS — a wiped mutual attacker still "
                      "deals its full figure, exactly like a wiped defender.")
            elif v < 0.05:
                print("  VERDICT: SEQUENTIAL — side A killed it before it "
                      "fired. The side letter is worth a whole stack.")
            else:
                print(f"  VERDICT: neither ({v}).")

    print("\n  4. and the control the page itself offers: when only ONE side")
    print("     attacks, the page says the side letter cannot matter.\n")
    print(f"  {'configuration':34}{'A lost':>10}{'B lost':>10}")
    for label, au, bu in (("A=inf attacks, B=st defends", "inf", "st"),
                          ("A=st defends... (swap roles)", "st", "inf")):
        dd = run(label, au, 10, bu, 10, False)
        if dd:
            a = (dd.get("A.1.1") or {}).get("lost")
            b = (dd.get("B.1.1") or {}).get("lost")
            f = lambda v: "-" if v is None else f"{v:.2f}"
            print(f"  {label:34}{f(a):>10}{f(b):>10}")


# Land-vs-land columns and per-unit max HP, from web/data.js. Only the land
# column is needed here: every stack in this experiment is a land stack.
LAND_ATK = {"inf": 4.0, "cav": 15.0, "ac": 6.0, "lart": 5.0, "art": 8.0,
            "rrg": 20.0, "lt": 30.0, "ht": 45.0, "st": 25.0}
LAND_DEF = {"inf": 5.0, "cav": 7.5, "ac": 12.0, "lart": 1.0, "art": 2.7,
            "rrg": 6.7, "lt": 30.0, "ht": 45.0, "st": 6.3}
LAND_HP = {"inf": 20, "cav": 25, "ac": 60, "lart": 10, "art": 20,
           "rrg": 60, "lt": 175, "ht": 260, "st": 40}


def _m(f: float) -> float:
    return 0.05 + 0.95 * f


def predict_mutual(a_unit: str, a_n: int, b_unit: str, b_n: int
                   ) -> tuple[float, float, str]:
    """Two engagements in order, each fought by whoever is still standing.

    Engagement 1 is an ordinary battle: A attacks with its ATTACK column, B
    answers with its DEFENCE column, both from the pre-round state -- which is
    exactly the one-sided model this project already has. Then the stacks are
    updated, and engagement 2 is the same battle with the roles swapped and the
    survivors fighting it.

    A stack destroyed in engagement 1 never fights engagement 2. That is what
    "Army A will always attack first" is worth, and it is worth a whole stack.
    """
    a_pool = float(a_n * LAND_HP[a_unit])
    b_pool = float(b_n * LAND_HP[b_unit])
    a_surv, b_surv = a_n, b_n

    def out(coef: float, surv: int, pool: float, maxhp: int) -> float:
        if surv <= 0 or pool <= 0:
            return 0.0
        return coef * effective_units(surv) * _m(pool / (surv * maxhp))

    # Engagement 1 -- A attacks.
    d_b = out(LAND_ATK[a_unit], a_surv, a_pool, LAND_HP[a_unit])
    d_a = out(LAND_DEF[b_unit], b_surv, b_pool, LAND_HP[b_unit])
    d_b, d_a = min(d_b, b_pool), min(d_a, a_pool)
    b_lost, a_lost = d_b, d_a
    per_b = b_pool / b_surv
    per_a = a_pool / a_surv
    b_surv -= int(d_b // per_b)
    a_surv -= int(d_a // per_a)
    b_pool -= d_b
    a_pool -= d_a

    if b_pool <= 1e-9 or b_surv <= 0:
        return a_lost, b_lost, "B destroyed in engagement 1 — it never fires"

    # Engagement 2 -- B attacks, with what is left of both stacks.
    d_a2 = out(LAND_ATK[b_unit], b_surv, b_pool, LAND_HP[b_unit])
    d_b2 = out(LAND_DEF[a_unit], a_surv, a_pool, LAND_HP[a_unit])
    a_lost += min(d_a2, a_pool)
    b_lost += min(d_b2, b_pool)
    return a_lost, b_lost, "both engagements fought"


def exp_mutual_law(p: Probe) -> None:
    """Confirm the two-engagement law, and test the page's own control.

    The first mutual sweep produced four cells and all four fall out of one
    rule to the printed decimal. Four cells fitted by a rule invented to
    explain them is not a measurement, so this predicts each reading BEFORE
    submitting it, across a roster whose attack and defence columns disagree by
    up to a factor of four and in both directions.

    The attacker is deliberately large so that nothing is censored: the first
    sweep lost four of its six rows because ten infantry are wiped outright by
    ten stormtroopers firing second, which is itself the finding but leaves no
    number to check.

    THE PAGE'S OWN CONTROL. It says the side letter matters ONLY when both
    stacks attack: "if a stack in one army is attacking a stack that is just
    defending, it will make no difference which side they are on." That is
    falsifiable in one pair of requests -- put the attacker on B and the
    defender on A, which no experiment here has ever done either.
    """
    print("\n  1. predicted BEFORE submitting, across both directions of the "
          "attack/defence gap\n")
    print(f"  {'A':>10} {'B':>10}{'A lost':>10}{'pred':>10}{'B lost':>10}"
          f"{'pred':>10}   note")
    agree = 0
    total = 0
    for b_unit in ("st", "rrg", "cav", "ac", "inf", "lart", "art", "lt"):
        a_n, b_n = 100, 10
        pa, pb, note = predict_mutual("inf", a_n, b_unit, b_n)
        ov = settings(1)
        ov.update(duel(1, "inf", a_n, b_unit, b_n))
        ov["B.1.target"] = "A.1"
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {'100 inf':>10} {b_n} {b_unit}: {e}"[:92]); continue
        d = dict(p.last_details)
        record("mutual_law", {"a_unit": "inf", "a_n": a_n, "b_unit": b_unit,
                              "b_n": b_n, "mutual": True,
                              "pred_a": pa, "pred_b": pb, "detail": d,
                              "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = (d.get("A.1.1") or {}); b = (d.get("B.1.1") or {})
        if a.get("lost") is None or b.get("lost") is None:
            print(f"  {'100 inf':>10} {b_n:>7} {b_unit}   no reading"); continue
        total += 1
        ok = abs(a["lost"] - pa) < 0.6 and abs(b["lost"] - pb) < 0.6
        agree += 1 if ok else 0
        print(f"  {'100 inf':>10} {f'{b_n} {b_unit}':>10}{a['lost']:>10.2f}"
              f"{pa:>10.2f}{b['lost']:>10.2f}{pb:>10.2f}   "
              f"{'' if ok else 'MISS — '}{note}")
    print(f"\n  {agree}/{total} cells predicted in advance")

    print("\n  2. the page's control: with only ONE side attacking, does the "
          "side letter matter?\n")
    print(f"  {'configuration':38}{'A lost':>10}{'B lost':>10}")
    reads = {}
    for label, a_t, b_t in (("A attacks (A=inf, B=st defends)", "B.1", "0"),
                            ("B attacks (A=inf defends, B=st)", "0", "A.1")):
        ov = settings(1)
        ov.update(duel(1, "inf", 10, "st", 10))
        ov["A.1.target"] = a_t
        ov["B.1.target"] = b_t
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {label:38} {e}"[:92]); continue
        d = dict(p.last_details)
        record("mutual_control", {"a_target": a_t, "b_target": b_t,
                                  "detail": d,
                                  "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = (d.get("A.1.1") or {}).get("lost")
        b = (d.get("B.1.1") or {}).get("lost")
        reads[label] = (a, b)
        f = lambda v: "-" if v is None else f"{v:.2f}"
        print(f"  {label:38}{f(a):>10}{f(b):>10}")
    if len(reads) == 2:
        (a1, b1), (a2, b2) = reads.values()
        if None not in (a1, b1, a2, b2):
            mirror = abs(a1 - b2) < 0.05 and abs(b1 - a2) < 0.05
            verdict = ("the two are exact mirrors — the side letter is inert "
                       "when only one side attacks, as the page says."
                       if mirror else
                       "NOT mirrors — the side letter matters even one-sided, "
                       "which the page denies.")
            print(f"\n  VERDICT: {verdict}")

    print("\n  3. what does a second round of a mutual battle look like?\n")
    print(f"  {'rounds':>7}{'A lost':>10}{'B lost':>10}{'A this round':>14}"
          f"{'B this round':>14}")
    pa_, pb_ = 0.0, 0.0
    for rounds in (1, 2, 3):
        ov = settings(rounds)
        ov.update(duel(1, "inf", 100, "ac", 10))
        ov["B.1.target"] = "A.1"
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {rounds:>7} {e}"[:92]); continue
        d = dict(p.last_details)
        record("mutual_rounds", {"a_unit": "inf", "a_n": 100, "b_unit": "ac",
                                 "b_n": 10, "mutual": True, "rounds": rounds,
                                 "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        a = (d.get("A.1.1") or {}).get("lost")
        b = (d.get("B.1.1") or {}).get("lost")
        if a is None or b is None:
            print(f"  {rounds:>7}   no reading"); continue
        print(f"  {rounds:>7}{a:>10.2f}{b:>10.2f}{a - pa_:>14.2f}"
              f"{b - pb_:>14.2f}")
        pa_, pb_ = a, b


def exp_mutual_order(p: Probe) -> None:
    """Two things the first sweep got wrong or did not ask.

    A BROKEN CONTROL, reported here rather than quietly fixed. exp_mutual_law
    set out to test the page's claim that the side letter is inert when only
    one side attacks, and compared

        A = inf attacking, B = st defending      vs
        A = inf DEFENDING, B = st attacking

    which are not mirrors of each other at all -- they are two different
    battles, one with infantry attacking and one with stormtroopers attacking.
    Naturally they disagreed, and the sweep printed "the side letter matters
    even one-sided, which the page denies." That verdict was a defect in the
    rig, exactly as §0 says to assume. The mirror keeps the ROLES and moves the
    stacks between armies:

        A = inf attacks   / B = st defends       vs
        A = st defends    / B = inf attacks

    THE ASYMMETRY ITSELF, which is the whole point of the page's claim and
    which the first sweep never measured. Same pair, mutual, in both side
    assignments. If A really strikes first the smaller stack should fare
    measurably better holding the A slot, and the difference should be
    predictable in advance from the two-engagement law rather than merely
    present.
    """
    def go(tag: str, a_unit: str, a_n: int, a_target: str,
           b_unit: str, b_n: int, b_target: str) -> dict | None:
        ov = settings(1)
        ov.update(duel(1, a_unit, a_n, b_unit, b_n))
        ov["A.1.target"] = a_target
        ov["B.1.target"] = b_target
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"    {tag}: {e}"[:92]); return None
        d = dict(p.last_details)
        record("mutual_order", {"tag": tag, "a_unit": a_unit, "a_n": a_n,
                                "b_unit": b_unit, "b_n": b_n,
                                "a_target": a_target, "b_target": b_target,
                                "detail": d,
                                "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        return d

    print("\n  1. the mirror, done properly: same battle, stacks swapped "
          "between armies\n")
    print(f"  {'configuration':40}{'inf lost':>10}{'st lost':>10}")
    got = {}
    for tag, au, an, at, bu, bn, bt in (
            ("A=inf attacks / B=st defends", "inf", 10, "B.1", "st", 10, "0"),
            ("A=st defends  / B=inf attacks", "st", 10, "0", "inf", 10, "A.1")):
        d = go(tag, au, an, at, bu, bn, bt)
        if not d:
            continue
        a = (d.get("A.1.1") or {}).get("lost")
        b = (d.get("B.1.1") or {}).get("lost")
        inf_lost, st_lost = (a, b) if au == "inf" else (b, a)
        got[tag] = (inf_lost, st_lost)
        f = lambda v: "-" if v is None else f"{v:.2f}"
        print(f"  {tag:40}{f(inf_lost):>10}{f(st_lost):>10}")
    if len(got) == 2:
        (i1, s1), (i2, s2) = got.values()
        if None not in (i1, s1, i2, s2):
            same = abs(i1 - i2) < 0.05 and abs(s1 - s2) < 0.05
            verdict = ("identical — the side letter IS inert when only one side "
                       "attacks, as the page says."
                       if same else
                       "they differ, so the side letter matters even one-sided.")
            print(f"\n  VERDICT: {verdict}")

    print("\n  2. the asymmetry: the same mutual battle, both ways round\n")
    print(f"  {'configuration':40}{'inf lost':>10}{'pred':>9}"
          f"{'st lost':>10}{'pred':>9}")
    for tag, au, an, bu, bn in (("100 inf on A, 10 st on B", "inf", 100, "st", 10),
                                ("10 st on A, 100 inf on B", "st", 10, "inf", 100)):
        pa, pb, _ = predict_mutual(au, an, bu, bn)
        d = go(tag, au, an, "B.1", bu, bn, "A.1")
        if not d:
            continue
        a = (d.get("A.1.1") or {}).get("lost")
        b = (d.get("B.1.1") or {}).get("lost")
        inf_lost, st_lost = (a, b) if au == "inf" else (b, a)
        p_inf, p_st = (pa, pb) if au == "inf" else (pb, pa)
        f = lambda v: "-" if v is None else f"{v:.2f}"
        print(f"  {tag:40}{f(inf_lost):>10}{p_inf:>9.2f}"
              f"{f(st_lost):>10}{p_st:>9.2f}")
    print("\n  Whichever stack holds the A slot fires into an undamaged enemy "
          "and is\n  answered by a damaged one. That is the entire content of "
          "\"A attacks first\".")


def exp_real_army(p: Probe) -> None:
    """A real battle, read off a player's screen, against the live site.

    Everything measured so far has been a configuration this rig invented to
    isolate one law. This is the opposite: two armies as a player actually has
    them, mixed types at awkward HP, a hero, and a fortress. It is the only
    kind of test that catches a law that is individually right and wrongly
    combined.

    ATTACKER   35 infantry   453.6 / 700.0
               6 armoured cars 318.1 / 360.0
               17 cavalry    378.1 / 425.0
    DEFENDER   12 armoured cars 677.5 / 720.0
               Orhan "Kangal" Demir, 83.1 / 90.0
               level 4 fortress, full

    Every one of those maxima -- 700, 360, 425, 720, and the hero's 90 -- is
    what this project measured from scratch, and all five match the game's own
    display exactly.

    HP HERE IS THE ROW TOTAL. The site's field carries 1375.1 against a count
    of 75, which cannot be per unit when an infantryman caps at 20, and its
    tooltip says "hit points of this unit TYPE". The game shows the same
    totals. So the figures go in exactly as read.
    """
    # Corrected by the player: the fortress is level 3, not 4. That matters
    # twice over -- it is 150 HP rather than 200, and its damage reduction is
    # 0.15 x (150/50 + 1) = 60% rather than 75%, which is far closer to the
    # 62% their own in-game panel reads.
    FORT_LVL = "4"
    FORT_HP = "5"      # the game shows 5 / 50 — the TOP-BAND bar
    ATK = [("inf", 35, "453.6"), ("ac", 6, "318.1"), ("cav", 17, "378.1")]
    DEF = [("ac", 12, "677.5")]
    abb, lvl, hhp = HERO_FIELDS          # the hero is on the DEFENDING side

    def build(rounds, hero_level):
        ov = settings(rounds)
        ov.update(duel(1, "inf", 35, "ac", 12))       # blanks rows 2-15 both sides
        for i, (u, n, hp) in enumerate(ATK, start=1):
            ov[f"A.1.{i}.unit"] = u
            ov[f"A.1.{i}.count"] = str(n)
            ov[f"A.1.{i}.hp"] = hp
        for i, (u, n, hp) in enumerate(DEF, start=1):
            ov[f"B.1.{i}.unit"] = u
            ov[f"B.1.{i}.count"] = str(n)
            ov[f"B.1.{i}.hp"] = hp
        ov.update({abb: "kangal", lvl: str(hero_level), hhp: "83.1"})
        ov.update({"B.1.bldg.1.abb": "fortress", "B.1.bldg.1.lvl": FORT_LVL,
                   "B.1.bldg.1.hp": FORT_HP})
        return ov

    fields = HERO_FIELDS + ("B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp") \
        + composite_fields("A", 1, 3) + composite_fields("B", 1, 1)

    # The hero badge reads a star and a 9; the "Level 1" beside every unit is
    # the TECH level. Both readings are submitted rather than guessed between.
    for hero_level, ladder in ((9, (1, 3, 100)), (1, (1, 100))):
        for rounds in ladder:
            ov = build(rounds, hero_level)
            try:
                p.submit(ov, create=fields)
            except (BareFormReturned, ValueError) as e:
                print(f"  hero lv{hero_level}, {rounds} round(s): {e}"[:96])
                continue
            d = dict(p.last_details)
            record("real_army",
                   {"hero_level": hero_level, "rounds": rounds,
                    "attacker": ATK, "defender": DEF, "fortress": f"lvl{FORT_LVL} hp{FORT_HP}",
                    "detail": d, "summary": dict(p.last_summary)},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            print(f"\n  === Kangal level {hero_level}, {rounds} round(s)")
            for slot in sorted(d):
                v = d[slot] or {}
                extra = ""
                if v.get("dr_before") is not None:
                    extra = (f"   fortress DR {v.get('dr_before')}% -> "
                             f"{v.get('dr_after')}%")
                print(f"    {slot:16} lost {str(v.get('lost')):>9}"
                      f"  ({v.get('pct')}%)  died {v.get('died')}{extra}")
            for stack, s in (p.last_summary or {}).items():
                print(f"    {stack} summary: {s.get('hp_lost')} HP lost, "
                      f"{s.get('hours')} h to repair, ${s.get('cash')}")


def exp_fortress_hp_scale(p: Probe) -> None:
    """What does the site's fortress HP field actually count?

    A player reports a LEVEL 4 fortress reading "5 / 50" in game. This project
    measured the site's level-4 fortress as a 200 HP pool -- 50 per level -- so
    the two are not on the same scale and "5" could mean 5 of 200 (2.5%) or the
    10% the player's own bar shows. Those are different fortresses: the damage
    reduction is 0.15 x (hp/50 + 1), so 5 of 200 gives 16.5% and 20 of 200
    gives 21%.

    The site prints its own damage reduction on the building row, so it can
    simply be asked. Three settings, one round each, with everything else held
    where the real battle has it.
    """
    ATK = [("inf", 35, "453.6"), ("ac", 6, "318.1"), ("cav", 17, "378.1")]
    abb, lvl, hhp = HERO_FIELDS
    print(f"\n  {'hp field':>10}{'fort lost':>11}{'of pool':>9}"
          f"{'DR before':>11}{'DR after':>10}   what the field meant")
    for hp_field in ("100%", "10%", "5", "50"):
        ov = settings(1)
        ov.update(duel(1, "inf", 35, "ac", 12))
        for i, (u, n, hp) in enumerate(ATK, start=1):
            ov[f"A.1.{i}.unit"] = u
            ov[f"A.1.{i}.count"] = str(n)
            ov[f"A.1.{i}.hp"] = hp
        ov["B.1.1.unit"] = "ac"
        ov["B.1.1.count"] = "12"
        ov["B.1.1.hp"] = "677.5"
        ov.update({abb: "kangal", lvl: "9", hhp: "83.1"})
        ov.update({"B.1.bldg.1.abb": "fortress", "B.1.bldg.1.lvl": "4",
                   "B.1.bldg.1.hp": hp_field})
        fields = HERO_FIELDS + ("B.1.bldg.1.abb", "B.1.bldg.1.lvl",
                                "B.1.bldg.1.hp") \
            + composite_fields("A", 1, 3) + composite_fields("B", 1, 1)
        try:
            p.submit(ov, create=fields)
        except (BareFormReturned, ValueError) as e:
            print(f"  {hp_field:>10}  refused: {e}"[:96])
            continue
        d = dict(p.last_details)
        record("fortress_hp_scale",
               {"level": 4, "hp_field": hp_field, "detail": d,
                "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.bldg.1") or {}
        pool = b.get("pool")
        dr0, dr1 = b.get("dr_before"), b.get("dr_after")
        # DR = 0.15 x (hp/50 + 1)  ->  hp = 50 x (DR/0.15 - 1)
        implied = (50.0 * ((dr0 or 0) / 100.0 / 0.15 - 1.0)) if dr0 else None
        meaning = ("" if implied is None
                   else f"pool {pool}, so the field set {implied:.1f} HP")
        print(f"  {hp_field:>10}{str(b.get('lost')):>11}{str(pool):>9}"
              f"{str(dr0):>11}{str(dr1):>10}   {meaning}")


def read_back(p: Probe) -> dict[str, str]:
    """The FORM as the server returned it, which with updateCounts on carries
    the POST-BATTLE counts and HP rather than an echo of what was sent."""
    fs = FormScraper()
    fs.feed(p.last_response)
    return dict(fs.fields)


def exp_update_counts(p: Probe) -> None:
    """Read the server's OWN survivor counts, for the first time.

    settings() has sent updateCounts="" since the first request, so every one
    of the 2,585 readings on file reports HP LOST and nothing else. Survivors,
    remaining pool and deaths have always been INFERRED here -- deaths from
    floor(damage / per-unit HP), survivors from count minus deaths -- and that
    inference is what every multi-round result is built on. The switch that
    would check it has been sitting in the form the whole time.

    With it on the server rewrites the form it returns, so A.1.1.count comes
    back as what SURVIVED and A.1.1.hp as what they have left. That is a direct
    reading of three quantities this project has only ever computed.

    IT IS ALSO THE OBVIOUS DIAGNOSTIC for the one known wrong answer in the
    model. Against a real army the engine is exact at round 1 and drifts to
    about 4% by round 10, seeded by roughly half a hit point in the DEFENDER'S
    ROUND-TWO output. Output depends on survivors and on their HP; both are
    now readable per round instead of inferred, so the round where the two
    diverge can be pointed at rather than reasoned about.
    """
    print("\n  1. a battle whose every number this project already knows\n")
    print("     10 infantry vs 10 infantry, one round. Measured long ago:")
    print("     A loses 50.0 with 2 dead, B loses 40.0 with 2 dead.\n")
    ov = settings(1, update_counts=True)
    ov.update(duel(1, "inf", 10, "inf", 10))
    try:
        p.submit(ov)
    except (BareFormReturned, ValueError) as e:
        print(f"  refused: {e}"[:96])
        return
    back = read_back(p)
    d = dict(p.last_details)
    record("update_counts", {"label": "10 inf v 10 inf", "rounds": 1,
                             "detail": d, "form_back": back,
                             "summary": dict(p.last_summary)},
           {k: (v or {}).get("lost") for k, v in d.items()})
    print(f"  {'slot':10}{'lost':>8}{'inferred left':>15}{'server says':>13}"
          f"{'inferred HP':>13}{'server HP':>11}")
    for slot, n0, pool0 in (("A.1.1", 10, 200.0), ("B.1.1", 10, 200.0)):
        det = d.get(slot) or {}
        lost = det.get("lost")
        died = det.get("died")
        left_inf = None if died is None else n0 - int(died)
        hp_inf = None if lost is None else pool0 - lost
        print(f"  {slot:10}{str(lost):>8}{str(left_inf):>15}"
              f"{back.get(slot + '.count', '-'):>13}"
              f"{('-' if hp_inf is None else f'{hp_inf:.2f}'):>13}"
              f"{back.get(slot + '.hp', '-'):>11}")

    print("\n  2. the real army, round by round — where do the two diverge?\n")
    ATK = [("inf", 35, "453.6"), ("ac", 6, "318.1"), ("cav", 17, "378.1")]
    abb, lvl, hhp = HERO_FIELDS
    fields = HERO_FIELDS + ("B.1.bldg.1.abb", "B.1.bldg.1.lvl",
                            "B.1.bldg.1.hp") \
        + composite_fields("A", 1, 3) + composite_fields("B", 1, 1)
    print(f"  {'rnd':>4} | {'inf ct':>7}{'inf hp':>9} | {'ac ct':>6}{'ac hp':>9}"
          f" | {'cav ct':>7}{'cav hp':>9} | {'def ct':>7}{'def hp':>9}"
          f"{'hero hp':>9}{'fort hp':>9}")
    for rounds in (1, 2, 3, 4, 5):
        ov = settings(rounds, update_counts=True)
        ov.update(duel(1, "inf", 35, "ac", 12))
        for i, (u, n, hp) in enumerate(ATK, start=1):
            ov[f"A.1.{i}.unit"] = u
            ov[f"A.1.{i}.count"] = str(n)
            ov[f"A.1.{i}.hp"] = hp
        ov["B.1.1.unit"] = "ac"
        ov["B.1.1.count"] = "12"
        ov["B.1.1.hp"] = "677.5"
        ov.update({abb: "kangal", lvl: "9", hhp: "83.1"})
        ov.update({"B.1.bldg.1.abb": "fortress", "B.1.bldg.1.lvl": "4",
                   "B.1.bldg.1.hp": "5"})
        try:
            p.submit(ov, create=fields)
        except (BareFormReturned, ValueError) as e:
            print(f"  {rounds:>4} | refused: {e}"[:96])
            continue
        back = read_back(p)
        d = dict(p.last_details)
        record("update_counts_army",
               {"rounds": rounds, "hero_level": 9, "fortress": "lvl4 hp5",
                "detail": d, "form_back": back,
                "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        g = lambda k: back.get(k, "-")
        print(f"  {rounds:>4} | {g('A.1.1.count'):>7}{g('A.1.1.hp'):>9}"
              f" | {g('A.1.2.count'):>6}{g('A.1.2.hp'):>9}"
              f" | {g('A.1.3.count'):>7}{g('A.1.3.hp'):>9}"
              f" | {g('B.1.1.count'):>7}{g('B.1.1.hp'):>9}"
              f"{g('B.1.hero.hp'):>9}{g('B.1.bldg.1.hp'):>9}")


def stack_fields(stack: int) -> tuple[str, ...]:
    """Every field duel() SETS for one pair, so submit() can synthesise them.

    Blanking a field the form does not have is harmless -- submit() drops it --
    but SETTING one silently does nothing, which is how the fortress sweep lost
    six requests a run. Second-stack fields do not exist until the page's own
    JS clones them, so they all have to be named.
    """
    out: list[str] = []
    for side in ("A", "B"):
        out += [f"{side}.{stack}.target", f"{side}.{stack}.terrain",
                f"{side}.{stack}.position", f"{side}.{stack}.trench",
                f"{side}.{stack}.1.unit", f"{side}.{stack}.1.count",
                f"{side}.{stack}.1.hp"]
    return tuple(out)


def exp_multi_stack(p: Probe) -> None:
    """Two stacks a side -- 2 readings out of 2,585, and three documented laws.

    bytro.js allows a hundred stacks per army and this rig has sent two, once,
    for the bombardment friendly-fire cell. Everything else in the record is one
    stack against one stack, which is not how anybody actually fights.

    The help page documents three things about it and leaves a fourth blank:

        "Only a single stack at a given position should be assigned the
         buildings. All other land stacks at the same position as the stack
         assigned buildings (except aircraft transport) will inherit the same
         set of buildings ... If there is a stack at or near the same position
         that shouldn't receive the fortification bonus ... you can give it
         ... position 1, 2, or 3 km. That way they will still be within melee
         range for the battle, but won't recieve the fort protection."

    So: INHERITANCE by position, an EXCLUSION for aircraft transports, and an
    escape hatch at 1-3 km. The fourth section is headed "Auto-targeting
    behavior" and has no text under it at all -- the author meant to write it
    and did not -- so what a stack does when nothing is aimed at it is
    undocumented as well as unmeasured.

    THE MEASUREMENT IS A DIFFERENCE, not a reading. A fortress cuts incoming
    damage, so "did stack two inherit it?" is answered by running the same
    battle with and without the fortress and seeing whether B.2's losses move.
    Both pairs are melee infantry at the same position, isolated by target.
    """
    FORT = ("B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp")
    CREATE = stack_fields(2) + FORT

    def run(tag: str, *, fortress: bool, b2_pos: int = 0,
            b2_unit: str = "inf") -> dict:
        ov = settings(1)
        ov.update(duel(1, "inf", 10, "inf", 10))
        ov.update(duel(2, "inf", 10, b2_unit, 10))
        ov["B.2.position"] = str(b2_pos)
        if fortress:
            ov.update({FORT[0]: "fortress", FORT[1]: "5", FORT[2]: "100%"})
        try:
            p.submit(ov, create=CREATE)
        except (BareFormReturned, ValueError) as e:
            print(f"    {tag}: {e}"[:96])
            return {}
        d = dict(p.last_details)
        record("multi_stack", {"tag": tag, "fortress": fortress,
                               "b2_pos": b2_pos, "b2_unit": b2_unit,
                               "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        return d

    print("\n  1. does a second stack inherit the first stack's fortress?\n")
    print("     Two pairs of 10 infantry, both at 0 km, isolated by target.")
    print("     The fortress sits on B.1 only. If B.2's losses fall when it is")
    print("     added, B.2 inherited it.\n")
    print(f"  {'configuration':38}{'B.1 lost':>10}{'B.2 lost':>10}   verdict")
    base = run("no fortress", fortress=False)
    b1_0 = (base.get("B.1.1") or {}).get("lost")
    b2_0 = (base.get("B.2.1") or {}).get("lost")
    f = lambda v: "-" if v is None else f"{v:.2f}"
    print(f"  {'no fortress at all':38}{f(b1_0):>10}{f(b2_0):>10}   baseline")

    for tag, kw, expect in (
            ("fortress on B.1, B.2 at 0 km", dict(fortress=True), "inherits"),
            ("fortress on B.1, B.2 at 1 km", dict(fortress=True, b2_pos=1),
             "the page's escape hatch")):
        d = run(tag, **kw)
        b1 = (d.get("B.1.1") or {}).get("lost")
        b2 = (d.get("B.2.1") or {}).get("lost")
        note = ""
        if b2 is not None and b2_0 is not None:
            note = ("PROTECTED — it inherited the fortress"
                    if b2 < b2_0 - 0.05 else "NOT protected")
        print(f"  {tag:38}{f(b1):>10}{f(b2):>10}   {note}")

    print("\n  2. the exception: an aircraft transport at the same position\n")
    print(f"  {'configuration':38}{'B.2 lost':>10}   verdict")
    conv_base = run("convoy, no fortress", fortress=False, b2_unit="convoy")
    cb = (conv_base.get("B.2.1") or {}).get("lost")
    print(f"  {'convoy at 0 km, no fortress':38}{f(cb):>10}   baseline")
    conv_fort = run("convoy, fortress", fortress=True, b2_unit="convoy")
    cf = (conv_fort.get("B.2.1") or {}).get("lost")
    note = ""
    if cf is not None and cb is not None:
        note = ("PROTECTED — the page's exception does not hold"
                if cf < cb - 0.05 else "NOT protected — the exception holds")
    print(f"  {'convoy at 0 km, fortress on B.1':38}{f(cf):>10}   {note}")

    print("\n  3. the blank section: what happens to a stack nobody targets?\n")
    ov = settings(1)
    ov.update(duel(1, "inf", 10, "inf", 10))
    ov.update(duel(2, "inf", 10, "inf", 10))
    ov["A.2.target"] = "0"          # A.2 attacks nobody
    ov["B.2.target"] = "0"          # and nobody attacks B.2
    try:
        p.submit(ov, create=CREATE)
        d = dict(p.last_details)
        record("multi_stack_idle", {"tag": "A.2 and B.2 both defending",
                                    "detail": d,
                                    "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        print("     A.1 attacks B.1; A.2 and B.2 are both set to Defend.\n")
        for slot in sorted(d):
            v = d[slot] or {}
            print(f"     {slot:10} lost {str(v.get('lost')):>8}  ({v.get('pct')}%)")
    except (BareFormReturned, ValueError) as e:
        print(f"     refused: {e}"[:96])

    print("\n  4. two stacks concentrating on one defender\n")
    ov = settings(1)
    ov.update(duel(1, "inf", 10, "inf", 10))
    ov.update(duel(2, "inf", 10, "inf", 10))
    ov["A.2.target"] = "B.1"        # both attack the SAME stack
    ov["B.2.1.count"] = ""          # and B.2 is not fielded at all
    ov["B.2.1.hp"] = ""
    try:
        p.submit(ov, create=CREATE)
        d = dict(p.last_details)
        record("multi_stack_focus", {"tag": "A.1 and A.2 both target B.1",
                                     "detail": d,
                                     "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        print("     A.1 and A.2 both target B.1. One defender, two attackers.\n")
        for slot in sorted(d):
            v = d[slot] or {}
            print(f"     {slot:10} lost {str(v.get('lost')):>8}  ({v.get('pct')}%)")
        print("\n     A single 10-inf attacker takes 50.00 from a 10-inf "
              "defender.\n     Does the defender answer each attacker in full, "
              "or split its fire?")
    except (BareFormReturned, ValueError) as e:
        print(f"     refused: {e}"[:96])


def exp_bughunt(p: Probe) -> None:
    """One sweep aimed at the engine, not at the game.

    Every other experiment here asks the site a question. This one asks the
    MODEL a question and uses the site as the answer key, so its design rule is
    different: pick the cells where the engine is most likely to be wrong, not
    the cells that isolate a law.

    WHERE IT IS MOST LIKELY TO BE WRONG is readable straight off results.jsonl.
    Count the rounds column by experiment and almost every sweep in this project
    is one round: trenches, buildings, allocation, saturation, terrain, heroes,
    all measured at maxRounds=1. Multi-round exists only for bare stacks, one
    bombardment ladder, and the real-army run. So any law that is correct for a
    single round and applied WRONGLY on the second is invisible in the record,
    and that is exactly the class of defect the real-army run turned up six of.

    THREE PRONGS.

    A. THE FORTRESS AFTER THE GARRISON DIES. The suite already prints a
       discrepancy it could not explain: fought to the end, the site destroys
       the fortress outright and this engine leaves it at 97-100%. The obvious
       suspect is the stop condition -- the engine ends the battle when the
       defending side's pool is gone, and a fortress with nobody left to defend
       it may still be a target. Six ht against five infantry behind a level-5
       fortress puts the garrison in the ground at round 3 with 90 HP of
       fortress still standing, then asks for 5, 8 and 100 rounds. If the site
       keeps grinding, the engine stops one condition too early.

    B. A TRENCH OVER MULTIPLE ROUNDS. The trench is measured at two dozen
       levels and every reading is a single round. A trench changes both the
       pool and the output, and a factor applied to the opening state instead
       of to the survivors is the precise defect that was found twice already
       (allocation weights, and the hero's own output).

    C. A BUILDING GROUND DOWN WITH THE GARRISON INTACT. Prong A confounds the
       building with the deaths. Ten ht against forty infantry keeps everyone
       alive while the fortress falls, so building damage per round is read on
       its own.

    THE PREDICTIONS ARE WRITTEN DOWN FIRST. web/engine.js is run over every
    cell before the first request goes out and its answers are recorded into
    the meta of each row. A prediction made after the fact is not a prediction,
    and this project has caught itself reading a law off the data it was meant
    to test more than once.
    """
    import json as _json
    import os as _os
    base = _os.environ.get("BUGHUNT_DIR", ".")
    cells = _json.load(open(_os.path.join(base, "bughunt_cells.json")))
    pred = _json.load(open(_os.path.join(base, "bughunt_pred.json")))
    # A PREDICTION OLDER THAN THE ENGINE IS NOT A PREDICTION. bughunt_pred.json
    # is derived from web/engine.js; edit the engine and the file on disk
    # becomes a record of what the engine used to say. Submitting against it
    # would compare the site to a model that no longer exists and report the
    # difference as a finding.
    engine = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                           "web", "engine.js")
    pred_path = _os.path.join(base, "bughunt_pred.json")
    if _os.path.exists(engine) and \
            _os.path.getmtime(pred_path) < _os.path.getmtime(engine):
        print("  bughunt_pred.json is older than web/engine.js — re-run "
              "scripts/bughunt_predict.mjs. Nothing submitted.", file=sys.stderr)
        return

    missing = [c["id"] for c in cells if c["id"] not in pred]
    if missing:
        # Refuse rather than submit blind. A cell with no prediction cannot
        # produce a finding -- whatever comes back will look like a result and
        # be compared against nothing.
        print(f"  no prediction for {', '.join(missing)} — run predict.mjs "
              f"first. Nothing submitted.", file=sys.stderr)
        return

    rows: list[tuple[str, str, int, dict[str, float], dict[str, Any]]] = []
    for c in cells:
        ov = settings(str(c["rounds"]))
        ov.update(duel(1, c["atk"]["unit"], c["atk"]["count"],
                       c["def"]["unit"], c["def"]["count"],
                       trench=int(c.get("defTrench", 0)),
                       atk_trench=int(c.get("atkTrench", 0))))
        fields: tuple[str, ...] = ()
        if c.get("fortress"):
            ov.update({"B.1.bldg.1.abb": "fortress",
                       "B.1.bldg.1.lvl": str(c["fortress"]),
                       "B.1.bldg.1.hp": "100%"})
            fields = ("B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp")
        try:
            p.submit(ov, create=fields)
        except (BareFormReturned, ValueError) as e:
            print(f"  {c['id']}: {e}"[:100])
            continue
        d = dict(p.last_details)
        record("bughunt",
               {"cell": c, "rounds": c["rounds"], "predicted": pred[c["id"]],
                "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        rows.append((c["id"], c["prong"], c["rounds"], pred[c["id"]], d))
        print(f"  {c['id']} sent")

    def got(d: dict[str, Any], slot: str, key: str = "lost") -> float | None:
        v = d.get(slot) or {}
        return v.get(key)

    print("\n  cell prong                      rd   attacker lost      "
          "defender lost       fortress lost")
    print("  " + "-" * 94)
    findings: list[str] = []
    for cid, prong, rounds, pr, d in rows:
        line = [f"  {cid:4} {prong:26} {rounds:4}"]
        for label, slot, pkey in (("A", "A.1.1", "atk_lost"),
                                  ("B", "B.1.1", "def_lost"),
                                  ("bldg", "B.1.bldg.1", "bldg_lost")):
            g = got(d, slot)
            e = pr.get(pkey)
            if g is None and e is None:
                line.append(f"{'—':>19}")
                continue
            if g is None or e is None:
                line.append(f"{('site ' + str(g)) if e is None else ('engine ' + str(e))!s:>19}")
                findings.append(f"{cid} {label}: one side has a number and the "
                                f"other does not (site {g}, engine {e})")
                continue
            # A percentage gap on a big number and an absolute gap on a small
            # one; either alone calls something wrong that is not.
            off = abs(g - e)
            rel = off / max(abs(g), 1e-9)
            mark = " " if (off <= 0.05 or rel <= 0.005) else "*"
            line.append(f"{g:9.2f}/{e:8.2f}{mark}")
            if mark == "*":
                findings.append(f"{cid} {label}: site {g:.2f}, engine {e:.2f} "
                                f"({(e - g) / max(abs(g), 1e-9) * 100:+.1f}%)")
        print("".join(line))

    print("\n  (site / engine; * = the two disagree by more than 0.05 HP and 0.5%)")
    if findings:
        print(f"\n  {len(findings)} DISAGREEMENT(S) — each is a defect report "
              f"against the engine until shown otherwise:")
        for f in findings:
            print(f"    {f}")
    else:
        print("\n  No disagreement anywhere. That is a weaker result than it "
              "looks: it means these cells did not reach a defect, not that "
              "there is none.")


def exp_fort_drift(p: Probe) -> None:
    """The one number in this project the engine has never reproduced.

    Fought to the end, the site destroys the real army's level-4 fortress --
    200.0, "destroyed" -- and this engine stops at 193.83 with 6.17 HP of it
    standing. It has been printed as an unreproduced measurement for as long as
    the real-army rows have been on file.

    WHAT IS ALREADY KNOWN, ALL OF IT FROM THE ARCHIVE AND FOR FREE.

      * It is not the building-damage rate. The engine's cumulative fortress
        total matches the site at every round the site has been asked for:
        38.06/38.1, 71.02/71.0, 99.00/99.0, 141.68/141.7, 157.78/157.8,
        171.35/171.4, 183.12/183.1. Seven rounds, exact.
      * It is not the stop condition. exp_bughunt settled that directly: a
        fortress whose garrison is dead takes no further damage, at 5 rounds,
        8 or 100.
      * It is not the smaller fortresses. The same army against a pool of 150
        or 155 finishes the building and the engine agrees exactly. Only the
        full 200 is short, and only by 6.17.
      * The DEFENDER is where the two actually part company, and it starts at
        round 7: site 631.68 against engine 629.99, then 707.66 against 701.95.
        The engine under-damages the defender late, which leaves the attacker
        stronger for longer in the site's battle than in this one -- and a
        stronger attacker is exactly what the last few HP of fortress need.

    So the fortress is not the defect. It is the READOUT of a defect, and the
    defect is in the last three rounds of the defender's arithmetic. Rounds 1-6
    are exact and round 7 is not.

    WHAT THIS SWEEP ADDS. updateCounts rewrites the returned form with the
    site's own survivor counts and remaining HP, which is how the previous two
    defects in this area were found. That ladder exists on file for the 155-HP
    fortress at rounds 1-5 -- the stretch where nothing is wrong. Here it runs
    against the 200-HP fortress at rounds 1-9, over the rounds that actually
    diverge, so the first quantity to go wrong can be named: an attacker row's
    survivors, its HP, the defender's, or the hero's.

    Two controls come with it, because the hero is the obvious suspect and a
    suspect deserves a test rather than a story:

      * The same battle with NO HERO. The engine says that one destroys the
        fortress in 7 rounds -- a weaker defender lets the attacker live longer
        and hit the building harder. If the site agrees there and disagrees
        only when the hero is present, the hero's late-battle contribution is
        where to look.
      * exp_bughunt's prong A with a hero ADDED. That configuration is measured
        and its fortress survives; adding a hero must not change that, and if
        it does, the stop condition finding needs revisiting.

    And one methodological control: round 9 submitted with updateCounts OFF.
    Everything here is read through a switch this project has used exactly
    once. If the two disagree, the ladder is measuring the switch.
    """
    import json as _json
    import os as _os
    base = _os.environ.get("BUGHUNT_DIR", ".")
    engine = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                           "web", "engine.js")
    pred_path = _os.path.join(base, "fortdrift_pred.json")
    if not _os.path.exists(pred_path):
        print("  no fortdrift_pred.json — run scripts/fortdrift_predict.mjs "
              "first. Nothing submitted.", file=sys.stderr)
        return
    if _os.path.exists(engine) and \
            _os.path.getmtime(pred_path) < _os.path.getmtime(engine):
        print("  fortdrift_pred.json is older than web/engine.js — re-run "
              "scripts/fortdrift_predict.mjs. Nothing submitted.", file=sys.stderr)
        return
    pred = _json.load(open(pred_path))

    ATK = [("inf", 35, "453.6"), ("ac", 6, "318.1"), ("cav", 17, "378.1")]
    abb, lvl, hhp = HERO_FIELDS
    hero_fields = HERO_FIELDS
    bldg_fields = ("B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp")
    fields = hero_fields + bldg_fields \
        + composite_fields("A", 1, 3) + composite_fields("B", 1, 1)

    def army(rounds: Any, update: bool, hero: bool) -> dict[str, str]:
        ov = settings(rounds, update_counts=update)
        ov.update(duel(1, "inf", 35, "ac", 12))
        for i, (u, n, hp) in enumerate(ATK, start=1):
            ov[f"A.1.{i}.unit"] = u
            ov[f"A.1.{i}.count"] = str(n)
            ov[f"A.1.{i}.hp"] = hp
        ov["B.1.1.unit"] = "ac"
        ov["B.1.1.count"] = "12"
        ov["B.1.1.hp"] = "677.5"
        if hero:
            ov.update({abb: "kangal", lvl: "9", hhp: "83.1"})
        ov.update({"B.1.bldg.1.abb": "fortress", "B.1.bldg.1.lvl": "4",
                   "B.1.bldg.1.hp": "100%"})
        return ov

    print("\n  1. the real army against a FULL level-4 fortress, round by round")
    print("     site above, engine below; * marks the first quantity to part company\n")
    print(f"  {'rnd':>4} | {'inf ct':>7}{'inf hp':>9} | {'ac ct':>6}{'ac hp':>9}"
          f" | {'cav ct':>7}{'cav hp':>9} | {'def ct':>7}{'def hp':>9}"
          f"{'hero hp':>9}{'fort hp':>9}")
    for rounds in range(1, 10):
        try:
            p.submit(army(rounds, True, True), create=fields)
        except (BareFormReturned, ValueError) as e:
            print(f"  {rounds:>4} | refused: {e}"[:96])
            continue
        back = read_back(p)
        d = dict(p.last_details)
        record("fort_drift",
               {"rounds": rounds, "hero_level": 9, "fortress": "lvl4 100%",
                "update_counts": True, "predicted": pred.get(f"r{rounds}"),
                "detail": d, "form_back": back,
                "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        g = lambda k: back.get(k, "-")
        # The fortress comes back as a LEVEL plus a top-band HP, not a pool.
        # pool = (level - 1) x 50 + top-band, measured in fortress_hp_scale.
        try:
            fort = (float(g("B.1.bldg.1.lvl")) - 1) * 50 + float(g("B.1.bldg.1.hp"))
        except (TypeError, ValueError):
            fort = None
        print(f"  {rounds:>4} | {g('A.1.1.count'):>7}{g('A.1.1.hp'):>9}"
              f" | {g('A.1.2.count'):>6}{g('A.1.2.hp'):>9}"
              f" | {g('A.1.3.count'):>7}{g('A.1.3.hp'):>9}"
              f" | {g('B.1.1.count'):>7}{g('B.1.1.hp'):>9}"
              f"{g('B.1.hero.hp'):>9}"
              f"{('-' if fort is None else f'{fort:.2f}'):>9}")
        e = pred.get(f"r{rounds}") or {}
        if e:
            print(f"  {'eng':>4} | {e['inf']['alive']:>7}{e['inf']['hpLeft']:>9}"
                  f" | {e['ac']['alive']:>6}{e['ac']['hpLeft']:>9}"
                  f" | {e['cav']['alive']:>7}{e['cav']['hpLeft']:>9}"
                  f" | {e['def']['alive']:>7}{e['def']['hpLeft']:>9}"
                  f"{e['hero_hp']:>9}{e['fort_hp']:>9}")

    print("\n  2. round 9 with updateCounts OFF — is the switch changing the battle?")
    try:
        p.submit(army(9, False, True), create=fields)
        d = dict(p.last_details)
        record("fort_drift",
               {"rounds": 9, "hero_level": 9, "fortress": "lvl4 100%",
                "update_counts": False, "predicted": pred.get("r9"),
                "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.bldg.1") or {}
        print(f"     fortress lost {b.get('lost')}, destroyed={b.get('destroyed')}; "
              f"defender {(d.get('B.1.1') or {}).get('lost')}")
    except (BareFormReturned, ValueError) as e:
        print(f"     refused: {e}"[:96])

    print("\n  3. THE SAME BATTLE WITH NO HERO, fought out")
    print(f"     engine says {pred['no_hero_100']}")
    try:
        p.submit(army(100, False, False), create=bldg_fields
                 + composite_fields("A", 1, 3) + composite_fields("B", 1, 1))
        d = dict(p.last_details)
        record("fort_drift",
               {"rounds": 100, "hero_level": None, "fortress": "lvl4 100%",
                "update_counts": False, "predicted": pred["no_hero_100"],
                "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.bldg.1") or {}
        print(f"     site: fortress lost {b.get('lost')}, "
              f"destroyed={b.get('destroyed')}; defender "
              f"{(d.get('B.1.1') or {}).get('lost')}")
        if "B.1.hero" in d:
            print("     ! a hero row came back on a request that set no hero — "
                  "the no-hero control did NOT control for the hero.",
                  file=sys.stderr)
    except (BareFormReturned, ValueError) as e:
        print(f"     refused: {e}"[:96])

    print("\n  4. exp_bughunt's prong A with a hero added, fought out")
    print(f"     engine says {pred['prongA_with_hero_100']}")
    print("     its fortress survived at 159.8 of 250 with no hero; a hero "
          "must not change that")
    try:
        ov = settings(100)
        ov.update(duel(1, "ht", 6, "inf", 5))
        ov.update({abb: "kangal", lvl: "9", hhp: "100%"})
        ov.update({"B.1.bldg.1.abb": "fortress", "B.1.bldg.1.lvl": "5",
                   "B.1.bldg.1.hp": "100%"})
        p.submit(ov, create=hero_fields + bldg_fields)
        d = dict(p.last_details)
        record("fort_drift",
               {"rounds": 100, "hero_level": 9, "fortress": "lvl5 100%",
                "tag": "prongA_with_hero", "update_counts": False,
                "predicted": pred["prongA_with_hero_100"],
                "detail": d, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        b = d.get("B.1.bldg.1") or {}
        print(f"     site: fortress lost {b.get('lost')}, "
              f"destroyed={b.get('destroyed')}; defender "
              f"{(d.get('B.1.1') or {}).get('lost')}")
    except (BareFormReturned, ValueError) as e:
        print(f"     refused: {e}"[:96])


def exp_late_drift(p: Probe) -> None:
    """The residual exp_fort_drift left behind, and the one cheap way to split it.

    From round seven of the real-army battle this engine deals 2.2%, then 5.6%,
    then 8.3% less damage than the site -- on a state that matches the site's
    OWN readback exactly at the start of every one of those rounds. Same
    survivors, same remaining HP, same fortress, so the same damage reduction.
    It is in the output term and not in the state feeding it.

    Which is awkward, because both factors of the output term are measured to
    exhaustion. m(f) = 0.05 + 0.95f was swept at 100/75/50/25/10 per cent for
    five unit types on both sides -- fifty cells, every one exact -- so f down
    to 0.10 is covered and the residual sits at f around 0.4 to 0.55. E(n) has
    every rung from 1 to 113 measured. Neither is the suspect.

    FOUR PRONGS, AND THE FIRST IS WORTH THE OTHER THREE.

    G. IS THE SITE MEMORYLESS? Take the site's own round-6 and round-7 states
       out of the readback and submit them as FRESH ONE-ROUND BATTLES. If a
       one-round answer from a state equals the increment the multi-round
       battle showed from that same state, then a round is a pure function of
       the state at its start, the residual is reproducible in a single
       request, and it can be chased with cheap cells for as long as it takes.
       If it does NOT, the site carries something between rounds -- and no
       measurement in this archive could ever have seen it, because this
       archive is 2,600 single rounds.

       This engine is memoryless by construction, and its one-round answer
       from the round-6 state is its round-7 increment to three decimals. So
       the two hypotheses are cleanly separated by one request each.

    H. THE SINGLE-TYPE DEEP LADDER the gap named. Twenty heavy tanks against
       twenty: no fortress, no hero, no trench, one row a side, so E(n) and
       m(f) are the only two terms in the whole battle. Twelve rounds, neither
       side wiped, both ending on five units at f = 0.39. If the residual
       shows here it is in the core law. If it does not, the core law is clean
       over twelve rounds and the residual needs a mixture, a building or a
       hero -- which is a large narrowing bought cheaply.

    I and J. STRIP ONE INGREDIENT. I removes the fortress from the real army,
       J removes the hero. With H, every ingredient of the battle that shows
       the residual has been taken away once.

    Their round counts come from the engine's own fought= figure rather than
    from the real army's schedule: without the fortress the battle is over by
    round four, so asking for five, six and seven would buy three copies of
    one answer.
    """
    import json as _json
    import os as _os
    base = _os.environ.get("BUGHUNT_DIR", ".")
    engine = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                           "web", "engine.js")
    pred_path = _os.path.join(base, "latedrift_pred.json")
    if not _os.path.exists(pred_path):
        print("  no latedrift_pred.json — run scripts/latedrift_predict.mjs "
              "first. Nothing submitted.", file=sys.stderr)
        return
    if _os.path.exists(engine) and \
            _os.path.getmtime(pred_path) < _os.path.getmtime(engine):
        print("  latedrift_pred.json is older than web/engine.js — re-run "
              "scripts/latedrift_predict.mjs. Nothing submitted.", file=sys.stderr)
        return
    pred = _json.load(open(pred_path))

    abb, lvl, hhp = HERO_FIELDS
    bldg = ("B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp")
    full = HERO_FIELDS + bldg + composite_fields("A", 1, 3) \
        + composite_fields("B", 1, 1)

    # ---- G ---------------------------------------------------------------
    print("\n  G. the site's own mid-battle states, resubmitted as ONE round")
    print("     if a round is a pure function of the state it starts from,")
    print("     these reproduce the increments the long battle showed.\n")
    STATES = {
        "g6": {"inf": (11, "120.4"), "ac": (6, "145.8"), "cav": (7, "110.9"),
               "def": (4, "150.5"), "hero": "58.7", "fort": "42.2"},
        "g7": {"inf": (10, "103.8"), "ac": (6, "127.7"), "cav": (6, "95.0"),
               "def": (3, "77.5"), "hero": "51.4", "fort": "28.6"},
    }
    for key, st in STATES.items():
        ov = settings(1)
        ov.update(duel(1, "inf", st["inf"][0], "ac", st["def"][0]))
        for i, code in enumerate(("inf", "ac", "cav"), start=1):
            ov[f"A.1.{i}.unit"] = code
            ov[f"A.1.{i}.count"] = str(st[code][0])
            ov[f"A.1.{i}.hp"] = st[code][1]
        ov["B.1.1.unit"] = "ac"
        ov["B.1.1.count"] = str(st["def"][0])
        ov["B.1.1.hp"] = st["def"][1]
        ov.update({abb: "kangal", lvl: "9", hhp: st["hero"]})
        # Level 1 with the pool in the top band: the bar is 0-50 whatever the
        # level, so a 42.2 HP fortress is level 1 at 42.2 (fortress_hp_scale).
        ov.update({"B.1.bldg.1.abb": "fortress", "B.1.bldg.1.lvl": "1",
                   "B.1.bldg.1.hp": st["fort"]})
        try:
            p.submit(ov, create=full)
        except (BareFormReturned, ValueError) as e:
            print(f"     {key}: refused: {e}"[:96])
            continue
        d = dict(p.last_details)
        record("late_drift",
               {"prong": "G", "state": key, "rounds": 1, "cell": st,
                "predicted": pred[key], "detail": d,
                "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        e = pred[key]
        nxt = e["site_next"]
        print(f"     {key}  site one round : def "
              f"{(d.get('B.1.1') or {}).get('lost')}, hero "
              f"{(d.get('B.1.hero') or {}).get('lost')}, fort "
              f"{(d.get('B.1.bldg.1') or {}).get('lost')}")
        print(f"           long battle    : def {nxt['def']}, hero "
              f"{nxt['hero']}, fort {nxt['fort']}")
        print(f"           this engine    : def {e['def_lost']}, hero "
              f"{e['hero_lost']}, fort {e['fort_lost']}")

    # ---- H ---------------------------------------------------------------
    print("\n  H. 20 heavy tanks vs 20, twelve rounds, nothing else on the board")
    print(f"  {'rnd':>4} | {'A ct':>5}{'A hp':>10}{'A lost':>10}"
          f" | {'B ct':>5}{'B hp':>10}{'B lost':>10}   engine A/B lost")
    for rounds in range(1, 13):
        ov = settings(rounds, update_counts=True)
        ov.update(duel(1, "ht", 20, "ht", 20))
        try:
            p.submit(ov)
        except (BareFormReturned, ValueError) as e:
            print(f"  {rounds:>4} | refused: {e}"[:96])
            continue
        back = read_back(p)
        d = dict(p.last_details)
        record("late_drift",
               {"prong": "H", "rounds": rounds, "unit": "ht", "n": 20,
                "predicted": pred.get(f"h{rounds}"), "detail": d,
                "form_back": back, "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        e = pred.get(f"h{rounds}") or {}
        g = lambda k: back.get(k, "-")
        print(f"  {rounds:>4} | {g('A.1.1.count'):>5}{g('A.1.1.hp'):>10}"
              f"{str((d.get('A.1.1') or {}).get('lost')):>10}"
              f" | {g('B.1.1.count'):>5}{g('B.1.1.hp'):>10}"
              f"{str((d.get('B.1.1') or {}).get('lost')):>10}"
              f"   {e.get('a_lost')}/{e.get('b_lost')}")

    # ---- I and J ---------------------------------------------------------
    RA = [("inf", 35, "453.6"), ("ac", 6, "318.1"), ("cav", 17, "378.1")]
    for prong, fort, hero, ladder in (("I", False, True, (2, 3, 4)),
                                      ("J", True, False, (5, 6, 7))):
        print(f"\n  {prong}. the real army with "
              f"{'NO FORTRESS' if not fort else 'NO HERO'}")
        for rounds in ladder:
            ov = settings(rounds, update_counts=True)
            ov.update(duel(1, "inf", 35, "ac", 12))
            for i, (u, n, hp) in enumerate(RA, start=1):
                ov[f"A.1.{i}.unit"] = u
                ov[f"A.1.{i}.count"] = str(n)
                ov[f"A.1.{i}.hp"] = hp
            ov["B.1.1.unit"] = "ac"
            ov["B.1.1.count"] = "12"
            ov["B.1.1.hp"] = "677.5"
            create = composite_fields("A", 1, 3) + composite_fields("B", 1, 1)
            if hero:
                ov.update({abb: "kangal", lvl: "9", hhp: "83.1"})
                create += HERO_FIELDS
            if fort:
                ov.update({"B.1.bldg.1.abb": "fortress",
                           "B.1.bldg.1.lvl": "4", "B.1.bldg.1.hp": "100%"})
                create += bldg
            try:
                p.submit(ov, create=create)
            except (BareFormReturned, ValueError) as e:
                print(f"     {rounds:>2}: refused: {e}"[:96])
                continue
            back = read_back(p)
            d = dict(p.last_details)
            record("late_drift",
                   {"prong": prong, "rounds": rounds, "fortress": fort,
                    "hero": hero, "predicted": pred.get(f"{prong.lower()}{rounds}"),
                    "detail": d, "form_back": back,
                    "summary": dict(p.last_summary)},
                   {k: (v or {}).get("lost") for k, v in d.items()})
            e = pred.get(f"{prong.lower()}{rounds}") or {}
            g = lambda k: back.get(k, "-")
            print(f"     {rounds:>2}: site inf {g('A.1.1.count')}/{g('A.1.1.hp')}"
                  f"  ac {g('A.1.2.count')}/{g('A.1.2.hp')}"
                  f"  cav {g('A.1.3.count')}/{g('A.1.3.hp')}"
                  f"  def {g('B.1.1.count')}/{g('B.1.1.hp')}"
                  f"  hero {g('B.1.hero.hp')}")
            print(f"         eng  inf {e.get('inf')}  ac {e.get('ac')}"
                  f"  cav {e.get('cav')}  def {e.get('def')}"
                  f"  hero {e.get('hero_hp')}")


def exp_fortress_dr_low(p: Probe) -> None:
    """The fortress damage-reduction curve below 50 HP, which was never a curve.

    exp_late_drift found the residual by reading a column this project has been
    recording since the first fortress request and never looked at: the site
    PRINTS its own damage reduction on the building row, dr_before and
    dr_after. Seventy-three distinct (HP, DR) pairs were already on disk.

        DR = 0.15 x (hp/50 + 1)   is exact for every one of the 58 readings at
                                  50 HP and above, to the printed decimal
        and wrong for all 13 below it, by up to 8 points

    Below 50 the site is on a different straight line -- DR% = 5 + 0.5 x hp --
    which meets the first exactly at 50 HP and 30%. That fits all thirteen to
    the printed decimal. Every fortress in this project was entered at 100% and
    a full level, so a pool under 50 only ever appeared as the LAST GASP of a
    fortress being ground down, which is exactly the stretch of a battle where
    the engine's numbers went wrong.

    WHAT IS LEFT TO MEASURE is one thing: the floor. Two readings sit at zero,
    at 4.8 and 6.2 HP, and the lowest non-zero is 10.3 at 10.1% -- which the
    line predicts at 10.15. So a fortress under some threshold confers nothing
    at all, and the three points on file bracket it between 6.2 and 10.3
    without pinning it.

    Twelve requests, and no inference in them: the site prints the number, so
    each request reads a point off the curve directly instead of solving for it
    through a damage figure. The attacker is a single infantry so the building
    is barely touched and dr_before is the value for the HP as submitted.
    """
    print("\n  a level-1 fortress at each HP, reading the site's own DR column\n")
    print(f"  {'hp':>6} | {'site DR':>8} | {'5 + 0.5h':>9} | {'0.15(h/50+1)':>13}")
    print("  " + "-" * 46)
    fields = ("B.1.bldg.1.abb", "B.1.bldg.1.lvl", "B.1.bldg.1.hp")
    for hp in ("1", "5", "8", "9", "9.5", "10", "11", "15", "25", "35", "45", "48"):
        ov = settings(1)
        ov.update(duel(1, "inf", 1, "inf", 10))
        ov.update({"B.1.bldg.1.abb": "fortress", "B.1.bldg.1.lvl": "1",
                   "B.1.bldg.1.hp": hp})
        try:
            p.submit(ov, create=fields)
        except (BareFormReturned, ValueError) as e:
            print(f"  {hp:>6} | refused: {e}"[:96])
            continue
        d = dict(p.last_details)
        b = d.get("B.1.bldg.1") or {}
        record("fortress_dr_low",
               {"fortress_hp": hp, "level": 1, "detail": d,
                "summary": dict(p.last_summary)},
               {k: (v or {}).get("lost") for k, v in d.items()})
        dr = b.get("dr_before")
        h = float(hp)
        print(f"  {hp:>6} | {str(dr):>8} | {5 + 0.5 * h:9.2f} | "
              f"{15 * (h / 50 + 1):13.2f}")


EXPERIMENTS: dict[str, Callable[[Probe], None]] = {
    "fortress_dr_low": exp_fortress_dr_low,
    "late_drift": exp_late_drift,
    "fort_drift": exp_fort_drift,
    "bughunt": exp_bughunt,
    "unit_stats": exp_unit_stats,
    "repair_cost": exp_repair_cost,
    "hero_repair": exp_hero_repair,
    "hero_repair_all": exp_hero_repair_all,
    "bombardment": exp_bombardment,
    "bombardment_law": exp_bombardment_law,
    "bombardment_own": exp_bombardment_own,
    "bombardment_finish": exp_bombardment_finish,
    "bombardment_lucien": exp_bombardment_lucien,
    "bombardment_melee": exp_bombardment_melee,
    "togo_buff_clean": exp_togo_buff_clean,
    "mutual": exp_mutual,
    "mutual_law": exp_mutual_law,
    "mutual_order": exp_mutual_order,
    "real_army": exp_real_army,
    "fortress_hp_scale": exp_fortress_hp_scale,
    "update_counts": exp_update_counts,
    "multi_stack": exp_multi_stack,
    "range_roster": exp_range_roster,
    "return_fire": exp_return_fire,
    "mixed_range": exp_mixed_range,
    "target_terrain": exp_target_terrain,
    "embarked_hp": exp_embarked_hp,
    "embarked_class": exp_embarked_class,
    "defence_matrix": exp_defence_matrix,
    "defence_gaps": exp_defence_gaps,
    "balloon_class": exp_balloon_class,
    "embarked_is_convoy": exp_embarked_is_convoy,
    "class_matrix_2": exp_class_matrix_2,
    "balloon_columns": exp_balloon_columns,
    "attenuation_scope": exp_attenuation_scope,
    "multi_round_types": exp_multi_round_types,
    "hero_other_defending": exp_hero_other_defending,
    "hero_air_attacking": exp_hero_air_attacking,
    "hero_other_curves": exp_hero_other_curves,
    "hero_own_curves": exp_hero_own_curves,
    "hero_class_columns": exp_hero_class_columns,
    "hero_columns_small": exp_hero_columns_small,
    "togo_b_disagreement": exp_togo_b_disagreement,
    "togo_b_shape": exp_togo_b_shape,
    "togo_b_kind": exp_togo_b_kind,
    "hero_hp_scaling": exp_hero_hp_scaling,
    "land_hero_attacking": exp_land_hero_attacking,
    "land_hero_screen": exp_land_hero_screen,
    "hero_new_buffs": exp_hero_new_buffs,
    "hank_sides": exp_hank_sides,
    "land_hero_target_class": exp_land_hero_target_class,
    "land_hero_def_class": exp_land_hero_def_class,
    "m_f_generality": exp_m_f_generality,
    "building_levels": exp_building_levels,
    "e_n_gaps": exp_e_n_gaps,
    "patrol_pin": exp_patrol_pin,
    "building_damage_rest": exp_building_damage_rest,
    "field_coverage": exp_field_coverage,
    "debark_and_long_rounds": exp_debark_and_long_rounds,
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
    "hero_sides": exp_hero_sides,
    "multi_round": exp_multi_round,
    "hero_curves": exp_hero_curves,
    "offdiag": exp_offdiag,
    "trench_gaps": exp_trench_gaps,
    "fortress_edges": exp_fortress_edges,
    "building_damage": exp_building_damage,
    "position": exp_position,
    "hero_output_curves": exp_hero_output_curves,
    "hero_other_terrain": exp_hero_other_terrain,
    "cross_class": exp_cross_class,
    "edges": exp_edges,
    "balloon_trench": exp_balloon_and_trench,
    "class_matrix": exp_class_matrix,
    "last_edges": exp_last_edges,
    "close_out": exp_close_out,
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
    "unit_stats": 20, "buildings": 14, "patrol": 18, "mixed_stacks": 8, "heroes": 23, "stack_limits": 4, "hero_scaling": 9, "hero_table": 28, "hero_levels": 16, "hero_caps": 30, "stack_ladder": 9, "stack_order": 5, "hero_output": 21, "hero_buff_confirm": 5, "allocation": 9, "hero_full": 24, "hero_hp_cap": 22, "hero_sides": 30, "multi_round": 8, "hero_curves": 110, "offdiag": 8, "trench_gaps": 12, "fortress_edges": 20, "building_damage": 9, "position": 15, "hero_output_curves": 70, "hero_other_terrain": 24, "cross_class": 70, "edges": 35, "balloon_trench": 15, "class_matrix": 51, "last_edges": 20, "close_out": 35, "trenches": 10, "air_vs_ground": 30,
    "land_matrix": 100, "size_factor": 33, "hp_scaling": 10,
    "fortress": 6, "terrain": 7, "variance": 60,
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

    global DRY_RUN
    DRY_RUN = args.dry_run
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