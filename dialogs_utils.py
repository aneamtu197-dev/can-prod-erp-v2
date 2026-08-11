import streamlit as st
import requests
from datetime import datetime
from db import get_db

# --- ANAF API FUNCTION ---
def fetch_anaf_data(cui):
    try:
        clean_cui = ''.join(filter(str.isdigit, str(cui)))
        if not clean_cui: return None, "CUI invalid (conține doar cifre)."
        today = datetime.now().strftime("%Y-%m-%d")
        payload = [{"cui": int(clean_cui), "data": today}]
        headers = {"Content-Type": "application/json"}
        for version in ["v9", "v8", "v7"]:
            url = f"https://webservicesp.anaf.ro/PlatitorTvaRest/api/{version}/ws/tva"
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('cod') == 200 and data.get('found') and len(data.get('found')) > 0:
                    company = data['found'][0]
                    return {'name': company.get('denumire', ''), 'address': company.get('adresa', ''), 'reg_com': company.get('nrRegCom', '')}, None
                else: return None, "CUI-ul nu a fost găsit în baza de date ANAF."
            elif response.status_code in [403, 404]: continue
        return None, "🚨 ANAF blochează cererile. Te rugăm să introduci datele manual."
    except Exception as e: return None, "🚨 Eroare conexiune ANAF. Introdu manual."

def reset_raw_filters_callback():
    for k in ["f_raw_code", "f_raw_name", "f_raw_sub", "f_raw_supp", "f_raw_uom"]: st.session_state[k] = "All Sub-Groups" if "sub" in k else ("All Suppliers" if "supp" in k else ("All UoMs" if "uom" in k else ""))

def reset_buy_filters_callback():
    for k in ["f_buy_code", "f_buy_name", "f_buy_supp"]: st.session_state[k] = "All Suppliers" if "supp" in k else ""

def reset_fg_filters_callback():
    for k in ["f_fg_code", "f_fg_name", "f_fg_cat"]: st.session_state[k] = "All Categories" if "cat" in k else ""

def reset_bom_filters_callback():
    for k in ["f_bom_code", "f_bom_name", "f_bom_cust"]: st.session_state[k] = "All Customers" if "cust" in k else ""

def get_selected_ids(df, selected_rows):
    valid_ids = []
    if selected_rows:
        col_name = 'ID' if 'ID' in df.columns else ('id' if 'id' in df.columns else df.columns[0])
        for idx in selected_rows:
            if 0 <= idx < len(df): valid_ids.append(int(df.iloc[idx][col_name]))
    return valid_ids

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_stock_dialog(item_ids):
    st.error(f"Ești sigur că vrei să ștergi {len(item_ids)} articol(e)?")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn = get_db(); cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(item_ids))
        cursor.execute(f"DELETE FROM stock_items WHERE id IN ({placeholders})", item_ids)
        conn.commit(); st.success("Șters!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_suppliers_dialog(item_ids):
    st.error(f"Ești sigur că vrei să ștergi {len(item_ids)} furnizor(i)?")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn = get_db(); cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(item_ids))
        cursor.execute(f"DELETE FROM suppliers WHERE id IN ({placeholders})", item_ids)
        conn.commit(); st.success("Șters!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_customers_dialog(item_ids):
    st.error(f"Ești sigur că vrei să ștergi {len(item_ids)} client(i)?")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn = get_db(); cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(item_ids))
        cursor.execute(f"DELETE FROM customers WHERE id IN ({placeholders})", item_ids)
        conn.commit(); st.success("Șters!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_facilities_dialog(item_ids):
    st.error(f"Ești sigur că vrei să ștergi {len(item_ids)} echipament(e)?")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn = get_db(); cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(item_ids))
        cursor.execute(f"DELETE FROM production_facilities WHERE id IN ({placeholders})", item_ids)
        conn.commit(); st.success("Șters!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_operations_dialog(item_ids):
    st.error(f"Ești sigur că vrei să ștergi {len(item_ids)} operațiune(i)?")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn = get_db(); cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(item_ids))
        cursor.execute(f"DELETE FROM operations WHERE id IN ({placeholders})", item_ids)
        conn.commit(); st.success("Șters!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_boms_dialog(item_ids):
    st.error(f"Ești sigur că vrei să ștergi {len(item_ids)} rețetă(e)?")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn = get_db(); cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(item_ids))
        cursor.execute(f"DELETE FROM product_boms WHERE id IN ({placeholders})", item_ids)
        conn.commit(); st.success("Șters!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete Warehouses")
def bulk_delete_warehouses_dialog(item_ids):
    st.error(f"Ești sigur că vrei să ștergi {len(item_ids)} depozit(e)?")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn = get_db(); cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(item_ids))
        cursor.execute(f"SELECT count(id) FROM stock_items WHERE warehouse_id IN ({placeholders})", item_ids)
        if cursor.fetchone()[0] > 0:
            st.error("🚨 Eroare: Există materiale în aceste depozite!")
        else:
            cursor.execute(f"DELETE FROM warehouses WHERE id IN ({placeholders})", item_ids)
            conn.commit(); st.success("Șters!"); st.rerun()
