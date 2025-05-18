from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import MANAGER_PASSWORD
from database import (
    update_user_role,
    get_user_role,
    get_all_dormitories,
    add_dormitory,
    delete_dormitory,
    get_floors_by_dorm,
    add_floor,
    delete_floor,
    get_blocks_by_floor,
    add_block,
    delete_block,
    update_block_password,
    get_block_password,
    is_password_used,
    get_rooms_by_block,
    get_block_elders
)
from keyboards import (
    get_manager_panel,
    get_manage_dormitories_menu,
    get_manage_floors_menu,
    get_manage_blocks_menu,
    get_back_button
)

# Запрос пароля заведующего
async def request_manager_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает пароль для входа в панель заведующего"""
    query = update.callback_query
    
    # Устанавливаем флаг ожидания пароля
    context.user_data['awaiting_manager_password'] = True
    
    await query.edit_message_text(
        "🔐 Для входа в панель заведующего введите пароль:",
        reply_markup=get_back_button()
    )

# Обработка введенного пароля заведующего
async def handle_manager_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет введенный пароль заведующего"""
    # Сбрасываем флаг ожидания пароля
    context.user_data['awaiting_manager_password'] = False
    
    user_id = update.effective_user.id
    entered_password = update.message.text
    
    # Удаляем сообщение с паролем для безопасности
    try:
        await update.message.delete()
    except Exception as e:
        # Ошибка может возникнуть, если сообщение слишком старое или нет прав на удаление
        print(f"Не удалось удалить сообщение с паролем: {str(e)}")
        pass  # Продолжаем работу, даже если не удалось удалить сообщение
    
    if entered_password == MANAGER_PASSWORD:
        # Пароль верный, устанавливаем роль 'manager'
        update_user_role(user_id, 'manager')
        context.user_data['role'] = 'manager'
        
        await update.message.reply_text(
            "✅ Вы успешно вошли как заведующий.\n\n"
            "Теперь вы можете управлять общежитиями, этажами и блоками.",
            reply_markup=get_manager_panel()
        )
    else:
        # Пароль неверный
        await update.message.reply_text(
            "❌ Неверный пароль. Попробуйте снова или обратитесь к администратору.",
            reply_markup=get_back_button()
        )

