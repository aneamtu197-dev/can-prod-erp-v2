import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="CAN Prod ERP Custom", layout="wide", initial_sidebar_state="collapsed")

# 2. Database Initialization
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

    # Raw Materials, Buy Parts & Finished Goods Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(100) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(50) DEFAULT 'RAW MATERIAL',
        supplier_id INTEGER,
        unit_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        purchase_price REAL DEFAULT 0.0,
        selling_price REAL DEFAULT 0.0,
        current_stock REAL DEFAULT 0.0,
        min_stock REAL DEFAULT 0.0,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
        FOREIGN KEY (unit_id) REFERENCES units(id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
    );
    """)

    # Populate Default Units
    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:
        for c, n in [('pcs', 'Pieces'), ('kg', 'Kilograms'), ('m2', 'Square Meters'), ('l', 'Liters'), ('m', 'Linear Meters')]:
            cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (c, n))

    # Populate Default Warehouses
    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        for c, n, t in [('WH-MAIN', 'Main Central Warehouse', 'Internal Warehouse'), ('WH-CUST', 'Customer Virtual Location', 'Customer Virtual Storage')]:
            cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (c, n, t))

    # Populate Default Suppliers
    cursor.execute("SELECT COUNT(*) FROM suppliers")
    if cursor.fetchone()[0] == 0:
        for c, n, cp, p, e, lt in [('SUP001', 'Powder Coating Supplier SRL', 'John Smith', '+40722111222', 'orders@coating.com', 3), ('SUP002', 'Steel & Metal Producer SA', 'Mary Doe', '+40733444555', 'sales@steel.com', 5)]:
            cursor.execute("INSERT INTO suppliers (code, name, contact_person, phone, email, lead_time_days) VALUES (?, ?, ?, ?, ?, ?)", (c, n, cp, p, e, lt))

    conn.commit()
    conn.close()

init_custom_db()

def get_db():
    return sqlite3.connect('can_prod_v2.db')

# Function to Import MRPeasy CSV Into Stock
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

        name = str(row.get('part description', row.get('description', row.get('name', code)))).strip()
        
        # Category Mapping
        group = str(row.get('group number', row.get('group name', row.get('group', '')))).upper()
        if 'BUY' in group:
            category = 'BUY PART'
        elif 'SUB' in group:
            category = 'SUBASSEMBLY'
        elif 'FINISH' in group or 'PRODUS' in group:
            category = 'FINISHED GOOD'
        else:
            category = 'RAW MATERIAL'

        # Unit of Measure
        u_code = str(row.get('uom', row.get('unit of measure', row.get('unit', 'pcs')))).strip()
        cursor.execute("SELECT id FROM units WHERE code = ?", (u_code,))
        u_row = cursor.fetchone()
        if u_row:
            unit_id = u_row[0]
        else:
            cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (u_code, u_code))
            unit_id = cursor.lastrowid

        # Warehouse / Location
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

        # Numerical Values
        try: price = float(row.get('cost', row.get('cost price', 0)))
        except: price = 0.0

        try: sell_price = float(row.get('selling price', row.get('price', 0)))
        except: sell_price = 0.0

        try: stock = float(row.get('in stock', row.get('available', row.get('stoc', 0))))
        except: stock = 0.0

        try: min_st = float(row.get('reorder point', row.get('min stock', 0)))
        except: min_st = 0.0

        cursor.execute("SELECT id FROM stock_items WHERE code = ?", (code,))
        ex = cursor.fetchone()
        if ex:
            cursor.execute("""
                UPDATE stock_items SET name=?, category=?, unit_id=?, warehouse_id=?, purchase_price=?, selling_price=?, current_stock=?, min_stock=?
                WHERE code=?
            """, (name, category, unit_id, warehouse_id, price, sell_price, stock, min_st, code))
            updated_count += 1
        else:
            cursor.execute("""
                INSERT INTO stock_items (code, name, category, unit_id, warehouse_id, purchase_price, selling_price, current_stock, min_stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, category, unit_id, warehouse_id, price, sell_price, stock, min_st))
            imported_count += 1

    conn.commit()
    conn.close()
    return imported_count, updated_count

