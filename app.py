from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent
from linebot.v3.exceptions import InvalidSignatureError

from config import LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN
from models import init_db
from handlers import handle_text_message

app = Flask(__name__)

# 初始化資料庫
init_db()

if not LINE_CHANNEL_SECRET or not LINE_CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("請設定 LINE_CHANNEL_SECRET 和 LINE_CHANNEL_ACCESS_TOKEN 環境變數")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@app.route("/", methods=["GET"])
def health():
    return "LINE BOT is running!"


@handler.add(FollowEvent)
def on_follow(event):
    welcome_text = (
        "👋 歡迎使用記帳機器人！\n"
        "━━━━━━━━━━━━━━━\n"
        "我可以幫你快速記錄每日收支\n\n"
        "【快速開始】\n"
        "  📝 記支出：早餐 50\n"
        "  📝 也可以：早餐50\n"
        "  💵 記收入：收入 薪水 50000\n\n"
        "【查詢統計】\n"
        "  今日 / 本週 / 本月\n\n"
        "【AI 分析】\n"
        "  輸入「分析」查看消費報告\n\n"
        "輸入「說明」查看完整指令 📖"
    )

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=welcome_text)],
            )
        )


@handler.add(MessageEvent, message=TextMessageContent)
def on_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    result = handle_text_message(user_id, text)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        messages = []
        if result.get("text"):
            messages.append(TextMessage(text=result["text"]))

        if messages:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token, messages=messages
                )
            )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
