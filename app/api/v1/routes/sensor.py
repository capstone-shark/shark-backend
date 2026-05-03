from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.sensor import PoseDetectionCreate, PoseDetectionResponse
from app.services.sensor_service import PoseService

router = APIRouter(prefix="/pose", tags=["pose"])


@router.post("/", response_model=PoseDetectionResponse)
def create(data: PoseDetectionCreate, db: Session = Depends(get_db)):
    """라즈베리파이 → IoT Core → 여기로 자세 감지 결과 수신"""
    return PoseService(db).save(data)


@router.get("/", response_model=list[PoseDetectionResponse])
def get_all(db: Session = Depends(get_db)):
    return PoseService(db).get_all()


@router.get("/alerts", response_model=list[PoseDetectionResponse])
def get_alerts(db: Session = Depends(get_db)):
    """Falling / Lying 상태만 반환 (낙상 알림용)"""
    return PoseService(db).get_alerts()


@router.get("/{device_id}", response_model=list[PoseDetectionResponse])
def get_by_device(device_id: str, db: Session = Depends(get_db)):
    return PoseService(db).get_by_device(device_id)
