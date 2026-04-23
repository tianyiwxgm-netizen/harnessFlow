"""Startup-time configuration validation (L2-04 §3.7 external_endpoint_blocked)."""

from __future__ import annotations

from typing import Any

from app.multimodal.common.errors import L108Error


def validate_startup_config(config: dict[str, Any]) -> None:
    """Block startup if config declares non-empty external endpoints."""
    endpoints = config.get("endpoints")
    if endpoints:  # truthy list / dict / str → blocked
        raise L108Error(
            "external_endpoint_blocked",
            f"external endpoints not allowed: {endpoints!r}",
        )
