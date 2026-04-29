from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from campaign.api.routes import (
    campaigns,
    dashboard,
    health,
    inbox,
    personas,
    send,
    settings,
)
from campaign.config import get_settings
from campaign.logging import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("app.startup", env=get_settings().env, demo_mode=get_settings().campaign_demo_mode)
    yield
    log.info("app.shutdown")


app = FastAPI(title="Campaign v2 — B2B Outreach Agent", version="0.2.0", lifespan=lifespan)

dashboard.mount_static(app)

app.include_router(health.router)
app.include_router(personas.router)
app.include_router(settings.router)
app.include_router(campaigns.router)
app.include_router(inbox.router)
app.include_router(send.router)
app.include_router(dashboard.router)
