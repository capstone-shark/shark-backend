from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator

PoseState = Literal["Stood", "Sat", "Lying", "Falling", "Walking"]


class PoseDetectionCreate(BaseModel):
    device_id: str
    sensor_timestamp: int
    detected_state: PoseState
    confidence: float
    probabilities: list[float]  # [Stood, Sat, Lying, Falling, Walking]

    @field_validator("probabilities")
    @classmethod
    def check_length(cls, v):
        if len(v) != 5:
            raise ValueError("probabilities must have 5 values")
        return v


class PoseDetectionResponse(BaseModel):
    id: int
    device_id: str
    sensor_timestamp: int
    detected_state: str
    confidence: float
    probabilities: list[float]
    created_at: datetime

    class Config:
        from_attributes = True
