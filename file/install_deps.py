#!/usr/bin/env python3
"""
Скрипт для установки зависимостей бота
"""
import os
import sys
import subprocess
import logging
from datetime import datetime

# Настраиваем логирование
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'install_deps.log')

logging.basicConfig(
    filename=log_file,
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def install_dependencies():
    """Установка зависимостей из файла requirements.txt"""
    try:
        # Путь к файлу requirements.txt
        req_file = os.path.join(log_dir, 'requirements.txt')
        
        # Проверяем существование файла
        if not os.path.exists(req_file):
            logging.error(f"Файл {req_file} не найден!")
            return False
        
        # Получаем путь к pip, связанному с текущим Python
        python_path = sys.executable
        pip_command = [python_path, "-m", "pip", "install", "-r", req_file]
        
        logging.info(f"Устанавливаем зависимости из {req_file}")
        logging.info(f"Используем Python: {python_path}")
        logging.info(f"Команда установки: {' '.join(pip_command)}")
        
        # Запускаем установку
        process = subprocess.Popen(
            pip_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Получаем вывод и ошибки
        stdout, stderr = process.communicate()
        
        # Записываем результаты в лог
        logging.info("Результат установки:")
        for line in stdout.splitlines():
            logging.info(f"  {line}")
        
        if stderr:
            logging.warning("Ошибки при установке:")
            for line in stderr.splitlines():
                logging.warning(f"  {line}")
        
        # Проверяем успешность установки
        if process.returncode == 0:
            logging.info("Установка зависимостей успешно завершена")
            return True
        else:
            logging.error(f"Ошибка при установке зависимостей, код: {process.returncode}")
            return False
            
    except Exception as e:
        logging.error(f"Произошла ошибка: {str(e)}")
        return False

if __name__ == "__main__":
    logging.info("Начало установки зависимостей")
    success = install_dependencies()
    
    if success:
        logging.info("Зависимости успешно установлены")
        print("Зависимости успешно установлены!")
    else:
        logging.error("Не удалось установить зависимости")
        print("Не удалось установить зависимости. Проверьте файл install_deps.log для деталей.")
