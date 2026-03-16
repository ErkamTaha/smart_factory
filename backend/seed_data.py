"""
Seed script: Generate realistic devices and sensor readings for Smart Factory.
Run inside the backend container: python seed_data.py
"""

import asyncio
import random
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from app.database.database import SessionLocal as async_session_factory
from app.models.mqtt_models import MQTTDevice, MQTTSensorReading
from app.models.ss_models import SSSensor, SSSensorType
from app.models.acl_models import ACLUser


# ── Additional devices to create ──────────────────────────────────────────────
EXTRA_DEVICES = [
    {
        "device_id": "temp_sensor_floor_b2",
        "device_name": "Temperature Sensor - Floor B2",
        "device_type": "sensor",
        "location": "Factory Floor - Section B2",
        "description": "Ambient temperature monitoring for welding area B2",
        "is_active": True,
        "meta_data": {"manufacturer": "Sensirion AG", "model": "SHT85", "firmware_version": "2.1.0"},
    },
    {
        "device_id": "humidity_sensor_warehouse",
        "device_name": "Humidity Sensor - Warehouse",
        "device_type": "sensor",
        "location": "Warehouse - Storage Bay 3",
        "description": "Humidity monitoring for raw material storage",
        "is_active": True,
        "meta_data": {"manufacturer": "Sensirion AG", "model": "SHT85", "firmware_version": "2.1.0"},
    },
    {
        "device_id": "pressure_sensor_line_c",
        "device_name": "Pressure Sensor - Production Line C",
        "device_type": "sensor",
        "location": "Factory Floor - Production Line C",
        "description": "Pneumatic pressure monitoring for assembly line C",
        "is_active": True,
        "meta_data": {"manufacturer": "Honeywell", "model": "PX3AN0BS100PSAAX", "firmware_version": "1.5.2"},
    },
    {
        "device_id": "motion_sensor_loading_dock",
        "device_name": "Motion Sensor - Loading Dock",
        "device_type": "sensor",
        "location": "Loading Dock - Bay 1",
        "description": "Vehicle and personnel movement detection at loading dock",
        "is_active": True,
        "meta_data": {"manufacturer": "Bosch Security", "model": "ISC-BPR2-W12", "firmware_version": "3.0.1"},
    },
    {
        "device_id": "temp_sensor_server_room",
        "device_name": "Temperature Sensor - Server Room",
        "device_type": "sensor",
        "location": "IT - Server Room",
        "description": "Critical temperature monitoring for server room cooling",
        "is_active": True,
        "meta_data": {"manufacturer": "Sensirion AG", "model": "STS40", "firmware_version": "1.3.0"},
    },
    {
        "device_id": "pressure_sensor_compressor",
        "device_name": "Pressure Sensor - Air Compressor",
        "device_type": "sensor",
        "location": "Utility Room - Compressor Station",
        "description": "Main air compressor output pressure monitoring",
        "is_active": True,
        "meta_data": {"manufacturer": "Honeywell", "model": "PX3AN0BS150PSAAX", "firmware_version": "1.5.2"},
    },
]

# ── Sensor reading generation config ─────────────────────────────────────────
# Maps device_id -> (sensor_type_name, unit, base_value, amplitude, noise)
DEVICE_SENSOR_MAP = {
    # Temperature sensors — daily sine wave + noise
    "temp_sensor_floor_a1":   ("temperature", "C", 23.0, 3.0, 0.5),
    "temp_sensor_floor_b2":   ("temperature", "C", 26.0, 4.0, 0.8),
    "temp_sensor_server_room":("temperature", "C", 20.0, 1.5, 0.3),
    # Humidity sensors
    "humidity_sensor_floor_a1":  ("humidity", "%", 50.0, 10.0, 2.0),
    "humidity_sensor_warehouse": ("humidity", "%", 55.0, 15.0, 3.0),
    # Pressure sensors
    "pressure_sensor_line_b":     ("pressure", "psi", 65.0, 8.0, 1.5),
    "pressure_sensor_line_c":     ("pressure", "psi", 72.0, 6.0, 1.0),
    "pressure_sensor_compressor": ("pressure", "psi", 110.0, 5.0, 2.0),
    # Motion sensors — random spikes
    "motion_sensor_entrance_1":    ("motion", "count", 0.0, 1.0, 0.0),
    "motion_sensor_loading_dock":  ("motion", "count", 0.0, 1.0, 0.0),
}

HOURS_OF_DATA = 72  # 3 days of historical data
READINGS_PER_HOUR = 6  # one reading every 10 minutes


