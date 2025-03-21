from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response as _Response
from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from qcloud_cos import CosConfig, CosS3Client
from core.orm import *
from core.classes import *
from core.email import *
from core.utils import *
from datetime import datetime, timedelta
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

class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Any = await call_next(request)
        result = b""
        async for chunk in response.body_iterator:
            result += chunk
        log = Log(
            time=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            userAgent=request.headers.get("User-Agent", ""),
            ip=request.client.host if request.client else None,
            port=request.client.port if request.client else None,
            url=request.url.path,
            method=request.method,
            status=response.status_code,
            response=result.decode()
        )
        if request.url.path != "/api/logs/all":
            create_log(log)
        return _Response(
            content=result,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    
app.add_middleware(LogMiddleware)

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
        return Response(success=False, message="请通过人机验证。")
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
        expiry=int((datetime.now() + timedelta(minutes=5)).timestamp()),
    )
    try:
        exist = create_temporary_user(user)
        if not exist:
            return Response(success=False, message="用户已存在。")
        send_verification_email(request.email, request.username, token)
        return Response(
            success=True,
            message="用户创建成功。验证邮件已发送到你的邮箱。验证邮件在 5 分钟内有效。",
        )
    except Exception:
        return Response(success=False, message="创建用户失败。")


@app.post("/api/user/verify_email")
def _(request: UserVerifyRequest) -> Response:
    user = get_temp_user_by_token(request.token)
    if not user:
        return Response(success=False, message="令牌已过期。")
    remove_temporary_user(user)
    new_user = User(
        username=user.username,
        email=user.email,
        password=user.password,
    )
    result = create_user(new_user)
    if not result:
        return Response(success=False, message="创建用户失败。")
    return Response(success=True, message="用户验证成功。")


@app.post("/api/user/login")
def _(request: UserLoginRequest) -> JSONResponse:
    if not verify_turnstile_token(request.turnstileToken):
        return JSONResponse(
            Response(success=False, message="请通过人机验证。").model_dump()
        )
    user = get_user_by_email(request.email)
    temp_user = get_temp_user_by_email(request.email)
    if not user:
        if not temp_user:
            return JSONResponse(
                Response(success=False, message="用户未找到。").model_dump()
            )
        return JSONResponse(
            Response(success=False, message="用户未验证。").model_dump()
        )
    if verify_password(request.password, user.password):
        response = JSONResponse(
            Response(success=True, message="登录成功。").model_dump()
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
                Response(success=False, message="登陆失败。").model_dump()
            )
        response.set_cookie("WISMARTCOOKIE", cookie, expires=3600)
        return response
    return JSONResponse(
        Response(success=False, message="用户名或密码错误。").model_dump()
    )


@app.get("/api/user/logout")
def _(request: Request) -> JSONResponse:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return JSONResponse(Response(success=False, message="未登录。").model_dump())
    user = get_user_login_by_cookie(cookie)
    if not user:
        return JSONResponse(Response(success=False, message="未登录。").model_dump())
    result = remove_user_login(user)
    if not result:
        return JSONResponse(Response(success=False, message="登出失败。").model_dump())
    response = JSONResponse(Response(success=True, message="登出成功。").model_dump())
    response.delete_cookie("WISMARTCOOKIE")
    return response

@app.get("/api/user/all")
def _(request: Request) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    admin = False
    if cookie:
        login = get_user_login_by_cookie(cookie)
        user = get_user_by_email(login.email) if login else None
        if not user:
            return Response(success=False, message="未登录。")
        admin = verify_admin_by_email(user.email)
    if not admin:
        return Response(success=False, message="无访问权限。")
    db_users = get_all_users()
    users = [{"id": user.id,"email": user.email, "username": user.username} for user in db_users]
    return Response(success=True, data=users)

@app.get("/api/user/verify_login")
def _(request: Request) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=True, data=False)
    login = get_user_login_by_cookie(cookie)
    if not login:
        return Response(success=True, data=False)
    if login.time < int(datetime.now().timestamp()):
        return Response(success=True, data=False)
    return Response(success=True, data=True)


@app.get("/api/user/verify_admin")
def _(request: Request) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, data=False)
    login = get_user_login_by_cookie(cookie)
    if not login:
        return Response(success=False, data=False)
    admin = verify_admin_by_email(login.email)
    return Response(success=True, data=admin)


@app.post("/api/product/get")
def _(request: ProductFetchRequest) -> Response:
    types = [type.id for type in get_product_types()]
    if (
        request.page < 0
        or request.row < 1
        or request.row > 50
        or request.type
        and request.type not in types
        or request.keyword
        and request.keyword == ""
    ):
        return Response(success=False, message="参数错误。")
    types = get_product_types()
    products = get_products(request.page, request.row, request.type, request.keyword)
    config = CosConfig(
        Region=cos_region, SecretId=cos_secret_id, SecretKey=cos_secret_key
    )
    cos = CosS3Client(config)
    for product in products.products:
        product.image = get_presigned_url(product.image, cos) if product.image else None
    return Response(success=True, data=products)


