import os
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Text,
    select,
    func,
    inspect,
    or_,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///crm.db"
)

ADMIN_TELEGRAM_ID = os.getenv(
    "ADMIN_TELEGRAM_ID",
    ""
).strip()

ALLOWED_TELEGRAM_IDS = {
    x.strip()
    for x in os.getenv(
        "ALLOWED_TELEGRAM_IDS",
        ""
    ).split(",")
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
    echo=False,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
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

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

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
        default="🟢 فعال"
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


class PropertyPhoto(Base):
    __tablename__ = "property_photos"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    property_id: Mapped[int] = mapped_column(
        Integer,
        index=True
    )

    file_id: Mapped[str] = mapped_column(
        String(300)
    )

    created_at: Mapped[datetime] = mapped_column(
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

ALL_AREAS = "همه مناطق"

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

ACTIVE_PROPERTY_STATUSES = [
    "🟢 فعال",
    "🟡 در مذاکره",
    "فعال",
    "در مذاکره",
]

CLIENT_STATUSES = [
    "فعال",
    "خرید کرده",
    "منصرف شده",
]

ACTIVE_CLIENT_STATUSES = [
    "فعال",
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

PAGE_SIZE = 10

MAX_PROPERTY_PHOTOS = 3


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


class ClientEditForm(StatesGroup):
    client_id = State()
    field = State()
    value = State()


class PhotoForm(StatesGroup):
    property_id = State()


class EventForm(StatesGroup):
    property_id = State()
    event_type = State()
    note = State()


class SearchForm(StatesGroup):
    entity = State()
    query = State()


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
        value = (
            value
            .replace(",", "")
            .replace("٬", "")
        )
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


def display_value(value):
    if value is None:
        return ""

    if isinstance(value, float):
        return money(value)

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


async def callback_access_required(
    callback: CallbackQuery
) -> bool:

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


def one_column(
    items,
    include_cancel=True
):
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


def active_property_filter():
    return Property.status.in_(
        ACTIVE_PROPERTY_STATUSES
    )


def active_client_filter():
    return Client.status.in_(
        ACTIVE_CLIENT_STATUSES
    )


def pagination_keyboard(
    prefix,
    page,
    total_pages
):
    buttons = []

    if page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ قبلی",
                callback_data=f"{prefix}:{page - 1}"
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="noop"
        )
    )

    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="بعدی ➡️",
                callback_data=f"{prefix}:{page + 1}"
            )
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[buttons]
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
            role=(
                "مدیر"
                if is_admin(telegram_id)
                else "مشاور"
            )
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
# DATABASE MIGRATION
# =========================================================

async def migrate():

    async with engine.begin() as conn:

        await conn.run_sync(
            Base.metadata.create_all
        )

        def get_columns(
            sync_conn,
            table_name
        ):
            inspector = inspect(sync_conn)

            return {
                col["name"]
                for col in inspector.get_columns(
                    table_name
                )
            }

        def add_column_if_missing(
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
                    f"ADD COLUMN {column_name} "
                    f"{sql_type}"
                )

        # Properties
        await conn.run_sync(
            lambda sync_conn:
            add_column_if_missing(
                sync_conn,
                "properties",
                "address",
                "TEXT DEFAULT ''"
            )
        )

        await conn.run_sync(
            lambda sync_conn:
            add_column_if_missing(
                sync_conn,
                "properties",
                "unit_floor",
                "INTEGER DEFAULT 0"
            )
        )

        await conn.run_sync(
            lambda sync_conn:
            add_column_if_missing(
                sync_conn,
                "properties",
                "status",
                "VARCHAR(100) DEFAULT '🟢 فعال'"
            )
        )

        await conn.run_sync(
            lambda sync_conn:
            add_column_if_missing(
                sync_conn,
                "properties",
                "transaction_value",
                "FLOAT DEFAULT 0"
            )
        )

        await conn.run_sync(
            lambda sync_conn:
            add_column_if_missing(
                sync_conn,
                "properties",
                "updated_at",
                "TIMESTAMP"
            )
        )

        # Clients
        await conn.run_sync(
            lambda sync_conn:
            add_column_if_missing(
                sync_conn,
                "clients",
                "status",
                "VARCHAR(50) DEFAULT 'فعال'"
            )
        )

        # Backfill old NULL statuses
        await conn.execute(
            Property.__table__.update()
            .where(Property.status.is_(None))
            .values(status="🟢 فعال")
        )

        await conn.execute(
            Client.__table__.update()
            .where(Client.status.is_(None))
            .values(status="فعال")
        )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext
):

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

    if message.text not in [
        "دارد",
        "ندارد"
    ]:
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

    if message.text not in [
        "دارد",
        "ندارد"
    ]:
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
            ["مستأجر دارد", "مستأجر ندارد"],
            ["نامشخص"]
        ])
    )


