import telebot
from flask import Flask
import os
from threading import Thread

# ========================================================
# CÀI ĐẶT TOKEN
# ========================================================
# Nếu tạo bot mới, nhớ lấy Token mới từ BotFather và dán vào đây
TOKEN = '8227953136:AAHDE2OwZ9o3ZQ3XeBf4y6fqDRuEtX0Baek'

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# ========================================================
# 1. TÍNH NĂNG SOI KÈO LIVE (RUNNING PRO)
# ========================================================
def nba_running_pro(quarter, time_left, score_h, score_a, bookie_line):
    """
    quarter: Hiệp (1,2,3,4)
    time_left: Phút còn lại (VD: 5.5)
    score_h/a: Điểm chủ/khách
    bookie_line: Kèo Tài Xỉu nhà cái đang ra (Live line)
    """
    # 1. Tính thời gian đã trôi qua (NBA 1 hiệp 12 phút)
    if quarter > 4: # Overtime
        mins_played = 48 + ((quarter - 4) * 5) - time_left
        total_duration = 48 + (quarter - 4) * 5
    else:
        mins_played = ((quarter - 1) * 12) + (12 - time_left)
        total_duration = 48

    if mins_played <= 0: return "⏳ Trận đấu chưa bắt đầu."

    current_total = score_h + score_a
    
    # 2. Tính Tốc độ ghi điểm (PPM - Points Per Minute)
    ppm = current_total / mins_played
    
    # 3. Dự phóng điểm cuối trận (Projected Score)
    projected_score = ppm * total_duration
    
    # 4. Phân tích độ lệch (Edge)
    edge = projected_score - bookie_line
    
    signal = ""
    advice = ""
    
    # Logic Running Pro
    if edge >= 15:
        signal = "🚀 TỐC ĐỘ TÊN LỬA (Pace cực nhanh)"
        advice = f"💰 BIG BET: TÀI (OVER) {bookie_line} ngay! (Dự kiến: {int(projected_score)})"
    elif edge >= 8:
        signal = "🔥 TỐC ĐỘ CAO"
        advice = f"👉 BET: TÀI (OVER) {bookie_line} (Dư {int(edge)} điểm)"
    elif edge <= -15:
        signal = "🧊 ĐÓNG BĂNG (Pace cực chậm)"
        advice = f"💰 BIG BET: XỈU (UNDER) {bookie_line} ngay! (Dự kiến: {int(projected_score)})"
    elif edge <= -8:
        signal = "❄️ TỐC ĐỘ RÙA"
        advice = f"👉 BET: XỈU (UNDER) {bookie_line} (Thiếu {int(abs(edge))} điểm)"
    else:
        signal = "⚖️ KÈO CÂN (Nhà cái ra chuẩn)"
        advice = "👉 SKIP: Bỏ qua, rủi ro cao."

    # Cảnh báo Garbage Time (Giờ rác) nếu cách biệt quá lớn ở hiệp 4
    diff_score = abs(score_h - score_a)
    warning = ""
    if quarter == 4 and diff_score > 20:
        warning = "\n⚠️ **CẢNH BÁO:** Cách biệt >20 điểm -> Garbage Time. Đội hình chính có thể nghỉ, cẩn thận kèo đổi chiều."

    return f"""
🏀 **NBA RUNNING PRO**
⏱ Q{quarter} | {time_left}' left
Scores: {score_h}-{score_a} (Tổng: {current_total})
---------------------------
⚡ **Tốc độ (PPM):** {round(ppm, 2)} điểm/phút
🔮 **Dự phóng End Game:** {int(projected_score)} điểm
📊 **Kèo nhà cái:** {bookie_line}
---------------------------
{signal}
{advice}{warning}
"""

