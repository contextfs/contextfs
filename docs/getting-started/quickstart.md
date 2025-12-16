# Quick Start

This guide gets you productive with ContextFS in 5 minutes.

## Core Concepts

ContextFS stores **memories** - pieces of context that persist across sessions:

| Type | Use Case |
|------|----------|
| `fact` | Technical facts, configurations |
| `decision` | Architectural choices, trade-offs |
| `procedural` | How-to guides, workflows |
| `episodic` | Session summaries, events |
| `code` | Code snippets, patterns |
| `error` | Bug fixes, troubleshooting |
| `user` | User preferences |

## Saving Memories

### CLI

```bash
# Basic save
contextfs save "Use pytest for all new tests" --type decision

# With tags
contextfs save "API rate limit is 100 req/min" --type fact --tags api,limits

# With summary
contextfs save "Long detailed content..." --summary "Rate limiting setup" --type procedural
```

### Python

```python
from contextfs import ContextFS, MemoryType

ctx = ContextFS()

# Save with type
ctx.save(
    content="Authentication uses JWT with RS256 signing",
    type=MemoryType.DECISION,
    tags=["auth", "jwt", "security"],
    summary="JWT authentication approach"
)
```

### MCP (Claude Desktop/Code)

In Claude, use the `contextfs_save` tool:

```
Save to memory: We decided to use PostgreSQL for the user database because of its JSON support and reliability.

Type: decision
Tags: database, postgres
```

## Searching Memories

### CLI

```bash
# Semantic search
contextfs search "how does auth work"

# Filter by type
contextfs search "database" --type decision

# Limit results
contextfs search "api" --limit 5
```

### Python

```python
results = ctx.search("authentication flow", limit=5)

for r in results:
    print(f"[{r.score:.2f}] {r.memory.summary or r.memory.content[:50]}")
```

## Indexing Repositories

Index your codebase for semantic code search:

```bash
# Index current repo (auto-detects git root)
contextfs index

# Force re-index
contextfs index --force

# Full re-index (not incremental)
contextfs index --full
```

This creates searchable memories from:

- Source code files
- Documentation
- Git commit history

## Listing & Recalling

```bash
# List recent memories
contextfs list

# Filter by type
contextfs list --type decision

# Recall specific memory by ID
contextfs recall abc123
```

## Sessions

Track conversation sessions:

```python
ctx = ContextFS()

# Start a session
ctx.start_session(label="feature-auth")

# Log messages
ctx.log_message("user", "Implement OAuth login")
ctx.log_message("assistant", "I'll create the OAuth flow...")

# End and save
ctx.end_session(summary="Implemented OAuth with Google provider")
```

## Cross-Repo Search

Search across all your repositories:

```python
# Search all repos
results = ctx.search("authentication", cross_repo=True)

# Filter by project
results = ctx.search("api design", project="my-project")
```

## Next Steps

- [CLI Reference](cli.md) - Full command documentation
- [Architecture](../architecture/overview.md) - How ContextFS works
- [Integration](../integration/claude-desktop.md) - Setup with AI tools
