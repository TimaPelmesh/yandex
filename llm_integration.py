import requests
import json
import os
import pickle
import time
from typing import Dict, List, Any, Optional, Union
import logging
import re
import hashlib
import traceback

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("llm_integration.log"), logging.StreamHandler()]
)
logger = logging.getLogger("llm_integration")

class LocalLLM:
    """Класс для взаимодействия с локальной моделью через LM Studio API"""
    
    def __init__(self, 
                 api_base: str = "http://127.0.0.1:1234/v1",
                 cache_dir: str = "model/cache",
                 model: str = "qwen3-8b",
                 system_prompt: str = """Ты - опытный карьерный консультант и эксперт по профориентации с 15-летним опытом работы. 
Ты специализируешься на составлении детальных и персонализированных карьерных планов.
Твои ответы всегда:
1. Максимально конкретные и подробные
2. Основаны на актуальных данных рынка труда
3. Структурированы и логически выстроены
4. Полностью на русском языке
5. Адаптированы под индивидуальные особенности пользователя

При работе с форматом JSON:
- Ты строго следуешь запрошенной структуре данных
- Возвращаешь только валидный JSON без дополнительных комментариев
- Не используешь вложенные структуры, если это не требуется в запросе
- Проверяешь валидность JSON перед отправкой ответа

Ты отвечаешь детально, предоставляя от 5 до 10 пунктов в каждом разделе, когда это уместно."""):
        """
        Инициализирует объект LLM для работы с локальной моделью через API
        
        Args:
            api_base (str): Базовый URL для API
            cache_dir (str): Директория для кеша ответов
            model (str): Название модели для использования
            system_prompt (str): Системный промпт для модели
        """
        try:
            # Разбираем api_base на хост и порт
            if api_base.startswith('http://'):
                # Извлекаем хост и порт из URL
                parsed_url = api_base.replace('http://', '').split('/')
                if ':' in parsed_url[0]:
                    host_port = parsed_url[0].split(':')
                    self.host = host_port[0]
                    self.port = host_port[1]
                else:
                    self.host = parsed_url[0]
                    self.port = "1234"  # Порт по умолчанию
            else:
                # Если URL не содержит протокол, используем значения по умолчанию
                self.host = "127.0.0.1"
                self.port = "1234"
                
            logger.info(f"Инициализация LLM с хостом: {self.host}, портом: {self.port}")
        except Exception as e:
            logger.error(f"Ошибка при разборе URL API: {e}")
            # Устанавливаем значения по умолчанию в случае ошибки
            self.host = "127.0.0.1"
            self.port = "1234"
        
        self.api_base = api_base
        self.model = model
        self.system_prompt = system_prompt
        
        # Создаем директорию для кеша, если она не существует
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Путь к файлу кеша
        self.cache_file = os.path.join(self.cache_dir, "llm_cache.json")
        
        # Загружаем кеш, если он существует
        self.cache = self._load_cache()
        
        # Проверяем доступность сервера
        self._check_server()
    
    def _check_server(self) -> bool:
        """Проверяет доступность сервера LM Studio"""
        try:
            response = requests.get(f"{self.api_base}/models")
            if response.status_code == 200:
                logger.info(f"LM Studio доступен и работает. Модели: {response.json()}")
                return True
            else:
                logger.warning(f"LM Studio недоступен, код ответа: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке LM Studio: {e}")
            return False
    
    def _load_cache(self) -> Dict:
        """Загружает кеш из файла"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Ошибка при загрузке кеша: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """Сохраняет кеш в файл"""
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Ошибка при сохранении кеша: {e}")
    
    def generate(self, 
                prompt: str, 
                use_cache: bool = False,
                max_tokens: int = 2048,
                temperature: float = 0.5,
                top_p: float = 0.9,
                include_system_prompt: bool = True) -> Optional[str]:
        """
        Генерирует ответ модели на основе промпта
        
        Args:
            prompt: Текст промпта
            use_cache: Использовать ли кеш
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура генерации (0.1 - 1.0)
            top_p: Параметр top_p для генерации
            include_system_prompt: Включать ли системный промпт
            
        Returns:
            Сгенерированный текст или None в случае ошибки
        """
        # Сокращенный ключ кеша для более эффективного поиска
        cache_key = f"{prompt}_{max_tokens}_{temperature}"
        if use_cache and cache_key in self.cache:
            logger.info("Используем кешированный ответ")
            return self.cache[cache_key]
        
        messages = []
        
        if include_system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response_text = self._generate_with_llm(
            messages=messages, 
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )
        
        if not response_text:
            logger.warning("Получен пустой ответ от модели")
            return None
        
        # Удаляем теги <think> из ответа
        clean_response = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL) 
        
        # Также удаляем все оставшиеся теги <think> и </think> (на случай, если некоторые не закрыты)
        clean_response = clean_response.replace('<think>', '').replace('</think>', '')
        
        # Сохраняем очищенные ответы для отладки
        try:
            debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model', 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            with open(os.path.join(debug_dir, "last_raw_response.txt"), "w", encoding="utf-8") as f:
                f.write(response_text)
            with open(os.path.join(debug_dir, "last_clean_response.txt"), "w", encoding="utf-8") as f:
                f.write(clean_response)
        except Exception as e:
            logger.warning(f"Не удалось сохранить очищенный ответ: {e}")
        
        # Для моделей qwen, которые могут возвращать ответ внутри JSON-структуры
        if not clean_response.strip() and "content" in response_text:
            try:
                # Пытаемся извлечь содержимое из JSON-структуры
                match = re.search(r'"content"\s*:\s*"(.*?)"(?:,|})(?![^{]*})', response_text, re.DOTALL)
                if match:
                    extracted_content = match.group(1)
                    # Удаляем экранированные кавычки и переносы строк
                    clean_content = extracted_content.replace('\\"', '"').replace('\\n', '\n')
                    logger.info("Успешно извлечен контент из JSON-структуры ответа")
                    clean_response = clean_content
            except Exception as ex:
                logger.error(f"Ошибка при извлечении content из JSON: {ex}")
        
        # Если ответ все еще пустой, попробуем агрессивно извлечь текст между тегами assistant
        if not clean_response.strip() and "<assistant>" in response_text:
            try:
                # Ищем текст между <assistant> и </assistant>
                assistant_match = re.search(r'<assistant>(.*?)</assistant>', response_text, re.DOTALL)
                if assistant_match:
                    assistant_text = assistant_match.group(1)
                    logger.info("Извлечен текст из тегов <assistant>")
                    clean_response = assistant_text
            except Exception as ex:
                logger.error(f"Ошибка при извлечении текста из тегов assistant: {ex}")
        
        # Если после всех обработок текст стал пустым, используем оригинальный текст без тегов
        if not clean_response.strip():
            logger.warning("После обработки ответ пустой, использую JSON-извлечение")
            clean_response = self._aggressive_json_extract(response_text)
            if isinstance(clean_response, dict):
                # Вернулся словарь, преобразуем его в JSON-строку
                clean_response = json.dumps(clean_response, ensure_ascii=False, indent=2)
                logger.info("Получен JSON после агрессивного извлечения")
        
        final_response = clean_response.strip() if isinstance(clean_response, str) else json.dumps(clean_response, ensure_ascii=False, indent=2)
        
        # Сохраняем в кеш
        if use_cache and final_response:
            self.cache[cache_key] = final_response
            self._save_cache()
        
        logger.info(f"Финальный ответ после обработки: {len(final_response)} символов")
        return final_response
    
    def generate_roadmap(self, profession: str, region: str, user_info: str = "") -> Dict:
        """
        Генерирует структурированный карьерный план для указанной профессии
        
        Args:
            profession (str): Название профессии
            region (str): Регион (для учета региональной специфики)
            user_info (str): Информация о пользователе для персонализации
            
        Returns:
            Dict: Структурированный план карьерного развития
        """
        logger.info(f"Генерация карьерного плана для профессии '{profession}' в регионе '{region}'")
        
        if not profession:
            logger.error("Не указана профессия для генерации плана")
            return {}
            
        # Проверяем доступность LM Studio перед началом генерации
        if not self._check_server():
            logger.error("LM Studio недоступен, невозможно сгенерировать карьерный план")
            return {}
        
        # Формируем запрос для модели
        prompt = f"""Ты - опытный карьерный консультант и эксперт по профориентации с 15-летним опытом работы. Сгенерируй детальный, конкретный карьерный план для профессии "{profession}" в регионе "{region}" в формате JSON.

