import io
import re
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from fpdf import FPDF

# --- PAGE SETUP ---
st.set_page_config(page_title="Stock & Material Analytics Dashboard", layout="wide")

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


# --- HELPER FUNCTIONS FOR STOCK TAB ---
def parse_sheet_data(uploaded_file, sheet_name):
    """Parses a specific date tab, ignoring Excel summary total rows and parsing unit strings."""
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


# --- HELPER FUNCTIONS FOR MATERIAL STATUS TAB ---
def parse_material_status_sheet(uploaded_file, sheet_name):
    """Parses the 'Material Status' sheet."""
    header_df = pd.read_excel(uploaded_file, sheet_name=sheet_name, nrows=1, header=None)
    report_date = str(header_df.iloc[0, 4]).strip() if header_df.shape[1] > 4 and pd.notna(header_df.iloc[0, 4]) else "N/A"
    if report_date == "N/A":
        for val in header_df.values.flatten():
            if pd.notna(val) and re.search(r"\d{2}\.\d{2}\.\d{4}", str(val)):
                report_date = str(val).strip()
                break

    df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=1)
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.dropna(how="all")

    if "QTY" in df.columns:
        df["QTY"] = pd.to_numeric(df["QTY"], errors="coerce").fillna(0.0)

    for col in ["CATEGORY", "FROM", "STATUS", "GRADE"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()

    return report_date, df


# --- CHART GENERATION FOR PDF ---
def generate_bar_chart_bytes(cat_df, date_str):
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


def generate_pie_chart_bytes(cat_df, date_str):
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=200)
    valid_df = cat_df[cat_df["GD STOCK"] > 0]
    if valid_df.empty:
        valid_df = cat_df

    wedges, texts, autotexts = ax.pie(
        valid_df["GD STOCK"], 
        labels=valid_df["CAT."], 
        autopct="%1.1f%%", 
        startangle=90, 
        pctdistance=0.72,
        colors=["#1A365D", "#4299E1", "#319795", "#ED8936", "#9F7AEA"],
        textprops=dict(fontsize=8, color="#2D3748")
    )

    for autotext in autotexts:
        autotext.set_fontweight("bold")
        autotext.set_color("white")
        autotext.set_fontsize(8)

    ax.set_title(f"GD Stock Share by Category ({date_str})", fontsize=10, fontweight="bold", color="#1A365D", pad=12)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_comparison_bar_chart_bytes(primary_sums, compare_sums, date_str, compare_date):
    """Generates the side-by-side metric comparison bar chart for PDF."""
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=200)
    metrics = METRIC_COLS
    x = list(range(len(metrics)))
    width = 0.38

    p_vals = [primary_sums.get(m, 0.0) for m in metrics]
    c_vals = [compare_sums.get(m, 0.0) for m in metrics]

    rects1 = ax.bar([i - width/2 for i in x], p_vals, width=width, label=date_str, color="#0066CC")
    rects2 = ax.bar([i + width/2 for i in x], c_vals, width=width, label=compare_date, color="#80C1FF")

    ax.bar_label(rects1, fmt="%.1f", padding=3, fontsize=7, color="#1A365D", fontweight="bold")
    ax.bar_label(rects2, fmt="%.1f", padding=3, fontsize=7, color="#1A365D", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=8, color="#2D3748", fontweight="bold")
    ax.set_title(f"Metric Comparison: {date_str} vs {compare_date}", fontsize=11, fontweight="bold", color="#1A365D", pad=12)
    ax.legend(fontsize=8, loc="upper right", frameon=True, facecolor="#F8FAFC", edgecolor="none")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E0")
    ax.spines["bottom"].set_color("#CBD5E0")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#CBD5E0")

    max_val = max(max(p_vals, default=1), max(c_vals, default=1))
    ax.set_ylim(0, max_val * 1.18)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_mat_status_pie_bytes(status_df):
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=200)
    wedges, texts, autotexts = ax.pie(
        status_df["QTY"], 
        labels=status_df["STATUS"], 
        autopct="%1.1f%%", 
        startangle=90,
        pctdistance=0.72,
        colors=["#3182CE", "#DD6B20", "#319795", "#805AD5", "#E53E3E"],
        textprops=dict(fontsize=8, color="#2D3748")
    )
    for autotext in autotexts:
        autotext.set_fontweight("bold")
        autotext.set_color("white")
        autotext.set_fontsize(8)

    ax.set_title("QTY Distribution by Status", fontsize=10, fontweight="bold", color="#1A365D", pad=12)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_mat_source_bar_bytes(source_df):
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=200)
    sources = source_df["FROM"].astype(str).tolist()
    qtys = source_df["QTY"].tolist()

    rects = ax.bar(sources, qtys, color="#1A365D", width=0.45)
    ax.bar_label(rects, fmt="%.2f", padding=3, fontsize=7.5, color="#2D3748", fontweight="bold")

    ax.set_title("QTY Distribution by Source (FROM)", fontsize=10, fontweight="bold", color="#1A365D", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E0")
    ax.spines["bottom"].set_color("#CBD5E0")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#CBD5E0")

    max_val = max(qtys) if qtys else 1
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


def draw_metric_card(pdf, x, y, width, height, label, val, diff=None, compare_date=None, unit=""):
    pdf.set_fill_color(*BG_CARD)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.rect(x, y, width, height, style="FD")
    
    pdf.set_xy(x, y + 2)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(width, 4, label, align="C")
    
    pdf.set_xy(x, y + 6.5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    val_str = f"{val:,.3f} {unit}".strip()
    pdf.cell(width, 5, val_str, align="C")

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
    """Generates PDF report for Daily Stock sheet with Comparison Visuals."""
    pdf = AppPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    header_title = f"Dashboard Overview - {date_str}"
    if compare_date:
        header_title = f"Dashboard Comparison - {date_str} vs {compare_date}"

    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.rect(0, 0, 297, 22, style="F")
    
    pdf.set_xy(0, 6)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(297, 10, header_title, align="C")
    pdf.set_y(26)

    # Key Metrics
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, f"Key Metrics Overview: {date_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    row1_metrics = ["GD STOCK", "SOLD QTY", "INTANS", "BAL. QTY"]
    card_w, card_h, start_x = 66, (18 if compare_sums is not None else 15), 12
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
    pdf.cell(0, 6, "Orders & Movements", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    row2_metrics = [("TOTAL COIL", "COIL"), ("TOTAL BOOKING", "BOOKING"), ("TOTAL SAIL BSO", "SAIL BSO")]
    start_y, card_w_r2 = pdf.get_y(), 88

    for idx, (label, key) in enumerate(row2_metrics):
        x = start_x + idx * (card_w_r2 + 4)
        val = primary_sums.get(key, 0.0)
        diff = (val - compare_sums.get(key, 0.0)) if compare_sums is not None else None
        draw_metric_card(pdf, x, start_y, card_w_r2, card_h, label, val, diff, compare_date)

    pdf.set_y(start_y + card_h + 6)

    # Full Metrics Table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, "Full Metrics Summary Table", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    has_compare = compare_sums is not None
    sum_cols = ["Metric", f"{date_str} Total"]
    sum_widths = [136, 136]
    if has_compare:
        sum_cols = ["Metric", f"{date_str} Total", f"{compare_date} Total", "Difference"]
        sum_widths = [68, 68, 68, 68]

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(*PRIMARY_COLOR)
    for col_name, w in zip(sum_cols, sum_widths):
        pdf.cell(w, 5.5, col_name, border=1, align="C", fill=True)
    pdf.ln()

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

    # Category Charts Page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 8, "Visual Analysis - Category Breakdown", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    chart_y = pdf.get_y()
    img_w, img_h = 132, 75

    if "CAT." in df_primary.columns:
        cat_df = df_primary.groupby("CAT.")[METRIC_COLS].sum().reset_index()
        bar_buf = generate_bar_chart_bytes(cat_df, date_str)
        pie_buf = generate_pie_chart_bytes(cat_df, date_str)
        pdf.image(bar_buf, x=12, y=chart_y, w=img_w, h=img_h)
        pdf.image(pie_buf, x=150, y=chart_y, w=img_w, h=img_h)

    # Date Comparison Visual Page (ADDED)
    if has_compare:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*PRIMARY_COLOR)
        pdf.cell(0, 8, f"Date Comparison Analysis ({date_str} vs {compare_date})", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        comp_chart_buf = generate_comparison_bar_chart_bytes(primary_sums, compare_sums, date_str, compare_date)
        pdf.image(comp_chart_buf, x=15, y=pdf.get_y(), w=267, h=110)

    # Detailed Data Table Page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 8, f"Detailed Data Table ({date_str})", new_x="LMARGIN", new_y="NEXT")
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

    # Total Row
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


def generate_material_status_pdf_report(report_date, df_mat):
    """Generates PDF report for Material Status sheet."""
    pdf = AppPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.rect(0, 0, 297, 22, style="F")
    pdf.set_xy(0, 6)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(297, 10, f"Material Status Executive Report - {report_date}", align="C")
    pdf.set_y(26)

    total_qty = df_mat["QTY"].sum()
    status_summary = df_mat.groupby("STATUS")["QTY"].sum().reset_index()
    source_summary = df_mat.groupby("FROM")["QTY"].sum().reset_index()

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, "Material Status KPI Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    card_w, card_h, start_x = 66, 15, 12
    start_y = pdf.get_y()

    draw_metric_card(pdf, start_x, start_y, card_w, card_h, "TOTAL MATERIAL QTY", total_qty, unit="MT")

    unique_statuses = status_summary["STATUS"].tolist()
    for idx, st_name in enumerate(unique_statuses[:3]):
        x = start_x + (idx + 1) * (card_w + 3)
        st_val = status_summary[status_summary["STATUS"] == st_name]["QTY"].values[0]
        draw_metric_card(pdf, x, start_y, card_w, card_h, f"STATUS: {st_name}", st_val, unit="MT")

    pdf.set_y(start_y + card_h + 8)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 6, "Source (FROM) vs Status Breakdown Matrix", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pivot_df = pd.pivot_table(df_mat, values="QTY", index="FROM", columns="STATUS", aggfunc="sum", fill_value=0.0)
    pivot_df["TOTAL QTY"] = pivot_df.sum(axis=1)
    
    pivot_cols = ["FROM"] + [c for c in pivot_df.columns]
    p_width = 272 / len(pivot_cols)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*PRIMARY_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(*PRIMARY_COLOR)
    for col_name in pivot_cols:
        pdf.cell(p_width, 6, str(col_name), border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    pdf.set_draw_color(*BORDER_COLOR)
    for idx, (src, row) in enumerate(pivot_df.iterrows()):
        bg = ROW_ALT if idx % 2 == 1 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(p_width, 5, str(src), border="LRB", align="L", fill=True)
        for val in row:
            pdf.cell(p_width, 5, f"{val:,.3f}", border="LRB", align="R", fill=True)
        pdf.ln()

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 238, 222)
    pdf.set_text_color(20, 83, 45)
    pdf.cell(p_width, 6, "TOTAL", border=1, align="L", fill=True)
    for col in pivot_df.columns:
        pdf.cell(p_width, 6, f"{pivot_df[col].sum():,.3f}", border=1, align="R", fill=True)
    pdf.ln()

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 8, "Visual Analytics", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    chart_y = pdf.get_y()
    pie_mat_buf = generate_mat_status_pie_bytes(status_summary)
    bar_mat_buf = generate_mat_source_bar_bytes(source_summary)

    pdf.image(pie_mat_buf, x=12, y=chart_y, w=132, h=75)
    pdf.image(bar_mat_buf, x=150, y=chart_y, w=132, h=75)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 8, f"Detailed Material Status Data ({report_date})", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    mat_cols = ["CATEGORY", "THIK", "SIZE", "GRADE", "QTY", "FROM", "STATUS", "EXPECTED DATE"]
    mat_widths = [32, 20, 32, 32, 30, 42, 32, 42]

    def draw_mat_table_header():
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*PRIMARY_COLOR)
        pdf.set_text_color(255, 255, 255)
        pdf.set_draw_color(*PRIMARY_COLOR)
        for col, w in zip(mat_cols, mat_widths):
            pdf.cell(w, 6, col, border=1, align="C", fill=True)
        pdf.ln()

    draw_mat_table_header()
    pdf.set_font("Helvetica", "", 8)
    pdf.set_draw_color(*BORDER_COLOR)

    for r_idx, (_, row) in enumerate(df_mat.iterrows()):
        if pdf.get_y() > 180:
            pdf.add_page()
            draw_mat_table_header()

        bg = ROW_ALT if r_idx % 2 == 1 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*TEXT_DARK)

        pdf.cell(mat_widths[0], 5, str(row.get("CATEGORY", "")), border="LRB", align="L", fill=True)
        pdf.cell(mat_widths[1], 5, str(row.get("THIK", "")), border="LRB", align="C", fill=True)
        pdf.cell(mat_widths[2], 5, str(row.get("SIZE", "")), border="LRB", align="C", fill=True)
        pdf.cell(mat_widths[3], 5, str(row.get("GRADE", "")), border="LRB", align="C", fill=True)
        pdf.cell(mat_widths[4], 5, f"{row.get('QTY', 0):,.3f}", border="LRB", align="R", fill=True)
        pdf.cell(mat_widths[5], 5, str(row.get("FROM", "")), border="LRB", align="L", fill=True)
        pdf.cell(mat_widths[6], 5, str(row.get("STATUS", "")), border="LRB", align="C", fill=True)
        
        exp_date_str = str(row.get("EXPECTED DATE", ""))
        if "00:00:00" in exp_date_str:
            exp_date_str = exp_date_str.split()[0]
        pdf.cell(mat_widths[7], 5, exp_date_str, border="LRB", align="C", fill=True)
        pdf.ln()

    if pdf.get_y() > 180:
        pdf.add_page()
        draw_mat_table_header()

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 238, 222)
    pdf.set_text_color(20, 83, 45)
    pdf.cell(mat_widths[0] + mat_widths[1] + mat_widths[2] + mat_widths[3], 6, "TOTAL", border=1, align="C", fill=True)
    pdf.cell(mat_widths[4], 6, f"{total_qty:,.3f}", border=1, align="R", fill=True)
    pdf.cell(mat_widths[5] + mat_widths[6] + mat_widths[7], 6, "", border=1, fill=True)
    pdf.ln()

    return bytes(pdf.output())


