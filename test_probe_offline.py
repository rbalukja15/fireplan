#!/usr/bin/env python3
"""Offline verification of the multipart fix.

Serves the REAL captured dxcalc form (last_response.html) from localhost and
replicates the server behaviour we inferred: a POST whose body it cannot parse
falls through to re-rendering the bare form. Then drives the actual Probe class
against it end to end.
"""
import http.server
import os
import sys
import threading
from email.parser import BytesParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxcalc_probe as dp

FORM_HTML = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_response.html"), "rb").read()

RESULTS_HTML = b"""<html><body>
<div id="A.1.1">inf <span class="hpLeft">1120.5</span></div>
<div id="B.1.1">inf <span class="hpLeft">0.0</span></div>
</body></html>"""

received = {}


def parse_multipart(body: bytes, content_type: str) -> dict:
    msg = BytesParser().parsebytes(
        b"Content-Type: " + content_type.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
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
        # This is the modelled dxcalc behaviour: anything it cannot parse as
        # multipart yields the stock form, with no error of any kind.
        try:
            fields = parse_multipart(body, ctype)
        except Exception:
            received["mode"] = "unparsed -> bare form"
            return self._send(FORM_HTML)
        received["mode"] = "multipart parsed"
        received["fields"] = fields
        if "MainSubmitButton" not in fields:
            received["mode"] = "no marker -> bare form"
            return self._send(FORM_HTML)
        self._send(RESULTS_HTML)


srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

dp.BASE_URL = f"http://127.0.0.1:{port}/s1914"

print("=" * 68)
print("TEST 1 — encoder round-trips through a real multipart parser")
print("=" * 68)
sample = {"A.1.1.count": "75", "A.1.1.hp": "100%", "A.1.terrain": "land",
          "MainSubmitButton": "Start Battle", "A.1.target": "B.1"}
body, ctype = dp.encode_multipart(sample)
back = parse_multipart(body, ctype)
assert back == sample, f"MISMATCH\n got {back}\n want {sample}"
print(f"  {len(sample)} fields survived encode->parse byte-identical  OK")

print()
print("=" * 68)
print("TEST 2 — scraper reads the real form")
print("=" * 68)
p = dp.Probe(delay=0.0)
baseline = p.load_form()
print(f"  fields discovered : {len(baseline)}")
print(f"  post_url          : {p.post_url}")
print(f"  enctype           : {p.form_enctype}")
assert "multipart" in p.form_enctype, "enctype not detected!"
assert p.submit_marker == ("MainSubmitButton", "Start Battle"), p.submit_marker
print("  marker + enctype both recovered from live HTML  OK")

print()
print("=" * 68)
print("TEST 3 — end-to-end submit() against the modelled server")
print("=" * 68)
out = p.submit({"A.1.1.count": "50"})
print(f"  server saw        : {received['mode']}")
print(f"  fields received   : {len(received.get('fields', {}))}")
print(f"  readings parsed   : {out}")
assert out == {"A.1.1": 1120.5, "B.1.1": 0.0}, out
assert received["fields"]["A.1.1.count"] == "50", "override did not survive"
print("  override applied and hpLeft parsed  OK")

print()
print("=" * 68)
print("TEST 4 — the regression: urlencoded reproduces the reported symptom")
print("=" * 68)
p2 = dp.Probe(delay=0.0)
p2.load_form()
p2.form_enctype = "application/x-www-form-urlencoded"   # pre-fix behaviour
try:
    p2.submit({"A.1.1.count": "50"})
    print("  !! unexpectedly succeeded")
except dp.BareFormReturned as e:
    print(f"  server saw        : {received['mode']}")
    print(f"  raised            : BareFormReturned")
    print("  pre-fix path reproduces 'bare form, no oops' exactly  OK")

print()
print("ALL TESTS PASSED")
srv.shutdown()
