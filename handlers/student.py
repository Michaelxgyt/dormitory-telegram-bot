from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    get_all_dormitories, 
    get_floors_by_dorm, 
    get_blocks_by_floor, 
    get_rooms_by_block,
    get_room_details,
    add_user,
    update_user_room,
    get_user_duties,
    get_user_room_id
)
from keyboards import (
    get_main_menu,
    get_dormitory_menu,
    get_floor_menu,
    get_block_menu,
    get_room_menu,
    get_room_confirmation_menu,
    get_schedule_menu,
    get_back_button,
    get_other_options_menu
)

# Обработчик кнопок студента
async def handle_student_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки для роли студента"""
    query = update.callback_query
    callback_data = query.data
    user_id = update.effective_user.id
    
    # Выбор общежития, этажа, блока, комнаты
    if callback_data == "select_room":
        await select_dormitory(update, context)
    elif callback_data.startswith("dorm_"):
        dorm_id = int(callback_data.split("_")[1])
        context.user_data['selected_dorm_id'] = dorm_id
        await select_floor(update, context)
    elif callback_data.startswith("floor_"):
        floor_id = int(callback_data.split("_")[1])
        context.user_data['selected_floor_id'] = floor_id
        await select_block(update, context)
    elif callback_data.startswith("block_"):
        block_id = int(callback_data.split("_")[1])
        context.user_data['selected_block_id'] = block_id
        await select_room(update, context)
    elif callback_data.startswith("room_"):
        room_id = int(callback_data.split("_")[1])
        context.user_data['selected_room_id'] = room_id
        await confirm_room_selection(update, context)
    elif callback_data.startswith("confirm_room_"):
        room_id = int(callback_data.split("_")[2])
        await save_room_selection(update, context, room_id)
    
    # Навигация
    elif callback_data == "back_to_floors":
        await select_floor(update, context)
    elif callback_data == "back_to_blocks":
        await select_block(update, context)
    elif callback_data == "select_dorm":
        await select_dormitory(update, context)
    elif callback_data == "back_to_panel" or callback_data == "back_to_main":
        # Возврат на предыдущий экран
        user_id = update.effective_user.id
        has_room = get_user_room_id(user_id) is not None
        
        # Восстанавливаем состояние контекста пользователя
        context.user_data['has_room'] = has_room
        context.user_data.pop('duty_page', None)  # Сбрасываем страницу дежурств
        
        # Если мы были в меню дежурств, возвращаемся в главное меню
        username = update.effective_user.username or update.effective_user.first_name
        room_id = get_user_room_id(user_id)
        
        if room_id:
            room_details = get_room_details(room_id)
            if room_details:
                room_number, block_number, floor_number, dorm_name = room_details
                message = f"👋 Добро пожаловать, {username}!\n\n"
                message += f"🏠 Ваша комната: {room_number} (Блок {block_number}, Этаж {floor_number}, {dorm_name})\n\n"
                message += "Выберите действие:"
            else:
                message = f"👋 Добро пожаловать, {username}!\n\nВыберите действие:"
        else:
            message = f"👋 Добро пожаловать, {username}!\n\nВыберите действие:"
        
        await query.edit_message_text(
            message,
            reply_markup=get_main_menu('student', has_room)
        )
    
    # Просмотр расписания дежурств
    elif callback_data == "my_duties":
        await show_my_duties(update, context)
    elif callback_data.startswith("schedule_"):
        action = callback_data.split("_")[1]
        if action == "prev":
            context.user_data['duty_page'] = max(0, context.user_data.get('duty_page', 0) - 1)
        elif action == "next":
            context.user_data['duty_page'] = context.user_data.get('duty_page', 0) + 1
        await show_my_duties(update, context)
    
    # Меню "Прочее"
    elif callback_data == "other_options":
        await show_other_options(update, context)

# Обработчик текстовых сообщений студента
async def handle_student_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений для роли студента"""
    # В базовой реализации студент не принимает текстовые сообщения,
    # но можно расширить функционал
    await update.message.reply_text(
        "Пожалуйста, используйте меню для навигации.",
        reply_markup=get_main_menu('student', context.user_data.get('has_room', False))
    )

