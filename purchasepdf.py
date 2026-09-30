/**
 * MAIN FUNCTION: Generate Daily Stock Executive Report PDF
 */
function generateDailyStockReportPDF() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("DailyStock") || ss.getActiveSheet();
  var data = sheet.getDataRange().getValues();
  
  // Parse and calculate metrics accurately
  var metrics = calculateStockKPIs(data);
  
  // HTML Template for Daily Stock Report
  var htmlContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        @page { size: A4 landscape; margin: 12mm; }
        body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1e293b; margin: 0; padding: 0; }
        .header { background-color: #1b365d; color: white; padding: 14px 20px; text-align: center; border-radius: 4px; }
        .header h1 { margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.5px; }
        .section-title { font-size: 14px; font-weight: bold; color: #1b365d; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; }
        
        /* KPI Cards Grid */
        .kpi-container { display: table; width: 100%; table-layout: fixed; margin-top: 12px; }
        .kpi-card { display: table-cell; background: #f8fafc; border: 1px solid #e2e8f0; padding: 10px 5px; text-align: center; border-radius: 4px; }
        .kpi-title { font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; }
        .kpi-value { font-size: 15px; color: #1b365d; font-weight: bold; }
        
        /* Chart Section */
        .chart-box { text-align: center; margin-top: 20px; }
        .chart-box img { width: 85%; max-width: 680px; height: auto; }

        /* Multi-column Category Layout */
        .flex-row { display: table; width: 100%; table-layout: fixed; margin-top: 15px; }
        .flex-col { display: table-cell; vertical-align: top; width: 50%; padding-right: 10px; }
        .flex-col:last-child { padding-right: 0; padding-left: 10px; }

        /* Data Tables */
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 10px; }
        th { background-color: #1b365d; color: white; padding: 7px 5px; font-weight: 600; text-align: right; }
        th:nth-child(-n+5) { text-align: left; }
        td { border-bottom: 1px solid #cbd5e1; padding: 6px 5px; text-align: right; }
        td:nth-child(-n+5) { text-align: left; }
        tr:nth-child(even) { background-color: #f1f5f9; }
        .total-row td { font-weight: bold; background-color: #e2e8f0; border-top: 2px solid #1b365d; color: #0f172a; }

        .page-break { page-break-before: always; }
      </style>
    </head>
    <body>
      
      <!-- PAGE 1: KPI OVERVIEW & BAR CHART -->
      <div class="header">
        <h1>Daily Stock Executive Report - ${metrics.reportDate}</h1>
      </div>

      <div class="section-title">Executive KPI Overview</div>
      <div class="kpi-container">
        <div class="kpi-card"><div class="kpi-title">GD STOCK</div><div class="kpi-value">${formatNum(metrics.gdStock)}</div></div>
        <div class="kpi-card"><div class="kpi-title">COIL</div><div class="kpi-value">${formatNum(metrics.coil)}</div></div>
        <div class="kpi-card"><div class="kpi-title">SOLD QTY</div><div class="kpi-value">${formatNum(metrics.soldQty)}</div></div>
        <div class="kpi-card"><div class="kpi-title">INTANS</div><div class="kpi-value">${formatNum(metrics.intans)}</div></div>
        <div class="kpi-card"><div class="kpi-title">BOOKING</div><div class="kpi-value">${formatNum(metrics.booking)}</div></div>
        <div class="kpi-card"><div class="kpi-title">SAIL BSO</div><div class="kpi-value">${formatNum(metrics.sailBso)}</div></div>
        <div class="kpi-card"><div class="kpi-title">BAL. QTY</div><div class="kpi-value">${formatNum(metrics.balQty)}</div></div>
      </div>

      <div class="section-title">Stock Analytics Chart</div>
      <div class="chart-box">
        <img src="${getMainBarChartUrl(metrics)}" />
      </div>

      <!-- PAGE 2: CATEGORY BREAKDOWN CHARTS -->
      <div class="page-break"></div>
      <div class="section-title">Visual Analysis - Category Breakdown</div>
      <div class="flex-row">
        <div class="flex-col">
          <img src="${getCategoryBarChartUrl(metrics)}" style="width:100%;" />
        </div>
        <div class="flex-col">
          <img src="${getCategoryPieChartUrl(metrics)}" style="width:100%;" />
        </div>
      </div>

      <!-- PAGE 3: DETAILED ITEM BREAKDOWN TABLE -->
      <div class="page-break"></div>
      <div class="section-title">Detailed Stock Breakdown (${metrics.reportDate})</div>
      ${buildDetailedStockTableHTML(metrics)}

    </body>
    </html>
  `;

  createAndSavePDF("Stock_Report_" + metrics.reportDate + ".pdf", htmlContent);
}

/**
 * MAIN FUNCTION: Generate Material Status Report PDF
 */
function generateMaterialStatusReportPDF() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("MaterialStatus") || ss.getActiveSheet();
  var data = sheet.getDataRange().getValues();

  var matData = calculateMaterialStatusKPIs(data);

  var htmlContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        @page { size: A4 portrait; margin: 12mm; }
        body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1e293b; margin: 0; padding: 0; }
        .header { background-color: #1b365d; color: white; padding: 14px 20px; text-align: center; border-radius: 4px; }
        .header h1 { margin: 0; font-size: 18px; font-weight: 600; }
        .section-title { font-size: 13px; font-weight: bold; color: #1b365d; margin-top: 18px; margin-bottom: 8px; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; }
        
        .kpi-container { display: table; width: 100%; table-layout: fixed; margin-top: 10px; }
        .kpi-card { display: table-cell; background: #f8fafc; border: 1px solid #cbd5e1; padding: 10px; text-align: center; border-radius: 4px; }
        .kpi-title { font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; }
        .kpi-value { font-size: 16px; color: #1b365d; font-weight: bold; margin-top: 4px; }

        table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 10px; }
        th { background-color: #1b365d; color: white; padding: 6px; text-align: right; }
        th:nth-child(1) { text-align: left; }
        td { border-bottom: 1px solid #cbd5e1; padding: 5px; text-align: right; }
        td:nth-child(1) { text-align: left; }
        tr:nth-child(even) { background-color: #f8fafc; }
        .total-row td { font-weight: bold; background-color: #e2e8f0; border-top: 2px solid #1b365d; }

        .flex-row { display: table; width: 100%; table-layout: fixed; margin-top: 15px; }
        .flex-col { display: table-cell; vertical-align: middle; width: 50%; text-align: center; }
        .page-break { page-break-before: always; }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>Material Status Executive Report - ${matData.reportDate}</h1>
      </div>

      <div class="section-title">Material Status KPI Summary</div>
      <div class="kpi-container">
        <div class="kpi-card"><div class="kpi-title">TOTAL MATERIAL QTY</div><div class="kpi-value">${formatNum(matData.totalQty, 3)} MT</div></div>
        <div class="kpi-card"><div class="kpi-title">RECEIVED (RECD)</div><div class="kpi-value">${formatNum(matData.recdQty, 3)} MT</div></div>
        <div class="kpi-card"><div class="kpi-title">LOADING</div><div class="kpi-value">${formatNum(matData.loadingQty, 3)} MT</div></div>
        <div class="kpi-card"><div class="kpi-title">IN TRANSIT</div><div class="kpi-value">${formatNum(matData.intransitQty, 3)} MT</div></div>
      </div>

      <div class="section-title">Source (FROM) vs Status Breakdown Matrix</div>
      ${buildMaterialMatrixHTML(matData)}

      <div class="page-break"></div>
      <div class="section-title">Visual Analytics</div>
      <div class="flex-row">
        <div class="flex-col"><img src="${getMaterialPieChartUrl(matData)}" style="width:95%;" /></div>
        <div class="flex-col"><img src="${getMaterialSourceBarChartUrl(matData)}" style="width:95%;" /></div>
      </div>

      <div class="page-break"></div>
      <div class="section-title">Detailed Material Status Data (${matData.reportDate})</div>
      ${buildMaterialDetailsTableHTML(matData)}
    </body>
    </html>
  `;

  createAndSavePDF("Material_Status_Report_" + matData.reportDate + ".pdf", htmlContent);
}

// -----------------------------------------------------------------------------
// DATA PROCESSING & CALCULATION LOGIC
// -----------------------------------------------------------------------------

function calculateStockKPIs(data) {
  var res = {
    reportDate: Utilities.formatDate(new Date(), "GMT+5:30", "dd.MM.yyyy"),
    gdStock: 0, coil: 0, soldQty: 0, intans: 0, booking: 0, sailBso: 0, balQty: 0,
    categories: {}, items: []
  };

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[0] && !row[1] && !row[2]) continue;

    var category = String(row[0] || 'CHQ').trim();
    var thik = row[1];
    var width = row[2];
    var grade = row[3] || '';
    
    var gd = Number(row[4]) || 0;
    var coil = Number(row[5]) || 0;
    var sold = Number(row[6]) || 0;
    var rawIntans = Number(row[7]) || 0;
    var booking = Number(row[8]) || 0;
    var sail = Number(row[9]) || 0;
    var status = String(row[10] || '').trim().toUpperCase();

    // CRITICAL FIX: Ensure INTANS only counts when status is strictly INTRANSIT
    var validIntans = (status === 'INTRANSIT' || status === 'IN TRANSIT') ? rawIntans : 0;
    var bal = (gd + coil + validIntans) - sold - booking - sail;

    res.gdStock += gd;
    res.coil += coil;
    res.soldQty += sold;
    res.intans += validIntans;
    res.booking += booking;
    res.sailBso += sail;
    res.balQty += bal;

    // Track Category aggregated breakdown
    if (!res.categories[category]) {
      res.categories[category] = { gdStock: 0, soldQty: 0, balQty: 0 };
    }
    res.categories[category].gdStock += gd;
    res.categories[category].soldQty += sold;
    res.categories[category].balQty += bal;

    res.items.push({
      sr: res.items.length + 1, category: category, thik: thik, width: width, grade: grade,
      gdStock: gd, coil: coil, soldQty: sold, intans: validIntans, booking: booking, sailBso: sail, balQty: bal
    });
  }

  return res;
}

function calculateMaterialStatusKPIs(data) {
  var res = {
    reportDate: Utilities.formatDate(new Date(), "GMT+5:30", "dd.MM.yyyy"),
    totalQty: 0, recdQty: 0, loadingQty: 0, intransitQty: 0,
    sources: {}, items: []
  };

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[0] && !row[4]) continue;

    var qty = Number(row[4]) || 0;
    var source = String(row[5] || 'UNKNOWN').trim().toUpperCase();
    var status = String(row[6] || '').trim().toUpperCase();

    res.totalQty += qty;

    if (!res.sources[source]) {
      res.sources[source] = { RECD: 0, LOADING: 0, INTRANSIT: 0, TOTAL: 0 };
    }

    if (status === 'RECD' || status === 'RECEIVED') {
      res.recdQty += qty;
      res.sources[source].RECD += qty;
    } else if (status === 'LOADING') {
      res.loadingQty += qty;
      res.sources[source].LOADING += qty;
    } else if (status === 'INTRANSIT' || status === 'IN TRANSIT') {
      res.intransitQty += qty;
      res.sources[source].INTRANSIT += qty;
    }
    res.sources[source].TOTAL += qty;

    res.items.push({
      category: row[0], thik: row[1], size: row[2], grade: row[3],
      qty: qty, from: source, status: status, expDate: row[7] ? Utilities.formatDate(new Date(row[7]), "GMT+5:30", "dd.MM.yyyy") : ''
    });
  }

  return res;
}

// -----------------------------------------------------------------------------
// HTML TABLE BUILDERS
// -----------------------------------------------------------------------------

function buildDetailedStockTableHTML(m) {
  var rows = m.items.map(function(item) {
    return `<tr>
      <td>${item.sr}</td>
      <td>${item.category}</td>
      <td>${item.thik}</td>
      <td>${item.width}</td>
      <td>${item.grade}</td>
      <td>${formatNum(item.gdStock)}</td>
      <td>${formatNum(item.coil)}</td>
      <td>${formatNum(item.soldQty)}</td>
      <td>${formatNum(item.intans)}</td>
      <td>${formatNum(item.booking)}</td>
      <td>${formatNum(item.sailBso)}</td>
      <td>${formatNum(item.balQty)}</td>
    </tr>`;
  }).join('');

  return `
    <table>
      <thead>
        <tr>
          <th>SR</th><th>CATEGORY</th><th>THIK</th><th>WIDTH</th><th>GRADE</th>
          <th>GD STOCK</th><th>COIL</th><th>SOLD QTY</th><th>INTANS</th><th>BOOKING</th><th>SAIL BSO</th><th>BAL. QTY</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
        <tr class="total-row">
          <td colspan="5" style="text-align:center;">TOTAL</td>
          <td>${formatNum(m.gdStock)}</td>
          <td>${formatNum(m.coil)}</td>
          <td>${formatNum(m.soldQty)}</td>
          <td>${formatNum(m.intans)}</td>
          <td>${formatNum(m.booking)}</td>
          <td>${formatNum(m.sailBso)}</td>
          <td>${formatNum(m.balQty)}</td>
        </tr>
      </tbody>
    </table>
  `;
}

function buildMaterialMatrixHTML(mat) {
  var rows = Object.keys(mat.sources).map(function(src) {
    var s = mat.sources[src];
    return `<tr>
      <td>${src}</td>
      <td>${formatNum(s.RECD, 3)}</td>
      <td>${formatNum(s.LOADING, 3)}</td>
      <td>${formatNum(s.INTRANSIT, 3)}</td>
      <td>${formatNum(s.TOTAL, 3)}</td>
    </tr>`;
  }).join('');

  return `
    <table>
      <thead>
        <tr>
          <th>FROM</th><th>RECD</th><th>LOADING</th><th>INTRANSIT</th><th>TOTAL QTY</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
        <tr class="total-row">
          <td>TOTAL</td>
          <td>${formatNum(mat.recdQty, 3)}</td>
          <td>${formatNum(mat.loadingQty, 3)}</td>
          <td>${formatNum(mat.intransitQty, 3)}</td>
          <td>${formatNum(mat.totalQty, 3)}</td>
        </tr>
      </tbody>
    </table>
  `;
}

function buildMaterialDetailsTableHTML(mat) {
  var rows = mat.items.map(function(item) {
    return `<tr>
      <td>${item.category}</td>
      <td>${item.thik}</td>
      <td>${item.size}</td>
      <td>${item.grade}</td>
      <td>${formatNum(item.qty, 3)}</td>
      <td>${item.from}</td>
      <td>${item.status}</td>
      <td>${item.expDate}</td>
    </tr>`;
  }).join('');

  return `
    <table>
      <thead>
        <tr>
          <th>CATEGORY</th><th>THIK</th><th>SIZE</th><th>GRADE</th><th>QTY</th><th>FROM</th><th>STATUS</th><th>EXPECTED DATE</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
        <tr class="total-row">
          <td colspan="4" style="text-align:center;">TOTAL</td>
          <td>${formatNum(mat.totalQty, 3)}</td>
          <td colspan="3"></td>
        </tr>
      </tbody>
    </table>
  `;
}

// -----------------------------------------------------------------------------
// QUICKCHART GENERATORS
// -----------------------------------------------------------------------------

function getMainBarChartUrl(m) {
  var chart = {
    type: 'bar',
    data: {
      labels: ['GD STOCK', 'COIL', 'SOLD QTY', 'INTANS', 'BOOKING', 'SAIL BSO', 'BAL. QTY'],
      datasets: [{ data: [m.gdStock, m.coil, m.soldQty, m.intans, m.booking, m.sailBso, m.balQty], backgroundColor: '#1b365d' }]
    },
    options: {
      title: { display: true, text: 'Stock Quantity Breakdown (MT)', fontSize: 13, fontColor: '#1b365d' },
      legend: { display: false },
      plugins: { datalabels: { display: true, anchor: 'end', align: 'top', formatter: (v) => v.toFixed(2) } }
    }
  };
  return "https://quickchart.io/chart?c=" + encodeURIComponent(JSON.stringify(chart));
}

function getCategoryBarChartUrl(m) {
  var cats = Object.keys(m.categories);
  var chart = {
    type: 'bar',
    data: {
      labels: cats,
      datasets: [
        { label: 'GD STOCK', data: cats.map(c => m.categories[c].gdStock), backgroundColor: '#1b365d' },
        { label: 'SOLD QTY', data: cats.map(c => m.categories[c].soldQty), backgroundColor: '#38bdf8' },
        { label: 'BAL. QTY', data: cats.map(c => m.categories[c].balQty), backgroundColor: '#ef4444' }
      ]
    },
    options: {
      title: { display: true, text: 'Stock Distribution by Category', fontSize: 12 },
      plugins: { datalabels: { display: true, anchor: 'end', align: 'top', formatter: (v) => v.toFixed(1) } }
    }
  };
  return "https://quickchart.io/chart?c=" + encodeURIComponent(JSON.stringify(chart));
}

function getCategoryPieChartUrl(m) {
  var cats = Object.keys(m.categories);
  var chart = {
    type: 'pie',
    data: {
      labels: cats,
      datasets: [{ data: cats.map(c => m.categories[c].gdStock), backgroundColor: ['#1b365d', '#38bdf8', '#f59e0b', '#10b981'] }]
    },
    options: {
      title: { display: true, text: 'GD Stock Share by Category', fontSize: 12 },
      plugins: { datalabels: { formatter: (val, ctx) => {
        let sum = ctx.dataset.data.reduce((a, b) => a + b, 0);
        return ((val * 100) / sum).toFixed(1) + '%';
      }, color: '#fff', font: { weight: 'bold' } } }
    }
  };
  return "https://quickchart.io/chart?c=" + encodeURIComponent(JSON.stringify(chart));
}

function getMaterialPieChartUrl(mat) {
  var chart = {
    type: 'pie',
    data: {
      labels: ['RECD', 'LOADING', 'INTRANSIT'],
      datasets: [{ data: [mat.recdQty, mat.loadingQty, mat.intransitQty], backgroundColor: ['#3b82f6', '#f97316', '#14b8a6'] }]
    },
    options: {
      title: { display: true, text: 'QTY Distribution by Status', fontSize: 12 },
      plugins: { datalabels: { formatter: (val) => ((val * 100) / mat.totalQty).toFixed(1) + '%', color: '#fff', font: { weight: 'bold' } } }
    }
  };
  return "https://quickchart.io/chart?c=" + encodeURIComponent(JSON.stringify(chart));
}

function getMaterialSourceBarChartUrl(mat) {
  var sources = Object.keys(mat.sources);
  var chart = {
    type: 'bar',
    data: {
      labels: sources,
      datasets: [{ data: sources.map(s => mat.sources[s].TOTAL), backgroundColor: '#1b365d' }]
    },
    options: {
      title: { display: true, text: 'QTY Distribution by Source (FROM)', fontSize: 12 },
      legend: { display: false },
      plugins: { datalabels: { display: true, anchor: 'end', align: 'top', formatter: (v) => v.toFixed(2) } }
    }
  };
  return "https://quickchart.io/chart?c=" + encodeURIComponent(JSON.stringify(chart));
}

// -----------------------------------------------------------------------------
// HELPER UTILITIES
// -----------------------------------------------------------------------------

function createAndSavePDF(filename, htmlContent) {
  var blob = Utilities.newBlob(htmlContent, "text/html", filename.replace('.pdf', '.html'));
  var pdf = blob.getAs("application/pdf").setName(filename);
  DriveApp.createFile(pdf);
}

function formatNum(val, decimals) {
  var dec = decimals !== undefined ? decimals : 2;
  return Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
