import os
import sys
import logging
import asyncio
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory
import re

# Set seed for consistent language detection
DetectorFactory.seed = 0

# ========== CONFIGURATION ==========
# Get bot token from environment variable (Railway will set this)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    print("❌ ERROR: TELEGRAM_TOKEN environment variable not set!")
    print("Please set it in Railway dashboard: Variables tab")
    sys.exit(1)

# Set up logging for Railway
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)  # Railway captures stdout
    ]
)
logger = logging.getLogger(__name__)

# ========== SUPPORTED LANGUAGES ==========
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-cn": "Chinese (Simplified)",
    "ar": "Arabic",
    "hi": "Hindi",
    "bn": "Bengali",
    "ur": "Urdu",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "tr": "Turkish",
    "nl": "Dutch",
    "pl": "Polish",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "el": "Greek",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ms": "Malay",
    "tl": "Tagalog",
}

# ========== USER PREFERENCES ==========
# In production, use Redis/PostgreSQL. For demo, we use in-memory dict
# Railway can add Redis easily via plugins
user_preferences: Dict[int, str] = {}

# ========== COMMAND HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message when /start is issued."""
    user = update.effective_user
    welcome_text = f"""
🌟 *Welcome to Language Translator Bot, {user.first_name}!* 🌟

I can translate text between 30+ languages instantly!

📝 *How to use:*
• Send me any text → I'll translate it to your default language
• Use /setlang → Choose your target language (default: English)
• Use format: `text -> language` → Quick translation to any language

🌍 *Examples:*
• Send: "Hello world" → Translates to English
• Send: "Bonjour -> English" → Translates to English
• Send: "Good morning -> Spanish" → Translates to Spanish

📚 *Commands:*
/start - Show this message
/help - Detailed help guide
/about - Bot information
/setlang - Change your target language
/languages - List all supported languages

*Let's start translating!* 🚀
    """
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send detailed help message."""
    help_text = """
📚 *Language Translator Bot - Help Guide*

*Basic Usage:*
📝 Send any text → Auto-translates to your default language
🔧 Use /setlang to change your default language

*Advanced Usage - Quick Translate:*
Format: `[text] -> [language]`

Examples:
• `Hello -> Spanish` → Translates "Hello" to Spanish
• `Bonjour -> English` → Translates "Bonjour" to English
• `Guten Morgen -> French` → Translates to French

*Features:*
✅ Auto-detects source language
✅ 30+ languages supported
✅ Saves your language preference
✅ Quick inline translation
✅ No character limits (Google Translate handles it)

*Commands:*
/start - Welcome message
/help - This help guide
/about - Bot information
/setlang - Choose target language
/languages - See all supported languages

*Need help?* Just ask! I'm here to translate anything you need. 🌐
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send bot information."""
    about_text = """
🤖 *About Language Translator Bot*

*Version:* 1.0.0
*Created:* July 2026

*Powered by:*
• Google Translate API (via deep-translator)
• Python-Telegram-Bot v20
• Deployed on Railway

*Features:*
• Translate between 30+ languages
• Auto-detect source language
• User language preferences
• Inline translation with custom format
• Fast and reliable

*Source Code:*
GitHub: https://github.com/yourusername/telegram-translator-bot

*About Developer:*
Built for the @Languagetranslator08Bot project

