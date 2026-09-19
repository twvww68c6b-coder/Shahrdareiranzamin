import asyncio
import os
import re
import shutil
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    and_,
    delete,
    desc,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///realestate.db"
)

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

PAGE_SIZE = 10

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
    parse_mode=ParseMode.HTML,
)

dp = Dispatcher()
router = Router()
dp.include_router(router)


# ============================================================
# DATABASE
# ============================================================

class Base(AsyncAttrs, DeclarativeBase):
    pass


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============================================================
# CONSTANTS
# ============================================================

PROPERTY_STATUSES = [
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

PROPERTY_TYPES = [
    "آپارتمان",
    "ویلایی",
    "کلنگی",
    "زمین",
    "مغازه",
    "اداری",
    "تجاری",
    "سایر",
]

DOCUMENT_TYPES = [
    "سند تک‌برگ",
    "سند منگوله‌دار",
    "قولنامه‌ای",
    "وکالتی",
    "اوقافی",
    "سایر",
]

EVENT_TYPES = [
    "تماس با مالک",
    "بازدید",
    "مذاکره",
    "تغییر قیمت",
    "قرارداد",
    "پیگیری",
    "سایر",
]

ACTIVE_PROPERTY_STATUSES = [
    "🟢 فعال",
    "🟡 در مذاکره",
]


# ============================================================
# MODELS
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        default="",
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default="مشاور",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    area: Mapped[str] = mapped_column(
        String(150),
        default="",
        index=True,
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
        index=True,
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

    # --------------------------------------------------------
    # NEW
    # --------------------------------------------------------

    year_built: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    elevator: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    parking: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    parking_type: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    storage: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    tenant: Mapped[str] = mapped_column(
        String(100),
        default="",
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
        String(100),
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

    created_by: Mapped[int] = mapped_column(
        Integer,
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

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
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
        String(150),
        default="",
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

    # --------------------------------------------------------
    # NEW
    # --------------------------------------------------------

    min_year_built: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    max_year_built: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    bedrooms: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    description: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="فعال",
        index=True,
    )

    created_by: Mapped[int] = mapped_column(
        Integer,
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


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

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

    visit_date: Mapped[str] = mapped_column(
        String(100),
        default="",
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
        String(200),
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


class PropertyHistory(Base):
    __tablename__ = "property_history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    property_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    field_name: Mapped[str] = mapped_column(
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

    event_type: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    property_id: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    client_id: Mapped[int] = mapped_column(
        Integer,
        default=0,
        index=True,
    )

    activity_type: Mapped[str] = mapped_column(
        String(100),
        default="",
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


# ============================================================
# MIGRATION
# ============================================================

async def sqlite_backup_if_needed():
    """
    فقط برای SQLite.
    هیچ رکوردی حذف یا overwrite نمی‌شود.
    """

    if not DATABASE_URL.startswith("sqlite"):
        return

    db_path = DATABASE_URL.split("///")[-1]

    if not os.path.exists(db_path):
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"realestate_{timestamp}.db"

    try:
        source = sqlite3.connect(db_path)
        target = sqlite3.connect(str(backup_path))

        with target:
            source.backup(target)

        target.close()
        source.close()

    except Exception as e:
        print("Backup warning:", e)


async def migrate():
    """
    Migration کاملاً additive است.
    DROP / DELETE / TRUNCATE وجود ندارد.
    """

    await sqlite_backup_if_needed()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if not DATABASE_URL.startswith("sqlite"):
        return

    db_path = DATABASE_URL.split("///")[-1]

    if not os.path.exists(db_path):
        return

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    def columns(table_name):
        cursor.execute(
            f"PRAGMA table_info({table_name})"
        )
        return {
            row[1]
            for row in cursor.fetchall()
        }

    # --------------------------------------------------------
    # properties.year_built
    # --------------------------------------------------------

    property_columns = columns("properties")

    if "year_built" not in property_columns:
        cursor.execute(
            """
            ALTER TABLE properties
            ADD COLUMN year_built INTEGER DEFAULT 0
            """
        )

    # --------------------------------------------------------
    # clients.min_year_built
    # --------------------------------------------------------

    client_columns = columns("clients")

    if "min_year_built" not in client_columns:
        cursor.execute(
            """
            ALTER TABLE clients
            ADD COLUMN min_year_built INTEGER DEFAULT 0
            """
        )

    if "max_year_built" not in client_columns:
        cursor.execute(
            """
            ALTER TABLE clients
            ADD COLUMN max_year_built INTEGER DEFAULT 0
            """
        )

    connection.commit()
    connection.close()


# ============================================================
# FSM STATES
# ============================================================

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
    bedrooms = State()
    description = State()
    confirm = State()


class SearchForm(StatesGroup):
    query = State()


class VisitForm(StatesGroup):
    client = State()
    property = State()
    interest = State()
    price_reaction = State()
    property_reaction = State()
    objection = State()
    next_action = State()
    followup_date = State()
    note = State()


class PropertyEditForm(StatesGroup):
    value = State()


class StatusForm(StatesGroup):
    value = State()
    transaction_value = State()


class SearchPropertyForm(StatesGroup):
    area = State()
    min_price = State()
    max_price = State()
    min_sqm = State()
    max_sqm = State()
    property_type = State()
    min_year = State()
    max_year = State()
    owner = State()
    code = State()


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard(is_admin=False):
    rows = [
        [
            KeyboardButton(text="➕ ثبت فایل"),
            KeyboardButton(text="👥 ثبت مشتری"),
        ],
        [
            KeyboardButton(text="📂 فایل‌ها"),
            KeyboardButton(text="👤 مشتری‌ها"),
        ],
        [
            KeyboardButton(text="🔎 جستجوی فایل"),
            KeyboardButton(text="🔎 جستجوی مشتری"),
        ],
        [
            KeyboardButton(text="🎯 مچینگ مشتری"),
            KeyboardButton(text="🏠 فایل‌های مالک"),
        ],
        [
            KeyboardButton(text="📅 ثبت بازدید"),
            KeyboardButton(text="📌 پیگیری‌ها"),
        ],
        [
            KeyboardButton(text="📊 KPI من"),
        ],
    ]

    if is_admin:
        rows.append([
            KeyboardButton(text="📊 KPI تیم"),
            KeyboardButton(text="🕐 آخرین فعالیت‌ها"),
        ])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ لغو")]
        ],
        resize_keyboard=True,
    )


def back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 بازگشت")]
        ],
        resize_keyboard=True,
    )


def property_type_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="آپارتمان"),
                KeyboardButton(text="ویلایی"),
            ],
            [
                KeyboardButton(text="کلنگی"),
                KeyboardButton(text="زمین"),
            ],
            [
                KeyboardButton(text="مغازه"),
                KeyboardButton(text="اداری"),
            ],
            [
                KeyboardButton(text="تجاری"),
                KeyboardButton(text="سایر"),
            ],
            [
                KeyboardButton(text="❌ لغو"),
            ],
        ],
        resize_keyboard=True,
    )


def status_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=x)]
            for x in PROPERTY_STATUSES
        ] + [
            [KeyboardButton(text="❌ لغو")]
        ],
        resize_keyboard=True,
    )


# ============================================================
# BASIC HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def normalize_text(value) -> str:
    if value is None:
        return ""

    text = str(value).strip()

    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    return text


def parse_number(value, default=0):
    if value is None:
        return default

    text = normalize_text(value)

    if not text:
        return default

    replacements = {
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
        ",": "",
        "٬": "",
        " ": "",
    }

    for a, b in replacements.items():
        text = text.replace(a, b)

    try:
        return float(text)
    except Exception:
        return default


def format_number(value):
    try:
        value = float(value or 0)
    except Exception:
        return "0"

    if value.is_integer():
        return f"{int(value):,}"

    return f"{value:,.2f}"


def price_text(value):
    if not value:
        return "ثبت نشده"

    return format_number(value)


def year_text(value):
    if not value:
        return "ثبت نشده"

    return str(int(value))


def safe(value):
    return normalize_text(value) or "ثبت نشده"


async def get_or_create_user(
    session: AsyncSession,
    telegram_user,
):
    result = await session.execute(
        select(User).where(
            User.telegram_id == telegram_user.id
        )
    )

    user = result.scalar_one_or_none()

    if user:
        return user

    user = User(
        telegram_id=telegram_user.id,
        name=telegram_user.full_name or "",
        role="مدیر" if is_admin(telegram_user.id) else "مشاور",
        active=True,
    )

    session.add(user)
    await session.commit()

    return user


async def log_activity(
    session: AsyncSession,
    user_id: int,
    activity_type: str,
    description: str = "",
    property_id: int = 0,
    client_id: int = 0,
):
    activity = Activity(
        user_id=user_id,
        property_id=property_id,
        client_id=client_id,
        activity_type=activity_type,
        description=description,
    )

    session.add(activity)


async def add_property_history(
    session: AsyncSession,
    property_id: int,
    user_id: int,
    field_name: str,
    old_value,
    new_value,
    event_type: str = "سایر",
):
    history = PropertyHistory(
        property_id=property_id,
        user_id=user_id,
        field_name=field_name,
        old_value="" if old_value is None else str(old_value),
        new_value="" if new_value is None else str(new_value),
        event_type=event_type,
    )

    session.add(history)


def property_summary(p: Property) -> str:
    return (
        f"🏠 <b>{safe(p.code)}</b>\n"
        f"📍 {safe(p.area)}\n"
        f"📐 {format_number(p.sqm)} متر\n"
        f"💰 {price_text(p.price)}\n"
        f"🏗 نوع: {safe(p.property_type)}\n"
        f"📅 ساخت: {year_text(p.year_built)}\n"
        f"📌 وضعیت: {safe(p.status)}"
    )


def client_summary(c: Client) -> str:
    budget = ""

    if c.min_budget or c.max_budget:
        budget = (
            f"\n💰 بودجه: "
            f"{price_text(c.min_budget)} تا "
            f"{price_text(c.max_budget)}"
        )

    sqm = ""

    if c.min_sqm or c.max_sqm:
        sqm = (
            f"\n📐 متراژ: "
            f"{format_number(c.min_sqm)} تا "
            f"{format_number(c.max_sqm)}"
        )

    year = ""

    if c.min_year_built or c.max_year_built:
        year = (
            f"\n📅 سال ساخت: "
            f"{c.min_year_built or '—'} تا "
            f"{c.max_year_built or '—'}"
        )

    return (
        f"👤 <b>{safe(c.name)}</b>\n"
        f"🔖 کد: {safe(c.code)}\n"
        f"📱 {safe(c.phone)}\n"
        f"📍 {safe(c.area)}\n"
        f"🏠 نوع: {safe(c.property_type)}"
        f"{budget}"
        f"{sqm}"
        f"{year}\n"
        f"📌 وضعیت: {safe(c.status)}"
    )


async def commit_and_log(
    session: AsyncSession,
):
    await session.commit()


# ============================================================
# PAGINATION
# ============================================================

def pagination_keyboard(
    prefix: str,
    page: int,
    total_pages: int,
):
    buttons = []

    if page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ قبلی",
                callback_data=f"{prefix}:{page - 1}",
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text=f"صفحه {page}/{total_pages}",
            callback_data="noop",
        )
    )

    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="بعدی ➡️",
                callback_data=f"{prefix}:{page + 1}",
            )
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[buttons]
    )


# ============================================================
# PROPERTY MATCHING
# ============================================================

