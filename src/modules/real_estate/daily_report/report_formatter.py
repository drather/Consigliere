"""
report_formatter — DimensionResult 기반 제네릭 출력 계층.
차원 ID를 하드코딩하지 않는다. 모든 레이블·근거는 DimensionResult에서 온다.
"""
import itertools
from typing import Dict, List, Optional
from .report_types import TrendData, CommuteData


_TREND_COUNTER = itertools.count()


def render_trend(trend: TrendData) -> str:
    points = trend["points"]
    if not points:
        return "**📈 거래 추세** — 데이터 없음"

    uid = next(_TREND_COUNTER)
    avg_eok = trend["avg_eok"]
    change_pct = trend["change_pct"]
    area_sqm = trend["area_sqm"]
    prices = [p["price_eok"] for p in points]
    dates = [p["deal_date"] for p in points]
    n = len(points)

    is_rising = n < 2 or prices[-1] >= prices[0]
    color = "#a6e3a1" if is_rising else "#f38ba8"
    arrow = "▲" if change_pct > 0 else ("▼" if change_pct < 0 else "―")
    change_color = "#a6e3a1" if change_pct >= 0 else "#f38ba8"

    x_start, x_end = 60, 500
    y_top, y_bottom = 15, 70
    xs = (
        [x_start]
        if n == 1
        else [int(x_start + i * (x_end - x_start) / (n - 1)) for i in range(n)]
    )

    p_min, p_max = min(prices), max(prices)

    def price_to_y(p: float) -> int:
        if p_max == p_min:
            return (y_top + y_bottom) // 2
        return int(y_bottom - (p - p_min) / (p_max - p_min) * (y_bottom - y_top))

    ys = [price_to_y(p) for p in prices]
    high_idx = prices.index(max(prices))

    polyline_pts = " ".join(f"{x},{y}" for x, y in zip(xs, ys))
    polygon_pts = f"{polyline_pts} {xs[-1]},{y_bottom + 5} {xs[0]},{y_bottom + 5}"

    circles = ""
    labels = ""
    for i, (x, y, p) in enumerate(zip(xs, ys, prices)):
        is_last = i == n - 1
        is_high = i == high_idx and n > 1

        if is_last:
            fill, stroke, r = "#89b4fa", "#89b4fa", 6
            label_color, label_text = "#89b4fa", f"{p:.1f}억 ★"
        elif is_high:
            fill, stroke, r = color, color, 5
            label_color, label_text = color, f"{p:.1f}억 ↑"
        else:
            fill, stroke, r = "#1e1e2e", color, 4
            label_color, label_text = "#a6adc8", f"{p:.1f}억"

        circles += (
            f'<circle cx="{x}" cy="{y}" r="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
        )
        labels += (
            f'<text x="{x}" y="{y - 8}" text-anchor="middle" '
            f'fill="{label_color}" font-size="10" font-family="system-ui" '
            f'font-weight="600">{label_text}</text>\n'
        )

    mid_price = (p_max + p_min) / 2
    y_mid = (y_top + y_bottom) // 2
    y_labels = (
        f'<text x="555" y="18" text-anchor="end" fill="#6c7086" font-size="9" font-family="system-ui">{p_max:.1f}억</text>\n'
        f'<text x="555" y="{y_mid + 3}" text-anchor="end" fill="#6c7086" font-size="9" font-family="system-ui">{mid_price:.1f}억</text>\n'
        f'<text x="555" y="{y_bottom}" text-anchor="end" fill="#6c7086" font-size="9" font-family="system-ui">{p_min:.1f}억</text>\n'
    ) if p_max != p_min else ""

    date_items = "".join(
        f'<span style="flex:1;text-align:center">{d[5:]}</span>' for d in dates
    )
    date_labels = (
        f'<div style="display:flex;font-size:10px;color:#6c7086;'
        f'margin-top:4px;padding:0 50px">{date_items}</div>'
    )

    date_range_str = f"{dates[0][5:]} ~ {dates[-1][5:]}" if n > 1 else dates[0][5:]

    return (
        f'<div style="background:#181825;border-radius:10px;padding:12px 14px;margin-bottom:12px">\n'
        f'  <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:8px">\n'
        f'    <div>\n'
        f'      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:#6c7086">📈 최근 실거래 추세 ({n}건)</div>\n'
        f'      <div style="font-size:11px;color:#585b70;margin-top:2px">{date_range_str} · {area_sqm:.0f}㎡</div>\n'
        f'    </div>\n'
        f'    <div style="text-align:right">\n'
        f'      <div style="font-size:18px;font-weight:800;color:#cdd6f4">{avg_eok:.1f}억</div>\n'
        f'      <div style="font-size:12px;font-weight:700;color:{change_color}">{arrow} {abs(change_pct):.1f}% 전월比</div>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'  <svg viewBox="0 0 560 90" xmlns="http://www.w3.org/2000/svg" style="display:block;width:100%">\n'
        f'    <defs>\n'
        f'      <linearGradient id="grad{uid}" x1="0" y1="0" x2="0" y2="1">\n'
        f'        <stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>\n'
        f'        <stop offset="100%" stop-color="{color}" stop-opacity="0"/>\n'
        f'      </linearGradient>\n'
        f'    </defs>\n'
        f'    <line x1="0" y1="22" x2="560" y2="22" stroke="#313244" stroke-width="1" stroke-dasharray="4,4"/>\n'
        f'    <line x1="0" y1="45" x2="560" y2="45" stroke="#313244" stroke-width="1" stroke-dasharray="4,4"/>\n'
        f'    <line x1="0" y1="68" x2="560" y2="68" stroke="#313244" stroke-width="1" stroke-dasharray="4,4"/>\n'
        f'    {y_labels}'
        f'    <polygon points="{polygon_pts}" fill="url(#grad{uid})"/>\n'
        f'    <polyline points="{polyline_pts}" fill="none" stroke="{color}" '
        f'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>\n'
        f'    {circles}'
        f'    {labels}'
        f'  </svg>\n'
        f'  {date_labels}\n'
        f'</div>'
    )


