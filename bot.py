import os
from uuid import uuid4
import asyncio
import random
from datetime import datetime, timezone

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


def utcnow_naive():
    """Current UTC time as a NAIVE datetime.

    Drop-in replacement for the deprecated utcnow() call: the value is
    identical (naive, UTC), so it stays comparable with the naive DateTime
    columns already stored in the database and with TEHRAN_OFFSET math.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


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

# Optional extra managers: comma separated Telegram IDs.
ADMIN_TELEGRAM_IDS = {
    x.strip()
    for x in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
    if x.strip()
}
if ADMIN_TELEGRAM_ID:
    ADMIN_TELEGRAM_IDS.add(ADMIN_TELEGRAM_ID)

ALLOWED_TELEGRAM_IDS = {
    x.strip()
    for x in os.getenv(
        "ALLOWED_TELEGRAM_IDS",
        ""
    ).split(",")
    if x.strip()
}


# Rent is intentionally disabled in this version. Legacy rent DB columns remain
# only for backward compatibility; no rent UI/flow is exposed.
RENT_ENABLED = False

# Quick-register is fully local: no paid AI/API key is required.


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
connect_args = {}
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    }

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
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
        default=utcnow_naive
    )

    # ---- Stage 3+ additions ----
    can_sale: Mapped[int] = mapped_column(Integer, default=1)
    can_rent: Mapped[int] = mapped_column(Integer, default=1)


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
        default=utcnow_naive
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow_naive
    )

    # ---- Stage 2 additions (safe, all with defaults) ----
    deal_type: Mapped[str] = mapped_column(
        String(30), default="فروش", index=True
    )
    rent_type: Mapped[str] = mapped_column(
        String(30), default=""
    )
    ownership_type: Mapped[str] = mapped_column(
        String(20), default="عمومی", index=True
    )
    owner_user_id: Mapped[int] = mapped_column(
        Integer, nullable=True, index=True
    )
    is_urgent: Mapped[int] = mapped_column(
        Integer, default=0, index=True
    )
    urgent_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )
    follow_up_user_id: Mapped[int] = mapped_column(
        Integer, nullable=True
    )
    floor_label: Mapped[str] = mapped_column(
        String(50), default=""
    )
    convertible: Mapped[str] = mapped_column(
        String(30), default=""
    )
    lease_term: Mapped[str] = mapped_column(
        String(100), default=""
    )

    # ---- Quick-register additions (nullable / defaulted) ----
    building_age: Mapped[int] = mapped_column(
        Integer, nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(20), default="manual"
    )
    source_url: Mapped[str] = mapped_column(
        Text, nullable=True
    )
    divar_token: Mapped[str] = mapped_column(
        String(64), nullable=True, index=True
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
        default=utcnow_naive
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
        default=utcnow_naive
    )

    # ---- Stage 2 additions (safe, all with defaults) ----
    deal_type: Mapped[str] = mapped_column(
        String(30), default="فروش", index=True
    )
    rent_type: Mapped[str] = mapped_column(
        String(30), default=""
    )
    ownership_type: Mapped[str] = mapped_column(
        String(20), default="عمومی", index=True
    )
    owner_user_id: Mapped[int] = mapped_column(
        Integer, nullable=True, index=True
    )
    is_urgent: Mapped[int] = mapped_column(
        Integer, default=0, index=True
    )
    urgent_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )
    follow_up_user_id: Mapped[int] = mapped_column(
        Integer, nullable=True
    )
    max_deposit: Mapped[float] = mapped_column(
        Float, default=0
    )
    max_rent: Mapped[float] = mapped_column(
        Float, default=0
    )
    # Importance levels: "الزامی" / "ترجیحی" / "مهم نیست"
    elevator_pref: Mapped[str] = mapped_column(
        String(20), default="ترجیحی"
    )
    parking_pref: Mapped[str] = mapped_column(
        String(20), default="ترجیحی"
    )
    storage_pref: Mapped[str] = mapped_column(
        String(20), default="مهم نیست"
    )
    floor_pref: Mapped[str] = mapped_column(
        String(20), default="مهم نیست"
    )
    floor_min: Mapped[int] = mapped_column(
        Integer, nullable=True
    )
    floor_max: Mapped[int] = mapped_column(
        Integer, nullable=True
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
        default=utcnow_naive
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
        default=utcnow_naive
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

MAX_PROPERTY_PHOTOS = 5


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


PRICE_UNIT_LABEL = "میلیارد تومان"


def price_short(value):
    """Display-only short price for SALE amounts, in billion Toman.

    The DB stores sale prices in Toman. The display is in billion Toman with
    three decimals, where "/" is the Persian decimal separator:
    26_000_000_000 -> "26/000", 1_250_000_000 -> "1/250",
    850_000_000 -> "0/850". Precision is one million Toman (the value is
    rounded to the nearest million). The stored value is never modified;
    call this only when rendering text.
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "0"

    if value <= 0:
        return "0"

    millions = int(round(value / 1_000_000))

    return f"{millions // 1000}/{millions % 1000:03d}"


def price_label(value):
    return f"{price_short(value)} ({PRICE_UNIT_LABEL})"


def budget_label(low, high):
    return (
        f"{price_short(low)} تا {price_short(high)} "
        f"({PRICE_UNIT_LABEL})"
    )


def display_value(value):
    if value is None:
        return ""

    if isinstance(value, float):
        return money(value)

    return str(value)


def is_admin(user_id: int) -> bool:
    return str(user_id) in ADMIN_TELEGRAM_IDS


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
    return env_main_menu(user_id)


def _sale_only(model):
    # Rent files/clients stay in the DB but are hidden while RENT_ENABLED=0
    if RENT_ENABLED:
        return model.id > 0
    return or_(
        model.deal_type == ENV_SALE,
        model.deal_type.is_(None),
    )


def active_property_filter():
    return and_(
        Property.status.in_(ACTIVE_PROPERTY_STATUSES),
        _sale_only(Property),
    )


