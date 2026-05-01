"""分析报告服务：聚合统计、LLM 调用、HTML 导出"""
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from workday.core.models import AnalysisReport
from workday.core.logger import get_logger
from workday.utils import fmt_duration
logger = get_logger(__name__)

CATEGORIES = ["工作", "学习", "娱乐", "其他"]
CATEGORY_COLORS = {
    "工作": "#3b82f6",
    "学习": "#10b981",
    "娱乐": "#f59e0b",
    "其他": "#6b7280",
}


def _parse_week_range(period_key: str) -> tuple[int, int]:
    """解析 ISO 周 period_key (YYYY-Www) 为 (start_ts, end_ts)"""
    year_str, week_str = period_key.split("-W")
    year, week = int(year_str), int(week_str)
    monday = date.fromisocalendar(year, week, 1)
    next_monday = monday + timedelta(days=7)
    start_ts = int(datetime(monday.year, monday.month, monday.day, 0, 0, 0).timestamp())
    end_ts = int(datetime(next_monday.year, next_monday.month, next_monday.day, 0, 0, 0).timestamp())
    return start_ts, end_ts


def _parse_day_range(period_key: str) -> tuple[int, int]:
    """解析日 period_key (YYYY-MM-DD) 为 (start_ts, end_ts)"""
    d = date.fromisoformat(period_key)
    next_d = d + timedelta(days=1)
    start_ts = int(datetime(d.year, d.month, d.day, 0, 0, 0).timestamp())
    end_ts = int(datetime(next_d.year, next_d.month, next_d.day, 0, 0, 0).timestamp())
    return start_ts, end_ts


def _period_label(scope: str, period_key: str) -> str:
    if scope == "day":
        d = date.fromisoformat(period_key)
        week_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return f"{period_key} {week_names[d.weekday()]}"
    else:
        year_str, week_str = period_key.split("-W")
        year, week = int(year_str), int(week_str)
        monday = date.fromisocalendar(year, week, 1)
        sunday = monday + timedelta(days=6)
        return f"{period_key} ({monday.strftime('%m-%d')} ~ {sunday.strftime('%m-%d')})"


def compute_period_stats(db, scope: str, period_key: str) -> tuple[int, int, dict]:
    """计算指定时间段的统计数据，返回 (start_ts, end_ts, stats_dict)"""
    if scope == "day":
        start_ts, end_ts = _parse_day_range(period_key)
        cards = db.get_timeline_cards_by_day(period_key)
    else:
        start_ts, end_ts = _parse_week_range(period_key)
        cards = db.get_timeline_cards_by_time_range(start_ts, end_ts)

    cat_map: dict[str, dict] = {c: {"seconds": 0, "count": 0} for c in CATEGORIES}
    hourly: list[dict] = [{"hour": h, "seconds": 0} for h in range(24)]
    daily_map: dict[str, dict] = {}
    top_list = []
    total_seconds = 0

    for card in cards:
        duration = max(0, int(card.end_ts - card.start_ts))
        total_seconds += duration
        cat = card.category if card.category in CATEGORIES else "其他"
        cat_map[cat]["seconds"] += duration
        cat_map[cat]["count"] += 1

        dt = datetime.fromtimestamp(card.start_ts)
        hourly[dt.hour]["seconds"] += duration

        date_str = dt.strftime("%Y-%m-%d")
        if date_str not in daily_map:
            daily_map[date_str] = {"date": date_str, "seconds": 0, "category_seconds": {c: 0 for c in CATEGORIES}}
        daily_map[date_str]["seconds"] += duration
        daily_map[date_str]["category_seconds"][cat] += duration

        top_list.append({
            "title": card.title,
            "category": cat,
            "seconds": duration,
            "start": dt.strftime("%H:%M"),
            "description": card.description or "",
        })

    top_list.sort(key=lambda x: x["seconds"], reverse=True)

    category_breakdown = [
        {"category": c, "seconds": cat_map[c]["seconds"], "count": cat_map[c]["count"]}
        for c in CATEGORIES
    ]

    if scope == "week":
        daily_distribution = []
        for i in range(7):
            d = date.fromtimestamp(start_ts) + timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            if ds in daily_map:
                daily_distribution.append(daily_map[ds])
            else:
                daily_distribution.append({"date": ds, "seconds": 0, "category_seconds": {c: 0 for c in CATEGORIES}})
    else:
        daily_distribution = []

    stats = {
        "scope": scope,
        "period_key": period_key,
        "period_label": _period_label(scope, period_key),
        "total_cards": len(cards),
        "total_active_seconds": total_seconds,
        "category_breakdown": category_breakdown,
        "hourly_distribution": hourly,
        "daily_distribution": daily_distribution,
        "top_activities": top_list[:8],
    }
    return start_ts, end_ts, stats