def render_commute(commute: CommuteData) -> str:
    def fmt(minutes: Optional[int]) -> str:
        return f"{minutes}분" if minutes is not None else "조회 불가"

    transit_str = fmt(commute["transit_minutes"])
    car_str = fmt(commute["car_minutes"])
    walk_str = fmt(commute["walk_minutes"])
    route = commute.get("route_summary", "")

    lines = [
        "**🚌 출퇴근**",
        "| 대중교통 | 자차 | 도보 |",
        "|:---:|:---:|:---:|",
        f"| {transit_str} | {car_str} | {walk_str} |",
    ]
    if route:
        lines.append(f"*{route}*")
    return "\n".join(lines)


def render_scores(residential: List, investment: List) -> str:
    if not residential and not investment:
        return ""
    lines = ["**실거주 점수 분석**"]
    for dr in residential:
        lines.append(f"- {dr.label}: **{dr.score}점**")
        for sub in dr.evidence:
            lines.append(f"  - {sub}")
    lines += ["", "**투자성 점수 분석**"]
    for dr in investment:
        lines.append(f"- {dr.label}: **{dr.score}점**")
        for sub in dr.evidence:
            lines.append(f"  - {sub}")
    return "\n".join(lines)


def render_verdict(verdict: str) -> str:
    if not verdict:
        return ""
    return f"> 🔍 **오늘의 판단:** {verdict}"


def render_keypoints(key_points: List[str]) -> str:
    if not key_points:
        return ""
    lines = ["**주목할 점**"]
    lines.extend(f"- {kp}" for kp in key_points)
    return "\n".join(lines)


def format_macro_summary(macro_summary: str) -> List[str]:
    if not macro_summary:
        return ["데이터 없음"]
    items = [item.strip() for item in macro_summary.split("|") if item.strip()]
    return [f"- {item}" for item in items]


