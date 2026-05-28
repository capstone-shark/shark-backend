import json
import logging

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.fcm_token_repository import FCMTokenRepository

logger = logging.getLogger(__name__)

_firebase_initialized = False


def _init_firebase() -> None:
    global _firebase_initialized
    if _firebase_initialized:
        return
    if not settings.FIREBASE_CREDENTIALS:
        logger.warning("FIREBASE_CREDENTIALS not set — FCM disabled")
        return
    cred_dict = json.loads(settings.FIREBASE_CREDENTIALS)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    _firebase_initialized = True


def send_fall_alert(db: Session, device_id: str) -> None:
    _init_firebase()
    if not _firebase_initialized:
        return

    repo = FCMTokenRepository(db)
    tokens = repo.get_all_tokens()
    if not tokens:
        return

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(
            title="낙상 감지 경고",
            body=f"장치 {device_id}에서 낙상이 감지되었습니다.",
        ),
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="fall_alert_channel",
            ),
        ),
    )

    response = messaging.send_each_for_multicast(message)

    failed_tokens = [
        tokens[i]
        for i, result in enumerate(response.responses)
        if not result.success
    ]
    if failed_tokens:
        logger.info("Removing %d invalid FCM token(s)", len(failed_tokens))
        repo.delete_tokens(failed_tokens)
