import asyncio
import random
from telegram import Update
from telegram.ext import ContextTypes
from database import get_conn

WORD_BANK = {
    "cat": "A small domesticated feline.",
    "dog": "Man's best friend.",
    "bird": "It flies and chirps.",
    "cow": "Gives milk and moos.",
    "fish": "Lives in water and swims.",
    "lion": "King of the jungle.",
    "pizza": "Cheesy Italian dish.",
    "apple": "Keeps the doctor away.",
    "mountain": "A large natural elevation.",
    "rainbow": "Colorful arc in the sky.",
    "engineer": "Designs and builds things.",
    "freedom": "State of being free.",
    "chaos": "Complete disorder.",
    "epiphany": "Sudden realization.",
    "serendipity": "Happy accident.",
    "guitar": "String instrument.",
    "book": "Filled with pages and stories.",
    "moon": "Earth's natural satellite.",
    "sun": "Center of our solar system.",
    "river": "Flows through land.",
    "forest": "Dense area of trees.",
    "doctor": "Heals the sick.",
    "teacher": "Educates students.",
    "car": "Has wheels and drives.",
    "train": "Runs on tracks.",
    "plane": "Flies in the sky.",
    "hat": "Worn on the head.",
    "shoe": "Worn on the foot.",
    "ice": "Frozen water.",
    "fire": "Hot and burns.",
    "love": "Deep affection.",
    "truth": "Opposite of lie.",
    "dream": "Vision during sleep.",
    "peace": "Absence of conflict.",
    "justice": "Fair treatment.",
    "cookie": "Sweet baked treat.",
    "cake": "Celebration dessert.",
    "banana": "Yellow fruit.",
    "zebra": "Striped animal.",
    "panda": "Black and white bear.",
    "giraffe": "Tall animal with long neck.",
    "dolphin": "Smart sea mammal.",
    "shark": "Predator of the ocean.",
    "rabbit": "Hops and has long ears.",
    "kangaroo": "Jumps and has a pouch.",
    "mirror": "Reflects your image.",
    "clock": "Tells time.",
    "phone": "Used to call people.",
    "laptop": "Portable computer.",
    "rain": "Water falling from sky.",
    "snow": "Frozen white flakes.",
    "wind": "Air in motion.",
    "cloud": "Floating vapor in sky.",
    "earthquake": "Ground shaking event.",
    "volcano": "Erupts lava.",
    "artist": "Creates visual art.",
    "singer": "Performs songs.",
    "writer": "Creates stories.",
    "lawyer": "Defends in court.",
    "chef": "Cooks professionally.",
    "pilot": "Flies aircraft.",
    "driver": "Operates vehicles.",
    "actor": "Performs in films.",
    "dancer": "Moves rhythmically.",
    "scientist": "Studies the natural world.",
    "athlete": "Competes in sports.",
    "friend": "Someone you trust.",
    "smile": "Expression of happiness.",
    "cry": "Shed tears.",
    "laugh": "Sound of joy.",
    "swim": "Move through water.",
    "run": "Move quickly on foot.",
    "jump": "Leap into the air.",
    "sit": "Rest on a surface.",
    "stand": "Be upright.",
    "eat": "Consume food.",
    "drink": "Consume liquid.",
    "read": "Interpret text.",
    "write": "Put words on paper.",
    "draw": "Make pictures.",
    "play": "Engage in fun.",
    "talk": "Speak words.",
    "look": "Use your eyes.",
    "cook": "Prepare food.",
    "clean": "Remove dirt.",
    "yes": "Affirmative.",
    "no": "Negative.",
    "hello": "Greeting.",
    "bye": "Farewell.",
    "thank": "Show gratitude.",
    "please": "Polite request.",
    "good": "Positive quality.",
    "bad": "Negative quality."
}

user_sessions = {}

async def startwordgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = random.choice(list(WORD_BANK.keys()))
    session = {
        "word": word,
        "guessed": [],
        "lives": len(set(word)),
        "hint": WORD_BANK[word]
    }
    user_sessions[user_id] = session
    display = " ".join(["_" for _ in word])
    await update.message.reply_text(
        f"🎮 Word Guess Game Started!\nWord: {display}\nLives: {session['lives']}\nUse /ithink or /g <letter> to play \n /hint to get a hint."
    )

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)

    if not session:
        return await update.message.reply_text("⚠️ No active game. Use /startwordgame to begin.")

    if not context.args:
        return await update.message.reply_text("📝 Usage: /ithink <letter>")

    letter = context.args[0].lower()
    word = session["word"]
    guessed = session["guessed"]

    if letter in guessed:
        return await update.message.reply_text("🔁 Already guessed that letter.")

    guessed.append(letter)

    if letter in word:
        def _db_insert():
            with get_conn() as conn:
                conn.execute("""
                    INSERT INTO word_scores (user_id, username, points)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id) DO UPDATE SET points = points + 1
                """, (user_id, update.effective_user.username or "unknown"))
                conn.commit()
        await asyncio.to_thread(_db_insert)

        display = " ".join([c if c in guessed else "_" for c in word])
        if all(c in guessed for c in word):
            user_sessions.pop(user_id)
            return await update.message.reply_text(f"🏆 You guessed the word: {word}!\n🎉 Victory!")
        return await update.message.reply_text(f"✅ Correct!\nWord: {display}\nLives: {session['lives']}")
    else:
        session["lives"] -= 1
        if session["lives"] <= 0:
            user_sessions.pop(user_id)
            return await update.message.reply_text(f"💀 Out of lives!\nThe word was: {word}")
        display = " ".join([c if c in guessed else "_" for c in word])
        return await update.message.reply_text(f"❌ Wrong!\nWord: {display}\nLives left: {session['lives']}")

async def hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)

    if not session:
        return await update.message.reply_text("⚠️ No active game. Use /startwordgame to begin.")

    await update.message.reply_text(f"💡 Hint: {session['hint']}")

async def wordscore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    def _db_query():
        with get_conn() as conn:
            row = conn.execute("SELECT points FROM word_scores WHERE user_id = ?", (user_id,)).fetchone()
            return row[0] if row else 0
    points = await asyncio.to_thread(_db_query)
    await update.message.reply_text(f"🏅 Your Word Guess Score: {points} points")

async def wordtop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _db_query():
        with get_conn() as conn:
            return conn.execute("SELECT username, points FROM word_scores ORDER BY points DESC LIMIT 10").fetchall()
    rows = await asyncio.to_thread(_db_query)
    if not rows:
        return await update.message.reply_text("📭 No scores yet.")
    lines = ["🏆 Top Word Guess Players:"]
    for i, (username, points) in enumerate(rows, start=1):
        lines.append(f"{i}. @{username} — {points} pts")
    await update.message.reply_text("\n".join(lines))
