# CONSAT Secure Agentic Workflow Architecture

## Purpose

This document defines the final PoC system design for the CONSAT Secure Agentic Workflow. The system protects sensitive CONSAT data before AI-assisted code or workflow generation reaches an external LLM, then validates the generated output before it is returned to the user or exposed through Cline/MCP.

The PoC focuses on five controls:

- Sensitivity-aware routing between Local LLM and Cloud LLM paths
- Data masking and de-masking for cloud-bound prompts
- Policy enforcement for generated code and workflow output
- Audit and monitoring visibility for every workflow decision
- MCP/API/dashboard entry points for demonstration and integration

## High-Level Architecture

```text
User or Cline
    |
    v
API / MCP / Dashboard Simulation
    |
    v
SecureAgenticWorkflow
    |
    v
Sensitivity Router
    |
    +-- High sensitivity ----------------------+
    |                                          |
    v                                          |
Local LLM Path                                 |
    |                                          |
    v                                          |
Policy Enforcement <--------------------------+
    |
    +-- Pass -> Record metrics/audit -> Return approved output
    |
    +-- Fail -> Record metrics/audit -> Return rejection with violations

Cloud path:

Sensitivity Router
    |
    +-- Low or medium sensitivity
        |
        v
Data Masking
        |
        v
Cloud LLM Path using masked input
        |
        v
De-masking
        |
        v
Policy Enforcement
        |
        v
Record metrics/audit -> Return approved or rejected output
```

Current implementation note: the PoC currently simulates the LLM generation step by accepting an optional `llm_output`. Real Local LLM and Cloud LLM clients are planned for Task 2/8 hardening.

## Component Responsibilities

| Component | File | Responsibility | Current PoC status |
|---|---|---|---|
| Sensitivity Router | `sensitivity_router_prototype.py` | Classifies prompts/code, detects PII/secrets/internal resources, chooses local or cloud route, explains the decision. | Implemented |
| CONSAT Rules | `consat_rules.py` | Centralizes CONSAT-specific PII, secret, internal-resource, masking, and policy patterns. | Implemented |
| Data Masking Pipeline | `data_masking_prototype.py` | Replaces sensitive values with placeholders before cloud use, stores mapping, restores placeholders after cloud output. | Implemented as in-memory prototype |
| Policy Enforcement Pipeline | `policy_enforcement_prototype.py` | Checks generated code/output for hardcoded secrets, unsafe APIs, insecure config, forbidden libraries, and compliance warnings. | Implemented as rule-based prototype |
| Workflow Orchestrator | `secure_agentic_workflow.py` | Runs route, mask, LLM path selection, de-mask, policy check, metrics, and history recording in one flow. | Implemented |
| Monitoring | `monitoring_dashboard_prototype.py` | Records metrics, computes totals, raises alerts, reports health. | Implemented |
| Web Dashboard | `web_dashboard.py`, `templates/dashboard.html`, `static/` | Shows metrics, routing split, alerts, request history, and simulation controls. | Implemented prototype |
| REST API | `api_service.py` | Exposes route, mask, de-mask, policy check, workflow process, metrics, and history endpoints. | Implemented prototype |
| MCP Server | `mcp_server.py` | Exposes CONSAT tools to Cline-compatible MCP clients. | Stub implemented, pending real Cline verification |
| Audit Trail | Planned `audit.py` | Persist append-only workflow events for every request. | Missing as final component |

## Local Path Definition

The Local LLM path is used when the router detects content that must not leave the controlled environment.

Local path properties:

- Raw prompt stays inside the local runtime.
- No data masking is required before inference because the content does not leave the controlled environment.
- Policy enforcement still runs after generation.
- Monitoring records route, latency, masked item count, policy violations, and health.
- Final output is returned only if policy enforcement approves it.

Typical local triggers:

- Secrets such as API keys, bearer tokens, JWTs, passwords, GitHub tokens, or cloud credentials
- Internal infrastructure such as VPN hosts, internal service URLs, internal domains, private IPs, Kubernetes namespaces, or database URLs
- High-risk operational content such as deployment keys, runbook secrets, production incidents, or outage reports

Planned implementation:

- Ollama hosted on localhost or a controlled internal endpoint
- Model such as Llama 3 or Mistral, selected by environment/config
- Timeout, retry, and health checks before routing production traffic to this path

## Cloud Path Definition

