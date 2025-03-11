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


class ProductDetailRequest(BaseModel):
    id: int


class ProductFetchRequest(BaseModel):
    page: int
    row: int
    type: Optional[int] = None
    keyword: Optional[str] = None


class ProductCreateRequest(BaseModel):
    name: str
    type: int
    price: float
    description: str
    image: str | None
    stock: int | None
    isUnlimited: bool
    turnstileToken: str

class ProductTypeRemoveRequest(BaseModel):
    id: int

class ProductTypeCreateRequest(BaseModel):
    type: str


class COSCredentialGenerateRequest(BaseModel):
    fileName: str


class ProductChangeRequest(BaseModel):
    id: int
    isVerified: bool
    stock: int | None
    sales: int
    details: str

class ProductBuyRequest(BaseModel):
    id: int
    count: int


class Response(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
