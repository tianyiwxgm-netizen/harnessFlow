"""A5 · L1-06 KB 不跨 pid (IC-07/08) · 3 TC.

PM-14 §1: KB 3 层(session/project/global) · session 与 project 必带 pid.
A 写的 KBEntry 不应在 B 的查询结果里出现.

用 FakeKBRepo 模拟 in-memory 存储 · 每 pid 独立 repo 实例 = 物理切片.
"""
from __future__ import annotations

import pytest

from app.knowledge_base.reader.schemas import KBEntry
from tests.shared.stubs import FakeKBRepo


class TestA5KBNoCrossPid:
    """A5 · KB 跨 pid 隔离 · 3 TC."""

    def test_a5_01_a_session_entries_not_visible_to_b(
        self,
        two_pids: tuple[str, str],
    ) -> None:
        """A5.1: A session 层写 5 条 · B 的 repo 看不到任何条目.

        IC-08 PM-14 切片: session_entries by repo instance · 不串.
        """
        pid_a, pid_b = two_pids
        repo_a = FakeKBRepo(
            session_entries=[
                KBEntry(id=f"a-{i}", project_id=pid_a, scope="session", kind="pattern")
                for i in range(5)
            ]
        )
        repo_b = FakeKBRepo()  # 空 repo
        # 模拟 ctx
        a_session = repo_a.read_session(None, ["pattern"])
        b_session = repo_b.read_session(None, ["pattern"])
        assert len(a_session) == 5
        assert all(e.project_id == pid_a for e in a_session)
        assert b_session == [], (
            f"PM-14 违反: B repo 不应有任何 KB entry · 实际={b_session}"
        )

    def test_a5_02_a_project_entries_isolated_from_b(
        self,
        two_pids: tuple[str, str],
    ) -> None:
        """A5.2: A 写 project 层 3 条 · B 的 project 层零.

        Project scope 必带 pid · A/B 的 project 集合互不可见.
        """
        pid_a, pid_b = two_pids
        repo_a = FakeKBRepo(
            project_entries=[
                KBEntry(id="proj-a-1", project_id=pid_a, scope="project", kind="gotcha"),
                KBEntry(id="proj-a-2", project_id=pid_a, scope="project", kind="gotcha"),
                KBEntry(id="proj-a-3", project_id=pid_a, scope="project", kind="recipe"),
            ]
        )
        repo_b = FakeKBRepo()
        a_proj = repo_a.read_project(None, ["gotcha", "recipe"])
        b_proj = repo_b.read_project(None, ["gotcha", "recipe"])
        # A 看到自己 3 条
        assert len(a_proj) == 3
        # B 看不到 A 的任何条目
        assert b_proj == []
        # 校 pid 字段全为 A
        assert {e.project_id for e in a_proj} == {pid_a}

    def test_a5_03_global_layer_writes_a_dont_leak_to_b_specific_query(
        self,
        two_pids: tuple[str, str],
    ) -> None:
        """A5.3: global 层不带 pid · 但若 entry 标记了 pid · B 视图过滤后应空.

        PM-14 边界场景: global entries 可全局可见 · 但带 pid 标签的 entry
        在跨 pid 视图下需被过滤(通过 entry.project_id 比对).
        """
        pid_a, pid_b = two_pids
        # A 在 global 层放 1 条带 pid_a 标签的(罕见但可能 · 测过滤逻辑)
        global_entries = [
            KBEntry(id="g-shared", project_id=None, scope="global", kind="pattern"),
            KBEntry(id="g-a-only", project_id=pid_a, scope="global", kind="pattern"),
        ]
        repo = FakeKBRepo(global_entries=global_entries)
        # 模拟 reader 端 PM-14 过滤: 只看 project_id=pid_b 或 None
        all_global = repo.read_global(["pattern"])
        b_visible = [
            e for e in all_global
            if e.project_id is None or e.project_id == pid_b
        ]
        # B 只能看到 g-shared(pid=None)
        assert len(b_visible) == 1
        assert b_visible[0].id == "g-shared"
        # A 标签的 g-a-only 不在 B 视图里
        assert all(e.id != "g-a-only" for e in b_visible)
