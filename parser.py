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
        # Ищем строго по тегам заголовков и абзацев, где обычно пишется дата дня
        elements = soup.find_all(['h2', 'h3', 'p', 'strong', 'li'])
        
        raw_matches = []
        is_today_section = False  

        for elem in elements:
            text = elem.get_text().strip()
            if not text or len(text) > 200:
                continue
            
            text_lower = text.lower()
            
            # --- ПРОВЕРКА НА ЗАГОЛОВОК ДНЯ ---
            # Строка даты должна быть короткой и НЕ должна содержать счёт или двоеточие времени
            if month_str in text_lower and ":" not in text_lower and "–" not in text_lower and " - " not in text_lower:
                words = [w.strip(".,()-—") for w in text_lower.split()]
                
                # Проверяем точное совпадение числа дня (например "30" или "030")
                if day_str in words or f"0{day_str}" in words:
                    if len(text) < 40:  # Чистый заголовок дня
                        is_today_section = True
                        continue
                else:
                    # Если нашли заголовок ДРУГОГО дня — закрываем сбор
                    if is_today_section and len(text) < 40:
                        is_today_section = False
                        break 

            # --- СБОР МАТЧЕЙ ---
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
                            dt_ua = ua_tz.localize(datetime.combine(now_uk.date(), parsed_time))
                            dt_uk = dt_ua.astimezone(uk_tz)
                            time_uk_str = dt_uk.strftime("%H:%M")
                            
                            display_text = clean_text.replace(time_str, "").strip(" .,-—")
                            
                            # Сохраняем в список (время, текст), чтобы потом отсортировать
                            raw_matches.append((time_uk_str, f"⏰ *{time_uk_str}* (UK) | ⚽ {display_text}"))
                    except Exception:
                        raw_matches.append(("23:59", f"⚽ {text}"))

        # Фильтруем дубликаты, сохраняя связь с временем
        unique_matches = {}
        for time_key, match_text in raw_matches:
            unique_matches[match_text] = time_key

        # СОРТИРОВКА: Матчи 00:00 и 01:00 теперь ГАРАНТИРОВАННО будут в самом начале списка
        sorted_matches = sorted(unique_matches.keys(), key=lambda x: unique_matches[x])

        if sorted_matches:
            return f"📅 *Расписание матчей на сегодня ({today_formatted}):*\n\n" + "\n".join(sorted_matches)
        else:
            return f"📅 Сегодня (*{today_formatted}*) матчей ЧМ-2026 в расписании сайта не найдено."

    except Exception as error_parse:
        return f"❌ Ошибка парсера: {error_parse}"
                            
