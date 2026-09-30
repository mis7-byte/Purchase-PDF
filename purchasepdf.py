import io
import re
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from fpdf import FPDF

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Inventory & Material Status Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONSTANTS & CONFIGURATIONS ---
NUMERIC_COLS = [
    "THIK", "WIDTH", "GD STOCK", "COIL",
    "SOLD QTY", "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"
]
METRIC_COLS = [
    "GD STOCK", "COIL", "SOLD QTY",
    "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"
]

# Modern Executive Color Palette for PDF Reports
PRIMARY_COLOR = (26, 54, 93)      # Deep Navy (#1A365D)
SECONDARY_COLOR = (66, 153, 225)  # Soft Blue (#4299E1)
BG_CARD = (240, 244, 248)         # Light Blue-Gray (#F0F4F8)
TEXT_DARK = (45, 55, 72)          # Charcoal Text (#2D3748)
TEXT_MUTED = (113, 128, 150)      # Gray Label Text (#718096)
BORDER_COLOR = (226, 232, 240)    # Border Gray (#E2E8F0)
ROW_ALT = (248, 250, 252)         # Alternating Row Striping (#F8FAFC)

GREEN_BG = (220, 252, 231)
GREEN_TEXT = (22, 101, 52)
RED_BG = (254, 226, 226)
RED_TEXT = (153, 27, 27)


# --- DATA PARSING FUNCTIONS ---
def parse_stock_sheet(uploaded_file, sheet_name):
    """Parses daily stock tabs matching date format DD.MM.YYYY."""
    df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=1)
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.dropna(how="all")

    if "SR.NO." in df.columns:
        df["SR.NO._NUM"] = pd.to_numeric(df["SR.NO."], errors="coerce")
        df = df[df["SR.NO._NUM"].notna()].copy()
        df = df.drop(columns=["SR.NO._NUM"])

    if "THIK" in df.columns:
        df["THIK"] = df["THIK"].astype(str).str.replace(r"(?i)\s*mm", "", regex=True)

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            df[col] = 0.0

    return df


