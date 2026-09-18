import os
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    select,
    func,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")


DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1
        )

    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql+asyncpg://",
            1
        )

else:
    DATABASE_URL = "sqlite+aiosqlite:///crm.db"


# =========================
# DATABASE
# =========================

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
        unique=True
    )

    name: Mapped[str] = mapped_column(
        String(100)
    )

    role: Mapped[str] = mapped_column(
        String(50),
        default="agent"
    )


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    # اطلاعات اصلی
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True
    )

    area: Mapped[str] = mapped_column(
        String(100)
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

    bedrooms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # ساختمان
    floors: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    units_per_floor: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    elevator: Mapped[str] = mapped_column(
        String(20),
        default="ندارد"
    )

    parking: Mapped[str] = mapped_column(
        String(20),
        default="ندارد"
    )

    parking_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    storage: Mapped[str] = mapped_column(
        String(20),
        default="ندارد"
    )

    # وضعیت سکونت
    tenant: Mapped[str] = mapped_column(
        String(20),
        default="ندارد"
    )

    deposit: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    rent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    vacancy_date: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    # سند
    document_type: Mapped[str] = mapped_column(
        String(100),
        default="نامشخص"
    )

    # مالک
    owner_name: Mapped[str] = mapped_column(
        String(100)
    )

    owner_phone: Mapped[str] = mapped_column(
        String(50)
    )

    description: Mapped[str] = mapped_column(
        String(1000),
        default=""
    )

    # ثبت کننده
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id")
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
        String(100)
    )

    phone: Mapped[str] = mapped_column(
        String(50)
    )

    budget: Mapped[float] = mapped_column(
        Float
    )

    desired_area: Mapped[str] = mapped_column(
        String(100)
    )

    desired_sqm: Mapped[float] = mapped_column(
        Float
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id")
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

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id")
    )

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id")
    )

    agent_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    visit_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    outcome: Mapped[str] = mapped_column(
        String(200),
        default=""
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"),
        nullable=True
    )

    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id"),
        nullable=True
    )

    activity_type: Mapped[str] = mapped_column(
        String(100)
    )

    note: Mapped[str] = mapped_column(
        String(500),
        default=""
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


engine = create_async_engine(
    DATABASE_URL,
    echo=False
)

Session = async_sessionmaker(
    engine,
    expire_on_commit=False
)


async def init_db():

    async with engine.begin() as conn:

        await conn.run_sync(
            Base.metadata.create_all
        )


# =========================
# TELEGRAM
# =========================

dp = Dispatcher()


MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🏠 فایل‌ها"),
            KeyboardButton(text="👤 مشتری‌ها"),
        ],
        [
            KeyboardButton(text="➕ ثبت فایل"),
            KeyboardButton(text="➕ ثبت مشتری"),
        ],
        [
            KeyboardButton(text="👀 ثبت بازدید"),
            KeyboardButton(text="📞 پیگیری"),
        ],
        [
            KeyboardButton(text="🔎 پیشنهاد فایل"),
            KeyboardButton(text="📝 آخرین فعالیت‌ها"),
        ],
        [
            KeyboardButton(text="📊 KPI من"),
            KeyboardButton(text="👥 KPI تیم"),
        ],
    ],
    resize_keyboard=True
)


CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="❌ لغو")
        ]
    ],
    resize_keyboard=True
)


# =========================
# FILE FORM STATES
# =========================

class PropertyForm(StatesGroup):

    code = State()
    area = State()
    sqm = State()
    price = State()
    property_type = State()
    bedrooms = State()

    floors = State()
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


# =========================
# USER
# =========================

async def get_or_create_user(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(User).where(
                User.telegram_id == message.from_user.id
            )
        )

        user = result.scalar_one_or_none()

        if not user:

            user = User(
                telegram_id=message.from_user.id,
                name=message.from_user.full_name,
                role="agent"
            )

            session.add(user)

            await session.commit()

        return user


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await get_or_create_user(message)

    await message.answer(
        "🏙️ شهردار ایران‌زمین\n"
        "Hooman Real Estate\n\n"
        "سیستم مدیریت فایل، مشتری و تیم آماده است.\n\n"
        "از منوی پایین انتخاب کن:",
        reply_markup=MAIN_MENU
    )


