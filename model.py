import requests
import re
import random
import pickle
import os
import time
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
import traceback
import logging
import json

# Импортируем класс для работы с локальной моделью
try:
    from llm_integration import LocalLLM
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logging.warning("Модуль llm_integration не найден. Локальная модель LLM не будет использоваться.")

class JobRoadmapGenerator:
    """
    Класс для анализа вакансий и генерации персонализированной дорожной карты
    по освоению определенной профессии в выбранном регионе.
    """
    
    def __init__(self, model_path=None):
        """
        Инициализация генератора дорожных карт
        """
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Базовые наборы навыков (используются, если не удается получить данные из интернета)
        self.default_hard_skills = {
            'программист': ['Python', 'SQL', 'Git', 'Алгоритмы и структуры данных', 'API', 'Объектно-ориентированное программирование', 'Docker', 'CI/CD', 'Тестирование'],
            'frontend': ['JavaScript', 'HTML', 'CSS', 'React', 'Git', 'TypeScript', 'Webpack', 'REST API', 'Redux', 'Адаптивная верстка', 'Кросс-браузерная совместимость'],
            'бэкенд': ['Python/Java/C#', 'SQL', 'NoSQL', 'REST API', 'Git', 'Docker', 'Архитектура приложений', 'Оптимизация запросов', 'Многопоточность', 'Микросервисы'],
            'дизайнер': ['Figma', 'Adobe Photoshop', 'Adobe Illustrator', 'UI/UX', 'Прототипирование', 'Анимация', 'Адаптивный дизайн', 'Дизайн-системы', 'Исследование пользователей'],
            'маркетолог': ['SEO', 'SMM', 'Контекстная реклама', 'Аналитика', 'Копирайтинг', 'Email-маркетинг', 'Стратегическое планирование', 'A/B тестирование', 'Маркетинговые исследования'],
            'аналитик': ['SQL', 'Excel', 'Python', 'BI-инструменты', 'Статистика', 'Визуализация данных', 'A/B тестирование', 'Machine Learning', 'Прогнозирование', 'Сегментация'],
            'менеджер': ['Управление проектами', 'Agile/Scrum', 'MS Office', 'CRM', 'Бюджетирование', 'Стратегическое планирование', 'Soft skills', 'Управление персоналом', 'Переговоры']
        }
        
        self.default_soft_skills = [
            'Коммуникабельность', 'Работа в команде', 'Критическое мышление', 
            'Решение проблем', 'Адаптивность', 'Управление временем', 
            'Креативность', 'Эмоциональный интеллект', 'Стрессоустойчивость',
            'Лидерство', 'Самообучение', 'Мультизадачность', 'Проактивность'
        ]
        
        # Региональные особенности
        self.regional_trends = {
            'москва': [
                'Высокая конкуренция требует постоянного совершенствования навыков и специализации',
                'Востребованы знания английского языка для работы в международных компаниях',
                'Акцент на инновационные технологии и стартап-культуру',
                'Активное внедрение AI и machine learning во все сферы деятельности'
            ],
            'санкт-петербург': [
                'Развитие креативных индустрий и IT-сектора',
                'Баланс между классическим подходом и инновациями',
                'Востребованы специалисты с опытом работы в международных проектах',
                'Активное развитие образовательных технологий и финтеха'
            ],
            'новосибирск': [
                'Развитие научно-технологического кластера и сотрудничество с Академгородком',
                'Рост потребности в специалистах по автоматизации и робототехнике',
                'Междисциплинарные проекты на стыке науки и IT',
                'Увеличение числа распределенных команд с головными офисами в Москве'
            ],
            'екатеринбург': [
                'Рост промышленных IT-решений и цифровизация производства',
                'Развитие региональных IT-хабов и сотрудничество с промышленностью',
                'Востребованность навыков в сфере информационной безопасности',
                'Увеличение запроса на специалистов по интеграции систем'
            ],
            'казань': [
                'Активное развитие исламского банкинга и финтех-решений',
                'Государственная поддержка IT-стартапов и образовательных проектов',
                'Рост запроса на двуязычных специалистов (русский/татарский)',
                'Развитие региональных IT-парков и инкубаторов'
            ],
            'россия': [
                'Тренд на импортозамещение программного обеспечения и технологий',
                'Рост спроса на специалистов по информационной безопасности',
                'Увеличение проектов в сфере государственных цифровых услуг',
                'Развитие удаленной работы и распределенных команд'
            ]
        }
        
        # Детальные описания навыков
        self.skill_descriptions = {
            'Python': 'ключевой язык для автоматизации, анализа данных и бэкенд-разработки',
            'SQL': 'необходим для эффективной работы с базами данных и анализа информации',
            'Git': 'позволяет эффективно организовать командную работу над проектами',
            'JavaScript': 'основа современной веб-разработки и интерактивных интерфейсов',
            'HTML': 'фундамент создания веб-страниц и структурирования контента',
            'CSS': 'необходим для стилизации интерфейсов и создания отзывчивого дизайна',
            'React': 'востребованная библиотека для создания динамичных пользовательских интерфейсов',
            'TypeScript': 'повышает надежность кода благодаря статической типизации',
            'Docker': 'позволяет создавать изолированные среды для приложений',
            'REST API': 'стандарт взаимодействия между клиентской и серверной частями',
            'NoSQL': 'позволяет работать с неструктурированными данными в распределенных системах',
            'Agile/Scrum': 'методология для гибкого управления проектами и командной работы',
            'Excel': 'необходим для обработки данных, анализа и визуализации информации',
            'BI-инструменты': 'позволяют преобразовывать данные в наглядные бизнес-отчеты',
            'UI/UX': 'обеспечивает создание понятных и удобных пользовательских интерфейсов',
            'SEO': 'помогает повысить видимость сайтов в поисковых системах',
            'SMM': 'необходим для эффективного продвижения в социальных сетях',
            'Figma': 'современный инструмент для дизайна интерфейсов и прототипирования'
        }
        
        # Инициализация базовых компонентов модели
        self.vectorizer = TfidfVectorizer()
        self.skill_vectors = None
        self.profession_data = {}
        
        # Загрузка модели, если путь указан и файл существует
        if model_path and os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                    if isinstance(data, dict):
                        if 'vectorizer' in data:
                            self.vectorizer = data.get('vectorizer')
                        if 'skill_vectors' in data:
                            self.skill_vectors = data.get('skill_vectors')
                        if 'profession_data' in data:
                            self.profession_data = data.get('profession_data', {})
                print(f"Модель успешно загружена из {model_path}")
            except Exception as e:
                print(f"Ошибка при загрузке модели: {e}. Будет создана новая модель.")
        
        # Сохранение новой модели, если путь указан, но файл не существует
        if model_path and not os.path.exists(model_path):
            self.save_model(model_path)
            print(f"Создана новая модель в {model_path}")
        
        # Проверяем доступность LLM модели и инициализируем ее
        self.llm = None
        self.use_llm = False
        
        if LLM_AVAILABLE:
            try:
                self.llm = LocalLLM(model="qwen3-8b")  # Явно указываем использование модели qwen3-8b
                self.use_llm = True
                logging.info("Локальная LLM модель qwen3-8b успешно инициализирована")
            except Exception as e:
                logging.error(f"Ошибка при инициализации LLM модели: {e}")
    
    def save_model(self, model_path=None):
        """
        Сохранение модели в файл
        """
        if model_path is None:
            # Создаем директорию model, если она не существует
            os.makedirs('model', exist_ok=True)
            model_path = os.path.join('model', 'roadmap_model.pkl')
        
        # Создаем директорию model, если она не существует
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        data = {
            'vectorizer': self.vectorizer,
            'skill_vectors': self.skill_vectors,
            'profession_data': self.profession_data
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"Модель сохранена в {model_path}")
    
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
        
        # Ищем совпадения с ключевыми словами по типам профессий
        for prof_type, keywords in profession_keywords.items():
            for keyword in keywords:
                if keyword in profession_lower:
                    return prof_type
        
        # По умолчанию возвращаем "другое"
        return "другое"
    
    def search_hh_vacancies(self, profession, region=None, limit=5):
        """
        Поиск вакансий на HH.ru по профессии и региону
        
        Args:
            profession (str): Название профессии
            region (str): Название региона (город, область)
            limit (int): Максимальное количество вакансий
            
        Returns:
            list: Список URL вакансий
        """
        try:
            base_url = "https://api.hh.ru/vacancies"
            
            # Подготовка запроса
            params = {
                "text": profession,
                "per_page": limit,
                "page": 0
            }
            
            # Если указан регион, добавляем его в запрос
            if region:
                # Карта кодов популярных регионов (можно расширить)
                region_codes = {
                    "москва": "1",
                    "санкт-петербург": "2",
                    "новосибирск": "4",
                    "екатеринбург": "3",
                    "казань": "88",
                    "нижний новгород": "66",
                    "челябинск": "104",
                    "омск": "68",
                    "самара": "78",
                    "ростов-на-дону": "76",
                    "уфа": "99",
                    "красноярск": "54",
                    "пермь": "72",
                    "воронеж": "26"
                }
                
                # Пытаемся найти код региона
                region_lower = region.lower().strip()
                if region_lower in region_codes:
                    params["area"] = region_codes[region_lower]
                else:
                    # Если регион не найден в нашей карте кодов, делаем дополнительный запрос
                    # для поиска кода региона
                    region_search_url = "https://api.hh.ru/areas"
                    region_response = requests.get(region_search_url, headers=self.headers)
                    
                    if region_response.status_code == 200:
                        all_areas = region_response.json()
                        
                        # Функция для рекурсивного поиска региона
                        def find_area_id(areas, region_name):
                            for area in areas:
                                if region_name.lower() in area['name'].lower():
                                    return area['id']
                                if area.get('areas'):
                                    found_id = find_area_id(area['areas'], region_name)
                                    if found_id:
                                        return found_id
                            return None
                        
                        area_id = find_area_id(all_areas, region_lower)
                        if area_id:
                            params["area"] = area_id
            
            # Добавляем дополнительные параметры для медицинских профессий
            if any(med_term in profession.lower() for med_term in [
                'врач', 'медицин', 'хирург', 'терапевт', 'педиатр', 'стоматолог',
                'кардиолог', 'невролог', 'офтальмолог', 'ортопед', 'онколог',
                'гинеколог', 'дерматолог', 'фельдшер', 'медсестра', 'медбрат',
                'фармацевт', 'лаборант', 'рентгенолог'
            ]):
                # Для медицинских профессий добавляем специальные фильтры
                # Индустрия: Медицина, фармацевтика
                params["industry"] = "12"
                
                # Добавляем профессиональную область: Медицина, фармацевтика
                params["professional_role"] = "17"
            
            # Выполняем запрос
            response = requests.get(base_url, params=params, headers=self.headers)
            
            # Проверяем успешность запроса
            if response.status_code != 200:
                print(f"Ошибка при запросе к API HH: {response.status_code}")
                return []
            
            # Получаем данные
            data = response.json()
            
            # Если нет результатов, попробуем более общий запрос
            if data.get('found', 0) == 0:
                # Упрощаем запрос, убирая специфичные параметры
                if 'industry' in params:
                    del params['industry']
                if 'professional_role' in params:
                    del params['professional_role']
                
                # Делаем запрос с более общими параметрами
                simplified_response = requests.get(base_url, params=params, headers=self.headers)
                if simplified_response.status_code == 200:
                    data = simplified_response.json()
            
            # Извлекаем URL вакансий
            vacancy_urls = []
            for item in data.get('items', []):
                vacancy_urls.append(item['alternate_url'])
                
                # Ограничиваем количество
                if len(vacancy_urls) >= limit:
                    break
            
            print(f"Найдено {len(vacancy_urls)} вакансий для профессии '{profession}'")
            return vacancy_urls
            
        except Exception as e:
            print(f"Ошибка при поиске вакансий: {str(e)}")
            return []
    
    def extract_skills_from_vacancy(self, vacancy_url):
        """
        Извлечение навыков из описания вакансии на HH.ru
        """
        try:
            # Получаем содержимое страницы
            response = requests.get(vacancy_url, headers=self.headers)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Извлекаем текст описания вакансии
            vacancy_description = ""
            description_div = soup.find('div', {'data-qa': 'vacancy-description'})
            if description_div:
                vacancy_description = description_div.get_text()
            
            # Ищем блок с требованиями
            requirements_block = ""
            for block in soup.find_all(['div', 'p', 'ul']):
                text = block.get_text().lower()
                if 'требовани' in text or 'требуется' in text or 'необходимые навыки' in text or 'от вас' in text:
                    requirements_block += block.get_text() + "\n"
            
            # Если блок требований не найден, используем все описание
            if not requirements_block:
                requirements_block = vacancy_description
            
            # Комбинируем текст для анализа
            all_text = requirements_block + "\n" + vacancy_description
            
            # Паттерны для поиска навыков (расширенный список)
            skill_patterns = [
                # Стандартные паттерны
                r'знание\s+([^;,.]+)',
                r'опыт\s+работы\s+с\s+([^;,.]+)',
                r'опыт\s+([^;,.]+)',
                r'навыки\s+([^;,.]+)',
                r'умение\s+([^;,.]+)',
                r'владение\s+([^;,.]+)',
                
                # Добавляем паттерны для медицинских специальностей
                r'диагностика\s+([^;,.]+)',
                r'лечение\s+([^;,.]+)',
                r'опыт\s+проведения\s+([^;,.]+)',
                r'методы\s+([^;,.]+)',
                r'работа\s+с\s+([^;,.]+аппарат[^;,.]+)',
                r'работа\s+с\s+([^;,.]+оборудован[^;,.]+)',
                r'профилактика\s+([^;,.]+)',
                r'([^;,.]+)\s+обследовани[^;,.]+',
                r'([^;,.]+)\s+манипуляци[^;,.]+',
                r'([^;,.]+)\s+терапи[^;,.]+',
                r'([^;,.]+)\s+хирурги[^;,.]+',
                
                # Паттерны для списков навыков
                r'•\s+([^;•]+)',
                r'‣\s+([^;‣]+)',
                r'-\s+([^;-]+)',
                r'◦\s+([^;◦]+)',
                r'✓\s+([^;✓]+)'
            ]
            
            # Поиск медицинских терминов и процедур
            medical_terms = [
                'диагностика', 'терапия', 'хирургия', 'манипуляция', 
                'анализ', 'исследование', 'протокол', 'стандарт', 
                'узи', 'кт', 'мрт', 'экг', 'рентген', 
                'эндоскопия', 'лапароскопия', 'биопсия',
                'реабилитация', 'профилактика', 'консультирование',
                'операция', 'лечение', 'обследование'
            ]
            
            # Извлекаем навыки с использованием регулярных выражений
            skills = []
            
            # Поиск по паттернам
            for pattern in skill_patterns:
                matches = re.finditer(pattern, all_text, re.IGNORECASE)
                for match in matches:
                    skill = match.group(1).strip()
                    # Проверяем длину навыка (слишком короткие или длинные исключаем)
                    if 3 < len(skill) < 100:
                        skills.append(skill)
            
            # Ищем HTML списки с навыками
            ul_lists = soup.find_all('ul')
            for ul in ul_lists:
                items = ul.find_all('li')
                for item in items:
                    item_text = item.get_text().strip()
                    # Проверяем длину и осмысленность текста
                    if 3 < len(item_text) < 100:
                        skills.append(item_text)
            
            # Дополнительный поиск медицинских терминов во всём тексте страницы
            full_page_text = soup.get_text()
            for term in medical_terms:
                # Ищем в контексте фразы, содержащие медицинские термины
                for match in re.finditer(r'[^.;:,]{0,50}' + term + r'[^.;:,]{0,100}', full_page_text, re.IGNORECASE):
                    context = match.group(0).strip()
                    # Проверяем длину контекста
                    if 10 < len(context) < 150:
                        skills.append(context)
            
            # Нормализуем и чистим список навыков
            normalized_skills = []
            for skill in skills:
                # Очищаем от мусора
                skill = re.sub(r'^\s*[-•‣◦✓]\s*', '', skill)
                skill = skill.strip(',.;: ')
                
                # Проверяем минимальную длину и наличие осмысленных символов
                if len(skill) > 3 and re.search(r'[а-яА-Яa-zA-Z]', skill):
                    normalized_skills.append(skill)
            
            # Удаляем дубликаты и сортируем
            unique_skills = list(set(normalized_skills))
            unique_skills.sort()
            
            return unique_skills
        
        except Exception as e:
            print(f"Ошибка при извлечении навыков из вакансии {vacancy_url}: {str(e)}")
            return []

    def generate_skill_description(self, skill, profession):
        """
        Генерация детального описания навыка с учетом профессии
        """
        # Проверяем, есть ли готовое описание для навыка
        if skill in self.skill_descriptions:
            base_description = self.skill_descriptions[skill]
        else:
            # Если нет готового описания, генерируем обобщенное
            base_description = "важный инструмент для профессионального роста"
        
        # Добавляем контекст профессии и значимость
        profession_contexts = {
            'программист': f'для разработки эффективных и масштабируемых приложений',
            'разработчик': f'для создания современного программного обеспечения',
            'frontend': f'для создания современных и интерактивных пользовательских интерфейсов',
            'бэкенд': f'для разработки надежной серверной части приложений',
            'дизайнер': f'для создания привлекательных и удобных интерфейсов',
            'аналитик': f'для проведения глубокого анализа данных и формирования инсайтов',
            'маркетолог': f'для эффективного продвижения продуктов и услуг',
            'менеджер': f'для успешной координации и реализации проектов'
        }
        
        # Определяем подходящий контекст
        context = 'в современной IT-сфере'
        for key, value in profession_contexts.items():
            if key in profession.lower():
                context = value
                break
        
        return f"{base_description}. Этот навык особенно ценен {context}."
    
    def get_region_trends(self, region):
        """
        Получение региональных трендов в зависимости от указанного региона
        """
        region_lower = region.lower()
        
        # Проверяем, есть ли прямое соответствие региону
        for key in self.regional_trends.keys():
            if key in region_lower:
                return self.regional_trends[key]
        
        # Если нет прямого соответствия, возвращаем общероссийские тренды
        return self.regional_trends['россия']
    
    def generate_learning_steps(self, profession, skills, experience_level='junior'):
        """
        Генерация пошагового плана обучения для достижения уровня в профессии
        
        Args:
            profession (str): Название профессии
            skills (list): Список требуемых навыков
            experience_level (str): Уровень опыта (junior, middle, senior)
            
        Returns:
            list: Список шагов обучения с заголовком и описанием
        """
        # Определяем тип профессии для подбора соответствующих рекомендаций
        profession_type = self.find_profession_type(profession)
        
        # Выбираем количество месяцев для разных уровней опыта
        timeline_months = {
            'junior': 6,
            'middle': 12,
            'senior': 18
        }.get(experience_level.lower(), 6)
        
        # Отбираем наиболее важные навыки для изучения
        if len(skills) > 5:
            selected_skills = skills[:5]
        else:
            selected_skills = skills
            
        # Шаблоны для описания процесса обучения
        learning_templates = {
            'it': [
                "Изучение {skill} через практические проекты и задачи",
                "Освоение {skill} с использованием онлайн-курсов и документации",
                "Практическое применение {skill} в учебных проектах",
                "Углубленное понимание {skill} через решение практических задач",
                "Разработка собственных проектов с использованием {skill}"
            ],
            'финансы': [
                "Изучение основ {skill} и их применение в финансовом анализе",
                "Применение {skill} в моделировании финансовых процессов",
                "Решение практических кейсов по {skill}",
                "Анализ реальных ситуаций с применением {skill}",
                "Построение сложных финансовых моделей с использованием {skill}"
            ],
            'медицина': [
                "Изучение теоретических основ {skill} и клинических случаев",
                "Практическое применение {skill} в симулированных условиях",
                "Наблюдение за применением {skill} у опытных специалистов",
                "Ассистирование при применении {skill} под наблюдением",
                "Самостоятельное применение {skill} и анализ результатов"
            ],
            'маркетинг': [
                "Изучение принципов {skill} и успешных кейсов",
                "Разработка стратегий {skill} для учебных проектов",
                "Применение {skill} в небольших маркетинговых кампаниях",
                "Анализ эффективности {skill} на реальных примерах",
                "Построение комплексных маркетинговых планов с использованием {skill}"
            ],
            'образование': [
                "Изучение методик и подходов к {skill}",
                "Разработка учебных материалов с применением {skill}",
                "Проведение пробных занятий с использованием {skill}",
                "Анализ эффективности {skill} и корректировка подхода",
                "Интеграция {skill} в комплексную образовательную программу"
            ],
            'юриспруденция': [
                "Изучение нормативной базы по {skill}",
                "Анализ судебной практики в области {skill}",
                "Составление юридических документов с применением {skill}",
                "Моделирование правовых ситуаций в сфере {skill}",
                "Комплексный анализ сложных кейсов с применением {skill}"
            ],
            'инженерия': [
                "Изучение теоретических основ {skill}",
                "Практическое применение {skill} в простых проектах",
                "Разработка технических решений с использованием {skill}",
                "Оптимизация и улучшение решений на основе {skill}",
                "Внедрение инновационных подходов в применении {skill}"
            ],
            'дизайн': [
                "Изучение базовых принципов {skill} и успешных примеров",
                "Создание учебных проектов с применением {skill}",
                "Разработка собственного стиля применения {skill}",
                "Получение обратной связи и улучшение навыков {skill}",
                "Применение {skill} в комплексных дизайн-проектах"
            ]
        }
        
        # Технические термины для различных профессиональных областей
        technical_terms = {
            'it': ['фреймворки', 'библиотеки', 'микросервисы', 'алгоритмы', 'архитектура', 'паттерны проектирования'],
            'финансы': ['финансовые показатели', 'бюджетирование', 'управленческий учет', 'аудит', 'налоговая оптимизация'],
            'медицина': ['диагностика', 'методы лечения', 'протоколы', 'фармакология', 'реабилитация', 'профилактика'],
            'маркетинг': ['маркетинговый анализ', 'продвижение', 'таргетирование', 'конверсия', 'лидогенерация'],
            'образование': ['методики обучения', 'педагогические технологии', 'компетенции', 'оценка знаний'],
            'юриспруденция': ['судебная практика', 'нормативные акты', 'правовые прецеденты', 'юридическая техника'],
            'инженерия': ['проектирование', 'моделирование', 'расчеты', 'технические стандарты', 'оптимизация'],
            'дизайн': ['композиция', 'прототипирование', 'юзабилити', 'визуальная иерархия', 'интерактивность']
        }
        
        # Общие базовые шаги для любой профессии
        common_steps = [
            {
                "title": "Изучение теоретических основ профессии",
                "description": f"Получение базовых знаний о профессии {profession.capitalize()}, понимание ключевых концепций и фундаментальных принципов работы."
            },
            {
                "title": "Освоение базовых инструментов и технологий",
                "description": f"Знакомство с основными инструментами, необходимыми для работы в профессии {profession.capitalize()}, и практика их использования."
            },
            {
                "title": "Получение практического опыта",
                "description": "Решение реальных задач, выполнение учебных проектов и накопление практического опыта работы в профессиональной среде."
            },
            {
                "title": "Развитие профессиональных связей",
                "description": "Участие в профессиональных сообществах, посещение отраслевых мероприятий и налаживание контактов с другими специалистами в области."
            },
            {
                "title": "Постоянное самосовершенствование",
                "description": "Отслеживание актуальных тенденций в отрасли, изучение новых технологий и подходов для повышения профессионального уровня."
            }
        ]
        
        # Если не удалось определить тип профессии или нет специализированных шаблонов
        if profession_type not in learning_templates:
            return common_steps
        
        # Создаем шаги на основе выбранных навыков
        steps = []
        
        # Начинаем с ознакомительного шага
        steps.append({
            "title": f"Основы профессии {profession.capitalize()}",
            "description": f"Знакомство с базовыми принципами работы {profession.capitalize()}, понимание ключевых концепций и требований рынка."
        })
        
        # Добавляем шаги по навыкам
        for i, skill in enumerate(selected_skills):
            templates = learning_templates.get(profession_type, learning_templates['it'])
            
            # Генерируем описание на основе шаблона
            description = templates[i % len(templates)].format(skill=skill)
            
            # Добавляем технические термины для более профессионального звучания
            terms = technical_terms.get(profession_type, ['методология', 'специализация', 'компетенции', 'практика'])
            term = random.choice(terms)
            
            steps.append({
                "title": f"Изучение и практика: {skill}",
                "description": f"{description}. Освоение {term} в контексте {skill} для повышения эффективности работы."
            })
        
        # Добавляем заключительный шаг по проектному портфолио
        steps.append({
            "title": "Создание профессионального портфолио",
            "description": f"Формирование набора проектов и примеров работ, демонстрирующих ваши навыки и опыт в области {profession.capitalize()}."
        })
        
        # Ограничиваем количество шагов для разных уровней
        max_steps = min(7, len(steps))
        
        return steps[:max_steps]
    
    def get_default_roadmap(self, profession, experience_level='junior', region=None):
        """
        Возвращает дефолтную дорожную карту, если произошла ошибка
        
        Args:
            profession (str): Название профессии
            experience_level (str): Уровень опыта
            region (str): Регион пользователя
            
        Returns:
            dict: Дефолтная дорожная карта
        """
        profession_type = self.find_profession_type(profession)
        
        # Базовые навыки для разных типов профессий
        default_skills = {
            "it": ["Программирование", "Алгоритмы и структуры данных", "Базы данных", "Сетевые технологии"],
            "финансы": ["Финансовый анализ", "Бухгалтерский учет", "Excel", "Финансовое моделирование"],
            "медицина": ["Анатомия", "Физиология", "Фармакология", "Клиническое мышление"],
            "маркетинг": ["Маркетинговые исследования", "Брендинг", "SMM", "Аналитика"],
            "образование": ["Педагогика", "Психология", "Методика преподавания", "Ораторское искусство"],
            "юриспруденция": ["Гражданское право", "Уголовное право", "Юридическое письмо", "Навыки переговоров"],
            "инженерия": ["Черчение", "Проектирование", "Моделирование", "Технический анализ"],
            "дизайн": ["Композиция", "Типографика", "Графические редакторы", "UX/UI дизайн"],
        }
        
        # Получаем навыки в зависимости от типа профессии
        skills = default_skills.get(profession_type, ["Профессиональные знания", "Коммуникабельность", "Аналитическое мышление"])
        
        # Форматируем навыки с описаниями
        formatted_skills = self.format_skills_with_descriptions(skills, profession)
        
        # Генерируем шаги обучения
        steps = self.generate_learning_steps(profession, skills, experience_level)
        
        # Получаем ресурсы для обучения
        resources = self.get_learning_resources(profession_type, skills)
        
        # Получаем региональные рекомендации
        regional_recommendations = self.get_regional_recommendations(profession, region)
        
        # Определяем перспективы карьерного роста
        career_prospects = self.generate_career_prospects(profession, skills, experience_level)
        
        return {
            "profession": profession.capitalize(),
            "profession_type": profession_type,
            "description": f"{profession.capitalize()} - специалист, который {self.get_profession_description(profession)}",
            "skills": formatted_skills,
            "learning_steps": steps,
            "education": ["Высшее профильное образование", 
                          "Дополнительное профессиональное образование", 
                          "Профессиональные сертификаты"],
            "resources": resources,
            "career_prospects": career_prospects,
            "regional_recommendations": regional_recommendations,
            "trends": self.get_industry_trends(profession_type)
        }
    
    def get_local_llm(self):
        """
        Возвращает экземпляр класса LocalLLM для работы с локальной моделью.
        Если экземпляр уже существует, возвращает его, иначе создает новый.
        
        Returns:
            LocalLLM: Экземпляр класса для работы с локальной моделью
        """
        if not self.llm and LLM_AVAILABLE:
            try:
                from llm_integration import LocalLLM
                self.llm = LocalLLM(model="qwen3-8b")  # Явно указываем использование модели qwen3-8b
                self.use_llm = True
                logging.info("Локальная LLM модель qwen3-8b успешно инициализирована в get_local_llm")
            except Exception as e:
                logging.error(f"Ошибка при инициализации LLM модели в get_local_llm: {e}")
                
        if not self.llm:
            raise Exception("Локальная LLM модель недоступна. Проверьте наличие модуля llm_integration.py и доступность LM Studio на порту 1234.")
                
        return self.llm
        
    def generate_roadmap(self, user_input, region=None, user_info=None):
        """Генерирует карьерную дорожную карту на основе введенной пользователем профессии и региона.
        
        Args:
            user_input (str): Введенная пользователем профессия
            region (str): Регион (по умолчанию Россия)
            user_info (str): Информация о пользователе в свободной форме (включая опыт, навыки, интересы и т.д.)
            
        Returns:
            dict: Структурированная информация о карьерной дорожной карте
        """
        print(f"Получен запрос на генерацию карьерной карты для: {user_input} в регионе: {region}")
        
        # Нормализуем регион
        original_region = region
        if not region or region.strip().lower() in ["россия", "рф", "russia", "russian federation"]:
            region = "Россия"
        
        # Используем локальную модель
        local_llm = self.get_local_llm()
        
        # Генерируем карьерную карту
        roadmap = local_llm.generate_roadmap(user_input, original_region, user_info)
        
        # Добавляем информацию о профессии и регионе в результат
        roadmap["profession"] = user_input
        roadmap["region"] = original_region or "Россия"
        
        # Проверяем, что futureInsights представлен в виде списка
        if "futureInsights" in roadmap and isinstance(roadmap["futureInsights"], str):
            # Преобразуем строку в массив, разбивая по точке или новой строке
            insights_text = roadmap["futureInsights"]
            insights = []
            for insight in re.split(r'[.\n]+', insights_text):
                insight = insight.strip()
                if insight:  # Добавляем только непустые строки
                    insights.append(insight)
            
            if not insights:  # Если после разбивки нет элементов, используем весь текст
                insights = [insights_text]
                
            roadmap["futureInsights"] = insights
        
        # Извлекаем темы для изучения из плана обучения
        learning_topics = []
        if "learningPlan" in roadmap and isinstance(roadmap["learningPlan"], list):
            for step in roadmap["learningPlan"]:
                if isinstance(step, dict) and "title" in step:
                    # Убираем общие фразы из названия темы
                    topic = step["title"]
                    topic = re.sub(r'^(Изучение|Освоение|Практика|Знакомство с)\s+', '', topic)
                    topic = re.sub(r'^(и|практика|навыки)\s+', '', topic)
                    learning_topics.append(topic)
        
        # Добавляем хард-скиллы как дополнительные темы
        if "hardSkills" in roadmap and isinstance(roadmap["hardSkills"], list):
            for skill in roadmap["hardSkills"]:
                if isinstance(skill, str):
                    learning_topics.append(skill)
        
        # Находим образовательные ресурсы для тем
        if learning_topics:
            educational_resources = self.find_education_resources(user_input, learning_topics)
            roadmap["educationalResources"] = educational_resources
        
        # Генерируем персональные рекомендации если предоставлена информация о пользователе
        if user_info:
            # Используем LLM модель для генерации персональных рекомендаций
            personal_recommendations = self.generate_personal_recommendations_with_llm(user_input, region, user_info, local_llm)
            roadmap["personalRecommendations"] = personal_recommendations
        
        # Возвращаем результат
        return roadmap
    
    def generate_personal_recommendations_with_llm(self, profession, region, user_info, llm=None):
        """Генерирует персональные рекомендации, используя LLM модель.
        
        Args:
            profession (str): Название профессии
            region (str): Название региона
            user_info (str): Информация о пользователе
            llm (LocalLLM, optional): Экземпляр LocalLLM для генерации рекомендаций
            
        Returns:
            list: Список персонализированных рекомендаций
        """
        try:
            if not llm:
                llm = self.get_local_llm()
                
            # Создаем промпт для генерации персональных рекомендаций
            prompt = f"""Ты опытный карьерный консультант и коуч по профессиональному развитию с 15-летним стажем. 
На основе предоставленной информации о пользователе сгенерируй 5-7 глубоко персонализированных карьерных рекомендаций для профессии "{profession}" в регионе "{region}".

ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:
{user_info}

ТРЕБОВАНИЯ К РЕКОМЕНДАЦИЯМ:

1. ГЛУБОКАЯ ПЕРСОНАЛИЗАЦИЯ:
   - Тщательно проанализируй предоставленную информацию о пользователе
   - Учти явно указанные и подразумеваемые потребности, ограничения, сильные стороны и цели
   - Адаптируй рекомендации к конкретной ситуации пользователя
   - Учитывай возможные медицинские и личные особенности

2. ПРАКТИЧЕСКАЯ ЦЕННОСТЬ:
   - Каждая рекомендация должна быть конкретной и действенной
   - Рекомендации должны быть реалистичными и выполнимыми
   - Включай краткое обоснование ценности каждой рекомендации
   - При возможности указывай конкретные шаги или стратегии реализации

3. РЕГИОНАЛЬНАЯ СПЕЦИФИКА:
   - Учитывай особенности рынка труда в указанном регионе
   - Адаптируй рекомендации к местной деловой культуре и практикам
   - Рассматривай локальные возможности для развития и нетворкинга
   - Принимай во внимание региональный уровень заработных плат и конкуренции

4. ПРОФЕССИОНАЛЬНАЯ СПЕЦИФИКА:
   - Рекомендации должны четко соответствовать выбранной профессии
   - Учитывай актуальные тренды и требования в данной профессиональной области
   - Предлагай стратегии для развития наиболее ценных навыков в этой профессии
   - Учитывай типичную карьерную траекторию в данной профессии

5. ФОРМАТИРОВАНИЕ:
   - Каждая рекомендация должна быть представлена отдельным абзацем (5-7 предложений)
   - НЕ используй нумерацию, маркеры списков или другие элементы форматирования
   - НЕ используй кавычки в начале или конце рекомендаций
   - НЕ включай общие вводные фразы вроде "Вот мои рекомендации:" или заключения

СТРУКТУРА КАЖДОЙ РЕКОМЕНДАЦИИ:
- Начинай с четкого действия или стратегии
- Объясняй, почему это важно именно для этого пользователя
- Включай конкретные шаги или тактики реализации
- При необходимости упоминай ресурсы или инструменты
- Завершай указанием ожидаемого результата или пользы

Верни ТОЛЬКО сами рекомендации, каждую с новой строки, без дополнительного текста, вступлений или заключений.
"""
            # Генерируем ответ от модели с улучшенными параметрами для большей детализации
            response = llm.generate(
                prompt, 
                temperature=0.5,  # Увеличиваем температуру для более творческих ответов
                max_tokens=2048,  # Увеличиваем лимит токенов для более детальных рекомендаций
                top_p=0.95        # Увеличиваем разнообразие ответов
            )
            
            if not response:
                logging.warning("Не удалось получить ответ от LLM модели для персональных рекомендаций")
                return self.generate_personal_recommendations(user_info)
                
            # Преобразуем ответ в список рекомендаций
            # Разделяем текст на абзацы, считая что пустая строка разделяет рекомендации
            raw_recommendations = []
            current_rec = []
            
            for line in response.strip().split('\n'):
                if not line.strip() and current_rec:  # Пустая строка и есть накопленный текст
                    raw_recommendations.append(' '.join(current_rec))
                    current_rec = []
                elif line.strip():  # Непустая строка
                    current_rec.append(line.strip())
            
            # Добавляем последнюю рекомендацию, если она осталась
            if current_rec:
                raw_recommendations.append(' '.join(current_rec))
            
            # Если получен сплошной текст без разделителей, пробуем разделить по другим признакам
            if len(raw_recommendations) <= 1 and response.strip():
                # Пробуем разделить по точке и новой строке
                potential_recs = re.split(r'\.\s*\n', response.strip())
                if len(potential_recs) > 1:
                    raw_recommendations = [rec.strip() + '.' for rec in potential_recs if rec.strip()]
                else:
                    # Если не удалось разделить, просто берем весь текст как одну рекомендацию
                    raw_recommendations = [response.strip()]
            
            # Очищаем каждую рекомендацию от маркеров и кавычек
            recommendations = []
            for rec in raw_recommendations:
                if not rec.strip():
                    continue
                # Удаляем нумерацию и маркеры списков
                rec = re.sub(r'^[\d\-\*\.\)\s]+', '', rec.strip())
                # Удаляем кавычки в начале строки
                rec = re.sub(r'^["\'«]', '', rec)
                # Удаляем кавычки в конце строки
                rec = re.sub(r'["\'»]$', '', rec)
                if rec:
                    recommendations.append(rec)
            
            # Удаляем дубликаты
            recommendations = list(dict.fromkeys(recommendations))  # Удаление дубликатов с сохранением порядка
            
            # Если не удалось получить рекомендации, используем стандартный метод
            if not recommendations:
                logging.warning("После обработки ответа LLM модели не осталось рекомендаций, использую стандартный метод")
                return self.generate_personal_recommendations(user_info)
                
            # Ограничиваем количество рекомендаций
            if len(recommendations) > 7:
                recommendations = recommendations[:7]
            
            return recommendations
            
        except Exception as e:
            logging.error(f"Ошибка при генерации персональных рекомендаций с LLM: {e}")
            logging.error(traceback.format_exc())
            # В случае ошибки используем стандартный метод
            return self.generate_personal_recommendations(user_info)
    
    def generate_personal_recommendations(self, user_info):
        """Генерирует персональные рекомендации на основе информации о пользователе.
        Используется как запасной вариант, если генерация с LLM не удалась.
        
        Args:
            user_info (str): Информация о пользователе в свободной форме
            
        Returns:
            list: Список персонализированных рекомендаций
        """
        recommendations = []
        user_info_lower = user_info.lower()
        
        # Определяем опыт пользователя
        experience_level = None
        if any(word in user_info_lower for word in ["начинающий", "студент", "без опыта", "джуниор", "junior"]):
            experience_level = "junior"
        elif any(word in user_info_lower for word in ["опыт от 1", "опыт от 2", "опыт от 3", "мидл", "middle"]):
            experience_level = "middle"
        elif any(word in user_info_lower for word in ["опыт от 5", "опыт более 5", "сеньор", "senior"]):
            experience_level = "senior"
        
        # Определяем предпочтительный режим работы
        work_mode = None
        if any(word in user_info_lower for word in ["удаленка", "удаленно", "remote", "дистанционно"]):
            work_mode = "remote"
        elif any(word in user_info_lower for word in ["офис", "office", "очно"]):
            work_mode = "office"
        elif any(word in user_info_lower for word in ["гибрид", "hybrid", "смешанный"]):
            work_mode = "hybrid"
        
        # Добавляем рекомендации на основе опыта
        if experience_level == "junior":
            recommendations.append("Рекомендуется сосредоточиться на овладении базовыми навыками и технологиями, чтобы создать прочную основу.")
            recommendations.append("Ищите компании с хорошими программами стажировок и менторства для начинающих специалистов.")
            recommendations.append("Активно участвуйте в открытых проектах и создавайте портфолио работ для демонстрации ваших навыков.")
        elif experience_level == "middle":
            recommendations.append("Развивайте специализацию в определенной области, чтобы выделиться на рынке труда.")
            recommendations.append("Ищите проекты, которые предлагают возможности для профессионального роста и расширения вашего опыта.")
            recommendations.append("Начните развивать навыки управления небольшими задачами или командами.")
        elif experience_level == "senior":
            recommendations.append("Рассмотрите возможность развития в роли технического лидера или менеджера проектов.")
            recommendations.append("Ищите компании, которые ценят ваш опыт и предлагают возможности для стратегического влияния.")
            recommendations.append("Рассмотрите возможность наставничества для укрепления вашей репутации эксперта в отрасли.")
        
        # Добавляем рекомендации на основе режима работы
        if work_mode == "remote":
            recommendations.append("Для успешной удаленной работы важно иметь хорошие навыки самоорганизации и управления временем.")
            recommendations.append("Инвестируйте в качественное домашнее рабочее место и стабильное интернет-соединение.")
            recommendations.append("Активно участвуйте в онлайн-коммуникации с командой, чтобы избежать изоляции.")
        elif work_mode == "office":
            recommendations.append("Развивайте навыки личной коммуникации и работы в команде для эффективного взаимодействия в офисе.")
            recommendations.append("Используйте преимущества очного обучения и наставничества в офисном окружении.")
            recommendations.append("Уделяйте внимание развитию профессиональной сети контактов в вашей компании.")
        elif work_mode == "hybrid":
            recommendations.append("Гибридный формат требует гибкости и умения эффективно переключаться между разными режимами работы.")
            recommendations.append("Планируйте офисные дни для важных встреч и совместной работы над сложными задачами.")
            recommendations.append("Развивайте навыки цифровой коммуникации наряду с личным взаимодействием.")
        
        # Если определено менее 3 рекомендаций, добавляем общие
        if len(recommendations) < 3:
            general_recommendations = [
                "Регулярно обновляйте свои знания и навыки, следите за трендами в вашей области.",
                "Развивайте сеть профессиональных контактов через участие в мероприятиях и онлайн-сообществах.",
                "Ищите работу в компаниях, чьи ценности и культура соответствуют вашим личным предпочтениям.",
                "Не забывайте о балансе работы и личной жизни для долгосрочного успеха в карьере."
            ]
            
            for rec in general_recommendations:
                if len(recommendations) < 5:
                    if rec not in recommendations:
                        recommendations.append(rec)
                else:
                    break
        
        return recommendations
    
    def _estimate_average_salary(self, profession, experience_level):
        """Оценивает среднюю зарплату для указанной профессии и уровня опыта.
        
        Упрощенная логика, в реальном приложении здесь был бы более сложный алгоритм
        или обращение к базе данных/API зарплат.
        
        Args:
            profession (str): Название профессии
            experience_level (str): Уровень опыта
            
        Returns:
            int: Оценка средней зарплаты в рублях или None, если невозможно оценить
        """
        # Базовые зарплаты для разных типов профессий (очень упрощенно)
        base_salaries = {
            "разработчик": 120000,
            "дизайнер": 90000,
            "маркетолог": 80000,
            "аналитик": 100000,
            "менеджер": 110000,
            "инженер": 100000,
            "повар": 65000,
            "врач": 95000,
            "учитель": 60000,
            "юрист": 100000,
            "бухгалтер": 85000,
            "unknown": 75000
        }
        
        # Множители для разных уровней опыта
        experience_multipliers = {
            "junior": 0.7,
            "middle": 1.0,
            "senior": 1.8
        }
        
        # Находим подходящую базовую зарплату
        base_salary = None
        for key, salary in base_salaries.items():
            if key in profession.lower():
                base_salary = salary
                break
        
        if not base_salary:
            base_salary = base_salaries.get("unknown")
        
        # Применяем множитель опыта
        multiplier = experience_multipliers.get(experience_level, 1.0)
        
        return int(base_salary * multiplier)
    
    def get_learning_resources(self, profession_type, skills):
        """
        Генерирует рекомендуемые ресурсы для обучения на основе типа профессии и навыков
        
        Args:
            profession_type (str): Тип/категория профессии
            skills (list): Список технических навыков
            
        Returns:
            list: Список рекомендуемых ресурсов для обучения
        """
        # Базовые образовательные платформы по категориям
        platforms_by_category = {
            'it': [
                'Coursera - специализированные курсы по IT-направлениям',
                'Stepik - курсы по программированию и информатике',
                'Udemy - обширная база практических курсов от экспертов в IT',
                'GeekBrains - специализированные программы обучения IT-специальностям',
                'Skillbox - комплексные курсы с поддержкой менторов',
                'LeetCode - для отработки алгоритмических задач',
                'GitHub - для изучения открытых проектов и практики',
                'Stack Overflow - для решения технических вопросов',
                'Хабр - статьи и обсуждения IT-тематики на русском языке'
            ],
            'финансы': [
                'Нетология - курсы по финансовому анализу и менеджменту',
                'Высшая Школа Экономики - программы дополнительного профессионального образования',
                'Coursera - курсы от ведущих бизнес-школ',
                'Банк России - обучающие материалы по финансовой грамотности',
                'СберУниверситет - программы в сфере финансов и экономики',
                'Финам - обучающие материалы по финансовым рынкам',
                'Библиотека финансового аналитика - профессиональная литература',
                'CFI (Corporate Finance Institute) - сертификационные программы'
            ],
            'маркетинг': [
                'Нетология - курсы по маркетингу и SMM',
                'Skillbox - комплексные программы по маркетингу',
                'Яндекс.Практикум - курсы по интернет-маркетингу',
                'Google Digital Workshop - бесплатные курсы по цифровому маркетингу',
                'ВШЭ - программы дополнительного образования в сфере маркетинга',
                'Специализированные блоги (Texterra, Cossa, vc.ru) - актуальные тренды',
                'HubSpot Academy - бесплатные курсы по маркетингу и продажам',
                'MarketingProfs - профессиональные статьи и вебинары'
            ],
            'медицина': [
                'Медицинский образовательный портал для врачей - непрерывное медицинское образование',
                'Портал непрерывного медицинского и фармацевтического образования Минздрава России',
                'WebMed - образовательная платформа для медицинских работников',
                'MedElement - обучающие материалы и тесты для врачей',
                'PubMed - медицинские исследования и публикации',
                'Московский государственный медицинский университет им. И.М. Сеченова - курсы повышения квалификации',
                'Российское общество симуляционного обучения в медицине - тренинги и симуляции',
                'Специализированные медицинские журналы и издания'
            ],
            'образование': [
                'Педагогический университет "Первое сентября" - курсы для учителей',
                'Инфоурок - образовательный портал для педагогов',
                'Российская электронная школа - методические материалы',
                'Институт ЮНЕСКО по информационным технологиям в образовании - курсы по цифровой педагогике',
                'Академия Минпросвещения России - программы повышения квалификации',
                'Межрегиональная школа профессионального мастерства - обмен опытом между педагогами',
                'Профессиональные сообщества учителей-предметников',
                'Электронные библиотеки педагогических исследований'
            ],
            'строительство': [
                'Национальное объединение строителей (НОСТРОЙ) - курсы повышения квалификации',
                'МГСУ (НИУ) - дополнительное профессиональное образование',
                'Академия КНАУФ - обучение современным строительным технологиям',
                'Портал СметаРу - обучение сметному делу',
                'Строительный эксперт - профессиональное сообщество и обучающие материалы',
                'НОУ ИНТУИТ - курсы по САПР и строительному проектированию',
                'Специализированные строительные выставки и семинары',
                'Профессиональные ассоциации по различным строительным специальностям'
            ],
            'дизайн': [
                'Skillbox - комплексные курсы по графическому, веб- и UX/UI дизайну',
                'Нетология - обучающие программы по дизайну',
                'Bang Bang Education - курсы от ведущих дизайнеров',
                'Британская высшая школа дизайна - короткие интенсивные программы',
                'Behance - портфолио и вдохновение',
                'Dribbble - сообщество дизайнеров и работы',
                'Canva Design School - бесплатные уроки по дизайну',
                'Специализированные YouTube-каналы по дизайну',
                'Дизайн-сообщества в Telegram'
            ],
            'право': [
                'LF Академия - курсы для юристов',
                'Система КонсультантПлюс - обучающие материалы и семинары',
                'ГАРАНТ - образовательные проекты для юристов',
                'Российская школа частного права - программы повышения квалификации',
                'Юридический институт М-Логос - курсы и семинары',
                'Legal Academy - профессиональные курсы для юристов',
                'Специализированные юридические журналы и издания',
                'Профессиональные юридические сообщества и ассоциации'
            ]
        }
        
        # Общие образовательные ресурсы
        general_resources = [
            'Coursera - онлайн-курсы от ведущих университетов мира',
            'Stepik - образовательная платформа с курсами на русском языке',
            'Открытое образование - курсы от ведущих российских вузов',
            'Универсариум - открытая система электронного образования',
            'YouTube - образовательные каналы по различным направлениям',
            'Профильные сообщества в Telegram и VK',
            'Профессиональная литература и периодические издания',
            'Отраслевые конференции и семинары (онлайн и офлайн)'
        ]
        
        # Выбираем ресурсы в зависимости от типа профессии
        resources = []
        
        if profession_type in platforms_by_category:
            # Добавляем специализированные ресурсы для данного типа профессии
            resources.extend(random.sample(platforms_by_category[profession_type], 
                                         min(5, len(platforms_by_category[profession_type]))))
        
        # Добавляем общие ресурсы
        general_to_add = random.sample(general_resources, min(3, len(general_resources)))
        resources.extend(general_to_add)
        
        # Добавляем книги и ресурсы на основе навыков
        if skills:
            # Выбираем случайные навыки из списка для рекомендации книг
            selected_skills = random.sample(skills, min(3, len(skills)))
            for skill in selected_skills:
                resources.append(f"Книги и специализированные ресурсы по теме '{skill}'")
        
        # Перемешиваем ресурсы для более естественной рекомендации
        random.shuffle(resources)
        
        return resources[:8]  # Возвращаем не более 8 ресурсов 

    def generate_education_resources(self, profession, skills, experience_level='junior'):
        """
        Генерирует рекомендации по образовательным ресурсам для изучения профессии
        
        Args:
            profession (str): Название профессии
            skills (list): Список навыков для изучения
            experience_level (str): Уровень опыта ('junior', 'middle', 'senior')
            
        Returns:
            dict: Структурированный словарь с рекомендациями по образовательным ресурсам
        """
        profession_type = self.find_profession_type(profession)
        
        # Базовые платформы для онлайн-обучения по типу профессии
        online_platforms = {
            'it': ['Coursera', 'Udemy', 'Stepik', 'Яндекс Практикум', 'SkillBox', 'Хекслет', 'Geekbrains', 'Otus'],
            'финансы': ['Coursera', 'Нетология', 'Финам', 'BAS', 'ЧУ ДПО Финансовый университет'],
            'медицина': ['Медунивер', 'Osmosis', 'Medscape', 'НМО портал', 'Consilium Medicum'],
            'маркетинг': ['Нетология', 'SkillBox', 'Geekbrains', 'Яндекс Практикум', 'Marketing.by'],
            'образование': ['Фоксфорд', 'Инфоурок', 'Универсариум', 'Педсовет'],
            'юриспруденция': ['Национальная юридическая академия', 'Garant.ru', 'LF Академия', 'Закон.ру'],
            'инженерия': ['Stepik', 'Numeca', 'Лекториум', 'Ansys Learning'],
            'дизайн': ['Behance', 'SkillBox', 'Bang Bang Education', 'Нетология', 'Design Spot']
        }
        
        # Выбираем платформы по типу профессии
        platforms = online_platforms.get(profession_type, ['Coursera', 'Stepik', 'Нетология', 'SkillBox'])
        
        # Выбираем количество ресурсов в зависимости от уровня опыта
        if experience_level == 'junior':
            num_resources = 5  # Больше ресурсов для начинающих
        elif experience_level == 'middle':
            num_resources = 4
        else:  # senior
            num_resources = 3  # Меньше базовых ресурсов для опытных специалистов
            
        # Выбираем случайные платформы
        selected_platforms = random.sample(platforms, min(num_resources, len(platforms)))
        
        # Словарь с шаблонами для разных видов ресурсов
        resource_templates = {
            'онлайн_курсы': [
                "Курс «{skill} для начинающих» на платформе {platform}",
                "Интенсив «{skill}: от основ к практике» на {platform}",
                "Профессия «{profession}» на {platform}",
                "Специализация «{skill}» на платформе {platform}",
            ],
            'книги': [
                "«{skill}: практическое руководство» под редакцией экспертов в области",
                "«Основы {skill} для профессии {profession}»",
                "«{skill} на практике: подходы и методики»",
                "«Современные тенденции в области {skill}»",
            ],
            'сообщества': [
                "Профессиональное сообщество {profession} в Telegram",
                "Форум специалистов по {skill} на Habr",
                "Группа {profession} на платформе LinkedIn",
                "Сообщество практиков {skill} в Discord",
            ],
            'youtube': [
                "Канал «{skill} для профессионалов»",
                "Уроки по {skill} от ведущих экспертов",
                "Видеокурс «{profession} с нуля до профи»",
                "Вебинары по {skill} для специалистов разного уровня",
            ]
        }
        
        # Генерируем рекомендации по образовательным ресурсам
        education_resources = {}
        
        # Добавляем онлайн-курсы
        online_courses = []
        for i in range(num_resources):
            platform = selected_platforms[i % len(selected_platforms)]
            skill = skills[i % len(skills)]
            template = random.choice(resource_templates['онлайн_курсы'])
            course = template.format(skill=skill, platform=platform, profession=profession)
            online_courses.append(course)
        education_resources['онлайн_курсы'] = online_courses
        
        # Добавляем книги
        books = []
        for i in range(min(3, num_resources)):
            skill = skills[(i + 1) % len(skills)]
            template = random.choice(resource_templates['книги'])
            book = template.format(skill=skill, profession=profession)
            books.append(book)
        education_resources['книги'] = books
        
        # Добавляем профессиональные сообщества
        communities = []
        for i in range(2):
            skill = skills[(i + 2) % len(skills)]
            template = random.choice(resource_templates['сообщества'])
            community = template.format(skill=skill, profession=profession)
            communities.append(community)
        education_resources['профессиональные_сообщества'] = communities
        
        # Добавляем YouTube-каналы
        youtube_channels = []
        for i in range(min(2, num_resources - 1)):
            skill = skills[(i + 3) % len(skills)]
            template = random.choice(resource_templates['youtube'])
            channel = template.format(skill=skill, profession=profession)
            youtube_channels.append(channel)
        education_resources['youtube'] = youtube_channels
        
        # Для продвинутых специалистов добавляем дополнительные ресурсы
        if experience_level in ['middle', 'senior']:
            advanced_resources = [
                f"Профессиональная конференция по {profession} (ежегодная)",
                f"Специализированные воркшопы по {skills[0] if skills else profession}",
                f"Менторство от экспертов в области {profession}"
            ]
            education_resources['продвинутые_ресурсы'] = advanced_resources
            
        return education_resources 

    def find_education_resources(self, profession: str, topics: list) -> dict:
        """
        Находит образовательные ресурсы по списку тем, с учетом профессии
        
        Args:
            profession (str): Название профессии (например, 'системный администратор', 'программист 1С')
            topics (list): Список тем для изучения
            
        Returns:
            dict: Словарь с ресурсами по каждой теме
        """
        # Словарь доступных бесплатных курсов и ресурсов для различных профессий
        free_resources = {
            "системный администратор": {
                "общие": [
                    {"title": "Cisco Networking Academy", "url": "https://www.netacad.com/", "description": "Бесплатные курсы по сетевым технологиям"},
                    {"title": "Microsoft Learn", "url": "https://learn.microsoft.com/", "description": "Обучающие материалы по продуктам Microsoft"},
                    {"title": "Linux Foundation Training", "url": "https://training.linuxfoundation.org/free-courses/", "description": "Бесплатные курсы по Linux"},
                    {"title": "Хабр", "url": "https://habr.com/ru/hub/system_administration/", "description": "Статьи по системному администрированию"}
                ],
                "сети": [
                    {"title": "Введение в сетевые технологии", "url": "https://www.netacad.com/courses/networking/networking-essentials", "description": "Базовый курс по сетям от Cisco"},
                    {"title": "Network Chuck (YouTube)", "url": "https://www.youtube.com/c/NetworkChuck", "description": "Обучающие видео по сетевым технологиям"},
                    {"title": "Сети для самых маленьких", "url": "https://habr.com/ru/post/134892/", "description": "Популярная серия статей об основах сетей"}
                ],
                "безопасность": [
                    {"title": "Cybersecurity Essentials", "url": "https://www.netacad.com/courses/cybersecurity/cybersecurity-essentials", "description": "Основы кибербезопасности от Cisco"},
                    {"title": "SecurityLab", "url": "https://www.securitylab.ru/", "description": "Новости и статьи о безопасности"},
                    {"title": "Practical Networking (YouTube)", "url": "https://www.youtube.com/c/PracticalNetworking", "description": "Видео о сетевой безопасности"}
                ],
                "операционные системы": [
                    {"title": "Курс по Linux", "url": "https://stepik.org/course/762/", "description": "Введение в Linux"},
                    {"title": "Windows Server Administration", "url": "https://learn.microsoft.com/en-us/training/windows-server/", "description": "Администрирование Windows Server"},
                    {"title": "Курс Основы Linux от Яндекс Практикум", "url": "https://practicum.yandex.ru/profile/linux-administrating/", "description": "Интенсивный курс по основам Linux"}
                ],
                "мониторинг": [
                    {"title": "Zabbix Documentation", "url": "https://www.zabbix.com/documentation/", "description": "Документация по Zabbix"},
                    {"title": "Prometheus - Мониторинг систем и сервисов", "url": "https://prometheus.io/docs/introduction/overview/", "description": "Документация по Prometheus"},
                    {"title": "Grafana Tutorials", "url": "https://grafana.com/tutorials/", "description": "Уроки по работе с Grafana"}
                ],
                "автоматизация": [
                    {"title": "Ansible Documentation", "url": "https://docs.ansible.com/", "description": "Документация по Ansible"},
                    {"title": "PowerShell for Sysadmins", "url": "https://learning.oreilly.com/library/view/powershell-for-sysadmins/9781098139445/", "description": "Книга по PowerShell"},
                    {"title": "Terraform Tutorials", "url": "https://learn.hashicorp.com/terraform", "description": "Уроки по Terraform"}
                ]
            },
            "программист 1с": {
                "общие": [
                    {"title": "Учебные материалы 1С", "url": "https://edu.1cfresh.com/", "description": "Бесплатные курсы от 1С"},
                    {"title": "1С:Учебный центр №1", "url": "https://www.1c.ru/rus/partners/training/uc1/course.jsp", "description": "Курсы по разработке на 1С"},
                    {"title": "Инфостарт", "url": "https://infostart.ru/", "description": "Сообщество разработчиков 1С с массой полезных статей"}
                ],
                "программирование": [
                    {"title": "Введение в конфигурирование в 1С", "url": "https://edu.1cfresh.com/courses/course-v1:1C+1C-ERP-1+2020/about", "description": "Базовый курс по 1С:Предприятие"},
                    {"title": "1С:Предприятие 8.3. Практическое пособие разработчика", "url": "https://its.1c.ru/db/pubv83dev", "description": "Практическое пособие разработчика"},
                    {"title": "YouTube-канал \"Курсы 1С программирования\"", "url": "https://www.youtube.com/user/Courses1C", "description": "Обучающие видео по программированию в 1С"}
                ],
                "интерфейсы": [
                    {"title": "Курс по разработке интерфейсов в 1С", "url": "https://курсы-по-1с.рф/free/ui-ux-разработка-интерфейсов-в-1с/", "description": "Бесплатный курс по UI/UX в 1С"},
                    {"title": "Разработка современных пользовательских интерфейсов", "url": "https://its.1c.ru/db/metod8dev/content/2358/hdoc", "description": "Методические рекомендации по разработке интерфейсов"}
                ]
            },
            "веб-разработчик": {
                "общие": [
                    {"title": "MDN Web Docs", "url": "https://developer.mozilla.org/ru/", "description": "Документация по веб-технологиям"},
                    {"title": "freeCodeCamp", "url": "https://www.freecodecamp.org/", "description": "Интерактивные курсы по веб-разработке"},
                    {"title": "HTML Academy", "url": "https://htmlacademy.ru/courses", "description": "Интерактивные курсы по веб-разработке"},
                    {"title": "Хекслет", "url": "https://ru.hexlet.io/professions/frontend", "description": "Профессия фронтенд-разработчик"}
                ],
                "frontend": [
                    {"title": "JavaScript.info", "url": "https://javascript.info/", "description": "Современный учебник по JavaScript"},
                    {"title": "React Documentation", "url": "https://react.dev/", "description": "Официальная документация React"},
                    {"title": "CSS-Tricks", "url": "https://css-tricks.com/", "description": "Статьи и руководства по CSS"},
                    {"title": "Frontend Masters", "url": "https://frontendmasters.com/learn/", "description": "Схема обучения фронтенд-разработке"}
                ],
                "backend": [
                    {"title": "Django Documentation", "url": "https://docs.djangoproject.com/", "description": "Документация по Django"},
                    {"title": "Node.js Documentation", "url": "https://nodejs.org/en/docs/", "description": "Документация по Node.js"},
                    {"title": "PHP: The Right Way", "url": "https://phptherightway.com/", "description": "Руководство по современному PHP"},
                    {"title": "Spring Framework Documentation", "url": "https://spring.io/guides", "description": "Руководства по Spring Framework"}
                ],
                "базы данных": [
                    {"title": "PostgreSQL Tutorial", "url": "https://www.postgresqltutorial.com/", "description": "Руководство по PostgreSQL"},
                    {"title": "MongoDB University", "url": "https://university.mongodb.com/", "description": "Бесплатные курсы по MongoDB"},
                    {"title": "SQL Academy", "url": "https://sql-academy.org/ru", "description": "Интерактивный курс по SQL"}
                ],
                "devops": [
                    {"title": "Docker Documentation", "url": "https://docs.docker.com/get-started/", "description": "Начало работы с Docker"},
                    {"title": "Kubernetes Documentation", "url": "https://kubernetes.io/docs/home/", "description": "Документация по Kubernetes"},
                    {"title": "GitHub Actions", "url": "https://docs.github.com/en/actions", "description": "Руководство по CI/CD с GitHub Actions"}
                ]
            },
            "data scientist": {
                "общие": [
                    {"title": "Kaggle Learn", "url": "https://www.kaggle.com/learn", "description": "Бесплатные курсы по анализу данных"},
                    {"title": "DataCamp", "url": "https://www.datacamp.com/courses", "description": "Курсы по работе с данными (часть бесплатно)"},
                    {"title": "Открытое образование: Введение в Data Science", "url": "https://openedu.ru/course/mipt/INTRODS/", "description": "Курс от МФТИ по основам Data Science"}
                ],
                "машинное обучение": [
                    {"title": "Machine Learning Crash Course", "url": "https://developers.google.com/machine-learning/crash-course", "description": "Курс по ML от Google"},
                    {"title": "Курс по машинному обучению от ODS", "url": "https://mlcourse.ai/", "description": "Открытый курс по машинному обучению"},
                    {"title": "Практический курс по нейронным сетям", "url": "https://stepik.org/course/50352/", "description": "Курс на Stepik"}
                ],
                "python": [
                    {"title": "Python Data Science Handbook", "url": "https://jakevdp.github.io/PythonDataScienceHandbook/", "description": "Книга по работе с данными на Python"},
                    {"title": "Python для анализа данных", "url": "https://www.coursera.org/specializations/python-for-data-analysis-ru", "description": "Специализация на Coursera от МФТИ и Яндекс"},
                    {"title": "Курс по Pandas", "url": "https://stepik.org/course/77845/", "description": "Интерактивный курс по библиотеке Pandas"}
                ],
                "визуализация": [
                    {"title": "Plotly Documentation", "url": "https://plotly.com/python/", "description": "Руководство по созданию интерактивных визуализаций"},
                    {"title": "Seaborn Tutorial", "url": "https://seaborn.pydata.org/tutorial.html", "description": "Учебник по библиотеке Seaborn"},
                    {"title": "D3.js Gallery", "url": "https://observablehq.com/@d3/gallery", "description": "Галерея примеров визуализации на D3.js"}
                ]
            },
            "дизайнер": {
                "общие": [
                    {"title": "Обучение в Figma", "url": "https://help.figma.com/hc/en-us/categories/360002051613-Get-Started", "description": "Официальные руководства по Figma"},
                    {"title": "Дизайн-курсы от Skillbox", "url": "https://skillbox.ru/design/", "description": "Подборка бесплатных материалов по дизайну"},
                    {"title": "Behance", "url": "https://www.behance.net/", "description": "Платформа для вдохновения и портфолио"}
                ],
                "ui": [
                    {"title": "UI Design Daily", "url": "https://www.uidesigndaily.com/", "description": "Ежедневные UI компоненты для вдохновения"},
                    {"title": "UI/UX Design Patterns", "url": "https://uipatterns.io/", "description": "Коллекция паттернов UI/UX дизайна"},
                    {"title": "Material Design", "url": "https://material.io/design", "description": "Руководство по дизайну от Google"}
                ],
                "ux": [
                    {"title": "Nielsen Norman Group", "url": "https://www.nngroup.com/articles/", "description": "Статьи о пользовательском опыте"},
                    {"title": "UX Planet", "url": "https://uxplanet.org/", "description": "Публикации о UX дизайне"},
                    {"title": "Practical UX Methods", "url": "https://www.practical-ux-methods.com/", "description": "Практические методы UX исследований"}
                ],
                "типографика": [
                    {"title": "Typewolf", "url": "https://www.typewolf.com/", "description": "Ресурс о типографике и шрифтах"},
                    {"title": "Практическая типографика", "url": "https://www.artlebedev.ru/izdal/typography/", "description": "Классическая книга по типографике"},
                    {"title": "Google Fonts", "url": "https://fonts.google.com/", "description": "Бесплатные шрифты для использования в дизайне"}
                ]
            },
            "маркетолог": {
                "общие": [
                    {"title": "HubSpot Academy", "url": "https://academy.hubspot.com/", "description": "Бесплатные курсы по маркетингу"},
                    {"title": "Нетология: Маркетинг", "url": "https://netology.ru/marketing", "description": "Бесплатные материалы по маркетингу"},
                    {"title": "Marketing Teaching", "url": "https://blog.marketingteaching.ru/", "description": "Образовательный блог о маркетинге"}
                ],
                "smm": [
                    {"title": "SMM Planner", "url": "https://smmplanner.com/blog/", "description": "Блог о SMM"},
                    {"title": "Buffer Resources", "url": "https://buffer.com/resources/", "description": "Ресурсы для SMM специалистов"},
                    {"title": "ВКонтакте для бизнеса", "url": "https://vk.com/business", "description": "Руководства по маркетингу в ВКонтакте"}
                ],
                "контент-маркетинг": [
                    {"title": "Content Marketing Institute", "url": "https://contentmarketinginstitute.com/", "description": "Ресурс о контент-маркетинге"},
                    {"title": "Блог Texterra", "url": "https://texterra.ru/blog/", "description": "Статьи о контент-маркетинге"},
                    {"title": "Школа контент-маркетинга", "url": "https://semrush.com/academy/courses/content-marketing", "description": "Бесплатный курс по контент-маркетингу"}
                ],
                "аналитика": [
                    {"title": "Google Analytics Academy", "url": "https://analytics.google.com/analytics/academy/", "description": "Бесплатные курсы по Google Analytics"},
                    {"title": "Основы Яндекс.Метрики", "url": "https://yandex.ru/adv/edu/metrika-start", "description": "Руководство по Яндекс.Метрике"},
                    {"title": "DataReporter", "url": "https://datareporter.ru/", "description": "Блог об аналитике для маркетологов"}
                ]
            },
            "аналитик": {
                "общие": [
                    {"title": "Аналитика от Яндекс Практикум", "url": "https://practicum.yandex.ru/data-analyst/", "description": "Материалы по аналитике данных"},
                    {"title": "SkillFactory: Аналитика", "url": "https://skillfactory.ru/analytics", "description": "Бесплатные материалы по аналитике"},
                    {"title": "AnalyticsVidhya", "url": "https://www.analyticsvidhya.com/", "description": "Ресурс для аналитиков данных"}
                ],
                "sql": [
                    {"title": "SQL Academy", "url": "https://sql-academy.org/ru", "description": "Интерактивный курс по SQL"},
                    {"title": "PostgreSQL Tutorial", "url": "https://www.postgresqltutorial.com/", "description": "Туториалы по PostgreSQL"},
                    {"title": "Практический курс SQL", "url": "https://stepik.org/course/63054/", "description": "Курс на Stepik"}
                ],
                "bi": [
                    {"title": "Power BI от Microsoft", "url": "https://learn.microsoft.com/ru-ru/power-bi/", "description": "Руководства по Power BI"},
                    {"title": "Tableau Public", "url": "https://public.tableau.com/en-us/s/resources", "description": "Ресурсы по Tableau"},
                    {"title": "Datalens документация", "url": "https://datalens.yandex/docs", "description": "Документация по Yandex DataLens"}
                ],
                "статистика": [
                    {"title": "Анализ данных в Python", "url": "https://stepik.org/course/126346/", "description": "Курс по анализу данных"},
                    {"title": "Основы статистики", "url": "https://stepik.org/course/76/", "description": "Базовый курс по статистике"},
                    {"title": "StatSoft", "url": "http://www.statsoft.ru/home/textbook/", "description": "Электронный учебник по статистике"}
                ]
            }
        }
        
        # Словарь с ключевыми словами для сопоставления тем и ресурсов
        keywords = {
            "сети": ["сеть", "сетевой", "network", "cisco", "routing", "маршрутизация", "коммутация", "switching", "tcp/ip", "dns", "dhcp", "vlan"],
            "безопасность": ["безопасность", "security", "защита", "encryption", "шифрование", "firewall", "брандмауэр", "уязвимость", "vulnerability", "атака", "attack", "пентест", "pentest"],
            "операционные системы": ["windows", "linux", "unix", "операционная система", "ubuntu", "debian", "centos", "red hat", "системное администрирование", "administration"],
            "программирование": ["1с", "1c", "программирование", "разработка", "конфигурирование", "метаданные", "справочники", "программист", "разработчик", "developer", "coding", "алгоритм"],
            "frontend": ["javascript", "html", "css", "react", "vue", "angular", "фронтенд", "интерфейс", "верстка", "webpack", "typescript", "sass", "less"],
            "backend": ["server", "django", "flask", "node.js", "php", "ruby", "backend", "бэкенд", "сервер", "api", "rest", "express", "spring", "laravel", "symfony"],
            "базы данных": ["sql", "database", "база данных", "субд", "postgresql", "mysql", "oracle", "mongodb", "sqlite", "nosql", "replication", "репликация", "индексы", "запрос", "query"],
            "devops": ["docker", "kubernetes", "ci/cd", "jenkins", "gitlab", "github actions", "автоматизация", "automation", "деплой", "deployment", "контейнер", "container", "инфраструктура", "infrastructure"],
            "машинное обучение": ["ml", "machine learning", "машинное обучение", "нейронная сеть", "neural network", "ai", "искусственный интеллект", "deep learning", "глубокое обучение", "модель", "алгоритм", "классификация", "регрессия"],
            "python": ["python", "питон", "pandas", "numpy", "scipy", "matplotlib", "sklearn", "tensorflow", "pytorch", "jupyter", "anaconda", "django", "flask"],
            "визуализация": ["visualization", "визуализация", "dashboard", "дашборд", "chart", "график", "диаграмма", "tableau", "power bi", "superset", "grafana", "d3.js", "plotly", "seaborn"],
            "ui": ["ui", "интерфейс", "дизайн", "design", "макет", "layout", "компонент", "component", "сетка", "grid", "адаптивный", "responsive", "figma", "sketch", "adobe xd"],
            "ux": ["ux", "usability", "юзабилити", "пользовательский опыт", "user experience", "исследование", "research", "прототип", "prototype", "тестирование", "testing", "персона", "persona"],
            "типографика": ["typography", "типографика", "шрифт", "font", "текст", "text", "заголовок", "heading", "контраст", "contrast", "читаемость", "readability"],
            "smm": ["smm", "social media", "социальные сети", "контент", "content", "таргетинг", "targeting", "аудитория", "audience", "engagement", "вовлеченность", "продвижение", "promotion"],
            "контент-маркетинг": ["content marketing", "контент-маркетинг", "статья", "article", "блог", "blog", "копирайтинг", "copywriting", "редактура", "editing", "seo", "оптимизация", "optimization"],
            "аналитика": ["analytics", "аналитика", "метрики", "metrics", "google analytics", "яндекс метрика", "yandex metrica", "conversion", "конверсия", "reporting", "отчетность", "attribution", "атрибуция"],
            "sql": ["sql", "запрос", "query", "база данных", "database", "таблица", "table", "join", "объединение", "группировка", "group by", "индекс", "index", "оптимизация запросов", "query optimization"],
            "bi": ["bi", "business intelligence", "бизнес-аналитика", "dashboard", "дашборд", "отчет", "report", "визуализация", "visualization", "power bi", "tableau", "qlik", "datalens", "superset"],
            "статистика": ["statistics", "статистика", "вероятность", "probability", "распределение", "distribution", "выборка", "sample", "корреляция", "correlation", "регрессия", "regression", "анализ данных", "data analysis"],
            "мониторинг": ["monitoring", "мониторинг", "наблюдение", "alerting", "оповещение", "zabbix", "nagios", "prometheus", "grafana", "логи", "logs", "метрики", "metrics", "трассировка", "tracing"],
            "автоматизация": ["automation", "автоматизация", "скрипт", "script", "powershell", "bash", "ansible", "puppet", "chef", "terraform", "iac", "infrastructure as code", "ci/cd", "pipeline"]
        }
        
        # Нормализация названия профессии
        profession_lower = profession.lower()
        
        # Выбираем базовую категорию профессии
        profession_category = None
        if any(x in profession_lower for x in ["админ", "сисадмин", "system admin", "network", "системный администратор"]):
            profession_category = "системный администратор"
        elif any(x in profession_lower for x in ["1с", "1c", "предприятие"]):
            profession_category = "программист 1с"
        elif any(x in profession_lower for x in ["web", "веб", "frontend", "backend", "фронтенд", "бэкенд", "разработчик", "программист", "developer"]):
            profession_category = "веб-разработчик"
        elif any(x in profession_lower for x in ["data", "данные", "аналитик", "scientist", "ml", "машинное обучение", "статистика", "статистик"]):
            profession_category = "data scientist"
        elif any(x in profession_lower for x in ["дизайн", "designer", "ui", "ux", "интерфейс", "графика", "web design", "product design"]):
            profession_category = "дизайнер"
        elif any(x in profession_lower for x in ["маркетинг", "marketing", "smm", "контент", "реклама", "promotion", "pr", "public relations"]):
            profession_category = "маркетолог"
        elif any(x in profession_lower for x in ["аналитик", "analyst", "analytics", "bi", "business intelligence", "аналитика"]):
            profession_category = "аналитик"
        
        result = {}
        
        # Добавляем общие ресурсы для категории профессии, если она определена
        if profession_category and profession_category in free_resources:
            result["Общие ресурсы по профессии"] = free_resources[profession_category].get("общие", [])
        
        # Находим релевантные ресурсы для каждой темы
        for topic in topics:
            topic_lower = topic.lower()
            resources_for_topic = []
            
            # Определяем категории ключевых слов, присутствующих в теме
            matching_categories = []
            for category, words in keywords.items():
                if any(word in topic_lower for word in words):
                    matching_categories.append(category)
            
            # Если найдены совпадения и определена категория профессии
            if matching_categories and profession_category and profession_category in free_resources:
                for category in matching_categories:
                    if category in free_resources[profession_category]:
                        resources_for_topic.extend(free_resources[profession_category][category])
            
            # Если есть ресурсы для темы, добавляем их в результат
            if resources_for_topic:
                result[topic] = resources_for_topic
        
        # Если категория профессии не определена или нет ресурсов, добавляем универсальные
        if not result or len(result) <= 1:
            # Добавляем универсальные ресурсы для любой профессии
            universal_resources = [
                {"title": "Coursera", "url": "https://www.coursera.org/", "description": "Платформа с курсами от ведущих университетов (многие доступны для бесплатного просмотра)"},
                {"title": "edX", "url": "https://www.edx.org/", "description": "Курсы от ведущих университетов мира"},
                {"title": "Stepik", "url": "https://stepik.org/", "description": "Платформа с множеством бесплатных курсов на русском языке"},
                {"title": "YouTube", "url": "https://www.youtube.com/", "description": "Огромное количество бесплатных обучающих видео по любой теме"},
                {"title": "Хабр", "url": "https://habr.com/ru/", "description": "Статьи и туториалы по информационным технологиям"},
                {"title": "LinkedIn Learning", "url": "https://www.linkedin.com/learning/", "description": "Курсы по различным профессиональным навыкам (некоторые бесплатные)"},
                {"title": "Открытое образование", "url": "https://openedu.ru/", "description": "Платформа с бесплатными онлайн-курсами от ведущих вузов России"},
                {"title": "Академия Яндекса", "url": "https://academy.yandex.ru/", "description": "Образовательные проекты Яндекса по различным IT-направлениям"}
            ]
            
            result["Универсальные ресурсы"] = universal_resources
        
        # Ограничиваем количество ресурсов для каждой темы (не более 5)
        for topic, resources in result.items():
            result[topic] = resources[:5]
        
        return result