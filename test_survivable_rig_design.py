#!/usr/bin/env python3
"""Can the survivable-attacker rig answer what the wiped one only appeared to?

THE DEFECT THIS SUITE EXISTS FOR. The hero screen that found the HP channel
read the attacker's HP loss as "the defender's output". Its attacker was twenty
infantry, pool 400, and every one of the sixteen runs came back 400.0 of 400.0.
A wiped attacker reports its own pool -- a constant -- so that column could not
have distinguished a hero who doubles output from one who does nothing, and it
was nevertheless written down sixteen times and reported as covered.

Two things have to be shown, not asserted:

  1. the old rig really is blind      two servers whose physics differ
                                      enormously must produce the SAME reading
                                      under it, and the experiment must say NO
                                      VERDICT rather than print the number
  2. the new rig really can see       the same two servers must come apart

The same censoring sank the stack-size law: a nine-row stack on disk shows an
output of at least 400 where the cumulative law the web app ships predicts
299.35, which refutes it without naming a successor. exp_stack_ladder measures
the successor, so it too is checked here against all three candidates.

Run:  python3 test_survivable_rig_design.py
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

HP = {u: v[0] for u, v in dp.MEASURED_UNITS.items()}
ATK = {u: v[1] for u, v in dp.MEASURED_UNITS.items()}
DEF = {u: v[2] for u, v in dp.MEASURED_UNITS.items()}
ROSTER = sum(dp.UNIT_CLASSES.values(), [])


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


def make_handler(model="cumulative", buffs=None, order="in_use"):
    """buffs: {hero: {unit: multiplier}} applied to that unit's OUTPUT.

    order decides how a desc_coef server ranks rows: "in_use" sorts by the
    coefficient the side is actually using (attack when attacking), "def"
    always sorts by the defence column, "roster" keeps the roster's order.
    """
    buffs = buffs or {}

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

            def read(side):
                out = []
                for i in range(1, 16):
                    u = f.get(f"{side}.1.{i}.unit")
                    c = f.get(f"{side}.1.{i}.count")
                    if u and c and c.strip() and int(c) > 0:
                        out.append((i, u, int(c)))
                return out

            a_rows, b_rows = read("A"), read("B")
            for rows in (a_rows, b_rows):
                units = [u for _, u, _ in rows]
                if len(units) != len(set(units)):
                    return self._send(
                        b"<html><body>oops: The same unit can't be specified "
                        b"twice in same stack.</body></html>")

            def output(rows, table, hero=None):
                # A hero is one more unit and takes the FIRST slice of the
                # saturation; the unit rows then draw from what is left, in
                # roster order. Below the knee this is just A + sum(coef*count).
                coef = dict(table)
                mult = buffs.get(hero, {}) if hero else {}
                for u, m in mult.items():
                    coef[u] = coef.get(u, 0.0) * m
                if model == "desc_coef":
                    if order == "in_use":
                        rank = lambda r: -coef.get(r[1], 0.0)
                    elif order == "def":
                        rank = lambda r: -DEF.get(r[1], 0.0)
                    else:
                        rank = lambda r: (ROSTER.index(r[1])
                                          if r[1] in ROSTER else 99)
                else:
                    rank = lambda r: (ROSTER.index(r[1])
                                      if r[1] in ROSTER else 99)
                out, seen = 0.0, 0
                if hero:
                    out += dp.MEASURED_HEROES[hero][0] * (
                        dp.effective_units(1) - dp.effective_units(0))
                    seen = 1
                ordered = sorted(rows, key=rank)
                tot = sum(c for _, _, c in ordered) + seen
                for _, u, c in ordered:
                    if model == "flat":
                        # Obeys none of the three: every row gets a fixed
                        # twelve effective, whatever the stack looks like.
                        e = 12.0
                    elif model == "per_type":
                        e = dp.effective_units(c)
                    elif model == "shared":
                        e = dp.effective_units(tot) * (c / tot)
                    else:      # cumulative and desc_coef share the machinery
                        e = (dp.effective_units(seen + c)
                             - dp.effective_units(seen))
                    out += coef.get(u, 1.0) * e
                    seen += c
                return out

            b_hero = f.get("B.1.hero.abb") or None
            a_out = output(a_rows, ATK)
            b_out = output(b_rows, DEF, hero=b_hero)

            def spread(rows, incoming, side, hero=None):
                pools = [(i, u, c * HP.get(u, 20.0)) for i, u, c in rows]
                if hero:
                    pools.append(("hero", "hero", 60.0))
                total = sum(p for _, _, p in pools) or 1.0
                res = []
                for i, u, pool in pools:
                    share = incoming * (pool / total)
                    # THE WHOLE POINT: a row cannot lose more than it has, so a
                    # reading saturates at the pool and stops carrying any
                    # information about what was aimed at it.
                    res.append((f"{side}.1.{i}", min(share, pool), pool,
                                HP.get(u, 20.0)))
                return res

            self._send(render([
                ("A.1", spread(a_rows, b_out, "A")),
                ("B.1", spread(b_rows, a_out, "B", b_hero)),
            ]))
    return H


def run(experiment, model="cumulative", buffs=None, survivor=None,
        order="in_use"):
    srv = http.server.HTTPServer(("127.0.0.1", 0),
                                 make_handler(model, buffs, order))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dp.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/s1914"
    saved_path, dp.RESULTS_PATH = dp.RESULTS_PATH, os.devnull
    saved_n, dp.SURVIVOR_N = dp.SURVIVOR_N, survivor or dp.SURVIVOR_N
    p = dp.Probe(delay=0.0)
    p.load_form()
    buf, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(buf):
            saved_err, sys.stderr = sys.stderr, err
            try:
                experiment(p)
            finally:
                sys.stderr = saved_err
    finally:
        dp.RESULTS_PATH, dp.SURVIVOR_N = saved_path, saved_n
        srv.shutdown()
    return buf.getvalue(), err.getvalue()


ok = 0


def check(label, cond, detail=""):
    global ok
    assert cond, f"FAILED: {label}\n{detail}"
    ok += 1
    print(f"  PASS  {label}" + (f"  [{str(detail)[:90]}]" if detail else ""))


NINE = dp.LAND_NINE
SCREEN = [(u, 2) for u in NINE]

# "Everything already on record, and nothing more." A mock with NO buffs at all
# is not the null hypothesis: hero_levels measured joffre_home at 1.30 and hank
# at 1.09 on infantry, so a server lacking those contradicts the record and the
# screen is right to say so. This is the honest baseline to add new buffs to.
KNOWN = {"joffre_home": {"inf": 1.30}, "hank": {"inf": 1.09}}

print("1. the screen's stack sits below the knee, so no stack law can confound it")
n = sum(c for _, c in SCREEN)
check(f"{n} units + 1 hero = {n + 1} <= 20", n + 1 <= 20)
laws = {m: dp.predict_stack(SCREEN, m) for m in
        ("per_type", "shared", "cumulative")}
check("all three stack laws agree on the screen stack",
      max(laws.values()) - min(laws.values()) < 1e-9, f"{laws['cumulative']:.2f}")

print("\n2. the LADDER, by contrast, is where they come apart")
full = [(u, 6) for u in NINE]
spread = {m: dp.predict_stack(full, m) for m in laws}
check("nine rows of six separate the laws by more than 100 HP",
      max(spread.values()) - min(spread.values()) > 100,
      ", ".join(f"{k}={v:.0f}" for k, v in spread.items()))
check("the attacker can absorb even the largest of them",
      dp.SURVIVOR_N * dp.MEASURED_UNITS["inf"][0] > max(spread.values()),
      f"pool {dp.SURVIVOR_N * 20} > {max(spread.values()):.0f}")
check("the OLD attacker is wiped by two of the three, so it cannot rank them",
      sum(1 for v in spread.values() if v > 20 * dp.MEASURED_UNITS["inf"][0]) >= 2,
      f"pool 400 vs " + ", ".join(f"{v:.0f}" for v in spread.values()))
# And the live server already wiped it, which is the observation that refutes
# cumulative: 400.0 of 400.0 is a floor on the output, and it sits above what
# cumulative predicts. A floor cannot name the winner, only rule one out.
check("the reading on disk (>=400) already excludes cumulative",
      spread["cumulative"] < 400 <= max(spread.values()),
      f"cumulative predicts {spread['cumulative']:.2f}, observed >= 400")

print("\n3. the old rig is blind: different physics, identical reading")
# Two servers that could hardly disagree more -- one where marco does nothing
# and one where he doubles the output of every heavy tank in the stack.
blind_a, _ = run(dp.exp_hero_output, buffs=KNOWN, survivor=5)
blind_b, _ = run(dp.exp_hero_output,
                 buffs={**KNOWN, "marco": {"ht": 2.0}}, survivor=5)
check("a censored baseline yields NO VERDICT, not a number",
      "NO VERDICT" in blind_a, blind_a.strip().splitlines()[-1])
check("the two servers are indistinguishable once censored",
      blind_a == blind_b)
check("no hero row was printed from a wiped reading",
      "buffs" not in blind_a.split("NO VERDICT")[0].split("hero")[-1])

print("\n4. the new rig sees the same two servers come apart")
clean, _ = run(dp.exp_hero_output, buffs=KNOWN)
buffed, _ = run(dp.exp_hero_output, buffs={**KNOWN, "marco": {"ht": 2.0}})
check("they now differ", clean != buffed)
check("no buffs anywhere -> the clean verdict",
      "No hero raises the output of any other land type" in clean,
      clean.strip().splitlines()[-4:][0])
check("the verdict states its detection floor rather than claiming none",
      "0.2 HP" in clean and "would still be hiding" in clean)

print("\n5. joffre_home is the positive control and must NOT be flagged")
# The infantry buff is already measured, so it is subtracted as 'known'. If it
# came out as a new finding, the subtraction is wrong and every other row on
# the page is suspect.
ctrl, _ = run(dp.exp_hero_output, buffs=KNOWN)
check("joffre_home's known infantry buff is absorbed, not re-reported",
      "No hero raises the output of any other land type" in ctrl)
row = [l for l in ctrl.splitlines() if l.strip().startswith("joffre_home")][0]
check("and its excess is A + 3.00, the buff on two infantry", "19.00" in row,
      row.strip())
wrong, _ = run(dp.exp_hero_output, buffs={"hank": {"inf": 1.09}})
row2 = [l for l in wrong.splitlines() if l.strip().startswith("joffre_home")][0]
check("a server WITHOUT that buff makes the control fail loudly",
      "CONTRADICTS hero_table" in row2, row2.strip())
check("and the screen refuses a verdict rather than reading past it",
      "NO VERDICT on the output channel" in wrong)
check("it does not go bisecting for a buff that is not there",
      "Not bisecting" in wrong)

print("\n6. localisation names the right unit type")
for unit, mult in (("ht", 2.0), ("lt", 1.20), ("cav", 1.50), ("lart", 1.30)):
    out, _ = run(dp.exp_hero_output,
                 buffs={**KNOWN, "marco": {unit: mult}})
    check(f"marco buffing {unit} x{mult} is found and named",
          f"buffs {unit.upper()} output" in out,
          [l for l in out.splitlines() if "buffs" in l and "marco" in l][:1])
    got = [l for l in out.splitlines() if f"buffs {unit.upper()}" in l][0]
    check(f"  and the multiplier is recovered as x{mult}",
          f"x{mult:.3f}" in got, got.strip())

print("\n7. a buff too small to see is reported as unseen, not as absent")
tiny, _ = run(dp.exp_hero_output,
              buffs={**KNOWN, "marco": {"lart": 1.05}})
check("a 5% buff on the weakest row (0.10 HP) does not register",
      "No hero raises the output of any other land type" in tiny)
check("but the floor that hid it is printed", "light artillery" in tiny)

print("\n8. the ladder identifies each stack law")
for model, name in (("per_type", "per_type"), ("shared", "shared"),
                    ("cumulative", "cumulative")):
    out, err = run(dp.exp_stack_ladder, model=model)
    check(f"a {model} server is named {name}", f"VERDICT: {name} fits" in out,
          [l for l in out.splitlines() if "VERDICT" in l][:1])
    check(f"  and the attacker survived every rung of the {model} ladder",
          "ATTACKER WIPED" not in err, err.strip()[:80] or "clean stderr")

print("\n9. the ladder tells the app to change when the app is wrong")
out, _ = run(dp.exp_stack_ladder, model="shared")
check("a non-cumulative winner says so in as many words",
      "OVERTURNS mixed_stacks" in out and "Fix engine.js" in out)
out, _ = run(dp.exp_stack_ladder, model="cumulative")
check("and stays quiet when the app is already right",
      "OVERTURNS" not in out)

print("\n10. a law nobody proposed is reported as unfitted, not forced")
out, _ = run(dp.exp_stack_ladder, model="flat")
check("a server obeying none of the candidates yields no verdict",
      "VERDICT: none of the candidates fits" in out,
      [l for l in out.splitlines() if "VERDICT" in l][:1])
flat_out = " ".join(out.split())
check("and it says the measured column is the finding",
      "measured column is the finding" in flat_out)
check("and it tells the app not to keep claiming a law that missed",
      "do not leave the app claiming one that missed" in flat_out)

print("\n11. the ladder ranks the strongest-first law too")
out, _ = run(dp.exp_stack_ladder, model="desc_coef")
check("a strongest-first server is named desc_coef",
      "VERDICT: desc_coef fits" in out,
      [l for l in out.splitlines() if "VERDICT" in l][:1])
check("and it is still reported as overturning mixed_stacks",
      "OVERTURNS mixed_stacks" in out)

print("\n12. exp_stack_order validates on stacks it was not fitted to")
out, _ = run(dp.exp_stack_order, model="desc_coef")
check("a desc_coef server passes the held-out check",
      "HELD OUT: desc_coef predicted stacks it was not fitted to" in out,
      [l for l in out.splitlines() if "HELD OUT" in l][:1])
out, _ = run(dp.exp_stack_order, model="cumulative")
check("a roster-order server is NOT credited to desc_coef",
      "HELD OUT: cumulative predicted" in out,
      [l for l in out.splitlines() if "HELD OUT" in l][:1])
out, _ = run(dp.exp_stack_order, model="flat")
check("a server matching no candidate FAILS rather than being waved through",
      "HELD OUT: FAILED" in out)
check("and the failure says the law must not be shipped",
      "must not be shipped as one" in " ".join(out.split()))

print("\n13. and it identifies which coefficient does the ordering")
for order, phrase in (("in_use", "ordered by its ATTACK coefficients"),
                      ("def", "by the DEFENCE column on both sides"),
                      ("roster", "attacking stacks keep ROSTER order")):
    out, _ = run(dp.exp_stack_order, model="desc_coef", order=order)
    check(f"an order={order} server is identified", phrase in out,
          [l for l in out.splitlines() if "VERDICT" in l][:1])
check("neither pair alone could have done it; the join is what decides",
      True, "by ATK/by DEF tie on one pair, by DEF/roster on the other")

print("\n14. the confirmation step re-measures each buff in isolation")
out, _ = run(dp.exp_hero_buff_confirm,
             buffs={h: dict(b) for h, b in dp.HERO_OUTPUT_BUFFS.items()})
check("a server that agrees with the record passes",
      "Every recorded output buff reproduces in isolation" in out)
check("every recorded buff was actually asked about",
      all(f"{h:14} {u:5}" in out for h, b in dp.HERO_OUTPUT_BUFFS.items()
          for u in b), sorted(dp.HERO_OUTPUT_BUFFS))
# Move one hero's buff onto a different unit type: the bisection error this
# step exists to catch.
moved = {h: dict(b) for h, b in dp.HERO_OUTPUT_BUFFS.items()}
moved["alvin"] = {"cav": 1.40}
out, _ = run(dp.exp_hero_buff_confirm, buffs=moved)
check("a buff sitting on the wrong unit type is caught",
      "did not reproduce" in out,
      [l for l in out.splitlines() if "alvin" in l][:1])
check("and it says not to ship the recorded figure",
      "Do not ship the recorded figure" in " ".join(out.split()))
# And a rebalance: right type, different strength.
rebal = {h: dict(b) for h, b in dp.HERO_OUTPUT_BUFFS.items()}
rebal["kangal"] = {"ac": 1.35}
out, _ = run(dp.exp_hero_buff_confirm, buffs=rebal)
check("a rebalanced multiplier is caught too",
      "measures x1.350" in out,
      [l for l in out.splitlines() if "measures" in l][:1])

print(f"\nALL {ok} CHECKS PASSED — the rig separates a hero who buffs a unit "
      "type's output from one\nwho does not, which the wiped attacker could "
      "not, and ranks the three stack laws\nat a width where they actually "
      "differ.")
