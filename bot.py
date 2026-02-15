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

# --- REFINED EXTRACTION ENGINE ---

def get_sis_value(soup, label):
    """Finds exact text matches in table cells and returns the next sibling cell."""
    target = soup.find(string=lambda t: t and label in t.upper())
    if target:
        # Check if the value is in the same cell after a colon
        if ":" in target:
            return target.split(":", 1)[1].strip()
        # Otherwise, check the next cell (td)
        parent_td = target.find_parent('td')
        if parent_td:
            next_td = parent_td.find_next_sibling('td')
            if next_td:
                return next_td.get_text(strip=True)
    return "N/A"

async def fetch_portal_soup(reg):
    url = SIS_URL.format(id=b64_encode(reg))
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.get(url)
            return BeautifulSoup(r.text, 'html.parser') if r.status_code == 200 else None
        except:
            return None

# --- BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\nEnter Registration Number to login:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    msg = await update.message.reply_text(f"⏳ Syncing Profile `{reg}`...")
    soup = await fetch_portal_soup(reg)
    await msg.delete()

    if not soup:
        return await update.message.reply_text("❌ Portal Offline.")

    # Profile extraction targeting the exact structure in your screenshot
    name = get_sis_value(soup, "NAME")
    htc = get_sis_value(soup, "HTC NO")
    campus = get_sis_value(soup, "CAMPUS")
    year = get_sis_value(soup, "YEAR")

    profile_text = (
        f"👤 *STUDENT PROFILE*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📛 *NAME:* `{name}`\n"
        f"🆔 *HTC NO:* `{htc}`\n"
        f"🏢 *CAMPUS:* `{campus}`\n"
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

    soup = await fetch_portal_soup(reg)
    if not soup: return

    if query.data == "att":
        # Extract numeric attendance from the messy text string
        full_text = soup.get_text()
        match = re.search(r"Attendance\s*(\d+\.\d+)", full_text, re.I)
        val = match.group(1) if match else "N/A"
        await query.message.reply_text(f"📈 *Attendance for {reg}:* `{val}%`", parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "fee":
        # Multi-Year Fee Ledger implementation
        fee_msg = f"🆔 *ID:* `{reg}`\n\n💰 *FEE LEDGER (ALL-TIME)*\n━━━━━━━━━━━━━━━\n"
        
        # We look for rows that contain academic year markers (e.g., I B.Tech, II B.Tech)
        rows = soup.find_all('tr')
        found_data = False
        
        for row in rows:
            row_text = row.get_text(separator=" ").strip()
            # Regex to catch B.Tech year indicators
            if re.search(r"(I|II|III|IV|FINAL)\s*B\.TECH", row_text, re.I):
                cells = [c.get_text(strip=True) for c in row.find_all('td')]
                if len(cells) >= 4:
                    # Formatting based on your target image
                    year_label = cells[0]
                    paid = cells[-2] # Assuming penultimate column is Paid
                    bal = cells[-1]  # Assuming last column is Balance
                    
                    fee_msg += f"📅 *{year_label}*\n"
                    fee_msg += f" ├ Paid: `₹{paid}`\n"
                    fee_msg += f" └ Bal: `₹{bal}`\n\n"
                    found_data = True

        if not found_data:
            fee_msg += "⚠️ No detailed fee records found in current view."
            
        await query.message.reply_text(fee_msg, parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
