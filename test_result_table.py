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
# THIS ASSERTION USED TO READ  == ["A.1", "B.1"]  under the label "one summary
# per stack", and it passed for 2,585 readings. It was wrong the whole time.
# There is exactly ONE resultTable per ARMY, and every army in this project had
# exactly one stack, so an army total and a stack total were the same number
# and nothing could tell them apart. exp_multi_stack fielded two stacks a side
# and the difference showed instantly: the table after A.2 carries A.1 + A.2.
#
# The old assertion was not a bad test. It was an accurate record of what was
# known, and it went stale in exactly the way a hand-written constant goes
# stale -- which is the whole reason this file exists. Keeping the label while
# quietly widening the list would have hidden that; the label changes too.
check("one summary per ARMY, plus a stack alias where that is unambiguous",
      sorted(s.summaries) == ["A", "A.1", "B", "B.1"], str(sorted(s.summaries)))
check("the alias is the same object's values, not a second reading",
      s.summaries["A"] == s.summaries["A.1"])
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

print("\n9. TWO STACKS AN ARMY: the table is an army total")
# multi_stack_response.html is a genuine response from the exp_multi_stack run,
# with A.1+A.2 attacking B.1+B.2. It is the first capture in this project where
# an army total and a stack total are different numbers, so it is the only
# evidence that can tell the two apart -- which is why it is committed as a
# fixture rather than left in a scratch directory.
MULTI = open(os.path.join(HERE, "multi_stack_response.html")).read()
m = dp.StackSummaryScraper()
m.feed(MULTI)
check("two stacks an army yields two tables, not four",
      sorted(m.summaries) == ["A", "B"], str(sorted(m.summaries)))
check("no stack alias when the army has more than one stack",
      "A.1" not in m.summaries and "A.2" not in m.summaries)
md = details_of(MULTI)
check("all four stacks reported their own spans",
      sorted(md) == ["A.1.1", "A.2.1", "B.1.1", "B.2.1"], str(sorted(md)))
# THE ARITHMETIC THAT SETTLES IT. If the table were a stack total, the one
# following A.2 would say 90. It says 190, which is A.1's 100 plus A.2's 90.
check("A's table equals A.1 + A.2, not A.2 alone",
      m.summaries["A"]["hp_lost"] == md["A.1.1"]["lost"] + md["A.2.1"]["lost"]
      == 190.0, str(m.summaries["A"]["hp_lost"]))
check("B's table likewise",
      m.summaries["B"]["hp_lost"] == md["B.1.1"]["lost"] + md["B.2.1"]["lost"]
      == 80.0, str(m.summaries["B"]["hp_lost"]))
check("and the percentage is over the army's pool, not one stack's",
      abs(m.summaries["A"]["pct_lost"] - 100 * 190.0 / 400.0) < 0.05,
      str(m.summaries["A"]["pct_lost"]))
check("'hours' is an army total too, so it cannot be billed per stack",
      (m.summaries["A"]["hours"], m.summaries["B"]["hours"]) == (31.0, 13.0))
# The site said so all along, in a title attribute nobody had read: "The total
# hit points lost by all the stacks during the battle." Recorded here because a
# claim the source itself makes is worth more than an inference from arithmetic
# -- and because it is the reason to trust this beyond the one capture.
check("the site's own tooltip says 'all the stacks'",
      "lost by all the stacks" in MULTI)

print("\n10. the army total is cross-checked, never divided")
mref = dp.refine_details(md, m.summaries)
check("no substitution: the total is real but not divisible between stacks",
      all("lost_source" not in mref[s] for s in mref), str(mref))
check("spans survive untouched",
      [mref[s]["lost"] for s in sorted(mref)] == [100.0, 90.0, 40.0, 40.0])
# The guard has to survive the new key shape. Swap the two armies' totals and
# it must still refuse -- this is the building-row bug's exact shape, one level
# up, and the sum check is the only thing standing in front of it.
mswap = {"A": m.summaries["B"], "B": m.summaries["A"]}
mout = dp.refine_details(md, mswap, quiet=True)
check("a table attached to the wrong ARMY is refused too",
      [mout[s]["lost"] for s in sorted(mout)] == [100.0, 90.0, 40.0, 40.0])
# And an army whose two stacks between them show ONE unit row can still be
# sharpened: the total is divisible when there is only one thing to divide it
# into. A.2 empty, A.1 carrying the reading.
one = {"A.1.1": {"lost": 190.0, "pct": 47.5, "pool": 400.0}}
sharp = dp.refine_details(one, {"A": {"hp_lost": 190.04, "hours": 31.0}},
                          quiet=True)
check("one unit row under a two-stack army is still refined",
      sharp["A.1.1"]["lost"] == 190.04 and sharp["A.1.1"]["lost_source"] == 1.0)
check("and its stack extras come from the army row",
      sharp["A.1.1"]["stack_hours"] == 31.0)

print("\n11. the '% lost' header changed spelling mid-project")
# fortress_result.html was served "% lost"; multi_stack_response.html was served
# "%lost", and the site had added an "HP final" column in between. A literal
# header match filed the same quantity under two different keys -- 'pct_lost'
# on the early captures, 'lost' on the later ones -- and 'lost' is already the
# span reading's name for HP. Nothing had read it yet, so nothing on disk is
# wrong; the risk was entirely in front of us.
check("the two fixtures really do spell it differently",
      "% lost" in REAL and "%lost" in MULTI and "% lost" not in MULTI)
check("both spellings now land on the same key",
      "pct_lost" in s.summaries["A.1"] and "pct_lost" in m.summaries["A"])
check("neither files a percentage under 'lost'",
      "lost" not in s.summaries["A.1"] and "lost" not in m.summaries["A"])
check("the column the site added later arrived as data, not as a discard",
      m.summaries["A"]["hp_final"] == 210.0)
check("HP final + HP lost is the army's opening pool",
      m.summaries["A"]["hp_final"] + m.summaries["A"]["hp_lost"] == 400.0)
# Rows captured before the fix keep the key they were captured with. Reading
# them is a function's job, not a rewrite's.
check("the compatibility reader handles the old spelling",
      dp.summary_pct_lost({"lost": 0.4}) == 0.4)
check("and prefers the explicit key when both are somehow present",
      dp.summary_pct_lost({"lost": 0.4, "pct_lost": 47.5}) == 47.5)
check("and returns None rather than guessing when neither is there",
      dp.summary_pct_lost({"hp_lost": 1.0}) is None)

print(f"\nALL {ok} CHECKS PASSED")