def parse_material_status_sheet(uploaded_file, sheet_name="Material Status"):
    """Parses the 'Material Status' sheet with date in row 1 and header in row 2."""
    raw = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
    date_val = str(raw.iloc[0, 0]).strip()

    df = pd.read_excel(uploaded_file, sheet_name=sheet_name, skiprows=1)
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.dropna(how="all")

    if "QTY" in df.columns:
        df["QTY"] = pd.to_numeric(df["QTY"], errors="coerce").fillna(0.0)

    for c in ["CATEGORY", "FROM", "STATUS", "GRADE", "SIZE", "EXPECTED DATE"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    return date_val, df


# --- CHART GENERATION HELPERS (FOR PDF EXPORT) ---
def generate_stock_bar_chart_bytes(primary_sums):
    """Generates Stock Overview Bar Chart image bytes for PDF export."""
    fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=200)
    metrics = ["GD STOCK", "COIL", "SOLD QTY", "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"]
    values = [primary_sums.get(m, 0.0) for m in metrics]

    bars = ax.bar(metrics, values, color="#1A365D", width=0.5)
    ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=7, color="#2D3748", fontweight="bold")

    ax.set_title("Stock Quantity Breakdown (MT)", fontsize=10, fontweight="bold", color="#1A365D", pad=10)
    ax.tick_params(axis="x", rotation=20, labelsize=7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E0")
    ax.spines["bottom"].set_color("#CBD5E0")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#CBD5E0")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_status_pie_chart_bytes(status_df):
    """Generates Status Distribution Pie Chart image bytes for PDF export."""
    fig, ax = plt.subplots(figsize=(5.5, 3.2), dpi=200)
    status_summary = status_df.groupby("STATUS")["QTY"].sum()

    wedges, texts, autotexts = ax.pie(
        status_summary.values,
        labels=status_summary.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=["#319795", "#ED8936", "#4299E1", "#9F7AEA"],
        textprops=dict(fontsize=8, color="#2D3748")
    )

    for autotext in autotexts:
        autotext.set_fontweight("bold")
        autotext.set_color("white")
        autotext.set_fontsize(8)

    ax.set_title("QTY Distribution by Status", fontsize=10, fontweight="bold", color="#1A365D", pad=10)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_from_bar_chart_bytes(status_df):
    """Generates Source (FROM) Bar Chart image bytes for PDF export."""
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
    from_summary = status_df.groupby("FROM")["QTY"].sum().reset_index()

    bars = ax.bar(from_summary["FROM"], from_summary["QTY"], color="#1A365D", width=0.45)
    ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=7.5, color="#2D3748", fontweight="bold")

    ax.set_title("QTY Distribution by Source (FROM)", fontsize=10, fontweight="bold", color="#1A365D", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E0")
    ax.spines["bottom"].set_color("#CBD5E0")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#CBD5E0")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# --- FPDF CLASS DEFINITION WITH PAGE FOOTER ---
class AppPDF(FPDF):
    def footer(self):
        self.set_y(-10)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


# --- PDF GENERATOR 1: DAILY STOCK REPORT ---
def generate_stock_pdf(date_str, df_primary, df_compare=None, compare_date_str=None):
    pdf = AppPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Title Banner
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.rect(0, 0, 297, 22, style="F")

    pdf.set_xy(0, 6)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(297, 10, f"Daily Stock Executive Report - {date_str}", align="C")

    pdf.set_y(26)

    # 1. Executive Summary KPIs
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, "Executive KPI Overview", ln=True)
    pdf.ln(1)

    primary_sums = df_primary[METRIC_COLS].sum()
    compare_sums = df_compare[METRIC_COLS].sum() if df_compare is not None else None

    card_w = 37
    card_h = 16
    start_x = 10
    start_y = pdf.get_y()

    for idx, col_name in enumerate(METRIC_COLS):
        x = start_x + idx * (card_w + 2.5)
        pdf.set_fill_color(*BG_CARD)
        pdf.set_draw_color(*BORDER_COLOR)
        pdf.rect(x, start_y, card_w, card_h, style="FD")

        pdf.set_xy(x, start_y + 2)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(card_w, 3.5, col_name, align="C")

        val = primary_sums[col_name]
        pdf.set_xy(x, start_y + 6)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*PRIMARY_COLOR)
        pdf.cell(card_w, 4.5, f"{val:,.2f}", align="C")

        if compare_sums is not None:
            c_val = compare_sums[col_name]
            diff = val - c_val
            diff_str = f"{diff:+,.2f}"

            pdf.set_xy(x, start_y + 11)
            pdf.set_font("Helvetica", "B", 6.5)

            if diff > 0:
                pdf.set_fill_color(*GREEN_BG)
                pdf.set_text_color(*GREEN_TEXT)
            elif diff < 0:
                pdf.set_fill_color(*RED_BG)
                pdf.set_text_color(*RED_TEXT)
            else:
                pdf.set_fill_color(241, 245, 249)
                pdf.set_text_color(*TEXT_MUTED)

            tag_w = 26
            pdf.rect(x + (card_w - tag_w) / 2, start_y + 11, tag_w, 3.5, style="F")
            pdf.cell(card_w, 3.5, diff_str, align="C")

    pdf.set_y(start_y + card_h + 8)

    # 2. Charts & Detailed Table Page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, "Stock Analytics Chart", ln=True)
    pdf.ln(2)

    chart_img = generate_stock_bar_chart_bytes(primary_sums)
    pdf.image(chart_img, x=10, y=pdf.get_y(), w=160, h=75)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, f"Detailed Stock Breakdown ({date_str})", ln=True)
    pdf.ln(2)

    stock_cols = ["SR", "CATEGORY", "THIK", "WIDTH", "GRADE", "GD STOCK", "COIL", "SOLD QTY", "INTANS", "BOOKING", "SAIL BSO", "BAL. QTY"]
    stock_widths = [10, 28, 16, 18, 22, 23, 23, 23, 23, 23, 23, 25]

    def draw_stock_header():
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_fill_color(*PRIMARY_COLOR)
        pdf.set_text_color(255, 255, 255)
        for c, w in zip(stock_cols, stock_widths):
            pdf.cell(w, 6, c, border=1, align="C", fill=True)
        pdf.ln()

    draw_stock_header()
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_draw_color(*BORDER_COLOR)

    for r_idx, (_, row) in enumerate(df_primary.iterrows()):
        if pdf.get_y() > 180:
            pdf.add_page()
            draw_stock_header()

        bg = ROW_ALT if r_idx % 2 == 1 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*TEXT_DARK)

        pdf.cell(stock_widths[0], 5, str(r_idx + 1), border="LRB", align="C", fill=True)
        pdf.cell(stock_widths[1], 5, str(row.get("CATEGORY", "")), border="LRB", align="L", fill=True)
        pdf.cell(stock_widths[2], 5, str(row.get("THIK", "")), border="LRB", align="C", fill=True)
        pdf.cell(stock_widths[3], 5, str(row.get("WIDTH", "")), border="LRB", align="C", fill=True)
        pdf.cell(stock_widths[4], 5, str(row.get("GRADE", "")), border="LRB", align="C", fill=True)

        for c_i, col_key in enumerate(METRIC_COLS, start=5):
            val = row.get(col_key, 0.0)
            pdf.cell(stock_widths[c_i], 5, f"{val:,.2f}", border="LRB", align="R", fill=True)
        pdf.ln()

    # Total Row
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_fill_color(220, 238, 222)
    pdf.set_text_color(20, 83, 45)
    pdf.cell(sum(stock_widths[:5]), 6, "TOTAL", border=1, align="C", fill=True)
    for c_i, col_key in enumerate(METRIC_COLS, start=5):
        pdf.cell(stock_widths[c_i], 6, f"{primary_sums[col_key]:,.2f}", border=1, align="R", fill=True)
    pdf.ln()

    return bytes(pdf.output())


