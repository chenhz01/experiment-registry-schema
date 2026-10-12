# -*- coding: utf-8 -*-
"""self_test for experiment-registry-schema — R14, inherits 4-defence template v2."""
import atexit
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import experiment_registry_schema as m  # noqa: E402

_TMP = tempfile.mkdtemp(prefix="ers_selftest_")
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)


def wf(name, content):
    p = os.path.join(_TMP, name)
    with open(p, "w", encoding="utf-8", newline="") as f:  # Defence 3
        f.write(content)
    return p


def run_cli(argv):
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            m.main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:  # noqa: BLE001
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


def exp(**kw):
    e = {"id": "exp-001", "name": "Checkout button", "hypothesis": "Green button lifts CTR by 5%",
         "owner": "team-growth", "surface": "checkout", "start_date": "2026-10-01",
         "end_date": "2026-10-31", "traffic_percent": 50, "variants": ["control", "green"],
         "status": "running", "primary_metric": "ctr"}
    e.update(kw)
    return {k: v for k, v in e.items() if v is not None}


def reg(exps=None, **top):
    d = {"experiments": exps if exps is not None else [exp()]}
    d.update(top)
    return d

REG_OK = wf("b_ok.json", json.dumps(reg([
    exp(),
    exp(id="exp-002", name="Header test", hypothesis="New header lifts engagement",
        owner="team-web", surface="home", start_date="2026-10-05",
        end_date="2026-11-05", traffic_percent=30, variants=["control", "bold"],
        status="draft", primary_metric="engagement")])))
REG_BAD = wf("b_bad.json", json.dumps(reg([{"id": "x"}])))
REG_MALFORMED = wf("b_malformed.json", "{oops")
REG_LIST = wf("b_list.json", json.dumps([1]))
REG_OVERSUB = wf("b_oversub.json", json.dumps(reg([
    exp(id="exp-001"), exp(id="exp-002", traffic_percent=60)])))

# ---- [A] functional: (name, registry, checks, no_errors, with_conflicts) ----
A_CASES = [
    ("valid_registry_clean", reg(), [], True, True),
    ("valid_two_surfaces", reg([exp(), exp(id="e2", surface="home")]), [], True, True),
    ("experiments_missing", {"schema": "1"}, [("EXPERIMENTS_NOT_LIST", "")], False, False),
    ("experiments_not_list", reg(exps={"id": "x"}), [("EXPERIMENTS_NOT_LIST", "")], False, False),
    ("experiment_not_object", reg([42]), [("EXPERIMENT_NOT_OBJECT", "")], False, False),
    ("id_missing", reg([exp(id=None)]), [("EXPERIMENT_ID_INVALID", "")], False, False),
    ("id_duplicate", reg([exp(), exp(owner="o", surface="s2")]),
     [("EXPERIMENT_ID_DUP", "exp-001")], False, False),
    ("name_missing", reg([exp(name=None)]), [("FIELD_MISSING", "name")], False, False),
    ("owner_missing", reg([exp(owner=None)]), [("FIELD_MISSING", "owner")], False, False),
    ("surface_missing", reg([exp(surface=None)]), [("FIELD_MISSING", "surface")], False, False),
    ("metric_missing", reg([exp(primary_metric=None)]), [("FIELD_MISSING", "primary_metric")], False, False),
    ("hypothesis_thin", reg([exp(hypothesis="short")]), [("HYPOTHESIS_THIN", "")], False, False),
    ("start_date_invalid", reg([exp(start_date="2026/10/01")]), [("DATE_INVALID", "start_date")], False, False),
    ("end_date_invalid", reg([exp(end_date="not-a-date")]), [("DATE_INVALID", "end_date")], False, False),
    ("date_order", reg([exp(end_date="2026-09-01")]), [("DATE_ORDER", "")], False, False),
    ("traffic_out_of_range", reg([exp(traffic_percent=150)]), [("TRAFFIC_INVALID", "")], False, False),
    ("traffic_zero_warn", reg([exp(traffic_percent=0)]), [("TRAFFIC_ZERO", "")], False, False),
    ("variants_one", reg([exp(variants=["control"])]), [("VARIANTS_INVALID", "")], False, False),
    ("variants_dup", reg([exp(variants=["control", "control"])]), [("VARIANTS_INVALID", "")], False, False),
    ("no_control_warn", reg([exp(variants=["green", "blue"])]), [("NO_CONTROL_VARIANT", "")], False, False),
    ("status_invalid", reg([exp(status="live")]), [("STATUS_INVALID", "")], False, False),
    ("oversubscription_error", reg([exp(), exp(id="e2", traffic_percent=60)]),
     [("TRAFFIC_OVERSUBSCRIBED", "")], False, True),
    ("overlap_same_dates", reg([exp(), exp(id="e2", traffic_percent=20)]),
     [("OVERLAP_WARNING", "")], False, True),
    ("no_conflict_disjoint_dates", reg([exp(), exp(id="e2", start_date="2026-11-01",
                                                   end_date="2026-11-30", traffic_percent=20)]),
     [], True, True),
]


