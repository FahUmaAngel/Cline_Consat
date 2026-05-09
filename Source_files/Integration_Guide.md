# Integration Guide - All Tasks Combined

## Overview
คู่มือการเชื่อมต่อระบบ Task 4, 5, 6, 7 ให้ทำงานเป็น workflow เดียว

---

## Architecture Flow

```
User Input (Cline)
    ↓
┌─────────────────────────────────────────────────────────┐
│ Task 4: Sensitivity Router                              │
│ - ตรวจจับความสำคัญของข้อมูล                            │
│ - ตัดสินใจ: Local LLM vs Cloud LLM                     │
└─────────────────────────────────────────────────────────┘
    ↓
    ├─── HIGH SENSITIVITY ──→ ✅ Send to Local LLM
    │
    └─── LOW/MEDIUM SENSITIVITY ──→ Continue
                                     ↓
                        ┌─────────────────────────────────┐
                        │ Task 5: Data Masking Engine      │
                        │ - Mask PII, secrets, etc.       │
                        │ - Create mapping table          │
                        └─────────────────────────────────┘
                                     ↓
                        ✅ Send to Cloud LLM (Masked)
                                     ↓
                        Receive output from Cloud
                                     ↓
                        ┌─────────────────────────────────┐
                        │ De-masking                       │
                        │ - Restore original values       │
                        └─────────────────────────────────┘
    ↓ (From both paths)
┌─────────────────────────────────────────────────────────┐
│ Task 6: Policy Enforcement Layer                        │
│ - Check security violations                             │
│ - Check compliance rules                                │
│ - Validate output from LLM                              │
└─────────────────────────────────────────────────────────┘
    ↓
    ├─── CRITICAL VIOLATIONS ──→ ❌ REJECT
    │
    └─── PASS ──→ Approved
         ↓
┌─────────────────────────────────────────────────────────┐
│ Task 7: Monitoring Dashboard                            │
│ - Record metrics (routing, masking, violations)         │
│ - Check alerts                                          │
│ - Update dashboard                                      │
└─────────────────────────────────────────────────────────┘
    ↓
Return to User (Cline)
```

---

## Step-by-Step Implementation

### Step 1: Create Main Orchestrator

สร้างไฟล์ `secure_agentic_workflow.py`:

```python
from sensitivity_router_prototype import SensitivityRouter
from data_masking_prototype import DataMaskingPipeline
from policy_enforcement_prototype import PolicyEnforcementPipeline
from monitoring_dashboard_prototype import MonitoringDashboard
import time

class SecureAgenticWorkflow:
    """บริหารจัดการ workflow ทั้งหมด"""
    
    def __init__(self):
        self.router = SensitivityRouter()
        self.masking = DataMaskingPipeline()
        self.policy = PolicyEnforcementPipeline()
        self.monitoring = MonitoringDashboard()
    
    def process(self, user_input: str, llm_output: str = None) -> dict:
        """
        Process user input through the entire secure workflow
        
        Args:
            user_input: Original input from user/Cline
            llm_output: Optional - output from LLM to validate
        
        Returns:
            Final result with all checks
        """
        start_time = time.time()
        
        # ========== Step 1: Sensitivity Router ==========
        routing_result = self.router.route(user_input)
        use_local = routing_result['use_local_llm']
        
        # ========== Step 2: Determine Path ==========
        if use_local:
            # Local LLM path - no masking needed
            masked_input = user_input
            masking_info = None
            llm_to_use = "local"
        else:
            # Cloud LLM path - mask first
            masked_input, masking_info = self.masking.process_for_cloud(user_input)
            llm_to_use = "cloud"
        
        # ========== Step 3: Simulate LLM Output (if provided) ==========
        final_output = llm_output if llm_output else "Generated code/response"
        
        # ========== Step 4: De-mask if Cloud ==========
        if not use_local and llm_output:
            final_output = self.masking.restore_output(final_output)
        
        # ========== Step 5: Policy Enforcement ==========
        policy_result = self.policy.validate_ai_output(final_output)
        approved = policy_result['code_approved']
        
        # ========== Step 6: Monitoring ==========
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        masked_count = len(routing_result['detected_patterns']) if masking_info else 0
        violation_count = policy_result['critical_violations']
        
        self.monitoring.record_request(
            routing_decision="local" if use_local else "cloud",
            processing_time=processing_time,
            masked_items=masked_count,
            policy_violations=violation_count,
        )
        
        # ========== Final Result ==========
        return {
            'status': 'approved' if approved else 'rejected',
            'routing': {
                'decision': routing_result['routing_decision'],
                'reason': routing_result['reason'],
                'llm_used': llm_to_use,
            },
            'masking': masking_info,
            'policy_check': {
                'approved': approved,
                'violations': policy_result['violations'],
            },
            'processing_time_ms': f"{processing_time:.2f}",
            'final_output': final_output if approved else None,
        }
    
    def show_dashboard(self):
        """Display monitoring dashboard"""
        self.monitoring.display_dashboard()
    
    def export_audit_logs(self, filepath: str):
        """Export all audit logs and metrics"""
        self.router.audit.save_to_file(f"{filepath}/routing_audit.jsonl")
        self.monitoring.export_metrics_json(f"{filepath}/monitoring_metrics.json")
```

