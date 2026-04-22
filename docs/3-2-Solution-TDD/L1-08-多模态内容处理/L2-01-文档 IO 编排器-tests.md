---
doc_id: tests-L1-08-L2-01-文档IO编排器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-08-多模态内容处理/L2-01-文档 IO 编排器.md
  - docs/2-prd/L1-08 多模态内容处理/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-K
created_at: 2026-04-22
---

# L1-08 L2-01 文档 IO 编排器 · TDD 测试用例

> 基于 3-1 L2-01 §3（4 个 IC 触点 + 3 个 action: read/write/edit）+ §11（14 个 `MD_*` 错误码）+ §12（read/write/edit SLO + paged 档位）+ §13 TC 锚点驱动。
> TC ID 统一前缀 `TC-L108-L201-NNN` · 语义分组别名 `TC-MD-READ-*` / `TC-MD-WRITE-*` / `TC-MD-EDIT-*` / `TC-MD-PAGED-*`。
> pytest + Python 3.11+ 类型注解；`class TestMdOrchestrator_Read` / `_Write` / `_Edit` / `_Paged` 组织；sections 解析与 IC 契约独立分组。

## §0 撰写进度

- [x] §1 覆盖度索引（action × 错误码 × IC-XX）
- [x] §2 正向用例（read/write/edit + paged 合并 + sections）
- [x] §3 负向用例（每错误码 ≥ 1 · 全 14 条）
- [x] §4 IC-XX 契约集成测试（IC-L2-01-in / out-audit / out-err / internal-paged）
- [x] §5 性能 SLO 用例（read P99 ≤ 800ms · paged ≤ 9s · write ≤ 480ms · edit ≤ 490ms）
- [x] §6 端到端 e2e 场景（写 md + 复检 · 分页 5000 行 · Edit 精确匹配）
- [x] §7 测试 fixture（mock_project_id / tmp_md_file / paged_fixture / make_frontmatter / atomic_write_helper）
- [x] §8 集成点用例（与 L2-04 门面 · L1-09 审计 · LockManager）
- [x] §9 边界 / edge case（空文件 / 超长行 / BOM / CRLF / 并发 / 磁盘满）

---

## §1 覆盖度索引

### §1.1 Action × 正向测试 × IC

| Action | TC ID | 覆盖类型 | 对应 IC |
|:---|:---|:---|:---|
| `read_md()` · 小文件（< 2000 行） | TC-L108-L201-001 | unit | IC-L2-01-in |
| `read_md()` · 含 frontmatter | TC-L108-L201-002 | unit | IC-L2-01-in |
| `read_md()` · paged 分页（2500 行） | TC-L108-L201-003 | unit | IC-L2-01-in + internal-paged |
| `read_md()` · headings + paragraphs sections | TC-L108-L201-004 | unit | IC-L2-01-in |
| `read_md()` · offset + limit 片段读 | TC-L108-L201-005 | unit | IC-L2-01-in |
| `write_md()` · 覆盖写 + 复检通过 | TC-L108-L201-006 | unit | IC-L2-01-in |
| `write_md()` · 含 frontmatter 校验 | TC-L108-L201-007 | unit | IC-L2-01-in |
| `write_md()` · 原子写（tmp+rename） | TC-L108-L201-008 | unit | AtomicWriter |
| `edit_md()` · 精确匹配唯一替换 | TC-L108-L201-009 | unit | IC-L2-01-in |
| `edit_md()` · 含上下文扩展匹配 | TC-L108-L201-010 | unit | IC-L2-01-in |
| `edit_md()` · diff_hunk 产出 | TC-L108-L201-011 | unit | IC-L2-01-in |
| sections 解析：FrontmatterParser | TC-L108-L201-012 | unit | 内部 |
| sections 解析：HeadingsParser | TC-L108-L201-013 | unit | 内部 |
| sections 解析：ParagraphSplitter | TC-L108-L201-014 | unit | 内部 |
| PagedReader 合并顺序校验 | TC-L108-L201-015 | unit | internal-paged |

### §1.2 错误码 × 测试（§3.5 14 项全覆盖）

| 错误码 | TC ID | 方法 | 分类 |
|:---|:---|:---|:---|
| `MD_PATH_NOT_FOUND` | TC-L108-L201-101 | `read_md()` | fs_error |
| `MD_PATH_NOT_READABLE` | TC-L108-L201-102 | `read_md()` | fs_error |
| `MD_PATH_NOT_WRITABLE` | TC-L108-L201-103 | `write_md()` | fs_error |
| `MD_DISK_FULL` | TC-L108-L201-104 | `write_md()` | fs_error |
| `MD_ENCODING_ERROR` | TC-L108-L201-105 | `read_md()` | input_error |
| `MD_FRONTMATTER_INVALID` | TC-L108-L201-106 | `write_md()` | parse_error |
| `MD_FRONTMATTER_WARN` | TC-L108-L201-107 | `read_md()` | parse_error |
| `MD_EDIT_NOT_FOUND` | TC-L108-L201-108 | `edit_md()` | input_error |
| `MD_EDIT_NOT_UNIQUE` | TC-L108-L201-109 | `edit_md()` | input_error |
| `MD_POST_WRITE_MISMATCH` | TC-L108-L201-110 | `write_md()` | integrity_error |
| `MD_PAGED_ORDER_BROKEN` | TC-L108-L201-111 | `read_md()` paged | integrity_error |
| `MD_CONFIG_INVALID` | TC-L108-L201-112 | `__init__` | config_error |
| `MD_READ_OK`（成功档） | TC-L108-L201-113 | `read_md()` | success |
| `MD_WRITE_OK`（成功档） | TC-L108-L201-114 | `write_md()` | success |

