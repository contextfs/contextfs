# Web API Reference

ContextFS provides a REST API through the web server for programmatic access to memories and sessions.

## OpenAPI Specification

The server provides auto-generated OpenAPI documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Starting the Server

```bash
# Start web server on default port (8000)
contextfs web

# Custom host and port
contextfs web --host 0.0.0.0 --port 8765
```

The server provides:
- REST API at `/api/*`
- Web UI at `/`
- WebSocket at `/ws` for real-time updates
- OpenAPI docs at `/docs` (Swagger UI) and `/redoc` (ReDoc)

## Memory Endpoints

### List Memories

```http
GET /api/memories?limit=20&type=fact&namespace=repo-name
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Max results (1-100, default: 20) |
| `type` | string | Filter by memory type |
| `namespace` | string | Filter by namespace |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "abc123...",
      "content": "Memory content",
      "type": "fact",
      "tags": ["tag1", "tag2"],
      "summary": "Brief summary",
      "namespace_id": "repo-name",
      "project": "project-name",
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### Get Memory

```http
GET /api/memories/{memory_id}
```

Supports partial ID matching (8+ characters).

### Create Memory

```http
POST /api/memories
Content-Type: application/json

{
  "content": "Memory content",
  "type": "decision",
  "tags": ["api", "design"],
  "summary": "API design decision"
}
```

### Update Memory

```http
PUT /api/memories/{memory_id}
Content-Type: application/json

{
  "content": "Updated content",
  "type": "fact",
  "tags": ["updated", "tags"],
  "summary": "Updated summary",
  "project": "my-project"
}
```

All fields are optional - only provided fields will be updated.

### Delete Memory

```http
DELETE /api/memories/{memory_id}
```

## Search Endpoint

### Search Memories

```http
GET /api/search?q=query&type=fact&semantic=true&limit=20
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (required) |
| `type` | string | Filter by memory type |
| `namespace` | string | Filter by namespace |
| `limit` | int | Max results (1-100, default: 20) |
| `offset` | int | Pagination offset |
| `semantic` | bool | Use semantic search (default: true) |
| `smart` | bool | Use smart routing based on memory type |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "memory": { ... },
      "score": 0.95,
      "highlights": ["matched <mark>text</mark>"],
      "source": "rag"
    }
  ]
}
```

### Dual Search

```http
GET /api/search/dual?q=query
```

Returns results from both FTS and RAG backends separately.

## Session Endpoints

### List Sessions

```http
GET /api/sessions?limit=20&offset=0&tool=claude-code
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Max results (1-100, default: 20) |
| `offset` | int | Pagination offset |
| `tool` | string | Filter by tool name |

### Get Session

```http
GET /api/sessions/{session_id}
```

Returns session details including all messages.

### Update Session

```http
PUT /api/sessions/{session_id}
Content-Type: application/json

{
  "label": "new-label",
  "summary": "Session summary"
}
```

### Delete Session

```http
DELETE /api/sessions/{session_id}
```

Deletes the session and all associated messages.

## Utility Endpoints

### Get Statistics

```http
GET /api/stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_memories": 150,
    "memories_by_type": {
      "fact": 50,
      "decision": 30,
      "procedural": 40,
      "code": 30
    },
    "total_sessions": 25,
    "namespaces": ["repo1", "repo2"],
    "fts_indexed": 150,
    "rag_indexed": 150
  }
}
```

### Get Namespaces

```http
GET /api/namespaces
```

### Export Memories

```http
GET /api/export
```

Downloads all memories as JSON file.

### Download Database

```http
GET /api/database
```

Downloads SQLite database for offline use with sql.js.

## WebSocket

Connect to `/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'memory_created':
      console.log('New memory:', data.memory);
      break;
    case 'memory_updated':
      console.log('Updated memory:', data.memory);
      break;
    case 'memory_deleted':
      console.log('Deleted memory:', data.id);
      break;
    case 'session_updated':
      console.log('Updated session:', data.session);
      break;
    case 'session_deleted':
      console.log('Deleted session:', data.id);
      break;
  }
};

// Keep alive
ws.send(JSON.stringify({ type: 'ping' }));
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message"
}
```

HTTP status codes:
- `200` - Success
- `404` - Resource not found
- `422` - Validation error
- `500` - Server error
