# dxcalc — Supremacy 1914 combat research & calculators

A research project that reverse-engineers the combat model behind
[dxter's Supremacy 1914 battle calculator](https://dxcalc.com/s1914) by
black-box measurement, plus two calculators built on what it measured.

| Piece | What it is |
| --- | --- |
| `dxcalc_probe.py` | The measurement rig: stdlib-only Python that submits controlled battles to dxcalc.com (politely throttled) and records readings to `results.jsonl` — 168+ rows, each one a real response. |
| `web/` | The **research calculator**: dependency-free, no build step, every constant tagged with its measurement provenance. Its test suite replays `results.jsonl` row by row. Deployed at `/research/`. |
| `app/` | **Fireplan**: a React PWA + Chrome/Firefox extension version of the calculator — installable on a phone, with an editable Engine Data panel and one-click "Send to dxCalc" export. Deployed at the site root. |
| `test_*.py` | Offline suites that guard the rig: they prove each experiment design could distinguish the hypotheses it ruled between. No network. |
| `HANDOVER.md` | The research log and methodology contract. |

The deployed site: **https://rbalukja15.github.io/fireplan/** (Fireplan;
the research calculator lives under [`/research/`](https://rbalukja15.github.io/fireplan/research/)).

## Provenance & notices

- **Not affiliated** with Bytro Labs (Supremacy 1914), dxter (dxcalc.com), or
  NoxiaZ (Supremacy Utilities). Fan-made research, non-commercial.
- Every coefficient in both calculators traces to a measurement: probe sweeps
  against dxcalc.com (`results.jsonl`), values read off live game pages, or is
  explicitly flagged as unmeasured. Game *mechanics* are facts; all code here
  is original.
- The repo contains a few **captured HTML responses** from dxcalc.com
  (`last_response.html`, `fortress_result.html`, `multi_stack_response.html`,
  `app/calibration/`). They are kept as the fixtures the offline test
  suites replay — measurement records for interoperability research. dxter's
  client JavaScript (`bytro.js`) is deliberately **not** included. If you are
  dxter and want the captures removed or changed, open an issue or email —
  they will be removed on request.
- The probe is deliberately slow (default ≥1.5 s between requests) and every
  recorded request cost someone else's bandwidth: if you run it, keep it that
  way.

## License

MIT — see [LICENSE](LICENSE).
