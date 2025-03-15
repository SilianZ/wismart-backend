from sqlmodel import SQLModel, create_engine, Session, select, or_, column
from sqlmodel import Field
from typing import Union, Optional, Sequence, Literal
from core.env import *
from pydantic import BaseModel
from core.classes import *
from datetime import datetime

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
    expiry: int


class UserLogin(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str
    cookie: str
    time: int


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    type: int
    price: float
    description: str
    image: str | None
    stock: int | None
    sales: int = 0
    isVerified: bool = False
    isUnlimited: bool = False
    ownerId: int
    time: int


class ProductFetchResonse(BaseModel):
    products: Sequence[Product]
    maxPage: int
    page: int


class ProductType(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: str


class Trade(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    buyerId: int
    sellerId: int
    buyerEmail: str
    sellerEmail: str
    productId: int
    count: int
    total: float
    status: str = "pending"


engine = create_engine(database_url)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def create_temporary_user(user: TempUser) -> bool:
    with Session(engine) as session:
        existing_user = session.exec(
            select(User).where(
                or_(User.email == user.email, User.username == user.username)
            )
        ).first()
        existing_temp_user = session.exec(
            select(TempUser).where(
                or_(TempUser.email == user.email, TempUser.username == user.username)
            )
        ).first()
        if existing_temp_user or existing_user:
            return False
        session.add(user)
        session.commit()
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
        return session.exec(select(UserLogin).where(UserLogin.cookie == cookie)).first()


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
        return session.exec(select(TempUser).where(TempUser.token == token).where(TempUser.expiry >= datetime.now().timestamp())).first()


def get_temp_user_by_email(email: str) -> Union[TempUser, None]:
    with Session(engine) as session:
        return session.exec(select(TempUser).where(TempUser.email == email).where(TempUser.expiry >= datetime.now().timestamp())).first()


def get_products(
    page: int,
    row: int,
    type: Optional[int] = None,
    keyword: Optional[str] = None,
) -> ProductFetchResonse:
    try:
        with Session(engine) as session:
            query = select(Product).where(Product.isVerified == True)
            if type:
                query = query.where(Product.type == type)
            if keyword:
                print(keyword)
                query = query.filter(
                    or_(
                        column("name").like("%{}%".format(keyword)),
                        column("description").like("%{}%".format(keyword)),
                        column("id").like("%{}%".format(keyword)),
                    )
                )
            return ProductFetchResonse(
                products=session.exec(query.offset(page * row).limit(row)).all(),
                maxPage=len(session.exec(select(Product)).all()) // row,
                page=page,
            )

    except Exception as e:
        print(e)
        return ProductFetchResonse(products=[], maxPage=1, page=1)


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


def verify_admin_by_email(email: str) -> bool:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        return user.isAdmin if user else False


def get_all_products() -> Sequence[Product]:
    with Session(engine) as session:
        return session.exec(select(Product)).all()


def get_product_by_id(id: int, verified: bool) -> Union[Product, None]:
    with Session(engine) as session:
        query = select(Product).where(Product.id == id)
        if verified:
            query = query.where(Product.isVerified == True)
        return session.exec(query).first()


def change_product(product: Product, request: ProductChangeRequest) -> bool:
    try:
        with Session(engine) as session:
            db_product = session.get(Product, product.id)
            if db_product:
                db_product.isVerified = request.isVerified
                db_product.stock = request.stock
                db_product.sales = request.sales
                session.commit()
                return True
            return False
    except Exception:
        return False


def get_user_by_id(id: int) -> Union[User, None]:
    with Session(engine) as session:
        return session.exec(select(User).where(User.id == id)).first()


def remove_product_type_by_id(id: int) -> bool:
    try:
        with Session(engine) as session:
            product_type = session.exec(
                select(ProductType).where(ProductType.id == id)
            ).first()
            session.delete(product_type)
            session.commit()
            return True
    except Exception:
        return False


def create_product_type(product_type: ProductType) -> bool:
    try:
        with Session(engine) as session:
            session.add(product_type)
            session.commit()
            return True
    except Exception:
        return False
    
def create_trade(trade: Trade) -> bool:
    try:
        with Session(engine) as session:
            session.add(trade)
            session.commit()
            session.refresh(trade)
            return True
    except Exception:
        return False

def get_trade_by_id(id: int) -> Union[Trade, None]:
    with Session(engine) as session:
        return session.exec(select(Trade).where(Trade.id == id)).first()