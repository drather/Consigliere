from .models import AptAnalysisReport


def format_slack(report: AptAnalysisReport) -> str:
    return f"*{report.apt_name}* 심층 분석 완료"


def format_markdown(report: AptAnalysisReport) -> str:
    return f"# {report.apt_name}\n\n{report.llm_insight}"
