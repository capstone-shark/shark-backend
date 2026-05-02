from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class SensorData(Base):
    """IoT 센서로부터 수신한 데이터를 저장하는 테이블"""
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)  # IoT 디바이스 ID
    latitude = Column(Float, nullable=False)                # 위도
    longitude = Column(Float, nullable=False)               # 경도
    temperature = Column(Float, nullable=True)              # 수온
    created_at = Column(DateTime(timezone=True), server_default=func.now())
