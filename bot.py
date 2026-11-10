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
    Message,
)

# Bot tokeningiz
TOKEN = "9255758010:AAGBuwrm3sKAXI6l8FiUmeMOA4J56jCAfxA"

# Majburiy obuna kanallari
CHANNELS = [
    "@Mafiya_baku_02",
    "@Vertex_trading_official",
    "@Random_suhbat_bot_official",
]

# Yangi promokod
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
    age INTEGER,
    gender TEXT,
    search_gender TEXT,
    is_premium INTEGER DEFAULT 0,
    chats_count INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS queue (
    user_id INTEGER PRIMARY KEY,
    gender TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS active_chats (
    user1 INTEGER PRIMARY KEY,
    user2 INTEGER
)
""")
conn.commit()


# --- FSM (Holatlar) ---
class RegState(StatesGroup):
  waiting_for_age = State()
  waiting_for_gender = State()
  waiting_for_search_gender = State()


class PromoState(StatesGroup):
  waiting_for_promo = State()


# --- OBUNANI TEKSHIRish ---
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


# --- ASOSIY MENYU ---
async def show_main_menu(message: Message, state: FSMContext):
  await state.clear()
  user_id = message.from_user.id
  
  cursor.execute("SELECT age, gender FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  
  # Agar anketa to'ldirilmagan bo'lsa
  if not row or row[0] is None or row[1] is None:
    await message.answer("Yoshingizni kiriting (16 dan 99 gacha):")
    await state.set_state(RegState.waiting_for_age)
    return

  keyboard = InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text="🔍 Do'st qidirish", callback_data="search_partner")],
      [InlineKeyboardButton(text="👤 Mening hisobim", callback_data="my_profile")],
      [InlineKeyboardButton(text="⭐ Premium olish", callback_data="get_premium")]
  ])
  
  await message.answer("Asosiy menyu:", reply_markup=keyboard)


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
    await message.answer(
        "❌ Botdan foydalanish uchun quyidagi barcha kanallarga obuna bo'lishingiz shart:\n\n"
        "1. @Mafiya_baku_02\n2. @Vertex_trading_official\n3. @Random_suhbat_bot_official\n\n"
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


# --- ANKETA TIZIMI ---
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
  await state.update_data(gender=gender)
  
  keyboard = InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text="👨 Erkak", callback_data="search_male"),
       InlineKeyboardButton(text="👩 Ayol", callback_data="search_female")],
      [InlineKeyboardButton(text="🌐 Farqi yo'q", callback_data="search_any")]
  ])
  await callback.message.edit_text("Kimni qidiryapsiz?", reply_markup=keyboard)
  await state.set_state(RegState.waiting_for_search_gender)


@router.callback_query(RegState.waiting_for_search_gender, F.data.startswith("search_"))
async def process_search_gender(callback: CallbackQuery, state: FSMContext):
  search_map = {"search_male": "Erkak", "search_female": "Ayol", "search_any": "Farqi yo'q"}
  search_gender = search_map[callback.data]
  
  data = await state.get_data()
  age = data.get("age")
  gender = data.get("gender")
  user_id = callback.from_user.id
  username = callback.from_user.username

  cursor.execute(
      "UPDATE users SET username = ?, age = ?, gender = ?, search_gender = ? WHERE user_id = ?",
      (username, age, gender, search_gender, user_id)
  )
  conn.commit()

  await callback.message.delete()
  await callback.message.answer("Muvaffaqiyatli saqlandi! ✅")
  await show_main_menu(callback.message, state)


# --- MENING HISOBIM VA TAHRIRLASH ---
@router.callback_query(F.data == "my_profile")
async def my_profile(callback: CallbackQuery, state: FSMContext):
  user_id = callback.from_user.id
  cursor.execute("SELECT age, gender, is_premium, chats_count FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  
  if not row:
    await show_main_menu(callback.message, state)
    return

  age, gender, is_prem, chats_count = row
  prem_status = "⭐ Faol (Premium)" else "👤 Yo'q (Oddiy)" if not is_prem else "⭐ Faol (Premium)"
  
  text = (
      f"<b>📊 Sizning hisobingiz:</b>\n\n"
      f"👤 Ism: @{callback.from_user.username or 'Mavjud emas'}\n"
      f"📅 Yosh: {age}\n"
      f"🚻 Jins: {gender}\n"
      f"💬 Suhbatlar soni: {chats_count} ta\n"
      f"⭐ Premium: {prem_status}"
  )

  keyboard = InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text="⚙️ Anketani tahrirlash", callback_data="reset_profile")],
      [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
  ])
  
  await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
  await callback.message.delete()
  await show_main_menu(callback.message, state)


@router.callback_query(F.data == "reset_profile")
async def reset_profile(callback: CallbackQuery, state: FSMContext):
  await callback.message.delete()
  await callback.message.answer("Yoshingizni kiriting (16 dan 99 gacha):")
  await state.set_state(RegState.waiting_for_age)


# --- PROMOKOD ---
@router.callback_query(F.data == "get_premium")
async def ask_promocode(callback: CallbackQuery, state: FSMContext):
  await callback.message.edit_text(
      "Promokodni kiriting:\n\n<i>Promokod kiritishni istamasangiz /back buyrug'ini bosing.</i>",
      parse_mode="HTML"
  )
  await state.set_state(PromoState.waiting_for_promo)


@router.message(PromoState.waiting_for_promo, Command("back"))
async def cancel_promo(message: Message, state: FSMContext):
  await message.answer("Promokod kiritish bekor qilindi.")
  await show_main_menu(message, state)


@router.message(PromoState.waiting_for_promo)
async def check_promocode(message: Message, state: FSMContext):
  if message.text == VALID_PROMOCODE:
    cursor.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer("Tabriklaymiz! Siz Premium foydalanuvchi bo'ldingiz ⭐")
    await show_main_menu(message, state)
  else:
    await message.answer("❌ Promokod noto'g'ri.\nPromokod kiritishni istamasangiz /back buyrug'ini bosing.")


# --- QIDIRUV VA SUHBAT ---
@router.callback_query(F.data == "search_partner")
async def start_search(callback: CallbackQuery, state: FSMContext):
  user_id = callback.from_user.id

  # Eskisini to'xtatish
  cursor.execute("SELECT user2 FROM active_chats WHERE user1 = ? OR user2 = ?", (user_id, user_id))
  active = cursor.fetchone()
  if active:
    partner_id = active[0] if active[0] != user_id else active[1]
    cursor.execute("DELETE FROM active_chats WHERE user1 = ? OR user2 = ?", (user_id, user_id))
    conn.commit()
    try:
      await bot.send_message(partner_id, "Suhbatdoshingiz suhbatni tark etdi ❌")
      await show_main_menu(await bot.send_message(partner_id, "Asosiy menyu:"), state)
    except Exception:
      pass

  cursor.execute("DELETE FROM queue WHERE user_id = ?", (user_id,))
  
  cursor.execute("SELECT gender FROM users WHERE user_id = ?", (user_id,))
  row = cursor.fetchone()
  if not row or row[0] is None:
    await callback.message.answer("Avval anketani to'ldiring /start")
    await state.set_state(RegState.waiting_for_age)
    return
  user_gender = row[0]

  cursor.execute("SELECT user_id FROM queue LIMIT 1")
  queue_row = cursor.fetchone()

  if queue_row:
    partner_id = queue_row[0]
    cursor.execute("DELETE FROM queue WHERE user_id = ?", (partner_id,))
    
    cursor.execute("INSERT INTO active_chats (user1, user2) VALUES (?, ?)", (user_id, partner_id))
    # Statistika (chats_count ni bittaga oshirish)
    cursor.execute("UPDATE users SET chats_count = chats_count + 1 WHERE user_id IN (?, ?)", (user_id, partner_id))
    conn.commit()

    cursor.execute("SELECT is_premium, username FROM users WHERE user_id = ?", (user_id,))
    u1_data = cursor.fetchone()
    cursor.execute("SELECT is_premium, username FROM users WHERE user_id = ?", (partner_id,))
    u2_data = cursor.fetchone()

    u1_prem, u1_uname = u1_data[0], u1_data[1]
    u2_prem, u2_uname = u2_data[0], u2_data[1]

    text1 = "Suhbatdosh topildi! 🎉\n"
    if u1_prem and u2_uname:
      text1 += f"Suhbatdoshingiz username'i: @{u2_uname}"
    else:
      text1 += "Suhbatdoshingiz anonim."

    text2 = "Suhbatdosh topildi! 🎉\n"
    if u2_prem and u1_uname:
      text2 += f"Suhbatdoshingiz username'i: @{u1_uname}"
    else:
      text2 += "Suhbatdoshingiz anonim."

    stop_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 Suhbatni to'xtatish", callback_data="stop_chat")]
    ])

    await bot.send_message(user_id, text1, reply_markup=stop_kb)
    await bot.send_message(partner_id, text2, reply_markup=stop_kb)
    await callback.message.delete()
  else:
    cursor.execute("INSERT OR REPLACE INTO queue (user_id, gender) VALUES (?, ?)", (user_id, user_gender))
    conn.commit()
    stop_search_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Qidiruvni to'xtatish", callback_data="stop_search")]
    ])
    await callback.message.edit_text("Suhbatdosh qidirilmoqda...", reply_markup=stop_search_kb)


@router.callback_query(F.data == "stop_search")
async def stop_search(callback: CallbackQuery, state: FSMContext):
  cursor.execute("DELETE FROM queue WHERE user_id = ?", (callback.from_user.id,))
  conn.commit()
  await callback.message.delete()
  await show_main_menu(callback.message, state)


@router.callback_query(F.data == "stop_chat")
async def stop_chat(callback: CallbackQuery, state: FSMContext):
  user_id = callback.from_user.id
  cursor.execute("SELECT user2 FROM active_chats WHERE user1 = ? OR user2 = ?", (user_id, user_id))
  row = cursor.fetchone()
  
  if row:
    partner_id = row[0] if row[0] != user_id else row[1]
    cursor.execute("DELETE FROM active_chats WHERE user1 = ? OR user2 = ?", (user_id, user_id))
    conn.commit()
    
    try:
      await bot.send_message(partner_id, "Suhbatdoshingiz suhbatni tark etdi ❌")
      await show_main_menu(await bot.send_message(partner_id, "Asosiy menyu:"), state)
    except Exception:
      pass

  await callback.message.delete()
  await show_main_menu(callback.message, state)


# --- XABARLARNI YO'NALTIRISH ---
@router.message()
async def chat_message_handler(message: Message):
  user_id = message.from_user.id
  cursor.execute("SELECT user2 FROM active_chats WHERE user1 = ? OR user2 = ?", (user_id, user_id))
  row = cursor.fetchone()
  
  if row:
    partner_id = row[0] if row[0] != user_id else row[1]
    try:
      await message.copy_to(partner_id)
    except Exception:
      pass


async def main():
  dp.include_router(router)
  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
