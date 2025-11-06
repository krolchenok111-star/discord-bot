import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
import json
from flask import Flask
from threading import Thread
import requests

# ============================================================================
# ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖАНИЯ РАБОТЫ НА REPLIT
# ============================================================================

# Создаем Flask приложение (веб-сервер)
app = Flask('')

@app.route('/')
def home():
    return "🤖 Бот напоминаний работает! Статус: онлайн"

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/health')
def health():
    return "🤖 Бот напоминаний работает! Статус: онлайн", 200

def run_webserver():
    """Запускает веб-сервер в отдельном потоке"""
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    """Запускает веб-сервер для поддержания работы на Replit"""
    t = Thread(target=run_webserver)
    t.daemon = True
    t.start()

# ============================================================================
# ОСНОВНОЙ КОД БОТА
# ============================================================================

# Загрузка переменных окружения
load_dotenv()

# Настройка бота
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)

# Хранилища данных
reminders = {}
categories_data = {}
USERS_FILE = 'users_data.json'
CATEGORIES_FILE = 'categories.json'
ADMIN_ROLES = ['Администратор', 'Директор']  # Роли с правами администратора

# ============================================================================
# СИСТЕМА ХРАНЕНИЯ ДАННЫХ
# ============================================================================

def load_data():
    """Загрузка данных из файлов при запуске бота"""
    global reminders, categories_data
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                reminders = json.load(f)
        if os.path.exists(CATEGORIES_FILE):
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                categories_data = json.load(f)
        print("✅ Данные успешно загружены")
    except Exception as e:
        print(f"❌ Ошибка загрузки данных: {e}")

def save_data():
    """Сохранение данных в файлы"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(reminders, f, ensure_ascii=False, indent=2)
        with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(categories_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка сохранения данных: {e}")

def init_default_categories():
    """Инициализация стандартных категорий при первом запуске"""
    if not categories_data:
        categories_data['таймер'] = {
            'name': '⏰ Таймер',
            'subcategories': {
                'настраиваемый': {'name': '🔄 Настраиваемый таймер', 'type': 'custom', 'time': None, 'message': None},
                'оплата_дома': {'name': '🏠 Оплата дома', 'type': 'fixed', 'time': '0д 0ч 1м', 'message': 'Время оплатить дом!'},
                'оплата_недвижимости': {'name': '🏢 Оплата недвижимости', 'type': 'fixed', 'time': '0д 0ч 2м', 'message': 'Время оплатить недвижимость!'}
            }
        }
        categories_data['фарм'] = {
            'name': '🌾 Фарм',
            'subcategories': {
                'настраиваемый': {'name': '🔄 Настраиваемый таймер', 'type': 'custom', 'time': None, 'message': None},
                'билетики': {'name': '🎫 Билетики', 'type': 'fixed', 'time': '0д 1ч 0м', 'message': 'Проверить билетики!'},
                'квесты': {'name': '📜 Квесты', 'type': 'fixed', 'time': '0д 2ч 0м', 'message': 'Время квестов!'}
            }
        }
        categories_data['задания_клуба'] = {
            'name': '🏁 Задания клуба',
            'subcategories': {
                'настраиваемый': {'name': '🔄 Настраиваемый таймер', 'type': 'custom', 'time': None, 'message': None},
                'реднеки': {'name': '🤠 Реднеки', 'type': 'fixed', 'time': '0д 0ч 1м', 'message': 'Задание Реднеки!'},
                'мото_клуб': {'name': '🏍️ Мото клуб', 'type': 'fixed', 'time': '0д 0ч 1м', 'message': 'Задание Мото-клуба!'},
                'epsilon': {'name': '👽 Epsilon', 'type': 'fixed', 'time': '0д 0ч 1м', 'message': 'Задание Epsilon!'}
            }
        }
        save_data()
        print("✅ Стандартные категории инициализированы")

def is_admin(user):
    """Проверка прав администратора у пользователя"""
    if isinstance(user, discord.Member):
        return any(role.name in ADMIN_ROLES for role in user.roles)
    return False

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def parse_time_string(time_str):
    """Парсинг строки времени в секунды (например: '2ч30м' -> 9000)"""
    time_str = time_str.lower().replace(' ', '')
    total_seconds = 0
    current_num = ''

    for char in time_str:
        if char.isdigit():
            current_num += char
        else:
            if current_num:
                num = int(current_num)
                if char == 'с':
                    total_seconds += num
                elif char == 'м':
                    total_seconds += num * 60
                elif char == 'ч':
                    total_seconds += num * 3600
                elif char == 'д':
                    total_seconds += num * 86400
                current_num = ''

    return total_seconds

def format_time(seconds):
    """Форматирование секунд в читаемую строку"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)

    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}м")

    return " ".join(parts) if parts else "0сек"

