import logging
import json
from typing import List, Dict
from openai import OpenAI
import config

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=config.OPENAI_API_KEY)


async def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribe audio file to text using Whisper API

    Args:
        audio_file_path: Path to the audio file

    Returns:
        Transcribed text
    """
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=config.WHISPER_MODEL,
                file=audio_file
            )
        logger.info(f"Audio transcribed successfully: {transcript.text[:50]}...")
        return transcript.text
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise


async def generate_response(messages: List[Dict[str, str]], system_prompt: str) -> str:
    """
    Generate text response using GPT-4

    Args:
        messages: List of conversation messages in OpenAI format
        system_prompt: System prompt for the model

    Returns:
        Generated response text
    """
    try:
        response = client.chat.completions.create(
            model=config.GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *messages
            ],
            temperature=0.8,
            max_tokens=200  # Keep responses concise
        )
        response_text = response.choices[0].message.content
        logger.info(f"Generated response: {response_text[:50]}...")
        return response_text
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise


async def analyze_user_message(user_text: str, level: str, analysis_prompt: str) -> Dict:
    """
    Analyze user's message for grammar, alternative expressions, and vocabulary

    Args:
        user_text: User's transcribed message
        level: User's English level (A1-C2)
        analysis_prompt: System prompt for analysis

    Returns:
        Dictionary with analysis data (quality, corrected_sentence, short_analysis, full_analysis)
    """
    try:
        response = client.chat.completions.create(
            model=config.GPT_MODEL,
            messages=[
                {"role": "system", "content": analysis_prompt},
                {"role": "user", "content": f"Analyze this message from a {level} level student:\n\n{user_text}"}
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        analysis_text = response.choices[0].message.content
        logger.info(f"Generated analysis: {analysis_text[:100]}...")

        # Parse JSON response
        try:
            analysis_data = json.loads(analysis_text)
            return analysis_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON analysis: {e}")
            # Fallback response
            return {
                "language": "en",
                "detected_language": "",
                "quality": "good",
                "original_text": user_text,
                "corrected_sentence": user_text,
                "short_analysis": "Анализ недоступен",
                "full_analysis": "Не удалось проанализировать сообщение"
            }
    except Exception as e:
        logger.error(f"Error generating analysis: {e}")
        raise


async def text_to_speech(text: str, output_path: str) -> str:
    """
    Convert text to speech using OpenAI TTS API

    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file

    Returns:
        Path to the generated audio file
    """
    try:
        response = client.audio.speech.create(
            model=config.TTS_MODEL,
            voice=config.TTS_VOICE,
            input=text,
            response_format="mp3"
        )

        # Save the audio file
        response.stream_to_file(output_path)
        logger.info(f"TTS audio saved to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        raise
