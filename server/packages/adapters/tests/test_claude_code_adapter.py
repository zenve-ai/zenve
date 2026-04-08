from __future__ import annotations

from zenve_adapters.claude_code import ClaudeCodeAdapter
from zenve_models.adapter import ClaudeCodeConfig


def test_parse_token_usage_usage_key():
    adapter = ClaudeCodeAdapter()
    stdout = '{"usage": {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.005}}'

    result = adapter._parse_token_usage(stdout)

    assert result == {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.005}


def test_parse_token_usage_invalid_json_returns_none():
    adapter = ClaudeCodeAdapter()

    assert adapter._parse_token_usage("not json at all") is None
    assert adapter._parse_token_usage("") is None


def test_build_cli_args_with_tools():
    adapter = ClaudeCodeAdapter()
    config = ClaudeCodeConfig(model="claude-sonnet-4-6", max_turns=5)

    args = adapter._build_cli_args(config, "hello", "system prompt", tools=["Bash", "Read"])

    assert "--allowedTools" in args
    assert "Bash,Read" in args
    assert "--dangerously-skip-permissions" not in args


def test_build_cli_args_no_tools_skips_permissions():
    adapter = ClaudeCodeAdapter()
    config = ClaudeCodeConfig()

    args = adapter._build_cli_args(config, "hello", "system prompt", tools=None)

    assert "--dangerously-skip-permissions" in args
    assert "--allowedTools" not in args
