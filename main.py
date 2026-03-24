import asyncio
import aiosqlite
import random
import time
import os
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --------- AYARLAR ---------
TOKEN = os.getenv("BOT_TOKEN")  # Railway Secret olarak ekle
CREATOR_ID = 8446478484          # Kurucu ID
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --------- DATABASE SETUP ---------
async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                money INTEGER DEFAULT 1000,
                hp INTEGER DEFAULT 100,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                last_daily INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item TEXT
            )
        """)
        await db.commit()

asyncio.get_event_loop().run_until_complete(init_db())

# --------- KULLANICI FONKSİYONLARI ---------
async def get_user(user_id: int):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"user_id": row[0], "money": row[1], "hp": row[2], "xp": row[3], "level": row[4], "last_daily": row[5]}
            else:
                await db.execute("INSERT INTO users(user_id) VALUES(?)", (user_id,))
                await db.commit()
                return await get_user(user_id)

async def update_user(user_id: int, money=None, hp=None, xp=None, level=None, last_daily=None):
    async with aiosqlite.connect("database.db") as db:
        if money is not None:
            await db.execute("UPDATE users SET money=? WHERE user_id=?", (money, user_id))
        if hp is not None:
            await db.execute("UPDATE users SET hp=? WHERE user_id=?", (hp, user_id))
        if xp is not None:
            await db.execute("UPDATE users SET xp=? WHERE user_id=?", (xp, user_id))
        if level is not None:
            await db.execute("UPDATE users SET level=? WHERE user_id=?", (level, user_id))
        if last_daily is not None:
            await db.execute("UPDATE users SET last_daily=? WHERE user_id=?", (last_daily, user_id))
        await db.commit()

# --------- /start ---------
@dp.message(commands=["start"])
async def start(msg: types.Message):
    text = """
╔════════════════════╗
      💣 MAFIA EMPIRE 💣
╚════════════════════╝

💰 Para kazan, çete kur
🔫 Rakiplerini yok et
🏦 Büyük soygunlar yap

📜 Komutlar:
/profil → Hesabın
/daily → Günlük para
/gorev → Günlük görevler
/soygun → Banka soy
/saldır → Birine saldır
/cete → Çete kur
/market → Eşya al
/envanter → Eşyaların
/rank → Liderlik tablosu
/verpara → Kurucu özel

👑 Developer: @voidsafarov
"""
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Profil", callback_data="profil")],
        [InlineKeyboardButton("Günlük", callback_data="daily")],
        [InlineKeyboardButton("Soygun", callback_data="soygun")],
        [InlineKeyboardButton("Market", callback_data="market")]
    ])
    await msg.answer(text, reply_markup=buttons)

# --------- INLINE BUTTON HANDLER ---------
@dp.callback_query()
async def cb_handler(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    data = cb.data
    user = await get_user(user_id)

    if data == "profil":
        await cb.message.answer(f"💰 Para: {user['money']}\n❤️ Can: {user['hp']}\nXP: {user['xp']}\nLevel: {user['level']}")
    elif data == "daily":
        await handle_daily(cb.message, user)
    elif data == "soygun":
        await handle_soygun(cb.message, user)
    elif data == "market":
        await cb.message.answer("🛒 Market:\n1️⃣ Medkit (200₺)\n2️⃣ Silah (500₺)")

# --------- DAILY BONUS ---------
async def handle_daily(msg, user):
    now = int(time.time())
    if now - user["last_daily"] < 86400:  # 24 saat
        await msg.reply("❌ Günlük hakkını zaten kullandın!")
        return
    bonus = random.randint(500, 1500)
    await update_user(user["user_id"], money=user["money"]+bonus, last_daily=now)
    await msg.reply(f"💵 Günlük bonus alındı: +{bonus}₺")

# --------- SOYGUN ---------
async def handle_soygun(msg, user):
    win = random.choice([True, False])
    if win:
        amount = random.randint(500, 2000)
        await update_user(user["user_id"], money=user["money"]+amount)
        await msg.reply(f"🏦 Soygun başarılı! +{amount}₺")
    else:
        loss = random.randint(100, 500)
        await update_user(user["user_id"], money=max(user["money"]-loss,0))
        await msg.reply(f"🚔 Yakalandın! -{loss}₺")

# --------- /profil ---------
@dp.message(commands=["profil"])
async def profil(msg: types.Message):
    user = await get_user(msg.from_user.id)
    await msg.reply(f"💰 Para: {user['money']}\n❤️ Can: {user['hp']}\nXP: {user['xp']}\nLevel: {user['level']}")

# --------- /daily ---------
@dp.message(commands=["daily"])
async def daily(msg: types.Message):
    user = await get_user(msg.from_user.id)
    await handle_daily(msg, user)

# --------- /verpara (kurucu) ---------
@dp.message(commands=["verpara"])
async def verpara(msg: types.Message):
    if msg.from_user.id != CREATOR_ID:
        await msg.reply("❌ Sadece kurucu kullanabilir!")
        return
    try:
        args = msg.text.split()
        target_id = int(args[1])
        amount = int(args[2])
        target_user = await get_user(target_id)
        await update_user(target_id, money=target_user["money"]+amount)
        await msg.reply(f"✅ {amount}₺ başarıyla verildi!")
    except:
        await msg.reply("❌ Kullanım: /verpara user_id miktar")

# --------- /soygun ---------
@dp.message(commands=["soygun"])
async def soygun_cmd(msg: types.Message):
    user = await get_user(msg.from_user.id)
    await handle_soygun(msg, user)

# --------- RUN ---------
async def main():
    await dp.start_polling(bot)

asyncio.run(main())
