"""
ApartmentMasterService — 전수 구축(build_initial) + 온디맨드 조회(get_or_fetch).
"""
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from modules.real_estate.models import ApartmentMaster
from .client import ApartmentMasterClient
from .repository import ApartmentMasterRepository

logger = logging.getLogger(__name__)


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

    def build_initial(self, districts: List[Dict]) -> Dict[str, int]:
        """수도권 전체 지구 전수 구축. 이미 저장된 단지(complex_code 기준)는 스킵.

        Args:
            districts: config.yaml districts 목록 [{"code": "11680", "name": "강남구"}, ...]
        Returns:
            {"total": N, "saved": M, "skipped": K, "errors": E}
        """
        existing_codes = set(self.repository.get_all_complex_codes())
        total = saved = skipped = errors = 0

        for district in districts:
            sigungu_cd = district.get("code", "")
            name = district.get("name", sigungu_cd)
            complexes = self.client.fetch_complex_list(sigungu_cd)
            time.sleep(self.rate_limit_sec)

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
                    continue

                master = self._parse_info(kapt_name, sigungu_cd, kapt_code, info)
                try:
                    self.repository.save(master)
                    existing_codes.add(kapt_code)
                    saved += 1
                    logger.debug(f"[AptMaster] 저장: {kapt_name}({kapt_code}) — {master.household_count}세대")
                except Exception as e:
                    logger.error(f"[AptMaster] 저장 실패 {kapt_name}: {e}")
                    errors += 1

            logger.info(f"[AptMaster] {name}({sigungu_cd}) 완료: {len(complexes)}개 단지")

        logger.info(f"[AptMaster] build_initial 완료: total={total}, saved={saved}, skipped={skipped}, errors={errors}")
        return {"total": total, "saved": saved, "skipped": skipped, "errors": errors}

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
        kapt_code = self._match_name(apt_name, candidates)
        if not kapt_code:
            logger.debug(f"[AptMaster] 매칭 실패: {apt_name} in {district_code}")
            return None

        info = self.client.fetch_complex_info(kapt_code)
        if not info:
            return None

        master = self._parse_info(apt_name, district_code, kapt_code, info)
        try:
            self.repository.save(master)
        except Exception as e:
            logger.error(f"[AptMaster] 온디맨드 저장 실패 {apt_name}: {e}")
        return master

    def _match_name(self, apt_name: str, candidates: List[Dict]) -> Optional[str]:
        """apt_name ↔ kaptName 매칭: 완전일치 → 부분일치(포함관계).

        Returns: kaptCode or None
        """
        # 완전 일치
        for c in candidates:
            if c.get("kaptName", "") == apt_name:
                return c["kaptCode"]
        # 부분 일치 (한쪽이 다른 쪽을 포함)
        for c in candidates:
            k_name = c.get("kaptName", "")
            if apt_name in k_name or k_name in apt_name:
                return c["kaptCode"]
        return None

    @staticmethod
    def _parse_info(apt_name: str, district_code: str, kapt_code: str, info: Dict) -> ApartmentMaster:
        """API 응답 dict → ApartmentMaster."""
        def _int(val) -> int:
            try:
                return int(str(val).replace(",", "").strip())
            except (ValueError, TypeError):
                return 0

        return ApartmentMaster(
            apt_name=apt_name,
            district_code=district_code,
            complex_code=kapt_code,
            household_count=_int(info.get("hhldCnt", 0)),
            building_count=_int(info.get("bdNum", 0)),
            parking_count=_int(info.get("kaptTarea", 0)),
            constructor=str(info.get("kaptBcompany", "") or ""),
            approved_date=str(info.get("useAprDay", "") or ""),
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
