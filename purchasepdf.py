import io
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF

# --- PAGE SETUP ---
st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide")

NUMERIC_COLS = [
    "THIK", "WIDTH", "GD STOCK", "COIL",
    "SOLD QTY", "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"
]
METRIC_COLS = [
    "GD STOCK", "COIL", "SOLD QTY",
    "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"
]


# --- HELPER FUNCTIONS ---
def parse_sheet_data(uploaded_file, sheet_name):
    """Parses a specific date tab, ignoring Excel summary total rows and parsing unit strings."""
    df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=1)
    
    # Clean column names
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Drop empty rows
    df = df.dropna(how="all")
    
    # Filter out summary/total rows at the bottom
    if "SR.NO." in df.columns:
        df["SR.NO._NUM"] = pd.to_numeric(df["SR.NO."], errors="coerce")
        df = df[df["SR.NO._NUM"].notna()].copy()
        df = df.drop(columns=["SR.NO._NUM"])

    # Clean THIK column (strip unit strings like 'mm')
    if "THIK" in df.columns:
        df["THIK"] = df["THIK"].astype(str).str.replace(r"(?i)\s*mm", "", regex=True)

    # Convert numeric metrics safely
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            df[col] = 0.0

    return df


def generate_pdf_report(date_str, df_primary, primary_sums, compare_date_str=None, compare_sums=None):
    """Generates a PDF styled exactly like the Streamlit App layout."""
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    
    # --- PAGE TITLE ---
    pdf.set_font("Helvetica", "B", 16)
    title_text = f"Stock Summary Report - {date_str}" if not compare_date_str else f"Stock Comparison Report: {date_str} vs {compare_date_str}"
    pdf.cell(0, 10, title_text, ln=True, align="C")
    pdf.ln(3)

    # --- SECTION 1: KEY METRICS OVERVIEW (App KPI Cards Layout) ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "Key Metrics Overview", ln=True)
    pdf.ln(2)

    # KPI Card Layout
    kpi_list = [
        ("GD STOCK", primary_sums.get("GD STOCK", 0)),
        ("SOLD QTY", primary_sums.get("SOLD QTY", 0)),
        ("INTANS", primary_sums.get("INTANS", 0)),
        ("BAL. QTY", primary_sums.get("BAL. QTY", 0)),
        ("TOTAL COIL", primary_sums.get("COIL", 0)),
        ("TOTAL BOOKING", primary_sums.get("BOOKING", 0)),
        ("TOTAL SAIL BSO", primary_sums.get("SAIL BSO", 0))
    ]

    card_w = 38
    card_h = 16

    for idx, (label, val) in enumerate(kpi_list):
        if idx > 0 and idx % 7 == 0:
            pdf.ln(card_h + 3)
        
        x_pos = 10 + (idx % 7) * (card_w + 1)
        y_pos = pdf.get_y()
        
        # Draw Card Box
        pdf.rect(x_pos, y_pos, card_w, card_h)
        
        # Card Label
        pdf.set_xy(x_pos, y_pos + 2)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(card_w, 4, label, align="C")
        
        # Card Value
        pdf.set_xy(x_pos, y_pos + 7)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(card_w, 6, f"{val:,.2f}", align="C")

    pdf.set_y(pdf.get_y() + card_h + 6)

    # --- SECTION 2: DETAILED DATA TABLE ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, f"Detailed Data Table ({date_str})", ln=True)
    pdf.ln(2)

    table_cols = ["SR.NO.", "CAT.", "THIK", "WIDTH", "GD STOCK", "COIL", "SOLD QTY", "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"]
    col_widths = [14, 20, 16, 18, 25, 20, 25, 22, 22, 22, 28]

    # Header Row
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    for col, w in zip(table_cols, col_widths):
        pdf.cell(w, 6, col, border=1, align="C", fill=True)
    pdf.ln()

    # Data Rows
    pdf.set_font("Helvetica", "", 8)
    for _, row in df_primary.iterrows():
        pdf.cell(col_widths[0], 5, str(int(row["SR.NO."])) if pd.notna(row.get("SR.NO.")) else "", border=1, align="C")
        pdf.cell(col_widths[1], 5, str(row.get("CAT.", ""))[:12], border=1, align="L")
        pdf.cell(col_widths[2], 5, str(row.get("THIK", "")), border=1, align="C")
        pdf.cell(col_widths[3], 5, str(row.get("WIDTH", "")), border=1, align="C")
        pdf.cell(col_widths[4], 5, f"{row.get('GD STOCK', 0):,.2f}", border=1, align="R")
        pdf.cell(col_widths[5], 5, f"{row.get('COIL', 0):,.2f}", border=1, align="R")
        pdf.cell(col_widths[6], 5, f"{row.get('SOLD QTY', 0):,.2f}", border=1, align="R")
        pdf.cell(col_widths[7], 5, f"{row.get('INTANS', 0):,.2f}", border=1, align="R")
        pdf.cell(col_widths[8], 5, f"{row.get('BOOKING', 0):,.2f}", border=1, align="R")
        pdf.cell(col_widths[9], 5, f"{row.get('SAIL BSO', 0):,.2f}", border=1, align="R")
        pdf.cell(col_widths[10], 5, f"{row.get('BAL. QTY', 0):,.2f}", border=1, align="R")
        pdf.ln()

    # Total Summary Row at Bottom
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(200, 230, 200) # Highlight total row
    
    pdf.cell(col_widths[0] + col_widths[1] + col_widths[2] + col_widths[3], 6, "TOTAL", border=1, align="C", fill=True)
    for col, w in zip(METRIC_COLS, col_widths[4:]):
        pdf.cell(w, 6, f"{primary_sums.get(col, 0):,.2f}", border=1, align="R", fill=True)
    pdf.ln()

    return bytes(pdf.output())


