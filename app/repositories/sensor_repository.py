from sqlalchemy.orm import Session

from app.models.sensor import SensorData
from app.schemas.sensor import SensorDataCreate


class SensorRepository:
    """DB 쿼리만 담당하는 계층"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: SensorDataCreate) -> SensorData:
        sensor = SensorData(**data.model_dump())
        self.db.add(sensor)
        self.db.commit()
        self.db.refresh(sensor)
        return sensor

    def get_all(self) -> list[SensorData]:
        return self.db.query(SensorData).order_by(SensorData.created_at.desc()).all()

    def get_by_device(self, device_id: str) -> list[SensorData]:
        return (
            self.db.query(SensorData)
            .filter(SensorData.device_id == device_id)
            .order_by(SensorData.created_at.desc())
            .all()
        )
