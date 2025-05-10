import telebot
from telebot import types
import sqlite3
import json
from config import TOKEN

bot = telebot.TeleBot(TOKEN)

users = {}


def load_career_data():
    with open("career_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            age TEXT,
            mood TEXT,
            experience TEXT,
            interests TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_user(user_id, age, mood, experience, interests):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, age, mood, experience, interests)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, age, mood, experience, ",".join(interests)))
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    users[chat_id] = {}
    bot.send_message(chat_id, "Привет! Я помогу тебе найти новое направление. Сколько тебе лет?")
    bot.register_next_step_handler(message, ask_mood)

def ask_mood(message):
    chat_id = message.chat.id
    users[chat_id]["age"] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("🔥 Хочу вдохновения", "😫 Выгорел(а)", "👀 Просто интересно")
    bot.send_message(chat_id, "Как ты себя чувствуешь?", reply_markup=markup)
    bot.register_next_step_handler(message, ask_experience)

def ask_experience(message):
    chat_id = message.chat.id
    users[chat_id]["mood"] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("🎓 Учуcь", "🧑‍💼 Работаю", "🔄 Меняю профессию")
    bot.send_message(chat_id, "Какой у тебя опыт?", reply_markup=markup)
    bot.register_next_step_handler(message, ask_interests)

def ask_interests(message):
    chat_id = message.chat.id
    users[chat_id]["experience"] = message.text
    bot.send_message(chat_id, "Какие у тебя интересы? Напиши через запятую (например: дизайн, видео, психология)")
    bot.register_next_step_handler(message, show_recommendations)

def show_recommendations(message):
    chat_id = message.chat.id
    interests = [i.strip().lower() for i in message.text.split(",")]
    users[chat_id]["interests"] = interests

    careers = load_career_data()
    matches = []

    for career in careers:
        tags = [tag.lower() for tag in career['tags']]
        if any(interest in tags for interest in interests):
            matches.append(career)

    if not matches:
        bot.send_message(chat_id, "Пока не нашел ничего подходящего 😔, но скоро база обновится!")
    else:
        for career in matches:
            bot.send_message(
                chat_id,
                f"💼 *{career['title']}*\n\n{career['description']}",
                parse_mode="Markdown"
            )

    
    save_user(
        user_id=chat_id,
        age=users[chat_id]["age"],
        mood=users[chat_id]["mood"],
        experience=users[chat_id]["experience"],
        interests=interests
    )

    bot.send_message(chat_id, "Твоя анкета сохранена 🗂️. Хочешь начать заново — напиши /start")


@bot.message_handler(commands=['profile'])
def handle_profile(message):
    chat_id = message.chat.id
    user = get_user(chat_id)

    if not user:
        bot.send_message(chat_id, "Ты ещё не проходил анкету. Напиши /start, чтобы начать!")
        return

    age, mood, experience, interests = user[1], user[2], user[3], user[4]
    profile_text = (
        f"🧾 *Твоя анкета:*\n\n"
        f"📅 Возраст: {age}\n"
        f"💬 Настроение: {mood}\n"
        f"🧠 Опыт: {experience}\n"
        f"🎯 Интересы: {interests}"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("🔄 Обновить анкету")
    bot.send_message(chat_id, profile_text, parse_mode="Markdown", reply_markup=markup)
    bot.register_next_step_handler(message, profile_next_action)

def profile_next_action(message):
    if "обновить" in message.text.lower():
        send_welcome(message)
    else:
        bot.send_message(message.chat.id, "Если захочешь изменить данные — напиши /start.")


if __name__ == "__main__":
    init_db()
    print("Бот запущен.")
    bot.infinity_polling()
