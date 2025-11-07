from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.security.ss_manager import get_ss_manager
from app.websocket.manager import get_websocket_manager

router = APIRouter(prefix="/api/ss", tags=["SS Management"])


# Request models
class AlertCheck(BaseModel):
    sensor_id: str
    value: str
    unit: str


class LimitConfig(BaseModel):
    name: str
    config: str


class AddSensor(BaseModel):
    sensor_id: str
    pattern: str
    sensor_type: str
    active: bool
    limits: Dict


class UpdateSensor(BaseModel):
    pattern: str
    sensor_type: str
    active: bool
    limits: Dict


# SS Information Endpoints
@router.get("/info")
async def get_ss_info():
    """Get SS configuration information"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    return ss.get_ss_info()


@router.get("/sensors")
async def get_all_sensors():
    """Get list of all sensors in SS"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    sensors_list = []
    for sensor_id in ss.sensors.keys():
        sensor_info = ss.get_sensor_info(sensor_id)
        if sensor_info:
            sensors_list.append(sensor_info)

    return {"sensors": sensors_list, "count": len(sensors_list)}


@router.get("/sensors/{sensors_id}")
async def get_sensor(sensor_id: str):
    """Get specific sensor's SS information"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    sensor_info = ss.get_sensor_info(sensor_id)
    if not sensor_info:
        raise HTTPException(
            status_code=404, detail=f"Sensor {sensor_id} not found in SS"
        )

    return sensor_info


# Alert Check Endpoint
@router.post("/check")
async def check_alert(check: AlertCheck):
    """Check sensor data for alert"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    alert, alert_type = ss.check_limit_for_alert(
        check.sensor_id, check.value, check.unit
    )

    if alert:
        ws_manager = get_websocket_manager()
        await ws_manager.broadcast_system_alert(
            "warning",
            "Sensor data from sensor {check.sensor_id} is outside of limits",
            {
                "sensor_id": check.sensor_id,
                "value": check.value,
                "unit": check.unit,
                "alert_type": alert_type,
            },
        )

    return {
        "sensor_id": check.sensor_id,
        "value": check.value,
        "unit": check.unit,
        "alert": alert,
        "alert_type": alert_type,
    }


# Sensor Management Endpoints
@router.post("/sensors")
async def add_sensor(sensor: AddSensor):
    """Add a new sensor to SS"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    # Check if sensor already exists
    if sensor.sensor_id in ss.sensors:
        raise HTTPException(
            status_code=400, detail=f"sensor {sensor.sensor_id} already exists"
        )

    # Validate type
    if sensor.sensor_type not in ss.types:
        raise HTTPException(
            status_code=400, detail=f"Type {sensor.sensor_type} does not exist"
        )

    ss.add_sensor(
        sensor.sensor_id,
        sensor.pattern,
        sensor.sensor_type,
        sensor.active,
        sensor.limits,
    )

    return {
        "message": f"sensor {sensor.sensor_id} created successfully",
        "sensor": ss.get_sensor_info(sensor.sensor_id),
    }


@router.put("/sensors/{sensor_id}")
async def update_sensor(sensor_id: str, update: UpdateSensor):
    """Update sensor"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="ss manager not available")

    if sensor_id not in ss.sensors:
        raise HTTPException(status_code=404, detail=f"sensor {sensor_id} not found")

    # Update type if provided
    if update.sensor_type is not None:
        # Validate type
        if update.sensor_type not in ss.types:
            raise HTTPException(
                status_code=400, detail=f"Type {update.sensor_type} does not exist"
            )
        ss.update_sensor(
            sensor_id, update.pattern, update.sensor_type, update.active, update.limits
        )

    return {
        "message": f"Sensor {sensor_id} updated successfully",
        "sensor": ss.get_sensor_info(sensor_id),
    }


@router.delete("/sensors/{sensor_id}")
async def delete_sensor(sensor_id: str):
    """Remove sensor from SS"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    if sensor_id not in ss.sensors:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")

    ss.remove_sensor(sensor_id)

    return {"message": f"Sensor {sensor_id} removed successfully"}


@router.post("/sensors/{sensor_id}/permissions")
async def add_sensor_limit_config(sensor_id: str, config: LimitConfig):
    """Add limit config to sensor"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="ss manager not available")

    if sensor_id not in ss.sensors:
        raise HTTPException(status_code=404, detail=f"sensor {sensor_id} not found")

    limit_config = {LimitConfig.name: {LimitConfig.config}}

    ss.add_sensor_limit_config(sensor_id, limit_config)

    return {
        "message": f"Limit config added to sensor {sensor_id}",
        "sensor": ss.get_sensor_info(sensor_id),
    }


# SS Reload Endpoint
@router.post("/reload")
async def reload_ss():
    """Manually trigger SS configuration reload"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="ss manager not available")

    ss.reload()

    return {
        "message": "SS configuration reloaded successfully",
        "info": ss.get_ss_info(),
    }


"""ss = get_ss_manager()
        if not ss:
            logger.warning("SS manager not available, can't check for alerts")
            return True
        
        parts = topic.split("/")
        if len(parts) >= 4:
            sensor_id = parts[-2]
        
        alert = ss.check_limit_for_alert(sensor_id, data["value"], data["unit"])

        if alert:
            ws_manager = get_websocket_manager()
            await ws_manager.broadcast_system_alert("warning", payload) """
