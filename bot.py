import asyncio
from datetime import date, timedelta, datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from schedule import RED_WEEK, BLUE_WEEK
from database import (
    init_db,
    add_homework,
    get_homework_by_date,
    get_all_homework,
    get_homework,
    complete_homework,
    delete_homework,
    update_homework_subject,
    update_homework_date,
    update_homework_description,
    add_note,
    get_notes_by_date,
    get_all_notes,
    get_note,
    update_note_text,
    update_note_date,
    delete_note,
)


# ==========================================
# НАСТРОЙКИ
# ==========================================

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


RED_WEEK_START = date(2026, 9, 1)


# ==========================================
# СОЗДАНИЕ БОТА
# ==========================================

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ==========================================
# ДНИ
# ==========================================

DAYS = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]

SHORT_DAYS = [
    "Пн",
    "Вт",
    "Ср",
    "Чт",
    "Пт",
    "Сб",
    "Вс",
]


# ==========================================
# СОСТОЯНИЯ
# ==========================================

class HomeworkForm(StatesGroup):
    subject = State()
    due_date = State()
    description = State()


class HomeworkDateForm(StatesGroup):
    due_date = State()


class EditHomework(StatesGroup):
    subject = State()
    date = State()
    description = State()


class NoteForm(StatesGroup):
    text = State()
    date_choice = State()


class EditNote(StatesGroup):
    text = State()
    date = State()


# ==========================================
# ГЛАВНОЕ МЕНЮ
# ==========================================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📅 Расписание"),
            KeyboardButton(text="📝 Домашние задания"),
        ],
        [
            KeyboardButton(text="📌 Заметки"),
            KeyboardButton(text="📆 Сегодня"),
        ],
    ],
    resize_keyboard=True,
)


# ==========================================
# МЕНЮ ДЗ
# ==========================================

homework_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Добавить ДЗ"),
            KeyboardButton(text="📅 ДЗ на дату"),
        ],
        [
            KeyboardButton(text="📋 Все ДЗ"),
        ],
        [
            KeyboardButton(text="🔙 Главное меню"),
        ],
    ],
    resize_keyboard=True,
)


# ==========================================
# МЕНЮ ЗАМЕТОК
# ==========================================

notes_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Добавить заметку"),
            KeyboardButton(text="📋 Все заметки"),
        ],
        [
            KeyboardButton(text="🔙 Главное меню"),
        ],
    ],
    resize_keyboard=True,
)


# ==========================================
# КНОПКА ОТМЕНЫ
# ==========================================

cancel_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="❌ Отмена"),
        ]
    ],
    resize_keyboard=True,
)


# ==========================================
# ПОЛУЧАЕМ СПИСОК ПРЕДМЕТОВ
# ==========================================

def collect_subjects():
    subjects = []

    for week in (RED_WEEK, BLUE_WEEK):
        for lessons in week.values():
            for _, subject, _ in lessons:
                if subject not in subjects:
                    subjects.append(subject)

    return subjects


SUBJECTS = collect_subjects()


# ==========================================
# КРАСНАЯ / СИНЯЯ НЕДЕЛЯ
# ==========================================

def get_week_type(current_date):
    monday = current_date - timedelta(days=current_date.weekday())

    red_monday = (
        RED_WEEK_START
        - timedelta(days=RED_WEEK_START.weekday())
    )

    weeks_difference = (
        monday - red_monday
    ).days // 7

    if weeks_difference % 2 == 0:
        return "red"

    return "blue"


# ==========================================
# РАСПИСАНИЕ КОНКРЕТНОГО ДНЯ
# ==========================================

def get_day_schedule(current_date):
    week_type = get_week_type(current_date)

    if week_type == "red":
        schedule = RED_WEEK
    else:
        schedule = BLUE_WEEK

    return (
        week_type,
        schedule.get(current_date.weekday(), []),
    )


# ==========================================
# ЭМОДЗИ ТИПА ЗАНЯТИЯ
# ==========================================

def get_lesson_emoji(lesson_type):
    if lesson_type == "Лекция":
        return "🎓"

    if lesson_type == "Практика":
        return "📝"

    if lesson_type == "Лабораторная":
        return "🧪"

    return "📚"


