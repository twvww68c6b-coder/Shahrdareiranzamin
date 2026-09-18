import os
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from sqlalchemy import (
    String, Integer, Float, DateTime, Text, select, func, inspect
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///crm.db")

# ---------------------------------------------------------
# ACCESS CONTROL
# ---------------------------------------------------------
# Railway Variables:
#
# ADMIN_TELEGRAM_ID = telegram id of Hooman
#
# ALLOWED_TELEGRAM_IDS =
# 123456789,987654321,555555555
#
# Admin is automatically allowed.
# ---------------------------------------------------------

ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "").strip()

ALLOWED_TELEGRAM_IDS = {
    x.strip()
    for x in os.getenv("ALLOWED_TELEGRAM_IDS", "").split(",")
    if x.strip()
}


# =========================================================
# DATABASE URL
# =========================================================

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+asyncpg://",
        1
    )

elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1
    )

elif DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace(
        "sqlite:///",
        "sqlite+aiosqlite:///",
        1
    )


engine = create_async_engine(
    DATABASE_URL,
    echo=False
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False
)


# =========================================================
# DATABASE MODELS
# =========================================================

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    telegram_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    role: Mapped[str] = mapped_column(
        String(50),
        default="مشاور"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True
    )

    area: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    address: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    sqm: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    price: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    property_type: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    bedrooms: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    floors: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    unit_floor: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    units_per_floor: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    elevator: Mapped[str] = mapped_column(
        String(50),
        default=""
    )

    parking: Mapped[str] = mapped_column(
        String(50),
        default=""
    )

    parking_type: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    storage: Mapped[str] = mapped_column(
        String(50),
        default=""
    )

    tenant: Mapped[str] = mapped_column(
        String(50),
        default=""
    )

    deposit: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    rent: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    vacancy_date: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    document_type: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    owner_name: Mapped[str] = mapped_column(
        String(150),
        default=""
    )

    owner_phone: Mapped[str] = mapped_column(
        String(50),
        default=""
    )

    description: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    status: Mapped[str] = mapped_column(
        String(100),
        default="فعال"
    )

    transaction_value: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    created_by: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(150)
    )

    phone: Mapped[str] = mapped_column(
        String(50),
        default=""
    )

    area: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    min_sqm: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    max_sqm: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    min_budget: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    max_budget: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    property_type: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    # Kept for old database compatibility.
    # New customer registration does NOT ask for bedrooms.
    bedrooms: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    description: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="فعال"
    )

    created_by: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    property_id: Mapped[int] = mapped_column(
        Integer
    )

    client_id: Mapped[int] = mapped_column(
        Integer
    )

    agent_id: Mapped[int] = mapped_column(
        Integer
    )

    visited_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    interest: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    price_reaction: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    property_reaction: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    objection: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    next_action: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    followup_date: Mapped[str] = mapped_column(
        String(100),
        default=""
    )

    note: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    outcome: Mapped[str] = mapped_column(
        String(100),
        default=""
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer
    )

    property_id: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    client_id: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    activity_type: Mapped[str] = mapped_column(
        String(150)
    )

    note: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


# =========================================================
# CONSTANTS
# =========================================================

AREAS = [
    "خانی‌آباد نو جنوبی",
    "خانی‌آباد نو شمالی",
    "شهرک شریعتی",
    "شهرک بستان شمالی",
    "شهرک بستان جنوبی",
]

PROPERTY_TYPES = [
    "آپارتمان",
    "مجتمع",
    "کلنگی",
    "مستغلات",
    "ویلایی",
    "تجاری",
    "زمین",
    "اداری",
    "سایر",
]

STATUSES = [
    "🟢 فعال",
    "🟡 در مذاکره",
    "🔵 معامله شد - توسط ما",
    "🟣 معامله شد - توسط دیگری",
    "🔴 منصرف شد",
    "⚫ غیرفعال",
]

CLIENT_STATUSES = [
    "فعال",
    "خرید کرده",
    "منصرف شده",
]

INTERESTS = [
    "خیلی زیاد",
    "زیاد",
    "متوسط",
    "کم",
    "رد",
]

PRICE_REACTIONS = [
    "مناسب",
    "کمی بالا",
    "بالا",
    "خیلی بالا",
    "نظر نداد",
]

PROPERTY_REACTIONS = [
    "پسندید",
    "متوسط",
    "نپسندید",
    "نامشخص",
]

NEXT_ACTIONS = [
    "پیگیری",
    "بازدید مجدد",
    "مذاکره",
    "قرارداد",
    "رد شد",
    "فعلاً صبر",
]


# =========================================================
# FSM
# =========================================================

class PropertyForm(StatesGroup):
    code = State()
    area = State()
    address = State()
    sqm = State()
    price = State()
    property_type = State()
    bedrooms = State()
    floors = State()
    unit_floor = State()
    units_per_floor = State()
    elevator = State()
    parking = State()
    parking_type = State()
    storage = State()
    tenant = State()
    deposit = State()
    rent = State()
    vacancy_date = State()
    document_type = State()
    owner_name = State()
    owner_phone = State()
    description = State()
    confirmation = State()


class ClientForm(StatesGroup):
    name = State()
    phone = State()
    area = State()
    min_sqm = State()
    max_sqm = State()
    min_budget = State()
    max_budget = State()
    property_type = State()
    description = State()


class VisitForm(StatesGroup):
    client_id = State()
    property_id = State()
    interest = State()
    price_reaction = State()
    property_reaction = State()
    objection = State()
    next_action = State()
    followup_date = State()
    note = State()


class EditForm(StatesGroup):
    property_id = State()
    field = State()
    value = State()


class EventForm(StatesGroup):
    property_id = State()
    event_type = State()
    note = State()


class StatusForm(StatesGroup):
    property_id = State()
    status = State()
    transaction_value = State()


class ClientStatusForm(StatesGroup):
    client_id = State()
    status = State()


# =========================================================
# BOT
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# =========================================================
# HELPERS
# =========================================================

def normalize_digits(value):
    if value is None:
        return ""

    value = str(value)

    translation = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    )

    return value.translate(translation)


def number(value, default=0):
    try:
        value = normalize_digits(value)
        value = value.replace(",", "").replace("٬", "")
        return float(value)
    except Exception:
        return default


def money(value):
    if value is None:
        return "0"

    try:
        value = float(value)

        if value.is_integer():
            return f"{int(value):,}"

        return f"{value:,.2f}"

    except Exception:
        return str(value)


def is_admin(user_id: int) -> bool:
    return (
        ADMIN_TELEGRAM_ID != ""
        and str(user_id) == ADMIN_TELEGRAM_ID
    )


