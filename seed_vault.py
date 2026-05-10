"""
Seed the File Vault with realistic demo files for each tier.
All filenames relate to the Stockholm Bus IoT / CONSAT project.

Usage:  python3 seed_vault.py
"""

import file_vault

# Clear existing files first so we start fresh
for f in list(file_vault._manifest):
    file_vault.delete_file(f["file_id"])

# ─── PUBLIC files ──────────────────────────────────────────────
public_files = [
    ("stockholm_bus_routes_2026.csv",
     "route_id,line_number,line_name,operator,region\n"
     "R001,172,Ropsten-Gustavsberg,Keolis,Nacka\n"
     "R002,4,Radiohuset-Gullmarsplan,SL,Stockholm\n"
     "R003,69,Blockhusudden-Sergels Torg,SL,Stockholm\n",
     ["routes", "open-data"], "Published bus route schedule — fully public"),

    ("bus_stop_locations.json",
     '[\n  {"stop_id": "S001", "name": "T-Centralen", "lat": 59.3313, "lng": 18.0590},\n'
     '  {"stop_id": "S002", "name": "Slussen", "lat": 59.3198, "lng": 18.0720},\n'
     '  {"stop_id": "S003", "name": "Gullmarsplan", "lat": 59.2986, "lng": 18.0811}\n]\n',
     ["stops", "geo"], "Stop coordinates from Trafikverket open data"),

    ("fleet_vehicle_types.pdf",
     "CONSAT Fleet Overview 2026\n========================\n"
     "Volvo 7900 Electric — 42 seats — 12m\n"
     "Scania Citywide LFA — 38 seats — 18m articulated\n"
     "BYD K9 — 29 seats — battery electric\n",
     ["fleet", "specifications"], "Vehicle model specifications — non-sensitive"),

    ("passenger_count_monthly_summary.csv",
     "month,route,total_passengers,avg_daily\n"
     "2026-01,172,182400,5880\n2026-02,172,171200,6114\n"
     "2026-03,4,245000,7903\n2026-04,69,198700,6623\n",
     ["analytics", "ridership"], "Aggregated ridership stats — no personal data"),

    ("consat_gateway_api_docs.md",
     "# CONSAT Secure AI Gateway — Public API\n\n"
     "## Endpoints\n- `GET /api/bus-data` — Fetch bus data tables\n"
     "- `GET /api/policy` — View data classification policy\n"
     "- `POST /api/simulate` — Run agentic workflow simulation\n",
     ["api", "documentation"], "Public-facing API documentation"),

    ("quarterly_service_report_Q1_2026.pdf",
     "CONSAT Quarterly Service Report — Q1 2026\n"
     "On-time performance: 94.2%\nFleet availability: 97.8%\n"
     "Total km driven: 1,284,000 km\nPassenger satisfaction: 4.3/5\n",
     ["report", "quarterly"], "Published quarterly performance report"),
]

# ─── PII files ─────────────────────────────────────────────────
pii_files = [
    ("driver_roster_may_2026.xlsx",
     "driver_id,full_name,assigned_vehicle,assigned_route\n"
     "D001,Erik Lindström,V-1042,R001\n"
     "D002,Anna Johansson,V-1018,R002\n"
     "D003,Mohamed Hassan,V-1035,R003\n",
     ["drivers", "roster", "GDPR"], "Driver names linked to assignments — contains PII"),

    ("vehicle_registration_plates.csv",
     "vehicle_id,registration_plate,owner_entity\n"
     "V-1042,ABC 123,Keolis Sverige AB\n"
     "V-1018,DEF 456,Stockholms Lokaltrafik\n",
     ["vehicles", "registration"], "License plates link to legal entities — PII under GDPR"),

    ("iot_gps_traces_route172_20260501.json",
     '{"traces": [\n'
     '  {"driver_id": "D001", "lat": 59.3573, "lng": 18.1048, "ts": "08:14:22"},\n'
     '  {"driver_id": "D001", "lat": 59.3421, "lng": 18.0872, "ts": "08:22:05"}\n'
     ']}\n',
     ["GPS", "tracking", "GDPR"], "Real-time GPS linked to driver IDs — location tracking = PII"),

    ("technician_service_logs.csv",
     "log_id,date,vehicle_id,technician_name,technician_id,maintenance_type\n"
     "ML-001,2026-04-15,V-1042,Lars Svensson,T-201,brake_inspection\n"
     "ML-002,2026-04-18,V-1018,Fatima Al-Said,T-204,battery_check\n",
     ["maintenance", "technicians"], "Technician names and IDs — personal data"),

    ("driver_shift_break_locations.csv",
     "shift_id,driver_id,break_location,break_start,break_end\n"
     "SH-101,D001,Gustavsberg Depot,12:00,12:30\n"
     "SH-102,D002,Hornstull Café,11:45,12:15\n",
     ["shifts", "breaks", "location"], "Driver break locations track personal movement — PII"),
]

