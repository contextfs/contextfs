# Developer Memory Workflow (DMW) Guide

**The Complete Guide to AI-Native Development with Persistent Context**

---

## Table of Contents

1. [Introduction: What is AI-Native Development?](#introduction-what-is-ai-native-development)
2. [Understanding Developer Memory Workflow](#understanding-developer-memory-workflow)
3. [Core Concepts](#core-concepts)
4. [Getting Started](#getting-started)
5. [Solo Developer Workflows](#solo-developer-workflows)
6. [Team Workflows](#team-workflows)
7. [Memory Types Deep Dive](#memory-types-deep-dive)
8. [Session Management](#session-management)
9. [Best Practices](#best-practices)
10. [Common Patterns](#common-patterns)
11. [Advanced Topics](#advanced-topics)
12. [Troubleshooting](#troubleshooting)

---

## Introduction: What is AI-Native Development?

### The Problem with Traditional AI Assistants

If you've used ChatGPT, Claude, or other AI assistants for coding, you've likely experienced this frustration:

> **Day 1:** "We decided to use PostgreSQL with SQLAlchemy for the database layer."
>
> **Day 2:** "What database are we using?" → AI has no idea.

Traditional AI assistants are **stateless**. Every conversation starts fresh. This means:

- You constantly re-explain your project architecture
- Decisions made yesterday are forgotten today
- Context from one session doesn't carry to the next
- Team knowledge stays locked in individual conversations

### The AI-Native Development Paradigm

**AI-Native Development** is a new approach where AI assistants become true collaborators with **persistent memory**:

```
Traditional Development          AI-Native Development
─────────────────────────────    ─────────────────────────────
Human remembers everything       Human + AI share memory
AI forgets after each session    Decisions persist across sessions
Context lost between tools       Context flows between tools
Knowledge stays in heads         Knowledge stored and searchable
```

### What Changes with Persistent Memory?

| Before | After |
|--------|-------|
| "We use React" (every session) | AI already knows your stack |
| Re-explaining auth decisions | AI recalls JWT choice and why |
| Forgetting bug fix patterns | Searchable error solutions |
| Lost architectural context | Decisions with rationale preserved |
| Onboarding takes weeks | New devs query project memory |

---

## Understanding Developer Memory Workflow

### What is DMW?

**Developer Memory Workflow (DMW)** is a methodology for building and maintaining a persistent knowledge base that AI assistants can access. It transforms AI from a stateless tool into a context-aware collaborator.

Think of DMW as **version control for decisions** - just as Git tracks code changes, DMW tracks the *why* behind your code.

### The Memory Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE MEMORY LIFECYCLE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐│
│    │  CAPTURE │───▶│  STORE   │───▶│  SEARCH  │───▶│  APPLY   ││
│    └──────────┘    └──────────┘    └──────────┘    └──────────┘│
│         │               │               │               │       │
│    Decisions       Typed &         Semantic          Context    │
│    Errors          Tagged          Retrieval         Injection  │
│    Patterns        Indexed         Cross-repo        Into AI    │
│    Sessions        Embedded        By project        Prompts    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Capture Early, Capture Often**
   - Save decisions when you make them, not later
   - Document errors when you fix them
   - Record patterns as you discover them

2. **Type Your Memories**
   - Different memory types serve different purposes
   - Types enable smarter search and retrieval
   - Structured data is more useful than raw notes

3. **Tag for Discovery**
   - Tags create connections between memories
   - Consistent tagging enables powerful queries
   - Tags should reflect how you'll search later

4. **Search Before Implementing**
   - Always check existing knowledge first
   - Prior decisions should inform new ones
   - Avoid repeating solved problems

---

## Core Concepts

### Memory vs. Session vs. Namespace

Understanding these three concepts is essential:

#### Memory

A **memory** is a single piece of knowledge with metadata:

```python
Memory(
    content="Use bcrypt with cost factor 12 for password hashing",
    type=MemoryType.DECISION,
    tags=["security", "auth", "passwords"],
    summary="Password hashing standard",
    source_tool="claude-code",        # Which AI tool created it
    source_repo="backend-api",        # Which repo it came from
    project="my-saas"                 # Project grouping
)
```

#### Session

A **session** is a conversation with message history:

```python
Session(
    id="abc123",
    tool="claude-code",               # claude-code, claude-desktop, gemini, etc.
    label="auth-implementation",      # Human-readable label
    messages=[...],                   # User/assistant exchanges
    summary="Implemented OAuth2 with PKCE flow",  # Auto-generated
    started_at=datetime(...),
    ended_at=datetime(...)
)
```

Sessions capture the *journey* - how you arrived at decisions. Memories capture the *destination* - the decisions themselves.

#### Namespace

A **namespace** isolates memories by context:

```
~/.contextfs/
├── namespaces/
│   ├── repo-abc123/          # Repository A's memories
│   ├── repo-def456/          # Repository B's memories
│   └── global/               # Shared across all repos
```

By default, each git repository gets its own namespace. This prevents cross-contamination while allowing explicit sharing via projects.

### The Memory Type System

ContextFS uses a type system to categorize memories:

| Type | Purpose | When to Use |
|------|---------|-------------|
| `fact` | Immutable truths | API keys locations, conventions, configurations |
| `decision` | Choices with rationale | Architecture, library selection, trade-offs |
| `code` | Reusable patterns | Algorithms, boilerplate, snippets |
| `error` | Problem solutions | Bug fixes, error resolutions, workarounds |
| `procedural` | Step-by-step guides | Deployment, setup, workflows |
| `episodic` | Historical records | Session summaries, meeting notes |
| `user` | User preferences | Personal settings, workflows |

### Source Tool Tracking

ContextFS tracks which AI tool created each memory:

- `claude-code` - Claude Code CLI
- `claude-desktop` - Claude Desktop app
- `gemini` - Gemini CLI
- `codex` - OpenAI Codex CLI
- Custom tools via `CONTEXTFS_SOURCE_TOOL` env var

This enables filtering: "Show me decisions made in Claude Desktop last week"

---

## Getting Started

### Installation

```bash
# Quick start with uvx (no install needed)
uvx contextfs --help

# Or install permanently
pip install contextfs

# Or with uv
uv pip install contextfs
```

### Your First Memory

Let's save your first memory:

```bash
# Via CLI
contextfs save "This project uses Python 3.11 with FastAPI" \
    --type fact \
    --tags python,fastapi,stack

# Via MCP (in Claude Code/Desktop)
# Just tell the AI:
"Save to memory: We're using Python 3.11 with FastAPI. Type: fact, Tags: python, fastapi, stack"
```

### Your First Search

```bash
# Via CLI
contextfs search "what framework are we using"

# Via MCP
"Search our memory for framework decisions"
```

### Understanding the Output

```
[0.89] [fact] @backend-api
  This project uses Python 3.11 with FastAPI
  Tags: python, fastapi, stack
```

- `[0.89]` - Relevance score (0-1)
- `[fact]` - Memory type
- `@backend-api` - Source repository
- Content and tags follow

---

## Solo Developer Workflows

### Why Solo Devs Need DMW

Even working alone, you face challenges:

- **Context switching**: Returning to a project after weeks
- **Decision amnesia**: Forgetting *why* you chose something
- **Repeated research**: Solving the same problems twice
- **Lost experiments**: Forgetting what you tried before

DMW solves these by creating your personal knowledge base.

### The Solo Dev Daily Workflow

#### Morning Startup

```python
# 1. Check what you were working on
contextfs sessions --limit 5

# 2. Load yesterday's session context
contextfs load-session <session-id>

# 3. Search for relevant context
contextfs search "current task" --type procedural
```

#### During Development

```python
# When you make a decision
ctx.save(
    "Using Redis for session storage instead of JWT cookies - "
    "better for horizontal scaling",
    type=MemoryType.DECISION,
    tags=["sessions", "redis", "scaling"]
)

# When you fix a bug
ctx.save(
    "CORS preflight failing: needed explicit Access-Control-Max-Age header",
    type=MemoryType.ERROR,
    tags=["cors", "api", "headers"]
)

# When you discover a pattern
ctx.save(
    '''async def retry_with_backoff(fn, max_retries=3):
        for i in range(max_retries):
            try:
                return await fn()
            except Exception as e:
                if i == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** i)
    ''',
    type=MemoryType.CODE,
    tags=["async", "retry", "patterns"]
)
```

#### End of Day

```python
# Save session with summary
ctx.save(
    save_session="current",
    label="auth-feature-day-2"
)

# Or via MCP:
"Save this session to memory with label 'auth-feature-day-2'"
```

### Solo Dev Project Structure

Organize your memories by project phase:

```
Project Memory Structure
========================

📁 Architecture Phase
├── [decision] Database choice: PostgreSQL
├── [decision] API style: REST with OpenAPI
├── [decision] Auth: JWT with refresh tokens
└── [fact] Tech stack: Python 3.11, FastAPI, SQLAlchemy

📁 Implementation Phase
├── [code] Base repository pattern
├── [code] Custom exception hierarchy
├── [error] SQLAlchemy async session handling
└── [procedural] Local dev environment setup

📁 Deployment Phase
├── [procedural] Docker build process
├── [decision] Kubernetes vs ECS (chose ECS)
├── [error] Health check timeout issues
└── [fact] Production environment variables
```

### The Solo Dev Memory Checklist

Use this checklist during development:

- [ ] **New project?** Save tech stack decisions
- [ ] **Chose a library?** Save why you chose it over alternatives
- [ ] **Fixed a tricky bug?** Save the error and solution
- [ ] **Wrote reusable code?** Save the pattern
- [ ] **Set up something complex?** Save the procedure
- [ ] **End of session?** Save session summary

### Solo Dev Tips

1. **Be verbose in decisions**

   Bad: "Using Redis"

   Good: "Using Redis for session storage instead of database-backed sessions. Reasons: 1) Horizontal scaling without sticky sessions, 2) Sub-millisecond reads, 3) Built-in TTL for session expiry. Trade-off: Additional infrastructure to manage."

2. **Tag for future you**

   Think: "What will I search for in 6 months?"

   Tags should be: specific (`sqlalchemy`), categorical (`orm`), and contextual (`async-issues`)

3. **Create procedural memories for complex setups**

   If it took you an hour to figure out, write it down:

   ```python
   ctx.save(
       """Local Kubernetes Setup:
       1. Install minikube: brew install minikube
       2. Start cluster: minikube start --memory=4096
       3. Enable ingress: minikube addons enable ingress
       4. Set context: kubectl config use-context minikube
       5. Load local images: eval $(minikube docker-env)
       """,
       type=MemoryType.PROCEDURAL,
       tags=["kubernetes", "local-dev", "setup"]
   )
   ```

---

## Team Workflows

### Why Teams Need DMW

Team development amplifies the memory problem:

- **Knowledge silos**: "Only Sarah knows how auth works"
- **Onboarding friction**: New devs ask the same questions
- **Decision archaeology**: "Why did we build it this way?"
- **Context loss**: When team members leave
- **Duplicate solutions**: Different people solving the same problems

DMW creates a **shared brain** for the team.

### Team Architecture Options

#### Option 1: Shared Namespace (Small Teams)

Best for: 2-5 developers, single project

```json
// All team members use the same namespace
{
  "mcpServers": {
    "contextfs": {
      "command": "contextfs-mcp",
      "env": {
        "CONTEXTFS_NAMESPACE": "team-project-x"
      }
    }
  }
}
```

Pros:
- Simple setup
- Everyone sees everything
- Real-time knowledge sharing

Cons:
- No privacy for experiments
- Can get noisy with many devs

#### Option 2: Project-Based Sharing (Medium Teams)

Best for: 5-15 developers, multiple projects

```python
# Each dev has their own namespace, but shares via projects
ctx.save(
    "API rate limiting: 1000 req/min per user, 10000 req/min per org",
    type=MemoryType.DECISION,
    project="api-platform",  # Shared across team
    tags=["api", "rate-limiting", "security"]
)

# Search across project (from any repo)
results = ctx.search("rate limiting", project="api-platform")
```

Pros:
- Balance of private and shared
- Organized by logical projects
- Cross-repo knowledge sharing

Cons:
- Requires project discipline
- More setup overhead

#### Option 3: Sync to Central Database (Large Teams)

Best for: 15+ developers, enterprise

```bash
# Configure PostgreSQL sync
export CONTEXTFS_POSTGRES_URL="postgresql://..."
export CONTEXTFS_SYNC_INTERVAL=300  # 5 minutes

# Or enable in config
contextfs config set sync.enabled true
contextfs config set sync.postgres_url "postgresql://..."
```

Pros:
- Centralized knowledge base
- Full-text search across org
- Backup and compliance
- Analytics and insights

Cons:
- Infrastructure overhead
- Sync latency
- More complex setup

### Team Roles and Responsibilities

#### Memory Champion (Rotating Role)

Each sprint, assign a Memory Champion who:

- Reviews new memories for quality
- Ensures consistent tagging
- Identifies knowledge gaps
- Cleans up outdated memories
- Onboards new team members to DMW

#### Suggested Team Conventions

**Tagging Convention:**

```
# Layer tags
api, frontend, backend, database, infra

# Domain tags
auth, payments, users, notifications

# Status tags
deprecated, experimental, production

# Type-specific tags
bug-fix, security-fix, performance
```

**Decision Template:**

```python
# Team decision template
ctx.save(
    f"""## {title}

**Context:** {what_problem_were_we_solving}

**Decision:** {what_we_decided}

**Alternatives Considered:**
- {alt_1}: {why_rejected}
- {alt_2}: {why_rejected}

**Consequences:**
- {positive_consequence}
- {trade_off}

**Participants:** {who_was_involved}
**Date:** {when_decided}
""",
    type=MemoryType.DECISION,
    tags=[...],
    project="team-project"
)
```

### Team Workflow: Feature Development

#### 1. Feature Kickoff

```python
# Tech lead saves architectural decision
ctx.save(
    """## User Preferences Feature Architecture

    **Approach:** Event-sourced preferences with CQRS

    **Components:**
    - PreferenceCommand: Write model (Kafka)
    - PreferenceQuery: Read model (Redis cache)
    - PreferenceProjection: Sync service

    **Why:** User prefs are high-read, low-write.
    Event sourcing gives audit trail for compliance.
    """,
    type=MemoryType.DECISION,
    tags=["user-prefs", "architecture", "event-sourcing"],
    project="mobile-app"
)
```

#### 2. Implementation Phase

Each developer saves discoveries:

```python
# Developer A: Found an edge case
ctx.save(
    "User preferences: Handle null timezone gracefully - "
    "default to UTC, don't throw. Mobile clients send null "
    "on first launch before location permission.",
    type=MemoryType.ERROR,
    tags=["user-prefs", "timezone", "mobile"],
    project="mobile-app"
)

# Developer B: Created reusable code
ctx.save(
    '''class PreferenceCache:
        """Redis-backed preference cache with write-through."""

        def __init__(self, redis: Redis, ttl: int = 3600):
            self.redis = redis
            self.ttl = ttl

        async def get(self, user_id: str) -> dict:
            cached = await self.redis.get(f"prefs:{user_id}")
            if cached:
                return json.loads(cached)
            return await self._fetch_and_cache(user_id)
    ''',
    type=MemoryType.CODE,
    tags=["user-prefs", "caching", "redis"],
    project="mobile-app"
)
```

#### 3. Code Review Integration

Before reviewing, search for context:

```python
# In PR description or review
"Relevant memories for this PR:"
results = ctx.search("user preferences caching", project="mobile-app")
```

#### 4. Feature Completion

```python
# Save feature summary
ctx.save(
    """## User Preferences Feature - Complete

    **Shipped:** 2024-01-15
    **Team:** Alice (lead), Bob, Carol

    **What we built:**
    - Event-sourced preference storage
    - Redis cache with 1hr TTL
    - Real-time sync via WebSocket

    **Lessons learned:**
    - Kafka partition key should be user_id for ordering
    - Mobile null-handling is critical
    - Cache invalidation needs explicit events

    **Metrics:**
    - P99 read latency: 12ms (was 150ms)
    - Write throughput: 10k/sec
    """,
    type=MemoryType.EPISODIC,
    tags=["user-prefs", "feature-complete", "retrospective"],
    project="mobile-app"
)
```

### Team Onboarding with DMW

New team member workflow:

```python
# Day 1: Architecture overview
results = ctx.search("architecture overview", type=MemoryType.DECISION)
results = ctx.search("tech stack", type=MemoryType.FACT)

# Day 2: Development setup
results = ctx.search("local development setup", type=MemoryType.PROCEDURAL)
results = ctx.search("environment variables", type=MemoryType.FACT)

# Day 3: Key decisions
results = ctx.search("why we chose", type=MemoryType.DECISION)

# Day 4: Common issues
results = ctx.search("", type=MemoryType.ERROR, limit=20)

# Day 5: Code patterns
results = ctx.search("", type=MemoryType.CODE, limit=20)
```

### Team Memory Hygiene

#### Weekly Maintenance (Memory Champion)

```python
# Find stale memories
old_memories = ctx.list_recent(limit=100)
for m in old_memories:
    if m.created_at < datetime.now() - timedelta(days=90):
        # Review for relevance
        if is_outdated(m):
            ctx.update(m.id, tags=[*m.tags, "deprecated"])
```

#### Quarterly Review

1. **Audit decision memories**: Are they still accurate?
2. **Update procedural memories**: Do setups still work?
3. **Archive old errors**: Move solved issues to archive
4. **Refresh code patterns**: Update to current best practices

---

## Memory Types Deep Dive

### `fact` - Immutable Truths

**What:** Configuration, conventions, and stable truths about your project.

**When to use:**
- Environment configurations
- API endpoint documentation
- Coding conventions
- External service details

**Examples:**

```python
# Good facts
ctx.save(
    "Production database: PostgreSQL 15 on AWS RDS, "
    "instance: db.r6g.xlarge, region: us-east-1",
    type=MemoryType.FACT,
    tags=["database", "production", "aws"]
)

ctx.save(
    "API versioning: URL path-based (/v1/, /v2/), "
    "never breaking changes within a version",
    type=MemoryType.FACT,
    tags=["api", "versioning", "conventions"]
)

ctx.save(
    "Code style: Black formatter, 88 char line length, "
    "isort for imports, no type comments (use annotations)",
    type=MemoryType.FACT,
    tags=["code-style", "python", "formatting"]
)
```

**Best practices:**
- Keep facts atomic (one fact per memory)
- Update facts when they change (don't create duplicates)
- Use specific tags for filtering

### `decision` - Choices with Rationale

**What:** Architectural and technical decisions with the reasoning behind them.

**When to use:**
- Technology choices
- Architecture patterns
- Trade-off resolutions
- Policy decisions

**The ADR Format:**

```python
ctx.save(
    """## ADR-001: Use PostgreSQL over MongoDB

    **Status:** Accepted
    **Date:** 2024-01-10

    **Context:**
    We need a database for user data including profiles,
    preferences, and activity logs. Data is relational
    with complex queries needed for analytics.

    **Decision:**
    Use PostgreSQL 15 with the following setup:
    - Primary for writes, read replicas for analytics
    - JSONB columns for flexible schema portions
    - TimescaleDB extension for time-series activity data

    **Alternatives Considered:**

    1. MongoDB
       - Pro: Flexible schema, easy horizontal scaling
       - Con: Complex transactions, weaker consistency guarantees
       - Rejected: Our data is fundamentally relational

    2. MySQL
       - Pro: Widely understood, good performance
       - Con: Weaker JSON support, less advanced features
       - Rejected: PostgreSQL's JSONB and extensions better fit

    **Consequences:**
    - Team needs PostgreSQL expertise (training planned)
    - Can leverage existing RDS infrastructure
    - Must design schema carefully upfront
    - Analytics queries will be faster than document DB
    """,
    type=MemoryType.DECISION,
    tags=["database", "postgresql", "architecture", "adr"],
    project="backend-platform"
)
```

**Best practices:**
- Always include the "why" not just the "what"
- Document rejected alternatives
- Note trade-offs and consequences
- Use a consistent format (ADR recommended)

### `code` - Reusable Patterns

**What:** Code snippets, algorithms, and patterns worth remembering.

**When to use:**
- Solved a complex algorithm
- Created reusable utility code
- Discovered a useful pattern
- Wrote boilerplate you'll need again

**Examples:**

```python
# Algorithm pattern
ctx.save(
    '''def exponential_backoff(
        func: Callable,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ) -> Any:
        """
        Retry a function with exponential backoff.

        Args:
            func: Function to retry (should raise on failure)
            max_retries: Maximum retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay cap
            exponential_base: Base for exponential calculation
            jitter: Add randomness to prevent thundering herd

        Returns:
            Result of successful function call

        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e

                if attempt == max_retries - 1:
                    raise

                delay = min(
                    base_delay * (exponential_base ** attempt),
                    max_delay
                )

                if jitter:
                    delay *= (0.5 + random.random())

                time.sleep(delay)

        raise last_exception
    ''',
    type=MemoryType.CODE,
    tags=["retry", "backoff", "resilience", "patterns"],
    summary="Exponential backoff with jitter for retries"
)

# Utility pattern
ctx.save(
    '''from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database transactions.

    Usage:
        async with transaction(session) as tx:
            tx.add(user)
            tx.add(profile)
        # Auto-commits on success, rolls back on exception
    """
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    ''',
    type=MemoryType.CODE,
    tags=["sqlalchemy", "async", "transactions", "patterns"],
    summary="Async transaction context manager for SQLAlchemy"
)
```

**Best practices:**
- Include docstrings explaining usage
- Add type hints for clarity
- Show example usage in comments
- Tag with both specific and general terms

### `error` - Problem Solutions

**What:** Bugs encountered and how you fixed them.

**When to use:**
- Fixed a confusing bug
- Solved an error message
- Found a workaround
- Debugged a tricky issue

**Error Memory Format:**

```python
ctx.save(
    """## Error: SQLAlchemy DetachedInstanceError

    **Symptom:**
    `sqlalchemy.orm.exc.DetachedInstanceError: Instance <User at 0x...>
    is not bound to a Session`

    **Context:**
    Accessing lazy-loaded relationship after session closed.
    Happened in FastAPI background task.

    **Root Cause:**
    FastAPI dependency injection closes session after response.
    Background tasks run after response, session is gone.

    **Solution:**
    ```python
    # Option 1: Eager load what you need
    user = await session.execute(
        select(User)
        .options(selectinload(User.preferences))
        .where(User.id == user_id)
    )

    # Option 2: Create new session in background task
    @app.post("/action")
    async def action(background_tasks: BackgroundTasks):
        background_tasks.add_task(do_work)  # Gets own session

    # Option 3: Use expire_on_commit=False (careful!)
    async_session = sessionmaker(expire_on_commit=False)
    ```

    **Prevention:**
    - Always eager load relationships needed after response
    - Background tasks should create their own sessions
    - Consider the session lifecycle in async code
    """,
    type=MemoryType.ERROR,
    tags=["sqlalchemy", "async", "detached-instance", "fastapi"]
)
```

**Best practices:**
- Include the exact error message
- Describe the context where it occurred
- Explain the root cause
- Provide the solution with code
- Add prevention tips

### `procedural` - Step-by-Step Guides

**What:** Instructions for completing multi-step tasks.

**When to use:**
- Development environment setup
- Deployment procedures
- Complex configurations
- Troubleshooting workflows

**Examples:**

```python
ctx.save(
    """## Local Development Setup (macOS)

    ### Prerequisites
    - Homebrew installed
    - Docker Desktop running
    - Python 3.11+

    ### Steps

    1. **Clone and setup:**
       ```bash
       git clone git@github.com:company/backend.git
       cd backend
       python -m venv venv
       source venv/bin/activate
       pip install -e ".[dev]"
       ```

    2. **Start infrastructure:**
       ```bash
       docker compose up -d postgres redis
       # Wait for healthy status
       docker compose ps
       ```

    3. **Configure environment:**
       ```bash
       cp .env.example .env
       # Edit .env with your settings:
       # - DATABASE_URL=postgresql://...
       # - REDIS_URL=redis://localhost:6379
       ```

    4. **Initialize database:**
       ```bash
       alembic upgrade head
       python scripts/seed_dev_data.py
       ```

    5. **Run the server:**
       ```bash
       uvicorn app.main:app --reload --port 8000
       ```

    6. **Verify:**
       - API docs: http://localhost:8000/docs
       - Health check: http://localhost:8000/health

    ### Common Issues

    - **Port 5432 in use:** `docker compose down` or check for local Postgres
    - **Migration fails:** Ensure DATABASE_URL is correct in .env
    - **Import errors:** Re-run `pip install -e ".[dev]"`
    """,
    type=MemoryType.PROCEDURAL,
    tags=["setup", "local-dev", "macos", "onboarding"]
)
```

**Best practices:**
- Number the steps clearly
- Include verification steps
- Add common issues section
- Keep updated as process changes

### `episodic` - Historical Records

**What:** Records of events, sessions, and historical context.

**When to use:**
- Session summaries
- Meeting notes
- Sprint retrospectives
- Incident post-mortems

**Examples:**

```python
ctx.save(
    """## Incident Post-Mortem: API Outage 2024-01-15

    **Duration:** 14:30 - 15:45 UTC (75 minutes)
    **Severity:** P1 - Complete API unavailability
    **Customers Affected:** ~10,000

    ### Timeline
    - 14:30 - PagerDuty alert: API latency > 5s
    - 14:35 - On-call confirmed issue, escalated
    - 14:45 - Identified: Database connection pool exhausted
    - 15:00 - Root cause: Leaked connections from new feature
    - 15:15 - Hotfix deployed: Connection timeout added
    - 15:45 - Full recovery confirmed

    ### Root Cause
    New user sync feature opened DB connections in loop without
    closing them. Connection pool (max 100) exhausted in ~30 min
    under normal load.

    ### Resolution
    1. Immediate: Restart API servers to clear pool
    2. Hotfix: Add connection context manager
    3. Follow-up: Add connection pool monitoring

    ### Action Items
    - [ ] Add DB connection metrics to dashboard
    - [ ] Code review checklist for DB operations
    - [ ] Load test new features before deploy
    - [ ] Reduce connection pool timeout (30s → 10s)

    ### Lessons Learned
    - Connection leaks are silent until catastrophic
    - Need better visibility into pool utilization
    - New features need load testing gate
    """,
    type=MemoryType.EPISODIC,
    tags=["incident", "post-mortem", "database", "outage"]
)
```

---

## Session Management

### Understanding Sessions

Sessions capture the flow of a conversation - every message, decision, and discovery. They provide:

- **Continuity**: Resume where you left off
- **Context**: Understand how decisions evolved
- **Audit trail**: Track what was discussed
- **Learning**: Review past problem-solving approaches

### Session Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   START     │────▶│   ACTIVE    │────▶│    END      │
│             │     │             │     │             │
│ start_      │     │ add_        │     │ end_        │
│ session()   │     │ message()   │     │ session()   │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   SAVED     │
                    │             │
                    │ Searchable  │
                    │ Loadable    │
                    └─────────────┘
```

### Session Operations

#### Starting Sessions

```python
# Automatic (recommended) - MCP auto-starts sessions
# Just start using contextfs tools

# Manual with label
ctx.start_session(tool="claude-code", label="auth-refactor")

# MCP command
"Start a new session labeled 'auth-refactor'"
```

#### Logging Messages

```python
# Automatic - MCP logs tool calls automatically

# Manual logging for important exchanges
ctx.add_message("user", "Should we use JWTs or sessions?")
ctx.add_message("assistant", "Given your requirements, JWTs with...")

# MCP command
contextfs_message(role="user", content="Key decision point...")
```

#### Ending Sessions

```python
# With auto-summary
ctx.end_session(generate_summary=True)

# MCP command
"Save this session to memory with label 'auth-complete'"
```

#### Loading Previous Sessions

```python
# List recent sessions
sessions = ctx.list_sessions(limit=10)

# Load specific session
session = ctx.load_session(session_id="abc123")

# MCP commands
"Show my recent sessions"
"Load the session from yesterday about database design"
```

### Session Best Practices

1. **Label meaningful sessions**

   ```python
   # Good labels
   "auth-implementation-day-1"
   "bug-fix-cors-issue"
   "feature-user-prefs-design"

   # Bad labels
   "session-1"
   "work"
   "stuff"
   ```

2. **Save before context switch**

   Before switching to different work:
   ```
   "Save this session before I switch to the frontend work"
   ```

3. **Reference sessions in decisions**

   ```python
   ctx.save(
       "Chose event sourcing for audit requirements. "
       "See session 'audit-design-discussion' for full context.",
       type=MemoryType.DECISION,
       tags=["audit", "event-sourcing"]
   )
   ```

4. **Import external conversations**

   ```python
   # Import from Claude Desktop export
   ctx.import_conversation(
       json_content=exported_json,
       summary="OAuth design discussion from Desktop",
       tags=["oauth", "design", "imported"]
   )
   ```

---

## Best Practices

### The Memory-First Mindset

Train yourself to think: "Should I save this?"

**Save when you:**
- Make a decision (even small ones)
- Fix a bug that took > 5 minutes
- Write code you might reuse
- Figure out something confusing
- Complete a complex setup
- Finish a feature or milestone

**Don't save:**
- Trivial code changes
- Temporary debugging notes
- Personal todos (use a todo app)
- Sensitive credentials (use secrets manager)

### Writing Effective Memories

#### Be Specific and Searchable

```python
# Bad - too vague
ctx.save("Fixed the bug")

# Good - specific and searchable
ctx.save(
    "Fixed null pointer in UserService.getPreferences() - "
    "user.settings was null for new users without onboarding",
    type=MemoryType.ERROR,
    tags=["null-pointer", "user-service", "preferences", "onboarding"]
)
```

#### Include Context

```python
# Bad - no context
ctx.save("Use retry with backoff")

# Good - full context
ctx.save(
    "External payment API is flaky (~2% timeout rate). "
    "Implemented exponential backoff: base=1s, max=30s, retries=5. "
    "This gives 99.97% success rate per our SLA requirements.",
    type=MemoryType.DECISION,
    tags=["payments", "retry", "reliability", "external-api"]
)
```

#### Use Consistent Structure

Create templates for common memory types:

```python
# Decision template
DECISION_TEMPLATE = """
## {title}

**Context:** {why_we_needed_to_decide}

**Decision:** {what_we_decided}

**Alternatives:** {what_else_we_considered}

**Trade-offs:** {pros_and_cons}
"""

# Error template
ERROR_TEMPLATE = """
## {error_name}

**Error:** {exact_error_message}

**Context:** {when_and_where_it_happened}

**Cause:** {root_cause}

**Solution:** {how_to_fix}
```
"""
```

### Tagging Strategy

#### Tag Categories

1. **Domain tags**: `auth`, `payments`, `users`, `notifications`
2. **Technology tags**: `postgresql`, `redis`, `fastapi`, `react`
3. **Layer tags**: `api`, `database`, `frontend`, `infrastructure`
4. **Status tags**: `deprecated`, `experimental`, `production-ready`
5. **Action tags**: `bug-fix`, `performance`, `security`, `refactor`

#### Tagging Rules

- Use lowercase, hyphenated tags: `user-auth` not `UserAuth`
- Be consistent: pick `db` or `database`, not both
- Use 3-7 tags per memory (enough to find, not overwhelming)
- Include both specific and general: `postgresql` AND `database`

### Search Strategies

#### Natural Language Search

```python
# ContextFS understands natural queries
ctx.search("how do we handle authentication")
ctx.search("database connection issues")
ctx.search("deployment process for production")
```

#### Filtered Search

```python
# By type
ctx.search("authentication", type=MemoryType.DECISION)

# By project
ctx.search("api design", project="mobile-app")

# By source
ctx.search("cors", source_tool="claude-code")

# Combined
ctx.search(
    "performance",
    type=MemoryType.ERROR,
    project="backend",
    limit=10
)
```

#### Browse Recent

```python
# Recent by type
ctx.list_recent(type=MemoryType.DECISION, limit=20)

# Recent by repo
ctx.list_recent(source_repo="frontend", limit=10)
```

---

## Common Patterns

### Pattern 1: The Decision Log

Keep a running log of architectural decisions:

```python
# In CLAUDE.md or project setup
"""
When making architectural decisions, save them with:
- Type: decision
- Tags: architecture, adr, {domain}
- Format: ADR template
"""

# Example workflow
"We need to decide on a message queue.
 Save the decision once we choose."

# After discussion
ctx.save(
    """## ADR-007: Message Queue Selection

    **Decision:** Use AWS SQS over RabbitMQ

    **Rationale:**
    - Managed service reduces ops burden
    - Pay-per-use fits our variable load
    - Native AWS integration with Lambda

    **Trade-offs:**
    - Less feature-rich than RabbitMQ
    - Vendor lock-in
    - Max message size 256KB
    """,
    type=MemoryType.DECISION,
    tags=["architecture", "adr", "messaging", "aws", "sqs"]
)
```

### Pattern 2: The Bug Journal

Track bugs and solutions systematically:

```python
# When you fix a bug
ctx.save(
    """## Bug: Infinite Loop in WebSocket Reconnection

    **Symptom:** Browser tab freezes, 100% CPU

    **Cause:** Reconnection logic didn't have backoff,
    server rejecting fast enough to cause tight loop

    **Fix:**
    ```javascript
    let reconnectDelay = 1000;
    const maxDelay = 30000;

    function reconnect() {
        setTimeout(() => {
            connect();
            reconnectDelay = Math.min(reconnectDelay * 2, maxDelay);
        }, reconnectDelay);
    }
    ```

    **Prevention:** Always use backoff for reconnection logic
    """,
    type=MemoryType.ERROR,
    tags=["websocket", "reconnection", "infinite-loop", "frontend"]
)
```

### Pattern 3: The Setup Playbook

Document complex setups step by step:

```python
ctx.save(
    """## AWS ECS Deployment Setup

    ### Prerequisites
    - AWS CLI configured with appropriate IAM role
    - Docker image pushed to ECR
    - ECS cluster created

    ### Steps

    1. Create task definition:
       ```bash
       aws ecs register-task-definition \
         --cli-input-json file://task-definition.json
       ```

    2. Create service:
       ```bash
       aws ecs create-service \
         --cluster prod-cluster \
         --service-name api-service \
         --task-definition api-task:1 \
         --desired-count 2 \
         --launch-type FARGATE
       ```

    3. Configure load balancer (see ALB setup memory)

    4. Verify deployment:
       ```bash
       aws ecs describe-services \
         --cluster prod-cluster \
         --services api-service
       ```

    ### Troubleshooting
    - Task not starting: Check CloudWatch logs
    - Health check failing: Verify security groups
    - OOM errors: Increase task memory in definition
    """,
    type=MemoryType.PROCEDURAL,
    tags=["aws", "ecs", "deployment", "fargate", "infrastructure"]
)
```

### Pattern 4: The Code Cookbook

Build a library of useful code patterns:

```python
# Pagination pattern
ctx.save(
    '''from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    """Generic pagination response."""
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        size: int
    ) -> "Page[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )

# Usage:
# return Page.create(users, total_count, page=1, size=20)
    ''',
    type=MemoryType.CODE,
    tags=["pagination", "fastapi", "pydantic", "patterns"],
    summary="Generic pagination response model"
)
```

### Pattern 5: The Onboarding Guide

Create searchable onboarding content:

```python
ctx.save(
    """## New Developer Onboarding Checklist

    ### Day 1: Environment
    - [ ] Clone repositories (see 'repo setup' memory)
    - [ ] Install dependencies (see 'local dev setup' memory)
    - [ ] Get access to AWS, GitHub, Slack
    - [ ] Set up IDE with team settings

    ### Day 2: Architecture
    - [ ] Read architecture overview (search: 'architecture overview')
    - [ ] Review key decisions (search: type=decision, limit=20)
    - [ ] Understand deployment (search: 'deployment process')

    ### Day 3: Codebase
    - [ ] Run the test suite
    - [ ] Make a small change and deploy to staging
    - [ ] Review recent PRs for patterns

    ### Day 4: Domain
    - [ ] Read product documentation
    - [ ] Shadow a customer support call
    - [ ] Review common errors (search: type=error)

    ### Day 5: Contributing
    - [ ] Pick a good-first-issue
    - [ ] Pair with team member
    - [ ] Submit first PR

    ### Resources
    - Team Slack: #engineering
    - On-call rotation: PagerDuty
    - Documentation: Notion workspace
    """,
    type=MemoryType.PROCEDURAL,
    tags=["onboarding", "new-hire", "checklist", "team"]
)
```

---

## Advanced Topics

### Cross-Repository Knowledge

Share knowledge across related repositories:

```python
# In repo A: Save with project tag
ctx.save(
    "API rate limiting: 1000 req/min standard, 10000 req/min premium",
    type=MemoryType.FACT,
    project="platform",  # Shared project identifier
    tags=["api", "rate-limiting"]
)

# In repo B: Search across project
ctx.search("rate limiting", project="platform")
```

### Memory Lifecycle Management

#### Updating Memories

```python
# When information changes
ctx.update(
    memory_id="abc123",
    content="Updated: Rate limit now 2000 req/min standard",
    tags=["api", "rate-limiting", "updated-2024-01"]
)
```

#### Deprecating Memories

```python
# Mark as deprecated rather than delete
ctx.update(
    memory_id="old-memory",
    tags=[*existing_tags, "deprecated"],
    content=f"{existing_content}\n\n**DEPRECATED:** See memory xyz123 for current info"
)
```

#### Cleaning Up

```python
# Delete truly obsolete memories
ctx.delete(memory_id="abc123")

# Bulk cleanup via CLI
contextfs cleanup --older-than 180 --type episodic --dry-run
```

### Integration with Development Tools

#### Git Hooks

```bash
# .git/hooks/post-commit
#!/bin/bash
# Auto-save commit context to memory

COMMIT_MSG=$(git log -1 --pretty=%B)
COMMIT_HASH=$(git rev-parse --short HEAD)

# If commit message mentions a decision or fix
if echo "$COMMIT_MSG" | grep -qiE "(decision|decided|chose|fix|fixed|bug)"; then
    contextfs save "$COMMIT_MSG" \
        --type decision \
        --tags "git-commit,$COMMIT_HASH"
fi
```

#### CI/CD Integration

```yaml
# .github/workflows/deploy.yml
- name: Save deployment to memory
  run: |
    contextfs save \
      "Deployed ${{ github.sha }} to production at $(date)" \
      --type episodic \
      --tags deployment,production,${{ github.ref_name }}
```

### Custom Memory Types

Extend the type system for your needs:

```python
# Define custom types via metadata
ctx.save(
    "Sprint 42 retrospective notes...",
    type=MemoryType.EPISODIC,
    tags=["retro", "sprint-42"],
    metadata={
        "custom_type": "retrospective",
        "sprint": 42,
        "team": "platform"
    }
)

# Search with metadata
results = ctx.search("retrospective", metadata_filter={"sprint": 42})
```

---

## Troubleshooting

### Common Issues

#### "No memories found"

**Possible causes:**
1. Wrong namespace (check `contextfs status`)
2. Memories in different project
3. Search query too specific

**Solutions:**
```bash
# Check current namespace
contextfs status

# List all memories (no filter)
contextfs list --limit 50

# Search with broader query
contextfs search "database"  # instead of "PostgreSQL connection pool sizing"
```

#### "Session not saving"

**Possible causes:**
1. Session not started
2. Permission issues with data directory
3. Disk full

**Solutions:**
```bash
# Check data directory
ls -la ~/.contextfs/

# Check disk space
df -h ~/.contextfs/

# Start session manually
contextfs session start --label "test"
```

#### "Search returns irrelevant results"

**Possible causes:**
1. Embeddings not computed
2. Query too vague
3. Memories poorly tagged

**Solutions:**
```python
# Re-index to refresh embeddings
contextfs index --force

# Use more specific queries
ctx.search("PostgreSQL connection pool exhaustion error")

# Use type filters
ctx.search("database", type=MemoryType.ERROR)
```

#### "MCP tools not appearing"

**Possible causes:**
1. MCP server not running
2. Config file syntax error
3. Path issues

**Solutions:**
```bash
# Verify MCP server works
contextfs-mcp --help

# Check config syntax
cat ~/.config/claude/claude_desktop_config.json | python -m json.tool

# Use full path in config
which contextfs-mcp  # Use this path in config
```

### Getting Help

1. **Check logs:**
   ```bash
   # MCP server logs
   tail -f ~/.contextfs/logs/mcp.log

   # Claude Desktop logs
   tail -f ~/Library/Logs/Claude/*.log
   ```

2. **Enable debug mode:**
   ```bash
   export CONTEXTFS_DEBUG=true
   contextfs-mcp
   ```

3. **Report issues:**
   - GitHub: https://github.com/MagnetonIO/contextfs/issues
   - Include: contextfs version, OS, error messages, steps to reproduce

---

## Quick Reference

### CLI Commands

```bash
# Memory operations
contextfs save "content" --type TYPE --tags tag1,tag2
contextfs search "query" --type TYPE --limit N
contextfs recall MEMORY_ID
contextfs list --limit N --type TYPE
contextfs delete MEMORY_ID

# Session operations
contextfs sessions --limit N
contextfs session load SESSION_ID
contextfs session save --label "name"

# Repository operations
contextfs index [--force]
contextfs status

# Web UI
contextfs web --port 8000
```

### MCP Tools

```
contextfs_save          - Save memory
contextfs_search        - Search memories
contextfs_recall        - Get memory by ID
contextfs_list          - List recent memories
contextfs_update        - Update memory
contextfs_delete        - Delete memory
contextfs_index         - Index repository
contextfs_index_status  - Check indexing progress
contextfs_sessions      - List sessions
contextfs_load_session  - Load session
contextfs_message       - Add session message
contextfs_update_session - Update session
contextfs_delete_session - Delete session
contextfs_import_conversation - Import JSON conversation
```

### Memory Types

| Type | Use For |
|------|---------|
| `fact` | Configurations, conventions, stable truths |
| `decision` | Choices with rationale, ADRs |
| `code` | Patterns, snippets, algorithms |
| `error` | Bug fixes, error solutions |
| `procedural` | Setup guides, workflows |
| `episodic` | Sessions, incidents, history |

---

*This guide is maintained by the ContextFS community. Contributions welcome at [github.com/MagnetonIO/contextfs](https://github.com/MagnetonIO/contextfs).*
