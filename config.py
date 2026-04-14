import os
from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///accounting.db")
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID", "")
