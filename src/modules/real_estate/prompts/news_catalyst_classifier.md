---
task_type: REAL_ESTATE_ANALYSIS
output_format: json
---

아래 뉴스 기사 목록에서 주어진 단지/지역과 관련된 호재(positive) 또는 악재(negative) 정보를 추출하세요.

[분석 대상]
단지명: {{apt_name}}
지역: {{sigungu}}

[뉴스 기사]
{{news_list}}

---

JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

```json
{
  "catalysts": [
    {
      "type": "positive",
      "title": "관련 기사 제목 (30자 이내로 요약)",
      "date": "YYYY-MM-DD"
    }
  ]
}
```

규칙:
- 단지명 또는 지역과 직접 관련된 기사만 포함하세요.
- 관련 없는 기사는 제외하세요.
- type은 반드시 "positive" 또는 "negative" 중 하나여야 합니다.
- 호재 예시: GTX 개통, 재개발 확정, 대형 쇼핑몰 입점, 학교 신설
- 악재 예시: 공급 과잉, 재건축 불허, 혐오시설 입주, 규제 강화
- catalysts가 없으면 빈 배열 []을 반환하세요.
