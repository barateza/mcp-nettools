#!/usr/bin/env python3
"""
CLI entry point for MCP Network Tools server.
"""
import sys
from .server import mcp


def main():
    """Run the MCP server with the specified transport."""
    # Default to stdio transport
    transport = "stdio"
    port = 8000

    # Parse command line args
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--transport" and i+2 <= len(sys.argv[1:]):
            transport = sys.argv[i+2]
        elif arg == "--port" and i+2 <= len(sys.argv[1:]):
            port = int(sys.argv[i+2])

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        # host/port are runtime options passed straight to run(), not fields
        # on mcp.settings (that changed in mcp 2.0.0). `stateless_http=True`
        # opts into the MCP 2026-07-28 stateless protocol core: no
        # Mcp-Session-Id, no shared server-side state, so requests can land
        # on any instance behind a plain load balancer.
        mcp.run(transport="streamable-http", port=port, stateless_http=True)
    elif transport == "sse":
        # Deprecated as of MCP spec 2026-07-28. The legacy HTTP+SSE transport
        # still works during the deprecation window, but new deployments
        # should use --transport streamable-http instead.
        print(
            "Warning: the 'sse' transport is deprecated per the MCP "
            "2026-07-28 specification. Use --transport streamable-http instead.",
            file=sys.stderr,
        )
        mcp.run(transport="sse", port=port)
    else:
        print(f"Unknown transport: {transport}")
        sys.exit(1)


if __name__ == "__main__":
    main()