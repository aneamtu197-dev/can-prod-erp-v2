import streamlit as st
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
import re

def get_db_url():
    """Obține URL-ul din Secrets și asigură configurarea SSL."""
    try:
        url = st.secrets["postgres"]["url"]
        if "sslmode" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=require"
        return url
    except Exception:
        st.error("🚨 Nu s-a găsit cheia 'url' în Streamlit Cloud Secrets! Verifică secțiunea Secrets.")
        st.stop()

def get_db_engine():
    """Returnează un engine SQLAlchemy configurat pentru PostgreSQL."""
    url = get_db_url()
    return create_engine(
        url, 
        pool_pre_ping=True
    )

def get_db():
    """Returnează o conexiune directă psycopg2."""
    try:
        url = get_db_url()
        conn = psycopg2.connect(url)
        return conn
    except Exception as e:
        st.error(f"🚨 Eroare la conexiunea Supabase: {e}")
        st.stop()

def init_custom_db():
    """Creează structura de tabele în Supabase PostgreSQL la prima rulare."""
    engine = get_db_engine()
    with engine.begin() as conn:
        # --- SUPPLIERS TABLE ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            supplier_type VARCHAR(100) DEFAULT 'Raw Material Supplier',
            cui VARCHAR(50),
            reg_com VARCHAR(50),
            address TEXT,
            iban VARCHAR(100),
            bank_name VARCHAR(100),
            contact_person VARCHAR(255),
            phone VARCHAR(100),
            email VARCHAR(255),
            lead_time_days INTEGER DEFAULT 0
        );
        """))

        # --- CUSTOMERS TABLE ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            cui VARCHAR(50),
            reg_com VARCHAR(50),
            address TEXT,
            iban VARCHAR(100),
            bank_name VARCHAR(100),
            contact_person VARCHAR(255),
            phone VARCHAR(100),
            email VARCHAR(255)
        );
        """))

        # --- PRODUCTION FACILITIES ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS production_facilities (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            facility_type VARCHAR(100) DEFAULT 'Machine',
            brand_model VARCHAR(255),
            status VARCHAR(50) DEFAULT 'Operational',
            next_maintenance_date VARCHAR(50)
        );
        """))

        # --- OPERATIONS TABLE ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS operations (
            id SERIAL PRIMARY KEY,
            uniq_code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            cost_unit VARCHAR(20) DEFAULT 'Hour',
            rate_per_unit REAL DEFAULT 0.0,
            productivity_level REAL DEFAULT 1.0,
            hours_per_operator REAL DEFAULT 8.0,
            max_hours_day REAL DEFAULT 8.0,
            max_hours_week REAL DEFAULT 40.0,
            max_hours_month REAL DEFAULT 160.0,
            operators_count INTEGER DEFAULT 1,
            facility_id INTEGER REFERENCES production_facilities(id) ON DELETE SET NULL,
            is_outsourced INTEGER DEFAULT 0,
            preferred_supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
            outsourcing_type VARCHAR(100),
            material_supplied_by VARCHAR(50) DEFAULT 'CAN PROD'
        );
        """))

        # --- UNITS TABLE ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS units (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL
        );
        """))

        # --- WAREHOUSES TABLE ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS warehouses (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            location_type VARCHAR(100) DEFAULT 'Internal Warehouse',
            customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE
        );
        """))

        # --- STOCK ITEMS TABLE ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS stock_items (
            id SERIAL PRIMARY KEY,
            uniq_code VARCHAR(100),
            code VARCHAR(100) NOT NULL,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(50) DEFAULT 'RAW MATERIAL',
            sub_group VARCHAR(100) DEFAULT 'General',
            supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
            unit_id INTEGER NOT NULL REFERENCES units(id),
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
            purchase_price REAL DEFAULT 0.0,
            selling_price REAL DEFAULT 0.0,
            specific_weight REAL DEFAULT 0.0,
            weight_unit VARCHAR(20) DEFAULT 'kg',
            current_stock REAL DEFAULT 0.0,
            min_stock REAL DEFAULT 0.0,
            customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
            barcode VARCHAR(100)
        );
        """))

        # --- PRODUCT BOMS (MASTER RECIPE) ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS product_boms (
            id SERIAL PRIMARY KEY,
            product_item_id INTEGER UNIQUE NOT NULL REFERENCES stock_items(id) ON DELETE CASCADE,
            customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
            total_material_cost REAL DEFAULT 0.0,
            total_labor_cost REAL DEFAULT 0.0,
            total_production_cost REAL DEFAULT 0.0,
            calculated_weight REAL DEFAULT 0.0,
            markup_percent REAL DEFAULT 0.0
        );
        """))

        # --- BOM MATERIAL COMPONENTS ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS bom_materials (
            id SERIAL PRIMARY KEY,
            bom_id INTEGER NOT NULL REFERENCES product_boms(id) ON DELETE CASCADE,
            material_item_id INTEGER NOT NULL REFERENCES stock_items(id),
            quantity_required REAL DEFAULT 0.0,
            unit_cost REAL DEFAULT 0.0,
            total_cost REAL DEFAULT 0.0
        );
        """))

        # --- BOM OPERATIONS ROUTING ---
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS bom_operations (
            id SERIAL PRIMARY KEY,
            bom_id INTEGER NOT NULL REFERENCES product_boms(id) ON DELETE CASCADE,
            operation_id INTEGER NOT NULL REFERENCES operations(id),
            step_number INTEGER DEFAULT 1,
            duration_hours REAL DEFAULT 0.0,
            rate_applied REAL DEFAULT 0.0,
            total_cost REAL DEFAULT 0.0
        );
        """))

        # POPULATE DEFAULT UNITS
        res_u = conn.execute(text("SELECT COUNT(*) FROM units")).fetchone()[0]
        if res_u == 0:
            for c, n in [('pcs', 'Pieces'), ('kg', 'Kilograms'), ('Ml', 'Linear Meters'), ('m2', 'Square Meters'), ('l', 'Liters')]:
                conn.execute(text("INSERT INTO units (code, name) VALUES (:c, :n) ON CONFLICT DO NOTHING"), {"c": c, "n": n})

        # POPULATE DEFAULT WAREHOUSES
        res_w = conn.execute(text("SELECT COUNT(*) FROM warehouses")).fetchone()[0]
        if res_w == 0:
            for c, n, t in [('WH-MAIN', 'Main Central Warehouse', 'Internal Warehouse'), ('WH-FINISHED', 'Finished Goods Storage', 'Internal Warehouse')]:
                conn.execute(text("INSERT INTO warehouses (code, name, location_type) VALUES (:c, :n, :t) ON CONFLICT DO NOTHING"), {"c": c, "n": n, "t": t})

        auto_create_customer_warehouses_pg(conn)

