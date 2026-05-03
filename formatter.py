import os

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, require_env
from prompts import CHAT_SYSTEM_PROMPT, FORMATTING_SYSTEM_PROMPT


OPENROUTER_BASE_URL = "https://openrouter.ai/api"


def _configure_openrouter_for_claude_agent() -> None:
    token = require_env("OPENROUTER_API_KEY", OPENROUTER_API_KEY)
    os.environ["ANTHROPIC_BASE_URL"] = OPENROUTER_BASE_URL
    os.environ["ANTHROPIC_AUTH_TOKEN"] = token
    os.environ["ANTHROPIC_API_KEY"] = ""

    if OPENROUTER_MODEL:
        os.environ.setdefault("ANTHROPIC_DEFAULT_SONNET_MODEL", OPENROUTER_MODEL)
        os.environ.setdefault("ANTHROPIC_DEFAULT_OPUS_MODEL", OPENROUTER_MODEL)


def _format_history(history: list[dict]) -> str:
    if not history:
        return ""

    lines = []
    for item in history:
        role = item.get("role", "user")
        parts = item.get("parts", [])
        content = "\n".join(str(part) for part in parts).strip()
        if content:
            lines.append(f"{role}: {content}")

    return "\n\n".join(lines)


async def _run_agent(prompt: str, system_prompt: str) -> str:
    _configure_openrouter_for_claude_agent()

    from claude_agent_sdk import ClaudeAgentOptions, query

    result = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[],
            system_prompt=system_prompt,
            model=OPENROUTER_MODEL or None,
        ),
    ):
        if hasattr(message, "result") and message.result:
            result = str(message.result)

    if not result.strip():
        raise RuntimeError("Claude Agent SDK returned an empty response")

    return result.strip()


async def format_transcript(
    raw_transcript: str,
    few_shot_examples: list[str] | None = None,
    chunk_label: str | None = None,
    include_session_header: bool = True,
) -> str:
    if not raw_transcript.strip():
        raise ValueError("Transcript is empty")

    task_prompt = raw_transcript
    if few_shot_examples:
        examples_text = "\n\n---APPROVED EXAMPLE---\n".join(few_shot_examples)
        task_prompt = f"""Here are examples of correctly formatted proceedings that were approved:

{examples_text}

---

Now format this new transcript following the same style:

{raw_transcript}"""

    if chunk_label or not include_session_header:
        chunk_instructions = []
        if chunk_label:
            chunk_instructions.append(f"This transcript is {chunk_label}.")
        if not include_session_header:
            chunk_instructions.append(
                "Do not include the session header for this chunk; the final document already has one."
            )
        chunk_instructions.append(
            "Format only this chunk. Preserve speaker order and spoken wording exactly."
        )
        task_prompt = f"{' '.join(chunk_instructions)}\n\n{task_prompt}"

    prompt = f"""Return only the formatted legislative proceedings text. Do not explain your work.

{task_prompt}"""

    return await _run_agent(prompt, FORMATTING_SYSTEM_PROMPT)


async def chat_with_memory(user_message: str, history: list[dict]) -> str:
    if not user_message.strip():
        raise ValueError("Message is empty")

    history_text = _format_history(history)
    prompt = f"""Conversation history:
{history_text or "(no previous messages)"}

User message:
{user_message}

Reply with only the assistant's response."""

    return await _run_agent(prompt, CHAT_SYSTEM_PROMPT)
