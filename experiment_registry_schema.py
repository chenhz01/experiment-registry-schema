# -*- coding: utf-8 -*-
"""experiment-registry-schema: A/B experiment registry schema + conflict audit.

Validates experiment declarations (id/hypothesis/owner/surface/dates/traffic/
variants/status) and detects overlapping experiments on the same surface,
including traffic oversubscription. Pure stdlib, offline.
"""
import argparse
import datetime
import json
import sys

__version__ = "0.1.1"

VALID_STATUS = {"draft", "running", "paused", "completed", "cancelled"}


def _parse_date(s):
    if not isinstance(s, str):
        return None
    try:
        return datetime.datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _require_str(e, field, loc, add, min_len=1):
    v = e.get(field)
    if not isinstance(v, str) or len(v.strip()) < min_len:
        add("FIELD_MISSING", "ERROR",
            "experiment requires non-empty string '%s'" % field, loc)
        return False
    return True


def validate_registry(registry):
    """Validate a registry dict {experiments: [...]}; return findings.

    Raises TypeError when registry is not a dict.
    """
    if not isinstance(registry, dict):
        raise TypeError("registry must be a dict")
    findings = []

    def add(code, sev, msg, loc):
        findings.append({"code": code, "severity": sev, "message": msg, "location": loc})

    exps = registry.get("experiments")
    if not isinstance(exps, list):
        add("EXPERIMENTS_NOT_LIST", "ERROR",
            "registry.experiments must be a list", "$.experiments")
        return findings

    seen_ids = set()
    for i, e in enumerate(exps):
        loc = "$.experiments[%d]" % i
        if not isinstance(e, dict):
            add("EXPERIMENT_NOT_OBJECT", "ERROR", "experiment must be an object", loc)
            continue
        eid = e.get("id")
        if not isinstance(eid, str) or not eid.strip():
            add("EXPERIMENT_ID_INVALID", "ERROR",
                "experiment id must be a non-empty string", loc)
        elif eid in seen_ids:
            add("EXPERIMENT_ID_DUP", "ERROR", "duplicate experiment id: %s" % eid, loc)
        else:
            seen_ids.add(eid)

        for field in ("name", "owner", "surface", "primary_metric"):
            _require_str(e, field, loc, add)

        hyp = e.get("hypothesis")
        if not isinstance(hyp, str) or len(hyp.strip()) < 10:
            add("HYPOTHESIS_THIN", "WARN",
                "hypothesis missing or shorter than 10 chars", loc)

        d_start = _parse_date(e.get("start_date"))
        d_end = _parse_date(e.get("end_date"))
        if d_start is None:
            add("DATE_INVALID", "ERROR", "start_date must be ISO YYYY-MM-DD", loc)
        if d_end is None:
            add("DATE_INVALID", "ERROR", "end_date must be ISO YYYY-MM-DD", loc)
        if d_start and d_end and d_end < d_start:
            add("DATE_ORDER", "ERROR", "end_date is before start_date", loc)

        tp = e.get("traffic_percent")
        if not _is_num(tp) or not (0 <= tp <= 100):
            add("TRAFFIC_INVALID", "ERROR",
                "traffic_percent must be a number in [0, 100]", loc)
        elif tp == 0:
            add("TRAFFIC_ZERO", "WARN", "traffic_percent is 0", loc)

        variants = e.get("variants")
        if (not isinstance(variants, list) or len(variants) < 2
                or not all(isinstance(v, str) and v.strip() for v in variants)
                or len(set(variants)) != len(variants)):
            add("VARIANTS_INVALID", "ERROR",
                "variants must be >= 2 unique non-empty strings", loc)
        elif variants[0] != "control":
            add("NO_CONTROL_VARIANT", "WARN",
                "first variant should be 'control'", loc)

        if e.get("status") not in VALID_STATUS:
            add("STATUS_INVALID", "ERROR",
                "status must be one of %s" % sorted(VALID_STATUS), loc)
    return findings


def _date_range(e):
    d1, d2 = _parse_date(e.get("start_date")), _parse_date(e.get("end_date"))
    if d1 is None or d2 is None or d2 < d1:
        return None
    return (d1, d2)


def detect_conflicts(experiments):
    """Detect same-surface overlapping experiments and traffic oversubscription."""
    findings = []
    exps = [e for e in experiments if isinstance(e, dict)]
    for i in range(len(exps)):
        for j in range(i + 1, len(exps)):
            a, b = exps[i], exps[j]
            sa, sb = a.get("surface"), b.get("surface")
            if not isinstance(sa, str) or not sa or sa != sb:
                continue
            ra, rb = _date_range(a), _date_range(b)
            if ra is None or rb is None or ra[0] > rb[1] or rb[0] > ra[1]:
                continue
            ta = a.get("traffic_percent") if _is_num(a.get("traffic_percent")) else 0
            tb = b.get("traffic_percent") if _is_num(b.get("traffic_percent")) else 0
            pair = "%s x %s" % (a.get("id", "?"), b.get("id", "?"))
            if ta + tb > 100:
                findings.append({
                    "code": "TRAFFIC_OVERSUBSCRIBED", "severity": "ERROR",
                    "message": "overlapping on surface '%s' with traffic %s%% + %s%% > 100%% (%s)"
                               % (sa, ta, tb, pair), "location": "$.experiments"})
            else:
                findings.append({
                    "code": "OVERLAP_WARNING", "severity": "WARN",
                    "message": "overlapping date ranges on surface '%s' (%s)"
                               % (sa, pair), "location": "$.experiments"})
    return findings


def summarize(findings):
    out = {"error": 0, "warn": 0, "info": 0}
    for f in findings:
        key = f["severity"].lower()
        out[key] = out.get(key, 0) + 1
    return out


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="experiment-registry-schema",
        description="Validate an A/B experiment registry and detect "
                    "same-surface overlap / traffic conflicts.")
    p.add_argument("registry", help="path to registry JSON")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="emit findings as JSON")
    a = p.parse_args(argv)

    try:
        with open(a.registry, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except OSError as e:
        print("error: cannot read registry: %s" % e, file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print("error: registry is not valid JSON: %s" % e, file=sys.stderr)
        sys.exit(2)

    try:
        findings = validate_registry(registry)
    except TypeError as e:
        print("error: %s" % e, file=sys.stderr)
        sys.exit(2)
    if isinstance(registry, dict) and isinstance(registry.get("experiments"), list):
        findings += detect_conflicts(registry["experiments"])

    s = summarize(findings)
    if a.as_json:
        print(json.dumps({"findings": findings, "summary": s},
                         ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print("[%s] %s %s: %s" % (f["severity"], f["location"],
                                      f["code"], f["message"]))
        print("summary: %d error(s), %d warn(s), %d info(s)"
              % (s["error"], s["warn"], s["info"]))
    sys.exit(1 if s["error"] else 0)


if __name__ == "__main__":
    main()
