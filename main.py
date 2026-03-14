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

# --- 🛰️ HEARTBEAT ---
def run_heartbeat():
    port = int(os.environ.get("PORT", 8080))
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_CORE_V16.4_ACTIVE")
        def log_message(self, format, *args): return
    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("0.0.0.0", port), HealthCheckHandler) as httpd:
            httpd.serve_forever()
    except: pass

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- ⚙️ CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN")
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"
RESULT_BASE_URL = "https://narayanagroup.co.in/patient/EngAutonomousReport.aspx/{id}"

client = httpx.AsyncClient(timeout=50.0, verify=False, follow_redirects=True)

# --- 🛠️ UTILS ---
def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def get_acronym(name):
    excluded = ['AND', 'THE', 'OF', 'IN', 'FOR', 'WITH', 'BY', 'LAB', 'LABORATORY']
    words = [word for word in re.split(r'[\s\-]+', name) if word.upper() not in excluded]
    return "".join([word[0] for word in words if word]).upper()[:6] if words else "SUB"

# --- 🤖 SHADOW OPERATORS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banner = (
        "```\n"
        "   ☠️  G H O S T _ E N G I N E  ☠️\n"
        "   ----------------------------\n"
        "   [ STATUS: CORE_v16.4_ACTIVE ]\n"
        "```\n"
        "⚡ **AWAITING TARGET UID:**"
    )
    await update.message.reply_text(banner, parse_mode=ParseMode.MARKDOWN)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    log = await update.message.reply_text("`[!] INTERCEPTING PACKETS...`", parse_mode=ParseMode.MARKDOWN)
    
    encoded_id = b64_encode(reg)
    try:
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        name_tag = soup.find(string=re.compile("NAME", re.I))
        name = name_tag.find_parent('td').find_next_sibling('td').get_text(strip=True) if name_tag else "CLASSIFIED"
        
        await log.delete()
        intel = f"🔓 **TARGET:** `{name}` | `{reg}`"
        
        kb = [
            [InlineKeyboardButton("📊 ATTENDANCE", callback_data="att"), InlineKeyboardButton("🏆 GRADES", callback_data="res")],
            [InlineKeyboardButton("💰 FINANCIALS", callback_data="fee")],
            [InlineKeyboardButton("🌐 VIEW PORTAL", url=SIS_URL.format(id=encoded_id))],
            [InlineKeyboardButton("💀 PURGE", callback_data="clear")]
        ]
        await update.message.reply_text(intel, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except:
        await log.edit_text("❌ `NODE_ERROR: CONNECTION_FAILED`")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if not reg: return await query.answer("❌ SESSION_EXPIRED")
    
    encoded_id = b64_encode(reg)

    if query.data == "res":
        await query.answer("SCRAPING GRADES...")
        r = await client.get(RESULT_BASE_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        transcript = "```\n+-- [ GRADES ] --+\n"
        found, backlogs = False, 0
        for row in soup.find_all('tr'):
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 4:
                sub, grd = cols[2].get_text(strip=True), cols[3].get_text(strip=True).upper()
                if not sub or "SUB" in sub.upper() or len(grd) > 2: continue
                is_fail = grd in ["F", "AB", "FAIL", "W"]
                if is_fail: backlogs += 1
                transcript += f"| {get_acronym(sub).ljust(6)} | {grd.ljust(1)} | {'❌' if is_fail else '✅'} |\n"
                found = True
        transcript += "+--------------+```"
        sgpa = re.search(r"SGPA\s*[:]?\s*(\d+\.\d+)", soup.get_text(), re.I)
        res_msg = f"🏆 **SGPA:** `{sgpa.group(1) if sgpa else '0.00'}` | ⚠️ **BL:** `{backlogs}`\n{transcript if found else '`[!] ENCRYPTED`'}"
        await query.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "att":
        await query.answer("ISOLATING CURRENT SEM...")
        r = await client.get(SIS_URL.format(id=encoded_id))
        # Finding all instances of percentages and picking the last one (Current Sem)
        val = re.findall(r"(\d+\.\d+)\s*%", r.text)
        current_perc = val[-1] if val else "0.0"
        status = "🚨 ALERT" if float(current_perc) < 75 else "🛡️ SECURE"
        await query.message.reply_text(f"📊 **CURRENT SEM ATTENDANCE:** `{current_perc}%` | {status}", parse_mode=ParseMode.MARKDOWN)

    elif query.data == "fee":
        await query.answer("DUMPING FULL LEDGER...")
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        report = "💰 **FULL FINANCIAL LEDGER**\n━━━━━━━━━━━━━━━\n"
        found_any = False
        
        # Iterating through all 4 years to show full history
        years = ["I-BTECH", "II-BTECH", "III-BTECH", "IV-BTECH"]
        for y in years:
            anchor = soup.find(string=re.compile(f"FEE DETAILS\s*\({y}\)", re.I))
            if anchor:
                try:
                    # Target the next data row after the header
                    data_row = anchor.find_parent('tr').find_next_sibling('tr').get_text(" ")
                    paid = re.search(r"TOTAL PAID AMOUNT\s*:\s*([\d,.]+)", data_row, re.I)
                    bal = re.search(r"TOTAL BALANCE AMOUNT\s*:\s*([\d,.]+)", data_row, re.I)
                    
                    p_val = paid.group(1) if paid else "0"
                    b_val = bal.group(1) if bal else "0"
                    
                    report += f"📅 **{y}**\n├─ Paid: `₹{p_val}`\n└─ Bal: `₹{b_val}`\n\n"
                    found_any = True
                except: continue
        
        await query.message.reply_text(report if found_any else "❌ `NO FINANCIAL RECORDS`", parse_mode=ParseMode.MARKDOWN)

    elif query.data == "clear":
        await query.message.edit_text("`[!] SYSTEM PURGED.`")

# --- 🚀 RUNTIME ---
async def shadow_run():
    if not TOKEN: return
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.initialize()
    await app.updater.start_polling(drop_pending_updates=True)
    await app.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    try: asyncio.run(shadow_run())
    except: pass
