from __future__ import annotations

import logging

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from app.bot.handlers import handle_document, handle_message, start_command
from app.config import settings

logger = logging.getLogger(__name__)


def create_bot_app():
    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    return app


async def start_polling():
    app = create_bot_app()
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot started polling")
    return app


async def stop_polling(app):
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("Telegram bot stopped")