def active_client_filter():
    return and_(
        Client.status.in_(ACTIVE_CLIENT_STATUSES),
        _sale_only(Client),
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

        # ------------------------------------------------------
        # Stage 2: new columns (additive only, nothing is dropped)
        # ------------------------------------------------------
        STAGE2_COLUMNS = {
            "users": [
                ("can_sale", "INTEGER DEFAULT 1"),
                ("can_rent", "INTEGER DEFAULT 1"),
            ],
            "properties": [
                ("deal_type", "VARCHAR(30) DEFAULT 'فروش'"),
                ("rent_type", "VARCHAR(30) DEFAULT ''"),
                ("ownership_type", "VARCHAR(20) DEFAULT 'عمومی'"),
                ("owner_user_id", "INTEGER"),
                ("is_urgent", "INTEGER DEFAULT 0"),
                ("urgent_at", "TIMESTAMP"),
                ("follow_up_user_id", "INTEGER"),
                ("floor_label", "VARCHAR(50) DEFAULT ''"),
                ("convertible", "VARCHAR(30) DEFAULT ''"),
                ("lease_term", "VARCHAR(100) DEFAULT ''"),
                ("building_age", "INTEGER"),
                ("source", "VARCHAR(20) DEFAULT 'manual'"),
                ("source_url", "TEXT"),
                ("divar_token", "VARCHAR(64)"),
            ],
            "clients": [
                ("deal_type", "VARCHAR(30) DEFAULT 'فروش'"),
                ("rent_type", "VARCHAR(30) DEFAULT ''"),
                ("ownership_type", "VARCHAR(20) DEFAULT 'عمومی'"),
                ("owner_user_id", "INTEGER"),
                ("is_urgent", "INTEGER DEFAULT 0"),
                ("urgent_at", "TIMESTAMP"),
                ("follow_up_user_id", "INTEGER"),
                ("max_deposit", "FLOAT DEFAULT 0"),
                ("max_rent", "FLOAT DEFAULT 0"),
                ("elevator_pref", "VARCHAR(20) DEFAULT 'ترجیحی'"),
                ("parking_pref", "VARCHAR(20) DEFAULT 'ترجیحی'"),
                ("storage_pref", "VARCHAR(20) DEFAULT 'مهم نیست'"),
                ("floor_pref", "VARCHAR(20) DEFAULT 'مهم نیست'"),
                ("floor_min", "INTEGER"),
                ("floor_max", "INTEGER"),
            ],
        }

        # Detect the first run of this migration (before columns exist),
        # so the one-time rental classification never overwrites later edits.
        props_cols_before = await conn.run_sync(
            lambda sync_conn: get_columns(sync_conn, "properties")
        )
        first_run = "deal_type" not in props_cols_before

        for table_name, cols in STAGE2_COLUMNS.items():
            for col_name, col_type in cols:
                await conn.run_sync(
                    lambda sync_conn, t=table_name, c=col_name, ty=col_type:
                    add_column_if_missing(sync_conn, t, c, ty)
                )

        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_properties_divar_token "
            "ON properties (divar_token)"
        )
        await conn.exec_driver_sql(
            "UPDATE properties SET source = 'manual' WHERE source IS NULL"
        )

        # Backfill (idempotent: only touches rows that are still empty)
        # Existing files that have a deposit or rent amount are rentals.
        if first_run:
            await conn.exec_driver_sql(
                "UPDATE properties SET deal_type = 'اجاره' "
                "WHERE COALESCE(deposit, 0) > 0 OR COALESCE(rent, 0) > 0"
            )
        for table_name in ("properties", "clients"):
            await conn.exec_driver_sql(
                f"UPDATE {table_name} SET deal_type = 'فروش' "
                f"WHERE deal_type IS NULL"
            )
            await conn.exec_driver_sql(
                f"UPDATE {table_name} SET ownership_type = 'عمومی' "
                f"WHERE ownership_type IS NULL"
            )
            await conn.exec_driver_sql(
                f"UPDATE {table_name} SET is_urgent = 0 "
                f"WHERE is_urgent IS NULL"
            )
            await conn.exec_driver_sql(
                f"UPDATE {table_name} SET owner_user_id = ("
                f"SELECT users.id FROM users "
                f"WHERE users.telegram_id = {table_name}.created_by) "
                f"WHERE owner_user_id IS NULL"
            )
        await conn.exec_driver_sql(
            "UPDATE users SET can_sale = 1 WHERE can_sale IS NULL"
        )
        await conn.exec_driver_sql(
            "UPDATE users SET can_rent = 1 WHERE can_rent IS NULL"
        )
        # Existing clients all prefer (not require) elevator and parking.
        for col, default_value in (
            ("elevator_pref", "ترجیحی"),
            ("parking_pref", "ترجیحی"),
            ("storage_pref", "مهم نیست"),
            ("floor_pref", "مهم نیست"),
        ):
            await conn.exec_driver_sql(
                f"UPDATE clients SET {col} = '{default_value}' "
                f"WHERE {col} IS NULL"
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
    USER_ENV.pop(message.from_user.id, None)

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
        "سیستم مدیریت فایل، مشتری و تیم\n\n"
        + (
            "محیط کاری را انتخاب کن 👇"
            if RENT_ENABLED else "یک گزینه را انتخاب کن 👇"
        ),
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
# STAGE 3-9: ENVIRONMENTS, LISTS, DETAILS, MATCHING, URGENT,
#            ACTIVITIES  (additive block; old handlers below stay)
# =========================================================

from datetime import timedelta
from aiogram.filters import Command
from sqlalchemy import (
    update as sa_update,
    and_,
    true as sa_true,
)

ENV_SALE = "فروش"
ENV_RENT = "اجاره"
ENV_BUTTONS = {
    "🏠 فروش": ENV_SALE,
    "🔑 اجاره": ENV_RENT,
}
RENT_TYPES = ["رهن کامل", "رهن و اجاره", "اجاره"]

PREF_REQUIRED = "الزامی"
PREF_PREFERRED = "ترجیحی"
PREF_ANY = "مهم نیست"
PREF_CYCLE = [PREF_REQUIRED, PREF_PREFERRED, PREF_ANY]
PREF_ICONS = {
    PREF_REQUIRED: "🔴",
    PREF_PREFERRED: "🟡",
    PREF_ANY: "⚪",
}

LIST_PAGE_SIZE = 6
MATCH_PAGE_SIZE = 4
ACTIVITY_PAGE_SIZE = 10
MATCH_MIN_SCORE = 40
LAST_FLOOR_SENTINEL = 9999
TEHRAN_OFFSET = timedelta(hours=3, minutes=30)

# In-memory UI state (per Telegram user)
USER_ENV = {}
USER_FILTERS = {}
ACTIVITY_VIEW = {}


class ReplacePhotoForm(StatesGroup):
    photo = State()


class FloorRangeForm(StatesGroup):
    value = State()


class RentBudgetForm(StatesGroup):
    deposit = State()
    rent = State()


def current_env(tg_id):
    if not RENT_ENABLED:
        return ENV_SALE
    return USER_ENV.get(tg_id, ENV_SALE)


def env_main_menu(user_id: int):
    if RENT_ENABLED:
        if user_id not in USER_ENV:
            return keyboard(
                [["🏠 فروش", "🔑 اجاره"]],
                include_cancel=False
            )
        return keyboard(
            [
                ["🏠 فایل‌ها", "👤 مشتریان"],
                ["🎯 پیشنهاد به مشتری", "⚡ ثبت سریع"],
                ["📊 عملکرد من", "🔄 تغییر محیط"],
            ],
            include_cancel=False
        )
    rows = [
        ["🏠 فایل‌ها", "👤 مشتریان"],
        ["🎯 پیشنهاد به مشتری", "⚡ ثبت سریع"],
        ["📊 عملکرد من", "🤖 شهردار ایران‌زمین"],
    ]
    if is_admin(user_id):
        rows.append(["📊 داشبورد مدیریتی"])
    return keyboard(rows, include_cancel=False)


def _env_suffix(user_id: int):
    if not RENT_ENABLED:
        return ""
    return f" — {env_title(current_env(user_id))}"


def env_title(env):
    return "🏠 فروش" if env == ENV_SALE else "🔑 اجاره"


def pref_icon(value):
    return PREF_ICONS.get(value or PREF_ANY, "⚪")


def tehran_time(dt):
    if not dt:
        return ""
    return (dt + TEHRAN_OFFSET).strftime("%m/%d %H:%M")


def day_start_utc():
    now_local = utcnow_naive() + TEHRAN_OFFSET
    start_local = now_local.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start_local - TEHRAN_OFFSET


async def show(target, text, markup=None, edit=False):
    if edit:
        try:
            await target.edit_text(text, reply_markup=markup)
            return
        except Exception as exc:
            if "not modified" in str(exc).lower():
                return
    await target.answer(text, reply_markup=markup)


def vis_filter(model, user, tg_id):
    """Personal items are visible only to their owner (and admin)."""
    if is_admin(tg_id):
        return None
    return or_(
        model.ownership_type.is_(None),
        model.ownership_type != "شخصی",
        model.owner_user_id == user.id,
    )


def prop_price_text(p):
    if p.deal_type == ENV_RENT:
        return f"رهن {money(p.deposit)} / اجاره {money(p.rent)}"
    return price_label(p.price)


def client_budget_text(c):
    if c.deal_type == ENV_RENT:
        return (
            f"رهن تا {money(c.max_deposit)} / "
            f"اجاره تا {money(c.max_rent)}"
        )
    return budget_label(c.min_budget, c.max_budget)


def ownership_text(obj):
    if (obj.ownership_type or "عمومی") == "شخصی":
        return "👤 شخصی"
    return "🌐 عمومی"


async def user_name_map(session, ids):
    ids = {i for i in ids if i}
    if not ids:
        return {}
    result = await session.execute(
        select(User.id, User.name).where(User.id.in_(ids))
    )
    return {row[0]: (row[1] or "بدون نام") for row in result.all()}


# =========================================================
# ENVIRONMENT SELECTION + SUB MENUS
# =========================================================

@dp.message(F.text.in_(list(ENV_BUTTONS)))
async def choose_env(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    await state.clear()
    if not RENT_ENABLED:
        # stale keyboard on an old client: just show the new menu
        note = (
            "ℹ️ بخش اجاره فعلاً غیرفعال است."
            if ENV_BUTTONS[message.text] == ENV_RENT
            else "🏠 منوی اصلی"
        )
        await message.answer(
            note, reply_markup=env_main_menu(message.from_user.id)
        )
        return
    USER_ENV[message.from_user.id] = ENV_BUTTONS[message.text]
    await message.answer(
        f"{message.text}\nمحیط انتخاب شد.",
        reply_markup=env_main_menu(message.from_user.id)
    )


@dp.message(F.text == "🔄 تغییر محیط")
async def change_env(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    await state.clear()
    USER_ENV.pop(message.from_user.id, None)
    await message.answer(
        "محیط کاری را انتخاب کن:",
        reply_markup=env_main_menu(message.from_user.id)
    )


@dp.message(F.text == "⬅️ بازگشت")
async def back_to_env_menu(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    await state.clear()
    await message.answer(
        env_title(current_env(message.from_user.id))
        if RENT_ENABLED else "🏠 منوی اصلی",
        reply_markup=env_main_menu(message.from_user.id)
    )


async def require_env(message: Message):
    if RENT_ENABLED and message.from_user.id not in USER_ENV:
        await message.answer(
            "ابتدا محیط را انتخاب کن:",
            reply_markup=env_main_menu(message.from_user.id)
        )
        return False
    return True


@dp.message(F.text.in_({"🏠 فایل‌ها", "📁 فایل‌ها"}))
async def files_menu(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    if not await require_env(message):
        return
    await state.clear()
    await message.answer(
        f"🏠 فایل‌ها{_env_suffix(message.from_user.id)}",
        reply_markup=keyboard(
            [
                ["📋 همه فایل‌ها", "👤 فایل‌های من"],
                ["🌐 فایل‌های عمومی", "🚨 فایل‌های فوری"],
                ["⚡ ثبت سریع", "➕ ثبت فایل"],
                ["📢 پیشنهاد آگهی‌گذاری"],
                ["⬅️ بازگشت"],
            ],
            include_cancel=False
        )
    )


@dp.message(F.text.in_({"👤 مشتریان", "👥 مشتری‌ها"}))
async def clients_menu(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    if not await require_env(message):
        return
    await state.clear()
    await message.answer(
        f"👤 مشتریان{_env_suffix(message.from_user.id)}",
        reply_markup=keyboard(
            [
                ["📋 همه مشتری‌ها", "👤 مشتری‌های من"],
                ["🌐 مشتری‌های عمومی", "🚨 مشتری‌های فوری"],
                ["➕ ثبت مشتری", "⬅️ بازگشت"],
            ],
            include_cancel=False
        )
    )


@dp.message(F.text == "📢 پیشنهاد آگهی‌گذاری")
async def ad_menu_entry(message: Message, state: FSMContext):
    await ad_home(message, state)


@dp.message(F.text == "📊 داشبورد مدیریتی")
async def dash_menu_entry(message: Message, state: FSMContext):
    await dash_home(message, state)


@dp.message(F.text == "🤖 شهردار ایران‌زمین")
async def mayor_menu_entry(message: Message, state: FSMContext):
    await mayor_start(message, state)


LIST_ENTRIES = {
    "📋 همه فایل‌ها": ("p", "a"),
    "👤 فایل‌های من": ("p", "m"),
    "🌐 فایل‌های عمومی": ("p", "g"),
    "🚨 فایل‌های فوری": ("p", "u"),
    "📋 همه مشتری‌ها": ("c", "a"),
    "👤 مشتری‌های من": ("c", "m"),
    "🌐 مشتری‌های عمومی": ("c", "g"),
    "🚨 مشتری‌های فوری": ("c", "u"),
}


@dp.message(F.text.in_(list(LIST_ENTRIES)))
async def list_entry(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    if not await require_env(message):
        return
    await state.clear()
    kind, mode = LIST_ENTRIES[message.text]
    USER_FILTERS[(message.from_user.id, kind)] = {}
    await send_list(message, kind, mode, 1, message.from_user)


# =========================================================
# PAGINATED LISTS (files / clients) WITH FILTERS
# =========================================================

MODE_TITLES = {
    "a": "همه",
    "m": "من",
    "g": "عمومی",
    "u": "🚨 فوری",
}


async def send_list(target, kind, mode, page, tg_user, edit=False):
    tg_id = tg_user.id
    env = current_env(tg_id)
    flt = USER_FILTERS.setdefault((tg_id, kind), {})
    model = Property if kind == "p" else Client

    async with SessionLocal() as session:
        user = await get_user(session, tg_id, tg_user.full_name)
        conds = [model.deal_type == env]
        if flt.get("status"):
            conds.append(model.status == flt["status"])
        elif kind == "p":
            conds.append(active_property_filter())
        else:
            conds.append(active_client_filter())
        vis = vis_filter(model, user, tg_id)
        if vis is not None:
            conds.append(vis)
        if mode == "m":
            conds.append(model.owner_user_id == user.id)
        elif mode == "g":
            conds.append(or_(
                model.ownership_type.is_(None),
                model.ownership_type == "عمومی",
            ))
        elif mode == "u":
            conds.append(model.is_urgent == 1)
        if flt.get("area"):
            conds.append(model.area == flt["area"])

        total = await session.scalar(
            select(func.count(model.id)).where(*conds)
        ) or 0
        total_pages = max(
            1, (total + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE
        )
        page = max(1, min(page, total_pages))
        result = await session.execute(
            select(model)
            .where(*conds)
            .order_by(model.is_urgent.desc(), model.id.desc())
            .limit(LIST_PAGE_SIZE)
            .offset((page - 1) * LIST_PAGE_SIZE)
        )
        items = result.scalars().all()

    title = "📁 فایل‌ها" if kind == "p" else "👥 مشتری‌ها"
    lines = [
        f"{title} — {env_title(env)} — {MODE_TITLES[mode]}",
        f"صفحه {page} از {total_pages} — {total} مورد",
    ]
    if flt.get("area"):
        lines.append(f"📍 منطقه: {flt['area']}")
    if flt.get("status"):
        lines.append(f"📊 وضعیت: {flt['status']}")
    if not items:
        lines.append("\nمورد پیدا نشد.")

    rows = []
    for obj in items:
        flag = "🚨 " if obj.is_urgent else ""
        if kind == "p":
            label = (
                f"{flag}{obj.code} | {obj.area} | "
                f"{money(obj.sqm)}م | {prop_price_text(obj)}"
            )
            cb = f"popen:{obj.id}"
        else:
            label = (
                f"{flag}{obj.name} | {obj.area} | "
                f"{client_budget_text(obj)}"
            )
            cb = f"copen:{obj.id}"
        rows.append([
            InlineKeyboardButton(text=label[:60], callback_data=cb)
        ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(
            text="‹ قبلی",
            callback_data=f"L:{kind}:{mode}:{page - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"{page}/{total_pages}", callback_data="noop"
    ))
    if page < total_pages:
        nav.append(InlineKeyboardButton(
            text="بعدی ›",
            callback_data=f"L:{kind}:{mode}:{page + 1}"
        ))
    rows.append(nav)

    search_cb = "psearch:start" if kind == "p" else "csearch:start"
    rows.append([
        InlineKeyboardButton(text="🔍 جست‌وجو", callback_data=search_cb),
        InlineKeyboardButton(
            text="📍 منطقه", callback_data=f"FA:{kind}:{mode}"
        ),
        InlineKeyboardButton(
            text="📊 وضعیت", callback_data=f"FT:{kind}:{mode}"
        ),
    ])
    if flt:
        rows.append([InlineKeyboardButton(
            text="🧹 حذف فیلترها", callback_data=f"FC:{kind}:{mode}"
        )])

    await show(
        target,
        "\n".join(lines),
        InlineKeyboardMarkup(inline_keyboard=rows),
        edit=edit
    )


@dp.callback_query(F.data.startswith("L:"))
async def list_page_callback(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    try:
        _, kind, mode, page = callback.data.split(":")
        page = int(page)
    except Exception:
        await callback.answer("نامعتبر", show_alert=True)
        return
    await send_list(
        callback.message, kind, mode, page,
        callback.from_user, edit=True
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("FA:"))
async def filter_area_menu(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, kind, mode = callback.data.split(":")
    rows = [[InlineKeyboardButton(
        text="همه مناطق", callback_data=f"FS:{kind}:{mode}:0"
    )]]
    for i, area in enumerate(AREAS, start=1):
        rows.append([InlineKeyboardButton(
            text=area, callback_data=f"FS:{kind}:{mode}:{i}"
        )])
    await show(
        callback.message, "📍 منطقه را انتخاب کن:",
        InlineKeyboardMarkup(inline_keyboard=rows), edit=True
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("FS:"))
async def filter_area_set(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, kind, mode, idx = callback.data.split(":")
    idx = int(idx)
    flt = USER_FILTERS.setdefault((callback.from_user.id, kind), {})
    if idx == 0 or idx > len(AREAS):
        flt.pop("area", None)
    else:
        flt["area"] = AREAS[idx - 1]
    await send_list(
        callback.message, kind, mode, 1, callback.from_user, edit=True
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("FT:"))
async def filter_status_menu(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, kind, mode = callback.data.split(":")
    statuses = STATUSES if kind == "p" else CLIENT_STATUSES
    rows = [[InlineKeyboardButton(
        text="فقط فعال‌ها", callback_data=f"FU:{kind}:{mode}:0"
    )]]
    for i, st in enumerate(statuses, start=1):
        rows.append([InlineKeyboardButton(
            text=st, callback_data=f"FU:{kind}:{mode}:{i}"
        )])
    await show(
        callback.message, "📊 وضعیت را انتخاب کن:",
        InlineKeyboardMarkup(inline_keyboard=rows), edit=True
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("FU:"))
async def filter_status_set(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, kind, mode, idx = callback.data.split(":")
    idx = int(idx)
    statuses = STATUSES if kind == "p" else CLIENT_STATUSES
    flt = USER_FILTERS.setdefault((callback.from_user.id, kind), {})
    if idx == 0 or idx > len(statuses):
        flt.pop("status", None)
    else:
        flt["status"] = statuses[idx - 1]
    await send_list(
        callback.message, kind, mode, 1, callback.from_user, edit=True
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("FC:"))
async def filter_clear(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, kind, mode = callback.data.split(":")
    USER_FILTERS[(callback.from_user.id, kind)] = {}
    await send_list(
        callback.message, kind, mode, 1, callback.from_user, edit=True
    )
    await callback.answer()


# =========================================================
# POST-CREATE QUICK SETTINGS
# =========================================================

async def post_create_prompt(message, kind, obj_id, tg_user=None):
    """After a file/client is saved: fill owner, offer quick settings."""
    tg = tg_user or message.from_user
    model = Property if kind == "p" else Client
    async with SessionLocal() as session:
        user = await get_user(session, tg.id, tg.full_name)
        await session.execute(
            sa_update(model)
            .where(model.id == obj_id, model.owner_user_id.is_(None))
            .values(owner_user_id=user.id)
        )
        await session.commit()
        obj = (await session.execute(
            select(model).where(model.id == obj_id)
        )).scalar_one_or_none()
    if not obj:
        return

    rows = []
    if RENT_ENABLED and kind == "p" and obj.deal_type == ENV_RENT:
        rows.append([
            InlineKeyboardButton(
                text=name, callback_data=f"rt:{obj.id}:{i}"
            )
            for i, name in enumerate(RENT_TYPES)
        ])
    if kind == "c":
        if RENT_ENABLED and obj.deal_type == ENV_RENT:
            rows.append([InlineKeyboardButton(
                text="💵 سقف رهن و اجاره",
                callback_data=f"crb:{obj.id}"
            )])
        rows.append([InlineKeyboardButton(
            text="⚙️ ترجیحات (آسانسور، پارکینگ، ...)",
            callback_data=f"cpref:{obj.id}"
        )])
    rows.append([
        InlineKeyboardButton(
            text="👤 شخصی کردن" if ownership_text(obj) == "🌐 عمومی"
            else "🌐 عمومی کردن",
            callback_data=f"own:{kind}:{obj.id}"
        ),
        InlineKeyboardButton(
            text="🚨 فوری کردن", callback_data=f"urg:{kind}:{obj.id}"
        ),
    ])
    rows.append([InlineKeyboardButton(
        text="👁 مشاهده",
        callback_data=(
            f"popen:{obj.id}" if kind == "p" else f"copen:{obj.id}"
        )
    )])
    await message.answer(
        f"📌 تنظیمات سریع — الان: {ownership_text(obj)}، "
        f"{env_title(obj.deal_type)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@dp.callback_query(F.data.startswith("rt:"))
async def set_rent_type(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    if not RENT_ENABLED:
        await callback.answer(
            "بخش اجاره فعلاً غیرفعال است.", show_alert=True)
        return
    _, pid, idx = callback.data.split(":")
    async with SessionLocal() as session:
        await session.execute(
            sa_update(Property)
            .where(Property.id == int(pid))
            .values(rent_type=RENT_TYPES[int(idx)])
        )
        await session.commit()
    await callback.answer(f"✅ {RENT_TYPES[int(idx)]}")


# =========================================================
# ⚡ QUICK REGISTER  (ثبت سریع فایل فروش)
#
# Telegram Handler
#   -> Input Detector      (QRInputDetector)
#   -> Source Parser       (Divar / Text)
#   -> Local Extractor     (regex/rules; no paid AI required)
#   -> Normalizer          (qr_normalize)
#   -> Validator           (qr_validate)
#   -> Preview             (qr_render_preview)
#   -> Confirmation        (callbacks qk:*)
#   -> File Service        (qr_create_property)
#   -> Database
#
# New source = new parser + one branch in qr_run_pipeline.
# Nothing else (preview / edit / confirm / save) changes.
# =========================================================

import re
import json
import html as html_lib
from dataclasses import dataclass, field as dc_field
from urllib.parse import urlparse, unquote

import aiohttp
from aiogram.filters import StateFilter


class QuickForm(StatesGroup):
    waiting = State()
    preview = State()
    edit_value = State()


QR_SAVING = set()

QR_KNOWN_BUTTONS = {
    "➕ ثبت فایل", "➕ ثبت مشتری", "👀 ثبت بازدید", "📞 پیگیری",
    "📊 KPI من", "👥 KPI تیم", "📝 آخرین فعالیت‌ها", "🔎 پیشنهاد فایل",
    "🚨 فوری", "📊 فعالیت‌ها", "🔄 تغییر محیط", "📊 عملکرد من",
    "📢 پیشنهاد آگهی‌گذاری", "📊 داشبورد مدیریتی", "🤖 شهردار ایران‌زمین",
}


class QRError(Exception):
    pass


class QRRentListing(QRError):
    pass


class QRDuplicate(QRError):
    def __init__(self, prop_id, code):
        super().__init__("duplicate")
        self.prop_id = prop_id
        self.code = code


# ---------------------------------------------------------
# QR PURE START  (no network / telegram / db in this section)
# ---------------------------------------------------------

QR_ALL_FIELDS = [
    "transaction_type", "area", "address", "property_type",
    "meterage", "bedrooms", "floor", "total_floors", "building_age",
    "parking", "elevator", "storage", "price",
    "description", "owner_name", "owner_phone",
]

QR_LABELS = {
    "area": "منطقه",
    "address": "آدرس",
    "property_type": "نوع ملک",
    "meterage": "متراژ",
    "bedrooms": "تعداد خواب",
    "floor": "طبقه",
    "total_floors": "کل طبقات",
    "building_age": "سن بنا",
    "parking": "پارکینگ",
    "elevator": "آسانسور",
    "storage": "انباری",
    "price": "قیمت",
    "description": "توضیحات",
    "owner_name": "نام مالک",
    "owner_phone": "تلفن مالک",
}

QR_INT_FIELDS = {"bedrooms", "floor", "total_floors", "building_age"}
QR_BOOL_FIELDS = {"parking", "elevator", "storage"}
QR_REQUIRED = [("area", "منطقه"), ("meterage", "متراژ")]

QR_RANGES = {
    "meterage": (5, 100000),
    "bedrooms": (0, 20),
    "floor": (-3, 100),
    "total_floors": (1, 100),
    "building_age": (0, 100),
    "price": (10_000_000, 10 ** 13),
}

QR_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def qr_fa(value):
    return str(value).translate(QR_FA_DIGITS)


def qr_num_text(value):
    if value is None:
        return ""
    try:
        value = float(value)
    except Exception:
        return str(value)
    if value.is_integer():
        return qr_fa(f"{int(value):,}")
    return qr_fa(f"{value:,.2f}".rstrip("0").rstrip("."))


def qr_norm(text):
    t = normalize_digits(text or "")
    t = t.replace("ي", "ی").replace("ك", "ک")
    t = t.replace("ۀ", "ه").replace("ة", "ه")
    t = t.replace("\u200c", " ").replace("\u200f", "").replace("\u200e", "")
    t = re.sub(r"[ـ\u064b-\u065f]", "", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def qr_squash(text):
    # tolerant form used only to check that a quote exists in the source
    return re.sub(r"[\W_]+", "", qr_norm(text))


def qr_tokens(text):
    return {t for t in re.split(r"[\W_]+", qr_norm(text)) if t}


def qr_parse_number(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    t = qr_norm(str(value)).replace(",", "").replace("٬", "")
    t = t.replace("٫", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    return float(m.group(0)) if m else None


def qr_parse_int(value):
    n = qr_parse_number(value)
    return int(round(n)) if n is not None else None


QR_UNITS = {
    "میلیارد": 10 ** 9, "ملیارد": 10 ** 9,
    "میلیون": 10 ** 6, "هزار": 10 ** 3,
}


def qr_parse_price(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(round(value))
    t = qr_norm(str(value)).replace(",", "").replace("٬", "")
    t = t.replace("٫", ".").replace("/", ".")
    total = 0.0
    found = False
    for m in re.finditer(
        r"(\d+(?:\.\d+)?)\s*(میلیارد|ملیارد|میلیون|هزار)", t
    ):
        total += float(m.group(1)) * QR_UNITS[m.group(2)]
        found = True
    if found:
        return int(round(total))
    m = re.search(r"\d+(?:\.\d+)?", t)
    return int(round(float(m.group(0)))) if m else None


def qr_parse_bool(value):
    if isinstance(value, bool):
        return value
    t = qr_norm(str(value))
    if t in ("true", "yes", "دارد", "دارد.", "1"):
        return True
    if t in ("false", "no", "ندارد", "ندارد.", "0"):
        return False
    return None


def qr_clean_phone(value):
    digits = re.sub(r"\D", "", normalize_digits(str(value or "")))
    if re.fullmatch(r"09\d{9}", digits):
        return digits
    if re.fullmatch(r"0\d{10}", digits):
        return digits
    return None


def qr_match_area(raw):
    if not raw:
        return None
    n = qr_norm(raw)
    for a in AREAS:
        if qr_norm(a) == n:
            return a
    toks = qr_tokens(raw)
    if not toks:
        return None
    # the typed name is a part of exactly one defined area
    hits = [a for a in AREAS if toks <= qr_tokens(a)]
    if len(hits) == 1:
        return hits[0]
    # a defined area is fully contained in a longer typed text
    hits = [a for a in AREAS if qr_tokens(a) <= toks]
    if len(hits) == 1:
        return hits[0]
    return None


def qr_match_type(raw):
    if not raw:
        return None
    n = qr_norm(raw)
    for t in PROPERTY_TYPES:
        if qr_norm(t) == n:
            return t
    for t in PROPERTY_TYPES:
        if t != "سایر" and qr_norm(t) in n:
            return t
    return None


# ---- Divar helpers ----

QR_DIVAR_RE = re.compile(r"https?://(?:www\.)?divar\.ir/[^\s<>\"']+", re.I)


def qr_find_divar_url(text):
    m = QR_DIVAR_RE.search(text or "")
    if not m:
        return None
    return m.group(0).rstrip(".,;:)]»،؛")


def qr_divar_parts(url):
    try:
        p = urlparse(url)
    except Exception:
        return []
    return [unquote(x) for x in p.path.split("/") if x]


def qr_divar_token(url):
    parts = qr_divar_parts(url)
    if len(parts) >= 2 and parts[0] == "v":
        tok = parts[-1]
        if re.fullmatch(r"[A-Za-z0-9_-]{6,24}", tok):
            return tok
    return None


def qr_divar_slug(url):
    parts = qr_divar_parts(url)
    if len(parts) >= 3 and parts[0] == "v":
        return parts[1].replace("-", " ")
    return ""


def qr_deal_signals(text):
    n = qr_norm(text)
    rent = any(w in n for w in ("اجاره", "رهن", "ودیعه"))
    sale = any(w in n for w in ("فروش", "خرید"))
    return rent, sale


def qr_decide_transaction(head_text, ai_value):
    """Title/slug signal first; the AI value breaks ties. None = unknown."""
    rent, sale = qr_deal_signals(head_text)
    if rent and not sale:
        return "rent"
    if sale and not rent:
        return "sale"
    if ai_value in ("sale", "rent"):
        return ai_value
    return None


# ---- normalizer / validator ----

def qr_unpack(item):
    if isinstance(item, dict):
        return item.get("value"), item.get("evidence")
    return item, None


def qr_normalize(raw, source_text=None, kind="text"):
    """raw: {name: {"value":..., "evidence":...}} -> (fields, warnings).

    Unknown stays None. When the source text is available every non-null
    value must be backed by a quote that really exists in the source.
    """
    fields = {k: None for k in QR_ALL_FIELDS}
    warnings = []
    src = qr_squash(source_text) if source_text else None

    for name in QR_ALL_FIELDS:
        value, evidence = qr_unpack(raw.get(name))
        if isinstance(value, str):
            value = value.strip()
        if value in (None, "", [], {}):
            continue

        if name == "transaction_type":
            v = str(value).strip().lower()
            fields[name] = v if v in ("sale", "rent") else None
            continue

        if src is not None and name != "description":
            ev = qr_squash(str(evidence)) if evidence else ""
            if not ev or ev not in src:
                warnings.append({
                    "f": name,
                    "t": f"«{QR_LABELS[name]}» در متن منبع تأیید نشد و خالی ماند.",
                })
                continue
        if src is not None and name == "description":
            if qr_squash(str(value)) not in src:
                continue

        if name == "meterage":
            v = qr_parse_number(value)
        elif name == "price":
            v = qr_parse_price(value)
        elif name in QR_INT_FIELDS:
            v = qr_parse_int(value)
        elif name in QR_BOOL_FIELDS:
            v = qr_parse_bool(value)
        elif name == "area":
            v = qr_match_area(value)
            if v is None:
                warnings.append({
                    "f": "area",
                    "t": f"منطقه «{value}» با مناطق تعریف‌شده یکی نیست "
                         f"یا مبهم است؛ از «اصلاح» انتخابش کن.",
                })
        elif name == "property_type":
            v = qr_match_type(value)
        elif name == "owner_phone":
            v = qr_clean_phone(value)
        elif name == "description":
            v = str(value)[:600]
        else:
            v = str(value)[:200]
        fields[name] = v

    if kind in ("text", "voice") and source_text:
        # the user's own words are the description (nothing is invented)
        fields["description"] = source_text.strip()[:600]

    return fields, warnings


def qr_validate(fields, warnings):
    for name, (lo, hi) in QR_RANGES.items():
        v = fields.get(name)
        if v is None:
            continue
        if not (lo <= v <= hi):
            warnings.append({
                "f": name,
                "t": f"«{QR_LABELS[name]}» ({qr_num_text(v)}) "
                     f"نامعتبر بود و خالی ماند.",
            })
            fields[name] = None
    return fields, warnings


def qr_missing_required(fields):
    return [label for key, label in QR_REQUIRED if fields.get(key) in (None, "")]


def qr_floor_label(floor, total):
    if floor is None:
        return "نامشخص"
    if floor == 0:
        return "همکف"
    if floor < 0:
        return "زیرزمین"
    if not total:
        return f"طبقه {floor}"
    return ""


def qr_yn(value):
    if value is True:
        return "دارد"
    if value is False:
        return "ندارد"
    return ""


def qr_tri_line(icon, label, value):
    if value is True:
        return f"{icon} {label} دارد"
    if value is False:
        return f"{icon} {label} ندارد"
    return f"❔ {label} نامشخص"


QR_SOURCE_LABELS = {
    "divar": "لینک دیوار", "text": "متن", "voice": "ویس",
}


def qr_render_preview(draft):
    f = draft["fields"]
    lines = ["📋 فایل استخراج‌شده", ""]

    lines.append("📍 " + (f["area"] if f.get("area") else "❔ منطقه نامشخص"))
    if f.get("property_type"):
        lines.append(f"🏘 {f['property_type']}")
    lines.append(
        f"📐 {qr_num_text(f['meterage'])} متر"
        if f.get("meterage") is not None else "❔ متراژ نامشخص"
    )
    lines.append(
        f"🛏 {qr_fa(f['bedrooms'])} خواب"
        if f.get("bedrooms") is not None else "❔ تعداد خواب نامشخص"
    )
    if f.get("floor") is not None:
        txt = f"🏢 طبقه {qr_fa(f['floor'])}"
        if f.get("total_floors") is not None:
            txt += f" از {qr_fa(f['total_floors'])}"
        lines.append(txt)
    elif f.get("total_floors") is not None:
        lines.append(f"🏢 کل طبقات: {qr_fa(f['total_floors'])}")
    else:
        lines.append("❔ طبقه نامشخص")
    lines.append(
        f"🏗 {qr_fa(f['building_age'])} سال"
        if f.get("building_age") is not None else "❔ سن بنا نامشخص"
    )
    lines.append(qr_tri_line("🚗", "پارکینگ", f.get("parking")))
    lines.append(qr_tri_line("🛗", "آسانسور", f.get("elevator")))
    lines.append(qr_tri_line("📦", "انباری", f.get("storage")))
    lines.append(
        f"💰 {price_label(f['price'])}"
        if f.get("price") is not None else "❔ قیمت نامشخص"
    )
    if f.get("address"):
        lines.append(f"🏠 {f['address']}")
    if f.get("owner_name"):
        lines.append(f"👤 {f['owner_name']}")
    if f.get("owner_phone"):
        lines.append(f"📞 {qr_fa(f['owner_phone'])}")

    if draft.get("urgent_hint"):
        lines.append("")
        lines.append(
            "🚨 در ویس به‌صراحت فوریت گفته شد؛ بعد از ثبت می‌توانی "
            "«🚨 فوری کردن» را بزنی."
        )
    notes = [w["t"] for w in draft.get("warnings", [])]
    ft, tf = f.get("floor"), f.get("total_floors")
    if ft is not None and tf is not None and ft > tf:
        notes.append("طبقه از کل طبقات بیشتر است؛ بررسی کن.")
    if draft.get("similar_code"):
        notes.append(
            f"فایل مشابهی با کد {draft['similar_code']} قبلاً ثبت شده است."
        )
    if notes:
        lines.append("")
        lines += [f"⚠️ {n}" for n in notes]

    missing = qr_missing_required(f)
    if missing:
        lines += ["", "⛔ برای ثبت لازم است: " + "، ".join(missing)]

    if draft.get("transcript"):
        t = draft["transcript"].strip()
        lines += ["", "🎤 متن شنیده‌شده: " + (t[:250] + "…" if len(t) > 250 else t)]
    lines += ["", f"🔎 منبع: {QR_SOURCE_LABELS.get(draft.get('source'), '—')}"]
    text = "\n".join(lines)
    return text[:3900]


QR_EDIT_FIELDS = {
    "area": ("📍 منطقه", "choice"),
    "property_type": ("🏘 نوع ملک", "choice"),
    "meterage": ("📐 متراژ", "number"),
    "bedrooms": ("🛏 خواب", "int"),
    "floor": ("🏢 طبقه", "int"),
    "total_floors": ("🏬 کل طبقات", "int"),
    "building_age": ("🏗 سن بنا", "int"),
    "parking": ("🚗 پارکینگ", "tri"),
    "elevator": ("🛗 آسانسور", "tri"),
    "storage": ("📦 انباری", "tri"),
    "price": ("💰 قیمت", "price"),
    "address": ("🏠 آدرس", "text"),
    "owner_name": ("👤 مالک", "text"),
    "owner_phone": ("📞 تلفن مالک", "phone"),
}

QR_TRI = ["دارد", "ندارد", "نامشخص"]


def qr_choice_options(key):
    if key == "area":
        return list(AREAS)
    if key == "property_type":
        return list(PROPERTY_TYPES)
    return list(QR_TRI)


def qr_choice_value(key, idx):
    opts = qr_choice_options(key)
    if idx < 0 or idx >= len(opts):
        raise ValueError("bad index")
    if QR_EDIT_FIELDS[key][1] == "tri":
        return [True, False, None][idx]
    return opts[idx]


def qr_parse_edit(key, text):
    """-> (ok, value). '-' clears the field."""
    t = (text or "").strip()
    if t in ("-", "—", "حذف", "پاک"):
        return True, None
    kind = QR_EDIT_FIELDS[key][1]
    if kind == "number":
        v = qr_parse_number(t)
    elif kind == "int":
        v = qr_parse_int(t)
    elif kind == "price":
        v = qr_parse_price(t)
    elif kind == "phone":
        v = qr_clean_phone(t)
    else:
        v = t[:300] if t else None
    if v is None:
        return False, None
    if key in QR_RANGES:
        lo, hi = QR_RANGES[key]
        if not (lo <= v <= hi):
            return False, None
    return True, v


# ---------------------------------------------------------
# QR PURE END
# ---------------------------------------------------------


@dataclass
class QRSource:
    kind: str
    text: str = ""
    head: str = ""
    url: str = None
    token: str = None
    images: list = dc_field(default_factory=list)
    image_bytes: bytes = None
    image_mime: str = "image/jpeg"
    transcript: str = None


# ---- Source parser: Divar ----

class QRDivarParser:
    API = "https://api.divar.ir/v8/posts-v2/web/{token}"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; HoomanCRM/1.0)",
        "Accept": "application/json, text/html;q=0.8",
        "Accept-Language": "fa-IR,fa;q=0.9",
    }
    NUM_KEYS = ("price", "size", "room", "floor", "year", "age", "count")

    @classmethod
    def _walk(cls, node, texts, images, depth=0):
        if depth > 14:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    cls._walk(v, texts, images, depth + 1)
                elif isinstance(v, str):
                    cls._take_str(v, texts, images)
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    if any(x in str(k).lower() for x in cls.NUM_KEYS):
                        texts.append(f"{k}: {v}")
        elif isinstance(node, list):
            for v in node:
                if isinstance(v, (dict, list)):
                    cls._walk(v, texts, images, depth + 1)
                elif isinstance(v, str):
                    cls._take_str(v, texts, images)

    @staticmethod
    def _take_str(v, texts, images):
        v = v.strip()
        if not v:
            return
        if v.startswith("http"):
            low = v.lower()
            if re.search(r"\.(jpe?g|png|webp)(\?|$)", low) and not any(
                x in low for x in ("icon", "logo", "avatar", "placeholder")
            ):
                images.append(v)
            return
        if len(v) <= 2500:
            texts.append(v)

    @staticmethod
    def _meta(page, prop):
        for pat in (
            r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*content=["\']([^"\']*)["\']',
            r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']%s["\']',
        ):
            m = re.search(pat % re.escape(prop), page, re.I)
            if m:
                return html_lib.unescape(m.group(1)).strip()
        return ""

    @classmethod
    async def fetch(cls, url, token):
        texts, images = [], []
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(
            timeout=timeout, headers=cls.HEADERS
        ) as http:
            try:
                async with http.get(cls.API.format(token=token)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        cls._walk(data, texts, images)
            except Exception as exc:
                print("DIVAR API ERROR:", exc)

            if not texts:
                try:
                    async with http.get(url) as resp:
                        if resp.status == 200:
                            page = await resp.text()
                            for prop in ("og:title", "og:description", "description"):
                                v = cls._meta(page, prop)
                                if v:
                                    texts.append(v)
                            img = cls._meta(page, "og:image")
                            if img.startswith("http"):
                                images.append(img)
                            for blob in re.findall(
                                r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                                page, re.S | re.I,
                            ):
                                try:
                                    cls._walk(json.loads(blob), texts, images)
                                except Exception:
                                    pass
                except Exception as exc:
                    print("DIVAR PAGE ERROR:", exc)

        if not texts:
            raise QRError(
                "نتوانستم اطلاعات آگهی را از دیوار بگیرم "
                "(آگهی حذف شده یا دیوار پاسخ نداد).\n"
                "متن آگهی یا اسکرین‌شات آن را بفرست."
            )

        clean = []
        for t in texts:
            if not clean or clean[-1] != t:
                clean.append(t)
        uniq_images = list(dict.fromkeys(images))[:MAX_PROPERTY_PHOTOS]
        slug = qr_divar_slug(url)
        return QRSource(
            kind="divar",
            text="\n".join(clean)[:9000],
            head=" ".join([slug] + clean[:4]),
            url=url,
            token=token,
            images=uniq_images,
        )


# ---- Local extractor (no AI/API required) ----


def qr_extract_local(text):
    """Extract the useful sale-file fields from Persian free text / Divar text.

    This parser deliberately does not guess. It only returns values supported by
    recognizable words/patterns in the source. An optional external AI can be
    added later without changing the rest of the quick-register pipeline.
    """
    text = (text or "").strip()
    n = qr_norm(text)
    out = {}

    def put(name, value, evidence=None):
        if value is not None and value != "":
            out[name] = {"value": value, "evidence": evidence or str(value)}

    # Area: prefer one of the CRM's exact configured areas.
    area = qr_match_area(text)
    if area:
        put("area", area, area)

    # Property type.
    for pt in PROPERTY_TYPES:
        if pt != "سایر" and qr_norm(pt) in n:
            put("property_type", pt, pt)
            break

    # Meterage.
    meter_patterns = [
        r"(?:متراژ|زیربنا|مساحت|متراژ\s*ملک|size)\s*[:：]?\s*(\d+(?:[\.,]\d+)?)\s*(?:متر|مترمربع|متر مربع)?",
        r"(\d+(?:[\.,]\d+)?)\s*(?:متر|مترمربع|متر مربع)\b",
    ]
    for pat in meter_patterns:
        m = re.search(pat, n, re.I)
        if m:
            val = qr_parse_number(m.group(1))
            if val is not None:
                put("meterage", val, m.group(0))
                break

    # Bedrooms. Support both digits and common Persian number words.
    bedroom_words = {
        "یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5,
        "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10,
    }
    m = re.search(r"(?:\b(\d+)\s*خواب\b|\b(\d+)\s*خوابه\b|\b(\d+)\s*اتاق\b|\broom\s*[:：]?\s*(\d+)\b)", n)
    if m:
        raw = next((x for x in m.groups() if x is not None), None)
        put("bedrooms", qr_parse_int(raw), m.group(0))
    else:
        m = re.search(r"(یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده)\s*(?:خواب|خوابه|اتاق)", n)
        if m:
            put("bedrooms", bedroom_words[m.group(1)], m.group(0))

    # Floor and total floors.
    m = re.search(r"طبقه\s*(-?\d+)\s*(?:از|/|\s)\s*(\d+)\s*(?:طبقه)?", n)
    if m:
        put("floor", qr_parse_int(m.group(1)), m.group(0))
        put("total_floors", qr_parse_int(m.group(2)), m.group(0))
    else:
        m = re.search(r"(?:طبقه|واحد\s*طبقه)\s*(-?\d+)", n)
        if m:
            put("floor", qr_parse_int(m.group(1)), m.group(0))
        else:
            m = re.search(r"\bfloor\s*[:：]?\s*(-?\d+)\b", n)
            if m:
                put("floor", qr_parse_int(m.group(1)), m.group(0))
        m = re.search(r"(?:کل\s*طبقات|تعداد\s*طبقات|ساختمان\s*(?:با|دارای)\s*)\s*(\d+)\s*طبقه", n)
        if m:
            put("total_floors", qr_parse_int(m.group(1)), m.group(0))

    # Building age / construction year. Prefer an explicit construction year
    # so phrases such as "سال ساخت ۱۴۰۵" are never mistaken for an age.
    m = re.search(r"سال\s*ساخت\s*[:：]?\s*(1[34]\d{2})", n)
    if m:
        year = qr_parse_int(m.group(1))
        age = max(0, 1405 - year) if year is not None else None
        if age is not None and age <= 100:
            put("building_age", age, m.group(0))
    else:
        m = re.search(r"(?:سن\s*(?:بنا|ساختمان)|سن)\s*[:：]?\s*(\d+)\s*سال", n)
        if not m:
            m = re.search(r"(\d+)\s*ساله\b", n)
        if m:
            raw = m.group(1)
            age = qr_parse_int(raw)
            if age is not None and age <= 100:
                put("building_age", age, m.group(0))

    # Amenities. Explicit negative wording wins.
    def amenity(patterns_true, patterns_false, field):
        for pat in patterns_false:
            m = re.search(pat, n)
            if m:
                put(field, False, m.group(0))
                return
        for pat in patterns_true:
            m = re.search(pat, n)
            if m:
                put(field, True, m.group(0))
                return

    amenity(
        [r"پارکینگ\s*(?:دارد|دار|موجود|هست)", r"پارکینگ\b"],
        [r"بدون\s*پارکینگ", r"پارکینگ\s*ندارد", r"فاقد\s*پارکینگ"],
        "parking",
    )
    amenity(
        [r"آسانسور\s*(?:دارد|دار|موجود|هست)", r"آسانسور\b"],
        [r"بدون\s*آسانسور", r"آسانسور\s*ندارد", r"فاقد\s*آسانسور"],
        "elevator",
    )
    amenity(
        [r"انباری\s*(?:دارد|دار|موجود|هست)", r"انباری\b"],
        [r"بدون\s*انباری", r"انباری\s*ندارد", r"فاقد\s*انباری"],
        "storage",
    )

    # Price. Prefer phrases near price keywords; otherwise use common billion/million
    # expressions. We intentionally do not interpret a bare number as a price.
    price_patterns = [
        r"(?:قیمت|فروش|قیمت\s*کل|کل\s*قیمت|price)\s*[:：]?\s*([\d۰-۹\.,]+\s*(?:میلیارد|ملیارد|میلیون|هزار)?)(?:\s*تومان|\s*ت)?",
        r"([\d۰-۹\.,]+\s*(?:میلیارد|ملیارد|میلیون))\s*(?:تومان|ت)?",
    ]
    for pat in price_patterns:
        m = re.search(pat, n)
        if m:
            val = qr_parse_price(m.group(1))
            if val is not None and val >= QR_RANGES["price"][0]:
                put("price", val, m.group(0))
                break

    # Owner phone/name only when explicitly labelled.
    m = re.search(r"(?:تماس|شماره|موبایل|تلفن)\s*(?:مالک)?\s*[:：]?\s*(09[\d۰-۹]{9})", n)
    if m:
        phone = qr_clean_phone(m.group(1))
        put("owner_phone", phone, m.group(0))
    m = re.search(r"(?:مالک|نام\s*مالک)\s*[:：]\s*([^\n,،]{2,80})", text, re.I)
    if m:
        put("owner_name", m.group(1).strip(), m.group(0))

    # Address: only explicit labels, otherwise keep area separate.
    m = re.search(r"(?:آدرس|نشانی)\s*[:：]\s*([^\n]{2,200})", text, re.I)
    if m:
        put("address", m.group(1).strip(), m.group(0))

    # The source itself is the description; for Divar this is the raw extracted
    # listing text, for free text it is exactly what the agent typed.
    if text:
        put("description", text[:600], text[:300])

    # Sale only. A tenant/lease mention inside a sale listing must not turn it into rent.
    if re.search(r"\b(?:فروش|فروشی|فروش\s*آپارتمان|قیمت\s*فروش)\b", n):
        put("transaction_type", "sale", "فروش")

    return out


# ---- DB helpers (duplicate detection / file service) ----

async def qr_check_divar_duplicate(token):
    async with SessionLocal() as session:
        row = (await session.execute(
            select(Property.id, Property.code)
            .where(Property.divar_token == token)
            .limit(1)
        )).first()
    if row:
        raise QRDuplicate(row[0], row[1])


async def qr_find_similar(fields):
    a, m, p = fields.get("area"), fields.get("meterage"), fields.get("price")
    if not (a and m and p):
        return None
    async with SessionLocal() as session:
        return (await session.execute(
            select(Property.id, Property.code).where(
                Property.area == a,
                Property.price == float(p),
                Property.sqm.between(float(m) - 1, float(m) + 1),
                Property.deal_type == ENV_SALE,
            ).limit(1)
        )).first()


async def qr_generate_code(session):
    prefix = "Q" + utcnow_naive().strftime("%y%m%d") + "-"
    n = await session.scalar(
        select(func.count(Property.id)).where(Property.code.like(prefix + "%"))
    ) or 0
    for i in range(1, 60):
        code = f"{prefix}{n + i}"
        exists = await session.scalar(
            select(func.count(Property.id)).where(Property.code == code)
        )
        if not exists:
            return code
    return prefix + uuid4().hex[:6]


async def qr_create_property(tg_user, draft):
    f = draft["fields"]
    async with SessionLocal() as session:
        if draft.get("divar_token"):
            row = (await session.execute(
                select(Property.id, Property.code)
                .where(Property.divar_token == draft["divar_token"])
                .limit(1)
            )).first()
            if row:
                raise QRDuplicate(row[0], row[1])

        user = await get_user(session, tg_user.id, tg_user.full_name)
        code = await qr_generate_code(session)

        desc = f.get("description") or ""
        if draft.get("source_url"):
            desc = (desc + "\n\n" if desc else "") + f"🔗 {draft['source_url']}"

        floor = f.get("floor")
        total = f.get("total_floors")
        prop = Property(
            code=code,
            area=f["area"],
            address=f.get("address") or "",
            sqm=float(f["meterage"]),
            price=float(f.get("price") or 0),
            property_type=f.get("property_type") or "",
            bedrooms=f.get("bedrooms") or 0,
            floors=total or 0,
            unit_floor=floor if floor is not None else 0,
            units_per_floor=1,
            elevator=qr_yn(f.get("elevator")),
            parking=qr_yn(f.get("parking")),
            storage=qr_yn(f.get("storage")),
            owner_name=f.get("owner_name") or "",
            owner_phone=f.get("owner_phone") or "",
            description=desc,
            status="🟢 فعال",
            deal_type=ENV_SALE,
            floor_label=qr_floor_label(floor, total),
            created_by=tg_user.id,
            updated_at=utcnow_naive(),
            building_age=f.get("building_age"),
            source=draft.get("source") or "manual",
            source_url=draft.get("source_url"),
            divar_token=draft.get("divar_token"),
        )
        session.add(prop)
        await session.commit()

        for fid in (draft.get("photo_ids") or [])[:MAX_PROPERTY_PHOTOS]:
            session.add(PropertyPhoto(property_id=prop.id, file_id=fid))
        await session.commit()

        await add_activity(
            session,
            user.id,
            "ثبت فایل",
            f"فایل {prop.code} ثبت شد. (ثبت سریع: "
            f"{QR_SOURCE_LABELS.get(draft.get('source'), '—')})",
            property_id=prop.id,
        )
        await ensure_ad_row(session, prop.id)
    return prop


# ---- pipeline ----

async def qr_run_pipeline(message, kind, payload):
    head_text = ""
    source_text = None
    image_bytes = None
    image_mime = "image/jpeg"
    url = token = None
    photos = []
    transcript = None
    urgent_hint = False
    ai_raw = {}

    if kind == "divar":
        url = payload
        token = qr_divar_token(url)
        if not token:
            raise QRError(
                "این لینک، لینک مستقیم یک آگهی دیوار نیست.\n"
                "لینک خود آگهی را بفرست (مثل divar.ir/v/…)."
            )
        await qr_check_divar_duplicate(token)
        src = await QRDivarParser.fetch(url, token)
        source_text, head_text, photos = src.text, src.head, src.images

    elif kind == "text":
        source_text = payload

    elif kind == "voice":
        try:
            transcript, ai_raw, urgent_hint = await ai_voice_extract(
                payload["bytes"], payload.get("mime") or "audio/ogg"
            )
        except AIError as exc:
            raise QRError(exc.user_message)
        source_text = transcript

    else:
        raise QRError("فقط لینک دیوار، متن آزاد یا ویس پشتیبانی می‌شود.")

    raw = qr_extract_local(source_text)
    if kind == "voice":
        raw = qr_merge_raw(raw, ai_raw)
    fields, warnings = qr_normalize(raw, source_text, kind)
    fields, warnings = qr_validate(fields, warnings)

    tx = qr_decide_transaction(head_text, fields.get("transaction_type"))
    if tx == "rent":
        raise QRRentListing()
    # This CRM is sale-only. Mentions of a tenant inside a sale listing do not
    # convert the property to rent. Unknown transaction type is treated as sale.
    fields["transaction_type"] = "sale"

    similar = await qr_find_similar(fields)
    return {
        "source": kind,
        "source_url": url,
        "divar_token": token,
        "fields": fields,
        "warnings": warnings,
        "photos": photos,
        "photo_ids": [],
        "transcript": transcript,
        "urgent_hint": urgent_hint,
        "similar_id": similar[0] if similar else None,
        "similar_code": similar[1] if similar else None,
    }


async def qr_send_album(message, urls):
    ids = []
    urls = list(urls or [])[:MAX_PROPERTY_PHOTOS]
    if not urls:
        return ids
    try:
        if len(urls) == 1:
            sent = [await message.answer_photo(urls[0])]
        else:
            sent = await message.answer_media_group(
                [InputMediaPhoto(media=u) for u in urls]
            )
        return [s.photo[-1].file_id for s in sent if s.photo]
    except Exception as exc:
        print("ALBUM ERROR:", exc)
    for u in urls:
        try:
            s = await message.answer_photo(u)
            if s.photo:
                ids.append(s.photo[-1].file_id)
        except Exception as exc:
            print("PHOTO ERROR:", exc)
    return ids


# ---- keyboards ----

def qr_preview_markup(draft):
    rows = []
    if draft.get("similar_id"):
        rows.append([InlineKeyboardButton(
            text=f"👁 مشاهده فایل مشابه ({draft['similar_code']})"[:60],
            callback_data=f"popen:{draft['similar_id']}",
        )])
    if not qr_missing_required(draft["fields"]):
        rows.append([InlineKeyboardButton(
            text="✅ ثبت فایل", callback_data="qk:ok")])
    rows.append([
        InlineKeyboardButton(text="✏️ اصلاح", callback_data="qk:ed"),
        InlineKeyboardButton(text="❌ لغو", callback_data="qk:no"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def qr_edit_markup():
    rows, cur = [], []
    for key, (label, _kind) in QR_EDIT_FIELDS.items():
        cur.append(InlineKeyboardButton(
            text=label, callback_data=f"qk:f:{key}"))
        if len(cur) == 2:
            rows.append(cur)
            cur = []
    if cur:
        rows.append(cur)
    rows.append([InlineKeyboardButton(
        text="⬅️ بازگشت", callback_data="qk:bk")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def qr_choice_markup(key):
    opts = qr_choice_options(key)
    rows, cur = [], []
    for i, name in enumerate(opts):
        cur.append(InlineKeyboardButton(
            text=name, callback_data=f"qk:c:{key}:{i}"))
        limit = 1 if key == "area" else 2
        if len(cur) == limit:
            rows.append(cur)
            cur = []
    if cur:
        rows.append(cur)
    rows.append([
        InlineKeyboardButton(text="🧹 پاک کردن", callback_data=f"qk:c:{key}:x"),
        InlineKeyboardButton(text="⬅️ بازگشت", callback_data="qk:ed"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def qr_method_markup():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔗 لینک دیوار", callback_data="qk:m:link"),
        InlineKeyboardButton(text="📝 متن آزاد", callback_data="qk:m:text"),
    ], [
        InlineKeyboardButton(text="🎙 ثبت با ویس", callback_data="qk:m:voice"),
    ]])


QR_HINTS = {
    "voice": "🎙 مشخصات ملک را به‌صورت پیام صوتی (ویس) بفرست؛ مثلاً "
             "منطقه، متراژ، تعداد خواب، طبقه، قیمت و امکانات. "
             "بعد از تبدیل به متن، پیش‌نمایش را می‌بینی و فقط با "
             "تأیید خودت ثبت می‌شود.",
    "link": "🔗 لینک مستقیم آگهی دیوار را بفرست (مثل https://divar.ir/v/…).",
    "text": "📝 مشخصات را آزادانه در یک پیام بنوی؛ مثلاً:\n"
            "«خانی‌آباد نو جنوبی، ۸۵ متر، دو خواب، طبقه ۳، ۱۰ ساله، "
            "پارکینگ و آسانسور، ۳.۵ میلیارد»",
}



# ---- handlers ----

@dp.message(F.text == "⚡ ثبت سریع")
async def qr_start(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    await state.clear()
    await state.set_state(QuickForm.waiting)
    await message.answer(
        "⚡ ثبت سریع فایل فروش\n\n"
        "فقط یکی از این موارد را بفرست:\n"
        "🔗 لینک آگهی دیوار\n"
        "📝 متن آزاد مشخصات فایل\n"
        "🎙 پیام صوتی (ویس)\n\n"
        "مثال متن: خانی‌آباد نو جنوبی، ۸۵ متر، دو خواب، "
        "طبقه ۳، پارکینگ، آسانسور، ۳.۵ میلیارد",
        reply_markup=keyboard([], include_cancel=True),
    )
    await message.answer("نوع ورودی:", reply_markup=qr_method_markup())


async def qr_process(message, state, kind, payload):
    status = await message.answer("⏳ در حال استخراج اطلاعات…")
    draft = None
    try:
        draft = await qr_run_pipeline(message, kind, payload)
        if draft["photos"]:
            draft["photo_ids"] = await qr_send_album(message, draft["photos"])
    except QRDuplicate as dup:
        await message.answer(
            f"⚠️ این آگهی قبلاً در سیستم ثبت شده است.\n🔢 کد فایل: {dup.code}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="👁 مشاهده فایل", callback_data=f"popen:{dup.prop_id}")
            ]]),
        )
    except QRRentListing:
        await message.answer(
            "این آگهی مربوط به اجاره است. در حال حاضر ثبت فایل اجاره در ربات فعال نیست."
        )
    except QRError as exc:
        await message.answer(f"⚠️ {exc}")
    except Exception as exc:
        print("QUICK REGISTER ERROR:", repr(exc))
        await message.answer("⚠️ خطایی رخ داد؛ دوباره تلاش کن یا از «➕ ثبت فایل» استفاده کن.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass
    if not draft:
        return
    await state.set_state(QuickForm.preview)
    await state.update_data(draft=draft)
    await message.answer(
        qr_render_preview(draft), reply_markup=qr_preview_markup(draft)
    )


async def qr_leave_for_button(message, state):
    await state.clear()
    await message.answer(
        "ثبت سریع بسته شد. دوباره دکمه‌ی موردنظر را بزن.",
        reply_markup=main_menu(message.from_user.id),
    )


@dp.message(StateFilter(QuickForm.waiting, QuickForm.preview), F.text)
async def qr_on_text(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    text = message.text.strip()
    if text in QR_KNOWN_BUTTONS:
        await qr_leave_for_button(message, state)
        return
    url = qr_find_divar_url(text)
    if url:
        await qr_process(message, state, "divar", url)
    else:
        await qr_process(message, state, "text", text)


@dp.message(StateFilter(QuickForm.waiting, QuickForm.preview), F.voice)
async def qr_on_voice(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    if not ai_available():
        await message.answer(AI_UNAVAILABLE_TEXT)
        return
    v = message.voice
    if (v.duration or 0) > VOICE_MAX_SECONDS:
        await message.answer(
            f"ویس خیلی طولانی است (حداکثر {VOICE_MAX_SECONDS} ثانیه). "
            "کوتاه‌تر بفرست."
        )
        return
    if (v.file_size or 0) > VOICE_MAX_BYTES:
        await message.answer("حجم ویس زیاد است؛ کوتاه‌تر بفرست.")
        return
    try:
        buf = await bot.download(v)
        audio = buf.getvalue()
    except Exception as exc:
        print("VOICE DOWNLOAD ERROR:", type(exc).__name__)
        await message.answer("⚠️ دریافت ویس انجام نشد؛ دوباره بفرست.")
        return
    await qr_process(
        message, state, "voice",
        {"bytes": audio, "mime": v.mime_type or "audio/ogg"},
    )


@dp.message(StateFilter(QuickForm.waiting, QuickForm.preview))
async def qr_on_other(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    await message.answer("لینک دیوار یا متن آزاد مشخصات فایل را بفرست.")


@dp.message(StateFilter(QuickForm.edit_value), F.text)
async def qr_on_edit_value(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    text = message.text.strip()
    if text in QR_KNOWN_BUTTONS:
        await qr_leave_for_button(message, state)
        return
    data = await state.get_data()
    draft, key = data.get("draft"), data.get("edit_field")
    if not draft or key not in QR_EDIT_FIELDS:
        await state.clear()
        await message.answer(
            "نشست منقضی شد. دوباره «⚡ ثبت سریع» را بزن.",
            reply_markup=main_menu(message.from_user.id),
        )
        return
    ok, value = qr_parse_edit(key, text)
    if not ok:
        await message.answer("⚠️ مقدار نامعتبر است؛ دوباره بفرست (یا - برای پاک کردن).")
        return
    draft["fields"][key] = value
    draft["warnings"] = [w for w in draft["warnings"] if w.get("f") != key]
    if key in ("area", "meterage", "price"):
        sim = await qr_find_similar(draft["fields"])
        draft["similar_id"] = sim[0] if sim else None
        draft["similar_code"] = sim[1] if sim else None
    await state.set_state(QuickForm.preview)
    await state.update_data(draft=draft, edit_field=None)
    await message.answer(
        qr_render_preview(draft), reply_markup=qr_preview_markup(draft)
    )


@dp.callback_query(F.data.startswith("qk:"))
async def qr_callback(callback: CallbackQuery, state: FSMContext):
    if not await callback_access_required(callback):
        return
    parts = callback.data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "m":
        if parts[2] == "voice" and not ai_available():
            await callback.message.answer(AI_UNAVAILABLE_TEXT)
        else:
            await callback.message.answer(QR_HINTS.get(parts[2], ""))
        await callback.answer()
        return

    data = await state.get_data()
    draft = data.get("draft")
    if not draft:
        await callback.answer(
            "نشست منقضی شد. دوباره «⚡ ثبت سریع» را بزن.", show_alert=True)
        return

    if action == "no":
        await state.clear()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(
            "❌ ثبت سریع لغو شد.",
            reply_markup=main_menu(callback.from_user.id),
        )
        await callback.answer()
        return

    if action in ("bk", "ed", "c"):
        await state.set_state(QuickForm.preview)

    if action == "bk":
        await show(callback.message, qr_render_preview(draft),
                   qr_preview_markup(draft), edit=True)
        await callback.answer()
        return

    if action == "ed":
        await show(callback.message, "✏️ کدام مورد را اصلاح کنم؟",
                   qr_edit_markup(), edit=True)
        await callback.answer()
        return

    if action == "f":
        key = parts[2]
        if key not in QR_EDIT_FIELDS:
            await callback.answer()
            return
        label, kind = QR_EDIT_FIELDS[key]
        if kind in ("choice", "tri"):
            await show(callback.message, f"{label} را انتخاب کن:",
                       qr_choice_markup(key), edit=True)
        else:
            hints = {
                "price": "قیمت صحیح را وارد کنید.\n(مثلاً ۳.۵ میلیارد یا ۳۵۰۰۰۰۰۰۰۰)",
                "number": "متراژ صحیح را وارد کنید.",
                "phone": "تلفن صحیح را وارد کنید.",
            }
            plain = label.split(" ", 1)[1]
            await state.set_state(QuickForm.edit_value)
            await state.update_data(edit_field=key)
            await callback.message.answer(
                hints.get(key, f"{plain} صحیح را وارد کنید.")
                + "\n(برای پاک کردن مقدار: -)",
                reply_markup=keyboard([], include_cancel=True),
            )
        await callback.answer()
        return

    if action == "c":
        key, idx = parts[2], parts[3]
        if key not in QR_EDIT_FIELDS:
            await callback.answer()
            return
        try:
            value = None if idx == "x" else qr_choice_value(key, int(idx))
        except Exception:
            await callback.answer()
            return
        draft["fields"][key] = value
        draft["warnings"] = [w for w in draft["warnings"] if w.get("f") != key]
        if key == "area":
            sim = await qr_find_similar(draft["fields"])
            draft["similar_id"] = sim[0] if sim else None
            draft["similar_code"] = sim[1] if sim else None
        await state.update_data(draft=draft)
        await show(callback.message, qr_render_preview(draft),
                   qr_preview_markup(draft), edit=True)
        await callback.answer("✅ اصلاح شد")
        return

    if action == "ok":
        tg = callback.from_user
        missing = qr_missing_required(draft["fields"])
        if missing:
            await callback.answer(
                "برای ثبت لازم است: " + "، ".join(missing), show_alert=True)
            return
        if tg.id in QR_SAVING:
            await callback.answer("در حال ثبت…")
            return
        QR_SAVING.add(tg.id)
        try:
            prop = await qr_create_property(tg, draft)
        except QRDuplicate as dup:
            await state.clear()
            await callback.message.answer(
                f"⚠️ این آگهی قبلاً در سیستم ثبت شده است.\n🔢 کد فایل: {dup.code}",
                reply_markup=main_menu(tg.id),
            )
            await callback.answer()
            return
        except Exception as exc:
            print("QUICK SAVE ERROR:", repr(exc))
            await callback.answer("ثبت انجام نشد؛ دوباره تلاش کن.", show_alert=True)
            return
        finally:
            QR_SAVING.discard(tg.id)

        await state.clear()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        f = draft["fields"]
        price_txt = (
            price_label(f['price'])
            if f.get("price") is not None else "قیمت نامشخص"
        )
        await callback.message.answer(
            f"✅ فایل ثبت شد\n\n🔢 کد: {prop.code}\n"
            f"📍 {f['area']} | 📐 {qr_num_text(f['meterage'])} متر\n💰 {price_txt}",
            reply_markup=main_menu(tg.id),
        )
        await post_create_prompt(callback.message, "p", prop.id, tg_user=tg)
        await callback.answer("✅ ثبت شد")
        return

    await callback.answer()


# =========================================================
# 📊 عملکرد من  (main-menu entry; reuses the existing KPI + tools)
# =========================================================

@dp.message(F.text == "📊 عملکرد من")
async def performance_home(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    await state.clear()
    await my_kpi(message)
    rows = [["👀 ثبت بازدید", "📞 پیگیری"], ["📊 فعالیت‌ها"]]
    if is_admin(message.from_user.id):
        rows.append(["👥 KPI تیم", "📝 آخرین فعالیت‌ها"])
        rows.append(["📊 داشبورد مدیریتی"])
    rows.append(["⬅️ بازگشت"])
    await message.answer(
        "ابزارهای عملکرد 👇",
        reply_markup=keyboard(rows, include_cancel=False),
    )


# =========================================================
# OWNERSHIP / URGENT / FOLLOW-UP
# =========================================================

async def load_obj(session, kind, obj_id):
    model = Property if kind == "p" else Client
    return (await session.execute(
        select(model).where(model.id == obj_id)
    )).scalar_one_or_none()


@dp.callback_query(F.data.startswith("own:"))
async def toggle_ownership(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, kind, obj_id = callback.data.split(":")
    obj_id = int(obj_id)
    async with SessionLocal() as session:
        user = await get_user(
            session, callback.from_user.id, callback.from_user.full_name
        )
        obj = await load_obj(session, kind, obj_id)
        if not obj:
            await callback.answer("پیدا نشد", show_alert=True)
            return
        if obj.owner_user_id is None:
            obj.owner_user_id = user.id
        if (
            obj.owner_user_id != user.id
            and not is_admin(callback.from_user.id)
        ):
            await callback.answer(
                "فقط مسئول این مورد یا مدیر می‌تواند تغییر دهد.",
                show_alert=True
            )
            return
        obj.ownership_type = (
            "عمومی" if (obj.ownership_type or "عمومی") == "شخصی"
            else "شخصی"
        )
        await add_activity(
            session, user.id, "تغییر مالکیت",
            f"{ownership_text(obj)}",
            property_id=obj.id if kind == "p" else 0,
            client_id=obj.id if kind == "c" else 0,
        )
        await session.commit()
    if kind == "p":
        await send_property_detail(callback.message, obj_id, edit=True)
    else:
        await send_client_detail(callback.message, obj_id, edit=True)
    await callback.answer("✅ انجام شد")


async def notify_urgent(kind, obj, actor_tg_id):
    env = obj.deal_type or ENV_SALE
    flag_col = User.can_rent if env == ENV_RENT else User.can_sale
    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(flag_col == 1)
        )
        recipients = result.scalars().all()
        names = await user_name_map(session, [obj.owner_user_id])
    owner_name = names.get(obj.owner_user_id, "—")

    if kind == "p":
        text = (
            f"🚨 {env} فوری\n\n"
            f"{money(obj.sqm)} متر | {obj.area}\n"
            f"{obj.bedrooms} خواب\n"
            f"{prop_price_text(obj)}\n"
            f"👤 مسئول: {owner_name}"
        )
        view_cb = f"popen:{obj.id}"
    else:
        text = (
            f"🚨 مشتری {env} فوری\n\n"
            f"{obj.name} | {obj.area}\n"
            f"{client_budget_text(obj)}\n"
            f"👤 مسئول: {owner_name}"
        )
        view_cb = f"copen:{obj.id}"
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="مشاهده", callback_data=view_cb),
        InlineKeyboardButton(
            text="من پیگیری می‌کنم",
            callback_data=f"claim:{kind}:{obj.id}"
        ),
    ]])
    sent = 0
    for u in recipients:
        if u.telegram_id == actor_tg_id:
            continue
        try:
            await bot.send_message(
                u.telegram_id, text, reply_markup=markup
            )
            sent += 1
        except Exception as exc:
            print("URGENT NOTIFY ERROR:", exc)
    return sent


@dp.callback_query(F.data.startswith("urg:"))
async def toggle_urgent(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, kind, obj_id = callback.data.split(":")
    obj_id = int(obj_id)
    async with SessionLocal() as session:
        user = await get_user(
            session, callback.from_user.id, callback.from_user.full_name
        )
        obj = await load_obj(session, kind, obj_id)
        if not obj:
            await callback.answer("پیدا نشد", show_alert=True)
            return
        make_urgent = not obj.is_urgent
        obj.is_urgent = 1 if make_urgent else 0
        obj.urgent_at = utcnow_naive() if make_urgent else None
        if not make_urgent:
            obj.follow_up_user_id = None
        await add_activity(
            session, user.id,
            "فوری کردن" if make_urgent else "عادی کردن",
            "",
            property_id=obj.id if kind == "p" else 0,
            client_id=obj.id if kind == "c" else 0,
        )
        await session.commit()
    sent = 0
    if make_urgent:
        sent = await notify_urgent(kind, obj, callback.from_user.id)
    if kind == "p":
        await send_property_detail(callback.message, obj_id, edit=True)
    else:
        await send_client_detail(callback.message, obj_id, edit=True)
    if make_urgent:
        await callback.answer(
            f"🚨 فوری شد؛ به {sent} مشاور اطلاع داده شد.",
            show_alert=True
        )
    else:
        await callback.answer("✅ عادی شد")


@dp.callback_query(F.data.startswith("claim:"))
async def claim_followup(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, kind, obj_id = callback.data.split(":")
    obj_id = int(obj_id)
    model = Property if kind == "p" else Client
    async with SessionLocal() as session:
        user = await get_user(
            session, callback.from_user.id, callback.from_user.full_name
        )
        # Atomic: only succeeds if nobody has claimed it yet.
        result = await session.execute(
            sa_update(model)
            .where(
                model.id == obj_id,
                model.follow_up_user_id.is_(None),
            )
            .values(follow_up_user_id=user.id)
        )
        await session.commit()
        won = (result.rowcount or 0) == 1
        holder_id = None
        if not won:
            obj = await load_obj(session, kind, obj_id)
            holder_id = obj.follow_up_user_id if obj else None
        names = await user_name_map(session, [holder_id])
        if won:
            await add_activity(
                session, user.id, "پیگیری",
                "مسئول پیگیری شد",
                property_id=obj_id if kind == "p" else 0,
                client_id=obj_id if kind == "c" else 0,
            )

    view_cb = f"popen:{obj_id}" if kind == "p" else f"copen:{obj_id}"
    if won:
        who = user.name or callback.from_user.full_name
        suffix = f"\n\n✅ پیگیری: {who}"
        await callback.answer(
            "✅ تو مسئول پیگیری شدی.", show_alert=True
        )
    elif holder_id == user.id:
        await callback.answer(
            "این مورد قبلاً به نام خودت ثبت شده.", show_alert=True
        )
        return
    else:
        who = names.get(holder_id, "یک مشاور")
        suffix = f"\n\n📌 پیگیری قبلاً توسط {who} برداشته شده."
        await callback.answer(
            f"این مورد را {who} برداشته است.", show_alert=True
        )
    try:
        await callback.message.edit_text(
            (callback.message.text or "") + suffix,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="مشاهده", callback_data=view_cb)
            ]])
        )
    except Exception:
        pass


# =========================================================
# FILE DETAIL (summary + separate sections)
# =========================================================

def floor_text(p):
    if p.floor_label:
        return p.floor_label
    return f"{p.unit_floor} از {p.floors}"


async def send_property_detail(target, prop_id, edit=False):
    async with SessionLocal() as session:
        prop = await load_obj(session, "p", prop_id)
        if not prop:
            await target.answer("فایل پیدا نشد.")
            return
        names = await user_name_map(
            session, [prop.owner_user_id, prop.follow_up_user_id]
        )
        n_photos, n_videos = await media_counts(session, prop.id)
        ad_status = await session.scalar(
            select(PropertyAd.status).where(
                PropertyAd.property_id == prop.id
            )
        )
    flag = "🚨 " if prop.is_urgent else ""
    lines = [
        f"{flag}🏠 فایل {prop.code}",
        f"{env_title(prop.deal_type)} | {ownership_text(prop)}",
        f"📍 {prop.area}",
        f"📐 {money(prop.sqm)} متر | 🛏 {prop.bedrooms} خواب",
        f"💰 {prop_price_text(prop)}",
        f"📊 {prop.status}",
        f"🖼 عکس: {n_photos} | 🎬 ویدئو: {n_videos}",
        f"📢 آگهی: {AD_STATUS_LABELS.get(ad_status or AD_UNKNOWN, '—')}",
        f"👤 مسئول: {names.get(prop.owner_user_id, '—')}",
    ]
    if prop.is_urgent and prop.follow_up_user_id:
        lines.append(
            f"📌 پیگیری: {names.get(prop.follow_up_user_id, '—')}"
        )
    if (prop.description or '').strip():
        lines.append(f"📝 توضیحات: {prop.description.strip()}")
    rows = [
        [
            InlineKeyboardButton(
                text="📋 اطلاعات ملک",
                callback_data=f"ps:{prop.id}:info"),
            InlineKeyboardButton(
                text="💰 قیمت و شرایط",
                callback_data=f"ps:{prop.id}:price"),
        ],
        [
            InlineKeyboardButton(
                text="📸 تصاویر", callback_data=f"pimg:{prop.id}"),
            InlineKeyboardButton(
                text="👤 مالک / مسئول",
                callback_data=f"ps:{prop.id}:owner"),
        ],
        [
            InlineKeyboardButton(
                text="🎬 ویدئوها", callback_data=f"vp:{prop.id}"),
            InlineKeyboardButton(
                text="📢 وضعیت آگهی", callback_data=f"adv:s:{prop.id}"),
        ],
        [
            InlineKeyboardButton(
                text="📍 موقعیت", callback_data=f"ps:{prop.id}:loc"),
        ],
        [
            InlineKeyboardButton(
                text="🎯 مشتری‌های پیشنهادی",
                callback_data=f"mc:{prop.id}:1:0"),
            InlineKeyboardButton(
                text="📞 فعالیت‌ها و پیگیری‌ها",
                callback_data=f"pact:{prop.id}:1"),
        ],
        [
            InlineKeyboardButton(
                text="✅ عادی کردن" if prop.is_urgent
                else "🚨 فوری کردن",
                callback_data=f"urg:p:{prop.id}"),
            InlineKeyboardButton(
                text="🌐 عمومی کردن"
                if ownership_text(prop) == "👤 شخصی"
                else "👤 شخصی کردن",
                callback_data=f"own:p:{prop.id}"),
        ],
    ]
    if prop.is_urgent and not prop.follow_up_user_id:
        rows.append([InlineKeyboardButton(
            text="📌 من پیگیری می‌کنم",
            callback_data=f"claim:p:{prop.id}")])
    rows.append([
        InlineKeyboardButton(
            text="✏️ ویرایش", callback_data=f"edit:{prop.id}"),
        InlineKeyboardButton(
            text="🔄 وضعیت", callback_data=f"status:{prop.id}"),
    ])
    rows.append([InlineKeyboardButton(
        text="🗑 حذف فایل", callback_data=f"deleteprop:{prop.id}")])
    await show(
        target, "\n".join(lines),
        InlineKeyboardMarkup(inline_keyboard=rows), edit=edit
    )


@dp.callback_query(F.data.startswith("ps:"))
async def property_section(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, pid, sec = callback.data.split(":")
    async with SessionLocal() as session:
        p = await load_obj(session, "p", int(pid))
        if not p:
            await callback.answer("پیدا نشد", show_alert=True)
            return
        names = await user_name_map(
            session, [p.owner_user_id, p.follow_up_user_id]
        )
    extra = []
    if sec == "info":
        text = (
            f"📋 اطلاعات ملک {p.code}\n\n"
            f"🏢 نوع: {p.property_type}\n"
            f"📐 متراژ: {money(p.sqm)}\n"
            f"🛏 خواب: {p.bedrooms}\n"
            f"🏠 طبقه: {floor_text(p)}\n"
            f"🚪 واحد در طبقه: {p.units_per_floor}\n"
            f"🛗 آسانسور: {p.elevator or '—'}\n"
            f"🚗 پارکینگ: {p.parking or '—'}"
            f"{(' (' + p.parking_type + ')') if p.parking_type else ''}\n"
            f"📦 انباری: {p.storage or '—'}\n"
            f"📄 سند: {p.document_type or '—'}"
        )
    elif sec == "price":
        if RENT_ENABLED and p.deal_type == ENV_RENT:
            text = (
                f"💰 شرایط اجاره {p.code}\n\n"
                f"نوع: {p.rent_type or '—'}\n"
                f"رهن: {money(p.deposit)}\n"
                f"اجاره: {money(p.rent)}\n"
                f"تبدیل رهن/اجاره: {p.convertible or '—'}\n"
                f"مدت قرارداد: {p.lease_term or '—'}\n"
                f"وضعیت سکونت: {p.tenant or '—'}\n"
                f"تاریخ تخلیه: {p.vacancy_date or '—'}"
            )
        else:
            text = (
                f"💰 قیمت {p.code}\n\n"
                f"قیمت: {price_label(p.price)}\n"
                f"وضعیت سکونت: {p.tenant or '—'}\n"
                f"تاریخ تخلیه: {p.vacancy_date or '—'}\n"
                f"ارزش معامله: {price_label(p.transaction_value)}"
            )
    elif sec == "owner":
        text = (
            f"👤 مالک / مسئول {p.code}\n\n"
            f"مالک: {p.owner_name or '—'}\n"
            f"📞 تلفن: {p.owner_phone or '—'}\n"
            f"مسئول فایل: {names.get(p.owner_user_id, '—')}\n"
            f"نوع مالکیت: {ownership_text(p)}\n"
            f"مسئول پیگیری: {names.get(p.follow_up_user_id, '—')}"
        )
        extra.append([InlineKeyboardButton(
            text="📂 فایل‌های همین مالک",
            callback_data=f"owner:{p.id}")])
    elif sec == "loc":
        text = (
            f"📍 موقعیت {p.code}\n\n"
            f"منطقه: {p.area}\n"
            f"آدرس: {p.address or '—'}"
        )
    else:
        text = f"📝 توضیحات {p.code}\n\n{p.description or '—'}"
    extra.append([InlineKeyboardButton(
        text="⬅️ بازگشت به فایل", callback_data=f"popen:{p.id}")])
    await callback.message.answer(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=extra)
    )
    await callback.answer()


# ---------------- photos: album + manager ----------------

async def send_photo_manager(target, prop_id):
    async with SessionLocal() as session:
        photos = (await session.execute(
            select(PropertyPhoto)
            .where(PropertyPhoto.property_id == prop_id)
            .order_by(PropertyPhoto.created_at, PropertyPhoto.id)
        )).scalars().all()
    rows = []
    for i, ph in enumerate(photos, start=1):
        rows.append([
            InlineKeyboardButton(
                text=f"🗑 حذف {i}", callback_data=f"pd:{ph.id}"),
            InlineKeyboardButton(
                text=f"⭐ اصلی {i}", callback_data=f"pm:{ph.id}"),
            InlineKeyboardButton(
                text=f"🔄 جایگزین {i}", callback_data=f"pr:{ph.id}"),
        ])
    if len(photos) < MAX_PROPERTY_PHOTOS:
        rows.append([InlineKeyboardButton(
            text="➕ افزودن عکس", callback_data=f"photos:{prop_id}")])
    rows.append([InlineKeyboardButton(
        text="🎬 ویدئوها", callback_data=f"vp:{prop_id}")])
    rows.append([InlineKeyboardButton(
        text="⬅️ بازگشت به فایل", callback_data=f"popen:{prop_id}")])
    await target.answer(
        f"📸 مدیریت تصاویر ({len(photos)}/{MAX_PROPERTY_PHOTOS})\n"
        f"عکس شمارهٔ ۱ تصویر اصلی است.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    return len(photos)


@dp.callback_query(F.data.startswith("pimg:"))
async def property_images(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    prop_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        photos = (await session.execute(
            select(PropertyPhoto)
            .where(PropertyPhoto.property_id == prop_id)
            .order_by(PropertyPhoto.created_at, PropertyPhoto.id)
        )).scalars().all()
    if photos:
        media = [
            InputMediaPhoto(media=p.file_id)
            for p in photos[:MAX_PROPERTY_PHOTOS]
        ]
        try:
            if len(media) == 1:
                await bot.send_photo(
                    callback.message.chat.id, media[0].media
                )
            else:
                await bot.send_media_group(
                    callback.message.chat.id, media
                )
        except Exception as exc:
            print("SEND PHOTOS ERROR:", exc)
    await send_photo_manager(callback.message, prop_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("pd:"))
async def photo_delete(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    photo_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        ph = (await session.execute(
            select(PropertyPhoto).where(PropertyPhoto.id == photo_id)
        )).scalar_one_or_none()
        if not ph:
            await callback.answer("پیدا نشد", show_alert=True)
            return
        prop_id = ph.property_id
        await session.delete(ph)
        await session.commit()
        user = await get_user(
            session, callback.from_user.id, callback.from_user.full_name
        )
        await add_activity(
            session, user.id, "حذف عکس فایل", "یک عکس حذف شد.",
            property_id=prop_id,
        )
    await callback.answer("🗑 حذف شد")
    await send_photo_manager(callback.message, prop_id)


@dp.callback_query(F.data.startswith("pm:"))
async def photo_make_main(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    photo_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        ph = (await session.execute(
            select(PropertyPhoto).where(PropertyPhoto.id == photo_id)
        )).scalar_one_or_none()
        if not ph:
            await callback.answer("پیدا نشد", show_alert=True)
            return
        earliest = await session.scalar(
            select(func.min(PropertyPhoto.created_at)).where(
                PropertyPhoto.property_id == ph.property_id
            )
        )
        ph.created_at = (earliest or utcnow_naive()) - timedelta(
            seconds=1
        )
        prop_id = ph.property_id
        await session.commit()
    await callback.answer("⭐ تصویر اصلی شد")
    await send_photo_manager(callback.message, prop_id)


@dp.callback_query(F.data.startswith("pr:"))
async def photo_replace_start(callback: CallbackQuery, state: FSMContext):
    if not await callback_access_required(callback):
        return
    photo_id = int(callback.data.split(":")[1])
    await state.clear()
    await state.update_data(photo_id=photo_id)
    await state.set_state(ReplacePhotoForm.photo)
    await callback.message.answer(
        "📷 عکس جدید را بفرست (برای انصراف /start بزن)."
    )
    await callback.answer()


@dp.message(ReplacePhotoForm.photo, F.photo)
async def photo_replace_save(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        ph = (await session.execute(
            select(PropertyPhoto).where(
                PropertyPhoto.id == data.get("photo_id")
            )
        )).scalar_one_or_none()
        if not ph:
            await state.clear()
            await message.answer("عکس پیدا نشد.")
            return
        ph.file_id = message.photo[-1].file_id
        prop_id = ph.property_id
        user = await get_user(
            session, message.from_user.id, message.from_user.full_name
        )
        await add_activity(
            session, user.id, "اصلاح فایل", "عکس جایگزین شد",
            property_id=prop_id
        )
        await session.commit()
    await state.clear()
    await message.answer(
        "✅ عکس جایگزین شد.",
        reply_markup=env_main_menu(message.from_user.id)
    )
    await send_photo_manager(message, prop_id)


@dp.message(ReplacePhotoForm.photo)
async def photo_replace_wrong(message: Message):
    await message.answer("لطفاً یک عکس بفرست.")


# ---------------- activities of one file / client ----------------

async def send_entity_activities(target, kind, obj_id, page, edit=False):
    col = Activity.property_id if kind == "p" else Activity.client_id
    async with SessionLocal() as session:
        total = await session.scalar(
            select(func.count(Activity.id)).where(col == obj_id)
        ) or 0
        total_pages = max(
            1, (total + ACTIVITY_PAGE_SIZE - 1) // ACTIVITY_PAGE_SIZE
        )
        page = max(1, min(page, total_pages))
        result = await session.execute(
            select(Activity, User.name)
            .outerjoin(User, User.id == Activity.user_id)
            .where(col == obj_id)
            .order_by(Activity.created_at.desc())
            .limit(ACTIVITY_PAGE_SIZE)
            .offset((page - 1) * ACTIVITY_PAGE_SIZE)
        )
        rows_data = result.all()
    lines = [f"📞 فعالیت‌ها — صفحه {page} از {total_pages} ({total})\n"]
    if not rows_data:
        lines.append("فعالیتی ثبت نشده.")
    for act, uname in rows_data:
        note = (act.note or "")[:40]
        lines.append(
            f"{tehran_time(act.created_at)} | {uname or '—'} | "
            f"{act.activity_type}"
            f"{(' | ' + note) if note else ''}"
        )
    cb = "pact" if kind == "p" else "cact"
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(
            text="‹ قبلی", callback_data=f"{cb}:{obj_id}:{page - 1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(
            text="بعدی ›", callback_data=f"{cb}:{obj_id}:{page + 1}"))
    rows = [nav]
    if kind == "p":
        rows.append([
            InlineKeyboardButton(
                text="🕒 ثبت رویداد", callback_data=f"event:{obj_id}"),
            InlineKeyboardButton(
                text="📜 تاریخچه", callback_data=f"history:{obj_id}"),
        ])
    rows.append([InlineKeyboardButton(
        text="⬅️ بازگشت",
        callback_data=(
            f"popen:{obj_id}" if kind == "p" else f"copen:{obj_id}"
        )
    )])
    await show(
        target, "\n".join(lines),
        InlineKeyboardMarkup(inline_keyboard=rows), edit=edit
    )


@dp.callback_query(F.data.startswith("pact:"))
async def property_activities(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, pid, page = callback.data.split(":")
    await send_entity_activities(
        callback.message, "p", int(pid), int(page),
        edit=(int(page) != 1 or (callback.message.text or "").startswith("📞"))
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("cact:"))
async def client_activities(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, cid, page = callback.data.split(":")
    await send_entity_activities(
        callback.message, "c", int(cid), int(page),
        edit=(int(page) != 1 or (callback.message.text or "").startswith("📞"))
    )
    await callback.answer()


# =========================================================
# CLIENT DETAIL (summary + sections + preferences)
# =========================================================

async def send_client_detail(target, client_id, edit=False):
    async with SessionLocal() as session:
        c = await load_obj(session, "c", client_id)
        if not c:
            await target.answer("مشتری پیدا نشد.")
            return
        names = await user_name_map(
            session, [c.owner_user_id, c.follow_up_user_id]
        )
    flag = "🚨 " if c.is_urgent else ""
    lines = [
        f"{flag}👤 {c.name}",
        f"{env_title(c.deal_type)} | {ownership_text(c)}",
        f"📍 {c.area}",
        f"💰 {client_budget_text(c)}",
        f"📊 {c.status}",
        f"👤 مسئول: {names.get(c.owner_user_id, '—')}",
    ]
    if c.is_urgent and c.follow_up_user_id:
        lines.append(
            f"📌 پیگیری: {names.get(c.follow_up_user_id, '—')}"
        )
    rows = [
        [
            InlineKeyboardButton(
                text="📋 اطلاعات", callback_data=f"cs:{c.id}:info"),
            InlineKeyboardButton(
                text="💰 بودجه و شرایط",
                callback_data=f"cs:{c.id}:budget"),
        ],
        [
            InlineKeyboardButton(
                text="⚙️ ترجیحات", callback_data=f"cpref:{c.id}"),
            InlineKeyboardButton(
                text="👤 مسئول مشتری",
                callback_data=f"cs:{c.id}:owner"),
        ],
        [
            InlineKeyboardButton(
                text="🎯 فایل‌های مناسب",
                callback_data=f"mf:{c.id}:1:0"),
            InlineKeyboardButton(
                text="📞 فعالیت‌ها", callback_data=f"cact:{c.id}:1"),
        ],
        [
            InlineKeyboardButton(
                text="✅ عادی کردن" if c.is_urgent else "🚨 فوری کردن",
                callback_data=f"urg:c:{c.id}"),
            InlineKeyboardButton(
                text="🌐 عمومی کردن"
                if ownership_text(c) == "👤 شخصی"
                else "👤 شخصی کردن",
                callback_data=f"own:c:{c.id}"),
        ],
    ]
    if c.is_urgent and not c.follow_up_user_id:
        rows.append([InlineKeyboardButton(
            text="📌 من پیگیری می‌کنم",
            callback_data=f"claim:c:{c.id}")])
    rows.append([
        InlineKeyboardButton(
            text="✏️ اصلاح اطلاعات",
            callback_data=f"clientedit:{c.id}"),
        InlineKeyboardButton(
            text="🔄 تغییر وضعیت",
            callback_data=f"clientstatus:{c.id}"),
    ])
    rows.append([InlineKeyboardButton(
        text="🗑 حذف مشتری", callback_data=f"deleteclient:{c.id}")])
    await show(
        target, "\n".join(lines),
        InlineKeyboardMarkup(inline_keyboard=rows), edit=edit
    )


def floor_pref_text(c):
    if (c.floor_pref or PREF_ANY) == PREF_ANY:
        return "مهم نیست"
    lo, hi = c.floor_min, c.floor_max
    if lo == LAST_FLOOR_SENTINEL:
        return "آخرین طبقه"
    if lo is None and hi is None:
        return "بازه تعیین نشده"
    if lo == hi:
        return f"طبقه {lo}"
    return f"طبقه {lo} تا {hi}"


@dp.callback_query(F.data.startswith("cs:"))
async def client_section(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, cid, sec = callback.data.split(":")
    async with SessionLocal() as session:
        c = await load_obj(session, "c", int(cid))
        if not c:
            await callback.answer("پیدا نشد", show_alert=True)
            return
        names = await user_name_map(
            session, [c.owner_user_id, c.follow_up_user_id]
        )
    if sec == "info":
        text = (
            f"📋 {c.name}\n\n"
            f"📞 تلفن: {c.phone or '—'}\n"
            f"📍 منطقه: {c.area}\n"
            f"📐 متراژ: {money(c.min_sqm)} تا {money(c.max_sqm)}\n"
            f"🏢 نوع ملک: {c.property_type}\n"
            f"📝 {c.description or '—'}"
        )
    elif sec == "budget":
        text = (
            f"💰 بودجه {c.name} — {env_title(c.deal_type)}\n\n"
            f"{client_budget_text(c)}"
        )
    else:
        text = (
            f"👤 مسئول {c.name}\n\n"
            f"مسئول مشتری: {names.get(c.owner_user_id, '—')}\n"
            f"نوع مالکیت: {ownership_text(c)}\n"
            f"مسئول پیگیری: {names.get(c.follow_up_user_id, '—')}"
        )
    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="⬅️ بازگشت به مشتری",
                callback_data=f"copen:{c.id}")
        ]])
    )
    await callback.answer()


async def send_client_prefs(target, client_id, edit=False):
    async with SessionLocal() as session:
        c = await load_obj(session, "c", client_id)
    if not c:
        await target.answer("مشتری پیدا نشد.")
        return
    rows = [
        [InlineKeyboardButton(
            text=f"🛗 آسانسور: {pref_icon(c.elevator_pref)} "
                 f"{c.elevator_pref}",
            callback_data=f"cpc:{c.id}:e")],
        [InlineKeyboardButton(
            text=f"🚗 پارکینگ: {pref_icon(c.parking_pref)} "
                 f"{c.parking_pref}",
            callback_data=f"cpc:{c.id}:p")],
        [InlineKeyboardButton(
            text=f"📦 انباری: {pref_icon(c.storage_pref)} "
                 f"{c.storage_pref}",
            callback_data=f"cpc:{c.id}:s")],
        [InlineKeyboardButton(
            text=f"🏢 طبقه: {pref_icon(c.floor_pref)} "
                 f"{floor_pref_text(c)}",
            callback_data=f"cpc:{c.id}:f")],
        [InlineKeyboardButton(
            text="✏️ تعیین طبقه / بازه",
            callback_data=f"cfl:{c.id}")],
    ]
    if RENT_ENABLED and c.deal_type == ENV_RENT:
        rows.append([InlineKeyboardButton(
            text="💵 سقف رهن و اجاره", callback_data=f"crb:{c.id}")])
    rows.append([InlineKeyboardButton(
        text="⬅️ بازگشت به مشتری", callback_data=f"copen:{c.id}")])
    await show(
        target,
        f"⚙️ ترجیحات {c.name}\n\n"
        f"🔴 الزامی | 🟡 ترجیحی | ⚪ مهم نیست\n"
        f"با لمس هر مورد حالت عوض می‌شود.",
        InlineKeyboardMarkup(inline_keyboard=rows), edit=edit
    )


@dp.callback_query(F.data.startswith("cpref:"))
async def client_prefs_open(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    await send_client_prefs(
        callback.message, int(callback.data.split(":")[1])
    )
    await callback.answer()


PREF_FIELDS = {
    "e": "elevator_pref",
    "p": "parking_pref",
    "s": "storage_pref",
    "f": "floor_pref",
}


@dp.callback_query(F.data.startswith("cpc:"))
async def client_pref_cycle(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, cid, key = callback.data.split(":")
    field = PREF_FIELDS.get(key)
    if not field:
        await callback.answer("نامعتبر", show_alert=True)
        return
    async with SessionLocal() as session:
        c = await load_obj(session, "c", int(cid))
        if not c:
            await callback.answer("پیدا نشد", show_alert=True)
            return
        current = getattr(c, field) or PREF_ANY
        idx = PREF_CYCLE.index(current) if current in PREF_CYCLE else 2
        new_value = PREF_CYCLE[(idx + 1) % len(PREF_CYCLE)]
        setattr(c, field, new_value)
        if field == "floor_pref" and new_value == PREF_ANY:
            c.floor_min = None
            c.floor_max = None
        await session.commit()
    await send_client_prefs(callback.message, int(cid), edit=True)
    await callback.answer()


FLOOR_WORDS = {
    "زیرزمین": -1,
    "همکف": 0,
}


def parse_floor_range(text):
    t = normalize_digits(text or "").strip()
    if t in ("مهم نیست", "مهم نیست."):
        return "any", None, None
    if "آخرین" in t:
        return "ok", LAST_FLOOR_SENTINEL, LAST_FLOOR_SENTINEL
    for sep in ("تا", "-", "–", "،", ","):
        if sep in t:
            left, right = [x.strip() for x in t.split(sep, 1)]
            a = FLOOR_WORDS.get(left)
            b = FLOOR_WORDS.get(right)
            try:
                a = a if a is not None else int(left)
                b = b if b is not None else int(right)
            except Exception:
                return "bad", None, None
            return "ok", min(a, b), max(a, b)
    if t in FLOOR_WORDS:
        return "ok", FLOOR_WORDS[t], FLOOR_WORDS[t]
    try:
        n = int(t)
        return "ok", n, n
    except Exception:
        return "bad", None, None


@dp.callback_query(F.data.startswith("cfl:"))
async def client_floor_start(callback: CallbackQuery, state: FSMContext):
    if not await callback_access_required(callback):
        return
    await state.clear()
    await state.update_data(client_id=int(callback.data.split(":")[1]))
    await state.set_state(FloorRangeForm.value)
    await callback.message.answer(
        "🏢 طبقه را بنویس:\n"
        "مثال: 3 ، 2 تا 4 ، همکف ، زیرزمین ، آخرین طبقه ، مهم نیست"
    )
    await callback.answer()


@dp.message(FloorRangeForm.value)
async def client_floor_save(message: Message, state: FSMContext):
    kind, lo, hi = parse_floor_range(message.text)
    if kind == "bad":
        await message.answer("نامعتبر. مثال: 2 تا 4 یا همکف یا مهم نیست")
        return
    data = await state.get_data()
    cid = data.get("client_id")
    async with SessionLocal() as session:
        c = await load_obj(session, "c", cid)
        if not c:
            await state.clear()
            await message.answer("مشتری پیدا نشد.")
            return
        if kind == "any":
            c.floor_pref = PREF_ANY
            c.floor_min = None
            c.floor_max = None
        else:
            c.floor_min = lo
            c.floor_max = hi
            if (c.floor_pref or PREF_ANY) == PREF_ANY:
                c.floor_pref = PREF_PREFERRED
        await session.commit()
    await state.clear()
    await message.answer(
        "✅ ثبت شد.", reply_markup=env_main_menu(message.from_user.id)
    )
    await send_client_prefs(message, cid)


@dp.callback_query(F.data.startswith("crb:"))
async def client_rent_budget_start(
    callback: CallbackQuery, state: FSMContext
):
    if not await callback_access_required(callback):
        return
    if not RENT_ENABLED:
        await callback.answer(
            "بخش اجاره فعلاً غیرفعال است.", show_alert=True)
        return
    await state.clear()
    await state.update_data(client_id=int(callback.data.split(":")[1]))
    await state.set_state(RentBudgetForm.deposit)
    await callback.message.answer(
        "💵 سقف رهن را بنویس (برای بدون محدودیت 0):"
    )
    await callback.answer()


@dp.message(RentBudgetForm.deposit)
async def client_rent_budget_deposit(message: Message, state: FSMContext):
    value = number(message.text, None)
    if value is None or value < 0:
        await message.answer("عدد معتبر وارد کن.")
        return
    await state.update_data(max_deposit=value)
    await state.set_state(RentBudgetForm.rent)
    await message.answer("💵 سقف اجاره ماهانه را بنویس (یا 0):")


@dp.message(RentBudgetForm.rent)
async def client_rent_budget_rent(message: Message, state: FSMContext):
    value = number(message.text, None)
    if value is None or value < 0:
        await message.answer("عدد معتبر وارد کن.")
        return
    data = await state.get_data()
    cid = data.get("client_id")
    async with SessionLocal() as session:
        await session.execute(
            sa_update(Client)
            .where(Client.id == cid)
            .values(
                max_deposit=data.get("max_deposit", 0),
                max_rent=value,
            )
        )
        await session.commit()
    await state.clear()
    await message.answer(
        "✅ ثبت شد.", reply_markup=env_main_menu(message.from_user.id)
    )
    await send_client_prefs(message, cid)


# =========================================================
# MATCHING ENGINE (pure functions)
# =========================================================

W_BUDGET = 30
W_AREA = 20
W_SQM = 20
W_TYPE = 10
W_ELEVATOR = 7
W_PARKING = 7
W_STORAGE = 3
W_FLOOR = 3


def _has_feature(value):
    return str(value or "").strip() == "دارد"


def _limit_fit(value, limit):
    """1 = within limit, 0.5 = up to 10% above, 0 = more."""
    value = value or 0
    if limit is None or limit <= 0:
        return 1.0
    if value <= limit:
        return 1.0
    if (value - limit) / limit <= 0.10:
        return 0.5
    return 0.0


def property_floor_value(p):
    label = (p.floor_label or "").strip()
    if label == "زیرزمین":
        return -1
    if label == "همکف":
        return 0
    return p.unit_floor or 0


def property_is_last_floor(p):
    if (p.floor_label or "").strip() == "آخرین طبقه":
        return True
    return bool(p.floors) and p.unit_floor == p.floors


def match_score(client, prop):
    """
    Returns None if deal types differ, else a dict:
      score (0-100), eligible (no missing REQUIRED feature),
      reasons (list of short strings), missing (list of names).
    "مهم نیست" features are excluded from the maximum score,
    so they can never reduce it.
    """
    if (client.deal_type or ENV_SALE) != (prop.deal_type or ENV_SALE):
        return None

    earned = 0.0
    possible = 0.0
    reasons = []
    missing = []

    # ---- budget ----
    if (prop.deal_type or ENV_SALE) == ENV_RENT:
        dep_lim = client.max_deposit or 0
        rent_lim = client.max_rent or 0
        if dep_lim <= 0 and rent_lim <= 0:
            reasons.append("⚪ بودجه مشخص نشده")
        else:
            possible += W_BUDGET
            fit = (
                _limit_fit(prop.deposit, dep_lim)
                + _limit_fit(prop.rent, rent_lim)
            ) / 2
            earned += W_BUDGET * fit
            if fit == 1:
                reasons.append("✅ بودجه")
            elif fit > 0:
                reasons.append("⚠️ بودجه کمی بالاتر")
            else:
                reasons.append("❌ بودجه")
    else:
        bmax = client.max_budget or 0
        bmin = client.min_budget or 0
        if bmax <= 0 and bmin <= 0:
            reasons.append("⚪ بودجه مشخص نشده")
        else:
            possible += W_BUDGET
            price = prop.price or 0
            fit = _limit_fit(price, bmax)
            if fit == 1 and bmin > 0 and price < bmin:
                earned += W_BUDGET * 0.75
                reasons.append("⚠️ قیمت کمتر از حداقل بودجه")
            else:
                earned += W_BUDGET * fit
                if fit == 1:
                    reasons.append("✅ بودجه")
                elif fit > 0:
                    reasons.append("⚠️ تا ۱۰٪ بالاتر از سقف بودجه")
                else:
                    reasons.append("❌ بودجه")

    # ---- area ----
    if not client.area or client.area == ALL_AREAS:
        reasons.append("⚪ منطقه مهم نیست")
    else:
        possible += W_AREA
        if client.area == prop.area:
            earned += W_AREA
            reasons.append("✅ منطقه")
        else:
            reasons.append("❌ منطقه")

    # ---- area size ----
    lo = client.min_sqm or 0
    hi = client.max_sqm or 0
    if lo <= 0 and hi <= 0:
        reasons.append("⚪ متراژ مهم نیست")
    else:
        possible += W_SQM
        sqm = prop.sqm or 0
        upper = hi if hi > 0 else float("inf")
        if lo <= sqm <= upper:
            earned += W_SQM
            reasons.append("✅ متراژ")
        else:
            ref = hi if (hi > 0 and sqm > hi) else lo
            if ref > 0 and abs(sqm - ref) / ref <= 0.10:
                earned += W_SQM * 0.5
                reasons.append("⚠️ متراژ نزدیک")
            else:
                reasons.append("❌ متراژ")

    # ---- property type ----
    if not client.property_type or client.property_type == "سایر":
        reasons.append("⚪ نوع ملک مهم نیست")
    else:
        possible += W_TYPE
        if client.property_type == prop.property_type:
            earned += W_TYPE
            reasons.append("✅ نوع ملک")
        else:
            reasons.append("❌ نوع ملک")

    # ---- three-state features ----
    def feature(label, pref, has, weight):
        nonlocal earned, possible
        pref = pref or PREF_ANY
        if pref == PREF_ANY:
            reasons.append(f"⚪ {label} مهم نیست")
            return
        possible += weight
        if has:
            earned += weight
            reasons.append(f"✅ {label}")
        elif pref == PREF_REQUIRED:
            missing.append(label)
            reasons.append(f"🔴 {label} الزامی بود ولی فایل ندارد")
        else:
            reasons.append(
                f"⚠️ {label} ترجیحی بود ولی فایل ندارد"
            )

    feature(
        "آسانسور", client.elevator_pref,
        _has_feature(prop.elevator), W_ELEVATOR
    )
    feature(
        "پارکینگ", client.parking_pref,
        _has_feature(prop.parking), W_PARKING
    )
    feature(
        "انباری", client.storage_pref,
        _has_feature(prop.storage), W_STORAGE
    )

    # ---- floor ----
    fpref = client.floor_pref or PREF_ANY
    fmin, fmax = client.floor_min, client.floor_max
    if fpref == PREF_ANY or (fmin is None and fmax is None):
        reasons.append("⚪ طبقه مهم نیست")
    else:
        if fmin == LAST_FLOOR_SENTINEL:
            ok = property_is_last_floor(prop)
        else:
            val = property_floor_value(prop)
            ok = (
                (fmin is None or val >= fmin)
                and (fmax is None or val <= fmax)
            )
        feature("طبقه", fpref, ok, W_FLOOR)

    score = round(100 * earned / possible) if possible > 0 else 0
    return {
        "score": score,
        "eligible": not missing,
        "reasons": reasons,
        "missing": missing,
    }


# =========================================================
# MATCHING UI (both directions, paginated, with reasons)
# =========================================================

def short_reasons(reasons):
    return " | ".join(reasons)


async def send_match_page(
    target, direction, ref_id, page, tg_user, weak, edit=False
):
    """
    direction 'f': client -> files   (mf:{client}:{page}:{weak})
    direction 'c': file   -> clients (mc:{file}:{page}:{weak})
    weak=1 shows candidates missing a REQUIRED feature.
    """
    tg_id = tg_user.id
    async with SessionLocal() as session:
        user = await get_user(session, tg_id, tg_user.full_name)
        scored = []
        if direction == "f":
            client = await load_obj(session, "c", ref_id)
            if not client:
                await target.answer("مشتری پیدا نشد.")
                return
            conds = [
                Property.deal_type == (client.deal_type or ENV_SALE),
                active_property_filter(),
            ]
            vis = vis_filter(Property, user, tg_id)
            if vis is not None:
                conds.append(vis)
            candidates = (await session.execute(
                select(Property).where(*conds)
            )).scalars().all()
            visited = set((await session.execute(
                select(Visit.property_id).where(
                    Visit.client_id == client.id)
            )).scalars().all())
            for p in candidates:
                m = match_score(client, p)
                if m:
                    scored.append((m, p, p.id in visited))
            head = f"🎯 فایل‌های مناسب {client.name}"
        else:
            prop = await load_obj(session, "p", ref_id)
            if not prop:
                await target.answer("فایل پیدا نشد.")
                return
            conds = [
                Client.deal_type == (prop.deal_type or ENV_SALE),
                active_client_filter(),
            ]
            vis = vis_filter(Client, user, tg_id)
            if vis is not None:
                conds.append(vis)
            candidates = (await session.execute(
                select(Client).where(*conds)
            )).scalars().all()
            visited = set((await session.execute(
                select(Visit.client_id).where(
                    Visit.property_id == prop.id)
            )).scalars().all())
            for c in candidates:
                m = match_score(c, prop)
                if m:
                    scored.append((m, c, c.id in visited))
            head = f"🎯 مشتری‌های مناسب فایل {prop.code}"

    main_list = [
        x for x in scored
        if x[0]["eligible"] and x[0]["score"] >= MATCH_MIN_SCORE
    ]
    weak_list = [
        x for x in scored
        if not x[0]["eligible"] and x[0]["score"] >= MATCH_MIN_SCORE
    ]
    chosen = weak_list if weak else main_list
    chosen.sort(key=lambda x: x[0]["score"], reverse=True)

    total = len(chosen)
    total_pages = max(1, (total + MATCH_PAGE_SIZE - 1) // MATCH_PAGE_SIZE)
    page = max(1, min(page, total_pages))
    part = chosen[(page - 1) * MATCH_PAGE_SIZE: page * MATCH_PAGE_SIZE]

    title = head + (" — ⚠️ ناقص (الزامی را ندارند)" if weak else "")
    lines = [title, f"صفحه {page} از {total_pages} — {total} مورد", ""]
    if not part:
        lines.append("موردی پیدا نشد.")
    rows = []
    for i, (m, obj, was_visited) in enumerate(part, start=1):
        if direction == "f":
            name = f"{obj.code} | {obj.area} | {prop_price_text(obj)}"
            open_cb = f"popen:{obj.id}"
        else:
            name = f"{obj.name} | {obj.area}"
            open_cb = f"copen:{obj.id}"
        seen = " 👀" if was_visited else ""
        lines.append(f"{i}) {name} — {m['score']}٪{seen}")
        lines.append(short_reasons(m["reasons"]))
        lines.append("")
        rows.append([InlineKeyboardButton(
            text=f"{i}) {name}"[:60], callback_data=open_cb
        )])

    prefix = "mf" if direction == "f" else "mc"
    flag = 1 if weak else 0
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(
            text="‹ قبلی",
            callback_data=f"{prefix}:{ref_id}:{page - 1}:{flag}"))
    nav.append(InlineKeyboardButton(
        text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(
            text="بعدی ›",
            callback_data=f"{prefix}:{ref_id}:{page + 1}:{flag}"))
    rows.append(nav)
    if weak:
        rows.append([InlineKeyboardButton(
            text="⬅️ پیشنهادهای اصلی",
            callback_data=f"{prefix}:{ref_id}:1:0")])
    elif weak_list:
        rows.append([InlineKeyboardButton(
            text=f"⚠️ نزدیک ولی ناقص ({len(weak_list)})",
            callback_data=f"{prefix}:{ref_id}:1:1")])
    rows.append([InlineKeyboardButton(
        text="⬅️ بازگشت",
        callback_data=(
            f"copen:{ref_id}" if direction == "f"
            else f"popen:{ref_id}"
        )
    )])
    await show(
        target, "\n".join(lines),
        InlineKeyboardMarkup(inline_keyboard=rows), edit=edit
    )


@dp.callback_query(F.data.startswith("mf:"))
async def match_files_for_client(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, ref, page, weak = callback.data.split(":")
    await send_match_page(
        callback.message, "f", int(ref), int(page),
        callback.from_user, weak == "1",
        edit=(callback.message.text or "").startswith("🎯")
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("mc:"))
async def match_clients_for_file(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, ref, page, weak = callback.data.split(":")
    await send_match_page(
        callback.message, "c", int(ref), int(page),
        callback.from_user, weak == "1",
        edit=(callback.message.text or "").startswith("🎯")
    )
    await callback.answer()


# ---------------- suggestions section ----------------

@dp.message(F.text.in_({"🎯 پیشنهاد به مشتری", "🎯 پیشنهادها"}))
async def suggestions_menu(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    if not await require_env(message):
        return
    await state.clear()
    await message.answer(
        f"🎯 پیشنهاد به مشتری{_env_suffix(message.from_user.id)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🏠 فایل مناسب مشتری", callback_data="sg:c:1")],
            [InlineKeyboardButton(
                text="👤 مشتری مناسب فایل", callback_data="sg:p:1")],
        ])
    )


@dp.callback_query(F.data.startswith("sg:"))
async def suggestion_picker(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    _, kind, page = callback.data.split(":")
    page = int(page)
    tg = callback.from_user
    env = current_env(tg.id)
    model = Client if kind == "c" else Property
    async with SessionLocal() as session:
        user = await get_user(session, tg.id, tg.full_name)
        conds = [
            model.deal_type == env,
            active_client_filter() if kind == "c"
            else active_property_filter(),
        ]
        vis = vis_filter(model, user, tg.id)
        if vis is not None:
            conds.append(vis)
        total = await session.scalar(
            select(func.count(model.id)).where(*conds)
        ) or 0
        total_pages = max(
            1, (total + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE
        )
        page = max(1, min(page, total_pages))
        items = (await session.execute(
            select(model).where(*conds)
            .order_by(model.is_urgent.desc(), model.id.desc())
            .limit(LIST_PAGE_SIZE)
            .offset((page - 1) * LIST_PAGE_SIZE)
        )).scalars().all()
    rows = []
    for obj in items:
        flag = "🚨 " if obj.is_urgent else ""
        if kind == "c":
            label = f"{flag}{obj.name} | {obj.area}"
            cb = f"mf:{obj.id}:1:0"
        else:
            label = f"{flag}{obj.code} | {obj.area} | {money(obj.sqm)}م"
            cb = f"mc:{obj.id}:1:0"
        rows.append([InlineKeyboardButton(
            text=label[:60], callback_data=cb)])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(
            text="‹ قبلی", callback_data=f"sg:{kind}:{page - 1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(
            text="بعدی ›", callback_data=f"sg:{kind}:{page + 1}"))
    rows.append(nav)
    title = (
        "👤 مشتری را انتخاب کن:" if kind == "c"
        else "🏠 فایل را انتخاب کن:"
    )
    await show(
        callback.message,
        f"{title}\nصفحه {page} از {total_pages}",
        InlineKeyboardMarkup(inline_keyboard=rows), edit=True
    )
    await callback.answer()


# =========================================================
# URGENT SECTION
# =========================================================

@dp.message(F.text == "🚨 فوری")
async def urgent_menu(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    if not await require_env(message):
        return
    await state.clear()
    env = current_env(message.from_user.id)
    async with SessionLocal() as session:
        user = await get_user(
            session, message.from_user.id, message.from_user.full_name
        )
        counts = {}
        for kind, model in (("p", Property), ("c", Client)):
            conds = [model.deal_type == env, model.is_urgent == 1]
            conds.append(
                active_property_filter() if kind == "p"
                else active_client_filter()
            )
            vis = vis_filter(model, user, message.from_user.id)
            if vis is not None:
                conds.append(vis)
            counts[kind] = await session.scalar(
                select(func.count(model.id)).where(*conds)
            ) or 0
    await message.answer(
        f"🚨 فوری — {env_title(env)}\n\n"
        f"فایل‌های فوری: {counts['p']}\n"
        f"مشتری‌های فوری: {counts['c']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🏠 فایل‌های فوری", callback_data="L:p:u:1")],
            [InlineKeyboardButton(
                text="👤 مشتری‌های فوری", callback_data="L:c:u:1")],
        ])
    )


# =========================================================
# ACTIVITIES: SUMMARY -> DETAILS (paginated, filtered)
# =========================================================

PERIODS = {
    "t": ("امروز", 0),
    "w": ("۷ روز اخیر", 7),
    "m": ("۳۰ روز اخیر", 30),
}
PERIOD_ORDER = ["t", "w", "m"]


def period_start(period):
    start = day_start_utc()
    days = PERIODS[period][1]
    return start - timedelta(days=days)


def activity_base(select_stmt, env):
    return (
        select_stmt
        .select_from(Activity)
        .outerjoin(User, User.id == Activity.user_id)
        .outerjoin(Property, Property.id == Activity.property_id)
        .outerjoin(Client, Client.id == Activity.client_id)
    )


def activity_env_cond(env):
    return or_(
        Property.deal_type == env,
        Client.deal_type == env,
        and_(Property.id.is_(None), Client.id.is_(None)),
    )


@dp.message(F.text == "📊 فعالیت‌ها")
async def activities_home(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    if not await require_env(message):
        return
    await state.clear()
    env = current_env(message.from_user.id)
    start = day_start_utc()
    async with SessionLocal() as session:
        result = await session.execute(
            activity_base(
                select(User.name, func.count(Activity.id)), env
            )
            .where(Activity.created_at >= start, activity_env_cond(env))
            .group_by(User.name)
            .order_by(func.count(Activity.id).desc())
        )
        rows_data = result.all()
    total = sum(r[1] for r in rows_data)
    lines = [f"📊 فعالیت امروز — {env_title(env)}", ""]
    if not rows_data:
        lines.append("امروز فعالیتی ثبت نشده.")
    for name, count in rows_data:
        lines.append(f"{name or 'نامشخص'}: {count}")
    lines += ["", f"مجموع: {total}"]

    menu_rows = [
        ["👀 ثبت بازدید", "📞 پیگیری"],
        ["📊 KPI من"],
    ]
    if is_admin(message.from_user.id):
        menu_rows[1].append("👥 KPI تیم")
        menu_rows.append(["📝 آخرین فعالیت‌ها"])
    menu_rows.append(["⬅️ بازگشت"])
    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="جزئیات", callback_data="ad:t:0:1")
        ]])
    )
    await message.answer(
        "ابزارهای فعالیت 👇",
        reply_markup=keyboard(menu_rows, include_cancel=False)
    )


@dp.message(F.text == "📝 آخرین فعالیت‌ها")
async def latest_activities_v2(message: Message):
    if not await access_required(message):
        return
    if not is_admin(message.from_user.id):
        await message.answer("⛔ این بخش فقط برای مدیر سیستم است.")
        return
    if message.from_user.id not in USER_ENV:
        USER_ENV[message.from_user.id] = ENV_SALE
    await send_activity_details(
        message, "w", 0, 1, message.from_user.id
    )


async def activity_types():
    async with SessionLocal() as session:
        result = await session.execute(
            select(Activity.activity_type).distinct()
        )
        return sorted({r[0] for r in result.all() if r[0]})


async def send_activity_details(
    target, period, type_idx, page, tg_id, edit=False
):
    env = current_env(tg_id)
    types = await activity_types()
    type_name = types[type_idx - 1] if 0 < type_idx <= len(types) else None
    start = period_start(period)
    conds = [Activity.created_at >= start, activity_env_cond(env)]
    if type_name:
        conds.append(Activity.activity_type == type_name)

    async with SessionLocal() as session:
        total = await session.scalar(
            activity_base(select(func.count(Activity.id)), env)
            .where(*conds)
        ) or 0
        total_pages = max(
            1, (total + ACTIVITY_PAGE_SIZE - 1) // ACTIVITY_PAGE_SIZE
        )
        page = max(1, min(page, total_pages))
        result = await session.execute(
            activity_base(select(Activity, User.name), env)
            .where(*conds)
            .order_by(Activity.created_at.desc())
            .limit(ACTIVITY_PAGE_SIZE)
            .offset((page - 1) * ACTIVITY_PAGE_SIZE)
        )
        rows_data = result.all()

    lines = [
        f"📊 جزئیات فعالیت — {env_title(env)}",
        f"بازه: {PERIODS[period][0]} | نوع: {type_name or 'همه'}",
        f"صفحه {page} از {total_pages} — {total} مورد",
        "",
    ]
    if not rows_data:
        lines.append("فعالیتی پیدا نشد.")
    for act, uname in rows_data:
        note = (act.note or "")[:40]
        lines.append(
            f"{tehran_time(act.created_at)} | {uname or '—'} | "
            f"{act.activity_type}"
            f"{(' | ' + note) if note else ''}"
        )

    next_period = PERIOD_ORDER[
        (PERIOD_ORDER.index(period) + 1) % len(PERIOD_ORDER)
    ]
    next_type = (type_idx + 1) % (len(types) + 1)
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(
            text="‹ قبلی",
            callback_data=f"ad:{period}:{type_idx}:{page - 1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(
            text="بعدی ›",
            callback_data=f"ad:{period}:{type_idx}:{page + 1}"))
    rows = [
        nav,
        [
            InlineKeyboardButton(
                text=f"🗓 بازه: {PERIODS[next_period][0]} ←",
                callback_data=f"ad:{next_period}:{type_idx}:1"),
            InlineKeyboardButton(
                text="🏷 نوع بعدی",
                callback_data=f"ad:{period}:{next_type}:1"),
        ],
    ]
    await show(
        target, "\n".join(lines),
        InlineKeyboardMarkup(inline_keyboard=rows), edit=edit
    )


@dp.callback_query(F.data.startswith("ad:"))
async def activity_details_callback(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    try:
        _, period, type_idx, page = callback.data.split(":")
        if period not in PERIODS:
            raise ValueError
        await send_activity_details(
            callback.message, period, int(type_idx), int(page),
            callback.from_user.id,
            edit=(callback.message.text or "").startswith("📊 جزئیات")
        )
    except Exception as exc:
        print("ACTIVITY DETAIL ERROR:", exc)
        await callback.answer("خطا", show_alert=True)
        return
    await callback.answer()


# =========================================================
# ADMIN: advisor permissions   /perm <telegram_id> sale|rent on|off
# =========================================================

@dp.message(Command("perm"))
async def perm_command(message: Message):
    if not await access_required(message):
        return
    if not is_admin(message.from_user.id):
        await message.answer("⛔ فقط مدیر.")
        return
    parts = (message.text or "").split()
    if (
        len(parts) != 4
        or parts[2] not in ("sale", "rent")
        or parts[3] not in ("on", "off")
    ):
        await message.answer(
            "فرمت: /perm <آیدی تلگرام> sale|rent on|off"
        )
        return
    try:
        target_id = int(normalize_digits(parts[1]))
    except Exception:
        await message.answer("آیدی نامعتبر است.")
        return
    column = "can_sale" if parts[2] == "sale" else "can_rent"
    async with SessionLocal() as session:
        user = (await session.execute(
            select(User).where(User.telegram_id == target_id)
        )).scalar_one_or_none()
        if not user:
            await message.answer(
                "این کاربر هنوز /start نزده است."
            )
            return
        setattr(user, column, 1 if parts[3] == "on" else 0)
        await session.commit()
    await message.answer("✅ ثبت شد.")


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
        f"💰 قیمت: {price_label(data.get('price'))}\n"
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
            deal_type=current_env(message.from_user.id),
            created_by=message.from_user.id,
            updated_at=utcnow_naive()
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

        await ensure_ad_row(session, prop.id)

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
    await post_create_prompt(message, "p", prop.id)


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
        budget = budget_label(client.min_budget, client.max_budget)
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

async def send_property_detail_legacy(
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
            f"💰 قیمت: {price_label(prop.price)}\n"
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
            f"{price_label(prop.transaction_value)}\n"
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
        ),
        InlineKeyboardButton(
            text="🎬 ویدئوهای فایل",
            callback_data=f"vp:{prop_id}"
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

            prop.updated_at = utcnow_naive()

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

            prop.updated_at = utcnow_naive()

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

        await session.execute(
            sa_delete(PropertyVideo).where(
                PropertyVideo.property_id == prop.id
            )
        )
        await session.execute(
            sa_delete(PropertyAd).where(
                PropertyAd.property_id == prop.id
            )
        )

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
        prop.updated_at = utcnow_naive()

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

        await log_status_event(
            session, prop.id, user.id, old_status, message.text
        )

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
        prop.updated_at = utcnow_naive()

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

        await log_status_event(
            session, prop.id, user.id, old_status, SOLD_BY_US, value
        )

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
            deal_type=current_env(message.from_user.id),
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
    await post_create_prompt(message, "c", client.id)


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

        budget = budget_label(c.min_budget, c.max_budget)

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

async def send_client_detail_legacy(
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
        f"{budget_label(client.min_budget, client.max_budget)}\n"
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

            if not client or not prop or (
                not RENT_ENABLED
                and (client.deal_type == ENV_RENT or prop.deal_type == ENV_RENT)
            ):
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
            f"💰 {price_label(prop.price)}\n"
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
# STAGE 10: AI CLIENT, VIDEO, ADS, DASHBOARD, REMINDERS
# (additive block - nothing above this line was removed)
# =========================================================

import base64
import io
from datetime import date as date_cls

from aiogram.types import InputMediaVideo
from sqlalchemy import (
    BigInteger,
    UniqueConstraint,
    delete as sa_delete,
)
from sqlalchemy.exc import IntegrityError


# ---------------------------------------------------------
# Config (env only; the key is never printed or stored)
# ---------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = (
    os.getenv("GEMINI_MODEL", "").strip() or "gemini-flash-latest"
)
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

AI_UNAVAILABLE_TEXT = (
    "🤖 سرویس هوش مصنوعی فعلاً در دسترس نیست.\n"
    "بقیه‌ی امکانات ربات عادی کار می‌کنند؛ "
    "می‌توانی از ثبت متنی، لینک دیوار یا ثبت دستی استفاده کنی."
)

MAX_PROPERTY_VIDEOS = 3
VOICE_MAX_SECONDS = 180
VOICE_MAX_BYTES = 12 * 1024 * 1024

MAYOR_NAME = "شهردار ایران‌زمین"
MAYOR_INTRO = (
    "من شهردار ایران‌زمین هستم؛ دستیار هوشمند تیم املاک ایران‌زمین. "
    "کار من کمک به مشاورها برای مدیریت فایل‌ها، آماده‌سازی آگهی‌های "
    "حرفه‌ای، پیدا کردن فرصت‌های معاملاتی و افزایش شانس بستن "
    "قرارداد است."
)
MAYOR_SYSTEM = (
    f"تو «{MAYOR_NAME}» هستی؛ دستیار هوشمند تیم املاک ایران‌زمین. "
    "حرفه‌ای، دقیق، نتیجه‌محور و دوستانه-کاری هستی و فارسی روان "
    "می‌نویسی. تمرکزت بر جذب مشتری، فایل‌یابی، آگهی‌گذاری، بازدید، "
    "مذاکره و قرارداد است.\n"
    "قوانین سخت:\n"
    "۱) هرگز اطلاعات ملک، مشتری، قیمت، فعالیت یا آمار نساز. فقط از "
    "داده‌ی داده‌شده در همین گفتگو استفاده کن.\n"
    "۲) اگر اطلاعات ناقص است، سؤال بپرس یا بگو داده‌ی کافی نیست.\n"
    "۳) تو در این گفتگو هیچ اقدامی (ثبت، ویرایش، حذف، ارسال پیام، "
    "انتشار آگهی) انجام نمی‌دهی و نباید ادعا کنی انجام داده‌ای؛ "
    "مشاور باید از منوهای ربات استفاده کند.\n"
    "۴) درباره‌ی احتمال فروش یا میزان تقاضا بدون داده‌ی معتبر قطعی "
    "حرف نزن.\n"
    "۵) پاسخ‌ها کوتاه و کاربردی باشند."
)


# ---------------------------------------------------------
# New tables (created by Base.metadata.create_all in migrate();
# no existing table or column is altered)
# ---------------------------------------------------------

class PropertyVideo(Base):
    __tablename__ = "property_videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, index=True)
    file_id: Mapped[str] = mapped_column(String(300))
    file_unique_id: Mapped[str] = mapped_column(String(100), default="")
    duration: Mapped[int] = mapped_column(Integer, default=0)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow_naive
    )


AD_UNADVERTISED = "unadvertised"
AD_ADVERTISED = "advertised"
AD_REVIEW = "review"
AD_UNKNOWN = "unknown"  # virtual: no row exists for the property

AD_STATUS_LABELS = {
    AD_UNADVERTISED: "⬜ آگهی‌نشده",
    AD_ADVERTISED: "✅ آگهی‌شده",
    AD_REVIEW: "🔄 نیازمند بررسی مجدد",
    AD_UNKNOWN: "❔ وضعیت نامشخص",
}


class PropertyAd(Base):
    __tablename__ = "property_ads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default=AD_UNADVERTISED, index=True
    )
    platform: Mapped[str] = mapped_column(String(100), default="")
    published_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )
    title: Mapped[str] = mapped_column(Text, default="")
    text_short: Mapped[str] = mapped_column(Text, default="")
    text_full: Mapped[str] = mapped_column(Text, default="")
    missing_info: Mapped[str] = mapped_column(Text, default="")
    text_source: Mapped[str] = mapped_column(String(20), default="")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )
    marked_by: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow_naive
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow_naive
    )


class StatusEvent(Base):
    """Structured history of file status changes (for reports)."""
    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer, default=0)
    old_status: Mapped[str] = mapped_column(String(100), default="")
    new_status: Mapped[str] = mapped_column(String(100), default="")
    transaction_value: Mapped[float] = mapped_column(Float, default=0)
    source: Mapped[str] = mapped_column(String(20), default="live")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow_naive, index=True
    )


class ReminderLog(Base):
    __tablename__ = "reminder_logs"
    __table_args__ = (
        UniqueConstraint("tg_id", "day", name="uq_reminder_tg_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger)
    day: Mapped[str] = mapped_column(String(10))
    items: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow_naive
    )


SOLD_BY_US = "🔵 معامله شد - توسط ما"
SOLD_BY_OTHER = "🟣 معامله شد - توسط دیگری"
STATUS_DROPPED = "🔴 منصرف شد"
STATUS_NEGOTIATING = "🟡 در مذاکره"


async def log_status_event(
    session, property_id, user_id, old_status, new_status, value=0
):
    """Record a status change. Never lets a logging error break the flow."""
    try:
        session.add(StatusEvent(
            property_id=property_id,
            user_id=user_id or 0,
            old_status=old_status or "",
            new_status=new_status or "",
            transaction_value=float(value or 0),
            source="live",
        ))
        await session.commit()
    except Exception as exc:
        print("STATUS EVENT ERROR:", repr(exc)[:200])
        try:
            await session.rollback()
        except Exception:
            pass


async def ensure_ad_row(session, property_id, status=AD_UNADVERTISED):
    """Create the ad-tracking row for a NEW file (never overwrites)."""
    try:
        exists = await session.scalar(
            select(PropertyAd.id).where(
                PropertyAd.property_id == property_id
            )
        )
        if exists:
            return
        session.add(PropertyAd(property_id=property_id, status=status))
        await session.commit()
    except Exception as exc:
        print("AD ROW ERROR:", repr(exc)[:200])
        try:
            await session.rollback()
        except Exception:
            pass


def _parse_old_new(note):
    if not note or " → " not in note:
        return None
    old, new = note.split(" → ", 1)
    return old.strip(), new.strip()


async def backfill_status_events():
    """One-time import of old status changes from the activity log.

    Runs only when status_events is empty, so it is safe to repeat.
    """
    try:
        async with SessionLocal() as session:
            have = await session.scalar(
                select(func.count(StatusEvent.id))
            )
            if have:
                return
            rows = (await session.execute(
                select(Activity).where(
                    Activity.activity_type.in_(
                        ["تغییر وضعیت فایل", "معامله فایل"]
                    ),
                    Activity.property_id > 0,
                ).order_by(Activity.created_at)
            )).scalars().all()
            added = 0
            for a in rows:
                pair = _parse_old_new(a.note)
                if not pair:
                    continue
                old, new = pair
                value = 0.0
                if a.activity_type == "معامله فایل":
                    new = SOLD_BY_US
                    m = re.search(r"ارزش معامله:\s*([\d,\.]+)", a.note or "")
                    if m:
                        value = number(m.group(1), 0)
                session.add(StatusEvent(
                    property_id=a.property_id,
                    user_id=a.user_id or 0,
                    old_status=old[:100],
                    new_status=new[:100],
                    transaction_value=float(value or 0),
                    source="backfill",
                    created_at=a.created_at,
                ))
                added += 1
            await session.commit()
            print(f"status_events backfill: {added}")
    except Exception as exc:
        print("BACKFILL ERROR:", repr(exc)[:200])


# ---------------------------------------------------------
# Gemini (REST via aiohttp; no new dependency)
# ---------------------------------------------------------

class AIError(Exception):
    def __init__(self, user_message, code="error"):
        super().__init__(code)
        self.user_message = user_message
        self.code = code


def ai_available():
    return bool(GEMINI_API_KEY)


# Transient failures (Gemini 5xx, dropped connection) are retried a limited
# number of times with growing delays. AI_RETRY_DELAYS are the waits before
# the 2nd and 3rd attempt (a little random jitter is added on top), so at
# most 3 attempts are made. Timeouts and 400/401/403 are never retried;
# 429 is retried once.
AI_RETRY_DELAYS = (1.5, 4.0)
AI_RETRYABLE_STATUSES = (500, 502, 503, 504)
AI_RATE_LIMIT_RETRY_DELAY = 3.0


def ai_error_summary(data):
    """One-line, key-free summary of a Gemini error body for the log."""
    err = data.get("error") if isinstance(data, dict) else None
    if not isinstance(err, dict):
        return ""
    text = "{}: {}".format(
        str(err.get("status") or "")[:40],
        " ".join(str(err.get("message") or "").split())[:200],
    )
    if GEMINI_API_KEY:
        text = text.replace(GEMINI_API_KEY, "***")
    return text.strip(": ")


async def _ai_sleep(delay):
    await asyncio.sleep(delay + random.uniform(0, 0.5))


async def _gemini_post(body, headers, timeout):
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=timeout)
    ) as http:
        async with http.post(
            GEMINI_URL, json=body, headers=headers
        ) as resp:
            status = resp.status
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = {}
    return status, data


async def gemini_generate(
    parts, system=None, json_mode=False, temperature=0.2, timeout=60,
    label="ai",
):
    if not GEMINI_API_KEY:
        raise AIError(AI_UNAVAILABLE_TEXT, "no_key")

    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    max_attempts = len(AI_RETRY_DELAYS) + 1
    attempt = 0
    while True:
        attempt += 1
        can_retry = attempt < max_attempts
        try:
            status, data = await _gemini_post(body, headers, timeout)
        except asyncio.TimeoutError:
            print(f"AI TIMEOUT [{label}] attempt {attempt}/{max_attempts}")
            raise AIError(
                "⏱ پاسخ سرویس هوش مصنوعی دیر شد؛ کمی بعد دوباره تلاش کن.",
                "timeout",
            )
        except Exception as exc:
            print(
                f"AI NETWORK ERROR [{label}] "
                f"attempt {attempt}/{max_attempts}:",
                type(exc).__name__,
            )
            if can_retry:
                await _ai_sleep(AI_RETRY_DELAYS[attempt - 1])
                continue
            raise AIError(AI_UNAVAILABLE_TEXT, "network")

        if status == 429:
            print(f"AI ERROR: quota/rate limit (429) [{label}] "
                  f"attempt {attempt}/{max_attempts}")
            if attempt == 1:
                await _ai_sleep(AI_RATE_LIMIT_RETRY_DELAY)
                continue
            raise AIError(
                "🤖 سهمیه‌ی سرویس هوش مصنوعی فعلاً تمام شده؛ "
                "کمی بعد دوباره تلاش کن یا از ثبت متنی استفاده کن.",
                "quota",
            )
        if status in (400, 401, 403):
            print("AI ERROR:", status, f"[{label}]", ai_error_summary(data))
            raise AIError(AI_UNAVAILABLE_TEXT, "auth")
        if status in AI_RETRYABLE_STATUSES and can_retry:
            print(
                f"AI RETRY: http {status} [{label}] "
                f"attempt {attempt}/{max_attempts}",
                ai_error_summary(data),
            )
            await _ai_sleep(AI_RETRY_DELAYS[attempt - 1])
            continue
        if status != 200:
            print(
                f"AI ERROR: http {status} [{label}] "
                f"attempt {attempt}/{max_attempts}",
                ai_error_summary(data),
            )
            raise AIError(AI_UNAVAILABLE_TEXT, "server")
        break

    try:
        cands = data.get("candidates") or []
        parts_out = cands[0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts_out).strip()
    except Exception:
        text = ""
    if not text:
        raise AIError(
            "🤖 پاسخ قابل استفاده‌ای از سرویس هوش مصنوعی نگرفتم.",
            "empty",
        )
    return text


def parse_json_loose(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    a, b = text.find("{"), text.rfind("}")
    if a != -1 and b > a:
        try:
            return json.loads(text[a:b + 1])
        except Exception:
            pass
    return None


# ---------------------------------------------------------
# Voice registration helpers
# ---------------------------------------------------------

VOICE_PROMPT = (
    "این پیام صوتی فارسی یک مشاور املاک است که مشخصات یک فایل ملکی "
    "را می‌گوید. ابتدا گفتار را عیناً به متن فارسی تبدیل کن، سپس "
    "فقط مواردی را که صریحاً گفته شده استخراج کن. هیچ مقداری را حدس "
    "نزن و اگر چیزی گفته نشده آن را در خروجی نیاور.\n"
    "خروجی فقط JSON با این ساختار باشد:\n"
    '{"transcript": "متن کامل گفتار", '
    '"fields": {"<نام فیلد>": {"value": ..., "evidence": '
    '"عین عبارت گفته‌شده از transcript"}}, '
    '"urgent": false, "urgent_evidence": ""}\n'
    "نام فیلدهای مجاز و نوع مقدار:\n"
    "transaction_type: sale یا rent | area: منطقه/محله (متن) | "
    "address: آدرس | property_type: نوع ملک | meterage: عدد متر | "
    "bedrooms: عدد | floor: عدد طبقه | total_floors: عدد کل طبقات | "
    "building_age: عدد سن بنا | parking/elevator/storage: true یا false | "
    "price: قیمت فروش به تومان به‌صورت عدد کامل (مثلاً سه و نیم "
    "میلیارد = 3500000000) | owner_name | owner_phone.\n"
    "قانون evidence: برای هر فیلد، دقیقاً همان کلمات گفته‌شده را که "
    "مقدار از آن‌ها آمده بنویس و آن عبارت باید عیناً داخل transcript "
    "باشد.\n"
    "urgent را فقط وقتی true بگذار که گوینده صریحاً فوریت فروش را "
    "بگوید (مثل «فوری» یا «عجله دارد») و همان عبارت را در "
    "urgent_evidence بیاور."
)


async def ai_voice_extract(audio_bytes, mime="audio/ogg"):
    """Returns (transcript, raw_fields, urgent_hint). Raises AIError."""
    parts = [
        {"inline_data": {
            "mime_type": mime,
            "data": base64.b64encode(audio_bytes).decode("ascii"),
        }},
        {"text": VOICE_PROMPT},
    ]
    text = await gemini_generate(
        parts, json_mode=True, temperature=0.0, timeout=90, label="voice"
    )
    obj = parse_json_loose(text)
    if not isinstance(obj, dict):
        raise AIError(
            "🤖 نتوانستم ویس را درست تحلیل کنم؛ دوباره بفرست یا متنی "
            "ثبت کن.", "parse",
        )
    transcript = str(obj.get("transcript") or "").strip()
    if not transcript:
        raise AIError(
            "🎙 صدای قابل تشخیصی در ویس پیدا نشد؛ واضح‌تر بفرست.",
            "empty",
        )
    raw = {}
    fields = obj.get("fields")
    if isinstance(fields, dict):
        for key in QR_ALL_FIELDS:
            item = fields.get(key)
            if isinstance(item, dict):
                value = item.get("value")
                evidence = str(item.get("evidence") or "")
            else:
                value, evidence = item, ""
            if value in (None, "", [], {}):
                continue
            raw[key] = {"value": value, "evidence": evidence}
    urgent = False
    if obj.get("urgent") is True:
        ev = qr_squash(str(obj.get("urgent_evidence") or ""))
        urgent = bool(ev) and ev in qr_squash(transcript)
    return transcript, raw, urgent


def qr_merge_raw(local_raw, ai_raw):
    """Deterministic local values win; AI only fills the gaps."""
    merged = dict(ai_raw or {})
    for key, val in (local_raw or {}).items():
        merged[key] = val
    return merged


# ---------------------------------------------------------
# VIDEO SUPPORT
# ---------------------------------------------------------

class VideoForm(StatesGroup):
    property_id = State()


async def media_counts(session, property_id):
    photos = await session.scalar(
        select(func.count(PropertyPhoto.id)).where(
            PropertyPhoto.property_id == property_id
        )
    ) or 0
    videos = await session.scalar(
        select(func.count(PropertyVideo.id)).where(
            PropertyVideo.property_id == property_id
        )
    ) or 0
    return photos, videos


async def send_video_manager(target, prop_id):
    async with SessionLocal() as session:
        vids = (await session.execute(
            select(PropertyVideo)
            .where(PropertyVideo.property_id == prop_id)
            .order_by(PropertyVideo.created_at, PropertyVideo.id)
        )).scalars().all()
    rows = []
    for i, v in enumerate(vids, start=1):
        suffix = f" ({v.duration}ث)" if v.duration else ""
        rows.append([InlineKeyboardButton(
            text=f"🗑 حذف ویدئو {i}{suffix}",
            callback_data=f"vdel:{v.id}")])
    if len(vids) < MAX_PROPERTY_VIDEOS:
        rows.append([InlineKeyboardButton(
            text="➕ افزودن ویدئو", callback_data=f"vadd:{prop_id}")])
    rows.append([InlineKeyboardButton(
        text="📸 تصاویر", callback_data=f"pimg:{prop_id}")])
    rows.append([InlineKeyboardButton(
        text="⬅️ بازگشت به فایل", callback_data=f"popen:{prop_id}")])
    await target.answer(
        f"🎬 مدیریت ویدئوها ({len(vids)}/{MAX_PROPERTY_VIDEOS})",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    return len(vids)


@dp.callback_query(F.data.startswith("vp:"))
async def video_panel(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    prop_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        vids = (await session.execute(
            select(PropertyVideo)
            .where(PropertyVideo.property_id == prop_id)
            .order_by(PropertyVideo.created_at, PropertyVideo.id)
        )).scalars().all()
    chat_id = callback.message.chat.id
    try:
        if len(vids) == 1:
            await bot.send_video(chat_id, vids[0].file_id)
        elif len(vids) > 1:
            await bot.send_media_group(
                chat_id,
                [InputMediaVideo(media=v.file_id) for v in vids],
            )
    except Exception as exc:
        print("SEND VIDEOS ERROR:", repr(exc)[:200])
        await callback.message.answer(
            "⚠️ ارسال ویدئوها انجام نشد؛ دوباره تلاش کن."
        )
    await send_video_manager(callback.message, prop_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("vadd:"))
async def video_add_start(callback: CallbackQuery, state: FSMContext):
    if not await callback_access_required(callback):
        return
    prop_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        _, vcount = await media_counts(session, prop_id)
    if vcount >= MAX_PROPERTY_VIDEOS:
        await callback.answer(
            f"حداکثر {MAX_PROPERTY_VIDEOS} ویدئو مجاز است.",
            show_alert=True,
        )
        return
    await state.clear()
    await state.update_data(property_id=prop_id)
    await state.set_state(VideoForm.property_id)
    await callback.message.answer(
        f"🎬 ویدئوی فایل را بفرست ({vcount}/{MAX_PROPERTY_VIDEOS}).\n"
        "آن را به‌صورت «ویدئو» بفرست (نه فایل). "
        "وقتی تمام شد «پایان» را بزن.",
        reply_markup=keyboard([["پایان"]]),
    )
    await callback.answer()


@dp.message(VideoForm.property_id, F.video)
async def video_receive(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    data = await state.get_data()
    prop_id = data.get("property_id")
    if not prop_id:
        await state.clear()
        return
    async with SessionLocal() as session:
        _, vcount = await media_counts(session, prop_id)
        if vcount >= MAX_PROPERTY_VIDEOS:
            await message.answer(
                f"⚠️ حداکثر {MAX_PROPERTY_VIDEOS} ویدئو مجاز است. "
                "«پایان» را بزن."
            )
            return
        vid = message.video
        session.add(PropertyVideo(
            property_id=prop_id,
            file_id=vid.file_id,
            file_unique_id=vid.file_unique_id or "",
            duration=int(vid.duration or 0),
            file_size=int(vid.file_size or 0),
            created_by=message.from_user.id,
        ))
        await session.commit()
        user = await get_user(
            session, message.from_user.id, message.from_user.full_name
        )
        await add_activity(
            session, user.id, "افزودن ویدئو فایل",
            f"ویدئو {vcount + 1}/{MAX_PROPERTY_VIDEOS} اضافه شد.",
            property_id=prop_id,
        )
    await message.answer(
        f"✅ ویدئو ذخیره شد ({vcount + 1}/{MAX_PROPERTY_VIDEOS}). "
        "ویدئوی بعدی را بفرست یا «پایان» را بزن."
    )


@dp.message(VideoForm.property_id, F.text == "پایان")
async def video_add_done(message: Message, state: FSMContext):
    data = await state.get_data()
    prop_id = data.get("property_id")
    await state.clear()
    await message.answer(
        "✅ انجام شد.", reply_markup=main_menu(message.from_user.id)
    )
    if prop_id:
        await send_video_manager(message, prop_id)


@dp.message(VideoForm.property_id)
async def video_add_wrong(message: Message):
    await message.answer(
        "لطفاً یک ویدئو بفرست (به‌صورت ویدئو، نه فایل) یا «پایان» را بزن."
    )


@dp.callback_query(F.data.startswith("vdel:"))
async def video_delete(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return
    vid_id = int(callback.data.split(":")[1])
    async with SessionLocal() as session:
        v = (await session.execute(
            select(PropertyVideo).where(PropertyVideo.id == vid_id)
        )).scalar_one_or_none()
        if not v:
            await callback.answer("پیدا نشد", show_alert=True)
            return
        prop_id = v.property_id
        await session.delete(v)
        await session.commit()
        user = await get_user(
            session, callback.from_user.id, callback.from_user.full_name
        )
        await add_activity(
            session, user.id, "حذف ویدئو فایل", "یک ویدئو حذف شد.",
            property_id=prop_id,
        )
    await callback.answer("🗑 حذف شد")
    await send_video_manager(callback.message, prop_id)


# ---------------------------------------------------------
# 📢 AD SUGGESTIONS
# ---------------------------------------------------------

AD_PAGE_SIZE = 5
AD_STALE_DAYS = 45
AD_FRESH_DAYS = 14
AD_PLATFORMS = ["دیوار", "شیپور", "اینستاگرام", "سایر", "بدون ذکر پلتفرم"]


class AdEditForm(StatesGroup):
    text = State()


def ad_readiness(prop, n_photos, n_videos, now=None):
    """Explainable readiness score (0-100) for advertising a file.

    Uses only real stored fields. It is NOT a sale probability.
    Returns (score, todo_list, ok_list).
    """
    now = now or utcnow_naive()
    score = 0
    todo, ok = [], []

    if (prop.price or 0) > 0:
        score += 25
        ok.append("قیمت ثبت شده")
    else:
        todo.append("قیمت باید از مالک تأیید شود")
    if (prop.area or "").strip():
        score += 10
    else:
        todo.append("منطقه مشخص نیست")
    if (prop.sqm or 0) > 0:
        score += 10
    else:
        todo.append("متراژ مشخص نیست")
    if (prop.property_type or "").strip():
        score += 5
    else:
        todo.append("نوع ملک مشخص نیست")
    if (prop.bedrooms or 0) > 0:
        score += 5
    if (prop.floor_label or "").strip() or (prop.unit_floor or 0) != 0 \
            or (prop.floors or 0) > 0:
        score += 5
    else:
        todo.append("طبقه مشخص نیست")
    if (prop.address or "").strip():
        score += 5
    if len((prop.description or "").strip()) >= 20:
        score += 5

    if n_photos >= 5:
        score += 12
        ok.append(f"{n_photos} عکس")
    elif n_photos >= 3:
        score += 10
        ok.append(f"{n_photos} عکس")
    elif n_photos >= 1:
        score += 5
        todo.append("تعداد عکس کم است")
    else:
        todo.append("عکس ندارد")
    if n_videos > 0:
        score += 8
        ok.append("ویدئو دارد")

    ref = prop.updated_at or prop.created_at
    if ref:
        age = (now - ref).days
        if age <= AD_FRESH_DAYS:
            score += 10
            ok.append("به‌روز است")
        elif age <= AD_STALE_DAYS:
            score += 5
        else:
            todo.append(
                f"{age} روز بدون به‌روزرسانی؛ اعتبار فایل را تأیید کن"
            )
    return min(score, 100), todo, ok


def ad_reason_text(status, todo):
    if status == AD_REVIEW:
        base = "برای بررسی مجدد علامت خورده"
        return base + (("؛ " + "، ".join(todo[:2])) if todo else "")
    if not todo:
        return "اطلاعات کامل است اما هنوز آگهی‌گذاری ثبت نشده"
    return "قبل از آگهی‌گذاری: " + "، ".join(todo[:2])


def ad_missing_list(prop, n_photos):
    """Items the advisor must confirm with the owner (code-computed)."""
    items = []
    if (prop.price or 0) <= 0:
        items.append("قیمت نهایی")
    if not (prop.address or "").strip():
        items.append("آدرس/موقعیت دقیق")
    if not (prop.document_type or "").strip():
        items.append("وضعیت سند")
    for label, value in (
        ("آسانسور", prop.elevator),
        ("پارکینگ", prop.parking),
        ("انباری", prop.storage),
    ):
        if not (value or "").strip():
            items.append(f"وضعیت {label}")
    if not (prop.tenant or "").strip():
        items.append("وضعیت سکونت (خالی/مستأجر/مالک)")
    ref = prop.updated_at or prop.created_at
    if ref and (utcnow_naive() - ref).days > AD_STALE_DAYS:
        items.append("معتبر بودن فایل و قیمت (مدت زیادی به‌روز نشده)")
    if n_photos == 0:
        items.append("عکس ملک")
    return items


_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?98|0)?9\d{9}(?!\d)|(?<!\d)0\d{10}(?!\d)")


def sanitize_description(text):
    t = normalize_digits(text or "")
    t = _URL_RE.sub("", t)
    t = _PHONE_RE.sub("", t)
    t = re.sub(r"🔗", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:400]


def ad_facts(prop):
    """Only real DB values; used for both the AI prompt and the template."""
    f = []
    if (prop.property_type or "").strip():
        f.append(f"نوع ملک: {prop.property_type}")
    if (prop.area or "").strip():
        f.append(f"منطقه: {prop.area}")
    if (prop.sqm or 0) > 0:
        f.append(f"متراژ: {money(prop.sqm)} متر")
    if (prop.bedrooms or 0) > 0:
        f.append(f"تعداد خواب: {prop.bedrooms}")
    floor_info = (prop.floor_label or "").strip()
    if not floor_info and (prop.unit_floor or 0) != 0:
        floor_info = f"طبقه {prop.unit_floor}"
        if (prop.floors or 0) > 0:
            floor_info += f" از {prop.floors}"
    if floor_info:
        f.append(f"طبقه: {floor_info}")
    if prop.building_age is not None:
        f.append(f"سن بنا: {prop.building_age} سال")
    for label, value in (
        ("آسانسور", prop.elevator),
        ("پارکینگ", prop.parking),
        ("انباری", prop.storage),
    ):
        if (value or "").strip():
            f.append(f"{label}: {value}")
    if (prop.document_type or "").strip():
        f.append(f"سند: {prop.document_type}")
    if (prop.price or 0) > 0:
        f.append(f"قیمت: {price_label(prop.price)}")
    desc = sanitize_description(prop.description)
    if desc:
        f.append(f"توضیحات مالک: {desc}")
    return f


def ad_template_text(prop):
    """Deterministic fallback (no AI). Contains only stored facts."""
    bits = [prop.property_type or "ملک"]
    if (prop.sqm or 0) > 0:
        bits.append(f"{money(prop.sqm)} متری")
    if (prop.bedrooms or 0) > 0:
        bits.append(f"{prop.bedrooms} خوابه")
    title = " ".join(bits)
    if (prop.area or "").strip():
        title += f" در {prop.area}"
    facts = ad_facts(prop)
    short = title
    if (prop.price or 0) > 0:
        short += f" | قیمت: {price_label(prop.price)}"
    full = title + "\n\n" + "\n".join(f"• {x}" for x in facts)
    return title, short, full


def _numbers_in(text):
    return set(re.findall(r"\d+", normalize_digits(text or "")))


def ad_text_is_grounded(ad_text, facts):
    """Reject AI text that contains numbers absent from the stored facts."""
    allowed = _numbers_in("\n".join(facts))
    return _numbers_in(ad_text) <= allowed


AD_PROMPT = (
    "برای فایل ملکی زیر یک آگهی حرفه‌ای و روان فارسی بنویس.\n"
    "قوانین سخت: فقط از اطلاعات داده‌شده استفاده کن. هیچ امکانات، "
    "قیمت، موقعیت، شرایط پرداخت، مدت یا ویژگی‌ای که در اطلاعات نیست "
    "اضافه نکن. هیچ عدد جدیدی اضافه نکن. شماره تلفن یا لینک ننویس. "
    "قیمت را دقیقاً با همان قالب داده‌شده بنویس.\n"
    'خروجی فقط JSON: {"title": "عنوان کوتاه", "short": "نسخه کوتاه '
    '(حداکثر ۳ خط)", "full": "نسخه کامل"}\n\nاطلاعات فایل:\n'
)


async def generate_ad_text(prop):
    """Returns (title, short, full, source). source: ai | template."""
    facts = ad_facts(prop)
    if ai_available():
        try:
            text = await gemini_generate(
                [{"text": AD_PROMPT + "\n".join(facts)}],
                system=MAYOR_SYSTEM,
                json_mode=True,
                temperature=0.4,
                timeout=60,
                label="ad",
            )
            obj = parse_json_loose(text)
            if isinstance(obj, dict):
                title = str(obj.get("title") or "").strip()
                short = str(obj.get("short") or "").strip()
                full = str(obj.get("full") or "").strip()
                combined = " ".join([title, short, full])
                if (
                    title and full
                    and ad_text_is_grounded(combined, facts)
                    and not _URL_RE.search(combined)
                    and not _PHONE_RE.search(normalize_digits(combined))
                ):
                    return title, short or title, full, "ai"
                print("AD AI OUTPUT REJECTED (ungrounded)")
        except AIError as exc:
            print("AD AI ERROR:", exc.code)
        except Exception as exc:
            print("AD AI ERROR:", type(exc).__name__)
    t, s, f = ad_template_text(prop)
    return t, s, f, "template"


async def load_ad_candidates(session, tg_id, user):
    """Active sale files with their ad state + media counts."""
    stmt = select(Property).where(active_property_filter())
    vf = vis_filter(Property, user, tg_id)
    if vf is not None:
        stmt = stmt.where(vf)
    props = (await session.execute(stmt)).scalars().all()
    ids = [p.id for p in props]
    ads, photos, videos = {}, {}, {}
    if ids:
        for a in (await session.execute(
            select(PropertyAd).where(PropertyAd.property_id.in_(ids))
        )).scalars().all():
            ads[a.property_id] = a
        for pid, c in (await session.execute(
            select(PropertyPhoto.property_id, func.count(PropertyPhoto.id))
            .where(PropertyPhoto.property_id.in_(ids))
            .group_by(PropertyPhoto.property_id)
        )).all():
            photos[pid] = c
        for pid, c in (await session.execute(
            select(PropertyVideo.property_id, func.count(PropertyVideo.id))
            .where(PropertyVideo.property_id.in_(ids))
            .group_by(PropertyVideo.property_id)
        )).all():
            videos[pid] = c
    out = []
    for p in props:
        ad = ads.get(p.id)
        status = ad.status if ad else AD_UNKNOWN
        score, todo, ok = ad_readiness(
            p, photos.get(p.id, 0), videos.get(p.id, 0)
        )
        out.append({
            "prop": p, "ad": ad, "status": status, "score": score,
            "todo": todo, "photos": photos.get(p.id, 0),
            "videos": videos.get(p.id, 0),
        })
    return out


def ad_summary_counts(cands):
    c = {AD_UNADVERTISED: 0, AD_REVIEW: 0, AD_ADVERTISED: 0, AD_UNKNOWN: 0}
    for x in cands:
        c[x["status"]] = c.get(x["status"], 0) + 1
    return c


def _ad_home_markup(counts):
    rows = [
        [InlineKeyboardButton(
            text=f"📋 پیشنهادها ({counts[AD_UNADVERTISED] + counts[AD_REVIEW]})",
            callback_data="adv:l:1")],
        [InlineKeyboardButton(
            text=f"❔ وضعیت نامشخص ({counts[AD_UNKNOWN]})",
            callback_data="adv:uk:1")],
        [InlineKeyboardButton(
            text=f"✅ آگهی‌شده‌ها ({counts[AD_ADVERTISED]})",
            callback_data="adv:a:1")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def ad_home(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    await state.clear()
    async with SessionLocal() as session:
        user = await get_user(
            session, message.from_user.id, message.from_user.full_name
        )
        cands = await load_ad_candidates(
            session, message.from_user.id, user
        )
    counts = ad_summary_counts(cands)
    lines = [
        "📢 پیشنهاد آگهی‌گذاری",
        "",
        f"⬜ آگهی‌نشده: {counts[AD_UNADVERTISED]}",
        f"🔄 نیازمند بررسی مجدد: {counts[AD_REVIEW]}",
        f"❔ وضعیت نامشخص: {counts[AD_UNKNOWN]}",
        f"✅ آگهی‌شده: {counts[AD_ADVERTISED]}",
        "",
        "فایل‌های «نامشخص» هیچ‌وقت خودکار آگهی‌نشده فرض نمی‌شوند؛ "
        "وضعیتشان را خودت مشخص کن.",
        "ثبت «آگهی‌شده» فقط یک ثبت داخلی است؛ ربات در هیچ پلتفرمی "
        "آگهی منتشر نمی‌کند.",
    ]
    if not ai_available():
        lines.append(
            "ℹ️ هوش مصنوعی فعال نیست؛ متن آگهی با قالب پایه ساخته می‌شود."
        )
    await message.answer(
        "\n".join(lines), reply_markup=_ad_home_markup(counts)
    )


def _ad_card(i, x):
    p = x["prop"]
    price = price_label(p.price) if (p.price or 0) > 0 else "قیمت ثبت نشده"
    return (
        f"{i}) {p.code} | {p.area or '—'} | {money(p.sqm)}م\n"
        f"   💰 {price}\n"
        f"   📊 امتیاز آمادگی: {x['score']}/100 "
        f"(🖼 {x['photos']} | 🎬 {x['videos']})\n"
        f"   💡 {ad_reason_text(x['status'], x['todo'])}"
    )


async def ad_send_list(callback, kind, page):
    tg = callback.from_user
    async with SessionLocal() as session:
        user = await get_user(session, tg.id, tg.full_name)
        cands = await load_ad_candidates(session, tg.id, user)
    if kind == "l":
        items = [x for x in cands if x["status"] in (AD_UNADVERTISED, AD_REVIEW)]
        items.sort(key=lambda x: (-x["score"], x["prop"].id))
        title = "📋 پیشنهادهای آگهی‌گذاری (به ترتیب آمادگی)"
    elif kind == "uk":
        items = [x for x in cands if x["status"] == AD_UNKNOWN]
        items.sort(key=lambda x: x["prop"].id)
        title = "❔ فایل‌های با وضعیت آگهی نامشخص"
    else:
        items = [x for x in cands if x["status"] == AD_ADVERTISED]
        items.sort(key=lambda x: (
            x["ad"].published_at or datetime.min), reverse=True)
        title = "✅ فایل‌های آگهی‌شده"
    total = len(items)
    pages = max(1, (total + AD_PAGE_SIZE - 1) // AD_PAGE_SIZE)
    page = max(1, min(page, pages))
    chunk = items[(page - 1) * AD_PAGE_SIZE: page * AD_PAGE_SIZE]
    lines = [f"{title} — {total} فایل", ""]
    rows = []
    if not chunk:
        lines.append("موردی نیست.")
    for i, x in enumerate(chunk, start=(page - 1) * AD_PAGE_SIZE + 1):
        p = x["prop"]
        if kind == "a":
            ad = x["ad"]
            when = tehran_time(ad.published_at) if ad.published_at else "—"
            lines.append(
                f"{i}) {p.code} | {p.area or '—'}\n"
                f"   پلتفرم (اعلام مشاور): {ad.platform or '—'} | "
                f"زمان ثبت: {when}"
            )
        else:
            lines.append(_ad_card(i, x))
        lines.append("")
        row = [InlineKeyboardButton(
            text=f"👁 {p.code}", callback_data=f"popen:{p.id}")]
        if kind == "uk":
            row.append(InlineKeyboardButton(
                text="⬜ آگهی‌نشده", callback_data=f"adv:set:{p.id}:u"))
            row.append(InlineKeyboardButton(
                text="✅ آگهی‌شده", callback_data=f"adv:m:{p.id}"))
        elif kind == "a":
            row.append(InlineKeyboardButton(
                text="⚙️ وضعیت", callback_data=f"adv:s:{p.id}"))
        else:
            row.append(InlineKeyboardButton(
                text="✍️ متن آگهی", callback_data=f"adv:g:{p.id}"))
        rows.append(row)
    if kind == "uk" and total and is_admin(tg.id):
        rows.append([InlineKeyboardButton(
            text="⬜ همه‌ی نامشخص‌ها = آگهی‌نشده (مدیر)",
            callback_data="adv:bulk")])
    nav = pagination_keyboard(f"adv:{kind}", page, pages)
    rows.extend(nav.inline_keyboard)
    rows.append([InlineKeyboardButton(
        text="⬅️ خلاصه", callback_data="adv:home")])
    await show(
        callback.message, "\n".join(lines)[:3900],
        InlineKeyboardMarkup(inline_keyboard=rows), edit=True,
    )


async def _ad_get_prop(session, prop_id, tg_id):
    prop = (await session.execute(
        select(Property).where(Property.id == prop_id)
    )).scalar_one_or_none()
    if not prop:
        return None
    if (prop.ownership_type or "عمومی") == "شخصی" and not is_admin(tg_id):
        user = await get_user(session, tg_id, "")
        if prop.owner_user_id != user.id:
            return None
    return prop


def _ad_text_message(prop, ad, status_note=""):
    lines = [f"✍️ آگهی فایل {prop.code}"]
    lines.append(f"وضعیت: {AD_STATUS_LABELS.get(ad.status, '—')}")
    if ad.text_source == "ai":
        lines.append("منبع متن: هوش مصنوعی (از داده‌های ثبت‌شده)")
    elif ad.text_source == "manual":
        lines.append("منبع متن: ویرایش دستی مشاور")
    elif ad.text_source == "template":
        lines.append("منبع متن: قالب پایه (بدون هوش مصنوعی)")
    if status_note:
        lines.append(status_note)
    lines += ["", f"🏷 عنوان: {ad.title}", "", "📝 نسخه کوتاه:",
              ad.text_short, "", "📄 نسخه کامل:", ad.text_full]
    if ad.missing_info:
        lines += ["", "⚠️ قبل از انتشار از مالک تأیید شود:",
                  ad.missing_info]
    return "\n".join(lines)[:3900]


def _ad_text_markup(prop_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔁 تولید مجدد", callback_data=f"adv:r:{prop_id}"),
         InlineKeyboardButton(
            text="✏️ ویرایش متن", callback_data=f"adv:e:{prop_id}")],
        [InlineKeyboardButton(
            text="📋 کپی متن", callback_data=f"adv:c:{prop_id}"),
         InlineKeyboardButton(
            text="👁 مشاهده فایل", callback_data=f"popen:{prop_id}")],
        [InlineKeyboardButton(
            text="✅ ثبت به‌عنوان آگهی‌شده",
            callback_data=f"adv:m:{prop_id}")],
    ])


async def ad_generate_and_store(session, prop, user, regenerate):
    n_photos, _ = await media_counts(session, prop.id)
    title, short, full, source = await generate_ad_text(prop)
    missing = "\n".join(
        f"• {x}" for x in ad_missing_list(prop, n_photos)
    )
    ad = (await session.execute(
        select(PropertyAd).where(PropertyAd.property_id == prop.id)
    )).scalar_one_or_none()
    if not ad:
        ad = PropertyAd(property_id=prop.id, status=AD_UNKNOWN)
        session.add(ad)
        # a file with no tracking row stays "unknown" until the advisor
        # decides; generating text never marks it advertised/unadvertised.
    ad.title, ad.text_short, ad.text_full = title, short, full
    ad.missing_info = missing
    ad.text_source = source
    ad.generated_at = utcnow_naive()
    ad.updated_at = utcnow_naive()
    await session.commit()
    await add_activity(
        session, user.id,
        "تولید مجدد متن آگهی" if regenerate else "تولید متن آگهی",
        f"فایل {prop.code} | منبع: {source}",
        property_id=prop.id,
    )
    return ad


@dp.callback_query(F.data.startswith("adv:"))
async def ad_callbacks(callback: CallbackQuery, state: FSMContext):
    if not await callback_access_required(callback):
        return
    parts = callback.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    tg = callback.from_user

    if action == "home":
        async with SessionLocal() as session:
            user = await get_user(session, tg.id, tg.full_name)
            cands = await load_ad_candidates(session, tg.id, user)
        counts = ad_summary_counts(cands)
        await show(
            callback.message,
            "📢 پیشنهاد آگهی‌گذاری\n\n"
            f"⬜ آگهی‌نشده: {counts[AD_UNADVERTISED]}\n"
            f"🔄 نیازمند بررسی مجدد: {counts[AD_REVIEW]}\n"
            f"❔ نامشخص: {counts[AD_UNKNOWN]}\n"
            f"✅ آگهی‌شده: {counts[AD_ADVERTISED]}",
            _ad_home_markup(counts), edit=True,
        )
        await callback.answer()
        return

    if action in ("l", "uk", "a"):
        await ad_send_list(callback, action, int(parts[2]))
        await callback.answer()
        return

    if action in ("g", "r"):
        prop_id = int(parts[2])
        async with SessionLocal() as session:
            prop = await _ad_get_prop(session, prop_id, tg.id)
            if not prop:
                await callback.answer("فایل پیدا نشد", show_alert=True)
                return
            user = await get_user(session, tg.id, tg.full_name)
            ad = (await session.execute(
                select(PropertyAd).where(PropertyAd.property_id == prop_id)
            )).scalar_one_or_none()
            if action == "g" and ad and ad.text_full:
                text = _ad_text_message(prop, ad)
            else:
                await callback.answer("⏳ در حال تولید…")
                ad = await ad_generate_and_store(
                    session, prop, user, regenerate=(action == "r")
                )
                note = ""
                if ad.text_source == "template" and ai_available():
                    note = "ℹ️ متن هوش مصنوعی قابل اعتماد نبود؛ قالب پایه ساخته شد."
                text = _ad_text_message(prop, ad, note)
        await callback.message.answer(
            text, reply_markup=_ad_text_markup(prop_id)
        )
        try:
            await callback.answer()
        except Exception:
            pass
        return

    if action == "c":
        prop_id = int(parts[2])
        async with SessionLocal() as session:
            ad = (await session.execute(
                select(PropertyAd).where(PropertyAd.property_id == prop_id)
            )).scalar_one_or_none()
        if not ad or not ad.text_full:
            await callback.answer("ابتدا متن را تولید کن.", show_alert=True)
            return
        body = f"{ad.title}\n\n{ad.text_full}"
        await callback.message.answer(
            "📋 برای کپی، روی متن بزن:\n\n"
            f"<pre>{html_lib.escape(body)[:3500]}</pre>",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    if action == "e":
        prop_id = int(parts[2])
        await state.clear()
        await state.update_data(property_id=prop_id)
        await state.set_state(AdEditForm.text)
        await callback.message.answer(
            "✏️ متن جدید «نسخه کامل» آگهی را بفرست.\n"
            "(فقط اطلاعات تأییدشده بنویس.)",
            reply_markup=keyboard([], include_cancel=True),
        )
        await callback.answer()
        return

    if action == "set":
        prop_id, code = int(parts[2]), parts[3]
        new_status = AD_UNADVERTISED if code == "u" else AD_REVIEW
        async with SessionLocal() as session:
            prop = await _ad_get_prop(session, prop_id, tg.id)
            if not prop:
                await callback.answer("فایل پیدا نشد", show_alert=True)
                return
            user = await get_user(session, tg.id, tg.full_name)
            ad = (await session.execute(
                select(PropertyAd).where(PropertyAd.property_id == prop_id)
            )).scalar_one_or_none()
            old = ad.status if ad else AD_UNKNOWN
            if not ad:
                ad = PropertyAd(property_id=prop_id)
                session.add(ad)
            ad.status = new_status
            ad.marked_by = user.id
            ad.updated_at = utcnow_naive()
            await session.commit()
            await add_activity(
                session, user.id, "تغییر وضعیت آگهی",
                f"{AD_STATUS_LABELS.get(old)} → "
                f"{AD_STATUS_LABELS.get(new_status)}",
                property_id=prop_id,
            )
        await callback.answer("✅ ثبت شد")
        await callback.message.answer(
            f"✅ وضعیت آگهی فایل {prop.code}: "
            f"{AD_STATUS_LABELS[new_status]}"
        )
        return

    if action == "s":
        prop_id = int(parts[2])
        async with SessionLocal() as session:
            prop = await _ad_get_prop(session, prop_id, tg.id)
            ad = (await session.execute(
                select(PropertyAd).where(PropertyAd.property_id == prop_id)
            )).scalar_one_or_none()
        if not prop:
            await callback.answer("فایل پیدا نشد", show_alert=True)
            return
        st = ad.status if ad else AD_UNKNOWN
        rows = [
            [InlineKeyboardButton(
                text="🔄 نیاز به بررسی مجدد",
                callback_data=f"adv:set:{prop_id}:r")],
            [InlineKeyboardButton(
                text="⬜ آگهی‌نشده", callback_data=f"adv:set:{prop_id}:u")],
            [InlineKeyboardButton(
                text="✍️ متن آگهی", callback_data=f"adv:g:{prop_id}")],
            [InlineKeyboardButton(
                text="👁 مشاهده فایل", callback_data=f"popen:{prop_id}")],
        ]
        extra = ""
        if ad and ad.status == AD_ADVERTISED:
            extra = (
                f"\nپلتفرم (اعلام مشاور): {ad.platform or '—'}"
                f"\nزمان ثبت: "
                f"{tehran_time(ad.published_at) if ad.published_at else '—'}"
            )
        await callback.message.answer(
            f"📢 وضعیت آگهی فایل {prop.code}: "
            f"{AD_STATUS_LABELS[st]}{extra}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        await callback.answer()
        return

    if action == "m":
        prop_id = int(parts[2])
        rows = [[InlineKeyboardButton(
            text=name, callback_data=f"adv:p:{prop_id}:{i}")]
            for i, name in enumerate(AD_PLATFORMS)]
        rows.append([InlineKeyboardButton(
            text="❌ انصراف", callback_data=f"popen:{prop_id}")])
        await callback.message.answer(
            "این آگهی را در کدام پلتفرم گذاشته‌ای؟\n"
            "(ربات خودش آگهی منتشر نمی‌کند؛ این فقط ثبت اعلام توست.)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        await callback.answer()
        return

    if action == "p":
        prop_id, idx = int(parts[2]), int(parts[3])
        if not (0 <= idx < len(AD_PLATFORMS)):
            await callback.answer()
            return
        await callback.message.answer(
            f"تأیید می‌کنی که آگهی این فایل «{AD_PLATFORMS[idx]}» "
            "گذاشته شده است؟",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ تأیید و ثبت",
                    callback_data=f"adv:k:{prop_id}:{idx}"),
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data=f"popen:{prop_id}"),
            ]]),
        )
        await callback.answer()
        return

    if action == "k":
        prop_id, idx = int(parts[2]), int(parts[3])
        if not (0 <= idx < len(AD_PLATFORMS)):
            await callback.answer()
            return
        platform = "" if idx == len(AD_PLATFORMS) - 1 else AD_PLATFORMS[idx]
        async with SessionLocal() as session:
            prop = await _ad_get_prop(session, prop_id, tg.id)
            if not prop:
                await callback.answer("فایل پیدا نشد", show_alert=True)
                return
            user = await get_user(session, tg.id, tg.full_name)
            ad = (await session.execute(
                select(PropertyAd).where(PropertyAd.property_id == prop_id)
            )).scalar_one_or_none()
            old = ad.status if ad else AD_UNKNOWN
            if old == AD_ADVERTISED:
                await callback.answer("قبلاً آگهی‌شده ثبت شده.", show_alert=True)
                return
            if not ad:
                ad = PropertyAd(property_id=prop_id)
                session.add(ad)
            ad.status = AD_ADVERTISED
            ad.platform = platform
            ad.published_at = utcnow_naive()
            ad.marked_by = user.id
            ad.updated_at = utcnow_naive()
            await session.commit()
            await add_activity(
                session, user.id, "تأیید و ثبت آگهی‌شده",
                f"پلتفرم (اعلام مشاور): {platform or 'نامشخص'}",
                property_id=prop_id,
            )
        await callback.answer("✅ ثبت شد")
        await callback.message.answer(
            f"✅ فایل {prop.code} به‌عنوان «آگهی‌شده» ثبت شد.\n"
            "یادآوری: این ثبت بر اساس اعلام شماست و ربات انتشار "
            "واقعی را تأیید نمی‌کند."
        )
        return

    if action == "bulk":
        if not is_admin(tg.id):
            await callback.answer("⛔ فقط مدیر.", show_alert=True)
            return
        await callback.message.answer(
            "همه‌ی فایل‌های فعال با وضعیت نامشخص «آگهی‌نشده» علامت بخورند؟\n"
            "(فقط اگر مطمئنی هیچ‌کدام قبلاً آگهی نشده‌اند.)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ بله، همه", callback_data="adv:bulkok"),
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data="adv:home"),
            ]]),
        )
        await callback.answer()
        return

    if action == "bulkok":
        if not is_admin(tg.id):
            await callback.answer("⛔ فقط مدیر.", show_alert=True)
            return
        async with SessionLocal() as session:
            user = await get_user(session, tg.id, tg.full_name)
            cands = await load_ad_candidates(session, tg.id, user)
            n = 0
            for x in cands:
                if x["status"] == AD_UNKNOWN:
                    session.add(PropertyAd(
                        property_id=x["prop"].id, status=AD_UNADVERTISED,
                        marked_by=user.id))
                    n += 1
            await session.commit()
            await add_activity(
                session, user.id, "تغییر وضعیت آگهی",
                f"{n} فایل نامشخص → آگهی‌نشده (دسته‌ای)",
            )
        await callback.answer("✅ انجام شد")
        await callback.message.answer(f"✅ {n} فایل «آگهی‌نشده» علامت خورد.")
        return

    await callback.answer()


@dp.message(AdEditForm.text, F.text)
async def ad_edit_save(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    data = await state.get_data()
    prop_id = data.get("property_id")
    text = (message.text or "").strip()
    if not prop_id or not text:
        await state.clear()
        return
    async with SessionLocal() as session:
        prop = await _ad_get_prop(session, prop_id, message.from_user.id)
        if not prop:
            await state.clear()
            await message.answer("فایل پیدا نشد.")
            return
        user = await get_user(
            session, message.from_user.id, message.from_user.full_name
        )
        ad = (await session.execute(
            select(PropertyAd).where(PropertyAd.property_id == prop_id)
        )).scalar_one_or_none()
        if not ad:
            ad = PropertyAd(property_id=prop_id, status=AD_UNKNOWN)
            session.add(ad)
        ad.text_full = text[:3500]
        if not ad.title:
            ad.title = text.splitlines()[0][:150]
        if not ad.text_short:
            ad.text_short = ad.title
        ad.text_source = "manual"
        ad.updated_at = utcnow_naive()
        await session.commit()
        await add_activity(
            session, user.id, "ویرایش متن آگهی",
            f"متن آگهی فایل {prop.code} ویرایش شد.",
            property_id=prop_id,
        )
        out = _ad_text_message(prop, ad)
    await state.clear()
    await message.answer(
        "✅ متن ذخیره شد.", reply_markup=main_menu(message.from_user.id)
    )
    await message.answer(out, reply_markup=_ad_text_markup(prop_id))


# ---------------------------------------------------------
# 📊 MANAGER DASHBOARD (admin only, real DB data only)
# ---------------------------------------------------------

DASH_PAGE = 5
DASH_LIST_PAGE = 8
IDLE_DAYS = 14
ACTIONABLE_NEXT = ("پیگیری", "بازدید مجدد", "مذاکره", "قرارداد")
CALL_ACTIVITY_TYPES = ("تماس با مالک", "پیگیری")

DASH_PERIOD = {}   # tg_id -> period dict (UI state)
DASH_FILTER = {}   # tg_id -> files filter dict (UI state)


class DashForm(StatesGroup):
    custom = State()


# ---- Jalali <-> Gregorian (pure) ----

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    )
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def jalali_to_gregorian(jy, jm, jd):
    jy += 1595
    days = (
        -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4)
        + jd + (((jm - 1) * 31) if jm < 7 else (((jm - 7) * 30) + 186))
    )
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    months = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31,
              30, 31]
    gm = 0
    while gm < 13 and gd > months[gm]:
        gd -= months[gm]
        gm += 1
    return gy, gm, gd


_DATE_RE = re.compile(r"(\d{4})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{1,2})")


def parse_date_text(text):
    """Jalali (year < 1700) or Gregorian date text -> date, else None."""
    if not text:
        return None
    m = _DATE_RE.search(normalize_digits(text))
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        if y < 1700:
            if not (1 <= mo <= 12 and 1 <= d <= 31):
                return None
            y, mo, d = jalali_to_gregorian(y, mo, d)
        return date_cls(y, mo, d)
    except Exception:
        return None


def parse_all_dates(text):
    out = []
    for m in _DATE_RE.finditer(normalize_digits(text or "")):
        d = parse_date_text(m.group(0))
        if d:
            out.append(d)
    return out


def fmt_jalali(d):
    if not d:
        return "—"
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    return f"{jy}/{jm:02d}/{jd:02d}"


def tehran_today(now_utc=None):
    return ((now_utc or utcnow_naive()) + TEHRAN_OFFSET).date()


def tehran_day_start_utc(d):
    return datetime(d.year, d.month, d.day) - TEHRAN_OFFSET


def make_period(key, today=None, custom=None):
    today = today or tehran_today()
    if key == "t":
        s, e, label = today, today, "امروز"
    elif key == "w":
        s, e, label = today - timedelta(days=6), today, "۷ روز اخیر"
    elif key == "c" and custom:
        s, e = custom
        if s > e:
            s, e = e, s
        label = f"{fmt_jalali(s)} تا {fmt_jalali(e)}"
    else:
        key = "m"
        s, e, label = today - timedelta(days=29), today, "۳۰ روز اخیر"
    length = (e - s).days + 1
    ps, pe = s - timedelta(days=length), s - timedelta(days=1)
    return {
        "key": key, "label": label, "s": s, "e": e,
        "start": tehran_day_start_utc(s),
        "end": tehran_day_start_utc(e) + timedelta(days=1),
        "prev_start": tehran_day_start_utc(ps),
        "prev_end": tehran_day_start_utc(pe) + timedelta(days=1),
    }


def get_period(tg_id):
    p = DASH_PERIOD.get(tg_id)
    if p and p["key"] == "c":
        return p
    return make_period((p or {}).get("key", "m"))


def _in(dt, start, end):
    return dt is not None and start <= dt < end


# ---- data loading (DB -> plain dicts) ----

async def dash_load(period):
    async with SessionLocal() as session:
        users = (await session.execute(select(User))).scalars().all()
        props = (await session.execute(
            select(Property).where(_sale_only(Property))
        )).scalars().all()
        clients = (await session.execute(
            select(Client).where(_sale_only(Client))
        )).scalars().all()
        visits = (await session.execute(select(Visit))).scalars().all()
        events = (await session.execute(select(StatusEvent))).scalars().all()
        ad_rows = (await session.execute(
            select(PropertyAd.property_id, PropertyAd.status)
        )).all()
        photos = dict((await session.execute(
            select(PropertyPhoto.property_id, func.count(PropertyPhoto.id))
            .group_by(PropertyPhoto.property_id)
        )).all())
        videos = dict((await session.execute(
            select(PropertyVideo.property_id, func.count(PropertyVideo.id))
            .group_by(PropertyVideo.property_id)
        )).all())
        last_p = dict((await session.execute(
            select(Activity.property_id, func.max(Activity.created_at))
            .where(Activity.property_id > 0)
            .group_by(Activity.property_id)
        )).all())
        last_c = dict((await session.execute(
            select(Activity.client_id, func.max(Activity.created_at))
            .where(Activity.client_id > 0)
            .group_by(Activity.client_id)
        )).all())
        acts = (await session.execute(
            select(Activity.user_id, Activity.activity_type,
                   Activity.created_at)
            .where(Activity.created_at >= period["prev_start"])
        )).all()

    users_l = [{"id": u.id, "tg": u.telegram_id,
                "name": u.name or "بدون نام"} for u in users]
    tg_by_uid = {u["id"]: u["tg"] for u in users_l}
    ad_by_pid = {pid: st for pid, st in ad_rows}

    props_l = []
    for p in props:
        resp = tg_by_uid.get(p.owner_user_id) if p.owner_user_id else None
        props_l.append({
            "id": p.id, "code": p.code, "area": p.area or "",
            "status": p.status or "", "created_by": p.created_by,
            "resp_tg": resp or p.created_by,
            "created_at": p.created_at, "updated_at": p.updated_at,
            "price": p.price or 0, "sqm": p.sqm or 0,
            "type": p.property_type or "", "bedrooms": p.bedrooms or 0,
            "address": (p.address or "").strip(),
            "owner_phone": (p.owner_phone or "").strip(),
            "floor_known": bool(
                (p.floor_label or "").strip()
                or (p.unit_floor or 0) != 0 or (p.floors or 0) > 0),
            "deal_type": p.deal_type or ENV_SALE,
            "ad": ad_by_pid.get(p.id, AD_UNKNOWN),
            "photos": photos.get(p.id, 0), "videos": videos.get(p.id, 0),
            "last_act": last_p.get(p.id),
        })
    clients_l = [{
        "id": c.id, "name": c.name, "status": c.status or "",
        "created_by": c.created_by, "created_at": c.created_at,
        "max_budget": c.max_budget or 0, "last_act": last_c.get(c.id),
    } for c in clients]
    visits_l = [{
        "id": v.id, "property_id": v.property_id,
        "client_id": v.client_id, "agent_tg": v.agent_id,
        "visited_at": v.visited_at, "interest": v.interest or "",
        "next_action": v.next_action or "",
        "followup_date": v.followup_date or "",
    } for v in visits]
    events_l = [{
        "property_id": e.property_id, "user_id": e.user_id,
        "tg": tg_by_uid.get(e.user_id), "old": e.old_status,
        "new": e.new_status, "value": e.transaction_value or 0,
        "at": e.created_at,
    } for e in events]
    acts_l = [{"tg": tg_by_uid.get(uid), "type": t, "at": at}
              for uid, t, at in acts]
    return {
        "users": users_l, "properties": props_l, "clients": clients_l,
        "visits": visits_l, "events": events_l, "acts": acts_l,
    }


# ---- pure computations ----

def prop_critical_missing(p):
    miss = []
    if p["price"] <= 0:
        miss.append("قیمت")
    if not p["area"]:
        miss.append("منطقه")
    if p["sqm"] <= 0:
        miss.append("متراژ")
    if not p["type"]:
        miss.append("نوع ملک")
    if not p["owner_phone"]:
        miss.append("تلفن مالک")
    return miss


def prop_incomplete_missing(p):
    miss = list(prop_critical_missing(p))
    if not p["address"]:
        miss.append("آدرس")
    if not p["floor_known"]:
        miss.append("طبقه")
    if p["type"] == "آپارتمان" and p["bedrooms"] <= 0:
        miss.append("تعداد خواب")
    if p["photos"] == 0:
        miss.append("عکس")
    return miss


def dash_followups(data, now_utc):
    """Follow-ups taken from each client's LATEST visit.

    A follow-up is considered handled when the client has any logged
    activity after that visit record. Dates that cannot be parsed
    (e.g. «ندارد») produce no dated follow-up.
    """
    today = tehran_today(now_utc)
    props = {p["id"]: p for p in data["properties"]}
    clients = {c["id"]: c for c in data["clients"]}
    latest = {}
    for v in data["visits"]:
        if v["client_id"] not in clients:
            continue
        cur = latest.get(v["client_id"])
        if cur is None or (v["visited_at"] or datetime.min) > (
                cur["visited_at"] or datetime.min):
            latest[v["client_id"]] = v
    dated, waiting = [], []
    for cid, v in latest.items():
        c, p = clients[cid], props.get(v["property_id"])
        if c["status"] not in ACTIVE_CLIENT_STATUSES:
            continue
        if not p or p["status"] not in ACTIVE_PROPERTY_STATUSES:
            continue
        handled = bool(
            c["last_act"] and v["visited_at"]
            and c["last_act"] > v["visited_at"] + timedelta(minutes=10)
        )
        due = parse_date_text(v["followup_date"])
        item = {
            "client": c, "prop": p, "visit": v, "due": due,
            "agent_tg": v["agent_tg"], "handled": handled,
        }
        if due and not handled:
            if due < today:
                item["kind"] = "overdue"
                item["days_over"] = (today - due).days
            elif due == today:
                item["kind"] = "today"
            else:
                item["kind"] = "upcoming"
            dated.append(item)
        if (not handled and v["next_action"] in ACTIONABLE_NEXT):
            waiting.append(item)
    return {"dated": dated, "waiting": waiting, "today": today}


def dash_opportunities(data, now_utc, fol):
    action_pts = {"قرارداد": 40, "مذاکره": 30, "بازدید مجدد": 15,
                  "پیگیری": 10}
    interest_pts = {"خیلی زیاد": 25, "زیاد": 15, "متوسط": 5}
    props = {p["id"]: p for p in data["properties"]}
    clients = {c["id"]: c for c in data["clients"]}
    overdue_keys = {
        (i["client"]["id"], i["prop"]["id"]): i
        for i in fol["dated"] if i["kind"] == "overdue"
    }
    latest = {}
    for v in data["visits"]:
        key = (v["client_id"], v["property_id"])
        cur = latest.get(key)
        if cur is None or (v["visited_at"] or datetime.min) > (
                cur["visited_at"] or datetime.min):
            latest[key] = v
    users = {u["tg"]: u["name"] for u in data["users"]}
    out = []
    for (cid, pid), v in latest.items():
        c, p = clients.get(cid), props.get(pid)
        if not c or not p:
            continue
        if c["status"] not in ACTIVE_CLIENT_STATUSES:
            continue
        if p["status"] not in ACTIVE_PROPERTY_STATUSES:
            continue
        if v["next_action"] == "رد شد" or v["interest"] == "رد":
            continue
        score, reasons, gaps = 0, [], []
        pts = action_pts.get(v["next_action"])
        if pts:
            score += pts
            reasons.append(f"اقدام بعدی: {v['next_action']}")
        else:
            gaps.append("اقدام بعدی مشخص نیست")
        ip = interest_pts.get(v["interest"])
        if ip:
            score += ip
            reasons.append(f"علاقه مشتری: {v['interest']}")
        elif not v["interest"]:
            gaps.append("میزان علاقه ثبت نشده")
        if v["visited_at"]:
            age = (now_utc - v["visited_at"]).days
            bonus = 15 if age <= 3 else 10 if age <= 7 else 5 if age <= 14 else 0
            score += bonus
            reasons.append(f"آخرین بازدید {age} روز پیش")
        due = parse_date_text(v["followup_date"])
        if due:
            score += 5
        else:
            gaps.append("تاریخ پیگیری ثبت نشده")
        if c["max_budget"] > 0:
            if p["price"] > 0 and p["price"] <= c["max_budget"]:
                score += 10
                reasons.append("قیمت فایل در بودجه")
            elif p["price"] > c["max_budget"]:
                reasons.append("قیمت فایل بالاتر از بودجه")
        else:
            gaps.append("بودجه مشتری ثبت نشده")
        if p["status"] == STATUS_NEGOTIATING:
            score += 5
            reasons.append("فایل در حال مذاکره است")
        ov = overdue_keys.get((cid, pid))
        if ov:
            action = f"پیگیری فوری ({ov['days_over']} روز عقب‌افتاده)"
        elif v["next_action"] == "قرارداد":
            action = "پیگیری برای نهایی‌کردن قرارداد"
        elif v["next_action"] == "مذاکره":
            action = "ادامه‌ی مذاکره"
        elif v["next_action"] == "بازدید مجدد":
            action = "هماهنگی بازدید مجدد"
        else:
            action = "تماس پیگیری"
        out.append({
            "client": c, "prop": p, "visit": v, "score": min(score, 100),
            "reasons": reasons, "gaps": gaps, "action": action,
            "overdue": bool(ov),
            "agent": users.get(v["agent_tg"], f"کاربر {v['agent_tg']}"),
        })
    out.sort(key=lambda x: (-x["score"], x["prop"]["id"]))
    return out


def dash_summary(data, period, now_utc, fol):
    props = data["properties"]
    active = [p for p in props if p["status"] in ACTIVE_PROPERTY_STATUSES]
    s, e = period["start"], period["end"]
    ev = [x for x in data["events"] if _in(x["at"], s, e)]
    sold_us = {x["property_id"] for x in ev if x["new"] == SOLD_BY_US}
    sold_other = {x["property_id"] for x in ev if x["new"] == SOLD_BY_OTHER}
    dropped = {x["property_id"] for x in ev if x["new"] == STATUS_DROPPED}
    latest = {}
    for v in data["visits"]:
        cur = latest.get(v["client_id"])
        if cur is None or (v["visited_at"] or datetime.min) > (
                cur["visited_at"] or datetime.min):
            latest[v["client_id"]] = v
    cl = {c["id"]: c for c in data["clients"]}
    pr = {p["id"]: p for p in props}
    neg = 0
    for cid, v in latest.items():
        c, p = cl.get(cid), pr.get(v["property_id"])
        if (c and p and c["status"] in ACTIVE_CLIENT_STATUSES
                and p["status"] in ACTIVE_PROPERTY_STATUSES
                and v["next_action"] in ("مذاکره", "قرارداد")):
            neg += 1
    ad_un = sum(1 for p in active if p["ad"] in (AD_UNADVERTISED, AD_REVIEW))
    ad_unknown = sum(1 for p in active if p["ad"] == AD_UNKNOWN)
    return {
        "active_files": len(active),
        "new_files": sum(1 for p in props if _in(p["created_at"], s, e)),
        "negotiating_files": sum(
            1 for p in props if p["status"] == STATUS_NEGOTIATING),
        "sold_us": len(sold_us),
        "sold_other": len(sold_other),
        "dropped": len(dropped),
        "active_clients": sum(
            1 for c in data["clients"]
            if c["status"] in ACTIVE_CLIENT_STATUSES),
        "visits": sum(1 for v in data["visits"]
                      if _in(v["visited_at"], s, e)),
        "active_negotiations": neg,
        "contracts": len(sold_us),
        "overdue": sum(1 for i in fol["dated"] if i["kind"] == "overdue"),
        "due_today": sum(1 for i in fol["dated"] if i["kind"] == "today"),
        "unadvertised": ad_un,
        "ad_unknown": ad_unknown,
        "incomplete": sum(
            1 for p in active if prop_incomplete_missing(p)),
        "critical_missing": sum(
            1 for p in active if prop_critical_missing(p)),
    }


def dash_advisor_stats(data, period, fol):
    s, e = period["start"], period["end"]
    out = []
    for u in data["users"]:
        tg = u["tg"]
        files_reg = sum(
            1 for p in data["properties"]
            if p["created_by"] == tg and _in(p["created_at"], s, e))
        files_active = sum(
            1 for p in data["properties"]
            if p["created_by"] == tg
            and p["status"] in ACTIVE_PROPERTY_STATUSES)
        clients_active = sum(
            1 for c in data["clients"]
            if c["created_by"] == tg
            and c["status"] in ACTIVE_CLIENT_STATUSES)
        my_visits = [v for v in data["visits"]
                     if v["agent_tg"] == tg and _in(v["visited_at"], s, e)]
        visits_n = len(my_visits)
        neg_n = (
            sum(1 for v in my_visits if v["next_action"] == "مذاکره")
            + sum(1 for a in data["acts"]
                  if a["tg"] == tg and a["type"] == "مذاکره"
                  and _in(a["at"], s, e))
        )
        calls_n = sum(
            1 for a in data["acts"]
            if a["tg"] == tg and a["type"] in CALL_ACTIVITY_TYPES
            and _in(a["at"], s, e))
        contracts = len({
            x["property_id"] for x in data["events"]
            if x["tg"] == tg and x["new"] == SOLD_BY_US
            and _in(x["at"], s, e)})
        overdue = sum(1 for i in fol["dated"]
                      if i["kind"] == "overdue" and i["agent_tg"] == tg)
        waiting = sum(1 for i in fol["waiting"] if i["agent_tg"] == tg)
        if visits_n >= 5:
            neg_rate = f"{round(100 * neg_n / visits_n)}٪"
        else:
            neg_rate = None
        if neg_n >= 3:
            con_rate = f"{round(100 * contracts / neg_n)}٪"
        else:
            con_rate = None
        perf = max(
            0,
            files_reg * 1 + visits_n * 2 + (calls_n) * 1 + neg_n * 3
            + contracts * 10 - overdue * 1,
        )
        out.append({
            "tg": tg, "name": u["name"], "files_reg": files_reg,
            "files_active": files_active, "clients_active": clients_active,
            "calls": calls_n, "visits": visits_n, "negotiations": neg_n,
            "contracts": contracts, "overdue": overdue, "waiting": waiting,
            "neg_rate": neg_rate, "con_rate": con_rate, "perf": perf,
        })
    out.sort(key=lambda x: (-x["perf"], x["name"]))
    return out


def dash_alerts(data, now_utc, fol):
    props_with_dated = {
        i["prop"]["id"] for i in fol["dated"]}
    neg_no_next = [
        p for p in data["properties"]
        if p["status"] == STATUS_NEGOTIATING
        and p["id"] not in props_with_dated]
    cutoff = now_utc - timedelta(days=IDLE_DAYS)

    def ref(x):
        return x["last_act"] or x["created_at"]

    idle_files = [
        p for p in data["properties"]
        if p["status"] in ACTIVE_PROPERTY_STATUSES
        and ref(p) and ref(p) < cutoff]
    idle_clients = [
        c for c in data["clients"]
        if c["status"] in ACTIVE_CLIENT_STATUSES
        and ref(c) and ref(c) < cutoff]
    return {"neg_no_next": neg_no_next, "idle_files": idle_files,
            "idle_clients": idle_clients}


def dash_contracts(data, period):
    pr = {p["id"]: p for p in data["properties"]}
    users = {u["tg"]: u["name"] for u in data["users"]}

    def collect(start, end):
        seen, rows = set(), []
        for x in sorted(data["events"], key=lambda z: z["at"]):
            if x["new"] != SOLD_BY_US or not _in(x["at"], start, end):
                continue
            if x["property_id"] in seen:
                continue
            seen.add(x["property_id"])
            p = pr.get(x["property_id"])
            rows.append({
                "prop": p, "value": x["value"], "at": x["at"],
                "agent": users.get(x["tg"], "نامشخص"),
                "area": (p or {}).get("area") or "نامشخص",
                "deal": (p or {}).get("deal_type") or ENV_SALE,
            })
        return rows

    cur = collect(period["start"], period["end"])
    prev = collect(period["prev_start"], period["prev_end"])

    def tally(rows, key):
        d = {}
        for r in rows:
            d[r[key]] = d.get(r[key], 0) + 1
        return sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))

    def amount(rows):
        vals = [r["value"] for r in rows if r["value"] > 0]
        return sum(vals), len(vals)

    return {
        "rows": sorted(cur, key=lambda r: r["at"], reverse=True),
        "count": len(cur), "prev_count": len(prev),
        "by_agent": tally(cur, "agent"), "by_area": tally(cur, "area"),
        "by_deal": tally(cur, "deal"),
        "amount": amount(cur), "prev_amount": amount(prev),
    }


# ---- rendering helpers ----

def _guard_text():
    return "⛔ این بخش فقط برای مدیر سیستم است."


async def dash_guard_msg(message: Message):
    if not await access_required(message):
        return False
    if not is_admin(message.from_user.id):
        await message.answer(_guard_text())
        return False
    return True


async def dash_guard_cb(callback: CallbackQuery):
    if not await callback_access_required(callback):
        return False
    if not is_admin(callback.from_user.id):
        await callback.answer(_guard_text(), show_alert=True)
        return False
    return True


def dash_home_markup():
    def b(text, data):
        return InlineKeyboardButton(text=text, callback_data=data)
    return InlineKeyboardMarkup(inline_keyboard=[
        [b("📊 خلاصه مدیریت", "dsh:sum"), b("👥 عملکرد مشاوران", "dsh:adv:1")],
        [b("🎯 فرصت‌های نزدیک به قرارداد", "dsh:opp:1")],
        [b("⏰ پیگیری‌های عقب‌افتاده", "dsh:fol:1"),
         b("🏠 وضعیت فایل‌ها", "dsh:fil")],
        [b("📢 آگهی‌گذاری", "dsh:ads"), b("🤝 گزارش قراردادها", "dsh:con:1")],
        [b("📅 انتخاب بازه زمانی", "dsh:per")],
    ])


def _back_row():
    return [InlineKeyboardButton(
        text="⬅️ داشبورد", callback_data="dsh:home")]


def _name(data, tg):
    for u in data["users"]:
        if u["tg"] == tg:
            return u["name"]
    return f"کاربر {tg}"


def render_summary(sm, period):
    lines = [
        f"📊 خلاصه مدیریت — {period['label']}", "",
        "📁 فایل‌ها",
        f"• فایل‌های فعال: {sm['active_files']}",
        f"• فایل‌های جدید در بازه: {sm['new_files']}",
        f"• فایل‌های در حال مذاکره (وضعیت فایل): {sm['negotiating_files']}",
        f"• فروخته‌شده توسط تیم (بازه): {sm['sold_us']}",
        f"• فروخته‌شده توسط دیگران (بازه): {sm['sold_other']}",
        f"• منصرف‌شده/از دست‌رفته (بازه): {sm['dropped']}", "",
        "👥 مشتری و فعالیت",
        f"• مشتریان فعال: {sm['active_clients']}",
        f"• بازدیدهای انجام‌شده (بازه): {sm['visits']}",
        f"• مذاکرات فعال: {sm['active_negotiations']}",
        f"• قراردادهای نهایی‌شده (بازه): {sm['contracts']}", "",
        "⏰ پیگیری",
        f"• عقب‌افتاده: {sm['overdue']}",
        f"• سررسید امروز: {sm['due_today']}", "",
        "📢 آگهی و کیفیت فایل",
        f"• فایل‌های فعال آگهی‌نشده: {sm['unadvertised']}",
        f"• وضعیت آگهی نامشخص: {sm['ad_unknown']}",
        f"• فایل‌های ناقص: {sm['incomplete']}",
        f"• فاقد اطلاعات مهم: {sm['critical_missing']}", "",
        "ℹ️ شمارش‌ها از سوابق ثبت‌شده‌ی ربات است. معاملات قبل از "
        "نسخه‌ی جدید از یادداشت‌های فعالیت بازیابی شده‌اند.",
    ]
    return "\n".join(lines)


# ---- handlers ----

async def dash_home(message: Message, state: FSMContext):
    if not await dash_guard_msg(message):
        return
    await state.clear()
    period = get_period(message.from_user.id)
    DASH_PERIOD[message.from_user.id] = period
    await message.answer(
        f"📊 داشبورد مدیریتی\n📅 بازه: {period['label']}",
        reply_markup=dash_home_markup(),
    )


async def _dash_context(tg_id):
    period = get_period(tg_id)
    now = utcnow_naive()
    data = await dash_load(period)
    fol = dash_followups(data, now)
    return period, now, data, fol


@dp.callback_query(F.data.startswith("dsh:"))
async def dash_callbacks(callback: CallbackQuery, state: FSMContext):
    if not await dash_guard_cb(callback):
        return
    parts = callback.data.split(":")
    sec = parts[1] if len(parts) > 1 else ""
    tg = callback.from_user.id
    msg = callback.message

    try:
        if sec == "home":
            period = get_period(tg)
            await show(
                msg, f"📊 داشبورد مدیریتی\n📅 بازه: {period['label']}",
                dash_home_markup(), edit=True)

        elif sec == "per":
            if len(parts) == 2:
                rows = [
                    [InlineKeyboardButton(text="امروز", callback_data="dsh:per:t"),
                     InlineKeyboardButton(text="۷ روز اخیر", callback_data="dsh:per:w")],
                    [InlineKeyboardButton(text="۳۰ روز اخیر", callback_data="dsh:per:m"),
                     InlineKeyboardButton(text="بازه دلخواه", callback_data="dsh:per:c")],
                    _back_row(),
                ]
                await show(
                    msg, f"📅 بازه‌ی فعلی: {get_period(tg)['label']}\nیکی را انتخاب کن:",
                    InlineKeyboardMarkup(inline_keyboard=rows), edit=True)
            elif parts[2] == "c":
                await state.clear()
                await state.set_state(DashForm.custom)
                await msg.answer(
                    "📅 بازه را بفرست؛ مثال:\n"
                    "۱۴۰۵/۰۷/۰۱ تا ۱۴۰۵/۰۷/۱۵\n"
                    "(شمسی یا میلادی)",
                    reply_markup=keyboard([], include_cancel=True))
            else:
                DASH_PERIOD[tg] = make_period(parts[2])
                period, now, data, fol = await _dash_context(tg)
                sm = dash_summary(data, period, now, fol)
                await show(msg, render_summary(sm, period),
                           InlineKeyboardMarkup(inline_keyboard=[_back_row()]),
                           edit=True)

        elif sec == "sum":
            period, now, data, fol = await _dash_context(tg)
            sm = dash_summary(data, period, now, fol)
            await show(msg, render_summary(sm, period),
                       InlineKeyboardMarkup(inline_keyboard=[_back_row()]),
                       edit=True)

        elif sec == "adv":
            period, now, data, fol = await _dash_context(tg)
            stats = dash_advisor_stats(data, period, fol)
            if len(parts) >= 4 and parts[2] == "u":
                st = next((x for x in stats if x["tg"] == int(parts[3])), None)
                if not st:
                    await callback.answer("پیدا نشد", show_alert=True)
                    return
                calls = st["calls"] if st["calls"] else "—"
                lines = [
                    f"👤 {st['name']} — {period['label']}", "",
                    f"• فایل ثبت‌شده در بازه: {st['files_reg']}",
                    f"• فایل‌های فعال: {st['files_active']}",
                    f"• مشتریان فعال: {st['clients_active']}",
                    f"• تماس/پیگیری ثبت‌شده: {calls}",
                    f"• بازدید: {st['visits']}",
                    f"• مذاکره: {st['negotiations']}",
                    f"• قرارداد نهایی‌شده: {st['contracts']}",
                    f"• پیگیری عقب‌افتاده: {st['overdue']}",
                    f"• مشتری منتظر اقدام بعدی: {st['waiting']}",
                    f"• بازدید→مذاکره: {st['neg_rate'] or 'داده کافی نیست'}",
                    f"• مذاکره→قرارداد: {st['con_rate'] or 'داده کافی نیست'}",
                    "", f"امتیاز ترکیبی عملکرد: {st['perf']}",
                ]
                rows = [[InlineKeyboardButton(
                    text="⬅️ فهرست مشاوران", callback_data="dsh:adv:1")],
                    _back_row()]
                await show(msg, "\n".join(lines),
                           InlineKeyboardMarkup(inline_keyboard=rows), edit=True)
            else:
                page = int(parts[2]) if len(parts) > 2 else 1
                pages = max(1, (len(stats) + DASH_LIST_PAGE - 1) // DASH_LIST_PAGE)
                page = max(1, min(page, pages))
                chunk = stats[(page - 1) * DASH_LIST_PAGE: page * DASH_LIST_PAGE]
                lines = [f"👥 عملکرد مشاوران — {period['label']}",
                         "رتبه بر پایه‌ی عملکرد ترکیبی (فایل، تماس، بازدید، "
                         "مذاکره، قرارداد منهای پیگیری عقب‌افتاده)", ""]
                rows = []
                for i, st in enumerate(chunk, start=(page - 1) * DASH_LIST_PAGE + 1):
                    lines.append(
                        f"{i}) {st['name']} | امتیاز {st['perf']} | "
                        f"فایل {st['files_reg']} | بازدید {st['visits']} | "
                        f"مذاکره {st['negotiations']} | قرارداد {st['contracts']} | "
                        f"عقب‌افتاده {st['overdue']}")
                    rows.append([InlineKeyboardButton(
                        text=f"🔍 {st['name']}",
                        callback_data=f"dsh:adv:u:{st['tg']}")])
                if not chunk:
                    lines.append("مشاوری ثبت نشده.")
                rows.extend(pagination_keyboard("dsh:adv", page, pages).inline_keyboard)
                rows.append(_back_row())
                await show(msg, "\n".join(lines)[:3900],
                           InlineKeyboardMarkup(inline_keyboard=rows), edit=True)

        elif sec == "opp":
            period, now, data, fol = await _dash_context(tg)
            opps = dash_opportunities(data, now, fol)
            page = int(parts[2]) if len(parts) > 2 else 1
            pages = max(1, (len(opps) + DASH_PAGE - 1) // DASH_PAGE)
            page = max(1, min(page, pages))
            chunk = opps[(page - 1) * DASH_PAGE: page * DASH_PAGE]
            lines = ["🎯 فرصت‌های نزدیک به قرارداد",
                     "امتیاز فقط راهنمای اولویت است، نه احتمال قطعی.", ""]
            rows = []
            if not chunk:
                lines.append("فرصتی با داده‌ی کافی پیدا نشد.")
            for i, o in enumerate(chunk, start=(page - 1) * DASH_PAGE + 1):
                flag = "⏰ نیازمند اقدام | " if o["overdue"] else ""
                lines.append(
                    f"{i}) {flag}امتیاز {o['score']}\n"
                    f"   👤 {o['client']['name']} | 🏠 {o['prop']['code']} | "
                    f"مشاور: {o['agent']}\n"
                    f"   چرا: {('، '.join(o['reasons'])) or '—'}\n"
                    + (f"   کمبود داده: {('، '.join(o['gaps']))}\n" if o["gaps"] else "")
                    + f"   ➡️ {o['action']}\n")
                rows.append([
                    InlineKeyboardButton(
                        text=f"👤 {o['client']['name']}",
                        callback_data=f"copen:{o['client']['id']}"),
                    InlineKeyboardButton(
                        text=f"🏠 {o['prop']['code']}",
                        callback_data=f"popen:{o['prop']['id']}")])
            rows.extend(pagination_keyboard("dsh:opp", page, pages).inline_keyboard)
            rows.append(_back_row())
            await show(msg, "\n".join(lines)[:3900],
                       InlineKeyboardMarkup(inline_keyboard=rows), edit=True)

        elif sec == "fol":
            period, now, data, fol = await _dash_context(tg)
            al = dash_alerts(data, now, fol)
            overdue = sorted(
                [i for i in fol["dated"] if i["kind"] == "overdue"],
                key=lambda i: -i["days_over"])
            today_items = [i for i in fol["dated"] if i["kind"] == "today"]
            page = int(parts[2]) if len(parts) > 2 else 1
            pages = max(1, (len(overdue) + DASH_LIST_PAGE - 1) // DASH_LIST_PAGE)
            page = max(1, min(page, pages))
            chunk = overdue[(page - 1) * DASH_LIST_PAGE: page * DASH_LIST_PAGE]
            by_agent = {}
            for i in overdue:
                by_agent[i["agent_tg"]] = by_agent.get(i["agent_tg"], 0) + 1
            lines = ["⏰ پیگیری‌ها و هشدارها", "",
                     f"عقب‌افتاده: {len(overdue)} | سررسید امروز: {len(today_items)}"]
            if by_agent:
                lines.append("مشاوران دارای پیگیری عقب‌افتاده: " + "، ".join(
                    f"{_name(data, t)} ({n})" for t, n in by_agent.items()))
            if today_items:
                lines.append("")
                lines.append("📅 امروز باید پیگیری شوند:")
                for i in today_items[:8]:
                    lines.append(
                        f"• {i['client']['name']} ({i['prop']['code']}) — "
                        f"{_name(data, i['agent_tg'])}")
            lines += ["",
                      f"🤝 مذاکره بدون اقدام بعدی ثبت‌شده: {len(al['neg_no_next'])}"
                      + ("".join(f"\n• {p['code']}" for p in al['neg_no_next'][:6])),
                      f"💤 فایل فعال بدون فعالیت ({IDLE_DAYS}+ روز): {len(al['idle_files'])}"
                      + ("".join(f"\n• {p['code']}" for p in al['idle_files'][:6])),
                      f"💤 مشتری فعال بدون فعالیت ({IDLE_DAYS}+ روز): {len(al['idle_clients'])}"
                      + ("".join(f"\n• {c['name']}" for c in al['idle_clients'][:6])),
                      "", "عقب‌افتاده‌ها:"]
            rows = []
            if not chunk:
                lines.append("موردی نیست ✅")
            for i in chunk:
                lines.append(
                    f"• {i['client']['name']} | {i['prop']['code']} | "
                    f"{_name(data, i['agent_tg'])} | موعد {fmt_jalali(i['due'])} "
                    f"({i['days_over']} روز)")
                rows.append([
                    InlineKeyboardButton(
                        text=f"👤 {i['client']['name']}",
                        callback_data=f"copen:{i['client']['id']}"),
                    InlineKeyboardButton(
                        text=f"🏠 {i['prop']['code']}",
                        callback_data=f"popen:{i['prop']['id']}")])
            rows.extend(pagination_keyboard("dsh:fol", page, pages).inline_keyboard)
            rows.append(_back_row())
            await show(msg, "\n".join(lines)[:3900],
                       InlineKeyboardMarkup(inline_keyboard=rows), edit=True)

        elif sec in ("fil", "fc", "fl"):
            await _dash_files(callback, parts)

        elif sec == "ads":
            period, now, data, fol = await _dash_context(tg)
            act = [p for p in data["properties"]
                   if p["status"] in ACTIVE_PROPERTY_STATUSES]
            c = {AD_UNADVERTISED: 0, AD_REVIEW: 0, AD_ADVERTISED: 0, AD_UNKNOWN: 0}
            for p in act:
                c[p["ad"]] = c.get(p["ad"], 0) + 1
            rows = [[InlineKeyboardButton(
                text="📋 پیشنهادهای آگهی‌گذاری", callback_data="adv:home")],
                _back_row()]
            await show(
                msg,
                "📢 آگهی‌گذاری (فایل‌های فعال)\n\n"
                f"⬜ آگهی‌نشده: {c[AD_UNADVERTISED]}\n"
                f"🔄 نیازمند بررسی مجدد: {c[AD_REVIEW]}\n"
                f"❔ وضعیت نامشخص: {c[AD_UNKNOWN]}\n"
                f"✅ آگهی‌شده: {c[AD_ADVERTISED]}\n\n"
                "نامشخص‌ها آگهی‌نشده حساب نمی‌شوند.",
                InlineKeyboardMarkup(inline_keyboard=rows), edit=True)

        elif sec == "con":
            period, now, data, fol = await _dash_context(tg)
            rep = dash_contracts(data, period)
            page = int(parts[2]) if len(parts) > 2 else 1
            pages = max(1, (len(rep["rows"]) + DASH_LIST_PAGE - 1) // DASH_LIST_PAGE)
            page = max(1, min(page, pages))
            chunk = rep["rows"][(page - 1) * DASH_LIST_PAGE: page * DASH_LIST_PAGE]
            total, n_val = rep["amount"]
            ptotal, pn_val = rep["prev_amount"]
            lines = [f"🤝 گزارش قراردادها — {period['label']}", "",
                     f"قراردادهای نهایی‌شده: {rep['count']} "
                     f"(بازه‌ی قبل: {rep['prev_count']})"]
            if n_val:
                lines.append(
                    f"مجموع مبلغ ثبت‌شده: {price_label(total)} "
                    f"(برای {n_val} از {rep['count']} قرارداد مبلغ ثبت شده)")
                if pn_val:
                    lines.append(f"بازه‌ی قبل: {price_label(ptotal)}")
            elif rep["count"]:
                lines.append("مبلغ معامله برای این قراردادها ثبت نشده.")
            lines.append("کمیسیون/درآمد تخمین زده نمی‌شود.")
            if rep["by_agent"]:
                lines.append("به تفکیک مشاور: " + "، ".join(
                    f"{k} ({v})" for k, v in rep["by_agent"]))
            if rep["by_area"]:
                lines.append("به تفکیک منطقه: " + "، ".join(
                    f"{k} ({v})" for k, v in rep["by_area"]))
            if rep["by_deal"]:
                lines.append("به تفکیک نوع معامله: " + "، ".join(
                    f"{k} ({v})" for k, v in rep["by_deal"]))
            lines += ["", "جزئیات:"]
            rows = []
            if not chunk:
                lines.append("قراردادی در این بازه ثبت نشده.")
            for r in chunk:
                p = r["prop"]
                code = p["code"] if p else "—"
                val = price_label(r["value"]) if r["value"] > 0 else "مبلغ ثبت نشده"
                lines.append(
                    f"• {code} | {r['area']} | {r['agent']} | {val} | "
                    f"{fmt_jalali(tehran_today(r['at']))}")
                if p:
                    rows.append([InlineKeyboardButton(
                        text=f"🏠 {code}", callback_data=f"popen:{p['id']}")])
            rows.extend(pagination_keyboard("dsh:con", page, pages).inline_keyboard)
            rows.append(_back_row())
            await show(msg, "\n".join(lines)[:3900],
                       InlineKeyboardMarkup(inline_keyboard=rows), edit=True)

    except Exception as exc:
        print("DASHBOARD ERROR:", repr(exc)[:300])
        await msg.answer("⚠️ خطا در ساخت گزارش؛ دوباره تلاش کن.")
    try:
        await callback.answer()
    except Exception:
        pass


# ---- files status + filters ----

FIL_KINDS = [("all", "همه"), ("incomplete", "ناقص"),
             ("critical", "فاقد اطلاعات مهم"), ("unad", "آگهی‌نشده")]
FIL_AD = [None, AD_UNADVERTISED, AD_REVIEW, AD_ADVERTISED, AD_UNKNOWN]


def _fil_get(tg):
    return DASH_FILTER.setdefault(tg, {
        "kind": "all", "status": None, "area": None, "advisor": None,
        "ad": None})


def _cycle(options, current):
    try:
        i = options.index(current)
    except ValueError:
        i = -1
    return options[(i + 1) % len(options)]


def filter_files(data, flt):
    out = []
    for p in data["properties"]:
        if flt["status"] and p["status"] != flt["status"]:
            continue
        if flt["area"] and p["area"] != flt["area"]:
            continue
        if flt["advisor"] and p["resp_tg"] != flt["advisor"]:
            continue
        if flt["ad"] and p["ad"] != flt["ad"]:
            continue
        k = flt["kind"]
        if k == "incomplete" and not prop_incomplete_missing(p):
            continue
        if k == "critical" and not prop_critical_missing(p):
            continue
        if k == "unad" and p["ad"] not in (AD_UNADVERTISED, AD_REVIEW):
            continue
        out.append(p)
    return out


async def _dash_files(callback, parts):
    tg = callback.from_user.id
    msg = callback.message
    flt = _fil_get(tg)
    period, now, data, fol = await _dash_context(tg)
    sec = parts[1]
    advisors = [None] + sorted({p["resp_tg"] for p in data["properties"]
                                if p["resp_tg"]})
    if sec == "fc":
        field = parts[2]
        if field == "kind":
            flt["kind"] = _cycle([k for k, _ in FIL_KINDS], flt["kind"])
        elif field == "status":
            flt["status"] = _cycle([None] + STATUSES, flt["status"])
        elif field == "area":
            flt["area"] = _cycle([None] + AREAS, flt["area"])
        elif field == "advisor":
            flt["advisor"] = _cycle(advisors, flt["advisor"])
        elif field == "ad":
            flt["ad"] = _cycle(FIL_AD, flt["ad"])
        elif field == "reset":
            flt.update({"kind": "all", "status": None, "area": None,
                        "advisor": None, "ad": None})

    if sec == "fl":
        page = int(parts[2]) if len(parts) > 2 else 1
        files = filter_files(data, flt)
        pages = max(1, (len(files) + DASH_LIST_PAGE - 1) // DASH_LIST_PAGE)
        page = max(1, min(page, pages))
        chunk = files[(page - 1) * DASH_LIST_PAGE: page * DASH_LIST_PAGE]
        lines = [f"🏠 فهرست فایل‌ها — {len(files)} مورد", ""]
        rows = []
        if not chunk:
            lines.append("فایلی با این فیلتر نیست.")
        for p in chunk:
            miss = prop_incomplete_missing(p)
            price = price_short(p["price"]) if p["price"] > 0 else "—"
            lines.append(
                f"• {p['code']} | {p['area'] or '—'} | {p['sqm']:g}م | "
                f"{price} | {p['status']} | "
                f"{AD_STATUS_LABELS.get(p['ad'], '—')}"
                + (f"\n   ناقص: {'، '.join(miss)}" if miss else ""))
            rows.append([InlineKeyboardButton(
                text=f"🏠 {p['code']}", callback_data=f"popen:{p['id']}")])
        lines.append(f"\n(قیمت‌ها {PRICE_UNIT_LABEL})")
        rows.extend(pagination_keyboard("dsh:fl", page, pages).inline_keyboard)
        rows.append([InlineKeyboardButton(
            text="⬅️ فیلترها", callback_data="dsh:fil")])
        await show(msg, "\n".join(lines)[:3900],
                   InlineKeyboardMarkup(inline_keyboard=rows), edit=True)
        return

    by_status = {}
    for p in data["properties"]:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
    lines = ["🏠 وضعیت فایل‌ها", ""]
    for st in STATUSES:
        lines.append(f"{st}: {by_status.get(st, 0)}")
    files = filter_files(data, flt)
    kind_label = dict(FIL_KINDS)[flt["kind"]]
    lines += ["", f"فیلتر فعلی → {len(files)} فایل",
              f"نوع: {kind_label}",
              f"وضعیت: {flt['status'] or 'همه'}",
              f"منطقه: {flt['area'] or 'همه'}",
              f"مشاور: {_name(data, flt['advisor']) if flt['advisor'] else 'همه'}",
              f"آگهی: {AD_STATUS_LABELS.get(flt['ad']) if flt['ad'] else 'همه'}"]
    rows = [
        [InlineKeyboardButton(text=f"نوع: {kind_label}", callback_data="dsh:fc:kind"),
         InlineKeyboardButton(text="وضعیت", callback_data="dsh:fc:status")],
        [InlineKeyboardButton(text="منطقه", callback_data="dsh:fc:area"),
         InlineKeyboardButton(text="مشاور", callback_data="dsh:fc:advisor")],
        [InlineKeyboardButton(text="وضعیت آگهی", callback_data="dsh:fc:ad"),
         InlineKeyboardButton(text="♻️ پاک کردن فیلتر", callback_data="dsh:fc:reset")],
        [InlineKeyboardButton(text="📋 نمایش فهرست", callback_data="dsh:fl:1")],
        _back_row(),
    ]
    await show(msg, "\n".join(lines)[:3900],
               InlineKeyboardMarkup(inline_keyboard=rows), edit=True)


@dp.message(DashForm.custom, F.text)
async def dash_custom_period(message: Message, state: FSMContext):
    if not await dash_guard_msg(message):
        await state.clear()
        return
    dates = parse_all_dates(message.text)
    if len(dates) != 2:
        await message.answer(
            "دو تاریخ معتبر بفرست؛ مثال: ۱۴۰۵/۰۷/۰۱ تا ۱۴۰۵/۰۷/۱۵")
        return
    if (max(dates) - min(dates)).days > 730:
        await message.answer("بازه خیلی طولانی است (حداکثر ۲ سال).")
        return
    DASH_PERIOD[message.from_user.id] = make_period(
        "c", custom=(dates[0], dates[1]))
    await state.clear()
    period, now, data, fol = await _dash_context(message.from_user.id)
    sm = dash_summary(data, period, now, fol)
    await message.answer(
        render_summary(sm, period), reply_markup=main_menu(message.from_user.id))
    await message.answer(
        "داشبورد 👇", reply_markup=dash_home_markup())


# ---------------------------------------------------------
# ⏰ DAILY 10:00 REMINDER (Asia/Tehran, at-most-once per day)
# ---------------------------------------------------------

REMINDER_HOUR = 10
REMINDER_LAST_HOUR = 21
REMINDER_DONE_DAY = {"day": None}


def reminder_build(fol, tg):
    """Pure: text for one advisor, or None when there is nothing to say."""
    mine = [i for i in fol["dated"]
            if i["agent_tg"] == tg and i["kind"] in ("overdue", "today")]
    if not mine:
        return None, 0
    overdue = [i for i in mine if i["kind"] == "overdue"]
    today_items = [i for i in mine if i["kind"] == "today"]
    lines = ["⏰ یادآوری پیگیری‌های امروز", ""]
    if today_items:
        lines.append("📅 سررسید امروز:")
        for i in today_items[:10]:
            lines.append(f"• {i['client']['name']} — فایل {i['prop']['code']}")
    if overdue:
        lines.append("")
        lines.append("⚠️ عقب‌افتاده:")
        for i in sorted(overdue, key=lambda x: -x["days_over"])[:10]:
            lines.append(
                f"• {i['client']['name']} — فایل {i['prop']['code']} "
                f"({i['days_over']} روز)")
    return "\n".join(lines), len(mine)


async def reminder_tick(now_utc=None):
    now_utc = now_utc or utcnow_naive()
    local = now_utc + TEHRAN_OFFSET
    if not (REMINDER_HOUR <= local.hour < REMINDER_LAST_HOUR):
        return
    day = local.strftime("%Y-%m-%d")
    if REMINDER_DONE_DAY["day"] == day:
        return
    period = make_period("m", today=local.date())
    data = await dash_load(period)
    fol = dash_followups(data, now_utc)
    tgs = {i["agent_tg"] for i in fol["dated"]}
    for tg in tgs:
        if not tg or not is_allowed(tg):
            continue
        text, n = reminder_build(fol, tg)
        if not text:
            continue
        try:
            async with SessionLocal() as session:
                session.add(ReminderLog(tg_id=tg, day=day, items=n))
                await session.commit()
        except IntegrityError:
            continue  # already reminded today (e.g. before a restart)
        except Exception as exc:
            print("REMINDER LOG ERROR:", repr(exc)[:200])
            continue
        try:
            await bot.send_message(tg, text)
        except Exception as exc:
            print("REMINDER SEND ERROR:", type(exc).__name__)
    REMINDER_DONE_DAY["day"] = day


async def reminder_loop():
    await asyncio.sleep(20)
    while True:
        try:
            await reminder_tick()
        except Exception as exc:
            print("REMINDER LOOP ERROR:", repr(exc)[:200])
        await asyncio.sleep(60)


# ---------------------------------------------------------
# 🤖 «شهردار ایران‌زمین» assistant chat (grounded, no actions)
# ---------------------------------------------------------

class AssistantForm(StatesGroup):
    chat = State()


async def mayor_context(tg_id):
    """Short factual summary of THIS advisor's real data."""
    try:
        period = make_period("m")
        data = await dash_load(period)
        fol = dash_followups(data, utcnow_naive())
        mine_files = [p for p in data["properties"]
                      if p["created_by"] == tg_id
                      and p["status"] in ACTIVE_PROPERTY_STATUSES]
        mine_clients = [c for c in data["clients"]
                        if c["created_by"] == tg_id
                        and c["status"] in ACTIVE_CLIENT_STATUSES]
        overdue = [i for i in fol["dated"]
                   if i["agent_tg"] == tg_id and i["kind"] == "overdue"]
        today_items = [i for i in fol["dated"]
                       if i["agent_tg"] == tg_id and i["kind"] == "today"]
        return (
            f"فایل‌های فعال این مشاور: {len(mine_files)}\n"
            f"مشتریان فعال این مشاور: {len(mine_clients)}\n"
            f"پیگیری عقب‌افتاده: {len(overdue)}\n"
            f"پیگیری سررسید امروز: {len(today_items)}"
        )
    except Exception as exc:
        print("MAYOR CONTEXT ERROR:", repr(exc)[:200])
        return "داده‌ای در دسترس نیست."


async def mayor_start(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    await state.clear()
    if not ai_available():
        await message.answer(
            f"🤖 {MAYOR_NAME}\n\n{MAYOR_INTRO}\n\n{AI_UNAVAILABLE_TEXT}"
        )
        return
    ctx = await mayor_context(message.from_user.id)
    await state.set_state(AssistantForm.chat)
    await state.update_data(ctx=ctx, history=[])
    await message.answer(
        f"🤖 {MAYOR_NAME}\n\n{MAYOR_INTRO}\n\n"
        "سؤالت را بنویس. (برای خروج: «⬅️ بازگشت»)",
        reply_markup=keyboard([["⬅️ بازگشت"]], include_cancel=False),
    )


@dp.message(AssistantForm.chat, F.text)
async def mayor_chat(message: Message, state: FSMContext):
    if not await access_required(message):
        return
    data = await state.get_data()
    history = list(data.get("history") or [])[-6:]
    ctx = data.get("ctx") or ""
    convo = "\n".join(f"{r}: {t}" for r, t in history)
    prompt = (
        "داده‌ی واقعی این مشاور (تنها منبع مجاز اعداد):\n"
        f"{ctx}\n\n"
        + (f"گفتگوی قبلی:\n{convo}\n\n" if convo else "")
        + f"پیام مشاور: {message.text.strip()[:1500]}"
    )
    try:
        reply = await gemini_generate(
            [{"text": prompt}], system=MAYOR_SYSTEM, temperature=0.4,
            timeout=45, label="mayor")
    except AIError as exc:
        await message.answer(exc.user_message)
        return
    reply = reply[:3500]
    history += [("مشاور", message.text.strip()[:500]),
                (MAYOR_NAME, reply[:500])]
    await state.update_data(history=history[-8:])
    await message.answer(reply)


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
    await backfill_status_events()
    asyncio.create_task(reminder_loop())

    print(
        "🏙️ Hooman Real Estate CRM started."
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":
    asyncio.run(main())
