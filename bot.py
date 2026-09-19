# bot.py
# 🏙️ شهردار ایران‌زمین | Hooman Real Estate
# Telegram CRM for Real Estate Team
# aiogram 3.x + SQLAlchemy 2.x + SQLite/PostgreSQL

import os
import re
import math
import shutil
import asyncio
from datetime import datetime
from html import escape
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from sqlalchemy import (
    String,
    Integer,
    Text,
    Float,
    DateTime,
    select,
    func,
    or_,
    and_,
    inspect,
    text as sql_text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql+asyncpg://",
            1,
        )
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )
else:
    DATABASE_URL = "sqlite+aiosqlite:///realestate.db"


def parse_ids(value: str):
    result = set()
    for item in (value or "").split(","):
        item = item.strip()
        if item.isdigit():
            result.add(int(item))
    return result


ADMIN_IDS = parse_ids(os.getenv("ADMIN_IDS", ""))
ALLOWED_IDS = parse_ids(os.getenv("ALLOWED_IDS", ""))

PAGE_SIZE = 10

ACTIVE_PROPERTY_STATUSES = {
    "🟢 فعال",
    "🟡 در مذاکره",
    "فعال",
    "در مذاکره",
}

ACTIVE_CLIENT_STATUSES = {
    "فعال",
    "🟢 فعال",
}


# =========================================================
# DATABASE
# =========================================================

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        default="",
    )

    area: Mapped[str] = mapped_column(
        String(100),
        index=True,
        default="",
    )

    address: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    sqm: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    price: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    property_type: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    bedrooms: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    floors: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    unit_floor: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    units_per_floor: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    # 🆕 سال ساخت
    year_built: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    elevator: Mapped[str] = mapped_column(
        String(30),
        default="",
    )

    parking: Mapped[str] = mapped_column(
        String(30),
        default="",
    )

    parking_type: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    storage: Mapped[str] = mapped_column(
        String(30),
        default="",
    )

    tenant: Mapped[str] = mapped_column(
        String(100),
        default="مستأجر ندارد",
    )

    deposit: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    rent: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    vacancy_date: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    document_type: Mapped[str] = mapped_column(
        String(150),
        default="",
    )

    owner_name: Mapped[str] = mapped_column(
        String(150),
        default="",
        index=True,
    )

    owner_phone: Mapped[str] = mapped_column(
        String(50),
        default="",
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    status: Mapped[str] = mapped_column(
        String(100),
        default="🟢 فعال",
        index=True,
    )

    transaction_value: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        default="",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        default="",
        index=True,
    )

    phone: Mapped[str] = mapped_column(
        String(50),
        default="",
        index=True,
    )

    area: Mapped[str] = mapped_column(
        String(100),
        default="همه مناطق",
        index=True,
    )

    min_budget: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    max_budget: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    min_sqm: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    max_sqm: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    property_type: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    # 🆕 بازه سال ساخت موردنظر مشتری
    min_year_built: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    max_year_built: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    description: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    status: Mapped[str] = mapped_column(
        String(100),
        default="فعال",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    client_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    property_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    interest: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    price_reaction: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    property_reaction: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    objection: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    next_action: Mapped[str] = mapped_column(
        String(150),
        default="",
    )

    followup_date: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    note: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    activity_type: Mapped[str] = mapped_column(
        String(150),
        default="",
        index=True,
    )

    entity_type: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    entity_id: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


# 🆕 تاریخچه واقعی تغییرات فایل
class PropertyHistory(Base):
    __tablename__ = "property_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    property_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    field: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    old_value: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    new_value: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =========================================================
# CONSTANTS
# =========================================================

AREAS = [
    "همه مناطق",
    "خانی‌آباد",
    "خانی‌آباد نو",
    "نازی‌آباد",
    "شریعتی",
    "یاخچی‌آباد",
    "شهرک شریعتی",
    "نعمت‌آباد",
    "عبدالمطلب",
    "عباسی",
    "باغ آذری",
    "جوادیه",
    "زمزم",
    "مهرآباد جنوبی",
    "دولت‌آباد",
    "یافت‌آباد",
    "سایر",
]

PROPERTY_TYPES = [
    "آپارتمان",
    "کلنگی",
    "زمین",
    "ویلایی",
    "مغازه",
    "اداری",
    "تجاری",
    "باغ",
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
    "ندارد",
]

PRICE_REACTIONS = [
    "مناسب",
    "قابل مذاکره",
    "گران",
    "خیلی گران",
]

PROPERTY_REACTIONS = [
    "پسندید",
    "متوسط",
    "نپسندید",
]

NEXT_ACTIONS = [
    "پیگیری تلفنی",
    "بازدید مجدد",
    "مذاکره قیمت",
    "ارسال فایل مشابه",
    "انتظار",
    "قرارداد",
    "سایر",
]

EDITABLE_FIELDS = {
    "code": "کد فایل",
    "area": "منطقه",
    "address": "آدرس",
    "sqm": "متراژ",
    "price": "قیمت",
    "property_type": "نوع ملک",
    "bedrooms": "تعداد خواب",
    "floors": "تعداد طبقات",
    "unit_floor": "طبقه واحد",
    "units_per_floor": "واحد در طبقه",
    "year_built": "سال ساخت",
    "elevator": "آسانسور",
    "parking": "پارکینگ",
    "parking_type": "نوع پارکینگ",
    "storage": "انباری",
    "tenant": "مستأجر",
    "deposit": "رهن",
    "rent": "اجاره",
    "vacancy_date": "تاریخ تخلیه",
    "document_type": "نوع سند",
    "owner_name": "نام مالک/سازنده",
    "owner_phone": "تلفن مالک",
    "description": "توضیحات",
}


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
    year_built = State()
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
    confirm = State()


class ClientForm(StatesGroup):
    code = State()
    name = State()
    phone = State()
    area = State()
    min_budget = State()
    max_budget = State()
    min_sqm = State()
    max_sqm = State()
    property_type = State()
    min_year_built = State()
    max_year_built = State()
    description = State()
    confirm = State()


class VisitForm(StatesGroup):
    client_id = State()
    property_id = State()
    duplicate_decision = State()
    interest = State()
    price_reaction = State()
    property_reaction = State()
    objection = State()
    next_action = State()
    followup_date = State()
    note = State()


class EditForm(StatesGroup):
    value = State()


class StatusForm(StatesGroup):
    status = State()
    transaction_value = State()


class ClientStatusForm(StatesGroup):
    status = State()


class EventForm(StatesGroup):
    event_type = State()
    description = State()


class MatchForm(StatesGroup):
    client_id = State()


class SearchForm(StatesGroup):
    kind = State()
    step = State()


# =========================================================
# BOT
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# HELPERS
# =========================================================

def normalize_digits(value):
    if value is None:
        return ""

    table = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )

    return str(value).translate(table)


def number(value):
    value = normalize_digits(value)
    value = value.replace(",", "")
    value = value.replace("٬", "")
    value = value.strip()

    if not value:
        return 0

    try:
        return float(value)
    except Exception:
        return 0


def integer(value):
    try:
        return int(number(value))
    except Exception:
        return 0


def money(value):
    try:
        value = float(value or 0)
        if value == 0:
            return "—"

        if value.is_integer():
            return f"{int(value):,}"

        return f"{value:,.2f}"
    except Exception:
        return "—"


def fmt_date(value):
    if not value:
        return "—"

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")

    return str(value)


def short(value, length=70):
    value = str(value or "")
    if len(value) <= length:
        return value
    return value[:length - 3] + "..."


def is_admin(user_id):
    return user_id in ADMIN_IDS


def is_allowed(user_id):
    # برای تست اولیه، اگر هیچ ID در ENV تعریف نشده باشد،
    # همه مجاز هستند.
    if not ADMIN_IDS and not ALLOWED_IDS:
        return True

    return user_id in ADMIN_IDS or user_id in ALLOWED_IDS


def access_required(message: Message):
    if not is_allowed(message.from_user.id):
        return False
    return True


def callback_access_required(callback: CallbackQuery):
    return is_allowed(callback.from_user.id)


def keyboard(rows, resize=True):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=str(x)) for x in row]
            for row in rows
        ],
        resize_keyboard=resize,
    )


def one_column(items, cancel=True):
    rows = [[str(x)] for x in items]

    if cancel:
        rows.append(["❌ لغو"])

    return keyboard(rows)


def inline(rows):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=str(text_),
                    callback_data=str(data),
                )
                for text_, data in row
            ]
            for row in rows
        ]
    )


def main_menu():
    return keyboard(
        [
            ["➕ ثبت فایل", "📂 فایل‌ها"],
            ["➕ ثبت مشتری", "👥 مشتری‌ها"],
            ["🔎 جستجوی فایل", "🔎 جستجوی مشتری"],
            ["🎯 تطبیق مشتری", "📅 ثبت بازدید"],
            ["🔔 پیگیری‌ها", "📊 KPI من"],
            ["🏠 فایل‌های یک مالک"],
            ["📈 KPI تیم"],
            ["🕘 آخرین فعالیت‌ها"],
        ]
    )


def cancel_keyboard():
    return keyboard([["❌ لغو"]])


async def get_user(session, telegram_id, name=""):
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            name=name or "",
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

    elif name and user.name != name:
        user.name = name
        await session.commit()

    return user


async def add_activity(
    session,
    user_id,
    activity_type,
    entity_type="",
    entity_id=0,
    description="",
):
    activity = Activity(
        user_id=user_id,
        activity_type=activity_type,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )

    session.add(activity)


async def add_history(
    session,
    property_id,
    user_id,
    field,
    old_value,
    new_value,
):
    history = PropertyHistory(
        property_id=property_id,
        user_id=user_id,
        field=field,
        old_value=str(old_value or ""),
        new_value=str(new_value or ""),
    )

    session.add(history)


async def get_property(session, property_id):
    result = await session.execute(
        select(Property).where(Property.id == property_id)
    )
    return result.scalar_one_or_none()


async def get_client(session, client_id):
    result = await session.execute(
        select(Client).where(Client.id == client_id)
    )
    return result.scalar_one_or_none()


def property_is_active(prop):
    return prop and prop.status in ACTIVE_PROPERTY_STATUSES


def client_is_active(client):
    return client and client.status in ACTIVE_CLIENT_STATUSES


def normalize_property_status(status):
    mapping = {
        "فعال": "🟢 فعال",
        "در مذاکره": "🟡 در مذاکره",
        "معامله شد - توسط ما": "🔵 معامله شد - توسط ما",
        "معامله شد - توسط دیگری": "🟣 معامله شد - توسط دیگری",
        "منصرف شد": "🔴 منصرف شد",
        "غیرفعال": "⚫ غیرفعال",
    }

    return mapping.get(status, status)


# =========================================================
# DATABASE MIGRATION + BACKUP
# =========================================================

async def backup_database():
    """
    Backup SQLite before migration.
    PostgreSQL backup is intentionally not performed with
    filesystem copy because DATABASE_URL may be remote.
    """

    if not DATABASE_URL.startswith("sqlite"):
        return

    db_path = DATABASE_URL.split("///", 1)[-1]

    if not os.path.exists(db_path):
        return

    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = backup_dir / f"realestate_before_migration_{stamp}.db"

    try:
        shutil.copy2(db_path, backup_path)
    except Exception:
        pass


async def add_missing_column(
    connection,
    table_name,
    column_name,
    column_sql,
):
    inspector = inspect(connection.sync_connection)

    columns = await asyncio.to_thread(
        inspector.get_columns,
        table_name,
    )

    existing = {c["name"] for c in columns}

    if column_name not in existing:
        await connection.execute(
            sql_text(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {column_sql}"
            )
        )


