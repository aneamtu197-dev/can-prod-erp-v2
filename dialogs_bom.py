import streamlit as st
import pandas as pd
from db import get_db, generate_unique_item_code, generate_unique_facility_code, generate_unique_operation_code, safe_float
from pdf_engine import generate_bom_pdf, generate_routing_pdf

def get_or_create_product_bom(db_conn, target_prod_id, cust_id=None):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM product_boms WHERE product_item_id = %s ORDER BY id ASC", (target_prod_id,))
    rows = cursor.fetchall()
    if not rows:
        cursor.execute("INSERT INTO product_boms (product_item_id, customer_id) VALUES (%s, %s) RETURNING id", (target_prod_id, cust_id))
        new_id = cursor.fetchone()[0]
        db_conn.commit()
        return new_id
    main_bom_id = rows[0][0]
    if len(rows) > 1:
        other_ids = [r[0] for r in rows[1:]]
        placeholders = ",".join(["%s"] * len(other_ids))
        cursor.execute(f"UPDATE bom_materials SET bom_id = %s WHERE bom_id IN ({placeholders})", [main_bom_id] + other_ids)
        cursor.execute(f"UPDATE bom_operations SET bom_id = %s WHERE bom_id IN ({placeholders})", [main_bom_id] + other_ids)
        cursor.execute(f"DELETE FROM product_boms WHERE id IN ({placeholders})", other_ids)
        db_conn.commit()
    return main_bom_id

