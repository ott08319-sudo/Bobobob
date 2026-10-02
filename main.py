import asyncio
import logging
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent, BotCommand,
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

try:
    import g4f
    G4F_AVAILABLE = True
except ImportError:
    G4F_AVAILABLE = False

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


async def ask_ai(prompt: str) -> str:
    if not G4F_AVAILABLE:
        return "🤖 Нейросеть недоступна."
    try:
        r = await g4f.ChatCompletion.create_async(model=g4f.models.default, messages=[{"role": "user", "content": prompt}])
        return r
    except Exception as e:
        logging.error(f"AI error: {e}")
        return "🤖 Нейросеть задумалась."


games_active, scores, duels = {}, {}, {}

QUESTIONS = [
    {"q": "Сколько планет в Солнечной системе?", "a": ["7", "8", "9"], "correct": "8"},
    {"q": "Кто написал «Войну и мир»?", "a": ["Толстой", "Достоевский", "Пушкин"], "correct": "Толстой"},
    {"q": "Самая длинная река?", "a": ["Нил", "Амазонка", "Янцзы"], "correct": "Амазонка"},
    {"q": "Сколько цветов в радуге?", "a": ["5", "7", "9"], "correct": "7"},
    {"q": "Газ в атмосфере Земли?", "a": ["Кислород", "Азот", "CO2"], "correct": "Азот"},
    {"q": "Кто нарисовал Мону Лизу?", "a": ["Ван Гог", "Пикассо", "Леонардо"], "correct": "Леонардо"},
]

JOKES = [
    "— Как дела?\n— Как в сказке: чем дальше, тем страшнее.",
    "— Почему программисты путают Хэллоуин и Рождество?\n— Потому что OCT 31 == DEC 25.",
    "— Врач, я думаю, что я бот.\n— Не волнуйтесь, это баг.",
    "— Что сказал байт байту?\n— Ты мне не пара.",
    "— Почему скелеты не дерутся?\n— У них нет духа.",
]

TOILET_JOKES = [
    "💩 Почему какашка не ходит в школу? Она уже всё знает — была в унитазе!",
    "🚽 Что сказал унитаз какашке? «Ты меня достала!»",
    "💩 Какашка у врача:\n— Всё болит!\n— Где?\n— Везде! Меня смыли!",
    "🧻 Туалетная бумага спокойна — её время придёт.",
    "💩 Какашка на работе:\n— Сильные стороны?\n— Я всегда в потоке.",
    "🚽 Унитаз — где тебя ждут с объятиями.",
    "💩 Какашки не любят понедельники — после выходных их много.",
    "🧻 Туалетная бумага в баре:\n— Что будете?\n— Я одноразовая.",
    "💩 Какашка стала звездой — её крутили в прямом эфире.",
    "🚽 Какашки перед прыжком:\n— С богом!",
    "💩 Какашка в спортзале:\n— Цель?\n— Стать твёрдой.",
    "🚽 Унитаз грустный — его все используют, никто не обнимает.",
    "💩 Какашка и унитаз поссорились:\n— Ты меня не понимаешь!\n— Я тебя слишком хорошо понимаю.",
    "🧻 Туалетная бумага на свидании:\n— Ты мягкая!\n— Да, но быстро заканчиваюсь.",
    "💩 Какашка-блогер. Подписчиков ноль. Все смылись.",
]

CRINGE_JOKES = [
    "😬 Махнул рукой на прощание, а человек уже ушёл.",
    "😬 Сказал «спасибо» вместо «пожалуйста».",
    "😬 Поздоровался, а он не поздоровался.",
    "😬 Написал «ахахах», а сам не улыбнулся.",
    "😬 Сказал «я скоро», прошло три часа.",
    "😬 В тишине урчит живот. Все смотрят.",
    "😬 Позвонил, а он сбросил.",
    "😬 Пошутил, никто не засмеялся.",
    "😬 Мама зовёт по полному имени.",
    "😬 Сказал «доброе утро» в 3 дня.",
]