# ==========================================
# НОМЕР ПАРЫ ПО ВРЕМЕНИ НАЧАЛА
# ==========================================

def get_lesson_number(time):
    """Определяет номер пары по времени, а не по позиции в списке."""
    start_time = time.split("–", 1)[0].strip()

    lesson_numbers = {
        "08:30": 1,
        "10:15": 2,
        "12:15": 3,
        "14:00": 4,
        "15:45": 5,
    }

    return lesson_numbers.get(start_time, "?")


# ==========================================
# РАСПИСАНИЕ НА НЕДЕЛЮ
# ==========================================

def format_week_schedule(week_start):
    week_type = get_week_type(week_start)

    if week_type == "red":
        week_name = "🔴 Красная неделя"
    else:
        week_name = "🔵 Синяя неделя"

    week_end = week_start + timedelta(days=6)

    text = (
        f"{week_name}\n"
        f"📅 {week_start:%d.%m}"
        f" — "
        f"{week_end:%d.%m.%Y}\n\n"
    )

    for day_number in range(5):
        current_date = (
            week_start
            + timedelta(days=day_number)
        )

        _, lessons = get_day_schedule(current_date)

        text += "━━━━━━━━━━━━━━━━━━\n"
        text += f"📅 {DAYS[day_number]}\n"

        if not lessons:
            text += "Нет занятий\n\n"
            continue

        for lesson in lessons:
            time, subject, lesson_type = lesson
            number = get_lesson_number(time)

            text += (
                f"\n"
                f"{number}️⃣ {time}\n"
                f"📚 {subject}\n"
                f"{get_lesson_emoji(lesson_type)} "
                f"{lesson_type}\n"
            )

        text += "\n"

    return text + "━━━━━━━━━━━━━━━━━━"


# ==========================================
# КНОПКИ НЕДЕЛИ
# ==========================================

def get_week_keyboard(week_start):
    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    current_week = (
        date.today()
        - timedelta(days=date.today().weekday())
    )

    day_buttons = [
        InlineKeyboardButton(
            text=SHORT_DAYS[i],
            callback_data=(
                f"day:{(
                    week_start
                    + timedelta(days=i)
                ).isoformat()}"
            ),
        )
        for i in range(5)
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            day_buttons,
            [
                InlineKeyboardButton(
                    text="◀️ Предыдущая",
                    callback_data=(
                        f"week:{previous_week.isoformat()}"
                    ),
                ),
                InlineKeyboardButton(
                    text="Следующая ▶️",
                    callback_data=(
                        f"week:{next_week.isoformat()}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📍 Текущая неделя",
                    callback_data=(
                        f"week:{current_week.isoformat()}"
                    ),
                ),
            ],
        ]
    )


# ==========================================
# КНОПКИ ДНЯ
# ==========================================

def get_day_keyboard(current_date):
    previous_day = current_date - timedelta(days=1)
    next_day = current_date + timedelta(days=1)

    week_start = (
        current_date
        - timedelta(days=current_date.weekday())
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ Предыдущий",
                    callback_data=(
                        f"day:{previous_day.isoformat()}"
                    ),
                ),
                InlineKeyboardButton(
                    text="Следующий ▶️",
                    callback_data=(
                        f"day:{next_day.isoformat()}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📅 Вся неделя",
                    callback_data=(
                        f"week:{week_start.isoformat()}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📍 Сегодня",
                    callback_data=(
                        f"day:{date.today().isoformat()}"
                    ),
                ),
            ],
        ]
    )


# ==========================================
# КНОПКИ ПРЕДМЕТОВ
# ==========================================

def subject_keyboard(prefix="hwsub"):
    rows = []
    row = []

    for index, subject in enumerate(SUBJECTS):
        row.append(
            InlineKeyboardButton(
                text=subject,
                callback_data=f"{prefix}:{index}",
            )
        )

        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="back_hw",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ==========================================
# ИЩЕМ БЛИЖАЙШИЕ ДАТЫ ПРЕДМЕТА
# ==========================================

def next_subject_dates(
    subject,
    start=None,
    count=6,
):
    current = start or date.today()
    result = []

    for _ in range(70):
        if current.weekday() < 5:
            _, lessons = get_day_schedule(current)

            if any(
                lesson[1] == subject
                for lesson in lessons
            ):
                result.append(current)

                if len(result) == count:
                    break

        current += timedelta(days=1)

    return result


