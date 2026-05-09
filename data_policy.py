"""
Data Policy Engine
===================
Controls what data can be shared with external partners.
- PUBLIC: share freely
- PII: share only hashed/encrypted (GDPR)
- COMPANY_SECRET: never share externally (local LLM only)

Author: CONSAT PoC Team
Date: May 6, 2026
"""

import hashlib
import json
import base64
import os
from typing import Any, Dict, List, Optional
import audit_log

# Demo AES key (in production, use proper key management)
_DEMO_KEY = b"CONSAT_DEMO_KEY_2026_STOCKHOLM!!"  # 32 bytes for AES-256

# ============== Policy Table ==============
POLICY_TABLE = {
    "bus_routes": {
        "route_id":      {"classification": "PUBLIC", "action": "pass"},
        "line_number":   {"classification": "PUBLIC", "action": "pass"},
        "line_name":     {"classification": "PUBLIC", "action": "pass"},
        "operator":      {"classification": "PUBLIC", "action": "pass"},
        "region":        {"classification": "PUBLIC", "action": "pass"},
        "frequency_min": {"classification": "PUBLIC", "action": "pass"},
        "total_stops":   {"classification": "PUBLIC", "action": "pass"},
    },
    "bus_vehicles": {
        "vehicle_id":            {"classification": "PUBLIC",         "action": "pass"},
        "registration_plate":    {"classification": "PII",            "action": "encrypt"},  # encrypt: plate links directly to a legal entity
        "vehicle_type":          {"classification": "PUBLIC",         "action": "pass"},
        "capacity":              {"classification": "PUBLIC",         "action": "pass"},
        "iot_device_id":         {"classification": "COMPANY_SECRET", "action": "redact"},
        "firmware_version":      {"classification": "COMPANY_SECRET", "action": "redact"},
        "last_maintenance_date": {"classification": "PUBLIC",         "action": "pass"},
        "assigned_route":        {"classification": "PUBLIC",         "action": "pass"},
        "status":                {"classification": "PUBLIC",         "action": "pass"},
    },
    "drivers": {
        "driver_id":              {"classification": "PUBLIC",         "action": "pass"},   # internal reference ID, not personal data by itself
        "full_name":              {"classification": "PII",            "action": "hash"},
        "personal_number":        {"classification": "PII",            "action": "encrypt"},
        "phone":                  {"classification": "PII",            "action": "hash"},
        "email":                  {"classification": "PII",            "action": "hash"},
        "license_number":         {"classification": "PII",            "action": "encrypt"},
        "eco_drive_score":        {"classification": "COMPANY_SECRET", "action": "redact"},
        "training_certification": {"classification": "COMPANY_SECRET", "action": "redact"},
        "assigned_vehicle":       {"classification": "PUBLIC",         "action": "pass"},
    },
    "iot_sensor_readings": {
        "reading_id":                {"classification": "PUBLIC",         "action": "pass"},
        "vehicle_id":                {"classification": "PUBLIC",         "action": "pass"},
        "route_id":                  {"classification": "PUBLIC",         "action": "pass"},
        "timestamp":                 {"classification": "PUBLIC",         "action": "pass"},
        "latitude":                  {"classification": "PII",            "action": "hash"},   # precise GPS + driver_id = location tracking of individuals (GDPR)
        "longitude":                 {"classification": "PII",            "action": "hash"},
        "heading_deg":               {"classification": "PUBLIC",         "action": "pass"},
        "speed_kmh":                 {"classification": "PUBLIC",         "action": "pass"},
        "passenger_count":           {"classification": "PUBLIC",         "action": "pass"},
        "door_events":               {"classification": "PUBLIC",         "action": "pass"},
        "delay_minutes":             {"classification": "PUBLIC",         "action": "pass"},
        "ac_status":                 {"classification": "PUBLIC",         "action": "pass"},
        "fuel_consumption_l_per_km": {"classification": "COMPANY_SECRET", "action": "redact"},
        "battery_level_pct":         {"classification": "COMPANY_SECRET", "action": "redact"},
        "engine_temp_celsius":       {"classification": "COMPANY_SECRET", "action": "redact"},
        "brake_wear_pct":            {"classification": "COMPANY_SECRET", "action": "redact"},
        "tire_pressure_bar":         {"classification": "COMPANY_SECRET", "action": "redact"},
        "driver_id":                 {"classification": "PII",            "action": "hash"},
    },
    "bus_stops": {
        "stop_id":               {"classification": "PUBLIC", "action": "pass"},
        "stop_name":             {"classification": "PUBLIC", "action": "pass"},
        "latitude":              {"classification": "PUBLIC", "action": "pass"},   # fixed stop coords are public (not personal)
        "longitude":             {"classification": "PUBLIC", "action": "pass"},
        "route_ids":             {"classification": "PUBLIC", "action": "pass"},
        "has_shelter":           {"classification": "PUBLIC", "action": "pass"},
        "wheelchair_accessible": {"classification": "PUBLIC", "action": "pass"},
        "real_time_board":       {"classification": "PUBLIC", "action": "pass"},
    },
    "maintenance_logs": {
        "log_id":               {"classification": "PUBLIC",         "action": "pass"},
        "vehicle_id":           {"classification": "PUBLIC",         "action": "pass"},
        "date":                 {"classification": "PUBLIC",         "action": "pass"},
        "maintenance_type":     {"classification": "PUBLIC",         "action": "pass"},
        "technician_id":        {"classification": "PII",            "action": "hash"},   # person identifier — was wrongly SECRET
        "technician_name":      {"classification": "PII",            "action": "hash"},
        "cost_sek":             {"classification": "COMPANY_SECRET", "action": "redact"},
        "parts_replaced":       {"classification": "COMPANY_SECRET", "action": "redact"},
        "firmware_updated_to":  {"classification": "COMPANY_SECRET", "action": "redact"},
        "duration_hours":       {"classification": "PUBLIC",         "action": "pass"},
        "internal_notes":       {"classification": "COMPANY_SECRET", "action": "redact"},
    },
    "driver_shifts": {
        "shift_id":        {"classification": "PUBLIC",         "action": "pass"},
        "driver_id":       {"classification": "PII",            "action": "hash"},
        "vehicle_id":      {"classification": "PUBLIC",         "action": "pass"},
        "route_id":        {"classification": "PUBLIC",         "action": "pass"},
        "shift_date":      {"classification": "PUBLIC",         "action": "pass"},
        "start_time":      {"classification": "PUBLIC",         "action": "pass"},   # schedule data, not personal
        "end_time":        {"classification": "PUBLIC",         "action": "pass"},
        "depot":           {"classification": "PUBLIC",         "action": "pass"},   # operational facility, not a secret
        "break_location":  {"classification": "PII",            "action": "hash"},   # tracks personal movement
        "overtime_hours":  {"classification": "COMPANY_SECRET", "action": "redact"},
    },
    "incidents": {
        "incident_id":           {"classification": "PUBLIC",         "action": "pass"},
        "type":                  {"classification": "PUBLIC",         "action": "pass"},
        "severity":              {"classification": "PUBLIC",         "action": "pass"},
        "vehicle_id":            {"classification": "PUBLIC",         "action": "pass"},
        "driver_id":             {"classification": "PII",            "action": "hash"},
        "route_id":              {"classification": "PUBLIC",         "action": "pass"},
        "timestamp":             {"classification": "PUBLIC",         "action": "pass"},
        "latitude":              {"classification": "PII",            "action": "hash"},   # incident location tied to driver
        "longitude":             {"classification": "PII",            "action": "hash"},
        "description":           {"classification": "COMPANY_SECRET", "action": "redact"},
        "status":                {"classification": "PUBLIC",         "action": "pass"},
        "reported_to_authority": {"classification": "PUBLIC",         "action": "pass"},
    },
}

