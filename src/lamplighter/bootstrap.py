"""Skill-bootstrap orchestration for the Lamplighter agent harness.

Bootstrap turns an agent definition into a prepared local agent. The first (and
for now only) bootstrap step is installing skills: fetch the agent definition,
then for each skill fetch its document text and install it to disk.

Per ADR-0003, bootstrap is fail-fast with no rollback. Skills are processed
sequentially in payload order; the first document-fetch or install error stops
the whole bootstrap immediately, so later skills are never fetched. The
original exception propagates so the CLI can map it to an exit code, and skills
installed before the failing one are left on disk.
"""

from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .orchestrator import OrchestratorClient
from .skills import SkillInstaller


@dataclass(frozen=True)
class BootstrapResult:
    """The outcome of a successful skill-bootstrap.

    Attributes:
        agent_id: The agent id echoed by the fetched agent definition.
        installed_skills: Paths to each installed ``SKILL.md``, in payload
            order. Empty when the definition carried no skills.
    """

    agent_id: str
    installed_skills: tuple[Path, ...]


def bootstrap(
    config: Config,
    *,
    client: OrchestratorClient | None = None,
    installer: SkillInstaller | None = None,
) -> BootstrapResult:
    """Run the skill-bootstrap for the configured agent.

    Fetches the agent definition for ``config.agent_id``, then installs each of
    its skills in payload order. For every skill the document text is fetched
    from the document service (forwarding the skill's version) and written to
    disk by the installer.

    Bootstrap is fail-fast with no rollback (ADR-0003): skills are processed
    sequentially and the first :class:`~lamplighter.orchestrator.OrchestratorError`
    or :class:`~lamplighter.skills.SkillInstallError` aborts the run, so later
    skills are never fetched. The error propagates unchanged for the CLI to map
    to an exit code, and any skills installed before the failure stay on disk.

    Args:
        config: Resolved configuration carrying the agent id, service base
            URLs, and skills install directory.
        client: An optional orchestrator client. When ``None``, an
            :class:`OrchestratorClient` is built from ``config``.
        installer: An optional skill installer. When ``None``, a
            :class:`SkillInstaller` rooted at ``config.skills_dir`` is built.

    Returns:
        A :class:`BootstrapResult` naming the agent and the installed skill
        paths. Zero skills yields an empty ``installed_skills`` (no-op success).

    Raises:
        OrchestratorError: If fetching the agent definition or any skill
            document fails.
        SkillInstallError: If writing any skill to disk fails.
    """
    if client is None:
        client = OrchestratorClient(config)
    if installer is None:
        installer = SkillInstaller(config.skills_dir)

    definition = client.get_agent_definition(config.agent_id)

    installed: list[Path] = []
    for skill in definition.skills:
        text = client.get_document(skill.name, skill.version)
        path = installer.install(skill.name, text)
        installed.append(path)
        print(f"Installed skill {skill.name!r} to {path}")

    return BootstrapResult(agent_id=definition.agent_id, installed_skills=tuple(installed))