# ==========================================
# КНОПКИ ДАТ ПРЕДМЕТА
# ==========================================

def subject_date_keyboard(
    subject,
    prefix="hwdate",
):
    dates = next_subject_dates(subject)

    rows = []
    row = []

    for selected_date in dates:
        row.append(
            InlineKeyboardButton(
                text=(
                    f"{SHORT_DAYS[selected_date.weekday()]}"
                    f" {selected_date:%d.%m}"
                ),
                callback_data=(
                    f"{prefix}:{selected_date.isoformat()}"
                ),
            )
        )

        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                text="📅 Другая дата",
                callback_data="manual_hw_date",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="back_hw",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ==========================================
# КНОПКИ ДЕЙСТВИЙ С ДЗ
# ==========================================

def homework_actions(
    homework_id,
    completed=False,
):
    buttons = []

    if not completed:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Выполнено",
                    callback_data=(
                        f"done:{homework_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=(
                    f"edithw:{homework_id}"
                ),
            ),
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=(
                    f"delhw:{homework_id}"
                ),
            ),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# ==========================================
# МЕНЮ РЕДАКТИРОВАНИЯ ДЗ
# ==========================================

def edit_homework_menu(homework_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Предмет",
                    callback_data=(
                        f"edithwfield:"
                        f"{homework_id}:subject"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Дата",
                    callback_data=(
                        f"edithwfield:"
                        f"{homework_id}:date"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Текст",
                    callback_data=(
                        f"edithwfield:"
                        f"{homework_id}:description"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="back_hw",
                )
            ],
        ]
    )


# ==========================================
# КНОПКИ ЗАМЕТКИ
# ==========================================

def note_actions(note_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=(
                        f"editnote:{note_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=(
                        f"delnote:{note_id}"
                    ),
                ),
            ]
        ]
    )


# ==========================================
# МЕНЮ РЕДАКТИРОВАНИЯ ЗАМЕТКИ
# ==========================================

def edit_note_menu(note_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📌 Текст",
                    callback_data=(
                        f"editnotefield:"
                        f"{note_id}:text"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Дата",
                    callback_data=(
                        f"editnotefield:"
                        f"{note_id}:date"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="back_notes",
                )
            ],
        ]
    )


# ==========================================
# ПОЛНЫЙ ЭКРАН ДНЯ
# ==========================================

async def full_day_text(
    user_id,
    current_date,
):
    week_type, lessons = get_day_schedule(
        current_date
    )

    week_name = (
        "🔴 Красная неделя"
        if week_type == "red"
        else "🔵 Синяя неделя"
    )

    text = (
        f"{week_name}\n"
        f"📅 {DAYS[current_date.weekday()]}, "
        f"{current_date:%d.%m.%Y}\n\n"
    )

    text += "📚 РАСПИСАНИЕ\n"

    if lessons:
        for lesson in lessons:
            time, subject, lesson_type = lesson
            number = get_lesson_number(time)

            text += (
                f"\n{number}️⃣ {time}\n"
                f"📖 {subject}\n"
                f"{get_lesson_emoji(lesson_type)} "
                f"{lesson_type}\n"
            )
    else:
        text += "\nСегодня занятий нет 🎉\n"

    homework = await get_homework_by_date(
        user_id,
        current_date.isoformat(),
    )

    text += "\n📝 ДОМАШНИЕ ЗАДАНИЯ\n"

    if homework:
        for _, subject, description, completed in homework:
            status = "✅" if completed else "❌"

            text += (
                f"\n{status} {subject}\n"
                f"└ {description}\n"
            )
    else:
        text += "\nНет заданий 🎉\n"

    notes = await get_notes_by_date(
        user_id,
        current_date.isoformat(),
    )

    text += "\n📌 ЗАМЕТКИ\n"

    if notes:
        for _, note in notes:
            text += f"\n• {note}\n"
    else:
        text += "\nНет заметок.\n"

    return text


# ==========================================
# /START
# ==========================================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! 👋\n\n"
        "Я твой учебный помощник 📚\n\n"
        "Выбери нужный раздел:",
        reply_markup=main_menu,
    )


