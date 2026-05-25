"""
report_formatter — DimensionResult 기반 제네릭 출력 계층.
차원 ID를 하드코딩하지 않는다. 모든 레이블·근거는 DimensionResult에서 온다.
"""
import itertools
from typing import Dict, List, Optional
from .report_types import TrendData, CommuteData, LocationSummaryData, CompData, YieldData, SupplyData


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
    route = commute["route_summary"]

    lines = [
        "**🚌 출퇴근**",
        "| 대중교통 | 자차 | 도보 |",
        "|:---:|:---:|:---:|",
        f"| {transit_str} | {car_str} | {walk_str} |",
    ]
    if route:
        lines.append(f"*{route}*")
    return "\n".join(lines)


def _school_label(transfer_rate: float, nearby: int) -> str:
    if transfer_rate >= 0.06 or nearby >= 3:
        return "학군 우수"
    elif transfer_rate >= 0.03 or nearby >= 1:
        return "학군 양호"
    else:
        return "학군 평이"


def render_location_summary(loc: LocationSummaryData) -> str:
    lines = ["**📍 입지 현황**", ""]

    # 역세권
    stations = loc.get("subway_stations", [])
    if stations:
        station_parts = [
            f"{s['name']}({s['line']}) 도보 {s['walk_minutes']}분"
            for s in stations
        ]
        lines.append(f"🚇 **역세권** {'  ·  '.join(station_parts)}")
    else:
        lines.append("🚇 **역세권** 역 없음")

    # 생활편의
    amenity_parts = []
    if loc.get("mart_count", 0) > 0:
        amenity_parts.append(f"마트 {loc['mart_count']}")
    if loc.get("convenience_count", 0) > 0:
        amenity_parts.append(f"편의점 {loc['convenience_count']}")
    if loc.get("cafe_count", 0) > 0:
        amenity_parts.append(f"카페 {loc['cafe_count']}")
    if loc.get("restaurant_count", 0) > 0:
        amenity_parts.append(f"식당 {loc['restaurant_count']}")
    if loc.get("pharmacy_count", 0) > 0:
        amenity_parts.append(f"약국 {loc['pharmacy_count']}")
    if amenity_parts:
        lines.append(f"🛒 **생활편의** {'  ·  '.join(amenity_parts)}")

    # 의료
    medical = loc.get("medical_count", 0)
    if medical > 0:
        lines.append(f"🏥 **의료** 병원·의원 {medical}곳")

    # 자연
    park_m = loc.get("park_nearest_m", 0)
    if park_m > 0:
        lines.append(f"🌳 **자연** 공원 {park_m}m 이내")
    else:
        lines.append("🌳 **자연** 반경 내 공원 없음")

    # 학군
    school_score = loc.get("school_score")
    if school_score is not None:
        nearby = loc.get("school_nearby_count", 0)
        transfer = loc.get("school_transfer_rate", 0.0)
        per_teacher = loc.get("school_avg_per_teacher", 0.0)
        label = loc.get("school_label", "")
        school_parts = [f"반경 1km 학교 {nearby}곳"]
        if transfer > 0:
            school_parts.append(f"전입률 {transfer * 100:.1f}%")
        if per_teacher > 0:
            school_parts.append(f"교사1인당 학생 {per_teacher:.0f}명")
        lines.append(f"🏫 **학군** {'  ·  '.join(school_parts)} → **{label}**")
    else:
        lines.append("🏫 **학군** 학교 정보 수집 전")

    # 혐오시설 (있을 때만 행 표시)
    high = loc.get("nuisance_high_count", 0)
    mid = loc.get("nuisance_mid_count", 0)
    if high > 0 or mid > 0:
        nuisance_parts = []
        if high > 0:
            nuisance_parts.append(f"고위험 {high}곳")
        if mid > 0:
            nuisance_parts.append(f"중위험 {mid}곳")
        lines.append(f"⚠️ **혐오시설** {'  ·  '.join(nuisance_parts)}")

    return "\n".join(lines)


def render_scores(residential: List, investment: List) -> str:
    if not residential and not investment:
        return ""
    lines = ["**실거주 점수 분석**"]
    for dr in residential:
        lines.append(f"- {dr.label}: **{dr.score}점**")
    lines += ["", "**투자성 점수 분석**"]
    for dr in investment:
        lines.append(f"- {dr.label}: **{dr.score}점**")
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