def auto_create_customer_warehouses_pg(conn):
    custs = conn.execute(text("SELECT id, code, name FROM customers")).fetchall()
    for c_id, c_code, c_name in custs:
        wh_code = f"WH-CUST-{c_id:03d}"
        wh_name = c_name.strip()
        existing = conn.execute(text("SELECT id FROM warehouses WHERE customer_id = :cid"), {"cid": c_id}).fetchone()
        if not existing:
            conn.execute(text("INSERT INTO warehouses (code, name, location_type, customer_id) VALUES (:wcode, :wname, 'Customer Virtual Storage', :cid)"),
                         {"wcode": wh_code, "wname": wh_name, "cid": c_id})
        else:
            conn.execute(text("UPDATE warehouses SET name = :wname WHERE id = :wid"), {"wname": wh_name, "wid": existing[0]})

def generate_unique_item_code(db_conn, category, sub_group=""):
    cursor = db_conn.cursor()
    cat_upper = category.upper()
    if 'RAW' in cat_upper:
        if sub_group == 'Tabla': prefix = 'RM-TB-'
        elif sub_group == 'Teava': prefix = 'RM-TV-'
        elif sub_group == 'Europrofile': prefix = 'RM-EP-'
        else: prefix = 'RM-GEN-'
    elif 'BUY' in cat_upper: prefix = 'BP-'
    elif 'FINISHED' in cat_upper or 'SUB' in cat_upper or 'PRODUSE' in cat_upper: prefix = 'A0'
    else: prefix = 'ITM-'

    cursor.execute("SELECT uniq_code, code FROM stock_items WHERE uniq_code LIKE %s OR code LIKE %s", (f"{prefix}%", f"{prefix}%"))
    max_num = 0
    for (uc, c_val) in cursor.fetchall():
        for check_val in [uc, c_val]:
            if check_val and check_val.startswith(prefix):
                num_part = check_val.replace(prefix, '')
                if num_part.isdigit(): max_num = max(max_num, int(num_part))
            
    next_num = max_num + 1 if max_num > 0 else (1920 if prefix == 'A0' else 1)
    return f"A0{next_num:04d}" if prefix == 'A0' else f"{prefix}{next_num:04d}"

