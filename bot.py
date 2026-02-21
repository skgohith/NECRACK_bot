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

# --- 🛰️ 24/7 HEARTBEAT ---
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
RESULT_BASE_URL = "https://narayanagroup.co.in/patient/EngAutonomousReport.aspx/{id}"

# Robust Client with Real Browser Headers
limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
async_client = httpx.AsyncClient(
    timeout=30.0, 
    limits=limits, 
    follow_redirects=True, 
    verify=False,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
)

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def get_acronym(name):
    excluded = ['AND', 'THE', 'OF', 'IN', 'FOR', 'WITH', 'BY', 'LAB', 'LABORATORY']
    words = [word for word in re.split(r'[\s\-]+', name) if word.upper() not in excluded]
    if not words: return "SUB"
    if len(words) == 1: return words[0][:6].upper()
    return "".join([word[0] for word in words if word]).upper()

async def fetch_soup(url):
    try:
        r = await async_client.get(url)
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
    if not reg: return
    context.user_data["reg"] = reg
    encoded_id = b64_encode(reg)
    msg = await update.message.reply_text("⚡ *Syncing Engine...*")
    
    soup_sis = await fetch_soup(SIS_URL.format(id=encoded_id))
    await msg.delete()

    if not soup_sis: 
        return await update.message.reply_text("❌ *Portal Offline*\nServer is not responding.")

    name = "Student"
    name_tag = soup_sis.find(string=re.compile("NAME", re.I))
    if name_tag:
        try:
            name = name_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)
        except: pass

    profile_text = f"👤 *STUDENT PROFILE*\n━━━━━━━━━━━━━━━\n📛 *NAME:* `{name}`\n🆔 *ID:* `{reg}`\n"
    
    kb = [
        [InlineKeyboardButton("📊 Quick Attendance", callback_data="att"), InlineKeyboardButton("🏆 Quick Results", callback_data="res")],
        [InlineKeyboardButton("💰 Fee Ledger", callback_data="fee")],
        [InlineKeyboardButton("🌐 Attendance Portal", url=SIS_URL.format(id=encoded_id))],
        [InlineKeyboardButton("🌐 Result Portal", url=RESULT_BASE_URL.format(id=encoded_id))],
        [InlineKeyboardButton("🧹 Clear Dashboard", callback_data="clear")]
    ]
    
    await update.message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if not reg: return await query.answer("❌ Session Expired.")
    
    if query.data == "clear": return await query.message.delete()
    
    await query.answer("🚀 Processing...")
    encoded_id = b64_encode(reg)

    if query.data == "res":
        soup = await fetch_soup(RESULT_BASE_URL.format(id=encoded_id))
        if not soup: 
            return await query.message.reply_text("❌ Result Portal unreachable.")
        
        full_text = soup.get_text(separator=" ")
        sgpa_match = re.search(r"SGPA\s*[:]?\s*(\d+\.\d+)", full_text, re.I)
        sgpa = sgpa_match.group(1) if sgpa_match else "N/A"
        
        # --- FIXED TABLE DETECTION ---
        transcript = "```\n+---------+-----+-----+\n| SUB     | GRD | RES |\n+---------+-----+-----+\n"
        backlogs = 0
        found_data = False
        
        # Scan all tables to find the one containing grades
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 4:
                    # Column 2 is usually Subject, Column 3 is Grade
                    sub_text = cols[2].get_text(strip=True)
                    grade_text = cols[3].get_text(strip=True).upper()
                    
                    # Filter out header rows
                    if not sub_text or "SUBJECT" in sub_text.upper() or len(grade_text) > 2:
                        continue
                    
                    short_name = get_acronym(sub_text)
                    status = "F" if grade_text in ["F", "AB", "FAIL"] else "P"
                    if status == "F": backlogs += 1
                    
                    transcript += f"| {short_name.ljust(7)} | {grade_text.ljust(3)} | {status.ljust(3)} |\n"
                    found_data = True
            if found_data: break 

        transcript += "+---------+-----+-----+```" 

        res_msg = (
            f"🏆 *RESULTS:* `{reg}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 SGPA: `{sgpa}` | 📉 BL: `{backlogs}`\n\n"
            f"📖 *TRANSCRIPT:*\n{transcript if found_data else '⚠️ No records found.'}"
        )
        return await query.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN)

    # Attendance & Fee Logic
    soup = await fetch_soup(SIS_URL.format(id=encoded_id))
    if not soup: return await query.message.reply_text("❌ Portal Offline.")

    if query.data == "att":
        val = re.search(r"Attendance\s*(\d+\.\d+)", soup.get_text(), re.I)
        await query.message.reply_text(f"📊 *ATTENDANCE:* `{val.group(1) if val else 'N/A'}%`", parse_mode=ParseMode.MARKDOWN)
    elif query.data == "fee":
        fee_report = "💰 *FEE LEDGER*\n━━━━━━━━━━━━━━━\n"
        for y in ["I-BTECH", "II-BTECH", "III-BTECH", "FIN-BTECH"]:
            h = soup.find(string=re.compile(f"FEE DETAILS\s*\({y}\)", re.I))
            if h:
                try:
                    row = h.find_parent('tr').find_next_sibling('tr').get_text(separator=" ")
                    p = re.search(r"TOTAL PAID AMOUNT\s*:\s*([\d,.]+)", row)
                    b = re.search(r"TOTAL BALANCE AMOUNT\s*:\s*([\d,.]+)", row)
                    fee_report += f"📅 *{y}*: P: `₹{p.group(1) if p else '0'}` | B: `₹{b.group(1) if b else '0'}`\n"
                except: pass
        await query.message.reply_text(fee_report, parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling(drop_pending_updates=True)
    encoded_id = b64_encode(reg)

    if query.data == "res":
        soup = await fetch_soup(RESULT_BASE_URL.format(id=encoded_id))
        if not soup: 
            return await query.message.reply_text("❌ Result Portal unreachable.")
        
        full_text = soup.get_text(separator=" ")
        sgpa = re.search(r"SGPA\s*[:]?\s*(\d+\.\d+)", full_text, re.I)
        
        # FIX: Precise Alignment with Monospace Grid
        transcript = "```\n+---------+-----+-----+\n| SUB     | GRD | RES |\n+---------+-----+-----+\n"
        backlogs = 0
        table = soup.find('table')
        
        if table:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 4:
                    full_name = cols[2].get_text(strip=True)
                    grade = cols[3].get_text(strip=True).upper()
                    if not full_name or "SUBJECT" in full_name.upper(): continue
                    
                    short_name = get_acronym(full_name)
                    status = "F" if grade in ["F", "AB", "FAIL"] else "P"
                    if status == "F": backlogs += 1
                    
                    # Formatting columns to fixed widths
                    transcript += f"| {short_name.ljust(7)} | {grade.ljust(3)} | {status.ljust(3)} |\n"
            
            transcript += "+---------+-----+-----+```" 

        res_msg = (
            f"🏆 *RESULTS:* `{reg}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 SGPA: `{sgpa.group(1) if sgpa else 'N/A'}` | 📉 BL: `{backlogs}`\n\n"
            f"📖 *TRANSCRIPT:*\n{transcript}"
        )
        return await query.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN)

    # Attendance & Fee Logic
    soup = await fetch_soup(SIS_URL.format(id=encoded_id))
    if not soup: return await query.message.reply_text("❌ Portal Offline.")

    if query.data == "att":
        val = re.search(r"Attendance\s*(\d+\.\d+)", soup.get_text(), re.I)
        await query.message.reply_text(f"📊 *ATTENDANCE:* `{val.group(1) if val else 'N/A'}%`", parse_mode=ParseMode.MARKDOWN)
    elif query.data == "fee":
        fee_report = "💰 *FEE LEDGER*\n━━━━━━━━━━━━━━━\n"
        for y in ["I-BTECH", "II-BTECH", "III-BTECH", "FIN-BTECH"]:
            h = soup.find(string=re.compile(f"FEE DETAILS\s*\({y}\)", re.I))
            if h:
                row = h.find_parent('tr').find_next_sibling('tr').get_text(separator=" ")
                p = re.search(r"TOTAL PAID AMOUNT\s*:\s*([\d,.]+)", row)
                b = re.search(r"TOTAL BALANCE AMOUNT\s*:\s*([\d,.]+)", row)
                fee_report += f"📅 *{y}*: P: `₹{p.group(1) if p else '0'}` | B: `₹{b.group(1) if b else '0'}`\n"
        await query.message.reply_text(fee_report, parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling(drop_pending_updates=True)