def is_allowed(user_id: int) -> bool:
    if is_admin(user_id):
        return True

    return str(user_id) in ALLOWED_TELEGRAM_IDS


async def access_required(message: Message) -> bool:
    if is_allowed(message.from_user.id):
        return True

    await message.answer(
        "⛔ دسترسی شما به این ربات تأیید نشده است.\n\n"
        "در صورت نیاز، با مدیر سیستم تماس بگیرید."
    )

    return False


async def callback_access_required(callback: CallbackQuery) -> bool:
    if is_allowed(callback.from_user.id):
        return True

    await callback.answer(
        "⛔ دسترسی ندارید.",
        show_alert=True
    )

    return False


def keyboard(
    rows,
    include_cancel=True
):
    result = []

    for row in rows:
        result.append([
            KeyboardButton(text=str(x))
            for x in row
        ])

    if include_cancel:
        result.append([
            KeyboardButton(text="❌ لغو")
        ])

    return ReplyKeyboardMarkup(
        keyboard=result,
        resize_keyboard=True
    )


def one_column(items, include_cancel=True):
    return keyboard(
        [[x] for x in items],
        include_cancel=include_cancel
    )


def main_menu(user_id: int):
    rows = [
        ["🏠 فایل‌ها", "👤 مشتری‌ها"],
        ["➕ ثبت فایل", "➕ ثبت مشتری"],
        ["👀 ثبت بازدید", "📞 پیگیری"],
        ["🔎 پیشنهاد فایل", "📊 KPI من"],
    ]

    if is_admin(user_id):
        rows.append([
            "📝 آخرین فعالیت‌ها",
            "👥 KPI تیم"
        ])

    return keyboard(
        rows,
        include_cancel=False
    )


async def get_user(
    session: AsyncSession,
    telegram_id: int,
    name: str = ""
):
    result = await session.execute(
        select(User).where(
            User.telegram_id == telegram_id
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            name=name,
            role="مدیر" if is_admin(telegram_id) else "مشاور"
        )

        session.add(user)
        await session.commit()

    return user


async def add_activity(
    session,
    user_id,
    activity_type,
    note="",
    property_id=0,
    client_id=0
):
    activity = Activity(
        user_id=user_id,
        property_id=property_id,
        client_id=client_id,
        activity_type=activity_type,
        note=note
    )

    session.add(activity)
    await session.commit()


# =========================================================
# MIGRATION
# =========================================================

async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def get_columns(sync_conn, table_name):
            inspector = inspect(sync_conn)
            return {
                col["name"]
                for col in inspector.get_columns(table_name)
            }

        property_columns = await conn.run_sync(
            lambda sync_conn: get_columns(
                sync_conn,
                "properties"
            )
        )

        client_columns = await conn.run_sync(
            lambda sync_conn: get_columns(
                sync_conn,
                "clients"
            )
        )

        async def add_column_if_missing(
            sync_conn,
            table,
            column_name,
            sql_type
        ):
            columns = get_columns(
                sync_conn,
                table
            )

            if column_name not in columns:
                sync_conn.exec_driver_sql(
                    f"ALTER TABLE {table} "
                    f"ADD COLUMN {column_name} {sql_type}"
                )

        await conn.run_sync(
            lambda sync_conn: add_column_if_missing(
                sync_conn,
                "properties",
                "address",
                "TEXT DEFAULT ''"
            )
        )

        await conn.run_sync(
            lambda sync_conn: add_column_if_missing(
                sync_conn,
                "properties",
                "unit_floor",
                "INTEGER DEFAULT 0"
            )
        )

        await conn.run_sync(
            lambda sync_conn: add_column_if_missing(
                sync_conn,
                "properties",
                "status",
                "VARCHAR(100) DEFAULT 'فعال'"
            )
        )

        await conn.run_sync(
            lambda sync_conn: add_column_if_missing(
                sync_conn,
                "properties",
                "transaction_value",
                "FLOAT DEFAULT 0"
            )
        )

        await conn.run_sync(
            lambda sync_conn: add_column_if_missing(
                sync_conn,
                "properties",
                "updated_at",
                "DATETIME"
            )
        )

        await conn.run_sync(
            lambda sync_conn: add_column_if_missing(
                sync_conn,
                "clients",
                "status",
                "VARCHAR(50) DEFAULT 'فعال'"
            )
        )


# =========================================================
# START / ACCESS
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    await state.clear()

    if not await access_required(message):
        return

    async with SessionLocal() as session:

        await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

    await message.answer(
        "🏙️ **شهردار ایران‌زمین**\n"
        "Hooman Real Estate\n\n"
        "سیستم مدیریت فایل، مشتری و تیم",
        reply_markup=main_menu(
            message.from_user.id
        ),
        parse_mode="Markdown"
    )


@dp.message(F.text == "❌ لغو")
async def cancel_all(
    message: Message,
    state: FSMContext
):

    if not await access_required(message):
        return

    await state.clear()

    await message.answer(
        "❌ عملیات لغو شد.",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# PROPERTY REGISTRATION
# =========================================================

@dp.message(F.text == "➕ ثبت فایل")
async def property_start(
    message: Message,
    state: FSMContext
):

    if not await access_required(message):
        return

    await state.clear()

    await state.set_state(
        PropertyForm.code
    )

    await message.answer(
        "➕ ثبت فایل جدید\n\n"
        "کد فایل را وارد کن:"
    )


@dp.message(PropertyForm.code)
async def property_code(
    message: Message,
    state: FSMContext
):

    code = message.text.strip()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.code == code
            )
        )

        exists = result.scalar_one_or_none()

    if exists:
        await message.answer(
            "⚠️ این کد فایل قبلاً ثبت شده.\n"
            "یک کد دیگر وارد کن:"
        )
        return

    await state.update_data(
        code=code
    )

    await state.set_state(
        PropertyForm.area
    )

    await message.answer(
        "📍 منطقه ملک را انتخاب کن:",
        reply_markup=one_column(
            AREAS
        )
    )


@dp.message(PropertyForm.area)
async def property_area(
    message: Message,
    state: FSMContext
):

    if message.text not in AREAS:
        await message.answer(
            "لطفاً یکی از مناطق را انتخاب کن."
        )
        return

    await state.update_data(
        area=message.text
    )

    await state.set_state(
        PropertyForm.address
    )

    await message.answer(
        "🏠 آدرس دقیق ملک را وارد کن:"
    )


@dp.message(PropertyForm.address)
async def property_address(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        address=message.text.strip()
    )

    await state.set_state(
        PropertyForm.sqm
    )

    await message.answer(
        "📐 متراژ را وارد کن:"
    )


