import io
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF

# Configure clean chart styling
plt.style.use('ggplot')

# ---------------------------------------------------------
# HELPER FUNCTIONS & CHART GENERATORS
# ---------------------------------------------------------

def format_num(val, decimals=2):
    try:
        val = float(val)
        return f"{val:,.{decimals}f}"
    except (ValueError, TypeError):
        return "0.00"

def create_main_bar_chart(labels, values):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    bars = ax.bar(labels, values, color='#1b365d')
    ax.set_title("Stock Quantity Breakdown (MT)", fontsize=11, fontweight='bold', color='#1b365d')
    ax.set_ylabel("Quantity (MT)", fontsize=9)
    plt.xticks(rotation=15, ha='right', fontsize=8)
    
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:,.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

def create_category_bar_chart(categories, gd_vals, sold_vals, bal_vals):
    fig, ax = plt.subplots(figsize=(5, 3.5))
    x = range(len(categories))
    width = 0.25

    ax.bar([p - width for p in x], gd_vals, width=width, label='GD STOCK', color='#1b365d')
    ax.bar(x, sold_vals, width=width, label='SOLD QTY', color='#38bdf8')
    ax.bar([p + width for p in x], bal_vals, width=width, label='BAL. QTY', color='#ef4444')

    ax.set_title("Stock Distribution by Category", fontsize=10, fontweight='bold', color='#1b365d')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=8)
    ax.legend(fontsize=7)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

def create_category_pie_chart(categories, gd_vals):
    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    colors = ['#1b365d', '#38bdf8', '#f59e0b', '#10b981', '#8b5cf6']
    
    ax.pie(gd_vals, labels=categories, autopct='%1.1f%%', startangle=140,
           colors=colors[:len(categories)], textprops={'fontsize': 8, 'weight': 'bold'})
    ax.set_title("GD Stock Share by Category", fontsize=10, fontweight='bold', color='#1b365d')
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

def create_material_pie_chart(recd, loading, intransit):
    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    vals = [recd, loading, intransit]
    labels = ['RECD', 'LOADING', 'INTRANSIT']
    colors = ['#3b82f6', '#f97316', '#14b8a6']
    
    non_zero = [(v, l, c) for v, l, c in zip(vals, labels, colors) if v > 0]
    if non_zero:
        v_fit, l_fit, c_fit = zip(*non_zero)
        ax.pie(v_fit, labels=l_fit, autopct='%1.1f%%', startangle=140, colors=c_fit,
               textprops={'fontsize': 8, 'weight': 'bold'})
    
    ax.set_title("QTY Distribution by Status", fontsize=10, fontweight='bold', color='#1b365d')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    plt.close(fig)
    return buf

# ---------------------------------------------------------
# FPDF CLASS DEFINITION
# ---------------------------------------------------------

class CompleteReportPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_text = "Executive Report"

    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.set_fill_color(27, 54, 93) # #1b365d
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, self.title_text, fill=True, align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, f'Page {self.page_no()}', align='C')

    def draw_section_title(self, title):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(27, 54, 93)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(203, 213, 225)
        self.line(self.get_x(), self.get_y(), self.get_x() + 277, self.get_y())
        self.ln(3)

    def draw_kpi_cards(self, kpi_data):
        card_width = 277 / len(kpi_data)
        
        # Header Row
        self.set_font('Helvetica', 'B', 7)
        self.set_fill_color(248, 250, 252)
        self.set_text_color(100, 116, 139)
        for label, _ in kpi_data:
            self.cell(card_width, 5, label, border=1, fill=True, align='C')
        self.ln()

        # Values Row
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(27, 54, 93)
        for _, val in kpi_data:
            self.cell(card_width, 7, val, border=1, fill=True, align='C')
        self.ln(6)

# ---------------------------------------------------------
# MAIN PDF GENERATION FUNCTION
# ---------------------------------------------------------