В результат должны входить следующие разделы:
1. hardSkills - список из 5-7 ключевых технических навыков, необходимых в профессии (ОБЯЗАТЕЛЬНО с уровнем владения и конкретными примерами применения)
2. softSkills - список из 5-7 важных нетехнических навыков для успеха в профессии (с указанием конкретных рабочих ситуаций, где они применяются)
3. learningPlan - список из 6-8 последовательных шагов обучения с КОНКРЕТНЫМИ и СОДЕРЖАТЕЛЬНЫМИ названиями каждого шага и подробным описанием (минимум 200-300 символов на каждое описание)
4. futureInsights - список из 4-5 актуальных тенденций в профессии на ближайшие 2-3 года с конкретными примерами влияния на работу

{f"Информация о пользователе для персонализации: {user_info}" if user_info else ""}

ВАЖНО ПО ОФОРМЛЕНИЮ ПЛАНА ОБУЧЕНИЯ (learningPlan):
1. Каждый шаг ДОЛЖЕН иметь конкретное, информативное название (например, "Освоение инструментов для работы с базами данных PostgreSQL" вместо общего "Шаг 3" или "Освоение навыков")
2. Описание ДОЛЖНО быть подробным и включать:
   - Конкретные темы для изучения (с примерами)
   - Практические навыки, которые нужно освоить
   - Как эти знания применяются в реальной работе
   - Рекомендуемую продолжительность этапа
3. НЕ указывай конкретные курсы, книги или ресурсы - только темы и навыки
4. Убедись, что шаги выстроены в логической последовательности от базовых к продвинутым
5. Приоритет информативности и конкретности над краткостью

Верни ответ строго в формате JSON, без дополнительного текста вне JSON структуры. Формат должен быть таким:
```json
{{
  "hardSkills": ["Конкретный навык 1 с уровнем и примерами", "Конкретный навык 2 с уровнем и примерами", ...],
  "softSkills": ["Конкретный навык 1 с примерами ситуаций", "Конкретный навык 2 с примерами ситуаций", ...],
    "learningPlan": [
        {{
      "title": "Конкретное информативное название шага 1",
      "description": "Подробное детальное описание шага 1 с перечислением конкретных тем, практических навыков и их применения. Минимум 200-300 символов."
    }},
    ...
  ],
  "futureInsights": ["Конкретный тренд 1 с примерами влияния", "Конкретный тренд 2 с примерами влияния", ...]
}}
```

