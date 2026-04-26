import tempfile
import unittest
from unittest.mock import patch

import transcriber


class FakeTranscriptions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return "transcribed text"


class FakeAudio:
    def __init__(self) -> None:
        self.transcriptions = FakeTranscriptions()


class FakeGroq:
    instance = None

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.audio = FakeAudio()
        FakeGroq.instance = self


class TranscriberTests(unittest.TestCase):
    def test_transcribe_audio_sends_supported_filename_to_groq(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp3") as audio_file:
            audio_file.write(b"audio")
            audio_file.flush()

            with (
                patch.object(transcriber, "GROQ_API_KEY", "dummy"),
                patch.object(transcriber, "Groq", FakeGroq),
            ):
                result = transcriber.transcribe_audio(audio_file.name)

        self.assertEqual(result, "transcribed text")
        self.assertEqual(FakeGroq.instance.api_key, "dummy")

        request = FakeGroq.instance.audio.transcriptions.kwargs
        self.assertEqual(request["model"], "whisper-large-v3")
        self.assertEqual(request["language"], "te")
        self.assertEqual(request["response_format"], "text")
        self.assertEqual(request["file"][0], "assembly_audio.mp3")
        self.assertEqual(request["file"][2], "audio/mpeg")

