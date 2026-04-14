from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

Base = declarative_base()


class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # "income" or "expense"
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False, default="其他")
    description = Column(String, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.now)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
