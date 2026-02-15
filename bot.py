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

# --- 24/7 HEARTBEAT (Prevents Koyeb Sleeping) ---
def run_heartbeat():
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_ENGINE_ONLINE")
    # Koyeb routes traffic to port 8080
    with socketserver.TCPServer(("", 8080), HealthCheckHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- CONFIG ---
TOKEN = "8491426723:AAECUa6FEZbRy1ZKsJ7FWGA43QO3xIw5cHE"
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- DATA EXTRACTION ENGINE ---

async def get_portal_soup(reg):
    """Fetches the HTML source of the portal."""
    url = SIS_URL.format(id=b64_encode(reg))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
            return None
        except Exception:
            return None

def extract_field(soup, label_pattern):
    """Generic helper to find data next to a label in a table."""
    tag = soup.find(string=re.compile(label_pattern, re.I))
    if tag:
        # Move to the parent td, then to the next sibling td which has the value
        parent_td = tag.find_parent('td')
        if parent_td:
            next_td = parent_td.find_next_sibling('td')
            return next_td.get_text(strip=True) if next_td else "N/A"
    return "N/A"

# --- BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\n\nEnter Registration Number to fetch Profile:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    msg = await update.message.reply_text(f"🔍 Fetching data for `{reg}`...")
    soup = await get_portal_soup(reg)
    await msg.delete()

    if not soup:
        return await update.message.reply_text("❌ Portal Unreachable. Try again later.")

    # 📋 SCRAPE PROFILE DATA
    name = extract_field(soup, "Student Name")
    htc = extract_field(soup, "H.T.No")
    campus = extract_field(soup, "Campus")
    year = extract_field(soup, "Year")
    
    if name == "N/A":
        return await update.message.reply_text("❌ ID Not Found. Please check the registration number.")

    profile_text = (
        f"👤 *STUDENT PROFILE*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📛 *NAME:* `{name}`\n"
        f"🆔 *HTC NO:* `{htc}`\n"
        f"🏫 *CAMPUS:* `{campus}`\n"
        f"📅 *YEAR:* `{year}`\n"
    )

    # 🔘 NAVIGATION BUTTONS
    result_link = SIS_URL.format(id=b64_encode(reg))
    keyboard = [
        [InlineKeyboardButton("📊 Attendance", callback_data="show_att"),
         InlineKeyboardButton("💰 Fee Details", callback_data="show_fee")],
        [InlineKeyboardButton("🔗 Open Results in Browser", url=result_link)]
    ]

    await update.message.reply_text(
        profile_text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    await query.answer()

    if not reg:
        return await query.message.reply_text("❌ Session expired. Re-enter ID.")

    soup = await get_portal_soup(reg)
    
    if query.data == "show_att":
        att = extract_field(soup, "Attendance")
        await context.bot.send_message(
            query.message.chat_id, 
            f"📈 *Attendance for* `{reg}`: `{att}%`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "show_fee":
        # Example of targeted scraping for specific text in the fee section
        await context.bot.send_message(
            query.message.chat_id, 
            f"💰 *Fee Status for* `{reg}`: Please check the Result Link for the full ledger.",
            parse_mode=ParseMode.MARKDOWN
        )

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Drop pending updates to avoid Conflict errors on restart
    asyncio.get_event_loop().run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("GHOST_ENGINE_V16_ONLINE")
    app.run_polling()
