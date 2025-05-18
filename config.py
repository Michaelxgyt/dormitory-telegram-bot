import os

# Настройки бота
TOKEN = 'YOUR_TELEGRAM_TOKEN_HERE'  # Замените на ваш токен от BotFather

# Пароли для входа
ADMIN_PASSWORD = 'your_admin_password'  # Замените на надежный пароль
MANAGER_PASSWORD = 'your_manager_password'  # Замените на надежный пароль

# База данных
DB_NAME = 'dormitory.db'

# Временная зона
TIMEZONE = 'Europe/Moscow'

# Настройки уведомлений по умолчанию
DEFAULT_NOTIFICATION_SETTINGS = {
    'preview_time': '12:00',
    'duty_time': '22:00',
    'preview_text': "Напоминание: завтра ваше дежурство!",
    'duty_text': "Напоминание: пора дежурить!"
}
