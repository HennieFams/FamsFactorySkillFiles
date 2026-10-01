#!/usr/bin/env python3
"""Read-only Freshdesk MCP server (optional) - wraps freshdesk_api.py, which only does GET calls.
The agent normally uses freshdesk.py (command line) instead; this is for setups that load MCP servers."""
try:
    from mcp.server.fastmcp import FastMCP  # mcp 1.x
except ImportError:  # mcp 2.x renamed it
    from mcp.server.mcpserver import MCPServer as FastMCP  # type: ignore

import freshdesk_api as api

mcp = FastMCP("freshdesk")
for fn in (api.list_recent_tickets, api.get_ticket, api.get_ticket_conversation,
           api.get_contact, api.search_tickets):
    mcp.tool()(fn)

if __name__ == "__main__":
    mcp.run()
