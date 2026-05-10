# Task 5: Data Masking Engine - Implementation Guide

## Overview
Data Masking Engine คือระบบที่ปิดบังข้อมูลสำคัญ (PII, Secrets, Internal Resources) ก่อนส่งไปยัง Cloud LLM เพื่อให้ข้อมูลปลอดภัย และเก็บ mapping table เพื่อคืนค่าหลังจาก Cloud LLM ตอบกลับมา

---

## ส่วนประกอบหลัก 2 ชิ้น

### 1. MaskingEngine
**ทำหน้าที่:** ปิดบังข้อมูล (Mask) และคืนค่าต้นฉบับ (De-mask)

**ตัวอย่างการทำงาน:**
```
Original:  "email: john@example.com, api_key: sk_live_123abc"
           ↓
Masked:    "email: {MASKED_EMAIL_a1b2c3d4}, api_key: {MASKED_API_KEY_e5f6g7h8}"
           ↓
Mapping:   {
  "{MASKED_EMAIL_a1b2c3d4}": "john@example.com",
  "{MASKED_API_KEY_e5f6g7h8}": "sk_live_123abc"
}
           ↓
Cloud LLM processes masked input...
           ↓
Output:    "Here is the response for {MASKED_EMAIL_a1b2c3d4}..."
           ↓
De-masked: "Here is the response for john@example.com..."
```

**Pattern Types ที่รองรับ:**
- `email` - Email addresses
- `api_key` - API keys and tokens
- `password` - Hardcoded passwords
- `token` - Authentication tokens
- `internal_ip` - Internal IP addresses (10.x, 172.16.x, 192.168.x)
- `internal_domain` - Internal domains (.internal, .local, .consat, .corp)
- `database_url` - Database connection strings
- `ssn` - Social Security Numbers

### 2. DataMaskingPipeline
**ทำหน้าที่:** รวมการ mask/de-mask เข้ากับ workflow

**Method หลัก:**
- `process_for_cloud()` - Mask input ก่อนส่ง Cloud
- `restore_output()` - De-mask output จาก Cloud

---

## วิธีการใช้งาน

### Step 1: เตรียมสภาพแวดล้อม
```bash
cd d:\Hackathon\Cline_Consat
python data_masking_prototype.py
```

### Step 2: ดูผลลัพธ์ทดสอบ
```
Test 1: API Key + Domain
  ✓ Original input มี api_key และ internal domain
  ✓ Masked output เปลี่ยนเป็น placeholders
  ✓ De-masked output คืนค่าเดิม
```

### Step 3: ใช้งาน API ใน Code
```python
from data_masking_prototype import DataMaskingPipeline

# สร้าง pipeline instance
pipeline = DataMaskingPipeline()

# Mask input ก่อนส่ง Cloud
masked_input, meta = pipeline.process_for_cloud("contact: john@example.com")
# masked_input: "contact: {MASKED_EMAIL_...}"
# meta: {'masked_items': {...}, 'mapping_id': 'mapping_...'}

# Simulate Cloud LLM response
cloud_response = f"Response to {masked_input}"

# De-mask output
restored = pipeline.restore_output(cloud_response)
# restored: "Response to contact: john@example.com"

# Get summary
summary = pipeline.get_summary()
# {'total_masked_items': 1, 'pattern_breakdown': {'email': 1}, ...}
```

---

## ขั้นตอนการ Implement สำหรับ Production

### 1. ตรวจสอบ Pattern ที่ถูกต้อง
- [ ] ทดสอบ regex pattern กับตัวอย่างข้อมูลจริง CONSAT
- [ ] เพิ่ม pattern ใหม่หากจำเป็น (เช่น company-specific format)
- [ ] ทดสอบ false positives/negatives

### 2. ปรับแต่ง Masking Strategy
- [ ] ตัดสินใจ placeholder format (ปัจจุบัน: `{MASKED_TYPE_UUID}`)
- [ ] กำหนด retention policy สำหรับ mapping table
- [ ] เพิ่ม encryption สำหรับ mapping table (ถ้าจำเป็น)

