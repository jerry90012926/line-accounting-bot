import re
from datetime import datetime, timedelta
from models import get_session, Record
from chart import generate_ai_analysis

# 預設分類
CATEGORIES = ["飲食", "交通", "娛樂", "購物", "居住", "醫療", "教育", "其他"]

# 智慧分類關鍵字對應
KEYWORD_CATEGORY_MAP = {
    "飲食": [
        "早餐", "午餐", "晚餐", "宵夜", "便當", "飲料", "咖啡", "茶",
        "小吃", "火鍋", "燒烤", "拉麵", "壽司", "pizza", "漢堡",
        "雞排", "珍奶", "奶茶", "水果", "零食", "餐廳", "外送",
        "foodpanda", "ubereats", "吃飯", "食物", "麵包", "蛋糕",
        "超市", "全聯", "7-11", "全家", "萊爾富",
    ],
    "交通": [
        "捷運", "公車", "uber", "計程車", "taxi", "高鐵", "台鐵",
        "火車", "機票", "停車", "加油", "油錢", "悠遊卡", "交通",
        "客運", "腳踏車", "gogoro", "機車",
    ],
    "娛樂": [
        "電影", "ktv", "遊戲", "netflix", "spotify", "youtube",
        "演唱會", "旅遊", "住宿", "門票", "樂園", "唱歌", "書",
    ],
    "購物": [
        "衣服", "褲子", "鞋子", "包包", "配件", "3c", "手機",
        "電腦", "耳機", "蝦皮", "momo", "pchome", "淘寶", "amazon",
    ],
    "居住": [
        "房租", "水費", "電費", "瓦斯", "網路", "管理費", "租金",
        "第四台", "電話費", "手機費",
    ],
    "醫療": [
        "看醫生", "掛號", "藥", "醫院", "診所", "牙醫", "眼科",
        "健保", "保險",
    ],
    "教育": [
        "學費", "補習", "課程", "書籍", "文具", "線上課程", "udemy",
    ],
}


def guess_category(description):
    desc_lower = description.lower()
    for category, keywords in KEYWORD_CATEGORY_MAP.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return category
    return "其他"


def handle_text_message(user_id, text):
    if text in ("說明", "help", "幫助", "指令"):
        return handle_help()
    if text == "分類":
        return handle_categories()
    if text == "今日":
        return handle_today(user_id)
    if text == "本週":
        return handle_week(user_id)
    if text == "本月":
        return handle_month(user_id)
    if text in ("圖表", "報表", "分析"):
        return handle_chart(user_id)
    if text.startswith("刪除"):
        return handle_delete(user_id, text)
    if text.startswith("收入"):
        return handle_income(user_id, text)

    # 預設嘗試解析為支出記帳
    return handle_expense(user_id, text)


def handle_help():
    help_text = (
        "📒 記帳機器人使用說明\n"
        "━━━━━━━━━━━━━━━\n"
        "【記帳】\n"
        "  早餐 50\n"
        "  午餐 120 飲食\n"
        "  咖啡 65\n"
        "\n"
        "【記收入】\n"
        "  收入 薪水 50000\n"
        "  收入 獎金 3000\n"
        "\n"
        "【查詢】\n"
        "  今日 → 今日明細\n"
        "  本週 → 本週統計\n"
        "  本月 → 本月統計\n"
        "\n"
        "【AI 分析】\n"
        "  分析 → AI 分析本月消費\n"
        "\n"
        "【其他】\n"
        "  刪除 #編號 → 刪除記錄\n"
        "  分類 → 查看所有分類\n"
        "  說明 → 顯示此說明"
    )
    return {"text": help_text}


def handle_categories():
    text = "📂 支出分類一覽\n━━━━━━━━━━━━━━━\n"
    text += "、".join(CATEGORIES)
    text += "\n\n💡 記帳時可指定分類：\n  午餐 120 飲食\n\n未指定分類會自動判斷！"
    return {"text": text}


def handle_expense(user_id, text):
    # 支援格式:
    # 早餐 50  /  午餐 120 飲食  /  早餐50  /  午餐120飲食
    parts = text.split()

    if len(parts) >= 2:
        # 有空格: "早餐 50" 或 "午餐 120 飲食"
        description = parts[0]
        try:
            amount = float(parts[1])
        except ValueError:
            return {"text": "❓ 金額格式錯誤\n請輸入數字，例如：早餐 50"}
        category = parts[2] if len(parts) >= 3 and parts[2] in CATEGORIES else None
    else:
        # 沒空格: "早餐50" 或 "午餐120飲食"
        match = re.match(r"^(.+?)([\d.]+)(.*)$", text)
        if not match:
            return {"text": "❓ 格式不正確\n請輸入：品項 金額\n例如：早餐 50 或 早餐50"}
        description = match.group(1)
        try:
            amount = float(match.group(2))
        except ValueError:
            return {"text": "❓ 金額格式錯誤\n請輸入數字，例如：早餐 50"}
        suffix = match.group(3).strip()
        category = suffix if suffix in CATEGORIES else None

    if amount <= 0:
        return {"text": "❓ 金額必須大於 0"}

    if category is None:
        category = guess_category(description)

    session = get_session()
    try:
        record = Record(
            user_id=user_id,
            type="expense",
            amount=amount,
            category=category,
            description=description,
        )
        session.add(record)
        session.commit()
        record_id = record.id
    finally:
        session.close()

    return {
        "text": (
            f"✅ 已記錄支出\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📝 {description}\n"
            f"💰 ${amount:,.0f}\n"
            f"📂 {category}\n"
            f"🔢 編號 #{record_id}"
        )
    }


