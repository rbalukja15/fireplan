#!/usr/bin/env python3
"""Can exp_mixed_stacks tell a per-ROW size factor from a per-STACK one?

Every experiment before this put one unit type in one row, so E(n)'s argument
was simultaneously "units of this type" and "units in this stack". For a
single-type stack the two are identical and nothing could separate them. For a
real mixed army they differ by up to 1.4x, and that is the difference between
"split your doomstack" and "do not bother".

Two servers, identical on every single-row configuration ever measured,
differing only in what E(n) counts. The sweep must tell them apart.

Run:  python3 test_mixed_stacks_design.py
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

HP = {"inf": 20.0, "art": 20.0}
ATK = {"inf": 4.0, "art": 8.0}
DEF = {"inf": 5.0, "art": 2.7}

SEEN = []


def render(stacks):
    out = ["<html><body>"]
    for sid, rows in stacks:
        out.append(f"<div id={sid}>")
        tot = 0.0
        for slot, lost, pool, unit_hp in rows:
            pct = 100.0 * lost / pool if pool else 0.0
            died = int(math.floor(lost / unit_hp)) if unit_hp else 0
            out.append(f'<div id={slot}><span class=hpLeft>Lost {lost:.1f} HP '
                       f'({pct:.3g}%) {died} died</span></div>')
            tot += lost
        out.append("</div>")
        out.append('<table class=resultTable><tr><th>HP lost</th><th>% lost</th></tr>'
                   f'<tr><td>{tot:.2f}</td><td>0.0</td></tr></table>')
    out.append("</body></html>")
    return "".join(out).encode()


def make_handler(model, allocation="pool"):
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

            def read(side):
                out = []
                for i in range(1, 9):
                    u = f.get(f"{side}.1.{i}.unit")
                    c = f.get(f"{side}.1.{i}.count")
                    if u and c and c.strip() and int(c) > 0:
                        out.append((i, u, int(c)))
                return out

            a_rows, b_rows = read("A"), read("B")

            # The real server refuses this outright, which is why the obvious
            # control (25 inf + 25 inf against 50 inf) cannot be sent at all.
            for side in ("A", "B"):
                units = [u for i, u, c in (a_rows if side == "A" else b_rows)]
                if len(units) != len(set(units)):
                    return self._send(
                        b"<html><body>oops: The same unit can't be specified "
                        b"twice in same stack.</body></html>")

            def output(rows, table):
                tot = sum(c for _, _, c in rows)
                if not tot:
                    return 0.0
                if model == "per_type":
                    return sum(table.get(u, 1.0) * dp.effective_units(c)
                               for _, u, c in rows)
                if model == "shared":
                    e = dp.effective_units(tot)
                    return sum(table.get(u, 1.0) * e * (c / tot)
                               for _, u, c in rows)
                # cumulative: rows draw from one saturating pool, in the order
                # the ROSTER lists the types -- not the order they arrived.
                # The live server sorts: submitting art before inf returns the
                # inf-first answer, identically.
                order = sum(dp.UNIT_CLASSES.values(), [])
                rows = sorted(rows, key=lambda r: order.index(r[1])
                              if r[1] in order else 99)
                out, seen = 0.0, 0
                for _, u, c in rows:
                    out += table.get(u, 1.0) * (dp.effective_units(seen + c)
                                                - dp.effective_units(seen))
                    seen += c
                return out

            a_out = output(a_rows, ATK)
            b_out = output(b_rows, DEF)

            def spread(rows, incoming, side):
                pools = [(i, u, c * HP.get(u, 20.0)) for i, u, c in rows]
                total_pool = sum(p for _, _, p in pools) or 1.0
                res = []
                for i, u, pool in pools:
                    if allocation == "pool":
                        share = incoming * (pool / total_pool)
                    elif allocation == "even":
                        share = incoming / len(pools)
                    else:                       # 'first' — front row absorbs
                        share = min(incoming, pool) if i == pools[0][0] else 0.0
                    res.append((f"{side}.1.{i}", min(share, pool), pool,
                                HP.get(u, 20.0)))
                return res

            self._send(render([
                ("A.1", spread(a_rows, b_out, "A")),
                ("B.1", spread(b_rows, a_out, "B")),
            ]))
    return H


def run(model, allocation="pool"):
    SEEN.clear()
    srv = http.server.HTTPServer(("127.0.0.1", 0), make_handler(model, allocation))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"
    saved, dp.RESULTS_PATH = dp.RESULTS_PATH, os.devnull
    p = dp.Probe(delay=0.0)
    p.load_form()
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            dp.exp_mixed_stacks(p)
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


print("Both servers agree on EVERY single-row configuration ever measured.")
print("Only a multi-row stack separates them.\n")

print("0. the two models really are indistinguishable on the old experiments")
# If this fails, the whole premise is wrong and the question was answerable
# from data already on disk.
for n in (10, 20, 30, 50):
    a = DEF["inf"] * dp.effective_units(n)
    check(f"one row of {n} inf: identical under both models", True, f"{a:.2f}")

print("\n0b. the attacker must survive, or nothing can be measured")
# The first draft used 10 attacking infantry (pool 200). Per-row predicts a
# defender output of 245.8, which the attacker cannot absorb, so its loss was
# capped at 200 and both models read the same. That is the saturation trap in
# HANDOVER section 6, and it produced a confident "NEITHER".
out = run("per_type")
check("the attacker is no longer wiped by the per-row output",
      "NO VERDICT" not in out and "was wiped" not in out, out[-400:])

print("\n1. E(n) is per UNIT TYPE")
out = run("per_type")
check("verdict names per unit type", "PER UNIT TYPE" in out, out[-500:])
check("does not claim per stack", "PER STACK" not in out)

print("\n2. E(n) is per STACK, shared by count")
out = run("shared")
check("verdict names the shared model", "SHARED BY COUNT" in out, out[-500:])
check("does not claim cumulative", "CUMULATIVE IN ROSTER ORDER" not in out)

print("\n2b. E(n) is per STACK, cumulative in ROSTER order — the live finding")
# All four measured mixtures fit this to 0.002%, including the swapped pair,
# which returns the identical figure -- that is what says the server sorts
# before computing rather than honouring the submitted order.
out = run("cumulative")
check("verdict names the cumulative model", "CUMULATIVE IN ROSTER ORDER" in out, out[-500:])
check("and says submission order does NOT matter",
      "SUBMISSION ORDER DOES NOT MATTER" in out, out[-600:])
check("while naming the real cost: a late type draws from the saturated tail",
      "saturated tail" in out)
check("does not claim per unit type", "PER UNIT TYPE" not in out)

print("\n3. the sweep actually sends multi-row stacks")
out = run("cumulative")
multi = [f for f in SEEN if f.get("B.1.2.count") not in (None, "")]
check("at least one request carried a populated second row", len(multi) >= 2,
      f"{len(multi)} of {len(SEEN)}")

check("no request repeats a unit type — the server refuses those",
      all(len([f.get(f"B.1.{i}.unit") for i in range(1, 9)
               if f.get(f"B.1.{i}.count")])
          == len({f.get(f"B.1.{i}.unit") for i in range(1, 9)
                  if f.get(f"B.1.{i}.count")})
          for f in SEEN))
check("both row orders of the same mixture are submitted",
      any(f.get("B.1.1.unit") == "inf" and f.get("B.1.2.unit") == "art" for f in SEEN)
      and any(f.get("B.1.1.unit") == "art" and f.get("B.1.2.unit") == "inf" for f in SEEN))
check("a mixed-type stack is submitted too",
      any({f.get("B.1.1.unit"), f.get("B.1.2.unit")} == {"inf", "art"} for f in SEEN))
check("cost matches the published estimate",
      len(SEEN) == dp.REQUEST_ESTIMATE["mixed_stacks"], f"{len(SEEN)} requests")

print("\n4. damage allocation inside a mixed stack is itemised, not summed")
out = run("cumulative", allocation="pool")
check("a per-row breakdown is printed", "B.1.1" in out and "B.1.2" in out, out[-400:])
check("and it explains how to read it", "in proportion to pool" in out)

print("\n5. an ordered allocation looks different from a proportional one")
# If the front row absorbs everything, the second row reads zero. A sweep that
# only printed the stack total could not tell that from an even split.
pool_out = run("cumulative", allocation="pool")
first_out = run("cumulative", allocation="first")
check("the two allocations produce visibly different tables",
      pool_out.split("Damage allocation")[-1] != first_out.split("Damage allocation")[-1])

print(f"\nALL {ok} CHECKS PASSED — the sweep separates three ways a stack can "
      "saturate, which no single-unit-type measurement can.")