@dp.message(PropertyForm.sqm)
async def property_sqm(
    message: Message,
    state: FSMContext
):

    value = number(message.text)

    if value <= 0:
        await message.answer(
            "متراژ معتبر وارد کن:"
        )
        return

    await state.update_data(
        sqm=value
    )

    await state.set_state(
        PropertyForm.price
    )

    await message.answer(
        "💰 قیمت کل را وارد کن:"
    )


@dp.message(PropertyForm.price)
async def property_price(
    message: Message,
    state: FSMContext
):

    value = number(message.text)

    if value < 0:
        await message.answer(
            "قیمت معتبر وارد کن:"
        )
        return

    await state.update_data(
        price=value
    )

    await state.set_state(
        PropertyForm.property_type
    )

    await message.answer(
        "🏢 نوع ملک را انتخاب کن:",
        reply_markup=one_column(
            PROPERTY_TYPES
        )
    )


@dp.message(PropertyForm.property_type)
async def property_type(
    message: Message,
    state: FSMContext
):

    if message.text not in PROPERTY_TYPES:
        await message.answer(
            "لطفاً نوع ملک را از دکمه‌ها انتخاب کن."
        )
        return

    await state.update_data(
        property_type=message.text
    )

    await state.set_state(
        PropertyForm.bedrooms
    )

    await message.answer(
        "🛏 تعداد خواب:",
        reply_markup=keyboard([
            ["۰", "۱", "۲", "۳"],
            ["۴", "۵", "+۵"]
        ])
    )


@dp.message(PropertyForm.bedrooms)
async def property_bedrooms(
    message: Message,
    state: FSMContext
):

    if message.text == "+۵":
        await message.answer(
            "تعداد دقیق خواب را وارد کن:"
        )
        return

    value = number(message.text)

    if value < 0:
        await message.answer(
            "تعداد خواب معتبر وارد کن."
        )
        return

    await state.update_data(
        bedrooms=int(value)
    )

    await state.set_state(
        PropertyForm.floors
    )

    await message.answer(
        "🏢 تعداد کل طبقات ساختمان:",
        reply_markup=keyboard([
            ["همکف", "۱", "۲", "۳", "۴"],
            ["۵", "۶", "۷", "۸", "۸+"]
        ])
    )


@dp.message(PropertyForm.floors)
async def property_floors(
    message: Message,
    state: FSMContext
):

    if message.text == "۸+":
        await message.answer(
            "تعداد دقیق طبقات را وارد کن:"
        )
        return

    if message.text == "همکف":
        value = 0
    else:
        value = int(number(message.text))

    if value < 0:
        await message.answer(
            "تعداد طبقات معتبر وارد کن."
        )
        return

    await state.update_data(
        floors=value
    )

    await state.set_state(
        PropertyForm.unit_floor
    )

    await message.answer(
        "🏠 ملک در چه طبقه‌ای قرار دارد؟",
        reply_markup=keyboard([
            ["همکف", "۱", "۲", "۳", "۴"],
            ["۵", "۶", "۷", "۸", "۸+"]
        ])
    )


@dp.message(PropertyForm.unit_floor)
async def property_unit_floor(
    message: Message,
    state: FSMContext
):

    if message.text == "۸+":
        await message.answer(
            "طبقه دقیق را وارد کن:"
        )
        return

    if message.text == "همکف":
        value = 0
    else:
        value = int(number(message.text))

    if value < 0:
        await message.answer(
            "طبقه معتبر وارد کن."
        )
        return

    await state.update_data(
        unit_floor=value
    )

    await state.set_state(
        PropertyForm.units_per_floor
    )

    await message.answer(
        "🚪 چند واحد در هر طبقه؟",
        reply_markup=keyboard([
            ["۱", "۲", "۳", "۴", "+۴"]
        ])
    )


@dp.message(PropertyForm.units_per_floor)
async def property_units(
    message: Message,
    state: FSMContext
):

    if message.text == "+۴":
        await message.answer(
            "تعداد دقیق واحد در هر طبقه را وارد کن:"
        )
        return

    value = int(number(message.text))

    if value <= 0:
        await message.answer(
            "تعداد معتبر وارد کن."
        )
        return

    await state.update_data(
        units_per_floor=value
    )

    await state.set_state(
        PropertyForm.elevator
    )

    await message.answer(
        "🛗 آسانسور؟",
        reply_markup=keyboard([
            ["دارد", "ندارد"]
        ])
    )


@dp.message(PropertyForm.elevator)
async def property_elevator(
    message: Message,
    state: FSMContext
):

    if message.text not in ["دارد", "ندارد"]:
        return

    await state.update_data(
        elevator=message.text
    )

    await state.set_state(
        PropertyForm.parking
    )

    await message.answer(
        "🚗 پارکینگ؟",
        reply_markup=keyboard([
            ["دارد", "ندارد"]
        ])
    )


@dp.message(PropertyForm.parking)
async def property_parking(
    message: Message,
    state: FSMContext
):

    if message.text not in ["دارد", "ندارد"]:
        return

    await state.update_data(
        parking=message.text
    )

    if message.text == "دارد":

        await state.set_state(
            PropertyForm.parking_type
        )

        await message.answer(
            "نوع پارکینگ:",
            reply_markup=keyboard([
                ["اختصاصی", "مشاع"],
                ["مزاحم", "نامشخص"]
            ])
        )

    else:

        await state.update_data(
            parking_type=""
        )

        await state.set_state(
            PropertyForm.storage
        )

        await message.answer(
            "انباری؟",
            reply_markup=keyboard([
                ["دارد", "ندارد"]
            ])
        )


@dp.message(PropertyForm.parking_type)
async def property_parking_type(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        parking_type=message.text
    )

    await state.set_state(
        PropertyForm.storage
    )

    await message.answer(
        "انباری؟",
        reply_markup=keyboard([
            ["دارد", "ندارد"]
        ])
    )


@dp.message(PropertyForm.storage)
async def property_storage(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        storage=message.text
    )

    await state.set_state(
        PropertyForm.tenant
    )

    await message.answer(
        "وضعیت سکونت:",
        reply_markup=keyboard([
            ["خالی", "مالک‌نشین"],
            ["مستأجر دارد", "نامشخص"]
        ])
    )


@dp.message(PropertyForm.tenant)
async def property_tenant(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        tenant=message.text
    )

    await state.set_state(
        PropertyForm.deposit
    )

    await message.answer(
        "💵 مبلغ رهن/ودیعه را وارد کن.\n"
        "اگر ندارد ۰ بزن:"
    )


@dp.message(PropertyForm.deposit)
async def property_deposit(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        deposit=number(message.text)
    )

    await state.set_state(
        PropertyForm.rent
    )

    await message.answer(
        "💵 مبلغ اجاره را وارد کن.\n"
        "اگر ندارد ۰ بزن:"
    )


