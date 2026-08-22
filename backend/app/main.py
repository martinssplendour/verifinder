import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.services.operations import scheduler_loop


settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop = asyncio.Event()
    task = asyncio.create_task(scheduler_loop(stop)) if settings.scheduler_enabled else None
    try:
        yield
    finally:
        stop.set()
        if task:
            await task


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Provenance-first public-data API for VeriFinder.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.get("/")
async def root() -> dict:
    return {"name": "VeriFinder API", "docs": "/docs", "health": "/api/health"}
