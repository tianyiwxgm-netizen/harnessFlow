"""L2-07 产出物模板引擎 · public API。

被 L2-02/03/04/05/06 通过 IC-L2-02 调用 · 发 IC-09 审计事件。
详见 `app/project_lifecycle/template_engine/README.md` 与 tech §3.1。
"""
from app.project_lifecycle.template_engine.engine import TemplateEngine
from app.project_lifecycle.template_engine.errors import StartupError, TemplateEngineError
from app.project_lifecycle.template_engine.registry import (
    REQUIRED_KINDS_DEFAULT,
    TemplateLoader,
    TemplateRegistry,
)
from app.project_lifecycle.template_engine.schemas import (
    RenderedOutput,
    TemplateEntry,
    ValidationResult,
)

__all__ = [
    "TemplateEngine",
    "TemplateLoader",
    "TemplateRegistry",
    "REQUIRED_KINDS_DEFAULT",
    "RenderedOutput",
    "TemplateEntry",
    "ValidationResult",
    "TemplateEngineError",
    "StartupError",
]
