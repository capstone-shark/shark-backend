import logging

from sqlalchemy.orm import Session

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.repositories.sensor_repository import PoseRepository
from app.schemas.sensor import PoseDetectionCreate, PoseDetectionResponse
from app.services.notification_service import send_fall_alert

HEARTBEAT_SECONDS = 30
WINDOW_SIZE = 5
MAJORITY_THRESHOLD = 3

# 낙상 알림 디바운스 파라미터 (모델 프레임레이트 2fps 기준).
# 5프레임 윈도우 ≈ 2.5초, 회복 5프레임 ≈ 2.5초.
FALL_WINDOW_SIZE = 5
FALL_CONFIRM_COUNT = 3
RECOVERY_STREAK_REQUIRED = 5
ALERT_COOLDOWN_FLOOR = timedelta(seconds=10)
RECOVERY_STATES = {"Stood", "Walking", "Sat"}

logger = logging.getLogger(__name__)


@dataclass
class _FallAlertState:
    recent_states: deque = field(default_factory=lambda: deque(maxlen=FALL_WINDOW_SIZE))
    last_alert_at: datetime | None = None
    recovery_streak: int = 0
    has_recovered_since_alert: bool = False


# Per-device 알림 디바운스 상태. 단일 uvicorn worker 가정.
# 멀티 worker 환경으로 가면 Redis 등 외부 store 필요.
_fall_state_by_device: dict[str, _FallAlertState] = {}


class PoseService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = PoseRepository(db)

    def save(self, data: PoseDetectionCreate) -> PoseDetectionResponse:
        record = self.repo.create(data)
        if self._should_fire_fall_alert(record.device_id, record.detected_state, record.created_at):
            try:
                send_fall_alert(self.db, record.device_id)
            except Exception:
                logger.exception("FCM alert failed for device %s — data saved", record.device_id)
        return PoseDetectionResponse.model_validate(record)

    def _should_fire_fall_alert(self, device_id: str, state: str, now: datetime | None) -> bool:
        """슬라이딩 윈도우 + 회복-게이트 + 쿨다운 floor로 낙상 알림 디바운스."""
        fs = _fall_state_by_device.setdefault(device_id, _FallAlertState())
        fs.recent_states.append(state)

        # 회복 추적: streak은 매 프레임 갱신, sticky flag는 알림 발사 시까지 유지
        if state in RECOVERY_STATES:
            fs.recovery_streak += 1
            if fs.recovery_streak >= RECOVERY_STREAK_REQUIRED:
                fs.has_recovered_since_alert = True
        else:
            fs.recovery_streak = 0

        if state != "Falling":
            return False

        falling_count = sum(1 for s in fs.recent_states if s == "Falling")
        if falling_count < FALL_CONFIRM_COUNT:
            return False

        now = now or datetime.now(timezone.utc)
        if fs.last_alert_at is not None:
            if now - fs.last_alert_at < ALERT_COOLDOWN_FLOOR:
                return False
            if not fs.has_recovered_since_alert:
                return False

        fs.last_alert_at = now
        fs.recovery_streak = 0
        fs.has_recovered_since_alert = False
        return True

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
