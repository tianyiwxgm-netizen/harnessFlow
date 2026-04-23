"""TemplateLoader + TemplateRegistry · 对齐 tech §6.3。

启动时扫 `template_dir/**/*.md`，为每份含 `kind` 的模板：
  1. 解析 YAML frontmatter
  2. 用 jsonschema 校验 slot_schema 自身合法性
  3. 用 Jinja2 SandboxedEnvironment 预编译（语法错即 raise E004）
  4. 注册到 TemplateRegistry
最后对比 required_kinds · 缺即 StartupError。
"""
from __future__ import annotations

import glob
import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jinja2
import jsonschema
import yaml

try:
    from yaml import CSafeLoader as _YamlSafeLoader  # C-accelerated
except ImportError:  # pragma: no cover
    from yaml import SafeLoader as _YamlSafeLoader  # type: ignore[assignment]

from app.project_lifecycle.template_engine.errors import (
    E_TEMPLATE_SYNTAX_ERROR,
    StartupError,
    TemplateEngineError,
)
from app.project_lifecycle.template_engine.sandbox import build_sandbox_env
from app.project_lifecycle.template_engine.schemas import TemplateEntry

# 29 必需 kind（2 kickoff + 4 fourset + 9 pmp + 11 togaf + 3 closing）
REQUIRED_KINDS_DEFAULT: tuple[str, ...] = (
    "kickoff.goal", "kickoff.scope",
    "fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd",
    "pmp.integration", "pmp.scope", "pmp.schedule", "pmp.cost", "pmp.quality",
    "pmp.resource", "pmp.communication", "pmp.risk", "pmp.procurement",
    "togaf.preliminary",
    "togaf.phase_a", "togaf.phase_b",
    "togaf.phase_c_data", "togaf.phase_c_application",
    "togaf.phase_d", "togaf.phase_e", "togaf.phase_f", "togaf.phase_g", "togaf.phase_h",
    "togaf.adr",
    "closing.lessons_learned", "closing.delivery_manifest", "closing.retro_summary",
)


def _sha256_file(fp: str) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """分离 `---\\n<yaml>\\n---\\n<body>`。非 frontmatter 返 ({}, text)。"""
    if not text.startswith("---"):
        return {}, text
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    idx = rest.find("\n---")
    if idx < 0:
        return {}, text
    fm_str = rest[:idx]
    body = rest[idx + 4:]
    if body.startswith("\n"):
        body = body[1:]
    try:
        fm = yaml.load(fm_str, Loader=_YamlSafeLoader) or {}
    except yaml.YAMLError as exc:
        raise StartupError(f"frontmatter YAML error: {exc}") from exc
    if not isinstance(fm, dict):
        return {}, text
    return fm, body


@dataclass
class TemplateRegistry:
    _entries: dict[str, TemplateEntry] = field(default_factory=dict)

    def register(self, entry: TemplateEntry) -> None:
        self._entries[entry.kind] = entry

    def lookup(self, kind: str) -> TemplateEntry | None:
        return self._entries.get(kind)

    def kinds(self) -> list[str]:
        return list(self._entries.keys())

    def list(self) -> list[str]:
        return sorted(self._entries.keys())

    def get_version(self, kind: str) -> str | None:
        e = self._entries.get(kind)
        return e.version if e else None

    def __len__(self) -> int:
        return len(self._entries)


@dataclass
class TemplateLoader:
    template_dir: str
    required_kinds: tuple[str, ...] | list[str] = REQUIRED_KINDS_DEFAULT
    validate_slot_schemas: bool = False
    """启动时是否跑 jsonschema Draft202012 meta-校验。默认 off（每次 check_schema 约 240ms × 29 ≈ 7s）。

    由 CI 里设置 `HARNESSFLOW_STRICT_SCHEMA_CHECK=1` 开启；运行时 slot validation 独立跑。
    """

    def load_all(self) -> TemplateRegistry:
        root = Path(self.template_dir)
        if not root.exists():
            raise StartupError(f"template_dir not found: {self.template_dir}")

        registry = TemplateRegistry()
        env = build_sandbox_env()

        # 1. 并行 I/O + YAML 解析（每文件独立）
        file_paths = sorted(glob.glob(f"{self.template_dir}/**/*.md", recursive=True))
        parsed: list[tuple[str, dict[str, Any], str]] = []  # (fp, fm, body)

        def _parse(fp: str) -> tuple[str, dict[str, Any], str] | None:
            text = Path(fp).read_text(encoding="utf-8")
            fm, body = _split_frontmatter(text)
            if not fm or "kind" not in fm:
                return None
            return fp, fm, body

        with ThreadPoolExecutor(max_workers=8) as ex:
            for result in ex.map(_parse, file_paths):
                if result is not None:
                    parsed.append(result)

        # 2. 并行 Jinja2 compile（CPU bound 但 Jinja 多数 C 优化过 · GIL 释放短暂）
        def _compile(args: tuple[str, dict[str, Any], str]) -> TemplateEntry:
            fp, fm, body = args
            kind = fm["kind"]
            version = fm.get("version", "")
            slot_schema = fm.get("slot_schema")

            if not version or not slot_schema:
                raise TemplateEngineError(
                    error_code=E_TEMPLATE_SYNTAX_ERROR,
                    message=f"missing version/slot_schema metadata in {fp}",
                )

            if self.validate_slot_schemas:
                try:
                    jsonschema.Draft202012Validator.check_schema(slot_schema)
                except jsonschema.SchemaError as exc:
                    raise TemplateEngineError(
                        error_code=E_TEMPLATE_SYNTAX_ERROR,
                        message=f"invalid slot_schema in {fp}: {exc.message}",
                    ) from exc

            try:
                template_obj = env.from_string(body)
            except jinja2.TemplateSyntaxError as exc:
                raise TemplateEngineError(
                    error_code=E_TEMPLATE_SYNTAX_ERROR,
                    message=f"Jinja2 syntax error in {fp}: {exc.message}",
                ) from exc

            return TemplateEntry(
                id=f"{kind}.{version}",
                kind=kind,
                version=version,
                slot_schema=slot_schema,
                template_obj=template_obj,
                file_path=fp,
                file_sha256=_sha256_file(fp),
            )

        with ThreadPoolExecutor(max_workers=8) as ex:
            for entry in ex.map(_compile, parsed):
                registry.register(entry)

        missing = set(self.required_kinds) - set(registry.kinds())
        if missing:
            raise StartupError(f"Missing required templates: {sorted(missing)}")

        return registry
