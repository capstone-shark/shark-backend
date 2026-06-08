from sqlalchemy.orm import Session

from app.models.sensor import PoseDetection
from app.schemas.sensor import PoseDetectionCreate


class PoseRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: PoseDetectionCreate) -> PoseDetection:
        record = PoseDetection(**data.model_dump())
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_all(self) -> list[PoseDetection]:
        return self.db.query(PoseDetection).order_by(PoseDetection.created_at.desc()).all()

    def get_by_device(self, device_id: str) -> list[PoseDetection]:
        return (
            self.db.query(PoseDetection)
            .filter(PoseDetection.device_id == device_id)
            .order_by(PoseDetection.created_at.desc())
            .all()
        )

    def get_by_device_asc(self, device_id: str) -> list[PoseDetection]:
        return (
            self.db.query(PoseDetection)
            .filter(PoseDetection.device_id == device_id)
            .order_by(PoseDetection.created_at.asc())
            .all()
        )

    def get_alerts(self) -> list[PoseDetection]:
        """Falling 또는 Lying 상태만 반환"""
        return (
            self.db.query(PoseDetection)
            .filter(PoseDetection.detected_state.in_(["Falling", "Lying"]))
            .order_by(PoseDetection.created_at.desc())
            .all()
        )
