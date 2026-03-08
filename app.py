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
