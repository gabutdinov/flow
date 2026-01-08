import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in environment variables")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/bot.db")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL.upper())
)

# OpenAI model configuration
WHISPER_MODEL = "whisper-1"
GPT_MODEL = "gpt-4o"  # Using gpt-4o as it's more cost-effective
TTS_MODEL = "tts-1"
TTS_VOICE = "shimmer"  # Options: alloy, echo, fable, onyx, nova, shimmer

# Conversation configuration
MAX_CONTEXT_MESSAGES = 10  # Number of messages to keep in context
DEFAULT_USER_LEVEL = "B1"
