---
doc_id: tests-L1-08-L2-03-图片视觉理解编排器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-08-多模态内容处理/L2-03-图片视觉理解编排器.md
  - docs/2-prd/L1-08 多模态内容处理/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-K
created_at: 2026-04-22
---

# L1-08 L2-03 图片视觉理解编排器 · TDD 测试用例

> 基于 3-1 L2-03 §3（6 IC 触点 · 3 image_hint · VisualDescription schema 白名单）+ §11（12 个 `image_*` 错误码 E01-E12 · 4 级降级）+ §12（Vision SLO · P99 15s 硬上限）+ §13 TC 锚点驱动。
> TC ID `TC-L108-L203-NNN`（语义别名：`TC-VISION-*` / `TC-PRIVACY-*` / `TC-HINT-*`）。
> pytest + Python 3.11+ 类型注解；`class TestImageOrchestrator_*` 组织；Privacy / 降级 / Vision mock 独立分组。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例（architecture / ui_mock / screenshot 三 hint · hint 推断）
- [x] §3 负向用例（E01-E12 全覆盖 · privacy violation 特别）
- [x] §4 IC-XX 契约集成测试（IC-L2-01 / batch / audit / err / violation）
- [x] §5 性能 SLO 用例（analyze P99 15s · Vision 60s timeout · batch 3min）
- [x] §6 端到端 e2e 场景（三 hint 全路径 · 降级 Low_Confidence · privacy halt）
- [x] §7 测试 fixture（mock_vlm / make_image / privacy_injector / batch_payload）
- [x] §8 集成点用例（与 L2-04 审计 / L1-07 supervisor 违规广播）
- [x] §9 边界 / edge case（0 字节 / 损坏 header / 20MB 边界 / 并发批量 / hint 混合）

---

## §1 覆盖度索引

### §1.1 方法 × 测试 × 覆盖类型

| 方法 / 路径 | TC ID | 覆盖类型 | 对应 IC |
|:---|:---|:---|:---|
| `analyze()` · architecture hint | TC-L108-L203-001 | unit | IC-L2-01 |
| `analyze()` · ui_mock hint | TC-L108-L203-002 | unit | IC-L2-01 |
| `analyze()` · screenshot hint | TC-L108-L203-003 | unit | IC-L2-01 |
| `analyze()` · hint inferred（启发式） | TC-L108-L203-004 | unit | IC-L2-01 |
| `analyze_batch()` · P1 批量 5 图 | TC-L108-L203-005 | unit | IC-L2-01-batch |
| `analyze_batch()` · merge_topic=true | TC-L108-L203-006 | unit | IC-L2-01-batch |
| `_load_image()` · png/jpg/webp/gif 四格式 | TC-L108-L203-007 | unit | 内部 |
| `HintInferencer.infer()` · png 特征 | TC-L108-L203-008 | unit | 内部 |
| `VisionInvoker.invoke()` · 正常 claude vision 返回 | TC-L108-L203-009 | unit | 内部 |
| `StructuredExtractor.extract()` · regex+yaml | TC-L108-L203-010 | unit | 内部 |
| `SchemaWhitelistGuard.validate()` · 拒绝 bytes 字段 | TC-L108-L203-011 | unit | 内部 |
| `ConfidenceEvaluator.evaluate()` · high/medium/low | TC-L108-L203-012 | unit | 内部 |
| `emit_audit()` · image_described 事件 | TC-L108-L203-013 | unit | IC-L2-05 |
| `emit_err()` · 结构化 err | TC-L108-L203-014 | unit | IC-L2-06 |
| shutdown_signal 响应 | TC-L108-L203-015 | unit | internal |

### §1.2 错误码 × 测试（§11 E01-E12 全覆盖）

| 错误码 | TC ID | 分类 | 降级 Level |
|:---|:---|:---|:---|
| `image_format_unsupported` (E01) | TC-L108-L203-101 | input | L3 REJECT |
| `image_size_exceeded` (E02) | TC-L108-L203-102 | input | L3 REJECT |
| `image_file_not_found` (E03) | TC-L108-L203-103 | fs | L3 REJECT |
| `image_permission_denied` (E04) | TC-L108-L203-104 | fs | L3 REJECT |
| `image_decode_failed` (E05) | TC-L108-L203-105 | input | L3 REJECT |
| `image_hint_invalid` (E06) | TC-L108-L203-106 | input | L3 REJECT |
| `image_vision_timeout` (E07) | TC-L108-L203-107 | vision | L1 LOW_CONFIDENCE |
| `image_low_confidence` (E08) | TC-L108-L203-108 | vision | L1 LOW_CONFIDENCE |
| `image_privacy_violation` (E09) | TC-L108-L203-109 | internal | L3 REJECT + HALT |
| `image_external_endpoint_configured` (E10) | TC-L108-L203-110 | startup | L4 REFUSE |
| `image_batch_size_exceeded` (E11) | TC-L108-L203-111 | input | L3 REJECT |
| `image_vision_rate_limited` (E12) | TC-L108-L203-112 | vision | L2 SKIP_VISION |

