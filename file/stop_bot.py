#!/usr/bin/env python3
"""
Скрипт для остановки телеграм-бота
"""
import os
import sys
import signal
import subprocess
import logging
from datetime import datetime

# Настраиваем логирование
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'stop_bot.log')

logging.basicConfig(
    filename=log_file,
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def find_bot_processes():
    """Находит все процессы Python, связанные с ботом"""
    bot_processes = []
    
    # Сначала проверяем, есть ли файл с PID
    pid_file = os.path.join(log_dir, 'bot.pid')
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
                # Проверяем, существует ли процесс с таким PID
                try:
                    if os.name == 'nt':  # Windows
                        # Проверяем существование процесса в Windows
                        cmd = f'tasklist /FI "PID eq {pid}" /FO CSV'
                        output = subprocess.check_output(cmd, shell=True).decode('utf-8')
                        if str(pid) in output:
                            bot_processes.append(pid)
                    else:  # Linux/Unix
                        os.kill(pid, 0)  # Проверка существования процесса (сигнал 0 только проверяет)
                        bot_processes.append(pid)
                except (OSError, subprocess.CalledProcessError):
                    # Процесс не существует, удаляем файл PID
                    logging.warning(f"PID {pid} из файла не существует, удаляем файл")
                    try:
                        os.remove(pid_file)
                    except:
                        pass
        except Exception as e:
            logging.error(f"Ошибка при чтении файла PID: {str(e)}")
    
    # Если процесс не найден через файл PID, ищем через tasklist/ps
    if not bot_processes:
        try:
            # Команда для поиска процессов Python, запускающих main.py или tbot
            if os.name == 'nt':  # Windows
                # Ищем более широко - любые python процессы, связанные с tbot
                commands = [
                    'wmic process where "commandline like \'%main.py%\'" get processid',
                    'wmic process where "commandline like \'%tbot%\'" get processid'
                ]
                
                for command in commands:
                    try:
                        output = subprocess.check_output(command, shell=True).decode('utf-8')
                        for line in output.strip().split('\n')[1:]:  # Пропускаем заголовок
                            line = line.strip()
                            if line and line.isdigit():
                                pid = int(line)
                                if pid not in bot_processes:
                                    bot_processes.append(pid)
                    except:
                        continue
                
                # Если и это не сработало, ищем через tasklist
                if not bot_processes:
                    command = 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV'
                    output = subprocess.check_output(command, shell=True).decode('utf-8')
                    lines = output.strip().split('\n')[1:]  # Пропускаем заголовок
                    
                    for line in lines:
                        if ('python' in line.lower() and 
                            ('main.py' in line.lower() or 'tbot' in line.lower() or 'telegram' in line.lower())):
                            parts = line.strip('"').split('","')
                            if len(parts) >= 2:
                                pid = parts[1]
                                bot_processes.append(int(pid))
            else:  # Linux/Unix
                commands = [
                    "ps aux | grep 'python.*main.py' | grep -v grep",
                    "ps aux | grep 'python.*tbot' | grep -v grep",
                    "ps aux | grep 'python.*telegram' | grep -v grep"
                ]
                
                for command in commands:
                    try:
                        output = subprocess.check_output(command, shell=True).decode('utf-8')
                        lines = output.strip().split('\n')
                        
                        for line in lines:
                            parts = line.split()
                            if len(parts) > 1:
                                pid = int(parts[1])
                                if pid not in bot_processes:
                                    bot_processes.append(pid)
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Ошибка при выполнении команды {command}: {str(e)}")
                        continue
                    except Exception as e:
                        logging.error(f"Ошибка при обработке вывода команды {command}: {str(e)}")
                        continue
        except Exception as e:
            logging.error(f"Ошибка при поиске процессов: {str(e)}")
    
    return bot_processes

def stop_bot():
    """Останавливает все процессы телеграм-бота"""
    processes = find_bot_processes()
    
    if not processes:
        logging.info("Активные процессы бота не найдены")
        print("Процессы бота не найдены. Возможно, бот уже остановлен.")
        
        # Даже если процессы не найдены, удаляем pid файл если он существует
        pid_file = os.path.join(log_dir, 'bot.pid')
        if os.path.exists(pid_file):
            try:
                os.remove(pid_file)
                logging.info(f"Файл PID {pid_file} удален")
            except Exception as e:
                logging.error(f"Ошибка при удалении файла PID: {str(e)}")
        
        return False
    
    logging.info(f"Найдены процессы бота: {processes}")
    print(f"Найдены процессы бота: {processes}")
    
    success = True
    for pid in processes:
        try:
            # Сначала проверяем, действительно ли это процесс бота
            # (дополнительная проверка, чтобы избежать остановки системных процессов)
            process_info = ""
            try:
                if os.name == 'nt':  # Windows
                    cmd = f'wmic process where "processid={pid}" get commandline'
                    process_info = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
                else:  # Linux/Unix
                    cmd = f'ps -p {pid} -o command='
                    process_info = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
            except:
                pass
            
            # Проверяем, что это действительно процесс бота
            if process_info and ('python' in process_info.lower()) and \
               ('main.py' in process_info.lower() or 'tbot' in process_info.lower() or 'telegram' in process_info.lower()):
                # Останавливаем процесс
                if os.name == 'nt':  # Windows
                    try:
                        # Пробуем через taskkill сначала (более мягкий способ)
                        subprocess.run(['taskkill', '/PID', str(pid)], check=False)
                        logging.info(f"Процесс {pid} остановлен через taskkill")
                    except:
                        # Если не получилось, используем WinAPI
                        import ctypes
                        handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                        if handle:
                            result = ctypes.windll.kernel32.TerminateProcess(handle, 0)
                            ctypes.windll.kernel32.CloseHandle(handle)
                            if result:
                                logging.info(f"Процесс {pid} остановлен через WinAPI")
                            else:
                                raise Exception("Не удалось завершить процесс через WinAPI")
                else:  # Linux/Unix
                    os.kill(pid, signal.SIGTERM)
                
                logging.info(f"Процесс {pid} остановлен")
                print(f"Процесс {pid} остановлен")
            else:
                logging.warning(f"Процесс {pid} не похож на процесс бота. Пропускаем.")
                print(f"Процесс {pid} не похож на процесс бота. Пропускаем.")
                processes.remove(pid)  # Удаляем из списка процессов
                continue
        except Exception as e:
            logging.error(f"Ошибка при остановке процесса {pid}: {str(e)}")
            print(f"Ошибка при остановке процесса {pid}: {str(e)}")
            success = False
    
    # Проверяем, остались ли процессы
    remaining = find_bot_processes()
    if remaining:
        logging.warning(f"Остались процессы после попытки остановки: {remaining}")
        print(f"Некоторые процессы ({remaining}) не удалось остановить корректно.")
        
        # Пробуем остановить более жестко с SIGKILL
        if os.name != 'nt':  # Только для Linux/Unix
            for pid in remaining:
                try:
                    os.kill(pid, signal.SIGKILL)
                    logging.info(f"Процесс {pid} принудительно остановлен")
                    print(f"Процесс {pid} принудительно остановлен")
                except:
                    pass
    
    # Удаляем файл блокировки, если он существует
    lock_file = os.path.join(log_dir, 'bot.pid')
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            logging.info(f"Файл блокировки {lock_file} удален")
        except Exception as e:
            logging.error(f"Ошибка при удалении файла блокировки: {str(e)}")
    
    return success

def modify_run_bot():
    """Модифицирует скрипт run_bot.py для записи PID в файл"""
    run_bot_path = os.path.join(log_dir, 'run_bot.py')
    if not os.path.exists(run_bot_path):
        logging.error(f"Не найден файл {run_bot_path}")
        return False
    
    try:
        with open(run_bot_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, есть ли уже код для записи PID
        if 'bot.pid' in content and 'bot_process.pid' in content:
            logging.info("Файл run_bot.py уже содержит код для записи PID")
            return True
        
        # Находим место после строки с bot_process = subprocess.Popen
        if 'bot_process = subprocess.Popen' in content and 'logging.info(f\'Бот запущен с PID {bot_process.pid}\')' in content:
            # Добавляем код для записи PID в файл после логирования PID
            new_content = content.replace(
                'logging.info(f\'Бот запущен с PID {bot_process.pid}\')',
                'logging.info(f\'Бот запущен с PID {bot_process.pid}\')'+'\n        # Записываем PID в файл для упрощения остановки бота\n        with open(os.path.join(log_dir, \'bot.pid\'), \'w\') as pid_file:\n            pid_file.write(str(bot_process.pid))'
            )
            
            with open(run_bot_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logging.info("Файл run_bot.py успешно модифицирован для записи PID")
            return True
        else:
            logging.error("Не найдены необходимые строки в run_bot.py")
            return False
    except Exception as e:
        logging.error(f"Ошибка при модификации run_bot.py: {str(e)}")
        return False

if __name__ == "__main__":
    logging.info("Запуск скрипта остановки бота")
    
    # Пытаемся модифицировать run_bot.py для лучшей работы в будущем
    try:
        modify_run_bot()
    except Exception as e:
        logging.error(f"Не удалось модифицировать run_bot.py: {str(e)}")
    
    if stop_bot():
        logging.info("Бот успешно остановлен")
        print("Бот успешно остановлен!")
    else:
        logging.warning("Возникли проблемы при остановке бота")
        print("Возникли проблемы при остановке бота. Проверьте лог для деталей.")
