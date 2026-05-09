from sqlalchemy.orm import Session

from app.models.fcm_token import FCMToken


class FCMTokenRepository:

    def __init__(self, db: Session):
        self.db = db

    def upsert(self, token: str, device_name: str | None) -> FCMToken:
        existing = self.db.query(FCMToken).filter(FCMToken.token == token).first()
        if existing:
            return existing
        record = FCMToken(token=token, device_name=device_name)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_all_tokens(self) -> list[str]:
        return [row.token for row in self.db.query(FCMToken.token).all()]

    def delete_tokens(self, tokens: list[str]) -> None:
        if tokens:
            self.db.query(FCMToken).filter(FCMToken.token.in_(tokens)).delete(synchronize_session=False)
            self.db.commit()

    def delete_by_token(self, token: str) -> bool:
        deleted = self.db.query(FCMToken).filter(FCMToken.token == token).delete(synchronize_session=False)
        self.db.commit()
        return deleted > 0
