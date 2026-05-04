# CONSAT Secure Agentic Workflow PoC Plan

## 1. Infrastructure Requirements
- ระบุสภาพแวดล้อมที่จะใช้จริงในการพัฒนาและทดสอบ
- กำหนดว่าระบบจะรันบนเครื่องไหน, เซิร์ฟเวอร์ใด, หรือ VM/Container ใด
- ตรวจสอบว่า Local LLM, Masking Engine, MCP server และ Cloud integration สามารถทำงานร่วมกันได้

## 2. Local Machine Spec
- CPU: อย่างน้อย 8 cores, แนะนำ 16 cores ขึ้นไปสำหรับ Local LLM
- RAM: 32GB ขึ้นไป ถ้าใช้โมเดล 7B-14B
- Storage: SSD 500GB ขึ้นไปสำหรับโมเดลและ data cache
- GPU: ถ้ามี จะช่วยได้มากสำหรับ Local LLM แต่สามารถรันบน CPU ได้ถ้าขนาดโมเดลไม่ใหญ่
- OS: Linux หรือ Windows ที่รองรับ Ollama และ runtime ที่ต้องใช้

## 3. Network / Proxy Policy
- ระบุว่าเครื่อง Local ต้องเชื่อมต่อ Internet ได้หรือไม่
- หากเชื่อมต่อ Cloud LLM ต้องใช้งานผ่าน Proxy หรือ Firewall ใด
- จำกัดเส้นทางการส่งข้อมูล: เฉพาะ API endpoint ที่อนุญาตเท่านั้น
- กำหนดว่า external outbound traffic จะถูกควบคุมอย่างไร
- บันทึก URL/Domain ที่อนุญาต เช่น Anthropic API, Ollama local endpoint

## 4. หากใช้ Ollama ต้องรู้ Config
- ติดตั้ง Ollama และตรวจสอบเวอร์ชัน
- config หลักที่ต้องใช้ เช่น
  - `ollama start` / `ollama run`
  - model name ที่ใช้ เช่น `llama-3` หรือ `mistral`
  - port / host ที่ให้บริการ local LLM
  - memory / cache setting สำหรับ performance
  - security setting เช่น access control, network binding
- วางแผนว่า Local LLM จะเรียกผ่าน API endpoint แบบใด

## 5. ข้อเสนอแนะเพิ่มเติม
- เริ่มจากโฟกัสที่ `Sensitivity-Aware Routing` ก่อน
- ทำ Proof of Concept ให้เห็นว่า input ถูกส่งไปยัง Local/Cloud อย่างถูกต้อง
- สร้าง Audit Trail เพื่อบันทึก decision และเหตุผลการ routing
- ใช้เทคนิค Masking/De-masking แบบง่ายก่อน แล้วค่อยขยายให้ซับซ้อน
- ทำให้ระบบสามารถตรวจสอบ policy และผลลัพธ์ของ AI ได้ก่อนส่งคืนผู้ใช้
- เพิ่มระบบ Monitoring และ Browser Control เพื่อดูสถานะ routing, model selection, alert และค่าประสิทธิภาพแบบเรียลไทม์

## 5.1 Monitoring / Browser Control
- สร้าง dashboard browser control ง่าย ๆ สำหรับดู status ของระบบ
  - แสดงว่า request ใดถูกส่งไป Local vs Cloud
  - แสดง model ที่ใช้งาน และสถานะของ LLM
  - แจ้ง alert หากเกิด policy violation หรือ masking error
- เก็บ metrics ของระบบ เช่น request count, latency, error rate, masked fields
- เชื่อม monitoring เข้ากับ audit log เพื่อให้ตรวจสอบย้อนหลังได้

## 6. หากต้องการให้ช่วยร่าง
### 6.1 question template เพื่อถาม team CONSAT
- ขอรายละเอียด policy สำหรับข้อมูลความลับในโค้ด เช่น PII, secrets, internal API
- ต้องการให้ระบบบังคับใช้ library whitelist หรือมี blacklist หรือไม่
- ต้องการให้ Local LLM ทำงานกับโมเดลขนาดใด และมีข้อจำกัดด้าน compute อย่างไร
- รูปแบบ proxy/network ที่ใช้เมื่อเชื่อมต่อ Cloud LLM
- ข้อมูล Dummy หรือ sample prompt ที่ใช้ทดสอบ PoC
- มาตรฐานการตรวจสอบโค้ดขององค์กร เช่น error handling, logging, auth flow

### 6.2 project skeleton
- backend/
  - `router.py` หรือ `router.ts`
  - `masking.py` / `masking.ts`
  - `policy.py` / `policy.ts`
  - `audit.py` / `audit.ts`
- integration/
  - MCP server stub
  - Local LLM client
  - Cloud LLM client
- docs/
  - architecture.md
  - security-policy.md
- samples/
  - prompt_examples.md
  - sensitive_data_samples.md

### 6.3 proto code ของ sensitivity router + masking engine
- prototype ของ `sensitivity router` ที่อ่าน prompt และตัดสินใจ Local/Cloud
- prototype ของ `masking engine` ที่แปลง secret/PII เป็น placeholder และ de-mask คืน

## 7. ถ้าจะเริ่มจาก backend prototype โดยตรง
- ให้เลือกภาษาที่ถนัด:
  - หากต้องการเน้น integration กับ Cline/Node.js: ใช้ **TypeScript**
  - หากต้องการเน้นการพัฒนา logic, prototyping, และ ML integration: ใช้ **Python**
- แนะนำ:
  - ถ้าอยากได้ความเร็วในการเขียนและ prototype ให้ลง Python ก่อน
  - ถ้าต้องการต่อกับ Cline และ MCP ได้ลื่นขึ้น ให้เริ่ม TypeScript

## 8. ข้อเสนอแนะการเลือกภาษา
- **Python**: เหมาะสำหรับ backend prototype, masking, static analysis, integration กับ Presidio, AI workflow logic
- **TypeScript**: เหมาะสำหรับ MCP server, Cline extension, frontend integration, production-ready service
