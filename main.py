import logging
import os
import tempfile

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import TELEGRAM_BOT_TOKEN, validate_runtime_config
from docx_generator import generate_docx
from formatter import format_transcript
from transcriber import transcribe_audio


logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Namaste! Send an audio file or voice note, and I will return a formatted DOCX."
        )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.effective_attachment:
        return

    status_message = await update.message.reply_text("Audio processing started...")
    audio_path = ""
    docx_path = ""

    try:
        attachment = update.message.effective_attachment
        telegram_file = await attachment.get_file()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".audio") as tmp_audio:
            audio_path = tmp_audio.name

        await telegram_file.download_to_drive(audio_path)

        await status_message.edit_text("Transcribing audio...")
        transcript = transcribe_audio(audio_path)

        await status_message.edit_text("Formatting proceedings...")
        formatted = format_transcript(transcript)

        await status_message.edit_text("Generating DOCX...")
        docx_path = generate_docx(formatted, session_label="Assembly Proceedings")

        await status_message.edit_text("Done. Sending file...")
        with open(docx_path, "rb") as docx_file:
            await update.message.reply_document(
                document=docx_file,
                filename="proceedings.docx",
                caption="Ready for review. Uncertain spots are marked like [?word?].",
            )

        await status_message.delete()
    except Exception:
        logger.exception("Failed to process audio")
        await status_message.edit_text(
            "Sorry, I could not process that audio. Please check the file and try again."
        )
    finally:
        for path in (audio_path, docx_path):
            if path and os.path.exists(path):
                os.unlink(path)


def build_application() -> Application:
    validate_runtime_config()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.AUDIO, handle_audio)
    )
    return app


def main() -> None:
    app = build_application()
    app.run_polling()


if __name__ == "__main__":
    main()
