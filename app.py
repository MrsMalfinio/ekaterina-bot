# app.py — FastAPI веб-сервер для Telegram webhook
import os
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application
from bot import BOT_TOKEN, cmd_start, trigger_start, ask_again_cb, text_router, START_TRIGGERS
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

app = FastAPI()
application: Application | None = None

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret123")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def build_application() -> Application:
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", cmd_start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("(?i)"+START_TRIGGERS), trigger_start))
    telegram_app.add_handler(CallbackQueryHandler(ask_again_cb, pattern=r"^ask_again$"))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    return telegram_app

@app.on_event("startup")
async def on_startup():
    global application
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")
    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL не задан в переменных окружения")

    application = build_application()
    await application.initialize()
    await application.start()
    # Ставим вебхук
    await application.bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)

@app.on_event("shutdown")
async def on_shutdown():
    global application
    if application:
        await application.bot.delete_webhook()
        await application.stop()
        await application.shutdown()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await request.json()
    update = Update.de_json(data, bot=application.bot)  # type: ignore
    await application.process_update(update)            # type: ignore
    return {"ok": True}
