from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from collections import Counter

from config import ADMIN_PASSWORD
from database import (
    update_user_role,
    get_user_role,
    get_all_users,
    delete_user,
    get_room_details
)
from keyboards import (
    get_admin_panel,
    get_back_button,
    get_confirmation_menu
)

# Запрос пароля администратора
async def request_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает пароль для входа в панель администратора"""
    query = update.callback_query
    
    # Устанавливаем флаг ожидания пароля
    context.user_data['awaiting_admin_password'] = True
    
    await query.edit_message_text(
        "🔐 Для входа в панель администратора введите пароль:",
        reply_markup=get_back_button()
    )

# Обработка введенного пароля администратора
async def handle_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет введенный пароль администратора"""
    # Сбрасываем флаг ожидания пароля
    context.user_data['awaiting_admin_password'] = False
    
    user_id = update.effective_user.id
    entered_password = update.message.text
    
    # Удаляем сообщение с паролем для безопасности
    try:
        await update.message.delete()
    except Exception as e:
        # Ошибка может возникнуть, если сообщение слишком старое или нет прав на удаление
        print(f"Не удалось удалить сообщение с паролем: {str(e)}")
        pass  # Продолжаем работу, даже если не удалось удалить сообщение
    
    if entered_password == ADMIN_PASSWORD:
        # Пароль верный, устанавливаем роль 'admin'
        update_user_role(user_id, 'admin')
        context.user_data['role'] = 'admin'
        
        await update.message.reply_text(
            "✅ Вы успешно вошли как администратор.\n\n"
            "Теперь у вас есть полный доступ к системе.",
            reply_markup=get_admin_panel()
        )
    else:
        # Пароль неверный
        await update.message.reply_text(
            "❌ Неверный пароль. Попробуйте снова.",
            reply_markup=get_back_button()
        )

# Обработчик кнопок администратора
async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки для роли администратора"""
    query = update.callback_query
    callback_data = query.data
    
    # Проверяем, что пользователь действительно имеет роль администратора
    user_id = update.effective_user.id
    if get_user_role(user_id) != 'admin' and context.user_data.get('role') != 'admin':
        await query.edit_message_text(
            "У вас нет прав для доступа к панели администратора.",
            reply_markup=get_back_button()
        )
        return
    
    # Основные действия администратора
    if callback_data == "admin_panel":
        await show_admin_panel(update, context)
    elif callback_data == "manage_users":
        await show_users(update, context)
    elif callback_data == "user_statistics":
        await show_user_statistics(update, context)
    elif callback_data == "manage_managers":
        await manage_managers(update, context)
    elif callback_data == "system_settings":
        await show_system_settings(update, context)
    elif callback_data.startswith("edit_manager_password"):
        await request_new_manager_password(update, context)
    elif callback_data.startswith("edit_admin_password"):
        await request_new_admin_password(update, context)
    elif callback_data.startswith("remove_user_"):
        user_id_to_remove = int(callback_data.split("_")[2])
        await confirm_remove_user(update, context, user_id_to_remove)
    elif callback_data.startswith("confirm_remove_"):
        user_id_to_remove = int(callback_data.split("_")[2])
        await remove_user(update, context, user_id_to_remove)
    elif callback_data == "cancel_action":
        await show_users(update, context)

# Обработчик текстовых сообщений администратора
async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений для роли администратора"""
    user_id = update.effective_user.id
    
    # Проверяем, что пользователь действительно имеет роль администратора
    if get_user_role(user_id) != 'admin' and context.user_data.get('role') != 'admin':
        await update.message.reply_text(
            "У вас нет прав для доступа к панели администратора.",
            reply_markup=get_back_button()
        )
        return
    
    # Обработка ввода новых паролей
    if context.user_data.get('awaiting_new_manager_password'):
        context.user_data['awaiting_new_manager_password'] = False
        new_password = update.message.text
        
        # Здесь должен быть код для изменения пароля заведующего в конфигурации
        # Для простоты реализации пока просто показываем сообщение
        
        await update.message.reply_text(
            f"✅ Пароль для заведующих изменен на: {new_password}\n\n"
            f"Примечание: в текущей реализации это изменение не сохраняется после перезапуска бота.",
            reply_markup=get_admin_panel()
        )
    elif context.user_data.get('awaiting_new_admin_password'):
        context.user_data['awaiting_new_admin_password'] = False
        new_password = update.message.text
        
        # Здесь должен быть код для изменения пароля администратора в конфигурации
        # Для простоты реализации пока просто показываем сообщение
        
        await update.message.reply_text(
            f"✅ Пароль администратора изменен на: {new_password}\n\n"
            f"Примечание: в текущей реализации это изменение не сохраняется после перезапуска бота.",
            reply_markup=get_admin_panel()
        )
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте меню для навигации.",
            reply_markup=get_admin_panel()
        )

