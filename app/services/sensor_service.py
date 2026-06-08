import logging

from sqlalchemy.orm import Session

from collections import Counter
from datetime import timedelta

from app.repositories.sensor_repository import PoseRepository
from app.schemas.sensor import PoseDetectionCreate, PoseDetectionResponse
from app.services.notification_service import send_fall_alert

HEARTBEAT_SECONDS = 30
WINDOW_SIZE = 5
MAJORITY_THRESHOLD = 3

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

    def get_events(self, device_id: str) -> list[PoseDetectionResponse]:
        records = self.repo.get_by_device_asc(device_id)
        events: list[PoseDetectionResponse] = []
        last_state: str | None = None
        last_time = None

        for i, record in enumerate(records):
            should_log = False

            # 낙상: 즉시
            if record.detected_state == "Falling":
                should_log = True

            # 30초 heartbeat
            elif last_time is None or record.created_at - last_time >= timedelta(seconds=HEARTBEAT_SECONDS):
                should_log = True

            # 5프레임 중 3프레임 이상 새 상태면 자세 변경
            elif i >= WINDOW_SIZE - 1:
                window = records[i - WINDOW_SIZE + 1 : i + 1]
                counts = Counter(r.detected_state for r in window)
                majority_state, majority_count = counts.most_common(1)[0]
                if majority_count >= MAJORITY_THRESHOLD and majority_state != last_state:
                    should_log = True

            if should_log:
                events.append(PoseDetectionResponse.model_validate(record))
                last_state = record.detected_state
                last_time = record.created_at

        return list(reversed(events))

    def get_alerts(self) -> list[PoseDetectionResponse]:
        return [PoseDetectionResponse.model_validate(r) for r in self.repo.get_alerts()]
