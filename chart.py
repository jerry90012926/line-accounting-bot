import io
import os
import uuid
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 圖片儲存目錄
CHART_DIR = os.path.join(os.path.dirname(__file__), "static", "charts")
os.makedirs(CHART_DIR, exist_ok=True)


def _get_chinese_font():
    """嘗試找到系統中的中文字體"""
    chinese_fonts = [
        "Microsoft JhengHei",  # Windows 正黑體
        "Microsoft YaHei",     # Windows 微軟雅黑
        "SimHei",              # Windows 黑體
        "PingFang TC",         # macOS
        "Noto Sans CJK TC",   # Linux
        "WenQuanYi Micro Hei", # Linux
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in chinese_fonts:
        if font_name in available:
            return font_name
    return None


CHINESE_FONT = _get_chinese_font()

# 分類顏色
CATEGORY_COLORS = {
    "飲食": "#FF6B6B",
    "交通": "#4ECDC4",
    "娛樂": "#45B7D1",
    "購物": "#FFA07A",
    "居住": "#98D8C8",
    "醫療": "#F7DC6F",
    "教育": "#BB8FCE",
    "其他": "#AEB6BF",
}


def generate_expense_chart(category_totals, title):
    """
    生成支出圓餅圖，儲存到 static/charts/，回傳檔名。
    """
    categories = list(category_totals.keys())
    amounts = list(category_totals.values())
    colors = [CATEGORY_COLORS.get(c, "#AEB6BF") for c in categories]

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("#FFFFFF")

    wedges, texts, autotexts = ax.pie(
        amounts,
        labels=None,
        autopct="%1.0f%%",
        colors=colors,
        startangle=90,
        pctdistance=0.8,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )

    for autotext in autotexts:
        autotext.set_fontsize(11)
        autotext.set_fontweight("bold")

    # 圖例
    legend_labels = [f"{cat}  ${amt:,.0f}" for cat, amt in zip(categories, amounts)]
    if CHINESE_FONT:
        ax.legend(
            wedges,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(1, 0.5),
            fontsize=11,
            prop=font_manager.FontProperties(family=CHINESE_FONT, size=11),
        )
    else:
        ax.legend(
            wedges,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(1, 0.5),
            fontsize=11,
        )

    total = sum(amounts)
    if CHINESE_FONT:
        ax.set_title(
            f"{title} 支出分析\n總計 ${total:,.0f}",
            fontsize=16,
            fontweight="bold",
            pad=20,
            fontproperties=font_manager.FontProperties(family=CHINESE_FONT, size=16),
        )
    else:
        ax.set_title(
            f"{title} Expense\nTotal ${total:,.0f}",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

    plt.tight_layout()

    # 儲存到 static/charts/
    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(CHART_DIR, filename)
    fig.savefig(filepath, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    return filename
