"""Main entry point for the Workflow Orchestrator MCP Server package."""

import asyncio
from . import server

if __name__ == "__main__":
    asyncio.run(server.main())
