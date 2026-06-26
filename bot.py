import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiohttp import web

import config
from parser import get_london_matches

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчер
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Главная клавиатура
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
    waiting_msg = await message.answer("🔄 Залезаю в интернет, проверяю расписание...")
    report = await get_london_matches()
    await waiting_msg.delete()
    await message.answer(report, parse_mode="Markdown")


# --- ВЕБ-СЕРВЕР ДЛЯ ОБМАНА RENDER И ДЛЯ UPTIMEROBOT ---

# Этот хэндлер вернет статус 200 OK для UptimeRobot, когда тот перейдет по ссылке
async def handle_ping(request):
    return web.Response(text="Bot is alive!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render автоматически передает нужный порт в переменную окружения PORT.
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    await site.start()
    logging.info(f"=== Фоновый веб-сервер успешно запущен на порту {port} ===")


# --- ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА ---
async def main():
    # 1. Запускаем веб-сервер в фоновом режиме асинхронно
    asyncio.create_task(start_web_server())
    
    # 2. УДАЛЯЕМ КОНФЛИКТУЮЩИЕ ВЕБХУКИ (Чистим память Телеграма)
    logging.info("Очистка старых вебхуков...")
    await bot.delete_webhook(drop_pending)
    
