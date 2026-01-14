# Recall - Search and Load Relevant Context

Search ContextFS memory for relevant context based on the current task or query.

## Instructions

### 1. Determine Search Strategy

Based on the user's request or current working context, decide what to search for:

**If starting a new task:**
- Search for prior work on the same topic
- Search for relevant decisions and procedures
- Search for known errors and solutions

**If debugging:**
- Search for similar errors
- Search for related code patterns
- Search for prior debugging sessions

**If exploring code:**
- Search for architectural decisions
- Search for code patterns
- Search for API documentation

### 2. Execute Searches

Run multiple targeted searches:

```
# General context search
contextfs_search(
    query="<topic or task description>",
    limit=5,
    cross_repo=True
)

# Decision search
contextfs_search(
    query="<topic>",
    type="decision",
    limit=3
)

# Error/solution search (if debugging)
contextfs_search(
    query="<error or symptom>",
    type="error",
    limit=5
)

# Procedural search (if following a workflow)
contextfs_search(
    query="<procedure topic>",
    type="procedural",
    limit=3
)
```

### 3. Load Previous Sessions (if relevant)

If continuing prior work:
```
# List recent sessions
contextfs_sessions(limit=5, label="<optional filter>")

# Load specific session
contextfs_load_session(session_id="<id>", max_messages=20)
```

### 4. Explore Related Memories

If a memory seems highly relevant, explore its connections:
```
# Get related memories
contextfs_related(memory_id="<id>", max_depth=2)

# Get memory lineage (evolution history)
contextfs_lineage(memory_id="<id>")
```

## Output

Present findings organized by relevance:

1. **Most Relevant Memories** - Direct matches to the query
2. **Related Decisions** - Prior decisions that may affect current work
3. **Known Issues** - Errors and solutions that may be relevant
4. **Procedures to Follow** - Established workflows for similar tasks

Include memory IDs for reference so user can request more details.

## Example Usage

User: "I need to work on the authentication system"

Searches to run:
```
contextfs_search(query="authentication system", limit=5)
contextfs_search(query="auth", type="decision", limit=3)
contextfs_search(query="auth login", type="error", limit=3)
contextfs_search(query="authentication", type="procedural", limit=2)
```

Then synthesize findings into actionable context.
