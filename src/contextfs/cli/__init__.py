"""CLI for ContextFS."""

import typer

from contextfs import __version__

from .cloud import cloud_app
from .index import index_app
from .install import install_app
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
)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
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
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


# Register subcommand groups
app.add_typer(memory_app, name="memory")
app.add_typer(index_app, name="index")
app.add_typer(server_app, name="server")
app.add_typer(cloud_app, name="cloud")
app.add_typer(install_app, name="install")

__all__ = ["app", "console", "get_ctx"]


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
