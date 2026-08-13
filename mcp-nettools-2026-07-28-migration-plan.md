# mcp-nettools: Migration Plan for MCP Spec 2026-07-28

## Where the codebase stands today

mcp-nettools is a small, tools-only MCP server (`mcp_nettools/server.py`) built on the old high-level `FastMCP` API, pinned to `mcp>=0.2.0` (resolved to `1.6.0` in `uv.lock`). It exposes eleven synchronous tools (nmap, DNS, WHOIS, traceroute, port check, SSL scan, network scan, geolocation, HTTP headers, public IP) and nothing else — no resources, prompts, sampling, elicitation, roots, or logging. The CLI (`mcp_nettools/cli.py`) supports two transports: `stdio` (default) and the legacy `sse` transport with a hand-rolled `--port` flag. There's no auth layer, since it's meant to run locally over stdio or an unauthenticated SSE endpoint.

That footprint is actually good news for this migration: because the server doesn't touch sampling, elicitation, roots, or subscriptions, most of the protocol's stateful machinery it could have depended on was never used. The changes needed are concentrated in the SDK dependency, the transport, and a couple of small API renames — not in tool logic.

## What changed upstream and what it means here

The 2026-07-28 spec removes the `initialize` handshake and `Mcp-Session-Id`, requires `server/discover`, deprecates Roots/Sampling/Logging and the legacy HTTP+SSE transport, and adds cache hints (`ttlMs`/`cacheScope`) to list responses. The Python SDK's matching release is `mcp` **2.0.0** (current `uv.lock` pin resolves to `1.6.0`, from over 20 minor versions back).

I installed `mcp==2.0.0` in a sandbox to check the real API surface rather than guess, and confirmed one breaking change that matters directly: **`mcp.server.fastmcp.FastMCP` no longer exists.** The high-level server class moved and was renamed to `mcp.server.mcpserver.MCPServer` — this is the "client-server split" the SDK maintainers mention in the announcement (smaller package, faster imports). There's no compatibility shim, so the import in `server.py` line 21 will hard-fail on upgrade until it's changed.

The good news: the decorator API (`@mcp.tool()`), the `.settings` object, and `.run(transport=...)` all still work the same way. `run()`'s transport literal is now `"stdio" | "sse" | "streamable-http"` — `sse` still runs but is the deprecated legacy transport; `streamable-http` is the one to use for any HTTP deployment going forward. `MCPServer.__init__` also gained a `cache_hints` parameter for the new `ttlMs`/`cacheScope` fields on `tools/list`, though the SDK almost certainly supplies sane defaults so this is optional tuning, not a requirement to unblock the upgrade.

## Plan

**1. Bump the SDK dependency.** In `pyproject.toml`, change `"mcp>=0.2.0"` to `"mcp>=2.0.0,<3"`. Drop the explicit `fastapi` and `uvicorn` dependencies if they were only there to support SSE — `mcp` 2.0.0 already pulls in `starlette`, `uvicorn`, and `sse-starlette` itself for its HTTP transports, so those two lines are likely now redundant (verify after regenerating the lockfile). Regenerate `uv.lock`.

**2. Fix the import and class name in `server.py`.** Replace:
```python
from mcp.server.fastmcp import FastMCP
...
mcp = FastMCP("Network Tools MCP")
```
with:
```python
from mcp.server.mcpserver import MCPServer
...
mcp = MCPServer("Network Tools MCP")
```
No other code in `server.py` needs to change — all eleven `@mcp.tool()` functions and their Pydantic models are unaffected.

**3. Migrate the CLI off the legacy SSE transport.** In `cli.py`, the `--transport sse` path should become `--transport streamable-http` (keep `sse` accepted for one release as a deprecated alias that prints a warning, since the spec gives a 12-month deprecation window — but default new documentation and examples to `streamable-http`). The existing `mcp.settings.port = port` pattern still works unchanged for the new transport.

**4. Update `README.md`.** Replace the "Using SSE transport" section with a "Using Streamable HTTP transport" section (`uv run mcp-nettools --transport streamable-http --port 8000`), and note that `sse` is deprecated. This is also the place to correct the MCP client config example if any downstream users configure a remote endpoint.

**5. Update `examples/client_example.py`.** It uses `mcp.client.session.ClientSession` and `mcp.client.stdio.stdio_client` directly and calls `session.initialize()`. Confirm the 2.0.0 client still exposes `initialize()` as a compatibility no-op (the spec removed the handshake at the protocol level, but SDKs commonly keep a same-named call for local capability negotiation) — if it's been removed or changed, update the example accordingly. This needs a quick smoke test rather than a guess.

**6. Re-pin and smoke-test.** After the dependency and import changes, run `uv pip install -e ".[dev]"`, then run the existing test suite (`pytest`) and the client example against both `stdio` and `streamable-http` transports. The existing unit tests (`tests/test_basic.py`) only test the pure validation helpers and won't catch SDK-level breakage, so the real verification is: start the server, list tools, and call two or three tools end-to-end on each transport.

**7. Optional, not required for compliance:**
- Pass `cache_hints` to `MCPServer(...)` if you want explicit control over `tools/list` caching behavior instead of the SDK default — low priority since this tool list rarely changes at runtime.
- Consider whether `nmap_scan` and `network_scan` — the two tools capable of real side effects on a network — would benefit from the new MRTR-based elicitation pattern (a confirmation round-trip before running a scan against a range). This is a UX/safety enhancement, not something the spec requires, since the server never used sampling/elicitation/roots to begin with.
- The blog post's framing ("run in just a Worker") doesn't really apply to this server: it shells out to `nmap`/`traceroute` binaries and opens raw sockets, which need a real OS process, not a stateless edge Worker. Worth noting so nobody chases that angle expecting a lift-and-shift.

## What does *not* need to change

No tool has ever used sampling, elicitation, roots, or logging, so the deprecation of those features has no code impact. There's no OAuth/DCR flow in this server today, so the authorization-hardening changes (RFC 9207 `iss` validation, CIMD) are not applicable unless a future version adds remote auth. Tool signatures, Pydantic models, and validation logic are untouched.

## Estimated effort

This is a half-day change for one engineer: one import rename, one dependency bump, one CLI flag update, a README pass, and a manual smoke test across both transports. The risk is almost entirely in step 5 (confirming the client example's `initialize()` call and any other client-side API drift) since that's the one piece not directly exercised by the installed-package inspection above.
