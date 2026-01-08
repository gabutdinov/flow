import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import get_or_create_user, get_db, User
from services.conversation_service import ConversationService
from services.stats_service import StatsService
from prompts.system_prompt import (
    get_welcome_message,
    get_new_conversation_message,
    get_help_message
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    telegram_id = update.effective_user.id
    user = get_or_create_user(telegram_id)

    welcome_msg = get_welcome_message()
    await update.message.reply_text(welcome_msg)

    logger.info(f"User {telegram_id} started the bot")


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new command - start a new conversation"""
    telegram_id = update.effective_user.id
    user = get_or_create_user(telegram_id)

    # Start a new conversation
    ConversationService.start_new_conversation(user)

    new_conv_msg = get_new_conversation_message()
    await update.message.reply_text(new_conv_msg)

    logger.info(f"User {telegram_id} started a new conversation")


async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /topic command - set conversation topic"""
    telegram_id = update.effective_user.id
    user = get_or_create_user(telegram_id)

    # Get topic from command arguments
    if context.args:
        topic = " ".join(context.args)

        # Get or create active conversation and set topic
        conversation = ConversationService.get_or_create_active_conversation(user, topic)
        ConversationService.set_conversation_topic(conversation, topic)

        await update.message.reply_text(
            f"Great! Let's talk about {topic}. Send me a voice message to start the conversation!"
        )
        logger.info(f"User {telegram_id} set topic to: {topic}")
    else:
        await update.message.reply_text(
            "Please specify a topic. For example: /topic travel"
        )


async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /level command - set user's English level"""
    telegram_id = update.effective_user.id

    # Get level from command arguments
    if context.args:
        level = context.args[0].upper()
        valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]

        if level in valid_levels:
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if user:
                    user.level = level
                    db.commit()

                    await update.message.reply_text(
                        f"Your English level has been set to {level}. "
                        f"I'll adapt my responses accordingly!"
                    )
                    logger.info(f"User {telegram_id} set level to: {level}")
        else:
            await update.message.reply_text(
                f"Invalid level. Please use one of: {', '.join(valid_levels)}\n"
                f"Example: /level B2"
            )
    else:
        await update.message.reply_text(
            "Please specify your level (A1-C2). For example: /level B1"
        )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command - show user statistics"""
    telegram_id = update.effective_user.id
    user = get_or_create_user(telegram_id)

    stats = StatsService.get_user_stats(user)
    stats_message = StatsService.format_stats_message(stats, user.level)

    await update.message.reply_text(stats_message)
    logger.info(f"User {telegram_id} viewed stats")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_msg = get_help_message()
    await update.message.reply_text(help_msg)

    logger.info(f"User {update.effective_user.id} requested help")
