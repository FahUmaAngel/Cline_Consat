"""
Minimal MCP stdio server for Cline integration.

This server intentionally avoids external MCP SDK dependencies. It implements
the JSON-RPC methods Cline needs for initialize, tools/list, and tools/call.

Cline command:
    python D:\\Hackathon\\Cline_Consat\\mcp_server.py
"""

import sys
import os

# CRITICAL: Save the raw JSON-RPC pipe and redirect ALL print() to stderr.
# Any stray print() that reaches sys.stdout corrupts the Content-Length framing
# and causes Cline to see -32001 timeouts.
_json_rpc_out = sys.stdout.buffer
sys.stdout = sys.stderr

# Ensure project modules are importable regardless of CWD
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from contextlib import redirect_stdout
from typing import Any, Callable, Dict
import io
import json
import traceback
import datetime
import audit_log as _audit

# File-based debug log — safe to write from any thread, never touches the JSON-RPC pipe
_LOG_PATH = os.path.join(_PROJECT_DIR, "mcp_debug.log")

def _log(msg: str) -> None:
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')}] {msg}\n")
    except Exception:
        pass

_router = None
_masking = None
_policy = None
_workflow = None
_bus_db = None
_data_policy = None


def _get_components():
    global _router, _masking, _policy, _workflow, _bus_db, _data_policy
    if _workflow is None:
        from data_masking_prototype import DataMaskingPipeline
        from policy_enforcement_prototype import PolicyEnforcementPipeline
        from secure_agentic_workflow import SecureAgenticWorkflow
        from sensitivity_router_prototype import SensitivityRouter
        import stockholm_bus_data as bus_db_mod
        import data_policy as data_policy_mod
        _router = SensitivityRouter()
        _masking = DataMaskingPipeline()
        _policy = PolicyEnforcementPipeline()
        _workflow = SecureAgenticWorkflow()
        _bus_db = bus_db_mod
        _data_policy = data_policy_mod
    return _router, _masking, _policy, _workflow, _bus_db, _data_policy


_DASHBOARD_URL = os.getenv("CONSAT_DASHBOARD_URL", "http://localhost:8000")


def _notify_dashboard(tool: str, args: dict, result: dict) -> None:
    """
    Send the computed result to the dashboard for monitoring — fire-and-forget.
    Runs in a daemon thread so it NEVER blocks the MCP stdin/stdout loop.
    """
    import threading

    def _post() -> None:
        try:
            import urllib.request
            body = json.dumps({"tool": tool, "args": args, "result": result}).encode("utf-8")
            req = urllib.request.Request(
                f"{_DASHBOARD_URL}/api/mcp/track",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # Dashboard unavailable — silent, never crash MCP

    threading.Thread(target=_post, daemon=True).start()


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
    {
        "name": "consat_bus_query",
        "description": "Query Stockholm bus route, vehicle, or IoT sensor data. Policy is auto-applied: PII is hashed, company secrets are redacted for external sharing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language query about bus routes, vehicles, drivers, or sensor data. Example: 'Show drivers on line 172'"},
                "table": {"type": "string", "description": "Optional specific table: bus_routes, bus_vehicles, drivers, iot_sensor_readings"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "consat_driver_lookup",
        "description": "Look up driver information by driver ID. PII fields are auto-hashed for external partners. Full data only available via local LLM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "driver_id": {"type": "string", "description": "Driver ID, e.g. DRV-1001"},
            },
            "required": ["driver_id"],
        },
    },
    {
        "name": "consat_data_policy",
        "description": "Inspect the data sharing policy rules. Shows which fields are PUBLIC, PII (hashed), or COMPANY_SECRET (redacted) for each table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Optional table name to inspect. If empty, returns all tables."},
                "query": {"type": "string", "description": "Optional query text to classify its sensitivity level."},
            },
        },
    },
    {
        "name": "consat_audit_log",
        "description": "Retrieve the ISO27001 audit trail. Returns recent structured audit events (routing decisions, data access, masking, policy checks) and a compliance summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "last_n": {"type": "integer", "description": "Number of recent events to return (default 20)."},
            },
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
    router, _, _, _, _, _ = _get_components()
    result = router.route(args["text"])
    _audit.log_routing(
        sensitivity=result.get("sensitivity_level", "unknown"),
        decision=result.get("routing_decision", "unknown"),
        reason=result.get("reason", ""),
        trace_id=_audit.new_trace_id(),
        force_override=False,
    )
    _notify_dashboard("consat_route", args, result)
    return _content(result)