def _extract_trend(c: dict) -> TrendData:
    return TrendData(
        points=c.get("_recent_tx_points", []),
        avg_eok=round(c.get("avg_recent_price", 0) / 100_000_000, 2),
        change_pct=c.get("price_change_pct", 0.0),
        area_sqm=c.get("exclusive_area", 84.0),
    )


def _extract_commute(c: dict) -> CommuteData:
    return CommuteData(
        transit_minutes=c.get("commute_transit_minutes"),
        car_minutes=c.get("commute_car_minutes"),
        walk_minutes=c.get("commute_walk_minutes"),
        route_summary=c.get("_commute_route_summary", ""),
    )


def _extract_location_summary(c: dict) -> Optional[LocationSummaryData]:
    poi = c.get("_poi")
    if poi is None:
        return None

    # 역세권 — 도보 시간순 정렬, 최대 2개
    stations = sorted(poi.subway_stations, key=lambda s: s.get("walk_minutes", 99))[:2]
    subway = [
        {"name": s.get("name", "?"), "line": s.get("line", "?"), "walk_minutes": s.get("walk_minutes", 0)}
        for s in stations
    ]

    loc: LocationSummaryData = {
        "subway_stations": subway,
        "mart_count": poi.marts_count,
        "convenience_count": poi.convenience_count,
        "cafe_count": poi.cafe_count,
        "restaurant_count": poi.restaurant_count,
        "pharmacy_count": poi.pharmacy_count,
        "medical_count": poi.medical_count,
        "park_nearest_m": poi.park_nearest_m,
        "nuisance_high_count": poi.nuisance_high_count,
        "nuisance_mid_count": poi.nuisance_mid_count,
    }

    school_score = c.get("school_score")
    if school_score is not None:
        loc["school_nearby_count"] = c.get("school_nearby_count", 0)
        loc["school_transfer_rate"] = c.get("school_transfer_rate", 0.0)
        loc["school_avg_per_teacher"] = c.get("school_avg_per_teacher", 0.0)
        loc["school_score"] = school_score
        loc["school_label"] = _school_label(
            c.get("school_transfer_rate", 0.0),
            c.get("school_nearby_count", 0),
        )

    return loc


def _extract_comp(c: dict) -> "Optional[CompData]":
    if c.get("_comp_district_avg_per_sqm") is None:
        return None
    return CompData(
        district_avg_per_sqm=c["_comp_district_avg_per_sqm"],
        pct_vs_avg=c.get("_comp_pct_vs_avg", 0.0),
        similar_units=c.get("_comp_similar_units", []),
    )


def _extract_yield(c: dict) -> "Optional[YieldData]":
    if c.get("_yield_jeonse_rate") is None:
        return None
    return YieldData(
        jeonse_rate=c["_yield_jeonse_rate"],
        jeonse_avg=c.get("_yield_jeonse_avg", 0),
        gap_cost=c.get("_yield_gap_cost", 0),
        monthly_cost=c.get("_yield_monthly_cost", 0),
        jeonse_sample=c.get("_yield_jeonse_sample", 0),
    )


def _extract_supply(c: dict) -> "Optional[SupplyData]":
    if c.get("_supply_nearby_units") is None and not c.get("_news_catalysts"):
        return None
    return SupplyData(
        nearby_units=c.get("_supply_nearby_units", 0),
        supply_period=c.get("_supply_period", ""),
        news_catalysts=c.get("_news_catalysts", []),
    )


def render_price_comparison(comp: "Optional[CompData]") -> str:
    if not comp or not comp.get("district_avg_per_sqm"):
        return ""
    avg_man = comp["district_avg_per_sqm"] / 10000
    pct = comp["pct_vs_avg"]
    sign = "▲" if pct > 0 else "▼"
    color_word = "비쌈" if pct > 0 else "저렴"
    sign_pct = f"+{pct:.1f}%" if pct > 0 else f"{pct:.1f}%"
    lines = [f"**💹 가격 위치** — 구 평균 ㎡당 {avg_man:.0f}만원 대비 {sign} {sign_pct} {color_word}"]
    similars = comp.get("similar_units", [])
    if similars:
        parts = [f"{u['name']} {u['price_per_sqm']/10000:.0f}만" for u in similars[:3]]
        lines.append(f"유사 단지: {' · '.join(parts)}")
    return "  \n".join(lines)


