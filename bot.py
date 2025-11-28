import logging
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ==========================================
# SETUP LOGGING
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ==========================================
# GEMINI AI SETUP
# ==========================================
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    # Using the flash model for speed and efficiency
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    logging.error(f"Failed to configure Gemini AI: {e}")

# ==========================================
# BOT FUNCTIONS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command.
    """
    user_first_name = update.effective_user.first_name
    welcome_message = (
        f"Hello {user_first_name}! 👋\n\n"
        "I am a bot powered by Google's Gemini AI. "
        "Send me any message, and I'll do my best to answer it!\n\n"
        "Try asking: 'What is the capital of France?' or 'Write a short poem about coding.'"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /help command.
    """
    await update.message.reply_text(
        "Just send me a text message and I will reply using Gemini AI!\n"
        "Note: I currently process text-only messages."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles incoming text messages and sends them to Gemini.
    """
    user_text = update.message.text
    chat_id = update.effective_chat.id

    if not user_text:
        return

    # 1. Send "Typing..." action to show the bot is thinking
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        # 2. Generate content using Gemini
        # We run this in a separate thread/executor to avoid blocking the async event loop
        # providing a smoother experience if the API is slow.
        response = await asyncio.to_thread(model.generate_content, user_text)
        
        bot_response = response.text

        # 3. Telegram has a message limit of 4096 chars. 
        # If the response is too long, we might need to split it, but usually 
        # Gemini answers fit or we can let the library handle basic splitting 
        # or send it in chunks. For simplicity, we send standard text.
        # Markdown parsing can be tricky if Gemini sends broken syntax, 
        # so we default to plain text or basic HTML safe parsing if needed.
        
        await update.message.reply_text(bot_response)

    except Exception as e:
        logging.error(f"Error generating response: {e}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request. Please try again later."
        )

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found. Please check your .env file.")
        exit(1)
        
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY not found. Please check your .env file.")
        exit(1)

    print("Starting bot...")
    
    # Build the Telegram Application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Add Handlers
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help_command)
    
    # Filter for text messages that are not commands
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(message_handler)

    # Run the bot
    # polling() is the easiest method for local development
    application.run_polling()