# Обработчик кнопок заведующего
async def handle_manager_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки для роли заведующего"""
    query = update.callback_query
    callback_data = query.data
    
    # Проверяем, что пользователь действительно имеет роль заведующего
    user_id = update.effective_user.id
    if get_user_role(user_id) != 'manager' and context.user_data.get('role') != 'manager':
        await query.edit_message_text(
            "У вас нет прав для доступа к панели заведующего.",
            reply_markup=get_back_button()
        )
        return
    
    # Основные действия заведующего
    if callback_data == "manager_panel":
        await show_manager_panel(update, context)
    elif callback_data == "manage_dormitories":
        await show_dormitories(update, context)
    elif callback_data == "manage_floors":
        dorm_id = context.user_data.get('current_dorm_id')
        if dorm_id:
            await show_dorm_floors(update, context, dorm_id)
        else:
            await show_dormitories(update, context)
    elif callback_data == "add_dormitory":
        await request_dormitory_name(update, context)
    elif callback_data.startswith("edit_dorm_"):
        dorm_id = int(callback_data.split("_")[2])
        context.user_data['current_dorm_id'] = dorm_id
        await show_dorm_floors(update, context, dorm_id)
    elif callback_data.startswith("add_floor_"):
        dorm_id = int(callback_data.split("_")[2])
        await request_floor_number(update, context, dorm_id)
    elif callback_data.startswith("edit_floor_"):
        floor_id = int(callback_data.split("_")[2])
        await show_floor_blocks(update, context, floor_id)
    elif callback_data.startswith("add_block_"):
        floor_id = int(callback_data.split("_")[2])
        await request_block_info(update, context, floor_id)
    elif callback_data.startswith("edit_block_"):
        block_id = int(callback_data.split("_")[2])
        await show_block_info(update, context, block_id)
    # Обработчики для удаления объектов
    elif callback_data == "select_dorm_to_delete":
        await select_dormitory_to_delete(update, context)
    elif callback_data == "select_floor_to_delete":
        await select_floor_to_delete(update, context)
    elif callback_data == "select_block_to_delete":
        await select_block_to_delete(update, context)
    elif callback_data.startswith("confirm_delete_dorm_"):
        dorm_id = int(callback_data.split("_")[3])
        await confirm_delete_dormitory(update, context, dorm_id)
    elif callback_data.startswith("delete_dorm_"):
        dorm_id = int(callback_data.split("_")[2])
        await delete_dormitory_handler(update, context, dorm_id)
    elif callback_data.startswith("confirm_delete_floor_"):
        floor_id = int(callback_data.split("_")[3])
        await confirm_delete_floor(update, context, floor_id)
    elif callback_data.startswith("delete_floor_"):
        floor_id = int(callback_data.split("_")[2])
        await delete_floor_handler(update, context, floor_id)
    elif callback_data.startswith("confirm_delete_block_"):
        block_id = int(callback_data.split("_")[3])
        await confirm_delete_block(update, context, block_id)
    elif callback_data.startswith("delete_block_"):
        block_id = int(callback_data.split("_")[2])
        await delete_block_handler(update, context, block_id)
    elif callback_data == "change_block_password":
        block_id = context.user_data.get('current_block_id')
        if block_id:
            await request_new_block_password(update, context, block_id)
    elif callback_data == "view_all_schedules":
        await show_all_schedules(update, context)
    elif callback_data == "manage_elders":
        await manage_elders(update, context)

# Обработчик текстовых сообщений заведующего
async def handle_manager_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений для роли заведующего"""
    user_id = update.effective_user.id
    
    # Проверяем, что пользователь действительно имеет роль заведующего
    if get_user_role(user_id) != 'manager' and context.user_data.get('role') != 'manager':
        await update.message.reply_text(
            "У вас нет прав для доступа к панели заведующего.",
            reply_markup=get_back_button()
        )
        return
    
    # Обработка ввода данных – перенаправляем на специализированные функции
    if context.user_data.get('awaiting_dormitory_name'):
        await handle_dormitory_name(update, context)
    elif context.user_data.get('awaiting_floor_number'):
        await handle_floor_number(update, context)
    elif context.user_data.get('awaiting_block_number'):
        await handle_block_number(update, context)
    elif context.user_data.get('awaiting_block_password'):
        await handle_block_password(update, context)
    elif context.user_data.get('awaiting_new_block_password'):
        await handle_new_block_password(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте меню для навигации.",
            reply_markup=get_manager_panel()
        )

# Отображение панели заведующего
async def show_manager_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главную панель заведующего"""
    query = update.callback_query
    await query.edit_message_text(
        "⚙️ Панель управления заведующего\n\n"
        "Здесь вы можете управлять общежитиями, этажами, блоками и назначать старост.",
        reply_markup=get_manager_panel()
    )

# Функции для управления общежитиями
async def show_dormitories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех общежитий"""
    query = update.callback_query
    
    # Получаем список всех общежитий
    dormitories = get_all_dormitories()
    
    if not dormitories:
        await query.edit_message_text(
            "В системе пока нет общежитий. Добавьте первое общежитие.",
            reply_markup=get_manage_dormitories_menu([])
        )
        return
    
    await query.edit_message_text(
        "🏢 Управление общежитиями\n\n"
        "Выберите общежитие для управления или добавьте новое:",
        reply_markup=get_manage_dormitories_menu(dormitories)
    )