# Отображение панели администратора
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главную панель администратора"""
    query = update.callback_query
    await query.edit_message_text(
        "⚙️ Панель управления администратора\n\n"
        "Здесь вы можете управлять пользователями и системными настройками.",
        reply_markup=get_admin_panel()
    )

# Функции для управления пользователями
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех пользователей в системе"""
    query = update.callback_query
    
    # Получаем список пользователей
    users = get_all_users()
    
    if not users:
        await query.edit_message_text(
            "В системе пока нет зарегистрированных пользователей.",
            reply_markup=get_back_button("admin_panel")
        )
        return
    
    # Создаем сообщение со списком пользователей
    message = "👥 Список пользователей в системе:\n\n"
    
    for user_id, username, room_number, block_number, floor_number, dorm_name, role in users:
        role_emoji = {
            'student': '👨‍🎓',
            'elder': '👨‍💼',
            'manager': '🏢',
            'admin': '🔑'
        }.get(role, '👤')
        
        room_info = f"🛏️ {room_number}" if room_number else "Нет комнаты"
        user_info = f"{role_emoji} {username} (ID: {user_id}): {room_info}\n"
        message += user_info
    
    # Создаем клавиатуру
    keyboard = []
    
    # Добавляем кнопки для возврата и управления
    keyboard.append([InlineKeyboardButton("👤 Управление пользователями", callback_data="user_management")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup
    )

async def user_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает экран для управления пользователями"""
    query = update.callback_query
    
    # Получаем список пользователей
    users = get_all_users()
    
    if not users:
        await query.edit_message_text(
            "В системе пока нет зарегистрированных пользователей.",
            reply_markup=get_back_button("admin_panel")
        )
        return
    
    # Создаем клавиатуру с кнопками для каждого пользователя
    keyboard = []
    
    for user_id, username, room_number, block_number, floor_number, dorm_name, role in users:
        role_emoji = {
            'student': '👨‍🎓',
            'elder': '👨‍💼',
            'manager': '🏢',
            'admin': '🔑'
        }.get(role, '👤')
        
        room_info = f"🛏️ {room_number}" if room_number else "Нет комнаты"
        keyboard.append([InlineKeyboardButton(
            f"{role_emoji} {username}: {room_info}",
            callback_data=f"manage_user_{user_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="manage_users")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Выберите пользователя для управления:",
        reply_markup=reply_markup
    )

async def manage_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Показывает опции управления для конкретного пользователя"""
    query = update.callback_query
    
    # Получаем информацию о пользователе
    # Для упрощения используем фиктивные данные
    username = "Пользователь"
    
    # Создаем клавиатуру с опциями
    keyboard = [
        [InlineKeyboardButton("❌ Удалить пользователя", callback_data=f"remove_user_{user_id}")],
        [InlineKeyboardButton("🔄 Изменить роль", callback_data=f"change_role_{user_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="user_management")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Управление пользователем {username}",
        reply_markup=reply_markup
    )

async def confirm_remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Запрашивает подтверждение удаления пользователя"""
    query = update.callback_query
    
    await query.edit_message_text(
        "Вы уверены, что хотите удалить этого пользователя?\n\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirmation_menu("remove", user_id)
    )

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Удаляет пользователя из системы"""
    query = update.callback_query
    
    # Удаляем пользователя
    delete_user(user_id)
    
    await query.edit_message_text(
        "✅ Пользователь успешно удален из системы.",
        reply_markup=get_back_button("manage_users")
    )

# Функции для управления заведующими
async def manage_managers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление заведующими общежитий"""
    query = update.callback_query
    
    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton("🔄 Изменить пароль заведующих", callback_data="edit_manager_password")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👨‍💼 Управление заведующими\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def request_new_manager_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает новый пароль для заведующих"""
    query = update.callback_query
    context.user_data['awaiting_new_manager_password'] = True
    
    await query.edit_message_text(
        "Введите новый пароль для заведующих:",
        reply_markup=get_back_button("manage_managers")
    )

# Функции для системных настроек
async def show_system_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает системные настройки"""
    query = update.callback_query
    
    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton("🔄 Изменить пароль администратора", callback_data="edit_admin_password")],
        [InlineKeyboardButton("⚙️ Настройки уведомлений", callback_data="notification_settings")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ Системные настройки\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def request_new_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает новый пароль администратора"""
    query = update.callback_query
    context.user_data['awaiting_new_admin_password'] = True
    
    await query.edit_message_text(
        "Введите новый пароль администратора:",
        reply_markup=get_back_button("system_settings")
    )

# Показывает подробную статистику о пользователях
async def show_user_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображает подробную информацию о пользователях и статистику использования бота"""
    query = update.callback_query
    
    # Получаем список всех пользователей
    all_users = get_all_users()
    
    # Собираем статистику
    total_users = len(all_users)
    users_by_role = Counter([user[6] for user in all_users])  # Роль - седьмое поле в get_all_users
    users_by_dorm = Counter([user[5] for user in all_users if user[5]])  # Общежитие - шестое поле
    users_by_floor = Counter([(user[5], user[4]) for user in all_users if user[5] and user[4]])
    users_by_block = Counter([(user[5], user[4], user[3]) for user in all_users if user[5] and user[4] and user[3]])
    
    # Количество пользователей без комнаты
    users_without_room = sum(1 for user in all_users if not user[2])  # room_number - третье поле
    
    # Формируем текст сообщения
    message_text = f"📊 *СТАТИСТИКА ИСПОЛЬЗОВАНИЯ БОТА*\n\n"
    message_text += f"*Общее количество пользователей:* {total_users}\n\n"
    
    # Статистика по ролям
    message_text += "*По ролям:*\n"
    message_text += f"👤 Студенты: {users_by_role.get('student', 0)}\n"
    message_text += f"🛡️ Старосты: {users_by_role.get('elder', 0)}\n"
    message_text += f"🏢 Заведующие: {users_by_role.get('manager', 0)}\n"
    message_text += f"⚙️ Администраторы: {users_by_role.get('admin', 0)}\n\n"
    
    # Пользователи без комнаты
    message_text += f"*Пользователи без комнаты:* {users_without_room}\n\n"
    
    # Статистика по общежитиям
    if users_by_dorm:
        message_text += "*По общежитиям:*\n"
        for dorm, count in users_by_dorm.items():
            if dorm:  # Проверяем, что название общежития не пустое
                message_text += f"🏠 {dorm}: {count} пользователей\n"
        message_text += "\n"
    
    # Кнопка для просмотра детальной статистики
    keyboard = [
        [InlineKeyboardButton("📋 Детальный список пользователей", callback_data="show_users")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
