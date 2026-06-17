"""Tests for :mod:`lamplighter.cli`.

These invoke the Typer app via :class:`typer.testing.CliRunner` and monkeypatch
the module-level ``load_config`` and ``bootstrap`` names so the command's
exit-code contract can be exercised without touching the network or disk.
"""

from pathlib import Path

from typer.testing import CliRunner

from lamplighter import cli
from lamplighter.bootstrap import BootstrapResult
from lamplighter.config import Config, ConfigError
from lamplighter.orchestrator import OrchestratorError

runner = CliRunner()


def _fake_config() -> Config:
    """Build a throwaway Config; its fields are never read by the fakes."""
    return Config(
        agent_id="agent-123",
        agent_definition_service_url="https://def.example",
        document_service_url="https://doc.example",
        skills_dir=Path("/tmp/skills"),
    )


def test_cli_bootstrap_success_exit_0(monkeypatch) -> None:
    """A successful bootstrap exits 0 and reports the agent id and skill paths."""
    paths = (Path("/tmp/skills/tdd/SKILL.md"), Path("/tmp/skills/review/SKILL.md"))

    monkeypatch.setattr(cli, "load_config", lambda: _fake_config())
    monkeypatch.setattr(
        cli,
        "bootstrap",
        lambda config: BootstrapResult(agent_id="agent-123", installed_skills=paths),
    )

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 0
    assert "agent-123" in result.output
    assert "/tmp/skills/tdd/SKILL.md" in result.output
    assert "/tmp/skills/review/SKILL.md" in result.output


def test_cli_missing_env_exit_2(monkeypatch) -> None:
    """A ConfigError exits 2 and names the missing variable."""

    def _raise() -> Config:
        raise ConfigError("Missing required environment variables: AGENT_ID")

    monkeypatch.setattr(cli, "load_config", _raise)

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 2
    assert "AGENT_ID" in result.output


def test_cli_bootstrap_failure_exit_1(monkeypatch) -> None:
    """An OrchestratorError during bootstrap exits 1 with a clear message."""

    def _raise(config: Config) -> BootstrapResult:
        raise OrchestratorError("boom", resource="document tdd", status_code=404)

    monkeypatch.setattr(cli, "load_config", lambda: _fake_config())
    monkeypatch.setattr(cli, "bootstrap", _raise)

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 1
    assert "boom" in result.output
