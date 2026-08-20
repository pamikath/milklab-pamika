import streamlit as st
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from google import genai  # <--- เปลี่ยนมาใช้ SDK ตัวใหม่
import time
import json
import uuid

# ==========================================
# 0. การตั้งค่าเบื้องต้น & ฟังก์ชัน Observability (Trace)
# ==========================================
# ตั้งค่า API Key ของ Gemini ผ่าน Client ตัวใหม่
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))


def span(name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            # เก็บข้อมูลลงไฟล์ traces.jsonl
            trace_data = {
                "trace_id": st.session_state.get("trace_id", str(uuid.uuid4())),
                "span_name": name,
                "duration_sec": round(duration, 4),
                "timestamp": time.time()
            }
            with open("traces.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(trace_data) + "\n")

            return result
        return wrapper
    return decorator


# ==========================================
# TODO 1, 2, 3: โหลดไฟล์, Embed และสร้าง FAISS Index
# ==========================================
@st.cache_resource
def load_kb_and_index():
    with open("fashion_kb.md", "r", encoding="utf-8") as f:
        text = f.read()
    chunks = [c.strip() for c in text.split("\n\n")
              if c.strip() and len(c) > 10]

    embed_model = SentenceTransformer(
        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = embed_model.encode(chunks)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype('float32'))

    return chunks, embed_model, index


kb_chunks, st_embed_model, faiss_index = load_kb_and_index()


# ==========================================
# TODO 5: ฟังก์ชัน Retrieve ค้นหาข้อมูล
# ==========================================
@span(name="retrieve_top_k")
def retrieve_top_k(query, k=3):
    query_vector = st_embed_model.encode([query]).astype('float32')
    distances, indices = faiss_index.search(query_vector, k)

    retrieved = [kb_chunks[i] for i in indices[0]]
    return retrieved


# ==========================================
# TODO 6: ห่อ generate_answer ด้วย span
# ==========================================
@span(name="generate_answer")
def generate_answer(query, context_chunks):
    context_text = "\n\n".join(context_chunks)

    prompt = f"""
    คุณคือผู้ช่วยของร้านเช่าชุด กรุณาตอบคำถามลูกค้าโดยอิงจากข้อมูลต่อไปนี้เท่านั้น:
    
    ข้อมูลร้าน:
    {context_text}
    
    คำถามลูกค้า: {query}
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash', 
        contents=prompt
    )
    return response.text


# ==========================================
# TODO 4: สร้าง Chat UI
# ==========================================
st.title("👗 แชตบอทร้านเช่าชุด (RAG)")
st.caption("แชตบอทตอบคำถามลูกค้าด้วยระบบ RAG (Retrieval-Augmented Generation)")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "สวัสดีค่ะ! 👗 ร้านเช่าชุดยินดีให้บริการ มีคำถามเกี่ยวกับประเภทชุด ราคา หรือเงื่อนไขการเช่า ถามมาได้เลยนะคะ"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# เปลี่ยน placeholder ตรงช่องพิมพ์แชตให้เป็นตัวอย่างของร้านเช่าชุด
if user_query := st.chat_input("พิมพ์คำถามของคุณที่นี่... เช่น ชุดราตรียาวราคาเช่าเท่าไหร่?"):

    st.session_state.trace_id = str(uuid.uuid4())

    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("กำลังค้นหาข้อมูล..."):
            retrieved_chunks = retrieve_top_k(user_query, k=3)
            answer = generate_answer(user_query, retrieved_chunks)

            st.markdown(answer)

            with st.expander("🔍 Trace (Source Context)"):
                st.write("**Top-k Chunks ที่ระบบดึงมาได้:**")
                for i, chunk in enumerate(retrieved_chunks):
                    st.info(f"**Chunk {i+1}:** {chunk}")

    st.session_state.messages.append({"role": "assistant", "content": answer})
