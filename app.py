import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 1. Configurare Pagină
st.set_page_config(page_title="CAN Prod ERP Custom", layout="wide", initial_sidebar_state="collapsed")

# 2. Inițializare Bază de Date Custom
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

# 3. Preluare Pagină curentă din Query Parameters (Pentru navigare instantă fără reîncărcare grea)
query_params = st.query_params
active_page = query_params.get("page", "Home")
active_subtab = query_params.get("subtab", "Items")

# 4. Stilizare Aqua Glass Minimalistă & Aerisită
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    [data-testid="stSidebar"] { display: none; }

    /* Top Bar Aerisită Aqua */
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

    /* Meniu Icoane Orizontal (MRPeasy Style) */
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

    /* Subtabs Orizontale Aerisite */
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

    /* Launchpad Carduri Minimaliste (Pagină Principală) */
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

# 5. Top Bar Superior
now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(f"""
<div class="top-header">
    <div>
        <h3>CAN PROD &nbsp;|&nbsp; ERP Custom</h3>
    </div>
    <div style="font-size: 12px; font-weight: 600; opacity: 0.95;">
        🌐 ROU &nbsp;|&nbsp; 👤 Admin &nbsp;|&nbsp; ⏱️ {now_str}
    </div>
</div>
""", unsafe_allow_html=True)

# 6. Meniu Meniu Orizontal de Navigare Quick-Links
active_h = "mrp-nav-active" if active_page == "Home" else ""
active_s = "mrp-nav-active" if active_page == "Stock" else ""
active_b = "mrp-nav-active" if active_page == "BOM" else ""
active_r = "mrp-nav-active" if active_page == "RFQ" else ""

st.markdown(f"""
<div class="mrp-nav-bar">
    <a href="?page=Home" target="_self" class="mrp-nav-item {active_h}">🏠 Acasă</a>
    <a href="?page=Stock" target="_self" class="mrp-nav-item {active_s}">📦 Stoc & Gestiune</a>
    <a href="?page=BOM" target="_self" class="mrp-nav-item {active_b}">📑 Rețete & Operatori</a>
    <a href="?page=RFQ" target="_self" class="mrp-nav-item {active_r}">📊 Oferte & Comenzi</a>
</div>
""", unsafe_allow_html=True)

conn = get_db()

# ==========================================
# 1. ECRAN PRINCIPAL (LAUNCHPAD MINIMALIST)
# ==========================================
if active_page == "Home":
    st.markdown("#### Meniu Principal")
    st.caption("Alege modulul pe care dorești să îl accesezi. Datele se încarcă numai la deschiderea modulului.")
    st.write("")

    st.markdown("""
    <div class="launchpad-grid">
        <a href="?page=Stock" target="_self" class="launchpad-card">
            <div class="launchpad-icon">📦</div>
            <div class="launchpad-title">Stoc & Gestiune</div>
            <div class="launchpad-desc">Articole materii prime, piese cumpărate, furnizori, depozite și unități.</div>
        </a>
        <a href="?page=BOM" target="_self" class="launchpad-card">
            <div class="launchpad-icon">📑</div>
            <div class="launchpad-title">Rețete & Tehnologie</div>
            <div class="launchpad-desc">Definire bonuri de consum (BOM), norme de lucru și tarife operații.</div>
        </a>
        <a href="?page=RFQ" target="_self" class="launchpad-card">
            <div class="launchpad-icon">📊</div>
            <div class="launchpad-title">Oferte & Comenzi</div>
            <div class="launchpad-desc">Generare calculații de preț, oferte RFQ și comenzi de vânzare clienți.</div>
        </a>
        <a href="?page=Home" target="_self" class="launchpad-card">
            <div class="launchpad-icon">⚙️</div>
            <div class="launchpad-title">Setări & Utilitare</div>
            <div class="launchpad-desc">Configurări generale, drepturi utilizatori și import/export date.</div>
        </a>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MODUL STOC & GESTIUNE (ÎNCĂRCARE DOAR LA SOLICITARE)
# ==========================================
elif active_page == "Stock":
    
    subtabs = [
        ("Items", "📄 Nomenclator Articole"),
        ("Suppliers", "🚚 Furnizori"),
        ("Warehouses", "🏭 Depozite / Gestiuni"),
        ("Units", "📏 Unități de Măsură")
    ]

    subtabs_html = '<div class="mrp-subtabs">'
    for tab_key, tab_label in subtabs:
        act_class = "mrp-subtab-active" if active_subtab == tab_key else "mrp-subtab"
        subtabs_html += f'<a href="?page=Stock&subtab={tab_key}" target="_self" class="{act_class}">{tab_label}</a>'
    subtabs_html += '</div>'

    st.markdown(subtabs_html, unsafe_allow_html=True)

    # --- SUBTAB 1: NOMENCLATOR ARTICOLE ---
    if active_subtab == "Items":
        c_head, c_btn1, c_btn2 = st.columns([6, 2, 2])
        with c_head:
            st.markdown("##### Articole Stoc (Materie Primă & Buy Parts)")
        
        with c_btn1:
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

        with c_btn2:
            with st.popover("↑ Import MRPeasy CSV", use_container_width=True):
                st.caption("Încarcă fișierul CSV exportat din MRPeasy.")
                st.file_uploader("CSV Stoc", type=['csv'], key="import_items_csv")

        st.write("")
        
        # Filtre Compacte
        f1, f2 = st.columns([6, 4])
        with f1:
            search_code = st.text_input("🔍 Căutare după Cod sau Denumire", placeholder="Tastează pentru a filtra...", label_visibility="collapsed")
        with f2:
            search_cat = st.selectbox("Categorie", ["Toate Categories"] + ["MATERIE PRIMA", "BUY PART", "CONSUMABIL", "SUBANSAMBLU"], label_visibility="collapsed")

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
        if search_cat != "Toate Categories":
            query_items += " AND si.category = ?"
            params_items.append(search_cat)

        df_items = pd.read_sql_query(query_items, conn, params=params_items)
        st.dataframe(df_items, use_container_width=True, hide_index=True)

    # --- SUBTAB 2: FURNIZORI ---
    elif active_subtab == "Suppliers":
        s_head, s_btn = st.columns([8, 2])
        with s_head:
            st.markdown("##### Gestiune Furnizori (Suppliers)")
        with s_btn:
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

    # --- SUBTAB 3: DEPOZITE ---
    elif active_subtab == "Warehouses":
        w_head, w_btn = st.columns([8, 2])
        with w_head:
            st.markdown("##### Depozite & Gestiuni Locații")
        with w_btn:
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

    # --- SUBTAB 4: UNITĂȚI ---
    elif active_subtab == "Units":
        u_head, u_btn = st.columns([8, 2])
        with u_head:
            st.markdown("##### Unități de Măsură")
        with u_btn:
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

# ==========================================
# 3. CELELALTE MODULE
# ==========================================
elif active_page == "BOM":
    st.markdown("#### Rețete de Producție (BOM) & Operatori")
    st.info("Modulul de Rețete & Tehnologie este gata de configurat.")

elif active_page == "RFQ":
    st.markdown("#### Oferte & Comenzi (RFQ)")
    st.info("Modulul de Oferte & Comenzi este gata de configurat.")

conn.close()