ВАЖНО: В секции learningPlan НЕ УПОМИНАЙ конкретные ресурсы, книги, курсы или сайты. Указывай ТОЛЬКО ТЕМЫ для изучения и НАВЫКИ для освоения, без рекомендаций по учебным материалам.
"""

        # Используем общий метод для стандартного плана обучения
        logger.info(f"Использую стандартный план обучения для профессии: {profession}")
        
        # Подготавливаем структуру для результата по умолчанию
        if profession.lower() in ["повар", "шеф-повар", "кулинар"]:
            default_hard_skills = [
                "Знание технологии приготовления различных блюд, включая русскую и европейскую кухню",
                "Умение работать с профессиональным кухонным оборудованием (пароконвектоматы, шоковая заморозка)",
                "Знание санитарных норм и правил безопасности в соответствии с СанПиН",
                "Навыки профессиональной нарезки продуктов разного типа и текстуры",
                "Знание сезонных продуктов и умение составлять меню с их использованием"
            ]
            default_soft_skills = [
                "Работа в команде - умение эффективно коммуницировать в условиях горячего цеха",
                "Стрессоустойчивость - способность сохранять концентрацию во время пиковых нагрузок",
                "Умение работать в условиях многозадачности, выполняя несколько операций одновременно",
                "Пунктуальность - строгое соблюдение таймингов приготовления блюд",
                "Внимание к деталям, особенно в части презентации блюд и контроля качества"
            ]
            default_future_insights = [
                f"Рост спроса на национальную кухню в регионе {region}, особенно на локальные продукты",
                "Тренд на использование сезонных локальных продуктов с минимальным углеродным следом",
                "Увеличение спроса на здоровое питание, включая блюда для веганов и безглютеновые опции",
                "Развитие направления онлайн мастер-классов по кулинарии как дополнительный источник дохода шеф-поваров"
            ]
        else:
            default_hard_skills = [
                f"Ключевой профессиональный навык для {profession} с указанием конкретных инструментов",
                f"Основные технологии в профессии {profession} с примерами применения",
                f"Специализированное программное обеспечение для {profession} с указанием версий",
                f"Методологии работы в сфере {profession} с конкретными примерами",
                f"Технические стандарты в профессии {profession} с требуемым уровнем знаний"
            ]
            default_soft_skills = [
                "Эффективная коммуникация с различными типами стейкхолдеров в профессиональном контексте",
                "Адаптивность к быстро меняющимся технологиям и требованиям в профессиональной сфере", 
                "Навыки командной работы с использованием современных инструментов коллаборации", 
                "Организованность и управление временем с применением методик тайм-менеджмента",
                "Аналитическое мышление для решения комплексных профессиональных задач"
            ]
            default_future_insights = [
                f"Изменение требований к специалистам {profession} в {region} в ближайшие 2-3 года",
                f"Рост средней заработной платы в сфере {profession} на 15-20% в течение следующих 3-5 лет",
                f"Появление новых специализаций внутри профессии {profession} из-за технологических изменений",
                f"Увеличение спроса на специалистов {profession} со знанием смежных областей и технологий"
            ]
        
        default_result = {
            "hardSkills": default_hard_skills,
            "softSkills": default_soft_skills,
            "learningPlan": self._get_default_learning_plan(profession),
            "futureInsights": default_future_insights
        }
        
        # Делаем несколько попыток получить валидный JSON от модели с разными температурами
        for attempt in range(1, 4):
            logger.info(f"Попытка {attempt} получить карьерный план")
            
            # Для модели qwen3-8b используем более низкую температуру
            temperature = 0.1 if attempt == 1 else 0.05 if attempt == 2 else 0.02
            max_tokens = 4096  # Максимальное количество токенов для ответа
            
            response_text = self.generate(prompt, temperature=temperature, max_tokens=max_tokens)
            
            # Если ответ пустой, переходим к следующей попытке
            if not response_text:
                logger.warning(f"Получен пустой ответ в попытке {attempt}")
                continue
            
            # Сохраняем оригинальный ответ для отладки
            try:
                debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model', 'debug')
                os.makedirs(debug_dir, exist_ok=True)
                with open(os.path.join(debug_dir, f'roadmap_attempt_{attempt}.txt'), 'w', encoding='utf-8') as f:
                    f.write(response_text)
            except Exception as e:
                logger.warning(f"Не удалось сохранить ответ для отладки: {e}")
            
            # Очищаем ответ от возможных текстовых обрамлений
            cleaned_response = response_text
            
            # Удаляем маркеры кода markdown, если они есть
            cleaned_response = re.sub(r'^```json\s*', '', cleaned_response)
            cleaned_response = re.sub(r'\s*```$', '', cleaned_response)
            
            # Удаляем вводный текст до начала JSON
            if '{' in cleaned_response:
                start_idx = cleaned_response.find('{')
                cleaned_response = cleaned_response[start_idx:]
            
            # Удаляем текст после JSON
            if '}' in cleaned_response:
                end_idx = cleaned_response.rfind('}') + 1
                cleaned_response = cleaned_response[:end_idx]
            
            logger.info(f"Очищенный ответ: {cleaned_response[:100]}...")
            
            # Пробуем извлечь JSON из очищенного ответа
            try:
                roadmap = json.loads(cleaned_response)
                logger.info("Успешно извлечен JSON из очищенного ответа")
                
                # Проверяем наличие необходимых полей и корректность их формата
                is_valid = True
                
                # Проверка hardSkills
                if 'hardSkills' not in roadmap or not isinstance(roadmap['hardSkills'], list) or len(roadmap['hardSkills']) < 3:
                    logger.warning("Отсутствуют или недостаточно hardSkills")
                    is_valid = False
                    # Если поле есть, но некорректное - исправляем
                    if 'hardSkills' in roadmap and (not isinstance(roadmap['hardSkills'], list) or len(roadmap['hardSkills']) < 3):
                        roadmap['hardSkills'] = default_hard_skills
                
                # Проверка softSkills
                if 'softSkills' not in roadmap or not isinstance(roadmap['softSkills'], list) or len(roadmap['softSkills']) < 3:
                    logger.warning("Отсутствуют или недостаточно softSkills")
                    is_valid = False
                    # Если поле есть, но некорректное - исправляем
                    if 'softSkills' in roadmap and (not isinstance(roadmap['softSkills'], list) or len(roadmap['softSkills']) < 3):
                        roadmap['softSkills'] = default_soft_skills
                
                # Проверка learningPlan
                if 'learningPlan' not in roadmap or not isinstance(roadmap['learningPlan'], list) or len(roadmap['learningPlan']) < 3:
                    logger.warning("Отсутствует или недостаточно этапов в learningPlan")
                    is_valid = False
                    # Если поле есть, но некорректное - исправляем
                    if 'learningPlan' in roadmap and (not isinstance(roadmap['learningPlan'], list) or len(roadmap['learningPlan']) < 3):
                        roadmap['learningPlan'] = self._get_default_learning_plan(profession)
                
                # Проверка futureInsights
                if 'futureInsights' not in roadmap or not isinstance(roadmap['futureInsights'], list) or len(roadmap['futureInsights']) < 3:
                    logger.warning("Отсутствуют или недостаточно futureInsights")
                    is_valid = False
                    # Если поле есть, но некорректное - исправляем
                    if 'futureInsights' in roadmap and (not isinstance(roadmap['futureInsights'], list) or len(roadmap['futureInsights']) < 3):
                        roadmap['futureInsights'] = default_future_insights
                
                # Если план в целом валидный или мы исправили все проблемы, возвращаем его
                if is_valid:
                    logger.info(f"Успешно сгенерирован карьерный план в попытке {attempt}")
                    return roadmap
                else:
                    # Если удалось извлечь JSON, но некоторые поля отсутствуют или некорректны,
                    # добавляем недостающие поля из дефолтных значений
                    for key in default_result:
                        if key not in roadmap or not roadmap[key]:
                            roadmap[key] = default_result[key]
                    
                    logger.info("Карьерный план был неполным, но успешно дополнен недостающими полями")
                    return roadmap
                    
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при разборе JSON: {e}")
                # Продолжаем цикл для следующей попытки
            
            # Если с прямым извлечением не получилось, пробуем агрессивные методы
            if attempt == 3:  # На последней попытке
                try:
                    # Пробуем извлечь JSON агрессивным методом
                    roadmap = self._aggressive_json_extract(response_text)
                    
                    # Если что-то удалось извлечь
                    if roadmap:
                        logger.info("Удалось извлечь JSON агрессивным методом")
                        
                        # Проверяем и дополняем недостающие поля
                        for key in default_result:
                            if key not in roadmap or not roadmap[key]:
                                roadmap[key] = default_result[key]
                                
                        return roadmap
                        
                except Exception as e:
                    logger.error(f"Ошибка при агрессивном извлечении JSON: {e}")
        
        # Если все попытки неудачны, возвращаем значение по умолчанию
        logger.warning("Все попытки получить карьерный план не удались, возвращаю значение по умолчанию")
        
        return default_result
    
    def _generate_with_llm(self, messages, temperature=0.7, max_tokens=2048, top_p=0.9, user_prompt=None):
        """
        Генерирует ответ модели на основе сообщений
        
        Args:
            messages: Список сообщений для запроса
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов в ответе
            top_p: Параметр top_p для генерации
            user_prompt: Оригинальный запрос пользователя (для кеша)
            
        Returns:
            Сгенерированный текст
        """
        # Проверяем доступность сервера
        if not self._check_server():
            logger.error("LLM сервер недоступен")
            return None

        # Для кеширования нужно создать ключ на основе запроса
        if user_prompt:
            cache_key = hashlib.md5(user_prompt.encode()).hexdigest()
            result = self._get_from_cache(cache_key)
            if result:
                return result
        
        # Подготовка сообщений в формате ChatML
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"], 
                "content": msg["content"]
            })
        
        # Устанавливаем таймаут в зависимости от модели
        # qwen3-8b требует больше времени для генерации
        if "qwen" in self.model.lower():
            base_timeout_seconds = 600  # 10 минут для qwen моделей
            logger.info(f"Установлен увеличенный таймаут {base_timeout_seconds} секунд для модели {self.model}")
        else:
            base_timeout_seconds = 300  # 5 минут для других моделей
            
        # Формируем запрос к API
        api_url = f"http://{self.host}:{self.port}/v1/chat/completions"
        
        # Проверяем, что выбранная модель доступна
        available_models = self._get_available_models()
        if available_models and self.model not in available_models:
            logger.warning(f"Модель {self.model} не найдена среди доступных моделей: {available_models}")
            # Если модель недоступна, используем первую доступную
            if available_models:
                logger.info(f"Переключение на доступную модель: {available_models[0]}")
                self.model = available_models[0]
        
        # Составляем тело запроса
        request_body = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False
        }
        
        # Выполняем запрос с повторными попытками
        max_retries = 3
        current_retry = 0
        timeout_seconds = base_timeout_seconds
        
        while current_retry < max_retries:
            current_retry += 1
            logger.info(f"Попытка {current_retry} из {max_retries} для модели {self.model}")
            
            if current_retry > 1:
                # Между повторными попытками делаем паузу
                time.sleep(2)
                # Увеличиваем таймаут при каждой следующей попытке
                timeout_seconds = base_timeout_seconds + (current_retry - 1) * 120
                logger.info(f"Установлен увеличенный таймаут {timeout_seconds} секунд")
                
            try:
                logger.info(f"Отправка запроса к {api_url} для модели {self.model}")
                response = requests.post(
                    api_url,
                    json=request_body,
                    timeout=timeout_seconds
                )
                
                # Сохраняем весь ответ для отладки
                try:
                    debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model', 'debug')
                    os.makedirs(debug_dir, exist_ok=True)
                    with open(os.path.join(debug_dir, "api_response.json"), "w", encoding="utf-8") as f:
                        f.write(response.text)
                except Exception as e:
                    logger.warning(f"Не удалось сохранить API ответ: {e}")
                
                # Проверяем код ответа
                if response.status_code != 200:
                    logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                    if current_retry < max_retries:
                        logger.info(f"Повторная попытка {current_retry + 1}...")
                        continue
                    return None
                
                # Пытаемся распарсить JSON ответ
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка парсинга JSON ответа: {e}")
                    logger.error(f"Ответ API: {response.text[:500]}...")
                    if current_retry < max_retries:
                        continue
                    return None
                
                # Проверяем структуру ответа
                if 'choices' not in data or not data['choices'] or 'message' not in data['choices'][0]:
                    logger.error(f"Некорректная структура ответа: {data}")
                    if current_retry < max_retries:
                        continue
                    return None
                
                # Извлекаем содержимое ответа
                if 'content' in data['choices'][0]['message'] and data['choices'][0]['message']['content']:
                    content = data['choices'][0]['message']['content']
                    
                    # Проверка на очень короткие ответы (потенциально некорректные)
                    if len(content.strip()) < 10 and current_retry < max_retries:
                        logger.warning(f"Получен слишком короткий ответ: '{content}', повторная попытка...")
                        continue
                    
                    # Если пришел корректный ответ, сохраняем в кеш и возвращаем
                    if user_prompt and content:
                        self._add_to_cache(cache_key, content)
                    return content
                    
                else:
                    # Для модели qwen проверяем, не находится ли контент внутри JSON в поле text
                    raw_message = data['choices'][0]['message']
                    if isinstance(raw_message, dict) and raw_message.get('role') == 'assistant' and 'content' in raw_message:
                        content = raw_message['content']
                        if content:
                            if user_prompt:
                                self._add_to_cache(cache_key, content)
                            return content
                            
                    logger.warning(f"Пустой контент в ответе модели: {data['choices'][0]['message']}")
                    if current_retry < max_retries:
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                logger.error(f"Превышено время ожидания ответа от API (таймаут {timeout_seconds} сек) в попытке {current_retry}")
                if current_retry < max_retries:
                    continue
                return None
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка запроса: {e}")
                logger.error(traceback.format_exc())
                if current_retry < max_retries:
                    continue
                return None
                
            except Exception as e:
                logger.error(f"Неизвестная ошибка при запросе к API: {e}")
                logger.error(traceback.format_exc())
                if current_retry < max_retries:
                    continue
                return None
                
        # Если все попытки исчерпаны, возвращаем None
        logger.error("Все попытки запроса к API исчерпаны, возвращаю None")
        return None

    def _get_default_learning_plan(self, profession):
        """
        Возвращает план обучения по умолчанию для указанной профессии
        
        Args:
            profession (str): Название профессии
            
        Returns:
            list: Список этапов обучения
        """
        # Определяем категорию профессии для более персонализированного плана
        profession_lower = profession.lower()
        profession_category = "общая"
        
        if any(keyword in profession_lower for keyword in ["админ", "сисадмин", "администратор", "devops"]):
            profession_category = "системный_администратор"
        elif any(keyword in profession_lower for keyword in ["разработчик", "программист", "developer", "coder"]):
            profession_category = "разработчик"
        elif any(keyword in profession_lower for keyword in ["дизайн", "designer", "ui", "ux"]):
            profession_category = "дизайнер"
        elif any(keyword in profession_lower for keyword in ["аналитик", "analyst", "data", "данные"]):
            profession_category = "аналитик"
        elif any(keyword in profession_lower for keyword in ["маркетолог", "smm", "маркетинг", "marketing"]):
            profession_category = "маркетолог"
        elif any(keyword in profession_lower for keyword in ["врач", "медик", "доктор", "medical"]):
            profession_category = "медицина"
        
        # Планы обучения для разных категорий профессий
        learning_plans = {
            "системный_администратор": [
                {
                    "title": "Освоение основ операционных систем",
                    "description": "Изучение архитектуры и принципов работы операционных систем Windows и Linux. Практика с базовыми командами, файловыми системами и права доступа в обеих ОС. Настройка пользовательских учетных записей, групп и разрешений безопасности. Понимание процессов загрузки и инициализации системы. Рекомендуемая продолжительность этапа: 6-8 недель с ежедневной практикой по 2-3 часа."
                },
                {
                    "title": "Изучение сетевых технологий и протоколов",
                    "description": "Глубокое погружение в модель OSI и стек протоколов TCP/IP. Настройка сетевых интерфейсов, маршрутизации и DNS. Практика с инструментами диагностики сети (ping, traceroute, netstat, tcpdump). Понимание принципов работы VPN, VLAN и беспроводных сетей. Настройка DHCP-сервера и управление IP-адресами. Работа с межсетевыми экранами и правилами фильтрации трафика. Продолжительность: 8-10 недель."
                },
                {
                    "title": "Управление серверной инфраструктурой",
                    "description": "Установка и настройка серверных ОС (Windows Server, Linux). Развертывание и администрирование веб-серверов (Apache, Nginx), почтовых серверов (Postfix, Exchange) и серверов баз данных (MySQL, PostgreSQL, MS SQL). Управление доменной структурой и службой каталогов (Active Directory, LDAP). Настройка групповых политик и автоматизация управления серверами. Планирование резервного копирования и восстановления данных. Продолжительность: 10-12 недель."
                },
                {
                    "title": "Обеспечение безопасности ИТ-инфраструктуры",
                    "description": "Разработка политик безопасности и их внедрение. Настройка межсетевых экранов и IDS/IPS систем. Управление антивирусной защитой и обновлениями безопасности. Аудит системных событий и мониторинг потенциальных угроз. Защита от сетевых атак и социальной инженерии. Шифрование данных и управление цифровыми сертификатами. Настройка двухфакторной аутентификации и других механизмов контроля доступа. Продолжительность: 8-10 недель."
                },
                {
                    "title": "Внедрение систем мониторинга и диагностики",
                    "description": "Установка и настройка систем мониторинга (Zabbix, Nagios, Prometheus). Создание панелей мониторинга для отслеживания производительности серверов и сетевого оборудования. Настройка оповещений о критических событиях и автоматическое реагирование. Сбор и анализ системных логов с использованием ELK-стека. Мониторинг доступности сервисов и исследование причин отказов. Анализ трендов производительности и планирование мощностей. Продолжительность: 6-8 недель."
                },
                {
                    "title": "Автоматизация задач администрирования",
                    "description": "Изучение языков и инструментов для автоматизации (PowerShell, Bash, Python). Создание скриптов для выполнения рутинных административных задач. Внедрение систем управления конфигурациями (Ansible, Puppet, Chef). Практика с инструментами непрерывной интеграции и доставки (CI/CD). Автоматизация развертывания серверов и приложений. Создание пайплайнов для автоматического тестирования и обновления инфраструктуры. Продолжительность: 8-10 недель."
                },
                {
                    "title": "Освоение облачных технологий и виртуализации",
                    "description": "Изучение принципов работы с облачными платформами (AWS, Azure, GCP). Развертывание виртуальных машин и контейнеров (VMware, Hyper-V, Docker). Управление облачной инфраструктурой через консоль и API. Настройка масштабирования и балансировки нагрузки. Управление ресурсами и оптимизация затрат в облаке. Обеспечение безопасности и соответствия требованиям в облачной среде. Построение гибридных инфраструктур. Продолжительность: 10-12 недель."
                }
            ],
            "разработчик": [
                {
                    "title": "Изучение основ программирования и алгоритмов",
                    "description": "Освоение синтаксиса выбранного языка программирования (Python, Java, JavaScript и т.д.). Изучение базовых структур данных (массивы, списки, словари, хеш-таблицы) и алгоритмов (сортировка, поиск, обход графов). Практика написания простых программ для решения алгоритмических задач. Понимание принципов структурного и объектно-ориентированного программирования. Освоение техник отладки и тестирования кода. Продолжительность: 8-10 недель интенсивного обучения."
                },
                {
                    "title": "Разработка пользовательских интерфейсов и клиентской части",
                    "description": "Изучение HTML, CSS и JavaScript для создания интерактивных веб-страниц. Освоение современных фреймворков для фронтенд-разработки (React, Angular, Vue). Работа с DOM и событиями браузера. Создание адаптивных интерфейсов, работающих на различных устройствах. Оптимизация производительности клиентских приложений. Изучение принципов UX/UI дизайна для создания удобных интерфейсов. Работа с AJAX и асинхронными запросами. Продолжительность: 10-12 недель."
                },
                {
                    "title": "Освоение серверной разработки и работы с базами данных",
                    "description": "Создание серверных приложений на выбранной технологии (Node.js, Django, Spring, ASP.NET). Изучение принципов работы с реляционными базами данных (MySQL, PostgreSQL) и языка SQL. Освоение ORM-технологий для взаимодействия с базами данных. Проектирование схем данных и оптимизация запросов. Работа с NoSQL базами данных (MongoDB, Redis) для специфических сценариев. Обеспечение безопасности доступа к данным. Изучение принципов REST API и микросервисной архитектуры. Продолжительность: 10-12 недель."
                },
                {
                    "title": "Внедрение методологий и инструментов разработки",
                    "description": "Освоение системы контроля версий Git и платформ для совместной разработки (GitHub, GitLab). Изучение принципов Agile-разработки, Scrum и Kanban. Внедрение практик непрерывной интеграции и доставки (CI/CD). Настройка автоматического тестирования и интеграционных тестов. Работа с инструментами управления проектами и отслеживания задач. Изучение методологий code review и парного программирования. Автоматизация сборки проектов и управление зависимостями. Продолжительность: 6-8 недель."
                },
                {
                    "title": "Создание масштабируемых и отказоустойчивых систем",
                    "description": "Изучение принципов проектирования высоконагруженных систем. Освоение техник оптимизации производительности и масштабирования приложений. Внедрение кэширования на различных уровнях системы. Работа с очередями сообщений и асинхронной обработкой (RabbitMQ, Kafka). Изучение паттернов проектирования для создания гибких и поддерживаемых систем. Обеспечение отказоустойчивости и разработка стратегий восстановления при сбоях. Мониторинг и профилирование приложений. Продолжительность: 8-10 недель."
                },
                {
                    "title": "Обеспечение безопасности и тестирование приложений",
                    "description": "Изучение основных уязвимостей веб-приложений (OWASP Top 10). Внедрение защиты от XSS, CSRF, SQL-инъекций и других атак. Работа с аутентификацией и авторизацией пользователей. Создание комплексной стратегии тестирования (модульные, интеграционные, функциональные тесты). Освоение инструментов для автоматизированного тестирования. Внедрение практик безопасной разработки в процесс создания приложений. Проведение код-ревью с фокусом на безопасность. Продолжительность: 8-10 недель."
                },
                {
                    "title": "Освоение DevOps-практик и облачных технологий",
                    "description": "Изучение принципов DevOps и культуры взаимодействия разработки и эксплуатации. Работа с контейнерами (Docker) и оркестрацией (Kubernetes). Автоматизация развертывания в облачных платформах (AWS, Azure, GCP). Настройка мониторинга и логирования в распределенных системах. Внедрение инфраструктуры как кода (Terraform, CloudFormation). Автоматизация управления конфигурациями (Ansible, Chef, Puppet). Оптимизация процессов доставки ПО и управления релизами. Продолжительность: 10-12 недель."
                }
            ],
            "дизайнер": [
                {
                    "title": "Освоение фундаментальных принципов дизайна",
                    "description": "Изучение основ композиции, цветоведения, типографики и теории визуального восприятия. Практическое применение принципов баланса, контраста, ритма, пропорции в дизайн-макетах. Понимание психологии цвета и создание гармоничных цветовых схем. Освоение типографических приемов и правил для улучшения читаемости и визуальной иерархии. Развитие насмотренности через анализ работ признанных дизайнеров. Создание первых проектов с применением изученных принципов. Продолжительность: 6-8 недель."
                },
                {
                    "title": "Изучение графических редакторов и инструментов дизайна",
                    "description": "Освоение профессиональных графических редакторов (Figma, Adobe Photoshop, Illustrator). Изучение интерфейса программ, горячих клавиш и оптимальных рабочих процессов. Работа с растровой и векторной графикой, слоями, масками, эффектами. Создание и редактирование графических элементов, иллюстраций, иконок. Настройка экспорта материалов для различных платформ и устройств. Освоение принципов работы с прототипирующими инструментами. Организация файлов и настройка системы хранения дизайн-материалов. Продолжительность: 8-10 недель."
                },
                {
                    "title": "Проектирование пользовательских интерфейсов (UI Design)",
                    "description": "Изучение основных элементов интерфейса и принципов их организации. Создание макетов для различных платформ (веб, мобильные приложения, десктоп). Освоение сеток и модульных систем для выравнивания элементов. Разработка системы стилей, компонентов и паттернов для последовательного дизайна. Создание адаптивных интерфейсов для различных размеров экранов. Работа с микроанимацией и интерактивными элементами. Освоение принципов доступности (accessibility) в дизайне. Продолжительность: 10-12 недель."
                },
                {
                    "title": "Изучение пользовательского опыта (UX Design)",
                    "description": "Освоение методологии проектирования, ориентированного на пользователя. Изучение методов исследования потребностей и поведения пользователей. Создание персон, сценариев использования и карт путей пользователей. Проектирование информационной архитектуры и структуры приложений. Разработка прототипов различной степени детализации (wireframes, mockups). Проведение юзабилити-тестирования и итерационное улучшение дизайна на основе обратной связи. Изучение метрик UX и способов измерения эффективности дизайн-решений. Продолжительность: 8-10 недель."
                },
                {
                    "title": "Создание профессионального портфолио",
                    "description": "Организация и структурирование лучших работ в портфолио. Написание кейс-стади с описанием процесса работы над проектами (проблема, решение, результат). Создание личного сайта-портфолио или профиля на специализированных платформах (Behance, Dribbble). Подготовка презентаций дизайн-проектов для потенциальных клиентов/работодателей. Получение обратной связи от профессионального сообщества и доработка портфолио. Регулярное обновление и поддержание актуальности представленных работ. Продолжительность: 4-6 недель."
                },
                {
                    "title": "Освоение специализированных направлений дизайна",
                    "description": "Углубленное изучение выбранной специализации: брендинг, упаковка, иллюстрация, motion-дизайн, 3D-моделирование и т.д. Освоение специфических инструментов и методик работы в выбранном направлении. Изучение отраслевых стандартов, форматов и требований. Создание специализированных проектов для расширения портфолио. Изучение успешных кейсов и лучших практик в выбранной области. Взаимодействие со специалистами смежных областей (разработчики, маркетологи, копирайтеры). Продолжительность: 10-12 недель."
                },
                {
                    "title": "Развитие навыков коммуникации и презентации дизайн-решений",
                    "description": "Освоение техник эффективной презентации дизайн-концепций клиентам и команде. Развитие навыков аргументации дизайн-решений на основе исследований и данных. Изучение методов получения и обработки обратной связи о дизайне. Освоение профессиональной терминологии для точной коммуникации с заказчиками и коллегами. Практика проведения дизайн-ревью и воркшопов. Развитие навыков ведения клиентских проектов и управления ожиданиями заказчика. Изучение принципов оценки трудозатрат и формирования коммерческих предложений. Продолжительность: 6-8 недель."
                }
            ],
            "общая": [
                {
                    "title": f"Освоение фундаментальных основ профессии {profession}",
                    "description": f"Изучение базовых концепций, терминологии и принципов работы в сфере профессии {profession}. Знакомство с историей развития отрасли и ключевыми методологиями. Понимание структуры рынка труда и основных требований работодателей. Освоение профессиональных стандартов и этических норм. Изучение актуальной законодательной базы, регулирующей отрасль. Формирование общего представления о карьерных путях в профессии и требуемых компетенциях на разных уровнях. Продолжительность: 6-8 недель интенсивного обучения."
                },
                {
                    "title": f"Развитие базовых технических навыков {profession}",
                    "description": f"Освоение основных инструментов и технологий, необходимых для работы в сфере {profession}. Изучение стандартных рабочих процессов и методик выполнения ключевых задач. Практика использования специализированного программного обеспечения и платформ. Отработка типовых профессиональных задач под руководством наставников. Изучение систем отчетности и документации, принятых в отрасли. Формирование навыков эффективной работы с профессиональными ресурсами и источниками информации. Продолжительность: 8-10 недель с практическими заданиями."
                },
                {
                    "title": f"Углубленное изучение специализированных областей {profession}",
                    "description": f"Детальное освоение отдельных направлений и специализаций в рамках профессии {profession}. Изучение продвинутых методик и подходов к решению сложных профессиональных задач. Работа с кейсами и реальными проектами для формирования практического опыта. Анализ успешных практик и типичных ошибок в профессиональной деятельности. Развитие критического мышления и аналитических навыков для принятия обоснованных решений. Формирование собственного профессионального подхода и стиля работы. Продолжительность: 10-12 недель углубленного изучения."
                },
                {
                    "title": f"Практическое применение знаний и навыков в проектной работе",
                    "description": f"Участие в полноценных проектах с применением полученных знаний о профессии {profession}. Решение комплексных задач, требующих интеграции различных навыков и технологий. Работа в команде и взаимодействие со специалистами смежных областей. Развитие навыков управления проектами и соблюдения сроков. Документирование процессов и результатов работы в соответствии с профессиональными стандартами. Получение и интеграция обратной связи для улучшения качества работы. Анализ эффективности применяемых подходов и методик. Продолжительность: 8-10 недель интенсивной практики."
                },
                {
                    "title": f"Создание и оптимизация профессионального портфолио",
                    "description": f"Систематизация выполненных проектов и работ для демонстрации профессиональных компетенций в сфере {profession}. Описание методологии, процессов и результатов каждого проекта. Фокусирование на демонстрации ключевых навыков, востребованных в индустрии. Оптимизация представления проектов для различных аудиторий (работодатели, клиенты, коллеги). Получение экспертной оценки портфолио и внесение улучшений. Подготовка сопроводительных материалов, усиливающих презентацию работ. Разработка стратегии регулярного обновления и расширения портфолио. Продолжительность: 4-6 недель."
                },
                {
                    "title": f"Развитие профессиональных связей и участие в сообществе",
                    "description": f"Активное включение в профессиональные сообщества специалистов в области {profession}. Участие в отраслевых мероприятиях, конференциях, воркшопах и хакатонах. Выстраивание сети профессиональных контактов с коллегами, экспертами и потенциальными работодателями. Обмен опытом и знаниями через участие в дискуссиях, форумах и онлайн-группах. Получение менторской поддержки от опытных специалистов. Отслеживание трендов и инноваций в индустрии через коммуникацию в сообществе. Продолжительность: непрерывный процесс, 6-8 недель для формирования базовой сети контактов."
                },
                {
                    "title": f"Планирование дальнейшего развития и непрерывное обучение",
                    "description": f"Разработка индивидуальной стратегии профессионального роста в сфере {profession} на ближайшие 3-5 лет. Определение приоритетных направлений для углубления экспертизы и расширения компетенций. Создание системы отслеживания новых технологий, методологий и инструментов в отрасли. Формирование привычки регулярного самообучения и рефлексии. Планирование получения дополнительных сертификаций и специализаций. Определение долгосрочных карьерных целей и промежуточных этапов их достижения. Разработка мер по предотвращению профессионального выгорания. Продолжительность: 4-6 недель для создания плана, затем постоянная реализация."
                }
            ]
        }
        
        # Возвращаем план обучения для определенной категории профессии или общий план
        if profession_category in learning_plans:
            return learning_plans[profession_category]
        else:
            return learning_plans["общая"]

    def _get_available_models(self):
        """
        Получает список доступных моделей с сервера LM Studio
            
        Returns:
            list: Список доступных моделей или пустой список в случае ошибки
        """
        try:
            # Формируем URL для запроса списка моделей
            url = f"http://{self.host}:{self.port}/v1/models"
            
            # Выполняем GET запрос к API
            response = requests.get(url, timeout=10)
            
            # Проверяем успешность запроса
            if response.status_code == 200:
                data = response.json()
                logger.info(f"LM Studio доступен и работает. Модели: {data}")
                
                # Если есть доступные модели, возвращаем их
                if 'data' in data and isinstance(data['data'], list):
                    return [model['id'] for model in data['data'] if 'id' in model]
                    
            # Если запрос не успешен или в ответе нет моделей
            logger.warning(f"Не удалось получить список моделей. Статус: {response.status_code}")
            return []
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка моделей: {e}")
            logger.error(traceback.format_exc())
            return []