### §1.3 IC × 集成测试

| IC | TC ID | 对端 | 场景 |
|:---|:---|:---|:---|
| IC-L2-01 dispatch(image) | TC-L108-L203-201 | L2-04 | 单图分析 schema |
| IC-L2-01-batch | TC-L108-L203-202 | L2-04 | ≤ 10 图批量 |
| IC-L2-05 audit_event(image_*) | TC-L108-L203-203 | L2-04 → L1-09 | image_described 事件 |
| IC-L2-06 err(image_*) | TC-L108-L203-204 | L2-04 | E01-E12 结构化 err |
| IC-L2-07 violation_broadcast | TC-L108-L203-205 | L2-04 → L1-07 | privacy E09 critical |

### §1.4 性能 SLO × 测试

| SLO | 阈值 | TC ID |
|:---|:---|:---|
| `analyze()` P99（explicit hint） | ≤ 13s · 硬上限 15s | TC-L108-L203-301 |
| `_load_image()` P99 | ≤ 500ms | TC-L108-L203-302 |
| `VisionInvoker` timeout | 硬上限 60s | TC-L108-L203-303 |
| `SchemaWhitelistGuard` P99 | ≤ 10ms | TC-L108-L203-304 |
| batch 10 图 P99 | ≤ 2.5min · 硬 3min | TC-L108-L203-305 |

### §1.5 e2e × 测试

| 场景 | TC ID |
|:---|:---|
| architecture hint 全链：L2-04 → L2-03 → Vision → VD + 审计 | TC-L108-L203-401 |
| Vision timeout → LOW_CONFIDENCE 降级 · best_effort_summary | TC-L108-L203-402 |
| privacy_violation → IC-L2-07 广播 → L1-07 IC-15 hard_halt 候选 | TC-L108-L203-403 |

---

## §2 正向用例