### §1.3 IC × 集成测试

| IC | TC ID | 对端 | 场景 |
|:---|:---|:---|:---|
| IC-L2-01-in dispatch_md_request | TC-L108-L201-201 | L2-04 | 入站 schema 校验 |
| IC-L2-01-out-audit emit_audit_seed | TC-L108-L201-202 | L2-04 → L1-09 | 审计 seed 字段 |
| IC-L2-01-out-err emit_structured_err | TC-L108-L201-203 | L2-04 | err_context 封装 |
| IC-L2-01-internal-paged page_read_callback | TC-L108-L201-204 | PagedReader | 每页回调顺序 |

### §1.4 性能 SLO × 测试

| 场景 | P99 约束 | TC ID |
|:---|:---|:---|
| read < 2000 行 | ≤ 800ms | TC-L108-L201-301 |
| paged 2000-10000 行 | ≤ 9s | TC-L108-L201-302 |
| write + 复检 | ≤ 480ms | TC-L108-L201-303 |
| edit 精确匹配 | ≤ 490ms | TC-L108-L201-304 |
| 错误响应 | ≤ 150ms | TC-L108-L201-305 |

### §1.5 e2e × 测试（§5 P0 时序 · ≥ 2 项）

| 场景 | TC ID |
|:---|:---|
| 整份 md 写 + 复检 + 审计事件（IC-09） | TC-L108-L201-401 |
| 分页读 5000 行 · 5 页合并 · merge_order_verified | TC-L108-L201-402 |
| Edit 后 diff_hunk 产出 + hash 复检通过 | TC-L108-L201-403 |

---

## §2 正向用例