# --- MAIN APP LAYOUT ---
st.title("📊 Inventory & Stock Analytics Dashboard")

uploaded_file = st.sidebar.file_uploader("Upload Daily Stock Excel File", type=["xlsx", "xls"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    all_sheets = xls.sheet_names

    # Detect tabs matching date pattern DD.MM.YYYY
    date_sheets = [s for s in all_sheets if re.match(r"^\d{2}\.\d{2}\.\d{4}$", s.strip())]

    if not date_sheets:
        st.error("No tabs found matching the date format 'DD.MM.YYYY' (e.g., 29.09.2026). Please check sheet tab names.")
        st.stop()

    selected_date = st.sidebar.selectbox("Select Primary Date", date_sheets)
    enable_compare = st.sidebar.checkbox("Compare with another date")

    compare_date = None
    if enable_compare:
        remaining_dates = [d for d in date_sheets if d != selected_date]
        if remaining_dates:
            compare_date = st.sidebar.selectbox("Select Comparison Date", remaining_dates)
        else:
            st.sidebar.warning("Add more date tabs to compare.")

    # Load & parse data
    df_primary = parse_sheet_data(uploaded_file, selected_date)
    primary_sums = df_primary[METRIC_COLS].sum()

    df_compare = None
    compare_sums = None
    if compare_date:
        df_compare = parse_sheet_data(uploaded_file, compare_date)
        compare_sums = df_compare[METRIC_COLS].sum()

    # --- TOP KPI METRICS OVERVIEW ---
    st.header(f"📌 Key Metrics Overview: {selected_date}")

    # Row 1: Core Stock Quantities
    r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
    for col_widget, metric in zip([r1_col1, r1_col2, r1_col3, r1_col4], ["GD STOCK", "SOLD QTY", "INTANS", "BAL. QTY"]):
        with col_widget:
            val = primary_sums[metric]
            delta_val = f"{val - compare_sums[metric]:+,.3f} vs {compare_date}" if compare_sums is not None else None
            st.metric(label=metric, value=f"{val:,.3f}", delta=delta_val)

    st.markdown("### 📦 Orders & Movements")
    
    # Row 2: Coil, Booking, Sail BSO Sums
    r2_col1, r2_col2, r2_col3 = st.columns(3)
    for col_widget, metric in zip([r2_col1, r2_col2, r2_col3], ["COIL", "BOOKING", "SAIL BSO"]):
        with col_widget:
            val = primary_sums[metric]
            delta_val = f"{val - compare_sums[metric]:+,.3f} vs {compare_date}" if compare_sums is not None else None
            st.metric(label=f"TOTAL {metric}", value=f"{val:,.3f}", delta=delta_val)

    # --- EXPANDABLE COMPLETE METRICS TABLE ---
    with st.expander("🔢 View Full Metrics Summary Table"):
        summary_data = {"Metric": METRIC_COLS, f"{selected_date} Total": [primary_sums[m] for m in METRIC_COLS]}
        if compare_sums is not None:
            summary_data[f"{compare_date} Total"] = [compare_sums[m] for m in METRIC_COLS]
            summary_data["Difference"] = [primary_sums[m] - compare_sums[m] for m in METRIC_COLS]

        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

    # --- CHARTS SECTION ---
    st.markdown("---")
    st.header("📈 Visual Analysis")

    chart_tab1, chart_tab2 = st.tabs(["Category Breakdown", "Date Comparison"])

    with chart_tab1:
        if "CAT." in df_primary.columns:
            cat_df = df_primary.groupby("CAT.")[METRIC_COLS].sum().reset_index()

            col_left, col_right = st.columns(2)
            with col_left:
                fig_bar = px.bar(
                    cat_df, x="CAT.", y=["GD STOCK", "SOLD QTY", "BAL. QTY"],
                    barmode="group", title=f"Stock Distribution by Category ({selected_date})"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_right:
                fig_pie = px.pie(
                    cat_df, names="CAT.", values="GD STOCK",
                    title=f"GD Stock Share by Category ({selected_date})"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("Column 'CAT.' not found in data.")

    with chart_tab2:
        if compare_sums is not None:
            comp_df = pd.DataFrame({
                "Metric": METRIC_COLS,
                selected_date: primary_sums.values,
                compare_date: compare_sums.values
            }).melt(id_vars="Metric", var_name="Date", value_name="Total Quantity")

            fig_comp = px.bar(
                comp_df, x="Metric", y="Total Quantity", color="Date",
                barmode="group", title=f"Metric Comparison: {selected_date} vs {compare_date}"
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.info("Enable 'Compare with another date' in the sidebar to view comparison charts.")

    # --- DATA TABLE VIEW ---
    st.markdown("---")
    st.header(f"📄 Detailed Data Table ({selected_date})")

    df_display = df_primary.copy()
    total_row = {col: "" for col in df_display.columns}
    total_row["SR.NO."] = "TOTAL"
    for col in METRIC_COLS:
        total_row[col] = primary_sums[col]

    df_display = pd.concat([df_display, pd.DataFrame([total_row])], ignore_index=True)
    st.dataframe(df_display, use_container_width=True)

    # --- PDF EXPORT SECTION ---
    st.markdown("---")
    st.header("📥 Export Report")

    pdf_bytes = generate_pdf_report(
        date_str=selected_date,
        df_primary=df_primary,
        primary_sums=primary_sums,
        compare_date_str=compare_date,
        compare_sums=compare_sums
    )

    filename = f"Stock_Report_{selected_date}.pdf" if not compare_date else f"Stock_Comparison_{selected_date}_vs_{compare_date}.pdf"

    st.download_button(
        label="📄 Download PDF Report",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf"
    )

else:
    st.info("👈 Please upload your stock Excel file from the sidebar to begin.")
