import os
import tempfile
import json
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import concurrent.futures

# Bot token'ınızı buraya ekleyin
TELEGRAM_BOT_TOKEN = 'Bot Tokenimizi Giriyoruz'

# Komik mesajlar listesi
FUNNY_MESSAGES = [
    "🕺 Logları bulduk, şimdi dans etme zamanı! Dans, dans! 💃",
    "☕ Loglar hazır, kahve molası mı veriyoruz? Afiyet olsun! 🍵",
    "🕵️‍♀️ Aradığın log mu? İşte tam karşında, gizli hiçbir şey kalmadı! 🔍",
    "😎 Suçüstü yakalandın! Loglar ele geçirildi bile! 🚨",
    "🏆 Log avcısı günün kahramanı! Bravo sana! 🌟",
    "🌈 VIP Log Hizmeti: Senin için özel olarak hazırlandı! 💎",
    "🕶️ Gizli loglar artık açığa çıktı. Sır kalmadı! 🔓",
    "🎉 Log bulma operasyonu başarılı. Kutlama zamanı! 🎊",
    "🕯️ Loglar senin için özenle depolandı. Dedektiflik mezunu gibisin! 🏅",
    "🍽️ Log ziyafeti hazır! Afiyet olsun, log avcısı! 🍴"
]

# Log bulunamazsa kullanılacak teselli mesajları
NO_LOG_MESSAGES = [
    "🕵️‍♀️ *Şimdilik bulamadık ama merak etme!* \n"
    "🌐 Devasa veritabanımız sürekli güncelleniyor. Birazdan her şey netleşecek! 🔄",
    
    "🔍 *Log avcısı boş durmuyor!* \n"
    "💾 Güncel veritabanımız şu anda yeni veriler için taranıyor. Az sonra bulacağız! 🚀",
    
    "🌈 *Üzülme, her şey yolunda!* \n"
    "🔐 Gizli arşivlerimiz sürekli genişliyor. Bugün olmazsa yarın mutlaka bulacağız! 📊",
    
    "🕰️ *Zamana bırak!* \n"
    "🌍 Global log ağımız kesintisiz olarak veri topluyor. Şimdilik görünmez ama yakında her şey netleşecek! 🌐",
    
    "🤖 *Yapay zeka destekli log arama sistemimiz çalışıyor!* \n"
    "🔬 Detaylı tarama ve sürekli güncelleme modundayız. Az kaldı! 💡",
    
    "🔒 *Gizli bilgi deposu hazırlanıyor!* \n"
    "📡 Veritabanımız sürekli besleniyor, güncellemeler devam ediyor. Sabret! 🌟",
    
    "💡 *Henüz değil ama çok yakında!* \n"
    "🌐 Dünya çapındaki log ağımız her saniye genişliyor. İnan ki bulacağız! 🕵️‍♀️",
    
    "🚦 *Şu an için yeşil ışık yanmadı ama...* \n"
    "🔄 Dinamik veritabanımız sürekli güncelleme halinde. Umudunu kaybetme! 📈",
    
    "🌠 *Her bulunamayan log, yeni bir fırsattır!* \n"
    "🔍 Geniş arşivlerimiz her geçen saniye büyüyor. Bekle ve gör! 🌐",
    
    "🛡️ *Gizlilik ve güncellik bizim işimiz!* \n"
    "💽 Veritabanımız sürekli genişliyor, yeni bilgiler geliyor. Henüz değil ama çok yakında! 🚀"
]

# Premium kullanıcıların ID'leri ve abonelik bitiş tarihleri
premium_users = {}  # {user_id: expiration_date}

# Gösterilen logları takip etmek için bir sözlük
shown_logs = {}

# Kullanıcı sorgulama haklarını takip eden sözlük
user_search_limits = {}  # {user_id: remaining_attempts}

# Kullanıcılara verilen maksimum sorgulama hakkı
MAX_SEARCH_ATTEMPTS = 3

