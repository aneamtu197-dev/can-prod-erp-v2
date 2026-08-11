import streamlit as st
import pandas as pd
from db import get_db, generate_unique_item_code, safe_float

@st.dialog("➕ Add New Warehouse")
def add_warehouse_dialog():
    conn_dialog = get_db()
    with st.form("add_wh_form"):
        st.subheader("New Warehouse Details")
        w_code = st.text_input("Warehouse Code *", placeholder="e.g. WH-001")
        w_name = st.text_input("Warehouse Name *", placeholder="e.g. Depozit Central")
        w_loc = st.selectbox("Location Type", ["Internal Warehouse", "Customer Virtual Storage", "External / Third Party"])
        
        if st.form_submit_button("💾 Save Warehouse", type="primary", use_container_width=True):
            if w_code and w_name:
                cursor = conn_dialog.cursor()
                cursor.execute("SELECT id FROM warehouses WHERE code = %s", (w_code.strip(),))
                if cursor.fetchone(): st.warning("⚠️ Code exists!")
                else:
                    cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (%s, %s, %s)", (w_code.strip(), w_name.strip(), w_loc))
                    conn_dialog.commit(); st.success("Saved!"); st.rerun()
            else: st.warning("Complete missing fields!")

@st.dialog("⚙️ Gestionare Depozit")
def edit_warehouse_dialog(wh_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT code, name, location_type FROM warehouses WHERE id = %s", (wh_id,))
    row = cursor.fetchone()
    if row:
        with st.form("edit_wh_form"):
            e_code = st.text_input("Cod (Doar citire) *", value=row[0], disabled=True)
            e_name = st.text_input("Nume Depozit *", value=row[1])
            loc_opts = ["Internal Warehouse", "Customer Virtual Storage", "External / Third Party"]
            e_loc = st.selectbox("Tip Depozit", loc_opts, index=loc_opts.index(row[2]) if row[2] in loc_opts else 0)
            
            st.write("")
            c_save, c_del = st.columns([7, 3])
            if c_save.form_submit_button("💾 Salvează Modificările", type="primary", use_container_width=True):
                cursor.execute("UPDATE warehouses SET name=%s, location_type=%s WHERE id=%s", (e_name.strip(), e_loc, wh_id))
                conn_dialog.commit(); st.success("Updated!"); st.rerun()
            if c_del.form_submit_button("🗑️ Șterge Depozitul", use_container_width=True):
                cursor.execute("SELECT count(id) FROM stock_items WHERE warehouse_id = %s", (wh_id,))
                if cursor.fetchone()[0] > 0: st.error("🚨 Eroare: Există materiale asociate cu acest depozit!")
                else:
                    cursor.execute("DELETE FROM warehouses WHERE id = %s", (wh_id,)); conn_dialog.commit(); st.success("Deleted!"); st.rerun()

@st.dialog("➕ Add New Item to Stock")
def add_new_item_dialog(default_type="Raw Material"):
    conn_dialog = get_db()
    st.subheader("Step 1: Select Item Type")
    types = ["Raw Material", "Buy Part", "Finished Good / Subassembly"]
    item_type = st.selectbox("Item Type *", types, index=types.index(default_type) if default_type in types else 0)
    
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
        st.subheader("Step 2: Characteristics")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Uniq Code *", value=auto_uniq, disabled=True)
            code = st.text_input("Part No. / Original Code *", value=auto_uniq)
            name = st.text_input("Part Description / Name *")
            df_u = pd.read_sql_query("SELECT id, code, name FROM units", conn_dialog)
            u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u.iterrows()}
            selected_u = st.selectbox("UoM *", list(u_dict.keys()))
            df_s = pd.read_sql_query("SELECT id, name FROM suppliers", conn_dialog)
            s_dict = {r['name']: r['id'] for _, r in df_s.iterrows()}
            selected_s = st.selectbox("Supplier", ["No Supplier"] + list(s_dict.keys())) if item_type != "Finished Good / Subassembly" else "No Supplier"
            df_c = pd.read_sql_query("SELECT id, name FROM customers", conn_dialog)
            c_dict = {r['name']: r['id'] for _, r in df_c.iterrows()}
            selected_c = st.selectbox("Customer", ["General / Stock"] + list(c_dict.keys())) if item_type == "Finished Good / Subassembly" else "General / Stock"

        with col2:
            price = st.number_input("Purchase Price (€)", min_value=0.0) if item_type != "Finished Good / Subassembly" else 0.0
            selling_p = st.number_input("Selling Price (€)", min_value=0.0)
            c_w1, c_w2 = st.columns([2, 1])
            with c_w1: spec_weight = st.number_input("Spec Weight", min_value=0.0)
            with c_w2: w_unit = st.selectbox("Unit", ["kg", "lbs", "g"])
            df_w = pd.read_sql_query("SELECT id, name FROM warehouses", conn_dialog)
            w_dict = {r['name']: r['id'] for _, r in df_w.iterrows()}
            selected_w = st.selectbox("Warehouse", list(w_dict.keys()))
            stock_qty = st.number_input("Initial Stock", min_value=0.0)
            min_stock_qty = st.number_input("Reorder Point", min_value=0.0)

        if st.form_submit_button("💾 Save Item", type="primary", use_container_width=True):
            if auto_uniq and name:
                cursor = conn_dialog.cursor()
                cursor.execute("SELECT id FROM stock_items WHERE code = %s OR name = %s", (code.strip(), name.strip()))
                if cursor.fetchone(): st.warning("⚠️ Item exists!")
                else:
                    s_id = s_dict.get(selected_s) if selected_s != "No Supplier" else None
                    c_id = c_dict.get(selected_c) if selected_c != "General / Stock" else None
                    cursor.execute("""INSERT INTO stock_items (uniq_code, code, name, category, sub_group, supplier_id, customer_id, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                                          (auto_uniq, code.strip(), name.strip(), category, sub_group, s_id, c_id, u_dict.get(selected_u), w_dict.get(selected_w), price, selling_p, spec_weight, w_unit, stock_qty, min_stock_qty))
                    conn_dialog.commit(); st.success("Item saved!"); st.rerun()

@st.dialog("⚙️ Edit Item Details")
def edit_item_dialog(item_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT uniq_code, code, name, category, sub_group, supplier_id, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock, customer_id FROM stock_items WHERE id = %s", (item_id,))
    row = cursor.fetchone()
    if row:
        with st.form("edit_item_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Uniq Code *", value=row[0], disabled=True)
                e_code = st.text_input("Part No. *", value=row[1])
                e_name = st.text_input("Name *", value=row[2])
                e_sub = st.selectbox("Sub-Group", ["Tabla", "Teava", "Europrofile", "Raw Materials Diverse"]) if str(row[3]).upper() in ["RAW MATERIAL", "MATERIE PRIMA"] else row[4]
                
                df_u = pd.read_sql_query("SELECT id, code, name FROM units", conn_dialog)
                u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u.iterrows()}
                u_keys = list(u_dict.keys()); u_index = [idx for idx, k in enumerate(u_keys) if u_dict[k] == row[6]]
                selected_u = st.selectbox("UoM", u_keys, index=u_index[0] if u_index else 0)

                df_s = pd.read_sql_query("SELECT id, name FROM suppliers", conn_dialog)
                s_dict = {r['name']: r['id'] for _, r in df_s.iterrows()}
                s_keys = ["No Supplier"] + list(s_dict.keys()); s_curr = [k for k, v in s_dict.items() if v == row[5]]
                selected_s = st.selectbox("Supplier", s_keys, index=s_keys.index(s_curr[0]) if s_curr else 0)

                df_c = pd.read_sql_query("SELECT id, name FROM customers", conn_dialog)
                c_dict = {r['name']: r['id'] for _, r in df_c.iterrows()}
                c_keys = ["General / Stock"] + list(c_dict.keys()); c_curr = [k for k, v in c_dict.items() if v == row[14]]
                selected_c = st.selectbox("Customer", c_keys, index=c_keys.index(c_curr[0]) if c_curr else 0) if str(row[3]).upper() in ["FINISHED GOOD", "SUBASSEMBLY", "PRODUSE FINITE"] else "General / Stock"

            with col2:
                e_pprice = st.number_input("Purchase Price (€)", value=safe_float(row[8]))
                e_sprice = st.number_input("Selling Price (€)", value=safe_float(row[9]))
                c_w1, c_w2 = st.columns([2, 1])
                with c_w1: e_sweight = st.number_input("Spec Weight", value=safe_float(row[10]))
                with c_w2: e_wunit = st.selectbox("Unit", ["kg", "lbs", "g"], index=["kg", "lbs", "g"].index(row[11] if row[11] else "kg"))

                df_w = pd.read_sql_query("SELECT id, name FROM warehouses", conn_dialog)
                w_dict = {r['name']: r['id'] for _, r in df_w.iterrows()}
                w_keys = list(w_dict.keys()); w_curr = [k for k, v in w_dict.items() if v == row[7]]
                selected_w = st.selectbox("Warehouse", w_keys, index=w_keys.index(w_curr[0]) if w_curr else 0)

                e_stock = st.number_input("Current Stock", value=safe_float(row[12]))
                e_minstock = st.number_input("Reorder Point", value=safe_float(row[13]))

            c_save, c_del = st.columns([8, 2])
            if c_save.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                s_id = s_dict.get(selected_s) if selected_s != "No Supplier" else None
                c_id = c_dict.get(selected_c) if selected_c != "General / Stock" else None
                cursor.execute("""UPDATE stock_items SET code=%s, name=%s, sub_group=%s, supplier_id=%s, customer_id=%s, unit_id=%s, warehouse_id=%s, purchase_price=%s, selling_price=%s, specific_weight=%s, weight_unit=%s, current_stock=%s, min_stock=%s WHERE id=%s""", 
                               (e_code, e_name, e_sub, s_id, c_id, u_dict.get(selected_u), w_dict.get(selected_w), e_pprice, e_sprice, e_sweight, e_wunit, e_stock, e_minstock, item_id))
                conn_dialog.commit(); st.success("Updated!"); st.rerun()
            if c_del.form_submit_button("🗑️ Delete", use_container_width=True):
                cursor.execute("DELETE FROM stock_items WHERE id = %s", (item_id,)); conn_dialog.commit(); st.success("Deleted!"); st.rerun()
