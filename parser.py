import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

URL = "https://sportnews.24tv.ua/ru/kalendar-matchej-chempionate-mira-po-futbolu-2026-daty-matchej_n3079670"

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

async def get_london_matches():
    # 1. Время в Великобритании
    uk_tz = pytz.timezone('Europe/London')
    now_uk = datetime.now(uk_tz)
    
    day_str = str(now_uk.day)
    month_str = MONTHS_RU[now_uk.month]
    today_formatted = f"{day_str} {month_str}"
    
    debug_info = []
    debug_info.append(f"🤖 **Лог отладки парсера:**")
    debug_info.append(f"• Текущее время на сервере (UK): {now_uk.strftime('%Y-%m-%d %H:%M:%S')}")
    debug_info.append(f"• Ищем в тексте совпадения для: `{day_str}` и `{month_str}`")

    # 2. Скачиваем страницу
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, timeout=10) as response:
                debug_info.append(f"• Статус ответа сайта: {response.status}")
                if response.status != 200:
                    return f"❌ Сайт вернул статус {response.status}"
                html = await response.text()
        except Exception as e:
            return f"❌ Ошибка сети при скачивании сайта: {e}"

    # 3. Парсим
    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text()
    
    lines = page_text.split('\n')
    debug_info.append(f"• Всего строк получено с сайта: {len(lines)}")
    
    matches_today = []
    matched_lines_count = 0

    # Пройдемся по строкам
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        line_lower = line.lower()
        
        # Проверяем условия поиска
        has_day = day_str in line_lower
        has_month = month_str in line_lower
        
        # Запишем в логи первую попавшуюся строку с упоминанием месяца, чтобы посмотреть её структуру
        if has_month and matched_lines_count < 2:
            debug_info.append(f"📝 *Пример строки с месяцем:* `{line[:80]}`")
            matched_lines_count += 1

        if has_day and has_month and ":" in line_lower and ("–" in line_lower or "-" in line_lower):
            try:
                line = " ".join(line.split())
                
                if "," in line:
                    _, data_part = line.split(",", 1)
                    data_part = data_part.strip()
                else:
                    data_part = line
                
                time_part, teams_part = data_part.split(".", 1)
                time_ua_str = time_part.strip()
                teams_part = teams_part.strip()
                
                ua_tz = pytz.timezone('Europe/Kyiv')
                parsed_time = datetime.strptime(time_ua_str, "%H:%M").time()
                
                dt_ua = ua_tz.localize(datetime.combine(now_uk.date(), parsed_time))
                dt_uk = dt_ua.astimezone(uk_tz)
                time_uk_str = dt_uk.strftime("%H:%M")
                
                matches_today.append(f"⏰ *{time_uk_str}* (UK Time) | ⚽ {teams_part}")
            except Exception as e:
                debug_info.append(f"⚠️ Ошибка обработки строки матча: {e}")
                continue

    debug_info.append(f"• Найдено валидных матчей: {len(matches_today)}\n" + "—" * 15)

    # 4. Вывод результата вместе с логом
    if matches_today:
        report = f"📅 *Расписание матчей на сегодня ({today_formatted}):*\n\n" + "\n".join(matches_today)
    else:
        report = f"📅 Сегодня (*{today_formatted}*) матчей ЧМ-2026 в расписании сайта не найдено.{e}"
        
    # Склеиваем отчет и логи отладки
    return "\n".join(debug_info) + "\n\n" + report
        
