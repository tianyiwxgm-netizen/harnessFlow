"""Smoke test — 验证 multimodal 包骨架可 import。"""


def test_package_imports():
    import app.multimodal  # noqa: F401
    import app.multimodal.code_structure  # noqa: F401
    import app.multimodal.common  # noqa: F401
    import app.multimodal.doc_io  # noqa: F401
    import app.multimodal.path_safety  # noqa: F401
    import app.multimodal.vision  # noqa: F401


def test_external_deps_present():
    """确保 WP-00 装的依赖都可 import（后续 WP 依赖这些）"""
    import frontmatter  # noqa: F401  (python-frontmatter 的 import 名)
    import networkx  # noqa: F401
    import PIL  # noqa: F401  (Pillow)
    import pytesseract  # noqa: F401
    import tree_sitter  # noqa: F401
    import tree_sitter_go  # noqa: F401
    import tree_sitter_java  # noqa: F401
    import tree_sitter_python  # noqa: F401
    import tree_sitter_rust  # noqa: F401
    import tree_sitter_typescript  # noqa: F401
