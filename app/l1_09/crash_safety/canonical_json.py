"""L2-05 · RFC 8785 JCS canonical JSON · 对齐 3-1 §6.3.1.

依赖 `jcs` PyPI 包（RFC 8785 JSON Canonicalization Scheme）· 版本钉死避免
跨版本 hash 不一致（见 3-1 §4.5 风险矩阵）.

关键规则（RFC 8785）：
- 键按 UTF-16 code unit 升序
- 整数无 trailing `.0`
- 浮点 ES6 `Number.toString`
- 只 escape 控制字符 + `\"` / `\\`
- 禁 `NaN` / `Infinity`
"""
from __future__ import annotations

from typing import Any

import jcs


def canonical_json_without_hash(event_body: dict[str, Any]) -> bytes:
    """序列化 event body 为 RFC 8785 canonical JSON bytes.

    规则：
    1. 去除 `hash` 字段（防自引用 · body 的 hash 字段是 hash 结果 · 不参与 hash 计算）
    2. jcs.canonicalize · RFC 8785 规范化 · 返 bytes (utf-8)

    不变量：
        - 对相同 body（不管键顺序）返相同 bytes
        - 对含 `hash` 字段 vs 去 `hash` 字段返相同 bytes
    """
    body_copy = {k: v for k, v in event_body.items() if k != "hash"}
    result = jcs.canonicalize(body_copy)
    # jcs 0.2+ 返 bytes · 钉死实现（RFC 8785）
    return bytes(result)
