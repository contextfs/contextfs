"""CLI for ContextFS."""

import typer

from contextfs import __version__

from .cloud import cloud_app
from .index import index_app
from .memory import memory_app
from .server import server_app
from .utils import console, get_ctx


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"contextfs {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="contextfs",
    help="ContextFS - Semantic memory for AI agents",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main_callback(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
):
    """ContextFS - Semantic memory for AI agents."""
    pass


# Register top-level commands from memory_app
for command in memory_app.registered_commands:
    app.command(command.name)(command.callback)

# Register top-level commands from index_app
for command in index_app.registered_commands:
    app.command(command.name)(command.callback)

# Register top-level commands from server_app
for command in server_app.registered_commands:
    app.command(command.name)(command.callback)

# Register subcommand groups
app.add_typer(cloud_app, name="cloud")

__all__ = ["app", "console", "get_ctx"]


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
