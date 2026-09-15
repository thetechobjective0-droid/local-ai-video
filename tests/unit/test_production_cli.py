from typer.main import get_command

from app.production_cli import app


def test_operational_commands_are_exposed() -> None:
    command = get_command(app)

    assert "migrate" in command.commands
    assert "production-gate" in command.commands
    assert "acceptance" in command.commands
    assert "generate-media" in command.commands
