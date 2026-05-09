"""
Stockholm Bus Route Mock Database
==================================
Mock IoT sensor data for Stockholm bus routes with PII driver data.
Used to demonstrate Consat MCP policy-based data sharing.

Tables:
  BUS_ROUTES          - PUBLIC
  BUS_VEHICLES        - mixed (some COMPANY_SECRET)
  DRIVERS             - PII-heavy
  IOT_SENSOR_READINGS - mixed
  BUS_STOPS           - PUBLIC
  MAINTENANCE_LOGS    - COMPANY_SECRET
  DRIVER_SHIFTS       - PII-heavy
  INCIDENTS           - mixed

Author: CONSAT PoC Team
Date: May 6, 2026
"""

from datetime import datetime, timedelta
import random
import json

# ============== Table 1: Bus Routes ==============
BUS_ROUTES = [
    {"route_id": "BUS-001", "line_number": 1,   "line_name": "Stora Essingen - Frihamnen",          "operator": "Keolis",  "region": "Stockholm kommun", "frequency_min": 10, "total_stops": 22},
    {"route_id": "BUS-002", "line_number": 2,   "line_name": "Norrtull - Sofia",                    "operator": "Keolis",  "region": "Stockholm kommun", "frequency_min": 8,  "total_stops": 18},
    {"route_id": "BUS-003", "line_number": 3,   "line_name": "Södersjukhuset - Karolinska",         "operator": "Nobina", "region": "Stockholm kommun", "frequency_min": 10, "total_stops": 20},
    {"route_id": "BUS-004", "line_number": 4,   "line_name": "Gullmarsplan - Radiohuset",           "operator": "Nobina", "region": "Stockholm kommun", "frequency_min": 12, "total_stops": 15},
    {"route_id": "BUS-005", "line_number": 69,  "line_name": "Blockhusudden - Sergels torg",        "operator": "Keolis",  "region": "Stockholm kommun", "frequency_min": 15, "total_stops": 14},
    {"route_id": "BUS-006", "line_number": 172, "line_name": "Ropsten - Sickla köpkvarter",         "operator": "Nobina", "region": "Stockholm kommun", "frequency_min": 10, "total_stops": 19},
    {"route_id": "BUS-007", "line_number": 178, "line_name": "Mörby station - Danderyds sjukhus",   "operator": "Keolis",  "region": "Danderyd",         "frequency_min": 15, "total_stops": 8},
    {"route_id": "BUS-008", "line_number": 401, "line_name": "Cityterminalen - Kista",              "operator": "Nobina", "region": "Stockholm kommun", "frequency_min": 8,  "total_stops": 24},
    {"route_id": "BUS-009", "line_number": 55,  "line_name": "Hornstull - Liljeholmen",             "operator": "Keolis",  "region": "Stockholm kommun", "frequency_min": 10, "total_stops": 12},
    {"route_id": "BUS-010", "line_number": 62,  "line_name": "Slussen - Danvikshem",                "operator": "Nobina", "region": "Stockholm kommun", "frequency_min": 20, "total_stops": 10},
    {"route_id": "BUS-011", "line_number": 74,  "line_name": "Gullmarsplan - Telefonplan",          "operator": "Keolis",  "region": "Stockholm kommun", "frequency_min": 15, "total_stops": 11},
    {"route_id": "BUS-012", "line_number": 91,  "line_name": "Slussen - Nacka Forum",               "operator": "Nobina", "region": "Nacka kommun",     "frequency_min": 10, "total_stops": 16},
    {"route_id": "BUS-013", "line_number": 176, "line_name": "Danderyds sjukhus - Täby centrum",    "operator": "Keolis",  "region": "Täby kommun",      "frequency_min": 12, "total_stops": 21},
    {"route_id": "BUS-014", "line_number": 411, "line_name": "Cityterminalen - Lidingö centrum",    "operator": "Nobina", "region": "Lidingö stad",     "frequency_min": 20, "total_stops": 18},
]

