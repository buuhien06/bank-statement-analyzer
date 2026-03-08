import json
import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import database as db

# 1. Cấu hình ban đầu
load_dotenv()
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "").strip()

if api_key:
    genai.configure(api_key=api_key)
    # Sử dụng bản flash để tốc độ nhanh và ít lỗi quota
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

db.init_db()

st.set_page_config(page_title="Bank Analyzer - Gemini", layout="wide")
st.title("♊ Personal Bank Statement Analyzer (Gemini Edition)")

# 2. Các hàm xử lý
def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()

def clean_json_response(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1
4. Bấm **Save** và **Reboot app**.



---
**Tại sao lần này sẽ chạy?**
* Mình đã dùng model `gemini-1.5-flash` (không dùng bản 2.0 nữa để tránh lỗi quota).
* Mình đã thêm hàm `clean_json_response` để "gọt giũa" dữ liệu AI trả về, tránh lỗi parse JSON mà bạn hay gặp.

Bạn làm đủ 3 bước này chưa? Nếu rồi thì bấm **Reboot** và thử upload file xem Gemini có "ngoan" hơn lần trước không nhé!

**Bạn có muốn mình hướng dẫn cách kiểm tra xem API Key của bạn đang ở gói Free hay Pay-as-you-go để biết hạn mức sử dụng không?**
