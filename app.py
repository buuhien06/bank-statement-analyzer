import json
import os
import openai
import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import database as db

# 1. Cấu hình ban đầu
load_dotenv()
# Ưu tiên lấy key từ Streamlit Secrets (trên web) hoặc file .env (ở máy)
openai_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "").strip()

if openai_key:
    client = openai.OpenAI(api_key=openai_key)
else:
    client = None

db.init_db()

st.set_page_config(page_title="Bank Statement Analyzer", layout="wide")
st.title("💰 Personal Bank Statement Analyzer (OpenAI Edition)")

# 2. Các hàm xử lý kỹ thuật
def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()

def analyze_transactions_with_ai(statement_text):
    if not client:
        raise ValueError("Chưa cấu hình OPENAI_API_KEY. Hãy kiểm tra Secrets hoặc file .env.")

    prompt = f"""
Bạn là một trợ lý tài chính chuyên nghiệp. Hãy đọc nội dung sao kê ngân hàng sau đây và trích xuất danh sách giao dịch.
Yêu cầu trả về DUY NHẤT một mảng JSON (array of objects).

Mỗi giao dịch gồm:
- date: Định dạng YYYY-MM-DD
- amount: Số nguyên (Chi tiêu ghi số ÂM, Thu nhập ghi số DƯƠNG)
- description: Nội dung giao dịch
- category: Phân loại (Ăn uống, Lương, Mua sắm, Chuyển khoản, Di chuyển, Hóa đơn, Giải trí, Khác)

Nội dung sao kê:
{statement_text}
"""

    # Gọi OpenAI với chế độ JSON Mode để đảm bảo không bị lỗi định dạng
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Bạn là chuyên gia bóc tách dữ liệu sao kê sang định dạng JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" }
    )
    
    raw_content = response.choices[0].message.content
    data = json.loads(raw_content)
    
    # Xử lý trường hợp AI trả về object bọc ngoài (vd: {"transactions": [...]})
    if isinstance(data, dict):
        if "transactions" in data:
            transactions = data["transactions"]
        else:
            # Lấy giá trị đầu tiên nếu nó là danh sách
            first_val = next(iter(data.values()))
            transactions = first_val if isinstance(first_val, list) else [data]
    else:
        transactions = data

    df = pd.DataFrame(transactions)
    
    # Chuẩn hóa dữ liệu để khớp với Database
    expected_columns = ["date", "amount", "description", "category"]
    for col in expected_columns:
        if col not in df.columns:
            df[col] = 0 if col == "amount" else "N/A"
            
    df = df[expected_columns].copy()
    df["amount"] = pd.to_numeric(df["amount"], errors='coerce').fillna(0).astype(int)
    
    if df.empty:
        raise ValueError("AI không tìm thấy giao dịch nào hợp lệ.")
        
    return df

# 3. Giao diện ứng dụng (Tabs)
tab_upload, tab_dashboard = st.tabs(["📤 Tải dữ liệu lên", "📊 Xem Dashboard & Thống kê"])

with tab_upload:
    st.subheader("Tải lên sao kê PDF")
    uploaded_file = st.file_uploader("Chọn file sao kê PDF (ACB, VCB, Techcombank...)", type=["pdf"])

    if uploaded_file:
        st.info(f"📄 Đã nhận file: {uploaded_file.name}")

    if st.button("Phân tích bằng AI 🚀", type="primary"):
        if not uploaded_file:
            st.warning("Vui lòng tải lên một file PDF trước.")
        else:
            try:
                with st.spinner("Đang 'đọc' sao kê bằng AI..."):
                    text = extract_pdf_text(uploaded_file)
                    if not text:
                        raise ValueError("File PDF này không có nội dung văn bản để đọc.")
                    
                    df_result = analyze_transactions_with_ai(text)
                    inserted = db.insert_transactions(df_result)
                    
                st.success(f"✅ Xong! Đã xử lý {len(df_result)} giao dịch. Lưu mới {inserted} mục vào máy.")
                st.dataframe(df_result, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Lỗi: {str(e)}")

with tab_dashboard:
    st.subheader("Thống kê chi tiêu")
    try:
        data = db.get_all_transactions()
        if data.empty:
            st.info("Chưa có dữ liệu. Hãy quay lại Tab 1 để tải sao kê.")
        else:
            income = int(data[data["amount"] > 0]["amount"].sum())
            expense = int(data[data["amount"] < 0]["amount"].sum())
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng thu", f"{income:,}đ")
            c2.metric("Tổng chi", f"{abs(expense):,}đ", delta_color="inverse")
            c3.metric("Số dư", f"{income + expense:,}đ")
            
            st.dataframe(data.sort_values("date", ascending=False), use_container_width=True)
    except Exception as e:
        st.error(f"Không thể load dashboard: {e}")
