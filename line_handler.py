"""LINE 指令台與推播邏輯"""
import re
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage,
)

from config import (
    LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, OWNER_KEY, get_line_owner_ids
)
from models import get_session, Watchlist, PriceAlert
from stock import get_stock_info, format_price_message

LINE_OWNER_IDS = get_line_owner_ids()

_line_config = None


def _get_line_api():
    global _line_config
    if not LINE_CHANNEL_ACCESS_TOKEN:
        return None
    if _line_config is None:
        _line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    return _line_config


def is_line_owner(user_id: str) -> bool:
    if not LINE_OWNER_IDS:
        return True
    return user_id in LINE_OWNER_IDS


# ==================== 指令解析 ====================
def handle_line_text(user_id: str, text: str) -> str:
    """解析 LINE 訊息並回傳文字回覆"""
    if not is_line_owner(user_id):
        return "⛔ 你沒有權限使用這個 Bot"

    t = text.strip()

    if t in ("說明", "help", "幫助", "指令"):
        return _help()
    if t in ("清單", "自選股", "list"):
        return _list_watchlist()
    if t in ("行情", "watch"):
        return _watch_all()
    if t in ("警報清單", "警報", "alerts"):
        return _list_alerts()

    # 加入自選股: "加入 2330" / "加入 2330 台積電"
    m = re.match(r"^(?:加入|add)\s+(\S+)(?:\s+(.+))?$", t)
    if m:
        return _add_watchlist(m.group(1), (m.group(2) or "").strip())

    # 移除自選股: "移除 2330"
    m = re.match(r"^(?:移除|remove|del)\s+(\S+)$", t)
    if m:
        return _remove_watchlist(m.group(1))

    # 查價: "股價 2330" / "price 2330" / 單獨 "2330"
    m = re.match(r"^(?:股價|price)\s+(\S+)$", t)
    if m:
        return _query_price(m.group(1))
    if re.match(r"^\d{4,6}$", t):
        return _query_price(t)

    # 設定警報: "警報 2330 突破 1000" / "警報 2330 跌破 900"
    m = re.match(r"^(?:警報|alert)\s+(\S+)\s+(突破|跌破|above|below)\s+([\d.]+)$", t)
    if m:
        sym, direction_raw, price_str = m.groups()
        direction = "above" if direction_raw in ("突破", "above") else "below"
        return _add_alert(sym, direction, float(price_str))

    # 移除警報: "刪除警報 5" / "移除警報 5"
    m = re.match(r"^(?:刪除警報|移除警報|alert_remove)\s+#?(\d+)$", t)
    if m:
        return _remove_alert(int(m.group(1)))

    return (
        "❓ 不認得這個指令\n"
        "輸入「說明」查看可用指令"
    )


# ==================== 各指令實作 ====================
def _help():
    return (
        "📖 台股自選股 LINE 指令\n"
        "━━━━━━━━━━━━━━━\n"
        "【查價】\n"
        "  2330 (直接輸入代號)\n"
        "  股價 2330\n\n"
        "【自選股】\n"
        "  加入 2330\n"
        "  加入 2330 台積電\n"
        "  移除 2330\n"
        "  清單 → 查看自選股\n"
        "  行情 → 所有自選股即時報價\n\n"
        "【警報】\n"
        "  警報 2330 突破 1000\n"
        "  警報 2330 跌破 900\n"
        "  警報清單\n"
        "  刪除警報 5\n\n"
        "📱 也可在 Discord 用 slash commands"
    )


def _query_price(symbol: str) -> str:
    info = get_stock_info(symbol.upper())
    if not info:
        return f"❌ 找不到股票 {symbol}"
    # LINE 不支援 markdown，去掉 **
    return format_price_message(info).replace("**", "")


def _add_watchlist(symbol: str, note: str) -> str:
    symbol = symbol.upper()
    info = get_stock_info(symbol)
    if not info:
        return f"❌ 找不到股票 {symbol}"

    session = get_session()
    try:
        existing = session.query(Watchlist).filter_by(user_id=OWNER_KEY, symbol=symbol).first()
        if existing:
            return f"⚠️ {symbol} {info['name']} 已在自選股中"
        session.add(Watchlist(user_id=OWNER_KEY, symbol=symbol, name=info["name"], note=note))
        session.commit()
    finally:
        session.close()
    return f"✅ 已加入自選股\n{info['name']} ({symbol})\n目前價格：${info['price']:.2f}"


def _remove_watchlist(symbol: str) -> str:
    symbol = symbol.upper()
    session = get_session()
    try:
        item = session.query(Watchlist).filter_by(user_id=OWNER_KEY, symbol=symbol).first()
        if not item:
            return f"❌ {symbol} 不在自選股中"
        name = item.name
        session.delete(item)
        session.commit()
    finally:
        session.close()
    return f"🗑️ 已移除：{name} ({symbol})"


