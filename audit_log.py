"""
Audit Trail — ISO27001 Compliance
===================================
Append-only structured log of every data access, routing decision,
masking action, and policy enforcement event.

Each event is one JSON line in audit_trail.jsonl — never overwritten,
never deleted. Required for ISO27001 A.12.4 (logging and monitoring).
"""

import json
import os
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_trail.jsonl")


@dataclass
class AuditEvent:
    event_id: str
    timestamp: str          # ISO 8601 UTC
    trace_id: str           # request-level correlation ID (spans all steps)
    actor: str              # who triggered: "mcp_server", "workflow", "data_policy"
    action: str             # "query", "route", "mask", "policy_check", "data_access", "manual_override"
    resource: str           # table name, tool name, or component
    classification: str     # PUBLIC / PII / COMPANY_SECRET / N/A
    decision: str           # "allowed", "masked", "hashed", "encrypted", "redacted", "blocked", "rejected"
    reason: str             # human-readable compliance justification
    details: Dict = field(default_factory=dict)


class AuditLogger:
    """
    File-based append-only audit logger.
    Thread-safe: file append is atomic for small writes on Linux/Windows.
    """

    def __init__(self, log_path: str = _LOG_PATH):
        self._path = log_path

    def log(
        self,
        action: str,
        resource: str,
        classification: str,
        decision: str,
        reason: str,
        trace_id: str = "",
        actor: str = "system",
        details: Optional[Dict] = None,
    ) -> str:
        """Write one audit event. Returns the trace_id used."""
        event = AuditEvent(
            event_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(timezone.utc).isoformat(),
            trace_id=trace_id or str(uuid.uuid4())[:8],
            actor=actor,
            action=action,
            resource=resource,
            classification=classification,
            decision=decision,
            reason=reason,
            details=details or {},
        )
        line = json.dumps(asdict(event), ensure_ascii=False)
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass  # never crash the main process for a logging failure
        return event.trace_id

    def read_recent(self, n: int = 50) -> List[Dict]:
        """Return the last n audit events from the log file."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return [json.loads(ln) for ln in lines[-n:] if ln.strip()]
        except FileNotFoundError:
            return []

    def read_all(self) -> List[Dict]:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return [json.loads(ln) for ln in f if ln.strip()]
        except FileNotFoundError:
            return []

    def get_summary(self) -> Dict:
        """ISO27001 audit summary: counts by action and decision."""
        events = self.read_all()
        by_action: Dict[str, int] = {}
        by_decision: Dict[str, int] = {}
        by_classification: Dict[str, int] = {}
        for e in events:
            by_action[e["action"]] = by_action.get(e["action"], 0) + 1
            by_decision[e["decision"]] = by_decision.get(e["decision"], 0) + 1
            by_classification[e["classification"]] = by_classification.get(e["classification"], 0) + 1
        return {
            "total_events": len(events),
            "by_action": by_action,
            "by_decision": by_decision,
            "by_classification": by_classification,
        }


# Module-level singleton used by all callers
_logger = AuditLogger()


# ── Convenience helpers ────────────────────────────────────────────────────────

def new_trace_id() -> str:
    return str(uuid.uuid4())[:12]


def log_routing(
    sensitivity: str,
    decision: str,
    reason: str,
    trace_id: str = "",
    force_override: bool = False,
) -> None:
    """Log a routing decision (LOCAL vs CLOUD). ISO27001 A.13.1."""
    _logger.log(
        action="manual_override" if force_override else "route",
        resource="llm_router",
        classification=sensitivity.upper(),
        decision=decision,
        reason=reason,
        trace_id=trace_id,
        actor="sensitivity_router",
    )


def log_masking(table_or_resource: str, masked_count: int, trace_id: str = "") -> None:
    """Log a masking/de-identification event. ISO27001 A.18.1 / GDPR Art.25."""
    _logger.log(
        action="mask",
        resource=table_or_resource,
        classification="PII",
        decision="masked",
        reason=f"GDPR Art.25 data minimisation: {masked_count} item(s) masked before cloud transmission",
        trace_id=trace_id,
        actor="data_masking",
        details={"masked_count": masked_count},
    )


def log_policy_check(approved: bool, violations: int, trace_id: str = "") -> None:
    """Log a policy enforcement result. ISO27001 A.14.2."""
    _logger.log(
        action="policy_check",
        resource="output_validator",
        classification="N/A",
        decision="approved" if approved else "rejected",
        reason=f"ISO27001 A.14.2 output validation: {violations} critical violation(s) found",
        trace_id=trace_id,
        actor="policy_engine",
        details={"critical_violations": violations},
    )


def log_query_classification(
    query: str,
    classification: str,
    recommendation: str,
    trace_id: str = "",
) -> None:
    """Log a data query classification result. GDPR Art.5 / ISO27001 A.8.2."""
    decision = "allowed" if classification == "PUBLIC" else "restricted"
    _logger.log(
        action="query",
        resource="query_classifier",
        classification=classification,
        decision=decision,
        reason=recommendation,
        trace_id=trace_id,
        actor="data_policy",
        details={"query_snippet": query[:100]},
    )


def log_data_access(
    table: str,
    field_action: str,
    classification: str,
    trace_id: str = "",
    actor: str = "data_policy",
) -> None:
    """Log a field-level data access with the applied policy action. GDPR Art.5."""
    _action_map = {
        "pass": "allowed",
        "hash": "hashed",
        "encrypt": "encrypted",
        "redact": "redacted",
    }
    decision = _action_map.get(field_action, field_action)
    reason_map = {
        "allowed": f"PUBLIC field: no restriction",
        "hashed":  f"GDPR Art.4(1): PII pseudonymised via SHA-256",
        "encrypted": f"GDPR Art.5(1)(f): PII encrypted before external sharing",
        "redacted": f"ISO27001 A.8.2: COMPANY_SECRET field redacted",
    }
    _logger.log(
        action="data_access",
        resource=table,
        classification=classification,
        decision=decision,
        reason=reason_map.get(decision, decision),
        trace_id=trace_id,
        actor=actor,
    )


def get_recent_events(n: int = 50) -> List[Dict]:
    return _logger.read_recent(n)


def get_audit_summary() -> Dict:
    return _logger.get_summary()


# ── Standalone demo ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tid = new_trace_id()
    log_query_classification("Show driver phone for line 172", "PII", "Apply hash/encrypt before sharing externally.", trace_id=tid)
    log_routing("HIGH", "local", "HIGH sensitivity — blocked from cloud", trace_id=tid)
    log_masking("iot_sensor_readings", 3, trace_id=tid)
    log_policy_check(True, 0, trace_id=tid)

    print("Recent audit events:")
    for e in get_recent_events(4):
        print(f"  [{e['timestamp']}] {e['action']} | {e['classification']} | {e['decision']} | {e['reason'][:60]}")

    print("\nAudit summary:")
    summary = get_audit_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")
