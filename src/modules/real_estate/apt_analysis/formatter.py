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
    lines.append(report.llm_insight[:500] + ("..." if len(report.llm_insight) > 500 else ""))
    return "\n".join(lines)


def format_markdown(report: AptAnalysisReport) -> str:
    lines = [
        f"# {report.apt_name} 심층 분석",
        f"**분석일시:** {report.generated_at[:10]}",
        "",
        "## 실거래가 히스토리",
    ]
    for p in report.price_history[:20]:
        lines.append(f"- {p['date']}: {p['price']:,}원 ({p['area']}㎡)")

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
        lines.append(f"- 기준금리: {macro['base_rate'].get('value', '-')}%")
    if macro.get("loan_rate"):
        lines.append(f"- 주담대금리: {macro['loan_rate'].get('value', '-')}%")

    lines += ["", "## AI 종합 분석", report.llm_insight]
    return "\n".join(lines)
