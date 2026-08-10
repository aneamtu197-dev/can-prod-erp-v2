import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 1. Configurare Pagină
st.set_page_config(page_title="CAN Prod ERP", layout="wide", initial_sidebar_state="collapsed")

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

# 3. Query Params pentru Navigare
query_params = st.query_params
active_page = query_params.get("page", "Home")
active_subtab = query_params.get("subtab", "Items")

# 4. CSS REPLICAT DUPĂ POZĂ (Top Bar Aqua + Dark Grid Cards + Recent Items)
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #38bdf8 0%, #7dd3fc 40%, #bae6fd 100%);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    [data-testid="stSidebar"] { display: none; }

    /* Top Bar Meniuri Principale (Exact ca în poză) */
    .top-menu-bar {
        background-color: #0284c7;
        color: #ffffff;
        padding: 8px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 4px;
        margin-bottom: 20px;
        font-size: 13px;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .top-menu-left { display: flex; gap: 18px; align-items: center; }
    .top-menu-link { color: #f0f9ff; text-decoration: none; transition: color 0.15s; }
    .top-menu-link:hover { color: #ffffff; text-decoration: underline; }
    .top-menu-active { color: #ffffff; font-weight: 800; border-bottom: 2px solid #ffffff; }

    /* Search Bar Central */
    .search-box-container {
        display: flex;
        justify-content: center;
        margin-bottom: 30px;
        margin-top: 10px;
    }

    /* Carduri de pe centru (Grid Întunecat) */
    .priority-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 15px;
    }
    .priority-card {
        background-color: #1e293b;
        color: #ffffff;
        border-radius: 6px;
        padding: 22px 15px;
        text-align: center;
        text-decoration: none;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 110px;
        transition: all 0.2s ease-in-out;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .priority-card:hover {
        background-color: #0f172a;
        border-color: #0284c7;
        transform: translateY(-3px);
    }
    .priority-card-icon { font-size: 26px; margin-bottom: 8px; }
    .priority-card-title { font-size: 13px; font-weight: 700; color: #f8fafc; line-height: 1.3; }

    /* Recent Items Lateral Dreapta */
    .recent-items-box {
        background-color: #1e293b;
        color: #f8fafc;
        border-radius: 6px;
        padding: 15px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .recent-items-title {
        font-size: 14px; font-weight: 700; margin-bottom: 12px;
        padding-bottom: 8px; border-bottom: 1px solid #334155; color: #38bdf8;
    }
    .recent-item-link {
        display: block; color: #cbd5e1; text-decoration: none;
        padding: 6px 0; font-size: 12px; border-bottom: 1px dashed #334155;
    }
    .recent-item-link:hover { color: #38bdf8; }

    /* Container alb pentru paginile interioare */
    .content-container {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)

# 5. Top Bar cu Meniuri (Stil Poză)
st.markdown(f"""
<div class="top-menu-bar">
    <div class="top-menu-left">
        <span style="font-size: 16px; font-weight: 900; color: #ffffff; margin-right: 15px;">CAN PROD</span>
        <a href="?page=Home" target="_self" class="top-menu-link {'top-menu-active' if active_page=='Home' else ''}">Acasă</a>
        <a href="?page=Stock" target="_self" class="top-menu-link {'top-menu-active' if active_page=='Stock' else ''}">Gestiune Produse / Stoc</a>
        <a href="?page=BOM" target="_self" class="top-menu-link {'top-menu-active' if active_page=='BOM' else ''}">Producție & Operatori</a>
        <a href="?page=RFQ" target="_self" class="top-menu-link {'top-menu-active' if active_page=='RFQ' else ''}">Vânzări & Oferte</a>
        <a href="?page=Suppliers_Menu" target="_self" class="top-menu-link">Aprovizionare</a>
    </div>
    <div>
        <span style="background-color: #22c55e; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">Sistem Activ</span>
    </div>
</div>
""", unsafe_allow_html=True)

conn = get_db()

# ==========================================
# ECRAN PRINCIPAL (EXACT CA ÎN POZĂ)
# ==========================================
if active_page == "Home":
    
    # Bara de căutare centrală
    col_s1, col_s2, col_s3 = st.columns([2, 6, 2])
    with col_s2:
        search_query = st.text_input("", placeholder="🔍 Search customers, parts, documents and more...", label_visibility="collapsed")

    st.write("")

    # ZONA CENTRALĂ: CARDURI + RECENT ITEMS (2 COLOANE)
    col_cards, col_recent = st.columns([8, 3])

    with col_cards:
        st.markdown("""
        <div class="priority-grid">
            <a href="?page=Stock&subtab=Items" target="_self" class="priority-card">
                <div class="priority-card-icon">📋</div>
                <div class="priority-card-title">Nomenclator Articole</div>
            </a>
            <a href="?page=Stock&subtab=Suppliers" target="_self" class="priority-card">
                <div class="priority-card-icon">🚚</div>
                <div class="priority-card-title">Furnizori</div>
            </a>
            <a href="?page=Stock&subtab=Warehouses" target="_self" class="priority-card">
                <div class="priority-card-icon">🏭</div>
                <div class="priority-card-title">Depozite & Gestiuni</div>
            </a>
            <a href="?page=BOM" target="_self" class="priority-card">
                <div class="priority-card-icon">⚙️</div>
                <div class="priority-card-title">Rețete (BOM)</div>
            </a>
            <a href="?page=BOM" target="_self" class="priority-card">
                <div class="priority-card-icon">⏱️</div>
                <div class="priority-card-title">Norme Lucru Operatori</div>
            </a>
            <a href="?page=RFQ" target="_self" class="priority-card">
                <div class="priority-card-icon">📄</div>
                <div class="priority-card-title">Oferte Preț</div>
            </a>
            <a href="?page=RFQ" target="_self" class="priority-card">
                <div class="priority-card-icon">📦</div>
                <div class="priority-card-title">Comenzi Vânzare</div>
            </a>
            <a href="?page=Stock&subtab=Units" target="_self" class="priority-card">
                <div class="priority-card-icon">📏</div>
                <div class="priority-card-title">Unități de Măsură</div>
            </a>
            <a href="?page=Home" target="_self" class="priority-card">
                <div class="priority-card-icon">📊</div>
                <div class="priority-card-title">Rapoarte Stoc</div>
            </a>
            <a href="?page=Home" target="_self" class="priority-card">
                <div class="priority-card-icon">👤</div>
                <div class="priority-card-title">Setări Utilizatori</div>
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col_recent:
        st.markdown("""
        <div class="recent-items-box">
            <div class="recent-items-title">Recent Items</div>
            <a href="?page=Stock&subtab=Items" target="_self" class="recent-item-link">📄 Nomenclator Articole</a>
            <a href="?page=Stock&subtab=Suppliers" target="_self" class="recent-item-link">🚚 Lista Furnizori</a>
            <a href="?page=Stock&subtab=Warehouses" target="_self" class="recent-item-link">🏭 Depozite Central</a>
            <a href="?page=BOM" target="_self" class="recent-item-link">⚙️ Configurare Operații</a>
            <a href="?page=RFQ" target="_self" class="recent-item-link">📄 Oferte RFQ</a>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# ECRANE INTERIOARE (AFIȘATE ÎN CONTAINER ALB)
# ==========================================
elif active_page == "Stock":
    st.markdown('<div class="content-container">', unsafe_allow_html=True)
    
    st.subheader("📦 Gestiune Produse / Stoc")
    
    subtabs = [
        ("Items", "📄 Nomenclator Articole"),
        ("Suppliers", "🚚 Furnizori"),
        ("Warehouses", "🏭 Depozite / Gestiuni"),
        ("Units", "📏 Unități de Măsură")
    ]

    cols_t = st.columns(len(subtabs))
    for idx, (tab_k, tab_l) in enumerate(subtabs):
        with cols_t[idx]:
            if st.button(tab_l, use_container_width=True, type="primary" if active_subtab==tab_k else "secondary"):
                st.markdown(f'<meta http-equiv="refresh" content="0; url=?page=Stock&subtab={tab_k}">', unsafe_allow_html=True)

    st.write("")

    if active_subtab == "Items":
        c_head, c_btn = st.columns([8, 2])
        with c_head:
            st.markdown("##### Articole Stoc (Materie Primă & Buy Parts)")
        with c_btn:
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
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO stock_items 
                                (code, name, category, supplier_id, unit_id, warehouse_id, purchase_price, current_stock, min_stock)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (code.strip(), name.strip(), cat, s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), price, stock_qty, min_stock_qty))
                            conn.commit()
                            st.success("Articol salvat!")
                            st.rerun()

        st.write("")
        df_items = pd.read_sql_query("""
            SELECT si.code as 'Cod Reper', si.name as 'Denumire Articol', si.category as Categorie, s.name as Furnizor, u.code as UM, w.name as Depozit, si.purchase_price as 'Preț (€)', si.current_stock as 'Stoc'
            FROM stock_items si LEFT JOIN suppliers s ON si.supplier_id=s.id LEFT JOIN units u ON si.unit_id=u.id LEFT JOIN warehouses w ON si.warehouse_id=w.id
        """, conn)
        st.dataframe(df_items, use_container_width=True, hide_index=True)

    elif active_subtab == "Suppliers":
        st.markdown("##### Furnizori (Suppliers)")
        df_s = pd.read_sql_query("SELECT code as Cod, name as 'Nume Furnizor', contact_person as Contact, phone as Telefon, email as Email FROM suppliers", conn)
        st.dataframe(df_s, use_container_width=True, hide_index=True)

    elif active_subtab == "Warehouses":
        st.markdown("##### Depozite & Locații")
        df_w = pd.read_sql_query("SELECT code as Cod, name as 'Denumire Depozit', location_type as Tip FROM warehouses", conn)
        st.dataframe(df_w, use_container_width=True, hide_index=True)

    elif active_subtab == "Units":
        st.markdown("##### Unități de Măsură")
        df_u = pd.read_sql_query("SELECT code as Cod, name as Descriere FROM units", conn)
        st.dataframe(df_u, use_container_width=True, hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)

elif active_page == "BOM":
    st.markdown('<div class="content-container">', unsafe_allow_html=True)
    st.subheader("⚙️ Producție & Rețete Tehnologice (BOM)")
    st.info("Aici se definesc rețetele și normele de lucru.")
    st.markdown('</div>', unsafe_allow_html=True)

elif active_page == "RFQ":
    st.markdown('<div class="content-container">', unsafe_allow_html=True)
    st.subheader("📊 Oferte & Comenzi Vânzare")
    st.info("Aici se generează calculațiile de preț și ofertele.")
    st.markdown('</div>', unsafe_allow_html=True)

conn.close()
