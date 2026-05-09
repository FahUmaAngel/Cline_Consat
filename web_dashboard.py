"""
Web Dashboard for Secure Agentic Workflow
==========================================
Real-time monitoring UI using FastAPI + HTML/JS

Author: CONSAT PoC Team
Date: May 4, 2026
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
import asyncio
import io
import time
import uvicorn

# Import our existing components
from monitoring_dashboard_prototype import MonitoringDashboard
from secure_agentic_workflow import SecureAgenticWorkflow
import stockholm_bus_data as bus_db
import file_vault
import data_policy
import audit_log as _audit

# Global components
dashboard = None
workflow = None
active_connections = []

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Map legacy Thai routing reasons to English (for in-memory or on-disk entries
# written before the translation was applied to sensitivity_router_prototype.py)
_THAI_TRANSLATIONS: dict = {
    "HIGH SENSITIVITY data -> force Local LLM for security": "HIGH SENSITIVITY data -> force Local LLM for security",
    "MEDIUM SENSITIVITY data -> route to Cloud after Data Masking": "MEDIUM SENSITIVITY data -> route to Cloud after Data Masking",
    "LOW SENSITIVITY data -> route to Cloud LLM for performance": "LOW SENSITIVITY data -> route to Cloud LLM for performance",
}

def _translate(text: str) -> str:
    """Translate a known Thai string to English; pass through anything else."""
    return _THAI_TRANSLATIONS.get(text, text)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app"""
    global dashboard, workflow

    # Startup
    print("Starting CONSAT Web Dashboard...")
    workflow = SecureAgenticWorkflow()
    dashboard = workflow.monitoring

    yield

    # Shutdown
    print("Shutting down CONSAT Web Dashboard...")

# FastAPI app
app = FastAPI(
    title="CONSAT Secure Agentic Workflow Dashboard",
    lifespan=lifespan
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _get_dashboard():
    if workflow:
        return workflow.monitoring
    return dashboard


def _classify_from_patterns(item):
    """Derive the 4-tier data classification from the query's detected patterns.

    Classification is based on what the USER ASKED (sensitivity router output),
    not on what fields appeared in the database context.  The schema masker
    always processes all columns of retrieved records, so redacted_fields being
    non-empty does NOT mean the user asked for company secrets.
    """
    patterns = item.get("routing", {}).get("detected_patterns", [])
    sensitivity = item.get("routing", {}).get("sensitivity_level", "low")

    # No patterns detected → PUBLIC
    if not patterns:
        return "PUBLIC"

    # Vault upload tier patterns (tier:SECRET, tier:SPII, tier:PII, tier:PUBLIC)
    vault_tier_map = {
        "tier:secret": "COMPANY_SECRET",
        "tier:spii": "SPII",
        "tier:pii": "PII",
        "tier:public": "PUBLIC",
    }
    for p in patterns:
        mapped = vault_tier_map.get(p.lower())
        if mapped:
            return mapped

    # Check for COMPANY_SECRET indicators in detected patterns
    secret_keywords = [
        "consat_eco_drive", "consat_iot_internal", "consat_operations",
        "consat_finance", "business_secret",
    ]
    has_secret = any(
        any(kw in p.lower() for kw in secret_keywords)
        for p in patterns
    )
    if has_secret:
        return "COMPANY_SECRET"

    # Check for SPII indicators in detected patterns
    spii_keywords = ["personnummer", "personal_number", "license_number"]
    has_spii = any(
        any(kw in p.lower() for kw in spii_keywords)
        for p in patterns
    )
    if has_spii:
        return "SPII"

    # Check for PII indicators in detected patterns
    pii_prefixes = ["PII:", "KEYWORD:consat_driver_pii"]
    has_pii = any(
        any(p.startswith(prefix) or prefix in p for prefix in pii_prefixes)
        for p in patterns
    )
    if has_pii:
        return "PII"

    # Patterns detected but none matched specific tiers — use sensitivity level
    if sensitivity == "high":
        return "PII"  # HIGH but unknown type → treat as PII
    return "PUBLIC"


def _serialize_history(limit: int = 20):
    if not workflow:
        return []

    serialized = []
    for item in workflow.request_history[-limit:]:
        row = dict(item)
        row["input_preview"] = item.get("user_input", "Workflow request")
        row["route"] = item.get("routing", {}).get("llm_used", "unknown")
        row["sensitivity"] = item.get("routing", {}).get("sensitivity_level", "unknown")
        row["processing_time_ms"] = item.get("metrics", {}).get("processing_time_ms", "0")
        row["masked_items_count"] = item.get("metrics", {}).get("masked_items_count", 0)
        row["critical_violations"] = item.get("policy_check", {}).get("critical_violations", 0)
        row["force_overridden"] = item.get("force_overridden", False)
        row["secured_locally"] = item.get("secured_locally", False)
        row["force_route"] = item.get("force_route", "auto")
        # Rich policy data for the UI
        row["detected_patterns"] = item.get("routing", {}).get("detected_patterns", [])
        row["routing_reason"] = _translate(item.get("routing", {}).get("reason", ""))
        row["schema_masking"] = item.get("schema_masking", {})
        row["policy_violations"] = item.get("policy_check", {}).get("violations", [])
        row["data_classification"] = _classify_from_patterns(item)
        serialized.append(row)
    return serialized


def _payload(history_limit: int = 20):
    current_dashboard = _get_dashboard()
    if not current_dashboard:
        raise HTTPException(status_code=503, detail="Dashboard not initialized")

    stats = current_dashboard.calculator.calculate_stats()
    health = current_dashboard.get_health_status()
    workflow_stats = workflow.get_stats() if workflow else {"total_requests": 0}

    return {
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "health": health,
        "workflow_stats": workflow_stats,
        "alerts": current_dashboard.metrics_collector.get_all_alerts()[-10:],
        "history": _serialize_history(history_limit),
    }

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Serve main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request, "active_page": "monitor"})