# =========================
# CANCEL
# =========================

@dp.message(
    F.text == "❌ لغو"
)
async def cancel_form(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await message.answer(
        "❌ عملیات لغو شد.",
        reply_markup=MAIN_MENU
    )


# =========================
# FILES
# =========================

@dp.message(F.text == "🏠 فایل‌ها")
async def properties(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(Property)
            .order_by(
                Property.created_at.desc()
            )
            .limit(20)
        )

        properties = result.scalars().all()

    if not properties:

        await message.answer(
            "🏠 هنوز فایلی ثبت نشده."
        )
        return

    text = "🏠 آخرین فایل‌ها:\n\n"

    for p in properties:

        text += (
            f"🔹 {p.code}\n"
            f"📍 {p.area}\n"
            f"📐 {p.sqm:g} متر\n"
            f"💰 {p.price:,.0f}\n"
            f"🏠 {p.property_type}\n"
            f"📄 {p.document_type}\n\n"
        )

    await message.answer(text)


# =========================
# CLIENTS
# =========================

@dp.message(F.text == "👤 مشتری‌ها")
async def clients(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(Client)
            .order_by(
                Client.created_at.desc()
            )
            .limit(20)
        )

        clients = result.scalars().all()

    if not clients:

        await message.answer(
            "👤 هنوز مشتری ثبت نشده."
        )
        return

    text = "👤 آخرین مشتری‌ها:\n\n"

    for c in clients:

        text += (
            f"🔹 {c.name}\n"
            f"💰 بودجه: {c.budget:,.0f}\n"
            f"📍 {c.desired_area}\n"
            f"📐 {c.desired_sqm:g} متر\n\n"
        )

    await message.answer(text)


# =========================
# ADD PROPERTY - START
# =========================

@dp.message(F.text == "➕ ثبت فایل")
async def add_property(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await state.set_state(
        PropertyForm.code
    )

    await message.answer(
        "➕ ثبت فایل جدید\n\n"
        "مرحله ۱ از ۱۸\n\n"
        "🏷️ کد فایل را وارد کن:\n\n"
        "مثال: KH-001",
        reply_markup=CANCEL_KEYBOARD
    )


# =========================
# PROPERTY FORM
# =========================

@dp.message(PropertyForm.code)
async def property_code(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        code=message.text.strip()
    )

    await state.set_state(
        PropertyForm.area
    )

    await message.answer(
        "📍 محله / محدوده را وارد کن:",
        reply_markup=CANCEL_KEYBOARD
    )


@dp.message(PropertyForm.area)
async def property_area(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        area=message.text.strip()
    )

    await state.set_state(
        PropertyForm.sqm
    )

    await message.answer(
        "📐 متراژ را وارد کن:\n\n"
        "مثال: 85"
    )


@dp.message(PropertyForm.sqm)
async def property_sqm(
    message: Message,
    state: FSMContext
):

    try:
        sqm = float(
            message.text.replace(",", "")
        )
    except ValueError:

        await message.answer(
            "⚠️ متراژ باید عدد باشد.\n"
            "مثال: 85"
        )
        return

    await state.update_data(
        sqm=sqm
    )

    await state.set_state(
        PropertyForm.price
    )

    await message.answer(
        "💰 قیمت کل ملک را وارد کن:\n\n"
        "مثال: 12000000000"
    )


@dp.message(PropertyForm.price)
async def property_price(
    message: Message,
    state: FSMContext
):

    try:
        price = float(
            message.text.replace(",", "")
        )
    except ValueError:

        await message.answer(
            "⚠️ قیمت باید عدد باشد.\n"
            "مثال: 12000000000"
        )
        return

    await state.update_data(
        price=price
    )

    await state.set_state(
        PropertyForm.property_type
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="آپارتمان"),
                KeyboardButton(text="کلنگی"),
            ],
            [
                KeyboardButton(text="زمین"),
                KeyboardButton(text="مغازه"),
            ],
            [
                KeyboardButton(text="اداری"),
                KeyboardButton(text="سایر"),
            ],
            [
                KeyboardButton(text="❌ لغو")
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "🏠 نوع ملک را انتخاب کن:",
        reply_markup=keyboard
    )


@dp.message(PropertyForm.property_type)
async def property_type(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        property_type=message.text
    )

    await state.set_state(
        PropertyForm.bedrooms
    )

    await message.answer(
        "🛏️ تعداد خواب را وارد کن:\n\n"
        "اگر ندارد، 0 بنویس."
    )


@dp.message(PropertyForm.bedrooms)
async def property_bedrooms(
    message: Message,
    state: FSMContext
):

    try:
        bedrooms = int(message.text)
    except ValueError:

        await message.answer(
            "⚠️ تعداد خواب باید عدد باشد."
        )
        return

    await state.update_data(
        bedrooms=bedrooms
    )

    await state.set_state(
        PropertyForm.floors
    )

    await message.answer(
        "🏢 ساختمان چند طبقه است؟"
    )


@dp.message(PropertyForm.floors)
async def property_floors(
    message: Message,
    state: FSMContext
):

    try:
        floors = int(message.text)
    except ValueError:

        await message.answer(
            "⚠️ تعداد طبقات باید عدد باشد."
        )
        return

    await state.update_data(
        floors=floors
    )

    await state.set_state(
        PropertyForm.units_per_floor
    )

    await message.answer(
        "🏢 در هر طبقه چند واحد است؟"
    )


@dp.message(PropertyForm.units_per_floor)
async def property_units(
    message: Message,
    state: FSMContext
):

    try:
        units = int(message.text)
    except ValueError:

        await message.answer(
            "⚠️ تعداد واحد باید عدد باشد."
        )
        return

    await state.update_data(
        units_per_floor=units
    )

    await state.set_state(
        PropertyForm.elevator
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="دارد"),
                KeyboardButton(text="ندارد"),
            ],
            [
                KeyboardButton(text="❌ لغو")
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "🛗 آسانسور:",
        reply_markup=keyboard
    )


