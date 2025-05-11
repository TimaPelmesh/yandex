from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import pickle
import pandas as pd
import numpy as np
from model import JobRoadmapGenerator

# Инициализация Flask приложения
app = Flask(__name__, static_folder='static')
# Включаем CORS для всех маршрутов
CORS(app)

# Загрузка или создание модели
model_path = os.path.join(os.path.dirname(__file__), 'model', 'roadmap_model.pkl')
roadmap_model = JobRoadmapGenerator(model_path)

# Маршрут для главной страницы
@app.route('/')
def index():
    return render_template('index.html')

# Маршрут для страницы FAQ
@app.route('/faq')
def faq():
    return render_template('faq.html')

# Маршрут для статических файлов
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# API для анализа вакансии и региона
@app.route('/api/analyze', methods=['POST'])
def analyze():
    # Получаем данные из запроса
    data = request.json
    profession = data.get('profession', '')
    region = data.get('region', '')
    user_info = data.get('userInfo', '')
    medical_info = data.get('medicalInfo', '')
    
    # Объединяем пользовательскую информацию и медицинские особенности
    combined_user_info = user_info
    if medical_info:
        if combined_user_info:
            combined_user_info += f"\n\nМедицинские особенности: {medical_info}"
        else:
            combined_user_info = f"Медицинские особенности: {medical_info}"
    
    # Проверяем наличие данных
    if not profession or not region:
        return jsonify({'error': 'Необходимо указать профессию и регион'}), 400
    
    try:
        # Получаем дорожную карту с помощью модели
        result = roadmap_model.generate_roadmap(
            profession, 
            region=region,
            user_info=combined_user_info
        )
        return jsonify(result)
    except Exception as e:
        print(f"Ошибка при генерации дорожной карты: {e}")
        return jsonify({'error': 'Произошла ошибка при анализе данных. Пожалуйста, попробуйте позже.'}), 500

# API для получения образовательных ресурсов
@app.route('/api/resources', methods=['POST'])
def get_resources():
    data = request.json
    profession = data.get('profession', '')
    topics = data.get('topics', [])
    
    # Проверяем наличие данных
    if not profession:
        return jsonify({'error': 'Необходимо указать профессию'}), 400
    
    if not topics or not isinstance(topics, list):
        return jsonify({'error': 'Необходимо указать список тем для поиска ресурсов'}), 400
    
    try:
        # Используем модель для получения образовательных ресурсов
        resources = roadmap_model.find_education_resources(profession, topics)
        return jsonify(resources)
    except Exception as e:
        print(f"Ошибка при поиске образовательных ресурсов: {e}")
        return jsonify({'error': 'Произошла ошибка при поиске ресурсов. Пожалуйста, попробуйте позже.'}), 500

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True, port=8080) 