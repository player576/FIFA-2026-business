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
    
    # 2. Скачиваем страницу
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, timeout=10) as response:
                if response.status != 200:
                    return f"❌ Сайт вернул статус {response.status}"
                html = await response.text()
        except Exception as error_net:
            return f"❌ Ошибка сети при скачивании сайта: {error_net}"

    # 3. Парсим контент через элементы блоков
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Собираем текст из параграфов, списков и заголовков, где лежит расписание
        elements = soup.find_all(['p', 'li', 'h2', 'h3', 'div'])
        
        matches_today = []
        current_date_context = ""

        for elem in elements:
            text = elem.get_text().strip()
            if not text or len(text) > 200: # Пропускаем огромные куски текста
                continue
            
            text_lower = text.lower()
            
            # Если строка похожа на дату (например, "19 июня" или "пятница, 19 июня")
            if month_str in text_lower and any(str(i) in text_lower for i in range(1, 32)):
                current_date_context = text_lower

            # Ищем строчку с матчем (должно быть время через двоеточие и знак переноса/дефиса матча)
            if ":" in text_lower and ("–" in text_lower or "-" in text_lower or " против " in text_lower):
                # Проверяем, относится ли этот матч к сегодняшнему дню
                # Либо дата написана прямо в строке матча, либо в текущем заголовке над ней
                if (day_str in text_lower and month_str in text_lower) or (day_str in current_date_context and month_str in current_date_context):
                    try:
                        # Чистим текст от лишних пробелов
                        clean_text = " ".join(text.split())
                        
                        # Пробуем вытащить время Киев/МСК из строки для перевода в UK Time
                        # Формат обычно: "19:00. Группа А: ..." или "22:00 Команда - Команда"
                        time_str = ""
                        for word in clean_text.split():
                            if ":" in word:
                                time_str = word.strip(".,()[]")
                                break
                        
                        if time_str:
                            ua_tz = pytz.timezone('Europe/Kyiv')
                            parsed_time = datetime.strptime(time_str, "%H:%M").time()
                            
                            dt_ua = ua_tz.localize(datetime.combine(now_uk.date(), parsed_time))
                            dt_uk = dt_ua.astimezone(uk_tz)
                            time_uk_str = dt_uk.strftime("%H:%M")
                            
                            # Убираем время из текста, чтобы красиво отформатировать
                            display_text = clean_text.replace(time_str, "").strip(" .,-—")
                            matches_today.append(f"⏰ *{time_uk_str}* (UK Time) | ⚽ {display_text}")
                        else:
                            # Если точное время не распарсилось, выводим строку как есть
                            matches_today.append(f"⚽ {clean_text}")
                    except Exception:
                        # Если перевод времени споткнулся, просто добавляем исходный текст
                        matches_today.append(f"⚽ {text}")

        # Удаляем дубликаты, если они собрались из разных тегов
        matches_today = list(set(matches_today))

        # 4. Вывод результата
        if matches_today:
            return f"📅 *Расписание матчей на сегодня ({today_formatted}):*\n\n" + "\n".join(matches_today)
        else:
            return f"📅 Сегодня (*{today_formatted}*) матчей ЧМ-2026 в расписании сайта не найдено.\n\n_Возможно, на сегодня нет запланированных игр или календарь обновится позже._"

    except Exception as error_parse:
        return f"❌ Произошла ошибка при анализе сайта: {error_parse}"
                            