def calculate_seconds(days: int, hours: int, minutes: int):
    """Вычисление общего количества секунд из дней, часов и минут"""
    return days * 86400 + hours * 3600 + minutes * 60

# ============================================================================
# СИСТЕМА САМО-ПИНГА ДЛЯ ПОДДЕРЖАНИЯ АКТИВНОСТИ
# ============================================================================

@tasks.loop(minutes=4)
async def self_ping():
    """Само-пинг для поддержания активности Replit"""
    try:
        response = requests.get('http://127.0.0.1:5000/ping', timeout=5)
        print(f"✅ Self-ping: {response.status_code}")
    except Exception as e:
        print(f"❌ Self-ping failed: {e}")

# ============================================================================
# ГЛАВНОЕ МЕНЮ - КАТЕГОРИИ
# ============================================================================

class StartMenu(discord.ui.View):
    """Главное меню с выбором категорий"""
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label='⏰ Таймер', style=discord.ButtonStyle.primary, emoji='⏰')
    async def timer_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_subcategories(interaction, 'таймер')

    @discord.ui.button(label='🌾 Фарм', style=discord.ButtonStyle.success, emoji='🌾')
    async def farm_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_subcategories(interaction, 'фарм')

    @discord.ui.button(label='🏁 Задания клуба', style=discord.ButtonStyle.danger, emoji='🏁')
    async def club_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_subcategories(interaction, 'задания_клуба')

    @discord.ui.button(label='⚙️ Управление', style=discord.ButtonStyle.secondary, emoji='⚙️', row=1)
    async def admin_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message('❌ Недостаточно прав! Только для администраторов.', ephemeral=True)
            return
        await show_admin_categories(interaction)

async def show_subcategories(interaction: discord.Interaction, category_key: str):
    """Отображение подкатегорий выбранной категории"""
    if category_key not in categories_data:
        await interaction.response.send_message('❌ Категория не найдена!', ephemeral=True)
        return

    category = categories_data[category_key]

    embed = discord.Embed(
        title=f"{category['name']} - Подкатегории",
        description="Выберите нужную опцию:",
        color=0x00ff00
    )

    view = SubcategoryMenu(category_key)

    for key, subcat in category['subcategories'].items():
        time_info = f" | ⏰ {subcat['time']}" if subcat['time'] else ""
        embed.add_field(
            name=f"{subcat['name']}{time_info}",
            value=f"💬 {subcat['message'] or 'Настраиваемое напоминание'}",
            inline=False
        )

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class SubcategoryMenu(discord.ui.View):
    """Меню подкатегорий с кнопками"""
    def __init__(self, category_key: str):
        super().__init__(timeout=180)
        self.category_key = category_key

        category = categories_data[category_key]
        for key, subcat in category['subcategories'].items():
            button_label = subcat['name']
            if len(button_label) > 80:
                button_label = button_label[:77] + "..."

            button = discord.ui.Button(
                label=button_label,
                style=discord.ButtonStyle.primary,
                custom_id=f"sub_{key}"
            )
            button.callback = self.create_callback(key)
            self.add_item(button)

    def create_callback(self, sub_key):
        async def callback(interaction: discord.Interaction):
            await self.handle_subcategory(interaction, sub_key)
        return callback

    async def handle_subcategory(self, interaction: discord.Interaction, sub_key: str):
        category = categories_data[self.category_key]
        subcategory = category['subcategories'].get(sub_key)

        if not subcategory:
            await interaction.response.send_message('❌ Подкатегория не найдена!', ephemeral=True)
            return

        if subcategory['type'] == 'custom':
            await self.handle_custom_timer(interaction, self.category_key, sub_key)
        elif subcategory['type'] == 'fixed':
            await self.handle_fixed_timer(interaction, self.category_key, sub_key)

    async def handle_custom_timer(self, interaction: discord.Interaction, category_key: str, sub_key: str):
        modal = CustomTimerModal(category_key, sub_key)
        await interaction.response.send_modal(modal)

    async def handle_fixed_timer(self, interaction: discord.Interaction, category_key: str, sub_key: str):
        category = categories_data[category_key]
        subcategory = category['subcategories'][sub_key]

        total_seconds = parse_time_string(subcategory['time'])
        end_time = datetime.now() + timedelta(seconds=total_seconds)

        reminder_id = f"{interaction.user.id}_{datetime.now().timestamp()}"
        reminders[reminder_id] = {
            'message': subcategory['message'],
            'end_time': end_time.isoformat(),
            'user_id': interaction.user.id,
            'category': f"{category['name']} - {subcategory['name']}"
        }

        save_data()

        await interaction.response.send_message(
            f"✅ **Напоминание установлено!**\n"
            f"📁 **Категория:** {category['name']} - {subcategory['name']}\n"
            f"⏰ **Через:** {subcategory['time']}\n"
            f"📝 **Сообщение:** {subcategory['message']}\n"
            f"🕐 **Сработает:** {end_time.strftime('%d.%m.%Y в %H:%M:%S')}",
            ephemeral=True
        )