### Step 2: Test the Integration

```python
if __name__ == "__main__":
    workflow = SecureAgenticWorkflow()
    
    # Test Case 1: Safe query -> Cloud LLM
    result1 = workflow.process(
        user_input="สร้างฟังก์ชัน Python สำหรับ sorting",
        llm_output="def sort_list(items):\n    return sorted(items)"
    )
    print("Test 1 Result:", result1)
    
    # Test Case 2: Sensitive query -> Local LLM (no masking)
    result2 = workflow.process(
        user_input="สร้าง API สำหรับเชื่อมต่อ postgresql://admin:MySecret@db.internal:5432",
        llm_output="from config import get_db_conn\nconn = get_db_conn()"
    )
    print("Test 2 Result:", result2)
    
    # Show dashboard
    workflow.show_dashboard()
```

---

## File Structure

```
d:\Hackathon\Cline_Consat\
├── sensitivity_router_prototype.py        # Task 4
├── data_masking_prototype.py              # Task 5
├── policy_enforcement_prototype.py        # Task 6
├── monitoring_dashboard_prototype.py      # Task 7
├── secure_agentic_workflow.py             # Orchestrator (new)
├── integration_test.py                    # Integration test (new)
│
├── docs/
│   ├── Task4_Implementation_Guide.md
│   ├── Integration_Guide.md               # This file
│   └── Architecture.md
│
└── logs/
    ├── routing_audit.jsonl
    ├── monitoring_metrics.json
    └── policy_violations.json
```

---

## Integration Checklist

### ✅ Core Components
- [x] Task 4: Sensitivity Router - ตรวจจับความสำคัญ
- [x] Task 5: Data Masking Engine - ปิดบังข้อมูล
- [x] Task 6: Policy Enforcement - ตรวจสอบความปลอดภัย
- [x] Task 7: Monitoring Dashboard - ติดตามระบบ

### 🔧 Integration Steps
- [ ] สร้าง orchestrator (`secure_agentic_workflow.py`)
- [ ] เขียน integration tests
- [ ] ทดสอบแต่ละ component
- [ ] ทดสอบ end-to-end flow
- [ ] ปรับแต่ง patterns ให้เหมาะสม CONSAT
- [ ] เพิ่มเติม error handling

### 🚀 Production Ready
- [ ] Add logging/tracing
- [ ] Add metrics export (Prometheus/etc)
- [ ] Add API endpoints (FastAPI/Flask)
- [ ] Add MCP server integration
- [ ] Performance optimization
- [ ] Unit tests + integration tests

---

## Example Usage in Production

### Scenario: User sends code to Cline with sensitive data

```
Input: "สร้าง API client สำหรับเชื่อมต่อ postgresql://admin:password@db.internal"

↓ Step 1: Router decides
  → HIGH SENSITIVITY (detect: password, internal_domain, database_url)
  → Route to LOCAL LLM

↓ Step 2: Local LLM processes (no masking needed)
  → Generate safe code

↓ Step 3: Policy Enforcement checks
  → ✅ Code is safe (no hardcoded secrets)

↓ Step 4: Monitoring records
  → Local routing count: +1
  → Policy violations: 0

Output: Safe code returned to user
```

### Scenario: User sends benign request

```
Input: "สร้างฟังก์ชัน Python สำหรับ sort list"

↓ Step 1: Router decides
  → LOW SENSITIVITY
  → Route to CLOUD LLM (faster)

↓ Step 2: Masking (no sensitive data found)
  → Send original input to Cloud

↓ Step 3: Cloud LLM processes
  → Generate code

↓ Step 4: De-masking
  → No change (no data was masked)

↓ Step 5: Policy Enforcement checks
  → ✅ Code is safe

↓ Step 6: Monitoring records
  → Cloud routing count: +1
  → Processing time: 500ms
  → Masking items: 0

Output: Safe code returned to user
```

---

## Performance Expectations

| Task | Typical Time | Notes |
|------|--------------|-------|
| Router (Task 4) | ~50ms | Regex matching |
| Masking (Task 5) | ~100ms | Pattern replacement |
| Policy (Task 6) | ~200ms | Code analysis |
| Monitoring (Task 7) | ~20ms | Metrics recording |
| **Total** | **~370ms** | Can vary with input size |

---

## Next Steps

1. ✅ Implement orchestrator
2. ✅ Create integration tests
3. ✅ Add FastAPI endpoints
4. ✅ Create MCP server
5. ✅ Add Cline integration
6. ✅ Deploy to production
7. ✅ Monitor and optimize