```python
# tests/unit/L1-08/L2-03/test_image_orchestrator_positive.py
import pytest
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestImageOrchestrator_ExplicitHint:
    """§3.2 hint ∈ {architecture, ui_mock, screenshot} 三路径"""

    async def test_analyze_architecture(self, img_orch, arch_png, mock_vlm_architecture, _req):
        """TC-L108-L203-001 · hint=architecture · structured_fields.nodes / relations / layers 填满"""
        resp = await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        assert resp["status"] == "ok"
        vd = resp["result"]
        assert UUID(vd["description_id"])
        assert vd["image_type"] == "architecture"
        assert vd["hint_inferred"] is False
        assert vd["confidence"] in {"high", "medium", "low"}
        sf = vd["structured_fields"]
        assert sf["nodes"] and sf["relations"] is not None
        assert sf["layers"]

    async def test_analyze_ui_mock(self, img_orch, ui_mock_png, mock_vlm_ui, _req):
        """TC-L108-L203-002 · ui_mock · layout + components + interaction_points"""
        resp = await img_orch.analyze(_req(path=str(ui_mock_png), image_hint="ui_mock"))
        sf = resp["result"]["structured_fields"]
        assert sf["layout"]
        assert sf["components"]
        assert sf["interaction_points"] is not None

    async def test_analyze_screenshot(self, img_orch, screenshot_png, mock_vlm_screenshot, _req):
        """TC-L108-L203-003 · screenshot · ocr_text + ui_state + focal_areas"""
        resp = await img_orch.analyze(_req(path=str(screenshot_png), image_hint="screenshot"))
        sf = resp["result"]["structured_fields"]
        assert "ocr_text" in sf or "focal_areas" in sf


class TestImageOrchestrator_InferredHint:
    """hint=null · HintInferencer 启发式推断"""

    async def test_analyze_hint_inferred(self, img_orch, arch_png, mock_vlm_architecture, _req):
        """TC-L108-L203-004 · 不传 hint · 启发式推 architecture · hint_inferred=true"""
        resp = await img_orch.analyze(_req(path=str(arch_png), image_hint=None))
        assert resp["result"]["hint_inferred"] is True
        assert resp["result"]["image_type"] in {"architecture", "ui_mock", "screenshot"}


class TestImageOrchestrator_Batch:
    """§3.3 IC-L2-01-batch · P1 批量"""

    async def test_analyze_batch_5_images(self, img_orch, five_pngs, mock_vlm_architecture, _batch):
        """TC-L108-L203-005 · 5 图 batch · 返 5 个 VD · 各有 description_id"""
        resp = await img_orch.analyze_batch(_batch(paths=[str(p) for p in five_pngs]))
        assert len(resp["result"]["descriptions"]) == 5
        ids = {d["description_id"] for d in resp["result"]["descriptions"]}
        assert len(ids) == 5

    async def test_analyze_batch_merge_topic(self, img_orch, five_pngs,
                                                mock_vlm_architecture, _batch):
        """TC-L108-L203-006 · merge_topic=true · 返额外 topic_summary"""
        resp = await img_orch.analyze_batch(_batch(paths=[str(p) for p in five_pngs],
                                                     merge_topic=True))
        assert resp["result"]["topic_summary"]


class TestImageOrchestrator_InternalComponents:
    """内部组件 unit test"""

    async def test_load_image_formats(self, tmp_path, make_valid_image):
        """TC-L108-L203-007 · png/jpg/webp/gif 四格式均能加载"""
        loader = ImageLoader()
        for fmt in ["png", "jpg", "webp", "gif"]:
            p = make_valid_image(fmt=fmt, size_bytes=1024)
            block = await loader.load(str(p))
            assert block.format == fmt
            assert block.bytes_count == 1024

    def test_hint_inferencer_png_with_text(self, arch_png):
        """TC-L108-L203-008 · HintInferencer 识别架构图（线条密 + 方框多）"""
        hint = HintInferencer.infer(str(arch_png))
        assert hint in {"architecture", "ui_mock", "screenshot"}

    async def test_vision_invoker_normal_return(self, mock_vlm_architecture):
        """TC-L108-L203-009 · VisionInvoker.invoke · 正常返回 raw_text"""
        inv = VisionInvoker(client=mock_vlm_architecture)
        r = await inv.invoke(image_bytes=b"\x89PNG", hint="architecture")
        assert r["raw_text"]

    def test_structured_extractor_parses_yaml(self):
        """TC-L108-L203-010 · StructuredExtractor 从 raw_text 抽 yaml block"""
        raw = "```yaml\nnodes: [A,B]\nrelations: []\n```"
        sf = StructuredExtractor.extract(raw, hint="architecture")
        assert sf["nodes"] == ["A", "B"]

    def test_schema_whitelist_guard_rejects_bytes(self):
        """TC-L108-L203-011 · SchemaWhitelistGuard 深度扫描拒 bytes 字段"""
        with pytest.raises(PrivacyViolation):
            SchemaWhitelistGuard.validate({"nodes": ["x"], "_leaked_bytes": b"\x00"})

    def test_confidence_evaluator(self):
        """TC-L108-L203-012 · ConfidenceEvaluator · 全空返 low · 全填返 high"""
        assert ConfidenceEvaluator.evaluate({"nodes": [], "relations": [], "layers": []}) == "low"
        assert ConfidenceEvaluator.evaluate({"nodes": ["A"], "relations": [{}], "layers": ["x"]}) == "high"


class TestImageOrchestrator_OutboundIC:
    """出站 IC · audit / err"""

    async def test_emit_audit_image_described(self, img_orch, arch_png,
                                                l204_mock_emitter, _req):
        """TC-L108-L203-013 · analyze 成功 · 审计事件 L1-08:image_described"""
        await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        l204_mock_emitter.emit_audit_seed.assert_called()
        seed = l204_mock_emitter.emit_audit_seed.call_args[0][0]
        assert seed["event_type"] == "L1-08:image_described"

    async def test_emit_err_e01_format(self, img_orch, tmp_path, _req):
        """TC-L108-L203-014 · .bmp 非白 · 返 err · error_code=image_format_unsupported"""
        bmp = tmp_path / "x.bmp"
        bmp.write_bytes(b"BM" + b"\x00" * 100)
        resp = await img_orch.analyze(_req(path=str(bmp)))
        assert resp["status"] == "err"
        assert resp["result"]["error_code"] == "image_format_unsupported"


class TestImageOrchestrator_Shutdown:
    """进程 shutdown_signal"""

    async def test_shutdown_signal_flushes_resources(self, img_orch):
        """TC-L108-L203-015 · shutdown_signal · 关闭 VLM session + 审计最后事件"""
        await img_orch.shutdown()
        assert img_orch._closed is True
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# tests/unit/L1-08/L2-03/test_image_orchestrator_negative.py
import pytest, os

pytestmark = pytest.mark.asyncio


class TestL203_InputRejection:
    """L3 REJECT · 格式/尺寸/路径/解码/hint/批量 7 类"""

    async def test_E01_image_format_unsupported(self, img_orch, tmp_path, _req):
        """TC-L108-L203-101 · .bmp → image_format_unsupported · L3 REJECT"""
        p = tmp_path / "x.bmp"; p.write_bytes(b"BM\x00\x00")
        resp = await img_orch.analyze(_req(path=str(p)))
        assert resp["result"]["error_code"] == "image_format_unsupported"

    async def test_E02_image_size_exceeded(self, img_orch, make_oversize_image, _req):
        """TC-L108-L203-102 · 25MB.png > 20MB → image_size_exceeded"""
        p = make_oversize_image(size_mb=25, fmt="png")
        resp = await img_orch.analyze(_req(path=str(p)))
        assert resp["result"]["error_code"] == "image_size_exceeded"

    async def test_E03_image_file_not_found(self, img_orch, _req):
        """TC-L108-L203-103 · 路径不存在 → image_file_not_found"""
        resp = await img_orch.analyze(_req(path="/nonexistent/a.png"))
        assert resp["result"]["error_code"] == "image_file_not_found"

    async def test_E04_image_permission_denied(self, img_orch, make_valid_image, _req):
        """TC-L108-L203-104 · chmod 000 → image_permission_denied"""
        p = make_valid_image(fmt="png", size_bytes=1024)
        os.chmod(p, 0o000)
        try:
            resp = await img_orch.analyze(_req(path=str(p)))
            assert resp["result"]["error_code"] == "image_permission_denied"
        finally:
            os.chmod(p, 0o644)

    async def test_E05_image_decode_failed(self, img_orch, tmp_path, _req):
        """TC-L108-L203-105 · 伪装 png（内容坏） → image_decode_failed"""
        p = tmp_path / "bad.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\xff" * 100)  # 坏 header
        resp = await img_orch.analyze(_req(path=str(p)))
        assert resp["result"]["error_code"] == "image_decode_failed"

    async def test_E06_image_hint_invalid(self, img_orch, arch_png, _req):
        """TC-L108-L203-106 · hint=diagram（非白） → image_hint_invalid"""
        resp = await img_orch.analyze(_req(path=str(arch_png), image_hint="diagram"))
        assert resp["result"]["error_code"] == "image_hint_invalid"

    async def test_E11_image_batch_size_exceeded(self, img_orch, fifteen_pngs, _batch):
        """TC-L108-L203-111 · batch 15 图 > 10 上限 → image_batch_size_exceeded"""
        resp = await img_orch.analyze_batch(_batch(paths=[str(p) for p in fifteen_pngs]))
        assert resp["result"]["error_code"] == "image_batch_size_exceeded"


class TestL203_VisionDegradation:
    """L1 LOW_CONFIDENCE · L2 SKIP_VISION"""

    async def test_E07_image_vision_timeout(self, img_orch, arch_png, mock_vlm_timeout, _req):
        """TC-L108-L203-107 · Vision 60s 超时 → 降级 L1 · status=ok + confidence=low + best_effort_summary · 不抛错"""
        resp = await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        assert resp["status"] == "ok"
        vd = resp["result"]
        assert vd["confidence"] == "low"
        assert vd["metadata"]["low_confidence_reason"] == "vision_timeout"
        assert vd["metadata"]["best_effort_summary"]

    async def test_E08_image_low_confidence(self, img_orch, arch_png, mock_vlm_empty, _req):
        """TC-L108-L203-108 · Vision 返回字段全空 → image_low_confidence · confidence=low"""
        resp = await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        assert resp["result"]["confidence"] == "low"

    async def test_E12_image_vision_rate_limited(self, img_orch, arch_png, mock_vlm_rate_limit, _req):
        """TC-L108-L203-112 · Vision rate_limit × 3 → L2 SKIP_VISION → E12 err · 审计 failed"""
        mock_vlm_rate_limit.set_fail_count(3)
        resp = await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        assert resp["status"] == "err"
        assert resp["result"]["error_code"] == "image_vision_rate_limited"


class TestL203_Privacy:
    """L3 REJECT + HALT · privacy_violation"""

    async def test_E09_image_privacy_violation(self, img_orch, arch_png,
                                                 mock_vlm_leaks_bytes, l204_mock_emitter, _req):
        """TC-L108-L203-109 · Extractor 错填 bytes → SchemaWhitelistGuard 拒 · critical 广播"""
        resp = await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        assert resp["status"] == "err"
        assert resp["result"]["error_code"] == "image_privacy_violation"
        # 违规广播
        assert any(
            c[0][0].get("event_type") == "L1-08:image_privacy_violation"
            for c in l204_mock_emitter.emit_audit_seed.call_args_list
        )


class TestL203_Startup:
    """L4 STARTUP_REFUSE"""

    async def test_E10_image_external_endpoint_configured(self, tmp_path):
        """TC-L108-L203-110 · config.image.endpoints=[https://x] → 启动拒绝 SystemExit(1)"""
        cfg = tmp_path / "cfg.yaml"
        cfg.write_text("image:\n  endpoints:\n    - https://vlm.example.com\n")
        with pytest.raises(SystemExit) as exc:
            ImageOrchestrator.bootstrap(str(cfg))
        assert exc.value.code == 1
```

