from pydantic import BaseModel
from typing import Optional, Any


class UserRegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    turnstileToken: str


class UserVerifyRequest(BaseModel):
    token: str


class UserLoginRequest(BaseModel):
    email: str
    password: str
    turnstileToken: str


class Response(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
