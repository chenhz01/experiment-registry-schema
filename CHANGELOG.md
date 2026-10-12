# Changelog

## v0.1.1 (2026-10-13)

Round-2 revision after full self-review of the v0.1.0 draft:

- Added 4 extreme-edge test cases (100%+1% oversubscription, single-day
  experiments, uppercase status rejection, 50 same-surface experiments =
  1225 conflict pairs); suite grew 67 -> 71 cases, all PASS.
- Fixed self-test fixtures: CLI cases no longer pass a nonexistent
  subcommand word; the 3-way oversubscription fixture now uses 60/60/60
  traffic so every pair genuinely exceeds 100%.
- Measured and documented Performance numbers ([Measured] tags, repro
  commands), including the O(n^2) conflict-scan cost.
- Added ALIGNMENT.md (rules 85-100 audit, 16 items with evidence).

## v0.1.0 (2026-10-13)

Initial draft:

- Experiment schema validation: unique ids, required fields (name, owner,
  surface, primary_metric), hypothesis depth warning, ISO date parsing with
  ordering rule, traffic_percent bounds with zero-traffic warning, variants
  list rules (>= 2 unique, control first), status whitelist.
- Conflict detection: same-surface overlapping date ranges -> OVERLAP_WARNING;
  traffic sums > 100% -> TRAFFIC_OVERSUBSCRIBED error.
- CLI (`check`, `--json`) with exit-code contract 0/1/2.
- Self-test suite: 67 cases across functional / exception / extreme-edge
  classes, `SUMMARY: PASS n/n` reporting, four-defence template.
- README, MIT LICENSE.
