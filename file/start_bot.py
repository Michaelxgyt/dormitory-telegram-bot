#!/usr/bin/env python3
"""
Скрипт для прямого запуска бота без WSGI
"""
import logging
import os

# Настройка логирования
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'bot_error.log')

logging.basicConfig(
    filename=log_file,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('start_bot')

try:
    logger.info('Запуск бота напрямую через start_bot.py')
    
    # Импортируем функцию main из основного файла
    from main import main
    
    # Прямой запуск бота
    if __name__ == "__main__":
        import asyncio
        asyncio.run(main())
        
except Exception as e:
    logger.error(f'Ошибка при запуске бота: {str(e)}', exc_info=True)
    print(f'Ошибка при запуске бота: {str(e)}')