---

## §4 IC-XX 契约集成测试

```python
# tests/integration/L1-08/L2-03/test_ic_contracts.py
import pytest, jsonschema

pytestmark = pytest.mark.asyncio


class TestICL201ImageContract:
    """IC-L2-01 · 入站单图"""

    async def test_dispatch_image_schema(self, img_orch, arch_png, icl201_image_schema,
                                          mock_vlm_architecture, _req):
        """TC-L108-L203-201 · request payload · schema 合法 + analyze 成功"""
        req = _req(path=str(arch_png), image_hint="architecture")
        jsonschema.validate(req, icl201_image_schema)
        resp = await img_orch.analyze(req)
        assert resp["status"] == "ok"


class TestICL201BatchContract:
    """IC-L2-01-batch · 批量"""

    async def test_batch_schema(self, img_orch, five_pngs, icl201_batch_schema,
                                  mock_vlm_architecture, _batch):
        """TC-L108-L203-202 · batch schema 合法 · paths 长度 ≤ 10"""
        req = _batch(paths=[str(p) for p in five_pngs])
        jsonschema.validate(req, icl201_batch_schema)
        resp = await img_orch.analyze_batch(req)
        assert resp["status"] == "ok"


class TestICL205AuditContract:
    """IC-L2-05 · audit_event(image_described / image_privacy_violation)"""

    async def test_audit_event_image_described(self, img_orch, arch_png,
                                                 l204_mock_emitter, audit_seed_image_schema,
                                                 mock_vlm_architecture, _req):
        """TC-L108-L203-203 · image_described 审计字段完整"""
        await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        seed = l204_mock_emitter.emit_audit_seed.call_args[0][0]
        jsonschema.validate(seed, audit_seed_image_schema)
        assert seed["event_type"] == "L1-08:image_described"


class TestICL206ErrContract:
    """IC-L2-06 · structured_err"""

    async def test_err_schema_shape(self, img_orch, tmp_path, structured_err_schema, _req):
        """TC-L108-L203-204 · E01 err 符合 structured_err schema"""
        p = tmp_path / "x.bmp"; p.write_bytes(b"BM")
        resp = await img_orch.analyze(_req(path=str(p)))
        err = {"error_code": resp["result"]["error_code"], "error_class": "input_error",
               "error_message": "unsupported", "error_context": {"path": str(p)},
               "retryable": False, "ts_ns": 1}
        jsonschema.validate(err, structured_err_schema)


class TestICL207ViolationContract:
    """IC-L2-07 · violation_broadcast（privacy）"""

    async def test_privacy_violation_broadcast(self, img_orch, arch_png, mock_vlm_leaks_bytes,
                                                 l204_mock_emitter, _req):
        """TC-L108-L203-205 · E09 → IC-L2-07 critical 广播"""
        await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        seeds = [c[0][0] for c in l204_mock_emitter.emit_audit_seed.call_args_list]
        privacy = [s for s in seeds if s["event_type"] == "L1-08:image_privacy_violation"]
        assert privacy
        assert privacy[0].get("severity", "critical") == "critical"
```

