# Remember - Save Conversation Insights to Memory

Extract and save important information from this conversation to ContextFS long-term memory.

## Instructions

Analyze the current conversation and extract memories in these categories:

### 1. Decisions Made
For each decision identified:
```
contextfs_save(
    content="Decision: [what was decided]",
    type="decision",
    summary="[brief summary]",
    tags=["decision", "<topic>"],
    structured_data={
        "rationale": "[why this decision was made]",
        "alternatives": ["[other options considered]"],
        "context": "[relevant context]"
    }
)
```

### 2. Facts Learned
For each new fact about the codebase, user preferences, or domain:
```
contextfs_save(
    content="[the fact]",
    type="fact",
    summary="[brief summary]",
    tags=["fact", "<topic>"]
)
```

### 3. Errors and Solutions
For each error encountered and resolved:
```
contextfs_save(
    content="Error: [error description]\nCause: [root cause]\nSolution: [how it was fixed]",
    type="error",
    summary="[brief summary]",
    tags=["error", "<technology>", "solution"]
)
```

### 4. Procedures Discovered
For any workflow or procedure established:
```
contextfs_save(
    content="## [Procedure Name]\n\n1. [Step 1]\n2. [Step 2]\n...",
    type="procedural",
    summary="[brief summary]",
    tags=["procedure", "<topic>"]
)
```

### 5. Code Patterns
For notable code patterns or implementations:
```
contextfs_save(
    content="[code pattern with explanation]",
    type="code",
    summary="[what this pattern does]",
    tags=["code", "<language>", "<pattern-type>"]
)
```

## Execution Steps

1. **Review the conversation** - Identify all memorable content
2. **Check for duplicates** - Search existing memories before saving:
   ```
   contextfs_search(query="<topic>", limit=3)
   ```
3. **Save new memories** - Use appropriate type and structured_data
4. **Link related memories** - If connecting to existing memories:
   ```
   contextfs_link(from_id="<new_id>", to_id="<existing_id>", relation="related_to")
   ```
5. **Save session** - Finally, save the session itself:
   ```
   contextfs_save(save_session="current", label="<descriptive-label>")
   ```

## Output

After extraction, report:
- Number of memories saved by type
- Any memories that were evolved (updated) instead of created new
- Session label used

**Important**: Be thorough but avoid duplicating information that's already in memory. Always search first.