def _list_watchlist() -> str:
    session = get_session()
    try:
        items = session.query(Watchlist).filter_by(user_id=OWNER_KEY).order_by(Watchlist.created_at).all()
    finally:
        session.close()
    if not items:
        return "📭 還沒有自選股\n用「加入 2330」來新增"

    text = f"📋 自選股清單（{len(items)} 支）\n━━━━━━━━━━━━━━━\n"
    for it in items:
        text += f"• {it.name or it.symbol} ({it.symbol})"
        if it.note:
            text += f" — {it.note}"
        text += "\n"
    return text.rstrip()


def _watch_all() -> str:
    session = get_session()
    try:
        items = session.query(Watchlist).filter_by(user_id=OWNER_KEY).all()
    finally:
        session.close()

    if not items:
        return "📭 還沒有自選股\n用「加入 2330」來新增"

    text = "📊 自選股即時行情\n━━━━━━━━━━━━━━━\n"
    for it in items:
        info = get_stock_info(it.symbol)
        if not info:
            text += f"❌ {it.name or it.symbol} ({it.symbol}) 無法取得\n"
            continue
        arrow = "🔺" if info["change"] > 0 else ("🔻" if info["change"] < 0 else "▫️")
        sign = "+" if info["change"] > 0 else ""
        text += (
            f"{info['name']} ({it.symbol})\n"
            f"  ${info['price']:.2f} {arrow} {sign}{info['change']:.2f} ({sign}{info['change_pct']:.2f}%)\n"
        )
    return text.rstrip()


def _add_alert(symbol: str, direction: str, price: float) -> str:
    symbol = symbol.upper()
    info = get_stock_info(symbol)
    if not info:
        return f"❌ 找不到股票 {symbol}"

    session = get_session()
    try:
        item = PriceAlert(user_id=OWNER_KEY, symbol=symbol, direction=direction, target_price=price)
        session.add(item)
        session.commit()
        alert_id = item.id
    finally:
        session.close()

    dir_text = "突破" if direction == "above" else "跌破"
    return (
        f"⏰ 警報已設定 #{alert_id}\n"
        f"{info['name']} ({symbol}) {dir_text} ${price:.2f} 時通知"
    )


def _list_alerts() -> str:
    session = get_session()
    try:
        items = session.query(PriceAlert).filter_by(user_id=OWNER_KEY, triggered=0).all()
    finally:
        session.close()

    if not items:
        return "📭 沒有未觸發的警報"

    text = "⏰ 價格警報清單\n━━━━━━━━━━━━━━━\n"
    for a in items:
        dir_text = "🔺突破" if a.direction == "above" else "🔻跌破"
        text += f"#{a.id} {a.symbol} {dir_text} ${a.target_price:.2f}\n"
    text += "\n用「刪除警報 編號」移除"
    return text


def _remove_alert(alert_id: int) -> str:
    session = get_session()
    try:
        item = session.query(PriceAlert).filter_by(id=alert_id, user_id=OWNER_KEY).first()
        if not item:
            return f"❌ 找不到警報 #{alert_id}"
        session.delete(item)
        session.commit()
    finally:
        session.close()
    return f"🗑️ 已移除警報 #{alert_id}"


# ==================== LINE 推播 ====================
def _push_line_alert_sync(symbol, info, direction, target_price):
    """同步版本的 LINE 推播"""
    cfg = _get_line_api()
    if not cfg or not LINE_OWNER_IDS:
        return

    dir_text = "突破" if direction == "above" else "跌破"
    msg = (
        f"🚨 價格警報觸發！\n"
        f"{info['name']} ({symbol}) 已{dir_text}目標價 ${target_price:.2f}\n"
        f"目前價格：${info['price']:.2f}"
    )

    with ApiClient(cfg) as api_client:
        api = MessagingApi(api_client)
        for uid in LINE_OWNER_IDS:
            try:
                api.push_message(PushMessageRequest(
                    to=uid, messages=[TextMessage(text=msg)]
                ))
            except Exception as e:
                print(f"LINE 推播失敗 ({uid}): {e}")


async def push_line_alert(symbol, info, direction, target_price):
    """async 包裝：在 executor 執行同步推播，避免阻塞事件迴圈"""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _push_line_alert_sync, symbol, info, direction, target_price
    )


def get_welcome_message() -> str:
    return (
        "👋 歡迎使用台股自選股 Bot！\n"
        "━━━━━━━━━━━━━━━\n"
        "📈 輸入代號直接查價（例：2330）\n"
        "📋 加入 2330 → 加入自選股\n"
        "📊 行情 → 所有自選股即時報價\n"
        "⏰ 警報 2330 突破 1000\n\n"
        "輸入「說明」查看完整指令"
    )
