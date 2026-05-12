import argparse
import datetime
import json
import logging
import random
import re
import subprocess
import sys
import time
from urllib.parse import urljoin, urlparse
import requests


class Crawler:
    """Основной класс веб-краулера для обхода сайтов"""
    class CrawlerTimedOut(Exception):
        """Исключение, возникающее при превышении времени ожидания"""
        pass

    def __init__(self):
        """Инициализация краулера"""
        self._config = {}
        self._links = []
        self._start_time = None

    def _request(self, url):
        """
        Отправляет GET-запрос со случайным User-Agent
        :param url: URL для посещения
        :return: объект Response от requests
        """
        headers = {'user-agent': random.choice(self._config["user_agents"])}
        return requests.get(url, headers=headers, timeout=5)

    @staticmethod
    def _normalize_link(link, root_url):
        """
        Нормализует ссылки, преобразуя относительные в абсолютные
        :param link: ссылка из HTML
        :param root_url: URL страницы, откуда взята ссылка
        :return: абсолютная ссылка или None при ошибке
        """
        try:
            parsed_url = urlparse(link)
        except ValueError:
            return None

        parsed_root_url = urlparse(root_url)

        # '//' — сохранить текущий протокол
        if link.startswith("//"):
            return f"{parsed_root_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        # Относительный путь
        if not parsed_url.scheme:
            return urljoin(root_url, link)

        return link

    @staticmethod
    def _is_valid_url(url):
        """
        Проверяет, является ли URL валидным
        :param url: проверяемый URL
        :return: True если URL валиден
        """
        regex = re.compile(
            r'^(?:http|ftp)s?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return re.match(regex, url) is not None

    def _is_blacklisted(self, url):
        """
        Проверяет, находится ли URL в чёрном списке
        :param url: полный URL
        :return: True если URL в чёрном списке
        """
        return any(blacklisted in url for blacklisted in self._config["blacklisted_urls"])

    def _should_accept_url(self, url):
        """
        Фильтрует URL (валидность и чёрный список)
        :param url: проверяемый URL
        :return: True если URL можно принимать
        """
        return url and self._is_valid_url(url) and not self._is_blacklisted(url)

    def _extract_urls(self, body, root_url):
        """
        Извлекает все ссылки из HTML-страницы
        :param body: HTML-код страницы
        :param root_url: базовый URL страницы
        :return: список отфильтрованных ссылок
        """
        pattern = r"href=[\"'](?!#)(.*?)[\"'].*?"
        urls = re.findall(pattern, str(body))
        normalized = [self._normalize_link(url, root_url) for url in urls]
        return list(filter(self._should_accept_url, normalized))

    def _remove_and_blacklist(self, link):
        """
        Удаляет ссылку из текущего списка и добавляет в чёрный список
        :param link: удаляемая ссылка
        """
        self._config['blacklisted_urls'].append(link)
        self._links.remove(link)

    def _browse_from_links(self, depth=0):
        """
        Рекурсивно обходит ссылки, выбирая случайную
        :param depth: текущая глубина обхода
        """
        if not self._links or depth >= self._config['max_depth']:
            return

        if self._is_timeout_reached():
            raise self.CrawlerTimedOut

        link = random.choice(self._links)
        try:
            logging.info(f"Посещение {link}")
            response = self._request(link)
            content = response.content

            time.sleep(random.randrange(self._config["min_sleep"], self._config["max_sleep"]))

            new_links = self._extract_urls(content, link)
            if len(new_links) > 1:
                self._links = new_links
            else:
                self._remove_and_blacklist(link)

        except requests.exceptions.RequestException:
            logging.debug(f"Ошибка при запросе {link}, удаление из списка")
            self._remove_and_blacklist(link)

        self._browse_from_links(depth + 1)

    def load_config_file(self, file_path):
        """
        Загружает JSON-конфиг из файла
        :param file_path: путь к конфигу
        """
        with open(file_path, 'r') as f:
            self.set_config(json.load(f))

    def set_config(self, config):
        """
        Устанавливает конфигурацию краулера
        :param config: словарь с настройками
        """
        self._config = config

    def set_option(self, option, value):
        """
        Устанавливает отдельную опцию в конфиге
        :param option: ключ опции (например 'max_depth')
        :param value: значение опции
        """
        self._config[option] = value

    def _is_timeout_reached(self):
        """
        Проверяет, превышено ли время работы краулера
        :return: True если таймаут достигнут
        """
        if not self._config.get("timeout"):
            return False
        end_time = self._start_time + datetime.timedelta(seconds=self._config["timeout"])
        return datetime.datetime.now() >= end_time

    def crawl(self):
        """
        Запускает процесс обхода: выбирает корневой URL и начинает рекурсивный обход
        """
        self._start_time = datetime.datetime.now()

        while True:
            url = random.choice(self._config["root_urls"])
            try:
                body = self._request(url).content
                self._links = self._extract_urls(body, url)
                logging.debug(f"Найдено {len(self._links)} ссылок")
                self._browse_from_links()

            except (requests.exceptions.RequestException, MemoryError, Exception) as e:
                logging.warning(f"Ошибка при обработке {url}: {type(e).__name__}")

            except self.CrawlerTimedOut:
                logging.info("Таймаут превышен, завершение работы")
                return


def run_config_generator():
    """Запускает config_generator.py для генерации config.json"""
    logging.info("Запуск config_generator.py для генерации конфигурации...")
    try:
        result = subprocess.run(
            [sys.executable, "config_generator.py"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            logging.info("config_generator.py успешно выполнен")
            if result.stdout:
                logging.debug(f"Вывод генератора: {result.stdout}")
        else:
            logging.error(f"Ошибка при выполнении config_generator.py (код {result.returncode})")
            if result.stderr:
                logging.error(f"STDERR: {result.stderr}")
            sys.exit(1)
    except FileNotFoundError:
        logging.error("config_generator.py не найден в текущей директории")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Неизвестная ошибка при запуске config_generator.py: {e}")
        sys.exit(1)


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    run_config_generator()

    crawler = Crawler()
    
    config_path = "config.json"
    try:
        crawler.load_config_file(config_path)
        logging.info(f"Конфигурация успешно загружена из {config_path}")
    except FileNotFoundError:
        logging.error(f"Файл {config_path} не найден после выполнения генератора")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка парсинга JSON в {config_path}: {e}")
        sys.exit(1)

    # crawler.set_option('timeout', 10)
    # logging.info("Установлен таймаут: 10 секунд")

    logging.info("Запуск краулера...")
    crawler.crawl()
    logging.info("Работа краулера завершена")


if __name__ == '__main__':
    main()