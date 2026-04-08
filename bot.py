from flask import Flask
import threading

# كود وهمي لتشغيل سيرفر ويب بسيط لضمان عمل الخطة المجانية في Render
app = Flask(  )
@app.route( / )
def home(): return "Bot is Running!"

def run_web():
    app.run(host= 0.0.0.0 , port=int(os.environ.get( PORT , 8080)))

if __name__ ==  __main__ :
    # تشغيل سيرفر الويب في خلفية الكود
    threading.Thread(target=run_web).start()
    
    req = HTTPXRequest(connect_timeout=60.0, read_timeout=60.0)
    application = Application.builder().token(TOKEN).request(req).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("--- البوت يعمل الآن بنظام الويب المجاني ---")
    application.run_polling(drop_pending_updates=True)
