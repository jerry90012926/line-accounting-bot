from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

Base = declarative_base()


class Watchlist(Base):
    """使用者自選股"""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False)  # 台股代號，如 "2330"
    name = Column(String, default="")         # 公司名稱快取
    note = Column(String, default="")         # 使用者備註
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_symbol"),
    )


class PriceAlert(Base):
    """價格警報"""
    __tablename__ = "price_alert"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # "above" / "below"
    target_price = Column(Float, nullable=False)
    triggered = Column(Integer, default=0)  # 0 = 未觸發, 1 = 已觸發
    created_at = Column(DateTime, default=datetime.now)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
