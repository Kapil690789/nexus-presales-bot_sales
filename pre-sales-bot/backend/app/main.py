from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api import admin, documents, health, public_config, sessions
from backend.app.core.security import assert_admin_configured
from backend.app.core.settings import ROOT, get_settings, uploads_root
from backend.app.models.db import SessionLocal, init_db
from backend.app.rag.embeddings import embedding_backend
from backend.app.rag.ingest import ingest_all

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    settings = get_settings()
    try:
        uploads_root().mkdir(parents=True, exist_ok=True)
        init_db()
        with SessionLocal() as db:
            ingest_all(db)
    except Exception:
        log.exception("Startup index failed")
    if embedding_backend() == "hash":
        log.warning("Using the local hash embedder. Install sentence-transformers for BAAI/bge-small-en-v1.5.")
    if not settings.llm_api_key.strip():
        log.warning("LLM_API_KEY is empty. Answers stay grounded in retrieved notes without generation.")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    assert_admin_configured(settings)
    application = FastAPI(title="Pre-Sales Consultant", version="1.0.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(public_config.router)
    application.include_router(sessions.router)
    application.include_router(documents.router)
    application.include_router(admin.router)
    widget_dir = ROOT / "widget"
    public_dir = ROOT / "public"
    if widget_dir.is_dir():
        application.mount("/widget", StaticFiles(directory=widget_dir), name="widget")
    if public_dir.is_dir():
        application.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
    return application


app = create_app()