def score_budget(client: Client, prop: Property) -> float:
    price = prop.price or 0

    if price <= 0:
        return 0

    min_b = client.min_budget or 0
    max_b = client.max_budget or 0

    if min_b <= 0 and max_b <= 0:
        return 100

    if min_b > 0 and price < min_b:
        distance = (min_b - price) / min_b
        return max(0, 100 - distance * 100)

    if max_b > 0 and price > max_b:
        distance = (price - max_b) / max_b
        return max(0, 100 - distance * 100)

    return 100


def score_area(client: Client, prop: Property) -> float:
    client_area = normalize_text(client.area)
    prop_area = normalize_text(prop.area)

    if not client_area:
        return 100

    if client_area in ("همه", "همه مناطق", "فرقی ندارد"):
        return 100

    if client_area == prop_area:
        return 100

    if client_area in prop_area or prop_area in client_area:
        return 80

    return 0


def score_year(client: Client, prop: Property) -> float:
    year = prop.year_built or 0

    min_y = client.min_year_built or 0
    max_y = client.max_year_built or 0

    if min_y <= 0 and max_y <= 0:
        return 100

    if year <= 0:
        return 0

    if min_y > 0 and year < min_y:
        return max(
            0,
            100 - ((min_y - year) / max(min_y, 1)) * 100
        )

    if max_y > 0 and year > max_y:
        return max(
            0,
            100 - ((year - max_y) / max(max_y, 1)) * 100
        )

    return 100


def score_sqm(client: Client, prop: Property) -> float:
    sqm = prop.sqm or 0

    min_s = client.min_sqm or 0
    max_s = client.max_sqm or 0

    if min_s <= 0 and max_s <= 0:
        return 100

    if sqm <= 0:
        return 0

    if min_s > 0 and sqm < min_s:
        return max(
            0,
            100 - ((min_s - sqm) / max(min_s, 1)) * 100
        )

    if max_s > 0 and sqm > max_s:
        return max(
            0,
            100 - ((sqm - max_s) / max(max_s, 1)) * 100
        )

    return 100


def score_type(client: Client, prop: Property) -> float:
    ctype = normalize_text(client.property_type)
    ptype = normalize_text(prop.property_type)

    if not ctype:
        return 100

    if ctype in ("همه", "فرقی ندارد"):
        return 100

    if ctype == ptype:
        return 100

    return 0


def calculate_match_score(
    client: Client,
    prop: Property,
) -> float:

    budget = score_budget(client, prop)
    area = score_area(client, prop)
    year = score_year(client, prop)
    sqm = score_sqm(client, prop)
    ptype = score_type(client, prop)

    total = (
        budget * 0.40 +
        area * 0.30 +
        year * 0.15 +
        sqm * 0.10 +
        ptype * 0.05
    )

    return round(total, 2)


# ============================================================
# PROPERTY DETAIL KEYBOARD
# ============================================================

def property_detail_keyboard(
    property_id: int,
    is_admin_user: bool = False,
):
    rows = [
        [
            InlineKeyboardButton(
                text="✏️ ویرایش",
                callback_data=f"pedit:{property_id}",
            ),
            InlineKeyboardButton(
                text="📜 تاریخچه",
                callback_data=f"phistory:{property_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 تغییر وضعیت",
                callback_data=f"pstatus:{property_id}",
            ),
            InlineKeyboardButton(
                text="📅 ثبت بازدید",
                callback_data=f"pvisit:{property_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="👤 فایل‌های این مالک",
                callback_data=f"powner:{property_id}",
            ),
        ],
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ============================================================
# NOOP
# ============================================================

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


# ============================================================
# START
# ============================================================

@router.message(Command("start"))
async def start_handler(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    async with SessionLocal() as session:
        await get_or_create_user(
            session,
            message.from_user,
        )

    await message.answer(
        "🏙️ <b>شهردار ایران‌زمین</b>\n\n"
        "سیستم مدیریت فایل، مشتری، بازدید و مچینگ آماده است.",
        reply_markup=main_keyboard(
            is_admin(message.from_user.id)
        ),
    )
    # ============================================================
# CANCEL / BACK
# ============================================================

@router.message(F.text == "❌ لغو")
async def cancel_handler(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await message.answer(
        "لغو شد.",
        reply_markup=main_keyboard(
            is_admin(message.from_user.id)
        ),
    )


@router.message(F.text == "🔙 بازگشت")
async def back_handler(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await message.answer(
        "بازگشت به منوی اصلی.",
        reply_markup=main_keyboard(
            is_admin(message.from_user.id)
        ),
    )


# ============================================================
# REGISTER PROPERTY
# ============================================================

@router.message(F.text == "➕ ثبت فایل")
async def property_start(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await state.set_state(PropertyForm.code)

    await message.answer(
        "🔖 کد فایل را وارد کن:",
        reply_markup=cancel_keyboard(),
    )


@router.message(PropertyForm.code)
async def property_code(
    message: Message,
    state: FSMContext,
):
    code = normalize_text(message.text)

    if not code:
        await message.answer("کد فایل نمی‌تواند خالی باشد.")
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(Property).where(
                Property.code == code
            )
        )

        if result.scalar_one_or_none():
            await message.answer(
                "⚠️ این کد قبلاً ثبت شده است.\n"
                "یک کد دیگر وارد کن."
            )
            return

    await state.update_data(code=code)
    await state.set_state(PropertyForm.area)

    await message.answer("📍 منطقه / محدوده را وارد کن:")


@router.message(PropertyForm.area)
async def property_area(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        area=normalize_text(message.text)
    )

    await state.set_state(PropertyForm.address)

    await message.answer("📌 آدرس یا لوکیشن فایل را وارد کن:")


@router.message(PropertyForm.address)
async def property_address(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        address=normalize_text(message.text)
    )

    await state.set_state(PropertyForm.sqm)

    await message.answer("📐 متراژ را وارد کن:")


@router.message(PropertyForm.sqm)
async def property_sqm(
    message: Message,
    state: FSMContext,
):
    sqm = parse_number(message.text)

    if sqm <= 0:
        await message.answer(
            "متراژ معتبر وارد کن."
        )
        return

    await state.update_data(sqm=sqm)
    await state.set_state(PropertyForm.price)

    await message.answer(
        "💰 قیمت کل را وارد کن:"
    )


@router.message(PropertyForm.price)
async def property_price(
    message: Message,
    state: FSMContext,
):
    price = parse_number(message.text)

    if price < 0:
        await message.answer(
            "قیمت معتبر وارد کن."
        )
        return

    await state.update_data(price=price)
    await state.set_state(PropertyForm.property_type)

    await message.answer(
        "🏠 نوع ملک را انتخاب کن:",
        reply_markup=property_type_keyboard(),
    )


@router.message(PropertyForm.property_type)
async def property_type(
    message: Message,
    state: FSMContext,
):
    value = normalize_text(message.text)

    if value not in PROPERTY_TYPES:
        await message.answer(
            "یکی از گزینه‌های موجود را انتخاب کن.",
            reply_markup=property_type_keyboard(),
        )
        return

    await state.update_data(
        property_type=value
    )

    await state.set_state(PropertyForm.bedrooms)

    await message.answer(
        "🛏 تعداد خواب را وارد کن:\n"
        "اگر ندارد 0 بزن."
    )


@router.message(PropertyForm.bedrooms)
async def property_bedrooms(
    message: Message,
    state: FSMContext,
):
    bedrooms = int(parse_number(message.text))

    await state.update_data(
        bedrooms=bedrooms
    )

    await state.set_state(PropertyForm.floors)

    await message.answer(
        "🏢 تعداد طبقات ساختمان:"
    )


@router.message(PropertyForm.floors)
async def property_floors(
    message: Message,
    state: FSMContext,
):
    floors = int(parse_number(message.text))

    await state.update_data(
        floors=floors
    )

    await state.set_state(PropertyForm.unit_floor)

    await message.answer(
        "🔢 طبقه واحد:"
    )


@router.message(PropertyForm.unit_floor)
async def property_unit_floor(
    message: Message,
    state: FSMContext,
):
    unit_floor = int(parse_number(message.text))

    await state.update_data(
        unit_floor=unit_floor
    )

    await state.set_state(PropertyForm.units_per_floor)

    await message.answer(
        "🚪 تعداد واحد در هر طبقه:"
    )


@router.message(PropertyForm.units_per_floor)
async def property_units_per_floor(
    message: Message,
    state: FSMContext,
):
    units = int(parse_number(message.text))

    await state.update_data(
        units_per_floor=units
    )

    await state.set_state(PropertyForm.year_built)

    await message.answer(
        "📅 سال ساخت را وارد کن:\n"
        "مثلاً 1402\n"
        "اگر نامشخص است 0 بزن."
    )


# ============================================================
# YEAR BUILT
# ============================================================

@router.message(PropertyForm.year_built)
async def property_year_built(
    message: Message,
    state: FSMContext,
):
    year = int(parse_number(message.text))

    if year < 0:
        await message.answer(
            "سال ساخت معتبر نیست."
        )
        return

    if year != 0 and not (
        1200 <= year <= 1600
    ):
        await message.answer(
            "سال ساخت را به صورت شمسی وارد کن؛ "
            "مثلاً 1402."
        )
        return

    await state.update_data(
        year_built=year
    )

    await state.set_state(PropertyForm.elevator)

    await message.answer(
        "🛗 آسانسور دارد؟\n"
        "مثلاً: دارد / ندارد"
    )


@router.message(PropertyForm.elevator)
async def property_elevator(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        elevator=normalize_text(message.text)
    )

    await state.set_state(PropertyForm.parking)

    await message.answer(
        "🚗 پارکینگ دارد؟"
    )


@router.message(PropertyForm.parking)
async def property_parking(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        parking=normalize_text(message.text)
    )

    await state.set_state(PropertyForm.parking_type)

    await message.answer(
        "🅿️ نوع پارکینگ را وارد کن:\n"
        "مثلاً اختصاصی / مزاحم / سندی"
    )


@router.message(PropertyForm.parking_type)
async def property_parking_type(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        parking_type=normalize_text(message.text)
    )

    await state.set_state(PropertyForm.storage)

    await message.answer(
        "📦 انباری دارد؟"
    )


@router.message(PropertyForm.storage)
async def property_storage(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        storage=normalize_text(message.text)
    )

    await state.set_state(PropertyForm.tenant)

    await message.answer(
        "👤 وضعیت مستأجر:\n"
        "مثلاً مستأجر دارد / مستأجر ندارد"
    )


@router.message(PropertyForm.tenant)
async def property_tenant(
    message: Message,
    state: FSMContext,
):
    tenant = normalize_text(message.text)

    await state.update_data(
        tenant=tenant
    )

    if tenant == "مستأجر ندارد":
        await state.update_data(
            deposit=0,
            rent=0,
            vacancy_date="",
        )

        await state.set_state(
            PropertyForm.document_type
        )

        await message.answer(
            "📄 نوع سند را وارد کن:"
        )

        return

    await state.set_state(
        PropertyForm.deposit
    )

    await message.answer(
        "💵 مبلغ ودیعه را وارد کن:"
    )


@router.message(PropertyForm.deposit)
async def property_deposit(
    message: Message,
    state: FSMContext,
):
    deposit = parse_number(message.text)

    await state.update_data(
        deposit=deposit
    )

    await state.set_state(
        PropertyForm.rent
    )

    await message.answer(
        "💵 مبلغ اجاره را وارد کن:"
    )


@router.message(PropertyForm.rent)
async def property_rent(
    message: Message,
    state: FSMContext,
):
    rent = parse_number(message.text)

    await state.update_data(
        rent=rent
    )

    await state.set_state(
        PropertyForm.vacancy_date
    )

    await message.answer(
        "📅 تاریخ تخلیه را وارد کن:\n"
        "اگر مشخص نیست بنویس: نامشخص"
    )


@router.message(PropertyForm.vacancy_date)
async def property_vacancy_date(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        vacancy_date=normalize_text(message.text)
    )

    await state.set_state(
        PropertyForm.document_type
    )

    await message.answer(
        "📄 نوع سند را وارد کن:"
    )


@router.message(PropertyForm.document_type)
async def property_document_type(
    message: Message,
    state: FSMContext,
):
    value = normalize_text(message.text)

    await state.update_data(
        document_type=value
    )

    await state.set_state(
        PropertyForm.owner_name
    )

    await message.answer(
        "👤 نام مالک:"
    )


@router.message(PropertyForm.owner_name)
async def property_owner_name(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        owner_name=normalize_text(message.text)
    )

    await state.set_state(
        PropertyForm.owner_phone
    )

    await message.answer(
        "📱 شماره مالک:"
    )


@router.message(PropertyForm.owner_phone)
async def property_owner_phone(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        owner_phone=normalize_text(message.text)
    )

    await state.set_state(
        PropertyForm.description
    )

    await message.answer(
        "📝 توضیحات فایل:"
    )


@router.message(PropertyForm.description)
async def property_description(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        description=normalize_text(message.text)
    )

    data = await state.get_data()

    preview = (
        "📋 <b>پیش‌نمایش فایل</b>\n\n"
        f"🔖 کد: {safe(data.get('code'))}\n"
        f"📍 منطقه: {safe(data.get('area'))}\n"
        f"📌 آدرس: {safe(data.get('address'))}\n"
        f"📐 متراژ: {format_number(data.get('sqm'))}\n"
        f"💰 قیمت: {price_text(data.get('price'))}\n"
        f"🏠 نوع: {safe(data.get('property_type'))}\n"
        f"🛏 خواب: {data.get('bedrooms', 0)}\n"
        f"🏢 طبقات: {data.get('floors', 0)}\n"
        f"🔢 طبقه: {data.get('unit_floor', 0)}\n"
        f"🚪 واحد/طبقه: {data.get('units_per_floor', 0)}\n"
        f"📅 سال ساخت: {year_text(data.get('year_built'))}\n"
        f"🛗 آسانسور: {safe(data.get('elevator'))}\n"
        f"🚗 پارکینگ: {safe(data.get('parking'))}\n"
        f"📦 انباری: {safe(data.get('storage'))}\n"
        f"👤 مالک: {safe(data.get('owner_name'))}\n"
        f"📱 تلفن: {safe(data.get('owner_phone'))}\n"
        f"📄 سند: {safe(data.get('document_type'))}\n"
        f"📝 توضیحات: {safe(data.get('description'))}\n"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ ثبت نهایی",
                    callback_data="property_confirm",
                ),
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="property_cancel",
                ),
            ]
        ]
    )

    await state.set_state(
        PropertyForm.confirm
    )

    await message.answer(
        preview,
        reply_markup=keyboard,
    )


