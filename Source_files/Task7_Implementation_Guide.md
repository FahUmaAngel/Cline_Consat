# Task 7: Monitoring Dashboard - Implementation Guide

## Overview
Monitoring Dashboard คือระบบที่เก็บ metrics จากการทำงานของระบบทั้งหมด (Task 4-6) เพื่อติดตามประสิทธิภาพ ความปลอดภัย และสถานะของ Secure Agentic Workflow

---

## ส่วนประกอบหลัก 3 ชิ้น

### 1. MetricsCollector
**ทำหน้าที่:** รวบรวม metrics จากระบบต่าง ๆ

**Metrics ที่เก็บ:**
- `REQUEST_COUNT` - จำนวน requests ทั้งหมด
- `LOCAL_ROUTING_COUNT` - จำนวน requests ไป Local LLM
- `CLOUD_ROUTING_COUNT` - จำนวน requests ไป Cloud LLM
- `MASKING_ITEMS` - จำนวน items ที่ถูก mask
- `POLICY_VIOLATIONS` - จำนวน policy violations
- `PROCESSING_TIME` - เวลาประมวลผล (ms)
- `ERROR_COUNT` - จำนวน errors

**Alert Thresholds:**
```
processing_time_ms > 5000      → ⚠️ WARNING
error_rate_percent > 5          → ⚠️ WARNING
policy_violation_rate > 10     → 🔴 CRITICAL
```

### 2. DashboardCalculator
**ทำหน้าที่:** คำนวณสถิติและสรุป metrics

**สถิติที่คำนวณ:**
- Total requests
- Local/Cloud split percentage
- Average processing time
- Total masked items
- Policy violations count
- Alert counts

### 3. MonitoringDashboard
**ทำหน้าที่:** รวมระบบและแสดง dashboard

**Features:**
- Record request metrics
- Calculate statistics
- Display dashboard in text format
- Export metrics to JSON
- Get system health status

---

## วิธีการใช้งาน

### Step 1: เตรียมสภาพแวดล้อม
```bash
cd d:\Hackathon\Cline_Consat
python monitoring_dashboard_prototype.py
```

### Step 2: ดูผลลัพธ์ทดสอบ
```
📊 MONITORING DASHBOARD
Timestamp: 2026-05-04T22:12:47.550135

📈 REQUEST STATISTICS
  Total Requests: 7
  Local Routing: 2 (28.6%)
  Cloud Routing: 5 (71.4%)

⚙️ PROCESSING
  Avg Processing Time: 1618.57 ms
  Total Masked Items: 9

🔐 SECURITY & COMPLIANCE
  Total Policy Violations: 3
  Total Alerts: 1
  Critical Alerts: 0

System Health: DEGRADED ⚠️
```

### Step 3: ใช้งาน API ใน Code
```python
from monitoring_dashboard_prototype import MonitoringDashboard

# สร้าง dashboard instance
dashboard = MonitoringDashboard()

# Record request metrics
dashboard.record_request(
    routing_decision='cloud',
    processing_time=500.5,
    masked_items=2,
    policy_violations=0
)

# Display dashboard
dashboard.display_dashboard()

# Get health status
health = dashboard.get_health_status()
print(f"System Health: {health['health']}")

# Export metrics
dashboard.export_metrics_json('metrics.json')
```

---

## ขั้นตอนการ Implement สำหรับ Production

### 1. Integrate กับ Workflow
```python
from secure_agentic_workflow import SecureAgenticWorkflow

workflow = SecureAgenticWorkflow()

# Process request
result = workflow.process(user_input, llm_output)

# Monitoring จะ auto-record metrics
workflow.monitoring.record_request(
    routing_decision=result['routing']['decision'],
    processing_time=float(result['metrics']['processing_time_ms']),
    masked_items=result['metrics']['masked_items_count'],
    policy_violations=result['policy_check']['critical_violations'],
)

# Display dashboard
workflow.monitoring.display_dashboard()
```