# --- MAIN APP LAYOUT ---
st.title("📊 Inventory & Material Status Analytics Dashboard")

uploaded_file = st.sidebar.file_uploader("Upload Stock Excel File", type=["xlsx", "xls"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    all_sheets = xls.sheet_names

    mat_status_sheet = next((s for s in all_sheets if s.strip().lower() == "material status"), None)
    date_sheets = [s for s in all_sheets if re.match(r"^\d{2}\.\d{2}\.\d{4}$", s.strip())]

    app_mode = st.sidebar.radio("Select Analysis Module", ["Daily Stock Analysis", "Material Status"])

    # ---------------------------------------------------------
    # MODULE 1: DAILY STOCK ANALYSIS
    # ---------------------------------------------------------
    if app_mode == "Daily Stock Analysis":
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

        df_primary = parse_sheet_data(uploaded_file, selected_date)
        primary_sums = df_primary[METRIC_COLS].sum()

        df_compare, compare_sums = None, None
        if compare_date:
            df_compare = parse_sheet_data(uploaded_file, compare_date)
            compare_sums = df_compare[METRIC_COLS].sum()

        st.header(f"📌 Key Metrics Overview: {selected_date}")

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

        with st.expander("🔢 View Full Metrics Summary Table"):
            summary_data = {"Metric": METRIC_COLS, f"{selected_date} Total": [primary_sums[m] for m in METRIC_COLS]}
            if compare_sums is not None:
                summary_data[f"{compare_date} Total"] = [compare_sums[m] for m in METRIC_COLS]
                summary_data["Difference"] = [primary_sums[m] - compare_sums[m] for m in METRIC_COLS]
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

        st.markdown("---")
        st.header("📈 Visual Analysis")
        chart_tab1, chart_tab2 = st.tabs(["Category Breakdown", "Date Comparison"])

        with chart_tab1:
            if "CAT." in df_primary.columns:
                cat_df = df_primary.groupby("CAT.")[METRIC_COLS].sum().reset_index()
                col_left, col_right = st.columns(2)
                with col_left:
                    fig_bar = px.bar(cat_df, x="CAT.", y=["GD STOCK", "SOLD QTY", "BAL. QTY"], barmode="group",
                                     title=f"Stock Distribution by Category ({selected_date})", text_auto=".1f")
                    fig_bar.update_traces(textposition="outside")
                    st.plotly_chart(fig_bar, use_container_width=True)
                with col_right:
                    fig_pie = px.pie(cat_df, names="CAT.", values="GD STOCK", title=f"GD Stock Share by Category ({selected_date})")
                    fig_pie.update_traces(textinfo="percent+label")
                    st.plotly_chart(fig_pie, use_container_width=True)

        with chart_tab2:
            if compare_sums is not None:
                comp_df = pd.DataFrame({
                    "Metric": METRIC_COLS,
                    selected_date: primary_sums.values,
                    compare_date: compare_sums.values
                }).melt(id_vars="Metric", var_name="Date", value_name="Total Quantity")

                fig_comp = px.bar(comp_df, x="Metric", y="Total Quantity", color="Date", barmode="group",
                                  title=f"Metric Comparison: {selected_date} vs {compare_date}", text_auto=".1f")
                fig_comp.update_traces(textposition="outside")
                st.plotly_chart(fig_comp, use_container_width=True)
            else:
                st.info("Enable 'Compare with another date' in the sidebar to view comparison charts.")

        st.markdown("---")
        st.header(f"📄 Detailed Data Table ({selected_date})")
        df_display = df_primary.copy()
        
        # Calculate the average of positive BAL. QTY values for dynamic color thresholding
        positive_bal_qtys = df_display[df_display["BAL. QTY"] >= 0]["BAL. QTY"]
        bal_avg = positive_bal_qtys.mean() if not positive_bal_qtys.empty else 0.0

        def style_bal_qty(val):
            try:
                val = float(val)
                if val < 0:
                    return "background-color: #ffcdd2; color: #b71c1c; font-weight: bold;"  # Red (Negative)
                elif 0 <= val < bal_avg:
                    return "background-color: #fff9c4; color: #f57f17; font-weight: bold;"  # Yellow (Below Average)
                else:
                    return "background-color: #c8e6c9; color: #1b5e20; font-weight: bold;"  # Green (Above Average)
            except (ValueError, TypeError):
                return ""

        # Prepare Total Row
        total_row = {col: "" for col in df_display.columns}
        total_row["SR.NO."] = "TOTAL"
        for col in METRIC_COLS:
            total_row[col] = primary_sums[col]
            
        df_display = pd.concat([df_display, pd.DataFrame([total_row])], ignore_index=True)

        # Apply styling to BAL. QTY column
        styled_df = df_display.style.map(style_bal_qty, subset=["BAL. QTY"]).format(
            {col: "{:,.3f}" for col in METRIC_COLS if col in df_display.columns},
            na_rep=""
        )

        st.dataframe(styled_df, use_container_width=True)

        st.markdown("---")
        st.header("📥 Export Report")
        pdf_bytes = generate_pdf_report(selected_date, df_primary, primary_sums, compare_date, compare_sums)
        filename = f"Stock_Report_{selected_date}.pdf" if not compare_date else f"Stock_Comparison_{selected_date}_vs_{compare_date}.pdf"
        st.download_button("📄 Download Daily Stock PDF Report", data=pdf_bytes, file_name=filename, mime="application/pdf")

    # ---------------------------------------------------------
    # MODULE 2: MATERIAL STATUS
    # ---------------------------------------------------------
    elif app_mode == "Material Status":
        if not mat_status_sheet:
            st.error("Sheet named 'Material Status' was not found in the uploaded file.")
            st.stop()

        report_date, df_mat = parse_material_status_sheet(uploaded_file, mat_status_sheet)

        st.header(f"🚚 Material Status Overview ({report_date})")

        total_mat_qty = df_mat["QTY"].sum()
        status_grp = df_mat.groupby("STATUS")["QTY"].sum().to_dict()
        source_grp = df_mat.groupby("FROM")["QTY"].sum().reset_index()

        kpi_cols = st.columns(1 + len(status_grp))
        with kpi_cols[0]:
            st.metric("TOTAL MATERIAL QTY", f"{total_mat_qty:,.3f} MT")

        for idx, (st_name, st_val) in enumerate(status_grp.items()):
            with kpi_cols[idx + 1]:
                st.metric(f"STATUS: {st_name}", f"{st_val:,.3f} MT")

        st.markdown("---")
        st.subheader("📊 Source (FROM) vs Status Matrix")
        pivot_table = pd.pivot_table(df_mat, values="QTY", index="FROM", columns="STATUS", aggfunc="sum", fill_value=0.0)
        pivot_table["TOTAL QTY"] = pivot_table.sum(axis=1)
        st.dataframe(pivot_table.style.format("{:,.3f}"), use_container_width=True)

        st.markdown("---")
        st.header("📈 Visual Analytics")
        m_col1, m_col2 = st.columns(2)

        with m_col1:
            fig_mat_pie = px.pie(df_mat, names="STATUS", values="QTY", title="QTY Distribution by Status", hole=0.3)
            fig_mat_pie.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_mat_pie, use_container_width=True)

        with m_col2:
            fig_mat_bar = px.bar(source_grp, x="FROM", y="QTY", title="QTY Distribution by Source (FROM)", text_auto=".2f")
            fig_mat_bar.update_traces(textposition="outside")
            st.plotly_chart(fig_mat_bar, use_container_width=True)

        st.markdown("---")
        st.header("📄 Detailed Material Data")
        df_mat_display = df_mat.copy()
        tot_mat_row = {col: "" for col in df_mat_display.columns}
        tot_mat_row["CATEGORY"] = "TOTAL"
        tot_mat_row["QTY"] = total_mat_qty
        df_mat_display = pd.concat([df_mat_display, pd.DataFrame([tot_mat_row])], ignore_index=True)
        st.dataframe(df_mat_display, use_container_width=True)

        st.markdown("---")
        st.header("📥 Export Material Status Report")
        mat_pdf_bytes = generate_material_status_pdf_report(report_date, df_mat)
        mat_filename = f"Material_Status_Report_{report_date}.pdf"
        st.download_button("📄 Download Material Status PDF Report", data=mat_pdf_bytes, file_name=mat_filename, mime="application/pdf")

else:
    st.info("👈 Please upload your stock Excel file from the sidebar to begin.")
