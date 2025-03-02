from sqlmodel import SQLModel, create_engine, Session, select
from sqlmodel import Field
from typing import Union, Optional, Sequence
from core.scheduler import scheduler
from core.env import *
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from pydantic import BaseModel



class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    email: str
    password: str
    isAdmin: bool = False


class TempUser(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str
    username: str
    password: str
    token: str


class UserLogin(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str
    cookie: str
    time: int

class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    type: str
    price: float
    description: str
    image: str
    stock: int
    sales: int = 0
    isVerified: bool = False
    ownerId: int | None


class ProductFetchResonse(BaseModel):
    products: Sequence[Product]
    maxPage: int
    page: int

class ProductType(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: str

engine = create_engine(database_url)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def create_temporary_user(user: TempUser) -> bool:
    with Session(engine) as session:
        existing_user = session.exec(
            select(User).where(User.email == user.email or User.username == user.username)
        ).first()
        existing_temp_user = session.exec(
            select(TempUser).where(TempUser.email == user.email or TempUser.username == user.username)
        ).first()
        if existing_temp_user or existing_user:
            return False
        session.add(user)
        session.commit()
        delete_time = datetime.now() + timedelta(minutes=5)
        scheduler.add_job(
            remove_temporary_user,
            trigger=CronTrigger(
                year=delete_time.year,
                month=delete_time.month,
                day=delete_time.day,
                hour=delete_time.hour,
                minute=delete_time.minute,
                second=delete_time.second,
            ),
            args=[user],
        )
        return True


def create_user(user: User) -> bool:
    try:
        with Session(engine) as session:
            session.add(user)
            session.commit()
            return True
    except Exception:
        return False


def create_user_login(user: UserLogin) -> bool:
    try:
        with Session(engine) as session:
            session.add(user)
            session.commit()
            return True
    except Exception:
        return False


def remove_user_login(user: UserLogin) -> bool:
    try:
        with Session(engine) as session:
            session.delete(user)
            session.commit()
            return True
    except Exception:
        return False


def get_user_login_by_cookie(cookie: str) -> Union[UserLogin, None]:
    with Session(engine) as session:
        return session.exec(
            select(UserLogin).where(UserLogin.cookie == cookie)
        ).first()


def remove_temporary_user(user: TempUser) -> None:
    try:
        with Session(engine) as session:
            session.delete(user)
            session.commit()
    except Exception:
        pass
 

def get_user_by_email(email: str) -> Union[User, None]:
    with Session(engine) as session:
        return session.exec(select(User).where(User.email == email)).first()


def get_temp_user_by_token(token: str) -> Union[TempUser, None]:
    with Session(engine) as session:
        return session.exec(select(TempUser).where(TempUser.token == token)).first()

def get_products(page: int, row: int, type: Optional[str] = None, keyword: Optional[str] = None) -> ProductFetchResonse:
    with Session(engine) as session:
        query = select(Product).where(Product.isVerified == True)
        if type:
            query = query.where(Product.type == type)
        if keyword:
            query = query.where(keyword in Product.name or keyword in Product.description or keyword == str(Product.id))
        return ProductFetchResonse(products=session.exec(query.offset((page - 1) * row).limit(row)).all(), maxPage=len(session.exec(select(Product)).all()) // row + 1, page=page)
    
def create_product(product: Product) -> bool:
    try:
        with Session(engine) as session:
            session.add(product)
            session.commit()
            return True
    except Exception:
        return False
    
def get_product_types() -> Sequence[ProductType]:
    with Session(engine) as session:
        return session.exec(select(ProductType)).all()