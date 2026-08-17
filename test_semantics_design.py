#!/usr/bin/env python3
"""Does --semantics actually discriminate? Checked against both hypotheses.

An experiment that cannot distinguish its two candidate explanations is worse
than no experiment, because it returns a confident answer either way. So we
stand up two mock servers whose physics differ ONLY in what the hpLeft span
holds, tune both to reproduce the real observed 10v10 reading of A=50, B=40,
and require --semantics to reach the right verdict against each.

Both models fit the observed pair exactly. That is the whole point: one live
data point cannot separate them, and this proves the three-request design can.

Run:  python3 test_semantics_design.py
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

# Per-unit infantry damage under each model, chosen so that BOTH reproduce the
# real observed 10v10 result of A.1.1=50.0, B.1.1=40.0.
LOST_DEF_DMG, LOST_ATK_DMG = 5.0, 4.0          # reading = damage taken
REM_UNIT_HP = 10.0                              # reading = pool - damage taken
REM_DEF_DMG, REM_ATK_DMG = 5.0, 6.0


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
            atk = int(f.get("A.1.1.count") or 0)
            dfn = int(f.get("B.1.1.count") or 0)
            if model == "lost":
                a = dfn * LOST_DEF_DMG          # depends on OPPONENT only
                b = atk * LOST_ATK_DMG
            else:
                a = atk * REM_UNIT_HP - dfn * REM_DEF_DMG   # own pool - damage
                b = dfn * REM_UNIT_HP - atk * REM_ATK_DMG
            html = (f'<html><body>'
                    f'<div id="A.1.1"><span class="hpLeft">{a}</span></div>'
                    f'<div id="B.1.1"><span class="hpLeft">{b}</span></div>'
                    f'</body></html>')
            self._send(html.encode())
    return H


def run(model):
    srv = http.server.HTTPServer(("127.0.0.1", 0), make_handler(model))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"
    dp.RESULTS_PATH = os.devnull
    p = dp.Probe(delay=0.0)
    p.load_form()
    buf = io.StringIO()
    with redirect_stdout(buf):
        dp.semantics(p)
    srv.shutdown()
    return buf.getvalue()


ok = 0


def check(label, cond, detail=""):
    global ok
    assert cond, f"FAILED: {label}\n{detail}"
    ok += 1
    print(f"  PASS  {label}")


print("Both models are tuned to reproduce the real observation A=50.0, B=40.0.")
print("If the design works, --semantics must still tell them apart.\n")

print("1. server whose spans hold HP LOST")
out = run("lost")
base = [l for l in out.splitlines() if "baseline" in l][0]
check("reproduces the live 10v10 reading",
      "A.1.1=50.0" in base and "B.1.1=40.0" in base, base)
check("verdict is HP LOST", "VERDICT: hpLeft is HP LOST" in out, out)
check("recovers 4.0 attacking / 5.0 defending",
      "4.0 per unit attacking, 5.0 per unit defending" in out, out)

print("\n2. server whose spans hold HP REMAINING")
out = run("remaining")
base = [l for l in out.splitlines() if "baseline" in l][0]
check("reproduces the SAME live 10v10 reading",
      "A.1.1=50.0" in base and "B.1.1=40.0" in base, base)
check("verdict is NOT hp-lost", "VERDICT: NOT pure HP-lost" in out, out)
check("does not misreport a damage split",
      "per unit attacking" not in out, out)

print(f"\nALL {ok} CHECKS PASSED — the three requests separate the hypotheses "
      "that one request cannot.")
