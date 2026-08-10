import streamlit as st
import sqlite3
import pandas as pd
import re
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="CAN Prod ERP Custom", layout="wide", initial_sidebar_state="collapsed")

# 2. Database Initialization & Auto-Repair Schema
def init_custom_db():
    conn = sqlite3.connect('can_prod_v2.db')
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        contact_person VARCHAR(255),
        phone VARCHAR(100),
        email VARCHAR(255),
        lead_time_days INTEGER DEFAULT 0
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        location_type VARCHAR(100) DEFAULT 'Internal Warehouse'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uniq_code VARCHAR(100),
        code VARCHAR(100) NOT NULL,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(50) DEFAULT 'RAW MATERIAL',
        sub_group VARCHAR(100) DEFAULT 'General',
        supplier_id INTEGER,
        unit_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        purchase_price REAL DEFAULT 0.0,
        selling_price REAL DEFAULT 0.0,
        specific_weight REAL DEFAULT 0.0,
        weight_unit VARCHAR(20) DEFAULT 'kg',
        current_stock REAL DEFAULT 0.0,
        min_stock REAL DEFAULT 0.0,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
        FOREIGN KEY (unit_id) REFERENCES units(id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
    );
    """)

    cursor.execute("PRAGMA table_info(stock_items)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    
    missing_cols = {
        'uniq_code': "VARCHAR(100)",
        'sub_group': "VARCHAR(100) DEFAULT 'General'",
        'selling_price': "REAL DEFAULT 0.0",
        'specific_weight': "REAL DEFAULT 0.0",
        'weight_unit': "VARCHAR(20) DEFAULT 'kg'"
    }
    
    for col_name, col_type in missing_cols.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE stock_items ADD COLUMN {col_name} {col_type}")

    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:
        for c, n in [('Ml', 'Linear Meters'), ('kg', 'Kilograms'), ('pcs', 'Pieces'), ('m2', 'Square Meters'), ('l', 'Liters')]:
            cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (c, n))

    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        for c, n, t in [('WH-MAIN', 'Main Central Warehouse', 'Internal Warehouse'), ('WH-CUST', 'Customer Virtual Location', 'Customer Virtual Storage')]:
            cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (c, n, t))

    cursor.execute("SELECT COUNT(*) FROM suppliers")
    if cursor.fetchone()[0] == 0:
        for c, n, cp, p, e, lt in [('SUP001', 'Baurom Construct SRL', 'John Smith', '+40722111222', 'orders@baurom.ro', 3), ('SUP002', 'LemnConfex SRL', 'Mary Doe', '+40733444555', 'sales@lemnconfex.ro', 5)]:
            cursor.execute("INSERT INTO suppliers (code, name, contact_person, phone, email, lead_time_days) VALUES (?, ?, ?, ?, ?, ?)", (c, n, cp, p, e, lt))

    conn.commit()
    populate_missing_uniq_codes(conn)
    conn.close()

def populate_missing_uniq_codes(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, category, sub_group FROM stock_items WHERE uniq_code IS NULL OR uniq_code = '' OR uniq_code = 'nan'")
    rows = cursor.fetchall()
    
    for item_id, code, category, sub_group in rows:
        cat_upper = str(category).upper() if category else 'RAW MATERIAL'
        sg = str(sub_group) if sub_group else ''
        
        if 'RAW' in cat_upper:
            if sg == 'Tabla': prefix = 'RM-TB-'
            elif sg == 'Teava': prefix = 'RM-TV-'
            elif sg == 'Europrofile': prefix = 'RM-EP-'
            else: prefix = 'RM-GEN-'
        elif 'BUY' in cat_upper:
            prefix = 'BP-'
        elif 'FINISHED' in cat_upper or 'SUB' in cat_upper or 'PRODUSE' in cat_upper:
            prefix = 'A0'
        else:
            prefix = 'ITM-'

        cursor.execute("SELECT uniq_code, code FROM stock_items WHERE (uniq_code LIKE ? OR code LIKE ?) AND id != ?", (f"{prefix}%", f"{prefix}%", item_id))
        existing_records = cursor.fetchall()
        
        max_num = 0
        for (uc, c_val) in existing_records:
            for check_val in [uc, c_val]:
                if check_val and check_val.startswith(prefix):
                    num_part = check_val.replace(prefix, '')
                    if num_part.isdigit():
                        max_num = max(max_num, int(num_part))
        
        if code and code.startswith('A0') and cat_upper in ['FINISHED GOOD', 'PRODUSE FINITE']:
            new_code = code
        else:
            next_num = max_num + 1 if max_num > 0 else (1834 if prefix == 'A0' else 1)
            new_code = f"A0{next_num:04d}" if prefix == 'A0' else f"{prefix}{next_num:04d}"

        cursor.execute("UPDATE stock_items SET uniq_code = ? WHERE id = ?", (new_code, item_id))
    
    conn.commit()

init_custom_db()

def get_db():
    return sqlite3.connect('can_prod_v2.db')

def generate_unique_item_code(conn, category, sub_group=""):
    cursor = conn.cursor()
    cat_upper = category.upper()
    
    if 'RAW' in cat_upper:
        if sub_group == 'Tabla':
            prefix = 'RM-TB-'
        elif sub_group == 'Teava':
            prefix = 'RM-TV-'
        elif sub_group == 'Europrofile':
            prefix = 'RM-EP-'
        else:
            prefix = 'RM-GEN-'
    elif 'BUY' in cat_upper:
        prefix = 'BP-'
    elif 'FINISHED' in cat_upper or 'SUB' in cat_upper or 'PRODUSE' in cat_upper:
        prefix = 'A0'
    else:
        prefix = 'ITM-'

    cursor.execute("SELECT uniq_code, code FROM stock_items WHERE uniq_code LIKE ? OR code LIKE ?", (f"{prefix}%", f"{prefix}%"))
    existing_records = cursor.fetchall()
    
    max_num = 0
    for (uc, c_val) in existing_records:
        for check_val in [uc, c_val]:
            if check_val and check_val.startswith(prefix):
                num_part = check_val.replace(prefix, '')
                if num_part.isdigit():
                    max_num = max(max_num, int(num_part))
            
    next_num = max_num + 1 if max_num > 0 else (1834 if prefix == 'A0' else 1)
    
    if prefix == 'A0':
        return f"A0{next_num:04d}"
    else:
        return f"{prefix}{next_num:04d}"

def clean_and_classify_item(part_no, desc, group_num):
    text_upper = f"{part_no} {desc}".upper()
    buy_keywords = [
        'PIULITA', 'SURUB', 'SAIBA', 'CONEXPAND', 'CAPAC', 'TREPTA', 'ZINCAT 1000X', 'PICIOR',
        'POLICARBONAT', 'MANA CURENTA', 'CUTIE', 'M8_', 'M10_', 'M12_', 'M8X', 'M10X', 'M12X',
        'ANCORA', 'FOLIE', 'T35 X 0.5MM', 'A00891', 'A00755', 'A00625'
    ]

    if group_num == 'PRODUSE FINITE' or ('A00' in part_no and group_num == 'PRODUSE FINITE') or ('A01' in part_no and group_num == 'PRODUSE FINITE'):
        return 'PRODUSE FINITE', 'FINISHED GOOD', f"{part_no} - {desc}"
    
    elif group_num == 'BUY PARTS' or any(k in text_upper for k in buy_keywords):
        category = 'BUY PART'
        sub_group = 'Buy Parts'
        
        if 'ZINCAT 1000X' in text_upper:
            dim = part_no.replace('Zincat ', '').strip()
            name = f"Treapta Gratar Zincat {dim} mm"
        elif 'PIULITA NIT' in text_upper:
            dim = part_no.replace('Piulita Nit ', '').strip()
            name = f"Piulita Nit {dim}"
        elif 'M8_CU_FLANSA' in text_upper:
            name = "Piulita Hexagonala M8 cu Flansa"
        elif 'M8X40' in text_upper:
            name = "Surub M8x40 Complet Filetat"
        elif 'M8X110' in text_upper:
            name = "Surub M8x110 Complet Filetat"
        elif 'M12X70' in text_upper:
            name = "Surub Metric M12x70"
        elif 'M10X40' in text_upper:
            name = "Surub Metric M10x40"
        elif 'PIULITA' in text_upper:
            dim = part_no if 'M' in part_no else desc
            name = f"Piulita {dim.replace('Piulita ', '')}"
        elif 'SAIBA' in text_upper:
            dim = part_no if 'M' in part_no else desc
            name = f"Saiba Plana {dim.replace('saiba', '').replace('Saiba', '').strip()}"
        elif 'PICIOR REGLABIL' in text_upper:
            name = f"Picior Reglabil {part_no.replace('Picior Reglabil ', '')}"
        elif 'CONEXPAND' in text_upper:
            name = f"Conexpand Ancora Metalica {part_no.replace('Conexpand ', '')}"
        elif 'CAPAC PLASTIC 30X10' in text_upper:
            name = "Capac Plastic Oblong 30x10 mm"
        elif '30X30' in text_upper and 'CAPAC' in text_upper:
            name = "Capac Plastic Patrat 30x30 mm cu Filet M8"
        elif '50X50' in text_upper and 'CAPAC' in text_upper or part_no == 'Capac':
            name = "Capac Plastic Patrat 50x50 mm cu Filet M8"
        elif 'CAPAC FI 60' in text_upper or 'A00891' in text_upper:
            name = "Capac Plastic Rotund FI 60 mm Simplu"
        elif 'T35' in text_upper:
            name = "Tabla Cutata T35 x 0.5 mm + Folie Anticondens DryStop"
        elif 'POLICARBONAT' in text_upper:
            name = "Placa Policarbonat 3 Pereti (6000x2100 mm)"
        elif 'MANA CURENTA' in text_upper or 'A01841' in text_upper:
            name = "Mana Curenta din Lemn de Stejar"
        elif 'CUTIE CARTON' in text_upper or 'A00755' in text_upper:
            name = "Cutie Carton Ambalare Produse"
        else:
            name = f"{part_no} - {desc}"
        return sub_group, category, name

    else:
        category = 'RAW MATERIAL'
        europrofile_keywords = ['UPN', 'UNP', 'UPE', 'IPE', 'HEA', 'HEB', 'CORNIER', 'BARA', 'ROTUND', 'PATRAT', 'LAT', 'PLATBANDA', 'C 150X50', 'FI14', 'FI12', 'FI10', 'FI 25', 'FI 20', 'FI 8']
        
        if any(k in text_upper for k in europrofile_keywords) and not ('TEAVA' in text_upper or 'TV' in text_upper or 'ALU_' in text_upper):
            sub_group = 'Europrofile'
            if 'UPN' in text_upper or 'UNP' in text_upper or 'UPE' in text_upper:
                name = f"Profil Otel {part_no}"
            elif 'IPE' in text_upper or desc == 'IPE':
                dim = part_no if 'IPE' in part_no else f"IPE {part_no}"
                name = f"Profil Europrofil {dim}"
            elif 'HEA' in text_upper or desc == 'HEA':
                dim = part_no if 'HEA' in part_no else f"HEA {part_no}"
                name = f"Profil Europrofil {dim}"
            elif 'CORNIER' in text_upper:
                dim = part_no.replace(' CORNIER', '').replace('Cornier ', '').replace('60X60X6 CORNIER', '60x60x6')
                name = f"Profil Cornier Otel {dim} mm"
            elif 'ROTUND FI' in text_upper or part_no.startswith('Fi') or part_no.startswith('FI') or part_no.startswith('Bara fi'):
                dim = part_no.replace('Rotund FI', '').replace('Bara fi ', '').replace('Fi', '').replace('FI ', '').replace('FI', '').strip()
                name = f"Bara Rotunda Plina FI {dim} mm"
            elif 'PATRAT' in text_upper:
                dim = part_no.replace(' Patrat', '')
                name = f"Bara Patrata Plina {dim} mm"
            elif 'LAT' in text_upper or 'PLATBANDA' in text_upper:
                dim = part_no.replace('LAT ', '').replace('A00703 PLATBANDA', '80x4')
                name = f"Platbanda Otel {dim} mm"
            elif 'C 150X50' in text_upper:
                name = "Profil C Zincat 150x50x30x2 mm"
            else:
                name = f"Profil Otel {part_no}"

        elif any(k in text_upper for k in ['TB', 'TABLA', 'STRIATA', 'DX51D', 'PL 100X10']):
            sub_group = 'Tabla'
            if 'STRIATA' in text_upper:
                name = "Tabla Striata 3 mm"
            elif 'ZINCATA' in text_upper or 'DX51D' in text_upper:
                thick = part_no.replace('Tb', '').replace(' mm Zincata', '').strip()
                name = f"Tabla Zincata {thick} mm (DX51D)"
            elif 'PL 100X10' in text_upper:
                name = "Platbanda / Tabla 100x10 mm"
            else:
                thick = part_no.replace('Tb', '').replace(' mm', '').replace('.', '').strip()
                name = f"Tabla Neagra LBR {thick} mm"

        elif any(k in text_upper for k in ['TV', 'TEAVA', 'TEVA', 'ALU_', 'FI 219', 'FI 220', 'FI27', 'FI 76', 'FI 48', 'FI 42', 'FI 33', 'FI 28', '88,9X2', '18X2_PRECIZI', 'A01349']) or re.search(r'^\d+x\d+x[\d\.,]+', part_no.lower()):
            sub_group = 'Teava'
            if 'ALU_' in text_upper:
                dim = part_no.replace('ALU_', '')
                name = f"Teava Aluminiu Rectangulara {dim} mm"
            elif 'OVALA' in text_upper:
                name = f"Teava Ovala {part_no.replace('Teava ovala ', '')} mm"
            elif 'PRECIZIE' in text_upper:
                name = "Teava Otel Precizie FI 18x2 mm"
            elif 'FI' in text_upper or 'FI' in desc.upper():
                dim = part_no.replace('TV FI', '').replace('Tv Fi', '').replace('TV Fi', '').replace('TV Fi ', '').replace('Teava ', '').replace('tv fi ', '').replace('TV ', '').replace('Fi ', '').strip()
                name = f"Teava Rotunda FI {dim} mm"
            else:
                dim = part_no.replace('Teava ', '').replace(' Teava', '').replace(' TV', '').strip()
                name = f"Teava Rectangulara / Patrata {dim} mm"
        else:
            sub_group = 'Raw Materials Diverse'
            name = f"{part_no} - {desc}"

    name = re.sub(r'\s+', ' ', name).strip()
    return sub_group, category, name

def import_mrpeasy_items(df):
    conn = get_db()
    cursor = conn.cursor()
    imported_count = 0
    updated_count = 0
    df.columns = [str(col).strip().lower() for col in df.columns]

    for _, row in df.iterrows():
        orig_code = str(row.get('part no.', row.get('part number', row.get('code', '')))).strip()
        raw_desc = str(row.get('part description', row.get('description', row.get('name', orig_code)))).strip()
        group_num = str(row.get('group number', row.get('group name', row.get('group', '')))).strip()
        
        sub_group, category, clean_name = clean_and_classify_item(orig_code, raw_desc, group_num)

        if orig_code.startswith('A0') and category == 'FINISHED GOOD':
            uniq_code = orig_code
        else:
            uniq_code = generate_unique_item_code(conn, category, sub_group)

        item_code = orig_code if orig_code and orig_code != 'nan' else uniq_code

        u_code = str(row.get('uom', row.get('unit of measure', row.get('unit', 'pcs')))).strip()
        if not u_code or u_code == 'nan': u_code = 'pcs'
        cursor.execute("SELECT id FROM units WHERE code = ?", (u_code,))
        u_row = cursor.fetchone()
        if u_row:
            unit_id = u_row[0]
        else:
            cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (u_code, u_code))
            unit_id = cursor.lastrowid

        w_name = str(row.get('default storage location', row.get('storage location', row.get('location', 'Main Warehouse')))).strip()
        if not w_name or w_name == 'nan': w_name = 'Main Warehouse'
        cursor.execute("SELECT id FROM warehouses WHERE name = ?", (w_name,))
        w_row = cursor.fetchone()
        if w_row:
            warehouse_id = w_row[0]
        else:
            w_code = f"WH-{w_name[:5].upper().replace(' ', '')}"
            cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (w_code, w_name, 'Internal Warehouse'))
            warehouse_id = cursor.lastrowid

        v_name = str(row.get('vendor name', '')).strip()
        supplier_id = None
        if v_name and v_name != 'nan':
            cursor.execute("SELECT id FROM suppliers WHERE name = ?", (v_name,))
            s_row = cursor.fetchone()
            if s_row:
                supplier_id = s_row[0]
            else:
                cursor.execute("INSERT INTO suppliers (code, name) VALUES (?, ?)", (f"SUP-{v_name[:5].upper()}", v_name))
                supplier_id = cursor.lastrowid

        try: price = float(row.get('cost', row.get('cost price', 0)))
        except: price = 0.0

        try: sell_price = float(row.get('selling price', row.get('price', 0)))
        except: sell_price = 0.0

        try: weight_val = float(row.get('weight', 0))
        except: weight_val = 0.0

        weight_unit = str(row.get('unit of weight', 'kg')).strip()
        if not weight_unit or weight_unit == 'nan': weight_unit = 'kg'

        try: stock = float(row.get('in stock', row.get('available', row.get('stoc', 0))))
        except: stock = 0.0

        try: min_st = float(row.get('reorder point', row.get('min stock', 0)))
        except: min_st = 0.0

        cursor.execute("SELECT id FROM stock_items WHERE code = ? OR uniq_code = ?", (item_code, uniq_code))
        ex = cursor.fetchone()
        if ex:
            cursor.execute("""
                UPDATE stock_items SET uniq_code=?, name=?, category=?, sub_group=?, supplier_id=?, unit_id=?, warehouse_id=?, purchase_price=?, selling_price=?, specific_weight=?, weight_unit=?, current_stock=?, min_stock=?
                WHERE id=?
            """, (uniq_code, clean_name, category, sub_group, supplier_id, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st, ex[0]))
            updated_count += 1
        else:
            cursor.execute("""
                INSERT INTO stock_items (uniq_code, code, name, category, sub_group, supplier_id, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uniq_code, item_code, clean_name, category, sub_group, supplier_id, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st))
            imported_count += 1

    conn.commit()
    conn.close()
    return imported_count, updated_count

