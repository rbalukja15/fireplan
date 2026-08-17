#!/usr/bin/env python3
"""Can --run air_vs_ground detect a target-class rule? Checked both ways.

The standing question is whether a Bomber deals 25.0 to infantry and 0.0 to
heavy tanks. unit_stats measured 'tac' against 'tac' and got 3.0, so every air
coefficient in that table describes same-class combat only, and the off-diagonal
is unmeasured rather than known.

Two servers, tuned so that their DIAGONAL cells are identical — which is all
unit_stats ever saw — and differing only off it:

    flat    damage is a property of the attacker; every target takes the same
    class   soft targets take much more, armour takes nothing

If the matrix design works, unit_stats cannot separate these and this must.

The third thing tested here is the failure mode that made the experiment it
replaces useless: a defender stack wiped inside the measured round has its loss
capped at its own pool, and a capped reading is indistinguishable from a genuine
target-class rule. The old damage_air sent ONE attacker at twenty defenders and
recorded whatever came back.

Run:  python3 test_matchup_design.py
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

ARMOUR = {"lt", "ht", "ac"}
SOFT_DMG, ARMOUR_DMG = 25.0, 0.0     # 'class' model, off the diagonal

SEEN: list[dict] = []


def hp_of(code):
    return dp.MEASURED_UNITS.get(code, (20.0, 4.0, 5.0))[0]


def atk_of(code):
    return dp.MEASURED_UNITS.get(code, (20.0, 4.0, 5.0))[1]


def def_of(code):
    return dp.MEASURED_UNITS.get(code, (20.0, 4.0, 5.0))[2]


def render(rows):
    out = ["<html><body>"]
    for sid, slot, lost, pool in rows:
        pct = 100.0 * lost / pool if pool else 0.0
        out.append(f"<div id={sid}><div id={slot}><span class=hpLeft>"
                   f"Lost {lost:.1f} HP ({pct:.3g}%) "
                   f"{int(lost)} died</span></div></div>"
                   '<table class=resultTable>'
                   '<tr><th>HP lost</th><th>% lost</th></tr>'
                   f'<tr><td>{lost:.2f}</td><td>{pct:.1f}</td></tr></table>')
    out.append("</body></html>")
    return "".join(out).encode()


def make_handler(model):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, payload):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            self._send(FORM_HTML)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            f = {k: v[0] for k, v in urllib.parse.parse_qs(
                self.rfile.read(n).decode(), keep_blank_values=True).items()}
            if "MainSubmitButton" not in f:
                return self._send(FORM_HTML)
            SEEN.append(f)
            x, y = f.get("A.1.1.unit"), f.get("B.1.1.unit")
            a_n = int(f.get("A.1.1.count") or 0)
            d_n = int(f.get("B.1.1.count") or 0)

            if model == "flat" or x == y:
                per = atk_of(x)
            else:
                per = ARMOUR_DMG if y in ARMOUR else SOFT_DMG
            d_lost = per * dp.effective_units(a_n)
            a_lost = def_of(y) * dp.effective_units(d_n)
            # A stack cannot lose more than it has: this is the cap that
            # silently understates the opponent's damage.
            a_pool, d_pool = a_n * hp_of(x), d_n * hp_of(y)
            self._send(render([("A.1", "A.1.1", min(a_lost, a_pool), a_pool),
                               ("B.1", "B.1.1", min(d_lost, d_pool), d_pool)]))
    return H


def run(model, attackers, targets, terrain=("air", "land")):
    SEEN.clear()
    srv = http.server.HTTPServer(("127.0.0.1", 0), make_handler(model))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"
    dp.RESULTS_PATH = os.devnull
    p = dp.Probe(delay=0.0)
    p.load_form()
    buf = io.StringIO()
    with redirect_stdout(buf):
        dp.exp_matchups(p, attackers, targets, "test",
                        atk_terrain=terrain[0], def_terrain=terrain[1])
    srv.shutdown()
    return buf.getvalue()


ok = 0


def check(label, cond, detail=""):
    global ok
    assert cond, f"FAILED: {label}\n{detail}"
    ok += 1
    print(f"  PASS  {label}")


GROUND = ["inf", "lart", "ht", "lt"]

print("Both servers agree on every diagonal cell — all unit_stats ever saw.")
print("If the matrix design works, it must still tell them apart.\n")

print("1. damage is a property of the attacker alone")
out = run("flat", ["tac"], GROUND)
check("reports it as flat across targets", "flat at" in out, out)
check("does not invent a target-class rule", "TARGET-DEPENDENT" not in out, out)
check("recovers the measured 3.0 for a bomber",
      "flat at 3.00-3.00" in out, out)

print("\n2. soft targets take 25.0, armour takes nothing")
out = run("class", ["tac"], GROUND)
check("reports target dependence", "TARGET-DEPENDENT" in out, out)
check("names the units that take zero",
      "0 against ht, lt" in out, out)
check("does not report it as flat", "flat at" not in out, out)
check("and says a class rule and a bug look alike in one cell",
      "look identical in a single cell" in out, out)

print("\n3. the diagonal alone cannot tell them apart — which is the point")
flat_diag = run("flat", ["tac"], ["tac"])
class_diag = run("class", ["tac"], ["tac"])
check("same-class measurement is identical under both models",
      "3.000" in flat_diag and "3.000" in class_diag)
check("neither can be ruled target-dependent from it",
      "TARGET-DEPENDENT" not in flat_diag and "TARGET-DEPENDENT" not in class_diag)

print("\n4. defenders are sized so the reading is not capped by a wipe")
out = run("class", ["tac"], ["lart"])
# 10 bombers at 25.0 apiece is 250 HP against light artillery at 10 HP each:
# the twenty-defender stack the old experiment used holds 200 and is wiped,
# which would have read as 20.0 damage instead of 25.0.
counts = [int(f["B.1.1.count"]) for f in SEEN]
check("light artillery stack is sized well past a 20-unit default",
      counts[0] >= 100, str(counts))
check("so the true 25.0 comes back rather than a capped 20.0",
      "25.000" in out, out)
check("no wipe flag raised", "STILL WIPED" not in out, out)

print("\n5. a wipe that happens anyway is re-run, then flagged if it persists")


class Wiper(dp.Probe):
    """Every defender is wiped no matter how big the stack gets."""

    def __init__(self):
        super().__init__(delay=0.0)
        self.baseline = {"A.1.1.unit": "", "B.1.1.unit": "", "B.1.1.count": ""}
        self.submit_marker = ("MainSubmitButton", "Start Battle")
        self.counts = []

    def submit(self, overrides, create=()):
        self.counts.append(int(overrides["B.1.1.count"]))
        self.last_details = {
            "A.1.1": {"lost": 10.0, "pct": 5.0, "pool": 200.0},
            "B.1.1": {"lost": 50.0, "pct": 100.0, "pool": 50.0},
        }
        self.last_summary = {}
        return {"A.1.1": 10.0, "B.1.1": 50.0}


w = Wiper()
dp.RESULTS_PATH = os.devnull
buf = io.StringIO()
with redirect_stdout(buf):
    dp.exp_matchups(w, ["tac"], ["inf"], "test", "air", "land")
out = buf.getvalue()
check("the stack is enlarged rather than the reading accepted",
      len(w.counts) == 3 and w.counts[1] > w.counts[0], str(w.counts))
check("and the surviving cell is marked a lower bound",
      "STILL WIPED" in out, out)

print("\n6. one request yields BOTH roles, so nothing is measured twice")
out = run("flat", ["tac"], ["inf"])
check("a single submission per pairing", len(SEEN) == 1, f"{len(SEEN)}")
check("the attacker's damage is reported", "3.000" in out, out)
check("and the target's defence coefficient from the same battle",
      "5.000" in out, out)

print("\n7. refuses to rule on an empty matrix")
buf = io.StringIO()
with redirect_stdout(buf):
    dp.report_matchups({})
check("no verdict from no cells", "NO VERDICT" in buf.getvalue())
buf = io.StringIO()
with redirect_stdout(buf):
    dp.report_matchups({"tac": {"inf": 3.0}})
check("one target is not enough to call it flat",
      "cannot say" in buf.getvalue(), buf.getvalue())

print("\n8. defender sizing uses the roster's worst case, not the attacker's own")
# Sizing on tac's measured 3.0 would send 20 defenders and lose the reading.
check("a bomber's target stack is sized for 45 damage per unit",
      dp.defender_count("inf", 10) >= 50, str(dp.defender_count("inf", 10)))
check("heavy armour needs no padding beyond the floor",
      dp.defender_count("ht", 10) == 20, str(dp.defender_count("ht", 10)))
check("an unknown unit still gets a stack rather than a crash",
      dp.defender_count("nosuchunit", 10) >= 20)

print(f"\nALL {ok} CHECKS PASSED — the matrix separates a target-class rule "
      "from a flat attacker stat, which the diagonal cannot.")
