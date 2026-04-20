"""台股資料抓取（雙來源：證交所 + yfinance 備援）"""
import requests
import yfinance as yf

# 台灣證交所即時行情 API（盤中/盤後都能用）
TWSE_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


def _fetch_twse(symbol: str):
    """從證交所 API 抓上市/上櫃即時報價"""
    for prefix in ("tse_", "otc_"):
        try:
            params = {
                "ex_ch": f"{prefix}{symbol}.tw",
                "json": "1",
                "delay": "0",
            }
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                ),
                "Referer": "https://mis.twse.com.tw/stock/fibest.jsp",
            }
            r = requests.get(TWSE_URL, params=params, headers=headers, timeout=8)
            r.raise_for_status()
            data = r.json()
            arr = data.get("msgArray", [])
            if not arr:
                continue
            d = arr[0]

            # z=最新成交價, y=昨收, o=開盤, h=最高, l=最低, v=成交量, n=名稱
            def _f(key):
                v = d.get(key, "")
                if not v or v == "-":
                    return None
                try:
                    return float(v)
                except ValueError:
                    return None

            price = _f("z") or _f("y")  # 盤前用昨收
            if price is None:
                continue
            prev_close = _f("y") or price
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            return {
                "symbol": symbol,
                "name": d.get("n", symbol),
                "price": price,
                "open": _f("o") or price,
                "high": _f("h") or price,
                "low": _f("l") or price,
                "volume": int(_f("v") or 0) * 1000,  # TWSE 單位為張
                "prev_close": prev_close,
                "change": change,
                "change_pct": change_pct,
                "currency": "TWD",
                "source": "TWSE",
            }
        except Exception as e:
            print(f"TWSE {prefix}{symbol} 失敗: {e}")
            continue
    return None


def _fetch_yfinance(symbol: str):
    """備援：yfinance"""
    for suffix in (".TW", ".TWO"):
        try:
            ticker = yf.Ticker(f"{symbol}{suffix}")
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
                "name": info.get("longName") or info.get("shortName") or symbol,
                "price": current,
                "open": float(latest["Open"]),
                "high": float(latest["High"]),
                "low": float(latest["Low"]),
                "volume": int(latest["Volume"]),
                "prev_close": float(prev_close),
                "change": change,
                "change_pct": change_pct,
                "currency": "TWD",
                "source": "yfinance",
            }
        except Exception as e:
            print(f"yfinance {symbol}{suffix} 失敗: {e}")
            continue
    return None


def get_stock_info(symbol: str):
    """優先用證交所 API，失敗才用 yfinance"""
    symbol = symbol.strip().upper().replace(".TW", "").replace(".TWO", "")
    info = _fetch_twse(symbol)
    if info:
        return info
    return _fetch_yfinance(symbol)


def get_history(symbol, period="1mo"):
    """取得歷史資料（目前只用 yfinance）"""
    symbol = symbol.strip().upper()
    for suffix in (".TW", ".TWO"):
        try:
            ticker = yf.Ticker(f"{symbol}{suffix}")
            hist = ticker.history(period=period)
            if not hist.empty:
                return hist
        except Exception:
            continue
    return None


def format_price_message(info):
    """將股票資訊格式化"""
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
