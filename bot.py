import os
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
        Integer, primary_key=True
    )

    telegram_id: Mapped[int] = mapped_column(
        Integer, unique=True
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
        Integer, primary_key=True
    )

    code: Mapped[str] = mapped_column(
        String(50), unique=True
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

    owner_name: Mapped[str] = mapped_column(
        String(100)
    )

    owner_phone: Mapped[str] = mapped_column(
        String(50)
    )

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
        Integer, primary_key=True
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
        Integer, primary_key=True
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
        Integer, primary_key=True
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
async def start(message: Message):

    await get_or_create_user(message)

    await message.answer(
        "🏙️ شهردار ایران‌زمین\n"
        "Hooman Real Estate\n\n"
        "سیستم مدیریت فایل، مشتری و تیم آماده است.\n\n"
        "از منوی پایین انتخاب کن:",
        reply_markup=MAIN_MENU
    )


# =========================
# PROPERTIES
# =========================

@dp.message(F.text == "🏠 فایل‌ها")
async def properties(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(Property)
            .order_by(Property.created_at.desc())
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
            f"📐 {p.sqm} متر\n"
            f"💰 {p.price:,.0f}\n\n"
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
            .order_by(Client.created_at.desc())
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
            f"📐 {c.desired_sqm} متر\n\n"
        )

    await message.answer(text)


# =========================
# KPI
# =========================

async def get_kpi(user_id):

    async with Session() as session:

        properties = await session.scalar(
            select(func.count(Property.id))
            .where(Property.created_by == user_id)
        )

        clients = await session.scalar(
            select(func.count(Client.id))
            .where(Client.created_by == user_id)
        )

        visits = await session.scalar(
            select(func.count(Visit.id))
            .where(Visit.agent_id == user_id)
        )

        activities = await session.scalar(
            select(func.count(Activity.id))
            .where(Activity.user_id == user_id)
        )

    return (
        properties or 0,
        clients or 0,
        visits or 0,
        activities or 0
    )


@dp.message(F.text == "📊 KPI من")
async def my_kpi(message: Message):

    user = await get_or_create_user(message)

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
async def latest_activities(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(Activity)
            .order_by(Activity.created_at.desc())
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
            f"🕐 {a.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        )

    await message.answer(text)


# =========================
# FILE MATCHING
# =========================

@dp.message(F.text == "🔎 پیشنهاد فایل")
async def matching_info(message: Message):

    await message.answer(
        "🔎 موتور پیشنهاد فایل\n\n"
        "در نسخه بعدی این بخش بر اساس:\n"
        "💰 بودجه\n"
        "📍 محدوده\n"
        "📐 متراژ\n"
        "🏠 نوع ملک\n"
        "بهترین فایل‌ها را برای هر مشتری پیدا می‌کند."
    )


# =========================
# OTHER BUTTONS
# =========================

@dp.message(F.text == "➕ ثبت فایل")
async def add_property(message: Message):

    await message.answer(
        "➕ ثبت فایل\n\n"
        "فرم ثبت فایل را در مرحله بعد فعال می‌کنیم."
    )


@dp.message(F.text == "➕ ثبت مشتری")
async def add_client(message: Message):

    await message.answer(
        "➕ ثبت مشتری\n\n"
        "فرم ثبت مشتری را در مرحله بعد فعال می‌کنیم."
    )


@dp.message(F.text == "👀 ثبت بازدید")
async def add_visit(message: Message):

    await message.answer(
        "👀 ثبت بازدید\n\n"
        "در مرحله بعد مشتری و فایل را انتخاب می‌کنیم و "
        "سیستم بازدیدهای تکراری را کنترل خواهد کرد."
    )


@dp.message(F.text == "📞 پیگیری")
async def follow_up(message: Message):

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
