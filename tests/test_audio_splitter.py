import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from audio_splitter import split_audio


class AudioSplitterTests(unittest.TestCase):
    def test_split_audio_calls_ffmpeg_and_returns_sorted_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "chunk_001.mp3").write_bytes(b"second")
            Path(temp_dir, "chunk_000.mp3").write_bytes(b"first")

            with (
                patch("audio_splitter.shutil.which", return_value="/usr/bin/ffmpeg"),
                patch("audio_splitter.subprocess.run", return_value=Mock(returncode=0, stderr="")) as run,
            ):
                chunks = split_audio("input.mp3", temp_dir, chunk_seconds=120)

        self.assertEqual(chunks, [f"{temp_dir}/chunk_000.mp3", f"{temp_dir}/chunk_001.mp3"])
        command = run.call_args.args[0]
        self.assertIn("-segment_time", command)
        self.assertIn("120", command)

    def test_split_audio_requires_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("audio_splitter.shutil.which", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "ffmpeg is required"):
                    split_audio("input.mp3", temp_dir, chunk_seconds=120)
