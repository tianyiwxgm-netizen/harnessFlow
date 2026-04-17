"""
harnessFlow DoD verification primitive library.

Each primitive is a pure function `(args...) -> (actual, evidence_dict)`.
On dependency missing (e.g., ffprobe not installed) → raise DependencyMissing.
No other exceptions should leak; all failures return sentinel values and
record the reason in the evidence dict.

See method3.md § 6.1 bootstrap table for the canonical primitive list.
"""

from .errors import DependencyMissing
from .fs import file_exists, dir_exists, wc_lines, grep_count, retro_exists
from .video import ffprobe_duration, playback_check
from .oss import oss_head
from .http import curl_status, curl_json, uvicorn_started, vite_started
from .test_tools import (
    pytest_exit_code,
    pytest_all_green,
    playwright_nav,
    playwright_exit_code,
    type_check_exit_code,
)
from .screenshot import screenshot_has_content
from .schema import schema_valid
from .git_tools import no_public_api_breaking_change, diff_lines_net
from .perf import benchmark_regression_delta
from .docs import cross_refs_all_resolvable
from .review import code_review_verdict

TIER_MAP = {
    # existence
    "file_exists": "existence",
    "dir_exists": "existence",
    "retro_exists": "existence",
    # behavior
    "uvicorn_started": "behavior",
    "vite_started": "behavior",
    "curl_status": "behavior",
    "curl_json": "behavior",
    "playwright_nav": "behavior",
    "playwright_exit_code": "behavior",
    "pytest_exit_code": "behavior",
    "pytest_all_green": "behavior",
    "type_check_exit_code": "behavior",
    # quality
    "ffprobe_duration": "quality",
    "oss_head": "quality",
    "schema_valid": "quality",
    "code_review_verdict": "quality",
    "playback_check": "quality",
    "screenshot_has_content": "quality",
    "no_public_api_breaking_change": "quality",
    "wc_lines": "quality",
    "grep_count": "quality",
    "cross_refs_all_resolvable": "quality",
    "benchmark_regression_delta": "quality",
    "diff_lines_net": "quality",
}


def classify_tier(primitive: str) -> str:
    return TIER_MAP.get(primitive, "quality")


__all__ = [
    "DependencyMissing",
    "TIER_MAP",
    "classify_tier",
    "file_exists",
    "dir_exists",
    "wc_lines",
    "grep_count",
    "retro_exists",
    "ffprobe_duration",
    "playback_check",
    "oss_head",
    "curl_status",
    "curl_json",
    "uvicorn_started",
    "vite_started",
    "pytest_exit_code",
    "pytest_all_green",
    "playwright_nav",
    "playwright_exit_code",
    "type_check_exit_code",
    "screenshot_has_content",
    "schema_valid",
    "no_public_api_breaking_change",
    "diff_lines_net",
    "benchmark_regression_delta",
    "cross_refs_all_resolvable",
    "code_review_verdict",
]
