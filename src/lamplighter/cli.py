"""Console entry point for lamplighter.

This is a scaffold placeholder. The real ``bootstrap`` command is implemented
in Task 8 of the skill-bootstrap plan.
"""

import typer

app = typer.Typer(help="Lamplighter agent harness.")


@app.command()
def bootstrap() -> None:
    """Bootstrap the local agent from its agent definition (placeholder)."""
    raise NotImplementedError("bootstrap is implemented in Task 8")


if __name__ == "__main__":
    app()
