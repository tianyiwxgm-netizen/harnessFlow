"""prd / AC 文本 → 结构化 ACItem · §6.3 三级流水线的 Tier-1（模板匹配）实现。

当前 WP02 token 预算下：
  Tier 1 · 模板匹配 · 覆盖 Gherkin "Given/When/Then" + "必须/应当/禁止" 关键词
  Tier 2 · spaCy lemmatizer · 留下次（依赖 external model 装载）
  Tier 3 · LLM fallback   · 留下次（等 DoD 编译器 + L1-05 invoke_skill 真实接入）

所有 parse 失败的条款会进入 failed_ac_ids 列表 · 由 builder 转成
E_L204_L201_BLUEPRINT_AC_MISSING 走 AWAITING_CLARIFY 路径。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from app.quality_loop.tdd_blueprint.schemas import ACItem


# ---------------------------------------------------------------------------
# 模板库（§6.3 Tier 1 · 覆盖 ~60% 标准 AC）
# ---------------------------------------------------------------------------

_GHERKIN = re.compile(
    r"""
    (?:
        Given\s+(?P<given>.+?)
        \s+When\s+(?P<when>.+?)
        \s+Then\s+(?P<then>.+)
    )
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)

_MUST_PATTERNS = (
    re.compile(r"必须\s*(.+)"),
    re.compile(r"应当\s*(.+)"),
    re.compile(r"应\s*(.+)"),
    re.compile(r"shall\s+(.+)", re.IGNORECASE),
    re.compile(r"must\s+(.+)", re.IGNORECASE),
)

_FORBID_PATTERNS = (
    re.compile(r"禁止\s*(.+)"),
    re.compile(r"不得\s*(.+)"),
    re.compile(r"不允许\s*(.+)"),
    re.compile(r"禁\s*(.+)"),
    re.compile(r"shall\s+not\s+(.+)", re.IGNORECASE),
)

# AC 类型识别（§6.4 _classify_ac_kind）
_KIND_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ui", ("UI", "界面", "点击", "按钮", "页面", "展示", "frontend", "用户可见")),
    ("collab", ("调用", "协作", "API", "集成", "服务", "跨模块", "事件总线")),
    ("data", ("数据", "计算", "算法", "存储", "hash", "parse", "纯函数")),
)


# ---------------------------------------------------------------------------
# 预处理 + 切分
# ---------------------------------------------------------------------------


def split_ac_candidates(raw_text: str) -> list[str]:
    """按编号/空行/连续换行切分 AC 清单文本。"""
    if not raw_text or not raw_text.strip():
        return []
    # 先按双换行切段，再去除条目前的编号前缀
    blocks = re.split(r"\n\s*\n", raw_text.strip())
    items: list[str] = []
    numbered = re.compile(r"^\s*(?:\d+[\.\)、]|\-|\*|#+)\s*")
    for block in blocks:
        for line in block.splitlines():
            text = line.strip()
            if not text:
                continue
            text = numbered.sub("", text).strip()
            if text:
                items.append(text)
    return items


def _classify_kind(text: str) -> str:
    lowered = text.lower()
    for kind, hints in _KIND_HINTS:
        for h in hints:
            if h.lower() in lowered:
                return kind
    return "mixed"


def _template_match(text: str) -> dict[str, object] | None:
    """Tier 1 · 模板匹配 · 命中返回结构化 dict · 未命中返回 None。"""
    gh = _GHERKIN.search(text)
    if gh:
        return {
            "template": "gherkin",
            "given": gh.group("given").strip(),
            "when": gh.group("when").strip(),
            "then": gh.group("then").strip(),
        }
    for pat in _FORBID_PATTERNS:
        m = pat.search(text)
        if m:
            return {
                "template": "forbid",
                "action": m.group(1).strip(),
                "expected": "forbidden",
            }
    for pat in _MUST_PATTERNS:
        m = pat.search(text)
        if m:
            return {
                "template": "must",
                "action": m.group(1).strip(),
                "expected": "required",
            }
    return None


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


@dataclass
class ParseReport:
    parsed: list[ACItem]
    failed_ac_ids: list[str]

    @property
    def ok(self) -> bool:
        return not self.failed_ac_ids


def parse_ac_clauses(
    candidates: Iterable[str],
    *,
    allow_unstructured_fallback: bool = True,
) -> ParseReport:
    """对一组候选 AC 文本做 Tier-1 结构化 · 可选退化到 "raw fallback" 以避免假阴性。

    allow_unstructured_fallback=True · 若模板未命中则保留为 ACItem(kind=mixed, tier=1,
    confidence=0.3)，给 builder 机会分配 1 个 unit slot。这是为了 WP02 阶段绕开 Tier 2/3 · 避
    免对所有非标准 AC 都 raise。

    allow_unstructured_fallback=False · 严格模式（用于错误路径测试）· 未命中即 failed。
    """
    parsed: list[ACItem] = []
    failed: list[str] = []
    for idx, raw in enumerate(candidates):
        ac_id = f"AC-{idx+1:03d}"
        if not raw or not raw.strip():
            failed.append(ac_id)
            continue
        tmpl = _template_match(raw)
        kind = _classify_kind(raw)
        if tmpl is not None:
            parsed.append(
                ACItem(
                    id=ac_id,
                    raw_text=raw.strip(),
                    kind=kind,
                    parse_tier=1,
                    confidence=1.0,
                    structured=tmpl,
                )
            )
            continue
        if allow_unstructured_fallback:
            parsed.append(
                ACItem(
                    id=ac_id,
                    raw_text=raw.strip(),
                    kind=kind,
                    parse_tier=1,
                    confidence=0.3,
                    structured={"template": "fallback_raw", "raw": raw.strip()},
                )
            )
            continue
        failed.append(ac_id)
    return ParseReport(parsed=parsed, failed_ac_ids=failed)


def synth_clauses_for_count(
    count: int,
    *,
    seed_text: str = "系统必须验证输入",
) -> list[str]:
    """当上游没有真实 AC 文本时 · builder 可合成一组可 parse 的 dummy 文本。

    用于 WP02 单测 · 不走真实文件读（真实文件读 + hash 一致性校验留下次）。
    """
    if count <= 0:
        return []
    out: list[str] = []
    for i in range(count):
        if i % 4 == 0:
            out.append(f"必须 用户能成功提交表单（第 {i+1} 条）")
        elif i % 4 == 1:
            out.append(
                f"Given 已登录用户 When 点击保存按钮 Then 数据被持久化到数据库（第 {i+1} 条 UI）"
            )
        elif i % 4 == 2:
            out.append(f"禁止 未授权用户访问数据（第 {i+1} 条）")
        else:
            out.append(f"{seed_text}，数据哈希必须稳定（第 {i+1} 条 算法）")
    return out


def ac_clauses_hash(clauses: list[str]) -> str:
    """稳定 hash · 便于幂等 cache key（§3.1）。"""
    h = hashlib.sha256()
    for c in clauses:
        h.update(c.encode("utf-8"))
        h.update(b"\n")
    return "sha256:" + h.hexdigest()


__all__ = [
    "ParseReport",
    "parse_ac_clauses",
    "split_ac_candidates",
    "synth_clauses_for_count",
    "ac_clauses_hash",
]
