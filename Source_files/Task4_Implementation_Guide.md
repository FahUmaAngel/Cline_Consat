# Task 4: Sensitivity Router - Implementation Guide

## Overview
Sensitivity Router คือระบบวิเคราะห์ความสำคัญของข้อมูลจากผู้ใช้ (Prompt/Code) เพื่อตัดสินใจว่าจะส่งไป Local LLM (ปลอดภัย) หรือ Cloud LLM (เร็ว แต่ต้อง mask)

---

## ส่วนประกอบหลัก 4 ชิ้น

### 1. Sensitivity Detector
**ทำหน้าที่:** ตรวจจับข้อมูลสำคัญในข้อความ

**ตรวจจับรูปแบบ:**
- **PII (Personally Identifiable Information)**
  - Email: `user@example.com`
  - Phone: `+1 (555) 123-4567`
  - SSN: `123-45-6789`
  - ชื่อบุคคล: John, Alice, Michael, etc.

- **Secrets/Credentials**
  - API Keys: `api_key = "sk_live_..."`
  - Passwords: `password: "MySecret123"`
  - Tokens: `token: "jwt_token..."`
  - Private Keys: `-----BEGIN RSA PRIVATE KEY-----`
  - AWS Secrets: `AKIA...` (AWS format)

- **Internal Resources**
  - Internal IPs: `10.x.x.x`, `172.16.x.x`, `192.168.x.x`
  - Internal Domains: `.internal`, `.local`, `.consat`, `.corp`
  - Database URLs: `postgresql://...`, `mysql://...`
  - AWS Regions: `us-east-1`, `eu-west-1`, etc.

- **Sensitive Keywords**
  - Customer Data: `customer_pii`, `credit_card`
  - Salary Info: `salary`, `payroll`, `compensation`
  - Security: `vulnerability`, `exploit`, `backdoor`
  - Business: `trade_secret`, `proprietary`, `confidential`

### 2. Routing Decider
**ทำหน้าที่:** ตัดสินใจเส้นทาง (Local vs Cloud)

**ระดับความสำคัญและการตัดสินใจ:**
```
HIGH SENSITIVITY (Secrets + Internal Resources)
    ↓
  LOCAL LLM ✅ (ปลอดภัย 100%, ช้า)

MEDIUM SENSITIVITY (PII + Sensitive Keywords)
    ↓
  CLOUD LLM (หลัง Data Masking)

LOW SENSITIVITY (ข้อมูลธรรมดา)
    ↓
  CLOUD LLM ✅ (เร็ว, ปลอดภัยแล้ว)
```

### 3. Audit Trail
**ทำหน้าที่:** บันทึก routing decision เพื่อการตรวจสอบ

**บันทึกข้อมูล:**
- Timestamp
- Input text (short)
- Sensitivity level
- Detected patterns
- Routing decision
- Reason
- Confidence score

### 4. SensitivityRouter (Main)
**ทำหน้าที่:** บริหารจัดการระบบทั้งหมด

---

## วิธีการใช้งาน

### Step 1: เตรียมสภาพแวดล้อม
```bash
# คัดลอกไฟล์ prototype ไปยังโปรเจกต์
cd d:\Hackathon\Cline_Consat
python sensitivity_router_prototype.py
```

### Step 2: รันทดสอบ
```bash
python sensitivity_router_prototype.py
```

**ผลลัพธ์ที่คาดหวัง:**
```
================================================================================
SENSITIVITY ROUTER - PROTOTYPE TEST
================================================================================

Test 1: ข้อมูลทั่วไป (LOW)
--------------------------------------------------------------------------------
Input (first 60 chars): ช่วยฉันเขียนฟังก์ชัน Python สำหรับการคำนวณค่าเฉลี่ย...
Sensitivity Level: LOW
Detected Patterns: []
Routing Decision: CLOUD
Reason: ข้อมูล LOW SENSITIVITY -> ส่งไป Cloud LLM สำหรับความเร็ว
Use Local LLM: False
Require Masking: False

Test 2: มี Email (MEDIUM)
...
```

