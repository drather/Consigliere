import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.location.dimensions.transportation import TransportationDimension
from modules.real_estate.location.dimensions.education import EducationDimension
from modules.real_estate.location.dimensions.living_infra import LivingInfraDimension
from modules.real_estate.location.dimensions.medical import MedicalDimension
from modules.real_estate.location.dimensions.nature import NatureDimension

_TRANS_CFG = {"subway_close_min": 5, "commute_high_min": 20,
              "commute_medium_min": 35, "data_absent_neutral": 50}

# ── TransportationDimension ──────────────────────────────────
def test_transportation_high_score():
    dim = TransportationDimension(_TRANS_CFG)
    c = {"poi_stations": [{"walk_minutes": 3}], "commute_minutes": 15}
    assert dim.score(c) == 100

def test_transportation_low_score():
    dim = TransportationDimension(_TRANS_CFG)
    c = {"poi_stations": [{"walk_minutes": 15}], "commute_minutes": 45}
    assert dim.score(c) == 20

def test_transportation_neutral_when_no_data():
    dim = TransportationDimension(_TRANS_CFG)
    assert dim.score({}) == 50

def test_transportation_prefers_transit_minutes():
    dim = TransportationDimension(_TRANS_CFG)
    c = {"poi_stations": [{"walk_minutes": 3}],
         "commute_transit_minutes": 18, "commute_minutes": 40}
    # transit 18분 → HIGH (<=20), station 3분 → HIGH → average 100
    assert dim.score(c) == 100

# ── EducationDimension ───────────────────────────────────────
def test_education_passthrough_school_score():
    dim = EducationDimension({"data_absent_neutral": 50})
    assert dim.score({"school_score": 85}) == 85

def test_education_neutral_when_missing():
    dim = EducationDimension({"data_absent_neutral": 50})
    assert dim.score({}) == 50

# ── LivingInfraDimension ─────────────────────────────────────
def test_living_infra_high():
    dim = LivingInfraDimension({"high_count": 5, "medium_count": 2, "data_absent_neutral": 50})
    c = {"poi_convenience_count": 3, "poi_pharmacy_count": 2, "poi_marts_count": 1}
    assert dim.score(c) == 100  # total 6 >= 5

def test_living_infra_medium():
    dim = LivingInfraDimension({"high_count": 5, "medium_count": 2, "data_absent_neutral": 50})
    c = {"poi_convenience_count": 1, "poi_pharmacy_count": 1, "poi_marts_count": 1}
    assert dim.score(c) == 60  # total 3 >= 2

def test_living_infra_low():
    dim = LivingInfraDimension({"high_count": 5, "medium_count": 2, "data_absent_neutral": 50})
    c = {"poi_convenience_count": 0, "poi_pharmacy_count": 1, "poi_marts_count": 0}
    assert dim.score(c) == 20  # total 1 < 2

# ── MedicalDimension ─────────────────────────────────────────
def test_medical_high():
    dim = MedicalDimension({"high_count": 3, "medium_count": 1, "data_absent_neutral": 50})
    assert dim.score({"poi_medical_count": 5}) == 100

def test_medical_neutral_when_missing():
    dim = MedicalDimension({"high_count": 3, "medium_count": 1, "data_absent_neutral": 50})
    assert dim.score({}) == 50

# ── NatureDimension ──────────────────────────────────────────
def test_nature_high_close_park():
    dim = NatureDimension({"close_m": 300, "medium_m": 800, "data_absent_neutral": 50})
    assert dim.score({"poi_park_nearest_m": 200}) == 100

def test_nature_medium_park():
    dim = NatureDimension({"close_m": 300, "medium_m": 800, "data_absent_neutral": 50})
    assert dim.score({"poi_park_nearest_m": 500}) == 60

def test_nature_low_far_park():
    dim = NatureDimension({"close_m": 300, "medium_m": 800, "data_absent_neutral": 50})
    assert dim.score({"poi_park_nearest_m": 1200}) == 20

def test_nature_neutral_when_no_park():
    dim = NatureDimension({"close_m": 300, "medium_m": 800, "data_absent_neutral": 50})
    assert dim.score({"poi_park_nearest_m": 0}) == 50
    assert dim.score({}) == 50