The Cloud LLM path is used for prompts that are public, low sensitivity, or medium sensitivity after masking.

Cloud path properties:

- Prompt is inspected before any external call.
- Sensitive values are masked into placeholders before leaving the local runtime.
- Mapping stays local and is used only for de-masking the returned output.
- De-masked output still passes through policy enforcement.
- Critical policy violations reject the output even if routing and masking succeeded.

Typical cloud triggers:

- Public code generation requests with no detected sensitive data
- General programming help
- Medium sensitivity content where policy allows masking before cloud use
- PII-only content if project policy chooses "mask and cloud" instead of local-only handling

Planned implementation:

- Cloud LLM client such as Anthropic Claude or another approved API
- Network allow-list and proxy policy defined in environment setup
- Strict timeout, retry, and failure fallback behavior

## Routing Decision Matrix

| Input condition | Sensitivity | Route | Mask before LLM? | Reason |
|---|---:|---|---|---|
| API key, password, bearer token, JWT, GitHub token, Azure connection string | High | Local LLM | No | Secrets must not be sent to external LLMs. |
| Internal database URL, private IP, `.internal`, `.corp`, `.consat`, VPN or jump host | High | Local LLM | No | Internal infrastructure details are restricted. |
| Production incident, runbook secret, deployment key, VPN config | High | Local LLM | No | Operational security data stays local. |
| Employee ID, Thai phone, Thai citizen ID, email, customer PII | Medium | Cloud LLM by default after masking, or Local if stricter policy is enabled | Yes for cloud | PII can be transformed before external processing in PoC; stricter deployments can force local. |
| Customer contract, invoice batch, vendor payment, bank account keyword | Medium | Cloud LLM after masking or Local by policy | Yes for cloud | Business-sensitive content needs protection before cloud use. |
| Public code request, generic algorithm, documentation request | Low | Cloud LLM | No, unless patterns are detected | No protected content is detected. |
| Router error or unknown classifier failure | Unknown | Reject or Local fallback | No | Fail closed to avoid accidental external disclosure. |
| Masking failure on cloud path | Medium/High | Reject or Local fallback | No external call | Do not send unmasked sensitive content to cloud. |

## Main Request Sequence

```text
1. Client sends user_input and optional llm_output to API, MCP, or dashboard simulation.
2. SecureAgenticWorkflow creates a request_id and starts timing.
3. SensitivityRouter analyzes user_input.
4. Router returns sensitivity_level, detected_patterns, routing_decision, reason, and confidence.
5. If routing_decision is local:
   a. Use original user_input for the local LLM path.
   b. Mark llm_used as local.
6. If routing_decision is cloud:
   a. DataMaskingPipeline masks user_input.
   b. Store masking metadata and mapping_id locally.
   c. Send only masked input to the cloud LLM path.
   d. De-mask cloud output using the local mapping.
7. PolicyEnforcementPipeline validates final_output.
8. If critical violations exist, return rejected status and no final_output.
9. If policy passes, return approved status and final_output.
10. Monitoring records route, processing time, masked item count, and policy violations.
11. Workflow appends request history for dashboard/API visibility.
```

## Data Flow

| Data item | Source | Used by | Storage in current PoC | Security note |
|---|---|---|---|---|
| `user_input` | User/Cline/API | Router, masking, LLM path | In workflow request history | Should be redacted in future persistent audit logs. |
| `routing_result` | Router | Workflow, API/MCP/dashboard | In response/history | Safe to persist if input previews are redacted. |
| `masked_input` | Masking pipeline | Cloud LLM path | Temporary variable | Only this form should leave local runtime on cloud path. |
| `masking_info` | Masking pipeline | De-masking, dashboard/history | In memory | Mapping can contain sensitive placeholders and should be protected. |
| `llm_output` | Local/Cloud LLM or simulation | De-masking, policy | In response/history | Must pass policy before return. |
| `policy_result` | Policy pipeline | Workflow, dashboard/API | In response/history | Critical violations cause rejection. |
| `metrics` | Monitoring | Dashboard/API/MCP | In memory | Safe for dashboard; avoid raw sensitive values. |

## Error Paths

