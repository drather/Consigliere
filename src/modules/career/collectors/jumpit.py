import aiohttp
from typing import List, Dict, Any

from modules.career.collectors.base import BaseCollector
from modules.career.models import JobPosting


class JumpitCollector(BaseCollector):
    """
    점핏 내부 API로 서버/백엔드 채용공고를 수집한다.
    """
    def __init__(self, api_url: str, job_category: int, limit: int):
        super().__init__()
        self.api_url = api_url
        self.job_category = job_category
        self.limit = limit

    async def collect(self) -> List[JobPosting]:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Origin": "https://www.jumpit.co.kr",
            "Referer": "https://www.jumpit.co.kr/",
        }
        params = {
            "jobCategory": self.job_category,
            "sort": "rsp_rate",
            "page": 1,
        }

        all_postings: List[JobPosting] = []
        page = 1

        async with aiohttp.ClientSession(headers=headers) as session:
            while len(all_postings) < self.limit:
                params["page"] = page
                try:
                    async with session.get(
                        self.api_url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as resp:
                        if resp.status != 200:
                            self.logger.warning(f"점핏 API HTTP {resp.status} (page={page})")
                            break
                        data = await resp.json()
                except Exception as e:
                    self.logger.error(f"점핏 수집 실패 (page={page}): {e}")
                    break

                items = data.get("result", {}).get("positions", [])
                if not items:
                    break

                all_postings.extend(self._parse(items))
                page += 1

                total = data.get("result", {}).get("totalCount", 0)
                if len(all_postings) >= total:
                    break

        self.logger.info(f"점핏 수집 완료: {len(all_postings)}개")
        return all_postings[: self.limit]

    def _parse(self, items: List[Dict[str, Any]]) -> List[JobPosting]:
        postings = []
        for item in items:
            try:
                job_id = str(item.get("id", ""))
                url = f"https://www.jumpit.co.kr/position/{job_id}"
                skills = item.get("techStacks", [])
                if isinstance(skills, list):
                    skills = [s if isinstance(s, str) else s.get("name", "") for s in skills]

                postings.append(JobPosting(
                    id=job_id,
                    company=item.get("companyName", ""),
                    position=item.get("title", ""),
                    skills=skills,
                    salary_min=None,
                    salary_max=None,
                    experience_min=item.get("minCareer"),
                    url=url,
                    source="jumpit",
                ))
            except Exception as e:
                self.logger.debug(f"점핏 공고 파싱 실패: {e}")
        return postings