@dp.message(PropertyForm.tenant)
async def property_tenant(
    message: Message,
    state: FSMContext
):

    valid = [
        "خالی",
        "مالک‌نشین",
        "مستأجر دارد",
        "مستأجر ندارد",
        "نامشخص"
    ]

    if message.text not in valid:
        return

    await state.update_data(
        tenant=message.text
    )

    # =====================================================
    # FIX:
    # مستأجر ندارد → رهن/اجاره پرسیده نمی‌شود
    # =====================================================

    if message.text == "مستأجر ندارد":

        await state.update_data(
            deposit=0,
            rent=0,
            vacancy_date=""
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

        return

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
            "برای اصلاح، ابتدا فایل را ثبت کن؛ "
            "بعد از صفحه فایل می‌توانی هر فیلد را جداگانه تغییر بدهی."
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
            parking_type=data.get(
                "parking_type",
                ""
            ),
            storage=data.get(
                "storage",
                ""
            ),
            tenant=data.get(
                "tenant",
                ""
            ),
            deposit=data.get(
                "deposit",
                0
            ),
            rent=data.get(
                "rent",
                0
            ),
            vacancy_date=data.get(
                "vacancy_date",
                ""
            ),
            document_type=data.get(
                "document_type",
                ""
            ),
            owner_name=data.get(
                "owner_name",
                ""
            ),
            owner_phone=data.get(
                "owner_phone",
                ""
            ),
            description=data.get(
                "description",
                ""
            ),
            status="🟢 فعال",
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
            select(
                func.count(Property.id)
            ).where(
                Property.owner_name ==
                prop.owner_name,
                Property.owner_phone ==
                prop.owner_phone
            )
        )

        owner_count_value = (
            owner_count_result.scalar()
            or 0
        )

    await state.clear()

    await message.answer(
        f"✅ فایل با موفقیت ثبت شد.\n\n"
        f"🔢 کد: {data['code']}\n"
        f"📍 منطقه: {data['area']}\n"
        f"🏠 آدرس: {data['address']}\n"
        f"👤 فایل‌های این مالک/سازنده: "
        f"{owner_count_value}",
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================================================
# PROPERTY LIST - ACTIVE ONLY + PAGINATION
# =========================================================

async def send_property_page(
    target,
    page: int
):

    async with SessionLocal() as session:

        total = await session.scalar(
            select(func.count(Property.id))
            .where(
                active_property_filter()
            )
        )

        total = total or 0

        if total == 0:
            await target.answer(
                "📭 فایل زنده‌ای وجود ندارد."
            )
            return

        total_pages = (
            total + PAGE_SIZE - 1
        ) // PAGE_SIZE

        page = max(
            1,
            min(page, total_pages)
        )

        offset = (
            page - 1
        ) * PAGE_SIZE

        result = await session.execute(
            select(Property)
            .where(
                active_property_filter()
            )
            .order_by(
                Property.created_at.desc()
            )
            .offset(offset)
            .limit(PAGE_SIZE)
        )

        properties = result.scalars().all()

    buttons = [
        [
            InlineKeyboardButton(
                text="🔎 جستجوی فایل",
                callback_data="psearch:start"
            )
        ]
    ]

    for p in properties:
        buttons.append([
            InlineKeyboardButton(
                text=(
                    f"🏠 {p.code} | "
                    f"{p.area} | "
                    f"{money(p.sqm)}م"
                ),
                callback_data=f"popen:{p.id}"
            )
        ])

    buttons.append(
        pagination_keyboard(
            "plist",
            page,
            total_pages
        ).inline_keyboard[0]
    )

    markup = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await target.answer(
        f"📂 **فایل‌های زنده**\n"
        f"صفحه {page} از {total_pages} — "
        f"{total} فایل",
        reply_markup=markup,
        parse_mode="Markdown"
    )


@dp.message(F.text == "🏠 فایل‌ها")
async def property_list(
    message: Message
):

    if not await access_required(message):
        return

    await send_property_page(
        message,
        1
    )


@dp.callback_query(F.data.startswith("plist:"))
async def property_page_callback(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    page = int(
        callback.data.split(":")[1]
    )

    await send_property_page(
        callback.message,
        page
    )

    await callback.answer()


# =========================================================
# PROPERTY SEARCH
# =========================================================

async def send_property_search_page(target, query: str, page: int = 1):
    query = (query or "").strip()

    if not query:
        await send_property_page(target, 1)
        return

    pattern = f"%{query}%"

    async with SessionLocal() as session:
        where_clause = [
            active_property_filter(),
            or_(
                Property.code.ilike(pattern),
                Property.area.ilike(pattern),
                Property.address.ilike(pattern),
                Property.owner_name.ilike(pattern),
                Property.owner_phone.ilike(pattern),
                Property.property_type.ilike(pattern),
                Property.description.ilike(pattern),
            )
        ]

        total = await session.scalar(
            select(func.count(Property.id)).where(*where_clause)
        )
        total = total or 0

        if total == 0:
            await target.answer(
                f"🔎 برای «{query}» فایل فعالی پیدا نشد.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔎 جستجوی دوباره", callback_data="psearch:start")],
                    [InlineKeyboardButton(text="📂 همه فایل‌ها", callback_data="plist:1")],
                ])
            )
            return

        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = max(1, min(page, total_pages))
        offset = (page - 1) * PAGE_SIZE

        result = await session.execute(
            select(Property)
            .where(*where_clause)
            .order_by(Property.created_at.desc())
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        properties = result.scalars().all()

    buttons = [
        [InlineKeyboardButton(text="🔎 تغییر جستجو", callback_data="psearch:start")]
    ]

    for prop in properties:
        buttons.append([
            InlineKeyboardButton(
                text=f"🏠 {prop.code} | {prop.area} | {money(prop.sqm)}م",
                callback_data=f"popen:{prop.id}"
            )
        ])

    nav = pagination_keyboard("psearchpage", page, total_pages).inline_keyboard[0]
    buttons.append(nav)
    buttons.append([
        InlineKeyboardButton(text="📂 همه فایل‌ها", callback_data="plist:1")
    ])

    await target.answer(
        f"🔎 **نتیجه جستجوی فایل**\n"
        f"عبارت: `{query}`\n"
        f"صفحه {page} از {total_pages} — {total} فایل",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "psearch:start")
async def property_search_start(callback: CallbackQuery, state: FSMContext):
    if not await callback_access_required(callback):
        return

    await state.clear()
    await state.update_data(entity="property")
    await state.set_state(SearchForm.query)

    await callback.message.answer(
        "🔎 **جستجوی فایل**\n\n"
        "کد، منطقه، آدرس، نام مالک، شماره مالک، نوع ملک یا توضیحات را وارد کن:",
        reply_markup=keyboard([["❌ لغو"]], include_cancel=False),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(SearchForm.query)
async def search_query(message: Message, state: FSMContext):
    data = await state.get_data()
    entity = data.get("entity")
    query = (message.text or "").strip()

    if entity not in {"property", "client"}:
        return

    if not query:
        await message.answer("عبارت جستجو را وارد کن:")
        return

    await state.clear()

    if entity == "property":
        await state.update_data(property_search_query=query)
        await send_property_search_page(message, query, 1)
    else:
        await state.update_data(client_search_query=query)
        await send_client_search_page(message, query, 1)


@dp.callback_query(F.data.startswith("psearchpage:"))
async def property_search_page_callback(callback: CallbackQuery, state: FSMContext):
    if not await callback_access_required(callback):
        return

    try:
        page = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("صفحه نامعتبر است.", show_alert=True)
        return

    # Query is stored per-user only while a search flow is active. If absent,
    # ask for a fresh search instead of showing an unrelated result.
    data = await state.get_data()
    query = data.get("property_search_query")
    if not query:
        await callback.answer("جستجو منقضی شده؛ دوباره جستجو کن.", show_alert=True)
        await callback.message.answer(
            "🔎 برای جستجوی فایل روی «جستجوی فایل» بزن.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔎 جستجوی فایل", callback_data="psearch:start")]
            ])
        )
        return

    await send_property_search_page(callback.message, query, page)
    await callback.answer()


# =========================================================
# CLIENT SEARCH
# =========================================================

async def send_client_search_page(target, query: str, page: int = 1):
    query = (query or "").strip()

    if not query:
        await send_client_page(target, 1)
        return

    pattern = f"%{query}%"

    async with SessionLocal() as session:
        where_clause = [
            active_client_filter(),
            or_(
                Client.name.ilike(pattern),
                Client.phone.ilike(pattern),
                Client.area.ilike(pattern),
                Client.property_type.ilike(pattern),
                Client.description.ilike(pattern),
            )
        ]

        total = await session.scalar(
            select(func.count(Client.id)).where(*where_clause)
        )
        total = total or 0

        if total == 0:
            await target.answer(
                f"🔎 برای «{query}» مشتری فعالی پیدا نشد.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔎 جستجوی دوباره", callback_data="csearch:start")],
                    [InlineKeyboardButton(text="👤 همه مشتری‌ها", callback_data="clist:1")],
                ])
            )
            return

        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = max(1, min(page, total_pages))
        offset = (page - 1) * PAGE_SIZE

        result = await session.execute(
            select(Client)
            .where(*where_clause)
            .order_by(Client.created_at.desc())
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        clients = result.scalars().all()

    buttons = [
        [InlineKeyboardButton(text="🔎 تغییر جستجو", callback_data="csearch:start")]
    ]

    for client in clients:
        budget = f"{money(client.min_budget)} تا {money(client.max_budget)}"
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {client.name} | 💰 {budget}",
                callback_data=f"copen:{client.id}"
            )
        ])

    buttons.append(
        pagination_keyboard("csearchpage", page, total_pages).inline_keyboard[0]
    )
    buttons.append([
        InlineKeyboardButton(text="👤 همه مشتری‌ها", callback_data="clist:1")
    ])

    await target.answer(
        f"🔎 **نتیجه جستجوی مشتری**\n"
        f"عبارت: `{query}`\n"
        f"صفحه {page} از {total_pages} — {total} مشتری",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "csearch:start")
