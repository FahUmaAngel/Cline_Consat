"""
Minimal MCP stdio server for Cline integration.

This server intentionally avoids external MCP SDK dependencies. It implements
the JSON-RPC methods Cline needs for initialize, tools/list, and tools/call.

Cline command:
    python D:\\Hackathon\\Cline_Consat\\mcp_server.py
"""

from contextlib import redirect_stdout
from typing import Any, Callable, Dict
import io
import json
import sys
import traceback

from data_masking_prototype import DataMaskingPipeline
from policy_enforcement_prototype import PolicyEnforcementPipeline
from secure_agentic_workflow import SecureAgenticWorkflow
from sensitivity_router_prototype import SensitivityRouter


router = SensitivityRouter()
masking = DataMaskingPipeline()
policy = PolicyEnforcementPipeline()
workflow = SecureAgenticWorkflow()


TOOLS = [
    {
        "name": "consat_route",
        "description": "Classify input sensitivity and decide whether to use local or cloud LLM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Prompt or code to classify."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "consat_mask",
        "description": "Mask CONSAT-sensitive values before sending content to a cloud LLM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to mask."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "consat_policy_check",
        "description": "Validate generated code against CONSAT security and compliance rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code or LLM output to inspect."},
            },
            "required": ["code"],
        },
    },
    {
        "name": "consat_workflow_process",
        "description": "Run the full secure agentic workflow: route, mask, validate policy, and record metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_input": {"type": "string", "description": "User prompt or request."},
                "llm_output": {"type": "string", "description": "Optional generated output to validate."},
            },
            "required": ["user_input"],
        },
    },
    {
        "name": "consat_metrics",
        "description": "Return workflow, monitoring, health, and alert metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _content(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        ]
    }


def consat_route(args: Dict[str, Any]) -> Dict[str, Any]:
    return _content(router.route(args["text"]))


def consat_mask(args: Dict[str, Any]) -> Dict[str, Any]:
    masked_text, metadata = masking.process_for_cloud(args["text"])
    return _content(
        {
            "masked_text": masked_text,
            "metadata": metadata,
            "summary": masking.get_summary(),
        }
    )


def consat_policy_check(args: Dict[str, Any]) -> Dict[str, Any]:
    return _content(
        {
            "result": policy.validate_ai_output(args["code"]),
            "summary": policy.get_summary(),
        }
    )


def consat_workflow_process(args: Dict[str, Any]) -> Dict[str, Any]:
    log_buffer = io.StringIO()
    with redirect_stdout(log_buffer):
        result = workflow.process(args["user_input"], args.get("llm_output"))
    result["user_input"] = args["user_input"]
    return _content(
        {
            "success": True,
            "result": result,
            "logs": log_buffer.getvalue().splitlines()[-30:],
            "stats": workflow.get_stats(),
            "health": workflow.monitoring.get_health_status(),
        }
    )


def consat_metrics(args: Dict[str, Any]) -> Dict[str, Any]:
    return _content(
        {
            "workflow_stats": workflow.get_stats(),
            "monitoring": workflow.monitoring.calculator.calculate_stats(),
            "health": workflow.monitoring.get_health_status(),
            "alerts": workflow.monitoring.metrics_collector.get_all_alerts()[-20:],
        }
    )


TOOL_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "consat_route": consat_route,
    "consat_mask": consat_mask,
    "consat_policy_check": consat_policy_check,
    "consat_workflow_process": consat_workflow_process,
    "consat_metrics": consat_metrics,
}


def read_message() -> Dict[str, Any] | None:
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        line = line.decode("utf-8").strip()
        if not line:
            break
        key, value = line.split(":", 1)
        headers[key.lower()] = value.strip()

    content_length = int(headers.get("content-length", "0"))
    if content_length <= 0:
        return None
    body = sys.stdin.buffer.read(content_length)
    return json.loads(body.decode("utf-8"))


def send_message(message: Dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def success(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(request: Dict[str, Any]) -> Dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}

    if method == "initialize":
        return success(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "consat-secure-workflow", "version": "1.0.0"},
            },
        )

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return success(request_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return error(request_id, -32601, f"Unknown tool: {name}")
        try:
            return success(request_id, handler(arguments))
        except Exception as exc:
            details = traceback.format_exc(limit=4)
            return error(request_id, -32000, f"{exc}\n{details}")

    if request_id is None:
        return None
    return error(request_id, -32601, f"Unknown method: {method}")


def main() -> None:
    while True:
        request = read_message()
        if request is None:
            break
        response = handle(request)
        if response is not None:
            send_message(response)


if __name__ == "__main__":
    main()