def consat_mask(args: Dict[str, Any]) -> Dict[str, Any]:
    _, masking, _, _, _, _ = _get_components()
    masked_text, metadata = masking.process_for_cloud(args["text"])
    masked_count = sum(len(v) for v in metadata.get("masked_items", {}).values()) if metadata else 0
    _audit.log_masking("mcp_mask_request", masked_count, trace_id=_audit.new_trace_id())
    return _content(
        {
            "masked_text": masked_text,
            "metadata": metadata,
            "summary": masking.get_summary(),
        }
    )


def consat_policy_check(args: Dict[str, Any]) -> Dict[str, Any]:
    _, _, policy, _, _, _ = _get_components()
    validation = policy.validate_ai_output(args["code"])
    _audit.log_policy_check(
        approved=validation.get("code_approved", False),
        violations=validation.get("critical_violations", 0),
        trace_id=_audit.new_trace_id(),
    )
    return _content(
        {
            "result": validation,
            "summary": policy.get_summary(),
        }
    )


def consat_workflow_process(args: Dict[str, Any]) -> Dict[str, Any]:
    _, _, _, workflow, _, _ = _get_components()
    log_buffer = io.StringIO()
    with redirect_stdout(log_buffer):
        result = workflow.process(args["user_input"], args.get("llm_output"))
    result["user_input"] = args["user_input"]
    _notify_dashboard("consat_workflow_process", args, result)
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
    _, _, _, workflow, _, _ = _get_components()
    return _content(
        {
            "workflow_stats": workflow.get_stats(),
            "monitoring": workflow.monitoring.calculator.calculate_stats(),
            "health": workflow.monitoring.get_health_status(),
            "alerts": workflow.monitoring.metrics_collector.get_all_alerts()[-20:],
        }
    )


def consat_bus_query(args: Dict[str, Any]) -> Dict[str, Any]:
    _, _, _, _, bus_db, data_policy = _get_components()
    query = args["query"]
    classification = data_policy.classify_query(query)
    raw_results = bus_db.search_data(query)
    filtered = {}
    table_map = {
        "routes":      "bus_routes",
        "vehicles":    "bus_vehicles",
        "drivers":     "drivers",
        "readings":    "iot_sensor_readings",
        "stops":       "bus_stops",
        "maintenance": "maintenance_logs",
        "shifts":      "driver_shifts",
        "incidents":   "incidents",
    }
    for key, table_name in table_map.items():
        if raw_results.get(key):
            filtered[key] = data_policy.filter_for_external(table_name, raw_results[key])
    result = {
        "query_classification": classification,
        "filtered_results": filtered,
        "record_counts": {k: len(v) for k, v in filtered.items()},
        "policy_applied": True,
        "note": "PII fields are hashed, COMPANY_SECRET fields are redacted for external sharing.",
    }
    _notify_dashboard("consat_bus_query", args, result)
    return _content(result)