@dp.message(PropertyForm.rent)
async def property_rent(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        rent=number(message.text)
    )

    await state.set_state(
        PropertyForm.vacancy_date
    )

    await message.answer(
        "📅 تاریخ تخلیه:\n"
        "اگر خالی است بنویس «الان»"
    )


@dp.message(PropertyForm.vacancy_date)
async def property_vacancy(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        vacancy_date=message.text.strip()
    )

    await state.set_state(
        PropertyForm.document_type
    )

    await message.answer(
        "📄 نوع سند:",
        reply_markup=keyboard([
            ["تک‌برگ", "منگوله‌دار"],
            ["قولنامه‌ای", "نامشخص"]
        ])
    )


@dp.message(PropertyForm.document_type)
async def property_document(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        document_type=message.text
    )

    await state.set_state(
        PropertyForm.owner_name
    )

    await message.answer(
        "👤 نام مالک / سازنده:"
    )


@dp.message(PropertyForm.owner_name)
async def property_owner_name(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        owner_name=message.text.strip()
    )

    await state.set_state(
        PropertyForm.owner_phone
    )

    await message.answer(
        "📞 شماره مالک / سازنده:"
    )


@dp.message(PropertyForm.owner_phone)
async def property_owner_phone(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        owner_phone=message.text.strip()
    )

    await state.set_state(
        PropertyForm.description
    )

    await message.answer(
        "📝 توضیحات فایل:"
    )


@dp.message(PropertyForm.description)
async def property_description(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        description=message.text.strip()
    )

    data = await state.get_data()

    preview = (
        "📋 **پیش‌نمایش فایل**\n\n"
        f"🔢 کد: {data.get('code')}\n"
        f"📍 منطقه: {data.get('area')}\n"
        f"🏠 آدرس: {data.get('address')}\n"
        f"📐 متراژ: {money(data.get('sqm'))}\n"
        f"💰 قیمت: {money(data.get('price'))}\n"
        f"🏢 نوع: {data.get('property_type')}\n"
        f"🛏 خواب: {data.get('bedrooms')}\n"
        f"🏢 طبقات: {data.get('floors')}\n"
        f"🏠 طبقه ملک: {data.get('unit_floor')}\n"
        f"🚪 واحد در طبقه: {data.get('units_per_floor')}\n"
        f"🛗 آسانسور: {data.get('elevator')}\n"
        f"🚗 پارکینگ: {data.get('parking')}\n"
        f"📦 انباری: {data.get('storage')}\n"
        f"👤 مالک: {data.get('owner_name')}\n"
        f"📞 تلفن: {data.get('owner_phone')}\n"
        f"📝 توضیحات: {data.get('description')}\n"
    )

    await state.set_state(
        PropertyForm.confirmation
    )

    await message.answer(
        preview,
        reply_markup=keyboard([
            ["✅ ثبت نهایی", "✏️ اصلاح"],
            ["❌ لغو"]
        ]),
        parse_mode="Markdown"
    )


@dp.message(PropertyForm.confirmation)
async def property_confirmation(
    message: Message,
    state: FSMContext
):

    if message.text == "✏️ اصلاح":
        await message.answer(
            "بعد از ثبت فایل می‌توانی هر فیلد را جداگانه اصلاح کنی."
        )
        return

    if message.text != "✅ ثبت نهایی":
        return

    data = await state.get_data()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.code == data["code"]
            )
        )

        if result.scalar_one_or_none():
            await message.answer(
                "⚠️ این کد فایل قبلاً ثبت شده."
            )
            await state.clear()
            return

        prop = Property(
            code=data["code"],
            area=data["area"],
            address=data["address"],
            sqm=data["sqm"],
            price=data["price"],
            property_type=data["property_type"],
            bedrooms=data["bedrooms"],
            floors=data["floors"],
            unit_floor=data["unit_floor"],
            units_per_floor=data["units_per_floor"],
            elevator=data.get("elevator", ""),
            parking=data.get("parking", ""),
            parking_type=data.get("parking_type", ""),
            storage=data.get("storage", ""),
            tenant=data.get("tenant", ""),
            deposit=data.get("deposit", 0),
            rent=data.get("rent", 0),
            vacancy_date=data.get("vacancy_date", ""),
            document_type=data.get("document_type", ""),
            owner_name=data.get("owner_name", ""),
            owner_phone=data.get("owner_phone", ""),
            description=data.get("description", ""),
            status="فعال",
            created_by=message.from_user.id,
            updated_at=datetime.utcnow()
        )

        session.add(prop)
        await session.commit()

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "ثبت فایل",
            f"فایل {prop.code} ثبت شد.",
            property_id=prop.id
        )

        owner_count_result = await session.execute(
            select(func.count(Property.id)).where(
                Property.owner_name == prop.owner_name,
                Property.owner_phone == prop.owner_phone
            )
        )

        owner_count_value = owner_count_result.scalar() or 0

    await state.clear()

    await message.answer(
        f"✅ فایل با موفقیت ثبت شد.\n\n"
        f"🔢 کد: {data['code']}\n"
        f"📍 منطقه: {data['area']}\n"
        f"🏠 آدرس: {data['address']}\n"
        f"👤 فایل‌های این مالک/سازنده: {owner_count_value}",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# PROPERTY LIST
# =========================================================

@dp.message(F.text == "🏠 فایل‌ها")
async def property_list(
    message: Message
):

    if not await access_required(message):
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property)
            .order_by(Property.created_at.desc())
            .limit(30)
        )

        properties = result.scalars().all()

    if not properties:
        await message.answer(
            "📭 هنوز فایلی ثبت نشده."
        )
        return

    rows = []

    for p in properties:
        rows.append([
            f"🏠 {p.code} | {p.area}"
        ])

    await message.answer(
        "📂 فایل‌ها:",
        reply_markup=one_column(
            [x[0] for x in rows]
        )
    )


@dp.message(F.text.startswith("🏠 "))
async def property_open_from_list(
    message: Message
):

    if not await access_required(message):
        return

    code = message.text.replace("🏠 ", "").split("|")[0].strip()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.code == code
            )
        )

        prop = result.scalar_one_or_none()

        if not prop:
            await message.answer(
                "فایل پیدا نشد."
            )
            return

        await show_property(
            message,
            session,
            prop
        )