async def client_search_start(callback: CallbackQuery, state: FSMContext):
    if not await callback_access_required(callback):
        return

    await state.clear()
    await state.update_data(entity="client")
    await state.set_state(SearchForm.query)

    await callback.message.answer(
        "🔎 **جستجوی مشتری**\n\n"
        "نام، شماره، منطقه، نوع ملک یا توضیحات را وارد کن:",
        reply_markup=keyboard([["❌ لغو"]], include_cancel=False),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("csearchpage:"))
async def client_search_page_callback(callback: CallbackQuery, state: FSMContext):
    if not await callback_access_required(callback):
        return

    try:
        page = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("صفحه نامعتبر است.", show_alert=True)
        return

    data = await state.get_data()
    query = data.get("client_search_query")
    if not query:
        await callback.answer("جستجو منقضی شده؛ دوباره جستجو کن.", show_alert=True)
        await callback.message.answer(
            "🔎 برای جستجوی مشتری روی «جستجوی مشتری» بزن.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔎 جستجوی مشتری", callback_data="csearch:start")]
            ])
        )
        return

    await send_client_search_page(callback.message, query, page)
    await callback.answer()


# =========================================================
# PROPERTY DETAIL
# =========================================================

async def send_property_detail(
    target,
    prop_id
):

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id == prop_id
            )
        )

        prop = result.scalar_one_or_none()

        if not prop:
            await target.answer(
                "فایل پیدا نشد."
            )
            return

        result = await session.execute(
            select(
                func.count(Property.id)
            ).where(
                Property.owner_name ==
                prop.owner_name,
                Property.owner_phone ==
                prop.owner_phone
            )
        )

        owner_count_value = (
            result.scalar()
            or 0
        )

        photos_result = await session.execute(
            select(PropertyPhoto)
            .where(
                PropertyPhoto.property_id ==
                prop.id
            )
            .order_by(
                PropertyPhoto.created_at
            )
        )

        photos = photos_result.scalars().all()

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
            f"🅿️ نوع پارکینگ: {prop.parking_type}\n"
            f"📦 انباری: {prop.storage}\n"
            f"👤 وضعیت سکونت: {prop.tenant}\n"
            f"💵 رهن: {money(prop.deposit)}\n"
            f"💵 اجاره: {money(prop.rent)}\n"
            f"📅 تخلیه: {prop.vacancy_date}\n"
            f"📄 سند: {prop.document_type}\n"
            f"👤 مالک: {prop.owner_name}\n"
            f"📞 تلفن: {prop.owner_phone}\n"
            f"📊 وضعیت: {prop.status}\n"
            f"💰 ارزش معامله: "
            f"{money(prop.transaction_value)}\n"
            f"👥 تعداد فایل‌های مالک: "
            f"{owner_count_value}\n"
            f"📷 عکس‌ها: "
            f"{len(photos)}/{MAX_PROPERTY_PHOTOS}\n\n"
            f"📝 {prop.description}"
        )

        markup = InlineKeyboardMarkup(
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
                        text="📷 عکس‌ها",
                        callback_data=f"photos:{prop.id}"
                    ),
                    InlineKeyboardButton(
                        text="👤 فایل‌های مالک",
                        callback_data=f"owner:{prop.id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑 حذف فایل",
                        callback_data=f"deleteprop:{prop.id}"
                    )
                ]
            ]
        )

    await target.answer(
        text,
        reply_markup=markup,
        parse_mode="Markdown"
    )

    if photos:

        chat_id = target.chat.id

        media = [
            InputMediaPhoto(media=p.file_id)
            for p in photos
        ]

        try:
            await bot.send_media_group(
                chat_id,
                media
            )
        except Exception as exc:
            print(
                "SEND PHOTOS ERROR:",
                exc
            )


