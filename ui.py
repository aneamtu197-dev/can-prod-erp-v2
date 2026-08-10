import streamlit as st
from datetime import datetime

def load_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        [data-testid="stSidebar"] { display: none; }

        .top-header { background: linear-gradient(135deg, #0284c7 0%, #06b6d4 100%); color: #ffffff; padding: 12px 24px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(14, 165, 233, 0.2); }
        .top-header h3 { margin: 0; font-size: 20px; font-weight: 800; color: #ffffff; }

        .mrp-nav-bar { display: flex; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 10px 16px; gap: 15px; align-items: center; margin-bottom: 25px; border-radius: 12px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.03); }
        .mrp-nav-item { color: #0369a1; font-size: 14px; font-weight: 800; text-decoration: none; padding: 10px 22px; border-radius: 8px; background: linear-gradient(180deg, #ffffff 0%, #e0f2fe 100%); border: 1px solid #38bdf8; box-shadow: 0 4px 0 #0284c7, 0 5px 8px rgba(0, 0, 0, 0.12); transition: all 0.15s ease-in-out; display: inline-block; }
        .mrp-nav-item:hover { background: linear-gradient(180deg, #ffffff 0%, #bae6fd 100%); transform: translateY(-2px); box-shadow: 0 6px 0 #0284c7, 0 8px 12px rgba(14, 165, 233, 0.25); color: #0284c7; }
        .mrp-nav-active { background: linear-gradient(180deg, #0284c7 0%, #0369a1 100%) !important; color: #ffffff !important; border: 1px solid #0284c7 !important; box-shadow: 0 4px 0 #075985, 0 6px 10px rgba(2, 132, 199, 0.3) !important; }

        .mrp-subtabs { display: flex; gap: 12px; padding-bottom: 12px; margin-bottom: 25px; border-bottom: 2px solid #e2e8f0; }
        .mrp-subtab { color: #475569; font-size: 13px; font-weight: 700; text-decoration: none; padding: 8px 18px; border-radius: 8px; background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%); border: 1px solid #cbd5e1; box-shadow: 0 3px 0 #94a3b8, 0 4px 6px rgba(0,0,0,0.06); transition: all 0.15s ease; }
        .mrp-subtab:hover { background: linear-gradient(180deg, #ffffff 0%, #e2e8f0 100%); transform: translateY(-1px); box-shadow: 0 4px 0 #94a3b8, 0 5px 8px rgba(0,0,0,0.1); color: #0f172a; }
        .mrp-subtab-active { background: linear-gradient(180deg, #0ea5e9 0%, #0284c7 100%) !important; color: #ffffff !important; border: 1px solid #0284c7 !important; box-shadow: 0 3px 0 #0369a1, 0 4px 8px rgba(14, 165, 233, 0.25) !important; }

        .stock-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .stock-kpi-card { background: #ffffff; border-radius: 10px; padding: 14px 18px; border: 1px solid #e2e8f0; border-left: 5px solid #0284c7; box-shadow: 0 3px 6px rgba(0,0,0,0.04); display: flex; justify-content: space-between; align-items: center; }
        .stock-kpi-card-warning { border-left-color: #ef4444 !important; background: #fef2f2 !important; }
        .stock-kpi-val { font-size: 22px; font-weight: 800; color: #0f172a; margin: 0; }
        .stock-kpi-lbl { font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase; }

        .filter-panel { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px 10px 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03); }
        .launchpad-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 10px; }
        .launchpad-card { background-color: #ffffff; border: 1px solid #e2e8f0; border-top: 5px solid #0ea5e9; border-radius: 12px; padding: 26px 20px; text-align: center; text-decoration: none; transition: all 0.2s ease-in-out; box-shadow: 0 4px 0 #cbd5e1, 0 6px 10px rgba(0,0,0,0.05); }
        .launchpad-card:hover { transform: translateY(-4px); box-shadow: 0 8px 0 #0284c7, 0 12px 20px rgba(14, 165, 233, 0.2); border-top-color: #06b6d4; }
        .launchpad-icon { font-size: 36px; margin-bottom: 12px; }
        .launchpad-title { font-size: 16px; font-weight: 800; color: #0f172a; margin-bottom: 6px; }
        .launchpad-desc { font-size: 12px; color: #64748b; line-height: 1.4; }
    </style>
    """, unsafe_allow_html=True)

def render_top_header():
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    st.markdown(f"""
    <div class="top-header">
        <div><h3>CAN PROD &nbsp;|&nbsp; Custom ERP System</h3></div>
        <div style="font-size: 12px; font-weight: 600; opacity: 0.95;">
            🌐 ROU &nbsp;|&nbsp; 👤 Admin &nbsp;|&nbsp; ⏱️ {now_str}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_nav_bar(active_page):
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
