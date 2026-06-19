import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

URL = "https://sportnews.24tv.ua/ru/kalendar-matchej-chempionate-mira-po-futbolu-2026-daty-matchej_n3079670"

# Месяцы для поиска на русскоязычном сайте
MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

async def get_london_matches():
    # 1. Определяем текущую дату в Великобритании (GMT+1)
    uk_tz = pytz.timezone('Europe/London')
    now_uk = datetime.now(uk_tz)
    
    # Форматируем строку для поиска на сайте, например: "19 июня"
    today_str = f"{now_uk.day} {MONTHS_RU[now_uk.month]}"
    
    # 2. Асинхронно скачиваем страницу
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, timeout=10) as response:
                if response.status != 200:
                    return "❌ Не удалось загрузить спортивный сайт."
                html = await response.text()
        except Exception:
            return "❌ Ошибка сети при попытке получить расписание."

    # 3. Парсим контент
    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text()
    matches_today = []

    # Перебираем строки текста на странице
    for line in page_text.split('\n'):
        line = line.strip()
        
        # Нам нужны строки, начинающиеся с сегодняшней даты и содержащие знак матча "–" или "-"
        if line.startswith(today_str) and ("–" in line or "-" in line):
            try:
                # Пример строки: "19 июня, 22:00. США – Австралия"
                date_time_part, teams_part = line.split('.', 1)
                teams_part = teams_part.strip()
                
                # Забираем время ЧЧ:ММ (последние 5 символов из первой части)
                time_ua_str = date_time_part.split(',')[-1].strip()
                
                # Конвертируем время: Киев (GMT+3) -> Лондон (GMT+1). Разница -2 часа.
                ua_tz = pytz.timezone('Europe/Kyiv')
                
                # Строим объект времени для Киева
                parsed_time = datetime.strptime(time_ua_str, "%H:%M").time()
                dt_ua = ua_tz.localize(datetime.combine(now_uk.date(), parsed_time))
                
                # Переводим в часовой пояс Лондона
                dt_uk = dt_ua.astimezone(uk_tz)
                time_uk_str = dt_uk.strftime("%H:%M")
                
                matches_today.append(f"⏰ *{time_uk_str}* (UK Time) | ⚽ {teams_part}")
            except Exception:
                continue  # Если строка кривая, просто идем дальше

    # 4. Формируем красивый ответ
    if matches_today:
        return f"📅 *Расписание матчей на сегодня ({today_str}):*\n\n" + "\n".join(matches_today)
    else:
        return f"📅 Сегодня (*{today_str}*) матчей ЧМ-2026 не найдено."
  
