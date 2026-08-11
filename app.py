import streamlit as st
import pandas as pd
from datetime import datetime

from db import init_custom_db, get_db, import_mrpeasy_items, import_mrpeasy_customers
from ui import load_css, render_top_header, render_nav_bar

# Importăm absolut toate funcțiile de tip "fereastră popup" și callback-urile din noul fișier
from dialogs import (
    reset_raw_filters_callback, reset_buy_filters_callback, reset_fg_filters_callback, reset_bom_filters_callback,
    get_selected_ids,
    bulk_delete_stock_dialog, bulk_delete_suppliers_dialog, bulk_delete_customers_dialog, 
    bulk_delete_facilities_dialog, bulk_delete_operations_dialog, bulk_delete_boms_dialog, bulk_delete_warehouses_dialog,
    add_warehouse_dialog, edit_warehouse_dialog,
    add_new_item_dialog, edit_item_dialog,
    add_supplier_dialog, edit_supplier_dialog,
    add_customer_dialog, edit_customer_dialog,
    create_finished_product_dialog, manage_product_bom_dialog,
    add_facility_dialog, edit_facility_dialog,
    add_operation_dialog, edit_operation_dialog
)

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
active_subtab = query_params.get("subtab", "Product")

# Render UI Headers
render_top_header()
render_nav_bar(active_page)

conn = get_db()

# Session State for Dynamic Dropdown Reset
if "bom_select_version" not in st.session_state:
    st.session_state["bom_select_version"] = 0

