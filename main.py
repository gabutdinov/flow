#!/usr/bin/env python3
"""
English Speaking Practice Bot

A Telegram bot that helps users practice English through voice conversations
using OpenAI's Whisper (STT), GPT-4 (conversation), and TTS API.
"""

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import config
from database import init_db
from handlers.commands import (
    start_command,
    new_command,
    topic_command,
    level_command,
    stats_command,
    help_command
)
from handlers.voice import handle_voice_message, show_transcription_callback
from handlers.text import handle_text_message

# Configure logging
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot"""
    logger.info("Starting English Speaking Bot...")

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Create application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("new", new_command))
    application.add_handler(CommandHandler("topic", topic_command))
    application.add_handler(CommandHandler("level", level_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))

    # Register message handlers
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Register callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(show_transcription_callback))

    # Start bot
    logger.info("Bot is starting...")
    logger.info("Press Ctrl+C to stop")

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
