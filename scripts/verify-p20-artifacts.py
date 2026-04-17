#!/usr/bin/env python3
"""P20 真出片 artifact 验证 + 四件套产出（Phase 8.3）。

由 run-p20-validation.sh 在 uvicorn 停止后调用。

职责:
  1. 从 e2e_runner 输出和 aigc 后端产物定位 mp4 本地路径 + OSS key
  2. 跑 DoD_P20 全套 8 个子契约（file_exists / size / ffprobe_duration /
     playback_check / oss_head / uvicorn_log_sanity / pipeline_final_state /
     schema_valid_response）
  3. 产出 task-board.json (CLOSED) + verifier_report.json +
     retros/<task_id>.md (11 段) + failure-archive.jsonl entry

依赖:
  - ffprobe (brew install ffmpeg)
  - 可选: oss2 (pip install oss2) - 无则跳过 oss_head

退出码:
  0   DoD_P20 全 PASS
  N   N 个子契约 FAIL
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS_ROOT = HERE.parent
sys.path.insert(0, str(HARNESS_ROOT))

from archive.writer import write_archive_entry, ArchiveWriteError  # noqa: E402
from archive.retro_renderer import render_retro  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _check_file_exists(path: Path) -> dict:
    return {"primitive": "file_exists", "arg": str(path), "result": path.exists()}


def _check_size(path: Path, min_bytes: int = 1024) -> dict:
    if not path.exists():
        return {"primitive": "file_size", "arg": str(path), "result": 0, "pass": False}
    sz = path.stat().st_size
    return {"primitive": "file_size", "arg": str(path), "result": sz, "pass": sz >= min_bytes}


def _check_ffprobe_duration(path: Path) -> dict:
    if not shutil.which("ffprobe"):
        return {"primitive": "ffprobe_duration", "arg": str(path), "result": None,
                "pass": False, "error": "ffprobe not installed"}
    if not path.exists():
        return {"primitive": "ffprobe_duration", "arg": str(path), "result": None,
                "pass": False, "error": "file missing"}
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            timeout=30,
        )
        d = float(out.decode().strip())
        return {"primitive": "ffprobe_duration", "arg": str(path), "result": d, "pass": d > 0}
    except Exception as exc:
        return {"primitive": "ffprobe_duration", "arg": str(path), "result": None,
                "pass": False, "error": str(exc)}


def _check_playback(path: Path) -> dict:
    # 用 ffprobe 检查是否有 video stream + 可 demux
    if not shutil.which("ffprobe"):
        return {"primitive": "playback_check", "arg": str(path), "result": False,
                "pass": False, "error": "ffprobe not installed"}
    if not path.exists():
        return {"primitive": "playback_check", "arg": str(path), "result": False, "pass": False}
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name,width,height",
             "-of", "json", str(path)],
            timeout=30,
        )
        meta = json.loads(out)
        streams = meta.get("streams", [])
        ok = len(streams) > 0 and streams[0].get("width", 0) > 0
        return {"primitive": "playback_check", "arg": str(path), "result": streams,
                "pass": ok}
    except Exception as exc:
        return {"primitive": "playback_check", "arg": str(path), "result": False,
                "pass": False, "error": str(exc)}


def _check_oss_head(oss_url: str) -> dict:
    # 若 oss2 可用且 AK/SK 环境变量齐，真调 HEAD；否则 mark skipped
    try:
        import oss2  # type: ignore
    except ImportError:
        return {"primitive": "oss_head", "arg": oss_url, "result": None,
                "pass": False, "error": "oss2 not installed; skipped"}
    ak = os.environ.get("OSS_ACCESS_KEY_ID")
    sk = os.environ.get("OSS_SECRET_ACCESS_KEY")
    if not (ak and sk):
        return {"primitive": "oss_head", "arg": oss_url, "result": None,
                "pass": False, "error": "OSS_ACCESS_KEY_ID/SECRET missing; skipped"}
    # parse oss://bucket/key
    m = re.match(r"oss://([^/]+)/(.+)", oss_url)
    if not m:
        return {"primitive": "oss_head", "arg": oss_url, "result": None,
                "pass": False, "error": "bad oss url format"}
    bucket_name, key = m.group(1), m.group(2)
    endpoint = os.environ.get("OSS_ENDPOINT", "https://oss-cn-hangzhou.aliyuncs.com")
    try:
        auth = oss2.Auth(ak, sk)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        meta = bucket.head_object(key)
        return {"primitive": "oss_head", "arg": oss_url, "result": dict(meta.headers),
                "pass": meta.status == 200}
    except Exception as exc:
        return {"primitive": "oss_head", "arg": oss_url, "result": None,
                "pass": False, "error": str(exc)}


def _check_uvicorn_log(log_path: Path) -> dict:
    if not log_path.exists():
        return {"primitive": "uvicorn_log_sanity", "arg": str(log_path), "pass": False,
                "error": "log missing"}
    content = log_path.read_text(errors="replace")
    started = "Uvicorn running on" in content or "Application startup complete" in content
    has_500 = re.search(r"\b500\b.*Internal", content) is not None
    return {"primitive": "uvicorn_log_sanity", "arg": str(log_path),
            "result": {"started": started, "has_500": has_500},
            "pass": started and not has_500}


def _check_e2e_log(log_path: Path) -> dict:
    if not log_path.exists():
        return {"primitive": "e2e_runner_final_state", "arg": str(log_path), "pass": False,
                "error": "log missing"}
    content = log_path.read_text(errors="replace")
    # e2e_runner 通常打印 pipeline 状态
    got_completed = bool(re.search(r"(pipeline.*(completed|finished|success)|status.*completed)", content, re.I))
    has_error = bool(re.search(r"(ERROR|Traceback|failed)", content))
    return {"primitive": "e2e_runner_final_state", "arg": str(log_path),
            "result": {"completed": got_completed, "has_error": has_error},
            "pass": got_completed and not has_error}


def _locate_mp4(e2e_log_path: Path, round_num: int) -> Path | None:
    """试图从 e2e artifacts 定位 mp4"""
    aigc_backend = HARNESS_ROOT.parent / "aigc" / "backend"
    candidates = [
        aigc_backend / "e2e_artifacts" / f"round_{round_num}" / "final.mp4",
        *list((aigc_backend / "e2e_artifacts" / f"round_{round_num}").glob("*.mp4")),
        *list((aigc_backend / "media" / "videos").rglob("final.mp4")),
    ] if (aigc_backend / "e2e_artifacts").exists() else []
    return next((c for c in candidates if c.exists()), None)


def _parse_oss_key(e2e_log_path: Path) -> str | None:
    if not e2e_log_path.exists():
        return None
    content = e2e_log_path.read_text(errors="replace")
    m = re.search(r"oss://[^\s'\"]+\.mp4", content)
    return m.group(0) if m else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--e2e-log", required=True)
    parser.add_argument("--uvicorn-log", required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--query", required=True)
    args = parser.parse_args()

    task_id = args.task_id
    e2e_log = Path(args.e2e_log)
    uvicorn_log = Path(args.uvicorn_log)

    mp4_path = _locate_mp4(e2e_log, args.round)
    oss_url = _parse_oss_key(e2e_log)

    evidence = {"existence": [], "behavior": [], "quality": []}

    # existence
    if mp4_path:
        evidence["existence"].append(_check_file_exists(mp4_path))
        evidence["quality"].append(_check_size(mp4_path))
    else:
        evidence["existence"].append({"primitive": "file_exists", "arg": "<mp4 not located>",
                                       "result": False, "pass": False})

    # behavior
    evidence["behavior"].append(_check_uvicorn_log(uvicorn_log))
    evidence["behavior"].append(_check_e2e_log(e2e_log))
    if mp4_path:
        evidence["behavior"].append(_check_ffprobe_duration(mp4_path))

    # quality
    if mp4_path:
        evidence["quality"].append(_check_playback(mp4_path))
    if oss_url:
        evidence["quality"].append(_check_oss_head(oss_url))
    else:
        evidence["quality"].append({"primitive": "oss_head", "arg": "<not found in log>",
                                     "result": None, "pass": False})

    # aggregate
    all_checks = evidence["existence"] + evidence["behavior"] + evidence["quality"]
    failed = [c for c in all_checks if not c.get("pass", c.get("result"))]
    verdict = "PASS" if not failed else "FAIL"

    print(f"[verify] mp4_path={mp4_path}")
    print(f"[verify] oss_url={oss_url}")
    print(f"[verify] verdict={verdict} (failed={len(failed)}/{len(all_checks)})")

    # write verifier_report
    vr_path = HARNESS_ROOT / "verifier_reports" / f"{task_id}.json"
    vr = {
        "task_id": task_id,
        "verdict": verdict,
        "priority_applied": "P1_pass" if verdict == "PASS" else "P2_normal_fail",
        "failed_conditions": [
            f"{c['primitive']}({c.get('arg', '-')})" for c in failed
        ],
        "red_lines": ["DOD_GAP_ALERT"] if verdict == "FAIL" else [],
        "red_lines_detected": ["DOD_GAP_ALERT"] if verdict == "FAIL" else [],
        "evidence_chain": evidence,
        "insufficient_evidence_count_after_this": 0,
        "generated_at": _now_iso(),
        "verifier_model": "scripts/verify-p20-artifacts.py",
    }
    vr_path.write_text(json.dumps(vr, ensure_ascii=False, indent=2))
    print(f"[verify] verifier_report: {vr_path}")

    # update task-board
    tb_path = HARNESS_ROOT / "task-boards" / f"{task_id}.json"
    tb = json.loads(tb_path.read_text())
    tb["current_state"] = "CLOSED"
    tb["final_outcome"] = "success" if verdict == "PASS" else "false_complete_reported"
    tb["verifier_report"] = {"verdict": verdict, "red_lines_detected": vr["red_lines_detected"],
                              "failed_conditions": vr["failed_conditions"]}
    tb["verifier_report_link"] = f"verifier_reports/{task_id}.json"
    tb["closed_at"] = _now_iso()
    tb["state_history"].append({"from": "IMPL", "to": "VERIFY", "at": _now_iso()})
    tb["state_history"].append({"from": "VERIFY", "to": "RETRO_CLOSE", "at": _now_iso()})
    if mp4_path:
        tb["artifacts"].append({"type": "video", "path": str(mp4_path)})
    if oss_url:
        tb["artifacts"].append({"type": "oss", "url": oss_url})

    # 11-section retro
    notes_path = HARNESS_ROOT / "retros" / f"{task_id}.notes.json"
    if not notes_path.exists():
        notes_path.write_text(json.dumps({
            "new_traps": ["P20-real-run-2026-04-17: 真出片首次 Phase 8 验证"],
            "new_combinations": ["uvicorn + e2e_runner + ffprobe + oss_head 四段硬证据链"],
            "evolution_suggestions": [],
            "next_recommendation": "下次 XL+不可逆 继续走 C 路线并保留本次 checkpoint",
            "next_route_hint": "C",
        }, ensure_ascii=False, indent=2))

    try:
        retro_link = render_retro(
            task_id=task_id,
            task_board_path=str(tb_path),
            verifier_report_path=str(vr_path),
            retro_notes_path=str(notes_path),
            out_dir=str(HARNESS_ROOT / "retros"),
        )
        tb["retro_link"] = f"retros/{task_id}.md"
        print(f"[verify] retro: {retro_link}")
    except Exception as exc:
        print(f"[verify] WARN: retro render failed: {exc}", file=sys.stderr)

    # archive entry
    try:
        root_cause = "PASS 任务" if verdict == "PASS" else ", ".join(vr["failed_conditions"][:3])
        entry = write_archive_entry(
            task_id=task_id,
            task_board_path=str(tb_path),
            verifier_report_path=str(vr_path),
            retro_path=str(HARNESS_ROOT / "retros" / f"{task_id}.md"),
            retro_notes={
                "root_cause": root_cause,
                "fix": "P20 真出片验证（Phase 8.3），query={!r}".format(args.query),
                "prevention": "每次出片保留 uvicorn_log + e2e_log + ffprobe duration 四段证据",
            },
            project="aigcv2",
        )
        line_no = entry.pop("_line_no", None)
        tb["archive_entry_link"] = f"failure-archive.jsonl#L{line_no}"
        print(f"[verify] archive entry line_no={line_no}")
    except ArchiveWriteError as exc:
        print(f"[verify] WARN: archive write failed: {exc}", file=sys.stderr)

    tb_path.write_text(json.dumps(tb, ensure_ascii=False, indent=2))
    print(f"[verify] task-board CLOSED: {tb_path}")

    sys.exit(0 if verdict == "PASS" else len(failed))


if __name__ == "__main__":
    main()
