import os
import asyncio
import json
from datetime import datetime
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
REFERRAL_FILE = "referrals.json"
PROMO_INTERVAL = 21600  # авторассылка раз в 6 часов
GROUP_ID = int(os.getenv("GROUP_ID"))

def load_data():
    if os.path.exists(REFERRAL_FILE):
        with open(REFERRAL_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(REFERRAL_FILE, "w") as f:
        json.dump(data, f)

# Приветствие и логика рефералов
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    ref_by = None
    if context.args:
        ref_by = context.args[0]
    for member in update.message.new_chat_members:
        if ref_by and ref_by != str(member.id):
            data.setdefault(ref_by, [])
            if str(member.id) not in data[ref_by]:
                data[ref_by].append(str(member.id))
                save_data(data)
        await update.message.reply_text(
            f"👋 Добро пожаловать, {member.full_name}! "
            "Пригласи друзей, чтобы попасть в топ 📈"
        )

# /start команда с реф-ссылкой
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(
        f"🤝 Вот твоя реферальная ссылка:{link}"
    )

# /mystats — количество приглашённых
async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)
    count = len(data.get(user_id, []))
    await update.message.reply_text(f"📊 Ты пригласил {count} человек(а).")

# /topreferrers — топ 5
async def topreferrers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    top = sorted(data.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    msg = "🏆 Топ пригласивших:"
    for uid, refs in top:
        user = await context.bot.get_chat(uid)
        msg += f"- {user.first_name}: {len(refs)} чел."
    await update.message.reply_text(msg)

# Авторассылка
async def auto_promo(app):
    while True:
        try:
            await app.bot.send_message(
                chat_id=GROUP_ID,
                text="🚀 Напоминаем: приглашайте друзей и растите в рейтинге! 🔥"
            )
        except Exception as e:
            print(f"[!] AutoPromo error: {e}")
        await asyncio.sleep(PROMO_INTERVAL)

# Фильтр спама
async def spam_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if "http://" in message.text or "https://" in message.text or "t.me/" in message.text:
        try:
            await message.delete()
            await message.chat.kick_member(message.from_user.id)
            await message.reply_text(f"🚫 {message.from_user.first_name} был удалён за ссылки.")
        except:
            pass

# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("topreferrers", topreferrers))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), spam_filter))

    app.job_queue.run_repeating(lambda ctx: ctx.bot.send_message(
        chat_id=GROUP_ID,
        text="📣 Пригласи друга и получи место в топе! 🏅"
    ), PROMO_INTERVAL)

    app.run_polling()



from telegram import ReplyKeyboardMarkup

USER_DB = "users.json"
ADMIN_ID = 124522501
user_states = {}

def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, "r") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USER_DB, "w") as f:
        json.dump(data, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["👶 Новичок", "🚛 Овнер"], ["🧠 Диспетчер", "💰 Инвестор"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Привет! Пожалуйста, выбери кто ты:", reply_markup=reply_markup)
    user_states[update.effective_user.id] = {"step": "role"}

async def funnel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text.strip()
    state = user_states.get(user_id, {})

    if state.get("step") == "role" and msg in ["👶 Новичок", "🚛 Овнер", "🧠 Диспетчер", "💰 Инвестор"]:
        user_states[user_id]["role"] = msg
        user_states[user_id]["step"] = "last_name"
        await update.message.reply_text("Введите вашу фамилию:")
    elif state.get("step") == "last_name":
        user_states[user_id]["last_name"] = msg
        user_states[user_id]["step"] = "first_name"
        await update.message.reply_text("Введите ваше имя:")
    elif state.get("step") == "first_name":
        user_states[user_id]["first_name"] = msg
        user_states[user_id]["step"] = "phone"
        await update.message.reply_text("Введите ваш номер телефона или Telegram @юзернейм:")
    elif state.get("step") == "phone":
        user_states[user_id]["phone"] = msg
        # Сохраняем
        users = load_users()
        users[str(user_id)] = user_states[user_id]
        save_users(users)

        # Отправка админу
        data = user_states[user_id]
        msg_admin = (
            f"📥 Новый контакт с воронки:\n\n"
            f"Роль: {data['role']}\n"
            f"Фамилия: {data['last_name']}\n"
            f"Имя: {data['first_name']}\n"
            f"Телефон/контакт: {data['phone']}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg_admin)
        await update.message.reply_text("Спасибо! Ваша информация отправлена.")
        del user_states[user_id]


app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), funnel_handler))