@router.callback_query(
    PropertyForm.confirm,
    F.data == "property_cancel",
)
async def property_confirm_cancel(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await callback.message.edit_text(
        "ثبت فایل لغو شد."
    )

    await callback.message.answer(
        "منوی اصلی:",
        reply_markup=main_keyboard(
            is_admin(callback.from_user.id)
        ),
    )

    await callback.answer()


@router.callback_query(
    PropertyForm.confirm,
    F.data == "property_confirm",
)
async def property_confirm(
    callback: CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.code == data["code"]
            )
        )

        if result.scalar_one_or_none():
            await callback.answer(
                "این کد قبلاً ثبت شده.",
                show_alert=True,
            )
            return

        property_obj = Property(
            code=data.get("code", ""),
            area=data.get("area", ""),
            address=data.get("address", ""),
            sqm=data.get("sqm", 0),
            price=data.get("price", 0),
            property_type=data.get(
                "property_type",
                "",
            ),
            bedrooms=data.get(
                "bedrooms",
                0,
            ),
            floors=data.get(
                "floors",
                0,
            ),
            unit_floor=data.get(
                "unit_floor",
                0,
            ),
            units_per_floor=data.get(
                "units_per_floor",
                0,
            ),
            year_built=data.get(
                "year_built",
                0,
            ),
            elevator=data.get(
                "elevator",
                "",
            ),
            parking=data.get(
                "parking",
                "",
            ),
            parking_type=data.get(
                "parking_type",
                "",
            ),
            storage=data.get(
                "storage",
                "",
            ),
            tenant=data.get(
                "tenant",
                "",
            ),
            deposit=data.get(
                "deposit",
                0,
            ),
            rent=data.get(
                "rent",
                0,
            ),
            vacancy_date=data.get(
                "vacancy_date",
                "",
            ),
            document_type=data.get(
                "document_type",
                "",
            ),
            owner_name=data.get(
                "owner_name",
                "",
            ),
            owner_phone=data.get(
                "owner_phone",
                "",
            ),
            description=data.get(
                "description",
                "",
            ),
            status="🟢 فعال",
            created_by=callback.from_user.id,
        )

        session.add(property_obj)

        await session.flush()

        await log_activity(
            session=session,
            user_id=callback.from_user.id,
            activity_type="ثبت فایل",
            description=(
                f"ثبت فایل {property_obj.code}"
            ),
            property_id=property_obj.id,
        )

        await session.commit()

        property_id = property_obj.id

    await state.clear()

    await callback.message.edit_text(
        "✅ <b>فایل با موفقیت ثبت شد.</b>\n\n"
        f"🔖 کد: {data.get('code')}\n"
        f"📍 {data.get('area')}\n"
        f"📅 سال ساخت: "
        f"{year_text(data.get('year_built'))}"
    )

    await callback.message.answer(
        "منوی اصلی:",
        reply_markup=main_keyboard(
            is_admin(callback.from_user.id)
        ),
    )

    await callback.answer()


# ============================================================
# PROPERTY LIST
# ============================================================

async def send_property_page(
    message: Message,
    page: int = 1,
):
    async with SessionLocal() as session:

        count_result = await session.execute(
            select(func.count(Property.id)).where(
                Property.status.in_(
                    ACTIVE_PROPERTY_STATUSES
                )
            )
        )

        total = count_result.scalar() or 0

        total_pages = max(
            1,
            (total + PAGE_SIZE - 1) // PAGE_SIZE,
        )

        page = max(
            1,
            min(page, total_pages),
        )

        result = await session.execute(
            select(Property)
            .where(
                Property.status.in_(
                    ACTIVE_PROPERTY_STATUSES
                )
            )
            .order_by(
                desc(Property.created_at)
            )
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        )

        properties = result.scalars().all()

    if not properties:
        await message.answer(
            "📂 هیچ فایل فعالی ثبت نشده."
        )
        return

    text = (
        f"📂 <b>فایل‌های فعال</b>\n"
        f"صفحه {page} از {total_pages} — "
        f"{total} فایل\n\n"
    )

    for index, p in enumerate(properties, 1):
        text += (
            f"{index}. "
            f"<b>{safe(p.code)}</b> | "
            f"{safe(p.area)} | "
            f"{format_number(p.sqm)}م | "
            f"{price_text(p.price)}\n"
            f"   📅 {year_text(p.year_built)} | "
            f"{safe(p.status)}\n\n"
        )

    keyboard_rows = []

    for p in properties:
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"🏠 {p.code}",
                callback_data=f"pdetail:{p.id}",
            )
        ])

    pagination = pagination_keyboard(
        "plist",
        page,
        total_pages,
    )

    keyboard_rows.extend(
        pagination.inline_keyboard
    )

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard_rows
        ),
    )


@router.message(F.text == "📂 فایل‌ها")
async def property_list(
    message: Message,
):
    await send_property_page(
        message,
        page=1,
    )


@router.callback_query(
    F.data.startswith("plist:")
)
async def property_list_page(
    callback: CallbackQuery,
):
    page = int(
        callback.data.split(":")[1]
    )

    await callback.message.delete()

    await send_property_page(
        callback.message,
        page=page,
    )

    await callback.answer()


# ============================================================
# PROPERTY DETAIL
# ============================================================

async def send_property_detail(
    message: Message,
    property_id: int,
):
    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id == property_id
            )
        )

        p = result.scalar_one_or_none()

    if not p:
        await message.answer(
            "فایل پیدا نشد."
        )
        return

    text = (
        f"🏠 <b>جزئیات فایل {safe(p.code)}</b>\n\n"
        f"📍 منطقه: {safe(p.area)}\n"
        f"📌 آدرس: {safe(p.address)}\n"
        f"📐 متراژ: {format_number(p.sqm)} متر\n"
        f"💰 قیمت: {price_text(p.price)}\n"
        f"🏠 نوع: {safe(p.property_type)}\n"
        f"🛏 خواب: {p.bedrooms}\n"
        f"🏢 طبقات: {p.floors}\n"
        f"🔢 طبقه: {p.unit_floor}\n"
        f"🚪 واحد/طبقه: {p.units_per_floor}\n"
        f"📅 سال ساخت: {year_text(p.year_built)}\n"
        f"🛗 آسانسور: {safe(p.elevator)}\n"
        f"🚗 پارکینگ: {safe(p.parking)}\n"
        f"🅿️ نوع پارکینگ: {safe(p.parking_type)}\n"
        f"📦 انباری: {safe(p.storage)}\n"
        f"👤 مستأجر: {safe(p.tenant)}\n"
        f"💵 ودیعه: {price_text(p.deposit)}\n"
        f"💵 اجاره: {price_text(p.rent)}\n"
        f"📅 تخلیه: {safe(p.vacancy_date)}\n"
        f"📄 سند: {safe(p.document_type)}\n"
        f"👤 مالک: {safe(p.owner_name)}\n"
        f"📱 تلفن مالک: {safe(p.owner_phone)}\n"
        f"📌 وضعیت: {safe(p.status)}\n"
        f"📝 توضیحات: {safe(p.description)}"
    )

    await message.answer(
        text,
        reply_markup=property_detail_keyboard(
            property_id,
            is_admin_user=is_admin(
                message.chat.id
            ),
        ),
    )


@router.callback_query(
    F.data.startswith("pdetail:")
)
async def property_detail_callback(
    callback: CallbackQuery,
):
    property_id = int(
        callback.data.split(":")[1]
    )

    await send_property_detail(
        callback.message,
        property_id,
    )

    await callback.answer()


# ============================================================
# REGISTER CLIENT
# ============================================================

