from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.requests import Request
from contextlib import asynccontextmanager
from core.orm import *
from core.classes import *
from core.email import *
from core.utils import *
import hashlib
import random
import bcrypt


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler.start()
    create_db_and_tables()
    yield
    scheduler.shutdown()


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
async def _() -> RedirectResponse:
    return RedirectResponse("https://wismart.hfiuc.org")


@app.post("/api/user/register")
async def _(request: UserRegisterRequest) -> Response:
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
            success=True, message="用户创建成功！验证邮件已发送到您的邮箱。"
        )
    except Exception:
        return Response(success=False, message="创建用户失败！")


@app.post("/api/user/verify_email")
async def _(request: UserVerifyRequest) -> Response:
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
async def _(request: UserLoginRequest) -> JSONResponse:
    if not verify_turnstile_token(request.turnstileToken):
        return JSONResponse(
            Response(success=False, message="请通过人机验证！").model_dump()
        )
    user = get_user_by_email(request.email)
    if not user:
        return JSONResponse(
            Response(success=False, message="用户未找到！").model_dump()
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
            UserLogins(
                email=user.email,
                cookie=cookie,
                time=int((datetime.now() + timedelta(hours=1)).timestamp()),
            )
        )
        if not result:
            return JSONResponse(
                Response(success=False, message="登陆失败！").model_dump()
            )
        response.set_cookie("WISMARTCOOKIE", cookie, expires="1d")
        return response
    return JSONResponse(
        Response(success=False, message="用户名或密码错误！").model_dump()
    )

@app.post("/api/user/logout")
async def _(request: Request) -> JSONResponse:
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

@app.post("/api/user/verify_login")
async def _(request: Request) -> Response:
    cookie = request.cookies.get("WISMARTCOOKIE")
    if not cookie:
        return Response(success=True, data=False)
    user = get_user_login_by_cookie(cookie)
    if not user:
        return Response(success=True, data=False)
    if user.time < int(datetime.now().timestamp()):
        return Response(success=True, data=False)
    return Response(success=True, data=True)