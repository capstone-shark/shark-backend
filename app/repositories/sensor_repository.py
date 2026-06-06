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

    def get_all_asc_by_device(self) -> list[PoseDetection]:
        """전체 레코드를 (device_id, created_at) 오름차순으로. 디바이스별 디바운스 재생용."""
        return (
            self.db.query(PoseDetection)
            .order_by(PoseDetection.device_id, PoseDetection.created_at.asc())
            .all()
        )

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
