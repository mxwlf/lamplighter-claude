"""Console entry point for lamplighter.

Exposes a single ``bootstrap`` command that loads configuration from the
environment, runs the skill-bootstrap, and prints a summary. Failures are
mapped to precise exit codes for callers and CI:

* :class:`~lamplighter.config.ConfigError` -> exit ``2`` (configuration
  problem; the message names the missing variable(s)).
* :class:`~lamplighter.orchestrator.OrchestratorError` or
  :class:`~lamplighter.skills.SkillInstallError` -> exit ``1`` (bootstrap
  failed at runtime).
* Success -> exit ``0`` (summary printed to stdout).

The command body resolves :func:`load_config` and :func:`bootstrap` through the
module globals, so tests monkeypatch them at ``lamplighter.cli.load_config``
and ``lamplighter.cli.bootstrap``. The command function is named
``bootstrap_command`` to avoid shadowing the imported ``bootstrap`` helper; its
``@app.command("bootstrap")`` registration keeps the user-facing command name
``bootstrap``.
"""

import typer

from .bootstrap import bootstrap
from .config import ConfigError, load_config
from .orchestrator import OrchestratorError
from .skills import SkillInstallError

app = typer.Typer(help="Lamplighter agent harness.")


@app.command("bootstrap")
def bootstrap_command() -> None:
    """Bootstrap the local agent from its agent definition: install its skills.

    Loads configuration from the environment, runs the skill-bootstrap, and
    prints the agent id and each installed ``SKILL.md`` path on success.

    Exit codes:
        2: Configuration is missing or invalid (:class:`ConfigError`); the
            error message naming the missing variable(s) is written to stderr.
        1: Bootstrap failed at runtime (:class:`OrchestratorError` or
            :class:`SkillInstallError`); a clear message is written to stderr.
        0: Success; a summary is written to stdout.
    """
    try:
        config = load_config()
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    try:
        result = bootstrap(config)
    except (OrchestratorError, SkillInstallError) as exc:
        typer.echo(f"Bootstrap failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Bootstrapped agent {result.agent_id}")
    if result.installed_skills:
        typer.echo(f"Installed {len(result.installed_skills)} skill(s):")
        for path in result.installed_skills:
            typer.echo(f"  {path}")
    else:
        typer.echo("No skills to install.")


if __name__ == "__main__":
    app()
