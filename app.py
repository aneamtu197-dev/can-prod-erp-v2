import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 1. Configurare Pagină
st.set_page_config(page_title="CAN Prod ERP Custom", layout="wide", initial_sidebar_state="expanded")

# 2. Inițializare Bază de Date Nouă
def init_custom_db():
    conn = sqlite3.connect('can_prod_v2.db')
    cursor = conn.cursor()
    
    # Suppliers
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

    # Units
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL
    );
    """)

    # Warehouses
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        location_type VARCHAR(100) DEFAULT 'Internal Warehouse'
    );
    """)

    # Stock Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(100) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(50) DEFAULT 'MATERIE PRIMA',
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

    # Populate Defaults
    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:
        for c, n in [('pcs', 'Bucăți'), ('kg', 'Kilograme'), ('m2', 'Metri Pătrați'), ('l', 'Litri'), ('Ml', 'Metri Liniari')]:
            cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (c, n))

    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        for c, n, t in [('DEP-M', 'Depozit Central Materii Prime', 'Internal Warehouse'), ('DEP-C', 'Gestiune Virtuală Clienți', 'Customer Virtual Storage')]:
            cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (c, n, t))

    cursor.execute("SELECT COUNT(*) FROM suppliers")
    if cursor.fetchone()[0] == 0:
        for c, n, cp, p, e, lt in [('F001', 'Furnizor Vopsea Pulbere SRL', 'Ion Popescu', '0722111222', 'comenzi@vopsea.ro', 3), ('F002', 'Producător Inox & Metal SA', 'Maria Dan', '0733444555', 'vanzari@inox.ro', 5)]:
            cursor.execute("INSERT INTO suppliers (code, name, contact_person, phone, email, lead_time_days) VALUES (?, ?, ?, ?, ?, ?)", (c, n, cp, p, e, lt))

    conn.commit()
    conn.close()

init_custom_db()

def get_db():
    return sqlite3.connect('can_prod_v2.db')

# 3. SELECTOR DINAMIC DE INTERFAȚĂ & CROMATICA AQUA
st.sidebar.markdown("### 🎨 Personalizare Interfață")
ui_style = st.sidebar.selectbox("Alege Stilul Vizual (Aqua Themes)", [
    "1. Aqua Glass Modern (Recomandat)",
    "2. Minimalist Clean Aqua",
    "3. Industrial Aqua & Dark Slate"
])

# STILURI CSS APLICATE DINAMIC
if "1." in ui_style: # Aqua Glass Modern
    css_theme = """
    <style>
        .stApp { background-color: #f0f9ff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .main-card-header {
            background: linear-gradient(135deg, #0284c7 0%, #06b6d4 100%);
            color: #ffffff; padding: 18px 25px; border-radius: 12px;
            box-shadow: 0 4px 15px rgba(14, 165, 233, 0.2); margin-bottom: 25px;
        }
        .metric-box {
            background: #ffffff; border-radius: 10px; padding: 15px;
            border-left: 4px solid #0ea5e9; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 20px; border-radius: 8px; background-color: #e0f2fe; color: #0369a1; font-weight: 600;
        }
        .stTabs [aria-selected="true"] { background-color: #0284c7 !important; color: white !important; }
    </style>
    """
elif "2." in ui_style: # Minimalist Clean Aqua
    css_theme = """
    <style>
        .stApp { background-color: #ffffff; }
        .main-card-header {
            background-color: #f0f9ff; border: 1px solid #bae6fd; color: #0369a1;
            padding: 15px 20px; border-radius: 8px; margin-bottom: 20px;
        }
        .metric-box {
            background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 16px; border-radius: 4px; background-color: #f1f5f9; color: #475569; font-weight: 600;
        }
        .stTabs [aria-selected="true"] { background-color: #0ea5e9 !important; color: white !important; }
    </style>
    """
else: # Industrial Aqua & Dark Slate
    css_theme = """
    <style>
        .stApp { background-color: #f8fafc; }
        .main-card-header {
            background-color: #0f172a; color: #38bdf8;
            padding: 18px 25px; border-radius: 8px; border-left: 6px solid #06b6d4; margin-bottom: 25px;
        }
        .metric-box {
            background: #1e293b; color: #ffffff; border-radius: 8px; padding: 15px; border: 1px solid #334155;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 20px; border-radius: 6px; background-color: #e2e8f0; color: #1e293b; font-weight: 700;
        }
        .stTabs [aria-selected="true"] { background-color: #0f172a !important; color: #38bdf8 !important; }
    </style>
    """

st.markdown(css_theme, unsafe_allow_html=True)

