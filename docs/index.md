# ContextFS

<p align="center" style="font-size: 1.4em; color: #666;">
<strong>Universal AI Memory Layer</strong><br>
Cross-client, cross-repo context management with semantic search
</p>

---

<div class="grid cards" markdown>

-   :material-brain:{ .lg .middle } __Semantic Memory__

    ---

    Store and retrieve context using semantic search powered by ChromaDB and sentence transformers.

    [:octicons-arrow-right-24: Architecture](architecture/overview.md)

-   :material-source-repository-multiple:{ .lg .middle } __Cross-Repo__

    ---

    Memories are automatically namespaced by repository, with support for cross-repo search and project grouping.

    [:octicons-arrow-right-24: Namespaces](architecture/namespaces.md)

-   :material-robot:{ .lg .middle } __Multi-Client__

    ---

    Works with Claude Desktop, Claude Code, Gemini, ChatGPT, and any MCP-compatible client.

    [:octicons-arrow-right-24: Integration](integration/claude-desktop.md)

-   :material-console:{ .lg .middle } __CLI & MCP__

    ---

    Full-featured CLI for memory management plus MCP server for AI tool integration.

    [:octicons-arrow-right-24: CLI Reference](getting-started/cli.md)

</div>

## Installation

=== "pip"

    ```bash
    pip install contextfs
    ```

=== "uv"

    ```bash
    uv pip install contextfs
    ```

=== "pipx"

    ```bash
    pipx install contextfs
    ```

## Quick Example

```python
from contextfs import ContextFS

# Initialize (auto-detects current repo)
ctx = ContextFS()

# Save a memory
ctx.save(
    content="Authentication uses JWT tokens with 24h expiry",
    type="decision",
    tags=["auth", "security"]
)

# Search memories
results = ctx.search("how does authentication work?")
for r in results:
    print(f"{r.score:.2f}: {r.memory.content}")
```

## CLI Usage

```bash
# Save a memory
contextfs save "API uses REST with JSON responses" --type decision --tags api,design

# Search memories
contextfs search "API design patterns"

# Index a repository
contextfs index

# List recent memories
contextfs list
```

## Why ContextFS?

Modern AI development involves multiple tools, repositories, and long-running projects. ContextFS solves the **context fragmentation problem**:

- **Memory across sessions**: Don't repeat yourself to AI tools
- **Memory across tools**: Share context between Claude, Gemini, and others
- **Memory across repos**: Find related decisions from other projects
- **Semantic search**: Natural language queries over your entire context history

## Theoretical Foundation

ContextFS is built on principles from [Type-Safe Context Engineering](research/typesafe-context.md), applying insights from protein folding and type theory to AI memory systems.

---

<p align="center">
<a href="https://github.com/MagnetonIO/contextfs">GitHub</a> ·
<a href="https://pypi.org/project/contextfs/">PyPI</a> ·
MIT License
</p>
