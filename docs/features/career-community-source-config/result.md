# Result: Career 커뮤니티 소스 분류 config화

**완료일:** 2026-04-08

## 변경 내용

`config.yaml` — 각 community_source에 `category` 필드 추가
- reddit: `category: reddit`
- mastodon: `category: mastodon`
- clien, dcinside: `category: korean`

`config.py` — `get_community_source_categories()` 추가
- `{source_key: category}` dict 반환

`service.py`
- `_REDDIT_SOURCES`, `_MASTODON_SOURCES`, `_KOREAN_SOURCES` frozenset 3개 제거
- `_CATEGORY_MODEL` dict + `defaultdict` 기반 동적 분류로 교체
- `defaultdict` import 추가

`factory.py` — 주석에서 `service.py _*_SOURCES` 수정 안내 문구 제거

## 검증

- 179 passed (신규 테스트 2개 포함, pre-existing 1개 실패 무변화)

## 효과

새 소스 추가 시 수정 파일: `collectors/<new>.py` + `config.yaml` + `factory.py`
→ **service.py 무수정** (기존 카테고리에 속하는 경우)
