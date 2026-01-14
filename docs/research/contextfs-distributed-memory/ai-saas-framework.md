# AI-Accelerated SaaS Development Framework

## From Idea to Production in 2-3 Weeks with One Developer

**Based on the ContextFS case study: 58,607 lines of production code built by a single developer using AI-assisted development.**

---

## Executive Summary

This framework documents how a single developer built ContextFS - a distributed, type-safe AI memory system with:
- **Backend**: 45K lines Python (CLI, MCP server, sync service)
- **Frontend**: Full Next.js dashboard with billing, auth, admin
- **Cloud**: Multi-tenant SaaS with Stripe, OAuth, team management
- **Timeline**: 4 days to MVP, 2 weeks to feature-complete, 4 weeks to commercial platform

The key insight: **Service abstractions + AI coding assistants + modern frameworks = 10x development velocity**.

---

## Table of Contents

1. [Core Principles](#1-core-principles)
2. [Architecture Patterns](#2-architecture-patterns)
3. [Backend Framework](#3-backend-framework)
4. [Frontend Framework](#4-frontend-framework)
5. [Service Abstractions](#5-service-abstractions)
6. [AI-Assisted Development Workflow](#6-ai-assisted-development-workflow)
7. [Week-by-Week Roadmap](#7-week-by-week-roadmap)
8. [Tech Stack Recommendations](#8-tech-stack-recommendations)
9. [Deployment & DevOps](#9-deployment--devops)
10. [Reusable Components](#10-reusable-components)

---

## 1. Core Principles

### 1.1 Protocol-First Design

**Every major feature is defined as a protocol before implementation.**

```python
# Define the contract first
class StorageBackend(Protocol):
    def save(self, item: Item) -> Item: ...
    def search(self, query: str) -> list[Result]: ...
    def delete(self, id: str) -> bool: ...

# Then implement variations
class SQLiteBackend(StorageBackend): ...
class PostgresBackend(StorageBackend): ...
```

**Why it enables speed:**
- Swap implementations without changing business logic
- Test against protocol, not implementation
- AI can generate implementations from protocol specs
- Add new backends (Redis, MongoDB) without refactoring

### 1.2 Config-Driven Behavior

**Every feature controllable via environment variables.**

```python
class Settings(BaseSettings):
    backend: Literal["sqlite", "postgres"] = "sqlite"
    enable_billing: bool = False
    enable_teams: bool = False
    stripe_key: str | None = None

    model_config = SettingsConfigDict(env_prefix="APP_")
```

**Why it enables speed:**
- Same codebase for dev/staging/prod
- Feature flags without deployment
- CI can test all configurations
- AI understands env-var patterns universally

### 1.3 Graceful Degradation

**Advanced features are optional with automatic fallbacks.**

```python
# Try advanced → fallback to basic
def search(self, query: str):
    try:
        return self.vector_db.semantic_search(query)  # Advanced
    except VectorDBUnavailable:
        return self.sqlite.keyword_search(query)  # Fallback
```

**Why it enables speed:**
- Core always works (no blocking dependencies)
- Premium features don't break free tier
- Development doesn't require full stack
- AI can suggest fallback patterns

### 1.4 Multi-Interface, Single Core

**One core class serves CLI, API, MCP, and Web.**

```
┌─────────────────────────────────────────────┐
│  CLI (Typer)  │  API (FastAPI)  │  MCP      │
└───────────────────────┬─────────────────────┘
                        │
                ┌───────▼───────┐
                │   Core Class  │  ← Single source of truth
                └───────────────┘
```

**Why it enables speed:**
- No code duplication across interfaces
- Fix once, works everywhere
- AI generates interface wrappers easily
- Testing core = testing all interfaces

### 1.5 Pydantic Everywhere

**Runtime validation as a feature, not overhead.**

```python
class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    tier: Literal["free", "pro", "team"] = "free"

# Auto-validates, auto-documents, auto-serializes
@app.post("/users")
def create_user(request: CreateUserRequest): ...
```

**Why it enables speed:**
- Validation is automatic
- API docs generated from types
- IDE autocomplete works
- AI understands Pydantic patterns

---

## 2. Architecture Patterns

### 2.1 The Storage Router Pattern

**Central coordinator that keeps multiple backends in sync.**

```python
class StorageRouter:
    """Routes operations to appropriate backend(s)"""

    def __init__(self, primary: StorageBackend, secondary: StorageBackend = None):
        self.primary = primary      # e.g., SQLite (metadata)
        self.secondary = secondary  # e.g., ChromaDB (vectors)

    def save(self, item: Item) -> Item:
        # Save to primary (always)
        result = self.primary.save(item)

        # Save to secondary (if available)
        if self.secondary:
            self.secondary.save(result)

        return result

    def search(self, query: str) -> list[Result]:
        results = []

        # Get from both backends
        if self.secondary:
            results.extend(self.secondary.semantic_search(query))
        results.extend(self.primary.keyword_search(query))

        # Merge, dedupe, rank
        return self._merge_results(results)
```

**Use cases:**
- SQLite + ChromaDB (local development)
- PostgreSQL + pgvector (production)
- Any primary + any secondary

### 2.2 The Hybrid Search Pattern

**Combine keyword (FTS) and semantic (vector) search.**

```python
def hybrid_search(query: str, limit: int = 10) -> list[Result]:
    # Run both searches in parallel
    semantic_results = vector_db.search(query, limit * 2)
    keyword_results = fts_db.search(query, limit * 2)

    # Normalize scores to [0, 1]
    semantic_results = normalize_scores(semantic_results)
    keyword_results = normalize_scores(keyword_results)

    # Weighted merge (semantic usually weighted higher)
    merged = merge_by_id(
        semantic_results, weight=0.7,
        keyword_results, weight=0.3
    )

    return sorted(merged, key=lambda r: r.score, reverse=True)[:limit]
```

**Why hybrid wins:**
- Semantic catches synonyms ("auth" finds "authentication")
- Keyword catches exact matches ("JWT" finds "JWT")
- Best of both worlds

### 2.3 The Factory Pattern for Backends

**Auto-create correct backend from config.**

```python
def create_backend(settings: Settings) -> StorageBackend:
    match settings.backend:
        case "sqlite":
            return SQLiteBackend(settings.db_path)
        case "postgres":
            return PostgresBackend(settings.postgres_url)
        case "sqlite_vector":
            return StorageRouter(
                primary=SQLiteBackend(settings.db_path),
                secondary=ChromaDBBackend(settings.chroma_path)
            )
        case _:
            raise ValueError(f"Unknown backend: {settings.backend}")
```

### 2.4 The Lineage Pattern (Versioning)

**Track history of changes with relationships.**

```python
class LineageManager:
    def evolve(self, item_id: str, new_content: str, reason: ChangeReason) -> Item:
        """Create new version linked to original"""
        original = self.get(item_id)
        new_item = Item(content=new_content, parent_id=original.id)
        self.save(new_item)
        self.create_edge(original.id, new_item.id, "evolved_to")
        return new_item

    def merge(self, item_ids: list[str], merged_content: str) -> Item:
        """Combine multiple items into one"""
        merged = Item(content=merged_content)
        self.save(merged)
        for item_id in item_ids:
            self.create_edge(item_id, merged.id, "merged_into")
        return merged

    def get_history(self, item_id: str) -> list[Item]:
        """Get full evolution chain"""
        return self.traverse_graph(item_id, direction="ancestors")
```

---

## 3. Backend Framework

### 3.1 Project Structure

```
my-saas/
├── src/
│   └── my_saas/
│       ├── __init__.py
│       ├── core.py              # Main class (single entry point)
│       ├── models.py            # Pydantic models
│       ├── settings.py          # Config management
│       ├── storage/
│       │   ├── protocol.py      # StorageBackend protocol
│       │   ├── sqlite.py        # SQLite implementation
│       │   ├── postgres.py      # PostgreSQL implementation
│       │   └── router.py        # Multi-backend coordinator
│       ├── api/
│       │   ├── main.py          # FastAPI app
│       │   ├── routes/          # Route modules
│       │   └── deps.py          # Dependency injection
│       ├── cli/
│       │   ├── __init__.py      # Typer app
│       │   └── commands/        # Command modules
│       ├── auth/
│       │   ├── jwt.py           # Token handling
│       │   ├── oauth.py         # OAuth flows
│       │   └── api_keys.py      # API key management
│       └── billing/
│           ├── stripe.py        # Stripe integration
│           └── usage.py         # Usage tracking
├── service/                     # Cloud service (if separate)
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── unit/
│   └── integration/
├── migrations/
├── docker/
├── pyproject.toml
└── CLAUDE.md                   # AI instructions
```

### 3.2 Core Class Template

```python
# src/my_saas/core.py
from .settings import Settings
from .storage import create_backend, StorageBackend

class MySaaS:
    """Single entry point for all operations"""

    def __init__(
        self,
        settings: Settings | None = None,
        backend: StorageBackend | None = None,
    ):
        self.settings = settings or Settings()
        self.backend = backend or create_backend(self.settings)

    # CRUD operations delegate to backend
    def create(self, item: CreateRequest) -> Item:
        return self.backend.save(Item(**item.model_dump()))

    def get(self, id: str) -> Item | None:
        return self.backend.get(id)

    def search(self, query: str, **filters) -> list[Item]:
        return self.backend.search(query, **filters)

    def delete(self, id: str) -> bool:
        return self.backend.delete(id)

    # Business logic lives here
    def process(self, item: Item) -> ProcessedItem:
        # Your domain logic
        ...
```

### 3.3 FastAPI Integration

```python
# src/my_saas/api/main.py
from fastapi import FastAPI, Depends
from ..core import MySaaS
from ..settings import Settings

app = FastAPI(title="My SaaS API")

# Dependency injection
def get_core() -> MySaaS:
    return MySaaS(Settings())

@app.post("/items")
def create_item(
    request: CreateRequest,
    core: MySaaS = Depends(get_core)
) -> Item:
    return core.create(request)

@app.get("/items/{id}")
def get_item(
    id: str,
    core: MySaaS = Depends(get_core)
) -> Item:
    return core.get(id)
```

### 3.4 CLI Integration

```python
# src/my_saas/cli/__init__.py
import typer
from ..core import MySaaS

app = typer.Typer(help="My SaaS CLI")

@app.command()
def create(content: str):
    """Create a new item"""
    core = MySaaS()
    item = core.create(CreateRequest(content=content))
    typer.echo(f"Created: {item.id}")

@app.command()
def search(query: str, limit: int = 10):
    """Search items"""
    core = MySaaS()
    results = core.search(query, limit=limit)
    for r in results:
        typer.echo(f"[{r.score:.2f}] {r.content[:50]}...")
```

---

## 4. Frontend Framework

### 4.1 Project Structure

```
my-saas-web/
├── src/
│   ├── app/
│   │   ├── page.tsx                    # Landing page
│   │   ├── layout.tsx                  # Root layout
│   │   ├── (marketing)/                # Public pages
│   │   │   ├── pricing/
│   │   │   └── features/
│   │   ├── (dashboard)/                # Protected pages
│   │   │   ├── layout.tsx              # Dashboard layout
│   │   │   ├── page.tsx                # Dashboard home
│   │   │   ├── items/                  # CRUD pages
│   │   │   ├── billing/
│   │   │   ├── settings/
│   │   │   └── admin/
│   │   └── api/
│   │       └── auth/[...nextauth]/     # Auth routes
│   ├── components/
│   │   ├── ui/                         # Base components
│   │   ├── dashboard/                  # Dashboard components
│   │   └── marketing/                  # Marketing components
│   ├── lib/
│   │   ├── api.ts                      # API client
│   │   ├── auth.ts                     # NextAuth config
│   │   └── utils.ts                    # Utilities
│   └── styles/
│       └── globals.css                 # Design system
├── public/
├── package.json
└── tailwind.config.ts
```

### 4.2 API Client Pattern

```typescript
// src/lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL;

class ApiClient {
  private apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  // CRUD methods
  async createItem(data: CreateItemRequest): Promise<Item> {
    return this.request('/items', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getItems(params?: SearchParams): Promise<PaginatedResponse<Item>> {
    const query = new URLSearchParams(params as any).toString();
    return this.request(`/items?${query}`);
  }

  async deleteItem(id: string): Promise<void> {
    return this.request(`/items/${id}`, { method: 'DELETE' });
  }

  // Billing methods
  async getSubscription(): Promise<Subscription> {
    return this.request('/billing/subscription');
  }

  async createCheckoutSession(tier: string): Promise<{ url: string }> {
    return this.request('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ tier }),
    });
  }
}

export const createApiClient = (apiKey: string) => new ApiClient(apiKey);
```

### 4.3 Dashboard Layout Pattern

```typescript
// src/app/(dashboard)/layout.tsx
import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { Sidebar } from '@/components/dashboard/Sidebar';
import { Header } from '@/components/dashboard/Header';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession();

  if (!session) {
    redirect('/login');
  }

  return (
    <div className="min-h-screen bg-dark-950">
      <Sidebar />
      <div className="pl-64">
        <Header />
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### 4.4 Design System (Tailwind)

```css
/* src/styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .btn-primary {
    @apply px-4 py-2 rounded-lg font-medium
           bg-gradient-to-r from-purple-600 to-blue-600
           hover:from-purple-500 hover:to-blue-500
           text-white transition-all duration-200;
  }

  .btn-secondary {
    @apply px-4 py-2 rounded-lg font-medium
           border border-dark-700 bg-dark-800
           hover:bg-dark-700 text-white
           transition-all duration-200;
  }

  .card {
    @apply bg-dark-900/50 backdrop-blur-sm
           border border-dark-800 rounded-xl p-6;
  }

  .input {
    @apply w-full px-4 py-2 rounded-lg
           bg-dark-800 border border-dark-700
           text-white placeholder-dark-400
           focus:outline-none focus:ring-2 focus:ring-purple-500;
  }
}
```

---

## 5. Service Abstractions

### 5.1 Authentication Service

```python
# Reusable auth abstraction
class AuthService(Protocol):
    def create_user(self, email: str, password: str) -> User: ...
    def authenticate(self, email: str, password: str) -> Token: ...
    def verify_token(self, token: str) -> User: ...
    def create_api_key(self, user_id: str, name: str) -> ApiKey: ...
    def revoke_api_key(self, key_id: str) -> bool: ...

# JWT implementation
class JWTAuthService:
    def __init__(self, secret: str, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm

    def create_token(self, user: User, expires: timedelta) -> str:
        payload = {
            "sub": user.id,
            "email": user.email,
            "exp": datetime.utcnow() + expires,
        }
        return jwt.encode(payload, self.secret, self.algorithm)

    def verify_token(self, token: str) -> User:
        payload = jwt.decode(token, self.secret, [self.algorithm])
        return self.get_user(payload["sub"])
```

### 5.2 Billing Service

```python
# Reusable billing abstraction
class BillingService(Protocol):
    def create_customer(self, user: User) -> str: ...  # Returns customer_id
    def create_subscription(self, customer_id: str, tier: str) -> Subscription: ...
    def cancel_subscription(self, subscription_id: str) -> bool: ...
    def get_usage(self, user_id: str) -> Usage: ...
    def check_limit(self, user_id: str, resource: str) -> bool: ...

# Stripe implementation
class StripeBillingService:
    def __init__(self, api_key: str, prices: dict[str, str]):
        stripe.api_key = api_key
        self.prices = prices  # {"pro": "price_xxx", "team": "price_yyy"}

    def create_checkout_session(
        self,
        customer_id: str,
        tier: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": self.prices[tier], "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url

    def handle_webhook(self, payload: bytes, signature: str) -> None:
        event = stripe.Webhook.construct_event(
            payload, signature, self.webhook_secret
        )
        match event.type:
            case "checkout.session.completed":
                self._handle_checkout_completed(event.data.object)
            case "customer.subscription.updated":
                self._handle_subscription_updated(event.data.object)
            case "customer.subscription.deleted":
                self._handle_subscription_deleted(event.data.object)
```

### 5.3 Storage Service

```python
# Reusable storage abstraction
class StorageService(Protocol):
    def save(self, item: T) -> T: ...
    def get(self, id: str) -> T | None: ...
    def search(self, query: str, **filters) -> list[T]: ...
    def delete(self, id: str) -> bool: ...
    def list(self, **filters) -> list[T]: ...

# SQLite implementation
class SQLiteStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def save(self, item: Item) -> Item:
        with self._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO items VALUES (?, ?, ?, ?)",
                (item.id, item.content, item.type, item.created_at)
            )
        return item

    def search(self, query: str, **filters) -> list[Item]:
        with self._connection() as conn:
            # Use FTS5 for full-text search
            results = conn.execute(
                "SELECT * FROM items_fts WHERE content MATCH ?",
                (query,)
            ).fetchall()
        return [Item(**r) for r in results]

# PostgreSQL implementation
class PostgresStorage:
    def __init__(self, connection_url: str):
        self.pool = create_pool(connection_url)

    async def save(self, item: Item) -> Item:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO items VALUES ($1, $2, $3, $4) ON CONFLICT (id) DO UPDATE SET ...",
                item.id, item.content, item.type, item.created_at
            )
        return item
```

### 5.4 Sync Service

```python
# Reusable sync abstraction (for multi-device)
class SyncService(Protocol):
    def push(self, items: list[Item], device_id: str) -> SyncResult: ...
    def pull(self, device_id: str, since: datetime) -> list[Item]: ...
    def resolve_conflict(self, local: Item, remote: Item) -> Item: ...

# Vector clock implementation
class VectorClockSync:
    def push(self, items: list[Item], device_id: str) -> SyncResult:
        accepted, rejected, conflicts = [], [], []

        for item in items:
            # Increment local clock
            item.clock = item.clock.increment(device_id)

            # Check server version
            server_item = self.storage.get(item.id)

            if server_item is None:
                # New item, accept
                self.storage.save(item)
                accepted.append(item)
            elif item.clock.happens_before(server_item.clock):
                # Local is behind, reject
                rejected.append(item)
            elif server_item.clock.happens_before(item.clock):
                # Local is ahead, accept
                self.storage.save(item)
                accepted.append(item)
            else:
                # Concurrent modification, conflict
                conflicts.append((item, server_item))

        return SyncResult(accepted, rejected, conflicts)
```

---

## 6. AI-Assisted Development Workflow

### 6.1 The CLAUDE.md Pattern

**Create a project instruction file that AI assistants read:**

```markdown
# Project Instructions (CLAUDE.md)

## Architecture
- Protocol-first design: define interfaces before implementations
- Storage abstraction: SQLite locally, PostgreSQL in production
- Config-driven: all features controllable via environment variables

## Conventions
- Pydantic for all data models
- FastAPI for API routes
- Typer for CLI commands
- pytest for testing

## File Organization
- src/my_saas/core.py - Main entry point
- src/my_saas/storage/ - Storage backends
- src/my_saas/api/ - FastAPI routes
- tests/ - All tests

## Commands
- `pytest tests/` - Run tests
- `python -m my_saas.cli` - Run CLI
- `uvicorn my_saas.api.main:app` - Run API

## Database
- Local: SQLite at ~/.my_saas/data.db
- Production: PostgreSQL (POSTGRES_URL env var)

## Current Focus
[Update this section as you work]
```

### 6.2 Prompt Patterns for AI

**Feature Implementation:**
```
Implement [feature] following these patterns:
1. Add protocol method to StorageBackend in storage/protocol.py
2. Implement in SQLiteBackend (storage/sqlite.py)
3. Implement in PostgresBackend (storage/postgres.py)
4. Add API route in api/routes/[feature].py
5. Add CLI command in cli/commands/[feature].py
6. Add tests in tests/integration/test_[feature].py

Use existing code patterns. Reference storage/protocol.py for the protocol pattern.
```

**Bug Fix:**
```
Fix [bug description].
1. First, search the codebase for relevant files
2. Identify the root cause
3. Implement fix following existing patterns
4. Add test case that would have caught this bug
5. Verify fix doesn't break existing tests
```

**Refactoring:**
```
Refactor [component] to [goal].
1. Maintain backward compatibility
2. Keep existing tests passing
3. Update affected imports
4. Add migration if needed (database changes)
```

### 6.3 Iterative Development Loop

```
Week 1: Foundation
├── Day 1-2: Core + Storage protocol
├── Day 3-4: API routes + CLI
└── Day 5: Basic frontend

Week 2: Features
├── Day 1-2: Auth (JWT + API keys)
├── Day 3-4: Main feature implementation
└── Day 5: Testing + bug fixes

Week 3: Production
├── Day 1-2: Billing integration
├── Day 3: Admin dashboard
├── Day 4: Deployment setup
└── Day 5: Launch prep
```

---

## 7. Week-by-Week Roadmap

### Week 1: Foundation (Days 1-5)

**Day 1: Project Setup**
```bash
# Initialize project
mkdir my-saas && cd my-saas
uv init  # or: poetry init
uv add pydantic fastapi typer uvicorn

# Create structure
mkdir -p src/my_saas/{storage,api,cli}
touch src/my_saas/{core,models,settings}.py
```

**Day 2: Storage Protocol + SQLite**
- Define StorageBackend protocol
- Implement SQLiteBackend
- Add basic CRUD operations
- Write first tests

**Day 3: API Routes**
- FastAPI app setup
- CRUD endpoints
- Request/response models
- OpenAPI documentation

**Day 4: CLI**
- Typer app setup
- Mirror API functionality
- Interactive commands
- Help documentation

**Day 5: Basic Frontend**
- Next.js project setup
- API client
- Basic CRUD UI
- Tailwind styling

### Week 2: Features (Days 6-10)

**Day 6: Authentication**
- JWT token generation
- API key management
- Protected routes
- NextAuth setup

**Day 7: OAuth Integration**
- Google/GitHub providers
- Callback handling
- Session management

**Day 8-9: Core Feature**
- Main product feature
- Search/filtering
- Data processing
- Advanced UI

**Day 10: Testing**
- Unit tests
- Integration tests
- E2E tests
- Bug fixes

### Week 3: Production (Days 11-15)

**Day 11: PostgreSQL Backend**
- PostgresBackend implementation
- Migrations
- Production config

**Day 12: Stripe Billing**
- Customer creation
- Checkout sessions
- Webhook handling
- Usage tracking

**Day 13: Admin Dashboard**
- User management
- Statistics
- Admin actions

**Day 14: Deployment**
- Docker setup
- CI/CD pipeline
- Railway/Vercel config
- Domain setup

**Day 15: Launch**
- Final testing
- Documentation
- Monitoring setup
- Go live

---

## 8. Tech Stack Recommendations

### Backend

| Component | Recommendation | Alternative |
|-----------|---------------|-------------|
| Language | Python 3.11+ | TypeScript/Node |
| API Framework | FastAPI | Flask, Django |
| CLI Framework | Typer | Click, argparse |
| Data Validation | Pydantic v2 | dataclasses |
| Local DB | SQLite | DuckDB |
| Production DB | PostgreSQL | MySQL |
| Vector DB | ChromaDB | Pinecone, Weaviate |
| Async | asyncio | Trio |
| Testing | pytest | unittest |
| Auth | PyJWT | authlib |
| Billing | Stripe | Paddle |

### Frontend

| Component | Recommendation | Alternative |
|-----------|---------------|-------------|
| Framework | Next.js 14 | Remix, SvelteKit |
| State | React Query | SWR, Zustand |
| Styling | Tailwind CSS | styled-components |
| Auth | NextAuth.js | Clerk, Auth0 |
| UI Components | Custom + Tailwind | shadcn/ui, Radix |
| Icons | Lucide React | Heroicons |
| Forms | React Hook Form | Formik |

### Infrastructure

| Component | Recommendation | Alternative |
|-----------|---------------|-------------|
| Backend Hosting | Railway | Render, Fly.io |
| Frontend Hosting | Vercel | Netlify, Cloudflare |
| Database | Railway Postgres | Supabase, Neon |
| CI/CD | GitHub Actions | GitLab CI |
| Monitoring | Sentry | LogRocket |
| Email | Resend | SendGrid |

---

## 9. Deployment & DevOps

### 9.1 Docker Setup

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install uv && uv pip install --system .

# Copy source
COPY src/ src/
COPY migrations/ migrations/

# Run migrations and start server
CMD ["sh", "-c", "python -m my_saas.migrate && uvicorn my_saas.api.main:app --host 0.0.0.0 --port $PORT"]
```

### 9.2 GitHub Actions CI/CD

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install uv && uv pip install --system ".[dev]"
      - run: pytest tests/

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push Docker image
        run: |
          docker build -t ${{ secrets.DOCKER_IMAGE }} .
          docker push ${{ secrets.DOCKER_IMAGE }}
      - name: Deploy to Railway
        run: railway redeploy --service ${{ secrets.RAILWAY_SERVICE }}
```

### 9.3 Environment Variables

```bash
# .env.example
# Database
DATABASE_URL=sqlite:///~/.my_saas/data.db
POSTGRES_URL=postgresql://user:pass@host/db

# Auth
JWT_SECRET=your-secret-key
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000

# OAuth
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx

# Billing
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_TEAM=price_xxx

# API
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 10. Reusable Components

### 10.1 Copy-Paste Starters

**Storage Protocol:**
```python
# Copy this to storage/protocol.py
from typing import Protocol, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class StorageBackend(Protocol[T]):
    def save(self, item: T) -> T: ...
    def get(self, id: str) -> T | None: ...
    def search(self, query: str, limit: int = 10) -> list[T]: ...
    def delete(self, id: str) -> bool: ...
    def list(self, offset: int = 0, limit: int = 100) -> list[T]: ...
```

**Settings:**
```python
# Copy this to settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    # Database
    database_url: str = "sqlite:///data.db"

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"

    # Features
    enable_billing: bool = False
    enable_teams: bool = False

    # Stripe (if billing enabled)
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
```

**API Client (TypeScript):**
```typescript
// Copy this to lib/api.ts
class ApiClient {
  constructor(
    private baseUrl: string,
    private apiKey: string
  ) {}

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const res = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey,
        ...options.headers,
      },
    });
    if (!res.ok) throw new Error(`API Error: ${res.status}`);
    return res.json();
  }

  get<T>(endpoint: string) { return this.request<T>(endpoint); }
  post<T>(endpoint: string, data: any) {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  delete(endpoint: string) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}
```

### 10.2 Component Templates

**Dashboard Card:**
```tsx
// components/ui/Card.tsx
export function Card({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}
```

**Data Table:**
```tsx
// components/ui/DataTable.tsx
export function DataTable<T>({
  data,
  columns,
  onRowClick,
}: {
  data: T[];
  columns: { key: keyof T; header: string; render?: (item: T) => React.ReactNode }[];
  onRowClick?: (item: T) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-dark-700">
            {columns.map(col => (
              <th key={String(col.key)} className="text-left py-3 px-4 text-dark-400">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item, i) => (
            <tr
              key={i}
              onClick={() => onRowClick?.(item)}
              className="border-b border-dark-800 hover:bg-dark-800/50 cursor-pointer"
            >
              {columns.map(col => (
                <td key={String(col.key)} className="py-3 px-4 text-white">
                  {col.render ? col.render(item) : String(item[col.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Conclusion

This framework demonstrates that a single developer can build a production SaaS in 2-3 weeks by:

1. **Using proven abstractions** (Storage, Auth, Billing protocols)
2. **Leveraging AI assistants** for code generation and debugging
3. **Choosing batteries-included frameworks** (FastAPI, Next.js, Tailwind)
4. **Following protocol-first design** for flexibility
5. **Automating everything** (CI/CD, testing, deployment)

The ContextFS case study proves this is achievable:
- **58K lines** of production code
- **4 days** to MVP
- **2 weeks** to feature-complete
- **4 weeks** to commercial platform

The key is not working harder, but working smarter with the right abstractions and tools.

---

## References

- ContextFS Repository: Architecture patterns and implementation
- ContextFS Web: Frontend patterns and design system
- ContextFS Paper: Formal type system specification

---

*Framework Version 1.0 - January 2026*
*Based on the ContextFS development experience*
