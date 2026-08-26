# Calibration fixtures

Ground-truth dxcalc responses captured during development, one request each.

## dxcalc-10inf2art-vs-12inf

`*.body.txt` is the exact urlencoded body `buildDxcalcPayload` produced
(10 inf + 2 art attacking 12 defending inf, land, maxRounds 100);
`*.html` is what dxcalc.com/s1914 returned (2026-08-25).

What it established:

- The export payload is accepted end-to-end: the response carries `hpLeft`
  results, so the synthesized field set + `MainSubmitButton` marker are right.
- Infantry HP is 20 per unit: the 12-inf pool reads back as 240 HP.
- **Attack ≠ defense.** dxcalc has the 12 defending infantry winning
  (attacker loses all 240 HP; defender loses 175.9 of 240), while equal
  attack/defense values predict the attacker winning. Per-unit defense
  values are a separate, unmeasured table — the next thing the probe
  should sweep (fixed 1-attacker duels against a defending stack, reading
  the attacker's HP loss per round).