# Keywords that indicate queries touching sensitive data
SECRET_KEYWORDS = [
    # eco / performance scores (proprietary algorithm output)
    "eco_drive", "eco-drive", "ecodrive", "eco score", "eco-score", "eco drive score",
    "fuel_consumption", "fuel consumption", "fuel efficiency",
    # vehicle health telemetry
    "brake_wear", "brake wear", "engine_temp", "engine temperature",
    "battery_level", "tire_pressure",
    # CONSAT proprietary systems
    "firmware", "iot_device_id", "consat-iot", "consat_iot",
    "training_certification", "consat-cert",
    # financial / commercial
    "cost_sek", "maintenance cost", "internal cost", "salary", "wage",
    "pay", "compensation", "lön", "overtime",
    # supply chain & internal docs
    "parts_replaced", "internal_notes", "internal notes",
    "incident description",
    "proprietary", "confidential",
]

PII_KEYWORDS = [
    # field name variants
    "driver_name", "full_name", "personal_number", "personnummer",
    "license_number", "registration_plate", "technician_name", "technician_id",
    "break_location",
    # natural-language variants
    "personal number", "full name", "license number", "driver name",
    "driver phone", "driver email", "driver id",
    "registration plate", "phone number", "phone", "email",
    "who is driving", "driver schedule", "shift",
    # location tracking (GPS linked to a person = PII under GDPR)
    "latitude", "longitude", "gps", "coordinates", "location of driver",
    "driver location", "vehicle location",
    # Swedish
    "personnummer", "körkort",
]


# ============== Transform Functions ==============

def hash_value(value: Any, salt: str = "CONSAT_SALT_2026") -> str:
    """SHA-256 hash with Consat salt. One-way — cannot be reversed."""
    raw = f"{salt}:{value}"
    return f"HASH:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def encrypt_value(value: Any) -> str:
    """Simple base64 encoding for PoC demo (in production, use AES-256)."""
    raw = str(value).encode("utf-8")
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"ENC:{encoded}"


def decrypt_value(encrypted: str) -> str:
    """Reverse of encrypt_value for PoC."""
    if encrypted.startswith("ENC:"):
        encoded = encrypted[4:]
        return base64.b64decode(encoded).decode("utf-8")
    return encrypted


