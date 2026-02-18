from sqlmodel import create_engine, Session
import os

# 你给的连接信息（用户名 pstgres，密码 123456）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:123456@localhost:5432/postgres",
)

engine = create_engine(DATABASE_URL, echo=True)


def get_session():
    with Session(engine) as session:
        yield session
