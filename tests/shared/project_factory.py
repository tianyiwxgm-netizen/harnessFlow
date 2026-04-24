"""tests/shared/project_factory.py · 干净 project 构造器(M3-WP01).

**定位**:
    给跨 L1 集成测试一个**一行就能构造干净 project** 的工厂 fixture.
    初始化全套 artifact: chart(2-prd 4 件套) · wbs(L1-03) · tdd(main-1 L1-04) ·
    quality(gate) · kb(L1-06 三层) · gate_state(L1-02).

**非目标**(给后续 WP 留):
    - 不跑真实 LLM · 不调外部 skill · 不落真 git commit
    - 只写占位 json / 目录占位 · 保证 **schema 合法 · 路径可读**
    - 给 acceptance scenario-02(S1→S7 全链) 留 hook: 可按 stage 往里填真实 artifact

**M3-WP01 的"干净"定义**(参考 3-1 L1集成 §4.2 project_boot 协议):
    projects/<pid>/
        chart/
            charter.md          · 2-prd 4 件套 · 商业机会 / 业务目标
            plan.md             · 9-plans · PMI PMBOK 9 计划
            requirements.md     · MoSCoW / User Story / 验收
            risk.md             · 风险登记 · risk_path 指向
        architecture/
            adr.md              · TOGAF Phase D ADR
            togaf.md            · Phase A-H 阶段性产出
        wbs/
            wbs.json            · {wps: []} · L1-03 topology 空骨架
            topology.json       · {nodes: [], edges: []} · 空 DAG
        tdd/                    · main-1 TDD 规划产物根
            .keep
        quality/                · main-1 gate / verifier 根
            .keep
        kb/                     · L1-06 session scope · {entries: []}
            session.jsonl
        gates/                  · L1-02 gate_state 落地 · {current_stage: S1, gate_state: WAITING}
            state.json

**用法**:
    def test_something(project_factory):
        pid = "proj-xyz"
        project = project_factory(pid)
        assert project.pid == pid
        assert project.chart_dir.exists()
        # 可往 project.chart_dir / "charter.md" 追加内容测场景
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class ProjectWorkspace:
    """单个 project 的工作目录快照 · 所有关键路径预算好 · 测试可直接读写."""

    pid: str
    root: Path  # projects/<pid>/

    # 2-prd 4 件套
    chart_dir: Path
    charter_path: Path
    plan_path: Path
    requirements_path: Path
    risk_path: Path

    # TOGAF
    arch_dir: Path
    adr_path: Path
    togaf_path: Path

    # L1-03 WBS + DAG
    wbs_dir: Path
    wbs_path: Path
    topology_path: Path

    # main-1 TDD / quality
    tdd_dir: Path
    quality_dir: Path

    # L1-06 KB session scope
    kb_dir: Path
    kb_session_path: Path

    # L1-02 Gate state
    gates_dir: Path
    gate_state_path: Path

    def charter_content(self, text: str) -> None:
        """往 charter.md 追加内容(供 scenario 填充业务机会)."""
        self.charter_path.write_text(text, encoding="utf-8")

    def wbs_seed(self, wps: list[dict]) -> None:
        """把 wbs.json 置换为种子 WP 列表(供集成测 S3→S4→S5 链)."""
        self.wbs_path.write_text(
            json.dumps({"project_id": self.pid, "wps": wps}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def advance_gate(self, current_stage: str, gate_state: str = "WAITING") -> None:
        """推进 L1-02 gate_state(供 acceptance scenario_03 rework 测)."""
        self.gate_state_path.write_text(
            json.dumps(
                {
                    "project_id": self.pid,
                    "current_stage": current_stage,
                    "gate_state": gate_state,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def _make_project(projects_root: Path, pid: str) -> ProjectWorkspace:
    """在 projects_root 下实例化一个 pid 目录 · 写全 placeholder 文件.

    所有子目录必创建 · 关键文件用合法 JSON 空骨架预填(下游可直接读不崩).
    """
    root = projects_root / pid
    root.mkdir(parents=True, exist_ok=True)

    # ---------- 2-prd 4 件套 ----------
    chart_dir = root / "chart"
    chart_dir.mkdir(exist_ok=True)
    charter_path = chart_dir / "charter.md"
    charter_path.write_text(
        f"# Project Charter · {pid}\n\n- business_opportunity: TBD\n- objectives: TBD\n",
        encoding="utf-8",
    )
    plan_path = chart_dir / "plan.md"
    plan_path.write_text("# Plan · 9 PMBOK 计划占位\n", encoding="utf-8")
    requirements_path = chart_dir / "requirements.md"
    requirements_path.write_text("# Requirements · MoSCoW\n- must: []\n", encoding="utf-8")
    risk_path = chart_dir / "risk.md"
    risk_path.write_text("# Risk Register\n- risks: []\n", encoding="utf-8")

    # ---------- TOGAF ----------
    arch_dir = root / "architecture"
    arch_dir.mkdir(exist_ok=True)
    adr_path = arch_dir / "adr.md"
    adr_path.write_text("# ADR · placeholder\n", encoding="utf-8")
    togaf_path = arch_dir / "togaf.md"
    togaf_path.write_text("# TOGAF Phase A-H · placeholder\n", encoding="utf-8")

    # ---------- L1-03 WBS + DAG ----------
    wbs_dir = root / "wbs"
    wbs_dir.mkdir(exist_ok=True)
    wbs_path = wbs_dir / "wbs.json"
    wbs_path.write_text(
        json.dumps({"project_id": pid, "wps": []}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    topology_path = wbs_dir / "topology.json"
    topology_path.write_text(
        json.dumps({"project_id": pid, "nodes": [], "edges": []}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ---------- main-1 TDD / quality ----------
    tdd_dir = root / "tdd"
    tdd_dir.mkdir(exist_ok=True)
    (tdd_dir / ".keep").touch()
    quality_dir = root / "quality"
    quality_dir.mkdir(exist_ok=True)
    (quality_dir / ".keep").touch()

    # ---------- L1-06 KB session ----------
    kb_dir = root / "kb"
    kb_dir.mkdir(exist_ok=True)
    kb_session_path = kb_dir / "session.jsonl"
    kb_session_path.write_text("", encoding="utf-8")  # 空 jsonl · 下游 reader 需 tolerant

    # ---------- L1-02 Gate state ----------
    gates_dir = root / "gates"
    gates_dir.mkdir(exist_ok=True)
    gate_state_path = gates_dir / "state.json"
    gate_state_path.write_text(
        json.dumps(
            {
                "project_id": pid,
                "current_stage": "S1",
                "gate_state": "WAITING",
                "gates_history": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return ProjectWorkspace(
        pid=pid,
        root=root,
        chart_dir=chart_dir,
        charter_path=charter_path,
        plan_path=plan_path,
        requirements_path=requirements_path,
        risk_path=risk_path,
        arch_dir=arch_dir,
        adr_path=adr_path,
        togaf_path=togaf_path,
        wbs_dir=wbs_dir,
        wbs_path=wbs_path,
        topology_path=topology_path,
        tdd_dir=tdd_dir,
        quality_dir=quality_dir,
        kb_dir=kb_dir,
        kb_session_path=kb_session_path,
        gates_dir=gates_dir,
        gate_state_path=gate_state_path,
    )


@pytest.fixture
def project_factory(projects_root: Path):
    """一行构造干净 project 的工厂 · 返 ProjectWorkspace.

    用法:
        def test_foo(project_factory):
            p = project_factory("proj-xyz")
            # p.charter_path / p.wbs_path ... 全部可直接读写

        def test_bar(project_factory):
            # 同一 TC 内可构造多个(PM-14 多 pid 场景):
            foo = project_factory("proj-foo")
            bar = project_factory("proj-bar")
            assert foo.root != bar.root
    """
    def _factory(pid: str) -> ProjectWorkspace:
        return _make_project(projects_root, pid)

    return _factory


@pytest.fixture
def project_workspace(project_factory, project_id: str) -> ProjectWorkspace:
    """单 pid 默认 workspace · 用 project_id fixture 的默认值(proj-m3-shared).

    最常用的一行 fixture:
        def test_foo(project_workspace):
            assert project_workspace.chart_dir.exists()
    """
    return project_factory(project_id)
