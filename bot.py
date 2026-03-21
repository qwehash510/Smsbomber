mport requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

TOKEN = '8712193355:AAE8TAr0hAoGDo9HiABpVG6zp-x9eBbvfns'
API_URL = 'https://cvron.alwaysdata.net/cvronapi/sms-bomb.php'

# Conversation states
PHONE, COUNT, CONFIRM = range(3)

async def sms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Başla", callback_data='sms')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Merhaba! SMS botuna hoş geldiniz.\n"
        "SMS göndermek için başlayın.",
        reply_markup=reply_markup
    )
    return PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Telefon numarasını girin (örneğin: 5xxxxxxxxx):")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("Adet sayısını girin (örneğin: 50):")
    return COUNT

async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text)
        context.user_data['count'] = count
        keyboard = [
            [InlineKeyboardButton("Evet", callback_data='confirm_yes')],
            [InlineKeyboardButton("Hayır", callback_data='confirm_no')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Telefon: {context.user_data['phone']}\nAdet: {count}\nOnaylıyor musunuz?",
            reply_markup=reply_markup
        )
        return CONFIRM
    except ValueError:
        await update.message.reply_text("Geçersiz sayı. Lütfen tekrar girin.")
        return COUNT

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'confirm_yes':
        phone = context.user_data['phone']
        count = context.user_data['count']
        url = f"{API_URL}?phone={phone}&count={count}"
        response = requests.get(url)
        if response.status_code == 200:
            await query.edit_message_text("SMS gönderimi başlatıldı.")
        else:
            await query.edit_message_text("Hata oluştu.")
    else:
        await query.edit_message_text("İşlem iptal edildi. /sms ile tekrar başlayın.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("İşlem iptal edildi.")
    return ConversationHandler.END

app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("sms", sms)],
    states={
        PHONE: [CallbackQueryHandler(ask_phone, pattern='^sms$'), MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_count)],
        CONFIRM: [CallbackQueryHandler(confirm, pattern='^(confirm_yes|confirm_no)$')],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)
app.run_polling()
