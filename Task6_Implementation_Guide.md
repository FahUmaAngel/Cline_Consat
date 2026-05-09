# Task 6: Policy Enforcement Layer - Implementation Guide

## Overview
Policy Enforcement Layer คือระบบที่ตรวจสอบผลลัพธ์จาก LLM ว่าปฏิบัติตามนโยบายความปลอดภัยและการปฏิบัติตามข้อกำหนดขององค์กร CONSAT เพื่อป้องกันไม่ให้มีช่องโหว่ความปลอดภัยผ่านไป

---

## ส่วนประกอบหลัก 3 ชิ้น

### 1. Security Patterns Checker
**ทำหน้าที่:** ตรวจจับปัญหาความปลอดภัยในโค้ด

**ตรวจจับ:**
- `hardcoded_password` - รหัสผ่านที่เขียนตรง ❌
- `hardcoded_api_key` - API keys ที่เขียนตรง ❌
- `sql_injection_risk` - SQL injection vulnerability ❌
- `insecure_deserialization` - unsafe pickle/eval ❌

**ตัวอย่าง:**
```python
# ❌ CRITICAL
password = "MySecret123"
api_key = "sk_live_abc123"

# ✅ SAFE
password = os.environ.get('DB_PASSWORD')
api_key = get_api_key_from_config()
```

### 2. Compliance Patterns Checker
**ทำหน้าที่:** ตรวจสอบการปฏิบัติตามนโยบาย CONSAT

**ตรวจจับ:**
- `no_audit_log` - Database operations ไม่มี logging ⚠️
- `missing_error_handling` - External calls ไม่มี try-except ⚠️
- `unencrypted_transmission` - ใช้ HTTP แทน HTTPS ⚠️

**ตัวอย่าง:**
```python
# ❌ WARNING
response = requests.get("http://api.example.com")  # Not HTTPS!
cursor.execute(query)  # No error handling

# ✅ GOOD
try:
    response = requests.get("https://api.example.com", timeout=10)
except requests.RequestException as e:
    logger.error(f"API error: {e}")
    raise
```

### 3. Library Whitelist/Blacklist
**ทำหน้าที่:** ตรวจสอบว่า imports ใช้ approved libraries เท่านั้น

**Whitelist (Allowed):**
- `requests`, `flask`, `django`, `fastapi`
- `sqlalchemy`, `psycopg2`, `pymongo`
- `pydantic`, `jwt`, `cryptography`

**Blacklist (Forbidden):**
- `pickle` - unsafe deserialization
- `eval` - arbitrary code execution
- `exec` - arbitrary code execution

---

## วิธีการใช้งาน

### Step 1: เตรียมสภาพแวดล้อม
```bash
cd d:\Hackathon\Cline_Consat
python policy_enforcement_prototype.py
```

### Step 2: ดูผลลัพธ์ทดสอบ
```
Test 1: Safe Code (PASS)
  ✓ 0 violations found
  ✓ All imports are approved

Test 2: Hardcoded Password (FAIL)
  ✗ 1 critical violation
  ✗ Recommendation: Use os.environ.get()

Test 3: Unsafe Deserialization (FAIL)
  ✗ 2 critical violations
  ✗ Recommendation: Use json.loads()
```

### Step 3: ใช้งาน API ใน Code
```python
from policy_enforcement_prototype import PolicyEnforcementPipeline

# สร้าง pipeline instance
pipeline = PolicyEnforcementPipeline()

# ตรวจสอบโค้ด
code = """
def connect_db():
    conn = mysql.connector.connect(
        host="db.internal",
        user="admin",
        password="MySecret123"
    )
    return conn
"""

result = pipeline.validate_ai_output(code)

if result['code_approved']:
    print("✅ Code is approved")
else:
    print(f"❌ Code rejected: {result['critical_violations']} critical issues")
    for violation in result['violations']:
        print(f"  - [{violation['severity']}] {violation['message']}")
```

---

## ขั้นตอนการ Implement สำหรับ Production

### 1. ปรับแต่ง Security Patterns
```python
# Extend PolicyChecker to add CONSAT-specific patterns
class Consat PolicyChecker(PolicyChecker):
    def __init__(self):
        super().__init__()
        
        # Add CONSAT-specific security patterns
        self.security_patterns['consat_internal_api'] = {
            'regex': r'https://api\.consat\.internal',
            'severity': 'critical',
            'message': 'Should not hardcode internal API endpoints',
            'recommendation': 'Use config management',
        }
        
        self.security_patterns['customer_data_unencrypted'] = {
            'regex': r'customer_data.*plaintext',
            'severity': 'critical',
            'message': 'Customer data must be encrypted',
            'recommendation': 'Use encryption library',
        }
```

### 2. Update Library Whitelist
```python
# Customize allowed libraries for CONSAT
policy_checker.library_whitelist['allowed'].extend([
    'consat_sdk',  # Internal library
    'boto3',       # AWS integration
    'confluent_kafka',  # Kafka
])

policy_checker.library_whitelist['forbidden'].extend([
    'requests_unverified',  # Unsafe HTTP
])
```

