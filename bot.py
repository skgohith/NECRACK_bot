import base64
import asyncio
import http.server
import socketserver
import threading
import re
import httpx
import os
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
)

# --- 🛰️ 24/7 HEARTBEAT FOR KOYEB ---
def run_heartbeat():
    # Koyeb passes the port dynamically via environment variables
    port = int(os.environ.get("PORT", 8080))
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_ENGINE_ONLINE")
        def log_message(self, format, *args):
            return # Keep logs clean

    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            print(f"📡 Heartbeat Server live on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"❌ Heartbeat Failed: {e}")

# Start heartbeat in a background thread
threading.Thread(target=run_heartbeat, daemon=True).start()

# --- ⚙️ CONFIG ---
TOKEN = "8491426723:AAECUa6FEZbRy1ZKsJ7FWGA43QO3xIw5cHE"
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- 🔍 DATA EXTRACTION ENGINE ---

def get_sis_value(soup, label):
    """Finds student name and HTC number from the main table."""
    target = soup.find(string=re.compile(label, re.I))
    if target:
        parent_td = target.find_parent('td')
        if parent_td:
            next_td = parent_td.find_next_sibling('td')
            if next_td:
                return next_td.get_text(strip=True)
    return "N/A"

async def fetch_portal_soup(reg):
    """Fetches unique data from the SIS portal for each ID."""
    url = SIS_URL.format(id=b64_encode(reg))
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(timeout=45.0, headers=headers) as client:
        try:
            r = await client.get(url)
            return BeautifulSoup(r.text, 'html.parser') if r.status_code == 200 else None
        except:
            return None

# --- 🤖 BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\n\nEnter Registration Number to login:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    msg = await update.message.reply_text(f"⏳ Syncing Profile `{reg}`...")
    soup = await fetch_portal_soup(reg)
    await msg.delete()

    if not soup:
        return await update.message.reply_text("❌ Portal Offline. Please try again later.")

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
        [InlineKeyboardButton("🔗 Open Full Results", url=SIS_URL.format(id=b64_encode(reg)))],
        [InlineKeyboardButton("🧹 Clear Dashboard", callback_data="clear")]
    ]

    await update.message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    
    if query.data == "clear":
        await query.answer("🧹 Dashboard Cleared")
        return await query.message.delete()

    await query.answer()
    soup = await fetch_portal_soup(reg)
    if not soup: return

    if query.data == "att":
        full_text = soup.get_text(separator=" ")
        match = re.search(r"Attendance\s*(\d+\.\d+)", full_text, re.I)
        val = match.group(1) if match else "N/A"
        
        kb = [[InlineKeyboardButton("🗑️ Delete Info", callback_data="clear")]]
        await query.message.reply_text(
            f"📈 *CURRENT SEM ATTENDANCE*\n━━━━━━━━━━━━━━━\n🆔 ID: `{reg}`\n📊 Percentage: `{val}%`", 
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "fee":
        fee_report = f"💰 *FEE LEDGER (ALL-TIME)*\n━━━━━━━━━━━━━━━\n"
        year_patterns = ["I-BTECH", "II-BTECH", "III-BTECH", "FIN-BTECH"]
        found_data = False

        for year_code in year_patterns:
            header = soup.find(string=re.compile(f"FEE DETAILS\s*\({year_code}\)", re.I))
            if header:
                data_row = header.find_parent('tr').find_next_sibling('tr')
                if data_row:
                    row_text = data_row.get_text(separator=" ")
                    paid = re.search(r"TOTAL PAID AMOUNT\s*:\s*([\d,.]+)", row_text)
                    bal = re.search(r"TOTAL BALANCE AMOUNT\s*:\s*([\d,.]+)", row_text)
                    p_val = paid.group(1) if paid else "0.00"
                    b_val = bal.group(1) if bal else "0.00"
                    
                    fee_report += f"📅 *{year_code}*\n ├ Paid: `₹{p_val}`\n └ Bal: `₹{b_val}`\n\n"
                    found_data = True

        if not found_data:
            fee_report += "⚠️ No Fee Ledger rows could be extracted."

        kb = [[InlineKeyboardButton("🗑️ Delete Info", callback_data="clear")]]
        await query.message.reply_text(fee_report, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 Bot is launching...")
    app.run_polling(drop_pending_updates=True)
