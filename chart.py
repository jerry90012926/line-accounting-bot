import os


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def generate_ai_analysis(category_totals, total_income, total_expense, period_label):
    """
    用 AI 分析消費數據，回傳分析文字。
    """
    if not OPENAI_API_KEY:
        return _fallback_analysis(category_totals, total_income, total_expense, period_label)

    # 組裝消費資料
    expense_detail = "\n".join(
        f"- {cat}：${amt:,.0f}" for cat, amt in
        sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    )

    prompt = f"""你是一位專業的個人財務顧問。請根據以下{period_label}的收支資料，用繁體中文做出簡短分析和建議。

收入：${total_income:,.0f}
總支出：${total_expense:,.0f}
淨額：${total_income - total_expense:,.0f}

各分類支出：
{expense_detail}

請用以下格式回覆（控制在 300 字以內）：
1. 一句話總結本期消費狀況
2. 指出最大的支出項目及佔比
3. 給出 1-2 個具體的省錢建議
4. 如果有異常消費模式，提醒一下

語氣親切、口語化，適合在聊天軟體中閱讀。使用 emoji 讓內容更生動。"""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return _fallback_analysis(category_totals, total_income, total_expense, period_label)


def _fallback_analysis(category_totals, total_income, total_expense, period_label):
    """AI 不可用時的基本分析"""
    if not category_totals:
        return f"📭 {period_label}還沒有支出記錄"

    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    top_cat, top_amt = sorted_cats[0]
    top_pct = (top_amt / total_expense * 100) if total_expense > 0 else 0

    text = f"📊 {period_label}消費分析\n━━━━━━━━━━━━━━━\n"
    if total_income > 0:
        text += f"📈 收入：${total_income:,.0f}\n"
    text += f"📉 支出：${total_expense:,.0f}\n"
    text += f"💰 淨額：${total_income - total_expense:,.0f}\n\n"
    text += f"🔍 最大支出：{top_cat} ${top_amt:,.0f}（佔 {top_pct:.0f}%）\n\n"
    text += "📂 各項支出：\n"
    for cat, amt in sorted_cats:
        pct = (amt / total_expense * 100) if total_expense > 0 else 0
        bar = "█" * max(1, int(pct / 5))
        text += f"  {cat} {bar} ${amt:,.0f} ({pct:.0f}%)\n"

    return text
