import streamlit as st
import pandas as pd
from db import init_custom_db, get_db, generate_unique_item_code, import_mrpeasy_items, safe_float
from ui import load_css, render_top_header, render_nav_bar

st.set_page_config(page_title="CAN Prod ERP Custom", layout="wide", initial_sidebar_state="collapsed")

# Initialize DB & Load CSS
init_custom_db()
load_css()

query_params = st.query_params
active_page = query_params.get("page", "Home")
active_subtab = query_params.get("subtab", "Raw_Materials")

# Render UI Headers
render_top_header()
render_nav_bar(active_page)

conn = get_db()

# Callback Functions for Filters
def reset_raw_filters_callback():
    for k in ["f_raw_code", "f_raw_name", "f_raw_sub", "f_raw_supp", "f_raw_uom"]: st.session_state[k] = "All Sub-Groups" if "sub" in k else ("All Suppliers" if "supp" in k else ("All UoMs" if "uom" in k else ""))

def reset_buy_filters_callback():
    for k in ["f_buy_code", "f_buy_name", "f_buy_supp"]: st.session_state[k] = "All Suppliers" if "supp" in k else ""

def reset_fg_filters_callback():
    for k in ["f_fg_code", "f_fg_name", "f_fg_cat"]: st.session_state[k] = "All Categories" if "cat" in k else ""

# DIALOG MODAL FOR BULK DELETE STOCK ITEMS
@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_stock_dialog(item_ids):
    st.error(f"Are you sure you want to delete {len(item_ids)} item(s)? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True):
        st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(item_ids))
        cursor.execute(f"DELETE FROM stock_items WHERE id IN ({placeholders})", item_ids)
        conn.commit()
        st.success("Items deleted successfully!")
        st.rerun()

# DIALOG MODAL FOR BULK DELETE SUPPLIERS
@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_suppliers_dialog(item_ids):
    st.error(f"Are you sure you want to delete {len(item_ids)} supplier(s)? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True):
        st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(item_ids))
        cursor.execute(f"DELETE FROM suppliers WHERE id IN ({placeholders})", item_ids)
        conn.commit()
        st.success("Suppliers deleted successfully!")
        st.rerun()

