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

# --- MODERN PDF COLOR PALETTE ---
PRIMARY_COLOR = (26, 54, 93)     # Deep Navy (#1A365D)
SECONDARY_COLOR = (66, 153, 225) # Soft Blue (#4299E1)
BG_CARD = (240, 244, 248)        # Light Blue-Gray (#F0F4F8)
TEXT_DARK = (45, 55, 72)         # Charcoal Dark Text (#2D3748)
TEXT_MUTED = (113, 128, 150)     # Gray Label Text (#718096)
BORDER_COLOR = (226, 232, 240)   # Light Border Gray (#E2E8F0)
ROW_ALT = (248, 250, 252)        # Alternating Row Striping (#F8FAFC)

# Badge Colors
GREEN_BG = (220, 252, 231)
GREEN_TEXT = (22, 101, 52)
RED_BG = (254, 226, 226)
RED_TEXT = (153, 27, 27)


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
    """Generates a clean category bar chart."""
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=200)
    
    categories = cat_df["CAT."].astype(str).tolist()
    x = range(len(categories))
    width = 0.25

    rects1 = ax.bar([i - width for i in x], cat_df["GD STOCK"], width=width, label="GD STOCK", color="#1A365D")
    rects2 = ax.bar(x, cat_df["SOLD QTY"], width=width, label="SOLD QTY", color="#4299E1")
    rects3 = ax.bar([i + width for i in x], cat_df["BAL. QTY"], width=width, label="BAL. QTY", color="#E74C3C")

    for rects in [rects1, rects2, rects3]:
        ax.bar_label(rects, fmt="%.1f", padding=3, fontsize=7, color="#2D3748", fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, fontsize=8, color="#2D3748", fontweight="bold")
    ax.set_title(f"Stock Distribution by Category ({date_str})", fontsize=10, fontweight="bold", color="#1A365D", pad=12)
    ax.legend(fontsize=7, loc="upper left", frameon=True, facecolor="#F8FAFC", edgecolor="none")
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E0")
    ax.spines["bottom"].set_color("#CBD5E0")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#CBD5E0")

    max_val = max(cat_df[["GD STOCK", "SOLD QTY", "BAL. QTY"]].max().max(), 1)
    ax.set_ylim(0, max_val * 1.18)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_comparison_bar_chart_bytes(primary_sums, compare_sums, date_str, compare_date):
    """Generates a comparison bar chart matching the Streamlit metric comparison chart."""
    fig, ax = plt.subplots(figsize=(6.5, 3.5), dpi=200)
    
    metrics = METRIC_COLS
    x = range(len(metrics))
    width = 0.35

    vals_primary = [primary_sums.get(m, 0.0) for m in metrics]
    vals_compare = [compare_sums.get(m, 0.0) for m in metrics]

    rects1 = ax.bar([i - width / 2 for i in x], vals_primary, width=width, label=date_str, color="#0068C9")
    rects2 = ax.bar([i + width / 2 for i in x], vals_compare, width=width, label=compare_date, color="#83C8FF")

    for rects in [rects1, rects2]:
        ax.bar_label(rects, fmt="%.1f", padding=2, fontsize=6.5, color="#2D3748", fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(metrics, fontsize=7, color="#2D3748", fontweight="bold", rotation=15)
    ax.set_title(f"Metric Comparison: {date_str} vs {compare_date}", fontsize=9, fontweight="bold", color="#1A365D", pad=10)
    ax.legend(fontsize=7, loc="upper right", frameon=True, facecolor="#F8FAFC", edgecolor="none")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E0")
    ax.spines["bottom"].set_color("#CBD5E0")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#CBD5E0")

    max_val = max(max(vals_primary), max(vals_compare), 1)
    ax.set_ylim(0, max_val * 1.18)

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
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def draw_metric_card(pdf, x, y, width, height, label, val, diff=None, compare_date=None):
    """Helper to draw KPI card with optional comparison badge."""
    pdf.set_fill_color(*BG_CARD)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.rect(x, y, width, height, style="FD")
    
    # Metric Label
    pdf.set_xy(x, y + 2)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(width, 4, label, align="C")
    
    # Metric Value
    pdf.set_xy(x, y + 6.5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(width, 5, f"{val:,.3f}", align="C")

    # Comparison Badge
    if diff is not None and compare_date is not None:
        arrow = "^" if diff >= 0 else "v"
        badge_text = f"{arrow} {diff:+,.3f} vs {compare_date}"
        
        bg_col = GREEN_BG if diff >= 0 else RED_BG
        txt_col = GREEN_TEXT if diff >= 0 else RED_TEXT
        
        badge_w = width - 8
        badge_h = 4.5
        badge_x = x + 4
        badge_y = y + 12.5

        pdf.set_fill_color(*bg_col)
        pdf.set_draw_color(*bg_col)
        pdf.rect(badge_x, badge_y, badge_w, badge_h, style="FD")

        pdf.set_xy(badge_x, badge_y + 0.5)
        pdf.set_font("Helvetica", "B", 6)
        pdf.set_text_color(*txt_col)
        pdf.cell(badge_w, 3.5, badge_text, align="C")


def generate_pdf_report(date_str, df_primary, primary_sums, compare_date=None, compare_sums=None):
    """Generates a styled PDF report supporting date comparisons."""
    pdf = AppPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Header Title Text
    header_title = f"Dashboard Overview - {date_str}"
    if compare_date:
        header_title = f"Dashboard Comparison - {date_str} vs {compare_date}"

    # Header Banner (Centered Title across 297mm page width)
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.rect(0, 0, 297, 22, style="F")
    
    pdf.set_xy(0, 6)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(297, 10, header_title, align="C")
    
    pdf.set_y(26)

    # 1. KEY METRICS CARDS
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, f"Key Metrics Overview: {date_str}", ln=True)
    pdf.ln(1)

    row1_metrics = ["GD STOCK", "SOLD QTY", "INTANS", "BAL. QTY"]
    card_w = 66
    card_h = 18 if compare_sums is not None else 15
    start_x = 12
    start_y = pdf.get_y()

    for idx, metric in enumerate(row1_metrics):
        x = start_x + idx * (card_w + 3)
        val = primary_sums.get(metric, 0.0)
        diff = (val - compare_sums.get(metric, 0.0)) if compare_sums is not None else None
        
        draw_metric_card(pdf, x, start_y, card_w, card_h, metric, val, diff, compare_date)

    pdf.set_y(start_y + card_h + 5)

    # Orders & Movements
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, "Orders & Movements", ln=True)
    pdf.ln(1)

    row2_metrics = [("TOTAL COIL", "COIL"), ("TOTAL BOOKING", "BOOKING"), ("TOTAL SAIL BSO", "SAIL BSO")]
    start_y = pdf.get_y()
    card_w_r2 = 88

    for idx, (label, key) in enumerate(row2_metrics):
        x = start_x + idx * (card_w_r2 + 4)
        val = primary_sums.get(key, 0.0)
        diff = (val - compare_sums.get(key, 0.0)) if compare_sums is not None else None
        
        draw_metric_card(pdf, x, start_y, card_w_r2, card_h, label, val, diff, compare_date)

    pdf.set_y(start_y + card_h + 6)

    # 2. FULL METRICS SUMMARY TABLE
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, "Full Metrics Summary Table", ln=True)
    pdf.ln(1)

    has_compare = compare_sums is not None
    sum_cols = ["Metric", f"{date_str} Total"]
    sum_widths = [136, 136]
    if has_compare:
        sum_cols = ["Metric", f"{date_str} Total", f"{compare_date} Total", "Difference"]
        sum_widths = [68, 68, 68, 68]

    # Table Header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(*PRIMARY_COLOR)
    for col_name, w in zip(sum_cols, sum_widths):
        pdf.cell(w, 5.5, col_name, border=1, align="C", fill=True)
    pdf.ln()

    # Table Rows
    pdf.set_font("Helvetica", "", 8)
    pdf.set_draw_color(*BORDER_COLOR)
    for idx, m in enumerate(METRIC_COLS):
        bg = ROW_ALT if idx % 2 == 1 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*TEXT_DARK)
        
        pdf.cell(sum_widths[0], 5, f"  {m}", border="LRB", align="L", fill=True)
        pdf.cell(sum_widths[1], 5, f"{primary_sums.get(m, 0):,.3f}  ", border="LRB", align="R", fill=True)
        if has_compare:
            p_val = primary_sums.get(m, 0)
            c_val = compare_sums.get(m, 0)
            pdf.cell(sum_widths[2], 5, f"{c_val:,.3f}  ", border="LRB", align="R", fill=True)
            pdf.cell(sum_widths[3], 5, f"{p_val - c_val:+,.3f}  ", border="LRB", align="R", fill=True)
        pdf.ln()

    # 3. VISUAL ANALYSIS (CHARTS PAGE)
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 8, "Visual Analysis", ln=True)
    pdf.ln(2)

    chart_y = pdf.get_y()
    img_w, img_h = 132, 75

    if "CAT." in df_primary.columns:
        cat_df = df_primary.groupby("CAT.")[METRIC_COLS].sum().reset_index()
        bar_buf = generate_bar_chart_bytes(cat_df, date_str)
        pdf.image(bar_buf, x=12, y=chart_y, w=img_w, h=img_h)

    if has_compare:
        comp_chart_buf = generate_comparison_bar_chart_bytes(primary_sums, compare_sums, date_str, compare_date)
        pdf.image(comp_chart_buf, x=150, y=chart_y, w=img_w, h=img_h)

    # 4. DETAILED DATA TABLE
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 8, f"Detailed Data Table ({date_str})", ln=True)
    pdf.ln(2)

    table_cols = ["SR.NO.", "CAT.", "THIK", "WIDTH", "GD STOCK", "COIL", "SOLD QTY", "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"]
    col_widths = [14, 20, 16, 18, 25, 20, 25, 22, 22, 22, 28]

    def draw_table_header():
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*PRIMARY_COLOR)
        pdf.set_text_color(255, 255, 255)
        pdf.set_draw_color(*PRIMARY_COLOR)
        for col, w in zip(table_cols, col_widths):
            pdf.cell(w, 6, col, border=1, align="C", fill=True)
        pdf.ln()

    draw_table_header()

    # Data Rows
    pdf.set_font("Helvetica", "", 8)
    pdf.set_draw_color(*BORDER_COLOR)
    
    for r_idx, (_, row) in enumerate(df_primary.iterrows()):
        if pdf.get_y() > 180:
            pdf.add_page()
            draw_table_header()

        bg = ROW_ALT if r_idx % 2 == 1 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*TEXT_DARK)

        pdf.cell(col_widths[0], 5, str(int(row["SR.NO."])) if pd.notna(row.get("SR.NO.")) else "", border="LRB", align="C", fill=True)
        pdf.cell(col_widths[1], 5, str(row.get("CAT.", ""))[:12], border="LRB", align="L", fill=True)
        pdf.cell(col_widths[2], 5, str(row.get("THIK", "")), border="LRB", align="C", fill=True)
        pdf.cell(col_widths[3], 5, str(row.get("WIDTH", "")), border="LRB", align="C", fill=True)
        pdf.cell(col_widths[4], 5, f"{row.get('GD STOCK', 0):,.2f}", border="LRB", align="R", fill=True)
        pdf.cell(col_widths[5], 5, f"{row.get('COIL', 0):,.2f}", border="LRB", align="R", fill=True)
        pdf.cell(col_widths[6], 5, f"{row.get('SOLD QTY', 0):,.2f}", border="LRB", align="R", fill=True)
        pdf.cell(col_widths[7], 5, f"{row.get('INTANS', 0):,.2f}", border="LRB", align="R", fill=True)
        pdf.cell(col_widths[8], 5, f"{row.get('BOOKING', 0):,.2f}", border="LRB", align="R", fill=True)
        pdf.cell(col_widths[9], 5, f"{row.get('SAIL BSO', 0):,.2f}", border="LRB", align="R", fill=True)
        pdf.cell(col_widths[10], 5, f"{row.get('BAL. QTY', 0):,.2f}", border="LRB", align="R", fill=True)
        pdf.ln()

    # Total Summary Row
    if pdf.get_y() > 180:
        pdf.add_page()
        draw_table_header()

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 238, 222)
    pdf.set_text_color(20, 83, 45)
    pdf.set_draw_color(180, 220, 185)

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
                    text_auto=".1f"
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
