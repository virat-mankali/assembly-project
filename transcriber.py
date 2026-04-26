from pathlib import Path

from groq import Groq

from config import GROQ_API_KEY, MAX_AUDIO_SIZE_MB, require_env

SUPPORTED_AUDIO_SUFFIXES = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".opus", ".wav", ".webm"}
AUDIO_CONTENT_TYPES = {
    ".flac": "audio/flac",
    ".mp3": "audio/mpeg",
    ".mp4": "audio/mp4",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
}


def _validate_audio_file(file_path: str) -> None:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    max_bytes = MAX_AUDIO_SIZE_MB * 1024 * 1024
    if path.stat().st_size > max_bytes:
        raise ValueError(f"Audio file is larger than {MAX_AUDIO_SIZE_MB} MB")


def _audio_upload_metadata(file_path: str) -> tuple[str, str]:
    suffix = Path(file_path).suffix.lower()
    if suffix not in SUPPORTED_AUDIO_SUFFIXES:
        suffix = ".mp3"

    return f"assembly_audio{suffix}", AUDIO_CONTENT_TYPES[suffix]


def transcribe_audio(file_path: str) -> str:
    _validate_audio_file(file_path)
    client = Groq(api_key=require_env("GROQ_API_KEY", GROQ_API_KEY))
    upload_filename, content_type = _audio_upload_metadata(file_path)

    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(upload_filename, audio_file, content_type),
            language="te",
            response_format="text",
        )

    return str(transcription).strip()
