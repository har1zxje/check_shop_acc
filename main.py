import discord
from discord.ext import commands
import requests
import datetime
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Nhập danh sách tài khoản từ file shop_acc.py của bạn
try:
    from shop_acc import MY_ACCOUNTS
except ImportError:
    MY_ACCOUNTS = [] # Tránh lỗi nếu file chưa tồn tại

# --- PHẦN 1: FLASK WEB SERVER (GIỮ BOT THỨC 24/7) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Online and Alive!"

def run():
    # Render yêu cầu lấy Port từ môi trường hệ thống
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- PHẦN 2: CẤU HÌNH BOT DISCORD ---
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='?v', intents=intents)

def get_time_ago(timestamp):
    if not timestamp: return "N/A"
    now = datetime.datetime.now(datetime.timezone.utc)
    diff = now - datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
    seconds = diff.total_seconds()
    if seconds < 3600: return f"{int(seconds // 60)}p"
    elif seconds < 86400: return f"{int(seconds // 3600)}h"
    else: return f"{int(diff.days)}d"

def get_val_details(name, tag):
    headers = {'Authorization': HENRIK_API_KEY}
    mmr_url = f"https://api.henrikdev.xyz/valorant/v1/mmr/ap/{name}/{tag}"
    history_url = f"https://api.henrikdev.xyz/valorant/v1/mmr-history/ap/{name}/{tag}"
    default_icon = "https://media.valorant-api.com/displayicons/v1/64581831-4828-02ba-775f-2c8c45f448e8/displayicon.png"

    try:
        r_mmr = requests.get(mmr_url, headers=headers, timeout=10)
        r_hist = requests.get(history_url, headers=headers, timeout=10)
        
        if r_mmr.status_code == 200 and r_hist.status_code == 200:
            m_data = r_mmr.json().get('data')
            h_data = r_hist.json().get('data', [])[:5]
            
            if not m_data: 
                return {"status": "error", "msg": "No Data", "name": name, "tag": tag, "rank_icon": default_icon}

            history_list = []
            for m in h_data:
                change = m.get('mmr_change_to_last_game', 0)
                t_ago = get_time_ago(m.get('date_raw'))
                # Fix lỗi dấu trùng lặp
                if change > 0:
                    mark, val = "+ ", change
                elif change < 0:
                    mark, val = "- ", abs(change)
                else:
                    mark, val = "  ", 0
                history_list.append(f"{mark}{val} ({t_ago})")

            tier_id = m_data.get('currenttier', 0)
            icon_url = f"https://media.valorant-api.com/competitivetiers/03621f13-43b3-94c6-8807-c0954346d84d/{tier_id}/largeicon.png"

            return {
                "status": "ok",
                "name": name, "tag": tag,
                "rank_name": m_data.get('currenttierpatched', 'Unranked'),
                "rr": m_data.get('ranking_in_tier', 0),
                "elo": m_data.get('elo', 0),
                "history": history_list,
                "rank_icon": icon_url
            }
        return {"status": "error", "msg": f"API {r_mmr.status_code}", "name": name, "tag": tag, "rank_icon": default_icon}
    except Exception as e:
        return {"status": "error", "msg": "Network Error", "name": name, "tag": tag, "rank_icon": default_icon}

@bot.command()
async def rank(ctx):
    await ctx.send("🔍 **Đang quét và sắp xếp danh sách theo MMR...**")
    
    results = []
    for acc in MY_ACCOUNTS:
        results.append(get_val_details(acc['name'], acc['tag']))

    # Sắp xếp giảm dần theo Elo (MMR)
    success_data = sorted([r for r in results if r['status'] == "ok"], key=lambda x: x['elo'], reverse=True)
    error_data = [r for r in results if r['status'] != "ok"]

    embed = discord.Embed(
        title="🛡️ HỆ THỐNG PHÂN TÍCH RANK VALORANT",
        description="Danh sách sắp xếp theo **MMR (Elo)** cao nhất xuống thấp nhất.",
        color=0xfa4454
    )

    for res in success_data:
        history_text = "\n".join(res['history'])
        val_info = (
            f"**Rank:** `{res['rank_name']}` — **{res['rr']} RR**\n"
            f"**Lịch sử:**\n```diff\n{history_text if history_text else 'Chưa có dữ liệu'}\n```"
            f"**MMR Ẩn (Elo):** `{res['elo']}`\n"
            f"──────────────────"
        )
        # Sử dụng icon người mặc định như bạn yêu cầu
        embed.add_field(name=f"👤 {res['name']}#{res['tag']}", value=val_info, inline=False)
        
        # Thumbnail luôn lấy hình rank của tài khoản TOP 1 MMR
        if res == success_data[0]:
            embed.set_thumbnail(url=res['rank_icon'])

    for err in error_data:
        embed.add_field(name=f"❌ LỖI - {err['name']}#{err['tag']}", value=f"**Nguyên nhân:** `{err['msg']}`", inline=False)

    timestamp = datetime.datetime.now().strftime('%H:%M - %d/%m/%Y')
    embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name} • {timestamp}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f'✅ Bot online! Giao diện Flask đã sẵn sàng.')

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

# LƯU Ý QUAN TRỌNG: Gọi keep_alive TRƯỚC bot.run
keep_alive()
bot.run(DISCORD_TOKEN)