🌟 *Made with ❤️ for the Telegram community*
    """
    await update.message.reply_text(about_text, parse_mode="Markdown")

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all supported languages."""
    # Group languages into columns for better display
    lang_list = sorted(LANGUAGES.items())
    lines = []
    for code, name in lang_list:
        lines.append(f"• {name} (`{code}`)")
    
    # Split into chunks of 15 languages per message
    chunk_size = 15
    for i in range(0, len(lines), chunk_size):
        chunk = lines[i:i+chunk_size]
        text = "🌐 *Supported Languages:*\n\n" + "\n".join(chunk)
        if i + chunk_size < len(lines):
            text += "\n\n_Continued..._"
        await update.message.reply_text(text, parse_mode="Markdown")

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show language selection keyboard."""
    keyboard = []
    # Create keyboard in rows of 3
    lang_list = list(LANGUAGES.items())
    for i in range(0, len(lang_list), 3):
        row = []
        for j in range(i, min(i + 3, len(lang_list))):
            code, name = lang_list[j]
            row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
        keyboard.append(row)
    
    # Add a Cancel button
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌐 *Choose your default translation language:*\n\n"
        "All your messages will be translated to this language.",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "cancel":
        await query.edit_message_text("❌ Language selection cancelled.")
        return
    
    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        lang_name = LANGUAGES.get(lang_code, lang_code)
        
        # Save user preference
        user_preferences[user_id] = lang_code
        logger.info(f"User {user_id} set language to {lang_code}")
        
        await query.edit_message_text(
            f"✅ *Language updated successfully!*\n\n"
            f"I'll now translate all your messages to *{lang_name}*.\n\n"
            f"Send me any text to try it out! 🚀",
            parse_mode="Markdown",
        )

async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Translate the received text message."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Ignore if text is empty
    if not text:
        return
    
    logger.info(f"Translating text from user {user_id}: {text[:50]}...")
    
    try:
        # Check for custom format: "text -> language"
        translation_pattern = r"^(.*?)\s*->\s*([a-zA-Z\s\-]+)$"
        match = re.match(translation_pattern, text, re.IGNORECASE)
        
        if match:
            # ===== CUSTOM TRANSLATION FORMAT =====
            source_text = match.group(1).strip()
            target_lang_name = match.group(2).strip().lower()
            
            # Find language code from name
            target_lang_code = None
            for code, name in LANGUAGES.items():
                if target_lang_name in name.lower() or target_lang_name in code.lower():
                    target_lang_code = code
                    break
            
            if not target_lang_code:
                await update.message.reply_text(
                    f"❌ Language '{target_lang_name}' not supported.\n"
                    f"Use /languages to see all available languages.\n"
                    f"Or use /setlang to set a default language."
                )
                return
            
            # Detect source language
            try:
                source_lang = detect(source_text)
                source_lang_name = LANGUAGES.get(source_lang, "Unknown")
            except:
                source_lang = "auto"
                source_lang_name = "Unknown"
            
            # Translate
            translator = GoogleTranslator(source=source_lang, target=target_lang_code)
            translated = translator.translate(source_text)
            
            await update.message.reply_text(
                f"📝 *Original ({source_lang_name}):*\n{source_text}\n\n"
                f"🌐 *Translated ({LANGUAGES[target_lang_code]}):*\n{translated}",
                parse_mode="Markdown",
            )
            
        else:
            # ===== NORMAL TRANSLATION =====
            target_lang = user_preferences.get(user_id, "en")
            target_lang_name = LANGUAGES.get(target_lang, "English")
            
            # Detect source language
            try:
                source_lang = detect(text)
                source_lang_name = LANGUAGES.get(source_lang, "Unknown")
            except:
                source_lang = "auto"
                source_lang_name = "Unknown"
            
            # Translate
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated = translator.translate(text)
            
            # If source and target are the same, inform the user
            if source_lang == target_lang:
                await update.message.reply_text(
                    f"📝 *Text is already in {target_lang_name}:*\n{text}\n\n"
                    f"💡 To translate to a different language, use:\n"
                    f"`{text} -> Spanish`\n\n"
                    f"Or use /setlang to change your default language.",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text(
                    f"📝 *Original ({source_lang_name}):*\n{text}\n\n"
                    f"🌐 *Translated ({target_lang_name}):*\n{translated}\n\n"
                    f"💡 Use /setlang to change your default language.",
                    parse_mode="Markdown",
                )
            
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text(
            "❌ *Oops! Something went wrong.*\n\n"
            "I couldn't translate that text. Possible reasons:\n"
            "• Text might be too long\n"
            "• Unsupported language detected\n"
            "• Service temporary unavailable\n\n"
            "Try again with a shorter text or different format.\n"
            "Use /help for guidance.",
            parse_mode="Markdown",
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and notify user."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send error message to user
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ *An error occurred.*\n\n"
            "Please try again later. If the problem persists, "
            "contact the developer.",
            parse_mode="Markdown",
        )

# ========== MAIN FUNCTION ==========
def main() -> None:
    """Start the bot."""
    logger.info("🚀 Starting Language Translator Bot...")
    logger.info(f"Bot Token: {TOKEN[:10]}... (hidden for security)")
    
    try:
        # Create application
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Application created successfully")
        
        # ===== ADD HANDLERS =====
        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("about", about))
        application.add_handler(CommandHandler("setlang", set_language))
        application.add_handler(CommandHandler("languages", languages_command))
        
        # Callback query handler for inline keyboard
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Message handler for text messages (excluding commands)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text)
        )
        
        # Error handler
        application.add_error_handler(error_handler)
        
        logger.info("✅ All handlers registered")
        
        # ===== START POLLING =====
        logger.info("🔄 Starting polling...")
        logger.info("✅ Bot is now running and ready to receive messages!")
        logger.info(f"👉 Find your bot at: https://t.me/Languagetranslator08Bot")
        
        # Start polling with allowed updates
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
