import sqlite3
import pandas as pd
import re

def init_custom_db():
    conn = sqlite3.connect('can_prod_v2.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # --- SUPPLIERS TABLE ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    """)

    # --- CUSTOMERS TABLE ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    """)

    # --- PRODUCTION FACILITIES (EQUIPMENT / LOGISTICS) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS production_facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        facility_type VARCHAR(100) DEFAULT 'Machine',
        brand_model VARCHAR(255),
        status VARCHAR(50) DEFAULT 'Operational',
        next_maintenance_date VARCHAR(50)
    );
    """)

    # --- OPERATIONS TABLE ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        facility_id INTEGER,
        FOREIGN KEY (facility_id) REFERENCES production_facilities(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        location_type VARCHAR(100) DEFAULT 'Internal Warehouse'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uniq_code VARCHAR(100),
        code VARCHAR(100) NOT NULL,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(50) DEFAULT 'RAW MATERIAL',
        sub_group VARCHAR(100) DEFAULT 'General',
        supplier_id INTEGER,
        unit_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        purchase_price REAL DEFAULT 0.0,
        selling_price REAL DEFAULT 0.0,
        specific_weight REAL DEFAULT 0.0,
        weight_unit VARCHAR(20) DEFAULT 'kg',
        current_stock REAL DEFAULT 0.0,
        min_stock REAL DEFAULT 0.0,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
        FOREIGN KEY (unit_id) REFERENCES units(id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
    );
    """)

    # AUTO-REPAIR SCHEMA FOR OPERATIONS
    cursor.execute("PRAGMA table_info(operations)")
    existing_op_cols = [col[1] for col in cursor.fetchall()]
    if 'hours_per_operator' not in existing_op_cols:
        cursor.execute("ALTER TABLE operations ADD COLUMN hours_per_operator REAL DEFAULT 8.0")

    # DEFAULT UNITS
    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:
        for c, n in [('Ml', 'Linear Meters'), ('kg', 'Kilograms'), ('pcs', 'Pieces'), ('m2', 'Square Meters'), ('l', 'Liters')]:
            cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (c, n))

    # DEFAULT WAREHOUSES
    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        for c, n, t in [('WH-MAIN', 'Main Central Warehouse', 'Internal Warehouse'), ('WH-CUST', 'Customer Virtual Location', 'Customer Virtual Storage')]:
            cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (c, n, t))

    # DEFAULT FACILITIES
    cursor.execute("SELECT COUNT(*) FROM production_facilities")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO production_facilities (code, name, facility_type, brand_model) VALUES (?, ?, ?, ?)",
                       ('EQ-0001', 'Laser Tabla Trumpf', 'Laser Cutting', 'TruLaser 3030'))
        cursor.execute("INSERT INTO production_facilities (code, name, facility_type, brand_model) VALUES (?, ?, ?, ?)",
                       ('EQ-0002', 'Statie Sudura MIG-MAG', 'Welding Station', 'Kemppi MasterTig'))

    conn.commit()
    populate_missing_uniq_codes(conn)
    conn.close()

