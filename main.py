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

# --- 🛰️ RAILWAY NEURAL LINK (Keep-Alive) ---
def run_heartbeat():
    port = int(os.environ.get("PORT", 8080))
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_CORE_V16_STABLE")
        def log_message(self, format, *args): return
    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            httpd.serve_forever()
    except: pass

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- ⚙️ ENCRYPTED CONFIG ---
BOT_TOKEN = os.environ.get("8491426723:AAGtl7ZD7PSVd40cmTBZfGaM9RFO9636X-8")
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"
RESULT_BASE_URL = "https://narayanagroup.co.in/patient/EngAutonomousReport.aspx/{id}"

# Cloaking Headers
HEADERS = {
    "User-Agent": f"GhostEngine/Exploit-V16 (X11; Kali; Linux x86_64) Protocol/7.1.{random.randint(10,99)}",
    "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
}

client = httpx.AsyncClient(timeout=45.0, verify=False, headers=HEADERS)

# --- 🛠️ OSINT UTILS ---
def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def get_acronym(name):
    excluded = ['AND', 'THE', 'OF', 'IN', 'FOR', 'WITH', 'BY', 'LAB', 'LABORATORY']
    words = [word for word in re.split(r'[\s\-]+', name) if word.upper() not in excluded]
    if not words: return "NULL"
    return "".join([word[0] for word in words if word]).upper()[:6]

# --- 🤖 SHADOW OPERATORS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banner = (
        "```\n"
        "   ☠️  G H O S T _ E N G I N E  ☠️\n"
        "   ----------------------------\n"
        "   [ STATUS: SYSTEM BREACHING ]\n"
        "   [ VECTOR: REMOTE_OVERFLOW  ]\n"
        "```\n"
        "⚡ **AWAITING TARGET UID (Reg No):**\n"
        "_Send ID to initiate exfiltration..._"
    )
    await update.message.reply_text(banner, parse_mode=ParseMode.MARKDOWN)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    # Visual Hack Sequence
    log = await update.message.reply_text("`[!] SPOOFING IP...`", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.4)
    await log.edit_text("`[!] OVERRIDING PORTAL FIREWALL...`")
    await asyncio.sleep(0.4)
    await log.edit_text("`[!] EXFILTRATING SUBJECT_DATA...`")
    
    encoded_id = b64_encode(reg)
    try:
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        
        name = "CLASSIFIED"
        name_tag = soup.find(string=re.compile("NAME", re.I))
        if name_tag:
            name = name_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)

        await log.delete()
        
        intel = (
            f"🔓 **TARGET ASSET ACQUIRED**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **ALIAS:** `{name}`\n"
            f"🆔 **UID:** `{reg}`\n"
            f"🛡️ **THREAT:** `LEVEL_{random.randint(1,5)}`"
        )
        
        kb = [
            [InlineKeyboardButton("📊 INTERCEPT ATTENDANCE", callback_data="att")],
            [InlineKeyboardButton("🏆 DUMP GRADE_REPORTS", callback_data="res")],
            [InlineKeyboardButton("💰 EXTRACT FINANCIALS", callback_data="fee")],
            [InlineKeyboardButton("💀 PURGE TRACES", callback_data="clear")]
        ]
        
        await update.message.reply_text(intel, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await log.edit_text("❌ `CRITICAL_FAILURE: Node Connection Dropped.`")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if not reg: return await query.answer("❌ SESSION_EXPIRED")
    
    await query.answer("DECRYPTING PACKETS...")
    encoded_id = b64_encode(reg)

    if query.data == "res":
        r = await client.get(RESULT_BASE_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        
        transcript = "```\n+--- [ CORE_TRANSCRIPT ] ---+\n"
        transcript += "| CODE    | G | STATUS     |\n"
        transcript += "+---------+---+------------+\n"
        
        found, backlogs = False, 0
        for row in soup.find_all('tr'):
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 4:
                sub = cols[2].get_text(strip=True)
                grd = cols[3].get_text(strip=True).upper()
                if not sub or "SUB" in sub.upper() or len(grd) > 2: continue
                
                is_fail = grd in ["F", "AB", "FAIL", "W"]
                status = "❌ BREACHED" if is_fail else "✅ CLEARED"
                if is_fail: backlogs += 1
                
                transcript += f"| {get_acronym(sub).ljust(7)} | {grd.ljust(1)} | {status.ljust(10)} |\n"
                found = True
        
        transcript += "+--------------------------+```"
        
        full_text = soup.get_text(separator=" ")
        sgpa_match = re.search(r"SGPA\s*[:]?\s*(\d+\.\d+)", full_text, re.I)
        sgpa = sgpa_match.group(1) if sgpa_match else "0.00"
        
        verdict = "🔴 [ SYSTEM_STATE: COMPROMISED ]" if backlogs > 0 else "🟢 [ SYSTEM_STATE: SECURE ]"

        res_msg = (
            f"🏆 **EXFILTRATION COMPLETE**\n"
            f"📈 **SGPA:** `{sgpa}` | ⚠️ **BL:** `{backlogs}`\n"
            f"{verdict}\n\n"
            f"{transcript if found else '`[!] ENCRYPTED DATA NOT FOUND`'}"
        )
        await query.message.reply_text(res_msg, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "att":
        r = await client.get(SIS_URL.format(id=encoded_id))
        val = re.search(r"Attendance\s*(\d+\.\d+)", r.text, re.I)
        perc = val.group(1) if val else "0.0"
        alert = "🚨 CRITICAL_LEAK" if float(perc) < 75 else "🛡️ FULLY_ARMED"
        await query.message.reply_text(f"📊 **SURVEILLANCE:** `{perc}%` | {alert}", parse_mode=ParseMode.MARKDOWN)

    elif query.data == "fee":
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        report = "💰 **FINANCIAL_EXTRACT**\n━━━━━━━━━━━━━━━\n"
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
        await query.message.reply_text(report if found_fee else "❌ `NO FINANCIAL ASSETS DETECTED`", parse_mode=ParseMode.MARKDOWN)

    elif query.data == "clear":
        await query.message.edit_text("`[!] TRACES WIPED. GHOST MODE ACTIVE.`")

if __name__ == "__main__":
    print("💀 GHOST_ENGINE_V16 INITIALIZED. OPERATING UNDER SHADOW PROTOCOL...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
