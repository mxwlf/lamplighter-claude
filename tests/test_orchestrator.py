"""Tests for :mod:`lamplighter.orchestrator`."""

from pathlib import Path

import httpx
import pytest
import respx

from lamplighter.config import Config
from lamplighter.models import AgentDefinition
from lamplighter.orchestrator import OrchestratorClient, OrchestratorError

DEF_URL = "https://def.example"
DOC_URL = "https://doc.example"


@pytest.fixture
def config() -> Config:
    """Return a Config pointing at test orchestrator service base URLs."""
    return Config(
        agent_id="agent-123",
        agent_definition_service_url=DEF_URL,
        document_service_url=DOC_URL,
        skills_dir=Path("/tmp/skills"),
    )


@respx.mock
def test_get_agent_definition_success(config: Config) -> None:
    """A 200 JSON payload parses into an AgentDefinition with correct fields."""
    payload = {
        "agent_id": "agent-123",
        "skills": [
            {"name": "tdd", "version": "1.2.0"},
            {"name": "diagnose"},
        ],
        "task": {"context": "ctx", "instructions": "do the thing"},
    }
    respx.get(f"{DEF_URL}/agents/agent-123").mock(return_value=httpx.Response(200, json=payload))

    client = OrchestratorClient(config)
    definition = client.get_agent_definition("agent-123")

    assert isinstance(definition, AgentDefinition)
    assert definition.agent_id == "agent-123"
    assert len(definition.skills) == 2
    assert definition.skills[0].name == "tdd"
    assert definition.skills[0].version == "1.2.0"
    assert definition.skills[1].name == "diagnose"
    assert definition.skills[1].version is None
    assert definition.task.context == "ctx"
    assert definition.task.instructions == "do the thing"


@respx.mock
def test_get_agent_definition_404_raises(config: Config) -> None:
    """A 404 from the agent definition service raises OrchestratorError."""
    respx.get(f"{DEF_URL}/agents/agent-123").mock(return_value=httpx.Response(404))

    client = OrchestratorClient(config)
    with pytest.raises(OrchestratorError) as exc_info:
        client.get_agent_definition("agent-123")

    assert exc_info.value.status_code == 404
    assert "agent-123" in exc_info.value.resource


@respx.mock
def test_get_document_success_returns_text(config: Config) -> None:
    """A 200 text/plain document body is returned verbatim."""
    respx.get(f"{DOC_URL}/documents/tdd").mock(
        return_value=httpx.Response(200, text="SKILL BODY", headers={"content-type": "text/plain"})
    )

    client = OrchestratorClient(config)
    body = client.get_document("tdd")

    assert body == "SKILL BODY"


@respx.mock
def test_get_document_omits_version_when_absent(config: Config) -> None:
    """Calling get_document without a version sends no version query param."""
    route = respx.get(f"{DOC_URL}/documents/tdd").mock(return_value=httpx.Response(200, text="SKILL BODY"))

    client = OrchestratorClient(config)
    client.get_document("tdd")

    request = route.calls[-1].request
    assert "version" not in request.url.params


@respx.mock
def test_get_document_includes_version_when_present(config: Config) -> None:
    """Calling get_document with a version sends version=<value> as a query param."""
    route = respx.get(f"{DOC_URL}/documents/tdd").mock(return_value=httpx.Response(200, text="SKILL BODY"))

    client = OrchestratorClient(config)
    client.get_document("tdd", "1.2.0")

    request = route.calls[-1].request
    assert request.url.params["version"] == "1.2.0"


@respx.mock
def test_get_document_404_raises(config: Config) -> None:
    """A 404 from the document service raises OrchestratorError with status 404."""
    respx.get(f"{DOC_URL}/documents/tdd").mock(return_value=httpx.Response(404))

    client = OrchestratorClient(config)
    with pytest.raises(OrchestratorError) as exc_info:
        client.get_document("tdd")

    assert exc_info.value.status_code == 404
    assert "tdd" in exc_info.value.resource


@respx.mock
def test_network_error_raises_orchestrator_error(config: Config) -> None:
    """A transport error surfaces as OrchestratorError with status_code None."""
    respx.get(f"{DOC_URL}/documents/tdd").mock(side_effect=httpx.ConnectError("boom"))

    client = OrchestratorClient(config)
    with pytest.raises(OrchestratorError) as exc_info:
        client.get_document("tdd")

    assert exc_info.value.status_code is None
    assert "tdd" in exc_info.value.resource
