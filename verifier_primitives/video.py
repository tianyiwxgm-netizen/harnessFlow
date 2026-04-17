"""Video primitives: ffprobe_duration / playback_check."""

import os
import tempfile
from pathlib import Path

from ._shell import run


def ffprobe_duration(path: str) -> tuple[float, dict]:
    p = Path(path)
    if not p.is_file():
        return -1.0, {"path": str(p), "error": "not_a_file"}
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(p),
        ],
        require="ffprobe",
        timeout=15.0,
    )
    out = result["stdout"].strip()
    try:
        dur = float(out)
    except ValueError:
        return -1.0, {"path": str(p), "ffprobe": result, "error": "unparseable_duration"}
    return dur, {"path": str(p), "ffprobe": result, "duration_s": dur}


def playback_check(path: str, sample_time: str = "00:00:03") -> tuple[bool, dict]:
    """Extract a single frame and ensure it exists + nonzero size + not fully black.

    'Not black' is approximated by average pixel brightness check via ffmpeg's
    `blackdetect` filter. If ffmpeg isn't available → DependencyMissing.
    """
    p = Path(path)
    if not p.is_file():
        return False, {"path": str(p), "error": "not_a_file"}

    with tempfile.TemporaryDirectory() as tmpd:
        frame = Path(tmpd) / "frame.png"
        extract = run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                sample_time,
                "-i",
                str(p),
                "-vframes",
                "1",
                str(frame),
            ],
            require="ffmpeg",
            timeout=30.0,
        )
        if extract["exit_code"] != 0 or not frame.is_file() or frame.stat().st_size == 0:
            return False, {
                "path": str(p),
                "frame_extract": extract,
                "frame_exists": frame.is_file(),
                "error": "frame_extract_failed",
            }

        blackdetect = run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "info",
                "-i",
                str(p),
                "-vf",
                "blackdetect=d=2:pic_th=0.98",
                "-an",
                "-f",
                "null",
                "-",
            ],
            require="ffmpeg",
            timeout=60.0,
        )
        black_lines = [
            line for line in blackdetect["stderr"].splitlines() if "blackdetect" in line
        ]
        all_black = len(black_lines) > 0 and any("black_duration" in line for line in black_lines)
        return (not all_black), {
            "path": str(p),
            "sample_time": sample_time,
            "frame_bytes": frame.stat().st_size,
            "blackdetect_stderr_lines": black_lines[:10],
            "all_black": all_black,
        }
