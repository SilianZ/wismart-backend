from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.requests import Request
from contextlib import asynccontextmanager
from qcloud_cos import CosConfig, CosS3Client
from core.orm import *
from core.classes import *
from core.email import *
from core.utils import *
import hashlib
import random
import os
import bcrypt


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("Starting up...")
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://wismart.hfiuc.org"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@app.get("/")
def _() -> RedirectResponse:
    return RedirectResponse("https://wismart.hfiuc.org")


@app.post("/api/user/register")
def _(request: UserRegisterRequest) -> Response:
    if not verify_turnstile_token(request.turnstileToken):
        return Response(success=False, message="请通过人机验证！")
    token = hashlib.md5(
        (
            request.email + request.username + str(random.randint(100000, 999999))
        ).encode()
    ).hexdigest()
    user = TempUser(
        email=request.email,
        username=request.username,
        password=password_hash(request.password),
        token=token,
    )
    try:
        exist = create_temporary_user(user)
        if not exist:
            return Response(success=False, message="用户已存在！")
        send_verification_email(request.email, request.username, token)
        return Response(
            success=True, message="用户创建成功！验证邮件已发送到你的邮箱。"
        )
    except Exception:
        return Response(success=False, message="创建用户失败！")


@app.post("/api/user/verify_email")
def _(request: UserVerifyRequest) -> Response:
    user = get_temp_user_by_token(request.token)
    if not user:
        return Response(success=False, message="令牌已过期！")
    remove_temporary_user(user)
    new_user = User(
        username=user.username,
        email=user.email,
        password=user.password,
    )
    result = create_user(new_user)
    if not result:
        return Response(success=False, message="创建用户失败！")
    return Response(success=True, message="用户验证成功！")


@app.post("/api/user/login")
def _(request: UserLoginRequest) -> JSONResponse:
    if not verify_turnstile_token(request.turnstileToken):
        return JSONResponse(
            Response(success=False, message="请通过人机验证！").model_dump()
        )
    user = get_user_by_email(request.email)
    temp_user = get_temp_user_by_email(request.email)
    if not user:
        if not temp_user:
            return JSONResponse(
                Response(success=False, message="用户未找到！").model_dump()
            )
        return JSONResponse(
            Response(success=False, message="用户未验证！").model_dump()
        )
    if verify_password(request.password, user.password):
        response = JSONResponse(
            Response(success=True, message="登录成功！").model_dump()
        )
        cookie = hashlib.md5(
            (
                user.password
                + user.email
                + user.username
                + str(random.randint(100000, 999999))
            ).encode()
        ).hexdigest()
        result = create_user_login(
            UserLogin(
                email=user.email,
                cookie=cookie,
                time=int((datetime.now() + timedelta(hours=1)).timestamp()),
            )
        )
        if not result:
            return JSONResponse(
                Response(success=False, message="登陆失败！").model_dump()
            )
        response.set_cookie("WISMARTCOOKIE", cookie, expires=3600)
        return response
    return JSONResponse(
        Response(success=False, message="用户名或密码错误！").model_dump()
    )


@app.get("/api/user/logout")
def _(request: Request) -> JSONResponse:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return JSONResponse(Response(success=False, message="未登录！").model_dump())
    user = get_user_login_by_cookie(cookie)
    if not user:
        return JSONResponse(Response(success=False, message="未登录！").model_dump())
    result = remove_user_login(user)
    if not result:
        return JSONResponse(Response(success=False, message="登出失败！").model_dump())
    response = JSONResponse(Response(success=True, message="登出成功！").model_dump())
    response.delete_cookie("WISMARTCOOKIE")
    return response


@app.get("/api/user/verify_login")
def _(request: Request) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=True, data=False)
    user = get_user_login_by_cookie(cookie)
    if not user:
        return Response(success=True, data=False)
    if user.time < int(datetime.now().timestamp()):
        return Response(success=True, data=False)
    return Response(success=True, data=True)


@app.post("/api/product/get")
def _(request: ProductFetchRequest) -> Response:
    if (
        request.page < 0
        or request.row < 1
        or request.row > 50
        or request.type and request.type not in ["book", "clothing", "electronics", "food", "other"]
    ):
        return Response(success=False, message="参数错误！")
    products = get_products(request.page or 1, request.row or 10, request.type, request.keyword)
    config = CosConfig(Region=cos_region, SecretId=cos_secret_id, SecretKey=cos_secret_key)
    cos = CosS3Client(config)
    for product in products.products:
        product.image = get_presigned_url(product.image, cos) or ""
    print(products)
    return Response(success=True, data=products)


@app.post("/api/product/new")
def _(request: Request, body: ProductCreateRequest) -> Response:
    if not verify_turnstile_token(body.turnstileToken):
        return Response(success=False, message="请通过人机验证！")
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录！")
    user = get_user_login_by_cookie(cookie)
    if not user:
        return Response(success=False, message="未登录！")
    types = get_product_types()
    data = [type.type for type in types]
    if body.type not in data:
        return Response(success=False, message="无效的商品类型！")
    if body.price < 1 or body.stock < 1:
        return Response(success=False, message="价格或库存错误！")
    product = Product(
        name=body.name,
        type=body.type,
        price=body.price,
        description=body.description,
        image=body.image,
        stock=body.stock,
        ownerId=user.id,
    )
    result = create_product(product)
    if not result:
        return Response(success=False, message="创建商品失败！")
    return Response(success=True, message="商品创建成功！")


@app.get("/api/product/types")
def _() -> Response:
    types = get_product_types()
    data = [type.type for type in types]
    return Response(success=True, data=data)


@app.post("/api/cos/credential")
def _(request: Request, body: COSCredentialGenerateRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录！")
    user = get_user_login_by_cookie(cookie)
    if not user:
        return Response(success=False, message="未登录！")
    _, ext = os.path.splitext(body.fileName)
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
        return Response(success=False, message="非法文件，禁止上传！")

    credential = get_temp_cos_security_token(ext)
    if not credential:
        return Response(success=False, message="获取临时密钥失败！")
    return Response(
        success=True, data={"region": cos_region, "bucket": cos_bucket, **credential}
    )