# ============================================================================
# АДМИНИСТРАТИВНОЕ МЕНЮ - УПРАВЛЕНИЕ КАТЕГОРИЯМИ
# ============================================================================

async def show_admin_categories(interaction: discord.Interaction):
    """Показывает меню управления категориями для администраторов"""
    embed = discord.Embed(
        title='⚙️ Управление категориями',
        description='Выберите категорию для управления:',
        color=0xffa500
    )

    for key, category in categories_data.items():
        subcategories_count = len(category['subcategories'])
        embed.add_field(
            name=f"{category['name']}",
            value=f"📊 Подкатегорий: {subcategories_count}",
            inline=True
        )

    embed.add_field(
        name="➕ Новая категория",
        value="Создать новую категорию",
        inline=False
    )

    view = AdminCategoriesMenu()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class AdminCategoriesMenu(discord.ui.View):
    """Меню управления категориями для администраторов"""
    def __init__(self):
        super().__init__(timeout=180)
        self.create_buttons()

    def create_buttons(self):
        for key, category in categories_data.items():
            button_label = category['name']
            if len(button_label) > 80:
                button_label = button_label[:77] + "..."

            button = discord.ui.Button(
                label=button_label,
                style=discord.ButtonStyle.primary,
                custom_id=f"admin_cat_{key}"
            )
            button.callback = self.create_category_callback(key)
            self.add_item(button)

        add_button = discord.ui.Button(
            label='➕ Создать категорию',
            style=discord.ButtonStyle.success,
            custom_id="add_category"
        )
        add_button.callback = self.add_category_callback
        self.add_item(add_button)

    def create_category_callback(self, category_key):
        async def callback(interaction: discord.Interaction):
            await show_category_management(interaction, category_key)
        return callback

    async def add_category_callback(self, interaction: discord.Interaction):
        modal = AddCategoryModal()
        await interaction.response.send_modal(modal)