async def migrate():
    await backup_database()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        # -------------------------------------------------
        # Property migrations
        # -------------------------------------------------

        await add_missing_column(
            connection,
            "properties",
            "address",
            "TEXT DEFAULT ''",
        )

        await add_missing_column(
            connection,
            "properties",
            "unit_floor",
            "INTEGER DEFAULT 0",
        )

        await add_missing_column(
            connection,
            "properties",
            "status",
            "VARCHAR(100) DEFAULT '🟢 فعال'",
        )

        await add_missing_column(
            connection,
            "properties",
            "transaction_value",
            "FLOAT DEFAULT 0",
        )

        await add_missing_column(
            connection,
            "properties",
            "updated_at",
            "DATETIME",
        )

        await add_missing_column(
            connection,
            "properties",
            "year_built",
            "INTEGER DEFAULT 0",
        )

        # -------------------------------------------------
        # Client migrations
        # -------------------------------------------------

        await add_missing_column(
            connection,
            "clients",
            "status",
            "VARCHAR(100) DEFAULT 'فعال'",
        )

        await add_missing_column(
            connection,
            "clients",
            "min_year_built",
            "INTEGER DEFAULT 0",
        )

        await add_missing_column(
            connection,
            "clients",
            "max_year_built",
            "INTEGER DEFAULT 0",
        )

        # -------------------------------------------------
        # Normalize old property statuses
        # -------------------------------------------------

        await connection.execute(
            sql_text(
                """
                UPDATE properties
                SET status = '🟢 فعال'
                WHERE status = 'فعال'
                """
            )
        )

        await connection.execute(
            sql_text(
                """
                UPDATE properties
                SET status = '🟡 در مذاکره'
                WHERE status = 'در مذاکره'
                """
            )
        )

        # -------------------------------------------------
        # Create new history table if needed
        # -------------------------------------------------

        await connection.run_sync(Base.metadata.create_all)


# =========================================================
# START / ACCESS
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    if not access_required(message):
        await message.answer(
            "⛔ دسترسی شما به این ربات فعال نیست."
        )
        return

    async with SessionLocal() as session:
        await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name,
        )

    await message.answer(
        "🏙️ شهردار ایران‌زمین\n"
        "مدیریت فایل، مشتری، بازدید و فروش",
        reply_markup=main_menu(),
    )


@dp.message(Command("id"))
async def show_id(message: Message):
    await message.answer(
        f"Telegram ID شما:\n{message.from_user.id}"
    )


@dp.message(Command("register"))
async def register_user(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین.")
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(
            "فرمت:\n"
            "/register TELEGRAM_ID نام کاربر"
        )
        return

    telegram_id = int(parts[1])
    name = parts[2] if len(parts) > 2 else ""

    async with SessionLocal() as session:
        await get_user(session, telegram_id, name)

    await message.answer("✅ کاربر ثبت شد.")


@dp.message(Command("cancel"))
@dp.message(F.text == "❌ لغو")
async def cancel_all(message: Message, state: FSMContext):
    await state.clear()

    if access_required(message):
        await message.answer(
            "لغو شد.",
            reply_markup=main_menu(),
        )


# =========================================================
# PROPERTY REGISTRATION
# =========================================================

@dp.message(F.text == "➕ ثبت فایل")
async def property_start(message: Message, state: FSMContext):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await state.clear()
    await state.set_state(PropertyForm.code)

    await message.answer(
        "🔢 کد فایل را وارد کنید:",
        reply_markup=cancel_keyboard(),
    )


@dp.message(PropertyForm.code)
async def property_code(message: Message, state: FSMContext):
    code = message.text.strip()

    if not code:
        await message.answer("کد معتبر وارد کنید.")
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(Property).where(Property.code == code)
        )

        if result.scalar_one_or_none():
            await message.answer(
                "⚠️ این کد قبلاً ثبت شده است."
            )
            return

    await state.update_data(code=code)
    await state.set_state(PropertyForm.area)

    await message.answer(
        "📍 منطقه:",
        reply_markup=one_column(AREAS),
    )


@dp.message(PropertyForm.area)
async def property_area(message: Message, state: FSMContext):
    if message.text not in AREAS:
        await message.answer("از گزینه‌های موجود انتخاب کنید.")
        return

    await state.update_data(area=message.text)
    await state.set_state(PropertyForm.address)

    await message.answer(
        "📌 آدرس:",
        reply_markup=cancel_keyboard(),
    )


@dp.message(PropertyForm.address)
async def property_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await state.set_state(PropertyForm.sqm)

    await message.answer("📐 متراژ:")


@dp.message(PropertyForm.sqm)
async def property_sqm(message: Message, state: FSMContext):
    value = number(message.text)

    if value <= 0:
        await message.answer("متراژ معتبر وارد کنید.")
        return

    await state.update_data(sqm=value)
    await state.set_state(PropertyForm.price)

    await message.answer(
        "💰 قیمت کل:",
        reply_markup=cancel_keyboard(),
    )


@dp.message(PropertyForm.price)
async def property_price(message: Message, state: FSMContext):
    value = number(message.text)

    if value <= 0:
        await message.answer("قیمت معتبر وارد کنید.")
        return

    await state.update_data(price=value)
    await state.set_state(PropertyForm.property_type)

    await message.answer(
        "🏠 نوع ملک:",
        reply_markup=one_column(PROPERTY_TYPES),
    )


@dp.message(PropertyForm.property_type)
async def property_type(message: Message, state: FSMContext):
    if message.text not in PROPERTY_TYPES:
        await message.answer("نوع ملک را از گزینه‌ها انتخاب کنید.")
        return

    await state.update_data(property_type=message.text)
    await state.set_state(PropertyForm.bedrooms)

    await message.answer("🛏 تعداد خواب را وارد کنید؛ برای صفر، 0:")


@dp.message(PropertyForm.bedrooms)
async def property_bedrooms(message: Message, state: FSMContext):
    value = integer(message.text)

    if value < 0:
        await message.answer("عدد معتبر وارد کنید.")
        return

    await state.update_data(bedrooms=value)
    await state.set_state(PropertyForm.floors)

    await message.answer("🏢 تعداد طبقات:")


@dp.message(PropertyForm.floors)
async def property_floors(message: Message, state: FSMContext):
    value = integer(message.text)

    if value < 0:
        await message.answer("عدد معتبر وارد کنید.")
        return

    await state.update_data(floors=value)
    await state.set_state(PropertyForm.unit_floor)

    await message.answer("🔢 طبقه واحد:")


@dp.message(PropertyForm.unit_floor)
async def property_unit_floor(message: Message, state: FSMContext):
    value = integer(message.text)

    if value < 0:
        await message.answer("عدد معتبر وارد کنید.")
        return

    await state.update_data(unit_floor=value)
    await state.set_state(PropertyForm.units_per_floor)

    await message.answer("🚪 تعداد واحد در هر طبقه:")


@dp.message(PropertyForm.units_per_floor)
async def property_units_per_floor(
    message: Message,
    state: FSMContext,
):
    value = integer(message.text)

    if value < 0:
        await message.answer("عدد معتبر وارد کنید.")
        return

    await state.update_data(units_per_floor=value)
    await state.set_state(PropertyForm.year_built)

    await message.answer(
        "🏗 سال ساخت را وارد کنید.\n"
        "اگر نامشخص است 0 بزنید:"
    )


@dp.message(PropertyForm.year_built)
async def property_year_built(
    message: Message,
    state: FSMContext,
):
    value = integer(message.text)

    if value != 0 and not 1800 <= value <= 2100:
        await message.answer(
            "سال ساخت باید بین 1800 تا 2100 باشد یا 0."
        )
        return

    await state.update_data(year_built=value)
    await state.set_state(PropertyForm.elevator)

    await message.answer(
        "🛗 آسانسور:",
        reply_markup=one_column(
            ["دارد", "ندارد", "نامشخص"]
        ),
    )


@dp.message(PropertyForm.elevator)
async def property_elevator(
    message: Message,
    state: FSMContext,
):
    if message.text not in ["دارد", "ندارد", "نامشخص"]:
        await message.answer("انتخاب کنید.")
        return

    await state.update_data(elevator=message.text)
    await state.set_state(PropertyForm.parking)

    await message.answer(
        "🚗 پارکینگ:",
        reply_markup=one_column(
            ["دارد", "ندارد", "نامشخص"]
        ),
    )


@dp.message(PropertyForm.parking)
async def property_parking(
    message: Message,
    state: FSMContext,
):
    if message.text not in ["دارد", "ندارد", "نامشخص"]:
        await message.answer("انتخاب کنید.")
        return

    await state.update_data(parking=message.text)

    if message.text == "دارد":
        await state.set_state(PropertyForm.parking_type)
        await message.answer(
            "نوع پارکینگ:",
            reply_markup=one_column(
                [
                    "اختصاصی",
                    "مشاع",
                    "مزاحم",
                    "حیاط",
                    "پارکینگ سندی",
                    "سایر",
                ]
            ),
        )
    else:
        await state.update_data(parking_type="")
        await state.set_state(PropertyForm.storage)

        await message.answer(
            "📦 انباری:",
            reply_markup=one_column(
                ["دارد", "ندارد", "نامشخص"]
            ),
        )


@dp.message(PropertyForm.parking_type)
async def property_parking_type(
    message: Message,
    state: FSMContext,
):
    await state.update_data(parking_type=message.text)
    await state.set_state(PropertyForm.storage)

    await message.answer(
        "📦 انباری:",
        reply_markup=one_column(
            ["دارد", "ندارد", "نامشخص"]
        ),
    )


@dp.message(PropertyForm.storage)
async def property_storage(
    message: Message,
    state: FSMContext,
):
    if message.text not in ["دارد", "ندارد", "نامشخص"]:
        await message.answer("انتخاب کنید.")
        return

    await state.update_data(storage=message.text)
    await state.set_state(PropertyForm.tenant)

    await message.answer(
        "👤 وضعیت مستأجر:",
        reply_markup=one_column(
            [
                "مستأجر ندارد",
                "مستأجر دارد",
            ]
        ),
    )


@dp.message(PropertyForm.tenant)
async def property_tenant(
    message: Message,
    state: FSMContext,
):
    if message.text not in [
        "مستأجر ندارد",
        "مستأجر دارد",
    ]:
        await message.answer("انتخاب کنید.")
        return

    await state.update_data(tenant=message.text)

    if message.text == "مستأجر ندارد":
        await state.update_data(
            deposit=0,
            rent=0,
            vacancy_date="",
        )

        await state.set_state(PropertyForm.document_type)

        await message.answer(
            "📄 نوع سند:",
            reply_markup=one_column(
                [
                    "تک‌برگ",
                    "منگوله‌دار",
                    "قولنامه‌ای",
                    "وکالتی",
                    "سایر",
                ]
            ),
        )

    else:
        await state.set_state(PropertyForm.deposit)

        await message.answer("💵 مبلغ رهن:")


@dp.message(PropertyForm.deposit)
async def property_deposit(
    message: Message,
    state: FSMContext,
):
    value = number(message.text)

    await state.update_data(deposit=value)
    await state.set_state(PropertyForm.rent)

    await message.answer("💵 مبلغ اجاره:")


@dp.message(PropertyForm.rent)
async def property_rent(
    message: Message,
    state: FSMContext,
):
    value = number(message.text)

    await state.update_data(rent=value)
    await state.set_state(PropertyForm.vacancy_date)

    await message.answer(
        "📅 تاریخ تخلیه:",
        reply_markup=keyboard(
            [
                ["ندارد"],
                ["❌ لغو"],
            ]
        ),
    )


