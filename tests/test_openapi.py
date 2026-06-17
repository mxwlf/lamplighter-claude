"""Tests for the orchestrator OpenAPI specifications.

These tests validate the OpenAPI 3.1.0 specs Lamplighter consumes (the agent
definition service and the document service) and confirm the agent-definition
example payload round-trips through the real parser.

PyYAML and openapi-spec-validator are dev dependencies, so the specs are loaded
with ``yaml.safe_load`` and validated with ``openapi_spec_validator.validate``.
"""

from pathlib import Path

import yaml
from openapi_spec_validator import validate

from lamplighter.models import AgentDefinition

_OPENAPI_DIR = Path(__file__).resolve().parent.parent / "openapi"
_AGENT_DEFINITION_SPEC = _OPENAPI_DIR / "agent-definition-service.yaml"
_DOCUMENT_SPEC = _OPENAPI_DIR / "document-service.yaml"


def _load_spec(path: Path) -> dict:
    """Load and parse an OpenAPI spec from YAML.

    Args:
        path: The path to the spec file.

    Returns:
        The parsed spec as a dictionary.
    """
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_agent_definition_openapi_valid():
    """The agent-definition spec is a valid OpenAPI 3.1.0 document."""
    spec = _load_spec(_AGENT_DEFINITION_SPEC)

    validate(spec)

    assert spec["openapi"] == "3.1.0"
    assert "info" in spec
    assert "paths" in spec

    operation = spec["paths"]["/agents/{agent_id}"]["get"]
    assert "200" in operation["responses"]
    assert "404" in operation["responses"]

    # The path parameter is declared and required.
    params = {(p["name"], p["in"]): p for p in operation.get("parameters", [])}
    assert ("agent_id", "path") in params
    assert params[("agent_id", "path")]["required"] is True

    # Reusable component schemas are defined.
    schemas = spec["components"]["schemas"]
    assert "AgentDefinition" in schemas
    assert "Skill" in schemas
    assert "Task" in schemas

    # Forward compatibility: unknown top-level keys are tolerated.
    assert schemas["AgentDefinition"]["additionalProperties"] is True


def test_document_openapi_valid():
    """The document-service spec is a valid OpenAPI 3.1.0 document."""
    spec = _load_spec(_DOCUMENT_SPEC)

    validate(spec)

    assert spec["openapi"] == "3.1.0"
    assert "info" in spec
    assert "paths" in spec

    operation = spec["paths"]["/documents/{name}"]["get"]
    params = {(p["name"], p["in"]): p for p in operation.get("parameters", [])}

    # The path parameter is declared and required.
    assert ("name", "path") in params
    assert params[("name", "path")]["required"] is True

    # The optional version query parameter is present and not required.
    assert ("version", "query") in params
    assert params[("version", "query")]["required"] is False

    # The 200 response is plain text.
    ok_response = operation["responses"]["200"]
    assert "text/plain" in ok_response["content"]
    assert ok_response["content"]["text/plain"]["schema"]["type"] == "string"

    # The 404 response is documented.
    assert "404" in operation["responses"]


def _extract_definition_example(spec: dict) -> dict:
    """Pull the agent-definition example payload out of the spec.

    Prefers the 200 response example, falling back to the schema example.

    Args:
        spec: The parsed agent-definition OpenAPI document.

    Returns:
        The example agent-definition payload.
    """
    operation = spec["paths"]["/agents/{agent_id}"]["get"]
    media = operation["responses"]["200"]["content"]["application/json"]
    if "example" in media:
        return media["example"]
    return spec["components"]["schemas"]["AgentDefinition"]["example"]


def test_definition_schema_matches_model_example():
    """The spec's example payload parses through the real model parser."""
    spec = _load_spec(_AGENT_DEFINITION_SPEC)
    example = _extract_definition_example(spec)

    definition = AgentDefinition.from_json(example)

    assert definition.agent_id == example["agent_id"]
    assert len(definition.skills) == len(example["skills"]) == 2

    # One skill carries a version; the other defaults to None.
    versions = [skill.version for skill in definition.skills]
    assert any(v is not None for v in versions)
    assert any(v is None for v in versions)

    # Skill names round-trip in payload order.
    parsed_names = [skill.name for skill in definition.skills]
    example_names = [skill["name"] for skill in example["skills"]]
    assert parsed_names == example_names

    # The task context and instructions round-trip.
    assert definition.task.context == example["task"]["context"]
    assert definition.task.instructions == example["task"]["instructions"]