@dp.callback_query(F.data.startswith("popen:"))
async def property_open_callback(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    prop_id = int(
        callback.data.split(":")[1]
    )

    await send_property_detail(
        callback.message,
        prop_id
    )

    await callback.answer()


# Compatibility with old reply buttons
@dp.message(F.text.startswith("🏠 "))
async def property_open_from_list(
    message: Message
):

    if not await access_required(message):
        return

    code = (
        message.text
        .replace("🏠 ", "")
        .split("|")[0]
        .strip()
    )

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

    await send_property_detail(
        message,
        prop.id
    )


# =========================================================
# PROPERTY EDIT
# =========================================================

EDIT_FIELDS = {
    "code": "🔢 کد",
    "area": "📍 منطقه",
    "address": "🏠 آدرس",
    "sqm": "📐 متراژ",
    "price": "💰 قیمت",
    "property_type": "🏢 نوع ملک",
    "bedrooms": "🛏 خواب",
    "floors": "🏢 کل طبقات",
    "unit_floor": "🏠 طبقه ملک",
    "units_per_floor": "🚪 واحد در طبقه",
    "elevator": "🛗 آسانسور",
    "parking": "🚗 پارکینگ",
    "parking_type": "🅿️ نوع پارکینگ",
    "storage": "📦 انباری",
    "tenant": "👤 وضعیت سکونت",
    "deposit": "💵 رهن",
    "rent": "💵 اجاره",
    "vacancy_date": "📅 تخلیه",
    "document_type": "📄 سند",
    "owner_name": "👤 مالک",
    "owner_phone": "📞 تلفن مالک",
    "description": "📝 توضیحات",
}


def edit_keyboard(
    prop_id
):
    rows = []
    current = []

    for field, label in EDIT_FIELDS.items():

        current.append(
            InlineKeyboardButton(
                text=label,
                callback_data=(
                    f"editfield:{prop_id}:{field}"
                )
            )
        )

        if len(current) == 2:
            rows.append(current)
            current = []

    if current:
        rows.append(current)

    rows.append([
        InlineKeyboardButton(
            text="📷 عکس‌های فایل",
            callback_data=f"photos:{prop_id}"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            text="🗑 حذف فایل",
            callback_data=f"deleteprop:{prop_id}"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            text="⬅️ بازگشت به فایل",
            callback_data=f"popen:{prop_id}"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


@dp.callback_query(F.data.startswith("edit:"))
async def property_edit_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    prop_id = int(
        callback.data.split(":")[1]
    )

    await state.clear()

    await state.update_data(
        property_id=prop_id
    )

    await callback.message.answer(
        "✏️ کدام فیلد را می‌خواهی اصلاح کنی؟",
        reply_markup=edit_keyboard(
            prop_id
        )
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("editfield:"))
async def property_edit_field(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    parts = callback.data.split(":")

    prop_id = int(parts[1])
    field = parts[2]

    if field not in EDIT_FIELDS:
        await callback.answer(
            "فیلد نامعتبر است.",
            show_alert=True
        )
        return

    await state.update_data(
        property_id=prop_id,
        field=field
    )

    await state.set_state(
        EditForm.value
    )

    # Keyboard for known-choice fields
    if field == "area":

        await callback.message.answer(
            "📍 منطقه جدید:",
            reply_markup=one_column(
                AREAS
            )
        )

    elif field == "property_type":

        await callback.message.answer(
            "🏢 نوع ملک جدید:",
            reply_markup=one_column(
                PROPERTY_TYPES
            )
        )

    elif field == "elevator":

        await callback.message.answer(
            "🛗 آسانسور:",
            reply_markup=keyboard([
                ["دارد", "ندارد"]
            ])
        )

    elif field == "parking":

        await callback.message.answer(
            "🚗 پارکینگ:",
            reply_markup=keyboard([
                ["دارد", "ندارد"]
            ])
        )

    elif field == "parking_type":

        await callback.message.answer(
            "🅿️ نوع پارکینگ:",
            reply_markup=keyboard([
                ["اختصاصی", "مشاع"],
                ["مزاحم", "نامشخص"]
            ])
        )

    elif field == "storage":

        await callback.message.answer(
            "📦 انباری:",
            reply_markup=keyboard([
                ["دارد", "ندارد"]
            ])
        )

    elif field == "tenant":

        await callback.message.answer(
            "👤 وضعیت سکونت:",
            reply_markup=keyboard([
                ["خالی", "مالک‌نشین"],
                ["مستأجر دارد", "مستأجر ندارد"],
                ["نامشخص"]
            ])
        )

    elif field == "document_type":

        await callback.message.answer(
            "📄 نوع سند:",
            reply_markup=keyboard([
                ["تک‌برگ", "منگوله‌دار"],
                ["قولنامه‌ای", "نامشخص"]
            ])
        )

    else:

        await callback.message.answer(
            f"مقدار جدید برای "
            f"{EDIT_FIELDS[field]} را وارد کن:"
        )

    await callback.answer()


@dp.message(EditForm.value)
async def property_edit_value(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    prop_id = data.get("property_id")
    field = data.get("field")

    if not prop_id or not field:
        await state.clear()
        return

    raw_value = message.text.strip()

    numeric_fields = {
        "sqm",
        "price",
        "bedrooms",
        "floors",
        "unit_floor",
        "units_per_floor",
        "deposit",
        "rent",
    }

    if field in numeric_fields:

        value = number(raw_value)

        if value < 0:
            await message.answer(
                "❌ مقدار عددی معتبر وارد کن."
            )
            return

        if field in {
            "bedrooms",
            "floors",
            "unit_floor",
            "units_per_floor",
        }:
            value = int(value)

    else:
        value = raw_value

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id == prop_id
            )
        )

        prop = result.scalar_one_or_none()

        if not prop:
            await state.clear()
            await message.answer(
                "فایل پیدا نشد."
            )
            return

        old_value = getattr(
            prop,
            field,
            ""
        )

        # Unique code validation
        if field == "code":

            existing = await session.execute(
                select(Property).where(
                    Property.code == value,
                    Property.id != prop.id
                )
            )

            if existing.scalar_one_or_none():

                await message.answer(
                    "⚠️ این کد قبلاً برای فایل دیگری ثبت شده."
                )
                return

        # If tenant changes to no tenant,
        # automatically clear rent information.
        if field == "tenant" and value == "مستأجر ندارد":

            old_tenant = prop.tenant

            prop.tenant = value
            prop.deposit = 0
            prop.rent = 0
            prop.vacancy_date = ""

            prop.updated_at = datetime.utcnow()

            user = await get_user(
                session,
                message.from_user.id,
                message.from_user.full_name
            )

            note = (
                f"وضعیت سکونت: "
                f"{old_tenant} → {value}\n"
                f"رهن: {money(prop.deposit)}\n"
                f"اجاره: {money(prop.rent)}\n"
                f"تخلیه پاک شد."
            )

            await add_activity(
                session,
                user.id,
                "اصلاح فایل",
                note,
                property_id=prop.id
            )

            await session.commit()

        else:

            setattr(
                prop,
                field,
                value
            )

            prop.updated_at = datetime.utcnow()

            user = await get_user(
                session,
                message.from_user.id,
                message.from_user.full_name
            )

            await add_activity(
                session,
                user.id,
                "اصلاح فایل",
                f"{EDIT_FIELDS[field]}: "
                f"{display_value(old_value)} → "
                f"{display_value(value)}",
                property_id=prop.id
            )

            await session.commit()

    await state.clear()

    await message.answer(
        "✅ فیلد با موفقیت اصلاح شد.",
        reply_markup=main_menu(
            message.from_user.id
        )
    )

    await send_property_detail(
        message,
        prop_id
    )


# =========================================================
# PROPERTY PHOTOS (up to MAX_PROPERTY_PHOTOS)
# =========================================================

@dp.callback_query(F.data.startswith("photos:"))
async def property_photos_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    prop_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:

        count = await session.scalar(
            select(
                func.count(PropertyPhoto.id)
            ).where(
                PropertyPhoto.property_id ==
                prop_id
            )
        )

    count = count or 0

    await state.clear()

    await state.update_data(
        property_id=prop_id
    )

    await state.set_state(
        PhotoForm.property_id
    )

    if count >= MAX_PROPERTY_PHOTOS:

        await callback.message.answer(
            f"📷 این فایل الان {count}/"
            f"{MAX_PROPERTY_PHOTOS} عکس دارد "
            f"(حداکثر رسیده).\n\n"
            f"می‌توانی همه عکس‌های قبلی را پاک کنی "
            f"یا «پایان» را بزن.",
            reply_markup=keyboard([
                ["🗑 پاک کردن همه عکس‌ها"],
                ["پایان"]
            ])
        )

    else:

        await callback.message.answer(
            f"📷 عکس‌های فایل را بفرست "
            f"(حداکثر {MAX_PROPERTY_PHOTOS} عدد).\n"
            f"عکس‌های فعلی: {count}/"
            f"{MAX_PROPERTY_PHOTOS}\n\n"
            f"وقتی تمام شد «پایان» را بفرست.",
            reply_markup=keyboard([
                ["🗑 پاک کردن همه عکس‌ها"],
                ["پایان"]
            ])
        )

    await callback.answer()


@dp.message(PhotoForm.property_id, F.photo)
async def property_photo_receive(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    prop_id = data.get("property_id")

    if not prop_id:
        await state.clear()
        return

    async with SessionLocal() as session:

        count = await session.scalar(
            select(
                func.count(PropertyPhoto.id)
            ).where(
                PropertyPhoto.property_id ==
                prop_id
            )
        )

        count = count or 0

        if count >= MAX_PROPERTY_PHOTOS:

            await message.answer(
                f"⚠️ حداکثر {MAX_PROPERTY_PHOTOS} "
                f"عکس مجاز است. برای پایان "
                f"«پایان» را بفرست."
            )
            return

        file_id = message.photo[-1].file_id

        photo = PropertyPhoto(
            property_id=prop_id,
            file_id=file_id
        )

        session.add(photo)

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "افزودن عکس فایل",
            f"عکس {count + 1}/"
            f"{MAX_PROPERTY_PHOTOS} اضافه شد.",
            property_id=prop_id
        )

        await session.commit()

        count += 1

    if count >= MAX_PROPERTY_PHOTOS:

        await message.answer(
            f"✅ عکس ذخیره شد. "
            f"({count}/{MAX_PROPERTY_PHOTOS})\n"
            f"حداکثر تعداد عکس رسید. "
            f"«پایان» را بزن."
        )

    else:

        await message.answer(
            f"✅ عکس ذخیره شد. "
            f"({count}/{MAX_PROPERTY_PHOTOS})\n"
            f"برای ادامه عکس بعدی را بفرست یا "
            f"«پایان» را بزن."
        )


@dp.message(
    PhotoForm.property_id,
    F.text == "🗑 پاک کردن همه عکس‌ها"
)
async def property_photos_clear(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    prop_id = data.get("property_id")

    if not prop_id:
        await state.clear()
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(PropertyPhoto).where(
                PropertyPhoto.property_id ==
                prop_id
            )
        )

        photos = result.scalars().all()

        for photo in photos:
            await session.delete(photo)

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "حذف عکس‌های فایل",
            "همه عکس‌های فایل پاک شد.",
            property_id=prop_id
        )

        await session.commit()

    await message.answer(
        f"🗑 همه عکس‌ها پاک شد. حالا می‌توانی "
        f"عکس جدید بفرستی (حداکثر "
        f"{MAX_PROPERTY_PHOTOS} عدد) یا «پایان» را بزن."
    )


@dp.message(
    PhotoForm.property_id,
    F.text == "پایان"
)
async def property_photos_done(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    prop_id = data.get("property_id")

    await state.clear()

    await message.answer(
        "✅ ثبت عکس‌ها تمام شد.",
        reply_markup=main_menu(
            message.from_user.id
        )
    )

    if prop_id:
        await send_property_detail(
            message,
            prop_id
        )


# =========================================================
# PROPERTY DELETE
# =========================================================

@dp.callback_query(F.data.startswith("deleteprop:"))
async def property_delete_confirm(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    prop_id = int(
        callback.data.split(":")[1]
    )

    await callback.message.answer(
        "⚠️ آیا از حذف کامل این فایل مطمئنی؟\n"
        "این عملیات قابل بازگشت نیست.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ بله، حذف کن",
                        callback_data=(
                            f"deletepropok:{prop_id}"
                        )
                    ),
                    InlineKeyboardButton(
                        text="❌ انصراف",
                        callback_data=f"popen:{prop_id}"
                    )
                ]
            ]
        )
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("deletepropok:"))
async def property_delete_execute(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    prop_id = int(
        callback.data.split(":")[1]
    )

    await state.clear()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id == prop_id
            )
        )

        prop = result.scalar_one_or_none()

        if not prop:
            await callback.message.answer(
                "فایل پیدا نشد یا قبلاً حذف شده."
            )
            await callback.answer()
            return

        prop_code = prop.code

        photos_result = await session.execute(
            select(PropertyPhoto).where(
                PropertyPhoto.property_id ==
                prop.id
            )
        )

        for photo in photos_result.scalars().all():
            await session.delete(photo)

        user = await get_user(
            session,
            callback.from_user.id,
            callback.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "حذف فایل",
            f"فایل {prop_code} حذف شد."
        )

        await session.delete(prop)

        await session.commit()

    await callback.message.answer(
        f"🗑 فایل {prop_code} حذف شد.",
        reply_markup=main_menu(
            callback.from_user.id
        )
    )

    await callback.answer()


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

    await state.clear()

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
                Property.id ==
                data["property_id"]
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

    value = number(message.text)

    if value < 0:
        await message.answer(
            "ارزش معامله معتبر وارد کن:"
        )
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id ==
                data["property_id"]
            )
        )

        prop = result.scalar_one_or_none()

        if not prop:
            await state.clear()
            return

        old_status = prop.status

        prop.status = (
            "🔵 معامله شد - توسط ما"
        )

        prop.transaction_value = value
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
            f"ارزش معامله: {money(value)}",
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
                Activity.property_id ==
                prop_id
            )
            .order_by(
                Activity.created_at.desc()
            )
            .limit(50)
        )

        activities = result.scalars().all()

    if not activities:

        text = (
            "📜 تاریخچه‌ای ثبت نشده."
        )

    else:

        lines = [
            "📜 تاریخچه فایل:\n"
        ]

        for a in activities:

            lines.append(
                f"• {a.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"⚙️ {a.activity_type}\n"
                f"📝 {a.note}\n"
                f"👤 User ID: {a.user_id}\n"
            )

        text = "\n".join(lines)

    await callback.message.answer(
        text
    )

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

    await state.clear()

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
# OWNER FILES - ACTIVE FILES ONLY
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
                Property.owner_name ==
                prop.owner_name,
                Property.owner_phone ==
                prop.owner_phone,
                active_property_filter()
            )
            .order_by(
                Property.created_at.desc()
            )
        )

        files = result.scalars().all()

    lines = [
        f"👤 فایل‌های زنده {prop.owner_name}:\n"
    ]

    if not files:
        lines.append(
            "📭 فایل زنده‌ای از این مالک وجود ندارد."
        )

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
        reply_markup=one_column([
            *AREAS,
            ALL_AREAS
        ])
    )


