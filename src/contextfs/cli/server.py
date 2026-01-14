"""Server-related CLI commands."""

import shutil
import subprocess
from pathlib import Path

import typer

from .utils import console

server_app = typer.Typer(help="Server commands")


# =============================================================================
# MCP Server Helper Functions
# =============================================================================


def _check_mcp_running(host: str = "127.0.0.1", port: int = 8003) -> dict | None:
    """Check if MCP server is running. Returns status dict or None if not running."""
    import json
    import urllib.error
    import urllib.request

    try:
        url = f"http://{host}:{port}/health"
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode())
            return {"running": True, "status": data.get("status", "ok")}
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _get_mcp_pid(port: int = 8003) -> int | None:
    """Get PID of running MCP server on specified port."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except FileNotFoundError:
        pass

    try:
        result = subprocess.run(
            ["pgrep", "-f", f"contextfs.mcp.server.*{port}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except FileNotFoundError:
        pass

    return None


def _get_mcp_service_paths() -> dict:
    """Get platform-specific service file paths for MCP."""
    import platform

    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        return {
            "platform": "macos",
            "service_file": home / "Library/LaunchAgents/com.contextfs.mcp-server.plist",
            "service_name": "com.contextfs.mcp-server",
        }
    elif system == "Linux":
        return {
            "platform": "linux",
            "service_file": home / ".config/systemd/user/contextfs-mcp.service",
            "service_name": "contextfs-mcp",
        }
    else:
        return {"platform": "unknown"}


def _stop_mcp(port: int = 8003) -> bool:
    """Stop the MCP server."""
    import signal

    pid = _get_mcp_pid(port)
    if pid:
        try:
            import os

            os.kill(pid, signal.SIGTERM)
            return True
        except ProcessLookupError:
            pass
    return False


def _stop_chroma(port: int = 8000) -> bool:
    """Stop the ChromaDB server."""
    import signal

    pid = _get_chroma_pid(port)
    if pid:
        try:
            import os

            os.kill(pid, signal.SIGTERM)
            return True
        except ProcessLookupError:
            pass
    return False


@server_app.command("start")
def start_server(
    service: str = typer.Argument(..., help="Service to start: mcp, chroma"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(None, "--port", "-p", help="Port (default: mcp=8003, chroma=8000)"),
    foreground: bool = typer.Option(False, "--foreground", "-f", help="Run in foreground"),
):
    """Start MCP or ChromaDB server.

    Examples:
        contextfs start mcp               # Start MCP server (background)
        contextfs start chroma            # Start ChromaDB server (background)
        contextfs start mcp -f            # Run MCP in foreground
        contextfs start mcp -p 9000       # Custom port
    """
    if service == "mcp":
        default_port = port or 8003
        if _check_mcp_running(host, default_port):
            pid = _get_mcp_pid(default_port)
            console.print(f"[yellow]MCP server already running on {host}:{default_port}[/yellow]")
            if pid:
                console.print(f"   PID: {pid}")
            return

        if foreground:
            console.print(f"[bold]Starting MCP server on {host}:{default_port}[/bold]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            from contextfs.mcp import run_mcp_server

            run_mcp_server(host=host, port=default_port)
        else:
            import sys

            cmd = [
                sys.executable,
                "-m",
                "contextfs.mcp.server",
                "--host",
                host,
                "--port",
                str(default_port),
            ]
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            console.print(f"[green]MCP server started on {host}:{default_port}[/green]")

    elif service == "chroma":
        default_port = port or 8000
        data_path = Path.home() / ".contextfs" / "chroma_db"

        if _check_chroma_running(host, default_port):
            pid = _get_chroma_pid(default_port)
            console.print(f"[yellow]ChromaDB already running on {host}:{default_port}[/yellow]")
            if pid:
                console.print(f"   PID: {pid}")
            return

        chroma_bin = _find_chroma_bin()
        if not chroma_bin:
            console.print("[red]Error: 'chroma' CLI not found.[/red]")
            console.print("Install it with: pip install chromadb")
            raise typer.Exit(1)

        data_path.mkdir(parents=True, exist_ok=True)
        cmd = [
            chroma_bin,
            "run",
            "--path",
            str(data_path),
            "--host",
            host,
            "--port",
            str(default_port),
        ]

        if foreground:
            console.print(f"[bold]Starting ChromaDB server on {host}:{default_port}[/bold]")
            console.print(f"  Data path: {data_path}")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            try:
                subprocess.run(cmd)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped[/yellow]")
        else:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            console.print(f"[green]ChromaDB server started on {host}:{default_port}[/green]")

    else:
        console.print(f"[red]Unknown service: {service}[/red]")
        console.print("Valid services: mcp, chroma")
        raise typer.Exit(1)


@server_app.command("stop")
def stop_server(
    service: str = typer.Argument(..., help="Service to stop: mcp, chroma, all"),
    port: int = typer.Option(None, "--port", "-p", help="Port (default: mcp=8003, chroma=8000)"),
):
    """Stop MCP or ChromaDB server.

    Examples:
        contextfs stop mcp                # Stop MCP server
        contextfs stop chroma             # Stop ChromaDB server
        contextfs stop all                # Stop both servers
    """
    if service == "mcp" or service == "all":
        mcp_port = port or 8003
        if _stop_mcp(mcp_port):
            console.print(f"[green]MCP server stopped (port {mcp_port})[/green]")
        else:
            console.print(f"[yellow]MCP server not running on port {mcp_port}[/yellow]")

    if service == "chroma" or service == "all":
        chroma_port = port or 8000
        if _stop_chroma(chroma_port):
            console.print(f"[green]ChromaDB server stopped (port {chroma_port})[/green]")
        else:
            console.print(f"[yellow]ChromaDB server not running on port {chroma_port}[/yellow]")

    if service not in ("mcp", "chroma", "all"):
        console.print(f"[red]Unknown service: {service}[/red]")
        console.print("Valid services: mcp, chroma, all")
        raise typer.Exit(1)


@server_app.command("status")
def server_status(
    service: str = typer.Argument(None, help="Service to check: mcp, chroma (default: all)"),
):
    """Check status of MCP and ChromaDB servers.

    Examples:
        contextfs status                  # Check all servers
        contextfs status mcp              # Check MCP only
        contextfs status chroma           # Check ChromaDB only
    """
    services = [service] if service else ["mcp", "chroma"]

    for svc in services:
        if svc == "mcp":
            status = _check_mcp_running()
            if status:
                pid = _get_mcp_pid()
                console.print("[green]MCP server:[/green] running")
                console.print("   URL: http://127.0.0.1:8003/mcp/sse")
                if pid:
                    console.print(f"   PID: {pid}")
                paths = _get_mcp_service_paths()
                if paths["platform"] == "macos" and paths["service_file"].exists():
                    console.print("   Service: launchd (auto-start enabled)")
                elif paths["platform"] == "linux" and paths["service_file"].exists():
                    console.print("   Service: systemd (auto-start enabled)")
            else:
                console.print("[red]MCP server:[/red] not running")
                console.print("   Start with: contextfs start mcp")

        elif svc == "chroma":
            status = _check_chroma_running("127.0.0.1", 8000)
            if status:
                pid = _get_chroma_pid(8000)
                console.print("[green]ChromaDB server:[/green] running")
                console.print("   URL: http://127.0.0.1:8000")
                if pid:
                    console.print(f"   PID: {pid}")
                paths = _get_service_paths()
                if paths["platform"] == "macos" and paths["service_file"].exists():
                    console.print("   Service: launchd (auto-start enabled)")
                elif paths["platform"] == "linux" and paths["service_file"].exists():
                    console.print("   Service: systemd (auto-start enabled)")
            else:
                console.print("[red]ChromaDB server:[/red] not running")
                console.print("   Start with: contextfs start chroma")

        else:
            console.print(f"[red]Unknown service: {svc}[/red]")


@server_app.command("mcp-server")
def mcp_server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8003, "--port", "-p", help="Port to bind to"),
):
    """Start the MCP server (HTTP/SSE transport).

    This starts a single shared MCP service that all Claude Code sessions
    connect to via SSE (Server-Sent Events).

    Configure Claude Code with:
        {"mcpServers": {"contextfs": {"type": "sse", "url": "http://localhost:8003/mcp/sse"}}}

    Examples:
        contextfs mcp-server                # Start on localhost:8003
        contextfs mcp-server -p 8765        # Custom port

    Note: Prefer using 'contextfs start mcp' for background execution.
    """
    from contextfs.mcp import run_mcp_server

    run_mcp_server(host=host, port=port)


@server_app.command("install")
def install(
    target: str = typer.Argument("claude", help="Target: claude, gemini, codex, all"),
    path: Path = typer.Option(None, "--path", "-p", help="Project path for project-level install"),
    user_only: bool = typer.Option(
        False, "--user-only", help="Only install user-level (skip project)"
    ),
    no_service: bool = typer.Option(False, "--no-service", help="Don't install auto-start service"),
    no_start: bool = typer.Option(False, "--no-start", help="Don't start MCP server now"),
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove installation"),
):
    """Install ContextFS for AI coding tools.

    Targets:
        claude  - Claude Code & Desktop (default)
        gemini  - Gemini CLI
        codex   - Codex CLI
        all     - All supported tools

    For Claude, installs:
    - User-level: hooks, commands (/remember, /recall), MCP config
    - Project-level: CLAUDE.md memory protocol (merged, not replaced)
    - Starts MCP server and installs auto-start service

    Examples:
        contextfs install                    # Install for Claude (default)
        contextfs install claude             # Same as above
        contextfs install gemini             # Install for Gemini CLI
        contextfs install all                # Install for all tools
        contextfs install --user-only        # Skip project-level install
        contextfs install --no-service       # Don't install auto-start
        contextfs install --uninstall        # Remove installation
    """
    targets = [target] if target != "all" else ["claude", "gemini", "codex"]

    for t in targets:
        if t == "claude":
            _install_claude(path, user_only, no_service, no_start, uninstall)
        elif t == "gemini":
            _install_gemini(no_service, no_start, uninstall)
        elif t == "codex":
            _install_codex(no_service, no_start, uninstall)
        else:
            console.print(f"[red]Unknown target: {t}[/red]")
            console.print("Valid targets: claude, gemini, codex, all")
            raise typer.Exit(1)


def _install_claude(
    path: Path | None,
    user_only: bool,
    no_service: bool,
    no_start: bool,
    uninstall: bool,
) -> None:
    """Install for Claude Code & Desktop."""
    from contextfs.plugins.claude_code import (
        ClaudeCodePlugin,
        uninstall_claude_code,
        uninstall_claude_code_from_project,
    )

    project_path = path.resolve() if path else Path.cwd()

    if uninstall:
        uninstall_claude_code()
        if not user_only:
            uninstall_claude_code_from_project(project_path)
        console.print("[green]Claude Code installation removed.[/green]")
        return

    plugin = ClaudeCodePlugin(project_path=project_path if not user_only else None)
    plugin.install(include_project=not user_only)

    # Handle service/start options (plugin.install already handles these by default)
    # The no_service and no_start flags would need to be passed to the plugin
    # For now, the plugin always tries to start and install service


def _install_gemini(no_service: bool, no_start: bool, uninstall: bool) -> None:
    """Install for Gemini CLI."""
    from contextfs.plugins.gemini import GeminiPlugin

    if uninstall:
        console.print("[yellow]Gemini uninstall not yet implemented.[/yellow]")
        return

    plugin = GeminiPlugin()
    plugin.install()
    console.print("[green]Gemini CLI integration installed.[/green]")


def _install_codex(no_service: bool, no_start: bool, uninstall: bool) -> None:
    """Install for Codex CLI."""
    from contextfs.plugins.codex import CodexPlugin

    if uninstall:
        console.print("[yellow]Codex uninstall not yet implemented.[/yellow]")
        return

    plugin = CodexPlugin()
    plugin.install()
    console.print("[green]Codex CLI integration installed.[/green]")


@server_app.command("git-hooks")
def git_hooks(
    repo_path: str = typer.Argument(None, help="Repository path (default: current directory)"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing hooks"),
) -> None:
    """Install git hooks for automatic indexing.

    Installs post-commit and post-merge hooks that automatically
    run incremental indexing after commits and pulls.

    Examples:
        contextfs git-hooks              # Install to current repo
        contextfs git-hooks /path/to/repo
        contextfs git-hooks --force      # Overwrite existing hooks
    """
    # Determine target repo
    target = Path(repo_path).resolve() if repo_path else Path.cwd()

    # Verify it's a git repo
    git_dir = target / ".git"
    if not git_dir.exists():
        console.print(f"[red]Error: {target} is not a git repository[/red]")
        raise typer.Exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    # Find source hooks (bundled with package)
    import contextfs

    pkg_dir = Path(contextfs.__file__).parent.parent.parent
    source_hooks_dir = pkg_dir / "hooks"

    # If not found in package, create hooks inline
    hooks = {
        "post-commit": """#!/bin/bash
