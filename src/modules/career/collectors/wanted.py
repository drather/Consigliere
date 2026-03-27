import aiohttp
from typing import List, Dict, Any

from modules.career.collectors.base import BaseCollector
from modules.career.models import JobPosting


class WantedCollector(BaseCollector):
    """
    Wanted XHR API로 백엔드 채용공고를 수집한다.
    """
    def __init__(self, api_url: str, job_group_id: int, limit: int):
        super().__init__()
        self.api_url = api_url
        self.job_group_id = job_group_id
        self.limit = limit

    async def collect(self) -> List[JobPosting]:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.wanted.co.kr/",
        }
        params = {
            "job_group_id": self.job_group_id,
            "limit": self.limit,
            "offset": 0,
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(
                    self.api_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        self.logger.warning(f"Wanted API HTTP {resp.status}")
                        return []
                    try:
                        data = await resp.json()
                    except Exception as e:
                        self.logger.error(f"Wanted 응답 파싱 실패: {e}")
                        return []
            except Exception as e:
                self.logger.error(f"Wanted 수집 실패: {e}")
                return []

        postings = self._parse(data)
        self.logger.info(f"Wanted 수집 완료: {len(postings)}개")
        return postings

    def _parse(self, data: Dict[str, Any]) -> List[JobPosting]:
        postings = []
        for item in data.get("data", []):
            try:
                if not item:
                    continue
                job = item.get("job", item)
                if not job:
                    continue
                position = job.get("position", "")
                company = job.get("company", {}).get("name", "")
                job_id = str(job.get("id", ""))
                url = f"https://www.wanted.co.kr/wd/{job_id}"

                skills = [t.get("title", "") for t in job.get("tags", []) if t.get("title")]

                salary = job.get("salary", {}) or {}
                salary_min = salary.get("min")
                salary_max = salary.get("max")

                experience_min = job.get("experience_min")

                postings.append(JobPosting(
                    id=job_id,
                    company=company,
                    position=position,
                    skills=skills,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    experience_min=experience_min,
                    url=url,
                    source="wanted",
                ))
            except Exception as e:
                self.logger.debug(f"Wanted 공고 파싱 실패: {e}")
        return postings
