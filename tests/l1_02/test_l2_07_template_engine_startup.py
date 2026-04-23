"""L2-07 启动阶段 · TemplateLoader 相关 TC。

对齐 3-2 TDD md §3（TC-104 / TC-115）+ §5 SLO（TC-016 加载 ≤ 500ms）+ §2 正向基础（TC-010/011）。
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.l1_02.template_engine.errors import (
    E_TEMPLATE_SYNTAX_ERROR,
    StartupError,
    TemplateEngineError,
)
from app.l1_02.template_engine.registry import REQUIRED_KINDS_DEFAULT, TemplateLoader


def _write_minimal_tpl(fp: Path, kind: str) -> None:
    """写最小合法模板（slot_schema 仅 required x:string · 正文仅 {{ x }}）。"""
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(
        "---\n"
        f"kind: {kind}\n"
        "version: v1.0\n"
        "slot_schema:\n"
        "  type: object\n"
        "  required: [x]\n"
        "  properties:\n"
        "    x: {type: string}\n"
        "description: minimal test template\n"
        "author: test\n"
        "created_at: 2026-04-23\n"
        "---\n"
        "# t\n{{ x }}\n",
        encoding="utf-8",
    )


class TestL2_07_Startup:
    """TemplateLoader 启动期行为。"""

    def test_TC_L102_L207_115_missing_required_kinds_raises_startup_error(
        self, tmp_path: Path,
    ) -> None:
        """只放 1 个 kind · 缺 28 · StartupError crash（tech §6.3 required_kinds）。"""
        _write_minimal_tpl(tmp_path / "kickoff" / "goal.md", "kickoff.goal")
        loader = TemplateLoader(template_dir=str(tmp_path))
        with pytest.raises(StartupError) as exc:
            loader.load_all()
        assert "Missing required templates" in str(exc.value)

    def test_TC_L102_L207_104_bad_jinja_syntax_raises_template_engine_error(
        self, tmp_path: Path,
    ) -> None:
        """模板含 Jinja2 语法错 · 启动 E_L102_L207_004。"""
        bad = tmp_path / "kickoff" / "goal.md"
        bad.parent.mkdir(parents=True)
        bad.write_text(
            "---\nkind: kickoff.goal\nversion: v1.0\n"
            "slot_schema:\n  type: object\n  required: [x]\n"
            "  properties: {x: {type: string}}\n"
            "description: bad\nauthor: t\ncreated_at: 2026-04-23\n---\n"
            "{% for x in %}{{ x }}{% endfor %}\n",
            encoding="utf-8",
        )
        loader = TemplateLoader(
            template_dir=str(tmp_path),
            required_kinds=["kickoff.goal"],  # 绕过 29 完整性
        )
        with pytest.raises(TemplateEngineError) as exc:
            loader.load_all()
        assert exc.value.error_code == E_TEMPLATE_SYNTAX_ERROR

    def test_TC_L102_L207_016_load_real_29_templates_warm_p95_under_500ms(
        self, template_dir_real: Path,
    ) -> None:
        """启动加载 29 模板 · warm-cache P95 ≤ 500ms · cold ≤ 3s hard（tech §12.1）。

        SLO 语义：P95 指稳态（warm）· cold first-import 的一次性税不计入。
        取 5 次采样中的 median 作为 P50 · max 作为 P95（样本太小故用 max）。
        """
        loader = TemplateLoader(template_dir=str(template_dir_real))
        # 预热：一次加载触发 Jinja2 模块完整 import + 29 模板首次 compile
        cold_start = time.perf_counter()
        registry = loader.load_all()
        cold_ms = (time.perf_counter() - cold_start) * 1000
        assert cold_ms < 3000, f"cold startup exceeded hard SLO: {cold_ms:.0f}ms"

        # 5 次稳态采样
        samples: list[float] = []
        for _ in range(5):
            t = time.perf_counter()
            loader.load_all()
            samples.append((time.perf_counter() - t) * 1000)
        samples.sort()
        p50 = samples[2]
        p95 = samples[-1]  # 小样本近似

        assert p95 < 500, f"warm P95 {p95:.0f}ms > 500ms (samples={[f'{s:.0f}' for s in samples]})"
        assert p50 < 200, f"warm P50 {p50:.0f}ms > 200ms (samples={[f'{s:.0f}' for s in samples]})"

        kinds = registry.kinds()
        for k in REQUIRED_KINDS_DEFAULT:
            assert k in kinds, f"missing kind: {k}"

    def test_TC_L102_L207_011_get_template_version_returns_semver(
        self, template_dir_real: Path,
    ) -> None:
        loader = TemplateLoader(template_dir=str(template_dir_real))
        registry = loader.load_all()
        assert registry.get_version("kickoff.goal") == "v1.0"
        assert registry.get_version("pmp.scope") == "v1.0"
        assert registry.get_version("nonexistent.kind") is None

    def test_TC_L102_L207_010_list_returns_all_29(
        self, template_dir_real: Path,
    ) -> None:
        loader = TemplateLoader(template_dir=str(template_dir_real))
        registry = loader.load_all()
        kinds = registry.list()
        assert isinstance(kinds, list)
        assert len(kinds) >= 29
        required_sample = {
            "kickoff.goal", "kickoff.scope",
            "fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd",
            "pmp.scope", "pmp.cost", "pmp.risk",
            "togaf.preliminary", "togaf.phase_a", "togaf.adr",
            "closing.lessons_learned",
        }
        assert required_sample.issubset(set(kinds))

    def test_TC_L102_L207_016b_missing_dir_raises_startup_error(
        self, tmp_path: Path,
    ) -> None:
        """template_dir 不存在 · StartupError。"""
        missing = tmp_path / "does-not-exist"
        loader = TemplateLoader(template_dir=str(missing))
        with pytest.raises(StartupError):
            loader.load_all()
