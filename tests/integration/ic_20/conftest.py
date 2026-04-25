"""IC-20 audit_chain_verify 测试 fixtures.

继承 tests/shared 的 fixture(real_event_bus / event_bus_root / project_id 等).
"""
from __future__ import annotations

# Re-export shared fixtures
from tests.shared.conftest import (  # noqa: F401
    audit_sink,
    callback_waiter,
    ckpt_root,
    delegate_stub,
    event_bus_root,
    fake_kb_repo,
    fake_llm,
    fake_reranker,
    fake_scope_checker,
    fake_skill_invoker,
    fake_tool_client,
    kb_root,
    lock_root,
    no_sleep,
    other_project_id,
    project_id,
    projects_root,
    real_event_bus,
    state_spy,
    tmp_root,
)