### 3. Integrate กับ Routing Decision
```python
from sensitivity_router_prototype import SensitivityRouter
from data_masking_prototype import DataMaskingPipeline

router = SensitivityRouter()
masking = DataMaskingPipeline()

user_input = "ช่วยฉันเชื่อมต่อ postgresql://admin:pass@db.internal"

# Step 1: Check sensitivity
routing = router.route(user_input)

if not routing['use_local_llm']:
    # Step 2: Mask ก่อนส่ง Cloud
    masked_input, meta = masking.process_for_cloud(user_input)
    # ... send masked_input to Cloud LLM
else:
    # Send original input to Local LLM (no masking)
    pass
```

### 4. เก็บ Mapping Table สำหรับ De-masking
```python
# Save mapping table
masking.masking_engine.save_mapping_table('mapping_table.json')

# Load mapping table สำหรับ de-mask ภายหลัง
masking.masking_engine.load_mapping_table('mapping_table.json')
restored = masking.restore_output(cloud_output)
```

### 5. Monitor Masking Performance
```python
summary = pipeline.get_summary()
print(f"Total masked items: {summary['total_masked_items']}")
print(f"Pattern breakdown: {summary['pattern_breakdown']}")

# Example output:
# Total masked items: 8
# Pattern breakdown: {
#   'api_key': 1,
#   'internal_domain': 2,
#   'email': 2,
#   'database_url': 1,
#   'token': 1,
#   'internal_ip': 1
# }
```

---

## Advanced Features

### 1. Custom Masking Rules
```python
# Extend MaskingEngine to add custom patterns
class CustomMaskingEngine(MaskingEngine):
    def __init__(self):
        super().__init__()
        # Add custom pattern
        self.patterns['company_id'] = {
            'regex': r'CONSAT-\d{5}-[A-Z]{3}',
            'mask_fn': lambda m: f'{{MASKED_COMPANY_ID_{uuid.uuid4().hex[:8]}}}'
        }
```

### 2. Selective Masking
```python
# Mask only high-risk patterns
high_risk_patterns = ['api_key', 'password', 'token']

masked_text = user_input
for pattern_type in high_risk_patterns:
    # Apply masking for high-risk only
    pass
```

### 3. Audit Trail สำหรับ Masking
```python
# Get detailed masking records
for record in masking.masking_engine.records:
    print(f"{record.timestamp}: {record.pattern_type}")
    print(f"  Original: {record.original_value}")
    print(f"  Masked: {record.masked_value}")
```

---

## Checklist สำหรับ Task 5 Complete

- [ ] ดาวน์โหลด/คัดลอก `data_masking_prototype.py`
- [ ] รัน prototype และตรวจสอบผลลัพธ์
- [ ] ทำความเข้าใจโครงสร้าง MaskingEngine และ Pipeline
- [ ] ปรับแต่ง patterns ให้เหมาะสมกับ CONSAT ข้อมูล
- [ ] เทส mask/de-mask จากตัวอย่างข้อมูลจริง
- [ ] เก็บ mapping table และตรวจสอบความถูกต้อง
- [ ] เตรียมพร้อม integrate กับ Task 4 (Routing) และ Task 6 (Policy)

---

## Troubleshooting

### ❌ De-masking ไม่ทำงาน
**สาเหตุ:** Mapping table ไม่ตรงกัน
**วิธีแก้:** 
- ตรวจสอบว่า placeholder ใน output ตรงกับใน mapping table
- เก็บ mapping table ก่อน send ไป Cloud

### ❌ Pattern ตรวจจับผิด
**สาเหตุ:** Regex too greedy หรือ too strict
**วิธีแก้:**
- ทดสอบ regex กับ test cases
- ปรับ pattern ให้ได้ผลที่ดีสำหรับข้อมูล CONSAT

### ❌ Performance ช้า
**สาเหตุ:** Regex ซับซ้อนหรือ input ใหญ่
**วิธีแก้:**
- ใช้ re.compile() เพื่อ cache patterns
- ลด regex complexity
- ทำ caching ของ mapping results

---

## หมายเหตุ

- Prototype ใช้ UUID สั้น (8 char) สำหรับ placeholder
- Mapping table เก็บใน memory (ต้องเก็บ persistent สำหรับ production)
- De-masking ทำการ string replacement แบบง่าย (จำเป็นต้องเก็บ order ของ masking)