# 4. Header-ul Aplicației
now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(f"""
<div class="main-card-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="margin:0; font-size: 24px; font-weight: 800;">CAN PROD - Sistem Producție v2</h2>
            <span style="font-size: 13px; opacity: 0.9;">Platformă ERP Customizată &nbsp;|&nbsp; {now_str}</span>
        </div>
        <div style="text-align: right; font-size: 13px; font-weight: 600;">
            📍 Locație: ROU &nbsp;|&nbsp; 👤 Operator: Admin
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. Meniu Lateral Navigare
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Navigare Module")
menu_module = st.sidebar.radio("", [
    "📦 Stoc & Gestiune Materii",
    "⚙️ Operatori & Norme Lucru",
    "📑 Rețete Producție (BOM)",
    "📊 Oferte & Comenzi (RFQ)"
])

conn = get_db()

# ==========================================
# MODUL: STOC & GESTIUNE MATERII
# ==========================================
if menu_module == "📦 Stoc & Gestiune Materii":
    
    # KPI-uri vizuale
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    total_items = conn.cursor().execute("SELECT COUNT(*) FROM stock_items").fetchone()[0]
    total_suppliers = conn.cursor().execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    total_wh = conn.cursor().execute("SELECT COUNT(*) FROM warehouses").fetchone()[0]
    total_units = conn.cursor().execute("SELECT COUNT(*) FROM units").fetchone()[0]

    with col_kpi1:
        st.markdown(f'<div class="metric-box"><span>📦 Total Articole Stoc</span><h2 style="margin:5px 0 0 0; color:#0284c7;">{total_items}</h2></div>', unsafe_allow_html=True)
    with col_kpi2:
        st.markdown(f'<div class="metric-box"><span>🚚 Furnizori Activi</span><h2 style="margin:5px 0 0 0; color:#0284c7;">{total_suppliers}</h2></div>', unsafe_allow_html=True)
    with col_kpi3:
        st.markdown(f'<div class="metric-box"><span>🏭 Depozite / Gestiuni</span><h2 style="margin:5px 0 0 0; color:#0284c7;">{total_wh}</h2></div>', unsafe_allow_html=True)
    with col_kpi4:
        st.markdown(f'<div class="metric-box"><span>📏 Unități de Măsură</span><h2 style="margin:5px 0 0 0; color:#0284c7;">{total_units}</h2></div>', unsafe_allow_html=True)

    st.write("")
    st.write("")

    # Tabs Principal Stoc
    tab_items, tab_suppliers, tab_warehouses, tab_units = st.tabs([
        "📄 Articole Stoc (Materie Primă & Buy Parts)",
        "🚚 Furnizori (Suppliers)",
        "🏭 Depozite & Gestiuni (Warehouses)",
        "📏 Unități de Măsură (Units)"
    ])

    # --- TAB 1: ARTICOLE STOC ---
    with tab_items:
        c1, c2, c3 = st.columns([6, 2, 2])
        with c1:
            st.markdown("#### Nomenclator Articole")
        with c2:
            with st.popover("➕ Adaugă Articol Nou", use_container_width=True):
                with st.form("add_item_form"):
                    code = st.text_input("Cod Articol / Part No. *")
                    name = st.text_input("Denumire Articol *")
                    cat = st.selectbox("Categorie", ["MATERIE PRIMA", "BUY PART", "CONSUMABIL", "SUBANSAMBLU"])
                    
                    df_s_opts = pd.read_sql_query("SELECT id, name FROM suppliers ORDER BY name", conn)
                    s_dict = {r['name']: r['id'] for _, r in df_s_opts.iterrows()}
                    selected_s = st.selectbox("Furnizor Preferat", list(s_dict.keys()) if s_dict else ["Fără furnizor"])
                    
                    df_u_opts = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn)
                    u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u_opts.iterrows()}
                    selected_u = st.selectbox("Unitate de Măsură", list(u_dict.keys()))

                    df_w_opts = pd.read_sql_query("SELECT id, name FROM warehouses ORDER BY name", conn)
                    w_dict = {r['name']: r['id'] for _, r in df_w_opts.iterrows()}
                    selected_w = st.selectbox("Depozit Ințial", list(w_dict.keys()))

                    price = st.number_input("Preț Achiziție (€)", min_value=0.0, value=0.0, step=0.5)
                    stock_qty = st.number_input("Stoc Curent", min_value=0.0, value=0.0)
                    min_stock_qty = st.number_input("Stoc Minim Siguranță", min_value=0.0, value=0.0)

                    if st.form_submit_button("💾 Salvează Articolul"):
                        if code and name:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO stock_items 
                                    (code, name, category, supplier_id, unit_id, warehouse_id, purchase_price, current_stock, min_stock)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (code.strip(), name.strip(), cat, s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), price, stock_qty, min_stock_qty))
                                conn.commit()
                                st.success(f"Articolul {code} a fost salvat!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Eroare: {e}")

        with c3:
            with st.popover("↑ Import din MRPeasy CSV", use_container_width=True):
                st.caption("Alege fișierul CSV exportat din MRPeasy pentru încărcare automată.")
                st.file_uploader("Încarcă fișier CSV", type=['csv'], key="import_items_csv")

        st.write("")
        
        # Căutare și Filtrare
        f_c1, f_c2 = st.columns([6, 4])
        with f_c1:
            search_code = st.text_input("🔍 Căutare după Cod sau Denumire", placeholder="Caută reper...")
        with f_c2:
            search_cat = st.selectbox("Categorie", ["Toate"] + ["MATERIE PRIMA", "BUY PART", "CONSUMABIL", "SUBANSAMBLU"])

        query_items = """
            SELECT 
                si.id as ID,
                si.code as 'Cod Reper',
                si.name as 'Denumire Articol',
                si.category as 'Categorie',
                s.name as 'Furnizor Preferat',
                u.code as 'U.M.',
                w.name as 'Depozit',
                si.purchase_price as 'Preț (€)',
                si.current_stock as 'Stoc Curent',
                si.min_stock as 'Stoc Min.'
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
        if search_cat != "Toate":
            query_items += " AND si.category = ?"
            params_items.append(search_cat)

        df_items = pd.read_sql_query(query_items, conn, params=params_items)
        st.dataframe(df_items, use_container_width=True, hide_index=True)

    # --- TAB 2: FURNIZORI ---
    with tab_suppliers:
        s_top1, s_top2 = st.columns([8, 2])
        with s_top1:
            st.markdown("#### Lista Furnizorilor")
        with s_top2:
            with st.popover("➕ Adaugă Furnizor", use_container_width=True):
                with st.form("add_supplier_form"):
                    s_code = st.text_input("Cod Furnizor (ex: F003)")
                    s_name = st.text_input("Nume Furnizor *")
                    s_contact = st.text_input("Persoană Contact")
                    s_phone = st.text_input("Telefon")
                    s_email = st.text_input("E-mail")
                    s_lt = st.number_input("Timp livrare (zile)", min_value=0, value=3)

                    if st.form_submit_button("Salvează Furnizor"):
                        if s_code and s_name:
                            conn.cursor().execute("INSERT INTO suppliers (code, name, contact_person, phone, email, lead_time_days) VALUES (?, ?, ?, ?, ?, ?)", (s_code, s_name, s_contact, s_phone, s_email, s_lt))
                            conn.commit()
                            st.rerun()

        df_s = pd.read_sql_query("SELECT code as Cod, name as 'Nume Furnizor', contact_person as 'Persoană Contact', phone as Telefon, email as Email, lead_time_days as 'Timp Livrare (Zile)' FROM suppliers ORDER BY name", conn)
        st.dataframe(df_s, use_container_width=True, hide_index=True)

    # --- TAB 3: DEPOZITE ---
    with tab_warehouses:
        w_top1, w_top2 = st.columns([8, 2])
        with w_top1:
            st.markdown("#### Depozite & Locații Stocare")
        with w_top2:
            with st.popover("➕ Adaugă Depozit", use_container_width=True):
                with st.form("add_wh_form"):
                    w_code = st.text_input("Cod Locație (ex: DEP-03)")
                    w_name = st.text_input("Denumire Depozit / Client")
                    w_type = st.selectbox("Tip Depozit", ["Internal Warehouse", "Customer Storage", "Virtual Zone"])
                    if st.form_submit_button("Save"):
                        conn.cursor().execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (w_code, w_name, w_type))
                        conn.commit()
                        st.rerun()

        df_w = pd.read_sql_query("SELECT code as Cod, name as 'Denumire Depozit / Locație', location_type as 'Tip Gestiune' FROM warehouses ORDER BY name", conn)
        st.dataframe(df_w, use_container_width=True, hide_index=True)

    # --- TAB 4: UNITĂȚI DE MĂSURĂ ---
    with tab_units:
        u_top1, u_top2 = st.columns([8, 2])
        with u_top1:
            st.markdown("#### Unități de Măsură")
        with u_top2:
            with st.popover("➕ Adaugă Unitate", use_container_width=True):
                with st.form("add_u_form"):
                    u_code = st.text_input("Cod Unitate (ex: buc)")
                    u_name = st.text_input("Descriere (ex: Bucăți)")
                    if st.form_submit_button("Save"):
                        conn.cursor().execute("INSERT INTO units (code, name) VALUES (?, ?)", (u_code, u_name))
                        conn.commit()
                        st.rerun()

        df_u = pd.read_sql_query("SELECT code as Cod, name as 'Descriere Unitate' FROM units ORDER BY code", conn)
        st.dataframe(df_u, use_container_width=True, hide_index=True)

else:
    st.subheader(f"Modul: {menu_module}")
    st.info("Pregătit pentru configurarea detaliată în pasul următor.")

conn.close()
