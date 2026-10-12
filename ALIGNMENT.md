# Alignment Audit (Rules 85-100 / 16 items) — experiment-registry-schema

Audited: 2026-10-13 (round 2, v0.1.1).

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | 85 Safety/Ethics section | PASS | Process-hygiene tool, no offensive capability. README "Limits" covers gaming risk (traffic-reservation parking lot). No security-research content, so no separate Ethics section required. |
| 2 | 86 Privacy de-identification | PASS | Zero secrets/tokens/real names; owners/surfaces are placeholders (`team-growth`, `checkout`). Grep for `(sk-\|ghp_\|api_key=)` returns 0 hits. |
| 3 | 87 Copyright boundary | PASS | All content authored fresh; platform mentions are link-free structural references only. LICENSE (MIT, "zhengming contributors") present. |
| 4 | 88 Fact-check labeling | PASS | Performance numbers tagged [Measured] with repro command (timeit over validate+conflicts). |
| 5 | 89 Confidence grading | PASS | README closing block: High (schema/conflict semantics) / Medium (static-traffic signal choice) with justification. |
| 6 | 90 PLAN B built-in | PASS | README "Minimal Fallback": sort-by-surface pivot audit without the tool. |
| 7 | 91 Timeout presets | PASS | Quickstart marks ~2 min total, per-command ~0.5s, self-test ~0.5s. |
| 8 | 92 Rule-conflict arbitration | PASS | README "Design Trade-offs": validity > completeness > convenience; warn-vs-block choice for complementary slices. |
| 9 | 93 Version changelog | PASS | CHANGELOG.md has v0.1.0 and v0.1.1 with explicit iteration improvements. |
| 10 | 94 Exemption instruction | N/A | Session-governance rule; static repo content cannot carry exemptions. |
| 11 | 95 External-knowledge cutoff | PASS | README marks environment and "as of 2026-10-13" for landscape claims and measurements. |
| 12 | 96 Explicit assumptions | PASS | README `[Core Assumptions]` lists 4 premises. |
| 13 | 97 Logic-verification trio | PASS | self_test.py: 71 cases = functional A + CLI/exception B + extreme edges C (empty registry, unicode ids, 1000 experiments, 3-way overlaps). SUMMARY: PASS 71/71. |
| 14 | 98 Socratic question | PASS | FAQ "When NOT to use this tool?" (flag-platform shops; single-experiment teams). |
| 15 | 99 Pareto iteration | PASS | Two rounds traceable: v0.1.0 -> review -> v0.1.1 (+4 edge cases, fixture corrections). CHANGELOG + TestR2 class. |
| 16 | 100 Ultimate minimal entry | PASS | README opening paragraph is 55 words with a need-judgment ("otherwise skip it"). |

Repro for status column: `python self_test.py` -> `SUMMARY: PASS 71/71`.
