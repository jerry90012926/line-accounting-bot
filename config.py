import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")  # 可選，填入後指令同步更快
DISCORD_OWNER_IDS = os.getenv("DISCORD_OWNER_IDS", "")  # 逗號分隔的 User ID，空=開放所有人
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///watchlist.db")


def get_owner_ids():
    if not DISCORD_OWNER_IDS:
        return set()
    return {int(x.strip()) for x in DISCORD_OWNER_IDS.split(",") if x.strip()}