# ContextFS Post-Commit Hook - Auto-index on commit
set -e
if command -v contextfs &> /dev/null; then
    CONTEXTFS="contextfs"
elif [ -f "$HOME/.local/bin/contextfs" ]; then
    CONTEXTFS="$HOME/.local/bin/contextfs"
else
    exit 0
fi
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
(cd "$REPO_ROOT" && $CONTEXTFS index --incremental --mode files_only --quiet 2>/dev/null &) &
exit 0
""",
        "post-merge": """#!/bin/bash
# ContextFS Post-Merge Hook - Auto-index on pull/merge
set -e
if command -v contextfs &> /dev/null; then
    CONTEXTFS="contextfs"
elif [ -f "$HOME/.local/bin/contextfs" ]; then
    CONTEXTFS="$HOME/.local/bin/contextfs"
else
    exit 0
fi
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
(cd "$REPO_ROOT" && $CONTEXTFS index --incremental --quiet 2>/dev/null &) &
exit 0
""",
    }

    console.print(f"Installing ContextFS git hooks to: [cyan]{target}[/cyan]\n")

    for hook_name, hook_content in hooks.items():
        hook_path = hooks_dir / hook_name
        source_path = source_hooks_dir / hook_name if source_hooks_dir.exists() else None

        # Check if hook exists
        if hook_path.exists() and not force:
            console.print(f"  [yellow]{hook_name}:[/yellow] exists (use --force to overwrite)")
            continue

        # Backup existing hook
        if hook_path.exists():
            backup_path = hooks_dir / f"{hook_name}.bak"
            shutil.copy(hook_path, backup_path)
            console.print(f"  [dim]{hook_name}: backed up to {hook_name}.bak[/dim]")

        # Write hook (prefer source file if available)
        if source_path and source_path.exists():
            shutil.copy(source_path, hook_path)
        else:
            hook_path.write_text(hook_content)

        # Make executable
        hook_path.chmod(0o755)
        console.print(f"  [green]{hook_name}:[/green] installed")

    console.print("\n[green]Done![/green] ContextFS will auto-index on:")
    console.print("  - git commit (indexes changed files)")
    console.print("  - git pull/merge (indexes new files and commits)")


# =============================================================================
# ChromaDB Server Helper Functions
# =============================================================================


def _check_chroma_running(host: str, port: int) -> dict | None:
    """Check if ChromaDB server is running. Returns status dict or None if not running."""
    import json
    import urllib.error
    import urllib.request

    try:
        url = f"http://{host}:{port}/api/v2/heartbeat"
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode())
            return {"running": True, "heartbeat": data.get("nanosecond heartbeat")}
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _get_chroma_pid(port: int) -> int | None:
    """Get PID of running chroma process on specified port."""
    try:
        # Try lsof first (macOS/Linux)
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except FileNotFoundError:
        pass

    try:
        # Fallback: pgrep for chroma run
        result = subprocess.run(
            ["pgrep", "-f", f"chroma run.*{port}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except FileNotFoundError:
        pass

    return None


def _find_chroma_bin() -> str | None:
    """Find the chroma CLI executable."""
    import sys

    chroma_bin = shutil.which("chroma")
    if chroma_bin:
        return chroma_bin

    # Try to find it relative to the Python executable (e.g., in same venv)
    python_dir = Path(sys.executable).parent
    possible_paths = [
        python_dir / "chroma",
        python_dir.parent / "bin" / "chroma",
    ]
    for p in possible_paths:
        if p.exists():
            return str(p)

    return None


def _get_service_paths() -> dict:
    """Get platform-specific service file paths."""
    import platform

    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        return {
            "platform": "macos",
            "service_file": home / "Library/LaunchAgents/com.contextfs.chromadb.plist",
            "service_name": "com.contextfs.chromadb",
        }
    elif system == "Linux":
        return {
            "platform": "linux",
            "service_file": home / ".config/systemd/user/contextfs-chromadb.service",
            "service_name": "contextfs-chromadb",
        }
    elif system == "Windows":
        return {
            "platform": "windows",
            "service_name": "ContextFS-ChromaDB",
        }
    else:
        return {"platform": "unknown"}


def _install_macos_service(host: str, port: int, data_path: Path, chroma_bin: str) -> bool:
    """Install launchd service on macOS."""
    import plistlib

    paths = _get_service_paths()
    plist_path = paths["service_file"]
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    plist_content = {
        "Label": paths["service_name"],
        "ProgramArguments": [
            chroma_bin,
            "run",
            "--path",
            str(data_path),
            "--host",
            host,
            "--port",
            str(port),
        ],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(Path.home() / ".contextfs/logs/chromadb.log"),
        "StandardErrorPath": str(Path.home() / ".contextfs/logs/chromadb.err"),
    }

    # Ensure log directory exists
    (Path.home() / ".contextfs/logs").mkdir(parents=True, exist_ok=True)

    with open(plist_path, "wb") as f:
        plistlib.dump(plist_content, f)

    # Load the service
    subprocess.run(["launchctl", "load", str(plist_path)], check=True)
    return True


def _install_linux_service(host: str, port: int, data_path: Path, chroma_bin: str) -> bool:
    """Install systemd user service on Linux."""
    paths = _get_service_paths()
    service_path = paths["service_file"]
    service_path.parent.mkdir(parents=True, exist_ok=True)

    service_content = f"""[Unit]
