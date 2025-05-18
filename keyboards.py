from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Главное меню
def get_main_menu(user_role='student', has_room=False):
    keyboard = []
    
    # Кнопки для выбора комнаты и просмотра дежурств (только для студентов и старост)
    if user_role in ['student', 'elder']:
        if has_room:
            keyboard.append([InlineKeyboardButton("📅 Мои дежурства", callback_data="my_duties")])
            keyboard.append([InlineKeyboardButton("🔄 Изменить комнату", callback_data="select_room")])
        else:
            keyboard.append([InlineKeyboardButton("🏠 Выбрать комнату", callback_data="select_room")])
    
    # Добавляем кнопки в зависимости от роли
    if user_role == 'admin':
        keyboard.append([InlineKeyboardButton("⚙️ Панель администратора", callback_data="admin_panel")])
    elif user_role == 'manager':
        keyboard.append([InlineKeyboardButton("⚙️ Панель заведующего", callback_data="manager_panel")])
    elif user_role == 'elder':
        keyboard.append([InlineKeyboardButton("⚙️ Панель старосты", callback_data="elder_panel")])
    else:
        # Для обычных пользователей добавляем кнопку "Прочее"
        keyboard.append([InlineKeyboardButton("⚙️ Прочее", callback_data="other_options")])
    
    # Если пользователь уже вошел в роль, добавляем кнопку выхода
    if user_role != 'student':
        keyboard.append([InlineKeyboardButton("🚪 Выйти из панели управления", callback_data="logout_role")])
    
    return InlineKeyboardMarkup(keyboard)