from modules.real_estate.location.dimensions.commercial import CommercialDimension
from modules.real_estate.location.dimensions.price_potential import PricePotentialDimension
from modules.real_estate.location.dimensions.liquidity import LiquidityDimension
from modules.real_estate.location.dimensions.school_premium import SchoolPremiumDimension

# ── CommercialDimension ──────────────────────────────────────
def test_commercial_high():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 25, "poi_cafe_count": 10}
    # volume: 35>=30 → 100; diversity: restaurant(25>=3✅) cafe(10>=2✅) others(0) → 2/6*100=33
    # round(100*0.5 + 33*0.5) = round(66.5) = 67
    assert dim.score(c) == 67

def test_commercial_medium():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 8, "poi_cafe_count": 5}
    # volume: 13>=10 → 60; diversity: restaurant(8>=3✅) cafe(5>=2✅) → 2/6*100=33
    # round(60*0.5 + 33*0.5) = round(46.5) = 47
    assert dim.score(c) == 47

def test_commercial_low():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 3, "poi_cafe_count": 2}
    # volume: 5<10 → 20; diversity: restaurant(3>=3✅) cafe(2>=2✅) → 2/6*100=33
    # round(20*0.5 + 33*0.5) = round(26.5) = 27
    assert dim.score(c) == 27

def test_commercial_high_volume_all_diversity():
    cfg = {
        "high_count": 30, "medium_count": 10, "data_absent_neutral": 50,
        "diversity_min_count": {"restaurant": 3, "cafe": 2, "convenience": 1,
                                "pharmacy": 1, "medical": 1, "mart": 1},
    }
    dim = CommercialDimension(cfg)
    c = {
        "poi_restaurant_count": 45, "poi_cafe_count": 20,
        "poi_convenience_count": 5, "poi_pharmacy_count": 3,
        "poi_medical_count": 3, "poi_marts_count": 1,
    }
    # volume: 65>=30 → 100; diversity: 6/6 → 100
    assert dim.score(c) == 100

def test_commercial_high_volume_3_diversity():
    cfg = {
        "high_count": 30, "medium_count": 10, "data_absent_neutral": 50,
        "diversity_min_count": {"restaurant": 3, "cafe": 2, "convenience": 1,
                                "pharmacy": 1, "medical": 1, "mart": 1},
    }
    dim = CommercialDimension(cfg)
    c = {
        "poi_restaurant_count": 45, "poi_cafe_count": 20,
        "poi_convenience_count": 5,
        "poi_pharmacy_count": 0, "poi_medical_count": 0, "poi_marts_count": 0,
    }
    # volume: 65>=30 → 100; diversity: 3/6 → 50
    # round(100*0.5 + 50*0.5) = 75
    assert dim.score(c) == 75

def test_commercial_low_volume_all_diversity():
    cfg = {
        "high_count": 30, "medium_count": 10, "data_absent_neutral": 50,
        "diversity_min_count": {"restaurant": 3, "cafe": 2, "convenience": 1,
                                "pharmacy": 1, "medical": 1, "mart": 1},
    }
    dim = CommercialDimension(cfg)
    c = {
        "poi_restaurant_count": 3, "poi_cafe_count": 2,
        "poi_convenience_count": 1, "poi_pharmacy_count": 1,
        "poi_medical_count": 1, "poi_marts_count": 1,
    }
    # volume: 5<10 → 20; diversity: 6/6 → 100
    # round(20*0.5 + 100*0.5) = 60
    assert dim.score(c) == 60

def test_commercial_single_category_dominant():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 45, "poi_cafe_count": 20}
    # volume: 65>=30 → 100; diversity: restaurant(✅) cafe(✅) others(0) → 2/6=33
    # round(100*0.5 + 33*0.5) = 67
    assert dim.score(c) == 67

def test_commercial_diversity_boundary():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 3, "poi_cafe_count": 1}
    # restaurant(3>=3✅) cafe(1<2❌) → 1/6=17
    # volume: 4<10 → 20; round(20*0.5 + 17*0.5) = round(18.5) = 19
    assert dim.score(c) == 19

