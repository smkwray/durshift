import Plotly from "plotly.js-dist-min";

/* ── Theme ────────────────────────────────────────────────────── */

function getThemeColors() {
  const s = getComputedStyle(document.documentElement);
  return {
    grid: s.getPropertyValue("--plot-grid").trim(),
    font: s.getPropertyValue("--plot-font").trim(),
  };
}

const C = {
  blue: "#4a90d9",
  orange: "#e8914f",
  green: "#34d399",
  red: "#f87171",
  purple: "#a78bfa",
  teal: "#2dd4bf",
};

function layoutBase(extraRight = 0) {
  const t = getThemeColors();
  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: t.font, size: 13 },
    margin: { t: 24, r: 20 + extraRight, b: 48, l: 56 },
    xaxis: { gridcolor: t.grid, zerolinecolor: t.grid },
    yaxis: { gridcolor: t.grid, zerolinecolor: t.grid },
  };
}

const PCFG = { responsive: true, displayModeBar: false };

/* ── Theme toggle ─────────────────────────────────────────────── */

function initThemeToggle() {
  const saved = localStorage.getItem("durshift-theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved || (prefersDark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);
  document.querySelector('meta[name="color-scheme"]').content = theme;

  document.getElementById("theme-toggle").addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    document.querySelector('meta[name="color-scheme"]').content = next;
    localStorage.setItem("durshift-theme", next);
    relayoutAllCharts();
  });
}

const CHART_IDS = [
  "chart-monthly",
  "chart-duration-buckets",
  "chart-yield-changes",
  "chart-dealer-changes",
  "chart-operations",
  "chart-timeline",
  "chart-soma",
  "chart-tips-split",
];

function relayoutAllCharts() {
  const t = getThemeColors();
  const update = {
    "font.color": t.font,
    "xaxis.gridcolor": t.grid,
    "xaxis.zerolinecolor": t.grid,
    "yaxis.gridcolor": t.grid,
    "yaxis.zerolinecolor": t.grid,
  };
  for (const id of CHART_IDS) {
    const el = document.getElementById(id);
    if (el && el.data) Plotly.relayout(el, update);
  }
}

/* ── Data ─────────────────────────────────────────────────────── */

async function load(path) {
  const res = await fetch(path);
  return res.json();
}

function fmt(n) {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(1)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
  return `$${n.toLocaleString()}`;
}

/* ── Init ─────────────────────────────────────────────────────── */

async function init() {
  initThemeToggle();

  const [summary, monthly, buckets, yieldChanges, dealerChanges, operations, soma, topCusips] =
    await Promise.all([
      load("data/summary.json"),
      load("data/monthly_volume.json"),
      load("data/duration_buckets.json"),
      load("data/yield_changes.json"),
      load("data/dealer_changes.json"),
      load("data/operations.json"),
      load("data/soma.json").catch(() => null),
      load("data/top_cusips.json").catch(() => null),
    ]);

  renderSummary(summary);
  renderMonthly(monthly);
  renderDurationBuckets(buckets);
  renderTipsSplit(summary);
  renderYieldChanges(yieldChanges);
  renderDealerChanges(dealerChanges);
  renderOperations(operations);
  if (topCusips) renderTopCusips(topCusips);
  renderTimeline(operations);
  if (soma) {
    renderSoma(soma);
  } else {
    const el = document.getElementById("chart-soma");
    if (el) el.innerHTML = '<p style="text-align:center;color:var(--text-dim);padding:3rem 0;">SOMA data not available. Run fetch-soma-holdings.</p>';
  }
}

/* ── Renderers ────────────────────────────────────────────────── */

function renderSummary(s) {
  document.querySelector("#card-par .stat-value").textContent = fmt(s.total_par_B * 1e9);
  document.querySelector("#card-duration .stat-value").textContent = fmt(s.total_duration_dollars_B * 1e9);
  document.querySelector("#card-operations .stat-value").textContent = s.total_operation_dates.toLocaleString();
  document.querySelector("#card-cusips .stat-value").textContent = s.unique_cusips.toLocaleString();
  // Date range card
  const rangeEl = document.querySelector("#card-range .stat-value");
  if (rangeEl && s.date_range_start && s.date_range_end) {
    rangeEl.textContent = `${s.date_range_start.slice(0, 7)} — ${s.date_range_end.slice(0, 7)}`;
    rangeEl.style.fontSize = "1.1rem";
  }
}

function renderMonthly(data) {
  const L = layoutBase(48);
  Plotly.newPlot(
    "chart-monthly",
    [
      {
        x: data.map((d) => d.operation_date),
        y: data.map((d) => d.total_par / 1e9),
        type: "bar",
        name: "Par Retired ($B)",
        marker: { color: C.blue },
        hovertemplate: "%{x}<br>$%{y:.1f}B<extra>Par</extra>",
      },
      {
        x: data.map((d) => d.operation_date),
        y: data.map((d) => d.total_duration / 1e9),
        type: "scatter",
        mode: "lines+markers",
        name: "Duration-$ ($B)",
        yaxis: "y2",
        line: { color: C.orange, width: 2 },
        marker: { size: 5 },
        hovertemplate: "%{x}<br>$%{y:.1f}B<extra>Dur-$</extra>",
      },
    ],
    {
      ...L,
      yaxis: { ...L.yaxis, title: "Par Retired ($B)", rangemode: "tozero" },
      yaxis2: { title: "Duration-$ ($B)", overlaying: "y", side: "right", gridcolor: "transparent", rangemode: "tozero" },
      legend: { x: 0, y: 1.12, orientation: "h" },
      barmode: "group",
    },
    PCFG
  );
}