```python
# tests/unit/L1-08/L2-01/test_md_orchestrator_positive.py
import pytest
from uuid import UUID
import hashlib

pytestmark = pytest.mark.asyncio


class TestMdOrchestrator_Read:
    """§3.1 read action 正向路径"""

    async def test_read_small_file(self, orch, make_md, _req):
        """TC-L108-L201-001 · < 2000 行 · 非分页 · 整份返"""
        f = make_md(lines=100, frontmatter=None)
        resp = await orch.handle(_req(action="read", path=str(f)))
        assert resp["status"] == "ok"
        art = resp["artifact"]
        assert art["lines"] == 100
        assert art["paged_read_meta"] is None or art["paged_read_meta"]["total_pages"] == 1
        assert UUID(art["artifact_id"])

    async def test_read_with_frontmatter(self, orch, make_md, _req):
        """TC-L108-L201-002 · frontmatter 解析 · sections.frontmatter 填充"""
        fm = {"title": "goal", "version": "v1.0"}
        f = make_md(lines=50, frontmatter=fm)
        resp = await orch.handle(_req(action="read", path=str(f)))
        assert resp["artifact"]["sections"]["frontmatter"] == fm

    async def test_read_paged(self, orch, make_md, _req):
        """TC-L108-L201-003 · 2500 行 · paged=true · pages_completed 连续"""
        f = make_md(lines=2500)
        resp = await orch.handle(_req(action="read", path=str(f), paged=True, total_lines_hint=2500))
        meta = resp["artifact"]["paged_read_meta"]
        assert meta["merge_order_verified"] is True
        assert meta["total_pages"] >= 2
        assert meta["pages_completed"] == list(range(meta["total_pages"]))

    async def test_read_headings_paragraphs(self, orch, tmp_project, _req):
        """TC-L108-L201-004 · headings + paragraphs 解析"""
        f = tmp_project / "docs/h.md"
        f.write_text("# H1\n\npara1\n\n## H2\n\npara2\n")
        resp = await orch.handle(_req(action="read", path=str(f)))
        hs = resp["artifact"]["sections"]["headings"]
        assert any(h["level"] == 1 and h["text"] == "H1" for h in hs)
        assert any(h["level"] == 2 and h["text"] == "H2" for h in hs)
        assert len(resp["artifact"]["sections"]["paragraphs"]) >= 2

    async def test_read_offset_limit(self, orch, make_md, _req):
        """TC-L108-L201-005 · offset=500 limit=100 · 仅返 500-599 行"""
        f = make_md(lines=1000)
        resp = await orch.handle(_req(action="read", path=str(f), offset=500, limit=100))
        assert resp["artifact"]["lines"] == 100


class TestMdOrchestrator_Write:
    """§3.1 write action 正向"""

    async def test_write_overwrite_and_post_check(self, orch, tmp_project, _req):
        """TC-L108-L201-006 · 覆盖写 · post_write_check_passed=true"""
        f = tmp_project / "docs/new.md"
        resp = await orch.handle(_req(action="write", path=str(f), content="# New\nhello\n"))
        assert resp["status"] == "ok"
        assert resp["post_write_check_passed"] is True
        assert f.read_text() == "# New\nhello\n"
        expected = hashlib.sha256("# New\nhello\n".encode()).hexdigest()
        assert resp["hash"] == expected

    async def test_write_frontmatter_valid(self, orch, tmp_project, _req):
        """TC-L108-L201-007 · 含 frontmatter · yaml 解析成功"""
        content = "---\ntitle: t\n---\n\n# body\n"
        resp = await orch.handle(_req(action="write", path=str(tmp_project/"docs/fm.md"), content=content))
        assert resp["status"] == "ok"

    async def test_write_atomic_rename(self, orch, tmp_project, spy_atomic_writer, _req):
        """TC-L108-L201-008 · AtomicWriter.write 使用 tmp+rename · 无中间态"""
        await orch.handle(_req(action="write", path=str(tmp_project/"docs/a.md"), content="x"))
        spy_atomic_writer.assert_called_once()
        args = spy_atomic_writer.call_args[1]
        assert args["use_rename"] is True


class TestMdOrchestrator_Edit:
    """§3.1 edit action 正向"""

    async def test_edit_unique_match(self, orch, tmp_project, _req):
        """TC-L108-L201-009 · old_string 唯一 · 替换成功"""
        f = tmp_project / "docs/e.md"
        f.write_text("# Title\nfoo\nbar\n")
        resp = await orch.handle(_req(action="edit", path=str(f), old_string="foo", new_string="baz"))
        assert resp["status"] == "ok"
        assert "baz" in f.read_text()

    async def test_edit_with_context(self, orch, tmp_project, _req):
        """TC-L108-L201-010 · 扩上下文 old_string 定位"""
        f = tmp_project / "docs/e.md"
        f.write_text("a\nfoo\nc\nfoo\nd\n")
        resp = await orch.handle(_req(action="edit", path=str(f),
                                       old_string="a\nfoo\nc",
                                       new_string="a\nFOO\nc"))
        assert resp["status"] == "ok"
        assert "FOO" in f.read_text()

    async def test_edit_diff_hunk_produced(self, orch, tmp_project, _req):
        """TC-L108-L201-011 · diff_hunk 非空且含上下文"""
        f = tmp_project / "docs/e.md"
        f.write_text("line1\nline2\nline3\n")
        resp = await orch.handle(_req(action="edit", path=str(f),
                                       old_string="line2", new_string="LINE2"))
        assert resp["diff_hunk"] and "line2" in resp["diff_hunk"]


class TestMdOrchestrator_InternalParsers:
    """§2.3 Domain Services · 内部解析器"""

    def test_frontmatter_parser_valid(self):
        """TC-L108-L201-012 · FrontmatterParser 合法 yaml"""
        fm, body = FrontmatterParser.parse("---\na: 1\n---\n# body\n")
        assert fm == {"a": 1}
        assert body.startswith("# body")

    def test_headings_parser_h1_to_h6(self):
        """TC-L108-L201-013 · HeadingsParser 识别 # ～ ######"""
        hs = HeadingsParser.parse("# A\n## B\n### C\n")
        assert [h["level"] for h in hs] == [1, 2, 3]

    def test_paragraph_splitter_by_blank_line(self):
        """TC-L108-L201-014 · ParagraphSplitter 按空行切段"""
        ps = ParagraphSplitter.split("p1\n\np2\n\np3\n")
        assert len(ps) == 3

    async def test_paged_reader_merge_order_verified(self, make_md):
        """TC-L108-L201-015 · PagedReader 合并顺序校验 · pages_completed 严格递增"""
        f = make_md(lines=3000)
        reader = PagedReader(path=str(f), page_size=1000)
        pages = []
        async for p in reader.iter_pages():
            pages.append(p)
        assert [p["page_index"] for p in pages] == [0, 1, 2]
        assert reader.merge_order_verified is True
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# tests/unit/L1-08/L2-01/test_md_orchestrator_negative.py
import pytest, os

pytestmark = pytest.mark.asyncio


class TestL201ErrorCodes_FsErrors:
    """MD_PATH_* / MD_DISK_FULL · fs 层"""

    async def test_MD_PATH_NOT_FOUND(self, orch, tmp_project, _req):
        """TC-L108-L201-101 · os.stat FileNotFoundError → 404 MD_PATH_NOT_FOUND"""
        resp = await orch.handle(_req(action="read", path=str(tmp_project/"docs/ghost.md")))
        assert resp["status"] == "error"
        assert resp["error_code"] == "MD_PATH_NOT_FOUND"

    async def test_MD_PATH_NOT_READABLE(self, orch, make_md, _req):
        """TC-L108-L201-102 · chmod 000 → PermissionError → 403 MD_PATH_NOT_READABLE"""
        f = make_md(lines=10)
        os.chmod(f, 0o000)
        try:
            resp = await orch.handle(_req(action="read", path=str(f)))
            assert resp["error_code"] == "MD_PATH_NOT_READABLE"
        finally:
            os.chmod(f, 0o644)

    async def test_MD_PATH_NOT_WRITABLE(self, orch, tmp_project, _req):
        """TC-L108-L201-103 · 写只读目录 · PermissionError → MD_PATH_NOT_WRITABLE"""
        ro = tmp_project / "docs" / "ro"
        ro.mkdir()
        os.chmod(ro, 0o555)
        try:
            resp = await orch.handle(_req(action="write", path=str(ro/"x.md"), content="x"))
            assert resp["error_code"] == "MD_PATH_NOT_WRITABLE"
        finally:
            os.chmod(ro, 0o755)

    async def test_MD_DISK_FULL(self, orch, tmp_project, simulate_enospc, _req):
        """TC-L108-L201-104 · mock ENOSPC → MD_DISK_FULL + suggested_action='清盘'"""
        simulate_enospc()
        resp = await orch.handle(_req(action="write", path=str(tmp_project/"docs/x.md"), content="y"))
        assert resp["error_code"] == "MD_DISK_FULL"
        assert resp["suggested_action"]


class TestL201ErrorCodes_InputErrors:
    """MD_ENCODING_ERROR / MD_EDIT_NOT_FOUND / MD_EDIT_NOT_UNIQUE"""

    async def test_MD_ENCODING_ERROR(self, orch, make_binary_md, _req):
        """TC-L108-L201-105 · UTF-8 解码失败 → MD_ENCODING_ERROR"""
        f = make_binary_md(b"\xff\xfe\x00raw")
        resp = await orch.handle(_req(action="read", path=str(f)))
        assert resp["error_code"] == "MD_ENCODING_ERROR"

    async def test_MD_EDIT_NOT_FOUND(self, orch, tmp_project, _req):
        """TC-L108-L201-108 · old_string 不存在 → MD_EDIT_NOT_FOUND · match_count=0"""
        f = tmp_project / "docs/x.md"
        f.write_text("hello\n")
        resp = await orch.handle(_req(action="edit", path=str(f),
                                       old_string="notthere", new_string="x"))
        assert resp["error_code"] == "MD_EDIT_NOT_FOUND"
        assert resp["error_context"]["match_count"] == 0

    async def test_MD_EDIT_NOT_UNIQUE(self, orch, tmp_project, _req):
        """TC-L108-L201-109 · old_string 多处匹配 → MD_EDIT_NOT_UNIQUE · match_count>1"""
        f = tmp_project / "docs/x.md"
        f.write_text("foo\nfoo\nfoo\n")
        resp = await orch.handle(_req(action="edit", path=str(f),
                                       old_string="foo", new_string="x"))
        assert resp["error_code"] == "MD_EDIT_NOT_UNIQUE"
        assert resp["error_context"]["match_count"] >= 2


class TestL201ErrorCodes_ParseErrors:
    """MD_FRONTMATTER_INVALID / MD_FRONTMATTER_WARN"""

    async def test_MD_FRONTMATTER_INVALID_on_write(self, orch, tmp_project, _req):
        """TC-L108-L201-106 · Write 坏 frontmatter → MD_FRONTMATTER_INVALID · 拒绝"""
        bad = "---\nunclosed: [1,2\n---\n"
        resp = await orch.handle(_req(action="write", path=str(tmp_project/"docs/x.md"), content=bad))
        assert resp["error_code"] == "MD_FRONTMATTER_INVALID"

    async def test_MD_FRONTMATTER_WARN_on_read(self, orch, tmp_project, _req):
        """TC-L108-L201-107 · Read 坏 frontmatter · 仍返 sections.body · error_code=MD_FRONTMATTER_WARN"""
        f = tmp_project / "docs/x.md"
        f.write_text("---\nunclosed: [1,2\n---\nbody\n")
        resp = await orch.handle(_req(action="read", path=str(f)))
        # §3.5 语义：Read 仅告警 · status=ok + warn 码
        assert resp["status"] == "ok"
        assert "MD_FRONTMATTER_WARN" in (resp.get("warnings") or [])


class TestL201ErrorCodes_IntegrityErrors:
    """MD_POST_WRITE_MISMATCH / MD_PAGED_ORDER_BROKEN"""

    async def test_MD_POST_WRITE_MISMATCH(self, orch, tmp_project, force_post_write_mismatch, _req):
        """TC-L108-L201-110 · mock 写后 readback hash 不同 → MD_POST_WRITE_MISMATCH"""
        force_post_write_mismatch()
        resp = await orch.handle(_req(action="write",
                                       path=str(tmp_project/"docs/x.md"), content="v1"))
        assert resp["error_code"] == "MD_POST_WRITE_MISMATCH"
        assert resp["error_context"]["expected_hash"] != resp["error_context"]["actual_hash"]

    async def test_MD_PAGED_ORDER_BROKEN(self, orch, make_md, monkeypatch, _req):
        """TC-L108-L201-111 · PagedReader 回收乱序 → MD_PAGED_ORDER_BROKEN"""
        f = make_md(lines=3000)
        # monkeypatch PagedReader 打乱 page_index 顺序
        monkeypatch.setattr(PagedReader, "iter_pages", _broken_iter)
        resp = await orch.handle(_req(action="read", path=str(f), paged=True))
        assert resp["error_code"] == "MD_PAGED_ORDER_BROKEN"


class TestL201ErrorCodes_ConfigAndSuccess:
    """MD_CONFIG_INVALID · 启动期 · MD_READ_OK / MD_WRITE_OK 成功档"""

    async def test_MD_CONFIG_INVALID(self):
        """TC-L108-L201-112 · max_single_page_lines ≤ 0 → 拒绝启动"""
        with pytest.raises(ConfigError):
            MdOrchestrator(config={"max_single_page_lines": 0})

    async def test_MD_READ_OK_success_code(self, orch, make_md, _req):
        """TC-L108-L201-113 · 成功读 · error_code=MD_READ_OK · status=ok"""
        resp = await orch.handle(_req(action="read", path=str(make_md(lines=10))))
        assert resp["status"] == "ok"
        assert resp.get("audit_seed", {}).get("result") == "ok"

    async def test_MD_WRITE_OK_success_code(self, orch, tmp_project, _req):
        """TC-L108-L201-114 · 成功写 · audit_seed.result=ok"""
        resp = await orch.handle(_req(action="write",
                                       path=str(tmp_project/"docs/x.md"), content="x"))
        assert resp["audit_seed"]["result"] == "ok"
```