@dp.message(PropertyForm.vacancy_date)
async def property_vacancy_date(
    message: Message,
    state: FSMContext,
):
    value = message.text.strip()

    if value == "ندارد":
        value = ""

    await state.update_data(vacancy_date=value)
    await state.set_state(PropertyForm.document_type)

    await message.answer(
        "📄 نوع سند:",
        reply_markup=one_column(
            [
                "تک‌برگ",
                "منگوله‌دار",
                "قولنامه‌ای",
                "وکالتی",
                "سایر",
            ]
        ),
    )


@dp.message(PropertyForm.document_type)
async def property_document_type(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        document_type=message.text
    )

    await state.set_state(PropertyForm.owner_name)

    await message.answer("👤 نام مالک/سازنده:")


@dp.message(PropertyForm.owner_name)
async def property_owner_name(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        owner_name=message.text.strip()
    )

    await state.set_state(PropertyForm.owner_phone)

    await message.answer("📞 تلفن مالک:")


@dp.message(PropertyForm.owner_phone)
async def property_owner_phone(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        owner_phone=normalize_digits(message.text).strip()
    )

    await state.set_state(PropertyForm.description)

    await message.answer(
        "📝 توضیحات فایل:",
        reply_markup=cancel_keyboard(),
    )


@dp.message(PropertyForm.description)
async def property_description(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        description=message.text.strip()
    )

    data = await state.get_data()

    preview = (
        "📋 پیش‌نمایش فایل\n\n"
        f"کد: {data.get('code')}\n"
        f"منطقه: {data.get('area')}\n"
        f"آدرس: {data.get('address')}\n"
        f"متراژ: {money(data.get('sqm'))} متر\n"
        f"قیمت: {money(data.get('price'))}\n"
        f"نوع: {data.get('property_type')}\n"
        f"خواب: {data.get('bedrooms')}\n"
        f"طبقات: {data.get('floors')}\n"
        f"طبقه: {data.get('unit_floor')}\n"
        f"واحد/طبقه: {data.get('units_per_floor')}\n"
        f"سال ساخت: {data.get('year_built') or 'نامشخص'}\n"
        f"آسانسور: {data.get('elevator')}\n"
        f"پارکینگ: {data.get('parking')}\n"
        f"نوع پارکینگ: {data.get('parking_type') or '—'}\n"
        f"انباری: {data.get('storage')}\n"
        f"مستأجر: {data.get('tenant')}\n"
        f"رهن: {money(data.get('deposit'))}\n"
        f"اجاره: {money(data.get('rent'))}\n"
        f"تخلیه: {data.get('vacancy_date') or '—'}\n"
        f"سند: {data.get('document_type')}\n"
        f"مالک: {data.get('owner_name')}\n"
        f"تلفن: {data.get('owner_phone')}\n"
        f"توضیحات: {data.get('description') or '—'}\n"
    )

    await state.set_state(PropertyForm.confirm)

    await message.answer(
        preview,
        reply_markup=keyboard(
            [
                ["✅ ثبت نهایی"],
                ["❌ لغو"],
            ]
        ),
    )


@dp.message(PropertyForm.confirm)
async def property_confirm(
    message: Message,
    state: FSMContext,
):
    if message.text != "✅ ثبت نهایی":
        await state.clear()
        await message.answer(
            "ثبت فایل لغو شد.",
            reply_markup=main_menu(),
        )
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
                "⚠️ این کد قبلاً ثبت شده است."
            )
            return

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name,
        )

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
            year_built=data.get("year_built", 0),
            elevator=data["elevator"],
            parking=data["parking"],
            parking_type=data.get("parking_type", ""),
            storage=data["storage"],
            tenant=data["tenant"],
            deposit=data.get("deposit", 0),
            rent=data.get("rent", 0),
            vacancy_date=data.get("vacancy_date", ""),
            document_type=data["document_type"],
            owner_name=data["owner_name"],
            owner_phone=data["owner_phone"],
            description=data["description"],
            status="🟢 فعال",
            transaction_value=0,
        )

        session.add(prop)
        await session.flush()

        await add_history(
            session,
            prop.id,
            user.id,
            "ثبت فایل",
            "",
            f"فایل {prop.code} ثبت شد",
        )

        await add_activity(
            session,
            user.id,
            "ثبت فایل",
            "property",
            prop.id,
            f"ثبت فایل {prop.code}",
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ فایل با موفقیت ثبت شد.",
        reply_markup=main_menu(),
    )


# =========================================================
# PROPERTY DETAIL
# =========================================================

def property_text(prop: Property):
    return (
        "🏠 جزئیات فایل\n\n"
        f"🔢 کد: {prop.code}\n"
        f"📍 منطقه: {prop.area}\n"
        f"📌 آدرس: {prop.address or '—'}\n"
        f"📐 متراژ: {money(prop.sqm)} متر\n"
        f"💰 قیمت: {money(prop.price)}\n"
        f"🏠 نوع: {prop.property_type}\n"
        f"🛏 خواب: {prop.bedrooms}\n"
        f"🏢 طبقات: {prop.floors}\n"
        f"🔢 طبقه: {prop.unit_floor}\n"
        f"🚪 واحد/طبقه: {prop.units_per_floor}\n"
        f"🏗 سال ساخت: {prop.year_built or 'نامشخص'}\n"
        f"🛗 آسانسور: {prop.elevator or '—'}\n"
        f"🚗 پارکینگ: {prop.parking or '—'}\n"
        f"نوع پارکینگ: {prop.parking_type or '—'}\n"
        f"📦 انباری: {prop.storage or '—'}\n"
        f"👤 مستأجر: {prop.tenant or '—'}\n"
        f"💵 رهن: {money(prop.deposit)}\n"
        f"💵 اجاره: {money(prop.rent)}\n"
        f"📅 تخلیه: {prop.vacancy_date or '—'}\n"
        f"📄 سند: {prop.document_type or '—'}\n"
        f"👤 مالک/سازنده: {prop.owner_name or '—'}\n"
        f"📞 تلفن مالک: {prop.owner_phone or '—'}\n"
        f"📌 وضعیت: {prop.status}\n"
        f"📝 توضیحات: {prop.description or '—'}\n"
    )


def property_detail_keyboard(property_id):
    return inline(
        [
            [
                ("✏️ اصلاح", f"pedit:{property_id}"),
                ("📜 تاریخچه", f"phistory:{property_id}"),
            ],
            [
                ("🔄 تغییر وضعیت", f"pstatus:{property_id}"),
                ("📝 ثبت رویداد", f"pevent:{property_id}"),
            ],
            [
                ("👤 فایل‌های مالک", f"powner:{property_id}"),
            ],
        ]
    )


async def send_property_detail(
    target,
    property_id,
):
    async with SessionLocal() as session:
        prop = await get_property(session, property_id)

        if not prop:
            text_ = "❌ فایل پیدا نشد."
            if isinstance(target, CallbackQuery):
                await target.message.answer(text_)
                await target.answer()
            else:
                await target.answer(text_)
            return

        markup = property_detail_keyboard(prop.id)
        text_ = property_text(prop)

        if isinstance(target, CallbackQuery):
            await target.message.answer(
                text_,
                reply_markup=markup,
            )
            await target.answer()
        else:
            await target.answer(
                text_,
                reply_markup=markup,
            )


# =========================================================
# PROPERTY LIST + PAGINATION
# =========================================================

def pagination_keyboard(
    prefix,
    page,
    total,
):
    pages = max(1, math.ceil(total / PAGE_SIZE))

    rows = []

    nav = []

    if page > 1:
        nav.append(
            ("⬅️ قبلی", f"{prefix}:{page - 1}")
        )

    nav.append(
        (f"صفحه {page} از {pages}", "noop")
    )

    if page < pages:
        nav.append(
            ("بعدی ➡️", f"{prefix}:{page + 1}")
        )

    rows.append(nav)

    return inline(rows)


async def send_property_page(
    target,
    page=1,
    criteria=None,
):
    criteria = criteria or {}

    async with SessionLocal() as session:
        conditions = []

        if criteria.get("area"):
            conditions.append(
                Property.area == criteria["area"]
            )

        if criteria.get("min_price", 0) > 0:
            conditions.append(
                Property.price >= criteria["min_price"]
            )

        if criteria.get("max_price", 0) > 0:
            conditions.append(
                Property.price <= criteria["max_price"]
            )

        if criteria.get("min_sqm", 0) > 0:
            conditions.append(
                Property.sqm >= criteria["min_sqm"]
            )

        if criteria.get("max_sqm", 0) > 0:
            conditions.append(
                Property.sqm <= criteria["max_sqm"]
            )

        if criteria.get("property_type"):
            conditions.append(
                Property.property_type
                == criteria["property_type"]
            )

        if criteria.get("min_year", 0) > 0:
            conditions.append(
                Property.year_built
                >= criteria["min_year"]
            )

        if criteria.get("max_year", 0) > 0:
            conditions.append(
                Property.year_built
                <= criteria["max_year"]
            )

        if criteria.get("owner"):
            conditions.append(
                or_(
                    Property.owner_name.ilike(
                        f"%{criteria['owner']}%"
                    ),
                    Property.owner_phone.ilike(
                        f"%{criteria['owner']}%"
                    ),
                )
            )

        if criteria.get("code"):
            conditions.append(
                Property.code.ilike(
                    f"%{criteria['code']}%"
                )
            )

        if criteria.get("status"):
            conditions.append(
                Property.status == criteria["status"]
            )

        count_stmt = select(
            func.count(Property.id)
        )

        if conditions:
            count_stmt = count_stmt.where(
                and_(*conditions)
            )

        total = (
            await session.execute(count_stmt)
        ).scalar_one()

        pages = max(
            1,
            math.ceil(total / PAGE_SIZE),
        )

        page = max(1, min(page, pages))

        stmt = select(Property)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = (
            stmt.order_by(
                Property.created_at.desc()
            )
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )

        result = await session.execute(stmt)
        properties = result.scalars().all()

        if not properties:
            text_ = "❌ فایلی پیدا نشد."

            if isinstance(target, CallbackQuery):
                await target.message.answer(text_)
                await target.answer()
            else:
                await target.answer(text_)

            return

        text_ = (
            f"📂 فایل‌ها\n"
            f"صفحه {page} از {pages} — {total} فایل\n\n"
        )

        rows = []

        for p in properties:
            text_ += (
                f"🏠 {p.code} | "
                f"{p.area} | "
                f"{money(p.sqm)}م | "
                f"{money(p.price)}\n"
                f"{p.status}\n\n"
            )

            rows.append(
                [
                    (
                        f"{p.code} | {p.area} | "
                        f"{money(p.price)}",
                        f"pview:{p.id}",
                    )
                ]
            )

        nav = pagination_keyboard(
            "plist",
            page,
            total,
        ).inline_keyboard

        rows.extend(nav)

        markup = InlineKeyboardMarkup(
            inline_keyboard=rows
        )

        if isinstance(target, CallbackQuery):
            await target.message.answer(
                text_,
                reply_markup=markup,
            )
            await target.answer()
        else:
            await target.answer(
                text_,
                reply_markup=markup,
            )


@dp.message(F.text == "📂 فایل‌ها")
async def property_list(message: Message):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await send_property_page(message, 1, {})


@dp.callback_query(F.data.startswith("plist:"))
async def property_list_page(callback: CallbackQuery):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    page = int(callback.data.split(":")[1])

    await send_property_page(
        callback,
        page,
        {},
    )


