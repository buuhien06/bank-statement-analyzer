import sqlite3
import pandas as pd
import os

DB_NAME = "bank_data.db"

def init_db():
    """Khởi tạo bảng nếu chưa tồn tại"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tạo bảng với ràng buộc UNIQUE để tránh lưu trùng một giao dịch nhiều lần
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            amount INTEGER,
            description TEXT,
            category TEXT,
            UNIQUE(date, amount, description)
        )
    ''')
    conn.commit()
    conn.close()

def insert_transactions(df):
    """Lưu dữ liệu vào bảng, tự động bỏ qua các dòng đã tồn tại"""
    if df.empty:
        return 0
        
    conn = sqlite3.connect(DB_NAME)
    # Lấy số lượng bản ghi trước khi chèn
    initial_count = pd.read_sql("SELECT COUNT(*) FROM transactions", conn).iloc[0,0]
    
    # Chèn dữ liệu từng dòng để xử lý lỗi trùng lặp một cách êm đẹp
    cursor = conn.cursor()
    for _, row in df.iterrows():
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO transactions (date, amount, description, category)
                VALUES (?, ?, ?, ?)
            ''', (row['date'], row['amount'], row['description'], row['category']))
        except Exception:
            continue
            
    conn.commit()
    
    # Tính toán số lượng bản ghi mới thực sự được thêm vào
    final_count = pd.read_sql("SELECT COUNT(*) FROM transactions", conn).iloc[0,0]
    conn.close()
    
    return int(final_count - initial_count)

def get_all_transactions():
    """Lấy toàn bộ dữ liệu ra DataFrame để hiển thị trên Dashboard"""
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql("SELECT * FROM transactions ORDER BY date DESC", conn)
    except Exception:
        df = pd.DataFrame(columns=["id", "date", "amount", "description", "category"])
    conn.close()
    return df