function renderDurationBuckets(data) {
  const L = layoutBase();
  // Data arrives pre-sorted by maturity from generate_site_data.py
  Plotly.newPlot(
    "chart-duration-buckets",
    [
      {
        x: data.map((d) => d.maturity_bucket),
        y: data.map((d) => d.pct_par),
        type: "bar",
        name: "% of Par",
        marker: { color: C.blue },
        hovertemplate: "%{x}<br>%{y:.1f}%<extra>Par</extra>",
      },
      {
        x: data.map((d) => d.maturity_bucket),
        y: data.map((d) => d.pct_duration),
        type: "bar",
        name: "% of Duration-$",
        marker: { color: C.orange },
        hovertemplate: "%{x}<br>%{y:.1f}%<extra>Dur-$</extra>",
      },
    ],
    {
      ...L,
      barmode: "group",
      xaxis: { ...L.xaxis, type: "category", categoryorder: "array", categoryarray: data.map((d) => d.maturity_bucket) },
      yaxis: { ...L.yaxis, title: "Share (%)" },
      legend: { x: 0, y: 1.12, orientation: "h" },
    },
    PCFG
  );
}

function renderTipsSplit(summary) {
  const L = layoutBase();
  const nom = summary.nominal_par_B || 310;
  const tips = summary.tips_par_B || 11;
  Plotly.newPlot(
    "chart-tips-split",
    [
      {
        labels: ["Nominal Coupons", "TIPS"],
        values: [nom, tips],
        type: "pie",
        hole: 0.55,
        marker: { colors: [C.blue, C.green] },
        textinfo: "label+percent",
        textposition: "inside",
        insidetextorientation: "horizontal",
        hovertemplate: "%{label}<br>$%{value:.1f}B<br>%{percent}<extra></extra>",
        textfont: { size: 14 },
      },
    ],
    {
      ...L,
      margin: { ...L.margin, t: 16, b: 16 },
      showlegend: false,
      annotations: [{ text: `$${(nom + tips).toFixed(0)}B`, showarrow: false, font: { size: 22, color: getThemeColors().font } }],
    },
    PCFG
  );
}

function renderYieldChanges(data) {
  const L = layoutBase();
  const means = data.map((d) => d.mean_bp);
  Plotly.newPlot(
    "chart-yield-changes",
    [
      {
        x: data.map((d) => d.tenor),
        y: means,
        type: "bar",
        marker: { color: means.map((v) => (v > 0 ? C.red : C.blue)) },
        error_y: {
          type: "data",
          symmetric: false,
          array: data.map((d) => (d.ci_upper != null ? d.ci_upper - d.mean_bp : 0)),
          arrayminus: data.map((d) => (d.ci_lower != null ? d.mean_bp - d.ci_lower : 0)),
          visible: true,
          color: "#888",
          thickness: 1.5,
        },
        customdata: data.map((d) => [d.ci_lower, d.ci_upper, d.p_value, d.n]),
        hovertemplate: "%{x}: %{y:+.2f} bp<br>95% CI: [%{customdata[0]:+.2f}, %{customdata[1]:+.2f}]<br>p = %{customdata[2]:.3f} (n = %{customdata[3]})<extra></extra>",
      },
    ],
    {
      ...L,
      xaxis: { ...L.xaxis, type: "category", title: "CMT Tenor" },
      yaxis: { ...L.yaxis, title: "Mean Change (bp)" },
      showlegend: false,
      shapes: [{ type: "line", x0: -0.5, x1: data.length - 0.5, y0: 0, y1: 0, line: { color: "#888", width: 1, dash: "dot" } }],
    },
    PCFG
  );
}

function renderDealerChanges(data) {
  const L = layoutBase();
  const means = data.map((d) => d.mean_B);
  Plotly.newPlot(
    "chart-dealer-changes",
    [
      {
        x: data.map((d) => d.bucket),
        y: means,
        type: "bar",
        marker: { color: means.map((v) => (v >= 0 ? C.green : C.red)) },
        error_y: {
          type: "data",
          symmetric: false,
          array: data.map((d) => (d.ci_upper != null ? d.ci_upper - d.mean_B : 0)),
          arrayminus: data.map((d) => (d.ci_lower != null ? d.mean_B - d.ci_lower : 0)),
          visible: true,
          color: "#888",
          thickness: 1.5,
        },
        customdata: data.map((d) => [d.ci_lower, d.ci_upper, d.p_value, d.n]),
        hovertemplate: "%{x}: %{y:+.2f}B<br>95% CI: [%{customdata[0]:+.2f}, %{customdata[1]:+.2f}]<br>p = %{customdata[2]:.3f} (n = %{customdata[3]})<extra></extra>",
      },
    ],
    {
      ...L,
      xaxis: { ...L.xaxis, type: "category" },
      yaxis: { ...L.yaxis, title: "Mean Change ($B)" },
      showlegend: false,
      shapes: [{ type: "line", x0: -0.5, x1: data.length - 0.5, y0: 0, y1: 0, line: { color: "#888", width: 1, dash: "dot" } }],
    },
    PCFG
  );
}

