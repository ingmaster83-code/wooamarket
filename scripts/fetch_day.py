"""전국 공영도매시장 실시간 경매정보(data.go.kr 15141808) 하루치를 받아 집계 저장.
사용: python fetch_day.py 2026-10-27 [2026-10-26 ...]   (인자 없으면 어제)
환경변수 API_KEY(또는 DATA_GO_KR_API_KEY) 필요. 로컬은 hosppass/.env 폴백.
"""
import os, sys, re, json, gzip, time, datetime, urllib.request, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "data" / "daily"
URL = "https://apis.data.go.kr/B552845/katRealTime2/trades2"

def get_key():
    k = os.getenv("API_KEY") or os.getenv("DATA_GO_KR_API_KEY")
    if k: return k
    envf = ROOT.parent / "hosppass" / ".env"
    if envf.exists():
        for l in envf.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(?:API_KEY|DATA_GO_KR_API_KEY)\s*=\s*(.+)", l)
            if m: return m.group(1).strip().strip("\"'")
    sys.exit("API 키 없음")

def page(key, d, n):
    q = {"serviceKey": key, "pageNo": n, "numOfRows": 1000, "returnType": "json", "cond[trd_clcln_ymd::EQ]": d}
    for t in range(5):
        try:
            r = json.loads(urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(q), timeout=60).read().decode("utf-8"))
            b = r["response"]["body"]
            it = b["items"]["item"] if b.get("items") else []
            if isinstance(it, dict): it = [it]
            return int(b["totalCount"]), it
        except Exception as e:
            time.sleep(2 + t * 3)
    raise RuntimeError("page fail %s %s" % (d, n))

def f(x, dflt=0.0):
    try: return float(x)
    except Exception: return dflt

def fetch_day(key, d):
    total, items = page(key, d, 1)
    if total == 0: return None
    rows = list(items)
    for n in range(2, (total + 999) // 1000 + 1):
        rows += page(key, d, n)[1]
    # (시장, 소분류, 포장단위) 집계 + (소분류, 산지시도) 집계
    agg = {}; origin = {}
    for r in rows:
        prc, qty, uq = f(r.get("scsbd_prc")), f(r.get("qty")), f(r.get("unit_qty"))
        unit = (r.get("unit_nm") or "").strip()
        if prc <= 0 or qty <= 0 or uq <= 0 or not unit: continue
        per = prc / uq
        k = (r["whsl_mrkt_cd"], r["whsl_mrkt_nm"], r["gds_lclsf_cd"], r["gds_lclsf_nm"], r["gds_mclsf_cd"], r["gds_mclsf_nm"],
             r.get("gds_sclsf_cd", ""), r.get("gds_sclsf_nm", ""), unit)
        a = agg.setdefault(k, [0, 0.0, 0.0, per, per])  # n, units, amt, min, max
        a[0] += 1; a[1] += qty * uq; a[2] += prc * qty
        a[3] = min(a[3], per); a[4] = max(a[4], per)
        sido = (r.get("plor_nm") or "").split(" ")[0] or "미상"
        ok = (r["gds_mclsf_cd"], r["gds_mclsf_nm"], unit, sido)
        o = origin.setdefault(ok, [0, 0.0, 0.0]); o[0] += 1; o[1] += qty * uq; o[2] += prc * qty
    out = {"date": d, "rows": len(rows),
           "agg": [list(k) + [v[0], round(v[1], 2), round(v[2]), round(v[3], 2), round(v[4], 2)] for k, v in agg.items()],
           "origin": [list(k) + [v[0], round(v[1], 2), round(v[2])] for k, v in origin.items()]}
    return out

def main():
    key = get_key()
    days = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not days:  # 인자 없으면 KST 기준 최근 3일(이미 받은 날은 건너뜀)
        today = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date()
        days = [(today - datetime.timedelta(k)).strftime("%Y-%m-%d") for k in (3, 2, 1)]
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for d in days:
        p = OUTDIR / (d + ".json.gz")
        if p.exists() and "--force" not in sys.argv: print(d, "skip"); continue
        out = fetch_day(key, d)
        if out is None: print(d, "no data"); continue
        with gzip.open(p, "wt", encoding="utf-8") as fh: json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
        print(d, out["rows"], "rows ->", len(out["agg"]), "agg", p.stat().st_size // 1024, "KB", flush=True)

if __name__ == "__main__":
    main()
