import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import apply_migrations, sync_canonical_ingredients
from app.jobs import worker_loop
from app.routes import auth, health, pantry, profile, shopping, suggest


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_migrations()
    sync_canonical_ingredients()

    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(worker_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await worker_task


app = FastAPI(title="Kitchen", lifespan=lifespan)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(pantry.router)
app.include_router(suggest.router)
app.include_router(shopping.router)
app.include_router(profile.router)

static_dir = Path(settings.static_dir)
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
