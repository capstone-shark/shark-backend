import logging

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_api_key
from app.core.limiter import limiter
from app.core.websocket_manager import manager
from app.schemas.sensor import PoseDetectionCreate, PoseDetectionResponse
from app.services.sensor_service import PoseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pose", tags=["pose"])


@router.post("/", response_model=PoseDetectionResponse)
@limiter.limit("120/minute")
async def create(request: Request, data: PoseDetectionCreate, db: Session = Depends(get_db)):
    """라즈베리파이 → IoT Core → 여기로 자세 감지 결과 수신. 저장 후 WS 구독자에게 broadcast."""
    response = PoseService(db).save(data)
    await manager.broadcast(response.model_dump(mode="json"), device_id=response.device_id)
    return response


@router.websocket("/ws")
async def stream(websocket: WebSocket, api_key: str = Query(...), device_id: str | None = Query(default=None)):
    """포즈 데이터 실시간 스트림.

    - `api_key`: HTTP의 `X-API-Key`와 동일
    - `device_id`: 선택, 지정 시 해당 디바이스 이벤트만 수신
    """
    if not settings.API_KEY or api_key != settings.API_KEY:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, device_id=device_id)
    try:
        while True:
            # 클라이언트가 끊을 때까지 대기. ping/pong은 ASGI 레이어에서 처리.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WS handler error")
    finally:
        await manager.disconnect(websocket, device_id=device_id)


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
