import os
import re
import asyncio
import tempfile
import threading
from flask import Flask
from PIL import Image, ImageDraw, ImageFont, ImageOps
from telegram import InputSticker, Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import StickerFormat
from telegram.request import HTTPXRequest

TOKEN = "PUT_YOUR_TOKEN_HERE"
RIGHTS_TEXT = "@AhmshY"

# --- ويب سيرفر ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is Running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- تنظيف اسم الحزمة ---
def clean_name(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9_]", "_", text)
    return text[:20]

# --- تعديل الصورة ---
def process_image(in_p, out_p):
    try:
        img = Image.open(in_p)
        img = ImageOps.exif_transpose(img).convert("RGBA")
        img.thumbnail((512, 512))

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), RIGHTS_TEXT, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        x = img.width - tw - 10
        y = img.height - th - 10

        draw.rectangle([x-3, y-3, x+tw+3, y+th+3], fill=(0,0,0,90))
        draw.text((x, y), RIGHTS_TEXT, fill=(255,255,255,255), font=font)

        out = Image.alpha_composite(img, overlay).convert("RGB")
        out.save(out_p, "WEBP", quality=90)
        return True
    except:
        return False

# --- المعالجة ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    match = re.search(r"t\.me/addstickers/([A-Za-z0-9_]+)", text)
    if not match:
        await update.message.reply_text("❌ أرسل رابط حزمة صحيح")
        return

    pack_name = match.group(1)
    msg = await update.message.reply_text("⏳ جاري المعالجة...")

    try:
        sticker_set = await context.bot.get_sticker_set(pack_name)
        bot = await context.bot.get_me()

        new_name = f"stk_{user_id}_{clean_name(pack_name)}_by_{bot.username}"

        created = False
        count = 0

        with tempfile.TemporaryDirectory() as tmp:
            in_p = os.path.join(tmp, "in.webp")
            out_p = os.path.join(tmp, "out.webp")

            for sticker in sticker_set.stickers:

                if sticker.is_animated or sticker.is_video:
                    continue

                file = await context.bot.get_file(sticker.file_id)
                await file.download_to_drive(custom_path=in_p)

                if not process_image(in_p, out_p):
                    continue

                with open(out_p, "rb") as f:
                    s = InputSticker(
                        sticker=f,
                        emoji_list=[sticker.emoji or "✨"],
                        format=StickerFormat.STATIC
                    )

                    if not created:
                        await context.bot.create_new_sticker_set(
                            user_id=user_id,
                            name=new_name,
                            title=f"حقوق {RIGHTS_TEXT}",
                            stickers=[s]
                        )
                        created = True
                    else:
                        await context.bot.add_sticker_to_set(
                            user_id=user_id,
                            name=new_name,
                            sticker=s
                        )

                count += 1

                # مهم لتخفيف الضغط
                await asyncio.sleep(0.7)

        await msg.edit_text(
            f"✅ تم الانتهاء\n"
            f"عدد الملصقات: {count}\n"
            f"https://t.me/addstickers/{new_name}"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

# --- تشغيل ---
async def main():
    req = HTTPXRequest(connect_timeout=60, read_timeout=60)
    app_bot = Application.builder().token(TOKEN).request(req).build()

    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("البوت شغال 🔥")
    await app_bot.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()

    import asyncio
    asyncio.run(main())
