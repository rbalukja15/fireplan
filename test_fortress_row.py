#!/usr/bin/env python3
"""The fortress sweep must configure bldg.1, not the hidden bldg.0 template.

Models the server behaviour that bytro.js implies: bldg.0 is a template every
browser submits on every request, so the server has to ignore it, and real
buildings live at bldg.1..N. Under that server the OLD sweep is provably
inert -- its control and its level-1 run are the same request -- and the fixed
sweep reads mitigation.

Run:  python3 test_fortress_row.py
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
BASE_LOSS = 120.0          # defender's HP lost with no fortress
MITIGATION = 0.10          # each fortress level cuts incoming damage by 10%
posts = []


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
        posts.append(f)
        # bldg.0 is the hidden template: present in every real submission and
        # therefore necessarily ignored. Only bldg.1.. are real buildings.
        level = 0
        for i in range(1, 13):
            if f.get(f"B.1.bldg.{i}.abb") == "fortress" and f.get(f"B.1.bldg.{i}.hp"):
                level = int(f.get(f"B.1.bldg.{i}.lvl") or 0)
                break
        lost = BASE_LOSS * (1 - MITIGATION) ** level
        pool = 30 * 20.0
        html = (f'<html><body>'
                f'<div id="A.1.1"><span class="hpLeft">'
                f'Lost 150.0 HP ({150 / pool * 100:.1f}%) 7 died</span></div>'
                f'<div id="B.1.1"><span class="hpLeft">'
                f'Lost {lost:.1f} HP ({lost / pool * 100:.1f}%) '
                f'{int(lost // 20)} died</span></div>'
                f'</body></html>').encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)


srv = http.server.HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"

rows = []
dp.record = lambda tag, meta, readings: rows.append({**meta, "r": readings})

p = dp.Probe(delay=0.0)
p.load_form()
buf = io.StringIO()
with redirect_stdout(buf):
    dp.exp_fortress(p)
out = buf.getvalue()
srv.shutdown()

ok = 0


def check(label, cond, detail=""):
    global ok
    assert cond, f"FAILED: {label}  {detail}"
    ok += 1
    print(f"  PASS  {label}" + (f"  [{detail}]" if detail else ""))


print("1. the hidden template is in the baseline, which is what broke this")
check("bldg.0 present on a plain GET",
      p.baseline.get("B.1.bldg.0.abb") == "fortress")
check("and it already carries level 1", p.baseline.get("B.1.bldg.0.lvl") == "1")

print("\n2. the sweep now writes to bldg.1")
treatments = [f for f in posts[1:]]
check("every treatment sets bldg.1.abb",
      all(f.get("B.1.bldg.1.abb") == "fortress" for f in treatments),
      f"{len(treatments)} treatment posts")
check("levels 1-5 all sent",
      [f["B.1.bldg.1.lvl"] for f in treatments] == ["1", "2", "3", "4", "5"])
check("bldg.1 carries HP too (a row without it is ignored)",
      all(f.get("B.1.bldg.1.hp") == "100%" for f in treatments))

print("\n3. the template is passed through untouched, as a browser would")
check("bldg.0 still sent on every request",
      all(f.get("B.1.bldg.0.abb") == "fortress" for f in posts))
check("control and level-1 are now genuinely different requests",
      posts[0].get("B.1.bldg.1.abb") is None
      and treatments[0].get("B.1.bldg.1.abb") == "fortress")

print("\n4. mitigation is actually measured")
levels = {r["level"]: r["r"].get("B.1.1") for r in rows}
check("control reads the unmitigated loss", levels[0] == BASE_LOSS, str(levels[0]))
check("L1 is 10% lower", abs(levels[1] - BASE_LOSS * 0.9) < 0.05, str(levels[1]))
check("L5 compounds to ~59%",
      abs(levels[5] - BASE_LOSS * 0.9 ** 5) < 0.05, str(levels[5]))
check("ratios reported below 1.0", "ratio 0.9000" in out and "mitigation" in out)

print("\n5. the raw span text is recorded, not just the extracted number")
check("every row carries raw span text",
      all("raw" in r and r["raw"] for r in rows))
check("raw text is the literal markup content",
      rows[1]["raw"]["B.1.1"].startswith("Lost "), repr(rows[1]["raw"]["B.1.1"]))
check("parsed breakdown stored beside it",
      "pct" in rows[1]["detail"]["B.1.1"])

print("\n6. the OLD code would have measured nothing against this same server")
# Reproduce the old behaviour: write to bldg.0, which the server ignores.
old_control = {k: v for k, v in posts[0].items()}
old_level1 = dict(old_control)
old_level1.update({"B.1.bldg.0.abb": "fortress", "B.1.bldg.0.lvl": "1",
                   "B.1.bldg.0.hp": "100%"})
check("old control already equalled its own level-1 payload",
      old_control == old_level1,
      "baseline already held fortress/1/100% at index 0")

print("\n7. a building destroyed in the round still parses")
# Verbatim from the live buildings sweep: a level-1 Recruiting Office has 5 HP
# and 30 infantry deal 8.5 to buildings, so it dies in the measured round. The
# row loses its arrow and LVL tail and spaces the minus off the number. The old
# DELTA_RE required the arrow, so this parsed as nothing and the sweep printed
# "NO ROW" — the same reading it gives for a type the server ignored entirely,
# which is precisely the distinction the buildings experiment exists to make.
dead = dp.parse_reading("- 5.0 HP (100%) destroyed")
check("parses at all — not None", dead is not None, repr(dead))
check("reads the magnitude past the spaced minus", dead["lost"] == 5.0)
check("reads the percentage", dead["pct"] == 100.0)
check("flags it destroyed", dead.get("destroyed") == 1.0)
check("still recovers the pool", dead["pool"] == 5.0)
check("carries no level or DR — the page prints neither",
      "level" not in dead and "dr_before" not in dead)

alive = dp.parse_reading("-8.5 HP (14.2%) → LVL:1 51.5 HP")
check("a surviving building is not flagged destroyed",
      "destroyed" not in alive, repr(alive))
check("and a fortress row still reads its DR",
      dp.parse_reading("-8.5 HP (5.67%) → LVL:3 41.5 HP; DR: 60% → 57.5%")
      ["dr_before"] == 60.0)
check("a unit row is untouched by the destroyed branch",
      dp.parse_reading("Lost 50.0 HP (16.7%) 2 died")["died"] == 2.0)

print(f"\nALL {ok} CHECKS PASSED")
