"""
主入口：同時啟動 Discord Bot 與 Flask keep-alive 伺服器

Flask 提供 HTTP 端點讓 UptimeRobot 等監控服務定期 ping，
避免 Render 免費方案的服務休眠。
"""
import os
import threading
from flask import Flask
from bot import run_bot

app = Flask(__name__)


@app.route("/")
def home():
    return "Discord Stock Bot is alive!"


@app.route("/health")
def health():
    return {"status": "ok"}


def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    # 在背景執行緒跑 Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 主執行緒跑 Discord Bot
    run_bot()
