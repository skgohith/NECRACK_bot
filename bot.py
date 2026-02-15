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

# --- EXTRACTION ENGINE ---

def get_sis_value(soup, label):
    """Targets specific labels and handles adjacent cell extraction."""
    target = soup.find(string=re.compile(label, re.I))
    if target:
        if ":" in target:
            return target.split(":", 1)[1].strip()
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
    
    msg = await update.message.reply_text(f"⏳ Synchronizing Profile `{reg}`...")
    soup = await fetch_portal_soup(reg)
    await msg.delete()

    if not soup:
        return await update.message.reply_text("❌ Portal Offline. Please try again later.")

    # Profile Data (Campus and Year removed as per request)
    name = get_sis_value(soup, "NAME")
    htc = get_sis_value(soup, "HTC NO")

    profile_text = (
        f"👤 *STUDENT PROFILE*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📛 *NAME:* `{name}`\n"
        f"🆔 *HTC NO:* `{htc}`\n"
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
        full_text = soup.get_text()
        match = re.search(r"Attendance\s*(\d+\.\d+)", full_text, re.I)
        val = match.group(1) if match else "N/A"
        await query.message.reply_text(f"📈 *Attendance for {reg}:* `{val}%`", parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "fee":
        fee_header = f"🆔 *ID:* `{reg}`\n\n💰 *FEE LEDGER (ALL-TIME)*\n━━━━━━━━━━━━━━━\n"
        ledger_body = ""
        
        rows = soup.find_all('tr')
        for row in rows:
            row_text = row.get_text(separator=" ").strip()
            # Match academic years like I B.Tech, II B.Tech, etc.
            if re.search(r"(I|II|III|IV|FINAL)\s*B\.TECH", row_text, re.I):
                cells = [c.get_text(strip=True) for c in row.find_all('td')]
                if len(cells) >= 4:
                    year_label = cells[0]
                    paid = cells[-2] if cells[-2] else "0"
                    bal = cells[-1] if cells[-1] else "0"
                    
                    ledger_body += f"📅 *{year_label}*\n"
                    ledger_body += f" ├ Paid: `₹{paid}`\n"
                    ledger_body += f" └ Bal: `₹{bal}`\n\n"

        if not ledger_body:
            ledger_body = "⚠️ No fee data records could be extracted."

        await query.message.reply_text(fee_header + ledger_body, parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