@dp.message(ClientForm.area)
async def client_area(
    message: Message,
    state: FSMContext
):

    valid = [
        *AREAS,
        ALL_AREAS
    ]

    if message.text not in valid:

        await message.answer(
            "لطفاً یکی از مناطق یا «همه مناطق» را انتخاب کن."
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
# CLIENT LIST - ACTIVE ONLY + PAGINATION
# =========================================================

async def send_client_page(
    target,
    page: int
):

    async with SessionLocal() as session:

        total = await session.scalar(
            select(func.count(Client.id))
            .where(
                active_client_filter()
            )
        )

        total = total or 0

        if total == 0:
            await target.answer(
                "📭 مشتری زنده‌ای وجود ندارد."
            )
            return

        total_pages = (
            total + PAGE_SIZE - 1
        ) // PAGE_SIZE

        page = max(
            1,
            min(page, total_pages)
        )

        offset = (
            page - 1
        ) * PAGE_SIZE

        result = await session.execute(
            select(Client)
            .where(
                active_client_filter()
            )
            .order_by(
                Client.created_at.desc()
            )
            .offset(offset)
            .limit(PAGE_SIZE)
        )

        clients = result.scalars().all()

    buttons = [
        [
            InlineKeyboardButton(
                text="🔎 جستجوی مشتری",
                callback_data="csearch:start"
            )
        ]
    ]

    for c in clients:

        budget = (
            f"{money(c.min_budget)} تا "
            f"{money(c.max_budget)}"
        )

        buttons.append([
            InlineKeyboardButton(
                text=(
                    f"👤 {c.name} | "
                    f"💰 {budget}"
                ),
                callback_data=f"copen:{c.id}"
            )
        ])

    buttons.append(
        pagination_keyboard(
            "clist",
            page,
            total_pages
        ).inline_keyboard[0]
    )

    await target.answer(
        f"👤 **مشتری‌های زنده**\n"
        f"صفحه {page} از {total_pages} — "
        f"{total} مشتری",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
        parse_mode="Markdown"
    )


@dp.message(F.text == "👤 مشتری‌ها")
async def client_list(
    message: Message
):

    if not await access_required(message):
        return

    await send_client_page(
        message,
        1
    )


@dp.callback_query(F.data.startswith("clist:"))
async def client_page_callback(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    page = int(
        callback.data.split(":")[1]
    )

    await send_client_page(
        callback.message,
        page
    )

    await callback.answer()


# =========================================================
# CLIENT DETAIL
# =========================================================

async def send_client_detail(
    target,
    client_id
):

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client).where(
                Client.id == client_id
            )
        )

        client = result.scalar_one_or_none()

    if not client:
        await target.answer(
            "مشتری پیدا نشد."
        )
        return

    await target.answer(
        f"👤 **{client.name}**\n\n"
        f"📞 تلفن: {client.phone}\n"
        f"📍 منطقه: {client.area}\n"
        f"📐 متراژ: "
        f"{money(client.min_sqm)} تا "
        f"{money(client.max_sqm)}\n"
        f"💰 بودجه: "
        f"{money(client.min_budget)} تا "
        f"{money(client.max_budget)}\n"
        f"🏢 نوع ملک: {client.property_type}\n"
        f"📊 وضعیت: {client.status}\n"
        f"📝 توضیحات: {client.description}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ اصلاح اطلاعات",
                        callback_data=(
                            f"clientedit:{client.id}"
                        )
                    ),
                    InlineKeyboardButton(
                        text="🔄 تغییر وضعیت",
                        callback_data=(
                            f"clientstatus:{client.id}"
                        )
                    )
                ]
            ]
        ),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("copen:"))