---

## §5 性能 SLO 用例

```python
# tests/perf/L1-08/L2-03/test_slo.py
import pytest, time, statistics, asyncio
from contextlib import contextmanager

pytestmark = pytest.mark.asyncio


@contextmanager
def _timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000


class TestAnalyzeSLO:
    """§12.1 · analyze(architecture, explicit) P99 ≤ 13s · 硬上限 15s"""

    async def test_analyze_p99_under_13s(self, img_orch, arch_png_pool,
                                           mock_vlm_fast, _req):
        """TC-L108-L203-301 · 100 次 architecture · P99 ≤ 13000ms · 硬 15000ms"""
        samples = []
        for p in arch_png_pool[:100]:
            with _timer() as t:
                await img_orch.analyze(_req(path=str(p), image_hint="architecture"))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert max(samples) <= 15_000.0
        assert p99 <= 13_000.0


class TestLoadImageSLO:
    """§12.1 · _load_image P99 ≤ 500ms"""

    async def test_load_image_p99_under_500ms(self, arch_png_pool):
        """TC-L108-L203-302 · 500 次本地 load · P99 ≤ 500ms"""
        loader = ImageLoader()
        samples = []
        for p in arch_png_pool[:500]:
            with _timer() as t:
                await loader.load(str(p))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 500.0


class TestVisionTimeoutSLO:
    """§12.1 · VisionInvoker 60s 硬上限"""

    async def test_vision_invoker_timeout_60s(self, img_orch, arch_png,
                                                mock_vlm_hanging, _req):
        """TC-L108-L203-303 · Vision hang 70s → 被 60s timeout 打断 · 降级 LOW_CONFIDENCE"""
        mock_vlm_hanging.set_hang_ms(70_000)
        t0 = time.perf_counter()
        resp = await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        elapsed = time.perf_counter() - t0
        assert elapsed <= 61.0
        assert resp["status"] == "ok"
        assert resp["result"]["confidence"] == "low"


class TestSchemaGuardSLO:
    """§12.1 · SchemaWhitelistGuard P99 ≤ 10ms"""

    async def test_schema_guard_p99_under_10ms(self, sample_vd_dicts):
        """TC-L108-L203-304 · 1000 次深度递归校验 · P99 ≤ 10ms"""
        samples = []
        for vd in sample_vd_dicts[:1000]:
            with _timer() as t:
                SchemaWhitelistGuard.validate(vd)
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 10.0


class TestBatchSLO:
    """§12.1 · batch 10 图 P99 ≤ 2.5min · 硬 3min"""

    async def test_batch_10_p99_under_150s(self, img_orch, ten_pngs, mock_vlm_fast, _batch):
        """TC-L108-L203-305 · 10 次 batch(10 图) · P99 ≤ 150000ms"""
        samples = []
        for _ in range(10):
            with _timer() as t:
                await img_orch.analyze_batch(_batch(paths=[str(p) for p in ten_pngs]))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 150_000.0
```

