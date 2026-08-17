#!/usr/bin/env python3
"""Can exp_unit_stats recover known unit constants from battle output alone?

Stands up a server with a hidden unit table and the combat rules we have
established, then checks the sweep reads those exact constants back out. This
is the whole inference chain under test -- span text -> lost/pct/died -> pool
-> max HP, and losses -> per-unit attack and defence damage -- including the
saturation rescue and the balloon guard.

Run:  python3 test_unit_stats.py
"""
import http.server
import io
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

#                 max_hp,  dmg_attacking, dmg_defending
UNITS = {
    "inf": (20.0, 4.0, 5.0),      # the real, measured infantry values
    "ht": (120.0, 45.0, 50.0),    # heavy, survives 10v10 comfortably
    "rrg": (50.0, 60.0, 20.0),    # one-shots its own kind at 10v10 -> saturates
}
DEFAULT = (30.0, 6.0, 7.0)


def render(lost, pool, hp):
    pct = 100.0 * lost / pool if pool else 0.0
    died = int(math.floor(lost / hp))
    return f"Lost {lost:.1f} HP ({pct:.1f}%) {died} died"


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(FORM_HTML)))
        self.end_headers()
        self.wfile.write(FORM_HTML)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        f = {k: v[0] for k, v in urllib.parse.parse_qs(
            self.rfile.read(n).decode(), keep_blank_values=True).items()}
        code = f.get("A.1.1.unit", "inf")
        hp, d_atk, d_def = UNITS.get(code, DEFAULT)
        atk_n = int(f.get("A.1.1.count") or 0)
        def_n = int(f.get("B.1.1.count") or 0)
        pool_a, pool_b = atk_n * hp, def_n * hp
        # A is attacking: A's loss comes from the defenders, B's from attackers.
        lost_a = min(dp.effective_units(def_n) * d_def, pool_a)
        lost_b = min(dp.effective_units(atk_n) * d_atk, pool_b)
        html = (f'<html><body>'
                f'<div id="A.1.1"><span class="hpLeft">'
                f'{render(lost_a, pool_a, hp)}</span></div>'
                f'<div id="B.1.1"><span class="hpLeft">'
                f'{render(lost_b, pool_b, hp)}</span></div>'
                f'</body></html>').encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)


srv = http.server.HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"

rows = []
dp.record = lambda tag, meta, readings: rows.append(meta)

p = dp.Probe(delay=0.0)
p.load_form()
buf = io.StringIO()
with redirect_stdout(buf):
    dp.exp_unit_stats(p)
out = buf.getvalue()
srv.shutdown()

by_code = {r["unit"]: r for r in rows if "unit" in r}
ok = 0


def check(label, cond, detail=""):
    global ok
    assert cond, f"FAILED: {label}  {detail}"
    ok += 1
    print(f"  PASS  {label}" + (f"  [{detail}]" if detail else ""))


def near(a, b, tol=0.05):
    return a is not None and abs(a - b) < tol


print(f"swept {len(by_code)} unit types, {p.request_count} requests\n")

print("1. roster came from the live form, not a hardcoded list")
check("17 unit types found", len(by_code) == 17, str(len(by_code)))
check("classified across all three terrains",
      {r["terrain"] for r in by_code.values()} == {"land", "air", "sea"})

print("\n2. infantry constants recovered exactly")
r = by_code["inf"]
check("max HP 20.0", near(r["max_hp"], 20.0), str(r["max_hp"]))
check("4.0 attacking", near(r["dmg_attacking"], 4.0), str(r["dmg_attacking"]))
check("5.0 defending", near(r["dmg_defending"], 5.0), str(r["dmg_defending"]))

print("\n3. a heavy unit with quite different constants")
r = by_code["ht"]
check("max HP 120.0", near(r["max_hp"], 120.0), str(r["max_hp"]))
check("45.0 attacking", near(r["dmg_attacking"], 45.0), str(r["dmg_attacking"]))
check("50.0 defending", near(r["dmg_defending"], 50.0), str(r["dmg_defending"]))

print("\n4. saturation is detected and cleared, not silently fitted")
r = by_code["rrg"]
check("flagged as re-run", "re-run" in (r.get("note") or ""), repr(r.get("note")))
check("60.0 attacking recovered after rescue",
      near(r["dmg_attacking"], 60.0), str(r["dmg_attacking"]))
check("20.0 defending recovered", near(r["dmg_defending"], 20.0),
      str(r["dmg_defending"]))
check("max HP 50.0", near(r["max_hp"], 50.0), str(r["max_hp"]))

print("\n5. the balloon trap is refused, not sent")
check("bal skipped", "bal" in by_code and by_code["bal"].get("max_hp") is None)
check("and reported as skipped in the table", "SKIPPED" in out)

print("\n6. one request per unit in the common case")
check("well under a request per unit per side",
      p.request_count <= len(by_code) + 6, f"{p.request_count} requests")

print(f"\nALL {ok} CHECKS PASSED")
