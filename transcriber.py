from pathlib import Path

from groq import Groq

from config import GROQ_API_KEY, MAX_AUDIO_SIZE_MB, require_env


def _validate_audio_file(file_path: str) -> None:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    max_bytes = MAX_AUDIO_SIZE_MB * 1024 * 1024
    if path.stat().st_size > max_bytes:
        raise ValueError(f"Audio file is larger than {MAX_AUDIO_SIZE_MB} MB")


def transcribe_audio(file_path: str) -> str:
    _validate_audio_file(file_path)
    client = Groq(api_key=require_env("GROQ_API_KEY", GROQ_API_KEY))

    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file,
            language="te",
            response_format="text",
        )

    return str(transcription).strip()
