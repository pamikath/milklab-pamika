"""MilkLab Caption Generator (S1).

Usage:
    python caption_generator.py [--menu "ชื่อเมนู"] [--n 3]

Reads GOOGLE_API_KEY from env. Generates Thai captions for a milk menu item.
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from google import genai


PROMPT_TEMPLATE = """\
คุณคือ social media manager ของร้าน MilkLab° ร้านนมสดกลางคืน

จงเขียนแคปชั่นภาษาไทย 2 ถึง 3 ประโยคโปรโมตเมนูตามข้อมูลด้านล่าง:
{menu_context}

เงื่อนไข:
- โทนสนุก ใช้คำง่าย ใส่ emoji ได้
- ต้องมี call-to-action ปิดท้าย เช่น สั่งเลย หรือ ทักแชท
- ห้ามใช้ em dash
- ความยาวรวมไม่เกิน 280 ตัวอักษร
"""


def build_prompt_context(menu: str | dict | None) -> str:
    """Convert menu input into a richer prompt context with price and ingredients when available."""
    if isinstance(menu, dict):
        name = menu.get("name") or menu.get("menu") or ""
        details = menu.get("details") or {}
        price = details.get("price")
        ingredients = details.get("ingredients") or []
        parts = [f"ชื่อเมนู: {name}" if name else "ชื่อเมนู: -"]
        if price is not None:
            parts.append(f"ราคา: {price}")
        if ingredients:
            parts.append(
                f"ส่วนผสม: {', '.join(str(item) for item in ingredients)}")
        return "\n".join(parts)

    return f"ชื่อเมนู: {menu}"


def generate_caption(menu: str | dict | None, api_key: str | None = None, max_attempts: int = 3) -> str:
    """Generate a Thai caption for the given milk menu item, retrying when it is too long."""
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not set in env or argument")

    prompt_context = build_prompt_context(menu)
    for attempt in range(1, max_attempts + 1):
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=PROMPT_TEMPLATE.format(menu_context=prompt_context),
        )
        caption = (response.text or "").strip()
        if len(caption) <= 280:
            return caption

    return caption


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Thai captions for MilkLab menu items")
    parser.add_argument("--menu", help="ชื่อเมนูที่จะโปรโมต")
    parser.add_argument("-n", "--n", type=int, default=1,
                        help="จำนวนแคปชันที่ต้องการสร้าง (default: 1)")
    args = parser.parse_args(argv)
    if args.n < 1:
        parser.error("--n must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)

    menu = args.menu
    if not menu:
        if not sys.stdin.isatty():
            menu = sys.stdin.read().strip()
        else:
            menu = input("เมนูที่จะโปรโมต: ").strip()

    if not menu:
        print("กรุณาใส่ชื่อเมนู")
        return 1

    for index in range(args.n):
        caption = generate_caption(menu)
        if args.n > 1:
            print(f"แคปชันที่ {index + 1}:")
        print(caption)
        if index < args.n - 1:
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
