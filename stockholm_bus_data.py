"""
Stockholm Bus Route Mock Database
==================================
Mock IoT sensor data for Stockholm bus routes with PII driver data.
Used to demonstrate Consat MCP policy-based data sharing.

Author: CONSAT PoC Team
Date: May 6, 2026
"""

from datetime import datetime, timedelta
import random
import json

# ============== Table 1: Bus Routes ==============
BUS_ROUTES = [
    {"route_id": "BUS-001", "line_number": 1, "line_name": "Stora Essingen - Frihamnen", "operator": "Keolis", "region": "Stockholm kommun"},
    {"route_id": "BUS-002", "line_number": 2, "line_name": "Norrtull - Sofia", "operator": "Keolis", "region": "Stockholm kommun"},
    {"route_id": "BUS-003", "line_number": 3, "line_name": "Södersjukhuset - Karolinska", "operator": "Nobina", "region": "Stockholm kommun"},
    {"route_id": "BUS-004", "line_number": 4, "line_name": "Gullmarsplan - Radiohuset", "operator": "Nobina", "region": "Stockholm kommun"},
    {"route_id": "BUS-005", "line_number": 69, "line_name": "Blockhusudden - Sergels torg", "operator": "Keolis", "region": "Stockholm kommun"},
    {"route_id": "BUS-006", "line_number": 172, "line_name": "Ropsten - Sickla köpkvarter", "operator": "Nobina", "region": "Stockholm kommun"},
    {"route_id": "BUS-007", "line_number": 178, "line_name": "Mörby station - Danderyds sjukhus", "operator": "Keolis", "region": "Danderyd"},
    {"route_id": "BUS-008", "line_number": 401, "line_name": "Cityterminalen - Kista", "operator": "Nobina", "region": "Stockholm kommun"},
]

