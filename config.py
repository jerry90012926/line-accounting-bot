import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")  # 可選，填入後指令同步更快
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///watchlist.db")