# --- PDF GENERATOR 2: MATERIAL STATUS REPORT ---
def generate_material_status_pdf(date_str, df_mat):
    pdf = AppPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Header Banner
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.rect(0, 0, 297, 22, style="F")

    pdf.set_xy(0, 6)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(297, 10, f"Material Status Executive Report - {date_str}", align="C")

    pdf.set_y(26)

    # 1. KPI SUMMARY CARDS
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, "Material Status KPI Summary", ln=True)
    pdf.ln(1)

    total_qty = df_mat["QTY"].sum()
    status_grouped = df_mat.groupby("STATUS")["QTY"].sum().to_dict()

    card_w = 64
    card_h = 16
    start_x = 12
    start_y = pdf.get_y()

    cards_data = [
        ("TOTAL MATERIAL QTY", f"{total_qty:,.3f} MT"),
        ("RECEIVED (RECD)", f"{status_grouped.get('RECD', 0):,.3f} MT"),
        ("LOADING", f"{status_grouped.get('LOADING', 0):,.3f} MT"),
        ("IN TRANSIT", f"{status_grouped.get('INTRANSIT', 0):,.3f} MT")
    ]

    for idx, (label, val_str) in enumerate(cards_data):
        x = start_x + idx * (card_w + 3)
        pdf.set_fill_color(*BG_CARD)
        pdf.set_draw_color(*BORDER_COLOR)
        pdf.rect(x, start_y, card_w, card_h, style="FD")

        pdf.set_xy(x, start_y + 2.5)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(card_w, 4, label, align="C")

        pdf.set_xy(x, start_y + 7.5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*PRIMARY_COLOR)
        pdf.cell(card_w, 5, val_str, align="C")

    pdf.set_y(start_y + card_h + 8)

    # 2. SOURCE & STATUS MATRIX SUMMARY
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, "Source (FROM) vs Status Breakdown Matrix", ln=True)
    pdf.ln(1)

    pivot_mat = df_mat.pivot_table(index="FROM", columns="STATUS", values="QTY", aggfunc="sum", fill_value=0.0)
    for s_col in ["RECD", "LOADING", "INTRANSIT"]:
        if s_col not in pivot_mat.columns:
            pivot_mat[s_col] = 0.0

    pivot_mat["TOTAL QTY"] = pivot_mat.sum(axis=1)

    p_cols = ["FROM", "RECD", "LOADING", "INTRANSIT", "TOTAL QTY"]
    p_widths = [60, 50, 50, 50, 60]

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.set_text_color(255, 255, 255)
    for c_name, w in zip(p_cols, p_widths):
        pdf.cell(w, 6, c_name, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    pdf.set_draw_color(*BORDER_COLOR)
    for r_i, (from_loc, row_data) in enumerate(pivot_mat.iterrows()):
        bg = ROW_ALT if r_i % 2 == 1 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*TEXT_DARK)

        pdf.cell(p_widths[0], 5.5, f"  {from_loc}", border="LRB", align="L", fill=True)
        pdf.cell(p_widths[1], 5.5, f"{row_data['RECD']:,.3f}  ", border="LRB", align="R", fill=True)
        pdf.cell(p_widths[2], 5.5, f"{row_data['LOADING']:,.3f}  ", border="LRB", align="R", fill=True)
        pdf.cell(p_widths[3], 5.5, f"{row_data['INTRANSIT']:,.3f}  ", border="LRB", align="R", fill=True)
        pdf.cell(p_widths[4], 5.5, f"{row_data['TOTAL QTY']:,.3f}  ", border="LRB", align="R", fill=True)
        pdf.ln()

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 238, 222)
    pdf.set_text_color(20, 83, 45)
    pdf.cell(p_widths[0], 6, "TOTAL", border=1, align="C", fill=True)
    pdf.cell(p_widths[1], 6, f"{pivot_mat['RECD'].sum():,.3f}  ", border=1, align="R", fill=True)
    pdf.cell(p_widths[2], 6, f"{pivot_mat['LOADING'].sum():,.3f}  ", border=1, align="R", fill=True)
    pdf.cell(p_widths[3], 6, f"{pivot_mat['INTRANSIT'].sum():,.3f}  ", border=1, align="R", fill=True)
    pdf.cell(p_widths[4], 6, f"{pivot_mat['TOTAL QTY'].sum():,.3f}  ", border=1, align="R", fill=True)
    pdf.ln()

    # 3. CHARTS SECTION
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 8, "Visual Analytics", ln=True)
    pdf.ln(2)

    pie_img = generate_status_pie_chart_bytes(df_mat)
    bar_img = generate_from_bar_chart_bytes(df_mat)

    chart_y = pdf.get_y()
    pdf.image(pie_img, x=12, y=chart_y, w=130, h=75)
    pdf.image(bar_img, x=150, y=chart_y, w=130, h=75)

    # 4. DETAILED MATERIAL DATA TABLE
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 8, f"Detailed Material Status Data ({date_str})", ln=True)
    pdf.ln(2)

    tbl_cols = ["CATEGORY", "THIK", "SIZE", "GRADE", "QTY", "FROM", "STATUS", "EXPECTED DATE"]
    tbl_widths = [32, 20, 35, 28, 28, 35, 32, 35]

    def draw_mat_header():
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*PRIMARY_COLOR)
        pdf.set_text_color(255, 255, 255)
        for c, w in zip(tbl_cols, tbl_widths):
            pdf.cell(w, 6, c, border=1, align="C", fill=True)
        pdf.ln()

    draw_mat_header()

    pdf.set_font("Helvetica", "", 8)
    pdf.set_draw_color(*BORDER_COLOR)

    for r_idx, (_, row) in enumerate(df_mat.iterrows()):
        if pdf.get_y() > 180:
            pdf.add_page()
            draw_mat_header()

        bg = ROW_ALT if r_idx % 2 == 1 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*TEXT_DARK)

        pdf.cell(tbl_widths[0], 5, str(row.get("CATEGORY", "")), border="LRB", align="L", fill=True)
        pdf.cell(tbl_widths[1], 5, str(row.get("THIK", "")), border="LRB", align="C", fill=True)
        pdf.cell(tbl_widths[2], 5, str(row.get("SIZE", "")), border="LRB", align="C", fill=True)
        pdf.cell(tbl_widths[3], 5, str(row.get("GRADE", "")), border="LRB", align="C", fill=True)
        pdf.cell(tbl_widths[4], 5, f"{row.get('QTY', 0):,.3f}", border="LRB", align="R", fill=True)
        pdf.cell(tbl_widths[5], 5, str(row.get("FROM", "")), border="LRB", align="C", fill=True)
        pdf.cell(tbl_widths[6], 5, str(row.get("STATUS", "")), border="LRB", align="C", fill=True)
        pdf.cell(tbl_widths[7], 5, str(row.get("EXPECTED DATE", "")), border="LRB", align="C", fill=True)
        pdf.ln()

    # Total Row
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 238, 222)
    pdf.set_text_color(20, 83, 45)
    pdf.cell(sum(tbl_widths[:4]), 6, "TOTAL", border=1, align="C", fill=True)
    pdf.cell(tbl_widths[4], 6, f"{total_qty:,.3f}", border=1, align="R", fill=True)
    pdf.cell(sum(tbl_widths[5:]), 6, "", border=1, align="C", fill=True)
    pdf.ln()

    return bytes(pdf.output())


