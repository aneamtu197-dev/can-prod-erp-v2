import psycopg2
import streamlit as st
import pandas as pd
import math

# ==========================================
# 1. DATABASE CONNECTION
# ==========================================
def get_db():
    DATABASE_URL = "postgresql://postgres:gWJ8uOkdgotCKmC7@db.ptdkpxkftfnmtigzpttj.supabase.co:5432/postgres"
    return psycopg2.connect(DATABASE_URL)

# ==========================================
# 2. GENERATE UNIQUE CODES
# ==========================================
def generate_unique_item_code(conn, category, sub_group=""):
    cursor = conn.cursor()
    prefix = "FG"
    if category == "RAW MATERIAL": prefix = "RM"
    elif category == "BUY PART": prefix = "BP"
    
    cursor.execute("SELECT COUNT(id) FROM stock_items WHERE category = %s", (category,))
    count = cursor.fetchone()[0] + 1
    return f"{prefix}-{count:04d}"

def generate_unique_customer_code(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(id) FROM customers")
    count = cursor.fetchone()[0] + 1
    return f"CUST-{count:04d}"

def generate_unique_facility_code(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(id) FROM production_facilities")
    count = cursor.fetchone()[0] + 1
    return f"FAC-{count:03d}"

def generate_unique_operation_code(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(id) FROM operations")
    count = cursor.fetchone()[0] + 1
    return f"OP-{count:04d}"

# ==========================================
# 3. CSV IMPORTERS 
# ==========================================
# Daca ai logica avansata la import CSV, inlocuieste cu codul tau vechi in aceste 2 functii!
def import_mrpeasy_items(df):
    conn = get_db()
    cursor = conn.cursor()
    inserted, updated = 0, 0
    # Aici era logica ta de import materiale...
    conn.commit()
    conn.close()
    return inserted, updated

def import_mrpeasy_customers(df):
    conn = get_db()
    cursor = conn.cursor()
    inserted, updated = 0, 0
    # Aici era logica ta de import clienti...
    conn.commit()
    conn.close()
    return inserted, updated

# ==========================================
# 4. INITIALIZE DATABASE TABLES
# ==========================================
def init_custom_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Units
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100)
        )
    """)
    
    # 2. Customers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE,
            name VARCHAR(255) NOT NULL,
            cui VARCHAR(50),
            reg_com VARCHAR(50),
            address TEXT,
            iban VARCHAR(100),
            bank_name VARCHAR(100),
            contact_person VARCHAR(100),
            phone VARCHAR(50),
            email VARCHAR(100)
        )
    """)
    
    # 3. Suppliers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE,
            name VARCHAR(255) NOT NULL,
            supplier_type VARCHAR(100),
            contact_person VARCHAR(100),
            phone VARCHAR(50),
            email VARCHAR(100),
            lead_time_days INTEGER DEFAULT 0,
            cui VARCHAR(50),
            reg_com VARCHAR(50),
            address TEXT,
            iban VARCHAR(100),
            bank_name VARCHAR(100)
        )
    """)
    
    # 4. Warehouses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warehouses (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            location_type VARCHAR(100),
            customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL
        )
    """)
    
    # 5. Stock Items
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_items (
            id SERIAL PRIMARY KEY,
            uniq_code VARCHAR(100) UNIQUE,
            code VARCHAR(100),
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100),
            sub_group VARCHAR(100),
            supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
            customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
            unit_id INTEGER REFERENCES units(id) ON DELETE SET NULL,
            warehouse_id INTEGER REFERENCES warehouses(id) ON DELETE SET NULL,
            purchase_price DECIMAL(15,2) DEFAULT 0.0,
            selling_price DECIMAL(15,2) DEFAULT 0.0,
            specific_weight DECIMAL(15,2) DEFAULT 0.0,
            weight_unit VARCHAR(20) DEFAULT 'kg',
            current_stock DECIMAL(15,2) DEFAULT 0.0,
            min_stock DECIMAL(15,2) DEFAULT 0.0,
            barcode VARCHAR(100)
        )
    """)
    
    # 6. Production Facilities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS production_facilities (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE,
            name VARCHAR(255) NOT NULL,
            facility_type VARCHAR(100),
            brand_model VARCHAR(255),
            status VARCHAR(50) DEFAULT 'Operational',
            next_maintenance_date DATE
        )
    """)
    
    # 7. Operations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id SERIAL PRIMARY KEY,
            uniq_code VARCHAR(100) UNIQUE,
            name VARCHAR(255) NOT NULL,
            cost_unit VARCHAR(50),
            rate_per_unit DECIMAL(15,2) DEFAULT 0.0,
            productivity_level DECIMAL(5,2) DEFAULT 1.0,
            hours_per_operator DECIMAL(5,2) DEFAULT 8.0,
            max_hours_day DECIMAL(10,2) DEFAULT 0.0,
            max_hours_week DECIMAL(10,2) DEFAULT 0.0,
            max_hours_month DECIMAL(10,2) DEFAULT 0.0,
            operators_count INTEGER DEFAULT 1,
            facility_id INTEGER REFERENCES production_facilities(id) ON DELETE SET NULL,
            is_outsourced INTEGER DEFAULT 0,
            preferred_supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
            outsourcing_type VARCHAR(100),
            material_supplied_by VARCHAR(100)
        )
    """)
    
    # 8. Product BOMs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_boms (
            id SERIAL PRIMARY KEY,
            product_item_id INTEGER REFERENCES stock_items(id) ON DELETE CASCADE,
            customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
            calculated_weight DECIMAL(15,2) DEFAULT 0.0,
            total_material_cost DECIMAL(15,2) DEFAULT 0.0,
            total_labor_cost DECIMAL(15,2) DEFAULT 0.0,
            total_production_cost DECIMAL(15,2) DEFAULT 0.0,
            markup_percent DECIMAL(10,2) DEFAULT 0.0
        )
    """)
    
    # 9. BOM Materials
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bom_materials (
            id SERIAL PRIMARY KEY,
            bom_id INTEGER REFERENCES product_boms(id) ON DELETE CASCADE,
            material_item_id INTEGER REFERENCES stock_items(id) ON DELETE CASCADE,
            quantity_required DECIMAL(15,4) DEFAULT 0.0,
            unit_cost DECIMAL(15,2) DEFAULT 0.0,
            total_cost DECIMAL(15,2) DEFAULT 0.0
        )
    """)
    
    # 10. BOM Operations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bom_operations (
            id SERIAL PRIMARY KEY,
            bom_id INTEGER REFERENCES product_boms(id) ON DELETE CASCADE,
            operation_id INTEGER REFERENCES operations(id) ON DELETE CASCADE,
            step_number INTEGER DEFAULT 1,
            duration_hours DECIMAL(15,2) DEFAULT 0.0,
            rate_applied DECIMAL(15,2) DEFAULT 0.0,
            total_cost DECIMAL(15,2) DEFAULT 0.0
        )
    """)

    # ====================================================
    # 11. NOILE TABELE: SETĂRI ȘI UTILIZATORI
    # ====================================================
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS item_categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT
        )
    """)
    cursor.execute("SELECT count(*) FROM item_categories")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO item_categories (name) VALUES ('RAW MATERIAL'), ('BUY PART'), ('FINISHED GOOD'), ('SUBASSEMBLY')")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS item_subgroups (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT
        )
    """)
    cursor.execute("SELECT count(*) FROM item_subgroups")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO item_subgroups (name) VALUES ('Tabla'), ('Teava'), ('Europrofile'), ('Materiale Diverse'), ('Buy Parts'), ('Finished Goods')")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'User',
            is_active BOOLEAN DEFAULT TRUE
        )
    """)

    # Inseram niste unitati de masura default daca tabelul era complet gol
    cursor.execute("SELECT count(*) FROM units")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO units (code, name) VALUES ('buc', 'Bucata'), ('kg', 'Kilogram'), ('ml', 'Metru Liniar'), ('m2', 'Metru Patrat')")

    conn.commit()
    cursor.close()
    conn.close()
