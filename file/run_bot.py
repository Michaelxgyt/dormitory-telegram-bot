#!/usr/bin/env python3
"""
Скрипт для автоматического запуска и поддержания работы телеграм-бота
Простая версия без дополнительных зависимостей
"""
import os
import sys
import subprocess
import logging
import threading
import time
from datetime import datetime

def limit_log_file(log_file_path, max_lines=1000):
    """
    Ограничивает размер лог-файла, оставляя только последние max_lines строк.
    Если файл не существует, создает его.
    """
    try:
        if os.path.exists(log_file_path):
            # Создаем временный файл для безопасной записи
            temp_file = f"{log_file_path}.tmp"
            
            # Читаем последние max_lines строк с использованием команды tail
            with open(temp_file, 'w', encoding='utf-8') as f_out:
                # Используем команду tail для эффективного чтения последних строк
                if sys.platform == 'win32':
                    # Для Windows используем PowerShell
                    cmd = f'powershell -Command "Get-Content -Path \"{log_file_path}\" -Tail {max_lines}"'
                    process = subprocess.Popen(cmd, stdout=f_out, shell=True, text=True, encoding='utf-8')
                    process.wait()
                else:
                    # Для Linux/MacOS
                    cmd = ['tail', '-n', str(max_lines), log_file_path]
                    subprocess.run(cmd, stdout=f_out, check=True)
            
            # Заменяем исходный файл временным
            if os.path.exists(temp_file):
                if os.path.getsize(temp_file) > 0:  # Если временный файл не пустой
                    os.replace(temp_file, log_file_path)
                else:
                    os.remove(temp_file)
    except Exception as e:
        logging.error(f'Ошибка при ограничении размера лог-файла {log_file_path}: {str(e)}')
        # Пытаемся удалить временный файл в случае ошибки
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

def cleanup_logs_periodically(log_dir, interval=3600):
    """
    Фоновая задача для периодической очистки лог-файлов.
    Запускается в отдельном потоке.
    """
    while True:
        try:
            # Очищаем оба лог-файла
            limit_log_file(os.path.join(log_dir, 'bot_error.log'))
            limit_log_file(os.path.join(log_dir, 'bot_output.log'))
        except Exception as e:
            logging.error(f'Ошибка при периодической очистке логов: {str(e)}')
        
        # Ждем указанный интервал перед следующей проверкой
        time.sleep(interval)

# Настраиваем логирование
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'bot.log')

logging.basicConfig(
    filename=log_file,
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def start_bot():
    """Запускает телеграм-бота"""
    logging.info('Начинаем запуск телеграм-бота...')
    
    # Путь к файлу main.py
    main_script = os.path.join(log_dir, 'main.py')
    
    try:
        # Запускаем бота напрямую
        logging.info(f'Запускаем Python: {sys.executable}')
        logging.info(f'Запускаем скрипт: {main_script}')
        
        # Определяем пути к лог-файлам
        error_log_path = os.path.join(log_dir, 'bot_error.log')
        output_log_path = os.path.join(log_dir, 'bot_output.log')
        
        # Ограничиваем размер лог-файлов перед запуском
        limit_log_file(error_log_path)
        limit_log_file(output_log_path)
        
        # Запускаем фоновую задачу для периодической очистки логов
        log_cleaner_thread = threading.Thread(
            target=cleanup_logs_periodically,
            args=(log_dir, 3600),  # Проверяем логи каждый час
            daemon=True  # Поток завершится при завершении основного процесса
        )
        log_cleaner_thread.start()
        
        # Открываем процесс бота
        bot_process = subprocess.Popen(
            [sys.executable, main_script],
            stdout=open(output_log_path, 'a', encoding='utf-8'),
            stderr=open(error_log_path, 'a', encoding='utf-8')
        )
        
        logging.info(f'Бот запущен с PID {bot_process.pid}')
        
        # Не дожидаемся завершения процесса, так как бот работает постоянно
        return True
        
    except Exception as e:
        logging.error(f'Ошибка при запуске бота: {str(e)}')
        return False

if __name__ == "__main__":
    # Просто запускаем бота
    start_bot()
