from sqlmodel import SQLModel, create_engine, Session, select
from sqlmodel import Field
from typing import Union
from core.scheduler import scheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import os


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

class UserLogins(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str
    cookie: str
    time: int

sqlite_url = os.getenv("DATABASE_URL") or "sqlite:///test.db"
engine = create_engine(sqlite_url)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def create_temporary_user(user: TempUser) -> bool:
    create_db_and_tables()
    with Session(engine) as session:
        existing_user = session.exec(
            select(User).where(User.email == user.email)
        ).first()
        existing_temp_user = session.exec(
            select(TempUser).where(TempUser.email == user.email)
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
    create_db_and_tables()
    try:
        with Session(engine) as session:
            session.add(user)
            session.commit()
            return True
    except Exception:
        return False
    
def create_user_login(user: UserLogins) -> bool:
    create_db_and_tables()
    try:
        with Session(engine) as session:
            session.add(user)
            session.commit()
            return True
    except Exception:
        return False

def remove_temporary_user(user: TempUser) -> None:
    create_db_and_tables()
    try:
        with Session(engine) as session:
            session.delete(user)
            session.commit()
    except Exception:
        pass


def get_user_by_email(email: str) -> Union[User, None]:
    create_db_and_tables()
    with Session(engine) as session:
        return session.exec(select(User).where(User.email == email)).first()

def get_temp_user_by_token(token: str) -> Union[TempUser, None]:
    create_db_and_tables()
    with Session(engine) as session:
        return session.exec(select(TempUser).where(TempUser.token == token)).first()