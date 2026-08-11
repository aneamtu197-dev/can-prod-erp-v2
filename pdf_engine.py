import io
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 8, 'CAN PROD SRL - SYSTEM ERP', 0, 1, 'C')
        self.set_font('Helvetica', '', 9)
        self.cell(0, 5, 'Document Generat Automat | Fisa Tehnologica & Bon de Consum', 0, 1, 'C')
        self.line(10, 22, 200, 22)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_bom_pdf(prod_code, prod_name, cust_name, weight, df_materials, tot_mat_cost):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, f'BON DE CONSUM MATERIALE - {prod_code}', 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(40, 6, 'Denumire Produs:', 0, 0)
    pdf.cell(100, 6, str(prod_name), 0, 1)
    pdf.cell(40, 6, 'Client Asociat:', 0, 0)
    pdf.cell(100, 6, str(cust_name), 0, 1)
    pdf.cell(40, 6, 'Greutate Totala:', 0, 0)
    pdf.cell(100, 6, f'{weight:.2f} kg', 0, 1)
    pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(25, 7, 'Cod', 1, 0, 'C', True)
    pdf.cell(85, 7, 'Denumire Material', 1, 0, 'L', True)
    pdf.cell(25, 7, 'Cantitate', 1, 0, 'C', True)
    pdf.cell(25, 7, 'Pret Unit. (EUR)', 1, 0, 'R', True)
    pdf.cell(30, 7, 'Total (EUR)', 1, 1, 'R', True)
    
    pdf.set_font('Helvetica', '', 9)
    for _, r in df_materials.iterrows():
        code_str = str(r.get('Code', ''))[:12]
        mat_name_str = str(r.get('Material Name', ''))[:45]
        qty_str = f"{r.get('Qty', 0)} {r.get('UoM', '')}"
        price_val = float(r.get('Price', 0))
        tot_val = float(r.get('Total Cost', 0))
        
        pdf.cell(25, 6, code_str, 1, 0, 'C')
        pdf.cell(85, 6, mat_name_str, 1, 0, 'L')
        pdf.cell(25, 6, qty_str, 1, 0, 'C')
        pdf.cell(25, 6, f'{price_val:.2f}', 1, 0, 'R')
        pdf.cell(30, 6, f'{tot_val:.2f}', 1, 1, 'R')
        
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(160, 7, 'TOTAL COST MATERIALE:', 0, 0, 'R')
    pdf.cell(30, 7, f'{tot_mat_cost:.2f} EUR', 1, 1, 'R')
    
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()

def generate_routing_pdf(prod_code, prod_name, cust_name, df_ops, tot_lab_cost):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, f'FISA TEHNOLOGICA DE OPERATII (ROUTING) - {prod_code}', 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(40, 6, 'Denumire Produs:', 0, 0)
    pdf.cell(100, 6, str(prod_name), 0, 1)
    pdf.cell(40, 6, 'Client Asociat:', 0, 0)
    pdf.cell(100, 6, str(cust_name), 0, 1)
    pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(15, 7, 'Pas', 1, 0, 'C', True)
    pdf.cell(25, 7, 'Cod Op.', 1, 0, 'C', True)
    pdf.cell(70, 7, 'Denumire Operatie', 1, 0, 'L', True)
    pdf.cell(30, 7, 'Timp / Cant.', 1, 0, 'C', True)
    pdf.cell(25, 7, 'Tarif (EUR)', 1, 0, 'R', True)
    pdf.cell(25, 7, 'Total (EUR)', 1, 1, 'R', True)
    
    pdf.set_font('Helvetica', '', 9)
    for _, r in df_ops.iterrows():
        step_str = f"Step {r.get('Step', 1)}"
        code_str = str(r.get('Op Code', ''))[:12]
        op_name_str = str(r.get('Operation Name', ''))[:38]
        dur_str = f"{r.get('Duration', 0)} {r.get('Unit', '')}"
        rate_val = float(r.get('Rate', 0))
        tot_val = float(r.get('Total Cost', 0))
        
        pdf.cell(15, 6, step_str, 1, 0, 'C')
        pdf.cell(25, 6, code_str, 1, 0, 'C')
        pdf.cell(70, 6, op_name_str, 1, 0, 'L')
        pdf.cell(30, 6, dur_str, 1, 0, 'C')
        pdf.cell(25, 6, f'{rate_val:.2f}', 1, 0, 'R')
        pdf.cell(25, 6, f'{tot_val:.2f}', 1, 1, 'R')
        
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(140, 7, 'TOTAL COST OPERATII / MANOPERA:', 0, 0, 'R')
    pdf.cell(25, 7, f'{tot_lab_cost:.2f} EUR', 1, 1, 'R')
    
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
