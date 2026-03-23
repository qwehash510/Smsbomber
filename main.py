import telebot
import sqlite3
import random
from datetime import datetime, timedelta

bot = telebot.TeleBot("8512730251:AAEjDTJS3LOEpFHEfyUUB0p42ZJKWywlqP4")
conn = sqlite3.connect("kumar.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER, last_daily TIMESTAMP)")
conn.commit()

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        cursor.execute("INSERT INTO users (user_id, balance, last_daily) VALUES (?, ?, ?)", (user_id, 0, 0))
        conn.commit()
        return 0

def update_balance(user_id, amount):
    current_balance = get_balance(user_id)
    new_balance = current_balance + amount
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    return new_balance

def find_user(chat_id, target, reply_to_message=None):
    if reply_to_message and reply_to_message.from_user:
        return reply_to_message.from_user
    target = target.lstrip("@").lower()
    try:
        members = bot.get_chat_administrators(chat_id) + bot.get_chat_members(chat_id)
        for member in members:
            user = member.user
            if (user.username and user.username.lower() == target) or \
               (user.first_name and user.first_name.lower() == target) or \
               (f"@{user.username.lower()}" == target if user.username else False):
                return user
    except:
        pass
    return None

@bot.message_handler(commands=["start"])
def start(message):
    user = message.from_user.username or message.from_user.first_name
    bot.reply_to(message, f"""
✨ Kumar botuna hoşgeldin, {user} ✨

Bu botta kafa dağıtmak için şansın ile kumar oynayabilirsin.
- Komutlar şunlardır:
  🎰 /risk <miktar> veya /risk all - %50 şansla bahsinizi katlayın!
  🎲 /zar <miktar> - Zar at, 5 veya 6 gelirse 2x kazan!
  🎰 /slot <miktar> - Slot çek, üç aynı sembol 3x kazandırır!
  🏛 /bakiye - Bakiyenizi görün.
  💸 /gonder <@kullanıcı> <miktar> - Başkasına para gönderin.
  🪙 /gunluk - Her 24 saatte 100.000TL alın.
  👑 /bakiyever <@kullanıcı> <miktar> - Adminler için bakiye ekleme.
  🤑 /zenginler - En zengin oyuncuları görün.

👑 Developer - Coder: @darmadaginim
""")