DUMB_JOKES = [
    "🤪 Мужик врачу:\n— Какаю в 7 утра.\n— Отлично!\n— Но встаю в 9!",
    "🤪 — Как называется человек, который какает в унитаз?\n— Нормальный.",
    "🤪 Какашка какашке:\n— Ты чё такая?\n— Я смытая.",
    "🤪 — Почему не смыл?\n— Оставил на память.",
    "🤪 Сын:\n— Пап, что такое кринж?\n— Вот когда я это объясняю — это и есть кринж.",
    "🤪 Какашка какашке:\n— Потонем вместе!",
    "🤪 Мужик в туалете:\n— Бумага есть?\n— Нет!\n— А газета?\n— Это читальня или туалет?!",
    "🤪 Почему какашка опаздывает?\n— Идёт с самого низа.",
    "🤪 90% людей какают. Остальные 10% врут.",
    "🤪 Какашка в Книге рекордов — была самой большой. И её смыли.",
    "🤪 Табличка «Занято». Написал: «Я тоже занят, но жду».",
    "🤪 Почему какашки не летают?\n— Нет крыльев. И желания.",
    "🤪 Унитаз какашке:\n— Ты надоела!\n— А ты думал, я навсегда?",
    "🤪 Что сказал туалет после смыва?\n— Наконец-то тишина!",
    "🤪 Психолог:\n— Что тревожит?\n— Думаю, что я какашка.\n— Почему?\n— Меня все смывают.",
]

RIDDLES = [
    {"q": "Что видно с закрытыми глазами?", "a": "сон"},
    {"q": "Чем больше берёшь, тем больше становится?", "a": "яма"},
    {"q": "Идёт, но не двигается?", "a": "время"},
    {"q": "Твоё, но другие используют чаще?", "a": "имя"},
    {"q": "Мокнет, пока сохнет?", "a": "полотенце"},
]

COUNTRIES_FACTS = [
    "🇯🇵 В Японии 6800+ островов.",
    "🇦🇺 Австралия — континент без вулканов.",
    "🇧🇷 Бразилия названа в честь дерева.",
    "🇨🇦 В Канаде больше озёр, чем везде.",
    "🇷🇺 Россия больше Плутона.",
    "🇮🇸 В Исландии нет комаров.",
    "🇨🇭 Швейцария без моря.",
    "🇮🇳 Индия — самая населённая.",
]

COMPLIMENTS = [
    "Ты огонь! 🔥", "С тобой чат лучше! ✨", "Ты причина улыбок! 😊",
    "У тебя отличный юмор! 😄", "Ты умнее 99%! 🧠",
]

TRUTH_QUESTIONS = [
    "Самый неловкий момент?",
    "Притворялся больным?",
    "Самая странная привычка?",
    "Что последний раз гуглил?",
    "Какую песню стесняешься слушать?",
    "Кому последний раз врал?",
    "Самая тупая ссора?",
    "Что ел ночью?",
    "Самый кринжовый пост?",
    "Сколько раз проверял телефон?",
]

DARE_ACTIONS = [
    "Отправь смешной стикер.",
    "Последнее фото из галереи.",
    "Комплимент человеку справа.",
    "Скороговорка: «Шла Саша по шоссе».",
    "Сообщение капсом, как будто зол.",
    "Смешное прозвище для себя.",
    "Голосовое с пением (5 сек).",
    "3 факта, один — ложь.",
    "Напиши как робот 3 сообщения.",
    "Смешной стикер на аватарку на час.",
]

ASCII_ART = [
    "🐱\n /\\_/\\\n( o.o )\n > ^ <",
    "😼\n  /\\_/\\\n ( -.- )\n  > ^ <",
    "🎃\n  _____\n /     \\\n| () () |\n \\  ^  /\n  |||||",
]

ROULETTE = ["🔴 Красное", "⚫ Чёрное", "🟢 Зеро"]
COIN = ["🪙 Орёл", "🪙 Решка"]
DICE = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
BOT_USERNAME = None


def add_score(chat_id, user_id, points=1):
    scores.setdefault(chat_id, {})
    scores[chat_id][user_id] = scores[chat_id].get(user_id, 0) + points


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games"),
         InlineKeyboardButton(text="📊 Топ", callback_data="menu_top")],
        [InlineKeyboardButton(text="🎲 Рандом", callback_data="menu_random"),
         InlineKeyboardButton(text="😄 Шутка", callback_data="menu_joke")],
        [InlineKeyboardButton(text="💬 Комплимент", callback_data="menu_compliment"),
         InlineKeyboardButton(text="💩 Туалетный", callback_data="menu_toilet")],
        [InlineKeyboardButton(text="😬 Кринж", callback_data="menu_cringe"),
         InlineKeyboardButton(text="🤪 Тупые", callback_data="menu_dumb")],
        [InlineKeyboardButton(text="🎭 Правда/Действие", callback_data="menu_truth"),
         InlineKeyboardButton(text="🧩 Загадка", callback_data="menu_riddle")],
        [InlineKeyboardButton(text="🌍 Страны", callback_data="menu_country"),
         InlineKeyboardButton(text="🎨 ASCII", callback_data="menu_ascii")],
        [InlineKeyboardButton(text="🎰 Слоты", callback_data="menu_slots"),
         InlineKeyboardButton(text="🤖 Нейросеть", callback_data="menu_ai")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help")],
    ])


