from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

PoseState = Literal["Stood", "Sat", "Lying", "Falling", "Walking"]


class PoseDetectionCreate(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    sensor_timestamp: int = Field(gt=0)
    detected_state: PoseState
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: list[float]  # [Stood, Sat, Lying, Falling, Walking]

    @field_validator("probabilities")
    @classmethod
    def check_length(cls, v):
        if len(v) != 5:
            raise ValueError("probabilities must have 5 values")
        if any(p < 0.0 or p > 1.0 for p in v):
            raise ValueError("each probability must be between 0.0 and 1.0")
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