async def client_open_callback(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    client_id = int(
        callback.data.split(":")[1]
    )

    await send_client_detail(
        callback.message,
        client_id
    )

    await callback.answer()


# Compatibility
@dp.message(F.text.regexp(r"^👤 .*\|\s*\d+$"))
async def client_detail_old(
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

    await send_client_detail(
        message,
        client_id
    )


# =========================================================
# CLIENT EDIT
# =========================================================

CLIENT_EDIT_FIELDS = {
    "name": "👤 نام",
    "phone": "📞 شماره",
    "area": "📍 منطقه",
    "min_sqm": "📐 حداقل متراژ",
    "max_sqm": "📐 حداکثر متراژ",
    "min_budget": "💰 حداقل بودجه",
    "max_budget": "💰 حداکثر بودجه",
    "property_type": "🏢 نوع ملک",
    "description": "📝 توضیحات",
}


def client_edit_keyboard(
    client_id
):
    rows = []
    current = []

    for field, label in CLIENT_EDIT_FIELDS.items():

        current.append(
            InlineKeyboardButton(
                text=label,
                callback_data=(
                    f"clienteditfield:{client_id}:{field}"
                )
            )
        )

        if len(current) == 2:
            rows.append(current)
            current = []

    if current:
        rows.append(current)

    rows.append([
        InlineKeyboardButton(
            text="🗑 حذف مشتری",
            callback_data=f"deleteclient:{client_id}"
        )
    ])

    rows.append([
        InlineKeyboardButton(
            text="⬅️ بازگشت به مشتری",
            callback_data=f"copen:{client_id}"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


@dp.callback_query(F.data.startswith("clientedit:"))
async def client_edit_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    client_id = int(
        callback.data.split(":")[1]
    )

    await state.clear()

    await state.update_data(
        client_id=client_id
    )

    await callback.message.answer(
        "✏️ کدام فیلد را می‌خواهی اصلاح کنی؟",
        reply_markup=client_edit_keyboard(
            client_id
        )
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("clienteditfield:"))
async def client_edit_field(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    parts = callback.data.split(":")

    client_id = int(parts[1])
    field = parts[2]

    if field not in CLIENT_EDIT_FIELDS:
        await callback.answer(
            "فیلد نامعتبر است.",
            show_alert=True
        )
        return

    await state.update_data(
        client_id=client_id,
        field=field
    )

    await state.set_state(
        ClientEditForm.value
    )

    if field == "area":

        await callback.message.answer(
            "📍 منطقه جدید:",
            reply_markup=one_column([
                *AREAS,
                ALL_AREAS
            ])
        )

    elif field == "property_type":

        await callback.message.answer(
            "🏢 نوع ملک جدید:",
            reply_markup=one_column(
                PROPERTY_TYPES
            )
        )

    else:

        await callback.message.answer(
            f"مقدار جدید برای "
            f"{CLIENT_EDIT_FIELDS[field]} را وارد کن:"
        )

    await callback.answer()


@dp.message(ClientEditForm.value)
async def client_edit_value(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    client_id = data.get("client_id")
    field = data.get("field")

    if not client_id or not field:
        await state.clear()
        return

    raw_value = message.text.strip()

    numeric_fields = {
        "min_sqm",
        "max_sqm",
        "min_budget",
        "max_budget",
    }

    if field in numeric_fields:

        value = number(raw_value)

        if value < 0:
            await message.answer(
                "❌ مقدار عددی معتبر وارد کن."
            )
            return

    elif field == "area":

        if raw_value not in [*AREAS, ALL_AREAS]:
            await message.answer(
                "لطفاً یکی از مناطق یا «همه مناطق» را انتخاب کن."
            )
            return

        value = raw_value

    elif field == "property_type":

        if raw_value not in PROPERTY_TYPES:
            await message.answer(
                "لطفاً نوع ملک را از دکمه‌ها انتخاب کن."
            )
            return

        value = raw_value

    else:
        value = raw_value

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client).where(
                Client.id == client_id
            )
        )

        client = result.scalar_one_or_none()

        if not client:
            await state.clear()
            await message.answer(
                "مشتری پیدا نشد."
            )
            return

        old_value = getattr(
            client,
            field,
            ""
        )

        setattr(
            client,
            field,
            value
        )

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "اصلاح مشتری",
            f"{CLIENT_EDIT_FIELDS[field]}: "
            f"{display_value(old_value)} → "
            f"{display_value(value)}",
            client_id=client.id
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ اطلاعات مشتری اصلاح شد.",
        reply_markup=main_menu(
            message.from_user.id
        )
    )

    await send_client_detail(
        message,
        client_id
    )


# =========================================================
# CLIENT DELETE
# =========================================================

@dp.callback_query(F.data.startswith("deleteclient:"))
async def client_delete_confirm(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    client_id = int(
        callback.data.split(":")[1]
    )

    await callback.message.answer(
        "⚠️ آیا از حذف کامل این مشتری مطمئنی؟\n"
        "این عملیات قابل بازگشت نیست.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ بله، حذف کن",
                        callback_data=(
                            f"deleteclientok:{client_id}"
                        )
                    ),
                    InlineKeyboardButton(
                        text="❌ انصراف",
                        callback_data=f"copen:{client_id}"
                    )
                ]
            ]
        )
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("deleteclientok:"))
async def client_delete_execute(
    callback: CallbackQuery,
    state: FSMContext
):

    if not await callback_access_required(callback):
        return

    client_id = int(
        callback.data.split(":")[1]
    )

    await state.clear()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client).where(
                Client.id == client_id
            )
        )

        client = result.scalar_one_or_none()

        if not client:
            await callback.message.answer(
                "مشتری پیدا نشد یا قبلاً حذف شده."
            )
            await callback.answer()
            return

        client_name = client.name

        user = await get_user(
            session,
            callback.from_user.id,
            callback.from_user.full_name
        )

        await add_activity(
            session,
            user.id,
            "حذف مشتری",
            f"مشتری {client_name} حذف شد."
        )

        await session.delete(client)

        await session.commit()

    await callback.message.answer(
        f"🗑 مشتری {client_name} حذف شد.",
        reply_markup=main_menu(
            callback.from_user.id
        )
    )

    await callback.answer()


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

    await state.clear()

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
                Client.id ==
                data["client_id"]
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

        client_name = client.name

    await state.clear()

    await message.answer(
        f"✅ وضعیت {client_name} شد: "
        f"{message.text}",
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
                active_client_filter()
            )
            .order_by(
                Client.created_at.desc()
            )
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

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client).where(
                Client.id == client_id
            )
        )

        client = result.scalar_one_or_none()

        if not client or client.status != "فعال":

            await message.answer(
                "⚠️ این مشتری دیگر فعال نیست."
            )

            await state.clear()
            return

    await state.update_data(
        client_id=client_id
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property)
            .where(
                active_property_filter()
            )
            .order_by(
                Property.created_at.desc()
            )
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
            f"{p.code} | {p.area} | "
            f"{money(p.sqm)} متر"
            for p in properties
        ])
    )


