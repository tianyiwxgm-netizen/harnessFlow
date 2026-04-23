"""L1-02 跨 L2 共享枚举 / 值对象。"""
from __future__ import annotations

from enum import Enum


class CallerL2(str, Enum):
    """L1-02 7 个 L2 的调用方身份枚举（含 L2-01 · 因 L2-01 也会调 L2-07 渲染 Gate 卡片）。"""

    L2_01 = "L2-01"
    L2_02 = "L2-02"
    L2_03 = "L2-03"
    L2_04 = "L2-04"
    L2_05 = "L2-05"
    L2_06 = "L2-06"
    L2_07 = "L2-07"
