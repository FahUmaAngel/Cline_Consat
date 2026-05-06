"""
CONSAT-specific routing, masking, and policy rules.

Keep organization-specific patterns here so the router, masking engine, REST API,
and MCP server all use the same rule set.
"""

CONSAT_PII_PATTERNS = {
    "thai_citizen_id": r"\b\d{1}[- ]?\d{4}[- ]?\d{5}[- ]?\d{2}[- ]?\d{1}\b",
    "employee_id": r"\b(?:CONSAT|CSAT|EMP)[-_]?\d{4,8}\b",
    "thai_phone": r"\b(?:\+66|0)(?:6|8|9)\d[- ]?\d{3}[- ]?\d{4}\b",
    # Stockholm bus domain PII
    "swedish_personnummer": r"\b\d{6,8}[-]?\d{4}\b",
    "swedish_phone": r"\b\+46\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b",
    "swedish_driver_license": r"\bSE-DL-\d{4}-\d{4,6}\b",
    "driver_id": r"\bDRV-\d{4,6}\b",
}

CONSAT_SECRET_PATTERNS = {
    "openai_key": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b",
    "github_token": r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b",
    "jwt": r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
    "azure_connection_string": r"DefaultEndpointsProtocol=https;AccountName=[^;\s]+;AccountKey=[^;\s]+",
    "generic_bearer_token": r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}",
    # Stockholm bus domain secrets
    "consat_iot_device_id": r"\bCONSAT-IOT-\d{4,6}\b",
    "consat_certification": r"\bCONSAT-CERT-(?:ADV|STD|ELITE)\b",
}

CONSAT_INTERNAL_PATTERNS = {
    "consat_domain": r"\b[\w.-]+\.(?:consat|consat\.local|consat\.internal)\b",
    "internal_service_url": r"https?://[\w.-]+(?:\.svc\.cluster\.local|\.internal|\.corp)(?:[/:][^\s\"']*)?",
    "kubernetes_namespace": r"\b(?:namespace|ns)\s*[:=]\s*[\"']?(?:prod|staging|dev)-consat[\w-]*[\"']?",
    "vpn_host": r"\b(?:vpn|jump|bastion)[\w.-]*\.consat(?:\.local|\.internal)?\b",
    "sharepoint_path": r"https?://[\w.-]*sharepoint\.com/sites/consat[^\s\"']*",
}

CONSAT_SENSITIVE_KEYWORDS = {
    "consat_customer_data": [
        "consat_customer",
        "customer_contract",
        "customer_pii",
        "customer_export",
        "client_roster",
    ],
    "consat_operations": [
        "production incident",
        "outage report",
        "runbook secret",
        "deployment key",
        "vpn config",
    ],
    "consat_finance": [
        "invoice batch",
        "bank account",
        "vendor payment",
        "purchase order",
    ],
    # Stockholm bus domain - company secrets (never share externally)
    "consat_eco_drive": [
        "eco_drive",
        "eco-drive",
        "ecodrive",
        "fuel_consumption",
        "fuel consumption",
        "brake_wear",
        "brake wear",
        "engine_temp",
        "engine temperature",
    ],
    "consat_iot_internal": [
        "iot_device_id",
        "firmware_version",
        "consat-iot",
        "training_certification",
        "consat-cert",
    ],
    # Stockholm bus domain - PII keywords
    "consat_driver_pii": [
        "driver_name",
        "full_name",
        "personal_number",
        "personnummer",
        "license_number",
        "driver phone",
        "driver email",
        "registration_plate",
    ],
}

CONSAT_MASKING_PATTERNS = {
    **CONSAT_PII_PATTERNS,
    **CONSAT_SECRET_PATTERNS,
    **CONSAT_INTERNAL_PATTERNS,
}

CONSAT_SECURITY_PATTERNS = {
    "hardcoded_token": {
        "regex": r"(?:token|secret|client_secret)\s*=\s*[\"'][^\"']{8,}[\"']",
        "severity": "critical",
        "message": "Hardcoded token or secret found",
        "recommendation": "Load secrets from environment variables or a secrets manager.",
    },
    "shell_injection_risk": {
        "regex": r"subprocess\.(?:run|Popen|call)\([^)]*shell\s*=\s*True",
        "severity": "critical",
        "message": "subprocess call with shell=True detected",
        "recommendation": "Pass arguments as a list and keep shell=False.",
    },
    "unsafe_yaml_load": {
        "regex": r"yaml\.load\(",
        "severity": "critical",
        "message": "Unsafe YAML load detected",
        "recommendation": "Use yaml.safe_load().",
    },
    "tls_verify_disabled": {
        "regex": r"verify\s*=\s*False",
        "severity": "warning",
        "message": "TLS certificate verification disabled",
        "recommendation": "Keep certificate verification enabled for CONSAT services.",
    },
    "debug_enabled": {
        "regex": r"debug\s*=\s*True",
        "severity": "warning",
        "message": "Debug mode enabled",
        "recommendation": "Disable debug mode outside local development.",
    },
    "cors_allow_all": {
        "regex": r"allow_origins\s*=\s*\[\s*[\"']\*[\"']\s*\]",
        "severity": "warning",
        "message": "CORS allows all origins",
        "recommendation": "Restrict origins to approved CONSAT domains.",
    },
}

CONSAT_COMPLIANCE_PATTERNS = {
    "missing_consat_audit_for_admin": {
        "regex": r"(?s)(?:delete|update|admin|privilege).{0,160}(?!audit|logger|record)",
        "severity": "warning",
        "message": "Admin or data-changing flow may lack audit logging",
        "recommendation": "Record actor, action, target, timestamp, and outcome.",
    },
}

CONSAT_FORBIDDEN_LIBRARIES = [
    "pickle",
    "marshal",
    "shelve",
]