def handle_income(user_id, text):
    # 格式: 收入 描述 金額
    parts = text.split()
    if len(parts) < 3:
        return {"text": "❓ 格式不正確\n請輸入：收入 描述 金額\n例如：收入 薪水 50000"}

    description = parts[1]
    try:
        amount = float(parts[2])
    except ValueError:
        return {"text": "❓ 金額格式錯誤\n請輸入數字，例如：收入 薪水 50000"}

    if amount <= 0:
        return {"text": "❓ 金額必須大於 0"}

    session = get_session()
    try:
        record = Record(
            user_id=user_id,
            type="income",
            amount=amount,
            category="收入",
            description=description,
        )
        session.add(record)
        session.commit()
        record_id = record.id
    finally:
        session.close()

    return {
        "text": (
            f"✅ 已記錄收入\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📝 {description}\n"
            f"💰 +${amount:,.0f}\n"
            f"🔢 編號 #{record_id}"
        )
    }


def handle_delete(user_id, text):
    match = re.search(r"#?(\d+)", text)
    if not match:
        return {"text": "❓ 請指定編號\n例如：刪除 #5"}

    record_id = int(match.group(1))
    session = get_session()
    try:
        record = (
            session.query(Record)
            .filter(Record.id == record_id, Record.user_id == user_id)
            .first()
        )
        if not record:
            return {"text": f"❌ 找不到編號 #{record_id} 的記錄"}

        desc = record.description
        amount = record.amount
        session.delete(record)
        session.commit()
    finally:
        session.close()

    return {"text": f"🗑️ 已刪除記錄 #{record_id}\n{desc} ${amount:,.0f}"}


def handle_today(user_id):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    return _query_records(user_id, today, tomorrow, "今日")


def handle_week(user_id):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=today.weekday())  # Monday
    end = start + timedelta(days=7)
    return _query_records(user_id, start, end, "本週")


def handle_month(user_id):
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)
    return _query_records(user_id, start, end, "本月")


def _query_records(user_id, start, end, period_label):
    session = get_session()
    try:
        records = (
            session.query(Record)
            .filter(
                Record.user_id == user_id,
                Record.created_at >= start,
                Record.created_at < end,
            )
            .order_by(Record.created_at.desc())
            .all()
        )

        if not records:
            return {"text": f"📭 {period_label}還沒有任何記錄"}

        total_expense = sum(r.amount for r in records if r.type == "expense")
        total_income = sum(r.amount for r in records if r.type == "income")

        # 分類統計
        category_totals = {}
        for r in records:
            if r.type == "expense":
                category_totals[r.category] = category_totals.get(r.category, 0) + r.amount

        text = f"📊 {period_label}收支報告\n━━━━━━━━━━━━━━━\n"

        if total_income > 0:
            text += f"📈 收入：${total_income:,.0f}\n"
        text += f"📉 支出：${total_expense:,.0f}\n"
        text += f"💰 淨額：${total_income - total_expense:,.0f}\n"

        if category_totals:
            text += "\n📂 支出分類\n"
            sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            for cat, amount in sorted_cats:
                pct = (amount / total_expense * 100) if total_expense > 0 else 0
                text += f"  {cat}：${amount:,.0f} ({pct:.0f}%)\n"

        # 明細 (最多顯示 10 筆)
        text += f"\n📝 明細（最近 {min(len(records), 10)} 筆）\n"
        for r in records[:10]:
            icon = "📈" if r.type == "income" else "📉"
            sign = "+" if r.type == "income" else "-"
            text += f"  {icon} {r.description} {sign}${r.amount:,.0f} #{r.id}\n"

        if len(records) > 10:
            text += f"  ...還有 {len(records) - 10} 筆"

    finally:
        session.close()

    return {"text": text}


def handle_chart(user_id):
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)

    session = get_session()
    try:
        records = (
            session.query(Record)
            .filter(
                Record.user_id == user_id,
                Record.created_at >= start,
                Record.created_at < end,
            )
            .all()
        )
    finally:
        session.close()

    if not records:
        return {"text": "📭 本月還沒有任何記錄，無法分析"}

    total_expense = sum(r.amount for r in records if r.type == "expense")
    total_income = sum(r.amount for r in records if r.type == "income")

    category_totals = {}
    for r in records:
        if r.type == "expense":
            category_totals[r.category] = category_totals.get(r.category, 0) + r.amount

    period_label = now.strftime("%Y年%m月")
    analysis = generate_ai_analysis(category_totals, total_income, total_expense, period_label)

    return {"text": analysis}
