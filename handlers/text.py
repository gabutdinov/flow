import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_or_create_user
from services.conversation_service import ConversationService
from services.stats_service import StatsService
from services.openai_service import generate_response, analyze_user_message
from prompts.system_prompt import get_system_prompt, get_analysis_prompt

logger = logging.getLogger(__name__)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming text messages

    Process flow:
    1. Get user's text message
    2. Analyze for language and errors
    3. Generate response using GPT-4
    4. Send text response
    5. Save to database
    """
    telegram_id = update.effective_user.id
    user = get_or_create_user(telegram_id)

    try:
        # Get user's text message
        user_text = update.message.text
        logger.info(f"Received text from user {telegram_id}: {user_text[:50]}...")

        # Analyze user's message and send feedback
        await update.message.chat.send_action("typing")
        analysis_prompt = get_analysis_prompt(level=user.level)
        analysis_data = await analyze_user_message(user_text, user.level, analysis_prompt)

        # Check if message is in English
        if analysis_data.get("language") != "en":
            detected_lang = analysis_data.get("detected_language", "неизвестном языке")
            error_message = (
                f"❌ Обнаружен {detected_lang}\n\n"
                f"Пожалуйста, отправьте сообщение <b>на английском языке</b>.\n\n"
                f"This bot is for practicing English. Please send your message in English."
            )
            await update.message.reply_text(error_message, parse_mode="HTML")
            logger.warning(f"User {telegram_id} sent text message in {detected_lang}")
            return

        # Format short analysis with quality indicator
        quality_emoji = {
            "perfect": "✅",
            "good": "💡",
            "needs_work": "❌"
        }
        emoji = quality_emoji.get(analysis_data.get("quality", "good"), "💡")
        corrected_sentence = analysis_data.get("corrected_sentence", user_text)
        short_analysis = analysis_data.get("short_analysis", "")

        # Create inline keyboard with "Full analysis" button
        keyboard = [[InlineKeyboardButton("📖 Полный разбор", callback_data="full_analysis")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send short analysis
        short_message = f"{emoji} {corrected_sentence}\n\n<i>{short_analysis}</i>"
        analysis_msg = await update.message.reply_text(
            short_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

        # Store full analysis for later retrieval
        analysis_key = f"{analysis_msg.chat.id}_{analysis_msg.message_id}"
        if 'full_analyses' not in context.bot_data:
            context.bot_data['full_analyses'] = {}
        context.bot_data['full_analyses'][analysis_key] = analysis_data.get("full_analysis", "Анализ недоступен")
        logger.info(f"Sent short analysis to user {telegram_id}")

        # Get or create active conversation
        conversation = ConversationService.get_or_create_active_conversation(user)

        # Add user message to database
        ConversationService.add_message(
            conversation=conversation,
            role="user",
            text_content=user_text,
            audio_file_id=None  # No audio for text messages
        )

        # Get conversation context
        context_messages = ConversationService.get_conversation_context(conversation)

        # Get system prompt based on user level and topic
        topic = ConversationService.get_conversation_topic(conversation)
        system_prompt = get_system_prompt(level=user.level, topic=topic)

        # Generate response using GPT-4
        await update.message.chat.send_action("typing")
        response_text = await generate_response(context_messages, system_prompt)
        logger.info(f"Generated response: {response_text}")

        # Send text response
        await update.message.reply_text(response_text)

        # Add assistant message to database
        ConversationService.add_message(
            conversation=conversation,
            role="assistant",
            text_content=response_text,
            audio_file_id=None  # No audio for text responses
        )

        # Update user statistics
        StatsService.update_user_activity(user)

        logger.info(f"Successfully processed text message from user {telegram_id}")

    except Exception as e:
        logger.error(f"Error processing text message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error processing your message. "
            "Please try again or contact support if the problem persists."
        )
