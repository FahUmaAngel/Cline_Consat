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
        "description": "Mask CONSAT-sensitive values before sending content to a cloud LLM. Runs two passes: (1) schema-aware column masking against the POLICY_TABLE, then (2) regex pattern masking for emails, API keys, personnummer, etc.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to mask (can contain JSON with field names from the bus data schema)."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "consat_schema_mask",
        "description": "Apply schema-aware column masking directly: scan any JSON for field names that appear in the bus-data POLICY_TABLE and apply hash / encrypt / redact per column automatically. Use this to test or demonstrate column-level policy enforcement without going through the full workflow.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "JSON string or text containing JSON blocks with field names from the bus data schema."},
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
    return _content(router.route(args["text"]))


def consat_mask(args: Dict[str, Any]) -> Dict[str, Any]:
    _, masking, _, _, _, _ = _get_components()
    masked_text, metadata = masking.process_for_cloud(args["text"])
    schema_report = metadata.get("schema_masking", {})
    return _content(
        {
            "masked_text": masked_text,
            "metadata": metadata,
            "summary": masking.get_summary(),
            "schema_masking_report": {
                "fields_masked_by_column_policy": schema_report.get("fields_masked", 0),
                "tables_detected": schema_report.get("tables_detected", []),
                "hashed_fields":   schema_report.get("by_action", {}).get("hash", []),
                "encrypted_fields": schema_report.get("by_action", {}).get("encrypt", []),
                "redacted_fields": schema_report.get("by_action", {}).get("redact", []),
            },
        }
    )


def consat_schema_mask(args: Dict[str, Any]) -> Dict[str, Any]:
    """Standalone schema-aware column masking — no regex, just POLICY_TABLE."""
    import schema_aware_masker as sam
    masked_text, report = sam.scan_and_mask(args["text"])
    return _content({
        "masked_text": masked_text,
        "fields_masked": report["fields_masked"],
        "tables_detected": report["tables_detected"],
        "hashed_fields":   report["by_action"]["hash"],
        "encrypted_fields": report["by_action"]["encrypt"],
        "redacted_fields": report["by_action"]["redact"],
        "full_events": report["events"],
        "note": "Policy applied from POLICY_TABLE: PII fields are hashed/encrypted, COMPANY_SECRET fields are redacted.",
    })


def consat_policy_check(args: Dict[str, Any]) -> Dict[str, Any]:
    _, _, policy, _, _, _ = _get_components()
    return _content(
        {
            "result": policy.validate_ai_output(args["code"]),
            "summary": policy.get_summary(),
        }
    )


def consat_workflow_process(args: Dict[str, Any]) -> Dict[str, Any]:
    _, _, _, workflow, _, _ = _get_components()
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
        "routes": "bus_routes",
        "vehicles": "bus_vehicles",
        "drivers": "drivers",
        "readings": "iot_sensor_readings",
    }
    for key, table_name in table_map.items():
        if raw_results.get(key):
            filtered[key] = data_policy.filter_for_external(table_name, raw_results[key])
    return _content({
        "query_classification": classification,
        "filtered_results": filtered,
        "record_counts": {k: len(v) for k, v in filtered.items()},
        "policy_applied": True,
        "note": "PII fields are hashed, COMPANY_SECRET fields are redacted for external sharing.",
    })


def consat_driver_lookup(args: Dict[str, Any]) -> Dict[str, Any]:
    _, _, _, _, bus_db, data_policy = _get_components()
    driver_id = args["driver_id"]
    matches = [d for d in bus_db.DRIVERS if d["driver_id"] == driver_id]
    if not matches:
        return _content({"error": f"Driver {driver_id} not found", "available_ids": [d['driver_id'] for d in bus_db.DRIVERS]})
    raw = matches[0]
    filtered = data_policy.filter_record_for_external("drivers", raw)
    return _content({
        "driver_filtered": filtered,
        "policy_applied": True,
        "fields_hashed": [f for f, p in data_policy.POLICY_TABLE["drivers"].items() if p["action"] == "hash"],
        "fields_encrypted": [f for f, p in data_policy.POLICY_TABLE["drivers"].items() if p["action"] == "encrypt"],
        "fields_redacted": [f for f, p in data_policy.POLICY_TABLE["drivers"].items() if p["action"] == "redact"],
        "note": "Full unfiltered data only available via LOCAL LLM.",
    })


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


TOOL_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "consat_route": consat_route,
    "consat_mask": consat_mask,
    "consat_schema_mask": consat_schema_mask,
    "consat_policy_check": consat_policy_check,
    "consat_workflow_process": consat_workflow_process,
    "consat_metrics": consat_metrics,
    "consat_bus_query": consat_bus_query,
    "consat_driver_lookup": consat_driver_lookup,
    "consat_data_policy": consat_data_policy,
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
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.lower()] = value.strip()

    content_length = int(headers.get("content-length", "0"))
    if content_length <= 0:
        return None
    body = sys.stdin.buffer.read(content_length)
    return json.loads(body.decode("utf-8"))


def send_message(message: Dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    _json_rpc_out.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
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
