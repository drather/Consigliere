from datetime import date
from typing import Optional
from modules.career.models import CommunityTrendAnalysis, JobAnalysis, SkillGapAnalysis, TrendAnalysis


class DailyReporter:
    """
    분석 결과를 받아 일별 Markdown 리포트를 생성한다.
    LLM 호출 없이 코드 기반으로 조립한다.
    """

    def generate(
        self,
        report_date: date,
        job_analysis: JobAnalysis,
        trend_analysis: TrendAnalysis,
        skill_gap: SkillGapAnalysis,
        job_count_wanted: int,
        job_count_jumpit: int,
        community_trend: Optional[CommunityTrendAnalysis] = None,
    ) -> str:
        lines = [
            f"# 커리어 Daily Report — {report_date}",
            "",
            "## 💼 채용공고 요약",
            f"- **분석 건수:** Wanted {job_count_wanted}건 + 점핏 {job_count_jumpit}건",
        ]

        if job_analysis.top_skills:
            skill_freq = job_analysis.skill_frequency
            lines.append("- **핵심 요구 스킬:**")
            for s in job_analysis.top_skills[:8]:
                freq = skill_freq.get(s)
                lines.append(f"  - `{s}`" + (f" ({freq}건)" if freq else ""))

        salary = job_analysis.salary_range
        if salary.get("median"):
            median = salary["median"] // 10000 if salary["median"] > 10000 else salary["median"]
            p75 = salary.get("p75", 0)
            p75_str = f"{p75 // 10000}만" if p75 and p75 > 10000 else str(p75)
            p90 = salary.get("p90", 0)
            p90_str = f"{p90 // 10000}만" if p90 and p90 > 10000 else str(p90)
            lines.append(f"- **연봉:** 중앙값 {median}만 / 75%ile {p75_str} / 90%ile {p90_str}")

        if job_analysis.hiring_signal:
            lines.append(f"- **시장 시그널:** {job_analysis.hiring_signal}")

        if job_analysis.notable_postings:
            lines.append("- **주목할 포지션:**")
            for p in job_analysis.notable_postings[:3]:
                lines.append(
                    f"  - [{p.get('company')} — {p.get('position')}]({p.get('url')}) "
                    f"| {p.get('reason', '')}"
                )

        lines += [
            "",
            "## 🔥 기술 트렌드",
        ]

        if trend_analysis.hot_topics:
            lines.append("- **핫 토픽:**")
            for topic in trend_analysis.hot_topics:
                lines.append(f"  - `{topic}`")

        if trend_analysis.github_top:
            lines.append("- **GitHub 주목 레포:**")
            for r in trend_analysis.github_top[:3]:
                lines.append(
                    f"  - [{r.get('name')}]({r.get('url')}) ⭐{r.get('stars_today')} — {r.get('description', '')}"
                )

        if trend_analysis.hn_highlight:
            lines.append(f"- **HN 하이라이트:** {trend_analysis.hn_highlight}")

        if trend_analysis.devto_picks:
            lines.append("- **Dev.to 추천:**")
            for a in trend_analysis.devto_picks[:3]:
                lines.append(f"  - [{a.get('title')}]({a.get('url')})")

        if trend_analysis.backend_relevance_comment:
            comment_lines = [
                l.strip()
                for l in trend_analysis.backend_relevance_comment.split("\n")
                if l.strip()
            ]
            if len(comment_lines) <= 1:
                lines.append(f"- **백엔드 시사점:** {trend_analysis.backend_relevance_comment}")
            else:
                lines.append("- **백엔드 시사점:**")
                for cl in comment_lines:
                    lines.append(f"  - {cl}")

        lines += [
            "",
            "## 💰 연봉 인사이트",
        ]
        if salary.get("median"):
            lines.append(f"- 시장 중앙값 {median}만 / 75%ile {p75_str} / 90%ile {p90_str}")

        lines += [
            "",
            "## 🎯 스킬 갭 & 학습 추천",
            f"- **갭 점수:** {skill_gap.gap_score}/100"
            + (f" — {skill_gap.gap_trend}" if skill_gap.gap_trend else ""),
        ]

        if skill_gap.missing_skills:
            lines.append("- **핵심 부족 스킬:**")
            for s in skill_gap.missing_skills[:5]:
                urgency = s.get("urgency", "").upper()
                lines.append(f"  - `{s.get('skill')}` ({urgency})")

        if skill_gap.study_recommendations:
            lines.append("- **오늘의 학습 추천:**")
            for i, rec in enumerate(skill_gap.study_recommendations[:3], 1):
                lines.append(f"  {i}. **{rec.get('topic')}**")
                if rec.get("why"):
                    lines.append(f"     → {rec['why']}")
                if rec.get("resource"):
                    lines.append(f"     📚 {rec['resource']}")

        lines += self._build_community_section(community_trend)

        return "\n".join(lines)

    def _build_community_section(
        self, community_trend: Optional[CommunityTrendAnalysis]
    ) -> list:
        lines = ["", "## 🌐 커뮤니티 트렌드"]

        if community_trend is None:
            lines.append("- 커뮤니티 데이터 없음")
            return lines

        status = community_trend.collection_status
        failed = [s for s, v in status.items() if v == "failed"]
        partial = [s for s, v in status.items() if v == "partial"]

        if failed:
            lines.append(f"- ⚠️ **수집 실패 소스:** {', '.join(failed)}")
        if partial:
            lines.append(f"- ⚠️ **부분 수집 소스:** {', '.join(partial)}")

        if community_trend.hot_topics:
            lines.append("- **핫 토픽:**")
            for topic in community_trend.hot_topics:
                lines.append(f"  - `{topic}`")

        if community_trend.key_opinions:
            lines.append("- **커뮤니티 의견:**")
            for opinion in community_trend.key_opinions[:3]:
                lines.append(f"  - {opinion}")

        if community_trend.emerging_concerns:
            lines.append("- **떠오르는 우려사항:**")
            for concern in community_trend.emerging_concerns[:3]:
                lines.append(f"  - {concern}")

        if community_trend.community_summary:
            summary_lines = [l.strip() for l in community_trend.community_summary.split("\n") if l.strip()]
            if len(summary_lines) <= 1:
                lines.append(f"- **종합:** {community_trend.community_summary}")
            else:
                lines.append("- **종합:**")
                for sl in summary_lines:
                    lines.append(f"  - {sl}")

        return lines
