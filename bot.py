from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

import os
TOKEN = os.environ.get("8491426723:AAECUa6FEZbRy1ZKsJ7FWGA43QO3xIw5cHE")

ATTENDANCE_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R=MjAyMzA5MBI2NTZ4&T=-8584723613578166740"
RESULT_URL = "https://narayanagroup.co.in/patient/EngAutonomousReport.aspx/MjAyMjA5MDI2MDgx"


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to NECRACK Bot!\n\nPlease enter your *Registration Number*:",
        parse_mode="Markdown"
    )


# Receive registration number
async def receive_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip()
    context.user_data["reg"] = reg

    keyboard = [
        [InlineKeyboardButton("📊 Attendance", callback_data="attendance")],
        [InlineKeyboardButton("📝 Result", callback_data="result")]
    ]

    await update.message.reply_text(
        f"✅ Registration Number saved:\n`{reg}`\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# Button handler
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "attendance":
        await query.message.reply_text(
            "📊 Opening Attendance Portal…",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "Open Attendance",
                    web_app=WebAppInfo(url=ATTENDANCE_URL)
                )]
            ])
        )

    elif query.data == "result":
        await query.message.reply_text(
            "📝 Opening Result Portal…",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "Open Result",
                    web_app=WebAppInfo(url=RESULT_URL)
                )]
            ])
        )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reg))
    app.add_handler(CallbackQueryHandler(button_click))

    print("🤖 NECRACK_Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