def consat_driver_lookup(args: Dict[str, Any]) -> Dict[str, Any]:
    _, _, _, _, bus_db, data_policy = _get_components()
    driver_id = args["driver_id"]
    matches = [d for d in bus_db.DRIVERS if d["driver_id"] == driver_id]
    if not matches:
        return _content({"error": f"Driver {driver_id} not found", "available_ids": [d['driver_id'] for d in bus_db.DRIVERS]})
    raw = matches[0]
    filtered = data_policy.filter_record_for_external("drivers", raw)
    tid = _audit.new_trace_id()
    _audit.log_data_access("drivers", "hash", "PII", trace_id=tid, actor="mcp_server")
    result = {
        "driver_filtered": filtered,
        "policy_applied": True,
        "trace_id": tid,
        "fields_hashed": [f for f, p in data_policy.POLICY_TABLE["drivers"].items() if p["action"] == "hash"],
        "fields_encrypted": [f for f, p in data_policy.POLICY_TABLE["drivers"].items() if p["action"] == "encrypt"],
        "fields_redacted": [f for f, p in data_policy.POLICY_TABLE["drivers"].items() if p["action"] == "redact"],
        "note": "Full unfiltered data only available via LOCAL LLM.",
    }
    _notify_dashboard("consat_driver_lookup", args, result)
    return _content(result)


def consat_data_policy(args: Dict[str, Any]) -> Dict[str, Any]:
    _, _, _, _, _, data_policy = _get_components()
    result = {}
    table = args.get("table")
    query = args.get("query")
    if table:
        result["table_policy"] = data_policy.get_table_policy_summary(table)
    else:
        result["all_policies"] = data_policy.get_full_policy_summary()
    if query:
        result["query_classification"] = data_policy.classify_query(query)
    result["classification_levels"] = {
        "PUBLIC": "Share freely with external partners",
        "PII": "Share only with hash or encryption (GDPR)",
        "COMPANY_SECRET": "Never share externally — local LLM only",
    }
    return _content(result)


def consat_audit_log(args: Dict[str, Any]) -> Dict[str, Any]:
    last_n = int(args.get("last_n", 20))
    return _content({
        "recent_events": _audit.get_recent_events(last_n),
        "summary": _audit.get_audit_summary(),
        "log_file": "audit_trail.jsonl",
        "note": "Append-only audit trail. Required for ISO27001 A.12.4 logging and monitoring.",
    })


TOOL_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "consat_route": consat_route,
    "consat_mask": consat_mask,
    "consat_policy_check": consat_policy_check,
    "consat_workflow_process": consat_workflow_process,
    "consat_metrics": consat_metrics,
    "consat_bus_query": consat_bus_query,
    "consat_driver_lookup": consat_driver_lookup,
    "consat_data_policy": consat_data_policy,
    "consat_audit_log": consat_audit_log,
}


def read_message() -> Dict[str, Any] | None:
    """Read one newline-delimited JSON message from stdin (MCP 2025-11-25 transport)."""
    _log("READ_MSG waiting...")
    raw = sys.stdin.buffer.readline()
    if not raw:
        _log("READ_MSG got EOF")
        return None
    _log(f"READ_MSG raw: {raw[:120]!r}")
    line = raw.strip()
    if not line:
        return read_message()  # skip blank lines
    return json.loads(line.decode("utf-8"))


def send_message(message: Dict[str, Any]) -> None:
    """Send one newline-delimited JSON message to stdout (MCP 2025-11-25 transport)."""
    body = json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"
    _json_rpc_out.write(body)
    _json_rpc_out.flush()


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
                "protocolVersion": "2025-11-25",
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
            _log(f"TOOL_START {name}")
            result = handler(arguments)
            _log(f"TOOL_END   {name}")
            return success(request_id, result)
        except Exception as exc:
            details = traceback.format_exc(limit=4)
            _log(f"TOOL_ERROR {name}: {exc}")
            return error(request_id, -32000, f"{exc}\n{details}")

    if request_id is None:
        return None
    return error(request_id, -32601, f"Unknown method: {method}")


def main() -> None:
    _log("SERVER_START")
    while True:
        request = read_message()
        if request is None:
            _log("SERVER_EOF — exiting")
            break
        method = request.get("method", "?")
        _log(f"RECV {method}")
        response = handle(request)
        if response is not None:
            _log(f"SEND response for {method}")
            send_message(response)


if __name__ == "__main__":
    _log(f"MAIN_START pid={os.getpid()}")
    main()