@dp.message(VisitForm.property_id)
async def visit_property(
    message: Message,
    state: FSMContext
):

    code = (
        message.text
        .split("|")[0]
        .strip()
    )

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

        if prop.status not in ACTIVE_PROPERTY_STATUSES:

            await message.answer(
                "⚠️ این فایل دیگر زنده نیست."
            )
            return

        data = await state.get_data()

        previous_result = await session.execute(
            select(Visit)
            .where(
                Visit.client_id ==
                data["client_id"],
                Visit.property_id ==
                prop.id
            )
            .order_by(
                Visit.visited_at.desc()
            )
        )

        previous = (
            previous_result
            .scalars()
            .first()
        )

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
            f"اقدام بعدی: "
            f"{data['next_action']}",
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
            .join(
                Client,
                Client.id == Visit.client_id
            )
            .join(
                Property,
                Property.id == Visit.property_id
            )
            .where(
                Visit.followup_date != "",
                Client.status.in_(
                    ACTIVE_CLIENT_STATUSES
                ),
                Property.status.in_(
                    ACTIVE_PROPERTY_STATUSES
                )
            )
            .order_by(
                Visit.visited_at.desc()
            )
            .limit(50)
        )

        visits = result.scalars().all()

        if not visits:

            await message.answer(
                "📭 پیگیری فعالی وجود ندارد."
            )
            return

        lines = [
            "📞 **پیگیری‌های فعال**\n"
        ]

        for v in visits:

            client_result = await session.execute(
                select(Client).where(
                    Client.id == v.client_id
                )
            )

            client = (
                client_result
                .scalar_one_or_none()
            )

            prop_result = await session.execute(
                select(Property).where(
                    Property.id ==
                    v.property_id
                )
            )

            prop = (
                prop_result
                .scalar_one_or_none()
            )

            if not client or not prop:
                continue

            lines.append(
                f"👤 {client.name}\n"
                f"🏠 فایل: {prop.code}\n"
                f"📅 پیگیری: {v.followup_date}\n"
                f"➡️ اقدام: {v.next_action}\n"
            )

    await message.answer(
        "\n".join(lines),
        parse_mode="Markdown"
    )


# =========================================================
# SMART MATCHING
# =========================================================

@dp.message(F.text == "🔎 پیشنهاد فایل")
async def matching(message: Message):

    if not await access_required(message):
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(Client)
            .where(active_client_filter())
            .order_by(Client.created_at.desc())
        )
        clients = result.scalars().all()

    if not clients:
        await message.answer("مشتری فعالی وجود ندارد.")
        return

    await message.answer(
        "👤 مشتری را انتخاب کن:",
        reply_markup=one_column([
            f"{c.name} | {c.id}"
            for c in clients
        ])
    )