# Premium kullanıcıları kontrol eden işlev
def check_premium_users():
    current_time = datetime.now()
    expired_users = [user_id for user_id, expiry in premium_users.items() if current_time > expiry]
    for user_id in expired_users:
        del premium_users[user_id]

# Belirli bir anahtar kelimeye göre txt dosyalarını tarayan işlev
async def find_logs(keyword):
    logs = []
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            tasks = [
                loop.run_in_executor(executor, search_in_file, filename, keyword)
                for filename in os.listdir('.')
                if filename.endswith('.txt')
            ]
            results = await asyncio.gather(*tasks)
            for result in results:
                logs.extend(result)
    except Exception as e:
        print(f"find_logs sırasında hata: {str(e)}")
    return logs

def search_in_file(filename, keyword):
    logs = []
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                if keyword in line:
                    logs.append(line.strip())
    except UnicodeDecodeError:
        try:
            with open(filename, 'r', encoding='latin-1') as file:
                for line in file:
                    if keyword in line:
                        logs.append(line.strip())
        except Exception as e:
            print(f"{filename} dosyası okunurken hata oluştu: {str(e)}")
            return []

    return logs

# /start komutunu işleyen işlev
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    check_premium_users()
    user_id = update.message.from_user.id
    
    # Kullanıcının premium olup olmadığını kontrol et
    if user_id not in premium_users:
        # Kullanıcının daha önce başlatılıp başlatılmadığını kontrol edin
        if user_id not in user_search_limits:
            user_search_limits[user_id] = MAX_SEARCH_ATTEMPTS

        # Kullanıcının sorgulama haklarını kontrol edin
        if user_search_limits[user_id] <= 0:
            await update.message.reply_text(
                "🚫 *Üzgünüz!* Sorgulama hakkınız tükendi. \n\n"
                "💡 Yeni bir paket satın almak için @Bytncpx ile iletişime geçin. \n"
                "📞 Destek hattımız her zaman sizin için hazır! 🌟"
            )
            return
    
    welcome_message = (
        "🤖 *Log Tarama Botuna Hoş Geldiniz!* 🔍\n\n"
        "📜 Ben, gizli logları bulma konusunda uzmanlaşmış bir botum.\n"
        "✨ Belirli bir anahtar kelimeyi kullanarak log dosyalarını tarayabilirim.\n\n"
        "🎯 *Nasıl Kullanılır?*\n"
        "• Komut: `/log [anahtar kelime]`\n"
        "• *Örnek:* `/log netflix`\n\n"
        "🚀 Hemen aramaya başlayın ve logların sırlarını keşfedin! 🕵️‍♀️"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

# /log komutunu işleyen işlev
async def log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    check_premium_users()
    user_id = update.message.from_user.id
    
    # Kullanıcının premium olup olmadığını kontrol edin
    if user_id not in premium_users:
        if user_id not in user_search_limits:
            user_search_limits[user_id] = MAX_SEARCH_ATTEMPTS
        
        # Sorgulama hakkı kalmadıysa engelle
        if user_search_limits[user_id] <= 0:
            await update.message.reply_text(
                "🚫 *Sorgulama Hakkı Tükendi!* 🔒\n\n"
                "💡 Yeni bir paket satın almak için @Bytncpx ile iletişime geçin.\n"
                "📞 Destek ekibimiz yardımcı olmaya hazır! 🌈"
            )
            return

        # Kullanıcının sorgulama hakkını azalt
        user_search_limits[user_id] -= 1
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ *Eksik Parametre!* \n\n"
            "🔍 Lütfen bir *anahtar kelime* belirtin. \n"
            "📝 *Örnek:* `/log udemy`"
        )
        return

    keyword = context.args[0]
    chat_id = update.message.chat_id

    # Kullanıcıya işlemin başladığını belirten mesaj
    processing_message = await update.message.reply_text(
        f"🔬 *{keyword}* için loglar taranıyor... \n"
        "⏳ Lütfen sabırla bekleyin. Gizli bilgiler çıkarılıyor! 🕵️‍♀️"
    )

    try:
        # İşlem süresini belirlemek için zaman hesaplama
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)  # Örneğin, 30 saniye işlem süresi

        while datetime.now() < end_time:
            remaining_time = end_time - datetime.now()
            minutes, seconds = divmod(remaining_time.seconds, 60)
            await processing_message.edit_text(
                f"🔍 *{keyword}* için loglar taranıyor... \n"
                f"⏳ Kalan süre: {minutes} dakika {seconds} saniye \n"
                "🕰️ Birazdan sonuçları görüntüleyeceksiniz! 🌟"
            )
            await asyncio.sleep(5)  # Her 5 saniyede bir güncelle

        logs = await find_logs(keyword)

        # Daha önce gösterilen logları filtrele
        if chat_id in shown_logs:
            logs = [log for log in logs if log not in shown_logs[chat_id]]
        else:
            shown_logs[chat_id] = []

        if logs:
            # Her log satırının başına ve dosyanın başına reklam metnini ekle
            header = "📋 *Bytncpx Log Servisi* 🔐\n"
            logs = [f"📍 {log}" for log in logs]

            # Logları geçici bir dosyaya yaz
            with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
                temp_file.write(header + '\n'.join(logs))
                temp_file_path = temp_file.name
            
            # Gösterilen logları kaydet
            shown_logs[chat_id].extend(logs)

            # Dosyayı Telegram'a gönder
            await update.message.reply_document(
                document=open(temp_file_path, 'rb'),
                filename='logs.txt',
                caption="🎉 *Log Dosyanız Hazır!* 📂\n*İncelemek için tıklayın.* 🔍"
            )
            
            # Rastgele komik mesaj gönder
            funny_message = random.choice(FUNNY_MESSAGES)
            await update.message.reply_text(funny_message)
        else:
            # Log bulunamazsa rastgele teselli mesajı gönder
            no_log_message = random.choice(NO_LOG_MESSAGES)
            await update.message.reply_text(no_log_message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Hata Oluştu!* \n\n"
            f"🛠️ İşlem sırasında bir sorun meydana geldi: \n"
            f"*{str(e)}*\n"
            "📞 Destek ekibimize bildirebilirsiniz. 🆘"
        )
    finally:
        # İşlemin tamamlandığını belirten mesaj
        await processing_message.edit_text(
            "✅ *İşlem Tamamlandı!* \n"
            "🎊 Log tarama başarıyla sonuçlandırıldı. 🌟"
        )

# /add_premium komutunu işleyen işlev
async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ *Eksik Bilgi!* \n\n"
            "🆔 Lütfen bir kullanıcı ID'si belirtin. \n"
            "*Örnek:* `/add_premium 123456789`"
        )
        return

    try:
        user_id = int(context.args[0])
        expiration_date = datetime.now() + timedelta(days=30)
        premium_users[user_id] = expiration_date
        # Kullanıcının arama haklarını sınırsız yap
        user_search_limits[user_id] = float('inf')
        await update.message.reply_text(
            f"🏆 *Premium Kullanıcı Eklendi!* \n\n"
            f"🆔 Kullanıcı {user_id} artık *premium* statüsünde. \n"
            "🎉 Tüm özelliklerin keyfini çıkarın! 🌟"
        )
    except ValueError:
        await update.message.reply_text(
            "❌ *Geçersiz Kullanıcı ID'si!* \n\n"
            "🔢 Lütfen geçerli bir sayısal ID girin. \n"
            "📞 Sorun yaşamaya devam ederseniz destek alın. 🆘"
        )

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("log", log))
    app.add_handler(CommandHandler("add_premium", add_premium))

    app.run_polling()

if __name__ == '__main__':
    main()