### 2. Real-time Monitoring
```python
# Create background task สำหรับ periodic dashboard updates
import threading
import time

class RealtimeDashboard:
    def __init__(self, dashboard, update_interval=30):
        self.dashboard = dashboard
        self.update_interval = update_interval
    
    def start(self):
        thread = threading.Thread(target=self._update_loop, daemon=True)
        thread.start()
    
    def _update_loop(self):
        while True:
            time.sleep(self.update_interval)
            self.dashboard.display_dashboard()

# Usage
realtime = RealtimeDashboard(workflow.monitoring, update_interval=30)
realtime.start()
```

### 3. Export Metrics สำหรับ External Systems
```python
import json
import requests

def export_to_prometheus(dashboard, prometheus_url):
    """Export metrics to Prometheus"""
    stats = dashboard.calculator.calculate_stats()
    
    # Convert to Prometheus format
    prometheus_data = f"""
# HELP requests_total Total number of requests
# TYPE requests_total counter
requests_total {stats['total_requests']}

# HELP local_routing_count Local LLM requests
# TYPE local_routing_count counter
local_routing_count {stats['local_routing_count']}

# HELP cloud_routing_count Cloud LLM requests
# TYPE cloud_routing_count counter
cloud_routing_count {stats['cloud_routing_count']}

# HELP processing_time_ms Average processing time
# TYPE processing_time_ms gauge
processing_time_ms {float(stats['avg_processing_time_ms'])}
    """
    
    # Push to Prometheus
    requests.post(f"{prometheus_url}/metrics/put", data=prometheus_data)

def export_to_datadog(dashboard, datadog_api_key):
    """Export metrics to Datadog"""
    stats = dashboard.calculator.calculate_stats()
    
    metrics = {
        'requests_total': stats['total_requests'],
        'local_routing': stats['local_routing_count'],
        'cloud_routing': stats['cloud_routing_count'],
        'avg_processing_time_ms': float(stats['avg_processing_time_ms']),
    }
    
    headers = {'DD-API-KEY': datadog_api_key}
    requests.post('https://api.datadoghq.com/api/v1/series', 
                  json=metrics, headers=headers)
```

### 4. Alert Management
```python
class AlertManager:
    def __init__(self, dashboard):
        self.dashboard = dashboard
        self.alert_handlers = []
    
    def register_handler(self, handler_fn):
        """Register alert handler (email, slack, etc)"""
        self.alert_handlers.append(handler_fn)
    
    def check_alerts(self):
        """Check for alerts and notify"""
        alerts = self.dashboard.metrics_collector.get_all_alerts()
        
        for alert in alerts:
            if alert['severity'] == 'critical':
                for handler in self.alert_handlers:
                    handler(alert)
    
    def send_slack_alert(self, alert):
        """Send alert to Slack"""
        import requests
        payload = {
            'text': f"🔴 {alert['severity'].upper()}: {alert['message']}"
        }
        requests.post(SLACK_WEBHOOK_URL, json=payload)

# Usage
alert_mgr = AlertManager(workflow.monitoring)
alert_mgr.register_handler(alert_mgr.send_slack_alert)

while True:
    time.sleep(30)
    alert_mgr.check_alerts()
```

### 5. Custom Metrics
```python
# Add custom metrics specific to CONSAT
class ConSATMetrics:
    def __init__(self):
        self.consat_specific_metrics = {
            'customer_data_masked': 0,
            'internal_api_calls': 0,
            'gdpr_compliance_checks': 0,
            'iso27001_violations': 0,
        }
    
    def record_customer_data_masked(self, count):
        self.consat_specific_metrics['customer_data_masked'] += count
    
    def record_internal_api_call(self):
        self.consat_specific_metrics['internal_api_calls'] += 1
    
    def get_compliance_score(self):
        """Calculate CONSAT compliance score"""
        violations = self.consat_specific_metrics['iso27001_violations']
        checks = self.consat_specific_metrics['gdpr_compliance_checks']
        
        if checks == 0:
            return 100
        return int((1 - violations / checks) * 100)
```

