# CONSAT PoC Task List

## Overview
PoC นี้ต้องการระบบ Secure Agentic Workflow ที่สามารถคัดกรองข้อมูลก่อนส่งไปยัง LLM, ทำ Data Masking/De-masking, ควบคุมนโยบายด้านความปลอดภัย, และบันทึก Audit Trail พร้อมระบบ Monitoring / Browser Control.

## Task 1: Research and Requirements
1. รวบรวมโจทย์จาก CONSAT และ Cline
2. ระบุ pain points ที่เกี่ยวกับ data privacy, infrastructure, policy
3. กำหนด use case ตัวอย่าง 2-3 แบบ (High sensitivity / Low sensitivity)
4. ระบุ standard security เช่น GDPR, ISO27001, ISO9001/14001

## Task 2: Environment Setup
1. ติดตั้ง Ollama และเตรียม Local LLM
2. เตรียม Cloud LLM API (Anthropic Claude หรือบริการที่ใช้ได้)
3. สร้าง Virtual Environment / Node project
4. ตรวจสอบว่าเครื่องมี spec เพียงพอสำหรับ Local LLM
5. กำหนด network/proxy policy สำหรับการเชื่อมต่อ Cloud

## Task 3: System Design
1. ออกแบบ architecture ของ PoC
   - Input → Sensitivity Router → Local/Cloud Path → Policy Guardrail → Output
2. ระบุ modules ที่ต้องสร้าง
   - router, masking, policy, audit, monitoring
3. ออกแบบ data flow สำหรับ mask/de-mask
4. กำหนด criteria สำหรับ routing decision

## Task 4: Sensitivity Router
1. สร้างฟังก์ชันวิเคราะห์ prompt/code
2. เขียน pattern detection สำหรับ PII, secrets, internal resources
3. ทดสอบ decision tree ว่าจะ send ไป Local หรือ Cloud
4. บันทึกเหตุผลการ routing

## Task 5: Data Masking and De-masking
1. สร้าง Masking Engine
   - แปลงข้อมูลสำคัญเป็น placeholder
2. สร้าง Mapping Table สำหรับ de-masking
3. ทดสอบ flow: prompt -> mask -> cloud -> output -> de-mask
4. เพิ่ม support สำหรับหลายชนิดข้อมูล (API key, IP, domain, PII)

## Task 6: Policy Enforcement and Audit
1. สร้าง Validation Layer สำหรับ output
   - Static code analysis
   - Rule-based security check
2. ตรวจสอบว่าผลลัพธ์ไม่ contain hardcoded credentials หรือ internal leak
3. สร้าง Audit Trail ของ routing decision และการตรวจสอบ policy
4. เก็บ log สำหรับทุก transaction

## Task 7: Monitoring / Browser Control
1. สร้างระบบ Monitoring เบื้องต้น
   - เก็บ metrics เช่น requests, Local/Cloud split, errors, masked items
2. สร้าง dashboard browser control ง่าย ๆ
   - แสดงสถานะ current model
   - แสดง route selection
   - แสดง alert / policy violation
3. เชื่อม monitoring เข้ากับ audit log
4. ทดสอบ browser control ว่าสามารถดูข้อมูลได้เรียลไทม์

## Task 8: Integration with Cline / MCP
1. สร้าง MCP server stub หรือ integration layer
2. ทดสอบการเรียกใช้งานจาก Cline input
3. เชื่อม path Local LLM และ Cloud LLM เข้ากับ MCP
4. ยืนยันว่า Cline สามารถรับผลลัพธ์จากระบบได้

## Task 9: Demo and Presentation
1. เตรียม demo flow ที่ชัดเจน
   - High sensitivity -> Local LLM
   - Low sensitivity -> Cloud LLM (with masking)
2. แสดง audit trail และ monitoring dashboard
3. สรุป security benefits และ decision logic
4. เตรียมสไลด์สั้น ๆ และ script การนำเสนอ

## Task 10: Refinement and Hardening
1. ปรับปรุง performance ของ routing และ masking
2. เสริม error handling, retry, timeout
3. ทบทวน policy rules และปรับให้ครอบคลุม
4. เพิ่ม unit test และ integration test สำหรับ PoC
