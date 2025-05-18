import asyncio
import pytz
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import TIMEZONE, DEFAULT_NOTIFICATION_SETTINGS # Импортируем дефолтные настройки
from database import (
    # get_notification_settings, # Больше не используем напрямую для загрузки
    get_block_notification_settings, # Новая функция
    save_notification,
    get_users_by_room,
    get_todays_duties,
    get_tomorrows_duties,
    get_user_role,
    get_duty_details, # Добавлено для send_duty_change_notification
    get_room_details  # Добавлено для send_duty_change_notification
)

# Загружаем настройки уведомлений для конкретного блока, с фолбэком на дефолтные
def load_effective_notification_settings(block_id: int = None):
    if block_id:
        block_settings = get_block_notification_settings(block_id)
        # Создаем результирующий словарь, начиная с дефолтных значений
        effective_settings = DEFAULT_NOTIFICATION_SETTINGS.copy()
        # Обновляем его значениями из настроек блока, если они есть
        for key, value in block_settings.items():
            if value is not None: # Убедимся, что значение не пустое
                 effective_settings[key] = value
        return effective_settings
    return DEFAULT_NOTIFICATION_SETTINGS.copy() # Если block_id не предоставлен, возвращаем дефолтные


# Создаем компактную клавиатуру навигации
def get_compact_navigation(user_id):
    """Создает компактную клавиатуру для навигации после уведомлений"""
    user_role = get_user_role(user_id) or 'student'
    keyboard = []

    # Первый ряд - общие функции
    row1 = []
    row1.append(InlineKeyboardButton("🏠 Главная", callback_data="back_to_main"))
    # Кнопка "Мои дежурства" имеет смысл только если у пользователя есть комната
    # Для простоты пока оставим, но можно добавить проверку get_user_room_id(user_id)
    row1.append(InlineKeyboardButton("📅 Мои дежурства", callback_data="my_duties"))
    keyboard.append(row1)

    # Второй ряд - функции в зависимости от роли
    row2 = []
    if user_role == 'student':
        row2.append(InlineKeyboardButton("🛏️ Моя комната", callback_data="select_room"))
    elif user_role == 'elder':
        row2.append(InlineKeyboardButton("🛡️ Панель старосты", callback_data="elder_panel"))
    elif user_role == 'manager':
        row2.append(InlineKeyboardButton("🏫 Управление", callback_data="manager_panel"))
    elif user_role == 'admin':
        row2.append(InlineKeyboardButton("⚙️ Администрирование", callback_data="admin_panel"))

    if row2:
        keyboard.append(row2)

    return InlineKeyboardMarkup(keyboard)

# Функция для проверки и отправки уведомлений
async def check_and_send_notifications(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(pytz.timezone(TIMEZONE))
    current_time_str = now.strftime('%H:%M') # Текущее время как строка для сравнения
    today_date_str = now.strftime('%Y-%m-%d')
    tomorrow_date_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')

    # print(f"Проверка уведомлений: текущее время {current_time_str}") # Можно раскомментировать для отладки

    # Уведомления за день до дежурства (предварительные)
    tomorrow_duties = get_tomorrows_duties() # Эта функция теперь возвращает block_id
    # duties: (duty_id, room_id, room_number, block_number_str, floor_number, dorm_name, completed, block_id_int)

    for duty_id, room_id, room_number, _, _, _, _, duty_block_id in tomorrow_duties: # _ игнорируют ненужные поля
        settings = load_effective_notification_settings(duty_block_id) # Загружаем настройки для блока дежурства

        # Проверяем время предварительного уведомления для этого блока
        if current_time_str == settings['preview_time']:
            # print(f"Отправка предварительного уведомления для блока {duty_block_id} (комната {room_number}) на завтра ({tomorrow_date_str})") # Отладка
            users = get_users_by_room(room_id)
            if not users: # Добавим проверку на случай если в комнате нет юзеров
                # print(f"В комнате {room_number} (ID: {room_id}) нет пользователей для уведомления.")
                continue
            for user_id, username in users:
                message_text = settings['preview_text']
                custom_message = (f"🔔 {message_text}\n\n"
                                  f"📅 Дата: завтра ({tomorrow_date_str})\n"
                                  f"🛏️ Комната: {room_number}")
                try:
                    navigation_keyboard = get_compact_navigation(user_id)
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=custom_message,
                        reply_markup=navigation_keyboard
                    )
                    save_notification(user_id, 'preview', custom_message)
                except Exception as e:
                    print(f"Ошибка отправки уведомления пользователю {user_id} ({username}): {e}")

    # Уведомления в день дежурства
    today_duties = get_todays_duties() # Эта функция теперь возвращает block_id
    for duty_id, room_id, room_number, _, _, _, _, duty_block_id in today_duties:
        settings = load_effective_notification_settings(duty_block_id) # Загружаем настройки для блока дежурства

        # Проверяем время дежурного уведомления для этого блока
        if current_time_str == settings['duty_time']:
            # print(f"Отправка дежурного уведомления для блока {duty_block_id} (комната {room_number}) на сегодня ({today_date_str})") # Отладка
            users = get_users_by_room(room_id)
            if not users:
                # print(f"В комнате {room_number} (ID: {room_id}) нет пользователей для уведомления.")
                continue
            for user_id, username in users:
                message_text = settings['duty_text']
                custom_message = (f"⏰ {message_text}\n\n"
                                  f"📅 Дата: сегодня ({today_date_str})\n"
                                  f"🛏️ Комната: {room_number}")
                try:
                    navigation_keyboard = get_compact_navigation(user_id)
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=custom_message,
                        reply_markup=navigation_keyboard
                    )
                    save_notification(user_id, 'duty', custom_message)
                except Exception as e:
                    print(f"Ошибка отправки уведомления пользователю {user_id} ({username}): {e}")


