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
            self.wfile.write(b"GHOST_CORE_V18.0_ACTIVE")
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

client = httpx.AsyncClient(timeout=60.0, verify=False, follow_redirects=True, headers=HEADERS)

# --- 🛠️ UTILS ---
def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- 🤖 SHADOW OPERATORS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banner = (
        "```\n"
        "    ☠️  G H O S T _ E N G I N E  ☠️\n"
        "    ----------------------------\n"
        "    [ STATUS: CORE_v18.0_ACTIVE ]\n"
        "```\n"
        "⚡ **AWAITING TARGET UID:**"
    )
    await update.message.reply_text(banner, parse_mode=ParseMode.MARKDOWN)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    log = await update.message.reply_text("`[!] EXTRACTING DATA...`", parse_mode=ParseMode.MARKDOWN)
    
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
            [InlineKeyboardButton("💰 FEES", callback_data="fee")],
            [InlineKeyboardButton("🔗 VIEW PORTAL", url=SIS_URL.format(id=encoded_id))],
            [InlineKeyboardButton("💀 PURGE", callback_data="clear")]
        ]
        await update.message.reply_text(intel, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except:
        await log.edit_text("❌ `NODE_ERROR: PORTAL TIMEOUT`")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if not reg: return await query.answer("❌ SESSION_EXPIRED")
    encoded_id = b64_encode(reg)

    if query.data == "att":
        await query.answer("ISOLATING CURRENT SEM GAUGE...")
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        
        current_perc = "0.00"
        try:
            att_label = soup.find(string=re.compile(r"^Attendance$", re.I))
            if att_label:
                parent_row = att_label.find_parent('tr')
                cells = parent_row.find_all('td')
                for cell in cells[1:]:
                    val = cell.get_text(strip=True)
                    match = re.search(r"(\d{1,2}\.\d{2})", val)
                    if match and match.group(1) not in ["99.90", "99.9"]:
                        current_perc = match.group(1)
                        break
        except: pass

        await query.message.reply_text(f"📊 **CURRENT ATTENDANCE**\n📈 **SCORE:** `{current_perc}%`", parse_mode=ParseMode.MARKDOWN)

    elif query.data == "res":
        await query.answer("DUMPING GRADES...")
        r = await client.get(RESULT_BASE_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        
        report_lines = ["🏆 **GRADES**", "━━━━━━━━━━━━━━━"]
        found = False
        
        for row in soup.find_all('tr'):
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 4:
                subject_name = cols[2].get_text(strip=True)
                grade = cols[3].get_text(strip=True).upper()
                
                # Filter out header rows or invalid data
                if not subject_name or "SUBJECT" in subject_name.upper() or len(grade) > 2:
                    continue
                
                status_emoji = "✅" if grade not in ['F', 'AB', 'W', 'I'] else "❌"
                
                # Append formatted text for each subject
                report_lines.append(f"{status_emoji} **{subject_name}**")
                report_lines.append(f"└─ `GRADE: {grade}`\n")
                found = True
        
        if found:
            final_report = "\n".join(report_lines)
            await query.message.reply_text(final_report, parse_mode=ParseMode.MARKDOWN)
        else:
            await query.message.reply_text("`[!] NO GRADE DATA FOUND`", parse_mode=ParseMode.MARKDOWN)

    elif query.data == "fee":
        await query.answer("PULLING LEDGER...")
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        report = "💰 **LEDGER**\n━━━━━━━━━━━━━━━\n"
        for y in ["I-BTECH", "II-BTECH", "III-BTECH", "IV-BTECH", "FIN-BTECH"]:
            h = soup.find(string=re.compile(f"FEE DETAILS\s*\({y}\)", re.I))
            if h:
                try:
                    row = h.find_parent('tr').find_next_sibling('tr').get_text(" ")
                    p = re.search(r"PAID.*?([\d,.]+)", row, re.I).group(1)
                    b = re.search(r"BALANCE.*?([\d,.]+)", row, re.I).group(1)
                    report += f"📅 **{y}**: `P: ₹{p}` | `B: ₹{b}`\n"
                except: continue
        await query.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "clear":
        await query.message.edit_text("`[!] SYSTEM PURGED. SEND NEW REG NO.`")

# --- 🚀 RUNTIME ---
async def shadow_run():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("[!] GHOST_ENGINE ONLINE")
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(shadow_run())
    except KeyboardInterrupt:
        pass