async def show_property(
    message,
    session,
    prop
):

    result = await session.execute(
        select(func.count(Property.id)).where(
            Property.owner_name == prop.owner_name,
            Property.owner_phone == prop.owner_phone
        )
    )

    owner_count_value = result.scalar() or 0

    text = (
        f"🏠 **فایل {prop.code}**\n\n"
        f"📍 منطقه: {prop.area}\n"
        f"🏠 آدرس: {prop.address}\n"
        f"📐 متراژ: {money(prop.sqm)}\n"
        f"💰 قیمت: {money(prop.price)}\n"
        f"🏢 نوع: {prop.property_type}\n"
        f"🛏 خواب: {prop.bedrooms}\n"
        f"🏢 کل طبقات: {prop.floors}\n"
        f"🏠 طبقه ملک: {prop.unit_floor}\n"
        f"🚪 واحد/طبقه: {prop.units_per_floor}\n"
        f"🛗 آسانسور: {prop.elevator}\n"
        f"🚗 پارکینگ: {prop.parking}\n"
        f"📦 انباری: {prop.storage}\n"
        f"👤 مالک: {prop.owner_name}\n"
        f"📞 تلفن: {prop.owner_phone}\n"
        f"📊 وضعیت: {prop.status}\n"
        f"👥 تعداد فایل‌های مالک: {owner_count_value}\n\n"
        f"📝 {prop.description}"
    )

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ اصلاح",
                        callback_data=f"edit:{prop.id}"
                    ),
                    InlineKeyboardButton(
                        text="🔄 وضعیت",
                        callback_data=f"status:{prop.id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📜 تاریخچه",
                        callback_data=f"history:{prop.id}"
                    ),
                    InlineKeyboardButton(
                        text="🕒 رویداد",
                        callback_data=f"event:{prop.id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👤 فایل‌های مالک",
                        callback_data=f"owner:{prop.id}"
                    )
                ]
            ]
        ),
        parse_mode="Markdown"
    )


# =========================================================
# PROPERTY STATUS
# =========================================================

@dp.callback_query(F.data.startswith("status:"))
async def property_status_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    prop_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        property_id=prop_id
    )

    await state.set_state(
        StatusForm.status
    )

    await callback.message.answer(
        "وضعیت جدید فایل:",
        reply_markup=one_column(
            STATUSES
        )
    )

    await callback.answer()


@dp.message(StatusForm.status)
async def property_status_save(
    message: Message,
    state: FSMContext
):

    if message.text not in STATUSES:
        return

    data = await state.get_data()

    await state.update_data(
        status=message.text
    )

    if message.text == "🔵 معامله شد - توسط ما":

        await state.set_state(
            StatusForm.transaction_value
        )

        await message.answer(
            "💰 ارزش معامله را وارد کن:"
        )

        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id == data["property_id"]
            )
        )

        prop = result.scalar_one_or_none()

        if not prop:
            await state.clear()
            return

        old_status = prop.status

        prop.status = message.text
        prop.updated_at = datetime.utcnow()

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "تغییر وضعیت فایل",
            f"{old_status} → {message.text}",
            property_id=prop.id
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ وضعیت فایل تغییر کرد.",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


@dp.message(StatusForm.transaction_value)
async def property_transaction_value(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id == data["property_id"]
            )
        )

        prop = result.scalar_one_or_none()

        if not prop:
            await state.clear()
            return

        old_status = prop.status

        prop.status = "🔵 معامله شد - توسط ما"
        prop.transaction_value = number(message.text)
        prop.updated_at = datetime.utcnow()

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "معامله فایل",
            f"{old_status} → معامله شد توسط ما | "
            f"ارزش معامله: {money(prop.transaction_value)}",
            property_id=prop.id
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ معامله ثبت شد.",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# PROPERTY HISTORY
# =========================================================

@dp.callback_query(F.data.startswith("history:"))
async def property_history(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    prop_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(Activity)
            .where(
                Activity.property_id == prop_id
            )
            .order_by(
                Activity.created_at.desc()
            )
            .limit(30)
        )

        activities = result.scalars().all()

    if not activities:
        text = "📜 تاریخچه‌ای ثبت نشده."
    else:
        lines = ["📜 تاریخچه فایل:\n"]

        for a in activities:
            lines.append(
                f"• {a.created_at.strftime('%Y-%m-%d %H:%M')} | "
                f"{a.activity_type}\n"
                f"  {a.note}"
            )

        text = "\n".join(lines)

    await callback.message.answer(text)
    await callback.answer()


# =========================================================
# PROPERTY EVENT
# =========================================================

@dp.callback_query(F.data.startswith("event:"))
async def event_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    prop_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        property_id=prop_id
    )

    await state.set_state(
        EventForm.event_type
    )

    await callback.message.answer(
        "نوع رویداد:",
        reply_markup=one_column([
            "تماس با مالک",
            "بازدید",
            "مذاکره",
            "تغییر قیمت",
            "قرارداد",
            "پیگیری",
            "سایر"
        ])
    )

    await callback.answer()


@dp.message(EventForm.event_type)
async def event_type(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        event_type=message.text
    )

    await state.set_state(
        EventForm.note
    )

    await message.answer(
        "توضیح رویداد:"
    )


@dp.message(EventForm.note)
async def event_save(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    async with SessionLocal() as session:

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            data["event_type"],
            message.text,
            property_id=data["property_id"]
        )

    await state.clear()

    await message.answer(
        "✅ رویداد ثبت شد.",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# OWNER FILES
# =========================================================

@dp.callback_query(F.data.startswith("owner:"))
async def owner_files(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    prop_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id == prop_id
            )
        )

        prop = result.scalar_one_or_none()

        if not prop:
            await callback.answer(
                "فایل پیدا نشد.",
                show_alert=True
            )
            return

        result = await session.execute(
            select(Property)
            .where(
                Property.owner_name == prop.owner_name,
                Property.owner_phone == prop.owner_phone
            )
            .order_by(
                Property.created_at.desc()
            )
        )

        files = result.scalars().all()

    lines = [
        f"👤 فایل‌های {prop.owner_name}:\n"
    ]

    for p in files:
        lines.append(
            f"🏠 {p.code} | "
            f"{p.area} | "
            f"{money(p.sqm)} متر | "
            f"{p.status}"
        )

    await callback.message.answer(
        "\n".join(lines)
    )

    await callback.answer()


# =========================================================
# CLIENT REGISTRATION
# =========================================================

@dp.message(F.text == "➕ ثبت مشتری")
async def client_start(
    message: Message,
    state: FSMContext
):

    if not await access_required(message):
        return

    await state.clear()

    await state.set_state(
        ClientForm.name
    )

    await message.answer(
        "➕ ثبت مشتری\n\n"
        "نام مشتری:"
    )


@dp.message(ClientForm.name)
async def client_name(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        name=message.text.strip()
    )

    await state.set_state(
        ClientForm.phone
    )

    await message.answer(
        "📞 شماره مشتری:"
    )


