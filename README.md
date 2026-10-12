# experiment-registry-schema

A stdlib-only validator for A/B experiment registries: experiment declaration schema (hypothesis, owner, surface, dates, traffic, variants, status) plus same-surface overlap and traffic-oversubscription conflict detection. If more than one team runs experiments on shared surfaces, use this in CI; otherwise skip it.

## Problem

Experiment registries rot in spreadsheets. Two teams launch on the same checkout surface with 60% traffic each, variants lack a control, hypotheses are one word, and nobody notices until results are uninterpretable. The registry needs a mechanical gate that runs before experiments go live, offline, without a platform.

## How it works

- Registry = JSON: `{"experiments": [...]}`.
- Per experiment: non-empty unique `id`; required `name`, `owner`, `surface`, `primary_metric`; hypothesis >= 10 chars (WARN otherwise); ISO `start_date`/`end_date` with end >= start; `traffic_percent` in [0, 100]; `variants` = >= 2 unique strings with a `control` first; `status` in {draft, running, paused, completed, cancelled}.
- Conflict detection (`detect_conflicts`): for each same-surface pair with overlapping date ranges — traffic sum > 100% is an ERROR (`TRAFFIC_OVERSUBSCRIBED`), otherwise an OVERLAP WARNING.
- Findings are `{code, severity, message, location}`; exit 1 on any ERROR.

## Quickstart (~2 min)

```bash
python experiment_registry_schema.py check registry.json          # ~0.5s
python experiment_registry_schema.py check registry.json --json   # CI-friendly output
```

Then run the self-test suite: `python self_test.py` (~0.5s).

## Why not X

No direct equivalent found as of 2026-10-13: searches for "experiment registry schema validator / A/B test conflict checker" surface platform features and stats literature, not standalone offline validators. Nearest neighbors:

- **GrowthBook / LaunchDarkly / Statsig** — feature-flag platforms with some traffic-allocation guards; they enforce their own runtime, not a portable registry file, and can't audit a registry you keep in git.
- **JSON Schema + ajv** — covers field presence/types but not cross-record semantics: date overlap, traffic sums per surface, control-variant presence.
- **SQL over a spreadsheet** — the usual fallback; no severity model, no reusable schema, no CI exit codes, drifts per author.
- **PlanOut / stats libraries** — design and analysis of experiments, not registry hygiene.

## Performance

Measured on CPython 3.13.12, Windows 10 Pro, 2026-10-13:

- Full self-test suite (71 cases): **~0.5 s** [Measured] — repro: `python self_test.py`
- Validate + conflict-check 500 experiments (20 surfaces): **~281 ms/op** [Measured] — repro:

```bash
python -m timeit -s "import experiment_registry_schema as m, json; r=json.load(open('registry.json'))" "m.validate_registry(r); m.detect_conflicts(r['experiments'])"
```

Conflict detection is O(n^2) per surface; see Limits. Registry-scale use (hundreds of experiments) stays sub-second.

## Minimal Fallback

No installs needed beyond Python 3.8+. If you cannot run the validator, audit with a pivot: sort the registry by surface and eyeball adjacent rows for date overlap and traffic sums. You lose schema checks, severity levels, and the exit-code contract.

## Design Trade-offs

- **O(n^2) pair scan over indexing by surface**: registries are small (hundreds), simplicity wins; per-surface indexing is a drop-in optimization if registries grow 100x.
- **Overlap always reported, oversubscription only when sum > 100%**: two 50% tests overlapping are legitimate (complementary slices); the tool warns rather than blocks.
- **Priority order**: statistical validity (traffic/control/date rules) > completeness (owner/hypothesis) > convenience.

## Limits & Second-order Effects

- Traffic is treated as a static percentage; bandit-style dynamic allocation makes the 100% rule conservative.
- Date overlap assumes all experiments target the same audience — audience segmentation (geo, cohort) isn't modeled, so some warnings are false positives by design.
- Widely adopted, teams may register experiments they privately deprioritize just to "reserve" traffic — the ledger becomes a parking lot. Periodic status hygiene (`completed`/`cancelled`) is a human job.

## FAQ

**Does it compute statistical significance?** No — this is registry hygiene, not analysis. Pair it with your stats stack.

**Can two experiments share a surface?** Yes; you get a warning at overlap and an error only if declared traffic sums exceed 100%.

**When NOT to use this tool?** Skip it if a flag platform already owns allocation and enforces collision rules at runtime — a file-based registry would be a shadow source of truth. Also skip for single-experiment-at-a-time teams; the conflict layer is dead weight.

## [Core Assumptions]

1. Experiments target named surfaces (strings) and dates are a meaningful collision dimension.
2. Declared traffic percentages are roughly what the runtime will use.
3. Every valid experiment has >= 2 variants including a control.
4. Registries live as reviewable files (JSON in git), not only inside platform UIs.

---

Confidence: High (≥80%) for schema and conflict semantics — 71 self-test cases including 3-way overlaps and boundary traffic sums. Medium (60-79%) that static-traffic overlap is the right primary collision signal — depends on team allocation practice. Data as of 2026-10-13.

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 105 purpose-built AI-engineering tools across neglected niches.

Related tools: [image-alt-check](https://github.com/chenhz01/image-alt-check) · [metric-definition-dict](https://github.com/chenhz01/metric-definition-dict) · [image-prompt-schema](https://github.com/chenhz01/image-prompt-schema)
