"""Launch layer seam (NOT YET IMPLEMENTED).

Per ADR-0005, Lamplighter will drive agent execution via the Claude Agent SDK
(claude-agent-sdk: query()/ClaudeSDKClient with ClaudeAgentOptions). This module
is the seam where the prepared environment + agent definition become a launched
agent. The bootstrap layer (skill install) is complete; launch is future work.
"""

from .config import Config
from .models import AgentDefinition


def build_agent_options(config: Config, definition: AgentDefinition) -> object:
    """Assemble the ClaudeAgentOptions for launch. Not yet implemented.

    Args:
        config: The resolved configuration for the run.
        definition: The agent definition describing the agent's needs.

    Returns:
        The assembled launch options once implemented.

    Raises:
        NotImplementedError: Always; agent launch is a follow-up deliverable.
    """
    raise NotImplementedError("Agent launch is a follow-up deliverable; see ADR-0005.")


def launch(config: Config, definition: AgentDefinition) -> None:
    """Launch the prepared agent via the Claude Agent SDK. Not yet implemented.

    Args:
        config: The resolved configuration for the run.
        definition: The agent definition describing the agent's needs.

    Raises:
        NotImplementedError: Always; agent launch is a follow-up deliverable.
    """
    raise NotImplementedError("Agent launch is a follow-up deliverable; see ADR-0005.")