# 3. Query Parameters Navigation
query_params = st.query_params
active_page = query_params.get("page", "Home")
active_subtab = query_params.get("subtab", "Raw_Materials")

# 4. Aqua Minimalist Styling With 3D Big Buttons & Metric Cards
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
# 2. STOCK MODULE (WITH RAW MATERIALS, BUY PARTS & FINISHED GOODS)
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
            st.markdown("##### Raw Materials Inventory")
        
        with c_btn1:
            with st.popover("➕ Add Raw Material", use_container_width=True):
                with st.form("add_raw_form"):
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

                    price = st.number_input("Purchase Price (€)", min_value=0.0, value=0.0, step=0.5)
                    stock_qty = st.number_input("Current Stock Quantity", min_value=0.0, value=0.0)
                    min_stock_qty = st.number_input("Reorder Point / Min. Stock", min_value=0.0, value=0.0)

                    if st.form_submit_button("💾 Save Raw Material"):
                        if code and name:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO stock_items 
                                    (code, name, category, supplier_id, unit_id, warehouse_id, purchase_price, current_stock, min_stock)
                                    VALUES (?, ?, 'RAW MATERIAL', ?, ?, ?, ?, ?, ?)
                                """, (code.strip(), name.strip(), s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), price, stock_qty, min_stock_qty))
                                conn.commit()
                                st.success(f"Raw Material {code} saved successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

        with c_btn2:
            with st.popover("↑ Import MRPeasy CSV", use_container_width=True):
                st.caption("Upload the CSV file exported from MRPeasy to import materials automatically.")
                csv_file = st.file_uploader("Upload CSV", type=['csv'], key="import_items_csv")
                if csv_file is not None:
                    try:
                        df_up = pd.read_csv(csv_file)
                        st.write("File Preview:")
                        st.dataframe(df_up.head(3))
                        if st.button("🚀 Execute Import"):
                            ins, upd = import_mrpeasy_items(df_up)
                            st.success(f"Import Successful! Added: {ins}, Updated: {upd}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Import Error: {e}")

        st.write("")
        search_raw = st.text_input("🔍 Search Raw Materials by Part No. or Description", placeholder="Type to filter...", label_visibility="collapsed")

        q_raw = """
            SELECT 
                si.id as ID,
                si.code as 'Part No.',
                si.name as 'Part Description',
                s.name as 'Preferred Supplier',
                u.code as 'UoM',
                w.name as 'Warehouse',
                si.purchase_price as 'Purchase Price (€)',
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

        df_raw = pd.read_sql_query(q_raw, conn, params=params_raw)
        st.dataframe(df_raw, use_container_width=True, hide_index=True)

    # --- TAB 2: BUY PARTS ---
    elif active_subtab == "Buy_Parts":
        c_head, c_btn1 = st.columns([8, 2])
        with c_head:
            st.markdown("##### Purchased Parts (Buy Parts)")
        
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

                    price = st.number_input("Purchase Price (€)", min_value=0.0, value=0.0, step=0.5)
                    stock_qty = st.number_input("Current Stock Quantity", min_value=0.0, value=0.0)
                    min_stock_qty = st.number_input("Reorder Point / Min. Stock", min_value=0.0, value=0.0)

                    if st.form_submit_button("💾 Save Buy Part"):
                        if code and name:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO stock_items 
                                    (code, name, category, supplier_id, unit_id, warehouse_id, purchase_price, current_stock, min_stock)
                                    VALUES (?, ?, 'BUY PART', ?, ?, ?, ?, ?, ?)
                                """, (code.strip(), name.strip(), s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), price, stock_qty, min_stock_qty))
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
                si.current_stock as 'In Stock',
                si.min_stock as 'Reorder Point'
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
