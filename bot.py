# -*- coding: utf-8 -*-
# Требования: python-telegram-bot==21.4

import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ========= НАСТРОЙКИ =========
BOT_TOKEN = os.getenv("BOT_TOKEN")   # теперь берётся из переменных окружения
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # тоже из окружения

STATE_ASK_Q = "ask_question"
STATE_ASK_DOB = "ask_dob"

DOB_RE = re.compile(r"^(0?[1-9]|[12][0-9]|3[01])\.(0?[1-9]|1[0-2])\.(\d{4})$")
START_TRIGGERS = r"(\+|старт|начать|привет|задать\s+вопрос|написать\s+вопрос|спросить)"

ASK_AGAIN_KB = InlineKeyboardMarkup(
    [[InlineKeyboardButton("➕ Задать ещё вопрос", callback_data="ask_again")]]
)

# ========= ТЕКСТЫ =========
WELCOME_TEXT = (
    "<b>✨ Приветствую тебя</b> \n\n"
    "Здесь ты можешь задать любой вопрос. О себе, о переживаниях, о страхах или о том, что давно не даёт покоя.\n"
    "<b>Важно:</b> ❗️вопрос полностью анонимный. Даже я не увижу, от кого он пришёл.\n\n"
    "Пиши то, что действительно волнует. Иногда достаточно озвучить, и становится легче.\n"
    "А я разберу твой вопрос, и дам ответ в канале, чтобы каждая смогла найти отклик для себя.\n\n"
    "<b>🤍 Ты в безопасности. Здесь можно быть настоящей.</b>\n"
)

ASK_AGAIN_TEXT = "Если тебя снова что-то волнует, задай свой вопрос, я разберу его и дам тебе ответы"

ASK_DOB_PROMPT = (
    "Чтобы ответ был максимально точным и полезным, мне важно учитывать твою дату рождения.\n"
    "Это поможет взглянуть через призму нумерологии и понять твой вопрос глубже.\n\n"
    "📌 <b>Напиши, пожалуйста, свою дату рождения в формате: дд.мм.гггг</b>\n\n"
    "<b>Не переживай, всё так же полностью анонимно.</b> Никто не узнает, от кого пришёл вопрос, даже я 🤍"
)

THANK_YOU_TEXT = (
    "<b>Спасибо тебе за доверие и за этот вопрос 🙏</b>\n"
    "Совсем скоро я сделаю разбор и поделюсь им в канале.\n\n"
    "<b>Чтобы не пропустить разбор твоего вопроса, включи уведомления и будь рядом 🤍</b>"
)

# ========= ЛОГИКА =========
async def _start_flow(chat, context: ContextTypes.DEFAULT_TYPE, welcome: bool):
    context.user_data.clear()
    if welcome:
        await chat.reply_text(WELCOME_TEXT, parse_mode=ParseMode.HTML)
    context.user_data["state"] = STATE_ASK_Q

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _start_flow(update.message, context, welcome=True)

async def trigger_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _start_flow(update.message, context, welcome=True)

async def ask_again_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.message.reply_text(ASK_AGAIN_TEXT)
    context.user_data["state"] = STATE_ASK_Q

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    state = context.user_data.get("state")

    if state is None:
        if re.search(START_TRIGGERS, text, flags=re.IGNORECASE):
            return await _start_flow(update.message, context, welcome=True)
        return await update.message.reply_text("Напиши «старт» или нажми «Задать ещё вопрос», чтобы начать.")

    if state == STATE_ASK_Q:
        context.user_data["question"] = text
        context.user_data["state"] = STATE_ASK_DOB
        return await update.message.reply_text(ASK_DOB_PROMPT, parse_mode=ParseMode.HTML)

    if state == STATE_ASK_DOB:
        if not DOB_RE.match(text):
            return await update.message.reply_text("Формат даты: дд.мм.гггг (например, 17.09.1993)")

        question = context.user_data.get("question", "").strip()

        # сообщение Екатерине
        admin_msg = (
            "📝 Новый анонимный вопрос\n\n"
            f"📌 Вопрос: {question}\n"
            f"📅 Дата рождения: {text}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        except Exception as e:
            print("Не удалось отправить сообщение администратору:", e)

        # благодарность + КНОПКА
        await update.message.reply_text(
            THANK_YOU_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=ASK_AGAIN_KB
        )
        context.user_data.clear()
        return

    context.user_data.clear()
    await update.message.reply_text("Давай начнём сначала. Напиши «старт».")
    return

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("(?i)"+START_TRIGGERS), trigger_start))
    app.add_handler(CallbackQueryHandler(ask_again_cb, pattern=r"^ask_again$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
