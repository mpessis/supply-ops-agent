# supply-ops-agent

Python MCP server for sell-side ad ops diagnostics.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python server.py
```

## Conventions

- Python 3.10+, type hints on all functions
- No web UI, no Docker — runs as a stdio MCP server
- All data is synthetic mock data, no external API calls
- MCP SDK: `mcp` package (pip install mcp)
- No tests yet — manual testing via Claude Desktop or Claude Code MCP client
