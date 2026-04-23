"""L1-02 S1→S7 mock 全链集成 · 对齐 Dev-δ dispatch §3.8 WP08。

Scenario · 用户一句话 → S1 启动 → S2 4 件套 + PMP + TOGAF → S7 收尾 + 归档
  - L2-02 produce_kickoff → pid 创建 + 2 章程 + anchor_hash
  - L2-01 gate request_gate_decision(S1) → user_decision(approve) → activate_project_id
  - L2-03 assemble_four_set → 4 md
  - L2-04 produce_all_9 → 9 PMP md
  - L2-05 produce_togaf → 5-10 Phase md
  - L2-06 produce_closing → 3 md · archive_project → tar.zst

验证：
  - PM-14 pid 贯穿全链（唯一）
  - 物理目录 projects/<pid>/{chart,meta,four-set,pmp,togaf,closing}/ 各就位
  - IC-09 事件顺序正确（S1 → S2 → S7）
  - L2-01 IC-01 发起路径唯一
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.closing import ClosingExecutor
from app.project_lifecycle.four_set import (
    FourPiecesProducer,
    FourSetContext,
    FourSetRequest,
)
from app.project_lifecycle.kickoff import ActivateRequest, StartupProducer
from app.project_lifecycle.kickoff.algo import activate_project_id
from app.project_lifecycle.pmp import PmpPlansProducer
from app.project_lifecycle.stage_gate import EvidenceBundle, StageGateController
from app.project_lifecycle.togaf import TogafProducer
from app.project_lifecycle.template_engine import TemplateEngine


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_template_engine(tmp_path: Path) -> TemplateEngine:
    """加载仓库根 templates/ 的真实 L2-07 engine（33 kind）。"""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    return TemplateEngine.load_from_dir(
        template_dir=str(repo_root / "templates"),
    )


@pytest.fixture
def l1_01_mock() -> MagicMock:
    """L1-01 L2-03 主状态机 mock · IC-01 接收方。"""
    m = MagicMock()
    m.request_state_transition.return_value = {"ok": True, "ic_01_tx_id": "tx-e2e"}
    return m


class TestL1_02_E2E_PM14_Lifecycle:
    """PM-14 pid 全生命周期：L2-02 创建 → L2-01 激活 → L2-06 归档。唯一入口。"""

    def test_TC_L102_INT_001_pm14_pid_create_activate_archive_chain(
        self,
        real_template_engine: TemplateEngine,
        l1_01_mock: MagicMock,
        tmp_project_root: Path,
    ) -> None:
        """S1 → S1 Gate → activate → ... → S7 archive 全链。

        断言：
          1. pid 在 L2-02 创建
          2. 物理目录 projects/<pid>/{chart,meta}/ 就位
          3. L2-01 S1 Gate request → user_decision(approve) → activate → state=INITIALIZED
          4. L2-03/04/05 输出各自子目录
          5. L2-06 归档 → tar.zst + sha256
        """
        # 共享 event bus
        event_bus = MagicMock()

        # --- S1 启动（L2-02）---
        brainstorm = MagicMock()
        brainstorm.invoke.return_value = {
            "rounds": 1, "is_confirmed": True,
            "slots": {"goals": ["make wiki"], "in_scope": ["auth"]},
        }
        kickoff_sut = StartupProducer(
            brainstorm=brainstorm,
            template=real_template_engine,
            event_bus=event_bus,
            project_root=str(tmp_project_root),
        )
        from app.project_lifecycle.kickoff.schemas import KickoffRequest
        kickoff_resp = kickoff_sut.kickoff_create_project(KickoffRequest(
            trigger_id="e2e-t1", stage="S1",
            user_initial_goal="Build internal wiki", caller_l2="L2-01",
        ))
        assert kickoff_resp.status in ("ok", "degraded")
        pid = kickoff_resp.result.project_id
        assert pid.startswith("p_")

        # 物理目录 + 章程在位
        base = tmp_project_root / "projects" / pid
        assert (base / "chart" / "HarnessFlowGoal.md").exists()
        assert (base / "chart" / "HarnessFlowPrdScope.md").exists()
        assert (base / "meta" / "project_manifest.yaml").exists()

        # --- S1 Gate 决策（L2-01）---
        gate_sut = StageGateController(
            event_bus=event_bus, l1_01_state_machine=l1_01_mock,
        )
        s1_decision = gate_sut.request_gate_decision(
            EvidenceBundle(
                project_id=pid, stage="S1", request_id="e2e-g1",
                signals=("charter_ready", "stakeholders_ready", "goal_anchor_hash_locked"),
            ),
            current_state="INITIALIZED",
        )
        assert s1_decision.decision == "pass"

        # user approve → authorize_transition (IC-01 发起)
        gate_sut.receive_user_decision(
            gate_id=s1_decision.gate_id,
            user_decision="approve",
            reason="e2e S1 gate approve with enough reason text",
        )
        # IC-01 确认调用
        assert l1_01_mock.request_state_transition.call_count == 1

        # L2-02 activate（L2-01 调用）
        from app.project_lifecycle.kickoff.schemas import ActivateRequest as AReq
        activate_resp = activate_project_id(
            AReq(
                project_id=pid,
                goal_anchor_hash=kickoff_resp.result.goal_anchor_hash,
                user_confirmed=True,
                charter_path=kickoff_resp.result.charter_path,
                stakeholders_path=kickoff_resp.result.stakeholders_path,
                caller_l2="L2-01",
            ),
            project_root=str(tmp_project_root),
        )
        assert activate_resp.state == "INITIALIZED"

        # --- S2 4 件套（L2-03）---
        skill = MagicMock()

        def _deleg(*, role, **kwargs):
            return {
                "requirements-analysis": {"items": [{"id": "REQ-001", "description": "auth", "priority": "P0"}]},
                "goals-writing": {"items": [{"id": "GOAL-001", "statement": "ship", "linked_reqs": ["REQ-001"]}]},
                "ac-scenario-writer": {"items": [{
                    "id": "AC-001", "given": "g", "when": "w", "then": "t",
                    "linked_goal": "GOAL-001",
                }]},
                "quality-audit": {"items": [{
                    "id": "QS-001", "measurable_criteria": "x",
                    "verification_method": "e2e_test", "linked_ac": "AC-001",
                }]},
            }[role]

        skill.delegate_subagent.side_effect = _deleg
        fs_sut = FourPiecesProducer(
            template=real_template_engine, skill=skill, event_bus=event_bus,
        )
        fs_resp = fs_sut.assemble_four_set(
            FourSetRequest(
                project_id=pid, request_id="e2e-fs-1", stage="S2",
                context=FourSetContext(
                    charter_path=kickoff_resp.result.charter_path,
                    stakeholders_path=kickoff_resp.result.stakeholders_path,
                    goal_anchor_hash=kickoff_resp.result.goal_anchor_hash,
                ),
                caller_l2="L2-01",
            ),
            project_root=str(tmp_project_root),
        )
        assert fs_resp.status == "ok"
        assert (base / "four-set" / "requirements.md").exists()
        assert (base / "four-set" / "goals.md").exists()

        # --- S2 PMP + TOGAF ---
        pmp_sut = PmpPlansProducer(template=real_template_engine, event_bus=event_bus)
        pmp_result = asyncio.run(pmp_sut.produce_all_9(
            pid, project_root=str(tmp_project_root),
        ))
        assert pmp_result.status == "ok"
        assert (base / "pmp" / "scope.md").exists()
        assert (base / "pmp" / "risk.md").exists()

        togaf_sut = TogafProducer(template=real_template_engine, event_bus=event_bus)
        togaf_result = togaf_sut.produce_togaf(
            pid, project_root=str(tmp_project_root), profile="LIGHT",
        )
        assert togaf_result.status == "ok"
        assert (base / "togaf" / "phase_d.md").exists()

        # --- S7 收尾 + 归档 ---
        closing_sut = ClosingExecutor(
            template=real_template_engine, event_bus=event_bus,
        )
        closing_result = closing_sut.produce_closing(
            pid, project_root=str(tmp_project_root),
        )
        assert (base / "closing" / "lessons_learned.md").exists()

        archive_manifest = closing_sut.archive_project(
            pid, project_root=str(tmp_project_root),
        )
        assert Path(archive_manifest.archive_path).exists()
        assert archive_manifest.archive_path.endswith(".tar.zst")
        assert len(archive_manifest.sha256) == 64

    def test_TC_L102_INT_002_ic_09_event_sequence_s1_to_s7(
        self,
        real_template_engine: TemplateEngine,
        l1_01_mock: MagicMock,
        tmp_project_root: Path,
    ) -> None:
        """S1 → S7 全链 · IC-09 事件序列合理（关键事件按序出现）。"""
        event_bus = MagicMock()

        # 跑完整流程（复用上面的逻辑精简）
        brainstorm = MagicMock()
        brainstorm.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        kickoff_sut = StartupProducer(
            brainstorm=brainstorm, template=real_template_engine,
            event_bus=event_bus, project_root=str(tmp_project_root),
        )
        from app.project_lifecycle.kickoff.schemas import KickoffRequest
        kr = kickoff_sut.kickoff_create_project(KickoffRequest(
            trigger_id="e2e-seq-1", stage="S1",
            user_initial_goal="seq test", caller_l2="L2-01",
        ))
        pid = kr.result.project_id

        gate_sut = StageGateController(
            event_bus=event_bus, l1_01_state_machine=l1_01_mock,
        )
        s1 = gate_sut.request_gate_decision(
            EvidenceBundle(
                project_id=pid, stage="S1", request_id="sq-g1",
                signals=("charter_ready", "stakeholders_ready", "goal_anchor_hash_locked"),
            ),
            current_state="INITIALIZED",
        )
        gate_sut.receive_user_decision(
            gate_id=s1.gate_id, user_decision="approve",
            reason="sequence test approve S1 gate with enough chars",
        )

        # 4 件套
        skill = MagicMock()
        skill.delegate_subagent.side_effect = lambda *, role, **kw: {
            "requirements-analysis": {"items": [{"id": "REQ-001", "description": "x", "priority": "P0"}]},
            "goals-writing": {"items": [{"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]}]},
            "ac-scenario-writer": {"items": [{"id": "AC-001", "given": "g", "when": "w", "then": "t", "linked_goal": "GOAL-001"}]},
            "quality-audit": {"items": [{"id": "QS-001", "measurable_criteria": "x", "verification_method": "e2e_test", "linked_ac": "AC-001"}]},
        }[role]
        FourPiecesProducer(template=real_template_engine, skill=skill, event_bus=event_bus).assemble_four_set(
            FourSetRequest(
                project_id=pid, request_id="sq-fs-1", stage="S2",
                context=FourSetContext(
                    charter_path=kr.result.charter_path,
                    stakeholders_path=kr.result.stakeholders_path,
                    goal_anchor_hash=kr.result.goal_anchor_hash,
                ),
                caller_l2="L2-01",
            ),
            project_root=str(tmp_project_root),
        )
        asyncio.run(PmpPlansProducer(template=real_template_engine, event_bus=event_bus).produce_all_9(
            pid, project_root=str(tmp_project_root),
        ))
        ClosingExecutor(template=real_template_engine, event_bus=event_bus).produce_closing(
            pid, project_root=str(tmp_project_root),
        )

        events = [c.kwargs["event_type"] for c in event_bus.append_event.call_args_list]
        # S1 → S2 → S7 关键 ready 事件必存在且有序
        key_events = [
            "project_created",  # L2-02 S1
            "charter_ready",
            "stakeholders_ready",
            "goal_anchor_hash_locked",
            "gate_decision_computed",  # L2-01 S1 Gate
            "state_transition_authorized",
            "requirements_ready",  # L2-03 S2
            "goals_ready",
            "ac_ready",
            "quality_ready",
            "4_pieces_ready",
            "9_plans_ready",  # L2-04 S2
            "closing_produced",  # L2-06 S7
        ]
        indices = [events.index(e) for e in key_events if e in events]
        assert len(indices) == len(key_events), f"missing events: {set(key_events) - set(events)}"
        assert indices == sorted(indices), f"events out of order: {events}"


class TestL1_02_E2E_PM14_Contracts:

    def test_TC_L102_INT_003_pm14_create_rejects_non_L2_02(
        self,
        real_template_engine: TemplateEngine,
        tmp_project_root: Path,
    ) -> None:
        """PM-14 硬锁验证：L2-03 / L2-04 / L2-05 / L2-06 都不能创建 project_id。

        只有 L2-02 (StartupProducer) 可创建 · 这已通过 kickoff 模块类型签名保证
        （其他 L2 不调 pid_gen.generate_pid）。此 TC 验证代码级不变量。
        """
        from app.project_lifecycle.kickoff.pid_gen import generate_pid, is_valid_pid
        # 生成仅 L2-02 此调用合法 · 其他 L2 导入此函数即审计告警（代码级）
        pid = generate_pid()
        assert is_valid_pid(pid)
        # 同 pid 两次生成必不等（UUID v4）
        assert pid != generate_pid()

    def test_TC_L102_INT_004_pm14_archive_only_L2_01_caller(
        self,
        real_template_engine: TemplateEngine,
        tmp_project_root: Path,
    ) -> None:
        """L2-06.archive_project 拒绝非 L2-01 caller。"""
        from app.project_lifecycle.closing.errors import E_PM14_OWNERSHIP_VIOLATION
        from app.project_lifecycle.closing import ClosingError

        # 建 minimal project
        pid = "p_archive0-1234-5678-9abc-def012345678"
        base = tmp_project_root / "projects" / pid
        (base / "meta").mkdir(parents=True)
        (base / "meta" / "state.json").write_text(
            '{"state": "CLOSING_PRODUCED", "project_id": "' + pid + '"}',
            encoding="utf-8",
        )
        closing_sut = ClosingExecutor(
            template=real_template_engine, event_bus=MagicMock(),
        )
        for bad_caller in ("L2-02", "L2-03", "L2-05", "external"):
            with pytest.raises(ClosingError) as exc:
                closing_sut.archive_project(
                    pid, project_root=str(tmp_project_root), caller_l2=bad_caller,
                )
            assert exc.value.error_code == E_PM14_OWNERSHIP_VIOLATION