# Меню выбора общежития
def get_dormitory_menu(dormitories):
    keyboard = []
    for dorm_id, dorm_name in dormitories:
        keyboard.append([InlineKeyboardButton(f"🏠 {dorm_name}", callback_data=f"dorm_{dorm_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

# Меню выбора этажа
def get_floor_menu(floors, dorm_id):
    keyboard = []
    for floor_id, floor_number in floors:
        keyboard.append([InlineKeyboardButton(f"🔢 Этаж {floor_number}", callback_data=f"floor_{floor_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад к общежитиям", callback_data="select_dorm")])
    keyboard.append([InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

# Меню выбора блока
def get_block_menu(blocks, floor_id):
    keyboard = []
    for block_id, block_number in blocks:
        keyboard.append([InlineKeyboardButton(f"🚪 Блок {block_number}", callback_data=f"block_{block_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад к этажам", callback_data="back_to_floors")])
    keyboard.append([InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

# Меню выбора комнаты
def get_room_menu(rooms, block_id):
    keyboard = []
    row = []
    for i, (room_id, room_number) in enumerate(rooms):
        row.append(InlineKeyboardButton(f"🛏️ {room_number}", callback_data=f"room_{room_id}"))
        if len(row) == 2 or i == len(rooms) - 1:
            keyboard.append(row)
            row = []
    keyboard.append([InlineKeyboardButton("🔙 Назад к блокам", callback_data="back_to_blocks")])
    keyboard.append([InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

# Подтверждение выбора комнаты
def get_room_confirmation_menu(room_id, is_change=False):
    action = "изменить" if is_change else "выбрать"
    keyboard = [
        [InlineKeyboardButton("✅ Да", callback_data=f"confirm_room_{room_id}")],
        [InlineKeyboardButton("❌ Нет", callback_data="select_room")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Панель старосты
def get_elder_panel():
    keyboard = [
        [InlineKeyboardButton("📅 Автоматическое назначение дежурств", callback_data="auto_schedule")],
        [InlineKeyboardButton("📋 Просмотр расписания", callback_data="view_schedule")],
        [InlineKeyboardButton("✍️ Изменить дежурство", callback_data="edit_duty")],
        [InlineKeyboardButton("👥 Список жителей блока", callback_data="list_residents")],
        [InlineKeyboardButton("🏠 Создать комнаты в блоке", callback_data="create_rooms")],
        [InlineKeyboardButton("⏰ Настройки уведомлений", callback_data="notification_settings")],
        [InlineKeyboardButton("🔙 Вернуться в главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Панель заведующего
def get_manager_panel():
    keyboard = [
        [InlineKeyboardButton("🏠 Управление общежитиями", callback_data="manage_dormitories")],
        [InlineKeyboardButton("🔙 Вернуться в главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Панель администратора
def get_admin_panel():
    keyboard = [
        [InlineKeyboardButton("👤 Управление пользователями", callback_data="manage_users")],
        [InlineKeyboardButton("📊 Статистика использования", callback_data="user_statistics")],
        [InlineKeyboardButton("🏢 Управление заведующими", callback_data="manage_managers")],
        [InlineKeyboardButton("⚙️ Системные настройки", callback_data="system_settings")],
        [InlineKeyboardButton("🔙 Вернуться в главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Меню расписания дежурств
def get_schedule_menu(page=0, total_pages=1):
    keyboard = []
    nav_row = []
    
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data="schedule_prev"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data="schedule_next"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_panel")])
    return InlineKeyboardMarkup(keyboard)

# Меню редактирования дежурства
def get_edit_duty_menu(duties, page=0, items_per_page=5):
    keyboard = []
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(duties))
    
    for duty_id, date, room_number, completed in duties[start_idx:end_idx]:
        status = "✅" if completed else "⏳"
        keyboard.append([
            InlineKeyboardButton(
                f"{date}: Комната {room_number} {status}", 
                callback_data=f"edit_duty_{duty_id}"
            )
        ])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data="edit_duty_prev"))
    if end_idx < len(duties):
        nav_row.append(InlineKeyboardButton("➡️", callback_data="edit_duty_next"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_panel")])
    return InlineKeyboardMarkup(keyboard)

# Меню выбора новой комнаты для дежурства
def get_select_room_for_duty_menu(rooms, duty_id):
    keyboard = []
    row = []
    
    for i, (room_id, room_number) in enumerate(rooms):
        row.append(InlineKeyboardButton(
            f"🛏️ {room_number}", 
            callback_data=f"assign_duty_{duty_id}_{room_id}"
        ))
        
        if len(row) == 2 or i == len(rooms) - 1:
            keyboard.append(row)
            row = []
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="edit_duty")])
    return InlineKeyboardMarkup(keyboard)

# Меню настроек уведомлений
def get_notification_settings_menu(preview_time, duty_time):
    keyboard = [
        [InlineKeyboardButton(f"⏰ Предварительное: {preview_time}", callback_data="change_preview_time")],
        [InlineKeyboardButton(f"⏰ Дежурное: {duty_time}", callback_data="change_duty_time")],
        [InlineKeyboardButton("✍️ Текст предварительного", callback_data="change_preview_text")],
        [InlineKeyboardButton("✍️ Текст дежурного", callback_data="change_duty_text")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Меню управления общежитиями
def get_manage_dormitories_menu(dormitories):
    keyboard = []
    
    for dorm_id, dorm_name in dormitories:
        keyboard.append([InlineKeyboardButton(f"🏠 {dorm_name}", callback_data=f"edit_dorm_{dorm_id}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить общежитие", callback_data="add_dormitory")])
    if dormitories:  # Добавляем кнопку удаления только если есть общежития
        keyboard.append([InlineKeyboardButton("🗑️ Удалить общежитие", callback_data="select_dorm_to_delete")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="manager_panel")])
    return InlineKeyboardMarkup(keyboard)

# Меню управления этажами
def get_manage_floors_menu(floors, dorm_id):
    keyboard = []
    
    for floor_id, floor_number in floors:
        keyboard.append([InlineKeyboardButton(f"🔢 Этаж {floor_number}", callback_data=f"edit_floor_{floor_id}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить этаж", callback_data=f"add_floor_{dorm_id}")])
    if floors:  # Добавляем кнопку удаления только если есть этажи
        keyboard.append([InlineKeyboardButton("🗑️ Удалить этаж", callback_data="select_floor_to_delete")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="manage_dormitories")])
    return InlineKeyboardMarkup(keyboard)

# Меню управления блоками
def get_manage_blocks_menu(blocks, floor_id):
    keyboard = []
    
    for block_id, block_number in blocks:
        keyboard.append([InlineKeyboardButton(f"🚪 Блок {block_number}", callback_data=f"edit_block_{block_id}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить блок", callback_data=f"add_block_{floor_id}")])
    if blocks:  # Добавляем кнопку удаления только если есть блоки
        keyboard.append([InlineKeyboardButton("🗑️ Удалить блок", callback_data="select_block_to_delete")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="manage_floors")])
    return InlineKeyboardMarkup(keyboard)

# Меню управления жителями блока
def get_residents_menu(users, page=0, items_per_page=5):
    keyboard = []
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(users))
    
    for user_id, username, room_number in users[start_idx:end_idx]:
        keyboard.append([InlineKeyboardButton(
            f"👤 {username} - 🛏️ Комната {room_number}", 
            callback_data=f"manage_resident_{user_id}"
        )])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data="residents_prev"))
    if end_idx < len(users):
        nav_row.append(InlineKeyboardButton("➡️", callback_data="residents_next"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_panel")])
    return InlineKeyboardMarkup(keyboard)

# Меню действий с жителем
def get_resident_actions_menu(user_id):
    keyboard = [
        [InlineKeyboardButton("❌ Удалить жителя", callback_data=f"remove_resident_{user_id}")],
        [InlineKeyboardButton("🔄 Изменить комнату", callback_data=f"change_resident_room_{user_id}")],
        [InlineKeyboardButton("🔙 Назад к списку", callback_data="list_residents")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Меню подтверждения действия
def get_confirmation_menu(action, entity_id):
    keyboard = [
        [InlineKeyboardButton("✅ Да, подтвердить", callback_data=f"confirm_{action}_{entity_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Кнопка "назад"
def get_back_button(callback_data="back_to_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=callback_data)]])

# Меню "Прочее"
def get_other_options_menu():
    keyboard = [
        [InlineKeyboardButton("👨‍💼 Войти как староста", callback_data="login_elder")],
        [InlineKeyboardButton("🏢 Войти как заведующий", callback_data="login_manager")],
        [InlineKeyboardButton("🔑 Войти как администратор", callback_data="login_admin")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)
