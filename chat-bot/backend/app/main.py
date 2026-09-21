from contextlib import asynccontextmanager
from pathlib import Path
import logging
import os

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


@asynccontextmanager
async def lifespan(_application: FastAPI):
    init_db()
    ingest_on_startup()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    assert_admin_configured(settings)
    get_config()
    if not llm_available():
        log.warning("LLM_API_KEY is not set; using the offline fallback consultant.")
    application = FastAPI(title="DevConsult Pre-Sales Consultant", version="1.0.0", lifespan=lifespan)
    origins = settings.cors_origin_list
    cors_kwargs: dict = {
        "allow_origins": origins if origins != ["*"] else ["*"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    regex = settings.cors_origin_regex.strip()
    if regex:
        cors_kwargs["allow_origin_regex"] = regex
    application.add_middleware(CORSMiddleware, **cors_kwargs)
    application.include_router(health.router)
    application.include_router(public_config.router)
    application.include_router(sessions.router)
    application.include_router(documents.router)
    application.include_router(admin.router)

    widget_dir = ROOT / "widget" / "dist"
    public_dir = ROOT / "public"
    if widget_dir.exists():
        application.mount("/widget", StaticFiles(directory=widget_dir), name="widget")
    if public_dir.exists() and not os.environ.get("VERCEL"):
        application.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
    return application


app = create_app()
