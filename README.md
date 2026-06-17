# Lamplighter

Lamplighter is an agent harness that prepares a local agent to participate in
coding activities defined by an orchestrator. It reads an **agent definition**
from the orchestrator and bootstraps the local environment the agent needs —
starting with **skills**.

Lamplighter assumes it runs in a **task-scoped, disposable environment** (a
per-task container the orchestrator provisions and discards). Because the box
is dedicated to a single task, orchestrator-managed skills are installed
globally for the agent and overwritten in place on repeated runs.

## How it works

When you run `lamplighter bootstrap`, the harness:

1. Reads the agent id and service URLs from the environment.
2. Requests the agent definition from the **agent definition service**
   (`GET {AGENT_DEFINITION_SERVICE_URL}/agents/{AGENT_ID}`).
3. For each skill named in the definition, fetches the skill's `SKILL.md` text
   from the **document service**
   (`GET {DOCUMENT_SERVICE_URL}/documents/{name}`, with an optional `version`).
4. Installs each skill to `~/.claude/skills/<name>/SKILL.md` so the local agent
   discovers it.

Bootstrap is **fail-fast**: the first fetch or write error aborts the whole run
with a non-zero exit code, so a half-prepared agent never proceeds. Installs
are **idempotent** — re-running overwrites skills in place — and each skill is
written atomically.

> Lamplighter is built in two layers. This release implements the **bootstrap
> layer** (installing skills). A future **launch layer** will drive the agent's
> execution via the [Claude Agent SDK](https://pypi.org/project/claude-agent-sdk/)
> and is where coming-soon agent-definition elements such as **MCP servers** and
> **hooks** will be configured in code. The seam for that work exists in
> `lamplighter.launch` but is not yet implemented.

## Installation

Lamplighter is a Python package (requires Python >= 3.12) managed with
[uv](https://docs.astral.sh/uv/):

```sh
uv sync
```

This installs the package and the `lamplighter` console command into the
project environment. Run commands with `uv run lamplighter …`, or activate the
environment and call `lamplighter` directly.

## Configuration

Lamplighter is configured entirely through environment variables. The three
required variables must be set or the harness exits with code `2` and a message
naming every missing variable.

| Variable | Required | Description |
| --- | --- | --- |
| `AGENT_ID` | Yes | Identifier for the local agent; used to request its agent definition. |
| `AGENT_DEFINITION_SERVICE_URL` | Yes | Base URL of the agent definition service. A trailing slash is normalized away. |
| `DOCUMENT_SERVICE_URL` | Yes | Base URL of the document service. A trailing slash is normalized away. |
| `LAMPLIGHTER_SKILLS_DIR` | No | Install root for skills. Defaults to `~/.claude/skills`. `~` is expanded. |

No authentication is required in this release.

## Usage

```sh
export AGENT_ID="agent-007"
export AGENT_DEFINITION_SERVICE_URL="https://orchestrator.example/agent-definitions"
export DOCUMENT_SERVICE_URL="https://orchestrator.example/documents"

uv run lamplighter bootstrap
```

On success, Lamplighter prints the agent id and the path of each installed
skill, and exits `0`:

```
Bootstrapped agent agent-007
Installed 2 skill(s):
  /home/agent/.claude/skills/diagnose/SKILL.md
  /home/agent/.claude/skills/review/SKILL.md
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success — all named skills were installed. |
| `1` | Bootstrap failed at runtime (a document could not be fetched, or a skill could not be written). |
| `2` | Configuration error — a required environment variable is missing or empty. |

## Service contracts

Lamplighter talks to two orchestrator services. Both are described with
OpenAPI 3.1 in the [`openapi/`](openapi/) directory:

- [`openapi/agent-definition-service.yaml`](openapi/agent-definition-service.yaml) —
  `GET /agents/{agent_id}` returns the agent definition as JSON.
- [`openapi/document-service.yaml`](openapi/document-service.yaml) —
  `GET /documents/{name}` (optional `version` query) returns the raw `SKILL.md`
  text as `text/plain`.

### Agent definition (JSON)

```json
{
  "agent_id": "agent-007",
  "skills": [
    { "name": "diagnose", "version": "1.2.0" },
    { "name": "review" }
  ],
  "task": {
    "context": "Fix the failing build.",
    "instructions": "Run the tests, identify the regression, and patch it."
  }
}
```

- `skills` is a list of objects, each with a required `name` and an optional
  opaque `version`. When `version` is present it is forwarded to the document
  service; when absent, the document service returns the default revision.
- `task` is modeled but not acted on in this release.
- Unknown top-level keys (e.g. future `hooks` or `mcps`) are ignored, so the
  contract can grow without breaking existing clients.

## Development

This repo follows a **thin-wrapper CI** pattern: all check logic lives behind a
single `make ci` command that runs identically on a developer laptop and on
every CI platform.

```sh
make ci      # run the full check suite (pre-commit + ruff + ty + pytest + build)
make py-test # run the test suite only
make help    # list all targets
```

`make ci` runs:

- the [pre-commit](https://pre-commit.com) hooks (formatting, secret
  detection, conventional-commit message checks),
- `ruff` (format check + lint),
- `ty` (type check),
- `pytest` (the test suite — HTTP is mocked with `respx`, so no live network or
  Anthropic credentials are needed), and
- `uv build` (packaging check).

The GitHub Actions and Azure DevOps stubs do nothing more than check out the
code, install the prerequisites (`pre-commit`, `uv`), and run `make ci`. To
change *what* CI does, edit the [`Makefile`](Makefile) and
[`.pre-commit-config.yaml`](.pre-commit-config.yaml) — not the platform YAML.

### Requirements

- [`uv`](https://docs.astral.sh/uv/) for the Python toolchain and environment.
- [`pre-commit`](https://pre-commit.com) and a Python 3.10 interpreter for the
  commit hooks (see the hook requirements below).
- Run `make setup` once to wire up the shared git config and hooks.

> **Why a Python 3.10 interpreter for hooks?** Some pre-commit hooks
> (commitizen, sync-pre-commit-deps) require Python >= 3.10 and are pinned to
> `python3.10` in [`.pre-commit-config.yaml`](.pre-commit-config.yaml). This is
> independent of the package itself, which targets Python >= 3.12. Install a
> 3.10 interpreter (it need not be your default `python3`): `brew install
> python@3.10` (macOS), `sudo apt install python3.10` (Debian/Ubuntu), or
> `pyenv install 3.10`.