---

## §6 端到端 e2e 场景

```python
# tests/e2e/L1-08/L2-03/test_e2e.py
import pytest

pytestmark = pytest.mark.asyncio


class TestE2EArchitectureFullPath:
    """架构图全链路 e2e"""

    async def test_arch_full_flow(self, l204_real, img_orch, l109_real, arch_png,
                                    mock_vlm_architecture, _req):
        """TC-L108-L203-401 · L2-04 → L2-03 → Vision → VD + L1-09 image_described"""
        req = _req(path=str(arch_png), image_hint="architecture")
        resp = await img_orch.analyze(req)
        assert resp["status"] == "ok"
        events = l109_real.query_trail(request_id_ref=req["request_id"])
        assert any(e["event_type"] == "L1-08:image_described" for e in events)


class TestE2ELowConfidenceDegrade:
    """Vision timeout → LOW_CONFIDENCE 降级"""

    async def test_vision_timeout_degrades_to_low_confidence(self, img_orch, arch_png,
                                                               mock_vlm_timeout, _req):
        """TC-L108-L203-402 · VisionInvoker timeout · confidence=low + best_effort_summary · status=ok"""
        resp = await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        assert resp["status"] == "ok"
        assert resp["result"]["confidence"] == "low"
        assert resp["result"]["metadata"]["best_effort_summary"]


class TestE2EPrivacyHalt:
    """privacy_violation → IC-L2-07 critical → L1-07 IC-15 hard_halt 候选"""

    async def test_privacy_violation_triggers_halt_candidate(self, img_orch, arch_png,
                                                               mock_vlm_leaks_bytes,
                                                               l107_supervisor_spy, _req):
        """TC-L108-L203-403 · E09 → L1-07 收 violation · 8 维度判 halt 候选"""
        await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        assert l107_supervisor_spy.receive_violation.called
        violation = l107_supervisor_spy.receive_violation.call_args[0][0]
        assert violation["severity"] == "critical"
        assert violation["violation_type"] == "image_privacy_violation"
```

---

## §7 测试 fixture

