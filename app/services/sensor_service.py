import logging

from sqlalchemy.orm import Session

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.models.sensor import PoseDetection
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
    """슬라이딩 윈도우 + 회복 게이트 + 쿨다운 floor를 갖는 낙상 confirmed 여부 판정기.

    save() 시 in-memory 라이브 상태로도 쓰고, GET 시 과거 프레임을 재생할 때도 동일 로직으로 쓴다.
    """
    recent_states: deque = field(default_factory=lambda: deque(maxlen=FALL_WINDOW_SIZE))
    last_alert_at: datetime | None = None
    recovery_streak: int = 0
    has_recovered_since_alert: bool = False

    def consider(self, state: str, now: datetime) -> bool:
        """프레임 1개 처리. confirmed Falling이면 True, 아니면 False. 내부 상태도 갱신."""
        self.recent_states.append(state)

        if state in RECOVERY_STATES:
            self.recovery_streak += 1
            if self.recovery_streak >= RECOVERY_STREAK_REQUIRED:
                self.has_recovered_since_alert = True
        else:
            self.recovery_streak = 0

        if state != "Falling":
            return False

        falling_count = sum(1 for s in self.recent_states if s == "Falling")
        if falling_count < FALL_CONFIRM_COUNT:
            return False

        if self.last_alert_at is not None:
            if now - self.last_alert_at < ALERT_COOLDOWN_FLOOR:
                return False
            if not self.has_recovered_since_alert:
                return False

        self.last_alert_at = now
        self.recovery_streak = 0
        self.has_recovered_since_alert = False
        return True


# Per-device 알림 디바운스 상태. 단일 uvicorn worker 가정.
# 멀티 worker 환경으로 가면 Redis 등 외부 store 필요.
_fall_state_by_device: dict[str, _FallAlertState] = {}


def _replay_confirmed_fall_ids(records_asc: list[PoseDetection]) -> set[int]:
    """단일 디바이스의 시간 오름차순 레코드 시퀀스를 입력받아 confirmed Falling 레코드 ID 집합 반환.

    히스토리 조회 시 noise Falling 프레임을 응답에서 숨기기 위해 사용. DB는 raw 그대로 유지.
    """
    fs = _FallAlertState()
    confirmed: set[int] = set()
    for r in records_asc:
        if fs.consider(r.detected_state, r.created_at):
            confirmed.add(r.id)
    return confirmed


class PoseService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = PoseRepository(db)

    def save(self, data: PoseDetectionCreate) -> PoseDetectionResponse:
        record = self.repo.create(data)
        fs = _fall_state_by_device.setdefault(record.device_id, _FallAlertState())
        now = record.created_at or datetime.now(timezone.utc)
        if fs.consider(record.detected_state, now):
            try:
                send_fall_alert(self.db, record.device_id)
            except Exception:
                logger.exception("FCM alert failed for device %s — data saved", record.device_id)
        return PoseDetectionResponse.model_validate(record)

    def _all_confirmed_fall_ids(self) -> set[int]:
        """모든 디바이스의 confirmed Falling 레코드 ID 집합. /alerts, /pose/ 크로스-디바이스 응답 필터링용."""
        all_asc = self.repo.get_all_asc_by_device()
        by_device: dict[str, list[PoseDetection]] = defaultdict(list)
        for r in all_asc:
            by_device[r.device_id].append(r)
        confirmed: set[int] = set()
        for records in by_device.values():
            confirmed |= _replay_confirmed_fall_ids(records)
        return confirmed

    @staticmethod
    def _hide_noise_falls(records: list[PoseDetection], confirmed_fall_ids: set[int]) -> list[PoseDetection]:
        """Falling 중 confirmed가 아닌 것만 응답에서 제외. 다른 상태는 그대로."""
        return [r for r in records if r.detected_state != "Falling" or r.id in confirmed_fall_ids]

    def get_all(self) -> list[PoseDetectionResponse]:
        confirmed = self._all_confirmed_fall_ids()
        filtered = self._hide_noise_falls(self.repo.get_all(), confirmed)
        return [PoseDetectionResponse.model_validate(r) for r in filtered]

    def get_by_device(self, device_id: str) -> list[PoseDetectionResponse]:
        records_asc = self.repo.get_by_device_asc(device_id)
        confirmed = _replay_confirmed_fall_ids(records_asc)
        # 응답은 기존대로 desc. asc 시퀀스를 뒤집어서 반환.
        filtered_asc = self._hide_noise_falls(records_asc, confirmed)
        return [PoseDetectionResponse.model_validate(r) for r in reversed(filtered_asc)]

    def get_events(self, device_id: str) -> list[PoseDetectionResponse]:
        records = self.repo.get_by_device_asc(device_id)
        confirmed_falls = _replay_confirmed_fall_ids(records)
        events: list[PoseDetectionResponse] = []
        last_state: str | None = None
        last_time = None

        for i, record in enumerate(records):
            should_log = False

            # 낙상: confirmed 한 발사 프레임만 (1프레임 노이즈는 제외)
            if record.detected_state == "Falling":
                should_log = record.id in confirmed_falls

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
        confirmed = self._all_confirmed_fall_ids()
        filtered = self._hide_noise_falls(self.repo.get_alerts(), confirmed)
        return [PoseDetectionResponse.model_validate(r) for r in filtered]
