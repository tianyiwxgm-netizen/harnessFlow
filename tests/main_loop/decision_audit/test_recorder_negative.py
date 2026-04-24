"""L2-05 负向用例 · §11.1 10 项 E_AUDIT_* 全覆盖 + FLUSH_CONCURRENT.

对齐 3-2 §3 · TC-L101-L205-101~111 + 108b.
"""
from __future__ import annotations

import threading

import pytest

from app.main_loop.decision_audit.errors import AuditError


# ---------------------------------------------------------------------------
# record_audit 侧错误码
# ---------------------------------------------------------------------------


def test_TC_L101_L205_106_no_project_id_rejected(sut, make_audit_cmd) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=None, linked_tick="tick-001",
        reason="no pid", evidence=["evt-1"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_NO_PROJECT_ID"


def test_TC_L101_L205_107_no_reason_rejected(sut, mock_project_id, make_audit_cmd) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-001",
        reason="", evidence=["evt-1"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_NO_REASON"
    meta = [a for a in sut.get_recent_audits() if a.event_type == "L1-01:audit_rejected"]
    assert len(meta) >= 1


def test_TC_L101_L205_108_cross_project_rejected(sut, mock_project_id, make_audit_cmd) -> None:
    sut._register_tick("tick-other-pid", project_id="pid-OTHER-018f4a3b-9999-7000-FFFF")
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-other-pid",
        reason="wrong pid", evidence=["evt-1"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_CROSS_PROJECT"


def test_TC_L101_L205_109_unknown_event_type_rejected(sut, mock_project_id, make_audit_cmd) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="frobnicate_the_widget",
        project_id=mock_project_id, linked_tick="tick-001",
        reason="invalid action", evidence=["evt-1"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_EVENT_TYPE_UNKNOWN"


def test_TC_L101_L205_105_halt_on_fail_rejects_silently(sut, mock_project_id, make_audit_cmd) -> None:
    sut._force_halted()
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-after-halt",
        reason="should be rejected", evidence=["evt-x"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_HALT_ON_FAIL"
    assert sut.buffer_size() == 0


def test_TC_L101_L205_110_stale_buffer_force_flush_and_warn(sut, mock_project_id, make_audit_cmd) -> None:
    tick_a = "tick-stale-A"
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick=tick_a,
        reason="stale buffer fixture", evidence=["evt-a"],
    ))
    tick_b = "tick-next-B"
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick=tick_b,
        reason="next tick", evidence=["evt-b"],
    ))
    warns = [a for a in sut.get_recent_audits() if a.error_code == "E_AUDIT_STALE_BUFFER"]
    assert len(warns) == 1
    from_index = sut.query_by_tick(tick_id=tick_a, project_id=mock_project_id, include_buffered=False)
    assert from_index.count >= 1


# ---------------------------------------------------------------------------
# flush_buffer 侧错误码
# ---------------------------------------------------------------------------


def test_TC_L101_L205_101_write_fail_halts_l1(
    sut, mock_project_id, mock_event_bus, mock_l2_01_client, make_audit_cmd
) -> None:
    mock_event_bus.append_event.side_effect = IOError("disk full")
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-001",
        reason="write fail scenario", evidence=["evt-1"],
    ))
    with pytest.raises(AuditError) as exc:
        sut.flush_buffer(force=True, reason="tick_boundary")
    assert exc.value.error_code == "E_AUDIT_WRITE_FAIL"
    mock_l2_01_client.on_halt_signal.assert_called_once()
    payload = mock_l2_01_client.on_halt_signal.call_args.kwargs
    assert payload["source"] == "L2-05"
    assert payload["reason"] == "E_AUDIT_WRITE_FAIL"


def test_TC_L101_L205_104_hash_broken_warn_not_halt(
    sut, mock_project_id, mock_event_bus, mock_l1_07_client, make_audit_cmd
) -> None:
    mock_event_bus.get_last_hash.side_effect = [
        "ffff" * 16,  # 第 1 次 mismatch
        "ffff" * 16,  # retry mismatch
    ]
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-001",
        reason="hash mismatch scenario", evidence=["evt-1"],
    ))
    fr = sut.flush_buffer(force=True, reason="tick_boundary")
    assert fr.flushed_count == 1
    mock_l1_07_client.alert.assert_called_once()
    alert_payload = mock_l1_07_client.alert.call_args.kwargs
    assert alert_payload["error_code"] == "E_AUDIT_HASH_BROKEN"
    assert sut.current_state() != "HALTED"


def test_TC_L101_L205_111_flush_concurrent_waits_on_semaphore(
    sut, mock_project_id, make_audit_cmd
) -> None:
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-conc",
        reason="flush concurrent scenario", evidence=["evt-c"],
    ))
    results: list = []
    errors: list = []

    def worker() -> None:
        try:
            results.append(sut.flush_buffer(force=True, reason="tick_boundary"))
        except AuditError as e:
            errors.append(e)

    th1 = threading.Thread(target=worker)
    th2 = threading.Thread(target=worker)
    th1.start(); th2.start()
    th1.join(timeout=2); th2.join(timeout=2)
    assert len(results) == 2
    flushed_counts = sorted([r.flushed_count for r in results])
    assert flushed_counts == [0, 1]
    assert len(errors) == 0


# ---------------------------------------------------------------------------
# buffer overflow + query miss / cross
# ---------------------------------------------------------------------------


def test_TC_L101_L205_102_buffer_overflow_triggers_sync_flush(
    sut, mock_project_id, make_audit_cmd
) -> None:
    for i in range(64):
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=f"tick-{i}",
            reason=f"trigger {i}", evidence=[f"evt-{i}"],
        ))
    assert sut.buffer_size() == 64
    cmd_65 = make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-overflow",
        reason="trigger overflow", evidence=["evt-overflow"],
    )
    r = sut.record_audit(cmd_65)
    assert r.buffered is False
    assert r.event_id is not None
    audits = [a for a in sut.get_recent_audits() if a.error_code == "E_AUDIT_BUFFER_OVERFLOW"]
    assert len(audits) >= 1
    assert audits[0].level == "WARN"


def test_TC_L101_L205_103_query_miss_returns_empty_not_exception(sut, mock_project_id) -> None:
    r = sut.query_by_tick(tick_id="tick-ghost", project_id=mock_project_id, include_buffered=True)
    assert r.count == 0
    assert r.entries == []
    assert r.source in ("not_found", "buffer")


def test_TC_L101_L205_108b_query_cross_project_rejected(sut, mock_project_id, make_audit_cmd) -> None:
    tick_id = "tick-cross-query"
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick=tick_id,
        reason="cross-project query scenario", evidence=["evt-1"],
    ))
    with pytest.raises(AuditError) as exc:
        sut.query_by_tick(
            tick_id=tick_id,
            project_id="pid-OTHER-018f4a3b-9999-7000-FFFF",
            include_buffered=True,
        )
    assert exc.value.error_code == "E_AUDIT_CROSS_PROJECT"
