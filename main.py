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

# --- 🛰️ HEARTBEAT (Railway/Deployment Keep-Alive) ---
def run_heartbeat():
    port = int(os.environ.get("PORT", 8080))
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_CORE_V16.6_ACTIVE")
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

# --- 🤖 SHADOW OPERATORS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banner = (
        "```\n"
        "   ☠️  G H O S T _ E N G I N E  ☠️\n"
        "   ----------------------------\n"
        "   [ STATUS: CORE_v16.6_ACTIVE ]\n"
        "```\n"
        "⚡ **AWAITING TARGET UID:**"
    )
    await update.message.reply_text(banner, parse_mode=ParseMode.MARKDOWN)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    log = await update.message.reply_text("`[!] BREACHING FIREWALL...`", parse_mode=ParseMode.MARKDOWN)
    
    encoded_id = b64_encode(reg)
    try:
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        name_tag = soup.find(string=re.compile("NAME", re.I))
        name = name_tag.find_parent('td').find_next_sibling('td').get_text(strip=True) if name_tag else "CLASSIFIED"
        
        await log.delete()
        intel = (
            f"🔓 **TARGET ACQUIRED**\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **ALIAS:** `{name}`\n🆔 **UID:** `{reg}`\n\n"
            f"🌐 **[ PORTAL ACCESS ]**"
        )
        
        kb = [
            [InlineKeyboardButton("📊 ATTENDANCE", callback_data="att"), InlineKeyboardButton("🏆 GRADES", callback_data="res")],
            [InlineKeyboardButton("💰 FINANCIALS", callback_data="fee")],
            [InlineKeyboardButton("🔗 VIEW ATTENDANCE", url=SIS_URL.format(id=encoded_id)),
             InlineKeyboardButton("🔗 VIEW RESULTS", url=RESULT_BASE_URL.format(id=encoded_id))],
            [InlineKeyboardButton("💀 PURGE", callback_data="clear")]
        ]
        await update.message.reply_text(intel, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    except:
        await log.edit_text("❌ `NODE_ERROR: Connection Dropped.`")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if not reg: return await query.answer("❌ SESSION_EXPIRED")
    
    encoded_id = b64_encode(reg)

    if query.data == "att":
        await query.answer("FETCHING SEMESTER STATS...")
        r = await client.get(SIS_URL.format(id=encoded_id))
        
        # Scrape current semester heading (e.g., III-BTECH (II-SEM))
        sem_header = re.search(r"Current Sem\s*-\s*([^<]+)", r.text, re.I)
        sem_name = sem_header.group(1).strip() if sem_header else "CURRENT SEM"
        
        # Target the specific Attendance value percentage
        val = re.findall(r"(\d+\.\d+)\s*%", r.text)
        current_perc = val[-1] if val else "0.0"
        
        msg = f"📊 **{sem_name}**\n━━━━━━━━━━━━━━━━━━━━\n📈 **ATTENDANCE:** `{current_perc}%`"
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "fee":
        await query.answer("DUMPING FULL LEDGER...")
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        report = "💰 **FULL FINANCIAL LEDGER**\n━━━━━━━━━━━━━━━━━━━━\n"
        found_any = False
        
        # Updated search to include all years and FIN-BTECH as per image
        targets = ["I-BTECH", "II-BTECH", "III-BTECH", "IV-BTECH", "FIN-BTECH"]
        for t in targets:
            anchor = soup.find(string=re.compile(f"FEE DETAILS\s*\({t}\)", re.I))
            if anchor:
                try:
                    data_row = anchor.find_parent('tr').find_next_sibling('tr').get_text(" ")
                    paid = re.search(r"TOTAL PAID AMOUNT\s*:\s*([\d,.]+)", data_row, re.I)
                    bal = re.search(r"TOTAL BALANCE AMOUNT\s*:\s*([\d,.]+)", data_row, re.I)
                    
                    p_val = paid.group(1) if paid else "0.00"
                    b_val = bal.group(1) if bal else "0.00"
                    
                    report += f"📅 **{t}**\n├─ Paid: `₹{p_val}`\n└─ Bal:  `₹{b_val}`\n\n"
                    found_any = True
                except: continue
        
        await query.message.reply_text(report if found_any else "❌ `NO FINANCIAL DATA`", parse_mode=ParseMode.MARKDOWN)

    elif query.data == "res":
        # Standard result scrape logic remains available
        await query.answer("DECRYPTING GRADES...")
        await query.message.reply_text("`[!] Detailed results available via 'VIEW RESULTS' link.`")

    elif query.data == "clear":
        await query.message.edit_text("`[!] TRACES WIPED.`")

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