async def request_dormitory_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает название нового общежития"""
    query = update.callback_query
    context.user_data['awaiting_dormitory_name'] = True
    
    await query.edit_message_text(
        "Введите название нового общежития:",
        reply_markup=get_back_button("manage_dormitories")
    )

async def confirm_delete_dormitory(update: Update, context: ContextTypes.DEFAULT_TYPE, dorm_id: int):
    """Запрашивает подтверждение удаления общежития"""
    query = update.callback_query
    
    # Получаем информацию об общежитии
    dormitories = get_all_dormitories()
    dorm_name = "Неизвестное общежитие"
    
    for d_id, name in dormitories:
        if d_id == dorm_id:
            dorm_name = name
            break
    
    # Создаем клавиатуру с кнопками подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_dorm_{dorm_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="manage_dormitories")]
    ]
    
    await query.edit_message_text(
        f"⚠️ Вы уверены, что хотите удалить общежитие '{dorm_name}'?\n\n"
        "Это действие удалит все этажи, блоки и комнаты в этом общежитии!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_dormitory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, dorm_id: int):
    """Удаляет общежитие"""
    query = update.callback_query
    
    # Удаляем общежитие
    result = delete_dormitory(dorm_id)
    
    if result:
        await query.edit_message_text(
            "✅ Общежитие успешно удалено.",
            reply_markup=get_back_button("manage_dormitories")
        )
    else:
        await query.edit_message_text(
            "❌ Произошла ошибка при удалении общежития.",
            reply_markup=get_back_button("manage_dormitories")
        )

async def handle_dormitory_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает введенное название общежития"""
    # Сбрасываем флаг ожидания
    context.user_data['awaiting_dormitory_name'] = False
    
    # Получаем введенное название
    dorm_name = update.message.text.strip()
    
    if not dorm_name:
        await update.message.reply_text(
            "❌ Название общежития не может быть пустым. Попробуйте снова.",
            reply_markup=get_manager_panel()
        )
        return
    
    # Добавляем новое общежитие в базу данных
    dorm_id = add_dormitory(dorm_name)
    
    if dorm_id:
        await update.message.reply_text(
            f"✅ Общежитие '{dorm_name}' успешно добавлено.\n\n"
            "Теперь вы можете добавить этажи в это общежитие.",
            reply_markup=get_manager_panel()
        )
    else:
        await update.message.reply_text(
            "❌ Произошла ошибка при добавлении общежития. Возможно, такое название уже существует.",
            reply_markup=get_manager_panel()
        )

async def handle_floor_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает введенный номер этажа"""
    # Сбрасываем флаг ожидания
    context.user_data['awaiting_floor_number'] = False
    dorm_id = context.user_data.get('target_dorm_id')
    
    try:
        floor_number = int(update.message.text)
        
        # Добавляем новый этаж
        floor_id = add_floor(dorm_id, floor_number)
        
        if floor_id:
            await update.message.reply_text(
                f"✅ Этаж {floor_number} успешно добавлен.\n\n"
                "Теперь вы можете добавить блоки на этот этаж.",
                reply_markup=get_manager_panel()
            )
        else:
            await update.message.reply_text(
                "❌ Произошла ошибка при добавлении этажа. Возможно, такой этаж уже существует.",
                reply_markup=get_manager_panel()
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Некорректный номер этажа. Пожалуйста, введите число.",
            reply_markup=get_manager_panel()
        )

async def handle_block_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает введенный номер блока"""
    # Сбрасываем флаг ожидания
    context.user_data['awaiting_block_number'] = False
    floor_id = context.user_data.get('target_floor_id')
    block_number = update.message.text.strip()
    
    if not block_number:
        await update.message.reply_text(
            "❌ Номер блока не может быть пустым. Попробуйте снова.",
            reply_markup=get_manager_panel()
        )
        return
    
    # Переходим к вводу пароля для блока
    context.user_data['temp_block_number'] = block_number
    context.user_data['awaiting_block_password'] = True
    
    floor_id = context.user_data.get('target_floor_id')
    await update.message.reply_text(
        f"Введите пароль для блока {block_number}.\n"
        "Этот пароль будет использоваться старостой для входа в панель управления.",
        reply_markup=get_back_button(f"edit_floor_{floor_id}")
    )

async def handle_block_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает введенный пароль для блока"""
    # Сбрасываем флаг ожидания
    context.user_data['awaiting_block_password'] = False
    floor_id = context.user_data.get('target_floor_id')
    block_number = context.user_data.get('temp_block_number')
    block_password = update.message.text.strip()
    
    if not block_password:
        await update.message.reply_text(
            "❌ Пароль блока не может быть пустым. Попробуйте снова.",
            reply_markup=get_manager_panel()
        )
        return
    
    # Проверяем, используется ли уже этот пароль в других блоках
    if is_password_used(block_password):
        await update.message.reply_text(
            "❌ Этот пароль уже используется в другом блоке.\n\n"
            "Пожалуйста, используйте уникальный пароль для каждого блока.",
            reply_markup=get_manager_panel()
        )
        return
    
    # Добавляем новый блок
    block_id = add_block(floor_id, block_number, block_password)
    
    if block_id:
        await update.message.reply_text(
            f"✅ Блок {block_number} успешно добавлен.\n"
            f"Пароль для старосты: {block_password}\n\n"
            f"Не забудьте сообщить этот пароль старосте блока.\n\n"
            "Теперь вы можете добавить комнаты в этот блок.",
            reply_markup=get_manager_panel()
        )
    else:
        await update.message.reply_text(
            "❌ Произошла ошибка при добавлении блока. Возможно, такой блок уже существует.",
            reply_markup=get_manager_panel()
        )

async def handle_new_block_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает введенный новый пароль для блока"""
    # Сбрасываем флаг ожидания
    context.user_data['awaiting_new_block_password'] = False
    block_id = context.user_data.get('target_block_id')
    new_password = update.message.text.strip()
    
    if not new_password:
        await update.message.reply_text(
            "❌ Пароль блока не может быть пустым. Попробуйте снова.",
            reply_markup=get_manager_panel()
        )
        return
    
    # Обновляем пароль блока
    update_block_password(block_id, new_password)
    
    await update.message.reply_text(
        f"✅ Пароль блока успешно изменен на: {new_password}\n\n"
        f"Не забудьте сообщить новый пароль старосте блока.",
        reply_markup=get_manager_panel()
    )

