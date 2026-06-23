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
    # 1. Получаем точную текущую дату в UK
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

    # 3. Парсим строго по целевому дню
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Находим все текстовые элементы на странице
        elements = soup.find_all(['p', 'li', 'h2', 'h3', 'strong'])
        
        matches_today = []
        is_today_section = False  # Флаг: находимся ли мы внутри блока СЕГОДНЯШНЕЙ даты

        for elem in elements:
            text = elem.get_text().strip()
            if not text or len(text) > 250:
                continue
            
            text_lower = text.lower()
            
            # Проверяем, не является ли эта строка заголовком ДАТЫ
            # Строка должна содержать текущий месяц и именно текущий день отдельно (защита от "13 июня", если сегодня "3 июня")
            has_month = month_str in text_lower
            words = text_lower.split()
            has_exact_day = day_str in words or f"0{day_str}" in words or any(f"{day_str}" == w.strip(".,()-") for w in words)

            if has_month and has_exact_day and (len(text) < 40 or "матч" in text_lower or "тур" in text_lower):
                # Мы нашли заголовок сегодняшнего дня! Включаем сбор матчей
                is_today_section = True
                continue
            
            # Если мы зафиксировали начало сегодняшнего дня, но встретили ДРУГУЮ дату — выключаем сбор
            elif is_today_section and any(m in text_lower for m in MONTHS_RU.values()) and any(str(i) in text_lower for i in range(1, 32)):
                # Убедимся, что это реально другая дата, а не случайная строка
                if not has_exact_day:
                    is_today_section = False
                    break # Мы вышли из блока сегодняшних матчей, дальше парсить нет смысла

            # Если мы внутри блока сегодняшней даты — собираем строчки с матчами
            if is_today_section:
                # Строка матча обязательно содержит время через ":" и разделитель команд
                if ":" in text_lower and ("–" in text_lower or "-" in text_lower or " против " in text_lower or " - " in text_lower):
                    try:
                        clean_text = " ".join(text.split())
                        
                        # Извлекаем время из строки
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
                            
                            display_text = clean_text.replace(time_str, "").strip(" .,-—")
                            matches_today.append(f"⏰ *{time_uk_str}* (UK Time) | ⚽ {display_text}")
                        else:
                            matches_today.append(f"⚽ {clean_text}")
                    except Exception:
                        matches_today.append(f"⚽ {text}")

        # Удаляем дубликаты строк
        matches_today = list(set(matches_today))

        # 4. Формируем красивый и строгий ответ
        if matches_today:
            return f"📅 *Расписание матчей на сегодня ({today_formatted}):*\n\n" + "\n".join(matches_today)
        else:
            return f"📅 Сегодня (*{today_formatted}*) матчей ЧМ-2026 в расписании сайта не найдено.\n\n_Отдыхаем от футбола!_"

    except Exception as error_parse:
        return f"❌ Произошла ошибка при анализе сайта: {error_parse}"
        
