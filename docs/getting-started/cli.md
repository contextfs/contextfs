# CLI Reference

ContextFS provides a full-featured command-line interface. The main command is `contextfs` with a short alias `ctx`.

## Commands

### `contextfs save`

Save a memory to the store.

```bash
contextfs save CONTENT [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--type, -t` | Memory type: fact, decision, procedural, episodic, code, error, user |
| `--tags` | Comma-separated tags |
| `--summary, -s` | Brief summary |

**Examples:**

```bash
contextfs save "Use React 18 with TypeScript" --type decision --tags frontend,react

contextfs save "Deploy with: docker compose up -d" --type procedural --summary "Deployment command"
```

### `contextfs search`

Search memories using semantic similarity.

```bash
contextfs search QUERY [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit, -n` | Maximum results (default: 10) |
| `--type, -t` | Filter by memory type |

**Examples:**

```bash
contextfs search "how to deploy"
contextfs search "database" --type decision --limit 5
```

### `contextfs index`

Index a repository for semantic code search.

```bash
contextfs index [PATH] [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--force, -f` | Force re-index even if already indexed |
| `--incremental/--full` | Incremental (default) or full re-index |

**Examples:**

```bash
# Index current repo
contextfs index

# Index specific path
contextfs index /path/to/repo

# Force full re-index
contextfs index --force --full
```

### `contextfs list`

List recent memories.

```bash
contextfs list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit, -n` | Maximum results (default: 10) |
| `--type, -t` | Filter by memory type |

### `contextfs recall`

Recall a specific memory by ID.

```bash
contextfs recall MEMORY_ID
```

The ID can be partial (first 8 characters).

### `contextfs delete`

Delete a memory.

```bash
contextfs delete MEMORY_ID [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--yes, -y` | Skip confirmation |

### `contextfs sessions`

List recent sessions.

```bash
contextfs sessions [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit, -n` | Maximum results (default: 10) |
| `--tool` | Filter by tool (claude-code, gemini, etc.) |
| `--label` | Filter by label |

### `contextfs status`

Show ContextFS status and statistics.

```bash
contextfs status
```

Displays:
- Data directory location
- Current namespace
- Memory counts by type
- Vector store statistics
- Active session info

### `contextfs init`

Initialize ContextFS in a directory.

```bash
contextfs init [PATH]
```

Creates a `.contextfs/` directory and updates `.gitignore`.

### `contextfs serve`

Start the MCP server.

```bash
contextfs serve
```

Typically not run directly - used by Claude Desktop integration.

### `contextfs web`

Start the web UI server.

```bash
contextfs web [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--host, -h` | Host to bind (default: 127.0.0.1) |
| `--port, -p` | Port to bind (default: 8000) |

### `contextfs install-claude-desktop`

Install/uninstall MCP server for Claude Desktop.

```bash
contextfs install-claude-desktop [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--uninstall` | Remove from Claude Desktop |

### `contextfs save-session`

Save session for use with hooks.

```bash
contextfs save-session [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--label, -l` | Session label |
| `--transcript, -t` | Path to transcript JSONL file |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONTEXTFS_DATA_DIR` | Data storage directory | `~/.contextfs` |
| `CONTEXTFS_SOURCE_TOOL` | Tool identifier | auto-detect |
| `CONTEXTFS_EMBEDDING_MODEL` | Embedding model | `all-MiniLM-L6-v2` |

## Shell Completion

Install shell completion:

```bash
# Bash
contextfs --install-completion bash

# Zsh
contextfs --install-completion zsh

# Fish
contextfs --install-completion fish
```
