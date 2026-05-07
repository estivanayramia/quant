# MCP And Data Setup

Last updated: 2026-05-06.

## Codex MCPs

- `openaiDeveloperDocs`: official OpenAI Developer Docs MCP at
  `https://developers.openai.com/mcp`.
- `github`: official GitHub remote MCP at
  `https://api.githubcopilot.com/mcp/readonly`, using bearer token environment variable
  `GITHUB_TOKEN` and header `X-MCP-Toolsets=repos,pull_requests,actions`.
- `playwright`: `npx @playwright/mcp@latest`, kept as a light ad hoc browser helper.

## GitHub Auth

No GitHub token environment variable was present during setup. The GitHub MCP entry is
ready, but it only authenticates in Codex sessions launched with `GITHUB_TOKEN` set to a
read-only or least-privilege PAT that can read the target repository, pull requests, and
Actions metadata.

The local `gh` CLI was authenticated through keyring, but that token was not copied into
Codex config.

## DuckDB

DuckDB is available through Python. The signed community `duckdb_mcp` extension installs
and loads successfully with:

```sql
INSTALL duckdb_mcp FROM community;
LOAD duckdb_mcp;
```

This repo intentionally does not expose a broad DuckDB SQL MCP server to Codex by default.
Even a read-only SQL endpoint can read arbitrary local files through table functions if it
is not tightly sandboxed. Use `scripts/data/verify_duckdb_local.py` for local CSV/Parquet
inspection and add narrower tools later only after a filesystem access review.

## Codebase Memory MCP

Installed candidate: `DeusData/codebase-memory-mcp` v0.6.1, a local static Windows binary
with Codex CLI support.

Setup choices:

- Downloaded manually instead of running its installer, because the installer can write agent
  config and user PATH automatically.
- Verified the release checksum before extraction.
- Added Codex MCP entry `codebaseMemory` manually.
- Set `CBM_CACHE_DIR` to ignored repo-local `.cbm-cache`.
- Left `auto_index = false`.
- Added `.cbmignore` to skip external clones, local MCP binaries, caches, generated reports,
  and browser/data artifacts.
