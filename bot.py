"""Discord 台股自選股追蹤 Bot"""
import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import (
    DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, OWNER_KEY, get_discord_owner_ids
)
from models import init_db, get_session, Watchlist, PriceAlert
from stock import get_stock_info, format_price_message

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

OWNER_IDS = get_discord_owner_ids()

# 警報觸發時，用 hook 通知其他平台（例如 LINE）
# 每個 hook 是一個 async callable，接受 (symbol, info, direction, target_price)
_alert_push_hooks = []


def register_alert_hook(fn):
    _alert_push_hooks.append(fn)


async def _owner_check(interaction: discord.Interaction) -> bool:
    if not OWNER_IDS or interaction.user.id in OWNER_IDS:
        return True
    try:
        await interaction.response.send_message(
            "⛔ 你沒有權限使用這個 Bot", ephemeral=True
        )
    except Exception:
        pass
    return False


bot.tree.interaction_check = _owner_check


# ==================== 事件 ====================
@bot.event
async def on_ready():
    print(f"✅ Discord Bot 已登入: {bot.user} (id={bot.user.id})")
    print(f"📍 加入的 servers ({len(bot.guilds)}):")
    for g in bot.guilds:
        print(f"   - {g.name} (id={g.id}, members={g.member_count})")
    init_db()
    try:
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ 已同步 {len(synced)} 個 slash commands 到 guild {DISCORD_GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            print(f"✅ 已同步 {len(synced)} 個 global slash commands")
        for cmd in synced:
            print(f"   /{cmd.name}")
    except Exception as e:
        print(f"❌ 同步指令失敗: {e}")
        import traceback
        traceback.print_exc()

    if not price_alert_check.is_running():
        price_alert_check.start()


# 手動強制同步（在 Discord 傳 "!sync" 觸發，限 owner）
@bot.command(name="sync")
async def manual_sync(ctx):
    if OWNER_IDS and ctx.author.id not in OWNER_IDS:
        return
    try:
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
        else:
            synced = await bot.tree.sync()
        await ctx.send(f"✅ 已同步 {len(synced)} 個指令")
    except Exception as e:
        await ctx.send(f"❌ 同步失敗: {e}")


# ==================== 自選股指令 ====================
@bot.tree.command(name="add", description="加入自選股")
@app_commands.describe(symbol="台股代號（例：2330）", note="備註（可選）")
async def add_stock(interaction: discord.Interaction, symbol: str, note: str = ""):
    await interaction.response.defer()
    symbol = symbol.strip().upper()

    info = get_stock_info(symbol)
    if not info:
        await interaction.followup.send(f"❌ 找不到股票 `{symbol}`")
        return

    session = get_session()
    try:
        existing = session.query(Watchlist).filter_by(
            user_id=OWNER_KEY, symbol=symbol
        ).first()
        if existing:
            await interaction.followup.send(f"⚠️ `{symbol} {info['name']}` 已在自選股中")
            return

        item = Watchlist(user_id=OWNER_KEY, symbol=symbol, name=info["name"], note=note)
        session.add(item)
        session.commit()
    finally:
        session.close()

    await interaction.followup.send(
        f"✅ 已加入自選股：**{info['name']}** ({symbol})\n目前價格：${info['price']:.2f}"
    )


@bot.tree.command(name="remove", description="移除自選股")
@app_commands.describe(symbol="要移除的股票代號")
async def remove_stock(interaction: discord.Interaction, symbol: str):
    symbol = symbol.strip().upper()
    session = get_session()
    try:
        item = session.query(Watchlist).filter_by(user_id=OWNER_KEY, symbol=symbol).first()
        if not item:
            await interaction.response.send_message(f"❌ `{symbol}` 不在自選股中")
            return
        name = item.name
        session.delete(item)
        session.commit()
    finally:
        session.close()

    await interaction.response.send_message(f"🗑️ 已移除：**{name}** ({symbol})")


@bot.tree.command(name="list", description="查看自選股清單")
async def list_stocks(interaction: discord.Interaction):
    await interaction.response.defer()
    session = get_session()
    try:
        items = session.query(Watchlist).filter_by(user_id=OWNER_KEY).order_by(Watchlist.created_at).all()
    finally:
        session.close()

    if not items:
        await interaction.followup.send("📭 還沒有自選股\n用 `/add <股票代號>` 來新增")
        return

    embed = discord.Embed(title="📋 自選股清單", color=0x3498db)
    for item in items:
        value = f"ID: `{item.symbol}`"
        if item.note:
            value += f"\n備註：{item.note}"
        embed.add_field(name=item.name or item.symbol, value=value, inline=True)

    embed.set_footer(text=f"共 {len(items)} 支 · 用 /watch 查看即時行情")
    await interaction.followup.send(embed=embed)


# ==================== 查價指令 ====================
@bot.tree.command(name="price", description="查詢股價")
@app_commands.describe(symbol="台股代號（例：2330）")
async def price(interaction: discord.Interaction, symbol: str):
    await interaction.response.defer()
    symbol = symbol.strip().upper()
    info = get_stock_info(symbol)
    if not info:
        await interaction.followup.send(f"❌ 找不到股票 `{symbol}`")
        return
    await interaction.followup.send(format_price_message(info))


@bot.tree.command(name="watch", description="查看所有自選股即時行情")
async def watch(interaction: discord.Interaction):
    await interaction.response.defer()
    session = get_session()
    try:
        items = session.query(Watchlist).filter_by(user_id=OWNER_KEY).all()
    finally:
        session.close()

    if not items:
        await interaction.followup.send("📭 還沒有自選股\n用 `/add <股票代號>` 來新增")
        return

    embed = discord.Embed(title="📊 自選股即時行情", color=0x2ecc71)
    loop = asyncio.get_event_loop()

    tasks_list = [loop.run_in_executor(None, get_stock_info, item.symbol) for item in items]
    results = await asyncio.gather(*tasks_list)

    for item, info in zip(items, results):
        if not info:
            embed.add_field(
                name=f"{item.name or item.symbol} ({item.symbol})",
                value="❌ 無法取得資料",
                inline=False,
            )
            continue
        arrow = "🔺" if info["change"] > 0 else ("🔻" if info["change"] < 0 else "▫️")
        sign = "+" if info["change"] > 0 else ""
        embed.add_field(
            name=f"{info['name']} ({item.symbol})",
            value=f"💰 ${info['price']:.2f} {arrow} {sign}{info['change']:.2f} ({sign}{info['change_pct']:.2f}%)",
            inline=False,
        )

    embed.set_footer(text=f"共 {len(items)} 支")
    await interaction.followup.send(embed=embed)


# ==================== 價格警報 ====================
@bot.tree.command(name="alert", description="設定價格警報")
@app_commands.describe(symbol="股票代號", direction="突破或跌破", price="目標價格")
@app_commands.choices(direction=[
    app_commands.Choice(name="突破（高於）", value="above"),
    app_commands.Choice(name="跌破（低於）", value="below"),
])
async def alert(
    interaction: discord.Interaction,
    symbol: str,
    direction: app_commands.Choice[str],
    price: float,
):
    symbol = symbol.strip().upper()
    info = get_stock_info(symbol)
    if not info:
        await interaction.response.send_message(f"❌ 找不到股票 `{symbol}`")
        return

    session = get_session()
    try:
        item = PriceAlert(
            user_id=OWNER_KEY,
            symbol=symbol,
            direction=direction.value,
            target_price=price,
        )
        session.add(item)
        session.commit()
        alert_id = item.id
    finally:
        session.close()

    dir_text = "突破" if direction.value == "above" else "跌破"
    await interaction.response.send_message(
        f"⏰ 警報已設定 #{alert_id}\n**{info['name']}** ({symbol}) {dir_text} ${price:.2f}"
    )


@bot.tree.command(name="alerts", description="查看所有警報")
async def list_alerts(interaction: discord.Interaction):
    session = get_session()
    try:
        items = session.query(PriceAlert).filter_by(user_id=OWNER_KEY, triggered=0).all()
    finally:
        session.close()

    if not items:
        await interaction.response.send_message("📭 沒有未觸發的警報")
        return

    text = "⏰ **價格警報清單**\n"
    for a in items:
        dir_text = "🔺 突破" if a.direction == "above" else "🔻 跌破"
        text += f"  #{a.id} {a.symbol} {dir_text} ${a.target_price:.2f}\n"
    text += "\n用 `/alert_remove <編號>` 移除警報"
    await interaction.response.send_message(text)


@bot.tree.command(name="alert_remove", description="移除警報")
@app_commands.describe(alert_id="警報編號")
async def alert_remove(interaction: discord.Interaction, alert_id: int):
    session = get_session()
    try:
        item = session.query(PriceAlert).filter_by(id=alert_id, user_id=OWNER_KEY).first()
        if not item:
            await interaction.response.send_message(f"❌ 找不到警報 #{alert_id}")
            return
        session.delete(item)
        session.commit()
    finally:
        session.close()
    await interaction.response.send_message(f"🗑️ 已移除警報 #{alert_id}")


@bot.tree.command(name="help", description="查看使用說明")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 台股自選股 Bot 指令說明", color=0x9b59b6)
    embed.add_field(
        name="📋 自選股管理",
        value="`/add <代號> [備註]` — 加入自選股\n`/remove <代號>` — 移除自選股\n`/list` — 查看清單",
        inline=False,
    )
    embed.add_field(
        name="💰 查價",
        value="`/price <代號>` — 查單支股票\n`/watch` — 所有自選股即時行情",
        inline=False,
    )
    embed.add_field(
        name="⏰ 價格警報",
        value="`/alert <代號> <方向> <價格>` — 設定警報\n`/alerts` — 查看警報\n`/alert_remove <編號>` — 移除警報",
        inline=False,
    )
    embed.set_footer(text="資料來源：Yahoo Finance · 警報同步推送到 LINE")
    await interaction.response.send_message(embed=embed)


# ==================== 價格警報定時檢查 ====================
@tasks.loop(minutes=5)
async def price_alert_check():
    """每 5 分鐘檢查一次價格警報，觸發時推送到 Discord DM + LINE"""
    session = get_session()
    try:
        alerts = session.query(PriceAlert).filter_by(triggered=0).all()
        if not alerts:
            return

        symbols = {a.symbol for a in alerts}
        loop = asyncio.get_event_loop()
        price_map = {}
        for sym in symbols:
            info = await loop.run_in_executor(None, get_stock_info, sym)
            if info:
                price_map[sym] = info

        for a in alerts:
            info = price_map.get(a.symbol)
            if not info:
                continue
            current = info["price"]
            hit = (a.direction == "above" and current >= a.target_price) or \
                  (a.direction == "below" and current <= a.target_price)
            if not hit:
                continue

            dir_text = "突破" if a.direction == "above" else "跌破"
            msg = (
                f"🚨 價格警報觸發！\n"
                f"{info['name']} ({a.symbol}) 已{dir_text}目標價 ${a.target_price:.2f}\n"
                f"目前價格：${current:.2f}"
            )

            # Discord DM 給所有 owner
            for owner_id in OWNER_IDS:
                try:
                    user = await bot.fetch_user(owner_id)
                    await user.send(msg)
                except Exception as e:
                    print(f"Discord 推送失敗 ({owner_id}): {e}")

            # 呼叫所有註冊的 hooks（例如 LINE 推播）
            for hook in _alert_push_hooks:
                try:
                    await hook(a.symbol, info, a.direction, a.target_price)
                except Exception as e:
                    print(f"Alert hook 推送失敗: {e}")

            a.triggered = 1

        session.commit()
    finally:
        session.close()


def run_bot():
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError("請設定 DISCORD_BOT_TOKEN 環境變數")
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run_bot()
