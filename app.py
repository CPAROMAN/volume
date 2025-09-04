#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Starter: CSV ➜ 7-Day Projection", page_icon="📈", layout="wide")

st.title("📈 Python + Streamlit Starter (CSV ➜ 7-Day Projection)")
st.caption("Upload your sales CSV (DATE, PRODUCT, QTY_SOLD). We'll preview and generate a simple 7-day projection by weekday averages.")

with st.sidebar:
    st.header("Settings")
    preview_rows = st.number_input("Preview rows", min_value=10, max_value=5000, value=100, step=50)
    min_history_days = st.number_input("Min history (days) required", min_value=7, max_value=120, value=21, step=7)

@st.cache_data(show_spinner=False)
def load_csv(bytes_data: bytes) -> pd.DataFrame:
    f = io.BytesIO(bytes_data)
    try_order = [",", ";", "\t", "|"]
    for sep in try_order:
        f.seek(0)
        try:
            df = pd.read_csv(f, sep=sep, engine="python", on_bad_lines="skip", low_memory=True)
            if len(df.columns) >= 2:
                return df
        except:
            pass
    raise ValueError("Could not detect a valid CSV format.")

def normalize_columns(df: pd.DataFrame):
    cols = {c: c.strip().upper().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=cols)
    date_col = next((c for c in df.columns if c in ["DATE","ORDER_DATE","DAY"]), None)
    product_col = next((c for c in df.columns if c in ["PRODUCT","ITEM","SKU"]), None)
    qty_col = next((c for c in df.columns if c in ["QTY_SOLD","QUANTITY","UNITS"]), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    if qty_col:
        df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
    return df, date_col, product_col, qty_col

def weekday_projection(df, date_col, group_cols, qty_col, days_ahead=7):
    df = df.dropna(subset=[date_col]).copy()
    if df.empty: return pd.DataFrame()
    df["weekday"] = df[date_col].dt.weekday
    by_wd = df.groupby(group_cols+["weekday"])[qty_col].mean().reset_index().rename(columns={qty_col:"avg_qty"})
    last_date = pd.to_datetime(df[date_col].max())
    future = pd.date_range(last_date+pd.Timedelta(days=1), periods=days_ahead, freq="D")
    proj = pd.DataFrame({"DATE":future,"weekday":future.weekday})
    if group_cols:
        products = df[group_cols].drop_duplicates()
        proj = proj.merge(products, how="cross")
    proj = proj.merge(by_wd, on=group_cols+["weekday"], how="left")
    proj["PROJECTED_QTY"] = proj["avg_qty"].fillna(0).round(2)
    return proj.drop(columns=["avg_qty"])

uploaded = st.file_uploader("Upload CSV", type=["csv"])
if uploaded:
    df_raw = load_csv(uploaded.getvalue())
    df, DATE, PRODUCT, QTY = normalize_columns(df_raw)
    st.subheader("Preview")
    st.dataframe(df.head(preview_rows))
    if DATE and QTY:
        proj = weekday_projection(df, DATE, [PRODUCT] if PRODUCT else [], QTY)
        st.subheader("Next 7 Days Projection")
        st.dataframe(proj)
        st.download_button("⬇️ Download projection", proj.to_csv(index=False), "projection.csv","text/csv")
    else:
        st.warning("CSV must include DATE and QTY_SOLD.")
