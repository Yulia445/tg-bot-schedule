import asyncio
import os
import re
from dotenv import load_dotenv
from groq import AsyncGroq

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database import (init_db, get_db_schedule, clear_completely, 
                      delete_all_in_day, smart_delete, smart_cancel, 
                      add_lesson, format_schedule_text)

load_dotenv()

# --- НАЛАШТУВАННЯ ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 5297726318

GROQ_API_KEYS = [key.strip() for key in os.getenv("GROQ_API_KEYS", "").split(",") if key.strip()]
groq_clients = [AsyncGroq(api_key=key) for key in GROQ_API_KEYS]
current_key_index = 0

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# --- AI LOGIC ---
async def get_groq_completion(messages):
    global current_key_index
    if not groq_clients: return None
    client = groq_clients[current_key_index]
    try:
        return await client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages)
    except Exception as e:
        print(f"Помилка ключа Groq: {e}")
        current_key_index = (current_key_index + 1) % len(groq_clients)
        return await get_groq_completion(messages)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    b = ReplyKeyboardBuilder().button(text="📚 Розклад").as_markup(resize_keyboard=True)
    await m.answer("Бро в строю! 😎 Кажи, що змінити.", reply_markup=b)

@dp.message(F.text == "📚 Розклад")
async def show_s(m: types.Message):
    await m.answer(format_schedule_text())

@dp.message()
async def handle_ai(message: types.Message):
    print(f"DEBUG: Від {message.from_user.id}: {message.text}")
    
    if message.from_user.id != ADMIN_ID: return

    current_sched = str(get_db_schedule())
    
    prompt = f"""Ти — Support Bro. Допомагай Юлі з розкладом.
Твоє завдання: видавати ТІЛЬКИ команди в квадратних дужках.

БАЗА ЗНАНЬ (ВИКЛАДАЧІ):
- Математичний аналіз -> Дзюба М.В.
- Інформаційно-комунікаційні технології -> Шкатуляк В.В.
- Українська мова -> Соловій У.В.
- Критичне мислення -> Надурак В.В.
- Основи роботи з нейронними мережами -> Головчук П.В.
- Основи програмування -> Піцур М.Р.
- Англійська мова-> Куцела М.М.

ПРАВИЛА:
1. Якщо Юля каже СКАСУВАТИ пару — використовуй [CANCEL:Предмет:День].
2. Якщо Юля каже ВИДАЛИТИ пару (геть з бази) — використовуй [DELETE:Предмет:День].
3. Тип пари (Лекція/Практика) пиши ТІЛЬКИ якщо Юля це згадала. Якщо ні — пиши None.
4. Якщо викладач не вказаний — візьми з бази знань.

ФОРМАТИ КОМАНД:
- [ADD:Предмет:День:НомерПари:Викладач:Аудиторія:ТипПари]
- [CANCEL:Предмет:День]
- [DELETE:Предмет:День]
- [DELETE_ALL:День]
- [CLEAR_EVERYTHING]

КОНТЕКСТ РОЗКЛАДУ: {current_sched}
Текст Юлі: "{message.text}" """

    try:
        response = await get_groq_completion([
            {"role": "system", "content": "Ти — технічний модуль. Відповідай виключно командами."},
            {"role": "user", "content": prompt}
        ])

        if not response: return

        cmd_text = response.choices[0].message.content.strip()
        lines = cmd_text.split('\n')
        status_executed = False
        chat_reply = []

        for line in lines:
            line = line.strip()
            upper = line.upper()

            if "[CLEAR_EVERYTHING]" in upper:
                clear_completely()
                status_executed = True
                chat_reply.append("🧹 Розклад очищено!")
            
            elif "DELETE_ALL:" in upper or "DELETE:ALL:" in upper:
                try:
                    day = line.split(":")[-1].strip("[] ")
                    delete_all_in_day(day)
                    status_executed = True
                    chat_reply.append(f"🗑 День {day} видалено")
                except: pass

            elif "[DELETE:" in upper:
                try:
                    p = line.split("[DELETE:")[1].split("]")[0].split(":")
                    smart_delete(p[0].strip(), p[1].strip())
                    status_executed = True
                    chat_reply.append(f"🗑 Видалено: {p[0]}")
                except: pass

            elif "[CANCEL:" in upper:
                try:
                    p = line.split("[CANCEL:")[1].split("]")[0].split(":")
                    smart_cancel(p[0].strip(), p[1].strip())
                    status_executed = True
                    chat_reply.append(f"❌ Скасовано: {p[0]}")
                except: pass

            elif "[ADD:" in upper:
                try:
                    p = line.split("[ADD:")[1].split("]")[0].split(":")
                    if len(p) >= 5:
                        l_type = p[5].strip() if len(p) > 5 else "Лекція"
                        add_lesson(p[0].strip(), p[1].strip(), p[2].strip(), p[3].strip(), p[4].strip(), l_type)
                        status_executed = True
                        chat_reply.append(f"✅ Додано: {p[0]}")
                except: pass
            else:
                if line and not line.startswith("["):
                    chat_reply.append(line)

        if chat_reply:
            await message.answer("\n".join(chat_reply))
        
        if status_executed:
            await asyncio.sleep(0.4)
            await message.answer(format_schedule_text())

    except Exception as e:
        print(f"Помилка: {e}")
        await message.answer(f"Помилка: {e}")

# --- ЗАПУСК ---
async def main():
    init_db()
    print("Бро запущений! 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
