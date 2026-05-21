import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

TOKEN = "8518587819:AAGgCQ-JHywc0mQSsgAzAagEdQpTvFgOoI0"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في النسخة المستقرة والمطورة للبوت!\n\n"
        "🔗 أرسل لي رابط الفيديو الآن واختر الصيغة."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("❌ يرجى إرسال رابط صحيح.")
        return

    context.user_data['current_url'] = url
    keyboard = [
        [
            InlineKeyboardButton("🎬 فيديو MP4", callback_data="download_mp4"),
            InlineKeyboardButton("🎵 صوت MP3", callback_data="download_mp3")
        ]
    ]
    await update.message.reply_text("📥 اختر الصيغة المطلوبة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get('current_url')
    if not url:
        await query.edit_message_text("❌ انتهت الجلسة، أرسل الرابط مجدداً.")
        return

    choice = query.data
    status_message = await query.edit_message_text("⏳ جاري سحب الفيديو وتخطى الحماية (قد يستغرق دقيقة)...")

    # إعدادات تخطي الحظر وتحديد المتصفح الوهمي الاحترافي
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'proxy': '',  # يمكنك إضافة بروكسي هنا إذا كان سيرفرك محظوراً تماماً من يوتيوب
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        }
    }

    if choice == "download_mp4":
        ydl_opts = {
            **base_opts,
            'format': 'best[ext=mp4]/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

    try:
        # تشغيل التحميل في خيط معالجة آمن تماماً يمنع انهيار الكود
        def download():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if choice == "download_mp3":
                    filename = os.path.splitext(filename)[0] + ".mp3"
                return filename, info.get('title', 'Video'), info.get('uploader', 'Unknown')

        loop = asyncio.get_running_loop()
        filename, title, uploader = await loop.run_in_executor(None, download)

        await status_message.edit_text("🚀 جاري رفع الملف إلى تيليجرام...")

        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        caption_text = f"🎬 {title}\n📊 الحجم: {file_size_mb:.2f} MB"

        with open(filename, 'rb') as file_data:
            if choice == "download_mp4":
                if file_size_mb > 49.0:
                    await context.bot.send_document(chat_id=update.effective_chat.id, document=file_data, caption=caption_text)
                else:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=file_data, caption=caption_text, supports_streaming=True)
            else:
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=file_data, title=title, performer=uploader, caption=caption_text)

        if os.path.exists(filename):
            os.remove(filename)
        await status_message.delete()

    except Exception as e:
        # طباعة الخطأ الحقيقي مخفي في التيرمنال للمطور لمعرفته والتعامل معه
        print(f"--- DETAILED ERROR LOG --- \n{e}\n-------------------------")
        await status_message.edit_text("❌ المنصة المستضيفة للفيديو تمنع البوتات حالياً من التحميل، أو أن الرابط غير مدعوم.")

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))

    print("🚀 البوت النهائي المستقر يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
