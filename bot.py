import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Message,
)

# Bot tokeningiz
TOKEN = "9255758010:AAGBuwrm3sKAXI6l8FiUmeMOA4J56jCAfxA"

# --- FAKAT O'ZINGizNING KANALLARINGIZ (Boshqa begona kanal yo'q!) ---
CHANNELS = [
    "@Mafiya_baku_02",
    "@Vertex_trading_official",
    "@Random_suhbat_bot_official",
]

# Promokod
VALID_PROMOCODE = "ADMIN_AKA"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- BAZA BILAN ISHLASH ---
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    name TEXT,
    age INTEGER,
    gender TEXT,
    search_gender TEXT DEFAULT 'Farqi yo''q',
    is_premium INTEGER DEFAULT 0,
    chats_count INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS queue (
    user_id INTEGER PRIMARY KEY,
    gender TEXT,
    search_gender TEXT,
    is_premium INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS active_chats (
    user_id INTEGER PRIMARY KEY,
    partner_id INTEGER
)
""")
conn.commit()


# --- FSM (Holatlar) ---
class RegState(StatesGroup):
  waiting_for_name = State()
  waiting_for_age = State()
  waiting_for_gender = State()
  waiting_for_search_gender = State()


class PromoState(StatesGroup):
  waiting_for_promo = State()


# --- FAFAQAT O'ZINGIZNING KANALLaringizNI TEKSHIRISH ---
async def check_subscriptions(user_id: int) -> bool:
  for channel in CHANNELS:
    try:
      member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
      if member.status not in ["member", "administrator", "creator"]:
        return False
    except Exception:
      return False
  return True


def get_sub_keyboard():
  keyboard = []
  for ch in CHANNELS:
    keyboard.append([InlineKeyboardButton(text=f"📢 Obuna bo'lish", url=f"https://t.me/{ch.lstrip('@')}")])
  keyboard.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
  return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --- MENYU TUGMALARI ---
def get_main_menu_keyboard(is_premium: int):
  prem_btn = "👑 VIP qidirish" if is_premium else "⭐ Premium olish"
  return ReplyKeyboardMarkup(
      keyboard=[
          [KeyboardButton(text="🔍 Do'st qidirish"), KeyboardButton(text="👤 Mening hisobim")],
          [KeyboardButton(text=prem_btn), KeyboardButton(text="📊 Statistika")]
      ],
      resize_keyboard=True
  )


# --- ASOSIY MENYU ---
async def show_main_menu(message: Message, state: FSMContext):
  await state.clear()
  user_id = message.from_user.id
  
  cursor.execute("SELECT name, age, gender, is_premium FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  
  if not row or not row[0] or row[1] is None or not row[2]:
    await message.answer("Ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RegState.waiting_for_name)
    return

  is_prem = row[3]
  await message.answer("Asosiy menyu:", reply_markup=get_main_menu_keyboard(is_prem))


# --- START ---
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
  await state.clear()
  user_id = message.from_user.id
  username = message.from_user.username

  cursor.execute(
      "INSERT OR IGNORE INTO users (user_id, username, is_premium, chats_count) VALUES (?, ?, 0, 0)",
      (user_id, username),
  )
  cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
  conn.commit()

  is_subbed = await check_subscriptions(user_id)
  if not is_subbed:
    channels_text = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(CHANNELS)])
    await message.answer(
        f"❌ Botdan foydalanish uchun quyidagi barcha kanallarga obuna bo'lishingiz shart:\n\n"
        f"{channels_text}\n\n"
        "Obuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing:",
        reply_markup=get_sub_keyboard(),
        parse_mode="HTML",
    )
    return

  await show_main_menu(message, state)


@router.callback_query(F.data == "check_sub")
async def process_check_sub(callback: CallbackQuery, state: FSMContext):
  user_id = callback.from_user.id
  is_subbed = await check_subscriptions(user_id)
  if not is_subbed:
    await callback.answer("Siz hali hamma kanalga obuna bo'lmadingiz! ❌", show_alert=True)
    return

  await callback.message.delete()
  await show_main_menu(callback.message, state)


# --- ANKETA JARAYONI ---
@router.message(RegState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
  name = message.text.strip()
  if len(name) < 2:
    await message.answer("Iltimos, haqiqiy ismingizni kiriting:")
    return

  await state.update_data(name=name)
  await message.answer("Yoshingizni kiriting (16 dan 99 gacha):")
  await state.set_state(RegState.waiting_for_age)


@router.message(RegState.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
  if not message.text.isdigit():
    await message.answer("Iltimos, yoshni faqat raqamlar bilan kiriting!")
    return
  
  age = int(message.text)
  if not (16 <= age <= 99):
    await message.answer("❌ Xato! 16 dan 99 gacha bo'lgan yoshni kiriting:")
    return

  await state.update_data(age=age)
  
  keyboard = InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text="👨 Erkak", callback_data="gender_male"),
       InlineKeyboardButton(text="👩 Ayol", callback_data="gender_female")]
  ])
  await message.answer("Jinsingizni tanlang:", reply_markup=keyboard)
  await state.set_state(RegState.waiting_for_gender)


@router.callback_query(RegState.waiting_for_gender, F.data.startswith("gender_"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
  gender = "Erkak" if callback.data == "gender_male" else "Ayol"
  data = await state.get_data()
  name = data.get("name")
  age = data.get("age")
  user_id = callback.from_user.id
  username = callback.from_user.username

  cursor.execute(
      "UPDATE users SET username = ?, name = ?, age = ?, gender = ? WHERE user_id = ?",
      (username, name, age, gender, user_id)
  )
  conn.commit()
  await state.clear()
  await callback.message.delete()
  
  await callback.message.answer("TAYYOR (agar ismingizni qayta soʻrasa /start tugmasini bosing)")
  
  cursor.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  is_prem = row[0] if row else 0
  await show_main_menu(callback.message, state)


# --- STATISTIKA ---
@router.message(F.text == "📊 Statistika")
async def show_statistics(message: Message, state: FSMContext):
  user_id = message.from_user.id
  is_subbed = await check_subscriptions(user_id)
  if not is_subbed:
    channels_text = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(CHANNELS)])
    await message.answer(
        f"❌ Botdan foydalanish uchun quyidagi barcha kanallarga obuna bo'lishingiz shart:\n\n"
        f"{channels_text}\n\n"
        "Obuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing:",
        reply_markup=get_sub_keyboard(),
        parse_mode="HTML"
    )
    return

  cursor.execute("SELECT COUNT(*) FROM users")
  total_users = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(*) FROM queue")
  online_queue = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(DISTINCT user_id) FROM active_chats")
  active_chats_count = cursor.fetchone()[0]

  cursor.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  is_prem = row[0] if row else 0

  text = (
      f"📊 <b>Bot statistikasi:</b>\n\n"
      f"👥 Jami ro'yxatdan o'tganlar: {total_users} ta\n"
      f"🔍 Qidiruvda kutayotganlar: {online_queue} ta\n"
      f"💬 Hozirda suhbatlashayotganlar: {active_chats_count} ta"
  )
  await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu_keyboard(is_prem))


# --- MENING HISOBIM VA TAHRIRLASH ---
@router.message(F.text == "👤 Mening hisobim")
async def my_profile(message: Message, state: FSMContext):
  user_id = message.from_user.id
  is_subbed = await check_subscriptions(user_id)
  if not is_subbed:
    channels_text = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(CHANNELS)])
    await message.answer(
        f"❌ Botdan foydalanish uchun quyidagi barcha kanallarga obuna bo'lishingiz shart:\n\n"
        f"{channels_text}\n\n"
        "Obuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing:",
        reply_markup=get_sub_keyboard(),
        parse_mode="HTML"
    )
    return

  cursor.execute("SELECT name, age, gender, is_premium, chats_count FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  
  if not row:
    await show_main_menu(message, state)
    return

  name, age, gender, is_prem, chats_count = row
  prem_status = "⭐ Faol (Premium)" if is_prem else "👤 Yo'q (Oddiy)"
  
  text = (
      f"<b>📊 Sizning hisobingiz:</b>\n\n"
      f"👤 Ism: {name} (@{message.from_user.username or 'Mavjud emas'})\n"
      f"📅 Yosh: {age}\n"
      f"🚻 Jins: {gender}\n"
      f"💬 Suhbatlar soni: {chats_count} ta\n"
      f"⭐ Premium: {prem_status}"
  )

  keyboard = InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text="⚙️ Anketani tahrirlash", callback_data="reset_profile")],
  ])
  
  await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "reset_profile")
async def reset_profile(callback: CallbackQuery, state: FSMContext):
  await callback.message.delete()
  await callback.message.answer("Ismingizni kiriting:", reply_markup
  
