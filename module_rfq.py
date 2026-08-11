import streamlit as st
import pandas as pd

from db import import_mrpeasy_customers
from dialogs import (
    get_selected_ids, bulk_delete_customers_dialog,
    add_customer_dialog, edit_customer_dialog
)

def render_rfq_page(conn, active_subtab_rfq):
    subtabs_rfq_html = '<div class="mrp-subtabs">'
    for t_k, t_l in [("Customers", "👥 Customers"), ("Quotations", "📄 Quotations"), ("Orders", "🛒 Sales Orders")]:
        subtabs_rfq_html += f'<a href="?page=RFQ&subtab={t_k}" target="_self" class="{"mrp-subtab-active" if active_subtab_rfq == t_k else "mrp-subtab"}">{t_l}</a>'
    st.markdown(subtabs_rfq_html + '</div>', unsafe_allow_html=True)
    
    if active_subtab_rfq == "Customers":
        c_head, c_btn1, c_btn2 = st.columns([6, 2, 2])
        with c_head: st.markdown("##### Customer Database")
        with c_btn1:
            if st.button("➕ Add Customer", type="primary", use_container_width=True): add_customer_dialog()
        with c_btn2:
            with st.popover("↑ Import CSV", use_container_width=True):
                csv_file = st.file_uploader("Upload Customers CSV", type=['csv'], key="upload_cust_csv")
                if csv_file and st.button("Execute Import", key="exec_cust_imp"):
                    try:
                        df_upload = pd.read_csv(csv_file, sep=None, engine='python')
                        ins, upd = import_mrpeasy_customers(df_upload)
                        st.success(f"Added: {ins}, Updated: {upd}"); st.rerun()
                    except Exception as e: st.error(f"Eroare la citirea CSV: {e}")
            
        st.write("")
        df_c = pd.read_sql_query("SELECT id as ID, code as Code, cui as \"CUI\", name as \"Customer Name\", reg_com as \"Reg. Com.\", contact_person as \"Contact Person\", phone as Phone, email as Email FROM customers ORDER BY name", conn)
        sel_cust = st.dataframe(df_c, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_cust", column_config={"ID": None})
        
        if sel_cust and len(sel_cust.selection.rows) > 0:
            selected_ids = get_selected_ids(df_c, sel_cust.selection.rows)
            if selected_ids:
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1 and st.button("✏️ Edit Selected", use_container_width=True): edit_customer_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_customers_dialog(selected_ids)
                
    elif active_subtab_rfq == "Quotations":
        st.info("Quotations functionality will be added here.")
    elif active_subtab_rfq == "Orders":
        st.info("Sales Orders functionality will be added here.")
