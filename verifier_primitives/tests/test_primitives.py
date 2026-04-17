"""Unit tests for verifier-primitives library.

Only covers pure-Python primitives with no external deps so it runs in CI
without ffmpeg / curl / jsonschema / etc. Primitives that need externals
have thin smoke tests gated by `pytest.importorskip` / tool existence checks.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
# Make sibling package importable when pytest is invoked from repo root.
sys.path.insert(0, str(HERE.parent.parent))

from verifier_primitives import (  # noqa: E402
    DependencyMissing,
    TIER_MAP,
    classify_tier,
    code_review_verdict,
    cross_refs_all_resolvable,
    dir_exists,
    file_exists,
    grep_count,
    retro_exists,
    schema_valid,
    screenshot_has_content,
    wc_lines,
)


@pytest.fixture
def tmp_file(tmp_path):
    p = tmp_path / "hello.txt"
    p.write_text("line1\nline2\nline3\n", encoding="utf-8")
    return p


def test_file_exists_true(tmp_file):
    ok, ev = file_exists(str(tmp_file))
    assert ok is True
    assert ev["exists"] is True
    assert ev["size_bytes"] > 0


def test_file_exists_false(tmp_path):
    ok, ev = file_exists(str(tmp_path / "nope.txt"))
    assert ok is False
    assert ev["exists"] is False


def test_dir_exists(tmp_path):
    ok, _ = dir_exists(str(tmp_path))
    assert ok is True
    ok2, _ = dir_exists(str(tmp_path / "subdir"))
    assert ok2 is False


def test_wc_lines(tmp_file):
    n, ev = wc_lines(str(tmp_file))
    assert n == 3
    assert ev["lines"] == 3


def test_wc_lines_missing(tmp_path):
    n, ev = wc_lines(str(tmp_path / "gone.txt"))
    assert n == -1
    assert ev["error"] == "not_a_file"


def test_grep_count(tmp_file):
    n, _ = grep_count(r"^line\d$", str(tmp_file))
    assert n == 3
    n2, _ = grep_count(r"nothing", str(tmp_file))
    assert n2 == 0


def test_retro_exists_empty(tmp_path):
    empty = tmp_path / "retro.md"
    empty.write_text("", encoding="utf-8")
    ok, ev = retro_exists(str(empty))
    assert ok is False
    assert ev["nonempty"] is False


def test_retro_exists_nonempty(tmp_path):
    p = tmp_path / "retro.md"
    p.write_text("# retro\n", encoding="utf-8")
    ok, _ = retro_exists(str(p))
    assert ok is True


def test_screenshot_has_content_small(tmp_path):
    p = tmp_path / "shot.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    ok, ev = screenshot_has_content(str(p), min_bytes=2048)
    assert ok is False
    assert ev["size_bytes"] < 2048


def test_screenshot_has_content_ok(tmp_path):
    p = tmp_path / "shot.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 5000)
    ok, ev = screenshot_has_content(str(p), min_bytes=2048)
    assert ok is True
    assert ev["size_bytes"] >= 2048


def test_classify_tier():
    assert classify_tier("file_exists") == "existence"
    assert classify_tier("curl_status") == "behavior"
    assert classify_tier("ffprobe_duration") == "quality"
    # unknown primitive defaults to quality
    assert classify_tier("never_heard_of") == "quality"


def test_tier_map_covers_documented_primitives():
    must_have = {
        "file_exists",
        "ffprobe_duration",
        "oss_head",
        "playback_check",
        "retro_exists",
        "uvicorn_started",
        "curl_status",
        "pytest_exit_code",
        "schema_valid",
        "code_review_verdict",
        "vite_started",
        "playwright_nav",
        "playwright_exit_code",
        "screenshot_has_content",
        "type_check_exit_code",
        "wc_lines",
        "grep_count",
        "cross_refs_all_resolvable",
        "pytest_all_green",
        "benchmark_regression_delta",
        "no_public_api_breaking_change",
        "diff_lines_net",
    }
    assert must_have <= set(TIER_MAP.keys())


def test_schema_valid_success(tmp_path):
    pytest.importorskip("jsonschema")
    schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    schema_path = tmp_path / "s.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    ok, _ = schema_valid({"name": "hi"}, str(schema_path))
    assert ok is True


def test_schema_valid_fail(tmp_path):
    pytest.importorskip("jsonschema")
    schema = {"type": "object", "required": ["name"]}
    schema_path = tmp_path / "s.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    ok, ev = schema_valid({}, str(schema_path))
    assert ok is False
    assert "name" in ev.get("message", "")


def test_schema_valid_dep_missing(monkeypatch, tmp_path):
    import verifier_primitives.schema as schema_mod
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

    def fake_import(name, *args, **kwargs):
        if name == "jsonschema":
            raise ImportError("simulated missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    with pytest.raises(DependencyMissing):
        schema_mod.schema_valid({"x": 1}, str(tmp_path / "nope.json"))


def test_code_review_verdict_missing(tmp_path):
    v, ev = code_review_verdict("abc-123", reviews_dir=str(tmp_path))
    assert v == "MISSING"
    assert ev["error"] == "review_not_found"


def test_code_review_verdict_pass(tmp_path):
    (tmp_path / "abc-123.json").write_text(
        json.dumps({"verdict": "PASS", "issues": []}), encoding="utf-8"
    )
    v, _ = code_review_verdict("abc-123", reviews_dir=str(tmp_path))
    assert v == "PASS"


def test_cross_refs_all_resolvable(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    b.write_text("b", encoding="utf-8")
    a.write_text("[link1](b.md) [dead](missing.md) [ext](https://example.com)", encoding="utf-8")
    ok, ev = cross_refs_all_resolvable(str(a))
    assert ok is False
    assert ev["missing_count"] == 1
    assert ev["missing_sample"][0]["target"] == "missing.md"


# ---------- tool-dependent smoke tests (skipped if tool absent) ----------


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe not installed")
def test_ffprobe_duration_missing_file(tmp_path):
    from verifier_primitives import ffprobe_duration

    dur, ev = ffprobe_duration(str(tmp_path / "nope.mp4"))
    assert dur == -1.0
    assert ev["error"] == "not_a_file"


@pytest.mark.skipif(shutil.which("curl") is None, reason="curl not installed")
def test_curl_status_against_loopback_unreachable():
    from verifier_primitives import curl_status

    # An unused high port → curl fails fast; exit code nonzero, body empty
    code, ev = curl_status("http://127.0.0.1:6/unreachable", timeout=2.0)
    assert code == -1 or code == 0
    assert ev["url"].endswith("/unreachable")


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_diff_lines_net_runs_without_crash(tmp_path, monkeypatch):
    from verifier_primitives import diff_lines_net

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    net, ev = diff_lines_net(base="HEAD")
    # Empty repo HEAD diff should produce net == 0 or error but not crash
    assert isinstance(net, int)
    assert "base" in ev