def redact_value(field_name: str) -> str:
    """Replace company secret with redaction marker."""
    return f"[REDACTED:{field_name.upper()}]"


# ============== Core Policy Functions ==============

def get_field_policy(table_name: str, field_name: str) -> Dict:
    """Get the classification and action for a specific field."""
    table_policy = POLICY_TABLE.get(table_name, {})
    return table_policy.get(field_name, {"classification": "PUBLIC", "action": "pass"})


def apply_field_policy(table_name: str, field_name: str, value: Any) -> Any:
    """Apply policy transformation to a single field value."""
    policy = get_field_policy(table_name, field_name)
    action = policy["action"]

    if action == "pass":
        return value
    elif action == "hash":
        return hash_value(value)
    elif action == "encrypt":
        return encrypt_value(value)
    elif action == "redact":
        return redact_value(field_name)
    return value


def filter_record_for_external(table_name: str, record: Dict) -> Dict:
    """Apply policy to a single record for external sharing."""
    filtered = {}
    for field, value in record.items():
        filtered[field] = apply_field_policy(table_name, field, value)
    return filtered


def filter_for_external(table_name: str, records: List[Dict]) -> List[Dict]:
    """Apply policy to a list of records for external partner sharing."""
    return [filter_record_for_external(table_name, r) for r in records]


def classify_query(query_text: str, trace_id: str = "") -> Dict:
    """Analyze a natural-language query to determine if it touches sensitive data."""
    query_lower = query_text.lower()

    touches_secret = any(kw in query_lower for kw in SECRET_KEYWORDS)
    touches_pii = any(kw in query_lower for kw in PII_KEYWORDS)

    if touches_secret:
        classification = "COMPANY_SECRET"
        recommendation = "Route to LOCAL LLM only. Do NOT share externally."
    elif touches_pii:
        classification = "PII"
        recommendation = "Apply hash/encrypt before sharing externally."
    else:
        classification = "PUBLIC"
        recommendation = "Safe to share with external partners."

    result = {
        "query": query_text,
        "classification": classification,
        "touches_pii": touches_pii,
        "touches_secret": touches_secret,
        "recommendation": recommendation,
        "matched_keywords": [
            kw for kw in (SECRET_KEYWORDS + PII_KEYWORDS)
            if kw in query_lower
        ],
    }
    audit_log.log_query_classification(query_text, classification, recommendation, trace_id=trace_id)
    return result


def get_table_policy_summary(table_name: str) -> Dict:
    """Get a summary of all field classifications for a table."""
    table = POLICY_TABLE.get(table_name, {})
    summary = {"public": [], "pii": [], "company_secret": []}
    for field, policy in table.items():
        cls = policy["classification"].lower().replace(" ", "_")
        if cls in summary:
            summary[cls].append({"field": field, "action": policy["action"]})
    return summary


def get_full_policy_summary() -> Dict:
    """Get the complete policy for all tables."""
    return {table: get_table_policy_summary(table) for table in POLICY_TABLE}


# ============== Standalone Demo ==============

if __name__ == "__main__":
    from stockholm_bus_data import DRIVERS, IOT_SENSOR_READINGS, BUS_VEHICLES

    print("=" * 70)
    print("DATA POLICY ENGINE - DEMO")
    print("=" * 70)

    # Demo 1: Driver record before/after
    print("\n--- Driver Record: BEFORE policy ---")
    driver = DRIVERS[0]
    print(json.dumps(driver, indent=2, ensure_ascii=False))

    print("\n--- Driver Record: AFTER policy (external sharing) ---")
    filtered = filter_record_for_external("drivers", driver)
    print(json.dumps(filtered, indent=2, ensure_ascii=False))

    # Demo 2: IoT reading before/after
    print("\n--- IoT Reading: BEFORE policy ---")
    reading = IOT_SENSOR_READINGS[0]
    print(json.dumps(reading, indent=2, ensure_ascii=False))

    print("\n--- IoT Reading: AFTER policy (external sharing) ---")
    filtered_reading = filter_record_for_external("iot_sensor_readings", reading)
    print(json.dumps(filtered_reading, indent=2, ensure_ascii=False))

    # Demo 3: Query classification
    print("\n--- Query Classification ---")
    queries = [
        "Show me bus routes in Stockholm",
        "What is the driver phone number for line 172?",
        "Show eco-drive scores for all drivers",
    ]
    for q in queries:
        result = classify_query(q)
        print(f"\n  Query: \"{q}\"")
        print(f"  Classification: {result['classification']}")
        print(f"  Recommendation: {result['recommendation']}")

    # Demo 4: Full policy summary
    print("\n--- Policy Summary ---")
    summary = get_full_policy_summary()
    for table, fields in summary.items():
        pub = len(fields["public"])
        pii = len(fields["pii"])
        sec = len(fields["company_secret"])
        print(f"  {table}: {pub} public, {pii} PII, {sec} secret")

    print("\n✅ Policy engine ready!")
