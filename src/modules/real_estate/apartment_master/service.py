"""
ApartmentMasterService — 전수 구축(build_initial) + 온디맨드 조회(get_or_fetch).
"""
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from modules.real_estate.models import ApartmentMaster
from .client import ApartmentMasterClient
from .repository import ApartmentMasterRepository

logger = logging.getLogger(__name__)

_PROGRESS_LOG_INTERVAL = 50  # N건마다 진행상황 파일 갱신 + 로그 출력


class ApartmentMasterService:
    def __init__(
        self,
        client: ApartmentMasterClient,
        repository: ApartmentMasterRepository,
        rate_limit_sec: float = 0.3,
    ):
        self.client = client
        self.repository = repository
        self.rate_limit_sec = rate_limit_sec

    # ── Public API ─────────────────────────────────────────────────────────────

    def build_initial(
        self,
        districts: List[Dict],
        progress_path: Optional[str] = None,
    ) -> Dict[str, int]:
        """수도권 전체 지구 전수 구축. 이미 저장된 단지(complex_code 기준)는 스킵.

        중단 후 재시작 시 DB에 저장된 complex_code를 기준으로 자동 이어받기.
        progress_path 지정 시 진행상황을 JSON 파일로 실시간 기록.

        Args:
            districts: 대상 지구 목록 [{"code": "11680", "name": "강남구"}, ...]
            progress_path: 진행상황 JSON 파일 경로 (None 이면 파일 미기록)
        Returns:
            {"total": N, "saved": M, "skipped": K, "errors": E}
        """
        existing_codes = set(self.repository.get_all_complex_codes())
        total = saved = skipped = errors = 0
        started_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"[AptMaster] build_initial 시작 — 대상 {len(districts)}개 지구, "
            f"기존 저장 {len(existing_codes)}건 스킵 예정"
        )

        for district_idx, district in enumerate(districts, 1):
            sigungu_cd = district.get("code", "")
            name = district.get("name", sigungu_cd)
            complexes = self.client.fetch_complex_list(sigungu_cd)

            district_saved = district_errors = 0
            for item in complexes:
                kapt_code = item.get("kaptCode", "")
                kapt_name = item.get("kaptName", "")
                total += 1

                if kapt_code in existing_codes:
                    skipped += 1
                    continue

                info = self.client.fetch_complex_info(kapt_code)
                time.sleep(self.rate_limit_sec)

                if not info:
                    errors += 1
                    district_errors += 1
                    continue

                master = self._parse_info(kapt_name, sigungu_cd, kapt_code, info, list_item=item)
                try:
                    self.repository.save(master)
                    existing_codes.add(kapt_code)
                    saved += 1
                    district_saved += 1
                except Exception as e:
                    logger.error(f"[AptMaster] 저장 실패 {kapt_name}: {e}")
                    errors += 1
                    district_errors += 1

                # N건마다 진행상황 갱신
                if progress_path and saved % _PROGRESS_LOG_INTERVAL == 0:
                    self._write_progress(
                        progress_path, started_at, len(districts), district_idx,
                        name, total, saved, skipped, errors,
                    )
                    logger.info(
                        f"[AptMaster] 진행: {saved}건 저장 / {skipped}건 스킵 / "
                        f"{errors}건 오류 ({district_idx}/{len(districts)} 지구)"
                    )

            logger.info(
                f"[AptMaster] [{district_idx}/{len(districts)}] {name}({sigungu_cd}) 완료 "
                f"— 단지 {len(complexes)}개, 저장 {district_saved}개, 오류 {district_errors}개"
            )

        stats = {"total": total, "saved": saved, "skipped": skipped, "errors": errors}

        if progress_path:
            self._write_progress(
                progress_path, started_at, len(districts), len(districts),
                "완료", total, saved, skipped, errors, done=True,
            )

        logger.info(
            f"[AptMaster] build_initial 완료 — "
            f"total={total}, saved={saved}, skipped={skipped}, errors={errors}"
        )
        return stats

    def get_or_fetch(self, apt_name: str, district_code: str) -> Optional[ApartmentMaster]:
        """SQLite 조회 → 없으면 API 조회 후 저장.

        Args:
            apt_name: 실거래가 데이터의 아파트명
            district_code: 5자리 시군구코드
        """
        cached = self.repository.get(apt_name, district_code)
        if cached is not None:
            return cached

        return self._fetch_and_cache(apt_name, district_code)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _fetch_and_cache(self, apt_name: str, district_code: str) -> Optional[ApartmentMaster]:
        """API 호출 → 이름 매칭 → 기본정보 조회 → 저장."""
        candidates = self.client.fetch_complex_list(district_code)
        kapt_code, matched_item = self._match_name_with_item(apt_name, candidates)
        if not kapt_code:
            logger.debug(f"[AptMaster] 매칭 실패: {apt_name} in {district_code}")
            return None

        info = self.client.fetch_complex_info(kapt_code)
        if not info:
            return None

        master = self._parse_info(apt_name, district_code, kapt_code, info, list_item=matched_item)
        try:
            self.repository.save(master)
        except Exception as e:
            logger.error(f"[AptMaster] 온디맨드 저장 실패 {apt_name}: {e}")
        return master

    def _match_name(self, apt_name: str, candidates: List[Dict]) -> Optional[str]:
        """apt_name ↔ kaptName 매칭. Returns: kaptCode or None."""
        code, _ = self._match_name_with_item(apt_name, candidates)
        return code

    def _match_name_with_item(self, apt_name: str, candidates: List[Dict]):
        """apt_name ↔ kaptName 매칭: 완전일치 → 부분일치(포함관계).

        Returns: (kaptCode, matched_item) or (None, None)
        """
        for c in candidates:
            if c.get("kaptName", "") == apt_name:
                return c["kaptCode"], c
        for c in candidates:
            k_name = c.get("kaptName", "")
            if apt_name in k_name or k_name in apt_name:
                return c["kaptCode"], c
        return None, None

    @staticmethod
    def _parse_info(
        apt_name: str,
        district_code: str,
        kapt_code: str,
        info: Dict,
        list_item: Optional[Dict] = None,
    ) -> ApartmentMaster:
        """API 응답 dict → ApartmentMaster.

        Args:
            info:      API 2 (getAphusBassInfoV4) 응답
            list_item: API 1 (getTotalAptList3) 단지 항목 — as1~as4 시도/시군구/읍면동/리
        """
        def _int(val) -> int:
            try:
                return int(float(str(val).replace(",", "").strip()))
            except (ValueError, TypeError):
                return 0

        def _float(val) -> float:
            try:
                return float(str(val).replace(",", "").strip())
            except (ValueError, TypeError):
                return 0.0

        def _str(val) -> str:
            return str(val or "").strip()

        return ApartmentMaster(
            apt_name=apt_name,
            district_code=district_code,
            complex_code=kapt_code,
            # 기본 정보
            household_count=_int(info.get("hoCnt", 0)),
            building_count=_int(info.get("kaptDongCnt", 0)),
            parking_count=0,           # API 미제공
            constructor=_str(info.get("kaptBcompany")),
            approved_date=_str(info.get("kaptUsedate")),
            # 주소
            road_address=_str(info.get("doroJuso")),
            legal_address=_str(info.get("kaptAddr")),
            # 건물 구조
            top_floor=_int(info.get("kaptTopFloor", 0)),
            base_floor=_int(info.get("kaptBaseFloor", 0)),
            total_area=_float(info.get("kaptTarea", 0)),
            # 단지 특성
            heat_type=_str(info.get("codeHeatNm")),
            developer=_str(info.get("kaptAcompany")),
            elevator_count=_int(info.get("kaptdEcntp", 0)),
            # 전용면적별 세대수
            units_60=_int(info.get("kaptMparea60", 0)),
            units_85=_int(info.get("kaptMparea85", 0)),
            units_135=_int(info.get("kaptMparea135", 0)),
            units_136_plus=_int(info.get("kaptMparea136", 0)),
            # 행정구역 (API 1 목록 항목에서 추출)
            sido=_str((list_item or {}).get("as1")),
            sigungu=_str((list_item or {}).get("as2")),
            eupmyeondong=_str((list_item or {}).get("as3")),
            ri=_str((list_item or {}).get("as4")),
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _write_progress(
        path: str,
        started_at: str,
        total_districts: int,
        current_district_idx: int,
        current_district_name: str,
        total: int,
        saved: int,
        skipped: int,
        errors: int,
        done: bool = False,
    ) -> None:
        """진행상황을 JSON 파일로 기록."""
        try:
            data = {
                "status": "done" if done else "running",
                "started_at": started_at,
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "districts": {
                    "total": total_districts,
                    "current_index": current_district_idx,
                    "current_name": current_district_name,
                },
                "complexes": {
                    "total_seen": total,
                    "saved": saved,
                    "skipped_existing": skipped,
                    "errors": errors,
                },
                "resume_note": (
                    "재시작 시 DB에 저장된 단지를 자동으로 스킵합니다. "
                    "같은 스크립트를 그대로 재실행하세요."
                ),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[AptMaster] 진행상황 파일 기록 실패: {e}")
