import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import action_items, analytics, ask, health, meetings
from app.config import get_settings
from app.db import SessionLocal
from app.observability import configure_logging
from app.pipeline.pipeline import fail_stranded_meetings

configure_logging()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # A meeting left mid-pipeline by a previous crash/restart would otherwise be stuck
    # in a processing state forever. Mark any such meetings failed at startup.
    async with SessionLocal() as session:
        recovered = await fail_stranded_meetings(session)
    if recovered:
        logger.warning("recovered %d stranded meeting(s) on startup", recovered)
    yield


app = FastAPI(title="Meeting Intelligence Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

for module in (health, meetings, action_items, ask, analytics):
    app.include_router(module.router)
