# Result: 사용자 페르소나 기반 액션 플랜 제공

## 개요
부동산 시황 정보를 사용자의 개인적 상황과 결합하여, 실질적인 의사결정을 돕는 맞춤형 가이드라인 생성 기능을 성공적으로 구축했습니다.

## 주요 성과
- **페르소나 주입:** 소득, 자산, 직장 위치 등의 개인 정보를 리포트 생성 로직에 통합.
- **전략적 액션 플랜:** 단순 정보 전달이 아닌, 자금조달계획을 포함한 2~3가지 실행 안 제안.
- **금융 지식 대중화:** 어려운 금융 용어를 초보자 눈높이에서 자동 설명.

## 결과물 리스트
- **데이터:** `src/modules/real_estate/persona.yaml`
- **로직:** `src/modules/real_estate/service.py` (`generate_insight_report` 확장)
- **프롬프트:** `src/modules/real_estate/prompts/insight_parser.md`

## 검증 로그
(상세 내용은 Walkthrough 참조)
- 페르소나 정보 로드 성공
- 상황별 맞춤형 섹션(Action Plan) 생성 성공
- 금융 용어 해설 섹션 자동 포함 확인
