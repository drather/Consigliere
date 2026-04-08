# Spec: Career 커뮤니티 소스 분류 config화

**Feature:** `career-community-source-config`
**Branch:** `feature/career-community-source-config`
**작성일:** 2026-04-08

---

## 목표

`service.py`의 `_REDDIT_SOURCES`, `_MASTODON_SOURCES`, `_KOREAN_SOURCES` 하드코딩을 제거하고,
`config.yaml`의 `category` 필드 기반으로 동적 분류하도록 변경한다.

## 문제

새 커뮤니티 소스 추가 시 아래 3곳을 수정해야 함 (OCP 위반):
1. `collectors/<new>.py` 구현
2. `factory.py`에 Collector 추가
3. `service.py`의 `_REDDIT_SOURCES` / `_MASTODON_SOURCES` / `_KOREAN_SOURCES` 중 해당 집합에 키 추가

## 변경 범위

| 파일 | 변경 내용 |
|------|-----------|
| `config.yaml` | 각 community_source에 `category` 필드 추가 |
| `config.py` | `get_community_source_categories()` 메서드 추가 |
| `service.py` | frozenset 3개 제거 → config 기반 동적 분류 |
| `factory.py` | 주석에서 `_*_SOURCES` 수정 안내 문구 제거 |

## 변경 후 구조

```yaml
# config.yaml
community_sources:
  reddit:
    category: reddit
    ...
  mastodon:
    category: mastodon
    ...
  clien:
    category: korean
    ...
  dcinside:
    category: korean
    ...
```

```python
# service.py — 카테고리별 모델 매핑만 유지 (새 카테고리 추가 시에만 변경)
_CATEGORY_MODEL = {
    "reddit": RedditPost,
    "mastodon": NitterTweet,
    "korean": KoreanPost,
}
```

## 효과

새 소스 추가 시 수정 파일: `collectors/<new>.py` + `config.yaml` + `factory.py` (3곳)
→ `service.py` 무수정 (기존 카테고리에 속하는 경우)
