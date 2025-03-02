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


class ProductFetchRequest(BaseModel):
    page: int = 1
    row: int = 10
    type: Optional[str] = None
    keyword: Optional[str] = None

class ProductCreateRequest(BaseModel):
    name: str
    type: str
    price: float
    description: str
    image: str
    stock: int
    turnstileToken: str

class COSCredentialGenerateRequest(BaseModel):
    fileName: str


class Response(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