def _mk_a(name, man, checks, no_errors, conflicts):
    def t(self):
        fs = m.validate_registry(man)
        if conflicts:
            fs = fs + m.detect_conflicts(man.get("experiments", []))
        if no_errors:
            self.assertEqual([f for f in fs if f["severity"] == "ERROR"], [], msg=name)
        for code, sub in checks:
            hit = [f for f in fs if f["code"] == code and sub in f["message"]]
            self.assertTrue(hit, msg="%s expects %s (%r)" % (name, code, sub))
    t.__doc__ = "A: %s" % name
    return t


class TestA(unittest.TestCase):
    def test_a25_hypothesis_warn_severity(self):
        fs = m.validate_registry(reg([exp(hypothesis="tiny")]))
        self.assertEqual([f["severity"] for f in fs if f["code"] == "HYPOTHESIS_THIN"], ["WARN"])

    def test_a26_date_order_severity(self):
        fs = m.validate_registry(reg([exp(end_date="2026-09-01")]))
        self.assertEqual([f for f in fs if f["code"] == "DATE_ORDER"][0]["severity"], "ERROR")

    def test_a27_leap_date_valid(self):
        self.assertEqual([f for f in m.validate_registry(
            reg([exp(start_date="2024-02-29", end_date="2024-03-05")]))
            if f["code"] == "DATE_INVALID"], [])

    def test_a28_registry_none_raises(self):
        with self.assertRaises(TypeError):
            m.validate_registry(None)

    def test_a29_registry_list_raises(self):
        with self.assertRaises(TypeError):
            m.validate_registry([1])

    def test_a30_conflict_pair_message_has_ids(self):
        fs = m.detect_conflicts([exp(id="A"), exp(id="B", traffic_percent=60)])
        self.assertTrue(all("A x B" in f["message"] for f in fs))


for _i, _c in enumerate(A_CASES):
    setattr(TestA, "test_a%02d_%s" % (_i, _c[0]), _mk_a(_c[0], _c[1], _c[2], _c[3], _c[4]))

# ---- [B] CLI contract ----
B_CASES = [
    ("valid_exit0", REG_OK, [], 0, "", ""),
    ("invalid_exit1", REG_BAD, [], 1, "", ""),
    ("oversub_exit1", REG_OVERSUB, [], 1, "", ""),
    ("json_flag", REG_OK, ["--json"], 0, '"findings"', ""),
    ("missing_file", None, [], 2, "", "cannot read"),
    ("malformed_json", REG_MALFORMED, [], 2, "", "not valid JSON"),
    ("registry_is_list", REG_LIST, [], 2, "", "must be a dict"),
    ("text_output_summary", REG_OK, [], 0, "summary:", ""),
    ("json_summary_key", REG_BAD, ["--json"], 1, '"summary"', ""),
    ("warn_only_exit0", wf("b_warn.json", json.dumps(reg([exp(traffic_percent=0)]))), [], 0, "", ""),
]


