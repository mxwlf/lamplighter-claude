"""Tests for :mod:`lamplighter.launch`.

The launch layer is a seam stub per ADR-0005; these tests assert both entry
points raise :class:`NotImplementedError` so the seam stays unimplemented until
the follow-up deliverable lands.
"""

from pathlib import Path

import pytest

from lamplighter.config import Config
from lamplighter.launch import build_agent_options, launch
from lamplighter.models import AgentDefinition


def _fake_config() -> Config:
    """Build a minimal Config for the stub calls."""
    return Config(
        agent_id="agent-123",
        agent_definition_service_url="https://def.example",
        document_service_url="https://doc.example",
        skills_dir=Path("/tmp/skills"),
    )


def _fake_definition() -> AgentDefinition:
    """Build a minimal AgentDefinition for the stub calls."""
    return AgentDefinition(agent_id="agent-123", skills=())


def test_build_agent_options_not_implemented() -> None:
    """build_agent_options is a seam stub and raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        build_agent_options(_fake_config(), _fake_definition())


def test_launch_seam_not_implemented() -> None:
    """launch is a seam stub and raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        launch(_fake_config(), _fake_definition())
