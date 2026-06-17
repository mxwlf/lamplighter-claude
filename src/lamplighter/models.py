"""Domain models for agent definitions.

An agent definition is the bundle the orchestrator provides describing what an
agent needs for its task. This module models that payload as frozen dataclasses
and parses it from the JSON returned by the agent definition service.
"""

from dataclasses import dataclass, field


class ValidationError(Exception):
    """Raised when an agent definition payload is malformed."""


@dataclass(frozen=True)
class Skill:
    """A unit of task-specific instructions the local agent loads when relevant.

    Attributes:
        name: The skill name; non-empty and load-bearing for installation.
        version: Optional version string, or ``None`` when unspecified.
    """

    name: str
    version: str | None = None


@dataclass(frozen=True)
class Task:
    """The task context and instructions carried by an agent definition.

    Parsed for completeness, but the rest of the system does not act on it yet.

    Attributes:
        context: Free-form task context; empty string when unspecified.
        instructions: Free-form task instructions; empty string when unspecified.
    """

    context: str = ""
    instructions: str = ""


@dataclass(frozen=True)
class AgentDefinition:
    """A parsed agent definition describing what an agent needs for its task.

    Attributes:
        agent_id: The local agent identifier, echoed for traceability.
        skills: The skills the local agent should load, in payload order.
        task: The task context and instructions.
    """

    agent_id: str
    skills: tuple[Skill, ...]
    task: Task = field(default_factory=Task)

    @classmethod
    def from_json(cls, data: dict) -> "AgentDefinition":
        """Parse an agent definition from its JSON payload.

        Unknown top-level keys (e.g. future ``hooks`` or ``mcps``) are ignored
        for forward compatibility.

        Args:
            data: The decoded JSON object returned by the agent definition
                service.

        Returns:
            A fully populated, frozen :class:`AgentDefinition`.

        Raises:
            ValidationError: If the payload is malformed.
        """
        agent_id = _parse_agent_id(data.get("agent_id"))
        skills = _parse_skills(data.get("skills"))
        task = _parse_task(data.get("task"))
        return cls(agent_id=agent_id, skills=skills, task=task)


def _parse_agent_id(raw: object) -> str:
    """Validate and default the ``agent_id`` field.

    Args:
        raw: The raw ``agent_id`` value from the payload, if present.

    Returns:
        The agent id, or an empty string when absent.

    Raises:
        ValidationError: If ``agent_id`` is present but not a string.
    """
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise ValidationError(f"agent_id must be a string, got {type(raw).__name__}")
    return raw


def _parse_skills(raw: object) -> tuple[Skill, ...]:
    """Validate and parse the ``skills`` field into a tuple of skills.

    Args:
        raw: The raw ``skills`` value from the payload, if present.

    Returns:
        The parsed skills in payload order; empty when absent or null.

    Raises:
        ValidationError: If ``skills`` is present but not a list, or if any
            skill object is malformed.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValidationError(f"skills must be a list, got {type(raw).__name__}")
    return tuple(_parse_skill(item, index) for index, item in enumerate(raw))


def _parse_skill(raw: object, index: int) -> Skill:
    """Validate and parse a single skill object.

    Args:
        raw: The raw skill object from the payload.
        index: The skill's position in the ``skills`` list, for error messages.

    Returns:
        The parsed :class:`Skill`.

    Raises:
        ValidationError: If the skill object is not a mapping, lacks a
            non-empty string ``name``, or has a non-string ``version``.
    """
    if not isinstance(raw, dict):
        raise ValidationError(f"skills[{index}] must be an object, got {type(raw).__name__}")

    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise ValidationError(f"skills[{index}] must have a non-empty string 'name'")

    version = raw.get("version")
    if version is not None and not isinstance(version, str):
        raise ValidationError(f"skills[{index}] 'version' must be a string or null, got {type(version).__name__}")

    return Skill(name=name, version=version)


def _parse_task(raw: object) -> Task:
    """Validate and parse the optional ``task`` field.

    Args:
        raw: The raw ``task`` value from the payload, if present.

    Returns:
        The parsed :class:`Task`; an empty ``Task`` when absent or null.

    Raises:
        ValidationError: If ``task`` is present but not a mapping, or if its
            ``context`` or ``instructions`` fields are not strings.
    """
    if raw is None:
        return Task()
    if not isinstance(raw, dict):
        raise ValidationError(f"task must be an object, got {type(raw).__name__}")

    context = raw.get("context", "")
    if not isinstance(context, str):
        raise ValidationError(f"task 'context' must be a string, got {type(context).__name__}")

    instructions = raw.get("instructions", "")
    if not isinstance(instructions, str):
        raise ValidationError(f"task 'instructions' must be a string, got {type(instructions).__name__}")

    return Task(context=context, instructions=instructions)
