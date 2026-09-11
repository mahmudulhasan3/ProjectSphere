from contextlib import asynccontextmanager
import asyncio

from backend.app.routers import admin, auth, group, message, proposal, semester, settings as settings_router, supervisor, task
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.scheduler import periodic_notification_check

from backend.app.routers import (
    thesis,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(periodic_notification_check())
    yield
    scheduler_task.cancel()


app = FastAPI(title="ProjectSphere API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(group.router)
app.include_router(supervisor.router)
app.include_router(proposal.router)
app.include_router(task.router)
app.include_router(thesis.router)
app.include_router(message.router)
app.include_router(semester.router)
app.include_router(settings_router.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "ProjectSphere API"}
