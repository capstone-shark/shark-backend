from sqlalchemy.orm import Session

from app.repositories.sensor_repository import SensorRepository
from app.schemas.sensor import SensorDataCreate, SensorDataResponse


class SensorService:
    """비즈니스 로직을 담당하는 계층"""

    def __init__(self, db: Session):
        self.repo = SensorRepository(db)

    def save_sensor_data(self, data: SensorDataCreate) -> SensorDataResponse:
        sensor = self.repo.create(data)
        return SensorDataResponse.model_validate(sensor)

    def get_all_sensor_data(self) -> list[SensorDataResponse]:
        sensors = self.repo.get_all()
        return [SensorDataResponse.model_validate(s) for s in sensors]

    def get_sensor_data_by_device(self, device_id: str) -> list[SensorDataResponse]:
        sensors = self.repo.get_by_device(device_id)
        return [SensorDataResponse.model_validate(s) for s in sensors]