@app.get("/dashboard.html", response_class=HTMLResponse)
async def get_dashboard_html(request: Request):
    """Serve dashboard page when opened by its file-like URL."""
    return templates.TemplateResponse("dashboard.html", {"request": request, "active_page": "monitor"})

@app.get("/data-explorer", response_class=HTMLResponse)
async def get_data_explorer(request: Request):
    """Serve data explorer page."""
    return templates.TemplateResponse("data-explorer.html", {"request": request, "active_page": "data-explorer"})

@app.get("/file-vault", response_class=HTMLResponse)
async def get_file_vault(request: Request):
    """Serve file vault page."""
    return templates.TemplateResponse("file-vault.html", {"request": request, "active_page": "file-vault"})

# ── File Vault API ──────────────────────────────────────────────

@app.post("/api/vault/upload")
async def vault_upload(
    file: UploadFile = File(...),
    tier: str = Form(None),
    tags: str = Form(""),
    description: str = Form(""),
):
    """Upload a file to the vault."""
    content = await file.read()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    entry = file_vault.add_file(
        filename=file.filename,
        content_bytes=content,
        tier=tier if tier else None,
        tags=tag_list,
        description=description,
    )

    # ── Push audit event into dashboard history stream ──────────
    assigned_tier = entry["tier"]
    tier_to_sensitivity = {
        "PUBLIC": "low", "PII": "medium", "SPII": "high", "SECRET": "high"
    }
    tier_to_route = {
        "PUBLIC": "cloud", "PII": "local", "SPII": "local", "SECRET": "local"
    }
    tier_to_status = {
        "PUBLIC": "approved", "PII": "approved", "SPII": "blocked", "SECRET": "approved"
    }

    # ── Write ISO27001 audit trail entries ───────────────────────
    trace_id = _audit.new_trace_id()
    sensitivity_label = tier_to_sensitivity.get(assigned_tier, "low").upper()
    llm_decision = tier_to_route.get(assigned_tier, "local")
    _audit.log_routing(
        sensitivity=sensitivity_label,
        decision=llm_decision,
        reason=f"Vault upload — auto-classified as {assigned_tier} → routed to {llm_decision.upper()} LLM",
        trace_id=trace_id,
    )
    if assigned_tier in ("PII", "SPII", "SECRET"):
        _audit.log_masking("vault_file", 1, trace_id=trace_id)
    violations = 1 if assigned_tier == "SPII" else 0
    _audit.log_policy_check(violations == 0, violations, trace_id=trace_id)

    if workflow:
        workflow.request_history.append({
            "event_type": "vault_upload",
            "timestamp": time.time(),
            "user_input": f"File uploaded: {entry['filename']}",
            "status": tier_to_status.get(assigned_tier, "approved"),
            "routing": {
                "llm_used": tier_to_route.get(assigned_tier, "local"),
                "sensitivity_level": tier_to_sensitivity.get(assigned_tier, "low"),
                "detected_patterns": [f"tier:{assigned_tier}"],
                "reason": f"Vault upload — auto-classified as {assigned_tier}",
            },
            "metrics": {
                "processing_time_ms": 0,
                "masked_items_count": 1 if assigned_tier in ("PII", "SPII", "SECRET") else 0,
            },
            "policy_check": {
                "critical_violations": 1 if assigned_tier == "SPII" else 0,
            },
            "vault_file": {
                "file_id": entry["file_id"],
                "filename": entry["filename"],
                "tier": assigned_tier,
                "size_bytes": entry["size_bytes"],
            },
        })

    if workflow:
        workflow.monitoring.record_request(
            routing_decision=llm_decision,
            processing_time=0,
            masked_items=1 if assigned_tier in ("PII", "SPII", "SECRET") else 0,
            policy_violations=violations,
            sensitivity_level=tier_to_sensitivity.get(assigned_tier, "low"),
            force_overridden=False,
        )

    return {"success": True, "file": entry}