# Выбор общежития
async def select_dormitory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список общежитий для выбора"""
    query = update.callback_query
    
    dormitories = get_all_dormitories()
    
    if not dormitories:
        await query.edit_message_text(
            "В системе пока нет общежитий. Обратитесь к администратору.",
            reply_markup=get_back_button()
        )
        return
    
    await query.edit_message_text(
        "Выберите общежитие:",
        reply_markup=get_dormitory_menu(dormitories)
    )

# Выбор этажа
async def select_floor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список этажей выбранного общежития"""
    query = update.callback_query
    dorm_id = context.user_data.get('selected_dorm_id')
    
    if not dorm_id:
        await select_dormitory(update, context)
        return
    
    floors = get_floors_by_dorm(dorm_id)
    
    if not floors:
        await query.edit_message_text(
            "В этом общежитии пока нет добавленных этажей. Обратитесь к администратору.",
            reply_markup=get_back_button("select_dorm")
        )
        return
    
    await query.edit_message_text(
        "Выберите этаж:",
        reply_markup=get_floor_menu(floors, dorm_id)
    )

# Выбор блока
async def select_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список блоков выбранного этажа"""
    query = update.callback_query
    floor_id = context.user_data.get('selected_floor_id')
    
    if not floor_id:
        await select_floor(update, context)
        return
    
    blocks = get_blocks_by_floor(floor_id)
    
    if not blocks:
        await query.edit_message_text(
            "На этом этаже пока нет добавленных блоков. Обратитесь к администратору.",
            reply_markup=get_back_button("back_to_floors")
        )
        return
    
    await query.edit_message_text(
        "Выберите блок:",
        reply_markup=get_block_menu(blocks, floor_id)
    )

# Выбор комнаты
async def select_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список комнат выбранного блока"""
    query = update.callback_query
    block_id = context.user_data.get('selected_block_id')
    
    if not block_id:
        await select_block(update, context)
        return
    
    rooms = get_rooms_by_block(block_id)
    
    if not rooms:
        await query.edit_message_text(
            "В этом блоке пока нет добавленных комнат. Обратитесь к администратору.",
            reply_markup=get_back_button("back_to_blocks")
        )
        return
    
    await query.edit_message_text(
        "Выберите комнату:",
        reply_markup=get_room_menu(rooms, block_id)
    )