# DIALOG MODAL POP-UP FOR ADDING STOCK ITEMS
@st.dialog("➕ Add New Item to Stock")
def add_new_item_dialog(default_type="Raw Material"):
    conn_dialog = get_db()
    st.subheader("Step 1: Select Item Type & Category")
    
    types = ["Raw Material", "Buy Part", "Finished Good / Subassembly"]
    idx = types.index(default_type) if default_type in types else 0
    item_type = st.selectbox("Item Type *", types, index=idx)
    
    if item_type == "Raw Material":
        sub_group = st.selectbox("Main Sub-Group *", ["Tabla", "Teava", "Europrofile", "Raw Materials Diverse"])
        auto_uniq = generate_unique_item_code(conn_dialog, "RAW MATERIAL", sub_group)
        category = "RAW MATERIAL"
    elif item_type == "Buy Part":
        sub_group = "Buy Parts"
        auto_uniq = generate_unique_item_code(conn_dialog, "BUY PART")
        category = "BUY PART"
    else:
        sub_group = "Finished Goods"
        auto_uniq = generate_unique_item_code(conn_dialog, "FINISHED GOOD")
        category = st.selectbox("Category *", ["FINISHED GOOD", "SUBASSEMBLY"])

    with st.form("add_item_dynamic_form"):
        st.subheader("Step 2: Item Characteristics")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Uniq Code (Auto-Generated) *", value=auto_uniq, disabled=True)
            code = st.text_input("Part No. / Original Code *", value=auto_uniq)
            name = st.text_input("Part Description / Name *")
            df_u_opts = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn_dialog)
            u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u_opts.iterrows()}
            selected_u = st.selectbox("Unit of Measure (UoM) *", list(u_dict.keys()))
            if item_type != "Finished Good / Subassembly":
                df_s_opts = pd.read_sql_query("SELECT id, name FROM suppliers ORDER BY name", conn_dialog)
                s_dict = {r['name']: r['id'] for _, r in df_s_opts.iterrows()}
                selected_s = st.selectbox("Preferred Supplier", list(s_dict.keys()) if s_dict else ["No Supplier"])
            else:
                s_dict = {}; selected_s = None

        with col2:
            price = st.number_input("Purchase Price (€)", min_value=0.0) if item_type != "Finished Good / Subassembly" else 0.0
            selling_p = st.number_input("Selling Price (€)", min_value=0.0)
            col_w1, col_w2 = st.columns([2, 1])
            with col_w1: spec_weight = st.number_input("Specific Weight / Unit", min_value=0.0)
            with col_w2: w_unit = st.selectbox("Weight Unit", ["kg", "lbs", "g"])
            
            df_w_opts = pd.read_sql_query("SELECT id, name FROM warehouses ORDER BY name", conn_dialog)
            w_dict = {r['name']: r['id'] for _, r in df_w_opts.iterrows()}
            selected_w = st.selectbox("Storage Warehouse Location", list(w_dict.keys()))
            stock_qty = st.number_input("Initial Stock Quantity", min_value=0.0)
            min_stock_qty = st.number_input("Reorder Point / Min Stock", min_value=0.0)

        if st.form_submit_button("💾 Save Item", type="primary", use_container_width=True):
            if auto_uniq and name:
                conn_dialog.cursor().execute("""INSERT INTO stock_items (uniq_code, code, name, category, sub_group, supplier_id, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                                      (auto_uniq, code, name, category, sub_group, s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), price, selling_p, spec_weight, w_unit, stock_qty, min_stock_qty))
                conn_dialog.commit()
                st.success("Item saved!"); st.rerun()

# DIALOG MODAL POP-UP FOR EDITING STOCK ITEMS
@st.dialog("✏️ Edit Item Details")
def edit_item_dialog(item_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT uniq_code, code, name, category, sub_group, supplier_id, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock FROM stock_items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    
    if row:
        with st.form("edit_item_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Uniq Code (Read-Only) *", value=row[0], disabled=True)
                e_code = st.text_input("Part No. / Original Code *", value=row[1])
                e_name = st.text_input("Part Description / Name *", value=row[2])
                e_sub = st.selectbox("Sub-Group *", ["Tabla", "Teava", "Europrofile", "Raw Materials Diverse"]) if row[3] == "RAW MATERIAL" else row[4]
                
                df_u_opts = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn_dialog)
                u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u_opts.iterrows()}; u_keys = list(u_dict.keys())
                u_index = [idx for idx, k in enumerate(u_keys) if u_dict[k] == row[6]]
                selected_u = st.selectbox("Unit of Measure (UoM)", u_keys, index=u_index[0] if u_index else 0)

                df_s_opts = pd.read_sql_query("SELECT id, name FROM suppliers ORDER BY name", conn_dialog)
                s_dict = {r['name']: r['id'] for _, r in df_s_opts.iterrows()}; s_keys = ["No Supplier"] + list(s_dict.keys())
                s_curr = [k for k, v in s_dict.items() if v == row[5]]
                selected_s = st.selectbox("Supplier", s_keys, index=s_keys.index(s_curr[0]) if s_curr else 0)

            with col2:
                e_pprice = st.number_input("Purchase Price (€)", value=safe_float(row[8]))
                e_sprice = st.number_input("Selling Price (€)", value=safe_float(row[9]))
                
                c_w1, c_w2 = st.columns([2, 1])
                with c_w1: e_sweight = st.number_input("Spec Weight/Unit", value=safe_float(row[10]))
                with c_w2: e_wunit = st.selectbox("Unit", ["kg", "lbs", "g"], index=["kg", "lbs", "g"].index(row[11] if row[11] else "kg"))

                df_w_opts = pd.read_sql_query("SELECT id, name FROM warehouses ORDER BY name", conn_dialog)
                w_dict = {r['name']: r['id'] for _, r in df_w_opts.iterrows()}; w_keys = list(w_dict.keys())
                w_curr = [k for k, v in w_dict.items() if v == row[7]]
                selected_w = st.selectbox("Warehouse", w_keys, index=w_keys.index(w_curr[0]) if w_curr else 0)

                e_stock = st.number_input("Current Stock", value=safe_float(row[12]))
                e_minstock = st.number_input("Reorder Point", value=safe_float(row[13]))

            c_save, c_del = st.columns([8, 2])
            if c_save.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                cursor.execute("""UPDATE stock_items SET code=?, name=?, sub_group=?, supplier_id=?, unit_id=?, warehouse_id=?, purchase_price=?, selling_price=?, specific_weight=?, weight_unit=?, current_stock=?, min_stock=? WHERE id=?""", 
                               (e_code, e_name, e_sub, s_dict.get(selected_s), u_dict.get(selected_u), w_dict.get(selected_w), e_pprice, e_sprice, e_sweight, e_wunit, e_stock, e_minstock, item_id))
                conn_dialog.commit(); st.success("Updated!"); st.rerun()
            if c_del.form_submit_button("🗑️ Delete", use_container_width=True):
                cursor.execute("DELETE FROM stock_items WHERE id = ?", (item_id,)); conn_dialog.commit(); st.success("Deleted!"); st.rerun()

# DIALOG MODAL POP-UP FOR ADDING SUPPLIER
@st.dialog("➕ Add New Supplier")
def add_supplier_dialog():
    conn_dialog = get_db()
    with st.form("add_supplier_form"):
        st.subheader("Supplier Details")
        col1, col2 = st.columns(2)
        with col1:
            s_code = st.text_input("Supplier Code *", placeholder="e.g. SUP003")
            s_name = st.text_input("Supplier Name *")
            s_type = st.selectbox("Type of Supplier *", ["Raw Material Supplier", "Buy Parts Supplier", "General / Both"])
            s_lt = st.number_input("Lead Time (Days)", min_value=0, value=3)
        with col2:
            s_contact = st.text_input("Contact Person")
            s_phone = st.text_input("Phone Number")
            s_email = st.text_input("E-mail Address")

        st.divider()
        if st.form_submit_button("💾 Save Supplier", type="primary", use_container_width=True):
            if s_code and s_name:
                try:
                    conn_dialog.cursor().execute("INSERT INTO suppliers (code, name, supplier_type, contact_person, phone, email, lead_time_days) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                                (s_code.strip(), s_name.strip(), s_type, s_contact.strip(), s_phone.strip(), s_email.strip(), s_lt))
                    conn_dialog.commit()
                    st.success("Supplier saved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please fill in Code and Name!")

# DIALOG MODAL POP-UP FOR EDITING SUPPLIER
@st.dialog("✏️ Edit Supplier Details")
def edit_supplier_dialog(supp_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT code, name, supplier_type, contact_person, phone, email, lead_time_days FROM suppliers WHERE id = ?", (supp_id,))
    row = cursor.fetchone()
    
    if row:
        with st.form("edit_supplier_form"):
            col1, col2 = st.columns(2)
            with col1:
                e_code = st.text_input("Supplier Code *", value=row[0])
                e_name = st.text_input("Supplier Name *", value=row[1])
                type_opts = ["Raw Material Supplier", "Buy Parts Supplier", "General / Both"]
                e_type = st.selectbox("Type of Supplier *", type_opts, index=type_opts.index(row[2]) if row[2] in type_opts else 0)
                e_lt = st.number_input("Lead Time (Days)", min_value=0, value=int(row[6]))
            with col2:
                e_contact = st.text_input("Contact Person", value=row[3] if row[3] else "")
                e_phone = st.text_input("Phone Number", value=row[4] if row[4] else "")
                e_email = st.text_input("E-mail Address", value=row[5] if row[5] else "")

            c_save, c_del = st.columns([8, 2])
            if c_save.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                cursor.execute("UPDATE suppliers SET code=?, name=?, supplier_type=?, contact_person=?, phone=?, email=?, lead_time_days=? WHERE id=?", 
                               (e_code, e_name, e_type, e_contact, e_phone, e_email, e_lt, supp_id))
                conn_dialog.commit(); st.success("Updated!"); st.rerun()
            if c_del.form_submit_button("🗑️ Delete", use_container_width=True):
                cursor.execute("DELETE FROM suppliers WHERE id = ?", (supp_id,)); conn_dialog.commit(); st.success("Deleted!"); st.rerun()

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

    # --- TAB 1: RAW MATERIALS ---
    if active_subtab == "Raw_Materials" or active_subtab == "Items":
        c1, c2, c3 = st.columns([6, 2, 2])
        with c1: st.markdown("##### Raw Materials Inventory")
        with c2: 
            if st.button("➕ Add Item", use_container_width=True, type="primary"): add_new_item_dialog("Raw Material")
        with c3:
            with st.popover("↑ Import CSV", use_container_width=True):
                csv_file = st.file_uploader("Upload CSV", type=['csv'])
                if csv_file and st.button("Execute Import"):
                    ins, upd = import_mrpeasy_items(pd.read_csv(csv_file))
                    st.success(f"Added: {ins}, Updated: {upd}"); st.rerun()

        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns([2, 3, 2, 2, 1.5, 1.5])
        f_raw_code = col_f1.text_input("Part No. / Uniq Code", key="f_raw_code")
        f_raw_name = col_f2.text_input("Part Description", key="f_raw_name")
        f_raw_sub = col_f3.selectbox("Sub-Group", ["All Sub-Groups", "Tabla", "Teava", "Europrofile", "Raw Materials Diverse"], key="f_raw_sub")
        f_raw_supp = col_f4.selectbox("Supplier", ["All Suppliers"] + [r[0] for r in conn.cursor().execute("SELECT DISTINCT s.name FROM stock_items si JOIN suppliers s ON si.supplier_id=s.id WHERE si.category='RAW MATERIAL'").fetchall()], key="f_raw_supp")
        f_raw_uom = col_f5.selectbox("UoM", ["All UoMs"] + [r[0] for r in conn.cursor().execute("SELECT DISTINCT u.code FROM stock_items si JOIN units u ON si.unit_id=u.id WHERE si.category='RAW MATERIAL'").fetchall()], key="f_raw_uom")
        col_f6.write(""); col_f6.write(""); col_f6.button("🔄 Reset Filters", use_container_width=True, on_click=reset_raw_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_raw = "SELECT si.id as ID, si.uniq_code as 'Uniq Code', si.code as 'Part No.', si.name as 'Description', si.sub_group as 'Sub-Group', s.name as 'Supplier', u.code as 'UoM', si.specific_weight as 'Spec. Weight', si.purchase_price as 'Purchase Price (€)' FROM stock_items si LEFT JOIN suppliers s ON si.supplier_id = s.id LEFT JOIN units u ON si.unit_id = u.id WHERE si.category = 'RAW MATERIAL'"
        params = []
        if f_raw_code: q_raw += " AND (si.code LIKE ? OR si.uniq_code LIKE ?)"; params.extend([f"%{f_raw_code}%", f"%{f_raw_code}%"])
        if f_raw_name: q_raw += " AND si.name LIKE ?"; params.append(f"%{f_raw_name}%")
        if f_raw_sub != "All Sub-Groups": q_raw += " AND si.sub_group = ?"; params.append(f_raw_sub)
        if f_raw_supp != "All Suppliers": q_raw += " AND s.name = ?"; params.append(f_raw_supp)
        if f_raw_uom != "All UoMs": q_raw += " AND u.code = ?"; params.append(f_raw_uom)
        
        df_raw = pd.read_sql_query(q_raw, conn, params=params)
        sel = st.dataframe(df_raw, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_raw")
        
        if sel and len(sel.selection.rows) > 0:
            selected_ids = [int(df_raw.iloc[i]['ID']) for i in sel.selection.rows]
            st.info(f"☑️ Selected {len(selected_ids)} item(s)")
            col_a1, col_a2, _ = st.columns([2, 2, 8])
            with col_a1:
                if len(selected_ids) == 1:
                    if st.button("✏️ Edit Selected", use_container_width=True): edit_item_dialog(selected_ids[0])
            with col_a2:
                if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_stock_dialog(selected_ids)

    # --- TAB 2: BUY PARTS ---
    elif active_subtab == "Buy_Parts":
        st.markdown("##### Purchased Parts & Fasteners")
        if st.button("➕ Add Item", type="primary"): add_new_item_dialog("Buy Part")
        st.write("")

        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_b1, col_b2, col_b3, col_b4 = st.columns([3, 4, 3, 2])
        f_buy_code = col_b1.text_input("Part No.", key="f_buy_code")
        f_buy_name = col_b2.text_input("Description", key="f_buy_name")
        f_buy_supp = col_b3.selectbox("Supplier", ["All Suppliers"] + [r[0] for r in conn.cursor().execute("SELECT DISTINCT s.name FROM stock_items si JOIN suppliers s ON si.supplier_id=s.id WHERE si.category='BUY PART'").fetchall()], key="f_buy_supp")
        col_b4.write(""); col_b4.write(""); col_b4.button("🔄 Reset", use_container_width=True, on_click=reset_buy_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_buy = "SELECT si.id as ID, si.uniq_code as 'Uniq Code', si.code as 'Part No.', si.name as 'Description', s.name as 'Supplier', u.code as 'UoM', si.purchase_price as 'Purchase Price (€)' FROM stock_items si LEFT JOIN suppliers s ON si.supplier_id = s.id LEFT JOIN units u ON si.unit_id = u.id WHERE si.category = 'BUY PART'"
        params = []
        if f_buy_code: q_buy += " AND (si.code LIKE ? OR si.uniq_code LIKE ?)"; params.extend([f"%{f_buy_code}%", f"%{f_buy_code}%"])
        if f_buy_name: q_buy += " AND si.name LIKE ?"; params.append(f"%{f_buy_name}%")
        if f_buy_supp != "All Suppliers": q_buy += " AND s.name = ?"; params.append(f_buy_supp)
        
        df_buy = pd.read_sql_query(q_buy, conn, params=params)
        sel = st.dataframe(df_buy, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_buy")
        
        if sel and len(sel.selection.rows) > 0:
            selected_ids = [int(df_buy.iloc[i]['ID']) for i in sel.selection.rows]
            st.info(f"☑️ Selected {len(selected_ids)} item(s)")
            col_a1, col_a2, _ = st.columns([2, 2, 8])
            with col_a1:
                if len(selected_ids) == 1:
                    if st.button("✏️ Edit Selected", use_container_width=True): edit_item_dialog(selected_ids[0])
            with col_a2:
                if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_stock_dialog(selected_ids)

    # --- TAB 3: FINISHED GOODS ---
    elif active_subtab == "Finished_Goods":
        st.markdown("##### Finished Goods & Subassemblies")
        if st.button("➕ Add Item", type="primary"): add_new_item_dialog("Finished Good / Subassembly")
        st.write("")
        
        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col_fg1, col_fg2, col_fg3, col_fg4 = st.columns([3, 4, 3, 2])
        f_fg_code = col_fg1.text_input("Product Code", key="f_fg_code")
        f_fg_name = col_fg2.text_input("Description", key="f_fg_name")
        f_fg_cat = col_fg3.selectbox("Category", ["All Categories", "FINISHED GOOD", "SUBASSEMBLY"], key="f_fg_cat")
        col_fg4.write(""); col_fg4.write(""); col_fg4.button("🔄 Reset", use_container_width=True, on_click=reset_fg_filters_callback)
        st.markdown('</div>', unsafe_allow_html=True)

        q_fin = "SELECT si.id as ID, si.uniq_code as 'Uniq Code', si.name as 'Description', si.category as 'Category', u.code as 'UoM', si.selling_price as 'Selling Price (€)' FROM stock_items si LEFT JOIN units u ON si.unit_id = u.id WHERE si.category IN ('FINISHED GOOD', 'SUBASSEMBLY')"
        params = []
        if f_fg_code: q_fin += " AND (si.code LIKE ? OR si.uniq_code LIKE ?)"; params.extend([f"%{f_fg_code}%", f"%{f_fg_code}%"])
        if f_fg_name: q_fin += " AND si.name LIKE ?"; params.append(f"%{f_fg_name}%")
        if f_fg_cat != "All Categories": q_fin += " AND si.category = ?"; params.append(f_fg_cat)

        df_fin = pd.read_sql_query(q_fin, conn, params=params)
        sel = st.dataframe(df_fin, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_fin")
        
        if sel and len(sel.selection.rows) > 0:
            selected_ids = [int(df_fin.iloc[i]['ID']) for i in sel.selection.rows]
            st.info(f"☑️ Selected {len(selected_ids)} item(s)")
            col_a1, col_a2, _ = st.columns([2, 2, 8])
            with col_a1:
                if len(selected_ids) == 1:
                    if st.button("✏️ Edit Selected", use_container_width=True): edit_item_dialog(selected_ids[0])
            with col_a2:
                if st.button("🗑️ Delete Selected", use_container_width=True): bulk_delete_stock_dialog(selected_ids)

    # --- TAB 4: SUPPLIERS ---
    elif active_subtab == "Suppliers":
        c_head, c_btn = st.columns([8, 2])
        with c_head:
            st.markdown("##### Supplier Management")
        with c_btn:
            if st.button("➕ Add Supplier", type="primary", use_container_width=True): add_supplier_dialog()
        
        st.write("")
        df_s = pd.read_sql_query("SELECT id as ID, code as Code, name as 'Supplier Name', supplier_type as 'Supplier Type', contact_person as 'Contact Person', phone as Phone, email as Email, lead_time_days as 'Lead Time (Days)' FROM suppliers ORDER BY name", conn)
        
        sel_supp = st.dataframe(df_s, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="t_supp", column_config={"ID": None})
        
        if sel_supp and len(sel_supp.selection.rows) > 0:
            selected_ids = [int(df_s.iloc[i]['ID']) for i in sel_supp.selection.rows]
            st.info(f"☑️ Selected {len(selected_ids)} supplier(s)")
            col_a1, col_a2, _ = st.columns([2, 2, 8])
            with col_a1:
                if len(selected_ids) == 1:
                    if st.button("✏️ Edit Selected", use_container_width=True): 
                        edit_supplier_dialog(selected_ids[0])
            with col_a2:
                if st.button("🗑️ Delete Selected", use_container_width=True): 
                    bulk_delete_suppliers_dialog(selected_ids)

    # --- TAB 5: WAREHOUSES ---
    elif active_subtab == "Warehouses":
        st.markdown("##### Warehouses"); df_w = pd.read_sql_query("SELECT * FROM warehouses", conn); st.dataframe(df_w, hide_index=True)
    
    # --- TAB 6: UNITS ---
    elif active_subtab == "Units":
        st.markdown("##### Units"); df_u = pd.read_sql_query("SELECT * FROM units", conn); st.dataframe(df_u, hide_index=True)

elif active_page in ["BOM", "RFQ"]:
    st.info(f"{active_page} module ready for configuration.")

conn.close()
