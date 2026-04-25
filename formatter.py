import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, require_env
from prompts import FORMATTING_SYSTEM_PROMPT


def _configure_gemini() -> None:
    genai.configure(api_key=require_env("GEMINI_API_KEY", GEMINI_API_KEY))


def format_transcript(
    raw_transcript: str,
    few_shot_examples: list[str] | None = None,
) -> str:
    if not raw_transcript.strip():
        raise ValueError("Transcript is empty")

    _configure_gemini()
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=FORMATTING_SYSTEM_PROMPT,
    )

    prompt = raw_transcript
    if few_shot_examples:
        examples_text = "\n\n---APPROVED EXAMPLE---\n".join(few_shot_examples)
        prompt = f"""Here are examples of correctly formatted proceedings that were approved:

{examples_text}

---

Now format this new transcript following the same style:

{raw_transcript}"""

    response = model.generate_content(prompt)
    return response.text.strip()
