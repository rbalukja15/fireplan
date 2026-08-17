#!/usr/bin/env python3
"""The per-stack summary table, checked against the real captured response.

fortress_result.html is a genuine response from dxcalc.com, so these are not
assertions about a mock — they are assertions about markup the site actually
served. Two claims are being tested:

  1. The table carries more precision than the span it sits beside, and
     combining the table's HP with the span's percentage gives a better pool
     (hence a better max HP) than either source alone.

  2. The stack/table association is CHECKED rather than assumed. A building
     row inheriting the wrong slot cost this project its whole first phase,
     and the failure mode was invisible because the numbers still looked
     plausible. A table attached to the wrong stack would look plausible too,
     so refine_details() must refuse when the spans it claims to summarise do
     not add up to it.

Run:  python3 test_result_table.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dxcalc_probe as dp

REAL = open(os.path.join(HERE, "fortress_result.html")).read()
FORM = open(os.path.join(HERE, "last_response.html")).read()

ok = 0


def check(label, cond, detail=""):
    global ok
    assert cond, f"FAILED: {label} {detail}"
    ok += 1
    print(f"  PASS  {label}" + (f"  [{detail}]" if detail else ""))


def details_of(html):
    r = dp.ResultScraper()
    r.feed(html)
    return {k: v for k, v in
            ((k, dp.parse_reading(t)) for k, t in r.readings.items()) if v}


print("1. the table exists in the real response and parses")
s = dp.StackSummaryScraper()
s.feed(REAL)
check("one summary per stack", sorted(s.summaries) == ["A.1", "B.1"],
      str(sorted(s.summaries)))
check("attacker HP lost carries the extra digit",
      s.summaries["A.1"]["hp_lost"] == 141.67, str(s.summaries["A.1"]["hp_lost"]))
check("defender likewise", s.summaries["B.1"]["hp_lost"] == 11.33)
check("percentage column read", s.summaries["A.1"]["pct_lost"] == 23.6)
check("resource columns kept, unexplained but recorded",
      s.summaries["A.1"]["iron"] == 0.0 and "gas" in s.summaries["A.1"])
check("'$0' is parsed as a number, not dropped",
      s.summaries["A.1"]["cash"] == 0.0)
check("'hours' differs per stack, so it is not a constant",
      (s.summaries["A.1"]["hours"], s.summaries["B.1"]["hours"]) == (23.0, 1.0))
check("no spurious extra data rows", s.extra_rows == {}, str(s.extra_rows))

print("\n2. the bare form has no result tables at all")
empty = dp.StackSummaryScraper()
empty.feed(FORM)
check("nothing invented from a page without results", empty.summaries == {},
      str(empty.summaries))

print("\n3. the table counts UNIT rows only")
# B.1 lost 11.3 HP of infantry and 8.5 HP of fortress. Its table says 11.33,
# so the building is excluded — which is why refine_details() must exclude
# delta-notation rows from the sum it checks.
d = details_of(REAL)
check("building row present and in delta notation",
      d["B.1.bldg.1"]["delta"] == 1.0 and d["B.1.bldg.1"]["lost"] == 8.5)
check("table total matches the unit span alone, not unit + building",
      abs(s.summaries["B.1"]["hp_lost"] - d["B.1.1"]["lost"]) < 0.05
      and abs(s.summaries["B.1"]["hp_lost"]
              - (d["B.1.1"]["lost"] + d["B.1.bldg.1"]["lost"])) > 8.0)

print("\n4. refinement sharpens the numbers it is there to sharpen")
ref = dp.refine_details(d, s.summaries)
check("attacker's HP lost upgraded from the span",
      (d["A.1.1"]["lost"], ref["A.1.1"]["lost"]) == (141.7, 141.67))
check("the span value is kept alongside, not discarded",
      ref["A.1.1"]["lost_span"] == 141.7)
check("substitution is marked, so results.jsonl says where a number came from",
      ref["A.1.1"]["lost_source"] == 1.0)
check("building row left alone — a stack total cannot refine it",
      ref["B.1.bldg.1"] == d["B.1.bldg.1"])
# 30 infantry at 20 HP each is a 600 HP pool, known independently.
before = abs(d["B.1.1"]["pool"] - 600.0)
after = abs(ref["B.1.1"]["pool"] - 600.0)
check("pool moves closer to the known 600",
      after < before, f"{d['B.1.1']['pool']} -> {ref['B.1.1']['pool']}")
check("and by enough to matter to max HP", before / max(after, 1e-9) > 3,
      f"error {before:.2f} -> {after:.2f} HP")
check("per-unit max HP now within 0.1 of 20.0",
      abs(ref["B.1.1"]["pool"] / 30 - 20.0) < 0.1,
      f"{ref['B.1.1']['pool'] / 30:.4f}")
check("stack-level extras carried through",
      ref["A.1.1"]["stack_hours"] == 23.0)

print("\n5. THE GUARD: a table attached to the wrong stack is refused")
# The exact bug class that cost this project its first phase, in a new place.
swapped = {"A.1": s.summaries["B.1"], "B.1": s.summaries["A.1"]}
out = dp.refine_details(d, swapped, quiet=True)
check("no substitution when the spans do not sum to the table",
      out["A.1.1"]["lost"] == 141.7 and out["B.1.1"]["lost"] == 11.3,
      f"{out['A.1.1']['lost']}, {out['B.1.1']['lost']}")
check("and no lost_source claimed",
      "lost_source" not in out["A.1.1"] and "lost_source" not in out["B.1.1"])
# A near miss must still be accepted: spans round to 0.1, so a 0.05 gap per
# row is expected and is not evidence of anything.
near = {"A.1": dict(s.summaries["A.1"], hp_lost=141.74)}
out = dp.refine_details(d, near, quiet=True)
check("but ordinary span rounding is tolerated", out["A.1.1"]["lost"] == 141.74)

print("\n6. a stack with two live unit rows keeps its spans")
two = {"A.1.1": {"lost": 60.0, "pct": 10.0, "pool": 600.0},
       "A.1.2": {"lost": 40.0, "pct": 20.0, "pool": 200.0}}
out = dp.refine_details(two, {"A.1": {"hp_lost": 100.0}}, quiet=True)
check("total is real but not divisible between them, so nothing is invented",
      (out["A.1.1"]["lost"], out["A.1.2"]["lost"]) == (60.0, 40.0))
check("no false mismatch warning either — the sum does agree",
      "lost_source" not in out["A.1.1"])

print("\n7. slot -> stack mapping")
check("unit slot", dp.stack_of("A.1.1") == "A.1")
check("building slot", dp.stack_of("B.1.bldg.1") == "B.1")
check("multi-digit stack index", dp.stack_of("B.12.3") == "B.12")
check("a stack id is not itself a slot", dp.stack_of("A.1") is None)

print("\n8. an unknown column is slugified, not dropped")
sc = dp.StackSummaryScraper()
sc.feed('<div id="A.1"><table class="resultTable">'
        '<tr><th>HP lost</th><th>Morale %</th></tr>'
        '<tr><td>10.5</td><td>7</td></tr></table></div>')
check("new column survives under a usable key",
      sc.summaries["A.1"].get("morale") == 7.0, str(sc.summaries))

print(f"\nALL {ok} CHECKS PASSED")
