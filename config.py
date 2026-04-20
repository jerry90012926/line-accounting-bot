import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")
DISCORD_OWNER_IDS = os.getenv("DISCORD_OWNER_IDS", "")  # 逗號分隔

# LINE
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_OWNER_USER_IDS = os.getenv("LINE_OWNER_USER_IDS", "")  # 逗號分隔

# 統一的擁有者 key（Discord 與 LINE 共用同一份自選股資料）
OWNER_KEY = os.getenv("OWNER_KEY", "default_owner")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data.db")


def get_discord_owner_ids():
    if not DISCORD_OWNER_IDS:
        return set()
    return {int(x.strip()) for x in DISCORD_OWNER_IDS.split(",") if x.strip()}


def get_line_owner_ids():
    if not LINE_OWNER_USER_IDS:
        return set()
    return {x.strip() for x in LINE_OWNER_USER_IDS.split(",") if x.strip()}
