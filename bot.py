import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database import init_db, add_user, update_user_profile, get_user, set_premium, set_user_status, get_stats

TOKEN = "9255758010:AAGBuwrm3sKAXI6l8FiUmeMOA4J56jCAfxA"
ADMIN_USERNAME = "@wynx_exe"
PROMO_CODE = "KOD397103"

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_queue = [] 
active_chats = {} 

class RegState(StatesGroup):
    name = State()
    age = State()
    gender = State()

class PromoState(StatesGroup):
    waiting_code = State()
    waiting_target = State()

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Do'st qidirish"), KeyboardButton(text="👑 Premium do'st qidirish")],
            [KeyboardButton(text="✏️ Anketani tahrirlash"), KeyboardButton(text="👥 Onlaynlar")],
            [KeyboardButton(text="❓ Yordam")]
        ],
        resize_keyboard=True
    )

def gender_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 O'g'il bola"), KeyboardButton(text="👩 Qiz bola")],
            [KeyboardButton(text="🌐 Farqi yo'q (Random)")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    init_db()
    add_user(message.from_user.id)
    user = get_user(message.from_user.id)
    
    if not user or not user[0]: 
        await message.answer("Salom! Tanishuv botiga xush kelibsiz.\nIltimos, ismingizni kiriting:")
        await state.set_state(RegState.name)
    else:
        await message.answer("Asosiy menyu:", reply_markup=main_menu())

@dp.message(RegState.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Yoshingizni kiriting (masalan: 18):")
    await state.set_state(RegState.age)

@dp.message(RegState.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, yoshingizni faqat raqamlarda kiriting:")
        return
    await state.update_data(age=int(message.text))
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="👨 O'g'il bola"), KeyboardButton(text="👩 Qiz bola")]],
        resize_keyboard=True
    )
    await message.answer("Jinsingizni tanlang:", reply_markup=kb)
    await state.set_state(RegState.gender)

@dp.message(RegState.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    if message.text not in ["👨 O'g'il bola", "👩 Qiz bola"]:
        await message.answer("Iltimos, tugmalardan birini bosing!")
        return
    
    data = await state.get_data()
    update_user_profile(message.from_user.id, data['name'], data['age'], message.text)
    await state.clear()
    
    await message.answer("Anketangiz tayyor! 🎉", reply_markup=main_menu())

@dp.message(F.text == "👥 Onlaynlar")
async def online_stats_handler(message: types.Message):
    total_reg, total_online = get_stats()
    text = (
        f"📊 **Statistika:**\n\n"
        f"• Botdan roʻyxatdan oʻtganlar soni: {total_reg}\n"
        f"• Hozir onlayn: {total_online}"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "❓ Yordam")
async def help_handler(message: types.Message):
    text = (
        "❓ **Asosiy savollarga javoblar:**\n\n"
        "1. **Bot qanday ishlaydi?** - 'Do'st qidirish' tugmasini bosib bepul suhbatdosh topishingiz mumkin.\n"
        "2. **Premium nima beradi?** - Jinsiy filtrlar orqali aniqroq suhbatdosh tanlash imkonini beradi.\n"
        "3. **Suhbatni qanday tugatish mumkin?** - /stop buyrug'ini bosing.\n"
        "4. **Yangi suhbatga o'tish:** - /next buyrug'ini bosing."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "✏️ Anketani tahrirlash")
async def edit_profile(message: types.Message, state: FSMContext):
    await message.answer("Yangi ismingizni kiriting:")
    await state.set_state(RegState.name)

@dp.message(F.text == "🔍 Do'st qidirish")
async def search_free_friend(message: types.Message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user or not user[0]:
        await message.answer("Avval /start buyrug'ini bosib anketani to'ldiring!")
        return

    set_user_status(uid, "searching")
    
    if search_queue:
        partner_id, _ = search_queue.pop(0)
        if partner_id != uid:
            active_chats[uid] = partner_id
            active_chats[partner_id] = uid
            set_user_status(uid, "chatting")
            set_user_status(partner_id, "chatting")
            
            p_data = get_user(partner_id)
            u_data = get_user(uid)
            
            await bot.send_message(uid, f"Suhbatdosh topildi!\nIsmi: {p_data[0]}\nYoshi: {p_data[1]}\nJinsi: {p_data[2]}\n\nSuhbatni tark etish uchun /stop bosing\nYangi suhbat uchun /next bosing")
            await bot.send_message(partner_id, f"Suhbatdosh topildi!\nIsmi: {u_data[0]}\nYoshi: {u_data[1]}\nJinsi: {u_data[2]}\n\nSuhbatni tark etish uchun /stop bosing\nYangi suhbat uchun /next bosing")
            return

    search_queue.append((uid, None))
    await message.answer("Suhbatdosh qidirilmoqda... ⏳\nBekor qilish uchun /stop bosing")

@dp.message(F.text == "👑 Premium do'st qidirish")
async def premium_search_handler(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid) 
    
    if user[4] == 1: 
        await message.answer("Sizda allaqachon premium mavjud! Kimni qidiramiz?", reply_markup=gender_keyboard())
        await state.set_state(PromoState.waiting_target)
    else:
        await message.answer(f"Promokodni kiriting:\nAgar promokodni bilmasangiz adminga murojaat qiling: {ADMIN_USERNAME}")
        await state.set_state(PromoState.waiting_code)

@dp.message(PromoState.waiting_code)
async def check_promo_code(message: types.Message, state: FSMContext):
    if message.text.strip() == PROMO_CODE:
        set_premium(message.from_user.id)
        await message.answer("Tabriklaymiz! Premium muvaffaqiyatli faollashtirildi 🎉. Endi qanday do'st kerak?", reply_markup=gender_keyboard())
        await state.set_state(PromoState.waiting_target)
    else:
        await message.answer(f"Noto'g'ri promokod! Adminga murojaat qiling: {ADMIN_USERNAME}")

@dp.message(PromoState.waiting_target, F.text.in_(["👨 O'g'il bola", "👩 Qiz bola", "🌐 Farqi yo'q (Random)"]))
async def premium_target_chosen(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    target = message.text
    set_user_status(uid, "searching")
    await state.clear()
    
    search_queue.append((uid, target))
    await message.answer(f"Tanlangan filtr bo'yicha suhbatdosh qidirilmoqda... ⏳", reply_markup=main_menu())

@dp.message(Command("stop"))
async def stop_chat(message: types.Message):
    uid = message.from_user.id
    set_user_status(uid, "free")
    
    if uid in active_chats:
        partner_id = active_chats[uid]
        del active_chats[uid]
        if partner_id in active_chats:
            del active_chats[partner_id]
        set_user_status(partner_id, "free")
        await bot.send_message(partner_id, "Suhbatdosh suhbatni tark etdi.", reply_markup=main_menu())
    
    global search_queue
    search_queue = [item for item in search_queue if item[0] != uid]
    
    await message.answer("Suhbat yakunlandi.", reply_markup=main_menu())

@dp.message(Command("next"))
async def next_chat(message: types.Message):
    await stop_chat(message)
    await search_free_friend(message)

@dp.message()
async def chat_message_relay(message: types.Message):
    uid = message.from_user.id
    if uid in active_chats:
        partner_id = active_chats[uid]
        await message.copy_to(partner_id)
    else:
        await message.answer("Siz hozir hech kim bilan gaplashmayapsiz. 'Do'st qidirish' tugmasini bosing.", reply_markup=main_menu())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
      
