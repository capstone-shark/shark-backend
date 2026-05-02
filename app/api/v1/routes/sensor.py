from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.sensor import SensorDataCreate, SensorDataResponse
from app.services.sensor_service import SensorService

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("/", response_model=SensorDataResponse)
def create_sensor_data(data: SensorDataCreate, db: Session = Depends(get_db)):
    """센서 데이터 저장"""
    return SensorService(db).save_sensor_data(data)


@router.get("/", response_model=list[SensorDataResponse])
def get_all_sensor_data(db: Session = Depends(get_db)):
    """전체 센서 데이터 조회"""
    return SensorService(db).get_all_sensor_data()


@router.get("/{device_id}", response_model=list[SensorDataResponse])
def get_sensor_data_by_device(device_id: str, db: Session = Depends(get_db)):
    """특정 디바이스 센서 데이터 조회"""
    return SensorService(db).get_sensor_data_by_device(device_id)