@dp.message(PropertyForm.elevator)
async def property_elevator(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        elevator=message.text
    )

    await state.set_state(
        PropertyForm.parking
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="دارد"),
                KeyboardButton(text="ندارد"),
            ],
            [
                KeyboardButton(text="❌ لغو")
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "🚗 پارکینگ:",
        reply_markup=keyboard
    )


@dp.message(PropertyForm.parking)
async def property_parking(
    message: Message,
    state: FSMContext
):

    value = message.text

    await state.update_data(
        parking=value
    )

    if value == "دارد":

        await state.set_state(
            PropertyForm.parking_type
        )

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="غیرمزاحم"
                    ),
                    KeyboardButton(
                        text="مزاحم"
                    ),
                ],
                [
                    KeyboardButton(text="❌ لغو")
                ]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "🅿️ نوع پارکینگ:",
            reply_markup=keyboard
        )

    else:

        await state.update_data(
            parking_type=None
        )

        await state.set_state(
            PropertyForm.storage
        )

        await message.answer(
            "📦 انباری:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [
                        KeyboardButton(text="دارد"),
                        KeyboardButton(text="ندارد"),
                    ],
                    [
                        KeyboardButton(text="❌ لغو")
                    ]
                ],
                resize_keyboard=True
            )
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

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="دارد"),
                KeyboardButton(text="ندارد"),
            ],
            [
                KeyboardButton(text="❌ لغو")
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "📦 انباری:",
        reply_markup=keyboard
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

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="دارد"),
                KeyboardButton(text="ندارد"),
            ],
            [
                KeyboardButton(text="❌ لغو")
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "👤 مستأجر دارد؟",
        reply_markup=keyboard
    )


