#!/usr/bin/env python3
"""Can exp_patrol tell patrol apart from air? Never touches dxcalc.com.

patrol had never been submitted once in 150 live requests, so every air
coefficient in the model described a DIRECT attack. When it finally ran it
turned up two mechanics, and the sweep got BOTH verdicts wrong on the first
pass. This suite exists so neither misreading can come back.

The two real mechanics, now measured:

  1. ATTRITION IS CHARGED DIFFERENTLY. A stack's output is
         base * E(n) * (1 - c * its_own_fraction_lost)
     with c = 1.0 for a direct air attack and c ~ 0.36 for patrol. The base
     stat is the SAME. Patrol therefore beats air by more the harder the
     target shoots back, and by nothing at all against a target that cannot.
     The first verdict called this "patrol differs AND depends on the target",
     which is exactly what a raw ratio looks like when one coefficient changes.

  2. maxRounds MEANS DIFFERENT THINGS. Patrol damage is proportional to
     maxRounds; air ignores maxRounds entirely and delivers one strike. The
     first verdict called air "worn down between ticks" because the per-round
     RATE fell -- but the rate falls whenever a constant is divided by a
     growing number, which is not attrition and not a finding.

Servers here differ only in those two knobs, plus the balloon trap.

Run:  python3 test_patrol_design.py
"""
import http.server
import io
import json
import math
import os
import sys
import threading
import urllib.parse
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dxcalc_probe as dp

FORM_HTML = open(os.path.join(HERE, "last_response.html"), "rb").read()

# Measured physics every server below shares.
AIR_ATK = {"int": 5.0, "tac": 30.0, "zep": 5.0, "bal": 2.0}
AIR_HP = {"int": 60.0, "tac": 80.0, "zep": 140.0, "bal": 40.0}
GROUND_DEF_VS_AIR = {"inf": 0.4, "ac": 8.0, "ht": 4.0}
GROUND_HP = {"inf": 20.0, "ac": 60.0, "ht": 260.0}

C_AIR = 1.0            # a direct strike pays its full attrition
C_PATROL = 0.36        # patrol pays about a third of it (measured)

SEEN = []


def render(rows):
    out = ["<html><body>"]
    for sid, slot, lost, pool, unit_hp in rows:
        pct = 100.0 * lost / pool if pool else 0.0
        died = int(math.floor(lost / unit_hp)) if unit_hp else 0
        out.append(f"<div id={sid}><div id={slot}><span class=hpLeft>"
                   f"Lost {lost:.1f} HP ({pct:.3g}%) {died} died</span></div></div>"
                   '<table class=resultTable>'
                   '<tr><th>HP lost</th><th>% lost</th></tr>'
                   f'<tr><td>{lost:.2f}</td><td>{pct:.1f}</td></tr></table>')
    out.append("</body></html>")
    return "".join(out).encode()


def make_handler(model, patrol_rounds="proportional", air_rounds="ignored",
                 bal_ok=True):
    """model: 'same' | 'attrition' | 'targeted'.

    'attrition' is the live finding: identical base stat, smaller c in patrol.
    'targeted'  is the rival hypothesis the sweep must not confuse it with --
                patrol genuinely scaling the stat, differently per target.
    """
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
            terrain = f.get("A.1.terrain")
            a_n = int(f.get("A.1.1.count") or 0)
            d_n = int(f.get("B.1.1.count") or 0)
            rounds = float(f.get("maxRounds") or 1)
            patrol = terrain == "patrol"

            # The live trap: the server refuses a balloon "in the air", and
            # patrol counts as the air for that check. This is why the roster
            # has a permanent hole.
            if x == "bal" and (terrain == "air" or (patrol and not bal_ok)):
                return self._send(FORM_HTML)

            base = AIR_ATK.get(x, 1.0)
            c = C_AIR
            if patrol:
                if model == "attrition":
                    c = C_PATROL
                elif model == "targeted":
                    base *= 0.25 if y in ("ac", "ht") else 1.5

            scale = 1.0
            if patrol and patrol_rounds == "proportional":
                scale = rounds
            if not patrol and air_rounds == "proportional":
                scale = rounds

            a_pool = a_n * AIR_HP.get(x, 60.0)
            d_pool = d_n * GROUND_HP.get(y, 20.0)
            a_lost = min(GROUND_DEF_VS_AIR.get(y, 0.4)
                         * dp.effective_units(d_n) * scale, a_pool)
            f_own = a_lost / a_pool if a_pool else 0.0
            d_lost = min(base * dp.effective_units(a_n) * (1 - c * f_own) * scale,
                         d_pool)
            self._send(render([
                ("A.1", "A.1.1", a_lost, a_pool, AIR_HP.get(x, 60.0)),
                ("B.1", "B.1.1", d_lost, d_pool, GROUND_HP.get(y, 20.0)),
            ]))
    return H


