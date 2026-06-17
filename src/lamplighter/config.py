"""Configuration loading for the Lamplighter agent harness.

Reads the environment variables Lamplighter needs to contact the orchestrator
and install skills, and exposes them as a frozen :class:`Config` value object.

The agent definition service and document service base URLs are stored as
given (whitespace-stripped, with any single trailing slash removed for
normalization); clients are responsible for appending their own paths.
"""

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SKILLS_DIR_PARTS = (".claude", "skills")  # under Path.home()

_REQUIRED_VARS = (
    "AGENT_ID",
    "AGENT_DEFINITION_SERVICE_URL",
    "DOCUMENT_SERVICE_URL",
)
_SKILLS_DIR_VAR = "LAMPLIGHTER_SKILLS_DIR"


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    """Resolved configuration for a single Lamplighter run.

    Attributes:
        agent_id: Identifier for the local agent, used to request its
            agent definition.
        agent_definition_service_url: Base URL of the agent definition service
            (no trailing path; trailing slash normalized away).
        document_service_url: Base URL of the document service (no trailing
            path; trailing slash normalized away).
        skills_dir: Resolved install root for orchestrator-managed skills.
    """

    agent_id: str
    agent_definition_service_url: str  # base URL, no trailing path
    document_service_url: str  # base URL, no trailing path
    skills_dir: Path  # resolved install root


def _normalize_base_url(value: str) -> str:
    """Strip whitespace and a single trailing slash from a base URL."""
    return value.strip().rstrip("/")


def load_config(env: dict[str, str] | None = None) -> Config:
    """Build Config from environment variables.

    Reads from ``env`` if provided, else ``os.environ``. Required vars:
      AGENT_ID, AGENT_DEFINITION_SERVICE_URL, DOCUMENT_SERVICE_URL
    Optional:
      LAMPLIGHTER_SKILLS_DIR (default: ~/.claude/skills)

    Raises ConfigError naming ALL missing required vars (collect them; do not
    fail on just the first). The skills_dir default must be
    Path.home() / ".claude" / "skills". If LAMPLIGHTER_SKILLS_DIR is set, use it
    expanded via Path(...).expanduser(). Strip whitespace from values; treat an
    empty/whitespace-only required var as missing.
    """
    source: dict[str, str] = dict(os.environ) if env is None else env

    values: dict[str, str] = {}
    missing: list[str] = []
    for name in _REQUIRED_VARS:
        raw = source.get(name, "")
        stripped = raw.strip()
        if stripped:
            values[name] = stripped
        else:
            missing.append(name)

    if missing:
        joined = ", ".join(missing)
        raise ConfigError(f"Missing required environment variables: {joined}")

    skills_dir_raw = source.get(_SKILLS_DIR_VAR, "").strip()
    if skills_dir_raw:
        skills_dir = Path(skills_dir_raw).expanduser()
    else:
        skills_dir = Path.home().joinpath(*DEFAULT_SKILLS_DIR_PARTS)

    return Config(
        agent_id=values["AGENT_ID"],
        agent_definition_service_url=_normalize_base_url(values["AGENT_DEFINITION_SERVICE_URL"]),
        document_service_url=_normalize_base_url(values["DOCUMENT_SERVICE_URL"]),
        skills_dir=skills_dir,
    )