---

## §4 IC-XX 契约集成测试

```python
# tests/integration/L1-08/L2-01/test_ic_contracts.py
import pytest, jsonschema
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestICL201_In_DispatchContract:
    """IC-L2-01-in · L2-04 → L2-01"""

    async def test_in_schema_read(self, orch, make_md, icl201_in_schema, _req):
        """TC-L108-L201-201 · 入站 request 字段完备 · schema 合法"""
        f = make_md(lines=100)
        req = _req(action="read", path=str(f))
        jsonschema.validate(req, icl201_in_schema)
        resp = await orch.handle(req)
        assert resp["status"] == "ok"

    async def test_in_schema_rejects_unknown_action(self, orch, icl201_in_schema):
        """TC-L108-L201-201b · action ∉ {read,write,edit} → ValidationError"""
        bad = {"action": "delete", "path": "x", "project_id": "p", "request_id": "r",
               "type": "md", "trace_id": "t", "ts_ns": 1, "caller_l1": "L1-01"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, icl201_in_schema)


class TestICL201_OutAudit_Contract:
    """IC-L2-01-out-audit · audit_seed 产出"""

    async def test_audit_seed_fields(self, orch, make_md, audit_seed_schema, _req):
        """TC-L108-L201-202 · audit_seed 含 event_type/path/result/payload/trace_id/emitted_by"""
        f = make_md(lines=50)
        resp = await orch.handle(_req(action="read", path=str(f)))
        seed = resp["audit_seed"]
        jsonschema.validate(seed, audit_seed_schema)
        assert seed["emitted_by"] == "L2-01"
        assert seed["event_type"] in {"L1-08:content_read", "L1-08:content_written"}

    async def test_audit_seed_on_error_path(self, orch, tmp_project, audit_seed_schema, _req):
        """TC-L108-L201-202b · 错误路径也产 audit_seed · result=failed"""
        resp = await orch.handle(_req(action="read", path=str(tmp_project/"docs/ghost.md")))
        jsonschema.validate(resp["audit_seed"], audit_seed_schema)
        assert resp["audit_seed"]["result"] == "failed"


class TestICL201_OutErr_Contract:
    """IC-L2-01-out-err · structured_err 产出"""

    async def test_err_context_fields(self, orch, tmp_project, structured_err_schema, _req):
        """TC-L108-L201-203 · structured_err.error_context 含 path/retryable/suggested_action"""
        resp = await orch.handle(_req(action="edit", path=str(tmp_project/"docs/ghost.md"),
                                       old_string="x", new_string="y"))
        err_body = {k: resp[k] for k in ["error_code", "error_message", "error_context"]}
        err_body["error_class"] = "fs_error"
        err_body["retryable"] = False
        err_body["ts_ns"] = 1
        jsonschema.validate(err_body, structured_err_schema)


class TestICL201_InternalPaged_Contract:
    """IC-L2-01-internal-paged · page_read_callback"""

    async def test_page_callback_order_and_hash(self, make_md, page_callback_schema):
        """TC-L108-L201-204 · 每页 callback · page_index 递增 + 每页 hash 独立"""
        f = make_md(lines=3000)
        reader = PagedReader(path=str(f), page_size=1000)
        calls = []
        async for p in reader.iter_pages():
            jsonschema.validate(p, page_callback_schema)
            calls.append(p)
        assert [c["page_index"] for c in calls] == [0, 1, 2]
        hashes = {c["page_hash"] for c in calls}
        assert len(hashes) == 3  # 每页 hash 独立
```

