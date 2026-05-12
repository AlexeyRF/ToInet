import json
import requests
import csv
import io
import re
from datetime import datetime

URL_MINJUST = "https://minjust.gov.ru/uploaded/files/exportfsm.csv"

ROOT_URLS = [
    "https://ya.ru",
    "https://vk.com",
    "https://mail.ru",
    "https://dzen.ru",
    "https://habr.com",
    "https://pikabu.ru",
    "https://rutube.ru",
    "https://www.rbc.ru",
    "https://lenta.ru",
    "https://vc.ru"
]

BASE_BLACKLIST = [
    ".ua",           # Все украинские домены
    "bit.ly",        # Сократители ссылок
    "t.co",
    "goo.gl",
    "clck.ru",
    "vk.cc",
    "is.gd",
    "tinyurl.com",
    "t.me",       
    ".css",
    ".ico",
    ".xml",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".iso",
    ".pdf"
]

SAFE_DOMAINS = {
    "vk.com", "ya.ru", "yandex.ru", "mail.ru", "ok.ru", "rutube.ru"
}

MODERN_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

def fetch_extremism_registry_domains():
    print("Загрузка реестра экстремистских материалов Минюста...")
    domains = set()
    try:
        headers = {'User-Agent': MODERN_USER_AGENTS[0]}
        response = requests.get(URL_MINJUST, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = None
        for enc in ['utf-8-sig', 'utf-8', 'cp1251', 'windows-1251']:
            try:
                content = response.content.decode(enc)
                break
            except:
                continue
                
        if content is None:
            raise Exception("Не удалось декодировать файл реестра.")

        csv_file = io.StringIO(content)
        reader = csv.reader(csv_file, delimiter=';', quotechar='"')
        
        domain_pattern = re.compile(r'(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,15})(?:[\/\s]|$)')
        
        for row in reader:
            if len(row) >= 2:
                text = row[1].lower()
                matches = domain_pattern.findall(text)
                for match in matches:
                    domain = match.strip('.)/,')
                    if domain and domain not in SAFE_DOMAINS:
                        domains.add(domain)

        print(f"Извлечено уникальных доменов из реестра: {len(domains)}")
        return list(domains)

    except Exception as e:
        print(f"Ошибка при получении базы Минюста: {e}")
        return []

def generate_config():
    print("Генерация конфигурации...")
    extremism_domains = fetch_extremism_registry_domains()
    final_blacklist = BASE_BLACKLIST + extremism_domains
    config = {
        "max_depth": 25,
        "min_sleep": 3,
        "max_sleep": 6,
        "timeout": False,
        "root_urls": ROOT_URLS,
        "blacklisted_urls": final_blacklist,
        "user_agents": MODERN_USER_AGENTS
    }
    output_filename = "config.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
        
    print(f"Конфигурация успешно сохранена в {output_filename}")

if __name__ == "__main__":
    generate_config()