@router.message(F.text == "👥 ثبت مشتری")
async def client_start(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await state.set_state(
        ClientForm.code
    )

    await message.answer(
        "🔖 کد مشتری:",
        reply_markup=cancel_keyboard(),
    )


@router.message(ClientForm.code)
async def client_code(
    message: Message,
    state: FSMContext,
):
    code = normalize_text(message.text)

    async with SessionLocal() as session:
        result = await session.execute(
            select(Client).where(
                Client.code == code
            )
        )

        if result.scalar_one_or_none():
            await message.answer(
                "⚠️ این کد مشتری قبلاً ثبت شده."
            )
            return

    await state.update_data(
        code=code
    )

    await state.set_state(
        ClientForm.name
    )

    await message.answer(
        "👤 نام مشتری:"
    )


@router.message(ClientForm.name)
async def client_name(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        name=normalize_text(message.text)
    )

    await state.set_state(
        ClientForm.phone
    )

    await message.answer(
        "📱 شماره تماس مشتری:"
    )


@router.message(ClientForm.phone)
async def client_phone(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        phone=normalize_text(message.text)
    )

    await state.set_state(
        ClientForm.area
    )

    await message.answer(
        "📍 منطقه موردنظر مشتری:\n"
        "مثلاً خانی‌آباد\n"
        "یا «همه»"
    )


@router.message(ClientForm.area)
async def client_area(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        area=normalize_text(message.text)
    )

    await state.set_state(
        ClientForm.min_budget
    )

    await message.answer(
        "💰 حداقل بودجه:"
    )


@router.message(ClientForm.min_budget)
async def client_min_budget(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        min_budget=parse_number(message.text)
    )

    await state.set_state(
        ClientForm.max_budget
    )

    await message.answer(
        "💰 حداکثر بودجه:"
    )


@router.message(ClientForm.max_budget)
async def client_max_budget(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        max_budget=parse_number(message.text)
    )

    await state.set_state(
        ClientForm.min_sqm
    )

    await message.answer(
        "📐 حداقل متراژ:"
    )


@router.message(ClientForm.min_sqm)
async def client_min_sqm(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        min_sqm=parse_number(message.text)
    )

    await state.set_state(
        ClientForm.max_sqm
    )

    await message.answer(
        "📐 حداکثر متراژ:"
    )


@router.message(ClientForm.max_sqm)
async def client_max_sqm(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        max_sqm=parse_number(message.text)
    )

    await state.set_state(
        ClientForm.property_type
    )

    await message.answer(
        "🏠 نوع ملک موردنظر:"
    )


@router.message(ClientForm.property_type)
async def client_property_type(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        property_type=normalize_text(
            message.text
        )
    )

    await state.set_state(
        ClientForm.min_year_built
    )

    await message.answer(
        "📅 حداقل سال ساخت موردنظر:\n"
        "اگر مهم نیست 0 بزن."
    )


@router.message(ClientForm.min_year_built)
async def client_min_year(
    message: Message,
    state: FSMContext,
):
    year = int(
        parse_number(message.text)
    )

    if year != 0 and not (
        1200 <= year <= 1600
    ):
        await message.answer(
            "سال ساخت معتبر نیست. "
            "مثلاً 1400 یا 0."
        )
        return

    await state.update_data(
        min_year_built=year
    )

    await state.set_state(
        ClientForm.max_year_built
    )

    await message.answer(
        "📅 حداکثر سال ساخت موردنظر:\n"
        "اگر مهم نیست 0 بزن."
    )


@router.message(ClientForm.max_year_built)
async def client_max_year(
    message: Message,
    state: FSMContext,
):
    year = int(
        parse_number(message.text)
    )

    if year != 0 and not (
        1200 <= year <= 1600
    ):
        await message.answer(
            "سال ساخت معتبر نیست."
        )
        return

    await state.update_data(
        max_year_built=year
    )

    await state.set_state(
        ClientForm.bedrooms
    )

    await message.answer(
        "🛏 تعداد خواب موردنظر:"
    )


@router.message(ClientForm.bedrooms)
async def client_bedrooms(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        bedrooms=int(
            parse_number(message.text)
        )
    )

    await state.set_state(
        ClientForm.description
    )

    await message.answer(
        "📝 توضیحات و نیاز مشتری:"
    )


@router.message(ClientForm.description)
async def client_description(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        description=normalize_text(
            message.text
        )
    )

    data = await state.get_data()

    text = (
        "👤 <b>پیش‌نمایش مشتری</b>\n\n"
        f"🔖 کد: {safe(data.get('code'))}\n"
        f"👤 نام: {safe(data.get('name'))}\n"
        f"📱 تلفن: {safe(data.get('phone'))}\n"
        f"📍 منطقه: {safe(data.get('area'))}\n"
        f"💰 بودجه: "
        f"{price_text(data.get('min_budget'))} "
        f"تا {price_text(data.get('max_budget'))}\n"
        f"📐 متراژ: "
        f"{format_number(data.get('min_sqm'))} "
        f"تا {format_number(data.get('max_sqm'))}\n"
        f"🏠 نوع: {safe(data.get('property_type'))}\n"
        f"📅 سال ساخت: "
        f"{data.get('min_year_built') or '—'} "
        f"تا {data.get('max_year_built') or '—'}\n"
        f"🛏 خواب: {data.get('bedrooms', 0)}\n"
        f"📝 توضیحات: {safe(data.get('description'))}"
    )

    await state.set_state(
        ClientForm.confirm
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ ثبت نهایی",
                    callback_data="client_confirm",
                ),
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="client_cancel",
                ),
            ]
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard,
    )


@router.callback_query(
    ClientForm.confirm,
    F.data == "client_cancel",
)
async def client_cancel(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await callback.message.edit_text(
        "ثبت مشتری لغو شد."
    )

    await callback.message.answer(
        "منوی اصلی:",
        reply_markup=main_keyboard(
            is_admin(callback.from_user.id)
        ),
    )

    await callback.answer()


@router.callback_query(
    ClientForm.confirm,
    F.data == "client_confirm",
)
async def client_confirm(
    callback: CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client).where(
                Client.code == data["code"]
            )
        )

        if result.scalar_one_or_none():
            await callback.answer(
                "این کد مشتری قبلاً ثبت شده.",
                show_alert=True,
            )
            return

        client = Client(
            code=data.get("code", ""),
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            area=data.get("area", ""),
            min_budget=data.get(
                "min_budget",
                0,
            ),
            max_budget=data.get(
                "max_budget",
                0,
            ),
            min_sqm=data.get(
                "min_sqm",
                0,
            ),
            max_sqm=data.get(
                "max_sqm",
                0,
            ),
            property_type=data.get(
                "property_type",
                "",
            ),
            min_year_built=data.get(
                "min_year_built",
                0,
            ),
            max_year_built=data.get(
                "max_year_built",
                0,
            ),
            bedrooms=data.get(
                "bedrooms",
                0,
            ),
            description=data.get(
                "description",
                "",
            ),
            status="فعال",
            created_by=callback.from_user.id,
        )

        session.add(client)

        await session.flush()

        await log_activity(
            session=session,
            user_id=callback.from_user.id,
            activity_type="ثبت مشتری",
            description=(
                f"ثبت مشتری {client.code}"
            ),
            client_id=client.id,
        )

        await session.commit()

    await state.clear()

    await callback.message.edit_text(
        "✅ <b>مشتری با موفقیت ثبت شد.</b>\n\n"
        f"🔖 کد: {data.get('code')}\n"
        f"👤 {data.get('name')}\n"
        f"📍 {data.get('area')}"
    )

    await callback.message.answer(
        "منوی اصلی:",
        reply_markup=main_keyboard(
            is_admin(callback.from_user.id)
        ),
    )

    await callback.answer()


# ============================================================
# CLIENT LIST
# ============================================================

async def send_client_page(
    message: Message,
    page: int = 1,
):
    async with SessionLocal() as session:

        count_result = await session.execute(
            select(func.count(Client.id)).where(
                Client.status == "فعال"
            )
        )

        total = count_result.scalar() or 0

        total_pages = max(
            1,
            (total + PAGE_SIZE - 1)
            // PAGE_SIZE,
        )

        page = max(
            1,
            min(page, total_pages),
        )

        result = await session.execute(
            select(Client)
            .where(
                Client.status == "فعال"
            )
            .order_by(
                desc(Client.created_at)
            )
            .offset(
                (page - 1) * PAGE_SIZE
            )
            .limit(PAGE_SIZE)
        )

        clients = result.scalars().all()

    if not clients:
        await message.answer(
            "👤 مشتری فعال وجود ندارد."
        )
        return

    text = (
        f"👥 <b>مشتری‌های فعال</b>\n"
        f"صفحه {page} از {total_pages} — "
        f"{total} مشتری\n\n"
    )

    rows = []

    for c in clients:
        text += (
            f"👤 <b>{safe(c.name)}</b> | "
            f"{safe(c.code)}\n"
            f"   📍 {safe(c.area)} | "
            f"💰 {price_text(c.max_budget)}\n\n"
        )

        rows.append([
            InlineKeyboardButton(
                text=f"👤 {c.code} - {c.name}",
                callback_data=f"cdetail:{c.id}",
            )
        ])

    pagination = pagination_keyboard(
        "clist",
        page,
        total_pages,
    )

    rows.extend(
        pagination.inline_keyboard
    )

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )


@router.message(F.text == "👤 مشتری‌ها")
async def client_list(
    message: Message,
):
    await send_client_page(
        message,
        1,
    )


@router.callback_query(
    F.data.startswith("clist:")
)
async def client_list_page(
    callback: CallbackQuery,
):
    page = int(
        callback.data.split(":")[1]
    )

    await callback.message.delete()

    await send_client_page(
        callback.message,
        page,
    )

    await callback.answer()


# ============================================================
# CLIENT DETAIL
# ============================================================

@router.callback_query(
    F.data.startswith("cdetail:")
)
async def client_detail(
    callback: CallbackQuery,
):
    client_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:
        result = await session.execute(
            select(Client).where(
                Client.id == client_id
            )
        )

        client = result.scalar_one_or_none()

    if not client:
        await callback.answer(
            "مشتری پیدا نشد.",
            show_alert=True,
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎯 مچینگ",
                    callback_data=(
                        f"match:{client.id}:1"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 تغییر وضعیت",
                    callback_data=(
                        f"cstatus:{client.id}"
                    ),
                ),
            ],
        ]
    )

    await callback.message.answer(
        client_summary(client),
        reply_markup=keyboard,
    )

    await callback.answer()


# ============================================================
# OWNER FILES
# ============================================================

@router.message(F.text == "🏠 فایل‌های مالک")
async def owner_files_start(
    message: Message,
):
    await message.answer(
        "نام مالک یا شماره مالک را وارد کن:"
    )

    # The next message is handled by the lightweight
    # owner-search handler below through temporary state.
    await owner_search_state.set(
        message.from_user.id
    )


class OwnerSearchState:
    _users = set()

    @classmethod
    def set(cls, user_id):
        cls._users.add(user_id)

    @classmethod
    def has(cls, user_id):
        return user_id in cls._users

    @classmethod
    def clear(cls, user_id):
        cls._users.discard(user_id)


owner_search_state = OwnerSearchState()


@router.message(
    lambda message:
    owner_search_state.has(
        message.from_user.id
    )
)
async def owner_files_search(
    message: Message,
):
    query = normalize_text(message.text)

    owner_search_state.clear(
        message.from_user.id
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property)
            .where(
                Property.status.in_(
                    ACTIVE_PROPERTY_STATUSES
                ),
                or_(
                    Property.owner_name.ilike(
                        f"%{query}%"
                    ),
                    Property.owner_phone.ilike(
                        f"%{query}%"
                    ),
                ),
            )
            .order_by(
                desc(Property.created_at)
            )
        )

        properties = result.scalars().all()

    if not properties:
        await message.answer(
            "فایل فعالی برای این مالک پیدا نشد."
        )
        return

    text = (
        f"🏠 <b>فایل‌های مالک: "
        f"{query}</b>\n\n"
    )

    rows = []

    for p in properties:
        text += (
            f"🔖 {safe(p.code)} | "
            f"{safe(p.area)} | "
            f"{format_number(p.sqm)} متر | "
            f"{price_text(p.price)}\n"
        )

        rows.append([
            InlineKeyboardButton(
                text=f"🏠 {p.code}",
                callback_data=f"pdetail:{p.id}",
            )
        ])

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )
    # ============================================================
# SEARCH PROPERTY
# ============================================================