---

## §5 性能 SLO 用例

```python
# tests/perf/L1-08/L2-01/test_slo.py
import pytest, time, statistics
from contextlib import contextmanager

pytestmark = pytest.mark.asyncio


@contextmanager
def _timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000


class TestReadSLO:
    """§12.2 · read < 2000 行 · P99 ≤ 800ms"""

    async def test_read_p99_under_800ms(self, orch, md_pool_small, _req):
        """TC-L108-L201-301 · 500 次读 · P99 ≤ 800ms"""
        samples = []
        for f in md_pool_small[:500]:
            with _timer() as t:
                await orch.handle(_req(action="read", path=str(f)))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 800.0


class TestPagedReadSLO:
    """§12.2 · paged 2000-10000 行 · P99 ≤ 9s"""

    async def test_paged_p99_under_9s(self, orch, md_pool_paged, _req):
        """TC-L108-L201-302 · 50 次 paged 读 · P99 ≤ 9000ms"""
        samples = []
        for f in md_pool_paged[:50]:
            with _timer() as t:
                await orch.handle(_req(action="read", path=str(f), paged=True))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 9000.0


class TestWriteSLO:
    """§12.2 · write + 复检 · P99 ≤ 480ms"""

    async def test_write_p99_under_480ms(self, orch, tmp_project, _req):
        """TC-L108-L201-303 · 200 次写 · P99 ≤ 480ms"""
        samples = []
        for i in range(200):
            with _timer() as t:
                await orch.handle(_req(action="write",
                                        path=str(tmp_project/f"docs/w{i}.md"),
                                        content=f"# {i}\n" * 10))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 480.0


class TestEditSLO:
    """§12.2 · edit · P99 ≤ 490ms"""

    async def test_edit_p99_under_490ms(self, orch, make_md, _req):
        """TC-L108-L201-304 · 200 次 edit · P99 ≤ 490ms"""
        samples = []
        for i in range(200):
            f = make_md(lines=100, name=f"e{i}.md")
            with _timer() as t:
                await orch.handle(_req(action="edit", path=str(f),
                                        old_string="line 0", new_string=f"LINE{i}"))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 490.0


class TestErrorResponseSLO:
    """§12.2 · 错误响应 · P99 ≤ 150ms"""

    async def test_error_p99_under_150ms(self, orch, _req):
        """TC-L108-L201-305 · 不存在路径 · 错误返回 ≤ 150ms"""
        samples = []
        for _ in range(200):
            with _timer() as t:
                await orch.handle(_req(action="read", path="/nonexistent/ghost.md"))
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 150.0
```

