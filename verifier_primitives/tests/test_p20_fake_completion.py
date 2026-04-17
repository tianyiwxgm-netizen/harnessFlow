"""P20 fake-completion replay unit test.

Acceptance signal for Phase 6: given a task-board that LOOKS done (mp4 exists
on disk) but is actually missing the OSS upload leg, the Verifier executor
must refuse to return PASS.

Constructs a fake P20 task-board in a tmp dir, monkeypatches the primitive
resolver to return:
  - file_exists(...) → True  (disk artifact was written)
  - ffprobe_duration(...) → raise DependencyMissing  (ffprobe not installed)
  - oss_head(...).status_code → 403  (upload failed / not signed)
  - playback_check(...) → raise DependencyMissing
  - retro_exists(...) → True

Expected outcomes:
  1. Primary scenario with OSS=403 → verdict == "FAIL", priority=="P0_red_line",
     red_lines contains DOD_GAP_ALERT.
  2. Scenario with OSS=200 but ffprobe dep missing → verdict ==
     "INSUFFICIENT_EVIDENCE" first time; after cap exceeded, upgrades to FAIL.
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from verifier_primitives.executor import eval_verifier  # noqa: E402
from verifier_primitives.errors import DependencyMissing  # noqa: E402


P20_DOD = (
    'file_exists("media/p20.mp4")'
    " AND ffprobe_duration(\"media/p20.mp4\") > 0"
    ' AND oss_head("https://cdn.example.com/p20.mp4").status_code == 200'
    ' AND playback_check("media/p20.mp4") == True'
    ' AND retro_exists("harnessFlow /retros/p20.md")'
)


def _make_resolver(**overrides):
    def file_exists(_path):
        return True, {"path": _path, "exists": True, "size_bytes": 42}

    def ffprobe_dep_missing(_path):
        raise DependencyMissing("ffprobe", "not installed in CI")

    def oss_head_403(_url):
        return {"status_code": 403}, {"url": _url, "status_code": 403}

    def oss_head_200(_url):
        return {"status_code": 200}, {"url": _url, "status_code": 200}

    def playback_dep_missing(_path):
        raise DependencyMissing("ffmpeg", "not installed in CI")

    def retro_exists(_path):
        return True, {"path": _path, "nonempty": True}

    defaults = {
        "file_exists": file_exists,
        "ffprobe_duration": ffprobe_dep_missing,
        "oss_head": oss_head_403,
        "playback_check": playback_dep_missing,
        "retro_exists": retro_exists,
    }
    defaults.update(overrides)

    def resolver(name):
        return defaults.get(name)

    return resolver


def test_p20_fake_completion_oss_fail_is_caught():
    tb = {
        "task_id": "p20-fake",
        "route": "C",
        "dod_expression": P20_DOD,
        "insufficient_evidence_count": 0,
        "red_lines": [],
    }
    resolver = _make_resolver()
    report = eval_verifier(
        task_id="p20-fake",
        dod_expression=P20_DOD,
        task_board=tb,
        primitive_resolver=resolver,
    )
    assert report.verdict == "FAIL", f"expected FAIL, got {report.verdict}; failed_conditions={report.failed_conditions}"
    assert "DOD_GAP_ALERT" in report.red_lines, f"red_lines={report.red_lines}"
    assert report.priority_applied == "P0_red_line"
    assert any("oss_head" in cond for cond in report.failed_conditions)


def test_p20_insufficient_evidence_caps_to_fail():
    # OSS fixed to 200 (pass), but ffprobe + playback deps missing.
    def oss_head_200(url):
        return {"status_code": 200}, {"url": url, "status_code": 200}

    resolver = _make_resolver(oss_head=oss_head_200)

    # First attempt — count starts at 0 → INSUFFICIENT_EVIDENCE
    tb_first = {
        "task_id": "p20-fake",
        "route": "C",
        "dod_expression": P20_DOD,
        "insufficient_evidence_count": 0,
        "red_lines": [],
    }
    r1 = eval_verifier("p20-fake", P20_DOD, tb_first, resolver, cap=2)
    assert r1.verdict == "INSUFFICIENT_EVIDENCE"
    assert r1.priority_applied == "P3_insufficient_evidence"
    assert r1.insufficient_evidence_count_after_this == 1

    # Second attempt — count was 1, reaches cap (2) → FAIL upgrade
    tb_second = {**tb_first, "insufficient_evidence_count": 1}
    r2 = eval_verifier("p20-fake", P20_DOD, tb_second, resolver, cap=2)
    assert r2.verdict == "FAIL"
    assert r2.priority_applied == "P3_cap_exceeded"
    assert r2.insufficient_evidence_count_after_this == 2


def test_p20_all_green_returns_pass():
    def oss_head_200(url):
        return {"status_code": 200}, {"url": url, "status_code": 200}

    def ffprobe_ok(_path):
        return 58.32, {"path": _path, "duration_s": 58.32}

    def playback_ok(_path):
        return True, {"path": _path, "all_black": False}

    resolver = _make_resolver(
        oss_head=oss_head_200,
        ffprobe_duration=ffprobe_ok,
        playback_check=playback_ok,
    )
    tb = {
        "task_id": "p20-fake",
        "route": "C",
        "dod_expression": P20_DOD,
        "insufficient_evidence_count": 0,
        "red_lines": [],
    }
    r = eval_verifier("p20-fake", P20_DOD, tb, resolver)
    assert r.verdict == "PASS", f"expected PASS; failed_conditions={r.failed_conditions}"
    assert r.priority_applied == "P1_pass"
    assert r.failed_conditions == []


def test_verdict_decision_priority_red_line_beats_insufficient():
    # Mix: OSS fails (P0 fodder) AND ffprobe dep missing. Red-line fail must win.
    resolver = _make_resolver()  # default: oss 403 + ffprobe missing
    tb = {
        "task_id": "p20-fake",
        "route": "C",
        "dod_expression": P20_DOD,
        "insufficient_evidence_count": 0,
        "red_lines": [],
    }
    r = eval_verifier("p20-fake", P20_DOD, tb, resolver)
    assert r.verdict == "FAIL"
    assert r.priority_applied == "P0_red_line"


# ---------------- red-team cases (Phase 6 reviewer P0 + P1 issues) ----------------


def test_normal_fail_without_red_line_is_p2():
    dod = 'file_exists("README.md") AND wc_lines("README.md") >= 100'

    def file_exists_ok(_):
        return True, {"exists": True, "size_bytes": 10}

    def wc_lines_short(_):
        return 50, {"lines": 50}

    def resolver(name):
        return {"file_exists": file_exists_ok, "wc_lines": wc_lines_short}.get(name)

    tb = {"task_id": "docs-fake", "dod_expression": dod, "red_lines": [], "insufficient_evidence_count": 0}
    r = eval_verifier("docs-fake", dod, tb, resolver)
    assert r.verdict == "FAIL"
    assert r.priority_applied == "P2_normal_fail", f"got {r.priority_applied}; red_lines={r.red_lines}"
    assert "DOD_GAP_ALERT" not in r.red_lines


def test_nested_call_resolves_inner_primitive():
    dod = (
        'schema_valid(curl_json("http://localhost:8000/materials/reddit"), "schemas/m.json") == True'
    )
    calls = []

    def curl_json_fake(url):
        calls.append(("curl_json", url))
        return {"items": [], "malformed": True}, {"url": url}

    def schema_valid_reject(data, schema_path):
        calls.append(("schema_valid", data, schema_path))
        if not isinstance(data, dict) or "malformed" in data:
            return False, {"schema_path": schema_path, "valid": False, "message": "extra key"}
        return True, {"schema_path": schema_path, "valid": True}

    def resolver(name):
        return {"curl_json": curl_json_fake, "schema_valid": schema_valid_reject}.get(name)

    tb = {"task_id": "nested", "dod_expression": dod, "red_lines": [], "insufficient_evidence_count": 0}
    r = eval_verifier("nested", dod, tb, resolver)
    assert any(c[0] == "curl_json" for c in calls), "curl_json must be invoked first"
    assert any(c[0] == "schema_valid" for c in calls), "schema_valid must get resolved data"
    assert r.verdict == "FAIL"
    assert "DOD_GAP_ALERT" in r.red_lines
    behavior = r.evidence_chain["behavior"]
    assert any(e.get("nested_under") == "schema_valid" and e["primitive"] == "curl_json" for e in behavior)


def test_bare_oss_head_is_not_rubber_stamped():
    dod = 'file_exists("a.mp4") AND oss_head("https://cdn.example.com/a.mp4")'

    def file_exists_ok(_):
        return True, {"exists": True}

    def oss_head_bad(url):
        return {"status_code": 500}, {"url": url, "status_code": 500}

    def resolver(name):
        return {"file_exists": file_exists_ok, "oss_head": oss_head_bad}.get(name)

    tb = {"task_id": "bare-oss", "dod_expression": dod, "red_lines": [], "insufficient_evidence_count": 0}
    r = eval_verifier("bare-oss", dod, tb, resolver)
    assert r.verdict == "INSUFFICIENT_EVIDENCE"
    assert r.priority_applied == "P3_insufficient_evidence"
    assert "DOD_GAP_ALERT" in r.red_lines


def test_primitive_signature_mismatch_degrades_to_insufficient():
    dod = 'code_review_verdict == "PASS"'

    def code_review_needs_task_id(task_id):
        return "PASS", {"task_id": task_id, "verdict": "PASS"}

    def resolver(name):
        return {"code_review_verdict": code_review_needs_task_id}.get(name)

    tb = {"task_id": "missing-wrap", "dod_expression": dod, "red_lines": [], "insufficient_evidence_count": 0}
    r = eval_verifier("missing-wrap", dod, tb, resolver)
    assert r.verdict == "INSUFFICIENT_EVIDENCE"
    q = r.evidence_chain["quality"]
    assert any(e.get("insufficient") and "primitive_call_failed" in str(e.get("evidence")) for e in q)


def test_insufficient_evidence_flags_dod_gap_alert():
    dod = 'file_exists("media/x.mp4") AND ffprobe_duration("media/x.mp4") > 0'

    def file_exists_ok(_):
        return True, {"exists": True}

    def ffprobe_missing(_):
        raise DependencyMissing("ffprobe", "absent in CI")

    def resolver(name):
        return {"file_exists": file_exists_ok, "ffprobe_duration": ffprobe_missing}.get(name)

    tb = {"task_id": "ie-alert", "dod_expression": dod, "red_lines": [], "insufficient_evidence_count": 0}
    r = eval_verifier("ie-alert", dod, tb, resolver)
    assert r.verdict == "INSUFFICIENT_EVIDENCE"
    assert "DOD_GAP_ALERT" in r.red_lines


def test_unknown_primitive_is_insufficient_not_crash():
    dod = 'file_exists("x") AND this_primitive_does_not_exist("y") == 1'

    def file_exists_ok(_):
        return True, {"exists": True}

    def resolver(name):
        return {"file_exists": file_exists_ok}.get(name)

    tb = {"task_id": "unk", "dod_expression": dod, "red_lines": [], "insufficient_evidence_count": 0}
    r = eval_verifier("unk", dod, tb, resolver, cap=5)
    assert r.verdict == "INSUFFICIENT_EVIDENCE"
