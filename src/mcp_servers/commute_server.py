"""
commute_server.py — T-map 출퇴근 시간 MCP 서버.
CommuteService를 Claude Code 대화 세션에서 도구로 노출한다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

import yaml
from mcp.server.fastmcp import FastMCP
from modules.real_estate.commute.tmap_client import TmapClient
from modules.real_estate.commute.commute_repository import CommuteRepository
from modules.real_estate.commute.commute_service import CommuteService
from modules.real_estate.geocoder import GeocoderService

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "modules", "real_estate", "config.yaml")

with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f) or {}

_commute_cfg = _cfg.get("commute", {
    "destination": "삼성역",
    "destination_lat": 37.5088,
    "destination_lng": 127.0633,
    "cache_ttl_days": 90,
})
_commute_db = os.path.join(
    os.path.dirname(__file__), "..", "..", _cfg.get("commute_cache_db_path", "data/commute_cache.db")
)

os.makedirs(os.path.dirname(_commute_db), exist_ok=True)

_commute_service = CommuteService(
    repo=CommuteRepository(db_path=_commute_db, ttl_days=int(_commute_cfg.get("cache_ttl_days", 90))),
    tmap_client=TmapClient(api_key=os.getenv("TMAP_API_KEY", "")),
    geocoder=GeocoderService(api_key=os.getenv("KAKAO_API_KEY", "")),
    config=_commute_cfg,
)

mcp = FastMCP("commute")


@mcp.tool()
def get_commute_time(
    address: str,
    apt_name: str,
    district_code: str,
    mode: str = "transit",
) -> dict:
    """
    아파트 도로명주소 → 삼성역 출퇴근 시간 조회 (캐시 우선).

    Args:
        address: 도로명주소 (예: "서울 송파구 가락동 124")
        apt_name: 아파트 단지명 (예: "송파파크데일1단지")
        district_code: 지역코드 5자리 (예: "11710")
        mode: "transit"(대중교통), "car"(자차), "walking"(도보) 중 하나

    Returns:
        {"duration_minutes": int, "destination": str, "mode": str, "cached": bool}
        조회 실패 시 {"error": str}
    """
    origin_key = f"{district_code}__{apt_name}"
    result = _commute_service.get(
        origin_key=origin_key,
        road_address=address,
        apt_name=apt_name,
        district_code=district_code,
        mode=mode,
    )
    if result is None:
        return {"error": f"출퇴근 시간 조회 실패 — {apt_name} ({mode})"}
    return {
        "duration_minutes": result.duration_minutes,
        "destination": result.destination,
        "mode": result.mode,
        "cached": result.cached,
    }


@mcp.tool()
def get_all_commute_times(
    address: str,
    apt_name: str,
    district_code: str,
) -> dict:
    """
    대중교통·자차·도보 3가지 출퇴근 시간을 한번에 조회한다.

    Args:
        address: 도로명주소 (예: "서울 송파구 가락동 124")
        apt_name: 아파트 단지명
        district_code: 지역코드 5자리

    Returns:
        {"transit": int, "car": int, "walking": int} (분 단위, 조회 실패한 모드는 null)
    """
    origin_key = f"{district_code}__{apt_name}"
    results = _commute_service.get_all_modes(origin_key, address, apt_name, district_code)
    return {
        "transit": results["transit"].duration_minutes if "transit" in results else None,
        "car": results["car"].duration_minutes if "car" in results else None,
        "walking": results["walking"].duration_minutes if "walking" in results else None,
    }


if __name__ == "__main__":
    mcp.run()
