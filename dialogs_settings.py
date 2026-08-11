import streamlit as st
from db import get_db

@st.dialog("➕ Add New Category")
def add_category_dialog():
    conn_dialog = get_db()
    with st.form("add_cat_form"):
        c_name = st.text_input("Category Name *", placeholder="e.g. PACKAGING")
        c_desc = st.text_area("Description")
        if st.form_submit_button("💾 Save Category", type="primary", use_container_width=True):
            if c_name.strip():
                cursor = conn_dialog.cursor()
                cursor.execute("INSERT INTO item_categories (name, description) VALUES (%s, %s) ON CONFLICT DO NOTHING", (c_name.strip().upper(), c_desc.strip()))
                conn_dialog.commit(); st.success("Saved!"); st.rerun()

@st.dialog("➕ Add New Sub-Group")
def add_subgroup_dialog():
    conn_dialog = get_db()
    with st.form("add_sub_form"):
        s_name = st.text_input("Sub-Group Name *", placeholder="e.g. Suruburi")
        s_desc = st.text_area("Description")
        if st.form_submit_button("💾 Save Sub-Group", type="primary", use_container_width=True):
            if s_name.strip():
                cursor = conn_dialog.cursor()
                cursor.execute("INSERT INTO item_subgroups (name, description) VALUES (%s, %s) ON CONFLICT DO NOTHING", (s_name.strip(), s_desc.strip()))
                conn_dialog.commit(); st.success("Saved!"); st.rerun()

@st.dialog("➕ Add Unit of Measure")
def add_unit_dialog():
    conn_dialog = get_db()
    with st.form("add_uom_form"):
        u_code = st.text_input("Unit Code *", placeholder="e.g. ml")
        u_name = st.text_input("Full Name", placeholder="e.g. Metru liniar")
        if st.form_submit_button("💾 Save Unit", type="primary", use_container_width=True):
            if u_code.strip():
                cursor = conn_dialog.cursor()
                cursor.execute("INSERT INTO units (code, name) VALUES (%s, %s) ON CONFLICT DO NOTHING", (u_code.strip(), u_name.strip()))
                conn_dialog.commit(); st.success("Saved!"); st.rerun()
