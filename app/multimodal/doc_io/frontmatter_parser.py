"""Frontmatter parser · python-frontmatter wrapper with strict validation."""

from __future__ import annotations

from typing import Any

import frontmatter

from app.multimodal.common.errors import L108Error


# Keys required by harnessFlow doc convention · aligned with 3-1/3-2 template
REQUIRED_KEYS: frozenset[str] = frozenset({"doc_id", "doc_type"})


def parse(raw_text: str) -> tuple[dict[str, Any], str]:
    """Parse raw md text → (metadata_dict, body_str).

    Returns empty dict + original text when no frontmatter block present.
    Raises L108Error('type_mismatch') on malformed YAML block.
    """
    try:
        post = frontmatter.loads(raw_text)
    except Exception as e:  # YAMLError etc.
        raise L108Error("type_mismatch", f"malformed frontmatter: {e}") from e
    return dict(post.metadata), post.content


def assert_required_keys(metadata: dict[str, Any]) -> None:
    """Write-time guard · all REQUIRED_KEYS must be present."""
    missing = REQUIRED_KEYS - metadata.keys()
    if missing:
        raise L108Error(
            "type_mismatch",
            f"frontmatter missing required keys: {sorted(missing)}",
        )


def dump(metadata: dict[str, Any], body: str) -> str:
    """Render md text with frontmatter block."""
    post = frontmatter.Post(content=body, **metadata)
    return frontmatter.dumps(post)
