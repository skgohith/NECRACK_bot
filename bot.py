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
# Dynamic result URL based on your specific autonomous portal link
RESULT_URL = "https://narayanagroup.co.in/patient/EngAutonomousReport.aspx/MjAyMjA5MDl2MGgx"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- 🔍 DATA EXTRACTION ENGINE ---

async def fetch_soup(url):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with httpx.AsyncClient(timeout=50.0, headers=headers, follow_redirects=True, verify=False) as client:
        try:
            r = await client.get(url)
            return BeautifulSoup(r.text, 'html.parser') if r.status_code == 200 else None
        except: return None

# --- 🤖 BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\nEnter Registration Number:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    msg = await update.message.reply_text(f"⏳ Synchronizing Ghost Engine for `{reg}`...")
    soup = await fetch_soup(SIS_URL.format(id=b64_encode(reg)))
    await msg.delete()

    if not soup:
        return await update.message.reply_text("❌ *Portal Offline*\nTry again in a moment.")

    name_target = soup.find(string=re.compile("NAME", re.I))
    name = name_target.find_parent('td').find_next_sibling('td').get_text(strip=True) if name_target else "N/A"

    profile_text = f"👤 *STUDENT PROFILE*\n━━━━━━━━━━━━━━━\n📛 *NAME:* `{name}`\n🆔 *ID:* `{reg}`\n"
    keyboard = [[InlineKeyboardButton("📊 Attendance", callback_data="att"), InlineKeyboardButton("🏆 Results", callback_data="res")],
                [InlineKeyboardButton("💰 Fee Ledger", callback_data="fee")],
                [InlineKeyboardButton("🧹 Clear Dashboard", callback_data="clear")]]
    await update.message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if query.data == "clear": return await query.message.delete()
    await query.answer("📡 Fetching Data...")

    if query.data == "res":
        soup = await fetch_soup(RESULT_URL)
        if not soup: return await query.message.reply_text("❌ Results Portal Unreachable.")
        
        full_text = soup.get_text(separator=" ")
        sgpa_match = re.search(r"SGPA\s*[:]?\s*(\d+\.\d+)", full_text, re.I)
        sgpa = sgpa_match.group(1) if sgpa_match else "N/A"

        transcript = ""
        backlogs = 0
        # Target the table containing "Subject Name"
        table = soup.find('table', {'id': re.compile(r'GridView|DataGrid|Table', re.I)}) or soup.find('table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5: # Ensuring it's a data row
                    sub_name = cols[2].get_text(strip=True) # Subject Name column
                    grade = cols[3].get_text(strip=True)    # Grades column
                    if sub_name and grade and sub_name != "Subject Name":
                        if grade in ["F", "AB"]: backlogs += 1
                        # Highlight outstanding grades in bold
                        display_grade = f"**{grade}**" if grade in ["O", "A+", "A"] else f"({grade})"
                        transcript += f" ┕ `{sub_name}`: {display_grade}\n"

        res_msg = (
            f"🏆 *ACADEMIC RESULTS*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{reg}`\n"
            f"📈 SGPA: `{sgpa}`\n"
            f"📉 Total Backlogs: `{backlogs}`\n\n"
            f"✅ *SEMESTER TRANSCRIPT:*\n"
            f"{transcript if transcript else '⚠️ No transcript data found.'}\n"
        )
        kb = [[InlineKeyboardButton("🗑️ Delete", callback_data="clear")]]
        return await query.message.reply_text(res_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    # Re-fetch SIS soup for Attendance/Fee
    soup = await fetch_soup(SIS_URL.format(id=b64_encode(reg)))
    if not soup: return

    if query.data == "att":
        val = re.search(r"Attendance\s*(\d+\.\d+)", soup.get_text(), re.I)
        kb = [[InlineKeyboardButton("🗑️ Delete", callback_data="clear")]]
        await query.message.reply_text(f"📈 *ATTENDANCE*\n📊 Percentage: `{val.group(1) if val else 'N/A'}%`", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "fee":
        fee_report = f"💰 *FEE LEDGER*\n━━━━━━━━━━━━━━━\n"
        for y in ["I-BTECH", "II-BTECH", "III-BTECH", "FIN-BTECH"]:
            h = soup.find(string=re.compile(f"FEE DETAILS\s*\({y}\)", re.I))
            if h:
                row = h.find_parent('tr').find_next_sibling('tr').get_text(separator=" ")
                p = re.search(r"TOTAL PAID AMOUNT\s*:\s*([\d,.]+)", row)
                b = re.search(r"TOTAL BALANCE AMOUNT\s*:\s*([\d,.]+)", row)
                fee_report += f"📅 *{y}*\n ├ Paid: `₹{p.group(1) if p else '0.00'}`\n └ Bal: `₹{b.group(1) if b else '0.00'}`\n\n"
        kb = [[InlineKeyboardButton("🗑️ Delete", callback_data="clear")]]
        await query.message.reply_text(fee_report, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling(drop_pending_updates=True)
