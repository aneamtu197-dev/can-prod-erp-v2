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

    # Raw Materials & Stock Items Table
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

# Function to Import MRPeasy CSV Into Stock (Raw Materials)
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
        if 'BUY' in group or 'MATERIA' in group or 'RAW' in group:
            category = 'RAW MATERIAL'
        elif 'SUB' in group:
            category = 'SUBASSEMBLY'
        else:
            category = 'BUY PART'

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

        try: stock = float(row.get('in stock', row.get('available', row.get('stoc', 0))))
        except: stock = 0.0

        try: min_st = float(row.get('reorder point', row.get('min stock', 0)))
        except: min_st = 0.0

        cursor.execute("SELECT id FROM stock_items WHERE code = ?", (code,))
        ex = cursor.fetchone()
        if ex:
            cursor.execute("""
                UPDATE stock_items SET name=?, category=?, unit_id=?, warehouse_id=?, purchase_price=?, current_stock=?, min_stock=?
                WHERE code=?
            """, (name, category, unit_id, warehouse_id, price, stock, min_st, code))
            updated_count += 1
        else:
            cursor.execute("""
                INSERT INTO stock_items (code, name, category, unit_id, warehouse_id, purchase_price, current_stock, min_stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, category, unit_id, warehouse_id, price, stock, min_st))
            imported_count += 1

    conn.commit()
    conn.close()
    return imported_count, updated_count

# 3. Query Parameters Navigation
query_params = st.query_params
active_page = query_params.get("page", "Home")
active_subtab = query_params.get("subtab", "Raw_Materials")

# 4. Aqua Minimalist Styling
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    [data-testid="stSidebar"] { display: none; }

    .top-header {
        background: linear-gradient(135deg, #0284c7 0%, #06b6d4 100%);
        color: #ffffff;
        padding: 10px 24px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.15);
    }
    .top-header h3 { margin: 0; font-size: 18px; font-weight: 800; color: #ffffff; }

    .mrp-nav-bar {
        display: flex;
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 6px 12px;
        gap: 10px;
        align-items: center;
        margin-bottom: 20px;
        border-radius: 8px;
    }
    .mrp-nav-item {
        color: #0369a1;
        font-size: 13px;
        font-weight: 700;
        text-decoration: none;
        padding: 6px 14px;
        border-radius: 6px;
        transition: all 0.15s ease-in-out;
    }
    .mrp-nav-item:hover { background-color: #e0f2fe; color: #0284c7; }
    .mrp-nav-active { background-color: #0284c7; color: #ffffff !important; }

    .mrp-subtabs {
        display: flex;
        gap: 15px;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 8px;
        margin-bottom: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    .mrp-subtab-active { color: #0284c7; border-bottom: 2px solid #0284c7; padding-bottom: 8px; text-decoration: none; font-weight: 700; }
    .mrp-subtab { color: #64748b; text-decoration: none; }
    .mrp-subtab:hover { color: #0f172a; }

    .launchpad-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin-top: 10px;
    }
    .launchpad-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #0ea5e9;
        border-radius: 10px;
        padding: 24px 20px;
        text-align: center;
        text-decoration: none;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .launchpad-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 20px rgba(14, 165, 233, 0.12);
        border-top-color: #06b6d4;
    }
    .launchpad-icon { font-size: 32px; margin-bottom: 12px; }
    .launchpad-title { font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 6px; }
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

# 6. Main Navigation Bar (English)
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
            <div class="launchpad-desc">Manage Raw Materials, Buy Parts, Suppliers, Warehouses, and Units of Measure.</div>
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
# 2. STOCK MODULE (RAW MATERIALS & MANAGEMENT)
# ==========================================
elif active_page == "Stock":
    
    subtabs = [
        ("Raw_Materials", "📄 Raw Materials"),
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

    # --- SUBTAB 1: RAW MATERIALS ---
    if active_subtab == "Raw_Materials" or active_subtab == "Items":
        c_head, c_btn1, c_btn2 = st.columns([6, 2, 2])
        with c_head:
            st.markdown("##### Raw Materials & Purchased Parts")
        
        with c_btn1:
            with st.popover("➕ Add Raw Material", use_container_width=True):
                with st.form("add_item_form"):
                    code = st.text_input("Part No. / Item Code *")
                    name = st.text_input("Part Description *")
                    cat = st.selectbox("Category", ["RAW MATERIAL", "BUY PART", "CONSUMABLE", "SUBASSEMBLY"])
                    
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
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (code.strip(), name.strip(), cat, s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), price, stock_qty, min_stock_qty))
                                conn.commit()
                                st.success(f"Item {code} saved successfully!")
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
        
        # Compact Filters
        f1, f2 = st.columns([6, 4])
        with f1:
            search_code = st.text_input("🔍 Search by Part No. or Description", placeholder="Type to filter...", label_visibility="collapsed")
        with f2:
            search_cat = st.selectbox("Category", ["All Categories"] + ["RAW MATERIAL", "BUY PART", "CONSUMABLE", "SUBASSEMBLY"], label_visibility="collapsed")

        query_items = """
            SELECT 
                si.id as ID,
                si.code as 'Part No.',
                si.name as 'Part Description',
                si.category as 'Category',
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
            WHERE 1=1
        """
        params_items = []
        if search_code:
            query_items += " AND (si.code LIKE ? OR si.name LIKE ?)"
            params_items.extend([f"%{search_code}%", f"%{search_code}%"])
        if search_cat != "All Categories":
            query_items += " AND si.category = ?"
            params_items.append(search_cat)

        df_items = pd.read_sql_query(query_items, conn, params=params_items)
        st.dataframe(df_items, use_container_width=True, hide_index=True)

    # --- SUBTAB 2: SUPPLIERS ---
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

    # --- SUBTAB 3: WAREHOUSES ---
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

    # --- SUBTAB 4: UNITS OF MEASUREMENT ---
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
