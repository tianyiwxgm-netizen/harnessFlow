"""A6 · 空 pid / 错格式 / 系统保留 pid · 4 TC.

PM-14 §1: project_id 必合法 + 受 schema 拦.
- 空 pid → ValidationError(不落盘)
- 错格式(如大写 / 含特殊字符) → ValidationError
- 'system' 保留 pid → 允许写(L1-09 §3.9.2 system 级事件)
- 超长(>40) → ValidationError
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import assert_ic_09_emitted


class TestA6PidFormatViolations:
    """A6 · pid 格式校验 · 4 TC."""

    def test_a6_01_empty_pid_rejected(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
    ) -> None:
        """A6.1: pid='' 空字符串 · Pydantic ValidationError · 不落盘."""
        with pytest.raises(ValidationError):
            Event(
                project_id="",  # 空 pid
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={},
                timestamp=datetime.now(UTC),
            )

    def test_a6_02_invalid_format_uppercase_rejected(
        self,
    ) -> None:
        """A6.2: pid 含大写字母 · 不匹配 ^[a-z0-9_-]{1,40}$ · 拒.

        IC-09 §3.9.2 pattern 严格小写蛇形 + 数字 + - + _.
        """
        with pytest.raises(ValidationError):
            Event(
                project_id="ProjAlpha",  # 含大写
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={},
                timestamp=datetime.now(UTC),
            )

    def test_a6_03_too_long_pid_rejected(
        self,
    ) -> None:
        """A6.3: pid 长度 > 40 · ValidationError · 拒.

        PM-14 切片键长度上限 40 char.
        """
        long_pid = "a" * 41
        with pytest.raises(ValidationError):
            Event(
                project_id=long_pid,
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={},
                timestamp=datetime.now(UTC),
            )

    def test_a6_04_system_reserved_pid_accepted_for_system_events(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
    ) -> None:
        """A6.4: pid='system' 保留 · L1-09:bus_halted 等系统级事件可用.

        IC-09 §3.9.2 _SYSTEM_PROJECT_VALUES = {'system'} · 是合法值.
        """
        # 正常构造 + 落盘
        evt = Event(
            project_id="system",
            type="L1-09:meta_event_persisted",
            actor="audit_mirror",
            payload={"self_event_id": "evt_sys"},
            timestamp=datetime.now(UTC),
        )
        result = real_event_bus.append(evt)
        assert result.persisted is True
        # system 分片下应有 1 条
        assert_ic_09_emitted(
            event_bus_root,
            project_id="system",
            event_type="L1-09:meta_event_persisted",
            min_count=1,
        )