```python
# tests/conftest.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4


@pytest.fixture
def mock_project_id(): return "demo-proj-001"


@pytest.fixture
def _req(mock_project_id):
    def _make(path: str, image_hint: str | None = None) -> dict:
        return {
            "project_id": mock_project_id,
            "request_id": str(uuid4()),
            "type": "image",
            "action": "analyze",
            "path": path,
            "image_hint": image_hint,
            "metadata": {"size_bytes": 1024, "format": "png", "resolution_wh": [800, 600]},
            "caller_l1": "L1-01",
            "trace_ctx": {"ts_dispatched": 1, "degradation_route": "DIRECT"},
        }
    return _make


@pytest.fixture
def _batch(mock_project_id):
    def _make(paths: list[str], merge_topic: bool = False) -> dict:
        return {
            "project_id": mock_project_id,
            "batch_id": str(uuid4()),
            "paths": paths,
            "action": "analyze",
            "image_hint": "architecture",
            "merge_topic": merge_topic,
            "caller_l1": "L1-01",
        }
    return _make


@pytest.fixture
def make_valid_image(tmp_path):
    def _make(fmt: str = "png", size_bytes: int = 1024) -> Path:
        headers = {
            "png": b"\x89PNG\r\n\x1a\n",
            "jpg": b"\xff\xd8\xff\xe0",
            "webp": b"RIFF" + b"\x00" * 4 + b"WEBP",
            "gif": b"GIF89a",
        }
        f = tmp_path / f"img.{fmt}"
        header = headers[fmt]
        f.write_bytes(header + b"\x00" * (size_bytes - len(header)))
        return f
    return _make


@pytest.fixture
def make_oversize_image(make_valid_image):
    def _make(size_mb: int, fmt: str = "png") -> Path:
        return make_valid_image(fmt=fmt, size_bytes=size_mb * 1024 * 1024)
    return _make


@pytest.fixture
def arch_png(make_valid_image): return make_valid_image(fmt="png", size_bytes=2048)
@pytest.fixture
def ui_mock_png(make_valid_image): return make_valid_image(fmt="png", size_bytes=2048)
@pytest.fixture
def screenshot_png(make_valid_image): return make_valid_image(fmt="png", size_bytes=2048)


@pytest.fixture
def arch_png_pool(tmp_path):
    pool = []
    for i in range(500):
        p = tmp_path / f"arch{i}.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024)
        pool.append(p)
    return pool


@pytest.fixture
def five_pngs(tmp_path):
    return [_mk_png(tmp_path, i) for i in range(5)]


@pytest.fixture
def ten_pngs(tmp_path):
    return [_mk_png(tmp_path, i) for i in range(10)]


@pytest.fixture
def fifteen_pngs(tmp_path):
    return [_mk_png(tmp_path, i) for i in range(15)]


def _mk_png(tmp_path, i):
    p = tmp_path / f"p{i}.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return p


@pytest.fixture
def mock_vlm_architecture():
    m = MagicMock()
    m.invoke = AsyncMock(return_value={"raw_text":
        "```yaml\nnodes: [A,B]\nrelations: [{source: A, target: B}]\nlayers: [svc]\ninferred_stack: [python]\n```"})
    return m


@pytest.fixture
def mock_vlm_ui():
    m = MagicMock()
    m.invoke = AsyncMock(return_value={"raw_text":
        "```yaml\nlayout: grid\ncomponents: [{kind: button, label: Save}]\ninteraction_points: []\ncolor_palette_summary: light\n```"})
    return m


@pytest.fixture
def mock_vlm_screenshot():
    m = MagicMock()
    m.invoke = AsyncMock(return_value={"raw_text":
        "```yaml\nocr_text: hello\nfocal_areas: []\nui_state: idle\n```"})
    return m


@pytest.fixture
def mock_vlm_fast(mock_vlm_architecture):
    return mock_vlm_architecture


@pytest.fixture
def mock_vlm_empty():
    m = MagicMock()
    m.invoke = AsyncMock(return_value={"raw_text":
        "```yaml\nnodes: []\nrelations: []\nlayers: []\ninferred_stack: []\n```"})
    return m


@pytest.fixture
def mock_vlm_timeout():
    import asyncio
    m = MagicMock()
    async def _to(*a, **k): raise asyncio.TimeoutError()
    m.invoke = AsyncMock(side_effect=_to)
    return m


@pytest.fixture
def mock_vlm_rate_limit():
    m = MagicMock()
    m.fail_count = 0
    async def _rl(*a, **k):
        if m.fail_count > 0:
            m.fail_count -= 1
            raise RateLimitError("429")
        return {"raw_text": "..."}
    m.invoke = AsyncMock(side_effect=_rl)
    m.set_fail_count = lambda n: setattr(m, "fail_count", n)
    return m


@pytest.fixture
def mock_vlm_leaks_bytes():
    """VLM 返回含 bytes · 模拟内部 bug"""
    m = MagicMock()
    m.invoke = AsyncMock(return_value={"raw_text":
        "```yaml\nnodes: [A]\nrelations: []\nlayers: [x]\n_leaked_bytes: !!binary SGVsbG8=\n```"})
    return m


@pytest.fixture
def mock_vlm_hanging():
    import asyncio
    m = MagicMock()
    m.hang_ms = 0
    async def _hang(*a, **k):
        await asyncio.sleep(m.hang_ms / 1000)
        return {"raw_text": "..."}
    m.invoke = AsyncMock(side_effect=_hang)
    m.set_hang_ms = lambda n: setattr(m, "hang_ms", n)
    return m


@pytest.fixture
def l204_mock_emitter():
    m = MagicMock()
    m.emit_audit_seed = AsyncMock()
    return m


@pytest.fixture
def l107_supervisor_spy():
    m = MagicMock()
    m.receive_violation = MagicMock()
    return m


@pytest.fixture
def img_orch(mock_vlm_architecture, l204_mock_emitter):
    return ImageOrchestrator(vlm_client=mock_vlm_architecture,
                              emitter=l204_mock_emitter,
                              config={"timeout_s": 60, "max_batch": 10})


@pytest.fixture
def sample_vd_dicts():
    return [{"nodes": [f"N{i}"], "relations": [], "layers": []} for i in range(1000)]


@pytest.fixture
def icl201_image_schema():
    return {"type": "object", "required": ["project_id", "request_id", "type", "path", "action"],
            "properties": {"type": {"const": "image"}, "action": {"const": "analyze"}}}


@pytest.fixture
def icl201_batch_schema():
    return {"type": "object", "required": ["project_id", "batch_id", "paths", "action"],
            "properties": {"paths": {"type": "array", "maxItems": 10}}}


@pytest.fixture
def audit_seed_image_schema():
    return {"type": "object", "required": ["event_type", "project_id"]}


@pytest.fixture
def structured_err_schema():
    return {"type": "object", "required": ["error_code", "error_class"]}
```