def safe_float(val):
    if val in (None, "", "nan", "NaN"): 
        return 0.0
    try:
        return float(val)
    except:
        return 0.0

# CALLBACK FUNCTIONS FOR RESETTING FILTERS
def reset_raw_filters_callback():
    st.session_state["f_raw_code"] = ""
    st.session_state["f_raw_name"] = ""
    st.session_state["f_raw_sub"] = "All Sub-Groups"
    st.session_state["f_raw_supp"] = "All Suppliers"
    st.session_state["f_raw_uom"] = "All UoMs"

def reset_buy_filters_callback():
    st.session_state["f_buy_code"] = ""
    st.session_state["f_buy_name"] = ""
    st.session_state["f_buy_supp"] = "All Suppliers"

def reset_fg_filters_callback():
    st.session_state["f_fg_code"] = ""
    st.session_state["f_fg_name"] = ""
    st.session_state["f_fg_cat"] = "All Categories"

# 3. Query Parameters Navigation
query_params = st.query_params
active_page = query_params.get("page", "Home")
active_subtab = query_params.get("subtab", "Raw_Materials")

# 4. Aqua Minimalist Styling With 3D Big Buttons
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    [data-testid="stSidebar"] { display: none; }

    /* Header Bar */
    .top-header {
        background: linear-gradient(135deg, #0284c7 0%, #06b6d4 100%);
        color: #ffffff;
        padding: 12px 24px;
        border-radius: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.2);
    }
    .top-header h3 { margin: 0; font-size: 20px; font-weight: 800; color: #ffffff; }

    /* Navigation Bar */
    .mrp-nav-bar {
        display: flex;
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        padding: 10px 16px;
        gap: 15px;
        align-items: center;
        margin-bottom: 25px;
        border-radius: 12px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.03);
    }

    .mrp-nav-item {
        color: #0369a1;
        font-size: 14px;
        font-weight: 800;
        text-decoration: none;
        padding: 10px 22px;
        border-radius: 8px;
        background: linear-gradient(180deg, #ffffff 0%, #e0f2fe 100%);
        border: 1px solid #38bdf8;
        box-shadow: 0 4px 0 #0284c7, 0 5px 8px rgba(0, 0, 0, 0.12);
        transition: all 0.15s ease-in-out;
        display: inline-block;
    }

    .mrp-nav-item:hover {
        background: linear-gradient(180deg, #ffffff 0%, #bae6fd 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 0 #0284c7, 0 8px 12px rgba(14, 165, 233, 0.25);
        color: #0284c7;
    }

    .mrp-nav-item:active {
        transform: translateY(2px);
        box-shadow: 0 2px 0 #0284c7, 0 3px 4px rgba(0, 0, 0, 0.1);
    }

    .mrp-nav-active {
        background: linear-gradient(180deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        border: 1px solid #0284c7 !important;
        box-shadow: 0 4px 0 #075985, 0 6px 10px rgba(2, 132, 199, 0.3) !important;
    }

    /* Sub-tabs with 3D effect */
    .mrp-subtabs {
        display: flex;
        gap: 12px;
        padding-bottom: 12px;
        margin-bottom: 25px;
        border-bottom: 2px solid #e2e8f0;
    }

    .mrp-subtab {
        color: #475569;
        font-size: 13px;
        font-weight: 700;
        text-decoration: none;
        padding: 8px 18px;
        border-radius: 8px;
        background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
        border: 1px solid #cbd5e1;
        box-shadow: 0 3px 0 #94a3b8, 0 4px 6px rgba(0,0,0,0.06);
        transition: all 0.15s ease;
    }

    .mrp-subtab:hover {
        background: linear-gradient(180deg, #ffffff 0%, #e2e8f0 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 0 #94a3b8, 0 5px 8px rgba(0,0,0,0.1);
        color: #0f172a;
    }

    .mrp-subtab-active {
        background: linear-gradient(180deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: #ffffff !important;
        border: 1px solid #0284c7 !important;
        box-shadow: 0 3px 0 #0369a1, 0 4px 8px rgba(14, 165, 233, 0.25) !important;
    }

    /* KPI Metric Cards */
    .stock-kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin-bottom: 20px;
    }

    .stock-kpi-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 14px 18px;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #0284c7;
        box-shadow: 0 3px 6px rgba(0,0,0,0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .stock-kpi-card-warning {
        border-left-color: #ef4444 !important;
        background: #fef2f2 !important;
    }

    .stock-kpi-val {
        font-size: 22px;
        font-weight: 800;
        color: #0f172a;
        margin: 0;
    }

    .stock-kpi-lbl {
        font-size: 12px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
    }

    /* Table Filter Box Container */
    .filter-panel {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px 10px 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }

    /* Launchpad Cards */
    .launchpad-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin-top: 10px;
    }

    .launchpad-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 5px solid #0ea5e9;
        border-radius: 12px;
        padding: 26px 20px;
        text-align: center;
        text-decoration: none;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 0 #cbd5e1, 0 6px 10px rgba(0,0,0,0.05);
    }

    .launchpad-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 0 #0284c7, 0 12px 20px rgba(14, 165, 233, 0.2);
        border-top-color: #06b6d4;
    }

    .launchpad-icon { font-size: 36px; margin-bottom: 12px; }
    .launchpad-title { font-size: 16px; font-weight: 800; color: #0f172a; margin-bottom: 6px; }
    .launchpad-desc { font-size: 12px; color: #64748b; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

# 5. Top Navigation Header
now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(f"""
<div class="top-header">
    <div>
        <h3>CAN PROD &nbsp;|&nbsp; Custom ERP System</h3>
    </div>
    <div style="font-size: 12px; font-weight: 600; opacity: 0.95;">
        🌐 ROU &nbsp;|&nbsp; 👤 Admin &nbsp;|&nbsp; ⏱️ {now_str}
    </div>
</div>
""", unsafe_allow_html=True)

# 6. Main Navigation Bar
active_h = "mrp-nav-active" if active_page == "Home" else ""
active_s = "mrp-nav-active" if active_page == "Stock" else ""
active_b = "mrp-nav-active" if active_page == "BOM" else ""
active_r = "mrp-nav-active" if active_page == "RFQ" else ""

st.markdown(f"""
<div class="mrp-nav-bar">
    <a href="?page=Home" target="_self" class="mrp-nav-item {active_h}">🏠 Home</a>
    <a href="?page=Stock" target="_self" class="mrp-nav-item {active_s}">📦 Stock</a>
    <a href="?page=BOM" target="_self" class="mrp-nav-item {active_b}">📑 Production & BOM</a>
    <a href="?page=RFQ" target="_self" class="mrp-nav-item {active_r}">📊 Orders & RFQ</a>
</div>
""", unsafe_allow_html=True)

conn = get_db()

# DIALOG MODAL POP-UP FOR ADDING NEW ITEM DYNAMICALLY
@st.dialog("➕ Add New Item to Stock")
def add_new_item_dialog():
    st.subheader("Step 1: Select Item Type & Category")
    item_type = st.selectbox("Item Type *", ["Raw Material", "Buy Part", "Finished Good / Subassembly"])
    
    # 1. EXTRACT SUB-GROUP OUTSIDE THE FORM SO IT TRIGGERS A RERUN LIVE
    if item_type == "Raw Material":
        sub_group = st.selectbox("Main Sub-Group *", ["Tabla", "Teava", "Europrofile", "Raw Materials Diverse"])
        auto_uniq = generate_unique_item_code(conn, "RAW MATERIAL", sub_group)
        category = "RAW MATERIAL"
    elif item_type == "Buy Part":
        sub_group = "Buy Parts"
        auto_uniq = generate_unique_item_code(conn, "BUY PART")
        category = "BUY PART"
    else:
        sub_group = "Finished Goods"
        auto_uniq = generate_unique_item_code(conn, "FINISHED GOOD")
        category = st.selectbox("Category *", ["FINISHED GOOD", "SUBASSEMBLY"])

    # 2. OPEN THE FORM FOR THE REST OF THE FIELDS
    with st.form("add_item_dynamic_form"):
        st.subheader("Step 2: Item Characteristics & Specifications")
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("Uniq Code (Auto-Generated) *", value=auto_uniq, disabled=True)
            
            code = st.text_input("Part No. / Original Code *", value=auto_uniq)
            name = st.text_input("Part Description / Name *", placeholder="e.g. Teava Rotunda FI 48.3x4 mm")
            
            df_u_opts = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn)
            u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u_opts.iterrows()}
            selected_u = st.selectbox("Unit of Measure (UoM) *", list(u_dict.keys()))

            if item_type != "Finished Good / Subassembly":
                df_s_opts = pd.read_sql_query("SELECT id, name FROM suppliers ORDER BY name", conn)
                s_dict = {r['name']: r['id'] for _, r in df_s_opts.iterrows()}
                selected_s = st.selectbox("Preferred Supplier", list(s_dict.keys()) if s_dict else ["No Supplier"])
            else:
                s_dict = {}
                selected_s = None

        with col2:
            if item_type != "Finished Good / Subassembly":
                price = st.number_input("Purchase Price (€)", min_value=0.0, value=0.0, step=0.1)
            else:
                price = 0.0

            selling_p = st.number_input("Selling Price (€)", min_value=0.0, value=0.0, step=0.1)
            
            col_w1, col_w2 = st.columns([2, 1])
            with col_w1:
                spec_weight = st.number_input("Specific Weight / Unit", min_value=0.0, value=0.0, step=0.1)
            with col_w2:
                w_unit = st.selectbox("Weight Unit", ["kg", "lbs", "g"], index=0)

            df_w_opts = pd.read_sql_query("SELECT id, name FROM warehouses ORDER BY name", conn)
            w_dict = {r['name']: r['id'] for _, r in df_w_opts.iterrows()}
            selected_w = st.selectbox("Storage Warehouse Location", list(w_dict.keys()))

            stock_qty = st.number_input("Initial Stock Quantity", min_value=0.0, value=0.0)
            min_stock_qty = st.number_input("Reorder Point / Min Stock", min_value=0.0, value=0.0)

        st.divider()
        if st.form_submit_button("💾 Save Item to Stock", type="primary", use_container_width=True):
            if auto_uniq and name:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO stock_items 
                        (uniq_code, code, name, category, sub_group, supplier_id, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (auto_uniq.strip(), code.strip(), name.strip(), category, sub_group, s_dict.get(selected_s) if selected_s else None, u_dict.get(selected_u), w_dict.get(selected_w), price, selling_p, spec_weight, w_unit, stock_qty, min_stock_qty))
                    conn.commit()
                    st.success(f"Item {auto_uniq} saved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving item: {e}")
            else:
                st.warning("Please fill in Part No. and Name!")

# DIALOG MODAL POP-UP PENTRU EDITARE ȘI ȘTERGERE ITEM EXISTENT
@st.dialog("✏️ Edit Item Details")
def edit_item_dialog(item_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT uniq_code, code, name, category, sub_group, supplier_id, unit_id, warehouse_id, 
               purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock 
        FROM stock_items WHERE id = ?
    """, (item_id,))
    row = cursor.fetchone()
    
    if row:
        i_uniq = row[0] if row[0] else ""
        i_code = row[1] if row[1] else ""
        i_name = row[2] if row[2] else ""
        i_cat = row[3] if row[3] else "RAW MATERIAL"
        i_sub = row[4] if row[4] else "General"
        i_supp_id = row[5]
        i_unit_id = row[6]
        i_wh_id = row[7]
        i_pprice = safe_float(row[8])
        i_sprice = safe_float(row[9])
        i_sweight = safe_float(row[10])
        i_wunit = row[11] if row[11] else "kg"
        i_stock = safe_float(row[12])
        i_minstock = safe_float(row[13])

        st.caption(f"Editing Item ID: #{item_id} | Category: **{i_cat}**")

        with st.form("edit_item_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.text_input("Uniq Code (Read-Only) *", value=i_uniq, disabled=True)
                
                e_code = st.text_input("Part No. / Original Code *", value=i_code)
                e_name = st.text_input("Part Description / Name *", value=i_name)
                
                if i_cat == "RAW MATERIAL":
                    sub_opts = ["Tabla", "Teava", "Europrofile", "Raw Materials Diverse"]
                    e_sub = st.selectbox("Sub-Group *", sub_opts, index=sub_opts.index(i_sub) if i_sub in sub_opts else 0)
                else:
                    e_sub = i_sub

                df_u_opts = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn)
                u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u_opts.iterrows()}
                u_keys = list(u_dict.keys())
                u_index = [idx for idx, k in enumerate(u_keys) if u_dict[k] == i_unit_id]
                selected_u = st.selectbox("Unit of Measure (UoM) *", u_keys, index=u_index[0] if u_index else 0)

                df_s_opts = pd.read_sql_query("SELECT id, name FROM suppliers ORDER BY name", conn)
                s_dict = {r['name']: r['id'] for _, r in df_s_opts.iterrows()}
                s_keys = ["No Supplier"] + list(s_dict.keys())
                s_curr = [k for k, v in s_dict.items() if v == i_supp_id]
                selected_s = st.selectbox("Preferred Supplier", s_keys, index=s_keys.index(s_curr[0]) if s_curr else 0)

            with col2:
                e_pprice = st.number_input("Purchase Price (€)", min_value=0.0, value=i_pprice, step=0.1)
                e_sprice = st.number_input("Selling Price (€)", min_value=0.0, value=i_sprice, step=0.1)
                
                col_w1, col_w2 = st.columns([2, 1])
                with col_w1:
                    e_sweight = st.number_input("Specific Weight / Unit", min_value=0.0, value=i_sweight, step=0.1)
                with col_w2:
                    w_opts = ["kg", "lbs", "g"]
                    e_wunit = st.selectbox("Weight Unit", w_opts, index=w_opts.index(i_wunit) if i_wunit in w_opts else 0)

                df_w_opts = pd.read_sql_query("SELECT id, name FROM warehouses ORDER BY name", conn)
                w_dict = {r['name']: r['id'] for _, r in df_w_opts.iterrows()}
                w_keys = list(w_dict.keys())
                w_curr = [k for k, v in w_dict.items() if v == i_wh_id]
                selected_w = st.selectbox("Storage Warehouse Location", w_keys, index=w_keys.index(w_curr[0]) if w_curr else 0)

                e_stock = st.number_input("Current Stock Quantity", min_value=0.0, value=i_stock)
                e_minstock = st.number_input("Reorder Point / Min Stock", min_value=0.0, value=i_minstock)

            st.divider()
            c_save, c_del = st.columns([8, 2])
            with c_save:
                submit_save = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
            with c_del:
                submit_del = st.form_submit_button("🗑️ Delete", use_container_width=True)

            if submit_save:
                cursor.execute("""
                    UPDATE stock_items SET 
                    code=?, name=?, sub_group=?, supplier_id=?, unit_id=?, warehouse_id=?,
                    purchase_price=?, selling_price=?, specific_weight=?, weight_unit=?, current_stock=?, min_stock=?
                    WHERE id=?
                """, (e_code.strip(), e_name.strip(), e_sub, s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), e_pprice, e_sprice, e_sweight, e_wunit, e_stock, e_minstock, item_id))
                conn.commit()
                st.success("Item updated successfully!")
                st.rerun()

            if submit_del:
                cursor.execute("DELETE FROM stock_items WHERE id = ?", (item_id,))
                conn.commit()
                st.success("Item deleted!")
                st.rerun()

# ==========================================
# 1. HOME SCREEN (LAUNCHPAD)
# ==========================================
if active_page == "Home":
    st.markdown("#### Main Dashboard")
    st.caption("Select a module to proceed. Data loads on demand to keep the system fast.")
    st.write("")

    st.markdown("""
    <div class="launchpad-grid">
        <a href="?page=Stock" target="_self" class="launchpad-card">
            <div class="launchpad-icon">📦</div>
            <div class="launchpad-title">Stock</div>
            <div class="launchpad-desc">Manage Raw Materials, Buy Parts, Finished Goods, Suppliers, and Warehouses.</div>
        </a>
        <a href="?page=BOM" target="_self" class="launchpad-card">
            <div class="launchpad-icon">📑</div>
            <div class="launchpad-title">Production & BOM</div>
            <div class="launchpad-desc">Define Bills of Materials (BOM), Workstations, Routing, and Hourly Rates.</div>
        </a>
        <a href="?page=RFQ" target="_self" class="launchpad-card">
            <div class="launchpad-icon">📊</div>
            <div class="launchpad-title">Orders & RFQ</div>
            <div class="launchpad-desc">Generate Cost Calculations, Quotations, and Manage Customer Orders.</div>
        </a>
        <a href="?page=Home" target="_self" class="launchpad-card">
            <div class="launchpad-icon">⚙️</div>
            <div class="launchpad-title">Settings & Utilities</div>
            <div class="launchpad-desc">System configuration, User Permissions, Data Import & Export.</div>
        </a>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. STOCK MODULE
# ==========================================
elif active_page == "Stock":
    
    raw_count = conn.cursor().execute("SELECT COUNT(*) FROM stock_items WHERE category = 'RAW MATERIAL'").fetchone()[0]
    buy_count = conn.cursor().execute("SELECT COUNT(*) FROM stock_items WHERE category = 'BUY PART'").fetchone()[0]
    finished_count = conn.cursor().execute("SELECT COUNT(*) FROM stock_items WHERE category IN ('FINISHED GOOD', 'SUBASSEMBLY')").fetchone()[0]
    low_stock_count = conn.cursor().execute("SELECT COUNT(*) FROM stock_items WHERE current_stock <= min_stock AND min_stock > 0").fetchone()[0]

    st.markdown(f"""
    <div class="stock-kpi-grid">
        <div class="stock-kpi-card">
            <div>
                <div class="stock-kpi-lbl">Raw Materials</div>
                <div class="stock-kpi-val">{raw_count}</div>
            </div>
            <div style="font-size: 24px;">📄</div>
        </div>
        <div class="stock-kpi-card">
            <div>
                <div class="stock-kpi-lbl">Buy Parts</div>
                <div class="stock-kpi-val">{buy_count}</div>
            </div>
            <div style="font-size: 24px;">⚙️</div>
        </div>
        <div class="stock-kpi-card">
            <div>
                <div class="stock-kpi-lbl">Finished Goods</div>
                <div class="stock-kpi-val">{finished_count}</div>
            </div>
            <div style="font-size: 24px;">🏆</div>
        </div>
        <div class="stock-kpi-card {'stock-kpi-card-warning' if low_stock_count > 0 else ''}">
            <div>
                <div class="stock-kpi-lbl" style="{'color:#ef4444;' if low_stock_count > 0 else ''}">Reorder Alerts</div>
                <div class="stock-kpi-val" style="{'color:#ef4444;' if low_stock_count > 0 else ''}">{low_stock_count}</div>
            </div>
            <div style="font-size: 24px;">⚠️</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    subtabs = [
        ("Raw_Materials", "📄 Raw Materials"),
        ("Buy_Parts", "⚙️ Buy Parts"),
        ("Finished_Goods", "🏆 Finished Goods"),
        ("Suppliers", "🚚 Suppliers"),
        ("Warehouses", "🏭 Warehouses"),
        ("Units", "📏 Units of Measurement")
    ]

    subtabs_html = '<div class="mrp-subtabs">'
    for tab_key, tab_label in subtabs:
        act_class = "mrp-subtab-active" if active_subtab == tab_key else "mrp-subtab"
        subtabs_html += f'<a href="?page=Stock&subtab={tab_key}" target="_self" class="{act_class}">{tab_label}</a>'
    subtabs_html += '</div>'

    st.markdown(subtabs_html, unsafe_allow_html=True)

    # --- TAB 1: RAW MATERIALS ---
    if active_subtab == "Raw_Materials" or active_subtab == "Items":
        c_head, c_btn1, c_btn2 = st.columns([6, 2, 2])
        with c_head:
            st.markdown("##### Raw Materials Inventory (Tabla, Teava, Europrofile)")
        
        with c_btn1:
            if st.button("➕ Add Item (Pop-Up)", use_container_width=True, type="primary"):
                add_new_item_dialog()

        with c_btn2:
            with st.popover("↑ Import MRPeasy CSV", use_container_width=True):
                st.caption("Upload articles_20260810 (1).csv exported from MRPeasy.")
                csv_file = st.file_uploader("Upload CSV", type=['csv'], key="import_items_csv")
                if csv_file is not None:
                    try:
                        df_up = pd.read_csv(csv_file)
                        st.write("File Preview:")
                        st.dataframe(df_up.head(3))
                        if st.button("🚀 Execute Smart Import"):
                            ins, upd = import_mrpeasy_items(df_up)
                            st.success(f"Import Successful! Added: {ins}, Updated: {upd}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Import Error: {e}")

        st.write("")

        supplier_options = ["All Suppliers"] + [r[0] for r in conn.cursor().execute("SELECT DISTINCT s.name FROM stock_items si JOIN suppliers s ON si.supplier_id = s.id WHERE si.category = 'RAW MATERIAL' AND s.name IS NOT NULL ORDER BY s.name").fetchall()]
        uom_options = ["All UoMs"] + [r[0] for r in conn.cursor().execute("SELECT DISTINCT u.code FROM stock_items si JOIN units u ON si.unit_id = u.id WHERE si.category = 'RAW MATERIAL' AND u.code IS NOT NULL ORDER BY u.code").fetchall()]

        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns([2, 3, 2, 2, 1.5, 1.5])

        with col_f1:
            f_raw_code = st.text_input("Part No. / Uniq Code", key="f_raw_code", placeholder="Search Code...")
        with col_f2:
            f_raw_name = st.text_input("Part Description", key="f_raw_name", placeholder="Search Description...")
        with col_f3:
            f_raw_sub = st.selectbox("Sub-Group", ["All Sub-Groups", "Tabla", "Teava", "Europrofile", "Raw Materials Diverse"], key="f_raw_sub")
        with col_f4:
            f_raw_supp = st.selectbox("Preferred Supplier", supplier_options, key="f_raw_supp")
        with col_f5:
            f_raw_uom = st.selectbox("UoM", uom_options, key="f_raw_uom")
        with col_f6:
            st.write("")
            st.write("")
            st.button("🔄 Reset Filters", use_container_width=True, key="reset_raw_filters", on_click=reset_raw_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_raw = """
            SELECT 
                si.id as ID,
                si.uniq_code as 'Uniq Code',
                si.code as 'Original Part No.',
                si.name as 'Part Description',
                si.sub_group as 'Main Sub-Group',
                s.name as 'Preferred Supplier',
                u.code as 'UoM',
                si.specific_weight as 'Spec. Weight',
                si.purchase_price as 'Purchase Price (€)',
                si.selling_price as 'Selling Price (€)'
            FROM stock_items si
            LEFT JOIN suppliers s ON si.supplier_id = s.id
            LEFT JOIN units u ON si.unit_id = u.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE si.category = 'RAW MATERIAL'
        """
        params_raw = []
        if f_raw_code:
            q_raw += " AND (si.code LIKE ? OR si.uniq_code LIKE ?)"
            params_raw.extend([f"%{f_raw_code}%", f"%{f_raw_code}%"])
        if f_raw_name:
            q_raw += " AND si.name LIKE ?"
            params_raw.append(f"%{f_raw_name}%")
        if f_raw_sub != "All Sub-Groups":
            q_raw += " AND si.sub_group = ?"
            params_raw.append(f_raw_sub)
        if f_raw_supp != "All Suppliers":
            q_raw += " AND s.name = ?"
            params_raw.append(f_raw_supp)
        if f_raw_uom != "All UoMs":
            q_raw += " AND u.code = ?"
            params_raw.append(f_raw_uom)

        q_raw += " ORDER BY si.sub_group, si.uniq_code"
        df_raw = pd.read_sql_query(q_raw, conn, params=params_raw)
        
        st.caption("💡 Click on any row below to edit the item details.")
        selection = st.dataframe(
            df_raw, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="raw_items_table",
            column_config={
                "ID": None,
                "Purchase Price (€)": st.column_config.NumberColumn("Purchase Price (€)", format="%.2f €"),
                "Selling Price (€)": st.column_config.NumberColumn("Selling Price (€)", format="%.2f €"),
                "Spec. Weight": st.column_config.NumberColumn("Spec. Weight", format="%.2f")
            }
        )

        if selection and len(selection.selection.rows) > 0:
            selected_idx = selection.selection.rows[0]
            target_id = int(df_raw.iloc[selected_idx]['ID'])
            edit_item_dialog(target_id)

    # --- TAB 2: BUY PARTS ---
    elif active_subtab == "Buy_Parts":
        c_head, c_btn1 = st.columns([8, 2])
        with c_head:
            st.markdown("##### Purchased Parts & Fasteners (Buy Parts)")
        
        with c_btn1:
            if st.button("➕ Add Item (Pop-Up)", use_container_width=True, type="primary"):
                add_new_item_dialog()

        st.write("")

        buy_suppliers = ["All Suppliers"] + [r[0] for r in conn.cursor().execute("SELECT DISTINCT s.name FROM stock_items si JOIN suppliers s ON si.supplier_id = s.id WHERE si.category = 'BUY PART' AND s.name IS NOT NULL ORDER BY s.name").fetchall()]

        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_b1, col_b2, col_b3, col_b4 = st.columns([3, 4, 3, 2])

        with col_b1:
            f_buy_code = st.text_input("Part No. / Uniq Code", key="f_buy_code", placeholder="Search Code...")
        with col_b2:
            f_buy_name = st.text_input("Part Description", key="f_buy_name", placeholder="Search Description...")
        with col_b3:
            f_buy_supp = st.selectbox("Preferred Supplier", buy_suppliers, key="f_buy_supp")
        with col_b4:
            st.write("")
            st.write("")
            st.button("🔄 Reset Filters", use_container_width=True, key="reset_buy_filters", on_click=reset_buy_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_buy = """
            SELECT 
                si.id as ID,
                si.uniq_code as 'Uniq Code',
                si.code as 'Original Part No.',
                si.name as 'Part Description',
                s.name as 'Preferred Supplier',
                u.code as 'UoM',
                w.name as 'Warehouse',
                si.purchase_price as 'Purchase Price (€)',
                si.selling_price as 'Selling Price (€)'
            FROM stock_items si
            LEFT JOIN suppliers s ON si.supplier_id = s.id
            LEFT JOIN units u ON si.unit_id = u.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE si.category = 'BUY PART'
        """
        params_buy = []
        if f_buy_code:
            q_buy += " AND (si.code LIKE ? OR si.uniq_code LIKE ?)"
            params_buy.extend([f"%{f_buy_code}%", f"%{f_buy_code}%"])
        if f_buy_name:
            q_buy += " AND si.name LIKE ?"
            params_buy.append(f"%{f_buy_name}%")
        if f_buy_supp != "All Suppliers":
            q_buy += " AND s.name = ?"
            params_buy.append(f_buy_supp)

        df_buy = pd.read_sql_query(q_buy, conn, params=params_buy)
        
        st.caption("💡 Click on any row below to edit the item details.")
        selection = st.dataframe(
            df_buy, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="buy_items_table",
            column_config={
                "ID": None,
                "Purchase Price (€)": st.column_config.NumberColumn("Purchase Price (€)", format="%.2f €"),
                "Selling Price (€)": st.column_config.NumberColumn("Selling Price (€)", format="%.2f €")
            }
        )

        if selection and len(selection.selection.rows) > 0:
            selected_idx = selection.selection.rows[0]
            target_id = int(df_buy.iloc[selected_idx]['ID'])
            edit_item_dialog(target_id)

    # --- TAB 3: FINISHED GOODS ---
    elif active_subtab == "Finished_Goods":
        c_head, c_btn1 = st.columns([8, 2])
        with c_head:
            st.markdown("##### Finished Goods & Subassemblies")
        
        with c_btn1:
            if st.button("➕ Add Item (Pop-Up)", use_container_width=True, type="primary"):
                add_new_item_dialog()

        st.write("")

        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_fg1, col_fg2, col_fg3, col_fg4 = st.columns([3, 4, 3, 2])

        with col_fg1:
            f_fg_code = st.text_input("Product Code / Uniq Code", key="f_fg_code", placeholder="Search Code...")
        with col_fg2:
            f_fg_name = st.text_input("Product Description", key="f_fg_name", placeholder="Search Description...")
        with col_fg3:
            f_fg_cat = st.selectbox("Category", ["All Categories", "FINISHED GOOD", "SUBASSEMBLY"], key="f_fg_cat")
        with col_fg4:
            st.write("")
            st.write("")
            st.button("🔄 Reset Filters", use_container_width=True, key="reset_fg_filters", on_click=reset_fg_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_fin = """
            SELECT 
                si.id as ID,
                si.uniq_code as 'Uniq Code',
                si.code as 'Original Product Code',
                si.name as 'Product Description',
                si.category as 'Category',
                u.code as 'UoM',
                w.name as 'Warehouse',
                si.selling_price as 'Selling Price (€)'
            FROM stock_items si
            LEFT JOIN units u ON si.unit_id = u.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE si.category IN ('FINISHED GOOD', 'SUBASSEMBLY')
        """
        params_fin = []
        if f_fg_code:
            q_fin += " AND (si.code LIKE ? OR si.uniq_code LIKE ?)"
            params_fin.extend([f"%{f_fg_code}%", f"%{f_fg_code}%"])
        if f_fg_name:
            q_fin += " AND si.name LIKE ?"
            params_fin.append(f"%{f_fg_name}%")
        if f_fg_cat != "All Categories":
            q_fin += " AND si.category = ?"
            params_fin.append(f_fg_cat)

        df_fin = pd.read_sql_query(q_fin, conn, params=params_fin)
        
        st.caption("💡 Click on any row below to edit the item details.")
        selection = st.dataframe(
            df_fin, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="fg_items_table",
            column_config={
                "ID": None,
                "Selling Price (€)": st.column_config.NumberColumn("Selling Price (€)", format="%.2f €")
            }
        )

        if selection and len(selection.selection.rows) > 0:
            selected_idx = selection.selection.rows[0]
            target_id = int(df_fin.iloc[selected_idx]['ID'])
            edit_item_dialog(target_id)

    # --- TAB 4: SUPPLIERS ---
    elif active_subtab == "Suppliers":
        s_head, s_btn = st.columns([8, 2])
        with s_head:
            st.markdown("##### Supplier Management")
        with s_btn:
            with st.popover("➕ Add Supplier", use_container_width=True):
                with st.form("add_supplier_form"):
                    s_code = st.text_input("Supplier Code (e.g. SUP003)")
                    s_name = st.text_input("Supplier Name *")
                    s_contact = st.text_input("Contact Person")
                    s_phone = st.text_input("Phone Number")
                    s_email = st.text_input("E-mail Address")
                    s_lt = st.number_input("Lead Time (Days)", min_value=0, value=3)

                    if st.form_submit_button("Save Supplier"):
                        if s_code and s_name:
                            conn.cursor().execute("INSERT INTO suppliers (code, name, contact_person, phone, email, lead_time_days) VALUES (?, ?, ?, ?, ?, ?)", (s_code, s_name, s_contact, s_phone, s_email, s_lt))
                            conn.commit()
                            st.rerun()

        df_s = pd.read_sql_query("SELECT code as Code, name as 'Supplier Name', contact_person as 'Contact Person', phone as Phone, email as Email, lead_time_days as 'Lead Time (Days)' FROM suppliers ORDER BY name", conn)
        st.dataframe(df_s, use_container_width=True, hide_index=True)

    # --- TAB 5: WAREHOUSES ---
    elif active_subtab == "Warehouses":
        w_head, w_btn = st.columns([8, 2])
        with w_head:
            st.markdown("##### Warehouses & Storage Locations")
        with w_btn:
            with st.popover("➕ Add Warehouse", use_container_width=True):
                with st.form("add_wh_form"):
                    w_code = st.text_input("Location Code (e.g. WH-03)")
                    w_name = st.text_input("Warehouse / Customer Name")
                    w_type = st.selectbox("Location Type", ["Internal Warehouse", "Customer Storage", "Virtual Zone"])
                    if st.form_submit_button("Save Warehouse"):
                        conn.cursor().execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (w_code, w_name, w_type))
                        conn.commit()
                        st.rerun()

        df_w = pd.read_sql_query("SELECT code as Code, name as 'Warehouse / Location Name', location_type as 'Type' FROM warehouses ORDER BY name", conn)
        st.dataframe(df_w, use_container_width=True, hide_index=True)

    # --- TAB 6: UNITS ---
    elif active_subtab == "Units":
        u_head, u_btn = st.columns([8, 2])
        with u_head:
            st.markdown("##### Units of Measurement (UoM)")
        with u_btn:
            with st.popover("➕ Add Unit", use_container_width=True):
                with st.form("add_u_form"):
                    u_code = st.text_input("Unit Code (e.g. pcs)")
                    u_name = st.text_input("Description (e.g. Pieces)")
                    if st.form_submit_button("Save Unit"):
                        conn.cursor().execute("INSERT INTO units (code, name) VALUES (?, ?)", (u_code, u_name))
                        conn.commit()
                        st.rerun()

        df_u = pd.read_sql_query("SELECT code as Code, name as 'Description' FROM units ORDER BY code", conn)
        st.dataframe(df_u, use_container_width=True, hide_index=True)

# ==========================================
# 3. OTHER MODULES (PRODUCTION & RFQ)
# ==========================================
elif active_page == "BOM":
    st.markdown("#### Production & BOM Management")
    st.info("Production & BOM module is ready for configuration.")

elif active_page == "RFQ":
    st.markdown("#### Quotations & Customer Orders (RFQ)")
    st.info("Orders & RFQ module is ready for configuration.")

conn.close()
