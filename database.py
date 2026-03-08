import sqlite3
from pathlib import Path

import pandas as pd


DB_PATH = Path(__file__).resolve().parent / "bank_data.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT NOT NULL,
                category TEXT,
                UNIQUE(date, amount, description)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def insert_transactions(df):
    if df is None or df.empty:
        return 0

    required_columns = ["date", "amount", "description", "category"]
    data = df.copy()
    data = data.reindex(columns=required_columns)
    data["date"] = data["date"].astype(str).str.strip()
    data["description"] = data["description"].astype(str).str.strip()
    data["category"] = data["category"].fillna("Chưa phân loại").astype(str).str.strip()
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce").fillna(0).astype(int)
    data = data.dropna(subset=["date", "description"])
    data = data[
        (data["date"] != "")
        & (data["description"] != "")
    ].drop_duplicates(subset=["date", "amount", "description"])

    if data.empty:
        return 0

    conn = sqlite3.connect(DB_PATH)
    try:
        existing = pd.read_sql_query(
            "SELECT date, amount, description FROM transactions",
            conn,
        )
        if not existing.empty:
            existing_keys = set(
                zip(existing["date"], existing["amount"], existing["description"])
            )
            data = data[
                ~data.apply(
                    lambda row: (row["date"], row["amount"], row["description"]) in existing_keys,
                    axis=1,
                )
            ]

        if data.empty:
            return 0

        data.to_sql("transactions", conn, if_exists="append", index=False)
        return len(data)
    finally:
        conn.close()


def get_all_transactions():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            """
            SELECT id, date, amount, description, category
            FROM transactions
            ORDER BY date DESC, id DESC
            """,
            conn,
        )
        if not df.empty:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
        return df
    finally:
        conn.close()
