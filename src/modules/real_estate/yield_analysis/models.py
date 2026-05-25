from dataclasses import dataclass


@dataclass
class YieldResult:
    jeonse_rate: float      # 전세가율 0~1
    jeonse_avg: int         # 평균 전세가(만원)
    gap_cost: int           # 갭투자 비용(만원) = 매매가 - 전세가
    monthly_cost: int       # 월 보유비용(만원) = 원리금 + 관리비 15만원
    jeonse_sample: int      # 표본 건수
