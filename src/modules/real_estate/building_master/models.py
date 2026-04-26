from dataclasses import dataclass
from typing import Optional


@dataclass
class BuildingMaster:
    mgm_pk: str                              # 관리건축물대장PK (22자리)
    building_name: str                       # 건물명
    sigungu_code: str                        # 시군구코드 5자리 (API 요청 코드)
    bjdong_code: str = ""                    # 법정동코드 5자리 (API 응답)
    parcel_pnu: str = ""                     # sigungu_code + bjdong_code = 10자리
    road_address: Optional[str] = None      # 도로명주소
    jibun_address: Optional[str] = None     # 지번주소
    completion_year: Optional[int] = None   # 준공연도
    total_units: Optional[int] = None       # 세대수
    total_buildings: Optional[int] = None   # 동수
    floor_area_ratio: Optional[float] = None    # 용적률
    building_coverage_ratio: Optional[float] = None  # 건폐율
    collected_at: str = ""