@app.post("/api/product/detail")
def _(request: ProductDetailRequest) -> Response:
    product = get_product_by_id(request.id, True)
    if not product:
        return Response(success=False, message="无效的商品。")
    config = CosConfig(
        Region=cos_region, SecretId=cos_secret_id, SecretKey=cos_secret_key
    )
    cos = CosS3Client(config)
    product.image = get_presigned_url(product.image, cos) if product.image else None
    return Response(success=True, data=product)


@app.get("/api/product/all")
def _(request: Request) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    admin = False
    if cookie:
        login = get_user_login_by_cookie(cookie)
        user = get_user_by_email(login.email) if login else None
        if not user:
            return Response(success=False, message="未登录。")
        admin = verify_admin_by_email(user.email)
    if not admin:
        return Response(success=False, message="无访问权限。")
    products = get_all_products()
    config = CosConfig(
        Region=cos_region, SecretId=cos_secret_id, SecretKey=cos_secret_key
    )
    cos = CosS3Client(config)
    for product in products:
        product.image = get_presigned_url(product.image, cos) if product.image else None
    return Response(success=True, data=products)


@app.post("/api/product/new")
def _(request: Request, body: ProductCreateRequest) -> Response:
    if not verify_turnstile_token(body.turnstileToken):
        return Response(success=False, message="请通过人机验证。")
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    types = get_product_types()
    data = [type.id for type in types]
    if body.type not in data:
        return Response(success=False, message="无效的商品类型。")
    if body.price < 1 or (not body.isUnlimited and (not body.stock or body.stock < 1)):
        return Response(success=False, message="价格或库存错误。")
    product = Product(
        name=body.name,
        type=body.type,
        price=body.price,
        description=body.description,
        image=body.image,
        stock=body.stock,
        isUnlimited=body.isUnlimited,
        ownerId=user.id or -1,
        time=int(datetime.now().timestamp()),
    )
    result = create_product(product)
    if not result:
        return Response(success=False, message="创建商品失败。")
    return Response(success=True, message="商品创建成功。")


@app.get("/api/product/types")
def _() -> Response:
    return Response(success=True, data=get_product_types())


