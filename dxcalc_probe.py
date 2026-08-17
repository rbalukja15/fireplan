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
    python3 dxcalc_probe.py --run damage_land
    python3 dxcalc_probe.py --run all --delay 2.0

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

Per-unit base damage (partial):
    infantry 4.0 | cavalry 15 | artillery 8 | heavy tank 45

Trenches add to the defender's HP pool rather than reducing incoming damage.
Levels 1-3 conferred no measurable benefit at all.

KNOWN SERVER BUG
    A Balloon ('bal') in 'air' terrain makes the server silently return the
    bare input form: no error, no results, and the ENTIRE multi-stack batch is
    aborted, not just that pair. Reproduced three times; vanished the moment
    'bal' was dropped. guard_payload() below refuses to send that combination.

STILL OPEN
    - Fortresses produced zero effect in every configuration tried. Most
      likely the synthetic building rows are missing something the real UI
      attaches, so this says more about the rig than about the calculator.
    - Tactical bomber deals 25.0 to infantry but 0.0 to heavy tanks, while
      fighters deal 0 ground damage generally. Target-class rule or bug?
      One data point each; needs the full air x ground matrix.
    - Naval roster untouched.
    - Terrain multipliers untouched.
    - Variance distribution (the +/-10% roll) never sampled.

ISOLATION TECHNIQUE
    Up to 8 independent duels can share one POST if the stacks sit 10+ km
    apart, which is beyond the 5 km melee range, so no pair interferes with
    another. Keep terrain homogeneous within a submission (all land, or all
    air, or all sea) — mixed-terrain multi-pair runs were unreliable.

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
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Callable

BASE_URL = "https://dxcalc.com/s1914"
DEFAULT_DELAY = 1.5
RESULTS_PATH = "results.jsonl"

SLOT_RE = re.compile(r"^([AB])\.(\d+)\.(\d+)$")
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "form":
            if self.form_action is None:
                self.form_action = a.get("action", "")
                self.form_method = a.get("method", "post").lower()
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
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        node_id = a.get("id", "")
        if SLOT_RE.match(node_id):
            self._slot = node_id
        classes = a.get("class", "").split()
        if tag == "span" and "hpLeft" in classes:
            self._capture = True
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._capture:
            self._capture = False
            text = "".join(self._buf).strip()
            if self._slot and text:
                self.readings[self._slot] = text


# onAttack(name, value) injects a hidden field at click time so the server can
# recognise the POST as an attack. It is NOT in the DOM, so it never showed up
# in a field dump — and without it the server just re-renders the empty form.
ONATTACK_RE = re.compile(
    r"""onAttack\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)""")


def find_submit_marker(page: str) -> tuple[str, str] | None:
    """Recover the hidden marker field from the button's onclick attribute."""
    m = ONATTACK_RE.search(html_mod.unescape(page))
    return (m.group(1), m.group(2)) if m else None


OOPS_RE = re.compile(r"oops:[^<>\n]{0,200}", re.I)


def find_oops(html: str) -> list[str]:
    """The calculator reports bad input as 'oops: ...' text. Read it back."""
    return [m.strip() for m in OOPS_RE.findall(html)]


def parse_hp(text: str) -> float | None:
    m = re.search(r"-?\d+(?:[.,]\d+)?", text.replace(",", "."))
    return float(m.group(0)) if m else None


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
    """Server handed back the empty input form: no results, no error."""


