"""archive.sequence_verifier — v1.5 main-skill 调度序列约束工具（fix defects #2）.

提供两层防御：
  1. loader.list_must_load_memories() — bootstrap 阶段列出必须 Read 的 feedback_workflow_* /
     feedback_prp_* memory 文件清单，主 skill § 2.1 step 3 强制装载。
  2. verifier.verify_route_sequence() — execute_route() 调度任何 ECC/SP skill 前调用，
     解析 flow-catalog.md 对应 § 提取 expected sequence，与 planned_steps 对比，缺/多/
     乱序 → 返回 mismatch 报告供主 skill / Supervisor 判 BLOCK。
"""
from .loader import (
    MEMORY_FILE_PATTERN,
    list_must_load_memories,
    read_must_load_memories,
)
from .verifier import (
    parse_flow_catalog_route,
    verify_route_sequence,
    SEQ_LINE_RE,
)

__all__ = [
    "MEMORY_FILE_PATTERN",
    "list_must_load_memories",
    "read_must_load_memories",
    "parse_flow_catalog_route",
    "verify_route_sequence",
    "SEQ_LINE_RE",
]
