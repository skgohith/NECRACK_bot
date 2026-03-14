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

# --- 🛰️ THE HEARTBEAT (KEEPALIVE) ---
def run_heartbeat():
    port = int(os.environ.get("PORT", 8080))
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_SYSTEM_ACTIVE")
        def log_message(self, format, *args): return

    try:
        socketserver.TCPServer.allow_reuse_address = True
        # Binding to 0.0.0.0 ensures Railway can reach the server
        with socketserver.TCPServer(("0.0.0.0", port), HealthCheckHandler) as httpd:
            print(f"📡 Heartbeat/Web Server active on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"❌ Heartbeat Server Error: {e}")

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- ⚙️ GHOST CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN")
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"
RESULT_BASE_URL = "https://narayanagroup.co.in/patient/EngAutonomousReport.aspx/{id}"

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
]

client = httpx.AsyncClient(
    timeout=40.0, 
    follow_redirects=True, 
    verify=False,
    headers={"User-Agent": random.choice(USER_AGENTS)}
)

# --- 🛠️ UTILS ---
def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- 🤖 HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "⚡ **GHOST_ENGINE v16.0 ONLINE**\n"
        "```\n"
        "  _____ _    _  ____   _____ _______ \n"
        " / ____| |  | |/ __ \\ / ____|__   __|\n"
        "| |  __| |__| | |  | | (___    | |   \n"
        "| | |_ |  __  | |  | |\\___ \\   | |   \n"
        "| |__| | |  | | |__| |____) |  | |   \n"
        " \\_____|_|  |_|\\____/|_____/   |_|   \n"
        "```\n"
        "📡 *Awaiting Registration ID...*"
    )
    await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    status_msg = await update.message.reply_text("🔍 `INJECTING PACKETS...`")
    await asyncio.sleep(0.5)
    await status_msg.edit_text("🧬 `DECRYPTING DATA...`")

    encoded_id = b64_encode(reg)
    try:
        r = await client.get(SIS_URL.format(id=encoded_id))
        soup = BeautifulSoup(r.text, 'html.parser')
        
        name = "UNKNOWN_ENTITY"
        name_tag = soup.find(string=re.compile("NAME", re.I))
        if name_tag:
            try:
                name = name_tag.find_parent('td').find_next_sibling('td').get_text(strip=True)
            except: pass

        await status_msg.delete()
        
        profile = (
            f"👤 **TARGET ACQUIRED**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📛 **NAME:** `{name}`\n"
            f"🆔 **UID:** `{reg}`\n"
            f"🌐 **STATUS:** `CONNECTED`"
        )
        
        kb = [
            [InlineKeyboardButton("📊 ATTENDANCE", callback_data="att"), InlineKeyboardButton("🏆 RESULTS", callback_data="res")],
            [InlineKeyboardButton("💰 FEE LEDGER", callback_data="fee")],
            [InlineKeyboardButton("❌ DISCONNECT", callback_data="clear")]
        ]
        
        await update.message.reply_text(profile, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    
    except Exception as e:
        await status_msg.edit_text("⚠️ **CONNECTION BREACHED.** Portal unreachable.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    if not reg: 
        return await query.answer("Session expired. Please re-enter ID.")
    
    await query.answer("Extracting Data...")
    
    if query.data == "res":
        res_text = (
            f"🏆 **GRADE SHEET: {reg}**\n"
            "```\n"
            "DATA RETRIEVAL ACTIVE...\n"
            "```"
        )
        await query.message.reply_text(res_text, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "clear":
        await query.message.edit_text("🔌 **SESSION TERMINATED.**")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ CRITICAL ERROR: BOT_TOKEN not found in environment variables.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
        app.add_handler(CallbackQueryHandler(button_handler))
        
        print("🤖 GHOST_ENGINE is starting...")
        # THE FIX: This clears the backlog of old messages and forces a clean start
        app.run_polling(drop_pending_updates=True)
