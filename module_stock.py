import streamlit as st
import pandas as pd
from datetime import datetime

from db import import_mrpeasy_items
from dialogs_utils import (
    reset_raw_filters_callback, reset_buy_filters_callback, reset_fg_filters_callback,
    get_selected_ids, bulk_delete_stock_dialog, bulk_delete_suppliers_dialog, bulk_delete_warehouses_dialog
)
from dialogs_stock import add_new_item_dialog, edit_item_dialog, add_warehouse_dialog, edit_warehouse_dialog
from dialogs_partners import add_supplier_dialog, edit_supplier_dialog
from dialogs_bom import create_finished_product_dialog

def render_stock_page(conn, active_subtab):
    if active_subtab == "Items": active_subtab = "Raw_Materials"
    
    subtabs_html = '<div class="mrp-subtabs">'
    for t_k, t_l in [("Raw_Materials", "📄 Raw Materials"), ("Buy_Parts", "⚙️ Buy Parts"), ("Finished_Goods", "🏆 Finished Goods"), ("Suppliers", "🚚 Suppliers"), ("Warehouses", "🏭 Warehouses"), ("Units", "📏 Units")]:
        subtabs_html += f'<a href="?page=Stock&subtab={t_k}" target="_self" class="{"mrp-subtab-active" if active_subtab == t_k else "mrp-subtab"}">{t_l}</a>'
    st.markdown(subtabs_html + '</div>', unsafe_allow_html=True)

    if active_subtab == "Raw_Materials":
        c1, c2, c3 = st.columns([6, 2, 2])
        with c1: st.markdown("##### Raw Materials Inventory")
        with c2: 
            if st.button("➕ Add Item", use_container_width=True, type="primary"): add_new_item_dialog("Raw Material")
        with c3:
            with st.popover("↑ Import CSV", use_container_width=True):
                csv_file = st.file_uploader("Upload CSV", type=['csv'])
                if csv_file and st.button("Execute Import"):
                    try:
                        df_upload = pd.read_csv(csv_file, sep=None, engine='python')
                        ins, upd = import_mrpeasy_items(df_upload)
                        st.success(f"Added: {ins}, Updated: {upd}"); st.rerun()
                    except Exception as e: st.error(f"Eroare: {e}")

        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns([2, 3, 2, 2, 1.5, 1.5])
        f_raw_code = col_f1.text_input("Part No. / Uniq Code", key="f_raw_code")
        f_raw_name = col_f2.text_input("Part Description", key="f_raw_name")
        f_raw_sub = col_f3.selectbox("Sub-Group", ["All Sub-Groups", "Tabla", "Teava", "Europrofile", "Raw Materials Diverse"], key="f_raw_sub")
        df_raw_supp = pd.read_sql_query("SELECT DISTINCT s.name FROM stock_items si JOIN suppliers s ON si.supplier_id=s.id WHERE UPPER(si.category) IN ('RAW MATERIAL', 'MATERIE PRIMA')", conn)
        f_raw_supp = col_f4.selectbox("Supplier", ["All Suppliers"] + df_raw_supp['name'].tolist(), key="f_raw_supp")
        df_raw_uom = pd.read_sql_query("SELECT DISTINCT u.code FROM stock_items si JOIN units u ON si.unit_id=u.id WHERE UPPER(si.category) IN ('RAW MATERIAL', 'MATERIE PRIMA')", conn)
        f_raw_uom = col_f5.selectbox("UoM", ["All UoMs"] + df_raw_uom['code'].tolist(), key="f_raw_uom")
        col_f6.write(""); col_f6.write(""); col_f6.button("🔄 Reset Filters", use_container_width=True, on_click=reset_raw_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_raw = "SELECT si.id as ID, si.uniq_code as \"Uniq Code\", si.code as \"Part No.\", si.name as \"Description\", si.sub_group as \"Sub-Group\", s.name as \"Supplier\", u.code as \"UoM\", si.specific_weight as \"Spec. Weight\", si.purchase_price as \"Purchase Price (€)\" FROM stock_items si LEFT JOIN suppliers s ON si.supplier_id = s.id LEFT JOIN units u ON si.unit_id = u.id WHERE UPPER(si.category) IN ('RAW MATERIAL', 'MATERIE PRIMA', 'RAW MATERIALS')"
        params = []
        if f_raw_code: q_raw += " AND (si.code LIKE %s OR si.uniq_code LIKE %s)"; params.extend([f"%{f_raw_code}%", f"%{f_raw_code}%"])
        if f_raw_name: q_raw += " AND si.name LIKE %s"; params.append(f"%{f_raw_name}%")
        if f_raw_sub != "All Sub-Groups": q_raw += " AND si.sub_group = %s"; params.append(f_raw_sub)
        if f_raw_supp != "All Suppliers": q_raw += " AND s.name = %s"; params.append(f_raw_supp)
        if f_raw_uom != "All UoMs": q_raw += " AND u.code = %s"; params.append(f_raw_uom)
        
        df_raw = pd.read_sql_query(q_raw, conn, params=params if params else None)
        sel = st.dataframe(df_raw, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_raw")
        if sel and len(sel.selection.rows) > 0:
            selected_ids = get_selected_ids(df_raw, sel.selection.rows)
            if selected_ids:
                c_btn_action, _ = st.columns([3, 7])
                with c_btn_action:
                    if len(selected_ids) == 1:
                        if st.button("⚙️ Gestionează Material Selectat", use_container_width=True): edit_item_dialog(selected_ids[0])
                    else:
                        if st.button("🗑️ Ștergere Multiplă (Bulk Delete)", use_container_width=True): bulk_delete_stock_dialog(selected_ids)

    elif active_subtab == "Buy_Parts":
        st.markdown("##### Purchased Parts & Fasteners")
        if st.button("➕ Add Item", type="primary"): add_new_item_dialog("Buy Part")
        st.write("")

        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_b1, col_b2, col_b3, col_b4 = st.columns([3, 4, 3, 2])
        f_buy_code = col_b1.text_input("Part No.", key="f_buy_code")
        f_buy_name = col_b2.text_input("Description", key="f_buy_name")
        df_buy_supp = pd.read_sql_query("SELECT DISTINCT s.name FROM stock_items si JOIN suppliers s ON si.supplier_id=s.id WHERE UPPER(si.category) IN ('BUY PART', 'BUY PARTS')", conn)
        f_buy_supp = col_b3.selectbox("Supplier", ["All Suppliers"] + df_buy_supp['name'].tolist(), key="f_buy_supp")
        col_b4.write(""); col_b4.write(""); col_b4.button("🔄 Reset", use_container_width=True, on_click=reset_buy_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_buy = "SELECT si.id as ID, si.uniq_code as \"Uniq Code\", si.code as \"Part No.\", si.name as \"Description\", s.name as \"Supplier\", u.code as \"UoM\", si.purchase_price as \"Purchase Price (€)\" FROM stock_items si LEFT JOIN suppliers s ON si.supplier_id = s.id LEFT JOIN units u ON si.unit_id = u.id WHERE UPPER(si.category) IN ('BUY PART', 'BUY PARTS')"
        params = []
        if f_buy_code: q_buy += " AND (si.code LIKE %s OR si.uniq_code LIKE %s)"; params.extend([f"%{f_buy_code}%", f"%{f_buy_code}%"])
        if f_buy_name: q_buy += " AND si.name LIKE %s"; params.append(f"%{f_buy_name}%")
        if f_buy_supp != "All Suppliers": q_buy += " AND s.name = %s"; params.append(f_buy_supp)
        
        df_buy = pd.read_sql_query(q_buy, conn, params=params if params else None)
        sel = st.dataframe(df_buy, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_buy")
        if sel and len(sel.selection.rows) > 0:
            selected_ids = get_selected_ids(df_buy, sel.selection.rows)
            if selected_ids:
                c_btn_action, _ = st.columns([3, 7])
                with c_btn_action:
                    if len(selected_ids) == 1:
                        if st.button("⚙️ Gestionează Articol Selectat", use_container_width=True): edit_item_dialog(selected_ids[0])
                    else:
                        if st.button("🗑️ Ștergere Multiplă (Bulk Delete)", use_container_width=True): bulk_delete_stock_dialog(selected_ids)

    elif active_subtab == "Finished_Goods":
        c_head, c_btn = st.columns([8, 2])
        with c_head: st.markdown("##### Finished Goods & Subassemblies Inventory")
        with c_btn:
            if st.button("➕ Create Product", type="primary", use_container_width=True): create_finished_product_dialog()
        st.write("")
        
        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_fg1, col_fg2, col_fg3, col_fg4 = st.columns([3, 4, 3, 2])
        f_fg_code = col_fg1.text_input("Product Code", key="f_fg_code")
        f_fg_name = col_fg2.text_input("Description", key="f_fg_name")
        f_fg_cat = col_fg3.selectbox("Category", ["All Categories", "FINISHED GOOD", "SUBASSEMBLY"], key="f_fg_cat")
        col_fg4.write(""); col_fg4.write(""); col_fg4.button("🔄 Reset", use_container_width=True, on_click=reset_fg_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_fin = """SELECT si.id as ID, si.uniq_code as "Uniq Code", si.name as "Description", si.category as "Category", COALESCE(c.name, 'General / Stock') as "Assigned Customer", w.name as "Virtual Storage Location", u.code as "UoM", si.specific_weight as "Weight (kg)", si.purchase_price as "BOM Cost (€)", si.selling_price as "Selling Price (€)", si.barcode as "Barcode" FROM stock_items si LEFT JOIN units u ON si.unit_id = u.id LEFT JOIN customers c ON si.customer_id = c.id LEFT JOIN warehouses w ON si.warehouse_id = w.id WHERE UPPER(si.category) IN ('FINISHED GOOD', 'SUBASSEMBLY', 'PRODUSE FINITE')"""
        params = []
        if f_fg_code: q_fin += " AND (si.code LIKE %s OR si.uniq_code LIKE %s)"; params.extend([f"%{f_fg_code}%", f"%{f_fg_code}%"])
        if f_fg_name: q_fin += " AND si.name LIKE %s"; params.append(f"%{f_fg_name}%")
        if f_fg_cat != "All Categories": q_fin += " AND si.category = %s"; params.append(f_fg_cat)

        df_fin = pd.read_sql_query(q_fin, conn, params=params if params else None)
        sel = st.dataframe(df_fin, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_fin", column_config={"BOM Cost (€)": st.column_config.NumberColumn("BOM Cost (€)", format="%.2f €"), "Selling Price (€)": st.column_config.NumberColumn("Selling Price (€)", format="%.2f €"), "Weight (kg)": st.column_config.NumberColumn("Weight (kg)", format="%.2f kg")})
        
        if sel and len(sel.selection.rows) > 0:
            selected_ids = get_selected_ids(df_fin, sel.selection.rows)
            if selected_ids:
                c_btn_action, _ = st.columns([3, 7])
                with c_btn_action:
                    if len(selected_ids) == 1:
                        if st.button("⚙️ Gestionează Produs Selectat", use_container_width=True): edit_item_dialog(selected_ids[0])
                    else:
                        if st.button("🗑️ Ștergere Multiplă (Bulk Delete)", use_container_width=True): bulk_delete_stock_dialog(selected_ids)

    elif active_subtab == "Suppliers":
        c_head, c_btn = st.columns([8, 2])
        with c_head: st.markdown("##### Supplier Management")
        with c_btn:
            if st.button("➕ Add Supplier", type="primary", use_container_width=True): add_supplier_dialog()
        
        st.write("")
        df_s = pd.read_sql_query("SELECT id as ID, code as Code, cui as \"CUI\", name as \"Supplier Name\", supplier_type as \"Supplier Type\", contact_person as \"Contact Person\", phone as Phone, email as Email, lead_time_days as \"Lead Time (Days)\" FROM suppliers ORDER BY name", conn)
        sel_supp = st.dataframe(df_s, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_supp", column_config={"ID": None})
        if sel_supp and len(sel_supp.selection.rows) > 0:
            selected_ids = get_selected_ids(df_s, sel_supp.selection.rows)
            if selected_ids:
                c_btn_action, _ = st.columns([3, 7])
                with c_btn_action:
                    if len(selected_ids) == 1:
                        if st.button("⚙️ Gestionează Furnizor Selectat", use_container_width=True): edit_supplier_dialog(selected_ids[0])
                    else:
                        if st.button("🗑️ Ștergere Multiplă (Bulk Delete)", use_container_width=True): bulk_delete_suppliers_dialog(selected_ids)

    elif active_subtab == "Warehouses":
        c_head, c_btn1, c_btn2 = st.columns([5, 2, 3])
        with c_head: st.markdown("##### Warehouses & Customer Virtual Storage")
        with c_btn1:
            if st.button("➕ Add Warehouse", type="primary", use_container_width=True): add_warehouse_dialog()
        with c_btn2:
            if st.button("🔄 Auto-Generare (Clienți)", type="primary", use_container_width=True):
                cursor_w = conn.cursor()
                cursor_w.execute("SELECT id, name FROM customers")
                created_count = 0
                for c_id, c_name in cursor_w.fetchall():
                    v_name = f"v_{c_name}"
                    unique_timestamp = int(datetime.now().timestamp() * 1000)
                    v_code = f"WH-V-{c_id}-{unique_timestamp}" 
                    cursor_w.execute("SELECT id FROM warehouses WHERE customer_id = %s OR name = %s", (c_id, v_name))
                    if not cursor_w.fetchone():
                        cursor_w.execute("INSERT INTO warehouses (code, name, location_type, customer_id) VALUES (%s, %s, 'Customer Virtual Storage', %s)", (v_code, v_name, c_id))
                        created_count += 1
                conn.commit()
                if created_count > 0: st.success(f"🎉 S-au creat {created_count} depozite virtuale noi!")
                else: st.info("Toți clienții au deja depozite virtuale alocate.")
                st.rerun()

        df_w = pd.read_sql_query("SELECT w.id as ID, w.code as \"Code\", w.name as \"Warehouse Name\", w.location_type as Type, COALESCE(c.name, 'Internal') as \"Owner Customer\" FROM warehouses w LEFT JOIN customers c ON w.customer_id = c.id ORDER BY w.name", conn)
        sel_wh = st.dataframe(df_w, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_wh", column_config={"ID": None})
        if sel_wh and len(sel_wh.selection.rows) > 0:
            selected_ids = get_selected_ids(df_w, sel_wh.selection.rows)
            if selected_ids:
                c_btn_action, _ = st.columns([3, 7])
                with c_btn_action:
                    if len(selected_ids) == 1:
                        if st.button("⚙️ Gestionează Depozit Selectat", use_container_width=True): edit_warehouse_dialog(selected_ids[0])
                    else:
                        if st.button("🗑️ Ștergere Multiplă (Bulk Delete)", use_container_width=True): bulk_delete_warehouses_dialog(selected_ids)

    elif active_subtab == "Units":
        st.markdown("##### Units"); df_u = pd.read_sql_query("SELECT * FROM units", conn); st.dataframe(df_u, hide_index=True)