async def handle_room_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает введенный номер комнаты"""
    # Сбрасываем флаг ожидания
    context.user_data['awaiting_room_number'] = False
    block_id = context.user_data.get('target_block_id')
    
    try:
        room_number = int(update.message.text)
        
        # Добавляем новую комнату
        room_id = add_room(block_id, room_number)
        
        if room_id:
            await update.message.reply_text(
                f"✅ Комната {room_number} успешно добавлена.",
                reply_markup=get_manager_panel()
            )
        else:
            await update.message.reply_text(
                "❌ Произошла ошибка при добавлении комнаты. Возможно, такая комната уже существует.",
                reply_markup=get_manager_panel()
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Некорректный номер комнаты. Пожалуйста, введите число.",
            reply_markup=get_manager_panel()
        )

# Функции для управления этажами
async def show_dorm_floors(update: Update, context: ContextTypes.DEFAULT_TYPE, dorm_id: int):
    """Показывает список этажей в общежитии"""
    query = update.callback_query
    context.user_data['current_dorm_id'] = dorm_id
    
    # Получаем список этажей
    floors = get_floors_by_dorm(dorm_id)
    
    # Получаем название общежития
    dormitories = get_all_dormitories()
    dorm_name = "Неизвестное общежитие"
    
    for d_id, name in dormitories:
        if d_id == dorm_id:
            dorm_name = name
            break
    
    if not floors:
        await query.edit_message_text(
            f"🏢 Общежитие: {dorm_name}\n\n"
            "В этом общежитии пока нет этажей. Добавьте первый этаж.",
            reply_markup=get_manage_floors_menu([], dorm_id)
        )
        return
    
    await query.edit_message_text(
        f"🏢 Общежитие: {dorm_name}\n\n"
        "Выберите этаж для управления или добавьте новый:",
        reply_markup=get_manage_floors_menu(floors, dorm_id)
    )

async def request_floor_number(update: Update, context: ContextTypes.DEFAULT_TYPE, dorm_id: int):
    """Запрашивает номер нового этажа"""
    query = update.callback_query
    context.user_data['awaiting_floor_number'] = True
    context.user_data['target_dorm_id'] = dorm_id
    
    await query.edit_message_text(
        "Введите номер нового этажа (число):",
        reply_markup=get_back_button("manage_dormitories")
    )

async def confirm_delete_floor(update: Update, context: ContextTypes.DEFAULT_TYPE, floor_id: int):
    """Запрашивает подтверждение удаления этажа"""
    query = update.callback_query
    dorm_id = context.user_data.get('current_dorm_id')
    
    # Получаем информацию об этаже
    floors = get_floors_by_dorm(dorm_id)
    floor_number = "неизвестный"
    
    for f_id, number in floors:
        if f_id == floor_id:
            floor_number = number
            break
    
    # Создаем клавиатуру с кнопками подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_floor_{floor_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"edit_dorm_{dorm_id}")]
    ]
    
    await query.edit_message_text(
        f"⚠️ Вы уверены, что хотите удалить этаж {floor_number}?\n\n"
        "Это действие удалит все блоки и комнаты на этом этаже!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_floor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, floor_id: int):
    """Удаляет этаж"""
    query = update.callback_query
    dorm_id = context.user_data.get('current_dorm_id')
    
    # Удаляем этаж
    result = delete_floor(floor_id)
    
    if result:
        await query.edit_message_text(
            "✅ Этаж успешно удален.",
            reply_markup=get_back_button(f"edit_dorm_{dorm_id}")
        )
    else:
        await query.edit_message_text(
            "❌ Произошла ошибка при удалении этажа.",
            reply_markup=get_back_button(f"edit_dorm_{dorm_id}")
        )

# Функции для управления блоками
async def show_floor_blocks(update: Update, context: ContextTypes.DEFAULT_TYPE, floor_id: int):
    """Показывает список блоков на этаже"""
    query = update.callback_query
    context.user_data['current_floor_id'] = floor_id
    
    # Получаем список блоков
    blocks = get_blocks_by_floor(floor_id)
    
    # Получаем информацию об этаже
    dorm_id = context.user_data.get('current_dorm_id')
    floors = get_floors_by_dorm(dorm_id)
    floor_number = "неизвестный"
    
    for f_id, number in floors:
        if f_id == floor_id:
            floor_number = number
            break
    
    if not blocks:
        await query.edit_message_text(
            f"🔢 Этаж: {floor_number}\n\n"
            "На этом этаже пока нет блоков. Добавьте первый блок.",
            reply_markup=get_manage_blocks_menu(blocks, floor_id)
        )
        return
    
    await query.edit_message_text(
        f"🔢 Этаж: {floor_number}\n\n"
        "Выберите блок для управления или добавьте новый:",
        reply_markup=get_manage_blocks_menu(blocks, floor_id)
    )

async def request_block_info(update: Update, context: ContextTypes.DEFAULT_TYPE, floor_id: int):
    query = update.callback_query
    context.user_data['awaiting_block_number'] = True
    context.user_data['target_floor_id'] = floor_id
    
    await query.edit_message_text(
        "Введите номер или название нового блока:",
        reply_markup=get_back_button(f"edit_floor_{floor_id}")
    )

async def confirm_delete_block(update: Update, context: ContextTypes.DEFAULT_TYPE, block_id: int):
    """Запрашивает подтверждение удаления блока"""
    query = update.callback_query
    floor_id = context.user_data.get('current_floor_id')
    
    # Получаем информацию об блоке
    blocks = get_blocks_by_floor(floor_id)
    block_number = "неизвестный"
    
    for b_id, number in blocks:
        if b_id == block_id:
            block_number = number
            break
    
    # Создаем клавиатуру с кнопками подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_block_{block_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"edit_floor_{floor_id}")]
    ]
    
    await query.edit_message_text(
        f"⚠️ Вы уверены, что хотите удалить блок {block_number}?\n\n"
        "Это действие удалит все комнаты в этом блоке!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_block_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, block_id: int):
    """Удаляет блок"""
    query = update.callback_query
    floor_id = context.user_data.get('current_floor_id')
    
    # Удаляем блок
    result = delete_block(block_id)
    
    if result:
        await query.edit_message_text(
            "✅ Блок успешно удален.",
            reply_markup=get_back_button(f"edit_floor_{floor_id}")
        )
    else:
        await query.edit_message_text(
            "❌ Произошла ошибка при удалении блока.",
            reply_markup=get_back_button(f"edit_floor_{floor_id}")
        )

async def show_block_info(update: Update, context: ContextTypes.DEFAULT_TYPE, block_id: int):
    """Показывает информацию о блоке"""
    query = update.callback_query
    floor_id = context.user_data.get('current_floor_id')
    
    # Сохраняем id блока в контексте
    context.user_data['current_block_id'] = block_id
    
    # Получаем информацию о блоке
    blocks = get_blocks_by_floor(floor_id)
    block_number = "неизвестный"
    
    for b_id, number in blocks:
        if b_id == block_id:
            block_number = number
            break
    
    # Получаем информацию о старостах блока
    elder_info = get_block_elders(block_id)
    elder_text = ""
    
    if elder_info:
        elder_text = "\n\nСтаросты блока:\n"
        for elder in elder_info:
            last_login = elder.get('last_login', 'Никогда')
            elder_text += f"👨‍💼 {elder['username']} (последний вход: {last_login})\n"
    else:
        elder_text = "\n\nСтарост блока нет или они еще не заходили в систему."
    
    # Создаем клавиатуру управления блоком
    keyboard = [
        [InlineKeyboardButton("🔑 Изменить пароль блока", callback_data="change_block_password")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"edit_floor_{floor_id}")]
    ]
    
    await query.edit_message_text(
        f"🚪 Блок: {block_number}{elder_text}\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def request_new_block_password(update: Update, context: ContextTypes.DEFAULT_TYPE, block_id: int):
    """Запрашивает новый пароль для блока"""
    query = update.callback_query
    context.user_data['awaiting_new_block_password'] = True
    context.user_data['target_block_id'] = block_id
    
    await query.edit_message_text(
        "Введите новый пароль для блока:",
        reply_markup=get_back_button("edit_block_" + str(block_id))
    )

# Функции для выбора объектов для удаления
async def select_dormitory_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список общежитий для выбора удаления"""
    query = update.callback_query
    
    # Получаем список всех общежитий
    dormitories = get_all_dormitories()
    
    if not dormitories:
        await query.edit_message_text(
            "В системе пока нет общежитий.",
            reply_markup=get_back_button("manage_dormitories")
        )
        return
    
    # Создаем клавиатуру с кнопками для каждого общежития
    keyboard = []
    for dorm_id, dorm_name in dormitories:
        keyboard.append([InlineKeyboardButton(
            f"🏠 {dorm_name}", 
            callback_data=f"confirm_delete_dorm_{dorm_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="manage_dormitories")])
    
    await query.edit_message_text(
        "⚠️ Выберите общежитие, которое хотите удалить:\n\n"
        "Эта операция безвозвратно удалит все этажи, блоки и комнаты в выбранном общежитии!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_floor_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список этажей для выбора удаления"""
    query = update.callback_query
    dorm_id = context.user_data.get('current_dorm_id')
    
    if not dorm_id:
        await query.edit_message_text(
            "Не удалось определить текущее общежитие.",
            reply_markup=get_back_button("manage_dormitories")
        )
        return
    
    # Получаем список этажей
    floors = get_floors_by_dorm(dorm_id)
    
    if not floors:
        await query.edit_message_text(
            "В этом общежитии пока нет этажей.",
            reply_markup=get_back_button(f"edit_dorm_{dorm_id}")
        )
        return
    
    # Создаем клавиатуру с кнопками для каждого этажа
    keyboard = []
    for floor_id, floor_number in floors:
        keyboard.append([InlineKeyboardButton(
            f"🔢 Этаж {floor_number}", 
            callback_data=f"confirm_delete_floor_{floor_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_dorm_{dorm_id}")])
    
    await query.edit_message_text(
        "⚠️ Выберите этаж, который хотите удалить:\n\n"
        "Эта операция безвозвратно удалит все блоки и комнаты на выбранном этаже!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_block_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список блоков для выбора удаления"""
    query = update.callback_query
    floor_id = context.user_data.get('current_floor_id')
    
    if not floor_id:
        await query.edit_message_text(
            "Не удалось определить текущий этаж.",
            reply_markup=get_back_button("manage_floors")
        )
        return
    
    # Получаем список блоков
    blocks = get_blocks_by_floor(floor_id)
    
    if not blocks:
        await query.edit_message_text(
            "На этом этаже пока нет блоков.",
            reply_markup=get_back_button(f"edit_floor_{floor_id}")
        )
        return
    
    # Создаем клавиатуру с кнопками для каждого блока
    keyboard = []
    for block_id, block_number in blocks:
        keyboard.append([InlineKeyboardButton(
            f"🚪 Блок {block_number}", 
            callback_data=f"confirm_delete_block_{block_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_floor_{floor_id}")])
    
    await query.edit_message_text(
        "⚠️ Выберите блок, который хотите удалить:\n\n"
        "Эта операция безвозвратно удалит все комнаты в выбранном блоке!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Функции для просмотра расписаний всех блоков
async def show_all_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расписания всех блоков"""
    query = update.callback_query
    
    # Пока реализуем заглушку
    await query.edit_message_text(
        "🗓 Расписания дежурств всех блоков\n\n"
        "Функция в разработке.",
        reply_markup=get_back_button("manager_panel")
    )

# Функции для управления старостами
async def manage_elders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление старостами блоков"""
    query = update.callback_query
    
    # Пока реализуем заглушку
    await query.edit_message_text(
        "👨‍💼 Управление старостами\n\n"
        "Функция в разработке.",
        reply_markup=get_back_button("manager_panel")
    )
