"""L2-07 SLO 性能基准 · 对齐 3-2 TDD md §5 + tech §12.1。

6 个 SLO 指标：
| 指标 | P50 | P95 | 硬上限 |
|:---|:---|:---|:---|
| 单次 render_template | 20ms | 100ms | 2s |
| slot jsonschema 校验 | 1ms | 5ms | 100ms |
| Jinja2 sandbox 渲染 | 10ms | 50ms | 1s |
| output hash 计算 (200KB) | 5ms | 20ms | 200ms |
| 启动加载 27 模板 | 200ms | 500ms | 3s（covered in startup tests）|
| 并发 50 render | — | — | — |

测试策略：warm-cache · N=20 样本 · 用 max 作为 P95 近似（小样本）。
"""
from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from app.l1_02.template_engine.engine import TemplateEngine
from app.l1_02.template_engine.hashing import compute_output_hash


@pytest.fixture
def sut(template_dir_real, mock_event_bus) -> TemplateEngine:
    return TemplateEngine.load_from_dir(
        template_dir=str(template_dir_real),
        event_emitter=mock_event_bus,
    )


def _p95(samples: list[float]) -> float:
    """N 样本的简化 P95 · 取排序后 ceil(0.95·N) 位。"""
    s = sorted(samples)
    idx = int(len(s) * 0.95) - 1
    idx = max(0, min(idx, len(s) - 1))
    return s[idx]


def _p50(samples: list[float]) -> float:
    s = sorted(samples)
    return s[len(s) // 2]


class TestL2_07_Performance:

    def test_TC_L102_L207_501_single_render_p95_under_100ms(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """单次 render_template · warm P95 ≤ 100ms。"""
        slots: dict[str, Any] = {
            "scope_statement": "重构项目",
            "scope_items": [
                {"name": f"mod-{i}", "description": "x", "owner": "o", "duration_days": i + 1}
                for i in range(10)
            ],
            "out_of_scope": [],
        }
        # warm
        sut.render_template(
            request_id="r0", project_id=mock_project_id, kind="pmp.scope",
            slots=slots, caller_l2="L2-04",
        )
        # measure
        samples: list[float] = []
        for i in range(20):
            t = time.perf_counter()
            sut.render_template(
                request_id=f"r{i}", project_id=mock_project_id, kind="pmp.scope",
                slots=slots, caller_l2="L2-04",
            )
            samples.append((time.perf_counter() - t) * 1000)
        p50 = _p50(samples)
        p95 = _p95(samples)
        assert p95 < 100, f"P95 {p95:.1f}ms > 100ms (samples={samples})"
        assert p50 < 20, f"P50 {p50:.1f}ms > 20ms"

    def test_TC_L102_L207_502_slot_validation_p95_under_5ms(
        self, sut: TemplateEngine,
    ) -> None:
        """validate_slots · warm P95 ≤ 5ms。"""
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        # warm
        sut.validate_slots("kickoff.goal", slots)
        samples: list[float] = []
        for _ in range(30):
            t = time.perf_counter()
            sut.validate_slots("kickoff.goal", slots)
            samples.append((time.perf_counter() - t) * 1000)
        p95 = _p95(samples)
        assert p95 < 5, f"validate P95 {p95:.2f}ms > 5ms"

    def test_TC_L102_L207_503_jinja_render_p95_under_50ms(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """Jinja2 sandbox 渲染（间接测：render_template 去除 jsonschema/hash 的下界比例）。"""
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        # warm
        sut.render_template(
            request_id="r0", project_id=mock_project_id, kind="kickoff.goal",
            slots=slots, caller_l2="L2-02",
        )
        samples: list[float] = []
        for i in range(20):
            t = time.perf_counter()
            sut.render_template(
                request_id=f"r{i}", project_id=mock_project_id, kind="kickoff.goal",
                slots=slots, caller_l2="L2-02",
            )
            samples.append((time.perf_counter() - t) * 1000)
        p95 = _p95(samples)
        assert p95 < 50, f"simple render P95 {p95:.1f}ms > 50ms"

    def test_TC_L102_L207_504_output_hash_200kb_p95_under_20ms(self) -> None:
        """compute_output_hash 200KB body · warm P95 ≤ 20ms。"""
        # 构造 200KB body 含 frontmatter
        body = "---\ntemplate_id: t.v1.0\n---\n" + ("X" * (200 * 1024))
        # warm
        compute_output_hash(body)
        samples: list[float] = []
        for _ in range(20):
            t = time.perf_counter()
            compute_output_hash(body)
            samples.append((time.perf_counter() - t) * 1000)
        p95 = _p95(samples)
        assert p95 < 20, f"hash 200KB P95 {p95:.1f}ms > 20ms"

    def test_TC_L102_L207_506_concurrent_50_render_thread_safe(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """并发 50 线程 render · 全部成功 · 无崩溃 · 返回 RenderedOutput。"""
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        results: list[Any] = []
        errors: list[BaseException] = []
        lock = threading.Lock()

        def _do(i: int) -> None:
            try:
                out = sut.render_template(
                    request_id=f"concurrent-{i}", project_id=mock_project_id,
                    kind="kickoff.goal", slots=slots, caller_l2="L2-02",
                )
                with lock:
                    results.append(out)
            except BaseException as exc:  # noqa: BLE001
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_do, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert not errors, f"concurrent render raised: {errors[0]}"
        assert len(results) == 50
        # 所有结果应该幂等 · 同 slots 产同 body_sha256
        sha_set = {r.body_sha256 for r in results}
        assert len(sha_set) == 1, f"expected idempotent hashes, got {len(sha_set)} distinct"

    def test_TC_L102_L207_505_restart_load_warm_under_1s(
        self, template_dir_real,
    ) -> None:
        """启动加载二次冷启（新实例 · 已 warm module import）· hard ≤ 1000ms。"""
        from app.l1_02.template_engine.registry import TemplateLoader

        # 预热 import
        loader0 = TemplateLoader(template_dir=str(template_dir_real))
        loader0.load_all()

        # 创建新 loader 实例 · 测冷启 · 模板文件已 OS cache
        samples: list[float] = []
        for _ in range(3):
            loader = TemplateLoader(template_dir=str(template_dir_real))
            t = time.perf_counter()
            loader.load_all()
            samples.append((time.perf_counter() - t) * 1000)
        max_ms = max(samples)
        # hard ≤ 1000ms（实际应 400-600ms · 留宽）
        assert max_ms < 1000, f"restart load max {max_ms:.0f}ms > 1000ms (samples={samples})"