@bot.message_handler(commands=["bakiye"])
def bakiye(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    bot.reply_to(message, f"🏛 Bakiyeniz: {balance}TL")

@bot.message_handler(commands=["bakiyever"])
def bakiyever(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "❌ Sadece adminler bu komutu kullanabilir!")
        return
    try:
        parts = message.text.split()
        reply = message.reply_to_message
        if len(parts) != 3 and not reply:
            bot.reply_to(message, "⚠️ Kullanım: /bakiyever kullanıcı İD miktar veya bir mesajı yanıtlayın!")
            return
        if reply:
            target_user = find_user(chat_id, "", reply)
            amount = int(parts[1]) if len(parts) > 1 else None
        else:
            target_user = find_user(chat_id, parts[1])
            amount = int(parts[2])
        if not target_user:
            bot.reply_to(message, "⚠️ Kullanıcı bulunamadı! kullanıcı ID veya kişinin mesajını yanıtlayın.")
            return
        if not amount or amount <= 0:
            bot.reply_to(message, "⚠️ Geçerli bir miktar girin!")
            return
        new_balance = update_balance(target_user.id, amount)
        bot.reply_to(message, f"✅ @{target_user.username or target_user.first_name} kişisine {amount}TL gönderildi.\nGüncel bakiyesi: {new_balance}TL")
    except ValueError:
        bot.reply_to(message, "⚠️ Geçerli bir miktar girin!")
    except:
        bot.reply_to(message, "⚠️ Hata! Doğru formatta yazın veya bir mesajı yanıtlayın.")

@bot.message_handler(commands=["risk"])
def risk(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "⚠️ Kullanım: /risk miktar veya /risk all")
            return
        amount = parts[1].lower()
        if amount == "all":
            amount = balance
        else:
            amount = int(amount)
        if amount <= 0 or amount > balance:
            bot.reply_to(message, "⚠️ Yeterli bakiyeniz yok veya geçersiz miktar!")
            return
        if random.random() < 0.5:
            new_balance = update_balance(user_id, amount)
            bot.reply_to(message, f"🎉 Tebrikler, {amount}TL kazandınız!\nGüncel bakiyeniz: {new_balance}TL")
        else:
            new_balance = update_balance(user_id, -amount)
            bot.reply_to(message, f"😭 Üzgünüz, {amount}TL kaybettiniz.\nGüncel bakiyeniz: {new_balance}TL")
    except ValueError:
        bot.reply_to(message, "⚠️ Geçerli bir miktar girin: /risk miktar veya /risk all")
    except:
        bot.reply_to(message, "⚠️ Hata oluştu! Tekrar deneyin.")

@bot.message_handler(commands=["zar"])
def zar(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "⚠️ Kullanım: /zar miktar")
            return
        amount = int(parts[1])
        if amount <= 0 or amount > balance:
            bot.reply_to(message, "⚠️ Yeterli bakiyeniz yok veya geçersiz miktar!")
            return
        roll = random.randint(1, 6)
        if roll >= 5:
            win = amount * 2
            new_balance = update_balance(user_id, win)
            bot.reply_to(message, f"🎲 Zar: {roll}! Tebrikler, {win}TL kazandınız!\nGüncel bakiyeniz: {new_balance}TL")
        else:
            new_balance = update_balance(user_id, -amount)
            bot.reply_to(message, f"🎲 Zar: {roll}. Üzgünüz, {amount}TL kaybettiniz.\nGüncel bakiyeniz: {new_balance}TL")
    except ValueError:
        bot.reply_to(message, "⚠️ Geçerli bir miktar girin: /zar miktar")
    except:
        bot.reply_to(message, "⚠️ Hata oluştu! Tekrar deneyin.")

@bot.message_handler(commands=["slot"])
def slot(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "⚠️ Kullanım: /slot miktar")
            return
        amount = int(parts[1])
        if amount <= 0 or amount > balance:
            bot.reply_to(message, "⚠️ Yeterli bakiyeniz yok veya geçersiz miktar!")
            return
        symbols = ["🍎", "🍊", "🍒", "💎"]
        result = [random.choice(symbols) for _ in range(3)]
        if result[0] == result[1] == result[2]:
            win = amount * 3
            new_balance = update_balance(user_id, win)
            bot.reply_to(message, f"🎰 {result[0]} {result[1]} {result[2]} Jackpot! {win}TL kazandınız!\nGüncel bakiyeniz: {new_balance}TL")
        else:
            new_balance = update_balance(user_id, -amount)
            bot.reply_to(message, f"🎰 {result[0]} {result[1]} {result[2]} Üzgünüz, {amount}TL kaybettiniz.\nGüncel bakiyeniz: {new_balance}TL")
    except ValueError:
        bot.reply_to(message, "⚠️ Geçerli bir miktar girin: /slot miktar")
    except:
        bot.reply_to(message, "⚠️ Hata oluştu! Tekrar deneyin.")

@bot.message_handler(commands=["gonder"])
def gonder(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    try:
        parts = message.text.split()
        reply = message.reply_to_message
        if len(parts) != 3 and not reply:
            bot.reply_to(message, "⚠️ Kullanım: /gonder @kullanıcı miktar veya bir mesajı yanıtlayın!")
            return
        if reply:
            target_user = find_user(message.chat.id, "", reply)
            amount = int(parts[1]) if len(parts) > 1 else None
        else:
            target_user = find_user(message.chat.id, parts[1])
            amount = int(parts[2])
        if not target_user:
            bot.reply_to(message, "⚠️ Kullanıcı bulunamadı! @kullanıcı, kullanıcı adı veya görünen isim kullanın.")
            return
        if not amount or amount <= 0 or amount > balance:
            bot.reply_to(message, "⚠️ Geçerli bir miktar girin veya bakiyeniz yetersiz!")
            return
        if target_user.id == user_id:
            bot.reply_to(message, "❌ Kendinize para gönderemezsiniz!")
            return
        update_balance(user_id, -amount)
        new_balance_target = update_balance(target_user.id, amount)
        bot.reply_to(message, f"💸 @{target_user.username or target_user.first_name} kişisine {amount}TL gönderildi!\nOnun bakiyesi: {new_balance_target}TL\nSenin bakiyen: {get_balance(user_id)}TL")
    except ValueError:
        bot.reply_to(message, "⚠️ Geçerli bir miktar girin!")
    except:
        bot.reply_to(message, "⚠️ Hata! Doğru formatta yazın veya bir mesajı yanıtlayın.")

@bot.message_handler(commands=["gunluk"])
def gunluk(message):
    user_id = message.from_user.id
    cursor.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    now = datetime.now()
    if result and result[0]:
        last_daily = datetime.fromtimestamp(result[0])
        if now - last_daily < timedelta(hours=24):
            remaining = (last_daily + timedelta(hours=24)) - now
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes = remainder // 60
            bot.reply_to(message, f"⏳ Günlük ödül için {hours}s {minutes}dk beklemelisin!")
            return
    new_balance = update_balance(user_id, 100000)
    cursor.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (now.timestamp(), user_id))
    conn.commit()
    bot.reply_to(message, f"🪙 Günlük ödül alındı! 100.000TL eklendi.\nGüncel bakiyeniz: {new_balance}TL")

@bot.message_handler(commands=["zenginler"])
def zenginler(message):
    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")
    results = cursor.fetchall()
    if not results:
        bot.reply_to(message, "🤑 Henüz kimse bakiye kazanmamış!")
        return
    response = "🏆 En Zengin Oyuncular 🏆\n\n"
    for i, (user_id, balance) in enumerate(results, 1):
        try:
            user = bot.get_chat_member(message.chat.id, user_id).user
            username = user.username or user.first_name
            response += f"{i}. 🥇 @{username}: {balance}TL\n" if i == 1 else f"{i}. 🥈 @{username}: {balance}TL\n" if i == 2 else f"{i}. 🥉 @{username}: {balance}TL\n" if i == 3 else f"{i}. 💰 @{username}: {balance}TL\n"
        except:
            continue
    bot.reply_to(message, response)

bot.polling()