def populate_missing_uniq_codes(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, category, sub_group FROM stock_items WHERE uniq_code IS NULL OR uniq_code = '' OR uniq_code = 'nan'")
    rows = cursor.fetchall()
    for item_id, code, category, sub_group in rows:
        cat_upper = str(category).upper() if category else 'RAW MATERIAL'
        sg = str(sub_group) if sub_group else ''
        if 'RAW' in cat_upper:
            if sg == 'Tabla': prefix = 'RM-TB-'
            elif sg == 'Teava': prefix = 'RM-TV-'
            elif sg == 'Europrofile': prefix = 'RM-EP-'
            else: prefix = 'RM-GEN-'
        elif 'BUY' in cat_upper: prefix = 'BP-'
        elif 'FINISHED' in cat_upper or 'SUB' in cat_upper or 'PRODUSE' in cat_upper: prefix = 'A0'
        else: prefix = 'ITM-'

        cursor.execute("SELECT uniq_code, code FROM stock_items WHERE (uniq_code LIKE ? OR code LIKE ?) AND id != ?", (f"{prefix}%", f"{prefix}%", item_id))
        existing_records = cursor.fetchall()
        max_num = 0
        for (uc, c_val) in existing_records:
            for check_val in [uc, c_val]:
                if check_val and check_val.startswith(prefix):
                    num_part = check_val.replace(prefix, '')
                    if num_part.isdigit(): max_num = max(max_num, int(num_part))
        
        if code and code.startswith('A0') and cat_upper in ['FINISHED GOOD', 'PRODUSE FINITE']:
            new_code = code
        else:
            next_num = max_num + 1 if max_num > 0 else (1834 if prefix == 'A0' else 1)
            new_code = f"A0{next_num:04d}" if prefix == 'A0' else f"{prefix}{next_num:04d}"

        cursor.execute("UPDATE stock_items SET uniq_code = ? WHERE id = ?", (new_code, item_id))
    conn.commit()

def get_db():
    return sqlite3.connect('can_prod_v2.db', check_same_thread=False)

def generate_unique_item_code(conn, category, sub_group=""):
    cursor = conn.cursor()
    cat_upper = category.upper()
    if 'RAW' in cat_upper:
        if sub_group == 'Tabla': prefix = 'RM-TB-'
        elif sub_group == 'Teava': prefix = 'RM-TV-'
        elif sub_group == 'Europrofile': prefix = 'RM-EP-'
        else: prefix = 'RM-GEN-'
    elif 'BUY' in cat_upper: prefix = 'BP-'
    elif 'FINISHED' in cat_upper or 'SUB' in cat_upper or 'PRODUSE' in cat_upper: prefix = 'A0'
    else: prefix = 'ITM-'

    cursor.execute("SELECT uniq_code, code FROM stock_items WHERE uniq_code LIKE ? OR code LIKE ?", (f"{prefix}%", f"{prefix}%"))
    max_num = 0
    for (uc, c_val) in cursor.fetchall():
        for check_val in [uc, c_val]:
            if check_val and check_val.startswith(prefix):
                num_part = check_val.replace(prefix, '')
                if num_part.isdigit(): max_num = max(max_num, int(num_part))
            
    next_num = max_num + 1 if max_num > 0 else (1834 if prefix == 'A0' else 1)
    return f"A0{next_num:04d}" if prefix == 'A0' else f"{prefix}{next_num:04d}"

def generate_unique_customer_code(conn):
    cursor = conn.cursor()
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

def generate_unique_facility_code(conn):
    cursor = conn.cursor()
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

def generate_unique_operation_code(conn):
    cursor = conn.cursor()
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
        if 'ZINCAT 1000X' in text_upper: name = f"Treapta Gratar Zincat {part_no.replace('Zincat ', '').strip()} mm"
        elif 'PIULITA NIT' in text_upper: name = f"Piulita Nit {part_no.replace('Piulita Nit ', '').strip()}"
        elif 'M8_CU_FLANSA' in text_upper: name = "Piulita Hexagonala M8 cu Flansa"
        elif 'M8X40' in text_upper: name = "Surub M8x40 Complet Filetat"
        elif 'M8X110' in text_upper: name = "Surub M8x110 Complet Filetat"
        elif 'M12X70' in text_upper: name = "Surub Metric M12x70"
        elif 'M10X40' in text_upper: name = "Surub Metric M10x40"
        elif 'PIULITA' in text_upper: name = f"Piulita {(part_no if 'M' in part_no else desc).replace('Piulita ', '')}"
        elif 'SAIBA' in text_upper: name = f"Saiba Plana {(part_no if 'M' in part_no else desc).replace('saiba', '').replace('Saiba', '').strip()}"
        elif 'PICIOR REGLABIL' in text_upper: name = f"Picior Reglabil {part_no.replace('Picior Reglabil ', '')}"
        elif 'CONEXPAND' in text_upper: name = f"Conexpand Ancora Metalica {part_no.replace('Conexpand ', '')}"
        elif 'CAPAC PLASTIC 30X10' in text_upper: name = "Capac Plastic Oblong 30x10 mm"
        elif '30X30' in text_upper and 'CAPAC' in text_upper: name = "Capac Plastic Patrat 30x30 mm cu Filet M8"
        elif '50X50' in text_upper and 'CAPAC' in text_upper or part_no == 'Capac': name = "Capac Plastic Patrat 50x50 mm cu Filet M8"
        elif 'CAPAC FI 60' in text_upper or 'A00891' in text_upper: name = "Capac Plastic Rotund FI 60 mm Simplu"
        elif 'T35' in text_upper: name = "Tabla Cutata T35 x 0.5 mm + Folie Anticondens DryStop"
        elif 'POLICARBONAT' in text_upper: name = "Placa Policarbonat 3 Pereti (6000x2100 mm)"
        elif 'MANA CURENTA' in text_upper or 'A01841' in text_upper: name = "Mana Curenta din Lemn de Stejar"
        elif 'CUTIE CARTON' in text_upper or 'A00755' in text_upper: name = "Cutie Carton Ambalare Produse"
        else: name = f"{part_no} - {desc}"
        return 'Buy Parts', 'BUY PART', name
    else:
        europrofile_keywords = ['UPN', 'UNP', 'UPE', 'IPE', 'HEA', 'HEB', 'CORNIER', 'BARA', 'ROTUND', 'PATRAT', 'LAT', 'PLATBANDA', 'C 150X50', 'FI14', 'FI12', 'FI10', 'FI 25', 'FI 20', 'FI 8']
        if any(k in text_upper for k in europrofile_keywords) and not ('TEAVA' in text_upper or 'TV' in text_upper or 'ALU_' in text_upper):
            if 'UPN' in text_upper or 'UNP' in text_upper or 'UPE' in text_upper: name = f"Profil Otel {part_no}"
            elif 'IPE' in text_upper or desc == 'IPE': name = f"Profil Europrofil {part_no if 'IPE' in part_no else f'IPE {part_no}'}"
            elif 'HEA' in text_upper or desc == 'HEA': name = f"Profil Europrofil {part_no if 'HEA' in part_no else f'HEA {part_no}'}"
            elif 'CORNIER' in text_upper: name = f"Profil Cornier Otel {part_no.replace(' CORNIER', '').replace('Cornier ', '').replace('60X60X6 CORNIER', '60x60x6')} mm"
            elif 'ROTUND FI' in text_upper or part_no.startswith('Fi') or part_no.startswith('FI') or part_no.startswith('Bara fi'): name = f"Bara Rotunda Plina FI {part_no.replace('Rotund FI', '').replace('Bara fi ', '').replace('Fi', '').replace('FI ', '').replace('FI', '').strip()} mm"
            elif 'PATRAT' in text_upper: name = f"Bara Patrata Plina {part_no.replace(' Patrat', '')} mm"
            elif 'LAT' in text_upper or 'PLATBANDA' in text_upper: name = f"Platbanda Otel {part_no.replace('LAT ', '').replace('A00703 PLATBANDA', '80x4')} mm"
            elif 'C 150X50' in text_upper: name = "Profil C Zincat 150x50x30x2 mm"
            else: name = f"Profil Otel {part_no}"
            return 'Europrofile', 'RAW MATERIAL', re.sub(r'\s+', ' ', name).strip()
        elif any(k in text_upper for k in ['TB', 'TABLA', 'STRIATA', 'DX51D', 'PL 100X10']):
            if 'STRIATA' in text_upper: name = "Tabla Striata 3 mm"
            elif 'ZINCATA' in text_upper or 'DX51D' in text_upper: name = f"Tabla Zincata {part_no.replace('Tb', '').replace(' mm Zincata', '').strip()} mm (DX51D)"
            elif 'PL 100X10' in text_upper: name = "Platbanda / Tabla 100x10 mm"
            else: name = f"Tabla Neagra LBR {part_no.replace('Tb', '').replace(' mm', '').replace('.', '').strip()} mm"
            return 'Tabla', 'RAW MATERIAL', re.sub(r'\s+', ' ', name).strip()
        elif any(k in text_upper for k in ['TV', 'TEAVA', 'TEVA', 'ALU_', 'FI 219', 'FI 220', 'FI27', 'FI 76', 'FI 48', 'FI 42', 'FI 33', 'FI 28', '88,9X2', '18X2_PRECIZI', 'A01349']) or re.search(r'^\d+x\d+x[\d\.,]+', part_no.lower()):
            if 'ALU_' in text_upper: name = f"Teava Aluminiu Rectangulara {part_no.replace('ALU_', '')} mm"
            elif 'OVALA' in text_upper: name = f"Teava Ovala {part_no.replace('Teava ovala ', '')} mm"
            elif 'PRECIZIE' in text_upper: name = "Teava Otel Precizie FI 18x2 mm"
            elif 'FI' in text_upper or 'FI' in desc.upper(): name = f"Teava Rotunda FI {part_no.replace('TV FI', '').replace('Tv Fi', '').replace('TV Fi', '').replace('TV Fi ', '').replace('Teava ', '').replace('tv fi ', '').replace('TV ', '').replace('Fi ', '').strip()} mm"
            else: name = f"Teava Rectangulara / Patrata {part_no.replace('Teava ', '').replace(' Teava', '').replace(' TV', '').strip()} mm"
            return 'Teava', 'RAW MATERIAL', re.sub(r'\s+', ' ', name).strip()
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
        cursor.execute("SELECT id FROM units WHERE code = ?", (u_code,))
        u_row = cursor.fetchone()
        unit_id = u_row[0] if u_row else cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (u_code, u_code)).lastrowid

        w_name = str(row.get('default storage location', 'Main Warehouse')).strip()
        cursor.execute("SELECT id FROM warehouses WHERE name = ?", (w_name,))
        w_row = cursor.fetchone()
        warehouse_id = w_row[0] if w_row else cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (f"WH-{w_name[:5].upper().replace(' ', '')}", w_name, 'Internal Warehouse')).lastrowid

        price = safe_float(row.get('cost', 0))
        sell_price = safe_float(row.get('selling price', 0))
        weight_val = safe_float(row.get('weight', 0))
        weight_unit = str(row.get('unit of weight', 'kg')).strip()
        stock = safe_float(row.get('in stock', 0))
        min_st = safe_float(row.get('reorder point', 0))

        cursor.execute("SELECT id FROM stock_items WHERE code = ? OR uniq_code = ?", (item_code, uniq_code))
        ex = cursor.fetchone()
        if ex:
            cursor.execute("""UPDATE stock_items SET uniq_code=?, name=?, category=?, sub_group=?, unit_id=?, warehouse_id=?, purchase_price=?, selling_price=?, specific_weight=?, weight_unit=?, current_stock=?, min_stock=? WHERE id=?""", 
                           (uniq_code, clean_name, category, sub_group, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st, ex[0]))
            upd += 1
        else:
            cursor.execute("""INSERT INTO stock_items (uniq_code, code, name, category, sub_group, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                           (uniq_code, item_code, clean_name, category, sub_group, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st))
            ins += 1
    conn.commit()
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
        
        if not code or not name:
            continue

        val_reg = get_field(['reg. no.', 'reg. no', 'reg no', 'registration number'])
        val_vat = get_field(['tax/vat number', 'tax number', 'vat number', 'cui'])

        cui = ''
        reg_com = ''

        for val in [val_reg, val_vat]:
            if not val or val.lower() in ['nan', 'xxxx', '0000000', 'none']:
                continue
            val_upper = val.upper()
            if 'J' in val_upper or 'F' in val_upper or '/' in val:
                if not reg_com: reg_com = val
            else:
                if not cui: cui = val

        address_parts = []
        for col_name in ['address', 'first line of address', 'second line of address', 'city', 'state', 'postal code', 'country']:
            v = get_field([col_name])
            if v and v not in address_parts:
                address_parts.append(v)
        address = ", ".join(address_parts)

        fn = get_field(['first name'])
        ln = get_field(['last name'])
        contact_person = f"{fn} {ln}".strip()

        phone = get_field(['phone', 'address phone'])
        email = get_field(['e-mail', 'email'])

        cursor.execute("SELECT id FROM customers WHERE code = ? OR (cui != '' AND cui = ?)", (code, cui))
        ex = cursor.fetchone()
        if ex:
            cursor.execute("""
                UPDATE customers SET code=?, name=?, cui=?, reg_com=?, address=?, contact_person=?, phone=?, email=?
                WHERE id=?
            """, (code, name, cui, reg_com, address, contact_person, phone, email, ex[0]))
            upd += 1
        else:
            cursor.execute("""
                INSERT INTO customers (code, name, cui, reg_com, address, contact_person, phone, email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, cui, reg_com, address, contact_person, phone, email))
            ins += 1

    conn.commit()
    conn.close()
    return ins, upd

def safe_float(val):
    if val in (None, "", "nan", "NaN"): return 0.0
    try: return float(val)
    except: return 0.0
