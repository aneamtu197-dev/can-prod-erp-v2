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
    
    # Suppliers Table
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

    # Units Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL
    );
    """)

    # Warehouses Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        location_type VARCHAR(100) DEFAULT 'Internal Warehouse'
    );
    """)

    # Stock Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(100) UNIQUE NOT NULL,
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

    # AUTO-REPAIR: Add missing columns if database table existed prior to schema updates
    cursor.execute("PRAGMA table_info(stock_items)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    
    missing_cols = {
        'sub_group': "VARCHAR(100) DEFAULT 'General'",
        'selling_price': "REAL DEFAULT 0.0",
        'specific_weight': "REAL DEFAULT 0.0",
        'weight_unit': "VARCHAR(20) DEFAULT 'kg'"
    }
    
    for col_name, col_type in missing_cols.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE stock_items ADD COLUMN {col_name} {col_type}")

    # Populate Default Units
    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:
        for c, n in [('Ml', 'Metri Liniari'), ('kg', 'Kilograme'), ('pcs', 'Pieces'), ('m2', 'Square Meters'), ('l', 'Liters')]:
            cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (c, n))

    # Populate Default Warehouses
    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        for c, n, t in [('WH-MAIN', 'Main Central Warehouse', 'Internal Warehouse'), ('WH-CUST', 'Customer Virtual Location', 'Customer Virtual Storage')]:
            cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (c, n, t))

    # Populate Default Suppliers
    cursor.execute("SELECT COUNT(*) FROM suppliers")
    if cursor.fetchone()[0] == 0:
        for c, n, cp, p, e, lt in [('SUP001', 'Baurom Construct SRL', 'John Smith', '+40722111222', 'orders@baurom.ro', 3), ('SUP002', 'LemnConfex SRL', 'Mary Doe', '+40733444555', 'sales@lemnconfex.ro', 5)]:
            cursor.execute("INSERT INTO suppliers (code, name, contact_person, phone, email, lead_time_days) VALUES (?, ?, ?, ?, ?, ?)", (c, n, cp, p, e, lt))

    conn.commit()
    conn.close()

init_custom_db()

def get_db():
    return sqlite3.connect('can_prod_v2.db')

# Intelligent Item Classifier & Name Cleaner for MRPeasy Import
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

