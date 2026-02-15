import base64
import asyncio
import http.server
import socketserver
import threading
import re
import httpx
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
)

# --- 24/7 HEARTBEAT (Koyeb "Always Running") ---
def run_heartbeat():
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_ENGINE_ONLINE")
    with socketserver.TCPServer(("", 8080), HealthCheckHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- CONFIG ---
TOKEN = "8491426723:AAECUa6FEZbRy1ZKsJ7FWGA43QO3xIw5cHE"
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- TEXT EXTRACTION ENGINE (Attendance Page) ---

async def get_attendance_page_data(reg):
    """Scrapes data directly from the Attendance/Profile page as text."""
    url = SIS_URL.format(id=b64_encode(reg))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code != 200: return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Helper to find values based on table labels
            def find_label_value(label_text):
                tag = soup.find(string=re.compile(label_text, re.I))
                if tag:
                    # Look for the next td which usually contains the data
                    td = tag.find_parent('td') if tag.name != 'td' else tag
                    if td:
                        next_td = td.find_next_sibling('td')
                        return next_td.get_text(strip=True) if next_td else "N/A"
                return "N/A"

            return {
                "name": find_label_value("Student Name"),
                "htc": find_label_value("H.T.No"),
                "campus": find_label_value("Campus"),
                "year": find_label_value("Year"),
                "total_attendance": find_label_value("Attendance"), # Often found in the same page summary
                "soup": soup 
            }
        except Exception:
            return None

# --- BOT INTERFACE ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\n\nEnter Registration Number to see Profile & Menu:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    status = await update.message.reply_text(f"⏳ Extracting data for `{reg}` from Attendance portal...")
    data = await get_attendance_page_data(reg)
    await status.delete()

    if not data or data['name'] == "N/A":
        return await update.message.reply_text("❌ Error: Could not find data for this ID. Check if portal is up.")

    # Profile View (Text Format)
    profile_msg = (
        f"👤 *STUDENT PROFILE*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📛 *NAME:* `{data['name']}`\n"
        f"🆔 *HTC NO:* `{data['htc']}`\n"
        f"🏫 *CAMPUS:* `{data['campus']}`\n"
        f"📅 *YEAR:* `{data['year']}`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 *TOTAL ATTENDANCE:* `{data['total_attendance']}%`"
    )

    # Separate Buttons
    result_link = SIS_URL.format(id=b64_encode(reg))
    keyboard = [
        [InlineKeyboardButton("📊 Detailed Attendance", callback_data="det_att")],
        [InlineKeyboardButton("💰 Fee Details", callback_data="det_fee")],
        [InlineKeyboardButton("🔗 Open Results in Browser", url=result_link)]
    ]

    await update.message.reply_text(
        profile_msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    await query.answer()

    if query.data == "det_att":
        await context.bot.send_message(query.message.chat_id, f"📝 *Detailed Attendance table for {reg}* is being processed...")
        # Add logic to scrape and format the specific attendance table here
    
    elif query.data == "det_fee":
        await context.bot.send_message(query.message.chat_id, f"💳 *Fee Ledger for {reg}* is being processed...")

# --- RUN BOT ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("GHOST_ENGINE_TEXT_MODE_ONLINE")
    app.run_polling()
