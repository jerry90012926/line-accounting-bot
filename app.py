from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

from config import LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN
from models import init_db
from handlers import handle_text_message

app = Flask(__name__)

# 初始化資料庫（確保 gunicorn 啟動時也會執行）
init_db()

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
        if result.get("image_url"):
            messages.append(
                ImageMessage(
                    original_content_url=result["image_url"],
                    preview_image_url=result["image_url"],
                )
            )

        if messages:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token, messages=messages
                )
            )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
