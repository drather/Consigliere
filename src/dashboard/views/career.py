import requests
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _get(path: str, params: dict = None) -> Optional[Any]:
    try:
        r = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API 오류: {e}")
        return None


def _post(path: str, params: dict = None, json: dict = None) -> Optional[Any]:
    try:
        r = requests.post(f"{API_BASE_URL}{path}", params=params, json=json, timeout=120)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API 오류: {e}")
        return None


def show_career():
    st.title("🚀 커리어 Daily Report")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 리포트", "📈 스킬 갭 히스토리", "👤 페르소나 편집", "⚙️ 파이프라인"])

    # ── 탭 1: 리포트 뷰어 ────────────────────────────────────────────
    with tab1:
        st.subheader("일별 / 주간 / 월간 리포트")

        report_type = st.radio("리포트 종류", ["일별", "주간", "월간"], horizontal=True)

        if report_type == "일별":
            data = _get("/dashboard/career/reports/daily")
            dates = data.get("dates", []) if data else []
            if not dates:
                st.info("저장된 일별 리포트가 없습니다. 파이프라인을 실행하세요.")
            else:
                selected = st.selectbox("날짜 선택", sorted(dates, reverse=True))
                if selected:
                    report = _get(f"/dashboard/career/reports/daily/{selected}")
                    if report:
                        st.markdown(report.get("report", ""))

        elif report_type == "주간":
            data = _get("/dashboard/career/reports/weekly")
            weeks = data.get("weeks", []) if data else []
            if not weeks:
                st.info("저장된 주간 리포트가 없습니다.")
            else:
                selected = st.selectbox("주간 선택", sorted(weeks, reverse=True))
                # 주간 리포트는 파일 직접 읽기 (현재 GET 엔드포인트 없음 — 추후 추가 가능)
                st.info(f"선택: {selected} — 상세 조회는 추후 지원 예정")

        elif report_type == "월간":
            data = _get("/dashboard/career/reports/monthly")
            months = data.get("months", []) if data else []
            if not months:
                st.info("저장된 월간 리포트가 없습니다.")
            else:
                selected = st.selectbox("월 선택", sorted(months, reverse=True))
                st.info(f"선택: {selected} — 상세 조회는 추후 지원 예정")

    # ── 탭 2: 스킬 갭 히스토리 ──────────────────────────────────────
    with tab2:
        st.subheader("스킬 갭 점수 추이")
        weeks = st.slider("조회 기간 (주)", min_value=1, max_value=12, value=4)
        data = _get("/dashboard/career/skill-gap/history", params={"weeks": weeks})
        history = data.get("history", []) if data else []

        if not history:
            st.info("스킬 갭 히스토리가 없습니다. 리포트를 먼저 생성하세요.")
        else:
            df = pd.DataFrame(history)
            if "date" in df.columns and "gap_score" in df.columns:
                df = df.sort_values("date")
                st.line_chart(df.set_index("date")["gap_score"])
                st.dataframe(df[["date", "gap_score", "missing_skills"]], use_container_width=True)

    # ── 탭 3: 페르소나 편집 ──────────────────────────────────────────
    with tab3:
        st.subheader("커리어 페르소나 편집")
        persona = _get("/dashboard/career/persona")
        if not persona:
            st.warning("페르소나 로드 실패")
        else:
            with st.form("persona_form"):
                user = persona.get("user", {})
                skills = persona.get("skills", {})
                learning = persona.get("learning", {})
                job_search = persona.get("job_search", {})

                st.markdown("#### 기본 정보")
                col1, col2 = st.columns(2)
                with col1:
                    exp_years = st.number_input("경력 (년)", value=user.get("experience_years", 3), min_value=0)
                    domain = st.text_input("직군", value=user.get("domain", ""))
                with col2:
                    goal = st.text_input("커리어 목표", value=user.get("career_goal", ""))
                    current_focus = st.text_input("현재 학습 포커스", value=learning.get("current_focus", ""))

                st.markdown("#### 보유 스킬 (쉼표로 구분)")
                current_skills = st.text_area(
                    "현재 스킬", value=", ".join(skills.get("current", []))
                )
                learning_skills = st.text_area(
                    "학습 중 스킬", value=", ".join(skills.get("learning", []))
                )
                target_skills = st.text_area(
                    "목표 스킬", value=", ".join(skills.get("target", []))
                )

                st.markdown("#### 구직 설정")
                active = st.checkbox("구직 활성화", value=job_search.get("active", False))
                min_salary = st.number_input(
                    "최소 희망 연봉 (원)", value=job_search.get("min_salary", 60000000), step=1000000
                )

                submitted = st.form_submit_button("저장")
                if submitted:
                    updates = {
                        "user": {**user, "experience_years": exp_years, "domain": domain, "career_goal": goal},
                        "skills": {
                            "current": [s.strip() for s in current_skills.split(",") if s.strip()],
                            "learning": [s.strip() for s in learning_skills.split(",") if s.strip()],
                            "target": [s.strip() for s in target_skills.split(",") if s.strip()],
                        },
                        "learning": {**learning, "current_focus": current_focus},
                        "job_search": {**job_search, "active": active, "min_salary": min_salary},
                    }
                    result = requests.patch(
                        f"{API_BASE_URL}/dashboard/career/persona",
                        json={"updates": updates},
                        timeout=10,
                    )
                    if result.status_code == 200:
                        st.success("페르소나 저장 완료!")
                    else:
                        st.error(f"저장 실패: {result.text}")

    # ── 탭 4: 파이프라인 실행 ────────────────────────────────────────
    with tab4:
        st.subheader("파이프라인 수동 실행")
        target_date = st.date_input("실행 날짜")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📥 채용공고 수집"):
                with st.spinner("수집 중..."):
                    res = _post("/jobs/career/fetch-jobs", params={"target_date": str(target_date)})
                if res:
                    st.success(f"Wanted + 점핏 {res.get('count')}건 수집 완료")

        with col2:
            if st.button("📡 트렌드 수집"):
                with st.spinner("수집 중..."):
                    res = _post("/jobs/career/fetch-trends", params={"target_date": str(target_date)})
                if res:
                    st.success(f"GitHub {res.get('repos')}개 / HN {res.get('stories')}개 / Dev.to {res.get('articles')}개")

        with col3:
            if st.button("🚀 전체 파이프라인 실행"):
                with st.spinner("분석 중... (1~2분 소요)"):
                    res = _post("/jobs/career/run-pipeline", params={"target_date": str(target_date)})
                if res:
                    st.success("파이프라인 완료!")
                    st.text_area("리포트 미리보기", res.get("report_preview", ""), height=300)

        st.divider()
        col4, col5 = st.columns(2)
        with col4:
            if st.button("📋 주간 리포트 생성"):
                with st.spinner("생성 중..."):
                    res = _post("/jobs/career/generate-weekly-report")
                if res:
                    st.success("주간 리포트 생성 완료")
        with col5:
            if st.button("📅 월간 리포트 생성"):
                with st.spinner("생성 중..."):
                    res = _post("/jobs/career/generate-monthly-report")
                if res:
                    st.success("월간 리포트 생성 완료")
