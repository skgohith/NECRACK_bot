import base64
import asyncio
import httpx
import re
import http.server
import socketserver
import threading
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
)

# --- 24/7 HEARTBEAT (KOYEB FIX) ---
def run_heartbeat():
    """Starts a simple web server to keep the hosting service from sleeping."""
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_ENGINE_ONLINE")

    with socketserver.TCPServer(("", 8080), HealthCheckHandler) as httpd:
        httpd.serve_forever()

# Start heartbeat in background thread
threading.Thread(target=run_heartbeat, daemon=True).start()

# --- CONFIG ---
TOKEN = "8491426723:AAECUa6FEZbRy1ZKsJ7FWGA43QO3xIw5cHE"
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"

# --- CORE ENGINE ---

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

async def get_portal_data(reg):
    url = SIS_URL.format(id=b64_encode(reg))
    async with httpx.AsyncClient(timeout=25.0) as client:
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = await client.get(url, headers=headers)
            return BeautifulSoup(response.text, 'html.parser') if response.status_code == 200 else None
        except:
            return None

async def scrape_attendance(reg):
    soup = await get_portal_data(reg)
    if not soup: return "❌ Portal Unreachable."
    text = soup.get_text()
    att = re.search(r"Attendance\s*([\d.]+)", text, re.I)
    return (
        f"📈 *CURRENT SEMESTER STATUS*\n━━━━━━━━━━━━━━━\n"
        f"✅ Attendance: `{att.group(1) if att else 'N/A'}%`"
    )

async def scrape_fees(reg):
    soup = await get_portal_data(reg)
    if not soup: return "❌ Portal Unreachable."
    fee_sections = soup.find_all(text=re.compile(r"FEE DETAILS", re.I))
    res = "💰 *FEE LEDGER (ALL-TIME)*\n━━━━━━━━━━━━━━━\n"
    if not fee_sections: return res + "⚠️ No fee history detected."

    for section in fee_sections:
        parent = section.find_parent("tr") or section.find_parent("table")
        data_container = parent.find_next_sibling() if parent else None
        if data_container:
            data_text = data_container.get_text(separator=" ", strip=True)
            year_label = re.search(r"\((.*?)\)", section)
            paid = re.search(r"PAID AMOUNT\s*:\s*([\d,.]+)", data_text)
            bal = re.search(r"BALANCE AMOUNT\s*:\s*([\d,.]+)", data_text)
            if year_label and paid:
                display_year = year_label.group(1).replace("FIN-BTECH", "Final B.Tech").replace("-BTECH", " B.Tech")
                res += f"📅 *{display_year}*\n   ├ Paid: `₹{paid.group(1)}` \n   └ Bal: `₹{bal.group(1) if bal else '0.00'}`\n\n"
    return res

# --- BOT INTERFACE ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\n\nEnter Registration ID to start:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    keyboard = [[InlineKeyboardButton("📊 Attendance", callback_data="att")], [InlineKeyboardButton("💰 Fee Ledger", callback_data="fee")]]
    await update.message.reply_text(f"🔑 *ID AUTHENTICATED:* `{reg}`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if not reg: return await query.answer("Session expired.")
    await query.answer("Fetching...")
    report = await scrape_attendance(reg) if query.data == "att" else await scrape_fees(reg)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🆔 *ID:* `{reg}`\n\n{report}", parse_mode=ParseMode.MARKDOWN)

# --- RUN ---
if __name__ == "__main__":
    print("GHOST_ENGINE_V16_STARTING...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()