import streamlit as st
from db import get_db, generate_unique_customer_code
from dialogs_utils import fetch_anaf_data

@st.dialog("➕ Add New Supplier")
def add_supplier_dialog():
    conn_dialog = get_db()
    st.subheader("🔍 Auto-Complete via ANAF API")
    col_anaf1, col_anaf2 = st.columns([3, 1])
    with col_anaf1: search_cui = st.text_input("CUI (RO...)", key="s_cui_input")
    with col_anaf2:
        st.write(""); st.write("")
        if st.button("Search ANAF", use_container_width=True):
            if search_cui:
                with st.spinner('Se caută...'):
                    data, err = fetch_anaf_data(search_cui)
                if data:
                    st.session_state['s_anaf_name'] = data['name']; st.session_state['s_anaf_address'] = data['address']
                    st.session_state['s_anaf_reg'] = data['reg_com']; st.session_state['s_anaf_cui'] = search_cui
                    st.success("Date descărcate!")
                else: st.error(err)
    st.divider()
    with st.form("add_supplier_form"):
        col1, col2 = st.columns(2)
        with col1:
            s_code = st.text_input("Supplier Internal Code *", placeholder="e.g. SUP003")
            s_cui = st.text_input("CUI / Tax ID *", value=st.session_state.get('s_anaf_cui', ''))
            s_name = st.text_input("Supplier Name *", value=st.session_state.get('s_anaf_name', ''))
            s_reg = st.text_input("Reg. Com. (J.../...)", value=st.session_state.get('s_anaf_reg', ''))
            s_type = st.selectbox("Type of Supplier *", ["Raw Material Supplier", "Buy Parts Supplier", "General / Both"])
            s_address = st.text_area("Address", value=st.session_state.get('s_anaf_address', ''), height=105)
        with col2:
            s_contact = st.text_input("Contact Person")
            s_phone = st.text_input("Phone Number")
            s_email = st.text_input("E-mail Address")
            s_lt = st.number_input("Lead Time (Days)", min_value=0, value=3)
            st.markdown("##### Banking Details")
            s_iban = st.text_input("IBAN")
            s_bank = st.text_input("Bank Name")

        if st.form_submit_button("💾 Save Supplier", type="primary", use_container_width=True):
            if s_code and s_name:
                cursor = conn_dialog.cursor()
                cursor.execute("SELECT id FROM suppliers WHERE code = %s OR name = %s", (s_code.strip(), s_name.strip()))
                if cursor.fetchone(): st.warning("⚠️ Exists!")
                else:
                    cursor.execute("INSERT INTO suppliers (code, name, supplier_type, contact_person, phone, email, lead_time_days, cui, reg_com, address, iban, bank_name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                                                (s_code.strip(), s_name.strip(), s_type, s_contact.strip(), s_phone.strip(), s_email.strip(), s_lt, s_cui.strip(), s_reg.strip(), s_address.strip(), s_iban.strip(), s_bank.strip()))
                    conn_dialog.commit(); st.success("Saved!"); st.rerun()

@st.dialog("⚙️ Edit Supplier Details")
def edit_supplier_dialog(supp_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT code, name, supplier_type, contact_person, phone, email, lead_time_days, cui, reg_com, address, iban, bank_name FROM suppliers WHERE id = %s", (supp_id,))
    row = cursor.fetchone()
    if row:
        with st.form("edit_supplier_form"):
            col1, col2 = st.columns(2)
            with col1:
                e_code = st.text_input("Code *", value=row[0])
                e_cui = st.text_input("CUI", value=row[7] if row[7] else "")
                e_name = st.text_input("Name *", value=row[1])
                e_reg = st.text_input("Reg. Com.", value=row[8] if row[8] else "")
                e_type = st.selectbox("Type", ["Raw Material Supplier", "Buy Parts Supplier", "General / Both"], index=["Raw Material Supplier", "Buy Parts Supplier", "General / Both"].index(row[2]) if row[2] in ["Raw Material Supplier", "Buy Parts Supplier", "General / Both"] else 0)
                e_address = st.text_area("Address", value=row[9] if row[9] else "", height=105)
            with col2:
                e_contact = st.text_input("Contact Person", value=row[3] if row[3] else "")
                e_phone = st.text_input("Phone", value=row[4] if row[4] else "")
                e_email = st.text_input("Email", value=row[5] if row[5] else "")
                e_lt = st.number_input("Lead Time", min_value=0, value=int(row[6]))
                st.markdown("##### Banking Details")
                e_iban = st.text_input("IBAN", value=row[10] if row[10] else "")
                e_bank = st.text_input("Bank Name", value=row[11] if row[11] else "")

            c_save, c_del = st.columns([8, 2])
            if c_save.form_submit_button("💾 Save", type="primary", use_container_width=True):
                cursor.execute("UPDATE suppliers SET code=%s, name=%s, supplier_type=%s, contact_person=%s, phone=%s, email=%s, lead_time_days=%s, cui=%s, reg_com=%s, address=%s, iban=%s, bank_name=%s WHERE id=%s", 
                               (e_code, e_name, e_type, e_contact, e_phone, e_email, e_lt, e_cui, e_reg, e_address, e_iban, e_bank, supp_id))
                conn_dialog.commit(); st.success("Updated!"); st.rerun()
            if c_del.form_submit_button("🗑️ Delete", use_container_width=True):
                cursor.execute("DELETE FROM suppliers WHERE id = %s", (supp_id,)); conn_dialog.commit(); st.success("Deleted!"); st.rerun()

@st.dialog("➕ Add New Customer")
def add_customer_dialog():
    conn_dialog = get_db()
    auto_cust_code = generate_unique_customer_code(conn_dialog)
    st.subheader("🔍 Auto-Complete via ANAF API")
    col_anaf1, col_anaf2 = st.columns([3, 1])
    with col_anaf1: search_cui = st.text_input("CUI (RO...)", key="c_cui_input")
    with col_anaf2:
        st.write(""); st.write("")
        if st.button("Search ANAF", key="btn_c_anaf", use_container_width=True):
            if search_cui:
                with st.spinner('Se caută...'):
                    data, err = fetch_anaf_data(search_cui)
                if data:
                    st.session_state['c_anaf_name'] = data['name']; st.session_state['c_anaf_address'] = data['address']
                    st.session_state['c_anaf_reg'] = data['reg_com']; st.session_state['c_anaf_cui'] = search_cui
                    st.success("Date descărcate!")
                else: st.error(err)
    st.divider()
    with st.form("add_customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Code *", value=auto_cust_code, disabled=True)
            c_cui = st.text_input("CUI", value=st.session_state.get('c_anaf_cui', ''))
            c_name = st.text_input("Name *", value=st.session_state.get('c_anaf_name', ''))
            c_reg = st.text_input("Reg. Com.", value=st.session_state.get('c_anaf_reg', ''))
            c_address = st.text_area("Address", value=st.session_state.get('c_anaf_address', ''), height=105)
        with col2:
            c_contact = st.text_input("Contact Person")
            c_phone = st.text_input("Phone Number")
            c_email = st.text_input("E-mail Address")
            st.markdown("##### Banking Details")
            c_iban = st.text_input("IBAN")
            c_bank = st.text_input("Bank Name")

        if st.form_submit_button("💾 Save Customer", type="primary", use_container_width=True):
            if c_name.strip():
                cursor = conn_dialog.cursor()
                cursor.execute("INSERT INTO customers (code, name, cui, reg_com, address, iban, bank_name, contact_person, phone, email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id", 
                                            (auto_cust_code, c_name.strip(), c_cui.strip(), c_reg.strip(), c_address.strip(), c_iban.strip(), c_bank.strip(), c_contact.strip(), c_phone.strip(), c_email.strip()))
                new_c_id = cursor.fetchone()[0]
                wh_code = f"WH-CUST-{new_c_id:03d}"
                cursor.execute("INSERT INTO warehouses (code, name, location_type, customer_id) VALUES (%s, %s, 'Customer Virtual Storage', %s)", (wh_code, c_name.strip(), new_c_id))
                conn_dialog.commit(); st.success("Saved!"); st.rerun()

@st.dialog("⚙️ Edit Customer Details")
def edit_customer_dialog(cust_id):
    conn_dialog = get_db()
    cursor = conn_dialog.cursor()
    cursor.execute("SELECT code, name, cui, reg_com, address, iban, bank_name, contact_person, phone, email FROM customers WHERE id = %s", (cust_id,))
    row = cursor.fetchone()
    if row:
        with st.form("edit_customer_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Code *", value=row[0], disabled=True)
                e_cui = st.text_input("CUI", value=row[2] if row[2] else "")
                e_name = st.text_input("Name *", value=row[1])
                e_reg = st.text_input("Reg. Com.", value=row[3] if row[3] else "")
                e_address = st.text_area("Address", value=row[4] if row[4] else "", height=105)
            with col2:
                e_contact = st.text_input("Contact Person", value=row[7] if row[7] else "")
                e_phone = st.text_input("Phone", value=row[8] if row[8] else "")
                e_email = st.text_input("Email", value=row[9] if row[9] else "")
                st.markdown("##### Banking Details")
                e_iban = st.text_input("IBAN", value=row[5] if row[5] else "")
                e_bank = st.text_input("Bank Name", value=row[6] if row[6] else "")

            c_save, c_del = st.columns([8, 2])
            if c_save.form_submit_button("💾 Save", type="primary", use_container_width=True):
                cursor.execute("UPDATE customers SET name=%s, cui=%s, reg_com=%s, address=%s, iban=%s, bank_name=%s, contact_person=%s, phone=%s, email=%s WHERE id=%s", 
                               (e_name.strip(), e_cui.strip(), e_reg.strip(), e_address.strip(), e_iban.strip(), e_bank.strip(), e_contact.strip(), e_phone.strip(), e_email.strip(), cust_id))
                cursor.execute("UPDATE warehouses SET name=%s WHERE customer_id=%s", (e_name.strip(), cust_id))
                conn_dialog.commit(); st.success("Updated!"); st.rerun()
            if c_del.form_submit_button("🗑️ Delete", use_container_width=True):
                cursor.execute("DELETE FROM customers WHERE id = %s", (cust_id,)); conn_dialog.commit(); st.success("Deleted!"); st.rerun()
