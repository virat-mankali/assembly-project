import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main


class FakeTelegramFile:
    file_path = "https://api.telegram.org/file/bot-token/music/file_1.mp3"

    async def download_to_drive(self, path: str) -> None:
        self.download_path = path
        with open(path, "wb") as audio_file:
            audio_file.write(b"audio")


class FakeAttachment:
    def __init__(self) -> None:
        self.telegram_file = FakeTelegramFile()

    async def get_file(self) -> FakeTelegramFile:
        return self.telegram_file


class FakeStatusMessage:
    def __init__(self) -> None:
        self.text_updates: list[str] = []
        self.deleted = False

    async def edit_text(self, text: str) -> None:
        self.text_updates.append(text)

    async def delete(self) -> None:
        self.deleted = True


class FakeMessage:
    def __init__(self) -> None:
        self.effective_attachment = FakeAttachment()
        self.status_message = FakeStatusMessage()
        self.sent_document: dict | None = None

    async def reply_text(self, text: str) -> FakeStatusMessage:
        self.status_message.text_updates.append(text)
        return self.status_message

    async def reply_document(self, document, filename: str, caption: str) -> None:
        self.sent_document = {
            "content": document.read(),
            "filename": filename,
            "caption": caption,
        }


class FakeUser:
    id = 42


class FakeUpdate:
    def __init__(self) -> None:
        self.message = FakeMessage()
        self.effective_user = FakeUser()


class Phase3Tests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_audio_uses_recent_approved_versions(self) -> None:
        update = FakeUpdate()
        docx = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        docx.write(b"docx")
        docx.close()
        chunks = ["/tmp/chunk_000.mp3", "/tmp/chunk_001.mp3"]

        with (
            patch.object(main, "split_audio", return_value=chunks) as split_audio,
            patch.object(
                main,
                "transcribe_audio",
                side_effect=["raw transcript 1", "raw transcript 2"],
            ) as transcribe_audio,
            patch.object(
                main,
                "get_recent_approved_versions",
                return_value=["approved example"],
            ) as get_examples,
            patch.object(
                main,
                "format_transcript",
                side_effect=["formatted 1", "formatted 2"],
            ) as format_transcript,
            patch.object(main, "generate_docx", return_value=docx.name) as generate_docx,
        ):
            await main.handle_audio(update, context=None)

        audio_path = update.message.effective_attachment.telegram_file.download_path
        self.assertTrue(audio_path.endswith(".mp3"))
        split_audio.assert_called_once()
        self.assertEqual(Path(split_audio.call_args.args[0]).suffix, ".mp3")
        get_examples.assert_called_once_with(42, limit=3)
        self.assertEqual([call.args[0] for call in transcribe_audio.call_args_list], chunks)
        self.assertEqual(
            [call.kwargs["chunk_label"] for call in format_transcript.call_args_list],
            ["chunk 1 of 2", "chunk 2 of 2"],
        )
        self.assertEqual(
            [call.kwargs["include_session_header"] for call in format_transcript.call_args_list],
            [True, False],
        )
        format_transcript.assert_any_call(
            "raw transcript 1",
            few_shot_examples=["approved example"],
            chunk_label="chunk 1 of 2",
            include_session_header=True,
        )
        format_transcript.assert_any_call(
            "raw transcript 2",
            few_shot_examples=["approved example"],
            chunk_label="chunk 2 of 2",
            include_session_header=False,
        )
        generate_docx.assert_called_once_with("formatted 1\n\nformatted 2")
        self.assertEqual(update.message.sent_document["filename"], "proceedings.docx")
        self.assertTrue(update.message.status_message.deleted)
        self.assertFalse(os.path.exists(docx.name))