Description=ChromaDB Server for ContextFS
After=network.target

[Service]
Type=simple
ExecStart={chroma_bin} run --path {data_path} --host {host} --port {port}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""

    service_path.write_text(service_content)

    # Enable and start the service
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", paths["service_name"]], check=True)
    subprocess.run(["systemctl", "--user", "start", paths["service_name"]], check=True)
    return True


def _install_windows_service(host: str, port: int, data_path: Path, chroma_bin: str) -> bool:
    """Install Windows Task Scheduler task."""
    paths = _get_service_paths()
    task_name = paths["service_name"]

    # Create XML for scheduled task
    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>ChromaDB Server for ContextFS</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions>
    <Exec>
      <Command>{chroma_bin}</Command>
      <Arguments>run --path {data_path} --host {host} --port {port}</Arguments>
    </Exec>
  </Actions>
</Task>
"""

    # Write temp XML file and import
    temp_xml = Path.home() / ".contextfs" / "chromadb_task.xml"
    temp_xml.parent.mkdir(parents=True, exist_ok=True)
    temp_xml.write_text(xml_content, encoding="utf-16")

    subprocess.run(
        ["schtasks", "/create", "/tn", task_name, "/xml", str(temp_xml), "/f"],
        check=True,
    )
    temp_xml.unlink()

    # Start the task now
    subprocess.run(["schtasks", "/run", "/tn", task_name], check=True)
    return True


def _uninstall_service() -> bool:
    """Uninstall the service for the current platform."""
    paths = _get_service_paths()
    platform = paths["platform"]

    if platform == "macos":
        plist_path = paths["service_file"]
        if plist_path.exists():
            subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
            plist_path.unlink()
        return True
    elif platform == "linux":
        service_path = paths["service_file"]
        if service_path.exists():
            subprocess.run(["systemctl", "--user", "stop", paths["service_name"]], check=False)
            subprocess.run(["systemctl", "--user", "disable", paths["service_name"]], check=False)
            service_path.unlink()
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        return True
    elif platform == "windows":
        subprocess.run(["schtasks", "/delete", "/tn", paths["service_name"], "/f"], check=False)
        return True
    return False


@server_app.command("chroma-server")
def chroma_server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    data_path: Path = typer.Option(
        None, "--path", help="ChromaDB data path (default: ~/.contextfs/chroma_db)"
    ),
    background: bool = typer.Option(False, "--daemon", "-d", help="Run in background"),
    status: bool = typer.Option(False, "--status", "-s", help="Check server status"),
    install: bool = typer.Option(
        False, "--install", help="Install as system service (auto-start on boot)"
    ),
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove system service"),
):
    """Start ChromaDB server for multi-process access.

    Running ChromaDB as a server prevents corruption from concurrent access.
    All ContextFS instances connect to this server instead of using embedded mode.

    After starting the server, set CONTEXTFS_CHROMA_HOST=localhost in your
    environment or add chroma_host: localhost to your config.

    Examples:
        contextfs chroma-server                    # Start on localhost:8000
        contextfs chroma-server -p 8001            # Custom port
        contextfs chroma-server --daemon           # Run in background
        contextfs chroma-server --status           # Check if running
        contextfs chroma-server --install          # Install as system service
        contextfs chroma-server --uninstall        # Remove system service
    """
    # Default data path
    if data_path is None:
        data_path = Path.home() / ".contextfs" / "chroma_db"

    # Handle --status
    if status:
        server_status = _check_chroma_running(host, port)
        if server_status:
            pid = _get_chroma_pid(port)
            console.print("[green]ChromaDB server is running[/green]")
            console.print(f"   URL: http://{host}:{port}")
            if pid:
                console.print(f"   PID: {pid}")

            # Check if installed as service
            paths = _get_service_paths()
            if paths["platform"] == "macos" and paths["service_file"].exists():
                console.print("   Service: launchd (auto-start enabled)")
            elif paths["platform"] == "linux" and paths["service_file"].exists():
                console.print("   Service: systemd (auto-start enabled)")
        else:
            console.print("[red]ChromaDB server is not running[/red]")
            console.print("   Start with: contextfs chroma-server --daemon")
        return

    # Handle --uninstall
    if uninstall:
        console.print("Removing ChromaDB service...")
        if _uninstall_service():
            console.print("[green]Service removed[/green]")
        else:
            console.print("[yellow]No service found or unsupported platform[/yellow]")
        return

    # Find chroma binary (needed for start and install)
    chroma_bin = _find_chroma_bin()
    if not chroma_bin:
        console.print("[red]Error: 'chroma' CLI not found.[/red]")
        console.print("Install it with: pip install chromadb")
        raise typer.Exit(1)

    data_path.mkdir(parents=True, exist_ok=True)

    # Handle --install
    if install:
        # Check if already running
        if _check_chroma_running(host, port):
            console.print(f"[yellow]ChromaDB already running on {host}:{port}[/yellow]")

        paths = _get_service_paths()
        platform = paths["platform"]

        console.print(f"Installing ChromaDB service for {platform}...")

        try:
            if platform == "macos":
                _install_macos_service(host, port, data_path, chroma_bin)
            elif platform == "linux":
                _install_linux_service(host, port, data_path, chroma_bin)
            elif platform == "windows":
                _install_windows_service(host, port, data_path, chroma_bin)
            else:
                console.print(f"[red]Unsupported platform: {platform}[/red]")
                console.print("Use Docker instead: docker-compose --profile with-chromadb up -d")
                raise typer.Exit(1)

            console.print("[green]Service installed and started[/green]")
            console.print("   ChromaDB will auto-start on boot")
            console.print()
            console.print("[green]To use server mode, set:[/green]")
            console.print(f"  export CONTEXTFS_CHROMA_HOST={host}")
            console.print(f"  export CONTEXTFS_CHROMA_PORT={port}")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to install service: {e}[/red]")
            raise typer.Exit(1)
        return

    # Check if already running before starting
    if _check_chroma_running(host, port):
        pid = _get_chroma_pid(port)
        console.print(f"[yellow]ChromaDB already running on {host}:{port}[/yellow]")
        if pid:
            console.print(f"   PID: {pid}")
        console.print()
        console.print("[green]To use server mode, set:[/green]")
        console.print(f"  export CONTEXTFS_CHROMA_HOST={host}")
        console.print(f"  export CONTEXTFS_CHROMA_PORT={port}")
        return

    console.print("[bold]ChromaDB Server[/bold]")
    console.print(f"  Data path: {data_path}")
    console.print(f"  Listening: http://{host}:{port}")
    console.print()
    console.print("[green]To use server mode, set:[/green]")
    console.print(f"  export CONTEXTFS_CHROMA_HOST={host}")
    console.print(f"  export CONTEXTFS_CHROMA_PORT={port}")
    console.print()

    # Build the chroma run command
    cmd = [
        chroma_bin,
        "run",
        "--path",
        str(data_path),
        "--host",
        host,
        "--port",
        str(port),
    ]

    if background:
        # Start in background
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        console.print("[green]ChromaDB server started in background[/green]")
        console.print("   PID can be found with: pgrep -f 'chroma run'")
    else:
        # Run in foreground
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped[/yellow]")
