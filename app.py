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
# Lấy key từ Secrets của Streamlit (Ưu tiên) hoặc file .env
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "").strip()

if api_key:
    genai.configure(api_key=api_key)
    # Sử dụng bản gemini-1.5-flash để tiết kiệm hạn mức và tốc độ nhanh
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

# Khởi tạo database (SQLite)
db.init_db()

st.set_page_config(page_title="Bank Analyzer - Gemini", layout="wide")
st.title("♊ Personal Bank Statement Analyzer (Gemini Edition)")

# 2. Các hàm xử lý kỹ thuật
def extract_pdf_text(uploaded_file):
    """Trích xuất văn bản từ file PDF"""
    try:
        reader = PdfReader(uploaded_file)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception as e:
        st.error(f"Lỗi đọc PDF: {e}")
        return ""

def clean_json_response(text):
    """Lọc bỏ các ký tự markdown (```json) để lấy đúng mảng dữ liệu"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Loại bỏ dòng đầu tiên (```json) và dòng cuối (```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    
    # Tìm vị trí mảng JSON [ ... ]
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    return cleaned

def analyze_transactions_with_ai(statement_text):
    """Gửi dữ liệu sang Gemini để bóc tách giao dịch"""
    if not model:
        raise ValueError("Chưa cấu hình GEMINI_API_KEY trong Secrets.")

    prompt = f"""
Bạn là một chuyên gia phân tích dữ liệu ngân hàng Việt Nam.
Hãy đọc nội dung sao kê dưới đây và trích xuất TOÀN BỘ giao dịch sang mảng JSON.

Yêu cầu định dạng JSON:
- date: YYYY-MM-DD
- amount: Số nguyên (Tiền ra ghi số ÂM, tiền vào ghi số DƯƠNG)
- description: Nội dung giao dịch chi tiết
- category: Một trong các nhãn (Ăn uống, Lương, Mua sắm, Chuyển khoản, Di chuyển, Hóa đơn, Giải trí, Khác)

Quy tắc:
- Không trả về lời giải thích, chỉ trả về duy nhất mảng JSON.
- Đảm bảo amount là số nguyên, không có dấu phân cách.

Nội dung sao kê:
{statement_text}
"""
    response = model.generate_content(prompt)
    if not response or not response.text:
        raise ValueError("AI không phản hồi hoặc không có dữ liệu.")
        
    json_text = clean_json_response(response.text)
    transactions = json.loads(json_text)
    
    # Chuyển thành DataFrame và chuẩn hóa
    df = pd.DataFrame(transactions)
    expected = ["date", "amount", "description", "category"]
    
    # Đảm bảo đủ cột
    for col in expected:
        if col not in df.columns:
            df[col] = "N/A" if col != "amount" else 0
            
    df = df[expected].copy()
    df["amount"] = pd.to_numeric(df["amount"], errors='coerce').fillna(0).astype(int)
    return df

# 3. Giao diện (Tabs)
tab_upload, tab_dashboard = st.tabs(["📤 Tải lên dữ liệu", "📊 Xem Dashboard"])

with tab_upload:
    st.subheader("Tải lên sao kê PDF")
    file = st.file_uploader("Chọn file PDF sao kê (ACB, VCB, Techcombank...)", type=["pdf"])
    
    if st.button("Phân tích bằng AI 🚀", type="primary"):
        if file:
            try:
                with st.spinner("Gemini đang đọc và phân tích dữ liệu..."):
                    raw_text = extract_pdf_text(file)
                    if not raw_text:
                        raise ValueError("Không tìm thấy văn bản trong file PDF.")
                        
                    df_result = analyze_transactions_with_ai(raw_text)
                    # Lưu vào Database
                    inserted = db.insert_transactions(df_result)
                    
                st.success(f"✅ Thành công! Đã xử lý {len(df_result)} giao dịch (Lưu mới: {inserted}).")
                st.dataframe(df_result, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Lỗi: {str(e)}")
        else:
            st.warning("Vui lòng tải file PDF lên trước.")

with tab_dashboard:
    st.subheader("Thống kê chi tiêu")
    try:
        all_data = db.get_all_transactions()
        if not all_data.empty:
            income = int(all_data[all_data["amount"] > 0]["amount"].sum())
            expense = int(all_data[all_data["amount"] < 0]["amount"].sum())
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng Thu", f"{income:,}đ")
            col2.metric("Tổng Chi", f"{abs(expense):,}đ", delta_color="inverse")
            col3.metric("Số dư", f"{income + expense:,}đ")
            
            st.dataframe(all_data.sort_values("date", ascending=False), use_container_width=True)
        else:
            st.info("Chưa có dữ và liệu trong database. Hãy tải lên ở Tab 1.")
    except Exception as e:
        st.error(f"Lỗi load dữ liệu: {e}")