@dp.message(ClientForm.phone)
async def client_phone(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        phone=message.text.strip()
    )

    await state.set_state(
        ClientForm.area
    )

    await message.answer(
        "📍 منطقه موردنظر مشتری:",
        reply_markup=one_column(
            AREAS
        )
    )


@dp.message(ClientForm.area)
async def client_area(
    message: Message,
    state: FSMContext
):

    if message.text not in AREAS:
        await message.answer(
            "لطفاً یکی از مناطق را انتخاب کن."
        )
        return

    await state.update_data(
        area=message.text
    )

    await state.set_state(
        ClientForm.min_sqm
    )

    await message.answer(
        "📐 حداقل متراژ:"
    )


@dp.message(ClientForm.min_sqm)
async def client_min_sqm(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        min_sqm=number(message.text)
    )

    await state.set_state(
        ClientForm.max_sqm
    )

    await message.answer(
        "📐 حداکثر متراژ:"
    )


@dp.message(ClientForm.max_sqm)
async def client_max_sqm(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        max_sqm=number(message.text)
    )

    await state.set_state(
        ClientForm.min_budget
    )

    await message.answer(
        "💰 حداقل بودجه:"
    )


@dp.message(ClientForm.min_budget)
async def client_min_budget(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        min_budget=number(message.text)
    )

    await state.set_state(
        ClientForm.max_budget
    )

    await message.answer(
        "💰 حداکثر بودجه:"
    )


@dp.message(ClientForm.max_budget)
async def client_max_budget(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        max_budget=number(message.text)
    )

    await state.set_state(
        ClientForm.property_type
    )

    await message.answer(
        "🏢 نوع ملک موردنظر:",
        reply_markup=one_column(
            PROPERTY_TYPES
        )
    )


@dp.message(ClientForm.property_type)
async def client_property_type(
    message: Message,
    state: FSMContext
):

    if message.text not in PROPERTY_TYPES:
        return

    await state.update_data(
        property_type=message.text
    )

    await state.set_state(
        ClientForm.description
    )

    await message.answer(
        "📝 توضیحات مشتری:"
    )


@dp.message(ClientForm.description)
async def client_save(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    async with SessionLocal() as session:

        client = Client(
            name=data["name"],
            phone=data["phone"],
            area=data["area"],
            min_sqm=data["min_sqm"],
            max_sqm=data["max_sqm"],
            min_budget=data["min_budget"],
            max_budget=data["max_budget"],
            property_type=data["property_type"],
            bedrooms=0,
            description=message.text,
            status="فعال",
            created_by=message.from_user.id
        )

        session.add(client)
        await session.commit()

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "ثبت مشتری",
            f"مشتری {client.name} ثبت شد.",
            client_id=client.id
        )

    await state.clear()

    await message.answer(
        "✅ مشتری ثبت شد.",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# CLIENT LIST
# =========================================================

@dp.message(F.text == "👤 مشتری‌ها")
async def client_list(
    message: Message
):

    if not await access_required(message):
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client)
            .order_by(Client.created_at.desc())
            .limit(50)
        )

        clients = result.scalars().all()

    if not clients:
        await message.answer(
            "📭 هنوز مشتری‌ای ثبت نشده."
        )
        return

    lines = ["👤 مشتری‌ها:\n"]

    buttons = []

    for c in clients:

        budget = (
            f"{money(c.min_budget)} تا "
            f"{money(c.max_budget)}"
        )

        status_icon = {
            "فعال": "🟢",
            "خرید کرده": "🔵",
            "منصرف شده": "🔴"
        }.get(c.status, "⚪")

        lines.append(
            f"{status_icon} {c.name} | "
            f"💰 {budget}"
        )

        buttons.append([
            f"👤 {c.name} | {c.id}"
        ])

    await message.answer(
        "\n".join(lines),
        reply_markup=one_column(
            [x[0] for x in buttons]
        )
    )


@dp.message(F.text.startswith("👤 "))
async def client_detail(
    message: Message
):

    if not await access_required(message):
        return

    try:
        client_id = int(
            message.text.split("|")[-1].strip()
        )
    except Exception:
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client).where(
                Client.id == client_id
            )
        )

        client = result.scalar_one_or_none()

        if not client:
            await message.answer(
                "مشتری پیدا نشد."
            )
            return

    await message.answer(
        f"👤 **{client.name}**\n\n"
        f"📞 تلفن: {client.phone}\n"
        f"📍 منطقه: {client.area}\n"
        f"📐 متراژ: {money(client.min_sqm)} تا {money(client.max_sqm)}\n"
        f"💰 بودجه: {money(client.min_budget)} تا {money(client.max_budget)}\n"
        f"🏢 نوع ملک: {client.property_type}\n"
        f"📊 وضعیت: {client.status}\n"
        f"📝 توضیحات: {client.description}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 تغییر وضعیت",
                        callback_data=f"clientstatus:{client.id}"
                    )
                ]
            ]
        ),
        parse_mode="Markdown"
    )


# =========================================================
# CLIENT STATUS
# =========================================================

@dp.callback_query(F.data.startswith("clientstatus:"))
async def client_status_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    client_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        client_id=client_id
    )

    await state.set_state(
        ClientStatusForm.status
    )

    await callback.message.answer(
        "وضعیت مشتری:",
        reply_markup=one_column(
            CLIENT_STATUSES
        )
    )

    await callback.answer()


@dp.message(ClientStatusForm.status)
async def client_status_save(
    message: Message,
    state: FSMContext
):

    if message.text not in CLIENT_STATUSES:
        return

    data = await state.get_data()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client).where(
                Client.id == data["client_id"]
            )
        )

        client = result.scalar_one_or_none()

        if not client:
            await state.clear()
            return

        old_status = client.status

        client.status = message.text

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "تغییر وضعیت مشتری",
            f"{old_status} → {message.text}",
            client_id=client.id
        )

        await session.commit()

    await state.clear()

    await message.answer(
        f"✅ وضعیت {client.name} شد: {message.text}",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# VISIT
# =========================================================

@dp.message(F.text == "👀 ثبت بازدید")
async def visit_start(
    message: Message,
    state: FSMContext
):

    if not await access_required(message):
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client)
            .where(
                Client.status == "فعال"
            )
            .order_by(Client.created_at.desc())
        )

        clients = result.scalars().all()

    if not clients:
        await message.answer(
            "اول یک مشتری فعال ثبت کن."
        )
        return

    await state.clear()

    await state.set_state(
        VisitForm.client_id
    )

    await message.answer(
        "👤 مشتری را انتخاب کن:",
        reply_markup=one_column([
            f"{c.name} | {c.id}"
            for c in clients
        ])
    )


