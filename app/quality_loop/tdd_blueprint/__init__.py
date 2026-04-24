"""L1-04 L2-01 TDD 蓝图生成器 · 包入口。

源文档：
  docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-01-TDD 蓝图生成器.md
  docs/3-2-Solution-TDD/L1-04-Quality Loop/L2-01-TDD 蓝图生成器-tests.md

分工：
  - schemas          ·  Pydantic dataclass schema（请求 / 响应 / 聚合）
  - requirement_parser · prd / AC 文本 → 结构化 ACItem（模板匹配为主 · NLP/LLM 留下次）
  - coverage_planner · 按 GWT × 边界 × 错误码构建 ACMatrix / TestPyramid / CoverageTarget
  - blueprint_builder · 纯函数 Factory · 组装 TDDBlueprint + 主 generate_blueprint 入口
  - dod_adapter      · 依赖 WP01 DoD 编译器的接口适配层 · 当前 Mock

WP02 当前 token 预算 · 核心优先：parser + planner + builder + dod_adapter Mock。
真实 DoD 接入（WP01 完后）、perf SLO bench、e2e S3 Gate 链 · 留下次。
"""

from app.quality_loop.tdd_blueprint.blueprint_builder import TDDBlueprintGenerator
from app.quality_loop.tdd_blueprint.dod_adapter import DoDAdapter, MockDoDAdapter
from app.quality_loop.tdd_blueprint.schemas import (
    ACItem,
    ACMatrix,
    ACMatrixRow,
    BlueprintState,
    BroadcastReadyRequest,
    BroadcastReadyResponse,
    CoverageTarget,
    GenerateBlueprintRequest,
    GenerateBlueprintResponse,
    GetBlueprintQuery,
    GetBlueprintResponse,
    TDDBlueprint,
    TDDBlueprintError,
    TestEnvBlueprint,
    TestPyramid,
    ValidateCoverageQuery,
    ValidateCoverageResponse,
)

__all__ = [
    "TDDBlueprintGenerator",
    "DoDAdapter",
    "MockDoDAdapter",
    "ACItem",
    "ACMatrix",
    "ACMatrixRow",
    "BlueprintState",
    "BroadcastReadyRequest",
    "BroadcastReadyResponse",
    "CoverageTarget",
    "GenerateBlueprintRequest",
    "GenerateBlueprintResponse",
    "GetBlueprintQuery",
    "GetBlueprintResponse",
    "TDDBlueprint",
    "TDDBlueprintError",
    "TestEnvBlueprint",
    "TestPyramid",
    "ValidateCoverageQuery",
    "ValidateCoverageResponse",
]
