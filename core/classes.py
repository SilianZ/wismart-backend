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
    page: int
    row: int
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

class ProductTypeRemoveRequest(BaseModel):
    type: str

class ProductTypeCreateRequest(BaseModel):
    type: str


class COSCredentialGenerateRequest(BaseModel):
    fileName: str


class ChangeProductRequest(BaseModel):
    id: int
    isVerified: bool
    stock: int
    sales: int
    details: str


class Response(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
