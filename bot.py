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

limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
async_client = httpx.AsyncClient(timeout=30.0, limits=limits, follow_redirects=True, verify=False)

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def get_acronym(name):
    excluded = ['AND', 'THE', 'OF', 'IN', 'FOR', 'WITH', 'BY', 'LAB', 'LABORATORY']
    words = [word for word in re.split(r'[\s\-]+', name) if word.upper() not in excluded]
    if len(words) == 1: return words[0][:6].upper()
    return "".join([word[0] for word in words if word]).upper()

async def fetch_soup(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"}
    try:
        r = await async_client.get(url, headers=headers)
        return BeautifulSoup(r.text, 'html.parser') if r.status_code == 200 else None
    except: return None

# --- 🤖 BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\nEnter Registration Number:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    encoded_id = b64_encode(reg)
    msg = await update.message.reply_text("⚡ *Syncing Engine...*")
    
    results = await asyncio.gather(
        fetch_soup(SIS_URL.format(id=encoded_id)),
        fetch_soup(RESULT_BASE_URL.format(id=encoded_id))
    )
    soup_sis, _ = results
    await msg.delete()

    if not soup_sis: return await update.message.reply_text("❌ *Portal Offline*")

    name_target = soup_sis.find(string=re.compile("NAME", re.I))
    name = name_target.find_parent('td').find_next_sibling('td').get_text(strip=True) if name_target else "N/A"

    profile_text = f"👤 *STUDENT PROFILE*\n━━━━━━━━━━━━━━━\n📛 *NAME:* `{name}`\n🆔 *ID:* `{reg}`\n"
    kb = [[InlineKeyboardButton("📊 Attendance", callback_data="att"), InlineKeyboardButton("🏆 Results", callback_data="res")],
          [InlineKeyboardButton("💰 Fee Ledger", callback_data="fee")],
          [InlineKeyboardButton("🧹 Clear Dashboard", callback_data="clear")]]
    await update.message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if query.data == "clear": return await query.message.delete()
    await query.answer("🚀 Ghost Speed Active...")
    encoded_id = b64_encode(reg)

    if query.data == "res":
        soup = await fetch_soup(RESULT_BASE_URL.format(id=encoded_id))
        if not soup: return await query.message.reply_text("❌ Results Unreachable.")
        
        full_text = soup.get_text(separator=" ")
        sgpa = re.search(r"SGPA\s*[:]?\s*(\d+\.\d+)", full_text, re.I)
        
        # --- FIXED ALIGNMENT LOGIC ---
        # Headers: SUB (7 chars) | GRD (4 chars) | RES
        transcript = "```\nSUB     | GRD | RES\n--------|-----|-----\n"
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
                    res_status = "PASS"
                    if grade in ["F", "AB", "FAIL"]:
                        res_status = "FAIL"
                        backlogs += 1
                    
                    # Aligns data exactly under the headers
                    transcript += f"{short_name.ljust(7)} | {grade.ljust(3)} | {res_status}\n"
            
            transcript += "```" 

        res_msg = (
            f"🏆 *RESULTS:* `{reg}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 SGPA: `{sgpa.group(1) if sgpa else 'N/A'}` | 📉 BL: `{backlogs}`\n\n"
            f"📖 *TRANSCRIPT:*\n{transcript if len(transcript) > 30 else '⚠️ No records found.'}"
        )
        return await query.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN)

    # Standard SIS logic for Attendance/Fee
    soup = await fetch_soup(SIS_URL.format(id=encoded_id))
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
                    short_name = get_acronym(full_name)
                    res_status = "P"
                    if grade in ["F", "AB", "FAIL"]:
                        res_status = "F"
                        backlogs += 1
                    
                    # Formatting columns using ljust for alignment
                    transcript += f"{short_name.ljust(5)} | {grade.ljust(3)} | {res_status}\n"
            
            transcript += "```" # End table block

        res_msg = (
            f"🏆 *RESULTS:* `{reg}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 SGPA: `{sgpa.group(1) if sgpa else 'N/A'}` | 📉 BL: `{backlogs}`\n\n"
            f"📖 *TRANSCRIPT:*\n{transcript if len(transcript) > 20 else '⚠️ No records.'}"
        )
        return await query.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN)

    # Attendance/Fee Ledger
    soup = await fetch_soup(SIS_URL.format(id=encoded_id))
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
                    if grade in ["F", "AB", "FAIL"]:
                        status = "FAIL"
                        backlogs += 1
                    
                    # FORMAT: SUB | GRADE | STATUS
                    transcript += f" ┕ `{short_name.ljust(5)}` | `{grade.center(3)}` | **{status}**\n"

        res_msg = (
            f"🏆 *RESULTS:* `{reg}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 SGPA: `{sgpa.group(1) if sgpa else 'N/A'}` | 📉 BL: `{backlogs}`\n\n"
            f"📖 *TRANSCRIPT (SUB | GRD | RES):*\n{transcript if transcript else '⚠️ No records.'}"
        )
        return await query.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN)

    # Attendance/Fee
    soup = await fetch_soup(SIS_URL.format(id=encoded_id))
    if query.data == "att":
        val = re.search(r"Attendance\s*(\d+\.\d+)", soup.get_text(), re.I)
        await query.message.reply_text(f"📊 *ATTENDANCE:* `{val.group(1) if val else 'N/A'}%`")
    elif query.data == "fee":
        fee_report = "💰 *FEE LEDGER*\n━━━━━━━━━━━━━━━\n"
        for y in ["I-BTECH", "II-BTECH", "III-BTECH", "FIN-BTECH"]:
            h = soup.find(string=re.compile(f"FEE DETAILS\s*\({y}\)", re.I))
            if h:
                row = h.find_parent('tr').find_next_sibling('tr').get_text(separator=" ")
                p = re.search(r"TOTAL PAID AMOUNT\s*:\s*([\d,.]+)", row); b = re.search(r"TOTAL BALANCE AMOUNT\s*:\s*([\d,.]+)", row)
                fee_report += f"📅 *{y}*: P: `₹{p.group(1) if p else '0'}` | B: `₹{b.group(1) if b else '0'}`\n"
        await query.message.reply_text(fee_report, parse_mode=ParseMode.MARKDOWN)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling(drop_pending_updates=True)


