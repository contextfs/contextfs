"""Install CLI commands for agent integrations."""

import json
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

install_app = typer.Typer(
    name="install",
    help="Install ContextFS integrations for coding agents",
    no_args_is_help=True,
)

# Template directory (relative to this file)
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _get_template_path(template: str) -> Path:
    """Get the path to a template file."""
    return TEMPLATES_DIR / template


def _ensure_dir(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def _copy_template(src: Path, dest: Path, quiet: bool = False) -> bool:
    """Copy a template file, backing up if exists."""
    if dest.exists():
        # Create backup
        backup = dest.with_suffix(dest.suffix + ".bak")
        shutil.copy2(dest, backup)
        if not quiet:
            console.print(f"  [dim]Backed up: {dest.name} -> {backup.name}[/dim]")

    shutil.copy2(src, dest)
    return True


@install_app.command("claude")
def install_claude(
    global_only: bool = typer.Option(
        False, "--global", "-g", help="Only install global skills and MCP"
    ),
    project_only: bool = typer.Option(False, "--project", "-p", help="Only install project hooks"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing files without backup"
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """Install ContextFS integration for Claude Code.

    This command installs:
    - Global skills: ~/.claude/commands/remember.md, recall.md
    - Project hooks: .claude/settings.local.json
    - Project agents: .claude/agents/memory-extractor.md
    - MCP server configuration in ~/.claude.json

    Examples:
        contextfs install claude           # Full installation
        contextfs install claude --global  # Only global skills + MCP
        contextfs install claude --project # Only project hooks
    """
    installed = []
    skipped = []

    # Global skills
    if not project_only:
        global_claude_dir = Path.home() / ".claude"
        global_commands_dir = global_claude_dir / "commands"
        _ensure_dir(global_commands_dir)

        # Install remember.md
        remember_src = _get_template_path("commands/remember.md")
        remember_dest = global_commands_dir / "remember.md"
        if remember_src.exists():
            _copy_template(remember_src, remember_dest, quiet)
            installed.append(("Global skill", str(remember_dest)))
        else:
            skipped.append(("remember.md", "Template not found"))

        # Install recall.md
        recall_src = _get_template_path("commands/recall.md")
        recall_dest = global_commands_dir / "recall.md"
        if recall_src.exists():
            _copy_template(recall_src, recall_dest, quiet)
            installed.append(("Global skill", str(recall_dest)))
        else:
            skipped.append(("recall.md", "Template not found"))

    # Project hooks and agents
    if not global_only:
        project_claude_dir = Path.cwd() / ".claude"
        _ensure_dir(project_claude_dir)

        # Install hooks (settings.local.json)
        hooks_src = _get_template_path("hooks.json")
        hooks_dest = project_claude_dir / "settings.local.json"

        if hooks_src.exists():
            # Load template and modify structure
            with open(hooks_src) as f:
                hooks_config = json.load(f)

            # Write to project
            if hooks_dest.exists() and not force:
                # Merge with existing
                with open(hooks_dest) as f:
                    existing = json.load(f)
                # Deep merge hooks
                if "hooks" not in existing:
                    existing["hooks"] = {}
                for hook_type, hook_list in hooks_config.get("hooks", {}).items():
                    if hook_type not in existing["hooks"]:
                        existing["hooks"][hook_type] = hook_list
                    # else: keep existing hooks
                with open(hooks_dest, "w") as f:
                    json.dump(existing, f, indent=2)
                    f.write("\n")
                installed.append(("Project hooks", f"{hooks_dest} (merged)"))
            else:
                with open(hooks_dest, "w") as f:
                    json.dump(hooks_config, f, indent=2)
                    f.write("\n")
                installed.append(("Project hooks", str(hooks_dest)))

        # Install agents
        agents_dir = project_claude_dir / "agents"
        _ensure_dir(agents_dir)

        agent_src = _get_template_path("agents/memory-extractor.md")
        agent_dest = agents_dir / "memory-extractor.md"
        if agent_src.exists():
            _copy_template(agent_src, agent_dest, quiet)
            installed.append(("Project agent", str(agent_dest)))

        # Install project commands (copy from global)
        commands_dir = project_claude_dir / "commands"
        _ensure_dir(commands_dir)

        for cmd_file in ["remember.md", "recall.md"]:
            cmd_src = _get_template_path(f"commands/{cmd_file}")
            cmd_dest = commands_dir / cmd_file
            if cmd_src.exists():
                _copy_template(cmd_src, cmd_dest, quiet)
                installed.append(("Project skill", str(cmd_dest)))

    # MCP server configuration (always installed unless project_only)
    if not project_only:
        mcp_config_path = Path.home() / ".claude.json"
        if mcp_config_path.exists():
            with open(mcp_config_path) as f:
                claude_config = json.load(f)
        else:
            claude_config = {}

        if "mcpServers" not in claude_config:
            claude_config["mcpServers"] = {}

        # Add contextfs MCP server (SSE/HTTP mode)
        claude_config["mcpServers"]["contextfs"] = {
            "type": "sse",
            "url": "http://127.0.0.1:8003/mcp/sse",
        }

        with open(mcp_config_path, "w") as f:
            json.dump(claude_config, f, indent=2)
            f.write("\n")

        installed.append(("MCP server", str(mcp_config_path)))

    # Output summary
    if not quiet:
        if installed:
            console.print("\n[green]ContextFS installed for Claude Code![/green]\n")

            table = Table(title="Installed Components")
            table.add_column("Type", style="cyan")
            table.add_column("Location")

            for item_type, location in installed:
                table.add_row(item_type, location)

            console.print(table)

            console.print("\n[bold]Next steps:[/bold]")
            console.print("  1. Restart Claude Code to load hooks and MCP server")
            console.print("  2. Use /remember to save memories")
            console.print("  3. Use /recall to search memories")
            console.print(
                "  4. MCP tools (contextfs_save, contextfs_search, etc.) are now available"
            )
        else:
            console.print("[yellow]Nothing installed[/yellow]")

        if skipped:
            console.print("\n[yellow]Skipped:[/yellow]")
            for name, reason in skipped:
                console.print(f"  {name}: {reason}")
    else:
        if installed:
            print(f"Installed {len(installed)} components for Claude Code")


@install_app.command("cursor")
def install_cursor(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """Install ContextFS integration for Cursor IDE.

    Coming soon - Cursor IDE integration.
    """
    if not quiet:
        console.print("[yellow]Cursor IDE integration coming soon![/yellow]")
        console.print("\nPlanned features:")
        console.print("  - Custom rules for ContextFS")
        console.print("  - Memory search integration")
        console.print("  - Auto-save on file changes")


@install_app.command("windsurf")
def install_windsurf(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """Install ContextFS integration for Windsurf.

    Coming soon - Windsurf integration.
    """
    if not quiet:
        console.print("[yellow]Windsurf integration coming soon![/yellow]")
        console.print("\nPlanned features:")
        console.print("  - Cascade memory integration")
        console.print("  - Flow context enhancement")


@install_app.command("list")
def list_agents():
    """List available agent integrations."""
    console.print("\n[bold]Available Agent Integrations[/bold]\n")

    table = Table()
    table.add_column("Agent", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Description")

    table.add_row(
        "claude", "[green]Available[/green]", "Claude Code CLI integration with hooks and skills"
    )
    table.add_row("cursor", "[yellow]Coming Soon[/yellow]", "Cursor IDE integration")
    table.add_row("windsurf", "[yellow]Coming Soon[/yellow]", "Windsurf integration")
    table.add_row("vscode", "[dim]Planned[/dim]", "VS Code extension")
    table.add_row("jetbrains", "[dim]Planned[/dim]", "JetBrains IDE plugin")

    console.print(table)
    console.print("\n[dim]Use 'contextfs install <agent>' to install[/dim]")


@install_app.command("status")
def install_status():
    """Check installation status for all integrations."""
    console.print("\n[bold]ContextFS Installation Status[/bold]\n")

    # Check Claude Code
    global_commands = Path.home() / ".claude" / "commands"
    claude_config = Path.home() / ".claude.json"

    claude_items = []

    # Global skills
    for skill in ["remember.md", "recall.md"]:
        skill_path = global_commands / skill
        if skill_path.exists():
            claude_items.append((f"Global skill: {skill}", "[green]Installed[/green]"))
        else:
            claude_items.append((f"Global skill: {skill}", "[red]Missing[/red]"))

    # Project hooks
    project_hooks = Path.cwd() / ".claude" / "settings.local.json"
    if project_hooks.exists():
        claude_items.append(("Project hooks", "[green]Installed[/green]"))
    else:
        claude_items.append(("Project hooks", "[yellow]Not installed[/yellow]"))

    # MCP server
    if claude_config.exists():
        try:
            with open(claude_config) as f:
                config = json.load(f)
            if "contextfs" in config.get("mcpServers", {}):
                claude_items.append(("MCP server", "[green]Configured[/green]"))
            else:
                claude_items.append(("MCP server", "[yellow]Not configured[/yellow]"))
        except Exception:
            claude_items.append(("MCP server", "[red]Config error[/red]"))
    else:
        claude_items.append(("MCP server", "[dim]No Claude config[/dim]"))

    # Display
    table = Table(title="Claude Code")
    table.add_column("Component", style="cyan")
    table.add_column("Status")

    for component, status in claude_items:
        table.add_row(component, status)

    console.print(table)

    # Suggestions
    missing = [c for c, s in claude_items if "Missing" in s or "Not installed" in s]
    if missing:
        console.print("\n[yellow]To complete installation:[/yellow]")
        console.print("  contextfs install claude")
