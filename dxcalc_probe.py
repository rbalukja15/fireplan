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

Per-unit base damage, other units — PROVISIONAL, RE-RUN BEFORE USE:
    cavalry 15 | artillery 8 | heavy tank 45
    Collected before we noticed the stock form ships B.1.2=ac x5, B.1.3=lt x3,
    B.1.4=ht x1 pre-filled, so any run that set only row 1 was silently
    fighting three extra defender types. duel() now blanks rows 2-8, but these
    numbers predate that, AND they carry no attack/defence label. Suspect on
    both counts.

Trenches add to the defender's HP pool rather than reducing incoming damage.
Levels 1-3 conferred no measurable benefit at all.

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
    - Fortress mitigation, now that the sweep writes to bldg.1. Unmeasured
      rather than zero: the previous null result was an artifact of the index.
      Extend to the other seven building types once forts read non-1.0.
    - Tactical bomber deals 25.0 to infantry but 0.0 to heavy tanks, while
      fighters deal 0 ground damage generally. Target-class rule or bug?
      One data point each; needs the full air x ground matrix.
    - Naval roster untouched.
    - Terrain multipliers untouched.
    - Variance distribution (the +/-10% roll) never sampled.

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
    r"Lost\s+([\d.]+)\s*HP\s*\(\s*([\d.]+)\s*%\s*\)"
    r"(?:\s*(?:all\s+)?(\d+)\s+died)?", re.I)


def parse_reading(text: str) -> dict[str, float] | None:
    """Full breakdown of one result span, not just the leading number."""
    m = READING_RE.search(strip_thousands(text))
    if not m:
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
    """Server handed back the empty input form: no results, no error."""


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
        # Full breakdown lives on the Probe; the return value stays a plain
        # slot -> HP-lost mapping so existing experiments keep working.
        self.last_details = {}
        out: dict[str, float] = {}
        for slot, text in scraper.readings.items():
            detail = parse_reading(text)
            if detail is not None:
                self.last_details[slot] = detail
                out[slot] = detail["lost"]
                continue
            val = parse_hp(text)          # fallback for unrecognised phrasing
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
    record("fortress", {"level": 0, "note": "control, no bldg row"}, control)
    ref = control.get("B.1.1")
    print(f"  control (no fortress): defender lost {ref}")

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
        record("fortress", {"level": level, "hp": "100%", "row": row}, r)
        got = r.get("B.1.1")
        ratio = (got / ref) if (ref and got is not None) else None
        print(f"  fortress L{level}: defender lost {got}"
              + (f"   ratio {ratio:.4f}" if ratio is not None else "")
              + ("  <- mitigation" if ratio is not None and ratio < 0.999 else ""))


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
            print(f"  response  : {len(body)} bytes -> last_response.html", file=sys.stderr)
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