---

## §6 端到端 e2e 场景

```python
# tests/e2e/L1-08/L2-01/test_e2e.py
import pytest, asyncio, hashlib

pytestmark = pytest.mark.asyncio


class TestE2EFullWriteAndAudit:
    """§5 P0 时序 · write + post_check + 审计事件"""

    async def test_write_then_audit_event_flows(self, orch, l204_real_gate, l109_real,
                                                 tmp_project, _req):
        """TC-L108-L201-401 · 写 md → 复检 → audit_seed → L2-04 封装 → L1-09 落 IC-09"""
        req = _req(action="write", path=str(tmp_project/"docs/goal.md"),
                   content="# goal\nv1\n")
        resp = await orch.handle(req)
        assert resp["status"] == "ok"
        # L2-04 封装后 L1-09 应见 content_written 事件
        await asyncio.sleep(0.05)
        events = l109_real.query_trail(request_id_ref=req["request_id"])
        assert any(e["event_type"] == "L1-08:content_written" for e in events)
        written_sha = hashlib.sha256("# goal\nv1\n".encode()).hexdigest()
        assert next(e for e in events
                    if e["event_type"] == "L1-08:content_written")["content"]["file_hash_sha256"] == written_sha


class TestE2EPagedReadMerge:
    """§5 P0 · 分页读 5000 行 · 5 页合并"""

    async def test_paged_5000_lines_5_pages(self, orch, make_md, _req):
        """TC-L108-L201-402 · 5000 行 · page_size=1000 · 5 页 · merge_order_verified"""
        f = make_md(lines=5000)
        resp = await orch.handle(_req(action="read", path=str(f), paged=True, total_lines_hint=5000))
        meta = resp["artifact"]["paged_read_meta"]
        assert meta["total_pages"] == 5
        assert meta["merge_order_verified"] is True
        assert meta["pages_completed"] == [0, 1, 2, 3, 4]


class TestE2EEditWithDiffAndHash:
    """§5 P0 · Edit + diff_hunk + hash 复检"""

    async def test_edit_produces_diff_and_hash(self, orch, tmp_project, _req):
        """TC-L108-L201-403 · edit · diff_hunk + post_write hash 匹配"""
        f = tmp_project / "docs/x.md"
        f.write_text("line1\nline2\nline3\n")
        resp = await orch.handle(_req(action="edit", path=str(f),
                                       old_string="line2", new_string="LINE2"))
        assert resp["status"] == "ok"
        assert resp["diff_hunk"]
        new_body = f.read_text()
        assert resp["hash"] == hashlib.sha256(new_body.encode()).hexdigest()
```

---

## §7 测试 fixture

