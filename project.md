# Assembly Reporter Bot — Project Spec

**Project:** Telegram bot that transcribes Telangana Assembly session audio recordings, formats them into proper legislative proceedings, and learns from approved versions over time.

**Built for:** A senior assembly reporter covering Telangana Legislature sessions.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Bot framework | `python-telegram-bot` v21 |
| Transcription | Groq API — `whisper-large-v3` |
| Formatting/AI | Google Gemini `gemini-2.5-pro` |
| Memory | SQLite via `sqlite3` (stdlib) |
| Document generation | `python-docx` |
| Hosting | Render (free tier, always-on web service) |
| Language | Python 3.11+ |

---

## Project Structure

```
assembly-bot/
├── main.py                  # Entry point, Telegram bot handlers
├── transcriber.py           # Groq Whisper integration
├── formatter.py             # Gemini formatting logic
├── memory.py                # SQLite memory + conversation history
├── docx_generator.py        # python-docx output
├── config.py                # All env vars and constants
├── prompts.py               # All system prompts (keep separate, easy to tune)
├── database/
│   └── bot_memory.db        # SQLite DB (gitignored)
├── requirements.txt
├── render.yaml              # Render deployment config
└── .env                     # API keys (gitignored)
```

---

## Environment Variables

```env
TELEGRAM_BOT_TOKEN=
GROQ_API_KEY=
GEMINI_API_KEY=
```

---

## Phase 1 — Core Pipeline (Ship First)

**Goal:** Dad sends audio → gets .docx back. Nothing else.

### Step 1.1 — Project Setup

```bash
pip install python-telegram-bot groq google-generativeai python-docx python-dotenv
```

`requirements.txt`:
```
python-telegram-bot==21.5
groq==0.11.0
google-generativeai==0.8.0
python-docx==1.1.2
python-dotenv==1.0.1
```

### Step 1.2 — Config (`config.py`)

```python
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-2.5-pro"
MAX_AUDIO_SIZE_MB = 25  # Groq limit
```

### Step 1.3 — Transcription (`transcriber.py`)

```python
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file,
            language="te",  # Telugu — helps accuracy massively
            response_format="text"
        )
    return transcription
```

> **Note:** Set `language="te"` for Telugu sessions. For mixed Telugu+English sessions (which is most of them), you can try `language=None` and let Whisper auto-detect — test both and see which gives better results for your dad's recordings.

### Step 1.4 — System Prompt (`prompts.py`)

This is the most important file. Tune this aggressively.

```python
FORMATTING_SYSTEM_PROMPT = """
You are an expert formatter for Telangana Legislative Assembly proceedings.

Your job is to take a raw audio transcript and format it into a clean, 
structured legislative document — exactly like official assembly records.

## Output Format Rules:
- Speaker names are prefixed with their title and formatted as:
  `} Sri [Name] ([Party]):` for members
  `MR. SPEAKER:` for the Speaker
- Each speaker's dialogue is a separate paragraph
- Preserve both Telugu and English content exactly as spoken
- Do NOT translate — keep the language as-is
- Fix obvious transcription errors for proper nouns

## Known Politicians & Entities (fix spelling if transcription garbles these):
- KTR = K.T. Rama Rao (BRS)
- Revanth Reddy = Chief Minister, Congress
- Harish Rao = BRS leader (transcription may write "H Rao" or "Harris Rao")
- D. Sridhar Babu = Minister, Municipal Administration
- Musi = Musi River Rejuvenation Project
- L&T Metro = Hyderabad Metro Rail
- DPR = Detailed Project Report
- FTL = Full Tank Level
- HMDA = Hyderabad Metropolitan Development Authority

## Formatting Rules for Numbers:
- "200cr" or "200 crore" → Rs. 200 Crores
- "15000 crore" → Rs. 15,000 Crores
- "1.5 lakh crore" → Rs. 1,50,000 Crores
- Always use Indian number formatting

## Uncertain Words:
- If you are not confident about a word or name, wrap it in [?word?]
- This helps the reporter find and fix uncertain spots quickly

## Structure:
1. Session header (date, time if mentioned)
2. Speaker dialogues in order
3. Any announcements or voting results at the end

Output clean, professional text ready for official documentation.
"""

CHAT_SYSTEM_PROMPT = """
You are a helpful assistant for a senior Telangana Assembly reporter.
Be warm, friendly, and concise. You speak in a mix of English and Telugu naturally.
You help with transcription, formatting assembly proceedings, and answering 
questions about the workflow. Keep responses short and practical.
"""
```

