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

# --- 24/7 HEARTBEAT ---
def run_heartbeat():
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_ENGINE_ONLINE")
    try:
        with socketserver.TCPServer(("", 8080), HealthCheckHandler) as httpd:
            httpd.serve_forever()
    except:
        pass

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- CONFIG ---
TOKEN = "8491426723:AAECUa6FEZbRy1ZKsJ7FWGA43QO3xIw5cHE"
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- SMART EXTRACTION ENGINE ---

def get_clean_value(soup, label):
    """Finds the label and gets the immediate next text piece, cleaning up noise."""
    target = soup.find(string=re.compile(label, re.I))
    if target:
        # Move up to parent, then find next cell
        parent = target.find_parent(['td', 'span', 'b'])
        if parent:
            text_after = parent.next_sibling
            if text_after and isinstance(text_after, str):
                return text_after.strip(': ').strip()
            
            # If not a sibling, check the next cell
            val_td = parent.find_next('td')
            if val_td:
                return val_td.get_text(strip=True).strip(': ').strip()
    return "N/A"

async def get_portal_data(reg):
    url = SIS_URL.format(id=b64_encode(reg))
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        try:
            r = await client.get(url)
            if r.status_code == 200:
                return BeautifulSoup(r.text, 'html.parser')
            return None
        except:
            return None

# --- BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\nEnter Registration Number:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    msg = await update.message.reply_text(f"⏳ Syncing Profile `{reg}`...")
    soup = await get_portal_data(reg)
    await msg.delete()

    if not soup:
        return await update.message.reply_text("❌ Portal Offline.")

    # 📋 Profile Data (Targets labels from your Screenshot)
    name = get_clean_value(soup, "NAME")
    htc = get_clean_value(soup, "HTC NO")
    campus = get_clean_value(soup, "CAMPUS")
    year = get_clean_value(soup, "YEAR")

    profile_text = (
        f"👤 *STUDENT PROFILE*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📛 *NAME:* `{name}`\n"
        f"🆔 *HTC NO:* `{htc}`\n"
        f"🏫 *CAMPUS:* `{campus}`\n"
        f"📅 *YEAR:* `{year}`\n"
    )

    keyboard = [
        [InlineKeyboardButton("📊 Attendance", callback_data="att"),
         InlineKeyboardButton("💰 Fee Ledger", callback_data="fee")],
        [InlineKeyboardButton("🔗 Open Full Results", url=SIS_URL.format(id=b64_encode(reg)))]
    ]

    await update.message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    await query.answer()

    soup = await get_portal_data(reg)
    if not soup: return

    if query.data == "att":
        # Extract Attendance and clean the messy string
        raw_att = get_clean_value(soup, "Attendance")
        # Logic to clean "OverallAverage86.81Rank..."
        clean_att = re.search(r"(\d+\.\d+)", raw_att)
        val = clean_att.group(1) if clean_att else raw_att
        
        await context.bot.send_message(
            query.message.chat_id, 
            f"📈 *Attendance for* `{reg}`: `{val}%`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "fee":
        # Targeted Fee Check (Looking for 'Balance' label)
        balance = get_clean_value(soup, "Balance")
        await context.bot.send_message(
            query.message.chat_id, 
            f"💰 *Fee Balance for* `{reg}`: `₹{balance}`\n\n(Check browser link for full Ledger)",
            parse_mode=ParseMode.MARKDOWN
        )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    asyncio.get_event_loop().run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
