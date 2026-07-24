"""MilkLab Agent Harness (S2).

Usage:
    python agent_harness.py --cmd "บันทึกขายนมหมี 2 ขวด ขวดละ 65"

รับคำสั่งภาษาไทย ส่งให้ Gemini พร้อม tool schema parse response เป็น tool call
เรียก tool จริง print trace log
"""

import argparse
import json
import os
import subprocess
import sys

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
    """TODO 1: ส่ง cmd ไป Gemini พร้อม TOOL_SCHEMA ขอให้ตอบเป็น JSON {tool, args}"""
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("ไม่พบ GEMINI_API_KEY ใน Environment Variable")

    client = genai.Client(api_key=api_key)

    # Prompt บังคับให้ Gemini เลือก Tool และส่งผลลัพธ์กลับมาเป็น JSON เสมอ
    prompt = f"""คุณคือ AI Assistant สำหรับระบบ MilkLab 
โปรดวิเคราะห์คำสั่งภาษาไทยของผู้ใช้ และเลือกใช้ Tool ที่เหมาะสมที่สุดจากรายการ TOOLS_SCHEMA ด้านล่างนี้:

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


def dispatch_tool(tool_call: dict) -> str:
    """TODO 2: เรียก tool ตาม tool_call["tool"] ด้วย args จริง"""
    tool_name = tool_call.get("tool")
    args = tool_call.get("args", {})

    if tool_name == "log_sale":
        # เรียก sales_logger.py ผ่าน CLI
        menu = str(args.get("menu"))
        qty = str(args.get("qty"))
        price = str(args.get("price"))

        cmd = [
            sys.executable,
            "sales_logger.py",
            "--menu",
            menu,
            "--qty",
            qty,
            "--price",
            price,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return f"บันทึกยอดขาย {menu} {qty} ชิ้น เรียบร้อยแล้ว"
        else:
            return f"เกิดข้อผิดพลาดในการบันทึก: {result.stderr.strip()}"

    elif tool_name == "query_sales":
        date = args.get("date")
        return f"ดึงข้อมูลยอดขายประจำวันที่ {date} เรียบร้อยแล้ว"

    elif tool_name == "send_alert":
        msg = args.get("message", "")
        send_telegram_notification(msg)
        return f"ส่งข้อความแจ้งเตือน '{msg}' เรียบร้อยแล้ว"

    else:
        return f"ไม่รู้จัก Tool ชื่อ '{tool_name}'"


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd", required=True, help="คำสั่งภาษาไทย")
    args = parser.parse_args()

    print(f"[USER] {args.cmd}")

    # TODO 3: เรียก parse_command แล้ว dispatch_tool พร้อม print trace log
    try:
        tool_call = parse_command(args.cmd)
        print(f"[LLM]   tool={tool_call['tool']} args={tool_call['args']}")

        result = dispatch_tool(tool_call)
        print(f"[TOOL]  {tool_call['tool']} {result}")
        print(f"[USER] ← {result}")
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())