@dp.callback_query(F.data.startswith("pview:"))
async def property_view_callback(callback: CallbackQuery):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    property_id = int(callback.data.split(":")[1])
    await send_property_detail(
        callback,
        property_id,
    )


@dp.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


# =========================================================
# PROPERTY EDIT
# =========================================================

@dp.callback_query(F.data.startswith("pedit:"))
async def property_edit_menu(callback: CallbackQuery):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    property_id = int(callback.data.split(":")[1])

    rows = []

    items = list(EDITABLE_FIELDS.items())

    for i in range(0, len(items), 2):
        row = []

        for key, label in items[i:i + 2]:
            row.append(
                (
                    label,
                    f"efield:{property_id}:{key}",
                )
            )

        rows.append(row)

    rows.append(
        [
            (
                "🔄 تغییر وضعیت",
                f"pstatus:{property_id}",
            )
        ]
    )

    await callback.message.answer(
        "✏️ فیلدی را که می‌خواهید اصلاح شود انتخاب کنید:",
        reply_markup=inline(rows),
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("efield:"))
async def property_edit_field(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    _, property_id, field = callback.data.split(":", 2)

    property_id = int(property_id)

    if field not in EDITABLE_FIELDS:
        await callback.answer("فیلد نامعتبر.", show_alert=True)
        return

    await state.clear()

    await state.update_data(
        edit_property_id=property_id,
        edit_field=field,
    )

    # انتخابی‌ها
    if field == "area":
        await callback.message.answer(
            "منطقه جدید:",
            reply_markup=one_column(AREAS),
        )

    elif field == "property_type":
        await callback.message.answer(
            "نوع ملک:",
            reply_markup=one_column(PROPERTY_TYPES),
        )

    elif field == "elevator":
        await callback.message.answer(
            "آسانسور:",
            reply_markup=one_column(
                ["دارد", "ندارد", "نامشخص"]
            ),
        )

    elif field == "parking":
        await callback.message.answer(
            "پارکینگ:",
            reply_markup=one_column(
                ["دارد", "ندارد", "نامشخص"]
            ),
        )

    elif field == "storage":
        await callback.message.answer(
            "انباری:",
            reply_markup=one_column(
                ["دارد", "ندارد", "نامشخص"]
            ),
        )

    elif field == "tenant":
        await callback.message.answer(
            "وضعیت مستأجر:",
            reply_markup=one_column(
                [
                    "مستأجر ندارد",
                    "مستأجر دارد",
                ]
            ),
        )

    else:
        await callback.message.answer(
            f"مقدار جدید «{EDITABLE_FIELDS[field]}» را وارد کنید:",
            reply_markup=cancel_keyboard(),
        )

    await state.set_state(EditForm.value)
    await callback.answer()


@dp.message(EditForm.value)
async def property_edit_save(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    property_id = data.get("edit_property_id")
    field = data.get("edit_field")

    if not property_id or not field:
        await state.clear()
        await message.answer(
            "❌ عملیات ویرایش نامعتبر است.",
            reply_markup=main_menu(),
        )
        return

    raw = message.text.strip()

    if raw == "❌ لغو":
        await state.clear()
        await message.answer(
            "ویرایش لغو شد.",
            reply_markup=main_menu(),
        )
        return

    async with SessionLocal() as session:
        prop = await get_property(
            session,
            property_id,
        )

        if not prop:
            await state.clear()
            await message.answer("❌ فایل پیدا نشد.")
            return

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name,
        )

        old_value = getattr(prop, field)

        new_value = raw

        numeric_fields = {
            "sqm",
            "price",
            "deposit",
            "rent",
        }

        integer_fields = {
            "bedrooms",
            "floors",
            "unit_floor",
            "units_per_floor",
            "year_built",
        }

        if field in numeric_fields:
            new_value = number(raw)

        elif field in integer_fields:
            new_value = integer(raw)

            if field == "year_built":
                if new_value != 0 and not 1800 <= new_value <= 2100:
                    await message.answer(
                        "سال ساخت باید بین 1800 تا 2100 یا 0 باشد."
                    )
                    return

        if field == "code":
            result = await session.execute(
                select(Property).where(
                    Property.code == str(new_value),
                    Property.id != prop.id,
                )
            )

            if result.scalar_one_or_none():
                await message.answer(
                    "⚠️ این کد قبلاً استفاده شده است."
                )
                return

        setattr(prop, field, new_value)

        # منطق مستأجر
        if field == "tenant" and new_value == "مستأجر ندارد":
            prop.deposit = 0
            prop.rent = 0
            prop.vacancy_date = ""

        if str(old_value) != str(new_value):
            await add_history(
                session,
                prop.id,
                user.id,
                EDITABLE_FIELDS[field],
                old_value,
                new_value,
            )

            await add_activity(
                session,
                user.id,
                "اصلاح فایل",
                "property",
                prop.id,
                (
                    f"{EDITABLE_FIELDS[field]}: "
                    f"{old_value} → {new_value}"
                ),
            )

        prop.updated_at = datetime.utcnow()

        await session.commit()

        text_ = property_text(prop)

    await state.clear()

    await message.answer(
        "✅ اصلاح انجام شد.\n\n" + text_,
        reply_markup=property_detail_keyboard(
            property_id
        ),
    )


# =========================================================
# PROPERTY STATUS
# =========================================================

@dp.callback_query(F.data.startswith("pstatus:"))
async def property_status_menu(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    property_id = int(callback.data.split(":")[1])

    await state.clear()
    await state.update_data(
        status_property_id=property_id
    )
    await state.set_state(StatusForm.status)

    await callback.message.answer(
        "وضعیت جدید فایل:",
        reply_markup=one_column(
            STATUSES,
            cancel=True,
        ),
    )

    await callback.answer()


@dp.message(StatusForm.status)
async def property_status_select(
    message: Message,
    state: FSMContext,
):
    if message.text not in STATUSES:
        await message.answer("وضعیت معتبر انتخاب کنید.")
        return

    data = await state.get_data()

    await state.update_data(
        new_status=message.text
    )

    if message.text == "🔵 معامله شد - توسط ما":
        await state.set_state(
            StatusForm.transaction_value
        )

        await message.answer(
            "💰 ارزش معامله را وارد کنید:"
        )

    else:
        await save_property_status(
            message,
            state,
            data.get("new_status"),
            0,
        )


@dp.message(StatusForm.transaction_value)
async def property_transaction_value(
    message: Message,
    state: FSMContext,
):
    value = number(message.text)

    if value < 0:
        await message.answer("عدد معتبر وارد کنید.")
        return

    data = await state.get_data()

    await save_property_status(
        message,
        state,
        data.get("new_status"),
        value,
    )


async def save_property_status(
    message,
    state,
    new_status,
    transaction_value,
):
    data = await state.get_data()

    property_id = data.get("status_property_id")

    async with SessionLocal() as session:
        prop = await get_property(
            session,
            property_id,
        )

        if not prop:
            await state.clear()
            await message.answer("❌ فایل پیدا نشد.")
            return

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name,
        )

        old_status = prop.status
        old_transaction = prop.transaction_value

        prop.status = normalize_property_status(
            new_status
        )

        if prop.status == "🔵 معامله شد - توسط ما":
            prop.transaction_value = transaction_value
        else:
            prop.transaction_value = 0

        await add_history(
            session,
            prop.id,
            user.id,
            "وضعیت",
            old_status,
            prop.status,
        )

        if old_transaction != prop.transaction_value:
            await add_history(
                session,
                prop.id,
                user.id,
                "ارزش معامله",
                old_transaction,
                prop.transaction_value,
            )

        await add_activity(
            session,
            user.id,
            "تغییر وضعیت فایل",
            "property",
            prop.id,
            f"{old_status} → {prop.status}",
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ وضعیت فایل تغییر کرد.",
        reply_markup=main_menu(),
    )


# =========================================================
# PROPERTY HISTORY
# =========================================================

@dp.callback_query(F.data.startswith("phistory:"))
async def property_history(
    callback: CallbackQuery,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    property_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        prop = await get_property(
            session,
            property_id,
        )

        if not prop:
            await callback.answer(
                "فایل پیدا نشد.",
                show_alert=True,
            )
            return

        result = await session.execute(
            select(PropertyHistory)
            .where(
                PropertyHistory.property_id
                == property_id
            )
            .order_by(
                PropertyHistory.created_at.desc()
            )
            .limit(50)
        )

        rows = result.scalars().all()

        text_ = (
            f"📜 تاریخچه فایل {prop.code}\n\n"
        )

        if not rows:
            text_ += "هنوز تاریخچه‌ای ثبت نشده است."
        else:
            user_cache = {}

            for h in rows:
                if h.user_id not in user_cache:
                    user_result = await session.execute(
                        select(User).where(
                            User.id == h.user_id
                        )
                    )

                    u = user_result.scalar_one_or_none()

                    user_cache[h.user_id] = (
                        u.name if u else str(h.user_id)
                    )

                text_ += (
                    f"🕒 {fmt_date(h.created_at)}\n"
                    f"👤 {user_cache[h.user_id]}\n"
                    f"📌 {h.field}\n"
                    f"⬅️ {short(h.old_value, 100)}\n"
                    f"➡️ {short(h.new_value, 100)}\n\n"
                )

        await callback.message.answer(text_)
        await callback.answer()


# =========================================================
# PROPERTY EVENTS
# =========================================================

@dp.callback_query(F.data.startswith("pevent:"))
async def property_event_start(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    property_id = int(callback.data.split(":")[1])

    await state.clear()
    await state.update_data(
        event_property_id=property_id
    )

    await state.set_state(EventForm.event_type)

    await callback.message.answer(
        "نوع رویداد:",
        reply_markup=one_column(
            [
                "تماس با مالک",
                "بازدید",
                "مذاکره",
                "تغییر قیمت",
                "قرارداد",
                "پیگیری",
                "سایر",
            ]
        ),
    )

    await callback.answer()


@dp.message(EventForm.event_type)
async def property_event_type(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        event_type=message.text
    )

    await state.set_state(EventForm.description)

    await message.answer(
        "توضیح رویداد:"
    )


@dp.message(EventForm.description)
async def property_event_save(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    async with SessionLocal() as session:
        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name,
        )

        await add_activity(
            session,
            user.id,
            data["event_type"],
            "property",
            data["event_property_id"],
            message.text.strip(),
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ رویداد ثبت شد.",
        reply_markup=main_menu(),
    )


# =========================================================
# OWNER FILES
# =========================================================

@dp.message(F.text == "🏠 فایل‌های یک مالک")
async def owner_files_start(
    message: Message,
):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await message.answer(
        "نام مالک یا شماره تلفن را وارد کنید:",
        reply_markup=cancel_keyboard(),
    )


@dp.callback_query(F.data.startswith("powner:"))
async def owner_files_from_property(
    callback: CallbackQuery,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    property_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        prop = await get_property(session, property_id)

        if not prop:
            await callback.answer(
                "فایل پیدا نشد.",
                show_alert=True,
            )
            return

        await send_owner_files(
            callback.message,
            prop.owner_name,
            prop.owner_phone,
        )

    await callback.answer()


async def send_owner_files(
    target,
    owner_name,
    owner_phone,
):
    async with SessionLocal() as session:
        conditions = []

        if owner_name:
            conditions.append(
                Property.owner_name == owner_name
            )

        if owner_phone:
            conditions.append(
                Property.owner_phone == owner_phone
            )

        if not conditions:
            await target.answer("مالک مشخص نیست.")
            return

        result = await session.execute(
            select(Property)
            .where(
                and_(
                    or_(*conditions),
                    Property.status.in_(
                        list(ACTIVE_PROPERTY_STATUSES)
                    ),
                )
            )
            .order_by(
                Property.created_at.desc()
            )
        )

        properties = result.scalars().all()

        if not properties:
            await target.answer(
                "❌ فایل زنده‌ای برای این مالک پیدا نشد."
            )
            return

        text_ = (
            f"🏠 فایل‌های زنده مالک\n"
            f"{owner_name or '—'}\n"
            f"{owner_phone or '—'}\n\n"
            f"تعداد: {len(properties)}\n\n"
        )

        rows = []

        for p in properties:
            text_ += (
                f"{p.code} | {p.area} | "
                f"{money(p.sqm)}م | "
                f"{money(p.price)}\n"
            )

            rows.append(
                [
                    (
                        f"{p.code} | {p.area}",
                        f"pview:{p.id}",
                    )
                ]
            )

        await target.answer(
            text_,
            reply_markup=inline(rows),
        )


@dp.message(F.text)
async def owner_files_text_fallback(message: Message):
    """
    عمداً پایین‌تر از handlerهای FSM قرار گرفته.
    برای متن عادی که با نام/شماره مالک ارسال شود.
    """

    if not access_required(message):
        return

    # پیام‌های منوی اصلی
    menu_values = {
        "➕ ثبت فایل",
        "📂 فایل‌ها",
        "➕ ثبت مشتری",
        "👥 مشتری‌ها",
        "🔎 جستجوی فایل",
        "🔎 جستجوی مشتری",
        "🎯 تطبیق مشتری",
        "📅 ثبت بازدید",
        "🔔 پیگیری‌ها",
        "📊 KPI من",
        "🏠 فایل‌های یک مالک",
        "📈 KPI تیم",
        "🕘 آخرین فعالیت‌ها",
    }

    if message.text in menu_values:
        return

    # اگر رشته شبیه تلفن باشد یا طول آن منطقی باشد،
    # به عنوان جستجوی مالک هم قابل استفاده است.
    if (
        any(ch.isdigit() for ch in message.text)
        or len(message.text.strip()) >= 3
    ):
        await send_owner_files(
            message,
            message.text.strip(),
            message.text.strip(),
        )


# =========================================================
# CLIENT REGISTRATION
# =========================================================

@dp.message(F.text == "➕ ثبت مشتری")
async def client_start(
    message: Message,
    state: FSMContext,
):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await state.clear()
    await state.set_state(ClientForm.code)

    await message.answer(
        "🔢 کد مشتری:",
        reply_markup=cancel_keyboard(),
    )


@dp.message(ClientForm.code)
async def client_code(
    message: Message,
    state: FSMContext,
):
    code = message.text.strip()

    async with SessionLocal() as session:
        result = await session.execute(
            select(Client).where(
                Client.code == code
            )
        )

        if result.scalar_one_or_none():
            await message.answer(
                "⚠️ این کد قبلاً ثبت شده."
            )
            return

    await state.update_data(code=code)
    await state.set_state(ClientForm.name)

    await message.answer("👤 نام مشتری:")


@dp.message(ClientForm.name)
async def client_name(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        name=message.text.strip()
    )

    await state.set_state(ClientForm.phone)

    await message.answer("📞 تلفن مشتری:")


@dp.message(ClientForm.phone)
async def client_phone(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        phone=normalize_digits(message.text)
    )

    await state.set_state(ClientForm.area)

    await message.answer(
        "📍 منطقه موردنظر:",
        reply_markup=one_column(AREAS),
    )


@dp.message(ClientForm.area)
async def client_area(
    message: Message,
    state: FSMContext,
):
    if message.text not in AREAS:
        await message.answer("از گزینه‌ها انتخاب کنید.")
        return

    await state.update_data(
        area=message.text
    )

    await state.set_state(ClientForm.min_budget)

    await message.answer(
        "💰 حداقل بودجه:\n"
        "اگر محدودیت ندارد 0 بزنید."
    )


@dp.message(ClientForm.min_budget)
async def client_min_budget(
    message: Message,
    state: FSMContext,
):
    value = number(message.text)

    await state.update_data(
        min_budget=value
    )

    await state.set_state(ClientForm.max_budget)

    await message.answer(
        "💰 حداکثر بودجه:\n"
        "اگر محدودیت ندارد 0 بزنید."
    )


@dp.message(ClientForm.max_budget)
async def client_max_budget(
    message: Message,
    state: FSMContext,
):
    value = number(message.text)

    await state.update_data(
        max_budget=value
    )

    await state.set_state(ClientForm.min_sqm)

    await message.answer(
        "📐 حداقل متراژ:\n"
        "اگر محدودیت ندارد 0 بزنید."
    )


@dp.message(ClientForm.min_sqm)
async def client_min_sqm(
    message: Message,
    state: FSMContext,
):
    value = number(message.text)

    await state.update_data(
        min_sqm=value
    )

    await state.set_state(ClientForm.max_sqm)

    await message.answer(
        "📐 حداکثر متراژ:\n"
        "اگر محدودیت ندارد 0 بزنید."
    )


@dp.message(ClientForm.max_sqm)
async def client_max_sqm(
    message: Message,
    state: FSMContext,
):
    value = number(message.text)

    await state.update_data(
        max_sqm=value
    )

    await state.set_state(ClientForm.property_type)

    await message.answer(
        "🏠 نوع ملک:",
        reply_markup=one_column(
            PROPERTY_TYPES + ["همه انواع"]
        ),
    )


@dp.message(ClientForm.property_type)
async def client_property_type(
    message: Message,
    state: FSMContext,
):
    if (
        message.text not in PROPERTY_TYPES
        and message.text != "همه انواع"
    ):
        await message.answer("نوع ملک را انتخاب کنید.")
        return

    value = (
        ""
        if message.text == "همه انواع"
        else message.text
    )

    await state.update_data(
        property_type=value
    )

    await state.set_state(
        ClientForm.min_year_built
    )

    await message.answer(
        "🏗 حداقل سال ساخت:\n"
        "برای بدون محدودیت 0 بزنید."
    )


@dp.message(ClientForm.min_year_built)
async def client_min_year(
    message: Message,
    state: FSMContext,
):
    value = integer(message.text)

    if value != 0 and not 1800 <= value <= 2100:
        await message.answer(
            "سال ساخت معتبر وارد کنید یا 0."
        )
        return

    await state.update_data(
        min_year_built=value
    )

    await state.set_state(
        ClientForm.max_year_built
    )

    await message.answer(
        "🏗 حداکثر سال ساخت:\n"
        "برای بدون محدودیت 0 بزنید."
    )


@dp.message(ClientForm.max_year_built)
async def client_max_year(
    message: Message,
    state: FSMContext,
):
    value = integer(message.text)

    if value != 0 and not 1800 <= value <= 2100:
        await message.answer(
            "سال ساخت معتبر وارد کنید یا 0."
        )
        return

    await state.update_data(
        max_year_built=value
    )

    await state.set_state(
        ClientForm.description
    )

    await message.answer(
        "📝 توضیحات مشتری:"
    )


@dp.message(ClientForm.description)
async def client_description(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        description=message.text.strip()
    )

    data = await state.get_data()

    preview = (
        "👤 پیش‌نمایش مشتری\n\n"
        f"کد: {data.get('code')}\n"
        f"نام: {data.get('name')}\n"
        f"تلفن: {data.get('phone')}\n"
        f"منطقه: {data.get('area')}\n"
        f"بودجه: {money(data.get('min_budget'))}"
        f" تا {money(data.get('max_budget'))}\n"
        f"متراژ: {money(data.get('min_sqm'))}"
        f" تا {money(data.get('max_sqm'))}\n"
        f"نوع: {data.get('property_type') or 'همه انواع'}\n"
        f"سال ساخت: "
        f"{data.get('min_year_built') or 'بدون محدودیت'}"
        f" تا "
        f"{data.get('max_year_built') or 'بدون محدودیت'}\n"
        f"توضیحات: {data.get('description') or '—'}"
    )

    await state.set_state(ClientForm.confirm)

    await message.answer(
        preview,
        reply_markup=keyboard(
            [
                ["✅ ثبت نهایی"],
                ["❌ لغو"],
            ]
        ),
    )


@dp.message(ClientForm.confirm)
async def client_confirm(
    message: Message,
    state: FSMContext,
):
    if message.text != "✅ ثبت نهایی":
        await state.clear()
        await message.answer(
            "ثبت مشتری لغو شد.",
            reply_markup=main_menu(),
        )
        return

    data = await state.get_data()

    async with SessionLocal() as session:
        result = await session.execute(
            select(Client).where(
                Client.code == data["code"]
            )
        )

        if result.scalar_one_or_none():
            await message.answer(
                "⚠️ این کد قبلاً ثبت شده."
            )
            return

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name,
        )

        client = Client(
            code=data["code"],
            name=data["name"],
            phone=data["phone"],
            area=data["area"],
            min_budget=data.get("min_budget", 0),
            max_budget=data.get("max_budget", 0),
            min_sqm=data.get("min_sqm", 0),
            max_sqm=data.get("max_sqm", 0),
            property_type=data.get("property_type", ""),
            min_year_built=data.get(
                "min_year_built",
                0,
            ),
            max_year_built=data.get(
                "max_year_built",
                0,
            ),
            description=data.get(
                "description",
                "",
            ),
            status="فعال",
        )

        session.add(client)
        await session.flush()

        await add_activity(
            session,
            user.id,
            "ثبت مشتری",
            "client",
            client.id,
            f"ثبت مشتری {client.code}",
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ مشتری ثبت شد.",
        reply_markup=main_menu(),
    )


# =========================================================
# CLIENT LIST + PAGINATION
# =========================================================

async def send_client_page(
    target,
    page=1,
    criteria=None,
):
    criteria = criteria or {}

    async with SessionLocal() as session:
        conditions = []

        if criteria.get("active_only"):
            conditions.append(
                Client.status.in_(
                    list(ACTIVE_CLIENT_STATUSES)
                )
            )

        if criteria.get("status"):
            conditions.append(
                Client.status
                == criteria["status"]
            )

        if criteria.get("area"):
            conditions.append(
                Client.area == criteria["area"]
            )

        if criteria.get("min_budget", 0) > 0:
            conditions.append(
                Client.max_budget
                >= criteria["min_budget"]
            )

        if criteria.get("max_budget", 0) > 0:
            conditions.append(
                Client.min_budget
                <= criteria["max_budget"]
            )

        if criteria.get("min_sqm", 0) > 0:
            conditions.append(
                Client.max_sqm
                >= criteria["min_sqm"]
            )

        if criteria.get("max_sqm", 0) > 0:
            conditions.append(
                Client.min_sqm
                <= criteria["max_sqm"]
            )

        if criteria.get("property_type"):
            conditions.append(
                Client.property_type
                == criteria["property_type"]
            )

        if criteria.get("name"):
            conditions.append(
                or_(
                    Client.name.ilike(
                        f"%{criteria['name']}%"
                    ),
                    Client.phone.ilike(
                        f"%{criteria['name']}%"
                    ),
                    Client.code.ilike(
                        f"%{criteria['name']}%"
                    ),
                )
            )

        count_stmt = select(
            func.count(Client.id)
        )

        if conditions:
            count_stmt = count_stmt.where(
                and_(*conditions)
            )

        total = (
            await session.execute(count_stmt)
        ).scalar_one()

        pages = max(
            1,
            math.ceil(total / PAGE_SIZE),
        )

        page = max(1, min(page, pages))

        stmt = select(Client)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = (
            stmt.order_by(
                Client.created_at.desc()
            )
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )

        result = await session.execute(stmt)

        clients = result.scalars().all()

        if not clients:
            text_ = "❌ مشتری‌ای پیدا نشد."

            if isinstance(target, CallbackQuery):
                await target.message.answer(text_)
                await target.answer()
            else:
                await target.answer(text_)

            return

        text_ = (
            f"👥 مشتری‌ها\n"
            f"صفحه {page} از {pages} — {total} مشتری\n\n"
        )

        rows = []

        for c in clients:
            text_ += (
                f"👤 {c.code} | {c.name}\n"
                f"📍 {c.area} | "
                f"💰 {money(c.max_budget)} | "
                f"📐 {money(c.max_sqm)}م\n"
                f"وضعیت: {c.status}\n\n"
            )

            rows.append(
                [
                    (
                        f"{c.code} | {c.name}",
                        f"cview:{c.id}",
                    )
                ]
            )

        nav = pagination_keyboard(
            "clist",
            page,
            total,
        ).inline_keyboard

        rows.extend(nav)

        markup = InlineKeyboardMarkup(
            inline_keyboard=rows
        )

        if isinstance(target, CallbackQuery):
            await target.message.answer(
                text_,
                reply_markup=markup,
            )
            await target.answer()
        else:
            await target.answer(
                text_,
                reply_markup=markup,
            )


@dp.message(F.text == "👥 مشتری‌ها")
async def client_list(message: Message):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await send_client_page(
        message,
        1,
        {"active_only": True},
    )


@dp.callback_query(F.data.startswith("clist:"))
async def client_list_page(
    callback: CallbackQuery,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    page = int(callback.data.split(":")[1])

    await send_client_page(
        callback,
        page,
        {"active_only": True},
    )


# =========================================================
# CLIENT DETAIL
# =========================================================

def client_text(client: Client):
    return (
        "👤 جزئیات مشتری\n\n"
        f"🔢 کد: {client.code}\n"
        f"👤 نام: {client.name}\n"
        f"📞 تلفن: {client.phone}\n"
        f"📍 منطقه: {client.area}\n"
        f"💰 بودجه: {money(client.min_budget)}"
        f" تا {money(client.max_budget)}\n"
        f"📐 متراژ: {money(client.min_sqm)}"
        f" تا {money(client.max_sqm)}\n"
        f"🏠 نوع ملک: "
        f"{client.property_type or 'همه انواع'}\n"
        f"🏗 سال ساخت: "
        f"{client.min_year_built or 'بدون محدودیت'}"
        f" تا "
        f"{client.max_year_built or 'بدون محدودیت'}\n"
        f"📌 وضعیت: {client.status}\n"
        f"📝 توضیحات: {client.description or '—'}"
    )


@dp.callback_query(F.data.startswith("cview:"))
async def client_view(
    callback: CallbackQuery,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    client_id = int(callback.data.split(":")[1])

    async with SessionLocal() as session:
        client = await get_client(
            session,
            client_id,
        )

        if not client:
            await callback.answer(
                "مشتری پیدا نشد.",
                show_alert=True,
            )
            return

        await callback.message.answer(
            client_text(client),
            reply_markup=inline(
                [
                    [
                        (
                            "🎯 تطبیق فایل",
                            f"match:{client.id}",
                        )
                    ],
                    [
                        (
                            "📅 ثبت بازدید",
                            f"visitclient:{client.id}",
                        )
                    ],
                    [
                        (
                            "🔄 تغییر وضعیت",
                            f"cstatus:{client.id}",
                        )
                    ],
                ]
            ),
        )

    await callback.answer()


# =========================================================
# CLIENT STATUS
# =========================================================

@dp.callback_query(F.data.startswith("cstatus:"))
async def client_status_menu(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    client_id = int(callback.data.split(":")[1])

    await state.clear()
    await state.update_data(
        status_client_id=client_id
    )

    await state.set_state(
        ClientStatusForm.status
    )

    await callback.message.answer(
        "وضعیت مشتری:",
        reply_markup=one_column(
            CLIENT_STATUSES
        ),
    )

    await callback.answer()


@dp.message(ClientStatusForm.status)
async def client_status_save(
    message: Message,
    state: FSMContext,
):
    if message.text not in CLIENT_STATUSES:
        await message.answer("وضعیت معتبر انتخاب کنید.")
        return

    data = await state.get_data()

    async with SessionLocal() as session:
        client = await get_client(
            session,
            data["status_client_id"],
        )

        if not client:
            await state.clear()
            await message.answer("❌ مشتری پیدا نشد.")
            return

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name,
        )

        old = client.status
        client.status = message.text

        await add_activity(
            session,
            user.id,
            "تغییر وضعیت مشتری",
            "client",
            client.id,
            f"{old} → {client.status}",
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ وضعیت مشتری تغییر کرد.",
        reply_markup=main_menu(),
    )


# =========================================================
# SMART MATCHING
# =========================================================

def score_range(
    value,
    minimum,
    maximum,
):
    value = float(value or 0)
    minimum = float(minimum or 0)
    maximum = float(maximum or 0)

    if minimum <= 0 and maximum <= 0:
        return 100.0

    if minimum > 0 and maximum > 0:
        if minimum > maximum:
            minimum, maximum = maximum, minimum

        if minimum <= value <= maximum:
            return 100.0

        if value < minimum:
            if minimum == 0:
                return 100.0

            distance = (
                (minimum - value) / minimum
            )

            return max(
                0,
                100 - distance * 100,
            )

        distance = (
            (value - maximum) / maximum
        )

        return max(
            0,
            100 - distance * 100,
        )

    if minimum > 0:
        if value >= minimum:
            return 100.0

        distance = (
            (minimum - value) / minimum
        )

        return max(
            0,
            100 - distance * 100,
        )

    if maximum > 0:
        if value <= maximum:
            return 100.0

        distance = (
            (value - maximum) / maximum
        )

        return max(
            0,
            100 - distance * 100,
        )

    return 100.0


def year_score(prop_year, client_min, client_max):
    prop_year = int(prop_year or 0)
    client_min = int(client_min or 0)
    client_max = int(client_max or 0)

    if client_min <= 0 and client_max <= 0:
        return 100.0

    if prop_year <= 0:
        return 0.0

    if client_min > 0 and client_max > 0:
        if client_min > client_max:
            client_min, client_max = (
                client_max,
                client_min,
            )

        if client_min <= prop_year <= client_max:
            return 100.0

        distance = (
            client_min - prop_year
            if prop_year < client_min
            else prop_year - client_max
        )

        return max(
            0,
            100 - (distance / 20) * 100,
        )

    if client_min > 0:
        if prop_year >= client_min:
            return 100.0

        distance = client_min - prop_year

        return max(
            0,
            100 - (distance / 20) * 100,
        )

    if client_max > 0:
        if prop_year <= client_max:
            return 100.0

        distance = prop_year - client_max

        return max(
            0,
            100 - (distance / 20) * 100,
        )

    return 100.0


def match_score(client, prop):
    # 40% قیمت
    budget = score_range(
        prop.price,
        client.min_budget,
        client.max_budget,
    )

    # 30% منطقه
    if (
        not client.area
        or client.area in {
            "همه مناطق",
            "همه",
            "کل مناطق",
        }
    ):
        area = 100.0
    else:
        area = (
            100.0
            if client.area == prop.area
            else 0.0
        )

    # 15% سال ساخت
    year = year_score(
        prop.year_built,
        client.min_year_built,
        client.max_year_built,
    )

    # 10% متراژ
    sqm = score_range(
        prop.sqm,
        client.min_sqm,
        client.max_sqm,
    )

    # 5% نوع ملک
    if (
        not client.property_type
        or client.property_type == "همه انواع"
    ):
        property_type = 100.0
    else:
        property_type = (
            100.0
            if client.property_type
            == prop.property_type
            else 0.0
        )

    total = (
        budget * 0.40
        + area * 0.30
        + year * 0.15
        + sqm * 0.10
        + property_type * 0.05
    )

    return round(total, 1)


async def send_matching_page(
    target,
    client_id,
    page=1,
):
    async with SessionLocal() as session:
        client = await get_client(
            session,
            client_id,
        )

        if not client:
            text_ = "❌ مشتری پیدا نشد."

            if isinstance(target, CallbackQuery):
                await target.message.answer(text_)
                await target.answer()
            else:
                await target.answer(text_)

            return

        if not client_is_active(client):
            text_ = (
                "⚠️ این مشتری دیگر در عملیات فعال نیست."
            )

            if isinstance(target, CallbackQuery):
                await target.message.answer(text_)
                await target.answer()
            else:
                await target.answer(text_)

            return

        result = await session.execute(
            select(Property).where(
                Property.status.in_(
                    list(ACTIVE_PROPERTY_STATUSES)
                )
            )
        )

        properties = result.scalars().all()

        scored = []

        for prop in properties:
            score = match_score(
                client,
                prop,
            )

            # فقط فایل‌های مناسب
            if score >= 50:
                scored.append(
                    (
                        score,
                        prop,
                    )
                )

        scored.sort(
            key=lambda x: (
                x[0],
                x[1].price,
            ),
            reverse=True,
        )

        total = len(scored)

        if total == 0:
            text_ = (
                "فایل زنده مناسب با معیارهای این مشتری پیدا نشد."
            )

            if isinstance(target, CallbackQuery):
                await target.message.answer(text_)
                await target.answer()
            else:
                await target.answer(text_)

            return

        pages = max(
            1,
            math.ceil(total / PAGE_SIZE),
        )

        page = max(
            1,
            min(page, pages),
        )

        start = (
            page - 1
        ) * PAGE_SIZE

        selected = scored[
            start:start + PAGE_SIZE
        ]

        text_ = (
            f"🎯 فایل‌های مناسب برای "
            f"{client.name}\n\n"
            f"صفحه {page} از {pages} — "
            f"{total} نتیجه\n\n"
            "وزن تطبیق:\n"
            "💰 قیمت 40% | 📍 منطقه 30% | "
            "🏗 سال ساخت 15% | 📐 متراژ 10% | "
            "🏠 نوع ملک 5%\n\n"
        )

        rows = []

        for score, prop in selected:
            text_ += (
                f"⭐ {score}% | "
                f"{prop.code} | "
                f"{prop.area}\n"
                f"📐 {money(prop.sqm)} متر | "
                f"💰 {money(prop.price)}\n"
                f"🏗 {prop.year_built or 'نامشخص'} | "
                f"{prop.property_type}\n\n"
            )

            rows.append(
                [
                    (
                        f"⭐ {score}% | {prop.code}",
                        f"matchp:{prop.id}",
                    )
                ]
            )

        nav = []

        if page > 1:
            nav.append(
                (
                    "⬅️ قبلی",
                    f"matchpage:{client.id}:{page - 1}",
                )
            )

        nav.append(
            (
                f"صفحه {page} از {pages}",
                "noop",
            )
        )

        if page < pages:
            nav.append(
                (
                    "بعدی ➡️",
                    f"matchpage:{client.id}:{page + 1}",
                )
            )

        rows.append(nav)

        markup = InlineKeyboardMarkup(
            inline_keyboard=rows
        )

        if isinstance(target, CallbackQuery):
            await target.message.answer(
                text_,
                reply_markup=markup,
            )
            await target.answer()
        else:
            await target.answer(
                text_,
                reply_markup=markup,
            )


@dp.message(F.text == "🎯 تطبیق مشتری")
async def matching_start(
    message: Message,
    state: FSMContext,
):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await state.clear()
    await state.set_state(
        MatchForm.client_id
    )

    async with SessionLocal() as session:
        result = await session.execute(
            select(Client)
            .where(
                Client.status.in_(
                    list(ACTIVE_CLIENT_STATUSES)
                )
            )
            .order_by(
                Client.created_at.desc()
            )
            .limit(100)
        )

        clients = result.scalars().all()

    if not clients:
        await state.clear()
        await message.answer(
            "❌ مشتری فعال وجود ندارد.",
            reply_markup=main_menu(),
        )
        return

    rows = []

    for c in clients:
        rows.append(
            [
                (
                    f"{c.code} | {c.name} | {c.area}",
                    f"match:{c.id}",
                )
            ]
        )

    await message.answer(
        "👤 مشتری را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )


@dp.callback_query(F.data.startswith("match:"))
async def matching_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    client_id = int(
        callback.data.split(":")[1]
    )

    await state.clear()

    await send_matching_page(
        callback,
        client_id,
        1,
    )


@dp.callback_query(F.data.startswith("matchpage:"))
async def matching_page(
    callback: CallbackQuery,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    _, client_id, page = callback.data.split(":")

    await send_matching_page(
        callback,
        int(client_id),
        int(page),
    )


@dp.callback_query(F.data.startswith("matchp:"))
async def matching_property(
    callback: CallbackQuery,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    property_id = int(
        callback.data.split(":")[1]
    )

    await send_property_detail(
        callback,
        property_id,
    )


# =========================================================
# VISIT
# =========================================================

@dp.message(F.text == "📅 ثبت بازدید")
async def visit_start(
    message: Message,
    state: FSMContext,
):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await state.clear()
    await state.set_state(
        VisitForm.client_id
    )

    async with SessionLocal() as session:
        result = await session.execute(
            select(Client)
            .where(
                Client.status.in_(
                    list(ACTIVE_CLIENT_STATUSES)
                )
            )
            .order_by(
                Client.created_at.desc()
            )
        )

        clients = result.scalars().all()

    if not clients:
        await state.clear()
        await message.answer(
            "❌ مشتری فعال وجود ندارد.",
            reply_markup=main_menu(),
        )
        return

    rows = []

    for c in clients:
        rows.append(
            [
                (
                    f"{c.code} | {c.name}",
                    f"visitclient:{c.id}",
                )
            ]
        )

    await message.answer(
        "👤 مشتری را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )


@dp.callback_query(F.data.startswith("visitclient:"))
async def visit_client_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    client_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:
        client = await get_client(
            session,
            client_id,
        )

        if not client or not client_is_active(client):
            await callback.answer(
                "این مشتری فعال نیست.",
                show_alert=True,
            )
            return

        result = await session.execute(
            select(Property)
            .where(
                Property.status.in_(
                    list(ACTIVE_PROPERTY_STATUSES)
                )
            )
            .order_by(
                Property.created_at.desc()
            )
            .limit(100)
        )

        properties = result.scalars().all()

    await state.clear()
    await state.update_data(
        visit_client_id=client_id
    )
    await state.set_state(
        VisitForm.property_id
    )

    if not properties:
        await state.clear()
        await callback.message.answer(
            "❌ فایل زنده وجود ندارد.",
            reply_markup=main_menu(),
        )
        await callback.answer()
        return

    rows = []

    for p in properties:
        rows.append(
            [
                (
                    f"{p.code} | {p.area} | "
                    f"{money(p.price)}",
                    f"visitproperty:{p.id}",
                )
            ]
        )

    await callback.message.answer(
        "🏠 فایل بازدید:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("visitproperty:"))
async def visit_property_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    property_id = int(
        callback.data.split(":")[1]
    )

    data = await state.get_data()
    client_id = data.get("visit_client_id")

    if not client_id:
        await callback.answer(
            "اطلاعات بازدید منقضی شده.",
            show_alert=True,
        )
        return

    async with SessionLocal() as session:
        client = await get_client(
            session,
            client_id,
        )

        prop = await get_property(
            session,
            property_id,
        )

        if (
            not client
            or not prop
            or not client_is_active(client)
            or not property_is_active(prop)
        ):
            await callback.answer(
                "مشتری یا فایل فعال نیست.",
                show_alert=True,
            )
            return

        result = await session.execute(
            select(Visit)
            .where(
                Visit.client_id == client_id,
                Visit.property_id == property_id,
            )
            .order_by(
                Visit.created_at.desc()
            )
            .limit(1)
        )

        previous = result.scalar_one_or_none()

    await state.update_data(
        visit_property_id=property_id
    )

    if previous:
        await state.set_state(
            VisitForm.duplicate_decision
        )

        await callback.message.answer(
            "⚠️ برای این مشتری قبلاً از این فایل بازدید ثبت شده است.\n\n"
            "می‌خواهید بازدید مجدد ثبت شود؟",
            reply_markup=keyboard(
                [
                    ["🔄 ثبت بازدید مجدد"],
                    ["❌ لغو"],
                ]
            ),
        )

    else:
        await state.set_state(
            VisitForm.interest
        )

        await callback.message.answer(
            "⭐ میزان علاقه:",
            reply_markup=one_column(
                INTERESTS
            ),
        )

    await callback.answer()


@dp.message(VisitForm.duplicate_decision)
async def visit_duplicate_decision(
    message: Message,
    state: FSMContext,
):
    if message.text == "❌ لغو":
        await state.clear()
        await message.answer(
            "بازدید لغو شد.",
            reply_markup=main_menu(),
        )
        return

    if message.text != "🔄 ثبت بازدید مجدد":
        await message.answer(
            "یکی از گزینه‌ها را انتخاب کنید."
        )
        return

    await state.set_state(
        VisitForm.interest
    )

    await message.answer(
        "⭐ میزان علاقه:",
        reply_markup=one_column(
            INTERESTS
        ),
    )


@dp.message(VisitForm.interest)
async def visit_interest(
    message: Message,
    state: FSMContext,
):
    if message.text not in INTERESTS:
        await message.answer("انتخاب کنید.")
        return

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
        ),
    )


@dp.message(VisitForm.price_reaction)
async def visit_price(
    message: Message,
    state: FSMContext,
):
    if message.text not in PRICE_REACTIONS:
        await message.answer("انتخاب کنید.")
        return

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
        ),
    )


@dp.message(VisitForm.property_reaction)
async def visit_property_reaction(
    message: Message,
    state: FSMContext,
):
    if message.text not in PROPERTY_REACTIONS:
        await message.answer("انتخاب کنید.")
        return

    await state.update_data(
        property_reaction=message.text
    )

    await state.set_state(
        VisitForm.objection
    )

    await message.answer(
        "❗ اعتراض/ایراد مشتری:"
    )


@dp.message(VisitForm.objection)
async def visit_objection(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        objection=message.text.strip()
    )

    await state.set_state(
        VisitForm.next_action
    )

    await message.answer(
        "➡️ اقدام بعدی:",
        reply_markup=one_column(
            NEXT_ACTIONS
        ),
    )


@dp.message(VisitForm.next_action)
async def visit_next_action(
    message: Message,
    state: FSMContext,
):
    if message.text not in NEXT_ACTIONS:
        await message.answer("انتخاب کنید.")
        return

    await state.update_data(
        next_action=message.text
    )

    await state.set_state(
        VisitForm.followup_date
    )

    await message.answer(
        "📅 تاریخ پیگیری:\n"
        "اگر ندارد «ندارد» بنویسید."
    )


@dp.message(VisitForm.followup_date)
async def visit_followup(
    message: Message,
    state: FSMContext,
):
    value = message.text.strip()

    if value == "ندارد":
        value = ""

    await state.update_data(
        followup_date=value
    )

    await state.set_state(
        VisitForm.note
    )

    await message.answer(
        "📝 یادداشت:"
    )


@dp.message(VisitForm.note)
async def visit_save(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    async with SessionLocal() as session:
        client = await get_client(
            session,
            data["visit_client_id"],
        )

        prop = await get_property(
            session,
            data["visit_property_id"],
        )

        if (
            not client
            or not prop
            or not client_is_active(client)
            or not property_is_active(prop)
        ):
            await state.clear()
            await message.answer(
                "❌ مشتری یا فایل دیگر فعال نیست.",
                reply_markup=main_menu(),
            )
            return

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name,
        )

        visit = Visit(
            client_id=client.id,
            property_id=prop.id,
            user_id=user.id,
            interest=data["interest"],
            price_reaction=data["price_reaction"],
            property_reaction=data["property_reaction"],
            objection=data["objection"],
            next_action=data["next_action"],
            followup_date=data["followup_date"],
            note=message.text.strip(),
        )

        session.add(visit)
        await session.flush()

        await add_activity(
            session,
            user.id,
            "بازدید",
            "property",
            prop.id,
            (
                f"بازدید مشتری {client.name} "
                f"از فایل {prop.code}"
            ),
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ بازدید ثبت شد.",
        reply_markup=main_menu(),
    )


# =========================================================
# FOLLOW UPS
# =========================================================

@dp.message(F.text == "🔔 پیگیری‌ها")
async def followups(message: Message):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(
                Visit,
                Client,
                Property,
            )
            .join(
                Client,
                Client.id == Visit.client_id,
            )
            .join(
                Property,
                Property.id == Visit.property_id,
            )
            .where(
                Visit.followup_date != "",
                Client.status.in_(
                    list(ACTIVE_CLIENT_STATUSES)
                ),
                Property.status.in_(
                    list(ACTIVE_PROPERTY_STATUSES)
                ),
            )
            .order_by(
                Visit.created_at.desc()
            )
            .limit(100)
        )

        rows = result.all()

        if not rows:
            await message.answer(
                "🔔 پیگیری فعالی ثبت نشده است."
            )
            return

        text_ = "🔔 پیگیری‌های فعال\n\n"

        for visit, client, prop in rows:
            text_ += (
                f"📅 {visit.followup_date}\n"
                f"👤 {client.name} | {client.phone}\n"
                f"🏠 {prop.code} | {prop.area}\n"
                f"➡️ {visit.next_action}\n"
                f"📝 {visit.note or '—'}\n\n"
            )

        await message.answer(text_)


# =========================================================
# SEARCH MENU
# =========================================================

SEARCH_PROPERTY_STEPS = [
    "area",
    "min_price",
    "max_price",
    "min_sqm",
    "max_sqm",
    "property_type",
    "min_year",
    "max_year",
    "owner",
    "code",
    "status",
]

SEARCH_CLIENT_STEPS = [
    "area",
    "min_budget",
    "max_budget",
    "min_sqm",
    "max_sqm",
    "property_type",
    "name",
    "status",
]


def search_step_question(kind, step):
    if kind == "property":
        questions = {
            "area": (
                "📍 منطقه را انتخاب کنید:",
                one_column(AREAS),
            ),
            "min_price": (
                "💰 حداقل قیمت؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "max_price": (
                "💰 حداکثر قیمت؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "min_sqm": (
                "📐 حداقل متراژ؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "max_sqm": (
                "📐 حداکثر متراژ؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "property_type": (
                "🏠 نوع ملک:",
                one_column(
                    PROPERTY_TYPES + ["همه انواع"]
                ),
            ),
            "min_year": (
                "🏗 حداقل سال ساخت؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "max_year": (
                "🏗 حداکثر سال ساخت؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "owner": (
                "👤 نام مالک/شماره تلفن؛ برای رد کردن «—»:",
                cancel_keyboard(),
            ),
            "code": (
                "🔢 کد فایل؛ برای رد کردن «—»:",
                cancel_keyboard(),
            ),
            "status": (
                "📌 وضعیت:",
                one_column(
                    ["همه وضعیت‌ها"] + STATUSES
                ),
            ),
        }

    else:
        questions = {
            "area": (
                "📍 منطقه:",
                one_column(AREAS),
            ),
            "min_budget": (
                "💰 حداقل بودجه؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "max_budget": (
                "💰 حداکثر بودجه؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "min_sqm": (
                "📐 حداقل متراژ؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "max_sqm": (
                "📐 حداکثر متراژ؛ برای بدون محدودیت 0:",
                cancel_keyboard(),
            ),
            "property_type": (
                "🏠 نوع ملک:",
                one_column(
                    PROPERTY_TYPES + ["همه انواع"]
                ),
            ),
            "name": (
                "👤 نام، تلفن یا کد مشتری؛ برای رد کردن «—»:",
                cancel_keyboard(),
            ),
            "status": (
                "📌 وضعیت مشتری:",
                one_column(
                    ["همه وضعیت‌ها"] + CLIENT_STATUSES
                ),
            ),
        }

    return questions[step]


async def start_search(
    message: Message,
    state: FSMContext,
    kind,
):
    await state.clear()

    await state.update_data(
        search_kind=kind,
        search_criteria={},
        search_index=0,
    )

    await state.set_state(
        SearchForm.step
    )

    step = (
        SEARCH_PROPERTY_STEPS[0]
        if kind == "property"
        else SEARCH_CLIENT_STEPS[0]
    )

    question, markup = search_step_question(
        kind,
        step,
    )

    await state.update_data(
        search_step=step
    )

    await message.answer(
        question,
        reply_markup=markup,
    )


@dp.message(F.text == "🔎 جستجوی فایل")
async def property_search_start(
    message: Message,
    state: FSMContext,
):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await start_search(
        message,
        state,
        "property",
    )


@dp.message(F.text == "🔎 جستجوی مشتری")
async def client_search_start(
    message: Message,
    state: FSMContext,
):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    await start_search(
        message,
        state,
        "client",
    )


@dp.message(SearchForm.step)
async def search_router(
    message: Message,
    state: FSMContext,
):
    if message.text == "❌ لغو":
        await state.clear()
        await message.answer(
            "جستجو لغو شد.",
            reply_markup=main_menu(),
        )
        return

    data = await state.get_data()

    kind = data.get("search_kind")
    step = data.get("search_step")
    criteria = data.get(
        "search_criteria",
        {},
    )

    if not kind or not step:
        await state.clear()
        await message.answer(
            "❌ جستجو منقضی شده.",
            reply_markup=main_menu(),
        )
        return

    value = message.text.strip()

    if kind == "property":
        if step == "area":
            if value not in AREAS:
                await message.answer("از گزینه‌ها انتخاب کنید.")
                return

            if value != "همه مناطق":
                criteria["area"] = value

        elif step == "min_price":
            criteria["min_price"] = number(value)

        elif step == "max_price":
            criteria["max_price"] = number(value)

        elif step == "min_sqm":
            criteria["min_sqm"] = number(value)

        elif step == "max_sqm":
            criteria["max_sqm"] = number(value)

        elif step == "property_type":
            if value != "همه انواع" and value not in PROPERTY_TYPES:
                await message.answer("نوع ملک معتبر نیست.")
                return

            if value != "همه انواع":
                criteria["property_type"] = value

        elif step == "min_year":
            v = integer(value)

            if v != 0 and not 1800 <= v <= 2100:
                await message.answer("سال ساخت معتبر نیست.")
                return

            criteria["min_year"] = v

        elif step == "max_year":
            v = integer(value)

            if v != 0 and not 1800 <= v <= 2100:
                await message.answer("سال ساخت معتبر نیست.")
                return

            criteria["max_year"] = v

        elif step == "owner":
            if value != "—":
                criteria["owner"] = value

        elif step == "code":
            if value != "—":
                criteria["code"] = value

        elif step == "status":
            if value != "همه وضعیت‌ها":
                criteria["status"] = normalize_property_status(
                    value
                )

        steps = SEARCH_PROPERTY_STEPS

    else:
        if step == "area":
            if value not in AREAS:
                await message.answer("از گزینه‌ها انتخاب کنید.")
                return

            if value != "همه مناطق":
                criteria["area"] = value

        elif step == "min_budget":
            criteria["min_budget"] = number(value)

        elif step == "max_budget":
            criteria["max_budget"] = number(value)

        elif step == "min_sqm":
            criteria["min_sqm"] = number(value)

        elif step == "max_sqm":
            criteria["max_sqm"] = number(value)

        elif step == "property_type":
            if value != "همه انواع" and value not in PROPERTY_TYPES:
                await message.answer("نوع ملک معتبر نیست.")
                return

            if value != "همه انواع":
                criteria["property_type"] = value

        elif step == "name":
            if value != "—":
                criteria["name"] = value

        elif step == "status":
            if value != "همه وضعیت‌ها":
                criteria["status"] = value

        steps = SEARCH_CLIENT_STEPS

    await state.update_data(
        search_criteria=criteria
    )

    current_index = steps.index(step)

    if current_index + 1 >= len(steps):
        await state.clear()

        if kind == "property":
            await send_property_page(
                message,
                1,
                criteria,
            )
        else:
            await send_client_page(
                message,
                1,
                criteria,
            )

        return

    next_step = steps[
        current_index + 1
    ]

    await state.update_data(
        search_step=next_step
    )

    question, markup = search_step_question(
        kind,
        next_step,
    )

    await message.answer(
        question,
        reply_markup=markup,
    )


# =========================================================
# SEARCH PAGINATION WITH CRITERIA
# =========================================================

@dp.callback_query(F.data.startswith("searchp:"))
async def search_property_pagination(
    callback: CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()

    criteria = data.get(
        "search_property_criteria",
        {},
    )

    page = int(
        callback.data.split(":")[1]
    )

    await send_property_page(
        callback,
        page,
        criteria,
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("searchc:"))
async def search_client_pagination(
    callback: CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()

    criteria = data.get(
        "search_client_criteria",
        {},
    )

    page = int(
        callback.data.split(":")[1]
    )

    await send_client_page(
        callback,
        page,
        criteria,
    )

    await callback.answer()


# =========================================================
# KPI
# =========================================================

async def kpi_for_user(
    session,
    user_id,
):
    activity_count = (
        await session.execute(
            select(
                func.count(Activity.id)
            ).where(
                Activity.user_id == user_id
            )
        )
    ).scalar_one()

    visit_count = (
        await session.execute(
            select(
                func.count(Visit.id)
            ).where(
                Visit.user_id == user_id
            )
        )
    ).scalar_one()

    total_files = (
        await session.execute(
            select(
                func.count(Property.id)
            )
        )
    ).scalar_one()

    active_files = (
        await session.execute(
            select(
                func.count(Property.id)
            ).where(
                Property.status.in_(
                    list(ACTIVE_PROPERTY_STATUSES)
                )
            )
        )
    ).scalar_one()

    sold_by_us = (
        await session.execute(
            select(
                func.count(Property.id)
            ).where(
                Property.status
                == "🔵 معامله شد - توسط ما"
            )
        )
    ).scalar_one()

    total_clients = (
        await session.execute(
            select(
                func.count(Client.id)
            )
        )
    ).scalar_one()

    active_clients = (
        await session.execute(
            select(
                func.count(Client.id)
            ).where(
                Client.status.in_(
                    list(ACTIVE_CLIENT_STATUSES)
                )
            )
        )
    ).scalar_one()

    return {
        "activity": activity_count,
        "visits": visit_count,
        "total_files": total_files,
        "active_files": active_files,
        "sold_by_us": sold_by_us,
        "total_clients": total_clients,
        "active_clients": active_clients,
    }


@dp.message(F.text == "📊 KPI من")
async def my_kpi(message: Message):
    if not access_required(message):
        await message.answer("⛔ دسترسی ندارید.")
        return

    async with SessionLocal() as session:
        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.full_name,
        )

        kpi = await kpi_for_user(
            session,
            user.id,
        )

    await message.answer(
        "📊 KPI من\n\n"
        f"⚡ فعالیت‌ها: {kpi['activity']}\n"
        f"📅 بازدیدها: {kpi['visits']}\n"
        f"📂 کل فایل‌ها: {kpi['total_files']}\n"
        f"🟢 فایل‌های زنده: {kpi['active_files']}\n"
        f"🔵 معامله توسط ما: {kpi['sold_by_us']}\n"
        f"👥 کل مشتری‌ها: {kpi['total_clients']}\n"
        f"🟢 مشتری‌های فعال: {kpi['active_clients']}"
    )


@dp.message(F.text == "📈 KPI تیم")
async def team_kpi(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ فقط ادمین به KPI تیم دسترسی دارد."
        )
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(User)
            .order_by(User.name.asc())
        )

        users = result.scalars().all()

        text_ = "📈 KPI تیم\n\n"

        for user in users:
            kpi = await kpi_for_user(
                session,
                user.id,
            )

            text_ += (
                f"👤 {user.name or user.telegram_id}\n"
                f"⚡ فعالیت: {kpi['activity']}\n"
                f"📅 بازدید: {kpi['visits']}\n"
                f"📂 کل فایل‌ها: {kpi['total_files']}\n"
                f"🟢 زنده: {kpi['active_files']}\n"
                f"🔵 معامله ما: {kpi['sold_by_us']}\n"
                f"👥 مشتری فعال: {kpi['active_clients']}\n\n"
            )

    await message.answer(text_)


# =========================================================
# LAST ACTIVITIES
# =========================================================

@dp.message(F.text == "🕘 آخرین فعالیت‌ها")
async def last_activities(
    message: Message,
):
    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ فقط ادمین."
        )
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(
                Activity,
                User,
            )
            .outerjoin(
                User,
                User.id == Activity.user_id,
            )
            .order_by(
                Activity.created_at.desc()
            )
            .limit(50)
        )

        rows = result.all()

        if not rows:
            await message.answer(
                "فعالیتی ثبت نشده است."
            )
            return

        text_ = "🕘 آخرین فعالیت‌ها\n\n"

        for activity, user in rows:
            text_ += (
                f"🕒 {fmt_date(activity.created_at)}\n"
                f"👤 {user.name if user else activity.user_id}\n"
                f"📌 {activity.activity_type}\n"
                f"{short(activity.description, 150)}\n\n"
            )

    await message.answer(text_)


# =========================================================
# DIRECT CLIENT SEARCH / LIST FALLBACK
# =========================================================

@dp.message(F.text == "👥 مشتری‌ها")
async def duplicate_client_list_guard(message: Message):
    # این handler عمداً هیچ کاری نمی‌کند.
    # handler اصلی در aiogram قبل‌تر اجرا می‌شود.
    return


# =========================================================
# CALLBACK: DIRECT PROPERTY DETAIL
# =========================================================

@dp.callback_query(F.data.startswith("property:"))
async def old_property_callback(
    callback: CallbackQuery,
):
    if not callback_access_required(callback):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    property_id = int(
        callback.data.split(":")[1]
    )

    await send_property_detail(
        callback,
        property_id,
    )


# =========================================================
# ERROR HANDLER
# =========================================================

@dp.error()
async def global_error_handler(
    event,
):
    try:
        update = event.update

        if isinstance(update, Message):
            await update.answer(
                "⚠️ خطایی رخ داد. دوباره تلاش کنید."
            )

        elif isinstance(update, CallbackQuery):
            await update.answer(
                "⚠️ خطایی رخ داد.",
                show_alert=True,
            )

    except Exception:
        pass


# =========================================================
# STARTUP
# =========================================================

async def main():
    await migrate()

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