def generate_value(sensor_type: str, base: float, amplitude: float, noise: float,
                   hour_of_day: int, minute: int) -> float:
    """Generate a realistic sensor value based on time of day."""
    t = (hour_of_day + minute / 60.0) / 24.0  # 0..1 fraction of day

    if sensor_type == "motion":
        # Motion: higher during work hours (6am-6pm), random spikes
        if 6 <= hour_of_day <= 18:
            return float(random.choices([0, 1, 2, 3, 5, 8], weights=[30, 25, 20, 15, 7, 3])[0])
        else:
            return float(random.choices([0, 1], weights=[85, 15])[0])

    # Continuous sensors: sine wave + noise
    # Peak at 2pm (hour 14), trough at 2am (hour 2)
    sine_val = math.sin(2 * math.pi * (t - 0.083))  # shift so peak ~ 14:00
    value = base + amplitude * sine_val + random.gauss(0, noise)

    if sensor_type == "humidity":
        value = max(10.0, min(95.0, value))
    elif sensor_type == "temperature":
        value = max(5.0, min(50.0, value))
    elif sensor_type == "pressure":
        value = max(0.0, min(200.0, value))

    return round(value, 2)


async def seed():
    async with async_session_factory() as db:
        # ── 1. Create extra devices ──────────────────────────────────────
        created_devices = 0
        for dev_data in EXTRA_DEVICES:
            result = await db.execute(
                select(MQTTDevice).where(MQTTDevice.device_id == dev_data["device_id"])
            )
            if not result.scalars().first():
                db.add(MQTTDevice(**dev_data))
                created_devices += 1
        await db.commit()
        print(f"Created {created_devices} new devices")

        # ── 2. Load lookup tables ────────────────────────────────────────
        # Devices
        result = await db.execute(select(MQTTDevice))
        devices = {d.device_id: d for d in result.scalars()}

        # Sensor types
        result = await db.execute(select(SSSensorType))
        sensor_types = {st.name: st for st in result.scalars()}

        # Sensors
        result = await db.execute(select(SSSensor))
        sensors = {s.sensor_id: s for s in result.scalars()}

        # Users (pick a user to attribute readings to)
        result = await db.execute(select(ACLUser).where(ACLUser.username == "erkam"))
        user = result.scalars().first()
        if not user:
            print("ERROR: No user found to attribute readings to")
            return

        # ── 3. Create sensors for new devices if missing ─────────────────
        created_sensors = 0
        for device_id, (type_name, *_) in DEVICE_SENSOR_MAP.items():
            if device_id not in sensors and device_id in devices:
                st = sensor_types.get(type_name)
                if st:
                    sensor = SSSensor(
                        sensor_id=device_id,
                        pattern=f"sf/sensors/{device_id}/{type_name}",
                        sensor_type_id=st.id,
                        is_active=True,
                    )
                    db.add(sensor)
                    created_sensors += 1
        await db.commit()
        print(f"Created {created_sensors} new sensors")

        # Reload sensors
        result = await db.execute(select(SSSensor))
        sensors = {s.sensor_id: s for s in result.scalars()}

        # ── 4. Generate sensor readings ──────────────────────────────────
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=HOURS_OF_DATA)
        total_readings = 0
        batch = []

        for device_id, (type_name, unit, base, amplitude, noise) in DEVICE_SENSOR_MAP.items():
            device = devices.get(device_id)
            sensor = sensors.get(device_id)
            st = sensor_types.get(type_name)

            if not device or not sensor or not st:
                print(f"  SKIP {device_id}: device={bool(device)} sensor={bool(sensor)} type={bool(st)}")
                continue

            t = start_time
            while t <= now:
                value = generate_value(type_name, base, amplitude, noise, t.hour, t.minute)

                reading = MQTTSensorReading(
                    device_id=device.id,
                    sensor_id=sensor.id,
                    sensor_type=st.id,
                    value=value,
                    unit=unit,
                    timestamp=t,
                    mqtt_topic=f"sf/sensors/{device_id}/{type_name}",
                    qos=1,
                    retain=False,
                    raw_data={"value": value, "unit": unit, "device_id": device_id},
                    user_id=user.id,
                )
                batch.append(reading)
                total_readings += 1

                # Flush in batches of 500
                if len(batch) >= 500:
                    db.add_all(batch)
                    await db.commit()
                    batch = []

                # Advance by ~10 minutes with slight jitter
                t += timedelta(minutes=10, seconds=random.randint(-30, 30))

            # Update device last_seen
            device.last_seen = now

        # Flush remaining
        if batch:
            db.add_all(batch)
            await db.commit()

        print(f"Generated {total_readings} sensor readings across {len(DEVICE_SENSOR_MAP)} devices")
        print(f"Time range: {start_time.isoformat()} → {now.isoformat()}")


if __name__ == "__main__":
    asyncio.run(seed())
