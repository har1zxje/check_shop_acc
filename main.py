import discord
from discord.ext import commands
import requests
import datetime
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import time

# --- PHẦN 1: FLASK WEB SERVER (TỐI ƯU CHO RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Online and Alive!"

def run():
    # Render yêu cầu lắng nghe trên Port hệ thống cấp
    # Chúng ta ưu tiên lấy PORT từ Environment, mặc định là 10000
    port = int(os.environ.get("PORT", 10000))
    print(f"--- Flask đang khởi động tại Port: {port} ---")
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True # Đặt daemon để thread này không bị kẹt khi tắt bot
    t.start()

# --- PHẦN 2: CẤU HÌNH BOT DISCORD ---
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')

try:
    from shop_acc import MY_ACCOUNTS
except ImportError:
    MY_ACCOUNTS = []

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='?v', intents=intents)

# (Giữ nguyên các hàm get_time_ago, get_val_details và command rank của bạn ở đây)
# ... [Phần code xử lý Valorant giữ nguyên như cũ] ...

@bot.event
async def on_ready():
    print(f'✅ Bot Discord đã đăng nhập: {bot.user}')

# --- PHẦN 3: KHỞI CHẠY (QUAN TRỌNG) ---
if __name__ == "__main__":
    # 1. Bật Flask trước
    keep_alive()
    
    # 2. Nghỉ 2 giây để chắc chắn Flask đã chiếm được Port trước khi Bot chạy
    time.sleep(2) 
    
    # 3. Chạy Bot
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ LỖI: Thiếu DISCORD_TOKEN trong Environment Variables!")