@app.get("/api/vault/files")
async def vault_list(
    tier: str = None,
    search: str = None,
    view: str = "admin",
):
    """List files in the vault."""
    files = file_vault.list_files(tier=tier, search=search, view=view)
    return {"files": files, "count": len(files)}

@app.get("/api/vault/stats")
async def vault_stats():
    """Get vault statistics."""
    return file_vault.get_vault_stats()

@app.get("/api/vault/tiers")
async def vault_tiers():
    """Get tier definitions."""
    return file_vault.TIERS

@app.put("/api/vault/files/{file_id}")
async def vault_update(file_id: str, data: dict):
    """Update file metadata (tier, tags, description, starred)."""
    result = file_vault.update_file(
        file_id,
        tier=data.get("tier"),
        tags=data.get("tags"),
        description=data.get("description"),
        starred=data.get("starred"),
    )
    if not result:
        raise HTTPException(status_code=404, detail="File not found")
    return {"success": True, "file": result}

@app.delete("/api/vault/files/{file_id}")
async def vault_delete(file_id: str):
    """Delete a file from the vault."""
    if not file_vault.delete_file(file_id):
        raise HTTPException(status_code=404, detail="File not found")
    return {"success": True}

@app.get("/api/vault/download/{file_id}")
async def vault_download(file_id: str):
    """Download a file from the vault."""
    entry = file_vault.get_file(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="File not found")
    content = file_vault.get_file_bytes(file_id)
    if content is None:
        raise HTTPException(status_code=404, detail="File data not found")
    # Update download count
    entry["download_count"] = entry.get("download_count", 0) + 1
    file_vault._persist()
    return StreamingResponse(
        io.BytesIO(content),
        media_type=entry.get("mime_guess", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{entry["filename"]}"'},
    )

@app.get("/api/bus-data")
async def get_bus_data(table: str = "bus_routes", view: str = "internal"):
    """Get bus data with policy filtering.

    view modes:
      admin    → raw data, everything visible
      internal → SPII masked, PII + SECRET visible
      external → SPII + PII masked, SECRET redacted
    """
    table_data_map = {
        "bus_routes":         bus_db.BUS_ROUTES,
        "bus_vehicles":       bus_db.BUS_VEHICLES,
        "drivers":            bus_db.DRIVERS,
        "iot_sensor_readings": bus_db.IOT_SENSOR_READINGS,
        "bus_stops":          bus_db.BUS_STOPS,
        "maintenance_logs":   bus_db.MAINTENANCE_LOGS,
        "driver_shifts":      bus_db.DRIVER_SHIFTS,
        "incidents":          bus_db.INCIDENTS,
    }
    raw = table_data_map.get(table, [])
    if not raw:
        raise HTTPException(status_code=404, detail=f"Unknown table: {table}")

    if view == "admin":
        return {"table": table, "view": "admin", "data": raw, "count": len(raw)}
    elif view == "external":
        filtered = data_policy.filter_records(table, raw, mode="external")
        return {"table": table, "view": "external", "data": filtered, "count": len(filtered)}
    else:
        # internal — mask SPII only
        filtered = data_policy.filter_records(table, raw, mode="internal")
        return {"table": table, "view": "internal", "data": filtered, "count": len(filtered)}

@app.get("/api/data-policy")
async def get_data_policy(table: str = None):
    """Get policy metadata for tables."""
    if table:
        return {"table": table, "policy": data_policy.get_table_policy_summary(table),
                "fields": data_policy.POLICY_TABLE.get(table, {})}
    return {"policies": data_policy.get_full_policy_summary(),
            "all_fields": data_policy.POLICY_TABLE}

@app.post("/api/classify-query")
async def classify_query(request_data: dict):
    """Classify a natural-language query."""
    query = request_data.get("query", "")
    return data_policy.classify_query(query)

@app.get("/api/metrics")
async def get_metrics():
    """Get current metrics data"""
    try:
        return _payload()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")

@app.get("/api/workflow-stats")
async def get_workflow_stats():
    """Get workflow statistics"""
    try:
        if not workflow:
            raise HTTPException(status_code=503, detail="Workflow not initialized")

        workflow_stats = workflow.get_stats()
        return {
            "timestamp": datetime.now().isoformat(),
            "workflow_stats": workflow_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting workflow stats: {str(e)}")

@app.get("/api/request-history")
async def get_request_history(limit: int = 20):
    """Get recent request history"""
    try:
        if not workflow:
            raise HTTPException(status_code=503, detail="Workflow not initialized")

        return {
            "timestamp": datetime.now().isoformat(),
            "history": _serialize_history(limit),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting request history: {str(e)}")

@app.post("/api/simulate-request")
async def simulate_request(request_data: dict):
    """Simulate a workflow request for testing"""
    try:
        if not workflow:
            raise HTTPException(status_code=503, detail="Workflow not initialized")

        user_input = request_data.get("user_input", "Test input")
        llm_output = request_data.get("llm_output", None)
        force_route = request_data.get("force_route", "auto")

        log_buffer = io.StringIO()

        def _run():
            with redirect_stdout(log_buffer):
                return workflow.process(user_input, llm_output, force_route=force_route)

        result = await asyncio.to_thread(_run)
        result["user_input"] = user_input

        return {
            "success": True,
            "result": result,
            "dashboard": _payload(),
            "logs": log_buffer.getvalue().splitlines()[-20:],
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

@app.post("/api/mcp/track")
async def mcp_track(request_data: dict):
    """
    Lightweight endpoint called by the MCP server's background thread.
    Accepts a pre-computed tool result and records it in dashboard history.
    No heavy processing — just records and returns immediately.
    """
    if not workflow:
        return {"success": False}

    import time as _time
    tool   = request_data.get("tool", "")
    args   = request_data.get("args", {})
    result = request_data.get("result", {})

    try:
        if tool == "consat_workflow_process":
            routing  = result.get("routing", {})
            metrics  = result.get("metrics", {})
            entry = {
                **result,
                "user_input": result.get("user_input", args.get("user_input", "")),
            }
            workflow.request_history.append(entry)
            workflow.monitoring.record_request(
                routing_decision  = routing.get("llm_used", "cloud"),
                processing_time   = float(metrics.get("processing_time_ms", 0)),
                masked_items      = int(metrics.get("masked_items_count", 0)),
                policy_violations = result.get("policy_check", {}).get("critical_violations", 0),
                sensitivity_level = routing.get("sensitivity_level", "low"),
                force_overridden  = result.get("force_overridden", False),
            )

        elif tool in ("consat_route", "consat_bus_query", "consat_driver_lookup"):
            # Determine query text and run a fast (no-LLM) sensitivity check
            if tool == "consat_route":
                query_text = args.get("text", "")
                sensitivity = result.get("sensitivity_level", "low")
                llm_used    = result.get("routing_decision", "cloud")
                patterns    = result.get("detected_patterns", [])
                reason      = result.get("reason", "")
            else:
                query_text = (f"Driver lookup {args.get('driver_id','')}"
                              if tool == "consat_driver_lookup" else args.get("query", ""))
                route_info  = workflow.router.route(query_text)
                sensitivity = route_info["sensitivity_level"]
                llm_used    = route_info["routing_decision"]
                patterns    = route_info.get("detected_patterns", [])
                reason      = route_info.get("reason", "")

            status = "blocked" if llm_used == "local" else "approved"
            entry = {
                "request_id":     f"mcp_{tool[:4]}_{int(_time.time()*1000)}",
                "user_input":     f"[Cline] {query_text[:80]}",
                "status":         status,
                "force_overridden": False,
                "force_route":    "auto",
                "timestamp":      _time.time(),
                "routing": {
                    "decision":          llm_used,
                    "reason":            reason,
                    "llm_used":          llm_used,
                    "sensitivity_level": sensitivity,
                    "detected_patterns": patterns,
                },
                "masking":       None,
                "policy_check":  {"approved": True, "total_violations": 0,
                                  "critical_violations": 0, "violations": []},
                "metrics":       {"processing_time_ms": "0", "masked_items_count": 0},
                "final_output":  None,
            }
            workflow.request_history.append(entry)
            workflow.monitoring.record_request(
                routing_decision  = llm_used,
                processing_time   = 0,
                masked_items      = 0,
                policy_violations = 0,
                sensitivity_level = sensitivity,
                force_overridden  = False,
            )

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/mcp/call")
async def mcp_call(request_data: dict):
    """
    Bridge endpoint for the MCP server (Cline integration).
    Every Cline tool call is forwarded here so it passes through the dashboard's
    workflow instance and appears in the monitoring UI.
    """
    if not workflow:
        return {"success": False, "error": "Workflow not initialized"}

    tool = request_data.get("tool", "")
    args = request_data.get("args", {})

    try:
        if tool == "consat_workflow_process":
            user_input = args.get("user_input", "")
            llm_output = args.get("llm_output")
            force_route = args.get("force_route", "auto")
            log_buffer = io.StringIO()
            def _run_wf():
                with redirect_stdout(log_buffer):
                    return workflow.process(user_input, llm_output, force_route=force_route)
            result = await asyncio.to_thread(_run_wf)
            result["user_input"] = user_input
            return {"success": True, "result": result, "logs": log_buffer.getvalue().splitlines()[-20:]}

        elif tool == "consat_route":
            text = args.get("text", "")
            # Run through the full workflow (with a stub output) so it appears in history
            log_buffer = io.StringIO()
            def _run_rt():
                with redirect_stdout(log_buffer):
                    return workflow.process(
                        text,
                        llm_output="[Sensitivity classification — no LLM response needed]",
                        force_route="auto",
                    )
            await asyncio.to_thread(_run_rt)
            return {"success": True, "result": workflow.router.route(text)}

        elif tool == "consat_bus_query":
            query = args.get("query", "")
            # Track in dashboard via workflow
            log_buffer = io.StringIO()
            def _run_bq():
                with redirect_stdout(log_buffer):
                    return workflow.process(
                        query,
                        llm_output="[Bus data query — policy-filtered results returned to Cline]",
                        force_route="auto",
                    )
            await asyncio.to_thread(_run_bq)
            # Return the actual policy-filtered bus data
            classification = data_policy.classify_query(query)
            raw_results = bus_db.search_data(query)
            filtered = {}
            table_map = {"routes": "bus_routes", "vehicles": "bus_vehicles",
                         "drivers": "drivers", "readings": "iot_sensor_readings"}
            for key, tname in table_map.items():
                if raw_results.get(key):
                    filtered[key] = data_policy.filter_for_external(tname, raw_results[key])
            return {
                "success": True,
                "query_classification": classification,
                "filtered_results": filtered,
                "record_counts": {k: len(v) for k, v in filtered.items()},
                "policy_applied": True,
                "note": "PII fields are hashed, COMPANY_SECRET fields are redacted.",
            }

        elif tool == "consat_driver_lookup":
            driver_id = args.get("driver_id", "")
            # Track in dashboard — driver_id regex triggers HIGH → LOCAL routing
            log_buffer = io.StringIO()
            def _run_dl():
                with redirect_stdout(log_buffer):
                    return workflow.process(
                        f"Driver lookup: {driver_id}",
                        llm_output="[Driver data retrieved and filtered by data policy]",
                        force_route="auto",
                    )
            await asyncio.to_thread(_run_dl)
            matches = [d for d in bus_db.DRIVERS if d["driver_id"] == driver_id]
            if not matches:
                return {"success": True, "result": {"error": f"Driver {driver_id} not found",
                        "available_ids": [d["driver_id"] for d in bus_db.DRIVERS]}}
            filtered = data_policy.filter_record_for_external("drivers", matches[0])
            return {
                "success": True,
                "result": {
                    "driver_filtered": filtered,
                    "policy_applied": True,
                    "fields_hashed":    [f for f, p in data_policy.POLICY_TABLE["drivers"].items() if p["action"] == "hash"],
                    "fields_encrypted": [f for f, p in data_policy.POLICY_TABLE["drivers"].items() if p["action"] == "encrypt"],
                    "fields_redacted":  [f for f, p in data_policy.POLICY_TABLE["drivers"].items() if p["action"] == "redact"],
                    "note": "Full unfiltered data only available via LOCAL LLM.",
                }
            }

        else:
            return {"success": False, "error": f"Unknown tool for MCP bridge: {tool}"}

    except Exception as e:
        import traceback as _tb
        return {"success": False, "error": str(e), "traceback": _tb.format_exc(limit=3)}


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics updates"""
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            await asyncio.sleep(3)

            try:
                await websocket.send_json(_payload())
            except Exception as e:
                await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/api/audit-log")
async def get_audit_log(last_n: int = 30):
    """Return ISO27001 audit trail events and compliance summary."""
    import audit_log as _audit
    events = _audit.get_recent_events(last_n)
    for e in events:
        if "reason" in e:
            e["reason"] = _translate(e["reason"])
    return {
        "timestamp": datetime.now().isoformat(),
        "recent_events": events,
        "summary": _audit.get_audit_summary(),
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {
            "dashboard": dashboard is not None,
            "workflow": workflow is not None,
        }
    }

if __name__ == "__main__":
    # Create necessary directories
    Path("templates").mkdir(exist_ok=True)
    Path("static/css").mkdir(parents=True, exist_ok=True)
    Path("static/js").mkdir(parents=True, exist_ok=True)

    print("Starting Web Dashboard on http://localhost:8000")
    print("Dashboard: http://localhost:8000")
    print("Real-time updates via WebSocket")

    uvicorn.run(
        "web_dashboard:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