# Функция для отправки уведомлений о смене дня дежурства
async def send_duty_change_notification(bot, duty_id, old_room_id, new_room_id):
    """
    Отправляет уведомление жителям комнаты о смене дня дежурства
    :param bot: Экземпляр Telegram бота
    :param duty_id: ID дежурства
    :param old_room_id: ID старой комнаты (может быть None, если дежурство только что создано)
    :param new_room_id: ID новой комнаты
    """
    # Получаем детали дежурства (дату)
    duty_details_info = get_duty_details(duty_id) # Переименовал
    if not duty_details_info:
        print(f"Не удалось получить информацию о дежурстве {duty_id}")
        return

    duty_date = duty_details_info[0]  # Предполагаем, что первый элемент - это дата

    # Получаем данные о старой комнате
    old_room_number = "Неизвестная комната"
    if old_room_id:
        old_room_details = get_room_details(old_room_id)
        if old_room_details:
            old_room_number = old_room_details[0]


    # Получаем данные о новой комнате
    new_room_details = get_room_details(new_room_id)
    if not new_room_details:
        print(f"Не удалось получить информацию о комнате {new_room_id}")
        return

    new_room_number = new_room_details[0]

    # Отправляем уведомления жителям старой комнаты (если она была)
    if old_room_id and old_room_id != new_room_id: # Добавил проверку, что комната изменилась
        old_room_users = get_users_by_room(old_room_id)
        for user_id, username in old_room_users:
            message = (f"🔄 Изменение дежурства!\n\n"
                       f"Дежурство на {duty_date} было перенесено с вашей комнаты (№{old_room_number}) "
                       f"на комнату №{new_room_number}.\n\n"
                       f"Ваша комната больше не дежурит в этот день!")

            try:
                navigation_keyboard = get_compact_navigation(user_id)
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=navigation_keyboard
                )
                save_notification(user_id, 'duty_change_removed', message) # Изменил тип
            except Exception as e:
                print(f"Ошибка отправки уведомления (старая комната) пользователю {user_id} ({username}): {e}")

    # Отправляем уведомления жителям новой комнаты
    if new_room_id: # Проверка на случай, если новая комната = None (хотя это не должно быть)
        new_room_users = get_users_by_room(new_room_id)
        for user_id, username in new_room_users:
            if old_room_id == new_room_id: # Если комната та же, текст немного другой
                 message = (f"ℹ️ Обновление дежурства!\n\n"
                           f"Дежурство для вашей комнаты (№{new_room_number}) на {duty_date} было обновлено.\n"
                           f"Проверьте свои дежурства для актуальной информации.")
            else:
                message = (f"⚠️ Новое дежурство!\n\n"
                           f"Вашей комнате (№{new_room_number}) назначено дежурство на {duty_date}.")

            try:
                navigation_keyboard = get_compact_navigation(user_id)
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=navigation_keyboard
                )
                save_notification(user_id, 'duty_change_assigned', message) # Изменил тип
            except Exception as e:
                print(f"Ошибка отправки уведомления (новая комната) пользователю {user_id} ({username}): {e}")

# Установка планировщика задач
def setup_notification_scheduler(application):
    # Запускаем проверку уведомлений каждую минуту
    application.job_queue.run_repeating(check_and_send_notifications, interval=60, first=5) # first=5 чтобы дать боту время запуститься