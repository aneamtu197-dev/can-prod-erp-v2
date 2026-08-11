import streamlit as st
import pandas as pd

from dialogs_utils import (
    reset_bom_filters_callback, get_selected_ids,
    bulk_delete_boms_dialog, bulk_delete_operations_dialog, bulk_delete_facilities_dialog
)
from dialogs_bom import (
    create_finished_product_dialog, manage_product_bom_dialog,
    add_facility_dialog, edit_facility_dialog,
    add_operation_dialog, edit_operation_dialog
)

def render_bom_page(conn, active_subtab_bom):
    subtabs_bom_html = '<div class="mrp-subtabs">'
    for t_k, t_l in [("Product", "📦 Product Recipes"), ("Operations", "⚙️ Operations"), ("Facilities", "🏢 Production Facilities"), ("Outsourcing", "🚚 Subcontracting"), ("BOM_Recipes", "📑 BOM Recipes"), ("Routing", "🔀 Routing")]:
        subtabs_bom_html += f'<a href="?page=BOM&subtab={t_k}" target="_self" class="{"mrp-subtab-active" if active_subtab_bom == t_k else "mrp-subtab"}">{t_l}</a>'
    st.markdown(subtabs_bom_html + '</div>', unsafe_allow_html=True)
    
    if st.session_state.get("keep_bom_dialog_open") and "active_bom_dialog_prod_id" in st.session_state:
        manage_product_bom_dialog(st.session_state["active_bom_dialog_prod_id"])

    if active_subtab_bom == "Product":
        c_head, c_btn1, c_btn2 = st.columns([6, 2, 2])
        with c_head: st.markdown("##### Product BOM Recipes & Manufacturing Cost Calculations")
        with c_btn1:
            if st.button("➕ Create Finished Product", type="primary", use_container_width=True): create_finished_product_dialog()
        with c_btn2:
            if st.button("🛠️ Edit Recipe / Routing", use_container_width=True): manage_product_bom_dialog()
            
        st.write("")
        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_b1, col_b2, col_b3, col_b4 = st.columns([3, 4, 3, 2])
        f_bom_code = col_b1.text_input("Product Code", key="f_bom_code")
        f_bom_name = col_b2.text_input("Product Name", key="f_bom_name")
        df_cust_list = pd.read_sql_query("SELECT name FROM customers ORDER BY name", conn)
        cust_opts = ["All Customers", "General / Stock Product"] + df_cust_list['name'].tolist()
        f_bom_cust = col_b3.selectbox("Customer", cust_opts, key="f_bom_cust")
        col_b4.write(""); col_b4.write(""); col_b4.button("🔄 Reset Filters", use_container_width=True, on_click=reset_bom_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_boms_clean = """
            SELECT b.id as ID, si.uniq_code as "Product Code", si.name as "Product Name", COALESCE(c.name, 'General / Stock Product') as "Customer", COALESCE(b.calculated_weight, 0.0) as "Weight (kg)", b.total_material_cost as "Material Cost (€)", b.total_labor_cost as "Operations Cost (€)", b.total_production_cost as "Total BOM Cost (€)"
            FROM product_boms b JOIN stock_items si ON b.product_item_id = si.id LEFT JOIN customers c ON b.customer_id = c.id WHERE 1=1
        """
        params_b = []
        if f_bom_code: q_boms_clean += " AND si.uniq_code LIKE %s"; params_b.append(f"%{f_bom_code}%")
        if f_bom_name: q_boms_clean += " AND si.name LIKE %s"; params.append(f"%{f_bom_name}%")
        if f_bom_cust != "All Customers":
            if f_bom_cust == "General / Stock Product": q_boms_clean += " AND c.name IS NULL"
            else: q_boms_clean += " AND c.name = %s"; params_b.append(f_bom_cust)

        q_boms_clean += " ORDER BY si.name"
        df_boms = pd.read_sql_query(q_boms_clean, conn, params=params_b if params_b else None)
        
        sel_boms = st.dataframe(df_boms, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_boms", column_config={"ID": None, "Weight (kg)": st.column_config.NumberColumn("Weight (kg)", format="%.2f kg"), "Material Cost (€)": st.column_config.NumberColumn("Material Cost (€)", format="%.2f €"), "Operations Cost (€)": st.column_config.NumberColumn("Operations Cost (€)", format="%.2f €"), "Total BOM Cost (€)": st.column_config.NumberColumn("Total BOM Cost (€)", format="%.2f €")})
        
        if sel_boms and len(sel_boms.selection.rows) > 0:
            selected_ids = get_selected_ids(df_boms, sel_boms.selection.rows)
            if selected_ids:
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1:
                        cursor_page = conn.cursor()
                        cursor_page.execute("SELECT product_item_id FROM product_boms WHERE id = %s", (selected_ids[0],))
                        p_row = cursor_page.fetchone()
                        if p_row and st.button("✏️ Edit Selected Recipe", use_container_width=True): 
                            st.session_state["active_bom_dialog_prod_id"] = p_row[0]
                            st.session_state["keep_bom_dialog_open"] = True
                            st.rerun()
                with col_a2:
                    if st.button("🗑️ Delete Selected Recipe", use_container_width=True): bulk_delete_boms_dialog(selected_ids)

    elif active_subtab_bom == "Operations":
        c_head, c_btn = st.columns([8, 2])
        with c_head: st.markdown("##### Manufacturing Operations & Process Rates")
        with c_btn:
            if st.button("➕ Add Operation", type="primary", use_container_width=True): add_operation_dialog()
            
        st.write("")
        q_op = """SELECT o.id as ID, o.uniq_code as "Uniq Code", o.name as "Operation Name", CASE WHEN o.is_outsourced = 1 THEN '🚚 OUTSOURCED (' || COALESCE(s.name, 'No Supplier') || ')' ELSE COALESCE(f.name, 'Internal Machine') END as "Execution Facility / Supplier", o.cost_unit as "Cost Unit", o.rate_per_unit as "Rate (€)", CASE WHEN o.is_outsourced = 1 THEN '-' ELSE CAST(o.productivity_level AS TEXT) END as "Productivity", CASE WHEN o.is_outsourced = 1 THEN '-' ELSE CAST(o.operators_count AS TEXT) END as "Operators", CASE WHEN o.is_outsourced = 1 THEN '-' ELSE CAST(o.max_hours_day AS TEXT) END as "Max Hrs/Day" FROM operations o LEFT JOIN production_facilities f ON o.facility_id = f.id LEFT JOIN suppliers s ON o.preferred_supplier_id = s.id ORDER BY o.uniq_code"""
        df_op = pd.read_sql_query(q_op, conn)
        sel_op = st.dataframe(df_op, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_op", column_config={"ID": None, "Rate (€)": st.column_config.NumberColumn("Rate (€)", format="%.2f €")})
        
        if sel_op and len(sel_op.selection.rows) > 0:
            selected_ids = get_selected_ids(df_op, sel_op.selection.rows)
            if selected_ids:
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1 and st.button("✏️ Edit Selected", use_container_width=True): edit_operation_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_operations_dialog(selected_ids)

    elif active_subtab_bom == "Facilities":
        c_head, c_btn = st.columns([8, 2])
        with c_head: st.markdown("##### Production Facilities & Equipment Inventory")
        with c_btn:
            if st.button("➕ Add Facility", type="primary", use_container_width=True): add_facility_dialog()
            
        st.write("")
        df_fac = pd.read_sql_query("SELECT id as ID, code as Code, name as \"Equipment Name\", facility_type as \"Type\", brand_model as \"Brand / Model\", status as \"Status\", next_maintenance_date as \"Next Maintenance\" FROM production_facilities ORDER BY code", conn)
        sel_fac = st.dataframe(df_fac, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_fac", column_config={"ID": None})
        if sel_fac and len(sel_fac.selection.rows) > 0:
            selected_ids = get_selected_ids(df_fac, sel_fac.selection.rows)
            if selected_ids:
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1 and st.button("✏️ Edit Selected", use_container_width=True): edit_facility_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_facilities_dialog(selected_ids)

    elif active_subtab_bom == "Outsourcing":
        st.markdown("##### 🚚 Subcontracting Management (Outsourced Operations)")
        st.caption("Centralizator al operațiunilor externe și comenzi către furnizorii de servicii (zincare, vopsire, strunjire, etc.).")
        q_sub = """SELECT o.uniq_code as "Op Code", o.name as "Operation Name", COALESCE(s.name, 'No Preferred Supplier') as "Subcontractor / Supplier", o.outsourcing_type as "Process Type", o.material_supplied_by as "Material Provision", o.cost_unit as "Billing Unit", o.rate_per_unit as "Estimated Rate (€)" FROM operations o LEFT JOIN suppliers s ON o.preferred_supplier_id = s.id WHERE o.is_outsourced = 1 ORDER BY o.uniq_code"""
        df_sub = pd.read_sql_query(q_sub, conn)
        if len(df_sub) > 0: st.dataframe(df_sub, use_container_width=True, hide_index=True, column_config={"Estimated Rate (€)": st.column_config.NumberColumn("Estimated Rate (€)", format="%.2f €")})
        else: st.info("No outsourced operations created yet. Toggle 'Is Subcontracted / Outsourced Operation?' when adding an Operation.")

    elif active_subtab_bom == "BOM_Recipes": st.info("BOM Recipes module configured.")
    elif active_subtab_bom == "Routing": st.info("Routing functionality configured.")
