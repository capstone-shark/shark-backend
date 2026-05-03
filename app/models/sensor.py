from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class PoseDetection(Base):
    __tablename__ = "pose_detections"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)
    sensor_timestamp = Column(BigInteger, nullable=False)
    detected_state = Column(String, nullable=False, index=True)  # Stood/Sat/Lying/Falling/Walking
    confidence = Column(Float, nullable=False)
    probabilities = Column(JSONB, nullable=False)  # [Stood, Sat, Lying, Falling, Walking]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
