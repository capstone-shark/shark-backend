from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.fcm_token_repository import FCMTokenRepository
from app.schemas.fcm_token import FCMTokenRegister, FCMTokenResponse

router = APIRouter(prefix="/tokens", tags=["notification"])


@router.post("/", response_model=FCMTokenResponse, status_code=201)
def register_token(body: FCMTokenRegister, db: Session = Depends(get_db)):
    """FCM 토큰 등록 (이미 있으면 그대로 반환)"""
    record = FCMTokenRepository(db).upsert(body.token, body.device_name)
    return FCMTokenResponse.model_validate(record)


@router.delete("/{token}", status_code=204)
def delete_token(token: str, db: Session = Depends(get_db)):
    """FCM 토큰 삭제"""
    deleted = FCMTokenRepository(db).delete_by_token(token)
    if not deleted:
        raise HTTPException(status_code=404, detail="Token not found")
