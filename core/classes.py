from pydantic import BaseModel
from fastapi import Request
from typing import Optional, Any


class UserRegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    turnstileToken: str
    request: Request


class UserVerifyRequest(BaseModel):
    token: str
    request: Request


class UserLoginRequest(BaseModel):
    email: str
    password: str
    turnstileToken: str
    request: Request


class ProductFetchRequest(BaseModel):
    page: int = 1
    row: int = 10
    type: Optional[str] = None
    keyword: Optional[str] = None
    request: Request

class ProductCreateRequest(BaseModel):
    name: str
    type: str
    price: float
    description: str
    image: str
    stock: int
    request: Request
    turnstileToken: str

class COSCredentialGenerateRequest(BaseModel):
    fileName: str
    request: Request


class Response(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