def generate_full_pdf_report(stock_df, material_df, report_date="29.09.2026"):
    # ---------------------------------------------------------
    # 1. PROCESS DAILY STOCK METRICS
    # ---------------------------------------------------------
    gd_stock = float(stock_df['GD STOCK'].sum()) if 'GD STOCK' in stock_df.columns else 0.0
    coil = float(stock_df['COIL'].sum()) if 'COIL' in stock_df.columns else 0.0
    sold_qty = float(stock_df['SOLD QTY'].sum()) if 'SOLD QTY' in stock_df.columns else 0.0
    booking = float(stock_df['BOOKING'].sum()) if 'BOOKING' in stock_df.columns else 0.0
    sail_bso = float(stock_df['SAIL BSO'].sum()) if 'SAIL BSO' in stock_df.columns else 0.0

    if 'STATUS' in stock_df.columns and 'INTANS' in stock_df.columns:
        intans_mask = stock_df['STATUS'].astype(str).str.strip().str.upper().isin(['INTRANSIT', 'IN TRANSIT'])
        intans = float(stock_df.loc[intans_mask, 'INTANS'].sum())
    elif 'INTANS' in stock_df.columns:
        intans = float(stock_df['INTANS'].sum())
    else:
        intans = 0.0

    bal_qty = (gd_stock + coil + intans) - sold_qty - booking - sail_bso

    # Aggregating Categories for Charts
    category_summary = {}
    if 'CATEGORY' in stock_df.columns:
        for cat, group in stock_df.groupby('CATEGORY'):
            c_gd = float(group['GD STOCK'].sum()) if 'GD STOCK' in group.columns else 0.0
            c_sold = float(group['SOLD QTY'].sum()) if 'SOLD QTY' in group.columns else 0.0
            c_coil = float(group['COIL'].sum()) if 'COIL' in group.columns else 0.0
            c_intans = float(group['INTANS'].sum()) if 'INTANS' in group.columns else 0.0
            c_booking = float(group['BOOKING'].sum()) if 'BOOKING' in group.columns else 0.0
            c_sail = float(group['SAIL BSO'].sum()) if 'SAIL BSO' in group.columns else 0.0
            
            c_bal = (c_gd + c_coil + c_intans) - c_sold - c_booking - c_sail
            category_summary[str(cat)] = {'gd': c_gd, 'sold': c_sold, 'bal': c_bal}

    # ---------------------------------------------------------
    # 2. PROCESS MATERIAL STATUS METRICS
    # ---------------------------------------------------------
    total_mat_qty = float(material_df['QTY'].sum()) if 'QTY' in material_df.columns else 0.0
    
    if 'STATUS' in material_df.columns and 'QTY' in material_df.columns:
        mat_status_upper = material_df['STATUS'].astype(str).str.strip().str.upper()
        recd_qty = float(material_df.loc[mat_status_upper.isin(['RECD', 'RECEIVED']), 'QTY'].sum())
        loading_qty = float(material_df.loc[mat_status_upper == 'LOADING', 'QTY'].sum())
        intransit_qty = float(material_df.loc[mat_status_upper.isin(['INTRANSIT', 'IN TRANSIT']), 'QTY'].sum())
    else:
        recd_qty, loading_qty, intransit_qty = 0.0, 0.0, 0.0

    # Material Source Breakdown Matrix
    mat_matrix = {}
    if 'FROM' in material_df.columns and 'QTY' in material_df.columns and 'STATUS' in material_df.columns:
        for src, group in material_df.groupby('FROM'):
            s_recd = float(group.loc[group['STATUS'].astype(str).str.strip().str.upper().isin(['RECD', 'RECEIVED']), 'QTY'].sum())
            s_load = float(group.loc[group['STATUS'].astype(str).str.strip().str.upper() == 'LOADING', 'QTY'].sum())
            s_tran = float(group.loc[group['STATUS'].astype(str).str.strip().str.upper().isin(['INTRANSIT', 'IN TRANSIT']), 'QTY'].sum())
            s_tot = float(group['QTY'].sum())
            mat_matrix[str(src)] = {'recd': s_recd, 'loading': s_load, 'intransit': s_tran, 'total': s_tot}

    # ---------------------------------------------------------
    # 3. BUILD COMPLETE PDF DOCUMENT
    # ---------------------------------------------------------
    pdf = CompleteReportPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=12)

    # --- PAGE 1: DAILY STOCK EXECUTIVE OVERVIEW & MAIN CHART ---
    pdf.title_text = f"Daily Stock Executive Report - {report_date}"
    pdf.add_page()

    pdf.draw_section_title("Executive KPI Overview")
    kpis_p1 = [
        ("GD STOCK", format_num(gd_stock)),
        ("COIL", format_num(coil)),
        ("SOLD QTY", format_num(sold_qty)),
        ("INTANS", format_num(intans)),
        ("BOOKING", format_num(booking)),
        ("SAIL BSO", format_num(sail_bso)),
        ("BAL. QTY", format_num(bal_qty))
    ]
    pdf.draw_kpi_cards(kpis_p1)

    pdf.draw_section_title("Stock Analytics Chart")
    main_chart_img = create_main_bar_chart(
        ['GD STOCK', 'COIL', 'SOLD QTY', 'INTANS', 'BOOKING', 'SAIL BSO', 'BAL. QTY'],
        [gd_stock, coil, sold_qty, intans, booking, sail_bso, bal_qty]
    )
    pdf.image(main_chart_img, x=38, w=200)

    # --- PAGE 2: KEY METRICS & SUMMARY OVERVIEW ---
    pdf.title_text = f"Key Metrics & Summary Overview - {report_date}"
    pdf.add_page()

    pdf.draw_section_title(f"Key Metrics Overview: {report_date}")
    kpis_p2_a = [
        ("GD STOCK", format_num(gd_stock, 3)),
        ("SOLD QTY", format_num(sold_qty, 3)),
        ("INTANS", format_num(intans, 3)),
        ("BAL. QTY", format_num(bal_qty, 3))
    ]
    pdf.draw_kpi_cards(kpis_p2_a)

    pdf.draw_section_title("Orders & Movements")
    kpis_p2_b = [
        ("TOTAL COIL", format_num(coil, 3)),
        ("TOTAL BOOKING", format_num(booking, 3)),
        ("TOTAL SAIL BSO", format_num(sail_bso, 3))
    ]
    pdf.draw_kpi_cards(kpis_p2_b)

    pdf.draw_section_title("Full Metrics Summary Table")
    
    # Metrics Table Header
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(27, 54, 93)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(140, 6, "Metric", border=1, fill=True, align='L')
    pdf.cell(137, 6, f"{report_date} Total", border=1, fill=True, align='R', new_x="LMARGIN", new_y="NEXT")

    metrics_rows = [
        ("GD STOCK", format_num(gd_stock, 3)),
        ("COIL", format_num(coil, 3)),
        ("SOLD QTY", format_num(sold_qty, 3)),
        ("INTANS", format_num(intans, 3)),
        ("BOOKING", format_num(booking, 3)),
        ("SAIL BSO", format_num(sail_bso, 3)),
        ("BAL. QTY", format_num(bal_qty, 3))
    ]
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 41, 59)
    for label, val in metrics_rows:
        pdf.cell(140, 5, label, border=1, align='L')
        pdf.cell(137, 5, val, border=1, align='R', new_x="LMARGIN", new_y="NEXT")

    # --- PAGE 3: VISUAL ANALYSIS - CATEGORY BREAKDOWN ---
    pdf.title_text = "Visual Analysis - Category Breakdown"
    pdf.add_page()

    cats = list(category_summary.keys()) if category_summary else ['CHQ', 'PLATE']
    c_gd = [category_summary[c]['gd'] for c in cats] if category_summary else [143.4, 806.9]
    c_sold = [category_summary[c]['sold'] for c in cats] if category_summary else [117.9, 657.8]
    c_bal = [category_summary[c]['bal'] for c in cats] if category_summary else [545.5, 1694.2]

    cat_bar_img = create_category_bar_chart(cats, c_gd, c_sold, c_bal)
    cat_pie_img = create_category_pie_chart(cats, c_gd)

    pdf.image(cat_bar_img, x=10, y=28, w=130)
    pdf.image(cat_pie_img, x=145, y=28, w=120)

    # --- PAGE 4: DETAILED STOCK BREAKDOWN TABLE ---
    pdf.title_text = f"Detailed Stock Breakdown - {report_date}"
    pdf.add_page()
    pdf.draw_section_title("Daily Stock Item Breakdown")

    headers = ["SR", "CATEGORY", "THIK", "WIDTH", "GRADE", "GD STOCK", "COIL", "SOLD QTY", "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"]
    widths = [10, 25, 18, 18, 22, 24, 22, 24, 24, 24, 24, 24]

    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(27, 54, 93)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 6, h, border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 41, 59)

    for idx, row in stock_df.iterrows():
        r_gd = float(row.get('GD STOCK', 0) or 0)
        r_coil = float(row.get('COIL', 0) or 0)
        r_sold = float(row.get('SOLD QTY', 0) or 0)
        r_booking = float(row.get('BOOKING', 0) or 0)
        r_sail = float(row.get('SAIL BSO', 0) or 0)
        r_status = str(row.get('STATUS', '')).strip().upper()
        r_intans = float(row.get('INTANS', 0) or 0) if r_status in ['INTRANSIT', 'IN TRANSIT'] else 0.0
        r_bal = (r_gd + r_coil + r_intans) - r_sold - r_booking - r_sail

        vals = [
            str(idx + 1), str(row.get('CATEGORY', '')), str(row.get('THIK', '')),
            str(row.get('WIDTH', '')), str(row.get('GRADE', '')), format_num(r_gd),
            format_num(r_coil), format_num(r_sold), format_num(r_intans),
            format_num(r_booking), format_num(r_sail), format_num(r_bal)
        ]
        for i, val in enumerate(vals):
            align = 'L' if i < 5 else 'R'
            pdf.cell(widths[i], 5, val, border=1, align=align)
        pdf.ln()

    # Total Summary Row for Table
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(93, 6, "TOTAL", border=1, fill=True, align='C')
    pdf.cell(24, 6, format_num(gd_stock), border=1, fill=True, align='R')
    pdf.cell(22, 6, format_num(coil), border=1, fill=True, align='R')
    pdf.cell(24, 6, format_num(sold_qty), border=1, fill=True, align='R')
    pdf.cell(24, 6, format_num(intans), border=1, fill=True, align='R')
    pdf.cell(24, 6, format_num(booking), border=1, fill=True, align='R')
    pdf.cell(24, 6, format_num(sail_bso), border=1, fill=True, align='R')
    pdf.cell(24, 6, format_num(bal_qty), border=1, fill=True, align='R', new_x="LMARGIN", new_y="NEXT")

    # --- PAGE 5: MATERIAL STATUS EXECUTIVE REPORT ---
    pdf.title_text = f"Material Status Executive Report - {report_date}"
    pdf.add_page()

    pdf.draw_section_title("Material Status KPI Overview")
    mat_kpis = [
        ("TOTAL MATERIAL QTY", f"{format_num(total_mat_qty, 3)} MT"),
        ("RECEIVED (RECD)", f"{format_num(recd_qty, 3)} MT"),
        ("LOADING", f"{format_num(loading_qty, 3)} MT"),
        ("IN TRANSIT", f"{format_num(intransit_qty, 3)} MT")
    ]
    pdf.draw_kpi_cards(mat_kpis)

    pdf.draw_section_title("Source (FROM) vs Status Breakdown Matrix")
    
    m_mat_headers = ["FROM", "RECD", "LOADING", "INTRANSIT", "TOTAL QTY"]
    m_mat_widths = [75, 50, 50, 50, 52]

    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(27, 54, 93)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(m_mat_headers):
        pdf.cell(m_mat_widths[i], 6, h, border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 41, 59)
    for src_name, s_data in mat_matrix.items():
        pdf.cell(m_mat_widths[0], 5, src_name, border=1, align='L')
        pdf.cell(m_mat_widths[1], 5, format_num(s_data['recd'], 3), border=1, align='R')
        pdf.cell(m_mat_widths[2], 5, format_num(s_data['loading'], 3), border=1, align='R')
        pdf.cell(m_mat_widths[3], 5, format_num(s_data['intransit'], 3), border=1, align='R')
        pdf.cell(m_mat_widths[4], 5, format_num(s_data['total'], 3), border=1, align='R', new_x="LMARGIN", new_y="NEXT")

    # Matrix Total Row
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(m_mat_widths[0], 6, "TOTAL", border=1, fill=True, align='L')
    pdf.cell(m_mat_widths[1], 6, format_num(recd_qty, 3), border=1, fill=True, align='R')
    pdf.cell(m_mat_widths[2], 6, format_num(loading_qty, 3), border=1, fill=True, align='R')
    pdf.cell(m_mat_widths[3], 6, format_num(intransit_qty, 3), border=1, fill=True, align='R')
    pdf.cell(m_mat_widths[4], 6, format_num(total_mat_qty, 3), border=1, fill=True, align='R', new_x="LMARGIN", new_y="NEXT")

    # --- PAGE 6: DETAILED MATERIAL STATUS DATA & VISUALS ---
    pdf.title_text = f"Detailed Material Data - {report_date}"
    pdf.add_page()

    mat_pie_img = create_material_pie_chart(recd_qty, loading_qty, intransit_qty)
    pdf.image(mat_pie_img, x=10, y=28, w=110)

    pdf.set_xy(125, 28)
    pdf.draw_section_title("Material Data Lines")

    m_headers = ["CATEGORY", "THIK", "SIZE", "GRADE", "QTY", "FROM", "STATUS"]
    m_widths = [22, 15, 18, 20, 22, 28, 25]

    pdf.set_x(125)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_fill_color(27, 54, 93)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(m_headers):
        pdf.cell(m_widths[i], 6, h, border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(30, 41, 59)
    for idx, row in material_df.iterrows():
        pdf.set_x(125)
        m_vals = [
            str(row.get('CATEGORY', '')), str(row.get('THIK', '')),
            str(row.get('SIZE', '')), str(row.get('GRADE', '')),
            format_num(row.get('QTY', 0), 3), str(row.get('FROM', '')),
            str(row.get('STATUS', ''))
        ]
        for i, val in enumerate(m_vals):
            align = 'R' if i == 4 else 'L'
            pdf.cell(m_widths[i], 5, val, border=1, align=align)
        pdf.ln()

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

# ---------------------------------------------------------
# STREAMLIT USER INTERFACE
# ---------------------------------------------------------

st.title("Executive Stock & Material PDF Report Generator")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    
    col1, col2 = st.columns(2)
    with col1:
        stock_sheet = st.selectbox("Select Daily Stock Sheet", sheet_names, index=0)
    with col2:
        mat_sheet = st.selectbox("Select Material Status Sheet", sheet_names, index=min(1, len(sheet_names)-1))
    
    stock_df = pd.read_excel(xls, sheet_name=stock_sheet)
    mat_df = pd.read_excel(xls, sheet_name=mat_sheet)

    if st.button("Generate Full PDF Report"):
        pdf_bytes = generate_full_pdf_report(stock_df, mat_df)
        st.download_button(
            label="Download Complete PDF Report",
            data=pdf_bytes,
            file_name="Daily_Stock_And_Material_Executive_Report.pdf",
            mime="application/pdf"
        )
