import os
import tempfile
import unittest
from unittest.mock import patch

import main


class FakeTelegramFile:
    async def download_to_drive(self, path: str) -> None:
        with open(path, "wb") as audio_file:
            audio_file.write(b"audio")


class FakeAttachment:
    async def get_file(self) -> FakeTelegramFile:
        return FakeTelegramFile()


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

        with (
            patch.object(main, "transcribe_audio", return_value="raw transcript"),
            patch.object(
                main,
                "get_recent_approved_versions",
                return_value=["approved example"],
            ) as get_examples,
            patch.object(main, "format_transcript", return_value="formatted") as format_transcript,
            patch.object(main, "generate_docx", return_value=docx.name),
        ):
            await main.handle_audio(update, context=None)

        get_examples.assert_called_once_with(42, limit=3)
        format_transcript.assert_called_once_with(
            "raw transcript",
            few_shot_examples=["approved example"],
        )
        self.assertEqual(update.message.sent_document["filename"], "proceedings.docx")
        self.assertTrue(update.message.status_message.deleted)
        self.assertFalse(os.path.exists(docx.name))

