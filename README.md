# English Speaking Practice Bot

A Telegram bot that helps you practice English through natural voice conversations. The bot uses OpenAI's Whisper for speech-to-text, GPT-4 for intelligent conversation, and OpenAI TTS for text-to-speech.

## Features

- Voice conversation practice in English
- Adaptive responses based on your English level (A1-C2)
- Topic-based conversations
- Conversation history and context management
- Learning statistics tracking (messages, active days, streak)
- Natural, friendly teaching style

## Technology Stack

- Python 3.11+
- python-telegram-bot (Telegram Bot API)
- OpenAI API (Whisper, GPT-4, TTS)
- SQLAlchemy + SQLite (database)
- python-dotenv (configuration)

## Project Structure

```
EnglishSpeakingBot/
├── main.py                 # Entry point
├── config.py               # Configuration
├── handlers/
│   ├── commands.py         # Command handlers
│   └── voice.py            # Voice message handler
├── services/
│   ├── openai_service.py   # OpenAI API integration
│   ├── conversation_service.py  # Conversation management
│   └── stats_service.py    # Statistics tracking
├── database/
│   ├── models.py           # Database models
│   ├── db.py               # Database initialization
│   └── __init__.py
├── prompts/
│   └── system_prompt.py    # GPT-4 system prompts
├── requirements.txt
├── .env.example
└── README.md
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11 or higher
- Telegram account
- OpenAI API key

### 2. Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Save the bot token you receive

### 3. Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com)
2. Sign up or log in
3. Navigate to API keys section
4. Create a new API key and save it

### 4. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env file and add your tokens
# TELEGRAM_BOT_TOKEN=your_bot_token_here
# OPENAI_API_KEY=your_openai_key_here
```

### 6. Run the Bot

```bash
# Make sure virtual environment is activated
python main.py
```

You should see:
```
Starting English Speaking Bot...
Initializing database...
Database initialized successfully
Bot is starting...
Press Ctrl+C to stop
```

### 7. Run with Docker

```bash
# Build image
docker build -t english-speaking-bot .

# Run container (expects .env next to docker-compose.yml)
docker compose up -d

# View logs
docker compose logs -f
```

Volumes:
- `./bot.db` → `/app/bot.db` (SQLite data)
- `./temp_audio` → `/app/temp_audio` (temporary audio files)

## Usage

### Commands

- `/start` - Start the bot and get welcome message
- `/new` - Start a new conversation (clear context)
- `/topic [topic]` - Set conversation topic (e.g., `/topic travel`)
- `/level [A1-C2]` - Set your English level (e.g., `/level B2`)
- `/stats` - View your learning statistics
- `/help` - Show help message

### How to Use

1. Start the bot with `/start`
2. Optionally set your level with `/level` (default is B1)
3. Optionally set a topic with `/topic`
4. Send a voice message in English
5. The bot will:
   - Transcribe your message
   - Generate a contextual response
   - Send back a voice message with the response
   - Also send the text version for reference

## Database

The bot uses SQLite database (`bot.db`) with the following tables:

- `users` - User information and English level
- `conversations` - Conversation sessions
- `messages` - Individual messages (user and assistant)
- `user_stats` - Learning statistics

## Configuration

Key configuration options in `config.py`:

- `GPT_MODEL` - GPT model to use (default: gpt-4o)
- `WHISPER_MODEL` - Whisper model (default: whisper-1)
- `TTS_VOICE` - TTS voice (default: alloy)
- `MAX_CONTEXT_MESSAGES` - Number of messages in context (default: 10)
- `DEFAULT_USER_LEVEL` - Default English level (default: B1)

## Development

### Adding New Features

1. Create new handlers in `handlers/` directory
2. Create new services in `services/` directory
3. Register handlers in `main.py`
4. Update database models in `database/models.py` if needed

### Logging

The bot logs to console with configurable log level (set `LOG_LEVEL` in `.env`):
- `DEBUG` - Detailed information
- `INFO` - General information (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages

## Troubleshooting

### Bot doesn't respond to voice messages

- Check that OpenAI API key is valid and has credits
- Check internet connection
- Look at console logs for errors

### Database errors

- Delete `bot.db` file and restart the bot
- Check file permissions

### Voice messages not being transcribed

- Ensure the audio file is in a supported format
- Check OpenAI API status
- Verify Whisper API access

## Future Enhancements

- Progress tracking and analysis
- Error correction feedback
- Personalized exercises
- Vocabulary building
- Anki integration
- Web dashboard

## License

This project is for educational purposes.

## Support

For issues and questions, please check the logs and configuration first.

## Credits

Built with:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [OpenAI API](https://platform.openai.com)
- [SQLAlchemy](https://www.sqlalchemy.org)