# --- MAIN APP ROUTING & CONTROLLER ---
st.title("📊 Inventory & Material Status Control Center")

uploaded_file = st.sidebar.file_uploader("Upload Master Excel File", type=["xlsx", "xls"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    all_sheets = xls.sheet_names

    has_material_sheet = "Material Status" in all_sheets
    date_sheets = [s for s in all_sheets if re.match(r"^\d{2}\.\d{2}\.\d{4}$", s.strip())]

    app_sections = []
    if date_sheets:
        app_sections.append("📦 Daily Stock Overview")
    if has_material_sheet:
        app_sections.append("🚚 Material Status")

    if not app_sections:
        st.error("No valid 'DD.MM.YYYY' stock sheet or 'Material Status' sheet found in the uploaded file.")
        st.stop()

    active_section = st.sidebar.radio("Select Section", app_sections)

    # ==========================================
    # SECTION 1: MATERIAL STATUS SECTION
    # ==========================================
    if active_section == "🚚 Material Status":
        st.header("🚚 Material Status Tracking & Analysis")

        mat_date, df_mat = parse_material_status_sheet(uploaded_file, "Material Status")

        # --- KPI CARDS ---
        st.markdown(f"### 📌 Material Status KPIs ({mat_date})")

        total_qty = df_mat["QTY"].sum()
        status_sums = df_mat.groupby("STATUS")["QTY"].sum().to_dict()

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Total Material Qty", f"{total_qty:,.3f} MT")
        m_col2.metric("Received (RECD)", f"{status_sums.get('RECD', 0):,.3f} MT")
        m_col3.metric("Loading", f"{status_sums.get('LOADING', 0):,.3f} MT")
        m_col4.metric("In Transit", f"{status_sums.get('INTRANSIT', 0):,.3f} MT")

        # --- PIVOT MATRIX BREAKDOWN ---
        st.markdown("---")
        st.subheader("📊 Source (FROM) vs Status Summary Matrix")

        pivot_matrix = df_mat.pivot_table(index="FROM", columns="STATUS", values="QTY", aggfunc="sum", fill_value=0.0)
        pivot_matrix["TOTAL QTY"] = pivot_matrix.sum(axis=1)

        st.dataframe(pivot_matrix.style.format("{:,.3f}"), use_container_width=True)

        # --- CHARTS SECTION ---
        st.markdown("---")
        st.subheader("📈 Visual Distribution")
        ch_col1, ch_col2 = st.columns(2)

        with ch_col1:
            fig_status_pie = px.pie(
                df_mat, names="STATUS", values="QTY",
                title="Total QTY Share by Status",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_status_pie.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_status_pie, use_container_width=True)

        with ch_col2:
            fig_from_bar = px.bar(
                df_mat.groupby(["FROM", "STATUS"])["QTY"].sum().reset_index(),
                x="FROM", y="QTY", color="STATUS",
                title="QTY Breakdown by Source (FROM) & Status",
                barmode="stack", text_auto=".2f"
            )
            st.plotly_chart(fig_from_bar, use_container_width=True)

        # --- DETAILED TABLE ---
        st.markdown("---")
        st.subheader(f"📄 Detailed Material Data Table ({mat_date})")

        df_mat_display = df_mat.copy()
        tot_row = {c: "" for c in df_mat_display.columns}
        tot_row["CATEGORY"] = "TOTAL"
        tot_row["QTY"] = total_qty

        df_mat_display = pd.concat([df_mat_display, pd.DataFrame([tot_row])], ignore_index=True)
        st.dataframe(df_mat_display, use_container_width=True)

        # --- PDF DOWNLOAD ---
        st.markdown("---")
        st.subheader("📥 Export Material Status PDF Report")

        mat_pdf_bytes = generate_material_status_pdf(mat_date, df_mat)
        st.download_button(
            label="📄 Download Material Status PDF Report",
            data=mat_pdf_bytes,
            file_name=f"Material_Status_Report_{mat_date}.pdf",
            mime="application/pdf"
        )

    # ==========================================
    # SECTION 2: DAILY STOCK OVERVIEW SECTION
    # ==========================================
    elif active_section == "📦 Daily Stock Overview":
        selected_date = st.sidebar.selectbox("Select Primary Date", date_sheets)
        enable_compare = st.sidebar.checkbox("Compare with another date")

        compare_date = None
        if enable_compare:
            remaining_dates = [d for d in date_sheets if d != selected_date]
            if remaining_dates:
                compare_date = st.sidebar.selectbox("Select Comparison Date", remaining_dates)

        df_primary = parse_stock_sheet(uploaded_file, selected_date)
        primary_sums = df_primary[METRIC_COLS].sum()

        df_compare = None
        compare_sums = None
        if compare_date:
            df_compare = parse_stock_sheet(uploaded_file, compare_date)
            compare_sums = df_compare[METRIC_COLS].sum()

        st.header(f"📌 Key Metrics Overview: {selected_date}")

        # Core Stock Metrics
        r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
        for col_widget, metric in zip([r1_col1, r1_col2, r1_col3, r1_col4], ["GD STOCK", "SOLD QTY", "INTANS", "BAL. QTY"]):
            with col_widget:
                val = primary_sums[metric]
                delta_val = f"{val - compare_sums[metric]:+,.3f} vs {compare_date}" if compare_sums is not None else None
                st.metric(label=metric, value=f"{val:,.3f}", delta=delta_val)

        st.markdown("### 📦 Orders & Movements")

        r2_col1, r2_col2, r2_col3 = st.columns(3)
        for col_widget, metric in zip([r2_col1, r2_col2, r2_col3], ["COIL", "BOOKING", "SAIL BSO"]):
            with col_widget:
                val = primary_sums[metric]
                delta_val = f"{val - compare_sums[metric]:+,.3f} vs {compare_date}" if compare_sums is not None else None
                st.metric(label=f"TOTAL {metric}", value=f"{val:,.3f}", delta=delta_val)

        st.markdown("---")
        st.subheader(f"📄 Detailed Stock Table ({selected_date})")
        st.dataframe(df_primary, use_container_width=True)

        st.markdown("---")
        st.subheader("📥 Export Stock PDF Report")
        stock_pdf_bytes = generate_stock_pdf(selected_date, df_primary, df_compare, compare_date)
        st.download_button(
            label="📄 Download Stock Overview PDF Report",
            data=stock_pdf_bytes,
            file_name=f"Stock_Report_{selected_date}.pdf",
            mime="application/pdf"
        )

else:
    st.info("👈 Please upload your stock / material status Excel file to begin.")
