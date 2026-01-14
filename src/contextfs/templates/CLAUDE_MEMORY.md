# ContextFS Memory Management Protocol

## Memory Operations (MANDATORY)

You have access to ContextFS for persistent memory across sessions. Use these operations actively throughout your work - memory management is infrastructure, not optional.

### When to Save Memories

**ALWAYS save immediately when you:**

1. **Learn a new fact** about the codebase, architecture, or user preferences
   - Use: `contextfs_save` with `type="fact"`
   - Example: "User prefers functional programming style"

2. **Make or discover a decision** with rationale
   - Use: `contextfs_save` with `type="decision"` and `structured_data` including rationale
   - Example: "Chose PostgreSQL over MySQL for JSON support"

3. **Encounter and solve an error**
   - Use: `contextfs_save` with `type="error"`
   - Include: error message, cause, solution
   - Example: "ChromaDB collection not found - fix: reconnect MCP"

4. **Discover a procedure or workflow**
   - Use: `contextfs_save` with `type="procedural"`
   - Include: step-by-step instructions
   - Example: "How to deploy to Railway using Docker"

5. **Complete a significant task**
   - Use: `contextfs_save` with `type="episodic"` or save session with label

6. **Complete a plan or implementation**
   - Use: `contextfs_save` with `type="procedural"`
   - Include: objective, files modified, key decisions
   - Example: Save implementation plans after approval and completion

### When to Search Memories

**ALWAYS search FIRST when you:**

1. **Start a new task** - Check for prior context
   ```
   contextfs_search(query="<task topic>", limit=5)
   ```

2. **Encounter an error** - Check if it's been solved before
   ```
   contextfs_search(query="<error message>", type="error", limit=5)
   ```

3. **Need to make a decision** - Check for prior decisions on the topic
   ```
   contextfs_search(query="<decision topic>", type="decision", limit=5)
   ```

4. **Explore unfamiliar code** - Check for documented patterns
   ```
   contextfs_search(query="<code area>", type="code", limit=10)
   ```

### Memory Type Reference

| Type | When to Use | Example |
|------|------------|---------|
| `fact` | Learned information about codebase/user | "API uses JWT auth" |
| `decision` | Choices made with rationale | "Use Redis for caching" |
| `procedural` | Step-by-step workflows | "How to add a new endpoint" |
| `episodic` | Session summaries, conversations | "Debugged auth flow" |
| `error` | Errors encountered and solutions | "CORS fix for API" |
| `code` | Code snippets, patterns | "Auth middleware pattern" |
| `api` | API endpoints, schemas | "POST /users payload" |
| `config` | Configuration details | "Required env vars" |

### Session Management

**Before ending a session:**
1. Save important learnings that haven't been saved yet
2. Use `contextfs_save` with `save_session="current"` and a descriptive label
3. Or use `/remember` skill for automatic extraction

**At session start:**
1. Search for relevant context based on working directory
2. Load previous session if continuing work: `contextfs_load_session`

### Memory Evolution

When knowledge updates or corrections are needed:
- Use `contextfs_evolve` to update existing memories (preserves history)
- Use `contextfs_link` to connect related memories
- Use `contextfs_merge` to consolidate duplicate information

### Quick Reference Commands

```
# Save a fact
contextfs_save(content="...", type="fact", tags=["topic"], summary="Brief summary")

# Save a decision
contextfs_save(content="Decided to use X because Y", type="decision",
               structured_data={"rationale": "Y", "alternatives": ["A", "B"]})

# Search before acting
contextfs_search(query="relevant topic", limit=5, cross_repo=True)

# Save session at end
contextfs_save(save_session="current", label="descriptive-label")
```

## Integration with Development Workflow

1. **Before coding**: Search memory for patterns, decisions, gotchas
2. **During coding**: Save errors encountered and solutions found
3. **After coding**: Save decisions made and lessons learned
4. **Before committing**: Ensure important context is saved to memory

Memory is your persistent context. Use it actively, not as an afterthought.
