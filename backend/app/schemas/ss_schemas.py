from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class AlertCheck(BaseModel):
    sensor_id: str
    value: str
    unit: str


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
