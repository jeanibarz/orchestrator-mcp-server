"""Workflow Orchestrator MCP Server Package."""

import asyncio

from . import server


def main() -> None:
    """Run the main entry point for the package."""
    asyncio.run(server.main())


# Optionally expose other important items at package level
__all__ = ["main", "server"]