@dp.message(PropertyForm.tenant)
async def property_tenant(
    message: Message,
    state: FSMContext
):

    value = message.text

    await state.update_data(
        tenant=value
    )

    if value == "دارد":

        await state.set_state(
            PropertyForm.deposit
        )

        await message.answer(
            "💰 مبلغ رهن را وارد کن:\n\n"
            "مثال: 500000000"
        )

    else:

        await state.update_data(
            deposit=None,
            rent=None,
            vacancy_date=None
        )

        await state.set_state(
            PropertyForm.document_type
        )

        await send_document_keyboard(message)


@dp.message(PropertyForm.deposit)
async def property_deposit(
    message: Message,
    state: FSMContext
):

    try:
        deposit = float(
            message.text.replace(",", "")
        )
    except ValueError:

        await message.answer(
            "⚠️ مبلغ رهن باید عدد باشد."
        )
        return

    await state.update_data(
        deposit=deposit
    )

    await state.set_state(
        PropertyForm.rent
    )

    await message.answer(
        "💵 مبلغ اجاره ماهانه را وارد کن:\n\n"
        "اگر ندارد، 0 بنویس."
    )


@dp.message(PropertyForm.rent)
async def property_rent(
    message: Message,
    state: FSMContext
):

    try:
        rent = float(
            message.text.replace(",", "")
        )
    except ValueError:

        await message.answer(
            "⚠️ مبلغ اجاره باید عدد باشد."
        )
        return

    await state.update_data(
        rent=rent
    )

    await state.set_state(
        PropertyForm.vacancy_date
    )

    await message.answer(
        "📅 تاریخ تخلیه را وارد کن:\n\n"
        "مثال: 1405/12/01\n"
        "اگر مشخص نیست، بنویس «نامشخص»."
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

    await send_document_keyboard(message)


async def send_document_keyboard(message: Message):

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="تک‌برگ"),
                KeyboardButton(text="اوقافی"),
            ],
            [
                KeyboardButton(
                    text="قدیمی / منگوله‌دار"
                ),
                KeyboardButton(
                    text="قولنامه‌ای"
                ),
            ],
            [
                KeyboardButton(text="سایر"),
            ],
            [
                KeyboardButton(text="❌ لغو")
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "📄 نوع سند را انتخاب کن:",
        reply_markup=keyboard
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
        "👤 نام مالک را وارد کن:"
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
        "📞 شماره تماس مالک را وارد کن:"
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
        "📝 توضیحات فایل را وارد کن:\n\n"
        "مثال:\n"
        "نور عالی، بازسازی کامل، سند آماده انتقال\n\n"
        "اگر توضیح خاصی ندارد، بنویس «ندارد»."
    )


@dp.message(PropertyForm.description)
async def property_description(
    message: Message,
    state: FSMContext
):

    description = message.text.strip()

    if description == "ندارد":
        description = ""

    await state.update_data(
        description=description
    )

    data = await state.get_data()

    summary = (
        "📋 پیش‌نمایش فایل\n\n"

        f"🏷️ کد: {data['code']}\n"
        f"📍 محله: {data['area']}\n"
        f"📐 متراژ: {data['sqm']:g} متر\n"
        f"💰 قیمت: {data['price']:,.0f}\n"
        f"🏠 نوع: {data['property_type']}\n"
        f"🛏️ خواب: {data['bedrooms']}\n\n"

        f"🏢 طبقات: {data['floors']}\n"
        f"🏢 واحد/طبقه: {data['units_per_floor']}\n"
        f"🛗 آسانسور: {data['elevator']}\n"
        f"🚗 پارکینگ: {data['parking']}\n"
        f"🅿️ نوع پارکینگ: "
        f"{data.get('parking_type') or '-'}\n"
        f"📦 انباری: {data['storage']}\n\n"

        f"👤 مستأجر: {data['tenant']}\n"
        f"💰 رهن: "
        f"{data.get('deposit') or 0:,.0f}\n"
        f"💵 اجاره: "
        f"{data.get('rent') or 0:,.0f}\n"
        f"📅 تخلیه: "
        f"{data.get('vacancy_date') or '-'}\n\n"

        f"📄 سند: {data['document_type']}\n"
        f"👤 مالک: {data['owner_name']}\n"
        f"📞 تماس: {data['owner_phone']}\n"
        f"📝 توضیحات: "
        f"{data.get('description') or '-'}\n\n"

        "آیا اطلاعات درست است؟"
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="✅ ثبت نهایی"
                ),
                KeyboardButton(
                    text="✏️ اصلاح"
                ),
            ],
            [
                KeyboardButton(
                    text="❌ لغو"
                )
            ]
        ],
        resize_keyboard=True
    )

    await state.set_state(
        PropertyForm.confirmation
    )

    await message.answer(
        summary,
        reply_markup=keyboard
    )


