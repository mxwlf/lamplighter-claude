"""Tests for :mod:`lamplighter.config`."""

from pathlib import Path

import pytest

from lamplighter.config import Config, ConfigError, load_config


def _base_env() -> dict[str, str]:
    """Return an env mapping with all required vars present."""
    return {
        "AGENT_ID": "agent-123",
        "AGENT_DEFINITION_SERVICE_URL": "https://orchestrator.example/definitions",
        "DOCUMENT_SERVICE_URL": "https://orchestrator.example/documents",
    }


def test_load_config_all_present() -> None:
    """All required vars present and no override yields a populated Config."""
    config = load_config(env=_base_env())

    assert isinstance(config, Config)
    assert config.agent_id == "agent-123"
    assert config.agent_definition_service_url == "https://orchestrator.example/definitions"
    assert config.document_service_url == "https://orchestrator.example/documents"
    assert config.skills_dir == Path.home() / ".claude" / "skills"


def test_load_config_missing_agent_id_raises() -> None:
    """Omitting AGENT_ID raises ConfigError naming it."""
    env = _base_env()
    del env["AGENT_ID"]

    with pytest.raises(ConfigError) as exc_info:
        load_config(env=env)

    assert "AGENT_ID" in str(exc_info.value)


def test_load_config_missing_both_service_urls_raises_naming_both() -> None:
    """Omitting both service URLs raises ConfigError naming both."""
    env = _base_env()
    del env["AGENT_DEFINITION_SERVICE_URL"]
    del env["DOCUMENT_SERVICE_URL"]

    with pytest.raises(ConfigError) as exc_info:
        load_config(env=env)

    message = str(exc_info.value)
    assert "AGENT_DEFINITION_SERVICE_URL" in message
    assert "DOCUMENT_SERVICE_URL" in message


def test_skills_dir_defaults_to_home_claude_skills() -> None:
    """Without an override, skills_dir defaults to ~/.claude/skills."""
    config = load_config(env=_base_env())

    assert config.skills_dir == Path.home() / ".claude" / "skills"


def test_skills_dir_override_respected(tmp_path: Path) -> None:
    """LAMPLIGHTER_SKILLS_DIR overrides the default and is expanded."""
    env = _base_env()
    env["LAMPLIGHTER_SKILLS_DIR"] = str(tmp_path / "custom-skills")

    config = load_config(env=env)

    assert config.skills_dir == (tmp_path / "custom-skills").expanduser()


def test_empty_required_var_treated_as_missing() -> None:
    """An empty/whitespace-only required var is treated as missing."""
    env = _base_env()
    env["AGENT_ID"] = ""

    with pytest.raises(ConfigError) as exc_info:
        load_config(env=env)

    assert "AGENT_ID" in str(exc_info.value)
