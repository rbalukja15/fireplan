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


print("1. multipart encoder round-trips through a real MIME parser")
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
