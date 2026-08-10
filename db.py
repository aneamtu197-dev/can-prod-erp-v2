import sqlite3
import pandas as pd
import re

def init_custom_db():
    # Permitem accesul Multi-Thread pentru a rezolva eroarea din Pop-Up-uri
    conn = sqlite3.connect('can_prod_v2.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(50) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        supplier_type VARCHAR(100) DEFAULT 'Raw Material Supplier',
        contact_person VARCHAR(255),
        phone VARCHAR(100),
        email VARCHAR(255),
        lead_time_days INTEGER DEFAULT 0
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

    # AUTO-REPAIR SCHEMA FOR STOCK ITEMS
    cursor.execute("PRAGMA table_info(stock_items)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    for col_name, col_type in {'uniq_code': "VARCHAR(100)", 'sub_group': "VARCHAR(100) DEFAULT 'General'", 'selling_price': "REAL DEFAULT 0.0", 'specific_weight': "REAL DEFAULT 0.0", 'weight_unit': "VARCHAR(20) DEFAULT 'kg'"}.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE stock_items ADD COLUMN {col_name} {col_type}")

    # AUTO-REPAIR SCHEMA FOR SUPPLIERS
    cursor.execute("PRAGMA table_info(suppliers)")
    if 'supplier_type' not in [col[1] for col in cursor.fetchall()]:
        cursor.execute("ALTER TABLE suppliers ADD COLUMN supplier_type VARCHAR(100) DEFAULT 'Raw Material Supplier'")

    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:
        for c, n in [('Ml', 'Linear Meters'), ('kg', 'Kilograms'), ('pcs', 'Pieces'), ('m2', 'Square Meters'), ('l', 'Liters')]:
            cursor.execute("INSERT INTO units (code, name) VALUES (?, ?)", (c, n))

    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        for c, n, t in [('WH-MAIN', 'Main Central Warehouse', 'Internal Warehouse'), ('WH-CUST', 'Customer Virtual Location', 'Customer Virtual Storage')]:
            cursor.execute("INSERT INTO warehouses (code, name, location_type) VALUES (?, ?, ?)", (c, n, t))

    cursor.execute("SELECT COUNT(*) FROM suppliers")
    if cursor.fetchone()[0] == 0:
        for c, n, stype, cp, p, e, lt in [('SUP001', 'Baurom Construct SRL', 'Raw Material Supplier', 'John Smith', '+40722111222', 'orders@baurom.ro', 3), ('SUP002', 'LemnConfex SRL', 'Buy Parts Supplier', 'Mary Doe', '+40733444555', 'sales@lemnconfex.ro', 5)]:
            cursor.execute("INSERT INTO suppliers (code, name, supplier_type, contact_person, phone, email, lead_time_days) VALUES (?, ?, ?, ?, ?, ?, ?)", (c, n, stype, cp, p, e, lt))

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

        v_name = str(row.get('vendor name', '')).strip()
        supplier_id = None
        if v_name and v_name != 'nan':
            cursor.execute("SELECT id FROM suppliers WHERE name = ?", (v_name,))
            s_row = cursor.fetchone()
            supplier_id = s_row[0] if s_row else cursor.execute("INSERT INTO suppliers (code, name, supplier_type) VALUES (?, ?, ?)", (f"SUP-{v_name[:5].upper()}", v_name, "General / Both")).lastrowid

        price = safe_float(row.get('cost', 0))
        sell_price = safe_float(row.get('selling price', 0))
        weight_val = safe_float(row.get('weight', 0))
        weight_unit = str(row.get('unit of weight', 'kg')).strip()
        stock = safe_float(row.get('in stock', 0))
        min_st = safe_float(row.get('reorder point', 0))

        cursor.execute("SELECT id FROM stock_items WHERE code = ? OR uniq_code = ?", (item_code, uniq_code))
        ex = cursor.fetchone()
        if ex:
            cursor.execute("""UPDATE stock_items SET uniq_code=?, name=?, category=?, sub_group=?, supplier_id=?, unit_id=?, warehouse_id=?, purchase_price=?, selling_price=?, specific_weight=?, weight_unit=?, current_stock=?, min_stock=? WHERE id=?""", 
                           (uniq_code, clean_name, category, sub_group, supplier_id, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st, ex[0]))
            upd += 1
        else:
            cursor.execute("""INSERT INTO stock_items (uniq_code, code, name, category, sub_group, supplier_id, unit_id, warehouse_id, purchase_price, selling_price, specific_weight, weight_unit, current_stock, min_stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                           (uniq_code, item_code, clean_name, category, sub_group, supplier_id, unit_id, warehouse_id, price, sell_price, weight_val, weight_unit, stock, min_st))
            ins += 1
    conn.commit()
    return ins, upd

def safe_float(val):
    if val in (None, "", "nan", "NaN"): return 0.0
    try: return float(val)
    except: return 0.0
