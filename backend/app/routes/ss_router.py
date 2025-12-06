"""
SS (Sensor Security) API routes with database integration
"""

from fastapi import APIRouter, HTTPException, Depends
import traceback
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.managers.db_ss_manager import get_ss_manager
from app.websocket.manager import get_websocket_manager
from app.schemas.ss_schemas import AddSensor, UpdateSensor, AlertCheck, SensorLimit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ss", tags=["SS Management"])


# SS Information Endpoints
@router.get("/info")
async def get_ss_info(db: AsyncSession = Depends(get_db)):
    """Get SS configuration information"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")

        info = await ss.get_ss_info(db)
        return info
    except Exception as e:
        logger.error(f"Error in get_ss_info:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sensors")
async def get_all_sensors(
    check_activeness: bool = True, db: AsyncSession = Depends(get_db)
):
    """Get list of all sensors in SS"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")

        sensors = await ss.get_all_sensors(check_activeness, db)
        return sensors
    except Exception as e:
        logger.error(f"Error in get_all_sensors:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sensors/{sensor_id}")
async def get_sensor(sensor_id: str, db: AsyncSession = Depends(get_db)):
    """Get specific sensor's SS information"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")

        sensor_info = await ss.get_sensor_info(sensor_id, db)
        if not sensor_info:
            raise HTTPException(
                status_code=404, detail=f"Sensor {sensor_id} not found in SS"
            )

        return sensor_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_sensor:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_all_sensor_types(db: AsyncSession = Depends(get_db)):
    """Get all sensor types"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")

        types_dict = await ss.get_all_sensor_types(db)
        return types_dict
    except Exception as e:
        logger.error(f"Error in get_all_sensor_types:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Alert Check Endpoint
@router.post("/check")
async def check_alert(check: AlertCheck, db: AsyncSession = Depends(get_db)):
    """Check sensor data for alert"""
    try:
        ss = get_ss_manager()
        if not ss:
            raise HTTPException(status_code=503, detail="SS manager not available")

        alert_triggered, alert_type = await ss.check_limit_for_alert(
            check.sensor_id, float(check.value), check.unit, db
        )

        # Commit the alert if one was created
        await db.commit()

        if alert_triggered:
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
            "alert_triggered": alert_triggered,
            "alert_type": alert_type,
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in check_alert:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Sensor Management Endpoints
@router.post("/sensors")
async def add_sensor(sensor: AddSensor, db: AsyncSession = Depends(get_db)):
    """Add a new sensor to SS"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.add_sensor(
            sensor_id=sensor.sensor_id,
            pattern=sensor.pattern,
            sensor_type=sensor.sensor_type,
            active=sensor.is_active,
            limits=sensor.limits,
            db=db,
        )

        # Commit the new sensor
        await db.commit()

        return {
            "message": f"Sensor {sensor.sensor_id} created successfully",
            "sensor": await ss.get_sensor_info(sensor.sensor_id, db),
        }
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in add_sensor:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sensors/{sensor_id}")
async def update_sensor(
    sensor_id: str, update: UpdateSensor, db: AsyncSession = Depends(get_db)
):
    """Update sensor"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.update_sensor(
            sensor_id=sensor_id,
            pattern=update.pattern,
            sensor_type=update.sensor_type,
            active=update.is_active,
            limits=update.limits,
            db=db,
        )

        # Commit the update
        await db.commit()

        return {
            "message": f"Sensor {sensor_id} updated successfully",
            "sensor": await ss.get_sensor_info(sensor_id, db),
        }
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in update_sensor:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sensors/{sensor_id}")
async def delete_sensor(sensor_id: str, db: AsyncSession = Depends(get_db)):
    """Remove sensor from SS"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.remove_sensor(sensor_id, db)

        # Commit the deletion
        await db.commit()

        return {"message": f"Sensor {sensor_id} removed successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in delete_sensor:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# SS Reload Endpoint
@router.post("/reload")
async def reload_ss(db: AsyncSession = Depends(get_db)):
    """Manually trigger SS configuration reload"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.reload(db)

        return {
            "message": "SS configuration reloaded successfully",
            "info": await ss.get_ss_info(db),
        }
    except Exception as e:
        logger.error(f"Error in reload_ss:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Alerts Endpoints
@router.get("/alerts")
async def get_alerts(
    limit: int = 0, include_resolved: bool = True, db: AsyncSession = Depends(get_db)
):
    """Get recent alerts"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        alerts = await ss.get_alerts(limit, include_resolved, db)
        return alerts
    except Exception as e:
        logger.error(f"Error in get_alerts:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark an alert as resolved"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.resolve_alert(alert_id, db)

        # Commit the resolution
        await db.commit()

        return {"message": f"Alert {alert_id} resolved successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in resolve_alert:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/revert")
async def revert_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Revert an alert"""
    ss = get_ss_manager()
    if not ss:
        raise HTTPException(status_code=503, detail="SS manager not available")

    try:
        await ss.revert_alert(alert_id, db)

        # Commit the revert
        await db.commit()

        return {"message": f"Alert {alert_id} reverted successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in revert_alert:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