### Step 1.5 — Formatter (`formatter.py`)

```python
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL
from prompts import FORMATTING_SYSTEM_PROMPT

genai.configure(api_key=GEMINI_API_KEY)

def format_transcript(raw_transcript: str, few_shot_examples: list[str] = None) -> str:
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=FORMATTING_SYSTEM_PROMPT
    )
    
    prompt = raw_transcript
    
    # If we have approved examples from DB, inject them as few-shot
    if few_shot_examples:
        examples_text = "\n\n---APPROVED EXAMPLE---\n".join(few_shot_examples)
        prompt = f"""Here are examples of correctly formatted proceedings that were approved:

{examples_text}

---

Now format this new transcript following the same style:

{raw_transcript}"""
    
    response = model.generate_content(prompt)
    return response.text
```

### Step 1.6 — DOCX Generator (`docx_generator.py`)

```python
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import tempfile
import os

def generate_docx(formatted_text: str, session_label: str = "") -> str:
    doc = Document()
    
    # Page margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.25)
    
    # Title
    if session_label:
        title = doc.add_heading(session_label, level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Content — split by lines, add paragraphs
    for line in formatted_text.split("\n"):
        if line.strip():
            para = doc.add_paragraph(line)
            para.style.font.size = Pt(12)
            para.style.font.name = "Times New Roman"
    
    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(tmp.name)
    return tmp.name
```

### Step 1.7 — Main Bot (`main.py`) — Phase 1 version

```python
import logging
import os
import tempfile
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from transcriber import transcribe_audio
from formatter import format_transcript
from docx_generator import generate_docx

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! 🙏 Audio file పంపండి, నేను transcribe చేసి .docx తయారు చేస్తాను."
    )

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Audio processing మొదలైంది...")

    # Download audio
    file = await update.message.effective_attachment.get_file()
    tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    await file.download_to_drive(tmp_audio.name)

    try:
        # Step 1: Transcribe
        await msg.edit_text("🎙️ Transcribing...")
        transcript = transcribe_audio(tmp_audio.name)

        # Step 2: Format
        await msg.edit_text("📝 Formatting proceedings...")
        formatted = format_transcript(transcript)

        # Step 3: Generate DOCX
        docx_path = generate_docx(formatted, session_label="Assembly Proceedings")

        # Step 4: Send back
        await msg.edit_text("✅ Done! Sending file...")
        with open(docx_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="proceedings.docx",
                caption="Ready for review! [?] marks are uncertain spots 🔍"
            )

    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        os.unlink(tmp_audio.name)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.AUDIO, handle_audio))
    app.run_polling()

if __name__ == "__main__":
    main()
```

---

## Phase 2 — Memory + Friendly Chat

**Goal:** Bot remembers conversation context, talks friendly, handles non-audio messages too.

### Step 2.1 — SQLite Memory (`memory.py`)

```python
import sqlite3
import json
from datetime import datetime

DB_PATH = "database/bot_memory.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Conversation history per user
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,           -- 'user' or 'model'
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Approved final versions submitted by dad
    c.execute("""
        CREATE TABLE IF NOT EXISTS approved_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            original_transcript TEXT,
            formatted_output TEXT,
            approved_docx_text TEXT,  -- extracted text from final submitted docx
            session_label TEXT,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def save_message(user_id: int, role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()
    conn.close()

def get_history(user_id: int, last_n: int = 10) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """SELECT role, content FROM conversations 
           WHERE user_id = ? 
           ORDER BY timestamp DESC LIMIT ?""",
        (user_id, last_n)
    )
    rows = c.fetchall()
    conn.close()
    # Reverse to get chronological order
    return [{"role": r[0], "parts": [r[1]]} for r in reversed(rows)]

def save_approved_version(user_id: int, approved_text: str, session_label: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """INSERT INTO approved_versions (user_id, approved_docx_text, session_label) 
           VALUES (?, ?, ?)""",
        (user_id, approved_text, session_label)
    )
    conn.commit()
    conn.close()

def get_recent_approved_versions(user_id: int, limit: int = 3) -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """SELECT approved_docx_text FROM approved_versions 
           WHERE user_id = ? 
           ORDER BY submitted_at DESC LIMIT ?""",
        (user_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]
```

