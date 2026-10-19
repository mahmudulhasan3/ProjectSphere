from contextlib import asynccontextmanager
import asyncio

from app.routers import (
    admin,
    auth,
    group,
    message,
    proposal,
    semester,
    settings as settings_router,
    supervisor,
    task,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.scheduler import periodic_notification_check
from app.core.cloudinary_config import configure_cloudinary
from app.routers import (
    thesis,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(periodic_notification_check())
    yield
    scheduler_task.cancel()


configure_cloudinary()
app = FastAPI(title="ProjectSphere API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://projectsphere-frontend.vercel.app",
        "https://projectsphere-frontend-olkxdbe1h-project-sphere.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
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