def generate_report(db, scope: str, period_key: str) -> AnalysisReport:
    """生成分析报告（含 LLM 调用），保存到数据库并返回"""
    from workday.services.llm_call import generate_analysis_summary
    from workday.services.prompts import get_analysis_summary_prompt
    from workday.core.config import get_config

    start_ts, end_ts, stats = compute_period_stats(db, scope, period_key)

    if stats["total_cards"] == 0:
        raise ValueError(f"该时间段 ({period_key}) 无活动数据，无法生成报告")

    prompt = get_analysis_summary_prompt(
        scope_label=stats["period_label"],
        stats=stats,
        cards_brief=stats["top_activities"],
    )

    summary = generate_analysis_summary(prompt)
    model = get_config().llm.model

    report = AnalysisReport(
        scope=scope,
        period_key=period_key,
        start_ts=start_ts,
        end_ts=end_ts,
        stats_json=json.dumps(stats, ensure_ascii=False),
        summary=summary,
        model=model,
    )
    db.insert_or_replace_analysis_report(report)
    return report


def _blocks_to_html(blocks: list) -> str:
    """将 markdown_parser blocks 转为 HTML 片段"""
    parts = []
    in_ul = False
    for text, kind in blocks:
        if kind == "bullet":
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{text}</li>")
        else:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            if kind == "title":
                parts.append(f"<h1>{text}</h1>")
            elif kind == "heading":
                parts.append(f"<h2>{text}</h2>")
            elif kind == "subheading":
                parts.append(f"<h3>{text}</h3>")
            elif kind == "body":
                parts.append(f"<p>{text}</p>")
            elif kind == "code":
                parts.append(f"<pre><code>{text}</code></pre>")
            elif kind == "space":
                pass
    if in_ul:
        parts.append("</ul>")
    return "\n".join(parts)


