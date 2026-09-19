import asyncio
import math
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from sqlalchemy import (
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    select,
    func,
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

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

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

PROPERTY_STATUSES = [
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
]

CLIENT_STATUSES = [
    "فعال",
    "خرید کرده",
    "منصرف شده",
]


# =========================================================
# DATABASE
# =========================================================

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[int] = mapped_column(Integer, default=1)


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    code: Mapped[str] = mapped_column(
        String(100), unique=True, index=True
    )

    area: Mapped[str] = mapped_column(String(200), default="")
    address: Mapped[str] = mapped_column(Text, default="")

    sqm: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[int] = mapped_column(Integer, default=0)

    property_type: Mapped[str] = mapped_column(
        String(100), default=""
    )

    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    floors: Mapped[int] = mapped_column(Integer, default=0)
    unit_floor: Mapped[int] = mapped_column(Integer, default=0)
    units_per_floor: Mapped[int] = mapped_column(Integer, default=0)

    year_built: Mapped[int] = mapped_column(
        Integer, default=0, index=True
    )

    elevator: Mapped[str] = mapped_column(String(50), default="")
    parking: Mapped[str] = mapped_column(String(50), default="")
    parking_type: Mapped[str] = mapped_column(String(100), default="")
    storage: Mapped[str] = mapped_column(String(50), default="")

    tenant: Mapped[str] = mapped_column(String(100), default="")
    deposit: Mapped[int] = mapped_column(Integer, default=0)
    rent: Mapped[int] = mapped_column(Integer, default=0)
    vacancy_date: Mapped[str] = mapped_column(String(100), default="")

    document_type: Mapped[str] = mapped_column(String(200), default="")

    owner_name: Mapped[str] = mapped_column(
        String(200), default="", index=True
    )
    owner_phone: Mapped[str] = mapped_column(
        String(100), default="", index=True
    )

    description: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[str] = mapped_column(
        String(100),
        default="🟢 فعال",
        index=True
    )

    transaction_value: Mapped[int] = mapped_column(
        Integer, default=0
    )

    created_by: Mapped[int] = mapped_column(
        Integer, default=0, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    code: Mapped[str] = mapped_column(
        String(100), unique=True, index=True
    )

    name: Mapped[str] = mapped_column(
        String(200), default="", index=True
    )

    phone: Mapped[str] = mapped_column(
        String(100), default="", index=True
    )

    area: Mapped[str] = mapped_column(
        String(200), default=""
    )

    min_budget: Mapped[int] = mapped_column(
        Integer, default=0
    )

    max_budget: Mapped[int] = mapped_column(
        Integer, default=0
    )

    min_sqm: Mapped[int] = mapped_column(
        Integer, default=0
    )

    max_sqm: Mapped[int] = mapped_column(
        Integer, default=0
    )

    property_type: Mapped[str] = mapped_column(
        String(100), default=""
    )

    min_year_built: Mapped[int] = mapped_column(
        Integer, default=0
    )

    max_year_built: Mapped[int] = mapped_column(
        Integer, default=0
    )

    description: Mapped[str] = mapped_column(
        Text, default=""
    )

    status: Mapped[str] = mapped_column(
        String(100),
        default="فعال",
        index=True
    )

    created_by: Mapped[int] = mapped_column(
        Integer, default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id")
    )

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id")
    )

    user_id: Mapped[int] = mapped_column(
        Integer, default=0
    )

    interest: Mapped[int] = mapped_column(Integer, default=0)
    price_reaction: Mapped[int] = mapped_column(Integer, default=0)
    property_reaction: Mapped[int] = mapped_column(Integer, default=0)

    objection: Mapped[str] = mapped_column(Text, default="")
    next_action: Mapped[str] = mapped_column(Text, default="")
    followup_date: Mapped[str] = mapped_column(String(100), default="")
    note: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        Integer, default=0
    )

    activity_type: Mapped[str] = mapped_column(
        String(100), default=""
    )

    description: Mapped[str] = mapped_column(
        Text, default=""
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class PropertyHistory(Base):
    __tablename__ = "property_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id")
    )

    user_id: Mapped[int] = mapped_column(
        Integer, default=0
    )

    field: Mapped[str] = mapped_column(
        String(100), default=""
    )

    old_value: Mapped[str] = mapped_column(
        Text, default=""
    )

    new_value: Mapped[str] = mapped_column(
        Text, default=""
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


# =========================================================
# BOT
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


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
    interest = State()
    price_reaction = State()
    property_reaction = State()
    objection = State()
    next_action = State()
    followup_date = State()
    note = State()


# =========================================================
# HELPERS
# =========================================================

def allowed(user_id: int) -> bool:
    return not ADMIN_IDS or user_id in ADMIN_IDS


def admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def main_keyboard(user_id: int):
    rows = [
        [
            KeyboardButton(text="➕ ثبت فایل"),
            KeyboardButton(text="👤 ثبت مشتری"),
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

    if admin(user_id):
        rows += [
            [
                KeyboardButton(text="📊 KPI تیم"),
                KeyboardButton(text="🕘 آخرین فعالیت‌ها"),
            ]
        ]

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True
    )


def money(value: int) -> str:
    if not value:
        return "—"

    return f"{value:,}"


def parse_int(text: str) -> int:
    text = (
        text.replace(",", "")
        .replace("٬", "")
        .replace(" ", "")
    )

    if not text:
        return 0

    return int(text)


async def activity(
    session: AsyncSession,
    user_id: int,
    activity_type: str,
    description: str,
):
    session.add(
        Activity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
        )
    )


# =========================================================
# START
# =========================================================

@router.message(Command("start"))
async def start(message: Message):
    if not allowed(message.from_user.id):
        await message.answer("⛔ دسترسی شما مجاز نیست.")
        return

    await message.answer(
        "🏙️ <b>شهردار ایران‌زمین</b>\n\n"
        "سیستم مدیریت فایل، مشتری و فروش املاک",
        parse_mode="HTML",
        reply_markup=main_keyboard(message.from_user.id)
    )


@router.message(Command("id"))
async def get_id(message: Message):
    await message.answer(
        f"🆔 Telegram ID:\n{message.from_user.id}"
    )


# =========================================================
# PROPERTY REGISTRATION
# =========================================================

PROPERTY_STEPS = [
    ("code", "کد فایل را وارد کن:"),
    ("area", "منطقه / محله را وارد کن:"),
    ("address", "آدرس را وارد کن:"),
    ("sqm", "متراژ را وارد کن:"),
    ("price", "قیمت کل را وارد کن:"),
    ("property_type", "نوع ملک را وارد کن:"),
    ("bedrooms", "تعداد خواب:"),
    ("floors", "تعداد طبقات:"),
    ("unit_floor", "طبقه واحد:"),
    ("units_per_floor", "تعداد واحد در طبقه:"),
    ("year_built", "سال ساخت:"),
    ("elevator", "آسانسور دارد؟"),
    ("parking", "پارکینگ دارد؟"),
    ("parking_type", "نوع پارکینگ:"),
    ("storage", "انباری دارد؟"),
    ("tenant", "وضعیت مستأجر:"),
    ("deposit", "رهن:"),
    ("rent", "اجاره:"),
    ("vacancy_date", "تاریخ تخلیه:"),
    ("document_type", "نوع سند:"),
    ("owner_name", "نام مالک:"),
    ("owner_phone", "شماره مالک:"),
    ("description", "توضیحات فایل:")
]


@router.message(F.text == "➕ ثبت فایل")
async def property_start(message: Message, state: FSMContext):
    if not allowed(message.from_user.id):
        return

    await state.clear()
    await state.set_state(PropertyForm.code)

    await message.answer(
        "➕ <b>ثبت فایل جدید</b>\n\n"
        "کد فایل را وارد کن:",
        parse_mode="HTML"
    )


@router.message(PropertyForm.code)
async def property_code(message: Message, state: FSMContext):
    code = message.text.strip()

    async with SessionLocal() as session:
        exists = (
            await session.execute(
                select(Property)
                .where(Property.code == code)
            )
        ).scalar_one_or_none()

    if exists:
        await message.answer(
            "⚠️ این کد قبلاً ثبت شده.\n"
            "یک کد دیگر وارد کن."
        )
        return

    await state.update_data(code=code)
    await state.set_state(PropertyForm.area)
    await message.answer("📍 منطقه / محله:")


@router.message(PropertyForm.area)
async def property_area(message: Message, state: FSMContext):
    await state.update_data(area=message.text.strip())
    await state.set_state(PropertyForm.address)
    await message.answer("📌 آدرس:")


@router.message(PropertyForm.address)
async def property_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await state.set_state(PropertyForm.sqm)
    await message.answer("📐 متراژ:")


@router.message(PropertyForm.sqm)
async def property_sqm(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("فقط عدد وارد کن.")
        return

    await state.update_data(sqm=value)
    await state.set_state(PropertyForm.price)
    await message.answer("💰 قیمت کل:")


@router.message(PropertyForm.price)
async def property_price(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("فقط عدد وارد کن.")
        return

    await state.update_data(price=value)
    await state.set_state(PropertyForm.property_type)
    await message.answer("🏠 نوع ملک:")


@router.message(PropertyForm.property_type)
async def property_type(message: Message, state: FSMContext):
    await state.update_data(property_type=message.text.strip())
    await state.set_state(PropertyForm.bedrooms)
    await message.answer("🛏 تعداد خواب:")


@router.message(PropertyForm.bedrooms)
async def property_bedrooms(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(bedrooms=value)
    await state.set_state(PropertyForm.floors)
    await message.answer("🏢 تعداد طبقات:")


@router.message(PropertyForm.floors)
async def property_floors(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(floors=value)
    await state.set_state(PropertyForm.unit_floor)
    await message.answer("طبقه واحد:")


@router.message(PropertyForm.unit_floor)
async def property_unit_floor(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(unit_floor=value)
    await state.set_state(PropertyForm.units_per_floor)
    await message.answer("تعداد واحد در هر طبقه:")


@router.message(PropertyForm.units_per_floor)
async def property_units(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(units_per_floor=value)
    await state.set_state(PropertyForm.year_built)
    await message.answer("🏗 سال ساخت:")


@router.message(PropertyForm.year_built)
async def property_year(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("سال ساخت باید عدد باشد.")
        return

    await state.update_data(year_built=value)
    await state.set_state(PropertyForm.elevator)
    await message.answer("🛗 آسانسور دارد؟")


@router.message(PropertyForm.elevator)
async def property_elevator(message: Message, state: FSMContext):
    await state.update_data(elevator=message.text.strip())
    await state.set_state(PropertyForm.parking)
    await message.answer("🚗 پارکینگ دارد؟")


@router.message(PropertyForm.parking)
async def property_parking(message: Message, state: FSMContext):
    await state.update_data(parking=message.text.strip())
    await state.set_state(PropertyForm.parking_type)
    await message.answer("نوع پارکینگ:")


@router.message(PropertyForm.parking_type)
async def property_parking_type(message: Message, state: FSMContext):
    await state.update_data(parking_type=message.text.strip())
    await state.set_state(PropertyForm.storage)
    await message.answer("انباری دارد؟")


@router.message(PropertyForm.storage)
async def property_storage(message: Message, state: FSMContext):
    await state.update_data(storage=message.text.strip())
    await state.set_state(PropertyForm.tenant)
    await message.answer("وضعیت مستأجر:")


@router.message(PropertyForm.tenant)
async def property_tenant(message: Message, state: FSMContext):
    await state.update_data(tenant=message.text.strip())
    await state.set_state(PropertyForm.deposit)
    await message.answer("رهن:")


@router.message(PropertyForm.deposit)
async def property_deposit(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(deposit=value)
    await state.set_state(PropertyForm.rent)
    await message.answer("اجاره:")


@router.message(PropertyForm.rent)
async def property_rent(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(rent=value)
    await state.set_state(PropertyForm.vacancy_date)
    await message.answer("تاریخ تخلیه:")


@router.message(PropertyForm.vacancy_date)
async def property_vacancy(message: Message, state: FSMContext):
    await state.update_data(vacancy_date=message.text.strip())
    await state.set_state(PropertyForm.document_type)
    await message.answer("نوع سند:")


@router.message(PropertyForm.document_type)
async def property_document(message: Message, state: FSMContext):
    await state.update_data(document_type=message.text.strip())
    await state.set_state(PropertyForm.owner_name)
    await message.answer("👤 نام مالک:")


@router.message(PropertyForm.owner_name)
async def property_owner(message: Message, state: FSMContext):
    await state.update_data(owner_name=message.text.strip())
    await state.set_state(PropertyForm.owner_phone)
    await message.answer("📞 شماره مالک:")


@router.message(PropertyForm.owner_phone)
async def property_owner_phone(message: Message, state: FSMContext):
    await state.update_data(owner_phone=message.text.strip())
    await state.set_state(PropertyForm.description)
    await message.answer("📝 توضیحات:")


@router.message(PropertyForm.description)
async def property_description(
    message: Message,
    state: FSMContext
):
    await state.update_data(description=message.text.strip())

    data = await state.get_data()

    text = (
        "📋 <b>پیش‌نمایش فایل</b>\n\n"
        f"کد: {data['code']}\n"
        f"منطقه: {data['area']}\n"
        f"متراژ: {data['sqm']}\n"
        f"قیمت: {money(data['price'])}\n"
        f"نوع: {data['property_type']}\n"
        f"خواب: {data['bedrooms']}\n"
        f"سال ساخت: {data['year_built']}\n"
        f"مالک: {data['owner_name']}\n"
        f"تلفن: {data['owner_phone']}\n"
        f"توضیحات: {data['description']}"
    )

    await state.set_state(PropertyForm.confirm)

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ ثبت نهایی",
                        callback_data="property_save"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ لغو",
                        callback_data="cancel"
                    )
                ]
            ]
        )
    )


@router.callback_query(F.data == "property_save")
async def property_save(
    callback: CallbackQuery,
    state: FSMContext
):
    data = await state.get_data()

    async with SessionLocal() as session:
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
            year_built=data["year_built"],
            elevator=data["elevator"],
            parking=data["parking"],
            parking_type=data["parking_type"],
            storage=data["storage"],
            tenant=data["tenant"],
            deposit=data["deposit"],
            rent=data["rent"],
            vacancy_date=data["vacancy_date"],
            document_type=data["document_type"],
            owner_name=data["owner_name"],
            owner_phone=data["owner_phone"],
            description=data["description"],
            status="🟢 فعال",
            created_by=callback.from_user.id,
        )

        session.add(prop)

        await session.flush()

        await activity(
            session,
            callback.from_user.id,
            "ثبت فایل",
            f"فایل {prop.code} ثبت شد."
        )

        await session.commit()

    await state.clear()

    await callback.message.edit_text(
        "✅ فایل با موفقیت ثبت شد."
    )

    await callback.answer()


# =========================================================
# CLIENT REGISTRATION
# =========================================================

@router.message(F.text == "👤 ثبت مشتری")
async def client_start(
    message: Message,
    state: FSMContext
):
    await state.clear()
    await state.set_state(ClientForm.code)

    await message.answer(
        "👤 ثبت مشتری\n\nکد مشتری:"
    )


@router.message(ClientForm.code)
async def client_code(
    message: Message,
    state: FSMContext
):
    code = message.text.strip()

    async with SessionLocal() as session:
        exists = (
            await session.execute(
                select(Client)
                .where(Client.code == code)
            )
        ).scalar_one_or_none()

    if exists:
        await message.answer("این کد مشتری قبلاً ثبت شده.")
        return

    await state.update_data(code=code)
    await state.set_state(ClientForm.name)
    await message.answer("نام مشتری:")


@router.message(ClientForm.name)
async def client_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ClientForm.phone)
    await message.answer("شماره تماس:")


@router.message(ClientForm.phone)
async def client_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(ClientForm.area)
    await message.answer("منطقه موردنظر:")


@router.message(ClientForm.area)
async def client_area(message: Message, state: FSMContext):
    await state.update_data(area=message.text.strip())
    await state.set_state(ClientForm.min_budget)
    await message.answer("حداقل بودجه:")


@router.message(ClientForm.min_budget)
async def client_min_budget(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(min_budget=value)
    await state.set_state(ClientForm.max_budget)
    await message.answer("حداکثر بودجه:")


@router.message(ClientForm.max_budget)
async def client_max_budget(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(max_budget=value)
    await state.set_state(ClientForm.min_sqm)
    await message.answer("حداقل متراژ:")


@router.message(ClientForm.min_sqm)
async def client_min_sqm(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(min_sqm=value)
    await state.set_state(ClientForm.max_sqm)
    await message.answer("حداکثر متراژ:")


@router.message(ClientForm.max_sqm)
async def client_max_sqm(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(max_sqm=value)
    await state.set_state(ClientForm.property_type)
    await message.answer("نوع ملک:")


@router.message(ClientForm.property_type)
async def client_type(message: Message, state: FSMContext):
    await state.update_data(property_type=message.text.strip())
    await state.set_state(ClientForm.min_year_built)
    await message.answer(
        "حداقل سال ساخت موردنظر:\n"
        "اگر مهم نیست 0 وارد کن."
    )


@router.message(ClientForm.min_year_built)
async def client_min_year(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(min_year_built=value)
    await state.set_state(ClientForm.max_year_built)
    await message.answer(
        "حداکثر سال ساخت موردنظر:\n"
        "اگر مهم نیست 0 وارد کن."
    )


@router.message(ClientForm.max_year_built)
async def client_max_year(message: Message, state: FSMContext):
    try:
        value = parse_int(message.text)
    except:
        await message.answer("عدد وارد کن.")
        return

    await state.update_data(max_year_built=value)
    await state.set_state(ClientForm.description)
    await message.answer("توضیحات مشتری:")


@router.message(ClientForm.description)
async def client_description(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        description=message.text.strip()
    )

    data = await state.get_data()

    await state.set_state(ClientForm.confirm)

    await message.answer(
        "📋 <b>اطلاعات مشتری</b>\n\n"
        f"کد: {data['code']}\n"
        f"نام: {data['name']}\n"
        f"تلفن: {data['phone']}\n"
        f"منطقه: {data['area']}\n"
        f"بودجه: {money(data['min_budget'])}"
        f" تا {money(data['max_budget'])}\n"
        f"متراژ: {data['min_sqm']} تا {data['max_sqm']}\n"
        f"نوع: {data['property_type']}\n"
        f"سال ساخت: {data['min_year_built']} تا "
        f"{data['max_year_built']}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ ثبت",
                        callback_data="client_save"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ لغو",
                        callback_data="cancel"
                    )
                ]
            ]
        )
    )


@router.callback_query(F.data == "client_save")
async def client_save(
    callback: CallbackQuery,
    state: FSMContext
):
    data = await state.get_data()

    async with SessionLocal() as session:
        client = Client(
            code=data["code"],
            name=data["name"],
            phone=data["phone"],
            area=data["area"],
            min_budget=data["min_budget"],
            max_budget=data["max_budget"],
            min_sqm=data["min_sqm"],
            max_sqm=data["max_sqm"],
            property_type=data["property_type"],
            min_year_built=data["min_year_built"],
            max_year_built=data["max_year_built"],
            description=data["description"],
            status="فعال",
            created_by=callback.from_user.id,
        )

        session.add(client)

        await activity(
            session,
            callback.from_user.id,
            "ثبت مشتری",
            f"مشتری {client.name} ثبت شد."
        )

        await session.commit()

    await state.clear()

    await callback.message.edit_text(
        "✅ مشتری با موفقیت ثبت شد."
    )

    await callback.answer()


# =========================================================
# MATCHING
# =========================================================

def score_budget(client: Client, prop: Property) -> float:
    minimum = client.min_budget
    maximum = client.max_budget

    if minimum == 0 and maximum == 0:
        return 100

    if minimum and prop.price < minimum:
        return max(
            0,
            100 - ((minimum - prop.price) / minimum * 100)
        )

    if maximum and prop.price > maximum:
        return max(
            0,
            100 - ((prop.price - maximum) / maximum * 100)
        )

    return 100


def score_area(client: Client, prop: Property) -> float:
    if not client.area:
        return 100

    if client.area in (
        "همه",
        "همه مناطق",
        "فرقی ندارد",
    ):
        return 100

    return 100 if client.area in prop.area else 0


def score_year(client: Client, prop: Property) -> float:
    if (
        client.min_year_built == 0
        and client.max_year_built == 0
    ):
        return 100

    if prop.year_built == 0:
        return 0

    minimum = client.min_year_built
    maximum = client.max_year_built

    if minimum and prop.year_built < minimum:
        return max(
            0,
            100 - ((minimum - prop.year_built) / 20 * 100)
        )

    if maximum and prop.year_built > maximum:
        return max(
            0,
            100 - ((prop.year_built - maximum) / 20 * 100)
        )

    return 100


def score_sqm(client: Client, prop: Property) -> float:
    minimum = client.min_sqm
    maximum = client.max_sqm

    if minimum == 0 and maximum == 0:
        return 100

    if minimum and prop.sqm < minimum:
        return max(
            0,
            100 - ((minimum - prop.sqm) / minimum * 100)
        )

    if maximum and prop.sqm > maximum:
        return max(
            0,
            100 - ((prop.sqm - maximum) / maximum * 100)
        )

    return 100


def score_type(client: Client, prop: Property) -> float:
    if not client.property_type:
        return 100

    if client.property_type in (
        "همه",
        "فرقی ندارد",
    ):
        return 100

    return (
        100
        if client.property_type == prop.property_type
        else 0
    )


def matching_score(client: Client, prop: Property) -> float:
    return (
        score_budget(client, prop) * 0.40
        + score_area(client, prop) * 0.30
        + score_year(client, prop) * 0.15
        + score_sqm(client, prop) * 0.10
        + score_type(client, prop) * 0.05
    )


@router.message(F.text == "🎯 مچینگ مشتری")
async def matching_start(message: Message):
    async with SessionLocal() as session:
        clients = (
            await session.execute(
                select(Client)
                .where(Client.status == "فعال")
                .order_by(Client.id.desc())
            )
        ).scalars().all()

    if not clients:
        await message.answer(
            "مشتری فعال وجود ندارد."
        )
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=f"👤 {c.name} | {c.code}",
                callback_data=f"match_client:{c.id}"
            )
        ]
        for c in clients[:PAGE_SIZE]
    ]

    await message.answer(
        "🎯 مشتری را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )


@router.callback_query(F.data.startswith("match_client:"))
async def matching_client(callback: CallbackQuery):
    client_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:
        client = await session.get(Client, client_id)

        properties = (
            await session.execute(
                select(Property)
                .where(
                    Property.status.in_(
                        ACTIVE_PROPERTY_STATUSES
                    )
                )
            )
        ).scalars().all()

    if not client:
        await callback.answer(
            "مشتری پیدا نشد.",
            show_alert=True
        )
        return

    results = []

    for prop in properties:
        score = matching_score(client, prop)

        if score > 0:
            results.append(
                (score, prop)
            )

    results.sort(
        key=lambda x: x[0],
        reverse=True
    )

    if not results:
        await callback.message.edit_text(
            "فایل زنده مناسب با معیارهای این مشتری پیدا نشد."
        )
        await callback.answer()
        return

    text = (
        f"🎯 <b>مچینگ برای {client.name}</b>\n\n"
    )

    buttons = []

    for score, prop in results[:10]:
        text += (
            f"🏠 {prop.code}\n"
            f"📍 {prop.area}\n"
            f"📐 {prop.sqm} متر\n"
            f"💰 {money(prop.price)}\n"
            f"🏗 {prop.year_built or 'نامشخص'}\n"
            f"⭐ امتیاز: {score:.1f}%\n"
            "────────────\n"
        )

        buttons.append([
            InlineKeyboardButton(
                text=f"🏠 مشاهده {prop.code}",
                callback_data=f"property:{prop.id}"
            )
        ])

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


# =========================================================
# PROPERTY DETAIL
# =========================================================

@router.callback_query(F.data.startswith("property:"))
async def property_detail(callback: CallbackQuery):
    property_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:
        prop = await session.get(
            Property,
            property_id
        )

    if not prop:
        await callback.answer(
            "فایل پیدا نشد.",
            show_alert=True
        )
        return

    text = (
        "🏠 <b>جزئیات فایل</b>\n\n"
        f"کد: {prop.code}\n"
        f"📍 منطقه: {prop.area}\n"
        f"📌 آدرس: {prop.address}\n"
        f"📐 متراژ: {prop.sqm}\n"
        f"💰 قیمت: {money(prop.price)}\n"
        f"🏠 نوع: {prop.property_type}\n"
        f"🛏 خواب: {prop.bedrooms}\n"
        f"🏢 طبقات: {prop.floors}\n"
        f"🔢 طبقه: {prop.unit_floor}\n"
        f"🏗 سال ساخت: {prop.year_built or 'نامشخص'}\n"
        f"🛗 آسانسور: {prop.elevator}\n"
        f"🚗 پارکینگ: {prop.parking}\n"
        f"📦 انباری: {prop.storage}\n"
        f"📄 سند: {prop.document_type}\n"
        f"👤 مالک: {prop.owner_name}\n"
        f"📞 {prop.owner_phone}\n"
        f"📌 وضعیت: {prop.status}\n\n"
        f"📝 {prop.description}"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🕘 تاریخچه",
                        callback_data=f"history:{prop.id}"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# =========================================================
# OWNER FILES
# =========================================================

@router.message(F.text == "🏠 فایل‌های مالک")
async def owner_files(message: Message):
    await message.answer(
        "نام یا شماره مالک را وارد کن."
    )


@router.message(
    lambda m: (
        m.text
        and not m.text.startswith("/")
        and len(m.text) > 3
        and m.text not in {
            "➕ ثبت فایل",
            "👤 ثبت مشتری",
            "🔎 جستجوی فایل",
            "🔎 جستجوی مشتری",
            "🎯 مچینگ مشتری",
            "🏠 فایل‌های مالک",
            "📅 ثبت بازدید",
            "📌 پیگیری‌ها",
            "📊 KPI من",
            "📊 KPI تیم",
            "🕘 آخرین فعالیت‌ها",
        }
    )
)
async def owner_search(message: Message):
    # فقط زمانی اجرا می‌شود که متن شبیه شماره یا نام مالک باشد.
    # برای جلوگیری از تداخل، جستجو را فقط در صورتی انجام می‌دهیم
    # که نتیجه‌ای وجود داشته باشد.

    query = message.text.strip()

    async with SessionLocal() as session:
        result = await session.execute(
            select(Property)
            .where(
                (
                    Property.owner_name.ilike(
                        f"%{query}%"
                    )
                )
                |
                (
                    Property.owner_phone.ilike(
                        f"%{query}%"
                    )
                )
            )
            .where(
                Property.status.in_(
                    ACTIVE_PROPERTY_STATUSES
                )
            )
        )

        properties = result.scalars().all()

    if not properties:
        return

    text = "🏠 <b>فایل‌های مالک</b>\n\n"

    for p in properties:
        text += (
            f"کد: {p.code}\n"
            f"منطقه: {p.area}\n"
            f"متراژ: {p.sqm}\n"
            f"قیمت: {money(p.price)}\n"
            "────────────\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# FOLLOW UPS
# =========================================================

@router.message(F.text == "📌 پیگیری‌ها")
async def followups(message: Message):
    async with SessionLocal() as session:
        visits = (
            await session.execute(
                select(Visit)
                .where(
                    Visit.followup_date != ""
                )
                .order_by(
                    Visit.id.desc()
                )
                .limit(20)
            )
        ).scalars().all()

        if not visits:
            await message.answer(
                "📌 پیگیری ثبت‌شده‌ای وجود ندارد."
            )
            return

        text = "📌 <b>پیگیری‌ها</b>\n\n"

        for visit in visits:
            client = await session.get(
                Client,
                visit.client_id
            )

            prop = await session.get(
                Property,
                visit.property_id
            )

            text += (
                f"👤 {client.name if client else '-'}\n"
                f"🏠 {prop.code if prop else '-'}\n"
                f"📅 {visit.followup_date}\n"
                f"➡️ {visit.next_action or '-'}\n"
                "────────────\n"
            )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# KPI
# =========================================================

@router.message(F.text == "📊 KPI من")
async def my_kpi(message: Message):
    user_id = message.from_user.id

    async with SessionLocal() as session:

        activities = (
            await session.execute(
                select(func.count(Activity.id))
                .where(
                    Activity.user_id == user_id
                )
            )
        ).scalar() or 0

        visits = (
            await session.execute(
                select(func.count(Visit.id))
                .where(
                    Visit.user_id == user_id
                )
            )
        ).scalar() or 0

        files = (
            await session.execute(
                select(func.count(Property.id))
                .where(
                    Property.created_by == user_id
                )
            )
        ).scalar() or 0

        active_files = (
            await session.execute(
                select(func.count(Property.id))
                .where(
                    Property.created_by == user_id,
                    Property.status.in_(
                        ACTIVE_PROPERTY_STATUSES
                    )
                )
            )
        ).scalar() or 0

        sold = (
            await session.execute(
                select(func.count(Property.id))
                .where(
                    Property.created_by == user_id,
                    Property.status ==
                    "🔵 معامله شد - توسط ما"
                )
            )
        ).scalar() or 0

    await message.answer(
        "📊 <b>KPI من</b>\n\n"
        f"📌 فعالیت‌ها: {activities}\n"
        f"📅 بازدیدها: {visits}\n"
        f"🏠 فایل ثبت‌شده: {files}\n"
        f"🟢 فایل فعال: {active_files}\n"
        f"🔵 معامله توسط ما: {sold}",
        parse_mode="HTML"
    )


@router.message(F.text == "📊 KPI تیم")
async def team_kpi(message: Message):
    if not admin(message.from_user.id):
        await message.answer(
            "⛔ این بخش فقط برای ادمین است."
        )
        return

    async with SessionLocal() as session:
        users = (
            await session.execute(
                select(User)
                .where(User.active == 1)
            )
        ).scalars().all()

        if not users:
            await message.answer(
                "هنوز عضوی ثبت نشده."
            )
            return

        text = "📊 <b>KPI تیم</b>\n\n"

        for user in users:

            activities = (
                await session.execute(
                    select(func.count(Activity.id))
                    .where(
                        Activity.user_id ==
                        user.telegram_id
                    )
                )
            ).scalar() or 0

            visits = (
                await session.execute(
                    select(func.count(Visit.id))
                    .where(
                        Visit.user_id ==
                        user.telegram_id
                    )
                )
            ).scalar() or 0

            files = (
                await session.execute(
                    select(func.count(Property.id))
                    .where(
                        Property.created_by ==
                        user.telegram_id
                    )
                )
            ).scalar() or 0

            text += (
                f"👤 <b>{user.name}</b>\n"
                f"فعالیت: {activities}\n"
                f"بازدید: {visits}\n"
                f"فایل: {files}\n"
                "────────────\n"
            )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# LAST ACTIVITIES
# =========================================================

@router.message(F.text == "🕘 آخرین فعالیت‌ها")
async def last_activities(message: Message):
    if not admin(message.from_user.id):
        await message.answer(
            "⛔ این بخش فقط برای ادمین است."
        )
        return

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Activity)
                .order_by(
                    Activity.id.desc()
                )
                .limit(30)
            )
        ).scalars().all()

    if not rows:
        await message.answer(
            "فعالیتی ثبت نشده."
        )
        return

    text = "🕘 <b>آخرین فعالیت‌ها</b>\n\n"

    for row in rows:
        text += (
            f"#{row.id} | {row.activity_type}\n"
            f"{row.description}\n"
            f"👤 {row.user_id}\n"
            f"🕒 {row.created_at}\n"
            "────────────\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# PROPERTY HISTORY
# =========================================================

@router.callback_query(
    F.data.startswith("history:")
)
async def property_history(callback: CallbackQuery):
    property_id = int(
        callback.data.split(":")[1]
    )

    async with SessionLocal() as session:
        history = (
            await session.execute(
                select(PropertyHistory)
                .where(
                    PropertyHistory.property_id ==
                    property_id
                )
                .order_by(
                    PropertyHistory.id.desc()
                )
                .limit(50)
            )
        ).scalars().all()

    if not history:
        await callback.message.answer(
            "برای این فایل هنوز تاریخچه‌ای ثبت نشده."
        )
        await callback.answer()
        return

    text = "🕘 <b>تاریخچه فایل</b>\n\n"

    for h in history:
        text += (
            f"🔹 {h.field}\n"
            f"قبلی: {h.old_value}\n"
            f"جدید: {h.new_value}\n"
            f"🕒 {h.created_at}\n"
            "────────────\n"
        )

    await callback.message.answer(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# CANCEL
# =========================================================

@router.callback_query(F.data == "cancel")
async def cancel_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()

    await callback.message.edit_text(
        "❌ عملیات لغو شد."
    )

    await callback.answer()


# =========================================================
# DATABASE INIT
# =========================================================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )


# =========================================================
# MAIN
# =========================================================

async def main():
    await init_db()

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    print(
        "🏙️ Shahrdare Iran Zamin started..."
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