def property_search_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 منطقه")],
            [KeyboardButton(text="💰 حداقل قیمت")],
            [KeyboardButton(text="💰 حداکثر قیمت")],
            [KeyboardButton(text="📐 حداقل متراژ")],
            [KeyboardButton(text="📐 حداکثر متراژ")],
            [KeyboardButton(text="🏠 نوع ملک")],
            [KeyboardButton(text="📅 حداقل سال ساخت")],
            [KeyboardButton(text="📅 حداکثر سال ساخت")],
            [KeyboardButton(text="👤 مالک")],
            [KeyboardButton(text="🔖 کد فایل")],
            [KeyboardButton(text="🔎 جستجوی نهایی")],
            [KeyboardButton(text="❌ لغو")],
        ],
        resize_keyboard=True,
    )


@router.message(F.text == "🔎 جستجوی فایل")
async def property_search_start(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await state.update_data(
        search_kind="property",
        search_filters={},
    )

    await message.answer(
        "🔎 <b>جستجوی فایل</b>\n\n"
        "می‌توانی فیلترها را یکی‌یکی وارد کنی.\n"
        "در پایان «جستجوی نهایی» را بزن.",
        reply_markup=property_search_keyboard(),
    )


@router.message(F.text == "📍 منطقه")
async def search_property_area(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="area"
    )

    await message.answer(
        "📍 منطقه موردنظر را وارد کن:"
    )


@router.message(F.text == "💰 حداقل قیمت")
async def search_property_min_price(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="min_price"
    )

    await message.answer(
        "💰 حداقل قیمت را وارد کن:"
    )


@router.message(F.text == "💰 حداکثر قیمت")
async def search_property_max_price(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="max_price"
    )

    await message.answer(
        "💰 حداکثر قیمت را وارد کن:"
    )


@router.message(F.text == "📐 حداقل متراژ")
async def search_property_min_sqm(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="min_sqm"
    )

    await message.answer(
        "📐 حداقل متراژ:"
    )


@router.message(F.text == "📐 حداکثر متراژ")
async def search_property_max_sqm(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="max_sqm"
    )

    await message.answer(
        "📐 حداکثر متراژ:"
    )


@router.message(F.text == "🏠 نوع ملک")
async def search_property_type(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="property_type"
    )

    await message.answer(
        "🏠 نوع ملک را وارد کن:"
    )


@router.message(F.text == "📅 حداقل سال ساخت")
async def search_property_min_year(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="min_year"
    )

    await message.answer(
        "📅 حداقل سال ساخت:"
    )


@router.message(F.text == "📅 حداکثر سال ساخت")
async def search_property_max_year(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="max_year"
    )

    await message.answer(
        "📅 حداکثر سال ساخت:"
    )


@router.message(F.text == "👤 مالک")
async def search_property_owner(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="owner"
    )

    await message.answer(
        "👤 نام یا شماره مالک:"
    )


@router.message(F.text == "🔖 کد فایل")
async def search_property_code(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    await state.update_data(
        search_step="code"
    )

    await message.answer(
        "🔖 کد فایل:"
    )


# ============================================================
# PROPERTY SEARCH INPUT ROUTER
# ============================================================

@router.message()
async def property_search_input_router(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    step = data.get("search_step")

    if not step:
        return

    filters = data.get(
        "search_filters",
        {},
    )

    value = normalize_text(message.text)

    if step == "area":
        filters["area"] = value

    elif step == "min_price":
        filters["min_price"] = parse_number(value)

    elif step == "max_price":
        filters["max_price"] = parse_number(value)

    elif step == "min_sqm":
        filters["min_sqm"] = parse_number(value)

    elif step == "max_sqm":
        filters["max_sqm"] = parse_number(value)

    elif step == "property_type":
        filters["property_type"] = value

    elif step == "min_year":
        filters["min_year"] = int(
            parse_number(value)
        )

    elif step == "max_year":
        filters["max_year"] = int(
            parse_number(value)
        )

    elif step == "owner":
        filters["owner"] = value

    elif step == "code":
        filters["code"] = value

    else:
        return

    await state.update_data(
        search_filters=filters,
        search_step=None,
    )

    await message.answer(
        "✅ فیلتر ثبت شد.\n"
        "فیلتر بعدی را انتخاب کن یا «جستجوی نهایی» را بزن.",
        reply_markup=property_search_keyboard(),
    )


# ============================================================
# PROPERTY SEARCH EXECUTION
# ============================================================

@router.message(F.text == "🔎 جستجوی نهایی")
async def property_search_execute(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "property":
        return

    filters = data.get(
        "search_filters",
        {},
    )

    await state.update_data(
        property_search_filters=filters,
        property_search_page=1,
    )

    await send_property_search_results(
        message,
        state,
        page=1,
    )


async def send_property_search_results(
    message: Message,
    state: FSMContext,
    page: int = 1,
):
    data = await state.get_data()

    filters = data.get(
        "property_search_filters",
        {},
    )

    conditions = [
        Property.status.in_(
            ACTIVE_PROPERTY_STATUSES
        )
    ]

    area = filters.get("area")

    if area and area not in (
        "همه",
        "همه مناطق",
        "فرقی ندارد",
    ):
        conditions.append(
            Property.area.ilike(
                f"%{area}%"
            )
        )

    min_price = filters.get("min_price", 0)

    if min_price:
        conditions.append(
            Property.price >= min_price
        )

    max_price = filters.get("max_price", 0)

    if max_price:
        conditions.append(
            Property.price <= max_price
        )

    min_sqm = filters.get("min_sqm", 0)

    if min_sqm:
        conditions.append(
            Property.sqm >= min_sqm
        )

    max_sqm = filters.get("max_sqm", 0)

    if max_sqm:
        conditions.append(
            Property.sqm <= max_sqm
        )

    property_type = filters.get(
        "property_type"
    )

    if property_type and property_type not in (
        "همه",
        "همه انواع",
        "فرقی ندارد",
    ):
        conditions.append(
            Property.property_type.ilike(
                f"%{property_type}%"
            )
        )

    min_year = filters.get(
        "min_year",
        0,
    )

    if min_year:
        conditions.append(
            Property.year_built >= min_year
        )

    max_year = filters.get(
        "max_year",
        0,
    )

    if max_year:
        conditions.append(
            Property.year_built <= max_year
        )

    owner = filters.get("owner")

    if owner:
        conditions.append(
            or_(
                Property.owner_name.ilike(
                    f"%{owner}%"
                ),
                Property.owner_phone.ilike(
                    f"%{owner}%"
                ),
            )
        )

    code = filters.get("code")

    if code:
        conditions.append(
            Property.code.ilike(
                f"%{code}%"
            )
        )

    async with SessionLocal() as session:

        count_result = await session.execute(
            select(
                func.count(Property.id)
            ).where(
                and_(*conditions)
            )
        )

        total = count_result.scalar() or 0

        total_pages = max(
            1,
            (total + PAGE_SIZE - 1)
            // PAGE_SIZE,
        )

        page = max(
            1,
            min(page, total_pages),
        )

        result = await session.execute(
            select(Property)
            .where(
                and_(*conditions)
            )
            .order_by(
                desc(Property.created_at)
            )
            .offset(
                (page - 1) * PAGE_SIZE
            )
            .limit(PAGE_SIZE)
        )

        properties = result.scalars().all()

    if not properties:
        await message.answer(
            "🔎 فایل زنده مناسبی با این فیلترها پیدا نشد."
        )
        return

    text = (
        "🔎 <b>نتایج جستجوی فایل</b>\n"
        f"صفحه {page} از {total_pages} — "
        f"{total} فایل\n\n"
    )

    rows = []

    for p in properties:
        text += (
            f"🏠 <b>{safe(p.code)}</b>\n"
            f"📍 {safe(p.area)} | "
            f"📐 {format_number(p.sqm)} متر\n"
            f"💰 {price_text(p.price)} | "
            f"📅 {year_text(p.year_built)}\n"
            f"🏗 {safe(p.property_type)}\n\n"
        )

        rows.append([
            InlineKeyboardButton(
                text=f"🏠 {p.code}",
                callback_data=f"pdetail:{p.id}",
            )
        ])

    pagination = pagination_keyboard(
        "psearch",
        page,
        total_pages,
    )

    rows.extend(
        pagination.inline_keyboard
    )

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows,
        ),
    )


@router.callback_query(
    F.data.startswith("psearch:")
)
async def property_search_page(
    callback: CallbackQuery,
    state: FSMContext,
):
    page = int(
        callback.data.split(":")[1]
    )

    await send_property_search_results(
        callback.message,
        state,
        page,
    )

    await callback.answer()


# ============================================================
# FREE TEXT PROPERTY SEARCH
# ============================================================

def extract_price_from_text(text: str):
    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        text.replace(",", ""),
    )

    if not numbers:
        return None

    return float(numbers[-1])


@router.message(
    F.text.startswith("🔎"),
    ~F.text.in_([
        "🔎 جستجوی فایل",
        "🔎 جستجوی مشتری",
    ]),
)
async def free_search(
    message: Message,
    state: FSMContext,
):
    query = normalize_text(
        message.text
    ).replace("🔎", "").strip()

    if not query:
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property)
            .where(
                Property.status.in_(
                    ACTIVE_PROPERTY_STATUSES
                ),
                or_(
                    Property.code.ilike(
                        f"%{query}%"
                    ),
                    Property.area.ilike(
                        f"%{query}%"
                    ),
                    Property.address.ilike(
                        f"%{query}%"
                    ),
                    Property.owner_name.ilike(
                        f"%{query}%"
                    ),
                    Property.description.ilike(
                        f"%{query}%"
                    ),
                ),
            )
            .order_by(
                desc(Property.created_at)
            )
            .limit(PAGE_SIZE)
        )

        properties = result.scalars().all()

    if not properties:
        await message.answer(
            "فایل مناسبی پیدا نشد."
        )
        return

    rows = []

    text = (
        f"🔎 <b>نتایج: {query}</b>\n\n"
    )

    for p in properties:
        text += (
            f"🏠 <b>{p.code}</b> | "
            f"{safe(p.area)} | "
            f"{format_number(p.sqm)} متر | "
            f"{price_text(p.price)}\n"
        )

        rows.append([
            InlineKeyboardButton(
                text=f"🏠 {p.code}",
                callback_data=f"pdetail:{p.id}",
            )
        ])

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )


# ============================================================
# PROPERTY EDIT
# ============================================================

PROPERTY_EDIT_FIELDS = {
    "code": "🔖 کد",
    "area": "📍 منطقه",
    "address": "📌 آدرس",
    "sqm": "📐 متراژ",
    "price": "💰 قیمت",
    "property_type": "🏠 نوع ملک",
    "bedrooms": "🛏 خواب",
    "floors": "🏢 طبقات",
    "unit_floor": "🔢 طبقه",
    "units_per_floor": "🚪 واحد در طبقه",
    "year_built": "📅 سال ساخت",
    "elevator": "🛗 آسانسور",
    "parking": "🚗 پارکینگ",
    "parking_type": "🅿️ نوع پارکینگ",
    "storage": "📦 انباری",
    "tenant": "👤 مستأجر",
    "deposit": "💵 ودیعه",
    "rent": "💵 اجاره",
    "vacancy_date": "📅 تخلیه",
    "document_type": "📄 نوع سند",
    "owner_name": "👤 نام مالک",
    "owner_phone": "📱 شماره مالک",
    "description": "📝 توضیحات",
}