# Подтверждение выбора комнаты
async def confirm_room_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает подтверждение выбора комнаты"""
    query = update.callback_query
    room_id = context.user_data.get('selected_room_id')
    
    if not room_id:
        await select_room(update, context)
        return
    
    # Получаем подробную информацию о комнате
    room_details = get_room_details(room_id)
    
    if not room_details:
        await query.edit_message_text(
            "Не удалось получить информацию о комнате. Пожалуйста, выберите другую комнату.",
            reply_markup=get_back_button("back_to_blocks")
        )
        return
    
    room_number, block_number, floor_number, dorm_name = room_details
    
    # Проверяем, есть ли у пользователя уже выбранная комната
    current_room_id = get_user_room_id(update.effective_user.id)
    is_change = current_room_id is not None
    
    message = f"Вы выбрали:\n\n"
    message += f"🏠 Общежитие: {dorm_name}\n"
    message += f"🔢 Этаж: {floor_number}\n"
    message += f"🚪 Блок: {block_number}\n"
    message += f"🛏️ Комната: {room_number}\n\n"
    
    if is_change:
        message += "Вы хотите изменить свою комнату на эту?"
    else:
        message += "Подтвердить выбор?"
    
    await query.edit_message_text(
        message,
        reply_markup=get_room_confirmation_menu(room_id, is_change)
    )

# Сохранение выбора комнаты
async def save_room_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, room_id: int):
    """Сохраняет выбор комнаты пользователя"""
    query = update.callback_query
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Получаем информацию о комнате
    room_details = get_room_details(room_id)
    
    if not room_details:
        await query.edit_message_text(
            "Не удалось получить информацию о комнате. Пожалуйста, попробуйте снова.",
            reply_markup=get_back_button()
        )
        return
    
    room_number, block_number, floor_number, dorm_name = room_details
    
    # Проверяем, новый ли это пользователь или обновление комнаты
    current_room_id = get_user_room_id(user_id)
    
    if current_room_id:
        # Обновляем комнату существующего пользователя
        update_user_room(user_id, room_id)
    else:
        # Добавляем нового пользователя
        add_user(user_id, username, room_id)
    
    # Обновляем флаг наличия комнаты
    context.user_data['has_room'] = True
    
    await query.edit_message_text(
        f"✅ Вы успешно {current_room_id and 'изменили' or 'выбрали'} комнату:\n\n"
        f"🏠 Общежитие: {dorm_name}\n"
        f"🔢 Этаж: {floor_number}\n"
        f"🚪 Блок: {block_number}\n"
        f"🛏️ Комната: {room_number}\n\n"
        f"Теперь вы будете получать уведомления о дежурствах для этой комнаты.",
        reply_markup=get_main_menu('student', True)
    )

# Показать расписание дежурств пользователя
async def show_my_duties(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список предстоящих дежурств пользователя"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Получаем информацию о комнате пользователя
    room_id = get_user_room_id(user_id)
    room_details = get_room_details(room_id) if room_id else None
    
    # Получаем список дежурств
    duties = get_user_duties(user_id)
    
    if not duties:
        await query.edit_message_text(
            "🗓️ Информация о дежурствах\n\n"
            "У вас пока нет запланированных дежурств.\n\n"
            "Если вы считаете, что это ошибка, обратитесь к старосте блока.",
            reply_markup=get_back_button("back_to_main")
        )
        return
    
    # Определяем страницу
    page = context.user_data.get('duty_page', 0)
    items_per_page = 5
    total_pages = (len(duties) + items_per_page - 1) // items_per_page
    
    # Проверяем, что страница в допустимом диапазоне
    if page >= total_pages:
        page = 0
        context.user_data['duty_page'] = 0
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(duties))
    
    # Добавляем информацию о комнате и блоке в заголовок
    room_info = ""
    if room_details:
        room_number, block_number, floor_number, dorm_name = room_details
        room_info = f"\n🏠 Общежитие: {dorm_name}\n"
        room_info += f"🔢 Этаж: {floor_number}\n"
        room_info += f"🚪 Блок: {block_number}\n"
        room_info += f"🛏️ Комната: {room_number}\n"
    
    message = "🗓️ Информация о дежурствах{room_info}\n\nБлижайшие дежурства:\n"
    
    # Форматируем даты и добавляем дополнительную информацию о днях недели
    from datetime import datetime
    for date, completed in duties[start_idx:end_idx]:
        # Преобразуем строку даты в объект datetime
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            # Получаем название дня недели на русском
            weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            weekday = weekdays[date_obj.weekday()]
            # Форматируем дату в более читабельном формате
            formatted_date = date_obj.strftime('%d.%m.%Y')
        except:
            weekday = ""
            formatted_date = date
        
        # Определяем статус дежурства
        if completed:
            status = "✅ Выполнено"
        else:
            # Проверяем, является ли дата сегодняшней
            today = datetime.now().strftime('%Y-%m-%d')
            if date == today:
                status = "🔥 Сегодня"
            else:
                status = "⏳ Ожидается"
        
        message += f"• {formatted_date} ({weekday}): {status}\n"
    
    message += f"\nСтраница {page + 1} из {total_pages}\n\n"
    message += "ℹ️ Если у вас есть вопросы по расписанию, обратитесь к старосте блока."
    
    # Создаем клавиатуру с кнопками навигации
    keyboard = []
    nav_row = []
    
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data="schedule_prev"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data="schedule_next"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_other_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню с дополнительными опциями (вход в различные роли)"""
    query = update.callback_query
    
    await query.edit_message_text(
        "⚙️ Дополнительные опции\n\n"
        "Выберите, в какую панель управления вы хотите войти:",
        reply_markup=get_other_options_menu()
    )
