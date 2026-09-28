
---

## 📄 4) `main.py` — الكود الكامل

```python
# =========================================================
# Auto-install dependencies
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

    if need_install:
        for cmd in (
            [sys.executable, "-m", "pip", "install", "--upgrade",
             "python-telegram-bot>=21.0", "httpx"],
            [sys.executable, "-m", "pip", "install", "--user", "--upgrade",
             "python-telegram-bot>=21.0", "httpx"],
        ):
            try:
                subprocess.check_call(cmd)
                break
            except Exception:
                continue


_ensure_dependencies()

# =========================================================
# Imports
# =========================================================
import os
import io
import json
import re
import html
import asyncio
import difflib
import random
from pathlib import Path
from urllib.parse import quote, unquote
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InputFile,
    MessageEntity,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    InlineQueryHandler,
)
from telegram.helpers import escape_markdown
from telegram.request import HTTPXRequest

# =========================================================
# Config
# =========================================================
TELEGRAM_TOKEN = "8950210404:AAFFLFk3Dj_oUW9xs_a6W0Wm-lxKGqEjIFc"
OWNER_ID = 5807843837
MY_CHANNEL_ID = "ahmshy"
CHANNEL_URL = f"https://t.me/{MY_CHANNEL_ID}"

DB_DIR = Path("packs_db")
DB_DIR.mkdir(exist_ok=True)
INDEX_FILE = DB_DIR / "index.json"
ITEMS_PER_PAGE = 5

SEARCH_CB_PREFIX = "pgs"
ALPHA_CB_PREFIX = "alpha"
SHOW_ALPHA = "show_alpha"
SHOW_BANNED = "show_banned"
UNBAN_CB = "unban"

BACKUP_FILE_NAME = "packs_db_backup.json"
BACKUP_INTERVAL = 86400

RECENT_PACKS_LIMIT = 10
PACKS_BEFORE_NOTIFY = 10
NOTIFY_DELAY = 30 * 60
NOTIFY_STAGGER = 3

APP_REF = None

# =========================================================
# Button helper
# =========================================================
def make_btn(text, callback_data=None, url=None, style=None):
    kwargs = {"text": text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if style is not None:
        kwargs["style"] = style
    try:
        return InlineKeyboardButton(**kwargs)
    except TypeError:
        kwargs.pop("style", None)
        return InlineKeyboardButton(**kwargs)

# =========================================================
# Deep Link Helpers
# =========================================================
_B36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"


def encode_chat_b36(chat_id, length=12):
    negative = chat_id < 0
    n = abs(int(chat_id))
    if n == 0:
        encoded = "0"
    else:
        encoded = ""
        while n > 0:
            encoded = _B36_CHARS[n % 36] + encoded
            n //= 36
    sign = "n" if negative else "p"
    padded = sign + encoded.zfill(length - 1)
    return padded[:length]


def decode_chat_b36(s):
    if not s or len(s) < 2:
        return None
    sign = s[0]
    body = s[1:]
    n = 0
    for ch in body:
        if ch not in _B36_CHARS:
            return None
        n = n * 36 + _B36_CHARS.index(ch)
    if sign == "n":
        n = -n
    return n


def make_deep_link(bot_username, set_name, chat_id=None):
    if not bot_username:
        return None
    if chat_id is None:
        return f"https://t.me/{bot_username}?start=pack_{set_name}"
    chat_enc = encode_chat_b36(chat_id)
    return f"https://t.me/{bot_username}?start=open_{chat_enc}_{set_name}"


def parse_deep_link(arg):
    if not arg:
        return (None, None)
    if arg.startswith("pack_"):
        return (arg[5:], None)
    if arg.startswith("open_"):
        rest = arg[5:]
        if len(rest) < 13:
            return (None, None)
        chat_part = rest[:12]
        remaining = rest[12:]
        if remaining.startswith("_"):
            set_name = remaining[1:]
        else:
            set_name = remaining
        chat_id = decode_chat_b36(chat_part)
        return (set_name, chat_id)
    return (None, None)


async def get_group_url(bot, chat_id):
    try:
        chat = await bot.get_chat(chat_id)
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}"
        if getattr(chat, "invite_link", None):
            return chat.invite_link
        try:
            invite = await bot.create_chat_invite_link(chat_id)
            return invite.invite_link
        except Exception:
            return None
    except Exception:
        return None

# =========================================================
# Source Detection
# =========================================================
def is_channel_message(msg):
    try:
        sender = getattr(msg, "sender_chat", None)
        if sender and getattr(sender, "type", None) == "channel":
            return True
        fwd = getattr(msg, "forward_from_chat", None)
        if fwd and getattr(fwd, "type", None) == "channel":
            return True
    except Exception:
        pass
    return False


def has_hidden_pack_link(msg):
    try:
        entities = list(getattr(msg, "entities", None) or []) + \
                   list(getattr(msg, "caption_entities", None) or [])
        for ent in entities:
            if ent.type == "text_link" and getattr(ent, "url", None):
                url = ent.url
                if "addstickers" in url or "addemoji" in url:
                    return True
    except Exception:
        pass
    return False

# =========================================================
# Texts
# =========================================================
TEXTS = {
    "ar": {
        "welcome": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "◆ <b>أهلاً {user} في بوت أرشيف الملصقات</b> ▣\n\n"
            "⌕ <b>البحث بالأمر:</b>\n"
            "•|| اكتب <code>/search &lt;كلمة&gt;</code>\n\n"
            "➤ <b>البحث المضمن:</b>\n"
            "•|| اكتب <code>@{bot} &lt;كلمة&gt;</code> في أي محادثة!\n\n"
            "◉ <b>قناتنا:</b> <a href=\"https://t.me/AhmShY\">@Ahmshy</a>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "group_welcome": (
            "◆ <b>بوت أرشيف الملصقات</b>\n"
            "⌕ استخدم <code>/search &lt;كلمة&gt;</code> أو الوضع المضمن "
            "<code>@{bot} &lt;كلمة&gt;</code>\n"
            "◉ القناة: @Ahmshy"
        ),
        "lang_set": "✓ تم تعيين اللغة العربية.",
        "banned": "⊘ أنت محظور من استخدام هذا البوت.",
        "unknown_cmd": (
            "⚡ <b>أمر غير معروف.</b>\n\n"
            "⌕ استخدم <code>/search &lt;كلمة&gt;</code>\n"
            "➤ أو الوضع المضمن: <code>@{bot} &lt;كلمة&gt;</code>"
        ),
        "only_private": "هذا الزر يعمل في المحادثة الخاصة فقط.",
        "button_not_for_you": "⚡ هذا الزر ليس لك.",
        "main_menu": "⌂ القائمة الرئيسية",
        "view_packs": "▤ عرض الحزم",
        "commands": "☰ الأوامر",
        "statistics": "▦ الإحصائيات",
        "request_pack": "✉ طلب حزمة",
        "change_lang_btn": "◐ اللغة",
        "owner_contact": "☏ المالك",
        "channel_link": "◉ القناة",
        "help_btn": "▤ شرح الاستخدام",
        "change_lang": "◐ <b>اختر لغتك / Choose your language</b>",
        "new_packs_btn": "✦ آخر الحزم المضافة",
        "backup_btn": "⬇ نسخة احتياطية",
        "video_manage_btn": "▶ فيديو الشرح: {status}",
        "forwarding_btn": "✉ التوجيه: {status}",
        "premium_packs_btn": "★ حزم الميزة",
        "regular_packs_btn": "▣ حزم عادية",
        "save_btn": "✓ حفظ",
        "rename_btn": "✎ إعادة تسمية",
        "ignore_btn": "✕ تجاهل",
        "report_delete_btn": "✕ حذف",
        "report_ignore_btn": "✕ تجاهل",
        "video_delete_btn": "✕ حذف الفيديو",
        "request_again_btn": "✉ طلب حزمة أخرى",
        "channel_btn": "◉ قناتنا الأساسية",
        "resend_request_now": "✉ إعادة إرسال الطلب الآن",
        "subscribe_channel": "◉ اشترك في قناتنا",
        "request_pack_btn": "✉ طلب الحزمة",
        "easy_search_btn": "⌕ البحث السهل",
        "back_to_group_btn": "← العودة إلى المجموعة",
        "open_pack_btn": "⛓ اضغط هنا لإضافة الحزمة",
        "open_premium_pack_btn": "⛓ اضغط هنا لفتح الحزمة المميزة",
        "easy_search_prompt": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "⌕ <b>البحث السهل</b>\n"
            "┗━━━━━≪✠≫━━━━━┛\n\n"
            "▤ اكتب اسم <b>شخصية معينة</b> أو <b>عمل كامل</b>\n\n"
            "◈ <b>أمثلة:</b>\n"
            "•|| <code>Naruto</code> – للبحث عن شخصية\n"
            "•|| <code>One Piece</code> – للبحث عن عمل كامل\n"
            "•|| <code>Gojo</code> – للبحث عن شخصية\n\n"
            "⚡ <b>ملاحظة:</b> يجب أن يكون الاسم بالإنجليزية"
        ),
        "easy_search_placeholder": "اكتب هنا...",
        "pack_open_from_group_title": "▣ <b>{title}</b>",
        "pack_not_found_for_user": "⚡ الحزمة غير موجودة.",
        "search_forwarded_by_owner_sent": "✓ تم إرسال نتائج البحث إلى المستخدم.",
        "search_forwarded_by_owner_empty": "⚡ يرجى كتابة كلمة البحث بعد الأمر.\n•|| مثال: <code>/search Naruto</code>",
        "search_results_for_user": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "<a href=\"https://t.me/AhmShY\">⌕ نتائج البحث عن:</a> <code>{query}</code>\n"
            "•|| ▣ عدد الحزم: {count}\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "stats": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "▦ <b>الإحصائيات</b>\n\n"
            "•|| ▣ <b>الحزم:</b> <code>{packs}</code>\n"
            "•|| ★ <b>البريميوم:</b> <code>{premium}</code>\n"
            "•|| ◉ <b>المستخدمون:</b> <code>{users}</code>\n"
            "•|| ◆ <b>المشرفون:</b> <code>{admins}</code>\n"
            "•|| ⊘ <b>المحظورون:</b> <code>{banned}</code>\n"
            "•|| ⌕ <b>عمليات البحث:</b> <code>{searches}</code>\n"
            "•|| ★ <b>أكثر استعلام:</b> <code>{top}</code>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "admin_commands": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "☰ <b>قائمة الأوامر</b>\n\n"
            "• <b>أوامر المشرفين والمالك</b>\n"
            "• <code>/search &lt;كلمة&gt;</code> – بحث\n"
            "• <code>/add</code> (رد على ملصق) – إضافة\n"
            "• <code>/addpremium &lt;رابط&gt;</code> – بريميوم قسري ★\n"
            "• <code>/rename &lt;اسم&gt;</code> (رد على ملصق أو رابط) – تسمية\n"
            "• <code>/del</code> (رد على ملصق) – حذف\n"
            "• <code>/scan</code> – فحص الحزم\n"
            "• <code>حظر @username</code> / <code>رفع الحظر @username</code>\n"
            "• <code>/broadcast</code> (رد على رسالة) – بث\n"
            "• <code>/backup</code> – نسخة احتياطية ⬇\n"
            "• <code>/setvideo</code> (رد على فيديو) – تعيين فيديو الشرح\n"
            "• <code>/delvideo</code> – حذف فيديو الشرح\n\n"
            "▤ <b>لإضافة حزم:</b>\n"
            "أرسل رابط <code>addstickers</code> (عادي) أو <code>addemoji</code> (بريميوم)\n"
        ),
        "pack_added": "✓ <b>تمت الإضافة بنجاح!</b>\n•|| ▣ <b>الاسم:</b> {name}",
        "pack_added_simple": "✓ <b>تمت الإضافة:</b> {name}",
        "enter_name": "⚡ <b>اكتب اسماً صالحاً لهذه الحزمة:</b>",
        "new_pack_detected": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ *تم اكتشاف حزمة جديدة!*\n"
            "•|| ◉ *من:* [{user}](tg://user?id={uid})\n"
            "•|| ▣ *الاسم:* `{src}`\n"
            "•|| ✦ *المفلتر:* `{filtered}`\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "new_pack_from_channel": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ *حزمة من قناة*\n"
            "•|| ▣ *الاسم:* `{src}`\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "already_saved": "⚡ *محفوظة سابقاً.*",
        "needs_name": "⚡ *بحاجة لاسم مخصص. اكتبه الآن:*",
        "saved": "✓ *تم الحفظ:* `{name}`",
        "error": "✕ *خطأ.*",
        "type_new_name": "✎ *اكتب الاسم الجديد الآن:*",
        "ignored": "✕ *تم التجاهل.*",
        "reply_to_sticker_add": "⚡ رد على ملصق لإضافته.",
        "not_from_pack": "⚡ هذا الملصق ليس من حزمة.",
        "already_exists": "⚡ هذه الحزمة موجودة بالفعل.",
        "invalid_name": "⚡ عذراً، الاسم غير صالح.",
        "error_occurred": "✕ خطأ: {err}",
        "reply_to_sticker_del": "⚡ رد على ملصق من الحزمة المراد حذفها.",
        "not_found": "⚡ هذه الحزمة غير موجودة.",
        "pack_not_found_short": "⚡ الحزمة غير موجودة.",
        "deleted": "✓ تم الحذف: <code>{name}</code>",
        "deleted_short": "✓ تم الحذف!",
        "reply_to_sticker_rename": (
            "⚡ <b>رد على ملصق أو على رسالة تحتوي رابط حزمة</b>\n"
            "•|| ثم اكتب: <code>/rename الاسم الجديد</code>"
        ),
        "usage_rename": "⚡ الاستخدام: <code>/rename &lt;الاسم الجديد&gt;</code>",
        "enter_new_name": "✎ <b>أرسل الاسم الجديد للحزمة:</b>\n•|| ▣ <code>{set_name}</code>",
        "no_results": "✕ لا توجد نتائج لـ <code>{query}</code>.",
        "search_results": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "<a href=\"https://t.me/AhmShY\">⌕ نتائج البحث عن:</a> <code>{query}</code>\n"
            "•|| ▣ عدد الحزم: {count}\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "enter_search_term": "⚡ <b>يرجى إدخال كلمة للبحث.</b>\n•|| مثال: <code>/search anime</code>",
        "did_you_mean": "هل تقصد: {word}؟",
        "no_results_short": "لا نتائج",
        "alpha_index_header": "▤ <b>اختر الحرف الأول للحزمة:</b>",
        "alpha_filter": "▤ <b>الحزم التي تبدأ بحرف {letter}</b> (عددها {count})",
        "alpha_unknown": "▤ <b>الحزم التي لا تبدأ بحرف لاتيني</b> (عددها {count})",
        "no_packs_letter": "✕ لا توجد حزم تبدأ بـ {letter}",
        "recent_packs_header": "✦ <b>آخر الحزم المضافة</b>",
        "premium_packs_header": "★ <b>حزم الميزة</b> (عددها {count})",
        "regular_packs_header": "▣ <b>الحزم العادية</b> (عددها {count})",
        "no_recent_packs": "⚡ لا توجد حزم مضافة مؤخراً.",
        "no_premium_packs": "⚡ لا توجد حزم ميزة بعد.",
        "no_regular_packs": "⚡ لا توجد حزم عادية بعد.",
        "cmd_from_user": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>أمر من:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▤ <b>الأمر:</b> <code>{cmd}</code>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "msg_from_user": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>رسالة من:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "new_user_notification": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ <b>مستخدم جديد!</b>\n"
            "•|| ◉ <b>الاسم:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▦ <b>التاريخ:</b> {date}\n"
            "•|| ▦ <b>عدد المستخدمين الآن:</b> <code>{total}</code>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "cant_ban_owner": "⚡ لا يمكن حظر المالك.",
        "user_banned": "✓ تم حظر {user}.",
        "already_banned": "⚡ هذا المستخدم محظور بالفعل.",
        "user_unbanned": "✓ تم رفع الحظر عن {user}.",
        "not_banned": "⚡ هذا المستخدم غير محظور.",
        "not_banned_short": "⚡ غير محظور.",
        "unbanned_msg": "✓ تم فك الحظر!",
        "banned_list_header": "⊘ <b>قائمة المحظورين</b>",
        "no_banned_users": "✓ لا يوجد محظورون.",
        "banned_user_item": "• {user} (<code>{uid}</code>)",
        "show_banned_btn": "⊘ المحظورون",
        "unban_btn": "✦ فك الحظر",
        "user_not_found": "⚡ لم يتم العثور على المستخدم.",
        "reply_broadcast": "⚡ <b>رد على الرسالة المراد بثها.</b>",
        "no_users": "⚡ <b>لا يوجد مستخدمون للبث.</b>",
        "broadcast_done": "✓ <b>تم البث!</b>\n•|| تم التسليم لـ: <code>{count}</code> مستخدم.",
        "admin_reply_sent": "✓ تم إرسال ردك إلى المستخدم.",
        "admin_reply_fail": "⚡ تعذر إرسال الرد، ربما قام المستخدم بحظر البوت.",
        "forwarding_toggled": "✓ تم تحديث التوجيه",
        "forwarding_on": "● مفعّل",
        "forwarding_off": "○ متوقف",
        "admin_reply_header": "✉ <b>رد من الإدارة:</b>",
        "request_sent": "✓ تم إرسال طلبك إلى المالك، سيتم الرد عليك قريباً.",
        "request_notification": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>طلب حزمة جديد</b>\n"
            "•|| ◉ <b>من:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▤ <b>الطلب:</b> {request}\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "ask_request_pack": "✉ <b>يرجى كتابة اسم الحزمة أو وصفها التي تبحث عنها:</b>",
        "request_from_owner_msg": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>يمكنك طلب الحزمة من المالك</b>\n\n"
            "•|| اكتب اسم الحزمة أو وصفها وسيتم إرسالها للمالك مباشرة:\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "request_executed": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ <b>تم تنفيذ طلبك بنجاح!</b>\n\n"
            "•|| نتمنى أن تنال الحزمة إعجابك\n"
            "•|| يسعدنا خدمتك في أي وقت\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "resend_request_header": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>إعادة إرسال طلب</b>\n"
            "•|| ◉ <b>من:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▤ <b>الطلب:</b> {request}\n"
            "┗━━━━━≪✠≫━━━━━┛\n\n"
            "← <i>رد على هذه الرسالة لتوصيل الرد للطالب</i>"
        ),
        "no_saved_request": "⚡ لا يوجد طلب محفوظ",
        "report_success": "⚠ تم الإبلاغ بنجاح، سيتم مراجعة الحزمة.",
        "report_notification": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "⚠ <b>بلاغ عن حزمة</b>\n"
            "•|| ◉ <b>من:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▣ <b>الحزمة:</b> {pack_name}\n"
            "•|| ⛓ <b>الرابط:</b> <a href=\"{pack_url}\">{pack_name}</a>\n"
            "•|| ▤ <b>السبب:</b> {reason}\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "report_handled": "✓ تم التعامل مع البلاغ.",
        "report_ignored": "✕ تم تجاهل البلاغ.",
        "ask_report_reason": "▤ <b>يرجى كتابة سبب البلاغ:</b>",
        "ask_report_reason_short": "⚡ الرجاء كتابة سبب البلاغ.",
        "help_text": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "▤ <b>شرح استخدام البوت</b>\n"
            "┗━━━━━≪✠≫━━━━━┛\n\n"
            "⌕ <b>1) البحث عن الملصقات:</b>\n"
            "•|| اكتب هنا: <code>/search كلمة</code>\n"
            "•|| أو في أي محادثة: <code>@البوت كلمة</code>\n"
            "•|| أو اضغط زر <b>«▤ عرض الحزم»</b> وتصفح بالحروف\n\n"
            "▣ <b>2) عرض الحزم:</b>\n"
            "•|| اضغط <b>«▤ عرض الحزم»</b>\n"
            "•|| اختر الحرف الأول من اسم الحزمة\n"
            "•|| اضغط على الحزمة لإضافتها لتيليجرام\n\n"
            "★ <b>3) الحزم البريميوم:</b>\n"
            "•|| تظهر بنجمة <b>★</b> قبل الاسم\n"
            "•|| بعضها يحتاج <b>تيليجرام بريميوم</b> لاستخدامها\n\n"
            "✉ <b>4) طلب حزمة:</b>\n"
            "•|| إذا لم تجد حزمة، اضغط <b>«✉ طلب حزمة»</b>\n"
            "•|| اكتب اسم/وصف الحزمة ← سيصل للمالك\n\n"
            "⚠ <b>5) الإبلاغ عن حزمة:</b>\n"
            "•|| بجانب كل حزمة في البحث يوجد زر ⚠\n"
            "•|| اضغطه واكتب سبب البلاغ\n\n"
            "◐ <b>6) تغيير اللغة:</b>\n"
            "•|| اضغط زر <b>«◐ اللغة»</b>\n\n"
            "◉ <b>7) قناتنا:</b>\n"
            "•|| <a href=\"https://t.me/AhmShY\">@Ahmshy</a>\n\n"
            "◈ <b>نصيحة:</b> استخدم زر <b>«⌕ البحث»</b> في الوضع المضمن للوصول السريع من أي محادثة!\n\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "set_video_success": "✓ تم حفظ فيديو الشرح بنجاح!",
        "set_video_reply": "⚡ <b>رد على فيديو</b> ثم اكتب <code>/setvideo</code>",
        "del_video_success": "✓ تم حذف فيديو الشرح.",
        "del_video_not_found": "⚡ لا يوجد فيديو شرح محفوظ.",
        "video_manage_info": (
            "▶ <b>إدارة فيديو الشرح</b>\n\n"
            "•|| <b>الحالة:</b> {status}\n\n"
            "◆ <b>لإضافة فيديو:</b>\n"
            "•|| رد على الفيديو بأمر <code>/setvideo</code>\n\n"
            "◆ <b>لحذف الفيديو:</b>\n"
            "•|| استخدم أمر <code>/delvideo</code>\n\n"
            "◈ يمكنك أيضاً تجربة الشرح: زر «▤ شرح الاستخدام» في القائمة."
        ),
        "video_manage_info_deleted": (
            "▶ <b>إدارة فيديو الشرح</b>\n\n"
            "•|| <b>الحالة:</b> ✕ غير مضاف\n\n"
            "◆ <b>لإضافة فيديو:</b>\n"
            "•|| رد على الفيديو بأمر <code>/setvideo</code>"
        ),
        "video_status_added": "✓ مضاف",
        "video_status_not_added": "✕ غير مضاف",
        "backup_creating": "⌛ جاري إنشاء النسخة...",
        "backup_sent": "✓ تم إرسال النسخة لك!",
        "backup_failed": "✕ فشل إنشاء النسخة",
        "scan_started": "⌕ بدء فحص الحزم...",
        "scan_complete": (
            "✓ <b>تم الفحص!</b>\n\n"
            "•|| ✕ تم حذف {deleted} حزمة.\n"
            "•|| ✎ تم تحديث {updated} حزمة.\n"
            "•|| ✓ لم تتغير {unchanged} حزمة."
        ),
        "new_packs_notification": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ <b>تم إضافة حزم جديدة!</b>\n\n"
            "•|| اضغط /start لرؤيتها ⌕\n"
            "•|| ◉ <a href=\"https://t.me/AhmShY\">قناتنا</a>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "inline_all_packs": "▣ جميع الحزم ({count})",
        "inline_pack_item": "{num}. {title}",
        "inline_all_packs_title": "▣ جميع الحزم المطابقة للبحث:",
        "inline_pack_label": "▣ <b>حزمة ملصقات:</b>",
        "inline_channel_follow": "◉ تابع قناتنا:",
        "inline_pack_count_desc": "عدد الحزم: {count}",
        "inline_pack_link_desc": "اضغط لفتح في البوت",
        "inline_no_results_title": "✕ لا توجد نتائج",
        "inline_no_results_msg": "✕ لا توجد نتائج لـ: <code>{query}</code>",
        "inline_no_results_desc": "لا توجد نتائج مطابقة",
        "inline_msg_header": "⌕ نتائج البحث",
        "inline_msg_query_label": "▤ الاستعلام:",
        "inline_msg_count_label": "▣ عدد الحزم:",
        "inline_msg_hint": "اضغط على اسم الحزمة لفتحها في البوت",
        "inline_msg_channel_label": "◉ قناتنا:",
    },

    "en": {
        "welcome": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "◆ <b>Welcome {user} to the Sticker Archive Bot</b> ▣\n\n"
            "⌕ <b>Search via Command:</b>\n"
            "•|| Type <code>/search &lt;keyword&gt;</code>\n\n"
            "➤ <b>Inline Search:</b>\n"
            "•|| Type <code>@{bot} &lt;keyword&gt;</code> in any chat!\n\n"
            "◉ <b>Our Channel:</b> <a href=\"https://t.me/AhmShY\">@Ahmshy</a>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "group_welcome": (
            "◆ <b>Sticker Archive Bot</b>\n"
            "⌕ Use <code>/search &lt;keyword&gt;</code> or inline "
            "<code>@{bot} &lt;keyword&gt;</code>\n"
            "◉ Channel: @Ahmshy"
        ),
        "lang_set": "✓ Language set to English.",
        "banned": "⊘ You are banned from using this bot.",
        "unknown_cmd": (
            "⚡ <b>Unknown command.</b>\n\n"
            "⌕ Use <code>/search &lt;keyword&gt;</code>\n"
            "➤ Or inline: <code>@{bot} &lt;keyword&gt;</code>"
        ),
        "only_private": "This button works only in private chat.",
        "button_not_for_you": "⚡ This button is not for you.",
        "main_menu": "⌂ Main Menu",
        "view_packs": "▤ View Packs",
        "commands": "☰ Commands",
        "statistics": "▦ Statistics",
        "request_pack": "✉ Request Pack",
        "change_lang_btn": "◐ Language",
        "owner_contact": "☏ Owner",
        "channel_link": "◉ Channel",
        "help_btn": "▤ How to Use",
        "change_lang": "◐ <b>Choose your language / اختر لغتك</b>",
        "new_packs_btn": "✦ Recently Added",
        "backup_btn": "⬇ Backup",
        "video_manage_btn": "▶ Tutorial Video: {status}",
        "forwarding_btn": "✉ Forwarding: {status}",
        "premium_packs_btn": "★ Premium Packs",
        "regular_packs_btn": "▣ Regular Packs",
        "save_btn": "✓ Save",
        "rename_btn": "✎ Rename",
        "ignore_btn": "✕ Ignore",
        "report_delete_btn": "✕ Delete",
        "report_ignore_btn": "✕ Ignore",
        "video_delete_btn": "✕ Delete Video",
        "request_again_btn": "✉ Request Another Pack",
        "channel_btn": "◉ Our Channel",
        "resend_request_now": "✉ Resend Request Now",
        "subscribe_channel": "◉ Subscribe to our channel",
        "request_pack_btn": "✉ Request Pack",
        "easy_search_btn": "⌕ Easy Search",
        "back_to_group_btn": "← Back to Group",
        "open_pack_btn": "⛓ Tap here to add the pack",
        "open_premium_pack_btn": "⛓ Tap here to open the premium pack",
        "easy_search_prompt": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "⌕ <b>Easy Search</b>\n"
            "┗━━━━━≪✠≫━━━━━┛\n\n"
            "▤ Type a <b>character name</b> or a <b>full title</b>\n\n"
            "◈ <b>Examples:</b>\n"
            "•|| <code>Naruto</code> – to search for a character\n"
            "•|| <code>One Piece</code> – to search for a full title\n"
            "•|| <code>Gojo</code> – to search for a character\n\n"
            "⚡ <b>Note:</b> The name must be in English"
        ),
        "easy_search_placeholder": "Type here...",
        "pack_open_from_group_title": "▣ <b>{title}</b>",
        "pack_not_found_for_user": "⚡ Pack not found.",
        "search_forwarded_by_owner_sent": "✓ Search results sent to the user.",
        "search_forwarded_by_owner_empty": "⚡ Please write the search term after the command.\n•|| Example: <code>/search Naruto</code>",
        "search_results_for_user": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "<a href=\"https://t.me/AhmShY\">⌕ Search results for:</a> <code>{query}</code>\n"
            "•|| ▣ Packs found: {count}\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "stats": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "▦ <b>Statistics</b>\n\n"
            "•|| ▣ <b>Packs:</b> <code>{packs}</code>\n"
            "•|| ★ <b>Premium:</b> <code>{premium}</code>\n"
            "•|| ◉ <b>Users:</b> <code>{users}</code>\n"
            "•|| ◆ <b>Admins:</b> <code>{admins}</code>\n"
            "•|| ⊘ <b>Banned:</b> <code>{banned}</code>\n"
            "•|| ⌕ <b>Searches:</b> <code>{searches}</code>\n"
            "•|| ★ <b>Top Query:</b> <code>{top}</code>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "admin_commands": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "☰ <b>Command List</b>\n\n"
            "• <b>Admin & Owner Commands</b>\n"
            "• <code>/search &lt;keyword&gt;</code> – search\n"
            "• <code>/add</code> (reply to sticker) – add pack\n"
            "• <code>/addpremium &lt;link&gt;</code> – force premium ★\n"
            "• <code>/rename &lt;name&gt;</code> (reply to sticker/link) – rename\n"
            "• <code>/del</code> (reply to sticker) – delete pack\n"
            "• <code>/scan</code> – scan packs\n"
            "• <code>حظر @username</code> / <code>رفع الحظر @username</code>\n"
            "• <code>/broadcast</code> (reply to message) – broadcast\n"
            "• <code>/backup</code> – manual backup ⬇\n"
            "• <code>/setvideo</code> (reply to video) – set tutorial video\n"
            "• <code>/delvideo</code> – delete tutorial video\n"
        ),
        "pack_added": "✓ <b>Pack added successfully!</b>\n•|| ▣ <b>Name:</b> {name}",
        "pack_added_simple": "✓ <b>Added:</b> {name}",
        "enter_name": "⚡ <b>Type a valid name for this pack:</b>",
        "new_pack_detected": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ *New Pack Detected!*\n"
            "•|| ◉ *From:* [{user}](tg://user?id={uid})\n"
            "•|| ▣ *Name:* `{src}`\n"
            "•|| ✦ *Filtered:* `{filtered}`\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "new_pack_from_channel": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ *Pack from channel*\n"
            "•|| ▣ *Name:* `{src}`\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "already_saved": "⚡ *Already saved.*",
        "needs_name": "⚡ *Needs custom name. Type it now:*",
        "saved": "✓ *Saved:* `{name}`",
        "error": "✕ *Error.*",
        "type_new_name": "✎ *Type the new name now:*",
        "ignored": "✕ *Ignored.*",
        "reply_to_sticker_add": "⚡ Reply to a sticker to add it.",
        "not_from_pack": "⚡ This sticker is not from a pack.",
        "already_exists": "⚡ This pack already exists.",
        "invalid_name": "⚡ Invalid name.",
        "error_occurred": "✕ Error: {err}",
        "reply_to_sticker_del": "⚡ Reply to a sticker from the pack to delete.",
        "not_found": "⚡ This pack does not exist.",
        "pack_not_found_short": "⚡ Pack not found.",
        "deleted": "✓ Deleted: <code>{name}</code>",
        "deleted_short": "✓ Deleted!",
        "reply_to_sticker_rename": (
            "⚡ <b>Reply to a sticker or a message containing a pack link</b>\n"
            "•|| Then type: <code>/rename New Name</code>"
        ),
        "usage_rename": "⚡ Usage: <code>/rename &lt;New Name&gt;</code>",
        "enter_new_name": "✎ <b>Send the new pack name:</b>\n•|| ▣ <code>{set_name}</code>",
        "no_results": "✕ No results for <code>{query}</code>.",
        "search_results": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "<a href=\"https://t.me/AhmShY\">⌕ Search results for:</a> <code>{query}</code>\n"
            "•|| ▣ Packs found: {count}\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "enter_search_term": "⚡ <b>Please enter a search term.</b>\n•|| Example: <code>/search anime</code>",
        "did_you_mean": "Did you mean: {word}?",
        "no_results_short": "No results",
        "alpha_index_header": "▤ <b>Choose the first letter of the pack:</b>",
        "alpha_filter": "▤ <b>Packs starting with letter {letter}</b> (count: {count})",
        "alpha_unknown": "▤ <b>Packs not starting with a Latin letter</b> (count: {count})",
        "no_packs_letter": "✕ No packs starting with {letter}",
        "recent_packs_header": "✦ <b>Recently Added Packs</b>",
        "premium_packs_header": "★ <b>Premium Packs</b> ({count})",
        "regular_packs_header": "▣ <b>Regular Packs</b> ({count})",
        "no_recent_packs": "⚡ No packs added recently.",
        "no_premium_packs": "⚡ No premium packs yet.",
        "no_regular_packs": "⚡ No regular packs yet.",
        "cmd_from_user": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>Command from:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▤ <b>Command:</b> <code>{cmd}</code>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "msg_from_user": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>Message from:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "new_user_notification": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ <b>New User!</b>\n"
            "•|| ◉ <b>Name:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▦ <b>Date:</b> {date}\n"
            "•|| ▦ <b>Total users now:</b> <code>{total}</code>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "cant_ban_owner": "⚡ Cannot ban the owner.",
        "user_banned": "✓ Banned {user}.",
        "already_banned": "⚡ User is already banned.",
        "user_unbanned": "✓ Unbanned {user}.",
        "not_banned": "⚡ User is not banned.",
        "not_banned_short": "⚡ Not banned.",
        "unbanned_msg": "✓ Unbanned!",
        "banned_list_header": "⊘ <b>Banned Users</b>",
        "no_banned_users": "✓ No banned users.",
        "banned_user_item": "• {user} (<code>{uid}</code>)",
        "show_banned_btn": "⊘ Banned",
        "unban_btn": "✦ Unban",
        "user_not_found": "⚡ User not found.",
        "reply_broadcast": "⚡ <b>Reply to the message to broadcast.</b>",
        "no_users": "⚡ <b>No users to broadcast to.</b>",
        "broadcast_done": "✓ <b>Broadcast Complete!</b>\n•|| Delivered to: <code>{count}</code> users.",
        "admin_reply_sent": "✓ Reply sent to user.",
        "admin_reply_fail": "⚡ Could not send reply.",
        "forwarding_toggled": "✓ Forwarding Updated",
        "forwarding_on": "● ON",
        "forwarding_off": "○ OFF",
        "admin_reply_header": "✉ <b>Reply from admin:</b>",
        "request_sent": "✓ Your request has been sent to the owner.",
        "request_notification": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>New pack request</b>\n"
            "•|| ◉ <b>From:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▤ <b>Request:</b> {request}\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "ask_request_pack": "✉ <b>Please write the pack name or description you're looking for:</b>",
        "request_from_owner_msg": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>You can request the pack from the owner</b>\n\n"
            "•|| Write the pack name or description and it will be sent to the owner:\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "request_executed": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ <b>Your request has been fulfilled!</b>\n\n"
            "•|| We hope you enjoy the pack\n"
            "•|| Happy to help anytime\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "resend_request_header": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✉ <b>Resend Request</b>\n"
            "•|| ◉ <b>From:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▤ <b>Request:</b> {request}\n"
            "┗━━━━━≪✠≫━━━━━┛\n\n"
            "← <i>Reply to this message to deliver your reply to the user</i>"
        ),
        "no_saved_request": "⚡ No saved request",
        "report_success": "⚠ Report submitted, the pack will be reviewed.",
        "report_notification": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "⚠ <b>Pack Report</b>\n"
            "•|| ◉ <b>From:</b> <a href=\"tg://user?id={uid}\">{user}</a>\n"
            "•|| # <code>{uid}</code>\n"
            "•|| ▣ <b>Pack:</b> {pack_name}\n"
            "•|| ⛓ <b>Link:</b> <a href=\"{pack_url}\">{pack_name}</a>\n"
            "•|| ▤ <b>Reason:</b> {reason}\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "report_handled": "✓ Report handled.",
        "report_ignored": "✕ Report ignored.",
        "ask_report_reason": "▤ <b>Please write the reason for your report:</b>",
        "ask_report_reason_short": "⚡ Please write the report reason.",
        "help_text": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "▤ <b>How to Use the Bot</b>\n"
            "┗━━━━━≪✠≫━━━━━┛\n\n"
            "⌕ <b>1) Search stickers:</b>\n"
            "•|| Type here: <code>/search keyword</code>\n"
            "•|| Or in any chat: <code>@Bot keyword</code>\n"
            "•|| Or tap <b>«▤ View Packs»</b> and browse\n\n"
            "▣ <b>2) View packs:</b>\n"
            "•|| Tap <b>«▤ View Packs»</b>\n"
            "•|| Choose the first letter\n"
            "•|| Tap a pack to add it to Telegram\n\n"
            "★ <b>3) Premium packs:</b>\n"
            "•|| Marked with <b>★</b> before the name\n"
            "•|| Some require <b>Telegram Premium</b>\n\n"
            "✉ <b>4) Request a pack:</b>\n"
            "•|| Tap <b>«✉ Request Pack»</b>\n"
            "•|| Type name/description → sent to owner\n\n"
            "⚠ <b>5) Report a pack:</b>\n"
            "•|| Next to each pack there's a ⚠ button\n"
            "•|| Tap it and write the reason\n\n"
            "◐ <b>6) Change language:</b>\n"
            "•|| Tap <b>«◐ Language»</b>\n\n"
            "◉ <b>7) Our Channel:</b>\n"
            "•|| <a href=\"https://t.me/AhmShY\">@Ahmshy</a>\n\n"
            "◈ <b>Tip:</b> Use inline mode <b>«⌕ Search»</b> from any chat!\n\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "set_video_success": "✓ Tutorial video saved successfully!",
        "set_video_reply": "⚡ <b>Reply to a video</b> then type <code>/setvideo</code>",
        "del_video_success": "✓ Tutorial video deleted.",
        "del_video_not_found": "⚡ No tutorial video is set.",
        "video_manage_info": (
            "▶ <b>Tutorial Video Settings</b>\n\n"
            "•|| <b>Status:</b> {status}\n\n"
            "◆ <b>To add a video:</b>\n"
            "•|| Reply to the video with <code>/setvideo</code>\n\n"
            "◆ <b>To delete the video:</b>\n"
            "•|| Use <code>/delvideo</code>\n\n"
            "◈ You can also try the tutorial: tap «▤ How to Use» in the menu."
        ),
        "video_manage_info_deleted": (
            "▶ <b>Tutorial Video Settings</b>\n\n"
            "•|| <b>Status:</b> ✕ Not set\n\n"
            "◆ <b>To add a video:</b>\n"
            "•|| Reply to the video with <code>/setvideo</code>"
        ),
        "video_status_added": "✓ Set",
        "video_status_not_added": "✕ Not set",
        "backup_creating": "⌛ Creating backup...",
        "backup_sent": "✓ Backup sent to you!",
        "backup_failed": "✕ Backup failed",
        "scan_started": "⌕ Scanning packs...",
        "scan_complete": (
            "✓ <b>Scan complete!</b>\n\n"
            "•|| ✕ Deleted {deleted} packs.\n"
            "•|| ✎ Updated {updated} packs.\n"
            "•|| ✓ Unchanged {unchanged} packs."
        ),
        "new_packs_notification": (
            "┏━━━━━≪✠≫━━━━━┓\n"
            "✦ <b>New packs have been added!</b>\n\n"
            "•|| Press /start to explore them ⌕\n"
            "•|| ◉ <a href=\"https://t.me/AhmShY\">Our channel</a>\n"
            "┗━━━━━≪✠≫━━━━━┛"
        ),
        "inline_all_packs": "▣ All packs ({count})",
        "inline_pack_item": "{num}. {title}",
        "inline_all_packs_title": "▣ All packs matching your search:",
        "inline_pack_label": "▣ <b>Sticker Pack:</b>",
        "inline_channel_follow": "◉ Follow our channel:",
        "inline_pack_count_desc": "Packs: {count}",
        "inline_pack_link_desc": "Tap to open in the bot",
        "inline_no_results_title": "✕ No results",
        "inline_no_results_msg": "✕ No results for: <code>{query}</code>",
        "inline_no_results_desc": "No matching results",
        "inline_msg_header": "⌕ Search Results",
        "inline_msg_query_label": "▤ Query:",
        "inline_msg_count_label": "▣ Packs:",
        "inline_msg_hint": "Tap a pack name to open it in the bot",
        "inline_msg_channel_label": "◉ Our Channel:",
    }
}

LANG_KEYBOARD = InlineKeyboardMarkup([
    [
        make_btn("🇸🇦 العربية", callback_data="set_lang|ar", style="primary"),
        make_btn("🇬🇧 English", callback_data="set_lang|en", style="primary"),
    ]
])

# =========================================================
# Helper Functions
# =========================================================
EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F1E0-\U0001F1FF\U00002600-\U000026FF]+",
    flags=re.UNICODE,
)


def clean_title(text: str) -> str:
    if not text:
        return ""
    bad_words = [
        r"𝚅𝙲𝚽", r"join", r"𝐽𝑂𝐼𝑁", r"𝑱𝒐𝒊𝒏", r"𑁍", r"━Y", r"𝗧𝗐𝗂𝗍",
        r":", r"-", r"_", r"\|", r"\.", r"ᗷY 𓉮", r"ᗷY", r"𓉮"
    ]
    for word in bad_words:
        text = re.sub(word, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"@[A-Za-z0-9_]+", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = EMOJI_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_premium_pack(pack: dict) -> bool:
    return bool(pack.get("is_premium", False))


def is_emoji_pack(pack: dict) -> bool:
    return bool(pack.get("is_emoji", False))


def get_user_display(user):
    if user.first_name:
        return html.escape(user.first_name)
    return f"User {user.id}"


def get_lang(user_id):
    return DB.get("users_lang", {}).get(str(user_id), "en")


def set_lang(user_id, lang):
    if "users_lang" not in DB:
        DB["users_lang"] = {}
    DB["users_lang"][str(user_id)] = lang
    save_db(DB)


def get_text(user_id, key, **kwargs):
    lang = get_lang(user_id)
    text = TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, ""))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


async def resolve_user(bot, user_input, user_id):
    user_input = user_input.strip()
    if not user_input:
        return None
    if user_input.startswith('@'):
        username = user_input[1:]
        try:
            return await bot.get_chat(username)
        except Exception:
            return None
    else:
        try:
            uid = int(user_input)
            return await bot.get_chat(uid)
        except Exception:
            return None


def extract_links_from_entities(msg):
    links = []
    entities = list(getattr(msg, "entities", None) or []) + \
               list(getattr(msg, "caption_entities", None) or [])
    text = msg.text or msg.caption or ""
    for ent in entities:
        if ent.type == "text_link" and getattr(ent, "url", None):
            links.append(ent.url)
        elif ent.type == "url":
            try:
                links.append(text[ent.offset:ent.offset + ent.length])
            except Exception:
                pass
    return links


def combine_text_and_entity_links(msg):
    text = msg.text or msg.caption or ""
    entity_links = extract_links_from_entities(msg)
    if entity_links:
        text += "\n" + "\n".join(entity_links)
    return text


def extract_pack_names_from_text(text: str):
    if not text:
        return []
    names = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        match = re.search(
            r"(?:https?://)?(?:t\.me|telegram\.me)/(?:addstickers|addemoji)/([A-Za-z0-9_]+)",
            line,
        )
        if match:
            names.append(match.group(1))
            continue
        match = re.match(r'^\d+\.\s*(.+)$', line)
        if match:
            raw = match.group(1).strip()
            name_match = re.match(r'^([A-Za-z0-9_]+(?:\s+[A-Za-z0-9_]+)*)', raw)
            if name_match:
                clean = name_match.group(1).strip()
                if clean:
                    names.append(clean)
            continue
        if re.match(r'^[A-Za-z0-9_]+$', line) and len(line) > 2:
            if not re.search(r'[أ-ي]', line):
                names.append(line)
    return names


async def get_sticker_set_with_retry(bot, set_name):
    candidates = [
        set_name,
        set_name.replace(" ", "_"),
        set_name.replace(" ", ""),
        set_name.replace(" ", "-"),
    ]
    candidates = list(dict.fromkeys(candidates))
    for name in candidates:
        try:
            st_set = await bot.get_sticker_set(name)
            return st_set
        except Exception:
            continue
    return None


def get_recent_packs(limit=RECENT_PACKS_LIMIT):
    items = [(k, v) for k, v in DB["packs"].items() if v.get("added_at")]
    items.sort(key=lambda x: x[1].get("added_at", ""), reverse=True)
    return items[:limit]


def find_search_suggestions(query, max_suggestions=3):
    query_words = re.findall(r"[A-Za-z0-9]+", query.lower())
    if not query_words:
        return []

    all_words = set()
    for pack in DB["packs"].values():
        for w in re.findall(r"[A-Za-z0-9]+", pack.get("title", "").lower()):
            if len(w) >= 3:
                all_words.add(w)

    if not all_words:
        return []

    word_list = list(all_words)
    suggestions, seen = [], set()

    for qw in query_words:
        if len(qw) < 3:
            continue
        for m in difflib.get_close_matches(qw, word_list, n=3, cutoff=0.65):
            if m != qw and m not in seen and qw not in m:
                seen.add(m)
                suggestions.append(m)
        for w in word_list:
            if w != qw and (qw in w or w in qw) and w not in seen:
                if abs(len(w) - len(qw)) <= 6:
                    seen.add(w)
                    suggestions.append(w)

    return suggestions[:max_suggestions]


def finalize_new_pack(key, pack_data):
    pack_data["added_at"] = datetime.now().isoformat()
    DB["packs"][key] = pack_data
    DB["stats"]["packs_since_notify"] = DB["stats"].get("packs_since_notify", 0) + 1
    save_db(DB)

    if DB["stats"].get("packs_since_notify", 0) >= PACKS_BEFORE_NOTIFY:
        DB["stats"]["packs_since_notify"] = 0
        save_db(DB)
        if APP_REF is not None:
            try:
                asyncio.create_task(schedule_new_packs_notification())
            except Exception:
                pass


async def schedule_new_packs_notification():
    await asyncio.sleep(NOTIFY_DELAY)
    users = list(DB.get("users", []))
    if not users or APP_REF is None:
        return
    for uid in users:
        try:
            txt = get_text(uid, "new_packs_notification")
            await APP_REF.bot.send_message(
                chat_id=uid, text=txt, parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception:
            pass
        await asyncio.sleep(NOTIFY_STAGGER)

# =========================================================
# Database
# =========================================================
def save_db(data):
    INDEX_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_db():
    default = {
        "packs": {},
        "settings": {"forward_messages": True, "tutorial_video_id": None},
        "users": [],
        "admins": [],
        "banned_users": [],
        "users_lang": {},
        "stats": {"total_searches": 0, "search_queries": {}, "packs_since_notify": 0},
    }
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            if "packs" not in data:
                data["packs"] = {}
            if "settings" not in data:
                data["settings"] = {"forward_messages": True, "tutorial_video_id": None}
            if "tutorial_video_id" not in data["settings"]:
                data["settings"]["tutorial_video_id"] = None
            if "users" not in data:
                data["users"] = []
            if "admins" not in data:
                data["admins"] = []
            if "banned_users" not in data:
                data["banned_users"] = []
            if "users_lang" not in data:
                data["users_lang"] = {}
            if "stats" not in data:
                data["stats"] = {"total_searches": 0, "search_queries": {}, "packs_since_notify": 0}
            data["stats"].setdefault("packs_since_notify", 0)
            return data
        except Exception:
            return default
    return default


DB = load_db()

# =========================================================
# Backup
# =========================================================
async def do_backup(bot, reason=""):
    try:
        data = json.dumps(DB, ensure_ascii=False, indent=2).encode("utf-8")
        premium_count = sum(1 for p in DB.get("packs", {}).values() if p.get("is_premium"))
        await bot.send_document(
            chat_id=OWNER_ID,
            document=InputFile(io.BytesIO(data), filename=BACKUP_FILE_NAME),
            caption=(
                f"⬇ <b>Backup / نسخة احتياطية</b>\n"
                f"•|| ▣ Packs: <code>{len(DB.get('packs', {}))}</code>\n"
                f"•|| ★ Premium: <code>{premium_count}</code>\n"
                f"•|| ◉ Users: <code>{len(DB.get('users', []))}</code>\n"
                f"•|| ▦ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"•|| ▤ Reason: {reason or 'auto'}\n\n"
                f"◆ <b>To restore:</b> Send this file to the bot in private."
            ),
            parse_mode="HTML",
        )
        return True
    except Exception as e:
        print(f"[backup] failed: {e}")
        return False


async def backup_loop(app):
    await asyncio.sleep(30)
    await do_backup(app.bot, reason="startup")
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        await do_backup(app.bot, reason="auto (every 24h)")


async def post_init(app):
    global APP_REF
    APP_REF = app
    if not DB.get("packs"):
        try:
            await app.bot.send_message(
                chat_id=OWNER_ID,
                text=(
                    "⚡ <b>قاعدة البيانات فارغة! / Database is empty!</b>\n\n"
                    f"أرسل ملف النسخة الاحتياطية (<code>{BACKUP_FILE_NAME}</code>) للاستعادة.\n"
                    f"Send the backup file (<code>{BACKUP_FILE_NAME}</code>) to restore."
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
    asyncio.create_task(backup_loop(app))


async def handle_backup_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message
    if not user or not msg or not msg.document:
        return
    if user.id != OWNER_ID:
        return
    if msg.chat.type != "private":
        return
    if not (msg.document.file_name or "").lower().endswith(".json"):
        return
    try:
        file = await msg.document.get_file()
        raw = await file.download_as_bytearray()
        new_db = json.loads(bytes(raw).decode("utf-8"))
        if "packs" not in new_db:
            await msg.reply_text("✕ الملف غير صالح / Invalid file.")
            return

        DB.clear()
        DB.update(new_db)
        DB.setdefault("packs", {})
        DB.setdefault("settings", {"forward_messages": True, "tutorial_video_id": None})
        DB["settings"].setdefault("forward_messages", True)
        DB["settings"].setdefault("tutorial_video_id", None)
        DB.setdefault("users", [])
        DB.setdefault("admins", [])
        DB.setdefault("banned_users", [])
        DB.setdefault("users_lang", {})
        DB.setdefault("stats", {"total_searches": 0, "search_queries": {}, "packs_since_notify": 0})
        DB["stats"].setdefault("packs_since_notify", 0)
        save_db(DB)

        premium_count = sum(1 for p in DB["packs"].values() if p.get("is_premium"))
        await msg.reply_text(
            f"✓ <b>تم استعادة كل الإعدادات بنجاح!</b>\n\n"
            f"•|| ▣ الحزم: <code>{len(DB['packs'])}</code>\n"
            f"•|| ★ بريميوم: <code>{premium_count}</code>\n"
            f"•|| ◉ المستخدمون: <code>{len(DB['users'])}</code>\n"
            f"•|| ◆ المشرفون: <code>{len(DB['admins'])}</code>\n"
            f"•|| ⊘ المحظورون: <code>{len(DB['banned_users'])}</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        await msg.reply_text(f"✕ خطأ / Error: <code>{html.escape(str(e))}</code>", parse_mode="HTML")


async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    ok = await do_backup(context.bot, reason="manual")
    if ok:
        await update.effective_message.reply_text("✓ Backup created / تم إنشاء نسخة احتياطية.")
    else:
        await update.effective_message.reply_text("✕ Backup failed / فشل إنشاء النسخة.")

# =========================================================
# Pack Helpers
# =========================================================
async def add_pack_from_link(context, set_name, url_type="stickers", force_premium=None):
    key = set_name.lower()
    is_emoji_from_url = (url_type == "emoji")

    if force_premium is None:
        is_premium = is_emoji_from_url
    else:
        is_premium = force_premium

    if key in DB["packs"]:
        existing = DB["packs"][key]
        changed = False
        if is_premium and not existing.get("is_premium"):
            existing["is_premium"] = True
            changed = True
        if is_emoji_from_url and not existing.get("is_emoji"):
            existing["is_emoji"] = True
            existing["url"] = f"https://t.me/addemoji/{set_name}"
            changed = True
        if changed:
            save_db(DB)
            return ("upgraded", existing.get("title", set_name), existing.get("is_emoji", False))
        return ("exists", existing.get("title", set_name), existing.get("is_emoji", False))

    try:
        st_set = await context.bot.get_sticker_set(set_name)
    except Exception:
        return ("failed", set_name, False)

    sticker_type = getattr(st_set, "sticker_type", "regular")
    actual_is_emoji = (sticker_type == "custom_emoji")

    title = clean_title(st_set.title or set_name) or set_name
    pack_url = (
        f"https://t.me/addemoji/{set_name}"
        if actual_is_emoji
        else f"https://t.me/addstickers/{set_name}"
    )

    finalize_new_pack(key, {
        "title": title,
        "url": pack_url,
        "set_name": set_name,
        "is_premium": is_premium,
        "is_emoji": actual_is_emoji,
    })
    return ("added", title, actual_is_emoji)


async def handle_owner_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user_id = update.effective_user.id
    combined_text = combine_text_and_entity_links(msg)

    matches = re.findall(
        r"(?:t\.me|telegram\.me)/(addstickers|addemoji)/([A-Za-z0-9_]+)",
        combined_text,
    )
    if not matches:
        return False

    seen = set()
    unique_matches = []
    for url_type, set_name in matches:
        k = (url_type, set_name)
        if k not in seen:
            seen.add(k)
            unique_matches.append((url_type, set_name))

    added_stickers = []
    added_emoji = []
    upgraded = []
    rename_targets = []

    for url_type, set_name in unique_matches:
        kind = "emoji" if url_type == "addemoji" else "stickers"
        status, info, is_emoji = await add_pack_from_link(context, set_name, url_type=kind)

        if status == "added":
            if is_emoji:
                added_emoji.append((info, set_name))
            else:
                added_stickers.append((info, set_name))
            rename_targets.append((info, set_name))
        elif status == "upgraded":
            upgraded.append((info, set_name))
            rename_targets.append((info, set_name))

    if not added_stickers and not added_emoji and not upgraded:
        return True

    ar = (get_lang(user_id) == "ar")
    lines = ["▤ <b>نتيجة إضافة الحزم:</b>" if ar else "▤ <b>Added packs result:</b>", ""]

    if added_stickers:
        lines.append(f"▣ <b>{'حزم ملصقات عادية' if ar else 'Regular sticker packs'} ({len(added_stickers)}):</b>")
        lines += [f"• {html.escape(t)}" for t, _ in added_stickers]
        lines.append("")

    if added_emoji:
        lines.append(f"★ <b>{'حزم إيموجي بريميوم' if ar else 'Premium emoji packs'} ({len(added_emoji)}):</b>")
        lines += [f"• {html.escape(t)}" for t, _ in added_emoji]
        lines.append("")

    if upgraded:
        lines.append(f"✦ <b>{'رُقّيت إلى بريميوم' if ar else 'Upgraded to premium'} ({len(upgraded)}):</b>")
        lines += [f"• ★ {html.escape(t)}" for t, _ in upgraded]

    keyboard = []
    for title, set_name in rename_targets:
        label = title if len(title) <= 25 else title[:25] + "..."
        prefix = "✎ إعادة تسمية" if ar else "✎ Rename"
        keyboard.append([
            make_btn(f"{prefix}: {label}",
                     callback_data=f"rename_link|{set_name}", style="primary")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await msg.reply_text("\n".join(lines).strip(), parse_mode="HTML", reply_markup=reply_markup)
    return True


async def process_pack_link_by_source(update, context, url_type, set_name, sender_is_owner,
                                     from_channel, chat_type):
    user = update.effective_user
    msg = update.effective_message
    key = set_name.lower()

    if key in DB["packs"]:
        if sender_is_owner:
            await msg.reply_text(
                get_text(OWNER_ID, "already_saved"),
                parse_mode="Markdown"
            )
        return

    try:
        st_set = await context.bot.get_sticker_set(set_name)
    except Exception:
        if sender_is_owner:
            await msg.reply_text(
                f"✕ <b>لم أجد الحزمة:</b> <code>{html.escape(set_name)}</code>",
                parse_mode="HTML"
            )
        return

    sticker_type = getattr(st_set, "sticker_type", "regular")
    actual_is_emoji = (sticker_type == "custom_emoji")
    title_source = st_set.title or set_name
    title = clean_title(title_source) or set_name
    is_premium = actual_is_emoji
    pack_url = (
        f"https://t.me/addemoji/{set_name}"
        if actual_is_emoji
        else f"https://t.me/addstickers/{set_name}"
    )

    if sender_is_owner:
        finalize_new_pack(key, {
            "title": title,
            "url": pack_url,
            "set_name": set_name,
            "is_premium": is_premium,
            "is_emoji": actual_is_emoji,
        })
        await msg.reply_text(
            get_text(OWNER_ID, "pack_added_simple", name=html.escape(title)),
            parse_mode="HTML"
        )
        return

    if from_channel:
        finalize_new_pack(key, {
            "title": title,
            "url": pack_url,
            "set_name": set_name,
            "is_premium": is_premium,
            "is_emoji": actual_is_emoji,
        })
        return

    esc_title = escape_markdown(title if title else "No valid name", version=1)
    esc_src = escape_markdown(title_source, version=1)
    try:
        esc_user = escape_markdown(user.first_name or "User", version=1)
    except Exception:
        esc_user = "User"

    approval_text = get_text(
        OWNER_ID,
        "new_pack_detected",
        user=esc_user,
        uid=user.id,
        src=esc_src,
        filtered=esc_title
    )

    keyboard = InlineKeyboardMarkup([
        [make_btn(get_text(OWNER_ID, "save_btn"),
                  callback_data=f"+|{set_name}", style="success")],
        [
            make_btn(get_text(OWNER_ID, "rename_btn"),
                     callback_data=f"r|{set_name}", style="primary"),
            make_btn(get_text(OWNER_ID, "ignore_btn"),
                     callback_data=f"-|{set_name}", style="danger"),
        ]
    ])

    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=approval_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception:
        pass

# =========================================================
# Permissions
# =========================================================
def is_admin(user_id):
    return user_id == OWNER_ID or user_id in DB.get("admins", [])


def track_user(user_id):
    if user_id not in DB["users"] and user_id != OWNER_ID:
        DB["users"].append(user_id)
        save_db(DB)
        return True
    return False


def track_search(query):
    query = query.strip().lower()
    if not query:
        return
    DB["stats"]["total_searches"] = DB["stats"].get("total_searches", 0) + 1
    DB["stats"]["search_queries"][query] = DB["stats"]["search_queries"].get(query, 0) + 1
    save_db(DB)


def get_top_search():
    queries = DB["stats"].get("search_queries", {})
    if not queries:
        return "None"
    return max(queries, key=queries.get)


def normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def encode_query(query: str) -> str:
    return quote(query, safe="")


def decode_query(query: str) -> str:
    try:
        return unquote(query)
    except Exception:
        return query


def pack_matches_query(pack_title: str, query: str) -> bool:
    return normalize_query(query) in normalize_query(pack_title)


def build_pack_button_text(idx, pack):
    title = pack.get("title", "Sticker Pack")
    star = "★ " if is_premium_pack(pack) else ""
    return f"{idx}. {star}{title}"

# =========================================================
# Keyboards
# =========================================================
def get_stats_text(user_id):
    users_count = len(DB.get("users", []))
    total_searches = DB["stats"].get("total_searches", 0)
    top_search = get_top_search()
    admins_list = DB.get("admins", [])
    banned_count = len(DB.get("banned_users", []))
    premium_count = sum(1 for p in DB["packs"].values() if p.get("is_premium"))

    return get_text(
        user_id, "stats",
        packs=len(DB['packs']),
        premium=premium_count,
        users=users_count,
        admins=len(admins_list),
        banned=banned_count,
        searches=total_searches,
        top=html.escape(top_search),
    )


def get_commands_text(user_id):
    admin_cmds = get_text(user_id, "admin_commands")
    return admin_cmds + "\n┗━━━━━≪✠≫━━━━━┛"


def get_forwarding_status_text(user_id):
    status = "on" if DB["settings"].get("forward_messages", True) else "off"
    return get_text(user_id, "forwarding_on" if status == "on" else "forwarding_off")


def get_main_keyboard(user_id):
    is_admin_user = is_admin(user_id)

    buttons = [
        [make_btn(get_text(user_id, "view_packs"), callback_data=SHOW_ALPHA, style="primary")],
        [make_btn(get_text(user_id, "easy_search_btn"), callback_data="easy_search", style="primary")],
        [make_btn(get_text(user_id, "new_packs_btn"), callback_data="show_recent|0", style="success")],
        [make_btn(get_text(user_id, "request_pack"), callback_data="request_pack", style="primary")],
        [make_btn(get_text(user_id, "help_btn"), callback_data="show_help", style="primary")],
        [
            make_btn(get_text(user_id, "owner_contact"), url="https://t.me/KKFEE", style="primary"),
            make_btn(get_text(user_id, "channel_link"), url="https://t.me/AHMSHY", style="primary"),
        ],
        [make_btn(get_text(user_id, "change_lang_btn"), callback_data="change_lang", style="primary")],
    ]

    if is_admin_user:
        buttons.insert(2, [
            make_btn(get_text(user_id, "commands"), callback_data="show_commands", style="primary"),
            make_btn(get_text(user_id, "statistics"), callback_data="show_stats", style="primary"),
        ])
        buttons.insert(3, [
            make_btn(get_text(user_id, "show_banned_btn"), callback_data=SHOW_BANNED, style="danger"),
        ])

    if user_id == OWNER_ID:
        buttons.append([
            make_btn(get_text(user_id, "backup_btn"), callback_data="do_backup", style="success"),
        ])
        video_set = "✓" if DB["settings"].get("tutorial_video_id") else "✕"
        buttons.append([
            make_btn(get_text(user_id, "video_manage_btn", status=video_set),
                     callback_data="manage_video", style="primary")
        ])
        fwd_status = get_forwarding_status_text(user_id)
        buttons.append([
            make_btn(get_text(user_id, "forwarding_btn", status=fwd_status),
                     callback_data="toggle_forward", style="primary")
        ])

    return InlineKeyboardMarkup(buttons)


def get_stats_keyboard(user_id):
    fwd_status = get_forwarding_status_text(user_id)
    return InlineKeyboardMarkup([
        [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")],
        [make_btn(get_text(user_id, "forwarding_btn", status=fwd_status),
                  callback_data="toggle_forward", style="primary")],
    ])


def get_commands_keyboard(user_id):
    fwd_status = get_forwarding_status_text(user_id)
    return InlineKeyboardMarkup([
        [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")],
        [make_btn(get_text(user_id, "forwarding_btn", status=fwd_status),
                  callback_data="toggle_forward", style="primary")],
    ])


def get_alpha_index_keyboard(user_id, initiator_id):
    buttons = [
        [
            make_btn(get_text(user_id, "premium_packs_btn"),
                     callback_data=f"list_premium|{initiator_id}|0", style="primary"),
            make_btn(get_text(user_id, "regular_packs_btn"),
                     callback_data=f"list_regular|{initiator_id}|0", style="primary"),
        ]
    ]
    letters = [chr(ord('A') + i) for i in range(26)]
    row = []
    for i, letter in enumerate(letters):
        if i % 7 == 0 and i > 0:
            buttons.append(row)
            row = []
        row.append(make_btn(letter, callback_data=f"{ALPHA_CB_PREFIX}|{initiator_id}|{letter}|0", style="primary"))
    if row:
        buttons.append(row)
    buttons.append([make_btn("#", callback_data=f"{ALPHA_CB_PREFIX}|{initiator_id}|#|0", style="primary")])
    buttons.append([make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")])
    return InlineKeyboardMarkup(buttons)


def build_search_keyboard_for_group(all_items, page, user_id, initiator_id, chat_type,
                                    encoded_query=None, letter=None, source="search",
                                    nav_prefix=None, bot_username=None, group_chat_id=None,
                                    pressed_key=None):
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_page_items = all_items[start_idx:end_idx]
    show_actions = (chat_type == "private")

    keyboard = []
    for idx, pack in enumerate(current_page_items, start=start_idx + 1):
        key = pack.get("set_name", "").lower()
        set_name_actual = pack.get("set_name", "")
        button_text = build_pack_button_text(idx, pack)
        pack_url = pack.get("url", "")

        # إذا كان هذا الزر مضغوطاً سابقاً → أخضر
        btn_style = "success" if (pressed_key and key == pressed_key) else None

        if chat_type == "private":
            open_btn = make_btn(
                button_text,
                callback_data=f"packv|{key}|{page}",
                style=btn_style,
            )
        else:
            deep_url = None
            if bot_username and set_name_actual:
                if group_chat_id is not None:
                    deep_url = make_deep_link(bot_username, set_name_actual, group_chat_id)
                else:
                    deep_url = make_deep_link(bot_username, set_name_actual, None)
            if deep_url:
                open_btn = make_btn(button_text, url=deep_url)
            else:
                open_btn = make_btn(button_text, url=pack_url)

        if show_actions:
            if is_admin(user_id):
                if source == "alpha":
                    del_cb = f"del|{page}|{key}|{letter}|{initiator_id}"
                else:
                    del_cb = f"del_search|{page}|{key}|{encoded_query}|{initiator_id}"
                keyboard.append([open_btn, make_btn("✕", callback_data=del_cb, style="danger")])
            else:
                if source == "alpha":
                    rep_cb = f"report|{key}|{page}|{letter}|{initiator_id}"
                else:
                    rep_cb = f"report_search|{key}|{page}|{encoded_query}|{initiator_id}"
                keyboard.append([open_btn, make_btn("⚠", callback_data=rep_cb, style="danger")])
        else:
            keyboard.append([open_btn])

    nav_buttons = []
    total = len(all_items)
    if nav_prefix:
        if page > 0:
            nav_buttons.append(make_btn("←", callback_data=f"{nav_prefix}|{page-1}", style="primary"))
        if end_idx < total:
            nav_buttons.append(make_btn("→", callback_data=f"{nav_prefix}|{page+1}", style="primary"))
    else:
        if source == "alpha":
            if page > 0:
                nav_buttons.append(make_btn(
                    "←",
                    callback_data=f"{ALPHA_CB_PREFIX}|{initiator_id}|{letter}|{page-1}",
                    style="primary"
                ))
            if end_idx < total:
                nav_buttons.append(make_btn(
                    "→",
                    callback_data=f"{ALPHA_CB_PREFIX}|{initiator_id}|{letter}|{page+1}",
                    style="primary"
                ))
        else:
            safe_query = encoded_query or ""
            prefix = f"{SEARCH_CB_PREFIX}|{initiator_id}|{safe_query}"
            if page > 0:
                nav_buttons.append(make_btn("←", callback_data=f"{prefix}|{page-1}", style="primary"))
            if end_idx < total:
                nav_buttons.append(make_btn("→", callback_data=f"{prefix}|{page+1}", style="primary"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    if chat_type == "private":
        keyboard.append([make_btn(get_text(user_id, "main_menu"),
                                  callback_data="btn_home", style="danger")])
    else:
        keyboard.append([make_btn(get_text(user_id, "subscribe_channel"),
                                  url=CHANNEL_URL, style="primary")])

    return InlineKeyboardMarkup(keyboard), total


async def send_pack_to_user(bot, user_id, set_name, source_chat_id=None):
    key = set_name.lower()
    pack = DB["packs"].get(key)

    if not pack:
        try:
            st_set = await bot.get_sticker_set(set_name)
            sticker_type = getattr(st_set, "sticker_type", "regular")
            actual_is_emoji = (sticker_type == "custom_emoji")
            title = clean_title(st_set.title or set_name) or set_name
            pack_url = (
                f"https://t.me/addemoji/{set_name}"
                if actual_is_emoji
                else f"https://t.me/addstickers/{set_name}"
            )
            pack = {
                "title": title,
                "url": pack_url,
                "set_name": set_name,
                "is_premium": actual_is_emoji,
                "is_emoji": actual_is_emoji,
            }
        except Exception:
            await bot.send_message(
                chat_id=user_id,
                text=get_text(user_id, "pack_not_found_for_user"),
            )
            return

    title = pack.get("title", set_name)
    url = pack.get("url", "")
    is_premium = pack.get("is_premium", False)
    set_name_actual = pack.get("set_name", set_name)

    buttons = []
    if source_chat_id:
        back_url = await get_group_url(bot, source_chat_id)
        if back_url:
            buttons.append([make_btn(
                get_text(user_id, "back_to_group_btn"),
                url=back_url, style="success"
            )])
    buttons.append([make_btn(
        get_text(user_id, "main_menu"),
        callback_data="btn_home", style="danger"
    )])
    kb = InlineKeyboardMarkup(buttons)

    if is_premium:
        text = (
            f"★ <b>{html.escape(title)}</b>\n\n"
            f"<a href=\"{url}\">{get_text(user_id, 'open_premium_pack_btn')}</a>"
        )
        try:
            await bot.send_message(
                chat_id=user_id, text=text, parse_mode="HTML",
                reply_markup=kb, disable_web_page_preview=True
            )
        except Exception:
            pass
    else:
        try:
            st_set = await bot.get_sticker_set(set_name_actual)
            if st_set.stickers:
                first_sticker = st_set.stickers[0]
                await bot.send_sticker(chat_id=user_id, sticker=first_sticker.file_id)
        except Exception:
            pass

        text = (
            f"▣ <b>{html.escape(title)}</b>\n\n"
            f"<a href=\"{url}\">{get_text(user_id, 'open_pack_btn')}</a>"
        )
        try:
            await bot.send_message(
                chat_id=user_id, text=text, parse_mode="HTML",
                reply_markup=kb, disable_web_page_preview=True
            )
        except Exception:
            pass


def build_inline_message_with_entities(user_id, query, packs, bot_username):
    header = get_text(user_id, "inline_msg_header")
    query_lbl = get_text(user_id, "inline_msg_query_label")
    count_lbl = get_text(user_id, "inline_msg_count_label")
    hint = get_text(user_id, "inline_msg_hint")
    channel_lbl = get_text(user_id, "inline_msg_channel_label")
    divider = "━━━━━━━━━━━━━━━"

    parts = []
    entities = []
    offset = 0

    def add_text(t):
        nonlocal offset
        if not t:
            return
        parts.append(t)
        offset += len(t)

    def add_bold(t):
        nonlocal offset
        if not t:
            return
        start = offset
        parts.append(t)
        entities.append(MessageEntity(type=MessageEntity.BOLD, offset=start, length=len(t)))
        offset += len(t)

    def add_code(t):
        nonlocal offset
        if not t:
            return
        start = offset
        parts.append(t)
        entities.append(MessageEntity(type=MessageEntity.CODE, offset=start, length=len(t)))
        offset += len(t)

    def add_link(t, url):
        nonlocal offset
        if not t or not url:
            return
        start = offset
        parts.append(t)
        entities.append(MessageEntity(type=MessageEntity.TEXT_LINK, offset=start, length=len(t), url=url))
        offset += len(t)

    add_text(divider + "\n")
    add_bold(header)
    add_text("\n\n")
    add_text(f"{query_lbl} ")
    add_code(query)
    add_text("\n")
    add_text(f"{count_lbl} {len(packs)}\n")
    add_text(divider + "\n\n")

    for i, pack in enumerate(packs, 1):
        title = pack.get("title", "Pack")
        set_name_actual = pack.get("set_name", "")
        star = "★ " if is_premium_pack(pack) else ""

        if set_name_actual and bot_username:
            deep = make_deep_link(bot_username, set_name_actual, None)
        else:
            deep = pack.get("url", "")

        add_text(f"{i}. {star}")
        add_link(title, deep)
        add_text("\n")

    add_text("\n")
    add_text(hint + "\n\n")
    add_text(divider + "\n")
    add_text(channel_lbl + " ")
    add_link("@Ahmshy", CHANNEL_URL)

    return "".join(parts), entities


async def _send_help_demo(bot, user_id):
    await asyncio.sleep(3)
    packs = list(DB["packs"].values())
    if not packs:
        return
    pack = random.choice(packs)
    title = pack.get("title", "")
    words = [w for w in re.findall(r"[A-Za-z0-9]+", title) if len(w) >= 3]
    query = random.choice(words) if words else title
    if not query:
        return

    demo_msg = await bot.send_message(
        chat_id=user_id,
        text=f"<code>/search {html.escape(query)}</code>",
        parse_mode="HTML",
    )
    await asyncio.sleep(1)

    q = normalize_query(query)
    all_items = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
    all_items.sort(key=lambda x: x.get("title", "").lower())
    total = len(all_items)
    if total == 0:
        await bot.send_message(
            chat_id=user_id,
            text=get_text(user_id, "no_results", query=html.escape(query)),
            parse_mode="HTML",
        )
        return

    kb, _ = build_search_keyboard_for_group(all_items, 0, user_id, user_id, "private",
                                            encoded_query=encode_query(query), source="search")
    try:
        await bot.send_message(
            chat_id=user_id,
            text=get_text(user_id, "search_results", query=html.escape(query), count=total),
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_to_message_id=demo_msg.message_id,
        )
    except Exception:
        await bot.send_message(
            chat_id=user_id,
            text=get_text(user_id, "search_results", query=html.escape(query), count=total),
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

# =========================================================
# Inline Query Handler
# =========================================================
async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in DB.get("banned_users", []):
        return

    query = normalize_query(update.inline_query.query)
    if not query:
        return

    track_user(user_id)
    track_search(query)

    bot_username = context.bot.username or "Bot"

    filtered_packs = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), query)]
    total = len(filtered_packs)

    if total == 0:
        no_results_title = get_text(user_id, "inline_no_results_title")
        no_results_text = get_text(user_id, "inline_no_results_msg", query=html.escape(query))
        results = [
            InlineQueryResultArticle(
                id="no_results",
                title=no_results_title,
                input_message_content=InputTextMessageContent(
                    no_results_text, parse_mode="HTML", disable_web_page_preview=True
                ),
                description=get_text(user_id, "inline_no_results_desc"),
            )
        ]
        await update.inline_query.answer(results, cache_time=5)
        return

    filtered_packs.sort(key=lambda x: x.get("title", "").lower())

    results = []

    full_text, full_entities = build_inline_message_with_entities(
        user_id, query, filtered_packs, bot_username
    )
    all_packs_title = get_text(user_id, "inline_all_packs", count=total)
    results.append(
        InlineQueryResultArticle(
            id="all",
            title=all_packs_title,
            input_message_content=InputTextMessageContent(
                message_text=full_text,
                entities=full_entities,
                disable_web_page_preview=True,
            ),
            description=get_text(user_id, "inline_pack_count_desc", count=total),
        )
    )

    for i, pack in enumerate(filtered_packs[:50], 1):
        title = pack.get("title", "Sticker Pack")
        set_name_actual = pack.get("set_name", "")
        star = "★ " if is_premium_pack(pack) else ""
        pack_title = get_text(user_id, "inline_pack_item", num=i, title=f"{star}{title}")

        if set_name_actual:
            deep = make_deep_link(bot_username, set_name_actual, None)
        else:
            deep = pack.get("url", "")

        label = get_text(user_id, "inline_pack_label")
        channel_lbl = get_text(user_id, "inline_channel_follow")
        open_hint = get_text(user_id, "inline_msg_hint")

        parts = []
        entities = []
        off = 0

        def _add(t):
            nonlocal off
            if not t:
                return
            parts.append(t)
            off += len(t)

        def _add_bold(t):
            nonlocal off
            if not t:
                return
            start = off
            parts.append(t)
            entities.append(MessageEntity(type=MessageEntity.BOLD, offset=start, length=len(t)))
            off += len(t)

        def _add_link(t, url):
            nonlocal off
            if not t or not url:
                return
            start = off
            parts.append(t)
            entities.append(MessageEntity(type=MessageEntity.TEXT_LINK, offset=start, length=len(t), url=url))
            off += len(t)

        _add("━━━━━━━━━━━━━━━\n")
        _add_bold(label)
        _add("\n\n")
        _add(f"{star}")
        _add_link(title, deep)
        _add("\n\n" + open_hint + "\n")
        _add("━━━━━━━━━━━━━━━\n")
        _add(channel_lbl + " ")
        _add_link("@Ahmshy", CHANNEL_URL)

        results.append(
            InlineQueryResultArticle(
                id=str(i),
                title=pack_title,
                input_message_content=InputTextMessageContent(
                    message_text="".join(parts),
                    entities=entities,
                    disable_web_page_preview=True,
                ),
                description=get_text(user_id, "inline_pack_link_desc"),
            )
        )

    await update.inline_query.answer(results, cache_time=5)

# =========================================================
# Main Message Handler
# =========================================================
async def handle_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message
    if not user or not msg:
        return

    user_id = user.id
    is_owner = (user_id == OWNER_ID)
    is_admin_user = is_admin(user_id)
    text = (msg.text or "").strip()
    chat_type = msg.chat.type

    if user_id in DB.get("banned_users", []) and user_id != OWNER_ID:
        return

    forwarded_map = context.bot_data.get("forwarded_map", {})
    if msg.reply_to_message and msg.reply_to_message.message_id in forwarded_map:
        return

    if (context.user_data.get("awaiting_request") or
            context.user_data.get("pending_report") or
            context.user_data.get("awaiting_easy_search")):
        return

    is_new = track_user(user_id)
    if is_new:
        try:
            user_display = get_user_display(user)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_users = len(DB.get("users", []))
            notif_text = get_text(
                OWNER_ID, "new_user_notification",
                user=user_display, uid=user_id, date=now, total=total_users,
            )
            await context.bot.send_message(chat_id=OWNER_ID, text=notif_text, parse_mode="HTML")
        except Exception:
            pass

    if is_owner:
        pending_set_name = context.user_data.get("awaiting_pack_name")
        if pending_set_name and text and not text.startswith("/"):
            key = pending_set_name.lower()
            existing = DB["packs"].get(key, {})
            pack_url = existing.get("url", f"https://t.me/addstickers/{pending_set_name}")
            new_title = clean_title(text) or text

            if key not in DB["packs"]:
                finalize_new_pack(key, {
                    "title": new_title,
                    "url": pack_url,
                    "set_name": pending_set_name,
                    "is_premium": existing.get("is_premium", False),
                    "is_emoji": existing.get("is_emoji", False),
                })
            else:
                DB["packs"][key]["title"] = new_title
                save_db(DB)

            header = "✓ <b>تم تحديث الاسم:</b>" if get_lang(user_id) == "ar" else "✓ <b>Name updated:</b>"
            await msg.reply_text(
                f"{header}\n•|| ▣ <code>{html.escape(new_title)}</code>",
                parse_mode="HTML"
            )
            context.user_data["awaiting_pack_name"] = None
            return

    from_channel = is_channel_message(msg)
    combined_check = combine_text_and_entity_links(msg)

    if ("addstickers" in combined_check) or ("addemoji" in combined_check):
        matches = re.findall(
            r"(?:t\.me|telegram\.me)/(addstickers|addemoji)/([A-Za-z0-9_]+)",
            combined_check,
        )
        seen = set()
        uniq = []
        for ut, sn in matches:
            if (ut, sn) not in seen:
                seen.add((ut, sn))
                uniq.append((ut, sn))

        if uniq:
            hidden = has_hidden_pack_link(msg)

            if is_owner:
                added_stickers = []
                added_emoji = []
                upgraded = []
                rename_targets = []

                for ut, sn in uniq:
                    kind = "emoji" if ut == "addemoji" else "stickers"
                    status, info, is_e = await add_pack_from_link(context, sn, url_type=kind)
                    if status == "added":
                        if is_e:
                            added_emoji.append((info, sn))
                        else:
                            added_stickers.append((info, sn))
                        rename_targets.append((info, sn))
                    elif status == "upgraded":
                        upgraded.append((info, sn))
                        rename_targets.append((info, sn))

                if added_stickers or added_emoji or upgraded:
                    ar = (get_lang(user_id) == "ar")
                    lines = ["▤ <b>نتيجة إضافة الحزم:</b>" if ar else "▤ <b>Added packs result:</b>", ""]
                    if added_stickers:
                        lines.append(f"▣ <b>{'حزم ملصقات عادية' if ar else 'Regular sticker packs'} ({len(added_stickers)}):</b>")
                        lines += [f"• {html.escape(t)}" for t, _ in added_stickers]
                        lines.append("")
                    if added_emoji:
                        lines.append(f"★ <b>{'حزم إيموجي بريميوم' if ar else 'Premium emoji packs'} ({len(added_emoji)}):</b>")
                        lines += [f"• {html.escape(t)}" for t, _ in added_emoji]
                        lines.append("")
                    if upgraded:
                        lines.append(f"✦ <b>{'رُقّيت إلى بريميوم' if ar else 'Upgraded to premium'} ({len(upgraded)}):</b>")
                        lines += [f"• ★ {html.escape(t)}" for t, _ in upgraded]

                    keyboard = []
                    for title, sn in rename_targets:
                        label = title if len(title) <= 25 else title[:25] + "..."
                        prefix = "✎ إعادة تسمية" if ar else "✎ Rename"
                        keyboard.append([
                            make_btn(f"{prefix}: {label}",
                                     callback_data=f"rename_link|{sn}", style="primary")
                        ])
                    rm = InlineKeyboardMarkup(keyboard) if keyboard else None
                    await msg.reply_text("\n".join(lines).strip(), parse_mode="HTML", reply_markup=rm)
                return

            elif from_channel and hidden:
                for ut, sn in uniq:
                    await process_pack_link_by_source(
                        update, context, ut, sn,
                        sender_is_owner=False,
                        from_channel=True,
                        chat_type=chat_type,
                    )
                return

            else:
                for ut, sn in uniq:
                    await process_pack_link_by_source(
                        update, context, ut, sn,
                        sender_is_owner=False,
                        from_channel=False,
                        chat_type=chat_type,
                    )
                return

    if msg.sticker and msg.sticker.set_name:
        set_name = msg.sticker.set_name
        key = set_name.lower()

        if key not in DB["packs"]:
            try:
                st_set = await context.bot.get_sticker_set(set_name)
                title_source = st_set.title or set_name

                if MY_CHANNEL_ID.lower() in (st_set.title or "").lower() or MY_CHANNEL_ID.lower() in set_name.lower():
                    title = clean_title(title_source)
                    sticker_type = getattr(st_set, "sticker_type", "regular")
                    actual_is_emoji = (sticker_type == "custom_emoji")
                    pack_url = (
                        f"https://t.me/addemoji/{set_name}"
                        if actual_is_emoji
                        else f"https://t.me/addstickers/{set_name}"
                    )

                    if is_owner:
                        if not title:
                            context.user_data["awaiting_pack_name"] = set_name
                            await msg.reply_text(get_text(user_id, "enter_name"), parse_mode="HTML")
                            return
                        finalize_new_pack(key, {
                            "title": title,
                            "url": pack_url,
                            "set_name": set_name,
                            "is_premium": actual_is_emoji,
                            "is_emoji": actual_is_emoji,
                        })
                        await msg.reply_text(
                            get_text(user_id, "pack_added_simple", name=html.escape(title)),
                            parse_mode="HTML"
                        )
                        return

                    if from_channel:
                        finalize_new_pack(key, {
                            "title": title or set_name,
                            "url": pack_url,
                            "set_name": set_name,
                            "is_premium": actual_is_emoji,
                            "is_emoji": actual_is_emoji,
                        })
                        return

                    esc_title = escape_markdown(title if title else "No valid name", version=1)
                    esc_src = escape_markdown(title_source, version=1)
                    esc_user = escape_markdown(user.first_name or "User", version=1)

                    approval_text = get_text(
                        OWNER_ID, "new_pack_detected",
                        user=esc_user, uid=user.id, src=esc_src, filtered=esc_title,
                    )

                    keyboard = InlineKeyboardMarkup([
                        [make_btn(get_text(OWNER_ID, "save_btn"),
                                  callback_data=f"+|{set_name}", style="success")],
                        [
                            make_btn(get_text(OWNER_ID, "rename_btn"),
                                     callback_data=f"r|{set_name}", style="primary"),
                            make_btn(get_text(OWNER_ID, "ignore_btn"),
                                     callback_data=f"-|{set_name}", style="danger"),
                        ]
                    ])

                    await context.bot.send_sticker(chat_id=OWNER_ID, sticker=msg.sticker.file_id)
                    await context.bot.send_message(
                        chat_id=OWNER_ID, text=approval_text, reply_markup=keyboard, parse_mode="Markdown"
                    )
                    return
            except Exception:
                pass

    if text and not text.startswith('/'):
        combined = combine_text_and_entity_links(msg)
        pack_names = extract_pack_names_from_text(combined)
        if pack_names:
            for raw_name in pack_names:
                cleaned = clean_title(raw_name)
                if not cleaned:
                    continue
                st_set = await get_sticker_set_with_retry(context.bot, cleaned)
                if not st_set and raw_name != cleaned:
                    st_set = await get_sticker_set_with_retry(context.bot, raw_name)
                if not st_set:
                    continue
                set_name = st_set.name
                key = set_name.lower()
                if key in DB["packs"]:
                    continue
                if not (MY_CHANNEL_ID.lower() in (st_set.title or "").lower()
                        or MY_CHANNEL_ID.lower() in set_name.lower()):
                    continue

                title = clean_title(st_set.title or set_name) or set_name
                sticker_type = getattr(st_set, "sticker_type", "regular")
                actual_is_emoji = (sticker_type == "custom_emoji")
                pack_url = (
                    f"https://t.me/addemoji/{set_name}"
                    if actual_is_emoji
                    else f"https://t.me/addstickers/{set_name}"
                )

                if is_owner:
                    finalize_new_pack(key, {
                        "title": title,
                        "url": pack_url,
                        "set_name": set_name,
                        "is_premium": actual_is_emoji,
                        "is_emoji": actual_is_emoji,
                    })
                    continue

                if from_channel:
                    finalize_new_pack(key, {
                        "title": title,
                        "url": pack_url,
                        "set_name": set_name,
                        "is_premium": actual_is_emoji,
                        "is_emoji": actual_is_emoji,
                    })
                    continue

                esc_title = escape_markdown(title, version=1)
                esc_src = escape_markdown(st_set.title or set_name, version=1)
                esc_user = escape_markdown(user.first_name or "User", version=1)

                approval_text = get_text(
                    OWNER_ID, "new_pack_detected",
                    user=esc_user, uid=user.id, src=esc_src, filtered=esc_title,
                )

                keyboard = InlineKeyboardMarkup([
                    [make_btn(get_text(OWNER_ID, "save_btn"),
                              callback_data=f"+|{set_name}", style="success")],
                    [
                        make_btn(get_text(OWNER_ID, "rename_btn"),
                                 callback_data=f"r|{set_name}", style="primary"),
                        make_btn(get_text(OWNER_ID, "ignore_btn"),
                                 callback_data=f"-|{set_name}", style="danger"),
                    ]
                ])

                await context.bot.send_message(
                    chat_id=OWNER_ID, text=approval_text, reply_markup=keyboard, parse_mode="Markdown"
                )
            return

    if is_admin_user and text and not text.startswith('/'):
        target_input = None
        cmd = None

        if "حظر " in text:
            parts = text.split("حظر ", 1)
            if len(parts) > 1:
                cmd = "حظر"
                target_input = parts[1].strip()
        elif "رفع الحظر " in text:
            parts = text.split("رفع الحظر ", 1)
            if len(parts) > 1:
                cmd = "رفع الحظر"
                target_input = parts[1].strip()
        elif text.startswith("حظر"):
            target_input = text[3:].strip()
            if target_input:
                cmd = "حظر"
        elif text.startswith("رفع الحظر"):
            target_input = text[8:].strip()
            if target_input:
                cmd = "رفع الحظر"

        if cmd and target_input:
            target_chat = await resolve_user(context.bot, target_input, user_id)
            if not target_chat:
                await msg.reply_text(get_text(user_id, "user_not_found"))
                return
            target_user_id = target_chat.id
            user_display = get_user_display(target_chat)

            if cmd == "حظر":
                if target_user_id == OWNER_ID:
                    await msg.reply_text(get_text(user_id, "cant_ban_owner"))
                    return
                if target_user_id not in DB.get("banned_users", []):
                    DB["banned_users"].append(target_user_id)
                    save_db(DB)
                    await msg.reply_text(get_text(user_id, "user_banned", user=user_display))
                else:
                    await msg.reply_text(get_text(user_id, "already_banned"))
                return
            elif cmd == "رفع الحظر":
                if target_user_id in DB.get("banned_users", []):
                    DB["banned_users"].remove(target_user_id)
                    save_db(DB)
                    await msg.reply_text(get_text(user_id, "user_unbanned", user=user_display))
                else:
                    await msg.reply_text(get_text(user_id, "not_banned"))
                return

    if not is_owner and chat_type == "private":
        if text and text.startswith('/'):
            try:
                user_display = get_user_display(user)
                info_text = get_text(
                    OWNER_ID, "cmd_from_user",
                    user=user_display, uid=user.id, cmd=html.escape(text),
                )
                await context.bot.send_message(chat_id=OWNER_ID, text=info_text, parse_mode="HTML")
                await msg.forward(chat_id=OWNER_ID)
            except Exception:
                pass
        else:
            await msg.reply_text(
                get_text(user_id, "unknown_cmd", bot=context.bot.username or "Bot"),
                parse_mode="HTML"
            )
            if DB["settings"].get("forward_messages", True):
                try:
                    user_display = get_user_display(user)
                    info_text = get_text(
                        OWNER_ID, "msg_from_user",
                        user=user_display, uid=user.id,
                    )
                    info_msg = await context.bot.send_message(
                        chat_id=OWNER_ID, text=info_text, parse_mode="HTML"
                    )
                    forwarded_msg = await msg.forward(chat_id=OWNER_ID)

                    if "forwarded_map" not in context.bot_data:
                        context.bot_data["forwarded_map"] = {}
                    context.bot_data["forwarded_map"][forwarded_msg.message_id] = user.id
                    context.bot_data["forwarded_map"][info_msg.message_id] = user.id
                except Exception:
                    pass

# =========================================================
# Callback Handler
# =========================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = query.data or ""
    user_id = query.from_user.id
    chat_type = query.message.chat.type

    if user_id in DB.get("banned_users", []) and user_id != OWNER_ID:
        await query.answer(get_text(user_id, "banned"), show_alert=True)
        return

    if data.startswith("dosearch|"):
        await query.answer()
        new_q = decode_query(data.split("|", 1)[1])
        track_search(new_q)
        q = normalize_query(new_q)
        all_items = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        all_items.sort(key=lambda x: x.get("title", "").lower())
        total = len(all_items)
        if total == 0:
            await query.answer(get_text(user_id, "no_results_short"), show_alert=True)
            return
        kb, _ = build_search_keyboard_for_group(
            all_items, 0, user_id, user_id, chat_type,
            encoded_query=encode_query(new_q), source="search",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None,
        )
        await query.edit_message_text(
            get_text(user_id, "search_results", query=html.escape(new_q), count=total),
            reply_markup=kb, parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    # === زر فتح الحزمة في الخاص ===
    if data.startswith("packv|"):
        parts = data.split("|")
        if len(parts) < 3:
            await query.answer()
            return
        key = parts[1]
        try:
            page_pressed = int(parts[2])
        except Exception:
            page_pressed = 0

        pack = DB["packs"].get(key)
        if not pack:
            await query.answer(get_text(user_id, "pack_not_found_short"), show_alert=True)
            return

        url = pack.get("url", "")

        # 1) فتح الرابط
        opened = False
        if len(url) <= 250:
            try:
                await query.answer(url=url)
                opened = True
            except Exception:
                pass
        if not opened:
            await query.answer()

        # 2) تغيير لون الزر للأخضر (بدون تغيير النص)
        try:
            current_kb = query.message.reply_markup
            if current_kb:
                new_rows = []
                for row in current_kb.inline_keyboard:
                    new_row = []
                    for btn in row:
                        if btn.callback_data == data:
                            new_row.append(make_btn(
                                btn.text,
                                callback_data=btn.callback_data,
                                style="success",
                            ))
                        else:
                            new_row.append(btn)
                    new_rows.append(new_row)
                await query.edit_message_reply_markup(
                    reply_markup=InlineKeyboardMarkup(new_rows)
                )
        except Exception:
            pass
        return

    if data.startswith("show_recent|"):
        await query.answer()
        page = int(data.split("|")[1])
        items = get_recent_packs(RECENT_PACKS_LIMIT)
        if not items:
            await query.edit_message_text(
                get_text(user_id, "no_recent_packs"),
                reply_markup=InlineKeyboardMarkup([[
                    make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")
                ]]),
                parse_mode="HTML"
            )
            return
        all_items = [v for _, v in items]
        kb, total = build_search_keyboard_for_group(
            all_items, page, user_id, user_id, chat_type,
            source="search", nav_prefix="show_recent",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None,
        )
        await query.edit_message_text(
            get_text(user_id, "recent_packs_header"),
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if data.startswith("list_premium|"):
        parts = data.split("|")
        initiator_id = int(parts[1])
        page = int(parts[2])
        if initiator_id != user_id:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        await query.answer()
        all_items = [v for v in DB["packs"].values() if is_premium_pack(v)]
        all_items.sort(key=lambda x: x.get("title", "").lower())
        if not all_items:
            await query.edit_message_text(
                get_text(user_id, "no_premium_packs"),
                reply_markup=InlineKeyboardMarkup([[
                    make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")
                ]]),
                parse_mode="HTML"
            )
            return
        kb, total = build_search_keyboard_for_group(
            all_items, page, user_id, initiator_id, chat_type,
            source="search", nav_prefix="list_premium",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None,
        )
        nav_fixed = []
        for row in kb.inline_keyboard:
            new_row = []
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("list_premium|"):
                    page_part = btn.callback_data.split("|")[-1]
                    new_row.append(make_btn(
                        btn.text,
                        callback_data=f"list_premium|{initiator_id}|{page_part}",
                        style="primary",
                    ))
                else:
                    new_row.append(btn)
            nav_fixed.append(new_row)
        await query.edit_message_text(
            get_text(user_id, "premium_packs_header", count=total),
            reply_markup=InlineKeyboardMarkup(nav_fixed),
            parse_mode="HTML", disable_web_page_preview=True,
        )
        return

    if data.startswith("list_regular|"):
        parts = data.split("|")
        initiator_id = int(parts[1])
        page = int(parts[2])
        if initiator_id != user_id:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        await query.answer()
        all_items = [v for v in DB["packs"].values() if not is_premium_pack(v)]
        all_items.sort(key=lambda x: x.get("title", "").lower())
        if not all_items:
            await query.edit_message_text(
                get_text(user_id, "no_regular_packs"),
                reply_markup=InlineKeyboardMarkup([[
                    make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")
                ]]),
                parse_mode="HTML"
            )
            return
        kb, total = build_search_keyboard_for_group(
            all_items, page, user_id, initiator_id, chat_type,
            source="search", nav_prefix="list_regular",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None,
        )
        nav_fixed = []
        for row in kb.inline_keyboard:
            new_row = []
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("list_regular|"):
                    page_part = btn.callback_data.split("|")[-1]
                    new_row.append(make_btn(
                        btn.text,
                        callback_data=f"list_regular|{initiator_id}|{page_part}",
                        style="primary",
                    ))
                else:
                    new_row.append(btn)
            nav_fixed.append(new_row)
        await query.edit_message_text(
            get_text(user_id, "regular_packs_header", count=total),
            reply_markup=InlineKeyboardMarkup(nav_fixed),
            parse_mode="HTML", disable_web_page_preview=True,
        )
        return

    if data.startswith("resend_req|"):
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        await query.answer()
        target_uid = int(data.split("|")[1])
        req = context.bot_data.get("requests", {}).get(str(target_uid))
        if not req:
            await query.answer(get_text(OWNER_ID, "no_saved_request"), show_alert=True)
            return
        new_msg = await context.bot.send_message(
            chat_id=OWNER_ID,
            text=get_text(
                OWNER_ID, "resend_request_header",
                uid=target_uid, user=req["user_display"], request=html.escape(req["request"]),
            ),
            parse_mode="HTML",
        )
        context.bot_data.setdefault("forwarded_map", {})[new_msg.message_id] = target_uid
        return

    if data == "show_help":
        if chat_type != "private":
            await query.answer(get_text(user_id, "only_private"), show_alert=True)
            return
        await query.answer()
        video_id = DB["settings"].get("tutorial_video_id")

        try:
            await query.message.delete()
        except Exception:
            pass

        if video_id:
            try:
                await context.bot.send_video(
                    chat_id=user_id, video=video_id, caption="▶", parse_mode="HTML"
                )
            except Exception:
                pass

        await context.bot.send_message(
            chat_id=user_id,
            text=get_text(user_id, "help_text"),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]
            ])
        )

        asyncio.create_task(_send_help_demo(context.bot, user_id))
        return

    if data == "easy_search":
        if chat_type != "private":
            await query.answer(get_text(user_id, "only_private"), show_alert=True)
            return
        await query.answer()
        context.user_data["awaiting_easy_search"] = True
        await query.edit_message_text(
            get_text(user_id, "easy_search_prompt"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]
            ])
        )
        return

    if data == "manage_video":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        await query.answer()
        video_id = DB["settings"].get("tutorial_video_id")
        status = get_text(OWNER_ID, "video_status_added" if video_id else "video_status_not_added")
        info = get_text(OWNER_ID, "video_manage_info", status=status)

        keyboard = []
        if video_id:
            keyboard.append([make_btn(get_text(OWNER_ID, "video_delete_btn"),
                                      callback_data="del_tutorial_video", style="danger")])
        keyboard.append([make_btn(get_text(OWNER_ID, "main_menu"),
                                  callback_data="btn_home", style="danger")])

        await query.edit_message_text(info, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data == "del_tutorial_video":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        DB["settings"]["tutorial_video_id"] = None
        save_db(DB)
        await query.answer(get_text(OWNER_ID, "del_video_success"), show_alert=True)
        await query.edit_message_text(
            get_text(OWNER_ID, "video_manage_info_deleted"),
            reply_markup=InlineKeyboardMarkup([
                [make_btn(get_text(OWNER_ID, "main_menu"), callback_data="btn_home", style="danger")]
            ]),
            parse_mode="HTML"
        )
        return

    if data.startswith("rename_link|"):
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        set_name = data.split("|", 1)[1]
        context.user_data["awaiting_pack_name"] = set_name
        await query.answer()
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            get_text(OWNER_ID, "enter_new_name", set_name=html.escape(set_name)),
            parse_mode="HTML"
        )
        return

    if data.startswith("set_lang|"):
        if chat_type != "private":
            await query.answer(get_text(user_id, "only_private"), show_alert=True)
            return
        lang = data.split("|")[1]
        set_lang(user_id, lang)
        await query.answer(get_text(user_id, "lang_set"), show_alert=True)

        if context.user_data.get("reqpack_intent"):
            context.user_data["reqpack_intent"] = False
            context.user_data["awaiting_request"] = True
            await query.edit_message_text(
                get_text(user_id, "request_from_owner_msg"),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [make_btn(get_text(user_id, "main_menu"),
                              callback_data="btn_home", style="danger")]
                ])
            )
            return

        pending_deep = context.user_data.pop("pending_deep_pack", None)
        if pending_deep:
            await query.edit_message_text(
                get_text(user_id, "welcome",
                         user=html.escape(query.from_user.first_name),
                         bot=context.bot.username or "Bot"),
                reply_markup=get_main_keyboard(user_id),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            await send_pack_to_user(
                context.bot, user_id,
                pending_deep["set_name"], pending_deep.get("chat_id")
            )
            return

        await query.edit_message_text(
            get_text(user_id, "welcome",
                     user=html.escape(query.from_user.first_name),
                     bot=context.bot.username or "Bot"),
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if data == "change_lang":
        if chat_type != "private":
            await query.answer(get_text(user_id, "only_private"), show_alert=True)
            return
        await query.answer()
        await query.edit_message_text(
            get_text(user_id, "change_lang"),
            reply_markup=LANG_KEYBOARD,
            parse_mode="HTML"
        )
        return

    if data == "do_backup":
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        await query.answer(get_text(OWNER_ID, "backup_creating"), show_alert=False)
        ok = await do_backup(context.bot, reason="manual")
        if ok:
            await query.answer(get_text(OWNER_ID, "backup_sent"), show_alert=True)
        else:
            await query.answer(get_text(OWNER_ID, "backup_failed"), show_alert=True)
        return

    if data == "request_pack":
        await query.answer()
        context.user_data["awaiting_request"] = True
        await query.edit_message_text(
            get_text(user_id, "ask_request_pack"),
            parse_mode="HTML"
        )
        return

    if data.startswith("report|"):
        await query.answer()
        parts = data.split("|")
        if len(parts) < 4:
            return
        set_name_key = parts[1]
        page = int(parts[2])
        letter = parts[3]
        initiator_id = int(parts[4]) if len(parts) > 4 else user_id
        if initiator_id != user_id:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        pack_data = DB["packs"].get(set_name_key)
        if not pack_data:
            await query.edit_message_text(get_text(user_id, "pack_not_found_short"))
            return

        context.user_data["pending_report"] = {
            "set_name_key": set_name_key,
            "page": page,
            "letter": letter,
            "initiator_id": initiator_id,
            "pack_title": pack_data.get("title", "Unnamed"),
            "pack_url": pack_data.get("url", ""),
        }
        await query.edit_message_text(get_text(user_id, "ask_report_reason"), parse_mode="HTML")
        return

    if data.startswith("del_report|"):
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        parts = data.split("|")
        if len(parts) < 3:
            return
        set_name_key = parts[1]
        if set_name_key in DB["packs"]:
            del DB["packs"][set_name_key]
            save_db(DB)
            await query.edit_message_text(
                get_text(OWNER_ID, "report_handled") + "\n" +
                get_text(OWNER_ID, "deleted", name=html.escape(set_name_key)),
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(get_text(OWNER_ID, "pack_not_found_short"))
        return

    if data.startswith("ignore_report|"):
        if user_id != OWNER_ID:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        await query.edit_message_text(get_text(OWNER_ID, "report_ignored"), parse_mode="HTML")
        return

    if data == "show_commands":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        await query.answer()
        await query.edit_message_text(
            get_commands_text(user_id),
            reply_markup=get_commands_keyboard(user_id),
            parse_mode="HTML"
        )
        return

    if data == "show_stats":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        await query.answer()
        await query.edit_message_text(
            get_stats_text(user_id),
            reply_markup=get_stats_keyboard(user_id),
            parse_mode="HTML"
        )
        return

    if data == SHOW_BANNED:
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        await query.answer()
        banned_list = DB.get("banned_users", [])
        if not banned_list:
            await query.edit_message_text(
                get_text(user_id, "no_banned_users"),
                reply_markup=InlineKeyboardMarkup([
                    [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]
                ]),
                parse_mode="HTML"
            )
            return

        text = get_text(user_id, "banned_list_header") + "\n\n"
        keyboard = []
        for uid in banned_list:
            try:
                chat = await context.bot.get_chat(uid)
                user_name = get_user_display(chat)
            except Exception:
                user_name = f"Unknown ({uid})"
            text += get_text(user_id, "banned_user_item", user=user_name, uid=uid) + "\n"
            keyboard.append([
                make_btn(get_text(user_id, "unban_btn"),
                         callback_data=f"{UNBAN_CB}|{uid}", style="success")
            ])
        keyboard.append([make_btn(get_text(user_id, "main_menu"),
                                  callback_data="btn_home", style="danger")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data.startswith(f"{UNBAN_CB}|"):
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        target_user_id = int(data.split("|")[1])
        if target_user_id in DB.get("banned_users", []):
            DB["banned_users"].remove(target_user_id)
            save_db(DB)
            await query.answer(get_text(user_id, "unbanned_msg"), show_alert=True)

            banned_list = DB.get("banned_users", [])
            if not banned_list:
                await query.edit_message_text(
                    get_text(user_id, "no_banned_users"),
                    reply_markup=InlineKeyboardMarkup([
                        [make_btn(get_text(user_id, "main_menu"), callback_data="btn_home", style="danger")]
                    ]),
                    parse_mode="HTML"
                )
                return

            text = get_text(user_id, "banned_list_header") + "\n\n"
            keyboard = []
            for uid in banned_list:
                try:
                    chat = await context.bot.get_chat(uid)
                    user_name = get_user_display(chat)
                except Exception:
                    user_name = f"Unknown ({uid})"
                text += get_text(user_id, "banned_user_item", user=user_name, uid=uid) + "\n"
                keyboard.append([
                    make_btn(get_text(user_id, "unban_btn"),
                             callback_data=f"{UNBAN_CB}|{uid}", style="success")
                ])
            keyboard.append([make_btn(get_text(user_id, "main_menu"),
                                      callback_data="btn_home", style="danger")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await query.answer(get_text(user_id, "not_banned_short"), show_alert=True)
        return

    if data.startswith("+|"):
        await query.answer()
        set_name = data.split("|", 1)[1]
        key = set_name.lower()
        if key in DB["packs"]:
            await query.edit_message_text(get_text(OWNER_ID, "already_saved"), parse_mode="Markdown")
            return

        try:
            st_set = await context.bot.get_sticker_set(set_name)
            title = clean_title(st_set.title or set_name)
            if not title:
                context.user_data["awaiting_pack_name"] = set_name
                await query.edit_message_text(get_text(OWNER_ID, "needs_name"), parse_mode="Markdown")
                return

            sticker_type = getattr(st_set, "sticker_type", "regular")
            actual_is_emoji = (sticker_type == "custom_emoji")
            pack_url = (
                f"https://t.me/addemoji/{set_name}"
                if actual_is_emoji
                else f"https://t.me/addstickers/{set_name}"
            )

            finalize_new_pack(key, {
                "title": title,
                "url": pack_url,
                "set_name": set_name,
                "is_premium": actual_is_emoji,
                "is_emoji": actual_is_emoji,
            })
            await query.edit_message_text(
                get_text(OWNER_ID, "saved", name=escape_markdown(title, version=1)),
                parse_mode="Markdown"
            )
        except Exception:
            await query.edit_message_text(get_text(OWNER_ID, "error"), parse_mode="Markdown")
        return

    if data.startswith("r|"):
        await query.answer()
        set_name = data.split("|", 1)[1]
        context.user_data["awaiting_pack_name"] = set_name
        await query.edit_message_text(get_text(OWNER_ID, "type_new_name"), parse_mode="Markdown")
        return

    if data.startswith("-|"):
        await query.answer()
        await query.edit_message_text(get_text(OWNER_ID, "ignored"), parse_mode="Markdown")
        return

    if data.startswith(f"{SEARCH_CB_PREFIX}|"):
        await query.answer()
        parts = data.split("|", 3)
        try:
            initiator_id = int(parts[1])
            encoded_query = parts[2]
            page = int(parts[3])
        except Exception:
            return

        if initiator_id != user_id:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return

        search_query = decode_query(encoded_query)
        q = normalize_query(search_query)
        all_items = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        all_items.sort(key=lambda x: x.get("title", "").lower())
        total = len(all_items)

        if total == 0:
            await query.edit_message_text(
                get_text(user_id, "no_results", query=html.escape(search_query)),
                parse_mode="HTML"
            )
            return

        kb, _ = build_search_keyboard_for_group(
            all_items, page, user_id, initiator_id, chat_type,
            encoded_query=encoded_query, source="search",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None,
        )
        await query.edit_message_text(
            get_text(user_id, "search_results", query=html.escape(search_query), count=total),
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if data == SHOW_ALPHA:
        await query.answer()
        kb = get_alpha_index_keyboard(user_id, user_id)
        await query.edit_message_text(
            get_text(user_id, "alpha_index_header"),
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    if data.startswith(f"{ALPHA_CB_PREFIX}|"):
        await query.answer()
        parts = data.split("|")
        if len(parts) < 4:
            return
        try:
            initiator_id = int(parts[1])
            letter = parts[2]
            page = int(parts[3])
        except Exception:
            return

        if initiator_id != user_id:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return

        if letter == "#":
            all_items = [v for v in DB["packs"].values()
                         if not re.match(r'^[a-zA-Z]', v.get("title", ""))]
        else:
            all_items = [v for v in DB["packs"].values()
                         if v.get("title", "").lower().startswith(letter.lower())]
        all_items.sort(key=lambda x: x.get("title", "").lower())
        total = len(all_items)

        if total == 0:
            await query.edit_message_text(
                get_text(user_id, "no_packs_letter", letter=letter.upper()),
                parse_mode="HTML"
            )
            return

        kb, _ = build_search_keyboard_for_group(
            all_items, page, user_id, initiator_id, chat_type,
            letter=letter, source="alpha",
            bot_username=context.bot.username,
            group_chat_id=query.message.chat.id if chat_type != "private" else None,
        )
        if letter == "#":
            header = get_text(user_id, "alpha_unknown", count=total)
        else:
            header = get_text(user_id, "alpha_filter", letter=letter.upper(), count=total)

        await query.edit_message_text(
            header,
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if data.startswith("del_search|"):
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        parts = data.split("|", 4)
        try:
            page_to_refresh = int(parts[1])
            key_to_del = parts[2]
            encoded_query = parts[3]
            initiator_id = int(parts[4]) if len(parts) > 4 else user_id
            if key_to_del in DB["packs"]:
                del DB["packs"][key_to_del]
                save_db(DB)
                await query.answer(get_text(user_id, "deleted_short"), show_alert=True)
            search_query = decode_query(encoded_query)
            q = normalize_query(search_query)
            all_items = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
            all_items.sort(key=lambda x: x.get("title", "").lower())
            total = len(all_items)
            if total == 0:
                await query.edit_message_text(
                    get_text(user_id, "no_results", query=html.escape(search_query)),
                    parse_mode="HTML"
                )
                return
            kb, _ = build_search_keyboard_for_group(
                all_items, page_to_refresh, user_id, initiator_id, chat_type,
                encoded_query=encoded_query, source="search",
                bot_username=context.bot.username,
                group_chat_id=query.message.chat.id if chat_type != "private" else None,
            )
            await query.edit_message_text(
                get_text(user_id, "search_results", query=html.escape(search_query), count=total),
                reply_markup=kb,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            await query.answer()
        return

    if data.startswith("report_search|"):
        await query.answer()
        parts = data.split("|")
        if len(parts) < 5:
            return
        set_name_key = parts[1]
        page = int(parts[2])
        encoded_query = parts[3]
        initiator_id = int(parts[4]) if len(parts) > 4 else user_id
        if initiator_id != user_id:
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        pack_data = DB["packs"].get(set_name_key)
        if not pack_data:
            await query.edit_message_text(get_text(user_id, "pack_not_found_short"))
            return

        context.user_data["pending_report"] = {
            "set_name_key": set_name_key,
            "page": page,
            "encoded_query": encoded_query,
            "initiator_id": initiator_id,
            "pack_title": pack_data.get("title", "Unnamed"),
            "pack_url": pack_data.get("url", ""),
            "from_search": True,
        }
        await query.edit_message_text(get_text(user_id, "ask_report_reason"), parse_mode="HTML")
        return

    if data.startswith("del|"):
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        parts = data.split("|", 4)
        try:
            page_to_refresh = int(parts[1])
            key_to_del = parts[2]
            letter = parts[3]
            initiator_id = int(parts[4]) if len(parts) > 4 else user_id
            if key_to_del in DB["packs"]:
                del DB["packs"][key_to_del]
                save_db(DB)
                await query.answer(get_text(user_id, "deleted_short"), show_alert=True)
            if letter:
                if letter == "#":
                    all_items = [v for v in DB["packs"].values()
                                 if not re.match(r'^[a-zA-Z]', v.get("title", ""))]
                else:
                    all_items = [v for v in DB["packs"].values()
                                 if v.get("title", "").lower().startswith(letter.lower())]
                all_items.sort(key=lambda x: x.get("title", "").lower())
                total = len(all_items)
                if total == 0:
                    await query.edit_message_text(
                        get_text(user_id, "no_packs_letter", letter=letter.upper()),
                        parse_mode="HTML"
                    )
                    return
                show_actions = (chat_type == "private")
                kb, _ = build_search_keyboard_for_group(
                    all_items, page_to_refresh, user_id, initiator_id,
                    chat_type if show_actions else "public",
                    letter=letter, source="alpha",
                    bot_username=context.bot.username,
                    group_chat_id=query.message.chat.id if chat_type != "private" else None,
                )
                if letter == "#":
                    header = get_text(user_id, "alpha_unknown", count=total)
                else:
                    header = get_text(user_id, "alpha_filter", letter=letter.upper(), count=total)
                await query.edit_message_text(header, reply_markup=kb, parse_mode="HTML",
                                              disable_web_page_preview=True)
            else:
                kb = get_alpha_index_keyboard(user_id, initiator_id)
                await query.edit_message_text(get_text(user_id, "alpha_index_header"),
                                              reply_markup=kb, parse_mode="HTML")
        except Exception:
            await query.answer()
        return

    if data == "toggle_forward":
        if not is_admin(user_id):
            await query.answer(get_text(user_id, "button_not_for_you"), show_alert=True)
            return
        current_status = DB["settings"].get("forward_messages", True)
        DB["settings"]["forward_messages"] = not current_status
        save_db(DB)
        await query.answer(get_text(user_id, "forwarding_toggled"), show_alert=True)
        await query.edit_message_text(
            get_text(user_id, "welcome",
                     user=html.escape(query.from_user.first_name),
                     bot=context.bot.username or "Bot"),
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if data == "btn_home":
        await query.answer()
        await query.edit_message_text(
            get_text(user_id, "welcome",
                     user=html.escape(query.from_user.first_name),
                     bot=context.bot.username or "Bot"),
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

# =========================================================
# Request / Report / Easy Search Text Handler
# =========================================================
async def handle_request_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message
    if not user or not msg or not msg.text:
        return
    user_id = user.id
    chat_type = msg.chat.type

    if chat_type != "private":
        return

    # === البحث السهل ===
    if context.user_data.get("awaiting_easy_search"):
        query_text = msg.text.strip()
        if not query_text:
            return
        context.user_data["awaiting_easy_search"] = False
        track_search(query_text)
        q = normalize_query(query_text)
        all_items = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        all_items.sort(key=lambda x: x.get("title", "").lower())
        total = len(all_items)

        if total == 0:
            suggestions = find_search_suggestions(query_text)
            msg_text = get_text(user_id, "no_results", query=html.escape(query_text))
            kb_rows = []
            for s in suggestions:
                kb_rows.append([make_btn(
                    get_text(user_id, "did_you_mean", word=s),
                    callback_data=f"dosearch|{encode_query(s)}",
                    style="success",
                )])
            kb_rows.append([make_btn(
                get_text(user_id, "request_pack_btn"),
                callback_data="request_pack", style="primary",
            )])
            kb_rows.append([make_btn(
                get_text(user_id, "main_menu"),
                callback_data="btn_home", style="danger",
            )])
            await msg.reply_text(msg_text, parse_mode="HTML",
                                 reply_markup=InlineKeyboardMarkup(kb_rows))
            return

        kb, _ = build_search_keyboard_for_group(
            all_items, 0, user_id, user_id, chat_type,
            encoded_query=encode_query(query_text), source="search",
        )
        await msg.reply_text(
            get_text(user_id, "search_results", query=html.escape(query_text), count=total),
            reply_markup=kb, parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    # === طلب حزمة ===
    if context.user_data.get("awaiting_request"):
        request_text = msg.text.strip()
        if not request_text:
            return
        context.user_data["awaiting_request"] = False

        user_display = get_user_display(user)
        notif = get_text(
            OWNER_ID, "request_notification",
            user=user_display, uid=user.id, request=html.escape(request_text),
        )

        kb = InlineKeyboardMarkup([[
            make_btn(get_text(OWNER_ID, "resend_request_now"),
                     callback_data=f"resend_req|{user.id}", style="primary")
        ]])

        notif_msg = await context.bot.send_message(
            chat_id=OWNER_ID, text=notif, parse_mode="HTML", reply_markup=kb
        )

        try:
            await context.bot.pin_chat_message(
                chat_id=OWNER_ID, message_id=notif_msg.message_id,
                disable_notification=True,
            )
        except Exception:
            pass

        context.bot_data.setdefault("requests", {})[str(user.id)] = {
            "user_id": user.id,
            "user_display": user_display,
            "request": request_text,
        }
        if "forwarded_map" not in context.bot_data:
            context.bot_data["forwarded_map"] = {}
        context.bot_data["forwarded_map"][notif_msg.message_id] = user.id

        await msg.reply_text(
            get_text(user_id, "request_sent"),
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    # === بلاغ ===
    if context.user_data.get("pending_report"):
        report_data = context.user_data["pending_report"]
        reason = msg.text.strip()
        if not reason:
            await msg.reply_text(get_text(user_id, "ask_report_reason_short"))
            return

        user_display = get_user_display(user)
        report_text = get_text(
            OWNER_ID, "report_notification",
            user=user_display, uid=user_id,
            pack_name=html.escape(report_data["pack_title"]),
            pack_url=report_data["pack_url"],
            reason=html.escape(reason),
        )
        keyboard = InlineKeyboardMarkup([
            [
                make_btn(get_text(OWNER_ID, "report_delete_btn"),
                         callback_data=f"del_report|{report_data['set_name_key']}|{report_data['page']}",
                         style="danger"),
                make_btn(get_text(OWNER_ID, "report_ignore_btn"),
                         callback_data=f"ignore_report|{report_data['set_name_key']}|{report_data['page']}",
                         style="primary"),
            ]
        ])
        await context.bot.send_message(
            chat_id=OWNER_ID, text=report_text, reply_markup=keyboard,
            parse_mode="HTML", disable_web_page_preview=True,
        )
        await msg.reply_text(get_text(user_id, "report_success"))

        if report_data.get("from_search"):
            await msg.reply_text(
                get_text(user_id, "welcome", user=user_display,
                         bot=context.bot.username or "Bot"),
                reply_markup=get_main_keyboard(user_id),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            kb = get_alpha_index_keyboard(user_id, report_data.get("initiator_id", user_id))
            await msg.reply_text(get_text(user_id, "alpha_index_header"),
                                 reply_markup=kb, parse_mode="HTML")

        context.user_data["pending_report"] = None
        return

# =========================================================
# Add / Del / Rename / Scan Commands
# =========================================================
async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id):
        return
    user_id = user.id

    msg = update.effective_message
    if not msg or not msg.reply_to_message or not msg.reply_to_message.sticker:
        await msg.reply_text(get_text(user_id, "reply_to_sticker_add"))
        return

    set_name = msg.reply_to_message.sticker.set_name
    if not set_name:
        await msg.reply_text(get_text(user_id, "not_from_pack"))
        return

    key = set_name.lower()
    if key in DB["packs"]:
        return

    try:
        st_set = await context.bot.get_sticker_set(set_name)
        title = clean_title(st_set.title or set_name)
        if not title:
            await msg.reply_text(get_text(user_id, "invalid_name"))
            return

        sticker_type = getattr(st_set, "sticker_type", "regular")
        actual_is_emoji = (sticker_type == "custom_emoji")
        pack_url = (
            f"https://t.me/addemoji/{set_name}"
            if actual_is_emoji
            else f"https://t.me/addstickers/{set_name}"
        )

        finalize_new_pack(key, {
            "title": title,
            "url": pack_url,
            "set_name": set_name,
            "is_premium": actual_is_emoji,
            "is_emoji": actual_is_emoji,
        })
        await msg.reply_text(
            get_text(user_id, "pack_added_simple", name=html.escape(title)),
            parse_mode="HTML"
        )
    except Exception as e:
        await msg.reply_text(
            get_text(user_id, "error_occurred", err=html.escape(str(e))),
            parse_mode="HTML"
        )


async def cmd_addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        return
    msg = update.effective_message

    args = context.args or []
    raw = " ".join(args).strip()
    if not raw:
        usage = (
            "⚡ <b>الاستخدام:</b>\n"
            "<code>/addpremium https://t.me/addstickers/XXX</code>\n"
            "<code>/addpremium https://t.me/addemoji/XXX</code>\n"
            "أو <code>/addpremium اسم_الحزمة</code>"
            if get_lang(OWNER_ID) == "ar" else
            "⚡ <b>Usage:</b>\n"
            "<code>/addpremium https://t.me/addstickers/XXX</code>\n"
            "<code>/addpremium https://t.me/addemoji/XXX</code>\n"
            "Or <code>/addpremium pack_name</code>"
        )
        await msg.reply_text(usage, parse_mode="HTML")
        return

    m = re.search(r"(?:t\.me|telegram\.me)/(addstickers|addemoji)/([A-Za-z0-9_]+)", raw)
    if m:
        url_type = "emoji" if m.group(1) == "addemoji" else "stickers"
        set_name = m.group(2)
    else:
        url_type = "stickers"
        set_name = raw.split()[0]

    status, info, is_emoji = await add_pack_from_link(
        context, set_name, url_type=url_type, force_premium=True
    )
    if status in ("added", "upgraded"):
        ar = (get_lang(OWNER_ID) == "ar")
        keyboard = InlineKeyboardMarkup([
            [make_btn(get_text(OWNER_ID, "rename_btn"),
                      callback_data=f"rename_link|{set_name}", style="primary")]
        ])
        header = "★ <b>تمت الإضافة كبريميوم!</b>" if ar else "★ <b>Added as premium!</b>"
        name_lbl = "<b>الاسم:</b>" if ar else "<b>Name:</b>"
        await msg.reply_text(
            f"{header}\n•|| ▣ {name_lbl} {html.escape(info)}",
            parse_mode="HTML", reply_markup=keyboard,
        )
    elif status == "exists":
        pass
    else:
        ar = (get_lang(OWNER_ID) == "ar")
        err = (
            f"✕ لم أجد الحزمة: <code>{html.escape(set_name)}</code>" if ar
            else f"✕ Pack not found: <code>{html.escape(set_name)}</code>"
        )
        await msg.reply_text(err, parse_mode="HTML")


async def cmd_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id):
        return
    user_id = user.id

    msg = update.effective_message
    if not msg or not msg.reply_to_message or not msg.reply_to_message.sticker:
        await msg.reply_text(get_text(user_id, "reply_to_sticker_del"))
        return

    set_name = msg.reply_to_message.sticker.set_name
    if not set_name:
        await msg.reply_text(get_text(user_id, "not_from_pack"))
        return

    key = set_name.lower()
    if key not in DB["packs"]:
        await msg.reply_text(get_text(user_id, "not_found"))
        return

    del DB["packs"][key]
    save_db(DB)
    await msg.reply_text(get_text(user_id, "deleted", name=html.escape(set_name)), parse_mode="HTML")


async def cmd_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id):
        return
    user_id = user.id

    msg = update.effective_message
    if not msg:
        return

    ar = (get_lang(user_id) == "ar")

    if not msg.reply_to_message:
        prompt = (
            "⚡ <b>يجب أن ترد على رسالة.</b>\n\n"
            "•|| رد على <b>ملصق</b> أو <b>رسالة تحتوي رابط حزمة</b>\n"
            "•|| ثم اكتب: <code>/rename الاسم الجديد</code>"
            if ar else
            "⚡ <b>You must reply to a message.</b>\n\n"
            "•|| Reply to a <b>sticker</b> or a <b>message containing a pack link</b>\n"
            "•|| Then type: <code>/rename New Name</code>"
        )
        await msg.reply_text(prompt, parse_mode="HTML")
        return

    replied = msg.reply_to_message
    set_name = None
    url_type = "stickers"

    if replied.sticker and getattr(replied.sticker, "set_name", None):
        set_name = replied.sticker.set_name
        sticker_type = getattr(replied.sticker, "type", "regular")
        url_type = "emoji" if sticker_type == "custom_emoji" else "stickers"

    if not set_name:
        combined = combine_text_and_entity_links(replied)
        if combined:
            m = re.search(
                r"(?:t\.me|telegram\.me)/(addstickers|addemoji)/([A-Za-z0-9_]+)",
                combined,
            )
            if m:
                url_type = "emoji" if m.group(1) == "addemoji" else "stickers"
                set_name = m.group(2)

    if not set_name:
        prompt = (
            "⚡ <b>لم أجد حزمة في الرسالة المُرد عليها.</b>\n\n"
            "•|| تأكد أنك ترد على <b>ملصق</b> أو <b>رسالة تحتوي رابط حزمة</b>."
            if ar else
            "⚡ <b>No pack found in the replied message.</b>\n\n"
            "•|| Make sure you're replying to a <b>sticker</b> or a <b>message with a pack link</b>."
        )
        await msg.reply_text(prompt, parse_mode="HTML")
        return

    parts = (msg.text or "").split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        usage = (
            f"⚡ <b>الاستخدام:</b>\n"
            f"<code>/rename الاسم الجديد</code>\n\n"
            f"•|| ▣ الحزمة المستهدفة: <code>{html.escape(set_name)}</code>"
            if ar else
            f"⚡ <b>Usage:</b>\n"
            f"<code>/rename New Name</code>\n\n"
            f"•|| ▣ Target pack: <code>{html.escape(set_name)}</code>"
        )
        await msg.reply_text(usage, parse_mode="HTML")
        return

    raw_new_name = parts[1].strip()
    new_name = clean_title(raw_new_name) or raw_new_name

    key = set_name.lower()
    added_now = False

    if key not in DB["packs"]:
        status, info, is_emoji = await add_pack_from_link(context, set_name, url_type=url_type)
        if status == "failed":
            err = (
                f"✕ <b>لم أجد الحزمة في تيليجرام:</b>\n"
                f"•|| <code>{html.escape(set_name)}</code>"
                if ar else
                f"✕ <b>Pack not found on Telegram:</b>\n"
                f"•|| <code>{html.escape(set_name)}</code>"
            )
            await msg.reply_text(err, parse_mode="HTML")
            return
        added_now = (status == "added")

    if key in DB["packs"]:
        DB["packs"][key]["title"] = new_name
        save_db(DB)

        icon = "◈" if DB["packs"][key].get("is_emoji") else "▣"
        star = "★ " if DB["packs"][key].get("is_premium") else ""

        if added_now:
            header = ("✓ <b>تمت الإضافة وإعادة التسمية بنجاح!</b>" if ar
                      else "✓ <b>Added and renamed successfully!</b>")
        else:
            header = ("✓ <b>تم تحديث الاسم بنجاح!</b>" if ar
                      else "✓ <b>Name updated successfully!</b>")

        name_lbl = "الاسم الجديد" if ar else "New name"
        type_lbl = "النوع" if ar else "Type"
        type_val = (("بريميوم" if ar else "Premium")
                    if DB["packs"][key].get("is_premium")
                    else ("عادي" if ar else "Regular"))
        link_lbl = "افتح الحزمة" if ar else "Open pack"

        await msg.reply_text(
            f"{header}\n\n"
            f"•|| {icon} <b>{name_lbl}:</b> <code>{html.escape(new_name)}</code>\n"
            f"•|| {star}<b>{type_lbl}:</b> {type_val}\n"
            f"•|| ⛓ <b>Link:</b> <a href=\"{DB['packs'][key]['url']}\">{link_lbl}</a>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        await msg.reply_text(get_text(user_id, "not_found"))


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return

    msg = update.effective_message
    await msg.reply_text(get_text(user_id, "scan_started"))

    deleted = 0
    updated = 0
    unchanged = 0

    packs = DB["packs"]
    keys_to_delete = []

    for key, pack in packs.items():
        original_title = pack.get("title", "")
        cleaned = clean_title(original_title)

        if cleaned != original_title:
            if cleaned.strip() == "":
                keys_to_delete.append(key)
                deleted += 1
            else:
                packs[key]["title"] = cleaned
                updated += 1
        else:
            unchanged += 1

    for key in keys_to_delete:
        del packs[key]

    save_db(DB)
    await msg.reply_text(
        get_text(user_id, "scan_complete",
                 deleted=deleted, updated=updated, unchanged=unchanged),
        parse_mode="HTML"
    )

# =========================================================
# Video Commands
# =========================================================
async def cmd_setvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        return
    msg = update.effective_message

    if not msg.reply_to_message or not msg.reply_to_message.video:
        await msg.reply_text(get_text(OWNER_ID, "set_video_reply"), parse_mode="HTML")
        return

    video_id = msg.reply_to_message.video.file_id
    DB["settings"]["tutorial_video_id"] = video_id
    save_db(DB)
    await msg.reply_text(get_text(OWNER_ID, "set_video_success"), parse_mode="HTML")


async def cmd_delvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        return
    msg = update.effective_message

    if not DB["settings"].get("tutorial_video_id"):
        await msg.reply_text(get_text(OWNER_ID, "del_video_not_found"))
        return

    DB["settings"]["tutorial_video_id"] = None
    save_db(DB)
    await msg.reply_text(get_text(OWNER_ID, "del_video_success"))

# =========================================================
# Admin Reply Handler
# =========================================================
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id):
        return
    user_id = user.id

    msg = update.effective_message
    if not msg or not msg.reply_to_message:
        return

    if msg.text and msg.text.strip().startswith("/search"):
        return

    replied_msg_id = msg.reply_to_message.message_id
    forward_data = context.bot_data.get("forwarded_map", {})
    original_user_id = forward_data.get(replied_msg_id)
    if not original_user_id:
        return

    try:
        if msg.sticker:
            try:
                await context.bot.send_sticker(
                    chat_id=original_user_id, sticker=msg.sticker.file_id
                )
            except Exception:
                pass

            kb = InlineKeyboardMarkup([
                [make_btn(get_text(original_user_id, "request_again_btn"),
                          callback_data="request_pack", style="primary")],
                [make_btn(get_text(original_user_id, "channel_btn"),
                          url=CHANNEL_URL, style="primary")],
            ])
            await context.bot.send_message(
                chat_id=original_user_id,
                text=get_text(original_user_id, "request_executed"),
                parse_mode="HTML",
                reply_markup=kb,
            )
            await msg.reply_text(get_text(user_id, "admin_reply_sent"))
            return

        if msg.text:
            await context.bot.send_message(
                chat_id=original_user_id,
                text=f"{get_text(original_user_id, 'admin_reply_header')}\n{msg.text}",
                parse_mode="HTML",
            )
        else:
            await context.bot.send_message(
                chat_id=original_user_id,
                text=get_text(original_user_id, "admin_reply_header"),
                parse_mode="HTML",
            )
            await msg.copy(chat_id=original_user_id)
        await msg.reply_text(get_text(user_id, "admin_reply_sent"))
    except Exception:
        await msg.reply_text(get_text(user_id, "admin_reply_fail"))

# =========================================================
# /start /search /broadcast
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    user_name = html.escape(update.effective_user.first_name)
    chat_type = update.effective_chat.type

    if user_id in DB.get("banned_users", []) and user_id != OWNER_ID:
        await update.message.reply_text(get_text(user_id, "banned"))
        return

    if chat_type == "private":
        if context.args:
            arg = context.args[0]
            set_name_dl, chat_id_dl = parse_deep_link(arg)
            if set_name_dl:
                if str(user_id) not in DB.get("users_lang", {}):
                    context.user_data["pending_deep_pack"] = {
                        "set_name": set_name_dl,
                        "chat_id": chat_id_dl,
                    }
                    await update.message.reply_text(
                        get_text(user_id, "change_lang"),
                        reply_markup=LANG_KEYBOARD,
                        parse_mode="HTML",
                    )
                    return
                await send_pack_to_user(context.bot, user_id, set_name_dl, chat_id_dl)
                return

            if arg == "reqpack":
                context.user_data["reqpack_intent"] = True

        is_new = track_user(user_id)
        if is_new:
            try:
                user_display = get_user_display(update.effective_user)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                total_users = len(DB.get("users", []))
                notif_text = get_text(
                    OWNER_ID, "new_user_notification",
                    user=user_display, uid=user_id, date=now, total=total_users,
                )
                await context.bot.send_message(chat_id=OWNER_ID, text=notif_text, parse_mode="HTML")
            except Exception:
                pass

        if str(user_id) not in DB.get("users_lang", {}):
            await update.message.reply_text(
                get_text(user_id, "change_lang"),
                reply_markup=LANG_KEYBOARD,
                parse_mode="HTML",
            )
            return

        if context.user_data.get("reqpack_intent"):
            context.user_data["reqpack_intent"] = False
            context.user_data["awaiting_request"] = True
            await update.message.reply_text(
                get_text(user_id, "request_from_owner_msg"),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [make_btn(get_text(user_id, "main_menu"),
                              callback_data="btn_home", style="danger")]
                ]),
            )
            return

        bot_username = context.bot.username or "Bot"
        await update.message.reply_text(
            get_text(user_id, "welcome", user=user_name, bot=bot_username),
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    track_user(user_id)
    bot_username = context.bot.username or "Bot"
    await update.message.reply_text(
        get_text(user_id, "group_welcome", bot=bot_username),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    user_id = user.id

    if user_id in DB.get("banned_users", []) and user_id != OWNER_ID:
        return

    msg = update.effective_message
    if not msg:
        return

    query = " ".join(context.args).strip()

    if (user_id == OWNER_ID
            and msg.reply_to_message
            and context.bot_data.get("forwarded_map", {}).get(msg.reply_to_message.message_id)):
        target_user_id = context.bot_data["forwarded_map"][msg.reply_to_message.message_id]
        if not query:
            await msg.reply_text(
                get_text(OWNER_ID, "search_forwarded_by_owner_empty"),
                parse_mode="HTML",
            )
            return

        track_search(query)
        q = normalize_query(query)
        all_items = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
        all_items.sort(key=lambda x: x.get("title", "").lower())
        total = len(all_items)

        if total == 0:
            no_res = get_text(target_user_id, "no_results", query=html.escape(query))
            try:
                await context.bot.send_message(chat_id=target_user_id, text=no_res, parse_mode="HTML")
            except Exception:
                pass
            await msg.reply_text(get_text(OWNER_ID, "search_forwarded_by_owner_sent"))
            return

        kb, _ = build_search_keyboard_for_group(
            all_items, 0, target_user_id, target_user_id, "private",
            encoded_query=encode_query(query), source="search",
        )
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=get_text(target_user_id, "search_results_for_user",
                              query=html.escape(query), count=total),
                reply_markup=kb,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await msg.reply_text(get_text(OWNER_ID, "search_forwarded_by_owner_sent"))
        return

    track_user(user_id)
    if not query:
        await msg.reply_text(get_text(user_id, "enter_search_term"), parse_mode="HTML")
        return

    track_search(query)
    q = normalize_query(query)
    all_items = [v for k, v in DB["packs"].items() if pack_matches_query(v.get("title", ""), q)]
    all_items.sort(key=lambda x: x.get("title", "").lower())
    total = len(all_items)

    chat_type = update.effective_chat.type
    initiator_id = user_id
    group_chat_id = msg.chat.id if chat_type != "private" else None
    bot_username = context.bot.username or "Bot"

    if total == 0:
        suggestions = find_search_suggestions(query)
        msg_text = get_text(user_id, "no_results", query=html.escape(query))
        kb_rows = []
        for s in suggestions:
            kb_rows.append([make_btn(
                get_text(user_id, "did_you_mean", word=s),
                callback_data=f"dosearch|{encode_query(s)}",
                style="success",
            )])

        if chat_type == "private":
            kb_rows.append([make_btn(
                get_text(user_id, "request_pack_btn"),
                callback_data="request_pack", style="primary",
            )])
            kb_rows.append([make_btn(
                get_text(user_id, "main_menu"),
                callback_data="btn_home", style="danger",
            )])
        else:
            if bot_username:
                kb_rows.append([make_btn(
                    get_text(user_id, "request_pack_btn"),
                    url=f"https://t.me/{bot_username}?start=reqpack",
                    style="primary",
                )])
            kb_rows.append([make_btn(
                get_text(user_id, "subscribe_channel"),
                url=CHANNEL_URL, style="primary",
            )])

        await msg.reply_text(msg_text, parse_mode="HTML",
                             reply_markup=InlineKeyboardMarkup(kb_rows))
        return

    kb, _ = build_search_keyboard_for_group(
        all_items, 0, user_id, initiator_id, chat_type,
        encoded_query=encode_query(query), source="search",
        bot_username=bot_username, group_chat_id=group_chat_id,
    )

    await msg.reply_text(
        get_text(user_id, "search_results", query=html.escape(query), count=total),
        reply_markup=kb,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return

    user_id = OWNER_ID
    msg = update.effective_message
    if not msg.reply_to_message:
        await msg.reply_text(get_text(user_id, "reply_broadcast"), parse_mode="HTML")
        return

    users = DB.get("users", [])
    if not users:
        await msg.reply_text(get_text(user_id, "no_users"), parse_mode="HTML")
        return

    success = 0
    for uid in users:
        try:
            await context.bot.copy_message(
                chat_id=uid, from_chat_id=msg.chat_id,
                message_id=msg.reply_to_message.message_id,
            )
            success += 1
        except Exception:
            pass

    await msg.reply_text(get_text(user_id, "broadcast_done", count=success), parse_mode="HTML")

# =========================================================
# Main
# =========================================================
def main():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise ValueError("Please place your bot token in TELEGRAM_TOKEN")

    request = HTTPXRequest(
        connect_timeout=180.0,
        read_timeout=180.0,
        write_timeout=180.0,
        pool_timeout=180.0,
    )

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(request)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", cmd_search))
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

    app.add_handler(
        MessageHandler(
            filters.Document.ALL & filters.User(OWNER_ID) & filters.ChatType.PRIVATE,
            handle_backup_document,
        ),
        group=-1,
    )

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(InlineQueryHandler(inline_query_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_main))
    app.add_handler(MessageHandler(filters.REPLY, handle_admin_reply), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request_text), group=3)

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=None,
        poll_interval=0.0,
        timeout=300,
        bootstrap_retries=-1,
    )


if __name__ == "__main__":
    main()