@app.get("/api")
@app.post("/api/cos/credential")
def _(request: Request, body: COSCredentialGenerateRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    _, ext = os.path.splitext(body.fileName)
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
        return Response(success=False, message="非法文件，禁止上传。")

    credential = get_temp_cos_security_token(ext)
    if not credential:
        return Response(success=False, message="获取临时密钥失败。")
    return Response(
        success=True, data={"region": cos_region, "bucket": cos_bucket, **credential}
    )


@app.post("/api/product/change")
def _(request: Request, body: ProductChangeRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    product = get_product_by_id(body.id, False)
    if not product:
        return Response(success=False, message="商品不存在或无访问权限。")
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    admin = verify_admin_by_email(user.email)
    if not admin and product.ownerId != user.id:
        return Response(success=False, message="商品不存在或无访问权限。")
    if product.isVerified != body.isVerified and not admin:
        return Response(success=False, message="商品不存在或无访问权限。")
    result = change_product(body)
    owner = get_user_by_id(product.ownerId)
    if not owner:
        return Response(success=False, message="失败。")
    if result:
        send_status_change_email(
            "商品状态更新", owner.email, body.details or "", owner.username
        )
        return Response(success=True, message="成功。")
    return Response(success=False, message="失败。")


@app.post("/api/product/remove")
def _(request: Request, body: ProductRemoveRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    admin = verify_admin_by_email(user.email)
    if not admin:
        return Response(success=False, message="无效的商品或无访问权限。")
    product = get_product_by_id(body.id, False)
    if not product:
        return Response(success=False, message="无效的商品或无访问权限。")
    owner = get_user_by_id(product.ownerId)
    if not owner:
        return Response(success=False, message="失败。")
    result = remove_product_by_id(body.id)
    if result:
        send_status_change_email(
            "商品状态更新",
            owner.email,
            f"你的商品“{product.name}”已被管理员删除。",
            owner.username,
        )
        return Response(success=True, message="成功。")
    return Response(success=False, message="失败。")


@app.post("/api/product/types/remove")
def _(request: Request, body: ProductTypeRemoveRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    admin = verify_admin_by_email(user.email)
    if not admin:
        return Response(success=False, message="无访问权限。")
    result = remove_product_type_by_id(body.id)
    if result:
        return Response(success=True, message="成功。")
    return Response(success=False, message="失败。")


@app.post("/api/product/types/new")
def _(request: Request, body: ProductTypeCreateRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    admin = verify_admin_by_email(user.email)
    if not admin:
        return Response(success=False, message="无访问权限。")
    product_type = ProductType(type=body.type)
    result = create_product_type(product_type)
    if result:
        return Response(success=True, message="成功。")
    return Response(success=False, message="失败。")


@app.post("/api/product/types/change")
def _(request: Request, body: ProductTypeChangeRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    admin = verify_admin_by_email(user.email)
    if not admin:
        return Response(success=False, message="无效的商品类型或无访问权限。")
    type = get_product_type_by_id(body.id)
    if not type:
        return Response(success=True, message="无效的商品类型或无访问权限。")
    result = change_product_type(body)
    if result:
        return Response(success=True, message="成功。")
    return Response(success=False, message="失败。")


@app.post("/api/product/buy")
def _(request: Request, body: ProductBuyRequest) -> Response:
    if not verify_turnstile_token(body.turnstileToken):
        return Response(success=False, message="请通过人机验证。")
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    buyer = get_user_by_email(login.email) if login else None
    if not buyer:
        return Response(success=False, message="未登录。")
    product = get_product_by_id(body.id, True)
    if not product:
        return Response(success=False, message="无效的商品。")
    if product.ownerId == buyer.id:
        return Response(success=False, message="你不能自己购买自己的商品。")
    if product.stock and product.stock - product.sales < body.count:
        return Response(success=False, message="无效的购买数量。")
    change_product(
        ProductChangeRequest(
            id=product.id or -1,
            isVerified=product.isVerified,
            stock=product.stock,
            sales=product.sales + body.count,
        )
    )
    seller = get_user_by_id(product.ownerId)
    if not seller:
        return Response(success=False, message="无效的商品所有者。")
    trade = Trade(
        buyerId=buyer.id or -1,
        sellerId=seller.id or -1,
        buyerEmail=buyer.email,
        sellerEmail=seller.email,
        productId=product.id or -1,
        count=body.count,
        total=body.count * product.price,
    )
    result = create_trade(trade)
    if not result:
        return Response(success=False, message="失败。")
    send_product_trade_email(
        seller.email,
        seller.username,
        body.count,
        product.name,
        buyer.username,
        seller.username,
        trade.total,
        product.price,
        buyer.email,
        seller.email,
        trade.id or -1,
    )
    send_product_trade_email(
        buyer.email,
        buyer.username,
        body.count,
        product.name,
        buyer.username,
        seller.username,
        trade.total,
        product.price,
        buyer.email,
        seller.email,
        trade.id or -1,
    )
    return Response(success=True, message="成功。")


@app.post("/api/trade/detail")
def _(request: Request, body: TradeDetailFetchRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    trade = get_trade_by_id(body.id)
    if not trade:
        return Response(success=False, message="交易不存在或无访问权限。")
    if trade.buyerId != user.id and trade.sellerId != user.id:
        return Response(success=False, message="交易不存在或无访问权限。")
    return Response(success=False, data=trade)


@app.post("/api/trade/change")
def _(request: Request, body: TradeChangeRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    trade = get_trade_by_id(body.id)
    if not trade:
        return Response(success=False, message="交易不存在或无访问权限。")
    if trade.buyerId != user.id and trade.sellerId != user.id:
        return Response(success=False, message="交易不存在或无访问权限。")
    if trade.status != "pending":
        return Response(success=False, message="交易已结束。")
    if trade.status == body.status:
        return Response(success=False, message="无效的操作。")
    seller = get_user_by_id(trade.sellerId)
    buyer = get_user_by_id(trade.buyerId)
    result = change_trade(body)
    if not result:
        return Response(success=False, message="失败。")
    product = get_product_by_id(body.id, False)
    if not product:
        return Response(success=False, message="失败。")
    if body.status == "canceled":
        product.sales -= trade.count
        change_product(
            ProductChangeRequest(
                id=product.id or -1,
                isVerified=product.isVerified,
                stock=product.stock,
                sales=product.sales,
            )
        )
    send_status_change_email(
        "交易状态更新",
        trade.sellerEmail,
        f"你的交易 #{trade.id} 已{'完成' if body.status == 'completed' else '取消'}。",
        seller.username if seller else "",
    )
    send_status_change_email(
        "交易状态更新",
        trade.buyerEmail,
        f"你的交易 #{trade.id} 已{'完成' if body.status == 'completed' else '取消'}。",
        buyer.username if buyer else "",
    )
    return Response(success=True, message="成功。")


@app.post("/api/user/profile")
def _(request: Request, body: UserProfileFetchRequest) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    user_info = get_user_by_id(body.id)
    if not user_info:
        return Response(success=False, message="用户不存在。")
    data = {
        "email": user_info.email,
        "id": user_info.id,
        "username": user_info.username,
    }
    return Response(success=True, data=data)

@app.get("/api/logs/all")
def _(request: Request) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=False, message="未登录。")
    login = get_user_login_by_cookie(cookie)
    user = get_user_by_email(login.email) if login else None
    if not user:
        return Response(success=False, message="未登录。")
    admin = verify_admin_by_email(user.email)
    if not admin:
        return Response(success=False, message="无访问权限。")
    return Response(success=True, data=get_all_logs())