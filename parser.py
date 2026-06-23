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
    
    debug_info = []
    debug_info.append(f"🤖 **Диагностика парсера:**")
    debug_info.append(f"• Ищем дату: `{today_formatted}`")

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
        elements = soup.find_all(['p', 'li', 'h2', 'h3', 'strong', 'td'])
        
        matches_today = []
        is_today_section = False
        found_date_header = False

        for elem in elements:
            text = elem.get_text().strip()
            if not text or len(text) > 250:
                continue
            
            text_lower = text.lower()
            
            # Проверяем заголовок даты
            has_month = month_str in text_lower
            words = text_lower.split()
            # Более гибкая проверка на точное совпадение дня (чтобы ловить "23", "23-е", "23.06")
            has_exact_day = any(day_str == "".join(filter(str.isdigit, w)) for w in words)

            if has_month and has_exact_day and not found_date_header:
                if len(text) < 60 or "матч" in text_lower or "групп" in text_lower:
                    is_today_section = True
                    found_date_header = True
                    debug_info.append(f"✅ НАЙДЕН заголовок дня: `{text}`")
                    continue
            
            # Если мы уже в блоке сегодня, но встретили ДРУГУЮ дату — выходим
            elif is_today_section and any(m in text_lower for m in MONTHS_RU.values()):
                if not has_exact_day:
                    debug_info.append(f"🛑 Вышли из блока на строке: `{text[:50]}...`")
                    is_today_section = False
                    break

            # Собираем матчи
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
                            matches_today.append(f"⏰ *{time_uk_str}* | ⚽ {display_text}")
                        else:
                            matches_today.append(f"⚽ {clean_text}")
                    except Exception:
                        matches_today.append(f"⚽ {text}")

        if not found_date_header:
            debug_info.append("❌ Парсер вообще не смог найти на странице блок с сегодняшней датой!")

        matches_today = list(set(matches_today))

        # Собираем итоговый отчет
        if matches_today:
            report = f"📅 *Расписание матчей на сегодня ({today_formatted}):*\n\n" + "\n".join(matches_today)
        else:
            report = f"📅 Сегодня (*{today_formatted}*) матчей не найдено."
            
        return "\n".join(debug_info) + "\n\n" + report

    except Exception as error_parse:
        return f"❌ Произошла ошибка при анализе сайта: {error_parse}"
        