@dp.message(VisitForm.client_id)
async def visit_client(
    message: Message,
    state: FSMContext
):

    try:
        client_id = int(
            message.text.split("|")[-1].strip()
        )
    except Exception:
        return

    await state.update_data(
        client_id=client_id
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property)
            .where(
                Property.status.in_([
                    "🟢 فعال",
                    "🟡 در مذاکره",
                    "فعال",
                    "در مذاکره"
                ])
            )
            .order_by(Property.created_at.desc())
        )

        properties = result.scalars().all()

    if not properties:
        await message.answer(
            "فایل فعالی وجود ندارد."
        )
        await state.clear()
        return

    await state.set_state(
        VisitForm.property_id
    )

    await message.answer(
        "🏠 فایل را انتخاب کن:",
        reply_markup=one_column([
            f"{p.code} | {p.area} | {money(p.sqm)} متر"
            for p in properties
        ])
    )


@dp.message(VisitForm.property_id)
async def visit_property(
    message: Message,
    state: FSMContext
):

    code = message.text.split("|")[0].strip()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.code == code
            )
        )

        prop = result.scalar_one_or_none()

        if not prop:
            await message.answer(
                "فایل پیدا نشد."
            )
            return

        data = await state.get_data()

        previous_result = await session.execute(
            select(Visit)
            .where(
                Visit.client_id == data["client_id"],
                Visit.property_id == prop.id
            )
            .order_by(
                Visit.visited_at.desc()
            )
        )

        previous = previous_result.scalars().first()

        if previous:

            await message.answer(
                "⚠️ این مشتری قبلاً این فایل را دیده است.\n\n"
                f"آخرین بازدید: "
                f"{previous.visited_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"علاقه: {previous.interest}\n"
                f"پیگیری بعدی: {previous.followup_date}\n\n"
                "برای ثبت بازدید مجدد دوباره ادامه بده."
            )

    await state.update_data(
        property_id=prop.id
    )

    await state.set_state(
        VisitForm.interest
    )

    await message.answer(
        "🔥 میزان علاقه مشتری:",
        reply_markup=one_column(
            INTERESTS
        )
    )


@dp.message(VisitForm.interest)
async def visit_interest(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        interest=message.text
    )

    await state.set_state(
        VisitForm.price_reaction
    )

    await message.answer(
        "💰 واکنش به قیمت:",
        reply_markup=one_column(
            PRICE_REACTIONS
        )
    )


@dp.message(VisitForm.price_reaction)
async def visit_price(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        price_reaction=message.text
    )

    await state.set_state(
        VisitForm.property_reaction
    )

    await message.answer(
        "🏠 واکنش به ملک:",
        reply_markup=one_column(
            PROPERTY_REACTIONS
        )
    )


@dp.message(VisitForm.property_reaction)
async def visit_property_reaction(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        property_reaction=message.text
    )

    await state.set_state(
        VisitForm.objection
    )

    await message.answer(
        "❗ ایراد / اعتراض مشتری را بنویس:"
    )


@dp.message(VisitForm.objection)
async def visit_objection(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        objection=message.text
    )

    await state.set_state(
        VisitForm.next_action
    )

    await message.answer(
        "➡️ اقدام بعدی:",
        reply_markup=one_column(
            NEXT_ACTIONS
        )
    )


@dp.message(VisitForm.next_action)
async def visit_next_action(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        next_action=message.text
    )

    await state.set_state(
        VisitForm.followup_date
    )

    await message.answer(
        "📅 تاریخ پیگیری بعدی را وارد کن.\n"
        "مثلاً: ۱۴۰۵/۰۷/۰۱\n"
        "اگر نیاز نیست: «ندارد»"
    )


@dp.message(VisitForm.followup_date)
async def visit_followup(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        followup_date=message.text
    )

    await state.set_state(
        VisitForm.note
    )

    await message.answer(
        "📝 یادداشت بازدید:"
    )


@dp.message(VisitForm.note)
async def visit_save(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    async with SessionLocal() as session:

        visit = Visit(
            property_id=data["property_id"],
            client_id=data["client_id"],
            agent_id=message.from_user.id,
            interest=data["interest"],
            price_reaction=data["price_reaction"],
            property_reaction=data["property_reaction"],
            objection=data["objection"],
            next_action=data["next_action"],
            followup_date=data["followup_date"],
            note=message.text
        )

        session.add(visit)
        await session.commit()

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "ثبت بازدید",
            f"اقدام بعدی: {data['next_action']}",
            property_id=data["property_id"],
            client_id=data["client_id"]
        )

    await state.clear()

    await message.answer(
        "✅ کارنامه بازدید ثبت شد.",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# FOLLOW UPS
# =========================================================

@dp.message(F.text == "📞 پیگیری")
async def followups(
    message: Message
):

    if not await access_required(message):
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Visit)
            .where(
                Visit.followup_date != ""
            )
            .order_by(
                Visit.visited_at.desc()
            )
            .limit(50)
        )

        visits = result.scalars().all()

    if not visits:
        await message.answer(
            "📭 پیگیری فعالی ثبت نشده."
        )
        return

    lines = ["📞 پیگیری‌ها:\n"]

    for v in visits:

        async with SessionLocal() as session:

            client_result = await session.execute(
                select(Client).where(
                    Client.id == v.client_id
                )
            )

            client = client_result.scalar_one_or_none()

            if not client:
                continue

            # خرید کرده = دیگر در پیگیری نمایش داده نشود
            if client.status == "خرید کرده":
                continue

            prop_result = await session.execute(
                select(Property).where(
                    Property.id == v.property_id
                )
            )

            prop = prop_result.scalar_one_or_none()

        if not prop:
            continue

        lines.append(
            f"👤 {client.name}\n"
            f"🏠 فایل: {prop.code}\n"
            f"📅 پیگیری: {v.followup_date}\n"
            f"➡️ اقدام: {v.next_action}\n"
        )

    if len(lines) == 1:
        await message.answer(
            "📭 پیگیری فعالی وجود ندارد."
        )
        return

    await message.answer(
        "\n".join(lines)
    )


# =========================================================
# SMART MATCHING
# =========================================================

@dp.message(F.text == "🔎 پیشنهاد فایل")
async def matching(
    message: Message
):

    if not await access_required(message):
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client)
            .where(
                Client.status == "فعال"
            )
            .order_by(
                Client.created_at.desc()
            )
        )

        clients = result.scalars().all()

    if not clients:
        await message.answer(
            "مشتری فعالی وجود ندارد."
        )
        return

    await message.answer(
        "👤 مشتری را انتخاب کن:",
        reply_markup=one_column([
            f"{c.name} | {c.id}"
            for c in clients
        ])
    )


