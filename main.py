import discord
from discord.ext import commands
import requests
import datetime
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import time
import gc

# --- PHẦN 1: FLASK WEB SERVER (GIỮ BOT THỨC 24/7 TRÊN RENDER) ---
app = Flask('')

@app.route('/')
def home():
    now = datetime.datetime.now().strftime('%H:%M:%S')
    return f"Bot is Online and Alive! Last system ping: {now}"

def run():
    # Lấy cổng từ hệ thống Render, mặc định là 10000
    port = int(os.environ.get("PORT", 10000))
    print(f"--- Flask đang bắt đầu lắng nghe tại Port: {port} ---")
    # Tắt debug và reloader để tiết kiệm RAM tối đa cho gói Free
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True 
    t.start()

# --- PHẦN 2: CẤU HÌNH BOT DISCORD ---
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')

# Nhập danh sách tài khoản từ file shop_acc.py
try:
    from shop_acc import MY_ACCOUNTS
except ImportError:
    MY_ACCOUNTS = []
    print("❌ LỖI: Không tìm thấy file shop_acc.py trên hệ thống!")

# Cài đặt Intents (Nhớ bật Message Content Intent trong Discord Developer Portal)
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
        # Gọi API MMR
        r_mmr = requests.get(mmr_url, headers=headers, timeout=10)
        time.sleep(0.3) # Giãn cách cực ngắn tránh lỗi API Rate Limit của HenrikDev
        
        # Gọi API History
        r_hist = requests.get(history_url, headers=headers, timeout=10)
        
        if r_mmr.status_code == 200 and r_hist.status_code == 200:
            m_data = r_mmr.json().get('data')
            h_data = r_hist.json().get('data', [])[:5]
            
            if not m_data: return None

            history_list = []
            for m in h_data:
                change = m.get('mmr_change_to_last_game', 0)
                t_ago = get_time_ago(m.get('date_raw'))
                
                # SỬA LỖI DẤU TRÙNG LẶP: Dùng abs() để đảm bảo không bị hiện - -22
                if change > 0: mark, val = "+ ", change
                elif change < 0: mark, val = "- ", abs(change)
                else: mark, val = "  ", 0
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
    except Exception:
        return None
    return None

@bot.command()
async def rank(ctx):
    # Tin nhắn phản hồi ban đầu
    status_msg = await ctx.send("🔍 **Đang quét và sắp xếp danh sách theo MMR...**")
    
    results = []
    for acc in MY_ACCOUNTS:
        data = get_val_details(acc['name'], acc['tag'])
        if data:
            results.append(data)
        # NGHỈ 1.5 GIÂY giữa mỗi account: Đây là khóa để tránh lỗi 429 Too Many Requests
        time.sleep(1.5)

    if not results:
        return await status_msg.edit(content="❌ Không thể lấy dữ liệu từ API. Hãy kiểm tra API Key hoặc tên tài khoản.")

    # Sắp xếp giảm dần theo Elo (Người MMR cao nhất lên đầu)
    success_data = sorted(results, key=lambda x: x['elo'], reverse=True)
    
    embed = discord.Embed(
        title="🛡️ HỆ THỐNG PHÂN TÍCH RANK VALORANT",
        description="Dữ liệu được sắp xếp theo **MMR (Elo)** cao nhất xuống thấp nhất.",
        color=0xfa4454
    )

    for res in success_data:
        history_text = "\n".join(res['history'])
        val_info = (
            f"**Hạng:** `{res['rank_name']}` — **{res['rr']} RR**\n"
            f"**Lịch sử gần đây:**\n```diff\n{history_text if history_text else 'Chưa có dữ liệu'}\n```"
            f"**Elo hiện tại:** `{res['elo']}`\n"
            f"──────────────────"
        )
        embed.add_field(name=f"👤 {res['name']}#{res['tag']}", value=val_info, inline=False)
        
        # Thumbnail lấy hình rank của người đứng Top 1 MMR
        if res == success_data[0]:
            embed.set_thumbnail(url=res['rank_icon'])

    now_time = datetime.datetime.now().strftime('%H:%M - %d/%m/%Y')
    embed.set_footer(text=f"Yêu cầu bởi {ctx.author.name} • {now_time}", icon_url=ctx.author.display_avatar.url)
    
    # Sửa tin nhắn chờ thành bảng kết quả
    await status_msg.edit(content=None, embed=embed)
    
    # Dọn dẹp RAM ngay sau khi xong việc nặng để Render không tắt bot
    gc.collect()

@bot.event
async def on_ready():
    print(f'✅ Bot Discord đã trực tuyến: {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)

# --- PHẦN 3: KHỞI CHẠY VỚI CHẾ ĐỘ TỰ KẾT NỐI LẠI (GIẢI QUYẾT LỖI 429) ---
if __name__ == "__main__":
    # Khởi động Flask trước
    keep_alive()
    time.sleep(5)
    
    while True:
        try:
            if DISCORD_TOKEN:
                print("🚀 Đang khởi động Discord Client...")
                bot.run(DISCORD_TOKEN)
            else:
                print("❌ KHÔNG CÓ DISCORD_TOKEN. Hãy kiểm tra Environment Variables.")
                break
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print("⚠️ CẢNH BÁO: Discord đang chặn yêu cầu (Rate Limit). Nghỉ 60s để phục hồi...")
                time.sleep(60)
            else:
                print(f"❌ Lỗi HTTP: {e}. Thử lại sau 10s...")
                time.sleep(10)
        except Exception as e:
            print(f"❌ Lỗi hệ thống: {e}. Đang tái khởi động sau 10s...")
            time.sleep(10)
