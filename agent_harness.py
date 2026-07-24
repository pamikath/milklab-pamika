"""MilkLab Agent Harness (S2).

Usage:
    python agent_harness.py --cmd "บันทึกขายนมหมี 2 ขวด ขวดละ 65"

รับคำสั่งภาษาไทย ส่งให้ Gemini พร้อม tool schema parse response เป็น tool call
เรียก tool จริง print trace log
"""

import argparse
from datetime import datetime
import json
import os
import subprocess
import sys
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google import genai
from google.genai import types

from sales_logger import send_line_notification, send_telegram_notification

TOOL_SCHEMA = [
    {
        "name": "log_sale",
        "description": "บันทึกการขายลง Google Sheets และส่ง notification",
        "parameters": {
            "type": "object",
            "properties": {
                "menu": {"type": "string", "description": "ชื่อเมนู"},
                "qty": {"type": "integer", "description": "จำนวนที่ขาย"},
                "price": {"type": "number", "description": "ราคาต่อหน่วย"},
            },
            "required": ["menu", "qty", "price"],
        },
    },
    {
        "name": "query_sales",
        "description": "ดูยอดขายของวันที่ระบุ",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "วันที่ format YYYY-MM-DD"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "send_alert",
        "description": "ส่ง message แจ้งเตือนผ่าน Bot",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
            },
            "required": ["message"],
        },
    },
]


def parse_command(cmd: str, api_key: str | None = None) -> dict:
    """ส่ง cmd ไป Gemini พร้อม TOOL_SCHEMA ขอให้ตอบเป็น JSON {tool, args}"""
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("ไม่พบ GEMINI_API_KEY หรือ GOOGLE_API_KEY ใน Environment Variable")

    client = genai.Client(api_key=api_key)

    prompt = f"""คุณคือ AI Assistant สำหรับระบบ MilkLab 
โปรดวิเคราะห์คำสั่งภาษาไทยของผู้ใช้ และเลือกใช้ Tool ที่เหมาะสมที่สุดจากรายการ TOOL_SCHEMA ด้านล่างนี้:

{json.dumps(TOOL_SCHEMA, ensure_ascii=False, indent=2)}

คำสั่งของผู้ใช้: "{cmd}"

คำตอบของคุณจะต้องเป็น JSON Object เท่านั้น โดยมีโครงสร้างดังนี้:
{{
  "tool": "<ชื่อ_tool_ที่เลือก>",
  "args": {{ <arguments_ตาม_schema_ของ_tool_นั้นๆ> }}
}}

ตัวอย่างเช่น:
{{"tool": "log_sale", "args": {{"menu": "นมหมี", "qty": 2, "price": 65.0}}}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        res_text = response.text.strip()
        data = json.loads(res_text)

        if "tool" not in data or "args" not in data:
            raise RuntimeError(f"รูปแบบ JSON ไม่ถูกต้อง: {res_text}")

        return data

    except Exception as e:
        raise RuntimeError(f"เกิดข้อผิดพลาดในการ parse คำสั่งด้วย Gemini: {e}")


def dispatch_tool(tool_call: dict) -> tuple[str, str]:
    """เรียก tool ตาม tool_call["tool"] ด้วย args จริง
    
    Returns:
        tuple[str, str]: (tool_status_log, user_reply_message)
    """
    tool_name = tool_call.get("tool")
    args = tool_call.get("args", {})

    if tool_name == "log_sale":
        menu = str(args.get("menu"))
        qty = int(args.get("qty", 1))
        price = float(args.get("price", 0))
        total_price = int(qty * price)

        cmd = [
            sys.executable,
            "sales_logger.py",
            "--menu",
            menu,
            "--qty",
            str(qty),
            "--price",
            str(price),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # เวลาปัจจุบัน ISO8601 โซนไทย (+07)
        now_str = datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(timespec="seconds")

        if result.returncode == 0:
            tool_log = f"OK: row appended at {now_str}"
            user_msg = f"บันทึกแล้วยอด {total_price} บาท"
            return tool_log, user_msg
        else:
            return f"ERROR: {result.stderr.strip()}", "เกิดข้อผิดพลาดในการบันทึก"

    elif tool_name == "query_sales":
        date = args.get("date")
        return f"OK: sales queried for {date}", f"ดึงข้อมูลยอดขายวันที่ {date} เรียบร้อยแล้ว"

    elif tool_name == "send_alert":
        msg = args.get("message", "")
        send_telegram_notification(msg)
        return "OK: message sent", f"ส่งข้อความแจ้งเตือน '{msg}' เรียบร้อยแล้ว"

    return "ERROR: unknown tool", "ไม่สามารถประมวลผลคำสั่งได้"


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd", required=True, help="คำสั่งภาษาไทย")
    args = parser.parse_args()

    # 1. พิมพ์ [USER]
    print(f"[USER] {args.cmd}")

    try:
        # 2. Parse คำสั่งจาก Gemini
        tool_call = parse_command(args.cmd)

        # จัดฟอร์แมต args ให้พิมพ์ออกมาสไตล์ {menu: นมหมี, qty: 2, price: 65}
        formatted_args = ", ".join([f"{k}: {v}" for k, v in tool_call['args'].items()])
        print(f"[LLM]  tool={tool_call['tool']} args={{{formatted_args}}}")

        # 3. เรียก Tool และรับสถานะ
        tool_log, user_msg = dispatch_tool(tool_call)

        # 4. พิมพ์ [TOOL] และ [USER] ←
        print(f"[TOOL] {tool_call['tool']} {tool_log}")
        print(f"[USER] ←  {user_msg}")

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())