function renderOperations(data) {
  const L = layoutBase();
  const cm = data.filter((d) => d.operation_types.includes("Cash Management"));
  const ls = data.filter((d) => d.operation_types.includes("Liquidity Support") && !d.operation_types.includes("Cash Management"));
  const other = data.filter((d) => !d.operation_types.includes("Cash Management") && !d.operation_types.includes("Liquidity Support"));

  function tr(subset, name, color) {
    return {
      x: subset.map((d) => d.total_par / 1e9),
      y: subset.map((d) => d.avg_duration),
      text: subset.map((d) => d.operation_date),
      customdata: subset.map((d) => [d.n_securities, d.security_types, (d.total_duration_dollars / 1e9).toFixed(1)]),
      type: "scatter",
      mode: "markers",
      name,
      marker: { color, size: subset.map((d) => Math.max(6, Math.sqrt(d.total_par / 1e8) * 3)), opacity: 0.75 },
      hovertemplate:
        "<b>%{text}</b><br>Par: $%{x:.1f}B<br>Avg Duration: %{y:.1f}<br>Securities: %{customdata[0]}<br>Types: %{customdata[1]}<br>Dur-$: $%{customdata[2]}B<extra>%{fullData.name}</extra>",
    };
  }

  Plotly.newPlot(
    "chart-operations",
    [tr(ls, "Liquidity Support", C.blue), tr(cm, "Cash Management", C.orange), tr(other, "Other", C.purple)],
    {
      ...L,
      xaxis: { ...L.xaxis, type: "linear", title: "Total Par Accepted ($B)" },
      yaxis: { ...L.yaxis, type: "linear", title: "Avg Modified Duration" },
      legend: { x: 0.65, y: 0.95 },
    },
    PCFG
  );
}

function renderTopCusips(data) {
  const tbody = document.getElementById("top-cusips-body");
  if (!tbody) return;
  tbody.innerHTML = data
    .map(
      (d) =>
        `<tr><td>${d.cusip}</td><td>${d.security_type}</td><td>${d.coupon_pct}%</td><td>${d.maturity_date}</td><td>$${(d.total_par_M / 1000).toFixed(1)}B</td><td>${d.n_operations}</td><td>${d.avg_price.toFixed(1)}</td></tr>`
    )
    .join("");
}

function renderTimeline(data) {
  const L = layoutBase();
  Plotly.newPlot(
    "chart-timeline",
    [
      {
        x: data.map((d) => d.operation_date),
        y: data.map((d) => d.total_duration_dollars / 1e9),
        type: "bar",
        marker: {
          color: data.map((d) => (d.operation_types.includes("Cash Management") ? C.orange : C.blue)),
        },
        hovertemplate: "%{x}<br>$%{y:.1f}B dur-$<extra></extra>",
      },
    ],
    {
      ...L,
      xaxis: { ...L.xaxis, type: "date" },
      yaxis: { ...L.yaxis, title: "Duration-Dollars ($B)" },
      showlegend: false,
    },
    PCFG
  );
}

function renderSoma(data) {
  const L = layoutBase();
  const recent = data.filter((d) => d.date >= "2020");
  const dates = recent.map((d) => d.date);

  // Stack order: Notes & Bonds (bottom/largest) → MBS → TIPS → Bills (top)
  Plotly.newPlot(
    "chart-soma",
    [
      { x: dates, y: recent.map((d) => d.notes_bonds), type: "scatter", mode: "lines", name: "Notes & Bonds", line: { color: C.blue, width: 1 }, stackgroup: "one", fillcolor: "rgba(74,144,217,0.5)" },
      { x: dates, y: recent.map((d) => d.mbs), type: "scatter", mode: "lines", name: "MBS", line: { color: C.purple, width: 1 }, stackgroup: "one", fillcolor: "rgba(167,139,250,0.5)" },
      { x: dates, y: recent.map((d) => d.tips), type: "scatter", mode: "lines", name: "TIPS", line: { color: C.green, width: 1 }, stackgroup: "one", fillcolor: "rgba(52,211,153,0.5)" },
      { x: dates, y: recent.map((d) => d.bills), type: "scatter", mode: "lines", name: "Bills", line: { color: C.orange, width: 1 }, stackgroup: "one", fillcolor: "rgba(232,145,79,0.5)" },
    ],
    {
      ...L,
      xaxis: { ...L.xaxis, type: "date" },
      yaxis: { ...L.yaxis, title: "Holdings ($B)" },
      legend: { x: 0, y: 1.12, orientation: "h", traceorder: "normal" },
    },
    PCFG
  );
}

init();
