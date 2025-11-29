from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import traceback, logging
from app.security.db_ss_manager import get_ss_manager
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


class SensorLimit(BaseModel):
    id: Optional[int] = None
    name: str
    upper_limit: float
    lower_limit: float
    unit: str
    is_selected: bool


class AddSensor(BaseModel):
    sensor_id: str
    pattern: str
    sensor_type: str
    is_active: bool
    limits: List[SensorLimit]


class UpdateSensor(BaseModel):
    pattern: str
    sensor_type: str
    is_active: bool
    limits: List[SensorLimit]


# SS Information Endpoints
@router.get("/info")
async def get_ss_info():
    """Get SS configuration information"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")
        return await ss.get_ss_info()
    except Exception as e:
        logging.error(f"Error in get_ss_info:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sensors")
async def get_all_sensors(checkActiveness: bool = True):
    """Get list of all sensors in SS"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")
        return await ss.get_all_sensors(checkActiveness)
    except Exception as e:
        logging.error(f"Error in get_all_sensors:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sensors/{sensor_id}")
async def get_sensor(sensor_id: str):
    """Get specific sensor's SS information"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")

        sensor_info = await ss.get_sensor_info(sensor_id)
        if not sensor_info:
            raise HTTPException(
                status_code=404, detail=f"Sensor {sensor_id} not found in SS"
            )

        return sensor_info
    except Exception as e:
        logging.error(f"Error in get_sensor:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_all_sensor_types():
    """Get all sensor types"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")

        types_dict = await ss.get_all_sensor_types()
        return types_dict
    except Exception as e:
        logging.error(f"Error in get_all_sensor_types:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Alert Check Endpoint
@router.post("/check")
async def check_alert(check: AlertCheck):
    """Check sensor data for alert"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")

        alert, alert_type = await ss.check_limit_for_alert(
            check.sensor_id, float(check.value), check.unit
        )

        if alert:
            ws_manager = get_websocket_manager()
            await ws_manager.broadcast_system_alert(
                "warning",
                f"Sensor data from sensor {check.sensor_id} is outside of limits",
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
    except Exception as e:
        logging.error(f"Error in check_alert:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Sensor Management Endpoints
@router.post("/sensors")
async def add_sensor(sensor: AddSensor):
    """Add a new sensor to SS"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.add_sensor(
            sensor.sensor_id,
            sensor.pattern,
            sensor.sensor_type,
            sensor.is_active,
            sensor.limits,
        )

        return {
            "message": f"sensor {sensor.sensor_id} created successfully",
            "sensor": await ss.get_sensor_info(sensor.sensor_id),
        }
    except Exception as e:
        logging.error(f"Error in add_sensor:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sensors/{sensor_id}")
async def update_sensor(sensor_id: str, update: UpdateSensor):
    """Update sensor"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.update_sensor(
            sensor_id,
            update.pattern,
            update.sensor_type,
            update.is_active,
            update.limits,
        )

        return {
            "message": f"Sensor {sensor_id} updated successfully",
            "sensor": await ss.get_sensor_info(sensor_id),
        }
    except Exception as e:
        logging.error(f"Error in update_sensor:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sensors/{sensor_id}")
async def delete_sensor(sensor_id: str):
    """Remove sensor from SS"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.remove_sensor(sensor_id)
        return {"message": f"Sensor {sensor_id} removed successfully"}
    except Exception as e:
        logging.error(f"Error in delete_sensor:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# SS Reload Endpoint
@router.post("/reload")
async def reload_ss():
    """Manually trigger SS configuration reload"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.reload()

        return {
            "message": "SS configuration reloaded successfully",
            "info": await ss.get_ss_info(),
        }
    except Exception as e:
        logging.error(f"Error in reload_ss:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Alerts Endpoints
@router.get("/alerts")
async def get_alerts(limit: int = 0, include_resolved: bool = True):
    """Get recent alerts"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        alerts = await ss.get_alerts(limit, include_resolved)
        return alerts
    except Exception as e:
        logging.error(f"Error in get_recent_alerts:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Mark an alert as resolved"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.resolve_alert(alert_id)
        return True
    except Exception as e:
        logging.error(f"Error in resolve_alert:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/revert")
async def revert_alert(alert_id: int):
    """Revert an alert"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.revert_alert(alert_id)
        return True
    except Exception as e:
        logging.error(f"Error in revert_alert:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
