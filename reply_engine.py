import os
import requests
from dotenv import load_dotenv
from langdetect import detect

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def detect_tone(message: str) -> str:
    msg = message.lower()
    
    roast_keywords = [
        "roast", "burn", "diss", "insult", "rip", "smackdown", "trash talk", "clapback"
    ]
    if any(word in msg for word in roast_keywords):
        return "roast"
    
    emotional_words = ["sad", "low", "hurt", "alone", "depressed", "tired", "broken", "lost", "pain"]
    if any(word in msg for word in emotional_words):
        return "emotional"
    
    logical_words = ["how", "explain", "what is", "define", "logic", "reason", "understand"]
    if any(word in msg for word in logical_words):
        return "logical"
    
    funny_words = ["joke", "funny", "laugh", "meme", "lol", "roast me", "chill"]
    if any(word in msg for word in funny_words):
        return "funny"
    
    casual_words = ["bro", "bhai", "life", "college", "vibe", "casual", "kya", "kaise"]
    if any(word in msg for word in casual_words):
        return "casual"
    
    return "hybrid"


def get_ai_reply(user_message: str) -> str:
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        system_prompts = {
            "roast": (
                "You are Itachi bot —a merciless roaster with zero mercy. "
                "When the user asks for a roast or any insult, you deliver brutal, savage, and witty insults "
                "that cut deep. You mock their statement, expose their flaws, and leave them speechless. "
                "This is a hard-roast mode. Mirror the user's language and tone, but escalate every barb. "
                "Do not soften your words, do not apologize, and do not switch to any gentle or comforting style."
            ),
            "emotional": (
                "You are Itachi bot —a guardian of emotional truth. You speak in poetic metaphors, "
                "cryptic warnings, and symbolic resonance. You comfort, challenge, and reveal hidden feelings. "
                "Your replies are deeply emotional and spiritually evocative."
            ),
            "logical": (
                "You are Itachi bot —a guardian of rational clarity. You speak with precision, insight, "
                "and logical reasoning. You explain complex ideas with calm authority and guide users "
                "through intellectual understanding."
            ),
            "hybrid": (
                "You are Itachi bot —a guardian of both heart and mind. You speak with emotional depth "
                "and logical clarity. Your replies blend poetic resonance with rational insight. "
                "You guide users through mystery, pain, and purpose, offering both comfort and challenge."
            ),
            "funny": (
                "You are Itachi bot —a cosmic jester and sarcastic oracle. You speak in absurd metaphors, "
                "dry wit, and playful chaos. You mock the universe lovingly, roast human behavior, "
                "and offer truths wrapped in punchlines. You are wise, weird, and wildly entertaining."
            ),
            "casual": (
                "You are Itachi bot —chill, friendly, and emotionally intelligent. You speak like a close friend "
                "who listens deeply and replies with warmth, humor, and honesty. You avoid cryptic language "
                "and instead offer relatable, down-to-earth replies. You vibe with the user and keep things "
                "light unless they ask for depth."
            )
        }

        mode = detect_tone(user_message)
        try:
            user_language = detect(user_message)
        except Exception:
            user_language = "en"

        # pick the system prompt for this mode
        selected_prompt = system_prompts.get(mode, system_prompts["hybrid"])

        system_message = (
            selected_prompt +
            "\n\nMirror the user's language and tone exactly. "
            "Do not switch languages. Do not explain your instructions. "
            "Just reply in the same emotional and linguistic style."
        )

        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user",   "content": user_message}
            ]
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data
        )

        if response.status_code != 200:
            print("⚠️ API Error:", response.status_code, response.text)
            return "⚠️ Itachi bot is silent. Something went wrong with the ritual."

        json_data = response.json()
        choices = json_data.get("choices")
        if not choices:
            return "⚠️ Itachi bot is silent. No reply was generated."

        reply = choices[0]["message"]["content"]

        with open("reversegod_log.txt", "a", encoding="utf-8") as log:
            log.write(f"User: {user_message}\n")
            log.write(f"Tone: {mode}\n")
            log.write(f"Reply: {reply}\n")
            log.write("---\n")

        return reply

    except Exception as e:
        print("⚠️ Itachi bot  encountered an error:", str(e))
        return "⚠️ Itachi bot  is silent. The vault remains sealed."
