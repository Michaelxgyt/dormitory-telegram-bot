import asyncio
import os
import sys
import threading
import logging
from logging.handlers import RotatingFileHandler

# Настраиваем логирование
log_file = os.path.join(os.path.dirname(__file__), 'bot_error.log')
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=2)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   level=logging.INFO,
                   handlers=[handler])
logger = logging.getLogger('wsgi')

# Добавляем текущий каталог в путь для импорта
sys.path.insert(0, os.path.dirname(__file__))

# Переменная для хранения информации о состоянии бота
bot_process = None

def start_bot():
    try:
        logger.info('Запуск бота...')
        from main import main
        asyncio.run(main())
    except Exception as e:
        logger.error(f'Ошибка при запуске бота: {e}', exc_info=True)

# Функция для запуска бота через WSGI
def application(environ, start_response):
    global bot_process
    
    # Проверяем, запущен ли уже бот
    if bot_process is None or not bot_process.is_alive():
        try:
            logger.info('Создание нового потока для бота')
            bot_process = threading.Thread(target=start_bot)
            bot_process.daemon = True
            bot_process.start()
            status = '200 OK'
            message = b'Telegram bot is starting...'
        except Exception as e:
            logger.error(f'Ошибка запуска потока: {e}', exc_info=True)
            status = '500 Internal Server Error'
            message = f'Error starting bot: {str(e)}'.encode()
    else:
        status = '200 OK'
        message = b'Telegram bot is already running'
    
    # Отправляем ответ
    start_response(status, [('Content-Type', 'text/plain')])
    return [message]

# Для локального запуска
if __name__ == '__main__':
    logger.info('Локальный запуск бота')
    from main import main
    asyncio.run(main())