@st.dialog("➕ Create New Finished Product", width="large")
def create_finished_product_dialog():
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    auto_part_no = generate_unique_item_code(conn_dialog, "FINISHED GOOD")
    auto_barcode = f"BAR-{auto_part_no}"
    col1, col2 = st.columns(2)
    df_cust = pd.read_sql_query("SELECT id, name FROM customers ORDER BY name", conn_dialog)
    cust_dict = {r['name']: r['id'] for _, r in df_cust.iterrows()}
    df_wh = pd.read_sql_query("SELECT id, name, customer_id FROM warehouses ORDER BY name", conn_dialog)
    wh_dict = {r['name']: r['id'] for _, r in df_wh.iterrows()}
    cust_to_wh = {r['customer_id']: r['name'] for _, r in df_wh.iterrows() if r['customer_id']}

    if "p_cust_sel" not in st.session_state: st.session_state["p_cust_sel"] = "General / Stock Product"
    if "p_wh_sel" not in st.session_state: st.session_state["p_wh_sel"] = list(wh_dict.keys())[0] if wh_dict else ""

    def sync_cust_to_wh():
        selected = st.session_state.get("p_cust_sel_key")
        st.session_state["p_cust_sel"] = selected
        if selected in cust_dict:
            c_id = cust_dict[selected]
            if c_id in cust_to_wh: st.session_state["p_wh_sel"] = cust_to_wh[c_id]

    def sync_wh_to_cust():
        selected_wh = st.session_state.get("p_wh_sel_key")
        st.session_state["p_wh_sel"] = selected_wh
        cursor.execute("SELECT customer_id FROM warehouses WHERE name = %s", (selected_wh,))
        res = cursor.fetchone()
        if res and res[0]:
            c_id = res[0]
            matched = [k for k, v in cust_dict.items() if v == c_id]
            if matched: st.session_state["p_cust_sel"] = matched[0]

    with col1:
        st.text_input("Part No. *", value=auto_part_no, disabled=True)
        df_existing_prods = pd.read_sql_query("SELECT pb.id as bom_id, si.uniq_code, si.name FROM product_boms pb JOIN stock_items si ON pb.product_item_id = si.id ORDER BY si.name", conn_dialog)
        copy_dict = {f"{r['uniq_code']} - {r['name']}": r['bom_id'] for _, r in df_existing_prods.iterrows()}
        selected_copy = st.selectbox("Copy BOM", ["None (Start from Scratch)"] + list(copy_dict.keys()))
        part_desc = st.text_input("Part Description *")
        prod_group = st.selectbox("Product Group *", ["FINISHED GOOD", "SUBASSEMBLY", "PROTOTYPE / SAMPLE", "CUSTOM ORDER"])
        df_u = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn_dialog)
        u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u.iterrows()}
        sel_uom = st.selectbox("UoM *", list(u_dict.keys()))

    with col2:
        c_keys = ["General / Stock Product"] + list(cust_dict.keys())
        st.selectbox("Customer *", c_keys, index=c_keys.index(st.session_state["p_cust_sel"]) if st.session_state["p_cust_sel"] in c_keys else 0, key="p_cust_sel_key", on_change=sync_cust_to_wh)
        wh_keys = list(wh_dict.keys())
        st.selectbox("Default Storage *", wh_keys, index=wh_keys.index(st.session_state["p_wh_sel"]) if st.session_state["p_wh_sel"] in wh_keys else 0, key="p_wh_sel_key", on_change=sync_wh_to_cust)
        selling_p = st.number_input("Selling Price (€)", min_value=0.0)
        st.text_input("Barcode", value=auto_barcode, disabled=True)

    calc_weight = 0.0
    if selected_copy != "None (Start from Scratch)":
        src_bom_id = copy_dict[selected_copy]
        cursor.execute("SELECT si.name, bm.quantity_required, si.specific_weight FROM bom_materials bm JOIN stock_items si ON bm.material_item_id = si.id WHERE bm.bom_id = %s", (src_bom_id,))
        for m_name, qty, sp_w in cursor.fetchall():
            if sp_w: calc_weight += float(qty * sp_w)
            
    if st.button("💾 Save Item & Build Recipe", type="primary", use_container_width=True):
        if part_desc.strip():
            sel_cust_cur = st.session_state["p_cust_sel"]
            sel_wh_cur = st.session_state["p_wh_sel"]
            cust_id_val = cust_dict.get(sel_cust_cur) if sel_cust_cur != "General / Stock Product" else None
            cursor.execute("INSERT INTO stock_items (uniq_code, code, name, category, sub_group, customer_id, unit_id, warehouse_id, selling_price, specific_weight, weight_unit, barcode) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'kg', %s) RETURNING id", (auto_part_no, auto_part_no, part_desc.strip(), prod_group, "Finished Goods", cust_id_val, u_dict[sel_uom], wh_dict[sel_wh_cur], selling_p, calc_weight, auto_barcode))
            new_prod_id = cursor.fetchone()[0]
            new_bom_id = get_or_create_product_bom(conn_dialog, new_prod_id, cust_id_val)
            
            if selected_copy != "None (Start from Scratch)":
                src_bom_id = copy_dict[selected_copy]
                cursor.execute("SELECT material_item_id, quantity_required, unit_cost, total_cost FROM bom_materials WHERE bom_id = %s", (src_bom_id,))
                for m_item, qty, u_c, t_c in cursor.fetchall(): cursor.execute("INSERT INTO bom_materials (bom_id, material_item_id, quantity_required, unit_cost, total_cost) VALUES (%s, %s, %s, %s, %s)", (new_bom_id, m_item, qty, u_c, t_c))
                cursor.execute("SELECT operation_id, step_number, duration_hours, rate_applied, total_cost FROM bom_operations WHERE bom_id = %s", (src_bom_id,))
                for op_id, step_n, dur, r_app, t_c in cursor.fetchall(): cursor.execute("INSERT INTO bom_operations (bom_id, operation_id, step_number, duration_hours, rate_applied, total_cost) VALUES (%s, %s, %s, %s, %s, %s)", (new_bom_id, op_id, step_n, dur, r_app, t_c))
            conn_dialog.commit()
            st.session_state["active_bom_dialog_prod_id"] = new_prod_id
            st.session_state["keep_bom_dialog_open"] = True
            st.rerun()