### Step 2.2 — Chat Handler with History

Update `formatter.py` to support chat mode:

```python
def chat_with_memory(user_message: str, history: list[dict]) -> str:
    from prompts import CHAT_SYSTEM_PROMPT
    
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=CHAT_SYSTEM_PROMPT
    )
    
    chat = model.start_chat(history=history)
    response = chat.send_message(user_message)
    return response.text
```

### Step 2.3 — Update `main.py` with chat + memory

Add these handlers:

```python
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Save user message
    save_message(user_id, "user", user_text)
    
    # Get history
    history = get_history(user_id, last_n=10)
    
    # Chat
    response = chat_with_memory(user_text, history[:-1])  # exclude last msg, already in send
    
    # Save bot response
    save_message(user_id, "model", response)
    
    await update.message.reply_text(response)

# Register in main():
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
```

### Step 2.4 — Handle "final version" submission

Dad sends the approved .docx back to the bot with caption `/final` or just sends it as a document:

```python
async def handle_final_docx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Extract text from submitted docx
    file = await update.message.document.get_file()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    await file.download_to_drive(tmp.name)
    
    from docx import Document
    doc = Document(tmp.name)
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    
    save_approved_version(update.effective_user.id, text)
    await update.message.reply_text(
        "✅ Final version saved! Next transcriptions will learn from this style."
    )
    os.unlink(tmp.name)

# In main(), add:
app.add_handler(MessageHandler(
    filters.Document.FileExtension("docx") & filters.CaptionRegex(r"(?i)/final|final"),
    handle_final_docx
))
```

---

## Phase 3 — Learning from Approved Versions (Few-Shot)

**Goal:** Use saved approved .docx files to improve future formatting quality.

This is already wired in Phase 1's `format_transcript()` — just pass the examples:

```python
# In handle_audio(), update the format step:
examples = get_recent_approved_versions(user_id, limit=3)
formatted = format_transcript(transcript, few_shot_examples=examples)
```

That's it. Gemini will see the last 3 approved versions as style references and match the formatting automatically. No retraining needed.

---

## Phase 4 — Deployment on Render

### Step 4.1 — `render.yaml`

```yaml
services:
  - type: worker
    name: assembly-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: GROQ_API_KEY
        sync: false
      - key: GEMINI_API_KEY
        sync: false
```

Use `worker` type, not `web` — bots don't need HTTP.

### Step 4.2 — Persistent Disk for SQLite

In Render dashboard → your service → Disks → Add disk:
- Mount path: `/data`
- Size: 1 GB (free)

Update `DB_PATH` in `memory.py`:
```python
DB_PATH = "/data/bot_memory.db"
```

### Step 4.3 — Deploy

```bash
git init
git add .
git commit -m "initial commit"
# Push to GitHub, connect repo on Render
# Add env vars in Render dashboard
# Deploy
```

---

## Important Notes for Your AI Coding Agent

1. **Gemini model name** — Use `gemini-2.5-pro`.

2. **Groq audio limit** — 25MB per file. If dad's recordings are longer, split with `pydub` before sending to Groq.

3. **Whisper language** — Start with `language="te"` for Telugu. If mixed sessions sound worse, try `language=None` for auto-detect.

4. **Telegram file size limit** — Bots can receive files up to 20MB via `get_file()`. For larger audio, dad needs to compress or split.

5. **`[?word?]` convention** — This is the uncertain word marker. Make sure the Gemini prompt explicitly instructs this and the bot's reply message mentions it.

6. **`/final` command** — Keep the final version submission simple. Dad just sends the docx back with caption "final" — no complex command needed.

7. **DB folder** — Create `database/` folder before running locally. On Render, use `/data/` path instead.

8. **init_db()** — Call this once at bot startup in `main.py` before `app.run_polling()`.

---

## Future Ideas (Don't Build Now)

- Auto-detect session date from audio and label the docx filename accordingly
- `/summary` command — summarize the session in 5 bullet points
- Daily digest — bot sends dad a summary of all sessions covered that day
- Speaker diarization — use AssemblyAI or pyannote to auto-identify who is speaking before formatting