# Function to Import MRPeasy CSV Into Custom Stock Database
def import_mrpeasy_items(df):
    conn = get_db()
    cursor = conn.cursor()
    imported_count = 0
    updated_count = 0
    df.columns = [str(col).strip().lower() for col in df.columns]

    for _, row in df.iterrows():
        code = str(row.get('part no.', row.get('part number', row.get('code', '')))).strip()
        if not code or code == 'nan':
            continue

        raw_desc = str(row.get('part description', row.get('description', row.get('name', code)))).strip()
        group_num = str(row.get('group number', row.get('group name', row.get('group', '')))).strip()
        
        # Clean Description & Sub-Group Classification
        sub_group, category, clean_name = clean_and_classify_item(code, raw_desc, group_num)

        # Unit of Measure
        u_code = str(row.get('uom', row.get('unit of measure', row.get('unit', 'pcs')))).strip()
        if not u_code or u_code == 'nan': u_code = 'pcs'
        
        cursor.execute("SELECT id FROM units WHERE code = ?", (u_code,))
        u_row = cursor.fetchone()
        if u_row:
            unit_id = u_row[0]
        else:
            cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (u_code, u_code))
            unit_id = cursor.lastrowid

        # Warehouse / Storage Location
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

        # Supplier / Vendor Mapping
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

        # Numeric Fields
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

        cursor.execute("SELECT id FROM stock_items WHERE code = ?", (code,))
        ex = cursor.fetchone()
        if ex:
            cursor.execute("""
                UPDATE stock_items SET name=?, category=?, sub_group=?, supplier_id=?, unit_id=?, warehouse_id=?, purchase_price=?, selling_price=?, specific_weight=?, weight_unit=?, current_stock=?, min_stock=?
                WHERE code=?
            """, (clean_name, category, sub_group, supplier_id, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st, code))
            updated_count += 1
        else:
            cursor.execute("""
                INSERT INTO stock_items (code, name, category, sub_group, supplier_id, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, clean_name, category, sub_group, supplier_id, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st))
            imported_count += 1

    conn.commit()
    conn.close()
    return imported_count, updated_count

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

# Dialog Modal Pop-Up pentru Adăugare Manuală Materie Primă
@st.dialog("➕ Add New Raw Material / Item")
def add_raw_material_dialog():
    with st.form("add_raw_material_form"):
        st.subheader("Item Characteristics & Specifications")
        col1, col2 = st.columns(2)
        
        with col1:
            code = st.text_input("Part No. / Item Code *", placeholder="e.g. TV FI 48.3x4")
            name = st.text_input("Part Description / Name *", placeholder="e.g. Teava Rotunda FI 48.3x4 mm")
            sub_group = st.selectbox("Main Sub-Group *", ["Tabla", "Teava", "Europrofile", "Raw Materials Diverse"])
            
            df_u_opts = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn)
            u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u_opts.iterrows()}
            selected_u = st.selectbox("Unit of Measure (UoM) *", list(u_dict.keys()))

            df_s_opts = pd.read_sql_query("SELECT id, name FROM suppliers ORDER BY name", conn)
            s_dict = {r['name']: r['id'] for _, r in df_s_opts.iterrows()}
            selected_s = st.selectbox("Preferred Supplier", list(s_dict.keys()) if s_dict else ["No Supplier"])

        with col2:
            price = st.number_input("Purchase Price (€)", min_value=0.0, value=0.0, step=0.1)
            selling_p = st.number_input("Selling Price (€)", min_value=0.0, value=0.0, step=0.1)
            
            col_w1, col_w2 = st.columns([2, 1])
            with col_w1:
                spec_weight = st.number_input("Specific Weight / Unit", min_value=0.0, value=0.0, step=0.1)
            with col_w2:
                w_unit = st.selectbox("Weight Unit", ["kg", "lbs", "g"], index=0)

            df_w_opts = pd.read_sql_query("SELECT id, name FROM warehouses ORDER BY name", conn)
            w_dict = {r['name']: r['id'] for _, r in df_w_opts.iterrows()}
            selected_w = st.selectbox("Initial Warehouse Location", list(w_dict.keys()))

            stock_qty = st.number_input("Initial Stock Quantity", min_value=0.0, value=0.0)
            min_stock_qty = st.number_input("Reorder Point / Min Stock", min_value=0.0, value=0.0)

        st.divider()
        if st.form_submit_button("💾 Save Raw Material", type="primary", use_container_width=True):
            if code and name:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO stock_items 
                        (code, name, category, sub_group, supplier_id, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock)
                        VALUES (?, ?, 'RAW MATERIAL', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (code.strip(), name.strip(), sub_group, s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), price, selling_p, spec_weight, w_unit, stock_qty, min_stock_qty))
                    conn.commit()
                    st.success(f"Material {code} saved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please fill in Part No. and Name!")

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
# 2. STOCK MODULE (SYNTHESIZED & STYLED)
# ==========================================
elif active_page == "Stock":
    
    # Calculate Synthetic KPIs
    raw_count = conn.cursor().execute("SELECT COUNT(*) FROM stock_items WHERE category = 'RAW MATERIAL'").fetchone()[0]
    buy_count = conn.cursor().execute("SELECT COUNT(*) FROM stock_items WHERE category = 'BUY PART'").fetchone()[0]
    finished_count = conn.cursor().execute("SELECT COUNT(*) FROM stock_items WHERE category IN ('FINISHED GOOD', 'SUBASSEMBLY')").fetchone()[0]
    low_stock_count = conn.cursor().execute("SELECT COUNT(*) FROM stock_items WHERE current_stock <= min_stock AND min_stock > 0").fetchone()[0]

    # Synthetic Metric Bar
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

    # Sub-tabs Configuration
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
            if st.button("➕ Add Raw Material (Pop-Up)", use_container_width=True, type="primary"):
                add_raw_material_dialog()

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
        
        # Sub-Group Filter & Search
        f1, f2 = st.columns([6, 4])
        with f1:
            search_raw = st.text_input("🔍 Search Raw Materials by Part No. or Description", placeholder="Type to search...", label_visibility="collapsed")
        with f2:
            filter_sub = st.selectbox("Filter Sub-Group", ["All Sub-Groups", "Tabla", "Teava", "Europrofile", "Raw Materials Diverse"], label_visibility="collapsed")

        q_raw = """
            SELECT 
                si.id as ID,
                si.code as 'Part No.',
                si.name as 'Part Description',
                si.sub_group as 'Main Sub-Group',
                s.name as 'Preferred Supplier',
                u.code as 'UoM',
                si.specific_weight as 'Spec. Weight (kg/UoM)',
                si.purchase_price as 'Purchase Price (€)',
                si.selling_price as 'Selling Price (€)',
                si.current_stock as 'In Stock',
                si.min_stock as 'Reorder Point'
            FROM stock_items si
            LEFT JOIN suppliers s ON si.supplier_id = s.id
            LEFT JOIN units u ON si.unit_id = u.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE si.category = 'RAW MATERIAL'
        """
        params_raw = []
        if search_raw:
            q_raw += " AND (si.code LIKE ? OR si.name LIKE ?)"
            params_raw.extend([f"%{search_raw}%", f"%{search_raw}%"])
        if filter_sub != "All Sub-Groups":
            q_raw += " AND si.sub_group = ?"
            params_raw.append(filter_sub)

        q_raw += " ORDER BY si.sub_group, si.code"

        df_raw = pd.read_sql_query(q_raw, conn, params=params_raw)
        st.dataframe(
            df_raw, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Purchase Price (€)": st.column_config.NumberColumn("Purchase Price (€)", format="%.2f €"),
                "Selling Price (€)": st.column_config.NumberColumn("Selling Price (€)", format="%.2f €"),
                "Spec. Weight (kg/UoM)": st.column_config.NumberColumn("Spec. Weight", format="%.2f kg"),
                "In Stock": st.column_config.NumberColumn("In Stock", format="%.2f"),
                "Reorder Point": st.column_config.NumberColumn("Reorder Point", format="%.2f")
            }
        )

    # --- TAB 2: BUY PARTS ---
    elif active_subtab == "Buy_Parts":
        c_head, c_btn1 = st.columns([8, 2])
        with c_head:
            st.markdown("##### Purchased Parts & Fasteners (Buy Parts)")
        
        with c_btn1:
            with st.popover("➕ Add Buy Part", use_container_width=True):
                with st.form("add_buy_form"):
                    code = st.text_input("Part No. / Item Code *")
                    name = st.text_input("Part Description *")
                    
                    df_s_opts = pd.read_sql_query("SELECT id, name FROM suppliers ORDER BY name", conn)
                    s_dict = {r['name']: r['id'] for _, r in df_s_opts.iterrows()}
                    selected_s = st.selectbox("Preferred Supplier", list(s_dict.keys()) if s_dict else ["No Supplier"])
                    
                    df_u_opts = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn)
                    u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u_opts.iterrows()}
                    selected_u = st.selectbox("Unit of Measure", list(u_dict.keys()))

                    df_w_opts = pd.read_sql_query("SELECT id, name FROM warehouses ORDER BY name", conn)
                    w_dict = {r['name']: r['id'] for _, r in df_w_opts.iterrows()}
                    selected_w = st.selectbox("Initial Warehouse", list(w_dict.keys()))

                    price = st.number_input("Purchase Price (€)", min_value=0.0, value=0.0, step=0.1)
                    sell_p = st.number_input("Selling Price (€)", min_value=0.0, value=0.0, step=0.1)
                    stock_qty = st.number_input("Current Stock Quantity", min_value=0.0, value=0.0)

                    if st.form_submit_button("💾 Save Buy Part"):
                        if code and name:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO stock_items 
                                    (code, name, category, sub_group, supplier_id, unit_id, warehouse_id, purchase_price, selling_price, current_stock)
                                    VALUES (?, ?, 'BUY PART', 'Buy Parts', ?, ?, ?, ?, ?, ?)
                                """, (code.strip(), name.strip(), s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), price, sell_p, stock_qty))
                                conn.commit()
                                st.success(f"Buy Part {code} saved successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

        st.write("")
        search_buy = st.text_input("🔍 Search Buy Parts", placeholder="Type to filter...", label_visibility="collapsed")

        q_buy = """
            SELECT 
                si.id as ID,
                si.code as 'Part No.',
                si.name as 'Part Description',
                s.name as 'Preferred Supplier',
                u.code as 'UoM',
                w.name as 'Warehouse',
                si.purchase_price as 'Purchase Price (€)',
                si.selling_price as 'Selling Price (€)',
                si.current_stock as 'In Stock'
            FROM stock_items si
            LEFT JOIN suppliers s ON si.supplier_id = s.id
            LEFT JOIN units u ON si.unit_id = u.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE si.category = 'BUY PART'
        """
        params_buy = []
        if search_buy:
            q_buy += " AND (si.code LIKE ? OR si.name LIKE ?)"
            params_buy.extend([f"%{search_buy}%", f"%{search_buy}%"])

        df_buy = pd.read_sql_query(q_buy, conn, params=params_buy)
        st.dataframe(df_buy, use_container_width=True, hide_index=True)

    # --- TAB 3: FINISHED GOODS ---
    elif active_subtab == "Finished_Goods":
        c_head, c_btn1 = st.columns([8, 2])
        with c_head:
            st.markdown("##### Finished Goods & Subassemblies")
        
        with c_btn1:
            with st.popover("➕ Add Finished Good", use_container_width=True):
                with st.form("add_finished_form"):
                    code = st.text_input("Product Code / Part No. *")
                    name = st.text_input("Product Description *")
                    cat = st.selectbox("Category", ["FINISHED GOOD", "SUBASSEMBLY"])
                    
                    df_u_opts = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn)
                    u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u_opts.iterrows()}
                    selected_u = st.selectbox("Unit of Measure", list(u_dict.keys()))

                    df_w_opts = pd.read_sql_query("SELECT id, name FROM warehouses ORDER BY name", conn)
                    w_dict = {r['name']: r['id'] for _, r in df_w_opts.iterrows()}
                    selected_w = st.selectbox("Storage Warehouse", list(w_dict.keys()))

                    sell_price = st.number_input("Selling Price (€)", min_value=0.0, value=0.0, step=0.5)
                    stock_qty = st.number_input("In Stock Quantity", min_value=0.0, value=0.0)

                    if st.form_submit_button("💾 Save Finished Good"):
                        if code and name:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO stock_items 
                                    (code, name, category, unit_id, warehouse_id, selling_price, current_stock)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (code.strip(), name.strip(), cat, u_dict.get(selected_u), w_dict.get(selected_w), sell_price, stock_qty))
                                conn.commit()
                                st.success(f"Product {code} saved successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

        st.write("")
        search_fin = st.text_input("🔍 Search Finished Goods", placeholder="Type to filter...", label_visibility="collapsed")

        q_fin = """
            SELECT 
                si.id as ID,
                si.code as 'Product Code',
                si.name as 'Product Description',
                si.category as 'Category',
                u.code as 'UoM',
                w.name as 'Warehouse',
                si.selling_price as 'Selling Price (€)',
                si.current_stock as 'In Stock'
            FROM stock_items si
            LEFT JOIN units u ON si.unit_id = u.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE si.category IN ('FINISHED GOOD', 'SUBASSEMBLY')
        """
        params_fin = []
        if search_fin:
            q_fin += " AND (si.code LIKE ? OR si.name LIKE ?)"
            params_fin.extend([f"%{search_fin}%", f"%{search_fin}%"])

        df_fin = pd.read_sql_query(q_fin, conn, params=params_fin)
        st.dataframe(df_fin, use_container_width=True, hide_index=True)

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