@st.dialog("➕ Edit Product BOM Recipe", width="large")
def manage_product_bom_dialog(selected_prod_id=None):
    conn = get_db()
    st.session_state["keep_bom_dialog_open"] = False
    df_prods = pd.read_sql_query("SELECT id, uniq_code, code, name, customer_id FROM stock_items WHERE UPPER(category) IN ('FINISHED GOOD', 'SUBASSEMBLY', 'PRODUSE FINITE') ORDER BY name", conn)
    if len(df_prods) == 0: st.warning("Please add Finished Goods!"); return
    prod_dict = {f"{r['uniq_code']} - {r['name']}": r['id'] for _, r in df_prods.iterrows()}
    
    target_id = selected_prod_id or st.session_state.get("active_bom_dialog_prod_id")
    idx_prod = 0
    if target_id:
        curr_keys = [k for k, v in prod_dict.items() if v == target_id]
        if curr_keys: idx_prod = list(prod_dict.keys()).index(curr_keys[0])

    sel_prod_key = st.selectbox("Select Product *", list(prod_dict.keys()), index=idx_prod)
    target_prod_id = prod_dict[sel_prod_key]
    st.session_state["active_bom_dialog_prod_id"] = target_prod_id

    df_cust = pd.read_sql_query("SELECT id, name FROM customers ORDER BY name", conn)
    cust_dict = {r['name']: r['id'] for _, r in df_cust.iterrows()}
    cursor = conn.cursor()
    cursor.execute("SELECT uniq_code, name, customer_id FROM stock_items WHERE id = %s", (target_prod_id,))
    row_item = cursor.fetchone()
    curr_c_id = row_item[2] if row_item else None

    c_keys = ["General / Stock Product"] + list(cust_dict.keys())
    curr_c_name = [k for k, v in cust_dict.items() if v == curr_c_id]
    sel_cust_name = st.selectbox("Assigned Customer *", c_keys, index=c_keys.index(curr_c_name[0]) if curr_c_name else 0)

    bom_id = get_or_create_product_bom(conn, target_prod_id, cust_dict.get(sel_cust_name))
    st.divider()
    
    t_mat, t_ops = st.tabs(["📦 Material Consumption (BOM)", "⚙️ Labor Operations (Routing)"])
    
    with t_mat:
        df_all_mat = pd.read_sql_query("SELECT id, uniq_code, name FROM stock_items WHERE UPPER(category) NOT IN ('FINISHED GOOD', 'SUBASSEMBLY', 'PRODUSE FINITE') ORDER BY name", conn)
        mat_dict = {f"{r['uniq_code']} - {r['name']}": r['id'] for _, r in df_all_mat.iterrows()}
        df_bm = pd.read_sql_query("SELECT bm.id as ID, bm.material_item_id, si.uniq_code as Code, si.name as \"Material Name\", bm.quantity_required as Qty, u.code as UoM, bm.unit_cost as Price, bm.total_cost as \"Total Cost\" FROM bom_materials bm JOIN stock_items si ON bm.material_item_id = si.id JOIN units u ON si.unit_id = u.id WHERE bm.bom_id = %s", conn, params=[bom_id])
        if len(df_bm) > 0:
            for _, r_m in df_bm.iterrows():
                cm1, cm2, cm3, cm4, cm5 = st.columns([4, 2, 2, 2, 1])
                cm1.write(f"**{r_m['Code']} - {r_m['Material Name']}**")
                cm2.write(f"{r_m['Qty']} {r_m['UoM']}")
                cm3.write(f"{r_m['Price']} €")
                cm4.write(f"**{r_m['Total Cost']} €**")
                if cm5.button("🗑️", key=f"del_mat_{r_m['ID']}"):
                    cursor.execute("DELETE FROM bom_materials WHERE id = %s", (r_m['ID'],))
                    conn.commit(); st.session_state["keep_bom_dialog_open"] = True; st.rerun()

        col_m1, col_m2, col_m3 = st.columns([5, 3, 2])
        ver_m = st.session_state.get("bom_select_version", 0)
        add_mat_key = col_m1.selectbox("Select Material", [""] + list(mat_dict.keys()), key=f"mat_k_{ver_m}")
        add_mat_qty = col_m2.number_input("Qty", min_value=0.001, value=1.0, key=f"mat_q_{ver_m}")
        if col_m3.button("➕ Add", key="add_mat"):
            if add_mat_key:
                m_id = mat_dict[add_mat_key]
                cursor.execute("SELECT purchase_price FROM stock_items WHERE id = %s", (m_id,))
                price = cursor.fetchone()[0] or 0.0
                cursor.execute("INSERT INTO bom_materials (bom_id, material_item_id, quantity_required, unit_cost, total_cost) VALUES (%s, %s, %s, %s, %s)", (bom_id, m_id, add_mat_qty, price, float(price * add_mat_qty)))
                conn.commit(); st.session_state["bom_select_version"] = ver_m + 1; st.session_state["keep_bom_dialog_open"] = True; st.rerun()

    with t_ops:
        df_all_ops = pd.read_sql_query("SELECT id, uniq_code, name FROM operations ORDER BY uniq_code", conn)
        op_dict = {f"{r['uniq_code']} - {r['name']}": r['id'] for _, r in df_all_ops.iterrows()}
        df_bo = pd.read_sql_query("SELECT bo.id as ID, bo.step_number as Step, bo.operation_id, o.uniq_code as \"Op Code\", o.name as \"Operation Name\", o.cost_unit as Unit, bo.duration_hours as Duration, bo.rate_applied as Rate, bo.total_cost as \"Total Cost\" FROM bom_operations bo JOIN operations o ON bo.operation_id = o.id WHERE bo.bom_id = %s ORDER BY bo.step_number", conn, params=[bom_id])
        if len(df_bo) > 0:
            for _, r_o in df_bo.iterrows():
                co1, co2, co3, co4, co5 = st.columns([1, 4, 2, 2, 1])
                co1.write(f"S{r_o['Step']}")
                co2.write(f"**{r_o['Operation Name']}**")
                co3.write(f"{r_o['Duration']} {r_o['Unit']}")
                co4.write(f"**{r_o['Total Cost']} €**")
                if co5.button("🗑️", key=f"del_op_{r_o['ID']}"):
                    cursor.execute("DELETE FROM bom_operations WHERE id = %s", (r_o['ID'],)); conn.commit(); st.session_state["keep_bom_dialog_open"] = True; st.rerun()

        col_o1, col_o2, col_o3 = st.columns([5, 3, 2])
        ver_o = st.session_state.get("bom_select_version", 0)
        add_op_key = col_o1.selectbox("Select Operation", [""] + list(op_dict.keys()), key=f"op_k_{ver_o}")
        add_op_dur = col_o2.number_input("Qty/Dur", min_value=0.01, value=0.5, key=f"op_q_{ver_o}")
        if col_o3.button("➕ Add", key="add_op"):
            if add_op_key:
                o_id = op_dict[add_op_key]
                cursor.execute("SELECT rate_per_unit FROM operations WHERE id = %s", (o_id,))
                rate = cursor.fetchone()[0] or 0.0
                cursor.execute("SELECT COALESCE(MAX(step_number), 0) + 1 FROM bom_operations WHERE bom_id = %s", (bom_id,))
                next_step = cursor.fetchone()[0]
                cursor.execute("INSERT INTO bom_operations (bom_id, operation_id, step_number, duration_hours, rate_applied, total_cost) VALUES (%s, %s, %s, %s, %s, %s)", (bom_id, o_id, next_step, add_op_dur, rate, float(rate * add_op_dur)))
                conn.commit(); st.session_state["bom_select_version"] = ver_o + 1; st.session_state["keep_bom_dialog_open"] = True; st.rerun()

    cursor.execute("SELECT SUM(total_cost) FROM bom_materials WHERE bom_id = %s", (bom_id,))
    tot_mat_cost = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(total_cost) FROM bom_operations WHERE bom_id = %s", (bom_id,))
    tot_lab_cost = cursor.fetchone()[0] or 0.0
    tot_prod_cost = tot_mat_cost + tot_lab_cost

    if st.button("💾 Save Product Recipe & Update Costs", type="primary", use_container_width=True):
        c_id = cust_dict.get(sel_cust_name)
        cursor.execute("UPDATE product_boms SET customer_id=%s, total_material_cost=%s, total_labor_cost=%s, total_production_cost=%s WHERE id=%s", (c_id, tot_mat_cost, tot_lab_cost, tot_prod_cost, bom_id))
        cursor.execute("UPDATE stock_items SET customer_id=%s, purchase_price=%s WHERE id=%s", (c_id, tot_prod_cost, target_prod_id))
        conn.commit(); st.session_state["keep_bom_dialog_open"] = False; st.rerun()