def export_html(report: AnalysisReport, out_path: Path) -> None:
    """将分析报告导出为自包含 HTML 文件"""
    from workday.utils.markdown_parser import parse_markdown

    stats = json.loads(report.stats_json)
    _, blocks = parse_markdown(report.summary)
    summary_html = _blocks_to_html(blocks)

    period_label = stats.get("period_label", report.period_key)
    total_str = fmt_duration(stats.get("total_active_seconds", 0))
    total_cards = stats.get("total_cards", 0)

    cat_breakdown = stats.get("category_breakdown", [])
    main_cat = max(cat_breakdown, key=lambda x: x["seconds"], default={"category": "—", "seconds": 0})
    main_cat_total = stats.get("total_active_seconds", 1) or 1
    main_cat_pct = round(main_cat["seconds"] / main_cat_total * 100)

    top_activities = stats.get("top_activities", [])
    top_rows = ""
    for act in top_activities:
        top_rows += f"""<tr>
          <td>{act['start']}</td>
          <td><span class="cat-badge cat-{act['category']}">{act['category']}</span></td>
          <td>{act['title']}</td>
          <td>{fmt_duration(act['seconds'])}</td>
        </tr>"""

    pie_labels = json.dumps([c["category"] for c in cat_breakdown], ensure_ascii=False)
    pie_data = json.dumps([c["seconds"] // 60 for c in cat_breakdown])
    pie_colors = json.dumps([CATEGORY_COLORS.get(c["category"], "#999") for c in cat_breakdown])

    hourly = stats.get("hourly_distribution", [{"hour": h, "seconds": 0} for h in range(24)])
    hourly_labels = json.dumps([f"{h:02d}:00" for h in range(24)])
    hourly_data = json.dumps([h["seconds"] // 60 for h in hourly])

    scope = stats.get("scope", "day")
    weekly_chart_html = ""
    weekly_script = ""
    if scope == "week":
        daily = stats.get("daily_distribution", [])
        daily_labels = json.dumps([d["date"][5:] for d in daily], ensure_ascii=False)
        datasets = []
        for cat in CATEGORIES:
            datasets.append({
                "label": cat,
                "data": [d["category_seconds"].get(cat, 0) // 60 for d in daily],
                "backgroundColor": CATEGORY_COLORS.get(cat, "#999"),
            })
        daily_datasets = json.dumps(datasets, ensure_ascii=False)
        weekly_chart_html = """<div class="chart-card">
          <h3>每日活跃分布（分钟）</h3>
          <canvas id="dailyStack"></canvas>
        </div>"""
        weekly_script = f"""const dailyCtx = document.getElementById('dailyStack').getContext('2d');
    new Chart(dailyCtx, {{
      type: 'bar',
      data: {{ labels: {daily_labels}, datasets: {daily_datasets} }},
      options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }}, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, title: {{ display: true, text: '分钟' }} }} }} }}
    }});"""

    created_at = report.created_at.strftime("%Y-%m-%d %H:%M") if report.created_at else ""

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Workday 工作分析 · {period_label}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f8fafc; color: #1e293b; }}
    header {{ background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 28px 32px; }}
    header h1 {{ font-size: 1.8rem; margin-bottom: 4px; }}
    header p {{ opacity: 0.8; font-size: 0.95rem; }}
    .container {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
    @media (max-width: 768px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    .kpi-card {{ background: white; border-radius: 10px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
    .kpi-card .label {{ font-size: 0.78rem; color: #64748b; margin-bottom: 4px; }}
    .kpi-card .value {{ font-size: 1.6rem; font-weight: 700; color: #1e293b; }}
    .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 24px; }}
    .chart-card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
    .chart-card h3 {{ font-size: 0.9rem; color: #475569; margin-bottom: 14px; }}
    .summary-card {{ background: white; border-radius: 10px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 24px; }}
    .summary-card h2 {{ font-size: 1.1rem; color: #1e40af; margin-bottom: 16px; }}
    .summary-content h1 {{ font-size: 1.1rem; color: #1e40af; margin: 16px 0 8px; }}
    .summary-content h2 {{ font-size: 1rem; color: #1e40af; margin: 14px 0 6px; }}
    .summary-content h3 {{ font-size: 0.95rem; color: #475569; margin: 12px 0 4px; }}
    .summary-content p {{ color: #334155; line-height: 1.7; margin-bottom: 8px; }}
    .summary-content ul {{ padding-left: 20px; margin-bottom: 8px; }}
    .summary-content li {{ color: #334155; line-height: 1.7; }}
    .activities-card {{ background: white; border-radius: 10px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 24px; }}
    .activities-card h2 {{ font-size: 1rem; color: #475569; margin-bottom: 14px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    th {{ background: #f1f5f9; color: #475569; padding: 8px 12px; text-align: left; font-weight: 600; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }}
    tr:last-child td {{ border-bottom: none; }}
    .cat-badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; color: white; }}
    .cat-工作 {{ background: #3b82f6; }}
    .cat-学习 {{ background: #10b981; }}
    .cat-娱乐 {{ background: #f59e0b; }}
    .cat-其他 {{ background: #6b7280; }}
    footer {{ text-align: center; color: #94a3b8; font-size: 0.8rem; padding: 24px 0; }}
  </style>
</head>
<body>
  <header>
    <h1>Workday 工作分析报告</h1>
    <p>{period_label} &nbsp;·&nbsp; 生成时间：{created_at}</p>
  </header>
  <div class="container">
    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">总活跃时长</div><div class="value">{total_str}</div></div>
      <div class="kpi-card"><div class="label">活动卡片数</div><div class="value">{total_cards}</div></div>
      <div class="kpi-card"><div class="label">主要分类</div><div class="value">{main_cat['category']}</div></div>
      <div class="kpi-card"><div class="label">主要分类占比</div><div class="value">{main_cat_pct}%</div></div>
    </div>

    <div class="charts-grid">
      <div class="chart-card">
        <h3>分类分布（分钟）</h3>
        <canvas id="categoryPie"></canvas>
      </div>
      <div class="chart-card">
        <h3>小时活跃分布（分钟）</h3>
        <canvas id="hourlyBar"></canvas>
      </div>
      {weekly_chart_html}
    </div>

    <div class="summary-card">
      <h2>AI 工作总结</h2>
      <div class="summary-content">
        {summary_html}
      </div>
    </div>

    <div class="activities-card">
      <h2>主要活动</h2>
      <table>
        <thead><tr><th>时间</th><th>分类</th><th>活动</th><th>时长</th></tr></thead>
        <tbody>{top_rows}</tbody>
      </table>
    </div>
  </div>
  <footer>由 Workday 生成 · <a href="https://github.com/8DE4732A/workday" style="color:#94a3b8">GitHub</a></footer>

  <script>
    const pieCtx = document.getElementById('categoryPie').getContext('2d');
    new Chart(pieCtx, {{
      type: 'doughnut',
      data: {{ labels: {pie_labels}, datasets: [{{ data: {pie_data}, backgroundColor: {pie_colors}, borderWidth: 2 }}] }},
      options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }} }}
    }});

    const hourCtx = document.getElementById('hourlyBar').getContext('2d');
    new Chart(hourCtx, {{
      type: 'bar',
      data: {{ labels: {hourly_labels}, datasets: [{{ label: '活跃分钟', data: {hourly_data}, backgroundColor: '#3b82f6' }}] }},
      options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ title: {{ display: true, text: '分钟' }} }} }} }}
    }});

    {weekly_script}
  </script>
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
    logger.info(f"HTML report exported to {out_path}")