### 3. Integrate กับ Workflow
```python
from secure_agentic_workflow import SecureAgenticWorkflow

workflow = SecureAgenticWorkflow()

# Process input and get output from LLM
result = workflow.process(user_input, llm_output)

if not result['policy_check']['approved']:
    print(f"Code rejected! Violations:")
    for v in result['policy_check']['violations']:
        print(f"  {v['violation_type']}: {v['message']}")
else:
    print("✅ Code passed all policy checks!")
    print(result['final_output'])
```

### 4. Custom Policy Rules
```python
# Define custom compliance rules
compliance_rules = {
    'require_docstring': {
        'regex': r'def\s+\w+\(',
        'must_have': r'""".*"""',
        'severity': 'warning',
        'message': 'Function missing docstring',
    },
    'require_type_hints': {
        'regex': r'def\s+\w+\s*\(\s*\w+\s*:',  # Has type hints
        'severity': 'warning',
        'message': 'Function parameters should have type hints',
    },
}
```

### 5. Auto-Fix Suggestions
```python
# Provide automatic fixes for common issues
auto_fixes = {
    'hardcoded_password': {
        'find': r'password\s*=\s*["\']([^"\']+)["\']',
        'replace': 'password = os.environ.get("DB_PASSWORD")',
    },
    'unencrypted_http': {
        'find': r'http://',
        'replace': 'https://',
    },
}

# Apply auto-fixes where possible
def apply_auto_fixes(code, violations):
    fixed_code = code
    for violation in violations:
        if violation['violation_type'] in auto_fixes:
            fix = auto_fixes[violation['violation_type']]
            fixed_code = re.sub(fix['find'], fix['replace'], fixed_code)
    return fixed_code
```

---

## Violation Severity Levels

| Severity | Meaning | Action |
|----------|---------|--------|
| **CRITICAL** | Cannot approve, must fix | ❌ REJECT |
| **WARNING** | Should fix, but may approve with caution | ⚠️ WARN |
| **INFO** | Nice to have | ℹ️ INFO |

---

## Advanced Features

### 1. Context-Aware Checking
```python
# Different rules for different file types
if filename.endswith('.py'):
    check_python_patterns()
elif filename.endswith('.js'):
    check_javascript_patterns()
elif filename.endswith('.sql'):
    check_sql_patterns()
```

### 2. Whitelist/Blacklist Management
```python
# Store in database or config file
whitelist_config = {
    'approved_libs': ['requests', 'django'],
    'approved_endpoints': ['https://api.consat.internal'],
    'approved_databases': ['postgresql', 'mongodb'],
}

# Load and apply
policy_checker.update_whitelist(whitelist_config)
```

### 3. Policy Violation Dashboard
```python
# Track violations over time
violations_by_type = {}
violations_by_severity = {}

for violation in all_violations:
    v_type = violation['violation_type']
    severity = violation['severity']
    
    violations_by_type[v_type] = violations_by_type.get(v_type, 0) + 1
    violations_by_severity[severity] = violations_by_severity.get(severity, 0) + 1

# Display trends
print(f"Most common violations: {violations_by_type}")
print(f"Severity distribution: {violations_by_severity}")
```

---

## Checklist สำหรับ Task 6 Complete

- [ ] ดาวน์โหลด/คัดลอก `policy_enforcement_prototype.py`
- [ ] รัน prototype และตรวจสอบผลลัพธ์
- [ ] ทำความเข้าใจ 3 ส่วน: Security, Compliance, Libraries
- [ ] ปรับแต่ง policies ให้เหมาะสมกับ CONSAT standards
- [ ] เทส validate จากตัวอย่างโค้ดจริง
- [ ] สร้าง custom rules สำหรับ CONSAT
- [ ] เตรียมพร้อม integrate กับ secure_agentic_workflow.py

---

## Troubleshooting

### ❌ False Positives (ปฏิเสธโค้ดที่ดี)
**สาเหตุ:** Regex match ผิด
**วิธีแก้:**
- Refine regex pattern ให้ specific มากขึ้น
- Add whitelist exceptions
- Manual code review

### ❌ False Negatives (ยอมรับโค้ดที่ไม่ดี)
**สาเหตุ:** Regex ไม่ครอบคลุม
**วิธีแก้:**
- เพิ่ม pattern ใหม่
- Use AST parsing แทน regex (สำหรับ production)
- Regular pattern audit

### ❌ Performance ช้า
**สาเหตุ:** Regex ซับซ้อนหรือ input ใหญ่
**วิธีแก้:**
- Pre-compile regex patterns
- Split code analysis เป็น chunks
- Cache results

---

## หมายเหตุ

- Prototype ใช้ Regex ธรรมดา (เหมาะสำหรับ MVP)
- Production ควรใช้ AST (Abstract Syntax Tree) parsing สำหรับความแม่นยำสูง
- Library whitelist/blacklist เป็น static config (ต้องอัปเดตตามความเหมาะสม)
- Violation records เก็บไว้สำหรับ audit trail
