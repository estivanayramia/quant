"""Verify quant repo memory MCP setup.

Default checks are read-only. Pass `--write-test` to intentionally store and
search one MemoryGraph verification memory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CODEX_EXE = Path.home() / ".codex" / ".sandbox-bin" / "codex.exe"
CBM_EXE = REPO_ROOT / "tools" / "codebase-memory-mcp" / "extracted" / "codebase-memory-mcp.exe"
CBM_CACHE_DIR = REPO_ROOT / ".cbm-cache"
MEMORYGRAPH_EXE = REPO_ROOT / "tools" / ".venv-memorygraph" / "Scripts" / "memorygraph.exe"
MEMORYGRAPH_PYTHON = REPO_ROOT / "tools" / ".venv-memorygraph" / "Scripts" / "python.exe"
MEMORYGRAPH_DB = REPO_ROOT / ".memorygraph" / "memory.db"


def ensure_memorygraph_python() -> None:
    if not MEMORYGRAPH_PYTHON.exists():
        raise SystemExit(f"Missing MemoryGraph Python: {MEMORYGRAPH_PYTHON}")
    try:
        current = Path(sys.executable).resolve()
        target = MEMORYGRAPH_PYTHON.resolve()
    except OSError:
        return
    if current != target:
        result = subprocess.run(
            [str(MEMORYGRAPH_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
            cwd=REPO_ROOT,
            text=True,
        )
        raise SystemExit(result.returncode)


def parse_json_prefix(text: str) -> Any:
    decoder = json.JSONDecoder()
    stripped = text.lstrip()
    value, _ = decoder.raw_decode(stripped)
    return value


def run(command: list[str], env: dict[str, str] | None = None, timeout: int = 60) -> str:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout.strip()


def memorygraph_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "MEMORY_BACKEND": "sqlite",
            "MEMORY_TOOL_PROFILE": "core",
            "MEMORY_SQLITE_PATH": str(MEMORYGRAPH_DB),
            "MEMORY_LOG_LEVEL": "WARNING",
        }
    )
    return env


def verify_codebase_memory() -> dict[str, Any]:
    if not CBM_EXE.exists():
        raise SystemExit(f"Missing codebase-memory-mcp binary: {CBM_EXE}")

    env = os.environ.copy()
    env["CBM_CACHE_DIR"] = str(CBM_CACHE_DIR)
    version = run([str(CBM_EXE), "--version"], env=env)
    project = "C-Users-estiv-quant"
    search = run(
        [
            str(CBM_EXE),
            "cli",
            "search_graph",
            json.dumps(
                {
                    "project": project,
                    "label": "Function",
                    "name_pattern": ".*lane.*|.*readiness.*|.*replay.*",
                    "limit": 8,
                }
            ),
        ],
        env=env,
    )
    return {"version": version, "structural_search": json.loads(search)}


async def memorygraph_tools(write_test: bool) -> dict[str, Any]:
    if not MEMORYGRAPH_PYTHON.exists():
        raise SystemExit(f"Missing MemoryGraph Python: {MEMORYGRAPH_PYTHON}")

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async with stdio_client(
        StdioServerParameters(command=str(MEMORYGRAPH_EXE), args=[], env=memorygraph_env())
    ) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result: dict[str, Any] = {"tools": [tool.name for tool in tools.tools]}

        if write_test:
            stored = await session.call_tool(
                "store_memory",
                {
                    "type": "project",
                    "title": "MemoryGraph verification",
                    "content": (
                        "Intentional write-test memory for quant MemoryGraph setup. "
                        "MemoryGraph is local SQLite only and secondary to codebase-memory-mcp."
                    ),
                    "tags": ["quant", "memory-layer", "verification"],
                    "importance": 0.4,
                    "context": {"project_path": str(REPO_ROOT)},
                },
            )
            found = await session.call_tool(
                "search_memories",
                {"query": "MemoryGraph verification", "tags": ["verification"], "limit": 3},
            )
            result["write_test_store"] = stored.content[0].text if stored.content else str(stored)
            result["write_test_search"] = found.content[0].text if found.content else str(found)
        return result


def verify_memorygraph(write_test: bool) -> dict[str, Any]:
    if not MEMORYGRAPH_EXE.exists():
        raise SystemExit(f"Missing MemoryGraph executable: {MEMORYGRAPH_EXE}")
    version = run([str(MEMORYGRAPH_EXE), "--version"], env=memorygraph_env())
    health = run([str(MEMORYGRAPH_EXE), "--health", "--health-json"], env=memorygraph_env())
    tools = subprocess.run(
        [str(MEMORYGRAPH_PYTHON), "-c", "import mcp; print('mcp client ok')"],
        cwd=REPO_ROOT,
        env=memorygraph_env(),
        text=True,
        capture_output=True,
        timeout=30,
    )
    if tools.returncode != 0:
        raise SystemExit(tools.stderr)
    return {
        "version": version,
        "health": parse_json_prefix(health),
        "mcp": asyncio.run(memorygraph_tools(write_test)),
    }


def main() -> int:
    ensure_memorygraph_python()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-test", action="store_true")
    args = parser.parse_args()

    codex_list = run([str(CODEX_EXE), "mcp", "list"]) if CODEX_EXE.exists() else "codex.exe missing"
    report = {
        "codex_mcp_list_contains": {
            "codebaseMemory": "codebaseMemory" in codex_list,
            "memoryGraph": "memoryGraph" in codex_list,
        },
        "codebase_memory": verify_codebase_memory(),
        "memorygraph": verify_memorygraph(args.write_test),
    }
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
