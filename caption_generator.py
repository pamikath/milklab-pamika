"""MilkLab Caption Generator (S1).

Usage:
    python caption_generator.py [--dress "ชื่อชุด"] [--n 3]

Reads GOOGLE_API_KEY from env. Generates Thai captions for a Dress Rental Shop item.
"""

import argparse
import os
import sys
from dotenv import load_dotenv
from google import genai


PROMPT_TEMPLATE = """\
คุณคือ Social Media Manager ของร้านเช่าชุด (บริการเช่าชุดราตรี ชุดเดรส ชุดแฟชั่น และชุดออกงานต่างๆ)
จงเขียนแคปชั่นภาษาไทยความยาว 2 ถึง 3 ประโยค เพื่อโปรโมตชุด หรือแนะนำวิธีการแมตช์ชุด ตามข้อมูลด้านล่างนี้:

{item_context}

เงื่อนไข:
- ใช้ภาษาที่น่าดึงดูด เป็นกันเอง และช่วยเสริมความมั่นใจให้ผู้สวมใส่
- เน้นจุดเด่นของชุดที่เข้ากับรูปร่างหรืองานประเภทต่างๆ
- ห้ามใช้ em dash
- ความยาวรวมไม่เกิน 280 ตัวอักษร
"""


def build_prompt_context(dress: str | dict | None) -> str:
    """Convert dress input into a richer prompt context with price and features when available."""
    if isinstance(dress, dict):
        name = dress.get("name") or dress.get("dress") or ""
        details = dress.get("details") or {}
        price = details.get("price")
        features = details.get("features") or []

        parts = [f"ชื่อชุด: {name}" if name else "ชื่อชุด: -"]

        if price is not None:
            parts.append(f"ราคาเช่า: {price}")

        if features:
            parts.append(
                f"จุดเด่น: {', '.join(str(item) for item in features)}"
            )
        return "\n".join(parts)

    return f"ชื่อชุด: {dress}"


def generate_caption(dress: str | dict | None, api_key: str | None = None, max_attempts: int = 3) -> str:

    prompt_context = str(dress) if dress else "ชุดเดรสออกงานสวยๆ"

    actual_api_key = api_key or os.environ.get("GEMINI_API_KEY")

    client = genai.Client(api_key=actual_api_key)

    for _ in range(max_attempts):
        try:
            contents = PROMPT_TEMPLATE.format(item_context=prompt_context)

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents
            )

            caption = (response.text or "").strip()
            if len(caption) <= 280:
                return caption
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการเรียก AI: {e}")

    return caption if 'caption' in locals() else "ไม่สามารถสร้างแคปชั่นได้ในขณะนี้"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Thai captions for Dress Rental Shop items")
    parser.add_argument("--dress", help="ชื่อชุดหรือรายละเอียดชุดที่จะโปรโมต")
    parser.add_argument("-n", "--n", type=int, default=1,
                        help="จำนวนแคปชันที่ต้องการสร้าง (default: 1)")
    args = parser.parse_args(argv)
    if args.n < 1:
        parser.error("--n must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)

    dress = args.dress

    if not dress:
        if not sys.stdin.isatty():
            dress = sys.stdin.read().strip()
        else:
            dress = input("ชุดที่จะโปรโมต: ").strip()

    if not dress:
        print("กรุณาใส่ชื่อชุด")
        return 1

    for index in range(args.n):
        caption = generate_caption(dress=dress)
    print(caption)


if __name__ == "__main__":
    sys.exit(main())
