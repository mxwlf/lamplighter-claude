"""Tests for the agent definition domain models."""

import pytest

from lamplighter.models import AgentDefinition, Skill, Task, ValidationError


def test_parse_full_definition():
    """A complete payload populates agent_id, skills, and task fields."""
    data = {
        "agent_id": "agent-007",
        "skills": [
            {"name": "diagnose", "version": "1.2.0"},
            {"name": "review"},
        ],
        "task": {
            "context": "Fix the failing build.",
            "instructions": "Run the tests and patch the regression.",
        },
    }

    definition = AgentDefinition.from_json(data)

    assert definition.agent_id == "agent-007"
    assert definition.skills == (
        Skill(name="diagnose", version="1.2.0"),
        Skill(name="review", version=None),
    )
    assert definition.task == Task(
        context="Fix the failing build.",
        instructions="Run the tests and patch the regression.",
    )


def test_parse_skill_without_version():
    """A skill with only a name parses with version None."""
    definition = AgentDefinition.from_json({"skills": [{"name": "diagnose"}]})

    assert definition.skills == (Skill(name="diagnose"),)
    assert definition.skills[0].version is None


def test_parse_skill_missing_name_raises():
    """A skill object without a non-empty name raises ValidationError."""
    with pytest.raises(ValidationError):
        AgentDefinition.from_json({"skills": [{"version": "1.0.0"}]})

    with pytest.raises(ValidationError):
        AgentDefinition.from_json({"skills": [{"name": ""}]})


def test_parse_empty_skills_ok():
    """An empty skills list, or an absent skills key, yields no skills."""
    explicit_empty = AgentDefinition.from_json({"skills": []})
    assert explicit_empty.skills == ()

    absent = AgentDefinition.from_json({"agent_id": "agent-007"})
    assert absent.skills == ()


def test_parse_ignores_unknown_keys():
    """Unknown top-level keys are ignored for forward compatibility."""
    data = {
        "agent_id": "agent-007",
        "skills": [{"name": "diagnose"}],
        "hooks": [{"event": "pre-task"}],
        "mcps": {"server": "example"},
    }

    definition = AgentDefinition.from_json(data)

    assert definition.agent_id == "agent-007"
    assert definition.skills == (Skill(name="diagnose"),)


def test_task_modeled_but_optional():
    """An absent task defaults to empty strings; a present task populates it."""
    without_task = AgentDefinition.from_json({"skills": []})
    assert without_task.task == Task()
    assert without_task.task == Task(context="", instructions="")

    with_task = AgentDefinition.from_json(
        {
            "skills": [],
            "task": {"context": "ctx", "instructions": "do it"},
        }
    )
    assert with_task.task == Task(context="ctx", instructions="do it")


def test_parse_skills_not_a_list_raises():
    """A non-list skills value raises ValidationError."""
    with pytest.raises(ValidationError):
        AgentDefinition.from_json({"skills": "oops"})
