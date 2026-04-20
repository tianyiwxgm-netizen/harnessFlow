"""FastAPI backend for /harnessFlow-ui.

Serves:
  - /api/tasks                  list all task boards (enriched)
  - /api/tasks/{task_id}        single task detail (with artifacts)
  - /api/tasks/{task_id}/md     proxy read md file (by safe ?path=...)
  - /api/kb                     knowledge-base entries (mock)
  - /api/projects               projects registry (mock)
  - /api/stats                  aggregate stats
  - /                           serves frontend/index.html
  - /static/*                   nothing (frontend uses CDN only)
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from mock_data import (
    HARNESS_ROOT,
    list_all_task_boards,
    get_task_board,
    read_markdown_file,
    mock_knowledge_base,
    mock_projects,
    mock_admin_data,
)


app = FastAPI(title="harnessFlow-ui mock backend", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

FRONTEND_HTML = Path(__file__).resolve().parents[1] / "frontend" / "index.html"


@app.get("/")
def root():
    if FRONTEND_HTML.exists():
        return FileResponse(FRONTEND_HTML)
    return PlainTextResponse("frontend/index.html missing — scaffolding incomplete", status_code=500)


@app.get("/api/health")
def health():
    return {"status": "ok", "harness_root": str(HARNESS_ROOT)}


@app.get("/api/tasks")
def tasks_list():
    boards = list_all_task_boards()
    # Trim heavy fields for list view
    light = []
    for b in boards:
        # 优先使用 _derived.summary (中文正式标题)，回退到 goal_anchor.text
        derived = b.get("_derived") or {}
        goal_text = derived.get("summary") or (b.get("goal_anchor") or {}).get("text", "")[:200]
        light.append({
            "task_id": b.get("task_id"),
            "project": b.get("project", ""),
            "_scope": b.get("_scope"),
            "initial_user_input": (b.get("initial_user_input") or "")[:120],
            "goal_text": goal_text,
            "current_state": b.get("current_state"),
            "route_id": b.get("route_id") or b.get("route"),
            "size": b.get("size"),
            "task_type": b.get("task_type"),
            "risk": b.get("risk"),
            "progress_percentage": b.get("progress_percentage"),
            "created_at": b.get("created_at"),
            "closed_at": b.get("closed_at"),
            "final_outcome": b.get("final_outcome"),
            "retro_link": b.get("retro_link"),
            "archive_entry_link": b.get("archive_entry_link"),
        })
    return {"count": len(light), "tasks": light}


@app.get("/api/tasks/{task_id}")
def task_detail(task_id: str):
    b = get_task_board(task_id)
    if not b:
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    return b


@app.get("/api/tasks/{task_id}/md")
def task_md(task_id: str, path: str = Query(..., description="harnessFlow-root-relative path")):
    content = read_markdown_file(path)
    if content is None:
        raise HTTPException(status_code=404, detail=f"file not found or not allowed: {path}")
    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")


@app.get("/api/kb")
def kb_list(kind: str | None = None, scope: str | None = None, project_id: str | None = None):
    entries = mock_knowledge_base()
    if kind:
        entries = [e for e in entries if e["kind"] == kind]
    if scope:
        entries = [e for e in entries if e["scope"] == scope]
    if project_id:
        entries = [e for e in entries if e.get("project_id") == project_id]
    entries.sort(key=lambda e: e.get("evidence", {}).get("observed_count", 0), reverse=True)
    return {"count": len(entries), "entries": entries}


@app.get("/api/projects")
def projects_list():
    return {"count": len(mock_projects()), "projects": mock_projects()}


@app.get("/api/stats")
def stats():
    boards = list_all_task_boards()
    total = len(boards)
    by_state: dict[str, int] = {}
    by_route: dict[str, int] = {}
    by_project: dict[str, int] = {}
    success = 0
    active = 0
    paused = 0
    for b in boards:
        s = b.get("current_state", "UNKNOWN")
        by_state[s] = by_state.get(s, 0) + 1
        r = b.get("route_id") or b.get("route") or "?"
        by_route[r] = by_route.get(r, 0) + 1
        p = b.get("project", "unknown")
        by_project[p] = by_project.get(p, 0) + 1
        if b.get("final_outcome") == "success":
            success += 1
        if s in ("INIT", "CLARIFY", "ROUTE_SELECT", "PLAN", "IMPL", "VERIFY", "COMMIT"):
            active += 1
        if s == "PAUSED_ESCALATED":
            paused += 1
    closed = by_state.get("CLOSED", 0)
    success_rate = round(success / total * 100, 1) if total else 0
    return {
        "total": total,
        "closed": closed,
        "active": active,
        "paused": paused,
        "aborted": by_state.get("ABORTED", 0),
        "success_count": success,
        "success_rate_pct": success_rate,
        "by_state": by_state,
        "by_route": by_route,
        "by_project": by_project,
    }


@app.get("/api/admin")
def admin_all(section: str | None = Query(None, description="optional: engine_config|engine_instances|knowledge_base|supervisor_agent|primitives_registry|subagents_registry|skills_registry|analytics|diagnostics")):
    """后台管理总端点。传 ?section=xxx 只返单个模块。"""
    data = mock_admin_data()
    if section:
        if section not in data:
            raise HTTPException(status_code=400, detail=f"unknown section: {section}")
        return {section: data[section]}
    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
