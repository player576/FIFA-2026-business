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
    debug_info.append(f"🤖 **Бот ищет матчи покоординатно!**")
    debug_info.append(f"• Целевая дата: `{today_formatted}`")

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
        # Собираем текстовые элементы
        elements = soup.find_all(['p', 'li', 'td', 'strong'])
        
        raw_matches = []

        for elem in elements:
            text = elem.get_text().strip()
            if not text or len(text) > 200:
                continue
            
            text_lower = text.lower()
            
            # Строка должна содержать двоеточие (время) и разделитель команд
            if ":" in text_lower and ("–" in text_lower or "-" in text_lower or " против " in text_lower or " - " in text_lower):
                
                # Проверяем, относится ли эта конкретная строка к сегодняшнему дню
                if month_str in text_lower:
                    # Разбиваем строку на отдельные слова, чтобы проверить число дня
                    words = [w.strip(".,()[]-—:") for w in text_lower.split()]
                    
                    # Защита от счета матча: число должно идти РЯДОМ со словом месяца или в начале строки,
                    # но мы просто проверяем, есть ли day_str среди слов, И это слово не является частью счета матча (после двоеточия)
                    # Самый надежный способ — проверить, что day_str идет ПЕРЕД названием месяца или в первой половине строки
                    if day_str in words or f"0{day_str}" in words:
                        # Убедимся, что это не ложное срабатывание счета в конце строки
                        # Находим индекс слова с месяцем
                        try:
                            month_idx = -1
                            for i, word in enumerate(words):
                                if month_str in word:
                                    month_idx = i
                                    break
                            
                            # Если нашли месяц, проверяем, что наше число стоит где-то рядом (обычно прямо перед ним)
                            if month_idx != -1:
                                # Ищем, есть ли число в пределах 2 слов от месяца
                                start_search = max(0, month_idx - 2)
                                end_search = min(len(words), month_idx + 2)
                                sub_words = words[start_search:end_search]
                                
                                if day_str not in sub_words and f"0{day_str}" not in sub_words:
                                    continue # Это был счет матча, пропускаем строку
                        except Exception:
                            pass

                        # Если строка прошла валидацию даты — парсим время
                        try:
                            clean_text = " ".join(text.split())
                            time_str = ""
                            for word in clean_text.split():
                                if ":" in word:
                                    # Извлекаем чистое время ЧХ:ММ
                                    time_str = "".join([c for c in word if c.isdigit() or c == ":"])
                                    if ":" in time_str and len(time_str) >= 4:
                                        time_str = time_str[:5]
                                    break
                            
                            if time_str and len(time_str) == 5:
                                ua_tz = pytz.timezone('Europe/Kyiv')
                                parsed_time = datetime.strptime(time_str, "%H:%M").time()
                                
                                # Локализуем по Киеву и переводим в Лондон
                                dt_ua = ua_tz.localize(datetime.combine(now_uk.date(), parsed_time))
                                dt_uk = dt_ua.astimezone(uk_tz)
                                time_uk_str = dt_uk.strftime("%H:%M")
                                
                                # Очищаем текст от даты и старого времени, оставляя только команды и счет
                                display_text = clean_text
                                if time_str in display_text:
                                    display_text = display_text.replace(time_str, "")
                                # Удаляем упоминание даты из строки матча, чтобы не дублировать
                                if today_formatted in display_text:
                                    display_text = display_text.replace(today_formatted, "")
                                display_text = display_text.strip(" .,-—–:()")
                                
                                # Сохраняем (ключ_для_сортировки, готовая_строка)
                                raw_matches.append((time_uk_str, f"⏰ *{time_uk_str}* | ⚽ {display_text}"))
                        except Exception:
                            raw_matches.append(("23:59", f"⚽ {text}"))

        # Убираем дубликаты через словарь
        unique_matches = {}
        for time_key, match_text in raw_matches:
            unique_matches[match_text] = time_key

        # СОРТИРОВКА: Сортируем ключи по времени (от 00:00 до 23:59)
        # Матчи 00:00 теперь железно будут ПЕРВЫМИ в списке!
        sorted_matches = sorted(unique_matches.keys(), key=lambda x: unique_matches[x])

        debug_info.append(f"✅ Найдено строк матчей: `{len(sorted_matches)}`")

        if sorted_matches:
            report = f"📅 *Расписание матчей на сегодня ({today_formatted}):*\n\n" + "\n".join(sorted_matches)
        else:
            report = f"📅 Сегодня (*{today_formatted}*) матчей не найдено."
            
        return "\n".join(debug_info) + "\n\n" + report

    except Exception as error_parse:
        return f"❌ Произошла ошибка при анализе сайта: {error_parse}"
                                
