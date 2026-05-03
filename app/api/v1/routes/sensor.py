from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_api_key
from app.core.limiter import limiter
from app.schemas.sensor import PoseDetectionCreate, PoseDetectionResponse
from app.services.sensor_service import PoseService

router = APIRouter(prefix="/pose", tags=["pose"])


@router.post("/", response_model=PoseDetectionResponse)
@limiter.limit("120/minute")
def create(request: Request, data: PoseDetectionCreate, db: Session = Depends(get_db)):
    """라즈베리파이 → IoT Core → 여기로 자세 감지 결과 수신"""
    return PoseService(db).save(data)


@router.get("/", response_model=list[PoseDetectionResponse])
@limiter.limit("60/minute")
def get_all(request: Request, db: Session = Depends(get_db), _=Depends(verify_api_key)):
    return PoseService(db).get_all()


@router.get("/alerts", response_model=list[PoseDetectionResponse])
@limiter.limit("60/minute")
def get_alerts(request: Request, db: Session = Depends(get_db), _=Depends(verify_api_key)):
    """Falling / Lying 상태만 반환 (낙상 알림용)"""
    return PoseService(db).get_alerts()


@router.get("/{device_id}", response_model=list[PoseDetectionResponse])
@limiter.limit("60/minute")
def get_by_device(request: Request, device_id: str, db: Session = Depends(get_db), _=Depends(verify_api_key)):
    return PoseService(db).get_by_device(device_id)
