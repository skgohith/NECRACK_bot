import base64
import asyncio
import http.server
import socketserver
import threading
import re
import httpx
import os
import random
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
)

# --- 🛰️ 24/7 HEARTBEAT FOR KOYEB ---
def run_heartbeat():
    port = int(os.environ.get("PORT", 8080))
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_ENGINE_ONLINE")
        def log_message(self, format, *args): return

    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            httpd.serve_forever()
    except: pass

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- ⚙️ CONFIG ---
TOKEN = "8491426723:AAECUa6FEZbRy1ZKsJ7FWGA43QO3xIw5cHE"
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"

# List of Free Proxy Gateways / User Agents for Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- 🔍 DATA EXTRACTION ENGINE ---

def get_sis_value(soup, label):
    target = soup.find(string=re.compile(label, re.I))
    if target:
        parent_td = target.find_parent('td')
        if parent_td:
            next_td = parent_td.find_next_sibling('td')
            if next_td: return next_td.get_text(strip=True)
    return "N/A"

async def fetch_portal_soup(reg):
    url = SIS_URL.format(id=b64_encode(reg))
    
    # Rotates User-Agent for every request
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }

    async with httpx.AsyncClient(timeout=50.0, headers=headers, follow_redirects=True, verify=False) as client:
        try:
            # Note: For true IP rotation without a paid proxy, we rely on Koyeb's dynamic outbound routing
            r = await client.get(url)
            if r.status_code == 200:
                return BeautifulSoup(r.text, 'html.parser')
            return None
        except:
            return None

# --- 🤖 BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\nEnter Registration Number:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    msg = await update.message.reply_text(f"⏳ Rotating IP & Fetching `{reg}`...")
    soup = await fetch_portal_soup(reg)
    await msg.delete()

    if not soup:
        return await update.message.reply_text("❌ *Portal Offline*\nServer is blocking connections or down. Try again in 1 minute.")

    name = get_sis_value(soup, "NAME")
    htc = get_sis_value(soup, "HTC NO")

    profile_text = f"👤 *STUDENT PROFILE*\n━━━━━━━━━━━━━━━\n📛 *NAME:* `{name}`\n🆔 *HTC NO:* `{htc}`\n"
    
    keyboard = [
        [InlineKeyboardButton("📊 Attendance", callback_data="att"),
         InlineKeyboardButton("💰 Fee Ledger", callback_data="fee")],
        [InlineKeyboardButton("🔗 Open Results", url=SIS_URL.format(id=b64_encode(reg)))],
        [InlineKeyboardButton("🧹 Clear Dashboard", callback_data="clear")]
    ]
    await update.message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    
    if query.data == "clear":
        return await query.message.delete()

    await query.answer("🔄 Refreshing Data...")
    soup = await fetch_portal_soup(reg)
    if not soup:
        return await query.message.reply_text("❌ Portal Offline. Try again later.")

    if query.data == "att":
        full_text = soup.get_text(separator=" ")
        match = re.search(r"Attendance\s*(\d+\.\d+)", full_text, re.I)
        val = match.group(1) if match else "N/A"
        kb = [[InlineKeyboardButton("🗑️ Delete", callback_data="clear")]]
        await query.message.reply_text(f"📈 *ATTENDANCE*\nID: `{reg}`\n📊 Percentage: `{val}%`", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "fee":
        fee_report = f"💰 *FEE LEDGER*\n━━━━━━━━━━━━━━━\n"
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
                    fee_report += f"📅 *{year_code}*\n ├ Paid: `₹{paid.group(1) if paid else '0'}`\n └ Bal: `₹{bal.group(1) if bal else '0'}`\n\n"
                    found_data = True
        
        kb = [[InlineKeyboardButton("🗑️ Delete", callback_data="clear")]]
        await query.message.reply_text(fee_report if found_data else "⚠️ No fee data.", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling(drop_pending_updates=True)
    
    if query.data == "clear":
        return await query.message.delete()

    await query.answer("🔄 Refreshing Data...")
    soup = await fetch_portal_soup(reg)
    if not soup:
        return await query.message.reply_text("❌ Portal Offline. Try again later.")

    if query.data == "att":
        full_text = soup.get_text(separator=" ")
        match = re.search(r"Attendance\s*(\d+\.\d+)", full_text, re.I)
        val = match.group(1) if match else "N/A"
        kb = [[InlineKeyboardButton("🗑️ Delete", callback_data="clear")]]
        await query.message.reply_text(f"📈 *ATTENDANCE*\nID: `{reg}`\n📊 Percentage: `{val}%`", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "fee":
        fee_report = f"💰 *FEE LEDGER*\n━━━━━━━━━━━━━━━\n"
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
                    fee_report += f"📅 *{year_code}*\n ├ Paid: `₹{paid.group(1) if paid else '0'}`\n └ Bal: `₹{bal.group(1) if bal else '0'}`\n\n"
                    found_data = True
        
        kb = [[InlineKeyboardButton("🗑️ Delete", callback_data="clear")]]
        await query.message.reply_text(fee_report if found_data else "⚠️ No fee data.", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling(drop_pending_updates=True)

