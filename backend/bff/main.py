from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.bff.config import settings
from backend.bff.routes import health, trim_profile

app = FastAPI(
    title="HarnessFlow BFF",
    version=settings.bff_version,
    description="Backend-for-Frontend for the Human-Agent Collaboration UI (BC-10)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[settings.pid_header_name],
)

app.include_router(health.router, prefix="/api")
app.include_router(trim_profile.router, prefix="/api")
