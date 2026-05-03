import shutil
import subprocess
from pathlib import Path


def split_audio(
    input_path: str,
    output_dir: str,
    *,
    chunk_seconds: int,
) -> list[str]:
    if chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be greater than 0")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for audio chunking but was not found")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    chunk_pattern = output_path / "chunk_%03d.mp3"

    command = [
        ffmpeg,
        "-y",
        "-i",
        input_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "segment",
        "-segment_time",
        str(chunk_seconds),
        "-reset_timestamps",
        "1",
        str(chunk_pattern),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to split audio: {result.stderr.strip()}")

    chunks = sorted(str(path) for path in output_path.glob("chunk_*.mp3"))
    if not chunks:
        raise RuntimeError("ffmpeg did not create any audio chunks")

    return chunks
