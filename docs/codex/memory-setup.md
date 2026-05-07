# Codex Memory Setup

This repo uses two local memory layers:

- `codebaseMemory`: primary structural code graph from `codebase-memory-mcp`.
- `memoryGraph`: secondary durable project memory from MemoryGraph.

Both are local-first. Neither has broker, wallet, signing, order-placement, or live-trading
authority.

## codebaseMemory

- Binary: `tools/codebase-memory-mcp/extracted/codebase-memory-mcp.exe`
- Cache: `.cbm-cache/`
- Codex MCP env: `CBM_CACHE_DIR=C:\Users\estiv\quant\.cbm-cache`
- Auto-index: disabled
- Ignore file: `.cbmignore`

Refresh the structural index:

```powershell
python scripts\setup\index_repo_memory.py
```

## memoryGraph

- Binary: `tools/.venv-memorygraph/Scripts/memorygraph.exe`
- Database: `.memorygraph/memory.db`
- Backend: SQLite
- Tool profile: core
- Cloud backend: not configured

Codex MCP uses:

```text
MEMORY_BACKEND=sqlite
MEMORY_TOOL_PROFILE=core
MEMORY_SQLITE_PATH=C:\Users\estiv\quant\.memorygraph\memory.db
MEMORY_LOG_LEVEL=WARNING
```

Verify both memory layers:

```powershell
python scripts\setup\verify_memory_mcp.py
```

Use `--write-test` only when you intentionally want to store a test memory.