# =========================
# FINAL PROPERTY SAVE
# =========================

@dp.message(PropertyForm.confirmation)
async def property_confirmation(
    message: Message,
    state: FSMContext
):

    if message.text == "✏️ اصلاح":

        await state.set_state(
            PropertyForm.code
        )

        await message.answer(
            "✏️ از ابتدا اصلاح می‌کنیم.\n\n"
            "🏷️ کد فایل را وارد کن:",
            reply_markup=CANCEL_KEYBOARD
        )

        return

    if message.text != "✅ ثبت نهایی":

        await message.answer(
            "لطفاً یکی از گزینه‌های نمایش داده‌شده را انتخاب کن."
        )

        return

    data = await state.get_data()

    user = await get_or_create_user(
        message
    )

    async with Session() as session:

        # جلوگیری از کد تکراری
        result = await session.execute(
            select(Property).where(
                Property.code == data["code"]
            )
        )

        existing = result.scalar_one_or_none()

        if existing:

            await message.answer(
                "⚠️ این کد فایل قبلاً ثبت شده است.\n\n"
                f"کد: {existing.code}\n"
                f"محله: {existing.area}\n\n"
                "یک کد جدید وارد کن.",
                reply_markup=CANCEL_KEYBOARD
            )

            await state.set_state(
                PropertyForm.code
            )

            return

        property_obj = Property(
            code=data["code"],
            area=data["area"],
            sqm=data["sqm"],
            price=data["price"],
            property_type=data["property_type"],
            bedrooms=data["bedrooms"],
            floors=data["floors"],
            units_per_floor=data["units_per_floor"],
            elevator=data["elevator"],
            parking=data["parking"],
            parking_type=data.get(
                "parking_type"
            ),
            storage=data["storage"],
            tenant=data["tenant"],
            deposit=data.get("deposit"),
            rent=data.get("rent"),
            vacancy_date=data.get(
                "vacancy_date"
            ),
            document_type=data["document_type"],
            owner_name=data["owner_name"],
            owner_phone=data["owner_phone"],
            description=data.get(
                "description",
                ""
            ),
            created_by=user.id,
        )

        session.add(property_obj)

        await session.flush()

        # ثبت فعالیت
        activity = Activity(
            user_id=user.id,
            property_id=property_obj.id,
            activity_type="ثبت فایل",
            note=f"ثبت فایل {property_obj.code}"
        )

        session.add(activity)

        await session.commit()

    await state.clear()

    await message.answer(
        "✅ فایل با موفقیت ثبت شد.\n\n"

        f"🏷️ کد: {data['code']}\n"
        f"📍 {data['area']}\n"
        f"📐 {data['sqm']:g} متر\n"
        f"💰 {data['price']:,.0f}\n"
        f"🏠 {data['property_type']}\n\n"

        "👤 ثبت‌کننده: "
        f"{user.name}\n"
        f"🕐 زمان ثبت: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        "فایل وارد سیستم شد و در بخش "
        "🏠 فایل‌ها قابل مشاهده است.",
        reply_markup=MAIN_MENU
    )


# =========================
# KPI
# =========================

