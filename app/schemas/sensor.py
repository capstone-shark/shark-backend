from datetime import datetime
from pydantic import BaseModel


# 센서 데이터 생성 요청 시 받는 형식
class SensorDataCreate(BaseModel):
    device_id: str
    latitude: float
    longitude: float
    temperature: float | None = None


# 센서 데이터 응답 시 내보내는 형식
class SensorDataResponse(BaseModel):
    id: int
    device_id: str
    latitude: float
    longitude: float
    temperature: float | None
    created_at: datetime

    class Config:
        from_attributes = True
