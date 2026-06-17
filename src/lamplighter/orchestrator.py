"""HTTP client for the orchestrator services.

Lamplighter reads two orchestrator endpoints: the agent definition service,
which returns an agent definition as JSON keyed by agent id, and the document
service, which returns the raw text of a named document (e.g. a skill's
``SKILL.md`` body). This module wraps both behind :class:`OrchestratorClient`
and normalizes every failure into :class:`OrchestratorError`.
"""

import httpx

from .config import Config
from .models import AgentDefinition


class OrchestratorError(Exception):
    """Raised when an orchestrator service request fails (non-2xx or transport error).

    Attributes:
        resource: Human-readable description of the resource being fetched,
            e.g. ``"agent definition agent-123"`` or ``"document tdd"``.
        status_code: The HTTP status code for non-2xx responses, or ``None``
            for transport/network/timeout or parsing errors.
    """

    def __init__(self, message: str, *, resource: str, status_code: int | None = None) -> None:
        """Build an OrchestratorError carrying request context.

        Args:
            message: A description of what went wrong.
            resource: The resource being fetched when the error occurred.
            status_code: The HTTP status code, or ``None`` when not applicable.
        """
        super().__init__(message)
        self.resource = resource
        self.status_code = status_code


class OrchestratorClient:
    """Client for the orchestrator's agent definition and document services."""

    def __init__(self, config: Config, *, client: httpx.Client | None = None) -> None:
        """Store config and an httpx client.

        Args:
            config: Resolved configuration carrying the service base URLs.
            client: An optional injected :class:`httpx.Client`. When ``None``,
                an internal client is created. Injecting a client aids testing
                and connection reuse.
        """
        self._config = config
        self._client = client if client is not None else httpx.Client()

    def get_agent_definition(self, agent_id: str) -> AgentDefinition:
        """Fetch and parse the agent definition for ``agent_id``.

        Issues ``GET {agent_definition_service_url}/agents/{agent_id}`` and
        parses the JSON body via :meth:`AgentDefinition.from_json`.

        Args:
            agent_id: The identifier of the agent whose definition to fetch.

        Returns:
            The parsed :class:`AgentDefinition`.

        Raises:
            OrchestratorError: If the response is non-2xx, the transport fails,
                or the body cannot be decoded/validated as an agent definition.
        """
        base = self._config.agent_definition_service_url
        url = f"{base.rstrip('/')}/agents/{agent_id}"
        resource = f"agent definition {agent_id}"

        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OrchestratorError(
                f"Failed to fetch {resource}: HTTP {exc.response.status_code}",
                resource=resource,
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            raise OrchestratorError(
                f"Failed to fetch {resource}: {exc}",
                resource=resource,
                status_code=None,
            ) from exc

        try:
            data = response.json()
            return AgentDefinition.from_json(data)
        except Exception as exc:
            raise OrchestratorError(
                f"Failed to parse {resource}: {exc}",
                resource=resource,
                status_code=None,
            ) from exc

    def get_document(self, name: str, version: str | None = None) -> str:
        """Fetch the raw text of a named document.

        Issues ``GET {document_service_url}/documents/{name}``, adding a
        ``version`` query parameter only when ``version`` is not ``None``.

        Args:
            name: The document name to fetch.
            version: An optional version selector; when ``None`` no query
                parameter is sent.

        Returns:
            The raw response text, returned verbatim.

        Raises:
            OrchestratorError: If the response is non-2xx or the transport
                fails.
        """
        base = self._config.document_service_url
        url = f"{base.rstrip('/')}/documents/{name}"
        resource = f"document {name}"
        params = {"version": version} if version is not None else None

        try:
            response = self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OrchestratorError(
                f"Failed to fetch {resource}: HTTP {exc.response.status_code}",
                resource=resource,
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            raise OrchestratorError(
                f"Failed to fetch {resource}: {exc}",
                resource=resource,
                status_code=None,
            ) from exc

        return response.text
