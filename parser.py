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
    # 1. Определяем текущую дату и время в Великобритании (GMT+1)
    uk_tz = pytz.timezone('Europe/London')
    now_uk = datetime.now(uk_tz)
    
    # Нам нужны день (число) и название месяца в нижнем регистре
    day_str = str(now_uk.day)
    month_str = MONTHS_RU[now_uk.month]
    
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
        line_lower = line.lower()
        
        # Ищем гибко: в строке должно быть число дня, название месяца, двоеточие во времени и знак матча
        if day_str in line_lower and month_str in line_lower and ":" in line_lower and ("–" in line_lower or "-" in line_lower):
            try:
                # Очищаем строку от случайных двойных пробелов внутри текста
                line = " ".join(line.split())
                
                # Отделяем дату (все, что до запятой) от времени и команд
                if "," in line:
                    _, data_part = line.split(",", 1)
                    data_part = data_part.strip()
                else:
                    data_part = line
                
                # Разделяем время и команды по первой точке
                # Из "22:00. США – Австралия" получаем "22:00" и "США – Австралия"
                time_part, teams_part = data_part.split(".", 1)
                time_ua_str = time_part.strip()
                teams_part = teams_part.strip()
                
                # Конвертируем время из Киева (GMT+3) в Лондон (GMT+1) -> минус 2 часа
                ua_tz = pytz.timezone('Europe/Kyiv')
                parsed_time = datetime.strptime(time_ua_str, "%H:%M").time()
                
                # Собираем полноценную киевскую дату-время
                dt_ua = ua_tz.localize(datetime.combine(now_uk.date(), parsed_time))
                
                # Переводим в часовой пояс Великобритании
                dt_uk = dt_ua.astimezone(uk_tz)
                time_uk_str = dt_uk.strftime("%H:%M")
                
                matches_today.append(f"⏰ *{time_uk_str}* (UK Time) | ⚽ {teams_part}")
            except Exception:
                # Если какая-то строка текста оказалась левой и вызвала ошибку — просто пропускаем её
                continue

    # 4. Формируем красивый итоговый текст
    today_formatted = f"{day_str} {month_str}"
    if matches_today:
        return f"📅 *Расписание матчей на сегодня ({today_formatted}):*\n\n" + "\n".join(matches_today)
    else:
        return f"📅 Сегодня (*{today_formatted}*) матчей ЧМ-2026 не найдено."
        
