import os
import asyncio
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_ID = [124522501, 7510196452]
USER_DB = "users.json"
REFERRAL_FILE = "referrals.json"
PROMO_INTERVAL = 21600
user_states = {}

def load_data():
    if os.path.exists(REFERRAL_FILE):
        with open(REFERRAL_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(REFERRAL_FILE, "w") as f:
        json.dump(data, f)

def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, "r") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USER_DB, "w") as f:
        json.dump(data, f)

async def notify_admins(context, text):
    for admin_id in ADMIN_ID:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            print(f"[!] Error sending to admin {admin_id}: {e}")

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    ref_by = context.args[0] if context.args else None
    for member in update.message.new_chat_members:
        if ref_by and ref_by != str(member.id):
            data.setdefault(ref_by, [])
            if str(member.id) not in data[ref_by]:
                data[ref_by].append(str(member.id))
                save_data(data)
        await update.message.reply_text(
            "Чтобы продолжить, нажмите кнопку ниже и напишите боту в личку:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Зарегистрироваться", url="https://t.me/promotelabot?start=group")]
            ])
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    user_id = update.effective_user.id
    user_states[user_id] = {}
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👶 Новичок", callback_data="role_Новичок"),
         InlineKeyboardButton("🚛 Овнер", callback_data="role_Овнер")],
        [InlineKeyboardButton("🧠 Диспетчер", callback_data="role_Диспетчер"),
         InlineKeyboardButton("💰 Инвестор", callback_data="role_Инвестор")],
        [InlineKeyboardButton("Я драйвер", callback_data="role_Я драйвер"),
         InlineKeyboardButton("🔍 Консультация", callback_data="role_Консультация")]
    ])
    await update.message.reply_text("Пожалуйста, выбери кто ты:", reply_markup=keyboard)

async def role_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role = query.data.split("_", 1)[1]
    user_id = query.from_user.id
    user_states[user_id] = {"role": role}

    service_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Я драйвер", callback_data="service_Я драйвер")],
        [InlineKeyboardButton("хочу взять трейлер в аренду", callback_data="service_трейлер")],
        [InlineKeyboardButton("нужна открыть компанию MC/DOT", callback_data="service_MC")],
        [InlineKeyboardButton("купить готовую компанию с рекордом и MC/DOT", callback_data="service_готовая компания")],
        [InlineKeyboardButton("нужна консультация - eld", callback_data="service_eld")],
        [InlineKeyboardButton("нужна консультация - factoring", callback_data="service_factoring")],
        [InlineKeyboardButton("нужна консультация - accounting", callback_data="service_accounting")],
        [InlineKeyboardButton("нужна консультация - insurance", callback_data="service_insurance")],
        [InlineKeyboardButton("нужна консультация - registration", callback_data="service_registration")],
        [InlineKeyboardButton("нужна консультация - safety", callback_data="service_safety")],
        [InlineKeyboardButton("нужна консультация - compliance", callback_data="service_compliance")],
        [InlineKeyboardButton("нужна консультация - finance", callback_data="service_finance")],
        [InlineKeyboardButton("подбор трака/трейлера", callback_data="service_подбор")],
        [InlineKeyboardButton("нужен адвокат/юрист", callback_data="service_юрист")],
        [InlineKeyboardButton("ищу драйвера", callback_data="service_ищу драйвера")],
        [InlineKeyboardButton("🔍 Консультация", callback_data="service_консультация")]
    ])
    await query.message.reply_text("Что вас интересует?", reply_markup=service_keyboard)

async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service = query.data.split("_", 1)[1]
    user_id = query.from_user.id
    user_data = user_states.get(user_id, {})
    user_data["service"] = service
    user_states[user_id] = user_data

    msg_admin = (
        f"📥 Новый запрос от @{query.from_user.username or 'без username'}:"
        f"Роль: {user_data.get('role', 'не выбрана')}"
        f"Услуга: {service}"
    )
    await notify_admins(context, msg_admin)
    await query.message.reply_text("Спасибо! Ваш запрос отправлен, с вами скоро свяжутся.")

async def funnel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text.strip()
    state = user_states.get(user_id, {})

    if state.get("step") == "last_name":
        user_states[user_id]["last_name"] = msg
        user_states[user_id]["step"] = "first_name"
        await update.message.reply_text("Введите ваше имя:")
    elif state.get("step") == "first_name":
        user_states[user_id]["first_name"] = msg
        user_states[user_id]["step"] = "phone"
        await update.message.reply_text("Введите ваш номер телефона или Telegram @юзернейм:")
    elif state.get("step") == "phone":
        user_states[user_id]["phone"] = msg
        users = load_users()
        users[str(user_id)] = user_states[user_id]
        save_users(users)

        data = user_states[user_id]
        msg_admin = (
            f"📥 Новый контакт с воронки:"
            f"Роль: {data['role']}"
            f"Фамилия: {data['last_name']}"
            f"Имя: {data['first_name']}"
            f"Телефон/контакт: {data['phone']}"
        )
        await notify_admins(context, msg_admin)
        await update.message.reply_text("Спасибо! Ваша информация отправлена.")
        del user_states[user_id]

async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)
    count = len(data.get(user_id, []))
    await update.message.reply_text(f"📊 Ты пригласил {count} человек(а).")

async def topreferrers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    top = sorted(data.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    msg = "🏆 Топ пригласивших:"
    for uid, refs in top:
        try:
            user = await context.bot.get_chat(uid)
            msg += f"\n- {user.first_name}: {len(refs)} чел."
        except:
            pass
    await update.message.reply_text(msg)

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

async def spam_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if "http://" in message.text or "https://" in message.text or "t.me/" in message.text:
        try:
            await message.delete()
            await message.chat.kick_member(message.from_user.id)
            await message.reply_text(f"🚫 {message.from_user.first_name} был удалён за ссылки.")
        except:
            pass

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("topreferrers", topreferrers))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), spam_filter))
    app.add_handler(CallbackQueryHandler(role_selected, pattern="^role_"))
    app.add_handler(CallbackQueryHandler(service_selected, pattern="^service_"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), funnel_handler))
    app.run_polling()
