import base64
import asyncio
import http.server
import socketserver
import threading
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
)

# --- 24/7 HEARTBEAT ---
def run_heartbeat():
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"GHOST_ENGINE_ONLINE")
    with socketserver.TCPServer(("", 8080), HealthCheckHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_heartbeat, daemon=True).start()

# --- CONFIG ---
TOKEN = "8491426723:AAECUa6FEZbRy1ZKsJ7FWGA43QO3xIw5cHE"
SIS_URL = "http://115.241.194.20/sis/Examination/Reports/StudentSearchHTMLReport_student.aspx?R={id}&T=-8584723613578166740"

def b64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

# --- BACKGROUND SCREENSHOT ENGINE ---
async def capture_profile_screenshot(reg):
    url = SIS_URL.format(id=b64_encode(reg))
    async with async_playwright() as p:
        # Launching headless browser (invisible)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        try:
            # Navigate to the portal
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Locate the specific profile table or container (Adjust selector if needed)
            # This captures the top part of the page where the profile usually sits
            screenshot_path = f"profile_{reg}.png"
            await page.screenshot(path=screenshot_path, clip={"x": 0, "y": 0, "width": 1000, "height": 600})
            
            await browser.close()
            return screenshot_path
        except Exception as e:
            print(f"Screenshot Error: {e}")
            await browser.close()
            return None

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛰️ *NECRACK GHOST v16*\nEnter Registration ID to view Profile Screenshot:")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reg = update.message.text.strip().upper()
    context.user_data["reg"] = reg
    
    status_msg = await update.message.reply_text("📸 Capturing profile screenshot in background... Please wait.")
    
    # Take screenshot
    photo_path = await capture_profile_screenshot(reg)
    await status_msg.delete()

    result_link = SIS_URL.format(id=b64_encode(reg))
    keyboard = [[InlineKeyboardButton("🔗 Open Result Page", url=result_link)]]

    if photo_path:
        with open(photo_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"👤 *PROFILE DATA:* `{reg}`",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text("❌ Failed to capture screenshot. Portal might be down.")

# --- RUN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    asyncio.get_event_loop().run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    
    print("GHOST_ENGINE_V16_ONLINE_SCREENSHOT_ENABLED")
    app.run_polling()
