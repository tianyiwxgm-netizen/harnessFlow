"""L2-02 · 4 级偏差判定器 · 包入口。

Brief §3 简化版：
- 4 级 · INFO / WARN → IC-13 / ERROR → IC-14 / CRITICAL → IC-15
- 纯函数 · 确定性 · threshold_matrix YAML 配置
"""
from app.supervisor.deviation_judge.evaluator import (
    evaluate_deviation,
    filter_actionable,
)
from app.supervisor.deviation_judge.schemas import (
    DeviationError,
    DeviationLevel,
    DeviationVerdict,
    DimensionKey,
    DimensionThreshold,
    ThresholdMatrix,
)
from app.supervisor.deviation_judge.threshold_matrix import (
    default_matrix,
    load_matrix_from_dict,
    load_matrix_from_yaml,
)


# level → downstream IC 映射（下游 subagent 路由用）
LEVEL_TO_IC: dict[DeviationLevel, str | None] = {
    DeviationLevel.INFO: None,         # 仅记录
    DeviationLevel.WARN: "IC-13",      # push_suggestion
    DeviationLevel.ERROR: "IC-14",     # push_rollback_route
    DeviationLevel.CRITICAL: "IC-15",  # request_hard_halt
}


__all__ = [
    "evaluate_deviation",
    "filter_actionable",
    "DeviationError",
    "DeviationLevel",
    "DeviationVerdict",
    "DimensionKey",
    "DimensionThreshold",
    "ThresholdMatrix",
    "default_matrix",
    "load_matrix_from_dict",
    "load_matrix_from_yaml",
    "LEVEL_TO_IC",
]
