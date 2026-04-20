from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

Base = declarative_base()


class Watchlist(Base):
    """使用者自選股（Discord/LINE 共用）"""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)  # 統一的 owner key
    symbol = Column(String, nullable=False)
    name = Column(String, default="")
    note = Column(String, default="")
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
    triggered = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