# ============== Table 2: Bus Vehicles ==============
BUS_VEHICLES = [
    {"vehicle_id": "VH-4521", "registration_plate": "ABC 123", "vehicle_type": "diesel",   "capacity": 85,  "iot_device_id": "CONSAT-IOT-9832", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-15", "assigned_route": "BUS-006", "status": "in_service"},
    {"vehicle_id": "VH-4522", "registration_plate": "DEF 456", "vehicle_type": "hybrid",   "capacity": 90,  "iot_device_id": "CONSAT-IOT-9833", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-20", "assigned_route": "BUS-001", "status": "in_service"},
    {"vehicle_id": "VH-4523", "registration_plate": "GHI 789", "vehicle_type": "diesel",   "capacity": 85,  "iot_device_id": "CONSAT-IOT-9834", "firmware_version": "v3.1.8",      "last_maintenance_date": "2026-03-28", "assigned_route": "BUS-002", "status": "in_service"},
    {"vehicle_id": "VH-4524", "registration_plate": "JKL 012", "vehicle_type": "electric", "capacity": 80,  "iot_device_id": "CONSAT-IOT-9835", "firmware_version": "v3.2.0",      "last_maintenance_date": "2026-04-10", "assigned_route": "BUS-003", "status": "in_service"},
    {"vehicle_id": "VH-4525", "registration_plate": "MNO 345", "vehicle_type": "hybrid",   "capacity": 90,  "iot_device_id": "CONSAT-IOT-9836", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-25", "assigned_route": "BUS-005", "status": "in_service"},
    {"vehicle_id": "VH-4526", "registration_plate": "PQR 678", "vehicle_type": "diesel",   "capacity": 85,  "iot_device_id": "CONSAT-IOT-9837", "firmware_version": "v3.1.8",      "last_maintenance_date": "2026-04-01", "assigned_route": "BUS-004", "status": "in_service"},
    {"vehicle_id": "VH-4527", "registration_plate": "STU 901", "vehicle_type": "electric", "capacity": 80,  "iot_device_id": "CONSAT-IOT-9838", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-18", "assigned_route": "BUS-008", "status": "in_service"},
    {"vehicle_id": "VH-4528", "registration_plate": "VWX 234", "vehicle_type": "hybrid",   "capacity": 90,  "iot_device_id": "CONSAT-IOT-9839", "firmware_version": "v3.2.0",      "last_maintenance_date": "2026-04-22", "assigned_route": "BUS-007", "status": "in_service"},
    {"vehicle_id": "VH-4529", "registration_plate": "YZA 567", "vehicle_type": "electric", "capacity": 80,  "iot_device_id": "CONSAT-IOT-9840", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-28", "assigned_route": "BUS-009", "status": "in_service"},
    {"vehicle_id": "VH-4530", "registration_plate": "BCD 890", "vehicle_type": "diesel",   "capacity": 85,  "iot_device_id": "CONSAT-IOT-9841", "firmware_version": "v3.1.8",      "last_maintenance_date": "2026-03-15", "assigned_route": "BUS-010", "status": "maintenance"},
    {"vehicle_id": "VH-4531", "registration_plate": "EFG 123", "vehicle_type": "hybrid",   "capacity": 90,  "iot_device_id": "CONSAT-IOT-9842", "firmware_version": "v3.2.0",      "last_maintenance_date": "2026-04-30", "assigned_route": "BUS-011", "status": "in_service"},
    {"vehicle_id": "VH-4532", "registration_plate": "HIJ 456", "vehicle_type": "electric", "capacity": 80,  "iot_device_id": "CONSAT-IOT-9843", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-05-01", "assigned_route": "BUS-012", "status": "in_service"},
    {"vehicle_id": "VH-4533", "registration_plate": "KLM 789", "vehicle_type": "diesel",   "capacity": 100, "iot_device_id": "CONSAT-IOT-9844", "firmware_version": "v3.2.0",      "last_maintenance_date": "2026-04-12", "assigned_route": "BUS-013", "status": "in_service"},
    {"vehicle_id": "VH-4534", "registration_plate": "NOP 012", "vehicle_type": "hybrid",   "capacity": 90,  "iot_device_id": "CONSAT-IOT-9845", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-04-08", "assigned_route": "BUS-014", "status": "in_service"},
    {"vehicle_id": "VH-4535", "registration_plate": "QRS 345", "vehicle_type": "electric", "capacity": 80,  "iot_device_id": "CONSAT-IOT-9846", "firmware_version": "v3.2.1-beta", "last_maintenance_date": "2026-05-02", "assigned_route": "BUS-006", "status": "in_service"},
    {"vehicle_id": "VH-4536", "registration_plate": "TUV 678", "vehicle_type": "diesel",   "capacity": 85,  "iot_device_id": "CONSAT-IOT-9847", "firmware_version": "v3.1.8",      "last_maintenance_date": "2026-03-20", "assigned_route": "BUS-008", "status": "idle"},
]

# ============== Table 3: Drivers (PII-heavy) ==============
DRIVERS = [
    {"driver_id": "DRV-1001", "full_name": "Lars Eriksson",    "personal_number": "19850412-3456", "phone": "+46 70 123 4567", "email": "lars.eriksson@keolis.se",     "license_number": "SE-DL-2024-78341", "eco_drive_score": 87.3, "training_certification": "CONSAT-CERT-ADV",   "assigned_vehicle": "VH-4522"},
    {"driver_id": "DRV-1002", "full_name": "Anna Lindqvist",   "personal_number": "19900815-7823", "phone": "+46 73 234 5678", "email": "anna.lindqvist@nobina.se",    "license_number": "SE-DL-2023-56219", "eco_drive_score": 92.1, "training_certification": "CONSAT-CERT-ADV",   "assigned_vehicle": "VH-4524"},
    {"driver_id": "DRV-1003", "full_name": "Erik Johansson",   "personal_number": "19780623-1245", "phone": "+46 76 345 6789", "email": "erik.johansson@keolis.se",    "license_number": "SE-DL-2022-33456", "eco_drive_score": 78.5, "training_certification": "CONSAT-CERT-STD",   "assigned_vehicle": "VH-4521"},
    {"driver_id": "DRV-1004", "full_name": "Maria Svensson",   "personal_number": "19950307-9012", "phone": "+46 70 456 7890", "email": "maria.svensson@nobina.se",    "license_number": "SE-DL-2024-12098", "eco_drive_score": 95.0, "training_certification": "CONSAT-CERT-ADV",   "assigned_vehicle": "VH-4526"},
    {"driver_id": "DRV-1005", "full_name": "Oscar Nilsson",    "personal_number": "19880219-5678", "phone": "+46 72 567 8901", "email": "oscar.nilsson@keolis.se",     "license_number": "SE-DL-2023-89012", "eco_drive_score": 81.7, "training_certification": "CONSAT-CERT-STD",   "assigned_vehicle": "VH-4525"},
    {"driver_id": "DRV-1006", "full_name": "Sofia Andersson",  "personal_number": "19920614-3421", "phone": "+46 70 678 9012", "email": "sofia.andersson@nobina.se",   "license_number": "SE-DL-2024-45678", "eco_drive_score": 89.4, "training_certification": "CONSAT-CERT-ADV",   "assigned_vehicle": "VH-4523"},
    {"driver_id": "DRV-1007", "full_name": "Karl Bergström",   "personal_number": "19830901-8765", "phone": "+46 76 789 0123", "email": "karl.bergstrom@keolis.se",    "license_number": "SE-DL-2022-67890", "eco_drive_score": 74.2, "training_certification": "CONSAT-CERT-STD",   "assigned_vehicle": "VH-4528"},
    {"driver_id": "DRV-1008", "full_name": "Emma Pettersson",  "personal_number": "19970428-2345", "phone": "+46 73 890 1234", "email": "emma.pettersson@nobina.se",   "license_number": "SE-DL-2025-23456", "eco_drive_score": 91.8, "training_certification": "CONSAT-CERT-ADV",   "assigned_vehicle": "VH-4527"},
    {"driver_id": "DRV-1009", "full_name": "Gustav Holm",      "personal_number": "19860715-6789", "phone": "+46 70 901 2345", "email": "gustav.holm@keolis.se",       "license_number": "SE-DL-2023-78901", "eco_drive_score": 83.6, "training_certification": "CONSAT-CERT-STD",   "assigned_vehicle": "VH-4521"},
    {"driver_id": "DRV-1010", "full_name": "Maja Forsberg",    "personal_number": "19910322-1098", "phone": "+46 72 012 3456", "email": "maja.forsberg@nobina.se",     "license_number": "SE-DL-2024-34567", "eco_drive_score": 96.2, "training_certification": "CONSAT-CERT-ELITE", "assigned_vehicle": "VH-4524"},
    {"driver_id": "DRV-1011", "full_name": "Henrik Lundgren",  "personal_number": "19751104-4321", "phone": "+46 76 123 7890", "email": "henrik.lundgren@keolis.se",   "license_number": "SE-DL-2021-11234", "eco_drive_score": 70.1, "training_certification": "CONSAT-CERT-STD",   "assigned_vehicle": "VH-4529"},
    {"driver_id": "DRV-1012", "full_name": "Lena Magnusson",   "personal_number": "19890530-6543", "phone": "+46 73 456 0123", "email": "lena.magnusson@nobina.se",    "license_number": "SE-DL-2023-55678", "eco_drive_score": 88.0, "training_certification": "CONSAT-CERT-ADV",   "assigned_vehicle": "VH-4530"},
    {"driver_id": "DRV-1013", "full_name": "Patrik Olsson",    "personal_number": "19840209-7890", "phone": "+46 70 234 5678", "email": "patrik.olsson@keolis.se",     "license_number": "SE-DL-2022-98765", "eco_drive_score": 79.3, "training_certification": "CONSAT-CERT-STD",   "assigned_vehicle": "VH-4531"},
    {"driver_id": "DRV-1014", "full_name": "Ingrid Karlsson",  "personal_number": "19930817-2109", "phone": "+46 72 345 6789", "email": "ingrid.karlsson@nobina.se",   "license_number": "SE-DL-2024-76543", "eco_drive_score": 93.5, "training_certification": "CONSAT-CERT-ADV",   "assigned_vehicle": "VH-4532"},
    {"driver_id": "DRV-1015", "full_name": "Anders Björk",     "personal_number": "19801213-3456", "phone": "+46 76 456 7890", "email": "anders.bjork@keolis.se",      "license_number": "SE-DL-2022-43210", "eco_drive_score": 76.8, "training_certification": "CONSAT-CERT-STD",   "assigned_vehicle": "VH-4533"},
    {"driver_id": "DRV-1016", "full_name": "Karin Sjöberg",    "personal_number": "19960425-8765", "phone": "+46 73 567 8901", "email": "karin.sjoberg@nobina.se",     "license_number": "SE-DL-2025-32109", "eco_drive_score": 90.7, "training_certification": "CONSAT-CERT-ADV",   "assigned_vehicle": "VH-4534"},
]

# ============== Table 4: IoT Sensor Readings ==============
_ROUTE_COORDS = {
    "BUS-001": [(59.3215, 18.0010), (59.3280, 18.0350), (59.3350, 18.0680), (59.3410, 18.0920), (59.3460, 18.1100)],
    "BUS-002": [(59.3560, 18.0520), (59.3430, 18.0610), (59.3280, 18.0730), (59.3150, 18.0790), (59.3050, 18.0850)],
    "BUS-003": [(59.3060, 18.0440), (59.3200, 18.0400), (59.3380, 18.0330), (59.3510, 18.0290), (59.3610, 18.0250)],
    "BUS-004": [(59.3080, 18.0800), (59.3200, 18.0720), (59.3330, 18.0580), (59.3450, 18.0450), (59.3520, 18.0380)],
    "BUS-005": [(59.3260, 18.1170), (59.3310, 18.0920), (59.3350, 18.0680), (59.3370, 18.0510), (59.3390, 18.0380)],
    "BUS-006": [(59.3570, 18.1020), (59.3480, 18.0950), (59.3350, 18.0830), (59.3150, 18.0700), (59.3020, 18.1250)],
    "BUS-007": [(59.3980, 18.0360), (59.3920, 18.0310), (59.3870, 18.0290), (59.3820, 18.0320)],
    "BUS-008": [(59.3330, 18.0590), (59.3480, 18.0320), (59.3720, 17.9990), (59.4030, 17.9440), (59.4210, 17.9200)],
    "BUS-009": [(59.3160, 18.0300), (59.3190, 18.0200), (59.3220, 18.0100), (59.3260, 18.0020)],
    "BUS-010": [(59.3170, 18.0710), (59.3190, 18.0820), (59.3220, 18.0950), (59.3250, 18.1070)],
    "BUS-011": [(59.3080, 18.0800), (59.3120, 18.0630), (59.3160, 18.0480), (59.3200, 18.0280)],
    "BUS-012": [(59.3170, 18.0710), (59.3140, 18.0920), (59.3100, 18.1120), (59.3060, 18.1310)],
    "BUS-013": [(59.3980, 18.0360), (59.4100, 18.0410), (59.4250, 18.0490), (59.4380, 18.0680), (59.4560, 18.0730)],
    "BUS-014": [(59.3330, 18.0590), (59.3400, 18.1120), (59.3480, 18.1450), (59.3560, 18.1820)],
}


def _generate_sensor_readings():
    readings = []
    base_time = datetime(2026, 5, 6, 6, 0, 0)
    reading_id = 1
    vehicle_route = {v["vehicle_id"]: v["assigned_route"] for v in BUS_VEHICLES}
    vehicle_driver = {}
    for d in DRIVERS:
        vid = d["assigned_vehicle"]
        vehicle_driver.setdefault(vid, []).append(d["driver_id"])

    random.seed(42)

    for vehicle in BUS_VEHICLES:
        vid = vehicle["vehicle_id"]
        route = vehicle_route[vid]
        coords = _ROUTE_COORDS.get(route, [(59.33, 18.07)])
        drivers = vehicle_driver.get(vid, ["DRV-1001"])
        is_electric = vehicle["vehicle_type"] == "electric"
        is_hybrid = vehicle["vehicle_type"] == "hybrid"

        for i in range(10):
            t = base_time + timedelta(minutes=random.randint(0, 840))
            coord = coords[i % len(coords)]
            fuel = None if is_electric else round(random.uniform(0.28, 0.55), 2)
            battery = round(random.uniform(35, 98), 1) if (is_electric or is_hybrid) else None
            readings.append({
                "reading_id":               f"RD-20260506-{reading_id:04d}",
                "vehicle_id":               vid,
                "route_id":                 route,
                "timestamp":                t.strftime("%Y-%m-%dT%H:%M:%S+02:00"),
                "latitude":                 round(coord[0] + random.uniform(-0.003, 0.003), 5),
                "longitude":                round(coord[1] + random.uniform(-0.003, 0.003), 5),
                "heading_deg":              random.randint(0, 359),
                "speed_kmh":                round(random.uniform(0, 58), 1),
                "passenger_count":          random.randint(3, vehicle["capacity"] - 5),
                "door_events":              random.randint(0, 8),
                "delay_minutes":            round(random.uniform(-1.5, 6.0), 1),
                "fuel_consumption_l_per_km": fuel,
                "battery_level_pct":        battery,
                "engine_temp_celsius":      round(random.uniform(72, 102), 1),
                "brake_wear_pct":           round(random.uniform(35, 95), 1),
                "tire_pressure_bar":        round(random.uniform(7.2, 8.8), 2),
                "ac_status":                random.choice(["on", "on", "on", "off"]),
                "driver_id":                random.choice(drivers),
            })
            reading_id += 1

    return readings


IOT_SENSOR_READINGS = _generate_sensor_readings()


# ============== Table 5: Bus Stops (PUBLIC) ==============
BUS_STOPS = [
    {"stop_id": "STP-001", "stop_name": "Sergels torg",           "latitude": 59.3327, "longitude": 18.0645, "route_ids": ["BUS-002", "BUS-005", "BUS-009"], "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-002", "stop_name": "Slussen",                "latitude": 59.3196, "longitude": 18.0714, "route_ids": ["BUS-002", "BUS-010", "BUS-012"], "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-003", "stop_name": "Gullmarsplan",           "latitude": 59.3014, "longitude": 18.0793, "route_ids": ["BUS-004", "BUS-011"],            "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-004", "stop_name": "Ropsten",                "latitude": 59.3569, "longitude": 18.1018, "route_ids": ["BUS-006"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-005", "stop_name": "Sickla köpkvarter",      "latitude": 59.3021, "longitude": 18.1248, "route_ids": ["BUS-006"],                       "has_shelter": True,  "wheelchair_accessible": False, "real_time_board": True},
    {"stop_id": "STP-006", "stop_name": "Karolinska sjukhuset",   "latitude": 59.3514, "longitude": 18.0295, "route_ids": ["BUS-003", "BUS-013"],            "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-007", "stop_name": "Södersjukhuset",         "latitude": 59.3055, "longitude": 18.0437, "route_ids": ["BUS-003"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-008", "stop_name": "Danderyds sjukhus",      "latitude": 59.3980, "longitude": 18.0357, "route_ids": ["BUS-007", "BUS-013"],            "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-009", "stop_name": "Kista centrum",          "latitude": 59.4035, "longitude": 17.9449, "route_ids": ["BUS-008"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-010", "stop_name": "Cityterminalen",         "latitude": 59.3319, "longitude": 18.0577, "route_ids": ["BUS-008", "BUS-014"],            "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-011", "stop_name": "Blockhusudden",          "latitude": 59.3261, "longitude": 18.1175, "route_ids": ["BUS-005"],                       "has_shelter": False, "wheelchair_accessible": False, "real_time_board": False},
    {"stop_id": "STP-012", "stop_name": "Hornstull",              "latitude": 59.3159, "longitude": 18.0296, "route_ids": ["BUS-009"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-013", "stop_name": "Liljeholmen",            "latitude": 59.3100, "longitude": 18.0200, "route_ids": ["BUS-009"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-014", "stop_name": "Nacka Forum",            "latitude": 59.3060, "longitude": 18.1310, "route_ids": ["BUS-012"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-015", "stop_name": "Mörby station",          "latitude": 59.4000, "longitude": 18.0350, "route_ids": ["BUS-007"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-016", "stop_name": "Täby centrum",           "latitude": 59.4555, "longitude": 18.0730, "route_ids": ["BUS-013"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-017", "stop_name": "Lidingö centrum",        "latitude": 59.3560, "longitude": 18.1830, "route_ids": ["BUS-014"],                       "has_shelter": True,  "wheelchair_accessible": False, "real_time_board": True},
    {"stop_id": "STP-018", "stop_name": "Frihamnen",              "latitude": 59.3460, "longitude": 18.1090, "route_ids": ["BUS-001"],                       "has_shelter": False, "wheelchair_accessible": True,  "real_time_board": False},
    {"stop_id": "STP-019", "stop_name": "Norrtull",               "latitude": 59.3555, "longitude": 18.0515, "route_ids": ["BUS-002"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-020", "stop_name": "Telefonplan",            "latitude": 59.3205, "longitude": 18.0285, "route_ids": ["BUS-011"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    # Additional stops for BUS-001 (Stora Essingen - Frihamnen) and other routes
    {"stop_id": "STP-021", "stop_name": "Stora Essingen",         "latitude": 59.3215, "longitude": 18.0010, "route_ids": ["BUS-001"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-022", "stop_name": "Essingetorget",          "latitude": 59.3235, "longitude": 18.0155, "route_ids": ["BUS-001"],                       "has_shelter": False, "wheelchair_accessible": True,  "real_time_board": False},
    {"stop_id": "STP-023", "stop_name": "Primusgatan",            "latitude": 59.3270, "longitude": 18.0262, "route_ids": ["BUS-001"],                       "has_shelter": True,  "wheelchair_accessible": False, "real_time_board": True},
    {"stop_id": "STP-024", "stop_name": "Kristinebergs slott",    "latitude": 59.3295, "longitude": 18.0320, "route_ids": ["BUS-001"],                       "has_shelter": False, "wheelchair_accessible": False, "real_time_board": False},
    {"stop_id": "STP-025", "stop_name": "Fredhäll",               "latitude": 59.3330, "longitude": 18.0390, "route_ids": ["BUS-001"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-026", "stop_name": "Lindhagensplan",         "latitude": 59.3360, "longitude": 18.0510, "route_ids": ["BUS-001", "BUS-008"],            "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-027", "stop_name": "Thorildsplan",           "latitude": 59.3370, "longitude": 18.0075, "route_ids": ["BUS-001"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-028", "stop_name": "Sofia",                  "latitude": 59.3090, "longitude": 18.0910, "route_ids": ["BUS-002"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
    {"stop_id": "STP-029", "stop_name": "Danvikshem",             "latitude": 59.3250, "longitude": 18.1070, "route_ids": ["BUS-010"],                       "has_shelter": False, "wheelchair_accessible": False, "real_time_board": False},
    {"stop_id": "STP-030", "stop_name": "Radiohuset",             "latitude": 59.3520, "longitude": 18.0382, "route_ids": ["BUS-004"],                       "has_shelter": True,  "wheelchair_accessible": True,  "real_time_board": True},
]


# ============== Table 6: Maintenance Logs (COMPANY_SECRET) ==============
MAINTENANCE_LOGS = [
    {"log_id": "MNT-0001", "vehicle_id": "VH-4521", "date": "2026-04-15", "maintenance_type": "scheduled",  "technician_id": "TECH-201", "technician_name": "Björn Lindström",  "cost_sek": 4200,  "parts_replaced": ["brake pads front", "air filter"],       "firmware_updated_to": None,          "duration_hours": 3.5, "internal_notes": "Brake wear was at 82%. Replaced ahead of schedule per CONSAT maintenance protocol v4.2."},
    {"log_id": "MNT-0002", "vehicle_id": "VH-4522", "date": "2026-04-20", "maintenance_type": "scheduled",  "technician_id": "TECH-202", "technician_name": "Petra Holm",       "cost_sek": 1800,  "parts_replaced": ["cabin air filter"],                     "firmware_updated_to": "v3.2.1-beta", "duration_hours": 2.0, "internal_notes": "OTA firmware pushed. Device responded OK. Battery health at 94%."},
    {"log_id": "MNT-0003", "vehicle_id": "VH-4523", "date": "2026-03-28", "maintenance_type": "emergency",  "technician_id": "TECH-201", "technician_name": "Björn Lindström",  "cost_sek": 11500, "parts_replaced": ["front left tyre", "suspension bushing"], "firmware_updated_to": None,          "duration_hours": 6.0, "internal_notes": "Tyre blowout on Essingeleden. Root cause: kerb impact. Not covered by warranty. Insurance claim filed (REF-2026-04421)."},
    {"log_id": "MNT-0004", "vehicle_id": "VH-4524", "date": "2026-04-10", "maintenance_type": "scheduled",  "technician_id": "TECH-203", "technician_name": "Anna-Karin Berg",  "cost_sek": 2600,  "parts_replaced": ["wiper blades", "cabin air filter"],     "firmware_updated_to": "v3.2.0",      "duration_hours": 2.5, "internal_notes": "Battery pack capacity test: 97.3% retained. Charging curve nominal."},
    {"log_id": "MNT-0005", "vehicle_id": "VH-4525", "date": "2026-04-25", "maintenance_type": "scheduled",  "technician_id": "TECH-202", "technician_name": "Petra Holm",       "cost_sek": 3100,  "parts_replaced": ["brake pads rear"],                      "firmware_updated_to": None,          "duration_hours": 2.0, "internal_notes": "Routine check OK. Hybrid battery at 89%."},
    {"log_id": "MNT-0006", "vehicle_id": "VH-4526", "date": "2026-04-01", "maintenance_type": "scheduled",  "technician_id": "TECH-204", "technician_name": "Marcus Lund",      "cost_sek": 5400,  "parts_replaced": ["exhaust filter", "brake pads all four"], "firmware_updated_to": "v3.1.8",      "duration_hours": 4.0, "internal_notes": "High brake wear noted for this route. Recommend increased inspection frequency."},
    {"log_id": "MNT-0007", "vehicle_id": "VH-4527", "date": "2026-04-18", "maintenance_type": "scheduled",  "technician_id": "TECH-203", "technician_name": "Anna-Karin Berg",  "cost_sek": 1500,  "parts_replaced": ["cabin air filter"],                     "firmware_updated_to": "v3.2.1-beta", "duration_hours": 1.5, "internal_notes": "OTA update applied. IoT module recalibrated. Charging port cleaned."},
    {"log_id": "MNT-0008", "vehicle_id": "VH-4528", "date": "2026-04-22", "maintenance_type": "scheduled",  "technician_id": "TECH-204", "technician_name": "Marcus Lund",      "cost_sek": 2900,  "parts_replaced": ["wiper motor", "belt tensioner"],        "firmware_updated_to": None,          "duration_hours": 3.0, "internal_notes": "Wiper motor replaced under extended warranty. Claim submitted to Volvo Buses (WRN-2026-0091)."},
    {"log_id": "MNT-0009", "vehicle_id": "VH-4530", "date": "2026-03-15", "maintenance_type": "emergency",  "technician_id": "TECH-201", "technician_name": "Björn Lindström",  "cost_sek": 18700, "parts_replaced": ["engine injector x3", "turbo hose"],     "firmware_updated_to": None,          "duration_hours": 9.5, "internal_notes": "Engine fault code P0191. Injector pressure failure. Vehicle out of service since 2026-03-15. ETA return: 2026-05-10."},
    {"log_id": "MNT-0010", "vehicle_id": "VH-4529", "date": "2026-04-28", "maintenance_type": "scheduled",  "technician_id": "TECH-203", "technician_name": "Anna-Karin Berg",  "cost_sek": 1200,  "parts_replaced": ["cabin air filter"],                     "firmware_updated_to": "v3.2.1-beta", "duration_hours": 1.5, "internal_notes": "Battery health 99.1%. OTA update applied successfully."},
    {"log_id": "MNT-0011", "vehicle_id": "VH-4531", "date": "2026-04-30", "maintenance_type": "scheduled",  "technician_id": "TECH-202", "technician_name": "Petra Holm",       "cost_sek": 3300,  "parts_replaced": ["brake pads front", "air filter"],       "firmware_updated_to": "v3.2.0",      "duration_hours": 3.0, "internal_notes": "Hybrid battery health at 91%. All systems nominal."},
    {"log_id": "MNT-0012", "vehicle_id": "VH-4532", "date": "2026-05-01", "maintenance_type": "scheduled",  "technician_id": "TECH-203", "technician_name": "Anna-Karin Berg",  "cost_sek": 1400,  "parts_replaced": ["wiper blades"],                         "firmware_updated_to": "v3.2.1-beta", "duration_hours": 1.0, "internal_notes": "Battery pack at 95.8%. Fast charging port inspection OK."},
    {"log_id": "MNT-0013", "vehicle_id": "VH-4533", "date": "2026-04-12", "maintenance_type": "scheduled",  "technician_id": "TECH-204", "technician_name": "Marcus Lund",      "cost_sek": 6100,  "parts_replaced": ["brake pads all four", "cabin air filter","exhaust filter"], "firmware_updated_to": "v3.2.0", "duration_hours": 4.5, "internal_notes": "High-capacity bus. Heavy brake wear typical for Täby route gradient."},
    {"log_id": "MNT-0014", "vehicle_id": "VH-4534", "date": "2026-04-08", "maintenance_type": "scheduled",  "technician_id": "TECH-202", "technician_name": "Petra Holm",       "cost_sek": 2700,  "parts_replaced": ["cabin air filter", "wiper blades"],     "firmware_updated_to": "v3.2.1-beta", "duration_hours": 2.0, "internal_notes": "Hybrid battery 88%. All sensors calibrated."},
    {"log_id": "MNT-0015", "vehicle_id": "VH-4535", "date": "2026-05-02", "maintenance_type": "scheduled",  "technician_id": "TECH-203", "technician_name": "Anna-Karin Berg",  "cost_sek": 1300,  "parts_replaced": ["cabin air filter"],                     "firmware_updated_to": "v3.2.1-beta", "duration_hours": 1.0, "internal_notes": "New vehicle first service check. Battery 99.5%. All OK."},
    {"log_id": "MNT-0016", "vehicle_id": "VH-4536", "date": "2026-03-20", "maintenance_type": "emergency",  "technician_id": "TECH-201", "technician_name": "Björn Lindström",  "cost_sek": 22400, "parts_replaced": ["gearbox unit", "driveshaft seal", "transmission fluid"], "firmware_updated_to": None, "duration_hours": 14.0, "internal_notes": "Gearbox failure on Essingeleden. Severe transmission damage. Vehicle placed on idle status pending part delivery (ETA 2026-06-15). Cost flagged for insurance review."},
]


# ============== Table 7: Driver Shifts (PII-heavy) ==============
DRIVER_SHIFTS = [
    {"shift_id": "SHF-2026-001", "driver_id": "DRV-1001", "vehicle_id": "VH-4522", "route_id": "BUS-001", "shift_date": "2026-05-06", "start_time": "06:00", "end_time": "14:00", "depot": "Depot Hornsberg",      "break_location": "Frihamnen terminal",    "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-002", "driver_id": "DRV-1002", "vehicle_id": "VH-4524", "route_id": "BUS-003", "shift_date": "2026-05-06", "start_time": "07:00", "end_time": "15:00", "depot": "Depot Söderhallen",    "break_location": "Karolinska sjukhuset",  "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-003", "driver_id": "DRV-1003", "vehicle_id": "VH-4521", "route_id": "BUS-006", "shift_date": "2026-05-06", "start_time": "05:30", "end_time": "13:30", "depot": "Depot Lidingövägen",   "break_location": "Ropsten terminal",      "overtime_hours": 0.5},
    {"shift_id": "SHF-2026-004", "driver_id": "DRV-1004", "vehicle_id": "VH-4526", "route_id": "BUS-004", "shift_date": "2026-05-06", "start_time": "14:00", "end_time": "22:00", "depot": "Depot Söderhallen",    "break_location": "Gullmarsplan terminal", "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-005", "driver_id": "DRV-1005", "vehicle_id": "VH-4525", "route_id": "BUS-005", "shift_date": "2026-05-06", "start_time": "08:00", "end_time": "16:00", "depot": "Depot Lidingövägen",   "break_location": "Sergels torg",          "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-006", "driver_id": "DRV-1006", "vehicle_id": "VH-4523", "route_id": "BUS-002", "shift_date": "2026-05-06", "start_time": "06:30", "end_time": "14:30", "depot": "Depot Hornsberg",      "break_location": "Norrtull terminal",     "overtime_hours": 1.0},
    {"shift_id": "SHF-2026-007", "driver_id": "DRV-1007", "vehicle_id": "VH-4528", "route_id": "BUS-007", "shift_date": "2026-05-06", "start_time": "07:00", "end_time": "15:00", "depot": "Depot Danderyd",       "break_location": "Danderyds sjukhus",     "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-008", "driver_id": "DRV-1008", "vehicle_id": "VH-4527", "route_id": "BUS-008", "shift_date": "2026-05-06", "start_time": "05:00", "end_time": "13:00", "depot": "Depot Kista",          "break_location": "Kista centrum",         "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-009", "driver_id": "DRV-1009", "vehicle_id": "VH-4521", "route_id": "BUS-006", "shift_date": "2026-05-06", "start_time": "14:00", "end_time": "22:00", "depot": "Depot Lidingövägen",   "break_location": "Sickla terminal",       "overtime_hours": 0.5},
    {"shift_id": "SHF-2026-010", "driver_id": "DRV-1010", "vehicle_id": "VH-4524", "route_id": "BUS-003", "shift_date": "2026-05-06", "start_time": "15:00", "end_time": "23:00", "depot": "Depot Söderhallen",    "break_location": "Södersjukhuset",        "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-011", "driver_id": "DRV-1011", "vehicle_id": "VH-4529", "route_id": "BUS-009", "shift_date": "2026-05-06", "start_time": "06:00", "end_time": "14:00", "depot": "Depot Hornsberg",      "break_location": "Liljeholmen terminal",  "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-012", "driver_id": "DRV-1012", "vehicle_id": "VH-4530", "route_id": "BUS-010", "shift_date": "2026-05-06", "start_time": "07:00", "end_time": "15:00", "depot": "Depot Söderhallen",    "break_location": "Slussen terminal",      "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-013", "driver_id": "DRV-1013", "vehicle_id": "VH-4531", "route_id": "BUS-011", "shift_date": "2026-05-07", "start_time": "06:00", "end_time": "14:00", "depot": "Depot Hornsberg",      "break_location": "Telefonplan terminal",  "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-014", "driver_id": "DRV-1014", "vehicle_id": "VH-4532", "route_id": "BUS-012", "shift_date": "2026-05-07", "start_time": "07:30", "end_time": "15:30", "depot": "Depot Söderhallen",    "break_location": "Nacka Forum",           "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-015", "driver_id": "DRV-1015", "vehicle_id": "VH-4533", "route_id": "BUS-013", "shift_date": "2026-05-07", "start_time": "05:45", "end_time": "13:45", "depot": "Depot Danderyd",       "break_location": "Täby centrum",          "overtime_hours": 1.5},
    {"shift_id": "SHF-2026-016", "driver_id": "DRV-1016", "vehicle_id": "VH-4534", "route_id": "BUS-014", "shift_date": "2026-05-07", "start_time": "08:00", "end_time": "16:00", "depot": "Depot Lidingövägen",   "break_location": "Lidingö centrum",       "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-017", "driver_id": "DRV-1001", "vehicle_id": "VH-4522", "route_id": "BUS-001", "shift_date": "2026-05-07", "start_time": "06:00", "end_time": "14:00", "depot": "Depot Hornsberg",      "break_location": "Frihamnen terminal",    "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-018", "driver_id": "DRV-1003", "vehicle_id": "VH-4535", "route_id": "BUS-006", "shift_date": "2026-05-07", "start_time": "14:00", "end_time": "22:00", "depot": "Depot Lidingövägen",   "break_location": "Ropsten terminal",      "overtime_hours": 0.0},
    # 2026-05-08 — full day coverage
    {"shift_id": "SHF-2026-019", "driver_id": "DRV-1001", "vehicle_id": "VH-4522", "route_id": "BUS-001", "shift_date": "2026-05-08", "start_time": "06:00", "end_time": "14:00", "depot": "Depot Hornsberg",      "break_location": "Frihamnen terminal",    "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-020", "driver_id": "DRV-1002", "vehicle_id": "VH-4524", "route_id": "BUS-003", "shift_date": "2026-05-08", "start_time": "07:00", "end_time": "15:00", "depot": "Depot Söderhallen",    "break_location": "Karolinska sjukhuset",  "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-021", "driver_id": "DRV-1003", "vehicle_id": "VH-4521", "route_id": "BUS-006", "shift_date": "2026-05-08", "start_time": "05:30", "end_time": "13:30", "depot": "Depot Lidingövägen",   "break_location": "Ropsten terminal",      "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-022", "driver_id": "DRV-1004", "vehicle_id": "VH-4526", "route_id": "BUS-004", "shift_date": "2026-05-08", "start_time": "14:00", "end_time": "22:00", "depot": "Depot Söderhallen",    "break_location": "Gullmarsplan terminal", "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-023", "driver_id": "DRV-1005", "vehicle_id": "VH-4525", "route_id": "BUS-005", "shift_date": "2026-05-08", "start_time": "08:00", "end_time": "16:00", "depot": "Depot Lidingövägen",   "break_location": "Sergels torg",          "overtime_hours": 0.5},
    {"shift_id": "SHF-2026-024", "driver_id": "DRV-1006", "vehicle_id": "VH-4523", "route_id": "BUS-002", "shift_date": "2026-05-08", "start_time": "06:30", "end_time": "14:30", "depot": "Depot Hornsberg",      "break_location": "Norrtull terminal",     "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-025", "driver_id": "DRV-1007", "vehicle_id": "VH-4528", "route_id": "BUS-007", "shift_date": "2026-05-08", "start_time": "07:00", "end_time": "15:00", "depot": "Depot Danderyd",       "break_location": "Danderyds sjukhus",     "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-026", "driver_id": "DRV-1008", "vehicle_id": "VH-4527", "route_id": "BUS-008", "shift_date": "2026-05-08", "start_time": "05:00", "end_time": "13:00", "depot": "Depot Kista",          "break_location": "Kista centrum",         "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-027", "driver_id": "DRV-1009", "vehicle_id": "VH-4521", "route_id": "BUS-006", "shift_date": "2026-05-08", "start_time": "14:00", "end_time": "22:00", "depot": "Depot Lidingövägen",   "break_location": "Sickla terminal",       "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-028", "driver_id": "DRV-1010", "vehicle_id": "VH-4524", "route_id": "BUS-003", "shift_date": "2026-05-08", "start_time": "15:00", "end_time": "23:00", "depot": "Depot Söderhallen",    "break_location": "Södersjukhuset",        "overtime_hours": 0.5},
    {"shift_id": "SHF-2026-029", "driver_id": "DRV-1011", "vehicle_id": "VH-4529", "route_id": "BUS-009", "shift_date": "2026-05-08", "start_time": "06:00", "end_time": "14:00", "depot": "Depot Hornsberg",      "break_location": "Liljeholmen terminal",  "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-030", "driver_id": "DRV-1012", "vehicle_id": "VH-4531", "route_id": "BUS-011", "shift_date": "2026-05-08", "start_time": "14:00", "end_time": "22:00", "depot": "Depot Hornsberg",      "break_location": "Telefonplan terminal",  "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-031", "driver_id": "DRV-1013", "vehicle_id": "VH-4531", "route_id": "BUS-011", "shift_date": "2026-05-08", "start_time": "06:00", "end_time": "14:00", "depot": "Depot Hornsberg",      "break_location": "Telefonplan terminal",  "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-032", "driver_id": "DRV-1014", "vehicle_id": "VH-4532", "route_id": "BUS-012", "shift_date": "2026-05-08", "start_time": "07:30", "end_time": "15:30", "depot": "Depot Söderhallen",    "break_location": "Nacka Forum",           "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-033", "driver_id": "DRV-1015", "vehicle_id": "VH-4533", "route_id": "BUS-013", "shift_date": "2026-05-08", "start_time": "05:45", "end_time": "13:45", "depot": "Depot Danderyd",       "break_location": "Täby centrum",          "overtime_hours": 0.0},
    {"shift_id": "SHF-2026-034", "driver_id": "DRV-1016", "vehicle_id": "VH-4534", "route_id": "BUS-014", "shift_date": "2026-05-08", "start_time": "08:00", "end_time": "16:00", "depot": "Depot Lidingövägen",   "break_location": "Lidingö centrum",       "overtime_hours": 0.0},
]


# ============== Table 8: Incidents (Mixed sensitivity) ==============
INCIDENTS = [
    {"incident_id": "INC-2026-001", "type": "delay",              "severity": "low",    "vehicle_id": "VH-4523", "driver_id": "DRV-1006", "route_id": "BUS-002", "timestamp": "2026-05-06T08:14:00+02:00", "latitude": 59.3430, "longitude": 18.0610, "description": "Heavy traffic at Norrtull. 6-minute delay reported.", "status": "closed", "reported_to_authority": False},
    {"incident_id": "INC-2026-002", "type": "breakdown",          "severity": "high",   "vehicle_id": "VH-4530", "driver_id": "DRV-1012", "route_id": "BUS-010", "timestamp": "2026-03-15T09:42:00+02:00", "latitude": 59.3190, "longitude": 18.0820, "description": "Engine injector failure. Passengers transferred to replacement bus VH-4536. Vehicle towed to Depot Söderhallen.", "status": "open",   "reported_to_authority": True},
    {"incident_id": "INC-2026-003", "type": "passenger_incident", "severity": "medium", "vehicle_id": "VH-4521", "driver_id": "DRV-1003", "route_id": "BUS-006", "timestamp": "2026-05-05T17:33:00+02:00", "latitude": 59.3480, "longitude": 18.0950, "description": "Passenger fell while boarding. Minor injury reported. Emergency services called. Police report filed (2026-12345).", "status": "open",   "reported_to_authority": True},
    {"incident_id": "INC-2026-004", "type": "delay",              "severity": "low",    "vehicle_id": "VH-4527", "driver_id": "DRV-1008", "route_id": "BUS-008", "timestamp": "2026-05-06T07:55:00+02:00", "latitude": 59.3720, "longitude": 17.9990, "description": "Road works on Kista Entrégata caused 4-minute delay.", "status": "closed", "reported_to_authority": False},
    {"incident_id": "INC-2026-005", "type": "minor_collision",    "severity": "medium", "vehicle_id": "VH-4526", "driver_id": "DRV-1004", "route_id": "BUS-004", "timestamp": "2026-04-28T14:18:00+02:00", "latitude": 59.3200, "longitude": 18.0720, "description": "Low-speed contact with cyclist at Gullmarsplan. No injuries. Cyclist confirmed no damage. Incident documented per SL protocol.", "status": "closed", "reported_to_authority": True},
    {"incident_id": "INC-2026-006", "type": "delay",              "severity": "medium", "vehicle_id": "VH-4533", "driver_id": "DRV-1015", "route_id": "BUS-013", "timestamp": "2026-05-07T07:10:00+02:00", "latitude": 59.4250, "longitude": 18.0490, "description": "Signal fault at Danderyds sjukhus crossing. 11-minute delay. Reported to Trafikverket.", "status": "open",   "reported_to_authority": True},
    {"incident_id": "INC-2026-007", "type": "breakdown",          "severity": "medium", "vehicle_id": "VH-4528", "driver_id": "DRV-1007", "route_id": "BUS-007", "timestamp": "2026-04-30T10:05:00+02:00", "latitude": 59.3870, "longitude": 18.0290, "description": "Wiper motor failure during rain. Driver continued cautiously to Mörby station. Vehicle taken out of service for maintenance.", "status": "closed", "reported_to_authority": False},
    {"incident_id": "INC-2026-008", "type": "delay",              "severity": "low",    "vehicle_id": "VH-4525", "driver_id": "DRV-1005", "route_id": "BUS-005", "timestamp": "2026-05-06T09:20:00+02:00", "latitude": 59.3310, "longitude": 18.0920, "description": "Congestion near Djurgården entrance. 3-minute delay.", "status": "closed", "reported_to_authority": False},
    {"incident_id": "INC-2026-009", "type": "passenger_incident", "severity": "low",    "vehicle_id": "VH-4529", "driver_id": "DRV-1011", "route_id": "BUS-009", "timestamp": "2026-05-06T16:48:00+02:00", "latitude": 59.3190, "longitude": 18.0200, "description": "Verbal dispute between passengers. Driver intervened. Situation resolved without police involvement.", "status": "closed", "reported_to_authority": False},
    {"incident_id": "INC-2026-010", "type": "delay",              "severity": "high",   "vehicle_id": "VH-4535", "driver_id": "DRV-1003", "route_id": "BUS-006", "timestamp": "2026-05-07T08:02:00+02:00", "latitude": 59.3570, "longitude": 18.1020, "description": "Accident on Lidingövägen blocked route. 22-minute delay. Diversion via Ropsten approved by SL control.", "status": "open",   "reported_to_authority": True},
    {"incident_id": "INC-2026-011", "type": "security_alert",    "severity": "high",   "vehicle_id": "VH-4522", "driver_id": "DRV-1001", "route_id": "BUS-001", "timestamp": "2026-05-08T07:22:00+02:00", "latitude": 59.3280, "longitude": 18.0350, "description": "Suspicious unattended bag reported by driver at Lindhagensplan stop. Police unit dispatched. Bag cleared — forgotten commuter item. Route resumed after 18-min delay.", "status": "closed", "reported_to_authority": True},
    {"incident_id": "INC-2026-012", "type": "medical_emergency", "severity": "high",   "vehicle_id": "VH-4524", "driver_id": "DRV-1002", "route_id": "BUS-003", "timestamp": "2026-05-08T09:11:00+02:00", "latitude": 59.3380, "longitude": 18.0330, "description": "Passenger collapsed on board near Karolinska. Driver stopped at designated pull-over zone. Ambulance arrived in 6 minutes. Passenger transported to Karolinska sjukhuset.", "status": "closed", "reported_to_authority": True},
    {"incident_id": "INC-2026-013", "type": "vandalism",         "severity": "low",    "vehicle_id": "VH-4532", "driver_id": "DRV-1014", "route_id": "BUS-012", "timestamp": "2026-05-07T22:40:00+02:00", "latitude": 59.3100, "longitude": 18.1120, "description": "Graffiti found on rear window exterior at end-of-line Nacka Forum. Damage estimated 1 800 SEK. Cleaning crew notified. No suspects identified.", "status": "open",   "reported_to_authority": False},
    {"incident_id": "INC-2026-014", "type": "delay",             "severity": "medium", "vehicle_id": "VH-4533", "driver_id": "DRV-1015", "route_id": "BUS-013", "timestamp": "2026-05-08T07:50:00+02:00", "latitude": 59.4100, "longitude": 18.0410, "description": "Heavy rain and reduced visibility on Täby route. Driver reduced speed per safety protocol. 8-minute accumulated delay. Passengers notified via real-time board.", "status": "closed", "reported_to_authority": False},
    {"incident_id": "INC-2026-015", "type": "door_malfunction",  "severity": "medium", "vehicle_id": "VH-4523", "driver_id": "DRV-1006", "route_id": "BUS-002", "timestamp": "2026-05-08T10:35:00+02:00", "latitude": 59.3430, "longitude": 18.0610, "description": "Rear door failed to close fully at Norrtull stop. Driver bypassed with override. Passengers redirected to front door. Vehicle inspected at depot — door sensor replacement scheduled.", "status": "open",   "reported_to_authority": False},
]


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

def get_stops(route_id=None):
    if route_id:
        return [s for s in BUS_STOPS if route_id in s["route_ids"]]
    return BUS_STOPS

def get_maintenance_logs(vehicle_id=None):
    if vehicle_id:
        return [m for m in MAINTENANCE_LOGS if m["vehicle_id"] == vehicle_id]
    return MAINTENANCE_LOGS

def get_shifts(driver_id=None, vehicle_id=None, shift_date=None):
    results = DRIVER_SHIFTS
    if driver_id:
        results = [s for s in results if s["driver_id"] == driver_id]
    if vehicle_id:
        results = [s for s in results if s["vehicle_id"] == vehicle_id]
    if shift_date:
        results = [s for s in results if s["shift_date"] == shift_date]
    return results

def get_incidents(vehicle_id=None, route_id=None, severity=None):
    results = INCIDENTS
    if vehicle_id:
        results = [i for i in results if i["vehicle_id"] == vehicle_id]
    if route_id:
        results = [i for i in results if i["route_id"] == route_id]
    if severity:
        results = [i for i in results if i["severity"] == severity]
    return results

def search_data(query_text):
    query = query_text.lower()
    results = {"routes": [], "vehicles": [], "drivers": [], "readings": [], "stops": [], "maintenance": [], "shifts": [], "incidents": []}

    for route in BUS_ROUTES:
        if str(route["line_number"]) in query or route["line_name"].lower() in query or route["route_id"].lower() in query:
            rid = route["route_id"]
            results["routes"].append(route)
            results["vehicles"].extend(get_vehicles(rid))
            results["drivers"].extend(get_drivers_for_route(rid))
            results["readings"].extend(get_sensor_readings(route_id=rid))
            results["stops"].extend(get_stops(rid))
            results["incidents"].extend(get_incidents(route_id=rid))

    for driver in DRIVERS:
        if driver["driver_id"].lower() in query or driver["full_name"].lower() in query:
            if driver not in results["drivers"]:
                results["drivers"].append(driver)
            results["shifts"].extend(get_shifts(driver_id=driver["driver_id"]))

    for log in MAINTENANCE_LOGS:
        if log["technician_name"].lower() in query or log["technician_id"].lower() in query:
            if log not in results["maintenance"]:
                results["maintenance"].append(log)

    for vehicle in BUS_VEHICLES:
        if vehicle["vehicle_id"].lower() in query:
            if vehicle not in results["vehicles"]:
                results["vehicles"].append(vehicle)
            results["readings"].extend(get_sensor_readings(vehicle_id=vehicle["vehicle_id"]))
            results["maintenance"].extend(get_maintenance_logs(vehicle_id=vehicle["vehicle_id"]))

    if not any(results.values()):
        results = {
            "routes":      BUS_ROUTES[:3],
            "vehicles":    BUS_VEHICLES[:3],
            "drivers":     DRIVERS[:3],
            "readings":    IOT_SENSOR_READINGS[:5],
            "stops":       BUS_STOPS[:5],
            "maintenance": MAINTENANCE_LOGS[:3],
            "shifts":      DRIVER_SHIFTS[:3],
            "incidents":   INCIDENTS[:3],
        }

    return results


# ============== Standalone test ==============

if __name__ == "__main__":
    print("=" * 70)
    print("STOCKHOLM BUS ROUTE MOCK DATABASE")
    print("=" * 70)
    print(f"\nRoutes:           {len(BUS_ROUTES)}")
    print(f"Vehicles:         {len(BUS_VEHICLES)}")
    print(f"Drivers:          {len(DRIVERS)}")
    print(f"Sensor Readings:  {len(IOT_SENSOR_READINGS)}")
    print(f"Bus Stops:        {len(BUS_STOPS)}")
    print(f"Maintenance Logs: {len(MAINTENANCE_LOGS)}")
    print(f"Driver Shifts:    {len(DRIVER_SHIFTS)}")
    print(f"Incidents:        {len(INCIDENTS)}")

    print("\n--- Sample Route ---")
    print(json.dumps(BUS_ROUTES[5], indent=2, ensure_ascii=False))

    print("\n--- Sample Driver (PII!) ---")
    print(json.dumps(DRIVERS[0], indent=2, ensure_ascii=False))

    print("\n--- Sample IoT Reading ---")
    print(json.dumps(IOT_SENSOR_READINGS[0], indent=2, ensure_ascii=False))

    print("\n--- Sample Maintenance Log (COMPANY SECRET) ---")
    print(json.dumps(MAINTENANCE_LOGS[0], indent=2, ensure_ascii=False))

    print("\n--- Search 'line 172' ---")
    res = search_data("line 172")
    for k, v in res.items():
        if v:
            print(f"  {k}: {len(v)} records")

    print("\n✅ Mock database ready!")
