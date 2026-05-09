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
import uvicorn

# Import our existing components
from monitoring_dashboard_prototype import MonitoringDashboard
from secure_agentic_workflow import SecureAgenticWorkflow
import stockholm_bus_data as bus_db
import file_vault
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
        row["force_route"] = item.get("force_route", "auto")
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

@app.get("/file-vault", response_class=HTMLResponse)
async def get_file_vault(request: Request):
    """Serve file vault page."""
    return templates.TemplateResponse("file-vault.html", {"request": request})

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
    """Get bus data with optional policy filtering."""
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
    if view == "external":
        filtered = data_policy.filter_for_external(table, raw)
        return {"table": table, "view": "external", "data": filtered, "count": len(filtered)}
    return {"table": table, "view": "internal", "data": raw, "count": len(raw)}

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