def seed_air_cells(path):
    """The air_vs_ground rows exp_patrol reads back off disk.

    Generated from the same physics the servers use, with c = 1.0, so the base
    stat the sweep recovers from them is exactly AIR_ATK. Any coefficient it
    then reports for patrol is caused by the model under test, not by the
    fixture disagreeing with the server.
    """
    rows = []
    for unit in ("int", "tac", "zep"):
        for target in ("inf", "ac", "ht"):
            d_n = dp.defender_count(target, 10)
            a_pool = 10 * AIR_HP[unit]
            a_lost = min(GROUND_DEF_VS_AIR[target] * dp.effective_units(d_n),
                         a_pool)
            d_lost = (AIR_ATK[unit] * dp.effective_units(10)
                      * (1 - C_AIR * a_lost / a_pool))
            rows.append({"experiment": "air_vs_ground", "meta": {
                "atk": unit, "target": target, "def_n": d_n,
                "detail": {
                    "A.1.1": {"lost": a_lost, "pool": a_pool,
                              "pct": 100.0 * a_lost / a_pool},
                    "B.1.1": {"lost": d_lost,
                              "pool": d_n * GROUND_HP[target]},
                }}, "readings": {}})
    with open(path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


SEED = os.path.join(HERE, ".patrol_test_air_cells.jsonl")
seed_air_cells(SEED)


def run(**kw):
    SEEN.clear()
    srv = http.server.HTTPServer(("127.0.0.1", 0), make_handler(**kw))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"
    saved = dp.RESULTS_PATH
    dp.RESULTS_PATH = SEED
    p = dp.Probe(delay=0.0)
    p.load_form()
    real_record = dp.record
    dp.record = lambda tag, meta, readings: None      # never append to the seed
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            dp.exp_patrol(p)
    finally:
        dp.record = real_record
        dp.RESULTS_PATH = saved
        srv.shutdown()
    return buf.getvalue()


ok = 0


def check(label, cond, detail=""):
    global ok
    assert cond, f"FAILED: {label}\n{detail}"
    ok += 1
    print(f"  PASS  {label}" + (f"  [{str(detail)[:80]}]" if detail else ""))


def ladder_of(out, terrain):
    block = out.split("2. does a round subdivide?")[-1]
    keep, grab = [], False
    for line in block.splitlines():
        if line.strip().startswith(terrain):
            keep.append(line)
            grab = True
        elif grab and "->" in line:
            keep.append(line)
            grab = False
    return "\n".join(keep)


print("Every server returns identical AIR readings. Only patrol differs.\n")

print("1. patrol is air under another name")
out = run(model="same", patrol_rounds="ignored")
check("reports the same coefficient for both",
      "indistinguishable from air" in out, out[-300:])
check("does not claim a different delivery", "DIFFERENT DELIVERY" not in out)
check("does not demand its own matrix", "needs its own matrix" not in out)

print("\n2. THE LIVE FINDING: same stat, smaller attrition coefficient")
out = run(model="attrition")
check("recovers the base stat and blames the coefficient",
      "SAME BASE STAT, DIFFERENT DELIVERY" in out, out[-400:])
cline = [l for l in out.splitlines() if "patrol  c =" in l]
check(f"recovers c close to the {C_PATROL} the server used",
      bool(cline) and "c = 0.3" in cline[0], cline)
check("says the air column carries over with the coefficient",
      "DOES carry over" in out)
check("does NOT report it as a target rule",
      "needs its own matrix" not in out)

print("\n3. a genuine per-target multiplier is still caught")
# The rival hypothesis. If patrol really did scale the stat per target, no
# single coefficient fits, and the sweep must say so rather than average
# 1.5x on soft targets with 0.25x on armour into one tidy number.
out = run(model="targeted")
check("refuses to fit one coefficient", "needs its own matrix" in out, out[-400:])
check("and does not claim a shared base stat", "SAME BASE STAT" not in out)

print("\n4. maxRounds: proportional in patrol, ignored in air")
# Both mechanics as measured live. A rate-based reading alone cannot tell
# 'ignored' from 'attrition' -- both make the per-round rate fall.
out = run(model="attrition", patrol_rounds="proportional", air_rounds="ignored")
check("patrol is reported as proportional to maxRounds",
      "PROPORTIONAL TO maxRounds" in out, ladder_of(out, "patrol"))
check("air is reported as ignoring maxRounds",
      "maxRounds IS IGNORED" in out, ladder_of(out, "air"))
check("air is NOT misreported as inter-tick attrition",
      "worn down between ticks" not in out)
check("and the single-strike reading is named as such",
      "single strike, not a duration" in out)

print("\n5. a server where air DOES scale with rounds is not called 'ignored'")
out = run(model="attrition", patrol_rounds="proportional",
          air_rounds="proportional")
check("no false 'ignored' verdict for the air ladder",
      "maxRounds IS IGNORED" not in ladder_of(out, "air"),
      ladder_of(out, "air"))

print("\n6. the balloon, in the one terrain nobody had tried")
out = run(model="attrition", bal_ok=True)
check("a flyable balloon closes the roster hole",
      "bal FLIES IN PATROL" in out, out[-250:])
out = run(model="attrition", bal_ok=False)
check("a balloon refused in patrol too is reported, not silently dropped",
      "refused or unreadable in patrol" in out, out[-250:])
check("and it says to widen the guard", "Widen guard_payload" in out)

print("\n7. the sweep actually varies the fields it claims to")
out = run(model="attrition")
check("both terrains reached the server",
      {f.get("A.1.terrain") for f in SEEN} == {"patrol", "air"},
      str({f.get("A.1.terrain") for f in SEEN}))
check("the quarter-round ladder reached the server",
      {"0.25", "0.5", "0.75", "1"} <= {f.get("maxRounds") for f in SEEN},
      str(sorted({f.get("maxRounds") for f in SEEN})))
check("attacker count is 10, matching air_vs_ground so cells compare",
      all(f.get("A.1.1.count") == "10" for f in SEEN),
      str({f.get("A.1.1.count") for f in SEEN}))
check("the defender is always on land",
      all(f.get("B.1.terrain") == "land" for f in SEEN))
check("cost matches the published estimate",
      len(SEEN) == dp.REQUEST_ESTIMATE["patrol"], f"{len(SEEN)} requests")

os.unlink(SEED)
print(f"\nALL {ok} CHECKS PASSED — the sweep separates a shared stat with a "
      "different attrition coefficient from a real per-target rule, and "
      "'maxRounds is ignored' from 'worn down between ticks'.")
