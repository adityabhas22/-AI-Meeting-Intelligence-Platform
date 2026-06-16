from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import action_items, analytics, ask, health, meetings
from app.config import get_settings

app = FastAPI(title="Meeting Intelligence Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

for module in (health, meetings, action_items, ask, analytics):
    app.include_router(module.router)
