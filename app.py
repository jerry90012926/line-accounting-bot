"""
主入口：同時啟動
- Flask（LINE webhook + keep-alive）
- Discord Bot（背景執行緒）
- 警報推送 hook（Discord DM + LINE push）
"""
import os
import sys
import threading

# 關閉 stdout/stderr 緩衝，讓 Render log 即時顯示
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent
from linebot.v3.exceptions import InvalidSignatureError

from config import (
    DISCORD_BOT_TOKEN, LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN,
)
from models import init_db
from bot import bot, run_bot, register_alert_hook
from line_handler import handle_line_text, push_line_alert, get_welcome_message

app = Flask(__name__)
init_db()

# ==================== Flask routes ====================
@app.route("/")
def home():
    return "Stock Bot is alive!"


@app.route("/health")
def health():
    return {"status": "ok"}


# ==================== LINE webhook ====================
line_handler = None
line_configuration = None

if LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN:
    line_handler = WebhookHandler(LINE_CHANNEL_SECRET)
    line_configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

    @line_handler.add(FollowEvent)
    def on_follow(event):
        with ApiClient(line_configuration) as api_client:
            api = MessagingApi(api_client)
            api.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=get_welcome_message())],
            ))

    @line_handler.add(MessageEvent, message=TextMessageContent)
    def on_message(event):
        user_id = event.source.user_id
        text = event.message.text.strip()
        reply_text = handle_line_text(user_id, text)

        with ApiClient(line_configuration) as api_client:
            api = MessagingApi(api_client)
            api.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            ))


@app.route("/callback", methods=["POST"])
def callback():
    if not line_handler:
        return "LINE not configured", 503
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


# ==================== 警報推送橋接 ====================
# Discord bot 的警報 task 會呼叫這個 hook，推播到 LINE
register_alert_hook(push_line_alert)


# ==================== 啟動 ====================
def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError("請設定 DISCORD_BOT_TOKEN 環境變數")

    # 背景執行緒跑 Flask（LINE webhook + keep-alive）
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask 已在背景啟動（LINE webhook + keep-alive）")

    # 主執行緒跑 Discord Bot
    run_bot()
