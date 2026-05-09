from pydantic import BaseModel


class FCMTokenRegister(BaseModel):
    token: str
    device_name: str | None = None


class FCMTokenResponse(BaseModel):
    id: int
    token: str
    device_name: str | None

    model_config = {"from_attributes": True}
