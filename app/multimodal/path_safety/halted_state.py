"""Global L1-07 HALTED flag · when True, L1-08 refuses I/O (halted_denied)."""

from __future__ import annotations


class HaltedState:
    """Singleton-ish state holder. Tests manipulate directly."""
    _halted: bool = False

    @classmethod
    def set(cls, flag: bool) -> None:
        cls._halted = bool(flag)

    @classmethod
    def is_halted(cls) -> bool:
        return cls._halted
