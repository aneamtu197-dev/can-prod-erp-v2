import streamlit as st
import pandas as pd
import requests

from datetime import datetime
from db import (
    init_custom_db, get_db, generate_unique_item_code, generate_unique_customer_code, 
    generate_unique_facility_code, generate_unique_operation_code, import_mrpeasy_items, 
    import_mrpeasy_customers, safe_float
)
from ui import load_css, render_top_header, render_nav_bar

st.set_page_config(page_title="CAN Prod ERP Custom", layout="wide", initial_sidebar_state="collapsed")

# Initialize DB & Load CSS
init_custom_db()
load_css()

query_params = st.query_params
active_page = query_params.get("page", "Home")
active_subtab = query_params.get("subtab", "Product")

# Render UI Headers
render_top_header()
render_nav_bar(active_page)

conn = get_db()

# --- ANAF API FUNCTION ---
def fetch_anaf_data(cui):
    try:
        clean_cui = ''.join(filter(str.isdigit, str(cui)))
        if not clean_cui: return None, "CUI invalid (conține doar cifre)."
        
        today = datetime.now().strftime("%Y-%m-%d")
        payload = [{"cui": int(clean_cui), "data": today}]
        headers = {"Content-Type": "application/json"}
        
        for version in ["v9", "v8", "v7"]:
            url = f"https://webservicesp.anaf.ro/PlatitorTvaRest/api/{version}/ws/tva"
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('cod') == 200 and data.get('found') and len(data.get('found')) > 0:
                    company = data['found'][0]
                    return {
                        'name': company.get('denumire', ''),
                        'address': company.get('adresa', ''),
                        'reg_com': company.get('nrRegCom', '')
                    }, None
                else:
                    return None, "CUI-ul nu a fost găsit în baza de date ANAF."
            elif response.status_code in [403, 404]:
                continue
        return None, "🚨 ANAF blochează cererile de pe serverele Streamlit Cloud. Te rugăm să introduci datele manual."
    except Exception as e:
        return None, "🚨 Eroare conexiune ANAF. Te rugăm să introduci datele manual."

# Callback Functions for Filters
def reset_raw_filters_callback():
    for k in ["f_raw_code", "f_raw_name", "f_raw_sub", "f_raw_supp", "f_raw_uom"]: st.session_state[k] = "All Sub-Groups" if "sub" in k else ("All Suppliers" if "supp" in k else ("All UoMs" if "uom" in k else ""))

def reset_buy_filters_callback():
    for k in ["f_buy_code", "f_buy_name", "f_buy_supp"]: st.session_state[k] = "All Suppliers" if "supp" in k else ""

def reset_fg_filters_callback():
    for k in ["f_fg_code", "f_fg_name", "f_fg_cat"]: st.session_state[k] = "All Categories" if "cat" in k else ""

