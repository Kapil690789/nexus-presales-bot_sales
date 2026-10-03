from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api import admin, documents, health, public_config, sessions
from backend.app.core.security import assert_admin_configured, is_admin_misconfigured
from backend.app.core.settings import ROOT, get_settings, uploads_root
from backend.app.models.db import SessionLocal, init_db
from backend.app.rag.embeddings import embedding_backend
from backend.app.rag.ingest import ingest_all

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    try:
        settings = get_settings()
        # Indexing and database setup stay off the Vercel cold start. The first
        # database request runs them, so a hung database cannot fail every route.
        if not os.environ.get("VERCEL"):
            uploads_root().mkdir(parents=True, exist_ok=True)
            init_db()
            with SessionLocal() as db:
                ingest_all(db)
        if embedding_backend() == "hash" and not os.environ.get("VERCEL"):
            log.warning("Using the local hash embedder. Install sentence-transformers for BAAI/bge-small-en-v1.5.")
        if not settings.llm_api_key.strip():
            log.warning("LLM_API_KEY is empty. Answers stay grounded in retrieved notes without generation.")
    except Exception:
        log.exception("Startup failed")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    admin_misconfigured = is_admin_misconfigured(settings)
    if admin_misconfigured:
        log.error(
            "Production environment has missing or default admin password. Admin router disabled."
        )
    else:
        try:
            assert_admin_configured(settings)
        except RuntimeError:
            log.warning(
                "Admin password is missing or a default value. The app will still serve. Set a unique ADMIN_PASSWORD."
            )
    application = FastAPI(title="Pre-Sales Consultant", version="1.0.0", lifespan=lifespan)
    if "*" in settings.cors_origin_list:
        if settings.is_production_like:
            raise ValueError(
                "Wildcard CORS origin '*' with allow_credentials=True is unsafe and not allowed in production."
            )
        log.warning("Wildcard CORS origin '*' with allow_credentials=True is insecure.")

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
    if not admin_misconfigured:
        application.include_router(admin.router)
    # Vercel serves public/ from the CDN, including public/widget/consultant.js.
    # Mounting those directories here keeps them inside the function because of CORS.
    if not os.environ.get("VERCEL"):
        widget_dir = ROOT / "widget"
        public_dir = ROOT / "public"
        if widget_dir.is_dir():
            application.mount("/widget", StaticFiles(directory=widget_dir), name="widget")
        if public_dir.is_dir():
            application.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
    return application


app = create_app()
