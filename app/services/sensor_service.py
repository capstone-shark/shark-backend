from sqlalchemy.orm import Session

from app.repositories.sensor_repository import PoseRepository
from app.schemas.sensor import PoseDetectionCreate, PoseDetectionResponse


class PoseService:

    def __init__(self, db: Session):
        self.repo = PoseRepository(db)

    def save(self, data: PoseDetectionCreate) -> PoseDetectionResponse:
        record = self.repo.create(data)
        return PoseDetectionResponse.model_validate(record)

    def get_all(self) -> list[PoseDetectionResponse]:
        return [PoseDetectionResponse.model_validate(r) for r in self.repo.get_all()]

    def get_by_device(self, device_id: str) -> list[PoseDetectionResponse]:
        return [PoseDetectionResponse.model_validate(r) for r in self.repo.get_by_device(device_id)]

    def get_alerts(self) -> list[PoseDetectionResponse]:
        return [PoseDetectionResponse.model_validate(r) for r in self.repo.get_alerts()]