### Step 3: ใช้งาน API ใน Code
```python
from sensitivity_router_prototype import SensitivityRouter

# สร้าง router instance
router = SensitivityRouter()

# วิเคราะห์ input
result = router.route("your input text here")

# ตรวจสอบผลลัพธ์
if result['use_local_llm']:
    print("ส่งไป Local LLM")
    # ... เรียก Local LLM API
else:
    if result['require_masking']:
        print("ต้อง Mask ก่อนส่ง Cloud")
        # ... ทำ data masking
    print("ส่งไป Cloud LLM")
    # ... เรียก Cloud LLM API

# ดู audit log
summary = router.get_audit_summary()
print(summary)
```

---

## ภาคต่อที่ต้องพัฒนา (ขั้นตอนถัดไป)

### 1. ปรับปรุง Pattern Detection
- [ ] เพิ่ม regex patterns สำหรับ domain/company-specific data
- [ ] ใช้ NER (Named Entity Recognition) สำหรับ PII detection ขั้นสูง
- [ ] เพิ่ม pattern สำหรับ binary/encrypted data

### 2. ปรับปรุง Routing Logic
- [ ] เพิ่ม MEDIUM_HIGH category (masking ที่มีข้อจำกัด)
- [ ] สนับสนุน custom routing rules ต่อ organization
- [ ] เพิ่ม fallback logic สำหรับ edge cases

### 3. Integrate กับ Task 5 (Data Masking)
- [ ] เชื่อม routing result เข้ากับ masking engine
- [ ] เก็บ mapping table ของ masked values
- [ ] ตรวจสอบ de-masking ทำงานได้ถูกต้อง

### 4. Integrate กับ Task 6 (Policy Enforcement)
- [ ] ใช้ routing decision เพื่อเลือก policy checklist
- [ ] ตรวจสอบ output ตามนโยบายทั้ง Local และ Cloud
- [ ] บันทึก policy check results ในเดียวกันกับ audit trail

### 5. Integrate กับ Task 7 (Monitoring)
- [ ] ส่ง metrics ไปยัง monitoring dashboard
- [ ] ตรวจสอบ routing latency
- [ ] เก็บ performance metrics ต่อ sensitivity level

---

## ทดลองเองด้วย Custom Input

สามารถสร้าง test file เพิ่มเติมได้:

```python
# test_sensitivity_router.py
from sensitivity_router_prototype import SensitivityRouter

router = SensitivityRouter()

# Test case ของคุณเอง
test_inputs = [
    "บอกฉันวิธีสร้างเว็บไซต์ Django",
    "วิธีเชื่อมต่อ postgresql://root:MyPassword@db.internal:5432/users",
    "อีเมลของฉันคือ john.doe@gmail.com",
]

for input_text in test_inputs:
    result = router.route(input_text)
    print(f"Input: {input_text}")
    print(f"Decision: {result['routing_decision']}")
    print(f"Reason: {result['reason']}")
    print("---")
```

---

## Checklist สำหรับ Task 4 Complete

- [ ] ดาวน์โหลด/คัดลอก `sensitivity_router_prototype.py`
- [ ] รัน prototype และตรวจสอบผลลัพธ์
- [ ] ทำความเข้าใจโครงสร้าง 4 ส่วน (Detector, Decider, AuditTrail, Router)
- [ ] ปรับแต่ง patterns ให้เหมาะสมกับ CONSAT ข้อมูล
- [ ] สร้าง test cases จากตัวอย่างข้อมูลจริง
- [ ] บันทึก audit log และตรวจสอบความถูกต้อง
- [ ] เตรียมพร้อม integrate กับ Task 5 (Data Masking)

---

## หมายเหตุ

- Prototype นี้ใช้ Regex ธรรมดา เหมาะสำหรับ MVP
- ถ้าต้องการความแม่นยำสูงขึ้น ให้ใช้ Presidio (MS library) หรือ spaCy NER
- Audit trail เก็บจำนวนเต็ม คำลง file ได้โดยเรียก `router.audit.save_to_file('audit.log')`
