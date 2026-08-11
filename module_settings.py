import streamlit as st
import pandas as pd
from dialogs_settings import add_category_dialog, add_subgroup_dialog, add_unit_dialog

def render_settings_page(conn, active_subtab_settings):
    subtabs_html = '<div class="mrp-subtabs">'
    for t_k, t_l in [("Categories", "📂 Categories"), ("Subgroups", "📑 Sub-Groups"), ("Units", "📏 Units"), ("Users", "👥 Users & Roles")]:
        subtabs_html += f'<a href="?page=Settings&subtab={t_k}" target="_self" class="{"mrp-subtab-active" if active_subtab_settings == t_k else "mrp-subtab"}">{t_l}</a>'
    st.markdown(subtabs_html + '</div>', unsafe_allow_html=True)
    
    if active_subtab_settings == "Categories":
        c_head, c_btn = st.columns([8, 2])
        with c_head: st.markdown("##### Product & Item Categories")
        with c_btn:
            if st.button("➕ Add Category", type="primary", use_container_width=True): add_category_dialog()
        df_cat = pd.read_sql_query("SELECT id as ID, name as Category, description as Description FROM item_categories ORDER BY name", conn)
        st.dataframe(df_cat, use_container_width=True, hide_index=True)
        
    elif active_subtab_settings == "Subgroups":
        c_head, c_btn = st.columns([8, 2])
        with c_head: st.markdown("##### Item Sub-Groups")
        with c_btn:
            if st.button("➕ Add Sub-Group", type="primary", use_container_width=True): add_subgroup_dialog()
        df_sub = pd.read_sql_query("SELECT id as ID, name as \"Sub-Group\", description as Description FROM item_subgroups ORDER BY name", conn)
        st.dataframe(df_sub, use_container_width=True, hide_index=True)

    elif active_subtab_settings == "Units":
        c_head, c_btn = st.columns([8, 2])
        with c_head: st.markdown("##### Units of Measure")
        with c_btn:
            if st.button("➕ Add Unit", type="primary", use_container_width=True): add_unit_dialog()
        df_u = pd.read_sql_query("SELECT id as ID, code as Code, name as \"Unit Name\" FROM units ORDER BY code", conn)
        st.dataframe(df_u, use_container_width=True, hide_index=True)

    elif active_subtab_settings == "Users":
        st.markdown("##### 👥 System Users & Roles")
        st.info("Aici vom implementa crearea utilizatorilor, setarea parolelor și asignarea rolurilor (ex: Admin, Vânzări, Producție).")
        df_users = pd.read_sql_query("SELECT id as ID, username as Username, role as Role, is_active as \"Active Account\" FROM users ORDER BY username", conn)
        st.dataframe(df_users, use_container_width=True, hide_index=True)
