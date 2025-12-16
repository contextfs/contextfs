# Custom Agent Integration

Integrate ContextFS into your own AI agents and applications.

## Python API

### Basic Usage

```python
from contextfs import ContextFS, MemoryType

# Initialize
ctx = ContextFS()

# Save memories
ctx.save(
    content="User prefers detailed explanations",
    type=MemoryType.USER,
    tags=["preferences"]
)

# Search
results = ctx.search("user preferences")
for r in results:
    print(f"{r.score:.2f}: {r.memory.content}")
```

### With TypeSafe Context

Combine with the TypeSafe Context library:

```python
from pydantic import BaseModel
from typesafe_context import TypeSafeAgent, TypeSafeClient
from contextfs import ContextFS, ContextFSMemory

class TaskResult(BaseModel):
    success: bool
    output: str
    notes: list[str]

# Create memory-enabled agent
memory = ContextFSMemory(project="my-agent")
client = TypeSafeClient(provider="anthropic", model="claude-sonnet-4-20250514")
agent = TypeSafeAgent(name="assistant", client=client)

# Get relevant context
context = memory.get_context_for_task("Implement user auth")

# Run with type safety
result = agent.run(
    task=f"Context:\n{context}\n\nTask: Implement OAuth login",
    response_type=TaskResult
)

# Save result
memory.save_result(result, tags=["auth", "oauth"])
```

### Session Management

```python
ctx = ContextFS()

# Start session
session = ctx.start_session(
    tool="my-agent",
    label="feature-implementation"
)

# Log messages
ctx.log_message("user", "Implement rate limiting")
ctx.log_message("assistant", "I'll add rate limiting middleware...")

# End and summarize
ctx.end_session(summary="Implemented rate limiting with Redis backend")
```

## LangChain Integration

```python
from langchain.memory import BaseMemory
from contextfs import ContextFS

class ContextFSMemory(BaseMemory):
    def __init__(self, project: str = None):
        self.ctx = ContextFS()
        self.project = project

    @property
    def memory_variables(self) -> list[str]:
        return ["context"]

    def load_memory_variables(self, inputs: dict) -> dict:
        query = inputs.get("input", "")
        results = self.ctx.search(query, limit=5, project=self.project)
        context = "\n".join([r.memory.content for r in results])
        return {"context": context}

    def save_context(self, inputs: dict, outputs: dict) -> None:
        self.ctx.save(
            content=f"Q: {inputs['input']}\nA: {outputs['output']}",
            type="episodic",
            project=self.project
        )

# Use with LangChain
from langchain.chains import ConversationChain
from langchain.llms import Anthropic

memory = ContextFSMemory(project="my-app")
chain = ConversationChain(llm=Anthropic(), memory=memory)
```

## LlamaIndex Integration

```python
from llama_index.core.memory import BaseMemory
from contextfs import ContextFS

class ContextFSLlamaMemory(BaseMemory):
    def __init__(self):
        self.ctx = ContextFS()

    def get(self, input: str) -> list[str]:
        results = self.ctx.search(input, limit=10)
        return [r.memory.content for r in results]

    def put(self, content: str) -> None:
        self.ctx.save(content, type="episodic")
```

## REST API

For non-Python applications, run the web server:

```bash
contextfs web --host 0.0.0.0 --port 8000
```

### Endpoints

```bash
# Save memory
curl -X POST http://localhost:8000/api/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "API rate limit is 100/min", "type": "fact", "tags": ["api"]}'

# Search
curl "http://localhost:8000/api/memories/search?q=rate+limit&limit=5"

# List recent
curl "http://localhost:8000/api/memories?limit=10"

# Recall by ID
curl "http://localhost:8000/api/memories/abc123"
```

## MCP Protocol

Build your own MCP client:

```python
import json
from subprocess import Popen, PIPE

class ContextFSClient:
    def __init__(self):
        self.proc = Popen(
            ["contextfs-mcp"],
            stdin=PIPE,
            stdout=PIPE,
            text=True
        )

    def call_tool(self, name: str, arguments: dict) -> dict:
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": 1
        }
        self.proc.stdin.write(json.dumps(request) + "\n")
        self.proc.stdin.flush()
        response = json.loads(self.proc.stdout.readline())
        return response["result"]

    def search(self, query: str) -> list:
        return self.call_tool("contextfs_search", {"query": query})

    def save(self, content: str, type: str = "fact") -> dict:
        return self.call_tool("contextfs_save", {
            "content": content,
            "type": type
        })
```

## Multi-Agent Systems

### Shared Memory

Multiple agents sharing context:

```python
from contextfs import ContextFS

# All agents use the same project
PROJECT = "multi-agent-system"

class ResearchAgent:
    def __init__(self):
        self.ctx = ContextFS()
        self.ctx.project = PROJECT

    def research(self, topic: str):
        # Check what's already known
        prior = self.ctx.search(topic, project=PROJECT)

        # Do research...
        findings = self._do_research(topic)

        # Save for other agents
        self.ctx.save(findings, type="fact", project=PROJECT)

class ImplementationAgent:
    def __init__(self):
        self.ctx = ContextFS()
        self.ctx.project = PROJECT

    def implement(self, task: str):
        # Get research context
        research = self.ctx.search(task, project=PROJECT, type="fact")

        # Implement with context...
```

### Agent Handoff

```python
def handoff_context(from_agent: str, to_agent: str, task: str):
    ctx = ContextFS()

    # Get context from previous agent
    context = ctx.search(
        task,
        source_tool=from_agent,
        limit=20
    )

    # Format for next agent
    handoff = {
        "task": task,
        "prior_context": [r.memory.to_dict() for r in context],
        "from_agent": from_agent
    }

    return handoff
```

## Best Practices

### 1. Use Projects for Isolation

```python
# Separate contexts for different applications
ctx_prod = ContextFS()
ctx_prod.project = "my-app-prod"

ctx_dev = ContextFS()
ctx_dev.project = "my-app-dev"
```

### 2. Implement Retry Logic

```python
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def save_with_retry(ctx, content, **kwargs):
    return ctx.save(content, **kwargs)
```

### 3. Batch Operations

```python
# For bulk saves
memories = [
    {"content": "...", "type": "fact"},
    {"content": "...", "type": "decision"},
]

for m in memories:
    ctx.save(**m)
```

### 4. Handle Cross-Repo Carefully

```python
# Be explicit about cross-repo searches
results = ctx.search(
    query,
    cross_repo=True,  # Explicit
    project="my-project"  # Scoped to project
)
```