| Failure | Detection point | Expected behavior | User-visible result | Monitoring/audit event |
|---|---|---|---|---|
| Router cannot classify input | Sensitivity Router | Fail closed to local route or reject if local unavailable | "Routing failed" or local fallback notice | `routing_error` |
| Local LLM timeout | Local LLM client, planned | Retry within timeout budget, then reject or ask user to retry | "Local model timeout" | `llm_timeout`, route=`local` |
| Cloud LLM timeout | Cloud LLM client, planned | Retry within timeout budget; never resend unmasked content | "Cloud model timeout" | `llm_timeout`, route=`cloud` |
| Masking engine error | Data Masking Pipeline | Stop cloud path; reject or fallback to local | "Masking failed; request was not sent to cloud" | `masking_error` |
| De-masking error | Data Masking Pipeline | Reject output because placeholders cannot be safely restored | "De-masking failed" | `demasking_error` |
| Policy critical violation | Policy Enforcement | Reject output and withhold final generated content | Rejected status with violation summary | `policy_rejected` |
| Policy checker error | Policy Enforcement | Fail closed and reject output | "Policy check failed" | `policy_error` |
| Monitoring write error | Monitoring/Audit | Continue response if core controls succeeded, but surface degraded health | Approved/rejected result plus degraded monitoring | `monitoring_error` |
| Audit persistence failure | Planned Audit | Continue only for PoC; production should fail closed for regulated flows | "Audit unavailable" if strict mode | `audit_error` |

## Policy Enforcement Outcomes

| Policy result | Workflow status | Output handling |
|---|---|---|
| No critical violations | `approved` | Return final output. |
| Warnings only | `approved` in current PoC | Return final output with warnings in policy result. |
| One or more critical violations | `rejected` | Do not return final output. Return violation details. |
| Policy engine error | `rejected` planned | Fail closed until policy check succeeds. |

## Monitoring And Dashboard Design

The dashboard is intended to give the team operational visibility during demos and Cline integration tests.

Displayed signals:

- Total requests
- Approval rate
- Local versus cloud split
- Masked item count
- Critical alert count
- System health
- Average processing time
- Recent alerts
- Request history and route/status badges

Current dashboard data sources:

- `GET /api/metrics` in `web_dashboard.py`
- `GET /api/request-history` in `web_dashboard.py`
- `POST /api/simulate-request` in `web_dashboard.py`
- `WebSocket /ws/metrics` in `web_dashboard.py`

Static dashboard note:

- Opening `index.html` or `templates/dashboard.html` through a static server can show the UI.
- Realtime metrics, request simulation, and WebSocket updates require the FastAPI dashboard server.

## API And MCP Entry Points

| Interface | File | Purpose |
|---|---|---|
| REST API | `api_service.py` | Programmatic route/mask/de-mask/policy/workflow/metrics endpoints. |
| Web Dashboard | `web_dashboard.py` | Human dashboard and workflow simulation. |
| MCP Server | `mcp_server.py` | Cline-facing tool interface. |
| Static UI | `index.html`, `dashboard.html`, `templates/dashboard.html` | Browser-only dashboard display fallback. |

## Security Boundaries

Local trusted boundary:

- Router
- Masking and de-masking
- Mapping table
- Policy enforcement
- Monitoring and audit
- Local LLM endpoint

External boundary:

- Cloud LLM API
- CDN assets used by dashboard UI
- Browser clients connecting to the dashboard

Rules:

- Raw high-sensitivity data must remain inside the local trusted boundary.
- Cloud LLM calls must receive masked content only when sensitive patterns are present.
- Policy enforcement is mandatory on both local and cloud outputs.
- Audit logs must avoid storing raw secrets in future persistent storage.

## Current Gaps Against Final Design

- Real Local LLM client is not implemented yet.
- Real Cloud LLM client is not implemented yet.
- Persistent audit logging is not implemented yet.
- Error paths are documented here but not fully enforced in code.
- Dashboard model status is conceptual until LLM clients exist.
- Cline/MCP integration has a server stub but still needs live Cline verification.
- Unit and integration test coverage needs to be expanded beyond smoke tests.

## Implementation Roadmap

1. Add `audit.py` with append-only JSONL events and redacted payload previews.
2. Add `llm_clients.py` with Local Ollama and Cloud LLM clients.
3. Add environment-driven config for model names, endpoints, API keys, timeout, retry, and strict-mode behavior.
4. Update `SecureAgenticWorkflow` to call real LLM clients instead of simulated `llm_output`.
5. Add tests for router, masking, policy, workflow success/failure paths, API, and MCP.
6. Update dashboard to display current model, LLM health, audit event stream, and error alerts.
