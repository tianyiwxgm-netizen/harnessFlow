class DependencyMissing(Exception):
    """Raised when a system dependency (ffprobe / curl / pytest / ...) is not
    available. The Verifier treats this as INSUFFICIENT_EVIDENCE (not FAIL)."""

    def __init__(self, tool: str, detail: str = ""):
        self.tool = tool
        self.detail = detail
        super().__init__(f"dependency missing: {tool} ({detail})")
