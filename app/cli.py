"""Command-line entry point."""

import typer

from app.health import run_health_checks

app = typer.Typer(help="Local-only AI video generation agent.")


@app.command()
def health() -> None:
    """Run local dependency checks."""
    results = run_health_checks()
    for result in results:
        status = "OK" if result.ok else "MISSING"
        typer.echo(f"[{status}] {result.name}: {result.detail}")


@app.command()
def doctor() -> None:
    """Run the Phase 0 local environment doctor."""
    results = run_health_checks()
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        typer.echo(f"[{status}] {result.name}: {result.detail}")
    if not all(result.ok for result in results):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
