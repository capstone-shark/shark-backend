from fastapi import APIRouter, Request

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/")
def test_connection(request: Request):
    """연결 확인용 엔드포인트 - Postman, 앱, 라즈베리파이 등에서 테스트용"""
    client_ip = request.client.host
    return {
        "message": "연결 성공! 🦈",
        "client_ip": client_ip,
    }