def games_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Викторина", callback_data="game_quiz")],
        [InlineKeyboardButton(text="⚔️ Дуэль", callback_data="game_duel")],
        [InlineKeyboardButton(text="🎯 Угадай число", callback_data="game_guess")],
        [InlineKeyboardButton(text="📝 Слова", callback_data="game_word")],
        [InlineKeyboardButton(text="📈 Больше-меньше", callback_data="game_moreless")],
        [InlineKeyboardButton(text="🎰 Рулетка", callback_data="game_roulette")],
        [InlineKeyboardButton(text="🪙 Монетка", callback_data="game_coin")],
        [InlineKeyboardButton(text="🎲 Кубик", callback_data="game_dice")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")],
    ])


def ai_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Придумать игру", callback_data="ai_game")],
        [InlineKeyboardButton(text="📖 История", callback_data="ai_story")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")],
    ])


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🎉 Привет! Я развлекательный бот.\n\n🎮 /games — игры\n💩 /toilet — туалетный\n🤪 /dumb — тупые\n😬 /cringe — кринж\n🎭 /truth — правда/действие\n🤖 /ask — нейросеть", reply_markup=main_menu())


@dp.message(Command("games"))
async def cmd_games(message: Message):
    await message.answer("🎮 <b>Выбери игру:</b>", reply_markup=games_menu(), parse_mode="HTML")


@dp.message(Command("top"))
async def cmd_top(message: Message):
    cs = scores.get(message.chat.id, {})
    if not cs:
        await message.answer("📊 Пока никто не играл!")
        return
    s = sorted(cs.items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 <b>Топ:</b>\n\n"
    for i, (uid, sc) in enumerate(s, 1):
        try:
            m = await bot.get_chat_member(message.chat.id, uid)
            name = m.user.first_name
        except Exception:
            name = f"Игрок {uid}"
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{sc}</b>\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("random"))
async def cmd_random(message: Message):
    await message.answer(f"🎲 <b>{random.randint(1, 100)}</b>", parse_mode="HTML")


@dp.message(Command("joke"))
async def cmd_joke(message: Message):
    await message.answer(f"😄 {random.choice(JOKES)}")


@dp.message(Command("compliment"))
async def cmd_compliment(message: Message):
    await message.answer(f"💬 {random.choice(COMPLIMENTS)}")


@dp.message(Command("toilet"))
async def cmd_toilet(message: Message):
    await message.answer(random.choice(TOILET_JOKES))


@dp.message(Command("cringe"))
async def cmd_cringe(message: Message):
    await message.answer(random.choice(CRINGE_JOKES))


@dp.message(Command("dumb"))
async def cmd_dumb(message: Message):
    await message.answer(random.choice(DUMB_JOKES))


@dp.message(Command("truth"))
async def cmd_truth(message: Message):
    if random.choice([0, 1]):
        await message.answer(f"🎭 <b>Правда:</b>\n\n{random.choice(TRUTH_QUESTIONS)}", parse_mode="HTML")
    else:
        await message.answer(f"🎯 <b>Действие:</b>\n\n{random.choice(DARE_ACTIONS)}", parse_mode="HTML")


@dp.message(Command("riddle"))
async def cmd_riddle(message: Message):
    r = random.choice(RIDDLES)
    games_active[message.chat.id] = {"game": "riddle", "answer": r["a"]}
    await message.answer(f"🧩 <b>Загадка:</b>\n\n{r['q']}", parse_mode="HTML")


@dp.message(Command("country"))
async def cmd_country(message: Message):
    await message.answer(random.choice(COUNTRIES_FACTS))


@dp.message(Command("ascii"))
async def cmd_ascii(message: Message):
    await message.answer(f"<code>{random.choice(ASCII_ART)}</code>", parse_mode="HTML")


