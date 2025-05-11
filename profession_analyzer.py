import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
import random
import pandas as pd
from urllib.parse import quote
from typing import List, Dict, Tuple, Set, Optional, Any
from datetime import datetime
import urllib.parse

class ProfessionAnalyzer:
    """
    Класс для анализа профессий на основе данных из интернета.
    Ищет информацию о навыках, связанных с конкретной профессией 
    путем анализа релевантных интернет-ресурсов.
    """
    
    def __init__(self, cache_dir: str = 'cache'):
        """
        Инициализация анализатора профессий.
        
        Args:
            cache_dir: Директория для кэширования результатов
        """
        self.cache_dir = cache_dir
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
        ]
        
        # Словарь соответствия профессий категориям
        self.profession_categories = {
            'программист': 'IT',
            'разработчик': 'IT',
            'frontend': 'IT',
            'бэкенд': 'IT',
            'аналитик': 'IT',
            'тестировщик': 'IT',
            'devops': 'IT',
            
            'врач': 'медицина',
            'медсестра': 'медицина',
            'фармацевт': 'медицина',
            'лаборант': 'медицина',
            'стоматолог': 'медицина',
            
            'учитель': 'образование',
            'преподаватель': 'образование',
            'воспитатель': 'образование',
            'педагог': 'образование',
            
            'экономист': 'финансы',
            'бухгалтер': 'финансы',
            'финансист': 'финансы',
            'банкир': 'финансы',
            
            'маркетолог': 'маркетинг',
            'менеджер': 'менеджмент',
            'hr': 'HR',
            'рекрутер': 'HR',
            
            'юрист': 'право',
            'адвокат': 'право',
            
            'повар': 'кулинария',
            'официант': 'сервис',
            'бармен': 'сервис',
            
            'водитель': 'транспорт',
            'механик': 'транспорт',
            
            'журналист': 'медиа',
            'редактор': 'медиа',
            
            'дизайнер': 'дизайн',
            'художник': 'искусство',
            'фотограф': 'медиа'
        }
        
        # Списки базовых источников для различных категорий профессий
        self.base_sources = {
            'IT': ['hh.ru', 'habr.com', 'tproger.ru', 'geekbrains.ru', 'proglib.io'],
            'медицина': ['medspecial.ru', 'medvestnik.ru', 'vrachirf.ru', 'medicalc.ru', 'zdrav.ru'],
            'образование': ['ucheba.ru', 'pedsovet.org', 'educom.ru', 'prosv.ru', 'iro.ru'],
            'финансы': ['finans.ru', 'rbc.ru', 'banki.ru', 'expert.ru', 'cfin.ru'],
            'маркетинг': ['sostav.ru', 'cossa.ru', 'adindex.ru', 'marketologi.ru', 'spark.ru'],
            'менеджмент': ['e-xecutive.ru', 'hrm.ru', 'gd.ru', 'management.com.ua', 'pmmagazine.ru'],
            'право': ['pravo.ru', 'zakon.ru', 'consultant.ru', 'garant.ru', 'academia-moscow.ru'],
            'HR': ['hr-portal.ru', 'hh.ru', 'hr-journal.ru', 'hr-director.ru', 'hrtime.ru'],
            'кулинария': ['povarenok.ru', 'eda.ru', 'gotovim.ru', 'chefmarket.ru', 'gastronom.ru'],
            'сервис': ['restoclub.ru', 'restoranoff.ru', 'horeca-magazine.ru', 'servicology.ru', 'restoran.ru'],
            'транспорт': ['trucksales.ru', 'avtosreda.ru', 'transport-info.ru', 'os1.ru', 'wiki-motors.ru'],
            'медиа': ['mediajobs.ru', 'jrnlst.ru', 'journalist-virt.ru', 'jourmedia.ru', 'mediakritika.ru'],
            'дизайн': ['designspb.ru', 'designet.ru', 'kak.ru', 'say-hi.me', 'skillbox.ru'],
            'искусство': ['artinvestment.ru', 'artguide.com', 'artchive.ru', 'art-spb.ru', 'theartnewspaper.ru']
        }
        
        # Паттерны для извлечения навыков
        self.skill_patterns = [
            r'навыки[:\s]+([^\.;!?]+)[\.;!?]',
            r'требования[:\s]+([^\.;!?]+)[\.;!?]',
            r'умения[:\s]+([^\.;!?]+)[\.;!?]',
            r'компетенции[:\s]+([^\.;!?]+)[\.;!?]',
            r'[Дд]олжен (?:уметь|знать|владеть)[:\s]+([^\.;!?]+)[\.;!?]',
            r'[Оо]пыт работы[:\s]+([^\.;!?]+)[\.;!?]',
            r'[Хх]орошее знание[:\s]+([^\.;!?]+)[\.;!?]',
            r'[Зз]нание[:\s]+([^\.;!?]+)[\.;!?]',
            r'[Вв]ладение[:\s]+([^\.;!?]+)[\.;!?]',
            r'[Нн]еобходимые качества[:\s]+([^\.;!?]+)[\.;!?]',
            r'[Лл]ичностные качества[:\s]+([^\.;!?]+)[\.;!?]'
        ]
        
        # Маркеры для разделения навыков
        self.skill_separators = [',', ';', '•', '·', '—', '-', '–']
        
        # Стоп-слова для фильтрации
        self.stop_words = ['должен', 'требуется', 'необходимо', 'обязательно', 'желательно',
                           'приветствуется', 'а также', 'и', 'или', 'либо', 'не менее',
                           'от', 'до', 'рублей', 'р.', 'руб', '₽', '$', 'зарплата', 'опыт']
        
        # Создаем директорию для кэширования, если её нет
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def find_category(self, profession):
        """Определение категории профессии"""
        profession_lower = profession.lower()
        
        # Проверяем прямое соответствие
        for prof, category in self.profession_categories.items():
            if prof in profession_lower:
                return category
        
        # Если прямого соответствия не найдено, используем поиск
        return self._search_profession_category(profession)
    
    def find_profession_type(self, profession):
        """
        Определяет тип профессии по её названию с использованием ключевых слов.
        
        Args:
            profession (str): Название профессии
            
        Returns:
            str: Тип профессии (IT, финансы, медицина и т.д.)
        """
        # Преобразуем название профессии в нижний регистр для сравнения
        profession_lower = profession.lower()
        
        # Словарь типов профессий с ключевыми словами
        profession_keywords = {
            'IT': ['программист', 'разработчик', 'devops', 'frontend', 'backend', 'верстальщик', 
                   'тестировщик', 'qa', 'data scientist', 'аналитик данных', 'системный администратор', 
                   'cto', 'инженер', 'web', 'mobile', 'javascript', 'python', 'java', 'c++', 'c#', 
                   'php', 'android', 'ios', 'fullstack', 'ai', 'ml', 'devsecops', 'ui/ux'],
                   
            'финансы': ['бухгалтер', 'финансист', 'финансовый', 'аудитор', 'экономист', 
                        'банкир', 'трейдер', 'инвестиционный', 'казначей', 'кредитный', 'финансовый аналитик'],
                        
            'медицина': ['врач', 'медсестра', 'фармацевт', 'терапевт', 'хирург', 'стоматолог', 'педиатр', 
                         'психолог', 'психиатр', 'невролог', 'фельдшер', 'кардиолог', 'онколог', 'ветеринар'],
                         
            'маркетинг': ['маркетолог', 'smm', 'seo', 'медиа', 'pr', 'контекстолог', 'копирайтер', 
                          'таргетолог', 'бренд', 'продвижение', 'реклама', 'маркетинговый'],
                          
            'менеджмент': ['менеджер', 'руководитель', 'директор', 'управляющий', 'заведующий', 
                           'администратор', 'супервайзер', 'координатор', 'ceo', 'coo', 'проджект-менеджер'],
                           
            'продажи': ['продавец', 'sales', 'менеджер по продажам', 'торговый', 'консультант', 
                        'агент по продажам', 'представитель', 'кассир', 'merchandiser', 'продающий'],
                        
            'дизайн': ['дизайнер', 'художник', 'иллюстратор', 'графический', 'промышленный дизайн', 
                      'ui', 'ux', 'веб-дизайнер', 'motion', 'анимация', 'фотограф', 'креативный'],
                      
            'образование': ['учитель', 'преподаватель', 'педагог', 'воспитатель', 'тренер', 
                           'репетитор', 'методист', 'куратор', 'наставник', 'лектор', 'инструктор'],
                           
            'юриспруденция': ['юрист', 'адвокат', 'нотариус', 'прокурор', 'судья', 'юрисконсульт', 
                             'юридический', 'compliance', 'legal', 'арбитраж', 'правовой']
        }
        
        # Проверяем прямое соответствие в нашем словаре категорий профессий
        category = self.find_category(profession)
        if category and category in profession_keywords:
            return category
            
        # Если категория не найдена или не в нашем словаре ключевых слов,
        # ищем совпадения с ключевыми словами по типам профессий
        for prof_type, keywords in profession_keywords.items():
            for keyword in keywords:
                if keyword in profession_lower:
                    return prof_type
        
        # По умолчанию возвращаем "другое"
        return "другое"
    
    def _search_profession_category(self, profession):
        """Поиск категории профессии через запрос в интернет"""
        try:
            query = f"{profession} профессия категория"
            search_url = f"https://www.google.com/search?q={quote(query)}"
            
            headers = {'User-Agent': random.choice(self.user_agents)}
            response = requests.get(search_url, headers=headers)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Анализируем результаты поиска
            results = soup.find_all('div', attrs={'class': 'g'})
            
            categories_score = Counter()
            for result in results:
                text = result.get_text().lower()
                for category in self.base_sources.keys():
                    if category.lower() in text:
                        categories_score[category] += 1
            
            # Возвращаем наиболее вероятную категорию
            if categories_score:
                return categories_score.most_common(1)[0][0]
            
            return None
        except Exception as e:
            print(f"Ошибка при определении категории профессии: {e}")
            return None
    
    def get_search_queries(self, profession, region=''):
        """Формирование поисковых запросов для профессии"""
        queries = [
            f"{profession} необходимые навыки",
            f"{profession} требования к специалисту",
            f"{profession} профессиональные компетенции",
            f"{profession} что должен знать и уметь",
            f"{profession} обязанности и требования",
            f"{profession} образование {region}",
            f"{profession} образование {region} курсы",
            f"{profession} образование {region} онлайн",
            f"{profession} образование {region} заочно",
            f"{profession} образование {region} дистанционно"
        ]
        return queries
    
    def find_relevant_sources(self, profession, limit=5):
        """
        Находит релевантные источники информации о профессии в интернете.
        
        Args:
            profession (str): Название профессии для поиска.
            limit (int): Максимальное количество источников для возврата.
            
        Returns:
            list: Список URL релевантных источников.
        """
        try:
            # Формируем список различных поисковых запросов для более широкого охвата
            search_queries = [
                f"{profession} описание профессии",
                f"{profession} требуемые навыки",
                f"{profession} как стать",
                f"{profession} обучение",
                f"{profession} википедия",
                f"{profession} карьерный путь",
                f"{profession} обязанности",
                f"что должен знать {profession}",
                f"{profession} технологии 2023",
                f"{profession} учебные ресурсы",
                f"{profession} roadmap"
            ]
            
            all_results = []
            prioritized_domains = [
                'wikipedia.org',
                'habr.com',
                'github.com',
                'stackoverflow.com',
                'medium.com',
                'geeksforgeeks.org',
                'javatpoint.com',
                'tutorialspoint.com',
                'w3schools.com',
                'edu.', # Образовательные учреждения
                'skillbox.ru',
                'skillsetter.io',
                'hh.ru',
                'career.habr.com',
                'tproger.ru',
                'code.org',
                'edx.org',
                'coursera.org',
                'udemy.com',
                'stepik.org',
                'practicum.yandex.ru',
                'codecademy.com',
                'freecodecamp.org'
            ]
            
            # Выполняем поиск по каждому запросу
            for query in search_queries:
                try:
                    # Используем Google Custom Search API или BeautifulSoup для парсинга результатов
                    # В этой реализации будем использовать парсинг с помощью BeautifulSoup
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        search_results = soup.find_all('a')
                        
                        # Извлекаем URL из результатов поиска
                        for result in search_results:
                            href = result.get('href', '')
                            # Фильтруем URL результатов поиска
                            if href.startswith('/url?q='):
                                # Извлекаем URL из параметра q
                                url = href.split('/url?q=')[1].split('&')[0]
                                # Декодируем URL
                                url = urllib.parse.unquote(url)
                                
                                # Проверяем URL на валидность и релевантность
                                if self._is_valid_url(url) and self._is_relevant_url(url, profession):
                                    all_results.append(url)
                
                    # Пауза между запросами чтобы не нагружать сервер
                    time.sleep(1)
                except Exception as e:
                    print(f"Ошибка при выполнении поискового запроса '{query}': {str(e)}")
                    continue
            
            # Удаляем дубликаты URL
            unique_results = list(dict.fromkeys(all_results))
            
            # Сортируем результаты, отдавая приоритет определенным доменам
            prioritized_results = self._prioritize_sources(unique_results, prioritized_domains, profession)
            
            # Возвращаем ограниченное количество источников
            return prioritized_results[:limit]
        except Exception as e:
            print(f"Ошибка при поиске релевантных источников: {str(e)}")
            return []

    def _is_valid_url(self, url):
        """
        Проверяет валидность URL.
        
        Args:
            url (str): URL для проверки.
            
        Returns:
            bool: True, если URL валидный, иначе False.
        """
        # Проверяем, начинается ли URL с http:// или https://
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Исключаем нежелательные домены
        excluded_domains = [
            'translate.google.com',
            'webcache.googleusercontent.com',
            'accounts.google.com',
            'support.google.com',
            'maps.google.com',
            'play.google.com',
            'policies.google.com',
            'docs.google.com',
            'drive.google.com'
        ]
        
        for domain in excluded_domains:
            if domain in url:
                return False
        
        # Проверяем, является ли URL файлом для скачивания
        file_extensions = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.zip', '.rar', '.7z']
        if any(url.lower().endswith(ext) for ext in file_extensions):
            return False
        
        return True

    def _is_relevant_url(self, url, profession):
        """
        Проверяет релевантность URL для заданной профессии.
        
        Args:
            url (str): URL для проверки.
            profession (str): Название профессии.
            
        Returns:
            bool: True, если URL релевантен, иначе False.
        """
        # Извлекаем домен из URL
        domain = urllib.parse.urlparse(url).netloc.lower()
        
        # Исключаем социальные сети и форумы общего назначения, 
        # где информация может быть не очень структурированной
        excluded_social_domains = [
            'facebook.com',
            'twitter.com',
            'instagram.com',
            'vk.com',
            'ok.ru',
            'tiktok.com',
            'snapchat.com'
        ]
        
        if any(social_domain in domain for social_domain in excluded_social_domains):
            return False
        
        # Считаем URL релевантным, если он содержит название профессии в пути
        path = urllib.parse.urlparse(url).path.lower()
        profession_terms = profession.lower().split()
        
        # Проверяем, содержит ли путь URL термины из названия профессии
        return any(term in path for term in profession_terms)

    def _prioritize_sources(self, urls, prioritized_domains, profession):
        """
        Сортирует URL-адреса, отдавая приоритет определенным доменам и релевантности.
        
        Args:
            urls (list): Список URL для сортировки.
            prioritized_domains (list): Список приоритетных доменов.
            profession (str): Название профессии для проверки релевантности.
            
        Returns:
            list: Отсортированный список URL.
        """
        # Создаем словарь для хранения оценок URL
        url_scores = {}
        
        for url in urls:
            score = 0
            domain = urllib.parse.urlparse(url).netloc.lower()
            
            # Повышаем оценку за приоритетные домены
            for idx, prioritized_domain in enumerate(prioritized_domains):
                if prioritized_domain in domain:
                    # Чем выше в списке приоритетных доменов, тем выше оценка
                    score += len(prioritized_domains) - idx
                    break
            
            # Повышаем оценку, если URL содержит название профессии
            path = urllib.parse.urlparse(url).path.lower()
            profession_terms = profession.lower().split()
            for term in profession_terms:
                if term in path:
                    score += 2
            
            # Повышаем оценку для URL с определенными путями
            relevant_paths = ['guide', 'tutorial', 'course', 'learn', 'education', 'skill', 'roadmap', 'wiki', 'article', 'blog']
            for relevant_path in relevant_paths:
                if relevant_path in path:
                    score += 1
            
            # Добавляем оценку в словарь
            url_scores[url] = score
        
        # Сортируем URL по оценке (по убыванию)
        sorted_urls = sorted(urls, key=lambda url: url_scores.get(url, 0), reverse=True)
        
        return sorted_urls

    def search_wikipedia(self, query):
        """
        Ищет релевантные статьи в Википедии.
        
        Args:
            query (str): Поисковый запрос.
            
        Returns:
            list: Список URL статей Википедии.
        """
        try:
            # Формируем URL для поиска в Википедии
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"https://ru.wikipedia.org/w/index.php?search={encoded_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(search_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Проверяем, есть ли прямое перенаправление на статью
            if "search" not in response.url:
                return [response.url]
            
            # Иначе извлекаем результаты поиска
            search_results = []
            for result in soup.select('.mw-search-result-heading a'):
                url = f"https://ru.wikipedia.org{result['href']}"
                search_results.append(url)
            
            return search_results[:3]  # Возвращаем до 3 результатов
        except Exception as e:
            print(f"Ошибка при поиске в Википедии: {e}")
            return []

    def filter_relevant_urls(self, urls, query):
        """
        Фильтрует URLs по релевантности запросу.
        
        Args:
            urls (list): Список URL для фильтрации.
            query (str): Исходный запрос.
            
        Returns:
            list: Отфильтрованный список URL.
        """
        query_terms = set(query.lower().split())
        filtered_urls = []
        
        # Нежелательные домены или ключевые слова в URL
        blacklist = ['youtube.com', 'facebook.com', 'instagram.com', 'twitter.com']
        
        for url in urls:
            # Проверяем, не содержит ли URL нежелательные домены
            if any(domain in url for domain in blacklist):
                continue
            
            # Проверяем релевантность URL запросу
            url_path = urllib.parse.urlparse(url).path.lower()
            url_terms = set(re.findall(r'[a-zA-Zа-яА-Я0-9]+', url_path))
            
            # Если в URL есть хотя бы одно слово из запроса, считаем его релевантным
            if query_terms & url_terms or any(term in url.lower() for term in query_terms):
                filtered_urls.append(url)
            else:
                # Если нет совпадений в URL, добавляем его в конец списка (менее приоритетный)
                filtered_urls.append(url)
        
        return filtered_urls
    
    def extract_data_from_url(self, url):
        """
        Извлекает информацию о профессии из указанного URL.
        
        Args:
            url (str): URL для извлечения данных.
            
        Returns:
            dict: Словарь с извлеченными данными (описание, навыки, обучение и т.д.).
        """
        try:
            if not url or not isinstance(url, str):
                return {"error": "Недопустимый URL", "content": ""}
                
            # Инициализируем результаты
            result = {
                "source": url,
                "title": "",
                "description": "",
                "skills": {},
                "education": [],
                "career_path": [],
                "trends": [],
                "content": "",
                "source_type": "general"  # По умолчанию
            }
            
            # Определяем тип источника
            domain = urllib.parse.urlparse(url).netloc.lower()
            
            if 'wikipedia.org' in domain:
                result["source_type"] = "wiki"
            elif any(edu_domain in domain for edu_domain in ['coursera', 'udemy', 'stepik', 'skillbox', 'practicum', 'geekbrains']):
                result["source_type"] = "education"
            elif any(tech_domain in domain for tech_domain in ['habr', 'medium', 'stackoverflow', 'github']):
                result["source_type"] = "tech_community"
            elif 'hh.ru' in domain or 'career' in domain or 'job' in domain:
                result["source_type"] = "job_portal"
                
            # Отправляем запрос для получения HTML-страницы
            headers = {
                'User-Agent': random.choice(self.user_agents)
            }
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return {"error": f"Ошибка запроса: {response.status_code}", "content": ""}
                
            # Определяем кодировку страницы
            if 'charset' in response.headers.get('Content-Type', ''):
                encoding = response.encoding
            else:
                # Пытаемся определить кодировку из содержимого
                encoding = response.apparent_encoding
                
            # Парсим HTML
            soup = BeautifulSoup(response.content, 'html.parser', from_encoding=encoding)
            
            # Удаляем ненужные элементы
            for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
                
            # Извлекаем заголовок страницы
            title_tag = soup.find('title')
            if title_tag:
                result["title"] = title_tag.text.strip()
                
            # Предварительная обработка в зависимости от типа источника
            if result["source_type"] == "wiki":
                return self._extract_from_wiki(soup, result)
            elif result["source_type"] == "education":
                return self._extract_from_education(soup, result)
            elif result["source_type"] == "tech_community":
                return self._extract_from_tech_community(soup, result)
            elif result["source_type"] == "job_portal":
                return self._extract_from_job_portal(soup, result)
            else:
                return self._extract_from_general(soup, result)
                
        except Exception as e:
            print(f"Ошибка при извлечении данных из URL {url}: {str(e)}")
            return {"error": f"Ошибка при обработке: {str(e)}", "content": ""}
        
    def _extract_from_wiki(self, soup, result):
        """
        Извлекает информацию из страницы Википедии.
        
        Args:
            soup (BeautifulSoup): Объект BeautifulSoup с HTML-контентом.
            result (dict): Словарь для заполнения данными.
            
        Returns:
            dict: Обновленный словарь с извлеченными данными.
        """
        try:
            # Извлекаем основное содержимое
            content_div = soup.find('div', {'id': 'mw-content-text'})
            if content_div:
                # Извлекаем первый параграф (обычно содержит краткое описание)
                first_p = content_div.find('p', recursive=False)
                if first_p:
                    result["description"] = first_p.text.strip()
                    
                # Ищем секции, связанные с навыками, образованием и карьерой
                for heading in content_div.find_all(['h1', 'h2', 'h3']):
                    heading_text = heading.text.strip().lower()
                    
                    # Ищем разделы, связанные с навыками и компетенциями
                    if any(term in heading_text for term in ['навык', 'требован', 'компетенц', 'умени', 'знани']):
                        skills_section = self._extract_section_content(heading)
                        skills = self.extract_skills_from_text(skills_section)
                        result["skills"] = skills
                        
                    # Ищем разделы, связанные с образованием
                    elif any(term in heading_text for term in ['образован', 'обучени', 'курс', 'подготовк']):
                        education_section = self._extract_section_content(heading)
                        result["education"].append(education_section)
                        
                    # Ищем разделы, связанные с карьерой
                    elif any(term in heading_text for term in ['карьер', 'должност', 'профессиональ', 'рост', 'развити']):
                        career_section = self._extract_section_content(heading)
                        result["career_path"].append(career_section)
                        
                    # Ищем разделы, связанные с трендами и перспективами
                    elif any(term in heading_text for term in ['тренд', 'тенденц', 'перспектив', 'будущ', 'технолог']):
                        trends_section = self._extract_section_content(heading)
                        result["trends"].append(trends_section)
                        
            # Собираем весь чистый текст для общего анализа
            result["content"] = ' '.join([p.text.strip() for p in soup.find_all('p') if p.text.strip()])
            
            # Если не нашли навыки в специальных разделах, извлекаем их из всего контента
            if not result["skills"]:
                result["skills"] = self.extract_skills_from_text(result["content"])
            
            return result
        except Exception as e:
            print(f"Ошибка при извлечении данных из Wiki: {str(e)}")
            result["error"] = f"Ошибка при обработке Wiki: {str(e)}"
            return result
        
    def _extract_from_education(self, soup, result):
        """
        Извлекает информацию из образовательных платформ.
        
        Args:
            soup (BeautifulSoup): Объект BeautifulSoup с HTML-контентом.
            result (dict): Словарь для заполнения данными.
            
        Returns:
            dict: Обновленный словарь с извлеченными данными.
        """
        try:
            # Ищем описание курса/программы
            description_candidates = [
                soup.find('meta', {'name': 'description'}),
                soup.find('meta', {'property': 'og:description'})
            ]
            
            for candidate in description_candidates:
                if candidate and candidate.get('content'):
                    result["description"] = candidate.get('content').strip()
                    break
                    
            # Ищем информацию о навыках
            skills_sections = []
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                heading_text = heading.text.strip().lower()
                if any(term in heading_text for term in ['навык', 'научитесь', 'skill', 'умени', 'компетенц']):
                    next_el = heading.find_next(['p', 'ul', 'ol', 'div'])
                    if next_el:
                        skills_sections.append(next_el.text.strip())
                        
            # Извлекаем навыки из найденных секций
            all_skills_text = ' '.join(skills_sections)
            if all_skills_text:
                result["skills"] = self.extract_skills_from_text(all_skills_text)
                
            # Собираем информацию о программе обучения
            program_sections = []
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                heading_text = heading.text.strip().lower()
                if any(term in heading_text for term in ['програм', 'curriculum', 'модул', 'план', 'занятия']):
                    program_section = self._extract_section_content(heading)
                    program_sections.append(program_section)
                    
            result["education"] = program_sections
            
            # Ищем информацию о трудоустройстве и карьере
            career_sections = []
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                heading_text = heading.text.strip().lower()
                if any(term in heading_text for term in ['карьер', 'трудоустрой', 'работ', 'вакансии']):
                    career_section = self._extract_section_content(heading)
                    career_sections.append(career_section)
                    
            result["career_path"] = career_sections
            
            # Собираем весь чистый текст для общего анализа
            result["content"] = ' '.join([p.text.strip() for p in soup.find_all('p') if p.text.strip()])
            
            # Если не нашли навыки в специальных разделах, извлекаем их из всего контента
            if not result["skills"]:
                result["skills"] = self.extract_skills_from_text(result["content"])
            
            return result
        except Exception as e:
            print(f"Ошибка при извлечении данных из образовательной платформы: {str(e)}")
            result["error"] = f"Ошибка при обработке образовательной платформы: {str(e)}"
            return result
        
    def _extract_from_tech_community(self, soup, result):
        """
        Извлекает информацию из технических сообществ и блогов.
        
        Args:
            soup (BeautifulSoup): Объект BeautifulSoup с HTML-контентом.
            result (dict): Словарь для заполнения данными.
            
        Returns:
            dict: Обновленный словарь с извлеченными данными.
        """
        try:
            # Находим основной контент статьи
            article_containers = [
                soup.find('article'),
                soup.find('div', {'class': ['post', 'article', 'content', 'post-content']}),
                soup.find('div', {'id': ['article', 'post', 'content', 'post-content']})
            ]
            
            article = next((container for container in article_containers if container), None)
            
            if article:
                # Извлекаем первый параграф как описание
                first_p = article.find('p')
                if first_p:
                    result["description"] = first_p.text.strip()
                    
                # Извлекаем навыки из всего текста статьи
                article_text = article.text.strip()
                result["skills"] = self.extract_skills_from_text(article_text)
                
                # Ищем секции о карьере и трендах
                for heading in article.find_all(['h1', 'h2', 'h3', 'h4']):
                    heading_text = heading.text.strip().lower()
                    
                    if any(term in heading_text for term in ['карьер', 'путь', 'рост', 'позиц']):
                        career_section = self._extract_section_content(heading)
                        result["career_path"].append(career_section)
                        
                    elif any(term in heading_text for term in ['тренд', 'будущ', 'развит', 'перспектив']):
                        trends_section = self._extract_section_content(heading)
                        result["trends"].append(trends_section)
                        
                # Собираем весь текст статьи
                result["content"] = article_text
            else:
                # Если не найден контейнер статьи, собираем весь текст со страницы
                result["content"] = ' '.join([p.text.strip() for p in soup.find_all('p') if p.text.strip()])
                result["skills"] = self.extract_skills_from_text(result["content"])
                
            return result
        except Exception as e:
            print(f"Ошибка при извлечении данных из технического сообщества: {str(e)}")
            result["error"] = f"Ошибка при обработке технического сообщества: {str(e)}"
            return result
        
    def _extract_from_job_portal(self, soup, result):
        """
        Извлекает информацию из порталов с вакансиями.
        
        Args:
            soup (BeautifulSoup): Объект BeautifulSoup с HTML-контентом.
            result (dict): Словарь для заполнения данными.
            
        Returns:
            dict: Обновленный словарь с извлеченными данными.
        """
        try:
            # Для HeadHunter (hh.ru)
            if 'hh.ru' in result['source']:
                # Ищем описание вакансии
                description_div = soup.find('div', {'data-qa': 'vacancy-description'})
                if description_div:
                    result["description"] = description_div.text.strip()
                    
                    # Извлекаем навыки из описания
                    result["skills"] = self.extract_skills_from_text(result["description"])
                    
            # Ищем ключевые навыки
            skills_div = soup.find('div', {'class': 'bloko-tag-list'})
            if skills_div:
                skills_tags = skills_div.find_all('span', {'class': 'bloko-tag__section'})
                skills_from_tags = []
                for tag in skills_tags:
                    skill = tag.text.strip()
                    if skill:
                        skills_from_tags.append(skill)
                
                if skills_from_tags:
                    # Если у нас уже есть навыки из описания, добавляем навыки из тегов
                    # в категорию "прочие", иначе создаем новый словарь навыков
                    if result["skills"]:
                        other_skills = result["skills"].get("прочие", [])
                        other_skills.extend(skills_from_tags)
                        result["skills"]["прочие"] = list(set(other_skills))
                    else:
                        result["skills"] = {
                            "технические": [],
                            "soft_skills": [],
                            "языки": [],
                            "инструменты": [],
                            "прочие": skills_from_tags
                        }
                        
            # Ищем требования к образованию
            education_section = ""
            for keyword in ["высшее образование", "образование", "университет", "диплом", "степень"]:
                if keyword in result["description"].lower():
                    # Извлекаем предложение, содержащее ключевое слово
                    sentences = re.split(r'[.!?]', result["description"])
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            education_section += sentence.strip() + ". "
                            
            if education_section:
                result["education"].append(education_section)

            return result
        except Exception as e:
            print(f"Ошибка при извлечении данных из портала вакансий: {str(e)}")
            result["error"] = f"Ошибка при обработке портала вакансий: {str(e)}"
            return result

    def generate_skill_description(self, skills, profession):
        """
        Генерирует расширенные описания для навыков на основе контекста профессии.
        
        Args:
            skills (list): Список навыков для генерации описаний.
            profession (str): Профессия для контекста.
            
        Returns:
            dict: Словарь с расширенными описаниями навыков.
        """
        cache_file = os.path.join(self.cache_dir, f"skills_desc_{profession.replace(' ', '_')}.json")
        
        # Проверяем кэш
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                # Если все нужные навыки уже в кэше, возвращаем их
                if all(skill in cached_data for skill in skills):
                    return {skill: cached_data[skill] for skill in skills}
        else:
            cached_data = {}
        
        result = {}
        
        # Шаблоны описаний для различных типов навыков
        skill_templates = {
            'технические': [
                "Позволяет {профессия} эффективно {действие} в рабочем процессе.",
                "Необходим для {действие}, что является ключевым в работе {профессия}.",
                "Обеспечивает возможность {действие}, критично важно для профессионального {профессия}.",
                "Дает преимущество при {действие}, что ценится работодателями в сфере для {профессия}."
            ],
            'языки_программирования': [
                "Используется для {действие}, что является частью повседневных задач {профессия}.",
                "Позволяет {действие}, что необходимо для решения специализированных задач {профессия}.",
                "Применяется при {действие}, без чего невозможно эффективно работать {профессия}.",
                "Важен для {действие}, особенно в проектах, где {профессия} работает с {контекст}."
            ],
            'мягкие': [
                "Помогает {профессия} эффективно {действие} в рабочем коллективе.",
                "Позволяет {профессия} успешно {действие} при взаимодействии с {контекст}.",
                "Критично важно для {профессия}, так как часто требуется {действие}.",
                "Работодатели в этой сфере ценят специалистов, способных {действие}."
            ]
        }
        
        # Действия для различных типов навыков
        skill_actions = {
            'технические': [
                "решать сложные технические задачи", "оптимизировать рабочие процессы",
                "работать с профессиональным инструментарием", "автоматизировать рутинные операции",
                "анализировать технические данные", "создавать качественные продукты",
                "внедрять современные технологии", "поддерживать технические системы"
            ],
            'языки_программирования': [
                "разрабатывать программные решения", "писать эффективный и поддерживаемый код",
                "создавать масштабируемые приложения", "оптимизировать производительность систем",
                "интегрировать различные компоненты ПО", "реализовывать алгоритмы и структуры данных",
                "поддерживать и развивать существующие системы", "автоматизировать бизнес-процессы"
            ],
            'мягкие': [
                "взаимодействовать в команде", "решать конфликтные ситуации",
                "презентовать результаты работы", "адаптироваться к изменениям",
                "управлять приоритетами и временем", "эффективно коммуницировать с клиентами",
                "принимать взвешенные решения", "генерировать креативные идеи",
                "мотивировать коллег", "нести ответственность за результат"
            ]
        }
        
        # Контексты для различных типов навыков
        skill_contexts = {
            'технические': [
                "современными технологиями", "сложными проектами",
                "высоконагруженными системами", "разнообразными инструментами",
                "техническими ограничениями", "инновационными решениями"
            ],
            'языки_программирования': [
                "базами данных", "frontend-компонентами", "backend-системами",
                "мобильными приложениями", "интеграционными решениями",
                "высоконагруженными сервисами", "микросервисной архитектурой"
            ],
            'мягкие': [
                "клиентами", "командой разработки", "руководством",
                "заказчиками", "партнерами", "менее опытными коллегами",
                "внешними участниками проекта", "представителями смежных отделов"
            ]
        }
        
        # Определяем категории навыков
        technical_skills = ['python', 'java', 'javascript', 'c++', 'c#', 'sql', 'php', 'html', 'css',
                         'git', 'docker', 'kubernetes', 'aws', 'azure', 'excel', 'word', 'photoshop',
                         'illustrator', 'autocad', 'solidworks', 'revit', 'mysql', 'postgresql',
                         'mongodb', 'redis', 'react', 'angular', 'vue', 'django', 'flask', 'spring',
                         'tensorflow', 'pytorch', 'sklearn', 'pandas', 'numpy', 'linux', 'windows',
                         'macos', 'bash', 'powershell', 'jquery', 'bootstrap', 'sass', 'less',
                         'typescript', 'ruby', 'rails', 'laravel', 'symfony', 'node.js']
        
        programming_langs = ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'ruby',
                            'php', 'swift', 'kotlin', 'scala', 'rust', 'perl', 'r', 'matlab',
                            'bash', 'powershell', 'sql', 'nosql']
        
        # Список мягких навыков
        soft_skills = ['коммуникабельность', 'лидерство', 'работа в команде', 'организованность',
                      'ответственность', 'пунктуальность', 'стрессоустойчивость', 'креативность',
                      'обучаемость', 'целеустремленность', 'тайм-менеджмент', 'критическое мышление',
                      'эмоциональный интеллект', 'гибкость', 'адаптивность', 'клиентоориентированность']
        
        # Проверяем каждый навык
        for skill in skills:
            # Если навык уже в кэше, используем его
            if skill in cached_data:
                result[skill] = cached_data[skill]
                continue
            
            # Определяем тип навыка
            if skill.lower() in technical_skills or any(tech in skill.lower() for tech in technical_skills):
                skill_type = 'технические'
            elif skill.lower() in programming_langs or any(lang in skill.lower() for lang in programming_langs):
                skill_type = 'языки_программирования'
            elif skill.lower() in soft_skills:
                skill_type = 'мягкие'
            else:
                skill_type = 'технические'  # По умолчанию считаем навык техническим
            
            # Выбираем случайный шаблон и заполняем его
            template = random.choice(skill_templates[skill_type])
            action = random.choice(skill_actions[skill_type])
            context = random.choice(skill_contexts[skill_type])
            
            description = template.replace('{профессия}', profession)
            description = description.replace('{действие}', action)
            description = description.replace('{контекст}', context)
            
            result[skill] = description
            # Сохраняем в кэш
            cached_data[skill] = description
        
        # Обновляем кэш
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cached_data, f, ensure_ascii=False, indent=2)
        
        return result

    def extract_wikipedia_data(self, profession):
        """
        Извлекает информацию о профессии из Википедии.
        
        Args:
            profession (str): Название профессии для поиска в Википедии.
            
        Returns:
            dict: Словарь с информацией о профессии:
                - description (str): Общее описание профессии.
                - skills (list): Список навыков.
                - education (list): Список образовательных требований.
                - career_path (list): Список карьерных этапов.
                - trends (list): Тренды в профессии.
        """
        try:
            print(f"Поиск информации в Википедии для профессии: {profession}")
            # Проверяем кэш
            cache_file = os.path.join(self.cache_dir, f"wiki_{profession.replace(' ', '_')}.json")
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                        cache_time = os.path.getmtime(cache_file)
                        # Используем кэш, если он не старше 30 дней
                        if time.time() - cache_time < 30 * 24 * 60 * 60:
                            print(f"Используем кэшированные данные из Википедии для профессии {profession}")
                            return cached_data
                except Exception as e:
                    print(f"Ошибка при чтении кэша Википедии для профессии {profession}: {e}")
            
            # Формируем URL для поиска в Википедии
            search_url = f"https://ru.wikipedia.org/w/api.php?action=opensearch&format=json&search={urllib.parse.quote(profession)}&limit=1"
            
            headers = {'User-Agent': random.choice(self.user_agents)}
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Ошибка при поиске в Википедии: {response.status_code}")
                return None
                
            search_data = response.json()
            
            # Проверяем, есть ли результаты поиска
            if not search_data[1] or len(search_data[1]) == 0:
                print(f"Результаты для профессии {profession} не найдены в Википедии")
                return None
                
            # Получаем URL статьи
            article_url = search_data[3][0] if len(search_data[3]) > 0 else None
            
            if not article_url:
                print(f"URL статьи в Википедии для профессии {profession} не найден")
                return None
                
            print(f"Найдена статья в Википедии: {article_url}")
            
            # Получаем содержимое статьи
            article_response = requests.get(article_url, headers=headers, timeout=15)
            
            if article_response.status_code != 200:
                print(f"Ошибка при получении статьи из Википедии: {article_response.status_code}")
                return None
                
            # Парсим HTML-содержимое статьи
            soup = BeautifulSoup(article_response.text, 'html.parser')
            
            # Проверяем, что это действительно статья о профессии
            title = soup.find('h1', {'id': 'firstHeading'})
            if title and not any(keyword in title.text.lower() for keyword in [profession.lower(), 'специалист', 'профессия']):
                related_words = ['работа', 'должность', 'специальность', 'карьера', 'профессия']
                if not any(word in article_response.text.lower() for word in related_words):
                    print(f"Найденная статья, возможно, не относится к профессии {profession}")
                    
            # Извлекаем основной текст статьи
            main_content = soup.find('div', {'id': 'mw-content-text'})
            
            if not main_content:
                print(f"Не удалось найти основной контент статьи для профессии {profession}")
                return None
                
            # Извлекаем первый абзац для описания
            paragraphs = main_content.find_all('p')
            description = ""
            
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 50:  # Берем первый достаточно длинный абзац
                    description = text
                    break
                    
            if not description:
                print(f"Не удалось найти описание для профессии {profession}")
                
            # Извлекаем возможные навыки
            skills = []
            
            # Ищем списки, которые могут содержать навыки
            lists = main_content.find_all(['ul', 'ol'])
            
            skill_keywords = ['навык', 'умени', 'знани', 'владени', 'компетенц', 'требован', 'необходим']
            education_keywords = ['образован', 'обучени', 'квалификац', 'университет', 'специальност', 'степен', 'курс']
            career_keywords = ['карьер', 'должност', 'позици', 'ступен', 'рост', 'продвижен']
            trend_keywords = ['тенденц', 'тренд', 'развити', 'будущ', 'перспектив', 'изменени', 'эволюц']
            
            # Находим заголовки разделов
            headers = main_content.find_all(['h2', 'h3', 'h4'])
            
            education_list = []
            career_path = []
            trends = []
            
            # Проходим по заголовкам и связанному контенту
            for header in headers:
                header_text = header.get_text().lower()
                
                # Находим раздел навыков
                if any(keyword in header_text for keyword in skill_keywords):
                    next_element = header.find_next_sibling()
                    
                    while next_element and next_element.name not in ['h2', 'h3', 'h4']:
                        if next_element.name in ['ul', 'ol']:
                            for li in next_element.find_all('li'):
                                skill_text = li.get_text().strip()
                                if skill_text and len(skill_text) > 3 and skill_text not in skills:
                                    skills.append(skill_text)
                        next_element = next_element.find_next_sibling()
                        
                # Находим раздел образования
                elif any(keyword in header_text for keyword in education_keywords):
                    next_element = header.find_next_sibling()
                    
                    while next_element and next_element.name not in ['h2', 'h3', 'h4']:
                        if next_element.name in ['ul', 'ol']:
                            for li in next_element.find_all('li'):
                                edu_text = li.get_text().strip()
                                if edu_text and len(edu_text) > 3 and edu_text not in education_list:
                                    education_list.append(edu_text)
                        elif next_element.name == 'p':
                            p_text = next_element.get_text().strip()
                            if p_text and any(keyword in p_text.lower() for keyword in education_keywords):
                                education_list.append(p_text)
                        next_element = next_element.find_next_sibling()
                        
                # Находим раздел карьерного пути
                elif any(keyword in header_text for keyword in career_keywords):
                    next_element = header.find_next_sibling()
                    
                    while next_element and next_element.name not in ['h2', 'h3', 'h4']:
                        if next_element.name in ['ul', 'ol']:
                            for li in next_element.find_all('li'):
                                career_text = li.get_text().strip()
                                if career_text and len(career_text) > 3 and career_text not in career_path:
                                    career_path.append(career_text)
                        next_element = next_element.find_next_sibling()
                        
                # Находим раздел трендов
                elif any(keyword in header_text for keyword in trend_keywords):
                    next_element = header.find_next_sibling()
                    
                    while next_element and next_element.name not in ['h2', 'h3', 'h4']:
                        if next_element.name in ['ul', 'ol']:
                            for li in next_element.find_all('li'):
                                trend_text = li.get_text().strip()
                                if trend_text and len(trend_text) > 3 and trend_text not in trends:
                                    trends.append(trend_text)
                        elif next_element.name == 'p':
                            p_text = next_element.get_text().strip()
                            if p_text and any(keyword in p_text.lower() for keyword in trend_keywords):
                                sentences = re.split(r'[.!?]+', p_text)
                                for sentence in sentences:
                                    sent = sentence.strip()
                                    if sent and len(sent) > 20 and any(keyword in sent.lower() for keyword in trend_keywords):
                                        trends.append(sent)
                        next_element = next_element.find_next_sibling()
                        
            # Если мы не нашли навыков в заголовках, ищем их в списках
            if not skills:
                for lst in lists:
                    list_text = lst.get_text().lower()
                    
                    if any(keyword in list_text for keyword in skill_keywords):
                        for li in lst.find_all('li'):
                            skill_text = li.get_text().strip()
                            if skill_text and len(skill_text) > 3 and skill_text not in skills:
                                skills.append(skill_text)
            
            # Пытаемся извлечь навыки из текста, если мы их не нашли в списках
            if not skills:
                skills = self.extract_skills_from_text(description)
                
                # Дополнительно ищем навыки во всем тексте статьи
                full_text = main_content.get_text()
                more_skills = self.extract_skills_from_text(full_text)
                
                for skill in more_skills:
                    if skill not in skills:
                        skills.append(skill)
                    
            # Ограничиваем количество навыков
            skills = skills[:15]
            
            # Собираем результаты
            result = {
                "description": description,
                "skills": skills,
                "education": education_list,
                "career_path": career_path,
                "trends": trends
            }
            
            # Сохраняем результаты в кэш
            try:
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Ошибка при сохранении кэша Википедии для профессии {profession}: {e}")
                
            return result
            
        except Exception as e:
            print(f"Ошибка при извлечении данных из Википедии для профессии {profession}: {e}")
            return None

    def analyze_profession(self, profession, region=None):
        """
        Анализирует профессию, собирая информацию из различных источников.
        
        Args:
            profession (str): Название профессии для анализа.
            region (str, optional): Регион для анализа региональных особенностей.
            
        Returns:
            dict: Словарь с полной информацией о профессии:
                - description (str): Описание профессии.
                - hard_skills (list): Технические навыки.
                - soft_skills (list): Мягкие навыки.
                - education (list): Образовательные пути.
                - career_path (list): Карьерный путь.
                - trends (list): Тренды в профессии.
                - regional_specifics (dict): Региональные особенности (если указан регион).
                - learning_resources (list): Ресурсы для обучения.
                - hard_skills_desc (dict): Расширенные описания жестких навыков.
                - soft_skills_desc (dict): Расширенные описания мягких навыков.
        """
        try:
            print(f"Начинаем анализ профессии: {profession}")
            
            # Проверяем кэш
            cache_file = os.path.join(self.cache_dir, f"{profession.replace(' ', '_')}.json")
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                        cache_time = os.path.getmtime(cache_file)
                        # Используем кэш, если он не старше 7 дней
                        if time.time() - cache_time < 7 * 24 * 60 * 60:
                            print(f"Используем кэшированные данные для профессии {profession}")
                            return cached_data
                except Exception as e:
                    print(f"Ошибка при чтении кэша для профессии {profession}: {e}")
            
            # Инициализируем результат
            result = {
                "description": "",
                "hard_skills": [],
                "soft_skills": [],
                "education": [],
                "career_path": [],
                "trends": [],
                "regional_specifics": {},
                "learning_resources": []
            }
            
            # Получаем данные из Википедии
            print(f"Получаем данные из Википедии для профессии {profession}")
            wiki_data = self.extract_wikipedia_data(profession)
            
            if wiki_data:
                result["description"] = wiki_data.get("description", "")
                
                # Добавляем навыки из Википедии в список жестких навыков
                for skill in wiki_data.get("skills", []):
                    if skill not in result["hard_skills"]:
                        result["hard_skills"].append(skill)
                        
                # Добавляем образовательную информацию
                for edu in wiki_data.get("education", []):
                    if edu not in result["education"]:
                        result["education"].append(edu)
                        
                # Добавляем карьерный путь
                for career in wiki_data.get("career_path", []):
                    if career not in result["career_path"]:
                        result["career_path"].append(career)
                        
                # Добавляем тренды
                for trend in wiki_data.get("trends", []):
                    if trend not in result["trends"]:
                        result["trends"].append(trend)
            
            # Если нет описания, ищем через другие источники
            if not result["description"]:
                print(f"Ищем описание профессии {profession} через поисковые системы")
                search_query = f"{profession} профессия описание"
                try:
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
                    headers = {'User-Agent': random.choice(self.user_agents)}
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Ищем блок с описанием
                        for div in soup.find_all(['div', 'p']):
                            if len(div.text.strip()) > 100 and profession.lower() in div.text.lower():
                                result["description"] = div.text.strip()
                                break
                        
                        # Если не нашли в блоках, ищем URL с описанием
                        if not result["description"]:
                            for link in soup.find_all('a'):
                                href = link.get('href', '')
                                if 'url=' in href and any(domain in href for domain in ['wiki', 'hh.ru', 'superjob', 'proforientator', 'postupi.online']):
                                    matched = re.search(r'url=([^&]+)', href)
                                    if matched:
                                        url = urllib.parse.unquote(matched.group(1))
                                        if url.startswith('http'):
                                            try:
                                                url_data = self.extract_data_from_url(url)
                                                if url_data and url_data.get("description"):
                                                    result["description"] = url_data.get("description")
                                                    break
                                            except Exception as e:
                                                print(f"Ошибка при извлечении описания из URL {url}: {e}")
                except Exception as e:
                    print(f"Ошибка при поиске описания профессии: {e}")
            
            # Если все еще нет описания, используем общее описание
            if not result["description"] or len(result["description"]) < 50:
                result["description"] = f"{profession} - это специалист, который выполняет функции в своей профессиональной области. Профессионалы этого направления обладают специфическими знаниями и навыками, применяемыми в работе для решения различных задач."
            
            # Ищем образовательные ресурсы
            print(f"Ищем образовательные ресурсы для профессии {profession}")
            edu_search_query = f"{profession} курсы обучение"
            try:
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(edu_search_query)}"
                headers = {'User-Agent': random.choice(self.user_agents)}
                response = requests.get(search_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Ищем URL'ы образовательных ресурсов
                    edu_urls = []
                    for link in soup.find_all('a'):
                        href = link.get('href', '')
                        if 'url=' in href and any(domain in href for domain in ['edu', 'курс', 'образование', 'обучение', 'university']):
                            matched = re.search(r'url=([^&]+)', href)
                            if matched:
                                edu_url = urllib.parse.unquote(matched.group(1))
                                if edu_url.startswith('http') and not any(blocked in edu_url for blocked in ['google', 'youtube']):
                                    edu_urls.append(edu_url)
                    
                    # Берем только первые 2 ссылки для анализа
                    for edu_url in edu_urls[:2]:
                        try:
                            edu_data = self.extract_data_from_url(edu_url)
                            if edu_data:
                                result["education"].extend([item for item in edu_data.get("education", []) if item not in result["education"]])
                                result["hard_skills"].extend([item for item in edu_data.get("skills", []) if item not in result["hard_skills"]])
                                result["learning_resources"].append({
                                    "name": edu_data.get("title", "Образовательный ресурс"),
                                    "url": edu_url,
                                    "description": "Образовательный ресурс для получения необходимых навыков"
                                })
                        except Exception as e:
                            print(f"Ошибка при обработке образовательного URL {edu_url}: {e}")
            except Exception as e:
                print(f"Ошибка при поиске образовательных ресурсов: {e}")
                
            # Получаем данные о вакансиях
            print(f"Анализируем вакансии для профессии {profession}")
            job_data = self.search_job_vacancies(profession, region)
            
            if job_data:
                # Добавляем навыки из вакансий
                for skill in job_data.get("hard_skills", []):
                    if skill not in result["hard_skills"]:
                        result["hard_skills"].append(skill)
                
                for skill in job_data.get("soft_skills", []):
                    if skill not in result["soft_skills"]:
                        result["soft_skills"].append(skill)
                    
                # Добавляем тренды из вакансий
                for trend in job_data.get("trends", []):
                    if trend not in result["trends"]:
                        result["trends"].append(trend)
            
            # Если не нашли мягкие навыки, добавим общие
            if not result["soft_skills"]:
                result["soft_skills"] = [
                    "Коммуникабельность",
                    "Работа в команде",
                    "Аналитическое мышление",
                    "Организационные навыки",
                    "Умение решать проблемы",
                    "Самоорганизация",
                    "Адаптивность",
                    "Критическое мышление"
                ]
            
            # Если не нашли достаточно трендов, добавим общие
            if len(result["trends"]) < 3:
                general_trends = [
                    f"Цифровизация процессов в работе {profession}",
                    f"Использование искусственного интеллекта в задачах {profession}",
                    f"Автоматизация рутинных задач {profession}",
                    f"Удаленный формат работы для {profession}",
                    f"Более высокие требования к техническим навыкам {profession}",
                    f"Рост спроса на {profession} с международным опытом"
                ]
                
                # Добавляем общие тренды, которых еще нет в результате
                for trend in general_trends:
                    if trend not in result["trends"]:
                        result["trends"].append(trend)
                        if len(result["trends"]) >= 5:
                            break
            
            # Если не нашли достаточно образовательных путей, добавим общие
            if len(result["education"]) < 2:
                general_education = [
                    f"Высшее образование по специальности, связанной с {profession}",
                    f"Профессиональные курсы повышения квалификации для {profession}",
                    f"Самообразование с использованием онлайн-курсов и специализированной литературы",
                    f"Стажировки в компаниях на позиции {profession}"
                ]
                
                # Добавляем общие образовательные пути
                for edu in general_education:
                    if edu not in result["education"]:
                        result["education"].append(edu)
            
            # Если не нашли карьерный путь, добавим общий
            if not result["career_path"]:
                result["career_path"] = [
                    f"Младший специалист ({profession})",
                    f"Специалист ({profession})",
                    f"Старший специалист ({profession})",
                    f"Ведущий специалист / Руководитель направления"
                ]
            
            # Получаем региональные особенности, если указан регион
            if region:
                print(f"Анализируем региональные особенности для профессии {profession} в регионе {region}")
                region_data = self.get_regional_specifics(profession, region)
                result["regional_specifics"] = region_data
            
            # Создаем более подробные описания для навыков
            if result["hard_skills"]:
                hard_skills_desc = self.generate_skill_description(result["hard_skills"], profession)
                result["hard_skills_desc"] = hard_skills_desc
                
            if result["soft_skills"]:
                soft_skills_desc = self.generate_skill_description(result["soft_skills"], profession)
                result["soft_skills_desc"] = soft_skills_desc
                
            # Дополняем информацию о ресурсах для обучения
            if len(result["learning_resources"]) < 3:
                print(f"Поиск дополнительных обучающих ресурсов для профессии {profession}")
                learning_query = f"{profession} обучение курсы"
                try:
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(learning_query)}"
                    headers = {'User-Agent': random.choice(self.user_agents)}
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        for link in soup.find_all('a'):
                            href = link.get('href', '')
                            if 'url=' in href and not any(blocked in href for blocked in ['google', 'youtube']):
                                matched = re.search(r'url=([^&]+)', href)
                                if matched:
                                    resource_url = urllib.parse.unquote(matched.group(1))
                                    if resource_url.startswith('http'):
                                        # Проверяем, что такого URL еще нет в ресурсах
                                        if not any(resource["url"] == resource_url for resource in result["learning_resources"]):
                                            # Извлекаем заголовок ссылки
                                            title = link.text.strip()
                                            if not title or len(title) < 5:
                                                title = f"Обучающий ресурс по профессии {profession}"
                                            
                                            result["learning_resources"].append({
                                                "name": title,
                                                "url": resource_url,
                                                "description": f"Образовательный ресурс для изучения профессии {profession}"
                                            })
                                            
                                            if len(result["learning_resources"]) >= 3:
                                                break
                except Exception as e:
                    print(f"Ошибка при поиске дополнительных обучающих ресурсов: {e}")
            
            # Сохраняем результаты в кэш
            try:
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Ошибка при сохранении кэша для профессии {profession}: {e}")
                
            print(f"Анализ профессии {profession} завершен успешно")
            return result
        except Exception as e:
            print(f"Ошибка при анализе профессии {profession}: {e}")
            # Возвращаем базовый результат в случае ошибки
            return {
                "description": f"Профессия {profession} - специалист в своей области.",
                "hard_skills": ["Профессиональные навыки", "Специальные знания", "Технические умения"],
                "soft_skills": ["Коммуникабельность", "Работа в команде", "Аналитическое мышление"],
                "education": [f"Высшее образование по специальности, связанной с {profession}"],
                "career_path": [f"Младший специалист ({profession})", f"Специалист ({profession})", f"Старший специалист ({profession})"],
                "trends": [f"Цифровизация процессов в работе {profession}", f"Автоматизация рутинных задач {profession}"],
                "regional_specifics": {"demand_level": "средний"},
                "learning_resources": []
            }


# Пример использования:
if __name__ == "__main__":
    analyzer = ProfessionAnalyzer()
    result = analyzer.analyze_profession("врач", "Москва")
    print("\nРезультаты анализа:")
    print(f"Профессия: врач")
    print(f"Регион: Москва")
    print("\nПрофессиональные навыки:")
    for skill in result['hard_skills']:
        print(f"- {skill}")
    print("\nМягкие навыки:")
    for skill in result['soft_skills']:
        print(f"- {skill}")