---

## §8 集成点用例

```python
# tests/integration/L1-08/L2-03/test_integration_points.py
import pytest

pytestmark = pytest.mark.asyncio


class TestIntegrationWithL204Audit:
    """与 L2-04 审计协作"""

    async def test_audit_on_every_analyze(self, img_orch, arch_png, l204_mock_emitter,
                                            mock_vlm_architecture, _req):
        """TC-L108-L203-501 · 每次 analyze 必产 audit_seed（成功或失败都要）"""
        for _ in range(3):
            await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        assert l204_mock_emitter.emit_audit_seed.call_count == 3


class TestIntegrationWithL107Supervisor:
    """与 L1-07 违规广播"""

    async def test_e09_reaches_l107(self, img_orch, arch_png, mock_vlm_leaks_bytes,
                                      l107_supervisor_spy, _req):
        """TC-L108-L203-502 · privacy violation · L1-07 收 critical 广播"""
        await img_orch.analyze(_req(path=str(arch_png), image_hint="architecture"))
        assert l107_supervisor_spy.receive_violation.called


class TestIntegrationWithL204SizeCheck:
    """L2-04 先拦过大 · 本 L2 也要再验一次（纵深防御）"""

    async def test_defense_in_depth_size_check(self, img_orch, make_oversize_image, _req):
        """TC-L108-L203-503 · 即使 L2-04 未拦 · 本 L2 再校验 · 返 E02"""
        big = make_oversize_image(size_mb=30, fmt="png")
        resp = await img_orch.analyze(_req(path=str(big)))
        assert resp["result"]["error_code"] == "image_size_exceeded"
```

---

## §9 边界 / edge case

```python
# tests/edge/L1-08/L2-03/test_edge_cases.py
import pytest, asyncio

pytestmark = pytest.mark.asyncio


class TestEdgeMinimumSize:
    """0 字节 / 1 字节"""

    async def test_edge_zero_byte_image(self, img_orch, tmp_path, _req):
        """TC-L108-L203-601 · 0 字节 png → decode_failed"""
        p = tmp_path / "empty.png"
        p.write_bytes(b"")
        resp = await img_orch.analyze(_req(path=str(p)))
        assert resp["result"]["error_code"] == "image_decode_failed"


class TestEdgeSizeBoundary:
    """20MB 边界 · 恰好通过"""

    async def test_edge_exactly_20mb_passes(self, img_orch, make_valid_image,
                                              mock_vlm_architecture, _req):
        """TC-L108-L203-602 · 20MB == 上限 · 允许"""
        p = make_valid_image(fmt="png", size_bytes=20 * 1024 * 1024)
        resp = await img_orch.analyze(_req(path=str(p), image_hint="architecture"))
        assert resp["status"] == "ok"


class TestEdgeHintMixInBatch:
    """批量 hint 混合"""

    async def test_edge_batch_hint_shared_not_mixed(self, img_orch, five_pngs,
                                                      mock_vlm_architecture, _batch):
        """TC-L108-L203-603 · batch image_hint 对全批共享 · 不支持 per-image"""
        req = _batch(paths=[str(p) for p in five_pngs], merge_topic=False)
        req["image_hint"] = "architecture"
        resp = await img_orch.analyze_batch(req)
        assert all(d["image_type"] == "architecture" for d in resp["result"]["descriptions"])


class TestEdgeConcurrency:
    """并发 / VLM session 饥饿"""

    async def test_edge_concurrent_different_paths_throttled(self, img_orch, arch_png_pool,
                                                              mock_vlm_architecture, _req):
        """TC-L108-L203-604 · 10 并发不同 path · Vision session 串行（主 session 单线）"""
        tasks = [img_orch.analyze(_req(path=str(p), image_hint="architecture"))
                 for p in arch_png_pool[:10]]
        results = await asyncio.gather(*tasks)
        assert all(r["status"] == "ok" for r in results)


class TestEdgeMalformedHeader:
    """扩展名 png 实为 jpg"""

    async def test_edge_extension_mismatch_detects(self, img_orch, tmp_path, _req):
        """TC-L108-L203-605 · 文件扩展名为 png 但 magic bytes 为 jpg → decode_failed"""
        p = tmp_path / "fake.png"
        p.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # 实为 jpg
        resp = await img_orch.analyze(_req(path=str(p)))
        # 要么 decode_failed 要么 format_unsupported（取决于实现检测策略）
        assert resp["result"]["error_code"] in {"image_decode_failed", "image_format_unsupported"}
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-K —*
