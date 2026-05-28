import logging

from sqlalchemy.orm import Session

from app.repositories.sensor_repository import PoseRepository
from app.schemas.sensor import PoseDetectionCreate, PoseDetectionResponse
from app.services.notification_service import send_fall_alert

logger = logging.getLogger(__name__)


class PoseService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = PoseRepository(db)

    def save(self, data: PoseDetectionCreate) -> PoseDetectionResponse:
        record = self.repo.create(data)
        if record.detected_state == "Falling":
            try:
                send_fall_alert(self.db, record.device_id)
            except Exception:
                logger.exception("FCM alert failed for device %s — data saved", record.device_id)
        return PoseDetectionResponse.model_validate(record)

    def get_all(self) -> list[PoseDetectionResponse]:
        return [PoseDetectionResponse.model_validate(r) for r in self.repo.get_all()]

    def get_by_device(self, device_id: str) -> list[PoseDetectionResponse]:
        return [PoseDetectionResponse.model_validate(r) for r in self.repo.get_by_device(device_id)]

    def get_alerts(self) -> list[PoseDetectionResponse]:
        return [PoseDetectionResponse.model_validate(r) for r in self.repo.get_alerts()]
