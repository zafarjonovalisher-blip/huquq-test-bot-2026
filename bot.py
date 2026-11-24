import io
import os
from datetime import datetime
from fastapi import FastAPI, Request, Header, HTTPException
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Update, Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile
)
from PIL import Image, ImageDraw, ImageFont

TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
SECRET = os.getenv("WEBHOOK_SECRET")

if not TOKEN or not BASE_URL or not SECRET:
    raise RuntimeError("Server sozlamalari yetishmayapti!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()


class RegistrationStates(StatesGroup):
    waiting_fullname = State()
    waiting_phone = State()
    taking_test = State()


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


def load_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def generate_certificate(fullname: str, score: int, total: int = 15) -> bytes:
    width, height = 1600, 1120
    img = Image.new("RGB", (width, height), "#0B192C")
    draw = ImageDraw.Draw(img)

    # Tashqi va ichki tillarang ramkalar
    gold = "#D4AF37"
    soft_gold = "#F3E5AB"
    light_text = "#F8FAFC"
    muted_text = "#CBD5E1"
    accent_bg = "#13294B"

    draw.rectangle([36, 36, width - 36, height - 36], outline=gold, width=6)
    draw.rectangle([60, 60, width - 60, height - 60], outline=soft_gold, width=2)

    # Yuqori va pastki dekorativ bloklar
    draw.rectangle([90, 90, width - 90, 165], fill=accent_bg, outline=gold, width=2)
    draw.rectangle([90, height - 165, width - 90, height - 90], fill=accent_bg, outline=gold, width=2)

    # Burchak bezaklari
    corners = [(85, 85), (width - 85, 85), (85, height - 85), (width - 85, height - 85)]
    for cx, cy in corners:
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=gold)

    f_top = load_font(26, bold=True)
    f_title = load_font(68, bold=True)
    f_sub = load_font(28, bold=False)
    f_name = load_font(58, bold=True)
    f_body = load_font(28, bold=False)
    f_stat = load_font(32, bold=True)
    f_small = load_font(24, bold=False)

    def draw_centered(y: int, text: str, font, fill):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((width - w) / 2, y), text, font=font, fill=fill)

    percent = (score / total) * 100
    if percent >= 80:
        level_title = "A'LO DARAJADAGI BILIM"
        badge_color = "#22C55E"
    elif percent >= 50:
        level_title = "MUNOSIB NATIJA"
        badge_color = gold
    else:
        level_title = "ISHTIROK SERTIFIKATI"
        badge_color = "#38BDF8"

    draw_centered(114, "RASMIY BILIM SINOVI SERTIFIKATI", f_top, soft_gold)
    draw_centered(215, "SERTIFIKAT", f_title, gold)
    draw_centered(305, "Huquqiy savodxonlik bo'yicha maxsus test yakunlari asosida taqdim etiladi", f_sub, muted_text)

    draw_centered(395, "Ushbu sertifikat egasi:", f_body, light_text)

    # Ism-familiya chizig'i va matni
    clean_name = fullname.strip().upper()
    draw_centered(455, clean_name, f_name, light_text)
    draw.line([(320, 535), (width - 320, 535)], fill=gold, width=3)

    draw_centered(575, "Huquq fani yuzasidan 15 ta savoldan iborat test sinovini muvaffaqiyatli yakunladi.", f_body, muted_text)

    # Natija kartasi
    box_x1, box_y1, box_x2, box_y2 = 260, 645, width - 260, 795
    draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=18, fill=accent_bg, outline=gold, width=2)

    draw_centered(670, f"Natija: {score} / {total} ball   |   Ko'rsatkich: {percent:.1f}%", f_stat, soft_gold)
    draw_centered(725, f"Daraja: {level_title}", f_sub, badge_color)

    # Sana va imzo qismi
    today_str = datetime.now().strftime("%d.%m.%Y")
    draw.line([(220, 885), (560, 885)], fill=muted_text, width=2)
    draw.text((255, 898), f"Sana: {today_str}", font=f_small, fill=light_text)

    draw.line([(width - 560, 885), (width - 220, 885)], fill=muted_text, width=2)
    draw.text((width - 515, 898), "Huquq Test Platformasi", font=f_small, fill=light_text)

    draw_centered(height - 142, "Bilim — eng ishonchli huquqiy himoya", f_small, soft_gold)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.getvalue()


def keyboard(index: int) -> InlineKeyboardMarkup:
    options = questions[index][1]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer:{letter}"
        )]
        for option, letter in zip(options, ["A", "B", "C"])
    ])


