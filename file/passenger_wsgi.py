#!/usr/bin/env python3
import os
import sys
import threading
import time
import subprocess
import logging
from logging.handlers import RotatingFileHandler

# Настраиваем логирование
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'passenger_error.log')

handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=2)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[handler]
)
logger = logging.getLogger('passenger')

# Добавляем текущий каталог в путь поиска модулей
sys.path.insert(0, os.path.dirname(__file__))

# Переменная для отслеживания статуса бота
bot_thread = None
bot_started = False

def start_bot_thread():
    """Запускает бота в отдельном процессе"""
    global bot_started
    
    try:
        logger.info('Запуск телеграм-бота...')
        
        # Путь к Python интерпретатору и к скрипту бота
        python_path = sys.executable
        script_path = os.path.join(os.path.dirname(__file__), 'main.py')
        
        # Запускаем бота в отдельном процессе
        subprocess.Popen([python_path, script_path], 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
        
        bot_started = True
        logger.info('Бот успешно запущен')
    except Exception as e:
        logger.error(f'Ошибка при запуске бота: {str(e)}', exc_info=True)
        bot_started = False

# Функция для проверки и перезапуска бота при необходимости
def ensure_bot_running():
    global bot_thread, bot_started
    
    if not bot_started or (bot_thread is not None and not bot_thread.is_alive()):
        bot_thread = threading.Thread(target=start_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()

# Запуск бота при первом импорте модуля
ensure_bot_running()

# Стандартная функция для Passenger
def application(environ, start_response):
    # Убедимся, что бот запущен
    ensure_bot_running()
    
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Telegram bot is running']
