"""MilkLab Sales Logger (S2).

Usage:
    python sales_logger.py --menu "นมหมีฮอกไกโด" --qty 2 --price 65

Reads GOOGLE_SHEETS_CREDENTIALS and TELEGRAM_BOT_TOKEN (or LINE_CHANNEL_TOKEN) from env.
Appends row [timestamp, menu, qty, price, total] to a Google Sheet,
then sends a notification via Telegram or LINE bot.

นักศึกษาต้องเติม TODO ใน 4 จุดด้านล่างใน Session 2 Lab 1.3
"""

import argparse
import os
import sys
import json
from datetime import datetime
import requests
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_sheets_client() -> gspread.Client:
    """ดึง Credentials จาก Environment Variable และสร้าง gspread client."""
    creds_json_str = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_json_str:
        raise ValueError(
            "ไม่พบ GOOGLE_SHEETS_CREDENTIALS ใน Environment Variable")

    creds_dict = json.loads(creds_json_str)
    credentials = Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES)
    return gspread.authorize(credentials)


# ------------------------------------------------------------------
# ข้อ 3: ฟังก์ชันส่ง Notification (เลือกใช้ตาม Channel ที่ตั้งไว้)
# ------------------------------------------------------------------
def send_telegram_notification(message: str) -> None:
    """ส่งการแจ้งเตือนเข้า Telegram Bot."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[Warning] ไม่ได้ตั้งค่า Telegram Secrets — ข้ามการส่ง Notification")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"[Warning] ส่ง Telegram ไม่สำเร็จ: {response.text}")


def send_line_notification(message: str) -> None:
    """ส่งการแจ้งเตือนเข้า LINE OA (Messaging API)."""
    channel_token = os.environ.get("LINE_CHANNEL_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")  # หรือ Chat/Group ID

    if not channel_token or not user_id:
        print("[Warning] ไม่ได้ตั้งค่า LINE Secrets — ข้ามการส่ง Notification")
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_token}",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}]
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"[Warning] ส่ง LINE ไม่สำเร็จ: {response.text}")


# ------------------------------------------------------------------
# Main Function
# ------------------------------------------------------------------
def main() -> int:
    # ข้อ 1: อ่าน Command-line arguments (--menu, --qty, --price)
    parser = argparse.ArgumentParser(description="MilkLab Sales Logger")
    parser.add_argument("--menu", type=str, required=True, help="ชื่อเมนู")
    parser.add_argument("--qty", type=int, required=True, help="จำนวนที่ขาย")
    parser.add_argument("--price", type=float,
                        required=True, help="ราคาต่อหน่วย")
    parser.add_argument("--sheet-name", type=str,
                        default="Sales_Logger", help="ชื่อไฟล์ Google Sheet")

    args = parser.parse_args()

    # คำนวณราคารวม
    total = args.qty * args.price
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ข้อ 4: Handle case Sheets ไม่ accessible (Catch Exceptions และ exit 1)
    try:
        client = get_sheets_client()
        # เปิดไฟล์ Sheet ตามชื่อ (ระบุชื่อไฟล์ Sheet ของคุณ)
        spreadsheet = client.open(args.sheet_name)
        sheet = spreadsheet.sheet1  # เลือก Worksheet แผ่นแรก
    except Exception as e:
        print("\n❌ [ERROR] ไม่สามารถเข้าถึง Google Sheets ได้!")
        print(f"สาเหตุ: {e}")
        print("💡 วิธีแก้ไข:")
        print(" 1. ตรวจสอบว่าแชร์ Sheet ให้กับ Email ของ Service Account แล้วหรือยัง")
        print(" 2. ตรวจสอบว่าตั้งค่า GOOGLE_SHEETS_CREDENTIALS ใน Secrets ถูกต้องหรือไม่")
        print(" 3. ตรวจสอบชื่อไฟล์ Google Sheet ว่าตรงกันหรือไม่\n")
        sys.exit(1)

    # ข้อ 2: Append row [timestamp, menu, qty, price, total] ลง Sheets
    row_data = [timestamp, args.menu, args.qty, args.price, total]
    sheet.append_row(row_data)
    print(f"✅ บันทึกยอดขายสำเร็จ: {row_data}")

    # ข้อ 3: ส่ง Notification เข้า Bot
    notify_msg = (
        f"🥛 *MilkLab Sales Alert*\n"
        f"---------------------\n"
        f"📌 *เมนู:* {args.menu}\n"
        f"🔢 *จำนวน:* {args.qty} แก้ว\n"
        f"💵 *ราคาต่อแก้ว:* {args.price} บาท\n"
        f"💰 *ยอดรวม:* {total:.2f} บาท\n"
        f"🕒 *เวลา:* {timestamp}"
    )

    # เลือกใช้ฟังก์ชันแจ้งเตือนตามที่คุณตั้งค่า Secret ไว้
    send_telegram_notification(notify_msg)
    # send_line_notification(notify_msg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
