"""
Pydantic schemas for MQTT API endpoints
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# Request Schemas
class SensorDataRequest(BaseModel):
    """Schema for publishing sensor data"""

    device_id: str = Field(..., description="Unique device identifier")
    sensor_id: int = Field(..., description="Sensor database ID")
    sensor_type_id: int = Field(..., description="Sensor type database ID")
    value: float = Field(..., description="Sensor reading value")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: Optional[str] = Field(None, description="ISO format timestamp")
    user_id: int = Field(..., description="User ID who published this reading")
    qos: Optional[int] = Field(1, description="MQTT QoS level (0, 1, or 2)")
    retain: Optional[bool] = Field(False, description="MQTT retain flag")


class CommandRequest(BaseModel):
    """Schema for sending commands to devices"""

    device_id: str = Field(..., description="Target device identifier")
    command: str = Field(..., description="Command name/type")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Command parameters")
    user_id: int = Field(..., description="User ID who sent the command")
    qos: Optional[int] = Field(1, description="MQTT QoS level (0, 1, or 2)")
    retain: Optional[bool] = Field(False, description="MQTT retain flag")


class CommandStatusUpdate(BaseModel):
    """Schema for updating command status"""

    status: str = Field(
        ..., description="Command status (sent, acknowledged, executed, failed)"
    )
    response_data: Optional[Dict[str, Any]] = Field(
        None, description="Response data from device"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")


class DeviceCreate(BaseModel):
    """Schema for creating a new device"""

    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Human-readable device name")
    device_type: str = Field(..., description="Device type (sensor, actuator, gateway)")
    location: Optional[str] = Field(None, description="Physical location")
    description: Optional[str] = Field(None, description="Device description")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DeviceUpdate(BaseModel):
    """Schema for updating device information"""

    device_name: Optional[str] = Field(None, description="Human-readable device name")
    device_type: Optional[str] = Field(
        None, description="Device type (sensor, actuator, gateway)"
    )
    location: Optional[str] = Field(None, description="Physical location")
    description: Optional[str] = Field(None, description="Device description")
    is_active: Optional[bool] = Field(None, description="Device active status")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SessionCreate(BaseModel):
    """Schema for creating MQTT session"""

    user_id: int = Field(..., description="User ID")
    client_id: str = Field(..., description="MQTT client ID")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    subscribed_topics: Optional[List[str]] = Field(
        None, description="Initially subscribed topics"
    )
    connection_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional connection metadata"
    )


# Response Schemas
class DeviceResponse(BaseModel):
    """Schema for device response"""

    id: int
    device_id: str
    device_name: Optional[str]
    device_type: Optional[str]
    location: Optional[str]
    description: Optional[str]
    is_active: bool
    last_seen: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    meta_data: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class DeviceWithStats(DeviceResponse):
    """Device response with additional statistics"""

    sensor_readings_count: Optional[int] = 0
    commands_count: Optional[int] = 0
    latest_reading: Optional[str] = None


class SensorReadingResponse(BaseModel):
    """Schema for sensor reading response"""

    id: int
    device_id: int
    device_name: Optional[str]
    device_identifier: Optional[str]
    sensor_id: int
    sensor_identifier: Optional[str]
    sensor_pattern: Optional[str]
    sensor_type_id: int
    sensor_type_name: Optional[str]
    value: float
    unit: str
    timestamp: str
    mqtt_topic: str
    qos: int
    retain: bool
    raw_data: Optional[Dict[str, Any]]
    user_id: int
    username: Optional[str]

    class Config:
        from_attributes = True


class CommandResponse(BaseModel):
    """Schema for command response"""

    id: int
    device_id: int
    device_name: Optional[str]
    device_identifier: Optional[str]
    command: str
    parameters: Optional[Dict[str, Any]]
    status: str
    sent_at: str
    acknowledged_at: Optional[str]
    executed_at: Optional[str]
    mqtt_topic: str
    qos: int
    retain: bool
    user_id: int
    username: Optional[str]
    response_data: Optional[Dict[str, Any]]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Schema for session response"""

    id: int
    user_id: int
    username: Optional[str]
    user_email: Optional[str]
    client_id: str
    connected_at: str
    disconnected_at: Optional[str]
    is_active: bool
    last_activity: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    subscribed_topics: List[str]
    connection_metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    """Schema for device list response"""

    devices: List[DeviceWithStats]
    count: int


class SensorReadingListResponse(BaseModel):
    """Schema for sensor reading list response"""

    readings: List[SensorReadingResponse]
    count: int


class CommandListResponse(BaseModel):
    """Schema for command list response"""

    commands: List[CommandResponse]
    count: int


class SessionListResponse(BaseModel):
    """Schema for session list response"""

    sessions: List[SessionResponse]
    count: int


class MQTTStatsResponse(BaseModel):
    """Schema for MQTT statistics response"""

    total_devices: int
    active_devices: int
    total_readings: int
    total_commands: int
    readings_24h: int
    commands_24h: int
    active_sessions: int
    most_active_devices: List[Dict[str, Any]]


class SuccessResponse(BaseModel):
    """Generic success response"""

    message: str
    data: Optional[Dict[str, Any]] = None
