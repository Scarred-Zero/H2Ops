from typing import Optional, Dict
from pydantic import BaseModel, Field


class DeviceThresholds(BaseModel):
    ph_min: Optional[float] = Field(None, description="Minimum acceptable pH")
    ph_max: Optional[float] = Field(None, description="Maximum acceptable pH")
    turbidity_max_ntu: Optional[float] = Field(
        None, description="Maximum turbidity in NTU"
    )
    orp_min_mv: Optional[float] = Field(None, description="Minimum ORP in mV")
    # add other sensor thresholds as needed


class DeviceCreate(BaseModel):
    facility_id: str
    name: str
    device_type: str
    ph_setpoint: Optional[float] = 7.0
    thresholds: Optional[DeviceThresholds] = None


class DeviceRead(BaseModel):
    id: str
    facility_id: str
    name: str
    device_type: str
    ph_setpoint: float
    is_online: bool
    thresholds: Optional[DeviceThresholds] = None

    class Config:
        orm_mode = True
