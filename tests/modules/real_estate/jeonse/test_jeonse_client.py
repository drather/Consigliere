# tests/modules/real_estate/jeonse/test_jeonse_client.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.jeonse.client import JeonseClient

# 국토부 RTMSDataSvcAptRent API 실제 응답 형식 (영문 태그)
_SAMPLE_XML = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<response>
  <header>
    <resultCode>000</resultCode>
    <resultMsg>OK</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <aptNm>대치르엘</aptNm>
        <dealYear>2026</dealYear>
        <dealMonth>5</dealMonth>
        <dealDay>16</dealDay>
        <deposit>10,000</deposit>
        <monthlyRent>360</monthlyRent>
        <excluUseAr>84.7735</excluUseAr>
        <floor>9</floor>
      </item>
      <item>
        <aptNm>디에이치아너힐즈</aptNm>
        <dealYear>2026</dealYear>
        <dealMonth>5</dealMonth>
        <dealDay>23</dealDay>
        <deposit>110,200</deposit>
        <monthlyRent>0</monthlyRent>
        <excluUseAr>59.7479</excluUseAr>
        <floor>16</floor>
      </item>
    </items>
    <numOfRows>10</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>2</totalCount>
  </body>
</response>"""


def test_parse_extracts_transactions_from_real_api_response():
    client = JeonseClient()
    results = client._parse(_SAMPLE_XML, district_code="11680")

    assert len(results) == 2

    monthly = results[0]
    assert monthly.apt_name == "대치르엘"
    assert monthly.district_code == "11680"
    assert monthly.deal_date == "2026-05-16"
    assert monthly.exclusive_area == 84.7735
    assert monthly.deposit == 10000
    assert monthly.monthly_rent == 360
    assert monthly.contract_type == "monthly"
    assert monthly.floor == 9

    jeonse = results[1]
    assert jeonse.apt_name == "디에이치아너힐즈"
    assert jeonse.deposit == 110200
    assert jeonse.monthly_rent == 0
    assert jeonse.contract_type == "jeonse"


def test_parse_returns_empty_list_for_no_items():
    client = JeonseClient()
    xml = """<?xml version="1.0" encoding="utf-8"?>
<response><body><items></items></body></response>"""
    assert client._parse(xml, district_code="11680") == []
