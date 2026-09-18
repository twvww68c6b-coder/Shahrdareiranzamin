import os
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Text,
    select,
    func,
    inspect,
    text as sql_text,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

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
    DATABASE_URL = "sqlite+aiosqlite:///crm.db"


engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


# =========================================================
# DATABASE
# =========================================================

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200)
    )

    role: Mapped[str] = mapped_column(
        String(50),
        default="agent",
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
        String(100),
        unique=True,
        index=True,
    )

    area: Mapped[str] = mapped_column(
        String(200)
    )

    sqm: Mapped[float] = mapped_column(
        Float
    )

    price: Mapped[float] = mapped_column(
        Float
    )

    property_type: Mapped[str] = mapped_column(
        String(100)
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
        default=1,
    )

    elevator: Mapped[str] = mapped_column(
        String(20),
        default="ندارد",
    )

    parking: Mapped[str] = mapped_column(
        String(20),
        default="ندارد",
    )

    parking_type: Mapped[str] = mapped_column(
        String(50),
        default="",
    )

    storage: Mapped[str] = mapped_column(
        String(20),
        default="ندارد",
    )

    tenant: Mapped[str] = mapped_column(
        String(20),
        default="ندارد",
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
        String(200)
    )

    owner_phone: Mapped[str] = mapped_column(
        String(50)
    )

    description: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="فعال",
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
    )


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(200)
    )

    phone: Mapped[str] = mapped_column(
        String(50)
    )

    area: Mapped[str] = mapped_column(
        String(200),
        default="",
    )

    min_sqm: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    max_sqm: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    min_budget: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    max_budget: Mapped[float] = mapped_column(
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

    description: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    created_by: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    property_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    client_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    agent_id: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    visited_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    interest: Mapped[str] = mapped_column(
        String(50),
        default="",
    )

    price_reaction: Mapped[str] = mapped_column(
        String(50),
        default="",
    )

    property_reaction: Mapped[str] = mapped_column(
        String(50),
        default="",
    )

    objection: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    next_action: Mapped[str] = mapped_column(
        String(100),
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

    outcome: Mapped[str] = mapped_column(
        Text,
        default="",
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
    )

    property_id: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    client_id: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    activity_type: Mapped[str] = mapped_column(
        String(100)
    )

    note: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


# =========================================================
# FSM STATES
# =========================================================

class PropertyForm(StatesGroup):
    code = State()
    area = State()
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
    bedrooms = State()
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


# =========================================================
# KEYBOARDS
# =========================================================

def kb(rows):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=x) for x in row]
            for row in rows
        ],
        resize_keyboard=True,
    )


def inline(rows):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text_,
                    callback_data=data_,
                )
                for text_, data_ in row
            ]
            for row in rows
        ]
    )


MAIN = kb([
    ["🏠 فایل‌ها", "👤 مشتری‌ها"],
    ["➕ ثبت فایل", "➕ ثبت مشتری"],
    ["👀 ثبت بازدید", "📞 پیگیری"],
    ["🔎 پیشنهاد فایل", "📝 آخرین فعالیت‌ها"],
    ["📊 KPI من", "👥 KPI تیم"],
])

CANCEL = kb([
    ["❌ لغو"]
])


def bedrooms_keyboard():
    return kb([
        ["۰", "۱", "۲", "۳"],
        ["۴", "۵", "+۵"],
        ["❌ لغو"],
    ])


def units_keyboard():
    return kb([
        ["۱", "۲", "۳", "۴"],
        ["+۴"],
        ["❌ لغو"],
    ])


def floor_keyboard():
    return kb([
        ["همکف", "۱", "۲", "۳", "۴", "۵"],
        ["۶", "۷", "۸", "۹", "۱۰"],
        ["۱۱", "۱۲", "۱۳", "۱۴", "۱۵"],
        ["۱۶", "۱۷", "۱۸", "۱۹", "۲۰"],
        ["+۲۰", "❌ لغو"],
    ])


# =========================================================
# STATUS
# =========================================================

STATUS_NAMES = {
    "فعال": "🟢 فعال",
    "در مذاکره": "🟡 در مذاکره",
    "معامله شد - توسط ما": "🔵 معامله شد - توسط ما",
    "معامله شد - توسط دیگری": "🟣 معامله شد - توسط دیگری",
    "منصرف شد": "🔴 منصرف شد",
    "غیرفعال": "⚫ غیرفعال",
}


# =========================================================
# HELPERS
# =========================================================

def now():
    return datetime.utcnow()


def money(value):
    if not value:
        return "—"

    return f"{value:,.0f}"


