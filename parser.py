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
    # Работаем строго по времени Лондона (UK)
    uk_tz = pytz.timezone('Europe/London')
    now_uk = datetime.now(uk_tz)
    
    day_str = str(now_uk.day)
    month_str = MONTHS_RU[now_uk.month]
    today_formatted = f"{day_str} {month_str}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, timeout=10) as response:
                if response.status != 200:
                    return f"❌ Сайт вернул статус {response.status}"
                html = await response.text()
        except Exception as error_net:
            return f"❌ Ошибка сети при скачивании сайта: {error_net}"

    try:
        soup = BeautifulSoup(html, 'html.parser')
        elements = soup.find_all(['p', 'li', 'h2', 'h3', 'strong', 'td', 'div'])
        
        raw_matches = []
        is_today_section = False  

        for elem in elements:
            text = elem.get_text().strip()
            if not text or len(text) > 200:
                continue
            
            text_lower = text.lower()
            
            # 1. Проверяем, является ли строка заголовком ИМЕННО СЕГОДНЯШНЕГО дня
            if month_str in text_lower:
                words = [w.strip(".,()-") for w in text_lower.split()]
                if day_str in words or f"0{day_str}" in words:
                    if len(text) < 50:  # Короткая строка — точно заголовок даты
                        is_today_section = True
                        continue
                else:
                    # Если встретили заголовок с ДРУГИМ числом этого же месяца — выключаем сбор
                    if is_today_section and len(text) < 50:
                        is_today_section = False
                        break

            # 2. Собираем игры только если флаг "сегодня" активен
            if is_today_section:
                if ":" in text_lower and ("–" in text_lower or "-" in text_lower or " против " in text_lower or " - " in text_lower):
                    try:
                        clean_text = " ".join(text.split())
                        time_str = ""
                        for word in clean_text.split():
                            if ":" in word:
                                time_str = word.strip(".,()[]")
                                break
                        
                        if time_str:
                            ua_tz = pytz.timezone('Europe/Kyiv')
                            parsed_time = datetime.strptime(time_str, "%H:%M").time()
                            # Локализуем по Киеву (время на сайте) и переводим в Лондон
                            dt_ua = ua_tz.localize(datetime.combine(now_uk.date(), parsed_time))
                            dt_uk = dt_ua.astimezone(uk_tz)
                            time_uk_str = dt_uk.strftime("%H:%M")
                            
                            display_text = clean_text.replace(time_str, "").strip(" .,-—")
                            # Сохраняем кортеж (время_строка, текст_для_вывода) для последующей сортировки
                            raw_matches.append((time_uk_str, f"⏰ *{time_uk_str}* (UK) | ⚽ {display_text}"))
                        else:
                            raw_matches.append(("23:59", f"⚽ {clean_text}"))
                    except Exception:
                        raw_matches.append(("23:59", f"⚽ {text}"))

        # Убираем дубликаты через словарь, сохраняя структуру
        unique_matches = {}
        for time_key, match_text in raw_matches:
            unique_matches[match_text] = time_key

        # 3. СОРТИРОВКА: теперь матчи 00:00 железно будут в самом начале списка!
        sorted_matches = sorted(unique_matches.keys(), key=lambda x: unique_matches[x])

        if sorted_matches:
            return f"📅 *Расписание матчей на сегодня ({today_formatted}):*\n\n" + "\n".join(sorted_matches)
        else:
            return f"📅 Сегодня (*{today_formatted}*) матчей ЧМ-2026 в расписании сайта не найдено."

    except Exception as error_parse:
        return f"❌ Ошибка парсера: {error_parse}"
            