@st.dialog("➕ Add Production Facility")
def add_facility_dialog():
    conn_dialog = get_db()
    auto_fac_code = generate_unique_facility_code(conn_dialog)
    with st.form("add_facility_form"):
        f_name = st.text_input("Machine Name *")
        f_type = st.selectbox("Category", ["Laser Cutting", "Press Brake / Abkant", "Welding Station", "Powder Coating / Vopsitorie", "CNC Machining", "General Machine", "Manual Workstation"])
        if st.form_submit_button("💾 Save Facility", type="primary", use_container_width=True):
            if f_name.strip():
                cursor = conn_dialog.cursor()
                cursor.execute("INSERT INTO production_facilities (code, name, facility_type, status) VALUES (%s, %s, %s, 'Operational')", (auto_fac_code, f_name.strip(), f_type))
                conn_dialog.commit(); st.success("Facility saved!"); st.rerun()

@st.dialog("⚙️ Edit Facility Details")
def edit_facility_dialog(fac_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT code, name, facility_type FROM production_facilities WHERE id = %s", (fac_id,))
    row = cursor.fetchone()
    if row:
        with st.form("edit_facility_form"):
            e_name = st.text_input("Machine Name *", value=row[1])
            if st.form_submit_button("💾 Save Changes", type="primary"):
                cursor.execute("UPDATE production_facilities SET name=%s WHERE id=%s", (e_name.strip(), fac_id))
                conn_dialog.commit(); st.success("Updated!"); st.rerun()

@st.dialog("➕ Add Operation")
def add_operation_dialog():
    conn_dialog = get_db()
    auto_op_code = generate_unique_operation_code(conn_dialog)
    with st.form("add_operation_form"):
        op_name = st.text_input("Operation Name *")
        rate_unit = st.number_input("Rate per Unit (€) *", min_value=0.0, value=25.0)
        if st.form_submit_button("💾 Save Operation", type="primary", use_container_width=True):
            if op_name.strip():
                cursor = conn_dialog.cursor()
                cursor.execute("INSERT INTO operations (uniq_code, name, cost_unit, rate_per_unit, is_outsourced) VALUES (%s, %s, 'Hour', %s, 0)", (auto_op_code, op_name.strip(), rate_unit))
                conn_dialog.commit(); st.success("Operation saved!"); st.rerun()

@st.dialog("⚙️ Edit Operation")
def edit_operation_dialog(op_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT name, rate_per_unit FROM operations WHERE id = %s", (op_id,))
    row = cursor.fetchone()
    if row:
        with st.form("edit_operation_form"):
            e_name = st.text_input("Operation Name *", value=row[0])
            e_rate = st.number_input("Rate (€)", value=safe_float(row[1]))
            if st.form_submit_button("💾 Save Changes", type="primary"):
                cursor.execute("UPDATE operations SET name=%s, rate_per_unit=%s WHERE id=%s", (e_name.strip(), e_rate, op_id))
                conn_dialog.commit(); st.success("Updated!"); st.rerun()