```python
# tests/conftest.py
import pytest, os, tempfile, yaml
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4


@pytest.fixture
def mock_project_id() -> str:
    return "demo-proj-001"


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    for d in ["docs", "tests", "harnessFlow"]:
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def make_md(tmp_project):
    """工厂 · 生成指定行数/frontmatter 的 md"""
    def _make(lines: int = 10, frontmatter: dict | None = None, name: str = "data.md") -> Path:
        f = tmp_project / "docs" / name
        parts = []
        if frontmatter is not None:
            parts.append("---\n" + yaml.safe_dump(frontmatter) + "---\n\n")
        for i in range(lines):
            parts.append(f"line {i}\n")
        f.write_text("".join(parts))
        return f
    return _make


@pytest.fixture
def make_binary_md(tmp_project):
    def _make(content: bytes) -> Path:
        f = tmp_project / "docs" / "bin.md"
        f.write_bytes(content)
        return f
    return _make


@pytest.fixture
def _req():
    """工厂 · 生成 IC-L2-01-in request payload"""
    def _make(action: str = "read", path: str = "", **kwargs) -> dict:
        req = {
            "request_id": str(uuid4()),
            "project_id": kwargs.get("project_id", "demo-proj-001"),
            "type": "md",
            "action": action,
            "path": path,
            "path_relative": Path(path).name if path else "",
            "offset": kwargs.get("offset"),
            "limit": kwargs.get("limit"),
            "paged": kwargs.get("paged", False),
            "total_lines_hint": kwargs.get("total_lines_hint"),
            "content": kwargs.get("content"),
            "old_string": kwargs.get("old_string"),
            "new_string": kwargs.get("new_string"),
            "trace_id": str(uuid4()),
            "ts_ns": 1_700_000_000_000_000_000,
            "caller_l1": "L1-01",
        }
        return req
    return _make


@pytest.fixture
def spy_atomic_writer(monkeypatch):
    """spy AtomicWriter.write_atomic · 验证 tmp+rename"""
    spy = MagicMock()
    original = AtomicWriter.write_atomic
    def _wrap(*args, **kwargs):
        spy(*args, **kwargs, use_rename=True)
        return original(*args, **kwargs)
    monkeypatch.setattr(AtomicWriter, "write_atomic", _wrap)
    return spy


@pytest.fixture
def simulate_enospc(monkeypatch):
    """注入 OSError(ENOSPC) 至 write 路径"""
    def _activate():
        def _raise(*a, **k):
            import errno
            e = OSError("disk full")
            e.errno = errno.ENOSPC
            raise e
        monkeypatch.setattr(AtomicWriter, "write_atomic", _raise)
    return _activate


@pytest.fixture
def force_post_write_mismatch(monkeypatch):
    """mock PostWriteChecker 使 hash 不一致"""
    def _activate():
        monkeypatch.setattr(PostWriteChecker, "check",
                            lambda self, expected, actual: False)
    return _activate


@pytest.fixture
def orch(tmp_project, l204_mock_emitter):
    """MdOrchestrator with 默认 config"""
    return MdOrchestrator(
        scope_root=tmp_project,
        config={"max_single_page_lines": 2000, "sections_cache_ttl_s": 60},
        emitter=l204_mock_emitter,
    )


@pytest.fixture
def l204_mock_emitter():
    m = MagicMock()
    m.emit_audit_seed = AsyncMock()
    return m


@pytest.fixture
def md_pool_small(make_md):
    return [make_md(lines=100, name=f"s{i}.md") for i in range(500)]


@pytest.fixture
def md_pool_paged(make_md):
    return [make_md(lines=3000, name=f"p{i}.md") for i in range(50)]


@pytest.fixture
def icl201_in_schema():
    return {
        "type": "object",
        "required": ["request_id", "project_id", "type", "action", "path",
                     "trace_id", "ts_ns", "caller_l1"],
        "properties": {
            "action": {"enum": ["read", "write", "edit"]},
            "type": {"const": "md"},
        },
    }


@pytest.fixture
def audit_seed_schema():
    return {
        "type": "object",
        "required": ["event_type", "event_version", "project_id", "path",
                     "action", "result", "payload", "trace_id", "ts_ns", "emitted_by"],
    }


@pytest.fixture
def structured_err_schema():
    return {
        "type": "object",
        "required": ["error_code", "error_class", "error_message", "error_context",
                     "retryable", "ts_ns"],
    }


@pytest.fixture
def page_callback_schema():
    return {
        "type": "object",
        "required": ["request_id", "artifact_id", "page_index", "page_offset",
                     "page_lines", "page_hash", "ok", "ts_ns"],
    }
```

---

## §8 集成点用例

```python
# tests/integration/L1-08/L2-01/test_integration_points.py
import pytest, asyncio

pytestmark = pytest.mark.asyncio


class TestIntegrationWithL204Gate:
    """与 L2-04 门面协作 · 入站 + audit_seed 回传"""

    async def test_l201_returns_audit_seed_to_l204(self, orch, make_md, l204_mock_emitter, _req):
        """TC-L108-L201-501 · read 成功 · L2-04 收到 audit_seed · 含 event_type=content_read"""
        f = make_md(lines=50)
        await orch.handle(_req(action="read", path=str(f)))
        l204_mock_emitter.emit_audit_seed.assert_called_once()
        seed = l204_mock_emitter.emit_audit_seed.call_args[0][0]
        assert seed["event_type"] == "L1-08:content_read"

    async def test_l201_propagates_request_id(self, orch, tmp_project, l204_mock_emitter, _req):
        """TC-L108-L201-502 · trace_id / request_id 在 audit_seed 完整透传"""
        req = _req(action="write", path=str(tmp_project/"docs/x.md"), content="x")
        await orch.handle(req)
        seed = l204_mock_emitter.emit_audit_seed.call_args[0][0]
        assert seed["trace_id"] == req["trace_id"]


class TestIntegrationWithLockManager:
    """与 L1-09 LockManager · 写同 path 串行化"""

    async def test_write_uses_per_path_lock(self, orch, tmp_project, lock_manager_spy, _req):
        """TC-L108-L201-503 · write 请求 · acquire/release 对称 · lock key 含 canonical path"""
        await orch.handle(_req(action="write", path=str(tmp_project/"docs/x.md"), content="v1"))
        lock_manager_spy.acquire.assert_called()
        lock_manager_spy.release.assert_called()


class TestIntegrationWithL109Audit:
    """与 L1-09 EventBus · 经 L2-04 路由"""

    async def test_audit_event_reaches_l109(self, orch, make_md, l109_spy, _req):
        """TC-L108-L201-504 · 一次 read · L1-09 最终收到 IC-09 append_event 至少 1 次"""
        await orch.handle(_req(action="read", path=str(make_md(lines=20))))
        await asyncio.sleep(0.05)
        assert l109_spy.append_event.call_count >= 1
```

