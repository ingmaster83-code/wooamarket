# 우아도매시장 (wooamarket)

전국 공영도매시장 실시간 경매정보(data.go.kr 15141808, `apis.data.go.kr/B552845/katRealTime2/trades2`)를 하루 단위로 집계해 품목·시장·산지별 kg당 낙찰가 사이트를 만드는 Python 정적 생성기.

- `scripts/fetch_day.py [YYYY-MM-DD ...]` — 하루치(약 11만 건)를 받아 `data/daily/YYYY-MM-DD.json.gz` 로 집계 저장(인자 없으면 KST 최근 3일, 이미 있으면 건너뜀). API 이력이 한 달뿐이라 매일 누적 커밋한다.
- `scripts/build_site.py` — `data/daily/*` 로 `_site/` 생성(품목·품종·시장·시장×품목·분류·산지·순위).
- `scripts/check_site.py` — 링크/제목/JSON-LD 점검.
- Actions: 매일 15:30 UTC(KST 00:30) fetch → data 커밋 → 빌드 → 배포. 레포 시크릿 `API_KEY` 필요.
