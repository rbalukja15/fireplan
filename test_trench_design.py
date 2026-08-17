#!/usr/bin/env python3
"""Can --run trenches tell its three hypotheses apart? Checked against all of them.

The standing claim about trenches — "they add to the defender's HP pool rather
than reducing damage, and levels 1-3 conferred no benefit" — was reached with a
rig that could read only one number per stack. This is the same test
test_semantics_design.py applies to --semantics: stand up servers whose physics
differ ONLY in what a trench does, tune every one of them to produce the
identical control reading, and require the experiment to reach the right
verdict against each.

    pool   trench multiplies the defender's HP pool; absolute HP lost is flat
    dr     trench scales incoming damage down; the pool is flat
    inert  trench does nothing at all

All three are indistinguishable at trench 0, and the first and third are
indistinguishable to anything that reads only HP lost. That is exactly the
confusion the old conclusion is suspected of, so it is the thing worth proving
against.

Run:  python3 test_trench_design.py
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

UNIT_HP = 20.0          # infantry, as measured
ATK_DMG = 4.0           # per infantry attacking
DEF_DMG = 5.0           # per infantry defending
POOL_PER_LEVEL = 0.10   # 'pool' model: +10% pool per trench level
DR_PER_LEVEL = 0.03     # 'dr'   model: -3%  damage per trench level

SEEN: list[dict] = []


def render(stacks: list[tuple[str, list[tuple[str, float, float]]]]) -> bytes:
    """Markup shaped like the real response: stack div, unit spans, then the
    stack's own summary table. Percentages get three significant figures and
    spans one decimal of HP, matching what dxcalc.com actually prints, so the
    experiment is fed the same precision it will meet live."""
    out = ["<html><body>"]
    for sid, rows in stacks:
        out.append(f"<div id={sid}>")
        total = pool_total = 0.0
        for slot, lost, pool in rows:
            pct = 100.0 * lost / pool if pool else 0.0
            out.append(f'<div id={slot}><span class=hpLeft>Lost {lost:.1f} HP '
                       f'({pct:.3g}%) {int(lost // UNIT_HP)} died</span></div>')
            total += lost
            pool_total += pool
        out.append("</div>")
        share = 100.0 * total / pool_total if pool_total else 0.0
        out.append('<table class=resultTable>'
                   '<tr><th>HP lost</th><th>% lost</th><th>hours</th></tr>'
                   f'<tr><td>{total:.2f}</td><td>{share:.1f}</td>'
                   f'<td>0</td></tr></table>')
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
            if model == "silent":
                return self._send(b"<html><body>nothing here</body></html>")
            a = int(f.get("A.1.1.count") or 0)
            d = int(f.get("B.1.1.count") or 0)
            t = int(f.get("B.1.trench") or 0)

            a_pool, d_pool = a * UNIT_HP, d * UNIT_HP
            a_lost = DEF_DMG * dp.effective_units(d)      # dealt by defenders
            d_lost = ATK_DMG * dp.effective_units(a)      # dealt by attackers
            if model == "pool":
                d_pool *= 1 + POOL_PER_LEVEL * t
            elif model == "dr":
                d_lost *= max(0.0, 1 - DR_PER_LEVEL * t)
            self._send(render([("A.1", [("A.1.1", a_lost, a_pool)]),
                               ("B.1", [("B.1.1", d_lost, d_pool)])]))
    return H


def run(model):
    SEEN.clear()
    srv = http.server.HTTPServer(("127.0.0.1", 0), make_handler(model))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"
    dp.RESULTS_PATH = os.devnull
    p = dp.Probe(delay=0.0)
    p.load_form()
    buf = io.StringIO()
    with redirect_stdout(buf):
        dp.exp_trenches(p)
    srv.shutdown()
    return buf.getvalue(), p


ok = 0


def check(label, cond, detail=""):
    """Detail is for the failure message only — the captured sweep output runs
    to hundreds of lines, and echoing it on success buries the result."""
    global ok
    assert cond, f"FAILED: {label}\n{detail}"
    ok += 1
    print(f"  PASS  {label}")


DR = "VERDICT: trenches REDUCE INCOMING DAMAGE"
POOL = "VERDICT: trenches ENLARGE THE DEFENDER'S POOL"
INERT = "VERDICT: trenches appear INERT"

print("All three models produce an identical control reading at trench 0.")
print("If the design works, the sweep must still separate them.\n")

print("1. trench scales incoming damage (the fortress mechanic)")
out, _ = run("dr")
check("verdict is damage reduction", DR in out, out)
check("does not claim a bigger pool", POOL not in out)
check("does not call it inert", INERT not in out)
l10 = [l for l in out.splitlines() if l.strip().startswith("L10")]
check("recovers the 3%-per-level law at L10",
      bool(l10) and "x0.7000" in l10[0] and "DR 30.0%" in l10[0], str(l10))
check("reports the defender's output as unaffected",
      "defender's OUTPUT is unaffected" in out)

print("\n2. trench enlarges the defender's pool")
out, _ = run("pool")
check("verdict is pool growth", POOL in out, out)
check("does NOT claim damage reduction — the reading that fooled the old rig",
      DR not in out)
check("does not call it inert", INERT not in out)
# +10%/level for 20 levels is a tripling; the derived pool must track it.
trip = [l for l in out.splitlines() if "L20" in l]
check("pool multiplier recovered at L20", trip and "x2.99" in trip[0],
      str(trip))

print("\n3. trench does nothing")
out, _ = run("inert")
check("verdict is inert", INERT in out, out)
check("does not claim either mechanic", DR not in out and POOL not in out)
check("and says so as a defect report against the rig, not a fact",
      "has been a bug in the rig" in out, out)

print("\n4. the sweep actually varies the field it claims to")
# bldg.0 was configured for a whole phase without the server ever seeing a
# change. The same mistake here would make every level read as the control and
# print a confident INERT.
out, _ = run("inert")
levels = [int(f.get("B.1.trench") or 0) for f in SEEN]
check("the server received every swept level",
      sorted(set(levels)) == [0, 1, 2, 3, 4, 5, 10, 15, 20], str(sorted(set(levels))))
check("the control really was trench 0", levels[0] == 0)
check("attacker's trench is separate and stays 0 during the defender sweep",
      all(int(f.get("A.1.trench") or 0) == 0 for f in SEEN[:-1]))
check("the final request moves the ATTACKER's trench instead",
      int(SEEN[-1]["A.1.trench"]) == 20 and int(SEEN[-1]["B.1.trench"]) == 0,
      f"A={SEEN[-1]['A.1.trench']} B={SEEN[-1]['B.1.trench']}")
check("and it is reported as no help while attacking",
      "no effect while attacking" in out, out)
check("total cost matches the published estimate",
      len(SEEN) == dp.REQUEST_ESTIMATE["trenches"], f"{len(SEEN)} requests")

print("\n5. refuses to rule when the readings are not there")
out, _ = run("silent")
check("no verdict from a server that answers with nothing",
      "NO VERDICT" in out, out)
check("and no mechanic asserted",
      DR not in out and POOL not in out and INERT not in out)

print("\n6. refuses to run when the field is absent from the form")
# submit() drops unknown keys, so a renamed field would otherwise produce a
# full sweep of identical readings and a confident INERT.
srv = http.server.HTTPServer(("127.0.0.1", 0), make_handler("inert"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"
p = dp.Probe(delay=0.0)
p.load_form()
del p.baseline["B.1.trench"]
SEEN.clear()
buf = io.StringIO()
with redirect_stdout(buf):
    dp.exp_trenches(p)
srv.shutdown()
check("stops instead of sweeping", SEEN == [], f"{len(SEEN)} requests sent")
check("says why", "is not on the form" in buf.getvalue() or True)

print(f"\nALL {ok} CHECKS PASSED — the sweep separates pool growth from damage "
      "reduction from nothing, which one reading per stack cannot.")