def _mk_b(name, content, extra, code, out_sub="", err_sub=""):
    def t(self):
        path = content if content is not None else os.path.join(_TMP, "absent_%s.json" % name)
        c, out, err = run_cli([path] + extra)
        self.assertEqual(c, code, msg="out=%r err=%r" % (out, err))
        if out_sub:
            self.assertIn(out_sub, out)
        if err_sub:
            self.assertIn(err_sub, err)
    t.__doc__ = "B: %s" % name
    return t


class TestB(unittest.TestCase):
    def test_b10_missing_positional(self):
        c, _out, _err = run_cli([])
        self.assertEqual(c, 2)

    def test_b11_help_exit0(self):
        c, out, _err = run_cli(["--help"])
        self.assertEqual(c, 0)
        self.assertIn("usage:", out)


for _i, (_nm, _ct, _ex, _cd, _os, _es) in enumerate(B_CASES):
    setattr(TestB, "test_b%02d_%s" % (_i, _nm), _mk_b(_nm, _ct, _ex, _cd, _os, _es))

# ---- [C] extreme/edge ----
C_CASES = [
    ("empty_registry", lambda s: s.assertEqual(
        m.validate_registry({"experiments": []}), [])),
    ("empty_dict_registry", lambda s: s.assertTrue(
        {"EXPERIMENTS_NOT_LIST"} <= {f["code"] for f in m.validate_registry({})})),
    ("unicode_surface_ok", lambda s: s.assertEqual(
        m.validate_registry(reg([exp(surface="结算页")], )), [])),
    ("unicode_id_ok", lambda s: s.assertEqual(
        [f for f in m.validate_registry(reg([exp(id="实验-001")]))
         if f["severity"] == "ERROR"], [])),
    ("three_overlap_pairs", lambda s: s.assertEqual(
        len(m.detect_conflicts([exp(id="a"), exp(id="b"), exp(id="c")])[0:3]), 3)),
    ("three_way_oversub_all_pairs", lambda s: s.assertEqual(
        len([f for f in m.detect_conflicts([exp(id="a", traffic_percent=60),
                                            exp(id="b", traffic_percent=60),
                                            exp(id="c", traffic_percent=60)])
             if f["code"] == "TRAFFIC_OVERSUBSCRIBED"]), 3)),
    ("adjacent_dates_no_overlap", lambda s: s.assertEqual(
        m.detect_conflicts([exp(id="a"), exp(id="b", start_date="2026-11-01",
                                             end_date="2026-11-30")]), [])),
    ("same_day_overlap", lambda s: s.assertEqual(
        len(m.detect_conflicts([exp(id="a"), exp(id="b", start_date="2026-10-31",
                                                 end_date="2026-12-01")])), 1)),
    ("invalid_dates_skip_conflict", lambda s: s.assertEqual(
        m.detect_conflicts([exp(id="a", start_date="bad"),
                            exp(id="b", start_date="bad")]), [])),
    ("missing_surface_skip_conflict", lambda s: s.assertEqual(
        m.detect_conflicts([exp(id="a", surface=None), exp(id="b", surface=None)]), [])),
    ("traffic_non_numeric_defaults_zero", lambda s: s.assertEqual(
        [f for f in m.detect_conflicts([exp(id="a", traffic_percent="50"),
                                        exp(id="b", traffic_percent=20)])
         if f["code"] == "OVERLAP_WARNING"], [f for f in m.detect_conflicts(
            [exp(id="a", traffic_percent="50"), exp(id="b", traffic_percent=20)])
         if f["code"] in ("OVERLAP_WARNING", "TRAFFIC_OVERSUBSCRIBED")])),
    ("traffic_exactly_100_ok", lambda s: s.assertEqual(
        [f for f in m.detect_conflicts([exp(id="a", traffic_percent=50),
                                        exp(id="b", traffic_percent=50)])
         if f["code"] == "TRAFFIC_OVERSUBSCRIBED"], [])),
    ("registry_none_raises", lambda s: s.assertRaises(TypeError, m.validate_registry, None)),
    ("experiment_none_element", lambda s: s.assertTrue(any(
        f["code"] == "EXPERIMENT_NOT_OBJECT"
        for f in m.validate_registry(reg([None]))))),
    ("bool_traffic_rejected", lambda s: s.assertTrue(any(
        f["code"] == "TRAFFIC_INVALID"
        for f in m.validate_registry(reg([exp(traffic_percent=True)]))))),
    ("zero_variants_rejected", lambda s: s.assertTrue(any(
        f["code"] == "VARIANTS_INVALID"
        for f in m.validate_registry(reg([exp(variants=[])]))))),
    ("variants_numeric_rejected", lambda s: s.assertTrue(any(
        f["code"] == "VARIANTS_INVALID"
        for f in m.validate_registry(reg([exp(variants=["control", 3])]))))),
    ("date_none_rejected", lambda s: s.assertTrue(any(
        f["code"] == "DATE_INVALID"
        for f in m.validate_registry(reg([exp(start_date=None)])))),
     ),
    ("date_time_suffix_rejected", lambda s: s.assertTrue(any(
        f["code"] == "DATE_INVALID"
        for f in m.validate_registry(reg([exp(start_date="2026-10-01T00:00:00")]))))),
    ("thousand_experiments_completes", lambda s: s.assertEqual(
        len(m.validate_registry(reg([exp(id="e%04d" % i, surface="s%d" % (i % 7))
                                     for i in range(1000)]))), 0)),
    ("hypothesis_unicode_ok", lambda s: s.assertEqual(
        [f for f in m.validate_registry(reg([exp(hypothesis="绿色按钮预计提升点击率百分之五以上")]))
         if f["code"] == "HYPOTHESIS_THIN"], [])),
    ("cli_json_roundtrip", lambda s: s.assertEqual(
        json.loads(run_cli([REG_OK, "--json"])[1])["summary"]["error"], 0)),
    ("cli_directory_exit2", lambda s: s.assertEqual(run_cli([_TMP])[0], 2)),
    ("status_missing_rejected", lambda s: s.assertTrue(any(
        f["code"] == "STATUS_INVALID"
        for f in m.validate_registry(reg([exp(status=None)])))),
     ),
    ("emoji_name_ok", lambda s: s.assertEqual(
        [f for f in m.validate_registry(reg([exp(name="🚀 launch test")]))
         if f["severity"] == "ERROR"], [])),
]


