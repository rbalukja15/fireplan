#!/usr/bin/env python3
"""Offline verification of the POST path. Never touches dxcalc.com.

Serves the REAL captured form (last_response.html) from localhost and models
the server behaviour that a live --sanity run actually demonstrated:

  * BOTH urlencoded and multipart bodies are accepted and parsed.
  * The submit marker MainSubmitButton is what decides whether the POST counts
    as an attack. Without it the server re-renders the bare form, with no
    results and no 'oops' — the silent failure that cost this project days.

Run:  python3 test_probe_offline.py
"""
import http.server
import os
import sys
import threading
import urllib.parse
from email.parser import BytesParser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dxcalc_probe as dp

FORM_HTML = open(os.path.join(HERE, "last_response.html"), "rb").read()

RESULTS_HTML = b"""<html><body>
<div id="A.1.1">inf <span class="hpLeft">50.0</span></div>
<div id="B.1.1">inf <span class="hpLeft">40.0</span></div>
</body></html>"""

seen = {}


def parse_multipart(body: bytes, content_type: str) -> dict:
    msg = BytesParser().parsebytes(
        b"Content-Type: " + content_type.encode()
        + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
    if not msg.is_multipart():
        raise ValueError("not multipart")
    out = {}
    for part in msg.get_payload():
        name = part.get_param("name", header="content-disposition")
        out[name] = part.get_payload(decode=True).decode("utf-8")
    return out


class Handler(http.server.BaseHTTPRequestHandler):
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
        body = self.rfile.read(n)
        ctype = self.headers.get("Content-Type", "")
        if "multipart" in ctype:
            fields = parse_multipart(body, ctype)
            seen["encoding"] = "multipart"
        else:
            fields = {k: v[0] for k, v in
                      urllib.parse.parse_qs(body.decode(),
                                            keep_blank_values=True).items()}
            seen["encoding"] = "urlencoded"
        seen["fields"] = fields
        # The one rule that actually matters.
        if "MainSubmitButton" not in fields:
            seen["outcome"] = "no marker -> bare form"
            return self._send(FORM_HTML)
        seen["outcome"] = "accepted"
        self._send(RESULTS_HTML)


srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"

ok = 0


def check(label, cond, detail=""):
    global ok
    assert cond, f"FAILED: {label} {detail}"
    ok += 1
    print(f"  PASS  {label}" + (f"  [{detail}]" if detail else ""))


print("0. result-span parsing, against text observed on the live site")
r = dp.parse_reading("Lost 50.0 HP (16.7%) 2 died")
check("lost/pct/died recovered",
      r == {"lost": 50.0, "pct": 16.7, "died": 2.0, "pool": 299.4}, str(r))
check("pool implies 20 HP/infantry over 15 units",
      abs(r["pool"] / 15 - 20.0) < 0.05, f"{r['pool'] / 15}")
r = dp.parse_reading("Lost 60.0 HP (30%) 3 died")
check("second stack agrees on 20 HP/infantry over 10 units",
      abs(r["pool"] / 10 - 20.0) < 0.05, f"{r['pool'] / 10}")
check("integer percent parses", r["pct"] == 30.0)
check("'all N died' phrasing parses",
      dp.parse_reading("Lost 100.0 HP (100%) all 1 died")["died"] == 1.0)
check("missing death clause is tolerated",
      "died" not in dp.parse_reading("Lost 12.5 HP (5%)"))
check("blank rows yield nothing",
      dp.parse_reading("no living units specified here") is None)
# A comma is a thousands separator here, never a decimal point. Reading it as
# a decimal point silently divides by 1000, and only on large stacks.
check("thousands separator survives",
      dp.parse_reading("Lost 1,375.1 HP (91.7%) 68 died")["lost"] == 1375.1)
check("parse_hp fallback survives it too",
      dp.parse_hp("Lost 1,375.1 HP") == 1375.1,
      str(dp.parse_hp("Lost 1,375.1 HP")))
# Buildings report as "-8.5 HP (17%) →": delta notation, different wording.
r = dp.parse_reading("-8.5 HP (17%) →")
check("building delta span parses", r is not None and r["delta"] == 1.0, str(r))
check("magnitude taken; the sign is notation, not a negative loss",
      r["lost"] == 8.5)
check("pool implies a level-1 fortress has 50 HP", r["pool"] == 50.0)
check("level 5 implies 250 HP",
      dp.parse_reading("-8.5 HP (3.4%) →")["pool"] == 250.0)
check("ascii arrow accepted too",
      dp.parse_reading("-8.5 HP (17%) ->") is not None)
# The row continues past the arrow and names the mechanic outright.
r = dp.parse_reading("-8.5 HP (3.4%) → LVL:5 41.5 HP; DR: 90% → 87.5%")
check("building level read off the page", r["level"] == 5.0)
check("top-level HP remaining read off the page", r["hp_top_level"] == 41.5)
check("damage reduction before/after captured",
      (r["dr_before"], r["dr_after"]) == (90.0, 87.5), str(r))
check("page's DR agrees with the fitted law m(5)=0.10",
      abs((100 - r["dr_before"]) / 100 - (0.85 - 0.15 * 5)) < 1e-9)
check("DR = 0.15*(HP/50+1) reproduces the post-damage value",
      abs(0.15 * ((250 - 8.5) / 50 + 1) * 100 - r["dr_after"]) < 0.06)

# Spans nest: the arrow is wrapped in its own <span>, and stopping at that
# inner </span> truncated the row before LVL/DR — which is where the answer was.
s = dp.ResultScraper()
s.feed('<div id="B.1.bldg.1"><span class="hpLeft">-8.5 HP (3.4%) '
       '<span style="font-size:large">&#8594;</span> LVL:5 41.5 HP; '
       'DR: 90% &#8594; 87.5%</span></div>')
check("nested span does not truncate the reading",
      "DR" in s.readings["B.1.bldg.1"], repr(s.readings["B.1.bldg.1"]))

# A building's result row must not overwrite a unit stack's. Its id is
# B.1.bldg.1, which the original SLOT_RE ignored, so it inherited A.1.1 and
# clobbered the attacker's reading throughout the fortress sweep.
s = dp.ResultScraper()
s.feed('<div id="A.1.1"><span class="hpLeft">Lost 141.7 HP (23.6%) 7 died</span></div>'
       '<div id="B.1.bldg.1"><span class="hpLeft">-8.5 HP (17%) &#8594;</span></div>'
       '<div id="B.1.1"><span class="hpLeft">Lost 79.3 HP (13.2%) 3 died</span></div>')
check("attacker's reading survives a building row",
      s.readings["A.1.1"].startswith("Lost 141.7"), repr(s.readings.get("A.1.1")))
check("building gets its own slot", s.readings["B.1.bldg.1"].startswith("-8.5"))
check("defender unaffected", s.readings["B.1.1"].startswith("Lost 79.3"))

print("\n1. multipart encoder round-trips through a real MIME parser")
sample = {"A.1.1.count": "10", "A.1.1.hp": "100%", "A.1.terrain": "land",
          "MainSubmitButton": "Start Battle", "A.1.target": "B.1"}
body, ctype = dp.encode_multipart(sample)
check("encode -> parse is lossless", parse_multipart(body, ctype) == sample)

print("\n2. scraper reads the real captured form")
p = dp.Probe(delay=0.0)
baseline = p.load_form()
check("field count", len(baseline) == 33, f"{len(baseline)} fields")
check("submit marker recovered",
      p.submit_marker == ("MainSubmitButton", "Start Battle"))
check("enctype observed", "multipart" in p.form_enctype, p.form_enctype)
check("but urlencoded is the default we send", p.encoding == "urlencoded")

print("\n3. urlencoded submit — the path proven against the live server")
u = dp.Probe(delay=0.0, encoding="urlencoded")
u.load_form()
r = u.submit({"A.1.1.count": "10"})
check("server accepted", seen["outcome"] == "accepted", seen["encoding"])
check("marker was sent",
      seen["fields"].get("MainSubmitButton") == "Start Battle")
check("override applied", seen["fields"]["A.1.1.count"] == "10")
check("readings parsed", r == {"A.1.1": 50.0, "B.1.1": 40.0}, str(r))

print("\n4. multipart submit — byte-faithful browser fallback")
mp = dp.Probe(delay=0.0, encoding="multipart")
mp.load_form()
r = mp.submit({"A.1.1.count": "10"})
check("server accepted", seen["outcome"] == "accepted", seen["encoding"])
check("same readings as urlencoded", r == {"A.1.1": 50.0, "B.1.1": 40.0}, str(r))

print("\n5. REGRESSION: dropping the submit marker silently returns the bare form")
nm = dp.Probe(delay=0.0)
nm.load_form()
nm.submit_marker = None          # simulate the original bug
try:
    nm.submit({"A.1.1.count": "10"})
    raise AssertionError("expected BareFormReturned")
except dp.BareFormReturned:
    check("BareFormReturned raised",
          seen["outcome"] == "no marker -> bare form")
    check("and no 'oops' anywhere in the body — the silent failure",
          "oops" not in nm.last_response.lower())

print(f"\nALL {ok} CHECKS PASSED")
srv.shutdown()
