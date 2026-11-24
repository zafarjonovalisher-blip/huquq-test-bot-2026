import os
from fastapi import FastAPI, Request, Header, HTTPException
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Update, Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
SECRET = os.getenv("WEBHOOK_SECRET")

if not TOKEN or not BASE_URL or not SECRET:
    raise RuntimeError("Server sozlamalari yetishmayapti!")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()
sessions = {}

questions = [
    ("Konstitutsiya qanday yuridik kuchga ega?",
     ["A) Oddiy qonun bilan teng", "B) Oliy yuridik kuchga ega", "C) Faqat davlat organlari uchun"],
     "B"),
    ("Qonun chiqaruvchi oliy vakillik organi qaysi?",
     ["A) Vazirlar Mahkamasi", "B) Oliy sud", "C) Oliy Majlis"], "C"),
    ("Aybsizlik prezumpsiyasi nimani anglatadi?",
     ["A) Aybi isbotlanmaguncha shaxs aybsiz", "B) Gumon qilingan aybdor", "C) Har qanday gumon jazolanadi"], "A"),
    ("Davlat hokimiyati nechta tarmoqqa bo'linadi?",
     ["A) Ikki", "B) Uch", "C) To'rt"], "B"),
    ("Inson huquqlari kimlarga tegishli?",
     ["A) Faqat fuqarolarga", "B) Faqat kattalarga", "C) Har bir insonga"], "C"),
    ("Oliy Majlis nechta palatadan iborat?",
     ["A) Ikki", "B) Bir", "C) Uch"], "A"),
    ("Sud hokimiyatining asosiy vazifasi nima?",
     ["A) Qonun qabul qilish", "B) Odil sudlov", "C) Budjet tasdiqlash"], "B"),
    ("Qonunni bilmaslik javobgarlikdan ozod qiladimi?",
     ["A) Ha", "B) Faqat kattalarni", "C) Yo'q"], "C"),
    ("Zaruriy mudofaa qachon qo'llanadi?",
     ["A) Xavfli tajovuzdan himoyalanishda", "B) Qasos olishda", "C) Kelishmovchilikda"], "A"),
    ("Konstitutsiya va oddiy qonun ziddiyatida qaysi biri ustun?",
     ["A) Oddiy qonun", "B) Konstitutsiya", "C) Hokim qarori"], "B"),
    ("Voyaga yetmagan shaxs kim?",
     ["A) 21 yoshga to'lmagan", "B) 16 yoshga to'lmagan", "C) 18 yoshga to'lmagan"], "C"),
    ("Buzilgan huquqlarni himoya qilish uchun qayerga murojaat qilinadi?",
     ["A) Sudga yoki vakolatli organga", "B) Tanishlarga", "C) Hech qayerga"], "A"),
    ("Xalqaro shartnomada qonundan boshqacha qoida bo'lsa, qaysi qoida qo'llanadi?",
     ["A) Mahalliy qaror", "B) Xalqaro shartnoma", "C) Eski qonun"], "B"),
    ("So'z erkinligi mutlaq huquqmi?",
     ["A) Ha", "B) Faqat davlat xizmatchilariga", "C) Yo'q, qonuniy asoslarda cheklanishi mumkin"], "C"),
    ("Ma'muriy huquq nimani tartibga soladi?",
     ["A) Davlat boshqaruvi munosabatlarini", "B) Faqat merosni", "C) Faqat oilani"], "A")
]

def keyboard(index):
    options = questions[index][1]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer:{letter}"
        )]
        for option, letter in zip(options, ["A", "B", "C"])
    ])

async def send_question(message, index):
    question = questions[index][0]
    await message.answer(
        f"⚖️ HUQUQ TESTI\n\n"
        f"📌 Savol {index + 1}/15\n\n"
        f"{question}",
        reply_markup=keyboard(index)
    )

@dp.message(CommandStart())
async def start(message: Message):
    sessions[message.from_user.id] = {
        "index": 0,
        "correct": 0
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="⚖️ Huquq testini boshlash",
            callback_data="begin"
        )
    ]])
    await message.answer(
        "Assalomu alaykum!\n\n"
        "Huquq fanidan 15 ta testga tayyormisiz?",
        reply_markup=kb
    )

@dp.callback_query(F.data == "begin")
async def begin(call: CallbackQuery):
    sessions[call.from_user.id] = {
        "index": 0,
        "correct": 0
    }
    await call.answer()
    await send_question(call.message, 0)

@dp.callback_query(F.data.startswith("answer:"))
async def answer(call: CallbackQuery):
    user_id = call.from_user.id
    session = sessions.get(user_id)

    if not session:
        await call.answer("Avval /start bosing!", show_alert=True)
        return

    index = session["index"]

    if index >= 15:
        await call.answer("Test tugagan!")
        return

    selected = call.data.split(":")[1]
    correct_answer = questions[index][2]

    if selected == correct_answer:
        session["correct"] += 1
        await call.answer("✅ To'g'ri javob!")
    else:
        await call.answer("❌ Noto'g'ri javob!")

    session["index"] += 1
    next_index = session["index"]

    if next_index < 15:
        await send_question(call.message, next_index)
    else:
        score = session["correct"]
        wrong = 15 - score

        await call.message.answer(
            "🏁 TEST YAKUNLANDI!\n\n"
            f"✅ To'g'ri: {score}\n"
            f"❌ Noto'g'ri: {wrong}\n"
            f"📊 Natija: {score}/15\n"
            f"📈 Foiz: {score / 15 * 100:.1f}%\n\n"
            + ("🏆 Ajoyib natija!" if score >= 12
               else "👍 Yaxshi harakat!" if score >= 8
               else "📚 Yana mashq qiling!")
        )
        sessions.pop(user_id, None)

@app.get("/")
async def home():
    return {"status": "Huquq Test Bot ishlayapti!"}

@app.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    if x_telegram_bot_api_secret_token != SECRET:
        raise HTTPException(status_code=403)

    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def startup():
    await bot.set_webhook(
        f"{BASE_URL}/webhook",
        secret_token=SECRET
    )

@app.on_event("shutdown")
async def shutdown():
    await bot.session.close()
