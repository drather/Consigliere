from .models import AptAnalysisReport


def format_slack(report: AptAnalysisReport) -> str:
    lines = [f"*🔬 {report.apt_name} 심층 분석* ({report.generated_at[:10]})"]
    lines.append("")

    if report.jeonse_ratio is not None:
        lines.append(f"• 전세가율: {report.jeonse_ratio:.1f}%")
    if report.supply_risk_summary:
        lines.append(f"• 공급리스크: {report.supply_risk_summary}")
    if report.location_score:
        res = report.location_score.get("residential_total", "-")
        inv = report.location_score.get("investment_total", "-")
        lines.append(f"• 입지점수: 실거주 {res}점 / 투자 {inv}점")
    if report.commute_summary:
        commute_str = " | ".join(f"{k}: {v}분" for k, v in report.commute_summary.items())
        lines.append(f"• 출퇴근: {commute_str}")

    lines.append("")
    lines.append("*AI 종합 분석*")
    insight = report.llm_insight or ""
    lines.append(insight[:500] + ("..." if len(insight) > 500 else ""))
    return "\n".join(lines)


def format_markdown(report: AptAnalysisReport) -> str:
    lines = [
        f"# {report.apt_name} 심층 분석",
        f"**분석일시:** {report.generated_at[:10]}",
        "",
        "## 실거래가 히스토리",
    ]
    for p in report.price_history[:20]:
        date = p.get("date", "-")
        price = p.get("price", 0)
        area = p.get("area", "-")
        lines.append(f"- {date}: {price:,}원 ({area}㎡)")

    lines += ["", "## 지표 요약"]
    if report.jeonse_ratio is not None:
        lines.append(f"- 전세가율: **{report.jeonse_ratio:.1f}%**")
    if report.supply_risk_summary:
        lines.append(f"- 공급리스크: {report.supply_risk_summary}")
    if report.location_score:
        res = report.location_score.get("residential_total", "-")
        inv = report.location_score.get("investment_total", "-")
        lines.append(f"- 입지점수: 실거주 {res}점 / 투자 {inv}점")
    if report.commute_summary:
        commute_str = " | ".join(f"{k}: {v}분" for k, v in report.commute_summary.items())
        lines.append(f"- 출퇴근(삼성역 기준): {commute_str}")

    macro = report.macro_snapshot
    if macro.get("base_rate"):
        rate_val = macro['base_rate'].get('value') or '-'
        lines.append(f"- 기준금리: {rate_val}%")
    if macro.get("loan_rate"):
        rate_val = macro['loan_rate'].get('value') or '-'
        lines.append(f"- 주담대금리: {rate_val}%")

    lines += ["", "## AI 종합 분석", report.llm_insight]
    return "\n".join(lines)