def property_edit_keyboard(
    property_id: int,
):
    rows = []

    items = list(
        PROPERTY_EDIT_FIELDS.items()
    )

    for i in range(0, len(items), 2):
        row = []

        for field, title in items[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    text=title,
                    callback_data=(
                        f"editfield:{property_id}:{field}"
                    ),
                )
            )

        rows.append(row)

    rows.append([
        InlineKeyboardButton(
            text="🔙 بستن",
            callback_data="edit_close",
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


@router.callback_query(
    F.data.startswith("pedit:")
)
async def property_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
):
    property_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:
        result = await session.execute(
            select(Property).where(
                Property.id == property_id
            )
        )

        p = result.scalar_one_or_none()

    if not p:
        await callback.answer(
            "فایل پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "✏️ <b>فیلد موردنظر برای ویرایش را انتخاب کن:</b>",
        reply_markup=property_edit_keyboard(
            property_id
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("editfield:")
)
async def property_edit_field(
    callback: CallbackQuery,
    state: FSMContext,
):
    parts = callback.data.split(":")

    property_id = int(parts[1])
    field = parts[2]

    if field not in PROPERTY_EDIT_FIELDS:
        await callback.answer(
            "فیلد نامعتبر.",
            show_alert=True,
        )
        return

    await state.set_state(
        PropertyEditForm.value
    )

    await state.update_data(
        edit_property_id=property_id,
        edit_field=field,
    )

    await callback.message.answer(
        f"✏️ مقدار جدید برای "
        f"<b>{PROPERTY_EDIT_FIELDS[field]}</b> را وارد کن:"
    )

    await callback.answer()


@router.message(
    PropertyEditForm.value
)
async def property_edit_value(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    property_id = data.get(
        "edit_property_id"
    )

    field = data.get(
        "edit_field"
    )

    if not property_id or not field:
        await state.clear()
        return

    raw_value = normalize_text(
        message.text
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id == property_id
            )
        )

        p = result.scalar_one_or_none()

        if not p:
            await state.clear()
            await message.answer(
                "فایل پیدا نشد."
            )
            return

        old_value = getattr(
            p,
            field,
        )

        # ----------------------------------------------------
        # Convert value according to field
        # ----------------------------------------------------

        numeric_float_fields = {
            "sqm",
            "price",
            "deposit",
            "rent",
        }

        numeric_int_fields = {
            "bedrooms",
            "floors",
            "unit_floor",
            "units_per_floor",
            "year_built",
        }

        if field in numeric_float_fields:
            new_value = parse_number(
                raw_value
            )

        elif field in numeric_int_fields:
            new_value = int(
                parse_number(raw_value)
            )

            if field == "year_built":
                if new_value != 0 and not (
                    1200 <= new_value <= 1600
                ):
                    await message.answer(
                        "سال ساخت معتبر نیست."
                    )
                    return

        else:
            new_value = raw_value

        # ----------------------------------------------------
        # Unique code
        # ----------------------------------------------------

        if field == "code":

            existing = await session.execute(
                select(Property).where(
                    Property.code == new_value,
                    Property.id != property_id,
                )
            )

            if existing.scalar_one_or_none():
                await message.answer(
                    "⚠️ این کد قبلاً استفاده شده."
                )
                return

        setattr(
            p,
            field,
            new_value,
        )

        # ----------------------------------------------------
        # Tenant changed to no tenant
        # ----------------------------------------------------

        if (
            field == "tenant"
            and new_value == "مستأجر ندارد"
        ):
            p.deposit = 0
            p.rent = 0
            p.vacancy_date = ""

        await add_property_history(
            session=session,
            property_id=property_id,
            user_id=message.from_user.id,
            field_name=field,
            old_value=old_value,
            new_value=new_value,
            event_type=(
                "تغییر قیمت"
                if field == "price"
                else "سایر"
            ),
        )

        await log_activity(
            session=session,
            user_id=message.from_user.id,
            property_id=property_id,
            activity_type=(
                "تغییر قیمت"
                if field == "price"
                else "ویرایش فایل"
            ),
            description=(
                f"{field}: "
                f"{old_value} → {new_value}"
            ),
        )

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ تغییر با موفقیت ثبت شد."
    )

    await send_property_detail(
        message,
        property_id,
    )


@router.callback_query(
    F.data == "edit_close"
)
async def property_edit_close(
    callback: CallbackQuery,
):
    await callback.answer()


# ============================================================
# PROPERTY STATUS
# ============================================================

@router.callback_query(
    F.data.startswith("pstatus:")
)
async def property_status_start(
    callback: CallbackQuery,
    state: FSMContext,
):
    property_id = int(
        callback.data.split(":")[1]
    )

    await state.set_state(
        StatusForm.value
    )

    await state.update_data(
        status_property_id=property_id
    )

    await callback.message.answer(
        "📌 وضعیت جدید فایل را انتخاب کن:",
        reply_markup=status_keyboard(),
    )

    await callback.answer()


@router.message(
    StatusForm.value
)
async def property_status_value(
    message: Message,
    state: FSMContext,
):
    status = normalize_text(
        message.text
    )

    if status not in PROPERTY_STATUSES:
        await message.answer(
            "یکی از وضعیت‌های موجود را انتخاب کن."
        )
        return

    data = await state.get_data()

    property_id = data.get(
        "status_property_id"
    )

    if not property_id:
        await state.clear()
        return

    await state.update_data(
        new_property_status=status
    )

    if status == "🔵 معامله شد - توسط ما":
        await state.set_state(
            StatusForm.transaction_value
        )

        await message.answer(
            "💰 ارزش معامله را وارد کن:"
        )

        return

    await save_property_status(
        message,
        state,
        status,
        0,
    )


@router.message(
    StatusForm.transaction_value
)
async def property_transaction_value(
    message: Message,
    state: FSMContext,
):
    value = parse_number(
        message.text
    )

    data = await state.get_data()

    status = data.get(
        "new_property_status"
    )

    await save_property_status(
        message,
        state,
        status,
        value,
    )


async def save_property_status(
    message: Message,
    state: FSMContext,
    status: str,
    transaction_value: float,
):
    data = await state.get_data()

    property_id = data.get(
        "status_property_id"
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(Property).where(
                Property.id == property_id
            )
        )

        p = result.scalar_one_or_none()

        if not p:
            await state.clear()

            await message.answer(
                "فایل پیدا نشد."
            )
            return

        old_status = p.status

        p.status = status
        p.transaction_value = (
            transaction_value
            if status ==
            "🔵 معامله شد - توسط ما"
            else 0
        )

        await add_property_history(
            session=session,
            property_id=property_id,
            user_id=message.from_user.id,
            field_name="status",
            old_value=old_status,
            new_value=status,
            event_type=(
                "قرارداد"
                if status ==
                "🔵 معامله شد - توسط ما"
                else "سایر"
            ),
        )

        await log_activity(
            session=session,
            user_id=message.from_user.id,
            property_id=property_id,
            activity_type=(
                "قرارداد"
                if status ==
                "🔵 معامله شد - توسط ما"
                else "تغییر وضعیت"
            ),
            description=(
                f"{old_status} → {status}"
            ),
        )

        await session.commit()

    await state.clear()

    await message.answer(
        f"✅ وضعیت فایل به «{status}» تغییر کرد."
    )

    await send_property_detail(
        message,
        property_id,
    )


# ============================================================
# PROPERTY HISTORY
# ============================================================

@router.callback_query(
    F.data.startswith("phistory:")
)
async def property_history(
    callback: CallbackQuery,
):
    property_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(PropertyHistory)
            .where(
                PropertyHistory.property_id ==
                property_id
            )
            .order_by(
                desc(PropertyHistory.created_at)
            )
            .limit(50)
        )

        history = result.scalars().all()

        activity_result = await session.execute(
            select(Activity)
            .where(
                Activity.property_id ==
                property_id
            )
            .order_by(
                desc(Activity.created_at)
            )
            .limit(50)
        )

        activities = (
            activity_result.scalars().all()
        )

    text = "📜 <b>تاریخچه فایل</b>\n\n"

    if not history and not activities:
        text += "هنوز سابقه‌ای ثبت نشده."
    else:

        if history:
            text += "✏️ <b>تغییرات</b>\n"

            for h in history:
                created = h.created_at.strftime(
                    "%Y/%m/%d %H:%M"
                )

                text += (
                    f"• {created}\n"
                    f"  {safe(h.field_name)}: "
                    f"{safe(h.old_value)} → "
                    f"{safe(h.new_value)}\n"
                )

        if activities:
            text += "\n📌 <b>فعالیت‌ها</b>\n"

            for a in activities:
                created = a.created_at.strftime(
                    "%Y/%m/%d %H:%M"
                )

                text += (
                    f"• {created} — "
                    f"{safe(a.activity_type)}\n"
                    f"  {safe(a.description)}\n"
                )

    await callback.message.answer(
        text
    )

    await callback.answer()


# ============================================================
# CLIENT SEARCH
# ============================================================

@router.message(F.text == "🔎 جستجوی مشتری")
async def client_search_start(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await state.set_state(
        SearchForm.query
    )

    await state.update_data(
        search_kind="client"
    )

    await message.answer(
        "🔎 جستجوی مشتری\n\n"
        "نام، شماره، کد، منطقه، "
        "بودجه یا توضیحات را وارد کن:",
        reply_markup=cancel_keyboard(),
    )


@router.message(
    SearchForm.query
)
async def client_search_query(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    if data.get("search_kind") != "client":
        return

    query = normalize_text(
        message.text
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client)
            .where(
                or_(
                    Client.code.ilike(
                        f"%{query}%"
                    ),
                    Client.name.ilike(
                        f"%{query}%"
                    ),
                    Client.phone.ilike(
                        f"%{query}%"
                    ),
                    Client.area.ilike(
                        f"%{query}%"
                    ),
                    Client.property_type.ilike(
                        f"%{query}%"
                    ),
                    Client.description.ilike(
                        f"%{query}%"
                    ),
                )
            )
            .order_by(
                desc(Client.created_at)
            )
            .limit(PAGE_SIZE)
        )

        clients = result.scalars().all()

    await state.clear()

    if not clients:
        await message.answer(
            "👤 مشتری‌ای با این مشخصات پیدا نشد.",
            reply_markup=main_keyboard(
                is_admin(message.from_user.id)
            ),
        )
        return

    text = (
        f"🔎 <b>نتایج مشتری: {query}</b>\n\n"
    )

    rows = []

    for c in clients:
        text += (
            f"👤 <b>{safe(c.name)}</b>\n"
            f"🔖 {safe(c.code)} | "
            f"📱 {safe(c.phone)}\n"
            f"📍 {safe(c.area)} | "
            f"💰 {price_text(c.max_budget)}\n"
            f"📌 {safe(c.status)}\n\n"
        )

        rows.append([
            InlineKeyboardButton(
                text=f"👤 {c.code}",
                callback_data=f"cdetail:{c.id}",
            )
        ])

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows,
        ),
    )


# ============================================================
# CLIENT STATUS
# ============================================================

@router.callback_query(
    F.data.startswith("cstatus:")
)
async def client_status_start(
    callback: CallbackQuery,
    state: FSMContext,
):
    client_id = int(
        callback.data.split(":")[1]
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="فعال"
                )
            ],
            [
                KeyboardButton(
                    text="خرید کرده"
                )
            ],
            [
                KeyboardButton(
                    text="منصرف شده"
                )
            ],
            [
                KeyboardButton(
                    text="❌ لغو"
                )
            ],
        ],
        resize_keyboard=True,
    )

    await state.update_data(
        status_client_id=client_id
    )

    await state.set_state(
        StatusForm.value
    )

    await callback.message.answer(
        "📌 وضعیت مشتری را انتخاب کن:",
        reply_markup=keyboard,
    )

    await callback.answer()


# ============================================================
# CLIENT STATUS HANDLING
# ============================================================