async def get_user(
    session: AsyncSession,
    telegram_user,
):
    result = await session.execute(
        select(User).where(
            User.telegram_id == telegram_user.id
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_user.id,
            name=telegram_user.full_name or "کاربر",
        )

        session.add(user)
        await session.commit()

    return user


async def add_activity(
    session,
    user_id,
    activity_type,
    note="",
    property_id=None,
    client_id=None,
):
    session.add(
        Activity(
            user_id=user_id,
            activity_type=activity_type,
            note=note,
            property_id=property_id,
            client_id=client_id,
        )
    )


async def owner_count(
    session,
    owner_name,
    owner_phone,
):
    query = select(
        func.count(Property.id)
    ).where(
        Property.owner_name == owner_name,
        Property.owner_phone == owner_phone,
    )

    result = await session.execute(query)

    return int(result.scalar() or 0)


async def owner_files(
    session,
    owner_name,
    owner_phone,
):
    query = select(Property).where(
        Property.owner_name == owner_name,
        Property.owner_phone == owner_phone,
    ).order_by(
        Property.created_at.desc()
    )

    result = await session.execute(query)

    return list(result.scalars().all())


# =========================================================
# MIGRATION
# =========================================================

async def migrate():
    async with engine.begin() as conn:

        await conn.run_sync(
            Base.metadata.create_all
        )

        def sync_migrate(connection):

            inspector = inspect(connection)

            tables = inspector.get_table_names()

            if "properties" not in tables:
                return

            columns = {
                column["name"]
                for column in inspector.get_columns(
                    "properties"
                )
            }

            additions = {
                "unit_floor": "INTEGER DEFAULT 0",
                "status": "VARCHAR(50) DEFAULT 'فعال'",
                "transaction_value": "DOUBLE PRECISION DEFAULT 0",
                "updated_at": "TIMESTAMP",
            }

            for column_name, column_type in additions.items():

                if column_name not in columns:

                    connection.execute(
                        sql_text(
                            f"""
                            ALTER TABLE properties
                            ADD COLUMN {column_name}
                            {column_type}
                            """
                        )
                    )

        await conn.run_sync(sync_migrate)


# =========================================================
# BOT
# =========================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):

    async with SessionLocal() as session:

        user = await get_user(
            session,
            message.from_user,
        )

        await message.answer(
            f"""
🏙️ <b>شهردار ایران‌زمین | Hooman Real Estate</b>

سلام {user.name} 👋

CRM فایل، مالک، مشتری، بازدید و معامله آماده است.
""",
            reply_markup=MAIN,
        )


# =========================================================
# CANCEL
# =========================================================

@dp.message(F.text == "❌ لغو")
async def cancel(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await message.answer(
        "❌ عملیات لغو شد.",
        reply_markup=MAIN,
    )


# =========================================================
# ADD PROPERTY
# =========================================================

@dp.message(F.text == "➕ ثبت فایل")
async def add_property(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await state.set_state(
        PropertyForm.code
    )

    await message.answer(
        "🔢 کد فایل را وارد کن:",
        reply_markup=CANCEL,
    )


@dp.message(PropertyForm.code)
async def p_code(
    message: Message,
    state: FSMContext,
):

    code = message.text.strip()

    async with SessionLocal() as session:

        exists = (
            await session.execute(
                select(Property).where(
                    Property.code == code
                )
            )
        ).scalar_one_or_none()

        if exists:

            await message.answer(
                "⚠️ این کد فایل قبلاً ثبت شده.\n"
                "یک کد دیگر وارد کن."
            )

            return

    await state.update_data(
        code=code
    )

    await state.set_state(
        PropertyForm.area
    )

    await message.answer(
        "📍 منطقه / محله:"
    )


@dp.message(PropertyForm.area)
async def p_area(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        area=message.text.strip()
    )

    await state.set_state(
        PropertyForm.sqm
    )

    await message.answer(
        "📐 متراژ را وارد کن:"
    )


@dp.message(PropertyForm.sqm)
async def p_sqm(
    message: Message,
    state: FSMContext,
):

    try:

        value = float(
            message.text.replace(",", "")
        )

    except:

        await message.answer(
            "⚠️ فقط عدد وارد کن."
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
async def p_price(
    message: Message,
    state: FSMContext,
):

    try:

        value = float(
            message.text.replace(",", "")
        )

    except:

        await message.answer(
            "⚠️ فقط عدد وارد کن."
        )

        return

    await state.update_data(
        price=value
    )

    await state.set_state(
        PropertyForm.property_type
    )

    await message.answer(
        "🏷 نوع ملک را وارد کن:"
    )


@dp.message(PropertyForm.property_type)
async def p_type(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        property_type=message.text.strip()
    )

    await state.set_state(
        PropertyForm.bedrooms
    )

    await message.answer(
        "🛏 تعداد خواب:",
        reply_markup=bedrooms_keyboard(),
    )


@dp.message(PropertyForm.bedrooms)
async def p_bedrooms(
    message: Message,
    state: FSMContext,
):

    value_text = message.text.strip()

    if value_text == "+۵":

        await message.answer(
            "تعداد خواب را عددی وارد کن:"
        )

        return

    try:

        value = int(value_text)

        if value < 0:
            raise ValueError

    except:

        await message.answer(
            "یکی از گزینه‌ها را انتخاب کن."
        )

        return

    await state.update_data(
        bedrooms=value
    )

    await state.set_state(
        PropertyForm.floors
    )

    await message.answer(
        "🏢 تعداد کل طبقات ساختمان را وارد کن:",
        reply_markup=CANCEL,
    )


@dp.message(PropertyForm.floors)
async def p_floors(
    message: Message,
    state: FSMContext,
):

    try:

        value = int(
            message.text.strip()
        )

        if value < 0:
            raise ValueError

    except:

        await message.answer(
            "⚠️ تعداد طبقات را به صورت عدد وارد کن."
        )

        return

    await state.update_data(
        floors=value
    )

    await state.set_state(
        PropertyForm.unit_floor
    )

    await message.answer(
        "🏢 ملک طبقه چندمه؟",
        reply_markup=floor_keyboard(),
    )


@dp.message(PropertyForm.unit_floor)
async def p_unit_floor(
    message: Message,
    state: FSMContext,
):

    value_text = message.text.strip()

    if value_text == "همکف":

        value = 0

    elif value_text == "+۲۰":

        await message.answer(
            "شماره طبقه را وارد کن:"
        )

        return

    else:

        try:

            value = int(value_text)

            if value < 0:
                raise ValueError

        except:

            await message.answer(
                "یکی از گزینه‌های طبقه را انتخاب کن."
            )

            return

    await state.update_data(
        unit_floor=value
    )

    await state.set_state(
        PropertyForm.units_per_floor
    )

    await message.answer(
        "🏗 چند واحد در هر طبقه؟",
        reply_markup=units_keyboard(),
    )


@dp.message(PropertyForm.units_per_floor)
async def p_units(
    message: Message,
    state: FSMContext,
):

    value_text = message.text.strip()

    if value_text == "+۴":

        await message.answer(
            "تعداد واحد در طبقه را عددی وارد کن:"
        )

        return

    try:

        value = int(value_text)

        if value < 1:
            raise ValueError

    except:

        await message.answer(
            "یکی از گزینه‌ها را انتخاب کن."
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
        reply_markup=kb([
            ["دارد", "ندارد"],
            ["❌ لغو"],
        ]),
    )


@dp.message(PropertyForm.elevator)
async def p_elevator(
    message: Message,
    state: FSMContext,
):

    if message.text not in (
        "دارد",
        "ندارد",
    ):

        await message.answer(
            "دارد یا ندارد؟"
        )

        return

    await state.update_data(
        elevator=message.text
    )

    await state.set_state(
        PropertyForm.parking
    )

    await message.answer(
        "🚗 پارکینگ؟",
        reply_markup=kb([
            ["دارد", "ندارد"],
            ["❌ لغو"],
        ]),
    )


@dp.message(PropertyForm.parking)
async def p_parking(
    message: Message,
    state: FSMContext,
):

    if message.text not in (
        "دارد",
        "ندارد",
    ):

        await message.answer(
            "دارد یا ندارد؟"
        )

        return

    await state.update_data(
        parking=message.text
    )

    if message.text == "دارد":

        await state.set_state(
            PropertyForm.parking_type
        )

        await message.answer(
            "نوع پارکینگ؟",
            reply_markup=kb([
                ["غیرمزاحم", "مزاحم"],
                ["❌ لغو"],
            ]),
        )

    else:

        await state.update_data(
            parking_type=""
        )

        await state.set_state(
            PropertyForm.storage
        )

        await message.answer(
            "📦 انباری؟",
            reply_markup=kb([
                ["دارد", "ندارد"],
                ["❌ لغو"],
            ]),
        )


@dp.message(PropertyForm.parking_type)
async def p_parking_type(
    message: Message,
    state: FSMContext,
):

    if message.text not in (
        "غیرمزاحم",
        "مزاحم",
    ):

        await message.answer(
            "یکی از گزینه‌ها را انتخاب کن."
        )

        return

    await state.update_data(
        parking_type=message.text
    )

    await state.set_state(
        PropertyForm.storage
    )

    await message.answer(
        "📦 انباری؟",
        reply_markup=kb([
            ["دارد", "ندارد"],
            ["❌ لغو"],
        ]),
    )


@dp.message(PropertyForm.storage)
async def p_storage(
    message: Message,
    state: FSMContext,
):

    if message.text not in (
        "دارد",
        "ندارد",
    ):

        await message.answer(
            "دارد یا ندارد؟"
        )

        return

    await state.update_data(
        storage=message.text
    )

    await state.set_state(
        PropertyForm.tenant
    )

    await message.answer(
        "👤 مستأجر دارد؟",
        reply_markup=kb([
            ["دارد", "ندارد"],
            ["❌ لغو"],
        ]),
    )


@dp.message(PropertyForm.tenant)
async def p_tenant(
    message: Message,
    state: FSMContext,
):

    if message.text not in (
        "دارد",
        "ندارد",
    ):

        await message.answer(
            "دارد یا ندارد؟"
        )

        return

    await state.update_data(
        tenant=message.text
    )

    if message.text == "دارد":

        await state.set_state(
            PropertyForm.deposit
        )

        await message.answer(
            "💵 ودیعه:"
        )

    else:

        await state.update_data(
            deposit=0,
            rent=0,
            vacancy_date="",
        )

        await state.set_state(
            PropertyForm.document_type
        )

        await message.answer(
            "📄 نوع سند:",
            reply_markup=kb([
                ["تک‌برگ", "اوقافی", "قدیمی"],
                ["منگوله‌دار", "قولنامه‌ای", "سایر"],
                ["❌ لغو"],
            ]),
        )


@dp.message(PropertyForm.deposit)
async def p_deposit(
    message: Message,
    state: FSMContext,
):

    try:

        value = float(
            message.text.replace(",", "")
        )

    except:

        await message.answer(
            "⚠️ فقط عدد وارد کن."
        )

        return

    await state.update_data(
        deposit=value
    )

    await state.set_state(
        PropertyForm.rent
    )

    await message.answer(
        "💵 اجاره ماهانه:"
    )


@dp.message(PropertyForm.rent)
async def p_rent(
    message: Message,
    state: FSMContext,
):

    try:

        value = float(
            message.text.replace(",", "")
        )

    except:

        await message.answer(
            "⚠️ فقط عدد وارد کن."
        )

        return

    await state.update_data(
        rent=value
    )

    await state.set_state(
        PropertyForm.vacancy_date
    )

    await message.answer(
        "📅 تاریخ تخلیه / وضعیت تخلیه:"
    )


@dp.message(PropertyForm.vacancy_date)
async def p_vacancy(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        vacancy_date=message.text.strip()
    )

    await state.set_state(
        PropertyForm.document_type
    )

    await message.answer(
        "📄 نوع سند:",
        reply_markup=kb([
            ["تک‌برگ", "اوقافی", "قدیمی"],
            ["منگوله‌دار", "قولنامه‌ای", "سایر"],
            ["❌ لغو"],
        ]),
    )


@dp.message(PropertyForm.document_type)
async def p_document(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        document_type=message.text.strip()
    )

    await state.set_state(
        PropertyForm.owner_name
    )

    await message.answer(
        "👨 مالک / سازنده:"
    )


@dp.message(PropertyForm.owner_name)
async def p_owner_name(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        owner_name=message.text.strip()
    )

    await state.set_state(
        PropertyForm.owner_phone
    )

    await message.answer(
        "📞 شماره مالک:"
    )


@dp.message(PropertyForm.owner_phone)
async def p_owner_phone(
    message: Message,
    state: FSMContext,
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
async def p_description(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        description=message.text.strip()
    )

    data = await state.get_data()

    await state.set_state(
        PropertyForm.confirmation
    )

    preview = f"""
📋 <b>پیش‌نمایش فایل</b>

🔢 کد: {data["code"]}
📍 منطقه: {data["area"]}
📐 متراژ: {data["sqm"]:g}
💰 قیمت: {money(data["price"])}
🏷 نوع: {data["property_type"]}
🛏 خواب: {data["bedrooms"]}
🏢 طبقه: {data["unit_floor"] or "همکف"} از {data["floors"]}
🏗 واحد در طبقه: {data["units_per_floor"]}

🛗 آسانسور: {data["elevator"]}
🚗 پارکینگ: {data["parking"]} {data.get("parking_type", "")}
📦 انباری: {data["storage"]}

👤 مستأجر: {data["tenant"]}

📄 سند: {data["document_type"]}

👨 مالک: {data["owner_name"]}
📞 {data["owner_phone"]}

📝 {data["description"]}
"""

    await message.answer(
        preview,
        reply_markup=kb([
            ["✅ ثبت نهایی"],
            ["✏️ اصلاح", "❌ لغو"],
        ]),
    )


@dp.message(PropertyForm.confirmation)
async def p_confirmation(
    message: Message,
    state: FSMContext,
):

    if message.text == "✏️ اصلاح":

        await message.answer(
            "برای اصلاح از صفحه فایل استفاده کن.\n"
            "بعد از ثبت فایل، همه فیلدهای اصلی قابل ویرایش هستند."
        )

        return

    if message.text != "✅ ثبت نهایی":

        await message.answer(
            "یکی از گزینه‌ها را انتخاب کن."
        )

        return

    data = await state.get_data()

    async with SessionLocal() as session:

        user = await get_user(
            session,
            message.from_user,
        )

        exists = (
            await session.execute(
                select(Property).where(
                    Property.code == data["code"]
                )
            )
        ).scalar_one_or_none()

        if exists:

            await message.answer(
                "⚠️ این کد همین الان توسط شخص دیگری ثبت شده."
            )

            await state.clear()

            return

        property_ = Property(
            code=data["code"],
            area=data["area"],
            sqm=data["sqm"],
            price=data["price"],
            property_type=data["property_type"],
            bedrooms=data["bedrooms"],
            floors=data["floors"],
            unit_floor=data["unit_floor"],
            units_per_floor=data["units_per_floor"],
            elevator=data["elevator"],
            parking=data["parking"],
            parking_type=data.get(
                "parking_type",
                "",
            ),
            storage=data["storage"],
            tenant=data["tenant"],
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
            document_type=data["document_type"],
            owner_name=data["owner_name"],
            owner_phone=data["owner_phone"],
            description=data["description"],
            status="فعال",
            transaction_value=0,
            created_by=user.telegram_id,
            updated_at=now(),
        )

        session.add(property_)

        await session.flush()

        await add_activity(
            session,
            user.id,
            "ثبت فایل",
            "ثبت اولیه فایل",
            property_.id,
        )

        await session.commit()

        count = await owner_count(
            session,
            property_.owner_name,
            property_.owner_phone,
        )

        await message.answer(
            f"""
✅ <b>فایل {property_.code} ثبت شد.</b>

🟢 وضعیت: فعال

👤 مالک:
{property_.owner_name}

📂 تعداد فایل‌های این مالک:
<b>{count}</b>

👨‍💼 ثبت‌کننده:
{user.name}
""",
            reply_markup=MAIN,
        )

    await state.clear()


# =========================================================
# FILE LIST
# =========================================================

@dp.message(F.text == "🏠 فایل‌ها")
async def files(message: Message):

    async with SessionLocal() as session:

        properties = list(
            (
                await session.execute(
                    select(Property)
                    .order_by(
                        Property.created_at.desc()
                    )
                    .limit(50)
                )
            ).scalars().all()
        )

        if not properties:

            await message.answer(
                "هنوز فایلی ثبت نشده.",
                reply_markup=MAIN,
            )

            return

        rows = []

        for property_ in properties:

            button_text = (
                f"{STATUS_NAMES.get(property_.status, property_.status)} | "
                f"{property_.code} | "
                f"{property_.sqm:g}م | "
                f"{money(property_.price)}"
            )

            rows.append([
                (
                    button_text,
                    f"property:view:{property_.id}",
                )
            ])

        await message.answer(
            "🏠 <b>فایل‌ها</b>\n\n"
            "برای مشاهده جزئیات، روی فایل بزن:",
            reply_markup=inline(rows),
        )


@dp.callback_query(
    F.data == "property:list"
)
async def property_list_callback(
    call: CallbackQuery,
):

    await call.answer()

    await files(
        call.message
    )


# =========================================================
# PROPERTY DETAIL
# =========================================================

async def property_text(
    session,
    property_,
):

    creator = (
        await session.execute(
            select(User).where(
                User.telegram_id ==
                property_.created_by
            )
        )
    ).scalar_one_or_none()

    count = await owner_count(
        session,
        property_.owner_name,
        property_.owner_phone,
    )

    creator_name = (
        creator.name
        if creator
        else "نامشخص"
    )

    tenant_text = property_.tenant

    if property_.tenant == "دارد":

        tenant_text += (
            f"\n💵 ودیعه: {money(property_.deposit)}"
            f"\n💵 اجاره: {money(property_.rent)}"
            f"\n📅 تخلیه: {property_.vacancy_date}"
        )

    transaction = ""

    if property_.transaction_value:

        transaction = (
            f"\n💰 ارزش معامله: "
            f"{money(property_.transaction_value)}"
        )

    return f"""
🏠 <b>فایل {property_.code}</b>

📌 وضعیت:
<b>{STATUS_NAMES.get(property_.status, property_.status)}</b>
{transaction}

📍 منطقه: {property_.area}
📐 متراژ: {property_.sqm:g} متر
💰 قیمت: {money(property_.price)}

🏷 نوع ملک: {property_.property_type}
🛏 خواب: {property_.bedrooms}

🏢 طبقه:
{property_.unit_floor or "همکف"} از {property_.floors}

🏗 واحد در طبقه:
{property_.units_per_floor}

🛗 آسانسور:
{property_.elevator}

🚗 پارکینگ:
{property_.parking}
{property_.parking_type}

📦 انباری:
{property_.storage}

👤 مستأجر:
{tenant_text}

📄 سند:
{property_.document_type}

👨 مالک:
{property_.owner_name}

📞 {property_.owner_phone}

📂 تعداد فایل‌های همین مالک:
<b>{count}</b>

👨‍💼 ثبت‌کننده:
{creator_name}

🕒 تاریخ ثبت:
{property_.created_at.strftime("%Y-%m-%d %H:%M")}

📝 توضیحات:
{property_.description or "—"}
"""


def property_actions(
    property_id,
):

    return inline([
        [
            (
                "✏️ ویرایش",
                f"property:edit:{property_id}",
            ),
            (
                "🔄 وضعیت",
                f"property:status:{property_id}",
            ),
        ],
        [
            (
                "📜 تاریخچه",
                f"property:history:{property_id}",
            ),
            (
                "📌 رویداد جدید",
                f"property:event:{property_id}",
            ),
        ],
        [
            (
                "👤 فایل‌های همین مالک",
                f"property:owner:{property_id}",
            )
        ],
        [
            (
                "🔙 بازگشت",
                "property:list",
            )
        ],
    ])


@dp.callback_query(
    F.data.startswith("property:view:")
)
async def property_view(
    call: CallbackQuery,
):

    property_id = int(
        call.data.split(":")[2]
    )

    async with SessionLocal() as session:

        property_ = await session.get(
            Property,
            property_id,
        )

        if not property_:

            await call.answer(
                "فایل پیدا نشد.",
                show_alert=True,
            )

            return

        await call.message.edit_text(
            await property_text(
                session,
                property_,
            ),
            reply_markup=property_actions(
                property_id
            ),
        )

    await call.answer()


# =========================================================
# OWNER FILES
# =========================================================

@dp.callback_query(
    F.data.startswith("property:owner:")
)
async def property_owner(
    call: CallbackQuery,
):

    property_id = int(
        call.data.split(":")[2]
    )

    async with SessionLocal() as session:

        property_ = await session.get(
            Property,
            property_id,
        )

        if not property_:

            await call.answer(
                "فایل پیدا نشد.",
                show_alert=True,
            )

            return

        owner_properties = await owner_files(
            session,
            property_.owner_name,
            property_.owner_phone,
        )

        rows = []

        for item in owner_properties:

            rows.append([
                (
                    f"{STATUS_NAMES.get(item.status, item.status)} | "
                    f"{item.code} | "
                    f"{item.sqm:g}م",
                    f"property:view:{item.id}",
                )
            ])

        rows.append([
            (
                "🔙 برگشت",
                f"property:view:{property_id}",
            )
        ])

        await call.message.edit_text(
            f"""
👤 <b>فایل‌های مالک</b>

نام:
{property_.owner_name}

📞 {property_.owner_phone}

📂 تعداد فایل:
<b>{len(owner_properties)}</b>
""",
            reply_markup=inline(rows),
        )

    await call.answer()


# =========================================================
# STATUS
# =========================================================

@dp.callback_query(
    F.data.startswith("property:status:")
)
async def property_status(
    call: CallbackQuery,
    state: FSMContext,
):

    property_id = int(
        call.data.split(":")[2]
    )

    await state.clear()

    await state.update_data(
        property_id=property_id
    )

    await state.set_state(
        StatusForm.status
    )

    await call.message.answer(
        "🔄 وضعیت جدید فایل را انتخاب کن:",
        reply_markup=kb([
            ["فعال", "در مذاکره"],
            [
                "معامله شد - توسط ما",
                "معامله شد - توسط دیگری",
            ],
            [
                "منصرف شد",
                "غیرفعال",
            ],
            ["❌ لغو"],
        ]),
    )

    await call.answer()


@dp.message(StatusForm.status)
async def status_set(
    message: Message,
    state: FSMContext,
):

    if message.text not in STATUS_NAMES:

        await message.answer(
            "یکی از وضعیت‌ها را انتخاب کن."
        )

        return

    data = await state.get_data()

    await state.update_data(
        status=message.text
    )

    if message.text == "معامله شد - توسط ما":

        await state.set_state(
            StatusForm.transaction_value
        )

        await message.answer(
            "💰 ارزش معامله را وارد کن.\n"
            "اگر نمی‌خواهی ثبت کنی، ۰ وارد کن:"
        )

        return

    async with SessionLocal() as session:

        property_ = await session.get(
            Property,
            data["property_id"],
        )

        if not property_:

            await state.clear()

            await message.answer(
                "فایل پیدا نشد.",
                reply_markup=MAIN,
            )

            return

        old_status = property_.status

        property_.status = message.text

        property_.updated_at = now()

        user = await get_user(
            session,
            message.from_user,
        )

        await add_activity(
            session,
            user.id,
            "تغییر وضعیت",
            f"{old_status} → {property_.status}",
            property_.id,
        )

        await session.commit()

        await message.answer(
            f"""
✅ وضعیت فایل تغییر کرد.

قبل:
{STATUS_NAMES.get(old_status, old_status)}

بعد:
{STATUS_NAMES.get(property_.status, property_.status)}
""",
            reply_markup=MAIN,
        )

    await state.clear()


@dp.message(
    StatusForm.transaction_value
)
async def status_transaction_value(
    message: Message,
    state: FSMContext,
):

    try:

        value = float(
            message.text.replace(",", "")
        )

    except:

        await message.answer(
            "⚠️ فقط عدد وارد کن."
        )

        return

    data = await state.get_data()

    async with SessionLocal() as session:

        property_ = await session.get(
            Property,
            data["property_id"],
        )

        if not property_:

            await state.clear()

            await message.answer(
                "فایل پیدا نشد.",
                reply_markup=MAIN,
            )

            return

        old_status = property_.status

        property_.status = (
            "معامله شد - توسط ما"
        )

        property_.transaction_value = value

        property_.updated_at = now()

        user = await get_user(
            session,
            message.from_user,
        )

        await add_activity(
            session,
            user.id,
            "معامله",
            (
                f"{old_status} → معامله شد توسط ما | "
                f"ارزش معامله: {money(value)}"
            ),
            property_.id,
        )

        await session.commit()

        await message.answer(
            "🔵 معامله با موفقیت ثبت شد.\n\n"
            "وضعیت: معامله شد - توسط ما",
            reply_markup=MAIN,
        )

    await state.clear()


# =========================================================
# EDIT PROPERTY
# =========================================================

EDIT_FIELDS = {
    "price": "قیمت",
    "sqm": "متراژ",
    "area": "منطقه",
    "bedrooms": "خواب",
    "unit_floor": "طبقه ملک",
    "floors": "تعداد کل طبقات",
    "units_per_floor": "واحد در طبقه",
    "tenant": "مستأجر",
    "deposit": "ودیعه",
    "rent": "اجاره",
    "vacancy_date": "تاریخ تخلیه",
    "document_type": "نوع سند",
    "owner_name": "نام مالک",
    "owner_phone": "شماره مالک",
    "description": "توضیحات",
}


@dp.callback_query(
    F.data.startswith("property:edit:")
)
async def property_edit_menu(
    call: CallbackQuery,
):

    property_id = int(
        call.data.split(":")[2]
    )

    rows = []

    items = list(
        EDIT_FIELDS.items()
    )

    for index in range(
        0,
        len(items),
        2,
    ):

        row = []

        for field, label in items[
            index:index + 2
        ]:

            row.append(
                (
                    f"✏️ {label}",
                    f"editfield:{property_id}:{field}",
                )
            )

        rows.append(row)

    rows.append([
        (
            "🔙 برگشت",
            f"property:view:{property_id}",
        )
    ])

    await call.message.edit_reply_markup(
        reply_markup=inline(rows)
    )

    await call.answer()


@dp.callback_query(
    F.data.startswith("editfield:")
)
async def edit_field(
    call: CallbackQuery,
    state: FSMContext,
):

    _, property_id, field = (
        call.data.split(":")
    )

    await state.clear()

    await state.update_data(
        property_id=int(property_id),
        field=field,
    )

    await state.set_state(
        EditForm.value
    )

    await call.message.answer(
        f"✏️ مقدار جدید «{EDIT_FIELDS[field]}» را وارد کن:",
        reply_markup=CANCEL,
    )

    await call.answer()


@dp.message(EditForm.value)
async def edit_value(
    message: Message,
    state: FSMContext,
):

    data = await state.get_data()

    field = data["field"]

    property_id = data["property_id"]

    async with SessionLocal() as session:

        property_ = await session.get(
            Property,
            property_id,
        )

        if not property_:

            await state.clear()

            await message.answer(
                "فایل پیدا نشد.",
                reply_markup=MAIN,
            )

            return

        old_value = getattr(
            property_,
            field,
        )

        try:

            if field in (
                "price",
                "sqm",
                "deposit",
                "rent",
            ):

                new_value = float(
                    message.text.replace(",", "")
                )

            elif field in (
                "bedrooms",
                "unit_floor",
                "floors",
                "units_per_floor",
            ):

                new_value = int(
                    message.text
                )

            else:

                new_value = message.text.strip()

        except:

            await message.answer(
                "⚠️ مقدار واردشده درست نیست."
            )

            return

        setattr(
            property_,
            field,
            new_value,
        )

        property_.updated_at = now()

        user = await get_user(
            session,
            message.from_user,
        )

        await add_activity(
            session,
            user.id,
            "ویرایش فایل",
            (
                f"{EDIT_FIELDS[field]}: "
                f"{old_value} → {new_value}"
            ),
            property_.id,
        )

        await session.commit()

        await message.answer(
            f"""
✅ <b>{EDIT_FIELDS[field]}</b> تغییر کرد.

قبل:
{old_value}

بعد:
{new_value}
""",
            reply_markup=MAIN,
        )

    await state.clear()


# =========================================================
# PROPERTY HISTORY
# =========================================================

@dp.callback_query(
    F.data.startswith("property:history:")
)
async def property_history(
    call: CallbackQuery,
):

    property_id = int(
        call.data.split(":")[2]
    )

    async with SessionLocal() as session:

        property_ = await session.get(
            Property,
            property_id,
        )

        activities = list(
            (
                await session.execute(
                    select(Activity)
                    .where(
                        Activity.property_id ==
                        property_id
                    )
                    .order_by(
                        Activity.created_at.desc()
                    )
                    .limit(50)
                )
            ).scalars().all()
        )

        if not activities:

            text = (
                f"📜 تاریخچه فایل "
                f"{property_.code}\n\n"
                "هنوز فعالیتی ثبت نشده."
            )

        else:

            lines = [
                f"📜 <b>تاریخچه فایل {property_.code}</b>\n"
            ]

            for activity in activities:

                user = await session.get(
                    User,
                    activity.user_id,
                )

                user_name = (
                    user.name
                    if user
                    else "نامشخص"
                )

                lines.append(
                    f"• {activity.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"  {activity.activity_type}\n"
                    f"  {activity.note}\n"
                    f"  👤 {user_name}\n"
                )

            text = "\n".join(lines)

        await call.message.edit_text(
            text,
            reply_markup=inline([
                [
                    (
                        "🔙 برگشت",
                        f"property:view:{property_id}",
                    )
                ]
            ]),
        )

    await call.answer()


# =========================================================
# PROPERTY EVENTS
# =========================================================

@dp.callback_query(
    F.data.startswith("property:event:")
)
async def event_start(
    call: CallbackQuery,
    state: FSMContext,
):

    property_id = int(
        call.data.split(":")[2]
    )

    await state.clear()

    await state.update_data(
        property_id=property_id
    )

    await state.set_state(
        EventForm.event_type
    )

    await call.message.answer(
        "📌 نوع رویداد را انتخاب کن:",
        reply_markup=kb([
            ["📞 تماس مالک", "🤝 مذاکره"],
            ["👀 بازدید", "💰 تغییر قیمت"],
            ["📄 قرارداد", "📝 سایر"],
            ["❌ لغو"],
        ]),
    )

    await call.answer()


@dp.message(EventForm.event_type)
async def event_type(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        event_type=message.text
    )

    await state.set_state(
        EventForm.note
    )

    await message.answer(
        "📝 شرح رویداد را بنویس:"
    )


@dp.message(EventForm.note)
async def event_note(
    message: Message,
    state: FSMContext,
):

    data = await state.get_data()

    async with SessionLocal() as session:

        property_ = await session.get(
            Property,
            data["property_id"],
        )

        user = await get_user(
            session,
            message.from_user,
        )

        await add_activity(
            session,
            user.id,
            data["event_type"],
            message.text.strip(),
            property_.id if property_ else None,
        )

        await session.commit()

        await message.answer(
            "📌 رویداد با موفقیت ثبت شد.",
            reply_markup=MAIN,
        )

    await state.clear()


# =========================================================
# CLIENT
# =========================================================

@dp.message(F.text == "➕ ثبت مشتری")
async def add_client(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await state.set_state(
        ClientForm.name
    )

    await message.answer(
        "👤 نام مشتری:",
        reply_markup=CANCEL,
    )


@dp.message(ClientForm.name)
async def c_name(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        name=message.text.strip()
    )

    await state.set_state(
        ClientForm.phone
    )

    await message.answer(
        "📞 شماره تماس:"
    )


@dp.message(ClientForm.phone)
async def c_phone(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        phone=message.text.strip()
    )

    await state.set_state(
        ClientForm.area
    )

    await message.answer(
        "📍 منطقه / محله موردنظر:"
    )


@dp.message(ClientForm.area)
async def c_area(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        area=message.text.strip()
    )

    await state.set_state(
        ClientForm.min_sqm
    )

    await message.answer(
        "📐 حداقل متراژ:"
    )


@dp.message(ClientForm.min_sqm)
async def c_min_sqm(
    message: Message,
    state: FSMContext,
):

    try:

        value = float(
            message.text
        )

    except:

        await message.answer(
            "⚠️ عدد وارد کن."
        )

        return

    await state.update_data(
        min_sqm=value
    )

    await state.set_state(
        ClientForm.max_sqm
    )

    await message.answer(
        "📐 حداکثر متراژ:"
    )


@dp.message(ClientForm.max_sqm)
async def c_max_sqm(
    message: Message,
    state: FSMContext,
):

    try:

        value = float(
            message.text
        )

    except:

        await message.answer(
            "⚠️ عدد وارد کن."
        )

        return

    await state.update_data(
        max_sqm=value
    )

    await state.set_state(
        ClientForm.min_budget
    )

    await message.answer(
        "💰 حداقل بودجه:"
    )


@dp.message(ClientForm.min_budget)
async def c_min_budget(
    message: Message,
    state: FSMContext,
):

    try:

        value = float(
            message.text
        )

    except:

        await message.answer(
            "⚠️ عدد وارد کن."
        )

        return

    await state.update_data(
        min_budget=value
    )

    await state.set_state(
        ClientForm.max_budget
    )

    await message.answer(
        "💰 حداکثر بودجه:"
    )


@dp.message(ClientForm.max_budget)
async def c_max_budget(
    message: Message,
    state: FSMContext,
):

    try:

        value = float(
            message.text
        )

    except:

        await message.answer(
            "⚠️ عدد وارد کن."
        )

        return

    await state.update_data(
        max_budget=value
    )

    await state.set_state(
        ClientForm.property_type
    )

    await message.answer(
        "🏷 نوع ملک موردنظر:"
    )


@dp.message(ClientForm.property_type)
async def c_property_type(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        property_type=message.text.strip()
    )

    await state.set_state(
        ClientForm.bedrooms
    )

    await message.answer(
        "🛏 تعداد خواب:",
        reply_markup=bedrooms_keyboard(),
    )


@dp.message(ClientForm.bedrooms)
async def c_bedrooms(
    message: Message,
    state: FSMContext,
):

    if message.text == "+۵":

        await message.answer(
            "تعداد خواب را عددی وارد کن:"
        )

        return

    try:

        value = int(
            message.text
        )

    except:

        await message.answer(
            "یکی از گزینه‌ها را انتخاب کن."
        )

        return

    await state.update_data(
        bedrooms=value
    )

    await state.set_state(
        ClientForm.description
    )

    await message.answer(
        "📝 توضیحات مشتری:"
    )


@dp.message(ClientForm.description)
async def c_description(
    message: Message,
    state: FSMContext,
):

    data = await state.get_data()

    async with SessionLocal() as session:

        user = await get_user(
            session,
            message.from_user,
        )

        client = Client(
            name=data["name"],
            phone=data["phone"],
            area=data["area"],
            min_sqm=data["min_sqm"],
            max_sqm=data["max_sqm"],
            min_budget=data["min_budget"],
            max_budget=data["max_budget"],
            property_type=data["property_type"],
            bedrooms=data["bedrooms"],
            description=message.text.strip(),
            created_by=user.telegram_id,
        )

        session.add(client)

        await session.flush()

        await add_activity(
            session,
            user.id,
            "ثبت مشتری",
            "مشتری جدید",
            None,
            client.id,
        )

        await session.commit()

        await message.answer(
            f"✅ مشتری «{client.name}» ثبت شد.",
            reply_markup=MAIN,
        )

    await state.clear()


# =========================================================
# CLIENT LIST
# =========================================================

@dp.message(F.text == "👤 مشتری‌ها")
async def clients(
    message: Message,
):

    async with SessionLocal() as session:

        clients_ = list(
            (
                await session.execute(
                    select(Client)
                    .order_by(
                        Client.created_at.desc()
                    )
                    .limit(50)
                )
            ).scalars().all()
        )

        if not clients_:

            await message.answer(
                "هنوز مشتری ثبت نشده.",
                reply_markup=MAIN,
            )

            return

        rows = []

        for client in clients_:

            rows.append([
                (
                    f"👤 {client.name} | {client.phone}",
                    f"client:view:{client.id}",
                )
            ])

        await message.answer(
            "👤 <b>مشتری‌ها</b>",
            reply_markup=inline(rows),
        )


@dp.callback_query(
    F.data == "client:list"
)
async def client_list_callback(
    call: CallbackQuery,
):

    await call.answer()

    await clients(
        call.message
    )


@dp.callback_query(
    F.data.startswith("client:view:")
)
async def client_view(
    call: CallbackQuery,
):

    client_id = int(
        call.data.split(":")[2]
    )

    async with SessionLocal() as session:

        client = await session.get(
            Client,
            client_id,
        )

        if not client:

            await call.answer(
                "مشتری پیدا نشد.",
                show_alert=True,
            )

            return

        visits = list(
            (
                await session.execute(
                    select(Visit)
                    .where(
                        Visit.client_id ==
                        client_id
                    )
                    .order_by(
                        Visit.visited_at.desc()
                    )
                    .limit(20)
                )
            ).scalars().all()
        )

        lines = [
            f"👤 <b>{client.name}</b>",
            f"📞 {client.phone}",
            f"📍 {client.area}",
            (
                f"📐 {client.min_sqm:g}"
                f" تا {client.max_sqm:g} متر"
            ),
            (
                f"💰 {money(client.min_budget)}"
                f" تا {money(client.max_budget)}"
            ),
            f"🏷 {client.property_type}",
            f"🛏 خواب: {client.bedrooms}",
            f"👀 تعداد بازدید: {len(visits)}",
        ]

        if visits:

            lines.append(
                "\n📋 <b>آخرین بازدیدها:</b>"
            )

            for visit in visits[:10]:

                property_ = await session.get(
                    Property,
                    visit.property_id,
                )

                lines.append(
                    f"• {property_.code if property_ else '?'}"
                    f" | {visit.visited_at.strftime('%Y-%m-%d %H:%M')}"
                    f" | {visit.next_action}"
                )

        await call.message.edit_text(
            "\n".join(lines),
            reply_markup=inline([
                [
                    (
                        "🔙 مشتری‌ها",
                        "client:list",
                    )
                ]
            ]),
        )

    await call.answer()


# =========================================================
# VISIT
# =========================================================

@dp.message(F.text == "👀 ثبت بازدید")
async def visit_start(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    async with SessionLocal() as session:

        clients_ = list(
            (
                await session.execute(
                    select(Client)
                    .order_by(
                        Client.created_at.desc()
                    )
                    .limit(50)
                )
            ).scalars().all()
        )

        if not clients_:

            await message.answer(
                "اول مشتری ثبت کن.",
                reply_markup=MAIN,
            )

            return

        rows = []

        for client in clients_:

            rows.append([
                (
                    f"👤 {client.name}",
                    f"visitclient:{client.id}",
                )
            ])

        await message.answer(
            "👤 مشتری را انتخاب کن:",
            reply_markup=inline(rows),
        )


@dp.callback_query(
    F.data.startswith("visitclient:")
)
async def visit_client(
    call: CallbackQuery,
    state: FSMContext,
):

    client_id = int(
        call.data.split(":")[1]
    )

    await state.clear()

    await state.update_data(
        client_id=client_id
    )

    async with SessionLocal() as session:

        properties = list(
            (
                await session.execute(
                    select(Property)
                    .where(
                        Property.status.in_([
                            "فعال",
                            "در مذاکره",
                        ])
                    )
                    .order_by(
                        Property.created_at.desc()
                    )
                    .limit(50)
                )
            ).scalars().all()
        )

        if not properties:

            await call.message.answer(
                "فایل فعال نداریم."
            )

            return

        rows = []

        for property_ in properties:

            rows.append([
                (
                    f"{property_.code} | "
                    f"{property_.area} | "
                    f"{property_.sqm:g}م | "
                    f"{money(property_.price)}",
                    f"visitproperty:{property_.id}",
                )
            ])

        await call.message.answer(
            "🏠 فایل بازدیدشده را انتخاب کن:",
            reply_markup=inline(rows),
        )

    await call.answer()


@dp.callback_query(
    F.data.startswith("visitproperty:")
)
async def visit_property(
    call: CallbackQuery,
    state: FSMContext,
):

    property_id = int(
        call.data.split(":")[1]
    )

    data = await state.get_data()

    client_id = data.get(
        "client_id"
    )

    if not client_id:

        await call.answer(
            "جلسه ثبت بازدید منقضی شده.",
            show_alert=True,
        )

        return

    async with SessionLocal() as session:

        previous_visits = list(
            (
                await session.execute(
                    select(Visit)
                    .where(
                        Visit.client_id ==
                        client_id,
                        Visit.property_id ==
                        property_id,
                    )
                    .order_by(
                        Visit.visited_at.desc()
                    )
                )
            ).scalars().all()
        )

        if previous_visits:

            last = previous_visits[0]

            property_ = await session.get(
                Property,
                property_id,
            )

            client = await session.get(
                Client,
                client_id,
            )

            agent = await session.get(
                User,
                last.agent_id,
            )

            await call.message.answer(
                f"""
⚠️ <b>این مشتری قبلاً از این فایل بازدید کرده است.</b>

👤 مشتری:
{client.name}

🏠 فایل:
{property_.code}

👨‍💼 بازدید قبلی توسط:
{agent.name if agent else "نامشخص"}

🕒 تاریخ قبلی:
{last.visited_at.strftime("%Y-%m-%d %H:%M")}

آیا بازدید مجدد را ثبت می‌کنی؟
""",
                reply_markup=inline([
                    [
                        (
                            "❌ لغو",
                            "visitcancel",
                        ),
                        (
                            "🔄 ثبت بازدید مجدد",
                            f"visitrepeat:{client_id}:{property_id}",
                        ),
                    ]
                ]),
            )

            await call.answer()

            return

    await start_scorecard(
        call.message,
        state,
        client_id,
        property_id,
    )

    await call.answer()


@dp.callback_query(
    F.data.startswith("visitrepeat:")
)
async def visit_repeat(
    call: CallbackQuery,
    state: FSMContext,
):

    _, client_id, property_id = (
        call.data.split(":")
    )

    await start_scorecard(
        call.message,
        state,
        int(client_id),
        int(property_id),
    )

    await call.answer()


@dp.callback_query(
    F.data == "visitcancel"
)
async def visit_cancel(
    call: CallbackQuery,
    state: FSMContext,
):

    await state.clear()

    await call.message.answer(
        "❌ بازدید لغو شد.",
        reply_markup=MAIN,
    )

    await call.answer()


async def start_scorecard(
    message,
    state,
    client_id,
    property_id,
):

    await state.clear()

    await state.update_data(
        client_id=client_id,
        property_id=property_id,
    )

    await state.set_state(
        VisitForm.interest
    )

    await message.answer(
        """
👀 <b>بازدید ثبت شد.</b>

حالا نوبت <b>کارنامه بازدید</b> است.

🔥 میزان علاقه مشتری؟
""",
        reply_markup=kb([
            ["🔥 خیلی زیاد", "🟢 زیاد"],
            ["🟡 متوسط", "🔴 کم"],
            ["❌ رد"],
        ]),
    )


@dp.message(VisitForm.interest)
async def v_interest(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        interest=message.text
    )

    await state.set_state(
        VisitForm.price_reaction
    )

    await message.answer(
        "💰 واکنش مشتری به قیمت؟",
        reply_markup=kb([
            ["✅ مناسب", "🟡 کمی بالا"],
            ["🔴 بالا", "❌ خیلی بالا"],
            ["❓ نظر نداد"],
        ]),
    )


@dp.message(
    VisitForm.price_reaction
)
async def v_price(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        price_reaction=message.text
    )

    await state.set_state(
        VisitForm.property_reaction
    )

    await message.answer(
        "🏠 نظر کلی مشتری درباره ملک؟",
        reply_markup=kb([
            ["❤️ پسندید", "🟡 متوسط"],
            ["👎 نپسندید", "❓ نامشخص"],
        ]),
    )


@dp.message(
    VisitForm.property_reaction
)
async def v_reaction(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        property_reaction=message.text
    )

    await state.set_state(
        VisitForm.objection
    )

    await message.answer(
        "❗ اعتراض / ایراد اصلی مشتری چیست؟\n"
        "اگر ندارد بنویس: ندارد"
    )


@dp.message(
    VisitForm.objection
)
async def v_objection(
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
        "➡️ قدم بعدی چیست؟",
        reply_markup=kb([
            ["📞 پیگیری", "🔄 بازدید مجدد"],
            ["🤝 مذاکره", "📄 قرارداد"],
            ["❌ رد شد", "⏳ فعلاً صبر"],
        ]),
    )


@dp.message(
    VisitForm.next_action
)
async def v_next(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        next_action=message.text
    )

    await state.set_state(
        VisitForm.followup_date
    )

    await message.answer(
        "📅 تاریخ پیگیری بعدی را بنویس.\n"
        "مثلاً: 1405/07/02\n"
        "یا بنویس: ندارد"
    )


@dp.message(
    VisitForm.followup_date
)
async def v_followup(
    message: Message,
    state: FSMContext,
):

    await state.update_data(
        followup_date=message.text.strip()
    )

    await state.set_state(
        VisitForm.note
    )

    await message.answer(
        "📝 یادداشت نهایی بازدید:"
    )


@dp.message(VisitForm.note)
async def v_note(
    message: Message,
    state: FSMContext,
):

    data = await state.get_data()

    async with SessionLocal() as session:

        user = await get_user(
            session,
            message.from_user,
        )

        visit = Visit(
            property_id=data["property_id"],
            client_id=data["client_id"],
            agent_id=user.id,
            interest=data["interest"],
            price_reaction=data["price_reaction"],
            property_reaction=data["property_reaction"],
            objection=data["objection"],
            next_action=data["next_action"],
            followup_date=data["followup_date"],
            note=message.text.strip(),
            outcome=(
                f"{data['interest']} | "
                f"{data['property_reaction']} | "
                f"قدم بعدی: {data['next_action']}"
            ),
        )

        session.add(visit)

        await session.flush()

        await add_activity(
            session,
            user.id,
            "کارنامه بازدید",
            (
                f"علاقه: {visit.interest} | "
                f"قیمت: {visit.price_reaction} | "
                f"نظر: {visit.property_reaction} | "
                f"قدم بعدی: {visit.next_action} | "
                f"ایراد: {visit.objection}"
            ),
            visit.property_id,
            visit.client_id,
        )

        await session.commit()

        await message.answer(
            f"""
✅ <b>کارنامه بازدید ثبت شد.</b>

🔥 علاقه:
{visit.interest}

💰 واکنش قیمت:
{visit.price_reaction}

🏠 نظر ملک:
{visit.property_reaction}

➡️ قدم بعدی:
{visit.next_action}

📅 پیگیری:
{visit.followup_date}
""",
            reply_markup=MAIN,
        )

    await state.clear()


# =========================================================
# MATCHING
# =========================================================

@dp.message(F.text == "🔎 پیشنهاد فایل")
async def matching(
    message: Message,
):

    async with SessionLocal() as session:

        clients_ = list(
            (
                await session.execute(
                    select(Client)
                    .order_by(
                        Client.created_at.desc()
                    )
                    .limit(50)
                )
            ).scalars().all()
        )

        if not clients_:

            await message.answer(
                "اول مشتری ثبت کن.",
                reply_markup=MAIN,
            )

            return

        rows = []

        for client in clients_:

            rows.append([
                (
                    f"👤 {client.name}",
                    f"match:{client.id}",
                )
            ])

        await message.answer(
            "🔎 برای کدام مشتری پیشنهاد فایل می‌خواهی؟",
            reply_markup=inline(rows),
        )


@dp.callback_query(
    F.data.startswith("match:")
)
async def match_client(
    call: CallbackQuery,
):

    client_id = int(
        call.data.split(":")[1]
    )

    async with SessionLocal() as session:

        client = await session.get(
            Client,
            client_id,
        )

        visited = set(
            (
                await session.execute(
                    select(
                        Visit.property_id
                    ).where(
                        Visit.client_id ==
                        client_id
                    )
                )
            ).scalars().all()
        )

        properties = list(
            (
                await session.execute(
                    select(Property)
                    .where(
                        Property.status ==
                        "فعال"
                    )
                )
            ).scalars().all()
        )

        scored = []

        for property_ in properties:

            score = 0

            if (
                client.max_budget
                and property_.price <=
                client.max_budget
            ):

                score += 40

            elif not client.max_budget:

                score += 20

            if (
                client.area
                and client.area in property_.area
            ):

                score += 25

            elif not client.area:

                score += 12

            if (
                client.max_sqm
                and client.min_sqm <=
                property_.sqm <=
                client.max_sqm
            ):

                score += 20

            elif not client.max_sqm:

                score += 10

            if (
                client.property_type
                and client.property_type.strip()
                == property_.property_type.strip()
            ):

                score += 10

            elif not client.property_type:

                score += 5

            if (
                client.bedrooms == 0
                or client.bedrooms ==
                property_.bedrooms
            ):

                score += 5

            scored.append(
                (
                    score,
                    property_,
                    property_.id in visited,
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        top = scored[:10]

        if not top:

            await call.message.answer(
                "فایل منطبق پیدا نشد."
            )

            return

        rows = []

        for score, property_, was_visited in top:

            visited_text = (
                " ⚠️ بازدید شده"
                if was_visited
                else ""
            )

            rows.append([
                (
                    (
                        f"{score}% | "
                        f"{property_.code} | "
                        f"{property_.area} | "
                        f"{property_.sqm:g}م | "
                        f"{money(property_.price)}"
                        f"{visited_text}"
                    ),
                    f"property:view:{property_.id}",
                )
            ])

        await call.message.answer(
            f"🔎 <b>پیشنهاد فایل برای {client.name}</b>",
            reply_markup=inline(rows),
        )

    await call.answer()


# =========================================================
# ACTIVITIES
# =========================================================

@dp.message(F.text == "📝 آخرین فعالیت‌ها")
async def activities(
    message: Message,
):

    async with SessionLocal() as session:

        activities_ = list(
            (
                await session.execute(
                    select(Activity)
                    .order_by(
                        Activity.created_at.desc()
                    )
                    .limit(30)
                )
            ).scalars().all()
        )

        if not activities_:

            await message.answer(
                "هنوز فعالیتی ثبت نشده.",
                reply_markup=MAIN,
            )

            return

        lines = [
            "📝 <b>آخرین فعالیت‌ها</b>\n"
        ]

        for activity in activities_:

            user = await session.get(
                User,
                activity.user_id,
            )

            lines.append(
                f"• {activity.created_at.strftime('%Y-%m-%d %H:%M')}"
                f" | {activity.activity_type}"
                f" | {user.name if user else '?'}\n"
                f"  {activity.note}"
            )

        await message.answer(
            "\n".join(lines),
            reply_markup=MAIN,
        )


# =========================================================
# FOLLOW UPS
# =========================================================

@dp.message(F.text == "📞 پیگیری")
async def followups(
    message: Message,
):

    async with SessionLocal() as session:

        visits = list(
            (
                await session.execute(
                    select(Visit)
                    .where(
                        Visit.followup_date != "",
                        Visit.followup_date != "ندارد",
                    )
                    .order_by(
                        Visit.visited_at.desc()
                    )
                    .limit(50)
                )
            ).scalars().all()
        )

        if not visits:

            await message.answer(
                "📞 پیگیری ثبت‌شده‌ای نداریم.",
                reply_markup=MAIN,
            )

            return

        lines = [
            "📞 <b>پیگیری‌های ثبت‌شده</b>\n"
        ]

        for visit in visits:

            client = await session.get(
                Client,
                visit.client_id,
            )

            property_ = await session.get(
                Property,
                visit.property_id,
            )

            lines.append(
                f"• {visit.followup_date}"
                f" | {client.name if client else '?'}"
                f" | {property_.code if property_ else '?'}"
                f" | {visit.next_action}"
            )

        await message.answer(
            "\n".join(lines),
            reply_markup=MAIN,
        )


# =========================================================
# KPI
# =========================================================

async def user_kpi(
    session,
    user,
):

    files_count = int(
        (
            await session.execute(
                select(
                    func.count(Property.id)
                ).where(
                    Property.created_by ==
                    user.telegram_id
                )
            )
        ).scalar()
        or 0
    )

    clients_count = int(
        (
            await session.execute(
                select(
                    func.count(Client.id)
                ).where(
                    Client.created_by ==
                    user.telegram_id
                )
            )
        ).scalar()
        or 0
    )

    visits_count = int(
        (
            await session.execute(
                select(
                    func.count(Visit.id)
                ).where(
                    Visit.agent_id ==
                    user.id
                )
            )
        ).scalar()
        or 0
    )

    followups_count = int(
        (
            await session.execute(
                select(
                    func.count(Activity.id)
                ).where(
                    Activity.user_id ==
                    user.id,
                    Activity.activity_type.in_([
                        "کارنامه بازدید",
                        "پیگیری",
                    ])
                )
            )
        ).scalar()
        or 0
    )

    negotiations = int(
        (
            await session.execute(
                select(
                    func.count(Activity.id)
                ).where(
                    Activity.user_id ==
                    user.id,
                    Activity.activity_type.in_([
                        "🤝 مذاکره",
                        "مذاکره",
                    ])
                )
            )
        ).scalar()
        or 0
    )

    contracts = int(
        (
            await session.execute(
                select(
                    func.count(Activity.id)
                ).where(
                    Activity.user_id ==
                    user.id,
                    Activity.activity_type.in_([
                        "📄 قرارداد",
                        "قرارداد",
                        "معامله",
                    ])
                )
            )
        ).scalar()
        or 0
    )

    return (
        files_count,
        clients_count,
        visits_count,
        followups_count,
        negotiations,
        contracts,
    )


@dp.message(F.text == "📊 KPI من")
async def my_kpi(
    message: Message,
):

    async with SessionLocal() as session:

        user = await get_user(
            session,
            message.from_user,
        )

        (
            files_count,
            clients_count,
            visits_count,
            followups_count,
            negotiations,
            contracts,
        ) = await user_kpi(
            session,
            user,
        )

        await message.answer(
            f"""
📊 <b>KPI {user.name}</b>

🏠 فایل: {files_count}
👤 مشتری: {clients_count}
👀 بازدید: {visits_count}
📞 پیگیری / کارنامه: {followups_count}
🤝 مذاکره: {negotiations}
📄 قرارداد / معامله: {contracts}
""",
            reply_markup=MAIN,
        )


@dp.message(F.text == "👥 KPI تیم")
async def team_kpi(
    message: Message,
):

    async with SessionLocal() as session:

        users = list(
            (
                await session.execute(
                    select(User)
                    .order_by(
                        User.name
                    )
                )
            ).scalars().all()
        )

        lines = [
            "👥 <b>KPI تیم</b>\n"
        ]

        for user in users:

            (
                files_count,
                clients_count,
                visits_count,
                followups_count,
                negotiations,
                contracts,
            ) = await user_kpi(
                session,
                user,
            )

            lines.append(
                f"""
👤 {user.name}

🏠 {files_count} فایل
👤 {clients_count} مشتری
👀 {visits_count} بازدید
📞 {followups_count} پیگیری
🤝 {negotiations} مذاکره
📄 {contracts} قرارداد/معامله
"""
            )

        await message.answer(
            "\n".join(lines),
            reply_markup=MAIN,
        )


# =========================================================
# RUN
# =========================================================

async def main():

    await migrate()

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":
    asyncio.run(main())
