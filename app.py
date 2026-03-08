import json
import os

import google.generativeai as genai
import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader
from dotenv import load_dotenv

import database as db


load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

db.init_db()

st.set_page_config(page_title="Bank Statement Analyzer", layout="wide")
st.title("Personal Bank Statement Analyzer")


def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def clean_json_response(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    return cleaned


def analyze_transactions_with_ai(statement_text):
    if not model:
        raise ValueError("Thiếu GEMINI_API_KEY trong file .env.")

    prompt = f"""
Bạn là hệ thống bóc tách giao dịch ngân hàng.
Hãy đọc nội dung sao kê bên dưới và trả về DUY NHẤT một mảng JSON hợp lệ.

Yêu cầu:
- Mỗi phần tử là một object với các key: date, amount, description, category
- date phải ở định dạng YYYY-MM-DD
- amount là số nguyên
- category là một nhãn ngắn như: Ăn uống, Lương, Mua sắm, Chuyển khoản, Di chuyển, Hóa đơn, Giải trí, Khác
- Nếu một giao dịch là khoản chi thì amount âm
- Nếu một giao dịch là khoản thu thì amount dương
- Không thêm giải thích, không thêm markdown

Nội dung sao kê:
{statement_text}
"""
    response = model.generate_content(prompt)
    raw_text = getattr(response, "text", "") or ""
    if not raw_text.strip():
        raise ValueError("Gemini không trả về nội dung để phân tích.")

    json_text = clean_json_response(raw_text)
    transactions = json.loads(json_text)

    if not isinstance(transactions, list):
        raise ValueError("Dữ liệu AI trả về không phải là một mảng JSON.")

    df = pd.DataFrame(transactions)
    expected_columns = ["date", "amount", "description", "category"]
    missing_columns = [column for column in expected_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"JSON thiếu các cột bắt buộc: {', '.join(missing_columns)}"
        )

    df = df[expected_columns].copy()
    df["date"] = df["date"].astype(str).str.strip()
    df["description"] = df["description"].astype(str).str.strip()
    df["category"] = df["category"].fillna("Khác").astype(str).str.strip()
    df["amount"] = pd.to_numeric(df["amount"], errors="raise").astype(int)

    if df.empty:
        raise ValueError("Không tìm thấy giao dịch hợp lệ trong file PDF.")

    return df


tab_upload, tab_dashboard = st.tabs(["Tải dữ liệu lên", "Xem Dashboard & Thống kê"])

with tab_upload:
    st.subheader("Tải lên sao kê PDF")
    uploaded_file = st.file_uploader("Chọn file sao kê PDF", type=["pdf"])

    if uploaded_file is not None:
        st.info(f"Đã tải file: {uploaded_file.name}")

    if st.button("Phân tích bằng AI", type="primary"):
        if uploaded_file is None:
            st.warning("Vui lòng tải lên một file PDF trước khi phân tích.")
        else:
            try:
                with st.spinner("Đang đọc PDF và phân tích giao dịch bằng AI..."):
                    statement_text = extract_pdf_text(uploaded_file)
                    if not statement_text:
                        raise ValueError("Không thể trích xuất nội dung văn bản từ file PDF.")

                    transactions_df = analyze_transactions_with_ai(statement_text)
                    inserted_count = db.insert_transactions(transactions_df)

                st.success(
                    f"Phân tích thành công. Đã xử lý {len(transactions_df)} giao dịch, lưu mới {inserted_count} giao dịch vào database."
                )
                st.dataframe(transactions_df, use_container_width=True)
            except json.JSONDecodeError:
                st.error("Không thể parse JSON trả về từ Gemini. Hãy thử lại với file khác hoặc prompt khác.")
            except Exception as error:
                st.error(f"Đã xảy ra lỗi trong quá trình phân tích: {error}")

with tab_dashboard:
    st.subheader("Dashboard giao dịch")

    try:
        all_transactions = db.get_all_transactions()
        if all_transactions.empty:
            st.info("Chưa có dữ liệu giao dịch. Hãy tải sao kê ở tab đầu tiên.")
        else:
            total_income = int(all_transactions.loc[all_transactions["amount"] > 0, "amount"].sum())
            total_expense = int(all_transactions.loc[all_transactions["amount"] < 0, "amount"].sum())
            balance = total_income + total_expense

            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng thu", f"{total_income:,}")
            col2.metric("Tổng chi", f"{total_expense:,}")
            col3.metric("Số dư", f"{balance:,}")

            st.dataframe(all_transactions, use_container_width=True)
    except Exception as error:
        st.error(f"Không thể tải dữ liệu dashboard: {error}")
