import base64
import asyncio
import http.server
import socketserver
import threading
import re
import httpx
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
)

# --- 24/7 HEARTBEAT (Keeps Koyeb active) ---
def run_heartbeat():
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_ENGINE_ONLINE")
    try:
        with socketserver.TCPServer(("", 8080), HealthCheckHandler) as httpd:
            httpd.serve_forever()
    except:
        pass

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- CONFIG ---
TOKEN = "8491426723:AAECUa6FEZbRy1ZKsJ7FWGA43QO3xIw5cHE"
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- DATA EXTRACTION ENGINE ---

async def get_portal_soup(reg):
    url = SIS_URL.format(id=b64_encode(reg))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
            return None
        except Exception as e:
            print(f"Connection Error: {e}")
            return None

def extract_smart(soup, keywords):
    """Aggressive search: looks for labels and grabs the next text piece."""
    for keyword in keywords:
        # Search for any tag containing the keyword
        target = soup.find(string=re.compile(keyword, re.I))
        if target:
            # The data is usually in the next cell (td)
            parent = target.find_parent('td')
            if parent:
                # Check next sibling
                val = parent.find_next_sibling('td')
                if val:
                    return val.get_text(strip=True)
                # If not sibling, check next overall td
                val = target.find_next('td')
                if val:
                    return val.get_text(strip=True)
    return "N/A"

# --- BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\n\nEnter Registration Number to login:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    msg = await update.message.reply_text(f"⏳ Synchronizing with Portal for `{reg}`...")
    soup = await get_portal_soup(reg)
    await msg.delete()

    if not soup:
        return await update.message.reply_text("❌ Portal Unreachable. The college server is not responding.")

    # Extracting details using multiple keyword attempts
    name = extract_smart(soup, ["Student Name", "Name"])
    htc = extract_smart(soup, ["H.T.No", "Hall Ticket"])
    campus = extract_smart(soup, ["Campus", "College"])
    year = extract_smart(soup, ["Year", "Batch"])
    
    # Validation
    if name == "N/A" and htc == "N/A":
        return await update.message.reply_text(
            f"❌ *ID Not Found:* `{reg}`\n\nPossible reasons:\n"
            "• Registration ID is invalid.\n"
            "• Portal structure has changed.\n"
            "• Server is blocking the bot."
        )

    profile_text = (
        f"👤 *STUDENT PROFILE*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📛 *NAME:* `{name}`\n"
        f"🆔 *HTC NO:* `{htc}`\n"
        f"🏫 *CAMPUS:* `{campus}`\n"
        f"📅 *YEAR:* `{year}`\n"
    )

    result_link = SIS_URL.format(id=b64_encode(reg))
    keyboard = [
        [InlineKeyboardButton("📊 Attendance", callback_data="att"),
         InlineKeyboardButton("💰 Fee Ledger", callback_data="fee")],
        [InlineKeyboardButton("🔗 Open Full Results", url=result_link)]
    ]

    await update.message.reply_text(
        profile_text, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    reg = context.user_data.get("reg")
    await query.answer()

    if not reg:
        return await query.message.reply_text("❌ Session expired. Re-enter ID.")

    soup = await get_portal_soup(reg)
    if not soup:
        return await context.bot.send_message(query.message.chat_id, "❌ Portal Offline.")

    if query.data == "att":
        val = extract_smart(soup, ["Attendance", "Total Attendance"])
        await context.bot.send_message(
            query.message.chat_id, 
            f"📈 *Attendance for* `{reg}`: `{val if '%' in val else val+'%'}`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "fee":
        await context.bot.send_message(
            query.message.chat_id, 
            f"💰 *Fee Status for* `{reg}`: Please use the Browser Link for the detailed ledger.",
            parse_mode=ParseMode.MARKDOWN
        )

# --- EXECUTION ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Delete old webhooks to clear 'Conflict' errors
    asyncio.get_event_loop().run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("GHOST_ENGINE_V16_ONLINE_24/7")
    app.run_polling()