async def update_client_status(
    message: Message,
    state: FSMContext,
    status: str,
):
    data = await state.get_data()

    client_id = data.get(
        "status_client_id"
    )

    if not client_id:
        await state.clear()
        return

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

        old_status = client.status

        client.status = status

        await log_activity(
            session=session,
            user_id=message.from_user.id,
            client_id=client_id,
            activity_type="تغییر وضعیت مشتری",
            description=(
                f"{old_status} → {status}"
            ),
        )

        await session.commit()

    await state.clear()

    await message.answer(
        f"✅ وضعیت مشتری به «{status}» تغییر کرد.",
        reply_markup=main_keyboard(
            is_admin(message.from_user.id)
        ),
    )


# ============================================================
# SMART MATCHING
# ============================================================

@router.message(F.text == "🎯 مچینگ مشتری")
async def matching_start(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    async with SessionLocal() as session:

        result = await session.execute(
            select(Client)
            .where(
                Client.status == "فعال"
            )
            .order_by(
                desc(Client.created_at)
            )
            .limit(50)
        )

        clients = result.scalars().all()

    if not clients:
        await message.answer(
            "مشتری فعال برای مچینگ وجود ندارد."
        )
        return

    rows = []

    for c in clients:
        rows.append([
            InlineKeyboardButton(
                text=f"{c.code} — {c.name}",
                callback_data=f"match:{c.id}:1",
            )
        ])

    await message.answer(
        "🎯 <b>مشتری را برای مچینگ انتخاب کن:</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )


@router.callback_query(
    F.data.startswith("match:")
)
async def matching_results(
    callback: CallbackQuery,
):
    parts = callback.data.split(":")

    client_id = int(parts[1])
    page = int(parts[2])

    async with SessionLocal() as session:

        client_result = await session.execute(
            select(Client).where(
                Client.id == client_id
            )
        )

        client = (
            client_result.scalar_one_or_none()
        )

        if not client:
            await callback.answer(
                "مشتری پیدا نشد.",
                show_alert=True,
            )
            return

        property_result = await session.execute(
            select(Property)
            .where(
                Property.status.in_(
                    ACTIVE_PROPERTY_STATUSES
                )
            )
        )

        properties = (
            property_result.scalars().all()
        )

    scored = []

    for p in properties:
        score = calculate_match_score(
            client,
            p,
        )

        # Only active properties.
        # Zero-score records are not useful matches.
        if score > 0:
            scored.append(
                (
                    score,
                    p,
                )
            )

    scored.sort(
        key=lambda x: (
            x[0],
            x[1].price,
        ),
        reverse=True,
    )

    if not scored:
        await callback.message.answer(
            "فایل زنده مناسب با معیارهای این مشتری پیدا نشد."
        )

        await callback.answer()
        return

    total = len(scored)

    total_pages = max(
        1,
        (total + PAGE_SIZE - 1)
        // PAGE_SIZE,
    )

    page = max(
        1,
        min(page, total_pages),
    )

    start = (
        (page - 1)
        * PAGE_SIZE
    )

    page_items = scored[
        start:start + PAGE_SIZE
    ]

    text = (
        f"🎯 <b>مچینگ برای "
        f"{safe(client.name)}</b>\n"
        f"صفحه {page} از {total_pages}\n"
        f"وزن‌ها: قیمت 40٪ | منطقه 30٪ | "
        f"سال ساخت 15٪ | متراژ 10٪ | نوع 5٪\n\n"
    )

    rows = []

    for score, p in page_items:

        text += (
            f"🏠 <b>{safe(p.code)}</b> — "
            f"🎯 {score}%\n"
            f"📍 {safe(p.area)} | "
            f"📐 {format_number(p.sqm)} متر\n"
            f"💰 {price_text(p.price)} | "
            f"📅 {year_text(p.year_built)}\n\n"
        )

        rows.append([
            InlineKeyboardButton(
                text=f"🏠 {p.code} — {score}%",
                callback_data=f"pdetail:{p.id}",
            )
        ])

    pagination_rows = []

    if page > 1:
        pagination_rows.append(
            InlineKeyboardButton(
                text="⬅️ قبلی",
                callback_data=(
                    f"match:{client_id}:{page - 1}"
                ),
            )
        )

    pagination_rows.append(
        InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="noop",
        )
    )

    if page < total_pages:
        pagination_rows.append(
            InlineKeyboardButton(
                text="بعدی ➡️",
                callback_data=(
                    f"match:{client_id}:{page + 1}"
                ),
            )
        )

    rows.append(
        pagination_rows
    )

    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await callback.answer()
    # =========================
# PART 4 — VISIT / FOLLOWUP / KPI / FINAL
# =========================

# ---------- FIX: OWNER SEARCH STATE ----------
# اگر در بخش 2 این خط را با await نوشته‌ای:
# await owner_search_state.set(message.from_user.id)
# باید به این شکل باشد:
#
# owner_search_state.set(message.from_user.id)


# =========================
# VISIT REGISTRATION
# =========================

@router.message(F.text == "📅 ثبت بازدید")
async def visit_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.answer("⛔ دسترسی شما مجاز نیست.")
        return

    async with SessionLocal() as session:
        clients = (
            await session.execute(
                select(Client)
                .where(Client.status == "فعال")
                .order_by(Client.id.desc())
            )
        ).scalars().all()

    if not clients:
        await message.answer("هیچ مشتری فعال برای ثبت بازدید وجود ندارد.")
        return

    await state.set_state(VisitForm.client)
    await state.update_data(visit_client_page=1)

    await show_visit_clients(message, state, 1)


async def show_visit_clients(message, state, page=1):
    async with SessionLocal() as session:
        clients = (
            await session.execute(
                select(Client)
                .where(Client.status == "فعال")
                .order_by(Client.id.desc())
            )
        ).scalars().all()

    total = len(clients)

    if total == 0:
        await message.answer("مشتری فعال وجود ندارد.")
        return

    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))

    items = clients[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    buttons = []

    for c in items:
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {c.name} | {c.code}",
                callback_data=f"visit_client:{c.id}"
            )
        ])

    nav = []

    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"visit_clients_page:{page-1}"
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
                text="▶️",
                callback_data=f"visit_clients_page:{page+1}"
            )
        )

    buttons.append(nav)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        f"👤 انتخاب مشتری\n\nصفحه {page} از {total_pages} — {total} مشتری",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("visit_clients_page:"))
async def visit_clients_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])

    await callback.message.delete()
    await show_visit_clients(callback.message, state, page)

    await callback.answer()


@router.callback_query(F.data.startswith("visit_client:"))
async def visit_client_selected(callback: CallbackQuery, state: FSMContext):
    client_id = int(callback.data.split(":")[1])

    await state.update_data(client_id=client_id)

    async with SessionLocal() as session:
        client = await session.get(Client, client_id)

        if not client or client.status != "فعال":
            await callback.answer("مشتری فعال نیست.", show_alert=True)
            return

        properties = (
            await session.execute(
                select(Property)
                .where(Property.status.in_(ACTIVE_PROPERTY_STATUSES))
                .order_by(Property.id.desc())
            )
        ).scalars().all()

    if not properties:
        await callback.message.answer("هیچ فایل فعالی برای بازدید وجود ندارد.")
        await callback.answer()
        return

    await state.set_state(VisitForm.property)

    buttons = []

    for p in properties[:PAGE_SIZE]:
        buttons.append([
            InlineKeyboardButton(
                text=f"🏠 {p.code} | {p.area} | {p.sqm}م",
                callback_data=f"visit_property:{p.id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="❌ لغو",
            callback_data="visit_cancel"
        )
    ])

    await callback.message.edit_text(
        "🏠 فایل موردنظر برای بازدید را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

    await callback.answer()


@router.callback_query(F.data.startswith("visit_property:"))
async def visit_property_selected(callback: CallbackQuery, state: FSMContext):
    property_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    client_id = data.get("client_id")

    if not client_id:
        await callback.answer("اطلاعات مشتری پیدا نشد.", show_alert=True)
        return

    async with SessionLocal() as session:
        client = await session.get(Client, client_id)
        prop = await session.get(Property, property_id)

        if not client or not prop:
            await callback.answer("اطلاعات پیدا نشد.", show_alert=True)
            return

        existing = (
            await session.execute(
                select(Visit)
                .where(
                    Visit.client_id == client_id,
                    Visit.property_id == property_id
                )
                .order_by(Visit.id.desc())
            )
        ).scalars().first()

    if existing:
        await state.update_data(
            property_id=property_id,
            duplicate_visit=True
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 ثبت بازدید مجدد",
                        callback_data="visit_repeat"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ لغو",
                        callback_data="visit_cancel"
                    )
                ]
            ]
        )

        await callback.message.edit_text(
            "⚠️ این مشتری قبلاً این فایل را بازدید کرده است.\n\n"
            "اگر بازدید جدیدی انجام شده، بازدید مجدد را ثبت کن.",
            reply_markup=kb
        )

        await callback.answer()
        return

    await state.update_data(
        property_id=property_id,
        duplicate_visit=False
    )

    await start_visit_scorecard(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "visit_repeat")
async def visit_repeat(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    await state.update_data(duplicate_visit=False)

    await start_visit_scorecard(callback.message, state)
    await callback.answer()


async def start_visit_scorecard(message: Message, state: FSMContext):
    await state.set_state(VisitForm.interest)

    await message.edit_text(
        "📊 ارزیابی بازدید\n\n"
        "۱) میزان علاقه مشتری به ملک را از ۱ تا ۵ وارد کن:"
    )


@router.message(VisitForm.interest)
async def visit_interest(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())

        if value < 1 or value > 5:
            raise ValueError

    except Exception:
        await message.answer("لطفاً عددی بین ۱ تا ۵ وارد کن.")
        return

    await state.update_data(interest=value)
    await state.set_state(VisitForm.price_reaction)

    await message.answer(
        "۲) واکنش مشتری به قیمت را از ۱ تا ۵ وارد کن:"
    )


@router.message(VisitForm.price_reaction)
async def visit_price_reaction(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())

        if value < 1 or value > 5:
            raise ValueError

    except Exception:
        await message.answer("لطفاً عددی بین ۱ تا ۵ وارد کن.")
        return

    await state.update_data(price_reaction=value)
    await state.set_state(VisitForm.property_reaction)

    await message.answer(
        "۳) واکنش مشتری به خود ملک را از ۱ تا ۵ وارد کن:"
    )


@router.message(VisitForm.property_reaction)
async def visit_property_reaction(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())

        if value < 1 or value > 5:
            raise ValueError

    except Exception:
        await message.answer("لطفاً عددی بین ۱ تا ۵ وارد کن.")
        return

    await state.update_data(property_reaction=value)
    await state.set_state(VisitForm.objection)

    await message.answer(
        "۴) اصلی‌ترین ایراد یا اعتراض مشتری چیست؟"
    )


@router.message(VisitForm.objection)
async def visit_objection(message: Message, state: FSMContext):
    await state.update_data(objection=message.text.strip())
    await state.set_state(VisitForm.next_action)

    await message.answer(
        "۵) اقدام بعدی چیست؟\n"
        "مثلاً: تماس، مذاکره قیمت، بازدید مجدد، قرارداد"
    )


@router.message(VisitForm.next_action)
async def visit_next_action(message: Message, state: FSMContext):
    await state.update_data(next_action=message.text.strip())
    await state.set_state(VisitForm.followup_date)

    await message.answer(
        "۶) تاریخ پیگیری بعدی را وارد کن.\n"
        "اگر پیگیری ندارد، بنویس: ندارد"
    )


@router.message(VisitForm.followup_date)
async def visit_followup_date(message: Message, state: FSMContext):
    await state.update_data(followup_date=message.text.strip())
    await state.set_state(VisitForm.note)

    await message.answer(
        "۷) توضیحات بازدید:"
    )


@router.message(VisitForm.note)
async def visit_note(message: Message, state: FSMContext):
    await state.update_data(note=message.text.strip())

    data = await state.get_data()

    async with SessionLocal() as session:
        client = await session.get(Client, data["client_id"])
        prop = await session.get(Property, data["property_id"])

    if not client or not prop:
        await message.answer("اطلاعات بازدید پیدا نشد.")
        await state.clear()
        return

    summary = (
        "📋 <b>خلاصه بازدید</b>\n\n"
        f"👤 مشتری: {client.name}\n"
        f"🏠 فایل: {prop.code}\n"
        f"📍 منطقه: {prop.area}\n"
        f"📐 متراژ: {prop.sqm}\n\n"
        f"⭐ علاقه: {data['interest']}/5\n"
        f"💰 واکنش قیمت: {data['price_reaction']}/5\n"
        f"🏠 واکنش به ملک: {data['property_reaction']}/5\n"
        f"⚠️ اعتراض: {data['objection']}\n"
        f"➡️ اقدام بعدی: {data['next_action']}\n"
        f"📅 پیگیری: {data['followup_date']}\n"
        f"📝 یادداشت: {data['note']}\n"
    )

    await message.answer(
        summary,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ ثبت بازدید",
                        callback_data="visit_save"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ لغو",
                        callback_data="visit_cancel"
                    )
                ]
            ]
        )
    )


