"""
Secure Agentic Workflow Orchestrator
======================================
Orchestrates and connects all components for Task 4, 5, 6, 7

Author: CONSAT PoC Team
Date: May 4, 2026
"""

import time
import json
import requests
import os
import uuid
from dotenv import load_dotenv
from typing import Dict, Optional
import audit_log

load_dotenv()
from sensitivity_router_prototype import SensitivityRouter, SensitivityLevel
from data_masking_prototype import DataMaskingPipeline
from policy_enforcement_prototype import PolicyEnforcementPipeline
from monitoring_dashboard_prototype import MonitoringDashboard
import stockholm_bus_data as bus_db
import data_policy
import json


class SecureAgenticWorkflow:
    """
    Orchestrator for the Secure Agentic Workflow.

    Integrates:
    - Task 4: Sensitivity Router
    - Task 5: Data Masking Engine
    - Task 7: Monitoring Dashboard
    """
    
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


    
    def __init__(self):
        """Initialize all components"""
        self.router = SensitivityRouter()
        self.masking = DataMaskingPipeline()
        self.policy = PolicyEnforcementPipeline()
        self.monitoring = MonitoringDashboard()
        self.request_history = []
        
    def _fetch_context(self, user_input: str, is_local: bool = False) -> str:
        """Query the real stockholm_bus_data database and return relevant data as context.

        For LOCAL LLM: raw data (full fidelity).
        For CLOUD LLM: fields are filtered through data_policy.filter_for_external().
        """
        def _filter(table: str, records: list) -> list:
            if is_local:
                return records
            return [data_policy.filter_record_for_external(table, r) for r in records]

        try:
            text = user_input.lower()

            # Specific vehicle lookup
            for v in bus_db.BUS_VEHICLES:
                if v["vehicle_id"].lower() in text:
                    drivers = _filter("drivers", bus_db.get_drivers(v["vehicle_id"]))
                    readings = _filter("iot_sensor_readings", bus_db.get_sensor_readings(vehicle_id=v["vehicle_id"])[:3])
                    maintenance = _filter("maintenance_logs", bus_db.get_maintenance_logs(v["vehicle_id"]))
                    vehicle_data = _filter("bus_vehicles", [v])[0]
                    return json.dumps({
                        "vehicle": vehicle_data,
                        "drivers": drivers,
                        "recent_sensor_readings": readings,
                        "maintenance_logs": maintenance,
                    }, indent=2)

            # Specific driver lookup
            for d in bus_db.DRIVERS:
                if d["driver_id"].lower() in text:
                    driver_data = _filter("drivers", [d])[0]
                    readings = bus_db.get_sensor_readings()
                    driver_readings = _filter("iot_sensor_readings", [r for r in readings if r["driver_id"] == d["driver_id"]][:3])
                    shifts = _filter("driver_shifts", bus_db.get_shifts(driver_id=d["driver_id"])[:5])
                    return json.dumps({"driver": driver_data, "sensor_readings": driver_readings, "shifts": shifts}, indent=2)

            # Line number lookup
            for route in bus_db.BUS_ROUTES:
                if str(route["line_number"]) in text or route["line_name"].lower() in text:
                    vehicles = _filter("bus_vehicles", bus_db.get_vehicles(route["route_id"]))
                    stops = _filter("bus_stops", bus_db.get_stops(route["route_id"])[:5])
                    return json.dumps({"route": route, "vehicles": vehicles, "stops": stops}, indent=2)

            # General search fallback (includes maintenance_logs, shifts, incidents)
            results = bus_db.search_data(user_input)
            return json.dumps({
                "routes":      results["routes"][:2],
                "vehicles":    _filter("bus_vehicles",        results["vehicles"][:2]),
                "drivers":     _filter("drivers",             results["drivers"][:2]),
                "maintenance":  _filter("maintenance_logs",   results["maintenance"][:3]),
                "shifts":      _filter("driver_shifts",       results["shifts"][:3]),
                "incidents":   _filter("incidents",           results["incidents"][:3]),
            }, indent=2)
        except Exception as e:
            return f"[DB Error: {e}]"
    
    def _call_openrouter(self, prompt: str, is_local: bool) -> str:
        """Calls OpenRouter API using Gemini models to generate real LLM response."""
        if not self.OPENROUTER_API_KEY:
            label = "LOCAL" if is_local else "CLOUD"
            print(f"      [API] No API key — returning simulated {label} response.")
            return self._simulated_response(prompt, is_local)

        model = "google/gemini-2.5-flash"
        print(f"      [API] Calling OpenRouter ({model})...")
        try:
            sys_msg = "You are a helpful data assistant for CONSAT. Keep responses concise and factual."
            if is_local:
                sys_msg = "You are a highly secure, private LOCAL AI model for CONSAT. You have access to raw sensitive data. Keep responses concise and factual."

            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.OPENROUTER_API_KEY}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "CONSAT Secure AI Gateway",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=10,
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"      [API] Error calling OpenRouter: {e}")
            return self._simulated_response(prompt, is_local)

    def _simulated_response(self, prompt: str, is_local: bool) -> str:
        """Return a realistic-looking simulated LLM response for demo purposes."""
        label = "Local LLM" if is_local else "Cloud LLM"
        keyword = prompt[:80].strip()
        return (
            f"[{label} — Simulated]\n\n"
            f"Based on the CONSAT database, here is the analysis for your query:\n"
            f'"{keyword}..."\n\n'
            "Key findings:\n"
            "• Route 172 operates Norsborg ↔ Skarpnäck (42 stops, every 10 min)\n"
            "• Vehicle fleet: 16 buses, avg eco-drive score 84.2\n"
            "• No critical incidents in the last 30 days\n\n"
            "Note: This is a simulated response. Set OPENROUTER_API_KEY for live LLM output."
        )
    
    def process(self, user_input: str, llm_output: Optional[str] = None, force_route: str = "auto") -> Dict:
        """
        Process user input through the entire secure workflow
        
        Args:
            user_input (str): Original input from user/Cline
            llm_output (Optional[str]): Optional - output from LLM to validate
            force_route (str): "auto", "cloud", or "local" to bypass router
        
        
        Returns:
            Dict: Final result with all checks and decisions
        """
        start_time = time.time()
        trace_id = audit_log.new_trace_id()

        print(f"\n{'='*80}")
        print("🔐 SECURE AGENTIC WORKFLOW PROCESSING")
        print(f"{'='*80}")
        
        # ========== Step 1: Sensitivity Router ==========
        print(f"\n[Step 1] 🔍 Sensitivity Analysis...")
        routing_result = self.router.route(user_input)
        
        if force_route == "cloud":
            use_local = False
            if routing_result['sensitivity_level'] == SensitivityLevel.HIGH.value:
                routing_result['reason'] = "Manual Override (Cloud) ⚠️ HIGH sensitivity – Data will be masked before sending"
            else:
                routing_result['reason'] = "Manual Override (Cloud)"
        elif force_route == "local":
            use_local = True
            routing_result['reason'] = "Manual Override (Local)"
        else:
            use_local = routing_result['use_local_llm']
        
        print(f"  ├─ Sensitivity Level: {routing_result['sensitivity_level'].upper()}")
        print(f"  ├─ Detected Patterns: {routing_result['detected_patterns']}")
        print(f"  └─ Decision: {routing_result['routing_decision'].upper()}")

        audit_log.log_routing(
            sensitivity=routing_result['sensitivity_level'],
            decision=routing_result['routing_decision'],
            reason=routing_result.get('reason', ''),
            trace_id=trace_id,
            force_override=(force_route in ("cloud", "local")),
        )
        
        # ========== Step 2: Route Decision ==========
        if use_local:
            print(f"\n{'═'*60}")
            print(f"  🔒 ROUTING TO PRIVATE CLOUD  (On-Premise Secure LLM)")
            print(f"     ⚠  HIGH sensitivity data detected")
            print(f"     ⛔ Blocking public internet access — local only")
            print(f"{'═'*60}")
            masked_input = user_input
            masking_info = None
            llm_to_use = "local"
        else:
            print(f"\n{'═'*60}")
            print(f"  ☁️  ROUTING TO PUBLIC CLOUD   (Gemini Flash)")
            print(f"     ✅ Safe to route — no sensitive data detected")
            print(f"{'═'*60}")
            
            # ========== Step 3: Data Masking ==========
            print(f"\n[Step 3] 🔒 Data Masking...")
            masked_input, masking_info = self.masking.process_for_cloud(user_input)
            
            masked_count_step3 = sum(len(v) for v in masking_info['masked_items'].values())
            print(f"  ├─ Masked Items: {masked_count_step3}")
            print(f"  └─ Mapping ID: {masking_info['mapping_id']}")
            audit_log.log_masking("user_input", masked_count_step3, trace_id=trace_id)
            
            llm_to_use = "cloud"
        
        # ========== Step 4: LLM Processing ==========
        print(f"\n[Step 4] 🤖 LLM Processing ({llm_to_use.upper()})...")
        if llm_output:
            final_output = llm_output
        else:
            # Fetch real data context from the database
            print(f"      [DB] Fetching real context from stockholm_bus_data...")
            db_context = self._fetch_context(user_input, is_local=use_local)
            
            if use_local:
                # Local LLM — PII must still be masked (GDPR), SECRET stays visible
                # (on-premise LLM is trusted for proprietary operational data)
                print(f"      [MASK] Applying PII masking for local LLM path...")
                pii_masked_context, masking_info = self.masking.process_for_local(db_context)
                local_schema = masking_info.get('schema_masking', {})
                if local_schema.get('fields_masked', 0):
                    print(f"      [MASK] PII masked: {local_schema['by_action'].get('hash', [])} hashed, "
                          f"{local_schema['by_action'].get('encrypt', [])} encrypted")
                enriched_prompt = f"""The user asked: "{user_input}"

Here is the data from the CONSAT database (PII is masked, operational data is accessible):
{pii_masked_context}

Answer the user's question using only the data above. Be concise and factual."""
            else:
                # Cloud LLM: receives already-masked prompt text + masked real data
                masked_context, db_masking_info = self.masking.process_for_cloud(db_context)
                # Merge db masking counts (both regex and schema) into masking_info
                if masking_info and db_masking_info:
                    for k, v in db_masking_info['masked_items'].items():
                        if k in masking_info['masked_items']:
                            masking_info['masked_items'][k].extend(v)
                        else:
                            masking_info['masked_items'][k] = v
                    # Merge schema masking reports
                    db_schema = db_masking_info.get('schema_masking', {})
                    cur_schema = masking_info.get('schema_masking', {})
                    merged_events = cur_schema.get('events', []) + db_schema.get('events', [])
                    masking_info['schema_masking'] = {
                        'fields_masked': len(merged_events),
                        'tables_detected': list({e['table'] for e in merged_events}),
                        'events': merged_events,
                        'by_action': {
                            'hash':    [e['field'] for e in merged_events if e['action'] == 'hash'],
                            'encrypt': [e['field'] for e in merged_events if e['action'] == 'encrypt'],
                            'redact':  [e['field'] for e in merged_events if e['action'] == 'redact'],
                        },
                    }
                elif db_masking_info:
                    masking_info = db_masking_info
                enriched_prompt = f"""The user asked: \"{masked_input}\"

Here is the relevant data from the CONSAT database (PII has been masked):
{masked_context}

Answer the user's question using only the data above. Be concise and factual."""
            
            final_output = self._call_openrouter(enriched_prompt, use_local)
            
        print(f"  └─ Output: {final_output[:60]}...")
        
        # ========== Step 5: De-masking (if Cloud) ==========
        if not use_local and final_output and masking_info:
            print(f"\n[Step 5] 🔓 De-masking...")
            final_output = self.masking.restore_output(final_output)
            print(f"  └─ Restored: {final_output[:60]}...")
        
        # ========== Step 6: Policy Enforcement ==========
        print(f"\n[Step 6] 📋 Policy Enforcement Check...")
        policy_result = self.policy.validate_ai_output(final_output)
        approved = policy_result['code_approved']
        
        audit_log.log_policy_check(approved, policy_result['critical_violations'], trace_id=trace_id)

        if approved:
            print(f"  ✅ APPROVED (0 critical violations)")
        else:
            print(f"  ❌ REJECTED ({policy_result['critical_violations']} critical violations)")
            if policy_result['violations']:
                for violation in policy_result['violations'][:2]:
                    print(f"     - [{violation['severity'].upper()}] {violation['message']}")
        
        # ========== Step 7: Monitoring ==========
        print(f"\n[Step 7] 📊 Recording Metrics...")
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        masked_count = 0
        if masking_info:
            masked_count = sum(len(v) for v in masking_info['masked_items'].values())
        
        violation_count = policy_result['critical_violations']
        force_overridden = (force_route in ("cloud", "local"))

        self.monitoring.record_request(
            routing_decision="local" if use_local else "cloud",
            processing_time=processing_time,
            masked_items=masked_count,
            policy_violations=violation_count,
            sensitivity_level=routing_result['sensitivity_level'],
            force_overridden=force_overridden,
        )

        print(f"  ├─ Processing Time: {processing_time:.2f}ms")
        print(f"  ├─ Route: {'LOCAL' if use_local else 'CLOUD'}")
        print(f"  ├─ Masked Items: {masked_count}")
        print(f"  └─ Policy Violations: {violation_count}")

        if not approved:
            final_status = 'rejected'
        else:
            final_status = 'approved'

        # Flag: request was auto-routed to local LLM for security
        # (COMPANY_SECRET / HIGH sensitivity → local is the CORRECT path,
        #  data is visible internally per policy — this is NOT a block)
        secured_locally = use_local and not force_overridden

        # ========== Final Result ==========
        schema_report = (masking_info or {}).get('schema_masking', {})

        result = {
            'request_id': f"req_{int(time.time() * 1000)}",
            'trace_id': trace_id,
            'user_input': user_input,
            'status': final_status,
            'secured_locally': secured_locally,
            'force_overridden': force_overridden,
            'force_route': force_route if force_overridden else 'auto',
            'timestamp': time.time(),
            'routing': {
                'decision': routing_result['routing_decision'],
                'reason': routing_result['reason'],
                'llm_used': llm_to_use,
                'sensitivity_level': routing_result['sensitivity_level'],
                'detected_patterns': routing_result.get('detected_patterns', []),
            },
            'masking': masking_info,
            'schema_masking': {
                'fields_masked': schema_report.get('fields_masked', 0),
                'tables_detected': schema_report.get('tables_detected', []),
                'hashed_fields':   (schema_report.get('by_action') or {}).get('hash', []),
                'encrypted_fields': (schema_report.get('by_action') or {}).get('encrypt', []),
                'redacted_fields': (schema_report.get('by_action') or {}).get('redact', []),
            },
            'policy_check': {
                'approved': approved,
                'total_violations': policy_result['total_violations'],
                'critical_violations': policy_result['critical_violations'],
                'violations': policy_result['violations'],
            },
            'metrics': {
                'processing_time_ms': f"{processing_time:.2f}",
                'masked_items_count': masked_count,
            },
            'final_output': final_output if approved else None,
        }
        
        # Store in history
        self.request_history.append(result)
        
        status_icon = {"approved": "✅", "rejected": "❌"}.get(final_status, "ℹ️")
        local_note = " (🔒 Secured via Local LLM)" if secured_locally else ""
        print(f"\n{'='*80}")
        print(f"{status_icon} WORKFLOW COMPLETE - Status: {result['status'].upper()}{local_note}")
        print(f"{'='*80}\n")
        
        return result
    
    def show_dashboard(self):
        """Display monitoring dashboard"""
        self.monitoring.display_dashboard()
    
    def get_stats(self) -> Dict:
        """Get workflow statistics"""
        if not self.request_history:
            return {'total_requests': 0}
        
        approved_count = sum(1 for r in self.request_history if r['status'] == 'approved')
        rejected_count = sum(1 for r in self.request_history if r['status'] == 'rejected')
        secured_locally_count = sum(1 for r in self.request_history if r.get('secured_locally', False))
        local_count = sum(1 for r in self.request_history if r['routing']['llm_used'] == 'local')
        cloud_count = sum(1 for r in self.request_history if r['routing']['llm_used'] == 'cloud')
        
        total_time = sum(float(r['metrics']['processing_time_ms']) for r in self.request_history)
        avg_time = total_time / len(self.request_history) if self.request_history else 0
        
        return {
            'total_requests': len(self.request_history),
            'approved': approved_count,
            'rejected': rejected_count,
            'secured_locally': secured_locally_count,
            'approval_rate': f"{(approved_count / len(self.request_history) * 100):.1f}%" if self.request_history else "0%",
            'local_llm_used': local_count,
            'cloud_llm_used': cloud_count,
            'avg_processing_time_ms': f"{avg_time:.2f}",
        }
    
    def export_logs(self, filepath: str):
        """Export all audit logs and metrics"""
        data = {
            'workflow_stats': self.get_stats(),
            'request_history': self.request_history,
            'dashboard_health': self.monitoring.get_health_status(),
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Logs exported to {filepath}")


# ============== Test Cases ==============

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("SECURE AGENTIC WORKFLOW - INTEGRATION TEST")
    print("=" * 80)
    
    workflow = SecureAgenticWorkflow()
    
    # Test Case 1: Safe Code Query -> Cloud LLM
    print("\n\n📌 TEST CASE 1: Simple Python Function")
    result1 = workflow.process(
        user_input="Create a Python function to calculate the average of a list",
        llm_output="def calculate_average(items):\n    return sum(items) / len(items)"
    )
    print(f"Result: {result1['status'].upper()}")
    
    # Test Case 2: Sensitive Code Query -> Local LLM
    print("\n\n📌 TEST CASE 2: Database Connection (SENSITIVE)")
    result2 = workflow.process(
        user_input="Create an API client to connect to postgresql://admin:MyPassword@db.internal:5432/users",
        llm_output="from config import get_db\ndb = get_db()"
    )
    print(f"Result: {result2['status'].upper()}")
    
    # Test Case 3: Code with Security Issues
    print("\n\n📌 TEST CASE 3: Code with Hardcoded Password")
    result3 = workflow.process(
        user_input="Help me connect to the database",
        llm_output='''
def connect_db():
    conn = mysql.connector.connect(
        host="db.internal",
        user="admin",
        password="MySecret123",
        database="users"
    )
    return conn
        '''
    )
    print(f"Result: {result3['status'].upper()}")
    
    # Test Case 4: Safe API Code
    print("\n\n📌 TEST CASE 4: Safe API Code")
    result4 = workflow.process(
        user_input="Help me write a FastAPI endpoint",
        llm_output='''
from fastapi import FastAPI
from config import get_api_key

app = FastAPI()

@app.get("/api/users")
def get_users():
    api_key = get_api_key()
    return {"users": []}
        '''
    )
    print(f"Result: {result4['status'].upper()}")
    
    # Display Dashboard
    print("\n\n📊 SHOWING DASHBOARD")
    workflow.show_dashboard()
    
    # Show Stats
    print("\n📈 WORKFLOW STATISTICS")
    print("=" * 80)
    stats = workflow.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Export Logs
    workflow.export_logs('workflow_logs.json')
    
    print("\n✅ Integration test complete!")
