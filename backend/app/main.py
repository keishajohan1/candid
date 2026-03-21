from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.core.config import log_env_debug_status, settings
from app.core.logging import configure_logging

configure_logging(settings.log_level)
log_env_debug_status()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Candid backend API for neutral educational chat experiences.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(chat_router, prefix=settings.api_prefix, tags=["chat"])
app.include_router(ingest_router, prefix=settings.api_prefix, tags=["ingest"])
