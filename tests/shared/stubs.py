"""tests/shared/stubs.py · 跨 L1 mock 基础设施(M3-WP01).

**定位**:
    给集成测试**边界**层提供**最小可信替身**· 只替换"跨进程 / 外部服务 / 烧钱"
    边界, app/ 内部 L1 逻辑全部真 import.

**边界场景分类**:
    1. **L1-02 StateTransitionSpy** · L1-02 真实是跨进程状态机 · spy 记录即验契约
    2. **L1-05 DelegateVerifierStub** · verifier 独立 session 起 sub-agent · stub 直返
    3. **Callback waiter** · verifier 异步回调 · stub 预置结果避 poll
    4. **L1-06 FakeKB{Repo,ScopeChecker,Reranker}** · KB 3 层实际读是文件系统 · fake 返 in-memory
    5. **LLM / skill** · 烧钱调用 · fake 返预置 output
    6. **AuditSink** · L1-09 旁路 emit sink(替代真 bus 用)

**铁律**:
    - 所有 stub 构造时**只接 pure data** · 不触网络 / 不写盘 / 不起进程
    - stub 自身**不做业务逻辑** · 只记录调用 + 返预置值
    - PM-14: 凡是接 pid 字段的 stub · 记录必带 pid · 供跨分片隔离断言

**与 tests/integration/l1_04_cross_l1/conftest.py 的关系**:
    - 本模块是 WP09 stub 的**提炼版 + 通用化** · M3 其他 WP 直接 import 本模块
    - WP09 局部 conftest 的 stub 语义保持向后兼容(可再升级为 re-export)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# =============================================================================
# L1-02 IC-01 state_transition spy
# =============================================================================


@dataclass
class StateTransitionSpy:
    """L1-02 IC-01 state_transition 测试替身 · 记录调用 · 返 OK.

    真实 L1-02 实现(Dev-δ merged) 是跨进程状态机 · 在集成层无法直接挂进程.
    本 spy 验证 L1-04 → L1-02 契约字段完整(pid + wp_id + new_wp_state +
    escalated + route_id + 可选 target_stage/severity/level_count).

    用法:
        spy = StateTransitionSpy()
        await rollback_executor.execute(deps=Deps(state_transition=spy.state_transition), ...)
        assert_state_transition_to(spy.calls, wp_id="wp-1", new_wp_state="retry_s3")
    """

    calls: list[dict[str, Any]] = field(default_factory=list)

    async def state_transition(
        self,
        *,
        project_id: str,
        wp_id: str,
        new_wp_state: str,
        escalated: bool,
        route_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        record = {
            "project_id": project_id,
            "wp_id": wp_id,
            "new_wp_state": new_wp_state,
            "escalated": escalated,
            "route_id": route_id,
            **extra,
        }
        self.calls.append(record)
        return {"transitioned": True, **record}


# =============================================================================
# L1-05 IC-20 delegate_verifier stub
# =============================================================================


@dataclass
class DelegateVerifierStub:
    """L1-05 IC-20 delegate_verifier 测试替身 · 模拟独立 session 分配.

    真实 Dev-γ delegator 会起 sub-agent session · 消耗 token / API.
    本 stub 直接返 dispatched=True + `sub-*` 前缀合法 session_id · 保证
    L1-04 verifier orchestrator 的 IC-20 前缀硬红线校验通过.

    **错误注入**: error_queue 长度 >= 调用次序时 · 对应位置为 Exception 则抛该异常.
    供测试重试路径 / 降级路径:
        stub.error_queue = [TimeoutError("t1"), None]
        # 第 1 次 raise TimeoutError · 第 2 次正常返回
    """

    session_prefix: str = "sub-m3"
    calls: list[Any] = field(default_factory=list)
    error_queue: list[Exception | None] = field(default_factory=list)

    async def delegate_verifier(self, command: Any) -> Any:
        """统一 entry · 入参应为 IC20Command · 返 IC20DispatchResult."""
        from app.quality_loop.verifier.schemas import IC20DispatchResult

        self.calls.append(command)
        idx = len(self.calls) - 1
        if idx < len(self.error_queue):
            err = self.error_queue[idx]
            if err is not None:
                raise err
        delegation_id = getattr(command, "delegation_id", None) or f"del-{idx + 1}"
        return IC20DispatchResult(
            delegation_id=delegation_id,
            dispatched=True,
            verifier_session_id=f"{self.session_prefix}-{len(self.calls):03d}",
        )


# =============================================================================
# Verifier callback waiter stub
# =============================================================================


@dataclass
class CallbackWaiterStub:
    """verifier 独立 session 回调等待器 · in-memory 预置结果.

    真实实现: 订阅 L1-09 事件 verifier_verdict · 或 poll verifier_reports/<sid>.json.
    集成侧只验契约 payload 格式 · stub 直返预置结果 · 避 poll + 避 DB.
    """

    output: dict[str, Any] | None = None
    exc: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def wait(
        self,
        *,
        delegation_id: str,
        verifier_session_id: str,
        timeout_s: int,
    ) -> dict[str, Any]:
        self.calls.append({
            "delegation_id": delegation_id,
            "verifier_session_id": verifier_session_id,
            "timeout_s": timeout_s,
        })
        if self.exc is not None:
            raise self.exc
        return dict(self.output or {})


# =============================================================================
# L1-06 KB 3 层读替身
# =============================================================================


@dataclass
class FakeKBRepo:
    """L1-06 KB repo 极简 in-memory 实现 · 返预置条目.

    给 DoD 编译时 kb_read 用(main-1 WP01 DodCompiler) · 不走文件系统.
    """

    session_entries: list[Any] = field(default_factory=list)
    project_entries: list[Any] = field(default_factory=list)
    global_entries: list[Any] = field(default_factory=list)

    def read_session(self, _ctx: Any, _kinds: Any) -> list[Any]:
        return list(self.session_entries)

    def read_project(self, _ctx: Any, _kinds: Any) -> list[Any]:
        return list(self.project_entries)

    def read_global(self, _kinds: Any) -> list[Any]:
        return list(self.global_entries)


@dataclass
class FakeScopeChecker:
    """L1-06 scope_checker 替身 · 允许指定 scope 集.

    默认全允许(session/project/global) · 按需窄化:
        FakeScopeChecker(allowed=["session"])
    """

    allowed: list[str] = field(default_factory=lambda: ["session", "project", "global"])

    def scope_check(self, req: Any) -> Any:
        from app.knowledge_base.reader.schemas import ScopeCheckResult

        return ScopeCheckResult(
            allowed_scopes=list(self.allowed),
            isolation_ctx={"project_id": req.project_id},
        )


@dataclass
class FakeReranker:
    """L1-06 reranker 替身 · 按 observed_count DESC 简单排序."""

    def rerank(self, req: Any) -> Any:
        from app.knowledge_base.reader.schemas import RerankResponse

        ranked = sorted(
            req.candidates,
            key=lambda e: -int(getattr(e, "observed_count", 0) or 0),
        )[: req.top_k]
        return RerankResponse(ranked=ranked, signals_used=["observed_count"])


# =============================================================================
# LLM / Skill 通用 stub(烧钱调用替身)
# =============================================================================


@dataclass
class FakeLLMClient:
    """通用 LLM 调用替身 · 按 prompt 前缀映射到预置响应.

    用法:
        llm = FakeLLMClient(responses={
            "generate_script": "draft_v1",
            "default": "mock_response",
        })
        # 任意调用 llm.complete(prompt) / llm.chat(messages)
    """

    responses: dict[str, str] = field(default_factory=lambda: {"default": "mock"})
    call_log: list[dict[str, Any]] = field(default_factory=list)

    def _pick(self, prompt_or_msgs: Any) -> str:
        key = ""
        if isinstance(prompt_or_msgs, str):
            key = prompt_or_msgs[:60]
        for k, v in self.responses.items():
            if k == "default":
                continue
            if k in str(prompt_or_msgs):
                return v
        return self.responses.get("default", "mock")

    async def complete(self, prompt: str, **kw: Any) -> str:
        self.call_log.append({"method": "complete", "prompt": prompt, "kw": kw})
        return self._pick(prompt)

    async def chat(self, messages: list[dict[str, Any]], **kw: Any) -> str:
        self.call_log.append({"method": "chat", "messages": messages, "kw": kw})
        return self._pick(messages)


@dataclass
class FakeSkillInvoker:
    """L1-05 skill invoke 替身 · 返预置 SkillResult 形态数据.

    跟 app.skill_dispatch.invoker 对齐 · 按 skill_id 映射预置 output.
    """

    outputs: dict[str, Any] = field(default_factory=dict)
    call_log: list[dict[str, Any]] = field(default_factory=list)
    error_queue: list[Exception | None] = field(default_factory=list)

    async def invoke(self, *, skill_id: str, args: dict[str, Any], **kw: Any) -> Any:
        self.call_log.append({"skill_id": skill_id, "args": dict(args), "kw": kw})
        idx = len(self.call_log) - 1
        if idx < len(self.error_queue):
            err = self.error_queue[idx]
            if err is not None:
                raise err
        return self.outputs.get(skill_id, {"status": "ok", "skill_id": skill_id})


# =============================================================================
# AuditSink · 替代真 L1-09 EventBus 旁路接 audit 事件
# =============================================================================


@dataclass
class AuditSink:
    """极简 audit sink · 用于 L1-06 KBReadService 等模块的 _emit 钩子.

    不取代 real_event_bus · 仅在**某些测试场景只要记事件不要 bus 功能**时用.
    """

    events: list[dict[str, Any]] = field(default_factory=list)

    def append(self, *, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append({"type": event_type, "payload": dict(payload)})


# =============================================================================
# Tool call mock(L1-05 / L1-08 统一工具调用替身)
# =============================================================================


@dataclass
class FakeToolClient:
    """通用工具调用替身 · 按 tool_name 映射 output · 支持错误注入.

    对齐 skill_dispatch.invoker / multimodal.router 的工具接口概念.
    """

    outputs: dict[str, Any] = field(default_factory=dict)
    call_log: list[dict[str, Any]] = field(default_factory=list)
    error_queue: list[Exception | None] = field(default_factory=list)

    async def call(self, tool_name: str, args: dict[str, Any]) -> Any:
        self.call_log.append({"tool": tool_name, "args": dict(args)})
        idx = len(self.call_log) - 1
        if idx < len(self.error_queue):
            err = self.error_queue[idx]
            if err is not None:
                raise err
        return self.outputs.get(tool_name, {"ok": True})
