import io
import re
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
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


def generate_bar_chart_bytes(cat_df, date_str):
    """Generates a clean bar chart with data labels above bars using Matplotlib."""
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=200)
    
    categories = cat_df["CAT."].astype(str).tolist()
    x = range(len(categories))
    width = 0.25

    # Plot bars
    rects1 = ax.bar([i - width for i in x], cat_df["GD STOCK"], width=width, label="GD STOCK", color="#1f77b4")
    rects2 = ax.bar(x, cat_df["SOLD QTY"], width=width, label="SOLD QTY", color="#aec7e8")
    rects3 = ax.bar([i + width for i in x], cat_df["BAL. QTY"], width=width, label="BAL. QTY", color="#d62728")

    # Add data labels on top of each bar
    for rects in [rects1, rects2, rects3]:
        ax.bar_label(rects, fmt="%.1f", padding=3, fontsize=7, rotation=0)

    # Styling & Clean Aesthetics
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_title(f"Stock Distribution by Category ({date_str})", fontsize=10, fontweight="bold", pad=12)
    ax.legend(fontsize=7, loc="upper left")
    
    # Hide top and right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    # Add y-axis headroom so labels aren't cut off at the top
    max_val = max(cat_df[["GD STOCK", "SOLD QTY", "BAL. QTY"]].max().max(), 1)
    ax.set_ylim(0, max_val * 1.18)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_pie_chart_bytes(cat_df, date_str):
    """Generates a clean pie chart with percentages and category labels."""
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=200)
    
    valid_df = cat_df[cat_df["GD STOCK"] > 0]
    if valid_df.empty:
        valid_df = cat_df

    wedges, texts, autotexts = ax.pie(
        valid_df["GD STOCK"], 
        labels=valid_df["CAT."], 
        autopct="%1.1f%%", 
        startangle=90, 
        pctdistance=0.75,
        colors=["#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c"],
        textprops=dict(fontsize=8)
    )

    for autotext in autotexts:
        autotext.set_fontweight("bold")
        autotext.set_fontsize(8)

    ax.set_title(f"GD Stock Share by Category ({date_str})", fontsize=10, fontweight="bold", pad=12)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


class AppPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-10)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def generate_pdf_report(date_str, df_primary, primary_sums, compare_date=None, compare_sums=None):
    """Generates a multi-page PDF report matching dashboard layouts cleanly."""
    pdf = AppPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Dashboard Banner
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, f"Dashboard Overview - {date_str}", ln=True, align="L")
    pdf.ln(2)

    # ---------------------------------------------------------
    # 1. KEY METRICS OVERVIEW & ORDERS & MOVEMENTS
    # ---------------------------------------------------------
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, f"Key Metrics Overview: {date_str}", ln=True)
    pdf.ln(2)

    # Core Stock Cards
    row1_metrics = [
        ("GD STOCK", primary_sums.get("GD STOCK", 0)),
        ("SOLD QTY", primary_sums.get("SOLD QTY", 0)),
        ("INTANS", primary_sums.get("INTANS", 0)),
        ("BAL. QTY", primary_sums.get("BAL. QTY", 0)),
    ]

    card_w = 65
    card_h = 15
    start_x = 10
    start_y = pdf.get_y()

    for idx, (label, val) in enumerate(row1_metrics):
        x = start_x + idx * (card_w + 3)
        pdf.rect(x, start_y, card_w, card_h)
        pdf.set_xy(x, start_y + 2)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(card_w, 4, label, align="C")
        pdf.set_xy(x, start_y + 7)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(card_w, 6, f"{val:,.3f}", align="C")

    pdf.set_y(start_y + card_h + 4)

    # Orders & Movements
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, "Orders & Movements", ln=True)
    pdf.ln(2)

    row2_metrics = [
        ("TOTAL COIL", primary_sums.get("COIL", 0)),
        ("TOTAL BOOKING", primary_sums.get("BOOKING", 0)),
        ("TOTAL SAIL BSO", primary_sums.get("SAIL BSO", 0)),
    ]

    start_y = pdf.get_y()
    card_w_r2 = 87
    for idx, (label, val) in enumerate(row2_metrics):
        x = start_x + idx * (card_w_r2 + 4)
        pdf.rect(x, start_y, card_w_r2, card_h)
        pdf.set_xy(x, start_y + 2)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(card_w_r2, 4, label, align="C")
        pdf.set_xy(x, start_y + 7)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(card_w_r2, 6, f"{val:,.3f}", align="C")

    pdf.set_y(start_y + card_h + 6)

    # ---------------------------------------------------------
    # 2. FULL METRICS SUMMARY TABLE
    # ---------------------------------------------------------
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Full Metrics Summary Table", ln=True)
    pdf.ln(1)

    has_compare = compare_sums is not None
    sum_cols = ["Metric", f"{date_str} Total"]
    sum_widths = [135, 135]
    if has_compare:
        sum_cols = ["Metric", f"{date_str} Total", f"{compare_date} Total", "Difference"]
        sum_widths = [70, 70, 70, 60]

    # Table Header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    for col_name, w in zip(sum_cols, sum_widths):
        pdf.cell(w, 5, col_name, border=1, align="C", fill=True)
    pdf.ln()

    # Table Rows
    pdf.set_font("Helvetica", "", 8)
    for m in METRIC_COLS:
        pdf.cell(sum_widths[0], 5, m, border=1, align="L")
        pdf.cell(sum_widths[1], 5, f"{primary_sums.get(m, 0):,.3f}", border=1, align="R")
        if has_compare:
            p_val = primary_sums.get(m, 0)
            c_val = compare_sums.get(m, 0)
            pdf.cell(sum_widths[2], 5, f"{c_val:,.3f}", border=1, align="R")
            pdf.cell(sum_widths[3], 5, f"{p_val - c_val:+,.3f}", border=1, align="R")
        pdf.ln()

    # ---------------------------------------------------------
    # 3. VISUAL ANALYSIS (CHARTS PAGE)
    # ---------------------------------------------------------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Visual Analysis", ln=True)
    pdf.ln(2)

    if "CAT." in df_primary.columns:
        cat_df = df_primary.groupby("CAT.")[METRIC_COLS].sum().reset_index()
        
        # Generate chart images with data labels
        bar_buf = generate_bar_chart_bytes(cat_df, date_str)
        pie_buf = generate_pie_chart_bytes(cat_df, date_str)

        chart_y = pdf.get_y()
        img_w, img_h = 130, 75

        pdf.image(bar_buf, x=10, y=chart_y, w=img_w, h=img_h)
        pdf.image(pie_buf, x=145, y=chart_y, w=img_w, h=img_h)

    # ---------------------------------------------------------
    # 4. DETAILED DATA TABLE
    # ---------------------------------------------------------
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, f"Detailed Data Table ({date_str})", ln=True)
    pdf.ln(3)

    table_cols = ["SR.NO.", "CAT.", "THIK", "WIDTH", "GD STOCK", "COIL", "SOLD QTY", "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"]
    col_widths = [14, 20, 16, 18, 25, 20, 25, 22, 22, 22, 28]

    def draw_table_header():
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(230, 230, 230)
        for col, w in zip(table_cols, col_widths):
            pdf.cell(w, 6, col, border=1, align="C", fill=True)
        pdf.ln()

    draw_table_header()

    # Data Rows
    pdf.set_font("Helvetica", "", 8)
    for _, row in df_primary.iterrows():
        if pdf.get_y() > 180:
            pdf.add_page()
            draw_table_header()

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

    # Total Summary Row
    if pdf.get_y() > 180:
        pdf.add_page()
        draw_table_header()

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(200, 230, 200)

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
                    barmode="group", title=f"Stock Distribution by Category ({selected_date})",
                    text_auto=".1f"  # Adds data labels to Plotly interactive view
                )
                fig_bar.update_traces(textposition="outside")
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_right:
                fig_pie = px.pie(
                    cat_df, names="CAT.", values="GD STOCK",
                    title=f"GD Stock Share by Category ({selected_date})"
                )
                fig_pie.update_traces(textinfo="percent+label")
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
                barmode="group", title=f"Metric Comparison: {selected_date} vs {compare_date}",
                text_auto=".1f"
            )
            fig_comp.update_traces(textposition="outside")
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
        compare_date=compare_date,
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