async def send_matching_page(target, client_id: int, page: int = 1):
    """نمایش صفحه‌بندی‌شده پیشنهادهای فایل برای یک مشتری."""

    async with SessionLocal() as session:
        client_result = await session.execute(
            select(Client).where(Client.id == client_id)
        )
        client = client_result.scalar_one_or_none()

        if not client:
            await target.answer("مشتری پیدا نشد.")
            return

        if client.status not in ACTIVE_CLIENT_STATUSES:
            await target.answer("⚠️ این مشتری دیگر در لیست فعال نیست.")
            return

        prop_result = await session.execute(
            select(Property).where(active_property_filter())
        )
        properties = prop_result.scalars().all()

        visited_result = await session.execute(
            select(Visit.property_id).where(Visit.client_id == client.id)
        )
        visited_ids = set(visited_result.scalars().all())

    scored = []

    for p in properties:
        score = 0

        # بودجه = 40%
        if client.max_budget > 0:
            if p.price <= client.max_budget:
                if client.min_budget <= 0 or p.price >= client.min_budget:
                    score += 40
                else:
                    score += 30
            else:
                difference = (p.price - client.max_budget) / client.max_budget
                if difference <= 0.10:
                    score += 20

        # منطقه = 25%
        if client.area == ALL_AREAS or client.area == p.area:
            score += 25

        # متراژ = 20%
        if client.max_sqm > 0:
            if client.min_sqm <= p.sqm <= client.max_sqm:
                score += 20
            elif abs(p.sqm - client.max_sqm) / client.max_sqm <= 0.10:
                score += 10

        # نوع ملک = 15%
        if client.property_type == p.property_type or client.property_type == "سایر":
            score += 15

        scored.append((score, p, p.id in visited_ids))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        await target.answer("فایل مناسبی پیدا نشد.")
        return

    # صفحه‌بندی پیشنهادها
    page_size = 5
    total = len(scored)
    total_pages = (total + page_size - 1) // page_size
    page = max(1, min(page, total_pages))
    start_index = (page - 1) * page_size
    page_items = scored[start_index:start_index + page_size]

    lines = [
        f"🔎 **پیشنهاد فایل برای {client.name}**\n",
        f"صفحه {page} از {total_pages} — {total} پیشنهاد\n"
    ]

    buttons = []

    for score, prop, visited in page_items:
        visited_text = " | 👀 قبلاً دیده شده" if visited else ""
        lines.append(
            f"🏠 {prop.code}\n"
            f"📍 {prop.area}\n"
            f"📐 {money(prop.sqm)} متر\n"
            f"💰 {money(prop.price)}\n"
            f"🏢 {prop.property_type}\n"
            f"🎯 تطابق: {score}%{visited_text}\n"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"🏠 مشاهده {prop.code}",
                callback_data=f"popen:{prop.id}"
            )
        ])

    # ناوبری صفحات
    nav = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ قبلی",
                callback_data=f"matchpage:{client.id}:{page - 1}"
            )
        )
    nav.append(
        InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="noop"
        )
    )
    if page < total_pages:
        nav.append(
            InlineKeyboardButton(
                text="بعدی ➡️",
                callback_data=f"matchpage:{client.id}:{page + 1}"
            )
        )
    buttons.append(nav)

    await target.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@dp.message(F.text.regexp(r"^.*\|\s*\d+$"))
async def matching_client_selected(message: Message):

    if not await access_required(message):
        return

    try:
        client_id = int(message.text.split("|")[-1].strip())
    except Exception:
        return

    await send_matching_page(message, client_id, 1)


@dp.callback_query(F.data.startswith("matchpage:"))
async def matching_page_callback(callback: CallbackQuery):

    if not await callback_access_required(callback):
        return

    try:
        _, client_id, page = callback.data.split(":")
        client_id = int(client_id)
        page = int(page)
    except Exception:
        await callback.answer("صفحه نامعتبر است.")
        return

    await send_matching_page(callback.message, client_id, page)
    await callback.answer()


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

        user = (
            user_result
            .scalar_one_or_none()
        )

        if not user:
            return

        activity_count = await session.scalar(
            select(func.count(Activity.id))
            .where(
                Activity.user_id ==
                user.id
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

        active_files = await session.scalar(
            select(func.count(Property.id))
            .where(
                Property.created_by ==
                message.from_user.id,
                active_property_filter()
            )
        )

        sold_by_us = await session.scalar(
            select(func.count(Property.id))
            .where(
                Property.created_by ==
                message.from_user.id,
                Property.status ==
                "🔵 معامله شد - توسط ما"
            )
        )

        sold_by_other = await session.scalar(
            select(func.count(Property.id))
            .where(
                Property.created_by ==
                message.from_user.id,
                Property.status ==
                "🟣 معامله شد - توسط دیگری"
            )
        )

        cancelled_files = await session.scalar(
            select(func.count(Property.id))
            .where(
                Property.created_by ==
                message.from_user.id,
                Property.status ==
                "🔴 منصرف شد"
            )
        )

        inactive_files = await session.scalar(
            select(func.count(Property.id))
            .where(
                Property.created_by ==
                message.from_user.id,
                Property.status ==
                "⚫ غیرفعال"
            )
        )

        active_clients = await session.scalar(
            select(func.count(Client.id))
            .where(
                Client.created_by ==
                message.from_user.id,
                Client.status == "فعال"
            )
        )

        bought_clients = await session.scalar(
            select(func.count(Client.id))
            .where(
                Client.created_by ==
                message.from_user.id,
                Client.status == "خرید کرده"
            )
        )

        cancelled_clients = await session.scalar(
            select(func.count(Client.id))
            .where(
                Client.created_by ==
                message.from_user.id,
                Client.status == "منصرف شده"
            )
        )

    await message.answer(
        "📊 **KPI من**\n\n"

        "📁 **فایل‌ها — کل سابقه**\n"
        f"کل ثبت‌شده: {property_count or 0}\n"
        f"🟢 فعال/در مذاکره: {active_files or 0}\n"
        f"🔵 معامله توسط ما: {sold_by_us or 0}\n"
        f"🟣 معامله توسط دیگری: {sold_by_other or 0}\n"
        f"🔴 منصرف‌شده: {cancelled_files or 0}\n"
        f"⚫ غیرفعال: {inactive_files or 0}\n\n"

        "👥 **مشتری‌ها — کل سابقه**\n"
        f"کل ثبت‌شده: {client_count or 0}\n"
        f"🟢 فعال: {active_clients or 0}\n"
        f"🔵 خرید کرده: {bought_clients or 0}\n"
        f"🔴 منصرف شده: {cancelled_clients or 0}\n\n"

        f"👀 بازدید: {visits_count or 0}\n"
        f"📝 فعالیت: {activity_count or 0}",
        parse_mode="Markdown"
    )


# =========================================================
# TEAM KPI
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
            .order_by(
                User.created_at
            )
        )

        users = result.scalars().all()

        lines = [
            "👥 **KPI تیم**\n"
        ]

        for user in users:

            activities = await session.scalar(
                select(func.count(Activity.id))
                .where(
                    Activity.user_id ==
                    user.id
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

            active_files = await session.scalar(
                select(func.count(Property.id))
                .where(
                    Property.created_by ==
                    user.telegram_id,
                    active_property_filter()
                )
            )

            sold_by_us = await session.scalar(
                select(func.count(Property.id))
                .where(
                    Property.created_by ==
                    user.telegram_id,
                    Property.status ==
                    "🔵 معامله شد - توسط ما"
                )
            )

            bought_clients = await session.scalar(
                select(func.count(Client.id))
                .where(
                    Client.created_by ==
                    user.telegram_id,
                    Client.status ==
                    "خرید کرده"
                )
            )

            lines.append(
                f"👤 {user.name}\n"
                f"🏠 کل فایل: {files or 0}\n"
                f"🟢 فایل زنده: {active_files or 0}\n"
                f"🔵 معامله توسط ما: {sold_by_us or 0}\n"
                f"👤 کل مشتری: {clients or 0}\n"
                f"🔵 مشتری خریدکرده: "
                f"{bought_clients or 0}\n"
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
# NOOP CALLBACK
# =========================================================

@dp.callback_query(F.data == "noop")
async def noop_callback(
    callback: CallbackQuery
):

    if not await callback_access_required(callback):
        return

    await callback.answer()


# =========================================================
# UNKNOWN CALLBACK
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
    print(
        "BOT ERROR:",
        event.exception
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    await migrate()

    print(
        "🏙️ Hooman Real Estate CRM started."
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":
    asyncio.run(main())
