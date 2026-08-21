from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import apply_migrations, sync_canonical_ingredients
from app.routes import auth, health, pantry


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_migrations()
    sync_canonical_ingredients()
    yield


app = FastAPI(title="Kitchen", lifespan=lifespan)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(pantry.router)

static_dir = Path(settings.static_dir)
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