def format_stat_block(
    c: Dict,
    price_eok: float,
    change: float,
    trend,
    trend_area: float,
) -> List[str]:
    change_sign = "▲" if change > 0 else ("▼" if change < 0 else "―")
    change_str = f"{change_sign} {abs(change):.1f}%"

    lines = [
        f"💰 **거래** {c.get('recent_tx_count', 0)}건 · 평균 {price_eok:.1f}억 · 전월比 {change_str}",
        f"📍 **위치** {c.get('sigungu', '')} · {c.get('exclusive_area', 84):.0f}㎡ · {c.get('household_count', 0)}세대",
    ]

    if c.get("build_year"):
        lines.append(
            f"🏢 **건물** {c['build_year']}년 준공 · 용적률 {c.get('floor_area_ratio', '?')}% · 건폐율 {c.get('building_coverage_ratio', '?')}%"
        )

    commute = c.get("commute_transit_minutes")
    if commute is not None:
        lines.append(f"🚇 **출퇴근** {commute}분 (대중교통)")
    else:
        lines.append("🚇 **출퇴근** 미수집")

    poi = c.get("_poi")
    if poi:
        stations = poi.subway_stations[:2] if hasattr(poi, "subway_stations") else []
        if stations:
            s_str = " · ".join(f"{s.get('name', '?')} {s.get('walk_minutes', '?')}분" for s in stations)
            lines.append(f"🚉 **역세권** {s_str}")
        nuisance_h = getattr(poi, "nuisance_high_count", 0) or 0
        nuisance_m = getattr(poi, "nuisance_mid_count", 0) or 0
        if nuisance_h > 0:
            lines.append(f"⚠️ **혐오시설** 고강도 {nuisance_h}종 탐지")
        elif nuisance_m > 0:
            lines.append(f"⚠️ **혐오시설** 중강도 {nuisance_m}종 탐지")
        lines.append(
            f"🏫 **편의시설** 학교 {poi.schools_count}개 · 학원 {poi.academies_count}개 · 마트 {poi.marts_count}개"
        )

    if trend:
        lines.append(
            f"📊 **시세추세** ({trend_area:.0f}㎡) 평균 {trend.avg_price / 10000:.0f}만원 · "
            f"{trend.price_change_pct:+.1f}% · 월 {trend.monthly_volume:.1f}건"
        )

    return lines


def format_dimension_scores(c: Dict) -> List[str]:
    """LocationScore.residential_results / investment_results를 제네릭하게 렌더링."""
    ls = c.get("_location_score")
    if not ls:
        return []

    lines = ["**실거주 점수 분석**"]
    for dr in ls.residential_results:
        lines.append(f"- {dr.label}: **{dr.score}점**")
        for sub in dr.evidence:
            lines.append(f"  - {sub}")

    lines += ["", "**투자성 점수 분석**"]
    for dr in ls.investment_results:
        lines.append(f"- {dr.label}: **{dr.score}점**")
        for sub in dr.evidence:
            lines.append(f"  - {sub}")

    return lines


def build_markdown(
    date_str: str,
    date_range: str,
    macro_summary: str,
    market_summary: str,
    candidates: List[Dict],
    insights_map: Dict[str, Dict],
) -> str:
    lines = [
        f"# 데일리 부동산 브리핑 — {date_str}",
        "",
        f"**분석 기간:** {date_range} | **주목 단지:** {len(candidates)}개",
        "",
        "---",
        "",
        "## 거시경제 현황",
        *format_macro_summary(macro_summary),
        "",
        "---",
        "",
        "## 오늘의 시장 신호",
        market_summary or "분석 데이터 부족",
        "",
        "---",
        "",
        "## 주목 단지 분석",
        "",
    ]

    for i, c in enumerate(candidates, 1):
        name = c.get("apt_name", "?")
        score_pct = int(c.get("composite_score", 0) * 100)
        price_eok = c.get("avg_recent_price", 0) / 100_000_000
        change = c.get("price_change_pct", 0)
        trend = c.get("_trend")
        trend_area = c.get("_trend_area_sqm", 84)

        stat_block = format_stat_block(c, price_eok, change, trend, trend_area)

        lines += [
            f"### {i}. {name} — composite {score_pct}점",
            "",
            "<!-- stats -->",
            *stat_block,
            "<!-- /stats -->",
        ]

        ins = insights_map.get(name, {})
        if ins:
            lines.append("")

            trading = ins.get("trading_bullets", [])
            if trading:
                lines.append("**거래 동향**")
                lines.extend(f"- {b}" for b in trading)

            chars = ins.get("characteristics_bullets", [])
            if chars:
                lines.append("")
                lines.append("**단지 특징**")
                lines.extend(f"- {b}" for b in chars)

            dim_lines = format_dimension_scores(c)
            if dim_lines:
                lines.append("")
                lines.extend(dim_lines)

            strategy = ins.get("strategy_bullets", [])
            if strategy:
                lines.append("")
                lines.append("**전략 제안**")
                lines.extend(f"- {b}" for b in strategy)

        lines += ["", "---", ""]

    return "\n".join(lines)
