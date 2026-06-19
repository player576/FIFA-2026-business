import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

import config
from parser import get_london_matches

# Включаем логирование, чтобы на Render было видно, если что-то пойдет не так
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
    # Отправляем временный статус, чтобы заказчик видел, что бот «думает» и лезет в сеть
    waiting_msg = await message.answer("🔄 Залезаю в интернет, проверяю расписание...")
    
    # Получаем данные из нашего парсера
    report = await get_london_matches()
    
    # Удаляем сообщение со статусом ожидания и присылаем результат
    await waiting_msg.delete()
    await message.answer(report, parse_mode="Markdown")

# Запуск бота (Режим Polling - для тестов на ПК)
async def main():
    logging.info("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
