"""Tests for :mod:`lamplighter.bootstrap`.

These exercise the real :class:`OrchestratorClient` (over respx-mocked HTTP) and
a real :class:`SkillInstaller` pointed at ``tmp_path``, so installs actually
happen on disk. This is integration with the HTTP transport mocked, which is
the intent.
"""

import httpx
import pytest
import respx

from lamplighter.bootstrap import BootstrapResult, bootstrap
from lamplighter.config import Config
from lamplighter.orchestrator import OrchestratorClient, OrchestratorError
from lamplighter.skills import SKILL_FILENAME, SkillInstaller

DEF_URL = "https://def.example"
DOC_URL = "https://doc.example"
AGENT_ID = "agent-123"


@pytest.fixture
def config(tmp_path) -> Config:
    """Return a Config pointing at test service base URLs and a tmp skills dir."""
    return Config(
        agent_id=AGENT_ID,
        agent_definition_service_url=DEF_URL,
        document_service_url=DOC_URL,
        skills_dir=tmp_path,
    )


def _mock_definition(skills: list[dict]) -> None:
    """Mock the agent definition service to return ``skills`` for the agent."""
    payload = {"agent_id": AGENT_ID, "skills": skills}
    respx.get(f"{DEF_URL}/agents/{AGENT_ID}").mock(return_value=httpx.Response(200, json=payload))


@respx.mock
def test_bootstrap_installs_all_skills(config: Config, tmp_path) -> None:
    """Two mocked skills are both fetched and written, with ordered result paths."""
    _mock_definition([{"name": "alpha"}, {"name": "beta"}])
    respx.get(f"{DOC_URL}/documents/alpha").mock(return_value=httpx.Response(200, text="ALPHA BODY"))
    respx.get(f"{DOC_URL}/documents/beta").mock(return_value=httpx.Response(200, text="BETA BODY"))

    result = bootstrap(config, client=OrchestratorClient(config), installer=SkillInstaller(tmp_path))

    assert isinstance(result, BootstrapResult)
    assert result.agent_id == AGENT_ID
    assert len(result.installed_skills) == 2

    alpha_path = tmp_path / "alpha" / SKILL_FILENAME
    beta_path = tmp_path / "beta" / SKILL_FILENAME
    assert alpha_path.read_text() == "ALPHA BODY"
    assert beta_path.read_text() == "BETA BODY"

    assert result.installed_skills[0] == alpha_path.resolve()
    assert result.installed_skills[1] == beta_path.resolve()


@respx.mock
def test_bootstrap_fail_fast_on_document_error(config: Config, tmp_path) -> None:
    """A document fetch error aborts bootstrap and prevents fetching later skills."""
    _mock_definition([{"name": "alpha"}, {"name": "beta"}])
    respx.get(f"{DOC_URL}/documents/alpha").mock(return_value=httpx.Response(404))
    beta_route = respx.get(f"{DOC_URL}/documents/beta").mock(return_value=httpx.Response(200, text="BETA BODY"))

    with pytest.raises(OrchestratorError) as exc_info:
        bootstrap(config, client=OrchestratorClient(config), installer=SkillInstaller(tmp_path))

    assert exc_info.value.status_code == 404
    # The first skill failed on fetch, so the second skill's document was never requested.
    assert beta_route.call_count == 0
    # Neither skill should be on disk: alpha failed before install, beta never reached.
    assert not (tmp_path / "alpha" / SKILL_FILENAME).exists()
    assert not (tmp_path / "beta" / SKILL_FILENAME).exists()


@respx.mock
def test_bootstrap_no_rollback_leaves_prior_skill(config: Config, tmp_path) -> None:
    """When a later skill fails, the earlier installed skill stays on disk."""
    _mock_definition([{"name": "alpha"}, {"name": "beta"}])
    respx.get(f"{DOC_URL}/documents/alpha").mock(return_value=httpx.Response(200, text="ALPHA BODY"))
    respx.get(f"{DOC_URL}/documents/beta").mock(return_value=httpx.Response(500))

    with pytest.raises(OrchestratorError) as exc_info:
        bootstrap(config, client=OrchestratorClient(config), installer=SkillInstaller(tmp_path))

    assert exc_info.value.status_code == 500
    # No rollback: alpha installed before beta failed and remains on disk.
    alpha_path = tmp_path / "alpha" / SKILL_FILENAME
    assert alpha_path.read_text() == "ALPHA BODY"
    assert not (tmp_path / "beta" / SKILL_FILENAME).exists()


@respx.mock
def test_bootstrap_empty_skills_noop(config: Config, tmp_path) -> None:
    """An empty skill list is a no-op success with no files written."""
    _mock_definition([])

    result = bootstrap(config, client=OrchestratorClient(config), installer=SkillInstaller(tmp_path))

    assert result.agent_id == AGENT_ID
    assert result.installed_skills == ()
    # Nothing was written under the install root.
    assert list(tmp_path.iterdir()) == []


@respx.mock
def test_bootstrap_forwards_version_to_document_call(config: Config, tmp_path) -> None:
    """The skill version is forwarded to the document request; absent version sends none."""
    _mock_definition([{"name": "versioned", "version": "1.2.0"}, {"name": "plain"}])
    versioned_route = respx.get(f"{DOC_URL}/documents/versioned").mock(
        return_value=httpx.Response(200, text="VERSIONED BODY")
    )
    plain_route = respx.get(f"{DOC_URL}/documents/plain").mock(return_value=httpx.Response(200, text="PLAIN BODY"))

    bootstrap(config, client=OrchestratorClient(config), installer=SkillInstaller(tmp_path))

    versioned_request = versioned_route.calls[-1].request
    assert versioned_request.url.params["version"] == "1.2.0"

    plain_request = plain_route.calls[-1].request
    assert "version" not in plain_request.url.params
