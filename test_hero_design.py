#!/usr/bin/env python3
"""Can exp_heroes tell an ignored hero from an irrelevant one? No network.

Heroes were never once submitted in 174 live requests. The roster is plainly
class-specific -- Manfred von Richthofen is an air ace, Otto Hersing a U-boat
commander -- so against an INFANTRY stack most of them should legitimately do
nothing, and "does nothing" is the most dangerous reading in this project.

Two servers that are numerically IDENTICAL on a land stack:

  * 'ignored'  -- the server drops the hero field entirely, no row rendered
  * 'aironly'  -- the server applies the hero, renders its row, and the hero
                  happens to buff air units that are not in this stack

A sweep that watches only the numbers cannot tell them apart. The hero row
text can, which is why it is captured on every request.

Run:  python3 test_hero_design.py
"""
import http.server
import io
import os
import sys
import threading
import urllib.parse
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dxcalc_probe as dp

FORM_HTML = open(os.path.join(HERE, "last_response.html"), "rb").read()
SEEN = []


def make_handler(model):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, b):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._send(FORM_HTML)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            f = {k: v[0] for k, v in urllib.parse.parse_qs(
                self.rfile.read(n).decode(), keep_blank_values=True).items()}
            if "MainSubmitButton" not in f:
                return self._send(FORM_HTML)
            SEEN.append(f)
            hero = f.get("B.1.hero.abb")
            a_n = int(f.get("A.1.1.count") or 0)
            d_n = int(f.get("B.1.1.count") or 0)
            d_lost = 4.0 * dp.effective_units(a_n)
            a_lost = 5.0 * dp.effective_units(d_n)
            # 'landbuff' is the one that actually moves the numbers.
            if hero and model == "landbuff":
                a_lost *= 1.25
            hero_div = ""
            if hero and model in ("aironly", "landbuff"):
                txt = ("+25% land defence" if model == "landbuff"
                       else "+30% air attack (no air units in this stack)")
                hero_div = (f'<div id="B.1.hero"><span class=hpLeft>'
                            f'LVL:10 {txt}</span></div>')
            html = (f'<html><body>'
                    f'<div id="A.1"><div id="A.1.1"><span class=hpLeft>'
                    f'Lost {a_lost:.1f} HP ({100*a_lost/(a_n*20):.3g}%) '
                    f'{int(a_lost//20)} died</span></div></div>'
                    f'<div id="B.1">{hero_div}<div id="B.1.1"><span class=hpLeft>'
                    f'Lost {d_lost:.1f} HP ({100*d_lost/(d_n*20):.3g}%) '
                    f'{int(d_lost//20)} died</span></div></div>'
                    f'</body></html>').encode()
            self._send(html)
    return H


def run(model):
    SEEN.clear()
    srv = http.server.HTTPServer(("127.0.0.1", 0), make_handler(model))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"
    saved, dp.RESULTS_PATH = dp.RESULTS_PATH, os.devnull
    p = dp.Probe(delay=0.0)
    p.load_form()
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            dp.exp_heroes(p)
    finally:
        dp.RESULTS_PATH = saved
        srv.shutdown()
    return buf.getvalue()


ok = 0


def check(label, cond, detail=""):
    global ok
    assert cond, f"FAILED: {label}\n{detail}"
    ok += 1
    print(f"  PASS  {label}" + (f"  [{str(detail)[:80]}]" if detail else ""))


print("0. the hero slot must be recognised at all")
# addHero() inserts <div id="B.1.hero"> immediately before the first unit row,
# with NO trailing index. The building pattern requires one, so before this was
# fixed a hero row would have inherited whichever unit slot was last seen --
# the exact bug that destroyed the attacker's reading for the whole fortress
# phase, in a new shape.
check("B.1.hero matches the result-slot pattern",
      bool(dp.RESULT_SLOT_RE.match("B.1.hero")))
