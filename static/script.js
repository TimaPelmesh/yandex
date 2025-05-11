document.addEventListener('DOMContentLoaded', function() {
    const professionInput = document.getElementById('profession');
    const regionInput = document.getElementById('region');
    const userInfoTextarea = document.getElementById('user-info');
    const medicalInfoTextarea = document.getElementById('medical-info');
    const generateButton = document.getElementById('generate-button');
    const loader = document.getElementById('loader');
    const roadmap = document.getElementById('roadmap');
    const professionTitle = document.getElementById('profession-title');
    const regionTitle = document.getElementById('region-title');
    const hardSkillsList = document.getElementById('hard-skills');
    const softSkillsList = document.getElementById('soft-skills');
    const learningPlan = document.getElementById('learning-plan');
    const futureInsightsList = document.getElementById('future-insights');
    const personalRecommendations = document.getElementById('personal-recommendations');

    generateButton.addEventListener('click', generateRoadmap);

    // Также добавляем обработку нажатия Enter в полях ввода
    professionInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            generateRoadmap();
        }
    });

    regionInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            generateRoadmap();
        }
    });

    // Добавляем обработчик для FAQ-ссылки
    const faqLink = document.querySelector('.nav-link[href="#faq-section"]');
    const faqSection = document.getElementById('faq-section');
    
    if (faqLink && faqSection) {
        // Удаляем обработчик mouseover, оставляем только click
        faqLink.addEventListener('click', function(e) {
            e.preventDefault();
            faqSection.scrollIntoView({ behavior: 'smooth' });
        });
    }

    // Функция для генерации дорожной карты
    async function generateRoadmap() {
        const profession = professionInput.value.trim();
        const region = regionInput.value.trim();
        const userInfo = userInfoTextarea.value.trim();
        const medicalInfo = medicalInfoTextarea.value.trim();

        if (!profession) {
            alert('Пожалуйста, укажите профессию или вакансию');
            professionInput.focus();
            return;
        }

        if (!region) {
            alert('Пожалуйста, укажите регион (город или страну)');
            regionInput.focus();
            return;
        }

        // Скрываем предыдущие результаты, если они были
        roadmap.classList.add('hidden');
        
        // Показываем индикатор загрузки
        loader.classList.remove('hidden');

        try {
            // Отправляем запрос на API для анализа профессии и региона
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    profession: profession,
                    region: region,
                    userInfo: userInfo,
                    medicalInfo: medicalInfo
                })
            });

            if (!response.ok) {
                throw new Error(`Ошибка API: ${response.status}`);
            }

            // Получаем данные от сервера
            const roadmapData = await response.json();
            
            // Теперь запрашиваем образовательные ресурсы для профессии и тем
            const topics = [];
            
            // Извлекаем темы из дорожной карты
            if (roadmapData.learningPlan && Array.isArray(roadmapData.learningPlan)) {
                roadmapData.learningPlan.forEach(step => {
                    if (typeof step === 'object' && step.title) {
                        topics.push(step.title);
                    }
                    if (typeof step === 'object' && step.description) {
                        // Разбиваем описание на предложения и используем их как темы
                        const sentences = step.description.split(/[.!?]+/).filter(s => s.trim().length > 10);
                        topics.push(...sentences.slice(0, 2)); // Берем максимум 2 предложения из описания
                    }
                });
            }
            
            // Добавляем хардскиллы как дополнительные темы
            if (roadmapData.hardSkills && Array.isArray(roadmapData.hardSkills)) {
                roadmapData.hardSkills.forEach(skill => {
                    if (typeof skill === 'string') {
                        topics.push(skill);
                    } else if (typeof skill === 'object' && skill !== null) {
                        topics.push(skill.name || skill.description || "");
                    }
                });
            }
            
            // Запрашиваем ресурсы для найденных тем
            try {
                const resourcesResponse = await fetch('/api/resources', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        profession: profession,
                        topics: topics.filter(t => t && t.length > 0).slice(0, 15) // Ограничиваем до 15 тем
                    })
                });
                
                if (resourcesResponse.ok) {
                    const resourcesData = await resourcesResponse.json();
                    roadmapData.educationalResources = resourcesData;
                }
            } catch (resourcesError) {
                console.error('Ошибка при получении образовательных ресурсов:', resourcesError);
                // Продолжаем без ресурсов
            }
            
            // Заполняем данные на странице
            populateRoadmap(roadmapData);
            
            // Показываем результаты
            roadmap.classList.remove('hidden');
            
            // Прокручиваем к результатам
            roadmap.scrollIntoView({ behavior: 'smooth' });
        } catch (error) {
            console.error('Ошибка при получении данных:', error);
            alert('Произошла ошибка при анализе данных. Пожалуйста, попробуйте позже.');
        } finally {
            // Скрываем индикатор загрузки
            loader.classList.add('hidden');
        }
    }

    function populateRoadmap(data) {
        try {
            // Проверяем, что data - объект и содержит необходимые поля
            if (!data || typeof data !== 'object') {
                console.error('Неверный формат данных:', data);
                alert('Получены некорректные данные от сервера. Пожалуйста, попробуйте позже.');
                return;
            }
            
            // Заполняем заголовок, используем дефолтные значения если данные отсутствуют
            professionTitle.textContent = data.profession || 'указанной профессии';
            regionTitle.textContent = data.region || 'указанном регионе';
            
            // Сохраняем профессию для использования при фильтрации ресурсов
            const currentProfession = data.profession ? data.profession.toLowerCase() : '';
            
            // Отображаем персональные рекомендации, если они есть
            if (data.personalRecommendations && Array.isArray(data.personalRecommendations) && data.personalRecommendations.length > 0) {
                personalRecommendations.innerHTML = '';
                data.personalRecommendations.forEach(recommendation => {
                    const recommendationElement = document.createElement('div');
                    recommendationElement.className = 'recommendation-item no-icon';
                    
                    // Удаляем кавычки в начале и конце текста рекомендации
                    let cleanedText = recommendation;
                    if (typeof cleanedText === 'string') {
                        // Удаляем кавычки в начале строки
                        cleanedText = cleanedText.replace(/^["'"«]/, '');
                        // Удаляем кавычки в конце строки
                        cleanedText = cleanedText.replace(/["'"»]$/, '');
                    }
                    
                    recommendationElement.textContent = cleanedText;
                    personalRecommendations.appendChild(recommendationElement);
                });
                
                // Показываем блок с персональными рекомендациями
                document.getElementById('personal-recommendations-section').style.display = 'block';
            } else {
                // Скрываем блок, если рекомендаций нет
                document.getElementById('personal-recommendations-section').style.display = 'none';
            }
            
            // Заполняем профессиональные навыки
            hardSkillsList.innerHTML = '';
            if (data.hardSkills && Array.isArray(data.hardSkills)) {
                data.hardSkills.forEach(skill => {
                    // Обрабатываем случай, когда skill это объект с полем name или строка
                    let skillText = '';
                    if (typeof skill === 'object' && skill !== null) {
                        skillText = skill.name || skill.description || JSON.stringify(skill);
                    } else {
                        skillText = String(skill);
                    }
                    
                    const li = document.createElement('li');
                    li.textContent = skillText;
                    hardSkillsList.appendChild(li);
                });
            } else {
                // Если hardSkills отсутствует или не является массивом, отображаем заглушку
                const li = document.createElement('li');
                li.textContent = 'Информация о навыках недоступна';
                hardSkillsList.appendChild(li);
                console.error('Ошибка в формате hardSkills:', data.hardSkills);
            }
            
            // Заполняем гибкие навыки
            softSkillsList.innerHTML = '';
            if (data.softSkills && Array.isArray(data.softSkills)) {
                data.softSkills.forEach(skill => {
                    // Обрабатываем случай, когда skill это объект с полем name или строка
                    let skillText = '';
                    if (typeof skill === 'object' && skill !== null) {
                        skillText = skill.name || skill.description || JSON.stringify(skill);
                    } else {
                        skillText = String(skill);
                    }
                    
                    const li = document.createElement('li');
                    li.textContent = skillText;
                    softSkillsList.appendChild(li);
                });
            } else {
                // Если softSkills отсутствует или не является массивом, отображаем заглушку
                const li = document.createElement('li');
                li.textContent = 'Информация о навыках недоступна';
                softSkillsList.appendChild(li);
                console.error('Ошибка в формате softSkills:', data.softSkills);
            }
            
            // Создаем список для отслеживания всех добавленных ресурсов (по URL)
            const usedResourceUrls = new Set();
            
            // Заполняем план обучения
            learningPlan.innerHTML = '';
            if (data.learningPlan && Array.isArray(data.learningPlan)) {
                data.learningPlan.forEach((step, index) => {
                    const stepElement = document.createElement('div');
                    stepElement.className = 'learning-step';
                    
                    // Проверяем, является ли элемент объектом с полями
                    if (typeof step === 'object') {
                        // Получаем title и description или создаем содержательное название на основе описания
                        let title = step.название || step.title || step.name || '';
                        const description = step.описание || step.description || '';
                        const duration = step.длительность || step.duration || '';
                        const keyResults = step.ключевые_результаты || step.key_results || [];
                        
                        // Если название содержит только "Шаг X", генерируем его на основе описания
                        if (!title || /^шаг\s+\d+$/i.test(title)) {
                            // Извлекаем осмысленное название из описания
                            if (description) {
                                // Берем первую фразу описания (до первой точки или до 50 символов)
                                const firstSentence = description.split('.')[0];
                                title = firstSentence.length > 50 
                                    ? firstSentence.substring(0, 47) + '...' 
                                    : firstSentence;
                                
                                // Если это начинается с "Изучение", используем это как название
                                if (title.toLowerCase().startsWith('изучение')) {
                                    title = title;
                                }
                                // Если это слишком короткое, добавляем "Этап X: "
                                else if (title.length < 10) {
                                    title = `Этап ${index + 1}: ${title}`;
                                }
                            } else {
                                // Если нет описания, используем осмысленное название для шага
                                title = `Этап ${index + 1} профессионального развития`;
                            }
                        }
                        
                        // Создаем HTML для шага
                        let stepHtml = `
                            <strong class="step-title">${title}</strong>
                            <p>${description}</p>
                        `;
                        
                        if (duration) {
                            stepHtml += `<p><strong>Рекомендуемая продолжительность:</strong> ${duration}</p>`;
                        }
                        
                        if (Array.isArray(keyResults) && keyResults.length > 0) {
                            stepHtml += '<div><strong>Ключевые результаты:</strong><ul>';
                            keyResults.forEach(result => {
                                stepHtml += `<li>${result}</li>`;
                            });
                            stepHtml += '</ul></div>';
                        }
                        
                        // Функция для проверки релевантности ресурса к профессии
                        function isResourceRelevantToProfession(resource, profession) {
                            if (!profession) return true; // Если профессия не указана, считаем все ресурсы релевантными
                            
                            const professionLower = profession.toLowerCase();
                            const professionWords = professionLower.split(/\s+/);
                            const professionPatterns = [
                                // Общие образовательные платформы всегда релевантны
                                /coursera|udemy|stepik|edx|youtube|хабр|habr|github|stackoverflow/i,
                                // Если название ресурса или описание содержит слова из профессии
                                new RegExp(professionWords.filter(w => w.length > 3).join('|'), 'i')
                            ];
                            
                            // Проверяем нерелевантные технологии для разных профессий
                            const irrelevantTechPatterns = {
                                'дизайнер': /docker|kubernetes|git|devops|ci\/cd|backend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'блогер': /docker|kubernetes|git|devops|ci\/cd|backend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'маркетолог': /docker|kubernetes|devops|backend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'контент': /docker|kubernetes|devops|backend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'видео': /docker|kubernetes|git|devops|backend|java|php|c\+\+|c#|\.net/i,
                                'фотограф': /docker|kubernetes|git|devops|backend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'smm': /docker|kubernetes|git|devops|backend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'бьюти': /docker|kubernetes|git|devops|ci\/cd|backend|frontend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'стилист': /docker|kubernetes|git|devops|ci\/cd|backend|frontend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'бровист': /docker|kubernetes|git|devops|ci\/cd|backend|frontend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'визажист': /docker|kubernetes|git|devops|ci\/cd|backend|frontend|java|python|ruby|php|c\+\+|c#|\.net/i,
                                'макияж': /docker|kubernetes|git|devops|ci\/cd|backend|frontend|java|python|ruby|php|c\+\+|c#|\.net/i
                            };
                            
                            // Проверяем релевантные технологии для разных профессий
                            const relevantTechPatterns = {
                                'разработчик': /javascript|python|java|ruby|php|c\+\+|c#|\.net|frontend|backend|fullstack|бэкенд|фронтенд|фулстек|база данных|database|sql|nosql|ui\/ux|html|css|react|angular|vue|node|framework|фреймворк|git|api/i,
                                'программист': /javascript|python|java|ruby|php|c\+\+|c#|\.net|frontend|backend|fullstack|бэкенд|фронтенд|фулстек|база данных|database|sql|nosql|ui\/ux|html|css|react|angular|vue|node|framework|фреймворк|git|api/i,
                                'инженер': /javascript|python|java|ruby|php|c\+\+|c#|\.net|frontend|backend|fullstack|бэкенд|фронтенд|фулстек|база данных|database|sql|nosql|ui\/ux|html|css|react|angular|vue|node|framework|фреймворк|git|api|devops|docker|kubernetes|ci\/cd/i,
                                'дизайнер': /figma|sketch|adobe|photoshop|illustrator|xd|ui|ux|typography|типографика|композиция|цвет|color|wireframe|прототип|prototype|дизайн|design|интерфейс|interface|пользователь|user|опыт|experience/i,
                                'маркетолог': /маркетинг|marketing|seo|sem|smm|контент|content|email|социальн|social|media|таргет|target|аналитика|analytics|кампания|campaign|конверсия|conversion|воронка|funnel|лид|lead/i
                            };
                            
                            // Проверяем ресурс на релевантность
                            if (resource.title) {
                                const titleLower = resource.title.toLowerCase();
                                const descriptionLower = resource.description ? resource.description.toLowerCase() : '';
                                
                                // Проверяем на общие образовательные платформы
                                if (professionPatterns[0].test(titleLower)) {
                                    return true;
                                }
                                
                                // Проверяем на нерелевантные технологии
                                for (const prof in irrelevantTechPatterns) {
                                    if (professionLower.includes(prof) && 
                                        (irrelevantTechPatterns[prof].test(titleLower) || 
                                         irrelevantTechPatterns[prof].test(descriptionLower))) {
                                        return false;
                                    }
                                }
                                
                                // Проверяем на релевантные технологии
                                for (const prof in relevantTechPatterns) {
                                    if (professionLower.includes(prof) && 
                                        (relevantTechPatterns[prof].test(titleLower) || 
                                         relevantTechPatterns[prof].test(descriptionLower))) {
                                        return true;
                                    }
                                }
                                
                                // Проверяем, содержит ли ресурс слова из профессии
                                if (professionPatterns[1].test(titleLower) || 
                                    professionPatterns[1].test(descriptionLower)) {
                                    return true;
                                }
                            }
                            
                            // По умолчанию ресурс релевантен, если не удалось определить иначе
                            return true;
                        }
                        
                        // Ищем образовательные ресурсы для этого шага
                        if (data.educationalResources && typeof data.educationalResources === 'object') {
                            const stepResources = [];
                            
                            // Проверяем наличие ресурсов для названия шага
                            if (data.educationalResources[title]) {
                                // Фильтруем по релевантности к профессии
                                data.educationalResources[title].forEach(resource => {
                                    if (isResourceRelevantToProfession(resource, currentProfession)) {
                                        stepResources.push(resource);
                                    }
                                });
                            }
                            
                            // Проверяем, есть ли ресурсы по общей категории
                            if (data.educationalResources["Общие ресурсы по профессии"]) {
                                if (index === 0) { // Показываем общие ресурсы только на первом шаге
                                    // Фильтруем по релевантности к профессии
                                    data.educationalResources["Общие ресурсы по профессии"].forEach(resource => {
                                        if (isResourceRelevantToProfession(resource, currentProfession)) {
                                            stepResources.push(resource);
                                        }
                                    });
                                }
                            }
                            
                            // Если для этого шага есть ресурсы, добавляем их
                            if (stepResources.length > 0) {
                                stepHtml += '<div class="resource-section">';
                                stepHtml += '<h4>Полезные ресурсы для обучения</h4>';
                                stepHtml += '<div class="resource-list">';
                                
                                // Удаляем дубликаты ресурсов по URL
                                const uniqueResources = [];
                                stepResources.forEach(resource => {
                                    if (resource.url && !usedResourceUrls.has(resource.url)) {
                                        usedResourceUrls.add(resource.url);
                                        uniqueResources.push(resource);
                                    }
                                });
                                
                                // Ограничиваем максимум 3 ресурса на шаг
                                uniqueResources.slice(0, 3).forEach(resource => {
                                    stepHtml += `
                                        <div class="resource-item">
                                            <span class="resource-title">
                                                <a href="${resource.url}" target="_blank" rel="noopener noreferrer">
                                                    ${resource.title}
                                                </a>
                                                ${resource.free ? '<span class="resource-badge free">Бесплатно</span>' : ''}
                                            </span>
                                            <span class="resource-description">${resource.description || ''}</span>
                                        </div>
                                    `;
                                });
                                
                                stepHtml += '</div></div>';
                            }
                        }
                        
                        stepElement.innerHTML = stepHtml;
                    } else if (typeof step === 'string') {
                        // Если шаг - это просто строка, отображаем её
                        stepElement.innerHTML = `<p>${step}</p>`;
                    }
                    
                    learningPlan.appendChild(stepElement);
                });
            } else {
                // Если learningPlan отсутствует или не является массивом, отображаем заглушку
                learningPlan.innerHTML = '<p>Информация о плане обучения недоступна</p>';
                console.error('Ошибка в формате learningPlan:', data.learningPlan);
            }
            
            // Собираем все неиспользованные ресурсы в "Дополнительные образовательные ресурсы"
            if (data.educationalResources) {
                // Создаем плоский массив всех ресурсов, которые не были показаны в шагах
                const remainingResources = [];
                
                // Проходим по всем категориям ресурсов
                Object.keys(data.educationalResources).forEach(category => {
                    const resources = data.educationalResources[category];
                    if (Array.isArray(resources)) {
                        resources.forEach(resource => {
                            if (resource.url && !usedResourceUrls.has(resource.url) && 
                                isResourceRelevantToProfession(resource, currentProfession)) {
                                remainingResources.push({
                                    category: category,
                                    resource: resource
                                });
                                // Добавляем URL в использованные, чтобы избежать повторного отображения
                                usedResourceUrls.add(resource.url);
                            }
                        });
                    }
                });
                
                // Если остались неиспользованные ресурсы, создаем блок "Дополнительные образовательные ресурсы"
                if (remainingResources.length > 0) {
                    const resourcesSection = document.createElement('div');
                    resourcesSection.className = 'roadmap-section';
                    
                    let resourcesHtml = '<h4>Дополнительные образовательные ресурсы</h4>';
                    resourcesHtml += '<div class="resource-list">';
                    
                    // Группируем ресурсы по категориям для более логичного отображения
                    const resourcesByCategory = {};
                    remainingResources.forEach(item => {
                        if (!resourcesByCategory[item.category]) {
                            resourcesByCategory[item.category] = [];
                        }
                        resourcesByCategory[item.category].push(item.resource);
                    });
                    
                    // Отображаем ресурсы по категориям
                    Object.keys(resourcesByCategory).forEach(category => {
                        resourcesHtml += `<div class="resource-category"><h5>${category}</h5>`;
                        
                        resourcesByCategory[category].forEach(resource => {
                            resourcesHtml += `
                                <div class="resource-item">
                                    <span class="resource-title">
                                        <a href="${resource.url}" target="_blank" rel="noopener noreferrer">
                                            ${resource.title}
                                        </a>
                                        ${resource.free ? '<span class="resource-badge free">Бесплатно</span>' : ''}
                                    </span>
                                    <span class="resource-description">${resource.description || ''}</span>
                                </div>
                            `;
                        });
                        
                        resourcesHtml += '</div>';
                    });
                    
                    resourcesHtml += '</div>';
                    
                    resourcesSection.innerHTML = resourcesHtml;
                    roadmap.appendChild(resourcesSection);
                }
            }
            
            // Заполняем информацию о тенденциях будущего
            futureInsightsList.innerHTML = '';
            if (data.futureInsights) {
                // Если futureInsights - строка, преобразуем ее в массив
                const insightsArray = typeof data.futureInsights === 'string' 
                    ? [data.futureInsights] 
                    : Array.isArray(data.futureInsights) 
                        ? data.futureInsights 
                        : ['Информация о тенденциях недоступна'];
                
                insightsArray.forEach(insight => {
                    if (insight && typeof insight === 'string') {
                        const li = document.createElement('li');
                        li.textContent = insight;
                        futureInsightsList.appendChild(li);
                    }
                });
                
                // Если futureInsights пуст, добавляем заглушку
                if (futureInsightsList.children.length === 0) {
                    const li = document.createElement('li');
                    li.textContent = 'Информация о тенденциях недоступна';
                    futureInsightsList.appendChild(li);
                }
            } else {
                const li = document.createElement('li');
                li.textContent = 'Информация о тенденциях недоступна';
                futureInsightsList.appendChild(li);
                console.error('Ошибка в формате futureInsights:', data.futureInsights);
            }
        } catch (error) {
            console.error('Ошибка при заполнении дорожной карты:', error);
            alert('Произошла ошибка при отображении данных. Пожалуйста, попробуйте еще раз.');
        }
    }

    // Добавляем эффект мигания для кнопки
    const addButtonHighlight = () => {
        generateButton.classList.add('highlight');
        setTimeout(() => {
            generateButton.classList.remove('highlight');
        }, 1000);
    };

    // Запускаем эффект подсветки кнопки при загрузке страницы
    setTimeout(addButtonHighlight, 1000);
}); 