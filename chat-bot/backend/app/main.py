from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api import admin, documents, health, public_config, sessions
from backend.app.config_loader.loader import get_config
from backend.app.core.llm import llm_available
from backend.app.core.security import assert_admin_configured
from backend.app.core.settings import ROOT, get_settings
from backend.app.models.db import init_db
from backend.app.rag.ingest import ingest_on_startup

settings = get_settings()
log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    assert_admin_configured(settings)
    get_config()
    init_db()
    ingest_on_startup()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    if not llm_available():
        log.warning("LLM_API_KEY is not set; using the offline fallback consultant.")
    application = FastAPI(title="DevConsult Pre-Sales Consultant", version="1.0.0")
    origins = settings.cors_origin_list
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(public_config.router)
    application.include_router(sessions.router)
    application.include_router(documents.router)
    application.include_router(admin.router)

    widget_dir = ROOT / "widget" / "dist"
    public_dir = ROOT / "public"
    if widget_dir.exists():
        application.mount("/widget", StaticFiles(directory=widget_dir), name="widget")
    if public_dir.exists():
        application.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
    return application


app = create_app()