async def send_question(message: Message, index: int):
    question = questions[index][0]
    await message.answer(
        f"⚖️ <b>HUQUQ TESTI</b>\n\n"
        f"📌 Savol <b>{index + 1}/{len(questions)}</b>\n\n"
        f"{question}",
        reply_markup=keyboard(index),
        parse_mode="HTML"
    )


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RegistrationStates.waiting_fullname)
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "<b>Huquq fanidan 15 ta savollik rasmiy test</b> platformasiga xush kelibsiz!\n"
        "Test yakunida ismingiz tushirilgan maxsus sertifikat taqdim etiladi.\n\n"
        "1️⃣ Avval <b>Ism va familiyangizni</b> kiriting (masalan: <i>Alisher Zafarjonov</i>):",
        parse_mode="HTML"
    )


@dp.message(RegistrationStates.waiting_fullname)
async def get_fullname(message: Message, state: FSMContext):
    fullname = (message.text or "").strip()
    if len(fullname.split()) < 2 or len(fullname) < 4:
        await message.answer(
            "❗ Iltimos, <b>Ism va familiyani</b> to‘liq kiriting (kamida 2 ta so‘z):",
            parse_mode="HTML"
        )
        return

    await state.update_data(fullname=fullname)
    await state.set_state(RegistrationStates.waiting_phone)
    await message.answer(
        f"Rahmat, <b>{fullname}</b>! ✅\n\n"
        "2️⃣ Endi <b>telefon raqamingizni</b> kiriting (masalan: <code>+998901234567</code>):",
        parse_mode="HTML"
    )


@dp.message(RegistrationStates.waiting_phone)
async def get_phone(message: Message, state: FSMContext):
    phone = (message.text or "").strip()
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 9:
        await message.answer(
            "❗ Telefon raqam noto‘g‘ri ko‘rinadi. Qayta kiriting (masalan: <code>+998901234567</code>):",
            parse_mode="HTML"
        )
        return

    await state.update_data(phone=phone, index=0, correct=0)
    await state.set_state(RegistrationStates.taking_test)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🚀 Testni boshlash",
            callback_data="begin"
        )
    ]])
    data = await state.get_data()
    await message.answer(
        "Ma'lumotlaringiz saqlandi! 📋\n\n"
        f"👤 Ism-familiya: <b>{data['fullname']}</b>\n"
        f"📞 Telefon: <b>{phone}</b>\n"
        f"📝 Savollar soni: <b>{len(questions)} ta</b>\n\n"
        "Tayyor bo‘lsangiz, quyidagi tugmani bosing:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "begin")
async def begin(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("fullname"):
        await call.answer("Avval /start bosing!", show_alert=True)
        return

    await state.update_data(index=0, correct=0)
    await state.set_state(RegistrationStates.taking_test)
    await call.answer()
    await send_question(call.message, 0)


@dp.callback_query(F.data.startswith("answer:"))
async def answer(call: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()

    if current_state != RegistrationStates.taking_test.state or "index" not in data:
        await call.answer("Avval /start bosib ro‘yxatdan o‘ting!", show_alert=True)
        return

    index = data["index"]
    correct = data["correct"]

    if index >= len(questions):
        await call.answer("Test allaqachon yakunlangan!")
        return

    selected = call.data.split(":")[1]
    correct_answer = questions[index][2]

    if selected == correct_answer:
        correct += 1
        await call.answer("✅ To'g'ri javob!")
    else:
        await call.answer("❌ Noto'g'ri javob!")

    next_index = index + 1
    await state.update_data(index=next_index, correct=correct)

    if next_index < len(questions):
        await send_question(call.message, next_index)
    else:
        total = len(questions)
        wrong = total - correct
        percent = correct / total * 100
        fullname = data["fullname"]
        phone = data["phone"]

        verdict = (
            "🏆 Ajoyib natija!" if percent >= 80
            else "👍 Yaxshi harakat!" if percent >= 50
            else "📚 Yana mashq qiling!"
        )

        await call.message.answer(
            "🏁 <b>TEST YAKUNLANDI!</b>\n\n"
            f"👤 Ism-familiya: <b>{fullname}</b>\n"
            f"📞 Telefon: <b>{phone}</b>\n"
            f"✅ To'g'ri: <b>{correct}</b>\n"
            f"❌ Noto'g'ri: <b>{wrong}</b>\n"
            f"📊 Natija: <b>{correct}/{total}</b>\n"
            f"📈 Foiz: <b>{percent:.1f}%</b>\n\n"
            f"{verdict}\n\n"
            "⏳ Sertifikatingiz tayyorlanmoqda...",
            parse_mode="HTML"
        )

        cert_bytes = generate_certificate(fullname=fullname, score=correct, total=total)
        cert_file = BufferedInputFile(cert_bytes, filename="huquq_sertifikat.png")

        await call.message.answer_photo(
            photo=cert_file,
            caption=f"🎓 <b>{fullname}</b> nomiga rasmiy sertifikat tayyorlandi!",
            parse_mode="HTML"
        )
        await state.clear()


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
