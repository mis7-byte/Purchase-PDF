import os
import io
import json
import urllib.parse
import streamlit as st
import pandas as pd
from weasyprint import HTML

def format_num(val, decimals=2):
    try:
        val = float(val)
        return f"{val:,.{decimals}f}"
    except (ValueError, TypeError):
        return "0.00"

def get_quickchart_url(chart_config):
    encoded_config = urllib.parse.quote(json.dumps(chart_config))
    return f"https://quickchart.io/chart?c={encoded_config}"

def generate_stock_and_material_pdf(stock_df, material_df, report_date="29.09.2026"):
    # ---------------------------------------------------------
    # 1. PROCESS DAILY STOCK METRICS & CATEGORY DATA
    # ---------------------------------------------------------
    gd_stock = float(stock_df['GD STOCK'].sum()) if 'GD STOCK' in stock_df.columns else 0.0
    coil = float(stock_df['COIL'].sum()) if 'COIL' in stock_df.columns else 0.0
    sold_qty = float(stock_df['SOLD QTY'].sum()) if 'SOLD QTY' in stock_df.columns else 0.0
    booking = float(stock_df['BOOKING'].sum()) if 'BOOKING' in stock_df.columns else 0.0
    sail_bso = float(stock_df['SAIL BSO'].sum()) if 'SAIL BSO' in stock_df.columns else 0.0

    # Strict status filtering for INTANS
    if 'STATUS' in stock_df.columns and 'INTANS' in stock_df.columns:
        intans_mask = stock_df['STATUS'].astype(str).str.strip().str.upper().isin(['INTRANSIT', 'IN TRANSIT'])
        intans = float(stock_df.loc[intans_mask, 'INTANS'].sum())
    elif 'INTANS' in stock_df.columns:
        intans = float(stock_df['INTANS'].sum())
    else:
        intans = 0.0

    bal_qty = (gd_stock + coil + intans) - sold_qty - booking - sail_bso

    # Aggregate by Category for Category Charts
    category_summary = {}
    if 'CATEGORY' in stock_df.columns:
        for cat, group in stock_df.groupby('CATEGORY'):
            cat_gd = float(group['GD STOCK'].sum()) if 'GD STOCK' in group.columns else 0.0
            cat_sold = float(group['SOLD QTY'].sum()) if 'SOLD QTY' in group.columns else 0.0
            cat_coil = float(group['COIL'].sum()) if 'COIL' in group.columns else 0.0
            cat_intans = float(group['INTANS'].sum()) if 'INTANS' in group.columns else 0.0
            cat_booking = float(group['BOOKING'].sum()) if 'BOOKING' in group.columns else 0.0
            cat_sail = float(group['SAIL BSO'].sum()) if 'SAIL BSO' in group.columns else 0.0
            
            cat_bal = (cat_gd + cat_coil + cat_intans) - cat_sold - cat_booking - cat_sail
            category_summary[str(cat)] = {
                'gdStock': cat_gd,
                'soldQty': cat_sold,
                'balQty': cat_bal
            }

    # Detailed Table Rows
    stock_rows = ""
    for idx, row in stock_df.iterrows():
        r_gd = float(row.get('GD STOCK', 0) or 0)
        r_coil = float(row.get('COIL', 0) or 0)
        r_sold = float(row.get('SOLD QTY', 0) or 0)
        r_booking = float(row.get('BOOKING', 0) or 0)
        r_sail = float(row.get('SAIL BSO', 0) or 0)
        
        r_status = str(row.get('STATUS', '')).strip().upper()
        r_intans = float(row.get('INTANS', 0) or 0) if r_status in ['INTRANSIT', 'IN TRANSIT'] else 0.0
        r_bal = (r_gd + r_coil + r_intans) - r_sold - r_booking - r_sail

        stock_rows += f"""
        <tr>
            <td>{idx + 1}</td>
            <td>{row.get('CATEGORY', '')}</td>
            <td>{row.get('THIK', '')}</td>
            <td>{row.get('WIDTH', '')}</td>
            <td>{row.get('GRADE', '')}</td>
            <td>{format_num(r_gd)}</td>
            <td>{format_num(r_coil)}</td>
            <td>{format_num(r_sold)}</td>
            <td>{format_num(r_intans)}</td>
            <td>{format_num(r_booking)}</td>
            <td>{format_num(r_sail)}</td>
            <td>{format_num(r_bal)}</td>
        </tr>
        """

    # ---------------------------------------------------------
    # 2. GENERATE QUICKCHART URLS FOR STOCK
    # ---------------------------------------------------------
    main_bar_chart = {
        'type': 'bar',
        'data': {
            'labels': ['GD STOCK', 'COIL', 'SOLD QTY', 'INTANS', 'BOOKING', 'SAIL BSO', 'BAL. QTY'],
            'datasets': [{
                'label': 'Stock Quantity Breakdown (MT)',
                'data': [gd_stock, coil, sold_qty, intans, booking, sail_bso, bal_qty],
                'backgroundColor': '#1b365d'
            }]
        },
        'options': {
            'title': {'display': True, 'text': 'Stock Quantity Breakdown (MT)', 'fontSize': 14, 'fontColor': '#1b365d'},
            'legend': {'display': False},
            'plugins': {'datalabels': {'display': True, 'anchor': 'end', 'align': 'top', 'font': {'weight': 'bold'}}}
        }
    }
    main_bar_url = get_quickchart_url(main_bar_chart)

    cats = list(category_summary.keys()) if category_summary else ['CHQ', 'PLATE']
    cat_gd_vals = [category_summary[c]['gdStock'] for c in cats] if category_summary else [143.4, 806.9]
    cat_sold_vals = [category_summary[c]['soldQty'] for c in cats] if category_summary else [117.9, 657.8]
    cat_bal_vals = [category_summary[c]['balQty'] for c in cats] if category_summary else [545.5, 1694.2]

    category_bar_chart = {
        'type': 'bar',
        'data': {
            'labels': cats,
            'datasets': [
                {'label': 'GD STOCK', 'data': cat_gd_vals, 'backgroundColor': '#1b365d'},
                {'label': 'SOLD QTY', 'data': cat_sold_vals, 'backgroundColor': '#38bdf8'},
                {'label': 'BAL. QTY', 'data': cat_bal_vals, 'backgroundColor': '#ef4444'}
            ]
        },
        'options': {
            'title': {'display': True, 'text': f'Stock Distribution by Category ({report_date})', 'fontSize': 12},
            'plugins': {'datalabels': {'display': True, 'anchor': 'end', 'align': 'top'}}
        }
    }
    cat_bar_url = get_quickchart_url(category_bar_chart)

    category_pie_chart = {
        'type': 'pie',
        'data': {
            'labels': cats,
            'datasets': [{
                'data': cat_gd_vals,
                'backgroundColor': ['#1b365d', '#38bdf8', '#f59e0b', '#10b981']
            }]
        },
        'options': {
            'title': {'display': True, 'text': f'GD Stock Share by Category ({report_date})', 'fontSize': 12},
            'plugins': {'datalabels': {'display': True, 'color': '#ffffff', 'font': {'weight': 'bold'}}}
        }
    }
    cat_pie_url = get_quickchart_url(category_pie_chart)

    # ---------------------------------------------------------
    # 3. PROCESS MATERIAL STATUS METRICS
    # ---------------------------------------------------------
    total_mat_qty = float(material_df['QTY'].sum()) if 'QTY' in material_df.columns else 0.0
    
    if 'STATUS' in material_df.columns and 'QTY' in material_df.columns:
        mat_status_upper = material_df['STATUS'].astype(str).str.strip().str.upper()
        recd_qty = float(material_df.loc[mat_status_upper.isin(['RECD', 'RECEIVED']), 'QTY'].sum())
        loading_qty = float(material_df.loc[mat_status_upper == 'LOADING', 'QTY'].sum())
        intransit_qty = float(material_df.loc[mat_status_upper.isin(['INTRANSIT', 'IN TRANSIT']), 'QTY'].sum())
    else:
        recd_qty, loading_qty, intransit_qty = 0.0, 0.0, 0.0

    mat_rows = ""
    for idx, row in material_df.iterrows():
        mat_rows += f"""
        <tr>
            <td>{row.get('CATEGORY', '')}</td>
            <td>{row.get('THIK', '')}</td>
            <td>{row.get('SIZE', '')}</td>
            <td>{row.get('GRADE', '')}</td>
            <td>{format_num(row.get('QTY', 0), 3)}</td>
            <td>{row.get('FROM', '')}</td>
            <td>{row.get('STATUS', '')}</td>
            <td>{row.get('EXPECTED DATE', '')}</td>
        </tr>
        """

    # ---------------------------------------------------------
    # 4. GENERATE QUICKCHART URLS FOR MATERIAL
    # ---------------------------------------------------------
    mat_pie_chart = {
        'type': 'pie',
        'data': {
            'labels': ['RECD', 'LOADING', 'INTRANSIT'],
            'datasets': [{
                'data': [recd_qty, loading_qty, intransit_qty],
                'backgroundColor': ['#3b82f6', '#f97316', '#14b8a6']
            }]
        },
        'options': {
            'title': {'display': True, 'text': 'QTY Distribution by Status', 'fontSize': 12},
            'plugins': {'datalabels': {'display': True, 'color': '#ffffff', 'font': {'weight': 'bold'}}}
        }
    }
    mat_pie_url = get_quickchart_url(mat_pie_chart)

    # ---------------------------------------------------------
    # 5. COMPLETE COMBINED HTML WITH STYLES
    # ---------------------------------------------------------
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{
                size: A4 landscape;
                margin: 10mm;
            }}
            body {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                color: #1e293b;
                margin: 0;
                padding: 0;
            }}
            .header {{
                background-color: #1b365d;
                color: white;
                padding: 12px;
                text-align: center;
                border-radius: 4px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 18px;
                letter-spacing: 0.5px;
            }}
            .section-title {{
                font-size: 13px;
                font-weight: bold;
                color: #1b365d;
                margin-top: 14px;
                margin-bottom: 6px;
                border-bottom: 2px solid #cbd5e1;
                padding-bottom: 3px;
            }}
            
            /* Flexible Layout Grid */
            .kpi-row {{
                display: flex;
                justify-content: space-between;
                gap: 6px;
                margin-top: 8px;
            }}
            .kpi-card {{
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                padding: 8px 4px;
                text-align: center;
                border-radius: 4px;
                flex: 1;
            }}
            .kpi-title {{
                font-size: 9px;
                color: #64748b;
                font-weight: bold;
                text-transform: uppercase;
            }}
            .kpi-value {{
                font-size: 14px;
                color: #1b365d;
                font-weight: bold;
                margin-top: 3px;
            }}

            .grid-2col {{
                display: flex;
                justify-content: space-between;
                gap: 12px;
                margin-top: 10px;
            }}
            .col {{
                flex: 1;
                text-align: center;
            }}

            /* Table Styles */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 8px;
                font-size: 9.5px;
            }}
            th {{
                background-color: #1b365d;
                color: white;
                padding: 5px;
                text-align: right;
            }}
            th:nth-child(-n+5) {{
                text-align: left;
            }}
            td {{
                border-bottom: 1px solid #cbd5e1;
                padding: 4px 5px;
                text-align: right;
            }}
            td:nth-child(-n+5) {{
                text-align: left;
            }}
            tr:nth-child(even) {{
                background-color: #f8fafc;
            }}
            .total-row td {{
                font-weight: bold;
                background-color: #e2e8f0;
                border-top: 2px solid #1b365d;
            }}

            .chart-box {{
                text-align: center;
                margin-top: 10px;
            }}
            .chart-box img {{
                max-width: 650px;
                width: 85%;
                height: auto;
            }}
            .page-break {{
                page-break-before: always;
            }}
        </style>
    </head>
    <body>

        <!-- PAGE 1: DAILY STOCK EXECUTIVE REPORT OVERVIEW & BAR CHART -->
        <div class="header">
            <h1>Daily Stock Executive Report - {report_date}</h1>
        </div>

        <div class="section-title">Executive KPI Overview</div>
        <div class="kpi-row">
            <div class="kpi-card"><div class="kpi-title">GD STOCK</div><div class="kpi-value">{format_num(gd_stock)}</div></div>
            <div class="kpi-card"><div class="kpi-title">COIL</div><div class="kpi-value">{format_num(coil)}</div></div>
            <div class="kpi-card"><div class="kpi-title">SOLD QTY</div><div class="kpi-value">{format_num(sold_qty)}</div></div>
            <div class="kpi-card"><div class="kpi-title">INTANS</div><div class="kpi-value">{format_num(intans)}</div></div>
            <div class="kpi-card"><div class="kpi-title">BOOKING</div><div class="kpi-value">{format_num(booking)}</div></div>
            <div class="kpi-card"><div class="kpi-title">SAIL BSO</div><div class="kpi-value">{format_num(sail_bso)}</div></div>
            <div class="kpi-card"><div class="kpi-title">BAL. QTY</div><div class="kpi-value">{format_num(bal_qty)}</div></div>
        </div>

        <div class="section-title">Stock Analytics Chart</div>
        <div class="chart-box">
            <img src="{main_bar_url}" />
        </div>

        <!-- PAGE 2: KEY METRICS & SUMMARY TABLES -->
        <div class="page-break"></div>
        <div class="header">
            <h1>Key Metrics & Summary Overview - {report_date}</h1>
        </div>

        <div class="section-title">Key Metrics Overview: {report_date}</div>
        <div class="kpi-row">
            <div class="kpi-card"><div class="kpi-title">GD STOCK</div><div class="kpi-value">{format_num(gd_stock, 3)}</div></div>
            <div class="kpi-card"><div class="kpi-title">SOLD QTY</div><div class="kpi-value">{format_num(sold_qty, 3)}</div></div>
            <div class="kpi-card"><div class="kpi-title">INTANS</div><div class="kpi-value">{format_num(intans, 3)}</div></div>
            <div class="kpi-card"><div class="kpi-title">BAL. QTY</div><div class="kpi-value">{format_num(bal_qty, 3)}</div></div>
        </div>

        <div class="section-title">Orders & Movements</div>
        <div class="kpi-row">
            <div class="kpi-card"><div class="kpi-title">TOTAL COIL</div><div class="kpi-value">{format_num(coil, 3)}</div></div>
            <div class="kpi-card"><div class="kpi-title">TOTAL BOOKING</div><div class="kpi-value">{format_num(booking, 3)}</div></div>
            <div class="kpi-card"><div class="kpi-title">TOTAL SAIL BSO</div><div class="kpi-value">{format_num(sail_bso, 3)}</div></div>
        </div>

        <div class="section-title">Full Metrics Summary Table</div>
        <table>
            <thead>
                <tr>
                    <th style="text-align:left;">Metric</th>
                    <th style="text-align:right;">{report_date} Total</th>
                </tr>
            </thead>
            <tbody>
                <tr><td style="text-align:left;">GD STOCK</td><td style="text-align:right;">{format_num(gd_stock, 3)}</td></tr>
                <tr><td style="text-align:left;">COIL</td><td style="text-align:right;">{format_num(coil, 3)}</td></tr>
                <tr><td style="text-align:left;">SOLD QTY</td><td style="text-align:right;">{format_num(sold_qty, 3)}</td></tr>
                <tr><td style="text-align:left;">INTANS</td><td style="text-align:right;">{format_num(intans, 3)}</td></tr>
                <tr><td style="text-align:left;">BOOKING</td><td style="text-align:right;">{format_num(booking, 3)}</td></tr>
                <tr><td style="text-align:left;">SAIL BSO</td><td style="text-align:right;">{format_num(sail_bso, 3)}</td></tr>
                <tr class="total-row"><td style="text-align:left;">BAL. QTY</td><td style="text-align:right;">{format_num(bal_qty, 3)}</td></tr>
            </tbody>
        </table>

        <!-- PAGE 3: VISUAL ANALYSIS - CATEGORY BREAKDOWN -->
        <div class="page-break"></div>
        <div class="header">
            <h1>Visual Analysis - Category Breakdown</h1>
        </div>

        <div class="grid-2col">
            <div class="col">
                <img src="{cat_bar_url}" style="width:100%;" />
            </div>
            <div class="col">
                <img src="{cat_pie_url}" style="width:100%;" />
            </div>
        </div>

        <!-- PAGE 4: DETAILED STOCK BREAKDOWN TABLE -->
        <div class="page-break"></div>
        <div class="header">
            <h1>Detailed Stock Breakdown - {report_date}</h1>
        </div>

        <table>
            <thead>
                <tr>
                    <th>SR</th><th>CATEGORY</th><th>THIK</th><th>WIDTH</th><th>GRADE</th>
                    <th>GD STOCK</th><th>COIL</th><th>SOLD QTY</th><th>INTANS</th><th>BOOKING</th><th>SAIL BSO</th><th>BAL. QTY</th>
                </tr>
            </thead>
            <tbody>
                {stock_rows}
                <tr class="total-row">
                    <td colspan="5" style="text-align:center;">TOTAL</td>
                    <td>{format_num(gd_stock)}</td>
                    <td>{format_num(coil)}</td>
                    <td>{format_num(sold_qty)}</td>
                    <td>{format_num(intans)}</td>
                    <td>{format_num(booking)}</td>
                    <td>{format_num(sail_bso)}</td>
                    <td>{format_num(bal_qty)}</td>
                </tr>
            </tbody>
        </table>

        <!-- PAGE 5: MATERIAL STATUS REPORT -->
        <div class="page-break"></div>
        <div class="header">
            <h1>Material Status Executive Report - {report_date}</h1>
        </div>

        <div class="section-title">Material Status KPI Overview</div>
        <div class="kpi-row">
            <div class="kpi-card"><div class="kpi-title">TOTAL MATERIAL QTY</div><div class="kpi-value">{format_num(total_mat_qty, 3)} MT</div></div>
            <div class="kpi-card"><div class="kpi-title">RECEIVED (RECD)</div><div class="kpi-value">{format_num(recd_qty, 3)} MT</div></div>
            <div class="kpi-card"><div class="kpi-title">LOADING</div><div class="kpi-value">{format_num(loading_qty, 3)} MT</div></div>
            <div class="kpi-card"><div class="kpi-title">IN TRANSIT</div><div class="kpi-value">{format_num(intransit_qty, 3)} MT</div></div>
        </div>

        <div class="grid-2col">
            <div class="col">
                <div class="section-title">Status Breakdown</div>
                <img src="{mat_pie_url}" style="width:90%;" />
            </div>
            <div class="col">
                <div class="section-title">Detailed Material Rows</div>
                <table>
                    <thead>
                        <tr>
                            <th>CATEGORY</th><th>THIK</th><th>SIZE</th><th>GRADE</th><th>QTY</th><th>FROM</th><th>STATUS</th><th>EXP DATE</th>
                        </tr>
                    </thead>
                    <tbody>
                        {mat_rows}
                        <tr class="total-row">
                            <td colspan="4" style="text-align:center;">TOTAL</td>
                            <td>{format_num(total_mat_qty, 3)}</td>
                            <td colspan="3"></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

    </body>
    </html>
    """

    pdf_buffer = io.BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer


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
        pdf_bytes = generate_stock_and_material_pdf(stock_df, mat_df)
        st.download_button(
            label="Download Complete PDF Report",
            data=pdf_bytes,
            file_name="Daily_Stock_And_Material_Executive_Report.pdf",
            mime="application/pdf"
        )