@dp.message(F.text.regexp(r"^.*\|\s*\d+$"))
async def matching_client_selected(
    message: Message
):

    if not await access_required(message):
        return

    try:
        client_id = int(
            message.text.split("|")[-1].strip()
        )
    except Exception:
        return

    async with SessionLocal() as session:

        client_result = await session.execute(
            select(Client).where(
                Client.id == client_id
            )
        )

        client = client_result.scalar_one_or_none()

        if not client:
            return

        prop_result = await session.execute(
            select(Property).where(
                Property.status.in_([
                    "🟢 فعال",
                    "🟡 در مذاکره",
                    "فعال",
                    "در مذاکره"
                ])
            )
        )

        properties = prop_result.scalars().all()

        visited_result = await session.execute(
            select(Visit.property_id).where(
                Visit.client_id == client.id
            )
        )

        visited_ids = {
            x for x in visited_result.scalars().all()
        }

    scored = []

    for p in properties:

        score = 0

        # بودجه = 40%
        if client.max_budget > 0:

            if p.price <= client.max_budget:

                if (
                    client.min_budget <= 0
                    or p.price >= client.min_budget
                ):
                    score += 40

                else:
                    score += 30

            else:

                difference = (
                    p.price - client.max_budget
                ) / client.max_budget

                if difference <= 0.10:
                    score += 20

        # منطقه = 25%
        if client.area == p.area:
            score += 25

        # متراژ = 20%
        if client.max_sqm > 0:

            if (
                client.min_sqm <= p.sqm
                <= client.max_sqm
            ):
                score += 20

            elif (
                abs(p.sqm - client.max_sqm)
                / client.max_sqm <= 0.10
            ):
                score += 10

        # نوع ملک = 15%
        if (
            client.property_type == p.property_type
            or client.property_type == "سایر"
        ):
            score += 15

        scored.append(
            (
                score,
                p,
                p.id in visited_ids
            )
        )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    top = scored[:10]

    if not top:
        await message.answer(
            "فایل مناسبی پیدا نشد."
        )
        return

    lines = [
        f"🔎 پیشنهاد فایل برای {client.name}\n"
    ]

    for score, p, visited in top:

        visited_text = (
            " | 👀 قبلاً دیده شده"
            if visited
            else ""
        )

        lines.append(
            f"🏠 {p.code}\n"
            f"📍 {p.area}\n"
            f"📐 {money(p.sqm)} متر\n"
            f"💰 {money(p.price)}\n"
            f"🏢 {p.property_type}\n"
            f"🎯 تطابق: {score}%"
            f"{visited_text}\n"
        )

    await message.answer(
        "\n".join(lines)
    )


# =========================================================
# MY KPI
# =========================================================

@dp.message(F.text == "📊 KPI من")
async def my_kpi(
    message: Message
):

    if not await access_required(message):
        return

    async with SessionLocal() as session:

        user_result = await session.execute(
            select(User).where(
                User.telegram_id ==
                message.from_user.id
            )
        )

        user = user_result.scalar_one_or_none()

        if not user:
            return

        activity_count = await session.scalar(
            select(func.count(Activity.id))
            .where(
                Activity.user_id == user.id
            )
        )

        visits_count = await session.scalar(
            select(func.count(Visit.id))
            .where(
                Visit.agent_id ==
                message.from_user.id
            )
        )

        property_count = await session.scalar(
            select(func.count(Property.id))
            .where(
                Property.created_by ==
                message.from_user.id
            )
        )

        client_count = await session.scalar(
            select(func.count(Client.id))
            .where(
                Client.created_by ==
                message.from_user.id
            )
        )

    await message.answer(
        "📊 **KPI من**\n\n"
        f"🏠 فایل ثبت‌شده: {property_count or 0}\n"
        f"👤 مشتری ثبت‌شده: {client_count or 0}\n"
        f"👀 بازدید: {visits_count or 0}\n"
        f"📝 فعالیت: {activity_count or 0}",
        parse_mode="Markdown"
    )


# =========================================================
# TEAM KPI — ADMIN ONLY
# =========================================================

@dp.message(F.text == "👥 KPI تیم")
async def team_kpi(
    message: Message
):

    if not await access_required(message):
        return

    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ این بخش فقط برای مدیر سیستم است."
        )
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(User)
            .order_by(User.created_at)
        )

        users = result.scalars().all()

        lines = [
            "👥 **KPI تیم**\n"
        ]

        for user in users:

            activities = await session.scalar(
                select(func.count(Activity.id))
                .where(
                    Activity.user_id == user.id
                )
            )

            visits = await session.scalar(
                select(func.count(Visit.id))
                .where(
                    Visit.agent_id ==
                    user.telegram_id
                )
            )

            files = await session.scalar(
                select(func.count(Property.id))
                .where(
                    Property.created_by ==
                    user.telegram_id
                )
            )

            clients = await session.scalar(
                select(func.count(Client.id))
                .where(
                    Client.created_by ==
                    user.telegram_id
                )
            )

            lines.append(
                f"👤 {user.name}\n"
                f"🏠 فایل: {files or 0}\n"
                f"👤 مشتری: {clients or 0}\n"
                f"👀 بازدید: {visits or 0}\n"
                f"📝 فعالیت: {activities or 0}\n"
            )

    await message.answer(
        "\n".join(lines),
        parse_mode="Markdown"
    )


# =========================================================
# LAST ACTIVITIES — ADMIN ONLY
# =========================================================

@dp.message(F.text == "📝 آخرین فعالیت‌ها")
async def latest_activities(
    message: Message
):

    if not await access_required(message):
        return

    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ این بخش فقط برای مدیر سیستم است."
        )
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Activity)
            .order_by(
                Activity.created_at.desc()
            )
            .limit(50)
        )

        activities = result.scalars().all()

    if not activities:
        await message.answer(
            "📭 فعالیتی ثبت نشده."
        )
        return

    lines = [
        "📝 **آخرین فعالیت‌ها**\n"
    ]

    for a in activities:

        lines.append(
            f"• {a.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"👤 User ID: {a.user_id}\n"
            f"⚙️ {a.activity_type}\n"
            f"📝 {a.note}\n"
        )

    await message.answer(
        "\n".join(lines),
        parse_mode="Markdown"
    )


# =========================================================
# CALLBACK ACCESS GUARD
# =========================================================

@dp.callback_query()
async def unknown_callback(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    await callback.answer()


# =========================================================
# ERROR HANDLER
# =========================================================

@dp.errors()
async def errors_handler(event):
    print("BOT ERROR:", event.exception)


# =========================================================
# MAIN
# =========================================================

async def main():

    await migrate()

    print("🏙️ Hooman Real Estate CRM started.")

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":
    asyncio.run(main())