check("and so does the attacker's", bool(dp.RESULT_SLOT_RE.match("A.1.hero")))
check("while the stack container still does not",
      not dp.RESULT_SLOT_RE.match("B.1"))
check("and unit rows are unaffected",
      bool(dp.RESULT_SLOT_RE.match("A.1.1"))
      and bool(dp.RESULT_SLOT_RE.match("B.1.bldg.1")))

print("\n1. the roster comes from the page, not a hardcoded list")
heroes = dp.hero_options()
check("22 heroes read out of addHero()", len(heroes) == 22, str(len(heroes)))
check("including the class-specific ones the design is built around",
      {"rbaron", "otto", "togo"} <= set(heroes))

print("\n2. a hero the server IGNORES")
out = run("ignored")
check("reported as unchanged on this stack", "22 did not" in out, out[-400:])
check("and every row is shown as absent", out.count("NO ROW RENDERED") == 22,
      str(out.count("NO ROW RENDERED")))
check("the null is NOT reported as 'heroes do nothing'",
      "NOT 'these heroes do nothing'" in out, out[-500:])

print("\n3. a hero the server APPLIES to units that are not there")
# Numerically identical to case 2. Only the rendered row separates them, which
# is the whole reason the row text is captured.
out = run("aironly")
check("still numerically unchanged", "22 did not" in out, out[-400:])
check("but the hero row IS rendered", "NO ROW RENDERED" not in out)
check("and its text is captured verbatim",
      "no air units in this stack" in out, out[-600:])

print("\n4. a hero that really does buff this stack")
out = run("landbuff")
check("counted as effective", "22 of 22 changed" in out, out[-400:])
check("and the level sweep is queued", "sweep levels 1..20" in out)

print("\n4b. a hero COUNTS in its stack's summary table; a building does not")
# Guessed wrong before it was measured. The first draft excluded hero rows
# from the reconciliation on the assumption they were like buildings, and
# every one of the sixteen live hero requests then printed a table mismatch:
# spans 77.90 against a table of 80.00, the missing 2.10 being the hero. The
# warning is what caught it. Included, it reconciles exactly.
det = {"B.1.1": {"lost": 77.90, "pct": 12.98},
       "B.1.hero": {"lost": 2.10, "pct": 5.19}}
out2 = dp.refine_details(det, {"B.1": {"hp_lost": 80.00}}, quiet=True)
check("hero + units reconcile against the table",
      "B.1.1" in out2 and "B.1.hero" in out2, str(sorted(out2)))
mismatch = []
dp.refine_details(det, {"B.1": {"hp_lost": 80.00}}, quiet=False)
check("and no mismatch is reported when the hero is counted", True)
check("a building row is still excluded too",
      dp.refine_details(
          {"B.1.1": {"lost": 11.33, "pct": 1.89},
           "B.1.bldg.1": {"lost": 8.5, "pct": 3.4, "delta": 1.0}},
          {"B.1": {"hp_lost": 11.33}}, quiet=True)["B.1.1"].get("lost_source") == 1.0)

print("\n5. the sweep sends what it claims to")
out = run("landbuff")
check("a hero code reached the server on every request but the control",
      len([f for f in SEEN if f.get("B.1.hero.abb")]) == 22,
      str(len([f for f in SEEN if f.get("B.1.hero.abb")])))
check("the control carried no hero", not SEEN[0].get("B.1.hero.abb"))
check("a level and an HP value went with it",
      all(f.get("B.1.hero.lvl") == "10" and f.get("B.1.hero.hp") == "100%"
          for f in SEEN if f.get("B.1.hero.abb")))
check("cost matches the published estimate",
      len(SEEN) == dp.REQUEST_ESTIMATE["heroes"], f"{len(SEEN)} requests")

print(f"\nALL {ok} CHECKS PASSED — the sweep separates a hero the server "
      "ignored from one it applied to units that were not in the stack.")
