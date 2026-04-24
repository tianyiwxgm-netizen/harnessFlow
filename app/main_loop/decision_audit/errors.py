"""L2-05 错误码 · 对齐 3-1 §11.1 10 项 + §3 补充 3 项.

语义:
    - `E_AUDIT_WRITE_FAIL` · Critical · 必 halt L1(send halt_signal to L2-01)
    - `E_AUDIT_BUFFER_OVERFLOW` · Major · 降级为同步 flush + WARN
    - `E_AUDIT_QUERY_MISS` · Minor · 返空(非异常 · 但 AuditError.raised 可发起)
    - `E_AUDIT_HASH_BROKEN` · Major · WARN 不 halt(重查 L1-09 last_hash 后按当前 tip 重算)
    - `E_AUDIT_HALT_ON_FAIL` · Minor · halt 状态下 record_audit 拒绝
    - `E_AUDIT_NO_PROJECT_ID` · Minor · PM-14 根字段缺失
    - `E_AUDIT_NO_REASON` · Minor · 审计违规元事件
    - `E_AUDIT_CROSS_PROJECT` · Minor · project_id 错配
    - `E_AUDIT_EVENT_TYPE_UNKNOWN` · Minor · source_ic + action 不在白名单
    - `E_AUDIT_STALE_BUFFER` · Minor · tick 未 flush 残留 · 下 tick 自救
    - `E_AUDIT_FLUSH_CONCURRENT` · 运行时 · 并发 flush 走 semaphore
    - `E_AUDIT_QUERY_TIMEOUT` · 运行时 · 扫 jsonl 超时
    - `E_AUDIT_REPLAY_TIMEOUT` · 运行时 · replay 超时 · partial=true
    - `E_AUDIT_UNAUDITED_DECISION` · **Goal §4.1 铁律** · 未审计的决策(release blocker)
"""
from __future__ import annotations

from typing import Any


# 错误码常量(字符串 · 对齐 TDD 断言 `exc.value.error_code == "E_AUDIT_..."`)
E_AUDIT_WRITE_FAIL = "E_AUDIT_WRITE_FAIL"
E_AUDIT_BUFFER_OVERFLOW = "E_AUDIT_BUFFER_OVERFLOW"
E_AUDIT_QUERY_MISS = "E_AUDIT_QUERY_MISS"
E_AUDIT_HASH_BROKEN = "E_AUDIT_HASH_BROKEN"
E_AUDIT_HALT_ON_FAIL = "E_AUDIT_HALT_ON_FAIL"
E_AUDIT_NO_PROJECT_ID = "E_AUDIT_NO_PROJECT_ID"
E_AUDIT_NO_REASON = "E_AUDIT_NO_REASON"
E_AUDIT_CROSS_PROJECT = "E_AUDIT_CROSS_PROJECT"
E_AUDIT_EVENT_TYPE_UNKNOWN = "E_AUDIT_EVENT_TYPE_UNKNOWN"
E_AUDIT_STALE_BUFFER = "E_AUDIT_STALE_BUFFER"
E_AUDIT_FLUSH_CONCURRENT = "E_AUDIT_FLUSH_CONCURRENT"
E_AUDIT_QUERY_TIMEOUT = "E_AUDIT_QUERY_TIMEOUT"
E_AUDIT_REPLAY_TIMEOUT = "E_AUDIT_REPLAY_TIMEOUT"
E_AUDIT_UNAUDITED_DECISION = "E_AUDIT_UNAUDITED_DECISION"


class AuditError(Exception):
    """L2-05 所有审计错误基类.

    使用:
        raise AuditError("message", error_code=E_AUDIT_WRITE_FAIL)
        raise AuditError(error_code=E_AUDIT_HALT_ON_FAIL)

    属性:
        error_code: 对应 §11.1 错误码字符串 · **必填**(调用方 pattern 匹配)
        level: "CRITICAL" | "MAJOR" | "MINOR" · 默认 MINOR
        cause: 可选 · 嵌套异常描述
        extra: 可选 · 调试元信息
    """

    def __init__(
        self,
        message: str = "",
        *,
        error_code: str,
        level: str = "MINOR",
        cause: str | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(message or error_code)
        self.error_code = error_code
        self.level = level
        self.cause = cause
        self.extra = extra

    def __repr__(self) -> str:
        return f"AuditError({self.error_code}, level={self.level}, msg={self.args[0]!r})"


# 错误码到默认等级映射(供 Recorder 构造异常时用)
ERROR_LEVELS: dict[str, str] = {
    E_AUDIT_WRITE_FAIL: "CRITICAL",
    E_AUDIT_BUFFER_OVERFLOW: "MAJOR",
    E_AUDIT_HASH_BROKEN: "MAJOR",
    E_AUDIT_UNAUDITED_DECISION: "CRITICAL",
    # 其它均为 MINOR
    E_AUDIT_QUERY_MISS: "MINOR",
    E_AUDIT_HALT_ON_FAIL: "MINOR",
    E_AUDIT_NO_PROJECT_ID: "MINOR",
    E_AUDIT_NO_REASON: "MINOR",
    E_AUDIT_CROSS_PROJECT: "MINOR",
    E_AUDIT_EVENT_TYPE_UNKNOWN: "MINOR",
    E_AUDIT_STALE_BUFFER: "MINOR",
    E_AUDIT_FLUSH_CONCURRENT: "MINOR",
    E_AUDIT_QUERY_TIMEOUT: "MINOR",
    E_AUDIT_REPLAY_TIMEOUT: "MINOR",
}


def make_audit_error(error_code: str, message: str = "", **kwargs: Any) -> AuditError:
    """工厂 · 按 error_code 自动查 level."""
    level = ERROR_LEVELS.get(error_code, "MINOR")
    return AuditError(message, error_code=error_code, level=level, **kwargs)


__all__ = [
    "AuditError",
    "ERROR_LEVELS",
    "make_audit_error",
    # codes
    "E_AUDIT_WRITE_FAIL",
    "E_AUDIT_BUFFER_OVERFLOW",
    "E_AUDIT_QUERY_MISS",
    "E_AUDIT_HASH_BROKEN",
    "E_AUDIT_HALT_ON_FAIL",
    "E_AUDIT_NO_PROJECT_ID",
    "E_AUDIT_NO_REASON",
    "E_AUDIT_CROSS_PROJECT",
    "E_AUDIT_EVENT_TYPE_UNKNOWN",
    "E_AUDIT_STALE_BUFFER",
    "E_AUDIT_FLUSH_CONCURRENT",
    "E_AUDIT_QUERY_TIMEOUT",
    "E_AUDIT_REPLAY_TIMEOUT",
    "E_AUDIT_UNAUDITED_DECISION",
]