# ─── SPII files ────────────────────────────────────────────────
spii_files = [
    ("driver_personal_numbers.csv",
     "driver_id,full_name,personal_number,date_of_birth\n"
     "D001,Erik Lindström,19850315-XXXX,1985-03-15\n"
     "D002,Anna Johansson,19900722-XXXX,1990-07-22\n",
     ["personnummer", "sensitive-PII"], "Swedish personal numbers (personnummer) — highest PII sensitivity"),

    ("employee_contact_directory.xlsx",
     "employee_id,name,phone,email,home_address\n"
     "D001,Erik Lindström,+46701234567,erik@consat.se,Storgatan 12 Stockholm\n"
     "D003,Mohamed Hassan,+46709876543,mohamed@consat.se,Drottninggatan 45\n",
     ["contacts", "phone", "email"], "Full contact info including home addresses — sensitive PII"),

    ("driver_license_scans_batch12.pdf",
     "[BINARY — Scanned driver license images]\n"
     "Contains: photo ID, license number, personal number\n"
     "Drivers: D001, D002, D003, D005\n",
     ["biometric", "license", "scans"], "Scanned driver licenses with photos — biometric + SPII"),

    ("health_certificates_drivers_2026.pdf",
     "[BINARY — Medical fitness certificates]\n"
     "Driver D001 — Fit for duty, valid until 2027-03\n"
     "Driver D002 — Fit with conditions, valid until 2026-12\n",
     ["medical", "health", "certificates"], "Medical fitness records — health data is SPII"),
]

# ─── SECRET files ──────────────────────────────────────────────
secret_files = [
    ("eco_drive_scores_all_drivers_Q1.csv",
     "driver_id,eco_score,fuel_efficiency_index,hard_braking_events,smooth_acceleration_pct\n"
     "D001,87.4,0.92,3,94.1\n"
     "D002,91.2,0.97,1,96.8\n"
     "D003,78.9,0.84,7,88.3\n",
     ["eco-drive", "proprietary", "algorithm"], "Proprietary eco-drive algorithm output — CONSAT trade secret"),

    ("fleet_maintenance_costs_2026.xlsx",
     "vehicle_id,date,maintenance_type,cost_sek,parts_replaced,internal_notes\n"
     "V-1042,2026-03-12,engine_overhaul,148500,turbo+injectors,warranty dispute pending\n"
     "V-1018,2026-04-01,battery_replacement,285000,Li-ion 120kWh pack,supplier: CATL\n",
     ["costs", "financial", "confidential"], "Internal maintenance costs and supplier details"),

    ("firmware_iot_device_registry.json",
     '{\n  "devices": [\n'
     '    {"iot_device_id": "CONSAT-IOT-2024-0421", "firmware": "v3.8.2-beta", "vehicle": "V-1042"},\n'
     '    {"iot_device_id": "CONSAT-IOT-2024-0388", "firmware": "v3.7.1", "vehicle": "V-1018"}\n'
     '  ]\n}\n',
     ["firmware", "IoT", "device-registry"], "IoT device IDs and firmware versions — CONSAT proprietary"),

    ("incident_investigation_report_INC042.pdf",
     "INCIDENT REPORT — INC-042\nDate: 2026-04-22\nSeverity: HIGH\n"
     "Vehicle: V-1042, Route: 172\n"
     "Description: Brake system malfunction at Slussen junction.\n"
     "Root cause: Firmware v3.8.2-beta regression in ABS module.\n"
     "Action: Emergency patch deployed, all v3.8.2-beta devices recalled.\n",
     ["incident", "investigation", "confidential"], "Internal incident investigation with root cause — company secret"),

    ("consat_ai_routing_model_weights.bin",
     "[BINARY — PyTorch model checkpoint]\n"
     "Model: CONSAT-SensitivityRouter v2.1\n"
     "Accuracy: 97.3% on validation set\n"
     "Parameters: 12.4M\n",
     ["AI", "model", "proprietary"], "Trained sensitivity router model weights — core IP"),

    ("budget_forecast_2026_2027.xlsx",
     "category,2026_actual_sek,2027_forecast_sek,variance_pct\n"
     "fleet_maintenance,12400000,13800000,+11.3\n"
     "iot_infrastructure,8200000,9500000,+15.8\n"
     "driver_training,3100000,3400000,+9.7\n"
     "ai_development,5600000,7200000,+28.6\n",
     ["budget", "forecast", "financial"], "Multi-year financial forecast — highly confidential"),
]

# ─── Upload everything ─────────────────────────────────────────
count = 0
for filename, content, tags, desc in public_files:
    file_vault.add_file(filename, content.encode("utf-8"), tier="PUBLIC", tags=tags, description=desc)
    count += 1

for filename, content, tags, desc in pii_files:
    file_vault.add_file(filename, content.encode("utf-8"), tier="PII", tags=tags, description=desc)
    count += 1

for filename, content, tags, desc in spii_files:
    file_vault.add_file(filename, content.encode("utf-8"), tier="SPII", tags=tags, description=desc)
    count += 1

for filename, content, tags, desc in secret_files:
    file_vault.add_file(filename, content.encode("utf-8"), tier="SECRET", tags=tags, description=desc)
    count += 1

stats = file_vault.get_vault_stats()
print(f"\n✅ Seeded {count} demo files into the vault:")
for tier, info in stats["by_tier"].items():
    print(f"   {tier:12s}  {info['count']} files  ({info['size_bytes']:,} bytes)")
print(f"\n   Total: {stats['total_files']} files, {stats['total_size_bytes']:,} bytes")
