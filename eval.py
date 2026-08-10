import matplotlib.pyplot as plt
import numpy as np
# TODO: Import ตัว Vector Database หรือฟังก์ชัน Query จาก app.py ของคุณมาที่นี่
# ตัวอย่าง: from app import collection

# 1. เตรียม Ground Truth: 10 คำถาม + ID ของ Chunk ที่ควรจะตอบคำถามนั้นได้
ground_truths = [
    # กลุ่มคำถามที่ควรอ้างอิง Chunk 1 (ข้อมูลร้านทั่วไป, เวลาเปิดปิด, พิกัด)
    {"query": "ร้านเปิดกี่โมงคะ", "expected_chunk_id": "chunk_1"},
    {"query": "วันจันทร์ร้านเปิดไหม", "expected_chunk_id": "chunk_1"},
    {"query": "ร้านตั้งอยู่ที่ไหน", "expected_chunk_id": "chunk_1"},

    # กลุ่มคำถามที่ควรอ้างอิง Chunk 2 (เงื่อนไขการส่ง, การจอง, เมนูทางเลือก)
    {"query": "มีเมนู vegan ไหม", "expected_chunk_id": "chunk_2"},
    {"query": "ส่งเดลิเวอรี่ไกลแค่ไหน", "expected_chunk_id": "chunk_2"},
    {"query": "ค่าส่งคิดยังไง", "expected_chunk_id": "chunk_2"},
    {"query": "จองล่วงหน้าต้องทำยังไง", "expected_chunk_id": "chunk_2"},
    {"query": "มีขั้นต่ำในการสั่งไหม", "expected_chunk_id": "chunk_2"},

    # กลุ่มคำถามที่ควรอ้างอิง Chunk 3 (เมนูและราคา)
    {"query": "นมหมีฮอกไกโดราคาเท่าไหร่", "expected_chunk_id": "chunk_3"},
    {"query": "นมโกโก้บราวนี่แก้วขนาดกี่ ml", "expected_chunk_id": "chunk_3"}
]

precisions = []
recalls = []
top1_scores = []

print("🚀 เริ่มทำการประเมินระบบ Retrieval (Top-K = 3)...\n")

# 2. รัน Retrieval สำหรับแต่ละคำถาม
for item in ground_truths:
    query = item["query"]
    expected_id = item["expected_chunk_id"]

    # TODO: นำคำสั่งดึงข้อมูล Vector DB ของคุณมาใส่ตรงนี้
    # ตัวอย่างสำหรับ ChromaDB:
    # results = collection.query(query_texts=[query], n_results=3)
    # retrieved_ids = results['ids'][0]
    # distances = results['distances'][0]

    # --- ข้อมูลจำลอง (ลบออกแล้วใช้ของจริง) ---
    retrieved_ids = ["chunk_1", "chunk_5", "chunk_8"]
    distances = [0.25, 0.45, 0.60]  # คะแนน Similarity/Distance
    # -------------------------------------

    # เก็บ Top-1 Score ไว้ทำ Histogram
    if distances:
        top1_scores.append(distances[0])

    # เช็กว่าใน 3 อันดับแรก มี Chunk ที่ถูกต้องอยู่กี่อัน
    hits = sum(1 for doc_id in retrieved_ids if doc_id == expected_id)

    # 3. คำนวณ Precision@3 และ Recall@3
    # Precision@3 = จำนวนที่ retrieve ถูก / 3
    p_at_3 = hits / 3.0
    precisions.append(p_at_3)

    # Recall@3 = จำนวนที่ retrieve ถูก / จำนวน ground-truth chunk ทั้งหมดของข้อนั้น (ในที่นี้ถือว่ามีข้อละ 1 chunk)
    r_at_3 = hits / 1.0
    recalls.append(r_at_3)

# คำนวณค่าเฉลี่ย
avg_p3 = np.mean(precisions)
avg_r3 = np.mean(recalls)

print(f"✅ ประเมินครบ {len(ground_truths)} คำถามแล้ว!")
print("-" * 30)
print(f"📊 Average Precision@3 : {avg_p3:.2f}")
print(f"📊 Average Recall@3    : {avg_r3:.2f}")
print("-" * 30)

# 4. Plot Histogram ของ Similarity Score ของ Top-1
plt.figure(figsize=(8, 5))
plt.hist(top1_scores, bins=5, color='skyblue', edgecolor='black')
plt.title("Histogram of Top-1 Similarity Scores")
plt.xlabel("Similarity Score (Distance)")
plt.ylabel("Frequency (จำนวนคำถาม)")
plt.grid(axis='y', alpha=0.75)

# บันทึกเป็นไฟล์ภาพ (แทนการใช้ .show() เผื่อรันใน Codespaces)
plt.savefig('similarity_histogram.png')
print("📸 บันทึกกราฟ Histogram ลงไฟล์ 'similarity_histogram.png' เรียบร้อยแล้ว")
