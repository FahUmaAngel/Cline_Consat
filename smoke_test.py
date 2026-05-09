"""Smoke tests for CONSAT API and MCP integration."""

import asyncio
import json

import api_service as api
import mcp_server


async def test_api_handlers():
    ctx = api.lifespan(api.app)
    await ctx.__aenter__()
    try:
        health = await api.health()
        route = await api.route_text(
            api.RouteRequest(text="api_key=sk-proj-test12345678901234567890")
        )
        masked = await api.mask_text(
            api.MaskRequest(text="Contact EMP-12345 at john@consat.com")
        )
        policy = await api.check_policy(
            api.PolicyCheckRequest(code='password = "secret123"')
        )
        workflow = await api.process_workflow(
            api.WorkflowRequest(user_input="Create hello function", llm_output="print(123)")
        )

        assert health["status"] == "healthy"
        assert route["result"]["routing_decision"] == "local"
        assert masked["metadata"]["masked_items"]
        assert policy["result"]["code_approved"] is False
        assert workflow["success"] is True
        assert workflow["state"]["workflow_stats"]["total_requests"] == 1
    finally:
        await ctx.__aexit__(None, None, None)


def test_mcp_handlers():
    initialize = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    tools = mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    route = mcp_server.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "consat_route",
                "arguments": {"text": "vpn config for jump.consat.internal"},
            },
        }
    )

    assert initialize["result"]["serverInfo"]["name"] == "consat-secure-workflow"
    assert len(tools["result"]["tools"]) >= 5
    route_payload = json.loads(route["result"]["content"][0]["text"])
    assert route_payload["routing_decision"] == "local"


async def main():
    await test_api_handlers()
    test_mcp_handlers()
    print("SMOKE_TEST_OK")


if __name__ == "__main__":
    asyncio.run(main())
