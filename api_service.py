"""
FastAPI REST service for the CONSAT Secure Agentic Workflow.

Run:
    python api_service.py
"""

from contextlib import asynccontextmanager, redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import io

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import uvicorn

from data_masking_prototype import DataMaskingPipeline
from policy_enforcement_prototype import PolicyEnforcementPipeline
from secure_agentic_workflow import SecureAgenticWorkflow
from sensitivity_router_prototype import SensitivityRouter


router = None
masking = None
policy = None
workflow = None


class RouteRequest(BaseModel):
    text: str = Field(..., min_length=1)


class MaskRequest(BaseModel):
    text: str = Field(..., min_length=1)


class DemaskRequest(BaseModel):
    text: str = Field(..., min_length=1)


class PolicyCheckRequest(BaseModel):
    code: str = Field(..., min_length=1)


class WorkflowRequest(BaseModel):
    user_input: str = Field(..., min_length=1)
    llm_output: Optional[str] = None


def _now() -> str:
    return datetime.now().isoformat()


def _history(limit: int = 50) -> List[Dict[str, Any]]:
    if not workflow:
        return []
    return workflow.request_history[-limit:]


def _workflow_payload() -> Dict[str, Any]:
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized")
    return {
        "timestamp": _now(),
        "workflow_stats": workflow.get_stats(),
        "monitoring": workflow.monitoring.calculator.calculate_stats(),
        "health": workflow.monitoring.get_health_status(),
        "alerts": workflow.monitoring.metrics_collector.get_all_alerts()[-20:],
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global router, masking, policy, workflow

    router = SensitivityRouter()
    masking = DataMaskingPipeline()
    policy = PolicyEnforcementPipeline()
    workflow = SecureAgenticWorkflow()

    yield


app = FastAPI(
    title="CONSAT Secure Agentic Workflow API",
    version="1.0.0",
    description="REST API for routing, masking, policy checks, workflow execution, and monitoring.",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "service": "CONSAT Secure Agentic Workflow API",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": _now(),
        "components": {
            "router": router is not None,
            "masking": masking is not None,
            "policy": policy is not None,
            "workflow": workflow is not None,
        },
    }


@app.post("/v1/route")
async def route_text(request: RouteRequest):
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")
    return {
        "timestamp": _now(),
        "result": router.route(request.text),
    }


@app.post("/v1/mask")
async def mask_text(request: MaskRequest):
    if not masking:
        raise HTTPException(status_code=503, detail="Masking pipeline not initialized")
    masked_text, metadata = masking.process_for_cloud(request.text)
    return {
        "timestamp": _now(),
        "masked_text": masked_text,
        "metadata": metadata,
        "summary": masking.get_summary(),
    }


@app.post("/v1/demask")
async def demask_text(request: DemaskRequest):
    if not masking:
        raise HTTPException(status_code=503, detail="Masking pipeline not initialized")
    return {
        "timestamp": _now(),
        "text": masking.restore_output(request.text),
    }


@app.post("/v1/policy/check")
async def check_policy(request: PolicyCheckRequest):
    if not policy:
        raise HTTPException(status_code=503, detail="Policy pipeline not initialized")
    return {
        "timestamp": _now(),
        "result": policy.validate_ai_output(request.code),
        "summary": policy.get_summary(),
    }


@app.post("/v1/workflow/process")
async def process_workflow(request: WorkflowRequest):
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized")

    log_buffer = io.StringIO()
    with redirect_stdout(log_buffer):
        result = workflow.process(request.user_input, request.llm_output)
    result["user_input"] = request.user_input

    return {
        "timestamp": _now(),
        "success": True,
        "result": result,
        "logs": log_buffer.getvalue().splitlines()[-40:],
        "state": _workflow_payload(),
    }


@app.get("/v1/workflow/stats")
async def workflow_stats():
    return _workflow_payload()


@app.get("/v1/workflow/history")
async def workflow_history(limit: int = Query(default=50, ge=1, le=500)):
    return {
        "timestamp": _now(),
        "history": _history(limit),
    }


@app.get("/v1/monitoring/metrics")
async def monitoring_metrics():
    return _workflow_payload()


@app.post("/v1/export/logs")
async def export_logs(filepath: str = "workflow_logs_api.json"):
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized")

    output_path = Path(filepath)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path

    with redirect_stdout(io.StringIO()):
        workflow.export_logs(str(output_path))
    return {
        "timestamp": _now(),
        "path": str(output_path),
    }


if __name__ == "__main__":
    print("Starting CONSAT API service on http://127.0.0.1:8100")
    uvicorn.run(
        "api_service:app",
        host="127.0.0.1",
        port=8100,
        reload=False,
        log_level="info",
    )
