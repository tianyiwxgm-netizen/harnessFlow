"""Internal collaborators for TierManager · exposed for TDD injection.

These are intentionally simple in-memory structures. Persistent storage is
scoped to ``tier_manager.py`` + file layout; the collaborators here track
active projects, session slots, isolation rules, and post-filter audit.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .errors import TierError, TierErrorCode

# ---------------------------------------------------------------------------
# TierLayoutRepo · active project registry
# ---------------------------------------------------------------------------


@dataclass
class _ProjectTiers:
    project: bool = False
    global_: bool = True


class TierLayoutRepo:
    """Tracks which projects have tier-ready for each layer.

    Two concept lists are tracked separately:

    - ``_tiers``:   per-pid activation flags (set via ``set_tier_ready``,
                    consulted by ``is_activated``). Populated by
                    ``on_project_activated`` and by test fixtures.
    - ``_scan_list``: the explicit projects the expire-scanner should walk.
                    Rewritten by ``register_projects`` (replace semantics)
                    so tests can control scan scope without coupling to
                    the activation set.
    """

    def __init__(
        self,
        fs_root: Path,
        layout_path: Path,
        on_corrupt: Callable[[], None] | None = None,  # noqa: F821 - forward ref
    ) -> None:
        self._fs_root = fs_root
        self._layout_path = layout_path
        self._tiers: dict[str, _ProjectTiers] = {}
        self._scan_list: list[str] | None = None
        self._lock = threading.RLock()
        self._on_corrupt = on_corrupt

    # Query -----------------------------------------------------------------

    def is_activated(self, pid: str, layer: str = "project") -> bool:
        with self._lock:
            t = self._tiers.get(pid)
            if t is None:
                return False
            return {"session": True, "project": t.project, "global": t.global_}[layer]

    def list_all_projects(self) -> list[str]:
        """Return the effective scan list.

        If ``register_projects`` has been called, exactly those pids are
        returned; otherwise fall back to every tier-ready pid.
        """
        with self._lock:
            if self._scan_list is not None:
                return list(self._scan_list)
            return sorted(self._tiers.keys())

    # Mutate ----------------------------------------------------------------

    def set_tier_ready(
        self, pid: str, *, project: bool = True, global_: bool = True
    ) -> None:
        with self._lock:
            self._tiers[pid] = _ProjectTiers(project=project, global_=global_)

    def register_projects(self, pids: list[str]) -> None:
        """Replace the scan list AND ensure tier-ready for each pid."""
        with self._lock:
            self._scan_list = list(pids)
            for pid in pids:
                if pid not in self._tiers:
                    self._tiers[pid] = _ProjectTiers(project=True, global_=True)

    def reload(self) -> None:
        """Reload layout from yaml. Raises TierError on parse failure.

        Always calls ``yaml.safe_load`` (even on a missing file, with empty
        content), so monkey-patched corruption can be exercised from tests.
        """
        try:
            content = ""
            if self._layout_path.exists():
                content = self._layout_path.read_text()
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            if self._on_corrupt is not None:
                self._on_corrupt()
            raise TierError(TierErrorCode.TIER_REGISTRY_CORRUPT, str(e)) from e


# ---------------------------------------------------------------------------
# SessionIndex · sessions + dedup + per-session entry metadata
# ---------------------------------------------------------------------------


@dataclass
class _EntryMeta:
    entry_id: str
    last_observed_at: str = ""


class SessionIndex:
    """Tracks (project_id, session_id) → registered; dedup by title+kind."""

    def __init__(self) -> None:
        self._sessions: dict[str, set[str]] = {}  # pid → {session_id}
        self._dedup: dict[tuple[str, str, str, str], str] = {}
        self._entries: dict[tuple[str, str], dict[str, _EntryMeta]] = {}
        self._lock = threading.RLock()

    # Sessions --------------------------------------------------------------

    def register_session(self, pid: str, session_id: str) -> None:
        with self._lock:
            self._sessions.setdefault(pid, set()).add(session_id)

    def belongs_to(self, session_id: str, pid: str) -> bool:
        with self._lock:
            return session_id in self._sessions.get(pid, set())

    # Dedup -----------------------------------------------------------------

    def register(
        self,
        *,
        project_id: str,
        session_id: str,
        title: str,
        kind: str,
        entry_id: str,
    ) -> None:
        with self._lock:
            self._dedup[(project_id, session_id, title, kind)] = entry_id

    def lookup_dedup(
        self, *, project_id: str, session_id: str, title: str, kind: str
    ) -> str | None:
        with self._lock:
            return self._dedup.get((project_id, session_id, title, kind))

    # Entry metadata --------------------------------------------------------

    def add_entry(
        self, *, project_id: str, session_id: str, entry_id: str, last_observed_at: str
    ) -> None:
        with self._lock:
            bucket = self._entries.setdefault((project_id, session_id), {})
            bucket[entry_id] = _EntryMeta(entry_id=entry_id, last_observed_at=last_observed_at)

    def entries_for(self, project_id: str, session_id: str) -> list[_EntryMeta]:
        with self._lock:
            return list(self._entries.get((project_id, session_id), {}).values())


# ---------------------------------------------------------------------------
# IsolationEnforcer · PM-14 cross-project guard with test hook
# ---------------------------------------------------------------------------


class IsolationEnforcer:
    """Decides whether accessor_pid may read a given owner_pid at given scope.

    Tests can ``force_cross_project(accessor, owner)`` to simulate a bug where
    a caller drifts outside its project boundary.
    """

    def __init__(self) -> None:
        self._forced: dict[str, str] = {}  # accessor_pid → forced owner_pid

    def force_cross_project(self, accessor_pid: str, target_owner_pid: str) -> None:
        self._forced[accessor_pid] = target_owner_pid

    def check_project_layer(self, accessor_pid: str, owner_pid: str) -> bool:
        forced = self._forced.get(accessor_pid)
        if forced is not None and forced != accessor_pid:
            return False
        return accessor_pid == owner_pid

    def forced_owner_for(self, accessor_pid: str) -> str | None:
        return self._forced.get(accessor_pid)


# ---------------------------------------------------------------------------
# AuditTracker · records post-filter decisions for test inspection
# ---------------------------------------------------------------------------


@dataclass
class AuditTracker:
    expired_post_filter_log: list[str] = field(default_factory=list)

    def mark_expired(self, entry_id: str) -> None:
        if entry_id not in self.expired_post_filter_log:
            self.expired_post_filter_log.append(entry_id)


# ---------------------------------------------------------------------------
# SchemaValidator · jsonschema per kind
# ---------------------------------------------------------------------------

# Keep schemas tiny + purpose-built for WP01. Later phases may reload from
# ``projects/<pid>/kb/schemas/<kind>.schema.json`` (ADR-03 hard whitelist).

_BASE_CONTENT_MIN = 1
_BASE_CONTENT_MAX = 1_048_576  # 1 MiB cap; tests assert 10 MiB content rejected


def _schema_for_kind(kind: str) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["id", "scope", "kind", "title", "content"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "scope": {"type": "string", "enum": ["session"]},
            "kind": {"type": "string", "enum": [kind]},
            "title": {"type": "string", "minLength": 1, "maxLength": 1024},
            "content": {
                "type": "string",
                "minLength": _BASE_CONTENT_MIN,
                "maxLength": _BASE_CONTENT_MAX,
            },
            "observed_count": {"type": "integer", "minimum": 1},
        },
    }


class SchemaValidator:
    """jsonschema Draft-2020-12 validator with per-kind compiled schemas."""

    def __init__(self) -> None:
        from jsonschema import Draft202012Validator  # local import (lazy deps)

        self._validators: dict[str, Any] = {}
        self._driver = Draft202012Validator

    def _get(self, kind: str) -> Any:
        v = self._validators.get(kind)
        if v is None:
            v = self._driver(_schema_for_kind(kind))
            self._validators[kind] = v
        return v

    def validate(self, entry: dict[str, Any]) -> tuple[bool, list[dict[str, str]]]:
        kind = entry.get("kind", "")
        validator = self._get(kind)
        violations: list[dict[str, str]] = []
        for err in validator.iter_errors(entry):
            field_path = ".".join(str(p) for p in err.absolute_path) or "<root>"
            violations.append(
                {
                    "field": field_path,
                    "rule": str(err.validator),
                    "message": err.message,
                }
            )
        return (not violations, violations)
