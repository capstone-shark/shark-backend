from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.routes import notification, sensor, test
from app.core.database import Base, engine
from app.core.limiter import limiter
from app.models import fcm_token  # noqa: F401

# DB 테이블 자동 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Shark Backend API",
    description="IoT 센서 데이터 수집 및 관리 API",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 라우터 등록
app.include_router(sensor.router, prefix="/api/v1")
app.include_router(test.router, prefix="/api/v1")
app.include_router(notification.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Shark Backend 작동 중"}


@app.get("/health")
def health():
    return {"status": "ok"}
