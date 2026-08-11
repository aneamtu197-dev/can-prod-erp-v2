import streamlit as st
from db import init_custom_db, get_db
from ui import load_css, render_top_header, render_nav_bar

# Importăm noile noastre module separate!
from module_stock import render_stock_page
from module_bom import render_bom_page
from module_rfq import render_rfq_page

st.set_page_config(page_title="CAN Prod ERP Custom", layout="wide", initial_sidebar_state="collapsed")

# Initialize DB & Load CSS (CACHED pentru viteza maxima)
@st.cache_data
def setup_db_once():
    init_custom_db()
    return True

setup_db_once()
load_css()

# Inject Custom CSS for Resizable Dialog Modals
st.markdown("""
<style>
    div[data-testid="stDialog"] > div {
        resize: both !important;
        overflow: auto !important;
        min-width: 80vw !important;
        max-width: 95vw !important;
        min-height: 70vh !important;
        margin: auto !important;
    }
</style>
""", unsafe_allow_html=True)

query_params = st.query_params
active_page = query_params.get("page", "Home")

# Render UI Headers
render_top_header()
render_nav_bar(active_page)

conn = get_db()

# Session State for Dynamic Dropdown Reset
if "bom_select_version" not in st.session_state:
    st.session_state["bom_select_version"] = 0

# ==========================================
# PAGE ROUTING (Semaforul)
# ==========================================
if active_page == "Home":
    st.markdown("""
    <div class="launchpad-grid">
        <a href="?page=Stock" target="_self" class="launchpad-card"><div class="launchpad-icon">📦</div><div class="launchpad-title">Stock</div></a>
        <a href="?page=BOM" target="_self" class="launchpad-card"><div class="launchpad-icon">📑</div><div class="launchpad-title">Production & BOM</div></a>
        <a href="?page=RFQ" target="_self" class="launchpad-card"><div class="launchpad-icon">📊</div><div class="launchpad-title">Orders & RFQ</div></a>
        <a href="?page=Home" target="_self" class="launchpad-card"><div class="launchpad-icon">⚙️</div><div class="launchpad-title">Settings & Utilities</div></a>
    </div>
    """, unsafe_allow_html=True)

elif active_page == "Stock":
    active_subtab = query_params.get("subtab", "Raw_Materials")
    render_stock_page(conn, active_subtab)

elif active_page == "BOM":
    active_subtab_bom = query_params.get("subtab", "Product")
    render_bom_page(conn, active_subtab_bom)

elif active_page == "RFQ":
    active_subtab_rfq = query_params.get("subtab", "Customers")
    render_rfq_page(conn, active_subtab_rfq)

conn.close()
