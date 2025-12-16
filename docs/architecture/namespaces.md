# Namespaces & Cross-Repo Support

ContextFS automatically organizes memories by repository while supporting cross-repo search and project grouping.

## Namespace Hierarchy

```
global
├── repo-abc123 (my-frontend)
│   ├── session-1
│   └── session-2
├── repo-def456 (my-backend)
│   └── session-3
└── repo-ghi789 (shared-lib)
```

### Global Namespace

Memories saved without repo context:

```bash
# Outside any git repo
contextfs save "General preference" --type user
```

### Repository Namespace

Auto-detected from git:

```bash
cd my-project
contextfs save "Project-specific fact"
# Automatically namespaced to repo-{hash}
```

### Session Namespace

Within a conversation session:

```python
ctx.start_session(label="feature-auth")
ctx.log_message("user", "Implement OAuth")
# Messages scoped to this session
```

## Auto-Detection

ContextFS detects repository context automatically:

```python
ctx = ContextFS()

# Walks up from CWD to find .git
# Sets namespace_id = "repo-{sha256(path)[:12]}"
print(ctx.namespace_id)  # "repo-abc123def456"
```

## Cross-Repo Search

Search across all repositories:

```python
# Search only current repo (default)
results = ctx.search("authentication")

# Search all repos
results = ctx.search("authentication", cross_repo=True)
```

### CLI

```bash
# Current repo only
contextfs search "auth"

# All repos (coming soon)
contextfs search "auth" --all-repos
```

### MCP Tool

```json
{
  "tool": "contextfs_search",
  "arguments": {
    "query": "authentication patterns",
    "cross_repo": true
  }
}
```

## Project Grouping

Group memories across repos by project:

```python
# In frontend repo
ctx.save(
    "Frontend uses React 18",
    type=MemoryType.DECISION,
    project="my-saas"
)

# In backend repo
ctx.save(
    "Backend uses FastAPI",
    type=MemoryType.DECISION,
    project="my-saas"
)

# Search by project (from any repo)
results = ctx.search("tech stack", project="my-saas")
```

## Source Tracking

Every memory tracks its origin:

```python
memory = Memory(
    content="...",
    source_repo="my-frontend",      # Repo name
    source_file="src/auth/login.ts", # File path
    source_tool="claude-code",       # Creating tool
    project="my-saas",               # Project group
)
```

### List Repositories

```python
repos = ctx.list_repos()
# [{"name": "my-frontend", "namespace_id": "repo-abc123", ...}]
```

### List Projects

```python
projects = ctx.list_projects()
# [{"name": "my-saas", "memory_count": 42, ...}]
```

### List Source Tools

```python
tools = ctx.list_tools()
# ["claude-code", "claude-desktop", "gemini"]
```

## Namespace Isolation

By default, searches are scoped to the current namespace:

```python
# In frontend repo
ctx = ContextFS()  # namespace = "repo-frontend-hash"

# Only finds frontend memories
results = ctx.search("components")
```

### Explicit Namespace

Override the namespace:

```python
ctx = ContextFS(namespace_id="repo-backend-hash")
# Now searches backend repo
```

### Global Search

Search global namespace only:

```python
ctx = ContextFS(namespace_id="global")
```

## Best Practices

### 1. Use Projects for Related Repos

```python
# Consistent project name across repos
ctx.save(content, project="customer-portal")
```

### 2. Let Auto-Detection Work

Don't override namespace unless necessary:

```python
# Good: let it auto-detect
ctx = ContextFS()

# Avoid: manual namespace unless needed
ctx = ContextFS(namespace_id="custom-ns")
```

### 3. Tag by Scope

Use tags to indicate scope when needed:

```python
ctx.save(
    "Shared authentication library",
    tags=["shared", "auth", "library"]
)
```

### 4. Cross-Repo for Discovery

Use cross-repo search to find related work:

```python
# "Have I solved this before?"
results = ctx.search("rate limiting implementation", cross_repo=True)
```

## Data Model

```python
class Namespace(BaseModel):
    id: str              # "repo-abc123" or "global"
    name: str            # Human-readable name
    parent_id: str | None  # Hierarchy support
    repo_path: str | None  # Absolute path
    created_at: datetime
    metadata: dict

    @classmethod
    def for_repo(cls, repo_path: str) -> Namespace:
        repo_id = sha256(repo_path)[:12]
        return cls(
            id=f"repo-{repo_id}",
            name=repo_path.split("/")[-1],
            repo_path=repo_path,
        )
```
