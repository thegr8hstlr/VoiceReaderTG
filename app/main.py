from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router as routes_router
from app.api.vapi_webhook import router as webhook_router
from app.bot.runner import start_polling, stop_polling

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

_bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_app
    _bot_app = await start_polling()
    yield
    if _bot_app:
        await stop_polling(_bot_app)


app = FastAPI(title="VoiceReaderTG", lifespan=lifespan)
app.include_router(routes_router)
app.include_router(webhook_router)