def render_yield_analysis(yield_r: "Optional[YieldData]") -> str:
    if not yield_r or yield_r.get("jeonse_rate") is None:
        return ""
    rate_pct = yield_r["jeonse_rate"] * 100
    gap_eok = yield_r["gap_cost"] / 10000
    monthly = yield_r["monthly_cost"]
    sample = yield_r.get("jeonse_sample", 0)
    return (
        f"**🏠 수익 구조** — 전세가율 {rate_pct:.1f}% · "
        f"갭투자 {gap_eok:.1f}억 · 월 보유비용 {monthly}만원 "
        f"*(전세 {sample}건 기준)*"
    )


def render_supply_risk(supply: "Optional[SupplyData]") -> str:
    if not supply:
        return ""
    units = supply.get("nearby_units", 0)
    period = supply.get("supply_period", "")
    catalysts = supply.get("news_catalysts", [])

    lines = []
    if units > 0:
        lines.append(f"⚠️ **공급 리스크** — 반경 2km {units:,}세대 입주 예정 ({period})")
    else:
        lines.append("✅ **공급 리스크** — 반경 2km 공급 없음")

    for cat in catalysts[:3]:
        icon = "✅" if cat.get("type") == "positive" else "❌"
        lines.append(f"{icon} {cat.get('title', '')}")

    return "  \n".join(lines)


def _render_header(c: dict, index: int) -> str:
    name = c.get("apt_name", "?")
    score_pct = int(c.get("composite_score", 0) * 100)
    sigungu = c.get("sigungu", "")
    area = c.get("exclusive_area", 84)
    households = c.get("household_count", 0)
    return (
        f"### {index}. {name} — 종합 {score_pct}점\n\n"
        f"📍 {sigungu} · {area:.0f}㎡ · {households}세대"
    )


def build_candidate_card(c: dict, index: int = 0) -> str:
    trend = _extract_trend(c)
    commute = _extract_commute(c)
    location = _extract_location_summary(c)
    ls = c.get("_location_score")

    # New data extraction
    comp = _extract_comp(c)
    yield_r = _extract_yield(c)
    supply = _extract_supply(c)

    parts = [
        _render_header(c, index),
        render_price_comparison(comp),
        render_trend(trend),
        render_commute(commute),
        render_location_summary(location) if location else "",
        render_yield_analysis(yield_r),
        render_supply_risk(supply),
        render_scores(ls.residential_results, ls.investment_results) if ls else "",
        render_verdict(c.get("_verdict", "")),
        render_keypoints(c.get("_key_points", [])),
    ]
    return "\n\n".join(p for p in parts if p)


def build_markdown(
    date_str: str,
    date_range: str,
    macro_summary: str,
    market_summary: str,
    candidates: List[Dict],
    insights_map: Dict[str, Dict],  # API 호환성 유지 — Task 7에서 orchestrator가 _verdict/_key_points를 candidate dict에 직접 주입
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
        lines.append(build_candidate_card(c, index=i))
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _text_sparkline(points: List) -> str:
    if not points:
        return ""
    prices = [p["price_eok"] for p in points]
    p_min, p_max = min(prices), max(prices)
    if p_max == p_min:
        return "▄" * len(prices)
    return "".join(
        _SPARK_CHARS[int((p - p_min) / (p_max - p_min) * 7)]
        for p in prices
    )


def _slack_candidate_block(c: dict) -> str:
    trend = _extract_trend(c)
    commute = _extract_commute(c)

    name = c.get("apt_name", "?")
    score_pct = int(c.get("composite_score", 0) * 100)
    verdict = c.get("_verdict", "")
    key_points = c.get("_key_points", [])

    spark = _text_sparkline(trend["points"])
    avg = trend["avg_eok"]
    chg = trend["change_pct"]
    arrow = "▲" if chg > 0 else ("▼" if chg < 0 else "―")

    transit = commute["transit_minutes"]
    car = commute["car_minutes"]
    transit_str = f"🚌 {transit}분" if transit is not None else "🚌 조회불가"
    car_str = f" | 🚗 {car}분" if car is not None else ""

    lines = [
        f"*{name}* — 종합 {score_pct}점",
        f"💰 {avg:.1f}억 {arrow} {abs(chg):.1f}% {spark}",
        f"{transit_str}{car_str}",
    ]
    if verdict:
        lines.append(f"🔍 {verdict}")
    lines.extend(f"• {kp}" for kp in key_points[:3])
    return "\n".join(lines)


def build_slack(candidates: List[Dict]) -> str:
    blocks = [_slack_candidate_block(c) for c in candidates]
    return "\n\n---\n\n".join(blocks)