# ── PricePotentialDimension ──────────────────────────────────
_PP_CFG = {
    "recon_age_years": 30, "recon_far_max": 200,
    "recon_score_map": {"HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50},
    "data_absent_neutral": 50,
}

def test_price_potential_high_old_low_far():
    dim = PricePotentialDimension(_PP_CFG)
    c = {"build_year": 1990, "floor_area_ratio": 150}  # age 36 + FAR 150 → both conditions → HIGH
    assert dim.score(c) == 100

def test_price_potential_gtx_boosts_score():
    dim = PricePotentialDimension(_PP_CFG)
    c = {"reconstruction_potential": "LOW", "gtx_benefit": True}
    assert dim.score(c) == min(100, 20 + 30)  # 50

def test_price_potential_fallback_recon_map():
    dim = PricePotentialDimension(_PP_CFG)
    assert dim.score({"reconstruction_potential": "HIGH"}) == 100
    assert dim.score({"reconstruction_potential": "UNKNOWN"}) == 50

# ── LiquidityDimension ───────────────────────────────────────
def test_liquidity_high():
    dim = LiquidityDimension({"high_households": 500, "medium_households": 300, "data_absent_neutral": 50})
    assert dim.score({"household_count": 600}) == 100

def test_liquidity_neutral_when_missing():
    dim = LiquidityDimension({"high_households": 500, "medium_households": 300, "data_absent_neutral": 50})
    assert dim.score({}) == 50

# ── SchoolPremiumDimension ───────────────────────────────────
def test_school_premium_passthrough():
    dim = SchoolPremiumDimension({"data_absent_neutral": 50})
    assert dim.score({"school_score": 90}) == 90

def test_school_premium_neutral_when_missing():
    dim = SchoolPremiumDimension({"data_absent_neutral": 50})
    assert dim.score({}) == 50


from modules.real_estate.location.dimensions.nuisance import NuisanceDimension

_NUISANCE_CFG = {"high_score": 20, "mid_score": 60, "clean_score": 100, "data_absent_neutral": 50}

# ── NuisanceDimension ────────────────────────────────────────
def test_nuisance_clean():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({"poi_nuisance_high_count": 0, "poi_nuisance_mid_count": 0}) == 100

def test_nuisance_mid_only():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({"poi_nuisance_high_count": 0, "poi_nuisance_mid_count": 1}) == 60

def test_nuisance_high():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({"poi_nuisance_high_count": 1, "poi_nuisance_mid_count": 0}) == 20

def test_nuisance_high_dominates_mid():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({"poi_nuisance_high_count": 2, "poi_nuisance_mid_count": 1}) == 20

def test_nuisance_absent_data_returns_neutral():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({}) == 50


# ── BaseDimension 인터페이스 ──────────────────────────────────
from modules.real_estate.location.dimensions.transportation import TransportationDimension as _TD

def test_base_dimension_requires_label():
    """모든 구상 차원은 label 프로퍼티를 가져야 한다."""
    dim = _TD({"subway_close_min": 5, "commute_high_min": 20, "commute_medium_min": 35, "data_absent_neutral": 50})
    assert isinstance(dim.label, str)
    assert len(dim.label) > 0

def test_base_dimension_evidence_returns_list():
    """evidence()는 list[str]를 반환해야 한다."""
    dim = _TD({"subway_close_min": 5, "commute_high_min": 20, "commute_medium_min": 35, "data_absent_neutral": 50})
    result = dim.evidence({})
    assert isinstance(result, list)


# ── label/evidence 전수 테스트 ───────────────────────────────
from modules.real_estate.location.dimensions.education import EducationDimension
from modules.real_estate.location.dimensions.living_infra import LivingInfraDimension
from modules.real_estate.location.dimensions.medical import MedicalDimension
from modules.real_estate.location.dimensions.nature import NatureDimension
from modules.real_estate.location.dimensions.commercial import CommercialDimension
from modules.real_estate.location.dimensions.price_potential import PricePotentialDimension
from modules.real_estate.location.dimensions.liquidity import LiquidityDimension
from modules.real_estate.location.dimensions.school_premium import SchoolPremiumDimension
from modules.real_estate.location.dimensions.nuisance import NuisanceDimension

def test_transportation_label_and_evidence():
    dim = TransportationDimension(_TRANS_CFG)
    assert "교통" in dim.label
    ev = dim.evidence({"commute_transit_minutes": 25, "_commute_route_summary": "9호선 20분 → 도보 5분"})
    assert any("25분" in e for e in ev)
    assert any("9호선" in e for e in ev)

def test_transportation_evidence_with_poi():
    dim = TransportationDimension(_TRANS_CFG)
    mock_poi = type("P", (), {"subway_stations": [{"name": "강남역", "walk_minutes": 5}]})()
    ev = dim.evidence({"_poi": mock_poi})
    assert any("강남역" in e for e in ev)

def test_education_label_and_evidence():
    dim = EducationDimension({"data_absent_neutral": 50})
    assert "교육" in dim.label
    mock_poi = type("P", (), {"schools_count": 3, "academies_count": 20})()
    ev = dim.evidence({"_poi": mock_poi})
    assert any("3개" in e for e in ev)

def test_living_infra_label_and_evidence():
    dim = LivingInfraDimension({"high_count": 5, "medium_count": 2, "data_absent_neutral": 50})
    assert "생활" in dim.label or "인프라" in dim.label
    mock_poi = type("P", (), {"convenience_count": 5, "pharmacy_count": 3, "marts_count": 2})()
    ev = dim.evidence({"_poi": mock_poi})
    assert len(ev) >= 2

def test_medical_label_and_evidence():
    dim = MedicalDimension({"high_count": 3, "medium_count": 1, "data_absent_neutral": 50})
    assert "의료" in dim.label or "병원" in dim.label
    mock_poi = type("P", (), {"medical_count": 5})()
    ev = dim.evidence({"_poi": mock_poi})
    assert any("5" in e for e in ev)

def test_nature_label_and_evidence():
    dim = NatureDimension({"close_m": 300, "medium_m": 800, "data_absent_neutral": 50})
    assert "자연" in dim.label or "공원" in dim.label
    mock_poi = type("P", (), {"park_nearest_m": 250})()
    ev = dim.evidence({"_poi": mock_poi})
    assert any("250" in e for e in ev)

def test_commercial_label_and_evidence():
    cfg = {
        "high_count": 30, "medium_count": 10, "data_absent_neutral": 50,
        "diversity_min_count": {"restaurant": 3, "cafe": 2, "convenience": 1,
                                "pharmacy": 1, "medical": 1, "mart": 1},
    }
    dim = CommercialDimension(cfg)
    assert "상업" in dim.label or "상권" in dim.label
    ev = dim.evidence({
        "poi_restaurant_count": 20, "poi_cafe_count": 10,
        "poi_convenience_count": 5, "poi_pharmacy_count": 3,
        "poi_medical_count": 3, "poi_marts_count": 2,
    })
    assert any("6/6" in e for e in ev)

def test_price_potential_label_and_evidence():
    dim = PricePotentialDimension(_PP_CFG)
    assert "가격" in dim.label or "상승" in dim.label
    ev = dim.evidence({"price_change_pct": 3.5, "build_year": 1990})
    assert any("3.5" in e for e in ev)
    assert any("1990" in e for e in ev)

def test_liquidity_label_and_evidence():
    dim = LiquidityDimension({"high_households": 500, "medium_households": 300, "data_absent_neutral": 50})
    assert "환금" in dim.label or "유동" in dim.label
    ev = dim.evidence({"household_count": 1200, "recent_tx_count": 5})
    assert any("1,200" in e for e in ev)

def test_school_premium_label_and_evidence():
    dim = SchoolPremiumDimension({"data_absent_neutral": 50})
    assert "학군" in dim.label or "학교" in dim.label
    mock_poi = type("P", (), {"schools_count": 4, "academies_count": 30})()
    ev = dim.evidence({"_poi": mock_poi})
    assert any("4" in e for e in ev)

def test_nuisance_label_and_evidence_clean():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert "혐오" in dim.label
    ev = dim.evidence({"poi_nuisance_high_count": 0, "poi_nuisance_mid_count": 0})
    assert any("없음" in e for e in ev)

def test_nuisance_label_and_evidence_high():
    dim = NuisanceDimension(_NUISANCE_CFG)
    ev = dim.evidence({"poi_nuisance_high_count": 1, "poi_nuisance_mid_count": 0})
    assert any("고강도" in e for e in ev)

def test_nuisance_evidence_absent_data():
    dim = NuisanceDimension(_NUISANCE_CFG)
    ev = dim.evidence({})  # no poi_nuisance_high_count key
    assert any("미수집" in e for e in ev)