# ========================================================
# 2. TÍNH NĂNG SOI PRE-MATCH PRO (KELLY CRITERION)
# ========================================================
def nba_prematch_pro(home, away, line, avg_h_score, avg_h_allow, avg_a_score, avg_a_allow):
    """
    avg_h_score: Trung bình điểm GHI ĐƯỢC của chủ
    avg_h_allow: Trung bình điểm BỊ THỦNG LƯỚI của chủ (Defensive rating simplified)
    ...tương tự cho khách
    """
    # 1. Tính sức mạnh tấn công/phòng thủ
    # Dự đoán điểm Chủ = (Chủ ghi + Khách thủ) / 2
    proj_home = (avg_h_score + avg_a_allow) / 2
    # Dự đoán điểm Khách = (Khách ghi + Chủ thủ) / 2
    proj_away = (avg_a_score + avg_h_allow) / 2
    
    total_proj = proj_home + proj_away
    
    # 2. Tính Edge (Lợi thế so với nhà cái)
    edge = total_proj - line
    
    pick = ""
    kelly_msg = ""
    
    # 3. Quản lý vốn Kelly (Giả định Odds 1.90 chuẩn)
    # Edge càng cao -> Tự tin càng lớn -> Vào tiền càng nhiều
    confidence = abs(edge) 
    
    if edge > 0:
        pick = "TÀI (OVER)"
        if confidence >= 6:
            kelly_msg = "💰 Vốn khuyến nghị: 5-8% (Kèo thơm)"
        elif confidence >= 3:
            kelly_msg = "👉 Vốn khuyến nghị: 3% (Đánh vừa)"
        else:
            kelly_msg = "⚠️ Value thấp: Bỏ qua hoặc đánh vui 1%"
    else:
        pick = "XỈU (UNDER)"
        if confidence >= 6:
            kelly_msg = "💰 Vốn khuyến nghị: 5-8% (Kèo thơm)"
        elif confidence >= 3:
            kelly_msg = "👉 Vốn khuyến nghị: 3% (Đánh vừa)"
        else:
            kelly_msg = "⚠️ Value thấp: Bỏ qua hoặc đánh vui 1%"

    return f"""
🔮 **NBA PREMATCH PRO**
🏀 {home} vs {away}
---------------------------
📊 **Thống kê:**
- Chủ: Ghi {avg_h_score} | Thủng {avg_h_allow}
- Khách: Ghi {avg_a_score} | Thủng {avg_a_allow}
---------------------------
🧮 **Máy tính dự đoán:**
- Tỷ số: {home} {int(proj_home)} - {int(proj_away)} {away}
- Tổng điểm: **{int(total_proj)}** (Kèo cái: {line})
---------------------------
🎯 **CHỐT KÈO:** {pick}
{kelly_msg}
"""

# ========================================================
# XỬ LÝ LỆNH
# ========================================================

@bot.message_handler(commands=['run'])
def handle_live(message):
    try:
        # Cú pháp: /run [Hiệp] [Phút] [ĐiểmChủ] [ĐiểmKhách] [KèoLive]
        args = message.text.split()[1:]
        if len(args) < 5:
            bot.reply_to(message, "⚠️ Thiếu số! VD: Q2 còn 6.5p, 50-55, Kèo 220\n👉 `/run 2 6.5 50 55 220`")
            return
        res = nba_running_pro(int(args[0]), float(args[1]), int(args[2]), int(args[3]), float(args[4]))
        bot.reply_to(message, res, parse_mode="Markdown")
    except: bot.reply_to(message, "⚠️ Lỗi nhập liệu.")

@bot.message_handler(commands=['pre'])
def handle_pre(message):
    try:
        # Cú pháp: /pre [Chủ] [Khách] [KèoLine] [Chủ_Ghi] [Chủ_Thủng] [Khách_Ghi] [Khách_Thủng]
        content = message.text.replace("/pre", "").strip()
        args = content.split()
        if len(args) < 7:
            bot.reply_to(message, "⚠️ Thiếu số! Cần nhập chỉ số tấn công/phòng thủ.\nGõ /help để xem ví dụ.")
            return
        
        res = nba_prematch_pro(args[0], args[1], float(args[2]), float(args[3]), float(args[4]), float(args[5]), float(args[6]))
        bot.reply_to(message, res, parse_mode="Markdown")
    except Exception as e: bot.reply_to(message, f"⚠️ Lỗi: {e}")

@bot.message_handler(commands=['start', 'help'])
def start(m):
    bot.reply_to(m, """
🏀 **NBA BETTING BOT PRO**

1️⃣ **LIVE RUNNING (/run):**
`/run [Hiệp] [PhútCòn] [ScoreH] [ScoreA] [Line]`
VD: Hiệp 3 còn 8p, tỉ số 80-82, Kèo 230.5
👉 `/run 3 8.0 80 82 230.5`

2️⃣ **PREMATCH (/pre):**
`/pre [Chủ] [Khách] [Line] [ChủGhi] [ChủThủng] [KháchGhi] [KháchThủng]`
VD: Lakers vs Suns, Line 225. Lakers ghi 112 thủng 110. Suns ghi 115 thủng 114.
👉 `/pre Lakers Suns 225 112 110 115 114`
    """)

# SERVER
@server.route('/')
def ping(): return "NBA Bot Alive", 200
def run_web(): server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
def run_bot(): bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    run_bot()