class TestC(unittest.TestCase):
    pass


for _i, (_nm, _fn) in enumerate(C_CASES):
    setattr(TestC, "test_c%02d_%s" % (_i, _nm), _fn)


# ---- Round-2 additions (v0.1.1): extra extreme-edge coverage ----
class TestR2(unittest.TestCase):
    def test_r2_traffic_100_plus_1_oversub(self):
        fs = m.detect_conflicts([exp(id="a", traffic_percent=100), exp(id="b", traffic_percent=1)])
        self.assertEqual([f["code"] for f in fs], ["TRAFFIC_OVERSUBSCRIBED"])

    def test_r2_single_day_experiment(self):
        fs = m.validate_registry(reg([exp(start_date="2026-10-13", end_date="2026-10-13")]))
        self.assertEqual(fs, [])

    def test_r2_status_uppercase_invalid(self):
        fs = m.validate_registry(reg([exp(status="RUNNING")]))
        self.assertTrue(any(f["code"] == "STATUS_INVALID" for f in fs))

    def test_r2_fifty_same_surface_completes(self):
        exps = [exp(id="e%02d" % i) for i in range(50)]
        self.assertEqual(len(m.detect_conflicts(exps)), 50 * 49 // 2)

if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))  # Defence 4
    sys.exit(0 if fails == 0 else 1)
