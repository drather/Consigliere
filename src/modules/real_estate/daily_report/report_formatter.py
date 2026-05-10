"""
report_formatter — DimensionResult 기반 제네릭 출력 계층.
차원 ID를 하드코딩하지 않는다. 모든 레이블·근거는 DimensionResult에서 온다.
"""
from typing import Dict, List, Optional


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