async def get_kpi(user_id):

    async with Session() as session:

        properties = await session.scalar(
            select(func.count(Property.id))
            .where(
                Property.created_by == user_id
            )
        )

        clients = await session.scalar(
            select(func.count(Client.id))
            .where(
                Client.created_by == user_id
            )
        )

        visits = await session.scalar(
            select(func.count(Visit.id))
            .where(
                Visit.agent_id == user_id
            )
        )

        activities = await session.scalar(
            select(func.count(Activity.id))
            .where(
                Activity.user_id == user_id
            )
        )

    return (
        properties or 0,
        clients or 0,
        visits or 0,
        activities or 0
    )


@dp.message(F.text == "📊 KPI من")
async def my_kpi(message: Message):

    user = await get_or_create_user(
        message
    )

    properties, clients, visits, activities = (
        await get_kpi(user.id)
    )

    await message.answer(
        "📊 KPI شخصی\n\n"
        f"🏠 فایل ثبت‌شده: {properties}\n"
        f"👤 مشتری ثبت‌شده: {clients}\n"
        f"👀 بازدید: {visits}\n"
        f"📝 فعالیت: {activities}"
    )


# =========================
# TEAM KPI
# =========================

@dp.message(F.text == "👥 KPI تیم")
async def team_kpi(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(User)
        )

        users = result.scalars().all()

    text = "👥 KPI تیم\n\n"

    for user in users:

        properties, clients, visits, activities = (
            await get_kpi(user.id)
        )

        text += (
            f"👤 {user.name}\n"
            f"🏠 فایل: {properties}\n"
            f"👤 مشتری: {clients}\n"
            f"👀 بازدید: {visits}\n"
            f"📝 فعالیت: {activities}\n\n"
        )

    await message.answer(text)


# =========================
# RECENT ACTIVITIES
# =========================

@dp.message(F.text == "📝 آخرین فعالیت‌ها")
async def latest_activities(
    message: Message
):

    async with Session() as session:

        result = await session.execute(
            select(Activity)
            .order_by(
                Activity.created_at.desc()
            )
            .limit(15)
        )

        activities = result.scalars().all()

    if not activities:

        await message.answer(
            "📝 هنوز فعالیتی ثبت نشده."
        )
        return

    text = "📝 آخرین فعالیت‌ها\n\n"

    for a in activities:

        text += (
            f"• {a.activity_type}\n"
            f"📝 {a.note}\n"
            f"🕐 "
            f"{a.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        )

    await message.answer(text)


# =========================
# FILE MATCHING
# =========================

@dp.message(F.text == "🔎 پیشنهاد فایل")
async def matching_info(
    message: Message
):

    await message.answer(
        "🔎 موتور پیشنهاد فایل\n\n"
        "در مرحله بعد بر اساس:\n"
        "💰 بودجه\n"
        "📍 محدوده\n"
        "📐 متراژ\n"
        "🏠 نوع ملک\n"
        "🛏️ تعداد خواب\n\n"
        "فایل‌های مناسب مشتری را رتبه‌بندی می‌کنیم."
    )


# =========================
# OTHER BUTTONS
# =========================

@dp.message(F.text == "➕ ثبت مشتری")
async def add_client(
    message: Message
):

    await message.answer(
        "➕ ثبت مشتری\n\n"
        "فرم ثبت مشتری را در مرحله بعد فعال می‌کنیم."
    )


@dp.message(F.text == "👀 ثبت بازدید")
async def add_visit(
    message: Message
):

    await message.answer(
        "👀 ثبت بازدید\n\n"
        "در مرحله بعد مشتری و فایل را انتخاب می‌کنیم و "
        "سیستم بازدیدهای تکراری را کنترل خواهد کرد."
    )


@dp.message(F.text == "📞 پیگیری")
async def follow_up(
    message: Message
):

    await message.answer(
        "📞 پیگیری\n\n"
        "سیستم پیگیری‌ها در مرحله بعد فعال می‌شود."
    )


# =========================
# RUN
# =========================

async def main():

    await init_db()

    bot = Bot(
        token=BOT_TOKEN
    )

    print(
        "🏙️ شهردار ایران‌زمین is running..."
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