async def show_category_management(interaction: discord.Interaction, category_key: str):
    """Показывает меню управления конкретной категорией"""
    category = categories_data[category_key]

    embed = discord.Embed(
        title=f'⚙️ Управление: {category["name"]}',
        description='Выберите действие:',
        color=0x0099ff
    )

    embed.add_field(
        name="📊 Информация",
        value=f"Подкатегорий: {len(category['subcategories'])}",
        inline=False
    )

    if category['subcategories']:
        subcats_text = "\n".join([
            f"• {subcat['name']} ({subcat['type']})" 
            for subcat in category['subcategories'].values()
        ])
        embed.add_field(
            name="📁 Подкатегории",
            value=subcats_text,
            inline=False
        )

    view = CategoryManagementMenu(category_key)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class CategoryManagementMenu(discord.ui.View):
    """Меню управления конкретной категорией"""
    def __init__(self, category_key: str):
        super().__init__(timeout=180)
        self.category_key = category_key

    @discord.ui.button(label='✏️ Редактировать категорию', style=discord.ButtonStyle.primary)
    async def edit_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditCategoryModal(self.category_key)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='📝 Управление подкатегориями', style=discord.ButtonStyle.secondary)
    async def manage_subcategories(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_subcategories_management(interaction, self.category_key)

    @discord.ui.button(label='🗑️ Удалить категорию', style=discord.ButtonStyle.danger)
    async def delete_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        category_name = categories_data[self.category_key]['name']
        del categories_data[self.category_key]
        save_data()

        await interaction.response.send_message(
            f"✅ **Категория удалена!**\n"
            f"🗑️ {category_name}",
            ephemeral=True
        )

async def show_subcategories_management(interaction: discord.Interaction, category_key: str):
    """Показывает меню управления подкатегориями"""
    category = categories_data[category_key]

    embed = discord.Embed(
        title=f'📝 Управление подкатегориями: {category["name"]}',
        description='Выберите подкатегорию для управления или создайте новую:',
        color=0x9370DB
    )

    for key, subcat in category['subcategories'].items():
        time_info = f" | ⏰ {subcat['time']}" if subcat['time'] else ""
        embed.add_field(
            name=f"{subcat['name']}{time_info}",
            value=f"Тип: {subcat['type']} | 💬 {subcat['message'] or 'Нет сообщения'}",
            inline=False
        )

    view = SubcategoriesManagementMenu(category_key)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class SubcategoriesManagementMenu(discord.ui.View):
    """Меню управления подкатегориями"""
    def __init__(self, category_key: str):
        super().__init__(timeout=180)
        self.category_key = category_key
        self.create_buttons()

    def create_buttons(self):
        category = categories_data[self.category_key]

        for key, subcat in category['subcategories'].items():
            button_label = subcat['name']
            if len(button_label) > 80:
                button_label = button_label[:77] + "..."

            button = discord.ui.Button(
                label=button_label,
                style=discord.ButtonStyle.primary
            )
            button.callback = self.create_subcategory_callback(key)
            self.add_item(button)

        add_button = discord.ui.Button(
            label='➕ Добавить подкатегорию',
            style=discord.ButtonStyle.success
        )
        add_button.callback = self.add_subcategory_callback
        self.add_item(add_button)

        back_button = discord.ui.Button(
            label='↩️ Назад к категориям',
            style=discord.ButtonStyle.secondary
        )
        back_button.callback = self.back_callback
        self.add_item(back_button)

    def create_subcategory_callback(self, sub_key):
        async def callback(interaction: discord.Interaction):
            await show_subcategory_management(interaction, self.category_key, sub_key)
        return callback

    async def add_subcategory_callback(self, interaction: discord.Interaction):
        modal = AddSubcategoryModal(self.category_key)
        await interaction.response.send_modal(modal)

    async def back_callback(self, interaction: discord.Interaction):
        await show_admin_categories(interaction)

async def show_subcategory_management(interaction: discord.Interaction, category_key: str, sub_key: str):
    """Показывает меню управления конкретной подкатегорией"""
    category = categories_data[category_key]
    subcat = category['subcategories'][sub_key]

    embed = discord.Embed(
        title=f'⚙️ Управление: {subcat["name"]}',
        description='Выберите действие:',
        color=0x00ff00
    )

    embed.add_field(name="Тип", value=subcat['type'], inline=True)
    if subcat['time']:
        embed.add_field(name="Время", value=subcat['time'], inline=True)
    if subcat['message']:
        embed.add_field(name="Сообщение", value=subcat['message'], inline=True)

    view = SubcategoryManagementMenu(category_key, sub_key)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class SubcategoryManagementMenu(discord.ui.View):
    """Меню управления конкретной подкатегорией"""
    def __init__(self, category_key: str, sub_key: str):
        super().__init__(timeout=180)
        self.category_key = category_key
        self.sub_key = sub_key

    @discord.ui.button(label='✏️ Редактировать', style=discord.ButtonStyle.primary)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditSubcategoryModal(self.category_key, self.sub_key)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🗑️ Удалить', style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        category = categories_data[self.category_key]
        subcat_name = category['subcategories'][self.sub_key]['name']

        if len(category['subcategories']) <= 1:
            await interaction.response.send_message(
                "❌ Нельзя удалить последнюю подкатегорию в категории!",
                ephemeral=True
            )
            return

        del category['subcategories'][self.sub_key]
        save_data()

        await interaction.response.send_message(
            f"✅ **Подкатегория удалена!**\n"
            f"🗑️ {subcat_name}",
            ephemeral=True
        )

    @discord.ui.button(label='↩️ Назад', style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_subcategories_management(interaction, self.category_key)

# ============================================================================
# МОДАЛЬНЫЕ ОКНА ДЛЯ АДМИНИСТРАТИВНЫХ ФУНКЦИЙ
# ============================================================================

class AddCategoryModal(discord.ui.Modal, title='Создание новой категории'):
    name_input = discord.ui.TextInput(
        label='Название категории',
        placeholder='Введите название категории...',
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            import re
            key_base = re.sub(r'[^a-zA-Z0-9_]', '', self.name_input.value.lower().replace(' ', '_'))
            key = key_base

            counter = 1
            while key in categories_data:
                key = f"{key_base}_{counter}"
                counter += 1

            categories_data[key] = {
                'name': self.name_input.value,
                'subcategories': {
                    'настраиваемый': {
                        'name': '🔄 Настраиваемый таймер', 
                        'type': 'custom', 
                        'time': None, 
                        'message': None
                    }
                }
            }

            save_data()

            await interaction.response.send_message(
                f"✅ **Новая категория создана!**\n"
                f"📁 {self.name_input.value}\n"
                f"🔑 Ключ: {key}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ **Ошибка при создании категории:** {e}",
                ephemeral=True
            )

class EditCategoryModal(discord.ui.Modal, title='Редактирование категории'):
    def __init__(self, category_key: str):
        super().__init__()
        self.category_key = category_key
        self.name_input = discord.ui.TextInput(
            label='Название категории',
            placeholder='Введите название категории...',
            default=categories_data[category_key]['name'],
            required=True,
            max_length=50
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            categories_data[self.category_key]['name'] = self.name_input.value
            save_data()

            await interaction.response.send_message(
                f"✅ **Категория обновлена!**\n"
                f"📁 {self.name_input.value}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ **Ошибка при обновлении категории:** {e}",
                ephemeral=True
            )

class AddSubcategoryModal(discord.ui.Modal, title='Добавление подкатегории'):
    def __init__(self, category_key: str):
        super().__init__()
        self.category_key = category_key

    name_input = discord.ui.TextInput(
        label='Название подкатегории',
        placeholder='Введите название...',
        required=True,
        max_length=50
    )

    type_input = discord.ui.TextInput(
        label='Тип (custom/fixed)',
        placeholder='custom или fixed',
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            category = categories_data[self.category_key]
            subcat_type = self.type_input.value.lower()

            if subcat_type not in ['custom', 'fixed']:
                await interaction.response.send_message('❌ Тип должен быть "custom" или "fixed"!', ephemeral=True)
                return

            import re
            key_base = re.sub(r'[^a-zA-Z0-9_]', '', self.name_input.value.lower().replace(' ', '_'))
            key = key_base

            counter = 1
            while key in category['subcategories']:
                key = f"{key_base}_{counter}"
                counter += 1

            new_subcat = {
                'name': self.name_input.value,
                'type': subcat_type,
                'time': None,
                'message': None
            }

            if subcat_type == 'fixed':
                category['subcategories'][key] = new_subcat
                save_data()
                
                modal = FixedTimerSetupModal(self.category_key, key, new_subcat)
                await interaction.response.send_modal(modal)
            else:
                category['subcategories'][key] = new_subcat
                save_data()

                await interaction.response.send_message(
                    f"✅ **Новая подкатегория добавлена!**\n"
                    f"📝 {self.name_input.value}\n"
                    f"🔧 Тип: {subcat_type}",
                    ephemeral=True
                )

        except Exception as e:
            await interaction.response.send_message('❌ Произошла ошибка при создании подкатегории!', ephemeral=True)

class EditSubcategoryModal(discord.ui.Modal, title='Редактирование подкатегории'):
    def __init__(self, category_key: str, sub_key: str):
        super().__init__()
        self.category_key = category_key
        self.sub_key = sub_key

        category = categories_data[category_key]
        subcat = category['subcategories'][sub_key]

        self.name_input = discord.ui.TextInput(
            label='Название подкатегории',
            default=subcat['name'],
            required=True,
            max_length=50
        )

        self.add_item(self.name_input)

        if subcat['type'] == 'fixed':
            time_str = subcat['time'] or '0д 0ч 0м'
            time_parts = {'д': '0', 'ч': '0', 'м': '0'}
            current_num = ''

            for char in time_str:
                if char.isdigit():
                    current_num += char
                elif char in time_parts and current_num:
                    time_parts[char] = current_num
                    current_num = ''

            self.days_input = discord.ui.TextInput(
                label='Дни (для fixed)',
                default=time_parts['д'],
                required=True,
                max_length=3
            )
            self.hours_input = discord.ui.TextInput(
                label='Часы (для fixed)',
                default=time_parts['ч'],
                required=True,
                max_length=2
            )
            self.minutes_input = discord.ui.TextInput(
                label='Минуты (для fixed)',
                default=time_parts['м'],
                required=True,
                max_length=2
            )
            self.message_input = discord.ui.TextInput(
                label='Сообщение (для fixed)',
                default=subcat['message'] or '',
                required=True,
                max_length=100
            )

            self.add_item(self.days_input)
            self.add_item(self.hours_input)
            self.add_item(self.minutes_input)
            self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            category = categories_data[self.category_key]
            subcat = category['subcategories'][self.sub_key]

            subcat['name'] = self.name_input.value

            if subcat['type'] == 'fixed':
                days = int(self.days_input.value)
                hours = int(self.hours_input.value)
                minutes = int(self.minutes_input.value)

                if days < 0 or hours < 0 or minutes < 0:
                    await interaction.response.send_message('❌ Время не может быть отрицательным!', ephemeral=True)
                    return

                if hours > 23:
                    await interaction.response.send_message('❌ Часы не могут быть больше 23!', ephemeral=True)
                    return

                if minutes > 59:
                    await interaction.response.send_message('❌ Минуты не могут быть больше 59!', ephemeral=True)
                    return

                subcat['time'] = f"{days}д {hours}ч {minutes}м"
                subcat['message'] = self.message_input.value

            save_data()

            await interaction.response.send_message(
                f"✅ **Подкатегория обновлена!**\n"
                f"📝 {self.name_input.value}",
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message('❌ Ошибка! Введите корректные числовые значения времени.', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message('❌ Произошла ошибка при обновлении!', ephemeral=True)

class FixedTimerSetupModal(discord.ui.Modal, title='Настройка Fixed таймера'):
    def __init__(self, category_key: str, sub_key: str, subcat_data: dict):
        super().__init__()
        self.category_key = category_key
        self.sub_key = sub_key
        self.subcat_data = subcat_data

    days_input = discord.ui.TextInput(
        label='Дни',
        placeholder='Введите количество дней',
        default='0',
        required=True,
        max_length=3
    )

    hours_input = discord.ui.TextInput(
        label='Часы',
        placeholder='Введите количество часов (0-23)',
        default='0',
        required=True,
        max_length=2
    )

    minutes_input = discord.ui.TextInput(
        label='Минуты',
        placeholder='Введите количество минут (0-59)',
        default='0',
        required=True,
        max_length=2
    )

    message_input = discord.ui.TextInput(
        label='Сообщение напоминания',
        placeholder='Введите текст напоминания',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.days_input.value)
            hours = int(self.hours_input.value)
            minutes = int(self.minutes_input.value)
            message = self.message_input.value

            if days < 0 or hours < 0 or minutes < 0:
                await interaction.response.send_message('❌ Время не может быть отрицательным!', ephemeral=True)
                return

            if hours > 23:
                await interaction.response.send_message('❌ Часы не могут быть больше 23!', ephemeral=True)
                return

            if minutes > 59:
                await interaction.response.send_message('❌ Минуты не могут быть больше 59!', ephemeral=True)
                return

            self.subcat_data['time'] = f"{days}д {hours}ч {minutes}м"
            self.subcat_data['message'] = message

            category = categories_data[self.category_key]
            category['subcategories'][self.sub_key] = self.subcat_data
            save_data()

            await interaction.response.send_message(
                f"✅ **Fixed-таймер настроен!**\n"
                f"📝 {self.subcat_data['name']}\n"
                f"⏰ Время: {days}д {hours}ч {minutes}м\n"
                f"💬 Сообщение: {message}",
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message('❌ Ошибка! Введите корректные числовые значения.', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message('❌ Произошла ошибка при настройке таймера!', ephemeral=True)

# ============================================================================
# ФОРМЫ ДЛЯ ВВОДА ДАННЫХ
# ============================================================================

class CustomTimerModal(discord.ui.Modal, title='Настраиваемый таймер'):
    def __init__(self, category_key: str, sub_key: str):
        super().__init__()
        self.category_key = category_key
        self.sub_key = sub_key

    days_input = discord.ui.TextInput(
        label='Дни',
        placeholder='Введите количество дней (0 если не нужно)',
        default='0',
        required=True,
        max_length=3
    )

    hours_input = discord.ui.TextInput(
        label='Часы',
        placeholder='Введите количество часов (0-23)',
        default='0',
        required=True,
        max_length=2
    )

    minutes_input = discord.ui.TextInput(
        label='Минуты',
        placeholder='Введите количество минут (0-59)',
        default='0',
        required=True,
        max_length=2
    )

    message_input = discord.ui.TextInput(
        label='Сообщение напоминания',
        placeholder='Введите текст напоминания',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.days_input.value)
            hours = int(self.hours_input.value)
            minutes = int(self.minutes_input.value)
            message = self.message_input.value

            if days < 0 or hours < 0 or minutes < 0:
                await interaction.response.send_message('❌ Время не может быть отрицательным!', ephemeral=True)
                return

            if hours > 23:
                await interaction.response.send_message('❌ Часы не могут быть больше 23!', ephemeral=True)
                return

            if minutes > 59:
                await interaction.response.send_message('❌ Минуты не могут быть больше 59!', ephemeral=True)
                return

            total_seconds = calculate_seconds(days, hours, minutes)

            if total_seconds <= 0:
                await interaction.response.send_message('❌ Время не может быть нулевым!', ephemeral=True)
                return

            end_time = datetime.now() + timedelta(seconds=total_seconds)

            category = categories_data[self.category_key]
            subcategory = category['subcategories'][self.sub_key]

            reminder_id = f"{interaction.user.id}_{datetime.now().timestamp()}"
            reminders[reminder_id] = {
                'message': message,
                'end_time': end_time.isoformat(),
                'user_id': interaction.user.id,
                'category': f"{category['name']} - {subcategory['name']}"
            }

            save_data()

            time_str = format_time(total_seconds)

            await interaction.response.send_message(
                f"✅ **Настраиваемый таймер установлен!**\n"
                f"📁 **Категория:** {category['name']} - {subcategory['name']}\n"
                f"⏰ **Через:** {time_str} ({days}д {hours}ч {minutes}м)\n"
                f"📝 **Сообщение:** {message}\n"
                f"🕐 **Сработает:** {end_time.strftime('%d.%m.%Y в %H:%M:%S')}",
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message('❌ Ошибка! Введите корректные числовые значения.', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message('❌ Произошла ошибка при установке таймера!', ephemeral=True)

# ============================================================================
# КОМАНДЫ БОТА
# ============================================================================

@bot.event
async def on_ready():
    print('═' * 50)
    print(f'✅ Бот {bot.user.name if bot.user else "Discord Bot"} запущен!')
    if bot.user:
        print(f'🆔 ID: {bot.user.id}')
    print(f'🌐 Серверов: {len(bot.guilds)}')
    print('═' * 50)

    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="/старт - Умные напоминания"
    )
    await bot.change_presence(activity=activity)

    load_data()
    init_default_categories()
    check_reminders.start()
    self_ping.start()

@bot.command()
async def старт(ctx):
    embed = discord.Embed(
        title='🤖 Умная система напоминаний',
        description=(
            '**Добро пожаловать в систему умных напоминаний!**\n\n'
            '🎯 **Возможности бота:**\n'
            '• ⏰ Установка таймеров и напоминаний\n'
            '• 🌾 Напоминания для фарма ресурсов\n'
            '• 🏁 Автоматические задания клубов\n'
            '• ⚙️ Гибкая настройка категорий (для админов)\n\n'
            '**📋 Основные команды:**\n'
            '`/старт` - открыть главное меню\n'
            '`/моинапоминания` - показать активные напоминания\n\n'
            '💡 **Совет:** Меню автоматически закроется через 3 минуты неактивности'
        ),
        color=0x0099ff
    )

    embed.add_field(name='⏰ Таймер', value='Умные таймеры для повседневных задач', inline=True)
    embed.add_field(name='🌾 Фарм', value='Автоматические напоминания для фарма', inline=True)
    embed.add_field(name='🏁 Задания клуба', value='Клубные задания и мероприятия', inline=True)

    embed.set_footer(text='Выберите категорию ниже • Меню закроется через 3 минуты')

    message = await ctx.send(embed=embed, view=StartMenu())

    async def delete_message():
        await asyncio.sleep(180)
        try:
            await message.delete()
        except:
            pass

    asyncio.create_task(delete_message())

@bot.command()
async def моинапоминания(ctx):
    user_reminders = {k: v for k, v in reminders.items() 
                     if v['user_id'] == ctx.author.id}

    if not user_reminders:
        await ctx.send('⏰ У вас нет активных напоминаний!', ephemeral=True)
        return

    embed = discord.Embed(title='⏰ Ваши напоминания', color=0xffa500)

    for reminder_id, reminder_data in user_reminders.items():
        end_time = datetime.fromisoformat(reminder_data['end_time'])
        time_left = end_time - datetime.now()

        if time_left.total_seconds() > 0:
            time_str = format_time(time_left.total_seconds())

            embed.add_field(
                name=f"📁 {reminder_data['category']}",
                value=f'⏰ Осталось: {time_str}\n📝 {reminder_data["message"]}',
                inline=False
            )

    await ctx.send(embed=embed, ephemeral=True)

@bot.command()
async def помощь(ctx):
    embed = discord.Embed(
        title='📖 Помощь по боту напоминаний',
        description=(
            '**🤖 О боте:**\n'
            'Умная система напоминаний для Discord с гибкими настройками и удобным интерфейсом.\n\n'

            '**🎯 Основные команды:**\n'
            '`/старт` - Главное меню с категориями\n'
            '`/моинапоминания` - Активные напоминания\n'
            '`/помощь` - Эта справка\n\n'

            '**📁 Категории:**\n'
            '• **⏰ Таймер** - Универсальные таймеры\n'
            '• **🌾 Фарм** - Напоминания для игрового фарма\n'
            '• **🏁 Задания клуба** - Клубные активности\n\n'

            '**⚙️ Для администраторов:**\n'
            'Доступно управление категориями через кнопку "Управление" в главном меню\n\n'

            '**💡 Особенности:**\n'
            '• Автоматическая отправка напоминаний в ЛС\n'
            '• Гибкая настройка времени\n'
            '• Интуитивный интерфейс с кнопками\n'
            '• Автоудаление неактивных меню'
        ),
        color=0x9370DB
    )

    await ctx.send(embed=embed)

# ============================================================================
# ФОНОВАЯ ПРОВЕРКА НАПОМИНАНИЙ
# ============================================================================

@tasks.loop(seconds=10)
async def check_reminders():
    now = datetime.now()
    reminders_to_remove = []

    for reminder_id, reminder_data in reminders.items():
        if 'end_time' in reminder_data:
            end_time = datetime.fromisoformat(reminder_data['end_time'])

            if now >= end_time:
                try:
                    user = await bot.fetch_user(reminder_data['user_id'])
                    await user.send(
                        f"⏰ **НАПОМИНАНИЕ**\n"
                        f"📁 {reminder_data['category']}\n"
                        f"💬 {reminder_data['message']}"
                    )
                    reminders_to_remove.append(reminder_id)
                    print(f"📨 Отправлено напоминание пользователю {user.name}")
                except Exception as e:
                    print(f"❌ Ошибка отправки напоминания: {e}")
                    reminders_to_remove.append(reminder_id)

    for reminder_id in reminders_to_remove:
        del reminders[reminder_id]

    if reminders_to_remove:
        save_data()

# ============================================================================
# ЗАПУСК БОТА
# ============================================================================

keep_alive()
print("🌐 Веб-сервер запущен для поддержания работы на Replit")

token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    print("❌ Ошибка: Токен бота не найден в файле .env!")