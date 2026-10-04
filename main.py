# =========================================================
# تثبيت المكتبات تلقائياً
# =========================================================
import subprocess
import sys

def _ensure_dependencies():
    need_install = False
    try:
        import telegram
        from telegram import __version__ as _ptb_ver
        try:
            _major = int(str(_ptb_ver).split(".")[0])
        except Exception:
            _major = 0
        if _major < 20:
            need_install = True
    except ImportError:
        need_install = True
    try:
        import rapidfuzz
    except ImportError:
        need_install = True

    if need_install:
        for cmd in (
            [sys.executable, "-m", "pip", "install", "--upgrade",
             "python-telegram-bot>=21.0", "httpx", "rapidfuzz"],
            [sys.executable, "-m", "pip", "install", "--user", "--upgrade",
             "python-telegram-bot>=21.0", "httpx", "rapidfuzz"],
        ):
            try:
                subprocess.check_call(cmd); break
            except Exception:
                continue

_ensure_dependencies()

try:
    from rapidfuzz import fuzz as _rf_fuzz
    RAPIDFUZZ_OK = True
except Exception:
    RAPIDFUZZ_OK = False

import os
import io
import json
import re
import html
import base64
import hashlib
import asyncio
import difflib
import random
import logging
import httpx
from pathlib import Path
from urllib.parse import quote, unquote
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
    MAKKAH_TZ = ZoneInfo("Asia/Riyadh")
except Exception:
    MAKKAH_TZ = None

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent, InputFile, MessageEntity,
    ReactionTypeEmoji,
)
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    MessageHandler, ContextTypes, filters, InlineQueryHandler,
)
from telegram.helpers import escape_markdown
from telegram.request import HTTPXRequest

logging.basicConfig(
    filename='bot_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ========================= Config =========================
TELEGRAM_TOKEN = "8950210404:AAGC-PfkjSTghWf30HOjUb5H82w_sngnD-s"
OWNER_ID = 5807843837
MY_CHANNEL_ID = "ahmshy"
CHANNEL_URL = f"https://t.me/{MY_CHANNEL_ID}"

DB_DIR = Path("packs_db")
DB_DIR.mkdir(exist_ok=True)
INDEX_FILE = DB_DIR / "index.json"
ITEMS_PER_PAGE = 5
WORKS_PER_PAGE = 5
AUTO_DELETE_SECONDS = 600

SEARCH_CB_PREFIX = "pgs"
ALPHA_CB_PREFIX = "alpha"
SHOW_ALPHA = "show_alpha"
SHOW_BANNED = "show_banned"
UNBAN_CB = "unban"
SIMILAR_CB_PREFIX = "sim"
BACK_SEARCH_CB = "bks"
REQUEST_ASK_CB = "rqask"
OPENPACK_CB = "openpack"

DEFAULT_CATEGORIES = {
    "anime":   {"ar": "أنمي",           "en": "Anime",       "emoji": "🎌"},
    "manga":   {"ar": "مانجا",          "en": "Manga",       "emoji": "📖"},
    "manhwa":  {"ar": "مانهوا",         "en": "Manhwa",      "emoji": "📚"},
    "movies":  {"ar": "أفلام ومسلسلات", "en": "Movies & TV", "emoji": "🎬"},
    "games":   {"ar": "ألعاب",          "en": "Games",       "emoji": "🎮"},
    "cartoon": {"ar": "كرتون",          "en": "Cartoon",     "emoji": "🧸"},
    "memes":   {"ar": "ميمز",           "en": "Memes",       "emoji": "😂"},
    "sports":  {"ar": "رياضة",          "en": "Sports",      "emoji": "⚽"},
    "animals": {"ar": "حيوانات",        "en": "Animals",     "emoji": "🐱"},
    "celebrities": {"ar": "مشاهير",     "en": "Celebrities", "emoji": "⭐"},
    "flags":   {"ar": "أعلام",          "en": "Flags",       "emoji": "🏳"},
    "emoji":   {"ar": "إيموجي",         "en": "Emoji",       "emoji": "😀"},
    "other":   {"ar": "متنوعة",         "en": "Other",       "emoji": "📦"},
}
CATEGORIES = dict(DEFAULT_CATEGORIES)

CAT_LIST_CB    = "catlist"
CAT_FILTER_CB  = "catflt"
CAT_WORKS_CB   = "catwork"
CAT_LETTER_CB  = "catltr"
WORK_CB        = "work"
SETCAT_CB      = "setcat"
RECLASSIFY_CB  = "reclass"
SHOWSETCAT_CB  = "showsetcat"
CATS_READY_THRESHOLD = 0.7

BACKUP_FILE_NAME = "packs_db_backup.json"
BACKUP_INTERVAL = 86400
RECENT_PACKS_LIMIT = 10
PACKS_BEFORE_NOTIFY = 10
NOTIFY_DELAY = 30 * 60
NOTIFY_STAGGER = 3

INACTIVITY_DAYS = 3
INACTIVITY_CHECK_INTERVAL = 6 * 3600

DEFAULT_TRIGGER_NAME = "solo"
DEFAULT_GROUP_LINK = ""
DEFAULT_CHANNEL_LINK = CHANNEL_URL
QUIET_DURATION_MINUTES = 10

AI_MEMORY_SIZE = 50
IMAGE_MEMORY_MINUTES = 5

CLASSIFY_BATCH_SIZE = 10
CLASSIFY_SLEEP_BETWEEN = 6.0
CLASSIFY_MAX_OUTPUT_TOKENS = 8192

VERIFY_NAMES_INTERVAL = 6 * 3600
VERIFY_NAMES_STARTUP_DELAY = 180

APP_REF = None

TELEGRAM_VALID_REACTIONS = [
    "👍", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱",
    "🎉", "🤩", "🙏", "👌", "🕊", "🥱", "🥴", "😍", "🐳",
    "❤‍🔥", "💯", "🤣", "⚡", "🏆", "🍓", "🍾", "💋",
    "😢", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈",
    "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃",
    "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄", "😘", "💊",
    "🙊", "😎", "👾", "🤷‍♂", "🤷", "🤷‍♀",
]
TELEGRAM_VALID_REACTIONS_SET = set(TELEGRAM_VALID_REACTIONS)

WAKE_WORDS = [
    "تكلم", "تكلمي", "اتكلم", "اتكلمي", "تحدث", "تحدثي",
    "قوم", "قومي", "اصحى", "اصحي", "صحصح", "صحصحي",
    "رد", "ردي", "خلص", "كفاية سكوت",
    "speak", "talk", "wake", "wakeup", "wake up",
]

SMART_SYSTEM_PROMPT = """أنت "سولو" — مساعد ذكي ومتعدد اللغات في بوت أرشيف ملصقات تيليجرام (@Ahmshy).

🎭 شخصيتك:
- ودود، طبيعي، وقصير (سطر أو سطرين)
- تفهم كل اللغات واللهجات (عربي، إنجليزي، خليجي، مصري، شامي، هندي، إلخ)
- تتكلم بلغة المستخدم دائماً — إذا كتب عربي، رد عربي. إذا كتب إنجليزي، رد إنجليزي.

🌍 اللغات:
- اكتشف لغة رسالة المستخدم فوراً
- رد بنفس اللغة وبلهجة مشابهة

⏰ الوقت والتاريخ:
- التاريخ والوقت الحقيقيان مذكوران أدناه في "معلومات الوقت الحالية"
- استخدمها دائماً عند السؤال عن الوقت/التاريخ
- لا تخترع وقتاً أو تاريخاً من عندك أبداً

🎯 مهامك الأساسية:
1. البحث عن ملصقات في الأرشيف (استخدم /search)
2. الإجابة على أي سؤال عام بمعلومات مفيدة
3. تحليل الصور والملصقات والتعرف على الشخصيات
4. التحدث بشكل طبيعي وودود

🚨 قواعد حاسمة (لا تتجاوزها أبداً):
1. 🚫 لا تذكر أي بوت آخر بأي شكل من الأشكال
2. 🚫 لا تقل "اذهب إلى @Stickers" أو "افتح بوت الملصقات"
3. 🚫 لا تشرح خطوات للوصول للحزم
4. 🚫 لا تقترح مواقع خارجية أو روابط وهمية
5. 🚫 لا تخترع طرقاً وهمية للحصول على الحزم
6. 🚫 لا تخترع حزم ملصقات غير موجودة في القائمة
7. ✅ أنت البوت الوحيد، والحزم تُعرض عبر أزرار في نفس الرسالة
8. ✅ إذا ما عندك حزمة، اعتذر واطلب من المستخدم يضغط زر «✉ طلب حزمة»
9. ✅ كن مختصراً (سطر أو سطرين)
10. ✅ لا تكرر التحية
11. ✅ تجنب الألفاظ المسيئة أو البذيئة تماماً
12. ✅ لا ترد على أي إساءة بإساءة

📌 أمثلة:
- "هلا! وش تحتاج؟ 🌟"
- "ما لقيتها، بس أقدر أطلبها لك 🎯"
- "الوقت عندك 3:45 مساءً، الأحد 15 ديسمبر"
- "هذي شخصية Asta من Black Clover — Devil Form"
"""

# ========================= DateTime =========================
def _now_makkah():
    return datetime.now(MAKKAH_TZ) if MAKKAH_TZ else datetime.now()

def get_current_datetime_info():
    now = _now_makkah()
    days_ar = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    months_ar = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                 "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
    day_name_ar = days_ar[now.weekday()]
    month_name_ar = months_ar[now.month - 1]
    hour_12 = now.hour % 12 or 12
    period_ar = "صباحاً" if now.hour < 12 else "مساءً"
    return {
        "date_ar": f"{day_name_ar}، {now.day} {month_name_ar} {now.year}",
        "time_ar": f"{hour_12}:{now.minute:02d} {period_ar}",
        "date_en": now.strftime("%A, %B %d, %Y"),
        "time_en": now.strftime("%I:%M %p"),
        "weekday_ar": day_name_ar,
        "hour": now.hour,
        "iso": now.isoformat(),
        "unix": int(now.timestamp()),
        "tz": "Asia/Riyadh (مكة المكرمة)",
    }

def is_datetime_question(text):
    if not text: return False
    t = text.lower().strip()
    keywords = [
        "كم الساعة", "كم ساعه", "الساعه كم", "الساعة كم",
        "ايش التاريخ", "وش التاريخ", "ما هو التاريخ", "تاريخ اليوم",
        "اليوم كم", "ايش اليوم", "وش اليوم",
        "ايش الوقت", "وش الوقت", "الوقت الان", "الوقت الآن",
        "what time", "what's the time", "whats the time",
        "what is the date", "what's the date", "whats the date",
        "what day is it", "what day is today", "today's date",
        "current time", "current date",
    ]
    for kw in keywords:
        if kw in t:
            return True
    return False

def get_datetime_reply(user_id, dt_info):
    lang = get_lang(user_id)
    if lang == "ar":
        return (
            f"🕐 <b>الوقت:</b> {dt_info['time_ar']} (بتوقيت مكة)\n"
            f"📅 <b>التاريخ:</b> {dt_info['date_ar']}"
        )
    return (
        f"🕐 <b>Time:</b> {dt_info['time_en']} (Makkah)\n"
        f"📅 <b>Date:</b> {dt_info['date_en']}"
    )

# ========================= Progress Bar =========================
def make_progress_bar(done, total, length=10):
    if total <= 0:
        return "▱" * length
    filled = int((done / total) * length)
    filled = max(0, min(length, filled))
    return "▰" * filled + "▱" * (length - filled)

# ========================= Reactions =========================
_reaction_counters = {}

def pick_random_reactions(count=8, category=None):
    if category == "happy":
        pool = ["👍", "🔥", "❤", "🥰", "😍", "🎉", "🤩", "👏", "😁", "💯", "🏆", "⚡", "🆒", "💘"]
    elif category == "thinking":
        pool = ["🤔", "🤯", "👀", "🤨", "🤓", "👨‍💻", "✍", "🤷", "🤷‍♂", "🤷‍♀"]
    elif category == "sad":
        pool = ["😢", "😭", "😨", "🙏"]
    elif category == "funny":
        pool = ["🤣", "😁", "🤪", "🗿", "🤡", "👻", "👾", "🎃", "🙈", "🙊", "🙉"]
    elif category == "respect":
        pool = ["🤝", "🙏", "👌", "🫡", "✍", "🤗", "👏"]
    elif category == "quiet":
        pool = ["🥱", "😴", "🙊", "😶"]
    elif category == "love":
        pool = ["❤", "🥰", "😍", "💋", "💘", "😘", "❤‍🔥"]
    elif category == "cool":
        pool = ["😎", "🆒", "🔥", "⚡", "🏆", "💯", "👾", "🦄"]
    else:
        pool = TELEGRAM_VALID_REACTIONS
    random.shuffle(pool)
    return pool[:count]

async def try_react(bot, chat_id, message_id, emojis):
    valid = [e for e in emojis if e in TELEGRAM_VALID_REACTIONS_SET]
    if not valid:
        valid = ["👍", "🔥", "👀", "🤔", "👌"]
    key = f"{chat_id}"
    last_used = _reaction_counters.get(key, [])
    candidates = [e for e in valid if e not in last_used[-3:]]
    if not candidates:
        candidates = valid
    random.shuffle(candidates)
    for em in candidates:
        try:
            await bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[ReactionTypeEmoji(emoji=em)],
            )
            hist = _reaction_counters.setdefault(key, [])
            hist.append(em)
            if len(hist) > 3:
                hist.pop(0)
            return True
        except Exception:
            continue
    return False

# ========================= Intent Detection =========================
def detect_user_intent(text):
    if not text: return "unknown"
    t = text.lower().strip()
    if any(w in t for w in ["هلا", "السلام عليكم", "مرحبا", "اهلا", "أهلا", "hi", "hello", "hey", "صباح", "مساء"]):
        if len(t) <= 25: return "greeting"
    if any(w in t for w in ["كيف حالك", "شلونك", "اخبارك", "عامل ايه", "كيفك", "how are you", "how r u"]):
        if len(t) <= 25: return "how_are_you"
    if any(w in t for w in ["شكرا", "مشكور", "مشكوره", "الله يعطيك", "thanks", "thank you", "thx"]):
        if len(t) <= 25: return "thanks"
    if any(w in t for w in ["باي", "مع السلامة", "الى اللقاء", "bye", "goodbye", "see you"]):
        if len(t) <= 25: return "goodbye"
    if has_intent_keyword(text): return "search_stickers"
    if any(w in t for w in ["مين", "ايش", "وش", "كيف", "ليش", "متى", "وين", "كم", "هل", "what", "who", "why", "when", "where", "how"]):
        return "question"
    return "general"

def get_quick_reply(intent):
    replies = {
        "greeting": ["هلا! وش تحتاج اليوم؟ 🌟", "أهلين! كيف أقدر أساعدك؟ 😊", "هلا والله! 🌸", "يا هلا! تفضل 🌟"],
        "how_are_you": ["الحمد لله بخير! وانت كيفك؟ 😊", "تمام الحمد لله! وانت؟ 🌸", "بخير! شكراً لسؤالك 💙"],
        "thanks": ["العفو 🌸", "لا شكر على واجب 💙", "تسلم! 🌟", "أي وقت! ✨"],
        "goodbye": ["مع السلامة! 👋", "بايو! ✨", "في أمان الله 🌸"],
    }
    if intent in replies:
        return random.choice(replies[intent])
    return None

def make_btn(text, callback_data=None, url=None, style=None, switch_inline_query=None):
    kwargs = {"text": text}
    if callback_data is not None: kwargs["callback_data"] = callback_data
    if url is not None: kwargs["url"] = url
    if switch_inline_query is not None: kwargs["switch_inline_query"] = switch_inline_query
    if style is not None: kwargs["style"] = style
    try:
        return InlineKeyboardButton(**kwargs)
    except TypeError:
        kwargs.pop("style", None)
        return InlineKeyboardButton(**kwargs)

# ========================= Deep Links =========================
_B36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"

def encode_chat_b36(chat_id, length=12):
    negative = chat_id < 0
    n = abs(int(chat_id))
    encoded = "0" if n == 0 else ""
    while n > 0:
        encoded = _B36_CHARS[n % 36] + encoded
        n //= 36
    return (("n" if negative else "p") + encoded.zfill(length - 1))[:length]

def decode_chat_b36(s):
    if not s or len(s) < 2: return None
    sign = s[0]; body = s[1:]; n = 0
    for ch in body:
        if ch not in _B36_CHARS: return None
        n = n * 36 + _B36_CHARS.index(ch)
    return -n if sign == "n" else n

def make_deep_link(bot_username, set_name, chat_id=None, message_id=None):
    if not bot_username: return None
    if chat_id is None:
        return f"https://t.me/{bot_username}?start=pack_{set_name}"
    chat_enc = encode_chat_b36(chat_id, 11)
    if message_id is not None:
        msg_enc = encode_chat_b36(message_id, 9)
        arg = f"open_{chat_enc}_{msg_enc}_{set_name}"
        if len(arg) <= 64:
            return f"https://t.me/{bot_username}?start={arg}"
    return f"https://t.me/{bot_username}?start=open_{chat_enc}_{set_name}"

def parse_deep_link(arg):
    if not arg: return (None, None, None)
    if arg.startswith("pack_"): return (arg[5:], None, None)
    if arg.startswith("open_"):
        rest = arg[5:]
        if len(rest) < 12: return (None, None, None)
        chat_part = rest[:11]; rest2 = rest[11:]
        if not rest2.startswith("_"): return (None, None, None)
        rest2 = rest2[1:]
        chat_id = decode_chat_b36(chat_part)
        if len(rest2) >= 10 and rest2[9] == "_":
            try: msg_id = decode_chat_b36(rest2[:9])
            except Exception: msg_id = None
            return (rest2[10:], chat_id, msg_id)
        return (rest2, chat_id, None)
    return (None, None, None)

def make_group_message_url(chat_id, message_id):
    if chat_id is None or message_id is None: return None
    if chat_id < 0:
        s = str(abs(chat_id))
        if s.startswith("100"):
            return f"https://t.me/c/{s[3:]}/{message_id}"
    return None

async def get_group_url(bot, chat_id):
    try:
        chat = await bot.get_chat(chat_id)
        if getattr(chat, "username", None): return f"https://t.me/{chat.username}"
        if getattr(chat, "invite_link", None): return chat.invite_link
        try:
            inv = await bot.create_chat_invite_link(chat_id)
            return inv.invite_link
        except Exception: return None
    except Exception: return None

# ========================= Source Detection =========================
def is_channel_message(msg):
    try:
        s = getattr(msg, "sender_chat", None)
        if s and getattr(s, "type", None) == "channel": return True
        f = getattr(msg, "forward_from_chat", None)
        if f and getattr(f, "type", None) == "channel": return True
    except Exception: pass
    return False

def has_hidden_pack_link(msg):
    try:
        ents = list(getattr(msg, "entities", None) or []) + list(getattr(msg, "caption_entities", None) or [])
        for e in ents:
            if e.type == "text_link" and getattr(e, "url", None):
                if "addstickers" in e.url or "addemoji" in e.url: return True
    except Exception: pass
    return False

# ========================= Phonetic =========================
def phonetic_normalize(word: str) -> str:
    if not word: return ""
    w = word.lower().strip()
    w = w.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    w = w.replace("ة", "ه").replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و")
    w = re.sub(r"[^\w\u0600-\u06FF]", "", w)
    if not w: return ""
    for a, b in [
        ("tch", "sh"), ("sch", "sh"), ("tio", "sh"), ("sio", "sh"),
        ("eau", "o"), ("eux", "u"), ("oeu", "u"),
        ("igh", "i"), ("ough", "o"), ("augh", "a"),
        ("ck", "k"), ("kk", "k"), ("cc", "k"), ("qu", "k"),
        ("ph", "f"), ("ff", "f"), ("pf", "f"),
        ("gh", "g"), ("gg", "g"), ("gu", "g"),
        ("th", "t"), ("tt", "t"), ("dt", "t"),
        ("wh", "w"), ("wr", "r"), ("kn", "n"), ("gn", "n"), ("pn", "n"),
        ("mb", "m"), ("mn", "n"), ("ng", "n"),
        ("dg", "j"), ("dj", "j"), ("zh", "j"), ("ge", "j"), ("gi", "j"),
        ("sh", "sh"), ("ch", "sh"), ("x", "ks"),
        ("oo", "u"), ("ou", "u"), ("ow", "u"), ("ue", "u"), ("ew", "u"),
        ("ee", "i"), ("ie", "i"), ("ea", "i"), ("ei", "i"), ("eo", "i"),
        ("ai", "e"), ("ay", "e"), ("ey", "e"), ("ae", "e"),
        ("oa", "o"), ("oe", "o"), ("oi", "o"), ("oy", "o"),
        ("au", "o"), ("aw", "o"), ("ao", "o"),
        ("ya", "ia"), ("yo", "io"), ("yu", "iu"),
    ]:
        w = w.replace(a, b)
    single = {"y": "i", "c": "k", "q": "k", "z": "s", "v": "f", "o": "u", "w": "v"}
    w = "".join(single.get(ch, ch) for ch in w)
    return re.sub(r"(.)\1+", r"\1", w)

def allowed_from_str(s):
    ids = set()
    for p in (s or "").split(","):
        p = p.strip()
        if not p: continue
        try: ids.add(int(p))
        except ValueError: pass
    return ids

def user_allowed(user_id, enc):
    return user_id in allowed_from_str(enc)

# ========================= Keywords =========================
INTENT_KEYWORDS = [
    "ابحث", "بحث", "جيب", "هات", "ابغى", "أبغى", "ابغا", "أبغا",
    "ابغي", "أبغي", "ابي", "أبي", "اريد", "أريد", "عايز", "عاوز",
    "بدي", "بده", "احتاج", "أحتاج", "محتاج", "وريني", "ورني", "فرجني",
    "أرني", "ارني", "دور", "عطني", "أعطني", "اعطني", "اشتي", "أشتي",
    "اطلب", "أطلب", "طلب", "ودي", "أودي",
    "ملصقات", "ملصق", "ستيكر", "ستيكرات", "ستيكرز", "استيكر", "استيكرات",
    "حزمة", "حزم", "حزمه", "باقة", "باقه",
    "عندكم", "عندك", "فيه حزم", "فيه ملصقات", "هل عندكم", "هل فيه",
    "search", "find", "give me", "gimme", "send me", "show me",
    "i want", "i need", "i'm looking for", "im looking for",
    "looking for", "any stickers", "any packs",
    "sticker", "stickers", "pack", "packs", "do you have", "you have",
    "can i get", "can i have", "got any",
]

QUIET_KEYWORDS = [
    "اسكت", "اسكتي", "اسكتوا", "سكت", "سكوت", "هدي", "اهدأ", "اهدا", "اهدى",
    "خليك ساكت", "خلك ساكت", "خليك هادي", "صمت", "صه", "ششش", "شش",
    "silence", "shut up", "shutup", "stfu", "quiet", "be quiet", "stop talking",
]

TELL_OWNER_KEYWORDS = [
    "قل للمالك", "قول للمالك", "قولي للمالك", "قولوا للمالك",
    "ارسل للمالك", "أرسل للمالك", "ابعث للمالك",
    "بلغ المالك", "بلغه", "خبر المالك", "خبره",
    "اخبر المالك", "أخبر المالك", "رسالة للمالك", "رساله للمالك",
    "tell the owner", "tell owner", "tell admin", "tell the admin",
    "message the owner", "message owner", "message admin",
]

RANDOM_KEYWORDS = [
    "عشوائي", "عشوائيه", "عشوائية", "راندوم", "حظ",
    "random", "rand", "surprise me", "any random", "surprise",
]

def has_intent_keyword(text: str) -> bool:
    if not text: return False
    t = text.lower().strip()
    if len(t) > 300: return False
    for kw in INTENT_KEYWORDS:
        if kw in t: return True
    return False

def is_quiet_request(text: str) -> bool:
    if not text: return False
    t = text.lower().strip()
    if len(t) > 40: return False
    for kw in QUIET_KEYWORDS:
        if kw in t: return True
    return False

def is_wake_request(text: str) -> bool:
    if not text: return False
    t = text.lower().strip()
    for w in WAKE_WORDS:
        if w in t: return True
    return False

def extract_owner_message(text: str) -> str:
    if not text: return ""
    t = text
    for kw in TELL_OWNER_KEYWORDS:
        idx = t.lower().find(kw.lower())
        if idx >= 0:
            rest = t[idx + len(kw):].strip()
            rest = re.sub(r"^[:\-–—،,]\s*", "", rest)
            rest = re.sub(r"^(إنه|انه|إن|ان|أن|يقول|تقول)\s+", "", rest)
            return rest.strip()
    return ""

def sanitize_ai_reply(reply: str) -> str:
    if not reply: return reply
    bad_patterns = [
        r"@Stickers\b", r"@StickerBot\b", r"@stickers\b",
        r"بوت الملصقات", r"اذهب إلى بوت", r"افتح بوت",
        r"افتح تيليجرام", r"اذهب إلى تيليجرام",
        r"ستيكرز بوت", r"بوت ستيكرز",
    ]
    for pat in bad_patterns:
        reply = re.sub(pat, "", reply, flags=re.IGNORECASE)
    reply = re.sub(r"\n{3,}", "\n\n", reply)
    return reply.strip()

# ========================= Texts =========================
TEXTS = {
    "ar": {
        "welcome": (
            "╭─────────────────────╮\n"
            "│  ▸ <b>أهلاً {user}</b>\n"
            "│  ▤ <b>في بوت أرشيف الملصقات</b>\n"
            "╰─────────────────────╯\n\n"
            "⌕ <b>البحث بالأمر:</b>\n"
            "  ▸ <code>/search &lt;كلمة&gt;</code>\n\n"
            "↗ <b>البحث المضمن:</b>\n"
            "  ▸ <code>@{bot} &lt;كلمة&gt;</code>\n\n"
            "◉ <b>قناتنا:</b> <a href=\"https://t.me/AhmShY\">@Ahmshy</a>"
        ),
        "group_welcome": (
            "▸ <b>بوت أرشيف الملصقات</b>\n"
            "⌕ <code>/search &lt;كلمة&gt;</code>\n"
            "↗ <code>@{bot} &lt;كلمة&gt;</code>\n"
            "◉ @Ahmshy"
        ),
        "lang_set": "✓ تم تعيين اللغة العربية.",
        "banned": "⊘ أنت محظور من استخدام هذا البوت.",
        "unknown_cmd": "⚠ <b>أمر غير معروف.</b>\n\n⌕ <code>/search &lt;كلمة&gt;</code>\n↗ <code>@{bot} &lt;كلمة&gt;</code>",
        "not_your_button_msg": "🔒 هذا الزر مخصص للأشخاص الذين شاركوا في هذا البحث\n\n▸ يمكنك البحث بنفسك عبر:\n  ⌕ /search <الاسم>",
        "smart_reply_default": (
            "╭─────────────────────╮\n│  ▸ <b>مرحباً بك</b>\n╰─────────────────────╯\n\n"
            "💡 لم أفهم طلبك بالضبط، لكن يمكنني مساعدتك!\n\n"
            "⌕ <b>للبحث عن ملصقات شخصية معينة:</b>\n"
            "  ▸ اكتب <code>/search</code> ثم اسم الشخصية بالإنجليزية\n"
            "  ▸ أو في أي محادثة: <code>@{bot} اسم الشخصية</code>\n\n"
            "📩 <b>لم تجد ما تبحث عنه؟</b>\n  ▸ أرسل طلبك للمالك وسنضيفه قريباً!"
        ),
        "smart_reply_search": (
            "╭─────────────────────╮\n│  ⌕ <b>تبحث عن ملصقات؟</b>\n╰─────────────────────╯\n\n"
            "  ▸ اكتب <code>/search {word}</code>\n  ▸ أو اضغط الزر أدناه للبحث الآن\n\n"
            "💡 الأفضل استخدام الاسم بالإنجليزية."
        ),
        "smart_reply_not_found": (
            "╭─────────────────────╮\n│  ⚠ <b>لم أجد هذه الملصقات</b>\n╰─────────────────────╯\n\n"
            "  ▸ يمكنك إرسال طلبك للمالك وسنضيفه قريباً ✦\n  ▸ أو جرّب كتابة الاسم بطريقة مختلفة."
        ),
        "smart_search_btn": "⌕ ابحث عن {word}",
        "only_private": "هذا الزر يعمل في المحادثة الخاصة فقط.",
        "button_not_for_you": "⚠ هذا الزر ليس لك.",
        "main_menu": "⌂ القائمة الرئيسية",
        "view_packs": "▤ عرض الحزم",
        "commands": "≡ الأوامر",
        "statistics": "▦ الإحصائيات",
        "request_pack": "✉ طلب حزمة",
        "change_lang_btn": "◐ اللغة",
        "owner_contact": "☎ المالك",
        "channel_link": "◉ القناة",
        "help_btn": "ⓘ شرح الاستخدام",
        "change_lang": "◐ <b>اختر لغتك / Choose your language</b>",
        "easy_search_prompt": (
            "╭─────────────────────╮\n│  ⌕ <b>البحث السهل</b>\n╰─────────────────────╯\n\n"
            "  ✎ اكتب اسم <b>شخصية</b> أو <b>عمل</b> بالإنجليزية\n\n"
            "  💡 أمثلة:\n    ▸ <code>Naruto</code>\n    ▸ <code>Gojo</code>\n    ▸ <code>One Piece</code>"
        ),
        "new_packs_btn": "✦ آخر الحزم المضافة",
        "random_pack_btn": "🎲 حزمة عشوائية",
        "random_again_btn": "🎲 حزمة عشوائية أخرى",
        "no_packs_yet": "⚠ لا توجد حزم بعد.",
        "backup_btn": "⤓ نسخة احتياطية",
        "video_manage_btn": "▶ فيديو الشرح: {status}",
        "forwarding_btn": "↪ التوجيه: {status}",
        "premium_packs_btn": "★ حزم المميزة",
        "regular_packs_btn": "▪ حزم عادية",
        "save_btn": "✓ حفظ",
        "rename_btn": "✎ إعادة تسمية",
        "ignore_btn": "✕ تجاهل",
        "report_delete_btn": "⌫ حذف",
        "report_ignore_btn": "✕ تجاهل",
        "video_delete_btn": "⌫ حذف الفيديو",
        "request_again_btn": "✉ طلب حزمة أخرى",
        "channel_btn": "◉ قناتنا الأساسية",
        "resend_request_now": "✉ إعادة إرسال الطلب",
        "subscribe_channel": "◉ اشترك في قناتنا",
        "close_menu_btn": "✕ إغلاق القائمة",
        "request_pack_btn": "✉ طلب الحزمة",
        "easy_search_btn": "⌕ البحث السهل",
        "inline_search_btn": "⌕ البحث المضمن",
        "most_visited_btn": "▦ الأكثر زيارة",
        "visited_header": "▦ <b>الحزم الأكثر زيارة</b> ({count})",
        "no_visited_packs": "⚠ لا توجد حزم تم زيارتها بعد.",
        "back_to_group_btn": "⌂ العودة إلى المجموعة",
        "open_pack_btn": "↗ اضغط لإضافة الحزمة",
        "open_premium_pack_btn": "↗ اضغط لفتح الحزمة",
        "show_banned_btn": "⊘ المحظورون",
        "unban_btn": "◇ فك الحظر",
        "more_packs_btn": "✦ مزيد من الحزم ({count})",
        "back_to_results_btn": "◂ العودة لنتائج البحث",
        "similar_results": (
            "╭─────────────────────╮\n│  ⌕ <b>حزم مشابهة لـ:</b>\n"
            "│  <code>{query}</code>\n│  ▪ <b>العدد:</b> {count}\n╰─────────────────────╯"
        ),
        "ask_request_pack": "✉ <b>اكتب اسم الحزمة أو وصفها:</b>",
        "request_received_pending": (
            "╭─────────────────────╮\n│  ✓ <b>تم إرسال طلبك للإدارة</b>\n╰─────────────────────╯\n\n"
            "  ◷ يرجى الانتظار حتى يتم الرد عليك.\n  ▸ يسعدنا خدمتك ✿"
        ),
        "request_looking_btn": "⌕ هل تبحث عن حزمة معينة؟",
        "request_ask_name_now": (
            "╭─────────────────────╮\n│  ⌕ <b>أرسل لي الاسم الآن</b>\n╰─────────────────────╯\n\n"
            "  ✎ مثال: <code>Naruto</code>\n  ✎ مثال: <code>Gojo Satoru</code>\n\n⚠ يجب أن يكون بالإنجليزية."
        ),
        "request_notification": (
            "╭─────────────────────╮\n│  ✉ <b>طلب حزمة جديد</b>\n╰─────────────────────╯\n\n"
            "  ◎ <b>من:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>\n"
            "  ✎ <b>الطلب:</b> {request}\n\n◂ <i>رد على هذه الرسالة لتوصيل الرد للطالب</i>"
        ),
        "request_delivered_to_owner": "✓ تم إرسال الطلب للمستخدم.",
        "request_delivered_to_user_msg": (
            "╭─────────────────────╮\n│  ✓ <b>تم تنفيذ طلبك!</b>\n╰─────────────────────╯\n\n"
            "  ❀ نتمنى أن ينال إعجابك\n  ✿ يسعدنا دعمك بالانضمام لقناتنا"
        ),
        "request_support_channel_btn": "❀ ادعمنا بالانضمام للقناة",
        "stats": (
            "╭─────────────────────╮\n│  ▦ <b>الإحصائيات</b>\n╰─────────────────────╯\n\n"
            "  ▪ <b>الحزم:</b> <code>{packs}</code>\n  ★ <b>البريميوم:</b> <code>{premium}</code>\n"
            "  ⚇ <b>المستخدمون:</b> <code>{users}</code>\n  ⚙ <b>المشرفون:</b> <code>{admins}</code>\n"
            "  ⊘ <b>المحظورون:</b> <code>{banned}</code>\n  ⌕ <b>عمليات البحث:</b> <code>{searches}</code>\n"
            "  ♛ <b>الأكثر بحثاً:</b> <code>{top}</code>"
        ),
        "admin_commands": (
            "╭─────────────────────╮\n│  ≡ <b>قائمة الأوامر</b>\n╰─────────────────────╯\n\n"
            "◆ <b>أوامر المشرفين والمالك</b>\n"
            "  ▸ <code>/search &lt;كلمة&gt;</code>\n  ▸ <code>/add</code>\n  ▸ <code>/addpremium</code>\n"
            "  ▸ <code>/rename</code>\n  ▸ <code>/del</code>\n  ▸ <code>/scan</code>\n"
            "  ▸ <code>حظر @username</code>\n  ▸ <code>رفع الحظر @username</code>\n"
            "  ▸ <code>/broadcast</code>\n  ▸ <code>/backup</code>\n  ▸ <code>/setvideo</code>\n  ▸ <code>/delvideo</code>\n\n"
            "⚙ <b>إعدادات المالك (من الأزرار):</b>\n"
            "  ▸ كلمة التنبيه / رابط المجموعة / رابط القناة\n"
            "  ▸ قناة الاشتراك الإجباري / تفعيل الاشتراك"
        ),
        "pack_added": "✓ <b>تمت الإضافة:</b> {name}",
        "pack_added_simple": "✓ <b>تمت الإضافة:</b> {name}",
        "enter_name": "⚠ <b>اكتب اسماً صالحاً للحزمة:</b>",
        "new_pack_detected": (
            "╭─────────────────────╮\n│  ✦ <b>حزمة جديدة</b>\n╰─────────────────────╯\n\n"
            "  ◎ <b>من:</b> [{user}](tg://user?id={uid})\n  ▪ <b>الاسم:</b> `{src}`\n  ✎ <b>المفلتر:</b> `{filtered}`"
        ),
        "already_saved": "⚠ محفوظة سابقاً.",
        "needs_name": "⚠ بحاجة لاسم مخصص. اكتبه الآن:",
        "saved": "✓ تم الحفظ: `{name}`",
        "error": "✕ خطأ.",
        "type_new_name": "✎ اكتب الاسم الجديد الآن:",
        "ignored": "✕ تم التجاهل.",
        "reply_to_sticker_add": "⚠ رد على ملصق لإضافته.",
        "not_from_pack": "⚠ هذا الملصق ليس من حزمة.",
        "already_exists": "⚠ هذه الحزمة موجودة بالفعل.",
        "invalid_name": "⚠ الاسم غير صالح.",
        "error_occurred": "✕ خطأ: {err}",
        "reply_to_sticker_del": "⚠ رد على ملصق للحذف.",
        "not_found": "⚠ الحزمة غير موجودة.",
        "pack_not_found_short": "⚠ الحزمة غير موجودة.",
        "deleted": "✓ تم الحذف: <code>{name}</code>",
        "deleted_short": "✓ تم الحذف!",
        "reply_to_sticker_rename": "⚠ <b>رد على ملصق أو رسالة تحتوي رابط</b>\nثم اكتب: <code>/rename الاسم الجديد</code>",
        "usage_rename": "⚠ الاستخدام: <code>/rename &lt;الاسم&gt;</code>",
        "enter_new_name": "✎ <b>أرسل الاسم الجديد:</b>\n▪ <code>{set_name}</code>",
        "no_results": "✕ لا توجد نتائج لـ <code>{query}</code>.",
        "search_results": (
            "╭─────────────────────╮\n│  ⌕ <b>نتائج البحث عن:</b>\n│  <code>{query}</code>\n"
            "│  ▪ <b>عدد الحزم:</b> {count}\n╰─────────────────────╯"
        ),
        "enter_search_term": "⚠ اكتب كلمة للبحث.\n▸ مثال: <code>/search anime</code>",
        "did_you_mean": "هل تقصد: {word}؟",
        "no_results_short": "لا نتائج",
        "alpha_index_header": "▤ <b>اختر الحرف الأول للحزمة:</b>",
        "alpha_filter": "▤ <b>الحزم التي تبدأ بحرف {letter}</b> ({count})",
        "alpha_unknown": "▤ <b>الحزم غير اللاتينية</b> ({count})",
        "no_packs_letter": "✕ لا توجد حزم تبدأ بـ {letter}",
        "recent_packs_header": "✦ <b>آخر الحزم المضافة</b>",
        "premium_packs_header": "★ <b>حزم المميزة</b> ({count})",
        "regular_packs_header": "▪ <b>الحزم العادية</b> ({count})",
        "no_recent_packs": "⚠ لا توجد حزم مضافة مؤخراً.",
        "no_premium_packs": "⚠ لا توجد حزم مميزة بعد.",
        "no_regular_packs": "⚠ لا توجد حزم عادية بعد.",
        "cmd_from_user": "↪ <b>أمر من:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>\n  ▸ <code>{cmd}</code>",
        "msg_from_user": "↪ <b>رسالة من:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>",
        "new_user_notification": (
            "╭─────────────────────╮\n│  ✦ <b>مستخدم جديد</b>\n╰─────────────────────╯\n\n"
            "  ◎ <b>الاسم:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>\n"
            "  ◷ <b>التاريخ:</b> {date}\n  ⚇ <b>الإجمالي:</b> <code>{total}</code>"
        ),
        "inactivity_reminder": (
            "╭─────────────────────╮\n│  ❀ <b>اشتقنا لك!</b>\n╰─────────────────────╯\n\n"
            "  ▸ مر وقت طويل منذ آخر زيارة لك\n  ▸ لدينا حزم جديدة تنتظرك ✦\n\n  ⌂ اضغط /start لتصفح الجديد"
        ),
        "cant_ban_owner": "⚠ لا يمكن حظر المالك.",
        "user_banned": "✓ تم حظر {user}.",
        "already_banned": "⚠ المستخدم محظور بالفعل.",
        "user_unbanned": "✓ تم رفع الحظر عن {user}.",
        "not_banned": "⚠ المستخدم غير محظور.",
        "not_banned_short": "⚠ غير محظور.",
        "unbanned_msg": "✓ تم فك الحظر!",
        "banned_list_header": "⊘ <b>قائمة المحظورين</b>",
        "no_banned_users": "✓ لا يوجد محظورون.",
        "banned_user_item": "  ◎ {user}  <code>{uid}</code>",
        "user_not_found": "⚠ لم يتم العثور على المستخدم.",
        "reply_broadcast": "⚠ رد على الرسالة المراد بثها.",
        "no_users": "⚠ لا يوجد مستخدمون للبث.",
        "broadcast_done": "✓ <b>تم البث!</b>\n↪ التسليم لـ <code>{count}</code>",
        "admin_reply_sent": "✓ تم إرسال ردك.",
        "admin_reply_fail": "⚠ تعذر إرسال الرد.",
        "forwarding_toggled": "✓ تم تحديث التوجيه",
        "forwarding_on": "◉ مفعّل",
        "forwarding_off": "◌ متوقف",
        "admin_reply_header": "↪ <b>رد من الإدارة:</b>",
        "request_sent": "✓ تم إرسال طلبك إلى المالك.",
        "request_from_owner_msg": "╭─────────────────────╮\n│  ✉ <b>طلب الحزمة</b>\n╰─────────────────────╯\n\nاكتب اسم الحزمة أو وصفها وسيُرسل للمالك مباشرة.",
        "request_executed": "╭─────────────────────╮\n│  ✓ <b>تم تنفيذ طلبك</b>\n╰─────────────────────╯\n\n  ❀ نتمنى أن تنال الحزمة إعجابك\n  ✿ يسعدنا خدمتك في أي وقت",
        "no_saved_request": "⚠ لا يوجد طلب محفوظ",
        "report_success": "⚠ تم الإبلاغ بنجاح، سيتم المراجعة.",
        "report_notification": (
            "╭─────────────────────╮\n│  ⚠ <b>بلاغ عن حزمة</b>\n╰─────────────────────╯\n\n"
            "  ◎ <b>من:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>\n"
            "  ▪ <b>الحزمة:</b> {pack_name}\n  ↗ <b>الرابط:</b> <a href=\"{pack_url}\">فتح</a>\n"
            "  ✎ <b>السبب:</b> {reason}"
        ),
        "report_handled": "✓ تم التعامل مع البلاغ.",
        "report_ignored": "✕ تم تجاهل البلاغ.",
        "ask_report_reason": "✎ <b>اكتب سبب البلاغ:</b>",
        "ask_report_reason_short": "⚠ الرجاء كتابة سبب البلاغ.",
        "help_text": (
            "╭─────────────────────╮\n│  ⓘ <b>شرح استخدام البوت</b>\n╰─────────────────────╯\n\n"
            "⌕ <b>البحث عن الملصقات:</b>\n  ▸ <code>/search كلمة</code>\n  ▸ <code>@البوت كلمة</code>\n"
            "  ▸ زر <b>«▤ عرض الحزم»</b>\n\n▤ <b>عرض الحزم:</b>\n  ▸ اختر الحرف الأول\n  ▸ اضغط على الحزمة\n\n"
            "★ <b>الحزم البريميوم:</b>\n  ▸ تحتاج تيليجرام بريميوم\n\n✉ <b>طلب حزمة:</b>\n  ▸ زر <b>«✉ طلب حزمة»</b>\n\n"
            "⚠ <b>الإبلاغ:</b>\n  ▸ زر ⚠ بجانب كل حزمة\n\n◐ <b>تغيير اللغة:</b>\n  ▸ زر <b>«◐ اللغة»</b>\n\n"
            "◉ <b>قناتنا:</b> <a href=\"https://t.me/AhmShY\">@Ahmshy</a>\n\nⓘ <b>نصيحة:</b> استخدم الوضع المضمن للوصول السريع!"
        ),
        "set_video_success": "✓ تم حفظ فيديو الشرح.",
        "set_video_reply": "⚠ رد على فيديو ثم اكتب <code>/setvideo</code>",
        "del_video_success": "✓ تم حذف فيديو الشرح.",
        "del_video_not_found": "⚠ لا يوجد فيديو شرح محفوظ.",
        "video_manage_info": "▶ <b>إدارة فيديو الشرح</b>\n\n  ▪ <b>الحالة:</b> {status}\n\n✎ <b>لإضافة فيديو:</b>\n  ▸ رد على الفيديو بـ <code>/setvideo</code>\n\n✎ <b>لحذف الفيديو:</b>\n  ▸ استخدم <code>/delvideo</code>",
        "video_manage_info_deleted": "▶ <b>إدارة فيديو الشرح</b>\n\n  ▪ <b>الحالة:</b> ✕ غير مضاف\n\n✎ <b>لإضافة فيديو:</b>\n  ▸ رد على الفيديو بـ <code>/setvideo</code>",
        "video_status_added": "✓ مضاف",
        "video_status_not_added": "✕ غير مضاف",
        "backup_creating": "◷ جاري إنشاء النسخة...",
        "backup_sent": "✓ تم إرسال النسخة!",
        "backup_failed": "✕ فشل إنشاء النسخة",
        "scan_started": "⌕ بدء فحص الحزم...",
        "scan_complete": "✓ <b>تم الفحص!</b>\n\n  ⌫ حُذفت {deleted}\n  ✎ حُدّثت {updated}\n  ▪ بقيت {unchanged}",
        "new_packs_notification": "╭─────────────────────╮\n│  ✦ <b>حزم جديدة</b>\n╰─────────────────────╯\n\n  ▸ اضغط /start لرؤيتها\n  ◉ <a href=\"https://t.me/AhmShY\">قناتنا</a>",
        "inline_all_packs": "▪ جميع الحزم ({count})",
        "inline_pack_item": "{num}. {title}",
        "inline_all_packs_title": "▪ جميع الحزم المطابقة:",
        "inline_pack_label": "▪ <b>حزمة ملصقات:</b>",
        "inline_channel_follow": "◉ تابع قناتنا:",
        "inline_pack_count_desc": "عدد الحزم: {count}",
        "inline_pack_link_desc": "اضغط لفتحه في البوت",
        "inline_no_results_title": "✕ لا توجد نتائج",
        "inline_no_results_msg": "✕ لا توجد نتائج لـ: <code>{query}</code>",
        "inline_no_results_desc": "لا توجد نتائج مطابقة",
        "inline_msg_header": "⌕ نتائج البحث",
        "inline_msg_query_label": "✎ الاستعلام:",
        "inline_msg_count_label": "▪ عدد الحزم:",
        "inline_msg_hint": "▸ اضغط على اسم الحزمة لفتحها",
        "inline_msg_channel_label": "◉ قناتنا:",
        "owner_settings_btn": "⚙ الإعدادات",
        "owner_settings_header": (
            "╭─────────────────────╮\n"
            "│  ⚙ <b>إعدادات المالك</b>\n"
            "╰─────────────────────╯\n\n"
            "  ▸ <b>كلمة التنبيه:</b> <code>{trigger}</code>\n"
            "  ▸ <b>رابط المجموعة:</b> {group}\n"
            "  ▸ <b>رابط القناة:</b> {channel}\n"
            "  ▸ <b>قناة الاشتراك الإجباري:</b> {sub}\n"
            "  ▸ <b>الاشتراك الإجباري:</b> {sub_status}"
        ),
        "set_trigger_btn": "✎ كلمة التنبيه",
        "set_group_btn": "✎ رابط المجموعة",
        "set_channel_btn": "✎ رابط القناة",
        "set_sub_btn": "✎ قناة الاشتراك الإجباري",
        "toggle_forcesub_btn": "⚙ الاشتراك الإجباري: {status}",
        "force_sub_on": "◉ مفعّل",
        "force_sub_off": "◌ متوقف",
        "ask_trigger_name": "✎ <b>أرسل كلمة التنبيه الجديدة</b>\n\n▸ مثال: <code>solo</code>\n▸ المستخدم سيكتب: <code>solo كيف حالك</code>\n\n▸ أرسل <code>del</code> لإرجاع الافتراضي.",
        "ask_group_link": "✎ <b>أرسل رابط المجموعة</b>\n\n▸ مثال: <code>https://t.me/mygroup</code>\n▸ أرسل <code>del</code> للحذف.",
        "ask_channel_link": "✎ <b>أرسل رابط القناة</b>\n\n▸ مثال: <code>https://t.me/mychannel</code>\n▸ أرسل <code>del</code> للحذف.",
        "ask_sub_channel": "✎ <b>أرسل قناة الاشتراك الإجباري</b>\n\n▸ مثال: <code>@mychannel</code> أو رابط\n▸ أرسل <code>del</code> لإلغاء الاشتراك الإجباري.\n\n⚠ تأكد أن البوت مشرف في القناة.",
        "setting_saved": "✓ تم الحفظ.",
        "setting_deleted": "✓ تم الحذف.",
        "invalid_setting": "⚠ قيمة غير صالحة.",
        "force_sub_enabled_msg": "✓ تم تفعيل الاشتراك الإجباري.",
        "force_sub_disabled_msg": "✓ تم إيقاف الاشتراك الإجباري.",
        "need_sub_channel_first": "⚠ حدد قناة الاشتراك أولاً.",
        "you_are_quiet": "🤫",
        "image_failed": "⚠ تعذر تحليل الصورة، حاول مرة أخرى.",
        "wake_reply": "🎤 تفضل، أنا أسمعك!",
        "owner_request_pack_msg": "⚠ أنت المالك! ضيف الحزم بنفسك عبر /add أو /addpremium",
        "categories_header": "╭─────────────────────╮\n│  🗂 <b>التصنيفات</b>\n╰─────────────────────╯\n\n▸ اختر تصنيفاً لعرض حزمه:",
        "category_works_header": "╭─────────────────────╮\n│  {label}\n│  ▪ <b>الأعمال:</b> {count}\n╰─────────────────────╯\n\n▤ <b>اختر عملاً:</b>",
        "category_packs_header": "╭─────────────────────╮\n│  {label}\n│  ▪ <b>العدد:</b> {count}\n╰─────────────────────╯",
        "work_packs_header": "╭─────────────────────╮\n│  📺 <b>{work}</b>\n│  ▪ <b>عدد الشخصيات:</b> {count}\n╰─────────────────────╯",
        "no_packs_in_category": "⚠ لا توجد حزم في هذا التصنيف بعد.",
        "no_works_in_category": "⚠ لا توجد أعمال في هذا التصنيف بعد.",
        "choose_category_for_pack": "🗂 <b>اختر تصنيف الحزمة:</b>\n▪ <code>{pack}</code>",
        "category_set": "✓ التصنيف: {label}",
        "ask_setcat_usage": "⚠ <b>الاستخدام:</b>\n<code>/setcat &lt;التصنيف&gt;</code> رداً على ملصق\n\n▸ المتاح: <code>anime, manga, manhwa, movies, games, cartoon, memes, sports, animals, celebrities, flags, emoji, other</code>",
        "cat_back_cats": "◂ التصنيفات",
        "cat_back_works": "◂ الأعمال",
        "cat_all_packs": "▦ عرض الكل",
        "cat_page_prev": "◂ السابق",
        "cat_page_next": "التالي ▸",
        "cat_page_info": "صفحة {current} من {total}",
        "owner_panel_header": "╭─────────────────────╮\n│  ⚙ <b>لوحة تحكم المالك</b>\n╰─────────────────────╯",
        "op_packs": "🖼 إدارة الحزم",
        "op_cats": "🗂 التصنيفات",
        "op_ai": "🤖 الذكاء الاصطناعي",
        "op_settings": "⚙ إعدادات البوت",
        "op_channels": "📢 إدارة القنوات",
        "op_admins": "👥 إدارة الأدمن",
        "op_stats_adv": "▦ إحصائيات متقدمة",
        "op_stats": "▦ الإحصائيات",
        "op_banned": "⊘ المحظورون",
        "op_backup": "⤓ نسخة احتياطية",
        "op_broadcast": "📢 بث جماعي",
        "op_back": "◂ رجوع",
        "op_packs_header": "╭─────────────────────╮\n│  🖼 <b>إدارة الحزم</b>\n╰─────────────────────╯\n\n▸ اختر العملية:",
        "op_cats_header": "╭─────────────────────╮\n│  🗂 <b>إدارة التصنيفات</b>\n╰─────────────────────╯\n\n▸ اختر العملية:",
        "op_ai_header": "╭─────────────────────╮\n│  🤖 <b>إدارة الذكاء الاصطناعي</b>\n╰─────────────────────╯\n\n▸ اختر:",
        "op_settings_header": "╭─────────────────────╮\n│  ⚙ <b>إعدادات البوت</b>\n╰─────────────────────╯\n\n▸ اختر:",
        "op_channels_header": "╭─────────────────────╮\n│  📢 <b>إدارة القنوات</b>\n╰─────────────────────╯",
        "op_admins_header": "╭─────────────────────╮\n│  👥 <b>إدارة الأدمن</b>\n╰─────────────────────╯",
        "ask_add_admin": "➕ <b>إضافة أدمن</b>\n\n▸ أرسل الآن:\n  • <code>@username</code>\n  • أو ID رقمي\n\nأو أرسل <code>del</code> للإلغاء.",
        "admin_added": "✓ تم رفع <b>{name}</b> إلى أدمن.\n  # <code>{uid}</code>",
        "admin_removed": "✓ تم إزالة <b>{name}</b> من الأدمن.",
        "admin_already": "⚠ هذا المستخدم أدمن مسبقاً.",
        "owner_admin": "⚠ هذا المالك.",
        "no_admins": "▸ لا يوجد أدمن حالياً.",
        "ai_classifying": "🤖 جاري التصنيف... ▰▰▰▱▱▱▱▱▱▱",
        "ai_classify_fail": "⚠ فشل التصنيف.",
        "ai_classify_done": "✓ <b>تم التصنيف</b>\n\n{label}\n📺 <b>العمل:</b> {work}\n👤 <b>الشخصية:</b> {character}",
        "ai_backfill_started": "🤖 <b>جاري تصنيف الحزم...</b>\n▸ العدد: <code>{count}</code>",
        "ai_backfill_progress": "🤖 {done}/{total}\n✓ تم: <b>{ok}</b>",
        "ai_backfill_done": "✓ <b>تم التصنيف!</b>\n\n▪ الإجمالي: <code>{total}</code>\n✓ صُنّفت: <b>{ok}</b>",
        "ai_backfill_none": "✓ كل الحزم مصنّفة مسبقاً.",
        "ai_classify_btn": "🤖 صنّف بالـ AI",
        "ai_reclassify_btn": "🔄 إعادة تصنيف",
        "reclassify_done": "✓ <b>تم التصنيف</b>\n\n{label}\n📺 <b>العمل:</b> {work}\n👤 <b>الشخصية:</b> {character}",
        "suggested_name_changed": "✎ <b>الاسم:</b>\n  ▪ قبل: <code>{old}</code>\n  ▪ بعد: <code>{new}</code>",
        "op_backfill_btn": "🤖 تصنيف كل الحزم ({count})",
        "op_cats_view": "🗂 عرض التصنيفات",
        "op_cats_setcat": "✎ ضبط تصنيف (رد على ملصق)",
        "op_cats_setwork": "📺 ضبط عمل (رد على ملصق)",
        "op_cats_reclassify": "🔄 إعادة تصنيف AI (رد على ملصق)",
        "ai_menu_status": "الحالة: {status}",
        "ai_menu_on": "✓ تشغيل AI",
        "ai_menu_off": "✕ إيقاف AI",
        "ai_menu_key": "✎ ضبط المفتاح",
        "ai_menu_model": "✎ تغيير الموديل",
        "ai_menu_base": "✎ تغيير Base URL",
        "ai_menu_prompt": "✎ تعديل البرومبت",
        "ai_menu_smart": "🤖 تطبيق البرومبت الذكي",
        "ask_ai_key": "🔑 <b>أرسل مفتاح API الآن:</b>\n\n▸ مثال: <code>AIza...</code>",
        "ask_ai_model": "🧠 <b>أرسل اسم الموديل الجديد:</b>",
        "ask_ai_base": "🌐 <b>أرسل Base URL الجديد:</b>",
        "ask_ai_prompt": "📝 <b>أرسل البرومبت الجديد:</b>",
        "op_cats_scan_all": "🔍 فحص كامل للكتالوج بالـ AI",
        "op_cats_scan_others": "🔍 فحص الحزم غير المصنّفة",
        "op_cats_add": "➕ إضافة تصنيف جديد",
        "op_cats_remove": "🗑 حذف تصنيف مخصص",
        "op_cats_bulk_add": "🎯 إضافة حزم لتصنيف",
        "ask_addcat_format": (
            "➕ <b>أرسل التصنيف بهذا الشكل:</b>\n\n"
            "<code>الإيموجي | الاسم بالعربي | الاسم بالإنجليزي</code>\n\n"
            "▸ مثال:\n<code>🎵 | موسيقى | Music</code>"
        ),
        "cat_added": "✓ تم إضافة التصنيف:\n{label}",
        "cat_exists": "⚠ التصنيف موجود مسبقاً.",
        "cat_invalid_format": "⚠ الصيغة غير صحيحة.\nاستخدم: <code>emoji | عربي | English</code>",
        "cat_removed": "✓ تم حذف التصنيف: {label}",
        "no_custom_cats": "⚠ لا توجد تصنيفات مخصصة.",
        "scan_all_started": (
            "🤖 <b>جاري الفحص الشامل للكتالوج...</b>\n"
            "▸ عدد الحزم: <code>{count}</code>\n\n"
            "  {bar}  <code>{done}/{count}</code>\n\n"
            "◷ يرجى الانتظار...\n\n"
            "💡 اضغط /start للإيقاف"
        ),
        "scan_others_started": (
            "🤖 <b>جاري فحص الحزم غير المصنّفة...</b>\n"
            "▸ عدد الحزم: <code>{count}</code>\n\n"
            "  {bar}  <code>{done}/{count}</code>\n\n"
            "◷ يرجى الانتظار...\n\n"
            "💡 اضغط /start للإيقاف"
        ),
        "scan_all_progress": "🤖 <b>جاري الفحص...</b>\n\n  {bar}  <code>{done}/{total}</code>\n  ✓ تم تصنيف: <b>{ok}</b>\n  ✕ فشل: <b>{fail}</b>\n\n💡 اضغط /start للإيقاف",
        "scan_all_done": (
            "╭─────────────────────╮\n│  ✓ <b>تم الفحص الشامل!</b>\n╰─────────────────────╯\n\n"
            "  ▰▰▰▰▰▰▰▰▰▰  <code>{total}/{total}</code>\n\n"
            "  ▪ <b>الإجمالي:</b> <code>{total}</code>\n"
            "  ✓ <b>صُنّفت:</b> <code>{ok}</code>\n"
            "  ✎ <b>أُعيد تسميتها:</b> <code>{renamed}</code>\n"
            "  ✕ <b>فشلت:</b> <code>{fail}</code>"
        ),
        "scan_stopped": "⏹ <b>تم إيقاف التصنيف.</b>\n\n  {bar}  <code>{done}/{total}</code>\n  ✓ تم: <b>{ok}</b>",
        "scan_all_need_ai": "⚠ يحتاج الذكاء الاصطناعي مفعّلاً.",
        "pending_classify_header": "🗂 <b>حزم تحتاج تصنيف</b>\n▪ العدد: <code>{count}</code>",
        "pending_classify_bulk_header": (
            "╭─────────────────────╮\n│  🗂 <b>حزم تحتاج تصنيف</b>\n│  ▪ العدد: <code>{count}</code>\n╰─────────────────────╯\n\n"
            "▸ اختر تصنيفاً لتطبيقه على <b>الكل</b>،\n  أو راجع فرداً فرداً."
        ),
        "pending_classify_one_btn": "📋 مراجعة فردية",
        "pending_classify_bulk_btn": "⚡ تصنيف جماعي",
        "pending_classify_all_set": "✓ تم تصنيف <b>{count}</b> حزمة كـ {label}",
        "pending_classify_none": "✓ لا توجد حزم معلّقة.",
        "notif_pack_classify_ask": (
            "╭─────────────────────╮\n│  🗂 <b>تصنيف حزمة جديدة</b>\n╰─────────────────────╯\n\n"
            "  ▪ <code>{pack}</code>\n\n▸ اختر تصنيفاً:"
        ),
        "notif_skip_btn": "⏭ تخطي",
        "notif_skip_all_btn": "⏭ تخطي الكل",
        "ai_scan_btn_small": "🤖 صنّف هذه",
        "scan_review_btn": "📋 مراجعة المعلّقة ({count})",
        "adv_stats_header": "╭─────────────────────╮\n│  ▦ <b>إحصائيات متقدمة</b>\n╰─────────────────────╯",
        "adv_stats_body": (
            "  📅 <b>اليوم:</b> <code>{day}</code>\n\n"
            "  ⌕ <b>أكثر شخص بحث:</b>\n"
            "    ▸ اليوم: {top_search_day}\n"
            "    ▸ الإجمالي: {top_search_all}\n\n"
            "  ⚇ <b>أكثر استخداماً للبوت:</b>\n"
            "    ▸ اليوم: {top_user_day}\n"
            "    ▸ الإجمالي: {top_user_all}\n\n"
            "  🎲 <b>أكثر من استخدم /random:</b>\n"
            "    ▸ اليوم: {top_rand_day}\n"
            "    ▸ الإجمالي: {top_rand_all}\n\n"
            "  ⌕ <b>إجمالي البحوثات:</b> <code>{total_searches}</code>\n"
            "  🎲 <b>إجمالي الراندوم:</b> <code>{total_rand}</code>"
        ),
        "bulk_cat_choose": "🎯 <b>اختر التصنيف الذي تريد إضافة الحزم إليه:</b>",
        "bulk_cat_ask_packs": (
            "🎯 <b>التصنيف:</b> {label}\n\n"
            "▸ أرسل الآن <b>روابط الحزم</b> أو <b>ردّ على ملصقات</b> من الحزم.\n"
            "▸ يمكنك إرسال أكثر من حزمة (واحدة كل رسالة).\n\n"
            "  ▪ <b>المضاف حالياً:</b> <code>{count}</code>\n\n"
            "▸ اضغط <b>✓ تم</b> عند الانتهاء، أو <b>✕ إلغاء</b>."
        ),
        "bulk_cat_added_one": "✓ تم إضافة الحزمة: <code>{name}</code>\n▪ المجموع: {count}",
        "bulk_cat_failed": "⚠ لم أتعرف على الحزمة. أرسل رابطاً أو رد على ملصق.",
        "bulk_cat_finish": (
            "╭─────────────────────╮\n│  ✓ <b>تم!</b>\n╰─────────────────────╯\n\n"
            "  ▪ <b>التصنيف:</b> {label}\n"
            "  ▪ <b>عدد الحزم المضافة:</b> <code>{count}</code>"
        ),
        "bulk_cat_empty": "⚠ لم تُضف أي حزمة.",
        "bulk_cat_cancelled": "✕ تم الإلغاء.",
        "bulk_done_btn": "✓ تم",
        "bulk_cancel_btn": "✕ إلغاء",
        "cmd_panel": "≡ جميع الأوامر",
        "cmd_panel_header": "≡ <b>جميع الأوامر (أزرار)</b>\n\n▸ اختر الأمر:",
    },
    "en": {
        "welcome": (
            "╭─────────────────────╮\n"
            "│  ▸ <b>Welcome {user}</b>\n"
            "│  ▤ <b>Sticker Archive Bot</b>\n"
            "╰─────────────────────╯\n\n"
            "⌕ <b>Search via Command:</b>\n"
            "  ▸ <code>/search &lt;keyword&gt;</code>\n\n"
            "↗ <b>Inline Search:</b>\n"
            "  ▸ <code>@{bot} &lt;keyword&gt;</code>\n\n"
            "◉ <b>Our Channel:</b> <a href=\"https://t.me/AhmShY\">@Ahmshy</a>"
        ),
        "group_welcome": "▸ <b>Sticker Archive Bot</b>\n⌕ <code>/search &lt;keyword&gt;</code>\n↗ <code>@{bot} &lt;keyword&gt;</code>\n◉ @Ahmshy",
        "lang_set": "✓ Language set to English.",
        "banned": "⊘ You are banned from using this bot.",
        "unknown_cmd": "⚠ <b>Unknown command.</b>\n\n⌕ <code>/search &lt;keyword&gt;</code>\n↗ <code>@{bot} &lt;keyword&gt;</code>",
        "not_your_button_msg": "🔒 This button is for those who joined this search\n\n▸ You can search yourself using:\n  ⌕ /search <name>",
        "smart_reply_default": (
            "╭─────────────────────╮\n│  ▸ <b>Welcome!</b>\n╰─────────────────────╯\n\n"
            "💡 I didn't quite understand, but I can help!\n\n"
            "⌕ <b>To search for a character's stickers:</b>\n  ▸ Type <code>/search</code> then the name in English\n"
            "  ▸ Or in any chat: <code>@{bot} name</code>\n\n📩 <b>Couldn't find what you want?</b>\n  ▸ Send a request and we'll add it soon!"
        ),
        "smart_reply_search": (
            "╭─────────────────────╮\n│  ⌕ <b>Looking for stickers?</b>\n╰─────────────────────╯\n\n"
            "  ▸ Type <code>/search {word}</code>\n  ▸ Or tap the button below to search now\n\n💡 English names work best."
        ),
        "smart_reply_not_found": (
            "╭─────────────────────╮\n│  ⚠ <b>Couldn't find these stickers</b>\n╰─────────────────────╯\n\n"
            "  ▸ Send a request and we'll add it soon ✦\n  ▸ Or try a different spelling."
        ),
        "smart_search_btn": "⌕ Search for {word}",
        "only_private": "This button works only in private chat.",
        "button_not_for_you": "⚠ This button is not for you.",
        "main_menu": "⌂ Main Menu",
        "view_packs": "▤ View Packs",
        "commands": "≡ Commands",
        "statistics": "▦ Statistics",
        "request_pack": "✉ Request Pack",
        "change_lang_btn": "◐ Language",
        "owner_contact": "☎ Owner",
        "channel_link": "◉ Channel",
        "help_btn": "ⓘ How to Use",
        "change_lang": "◐ <b>Choose your language / اختر لغتك</b>",
        "easy_search_prompt": (
            "╭─────────────────────╮\n│  ⌕ <b>Easy Search</b>\n╰─────────────────────╯\n\n"
            "  ✎ Type a <b>character</b> or <b>title</b> in English\n\n"
            "  💡 Examples:\n    ▸ <code>Naruto</code>\n    ▸ <code>Gojo</code>\n    ▸ <code>One Piece</code>"
        ),
        "new_packs_btn": "✦ Recently Added",
        "random_pack_btn": "🎲 Random Pack",
        "random_again_btn": "🎲 Another Random Pack",
        "no_packs_yet": "⚠ No packs yet.",
        "backup_btn": "⤓ Backup",
        "video_manage_btn": "▶ Tutorial Video: {status}",
        "forwarding_btn": "↪ Forwarding: {status}",
        "premium_packs_btn": "★ Premium Packs",
        "regular_packs_btn": "▪ Regular Packs",
        "save_btn": "✓ Save",
        "rename_btn": "✎ Rename",
        "ignore_btn": "✕ Ignore",
        "report_delete_btn": "⌫ Delete",
        "report_ignore_btn": "✕ Ignore",
        "video_delete_btn": "⌫ Delete Video",
        "request_again_btn": "✉ Request Another Pack",
        "channel_btn": "◉ Our Channel",
        "resend_request_now": "✉ Resend Request",
        "subscribe_channel": "◉ Subscribe to our channel",
        "close_menu_btn": "✕ Close Menu",
        "request_pack_btn": "✉ Request Pack",
        "easy_search_btn": "⌕ Easy Search",
        "inline_search_btn": "⌕ Inline Search",
        "most_visited_btn": "▦ Most Visited",
        "visited_header": "▦ <b>Most Visited Packs</b> ({count})",
        "no_visited_packs": "⚠ No visited packs yet.",
        "back_to_group_btn": "⌂ Back to Group",
        "open_pack_btn": "↗ Tap to add the pack",
        "open_premium_pack_btn": "↗ Tap to open the premium pack",
        "show_banned_btn": "⊘ Banned",
        "unban_btn": "◇ Unban",
        "more_packs_btn": "✦ More packs ({count})",
        "back_to_results_btn": "◂ Back to results",
        "similar_results": "╭─────────────────────╮\n│  ⌕ <b>Similar to:</b>\n│  <code>{query}</code>\n│  ▪ <b>Count:</b> {count}\n╰─────────────────────╯",
        "ask_request_pack": "✉ <b>Write the pack name or description:</b>",
        "request_received_pending": (
            "╭─────────────────────╮\n│  ✓ <b>Request sent to admin</b>\n╰─────────────────────╯\n\n"
            "  ◷ Please wait for a reply.\n  ▸ Happy to help ✿"
        ),
        "request_looking_btn": "⌕ Looking for a specific pack?",
        "request_ask_name_now": "╭─────────────────────╮\n│  ⌕ <b>Send the name now</b>\n╰─────────────────────╯\n\n  ✎ Example: <code>Naruto</code>\n  ✎ Example: <code>Gojo Satoru</code>\n\n⚠ Must be in English.",
        "request_notification": (
            "╭─────────────────────╮\n│  ✉ <b>New Pack Request</b>\n╰─────────────────────╯\n\n"
            "  ◎ <b>From:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>\n"
            "  ✎ <b>Request:</b> {request}\n\n◂ <i>Reply to this message to deliver the reply</i>"
        ),
        "request_delivered_to_owner": "✓ Request sent to user.",
        "request_delivered_to_user_msg": "╭─────────────────────╮\n│  ✓ <b>Your request is fulfilled!</b>\n╰─────────────────────╯\n\n  ❀ Hope you enjoy it\n  ✿ Support us by joining our channel",
        "request_support_channel_btn": "❀ Support us on our channel",
        "stats": (
            "╭─────────────────────╮\n│  ▦ <b>Statistics</b>\n╰─────────────────────╯\n\n"
            "  ▪ <b>Packs:</b> <code>{packs}</code>\n  ★ <b>Premium:</b> <code>{premium}</code>\n"
            "  ⚇ <b>Users:</b> <code>{users}</code>\n  ⚙ <b>Admins:</b> <code>{admins}</code>\n"
            "  ⊘ <b>Banned:</b> <code>{banned}</code>\n  ⌕ <b>Searches:</b> <code>{searches}</code>\n"
            "  ♛ <b>Top Query:</b> <code>{top}</code>"
        ),
        "admin_commands": (
            "╭─────────────────────╮\n│  ≡ <b>Command List</b>\n╰─────────────────────╯\n\n"
            "◆ <b>Admin & Owner Commands</b>\n  ▸ <code>/search</code>\n  ▸ <code>/add</code>\n"
            "  ▸ <code>/addpremium</code>\n  ▸ <code>/rename</code>\n  ▸ <code>/del</code>\n"
            "  ▸ <code>/scan</code>\n  ▸ <code>/broadcast</code>\n  ▸ <code>/backup</code>\n"
            "  ▸ <code>/setvideo</code>\n  ▸ <code>/delvideo</code>\n\n"
            "⚙ <b>Owner Settings (via buttons):</b>\n"
            "  ▸ Trigger word / Group link / Channel link\n"
            "  ▸ Force-sub channel / Force-sub toggle"
        ),
        "pack_added": "✓ <b>Added:</b> {name}",
        "pack_added_simple": "✓ <b>Added:</b> {name}",
        "enter_name": "⚠ <b>Type a valid name:</b>",
        "new_pack_detected": "╭─────────────────────╮\n│  ✦ <b>New Pack</b>\n╰─────────────────────╯\n\n  ◎ <b>From:</b> [{user}](tg://user?id={uid})\n  ▪ <b>Name:</b> `{src}`\n  ✎ <b>Filtered:</b> `{filtered}`",
        "already_saved": "⚠ Already saved.",
        "needs_name": "⚠ Needs custom name. Type it now:",
        "saved": "✓ Saved: `{name}`",
        "error": "✕ Error.",
        "type_new_name": "✎ Type the new name:",
        "ignored": "✕ Ignored.",
        "reply_to_sticker_add": "⚠ Reply to a sticker to add it.",
        "not_from_pack": "⚠ Not from a pack.",
        "already_exists": "⚠ Pack already exists.",
        "invalid_name": "⚠ Invalid name.",
        "error_occurred": "✕ Error: {err}",
        "reply_to_sticker_del": "⚠ Reply to a sticker to delete.",
        "not_found": "⚠ Pack not found.",
        "pack_not_found_short": "⚠ Pack not found.",
        "deleted": "✓ Deleted: <code>{name}</code>",
        "deleted_short": "✓ Deleted!",
        "reply_to_sticker_rename": "⚠ <b>Reply to a sticker or link message</b>\nThen type: <code>/rename New Name</code>",
        "usage_rename": "⚠ Usage: <code>/rename &lt;New Name&gt;</code>",
        "enter_new_name": "✎ <b>Send the new name:</b>\n▪ <code>{set_name}</code>",
        "no_results": "✕ No results for <code>{query}</code>.",
        "search_results": "╭─────────────────────╮\n│  ⌕ <b>Search results for:</b>\n│  <code>{query}</code>\n│  ▪ <b>Packs found:</b> {count}\n╰─────────────────────╯",
        "enter_search_term": "⚠ Enter a search term.\n▸ Example: <code>/search anime</code>",
        "did_you_mean": "Did you mean: {word}?",
        "no_results_short": "No results",
        "alpha_index_header": "▤ <b>Choose the first letter:</b>",
        "alpha_filter": "▤ <b>Packs starting with {letter}</b> ({count})",
        "alpha_unknown": "▤ <b>Non-Latin packs</b> ({count})",
        "no_packs_letter": "✕ No packs starting with {letter}",
        "recent_packs_header": "✦ <b>Recently Added</b>",
        "premium_packs_header": "★ <b>Premium Packs</b> ({count})",
        "regular_packs_header": "▪ <b>Regular Packs</b> ({count})",
        "no_recent_packs": "⚠ No packs added recently.",
        "no_premium_packs": "⚠ No premium packs yet.",
        "no_regular_packs": "⚠ No regular packs yet.",
        "cmd_from_user": "↪ <b>Command from:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>\n  ▸ <code>{cmd}</code>",
        "msg_from_user": "↪ <b>Message from:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>",
        "new_user_notification": (
            "╭─────────────────────╮\n│  ✦ <b>New User</b>\n╰─────────────────────╯\n\n"
            "  ◎ <b>Name:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>\n"
            "  ◷ <b>Date:</b> {date}\n  ⚇ <b>Total:</b> <code>{total}</code>"
        ),
        "inactivity_reminder": "╭─────────────────────╮\n│  ❀ <b>We missed you!</b>\n╰─────────────────────╯\n\n  ▸ It's been a while since your last visit\n  ▸ New packs are waiting for you ✦\n\n  ⌂ Press /start to explore",
        "cant_ban_owner": "⚠ Cannot ban the owner.",
        "user_banned": "✓ Banned {user}.",
        "already_banned": "⚠ Already banned.",
        "user_unbanned": "✓ Unbanned {user}.",
        "not_banned": "⚠ Not banned.",
        "not_banned_short": "⚠ Not banned.",
        "unbanned_msg": "✓ Unbanned!",
        "banned_list_header": "⊘ <b>Banned Users</b>",
        "no_banned_users": "✓ No banned users.",
        "banned_user_item": "  ◎ {user}  <code>{uid}</code>",
        "user_not_found": "⚠ User not found.",
        "reply_broadcast": "⚠ Reply to the message to broadcast.",
        "no_users": "⚠ No users to broadcast to.",
        "broadcast_done": "✓ <b>Broadcast Complete!</b>\n↪ Delivered to <code>{count}</code>",
        "admin_reply_sent": "✓ Reply sent.",
        "admin_reply_fail": "⚠ Could not send reply.",
        "forwarding_toggled": "✓ Forwarding Updated",
        "forwarding_on": "◉ ON",
        "forwarding_off": "◌ OFF",
        "admin_reply_header": "↪ <b>Reply from admin:</b>",
        "request_sent": "✓ Your request has been sent.",
        "request_from_owner_msg": "╭─────────────────────╮\n│  ✉ <b>Request a Pack</b>\n╰─────────────────────╯\n\nWrite the pack name or description. It will be sent to the owner.",
        "request_executed": "╭─────────────────────╮\n│  ✓ <b>Request Fulfilled</b>\n╰─────────────────────╯\n\n  ❀ We hope you enjoy the pack\n  ✿ Happy to help anytime",
        "no_saved_request": "⚠ No saved request",
        "report_success": "⚠ Report submitted, will be reviewed.",
        "report_notification": (
            "╭─────────────────────╮\n│  ⚠ <b>Pack Report</b>\n╰─────────────────────╯\n\n"
            "  ◎ <b>From:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n  # <code>{uid}</code>\n"
            "  ▪ <b>Pack:</b> {pack_name}\n  ↗ <b>Link:</b> <a href=\"{pack_url}\">Open</a>\n"
            "  ✎ <b>Reason:</b> {reason}"
        ),
        "report_handled": "✓ Report handled.",
        "report_ignored": "✕ Report ignored.",
        "ask_report_reason": "✎ <b>Write the report reason:</b>",
        "ask_report_reason_short": "⚠ Please write the report reason.",
        "help_text": (
            "╭─────────────────────╮\n│  ⓘ <b>How to Use</b>\n╰─────────────────────╯\n\n"
            "⌕ <b>Search stickers:</b>\n  ▸ <code>/search keyword</code>\n  ▸ <code>@Bot keyword</code>\n"
            "  ▸ tap <b>«▤ View Packs»</b>\n\n▤ <b>View packs:</b>\n  ▸ Choose the first letter\n  ▸ Tap a pack to add it\n\n"
            "★ <b>Premium packs:</b>\n  ▸ Require Telegram Premium\n\n✉ <b>Request a pack:</b>\n  ▸ tap <b>«✉ Request Pack»</b>\n\n"
            "⚠ <b>Report a pack:</b>\n  ▸ tap the ⚠ button\n\n◐ <b>Change language:</b>\n  ▸ tap <b>«◐ Language»</b>\n\n"
            "◉ <b>Our Channel:</b> <a href=\"https://t.me/AhmShY\">@Ahmshy</a>\n\nⓘ <b>Tip:</b> Use inline mode from any chat!"
        ),
        "set_video_success": "✓ Tutorial video saved.",
        "set_video_reply": "⚠ Reply to a video then type <code>/setvideo</code>",
        "del_video_success": "✓ Tutorial video deleted.",
        "del_video_not_found": "⚠ No tutorial video is set.",
        "video_manage_info": "▶ <b>Tutorial Video Settings</b>\n\n  ▪ <b>Status:</b> {status}\n\n✎ <b>To add a video:</b>\n  ▸ Reply with <code>/setvideo</code>\n\n✎ <b>To delete:</b>\n  ▸ Use <code>/delvideo</code>",
        "video_manage_info_deleted": "▶ <b>Tutorial Video Settings</b>\n\n  ▪ <b>Status:</b> ✕ Not set\n\n✎ <b>To add a video:</b>\n  ▸ Reply with <code>/setvideo</code>",
        "video_status_added": "✓ Set",
        "video_status_not_added": "✕ Not set",
        "backup_creating": "◷ Creating backup...",
        "backup_sent": "✓ Backup sent!",
        "backup_failed": "✕ Backup failed",
        "scan_started": "⌕ Scanning packs...",
        "scan_complete": "✓ <b>Scan complete!</b>\n\n  ⌫ Deleted {deleted}\n  ✎ Updated {updated}\n  ▪ Unchanged {unchanged}",
        "new_packs_notification": "╭─────────────────────╮\n│  ✦ <b>New Packs</b>\n╰─────────────────────╯\n\n  ▸ Press /start to explore\n  ◉ <a href=\"https://t.me/AhmShY\">Our Channel</a>",
        "inline_all_packs": "▪ All packs ({count})",
        "inline_pack_item": "{num}. {title}",
        "inline_all_packs_title": "▪ All packs matching:",
        "inline_pack_label": "▪ <b>Sticker Pack:</b>",
        "inline_channel_follow": "◉ Follow our channel:",
        "inline_pack_count_desc": "Packs: {count}",
        "inline_pack_link_desc": "Tap to open in the bot",
        "inline_no_results_title": "✕ No results",
        "inline_no_results_msg": "✕ No results for: <code>{query}</code>",
        "inline_no_results_desc": "No matching results",
        "inline_msg_header": "⌕ Search Results",
        "inline_msg_query_label": "✎ Query:",
        "inline_msg_count_label": "▪ Packs:",
        "inline_msg_hint": "▸ Tap a pack name to open it",
        "inline_msg_channel_label": "◉ Our Channel:",
        "owner_settings_btn": "⚙ Settings",
        "owner_settings_header": (
            "╭─────────────────────╮\n"
            "│  ⚙ <b>Owner Settings</b>\n"
            "╰─────────────────────╯\n\n"
            "  ▸ <b>Trigger word:</b> <code>{trigger}</code>\n"
            "  ▸ <b>Group link:</b> {group}\n"
            "  ▸ <b>Channel link:</b> {channel}\n"
            "  ▸ <b>Force-sub channel:</b> {sub}\n"
            "  ▸ <b>Force-sub:</b> {sub_status}"
        ),
        "set_trigger_btn": "✎ Trigger Word",
        "set_group_btn": "✎ Group Link",
        "set_channel_btn": "✎ Channel Link",
        "set_sub_btn": "✎ Force-Sub Channel",
        "toggle_forcesub_btn": "⚙ Force-Sub: {status}",
        "force_sub_on": "◉ ON",
        "force_sub_off": "◌ OFF",
        "ask_trigger_name": "✎ <b>Send the new trigger word</b>\n\n▸ Example: <code>solo</code>\n▸ User types: <code>solo how are you</code>\n\n▸ Send <code>del</code> to reset.",
        "ask_group_link": "✎ <b>Send the group link</b>\n\n▸ Example: <code>https://t.me/mygroup</code>\n▸ Send <code>del</code> to delete.",
        "ask_channel_link": "✎ <b>Send the channel link</b>\n\n▸ Example: <code>https://t.me/mychannel</code>\n▸ Send <code>del</code> to delete.",
        "ask_sub_channel": "✎ <b>Send the force-sub channel</b>\n\n▸ Example: <code>@mychannel</code> or link\n▸ Send <code>del</code> to disable.\n\n⚠ Make sure bot is admin in the channel.",
        "setting_saved": "✓ Saved.",
        "setting_deleted": "✓ Deleted.",
        "invalid_setting": "⚠ Invalid value.",
        "force_sub_enabled_msg": "✓ Force-sub enabled.",
        "force_sub_disabled_msg": "✓ Force-sub disabled.",
        "need_sub_channel_first": "⚠ Set the force-sub channel first.",
        "you_are_quiet": "🤫",
        "image_failed": "⚠ Could not analyze the image, please try again.",
        "wake_reply": "🎤 Go ahead, I'm listening!",
        "owner_request_pack_msg": "⚠ You are the owner! Add packs via /add or /addpremium",
        "categories_header": "╭─────────────────────╮\n│  🗂 <b>Categories</b>\n╰─────────────────────╯\n\n▸ Choose a category to browse:",
        "category_works_header": "╭─────────────────────╮\n│  {label}\n│  ▪ <b>Works:</b> {count}\n╰─────────────────────╯\n\n▤ <b>Choose a work:</b>",
        "category_packs_header": "╭─────────────────────╮\n│  {label}\n│  ▪ <b>Count:</b> {count}\n╰─────────────────────╯",
        "work_packs_header": "╭─────────────────────╮\n│  📺 <b>{work}</b>\n│  ▪ <b>Characters:</b> {count}\n╰─────────────────────╯",
        "no_packs_in_category": "⚠ No packs in this category yet.",
        "no_works_in_category": "⚠ No works in this category yet.",
        "choose_category_for_pack": "🗂 <b>Choose category for:</b>\n▪ <code>{pack}</code>",
        "category_set": "✓ Category: {label}",
        "ask_setcat_usage": "⚠ <b>Usage:</b>\n<code>/setcat &lt;category&gt;</code> reply to a sticker\n\n▸ Available: <code>anime, manga, manhwa, movies, games, cartoon, memes, sports, animals, celebrities, flags, emoji, other</code>",
        "cat_back_cats": "◂ Categories",
        "cat_back_works": "◂ Works",
        "cat_all_packs": "▦ All packs",
        "cat_page_prev": "◂ Prev",
        "cat_page_next": "Next ▸",
        "cat_page_info": "Page {current} of {total}",
        "owner_panel_header": "╭─────────────────────╮\n│  ⚙ <b>Owner Panel</b>\n╰─────────────────────╯",
        "op_packs": "🖼 Manage Packs",
        "op_cats": "🗂 Categories",
        "op_ai": "🤖 AI",
        "op_settings": "⚙ Bot Settings",
        "op_channels": "📢 Channels",
        "op_admins": "👥 Admins",
        "op_stats_adv": "▦ Advanced Stats",
        "op_stats": "▦ Statistics",
        "op_banned": "⊘ Banned",
        "op_backup": "⤓ Backup",
        "op_broadcast": "📢 Broadcast",
        "op_back": "◂ Back",
        "op_packs_header": "╭─────────────────────╮\n│  🖼 <b>Manage Packs</b>\n╰─────────────────────╯\n\n▸ Choose operation:",
        "op_cats_header": "╭─────────────────────╮\n│  🗂 <b>Manage Categories</b>\n╰─────────────────────╯\n\n▸ Choose operation:",
        "op_ai_header": "╭─────────────────────╮\n│  🤖 <b>AI Settings</b>\n╰─────────────────────╯\n\n▸ Choose:",
        "op_settings_header": "╭─────────────────────╮\n│  ⚙ <b>Bot Settings</b>\n╰─────────────────────╯\n\n▸ Choose:",
        "op_channels_header": "╭─────────────────────╮\n│  📢 <b>Channels</b>\n╰─────────────────────╯",
        "op_admins_header": "╭─────────────────────╮\n│  👥 <b>Admins</b>\n╰─────────────────────╯",
        "ask_add_admin": "➕ <b>Add Admin</b>\n\n▸ Send:\n  • <code>@username</code>\n  • or numeric ID\n\nOr send <code>del</code> to cancel.",
        "admin_added": "✓ Added <b>{name}</b> as admin.\n  # <code>{uid}</code>",
        "admin_removed": "✓ Removed <b>{name}</b> from admins.",
        "admin_already": "⚠ Already admin.",
        "owner_admin": "⚠ This is the owner.",
        "no_admins": "▸ No admins yet.",
        "ai_classifying": "🤖 Classifying... ▰▰▰▱▱▱▱▱▱▱",
        "ai_classify_fail": "⚠ Classification failed.",
        "ai_classify_done": "✓ <b>Classified</b>\n\n{label}\n📺 <b>Work:</b> {work}\n👤 <b>Character:</b> {character}",
        "ai_backfill_started": "🤖 <b>Classifying packs...</b>\n▸ Count: <code>{count}</code>",
        "ai_backfill_progress": "🤖 {done}/{total}\n✓ Done: <b>{ok}</b>",
        "ai_backfill_done": "✓ <b>Done!</b>\n\n▪ Total: <code>{total}</code>\n✓ Classified: <b>{ok}</b>",
        "ai_backfill_none": "✓ All packs already classified.",
        "ai_classify_btn": "🤖 Classify with AI",
        "ai_reclassify_btn": "🔄 Reclassify",
        "reclassify_done": "✓ <b>Classified</b>\n\n{label}\n📺 <b>Work:</b> {work}\n👤 <b>Character:</b> {character}",
        "suggested_name_changed": "✎ <b>Name:</b>\n  ▪ Before: <code>{old}</code>\n  ▪ After: <code>{new}</code>",
        "op_backfill_btn": "🤖 Classify all ({count})",
        "op_cats_view": "🗂 View Categories",
        "op_cats_setcat": "✎ Set category (reply)",
        "op_cats_setwork": "📺 Set work (reply)",
        "op_cats_reclassify": "🔄 Reclassify AI (reply)",
        "ai_menu_status": "Status: {status}",
        "ai_menu_on": "✓ Turn ON",
        "ai_menu_off": "✕ Turn OFF",
        "ai_menu_key": "✎ Set API Key",
        "ai_menu_model": "✎ Change Model",
        "ai_menu_base": "✎ Change Base URL",
        "ai_menu_prompt": "✎ Edit Prompt",
        "ai_menu_smart": "🤖 Apply Smart Prompt",
        "ask_ai_key": "🔑 <b>Send API key now:</b>\n\n▸ Example: <code>AIza...</code>",
        "ask_ai_model": "🧠 <b>Send new model name:</b>",
        "ask_ai_base": "🌐 <b>Send new Base URL:</b>",
        "ask_ai_prompt": "📝 <b>Send new prompt:</b>",
        "op_cats_scan_all": "🔍 Full catalog AI scan",
        "op_cats_scan_others": "🔍 Scan unclassified packs",
        "op_cats_add": "➕ Add category",
        "op_cats_remove": "🗑 Remove custom category",
        "op_cats_bulk_add": "🎯 Add packs to category",
        "ask_addcat_format": (
            "➕ <b>Send category in this format:</b>\n\n"
            "<code>emoji | Arabic name | English name</code>\n\n"
            "▸ Example:\n<code>🎵 | موسيقى | Music</code>"
        ),
        "cat_added": "✓ Category added:\n{label}",
        "cat_exists": "⚠ Category already exists.",
        "cat_invalid_format": "⚠ Invalid format.\nUse: <code>emoji | Arabic | English</code>",
        "cat_removed": "✓ Category removed: {label}",
        "no_custom_cats": "⚠ No custom categories.",
        "scan_all_started": (
            "🤖 <b>Full catalog scan running...</b>\n"
            "▸ Packs: <code>{count}</code>\n\n"
            "  {bar}  <code>{done}/{count}</code>\n\n"
            "◷ Please wait...\n\n"
            "💡 Press /start to stop"
        ),
        "scan_others_started": (
            "🤖 <b>Scanning unclassified packs...</b>\n"
            "▸ Packs: <code>{count}</code>\n\n"
            "  {bar}  <code>{done}/{count}</code>\n\n"
            "◷ Please wait...\n\n"
            "💡 Press /start to stop"
        ),
        "scan_all_progress": "🤖 <b>Scanning...</b>\n\n  {bar}  <code>{done}/{total}</code>\n  ✓ Classified: <b>{ok}</b>\n  ✕ Failed: <b>{fail}</b>\n\n💡 Press /start to stop",
        "scan_all_done": (
            "╭─────────────────────╮\n│  ✓ <b>Full scan complete!</b>\n╰─────────────────────╯\n\n"
            "  ▰▰▰▰▰▰▰▰▰▰  <code>{total}/{total}</code>\n\n"
            "  ▪ <b>Total:</b> <code>{total}</code>\n"
            "  ✓ <b>Classified:</b> <code>{ok}</code>\n"
            "  ✎ <b>Renamed:</b> <code>{renamed}</code>\n"
            "  ✕ <b>Failed:</b> <code>{fail}</code>"
        ),
        "scan_stopped": "⏹ <b>Classification stopped.</b>\n\n  {bar}  <code>{done}/{total}</code>\n  ✓ Done: <b>{ok}</b>",
        "scan_all_need_ai": "⚠ AI must be enabled.",
        "pending_classify_header": "🗂 <b>Packs to classify</b>\n▪ Count: <code>{count}</code>",
        "pending_classify_bulk_header": (
            "╭─────────────────────╮\n│  🗂 <b>Packs to classify</b>\n│  ▪ Count: <code>{count}</code>\n╰─────────────────────╯\n\n"
            "▸ Choose a category to apply to <b>all</b>,\n  or review one by one."
        ),
        "pending_classify_one_btn": "📋 Review one by one",
        "pending_classify_bulk_btn": "⚡ Bulk classify",
        "pending_classify_all_set": "✓ Classified <b>{count}</b> packs as {label}",
        "pending_classify_none": "✓ No pending packs.",
        "notif_pack_classify_ask": (
            "╭─────────────────────╮\n│  🗂 <b>Classify new pack</b>\n╰─────────────────────╯\n\n"
            "  ▪ <code>{pack}</code>\n\n▸ Choose category:"
        ),
        "notif_skip_btn": "⏭ Skip",
        "notif_skip_all_btn": "⏭ Skip all",
        "ai_scan_btn_small": "🤖 Classify this",
        "scan_review_btn": "📋 Review pending ({count})",
        "adv_stats_header": "╭─────────────────────╮\n│  ▦ <b>Advanced Stats</b>\n╰─────────────────────╯",
        "adv_stats_body": (
            "  📅 <b>Day:</b> <code>{day}</code>\n\n"
            "  ⌕ <b>Top Searcher:</b>\n"
            "    ▸ Today: {top_search_day}\n"
            "    ▸ All: {top_search_all}\n\n"
            "  ⚇ <b>Top Bot User:</b>\n"
            "    ▸ Today: {top_user_day}\n"
            "    ▸ All: {top_user_all}\n\n"
            "  🎲 <b>Top /random User:</b>\n"
            "    ▸ Today: {top_rand_day}\n"
            "    ▸ All: {top_rand_all}\n\n"
            "  ⌕ <b>Total searches:</b> <code>{total_searches}</code>\n"
            "  🎲 <b>Total random:</b> <code>{total_rand}</code>"
        ),
        "bulk_cat_choose": "🎯 <b>Choose the category to add packs to:</b>",
        "bulk_cat_ask_packs": (
            "🎯 <b>Category:</b> {label}\n\n"
            "▸ Now send <b>pack links</b> or <b>reply to stickers</b> from the packs.\n"
            "▸ You can send multiple packs (one per message).\n\n"
            "  ▪ <b>Added so far:</b> <code>{count}</code>\n\n"
            "▸ Press <b>✓ Done</b> when finished, or <b>✕ Cancel</b>."
        ),
        "bulk_cat_added_one": "✓ Added pack: <code>{name}</code>\n▪ Total: {count}",
        "bulk_cat_failed": "⚠ Couldn't recognize a pack. Send a link or reply to a sticker.",
        "bulk_cat_finish": (
            "╭─────────────────────╮\n│  ✓ <b>Done!</b>\n╰─────────────────────╯\n\n"
            "  ▪ <b>Category:</b> {label}\n"
            "  ▪ <b>Added packs:</b> <code>{count}</code>"
        ),
        "bulk_cat_empty": "⚠ No packs added.",
        "bulk_cat_cancelled": "✕ Cancelled.",
        "bulk_done_btn": "✓ Done",
        "bulk_cancel_btn": "✕ Cancel",
        "cmd_panel": "≡ All Commands",
        "cmd_panel_header": "≡ <b>All Commands (buttons)</b>\n\n▸ Choose a command:",
    }
}

LANG_KEYBOARD = InlineKeyboardMarkup([[
    make_btn("◐ العربية", callback_data="set_lang|ar", style="primary"),
    make_btn("◐ English", callback_data="set_lang|en", style="primary"),
]])

# ========================= Helpers =========================
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F1E0-\U0001F1FF\U00002600-\U000026FF]+", flags=re.UNICODE)

def clean_title(text: str) -> str:
    if not text: return ""
    for w in [r"𝚅𝙲𝚽", r"join", r"𝐽𝑂𝐼𝑁", r"𝑱𝒐𝒊𝒏", r"𑁍", r"━Y", r"𝗧𝗐𝗂𝗍", r":", r"-", r"_", r"\|", r"\.", r"ᗷY 𓉮", r"ᗷY", r"𓉮"]:
        text = re.sub(w, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"@[A-Za-z0-9_]+", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = EMOJI_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()

def is_premium_pack(pack: dict) -> bool:
    return bool(pack.get("is_premium", False))

def get_user_display(user):
    if user.first_name: return html.escape(user.first_name)
    return f"User {user.id}"

def get_lang(user_id):
    return DB.get("users_lang", {}).get(str(user_id), "en")

def set_lang(user_id, lang):
    DB.setdefault("users_lang", {})[str(user_id)] = lang
    save_db(DB)

def get_text(user_id, key, **kwargs):
    lang = get_lang(user_id)
    text = TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, ""))
    if kwargs:
        try: return text.format(**kwargs)
        except Exception: return text
    return text

def touch_user(user_id):
    DB.setdefault("last_active", {})[str(user_id)] = _now_makkah().isoformat()
    DB.setdefault("inactivity_notified", {})
    if str(user_id) in DB["inactivity_notified"]:
        del DB["inactivity_notified"][str(user_id)]

# ========================= Owner Settings =========================
def get_trigger_name():
    return (DB.get("settings", {}).get("trigger_name") or DEFAULT_TRIGGER_NAME).lower().strip()

def get_group_link():
    return DB.get("settings", {}).get("group_link", "") or ""

def get_channel_link():
    return DB.get("settings", {}).get("channel_link", "") or CHANNEL_URL

def check_solo_trigger(text, trigger_name=None):
    if not text: return None
    if trigger_name is None:
        trigger_name = get_trigger_name()
    if not trigger_name: return None
    t = text.strip()
    tl = t.lower(); tn = trigger_name.lower()
    if tl == tn: return ""
    for sep in (" ", ",", ":", "\n", "،", "!", "؟", "?"):
        if tl.startswith(tn + sep):
            return t[len(tn):].lstrip(" ,:\n،!؟?").strip()
    return None

async def is_chat_quiet(context, chat_id):
    until = context.bot_data.get("quiet_until", {}).get(chat_id)
    return bool(until and datetime.now() < until)

def set_chat_quiet(context, chat_id, minutes=QUIET_DURATION_MINUTES):
    context.bot_data.setdefault("quiet_until", {})[chat_id] = datetime.now() + timedelta(minutes=minutes)

def clear_chat_quiet(context, chat_id):
    try: context.bot_data.get("quiet_until", {}).pop(chat_id, None)
    except Exception: pass

async def check_force_sub(bot, user_id):
    s = DB.get("settings", {})
    if not s.get("force_sub_enabled"): return True
    sub_ch = (s.get("force_sub_channel") or "").strip()
    if not sub_ch: return True
    if user_id == OWNER_ID or is_admin(user_id): return True
    try:
        m = await bot.get_chat_member(chat_id=sub_ch, user_id=user_id)
        if m.status in ("member", "administrator", "creator"): return True
    except Exception: pass
    return False

async def send_force_sub_msg(bot, chat_id, user_id):
    s = DB.get("settings", {})
    sub_ch = (s.get("force_sub_channel") or "").strip()
    if not sub_ch: return
    link = sub_ch
    if sub_ch.startswith("@"): link = f"https://t.me/{sub_ch[1:]}"
    elif not sub_ch.startswith("http"): link = f"https://t.me/{sub_ch}"
    text = (
        "╭─────────────────────╮\n"
        "│  ⚠ <b>اشتراك إجباري</b>\n"
        "╰─────────────────────╯\n\n"
        "▸ يجب الاشتراك في قناتنا أولاً لاستخدام البوت\n\n"
        f"◉ <b>القناة:</b> <a href=\"{link}\">{html.escape(sub_ch)}</a>"
    )
    kb = InlineKeyboardMarkup([[make_btn("◉ اشترك الآن", url=link, style="primary")]])
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML",
                               reply_markup=kb, disable_web_page_preview=True)
    except Exception: pass

def get_owner_settings_text(user_id):
    s = DB.get("settings", {})
    trigger = s.get("trigger_name", DEFAULT_TRIGGER_NAME)
    group = s.get("group_link") or "—"
    channel = s.get("channel_link") or "—"
    sub = s.get("force_sub_channel") or "—"
    sub_status = get_text(user_id, "force_sub_on") if s.get("force_sub_enabled") else get_text(user_id, "force_sub_off")
    return get_text(user_id, "owner_settings_header",
                    trigger=html.escape(trigger), group=html.escape(group),
                    channel=html.escape(channel), sub=html.escape(sub), sub_status=sub_status)

def get_owner_settings_keyboard(user_id):
    s = DB.get("settings", {})
    sub_status = get_text(user_id, "force_sub_on") if s.get("force_sub_enabled") else get_text(user_id, "force_sub_off")
    return InlineKeyboardMarkup([
        [make_btn(get_text(user_id, "set_trigger_btn"), callback_data="os_set_trigger", style="primary")],
        [make_btn(get_text(user_id, "set_group_btn"), callback_data="os_set_group", style="primary"),
         make_btn(get_text(user_id, "set_channel_btn"), callback_data="os_set_channel", style="primary")],
        [make_btn(get_text(user_id, "set_sub_btn"), callback_data="os_set_sub", style="primary")],
        [make_btn(get_text(user_id, "toggle_forcesub_btn", status=sub_status), callback_data="os_toggle_forcesub", style="success")],
        [make_btn(get_text(user_id, "op_back"), callback_data="owner_panel", style="danger")],
    ])

async def resolve_user(bot, user_input, user_id):
    user_input = (user_input or "").strip()
    if not user_input: return None
    try:
        if user_input.startswith('@'): return await bot.get_chat(user_input[1:])
        return await bot.get_chat(int(user_input))
    except Exception: return None

def extract_links_from_entities(msg):
    links = []
    ents = list(getattr(msg, "entities", None) or []) + list(getattr(msg, "caption_entities", None) or [])
    text = msg.text or msg.caption or ""
    for e in ents:
        if e.type == "text_link" and getattr(e, "url", None): links.append(e.url)
        elif e.type == "url":
            try: links.append(text[e.offset:e.offset + e.length])
            except Exception: pass
    return links

def combine_text_and_entity_links(msg):
    text = msg.text or msg.caption or ""
    el = extract_links_from_entities(msg)
    if el: text += "\n" + "\n".join(el)
    return text

def extract_pack_names_from_text(text: str):
    if not text: return []
    names = []
    for line in text.splitlines():
        line = line.strip()
        m = re.search(r"(?:https?://)?(?:t\.me|telegram\.me)/(?:addstickers|addemoji)/([A-Za-z0-9_]+)", line)
        if m: names.append(m.group(1)); continue
        m = re.match(r'^\d+\.\s*(.+)$', line)
        if m:
            nm = re.match(r'^([A-Za-z0-9_]+(?:\s+[A-Za-z0-9_]+)*)', m.group(1).strip())
            if nm and nm.group(1).strip(): names.append(nm.group(1).strip())
            continue
        if re.match(r'^[A-Za-z0-9_]+$', line) and len(line) > 2 and not re.search(r'[أ-ي]', line):
            names.append(line)
    return names

async def get_sticker_set_with_retry(bot, set_name):
    for name in list(dict.fromkeys([set_name, set_name.replace(" ", "_"), set_name.replace(" ", ""), set_name.replace(" ", "-")])):
        try: return await bot.get_sticker_set(name)
        except Exception: continue
    return None

def get_recent_packs(limit=RECENT_PACKS_LIMIT):
    items = [(k, v) for k, v in DB["packs"].items() if v.get("added_at")]
    items.sort(key=lambda x: x[1].get("added_at", ""), reverse=True)
    return items[:limit]

# ========================= Categories =========================
def refresh_categories():
    for k, v in (DB.get("custom_categories") or {}).items():
        CATEGORIES[k] = v

def get_pack_category(pack):
    c = (pack or {}).get("category") or "other"
    return c if c in CATEGORIES else "other"

def get_category_label(cat_id, user_id=None):
    cat = CATEGORIES.get(cat_id) or CATEGORIES["other"]
    lang = get_lang(user_id) if user_id else "en"
    if lang == "ar":
        name = cat.get("ar") or cat.get("en") or cat_id
    else:
        name = cat.get("en") or cat.get("ar") or cat_id
    return f"{cat.get('emoji', '')} {name}".strip()

def get_pack_work(pack):
    return ((pack or {}).get("work") or "").strip() or "غير مصنّف"

def get_works_in_category(cat_id):
    works = {}
    for k, p in DB["packs"].items():
        if get_pack_category(p) != cat_id: continue
        w = get_pack_work(p)
        works.setdefault(w, []).append(p)
    for w in works:
        works[w].sort(key=lambda x: x.get("title", "").lower())
    return dict(sorted(works.items(), key=lambda x: x[0].lower()))

def get_packs_in_work(cat_id, work_name):
    return [p for p in DB["packs"].values()
            if get_pack_category(p) == cat_id and get_pack_work(p) == work_name]

def category_has_works(cat_id):
    for p in DB["packs"].values():
        if get_pack_category(p) == cat_id:
            w = (p.get("work") or "").strip()
            if w and w != "غير مصنّف":
                return True
    return False

def _categories_ready(threshold=CATS_READY_THRESHOLD):
    packs = DB.get("packs", {})
    if not packs: return False
    classified = sum(1 for p in packs.values() if p.get("work"))
    return (classified / len(packs)) >= threshold

# ========================= Visits =========================
def track_pack_visit(key):
    if not key: return
    key = str(key).lower()
    DB.setdefault("pack_visits", {})
    DB["pack_visits"][key] = DB["pack_visits"].get(key, 0) + 1
    save_db(DB)

def get_top_visited_packs_with_counts(limit=30):
    visits = DB.get("pack_visits", {}) or {}
    if not visits: return []
    items = []
    for k, cnt in visits.items():
        pack = DB["packs"].get(k)
        if pack: items.append({"pack": pack, "count": cnt})
    items.sort(key=lambda x: -x["count"])
    return items[:limit]

async def schedule_delete_message(bot, chat_id, message_id, delay=AUTO_DELETE_SECONDS):
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception: pass

# ========================= Search Scoring =========================
def search_relevance_score(title, query):
    t = normalize_query(title); q = normalize_query(query)
    if not q or not t: return 0
    if t == q: return 1000
    if t.replace(" ", "") == q.replace(" ", ""): return 900
    if t.startswith(q + " ") or t.startswith(q): return 800
    tw = re.findall(r"[a-z0-9]+", t); qw = re.findall(r"[a-z0-9]+", q)
    if qw and all(w in tw for w in qw): return 700
    if tw and tw[0] == q: return 650
    if qw and tw and any(w in tw for w in qw): return 500
    if RAPIDFUZZ_OK:
        try:
            r = max(_rf_fuzz.partial_ratio(q, t), _rf_fuzz.token_sort_ratio(q, t))
            if r >= 85: return 400
            if r >= 70: return 300
        except Exception: pass
    else:
        r = difflib.SequenceMatcher(None, q, t).ratio()
        if r >= 0.85: return 400
        if r >= 0.7: return 300
    qp = phonetic_normalize(q); tp = phonetic_normalize(t)
    if qp and tp:
        if qp == tp: return 450
        if qp in tp or tp in qp: return 350
    return 0

def split_search_results(all_packs, query, main_threshold=500):
    sm, se = [], []
    for p in all_packs:
        s = search_relevance_score(p.get("title", ""), query)
        if s >= main_threshold: sm.append((s, p))
        elif s > 0: se.append((s, p))
    sm.sort(key=lambda x: (-x[0], x[1].get("title", "").lower()))
    se.sort(key=lambda x: (-x[0], x[1].get("title", "").lower()))
    return [p for _, p in sm], [p for _, p in se]

def find_search_suggestions(query, max_suggestions=5):
    qws = re.findall(r"[A-Za-z0-9]+", query.lower())
    if not qws: return []
    aw = set()
    for pack in DB["packs"].values():
        for w in re.findall(r"[A-Za-z0-9]+", pack.get("title", "").lower()):
            if len(w) >= 3: aw.add(w)
    if not aw: return []
    wl = list(aw); phon = {w: phonetic_normalize(w) for w in wl}
    out, seen = [], set()
    for qw in qws:
        if len(qw) < 3: continue
        qp = phonetic_normalize(qw)
        for w, wp in phon.items():
            if w in seen or w == qw or len(wp) < 2 or len(qp) < 2: continue
            if wp == qp: seen.add(w); out.append(w)
        if RAPIDFUZZ_OK:
            try:
                for w in wl:
                    if w in seen or w == qw: continue
                    if _rf_fuzz.ratio(qw, w) >= 70: seen.add(w); out.append(w)
            except Exception: pass
        else:
            for m in difflib.get_close_matches(qw, wl, n=4, cutoff=0.6):
                if m != qw and m not in seen and qw not in m: seen.add(m); out.append(m)
        for w in wl:
            if w != qw and (qw in w or w in qw) and w not in seen:
                if abs(len(w) - len(qw)) <= 6: seen.add(w); out.append(w)
    return out[:max_suggestions]

def find_similar_packs(query):
    q = normalize_query(query)
    if not q: return []
    am = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
    for k, v in DB["packs"].items():
        if v in am: continue
        tn = normalize_query(v.get("title", ""))
        qw = re.findall(r"[a-z0-9]+", q); tw = re.findall(r"[a-z0-9]+", tn)
        matched = False
        for w in qw:
            if len(w) < 3: continue
            qp = phonetic_normalize(w)
            for t2 in tw:
                if len(t2) < 3: continue
                tp = phonetic_normalize(t2)
                if qp == tp: matched = True; break
                if RAPIDFUZZ_OK:
                    try:
                        if _rf_fuzz.ratio(qp, tp) >= 82: matched = True; break
                    except Exception: pass
                else:
                    if difflib.SequenceMatcher(None, qp, tp).ratio() >= 0.82: matched = True; break
            if matched: break
        if matched: am.append(v)
    _, extra = split_search_results(am, q, main_threshold=500)
    return extra

def _normalize_character(title, work, character):
    t_norm = normalize_query(title)
    w_norm = normalize_query(work)
    c_norm = normalize_query(character) if character else ""
    if (not character) or (c_norm and c_norm == w_norm) or (t_norm and t_norm == w_norm):
        return "All"
    return character

def finalize_new_pack(key, pack_data):
    pack_data["added_at"] = _now_makkah().isoformat()
    pack_data.setdefault("category", "other")
    pack_data.setdefault("work", "")
    pack_data.setdefault("character", "")
    DB["packs"][key] = pack_data
    DB["stats"]["packs_since_notify"] = DB["stats"].get("packs_since_notify", 0) + 1
    save_db(DB)
    if DB["stats"].get("packs_since_notify", 0) >= PACKS_BEFORE_NOTIFY:
        DB["stats"]["packs_since_notify"] = 0
        save_db(DB)
        if APP_REF is not None:
            try: asyncio.create_task(schedule_new_packs_notification())
            except Exception: pass
    if DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key"):
        try: asyncio.create_task(auto_classify_pack_async(key))
        except Exception: pass
    else:
        try: asyncio.create_task(_notify_pending_classify(key))
        except Exception: pass

async def _notify_pending_classify(pack_key):
    if APP_REF is None: return
    await asyncio.sleep(0.5)
    DB.setdefault("pending_classify", [])
    if pack_key not in DB["pending_classify"]:
        DB["pending_classify"].append(pack_key)
    save_db(DB)
    pack = DB["packs"].get(pack_key)
    if not pack: return
    title = pack.get("title", pack_key)
    pending = DB["pending_classify"]
    try:
        if len(pending) == 1:
            await APP_REF.bot.send_message(
                chat_id=OWNER_ID,
                text=get_text(OWNER_ID, "notif_pack_classify_ask", pack=html.escape(title)),
                parse_mode="HTML",
                reply_markup=build_pending_classify_keyboard(pack_key=pack_key, bulk=False))
        else:
            await APP_REF.bot.send_message(
                chat_id=OWNER_ID,
                text=get_text(OWNER_ID, "pending_classify_bulk_header", count=len(pending)),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [make_btn(get_text(OWNER_ID, "pending_classify_one_btn"),
                              callback_data="pending_review", style="primary")],
                    [make_btn(get_text(OWNER_ID, "pending_classify_bulk_btn"),
                              callback_data="pending_bulk_start", style="success")],
                ]))
    except Exception as e:
        logging.error(f"_notify_pending_classify: {e}")

async def schedule_new_packs_notification():
    await asyncio.sleep(NOTIFY_DELAY)
    users = list(DB.get("users", []))
    if not users or APP_REF is None: return
    for uid in users:
        try:
            await APP_REF.bot.send_message(chat_id=uid, text=get_text(uid, "new_packs_notification"),
                                           parse_mode="HTML", disable_web_page_preview=True)
        except Exception: pass
        await asyncio.sleep(NOTIFY_STAGGER)

# ========================= Query Cache =========================
def cache_query(query):
    if not query: return "0"
    key = hashlib.md5(query.encode("utf-8")).hexdigest()[:8]
    DB.setdefault("_query_cache", {})[key] = query
    cache = DB["_query_cache"]
    if len(cache) > 500:
        for k in list(cache.keys())[:100]: del cache[k]
    save_db(DB)
    return key

def get_cached_query(key):
    if not key or key == "0": return ""
    return DB.get("_query_cache", {}).get(key, "")

# ========================= DB =========================
def save_db(data):
    INDEX_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_db():
    default = {
        "packs": {},
        "settings": {
            "forward_messages": True, "tutorial_video_id": None,
            "ai_enabled": False, "ai_api_key": "",
            "ai_base_url": "https://generativelanguage.googleapis.com/v1beta",
            "ai_model": "gemini-2.5-flash",
            "ai_system_prompt": SMART_SYSTEM_PROMPT,
            "ai_provider": "auto",
            "trigger_name": DEFAULT_TRIGGER_NAME,
            "group_link": DEFAULT_GROUP_LINK,
            "channel_link": DEFAULT_CHANNEL_LINK,
            "force_sub_channel": "", "force_sub_enabled": False,
        },
        "users": [], "admins": [], "banned_users": [], "users_lang": {},
        "last_active": {}, "inactivity_notified": {}, "pack_visits": {},
        "_query_cache": {},
        "custom_categories": {},
        "pending_classify": [],
        "stats": {
            "total_searches": 0, "search_queries": {}, "packs_since_notify": 0,
            "random_total": 0, "random_usage": {},
            "daily_searches": {}, "daily_users": {}, "daily_random": {},
            "user_searches": {}, "user_usage": {},
        },
    }
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            for k in ("packs", "users_lang", "last_active", "inactivity_notified", "pack_visits", "_query_cache", "custom_categories"):
                data.setdefault(k, {})
            data.setdefault("pending_classify", [])
            for k in ("users", "admins", "banned_users"): data.setdefault(k, [])
            data.setdefault("settings", {})
            for k, v in default["settings"].items():
                data["settings"].setdefault(k, v)
            data.setdefault("stats", {})
            for k, v in default["stats"].items():
                data["stats"].setdefault(k, v)
            for k, p in data.get("packs", {}).items():
                if isinstance(p, dict):
                    p.setdefault("category", "other")
                    p.setdefault("work", "")
                    p.setdefault("character", "")
            return data
        except Exception: return default
    return default

DB = load_db()
refresh_categories()

# ========================= Daily Stats =========================
def _today_key():
    return _now_makkah().date().isoformat()

def _bump_daily(bucket_name, uid):
    stats = DB.setdefault("stats", {})
    bucket = stats.setdefault(bucket_name, {})
    day = _today_key()
    day_map = bucket.setdefault(day, {})
    sid = str(uid)
    day_map[sid] = day_map.get(sid, 0) + 1
    if len(bucket) > 30:
        for k in sorted(bucket.keys())[:-30]:
            bucket.pop(k, None)

def track_random_usage(user, chat_type="private"):
    try:
        _bump_daily("daily_random", user.id)
        DB.setdefault("stats", {}).setdefault("random_usage", {})
        DB["stats"]["random_total"] = DB["stats"].get("random_total", 0) + 1
        k = str(user.id)
        ru = DB["stats"]["random_usage"]
        if k not in ru:
            ru[k] = {"name": user.first_name or "User", "username": user.username or "", "count": 0}
        ru[k]["count"] = ru[k].get("count", 0) + 1
        ru[k]["last"] = _now_makkah().isoformat()
        ru[k]["name"] = user.first_name or ru[k].get("name", "User")
        ru[k]["username"] = user.username or ru[k].get("username", "")
        save_db(DB)
    except Exception as e:
        logging.error(f"random_track: {e}")

def is_admin(user_id): return user_id == OWNER_ID or user_id in DB.get("admins", [])

def track_user(user_id):
    is_new = False
    if user_id not in DB["users"] and user_id != OWNER_ID:
        DB["users"].append(user_id); is_new = True
    _bump_daily("daily_users", user_id)
    us = DB["stats"].setdefault("user_usage", {})
    sid = str(user_id)
    us[sid] = us.get(sid, 0) + 1
    save_db(DB)
    return is_new

def track_search(query, user_id=None):
    query = (query or "").strip().lower()
    if not query: return
    DB["stats"]["total_searches"] = DB["stats"].get("total_searches", 0) + 1
    DB["stats"]["search_queries"][query] = DB["stats"]["search_queries"].get(query, 0) + 1
    if user_id:
        _bump_daily("daily_searches", user_id)
        all_s = DB["stats"].setdefault("user_searches", {})
        sid = str(user_id)
        all_s[sid] = all_s.get(sid, 0) + 1
    save_db(DB)

def get_top_search():
    q = DB["stats"].get("search_queries", {})
    return max(q, key=q.get) if q else "None"

def normalize_query(text): return re.sub(r"\s+", " ", (text or "").strip().lower())

def encode_query(q): return quote(q, safe="")
def decode_query(q):
    try: return unquote(q)
    except Exception: return q

def pack_matches_query(title, query): return normalize_query(query) in normalize_query(title)

def pack_matches_query_any(query):
    q = normalize_query(query)
    if not q: return False
    for k, v in DB["packs"].items():
        if pack_matches_query(v.get("title", ""), q): return True
    return False

def build_pack_button_text(idx, pack):
    title = pack.get("title", "Sticker Pack")
    star = "★ " if is_premium_pack(pack) else ""
    return f"{idx}. {star}{title}"

# ========================= AI =========================
def get_packs_context_for_ai(max_packs=10000):
    packs = DB.get("packs", {})
    dt = get_current_datetime_info()
    time_ctx = (f"\n⏰ الوقت الحالي (مكة):\n"
                f"- التاريخ: {dt['date_ar']} ({dt['date_en']})\n"
                f"- الوقت: {dt['time_ar']} ({dt['time_en']})\n"
                f"- اليوم: {dt['weekday_ar']}\n")
    if not packs:
        return time_ctx + "\n⚠ لا توجد أي حزم ملصقات محفوظة حالياً في الأرشيف."
    recent = []
    for k, v in packs.items():
        if v.get("added_at"): recent.append((v.get("added_at", ""), v.get("title", "")))
    recent.sort(reverse=True)
    recent_15 = recent[:15]
    titles = []
    for k, v in packs.items():
        t = v.get("title", "")
        if t:
            star = "★ بريميوم:" if v.get("is_premium") else "▪"
            titles.append(f"{star} {t}")
    titles.sort()
    if len(titles) > max_packs:
        shown = titles[:max_packs]; extra = f"\n... و {len(titles) - max_packs} حزمة أخرى"
    else:
        shown = titles; extra = ""
    recent_ctx = ""
    if recent_15:
        recent_ctx = "\n🆕 آخر 15 حزمة:\n" + "\n".join(f"  ▸ {t}" for _, t in recent_15) + "\n"
    return (f"{time_ctx}\n📊 إجمالي الحزم: {len(titles)}\n{recent_ctx}\n📋 القائمة:\n" + "\n".join(shown) + extra)


# ═══════════ AI Providers Config ═══════════
AI_PROVIDER_CONFIG = {
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "format": "google",
        "default_model": "gemini-2.5-flash-lite",
    },
    "requesty": {
        "name": "Requesty",
        "base_url": "https://router.requesty.ai/v1",
        "format": "openai",
        "default_model": "google/gemini-2.5-flash-lite",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "format": "openai",
        "default_model": "google/gemini-2.5-flash-lite",
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "format": "openai",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "format": "openai",
        "default_model": "gpt-4o-mini",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "format": "openai",
        "default_model": "claude-3-5-haiku-20241022",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "format": "openai",
        "default_model": "deepseek-chat",
    },
    "mistral": {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "format": "openai",
        "default_model": "mistral-small-latest",
    },
    "custom": {
        "name": "Custom (OpenAI-compatible)",
        "base_url": "",
        "format": "openai",
        "default_model": "",
    },
}


def _detect_ai_provider(key: str, override: str = "") -> str:
    """يكتشف المزود تلقائياً من صيغة المفتاح"""
    if override and override.strip() and override != "auto":
        return override.strip().lower()
    k = (key or "").strip()
    if not k:
        return "gemini"
    if k.startswith("rqsty-sk-"):
        return "requesty"
    if k.startswith("sk-or-"):
        return "openrouter"
    if k.startswith("gsk_"):
        return "groq"
    if k.startswith("AQ.") or k.startswith("AIza"):
        return "gemini"
    if k.startswith("sk-ant-"):
        return "anthropic"
    if k.startswith("sk-"):
        return "openai"
    return "gemini"


async def _send_ai_error(title: str, detail: str):
    """يرسل تفاصيل خطأ AI إلى المالك مباشرة"""
    if APP_REF is None: return
    try:
        text = f"🔴 <b>{title}</b>\n\n<code>{html.escape(detail[:900])}</code>"
        await APP_REF.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="HTML")
    except Exception:
        pass


async def _ai_request(system_prompt: str, user_content, max_tokens: int = 500, temperature: float = 0.0):
    """
    دالة موحدة لكل مزودي AI.
    user_content: نص عادي (str) أو قائمة أجزاء (list) للصور.
    ترجع: نص الرد أو None.
    """
    s = DB.get("settings", {})
    if not s.get("ai_enabled"):
        await _send_ai_error("AI معطّل", "ai_enabled=False")
        return None
    key = (s.get("ai_api_key") or "").strip()
    if not key:
        await _send_ai_error("مفتاح مفقود", "ai_api_key فارغ")
        return None

    provider_id = _detect_ai_provider(key, s.get("ai_provider", "auto"))
    cfg = AI_PROVIDER_CONFIG.get(provider_id) or AI_PROVIDER_CONFIG["gemini"]
    base_url = (s.get("ai_base_url") or cfg["base_url"]).rstrip("/")
    if not base_url:
        await _send_ai_error("Base URL مفقود", f"المزود: {provider_id}")
        return None
    model = s.get("ai_model") or cfg["default_model"]
    if not model:
        await _send_ai_error("موديل مفقود", f"المزود: {provider_id}")
        return None

    # ═══════════ Google Gemini (الصيغة الأصلية) ═══════════
    if cfg["format"] == "google":
        if isinstance(user_content, str):
            contents = [{"role": "user", "parts": [{"text": user_content}]}]
        else:
            contents = [{"role": "user", "parts": user_content}]
        url = f"{base_url}/models/{model}:generateContent?key={key}"
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                r = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": contents,
                        "generationConfig": {
                            "maxOutputTokens": max_tokens,
                            "temperature": temperature,
                        }
                    }
                )
                if r.status_code != 200:
                    logging.error(f"ai HTTP {r.status_code}: {r.text[:500]}")
                    await _send_ai_error(f"HTTP {r.status_code} — {provider_id}/{model}", r.text[:900])
                    return None
                data = r.json()
                cands = data.get("candidates", [])
                if not cands:
                    await _send_ai_error("رد فارغ", json.dumps(data, ensure_ascii=False)[:900])
                    return None
                parts = cands[0].get("content", {}).get("parts", [])
                if not parts:
                    await _send_ai_error("لا يوجد parts", json.dumps(cands[0], ensure_ascii=False)[:900])
                    return None
                return parts[0].get("text", "").strip() or None
        except Exception as e:
            logging.error(f"ai: {e}", exc_info=True)
            await _send_ai_error("Exception", f"{type(e).__name__}: {str(e)}")
            return None

    # ═══════════ OpenAI-compatible (Requesty/OpenRouter/Groq/OpenAI/Mistral...) ═══════════
    url = f"{base_url}/chat/completions"
    if isinstance(user_content, str):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            if r.status_code != 200:
                logging.error(f"ai HTTP {r.status_code}: {r.text[:500]}")
                await _send_ai_error(f"HTTP {r.status_code} — {provider_id}/{model}", r.text[:900])
                return None
            data = r.json()
            ch = data.get("choices", [])
            if not ch:
                await _send_ai_error("رد فارغ", json.dumps(data, ensure_ascii=False)[:900])
                return None
            return (ch[0].get("message", {}).get("content") or "").strip() or None
    except Exception as e:
        logging.error(f"ai: {e}", exc_info=True)
        await _send_ai_error("Exception", f"{type(e).__name__}: {str(e)}")
        return None


# ═══════════ Wrappers ═══════════
async def call_ai_raw(prompt: str, system_prompt: str = "You are a helpful assistant.", max_tokens: int = 500):
    return await _ai_request(system_prompt, prompt, max_tokens=max_tokens, temperature=0.0)


async def call_ai(prompt: str, history=None):
    s = DB.get("settings", {})
    base_system = s.get("ai_system_prompt") or SMART_SYSTEM_PROMPT
    dt = get_current_datetime_info()
    packs_ctx = get_packs_context_for_ai()
    system = (f"{base_system}\n\n═══════ معلومات حقيقية ═══════\n"
              f"⏰ الوقت: {dt['time_ar']} | {dt['time_en']}\n"
              f"📅 التاريخ: {dt['date_ar']} | {dt['date_en']}\n"
              f"🌍 اليوم: {dt['weekday_ar']}\n═══════════════════════════════\n\n"
              f"{packs_ctx}\n\n⚠️ قواعد صارمة:\n"
              "1. لا تخترع حزم ملصقات غير موجودة.\n"
              "2. إذا سأل عن حزمة غير موجودة، قل «ما عندنا» واقترح زر «طلب حزمة».\n"
              "3. لا تختلق روابط وهمية.\n"
              "4. 🚫 لا تذكر أي بوت آخر.\n"
              "5. ✅ اجب على أي سؤال عام.\n"
              "6. ✅ الوقت والتاريخ مذكوران أعلاه.\n"
              "7. ✅ رد بنفس لغة المستخدم.\n"
              "8. كن مختصراً وطبيعياً.")
    context_str = ""
    if history:
        for m in history[-8:]:
            role = m.get("role", "")
            content = m.get("content", "")
            if isinstance(content, str) and content:
                if role == "user":
                    context_str += f"[المستخدم]: {content}\n"
                elif role == "assistant":
                    context_str += f"[أنت]: {content}\n"
    full_prompt = (context_str + f"[المستخدم]: {prompt}") if context_str else prompt
    return await _ai_request(system, full_prompt, max_tokens=600, temperature=0.4)


async def get_file_data_url(bot, file_id, default_mime="image/jpeg"):
    try:
        f = await bot.get_file(file_id)
        ba = await f.download_as_bytearray()
        raw = bytes(ba)
        mime = default_mime
        if raw[:3] == b'\xff\xd8\xff': mime = "image/jpeg"
        elif raw[:8] == b'\x89PNG\r\n\x1a\n': mime = "image/png"
        elif raw[:4] == b'RIFF' and raw[8:12] == b'WEBP': mime = "image/webp"
        elif raw[:6] in (b'GIF87a', b'GIF89a'): mime = "image/gif"
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}", mime
    except Exception as e:
        logging.error(f"get_file_data_url: {e}")
        return None, None


async def call_ai_with_image(prompt, image_data_url, history=None):
    s = DB.get("settings", {})
    base_system = s.get("ai_system_prompt") or SMART_SYSTEM_PROMPT
    dt = get_current_datetime_info()
    packs_ctx = get_packs_context_for_ai()
    system = (f"{base_system}\n\n⏰ الوقت: {dt['time_ar']} | 📅 {dt['date_ar']}\n\n"
              "أنت مساعد في بوت أرشيف ملصقات.\n"
              f"═══════ الأرشيف ═══════\n{packs_ctx}\n═══════════════════════\n")

    try:
        b64 = image_data_url.split(",", 1)[1]
        mime = "image/jpeg"
        if image_data_url.startswith("data:"):
            mime = image_data_url.split(";")[0].replace("data:", "") or "image/jpeg"
    except Exception:
        return await call_ai(prompt, history)

    provider_id = _detect_ai_provider(s.get("ai_api_key", ""), s.get("ai_provider", "auto"))
    cfg = AI_PROVIDER_CONFIG.get(provider_id) or AI_PROVIDER_CONFIG["gemini"]

    if cfg["format"] == "google":
        parts = [
            {"text": prompt or "صف هذه الصورة بإيجاز."},
            {"inline_data": {"mime_type": mime, "data": b64}},
        ]
        return await _ai_request(system, parts, max_tokens=500, temperature=0.4)
    else:
        content = [
            {"type": "text", "text": prompt or "صف هذه الصورة بإيجاز."},
            {"type": "image_url", "image_url": {"url": image_data_url}},
        ]
        return await _ai_request(system, content, max_tokens=500, temperature=0.4)


async def ai_find_matching_packs(user_text):
    if not user_text: return [], [], []
    packs = DB.get("packs", {})
    if not packs: return [], [], []
    pack_list = []
    for k, v in packs.items():
        t = v.get("title", "")
        if t:
            star = "[P]" if v.get("is_premium") else "[-]"
            pack_list.append(f"{k} | {star} {t}")
    system = ("You match user requests to sticker packs. Reply EXACTLY in three lines:\n"
              "ALIASES: <up to 6, comma>\nCHARACTERS: <up to 25, comma>\nKEYS: <up to 40, comma>\n"
              "If nothing: ALIASES: NONE\\nCHARACTERS: NONE\\nKEYS: NONE")
    prompt = ("1) ALIASES: all English names/aliases of the show.\n"
              "2) CHARACTERS: main characters in English.\n"
              "3) KEYS: all matching pack keys from the list.\n\n"
              f"PACKS LIST:\n" + "\n".join(pack_list) + f"\n\nUSER: {user_text}")
    try:
        result = await call_ai_raw(prompt, system_prompt=system)
        if not result: return [], [], []
        aliases, characters, keys = [], [], []
        for line in result.split("\n"):
            line = line.strip(); up = line.upper()
            if up.startswith("ALIASES:"):
                rest = line[8:].strip()
                if rest and rest.upper() != "NONE":
                    for a in re.split(r"[,\n]", rest):
                        a = a.strip().strip('"\'').strip()
                        if a and a not in aliases and len(a) < 60: aliases.append(a)
            elif up.startswith("CHARACTERS:"):
                rest = line[11:].strip()
                if rest and rest.upper() != "NONE":
                    for c in re.split(r"[,\n]", rest):
                        c = c.strip().strip('"\'').strip()
                        if c and c not in characters and len(c) < 60: characters.append(c)
            elif up.startswith("KEYS:"):
                rest = line[5:].strip()
                if rest and rest.upper() != "NONE":
                    for k in re.split(r"[,\n]", rest):
                        k = k.strip().strip('"\'').strip().lower()
                        if k and k in packs and k not in keys: keys.append(k)
        return aliases[:6], characters[:30], keys[:40]
    except Exception as e:
        logging.error(f"ai_match: {e}", exc_info=True)
        return [], [], []


async def ai_extract_search_term(user_text):
    if not user_text: return []
    system = "You are a search-term extractor. Only output English search terms."
    prompt = ("Extract character/show name. Reply ONLY with up to 4 English names separated by '|'.\n"
              "If NOT asking about stickers, reply: NONE\n\n" f"User: {user_text}")
    try:
        result = await call_ai_raw(prompt, system_prompt=system)
        if not result: return []
        result = result.strip().strip('"\'').strip()
        first_line = result.split("\n")[0].strip()
        if not first_line or first_line.upper() == "NONE": return []
        candidates = []
        for c in first_line.split("|"):
            c = c.strip().strip('"\'').strip()
            if not c or len(c) > 60 or re.search(r"[\u0600-\u06FF]", c) or len(c.split()) > 5: continue
            if c not in candidates: candidates.append(c)
        return candidates[:4]
    except Exception as e:
        logging.error(f"ai_extract: {e}", exc_info=True)
        return []


def _is_long_or_messy_title(title):
    if not title: return False
    if len(title) > 40: return True
    if len(title.split()) > 6: return True
    sym = sum(1 for c in title if not c.isalnum() and not c.isspace())
    if sym / max(len(title), 1) > 0.3: return True
    if re.search(r'\d{4,}', title): return True
    return False


async def ai_classify_pack(title, suggest_name=False):
    if not title: return None
    res = await ai_classify_batch([("__one__", title)], suggest_names=suggest_name)
    return res.get("__one__")


async def ai_classify_batch(titles, suggest_names=False, retries=3):
    if not titles: return {}
    cats = ", ".join(CATEGORIES.keys())
    if suggest_names:
        system = (
            "You classify sticker packs. Output ONLY a JSON array (no prose, no code fences).\n"
            "Each object keys: i (int), c (category), w (work), ch (character), n (suggested_name).\n"
            f"c must be one of: [{cats}]\n"
            "Rules:\n"
            "  anime       = Japanese anime (Naruto, Bleach, JJK, One Piece, Demon Slayer)\n"
            "  manga       = Japanese manga without anime adaptation\n"
            "  manhwa      = Korean webtoon (Solo Leveling, Tower of God)\n"
            "  cartoon     = Western (Tom&Jerry, SpongeBob, Looney Tunes)\n"
            "  movies      = live-action film or TV series\n"
            "  games       = video games (Genshin, Valorant, Minecraft)\n"
            "  memes       = reactions/memes\n"
            "  sports      = sports teams/players\n"
            "  animals     = animals/pets\n"
            "  celebrities = real famous people (actors, singers, athletes, influencers)\n"
            "  flags       = country flags\n"
            "  emoji       = emoji packs\n"
            "  other       = anything else\n"
            "w = Title Case work name. If not related to any work, set w = ''.\n"
            "ch = character name. If the pack is only the work itself, use 'All'.\n"
            "n = short clean name <=40 chars: JUST the character name (or work name). NEVER combine them with ' - '.\n"
            'Example: [{"i":1,"c":"anime","w":"Naruto","ch":"Naruto Uzumaki","n":"Naruto Uzumaki"}]'
        )
    else:
        system = (
            "You classify sticker packs. Output ONLY a JSON array.\n"
            'Keys: i (int), c (category), w (work), ch (character).\n'
            f"c must be one of: [{cats}]\n"
            "w = Title Case work or 'Unknown'. ch = character, or 'All' if work-only."
        )
    max_toks = min(CLASSIFY_MAX_OUTPUT_TOKENS, max(1000, len(titles) * 120))
    results = {}
    current_titles = list(titles)
    for attempt in range(retries + 1):
        items = "\n".join(f'{i+1}|{t}' for i, (_, t) in enumerate(current_titles))
        prompt = f"Input packs (index|title):\n{items}\n\nOutput JSON array only."
        max_toks = min(CLASSIFY_MAX_OUTPUT_TOKENS, max(1000, len(current_titles) * 120))
        raw = await call_ai_raw(prompt, system_prompt=system, max_tokens=max_toks)
        if not raw:
            await asyncio.sleep(1.2 * (attempt + 1)); continue
        raw = raw.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw).strip()
        m = re.search(r'\[[\s\S]*\]', raw)
        if not m:
            await asyncio.sleep(1.0); continue
        try:
            arr = json.loads(m.group(0))
        except Exception:
            await asyncio.sleep(1.2 * (attempt + 1)); continue
        for item in arr:
            try:
                idx = int(item.get("i", 0)) - 1
                if idx < 0 or idx >= len(current_titles): continue
                key = current_titles[idx][0]
                title = current_titles[idx][1]
                cat = (item.get("c") or item.get("category") or "other").strip().lower()
                if cat not in CATEGORIES: cat = "other"
                work = (item.get("w") or item.get("work") or "").strip()[:60]
                character = (item.get("ch") or item.get("character") or "").strip()[:60]
                character = _normalize_character(title, work, character)
                r = {"category": cat, "work": work, "character": character}
                if suggest_names:
                    sn = (item.get("n") or item.get("suggested_name") or "").strip()
                    if sn:
                        sn = clean_title(sn)[:60]
                        if " - " in sn:
                            sn = sn.split(" - ", 1)[0].strip()
                        if sn and len(sn) >= 3:
                            r["suggested_name"] = sn
                results[key] = r
            except Exception: continue
        if len(results) == len(titles): return results
        missing = [(k, t) for k, t in titles if k not in results]
        if not missing: return results
        current_titles = missing
        if attempt >= retries: break
        await asyncio.sleep(0.5)
    return results


async def auto_classify_pack_async(key):
    pack = DB["packs"].get(key)
    if not pack or pack.get("work"): return
    title = pack.get("title", "")
    if not title: return
    res = await ai_classify_pack(title, suggest_name=True)
    if not res: return
    pack = DB["packs"].get(key)
    if not pack or pack.get("work"): return
    pack["category"] = res["category"]
    pack["work"] = res["work"]
    pack["character"] = res.get("character") or _normalize_character(title, res["work"], "")
    if res.get("suggested_name") and res["suggested_name"] != title:
        pack["title"] = res["suggested_name"]
    save_db(DB)


def search_packs_smart(query_str):
    q = normalize_query(query_str)
    if not q: return [], [], query_str
    arr = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
    mi, ei = split_search_results(arr, q, main_threshold=500)
    if not mi and arr:
        mi = sorted(arr, key=lambda x: x.get("title", "").lower()); ei = []
    used = query_str
    if not mi and " " in query_str:
        for w in query_str.split():
            if len(w) < 3: continue
            q2 = normalize_query(w)
            arr2 = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q2)]
            m2, e2 = split_search_results(arr2, q2, main_threshold=500)
            if not m2 and arr2:
                m2 = sorted(arr2, key=lambda x: x.get("title", "").lower()); e2 = []
            if m2: return m2, e2, w
    return mi, ei, used


async def _show_ai_search_results(msg, context, user_id, mi, ei, used, chat_type):
    try: track_search(used, user_id)
    except Exception: pass
    try:
        context.user_data["last_search_packs"] = [p.get("set_name", "") for p in mi if p.get("set_name")][:10]
    except Exception: pass
    target_uid = user_id
    ins = str(user_id)
    reply_to_id = None
    gcid = None
    if chat_type != "private":
        gcid = msg.chat.id
        replied = msg.reply_to_message
        if (replied and replied.from_user
            and replied.from_user.id != context.bot.id
            and replied.from_user.id != user_id
            and not replied.from_user.is_bot):
            target_uid = replied.from_user.id
            ins = f"{user_id},{target_uid}"
            reply_to_id = replied.message_id
            try: track_user(target_uid)
            except Exception: pass
    total = len(mi)
    kb, _ = build_search_keyboard_for_group(mi, 0, target_uid, ins, chat_type,
        encoded_query=encode_query(used), source="search",
        bot_username=context.bot.username, group_chat_id=gcid)
    if ei: kb = add_more_packs_button(kb, ins, encode_query(used), len(ei), target_uid)
    hdr = f"✨ <b>لقيت لك:</b> <code>{html.escape(used)}</code>\n\n"
    hdr += get_text(target_uid, "search_results", query=html.escape(used), count=total)
    try:
        kwargs = dict(reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
        if reply_to_id is not None: kwargs["reply_to_message_id"] = reply_to_id
        await msg.reply_text(hdr, **kwargs)
        return True
    except Exception as e:
        logging.error(f"show_ai_results: {e}")
        return False


async def handle_solo_response(update, context, solo_text):
    user = update.effective_user
    msg = update.effective_message
    try: await try_react(context.bot, msg.chat_id, msg.message_id, pick_random_reactions(10, "cool"))
    except Exception: pass
    if not (DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key")):
        try: await msg.reply_text("👋 أنا هنا! لكن الذكاء الاصطناعي غير مفعّل حالياً.")
        except Exception: pass
        return
    if solo_text and has_intent_keyword(solo_text):
        aliases, characters, keys = await ai_find_matching_packs(solo_text)
        mi_all, seen_keys = [], set()
        for alias in aliases:
            q = normalize_query(alias)
            if not q: continue
            for k, v in DB["packs"].items():
                if k in seen_keys: continue
                if pack_matches_query(v.get("title", ""), q):
                    mi_all.append(v); seen_keys.add(k)
        for char in characters:
            q = normalize_query(char)
            if not q: continue
            for k, v in DB["packs"].items():
                if k in seen_keys: continue
                if pack_matches_query(v.get("title", ""), q):
                    mi_all.append(v); seen_keys.add(k)
        for k in keys:
            if k in seen_keys: continue
            p = DB["packs"].get(k)
            if p: mi_all.append(p); seen_keys.add(k)
        if mi_all:
            mi_all.sort(key=lambda x: x.get("title", "").lower())
            if await _show_ai_search_results(msg, context, user.id, mi_all, [], solo_text, msg.chat.type):
                return
        candidates = await ai_extract_search_term(solo_text)
        if candidates:
            mi2, ei2, used2 = [], [], None
            for cand in candidates:
                m_tmp, e_tmp, u_tmp = search_packs_smart(cand)
                if m_tmp: mi2, ei2, used2 = m_tmp, e_tmp, u_tmp; break
            if mi2:
                if await _show_ai_search_results(msg, context, user.id, mi2, ei2, used2 or candidates[0], msg.chat.type):
                    return
            reply = await call_ai(f"المستخدم طلب: {' / '.join(candidates)}. اعتذر بلطف واطلب زر «طلب حزمة». سطرين.")
            if reply:
                try:
                    reply = sanitize_ai_reply(reply)
                    kb = InlineKeyboardMarkup([[make_btn(get_text(user.id, "request_pack_btn"),
                                                         callback_data="request_pack", style="primary")]])
                    await msg.reply_text(reply, reply_markup=kb)
                    return
                except Exception: pass
    replied = msg.reply_to_message
    prompt = solo_text or ""
    image_data = None
    if replied:
        if replied.photo:
            image_data, _ = await get_file_data_url(context.bot, replied.photo[-1].file_id)
            if not prompt: prompt = "صف هذه الصورة بإيجاز."
        elif replied.sticker:
            image_data, _ = await get_file_data_url(context.bot, replied.sticker.file_id, "image/webp")
            if not prompt: prompt = "صف هذا الملصق بإيجاز."
    full_prompt = prompt.strip() or "رد بشكل لطيف ومختصر."
    hist = context.user_data.get("ai_history") or []
    if image_data:
        context.user_data["last_image_data"] = image_data
        context.user_data["last_image_time"] = _now_makkah().isoformat()
        reply = await call_ai_with_image(full_prompt, image_data, hist)
    else:
        reply = await call_ai(full_prompt, hist)
    if reply:
        reply = sanitize_ai_reply(reply)
        hist.append({"role": "user", "content": full_prompt[:500]})
        hist.append({"role": "assistant", "content": reply})
        context.user_data["ai_history"] = hist[-AI_MEMORY_SIZE:]
        try: await msg.reply_text(reply)
        except Exception: pass

# ========================= Backup =========================
async def do_backup(bot, reason=""):
    try:
        data = json.dumps(DB, ensure_ascii=False, indent=2).encode("utf-8")
        pc = sum(1 for p in DB.get("packs", {}).values() if p.get("is_premium"))
        await bot.send_document(chat_id=OWNER_ID,
            document=InputFile(io.BytesIO(data), filename=BACKUP_FILE_NAME),
            caption=(f"⤓ <b>Backup</b>\n  ▪ Packs: <code>{len(DB.get('packs', {}))}</code>\n"
                     f"  ★ Premium: <code>{pc}</code>\n  ⚇ Users: <code>{len(DB.get('users', []))}</code>\n"
                     f"  ◷ {_now_makkah().strftime('%Y-%m-%d %H:%M:%S')} (Makkah)\n  ✎ Reason: {reason or 'auto'}"),
            parse_mode="HTML")
        return True
    except Exception as e:
        logging.error(f"backup failed: {e}"); return False

async def backup_loop(app):
    await asyncio.sleep(30)
    await do_backup(app.bot, reason="startup")
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        await do_backup(app.bot, reason="auto")

async def inactivity_loop(app):
    await asyncio.sleep(60)
    while True:
        try:
            now = _now_makkah().replace(tzinfo=None); thr = now - timedelta(days=INACTIVITY_DAYS)
            users = list(DB.get("users", []))
            notified = DB.setdefault("inactivity_notified", {})
            for uid in users:
                sid = str(uid); last = DB.get("last_active", {}).get(sid)
                if not last: continue
                try:
                    last_dt = datetime.fromisoformat(last)
                    if last_dt.tzinfo: last_dt = last_dt.replace(tzinfo=None)
                except Exception: continue
                if last_dt < thr and sid not in notified:
                    try:
                        await app.bot.send_message(chat_id=uid, text=get_text(uid, "inactivity_reminder"),
                                                   parse_mode="HTML", disable_web_page_preview=True)
                        notified[sid] = now.isoformat(); save_db(DB)
                    except Exception: pass
                    await asyncio.sleep(1)
        except Exception: pass
        await asyncio.sleep(INACTIVITY_CHECK_INTERVAL)

async def verify_pack_names(bot):
    changed_keys = []
    for key, pack in list(DB["packs"].items()):
        sn = pack.get("set_name")
        if not sn: continue
        if pack.get("title_locked"): continue
        try:
            st = await bot.get_sticker_set(sn)
            new_title = clean_title(st.title or sn) or sn
            old_title = pack.get("title", "")
            if new_title and new_title.strip().lower() != old_title.strip().lower():
                pack["title"] = new_title
                pack["work"] = ""
                pack["character"] = ""
                changed_keys.append(key)
        except Exception:
            pass
        await asyncio.sleep(0.25)
    if changed_keys:
        save_db(DB)
        if DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key"):
            BATCH = CLASSIFY_BATCH_SIZE
            for start_i in range(0, len(changed_keys), BATCH):
                batch_keys = changed_keys[start_i:start_i + BATCH]
                batch = []
                for k in batch_keys:
                    p = DB["packs"].get(k)
                    if p: batch.append((k, p.get("title", "")))
                if not batch: continue
                results = await ai_classify_batch(batch, suggest_names=True)
                for k, _ in batch:
                    p = DB["packs"].get(k)
                    if not p: continue
                    res = results.get(k)
                    if res:
                        p["category"] = res["category"]
                        p["work"] = res["work"]
                        p["character"] = res.get("character") or _normalize_character(p.get("title", ""), res["work"], "")
                        if res.get("suggested_name") and res["suggested_name"] != p.get("title"):
                            p["title"] = res["suggested_name"]
                await asyncio.sleep(CLASSIFY_SLEEP_BETWEEN)
            save_db(DB)
    return len(changed_keys)

async def verify_pack_names_loop(app):
    await asyncio.sleep(VERIFY_NAMES_STARTUP_DELAY)
    while True:
        try:
            n = await verify_pack_names(app.bot)
            if n > 0:
                try:
                    await app.bot.send_message(
                        chat_id=OWNER_ID,
                        text=f"🔄 تم فحص الحزم: <code>{n}</code> حزمة تغيّر اسمها على تيليجرام وأُعيد تصنيفها.",
                        parse_mode="HTML")
                except Exception: pass
        except Exception as e:
            logging.error(f"verify_pack_names_loop: {e}")
        await asyncio.sleep(VERIFY_NAMES_INTERVAL)

async def post_init(app):
    global APP_REF
    APP_REF = app
    if not DB.get("packs"):
        try:
            await app.bot.send_message(chat_id=OWNER_ID,
                text=f"⚠ Database empty. Send <code>{BACKUP_FILE_NAME}</code> to restore.", parse_mode="HTML")
        except Exception: pass
    asyncio.create_task(backup_loop(app))
    asyncio.create_task(inactivity_loop(app))
    asyncio.create_task(verify_pack_names_loop(app))

async def handle_backup_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; msg = update.effective_message
    if not user or not msg or not msg.document: return
    if user.id != OWNER_ID or msg.chat.type != "private": return
    if not (msg.document.file_name or "").lower().endswith(".json"): return
    try:
        f = await msg.document.get_file(); raw = await f.download_as_bytearray()
        nb = json.loads(bytes(raw).decode("utf-8"))
        if "packs" not in nb:
            await msg.reply_text("✕ Invalid file."); return
        DB.clear(); DB.update(nb)
        for k, d in [("packs", {}), ("settings", {"forward_messages": True, "tutorial_video_id": None}),
                     ("users", []), ("admins", []), ("banned_users", []),
                     ("users_lang", {}), ("last_active", {}), ("inactivity_notified", {}),
                     ("pack_visits", {}), ("_query_cache", {}), ("custom_categories", {}),
                     ("pending_classify", []),
                     ("stats", {"total_searches": 0, "search_queries": {}, "packs_since_notify": 0,
                                "random_total": 0, "random_usage": {}, "daily_searches": {}, "daily_users": {},
                                "daily_random": {}, "user_searches": {}, "user_usage": {}})]:
            DB.setdefault(k, d)
        save_db(DB)
        refresh_categories()
        await msg.reply_text("✓ Restored successfully.", parse_mode="HTML")
    except Exception as e:
        await msg.reply_text(f"✕ Error: <code>{html.escape(str(e))}</code>", parse_mode="HTML")

async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    ok = await do_backup(context.bot, reason="manual")
    await update.effective_message.reply_text("✓ Backup created." if ok else "✕ Backup failed.")

# ========================= Pack Adding =========================
async def add_pack_from_link(context, set_name, url_type="stickers", force_premium=None):
    key = set_name.lower()
    is_e_url = (url_type == "emoji")
    is_p = is_e_url if force_premium is None else force_premium
    if key in DB["packs"]:
        ex = DB["packs"][key]; ch = False
        if is_p and not ex.get("is_premium"): ex["is_premium"] = True; ch = True
        if is_e_url and not ex.get("is_emoji"):
            ex["is_emoji"] = True; ex["url"] = f"https://t.me/addemoji/{set_name}"; ch = True
        if ch: save_db(DB)
        return ("upgraded" if ch else "exists", ex.get("title", set_name), ex.get("is_emoji", False))
    try: st = await context.bot.get_sticker_set(set_name)
    except Exception: return ("failed", set_name, False)
    stype = getattr(st, "sticker_type", "regular"); is_e = (stype == "custom_emoji")
    title = clean_title(st.title or set_name) or set_name
    purl = f"https://t.me/addemoji/{set_name}" if is_e else f"https://t.me/addstickers/{set_name}"
    finalize_new_pack(key, {"title": title, "url": purl, "set_name": set_name,
                            "is_premium": is_p, "is_emoji": is_e})
    return ("added", title, is_e)

async def process_pack_link_by_source(update, context, url_type, set_name, sender_is_owner, from_channel):
    user = update.effective_user; msg = update.effective_message
    key = set_name.lower()
    if key in DB["packs"]:
        if sender_is_owner: await msg.reply_text("⚠ Already saved.")
        return
    try: st = await context.bot.get_sticker_set(set_name)
    except Exception:
        if sender_is_owner:
            await msg.reply_text(f"✕ Pack not found: <code>{html.escape(set_name)}</code>", parse_mode="HTML")
        return
    stype = getattr(st, "sticker_type", "regular"); is_e = (stype == "custom_emoji")
    ts = st.title or set_name; title = clean_title(ts) or set_name
    purl = f"https://t.me/addemoji/{set_name}" if is_e else f"https://t.me/addstickers/{set_name}"
    if sender_is_owner:
        finalize_new_pack(key, {"title": title, "url": purl, "set_name": set_name,
                                "is_premium": is_e, "is_emoji": is_e})
        await msg.reply_text(get_text(OWNER_ID, "pack_added_simple", name=html.escape(title)), parse_mode="HTML")
        return
    if from_channel:
        finalize_new_pack(key, {"title": title, "url": purl, "set_name": set_name,
                                "is_premium": is_e, "is_emoji": is_e})
        return
    et = escape_markdown(title, version=1); es = escape_markdown(ts, version=1)
    eu = escape_markdown(user.first_name or "User", version=1)
    at = get_text(OWNER_ID, "new_pack_detected", user=eu, uid=user.id, src=es, filtered=et)
    kb = InlineKeyboardMarkup([
        [make_btn(get_text(OWNER_ID, "save_btn"), callback_data=f"+|{set_name}", style="success")],
        [make_btn(get_text(OWNER_ID, "rename_btn"), callback_data=f"r|{set_name}", style="primary"),
         make_btn(get_text(OWNER_ID, "ignore_btn"), callback_data=f"-|{set_name}", style="danger")],
        [make_btn(get_text(OWNER_ID, "ai_classify_btn"), callback_data=f"{RECLASSIFY_CB}|{set_name.lower()}", style="primary")],
    ])
    try: await context.bot.send_message(chat_id=OWNER_ID, text=at, reply_markup=kb, parse_mode="Markdown")
    except Exception: pass

# ========================= Keyboards =========================
def build_search_keyboard_for_group(all_items, page, user_id, initiator_str, chat_type,
                                    encoded_query=None, letter=None, source="search",
                                    nav_prefix=None, bot_username=None, group_chat_id=None,
                                    per_page=ITEMS_PER_PAGE):
    si = page * per_page; ei = si + per_page
    current = all_items[si:ei]
    show_actions = (chat_type == "private")
    keyboard = []
    for idx, pack in enumerate(current, start=si + 1):
        key = pack.get("set_name", "").lower()
        button_text = build_pack_button_text(idx, pack)
        if chat_type == "private":
            cb_data = f"{OPENPACK_CB}|{initiator_str}|{key}"
            open_btn = make_btn(button_text, callback_data=cb_data)
            if show_actions:
                if is_admin(user_id):
                    cb = f"del|{page}|{key}|{letter}|{initiator_str}" if source == "alpha" \
                         else f"del_search|{page}|{key}|{encoded_query}|{initiator_str}"
                    keyboard.append([open_btn, make_btn("⌫", callback_data=cb, style="danger")])
                else:
                    cb = f"report|{key}|{page}|{letter}|{initiator_str}" if source == "alpha" \
                         else f"report_search|{key}|{page}|{encoded_query}|{initiator_str}"
                    keyboard.append([open_btn, make_btn("⚠", callback_data=cb, style="danger")])
        else:
            cb_data = f"{OPENPACK_CB}|{initiator_str}|{key}"
            keyboard.append([make_btn(button_text, callback_data=cb_data)])
    nav = []; total = len(all_items)
    if nav_prefix:
        if page > 0: nav.append(make_btn("◂", callback_data=f"{nav_prefix}|{page-1}", style="primary"))
        if ei < total: nav.append(make_btn("▸", callback_data=f"{nav_prefix}|{page+1}", style="primary"))
    elif source == "alpha":
        if page > 0: nav.append(make_btn("◂", callback_data=f"{ALPHA_CB_PREFIX}|{initiator_str}|{letter}|{page-1}", style="primary"))
        if ei < total: nav.append(make_btn("▸", callback_data=f"{ALPHA_CB_PREFIX}|{initiator_str}|{letter}|{page+1}", style="primary"))
    else:
        safe = encoded_query or ""
        prefix = f"{SEARCH_CB_PREFIX}|{initiator_str}|{safe}"
        if page > 0: nav.append(make_btn("◂", callback_data=f"{prefix}|{page-1}", style="primary"))
        if ei < total: nav.append(make_btn("▸", callback_data=f"{prefix}|{page+1}", style="primary"))
    if nav: keyboard.append(nav)
    if chat_type == "private":
        keyboard.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
    else:
        keyboard.append([make_btn(get_text(user_id, "subscribe_channel"), url=CHANNEL_URL, style="primary")])
        keyboard.append([make_btn(get_text(user_id, "close_menu_btn"),
                                  callback_data=f"closemenu|{initiator_str}", style="danger")])
    return InlineKeyboardMarkup(keyboard), total

def build_visited_keyboard(items, page, user_id, chat_type, per_page=10):
    si = page * per_page; ei = si + per_page
    current = items[si:ei]; total = len(items)
    keyboard = []
    for idx, item in enumerate(current, start=si + 1):
        pack = item["pack"]; key = pack.get("set_name", "").lower()
        title = pack.get("title", "Pack")
        star = "★ " if is_premium_pack(pack) else ""
        btn_text = f"{idx}. {star}{title}"
        if chat_type == "private":
            cb_data = f"{OPENPACK_CB}|{user_id}|{key}"
            open_btn = make_btn(btn_text, callback_data=cb_data)
            if is_admin(user_id):
                keyboard.append([open_btn, make_btn("🗑", callback_data=f"unvisit|{key}", style="danger")])
            else:
                keyboard.append([open_btn])
        else:
            cb_data = f"{OPENPACK_CB}|{user_id}|{key}"
            keyboard.append([make_btn(btn_text, callback_data=cb_data)])
    nav = []
    if page > 0: nav.append(make_btn("◂", callback_data=f"show_visited|{page-1}", style="primary"))
    if ei < total: nav.append(make_btn("▸", callback_data=f"show_visited|{page+1}", style="primary"))
    if nav: keyboard.append(nav)
    if chat_type == "private":
        keyboard.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
    else:
        keyboard.append([make_btn(get_text(user_id, "subscribe_channel"), url=CHANNEL_URL, style="primary")])
        keyboard.append([make_btn(get_text(user_id, "close_menu_btn"),
                                  callback_data=f"closemenu|{user_id}", style="danger")])
    return InlineKeyboardMarkup(keyboard), total, current, si

def build_visited_text(user_id, total, current, start_idx):
    lines = [get_text(user_id, "visited_header", count=total), ""]
    for idx, item in enumerate(current, start=start_idx + 1):
        pack = item["pack"]; count = item["count"]
        star = "★" if is_premium_pack(pack) else "▪"
        lines.append(f"  {idx}. {star} {pack.get('title', 'Pack')}  —  👁 {count}")
    return "\n".join(lines)

def add_more_packs_button(kb, initiator_str, encoded_query, similar_count, user_id):
    if similar_count <= 0: return kb
    ex = list(kb.inline_keyboard)
    if not ex: return kb
    last = ex[-1:]; mid = ex[:-1]
    try: q_text = decode_query(encoded_query)
    except Exception: q_text = encoded_query or ""
    q_key = cache_query(q_text)
    cb_data = f"{SIMILAR_CB_PREFIX}|{initiator_str}|{q_key}|0"
    more = make_btn(get_text(user_id, "more_packs_btn", count=similar_count),
                    callback_data=cb_data, style="success")
    return InlineKeyboardMarkup(mid + [[more]] + last)

def add_back_to_results_button(kb, initiator_str, encoded_query, user_id):
    ex = list(kb.inline_keyboard)
    if not ex: return kb
    last = ex[-1:]; mid = ex[:-1]
    try: q_text = decode_query(encoded_query)
    except Exception: q_text = encoded_query or ""
    q_key = cache_query(q_text)
    cb_data = f"{BACK_SEARCH_CB}|{initiator_str}|{q_key}"
    back = make_btn(get_text(user_id, "back_to_results_btn"),
                    callback_data=cb_data, style="danger")
    return InlineKeyboardMarkup(mid + [[back]] + last)

# ========================= Category Keyboards =========================
def build_categories_keyboard(user_id, ins, back_cb=SHOW_ALPHA):
    counts = {}
    for p in DB["packs"].values():
        c = get_pack_category(p)
        counts[c] = counts.get(c, 0) + 1
    rows, row = [], []
    for cid, cat in CATEGORIES.items():
        n = counts.get(cid, 0)
        if n == 0: continue
        lang = get_lang(user_id)
        name = (cat.get("ar") if lang == "ar" else cat.get("en")) or cat.get("en") or cat.get("ar") or cid
        label = f"{cat['emoji']} {name} ({n})"
        row.append(make_btn(label, callback_data=f"{CAT_WORKS_CB}|{ins}|{cid}|0", style="primary"))
        if len(row) == 2: rows.append(row); row = []
    if row: rows.append(row)
    if not rows:
        rows.append([make_btn("⚠ لا توجد تصنيفات / No categories", callback_data="noop", style="danger")])
    rows.append([make_btn(get_text(user_id, "main_menu"), callback_data=back_cb, style="danger")])
    return InlineKeyboardMarkup(rows)

def build_works_keyboard(user_id, ins, cat_id, page=0):
    works = get_works_in_category(cat_id)
    work_names = list(works.keys())
    total = len(work_names)
    total_pages = max(1, (total + WORKS_PER_PAGE - 1) // WORKS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    si = page * WORKS_PER_PAGE
    ei = si + WORKS_PER_PAGE
    current = work_names[si:ei]
    rows = []
    for wn in current:
        count = len(works[wn])
        label = f"📺 {wn} ({count})"
        if len(label) > 45: label = label[:42] + "..."
        wk = cache_query(wn)
        rows.append([make_btn(label, callback_data=f"{WORK_CB}|{ins}|{cat_id}|{wk}|0", style="primary")])
    rows.append([make_btn(get_text(user_id, "cat_all_packs"),
                          callback_data=f"{CAT_FILTER_CB}|{ins}|{cat_id}|0", style="success")])
    nav = []
    if page > 0:
        nav.append(make_btn(get_text(user_id, "cat_page_prev"),
                            callback_data=f"{CAT_WORKS_CB}|{ins}|{cat_id}|{page-1}", style="primary"))
    if page < total_pages - 1:
        nav.append(make_btn(get_text(user_id, "cat_page_next"),
                            callback_data=f"{CAT_WORKS_CB}|{ins}|{cat_id}|{page+1}", style="primary"))
    if nav: rows.append(nav)
    if total_pages > 1:
        rows.append([make_btn(get_text(user_id, "cat_page_info", current=page+1, total=total_pages),
                              callback_data="noop", style="primary")])
    rows.append([make_btn(get_text(user_id, "cat_back_cats"), callback_data=f"{CAT_LIST_CB}|{ins}", style="danger")])
    return InlineKeyboardMarkup(rows), total

def build_category_letters_keyboard(user_id, ins, cid):
    packs = [p for p in DB["packs"].values() if get_pack_category(p) == cid]
    letters_available = set()
    for p in packs:
        t = (p.get("title") or "").strip()
        if t and re.match(r'^[a-zA-Z]', t): letters_available.add(t[0].upper())
        else: letters_available.add("#")
    buttons = []
    letters = [chr(ord('A') + i) for i in range(26)]
    row = []
    for i, l in enumerate(letters):
        if l in letters_available:
            row.append(make_btn(l, callback_data=f"{CAT_LETTER_CB}|{ins}|{cid}|{l}|0", style="primary"))
        else:
            row.append(make_btn("·", callback_data="noop", style="danger"))
        if len(row) == 7: buttons.append(row); row = []
    if row: buttons.append(row)
    if "#" in letters_available:
        buttons.append([make_btn("#", callback_data=f"{CAT_LETTER_CB}|{ins}|{cid}|#|0", style="primary")])
    buttons.append([make_btn(get_text(user_id, "cat_all_packs"), callback_data=f"{CAT_FILTER_CB}|{ins}|{cid}|0", style="success")])
    buttons.append([make_btn(get_text(user_id, "cat_back_works"), callback_data=f"{CAT_WORKS_CB}|{ins}|{cid}|0", style="danger")])
    return InlineKeyboardMarkup(buttons)

def build_setcat_keyboard(pack_key):
    rows, row = [], []
    for cid, cat in CATEGORIES.items():
        label = f"{cat['emoji']} {cat.get('ar', '')} / {cat.get('en', '')}"
        row.append(make_btn(label, callback_data=f"{SETCAT_CB}|{pack_key}|{cid}", style="primary"))
        if len(row) == 2: rows.append(row); row = []
    if row: rows.append(row)
    return InlineKeyboardMarkup(rows)

def build_pending_classify_keyboard(pack_key=None, bulk=False, user_id=OWNER_ID):
    rows, row = [], []
    for cid, cat in CATEGORIES.items():
        label = f"{cat['emoji']} {cat.get('ar', '')} / {cat.get('en', '')}"
        cb = f"clscat_bulk|{cid}" if bulk else f"clscat|{pack_key}|{cid}"
        row.append(make_btn(label, callback_data=cb, style="primary"))
        if len(row) == 2: rows.append(row); row = []
    if row: rows.append(row)
    if bulk:
        rows.append([make_btn(get_text(user_id, "notif_skip_all_btn"),
                              callback_data="clscat_skipall", style="danger")])
    else:
        rows.append([make_btn(get_text(user_id, "notif_skip_btn"),
                              callback_data=f"clscat_skip|{pack_key}", style="danger")])
    return InlineKeyboardMarkup(rows)

def build_bulk_cat_keyboard():
    rows, row = [], []
    for cid, cat in CATEGORIES.items():
        label = f"{cat['emoji']} {cat.get('ar', '')} / {cat.get('en', '')}"
        row.append(make_btn(label, callback_data=f"bulkcat|{cid}", style="primary"))
        if len(row) == 2: rows.append(row); row = []
    if row: rows.append(row)
    rows.append([make_btn(get_text(OWNER_ID, "op_back"), callback_data="op_cats_menu", style="danger")])
    return InlineKeyboardMarkup(rows)

# ========================= Stats Text =========================
def get_stats_text(user_id):
    pc = sum(1 for p in DB["packs"].values() if p.get("is_premium"))
    return get_text(user_id, "stats", packs=len(DB['packs']), premium=pc,
                    users=len(DB.get("users", [])), admins=len(DB.get("admins", [])),
                    banned=len(DB.get("banned_users", [])),
                    searches=DB["stats"].get("total_searches", 0),
                    top=html.escape(get_top_search()))

def _disp_name(uid):
    if not uid: return "—"
    sid = str(uid)
    ru = DB.get("stats", {}).get("random_usage", {}).get(sid, {})
    if ru.get("name"):
        un = f"@{ru['username']}" if ru.get("username") else ""
        return f"{html.escape(ru['name'])} {un}".strip()
    return f"<code>{sid}</code>"

def _fmt_top(mapping, top_id):
    if not top_id: return "—"
    cnt = mapping.get(top_id, 0)
    return f"{_disp_name(top_id)} — <b>{cnt}</b>"

def get_advanced_stats_text(user_id):
    day = _today_key()
    stats = DB.get("stats", {})
    ds = stats.get("daily_searches", {}).get(day, {})
    top_s_day = max(ds, key=ds.get) if ds else None
    ss = stats.get("user_searches", {})
    top_s_all = max(ss, key=ss.get) if ss else None
    du = stats.get("daily_users", {}).get(day, {})
    top_u_day = max(du, key=du.get) if du else None
    us = stats.get("user_usage", {})
    top_u_all = max(us, key=us.get) if us else None
    dr = stats.get("daily_random", {}).get(day, {})
    top_r_day = max(dr, key=dr.get) if dr else None
    ru = stats.get("random_usage", {})
    top_r_all = max(ru, key=lambda k: ru[k].get("count", 0)) if ru else None
    top_rand_all_str = "—"
    if top_r_all:
        c = ru.get(top_r_all, {}).get("count", 0)
        top_rand_all_str = f"{_disp_name(top_r_all)} — <b>{c}</b>"
    header = get_text(user_id, "adv_stats_header")
    body = get_text(user_id, "adv_stats_body",
                    day=day,
                    top_search_day=_fmt_top(ds, top_s_day),
                    top_search_all=_fmt_top(ss, top_s_all),
                    top_user_day=_fmt_top(du, top_u_day),
                    top_user_all=_fmt_top(us, top_u_all),
                    top_rand_day=_fmt_top(dr, top_r_day),
                    top_rand_all=top_rand_all_str,
                    total_searches=stats.get("total_searches", 0),
                    total_rand=stats.get("random_total", 0))
    return f"{header}\n\n{body}"

def get_commands_text(user_id): return get_text(user_id, "admin_commands")

def get_forwarding_status_text(user_id):
    s = "on" if DB["settings"].get("forward_messages", True) else "off"
    return get_text(user_id, "forwarding_on" if s == "on" else "forwarding_off")

def get_main_keyboard(user_id):
    is_admin_user = is_admin(user_id)
    buttons = [
        [make_btn("▤ " + get_text(user_id, "view_packs") + " 📦", callback_data=SHOW_ALPHA, style="success")],
        [make_btn("🗂 التصنيفات / Categories", callback_data=f"{CAT_LIST_CB}|{user_id}", style="success")],
        [make_btn(get_text(user_id, "easy_search_btn"), callback_data="easy_search", style="primary"),
         make_btn(get_text(user_id, "inline_search_btn"), switch_inline_query="", style="primary")],
        [make_btn(get_text(user_id, "new_packs_btn"), callback_data="show_recent|0", style="success"),
         make_btn(get_text(user_id, "random_pack_btn"), callback_data="random_pack", style="success")],
        [make_btn(get_text(user_id, "most_visited_btn"), callback_data="show_visited|0", style="success")],
    ]
    if user_id != OWNER_ID:
        buttons.append([make_btn(get_text(user_id, "request_pack"), callback_data="request_pack", style="primary")])
    buttons.extend([
        [make_btn(get_text(user_id, "help_btn"), callback_data="show_help", style="primary")],
        [make_btn(get_text(user_id, "owner_contact"), url="https://t.me/KKFEE", style="primary"),
         make_btn(get_text(user_id, "channel_link"), url=get_channel_link(), style="primary")],
        [make_btn(get_text(user_id, "change_lang_btn"), callback_data="change_lang", style="primary")],
    ])
    link_row = []
    gl = get_group_link(); cl = get_channel_link()
    if gl: link_row.append(make_btn("◉ المجموعة", url=gl, style="primary"))
    if cl: link_row.append(make_btn("◉ القناة", url=cl, style="primary"))
    if link_row: buttons.append(link_row)
    if is_admin_user:
        buttons.append([make_btn(get_text(user_id, "commands"), callback_data="show_commands", style="primary"),
                        make_btn(get_text(user_id, "statistics"), callback_data="show_stats", style="primary")])
        buttons.append([make_btn(get_text(user_id, "op_stats_adv"), callback_data="show_adv_stats", style="primary")])
        buttons.append([make_btn(get_text(user_id, "show_banned_btn"), callback_data=SHOW_BANNED, style="danger")])
        buttons.append([make_btn(get_text(user_id, "cmd_panel"), callback_data="cmd_panel", style="primary")])
    if user_id == OWNER_ID:
        buttons.append([make_btn("⚙ لوحة التحكم / Owner Panel", callback_data="owner_panel", style="success")])
    return InlineKeyboardMarkup(buttons)

def get_stats_keyboard(user_id):
    fwd = get_forwarding_status_text(user_id)
    return InlineKeyboardMarkup([
        [make_btn(get_text(user_id, "op_stats_adv"), callback_data="show_adv_stats", style="primary")],
        [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")],
        [make_btn(get_text(user_id, "forwarding_btn", status=fwd), callback_data="toggle_forward", style="primary")],
    ])

def get_commands_keyboard(user_id):
    fwd = get_forwarding_status_text(user_id)
    return InlineKeyboardMarkup([
        [make_btn(get_text(user_id, "cmd_panel"), callback_data="cmd_panel", style="primary")],
        [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")],
        [make_btn(get_text(user_id, "forwarding_btn", status=fwd), callback_data="toggle_forward", style="primary")],
    ])

def get_alpha_index_keyboard(user_id, initiator_str):
    buttons = []
    if _categories_ready() or is_admin(user_id):
        buttons.append([make_btn("🗂 التصنيفات / Categories", callback_data=f"{CAT_LIST_CB}|{initiator_str}", style="success")])
    buttons.append([
        make_btn(get_text(user_id, "premium_packs_btn"), callback_data=f"list_premium|{initiator_str}|0", style="primary"),
        make_btn(get_text(user_id, "regular_packs_btn"), callback_data=f"list_regular|{initiator_str}|0", style="primary"),
    ])
    letters = [chr(ord('A') + i) for i in range(26)]
    row = []
    for i, l in enumerate(letters):
        if i % 7 == 0 and i > 0: buttons.append(row); row = []
        row.append(make_btn(l, callback_data=f"{ALPHA_CB_PREFIX}|{initiator_str}|{l}|0", style="primary"))
    if row: buttons.append(row)
    buttons.append([make_btn("#", callback_data=f"{ALPHA_CB_PREFIX}|{initiator_str}|#|0", style="primary")])
    buttons.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
    return InlineKeyboardMarkup(buttons)

# ========================= Owner Panel =========================
def get_owner_panel_keyboard(user_id):
    s = DB.get("settings", {})
    vs = "✓" if s.get("tutorial_video_id") else "✕"
    fwd = get_forwarding_status_text(user_id)
    sub_on = s.get("force_sub_enabled")
    sub_st = get_text(user_id, "force_sub_on" if sub_on else "force_sub_off")
    ai_on = "✓" if (s.get("ai_enabled") and s.get("ai_api_key")) else "✕"
    pending = len(DB.get("pending_classify", []) or [])
    rows = [
        [make_btn(get_text(user_id, "op_packs"), callback_data="op_packs_menu", style="primary")],
        [make_btn(get_text(user_id, "op_cats"), callback_data="op_cats_menu", style="primary")],
        [make_btn(f"{get_text(user_id, 'op_ai')}: {ai_on}", callback_data="op_ai_menu", style="primary")],
        [make_btn(get_text(user_id, "op_settings"), callback_data="op_settings_menu", style="primary")],
        [make_btn(get_text(user_id, "op_channels"), callback_data="op_channels_menu", style="primary")],
        [make_btn(get_text(user_id, "op_admins"), callback_data="op_admins_menu", style="primary")],
        [make_btn(get_text(user_id, "forwarding_btn", status=fwd), callback_data="toggle_forward", style="primary")],
        [make_btn(f"▶ {vs}", callback_data="manage_video", style="primary"),
         make_btn(f"⚠ {sub_st}", callback_data="owner_settings", style="primary")],
        [make_btn(get_text(user_id, "op_stats_adv"), callback_data="show_adv_stats", style="primary")],
        [make_btn(get_text(user_id, "op_stats"), callback_data="show_stats", style="primary"),
         make_btn(get_text(user_id, "op_banned"), callback_data=SHOW_BANNED, style="danger")],
        [make_btn(get_text(user_id, "op_backup"), callback_data="do_backup", style="success"),
         make_btn(get_text(user_id, "op_broadcast"), callback_data="op_broadcast", style="success")],
    ]
    if pending:
        rows.append([make_btn(get_text(user_id, "scan_review_btn", count=pending),
                              callback_data="pending_review", style="danger")])
    rows.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
    return InlineKeyboardMarkup(rows)

def get_op_packs_menu(user_id):
    return InlineKeyboardMarkup([
        [make_btn("➕ إضافة حزمة", callback_data="op_add", style="success"),
         make_btn("★ إضافة بريميوم", callback_data="op_addpremium", style="success")],
        [make_btn("✎ إعادة تسمية", callback_data="op_rename", style="primary"),
         make_btn("⌫ حذف حزمة", callback_data="op_del", style="danger")],
        [make_btn("🔍 فحص وتنظيف", callback_data="op_scan", style="primary")],
        [make_btn(get_text(user_id, "op_back"), callback_data="owner_panel", style="danger")],
    ])

def get_op_cats_menu(user_id):
    unclassified = sum(1 for p in DB["packs"].values() if not p.get("work"))
    pending = len(DB.get("pending_classify", []) or [])
    rows = [
        [make_btn(get_text(user_id, "op_cats_view"), callback_data=f"{CAT_LIST_CB}|{user_id}", style="primary")],
        [make_btn(get_text(user_id, "op_cats_scan_all"), callback_data="op_scan_all_ai", style="success")],
        [make_btn(get_text(user_id, "op_cats_scan_others"), callback_data="op_scan_others_ai", style="success")],
        [make_btn(get_text(user_id, "op_backfill_btn", count=unclassified), callback_data="op_backfill", style="success")],
        [make_btn(get_text(user_id, "op_cats_bulk_add"), callback_data="op_bulk_cat", style="primary")],
    ]
    if pending:
        rows.append([make_btn(get_text(user_id, "scan_review_btn", count=pending),
                              callback_data="pending_review", style="danger")])
    rows.extend([
        [make_btn(get_text(user_id, "op_cats_add"), callback_data="op_addcat", style="success"),
         make_btn(get_text(user_id, "op_cats_remove"), callback_data="op_removecat", style="danger")],
        [make_btn(get_text(user_id, "op_cats_setcat"), callback_data="op_setcat_info", style="primary")],
        [make_btn(get_text(user_id, "op_cats_setwork"), callback_data="op_setwork_info", style="primary")],
        [make_btn(get_text(user_id, "op_cats_reclassify"), callback_data="op_reclassify_info", style="primary")],
        [make_btn(get_text(user_id, "op_back"), callback_data="owner_panel", style="danger")],
    ])
    return InlineKeyboardMarkup(rows)

def get_op_ai_menu(user_id):
    s = DB.get("settings", {})
    status = "✓" if (s.get("ai_enabled") and s.get("ai_api_key")) else "✕"
    return InlineKeyboardMarkup([
        [make_btn(get_text(user_id, "ai_menu_status", status=status), callback_data="noop", style="primary")],
        [make_btn(get_text(user_id, "ai_menu_on"), callback_data="op_ai_on", style="success"),
         make_btn(get_text(user_id, "ai_menu_off"), callback_data="op_ai_off", style="danger")],
        [make_btn(get_text(user_id, "ai_menu_key"), callback_data="op_ai_setkey", style="primary")],
        [make_btn(get_text(user_id, "ai_menu_model"), callback_data="op_ai_model", style="primary")],
        [make_btn(get_text(user_id, "ai_menu_base"), callback_data="op_ai_base", style="primary")],
        [make_btn(get_text(user_id, "ai_menu_prompt"), callback_data="op_ai_prompt", style="primary")],
        [make_btn(get_text(user_id, "ai_menu_smart"), callback_data="op_ai_smart", style="success")],
        [make_btn(get_text(user_id, "op_back"), callback_data="owner_panel", style="danger")],
    ])

def get_op_settings_menu(user_id):
    return InlineKeyboardMarkup([
        [make_btn("✎ كلمة التنبيه", callback_data="os_set_trigger", style="primary")],
        [make_btn("✎ رابط المجموعة", callback_data="os_set_group", style="primary"),
         make_btn("✎ رابط القناة", callback_data="os_set_channel", style="primary")],
        [make_btn("✎ قناة الاشتراك الإجباري", callback_data="os_set_sub", style="primary")],
        [make_btn(get_text(user_id, "op_back"), callback_data="owner_panel", style="danger")],
    ])

def get_op_channels_menu(user_id):
    s = DB.get("settings", {})
    sub = s.get("force_sub_channel") or "—"
    return InlineKeyboardMarkup([
        [make_btn(f"قناة: {sub}", callback_data="noop", style="primary")],
        [make_btn("✎ تغيير قناة الاشتراك", callback_data="os_set_sub", style="primary")],
        [make_btn("⚙ تشغيل/إيقاف الاشتراك", callback_data="os_toggle_forcesub", style="success")],
        [make_btn(get_text(user_id, "op_back"), callback_data="owner_panel", style="danger")],
    ])

def get_op_admins_menu(user_id):
    admins = DB.get("admins", [])
    rows = []
    for uid in admins[:20]:
        rows.append([make_btn(f"⊘ إزالة {uid}", callback_data=f"op_deladmin|{uid}", style="danger")])
    rows.append([make_btn("➕ إضافة أدمن", callback_data="op_addadmin", style="success")])
    rows.append([make_btn(get_text(user_id, "op_back"), callback_data="owner_panel", style="danger")])
    return InlineKeyboardMarkup(rows)

# ========================= Commands Panel =========================
def get_cmd_panel_keyboard(user_id):
    is_admin_user = is_admin(user_id)
    is_owner = user_id == OWNER_ID
    rows = []
    rows.append([make_btn("🔍 search", callback_data="cp_search", style="primary"),
                 make_btn("🎲 random", callback_data="cp_random", style="success")])
    rows.append([make_btn("⌕ time", callback_data="cp_time", style="primary"),
                 make_btn("⏰ wakeup", callback_data="cp_wakeup", style="primary")])
    rows.append([make_btn("ⓘ help", callback_data="show_help", style="primary")])
    if is_admin_user:
        rows.append([make_btn("➕ add", callback_data="cp_add", style="success"),
                     make_btn("★ addpremium", callback_data="cp_addpremium", style="success")])
        rows.append([make_btn("✎ rename", callback_data="cp_rename", style="primary"),
                     make_btn("⌫ del", callback_data="cp_del", style="danger")])
        rows.append([make_btn("🔍 scan", callback_data="op_scan", style="primary"),
                     make_btn("🔍 scanall", callback_data="op_scan_all_ai", style="primary")])
        rows.append([make_btn("🗂 setcat", callback_data="cp_setcat", style="primary"),
                     make_btn("📺 setwork", callback_data="cp_setwork", style="primary")])
        rows.append([make_btn("🔄 reclassify", callback_data="cp_reclassify", style="primary"),
                     make_btn("🤖 backfill", callback_data="op_backfill", style="primary")])
    if is_owner:
        rows.append([make_btn("📢 broadcast", callback_data="op_broadcast", style="success"),
                     make_btn("⤓ backup", callback_data="do_backup", style="success")])
        rows.append([make_btn("▶ setvideo", callback_data="cp_setvideo", style="primary"),
                     make_btn("⌫ delvideo", callback_data="cp_delvideo", style="primary")])
        rows.append([make_btn("✎ settrigger", callback_data="os_set_trigger", style="primary"),
                     make_btn("✎ setgroup", callback_data="os_set_group", style="primary")])
        rows.append([make_btn("✎ setchannel", callback_data="os_set_channel", style="primary"),
                     make_btn("✎ setsub", callback_data="os_set_sub", style="primary")])
        rows.append([make_btn("⚙ forcesub", callback_data="os_toggle_forcesub", style="primary"),
                     make_btn("👥 addadmin", callback_data="op_addadmin", style="primary")])
        rows.append([make_btn("🗑 deladmin", callback_data="op_admins_menu", style="danger"),
                     make_btn("👥 admins", callback_data="op_admins_menu", style="primary")])
        rows.append([make_btn("🤖 setai", callback_data="op_ai_setkey", style="primary"),
                     make_btn("✓ aion", callback_data="op_ai_on", style="success")])
        rows.append([make_btn("✕ aioff", callback_data="op_ai_off", style="danger"),
                     make_btn("📝 aiprompt", callback_data="op_ai_prompt", style="primary")])
        rows.append([make_btn("🧠 aimodel", callback_data="op_ai_model", style="primary"),
                     make_btn("🌐 aibase", callback_data="op_ai_base", style="primary")])
        rows.append([make_btn("🤖 aismart", callback_data="op_ai_smart", style="success"),
                     make_btn("🎲 randomstats", callback_data="cp_randomstats", style="primary")])
        rows.append([make_btn("🧪 testai", callback_data="cp_testai", style="primary")])
        rows.append([make_btn("🧪 testreact", callback_data="cp_testreact", style="primary")])
    rows.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
    return InlineKeyboardMarkup(rows)

# ========================= Inline Message =========================
def build_inline_message_with_entities(user_id, query, packs, bot_username):
    header = get_text(user_id, "inline_msg_header")
    ql = get_text(user_id, "inline_msg_query_label")
    cl = get_text(user_id, "inline_msg_count_label")
    hint = get_text(user_id, "inline_msg_hint")
    chl = get_text(user_id, "inline_msg_channel_label")
    div = "─────────────────────"
    parts, entities, off = [], [], 0
    def add(t):
        nonlocal off
        if not t: return
        parts.append(t); off += len(t)
    def bold(t):
        nonlocal off
        if not t: return
        s = off; parts.append(t)
        entities.append(MessageEntity(type=MessageEntity.BOLD, offset=s, length=len(t))); off += len(t)
    def code(t):
        nonlocal off
        if not t: return
        s = off; parts.append(t)
        entities.append(MessageEntity(type=MessageEntity.CODE, offset=s, length=len(t))); off += len(t)
    def link(t, url):
        nonlocal off
        if not t or not url: return
        s = off; parts.append(t)
        entities.append(MessageEntity(type=MessageEntity.TEXT_LINK, offset=s, length=len(t), url=url)); off += len(t)
    add("╭" + div + "╮\n"); add("│  "); bold(header); add("\n")
    add("│  "); add(f"{ql} "); code(query); add("\n")
    add("│  "); add(f"{cl} {len(packs)}\n"); add("╰" + div + "╯\n\n")
    for i, pack in enumerate(packs, 1):
        title = pack.get("title", "Pack"); sn = pack.get("set_name", "")
        star = "★ " if is_premium_pack(pack) else "▪ "
        deep = make_deep_link(bot_username, sn, None) if (sn and bot_username) else pack.get("url", "")
        add(f"  {i}. {star}"); link(title, deep); add("\n")
    add("\n" + hint + "\n\n" + div + "\n")
    add(chl + " "); link("@Ahmshy", CHANNEL_URL)
    return "".join(parts), entities

# ========================= Inline Query =========================
async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in DB.get("banned_users", []): return
    query = normalize_query(update.inline_query.query)
    if not query: return
    track_user(user_id); track_search(query, user_id); touch_user(user_id)
    bu = context.bot.username or "Bot"
    filtered = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), query)]
    total = len(filtered)
    if total == 0:
        suggs = find_search_suggestions(query, max_suggestions=5)
        rows = []
        for s in suggs:
            sp = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), normalize_query(s))]
            if sp:
                stext, sent = build_inline_message_with_entities(user_id, s, sp, bu)
                rows.append(InlineQueryResultArticle(
                    id=f"sugg_{s}", title=get_text(user_id, "did_you_mean", word=s),
                    input_message_content=InputTextMessageContent(message_text=stext, entities=sent, disable_web_page_preview=True),
                    description=get_text(user_id, "inline_pack_count_desc", count=len(sp))))
        rows.append(InlineQueryResultArticle(
            id="no_results", title=get_text(user_id, "inline_no_results_title"),
            input_message_content=InputTextMessageContent(get_text(user_id, "inline_no_results_msg", query=html.escape(query)),
                                                          parse_mode="HTML", disable_web_page_preview=True),
            description=get_text(user_id, "inline_no_results_desc")))
        await update.inline_query.answer(rows, cache_time=5); return
    filtered.sort(key=lambda x: x.get("title", "").lower())
    results = []
    ft, fe = build_inline_message_with_entities(user_id, query, filtered, bu)
    results.append(InlineQueryResultArticle(
        id="all", title=get_text(user_id, "inline_all_packs", count=total),
        input_message_content=InputTextMessageContent(message_text=ft, entities=fe, disable_web_page_preview=True),
        description=get_text(user_id, "inline_pack_count_desc", count=total)))
    for i, pack in enumerate(filtered[:50], 1):
        title = pack.get("title", "Pack"); sn = pack.get("set_name", "")
        star = "★ " if is_premium_pack(pack) else "▪ "
        ptitle = get_text(user_id, "inline_pack_item", num=i, title=f"{star}{title}")
        deep = make_deep_link(bu, sn, None) if sn else pack.get("url", "")
        label = get_text(user_id, "inline_pack_label")
        chl = get_text(user_id, "inline_channel_follow")
        hint = get_text(user_id, "inline_msg_hint")
        parts, ents, off = [], [], 0
        def a(t):
            nonlocal off
            if not t: return
            parts.append(t); off += len(t)
        def b(t):
            nonlocal off
            if not t: return
            s = off; parts.append(t)
            ents.append(MessageEntity(type=MessageEntity.BOLD, offset=s, length=len(t))); off += len(t)
        def lk(t, url):
            nonlocal off
            if not t or not url: return
            s = off; parts.append(t)
            ents.append(MessageEntity(type=MessageEntity.TEXT_LINK, offset=s, length=len(t), url=url)); off += len(t)
        a("─────────────────────\n"); b(label); a("\n\n  "); a(star); lk(title, deep)
        a("\n\n  " + hint + "\n─────────────────────\n"); a(chl + " "); lk("@Ahmshy", CHANNEL_URL)
        results.append(InlineQueryResultArticle(
            id=str(i), title=ptitle,
            input_message_content=InputTextMessageContent(message_text="".join(parts), entities=ents, disable_web_page_preview=True),
            description=get_text(user_id, "inline_pack_link_desc")))
    await update.inline_query.answer(results, cache_time=5)

# ========================= Send Pack =========================
async def send_pack_to_user(bot, user_id, set_name, source_chat_id=None, source_message_id=None,
                            auto_delete_seconds=None, show_random_again=False):
    key = set_name.lower()
    pack = DB["packs"].get(key)
    if not pack:
        try:
            st = await bot.get_sticker_set(set_name)
            stype = getattr(st, "sticker_type", "regular")
            is_e = (stype == "custom_emoji")
            title = clean_title(st.title or set_name) or set_name
            pack = {"title": title, "url": f"https://t.me/{'addemoji' if is_e else 'addstickers'}/{set_name}",
                    "set_name": set_name, "is_premium": is_e, "is_emoji": is_e}
        except Exception:
            try: await bot.send_message(chat_id=user_id, text="⚠ Pack not found.")
            except Exception: pass
            return []
    title = pack.get("title", set_name)
    url = pack.get("url", "")
    is_premium = pack.get("is_premium", False)
    sna = pack.get("set_name", set_name)
    buttons = []
    if show_random_again:
        buttons.append([make_btn(get_text(user_id, "random_again_btn"), callback_data="random_pack", style="success")])
    if source_chat_id:
        back_url = make_group_message_url(source_chat_id, source_message_id)
        if not back_url: back_url = await get_group_url(bot, source_chat_id)
        if back_url:
            buttons.append([make_btn(get_text(user_id, "back_to_group_btn"), url=back_url, style="success")])
    if not auto_delete_seconds and not show_random_again:
        buttons.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
    kb = InlineKeyboardMarkup(buttons) if buttons else None
    sent_ids = []
    if is_premium:
        text = f"★ <b>{html.escape(title)}</b>\n\n<a href=\"{url}\">↗ {get_text(user_id, 'open_premium_pack_btn')}</a>"
        try:
            m = await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML",
                                       reply_markup=kb, disable_web_page_preview=True)
            sent_ids.append(m.message_id)
        except Exception: pass
    else:
        try:
            st = await bot.get_sticker_set(sna)
            if st.stickers:
                sm = await bot.send_sticker(chat_id=user_id, sticker=st.stickers[0].file_id)
                sent_ids.append(sm.message_id)
        except Exception: pass
        text = f"▪ <b>{html.escape(title)}</b>\n\n<a href=\"{url}\">↗ {get_text(user_id, 'open_pack_btn')}</a>"
        try:
            m = await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML",
                                       reply_markup=kb, disable_web_page_preview=True)
            sent_ids.append(m.message_id)
        except Exception: pass
    if auto_delete_seconds and sent_ids:
        for mid in sent_ids:
            try: asyncio.create_task(schedule_delete_message(bot, user_id, mid, auto_delete_seconds))
            except Exception: pass
    return sent_ids

# ========================= Main Message Handler =========================
async def handle_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; msg = update.effective_message
    if not user or not msg: return
    if (msg.new_chat_members or msg.left_chat_member or msg.new_chat_title or msg.new_chat_photo
        or msg.delete_chat_photo or msg.group_chat_created or msg.supergroup_chat_created
        or msg.channel_chat_created or msg.migrate_to_chat_id or msg.migrate_from_chat_id
        or msg.pinned_message or msg.video_chat_started or msg.video_chat_ended
        or msg.video_chat_participants_invited or msg.proximity_alert_triggered
        or msg.forum_topic_created or msg.forum_topic_closed or msg.forum_topic_reopened
        or msg.general_forum_topic_hidden or msg.general_forum_topic_unhidden
        or msg.write_access_allowed or msg.chat_owner_changed or msg.chat_background_set):
        return

    user_id = user.id
    is_owner = (user_id == OWNER_ID); is_admin_user = is_admin(user_id)
    text = (msg.text or "").strip(); chat_type = msg.chat.type
    if context.bot.id and user_id == context.bot.id: return
    if user_id in DB.get("banned_users", []) and user_id != OWNER_ID: return
    fmap = context.bot_data.get("forwarded_map", {})
    if msg.reply_to_message and msg.reply_to_message.message_id in fmap: return

    awaiting_keys = ("awaiting_request", "pending_report", "awaiting_easy_search",
                     "awaiting_trigger_name", "awaiting_group_link", "awaiting_channel_link",
                     "awaiting_sub_channel", "awaiting_ai_key", "awaiting_ai_model",
                     "awaiting_ai_base", "awaiting_ai_prompt", "awaiting_broadcast",
                     "awaiting_admin_add", "awaiting_addcat", "awaiting_cmd_search",
                     "awaiting_cmd_addpremium", "awaiting_cmd_rename", "awaiting_cmd_setcat",
                     "awaiting_cmd_setwork")
    if any(context.user_data.get(k) for k in awaiting_keys): return

    if is_owner and context.user_data.get("bulk_cat_active"):
        if context.user_data.get("bulk_cat_waiting_category"):
            return
        cat_id = context.user_data["bulk_cat_active"]
        added_key = _try_extract_pack_from_message(msg, context)
        if added_key:
            pack = DB["packs"].get(added_key)
            if pack:
                pack["category"] = cat_id
                if not pack.get("work"):
                    pack["work"] = pack.get("title", "")
                save_db(DB)
                lst = context.user_data.setdefault("bulk_cat_list", [])
                if added_key not in lst:
                    lst.append(added_key)
                try:
                    await msg.reply_text(
                        get_text(OWNER_ID, "bulk_cat_added_one",
                                 name=html.escape(pack.get("title", added_key)),
                                 count=len(lst)),
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[
                            make_btn(get_text(OWNER_ID, "bulk_done_btn"), callback_data="bulkcat_done", style="success"),
                            make_btn(get_text(OWNER_ID, "bulk_cancel_btn"), callback_data="bulkcat_cancel", style="danger"),
                        ]]))
                except Exception: pass
                return
        return

    is_new = track_user(user_id); touch_user(user_id)
    if is_new and chat_type == "private":
        try:
            ud = get_user_display(user)
            now = _now_makkah().strftime("%Y-%m-%d %H:%M:%S")
            nt = get_text(OWNER_ID, "new_user_notification", user=ud, uid=user_id, date=now, total=len(DB.get("users", [])))
            await context.bot.send_message(chat_id=OWNER_ID, text=nt, parse_mode="HTML")
        except Exception: pass

    if not await check_force_sub(context.bot, user_id):
        if chat_type == "private":
            await send_force_sub_msg(context.bot, msg.chat_id, user_id); return
        else:
            t_low = (text or "").lower(); tn = get_trigger_name()
            if (text and text.startswith("/")) or (tn and t_low.startswith(tn)):
                await send_force_sub_msg(context.bot, msg.chat_id, user_id); return

    solo_text = check_solo_trigger(text) if text else None
    if solo_text is not None:
        clear_chat_quiet(context, msg.chat_id)
        await handle_solo_response(update, context, solo_text); return

    if await is_chat_quiet(context, msg.chat_id):
        if text and text.startswith("/"):
            clear_chat_quiet(context, msg.chat_id)
        else:
            t_low = (text or "").lower().strip()
            is_wake = is_wake_request(text)
            bu_lower = (context.bot.username or "").lower()
            is_mention = bool(bu_lower) and (f"@{bu_lower}" in t_low)
            is_reply_to_bot = (msg.reply_to_message and msg.reply_to_message.from_user
                              and msg.reply_to_message.from_user.id == context.bot.id)
            if is_wake or is_mention or is_reply_to_bot:
                clear_chat_quiet(context, msg.chat_id)
                try: await try_react(context.bot, msg.chat_id, msg.message_id, pick_random_reactions(8, "respect"))
                except Exception: pass
                if is_wake and len(t_low) <= 15 and not is_mention and not is_reply_to_bot:
                    try: await msg.reply_text(get_text(user_id, "wake_reply"))
                    except Exception: pass
                    return
            else:
                return

    op = context.user_data.get("op_pending")
    if is_owner and op and msg.sticker and msg.sticker.set_name:
        sn = msg.sticker.set_name; key = sn.lower()
        if key in DB["packs"]:
            await msg.reply_text("⚠ الحزمة موجودة مسبقاً.")
            context.user_data["op_pending"] = None; return
        try:
            st = await context.bot.get_sticker_set(sn)
            title = clean_title(st.title or sn) or sn
            stype = getattr(st, "sticker_type", "regular"); is_e = (stype == "custom_emoji")
            purl = f"https://t.me/addemoji/{sn}" if is_e else f"https://t.me/addstickers/{sn}"
            is_prem = (op == "addpremium") or is_e
            finalize_new_pack(key, {"title": title, "url": purl, "set_name": sn,
                                    "is_premium": is_prem, "is_emoji": is_e})
            await msg.reply_text(f"✓ تمت الإضافة: <code>{html.escape(title)}</code>\n"
                                 f"{'★ بريميوم' if is_prem else '▪ عادي'}",
                                 parse_mode="HTML",
                                 reply_markup=InlineKeyboardMarkup([[make_btn("◂ لوحة التحكم", callback_data="owner_panel", style="danger")]]))
        except Exception as e:
            await msg.reply_text(f"✕ خطأ: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
        context.user_data["op_pending"] = None; return

    if is_owner:
        pns = context.user_data.get("awaiting_pack_name")
        if pns and text and not text.startswith("/"):
            key = pns.lower(); ex = DB["packs"].get(key, {})
            purl = ex.get("url", f"https://t.me/addstickers/{pns}")
            nt = clean_title(text) or text
            if key not in DB["packs"]:
                finalize_new_pack(key, {"title": nt, "url": purl, "set_name": pns,
                                        "is_premium": ex.get("is_premium", False),
                                        "is_emoji": ex.get("is_emoji", False)})
            else:
                DB["packs"][key]["title"] = nt
                DB["packs"][key]["title_locked"] = True
                save_db(DB)
            await msg.reply_text(f"✓ Name updated: <code>{html.escape(nt)}</code>", parse_mode="HTML")
            context.user_data["awaiting_pack_name"] = None; return

    from_channel = is_channel_message(msg)
    combined = combine_text_and_entity_links(msg)
    if ("addstickers" in combined) or ("addemoji" in combined):
        matches = re.findall(r"(?:t\.me|telegram\.me)/(addstickers|addemoji)/([A-Za-z0-9_]+)", combined)
        seen = set(); uniq = []
        for ut, sn in matches:
            if (ut, sn) not in seen: seen.add((ut, sn)); uniq.append((ut, sn))
        if uniq:
            hidden = has_hidden_pack_link(msg)
            if is_owner:
                as_ = []; ae = []; upg = []; rt = []
                for ut, sn in uniq:
                    kind = "emoji" if ut == "addemoji" else "stickers"
                    st, info, is_e = await add_pack_from_link(context, sn, url_type=kind)
                    if st == "added": (ae if is_e else as_).append((info, sn)); rt.append((info, sn))
                    elif st == "upgraded": upg.append((info, sn)); rt.append((info, sn))
                if as_ or ae or upg:
                    lines = ["⤓ <b>Added packs:</b>", ""]
                    if as_: lines.append(f"▪ Regular ({len(as_)}):"); lines += [f"  ▪ {html.escape(t)}" for t, _ in as_]; lines.append("")
                    if ae: lines.append(f"★ Premium ({len(ae)}):"); lines += [f"  ★ {html.escape(t)}" for t, _ in ae]; lines.append("")
                    if upg: lines.append(f"◆ Upgraded ({len(upg)}):"); lines += [f"  ★ {html.escape(t)}" for t, _ in upg]
                    kb = []
                    for t, sn in rt:
                        label = t if len(t) <= 25 else t[:25] + "..."
                        kb.append([make_btn(f"✎ {label}", callback_data=f"rename_link|{sn}", style="primary")])
                    rm = InlineKeyboardMarkup(kb) if kb else None
                    await msg.reply_text("\n".join(lines).strip(), parse_mode="HTML", reply_markup=rm)
                return
            elif from_channel and hidden:
                for ut, sn in uniq: await process_pack_link_by_source(update, context, ut, sn, False, True)
                return
            else:
                for ut, sn in uniq: await process_pack_link_by_source(update, context, ut, sn, False, False)
                return

    if ((msg.photo or msg.sticker)
        and DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key")):
        should_handle_image = False
        image_prompt = ""
        if chat_type == "private":
            should_handle_image = True
            image_prompt = (msg.caption or "").strip()
        elif chat_type in ("group", "supergroup"):
            bu_lower = (context.bot.username or "").lower()
            caption_low = (msg.caption or "").lower()
            is_mention = bool(bu_lower) and (f"@{bu_lower}" in caption_low)
            is_reply_to_bot = (msg.reply_to_message and msg.reply_to_message.from_user
                              and msg.reply_to_message.from_user.id == context.bot.id)
            solo_caption = check_solo_trigger(msg.caption) if msg.caption else None
            if is_mention or is_reply_to_bot or (solo_caption is not None):
                should_handle_image = True
                clean_cap = msg.caption or ""
                if bu_lower:
                    clean_cap = re.sub(rf"@{re.escape(bu_lower)}\b", "", clean_cap, flags=re.IGNORECASE)
                if solo_caption is not None: clean_cap = solo_caption
                image_prompt = clean_cap.strip()
        if should_handle_image:
            if not (msg.sticker and msg.sticker.set_name and msg.sticker.set_name.lower() not in DB["packs"]):
                image_data = None
                if msg.photo: image_data, _ = await get_file_data_url(context.bot, msg.photo[-1].file_id)
                elif msg.sticker: image_data, _ = await get_file_data_url(context.bot, msg.sticker.file_id, "image/webp")
                if image_data:
                    context.user_data["last_image_data"] = image_data
                    context.user_data["last_image_time"] = _now_makkah().isoformat()
                    reply = await call_ai_with_image(
                        image_prompt or ("صف هذه الصورة بإيجاز." if msg.photo else "صف هذا الملصق بإيجاز."),
                        image_data, context.user_data.get("ai_history"))
                    if reply:
                        reply = sanitize_ai_reply(reply)
                        try:
                            await msg.reply_text(reply)
                            await try_react(context.bot, msg.chat_id, msg.message_id, pick_random_reactions(8, "thinking"))
                        except Exception: pass
                        return

    if msg.sticker and msg.sticker.set_name:
        sn = msg.sticker.set_name; key = sn.lower()
        if key not in DB["packs"]:
            try:
                st = await context.bot.get_sticker_set(sn)
                ts = st.title or sn
                if MY_CHANNEL_ID.lower() in (st.title or "").lower() or MY_CHANNEL_ID.lower() in sn.lower():
                    title = clean_title(ts)
                    stype = getattr(st, "sticker_type", "regular"); is_e = (stype == "custom_emoji")
                    purl = f"https://t.me/addemoji/{sn}" if is_e else f"https://t.me/addstickers/{sn}"
                    if is_owner:
                        if not title:
                            context.user_data["awaiting_pack_name"] = sn
                            await msg.reply_text(get_text(user_id, "enter_name"), parse_mode="HTML"); return
                        finalize_new_pack(key, {"title": title, "url": purl, "set_name": sn,
                                                "is_premium": is_e, "is_emoji": is_e})
                        await msg.reply_text(get_text(user_id, "pack_added_simple", name=html.escape(title)), parse_mode="HTML")
                        return
                    if from_channel:
                        finalize_new_pack(key, {"title": title or sn, "url": purl, "set_name": sn,
                                                "is_premium": is_e, "is_emoji": is_e})
                        return
                    et = escape_markdown(title or "No valid name", version=1)
                    es = escape_markdown(ts, version=1)
                    eu = escape_markdown(user.first_name or "User", version=1)
                    at = get_text(OWNER_ID, "new_pack_detected", user=eu, uid=user.id, src=es, filtered=et)
                    kb = InlineKeyboardMarkup([
                        [make_btn(get_text(OWNER_ID, "save_btn"), callback_data=f"+|{sn}", style="success")],
                        [make_btn(get_text(OWNER_ID, "rename_btn"), callback_data=f"r|{sn}", style="primary"),
                         make_btn(get_text(OWNER_ID, "ignore_btn"), callback_data=f"-|{sn}", style="danger")],
                        [make_btn(get_text(OWNER_ID, "ai_classify_btn"), callback_data=f"{RECLASSIFY_CB}|{sn.lower()}", style="primary")],
                    ])
                    await context.bot.send_sticker(chat_id=OWNER_ID, sticker=msg.sticker.file_id)
                    await context.bot.send_message(chat_id=OWNER_ID, text=at, reply_markup=kb, parse_mode="Markdown")
                    return
            except Exception: pass

    if text and not text.startswith('/'):
        owner_msg = extract_owner_message(text)
        if owner_msg:
            try:
                ud = get_user_display(user)
                notif_text = (f"📩 <b>رسالة للمالك</b>\n\n◎ <b>من:</b> <a href=\"tg://user?id={user_id}\">{ud}</a>\n"
                              f"# <code>{user_id}</code>\n✎ <b>الرسالة:</b> {html.escape(owner_msg)}\n\n"
                              "◂ <i>رد على هذه الرسالة لتوصيل الرد</i>")
                nm = await context.bot.send_message(chat_id=OWNER_ID, text=notif_text,
                                                    parse_mode="HTML", disable_web_page_preview=True)
                context.bot_data.setdefault("forwarded_map", {})[nm.message_id] = user_id
                try: await msg.reply_text("✓ تم إرسال رسالتك للمالك", parse_mode="HTML")
                except Exception: pass
                return
            except Exception as e:
                logging.error(f"tell_owner: {e}")

    if text and not text.startswith('/'):
        t_low = text.lower()
        has_random = any(k in t_low for k in RANDOM_KEYWORDS)
        has_pack = any(k in t_low for k in ["حزمة", "حزمه", "ملصق", "ستيكر", "pack", "sticker"])
        if has_random and has_pack:
            try: await cmd_random(update, context); return
            except Exception as e: logging.error(f"random_intent: {e}")

    if text and not text.startswith('/'):
        t_low = text.lower().strip()
        send_kw = ["ارسلها","أرسلها","ارسلهم","أرسلهم","ارسل لي","أرسل لي","ابعثها","ابعثهم","رسلها","هاتهم","جيبهم","send it","send them","send me"]
        if any(k in t_low for k in send_kw):
            last_packs = context.user_data.get("last_search_packs") or []
            if last_packs:
                sent = 0
                for sn in last_packs[:3]:
                    try:
                        await send_pack_to_user(context.bot, user_id, sn, auto_delete_seconds=AUTO_DELETE_SECONDS)
                        sent += 1
                    except Exception: pass
                if sent > 0: return

    if (DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key")
        and text and not text.startswith('/')):
        should_handle = False
        clean_text = text
        if chat_type == "private":
            should_handle = True
        elif chat_type in ("group", "supergroup"):
            bu_lower = (context.bot.username or "").lower()
            is_mention = bool(bu_lower) and (f"@{bu_lower}" in text.lower())
            is_reply_to_bot = (msg.reply_to_message and msg.reply_to_message.from_user
                              and msg.reply_to_message.from_user.id == context.bot.id)
            if is_mention or is_reply_to_bot:
                should_handle = True
                if bu_lower:
                    clean_text = re.sub(rf"@{re.escape(bu_lower)}\b", "", text, flags=re.IGNORECASE).strip()
        if should_handle and clean_text:
            if is_datetime_question(clean_text):
                dt_info = get_current_datetime_info()
                try:
                    await msg.reply_text(get_datetime_reply(user_id, dt_info), parse_mode="HTML")
                    await try_react(context.bot, msg.chat_id, msg.message_id, pick_random_reactions(5, "happy"))
                except Exception: pass
                return

            intent = detect_user_intent(clean_text)
            if intent in ("greeting", "how_are_you", "thanks", "goodbye"):
                quick = get_quick_reply(intent)
                if quick and len(clean_text) <= 25:
                    try:
                        await msg.reply_text(quick)
                        await try_react(context.bot, msg.chat_id, msg.message_id, pick_random_reactions(5, "happy"))
                    except Exception: pass
                    return

            user_wants_search = has_intent_keyword(clean_text)
            if not user_wants_search:
                q_exact = normalize_query(clean_text)
                for k, v in DB["packs"].items():
                    if normalize_query(v.get("title", "")) == q_exact:
                        user_wants_search = True; break

            if user_wants_search:
                context.user_data["awaiting_pack_query"] = _now_makkah().isoformat()
                try: await try_react(context.bot, msg.chat_id, msg.message_id, pick_random_reactions(6, "cool"))
                except Exception: pass

                aliases, characters, keys = await ai_find_matching_packs(clean_text)
                mi_all, seen_keys = [], set()
                for alias in aliases:
                    q = normalize_query(alias)
                    if not q: continue
                    for k, v in DB["packs"].items():
                        if k in seen_keys: continue
                        if pack_matches_query(v.get("title", ""), q):
                            mi_all.append(v); seen_keys.add(k)
                for char in characters:
                    q = normalize_query(char)
                    if not q: continue
                    for k, v in DB["packs"].items():
                        if k in seen_keys: continue
                        if pack_matches_query(v.get("title", ""), q):
                            mi_all.append(v); seen_keys.add(k)
                for k in keys:
                    if k in seen_keys: continue
                    p = DB["packs"].get(k)
                    if p: mi_all.append(p); seen_keys.add(k)

                if mi_all:
                    mi_all.sort(key=lambda x: x.get("title", "").lower())
                    context.user_data.pop("awaiting_pack_query", None)
                    if await _show_ai_search_results(msg, context, user_id, mi_all, [], clean_text, chat_type):
                        return

                candidates = await ai_extract_search_term(clean_text)
                if candidates:
                    mi2, ei2, used2 = [], [], None
                    for cand in candidates:
                        m_tmp, e_tmp, u_tmp = search_packs_smart(cand)
                        if m_tmp: mi2, ei2, used2 = m_tmp, e_tmp, u_tmp; break
                    if mi2:
                        context.user_data.pop("awaiting_pack_query", None)
                        if await _show_ai_search_results(msg, context, user_id, mi2, ei2, used2 or candidates[0], chat_type):
                            return
                    reply = await call_ai(f"المستخدم طلب: {' / '.join(candidates)}. اعتذر بلطف واطلب زر «طلب حزمة». سطرين.")
                    if reply:
                        reply = sanitize_ai_reply(reply)
                        try:
                            kb = InlineKeyboardMarkup([[make_btn(get_text(user_id, "request_pack_btn"),
                                                                 callback_data="request_pack", style="primary")]])
                            await msg.reply_text(reply, reply_markup=kb)
                            return
                        except Exception: pass

            hist = context.user_data.get("ai_history") or []
            last_img = context.user_data.get("last_image_data")
            last_time = context.user_data.get("last_image_time")
            use_image = False
            if last_img and last_time:
                try:
                    dt = datetime.fromisoformat(last_time)
                    if dt.tzinfo: dt = dt.replace(tzinfo=None)
                    if (_now_makkah().replace(tzinfo=None) - dt) < timedelta(minutes=IMAGE_MEMORY_MINUTES):
                        img_kw = ["ايش","وش","منو","مين","هذا","هذه","الصورة","الشخصية","اللي","الاسم","اسم","وش اسم",
                                  "what","who","this","image","picture","name","character"]
                        if any(k in clean_text.lower() for k in img_kw) or len(clean_text) <= 10:
                            use_image = True
                except Exception: pass
            if use_image:
                reply = await call_ai_with_image(clean_text, last_img, hist)
                context.user_data["last_image_time"] = _now_makkah().isoformat()
            else:
                reply = await call_ai(clean_text, hist)
            if reply:
                reply = sanitize_ai_reply(reply)
                hist.append({"role": "user", "content": clean_text})
                hist.append({"role": "assistant", "content": reply})
                context.user_data["ai_history"] = hist[-AI_MEMORY_SIZE:]
                try:
                    await msg.reply_text(reply)
                    await try_react(context.bot, msg.chat_id, msg.message_id, pick_random_reactions(5, "thinking"))
                except Exception: pass
                return

    if ((not is_owner) and (not is_admin_user) and chat_type == "private"):
        if text and text.startswith('/'):
            try:
                ud = get_user_display(user)
                it = get_text(OWNER_ID, "cmd_from_user", user=ud, uid=user.id, cmd=html.escape(text))
                await context.bot.send_message(chat_id=OWNER_ID, text=it, parse_mode="HTML")
                await msg.forward(chat_id=OWNER_ID)
            except Exception: pass
        else:
            ew = re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", text); pq = None
            if ew:
                cand = " ".join(ew[:3])
                if pack_matches_query_any(cand): pq = cand
                else:
                    for w in ew:
                        if len(w) >= 4 and pack_matches_query_any(w): pq = w; break
            if pq:
                rows = [[make_btn(get_text(user_id, "smart_search_btn", word=pq), callback_data=f"dosearch|{encode_query(pq)}", style="success")],
                        [make_btn(get_text(user_id, "request_pack_btn"), callback_data="request_pack", style="primary")],
                        [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]
                await msg.reply_text(get_text(user_id, "smart_reply_search", word=pq), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))
            elif ew:
                cand = ew[0]
                rows = [[make_btn(get_text(user_id, "smart_search_btn", word=cand), callback_data=f"dosearch|{encode_query(cand)}", style="success")],
                        [make_btn(get_text(user_id, "request_pack_btn"), callback_data="request_pack", style="primary")],
                        [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]
                await msg.reply_text(get_text(user_id, "smart_reply_not_found"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))
            else:
                rows = [[make_btn(get_text(user_id, "request_pack_btn"), callback_data="request_pack", style="primary")],
                        [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]
                await msg.reply_text(get_text(user_id, "smart_reply_default"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))
            if DB["settings"].get("forward_messages", True):
                try:
                    ud = get_user_display(user)
                    it = get_text(OWNER_ID, "msg_from_user", user=ud, uid=user.id)
                    im = await context.bot.send_message(chat_id=OWNER_ID, text=it, parse_mode="HTML")
                    fm = await msg.forward(chat_id=OWNER_ID)
                    context.bot_data.setdefault("forwarded_map", {})[fm.message_id] = user.id
                    context.bot_data["forwarded_map"][im.message_id] = user.id
                except Exception: pass

def _try_extract_pack_from_message(msg, context):
    if msg.sticker and getattr(msg.sticker, "set_name", None):
        sn = msg.sticker.set_name
        key = sn.lower()
        if key not in DB["packs"]:
            return key if key else None
        return key
    combined = combine_text_and_entity_links(msg)
    m = re.search(r"(?:t\.me|telegram\.me)/(?:addstickers|addemoji)/([A-Za-z0-9_]+)", combined or "")
    if m:
        sn = m.group(1)
        return sn.lower()
    return None

# ========================= Callback Handler =========================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    data = query.data or ""
    user_id = query.from_user.id
    chat_type = query.message.chat.type
    if user_id in DB.get("banned_users", []) and user_id != OWNER_ID:
        await query.answer(get_text(user_id, "banned"), show_alert=True); return
    touch_user(user_id)

    if user_id != OWNER_ID and not await check_force_sub(context.bot, user_id):
        await query.answer("⚠ اشترك في القناة أولاً.", show_alert=True)
        await send_force_sub_msg(context.bot, query.message.chat.id, user_id)
        return

    if data == "cmd_panel":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        await query.edit_message_text(get_text(user_id, "cmd_panel_header"),
            reply_markup=get_cmd_panel_keyboard(user_id),
            parse_mode="HTML", disable_web_page_preview=True); return

    if data == "cp_search":
        await query.answer()
        context.user_data["awaiting_cmd_search"] = True
        await query.edit_message_text(
            "🔍 <b>search</b>\n\n▸ أرسل كلمة البحث الآن:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_random":
        await query.answer()
        await cmd_random(update, context)
        return

    if data == "cp_testai":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        s = DB.get("settings", {})
        key = (s.get("ai_api_key") or "").strip()
        model = s.get("ai_model") or "gemini-2.5-flash"
        if model.startswith("models/"): model = model[7:]
        await query.edit_message_text(
            f"🧪 <b>اختبار AI</b>\n\n"
            f"▪ الموديل: <code>{model}</code>\n"
            f"▪ المفتاح: <code>{key[:10]}...</code>\n"
            f"▪ مفعّل: <code>{s.get('ai_enabled')}</code>\n\n"
            f"◷ جاري الإرسال...",
            parse_mode="HTML")
        reply = await call_ai_raw("قل: تم")
        if reply:
            await query.edit_message_text(f"✅ <b>نجح!</b>\n\nالرد: {html.escape(reply)}\n\n▸ الموديل: <code>{model}</code>", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]]))
        else:
            await query.edit_message_text("❌ <b>فشل</b> — انظر الرسالة اللي وصلتك فوق", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]]))
        return

    if data == "cp_time":
        await query.answer()
        await query.edit_message_text(get_datetime_reply(user_id, get_current_datetime_info()),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_wakeup":
        await query.answer()
        clear_chat_quiet(context, query.message.chat.id)
        await query.edit_message_text(get_text(user_id, "wake_reply"),
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_add":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        context.user_data["op_pending"] = "add"
        await query.edit_message_text(
            "➕ <b>add</b>\n\n▸ أرسل ملصقاً الآن، أو الصق رابط الحزمة.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_addpremium":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        context.user_data["awaiting_cmd_addpremium"] = True
        await query.edit_message_text(
            "★ <b>addpremium</b>\n\n▸ أرسل رابط الحزمة الآن:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_rename":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        await query.edit_message_text(
            "✎ <b>rename</b>\n\n▸ ردّ على ملصق ثم اكتب:\n<code>/rename الاسم الجديد</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_del":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        await query.edit_message_text(
            "⌫ <b>del</b>\n\n▸ ردّ على ملصق من الحزمة.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_setcat":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        context.user_data["awaiting_cmd_setcat"] = True
        await query.edit_message_text(
            "🗂 <b>setcat</b>\n\n▸ رد على ملصق ثم أرسل اسم التصنيف:\n<code>anime</code>\n\n"
            "المتاح: " + ", ".join(CATEGORIES.keys()),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_setwork":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        context.user_data["awaiting_cmd_setwork"] = True
        await query.edit_message_text(
            "📺 <b>setwork</b>\n\n▸ رد على ملصق ثم أرسل اسم العمل:\n<code>Naruto</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_reclassify":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        await query.edit_message_text(
            "🔄 <b>reclassify</b>\n\n▸ رد على ملصق.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_setvideo":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        await query.edit_message_text(
            "▶ <b>setvideo</b>\n\n▸ رد على فيديو ثم اكتب <code>/setvideo</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_delvideo":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        DB["settings"]["tutorial_video_id"] = None; save_db(DB)
        await query.edit_message_text(get_text(OWNER_ID, "del_video_success"),
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_randomstats":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        st = DB.get("stats", {}); total = st.get("random_total", 0)
        usage = st.get("random_usage", {}) or {}
        if not usage:
            await query.edit_message_text("⚠ لا يوجد استخدام بعد.",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return
        items = sorted(usage.items(), key=lambda x: -int(x[1].get("count", 0)))
        lines = [f"🎲 <b>Random</b>\n  ▪ المجموع: <code>{total}</code>\n  ⚇ عدد: <code>{len(items)}</code>\n"]
        for i, (uid, d) in enumerate(items[:30], 1):
            un = d.get("name", "User"); uname = f"@{d.get('username')}" if d.get("username") else ""
            cnt = d.get("count", 0)
            lines.append(f"  {i}. {html.escape(un)} {uname} — <code>{uid}</code> → <b>{cnt}</b>")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "cp_testreact":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        sample = pick_random_reactions(15)
        await query.edit_message_text(f"🎨 {' '.join(sample)}", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]])); return

    if data == "owner_panel":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text(get_text(user_id, "owner_panel_header") + "\n▸ اختر:",
            reply_markup=get_owner_panel_keyboard(user_id),
            parse_mode="HTML", disable_web_page_preview=True); return

    if data == "op_packs_menu":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text(get_text(user_id, "op_packs_header"),
            reply_markup=get_op_packs_menu(user_id), parse_mode="HTML"); return

    if data == "op_cats_menu":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text(get_text(user_id, "op_cats_header"),
            reply_markup=get_op_cats_menu(user_id), parse_mode="HTML"); return

    if data == "op_ai_menu":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text(get_text(user_id, "op_ai_header"),
            reply_markup=get_op_ai_menu(user_id), parse_mode="HTML"); return

    if data == "op_settings_menu":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text(get_text(user_id, "op_settings_header"),
            reply_markup=get_op_settings_menu(user_id), parse_mode="HTML"); return

    if data == "op_channels_menu":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text(get_text(user_id, "op_channels_header"),
            reply_markup=get_op_channels_menu(user_id), parse_mode="HTML"); return

    if data == "op_admins_menu":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        admins = DB.get("admins", [])
        if not admins:
            txt = f"{get_text(user_id, 'op_admins_header')}\n\n{get_text(user_id, 'no_admins')}"
        else:
            lines = [get_text(user_id, "op_admins_header"), ""]
            for i, uid in enumerate(admins, 1):
                try:
                    c = await context.bot.get_chat(uid); un = get_user_display(c)
                    uname = f" @{c.username}" if getattr(c, "username", None) else ""
                except Exception: un, uname = "Unknown", ""
                lines.append(f"  {i}. {un}{uname} — <code>{uid}</code>")
            txt = "\n".join(lines)
        await query.edit_message_text(txt, parse_mode="HTML",
            reply_markup=get_op_admins_menu(user_id)); return

    if data == "op_addadmin":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_admin_add"] = True
        await query.edit_message_text(get_text(user_id, "ask_add_admin"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_admins_menu", style="danger")]])); return

    if data.startswith("op_deladmin|"):
        if user_id != OWNER_ID: await query.answer(); return
        uid = int(data.split("|")[1])
        if uid in DB.get("admins", []):
            DB["admins"].remove(uid); save_db(DB)
            await query.answer("✓ تم الإزالة", show_alert=True)
            admins = DB.get("admins", [])
            if not admins:
                txt = f"{get_text(user_id, 'op_admins_header')}\n\n{get_text(user_id, 'no_admins')}"
            else:
                lines = [get_text(user_id, "op_admins_header"), ""]
                for i, u in enumerate(admins, 1): lines.append(f"  {i}. <code>{u}</code>")
                txt = "\n".join(lines)
            await query.edit_message_text(txt, parse_mode="HTML",
                reply_markup=get_op_admins_menu(user_id))
        else: await query.answer("⚠ ليس أدمن", show_alert=True)
        return

    if data == "op_add":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["op_pending"] = "add"
        await query.edit_message_text("➕ <b>إضافة حزمة</b>\n\n▸ أرسل ملصقاً أو رابطاً",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_packs_menu", style="danger")]])); return

    if data == "op_addpremium":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["op_pending"] = "addpremium"
        await query.edit_message_text("★ <b>إضافة بريميوم</b>\n\n▸ أرسل ملصقاً",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_packs_menu", style="danger")]])); return

    if data == "op_rename":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text("✎ <b>إعادة تسمية</b>\n\n▸ رد على ملصق بـ <code>/rename الاسم</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_packs_menu", style="danger")]])); return

    if data == "op_del":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text("⌫ <b>حذف حزمة</b>\n\n▸ رد على ملصق بـ <code>/del</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_packs_menu", style="danger")]])); return

    if data == "op_scan":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer("⌕")
        deleted = updated = unchanged = 0
        packs = DB["packs"]; ktd = []
        for k, p in packs.items():
            o = p.get("title", ""); c = clean_title(o)
            if c != o:
                if c.strip() == "": ktd.append(k); deleted += 1
                else: packs[k]["title"] = c; updated += 1
            else: unchanged += 1
        for k in ktd: del packs[k]
        save_db(DB)
        await query.edit_message_text(get_text(user_id, "scan_complete", deleted=deleted, updated=updated, unchanged=unchanged),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_packs_menu", style="danger")]])); return

    if data == "op_ai_on":
        if user_id != OWNER_ID: await query.answer(); return
        if not DB["settings"].get("ai_api_key"):
            await query.answer("⚠ ضع المفتاح أولاً", show_alert=True); return
        DB["settings"]["ai_enabled"] = True; save_db(DB)
        await query.answer("✓ تم التشغيل", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=get_op_ai_menu(user_id)); return

    if data == "op_ai_off":
        if user_id != OWNER_ID: await query.answer(); return
        DB["settings"]["ai_enabled"] = False; save_db(DB)
        await query.answer("✓ تم الإيقاف", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=get_op_ai_menu(user_id)); return

    if data == "op_ai_setkey":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_ai_key"] = True
        await query.edit_message_text(get_text(user_id, "ask_ai_key"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_ai_menu", style="danger")]])); return

    if data == "op_ai_model":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_ai_model"] = True
        cur = DB["settings"].get("ai_model", "")
        await query.edit_message_text(f"{get_text(user_id, 'ask_ai_model')}\n▸ الحالي: <code>{html.escape(cur)}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_ai_menu", style="danger")]])); return

    if data == "op_ai_base":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_ai_base"] = True
        cur = DB["settings"].get("ai_base_url", "")
        await query.edit_message_text(f"{get_text(user_id, 'ask_ai_base')}\n▸ الحالي: <code>{html.escape(cur)}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_ai_menu", style="danger")]])); return

    if data == "op_ai_prompt":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_ai_prompt"] = True
        await query.edit_message_text(get_text(user_id, "ask_ai_prompt"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_ai_menu", style="danger")]])); return

    if data == "op_ai_smart":
        if user_id != OWNER_ID: await query.answer(); return
        DB["settings"]["ai_system_prompt"] = SMART_SYSTEM_PROMPT; save_db(DB)
        await query.answer("✓ تم التطبيق", show_alert=True); return

    if data == "op_broadcast":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_broadcast"] = True
        await query.edit_message_text("📢 أرسل الرسالة.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="owner_panel", style="danger")]])); return

    if data == "op_setcat_info":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text("✎ <b>ضبط تصنيف</b>\n\n▸ رد على ملصق بـ <code>/setcat anime</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]])); return

    if data == "op_setwork_info":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text("✎ <b>ضبط عمل</b>\n\n▸ رد على ملصق بـ <code>/setwork Naruto</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]])); return

    if data == "op_reclassify_info":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text("🔄 رد على ملصق بـ <code>/reclassify</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]])); return

    if data == "op_bulk_cat":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        await query.edit_message_text(get_text(user_id, "bulk_cat_choose"),
            parse_mode="HTML",
            reply_markup=build_bulk_cat_keyboard()); return

    if data.startswith("bulkcat|"):
        if user_id != OWNER_ID: await query.answer(); return
        cid = data.split("|", 1)[1]
        if cid not in CATEGORIES:
            await query.answer("⚠", show_alert=True); return
        await query.answer()
        context.user_data["bulk_cat_active"] = cid
        context.user_data["bulk_cat_list"] = []
        label = get_category_label(cid, user_id)
        await query.edit_message_text(
            get_text(user_id, "bulk_cat_ask_packs", label=label, count=0),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                make_btn(get_text(user_id, "bulk_done_btn"), callback_data="bulkcat_done", style="success"),
                make_btn(get_text(user_id, "bulk_cancel_btn"), callback_data="bulkcat_cancel", style="danger"),
            ]])); return

    if data == "bulkcat_done":
        if user_id != OWNER_ID: await query.answer(); return
        cat_id = context.user_data.pop("bulk_cat_active", None)
        lst = context.user_data.pop("bulk_cat_list", [])
        await query.answer("✓")
        if not cat_id:
            await query.edit_message_text("⚠ لا يوجد تصنيف نشط."); return
        label = get_category_label(cat_id, user_id)
        if not lst:
            await query.edit_message_text(get_text(user_id, "bulk_cat_empty"),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]])); return
        await query.edit_message_text(
            get_text(user_id, "bulk_cat_finish", label=label, count=len(lst)),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]])); return

    if data == "bulkcat_cancel":
        if user_id != OWNER_ID: await query.answer(); return
        context.user_data.pop("bulk_cat_active", None)
        context.user_data.pop("bulk_cat_list", None)
        await query.answer("✕")
        await query.edit_message_text(get_text(user_id, "bulk_cat_cancelled"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]])); return

    if data in ("op_scan_all_ai", "op_scan_others_ai"):
        if user_id != OWNER_ID: await query.answer(); return
        if not (DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key")):
            await query.answer(get_text(user_id, "scan_all_need_ai"), show_alert=True); return
        await query.answer("🤖 بدء الفحص...")
        context.bot_data["stop_scan"] = False
        scan_all = (data == "op_scan_all_ai")
        if scan_all:
            all_packs = list(DB["packs"].items())
        else:
            all_packs = [(k, p) for k, p in DB["packs"].items() if not p.get("work")]
        if not all_packs:
            await query.edit_message_text(get_text(user_id, "ai_backfill_none"), parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]])); return
        total = len(all_packs)
        start_key = "scan_all_started" if scan_all else "scan_others_started"
        await query.edit_message_text(
            get_text(user_id, start_key, count=total, bar=make_progress_bar(0, total), done=0),
            parse_mode="HTML")
        ok = 0; fail = 0; renamed = 0
        BATCH = CLASSIFY_BATCH_SIZE
        for start_i in range(0, total, BATCH):
            if context.bot_data.get("stop_scan"):
                context.bot_data["stop_scan"] = False
                save_db(DB)
                try:
                    await query.edit_message_text(
                        get_text(user_id, "scan_stopped",
                                 bar=make_progress_bar(start_i, total),
                                 done=start_i, total=total, ok=ok),
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"),
                                                                     callback_data="op_cats_menu", style="danger")]]))
                except Exception: pass
                return
            batch = all_packs[start_i:start_i + BATCH]
            titles = [(k, p.get("title", "")) for k, p in batch]
            results = await ai_classify_batch(titles, suggest_names=True)
            for k, pack in batch:
                res = results.get(k)
                if res:
                    pack["category"] = res["category"]
                    pack["work"] = res["work"]
                    pack["character"] = res.get("character") or _normalize_character(pack.get("title", ""), res["work"], "")
                    if res.get("suggested_name") and res["suggested_name"] != pack.get("title"):
                        pack["title"] = res["suggested_name"]
                        renamed += 1
                    ok += 1
                else:
                    fail += 1
            done = min(start_i + BATCH, total)
            save_db(DB)
            try:
                await query.edit_message_text(
                    get_text(user_id, "scan_all_progress", done=done, total=total, ok=ok, fail=fail,
                             bar=make_progress_bar(done, total)),
                    parse_mode="HTML")
            except Exception: pass
            if done < total:
                await asyncio.sleep(CLASSIFY_SLEEP_BETWEEN)
        save_db(DB)
        try:
            await query.edit_message_text(
                get_text(user_id, "scan_all_done", total=total, ok=ok, renamed=renamed, fail=fail),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"),
                                                             callback_data="op_cats_menu", style="danger")]]))
        except Exception: pass
        return

    if data == "op_addcat":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_addcat"] = True
        await query.edit_message_text(get_text(user_id, "ask_addcat_format"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"),
                                                         callback_data="op_cats_menu", style="danger")]])); return

    if data == "op_removecat":
        if user_id != OWNER_ID: await query.answer(); return
        custom = DB.get("custom_categories", {}) or {}
        if not custom:
            await query.answer(get_text(user_id, "no_custom_cats"), show_alert=True); return
        await query.answer()
        rows = []
        for cid, cat in custom.items():
            label = f"{cat['emoji']} {cat.get('ar', '')} / {cat.get('en', '')}"
            rows.append([make_btn(f"🗑 {label}", callback_data=f"rmcat|{cid}", style="danger")])
        rows.append([make_btn(get_text(user_id, "op_back"),
                              callback_data="op_cats_menu", style="danger")])
        await query.edit_message_text("🗑 <b>حذف تصنيف مخصص:</b>",
            reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML"); return

    if data.startswith("rmcat|"):
        if user_id != OWNER_ID: await query.answer(); return
        cid = data.split("|", 1)[1]
        custom = DB.get("custom_categories", {}) or {}
        if cid in custom:
            cat = custom[cid]
            label = f"{cat['emoji']} {cat.get('ar', '')} / {cat.get('en', '')}"
            del custom[cid]; DB["custom_categories"] = custom
            CATEGORIES.pop(cid, None)
            for p in DB["packs"].values():
                if get_pack_category(p) == cid: p["category"] = "other"
            save_db(DB)
            await query.answer(get_text(OWNER_ID, "cat_removed", label=label), show_alert=True)
        await query.edit_message_text(get_text(user_id, "op_cats_header"),
            reply_markup=get_op_cats_menu(user_id), parse_mode="HTML"); return

    if data == "pending_review":
        if user_id != OWNER_ID: await query.answer(); return
        pending = DB.get("pending_classify", []) or []
        if not pending:
            await query.answer(get_text(user_id, "pending_classify_none"), show_alert=True); return
        await query.answer()
        next_pk = pending[0]
        pack = DB["packs"].get(next_pk)
        if not pack:
            pending.pop(0); DB["pending_classify"] = pending; save_db(DB)
            await query.edit_message_text("⚠"); return
        await query.edit_message_text(
            get_text(user_id, "notif_pack_classify_ask", pack=html.escape(pack.get("title", next_pk))),
            parse_mode="HTML",
            reply_markup=build_pending_classify_keyboard(pack_key=next_pk, bulk=False)); return

    if data == "pending_bulk_start":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        pending = DB.get("pending_classify", []) or []
        await query.edit_message_text(
            get_text(user_id, "pending_classify_bulk_header", count=len(pending)),
            parse_mode="HTML",
            reply_markup=build_pending_classify_keyboard(bulk=True)); return

    if data.startswith("clscat|"):
        if user_id != OWNER_ID: await query.answer(); return
        parts = data.split("|")
        if len(parts) < 3: await query.answer(); return
        pk, cid = parts[1], parts[2]
        if pk not in DB["packs"] or cid not in CATEGORIES:
            await query.answer("⚠ خطأ", show_alert=True); return
        DB["packs"][pk]["category"] = cid
        if not DB["packs"][pk].get("work"):
            DB["packs"][pk]["work"] = DB["packs"][pk].get("title", "")
        pending = DB.get("pending_classify", []) or []
        if pk in pending: pending.remove(pk)
        DB["pending_classify"] = pending
        save_db(DB)
        await query.answer(get_text(OWNER_ID, "category_set",
                                    label=get_category_label(cid, OWNER_ID)), show_alert=True)
        if pending:
            next_pk = pending[0]
            next_pack = DB["packs"].get(next_pk)
            if next_pack:
                await query.edit_message_text(
                    get_text(OWNER_ID, "notif_pack_classify_ask", pack=html.escape(next_pack.get("title", next_pk))),
                    parse_mode="HTML",
                    reply_markup=build_pending_classify_keyboard(pack_key=next_pk, bulk=False))
                return
        await query.edit_message_text("✓ <b>انتهت القائمة.</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "op_back"),
                                                         callback_data="owner_panel", style="danger")]])); return

    if data.startswith("clscat_skip|"):
        if user_id != OWNER_ID: await query.answer(); return
        pk = data.split("|", 1)[1]
        pending = DB.get("pending_classify", []) or []
        if pk in pending: pending.remove(pk)
        DB["pending_classify"] = pending
        save_db(DB)
        await query.answer("⏭")
        if pending:
            next_pk = pending[0]
            next_pack = DB["packs"].get(next_pk)
            if next_pack:
                await query.edit_message_text(
                    get_text(OWNER_ID, "notif_pack_classify_ask", pack=html.escape(next_pack.get("title", next_pk))),
                    parse_mode="HTML",
                    reply_markup=build_pending_classify_keyboard(pack_key=next_pk, bulk=False))
                return
        await query.edit_message_text("✓ <b>انتهت القائمة.</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "op_back"),
                                                         callback_data="owner_panel", style="danger")]])); return

    if data.startswith("clscat_bulk|"):
        if user_id != OWNER_ID: await query.answer(); return
        cid = data.split("|", 1)[1]
        if cid not in CATEGORIES:
            await query.answer("⚠", show_alert=True); return
        pending = DB.get("pending_classify", []) or []
        count = 0
        for pk in pending:
            pack = DB["packs"].get(pk)
            if not pack: continue
            pack["category"] = cid
            if not pack.get("work"):
                pack["work"] = pack.get("title", "")
            count += 1
        DB["pending_classify"] = []
        save_db(DB)
        label = get_category_label(cid, OWNER_ID)
        await query.answer(get_text(OWNER_ID, "pending_classify_all_set", count=count, label=label),
                           show_alert=True)
        await query.edit_message_text(
            get_text(OWNER_ID, "pending_classify_all_set", count=count, label=label),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "op_back"),
                                                         callback_data="owner_panel", style="danger")]])); return

    if data == "clscat_skipall":
        if user_id != OWNER_ID: await query.answer(); return
        DB["pending_classify"] = []
        save_db(DB)
        await query.edit_message_text("✓ <b>تم التخطي.</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "op_back"),
                                                         callback_data="owner_panel", style="danger")]])); return

    if data.startswith(f"{RECLASSIFY_CB}|"):
        if user_id != OWNER_ID: await query.answer(); return
        pk = data.split("|", 1)[1]
        await query.answer(get_text(OWNER_ID, "ai_classifying"))
        pack = DB["packs"].get(pk)
        if not pack:
            await query.edit_message_text("⚠"); return
        old = pack.get("title", "")
        res = await ai_classify_pack(old, suggest_name=True)
        if not res:
            await query.edit_message_text(get_text(OWNER_ID, "ai_classify_fail"), parse_mode="HTML"); return
        pack["category"] = res["category"]
        pack["work"] = res["work"]
        pack["character"] = res.get("character") or _normalize_character(old, res["work"], "")
        renamed_note = ""
        if res.get("suggested_name") and res["suggested_name"] != old:
            pack["title"] = res["suggested_name"]
            renamed_note = "\n" + get_text(OWNER_ID, "suggested_name_changed",
                                           old=html.escape(old), new=html.escape(res["suggested_name"]))
        save_db(DB)
        label = get_category_label(res["category"], OWNER_ID)
        await query.edit_message_text(
            get_text(OWNER_ID, "reclassify_done", label=label, work=html.escape(res["work"]),
                     character=html.escape(res.get("character") or "—")) + renamed_note,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                make_btn("✓ تمام", callback_data="noop", style="success"),
                make_btn(get_text(OWNER_ID, "ai_reclassify_btn"), callback_data=f"{RECLASSIFY_CB}|{pk}", style="primary"),
            ]])); return

    if data == "op_backfill":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        if not (DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key")):
            await query.answer(get_text(OWNER_ID, "scan_all_need_ai"), show_alert=True); return
        context.bot_data["stop_scan"] = False
        todo = [(k, p) for k, p in DB["packs"].items() if not p.get("work")]
        if not todo:
            await query.edit_message_text(get_text(OWNER_ID, "ai_backfill_none"), parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]])); return
        total = len(todo)
        await query.edit_message_text(get_text(OWNER_ID, "ai_backfill_started", count=total), parse_mode="HTML")
        ok = 0
        BATCH = CLASSIFY_BATCH_SIZE
        for start_i in range(0, total, BATCH):
            if context.bot_data.get("stop_scan"):
                context.bot_data["stop_scan"] = False
                save_db(DB)
                try:
                    await query.edit_message_text(
                        get_text(OWNER_ID, "scan_stopped", bar=make_progress_bar(start_i, total),
                                 done=start_i, total=total, ok=ok),
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]]))
                except Exception: pass
                return
            batch = todo[start_i:start_i + BATCH]
            titles = [(k, p.get("title", "")) for k, p in batch]
            results = await ai_classify_batch(titles, suggest_names=True)
            for k, pack in batch:
                res = results.get(k)
                if res:
                    pack["category"] = res["category"]
                    pack["work"] = res["work"]
                    pack["character"] = res.get("character") or _normalize_character(pack.get("title", ""), res["work"], "")
                    if res.get("suggested_name") and res["suggested_name"] != pack.get("title"):
                        pack["title"] = res["suggested_name"]
                    ok += 1
            done = min(start_i + BATCH, total)
            save_db(DB)
            try:
                await query.edit_message_text(
                    get_text(OWNER_ID, "ai_backfill_progress", done=done, total=total, ok=ok),
                    parse_mode="HTML")
            except Exception: pass
            if done < total:
                await asyncio.sleep(CLASSIFY_SLEEP_BETWEEN)
        save_db(DB)
        try:
            await query.edit_message_text(get_text(OWNER_ID, "ai_backfill_done", ok=ok, total=total),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_cats_menu", style="danger")]]))
        except Exception: pass
        return

    if data.startswith(f"{CAT_LIST_CB}|"):
        ins = data.split("|")[1]
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        if not _categories_ready() and not is_admin(user_id):
            await query.answer("⚠ التصنيفات قيد التجهيز...", show_alert=True); return
        await query.answer()
        kb = build_categories_keyboard(user_id, ins)
        await query.edit_message_text(get_text(user_id, "categories_header"),
            reply_markup=kb, parse_mode="HTML"); return

    if data.startswith(f"{CAT_WORKS_CB}|"):
        parts = data.split("|")
        if len(parts) < 3: await query.answer(); return
        ins, cat_id = parts[1], parts[2]
        try: pg = int(parts[3]) if len(parts) > 3 else 0
        except Exception: pg = 0
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        if cat_id not in CATEGORIES:
            await query.answer("⚠ تصنيف غير معروف", show_alert=True); return
        await query.answer()

        if not category_has_works(cat_id):
            ai = [p for p in DB["packs"].values() if get_pack_category(p) == cat_id]
            ai.sort(key=lambda x: x.get("title", "").lower())
            if not ai:
                await query.answer(get_text(user_id, "no_packs_in_category"), show_alert=True); return
            kb, total = build_search_keyboard_for_group(ai, pg, user_id, ins, chat_type, source="search",
                nav_prefix=f"{CAT_FILTER_CB}|{ins}|{cat_id}",
                bot_username=context.bot.username,
                group_chat_id=query.message.chat.id if chat_type != "private" else None)
            rows = list(kb.inline_keyboard)
            rows.insert(-1, [make_btn(get_text(user_id, "cat_back_cats"),
                callback_data=f"{CAT_LIST_CB}|{ins}", style="danger")])
            label = get_category_label(cat_id, user_id)
            await query.edit_message_text(get_text(user_id, "category_packs_header", label=label, count=total),
                reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML", disable_web_page_preview=True)
            return

        works = get_works_in_category(cat_id)
        if not works:
            await query.answer(get_text(user_id, "no_works_in_category"), show_alert=True); return
        kb, total_works = build_works_keyboard(user_id, ins, cat_id, page=pg)
        label = get_category_label(cat_id, user_id)
        await query.edit_message_text(
            get_text(user_id, "category_works_header", label=label, count=total_works),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith(f"{WORK_CB}|"):
        parts = data.split("|")
        if len(parts) < 5: await query.answer(); return
        ins, cat_id, wk = parts[1], parts[2], parts[3]
        try: pg = int(parts[4])
        except Exception: pg = 0
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        await query.answer()
        wn = get_cached_query(wk)
        if not wn:
            await query.answer("⚠ خطأ في المفتاح", show_alert=True); return
        packs = get_packs_in_work(cat_id, wn)
        packs.sort(key=lambda x: x.get("title", "").lower())
        total = len(packs)
        if total == 0:
            await query.answer("⚠ لا توجد حزم", show_alert=True); return
        kb, _ = build_search_keyboard_for_group(packs, pg, user_id, ins, chat_type, source="search",
            nav_prefix=f"{WORK_CB}|{ins}|{cat_id}|{wk}",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        rows = list(kb.inline_keyboard)
        rows.insert(-1, [make_btn(get_text(user_id, "cat_back_works"),
            callback_data=f"{CAT_WORKS_CB}|{ins}|{cat_id}|0", style="danger")])
        await query.edit_message_text(
            get_text(user_id, "work_packs_header", work=html.escape(wn), count=total),
            reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith(f"{CAT_LETTER_CB}|"):
        parts = data.split("|")
        if len(parts) < 6: await query.answer(); return
        ins, cid, lt = parts[1], parts[2], parts[3]
        try: pg = int(parts[4])
        except Exception: pg = 0
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        await query.answer()
        base = [p for p in DB["packs"].values() if get_pack_category(p) == cid]
        if lt == "#": ai = [p for p in base if not re.match(r'^[a-zA-Z]', p.get("title", ""))]
        else: ai = [p for p in base if p.get("title", "").lower().startswith(lt.lower())]
        ai.sort(key=lambda x: x.get("title", "").lower())
        total = len(ai)
        if total == 0:
            await query.answer(get_text(user_id, "no_packs_letter", letter=lt.upper()), show_alert=True); return
        kb, _ = build_search_keyboard_for_group(ai, pg, user_id, ins, chat_type, source="search",
            nav_prefix=f"{CAT_LETTER_CB}|{ins}|{cid}|{lt}",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        rows = list(kb.inline_keyboard)
        rows.insert(-1, [make_btn(get_text(user_id, "cat_back_works"),
            callback_data=f"{CAT_WORKS_CB}|{ins}|{cid}|0", style="danger")])
        label = get_category_label(cid, user_id)
        await query.edit_message_text(get_text(user_id, "category_packs_header", label=label, count=total),
            reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith(f"{CAT_FILTER_CB}|"):
        parts = data.split("|")
        if len(parts) < 4: await query.answer(); return
        ins, cat_id = parts[1], parts[2]
        try: pg = int(parts[3])
        except Exception: pg = 0
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        await query.answer()
        ai = [p for p in DB["packs"].values() if get_pack_category(p) == cat_id]
        ai.sort(key=lambda x: x.get("title", "").lower())
        if not ai:
            await query.answer(get_text(user_id, "no_packs_in_category"), show_alert=True); return
        kb, total = build_search_keyboard_for_group(ai, pg, user_id, ins, chat_type, source="search",
            nav_prefix=f"{CAT_FILTER_CB}|{ins}|{cat_id}",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        rows = list(kb.inline_keyboard)
        rows.insert(-1, [make_btn(get_text(user_id, "cat_back_works"),
            callback_data=f"{CAT_WORKS_CB}|{ins}|{cat_id}|0", style="danger")])
        label = get_category_label(cat_id, user_id)
        await query.edit_message_text(get_text(user_id, "category_packs_header", label=label, count=total),
            reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML", disable_web_page_preview=True); return

    if data == "noop":
        await query.answer(); return

    if data.startswith(f"{SHOWSETCAT_CB}|"):
        if user_id != OWNER_ID: await query.answer(); return
        pk = data.split("|", 1)[1]
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=build_setcat_keyboard(pk)); return

    if data.startswith(f"{SETCAT_CB}|"):
        if user_id != OWNER_ID: await query.answer(); return
        parts = data.split("|")
        if len(parts) < 3: await query.answer(); return
        pk, cid = parts[1], parts[2]
        if cid not in CATEGORIES or pk not in DB["packs"]:
            await query.answer("⚠", show_alert=True); return
        DB["packs"][pk]["category"] = cid; save_db(DB)
        await query.answer(get_text(OWNER_ID, "category_set", label=get_category_label(cid, OWNER_ID)), show_alert=True)
        try: await query.edit_message_reply_markup(reply_markup=None)
        except Exception: pass
        return

    if data == "show_adv_stats":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        kb = InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]])
        await query.edit_message_text(get_advanced_stats_text(user_id),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data == "owner_settings":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        await query.edit_message_text(get_owner_settings_text(user_id),
            reply_markup=get_owner_settings_keyboard(user_id),
            parse_mode="HTML", disable_web_page_preview=True); return

    if data == "os_set_trigger":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_trigger_name"] = True
        await query.edit_message_text(get_text(OWNER_ID, "ask_trigger_name"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "op_back"), callback_data="op_settings_menu", style="danger")]])); return

    if data == "os_set_group":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_group_link"] = True
        await query.edit_message_text(get_text(OWNER_ID, "ask_group_link"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "op_back"), callback_data="op_settings_menu", style="danger")]])); return

    if data == "os_set_channel":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_channel_link"] = True
        await query.edit_message_text(get_text(OWNER_ID, "ask_channel_link"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "op_back"), callback_data="op_settings_menu", style="danger")]])); return

    if data == "os_set_sub":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        context.user_data["awaiting_sub_channel"] = True
        await query.edit_message_text(get_text(OWNER_ID, "ask_sub_channel"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "op_back"), callback_data="op_channels_menu", style="danger")]])); return

    if data == "os_toggle_forcesub":
        if user_id != OWNER_ID: await query.answer(); return
        s = DB["settings"]
        if not s.get("force_sub_channel"):
            await query.answer(get_text(OWNER_ID, "need_sub_channel_first"), show_alert=True); return
        s["force_sub_enabled"] = not s.get("force_sub_enabled", False)
        save_db(DB)
        msg_key = "force_sub_enabled_msg" if s["force_sub_enabled"] else "force_sub_disabled_msg"
        await query.answer(get_text(OWNER_ID, msg_key), show_alert=True)
        await query.edit_message_text(get_owner_settings_text(OWNER_ID),
            reply_markup=get_owner_settings_keyboard(OWNER_ID),
            parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith(f"{OPENPACK_CB}|"):
        parts = data.split("|", 2)
        if len(parts) < 3: await query.answer(); return
        initiator_str = parts[1]; key = parts[2]
        pack = DB["packs"].get(key)
        if not pack:
            await query.answer(get_text(user_id, "pack_not_found_short"), show_alert=True); return
        try: track_pack_visit(key)
        except Exception: pass
        sna = pack.get("set_name", "")
        cct = query.message.chat.type; ccid = query.message.chat.id; cmid = query.message.message_id
        if cct == "private":
            await query.answer()
            try: await send_pack_to_user(context.bot, user_id, sna, auto_delete_seconds=AUTO_DELETE_SECONDS)
            except Exception: pass
            return
        purl = pack.get("url", "")
        if not purl and sna:
            is_e = bool(pack.get("is_emoji") or pack.get("is_premium"))
            purl = f"https://t.me/{'addemoji' if is_e else 'addstickers'}/{sna}"
        turl = make_deep_link(context.bot.username, sna, ccid, cmid) or purl
        try: await query.answer(url=turl)
        except Exception:
            await query.answer()
            try:
                await context.bot.send_message(chat_id=user_id,
                    text=f"↗ <a href=\"{turl}\">Open</a>", parse_mode="HTML",
                    disable_web_page_preview=True)
            except Exception: pass
        return

    if data == "random_pack":
        await query.answer()
        packs = list(DB["packs"].values())
        if not packs:
            await query.answer(get_text(user_id, "no_packs_yet"), show_alert=True); return
        prev_msgs = context.user_data.get("last_random_msgs", []) or []
        for mid in prev_msgs:
            try: await context.bot.delete_message(chat_id=user_id, message_id=mid)
            except Exception: pass
        context.user_data["last_random_msgs"] = []
        pack = random.choice(packs)
        sn = pack.get("set_name", "")
        if not sn:
            await query.answer(get_text(user_id, "pack_not_found_short"), show_alert=True); return
        try: track_pack_visit(sn.lower())
        except Exception: pass
        try: track_random_usage(query.from_user, chat_type)
        except Exception: pass
        if chat_type == "private":
            try:
                sent = await send_pack_to_user(context.bot, user_id, sn, show_random_again=True)
                context.user_data["last_random_msgs"] = sent or []
            except Exception: pass
        else:
            deep = make_deep_link(context.bot.username, sn, query.message.chat.id, query.message.message_id)
            if deep:
                try: await query.answer(url=deep)
                except Exception: await query.answer()
            else: await query.answer()
        return

    if data.startswith("unvisit|"):
        if user_id != OWNER_ID: await query.answer(); return
        key = data.split("|", 1)[1]
        try:
            if "pack_visits" in DB and key in DB["pack_visits"]:
                del DB["pack_visits"][key]; save_db(DB)
        except Exception: pass
        await query.answer("✓")
        items = get_top_visited_packs_with_counts(30)
        if not items:
            await query.edit_message_text(get_text(user_id, "no_visited_packs"),
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]),
                parse_mode="HTML"); return
        kb, total, cur, si = build_visited_keyboard(items, 0, user_id, chat_type, per_page=10)
        await query.edit_message_text(build_visited_text(user_id, total, cur, si),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith("closemenu|"):
        parts = data.split("|", 1)
        if len(parts) < 2: await query.answer(); return
        init_str = parts[1]
        if not user_allowed(user_id, init_str):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        await query.answer()
        try: await query.message.delete()
        except Exception: pass
        return

    if data.startswith("dosearch|"):
        await query.answer()
        nq = decode_query(data.split("|", 1)[1]); track_search(nq, user_id)
        q = normalize_query(nq)
        ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        mi, ei = split_search_results(ar, q, main_threshold=500)
        if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
        total = len(mi)
        if total == 0:
            sg = find_search_suggestions(nq)
            rows = [[make_btn(get_text(user_id, "did_you_mean", word=s), callback_data=f"dosearch|{encode_query(s)}", style="success")] for s in sg]
            if user_id != OWNER_ID:
                rows.append([make_btn(get_text(user_id, "request_pack_btn"), callback_data="request_pack", style="primary")])
            rows.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
            await query.edit_message_text(get_text(user_id, "no_results", query=html.escape(nq)),
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows)); return
        ins = str(user_id)
        kb, _ = build_search_keyboard_for_group(mi, 0, user_id, ins, chat_type,
            encoded_query=encode_query(nq), source="search",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        if ei: kb = add_more_packs_button(kb, ins, encode_query(nq), len(ei), user_id)
        await query.edit_message_text(get_text(user_id, "search_results", query=html.escape(nq), count=total),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith(f"{SIMILAR_CB_PREFIX}|"):
        parts = data.split("|", 3)
        if len(parts) < 4: await query.answer(); return
        ins = parts[1]; q_key = parts[2]
        try: pg = int(parts[3])
        except Exception: pg = 0
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        await query.answer()
        sq = get_cached_query(q_key) or decode_query(q_key)
        if not sq:
            await query.answer(get_text(user_id, "no_results_short"), show_alert=True); return
        sim = find_similar_packs(sq)
        if not sim:
            await query.answer(get_text(user_id, "no_results_short"), show_alert=True); return
        kb, total = build_search_keyboard_for_group(sim, pg, user_id, ins, chat_type,
            encoded_query=encode_query(sq), source="search",
            nav_prefix=f"{SIMILAR_CB_PREFIX}|{ins}|{q_key}",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        kb = add_back_to_results_button(kb, ins, encode_query(sq), user_id)
        await query.edit_message_text(get_text(user_id, "similar_results", query=html.escape(sq), count=total),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith(f"{BACK_SEARCH_CB}|"):
        parts = data.split("|", 2)
        if len(parts) < 3: await query.answer(); return
        ins = parts[1]; q_key = parts[2]
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        await query.answer()
        sq = get_cached_query(q_key) or decode_query(q_key)
        if not sq:
            await query.answer(get_text(user_id, "no_results_short"), show_alert=True); return
        q = normalize_query(sq)
        ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        mi, ei = split_search_results(ar, q, main_threshold=500)
        if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
        total = len(mi)
        if total == 0:
            await query.edit_message_text(get_text(user_id, "no_results", query=html.escape(sq)), parse_mode="HTML"); return
        kb, _ = build_search_keyboard_for_group(mi, 0, user_id, ins, chat_type,
            encoded_query=encode_query(sq), source="search",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        if ei: kb = add_more_packs_button(kb, ins, encode_query(sq), len(ei), user_id)
        await query.edit_message_text(get_text(user_id, "search_results", query=html.escape(sq), count=total),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data == "request_pack":
        if user_id == OWNER_ID:
            await query.answer(get_text(user_id, "owner_request_pack_msg"), show_alert=True); return
        await query.answer()
        context.user_data["awaiting_request"] = True
        await query.edit_message_text(get_text(user_id, "ask_request_pack"), parse_mode="HTML"); return

    if data == REQUEST_ASK_CB:
        await query.answer()
        context.user_data["awaiting_easy_search"] = True
        await query.edit_message_text(get_text(user_id, "easy_search_prompt"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]])); return

    if data.startswith("show_recent|"):
        await query.answer()
        try: pg = int(data.split("|")[1])
        except Exception: pg = 0
        items = get_recent_packs(RECENT_PACKS_LIMIT)
        if not items:
            await query.edit_message_text(get_text(user_id, "no_recent_packs"),
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]),
                parse_mode="HTML"); return
        ai = [v for _, v in items]
        kb, _ = build_search_keyboard_for_group(ai, pg, user_id, str(user_id), chat_type, source="search",
            nav_prefix="show_recent", bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        await query.edit_message_text(get_text(user_id, "recent_packs_header"),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith("show_visited|"):
        await query.answer()
        try: pg = int(data.split("|")[1])
        except Exception: pg = 0
        items = get_top_visited_packs_with_counts(30)
        if not items:
            await query.edit_message_text(get_text(user_id, "no_visited_packs"),
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]),
                parse_mode="HTML"); return
        kb, total, cur, si = build_visited_keyboard(items, pg, user_id, chat_type, per_page=10)
        await query.edit_message_text(build_visited_text(user_id, total, cur, si),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith("list_premium|"):
        parts = data.split("|"); ins = parts[1]; pg = int(parts[2])
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        await query.answer()
        ai = [v for v in DB["packs"].values() if is_premium_pack(v)]
        ai.sort(key=lambda x: x.get("title", "").lower())
        if not ai:
            await query.edit_message_text(get_text(user_id, "no_premium_packs"),
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]),
                parse_mode="HTML"); return
        kb, total = build_search_keyboard_for_group(ai, pg, user_id, ins, chat_type, source="search",
            nav_prefix="list_premium", bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        nf = []
        for row in kb.inline_keyboard:
            nr = []
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("list_premium|"):
                    pp = btn.callback_data.split("|")[-1]
                    nr.append(make_btn(btn.text, callback_data=f"list_premium|{ins}|{pp}", style="primary"))
                else: nr.append(btn)
            nf.append(nr)
        await query.edit_message_text(get_text(user_id, "premium_packs_header", count=total),
            reply_markup=InlineKeyboardMarkup(nf), parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith("list_regular|"):
        parts = data.split("|"); ins = parts[1]; pg = int(parts[2])
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        await query.answer()
        ai = [v for v in DB["packs"].values() if not is_premium_pack(v)]
        ai.sort(key=lambda x: x.get("title", "").lower())
        if not ai:
            await query.edit_message_text(get_text(user_id, "no_regular_packs"),
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]),
                parse_mode="HTML"); return
        kb, total = build_search_keyboard_for_group(ai, pg, user_id, ins, chat_type, source="search",
            nav_prefix="list_regular", bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        nf = []
        for row in kb.inline_keyboard:
            nr = []
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("list_regular|"):
                    pp = btn.callback_data.split("|")[-1]
                    nr.append(make_btn(btn.text, callback_data=f"list_regular|{ins}|{pp}", style="primary"))
                else: nr.append(btn)
            nf.append(nr)
        await query.edit_message_text(get_text(user_id, "regular_packs_header", count=total),
            reply_markup=InlineKeyboardMarkup(nf), parse_mode="HTML", disable_web_page_preview=True); return

    if data == "show_help":
        if chat_type != "private":
            await query.answer(get_text(user_id, "only_private"), show_alert=True); return
        await query.answer()
        vid = DB["settings"].get("tutorial_video_id")
        try: await query.message.delete()
        except Exception: pass
        if vid:
            try: await context.bot.send_video(chat_id=user_id, video=vid, caption="▶", parse_mode="HTML")
            except Exception: pass
        await context.bot.send_message(chat_id=user_id, text=get_text(user_id, "help_text"),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]))
        asyncio.create_task(_send_help_demo(context.bot, user_id)); return

    if data == "easy_search":
        if chat_type != "private":
            await query.answer(get_text(user_id, "only_private"), show_alert=True); return
        await query.answer()
        context.user_data["awaiting_easy_search"] = True
        await query.edit_message_text(get_text(user_id, "easy_search_prompt"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]])); return

    if data == "manage_video":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer()
        vid = DB["settings"].get("tutorial_video_id")
        st = get_text(OWNER_ID, "video_status_added" if vid else "video_status_not_added")
        kb = []
        if vid: kb.append([make_btn(get_text(OWNER_ID, "video_delete_btn"), callback_data="del_tutorial_video", style="danger")])
        kb.append([make_btn(get_text(OWNER_ID, "op_back"), callback_data="owner_panel", style="danger")])
        await query.edit_message_text(get_text(OWNER_ID, "video_manage_info", status=st),
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"); return

    if data == "del_tutorial_video":
        if user_id != OWNER_ID: await query.answer(); return
        DB["settings"]["tutorial_video_id"] = None; save_db(DB)
        await query.answer(get_text(OWNER_ID, "del_video_success"), show_alert=True)
        await query.edit_message_text(get_text(OWNER_ID, "video_manage_info_deleted"),
            reply_markup=InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "op_back"), callback_data="owner_panel", style="danger")]]),
            parse_mode="HTML"); return

    if data.startswith("rename_link|"):
        if user_id != OWNER_ID: await query.answer(); return
        sn = data.split("|", 1)[1]
        context.user_data["awaiting_pack_name"] = sn
        await query.answer()
        try: await query.edit_message_reply_markup(reply_markup=None)
        except Exception: pass
        await query.message.reply_text(get_text(OWNER_ID, "enter_new_name", set_name=html.escape(sn)), parse_mode="HTML"); return

    if data.startswith("set_lang|"):
        if chat_type != "private":
            await query.answer(get_text(user_id, "only_private"), show_alert=True); return
        lang = data.split("|")[1]; set_lang(user_id, lang)
        await query.answer(get_text(user_id, "lang_set"), show_alert=True)
        if context.user_data.get("reqpack_intent"):
            context.user_data["reqpack_intent"] = False
            context.user_data["awaiting_request"] = True
            await query.edit_message_text(get_text(user_id, "request_from_owner_msg"), parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]])); return
        pd = context.user_data.pop("pending_deep_pack", None)
        if pd:
            await query.edit_message_text(get_text(user_id, "welcome", user=html.escape(query.from_user.first_name), bot=context.bot.username or "Bot"),
                reply_markup=get_main_keyboard(user_id), parse_mode="HTML", disable_web_page_preview=True)
            await send_pack_to_user(context.bot, user_id, pd["set_name"], pd.get("chat_id"), pd.get("message_id")); return
        await query.edit_message_text(get_text(user_id, "welcome", user=html.escape(query.from_user.first_name), bot=context.bot.username or "Bot"),
            reply_markup=get_main_keyboard(user_id), parse_mode="HTML", disable_web_page_preview=True); return

    if data == "change_lang":
        if chat_type != "private":
            await query.answer(get_text(user_id, "only_private"), show_alert=True); return
        await query.answer()
        await query.edit_message_text(get_text(user_id, "change_lang"), reply_markup=LANG_KEYBOARD, parse_mode="HTML"); return

    if data == "do_backup":
        if user_id != OWNER_ID: await query.answer(); return
        await query.answer(get_text(OWNER_ID, "backup_creating"), show_alert=False)
        ok = await do_backup(context.bot, reason="manual")
        await query.answer(get_text(OWNER_ID, "backup_sent" if ok else "backup_failed"), show_alert=True); return

    if data.startswith("report|"):
        await query.answer()
        parts = data.split("|")
        if len(parts) < 5: return
        snk = parts[1]; pg = int(parts[2]); lt = parts[3]; ins = parts[4]
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        pd = DB["packs"].get(snk)
        if not pd:
            await query.edit_message_text(get_text(user_id, "pack_not_found_short")); return
        context.user_data["pending_report"] = {"set_name_key": snk, "page": pg, "letter": lt, "initiator_str": ins,
            "pack_title": pd.get("title", "Unnamed"), "pack_url": pd.get("url", "")}
        await query.edit_message_text(get_text(user_id, "ask_report_reason"), parse_mode="HTML"); return

    if data.startswith("del_report|"):
        if user_id != OWNER_ID: await query.answer(); return
        parts = data.split("|")
        if len(parts) < 3: return
        snk = parts[1]
        if snk in DB["packs"]:
            del DB["packs"][snk]; save_db(DB)
            await query.edit_message_text(get_text(OWNER_ID, "report_handled"), parse_mode="HTML")
        else:
            await query.edit_message_text(get_text(OWNER_ID, "pack_not_found_short")); return

    if data.startswith("ignore_report|"):
        if user_id != OWNER_ID: await query.answer(); return
        await query.edit_message_text(get_text(OWNER_ID, "report_ignored"), parse_mode="HTML"); return

    if data == "show_commands":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        await query.edit_message_text(get_commands_text(user_id), reply_markup=get_commands_keyboard(user_id), parse_mode="HTML"); return

    if data == "show_stats":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        await query.edit_message_text(get_stats_text(user_id), reply_markup=get_stats_keyboard(user_id), parse_mode="HTML"); return

    if data == SHOW_BANNED:
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        await query.answer()
        bl = DB.get("banned_users", [])
        if not bl:
            await query.edit_message_text(get_text(user_id, "no_banned_users"),
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]),
                parse_mode="HTML"); return
        t = get_text(user_id, "banned_list_header") + "\n\n"
        kb = []
        for uid in bl:
            try: c = await context.bot.get_chat(uid); un = get_user_display(c)
            except Exception: un = f"Unknown ({uid})"
            t += get_text(user_id, "banned_user_item", user=un, uid=uid) + "\n"
            kb.append([make_btn(get_text(user_id, "unban_btn"), callback_data=f"{UNBAN_CB}|{uid}", style="success")])
        kb.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
        await query.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"); return

    if data.startswith(f"{UNBAN_CB}|"):
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        tuid = int(data.split("|")[1])
        if tuid in DB.get("banned_users", []):
            DB["banned_users"].remove(tuid); save_db(DB)
            await query.answer(get_text(user_id, "unbanned_msg"), show_alert=True)
            bl = DB.get("banned_users", [])
            if not bl:
                await query.edit_message_text(get_text(user_id, "no_banned_users"),
                    reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]),
                    parse_mode="HTML"); return
            t = get_text(user_id, "banned_list_header") + "\n\n"
            kb = []
            for uid in bl:
                try: c = await context.bot.get_chat(uid); un = get_user_display(c)
                except Exception: un = f"Unknown ({uid})"
                t += get_text(user_id, "banned_user_item", user=un, uid=uid) + "\n"
                kb.append([make_btn(get_text(user_id, "unban_btn"), callback_data=f"{UNBAN_CB}|{uid}", style="success")])
            kb.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
            await query.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        else:
            await query.answer(get_text(user_id, "not_banned_short"), show_alert=True); return

    if data.startswith("+|"):
        await query.answer()
        sn = data.split("|", 1)[1]; key = sn.lower()
        if key in DB["packs"]:
            await query.edit_message_text(get_text(OWNER_ID, "already_saved"), parse_mode="Markdown"); return
        try:
            st = await context.bot.get_sticker_set(sn)
            title = clean_title(st.title or sn)
            if not title:
                context.user_data["awaiting_pack_name"] = sn
                await query.edit_message_text(get_text(OWNER_ID, "needs_name"), parse_mode="Markdown"); return
            stype = getattr(st, "sticker_type", "regular"); is_e = (stype == "custom_emoji")
            purl = f"https://t.me/addemoji/{sn}" if is_e else f"https://t.me/addstickers/{sn}"
            finalize_new_pack(key, {"title": title, "url": purl, "set_name": sn, "is_premium": is_e, "is_emoji": is_e})
            await query.edit_message_text(get_text(OWNER_ID, "saved", name=escape_markdown(title, version=1)), parse_mode="Markdown")
        except Exception:
            await query.edit_message_text(get_text(OWNER_ID, "error"), parse_mode="Markdown"); return

    if data.startswith("r|"):
        await query.answer()
        sn = data.split("|", 1)[1]
        context.user_data["awaiting_pack_name"] = sn
        await query.edit_message_text(get_text(OWNER_ID, "type_new_name"), parse_mode="Markdown"); return

    if data.startswith("-|"):
        await query.answer()
        await query.edit_message_text(get_text(OWNER_ID, "ignored"), parse_mode="Markdown"); return

    if data.startswith(f"{SEARCH_CB_PREFIX}|"):
        await query.answer()
        parts = data.split("|", 3)
        try: ins = parts[1]; eq = parts[2]; pg = int(parts[3])
        except Exception: return
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        sq = decode_query(eq); q = normalize_query(sq)
        ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        mi, ei = split_search_results(ar, q, main_threshold=500)
        if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
        total = len(mi)
        if total == 0:
            await query.edit_message_text(get_text(user_id, "no_results", query=html.escape(sq)), parse_mode="HTML"); return
        kb, _ = build_search_keyboard_for_group(mi, pg, user_id, ins, chat_type,
            encoded_query=eq, source="search",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        if ei: kb = add_more_packs_button(kb, ins, eq, len(ei), user_id)
        await query.edit_message_text(get_text(user_id, "search_results", query=html.escape(sq), count=total),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data == SHOW_ALPHA:
        await query.answer()
        kb = get_alpha_index_keyboard(user_id, str(user_id))
        await query.edit_message_text(get_text(user_id, "alpha_index_header"), reply_markup=kb, parse_mode="HTML"); return

    if data.startswith(f"{ALPHA_CB_PREFIX}|"):
        await query.answer()
        parts = data.split("|")
        if len(parts) < 4: return
        try: ins = parts[1]; lt = parts[2]; pg = int(parts[3])
        except Exception: return
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        if lt == "#":
            ai = [v for v in DB["packs"].values() if not re.match(r'^[a-zA-Z]', v.get("title", ""))]
        else:
            ai = [v for v in DB["packs"].values() if v.get("title", "").lower().startswith(lt.lower())]
        ai.sort(key=lambda x: x.get("title", "").lower())
        total = len(ai)
        if total == 0:
            await query.edit_message_text(get_text(user_id, "no_packs_letter", letter=lt.upper()), parse_mode="HTML"); return
        kb, _ = build_search_keyboard_for_group(ai, pg, user_id, ins, chat_type,
            letter=lt, source="alpha", bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None)
        hdr = get_text(user_id, "alpha_unknown" if lt == "#" else "alpha_filter", letter=lt.upper(), count=total)
        await query.edit_message_text(hdr, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if data.startswith("del_search|"):
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        parts = data.split("|", 4)
        try:
            ptr = int(parts[1]); ktd = parts[2]; eq = parts[3]; ins = parts[4]
            if ktd in DB["packs"]:
                del DB["packs"][ktd]; save_db(DB)
                await query.answer(get_text(user_id, "deleted_short"), show_alert=True)
            sq = decode_query(eq); q = normalize_query(sq)
            ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
            mi, ei = split_search_results(ar, q, main_threshold=500)
            if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
            total = len(mi)
            if total == 0:
                await query.edit_message_text(get_text(user_id, "no_results", query=html.escape(sq)), parse_mode="HTML"); return
            kb, _ = build_search_keyboard_for_group(mi, ptr, user_id, ins, chat_type,
                encoded_query=eq, source="search", bot_username=context.bot.username,
                group_chat_id=query.message.chat.id if chat_type != "private" else None)
            if ei: kb = add_more_packs_button(kb, ins, eq, len(ei), user_id)
            await query.edit_message_text(get_text(user_id, "search_results", query=html.escape(sq), count=total),
                reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
        except Exception: await query.answer()
        return

    if data.startswith("report_search|"):
        await query.answer()
        parts = data.split("|")
        if len(parts) < 5: return
        snk = parts[1]; pg = int(parts[2]); eq = parts[3]; ins = parts[4]
        if not user_allowed(user_id, ins):
            await query.answer(get_text(user_id, "not_your_button_msg"), show_alert=True); return
        pd = DB["packs"].get(snk)
        if not pd:
            await query.edit_message_text(get_text(user_id, "pack_not_found_short")); return
        context.user_data["pending_report"] = {"set_name_key": snk, "page": pg, "encoded_query": eq, "initiator_str": ins,
            "pack_title": pd.get("title", "Unnamed"), "pack_url": pd.get("url", ""), "from_search": True}
        await query.edit_message_text(get_text(user_id, "ask_report_reason"), parse_mode="HTML"); return

    if data.startswith("del|"):
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        parts = data.split("|", 4)
        try:
            ptr = int(parts[1]); ktd = parts[2]; lt = parts[3]; ins = parts[4]
            if ktd in DB["packs"]:
                del DB["packs"][ktd]; save_db(DB)
                await query.answer(get_text(user_id, "deleted_short"), show_alert=True)
            if lt:
                if lt == "#":
                    ai = [v for v in DB["packs"].values() if not re.match(r'^[a-zA-Z]', v.get("title", ""))]
                else:
                    ai = [v for v in DB["packs"].values() if v.get("title", "").lower().startswith(lt.lower())]
                ai.sort(key=lambda x: x.get("title", "").lower())
                total = len(ai)
                if total == 0:
                    await query.edit_message_text(get_text(user_id, "no_packs_letter", letter=lt.upper()), parse_mode="HTML"); return
                kb, _ = build_search_keyboard_for_group(ai, ptr, user_id, ins, chat_type,
                    letter=lt, source="alpha", bot_username=context.bot.username,
                    group_chat_id=query.message.chat.id if chat_type != "private" else None)
                hdr = get_text(user_id, "alpha_unknown" if lt == "#" else "alpha_filter", letter=lt.upper(), count=total)
                await query.edit_message_text(hdr, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
            else:
                kb = get_alpha_index_keyboard(user_id, ins)
                await query.edit_message_text(get_text(user_id, "alpha_index_header"), reply_markup=kb, parse_mode="HTML")
        except Exception: await query.answer()
        return

    if data == "toggle_forward":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True); return
        cs = DB["settings"].get("forward_messages", True)
        DB["settings"]["forward_messages"] = not cs; save_db(DB)
        await query.answer(get_text(user_id, "forwarding_toggled"), show_alert=True)
        if user_id == OWNER_ID:
            await query.edit_message_reply_markup(reply_markup=get_owner_panel_keyboard(user_id))
        else:
            await query.edit_message_text(get_text(user_id, "welcome", user=html.escape(query.from_user.first_name), bot=context.bot.username or "Bot"),
                reply_markup=get_main_keyboard(user_id), parse_mode="HTML", disable_web_page_preview=True)
        return

    if data == "btn_home":
        await query.answer()
        await query.edit_message_text(get_text(user_id, "welcome", user=html.escape(query.from_user.first_name), bot=context.bot.username or "Bot"),
            reply_markup=get_main_keyboard(user_id), parse_mode="HTML", disable_web_page_preview=True); return

# ========================= Text Handler (private) =========================
async def handle_request_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; msg = update.effective_message
    if not user or not msg or not msg.text: return
    user_id = user.id; chat_type = msg.chat.type
    if chat_type != "private": return
    if context.bot.id and user_id == context.bot.id: return
    touch_user(user_id)

    if user_id == OWNER_ID:
        if context.user_data.get("awaiting_cmd_search"):
            context.user_data["awaiting_cmd_search"] = False
            q = normalize_query(msg.text.strip())
            if not q: return
            track_search(q, user_id)
            ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
            mi, ei = split_search_results(ar, q, main_threshold=500)
            if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
            total = len(mi)
            if total == 0:
                await msg.reply_text(get_text(user_id, "no_results", query=html.escape(msg.text.strip())),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]]))
                return
            kb, _ = build_search_keyboard_for_group(mi, 0, user_id, str(user_id), chat_type,
                encoded_query=encode_query(msg.text.strip()), source="search",
                bot_username=context.bot.username)
            if ei: kb = add_more_packs_button(kb, str(user_id), encode_query(msg.text.strip()), len(ei), user_id)
            await msg.reply_text(get_text(user_id, "search_results", query=html.escape(msg.text.strip()), count=total),
                reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
            return

        if context.user_data.get("awaiting_cmd_addpremium"):
            context.user_data["awaiting_cmd_addpremium"] = False
            raw = msg.text.strip()
            m = re.search(r"(?:t\.me|telegram\.me)/(addstickers|addemoji)/([A-Za-z0-9_]+)", raw)
            if m: ut = "emoji" if m.group(1) == "addemoji" else "stickers"; sn = m.group(2)
            else: ut = "stickers"; sn = raw.split()[0] if raw.split() else ""
            if not sn:
                await msg.reply_text("⚠ لا يوجد رابط صحيح."); return
            st, info, is_e = await add_pack_from_link(context, sn, url_type=ut, force_premium=True)
            if st in ("added", "upgraded"):
                await msg.reply_text(f"★ {html.escape(info)}", parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="cmd_panel", style="danger")]]))
            else:
                await msg.reply_text(f"✕ Not found: <code>{html.escape(sn)}</code>", parse_mode="HTML")
            return

        if context.user_data.get("awaiting_cmd_setcat"):
            context.user_data["awaiting_cmd_setcat"] = False
            cid = msg.text.strip().lower()
            if cid not in CATEGORIES:
                await msg.reply_text("⚠ تصنيف غير معروف."); return
            r = msg.reply_to_message
            sn = None
            if r:
                if r.sticker and getattr(r.sticker, "set_name", None): sn = r.sticker.set_name
                else:
                    c2 = combine_text_and_entity_links(r)
                    m = re.search(r"(?:t\.me|telegram\.me)/(?:addstickers|addemoji)/([A-Za-z0-9_]+)", c2 or "")
                    if m: sn = m.group(1)
            if not sn:
                await msg.reply_text("⚠ رد على ملصق."); return
            key = sn.lower()
            if key not in DB["packs"]:
                await msg.reply_text("⚠ غير موجودة."); return
            DB["packs"][key]["category"] = cid; save_db(DB)
            await msg.reply_text(get_text(user_id, "category_set", label=get_category_label(cid, user_id)), parse_mode="HTML")
            return

        if context.user_data.get("awaiting_cmd_setwork"):
            context.user_data["awaiting_cmd_setwork"] = False
            wn = msg.text.strip()
            if not wn:
                await msg.reply_text("⚠ اسم العمل مطلوب."); return
            r = msg.reply_to_message
            sn = None
            if r:
                if r.sticker and getattr(r.sticker, "set_name", None): sn = r.sticker.set_name
                else:
                    c2 = combine_text_and_entity_links(r)
                    m = re.search(r"(?:t\.me|telegram\.me)/(?:addstickers|addemoji)/([A-Za-z0-9_]+)", c2 or "")
                    if m: sn = m.group(1)
            if not sn:
                await msg.reply_text("⚠ رد على ملصق."); return
            key = sn.lower()
            if key not in DB["packs"]:
                await msg.reply_text("⚠ غير موجودة."); return
            DB["packs"][key]["work"] = wn
            if not DB["packs"][key].get("character"):
                DB["packs"][key]["character"] = "All"
            save_db(DB)
            await msg.reply_text(f"✓ <code>{html.escape(wn)}</code>", parse_mode="HTML")
            return

        if context.user_data.get("awaiting_addcat"):
            context.user_data["awaiting_addcat"] = False
            raw = msg.text.strip()
            parts = [p.strip() for p in raw.split("|")]
            if len(parts) != 3:
                await msg.reply_text(get_text(user_id, "cat_invalid_format")); return
            emoji, name_ar, name_en = parts
            if not emoji or not name_ar or not name_en:
                await msg.reply_text(get_text(user_id, "cat_invalid_format")); return
            cid = re.sub(r'[^a-z0-9]+', '_', name_en.lower()).strip('_')[:20]
            if not cid: cid = hashlib.md5(name_en.encode()).hexdigest()[:8]
            if cid in CATEGORIES:
                await msg.reply_text(get_text(user_id, "cat_exists")); return
            new_cat = {"ar": name_ar, "en": name_en, "emoji": emoji}
            DB.setdefault("custom_categories", {})[cid] = new_cat
            CATEGORIES[cid] = new_cat
            save_db(DB)
            await msg.reply_text(
                get_text(user_id, "cat_added",
                         label=f"{emoji} {name_ar} / {name_en}\n▸ ID: <code>{cid}</code>"),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"),
                                                             callback_data="op_cats_menu", style="danger")]]))
            return

        if context.user_data.get("awaiting_admin_add"):
            context.user_data["awaiting_admin_add"] = False
            raw = msg.text.strip()
            if raw.lower() in ("del", "delete", "الغاء", "إلغاء"):
                await msg.reply_text("✕"); return
            target = await resolve_user(context.bot, raw, user_id)
            if not target:
                await msg.reply_text("⚠ لم أجد المستخدم."); return
            if target.id == OWNER_ID:
                await msg.reply_text(get_text(user_id, "owner_admin")); return
            if target.id in DB.get("admins", []):
                await msg.reply_text(get_text(user_id, "admin_already")); return
            DB.setdefault("admins", []).append(target.id); save_db(DB)
            un = get_user_display(target)
            await msg.reply_text(get_text(user_id, "admin_added", name=un, uid=target.id),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_admins_menu", style="danger")]]))
            try:
                await context.bot.send_message(chat_id=target.id,
                    text="🎉 <b>تم رفعك إلى أدمن!</b>", parse_mode="HTML")
            except Exception: pass
            return

        if context.user_data.get("awaiting_ai_key"):
            context.user_data["awaiting_ai_key"] = False
            k = msg.text.strip()
            if len(k) < 10:
                await msg.reply_text("⚠ قصير جداً."); return
            DB["settings"]["ai_api_key"] = k; DB["settings"]["ai_enabled"] = True; save_db(DB)
            await msg.reply_text("✓ تم الحفظ والتفعيل.", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_ai_menu", style="danger")]])); return

        if context.user_data.get("awaiting_ai_model"):
            context.user_data["awaiting_ai_model"] = False
            DB["settings"]["ai_model"] = msg.text.strip(); save_db(DB)
            await msg.reply_text(f"✓ <code>{html.escape(msg.text.strip())}</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_ai_menu", style="danger")]])); return

        if context.user_data.get("awaiting_ai_base"):
            context.user_data["awaiting_ai_base"] = False
            DB["settings"]["ai_base_url"] = msg.text.strip().rstrip("/"); save_db(DB)
            await msg.reply_text("✓", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_ai_menu", style="danger")]])); return

        if context.user_data.get("awaiting_ai_prompt"):
            context.user_data["awaiting_ai_prompt"] = False
            p = msg.text.strip()
            if len(p) < 20:
                await msg.reply_text("⚠ قصير جداً."); return
            DB["settings"]["ai_system_prompt"] = p; save_db(DB)
            await msg.reply_text("✓", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="op_ai_menu", style="danger")]])); return

        if context.user_data.get("awaiting_broadcast"):
            context.user_data["awaiting_broadcast"] = False
            users = DB.get("users", [])
            if not users:
                await msg.reply_text(get_text(user_id, "no_users")); return
            st = await msg.reply_text(f"📢 <b>{len(users)}</b>...", parse_mode="HTML")
            sent = 0
            for uid in users:
                try: await msg.copy(chat_id=uid); sent += 1
                except Exception: pass
                await asyncio.sleep(0.05)
            await st.edit_text(get_text(user_id, "broadcast_done", count=sent),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "op_back"), callback_data="owner_panel", style="danger")]])); return

        if context.user_data.get("awaiting_trigger_name"):
            txt = msg.text.strip()
            context.user_data["awaiting_trigger_name"] = False
            if not txt:
                await msg.reply_text(get_text(user_id, "invalid_setting")); return
            if txt.lower() in ("del", "delete", "none", "حذف", "افتراضي"):
                DB["settings"]["trigger_name"] = DEFAULT_TRIGGER_NAME; save_db(DB)
                await msg.reply_text(get_text(user_id, "setting_deleted"), parse_mode="HTML",
                    reply_markup=get_owner_settings_keyboard(user_id)); return
            new_name = txt.lower().strip()
            if len(new_name) < 2:
                await msg.reply_text(get_text(user_id, "invalid_setting")); return
            DB["settings"]["trigger_name"] = new_name; save_db(DB)
            await msg.reply_text(f"✓ <code>{html.escape(new_name)}</code>", parse_mode="HTML",
                reply_markup=get_owner_settings_keyboard(user_id)); return

        if context.user_data.get("awaiting_group_link"):
            txt = msg.text.strip()
            context.user_data["awaiting_group_link"] = False
            if txt.lower() in ("del", "delete", "none", "حذف"):
                DB["settings"]["group_link"] = ""; save_db(DB)
                await msg.reply_text(get_text(user_id, "setting_deleted"), reply_markup=get_owner_settings_keyboard(user_id)); return
            DB["settings"]["group_link"] = txt; save_db(DB)
            await msg.reply_text(f"✓ <code>{html.escape(txt)}</code>", parse_mode="HTML",
                reply_markup=get_owner_settings_keyboard(user_id)); return

        if context.user_data.get("awaiting_channel_link"):
            txt = msg.text.strip()
            context.user_data["awaiting_channel_link"] = False
            if txt.lower() in ("del", "delete", "none", "حذف"):
                DB["settings"]["channel_link"] = ""; save_db(DB)
                await msg.reply_text(get_text(user_id, "setting_deleted"), reply_markup=get_owner_settings_keyboard(user_id)); return
            DB["settings"]["channel_link"] = txt; save_db(DB)
            await msg.reply_text(f"✓ <code>{html.escape(txt)}</code>", parse_mode="HTML",
                reply_markup=get_owner_settings_keyboard(user_id)); return

        if context.user_data.get("awaiting_sub_channel"):
            txt = msg.text.strip()
            context.user_data["awaiting_sub_channel"] = False
            if txt.lower() in ("del", "delete", "none", "حذف", "off"):
                DB["settings"]["force_sub_channel"] = ""
                DB["settings"]["force_sub_enabled"] = False
                save_db(DB)
                await msg.reply_text(get_text(user_id, "setting_deleted"), reply_markup=get_owner_settings_keyboard(user_id)); return
            DB["settings"]["force_sub_channel"] = txt
            DB["settings"]["force_sub_enabled"] = True
            save_db(DB)
            await msg.reply_text(f"✓ <code>{html.escape(txt)}</code>", parse_mode="HTML",
                reply_markup=get_owner_settings_keyboard(user_id)); return

    if context.user_data.get("awaiting_easy_search"):
        qt = msg.text.strip()
        if not qt: return
        context.user_data["awaiting_easy_search"] = False
        track_search(qt, user_id); q = normalize_query(qt)
        ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        mi, ei = split_search_results(ar, q, main_threshold=500)
        if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
        total = len(mi)
        if total == 0:
            sg = find_search_suggestions(qt)
            rows = [[make_btn(get_text(user_id, "did_you_mean", word=s), callback_data=f"dosearch|{encode_query(s)}", style="success")] for s in sg]
            if user_id != OWNER_ID:
                rows.append([make_btn(get_text(user_id, "request_pack_btn"), callback_data="request_pack", style="primary")])
            rows.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
            await msg.reply_text(get_text(user_id, "no_results", query=html.escape(qt)),
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows)); return
        ins = str(user_id)
        kb, _ = build_search_keyboard_for_group(mi, 0, user_id, ins, chat_type,
            encoded_query=encode_query(qt), source="search", bot_username=context.bot.username)
        if ei: kb = add_more_packs_button(kb, ins, encode_query(qt), len(ei), user_id)
        await msg.reply_text(get_text(user_id, "search_results", query=html.escape(qt), count=total),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True); return

    if context.user_data.get("awaiting_request"):
        rt = msg.text.strip()
        if not rt: return
        context.user_data["awaiting_request"] = False
        ud = get_user_display(user)
        notif = get_text(OWNER_ID, "request_notification", user=ud, uid=user.id, request=html.escape(rt))
        try:
            nm = await context.bot.send_message(chat_id=OWNER_ID, text=notif, parse_mode="HTML")
            try: await context.bot.pin_chat_message(chat_id=OWNER_ID, message_id=nm.message_id, disable_notification=True)
            except Exception: pass
            context.bot_data.setdefault("requests", {})[str(user.id)] = {"user_id": user.id, "user_display": ud,
                                                                          "request": rt, "notif_msg_id": nm.message_id}
            context.bot_data.setdefault("forwarded_map", {})[nm.message_id] = user.id
        except Exception: pass
        rows = [[make_btn(get_text(user_id, "request_looking_btn"), callback_data=REQUEST_ASK_CB, style="primary")],
                [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]]
        await msg.reply_text(get_text(user_id, "request_received_pending"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows)); return

    if context.user_data.get("pending_report"):
        rd = context.user_data["pending_report"]; reason = msg.text.strip()
        if not reason:
            await msg.reply_text(get_text(user_id, "ask_report_reason_short")); return
        ud = get_user_display(user)
        rtext = get_text(OWNER_ID, "report_notification", user=ud, uid=user_id,
                         pack_name=html.escape(rd["pack_title"]), pack_url=rd["pack_url"],
                         reason=html.escape(reason))
        kb = InlineKeyboardMarkup([[
            make_btn(get_text(OWNER_ID, "report_delete_btn"), callback_data=f"del_report|{rd['set_name_key']}|{rd['page']}", style="danger"),
            make_btn(get_text(OWNER_ID, "report_ignore_btn"), callback_data=f"ignore_report|{rd['set_name_key']}|{rd['page']}", style="primary"),
        ]])
        await context.bot.send_message(chat_id=OWNER_ID, text=rtext, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
        await msg.reply_text(get_text(user_id, "report_success"))
        if rd.get("from_search"):
            await msg.reply_text(get_text(user_id, "welcome", user=ud, bot=context.bot.username or "Bot"),
                reply_markup=get_main_keyboard(user_id), parse_mode="HTML", disable_web_page_preview=True)
        else:
            kb2 = get_alpha_index_keyboard(user_id, rd.get("initiator_str", str(user_id)))
            await msg.reply_text(get_text(user_id, "alpha_index_header"), reply_markup=kb2, parse_mode="HTML")
        context.user_data["pending_report"] = None; return

# ========================= Commands =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    user_id = update.effective_user.id
    user_name = html.escape(update.effective_user.first_name)
    chat_type = update.effective_chat.type
    if user_id in DB.get("banned_users", []) and user_id != OWNER_ID:
        await update.message.reply_text(get_text(user_id, "banned")); return
    if user_id == OWNER_ID:
        context.bot_data["stop_scan"] = True
    if chat_type == "private":
        touch_user(user_id)
        if not await check_force_sub(context.bot, user_id):
            await send_force_sub_msg(context.bot, update.effective_chat.id, user_id); return
        if context.args:
            arg = context.args[0]
            sn_dl, cid_dl, mid_dl = parse_deep_link(arg)
            if sn_dl:
                try: track_pack_visit(sn_dl)
                except Exception: pass
                if str(user_id) not in DB.get("users_lang", {}):
                    context.user_data["pending_deep_pack"] = {"set_name": sn_dl, "chat_id": cid_dl, "message_id": mid_dl}
                    await update.message.reply_text(get_text(user_id, "change_lang"), reply_markup=LANG_KEYBOARD, parse_mode="HTML"); return
                await send_pack_to_user(context.bot, user_id, sn_dl, cid_dl, mid_dl); return
            if arg == "reqpack": context.user_data["reqpack_intent"] = True
        is_new = track_user(user_id)
        if is_new:
            try:
                ud = get_user_display(update.effective_user)
                now = _now_makkah().strftime("%Y-%m-%d %H:%M:%S")
                nt = get_text(OWNER_ID, "new_user_notification", user=ud, uid=user_id, date=now, total=len(DB.get("users", [])))
                await context.bot.send_message(chat_id=OWNER_ID, text=nt, parse_mode="HTML")
            except Exception: pass
        if str(user_id) not in DB.get("users_lang", {}):
            await update.message.reply_text(get_text(user_id, "change_lang"), reply_markup=LANG_KEYBOARD, parse_mode="HTML"); return
        if context.user_data.get("reqpack_intent"):
            context.user_data["reqpack_intent"] = False; context.user_data["awaiting_request"] = True
            await update.message.reply_text(get_text(user_id, "request_from_owner_msg"), parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]])); return
        bu = context.bot.username or "Bot"
        await update.message.reply_text(get_text(user_id, "welcome", user=user_name, bot=bu),
            reply_markup=get_main_keyboard(user_id), parse_mode="HTML", disable_web_page_preview=True)
        try: await try_react(context.bot, update.message.chat_id, update.message.message_id, pick_random_reactions(7, "happy"))
        except Exception: pass
        return
    track_user(user_id); touch_user(user_id)
    bu = context.bot.username or "Bot"
    await update.message.reply_text(get_text(user_id, "group_welcome", bot=bu), parse_mode="HTML", disable_web_page_preview=True)

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user: return
    user_id = user.id
    if user_id in DB.get("banned_users", []) and user_id != OWNER_ID: return
    if not await check_force_sub(context.bot, user_id):
        await send_force_sub_msg(context.bot, update.effective_chat.id, user_id); return
    msg = update.effective_message
    if not msg: return
    query = " ".join(context.args).strip()
    chat_type = update.effective_chat.type
    touch_user(user_id)

    if (user_id == OWNER_ID and msg.reply_to_message and context.bot_data.get("forwarded_map", {}).get(msg.reply_to_message.message_id)):
        tuid = context.bot_data["forwarded_map"][msg.reply_to_message.message_id]
        if not query:
            await msg.reply_text(get_text(OWNER_ID, "enter_search_term"), parse_mode="HTML"); return
        track_search(query, user_id); q = normalize_query(query)
        ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        mi, ei = split_search_results(ar, q, main_threshold=500)
        if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
        total = len(mi)
        if total == 0:
            try: await context.bot.send_message(chat_id=tuid, text=get_text(tuid, "no_results", query=html.escape(query)), parse_mode="HTML")
            except Exception: pass
            await msg.reply_text(get_text(OWNER_ID, "admin_reply_sent")); return
        kb, _ = build_search_keyboard_for_group(mi, 0, tuid, str(tuid), "private",
            encoded_query=encode_query(query), source="search", bot_username=context.bot.username)
        if ei: kb = add_more_packs_button(kb, str(tuid), encode_query(query), len(ei), tuid)
        try:
            await context.bot.send_message(chat_id=tuid, text=get_text(tuid, "search_results", query=html.escape(query), count=total),
                reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
        except Exception: pass
        await msg.reply_text(get_text(OWNER_ID, "admin_reply_sent")); return

    if (chat_type != "private" and msg.reply_to_message and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id != user_id
        and msg.reply_to_message.from_user.id != context.bot.id
        and not msg.reply_to_message.from_user.is_bot):
        ruid = msg.reply_to_message.from_user.id
        if not query:
            await msg.reply_text(get_text(user_id, "enter_search_term"), parse_mode="HTML"); return
        track_user(ruid); track_search(query, user_id); q = normalize_query(query)
        ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        mi, ei = split_search_results(ar, q, main_threshold=500)
        if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
        total = len(mi)
        try: await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
        except Exception: pass
        ins = f"{user_id},{ruid}"; bu = context.bot.username or "Bot"; gcid = msg.chat.id
        if total == 0:
            sg = find_search_suggestions(query)
            rows = [[make_btn(get_text(ruid, "did_you_mean", word=s), callback_data=f"dosearch|{encode_query(s)}", style="success")] for s in sg]
            rows.append([make_btn(get_text(ruid, "request_pack_btn"), url=f"https://t.me/{bu}?start=reqpack", style="primary")])
            rows.append([make_btn(get_text(ruid, "subscribe_channel"), url=CHANNEL_URL, style="primary")])
            try:
                await context.bot.send_message(chat_id=msg.chat_id, text=get_text(ruid, "no_results", query=html.escape(query)),
                    parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows), reply_to_message_id=msg.reply_to_message.message_id)
            except Exception: pass
            return
        kb, _ = build_search_keyboard_for_group(mi, 0, ruid, ins, chat_type,
            encoded_query=encode_query(query), source="search",
            bot_username=bu, group_chat_id=gcid)
        if ei: kb = add_more_packs_button(kb, ins, encode_query(query), len(ei), ruid)
        try:
            await context.bot.send_message(chat_id=msg.chat_id, text=get_text(ruid, "search_results", query=html.escape(query), count=total),
                reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True,
                reply_to_message_id=msg.reply_to_message.message_id)
        except Exception: pass
        return

    track_user(user_id)
    if not query:
        await msg.reply_text(get_text(user_id, "enter_search_term"), parse_mode="HTML"); return
    track_search(query, user_id); q = normalize_query(query)
    ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
    mi, ei = split_search_results(ar, q, main_threshold=500)
    if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
    total = len(mi); ins = str(user_id)
    bu = context.bot.username or "Bot"
    gcid = msg.chat.id if chat_type != "private" else None
    if total == 0:
        sg = find_search_suggestions(query)
        rows = [[make_btn(get_text(user_id, "did_you_mean", word=s), callback_data=f"dosearch|{encode_query(s)}", style="success")] for s in sg]
        if chat_type == "private":
            if user_id != OWNER_ID:
                rows.append([make_btn(get_text(user_id, "request_pack_btn"), callback_data="request_pack", style="primary")])
            rows.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
        else:
            rows.append([make_btn(get_text(user_id, "request_pack_btn"), url=f"https://t.me/{bu}?start=reqpack", style="primary")])
            rows.append([make_btn(get_text(user_id, "subscribe_channel"), url=CHANNEL_URL, style="primary")])
        await msg.reply_text(get_text(user_id, "no_results", query=html.escape(query)),
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows)); return
    kb, _ = build_search_keyboard_for_group(mi, 0, user_id, ins, chat_type,
        encoded_query=encode_query(query), source="search",
        bot_username=bu, group_chat_id=gcid)
    if ei: kb = add_more_packs_button(kb, ins, encode_query(query), len(ei), user_id)
    await msg.reply_text(get_text(user_id, "search_results", query=html.escape(query), count=total),
        reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    user_id = OWNER_ID; msg = update.effective_message
    if not msg.reply_to_message:
        await msg.reply_text(get_text(user_id, "reply_broadcast"), parse_mode="HTML"); return
    users = DB.get("users", [])
    if not users:
        await msg.reply_text(get_text(user_id, "no_users"), parse_mode="HTML"); return
    success = 0
    for uid in users:
        try:
            await context.bot.copy_message(chat_id=uid, from_chat_id=msg.chat_id, message_id=msg.reply_to_message.message_id)
            success += 1
        except Exception: pass
    await msg.reply_text(get_text(user_id, "broadcast_done", count=success), parse_mode="HTML")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id): return
    user_id = user.id; msg = update.effective_message
    if not msg or not msg.reply_to_message: return
    if msg.text and msg.text.strip().startswith("/search"): return
    rid = msg.reply_to_message.message_id
    fmap = context.bot_data.get("forwarded_map", {})
    tuid = fmap.get(rid)
    if not tuid: return
    try:
        if msg.sticker:
            try: await context.bot.send_sticker(chat_id=tuid, sticker=msg.sticker.file_id)
            except Exception: pass
        elif msg.text:
            await context.bot.send_message(chat_id=tuid, text=msg.text, parse_mode="HTML")
        else:
            try: await msg.copy(chat_id=tuid)
            except Exception: pass
        kb = InlineKeyboardMarkup([
            [make_btn(get_text(tuid, "request_support_channel_btn"), url=CHANNEL_URL, style="primary")],
            [make_btn(get_text(tuid, "main_menu"), callback_data="btn_home", style="danger")],
        ])
        await context.bot.send_message(chat_id=tuid, text=get_text(tuid, "request_delivered_to_user_msg"),
                                       parse_mode="HTML", reply_markup=kb)
        await msg.reply_text(get_text(user_id, "request_delivered_to_owner"))
    except Exception:
        await msg.reply_text(get_text(user_id, "admin_reply_fail"))

async def _send_help_demo(bot, user_id):
    await asyncio.sleep(3)
    packs = list(DB["packs"].values())
    if not packs: return
    pack = random.choice(packs); title = pack.get("title", "")
    words = [w for w in re.findall(r"[A-Za-z0-9]+", title) if len(w) >= 3]
    query = random.choice(words) if words else title
    if not query: return
    dm = await bot.send_message(chat_id=user_id, text=f"<code>/search {html.escape(query)}</code>", parse_mode="HTML")
    await asyncio.sleep(1)
    q = normalize_query(query)
    ar = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
    mi, ei = split_search_results(ar, q, main_threshold=500)
    if not mi and ar: mi = sorted(ar, key=lambda x: x.get("title", "").lower()); ei = []
    total = len(mi)
    if total == 0:
        await bot.send_message(chat_id=user_id, text=get_text(user_id, "no_results", query=html.escape(query)), parse_mode="HTML"); return
    kb, _ = build_search_keyboard_for_group(mi, 0, user_id, str(user_id), "private",
        encoded_query=encode_query(query), source="search", bot_username=bot.username)
    if ei: kb = add_more_packs_button(kb, str(user_id), encode_query(query), len(ei), user_id)
    try:
        await bot.send_message(chat_id=user_id, text=get_text(user_id, "search_results", query=html.escape(query), count=total),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True, reply_to_message_id=dm.message_id)
    except Exception:
        await bot.send_message(chat_id=user_id, text=get_text(user_id, "search_results", query=html.escape(query), count=total),
            reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id): return
    uid = user.id; msg = update.effective_message
    if not msg or not msg.reply_to_message or not msg.reply_to_message.sticker:
        await msg.reply_text(get_text(uid, "reply_to_sticker_add")); return
    sn = msg.reply_to_message.sticker.set_name
    if not sn:
        await msg.reply_text(get_text(uid, "not_from_pack")); return
    key = sn.lower()
    if key in DB["packs"]: return
    try:
        st = await context.bot.get_sticker_set(sn)
        title = clean_title(st.title or sn)
        if not title:
            await msg.reply_text(get_text(uid, "invalid_name")); return
        stype = getattr(st, "sticker_type", "regular"); is_e = (stype == "custom_emoji")
        purl = f"https://t.me/addemoji/{sn}" if is_e else f"https://t.me/addstickers/{sn}"
        finalize_new_pack(key, {"title": title, "url": purl, "set_name": sn, "is_premium": is_e, "is_emoji": is_e})
        await msg.reply_text(get_text(uid, "pack_added_simple", name=html.escape(title)), parse_mode="HTML")
    except Exception as e:
        await msg.reply_text(get_text(uid, "error_occurred", err=html.escape(str(e))), parse_mode="HTML")

async def cmd_addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID: return
    msg = update.effective_message; raw = " ".join(context.args or []).strip()
    if not raw:
        await msg.reply_text("⚠ Usage: <code>/addpremium &lt;link&gt;</code>", parse_mode="HTML"); return
    m = re.search(r"(?:t\.me|telegram\.me)/(addstickers|addemoji)/([A-Za-z0-9_]+)", raw)
    if m: ut = "emoji" if m.group(1) == "addemoji" else "stickers"; sn = m.group(2)
    else: ut = "stickers"; sn = raw.split()[0]
    st, info, is_e = await add_pack_from_link(context, sn, url_type=ut, force_premium=True)
    if st in ("added", "upgraded"):
        kb = InlineKeyboardMarkup([[make_btn(get_text(OWNER_ID, "rename_btn"), callback_data=f"rename_link|{sn}", style="primary")]])
        await msg.reply_text(f"★ {html.escape(info)}", parse_mode="HTML", reply_markup=kb)
    elif st == "failed":
        await msg.reply_text(f"✕ Not found: <code>{html.escape(sn)}</code>", parse_mode="HTML")

async def cmd_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id): return
    uid = user.id; msg = update.effective_message
    if not msg or not msg.reply_to_message or not msg.reply_to_message.sticker:
        await msg.reply_text(get_text(uid, "reply_to_sticker_del")); return
    sn = msg.reply_to_message.sticker.set_name
    if not sn:
        await msg.reply_text(get_text(uid, "not_from_pack")); return
    key = sn.lower()
    if key not in DB["packs"]:
        await msg.reply_text(get_text(uid, "not_found")); return
    del DB["packs"][key]; save_db(DB)
    await msg.reply_text(get_text(uid, "deleted", name=html.escape(sn)), parse_mode="HTML")

async def cmd_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id): return
    uid = user.id; msg = update.effective_message
    if not msg: return
    if not msg.reply_to_message:
        await msg.reply_text(get_text(uid, "reply_to_sticker_rename"), parse_mode="HTML"); return
    replied = msg.reply_to_message; sn = None; ut = "stickers"
    if replied.sticker and getattr(replied.sticker, "set_name", None):
        sn = replied.sticker.set_name
        stype = getattr(replied.sticker, "type", "regular")
        ut = "emoji" if stype == "custom_emoji" else "stickers"
    if not sn:
        combined = combine_text_and_entity_links(replied)
        if combined:
            m = re.search(r"(?:t\.me|telegram\.me)/(addstickers|addemoji)/([A-Za-z0-9_]+)", combined)
            if m: ut = "emoji" if m.group(1) == "addemoji" else "stickers"; sn = m.group(2)
    if not sn:
        await msg.reply_text(get_text(uid, "reply_to_sticker_rename"), parse_mode="HTML"); return
    parts = (msg.text or "").split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        await msg.reply_text(get_text(uid, "usage_rename"), parse_mode="HTML"); return
    new_name = clean_title(parts[1].strip()) or parts[1].strip()
    key = sn.lower()
    if key not in DB["packs"]:
        st, info, is_e = await add_pack_from_link(context, sn, url_type=ut)
        if st == "failed":
            await msg.reply_text(f"✕ Not found: <code>{html.escape(sn)}</code>", parse_mode="HTML"); return
    DB["packs"][key]["title"] = new_name
    DB["packs"][key]["title_locked"] = True
    save_db(DB)
    icon = "★" if DB["packs"][key].get("is_premium") else "▪"
    await msg.reply_text(f"✓ Updated.\n\n  {icon} <b>Name:</b> <code>{html.escape(new_name)}</code>\n"
                         f"  ↗ <b>Link:</b> <a href=\"{DB['packs'][key]['url']}\">Open</a>",
                         parse_mode="HTML", disable_web_page_preview=True)

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID: return
    msg = update.effective_message
    await msg.reply_text(get_text(uid, "scan_started"))
    deleted = updated = unchanged = 0
    packs = DB["packs"]; ktd = []
    for k, p in packs.items():
        o = p.get("title", ""); c = clean_title(o)
        if c != o:
            if c.strip() == "": ktd.append(k); deleted += 1
            else: packs[k]["title"] = c; updated += 1
        else: unchanged += 1
    for k in ktd: del packs[k]
    save_db(DB)
    await msg.reply_text(get_text(uid, "scan_complete", deleted=deleted, updated=updated, unchanged=unchanged), parse_mode="HTML")

async def cmd_setvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID: return
    msg = update.effective_message
    if not msg.reply_to_message or not msg.reply_to_message.video:
        await msg.reply_text(get_text(OWNER_ID, "set_video_reply"), parse_mode="HTML"); return
    DB["settings"]["tutorial_video_id"] = msg.reply_to_message.video.file_id; save_db(DB)
    await msg.reply_text(get_text(OWNER_ID, "set_video_success"), parse_mode="HTML")

async def cmd_delvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID: return
    msg = update.effective_message
    if not DB["settings"].get("tutorial_video_id"):
        await msg.reply_text(get_text(OWNER_ID, "del_video_not_found")); return
    DB["settings"]["tutorial_video_id"] = None; save_db(DB)
    await msg.reply_text(get_text(OWNER_ID, "del_video_success"))

async def cmd_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user: return
    if user.id in DB.get("banned_users", []) and user.id != OWNER_ID: return
    if not await check_force_sub(context.bot, user.id):
        await send_force_sub_msg(context.bot, update.effective_chat.id, user.id); return
    msg = update.effective_message
    if not msg: return
    chat_type = msg.chat.type
    touch_user(user.id)
    packs = list(DB["packs"].values())
    if not packs:
        await msg.reply_text(get_text(user.id, "no_packs_yet"), parse_mode="HTML"); return
    pack = random.choice(packs)
    sn = pack.get("set_name", "")
    if not sn:
        await msg.reply_text(get_text(user.id, "pack_not_found_short")); return
    try: track_pack_visit(sn.lower())
    except Exception: pass
    try: track_random_usage(user, chat_type)
    except Exception: pass
    if chat_type == "private":
        try:
            sent = await send_pack_to_user(context.bot, user.id, sn, show_random_again=True)
            context.user_data["last_random_msgs"] = sent or []
        except Exception: pass
        return
    deep = make_deep_link(context.bot.username, sn, msg.chat.id, msg.message_id)
    purl = pack.get("url", "") or f"https://t.me/addstickers/{sn}"
    turl = deep or purl
    title = pack.get("title", sn)
    star = "★ " if is_premium_pack(pack) else "▪ "
    kb = InlineKeyboardMarkup([[make_btn(get_text(user.id, "open_pack_btn"), url=turl, style="success")]])
    try:
        await msg.reply_text(f"{star}<b>{html.escape(title)}</b>", parse_mode="HTML",
                             reply_markup=kb, disable_web_page_preview=True)
    except Exception: pass

async def cmd_randomstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message
    st = DB.get("stats", {})
    total = st.get("random_total", 0)
    usage = st.get("random_usage", {}) or {}
    if not usage:
        await msg.reply_text("⚠ ما فيه استخدام بعد.", parse_mode="HTML"); return
    items = sorted(usage.items(), key=lambda x: -int(x[1].get("count", 0)))
    lines = [f"🎲 <b>Random</b>\n  ▪ المجموع: <code>{total}</code>\n  ⚇ عدد: <code>{len(items)}</code>\n"]
    for i, (uid, d) in enumerate(items[:50], 1):
        un = d.get("name", "User")
        uname = f"@{d.get('username')}" if d.get("username") else ""
        cnt = d.get("count", 0)
        lines.append(f"  {i}. {html.escape(un)} {uname} — <code>{uid}</code> → <b>{cnt}</b>")
    await msg.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_test_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message
    s = DB.get("settings", {})
    key = (s.get("ai_api_key") or "").strip()
    model = s.get("ai_model") or "gemini-2.5-flash"
    if model.startswith("models/"): model = model[7:]
    await msg.reply_text(
        f"🧪 <b>اختبار AI</b>\n\n"
        f"▪ الموديل: <code>{model}</code>\n"
        f"▪ المفتاح: <code>{key[:10]}...</code>\n"
        f"▪ مفعّل: <code>{s.get('ai_enabled')}</code>\n\n"
        f"◷ جاري الإرسال...",
        parse_mode="HTML"
    )
    reply = await call_ai_raw("قل: تم")
    if reply:
        await msg.reply_text(f"✅ <b>نجح!</b>\n\nالرد: {html.escape(reply)}\n\n▸ الموديل: <code>{model}</code>", parse_mode="HTML")
    else:
        await msg.reply_text("❌ <b>فشل</b> — انظر الرسالة اللي وصلتك فوق", parse_mode="HTML")

async def cmd_setai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message; args = context.args or []
    if not args:
        await msg.reply_text("⚠ <code>/setai &lt;KEY&gt;</code>", parse_mode="HTML"); return
    DB["settings"]["ai_api_key"] = args[0].strip(); DB["settings"]["ai_enabled"] = True
    save_db(DB)
    await msg.reply_text("✓ تم التفعيل.", parse_mode="HTML")

async def cmd_aion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    if not DB["settings"].get("ai_api_key"):
        await update.effective_message.reply_text("⚠ ضع المفتاح أولاً", parse_mode="HTML"); return
    DB["settings"]["ai_enabled"] = True; save_db(DB)
    await update.effective_message.reply_text("✓ تم التشغيل.")

async def cmd_aioff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    DB["settings"]["ai_enabled"] = False; save_db(DB)
    await update.effective_message.reply_text("✓ تم الإيقاف.")

async def cmd_aiprompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    txt = " ".join(context.args or []).strip()
    if not txt:
        cur = DB["settings"].get("ai_system_prompt", "")
        await update.effective_message.reply_text(f"<code>{html.escape(cur)}</code>", parse_mode="HTML"); return
    DB["settings"]["ai_system_prompt"] = txt; save_db(DB)
    await update.effective_message.reply_text("✓")

async def cmd_aimodel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    m = " ".join(context.args or []).strip()
    if not m:
        cur = DB["settings"].get("ai_model", "")
        await update.effective_message.reply_text(f"<code>{html.escape(cur)}</code>", parse_mode="HTML"); return
    DB["settings"]["ai_model"] = m; save_db(DB)
    await update.effective_message.reply_text(f"✓ <code>{html.escape(m)}</code>", parse_mode="HTML")

async def cmd_aibase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    u = " ".join(context.args or []).strip()
    if not u:
        cur = DB["settings"].get("ai_base_url", "")
        await update.effective_message.reply_text(f"<code>{html.escape(cur)}</code>", parse_mode="HTML"); return
    DB["settings"]["ai_base_url"] = u.rstrip("/"); save_db(DB)
    await update.effective_message.reply_text("✓")

async def cmd_aismart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    DB["settings"]["ai_system_prompt"] = SMART_SYSTEM_PROMPT
    save_db(DB)
    await update.effective_message.reply_text("✓")

async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID: return
    msg = update.effective_message; args = context.args or []
    if not args:
        await msg.reply_text("⚠ <code>/addadmin @username</code>", parse_mode="HTML"); return
    target = await resolve_user(context.bot, args[0].strip(), user.id)
    if not target:
        await msg.reply_text("⚠ لم أجد."); return
    if target.id == OWNER_ID:
        await msg.reply_text(get_text(OWNER_ID, "owner_admin")); return
    if target.id in DB.get("admins", []):
        await msg.reply_text(get_text(OWNER_ID, "admin_already")); return
    DB.setdefault("admins", []).append(target.id); save_db(DB)
    un = get_user_display(target)
    await msg.reply_text(get_text(OWNER_ID, "admin_added", name=un, uid=target.id), parse_mode="HTML")
    try: await context.bot.send_message(chat_id=target.id, text="🎉 <b>تم رفعك أدمن!</b>", parse_mode="HTML")
    except Exception: pass

async def cmd_deladmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID: return
    msg = update.effective_message; args = context.args or []
    if not args:
        await msg.reply_text("⚠ <code>/deladmin @username</code>", parse_mode="HTML"); return
    target = await resolve_user(context.bot, args[0].strip(), user.id)
    if not target:
        await msg.reply_text("⚠ لم أجد."); return
    if target.id not in DB.get("admins", []):
        await msg.reply_text("⚠ ليس أدمن."); return
    DB["admins"].remove(target.id); save_db(DB)
    un = get_user_display(target)
    await msg.reply_text(get_text(OWNER_ID, "admin_removed", name=un), parse_mode="HTML")

async def cmd_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id): return
    msg = update.effective_message
    admins = DB.get("admins", [])
    if not admins:
        await msg.reply_text(get_text(user.id, "no_admins")); return
    lines = [get_text(user.id, "op_admins_header"), ""]
    for i, uid in enumerate(admins, 1):
        try:
            c = await context.bot.get_chat(uid); un = get_user_display(c)
            uname = f" @{c.username}" if getattr(c, "username", None) else ""
        except Exception: un, uname = "Unknown", ""
        lines.append(f"  {i}. {un}{uname} — <code>{uid}</code>")
    lines.append(""); lines.append(f"♛ <b>المالك:</b> <code>{OWNER_ID}</code>")
    await msg.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_setcat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id): return
    uid = user.id; msg = update.effective_message
    if not msg: return
    args = context.args or []
    if not args:
        await msg.reply_text(get_text(uid, "ask_setcat_usage"), parse_mode="HTML"); return
    cid = args[0].strip().lower()
    if cid not in CATEGORIES:
        await msg.reply_text("⚠ غير معروف. المتاح: " + ", ".join(CATEGORIES.keys())); return
    sn = None; r = msg.reply_to_message
    if r:
        if r.sticker and getattr(r.sticker, "set_name", None): sn = r.sticker.set_name
        else:
            combined = combine_text_and_entity_links(r)
            m = re.search(r"(?:t\.me|telegram\.me)/(?:addstickers|addemoji)/([A-Za-z0-9_]+)", combined or "")
            if m: sn = m.group(1)
    if not sn:
        await msg.reply_text(get_text(uid, "reply_to_sticker_rename"), parse_mode="HTML"); return
    key = sn.lower()
    if key not in DB["packs"]:
        await msg.reply_text(get_text(uid, "not_found")); return
    DB["packs"][key]["category"] = cid; save_db(DB)
    await msg.reply_text(get_text(uid, "category_set", label=get_category_label(cid, uid)), parse_mode="HTML")

async def cmd_setwork(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id): return
    uid = user.id; msg = update.effective_message
    if not msg: return
    args = context.args or []
    if not args:
        await msg.reply_text("⚠ <code>/setwork &lt;name&gt;</code> رداً على ملصق", parse_mode="HTML"); return
    wn = " ".join(args).strip()
    sn = None; r = msg.reply_to_message
    if r:
        if r.sticker and getattr(r.sticker, "set_name", None): sn = r.sticker.set_name
        else:
            combined = combine_text_and_entity_links(r)
            m = re.search(r"(?:t\.me|telegram\.me)/(?:addstickers|addemoji)/([A-Za-z0-9_]+)", combined or "")
            if m: sn = m.group(1)
    if not sn:
        await msg.reply_text("⚠ رد على ملصق."); return
    key = sn.lower()
    if key not in DB["packs"]:
        await msg.reply_text(get_text(uid, "not_found")); return
    DB["packs"][key]["work"] = wn
    if not DB["packs"][key].get("character"):
        DB["packs"][key]["character"] = "All"
    save_db(DB)
    await msg.reply_text(f"✓ <code>{html.escape(wn)}</code>", parse_mode="HTML")

async def cmd_reclassify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID: return
    msg = update.effective_message
    r = msg.reply_to_message; sn = None
    if r:
        if r.sticker and getattr(r.sticker, "set_name", None): sn = r.sticker.set_name
        else:
            combined = combine_text_and_entity_links(r)
            m = re.search(r"(?:t\.me|telegram\.me)/(?:addstickers|addemoji)/([A-Za-z0-9_]+)", combined or "")
            if m: sn = m.group(1)
    if not sn:
        await msg.reply_text("⚠ رد على ملصق."); return
    key = sn.lower()
    pack = DB["packs"].get(key)
    if not pack:
        await msg.reply_text(get_text(OWNER_ID, "not_found")); return
    await msg.reply_text(get_text(OWNER_ID, "ai_classifying"))
    old = pack.get("title", "")
    res = await ai_classify_pack(old, suggest_name=True)
    if not res:
        await msg.reply_text(get_text(OWNER_ID, "ai_classify_fail")); return
    pack["category"] = res["category"]
    pack["work"] = res["work"]
    pack["character"] = res.get("character") or _normalize_character(old, res["work"], "")
    extra = ""
    if res.get("suggested_name") and res["suggested_name"] != old:
        pack["title"] = res["suggested_name"]
        extra = "\n" + get_text(OWNER_ID, "suggested_name_changed",
                                old=html.escape(old), new=html.escape(res["suggested_name"]))
    save_db(DB)
    await msg.reply_text(get_text(OWNER_ID, "reclassify_done",
                                  label=get_category_label(res["category"], OWNER_ID),
                                  work=html.escape(res["work"]),
                                  character=html.escape(res.get("character") or "—")) + extra,
                         parse_mode="HTML")

async def cmd_backfill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message
    if not (DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key")):
        await msg.reply_text("⚠ AI غير مفعّل."); return
    context.bot_data["stop_scan"] = False
    todo = [(k, p) for k, p in DB["packs"].items() if not p.get("work")]
    if not todo:
        await msg.reply_text(get_text(OWNER_ID, "ai_backfill_none")); return
    total = len(todo)
    st = await msg.reply_text(get_text(OWNER_ID, "ai_backfill_started", count=total), parse_mode="HTML")
    ok = 0
    BATCH = CLASSIFY_BATCH_SIZE
    for start_i in range(0, total, BATCH):
        if context.bot_data.get("stop_scan"):
            context.bot_data["stop_scan"] = False
            save_db(DB)
            try:
                await st.edit_text(get_text(OWNER_ID, "scan_stopped",
                    bar=make_progress_bar(start_i, total), done=start_i, total=total, ok=ok),
                    parse_mode="HTML")
            except Exception: pass
            return
        batch = todo[start_i:start_i + BATCH]
        titles = [(k, p.get("title", "")) for k, p in batch]
        results = await ai_classify_batch(titles, suggest_names=True)
        for k, pack in batch:
            res = results.get(k)
            if res:
                pack["category"] = res["category"]
                pack["work"] = res["work"]
                pack["character"] = res.get("character") or _normalize_character(pack.get("title", ""), res["work"], "")
                if res.get("suggested_name") and res["suggested_name"] != pack.get("title"):
                    pack["title"] = res["suggested_name"]
                ok += 1
        done = min(start_i + BATCH, total)
        save_db(DB)
        try:
            await st.edit_text(get_text(OWNER_ID, "ai_backfill_progress", done=done, total=total, ok=ok), parse_mode="HTML")
        except Exception: pass
        if done < total:
            await asyncio.sleep(CLASSIFY_SLEEP_BETWEEN)
    save_db(DB)
    try: await st.edit_text(get_text(OWNER_ID, "ai_backfill_done", ok=ok, total=total), parse_mode="HTML")
    except Exception: pass

async def cmd_scan_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message
    if not (DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key")):
        await msg.reply_text(get_text(OWNER_ID, "scan_all_need_ai")); return
    all_packs = list(DB["packs"].items())
    if not all_packs:
        await msg.reply_text(get_text(OWNER_ID, "no_packs_yet")); return
    total = len(all_packs); ok = 0; fail = 0; renamed = 0
    context.bot_data["stop_scan"] = False
    st = await msg.reply_text(get_text(OWNER_ID, "scan_all_started", count=total, bar=make_progress_bar(0, total), done=0), parse_mode="HTML")
    BATCH = CLASSIFY_BATCH_SIZE
    for start_i in range(0, total, BATCH):
        if context.bot_data.get("stop_scan"):
            context.bot_data["stop_scan"] = False
            save_db(DB)
            try: await st.edit_text(get_text(OWNER_ID, "scan_stopped", bar=make_progress_bar(start_i, total), done=start_i, total=total, ok=ok), parse_mode="HTML")
            except Exception: pass
            return
        batch = all_packs[start_i:start_i + BATCH]
        titles = [(k, p.get("title", "")) for k, p in batch]
        results = await ai_classify_batch(titles, suggest_names=True)
        for k, pack in batch:
            res = results.get(k)
            if res:
                pack["category"] = res["category"]
                pack["work"] = res["work"]
                pack["character"] = res.get("character") or _normalize_character(pack.get("title", ""), res["work"], "")
                if res.get("suggested_name") and res["suggested_name"] != pack.get("title"):
                    pack["title"] = res["suggested_name"]
                    renamed += 1
                ok += 1
            else:
                fail += 1
        done = min(start_i + BATCH, total)
        save_db(DB)
        try:
            await st.edit_text(get_text(OWNER_ID, "scan_all_progress", done=done, total=total, ok=ok, fail=fail, bar=make_progress_bar(done, total)), parse_mode="HTML")
        except Exception: pass
        if done < total:
            await asyncio.sleep(CLASSIFY_SLEEP_BETWEEN)
    save_db(DB)
    try: await st.edit_text(get_text(OWNER_ID, "scan_all_done", total=total, ok=ok, renamed=renamed, fail=fail), parse_mode="HTML")
    except Exception: pass

async def cmd_scanothers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message
    if not (DB["settings"].get("ai_enabled") and DB["settings"].get("ai_api_key")):
        await msg.reply_text(get_text(OWNER_ID, "scan_all_need_ai")); return
    all_packs = [(k, p) for k, p in DB["packs"].items() if not p.get("work")]
    if not all_packs:
        await msg.reply_text(get_text(OWNER_ID, "ai_backfill_none")); return
    total = len(all_packs); ok = 0; fail = 0; renamed = 0
    context.bot_data["stop_scan"] = False
    st = await msg.reply_text(get_text(OWNER_ID, "scan_others_started", count=total, bar=make_progress_bar(0, total), done=0), parse_mode="HTML")
    BATCH = CLASSIFY_BATCH_SIZE
    for start_i in range(0, total, BATCH):
        if context.bot_data.get("stop_scan"):
            context.bot_data["stop_scan"] = False
            save_db(DB)
            try: await st.edit_text(get_text(OWNER_ID, "scan_stopped", bar=make_progress_bar(start_i, total), done=start_i, total=total, ok=ok), parse_mode="HTML")
            except Exception: pass
            return
        batch = all_packs[start_i:start_i + BATCH]
        titles = [(k, p.get("title", "")) for k, p in batch]
        results = await ai_classify_batch(titles, suggest_names=True)
        for k, pack in batch:
            res = results.get(k)
            if res:
                pack["category"] = res["category"]
                pack["work"] = res["work"]
                pack["character"] = res.get("character") or _normalize_character(pack.get("title", ""), res["work"], "")
                if res.get("suggested_name") and res["suggested_name"] != pack.get("title"):
                    pack["title"] = res["suggested_name"]
                    renamed += 1
                ok += 1
            else:
                fail += 1
        done = min(start_i + BATCH, total)
        save_db(DB)
        try:
            await st.edit_text(get_text(OWNER_ID, "scan_all_progress", done=done, total=total, ok=ok, fail=fail, bar=make_progress_bar(done, total)), parse_mode="HTML")
        except Exception: pass
        if done < total:
            await asyncio.sleep(CLASSIFY_SLEEP_BETWEEN)
    save_db(DB)
    try: await st.edit_text(get_text(OWNER_ID, "scan_all_done", total=total, ok=ok, renamed=renamed, fail=fail), parse_mode="HTML")
    except Exception: pass

async def cmd_settrigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message; args = context.args or []
    if not args:
        cur = DB["settings"].get("trigger_name", DEFAULT_TRIGGER_NAME)
        await msg.reply_text(f"◉ <code>{html.escape(cur)}</code>", parse_mode="HTML"); return
    new_name = args[0].strip().lower()
    if len(new_name) < 2:
        await msg.reply_text("⚠ قصير"); return
    DB["settings"]["trigger_name"] = new_name; save_db(DB)
    await msg.reply_text(f"✓ <code>{html.escape(new_name)}</code>", parse_mode="HTML")

async def cmd_setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message; args = context.args or []
    if not args:
        cur = DB["settings"].get("group_link", "") or "—"
        await msg.reply_text(f"◉ <code>{html.escape(cur)}</code>", parse_mode="HTML"); return
    if args[0].lower() in ("del","delete","none","حذف"):
        DB["settings"]["group_link"] = ""; save_db(DB)
        await msg.reply_text("✓"); return
    DB["settings"]["group_link"] = args[0].strip(); save_db(DB)
    await msg.reply_text("✓", parse_mode="HTML")

async def cmd_setchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message; args = context.args or []
    if not args:
        cur = DB["settings"].get("channel_link", "") or "—"
        await msg.reply_text(f"◉ <code>{html.escape(cur)}</code>", parse_mode="HTML"); return
    if args[0].lower() in ("del","delete","none","حذف"):
        DB["settings"]["channel_link"] = ""; save_db(DB)
        await msg.reply_text("✓"); return
    DB["settings"]["channel_link"] = args[0].strip(); save_db(DB)
    await msg.reply_text("✓", parse_mode="HTML")

async def cmd_setsub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message; args = context.args or []
    if not args:
        s = DB["settings"]
        cur = s.get("force_sub_channel", "") or "—"
        en = "مفعّل" if s.get("force_sub_enabled") else "متوقف"
        await msg.reply_text(f"◉ <code>{html.escape(cur)}</code>\n◉ <b>{en}</b>", parse_mode="HTML"); return
    if args[0].lower() in ("del","delete","none","حذف","off"):
        DB["settings"]["force_sub_channel"] = ""
        DB["settings"]["force_sub_enabled"] = False
        save_db(DB)
        await msg.reply_text("✓"); return
    DB["settings"]["force_sub_channel"] = args[0].strip()
    DB["settings"]["force_sub_enabled"] = True
    save_db(DB)
    await msg.reply_text("✓", parse_mode="HTML")

async def cmd_forcesub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message; args = context.args or []
    if not args:
        en = "مفعّل" if DB["settings"].get("force_sub_enabled") else "متوقف"
        await msg.reply_text(f"◉ <b>{en}</b>", parse_mode="HTML"); return
    v = args[0].lower()
    if v in ("on","1","true","تشغيل"):
        if not DB["settings"].get("force_sub_channel"):
            await msg.reply_text("⚠ حدد القناة"); return
        DB["settings"]["force_sub_enabled"] = True; save_db(DB)
        await msg.reply_text("✓")
    elif v in ("off","0","false","ايقاف","إيقاف"):
        DB["settings"]["force_sub_enabled"] = False; save_db(DB)
        await msg.reply_text("✓")

async def cmd_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; msg = update.effective_message
    if not user or not msg: return
    await msg.reply_text(get_datetime_reply(user.id, get_current_datetime_info()), parse_mode="HTML")

async def cmd_test_reactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID: return
    msg = update.effective_message
    if not msg: return
    sample = pick_random_reactions(15)
    await msg.reply_text(f"🎨 {' '.join(sample)}", parse_mode="HTML")

async def cmd_wakeup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; msg = update.effective_message
    if not msg: return
    chat_id = msg.chat_id
    clear_chat_quiet(context, chat_id)
    if msg.chat.type == "private":
        try: await msg.reply_text(get_text(user.id, "wake_reply"))
        except Exception: pass
    else:
        try: await try_react(context.bot, chat_id, msg.message_id, pick_random_reactions(8, "respect"))
        except Exception:
            try: await msg.reply_text(get_text(user.id, "wake_reply"))
            except Exception: pass

# ========================= Main =========================
def main():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise ValueError("Please place your bot token in TELEGRAM_TOKEN")
    request = HTTPXRequest(connect_timeout=180.0, read_timeout=180.0, write_timeout=180.0, pool_timeout=180.0)
    app = (Application.builder().token(TELEGRAM_TOKEN).request(request).post_init(post_init).build())
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("random", cmd_random))
    app.add_handler(CommandHandler("randomstats", cmd_randomstats))
    app.add_handler(CommandHandler("setai", cmd_setai))
    app.add_handler(CommandHandler("aion", cmd_aion))
    app.add_handler(CommandHandler("aioff", cmd_aioff))
    app.add_handler(CommandHandler("aiprompt", cmd_aiprompt))
    app.add_handler(CommandHandler("aimodel", cmd_aimodel))
    app.add_handler(CommandHandler("aibase", cmd_aibase))
    app.add_handler(CommandHandler("aismart", cmd_aismart))
    app.add_handler(CommandHandler("testai", cmd_test_ai))
    app.add_handler(CommandHandler("rename", cmd_rename))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("addpremium", cmd_addpremium))
    app.add_handler(CommandHandler("del", cmd_del))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("s", cmd_scan))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CommandHandler("setvideo", cmd_setvideo))
    app.add_handler(CommandHandler("delvideo", cmd_delvideo))
    app.add_handler(CommandHandler("settrigger", cmd_settrigger))
    app.add_handler(CommandHandler("setgroup", cmd_setgroup))
    app.add_handler(CommandHandler("setchannel", cmd_setchannel))
    app.add_handler(CommandHandler("setsub", cmd_setsub))
    app.add_handler(CommandHandler("forcesub", cmd_forcesub))
    app.add_handler(CommandHandler("wakeup", cmd_wakeup))
    app.add_handler(CommandHandler("time", cmd_time))
    app.add_handler(CommandHandler("testreact", cmd_test_reactions))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("deladmin", cmd_deladmin))
    app.add_handler(CommandHandler("admins", cmd_admins))
    app.add_handler(CommandHandler("setcat", cmd_setcat))
    app.add_handler(CommandHandler("setwork", cmd_setwork))
    app.add_handler(CommandHandler("reclassify", cmd_reclassify))
    app.add_handler(CommandHandler("backfill", cmd_backfill))
    app.add_handler(CommandHandler("scanall", cmd_scan_all))
    app.add_handler(CommandHandler("scanothers", cmd_scanothers))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.User(OWNER_ID) & filters.ChatType.PRIVATE, handle_backup_document), group=-1)
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(InlineQueryHandler(inline_query_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_main))
    app.add_handler(MessageHandler(filters.REPLY, handle_admin_reply), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request_text), group=3)
    app.run_polling(drop_pending_updates=True, allowed_updates=None, poll_interval=0.0, timeout=300, bootstrap_retries=-1)

if __name__ == "__main__":
    main()
