"""Main entry point for the Workflow Orchestrator MCP Server package."""

import asyncio
from . import server


def run_server():
    """Runs the main server asynchronous function."""
    # Consider adding argument parsing here if needed
    asyncio.run(server.main())


if __name__ == "__main__":
    run_server()