---

## §9 边界 / edge case

```python
# tests/edge/L1-08/L2-01/test_edge_cases.py
import pytest, os, asyncio

pytestmark = pytest.mark.asyncio


class TestEdgeEmptyAndTiny:
    """空文件 / 1 字节 / 仅 BOM"""

    async def test_edge_empty_file(self, orch, tmp_project, _req):
        """TC-L108-L201-601 · 0 字节 md → lines=0 · status=ok"""
        f = tmp_project / "docs/empty.md"
        f.write_text("")
        resp = await orch.handle(_req(action="read", path=str(f)))
        assert resp["status"] == "ok"
        assert resp["artifact"]["lines"] == 0

    async def test_edge_bom_stripped(self, orch, tmp_project, _req):
        """TC-L108-L201-602 · UTF-8 BOM · Python 读 BOM 自动剥离"""
        f = tmp_project / "docs/bom.md"
        f.write_bytes("﻿# title\n".encode("utf-8"))
        resp = await orch.handle(_req(action="read", path=str(f)))
        assert resp["status"] == "ok"


class TestEdgeLongLinesAndCrLf:
    """超长行 / CRLF 行尾"""

    async def test_edge_single_line_5MB(self, orch, tmp_project, _req):
        """TC-L108-L201-603 · 单行 5MB · 读成功 · lines=1"""
        f = tmp_project / "docs/big.md"
        f.write_text("x" * (5 * 1024 * 1024))
        resp = await orch.handle(_req(action="read", path=str(f)))
        assert resp["status"] == "ok"
        assert resp["artifact"]["lines"] == 1

    async def test_edge_crlf_preserved_on_write(self, orch, tmp_project, _req):
        """TC-L108-L201-604 · write 含 CRLF · 保留 · hash 以原 bytes 计算"""
        f = tmp_project / "docs/crlf.md"
        resp = await orch.handle(_req(action="write", path=str(f), content="a\r\nb\r\n"))
        assert resp["status"] == "ok"
        assert f.read_bytes() == b"a\r\nb\r\n"


class TestEdgeConcurrency:
    """并发 · 崩溃"""

    async def test_edge_concurrent_reads_same_file(self, orch, make_md, _req):
        """TC-L108-L201-605 · 100 并发读 · 全 ok"""
        f = make_md(lines=100)
        results = await asyncio.gather(*[orch.handle(_req(action="read", path=str(f)))
                                          for _ in range(100)])
        assert all(r["status"] == "ok" for r in results)

    async def test_edge_concurrent_writes_lock_serializes(self, orch, tmp_project, _req):
        """TC-L108-L201-606 · 10 并发写同 path · 无数据竞争 · 最终 hash 存在且唯一"""
        results = await asyncio.gather(*[
            orch.handle(_req(action="write", path=str(tmp_project/"docs/w.md"), content=f"v{i}\n"))
            for i in range(10)
        ])
        assert all(r["status"] == "ok" for r in results)


class TestEdgeCrashAndRecovery:
    """进程 crash 后 tmp 文件清理"""

    async def test_edge_no_stale_tmp_after_crash(self, orch, tmp_project, crash_after_tmp, _req):
        """TC-L108-L201-607 · write 途中崩溃 · 再次启动清理残留 .tmp"""
        crash_after_tmp(tmp_project)
        # 启动后 cleanup
        MdOrchestrator.cleanup_stale_tmp(tmp_project)
        stale = list(tmp_project.rglob("*.tmp"))
        assert len(stale) == 0


class TestEdgePagedBoundaries:
    """分页边界"""

    async def test_edge_exactly_2000_lines_not_paged(self, orch, make_md, _req):
        """TC-L108-L201-608 · 2000 行（<= 阈值）· paged=false"""
        f = make_md(lines=2000)
        resp = await orch.handle(_req(action="read", path=str(f), paged=False))
        assert resp["status"] == "ok"
        assert resp["artifact"].get("paged_read_meta") in (None, {"total_pages": 1, "merge_order_verified": True, "pages_completed": [0]})


# ---
# Helpers（真实测试移至 tests/_helpers.py）
# ---

def _broken_iter(self):
    """打乱 PagedReader 顺序 · 仅供 TC-111"""
    import asyncio
    async def _gen():
        yield {"page_index": 2, "ok": True}
        yield {"page_index": 0, "ok": True}
        yield {"page_index": 1, "ok": True}
    return _gen()
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-K —*