# ==========================================
# PAGE ROUTING
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
    subtabs_html = '<div class="mrp-subtabs">'
    for t_k, t_l in [("Raw_Materials", "📄 Raw Materials"), ("Buy_Parts", "⚙️ Buy Parts"), ("Finished_Goods", "🏆 Finished Goods"), ("Suppliers", "🚚 Suppliers"), ("Warehouses", "🏭 Warehouses"), ("Units", "📏 Units")]:
        subtabs_html += f'<a href="?page=Stock&subtab={t_k}" target="_self" class="{"mrp-subtab-active" if active_subtab == t_k else "mrp-subtab"}">{t_l}</a>'
    st.markdown(subtabs_html + '</div>', unsafe_allow_html=True)

    if active_subtab == "Raw_Materials" or active_subtab == "Items":
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
                        st.success(f"Added: {ins}, Updated: {upd}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Eroare la citirea CSV: {e}")

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
                st.info(f"☑️ Selected {len(selected_ids)} item(s)")
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1:
                        if st.button("✏️ Edit Selected", use_container_width=True): edit_item_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_stock_dialog(selected_ids)

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
                st.info(f"☑️ Selected {len(selected_ids)} item(s)")
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1:
                        if st.button("✏️ Edit Selected", use_container_width=True): edit_item_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_stock_dialog(selected_ids)

    elif active_subtab == "Finished_Goods":
        c_head, c_btn = st.columns([8, 2])
        with c_head: st.markdown("##### Finished Goods & Subassemblies Inventory")
        with c_btn:
            if st.button("➕ Create Product", type="primary", use_container_width=True):
                create_finished_product_dialog()
        st.write("")
        
        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_fg1, col_fg2, col_fg3, col_fg4 = st.columns([3, 4, 3, 2])
        f_fg_code = col_fg1.text_input("Product Code", key="f_fg_code")
        f_fg_name = col_fg2.text_input("Description", key="f_fg_name")
        f_fg_cat = col_fg3.selectbox("Category", ["All Categories", "FINISHED GOOD", "SUBASSEMBLY"], key="f_fg_cat")
        col_fg4.write(""); col_fg4.write(""); col_fg4.button("🔄 Reset", use_container_width=True, on_click=reset_fg_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_fin = """
            SELECT 
                si.id as ID, 
                si.uniq_code as "Uniq Code", 
                si.name as "Description", 
                si.category as "Category", 
                COALESCE(c.name, 'General / Stock') as "Assigned Customer",
                w.name as "Virtual Storage Location",
                u.code as "UoM", 
                si.specific_weight as "Weight (kg)",
                si.purchase_price as "BOM Cost (€)",
                si.selling_price as "Selling Price (€)",
                si.barcode as "Barcode"
            FROM stock_items si 
            LEFT JOIN units u ON si.unit_id = u.id 
            LEFT JOIN customers c ON si.customer_id = c.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE UPPER(si.category) IN ('FINISHED GOOD', 'SUBASSEMBLY', 'PRODUSE FINITE')
        """
        params = []
        if f_fg_code: q_fin += " AND (si.code LIKE %s OR si.uniq_code LIKE %s)"; params.extend([f"%{f_fg_code}%", f"%{f_fg_code}%"])
        if f_fg_name: q_fin += " AND si.name LIKE %s"; params.append(f"%{f_fg_name}%")
        if f_fg_cat != "All Categories": q_fin += " AND si.category = %s"; params.append(f_fg_cat)

        df_fin = pd.read_sql_query(q_fin, conn, params=params if params else None)
        sel = st.dataframe(df_fin, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_fin", 
                           column_config={
                               "BOM Cost (€)": st.column_config.NumberColumn("BOM Cost (€)", format="%.2f €"), 
                               "Selling Price (€)": st.column_config.NumberColumn("Selling Price (€)", format="%.2f €"),
                               "Weight (kg)": st.column_config.NumberColumn("Weight (kg)", format="%.2f kg")
                           })
        
        if sel and len(sel.selection.rows) > 0:
            selected_ids = get_selected_ids(df_fin, sel.selection.rows)
            if selected_ids:
                st.info(f"☑️ Selected {len(selected_ids)} item(s)")
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1:
                        if st.button("✏️ Edit Selected", use_container_width=True): edit_item_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_stock_dialog(selected_ids)

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
                st.info(f"☑️ Selected {len(selected_ids)} supplier(s)")
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1:
                        if st.button("✏️ Edit Selected", use_container_width=True): edit_supplier_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_suppliers_dialog(selected_ids)

    elif active_subtab == "Warehouses":
        c_head, c_btn1, c_btn2 = st.columns([5, 2, 3])
        with c_head: 
            st.markdown("##### Warehouses & Customer Virtual Storage")
        with c_btn1:
            if st.button("➕ Add Warehouse", type="primary", use_container_width=True): add_warehouse_dialog()
        with c_btn2:
            if st.button("🔄 Auto-Generare (Clienți)", type="primary", use_container_width=True):
                cursor_w = conn.cursor()
                cursor_w.execute("SELECT id, name FROM customers")
                all_customers = cursor_w.fetchall()
                
                created_count = 0
                for c_id, c_name in all_customers:
                    v_name = f"v_{c_name}"
                    unique_timestamp = int(datetime.now().timestamp() * 1000)
                    v_code = f"WH-V-{c_id}-{unique_timestamp}" 
                    
                    cursor_w.execute("SELECT id FROM warehouses WHERE customer_id = %s OR name = %s", (c_id, v_name))
                    if not cursor_w.fetchone():
                        cursor_w.execute(
                            "INSERT INTO warehouses (code, name, location_type, customer_id) VALUES (%s, %s, 'Customer Virtual Storage', %s)", 
                            (v_code, v_name, c_id)
                        )
                        created_count += 1
                        
                conn.commit()
                if created_count > 0:
                    st.success(f"🎉 S-au creat {created_count} depozite virtuale noi!")
                else:
                    st.info("Toți clienții au deja depozite virtuale alocate.")
                st.rerun()

        df_w = pd.read_sql_query("SELECT w.id as ID, w.code as \"Code\", w.name as \"Warehouse Name\", w.location_type as Type, COALESCE(c.name, 'Internal') as \"Owner Customer\" FROM warehouses w LEFT JOIN customers c ON w.customer_id = c.id ORDER BY w.name", conn)
        sel_wh = st.dataframe(df_w, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_wh", column_config={"ID": None})
        
        if sel_wh and len(sel_wh.selection.rows) > 0:
            selected_ids = get_selected_ids(df_w, sel_wh.selection.rows)
            if selected_ids:
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1:
                        if st.button("✏️ Edit Selected", use_container_width=True): edit_warehouse_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_warehouses_dialog(selected_ids)

    elif active_subtab == "Units":
        st.markdown("##### Units"); df_u = pd.read_sql_query("SELECT * FROM units", conn); st.dataframe(df_u, hide_index=True)

# ==========================================
# PRODUCTION & BOM MODULE
# ==========================================
elif active_page == "BOM":
    active_subtab_bom = query_params.get("subtab", "Product")
    
    subtabs_bom_html = '<div class="mrp-subtabs">'
    for t_k, t_l in [("Product", "📦 Product Recipes"), ("Operations", "⚙️ Operations"), ("Facilities", "🏢 Production Facilities"), ("Outsourcing", "🚚 Subcontracting"), ("BOM_Recipes", "📑 BOM Recipes"), ("Routing", "🔀 Routing")]:
        subtabs_bom_html += f'<a href="?page=BOM&subtab={t_k}" target="_self" class="{"mrp-subtab-active" if active_subtab_bom == t_k else "mrp-subtab"}">{t_l}</a>'
    st.markdown(subtabs_bom_html + '</div>', unsafe_allow_html=True)
    
    # Auto-reopen dialog if active
    if st.session_state.get("keep_bom_dialog_open") and "active_bom_dialog_prod_id" in st.session_state:
        manage_product_bom_dialog(st.session_state["active_bom_dialog_prod_id"])

    # --- PRODUCT RECIPES SUBTAB (FIRST TAB) ---
    if active_subtab_bom == "Product":
        c_head, c_btn1, c_btn2 = st.columns([6, 2, 2])
        with c_head: st.markdown("##### Product BOM Recipes & Manufacturing Cost Calculations")
        with c_btn1:
            if st.button("➕ Create Finished Product", type="primary", use_container_width=True):
                create_finished_product_dialog()
        with c_btn2:
            if st.button("🛠️ Edit Recipe / Routing", use_container_width=True): 
                manage_product_bom_dialog()
            
        st.write("")
        
        # FILTER PANEL FOR PRODUCT BOM RECIPES
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
            SELECT 
                b.id as ID,
                si.uniq_code as "Product Code",
                si.name as "Product Name",
                COALESCE(c.name, 'General / Stock Product') as "Customer",
                COALESCE(b.calculated_weight, 0.0) as "Weight (kg)",
                b.total_material_cost as "Material Cost (€)",
                b.total_labor_cost as "Operations Cost (€)",
                b.total_production_cost as "Total BOM Cost (€)"
            FROM product_boms b
            JOIN stock_items si ON b.product_item_id = si.id
            LEFT JOIN customers c ON b.customer_id = c.id
            WHERE 1=1
        """
        params_b = []
        if f_bom_code:
            q_boms_clean += " AND si.uniq_code LIKE %s"
            params_b.append(f"%{f_bom_code}%")
        if f_bom_name:
            q_boms_clean += " AND si.name LIKE %s"
            params_b.append(f"%{f_bom_name}%")
        if f_bom_cust != "All Customers":
            if f_bom_cust == "General / Stock Product":
                q_boms_clean += " AND c.name IS NULL"
            else:
                q_boms_clean += " AND c.name = %s"
                params_b.append(f_bom_cust)

        q_boms_clean += " ORDER BY si.name"

        df_boms = pd.read_sql_query(q_boms_clean, conn, params=params_b if params_b else None)
        
        sel_boms = st.dataframe(
            df_boms, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_boms",
            column_config={
                "ID": None,
                "Weight (kg)": st.column_config.NumberColumn("Weight (kg)", format="%.2f kg"),
                "Material Cost (€)": st.column_config.NumberColumn("Material Cost (€)", format="%.2f €"),
                "Operations Cost (€)": st.column_config.NumberColumn("Operations Cost (€)", format="%.2f €"),
                "Total BOM Cost (€)": st.column_config.NumberColumn("Total BOM Cost (€)", format="%.2f €")
            }
        )
        
        if sel_boms and len(sel_boms.selection.rows) > 0:
            selected_ids = get_selected_ids(df_boms, sel_boms.selection.rows)
            if selected_ids:
                st.info(f"☑️ Selected {len(selected_ids)} recipe(s)")
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
                    if st.button("🗑️ Delete Selected Recipe", use_container_width=True): 
                        bulk_delete_boms_dialog(selected_ids)

    # --- OPERATIONS SUBTAB ---
    elif active_subtab_bom == "Operations":
        c_head, c_btn = st.columns([8, 2])
        with c_head: st.markdown("##### Manufacturing Operations & Process Rates")
        with c_btn:
            if st.button("➕ Add Operation", type="primary", use_container_width=True): add_operation_dialog()
            
        st.write("")
        q_op = """
            SELECT 
                o.id as ID,
                o.uniq_code as "Uniq Code",
                o.name as "Operation Name",
                CASE 
                    WHEN o.is_outsourced = 1 THEN '🚚 OUTSOURCED (' || COALESCE(s.name, 'No Supplier') || ')'
                    ELSE COALESCE(f.name, 'Internal Machine')
                END as "Execution Facility / Supplier",
                o.cost_unit as "Cost Unit",
                o.rate_per_unit as "Rate (€)",
                CASE WHEN o.is_outsourced = 1 THEN '-' ELSE CAST(o.productivity_level AS TEXT) END as "Productivity",
                CASE WHEN o.is_outsourced = 1 THEN '-' ELSE CAST(o.operators_count AS TEXT) END as "Operators",
                CASE WHEN o.is_outsourced = 1 THEN '-' ELSE CAST(o.max_hours_day AS TEXT) END as "Max Hrs/Day"
            FROM operations o
            LEFT JOIN production_facilities f ON o.facility_id = f.id
            LEFT JOIN suppliers s ON o.preferred_supplier_id = s.id
            ORDER BY o.uniq_code
        """
        df_op = pd.read_sql_query(q_op, conn)
        sel_op = st.dataframe(
            df_op, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_op",
            column_config={
                "ID": None,
                "Rate (€)": st.column_config.NumberColumn("Rate (€)", format="%.2f €")
            }
        )
        
        if sel_op and len(sel_op.selection.rows) > 0:
            selected_ids = get_selected_ids(df_op, sel_op.selection.rows)
            if selected_ids:
                st.info(f"☑️ Selected {len(selected_ids)} operation(s)")
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1:
                        if st.button("✏️ Edit Selected", use_container_width=True): edit_operation_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_operations_dialog(selected_ids)

    # --- PRODUCTION FACILITIES SUBTAB ---
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
                st.info(f"☑️ Selected {len(selected_ids)} facility(ies)")
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1:
                        if st.button("✏️ Edit Selected", use_container_width=True): edit_facility_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_facilities_dialog(selected_ids)

    # --- SUBCONTRACTING / OUTSOURCING SUBTAB ---
    elif active_subtab_bom == "Outsourcing":
        st.markdown("##### 🚚 Subcontracting Management (Outsourced Operations)")
        st.caption("Centralizator al operațiunilor externe și comenzi către furnizorii de servicii (zincare, vopsire, strunjire, etc.).")
        
        q_sub = """
            SELECT 
                o.uniq_code as "Op Code",
                o.name as "Operation Name",
                COALESCE(s.name, 'No Preferred Supplier') as "Subcontractor / Supplier",
                o.outsourcing_type as "Process Type",
                o.material_supplied_by as "Material Provision",
                o.cost_unit as "Billing Unit",
                o.rate_per_unit as "Estimated Rate (€)"
            FROM operations o
            LEFT JOIN suppliers s ON o.preferred_supplier_id = s.id
            WHERE o.is_outsourced = 1
            ORDER BY o.uniq_code
        """
        df_sub = pd.read_sql_query(q_sub, conn)
        if len(df_sub) > 0:
            st.dataframe(df_sub, use_container_width=True, hide_index=True, column_config={"Estimated Rate (€)": st.column_config.NumberColumn("Estimated Rate (€)", format="%.2f €")})
        else:
            st.info("No outsourced operations created yet. Toggle 'Is Subcontracted / Outsourced Operation?' when adding an Operation.")

    elif active_subtab_bom == "BOM_Recipes":
        st.info("BOM Recipes module configured.")
    elif active_subtab_bom == "Routing":
        st.info("Routing functionality configured.")

# ==========================================
# RFQ & ORDERS MODULE
# ==========================================
elif active_page == "RFQ":
    active_subtab_rfq = query_params.get("subtab", "Customers")
    
    subtabs_rfq_html = '<div class="mrp-subtabs">'
    for t_k, t_l in [("Customers", "👥 Customers"), ("Quotations", "📄 Quotations"), ("Orders", "🛒 Sales Orders")]:
        subtabs_rfq_html += f'<a href="?page=RFQ&subtab={t_k}" target="_self" class="{"mrp-subtab-active" if active_subtab_rfq == t_k else "mrp-subtab"}">{t_l}</a>'
    st.markdown(subtabs_rfq_html + '</div>', unsafe_allow_html=True)
    
    # --- CUSTOMERS TAB ---
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
                        st.success(f"Added: {ins}, Updated: {upd}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Eroare la citirea CSV: {e}")
            
        st.write("")
        df_c = pd.read_sql_query("SELECT id as ID, code as Code, cui as \"CUI\", name as \"Customer Name\", reg_com as \"Reg. Com.\", contact_person as \"Contact Person\", phone as Phone, email as Email FROM customers ORDER BY name", conn)
        
        sel_cust = st.dataframe(df_c, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_cust", column_config={"ID": None})
        
        if sel_cust and len(sel_cust.selection.rows) > 0:
            selected_ids = get_selected_ids(df_c, sel_cust.selection.rows)
            if selected_ids:
                st.info(f"☑️ Selected {len(selected_ids)} customer(s)")
                col_a1, col_a2, _ = st.columns([2, 2, 8])
                with col_a1:
                    if len(selected_ids) == 1:
                        if st.button("✏️ Edit Selected", use_container_width=True): edit_customer_dialog(selected_ids[0])
                with col_a2:
                    if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_customers_dialog(selected_ids)
                
    elif active_subtab_rfq == "Quotations":
        st.info("Quotations functionality will be added here.")
    elif active_subtab_rfq == "Orders":
        st.info("Sales Orders functionality will be added here.")

conn.close()