@router.callback_query(F.data == "visit_save")
async def visit_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    async with SessionLocal() as session:
        client = await session.get(Client, data["client_id"])
        prop = await session.get(Property, data["property_id"])

        if not client or not prop:
            await callback.answer("اطلاعات پیدا نشد.", show_alert=True)
            return

        visit = Visit(
            client_id=client.id,
            property_id=prop.id,
            interest=data.get("interest", 0),
            price_reaction=data.get("price_reaction", 0),
            property_reaction=data.get("property_reaction", 0),
            objection=data.get("objection", ""),
            next_action=data.get("next_action", ""),
            followup_date=data.get("followup_date", ""),
            note=data.get("note", "")
        )

        session.add(visit)

        activity = Activity(
            user_id=callback.from_user.id,
            activity_type="بازدید",
            description=(
                f"ثبت بازدید مشتری {client.name} "
                f"برای فایل {prop.code}"
            )
        )

        session.add(activity)

        await session.commit()

    await state.clear()

    await callback.message.edit_text(
        "✅ بازدید با موفقیت ثبت شد."
    )

    await callback.answer()


@router.callback_query(F.data == "visit_cancel")
async def visit_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "❌ ثبت بازدید لغو شد."
    )

    await callback.answer()


# =========================
# FOLLOW UPS
# =========================

@router.message(F.text == "📌 پیگیری‌ها")
async def followups(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("⛔ دسترسی شما مجاز نیست.")
        return

    async with SessionLocal() as session:
        visits = (
            await session.execute(
                select(Visit)
                .order_by(Visit.id.desc())
                .limit(100)
            )
        ).scalars().all()

        if not visits:
            await message.answer("📌 هیچ پیگیری ثبت‌شده‌ای وجود ندارد.")
            return

        lines = ["📌 <b>پیگیری‌ها</b>\n"]

        count = 0

        for v in visits:
            if not v.followup_date:
                continue

            client = await session.get(Client, v.client_id)
            prop = await session.get(Property, v.property_id)

            if not client or not prop:
                continue

            lines.append(
                f"👤 {client.name}\n"
                f"🏠 {prop.code} | {prop.area}\n"
                f"📅 {v.followup_date}\n"
                f"➡️ {v.next_action or '-'}\n"
                f"⚠️ {v.objection or '-'}\n"
                "────────────"
            )

            count += 1

            if count >= 20:
                break

    if count == 0:
        await message.answer("📌 پیگیری ثبت‌شده‌ای پیدا نشد.")
        return

    await message.answer("\n".join(lines))


# =========================
# CLIENT STATUS — FIX
# =========================

@router.callback_query(F.data.startswith("client_status:"))
async def client_status_start_fixed(
    callback: CallbackQuery,
    state: FSMContext
):
    client_id = int(callback.data.split(":")[1])

    await state.set_state(StatusForm.value)
    await state.update_data(
        status_client_id=client_id,
        status_property_id=None
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 فعال",
                    callback_data="client_status_value:فعال"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔵 خرید کرده",
                    callback_data="client_status_value:خرید کرده"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔴 منصرف شده",
                    callback_data="client_status_value:منصرف شده"
                ]
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="status_cancel"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "وضعیت مشتری را انتخاب کن:",
        reply_markup=kb
    )

    await callback.answer()


@router.callback_query(F.data.startswith("client_status_value:"))
async def client_status_value(
    callback: CallbackQuery,
    state: FSMContext
):
    status = callback.data.split(":", 1)[1]

    data = await state.get_data()
    client_id = data.get("status_client_id")

    if not client_id:
        await callback.answer("مشتری پیدا نشد.", show_alert=True)
        return

    async with SessionLocal() as session:
        client = await session.get(Client, client_id)

        if not client:
            await callback.answer("مشتری پیدا نشد.", show_alert=True)
            return

        old_status = client.status
        client.status = status

        session.add(
            Activity(
                user_id=callback.from_user.id,
                activity_type="تغییر وضعیت مشتری",
                description=(
                    f"{client.name}: "
                    f"{old_status} → {status}"
                )
            )
        )

        await session.commit()

    await state.clear()

    await callback.message.edit_text(
        f"✅ وضعیت مشتری به «{status}» تغییر کرد."
    )

    await callback.answer()


@router.callback_query(F.data == "status_cancel")
async def status_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "❌ تغییر وضعیت لغو شد."
    )

    await callback.answer()


# =========================
# MY KPI
# =========================

@router.message(F.text == "📊 KPI من")
async def my_kpi(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("⛔ دسترسی شما مجاز نیست.")
        return

    user_id = message.from_user.id

    async with SessionLocal() as session:
        activity_count = (
            await session.execute(
                select(func.count(Activity.id))
                .where(Activity.user_id == user_id)
            )
        ).scalar() or 0

        visit_count = (
            await session.execute(
                select(func.count(Visit.id))
            ).scalar() or 0
        )

        total_files = (
            await session.execute(
                select(func.count(Property.id))
            )
        ).scalar() or 0

        active_files = (
            await session.execute(
                select(func.count(Property.id))
                .where(Property.status.in_(ACTIVE_PROPERTY_STATUSES))
            )
        ).scalar() or 0

        sold_by_us = (
            await session.execute(
                select(func.count(Property.id))
                .where(Property.status == "🔵 معامله شد - توسط ما")
            )
        ).scalar() or 0

        clients = (
            await session.execute(
                select(func.count(Client.id))
                .where(Client.status == "فعال")
            )
        ).scalar() or 0

    await message.answer(
        "📊 <b>KPI من</b>\n\n"
        f"📌 فعالیت‌ها: {activity_count}\n"
        f"📅 بازدیدها: {visit_count}\n"
        f"🏠 کل فایل‌ها: {total_files}\n"
        f"🟢 فایل‌های فعال: {active_files}\n"
        f"🔵 معامله‌شده توسط ما: {sold_by_us}\n"
        f"👤 مشتریان فعال: {clients}"
    )


# =========================
# TEAM KPI
# =========================

@router.message(F.text == "📊 KPI تیم")
async def team_kpi(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ این بخش فقط برای ادمین است.")
        return

    async with SessionLocal() as session:
        users = (
            await session.execute(
                select(User).order_by(User.id.asc())
            )
        ).scalars().all()

        if not users:
            await message.answer("عضوی برای نمایش KPI وجود ندارد.")
            return

        lines = ["📊 <b>KPI تیم</b>\n"]

        for user in users:
            activity_count = (
                await session.execute(
                    select(func.count(Activity.id))
                    .where(Activity.user_id == user.telegram_id)
                )
            ).scalar() or 0

            visit_count = (
                await session.execute(
                    select(func.count(Visit.id))
                    .where(Visit.user_id == user.telegram_id)
                )
            ).scalar() or 0

            files_count = (
                await session.execute(
                    select(func.count(Property.id))
                    .where(Property.created_by == user.telegram_id)
                )
            ).scalar() or 0

            active_files = (
                await session.execute(
                    select(func.count(Property.id))
                    .where(
                        Property.created_by == user.telegram_id,
                        Property.status.in_(ACTIVE_PROPERTY_STATUSES)
                    )
                )
            ).scalar() or 0

            sold = (
                await session.execute(
                    select(func.count(Property.id))
                    .where(
                        Property.created_by == user.telegram_id,
                        Property.status == "🔵 معامله شد - توسط ما"
                    )
                )
            ).scalar() or 0

            lines.append(
                f"👤 <b>{user.name or user.telegram_id}</b>\n"
                f"  فعالیت: {activity_count}\n"
                f"  بازدید: {visit_count}\n"
                f"  فایل: {files_count}\n"
                f"  فایل فعال: {active_files}\n"
                f"  معامله توسط ما: {sold}\n"
                "────────────"
            )

    await message.answer("\n".join(lines))


# =========================
# LAST ACTIVITIES — ADMIN
# =========================

@router.message(F.text == "🕘 آخرین فعالیت‌ها")
async def last_activities(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ این بخش فقط برای ادمین است.")
        return

    async with SessionLocal() as session:
        activities = (
            await session.execute(
                select(Activity)
                .order_by(Activity.id.desc())
                .limit(30)
            )
        ).scalars().all()

        if not activities:
            await message.answer("هیچ فعالیتی ثبت نشده است.")
            return

        lines = ["🕘 <b>آخرین فعالیت‌ها</b>\n"]

        for a in activities:
            lines.append(
                f"#{a.id} | {a.activity_type}\n"
                f"{a.description}\n"
                f"👤 کاربر: {a.user_id}\n"
                f"🕒 {a.created_at}\n"
                "────────────"
            )

    await message.answer("\n".join(lines))


# =========================
# ACCESS / USER REGISTRATION
# =========================

@router.message(Command("id"))
async def my_id(message: Message):
    await message.answer(
        f"🆔 Telegram ID شما:\n`{message.from_user.id}`",
        parse_mode="Markdown"
    )


@router.message(Command("register"))
async def register_user(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین می‌تواند کاربر ثبت کند.")
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "فرمت:\n"
            "/register TELEGRAM_ID نام"
        )
        return

    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer("Telegram ID باید عدد باشد.")
        return

    name = parts[2].strip()

    async with SessionLocal() as session:
        existing = (
            await session.execute(
                select(User)
                .where(User.telegram_id == telegram_id)
            )
        ).scalar_one_or_none()

        if existing:
            existing.name = name
            existing.active = True
        else:
            session.add(
                User(
                    telegram_id=telegram_id,
                    name=name,
                    active=True
                )
            )

        await session.commit()

    await message.answer(
        f"✅ کاربر {name} با موفقیت ثبت شد."
    )


# =========================
# UNKNOWN TEXT
# =========================

@router.message()
async def fallback_handler(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.answer("⛔ دسترسی شما مجاز نیست.")
        return

    current_state = await state.get_state()

    # اگر FSM فعال است، اجازه بده هندلر مربوطه کار کند.
    if current_state:
        return

    await message.answer(
        "از منوی اصلی استفاده کن.",
        reply_markup=main_keyboard(message.from_user.id)
    )


# =========================
# STARTUP
# =========================

async def main():
    await migrate()

    await bot.delete_webhook(drop_pending_updates=True)

    print("🏙️ شهردار ایران‌زمین started...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