# ============== Table 2: Bus Vehicles ==============
BUS_VEHICLES = [
    {"vehicle_id": "VH-4521", "registration_plate": "ABC 123", "iot_device_id": "CONSAT-IOT-9832", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-15", "assigned_route": "BUS-006"},
    {"vehicle_id": "VH-4522", "registration_plate": "DEF 456", "iot_device_id": "CONSAT-IOT-9833", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-20", "assigned_route": "BUS-001"},
    {"vehicle_id": "VH-4523", "registration_plate": "GHI 789", "iot_device_id": "CONSAT-IOT-9834", "firmware_version": "v3.1.8", "last_maintenance_date": "2026-03-28", "assigned_route": "BUS-002"},
    {"vehicle_id": "VH-4524", "registration_plate": "JKL 012", "iot_device_id": "CONSAT-IOT-9835", "firmware_version": "v3.2.0", "last_maintenance_date": "2026-04-10", "assigned_route": "BUS-003"},
    {"vehicle_id": "VH-4525", "registration_plate": "MNO 345", "iot_device_id": "CONSAT-IOT-9836", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-25", "assigned_route": "BUS-005"},
    {"vehicle_id": "VH-4526", "registration_plate": "PQR 678", "iot_device_id": "CONSAT-IOT-9837", "firmware_version": "v3.1.8", "last_maintenance_date": "2026-04-01", "assigned_route": "BUS-004"},
    {"vehicle_id": "VH-4527", "registration_plate": "STU 901", "iot_device_id": "CONSAT-IOT-9838", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-18", "assigned_route": "BUS-008"},
    {"vehicle_id": "VH-4528", "registration_plate": "VWX 234", "iot_device_id": "CONSAT-IOT-9839", "firmware_version": "v3.2.0", "last_maintenance_date": "2026-04-22", "assigned_route": "BUS-007"},
]

# ============== Table 3: Drivers (PII-heavy) ==============
DRIVERS = [
    {"driver_id": "DRV-1001", "full_name": "Lars Eriksson", "personal_number": "19850412-3456", "phone": "+46 70 123 4567", "email": "lars.eriksson@keolis.se", "license_number": "SE-DL-2024-78341", "eco_drive_score": 87.3, "training_certification": "CONSAT-CERT-ADV", "assigned_vehicle": "VH-4522"},
    {"driver_id": "DRV-1002", "full_name": "Anna Lindqvist", "personal_number": "19900815-7823", "phone": "+46 73 234 5678", "email": "anna.lindqvist@nobina.se", "license_number": "SE-DL-2023-56219", "eco_drive_score": 92.1, "training_certification": "CONSAT-CERT-ADV", "assigned_vehicle": "VH-4524"},
    {"driver_id": "DRV-1003", "full_name": "Erik Johansson", "personal_number": "19780623-1245", "phone": "+46 76 345 6789", "email": "erik.johansson@keolis.se", "license_number": "SE-DL-2022-33456", "eco_drive_score": 78.5, "training_certification": "CONSAT-CERT-STD", "assigned_vehicle": "VH-4521"},
    {"driver_id": "DRV-1004", "full_name": "Maria Svensson", "personal_number": "19950307-9012", "phone": "+46 70 456 7890", "email": "maria.svensson@nobina.se", "license_number": "SE-DL-2024-12098", "eco_drive_score": 95.0, "training_certification": "CONSAT-CERT-ADV", "assigned_vehicle": "VH-4526"},
    {"driver_id": "DRV-1005", "full_name": "Oscar Nilsson", "personal_number": "19880219-5678", "phone": "+46 72 567 8901", "email": "oscar.nilsson@keolis.se", "license_number": "SE-DL-2023-89012", "eco_drive_score": 81.7, "training_certification": "CONSAT-CERT-STD", "assigned_vehicle": "VH-4525"},
    {"driver_id": "DRV-1006", "full_name": "Sofia Andersson", "personal_number": "19920614-3421", "phone": "+46 70 678 9012", "email": "sofia.andersson@nobina.se", "license_number": "SE-DL-2024-45678", "eco_drive_score": 89.4, "training_certification": "CONSAT-CERT-ADV", "assigned_vehicle": "VH-4523"},
    {"driver_id": "DRV-1007", "full_name": "Karl Bergström", "personal_number": "19830901-8765", "phone": "+46 76 789 0123", "email": "karl.bergstrom@keolis.se", "license_number": "SE-DL-2022-67890", "eco_drive_score": 74.2, "training_certification": "CONSAT-CERT-STD", "assigned_vehicle": "VH-4528"},
    {"driver_id": "DRV-1008", "full_name": "Emma Pettersson", "personal_number": "19970428-2345", "phone": "+46 73 890 1234", "email": "emma.pettersson@nobina.se", "license_number": "SE-DL-2025-23456", "eco_drive_score": 91.8, "training_certification": "CONSAT-CERT-ADV", "assigned_vehicle": "VH-4527"},
    {"driver_id": "DRV-1009", "full_name": "Gustav Holm", "personal_number": "19860715-6789", "phone": "+46 70 901 2345", "email": "gustav.holm@keolis.se", "license_number": "SE-DL-2023-78901", "eco_drive_score": 83.6, "training_certification": "CONSAT-CERT-STD", "assigned_vehicle": "VH-4521"},
    {"driver_id": "DRV-1010", "full_name": "Maja Forsberg", "personal_number": "19910322-1098", "phone": "+46 72 012 3456", "email": "maja.forsberg@nobina.se", "license_number": "SE-DL-2024-34567", "eco_drive_score": 96.2, "training_certification": "CONSAT-CERT-ELITE", "assigned_vehicle": "VH-4524"},
]

# ============== Table 4: IoT Sensor Readings ==============
# GPS coordinates along real Stockholm bus routes
_ROUTE_COORDS = {
    "BUS-001": [(59.3215, 18.0010), (59.3280, 18.0350), (59.3350, 18.0680), (59.3410, 18.0920)],
    "BUS-002": [(59.3560, 18.0520), (59.3430, 18.0610), (59.3280, 18.0730), (59.3150, 18.0790)],
    "BUS-003": [(59.3060, 18.0440), (59.3200, 18.0400), (59.3380, 18.0330), (59.3510, 18.0290)],
    "BUS-005": [(59.3260, 18.1170), (59.3310, 18.0920), (59.3350, 18.0680), (59.3370, 18.0510)],
    "BUS-006": [(59.3570, 18.1020), (59.3480, 18.0950), (59.3350, 18.0830), (59.3150, 18.0700)],
    "BUS-008": [(59.3330, 18.0590), (59.3480, 18.0320), (59.3720, 17.9990), (59.4030, 17.9440)],
}

def _generate_sensor_readings():
    """Generate realistic IoT sensor readings."""
    readings = []
    base_time = datetime(2026, 5, 6, 6, 0, 0)
    reading_id = 1

    vehicle_route = {v["vehicle_id"]: v["assigned_route"] for v in BUS_VEHICLES}
    vehicle_driver = {}
    for d in DRIVERS:
        vid = d["assigned_vehicle"]
        vehicle_driver.setdefault(vid, []).append(d["driver_id"])

    random.seed(42)  # Reproducible data

    for vehicle in BUS_VEHICLES:
        vid = vehicle["vehicle_id"]
        route = vehicle_route[vid]
        coords = _ROUTE_COORDS.get(route, [(59.33, 18.07)])
        drivers = vehicle_driver.get(vid, ["DRV-1001"])

        for i in range(3):  # 3 readings per vehicle
            t = base_time + timedelta(minutes=random.randint(0, 720))
            coord = coords[i % len(coords)]
            readings.append({
                "reading_id": f"RD-20260506-{reading_id:03d}",
                "vehicle_id": vid,
                "route_id": route,
                "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S+02:00"),
                "latitude": round(coord[0] + random.uniform(-0.002, 0.002), 4),
                "longitude": round(coord[1] + random.uniform(-0.002, 0.002), 4),
                "speed_kmh": round(random.uniform(0, 55), 1),
                "passenger_count": random.randint(5, 45),
                "door_open_count": random.randint(0, 6),
                "fuel_consumption_l_per_km": round(random.uniform(0.35, 0.55), 2),
                "engine_temp_celsius": round(random.uniform(78, 98), 1),
                "brake_wear_pct": round(random.uniform(40, 95), 1),
                "driver_id": random.choice(drivers),
            })
            reading_id += 1

    return readings

IOT_SENSOR_READINGS = _generate_sensor_readings()


# ============== Query helpers ==============

def get_routes():
    return BUS_ROUTES

def get_route_by_line(line_number):
    return [r for r in BUS_ROUTES if r["line_number"] == line_number]

def get_vehicles(route_id=None):
    if route_id:
        return [v for v in BUS_VEHICLES if v["assigned_route"] == route_id]
    return BUS_VEHICLES

def get_drivers(vehicle_id=None):
    if vehicle_id:
        return [d for d in DRIVERS if d["assigned_vehicle"] == vehicle_id]
    return DRIVERS

def get_drivers_for_route(route_id):
    vehicle_ids = [v["vehicle_id"] for v in BUS_VEHICLES if v["assigned_route"] == route_id]
    return [d for d in DRIVERS if d["assigned_vehicle"] in vehicle_ids]

def get_sensor_readings(vehicle_id=None, route_id=None):
    results = IOT_SENSOR_READINGS
    if vehicle_id:
        results = [r for r in results if r["vehicle_id"] == vehicle_id]
    if route_id:
        results = [r for r in results if r["route_id"] == route_id]
    return results

def search_data(query_text):
    """Simple keyword search across all tables."""
    query = query_text.lower()
    results = {"routes": [], "vehicles": [], "drivers": [], "readings": []}

    # Check for line number
    for route in BUS_ROUTES:
        if str(route["line_number"]) in query or route["line_name"].lower() in query:
            results["routes"].append(route)
            rid = route["route_id"]
            results["vehicles"].extend(get_vehicles(rid))
            results["drivers"].extend(get_drivers_for_route(rid))
            results["readings"].extend(get_sensor_readings(route_id=rid))

    if not any(results.values()):
        # Fallback: return summary
        results = {
            "routes": BUS_ROUTES[:3],
            "vehicles": BUS_VEHICLES[:3],
            "drivers": DRIVERS[:3],
            "readings": IOT_SENSOR_READINGS[:5],
        }

    return results


# ============== Standalone test ==============

if __name__ == "__main__":
    print("=" * 70)
    print("STOCKHOLM BUS ROUTE MOCK DATABASE")
    print("=" * 70)
    print(f"\nRoutes:          {len(BUS_ROUTES)}")
    print(f"Vehicles:        {len(BUS_VEHICLES)}")
    print(f"Drivers:         {len(DRIVERS)}")
    print(f"Sensor Readings: {len(IOT_SENSOR_READINGS)}")

    print("\n--- Sample Route ---")
    print(json.dumps(BUS_ROUTES[5], indent=2, ensure_ascii=False))

    print("\n--- Sample Driver (PII!) ---")
    print(json.dumps(DRIVERS[0], indent=2, ensure_ascii=False))

    print("\n--- Sample IoT Reading ---")
    print(json.dumps(IOT_SENSOR_READINGS[0], indent=2, ensure_ascii=False))

    print("\n--- Search 'line 172' ---")
    res = search_data("line 172")
    print(f"  Routes: {len(res['routes'])}, Drivers: {len(res['drivers'])}, Readings: {len(res['readings'])}")

    print("\n✅ Mock database ready!")
