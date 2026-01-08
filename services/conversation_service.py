import logging
from typing import List, Dict, Optional
from datetime import datetime
from database import get_db, User, Conversation, Message
import config

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation context and history"""

    @staticmethod
    def get_or_create_active_conversation(user: User, topic: Optional[str] = None) -> Conversation:
        """Get the active conversation or create a new one"""
        with get_db() as db:
            # Attach user to the session
            user = db.merge(user)

            # Get the most recent conversation
            active_conversation = (
                db.query(Conversation)
                .filter(Conversation.user_id == user.id)
                .order_by(Conversation.started_at.desc())
                .first()
            )

            # Create a new conversation if none exists or if topic changed
            if not active_conversation or (topic and active_conversation.topic != topic):
                active_conversation = Conversation(
                    user_id=user.id,
                    topic=topic
                )
                db.add(active_conversation)
                db.commit()
                db.refresh(active_conversation)
                logger.info(f"Created new conversation {active_conversation.id} for user {user.telegram_id}")

            # Load all attributes before session closes
            _ = active_conversation.id
            _ = active_conversation.user_id
            _ = active_conversation.topic
            _ = active_conversation.started_at

            # Detach from session
            db.expunge(active_conversation)

            return active_conversation

    @staticmethod
    def start_new_conversation(user: User, topic: Optional[str] = None) -> Conversation:
        """Start a new conversation (used when /new command is issued)"""
        with get_db() as db:
            user = db.merge(user)

            new_conversation = Conversation(
                user_id=user.id,
                topic=topic
            )
            db.add(new_conversation)
            db.commit()
            db.refresh(new_conversation)
            logger.info(f"Started new conversation {new_conversation.id} for user {user.telegram_id}")

            # Load all attributes before session closes
            _ = new_conversation.id
            _ = new_conversation.user_id
            _ = new_conversation.topic
            _ = new_conversation.started_at

            # Detach from session
            db.expunge(new_conversation)

            return new_conversation

    @staticmethod
    def add_message(conversation: Conversation, role: str, text_content: str,
                    audio_file_id: Optional[str] = None) -> Message:
        """Add a message to the conversation"""
        with get_db() as db:
            conversation = db.merge(conversation)

            message = Message(
                conversation_id=conversation.id,
                role=role,
                text_content=text_content,
                audio_file_id=audio_file_id
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            logger.info(f"Added {role} message to conversation {conversation.id}")

            # Load all attributes before session closes
            _ = message.id
            _ = message.conversation_id
            _ = message.role
            _ = message.text_content
            _ = message.audio_file_id
            _ = message.created_at

            # Detach from session
            db.expunge(message)

            return message

    @staticmethod
    def get_conversation_context(conversation: Conversation, limit: int = None) -> List[Dict[str, str]]:
        """
        Get recent messages for conversation context

        Args:
            conversation: Conversation object
            limit: Maximum number of messages to retrieve (default from config)

        Returns:
            List of messages in OpenAI format [{"role": "user", "content": "..."}]
        """
        if limit is None:
            limit = config.MAX_CONTEXT_MESSAGES

        with get_db() as db:
            conversation = db.merge(conversation)

            messages = (
                db.query(Message)
                .filter(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.desc())
                .limit(limit)
                .all()
            )

            # Reverse to get chronological order
            messages = list(reversed(messages))

            # Convert to OpenAI format
            context = [
                {"role": msg.role, "content": msg.text_content}
                for msg in messages
            ]

            logger.info(f"Retrieved {len(context)} messages for context")
            return context

    @staticmethod
    def set_conversation_topic(conversation: Conversation, topic: str) -> None:
        """Set or update conversation topic"""
        with get_db() as db:
            conversation = db.merge(conversation)
            conversation.topic = topic
            db.commit()
            logger.info(f"Set topic '{topic}' for conversation {conversation.id}")

    @staticmethod
    def get_conversation_topic(conversation: Conversation) -> Optional[str]:
        """Get current conversation topic"""
        with get_db() as db:
            conversation = db.merge(conversation)
            return conversation.topic