# DIALOG MODALS FOR BULK DELETE
@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_stock_dialog(item_ids):
    st.error(f"Are you sure you want to delete {len(item_ids)} item(s)? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn_dialog = get_db()
        cursor = conn_dialog.cursor()
        placeholders = ",".join(["?"] * len(item_ids))
        cursor.execute(f"DELETE FROM stock_items WHERE id IN ({placeholders})", item_ids)
        conn_dialog.commit(); st.success("Deleted!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_suppliers_dialog(item_ids):
    st.error(f"Are you sure you want to delete {len(item_ids)} supplier(s)? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn_dialog = get_db()
        cursor = conn_dialog.cursor()
        placeholders = ",".join(["?"] * len(item_ids))
        cursor.execute(f"DELETE FROM suppliers WHERE id IN ({placeholders})", item_ids)
        conn_dialog.commit(); st.success("Deleted!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_customers_dialog(item_ids):
    st.error(f"Are you sure you want to delete {len(item_ids)} customer(s)? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn_dialog = get_db()
        cursor = conn_dialog.cursor()
        placeholders = ",".join(["?"] * len(item_ids))
        cursor.execute(f"DELETE FROM customers WHERE id IN ({placeholders})", item_ids)
        conn_dialog.commit(); st.success("Deleted!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_facilities_dialog(item_ids):
    st.error(f"Are you sure you want to delete {len(item_ids)} facility(ies)? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn_dialog = get_db()
        cursor = conn_dialog.cursor()
        placeholders = ",".join(["?"] * len(item_ids))
        cursor.execute(f"DELETE FROM production_facilities WHERE id IN ({placeholders})", item_ids)
        conn_dialog.commit(); st.success("Deleted!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_operations_dialog(item_ids):
    st.error(f"Are you sure you want to delete {len(item_ids)} operation(s)? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn_dialog = get_db()
        cursor = conn_dialog.cursor()
        placeholders = ",".join(["?"] * len(item_ids))
        cursor.execute(f"DELETE FROM operations WHERE id IN ({placeholders})", item_ids)
        conn_dialog.commit(); st.success("Deleted!"); st.rerun()

@st.dialog("⚠️ Confirm Bulk Delete")
def bulk_delete_boms_dialog(item_ids):
    st.error(f"Are you sure you want to delete {len(item_ids)} product recipe(s)? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True): st.rerun()
    if c2.button("Yes, Delete All", type="primary", use_container_width=True):
        conn_dialog = get_db()
        cursor = conn_dialog.cursor()
        placeholders = ",".join(["?"] * len(item_ids))
        cursor.execute(f"DELETE FROM product_boms WHERE id IN ({placeholders})", item_ids)
        conn_dialog.commit(); st.success("Deleted!"); st.rerun()

# HELPER TO SAFE EXTRACT IDS
def get_selected_ids(df, selected_rows):
    valid_ids = []
    if selected_rows:
        for idx in selected_rows:
            if 0 <= idx < len(df):
                valid_ids.append(int(df.iloc[idx]['ID']))
    return valid_ids

# ADVANCED PRODUCT ITEM CREATION DIALOG (MRPEASY MATCHING INTERFACE)
@st.dialog("➕ Create New Finished Product", width="large")
def create_finished_product_dialog():
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    
    auto_part_no = generate_unique_item_code(conn_dialog, "FINISHED GOOD")
    auto_barcode = f"BAR-{auto_part_no}"
    
    st.subheader("General Item Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Part No. / Uniq Number *", value=auto_part_no, disabled=True)
        
        # Copy Item Option
        df_existing_prods = pd.read_sql_query("""
            SELECT pb.id as bom_id, si.uniq_code, si.name 
            FROM product_boms pb 
            JOIN stock_items si ON pb.product_item_id = si.id 
            ORDER BY si.name
        """, conn_dialog)
        copy_dict = {f"{r['uniq_code']} - {r['name']}": r['bom_id'] for _, r in df_existing_prods.iterrows()}
        copy_options = ["None (Start from Scratch)"] + list(copy_dict.keys())
        selected_copy = st.selectbox("Copy BOM & Routing From Existing Item", copy_options)
        
        part_desc = st.text_input("Part Description *", placeholder="e.g. Scaun de birou ERGO-01")
        prod_group = st.selectbox("Product Group *", ["FINISHED GOOD", "SUBASSEMBLY", "PROTOTYPE / SAMPLE", "CUSTOM ORDER"])
        
        df_u = pd.read_sql_query("SELECT id, code, name FROM units ORDER BY code", conn_dialog)
        u_dict = {f"{r['code']} ({r['name']})": r['id'] for _, r in df_u.iterrows()}
        sel_uom = st.selectbox("Unit of Measurement *", list(u_dict.keys()))

    with col2:
        df_wh = pd.read_sql_query("SELECT id, name, location_type FROM warehouses ORDER BY name", conn_dialog)
        wh_dict = {f"{r['name']} [{r['location_type']}]": r['id'] for _, r in df_wh.iterrows()}
        sel_wh = st.selectbox("Default Storage Location (Customer Warehouse) *", list(wh_dict.keys()))
        
        df_cust = pd.read_sql_query("SELECT id, name FROM customers ORDER BY name", conn_dialog)
        cust_dict = {r['name']: r['id'] for _, r in df_cust.iterrows()}
        sel_cust = st.selectbox("Assigned Customer *", ["General / Stock Product"] + list(cust_dict.keys()))
        
        selling_p = st.number_input("Selling Price (€)", min_value=0.0, value=0.0, step=1.0)
        st.text_input("Barcode UPC-A/EAN-13 (Auto-Generated)", value=auto_barcode, disabled=True)

    st.divider()
    
    # Weight Calculation & Warning Section if Copying or Calculating
    calc_weight = 0.0
    missing_weights = []
    if selected_copy != "None (Start from Scratch)":
        src_bom_id = copy_dict[selected_copy]
        q_weight_check = """
            SELECT si.name, bm.quantity_required, si.specific_weight
            FROM bom_materials bm
            JOIN stock_items si ON bm.material_item_id = si.id
            WHERE bm.bom_id = ?
        """
        cursor.execute(q_weight_check, (src_bom_id,))
        mat_rows = cursor.fetchall()
        for m_name, qty, sp_w in mat_rows:
            if not sp_w or sp_w == 0.0:
                missing_weights.append(m_name)
            else:
                calc_weight += float(qty * sp_w)
                
        if missing_weights:
            st.warning(f"⚠️ Atenție: Următoarele materiale din rețeta copiată NU au greutatea specificată în stoc: **{', '.join(missing_weights)}**. Greutatea totală calculată poate fi incompletă!")
        else:
            st.info(f"⚖️ Greutatea totală calculată automat din BOM: **{calc_weight:.2f} kg**")
            
    if st.button("💾 Save Item & Build Recipe", type="primary", use_container_width=True):
        if part_desc.strip():
            # Anti duplicate check
            cursor.execute("SELECT id FROM stock_items WHERE name = ?", (part_desc.strip(),))
            if cursor.fetchone():
                st.warning(f"⚠️ Un produs cu denumirea '{part_desc.strip()}' există deja!")
            else:
                cust_id_val = cust_dict.get(sel_cust) if sel_cust != "General / Stock Product" else None
                cursor.execute("""
                    INSERT INTO stock_items (uniq_code, code, name, category, sub_group, customer_id, unit_id, warehouse_id, selling_price, specific_weight, weight_unit, barcode)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'kg', ?)
                """, (auto_part_no, auto_part_no, part_desc.strip(), prod_group, "Finished Goods", cust_id_val, u_dict[sel_uom], wh_dict[sel_wh], selling_p, calc_weight, auto_barcode))
                
                new_prod_id = cursor.lastrowid
                
                # Create Product BOM Record
                cursor.execute("INSERT INTO product_boms (product_item_id, customer_id, calculated_weight) VALUES (?, ?, ?)", (new_prod_id, cust_id_val, calc_weight))
                new_bom_id = cursor.lastrowid
                
                # COPY BOM & ROUTING IF SELECTED
                if selected_copy != "None (Start from Scratch)":
                    src_bom_id = copy_dict[selected_copy]
                    
                    # Copy materials
                    cursor.execute("SELECT material_item_id, quantity_required, unit_cost, total_cost FROM bom_materials WHERE bom_id = ?", (src_bom_id,))
                    for m_item, qty, u_c, t_c in cursor.fetchall():
                        cursor.execute("INSERT INTO bom_materials (bom_id, material_item_id, quantity_required, unit_cost, total_cost) VALUES (?, ?, ?, ?, ?)",
                                       (new_bom_id, m_item, qty, u_c, t_c))
                                       
                    # Copy operations
                    cursor.execute("SELECT operation_id, step_number, duration_hours, rate_applied, total_cost FROM bom_operations WHERE bom_id = ?", (src_bom_id,))
                    for op_id, step_n, dur, r_app, t_c in cursor.fetchall():
                        cursor.execute("INSERT INTO bom_operations (bom_id, operation_id, step_number, duration_hours, rate_applied, total_cost) VALUES (?, ?, ?, ?, ?, ?)",
                                       (new_bom_id, op_id, step_n, dur, r_app, t_c))
                                       
                    # Update totals
                    cursor.execute("SELECT SUM(total_cost) FROM bom_materials WHERE bom_id = ?", (new_bom_id,))
                    tot_m = cursor.fetchone()[0] or 0.0
                    cursor.execute("SELECT SUM(total_cost) FROM bom_operations WHERE bom_id = ?", (new_bom_id,))
                    tot_l = cursor.fetchone()[0] or 0.0
                    tot_p = tot_m + tot_l
                    
                    cursor.execute("UPDATE product_boms SET total_material_cost=?, total_labor_cost=?, total_production_cost=? WHERE id=?", (tot_m, tot_l, tot_p, new_bom_id))
                    cursor.execute("UPDATE stock_items SET purchase_price=? WHERE id=?", (tot_p, new_prod_id))

                conn_dialog.commit()
                st.success("Produs creat cu succes!"); st.rerun()
        else:
            st.warning("Te rugăm să introduci Part Description!")

# DIALOG MODAL POP-UP FOR PRODUCT RECIPES (BOM & ROUTING)
@st.dialog("➕ Edit Product BOM Recipe & Routing", width="large")
def manage_product_bom_dialog(selected_prod_id=None):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    
    # Load Finished Goods
    df_prods = pd.read_sql_query("SELECT id, uniq_code, code, name, customer_id FROM stock_items WHERE category IN ('FINISHED GOOD', 'SUBASSEMBLY') ORDER BY name", conn_dialog)
    if len(df_prods) == 0:
        st.warning("Please add Finished Goods in Stock before creating BOM Recipes!")
        return
        
    prod_dict = {f"{r['uniq_code']} - {r['name']}": r['id'] for _, r in df_prods.iterrows()}
    
    idx_prod = 0
    if selected_prod_id:
        curr_keys = [k for k, v in prod_dict.items() if v == selected_prod_id]
        if curr_keys: idx_prod = list(prod_dict.keys()).index(curr_keys[0])

    sel_prod_key = st.selectbox("Select Product (Finished Good) *", list(prod_dict.keys()), index=idx_prod)
    target_prod_id = prod_dict[sel_prod_key]

    # Load Customer
    df_cust = pd.read_sql_query("SELECT id, name FROM customers ORDER BY name", conn_dialog)
    cust_dict = {r['name']: r['id'] for _, r in df_cust.iterrows()}
    
    cursor.execute("SELECT customer_id FROM stock_items WHERE id = ?", (target_prod_id,))
    row_c = cursor.fetchone()
    curr_c_id = row_c[0] if row_c else None
    c_keys = ["General / Stock Product"] + list(cust_dict.keys())
    curr_c_name = [k for k, v in cust_dict.items() if v == curr_c_id]
    sel_cust_name = st.selectbox("Assigned Customer *", c_keys, index=c_keys.index(curr_c_name[0]) if curr_c_name else 0)

    # Fetch or Create BOM Master Record
    cursor.execute("SELECT id, total_material_cost, total_labor_cost, total_production_cost FROM product_boms WHERE product_item_id = ?", (target_prod_id,))
    bom_row = cursor.fetchone()
    if not bom_row:
        cursor.execute("INSERT INTO product_boms (product_item_id, customer_id) VALUES (?, ?)", (target_prod_id, cust_dict.get(sel_cust_name)))
        conn_dialog.commit()
        bom_id = cursor.lastrowid
    else:
        bom_id = bom_row[0]

    st.divider()
    
    # TABULAR BUILDER: MATERIALS & OPERATIONS
    t_mat, t_ops = st.tabs(["📦 Material Consumption (BOM)", "⚙️ Labor Operations (Routing)"])
    
    with t_mat:
        st.markdown("##### 1. Raw Materials & Buy Parts Required")
        df_all_mat = pd.read_sql_query("SELECT id, uniq_code, name, purchase_price, unit_id, specific_weight FROM stock_items WHERE category IN ('RAW MATERIAL', 'BUY PART') ORDER BY name", conn_dialog)
        mat_dict = {f"{r['uniq_code']} - {r['name']} ({r['purchase_price']} €)": r['id'] for _, r in df_all_mat.iterrows()}
        
        c_m1, c_m2, c_m3 = st.columns([5, 3, 2])
        with c_m1: add_mat_key = st.selectbox("Select Material Component", list(mat_dict.keys()), key="sel_bom_mat")
        with c_m2: add_mat_qty = st.number_input("Required Qty", min_value=0.001, value=1.0, step=0.1, key="num_bom_mat_qty")
        with c_m3:
            st.write(""); st.write("")
            if st.button("➕ Add Material", key="btn_add_mat", use_container_width=True):
                m_id = mat_dict[add_mat_key]
                cursor.execute("SELECT purchase_price FROM stock_items WHERE id = ?", (m_id,))
                price = cursor.fetchone()[0] or 0.0
                tot_c = float(price * add_mat_qty)
                cursor.execute("INSERT INTO bom_materials (bom_id, material_item_id, quantity_required, unit_cost, total_cost) VALUES (?, ?, ?, ?, ?)",
                               (bom_id, m_id, add_mat_qty, price, tot_c))
                conn_dialog.commit(); st.rerun()

        # Display Added Materials
        q_bm = """
            SELECT bm.id as ID, si.uniq_code as 'Code', si.name as 'Material Name', bm.quantity_required as 'Qty', u.code as 'UoM', bm.unit_cost as 'Price (€)', bm.total_cost as 'Total Cost (€)', si.specific_weight as 'Spec Weight'
            FROM bom_materials bm
            JOIN stock_items si ON bm.material_item_id = si.id
            JOIN units u ON si.unit_id = u.id
            WHERE bm.bom_id = ?
        """
        df_bm = pd.read_sql_query(q_bm, conn_dialog, params=[bom_id])
        if len(df_bm) > 0:
            st.dataframe(df_bm, use_container_width=True, hide_index=True, column_config={"Price (€)": st.column_config.NumberColumn("Price (€)", format="%.2f €"), "Total Cost (€)": st.column_config.NumberColumn("Total Cost (€)", format="%.2f €")})
            col_del_m1, _ = st.columns([3, 7])
            del_m_id = col_del_m1.selectbox("Select Row to Delete", df_bm['ID'].tolist(), key="sel_del_mat_row")
            if col_del_m1.button("🗑️ Remove Component", key="btn_del_mat"):
                cursor.execute("DELETE FROM bom_materials WHERE id = ?", (del_m_id,))
                conn_dialog.commit(); st.rerun()

    with t_ops:
        st.markdown("##### 2. Manufacturing Operations Routing")
        df_all_ops = pd.read_sql_query("SELECT id, uniq_code, name, rate_per_unit, cost_unit, is_outsourced FROM operations ORDER BY uniq_code", conn_dialog)
        op_dict = {f"{r['uniq_code']} - {r['name']} ({r['rate_per_unit']} € / {r['cost_unit']})": r['id'] for _, r in df_all_ops.iterrows()}
        
        c_o1, c_o2, c_o3 = st.columns([5, 3, 2])
        with c_o1: add_op_key = st.selectbox("Select Operation Step", list(op_dict.keys()), key="sel_bom_op")
        with c_o2: add_op_dur = st.number_input("Est. Duration / Qty (Hours/Pcs/m2)", min_value=0.01, value=0.5, step=0.1, key="num_bom_op_dur")
        with c_o3:
            st.write(""); st.write("")
            if st.button("➕ Add Operation Step", key="btn_add_op", use_container_width=True):
                o_id = op_dict[add_op_key]
                cursor.execute("SELECT rate_per_unit FROM operations WHERE id = ?", (o_id,))
                rate = cursor.fetchone()[0] or 0.0
                tot_c = float(rate * add_op_dur)
                cursor.execute("INSERT INTO bom_operations (bom_id, operation_id, duration_hours, rate_applied, total_cost) VALUES (?, ?, ?, ?, ?)",
                               (bom_id, o_id, add_op_dur, rate, tot_c))
                conn_dialog.commit(); st.rerun()

        q_bo = """
            SELECT bo.id as ID, o.uniq_code as 'Op Code', o.name as 'Operation Name', o.cost_unit as 'Unit', bo.duration_hours as 'Duration/Qty', bo.rate_applied as 'Rate (€)', bo.total_cost as 'Total Cost (€)'
            FROM bom_operations bo
            JOIN operations o ON bo.operation_id = o.id
            WHERE bo.bom_id = ?
        """
        df_bo = pd.read_sql_query(q_bo, conn_dialog, params=[bom_id])
        if len(df_bo) > 0:
            st.dataframe(df_bo, use_container_width=True, hide_index=True, column_config={"Rate (€)": st.column_config.NumberColumn("Rate (€)", format="%.2f €"), "Total Cost (€)": st.column_config.NumberColumn("Total Cost (€)", format="%.2f €")})
            col_del_o1, _ = st.columns([3, 7])
            del_o_id = col_del_o1.selectbox("Select Row to Delete", df_bo['ID'].tolist(), key="sel_del_op_row")
            if col_del_o1.button("🗑️ Remove Operation", key="btn_del_op"):
                cursor.execute("DELETE FROM bom_operations WHERE id = ?", (del_o_id,))
                conn_dialog.commit(); st.rerun()

    # Recalculate Totals & Weight
    cursor.execute("SELECT SUM(total_cost) FROM bom_materials WHERE bom_id = ?", (bom_id,))
    tot_mat_cost = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(total_cost) FROM bom_operations WHERE bom_id = ?", (bom_id,))
    tot_lab_cost = cursor.fetchone()[0] or 0.0
    
    tot_prod_cost = tot_mat_cost + tot_lab_cost

    # Weight Calculation Check
    calc_weight = 0.0
    missing_weights = []
    cursor.execute("SELECT si.name, bm.quantity_required, si.specific_weight FROM bom_materials bm JOIN stock_items si ON bm.material_item_id = si.id WHERE bm.bom_id = ?", (bom_id,))
    for m_name, qty, sp_w in cursor.fetchall():
        if not sp_w or sp_w == 0.0:
            missing_weights.append(m_name)
        else:
            calc_weight += float(qty * sp_w)

    st.divider()
    if missing_weights:
        st.warning(f"⚠️ Atenție: Componentele următoare NU au greutatea notată în stoc: **{', '.join(missing_weights)}**. Vă rugăm să le actualizați greutatea specfică în modulul Stock!")

    st.markdown("##### 📊 BOM Summary & Automatic Calculations")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total Material Cost", f"{tot_mat_cost:.2f} €")
    sc2.metric("Total Operations Cost", f"{tot_lab_cost:.2f} €")
    sc3.metric("TOTAL BOM COST", f"{tot_prod_cost:.2f} €")
    sc4.metric("Calculated Weight", f"{calc_weight:.2f} kg")

    if st.button("💾 Save Product Recipe & Update Costs", type="primary", use_container_width=True):
        c_id = cust_dict.get(sel_cust_name)
        cursor.execute("UPDATE product_boms SET customer_id=?, total_material_cost=?, total_labor_cost=?, total_production_cost=?, calculated_weight=? WHERE id=?",
                       (c_id, tot_mat_cost, tot_lab_cost, tot_prod_cost, calc_weight, bom_id))
        cursor.execute("UPDATE stock_items SET customer_id=?, purchase_price=?, specific_weight=? WHERE id=?", (c_id, tot_prod_cost, calc_weight, target_prod_id))
        conn_dialog.commit(); st.success("BOM Recipe successfully saved!"); st.rerun()

# DIALOG MODALS FOR PRODUCTION FACILITIES
@st.dialog("➕ Add Production Facility / Equipment")
def add_facility_dialog():
    conn_dialog = get_db()
    auto_fac_code = generate_unique_facility_code(conn_dialog)
    
    with st.form("add_facility_form"):
        st.subheader("Facility / Equipment Details")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Facility Code (Auto-Generated) *", value=auto_fac_code, disabled=True)
            f_name = st.text_input("Facility / Machine Name *", placeholder="e.g. Abkant Bystronic 150T")
            f_type = st.selectbox("Category / Type *", ["Laser Cutting", "Press Brake / Abkant", "Welding Station", "Powder Coating / Vopsitorie", "CNC Machining", "General Machine", "Manual Workstation"])
        with col2:
            f_brand = st.text_input("Brand / Model", placeholder="e.g. Trumpf TruLaser 3030")
            f_status = st.selectbox("Operational Status", ["Operational", "In Maintenance", "Standby / Idle", "Out of Service"])
            f_date = st.date_input("Next Maintenance Date")

        st.divider()
        if st.form_submit_button("💾 Save Facility", type="primary", use_container_width=True):
            if f_name.strip():
                cursor = conn_dialog.cursor()
                cursor.execute("SELECT id FROM production_facilities WHERE name = ?", (f_name.strip(),))
                if cursor.fetchone():
                    st.warning(f"⚠️ A facility with name '{f_name.strip()}' already exists!")
                else:
                    cursor.execute("INSERT INTO production_facilities (code, name, facility_type, brand_model, status, next_maintenance_date) VALUES (?, ?, ?, ?, ?, ?)",
                                   (auto_fac_code, f_name.strip(), f_type, f_brand.strip(), f_status, str(f_date)))
                    conn_dialog.commit(); st.success("Facility saved!"); st.rerun()
            else:
                st.warning("Please fill in Facility / Machine Name!")

@st.dialog("✏️ Edit Facility Details")
def edit_facility_dialog(fac_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT code, name, facility_type, brand_model, status, next_maintenance_date FROM production_facilities WHERE id = ?", (fac_id,))
    row = cursor.fetchone()
    if row:
        with st.form("edit_facility_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Facility Code (Read-Only) *", value=row[0], disabled=True)
                e_name = st.text_input("Facility / Machine Name *", value=row[1])
                types_opts = ["Laser Cutting", "Press Brake / Abkant", "Welding Station", "Powder Coating / Vopsitorie", "CNC Machining", "General Machine", "Manual Workstation"]
                e_type = st.selectbox("Category / Type *", types_opts, index=types_opts.index(row[2]) if row[2] in types_opts else 0)
            with col2:
                e_brand = st.text_input("Brand / Model", value=row[3] if row[3] else "")
                status_opts = ["Operational", "In Maintenance", "Standby / Idle", "Out of Service"]
                e_status = st.selectbox("Operational Status", status_opts, index=status_opts.index(row[4]) if row[4] in status_opts else 0)

            c_save, c_del = st.columns([8, 2])
            if c_save.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                cursor.execute("UPDATE production_facilities SET name=?, facility_type=?, brand_model=?, status=? WHERE id=?", 
                               (e_name.strip(), e_type, e_brand.strip(), e_status, fac_id))
                conn_dialog.commit(); st.success("Updated!"); st.rerun()
            if c_del.form_submit_button("🗑️ Delete", use_container_width=True):
                cursor.execute("DELETE FROM production_facilities WHERE id = ?", (fac_id,)); conn_dialog.commit(); st.success("Deleted!"); st.rerun()

# DIALOG MODALS FOR OPERATIONS
@st.dialog("➕ Add Manufacturing Operation")
def add_operation_dialog():
    conn_dialog = get_db()
    auto_op_code = generate_unique_operation_code(conn_dialog)
    
    df_fac = pd.read_sql_query("SELECT id, name, facility_type FROM production_facilities ORDER BY name", conn_dialog)
    fac_dict = {f"{r['name']} ({r['facility_type']})": r['id'] for _, r in df_fac.iterrows()}
    fac_options = ["No Equipment Assigned"] + list(fac_dict.keys())

    df_supp = pd.read_sql_query("SELECT id, name FROM suppliers ORDER BY name", conn_dialog)
    supp_dict = {r['name']: r['id'] for _, r in df_supp.iterrows()}
    supp_options = ["No Preferred Supplier"] + list(supp_dict.keys())

    st.subheader("Operation Characteristics")
    is_outsourced = st.toggle("🚚 Is Subcontracted / Outsourced Operation?", value=False)
    
    col1, col2 = st.columns(2)
    with col1:
        op_uniq = st.text_input("Operation Uniq Code (Auto-Generated) *", value=auto_op_code, disabled=True)
        op_name = st.text_input("Operation Name *", placeholder="e.g. Zincare termica sau Debitare laser teava")
        
        if not is_outsourced:
            selected_fac = st.selectbox("Assigned Facility / Equipment", fac_options)
            cost_unit = st.selectbox("Billing / Cost Unit *", ["Hour", "Sqm (m2)", "Pcs", "Meter"])
            rate_unit = st.number_input("Rate per Unit (€) *", min_value=0.0, value=25.0, step=1.0)
        else:
            selected_supp = st.selectbox("Preferred Outsourcing Supplier", supp_options)
            out_type = st.selectbox("Outsourcing Process Type *", ["Zincare Termica / Galvanizare", "Vopsire in Camp Electrostatic", "Strunjire CNC", "Frezare CNC", "Indoire / Bending", "Tratament Termic", "Debitare Externă", "General Subcontracting"])
            
    with col2:
        if not is_outsourced:
            prod_level = st.number_input("Productivity Level (1.0 = 100%, 0.9 = 90%) *", min_value=0.1, max_value=2.0, value=1.0, step=0.05)
            ops_val = st.number_input("Number of Operators *", min_value=1, value=1)
            hrs_per_op_val = st.number_input("Hours / Day per Operator *", min_value=1.0, max_value=24.0, value=8.0, step=0.5)
            
            calc_day = float(ops_val * hrs_per_op_val)
            calc_week = float(calc_day * 5.0)
            calc_month = float(calc_week * 4.0)

            st.markdown("##### Max Capacity Limits (Auto-Calculated)")
            max_day = st.number_input("Max Hours / Day (Total Workshop)", min_value=0.0, value=calc_day, step=0.5)
            max_week = st.number_input("Max Hours / Week", min_value=0.0, value=calc_week, step=1.0)
            max_month = st.number_input("Max Hours / Month", min_value=0.0, value=calc_month, step=5.0)
        else:
            cost_unit = st.selectbox("Billing Unit *", ["Pcs (per Bucată)", "Sqm (m2)", "Project / Lot", "kg"])
            rate_unit = st.number_input("Estimated Price / Unit (€) *", min_value=0.0, value=5.0, step=0.5)
            mat_supplied = st.radio("Material Provision *", ["CAN PROD (Material Asigurat de Noi)", "Supplier (Material Asigurat de Furnizor)"])

    st.divider()
    c_btn_save, c_btn_cancel = st.columns([8, 2])
    if c_btn_save.button("💾 Save Operation", type="primary", use_container_width=True):
        if op_name.strip():
            cursor = conn_dialog.cursor()
            cursor.execute("SELECT id FROM operations WHERE name = ?", (op_name.strip(),))
            if cursor.fetchone():
                st.warning(f"⚠️ An operation with the name '{op_name.strip()}' already exists!")
            else:
                if not is_outsourced:
                    fac_id = fac_dict.get(selected_fac) if selected_fac != "No Equipment Assigned" else None
                    cursor.execute("""
                        INSERT INTO operations (uniq_code, name, cost_unit, rate_per_unit, productivity_level, hours_per_operator, max_hours_day, max_hours_week, max_hours_month, operators_count, facility_id, is_outsourced)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """, (auto_op_code, op_name.strip(), cost_unit, rate_unit, prod_level, hrs_per_op_val, max_day, max_week, max_month, ops_val, fac_id))
                else:
                    supp_id = supp_dict.get(selected_supp) if selected_supp != "No Preferred Supplier" else None
                    mat_val = "CAN PROD" if "CAN PROD" in mat_supplied else "Supplier"
                    cursor.execute("""
                        INSERT INTO operations (uniq_code, name, cost_unit, rate_per_unit, is_outsourced, preferred_supplier_id, outsourcing_type, material_supplied_by)
                        VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                    """, (auto_op_code, op_name.strip(), cost_unit, rate_unit, supp_id, out_type, mat_val))
                
                conn_dialog.commit(); st.success("Operation saved!"); st.rerun()
        else:
            st.warning("Please fill in Operation Name!")

@st.dialog("✏️ Edit Operation Details")
def edit_operation_dialog(op_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT uniq_code, name, cost_unit, rate_per_unit, productivity_level, max_hours_day, max_hours_week, max_hours_month, operators_count, facility_id, hours_per_operator, is_outsourced, preferred_supplier_id, outsourcing_type, material_supplied_by FROM operations WHERE id = ?", (op_id,))
    row = cursor.fetchone()
    
    if row:
        is_outsourced_curr = bool(row[11])
        df_fac = pd.read_sql_query("SELECT id, name, facility_type FROM production_facilities ORDER BY name", conn_dialog)
        fac_dict = {f"{r['name']} ({r['facility_type']})": r['id'] for _, r in df_fac.iterrows()}
        fac_options = ["No Equipment Assigned"] + list(fac_dict.keys())
        
        df_supp = pd.read_sql_query("SELECT id, name FROM suppliers ORDER BY name", conn_dialog)
        supp_dict = {r['name']: r['id'] for _, r in df_supp.iterrows()}
        supp_options = ["No Preferred Supplier"] + list(supp_dict.keys())

        curr_fac_name = "No Equipment Assigned"
        if row[9]:
            curr_f = [k for k, v in fac_dict.items() if v == row[9]]
            if curr_f: curr_fac_name = curr_f[0]

        curr_supp_name = "No Preferred Supplier"
        if row[12]:
            curr_s = [k for k, v in supp_dict.items() if v == row[12]]
            if curr_s: curr_supp_name = curr_s[0]

        st.subheader("Edit Operation Characteristics")
        is_outsourced = st.toggle("🚚 Is Subcontracted / Outsourced Operation?", value=is_outsourced_curr)

        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Operation Uniq Code (Read-Only) *", value=row[0], disabled=True)
            e_name = st.text_input("Operation Name *", value=row[1])
            
            if not is_outsourced:
                e_fac = st.selectbox("Assigned Facility / Equipment", fac_options, index=fac_options.index(curr_fac_name) if curr_fac_name in fac_options else 0)
                units_list = ["Hour", "Sqm (m2)", "Pcs", "Meter"]
                e_unit = st.selectbox("Billing / Cost Unit *", units_list, index=units_list.index(row[2]) if row[2] in units_list else 0)
                e_rate = st.number_input("Rate per Unit (€) *", min_value=0.0, value=safe_float(row[3]))
            else:
                e_supp = st.selectbox("Preferred Outsourcing Supplier", supp_options, index=supp_options.index(curr_supp_name) if curr_supp_name in supp_options else 0)
                out_opts = ["Zincare Termica / Galvanizare", "Vopsire in Camp Electrostatic", "Strunjire CNC", "Frezare CNC", "Indoire / Bending", "Tratament Termic", "Debitare Externă", "General Subcontracting"]
                e_out_type = st.selectbox("Outsourcing Process Type *", out_opts, index=out_opts.index(row[13]) if row[13] in out_opts else 0)

        with col2:
            if not is_outsourced:
                e_prod = st.number_input("Productivity Level *", min_value=0.1, max_value=2.0, value=safe_float(row[4]))
                e_ops = st.number_input("Number of Operators *", min_value=1, value=int(row[8]) if row[8] else 1)
                e_hrs_per_op = st.number_input("Hours / Day per Operator *", min_value=1.0, max_value=24.0, value=safe_float(row[10]) if row[10] else 8.0, step=0.5)
                
                calc_day = float(e_ops * e_hrs_per_op)
                calc_week = float(calc_day * 5.0)
                calc_month = float(calc_week * 4.0)

                st.markdown("##### Max Capacity Limits")
                e_mday = st.number_input("Max Hours / Day (Total Workshop)", min_value=0.0, value=calc_day)
                e_mweek = st.number_input("Max Hours / Week", min_value=0.0, value=calc_week)
                e_mmonth = st.number_input("Max Hours / Month", min_value=0.0, value=calc_month)
            else:
                out_units = ["Pcs (per Bucată)", "Sqm (m2)", "Project / Lot", "kg"]
                e_unit = st.selectbox("Billing Unit *", out_units, index=out_units.index(row[2]) if row[2] in out_units else 0)
                e_rate = st.number_input("Estimated Price / Unit (€) *", min_value=0.0, value=safe_float(row[3]))
                mat_opts = ["CAN PROD (Material Asigurat de Noi)", "Supplier (Material Asigurat de Furnizor)"]
                curr_mat_idx = 0 if row[14] == "CAN PROD" else 1
                e_mat_supplied = st.radio("Material Provision *", mat_opts, index=curr_mat_idx)

        c_save, c_del = st.columns([8, 2])
        if c_save.button("💾 Save Changes", type="primary", use_container_width=True):
            if not is_outsourced:
                fac_id = fac_dict.get(e_fac) if e_fac != "No Equipment Assigned" else None
                cursor.execute("""
                    UPDATE operations SET name=?, cost_unit=?, rate_per_unit=?, productivity_level=?, hours_per_operator=?, max_hours_day=?, max_hours_week=?, max_hours_month=?, operators_count=?, facility_id=?, is_outsourced=0
                    WHERE id=?
                """, (e_name.strip(), e_unit, e_rate, e_prod, e_hrs_per_op, e_mday, e_mweek, e_mmonth, e_ops, fac_id, op_id))
            else:
                supp_id = supp_dict.get(e_supp) if e_supp != "No Preferred Supplier" else None
                mat_val = "CAN PROD" if "CAN PROD" in e_mat_supplied else "Supplier"
                cursor.execute("""
                    UPDATE operations SET name=?, cost_unit=?, rate_per_unit=?, is_outsourced=1, preferred_supplier_id=?, outsourcing_type=?, material_supplied_by=?
                    WHERE id=?
                """, (e_name.strip(), e_unit, e_rate, supp_id, e_out_type, mat_val, op_id))

            conn_dialog.commit(); st.success("Updated!"); st.rerun()
        if c_del.button("🗑️ Delete", use_container_width=True):
            cursor.execute("DELETE FROM operations WHERE id = ?", (op_id,)); conn_dialog.commit(); st.success("Deleted!"); st.rerun()

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
                si.uniq_code as 'Uniq Code', 
                si.name as 'Description', 
                si.category as 'Category', 
                COALESCE(c.name, 'General / Stock') as 'Assigned Customer',
                w.name as 'Virtual Storage Location',
                u.code as 'UoM', 
                si.specific_weight as 'Weight (kg)',
                si.purchase_price as 'BOM Cost (€)',
                si.selling_price as 'Selling Price (€)',
                si.barcode as 'Barcode'
            FROM stock_items si 
            LEFT JOIN units u ON si.unit_id = u.id 
            LEFT JOIN customers c ON si.customer_id = c.id
            LEFT JOIN warehouses w ON si.warehouse_id = w.id
            WHERE si.category IN ('FINISHED GOOD', 'SUBASSEMBLY')
        """
        params = []
        if f_fg_code: q_fin += " AND (si.code LIKE ? OR si.uniq_code LIKE ?)"; params.extend([f"%{f_fg_code}%", f"%{f_fg_code}%"])
        if f_fg_name: q_fin += " AND si.name LIKE ?"; params.append(f"%{f_fg_name}%")
        if f_fg_cat != "All Categories": q_fin += " AND si.category = ?"; params.append(f_fg_cat)

        df_fin = pd.read_sql_query(q_fin, conn, params=params)
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
        df_s = pd.read_sql_query("SELECT id as ID, code as Code, cui as 'CUI', name as 'Supplier Name', supplier_type as 'Supplier Type', contact_person as 'Contact Person', phone as Phone, email as Email, lead_time_days as 'Lead Time (Days)' FROM suppliers ORDER BY name", conn)
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
        st.markdown("##### Warehouses & Customer Virtual Storage")
        df_w = pd.read_sql_query("SELECT w.id as ID, w.code as Code, w.name as 'Warehouse Name', w.location_type as Type, COALESCE(c.name, 'Internal') as 'Owner Customer' FROM warehouses w LEFT JOIN customers c ON w.customer_id = c.id", conn)
        st.dataframe(df_w, use_container_width=True, hide_index=True)
        
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
        q_boms = """
            SELECT 
                b.id as ID,
                si.uniq_code as 'Product Code',
                si.name as 'Product Name',
                COALESCE(c.name, 'General / Stock Product') as 'Customer',
                b.calculated_weight as 'Weight (kg)',
                b.total_material_cost as 'Material Cost (€)',
                b.total_labor_cost as 'Operations Cost (€)',
                b.total_production_cost as 'Total BOM Cost (€)'
            FROM product_boms b
            JOIN stock_items si ON b.product_item_id = si.id
            LEFT JOIN customers c ON b.customer_id = c.id
            ORDER BY si.name
        """
        df_boms = pd.read_sql_query(q_boms, conn)
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
                        cursor_page.execute("SELECT product_item_id FROM product_boms WHERE id = ?", (selected_ids[0],))
                        p_row = cursor_page.fetchone()
                        if p_row and st.button("✏️ Edit Selected Recipe", use_container_width=True): 
                            manage_product_bom_dialog(p_row[0])
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
                o.uniq_code as 'Uniq Code',
                o.name as 'Operation Name',
                CASE 
                    WHEN o.is_outsourced = 1 THEN '🚚 OUTSOURCED (' || COALESCE(s.name, 'No Supplier') || ')'
                    ELSE COALESCE(f.name, 'Internal Machine')
                END as 'Execution Facility / Supplier',
                o.cost_unit as 'Cost Unit',
                o.rate_per_unit as 'Rate (€)',
                CASE WHEN o.is_outsourced = 1 THEN '-' ELSE CAST(o.productivity_level AS TEXT) END as 'Productivity',
                CASE WHEN o.is_outsourced = 1 THEN '-' ELSE CAST(o.operators_count AS TEXT) END as 'Operators',
                CASE WHEN o.is_outsourced = 1 THEN '-' ELSE CAST(o.max_hours_day AS TEXT) END as 'Max Hrs/Day'
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
        df_fac = pd.read_sql_query("SELECT id as ID, code as Code, name as 'Equipment Name', facility_type as 'Type', brand_model as 'Brand / Model', status as 'Status', next_maintenance_date as 'Next Maintenance' FROM production_facilities ORDER BY code", conn)
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
                o.uniq_code as 'Op Code',
                o.name as 'Operation Name',
                COALESCE(s.name, 'No Preferred Supplier') as 'Subcontractor / Supplier',
                o.outsourcing_type as 'Process Type',
                o.material_supplied_by as 'Material Provision',
                o.cost_unit as 'Billing Unit',
                o.rate_per_unit as 'Estimated Rate (€)'
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
                    ins, upd = import_mrpeasy_customers(pd.read_csv(csv_file))
                    st.success(f"Added: {ins}, Updated: {upd}"); st.rerun()
            
        st.write("")
        df_c = pd.read_sql_query("SELECT id as ID, code as Code, cui as 'CUI', name as 'Customer Name', reg_com as 'Reg. Com.', contact_person as 'Contact Person', phone as Phone, email as Email FROM customers ORDER BY name", conn)
        
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
