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
