import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import formatter
from prompts import FORMATTING_SYSTEM_PROMPT


class FakeResultMessage:
    result = " formatted proceedings "


class FakeClaudeAgentOptions:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


class FormatterTests(unittest.IsolatedAsyncioTestCase):
    async def test_format_transcript_uses_claude_agent_sdk_openrouter_config(self) -> None:
        captured = {}

        async def fake_query(prompt, options):
            captured["prompt"] = prompt
            captured["options"] = options
            yield FakeResultMessage()

        with (
            patch.object(formatter, "OPENROUTER_API_KEY", "or-key"),
            patch.object(formatter, "OPENROUTER_MODEL", "anthropic/test-model"),
            patch.dict(
                "sys.modules",
                {
                    "claude_agent_sdk": SimpleNamespace(
                        ClaudeAgentOptions=FakeClaudeAgentOptions,
                        query=fake_query,
                    )
                },
            ),
        ):
            result = await formatter.format_transcript("raw transcript")

        self.assertEqual(result, "formatted proceedings")
        self.assertEqual(os.environ["ANTHROPIC_BASE_URL"], "https://openrouter.ai/api")
        self.assertEqual(os.environ["ANTHROPIC_AUTH_TOKEN"], "or-key")
        self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "")
        self.assertIn("raw transcript", captured["prompt"])
        self.assertEqual(captured["options"].allowed_tools, [])
        self.assertEqual(captured["options"].system_prompt, FORMATTING_SYSTEM_PROMPT)
        self.assertEqual(captured["options"].model, "anthropic/test-model")