@dp.message(Command("slots"))
async def cmd_slots(message: Message):
    sym = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    r = [random.choice(sym) for _ in range(3)]
    t = f"🎰 <b>Слоты</b>\n\n| {r[0]} | {r[1]} | {r[2]} |\n\n"
    if r[0] == r[1] == r[2]:
        t += "🎉 <b>ДЖЕКПОТ!</b>"
        add_score(message.chat.id, message.from_user.id, 5)
    elif r[0] == r[1] or r[1] == r[2] or r[0] == r[2]:
        t += "✨ Два совпали!"
        add_score(message.chat.id, message.from_user.id, 1)
    else:
        t += "😢 Не повезло."
    await message.answer(t, parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("❓ /games /top /joke /compliment /toilet /cringe /dumb /truth /riddle /country /ascii /slots /ask /improvise\n\n🎯 /quiz /duel /guess /word /moreless /roulette /coin /dice")


@dp.message(Command("ask"))
async def cmd_ask(message: Message):
    q = message.text.replace("/ask", "").strip()
    if not q:
        await message.answer("Напиши: /ask вопрос")
        return
    await message.answer("🤔 Думаю...")
    await message.answer(f"🤖 {await ask_ai(q)}")


@dp.message(Command("improvise"))
async def cmd_improvise(message: Message):
    await message.answer("🤔 Придумываю...")
    g = await ask_ai("Придумай короткую игру для Telegram-чата на 2 минуты. Формат: название, правила. До 300 символов.")
    await message.answer(f"🎮 <b>Игра!</b>\n\n{g}", parse_mode="HTML")# ---------- ИГРЫ ----------
@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    q = random.choice(QUESTIONS)
    games_active[message.chat.id] = {"game": "quiz", "correct": q["correct"], "q": q["q"]}
    btns = [[InlineKeyboardButton(text=a, callback_data=f"quiz_{a}")] for a in q["a"]]
    btns.append([InlineKeyboardButton(text="❌ Стоп", callback_data="quiz_stop")])
    await message.answer(f"🧠 <b>Викторина!</b>\n\n{q['q']}",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")


@dp.callback_query(F.data.startswith("quiz_"))
async def cb_quiz(call: CallbackQuery):
    if call.data == "quiz_stop":
        games_active.pop(call.message.chat.id, None)
        await call.message.edit_text("🛑 Стоп.")
        await call.answer()
        return
    ans = call.data.replace("quiz_", "")
    g = games_active.get(call.message.chat.id)
    if not g or g["game"] != "quiz":
        await call.answer("Игра кончилась")
        return
    if ans == g["correct"]:
        add_score(call.message.chat.id, call.from_user.id, 1)
        await call.message.edit_text(f"✅ <b>Правильно!</b>\n\n{g['q']}\n\nОтвет: <b>{g['correct']}</b>\n\n🏆 {call.from_user.first_name} +1", parse_mode="HTML")
        games_active.pop(call.message.chat.id, None)
    else:
        await call.answer("❌ Неверно!", show_alert=True)


@dp.message(Command("guess"))
async def cmd_guess(message: Message):
    games_active[message.chat.id] = {"game": "guess", "number": random.randint(1, 100), "tries": 0}
    await message.answer("🎯 <b>Угадай число от 1 до 100!</b>", parse_mode="HTML")


@dp.message(Command("moreless"))
async def cmd_moreless(message: Message):
    games_active[message.chat.id] = {"game": "moreless", "number": random.randint(1, 50)}
    await message.answer("📈 <b>Больше-меньше! Число от 1 до 50.</b>", parse_mode="HTML")


@dp.message(F.text.regexp(r"^\d+$"))
async def on_number(message: Message):
    g = games_active.get(message.chat.id)
    if not g:
        return
    if g.get("game") == "guess":
        n = int(message.text)
        g["tries"] += 1
        if n == g["number"]:
            add_score(message.chat.id, message.from_user.id, 3)
            await message.reply(f"🎉 Угадал! <b>{g['number']}</b> (+3)", parse_mode="HTML")
            games_active.pop(message.chat.id, None)
        elif n < g["number"]:
            await message.reply("📈 Больше!")
        else:
            await message.reply("📉 Меньше!")
    elif g.get("game") == "moreless":
        n = int(message.text)
        if n == g["number"]:
            add_score(message.chat.id, message.from_user.id, 2)
            await message.reply(f"🎉 Угадал! <b>{g['number']}</b> (+2)", parse_mode="HTML")
            games_active.pop(message.chat.id, None)
        elif n < g["number"]:
            await message.reply("📈 Больше!")
        else:
            await message.reply("📉 Меньше!")


@dp.message(Command("word"))
async def cmd_word(message: Message):
    w = random.choice(["кот", "дом", "лес", "мир", "сон", "луна", "звезда", "море", "ветер", "огонь"])
    games_active[message.chat.id] = {"game": "word", "word": w}
    s = "".join(random.sample(w, len(w)))
    await message.answer(f"📝 <b>Угадай слово:</b> <code>{s}</code>", parse_mode="HTML")


@dp.message(F.text)
async def on_text(message: Message):
    g = games_active.get(message.chat.id)
    if not g:
        return
    t = message.text.lower().strip()
    if g.get("game") == "word" and t == g["word"]:
        add_score(message.chat.id, message.from_user.id, 2)
        await message.reply(f"✅ Правильно! <b>{g['word']}</b> (+2)", parse_mode="HTML")
        games_active.pop(message.chat.id, None)
    elif g.get("game") == "riddle" and t == g["answer"].lower():
        add_score(message.chat.id, message.from_user.id, 2)
        await message.reply(f"✅ Верно! <b>{g['answer']}</b> (+2)", parse_mode="HTML")
        games_active.pop(message.chat.id, None)


@dp.message(Command("duel"))
async def cmd_duel(message: Message):
    if not message.reply_to_message:
        await message.answer("⚔️ Ответь на сообщение соперника и напиши /duel")
        return
    p1, p2 = message.from_user.id, message.reply_to_message.from_user.id
    if p1 == p2:
        await message.answer("🤦 Нельзя с собой!")
        return
    duels[message.chat.id] = {"p1": p1, "p2": p2}
    btns = [
        [InlineKeyboardButton(text="✊ Камень", callback_data="duel_rock")],
        [InlineKeyboardButton(text="✋ Бумага", callback_data="duel_paper")],
        [InlineKeyboardButton(text="✌️ Ножницы", callback_data="duel_scissors")],
    ]
    await message.answer(f"⚔️ <b>Дуэль!</b>\n\n{message.from_user.first_name} vs {message.reply_to_message.from_user.first_name}",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")


@dp.callback_query(F.data.startswith("duel_"))
async def cb_duel(call: CallbackQuery):
    g = duels.get(call.message.chat.id)
    if not g:
        await call.answer("Дуэль кончилась")
        return
    if call.from_user.id not in (g["p1"], g["p2"]):
        await call.answer("Ты не участник!")
        return
    g[call.from_user.id] = call.data.replace("duel_", "")
    if all(k in g for k in (g["p1"], g["p2"])):
        c1, c2 = g[g["p1"]], g[g["p2"]]
        beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
        names = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
        try:
            m1 = await bot.get_chat_member(call.message.chat.id, g["p1"])
            m2 = await bot.get_chat_member(call.message.chat.id, g["p2"])
            n1, n2 = m1.user.first_name, m2.user.first_name
        except Exception:
            n1, n2 = "1", "2"
        if c1 == c2:
            r = f"🤝 Ничья!\n{n1}: {names[c1]}\n{n2}: {names[c2]}"
        elif beats[c1] == c2:
            add_score(call.message.chat.id, g["p1"], 2)
            r = f"🏆 {n1} победил!\n{n1}: {names[c1]}\n{n2}: {names[c2]}"
        else:
            add_score(call.message.chat.id, g["p2"], 2)
            r = f"🏆 {n2} победил!\n{n1}: {names[c1]}\n{n2}: {names[c2]}"
        duels.pop(call.message.chat.id, None)
        await call.message.edit_text(r)
    else:
        await call.answer("Ждём противника...")


@dp.message(Command("roulette"))
async def cmd_roulette(message: Message):
    await message.answer(f"🎰 <b>{random.choice(ROULETTE)}</b>", parse_mode="HTML")


@dp.message(Command("coin"))
async def cmd_coin(message: Message):
    await message.answer(f"🪙 {random.choice(COIN)}")


@dp.message(Command("dice"))
async def cmd_dice(message: Message):
    await message.answer(f"🎲 {random.choice(DICE)}")


# ---------- КНОПКИ ИГР ----------
@dp.callback_query(F.data == "game_quiz")
async def cb_gq(call: CallbackQuery):
    q = random.choice(QUESTIONS)
    games_active[call.message.chat.id] = {"game": "quiz", "correct": q["correct"], "q": q["q"]}
    btns = [[InlineKeyboardButton(text=a, callback_data=f"quiz_{a}")] for a in q["a"]]
    btns.append([InlineKeyboardButton(text="❌ Стоп", callback_data="quiz_stop")])
    await call.message.answer(f"🧠 <b>Викторина!</b>\n\n{q['q']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "game_duel")
async def cb_gd(call: CallbackQuery):
    await call.message.answer("⚔️ Ответь на сообщение соперника и напиши /duel")
    await call.answer()


@dp.callback_query(F.data == "game_guess")
async def cb_gg(call: CallbackQuery):
    games_active[call.message.chat.id] = {"game": "guess", "number": random.randint(1, 100), "tries": 0}
    await call.message.answer("🎯 <b>Угадай число от 1 до 100!</b>", parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "game_word")
async def cb_gw(call: CallbackQuery):
    w = random.choice(["кот", "дом", "лес", "мир", "сон", "луна", "звезда", "море", "ветер", "огонь"])
    games_active[call.message.chat.id] = {"game": "word", "word": w}
    s = "".join(random.sample(w, len(w)))
    await call.message.answer(f"📝 <b>Угадай слово:</b> <code>{s}</code>", parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "game_moreless")
async def cb_gm(call: CallbackQuery):
    games_active[call.message.chat.id] = {"game": "moreless", "number": random.randint(1, 50)}
    await call.message.answer("📈 <b>Больше-меньше! Число от 1 до 50.</b>", parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "game_roulette")
async def cb_gr(call: CallbackQuery):
    await call.message.answer(f"🎰 <b>{random.choice(ROULETTE)}</b>", parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "game_coin")
async def cb_gc(call: CallbackQuery):
    await call.message.answer(f"🪙 {random.choice(COIN)}")
    await call.answer()


@dp.callback_query(F.data == "game_dice")
async def cb_gdi(call: CallbackQuery):
    await call.message.answer(f"🎲 {random.choice(DICE)}")
    await call.answer()


# ---------- МЕНЮ НЕЙРОСЕТИ ----------
@dp.callback_query(F.data == "menu_ai")
async def cb_mai(call: CallbackQuery):
    await call.message.edit_text("🤖 <b>Нейросеть</b>", reply_markup=ai_menu(), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "ai_game")
async def cb_aig(call: CallbackQuery):
    await call.message.answer("🤔 Придумываю...")
    g = await ask_ai("Придумай короткую игру для Telegram-чата на 2 минуты. Формат: название, правила. До 300 символов.")
    await call.message.answer(f"🎮 <b>Игра!</b>\n\n{g}", parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "ai_story")
async def cb_ais(call: CallbackQuery):
    await call.message.answer("📖 Придумываю...")
    s = await ask_ai("Придумай короткую смешную историю на 5-6 предложений.")
    await call.message.answer(f"📖 <b>История:</b>\n\n{s}", parse_mode="HTML")
    await call.answer()


# ---------- МЕНЮ ----------
@dp.callback_query(F.data == "menu_main")
async def cb_mm(call: CallbackQuery):
    await call.message.edit_text("🎮 Главное меню:", reply_markup=main_menu())
    await call.answer()


@dp.callback_query(F.data == "menu_games")
async def cb_mg(call: CallbackQuery):
    await call.message.edit_text("🎮 <b>Выбери игру:</b>", reply_markup=games_menu(), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "menu_top")
async def cb_mt(call: CallbackQuery):
    cs = scores.get(call.message.chat.id, {})
    if not cs:
        await call.message.answer("📊 Пока никто не играл!")
        await call.answer()
        return
    s = sorted(cs.items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 <b>Топ:</b>\n\n"
    for i, (uid, sc) in enumerate(s, 1):
        try:
            m = await bot.get_chat_member(call.message.chat.id, uid)
            name = m.user.first_name
        except Exception:
            name = f"Игрок {uid}"
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{sc}</b>\n"
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "menu_random")
async def cb_mr(call: CallbackQuery):
    await call.message.answer(f"🎲 {random.randint(1, 100)}")
    await call.answer()


@dp.callback_query(F.data == "menu_joke")
async def cb_mj(call: CallbackQuery):
    await call.message.answer(f"😄 {random.choice(JOKES)}")
    await call.answer()


@dp.callback_query(F.data == "menu_compliment")
async def cb_mc(call: CallbackQuery):
    await call.message.answer(f"💬 {random.choice(COMPLIMENTS)}")
    await call.answer()


@dp.callback_query(F.data == "menu_toilet")
async def cb_mto(call: CallbackQuery):
    await call.message.answer(random.choice(TOILET_JOKES))
    await call.answer()


@dp.callback_query(F.data == "menu_cringe")
async def cb_mcr(call: CallbackQuery):
    await call.message.answer(random.choice(CRINGE_JOKES))
    await call.answer()


@dp.callback_query(F.data == "menu_dumb")
async def cb_mdu(call: CallbackQuery):
    await call.message.answer(random.choice(DUMB_JOKES))
    await call.answer()


@dp.callback_query(F.data == "menu_truth")
async def cb_mtr(call: CallbackQuery):
    if random.choice([0, 1]):
        await call.message.answer(f"🎭 <b>Правда:</b>\n\n{random.choice(TRUTH_QUESTIONS)}", parse_mode="HTML")
    else:
        await call.message.answer(f"🎯 <b>Действие:</b>\n\n{random.choice(DARE_ACTIONS)}", parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "menu_riddle")
async def cb_mri(call: CallbackQuery):
    r = random.choice(RIDDLES)
    games_active[call.message.chat.id] = {"game": "riddle", "answer": r["a"]}
    await call.message.answer(f"🧩 <b>Загадка:</b>\n\n{r['q']}", parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "menu_country")
async def cb_mco(call: CallbackQuery):
    await call.message.answer(random.choice(COUNTRIES_FACTS))
    await call.answer()


@dp.callback_query(F.data == "menu_ascii")
async def cb_mas(call: CallbackQuery):
    await call.message.answer(f"<code>{random.choice(ASCII_ART)}</code>", parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "menu_slots")
async def cb_ms(call: CallbackQuery):
    sym = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    r = [random.choice(sym) for _ in range(3)]
    t = f"🎰 <b>Слоты</b>\n\n| {r[0]} | {r[1]} | {r[2]} |\n\n"
    if r[0] == r[1] == r[2]:
        t += "🎉 <b>ДЖЕКПОТ!</b>"
        add_score(call.message.chat.id, call.from_user.id, 5)
    elif r[0] == r[1] or r[1] == r[2] or r[0] == r[2]:
        t += "✨ Два совпали!"
        add_score(call.message.chat.id, call.from_user.id, 1)
    else:
        t += "😢 Не повезло."
    await call.message.answer(t, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "menu_help")
async def cb_mh(call: CallbackQuery):
    await call.message.answer("❓ /games /top /joke /compliment /toilet /cringe /dumb /truth /riddle /country /ascii /slots /ask /improvise\n\n🎯 /quiz /duel /guess /word /moreless /roulette /coin /dice")
    await call.answer()


# ---------- ИНЛАЙН (расширенный) ----------
@dp.inline_query()
async def inline_handler(query: InlineQuery):
    t = query.query.strip().lower()
    res = []
    if not t:
        res = [
            InlineQueryResultArticle(id="r", title="🎲 Число", description="1-100", input_message_content=InputTextMessageContent(message_text=f"🎲 {random.randint(1, 100)}")),
            InlineQueryResultArticle(id="j", title="😄 Шутка", input_message_content=InputTextMessageContent(message_text=random.choice(JOKES))),
            InlineQueryResultArticle(id="to", title="💩 Туалетный", input_message_content=InputTextMessageContent(message_text=random.choice(TOILET_JOKES))),
            InlineQueryResultArticle(id="du", title="🤪 Тупой", input_message_content=InputTextMessageContent(message_text=random.choice(DUMB_JOKES))),
            InlineQueryResultArticle(id="cr", title="😬 Кринж", input_message_content=InputTextMessageContent(message_text=random.choice(CRINGE_JOKES))),
            InlineQueryResultArticle(id="co", title="💬 Комплимент", input_message_content=InputTextMessageContent(message_text=random.choice(COMPLIMENTS))),
            InlineQueryResultArticle(id="ri", title="🧩 Загадка", input_message_content=InputTextMessageContent(message_text=random.choice(RIDDLES)["q"])),
            InlineQueryResultArticle(id="cf", title="🌍 Страна", input_message_content=InputTextMessageContent(message_text=random.choice(COUNTRIES_FACTS))),
            InlineQueryResultArticle(id="as", title="🎨 ASCII", input_message_content=InputTextMessageContent(message_text=random.choice(ASCII_ART))),
            InlineQueryResultArticle(id="mo", title="🪙 Монетка", input_message_content=InputTextMessageContent(message_text=random.choice(COIN))),
            InlineQueryResultArticle(id="di", title="🎲 Кубик", input_message_content=InputTextMessageContent(message_text=random.choice(DICE))),
            InlineQueryResultArticle(id="ro", title="🎰 Рулетка", input_message_content=InputTextMessageContent(message_text=random.choice(ROULETTE))),
            InlineQueryResultArticle(id="tr", title="🎭 Правда/Действие", input_message_content=InputTextMessageContent(message_text=random.choice(TRUTH_QUESTIONS + DARE_ACTIONS))),
            InlineQueryResultArticle(id="ai", title="🤖 Спросить нейросеть", description="Напиши вопрос", input_message_content=InputTextMessageContent(message_text="🤖 Напиши /ask в чате, чтобы спросить нейросеть.")),
        ]
    elif "шутк" in t:
        res = [InlineQueryResultArticle(id="j", title="😄 Шутка", input_message_content=InputTextMessageContent(message_text=random.choice(JOKES)))]
    elif "туалет" in t or "какаш" in t:
        res = [InlineQueryResultArticle(id="to", title="💩 Туалетный", input_message_content=InputTextMessageContent(message_text=random.choice(TOILET_JOKES)))]
    elif "туп" in t:
        res = [InlineQueryResultArticle(id="du", title="🤪 Тупой", input_message_content=InputTextMessageContent(message_text=random.choice(DUMB_JOKES)))]
    elif "кринж" in t:
        res = [InlineQueryResultArticle(id="cr", title="😬 Кринж", input_message_content=InputTextMessageContent(message_text=random.choice(CRINGE_JOKES)))]
    elif "комплимент" in t:
        res = [InlineQueryResultArticle(id="co", title="💬 Комплимент", input_message_content=InputTextMessageContent(message_text=random.choice(COMPLIMENTS)))]
    elif "загадк" in t:
        res = [InlineQueryResultArticle(id="ri", title="🧩 Загадка", input_message_content=InputTextMessageContent(message_text=random.choice(RIDDLES)["q"]))]
    elif "страны" in t or "факт" in t:
        res = [InlineQueryResultArticle(id="cf", title="🌍 Страна", input_message_content=InputTextMessageContent(message_text=random.choice(COUNTRIES_FACTS)))]
    elif "ascii" in t:
        res = [InlineQueryResultArticle(id="as", title="🎨 ASCII", input_message_content=InputTextMessageContent(message_text=random.choice(ASCII_ART)))]
    elif "монет" in t:
        res = [InlineQueryResultArticle(id="mo", title="🪙 Монетка", input_message_content=InputTextMessageContent(message_text=random.choice(COIN)))]
    elif "кубик" in t:
        res = [InlineQueryResultArticle(id="di", title="🎲 Кубик", input_message_content=InputTextMessageContent(message_text=random.choice(DICE)))]
    elif "рулет" in t:
        res = [InlineQueryResultArticle(id="ro", title="🎰 Рулетка", input_message_content=InputTextMessageContent(message_text=random.choice(ROULETTE)))]
    elif "правда" in t or "действие" in t:
        res = [InlineQueryResultArticle(id="tr", title="🎭 Правда/Действие", input_message_content=InputTextMessageContent(message_text=random.choice(TRUTH_QUESTIONS + DARE_ACTIONS)))]
    else:
        res = [InlineQueryResultArticle(id="custom", title=f"Отправить: {query.query}", input_message_content=InputTextMessageContent(message_text=query.query))]
    await query.answer(results=res, cache_time=0)


# ---------- ГОСТЕВОЙ РЕЖИМ ----------
try:
    @dp.guest_message(F.text)
    async def guest_handler(message: Message):
        try:
            txt = message.text or ""
            q = txt.replace(f"@{BOT_USERNAME}", "").strip()
            ans = await ask_ai(q) if q else random.choice(JOKES + TOILET_JOKES + DUMB_JOKES)
            await message.answer_guest_query(
                result=InlineQueryResultArticle(id="g", title="Ответ",
                    input_message_content=InputTextMessageContent(message_text=ans))
            )
        except Exception as e:
            logging.error(f"Guest error: {e}")
except AttributeError:
    logging.warning("Гостевой режим недоступен в этой версии aiogram")


# ---------- ЗАПУСК ----------
async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Меню"),
        BotCommand(command="games", description="Игры"),
        BotCommand(command="top", description="Топ"),
        BotCommand(command="quiz", description="Викторина"),
        BotCommand(command="duel", description="Дуэль"),
        BotCommand(command="guess", description="Угадай число"),
        BotCommand(command="word", description="Слова"),
        BotCommand(command="moreless", description="Больше-меньше"),
        BotCommand(command="roulette", description="Рулетка"),
        BotCommand(command="coin", description="Монетка"),
        BotCommand(command="dice", description="Кубик"),
        BotCommand(command="random", description="Рандом"),
        BotCommand(command="joke", description="Шутка"),
        BotCommand(command="compliment", description="Комплимент"),
        BotCommand(command="toilet", description="Туалетный"),
        BotCommand(command="dumb", description="Тупые"),
        BotCommand(command="cringe", description="Кринж"),
        BotCommand(command="truth", description="Правда/Действие"),
        BotCommand(command="riddle", description="Загадка"),
        BotCommand(command="country", description="Страны"),
        BotCommand(command="ascii", description="ASCII"),
        BotCommand(command="slots", description="Слоты"),
        BotCommand(command="ask", description="Нейросеть"),
        BotCommand(command="improvise", description="Придумать игру"),
        BotCommand(command="help", description="Помощь"),
    ])


async def main():
    global BOT_USERNAME
    me = await bot.get_me()
    BOT_USERNAME = me.username
    await set_commands()
    logging.info(f"Бот @{BOT_USERNAME} запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