---

## Dashboard Types

### 1. Text-based Dashboard (CLI)
```
Suitable for: Development, logs viewing
Implemented in: monitoring_dashboard_prototype.py
```

### 2. Web-based Dashboard (Optional)
```
Suitable for: Production monitoring, team visibility
Technology: Flask/FastAPI + Chart.js/Grafana
Features:
  - Real-time metrics
  - Historical trends
  - Alert notifications
  - Export reports
```

### 3. Email Reports
```
Suitable for: Executive summary, daily reports
Content:
  - Total requests processed
  - Approval rate
  - Security issues found
  - Performance metrics
  - Recommendations
```

---

## Metrics Export Formats

### JSON Format
```json
{
  "dashboard_stats": {
    "total_requests": 100,
    "local_routing_percent": "25.0%",
    "avg_processing_time_ms": "450.25"
  },
  "all_metrics": [
    {
      "timestamp": "2026-05-04T22:12:47.550135",
      "metric_type": "request_count",
      "value": 1
    }
  ],
  "all_alerts": [
    {
      "timestamp": "2026-05-04T22:12:50.123456",
      "severity": "warning",
      "message": "Processing time 5500ms exceeds threshold"
    }
  ]
}
```

### CSV Format (for Excel/Data Analysis)
```csv
timestamp,metric_type,value,tags
2026-05-04T22:12:47,request_count,1,
2026-05-04T22:12:47,local_routing_count,1,"route=local"
2026-05-04T22:12:47,processing_time,500.5,
```

---

## Checklist สำหรับ Task 7 Complete

- [ ] ดาวน์โหลด/คัดลอก `monitoring_dashboard_prototype.py`
- [ ] รัน prototype และตรวจสอบผลลัพธ์
- [ ] ทำความเข้าใจ 3 ส่วน: Collector, Calculator, Dashboard
- [ ] เขียน metrics collection จาก workflow
- [ ] ทำสไตล์ dashboard ให้ดูดี
- [ ] เพิ่ม alert thresholds ที่เหมาะสม
- [ ] Export metrics ไปยัง external systems (ถ้าจำเป็น)
- [ ] เตรียมพร้อม integrate กับ secure_agentic_workflow.py

---

## Performance Considerations

| Component | Typical Time | Notes |
|-----------|--------------|-------|
| Record metric | ~1ms | Very fast |
| Calculate stats | ~5ms | Depends on # metrics |
| Display dashboard | ~10ms | Text output |
| Export JSON | ~20ms | File I/O |

---

## Troubleshooting

### ❌ Dashboard ไม่อัปเดต
**สาเหตุ:** Metrics ไม่ถูก record
**วิธีแก้:**
- ตรวจสอบว่า `record_request()` ถูกเรียก
- ดู logs ว่ามี error หรือไม่

### ❌ Alert ไม่ถูกสร้าง
**สาเหตุ:** Threshold ตั้งสูงเกินไป
**วิธีแก้:**
- ปรับ thresholds ในตัวสร้าง
- ทำ baseline หลังจาก 100+ requests

### ❌ Export ไม่ทำงาน
**สาเหตุ:** Permission issue หรือ disk full
**วิธีแก้:**
- ตรวจสอบ file permissions
- ตรวจสอบ disk space
- ลอง export ไปยัง temp directory

---

## หมายเหตุ

- Prototype เก็บ metrics ใน memory (ต้อง persistent storage สำหรับ production)
- Alert thresholds เป็น default values (ต้องปรับตามความต้องการ)
- Dashboard display เป็น text format (สามารถขยายไปเป็น web UI)
- Metrics export รองรับ JSON (สามารถเพิ่ม CSV, Prometheus, etc)
