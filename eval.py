import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# 1. โหลดคีย์จากไฟล์ .env
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("ไม่พบ GOOGLE_API_KEY ในไฟล์ .env")

genai.configure(api_key=GOOGLE_API_KEY)

# 2. ฟังก์ชันสำหรับประเมินผล


def evaluate_interaction(trace_data):
    # ปรับคีย์ด้านล่างนี้ให้ตรงกับโครงสร้างในไฟล์ traces.jsonl ของคุณ
    user_query = trace_data.get("user_query", "ไม่มีคำถาม")
    bot_response = trace_data.get("bot_response", "ไม่มีคำตอบ")
    context_used = trace_data.get("context", "")

    # สร้าง Prompt ให้ Gemini ทำหน้าที่เป็นผู้ประเมิน
    eval_prompt = f"""
    คุณเป็นผู้เชี่ยวชาญด้านการประเมินคุณภาพของ RAG Chatbot
    โปรดประเมินคำตอบของแชตบอตโดยอิงจากคำถามของผู้ใช้และข้อมูลอ้างอิง (Context) ที่กำหนดให้
    
    คำถามของผู้ใช้: {user_query}
    ข้อมูลอ้างอิง (Context): {context_used}
    คำตอบของแชตบอต: {bot_response}
    
    จงให้คะแนนตั้งแต่ 1 ถึง 5 (5 คือดีที่สุด) ในด้านความแม่นยำ (Accuracy) และความสอดคล้อง (Relevance) พร้อมให้เหตุผลสั้นๆ
    
    รูปแบบการตอบ:
    คะแนน: [1-5]/5
    เหตุผล: [คำอธิบายของคุณ]
    """

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(eval_prompt)
    return response.text

# 3. ฟังก์ชันหลักสำหรับอ่านไฟล์และรันประเมิน


def main():
    trace_file = "traces.jsonl"

    if not os.path.exists(trace_file):
        print(
            f"ไม่พบไฟล์ {trace_file} กรุณาตรวจสอบให้แน่ใจว่ามีการแชตเพื่อสร้าง log ไว้แล้ว")
        return

    print("🚀 เริ่มต้นการประเมินผล (Evaluation) จากไฟล์ traces.jsonl...")

    with open(trace_file, 'r', encoding='utf-8') as f:
        for index, line in enumerate(f):
            if line.strip():
                try:
                    data = json.loads(line)
                    print(f"\n--- 📝 รายการที่ {index + 1} ---")
                    print(f"คำถาม: {data.get('user_query', 'N/A')}")

                    # เรียกใช้งานฟังก์ชันประเมิน
                    evaluation_result = evaluate_interaction(data)
                    print("\n[ผลการประเมินจาก Gemini]")
                    print(evaluation_result)
                    print("-" * 40)

                except json.JSONDecodeError:
                    print(
                        f"บรรทัดที่ {index + 1} ไม่สามารถอ่านรูปแบบ JSON ได้")


if __name__ == "__main__":
    main()
