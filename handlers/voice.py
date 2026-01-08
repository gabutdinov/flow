import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from database import get_or_create_user
from services.conversation_service import ConversationService
from services.stats_service import StatsService
from services.openai_service import transcribe_audio, generate_response, text_to_speech, analyze_user_message
from prompts.system_prompt import get_system_prompt, get_analysis_prompt

logger = logging.getLogger(__name__)

# Create temp directory for audio files if it doesn't exist
TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming voice messages

    Process flow:
    1. Download voice message
    2. Transcribe using Whisper
    3. Get conversation context
    4. Generate response using GPT-4
    5. Convert response to speech using TTS
    6. Send voice and text response
    7. Save to database
    """
    telegram_id = update.effective_user.id
    user = get_or_create_user(telegram_id)

    try:
        # Send typing indicator
        await update.message.chat.send_action("typing")

        # Download voice message
        voice_file = await update.message.voice.get_file()
        voice_path = os.path.join(TEMP_DIR, f"voice_{telegram_id}_{update.message.message_id}.ogg")
        await voice_file.download_to_drive(voice_path)
        logger.info(f"Downloaded voice message from user {telegram_id}")

        # Transcribe audio to text
        await update.message.chat.send_action("typing")
        user_text = await transcribe_audio(voice_path)
        logger.info(f"Transcribed: {user_text}")

        # Analyze user's message and send feedback
        await update.message.chat.send_action("typing")
        analysis_prompt = get_analysis_prompt(level=user.level)
        analysis_data = await analyze_user_message(user_text, user.level, analysis_prompt)

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
            audio_file_id=update.message.voice.file_id
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

        # Convert response to speech
        await update.message.chat.send_action("record_voice")
        tts_path = os.path.join(TEMP_DIR, f"tts_{telegram_id}_{update.message.message_id}.mp3")
        await text_to_speech(response_text, tts_path)

        # Try to send voice message, fallback to text if forbidden
        audio_file_id = None
        voice_forbidden = False
        try:
            # Create inline keyboard with "Show text" button
            keyboard = [[InlineKeyboardButton("📝 Показать текст", callback_data=f"show_text")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send voice message without caption
            with open(tts_path, "rb") as audio_file:
                voice_message = await update.message.reply_voice(
                    voice=audio_file,
                    reply_markup=reply_markup
                )
                audio_file_id = voice_message.voice.file_id

            # Store the transcription text for later retrieval
            message_key = f"{voice_message.chat.id}_{voice_message.message_id}"
            if 'transcriptions' not in context.bot_data:
                context.bot_data['transcriptions'] = {}
            context.bot_data['transcriptions'][message_key] = response_text
            logger.info(f"Stored transcription for message {message_key}")

        except BadRequest as e:
            if "Voice_messages_forbidden" in str(e):
                # User has disabled voice messages in privacy settings
                voice_forbidden = True

                # Create inline keyboard with "Try again" button
                keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data="retry_voice")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                error_message = await update.message.reply_text(
                    f"{response_text}\n\n"
                    "⚠️ Я не могу отправить голосовое сообщение, так как у вас отключена "
                    "возможность их получения.\n\n"
                    "Чтобы включить голосовые сообщения:\n"
                    "1. Откройте Настройки Telegram\n"
                    "2. Конфиденциальность → Голосовые сообщения\n"
                    "3. Выберите 'Все' или добавьте Flow в 'Разрешать всегда'\n\n"
                    "Пока что я буду отвечать только текстом.",
                    reply_markup=reply_markup
                )

                # Store response text and audio path for retry
                message_key = f"{error_message.chat.id}_{error_message.message_id}"
                if 'retry_voice_data' not in context.bot_data:
                    context.bot_data['retry_voice_data'] = {}
                context.bot_data['retry_voice_data'][message_key] = {
                    'response_text': response_text,
                    'tts_path': tts_path,
                    'user_message_id': update.message.message_id
                }
                logger.warning(f"Voice messages forbidden for user {telegram_id}")
            else:
                # Re-raise if it's a different error
                raise

        # Add assistant message to database
        ConversationService.add_message(
            conversation=conversation,
            role="assistant",
            text_content=response_text,
            audio_file_id=audio_file_id
        )

        # Update user statistics
        StatsService.update_user_activity(user)

        # Clean up temp files
        try:
            os.remove(voice_path)
            # Don't delete tts_path if voice messages are forbidden (needed for retry)
            if not voice_forbidden:
                os.remove(tts_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {e}")

        logger.info(f"Successfully processed voice message from user {telegram_id}")

    except Exception as e:
        logger.error(f"Error processing voice message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error processing your voice message. "
            "Please try again or contact support if the problem persists."
        )

        # Clean up temp files in case of error
        try:
            if os.path.exists(voice_path):
                os.remove(voice_path)
            if os.path.exists(tts_path):
                os.remove(tts_path)
        except:
            pass


async def show_transcription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries for inline buttons
    - show_text/hide_text: Toggle voice message transcription
    - full_analysis/hide_full_analysis: Toggle full analysis details
    """
    query = update.callback_query
    await query.answer()

    # Get the message key
    message_key = f"{query.message.chat.id}_{query.message.message_id}"

    # Handle voice transcription toggle
    if query.data == "show_text":
        # Get the transcription text
        transcriptions = context.bot_data.get('transcriptions', {})
        transcription_text = transcriptions.get(message_key)

        if transcription_text:
            # Update button to "Hide text"
            keyboard = [[InlineKeyboardButton("🔽 Скрыть текст", callback_data="hide_text")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Edit message to add caption
            try:
                await query.edit_message_caption(
                    caption=transcription_text,
                    reply_markup=reply_markup
                )
                logger.info(f"Showed transcription for message {message_key}")
            except Exception as e:
                logger.error(f"Error editing message caption: {e}")
                await query.answer("Ошибка при показе текста", show_alert=True)
        else:
            await query.answer("Текст не найден", show_alert=True)
            logger.warning(f"Transcription not found for message {message_key}")

    elif query.data == "hide_text":
        # Update button back to "Show text"
        keyboard = [[InlineKeyboardButton("📝 Показать текст", callback_data="show_text")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Edit message to remove caption
        try:
            await query.edit_message_caption(
                caption=None,
                reply_markup=reply_markup
            )
            logger.info(f"Hid transcription for message {message_key}")
        except Exception as e:
            logger.error(f"Error editing message caption: {e}")
            await query.answer("Ошибка при скрытии текста", show_alert=True)

    # Handle full analysis toggle
    elif query.data == "full_analysis":
        # Get the full analysis text
        full_analyses = context.bot_data.get('full_analyses', {})
        full_analysis_text = full_analyses.get(message_key)

        if full_analysis_text:
            # Get current message text (short analysis)
            current_text = query.message.text or query.message.caption or ""

            # Update button to "Hide full analysis"
            keyboard = [[InlineKeyboardButton("🔼 Скрыть детали", callback_data="hide_full_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Combine short and full analysis
            full_message = f"{current_text}\n\n━━━━━━━━━━━━━━━\n\n{full_analysis_text}"

            # Edit message to show full analysis
            try:
                await query.edit_message_text(
                    text=full_message,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                logger.info(f"Showed full analysis for message {message_key}")

                # Store short text for later
                if 'short_analyses' not in context.bot_data:
                    context.bot_data['short_analyses'] = {}
                context.bot_data['short_analyses'][message_key] = current_text

            except Exception as e:
                logger.error(f"Error editing message text: {e}")
                await query.answer("Ошибка при показе полного разбора", show_alert=True)
        else:
            await query.answer("Полный разбор не найден", show_alert=True)
            logger.warning(f"Full analysis not found for message {message_key}")

    elif query.data == "hide_full_analysis":
        # Get the short analysis text
        short_analyses = context.bot_data.get('short_analyses', {})
        short_text = short_analyses.get(message_key)

        if short_text:
            # Update button back to "Full analysis"
            keyboard = [[InlineKeyboardButton("📖 Полный разбор", callback_data="full_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Edit message to show only short analysis
            try:
                await query.edit_message_text(
                    text=short_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                logger.info(f"Hid full analysis for message {message_key}")
            except Exception as e:
                logger.error(f"Error editing message text: {e}")
                await query.answer("Ошибка при скрытии полного разбора", show_alert=True)
        else:
            await query.answer("Ошибка", show_alert=True)
            logger.warning(f"Short analysis not found for message {message_key}")

    # Handle retry voice message
    elif query.data == "retry_voice":
        retry_voice_data_dict = context.bot_data.get('retry_voice_data', {})
        retry_data = retry_voice_data_dict.get(message_key)

        if retry_data:
            response_text = retry_data['response_text']
            tts_path = retry_data['tts_path']

            # Try to send voice message again
            try:
                # Create inline keyboard with "Show text" button
                keyboard = [[InlineKeyboardButton("📝 Показать текст", callback_data=f"show_text")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Send voice message without caption
                with open(tts_path, "rb") as audio_file:
                    voice_message = await query.message.reply_voice(
                        voice=audio_file,
                        reply_markup=reply_markup
                    )

                # Store the transcription text for later retrieval
                voice_message_key = f"{voice_message.chat.id}_{voice_message.message_id}"
                if 'transcriptions' not in context.bot_data:
                    context.bot_data['transcriptions'] = {}
                context.bot_data['transcriptions'][voice_message_key] = response_text
                logger.info(f"Stored transcription for message {voice_message_key}")

                # Delete the error message
                await query.message.delete()

                # Clean up retry data
                del retry_voice_data_dict[message_key]

                # Clean up temp audio file
                try:
                    if os.path.exists(tts_path):
                        os.remove(tts_path)
                        logger.info(f"Cleaned up temp file: {tts_path}")
                except Exception as e:
                    logger.warning(f"Error cleaning up temp file {tts_path}: {e}")

                await query.answer("✅ Голосовое сообщение отправлено!", show_alert=False)
                logger.info(f"Successfully retried voice message for {message_key}")

            except BadRequest as e:
                if "Voice_messages_forbidden" in str(e):
                    await query.answer(
                        "❌ Голосовые сообщения все еще отключены. "
                        "Пожалуйста, проверьте настройки Telegram.",
                        show_alert=True
                    )
                    logger.warning(f"Voice messages still forbidden on retry for {message_key}")
                else:
                    await query.answer("Ошибка при отправке голосового сообщения", show_alert=True)
                    logger.error(f"Error retrying voice message: {e}")
        else:
            await query.answer("Данные для повтора не найдены", show_alert=True)
            logger.warning(f"Retry data not found for message {message_key}")
