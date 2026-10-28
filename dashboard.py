"""Write and open an HTML dashboard from a completed screener scan."""

from __future__ import annotations

import json
import os
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD_FILE = "screener_dashboard.html"


def _json_ready(value):
    if value is None:
        return None
    try:
        if value != value:  # NaN
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and abs(value) == float("inf"):
        return None
    return value


def write_dashboard(scan: dict, output_path: str | Path = DASHBOARD_FILE) -> Path:
    payload = json.loads(json.dumps(scan, default=_json_ready, allow_nan=False))
    html = _render_html(payload)
    path = Path(output_path).resolve()
    path.write_text(html, encoding="utf-8")
    return path


def write_and_open(scan: dict, output_path: str | Path = DASHBOARD_FILE) -> Path:
    path = write_dashboard(scan, output_path)
    print(f"\n📊 Dashboard written to {path}")
    # GitHub Actions has no screen: only write the file there, don't open a browser.
    if os.environ.get("GITHUB_ACTIONS") != "true":
        webbrowser.open(path.as_uri())
        print("   Opened in your default browser.")
    return path


def _render_html(scan: dict) -> str:
    data_json = json.dumps(scan, ensure_ascii=True)
    generated = scan.get("generated_at", "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Riverside Market Screener</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg: #0f1419;
      --panel: #171e27;
      --line: #243042;
      --text: #e8eef6;
      --muted: #8b9bb4;
      --buy: #3dd68c;
      --sell: #f07178;
      --hold: #d4a017;
      --watch: #5eead4;
      --up: #3dd68c;
      --down: #f07178;
      --range: #8b9bb4;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Segoe UI", Inter, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    header {{
      padding: 1.25rem 1.5rem 1rem;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: wrap;
      align-items: flex-start;
    }}
    header .sub.rule {{
      max-width: 360px;
      text-align: right;
    }}
    h1 {{ font-size: 1.25rem; font-weight: 650; }}
    .sub {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem; }}
    main {{ padding: 1.25rem 1.5rem 2.5rem; max-width: 1280px; margin: 0 auto; }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }}
    .kpi {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 0.9rem 1rem;
    }}
    .kpi .label {{ color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; }}
    .kpi .value {{ font-size: 1.45rem; font-weight: 700; margin-top: 0.2rem; }}
    .playbook {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }}
    .note {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 0.85rem 1rem;
      font-size: 0.86rem;
    }}
    .note h3 {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.35rem; color: var(--muted); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      overflow: hidden;
      margin-bottom: 1.25rem;
      font-size: 0.88rem;
    }}
    th, td {{ padding: 0.65rem 0.75rem; text-align: left; border-bottom: 1px solid var(--line); }}
    th {{ color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }}
    tr:last-child td {{ border-bottom: none; }}
    tbody tr {{ cursor: pointer; }}
    tbody tr:hover, tbody tr.active {{ background: #1f2834; }}
    .badge {{
      display: inline-block;
      padding: 0.12rem 0.5rem;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.03em;
    }}
    .BUY {{ background: rgba(61, 214, 140, 0.15); color: var(--buy); }}
    .SELL {{ background: rgba(240, 113, 120, 0.15); color: var(--sell); }}
    .HOLD {{ background: rgba(212, 160, 23, 0.15); color: var(--hold); }}
    .WATCH {{ background: rgba(94, 234, 212, 0.15); color: var(--watch); }}
    .UPTREND {{ color: var(--up); }}
    .DOWNTREND {{ color: var(--down); }}
    .RANGE {{ color: var(--range); }}
    .tabs {{ display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 0.85rem; }}
    .tab {{
      background: var(--panel);
      border: 1px solid var(--line);
      color: var(--text);
      padding: 0.4rem 0.75rem;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.85rem;
    }}
    .tab.active {{ border-color: var(--watch); color: var(--watch); }}
    .panel {{ margin-bottom: 1.5rem; }}
    .signal-box {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 1rem 1.1rem;
      margin-bottom: 0.85rem;
    }}
    .signal-box h2 {{ font-size: 1.05rem; margin-bottom: 0.35rem; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 0.5rem;
      margin-top: 0.75rem;
    }}
    .metric {{
      background: #121820;
      border-radius: 8px;
      padding: 0.55rem 0.65rem;
    }}
    .metric span {{ display: block; color: var(--muted); font-size: 0.7rem; text-transform: uppercase; }}
    .metric strong {{ font-size: 0.95rem; }}
    .chart-wrap {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 0.75rem 0.85rem 0.4rem;
      margin-bottom: 0.75rem;
      height: 260px;
    }}
    .chart-wrap.short {{ height: 210px; }}
    .empty {{ color: var(--muted); padding: 1rem 0; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Riverside Market Screener</h1>
      <p class="sub">Trend-first crypto scan · generated {generated}</p>
    </div>
    <p class="sub rule">Never buy a downtrend just because RSI is low.</p>
  </header>
  <main>
    <section class="kpis" id="kpis"></section>
    <section class="playbook">
      <article class="note">
        <h3>Uptrend — when to buy</h3>
        <p>Buy a dip into EMA21, or a 20-day high break with volume. That is a discount inside a rising market.</p>
      </article>
      <article class="note">
        <h3>Downtrend — do not buy</h3>
        <p>WAIT RALLY means wait for a bounce into EMA21 to fade/sell, or a breakdown. Oversold is not a buy.</p>
      </article>
      <article class="note">
        <h3>Range — fade extremes</h3>
        <p>NO EDGE means chop. Only fade RSI at Bollinger bands. No trend to follow.</p>
      </article>
    </section>
    <table>
      <thead>
        <tr>
          <th>Ticker</th><th>Action</th><th>Setup</th><th>Regime</th>
          <th>Close</th><th>RSI</th><th>ADX</th><th>10d ROC</th>
        </tr>
      </thead>
      <tbody id="table-body"></tbody>
    </table>
    <div class="tabs" id="tabs"></div>
    <div id="panels"></div>
  </main>
  <script>
    const SCAN = {data_json};
    const ACTION_CLASS = {{ BUY: "BUY", SELL: "SELL", HOLD: "HOLD", WATCH: "WATCH" }};

    function money(v) {{
      if (v == null) return "—";
      return "$" + Number(v).toLocaleString(undefined, {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
    }}
    function num(v, d=1) {{
      if (v == null) return "—";
      return Number(v).toFixed(d);
    }}

    const assets = SCAN.assets || [];
    const counts = {{ BUY: 0, SELL: 0, HOLD: 0, WATCH: 0 }};
    assets.forEach(a => {{ counts[a.action] = (counts[a.action] || 0) + 1; }});

    const kpiRoot = document.getElementById("kpis");
    [
      ["Assets scanned", assets.length, ""],
      ["Buy setups", counts.BUY || 0, "buy"],
      ["Sell setups", counts.SELL || 0, "sell"],
      ["Holds / wait", (counts.HOLD || 0) + (counts.WATCH || 0), "hold"]
    ].forEach(([label, value, tone]) => {{
      const el = document.createElement("div");
      el.className = "kpi";
      el.innerHTML = `<div class="label">${{label}}</div><div class="value ${{tone}}">${{value}}</div>`;
      kpiRoot.appendChild(el);
    }});

    const tbody = document.getElementById("table-body");
    const tabs = document.getElementById("tabs");
    const panels = document.getElementById("panels");
    const charts = [];

    function showTicker(ticker) {{
      document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.ticker === ticker));
      document.querySelectorAll("tbody tr").forEach(r => r.classList.toggle("active", r.dataset.ticker === ticker));
      const panel = document.querySelector(`.panel[data-ticker="${{ticker}}"]`);
      if (panel) panel.scrollIntoView({{ behavior: "smooth", block: "start" }});
    }}

    assets.forEach((asset, idx) => {{
      const tr = document.createElement("tr");
      tr.dataset.ticker = asset.ticker;
      tr.innerHTML = `
        <td><strong>${{asset.ticker}}</strong></td>
        <td><span class="badge ${{asset.action}}">${{asset.action}}</span></td>
        <td>${{asset.setup}}</td>
        <td class="${{asset.regime}}">${{asset.regime}}</td>
        <td>${{money(asset.close)}}</td>
        <td>${{num(asset.rsi)}}</td>
        <td>${{num(asset.adx)}}</td>
        <td>${{asset.roc == null ? "—" : (asset.roc >= 0 ? "+" : "") + num(asset.roc) + "%"}}</td>`;
      tr.addEventListener("click", () => showTicker(asset.ticker));
      tbody.appendChild(tr);

      const tab = document.createElement("button");
      tab.className = "tab" + (idx === 0 ? " active" : "");
      tab.dataset.ticker = asset.ticker;
      tab.textContent = asset.ticker;
      tab.addEventListener("click", () => showTicker(asset.ticker));
      tabs.appendChild(tab);

      const panel = document.createElement("section");
      panel.className = "panel";
      panel.dataset.ticker = asset.ticker;
      panel.innerHTML = `
        <div class="signal-box">
          <h2>${{asset.ticker}} · <span class="badge ${{asset.action}}">${{asset.action}}</span> ${{asset.setup}}</h2>
          <p>${{asset.reason}}</p>
          <p class="sub" style="margin-top:0.4rem">Next: ${{asset.next_step}}</p>
          <div class="metrics">
            <div class="metric"><span>Close</span><strong>${{money(asset.close)}}</strong></div>
            <div class="metric"><span>EMA21 threshold</span><strong>${{money(asset.ema21)}}</strong></div>
            <div class="metric"><span>EMA50</span><strong>${{money(asset.ema50)}}</strong></div>
            <div class="metric"><span>RSI 14</span><strong>${{num(asset.rsi)}}</strong></div>
            <div class="metric"><span>ADX</span><strong>${{num(asset.adx)}}</strong></div>
            <div class="metric"><span>Supertrend</span><strong>${{asset.st_label}}</strong></div>
            <div class="metric"><span>Rel volume</span><strong>${{num(asset.rel_volume, 2)}}x</strong></div>
            <div class="metric"><span>MACD hist</span><strong>${{num(asset.macd_hist, 4)}}</strong></div>
          </div>
        </div>
        <div class="chart-wrap"><canvas id="price-${{idx}}"></canvas></div>
        <div class="chart-wrap short"><canvas id="rsi-${{idx}}"></canvas></div>
        <div class="chart-wrap short"><canvas id="macd-${{idx}}"></canvas></div>
        <div class="chart-wrap short"><canvas id="adx-${{idx}}"></canvas></div>`;
      panels.appendChild(panel);

      const labels = (asset.series && asset.series.dates) || [];
      const grid = {{ color: "#243042" }};
      const ticks = {{ color: "#8b9bb4" }};
      const xAxis = {{ ticks: {{ color: "#8b9bb4", maxRotation: 0, autoSkip: true, maxTicksLimit: 8 }}, grid: {{ display: false }} }};
      const common = {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ color: "#e8eef6", boxWidth: 12 }} }} }},
        scales: {{
          x: xAxis,
          y: {{ ticks, grid }}
        }}
      }};

      charts.push(new Chart(document.getElementById("price-" + idx), {{
        type: "line",
        data: {{
          labels,
          datasets: [
            {{ label: "Close", data: asset.series.close, borderColor: "#e8eef6", borderWidth: 2, pointRadius: 0, tension: 0.1 }},
            {{ label: "EMA21", data: asset.series.ema21, borderColor: "#5eead4", borderWidth: 1.5, pointRadius: 0, borderDash: [5, 4] }},
            {{ label: "EMA50", data: asset.series.ema50, borderColor: "#8b9bb4", borderWidth: 1.5, pointRadius: 0 }},
            {{ label: "BB upper", data: asset.series.bb_upper, borderColor: "#f07178", borderWidth: 1, pointRadius: 0, borderDash: [2, 3] }},
            {{ label: "BB lower", data: asset.series.bb_lower, borderColor: "#3dd68c", borderWidth: 1, pointRadius: 0, borderDash: [2, 3] }}
          ]
        }},
        options: {{ ...common, plugins: {{ ...common.plugins, title: {{ display: true, text: "Price vs EMA21 / EMA50 / Bollinger", color: "#e8eef6" }} }} }}
      }}));

      charts.push(new Chart(document.getElementById("rsi-" + idx), {{
        type: "line",
        data: {{
          labels,
          datasets: [
            {{ label: "RSI 14", data: asset.series.rsi, borderColor: "#d4a017", borderWidth: 2, pointRadius: 0, tension: 0.15 }},
            {{ label: "Overbought 70", data: labels.map(() => 70), borderColor: "#f07178", borderWidth: 1, pointRadius: 0, borderDash: [4, 4] }},
            {{ label: "Oversold 30", data: labels.map(() => 30), borderColor: "#3dd68c", borderWidth: 1, pointRadius: 0, borderDash: [4, 4] }}
          ]
        }},
        options: {{
          ...common,
          scales: {{ ...common.scales, y: {{ ...common.scales.y, min: 0, max: 100 }} }},
          plugins: {{ ...common.plugins, title: {{ display: true, text: "RSI (do not buy oversold in a downtrend)", color: "#e8eef6" }} }}
        }}
      }}));

      // MACD histogram on its own: sign = momentum direction, bar height = momentum strength.
      const macd = asset.series.macd_hist || [];
      charts.push(new Chart(document.getElementById("macd-" + idx), {{
        type: "bar",
        data: {{
          labels,
          datasets: [
            {{
              label: "MACD histogram",
              data: macd,
              backgroundColor: macd.map(v => v == null ? "transparent" : v >= 0 ? "rgba(61,214,140,0.75)" : "rgba(240,113,120,0.75)"),
              barPercentage: 1.0,
              categoryPercentage: 1.0
            }}
          ]
        }},
        options: {{
          ...common,
          plugins: {{
            legend: {{ display: false }},
            title: {{ display: true, text: "Momentum (MACD histogram): green above 0 = bullish, red below 0 = bearish", color: "#e8eef6" }},
            tooltip: {{ callbacks: {{ label: ctx => "MACD hist: " + num(ctx.parsed.y, 4) + (ctx.parsed.y >= 0 ? "  (bullish)" : "  (bearish)") }} }}
          }},
          scales: {{
            x: xAxis,
            y: {{
              ticks,
              grid: {{ color: c => c.tick.value === 0 ? "#8b9bb4" : "#243042", lineWidth: c => c.tick.value === 0 ? 1.5 : 1 }}
            }}
          }}
        }}
      }}));

      // ADX on its own fixed 0–60 scale with the 20/25 trend thresholds drawn in.
      const adx = asset.series.adx || [];
      charts.push(new Chart(document.getElementById("adx-" + idx), {{
        type: "line",
        data: {{
          labels,
          datasets: [
            {{ label: "ADX", data: adx, borderColor: "#5eead4", borderWidth: 2, pointRadius: 0, tension: 0.15 }},
            {{ label: "Trending > 25", data: labels.map(() => 25), borderColor: "#d4a017", borderWidth: 1, pointRadius: 0, borderDash: [4, 4] }},
            {{ label: "Choppy < 20", data: labels.map(() => 20), borderColor: "#8b9bb4", borderWidth: 1, pointRadius: 0, borderDash: [2, 3] }}
          ]
        }},
        options: {{
          ...common,
          scales: {{ ...common.scales, y: {{ ...common.scales.y, min: 0, max: 60 }} }},
          plugins: {{ ...common.plugins, title: {{ display: true, text: "Trend strength (ADX): above 25 = strong trend, below 20 = range/chop", color: "#e8eef6" }} }}
        }}
      }}));
    }});

    if (!assets.length) {{
      document.getElementById("panels").innerHTML = '<p class="empty">No assets passed the minimum history filter.</p>';
    }}
  </script>
</body>
</html>
"""