def generate_unique_customer_code(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT code FROM customers WHERE code LIKE 'CU%'")
    rows = cursor.fetchall()
    max_num = 0
    for (c_val,) in rows:
        if c_val and c_val.startswith('CU'):
            num_part = c_val.replace('CU', '')
            if num_part.isdigit():
                max_num = max(max_num, int(num_part))
    next_num = max_num + 1
    return f"CU{next_num:05d}"

def generate_unique_facility_code(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT code FROM production_facilities WHERE code LIKE 'EQ-%'")
    rows = cursor.fetchall()
    max_num = 0
    for (c_val,) in rows:
        if c_val and c_val.startswith('EQ-'):
            num_part = c_val.replace('EQ-', '')
            if num_part.isdigit():
                max_num = max(max_num, int(num_part))
    next_num = max_num + 1
    return f"EQ-{next_num:04d}"

def generate_unique_operation_code(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT uniq_code FROM operations WHERE uniq_code LIKE 'OP-%'")
    rows = cursor.fetchall()
    max_num = 0
    for (c_val,) in rows:
        if c_val and c_val.startswith('OP-'):
            num_part = c_val.replace('OP-', '')
            if num_part.isdigit():
                max_num = max(max_num, int(num_part))
    next_num = max_num + 1
    return f"OP-{next_num:04d}"

def clean_and_classify_item(part_no, desc, group_num):
    text_upper = f"{part_no} {desc}".upper()
    buy_keywords = ['PIULITA', 'SURUB', 'SAIBA', 'CONEXPAND', 'CAPAC', 'TREPTA', 'ZINCAT 1000X', 'PICIOR', 'POLICARBONAT', 'MANA CURENTA', 'CUTIE', 'M8_', 'M10_', 'M12_', 'M8X', 'M10X', 'M12X', 'ANCORA', 'FOLIE', 'T35 X 0.5MM', 'A00891', 'A00755', 'A00625']

    if group_num == 'PRODUSE FINITE' or ('A00' in part_no and group_num == 'PRODUSE FINITE') or ('A01' in part_no and group_num == 'PRODUSE FINITE'):
        return 'PRODUSE FINITE', 'FINISHED GOOD', f"{part_no} - {desc}"
    elif group_num == 'BUY PARTS' or any(k in text_upper for k in buy_keywords):
        return 'Buy Parts', 'BUY PART', f"{part_no} - {desc}"
    else:
        europrofile_keywords = ['UPN', 'UNP', 'UPE', 'IPE', 'HEA', 'HEB', 'CORNIER', 'BARA', 'ROTUND', 'PATRAT', 'LAT', 'PLATBANDA', 'C 150X50', 'FI14', 'FI12', 'FI10', 'FI 25', 'FI 20', 'FI 8']
        if any(k in text_upper for k in europrofile_keywords) and not ('TEAVA' in text_upper or 'TV' in text_upper or 'ALU_' in text_upper):
            return 'Europrofile', 'RAW MATERIAL', f"{part_no} - {desc}"
        elif any(k in text_upper for k in ['TB', 'TABLA', 'STRIATA', 'DX51D', 'PL 100X10']):
            return 'Tabla', 'RAW MATERIAL', f"{part_no} - {desc}"
        elif any(k in text_upper for k in ['TV', 'TEAVA', 'TEVA', 'ALU_', 'FI 219', 'FI 220', 'FI27', 'FI 76', 'FI 48', 'FI 42', 'FI 33', 'FI 28', '88,9X2', '18X2_PRECIZI', 'A01349']) or re.search(r'^\d+x\d+x[\d\.,]+', part_no.lower()):
            return 'Teava', 'RAW MATERIAL', f"{part_no} - {desc}"
        else:
            return 'Raw Materials Diverse', 'RAW MATERIAL', f"{part_no} - {desc}".strip()

def import_mrpeasy_items(df):
    conn = get_db()
    cursor = conn.cursor()
    ins = 0; upd = 0
    df.columns = [str(col).strip().lower() for col in df.columns]

    for _, row in df.iterrows():
        orig_code = str(row.get('part no.', row.get('part number', row.get('code', '')))).strip()
        if not orig_code or orig_code == 'nan': continue
        raw_desc = str(row.get('part description', row.get('description', row.get('name', orig_code)))).strip()
        group_num = str(row.get('group number', row.get('group name', row.get('group', '')))).strip()
        sub_group, category, clean_name = clean_and_classify_item(orig_code, raw_desc, group_num)

        if orig_code.startswith('A0') and category == 'FINISHED GOOD': uniq_code = orig_code
        else: uniq_code = generate_unique_item_code(conn, category, sub_group)
        item_code = orig_code if orig_code and orig_code != 'nan' else uniq_code

        u_code = str(row.get('uom', 'pcs')).strip()
        cursor.execute("SELECT id FROM units WHERE code = %s", (u_code,))
        u_row = cursor.fetchone()
        if u_row: unit_id = u_row[0]
        else:
            cursor.execute("INSERT INTO units (code, name) VALUES (%s, %s) RETURNING id", (u_code, u_code))
            unit_id = cursor.fetchone()[0]

        w_name = str(row.get('default storage location', 'Main Warehouse')).strip()
        cursor.execute("SELECT id FROM warehouses WHERE name = %s", (w_name,))
        w_row = cursor.fetchone()
        if w_row: warehouse_id = w_row[0]
        else:
            cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (%s, %s, %s) RETURNING id", (f"WH-{w_name[:5].upper().replace(' ', '')}", w_name, 'Internal Warehouse'))
            warehouse_id = cursor.fetchone()[0]

        price = safe_float(row.get('cost', 0))
        sell_price = safe_float(row.get('selling price', 0))
        weight_val = safe_float(row.get('weight', 0))
        weight_unit = str(row.get('unit of weight', 'kg')).strip()
        stock = safe_float(row.get('in stock', 0))
        min_st = safe_float(row.get('reorder point', 0))

        cursor.execute("SELECT id FROM stock_items WHERE code = %s OR uniq_code = %s", (item_code, uniq_code))
        ex = cursor.fetchone()
        if ex:
            cursor.execute("""UPDATE stock_items SET uniq_code=%s, name=%s, category=%s, sub_group=%s, unit_id=%s, warehouse_id=%s, purchase_price=%s, selling_price=%s, specific_weight=%s, weight_unit=%s, current_stock=%s, min_stock=%s WHERE id=%s""", 
                           (uniq_code, clean_name, category, sub_group, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st, ex[0]))
            upd += 1
        else:
            cursor.execute("""INSERT INTO stock_items (uniq_code, code, name, category, sub_group, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                           (uniq_code, item_code, clean_name, category, sub_group, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st))
            ins += 1
    conn.commit()
    conn.close()
    return ins, upd

def import_mrpeasy_customers(df):
    conn = get_db()
    cursor = conn.cursor()
    ins = 0; upd = 0
    col_map = {str(col).strip().lower(): col for col in df.columns}

    for _, row in df.iterrows():
        def get_field(name_list):
            for n in name_list:
                if n in col_map:
                    val = str(row[col_map[n]]).strip()
                    if val and val.lower() != 'nan':
                        return val
            return ''

        code = get_field(['number', 'code', 'customer code'])
        name = get_field(['name', 'customer name', 'company name'])
        if not code or not name: continue

        val_reg = get_field(['reg. no.', 'reg. no', 'reg no', 'registration number'])
        val_vat = get_field(['tax/vat number', 'tax number', 'vat number', 'cui'])

        cui = ''; reg_com = ''
        for val in [val_reg, val_vat]:
            if not val or val.lower() in ['nan', 'xxxx', '0000000', 'none']: continue
            val_upper = val.upper()
            if 'J' in val_upper or 'F' in val_upper or '/' in val:
                if not reg_com: reg_com = val
            else:
                if not cui: cui = val

        address_parts = [get_field([c]) for c in ['address', 'city', 'country'] if get_field([c])]
        address = ", ".join(address_parts)
        fn = get_field(['first name']); ln = get_field(['last name'])
        contact_person = f"{fn} {ln}".strip()
        phone = get_field(['phone']); email = get_field(['e-mail', 'email'])

        cursor.execute("SELECT id FROM customers WHERE code = %s OR (cui != '' AND cui = %s)", (code, cui))
        ex = cursor.fetchone()
        if ex:
            cursor.execute("""
                UPDATE customers SET code=%s, name=%s, cui=%s, reg_com=%s, address=%s, contact_person=%s, phone=%s, email=%s
                WHERE id=%s
            """, (code, name, cui, reg_com, address, contact_person, phone, email, ex[0]))
            upd += 1
        else:
            cursor.execute("""
                INSERT INTO customers (code, name, cui, reg_com, address, contact_person, phone, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (code, name, cui, reg_com, address, contact_person, phone, email))
            ins += 1

    conn.commit()
    conn.close()
    return ins, upd

def safe_float(val):
    if val in (None, "", "nan", "NaN"): return 0.0
    try: return float(val)
    except: return 0.0