# ==========================================
# ГЛАВНОЕ МЕНЮ
# ==========================================

@dp.message(F.text == "🔙 Главное меню")
async def back_main(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await message.answer(
        "📚 Главное меню",
        reply_markup=main_menu,
    )


# ==========================================
# ОТМЕНА
# ==========================================

@dp.message(F.text == "❌ Отмена")
async def cancel_message(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await message.answer(
        "❌ Действие отменено.",
        reply_markup=main_menu,
    )


@dp.callback_query(F.data == "back_hw")
async def back_hw(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await callback.message.answer(
        "📝 Домашние задания",
        reply_markup=homework_menu,
    )

    await callback.answer()


@dp.callback_query(F.data == "back_notes")
async def back_notes(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await callback.message.answer(
        "📌 Заметки",
        reply_markup=notes_menu,
    )

    await callback.answer()


# ==========================================
# 📅 РАСПИСАНИЕ
# ==========================================

@dp.message(F.text == "📅 Расписание")
async def schedule(message: Message):
    week_start = (
        date.today()
        - timedelta(days=date.today().weekday())
    )

    await message.answer(
        format_week_schedule(week_start),
        reply_markup=get_week_keyboard(
            week_start
        ),
    )


# ==========================================
# 📆 СЕГОДНЯ
# ==========================================

@dp.message(F.text == "📆 Сегодня")
async def today(message: Message):
    current_date = date.today()

    await message.answer(
        await full_day_text(
            message.from_user.id,
            current_date,
        ),
        reply_markup=get_day_keyboard(
            current_date
        ),
    )


# ==========================================
# ПЕРЕКЛЮЧЕНИЕ НЕДЕЛИ
# ==========================================

@dp.callback_query(
    F.data.startswith("week:")
)
async def change_week(
    callback: CallbackQuery,
):
    week_start = date.fromisoformat(
        callback.data.split(":", 1)[1]
    )

    await callback.message.edit_text(
        format_week_schedule(week_start),
        reply_markup=get_week_keyboard(
            week_start
        ),
    )

    await callback.answer()


# ==========================================
# ОТКРЫТИЕ ДНЯ
# ==========================================

@dp.callback_query(
    F.data.startswith("day:")
)
async def show_day(
    callback: CallbackQuery,
):
    current_date = date.fromisoformat(
        callback.data.split(":", 1)[1]
    )

    await callback.message.edit_text(
        await full_day_text(
            callback.from_user.id,
            current_date,
        ),
        reply_markup=get_day_keyboard(
            current_date
        ),
    )

    await callback.answer()


# ==========================================
# 📝 МЕНЮ ДЗ
# ==========================================

@dp.message(
    F.text == "📝 Домашние задания"
)
async def homework_menu_handler(
    message: Message,
):
    await message.answer(
        "📝 Домашние задания\n\n"
        "Выбери действие:",
        reply_markup=homework_menu,
    )


# ==========================================
# ➕ ДОБАВЛЕНИЕ ДЗ
# ==========================================

@dp.message(F.text == "➕ Добавить ДЗ")
async def add_hw_start(
    message: Message,
    state: FSMContext,
):
    await state.set_state(
        HomeworkForm.subject
    )

    await message.answer(
        "📚 Выбери предмет:",
        reply_markup=subject_keyboard(),
    )


@dp.callback_query(
    HomeworkForm.subject,
    F.data.startswith("hwsub:")
)
async def choose_subject(
    callback: CallbackQuery,
    state: FSMContext,
):
    index = int(
        callback.data.split(":", 1)[1]
    )

    subject = SUBJECTS[index]

    await state.update_data(
        subject=subject
    )

    await state.set_state(
        HomeworkForm.due_date
    )

    await callback.message.edit_text(
        f"📚 Предмет: {subject}\n\n"
        "📅 Выбери ближайшую дату:",
        reply_markup=subject_date_keyboard(
            subject
        ),
    )

    await callback.answer()


# ==========================================
# ДАТА ДЗ
# ==========================================

@dp.callback_query(
    HomeworkForm.due_date,
    F.data.startswith("hwdate:")
)
async def choose_hw_date(
    callback: CallbackQuery,
    state: FSMContext,
):
    selected_date = date.fromisoformat(
        callback.data.split(":", 1)[1]
    )

    await state.update_data(
        due_date=selected_date.isoformat()
    )

    await state.set_state(
        HomeworkForm.description
    )

    await callback.message.answer(
        f"📅 Дата: "
        f"{SHORT_DAYS[selected_date.weekday()]} "
        f"{selected_date:%d.%m.%Y}\n\n"
        "📝 Напиши, что задано:",
        reply_markup=cancel_menu,
    )

    await callback.answer()


@dp.callback_query(
    HomeworkForm.due_date,
    F.data == "manual_hw_date"
)
async def manual_hw_date(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.message.answer(
        "📅 Введи дату вручную:\n"
        "ДД.ММ.ГГГГ",
        reply_markup=cancel_menu,
    )

    await callback.answer()


@dp.message(
    HomeworkForm.due_date
)
async def manual_hw_date_text(
    message: Message,
    state: FSMContext,
):
    try:
        selected_date = datetime.strptime(
            message.text.strip(),
            "%d.%m.%Y",
        ).date()

    except ValueError:
        await message.answer(
            "❌ Неверная дата.\n"
            "Используй ДД.ММ.ГГГГ."
        )
        return

    await state.update_data(
        due_date=selected_date.isoformat()
    )

    await state.set_state(
        HomeworkForm.description
    )

    await message.answer(
        f"📅 Дата: "
        f"{SHORT_DAYS[selected_date.weekday()]} "
        f"{selected_date:%d.%m.%Y}\n\n"
        "📝 Напиши, что задано:",
        reply_markup=cancel_menu,
    )


# ==========================================
# СОХРАНЕНИЕ ДЗ
# ==========================================

@dp.message(
    HomeworkForm.description
)
async def save_hw(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    await add_homework(
        message.from_user.id,
        data["subject"],
        data["due_date"],
        message.text.strip(),
    )

    selected_date = date.fromisoformat(
        data["due_date"]
    )

    await state.clear()

    await message.answer(
        "✅ ДЗ сохранено!\n\n"
        f"📚 {data['subject']}\n"
        f"📅 "
        f"{SHORT_DAYS[selected_date.weekday()]} "
        f"{selected_date:%d.%m.%Y}\n"
        f"📝 {message.text.strip()}",
        reply_markup=homework_menu,
    )


# ==========================================
# 📋 ВСЕ ДЗ
# ==========================================

@dp.message(F.text == "📋 Все ДЗ")
async def all_hw(message: Message):
    homework = await get_all_homework(
        message.from_user.id
    )

    if not homework:
        await message.answer(
            "📋 У тебя пока нет ДЗ.",
            reply_markup=homework_menu,
        )
        return

    await message.answer(
        "📋 Домашние задания:",
        reply_markup=homework_menu,
    )

    for (
        homework_id,
        subject,
        due_date,
        description,
        completed,
    ) in homework:
        selected_date = date.fromisoformat(
            due_date
        )

        status = (
            "✅"
            if completed
            else "❌"
        )

        await message.answer(
            f"{status} 📅 "
            f"{SHORT_DAYS[selected_date.weekday()]} "
            f"{selected_date:%d.%m.%Y}\n"
            f"📚 {subject}\n"
            f"└ {description}",
            reply_markup=homework_actions(
                homework_id,
                completed
            ),
        )


# ==========================================
# 📅 ДЗ НА ДАТУ
# ==========================================

@dp.message(F.text == "📅 ДЗ на дату")
async def hw_on_date_start(
    message: Message,
    state: FSMContext,
):
    await state.set_state(
        HomeworkDateForm.due_date
    )

    await message.answer(
        "📅 Введи дату:\n"
        "ДД.ММ.ГГГГ",
        reply_markup=cancel_menu,
    )


@dp.message(
    HomeworkDateForm.due_date
)
async def view_hw_date(
    message: Message,
    state: FSMContext,
):
    try:
        selected_date = datetime.strptime(
            message.text.strip(),
            "%d.%m.%Y",
        ).date()

    except ValueError:
        await message.answer(
            "❌ Неверная дата.\n"
            "Используй ДД.ММ.ГГГГ."
        )
        return

    await state.clear()

    homework = await get_homework_by_date(
        message.from_user.id,
        selected_date.isoformat(),
    )

    await message.answer(
        f"📅 ДЗ на "
        f"{SHORT_DAYS[selected_date.weekday()]} "
        f"{selected_date:%d.%m.%Y}"
    )

    if not homework:
        await message.answer(
            "Домашних заданий нет 🎉",
            reply_markup=homework_menu,
        )
        return

    for (
        homework_id,
        subject,
        description,
        completed,
    ) in homework:
        status = (
            "✅"
            if completed
            else "❌"
        )

        await message.answer(
            f"{status} 📚 {subject}\n"
            f"└ {description}",
            reply_markup=homework_actions(
                homework_id,
                completed
            ),
        )

    await message.answer(
        "Выбери действие:",
        reply_markup=homework_menu,
    )


# ==========================================
# ✏️ РЕДАКТИРОВАНИЕ ДЗ
# ==========================================

@dp.callback_query(
    F.data.startswith("edithw:")
)
async def edit_hw_start(
    callback: CallbackQuery,
):
    homework_id = int(
        callback.data.split(":", 1)[1]
    )

    homework = await get_homework(
        homework_id,
        callback.from_user.id,
    )

    if not homework:
        await callback.answer(
            "ДЗ не найдено.",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "✏️ Что изменить?",
        reply_markup=edit_homework_menu(
            homework_id
        ),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("edithwfield:")
)
async def edit_hw_field(
    callback: CallbackQuery,
    state: FSMContext,
):
    _, homework_id_text, field = (
        callback.data.split(":", 2)
    )

    homework_id = int(
        homework_id_text
    )

    await state.update_data(
        homework_id=homework_id
    )

    if field == "subject":

        await state.set_state(
            EditHomework.subject
        )

        await callback.message.answer(
            "📚 Выбери новый предмет:",
            reply_markup=subject_keyboard(
                "edsub"
            ),
        )

    elif field == "date":

        homework = await get_homework(
            homework_id,
            callback.from_user.id,
        )

        if not homework:
            await callback.answer(
                "ДЗ не найдено.",
                show_alert=True,
            )
            return

        await state.set_state(
            EditHomework.date
        )

        await callback.message.answer(
            f"📅 Выбери новую дату для "
            f"«{homework[1]}»:",
            reply_markup=subject_date_keyboard(
                homework[1],
                "eddate",
            ),
        )

    elif field == "description":

        await state.set_state(
            EditHomework.description
        )

        await callback.message.answer(
            "📝 Напиши новый текст задания:",
            reply_markup=cancel_menu,
        )

    await callback.answer()


@dp.callback_query(
    EditHomework.subject,
    F.data.startswith("edsub:")
)
async def edit_hw_subject(
    callback: CallbackQuery,
    state: FSMContext,
):
    index = int(
        callback.data.split(":", 1)[1]
    )

    subject = SUBJECTS[index]

    data = await state.get_data()

    await update_homework_subject(
        data["homework_id"],
        callback.from_user.id,
        subject,
    )

    await state.clear()

    await callback.message.answer(
        f"✅ Предмет изменён на "
        f"«{subject}».",
        reply_markup=homework_menu,
    )

    await callback.answer()


@dp.callback_query(
    EditHomework.date,
    F.data.startswith("eddate:")
)
async def edit_hw_date_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    selected_date = date.fromisoformat(
        callback.data.split(":", 1)[1]
    )

    data = await state.get_data()

    await update_homework_date(
        data["homework_id"],
        callback.from_user.id,
        selected_date.isoformat(),
    )

    await state.clear()

    await callback.message.answer(
        "✅ Дата изменена на "
        f"{SHORT_DAYS[selected_date.weekday()]} "
        f"{selected_date:%d.%m.%Y}.",
        reply_markup=homework_menu,
    )

    await callback.answer()


@dp.callback_query(
    EditHomework.date,
    F.data == "manual_hw_date"
)
async def edit_hw_manual_date(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.message.answer(
        "📅 Введи новую дату:\n"
        "ДД.ММ.ГГГГ",
        reply_markup=cancel_menu,
    )

    await callback.answer()


@dp.message(EditHomework.date)
async def edit_hw_date_text(
    message: Message,
    state: FSMContext,
):
    try:
        selected_date = datetime.strptime(
            message.text.strip(),
            "%d.%m.%Y",
        ).date()

    except ValueError:
        await message.answer(
            "❌ Неверная дата.\n"
            "Используй ДД.ММ.ГГГГ."
        )
        return

    data = await state.get_data()

    await update_homework_date(
        data["homework_id"],
        message.from_user.id,
        selected_date.isoformat(),
    )

    await state.clear()

    await message.answer(
        "✅ Дата изменена на "
        f"{SHORT_DAYS[selected_date.weekday()]} "
        f"{selected_date:%d.%m.%Y}.",
        reply_markup=homework_menu,
    )


@dp.message(
    EditHomework.description
)
async def edit_hw_description(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    await update_homework_description(
        data["homework_id"],
        message.from_user.id,
        message.text.strip(),
    )

    await state.clear()

    await message.answer(
        "✅ Текст задания изменён.",
        reply_markup=homework_menu,
    )


# ==========================================
# ✅ ВЫПОЛНИТЬ ДЗ
# ==========================================

@dp.callback_query(
    F.data.startswith("done:")
)
async def done_hw(
    callback: CallbackQuery,
):
    homework_id = int(
        callback.data.split(":", 1)[1]
    )

    await complete_homework(
        homework_id,
        callback.from_user.id,
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.answer(
        "✅ ДЗ выполнено!"
    )


# ==========================================
# 🗑 УДАЛИТЬ ДЗ
# ==========================================

@dp.callback_query(
    F.data.startswith("delhw:")
)
async def del_hw(
    callback: CallbackQuery,
):
    homework_id = int(
        callback.data.split(":", 1)[1]
    )

    await delete_homework(
        homework_id,
        callback.from_user.id,
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.answer(
        "🗑 ДЗ удалено"
    )


# ==========================================
# 📌 МЕНЮ ЗАМЕТОК
# ==========================================

@dp.message(F.text == "📌 Заметки")
async def notes_menu_handler(
    message: Message,
):
    await message.answer(
        "📌 Заметки\n\n"
        "Выбери действие:",
        reply_markup=notes_menu,
    )


# ==========================================
# ➕ ДОБАВИТЬ ЗАМЕТКУ
# ==========================================

@dp.message(F.text == "➕ Добавить заметку")
async def add_note_start(
    message: Message,
    state: FSMContext,
):
    await state.set_state(
        NoteForm.text
    )

    await message.answer(
        "📌 Напиши заметку:",
        reply_markup=cancel_menu,
    )


@dp.message(NoteForm.text)
async def note_text(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        text=message.text.strip()
    )

    await state.set_state(
        NoteForm.date_choice
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📌 Без даты",
                    callback_data="notedate:none",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 На сегодня",
                    callback_data=(
                        f"notedate:"
                        f"{date.today().isoformat()}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📆 Выбрать дату",
                    callback_data="notedate:manual",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="back_notes",
                )
            ],
        ]
    )

    await message.answer(
        "📅 Привязать заметку к дате?",
        reply_markup=keyboard,
    )


@dp.callback_query(
    NoteForm.date_choice,
    F.data.startswith("notedate:")
)
async def note_date_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    value = callback.data.split(
        ":",
        1
    )[1]

    if value == "manual":

        await callback.message.answer(
            "📅 Введи дату:\n"
            "ДД.ММ.ГГГГ",
            reply_markup=cancel_menu,
        )

        await callback.answer()
        return

    data = await state.get_data()

    note_date = (
        None
        if value == "none"
        else value
    )

    await add_note(
        callback.from_user.id,
        data["text"],
        note_date,
    )

    await state.clear()

    await callback.message.answer(
        "✅ Заметка сохранена.",
        reply_markup=notes_menu,
    )

    await callback.answer()


@dp.message(
    NoteForm.date_choice
)
async def note_date_text(
    message: Message,
    state: FSMContext,
):
    try:
        selected_date = datetime.strptime(
            message.text.strip(),
            "%d.%m.%Y",
        ).date()

    except ValueError:
        await message.answer(
            "❌ Неверная дата.\n"
            "Используй ДД.ММ.ГГГГ."
        )
        return

    data = await state.get_data()

    await add_note(
        message.from_user.id,
        data["text"],
        selected_date.isoformat(),
    )

    await state.clear()

    await message.answer(
        "✅ Заметка сохранена.",
        reply_markup=notes_menu,
    )


# ==========================================
# 📋 ВСЕ ЗАМЕТКИ
# ==========================================

@dp.message(F.text == "📋 Все заметки")
async def all_notes(
    message: Message,
):
    notes = await get_all_notes(
        message.from_user.id
    )

    if not notes:
        await message.answer(
            "📋 У тебя пока нет заметок.",
            reply_markup=notes_menu,
        )
        return

    await message.answer(
        "📋 Все заметки:",
        reply_markup=notes_menu,
    )

    for note_id, text_value, note_date in notes:

        if note_date:
            title = (
                f"📅 "
                f"{date.fromisoformat(note_date):%d.%m.%Y}"
            )
        else:
            title = "📌 Без даты"

        await message.answer(
            f"{title}\n\n"
            f"{text_value}",
            reply_markup=note_actions(
                note_id
            ),
        )


# ==========================================
# ✏️ РЕДАКТИРОВАНИЕ ЗАМЕТКИ
# ==========================================

@dp.callback_query(
    F.data.startswith("editnote:")
)
async def edit_note_start(
    callback: CallbackQuery,
):
    note_id = int(
        callback.data.split(":", 1)[1]
    )

    note = await get_note(
        note_id,
        callback.from_user.id,
    )

    if not note:
        await callback.answer(
            "Заметка не найдена.",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "✏️ Что изменить?",
        reply_markup=edit_note_menu(
            note_id
        ),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("editnotefield:")
)
async def edit_note_field(
    callback: CallbackQuery,
    state: FSMContext,
):
    _, note_id_text, field = (
        callback.data.split(":", 2)
    )

    note_id = int(note_id_text)

    await state.update_data(
        note_id=note_id
    )

    if field == "text":

        await state.set_state(
            EditNote.text
        )

        await callback.message.answer(
            "📌 Напиши новый текст заметки:",
            reply_markup=cancel_menu,
        )

    elif field == "date":

        await state.set_state(
            EditNote.date
        )

        await callback.message.answer(
            "📅 Введи новую дату:\n"
            "ДД.ММ.ГГГГ\n\n"
            "Чтобы убрать дату, напиши:\n"
            "нет",
            reply_markup=cancel_menu,
        )

    await callback.answer()


@dp.message(EditNote.text)
async def edit_note_text(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    await update_note_text(
        data["note_id"],
        message.from_user.id,
        message.text.strip(),
    )

    await state.clear()

    await message.answer(
        "✅ Текст заметки изменён.",
        reply_markup=notes_menu,
    )


@dp.message(EditNote.date)
async def edit_note_date(
    message: Message,
    state: FSMContext,
):
    value = message.text.strip().lower()

    if value == "нет":
        selected_date = None

    else:
        try:
            selected_date = datetime.strptime(
                value,
                "%d.%m.%Y",
            ).date().isoformat()

        except ValueError:
            await message.answer(
                "❌ Неверная дата.\n"
                "Используй ДД.ММ.ГГГГ "
                "или напиши «нет»."
            )
            return

    data = await state.get_data()

    await update_note_date(
        data["note_id"],
        message.from_user.id,
        selected_date,
    )

    await state.clear()

    await message.answer(
        "✅ Дата заметки изменена.",
        reply_markup=notes_menu,
    )


# ==========================================
# 🗑 УДАЛИТЬ ЗАМЕТКУ
# ==========================================

@dp.callback_query(
    F.data.startswith("delnote:")
)
async def del_note(
    callback: CallbackQuery,
):
    note_id = int(
        callback.data.split(":", 1)[1]
    )

    await delete_note(
        note_id,
        callback.from_user.id,
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.answer(
        "🗑 Заметка удалена"
    )


# ==========================================
# ЗАПУСК
# ==========================================

async def main():
    await init_db()

    print("Бот запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())