class Probe:
    def __init__(self, delay: float = DEFAULT_DELAY, dry_run: bool = False,
                 insecure: bool = False) -> None:
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
        self.select_options = scraper.select_options
        self.select_groups = scraper.select_groups
        self.option_labels = scraper.option_labels
        if not self.baseline:
            raise RuntimeError("No form fields found — page layout changed?")
        return self.baseline

    def submit(self, overrides: dict[str, Any]) -> dict[str, float]:
        if not self.baseline:
            self.load_form()
        payload = dict(self.baseline)
        for k, v in overrides.items():
            if k not in payload:
                continue  # row/stack the live form doesn't have; skip it
            payload[k] = "" if v is None else str(v)

        if self.submit_marker:
            payload[self.submit_marker[0]] = self.submit_marker[1]

        guard_payload(payload)

        if self.dry_run:
            print(json.dumps({k: v for k, v in payload.items() if v}, indent=1))
            return {}

        self._throttle()
        body = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(
            self.post_url,
            data=body,
            headers={
                "User-Agent": UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": BASE_URL,
                "Origin": "https://dxcalc.com",
            },
        )
        with self.opener.open(req, timeout=60) as resp:
            html = resp.read().decode("utf-8", "replace")
        self.request_count += 1
        self.last_response = html

        oops = find_oops(html)
        if oops:
            raise BareFormReturned("server said -> " + " | ".join(oops[:4]))
        scraper = ResultScraper()
        scraper.feed(html)
        if not scraper.readings:
            with open("last_response.html", "w") as fh:
                fh.write(html)
            raise BareFormReturned(
                "No hpLeft spans in response. Either an invalid unit/terrain "
                "combination aborted the batch (see the balloon bug), or the "
                "POST body is missing a field the server requires."
            )
        out: dict[str, float] = {}
        for slot, text in scraper.readings.items():
            val = parse_hp(text)
            if val is not None:
                out[slot] = val
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
) -> dict[str, str]:
    """One isolated attacker-vs-defender pair in slot `stack`.

    A attacks B explicitly via the target field; B defends (target "0").
    Both sides share a position so ranged attackers are always in range and
    the defender inherits any buildings assigned at that position.
    """
    if def_terrain is None:
        def_terrain = atk_terrain
    payload = {
        f"A.{stack}.target": f"B.{stack}",
        f"A.{stack}.terrain": atk_terrain,
        f"A.{stack}.position": str(position),
        f"A.{stack}.trench": "0",
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


def exp_damage_land(p: Probe) -> None:
    """One attacker vs a fat defender stack, single round: HP delta IS base damage."""
    units = roster(p, "land")
    target = units[0] if units else "inf"
    for unit in units:
        ov = settings()
        ov.update(duel(1, unit, 1, target, 20))
        try:
            record("damage_land", {"unit": unit, "label": label_of(p, unit)},
                   p.submit(ov))
        except BareFormReturned as e:
            print(f"  ! {unit}: {e}", file=sys.stderr)


def exp_damage_air(p: Probe) -> None:
    """The unresolved one: does the bomber really do 0 to heavy tanks?

    Full air x ground matrix. If a plane is 0 against everything armoured and
    nonzero against everything soft, that's a target-class rule. If it's 0
    against heavy tanks specifically and fine against other armour, that's a
    bug worth mailing to dxcalc@gmail.com.

    One pair per submission: a single bad combination aborts the whole batch.
    """
    for unit in roster(p, "air"):
        for target in roster(p, "land"):
            ov = settings()
            ov.update(duel(1, unit, 1, target, 20,
                           atk_terrain="air", def_terrain="land"))
            try:
                record("damage_air",
                       {"unit": unit, "target": target,
                        "unit_label": label_of(p, unit),
                        "target_label": label_of(p, target)},
                       p.submit(ov))
            except (BareFormReturned, ValueError) as e:
                print(f"  ! {unit} vs {target}: {e}", file=sys.stderr)


def exp_damage_sea(p: Probe) -> None:
    units = roster(p, "naval")
    for unit in units:
        for target in units:
            ov = settings()
            ov.update(duel(1, unit, 1, target, 20, atk_terrain="sea", def_terrain="sea"))
            try:
                record("damage_sea",
                       {"unit": unit, "target": target,
                        "unit_label": label_of(p, unit)},
                       p.submit(ov))
            except BareFormReturned as e:
                print(f"  ! {unit} vs {target}: {e}", file=sys.stderr)


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
    """Retry of the sweep that produced nothing.

    Two likely reasons the earlier attempt read zero everywhere:
      1. A fortress row needs BOTH level and HP. The help page says any unit
         or building with missing/zero HP is silently ignored — the same rule
         that swallows incomplete unit rows. A level-only fortress row is
         therefore dropped without comment.
      2. Buildings attach to a POSITION, and every stack at that position
         inherits them. Spacing pairs 10 km apart to isolate them also
         separated the defender from its own fortress.

    So: same position for both stacks, and level plus HP on the building row.
    Run --dump-fields first and set BLDG_FIELDS to the real names.
    """
    bldg_abb = "B.1.bldg.0.abb"   # buildings protect the DEFENDER
    bldg_lvl = "B.1.bldg.0.lvl"   # note: bldg rows index from 0, unit rows from 1
    bldg_hp = "B.1.bldg.0.hp"
    if bldg_abb not in p.baseline:
        print("  ! building fields are not in the baseline form.", file=sys.stderr)
        print("    'add bldg' injects them client-side, so a plain GET can't", file=sys.stderr)
        print("    see them. In DevTools on the page, with a fortress added:", file=sys.stderr)
        print("      [...document.querySelectorAll('[name]')]", file=sys.stderr)
        print("        .map(e => e.name + ' = ' + e.value).join('\\n')", file=sys.stderr)
        print("    then paste the fortress rows in above.", file=sys.stderr)
        return

    # Control first: identical battle, no fortress. Every fort reading is a
    # ratio against this, so an absolute number never has to be trusted.
    base = settings()
    base.update(duel(1, "inf", 30, "inf", 30))
    try:
        record("fortress", {"level": 0, "note": "control, no bldg"}, p.submit(base))
    except BareFormReturned as e:
        print(f"  ! control: {e}", file=sys.stderr)
        return

    # Land terrain, both stacks at the same position so the defender actually
    # inherits its own fortress, and stacks big enough to survive one round —
    # a wipe saturates the result and hides any mitigation.
    for level in (1, 2, 3, 4, 5):
        ov = dict(settings(), **{bldg_abb: "fortress", bldg_lvl: str(level), bldg_hp: "100%"})
        ov.update(duel(1, "inf", 30, "inf", 30))
        try:
            record("fortress", {"level": level, "hp": "100%"}, p.submit(ov))
        except BareFormReturned as e:
            print(f"  ! fort L{level}: {e}", file=sys.stderr)


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


EXPERIMENTS: dict[str, Callable[[Probe], None]] = {
    "size_factor": exp_size_factor,
    "hp_scaling": exp_hp_scaling,
    "damage_land": exp_damage_land,
    "damage_air": exp_damage_air,
    "damage_sea": exp_damage_sea,
    "patrol": exp_patrol,
    "fortress": exp_fortress,
    "terrain": exp_terrain,
    "variance": exp_variance,
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
    args = ap.parse_args()

    p = Probe(delay=args.delay, dry_run=args.dry_run, insecure=args.insecure)
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
            print(f"  response  : {len(body)} bytes -> last_response.html", file=sys.stderr)
            for marker in ("hpLeft", "hpLost", "Lost ", "died", "oops", "Start Battle"):
                print(f"    contains {marker!r}: {marker in body}", file=sys.stderr)
            return 1
        print(f"SANITY OK: {readings}")
        return 0

    if not args.run:
        ap.print_help()
        return 0

    names = list(EXPERIMENTS) if args.run == "all" else [args.run]
    for name in names:
        fn = EXPERIMENTS.get(name)
        if not fn:
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
        if "CERTIFICATE_VERIFY_FAILED" in str(exc):
            print("\nPython can't find a CA bundle. In order of preference:", file=sys.stderr)
            print("  1. macOS python.org build — run the bundled installer:", file=sys.stderr)
            print("     open '/Applications/Python 3.x/Install Certificates.command'", file=sys.stderr)
            print("  2. pip install certifi   (this script picks it up automatically)", file=sys.stderr)
            print("  3. --insecure            (disables verification; last resort)", file=sys.stderr)
        sys.exit(1)