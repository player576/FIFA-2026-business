import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiohttp import web

import config
from parser import get_london_matches

# Включаем логирование, чтобы в панели Render было видно статус бота
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Главная клавиатура с кнопкой
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="⚽ Матчи на сегодня")
    return builder.as_markup(resize_keyboard=True)

# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот ЧМ-2026. Нажми на кнопку ниже, чтобы получить актуальное расписание матчей на сегодня по времени Великобритании (UK Time).",
        reply_markup=get_main_keyboard()
    )

# Хэндлер на нажатие кнопки получения матчей
@dp.message(lambda message: message.text == "⚽ Матчи на сегодня")
async def show_matches(message: types.Message):
    # Отправляем временный статус, чтобы пользователь видел, что бот работает
    waiting_msg = await message.answer("🔄 Залезаю в интернет, проверяю расписание...")
    
    # Получаем данные из нашего парсера
    report = await get_london_matches()
    
    # Удаляем сообщение со статусом ожидания и присылаем результат
    await waiting_msg.delete()
    await message.answer(report, parse_mode="Markdown")

# --- ХЭНДЛЕР ДЛЯ ОБМАНА RENDER ---
# Этот эндпоинт будет отвечать пинг-сервису Render, что всё хорошо
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

# Запуск бота и веб-сервера
async def main():
    logging.info("Запуск фонового веб-сервера для Render...")
    
    # Создаем минимальное веб-приложение
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render автоматически передает нужный ему порт в переменную окружения PORT.
    # Если её нет (например, при тесте на ПК), используем порт 8000.
    port = int(os.getenv("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    # Запускаем сервер в фоновом режиме асинхронно
    asyncio.create_task(site.start())
    logging.info(f"Временный веб-сервер успешно запущен на порту {port}")

    # Запускаем стандартный опрос Telegram (Polling)
    logging.info("Бот успешно запущен в режиме Polling!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
