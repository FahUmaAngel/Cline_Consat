"""
Schema-Aware Masker
====================
Scans any text / JSON blob for field names that appear in POLICY_TABLE and
applies the correct masking action (hash / encrypt / redact / pass)
*automatically* — no keywords or query text needed.

How it works:
  1. Try to parse the whole text as JSON.
  2. If that fails, extract embedded JSON objects/arrays using raw_decode.
  3. For each parsed structure, walk every key-value pair recursively.
  4. Infer which POLICY_TABLE table the record belongs to by fingerprinting
     its keys against known "signature" fields per table.
  5. Call data_policy.apply_field_policy() for every field.
  6. Reconstruct the text with masked values in-place.

Author: CONSAT PoC Team
Date:   May 2026
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import data_policy


# ---------------------------------------------------------------------------
# Table fingerprints
# ---------------------------------------------------------------------------
# For each table, a list of "signature" keys.  When a record shares ≥1 of
# these keys with a table, that table is considered a candidate; the table
# with the highest match count wins.
#
# Keys are ordered from most-unique to least-unique so that even a single
# match on the first entry gives a high confidence result.
# ---------------------------------------------------------------------------
TABLE_FINGERPRINTS: Dict[str, List[str]] = {
    "drivers": [
        "personal_number",        # uniquely identifies this table
        "license_number",
        "eco_drive_score",
        "training_certification",
        "full_name",
    ],
    "bus_vehicles": [
        "iot_device_id",          # uniquely identifies this table
        "firmware_version",
        "registration_plate",
        "vehicle_type",
        "capacity",
    ],
    "iot_sensor_readings": [
        "fuel_consumption_l_per_km",  # uniquely identifies this table
        "brake_wear_pct",
        "tire_pressure_bar",
        "engine_temp_celsius",
        "battery_level_pct",
        "speed_kmh",
        "heading_deg",
        "door_events",
        "delay_minutes",
    ],
    "maintenance_logs": [
        "cost_sek",               # uniquely identifies this table
        "parts_replaced",
        "internal_notes",
        "firmware_updated_to",
        "technician_id",
        "technician_name",
        "maintenance_type",
        "duration_hours",
    ],
    "driver_shifts": [
        "break_location",         # uniquely identifies this table
        "overtime_hours",
        "shift_date",
        "shift_id",
        "start_time",
        "end_time",
        "depot",
    ],
    "incidents": [
        "incident_id",            # uniquely identifies this table
        "reported_to_authority",
        "incident_type",
        "severity",
    ],
    "bus_routes": [
        "line_number",            # uniquely identifies this table
        "line_name",
        "frequency_min",
        "total_stops",
        "operator",
    ],
    "bus_stops": [
        "stop_name",              # uniquely identifies this table
        "has_shelter",
        "wheelchair_accessible",
        "real_time_board",
        "stop_id",
    ],
}


# ---------------------------------------------------------------------------
# Table inference
# ---------------------------------------------------------------------------

def infer_table_name(record_keys: List[str]) -> Optional[str]:
    """
    Infer which POLICY_TABLE table a record belongs to by counting how many
    fingerprint keys it shares with each table.  Returns the best-matching
    table name, or None if no match (0 shared fingerprint keys).

    Tie-breaking: the table with the highest fingerprint-key rank (i.e. whose
    first matching key appears earliest in TABLE_FINGERPRINTS[table]) wins,
    giving priority to more-unique signatures.
    """
    key_set = set(record_keys)
    best_table: Optional[str] = None
    best_score = 0
    best_rank = float("inf")   # lower = more unique key matched earlier

    for table, fingerprint_keys in TABLE_FINGERPRINTS.items():
        matched_indices = [
            i for i, k in enumerate(fingerprint_keys) if k in key_set
        ]
        if not matched_indices:
            continue
        score = len(matched_indices)
        rank = min(matched_indices)        # index of the most-unique key matched
        if score > best_score or (score == best_score and rank < best_rank):
            best_score = score
            best_rank = rank
            best_table = table

    return best_table if best_score >= 1 else None


# ---------------------------------------------------------------------------
# Record-level masking
# ---------------------------------------------------------------------------

def apply_policy_to_record(
    table_name: str,
    record: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict]]:
    """
    Apply POLICY_TABLE rules to every field in a record dict.

    Returns:
        masked_record  – dict with sensitive values replaced
        masking_events – list of {"field", "table", "action", "classification"}
    """
    masked: Dict[str, Any] = {}
    events: List[Dict] = []

    for field, value in record.items():
        policy = data_policy.get_field_policy(table_name, field)
        action = policy.get("action", "pass")
        classification = policy.get("classification", "PUBLIC")

        if action == "pass":
            masked[field] = value

        elif action == "hash":
            masked[field] = data_policy.hash_value(value)
            events.append({
                "field": field,
                "table": table_name,
                "action": "hash",
                "classification": classification,
            })

        elif action == "encrypt":
            masked[field] = data_policy.encrypt_value(value)
            events.append({
                "field": field,
                "table": table_name,
                "action": "encrypt",
                "classification": classification,
            })

        elif action == "redact":
            masked[field] = data_policy.redact_value(field)
            events.append({
                "field": field,
                "table": table_name,
                "action": "redact",
                "classification": classification,
            })

        else:
            masked[field] = value   # unknown action → safe pass-through

    return masked, events


# ---------------------------------------------------------------------------
# Recursive object walker
# ---------------------------------------------------------------------------

def _mask_object(
    obj: Any,
    parent_table: Optional[str] = None,
) -> Tuple[Any, List[Dict]]:
    """
    Recursively walk a parsed JSON structure and apply policy masking.

    - dicts  → infer table, apply per-field policy, recurse into nested values
    - lists  → recurse into each element
    - scalars → return as-is (scalars are only masked at the dict-field level)

    Returns (masked_obj, all_masking_events).
    """
    all_events: List[Dict] = []

    if isinstance(obj, dict):
        # Try to identify which table this dict belongs to
        table = infer_table_name(list(obj.keys())) or parent_table

        if table and table in data_policy.POLICY_TABLE:
            # Apply field-level policy
            masked_record, events = apply_policy_to_record(table, obj)
            all_events.extend(events)

            # Recurse into any nested dicts/lists that survived masking
            final: Dict[str, Any] = {}
            for k, v in masked_record.items():
                if isinstance(v, (dict, list)):
                    v, sub_events = _mask_object(v, table)
                    all_events.extend(sub_events)
                final[k] = v
            return final, all_events

        else:
            # No table match — recurse into children anyway (might be a
            # wrapper dict like {"filtered_results": {...}})
            result: Dict[str, Any] = {}
            for k, v in obj.items():
                v, sub_events = _mask_object(v, parent_table)
                all_events.extend(sub_events)
                result[k] = v
            return result, all_events

    elif isinstance(obj, list):
        result_list = []
        for item in obj:
            item, sub_events = _mask_object(item, parent_table)
            all_events.extend(sub_events)
            result_list.append(item)
        return result_list, all_events

    else:
        # Scalar (str, int, float, bool, None) — no field-name context here
        return obj, []


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json_blocks(text: str) -> List[Tuple[int, int, Any]]:
    """
    Scan `text` for valid JSON objects or arrays using json.JSONDecoder's
    raw_decode() so we don't need a regex.

    Returns a list of (start_index, end_index, parsed_object) tuples,
    where end_index is the character position immediately after the block.
    """
    decoder = json.JSONDecoder()
    results: List[Tuple[int, int, Any]] = []
    i = 0
    while i < len(text):
        # raw_decode only starts from a real JSON token
        if text[i] not in ('{', '['):
            i += 1
            continue
        try:
            obj, rel_end = decoder.raw_decode(text, i)
            abs_end = i + rel_end
            results.append((i, abs_end, obj))
            i = abs_end          # jump past this block
        except json.JSONDecodeError:
            i += 1
    return results


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def scan_and_mask(text: str) -> Tuple[str, Dict]:
    """
    Main entry point.  Given any text (free-form or JSON), apply schema-aware
    policy masking to every JSON structure found inside it.

    Strategy:
      1. Try to parse the entire text as JSON (fast path).
      2. If that fails, extract all embedded JSON blocks from the text and
         replace them in-place with their masked equivalents.
      3. For each parsed structure, recurse with _mask_object().

    Returns:
        masked_text  – text with sensitive field values replaced
        report       – {
            "fields_masked": int,
            "tables_detected": [str, ...],
            "events": [{field, table, action, classification}, ...],
            "by_action": {"hash": [...], "encrypt": [...], "redact": [...]},
        }
    """
    all_events: List[Dict] = []

    # ── Fast path: whole text is JSON ───────────────────────────────────────
    try:
        parsed = json.loads(text)
        masked_obj, all_events = _mask_object(parsed)
        masked_text = json.dumps(masked_obj, ensure_ascii=False, indent=2)

    # ── Fallback: scan for embedded JSON blocks ──────────────────────────────
    except (json.JSONDecodeError, ValueError):
        blocks = _extract_json_blocks(text)
        if not blocks:
            # No JSON found at all — return text unchanged, empty report
            return text, _build_report([])

        # Rebuild text by replacing each JSON block with its masked version
        parts: List[str] = []
        cursor = 0
        for start, end, parsed_block in blocks:
            parts.append(text[cursor:start])       # text before this block
            masked_block, events = _mask_object(parsed_block)
            all_events.extend(events)
            parts.append(json.dumps(masked_block, ensure_ascii=False))
            cursor = end
        parts.append(text[cursor:])                # text after last block
        masked_text = "".join(parts)

    return masked_text, _build_report(all_events)


def _build_report(events: List[Dict]) -> Dict:
    """Summarise masking events into a structured report."""
    return {
        "fields_masked": len(events),
        "tables_detected": sorted({e["table"] for e in events}),
        "events": events,
        "by_action": {
            "hash":    [e["field"] for e in events if e["action"] == "hash"],
            "encrypt": [e["field"] for e in events if e["action"] == "encrypt"],
            "redact":  [e["field"] for e in events if e["action"] == "redact"],
        },
    }


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    print("=" * 70)
    print("SCHEMA-AWARE MASKER — SELF TEST")
    print("=" * 70)

    # Test 1: Driver record
    driver = {
        "driver_id": "DRV-1001",
        "full_name": "Lars Eriksson",
        "personal_number": "19850412-3456",
        "phone": "+46 70 123 4567",
        "email": "lars.eriksson@keolis.se",
        "license_number": "SE-DL-2024-78341",
        "eco_drive_score": 87.3,
        "training_certification": "CONSAT-CERT-ADV",
        "assigned_vehicle": "VH-4522",
    }
    print("\n[Test 1] Driver record")
    masked, report = scan_and_mask(json.dumps(driver))
    print(f"  Fields masked : {report['fields_masked']}")
    print(f"  Hashed        : {report['by_action']['hash']}")
    print(f"  Encrypted     : {report['by_action']['encrypt']}")
    print(f"  Redacted      : {report['by_action']['redact']}")
    print(f"  Masked JSON   : {masked}")

    # Test 2: IoT reading
    reading = {
        "reading_id": "RD-20260506-0001",
        "vehicle_id": "VH-4521",
        "route_id": "BUS-006",
        "timestamp": "2026-05-06T06:14:00+02:00",
        "latitude": 59.34812,
        "longitude": 18.09412,
        "speed_kmh": 34.2,
        "fuel_consumption_l_per_km": 0.38,
        "brake_wear_pct": 72.1,
        "tire_pressure_bar": 7.9,
        "driver_id": "DRV-1003",
    }
    print("\n[Test 2] IoT sensor reading")
    masked, report = scan_and_mask(json.dumps(reading))
    print(f"  Fields masked : {report['fields_masked']}")
    print(f"  Redacted      : {report['by_action']['redact']}")
    print(f"  Hashed        : {report['by_action']['hash']}")

    # Test 3: Maintenance log
    log = {
        "log_id": "MNT-0001",
        "vehicle_id": "VH-4521",
        "date": "2026-04-15",
        "maintenance_type": "scheduled",
        "technician_id": "TECH-201",
        "technician_name": "Björn Lindström",
        "cost_sek": 4200,
        "parts_replaced": ["brake pads front", "air filter"],
        "duration_hours": 3.5,
        "internal_notes": "Brake wear was at 82%.",
    }
    print("\n[Test 3] Maintenance log")
    masked, report = scan_and_mask(json.dumps(log))
    print(f"  Fields masked : {report['fields_masked']}")
    print(f"  Redacted      : {report['by_action']['redact']}")
    print(f"  Hashed        : {report['by_action']['hash']}")

    # Test 4: Embedded JSON inside free text
    text_with_json = (
        'Here is the driver info: {"driver_id": "DRV-1002", "full_name": "Anna Lindqvist", '
        '"personal_number": "19900815-7823", "eco_drive_score": 92.1} — handle with care.'
    )
    print("\n[Test 4] Embedded JSON in free text")
    masked, report = scan_and_mask(text_with_json)
    print(f"  Fields masked : {report['fields_masked']}")
    print(f"  Masked text   : {masked}")

    # Test 5: Ambiguous field — vehicle_id alone should stay PUBLIC
    ambiguous = {"vehicle_id": "VH-4521", "status": "in_service"}
    print("\n[Test 5] Ambiguous record (no fingerprint keys)")
    masked, report = scan_and_mask(json.dumps(ambiguous))
    print(f"  Fields masked : {report['fields_masked']}  (expected 0)")
    print(f"  Masked JSON   : {masked}")

    print("\n✅ Schema-aware masker self-test complete!")
