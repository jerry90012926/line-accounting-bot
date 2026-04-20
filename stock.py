"""台股資料抓取（使用 yfinance）"""
import yfinance as yf


def _to_yf_symbol(symbol):
    """
    將台股代號轉為 yfinance 格式。
    2330 -> 2330.TW（上市）
    6488 -> 6488.TWO（上櫃，若 .TW 失敗會自動嘗試）
    """
    symbol = symbol.strip().upper()
    if "." in symbol:
        return symbol
    return f"{symbol}.TW"


def get_stock_info(symbol):
    """
    取得股票即時資訊，回傳 dict 或 None。
    """
    candidates = [f"{symbol}.TW", f"{symbol}.TWO"] if "." not in symbol else [symbol]

    for yf_symbol in candidates:
        try:
            ticker = yf.Ticker(yf_symbol)
            # 取最近兩天的資料來算漲跌
            hist = ticker.history(period="5d")
            if hist.empty:
                continue

            info = ticker.info
            latest = hist.iloc[-1]
            prev_close = hist.iloc[-2]["Close"] if len(hist) >= 2 else latest["Open"]
            current = float(latest["Close"])
            change = current - float(prev_close)
            change_pct = (change / float(prev_close)) * 100 if prev_close else 0

            return {
                "symbol": symbol,
                "yf_symbol": yf_symbol,
                "name": info.get("longName") or info.get("shortName") or symbol,
                "price": current,
                "open": float(latest["Open"]),
                "high": float(latest["High"]),
                "low": float(latest["Low"]),
                "volume": int(latest["Volume"]),
                "prev_close": float(prev_close),
                "change": change,
                "change_pct": change_pct,
                "currency": info.get("currency", "TWD"),
            }
        except Exception:
            continue

    return None


def get_history(symbol, period="1mo"):
    """取得歷史資料，用於圖表或趨勢分析"""
    yf_symbol = _to_yf_symbol(symbol)
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            # 嘗試上櫃
            ticker = yf.Ticker(f"{symbol}.TWO")
            hist = ticker.history(period=period)
        return hist if not hist.empty else None
    except Exception:
        return None


def format_price_message(info):
    """將股票資訊格式化成易讀文字"""
    if not info:
        return "❌ 找不到這支股票"

    arrow = "🔺" if info["change"] > 0 else ("🔻" if info["change"] < 0 else "▫️")
    sign = "+" if info["change"] > 0 else ""

    return (
        f"📊 **{info['name']}** ({info['symbol']})\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 現價：${info['price']:.2f}\n"
        f"{arrow} 漲跌：{sign}{info['change']:.2f} ({sign}{info['change_pct']:.2f}%)\n"
        f"📈 最高：${info['high']:.2f}\n"
        f"📉 最低：${info['low']:.2f}\n"
        f"🔓 開盤：${info['open']:.2f}\n"
        f"🔒 昨收：${info['prev_close']:.2f}\n"
        f"📦 成交量：{info['volume']:,}"
    )
