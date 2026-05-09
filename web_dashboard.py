"""
Web Dashboard for Secure Agentic Workflow
==========================================
Real-time monitoring UI using FastAPI + HTML/JS

Author: CONSAT PoC Team
Date: May 4, 2026
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
import asyncio
import io
import uvicorn

# Import our existing components
from monitoring_dashboard_prototype import MonitoringDashboard
from secure_agentic_workflow import SecureAgenticWorkflow
import stockholm_bus_data as bus_db
import data_policy

# Global components
dashboard = None
workflow = None
active_connections = []

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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
        row["routing_reason"] = item.get("routing", {}).get("reason", "")
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
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard.html", response_class=HTMLResponse)
async def get_dashboard_html(request: Request):
    """Serve dashboard page when opened by its file-like URL."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/data-explorer", response_class=HTMLResponse)
async def get_data_explorer(request: Request):
    """Serve data explorer page."""
    return templates.TemplateResponse("data-explorer.html", {"request": request})

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
