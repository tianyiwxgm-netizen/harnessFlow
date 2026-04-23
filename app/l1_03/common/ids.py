"""L1-03 的 id 类型。

三类 id 都是 `str` 子类，带 regex 校验：
- `HarnessFlowProjectId`：`pid-{slug}` · PM-14 全系统根字段
- `WPId`：`wp-{slug}` · WBS 内唯一
- `TopologyId`：`topo-{slug}` · 装图版本号

生产环境里 slug 推荐 ulid / uuid-v7；本 v1 用宽松 `[0-9a-zA-Z][0-9a-zA-Z_-]*` 正则，
兼容单元测试里的 `pid-test / wp-01 / topo-v1` 风格。
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator

_ID_BODY = r"[0-9a-zA-Z][0-9a-zA-Z_-]*"
_PID_RE = re.compile(rf"^pid-{_ID_BODY}$")
_WP_RE = re.compile(rf"^wp-{_ID_BODY}$")
_TOPO_RE = re.compile(rf"^topo-{_ID_BODY}$")


def _check(pattern: re.Pattern[str], label: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be str, got {type(value).__name__}")
    if not pattern.match(value):
        raise ValueError(f"{label} {value!r} must match {pattern.pattern}")
    return value


def validate_project_id(v: str) -> str:
    return _check(_PID_RE, "project_id", v)


def validate_wp_id(v: str) -> str:
    return _check(_WP_RE, "wp_id", v)


def validate_topology_id(v: str) -> str:
    return _check(_TOPO_RE, "topology_id", v)


HarnessFlowProjectId = Annotated[str, AfterValidator(validate_project_id)]
"""PM-14 根字段 · 所有事件 / WP / Topology 必带。"""

WPId = Annotated[str, AfterValidator(validate_wp_id)]
"""WorkPackage 唯一 id，wbs-scope 内唯一。"""

TopologyId = Annotated[str, AfterValidator(validate_topology_id)]
"""Topology 版本号，每次 load_topology / diff_merge 后递增。"""
