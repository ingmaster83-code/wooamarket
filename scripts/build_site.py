# -*- coding: utf-8 -*-
"""우아도매시장 정적 사이트 생성기 → _site/.
입력: data/daily/YYYY-MM-DD.json.gz (fetch_day.py, 공영도매시장 실시간 경매정보 일별 집계). kg 포장 거래만 사용."""
import sys, json, gzip, re, shutil, time, collections, statistics
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *

# ───────────────────────── 데이터 로드 ─────────────────────────
RAW = {}
for f in sorted((ROOT / "data" / "daily").glob("*.json.gz")):
    d = json.load(gzip.open(f, "rt", encoding="utf-8")); RAW[d["date"]] = d
DAYS = sorted(RAW)
if len(DAYS) >= 5:  # 수집 첫날처럼 장중에 시작한 부분 집계일은 제외
    med = statistics.median(RAW[x]["rows"] for x in DAYS)
    if RAW[DAYS[0]]["rows"] < 0.6 * med: DAYS = DAYS[1:]
ASOF = DAYS[-1]
def kd(d): return "%d월 %d일" % (int(d[5:7]), int(d[8:10]))

def new_series(): return collections.defaultdict(dict)
ITEM, SC, MKT, MI = new_series(), new_series(), new_series(), new_series()
NM = {}      # 이름 사전
ITEMBYMC = collections.defaultdict(list)
def add(S, key, d, n, u, a, mn, mx):
    r = S[key].get(d)
    if r is None: S[key][d] = [n, u, a, mn, mx]
    else: r[0] += n; r[1] += u; r[2] += a; r[3] = min(r[3], mn); r[4] = max(r[4], mx)
for d in DAYS:
    for a in RAW[d]["agg"]:
        mk, mkn, lc, lcn, mc, mcn, sc, scn, unit, n, u, am, mn, mx = a
        if unit != "kg": continue
        ik = (lc, mc)
        NM[("m", mk)] = mkn; NM[("l", lc)] = lcn; NM[("i", ik)] = mcn; NM[("s", (lc, mc, sc))] = scn
        add(ITEM, ik, d, n, u, am, mn, mx); add(SC, (lc, mc, sc), d, n, u, am, mn, mx)
        add(MKT, mk, d, n, u, am, mn, mx); add(MI, (mk, lc, mc), d, n, u, am, mn, mx)
for ik in ITEM: ITEMBYMC[(ik[1], NM[("i", ik)])].append(ik)
SIDO_FULL = {"경기": "경기도", "경남": "경상남도", "경북": "경상북도", "충남": "충청남도", "충북": "충청북도", "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "대전": "대전광역시", "인천": "인천광역시", "울산": "울산광역시", "광주": "광주광역시", "세종": "세종특별자치시", "강원": "강원특별자치도", "전북": "전북특별자치도", "제주": "제주특별자치도"}
DOMESTIC = set(SIDO_FULL.values()) | {"전남광주통합특별시"}
ETC = "기타·수입"
COUNTRY_FIX = {"카나다": "캐나다", "에쿠아도르": "에콰도르", "우즈베크": "우즈베키스탄", "남아프리카": "남아프리카공화국"}
def norm_origin(s):
    s = SIDO_FULL.get(s, s)
    if s in DOMESTIC: return s
    if s in ("-", "", "수입산", "한국", "마이너"): return ETC
    return COUNTRY_FIX.get(s, s)
def is_imp(s): return s not in DOMESTIC and s != ETC
ORI, SIDO = new_series(), new_series()
for d in DAYS:
    for o in RAW[d]["origin"]:
        mc, mcn, unit, sido, n, u, am = o
        if unit != "kg" or not ITEMBYMC.get((mc, mcn)): continue
        ik = max(ITEMBYMC[(mc, mcn)], key=lambda k: sum(r[1] for r in ITEM[k].values()))
        sido = norm_origin(sido)
        add(ORI, (ik, sido), d, n, u, am, 0, 0); add(SIDO, (sido, ik), d, n, u, am, 0, 0)

# ───────────────────────── 도우미 ─────────────────────────
def sl(s): return re.sub(r"[^0-9A-Za-z가-힣]+", "-", s).strip("-") or "x"
def pxr(r): return (r[2] / r[1]) if r and r[1] > 0 else None
def kw(x): return "-" if x is None else "{:,}원".format(int(round(x)))
def ton(u): return "{:,.1f}톤".format(u / 1000.0) if u >= 1000 else "{:,}kg".format(int(round(u)))
def pct(a, b):
    if a is None or not b: return None
    return (a - b) / b * 100.0
def pcts(p, plain=False):
    if p is None: return "-"
    if abs(p) < 0.05: return "변동 없음"
    t = "%+.1f%%" % p
    return t if plain else '<span class="%s">%s</span>' % ("up" if p > 0 else "down", t)
def move(p):
    if p is None: return ""
    if abs(p) < 0.05: return "변동이 없습니다"
    return "%.1f%% %s" % (abs(p), "올랐습니다" if p > 0 else "내렸습니다")
def table(heads, rows, num=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)
def chips(items): return '<div class="chips">%s</div>' % "".join('<a class="chip" href="%s">%s</a>' % (u, esc(t)) for t, u in items)
def stats_row(items): return '<div class="stat-row">%s</div>' % "".join('<div class="stat"><small>%s</small><b>%s</b></div>' % (a, b) for a, b in items)
def rng(ser, days):
    out = [0, 0.0, 0.0, 1e18, 0.0]
    for d in days:
        r = ser.get(d)
        if r: out[0] += r[0]; out[1] += r[1]; out[2] += r[2]; out[3] = min(out[3], r[3]); out[4] = max(out[4], r[4])
    return out if out[1] > 0 else None
def info(ser):
    """최근 경매일 기준 요약."""
    ds = sorted(ser); ld = ds[-1]; cur = ser[ld]; px = pxr(cur)
    prev = pxr(ser[ds[-2]]) if len(ds) >= 2 else None
    wk = rng(ser, ds[-8:-1]); wkp = pxr(wk) if wk else None
    allp = [pxr(ser[x]) for x in ds]
    return dict(ld=ld, ds=ds, cur=cur, px=px, prev=prev, d1=pct(px, prev), wk=wkp, d7=pct(px, wkp), lo=min(allp), hi=max(allp), n=len(ds))
def spark(ser, days):
    ds = [x for x in days if x in ser][-30:]
    if len(ds) < 2: return ""
    v = [pxr(ser[x]) for x in ds]; lo, hi = min(v), max(v); span = (hi - lo) or 1.0
    W, H, PL, PR, PT, PB = 720, 180, 50, 14, 16, 30
    pts = [(PL + (W - PL - PR) * i / (len(ds) - 1), PT + (H - PT - PB) * (1 - (y - lo) / span)) for i, y in enumerate(v)]
    poly = " ".join("%.1f,%.1f" % p for p in pts)
    dots = "".join('<circle cx="%.1f" cy="%.1f" r="2.6" fill="#15803D"/>' % p for p in pts)
    return ('<svg class="spark" viewBox="0 0 %d %d" role="img" aria-label="일별 평균 낙찰가 추이">'
            '<text x="4" y="%d" font-size="11" fill="#6B7280">%s</text><text x="4" y="%d" font-size="11" fill="#6B7280">%s</text>'
            '<polyline points="%s" fill="none" stroke="#22C55E" stroke-width="2.2"/>%s'
            '<text x="%d" y="%d" font-size="11" fill="#6B7280">%s</text><text x="%d" y="%d" font-size="11" fill="#6B7280" text-anchor="end">%s</text></svg>') % (
        W, H, PT + 4, "{:,}".format(int(round(hi))), H - PB, "{:,}".format(int(round(lo))), poly, dots, PL, H - 8, kd(ds[0]), W - PR, H - 8, kd(ds[-1]))
def trend_table(ser, days, nrows=14):
    ds = [x for x in days if x in ser][-nrows:][::-1]
    rows = []
    for x in ds:
        r = ser[x]; rows.append([kd(x), kw(pxr(r)), ton(r[1]), "{:,}".format(r[0])])
    return table(["경매일", "평균 낙찰가(kg)", "거래량", "거래 건수"], rows, (1, 2, 3))

# ───────────────────────── 페이지 대상 확정 ─────────────────────────
MIN_TRADES = 20
def tot_trades(ser): return sum(r[0] for r in ser.values())
ITEMS = {k: info(v) for k, v in ITEM.items() if tot_trades(v) >= MIN_TRADES}
inames = collections.Counter(NM[("i", k)] for k in ITEMS)
IPATH = {}
for k in sorted(ITEMS):
    nm = NM[("i", k)]; slug = sl(nm) + (("-" + sl(NM[("l", k[0])])) if inames[nm] > 1 else "")
    IPATH[k] = "/item/%s/" % slug
SCS = {}
for k, v in SC.items():
    if k[:2] in ITEMS and tot_trades(v) >= 30 and len(v) >= 2 and NM[("s", k)] != NM[("i", k[:2])]: SCS[k] = info(v)
sc_seen = collections.Counter()
SCPATH = {}
for k in sorted(SCS):
    base = IPATH[k[:2]] + sl(NM[("s", k)]) + "/"
    if base in SCPATH.values(): base = IPATH[k[:2]] + sl(NM[("s", k)]) + "-" + k[2] + "/"
    SCPATH[k] = base
MKTS = {k: info(v) for k, v in MKT.items() if tot_trades(v) >= 100}
MPATH = {k: "/market/%s/" % sl(NM[("m", k)]) for k in MKTS}
MIS = {k: info(v) for k, v in MI.items() if k[0] in MKTS and k[1:] in ITEMS and tot_trades(v) >= 15}
MIPATH = {k: MPATH[k[0]] + IPATH[k[1:]].split("/")[2] + "/" for k in MIS}
CATS = collections.defaultdict(list)
for k in ITEMS: CATS[k[0]].append(k)
CPATH = {c: "/category/%s/" % sl(NM[("l", c)]) for c in CATS}
SIDOS = sorted({k[0] for k in SIDO})
SDPATH = {s: "/origin/%s/" % sl(s) for s in SIDOS}
OIS = {k: info(v) for k, v in ORI.items() if k[0] in ITEMS and k[1] != ETC and tot_trades(v) >= 30 and len(v) >= 5 and sum(r[1] for r in v.values()) >= 3000}
OIPATH = {k: SDPATH[k[1]] + IPATH[k[0]].split("/")[2] + "/" for k in OIS}
def iname(k): return NM[("i", k)]
def mname(k): return NM[("m", k)]
def ilink(k, t=None): return '<a href="%s">%s</a>' % (IPATH[k], esc(t or iname(k)))
def mlink(k): return '<a href="%s">%s</a>' % (MPATH[k], esc(mname(k)))
MALIAS = {"서울가락": "가락시장", "서울강서": "강서시장", "부산엄궁": "엄궁시장", "부산반여": "반여시장"}
def mtitle(k):
    n = mname(k); return n + "(" + MALIAS[n] + ")" if n in MALIAS else n
NOTE = ("낙찰가는 공영도매시장 경매에서 확정된 가격을 kg당으로 환산한 값이며, 같은 날 같은 품목의 거래량 가중 평균입니다. 품종·등급·포장·산지에 따라 크게 다를 수 있고 소매가와는 유통비용만큼 차이가 납니다. %s 경매일까지의 자료입니다." % kd(ASOF))
ASOF_NOTE = "%s 기준" % kd(ASOF)
def region_list(k):
    return None

# ───────────────────────── 품목 ─────────────────────────
def origin_rows(ik, days=None, top=12):
    days = days or DAYS[-7:]
    agg = []
    for (k, sido), ser in ORI.items():
        if k != ik: continue
        r = rng(ser, days)
        if r: agg.append((sido, r))
    agg.sort(key=lambda x: -x[1][1])
    return agg[:top]
def market_rows(ik, day):
    rows = []
    for mk in MKTS:
        r = MI.get((mk, ik[0], ik[1]), {}).get(day)
        if r and r[1] > 0: rows.append((mk, r))
    rows.sort(key=lambda x: pxr(x[1]))
    return rows

def page_item(ik):
    I = ITEMS[ik]; nm = iname(ik); ser = ITEM[ik]; path = IPATH[ik]; ld = I["ld"]; lcn = NM[("l", ik[0])]
    mrows = market_rows(ik, ld); orows = origin_rows(ik)
    cheap = [x for x in mrows if x[1][1] >= 200]; ch = cheap[0] if cheap else (mrows[0] if mrows else None)
    ex = cheap[-1] if cheap else (mrows[-1] if mrows else None)
    lead = "<b>%s</b>(%s)의 %s 전국 공영도매시장 평균 낙찰가는 <b>kg당 %s</b>입니다." % (esc(nm), esc(lcn), kd(ld), kw(I["px"]))
    if I["d1"] is not None: lead += " 직전 경매일(%s)보다 %s." % (kd(I["ds"][-2]), move(I["d1"]))
    if I["d7"] is not None and I["wk"]: lead += " 최근 7경매일 평균(%s)과 비교하면 %s." % (kw(I["wk"]), move(I["d7"]))
    lead += " 그날 %s이(가) %s건 거래되었습니다." % (ton(I["cur"][1]), "{:,}".format(I["cur"][0]))
    if ch and ex and ch[0] != ex[0] and len(cheap) >= 2:
        lead += " 시장별로는 %s(kg당 %s)이(가) 가장 낮고 %s(kg당 %s)이(가) 가장 높았습니다." % (esc(mname(ch[0])), kw(pxr(ch[1])), esc(mname(ex[0])), kw(pxr(ex[1])))
    st = stats_row([("평균 낙찰가(kg)", kw(I["px"])), ("전 경매일 대비", pcts(I["d1"])), ("7경매일 평균 대비", pcts(I["d7"])), ("거래량", ton(I["cur"][1])), ("%d경매일 일평균 최저~최고" % I["n"], "%s~%s" % ("{:,}".format(int(round(I["lo"]))), "{:,}".format(int(round(I["hi"])))))])
    mt = table(["도매시장", "평균 낙찰가(kg)", "거래량", "거래 건수"], [[(('<a href="%s">%s</a>' % (MIPATH[(mk,) + ik], esc(mname(mk)))) if (mk,) + ik in MIPATH else esc(mname(mk))), kw(pxr(r)), ton(r[1]), "{:,}".format(r[0])] for mk, r in mrows], (1, 2, 3)) if mrows else ""
    ot = table(["산지(시·도)", "평균 낙찰가(kg)", "거래량(최근 7경매일)"], [[('<a href="%s">%s</a>' % (OIPATH[(ik, s)], esc(s))) if (ik, s) in OIPATH else esc(s), kw(pxr(r)), ton(r[1])] for s, r in orows], (1, 2)) if orows else ""
    vr = sorted([(k, v) for k, v in SCS.items() if k[:2] == ik], key=lambda x: -x[1]["cur"][1])
    vt = table(["품종·규격", "평균 낙찰가(kg)", "전 경매일 대비", "거래량"], [[('<a href="%s">%s</a>' % (SCPATH[k], esc(NM[("s", k)]))), kw(v["px"]), pcts(v["d1"]), ton(v["cur"][1])] for k, v in vr[:30]], (1, 2, 3)) if vr else ""
    sib = [k for k in sorted(CATS[ik[0]], key=lambda k: -ITEMS[k]["cur"][1]) if k != ik][:14]
    body = f"""
<div class="page-head"><h1>{esc(nm)} 도매시장 시세 — kg당 {kw(I['px'])}</h1><p>{esc(lcn)} · 전국 공영도매시장 경매 낙찰가 · {kd(ld)} 경매 기준</p></div>
<p class="lead">{lead}</p>
{st}
{ad()}
<h2 class="group-title">📈 일별 평균 낙찰가 추이 <small>최근 {min(30, len([x for x in DAYS if x in ser]))}경매일</small></h2>
{spark(ser, DAYS)}
{trend_table(ser, DAYS)}
{('<h2 class="group-title">🏪 도매시장별 낙찰가 <small>%s</small></h2>' % kd(ld) + mt) if mt else ''}
{('<h2 class="group-title">🚚 산지별 낙찰가</h2>' + ot) if ot else ''}
{('<h2 class="group-title">🏷️ 품종·규격별 시세</h2>' + vt) if vt else ''}
<p class="note">{NOTE}</p>
{chips([(esc(NM[("l", ik[0])]) + " 전체", CPATH[ik[0]]), ("가격 순위", "/rank/"), ("도매시장 전체", "/market/")] + [(iname(k), IPATH[k]) for k in sib])}
"""
    fq = [("%s 도매가는 지금 얼마인가요?" % nm, "%s 경매 기준 전국 공영도매시장 평균 낙찰가는 kg당 %s입니다." % (kd(ld), kw(I["px"])) + ((" 직전 경매일보다 %s." % move(I["d1"])) if I["d1"] is not None else ""))]
    if ch and ex and len(cheap) >= 2: fq.append(("%s는 어느 도매시장이 가장 싼가요?" % nm, "%s 거래량 200kg 이상 시장 중에서는 %s(kg당 %s)이(가) 가장 낮았고 %s(kg당 %s)이(가) 가장 높았습니다. 시장별 품질·등급 구성이 달라 단순 비교는 어렵습니다." % (kd(ld), mname(ch[0]), kw(pxr(ch[1])), mname(ex[0]), kw(pxr(ex[1])))))
    if orows: fq.append(("%s는 어디에서 많이 들어오나요?" % nm, "최근 7경매일 반입량이 가장 많은 산지는 %s(%s)이며 다음으로 %s 순입니다." % (orows[0][0], ton(orows[0][1][1]), ", ".join(s for s, _ in orows[1:4]) or "-")))
    fq.append(("도매시장 낙찰가와 마트 판매가는 왜 다른가요?", "도매 낙찰가는 산지에서 올라온 물량이 경매로 팔릴 때의 가격이며 소매가에는 유통·운송·포장 비용과 소매 마진이 더해집니다. 이 사이트의 가격은 소매가 아닌 도매 낙찰가입니다."))
    write(path, layout(path, "%s 도매시장 시세 — kg당 %s (%s)" % (nm, kw(I["px"]), kd(ld)), "%s 도매시장 경매 낙찰가 kg당 %s (%s 기준%s). 시장별·산지별·품종별 가격과 일별 추이를 한눈에." % (nm, kw(I["px"]), kd(ld), (", 전 경매일 대비 " + pcts(I["d1"], True)) if I["d1"] is not None else ""), body, fq,
          [("홈", "/"), ("품목별 시세", "/item/"), (nm, path)]), "0.8")

def page_sc(k):
    I = SCS[k]; ser = SC[k]; nm = NM[("s", k)]; ik = k[:2]; path = SCPATH[k]; ld = I["ld"]; par = ITEMS[ik]
    diff = pct(I["px"], par["px"]) if ld == par["ld"] else None
    lead = "<b>%s</b>은(는) %s의 품종·규격 구분입니다. %s 전국 공영도매시장 평균 낙찰가는 <b>kg당 %s</b>, 거래량은 %s(%s건)였습니다." % (esc(nm), esc(iname(ik)), kd(ld), kw(I["px"]), ton(I["cur"][1]), "{:,}".format(I["cur"][0]))
    if I["d1"] is not None: lead += " 직전 경매일(%s)보다 %s." % (kd(I["ds"][-2]), move(I["d1"]))
    if diff is not None and abs(diff) >= 0.05: lead += " 같은 날 %s 전체 평균(%s)보다 %.1f%% %s." % (esc(iname(ik)), kw(par["px"]), abs(diff), "높습니다" if diff > 0 else "낮습니다")
    st = stats_row([("평균 낙찰가(kg)", kw(I["px"])), ("전 경매일 대비", pcts(I["d1"])), ("7경매일 평균 대비", pcts(I["d7"])), ("거래량", ton(I["cur"][1]))])
    sib = [x for x in sorted((x for x in SCS if x[:2] == ik and x != k), key=lambda x: -SCS[x]["cur"][1])][:12]
    body = f"""
<div class="page-head"><h1>{esc(iname(ik))} {esc(nm)} 도매 시세 — kg당 {kw(I['px'])}</h1><p>{kd(ld)} 경매 기준 · 전국 공영도매시장</p></div>
<p class="lead">{lead}</p>
{st}
{ad()}
<h2 class="group-title">📈 일별 평균 낙찰가 추이</h2>
{spark(ser, DAYS)}
{trend_table(ser, DAYS)}
<p class="note">{NOTE}</p>
{chips([("%s 시세 전체" % iname(ik), IPATH[ik])] + [(NM[("s", x)], SCPATH[x]) for x in sib])}
"""
    fq = [("%s 도매가는 얼마인가요?" % nm, "%s 경매 기준 전국 공영도매시장 평균 낙찰가는 kg당 %s입니다." % (kd(ld), kw(I["px"]))), ("%s와(과) %s 가격은 왜 다른가요?" % (nm, iname(ik)), "같은 품목이어도 품종·크기·등급에 따라 낙찰가가 다르며 %s은(는) 그 중 한 규격입니다." % nm)]
    write(path, layout(path, "%s %s 도매 시세 — kg당 %s" % (iname(ik), nm, kw(I["px"])), "%s %s 도매시장 경매 낙찰가 kg당 %s (%s 기준). 일별 추이와 거래량." % (iname(ik), nm, kw(I["px"]), kd(ld)), body, fq,
          [("홈", "/"), ("품목별 시세", "/item/"), (iname(ik), IPATH[ik]), (nm, path)]), "0.5")

# ───────────────────────── 시장 ─────────────────────────
def page_market(mk):
    I = MKTS[mk]; nm = mname(mk); path = MPATH[mk]; ld = I["ld"]
    its = []
    for k in ITEMS:
        ser = MI.get((mk,) + k)
        if not ser or ld not in ser: continue
        its.append((k, ser[ld], info(ser) if (mk,) + k in MIS else None))
    its.sort(key=lambda x: -x[1][1])
    def row(x):
        k, r, i = x
        link = ('<a href="%s">%s</a>' % (MIPATH[(mk,) + k], esc(iname(k)))) if (mk,) + k in MIPATH else esc(iname(k))
        return [link, esc(NM[("l", k[0])]), kw(pxr(r)), pcts(i["d1"]) if i else "-", ton(r[1]), "{:,}".format(r[0])]
    top = its[:100]
    risers = sorted([x for x in its if x[2] and x[2]["d1"] is not None and x[1][1] >= 500], key=lambda x: -x[2]["d1"])[:5]
    lead = "<b>%s</b> 공영도매시장의 %s 경매에서는 %d개 품목, 총 %s(%s건)이 거래되었습니다. 거래량이 가장 많은 품목은 %s, %s이며 가장 많이 오른 품목은 %s입니다." % (
        esc(mtitle(mk)), kd(ld), len(its), ton(I["cur"][1]), "{:,}".format(I["cur"][0]), esc(iname(its[0][0])) if its else "-", esc(iname(its[1][0])) if len(its) > 1 else "-",
        (esc(iname(risers[0][0])) + "(" + pcts(risers[0][2]["d1"], True) + ")") if risers else "없습니다")
    cats = sorted({k[0] for k, _, _ in its})
    body = f"""
<div class="page-head"><h1>{esc(mtitle(mk))} 도매시장 경매 시세 — 품목별 낙찰가</h1><p>{kd(ld)} 경매 기준 · 거래량 많은 순 {len(top)}개 품목</p></div>
<p class="lead">{lead}</p>
{stats_row([("거래 품목", "%d개" % len(its)), ("거래량", ton(I["cur"][1])), ("거래 건수", "{:,}".format(I["cur"][0]))])}
{ad()}
{table(["품목", "분류", "평균 낙찰가(kg)", "전 경매일 대비", "거래량", "건수"], [row(x) for x in top], (2, 3, 4, 5))}
<p class="note">{NOTE}</p>
{chips([("도매시장 전체", "/market/"), ("가격 순위", "/rank/")] + [(NM[("l", c)], CPATH[c]) for c in cats if c in CPATH][:10])}
"""
    fq = [("%s 도매시장에서 거래량이 가장 많은 품목은?" % nm, "%s 경매 기준 %s입니다." % (kd(ld), ", ".join(iname(x[0]) for x in its[:3]) or "-")), ("%s 시세는 얼마나 자주 갱신되나요?" % nm, "경매가 열린 날의 낙찰 내역을 다음 날 새벽에 받아 갱신합니다. 휴장일에는 새 자료가 없습니다.")]
    write(path, layout(path, "%s 도매시장 경매 시세 — 오늘의 품목별 낙찰가" % mtitle(mk), "%s 도매시장 %s 경매 시세. %d개 품목 kg당 낙찰가와 전 경매일 대비 등락, 거래량." % (mtitle(mk), kd(ld), len(its)), body, fq, [("홈", "/"), ("시장별 시세", "/market/"), (nm, path)]), "0.7")

def page_mi(k):
    I = MIS[k]; mk = k[0]; ik = k[1:]; ser = MI[k]; path = MIPATH[k]; ld = I["ld"]; nat = ITEMS[ik]
    natp = pxr(ITEM[ik].get(ld)); diff = pct(I["px"], natp)
    lead = "<b>%s</b> 도매시장에서 <b>%s</b>의 %s 평균 낙찰가는 <b>kg당 %s</b>이고 거래량은 %s(%s건)입니다." % (esc(mtitle(mk)), esc(iname(ik)), kd(ld), kw(I["px"]), ton(I["cur"][1]), "{:,}".format(I["cur"][0]))
    if diff is not None and natp: lead += " 같은 날 전국 평균(%s)보다 %s." % (kw(natp), "비슷합니다" if abs(diff) < 0.05 else ("%.1f%% %s" % (abs(diff), "높습니다" if diff > 0 else "낮습니다")))
    if I["d1"] is not None: lead += " 이 시장 직전 경매일(%s)보다 %s." % (kd(I["ds"][-2]), move(I["d1"]))
    others = sorted([(m, r) for m, r in market_rows(ik, ld) if m != mk and r[1] >= 200], key=lambda x: pxr(x[1]))
    ot = table(["도매시장", "평균 낙찰가(kg)", "거래량"], [[(('<a href="%s">%s</a>' % (MIPATH[(m,) + ik], esc(mname(m)))) if (m,) + ik in MIPATH else esc(mname(m))), kw(pxr(r)), ton(r[1])] for m, r in others[:12]], (1, 2)) if others else ""
    body = f"""
<div class="page-head"><h1>{esc(mtitle(mk))} {esc(iname(ik))} 시세 — kg당 {kw(I['px'])}</h1><p>{kd(ld)} 경매 기준 · 도매시장 낙찰가</p></div>
<p class="lead">{lead}</p>
{stats_row([("평균 낙찰가(kg)", kw(I["px"])), ("전 경매일 대비", pcts(I["d1"])), ("전국 평균 대비", pcts(diff)), ("거래량", ton(I["cur"][1]))])}
{ad()}
<h2 class="group-title">📈 {esc(mname(mk))} 일별 평균 낙찰가 추이</h2>
{spark(ser, DAYS)}
{trend_table(ser, DAYS)}
{('<h2 class="group-title">🏪 다른 도매시장과 비교 <small>%s</small></h2>' % kd(ld) + ot) if ot else ''}
<p class="note">{NOTE}</p>
{chips([("%s 전국 시세" % iname(ik), IPATH[ik]), ("%s 전체 품목" % mname(mk), MPATH[mk])])}
"""
    fq = [("%s 도매시장 %s 가격은 얼마인가요?" % (mname(mk), iname(ik)), "%s 경매 기준 평균 낙찰가는 kg당 %s이며 전국 평균은 %s입니다." % (kd(ld), kw(I["px"]), kw(natp))), ("도매시장 가격과 마트 가격은 왜 다른가요?", "도매 낙찰가는 경매 확정가이고 소매가에는 유통·운송·소매 마진이 더해집니다.")]
    write(path, layout(path, "%s %s 시세 — kg당 %s (%s)" % (mtitle(mk), iname(ik), kw(I["px"]), kd(ld)), "%s 도매시장 %s 경매 낙찰가 kg당 %s (%s). 전국 평균 대비·일별 추이." % (mtitle(mk), iname(ik), kw(I["px"]), kd(ld)), body, fq, [("홈", "/"), ("시장별 시세", "/market/"), (mname(mk), MPATH[mk]), (iname(ik), path)]), "0.6")

def hub_market():
    ms = sorted(MKTS, key=lambda m: -MKTS[m]["cur"][1])
    rows = [['<a href="%s">%s</a>' % (MPATH[m], esc(mtitle(m))), kd(MKTS[m]["ld"]), "{:,}".format(MKTS[m]["cur"][0]), ton(MKTS[m]["cur"][1])] for m in ms]
    body = f"""
<div class="page-head"><h1>전국 공영도매시장별 경매 시세</h1><p>{len(ms)}개 시장 · {ASOF_NOTE}</p></div>
<p class="lead">서울가락·부산엄궁·대구북부 등 전국 {len(ms)}개 공영도매시장의 일별 경매 낙찰 내역을 시장별로 모았습니다. 시장을 고르면 거래량 많은 품목의 kg당 낙찰가와 전 경매일 대비 등락을 볼 수 있습니다.</p>
{ad()}
{table(['도매시장', '최근 경매일', '거래 건수', '거래량'], rows, (2, 3))}
<p class="note">{NOTE}</p>
"""
    write("/market/", layout("/market/", "전국 공영도매시장 경매 시세 — 시장별 품목 낙찰가", "전국 %d개 공영도매시장의 일별 경매 낙찰가를 시장별로 비교. 서울가락·부산엄궁 등." % len(ms), body, [("공영도매시장은 몇 곳인가요?", "이 사이트는 실시간 경매정보를 제공하는 전국 %d개 공영도매시장을 다룹니다." % len(ms))], [("홈", "/"), ("시장별 시세", "/market/")]), "0.8")

# ───────────────────────── 분류 · 품목 허브 ─────────────────────────
def page_cat(c):
    ks = sorted(CATS[c], key=lambda k: -ITEMS[k]["cur"][1]); nm = NM[("l", c)]; path = CPATH[c]
    rows = [[ilink(k), kw(ITEMS[k]["px"]), pcts(ITEMS[k]["d1"]), ton(ITEMS[k]["cur"][1]), kd(ITEMS[k]["ld"])] for k in ks]
    mov = sorted([k for k in ks if ITEMS[k]["d1"] is not None and ITEMS[k]["cur"][1] >= 2000], key=lambda k: -ITEMS[k]["d1"])
    lead = "<b>%s</b> 분류에는 %d개 품목이 있으며 거래량이 가장 많은 품목은 %s(kg당 %s)입니다.%s" % (esc(nm), len(ks), esc(iname(ks[0])), kw(ITEMS[ks[0]]["px"]),
        (" 최근 경매일 기준 가장 많이 오른 품목은 %s(%s), 가장 많이 내린 품목은 %s(%s)입니다." % (esc(iname(mov[0])), pcts(ITEMS[mov[0]]["d1"], True), esc(iname(mov[-1])), pcts(ITEMS[mov[-1]]["d1"], True))) if len(mov) >= 2 else "")
    body = f"""
<div class="page-head"><h1>{esc(nm)} 도매시장 시세 — {len(ks)}개 품목 낙찰가</h1><p>{ASOF_NOTE} · 거래량 많은 순</p></div>
<p class="lead">{lead}</p>
{ad()}
{table(['품목', '평균 낙찰가(kg)', '전 경매일 대비', '거래량', '경매일'], rows, (1, 2, 3))}
<p class="note">{NOTE}</p>
{chips([("분류 전체", "/category/"), ("가격 순위", "/rank/")])}
"""
    write(path, layout(path, "%s 도매시장 시세 — %d개 품목 kg당 낙찰가" % (nm, len(ks)), "%s %d개 품목의 도매시장 경매 낙찰가(kg당)와 전 경매일 대비 등락. %s." % (nm, len(ks), ASOF_NOTE), body, [("%s에는 어떤 품목이 있나요?" % nm, ", ".join(iname(k) for k in ks[:8]) + " 등 %d개 품목이 있습니다." % len(ks))], [("홈", "/"), ("분류별", "/category/"), (nm, path)]), "0.7")
def hub_cat():
    cs = sorted(CATS, key=lambda c: -sum(ITEMS[k]["cur"][1] for k in CATS[c]))
    rows = [['<a href="%s">%s</a>' % (CPATH[c], esc(NM[("l", c)])), len(CATS[c]), ", ".join(esc(iname(k)) for k in sorted(CATS[c], key=lambda k: -ITEMS[k]["cur"][1])[:5])] for c in cs]
    body = f"""
<div class="page-head"><h1>도매시장 경매 품목 분류별 시세</h1><p>{len(cs)}개 분류 · {ASOF_NOTE}</p></div>
<p class="lead">공영도매시장에서 거래되는 농수산물을 엽경채류·과일류·근채류 등 분류별로 나눠 kg당 낙찰가와 등락을 정리했습니다.</p>
{ad()}
{table(['분류', '품목 수', '주요 품목'], rows, (1,))}
<p class="note">{NOTE}</p>
"""
    write("/category/", layout("/category/", "도매시장 경매 품목 분류별 시세", "엽경채류·과일류·근채류 등 %d개 분류별 도매시장 경매 낙찰가." % len(cs), body, None, [("홈", "/"), ("분류별", "/category/")]), "0.7")
def hub_item():
    ks = sorted(ITEMS, key=lambda k: -ITEMS[k]["cur"][1])
    rows = [[ilink(k), esc(NM[("l", k[0])]), kw(ITEMS[k]["px"]), pcts(ITEMS[k]["d1"]), ton(ITEMS[k]["cur"][1])] for k in ks]
    body = f"""
<div class="page-head"><h1>품목별 도매시장 경매 시세 — {len(ks)}개 품목</h1><p>{ASOF_NOTE} · 거래량 많은 순</p></div>
<p class="lead">배추·사과·양파·감자 등 공영도매시장에서 거래되는 {len(ks)}개 농수산물 품목의 kg당 평균 낙찰가와 전 경매일 대비 등락을 모았습니다.</p>
{ad()}
{table(['품목', '분류', '평균 낙찰가(kg)', '전 경매일 대비', '거래량'], rows, (2, 3, 4))}
<p class="note">{NOTE}</p>
"""
    write("/item/", layout("/item/", "품목별 도매시장 경매 시세 — %d개 농수산물 kg당 낙찰가" % len(ks), "배추·사과·양파 등 %d개 품목의 도매시장 경매 낙찰가와 등락. %s." % (len(ks), ASOF_NOTE), body, None, [("홈", "/"), ("품목별 시세", "/item/")]), "0.8")

# ───────────────────────── 산지 ─────────────────────────
def page_sido(s):
    r7 = DAYS[-7:]; rows = []
    for (sd, ik), ser in SIDO.items():
        if sd != s or ik not in ITEMS: continue
        r = rng(ser, r7)
        if r: rows.append((ik, r))
    rows.sort(key=lambda x: -x[1][1]); path = SDPATH[s]
    if not rows: return
    tot = sum(r[1] for _, r in rows)
    imp = is_imp(s); kind = "수입산" if imp else "산지"
    lead = ("<b>%s</b>산 수입 농수산물은 최근 7경매일 동안 %d개 품목, 총 %s가 전국 공영도매시장에서 경매되었습니다. 반입량이 가장 많은 품목은 %s(%s)입니다." if imp else "<b>%s</b>에서 올라온 농수산물은 최근 7경매일 동안 %d개 품목, 총 %s가 전국 공영도매시장에서 경매되었습니다. 반입량이 가장 많은 품목은 %s(%s)입니다.") % (esc(s), len(rows), ton(tot), esc(iname(rows[0][0])), ton(rows[0][1][1]))
    body = f"""
<div class="page-head"><h1>{esc(s)}{"산 수입 농수산물" if imp else " 산지 농산물"} 도매 시세 — 품목별 낙찰가</h1><p>최근 7경매일 · {ASOF_NOTE}</p></div>
<p class="lead">{lead}</p>
{ad()}
{table(['품목', '평균 낙찰가(kg)', '반입 거래량'], [[('<a href="%s">%s</a>' % (OIPATH[(k, s)], esc(iname(k)))) if (k, s) in OIPATH else ilink(k), kw(pxr(r)), ton(r[1])] for k, r in rows[:80]], (1, 2))}
<p class="note">{NOTE} {"수입산은 원산지 국가 단위입니다." if imp else "산지는 경매 출하지의 시·도 단위입니다."}</p>
{chips([("산지 전체", "/origin/"), ("품목별 시세", "/item/")])}
"""
    write(path, layout(path, ("%s산 수입 농수산물 도매 시세 — 품목별 반입량·낙찰가" if imp else "%s 산지 농산물 도매 시세 — 품목별 반입량·낙찰가") % s, ("%s산 수입 농수산물의 도매시장 경매 낙찰가와 반입량(최근 7경매일, %d개 품목)." if imp else "%s에서 출하된 농수산물의 도매시장 경매 낙찰가와 반입량(최근 7경매일, %d개 품목).") % (s, len(rows)), body, [("%s 농산물 중 반입량이 가장 많은 품목은?" % s, "최근 7경매일 기준 %s입니다." % ", ".join(iname(k) for k, _ in rows[:3]))], [("홈", "/"), ("산지별", "/origin/"), (s, path)]), "0.6")
def page_oi(k):
    I = OIS[k]; ik, s = k; ser = ORI[k]; path = OIPATH[k]; ld = I["ld"]; nat = ITEMS[ik]; imp = is_imp(s)
    natp = pxr(ITEM[ik].get(ld)); diff = pct(I["px"], natp)
    lead = "<b>%s</b> <b>%s</b>의 %s 도매시장 평균 낙찰가는 <b>kg당 %s</b>이고 반입량은 %s(%s건)입니다." % (esc(s), esc(iname(ik)), kd(ld), kw(I["px"]), ton(I["cur"][1]), "{:,}".format(I["cur"][0]))
    if diff is not None and natp: lead += " 같은 날 전국 평균(%s)보다 %s." % (kw(natp), "비슷합니다" if abs(diff) < 0.05 else ("%.1f%% %s" % (abs(diff), "높습니다" if diff > 0 else "낮습니다")))
    if I["d1"] is not None: lead += " 이 산지 직전 경매일(%s)보다 %s." % (kd(I["ds"][-2]), move(I["d1"]))
    others = [(sd, r) for sd, r in origin_rows(ik, [ld], 30) if sd != s and sd != ETC and r[1] >= 200][:12]
    ot = table(["산지", "평균 낙찰가(kg)", "반입량"], [[(('<a href="%s">%s</a>' % (OIPATH[(ik, sd)], esc(sd))) if (ik, sd) in OIPATH else esc(sd)), kw(pxr(r)), ton(r[1])] for sd, r in others], (1, 2)) if others else ""
    body = f"""
<div class="page-head"><h1>{esc(s)} {esc(iname(ik))} 도매시세 — kg당 {kw(I['px'])}</h1><p>{kd(ld)} 경매 기준 · {'수입산' if imp else '산지별'} 도매시장 낙찰가</p></div>
<p class="lead">{lead}</p>
{stats_row([("평균 낙찰가(kg)", kw(I["px"])), ("전 경매일 대비", pcts(I["d1"])), ("전국 평균 대비", pcts(diff)), ("반입량", ton(I["cur"][1]))])}
{ad()}
<h2 class="group-title">📈 {esc(s)} {esc(iname(ik))} 일별 평균 낙찰가 추이</h2>
{spark(ser, DAYS)}
{trend_table(ser, DAYS)}
{('<h2 class="group-title">🚚 다른 산지와 비교 <small>%s</small></h2>' % kd(ld) + ot) if ot else ''}
<p class="note">{NOTE} {"수입산은 원산지 국가 단위입니다." if imp else "산지는 경매 출하지의 시·도 단위입니다."}</p>
{chips([("%s 전국 시세" % iname(ik), IPATH[ik]), ("%s 품목별 시세" % s, SDPATH[s]), ("산지별 전체", "/origin/")])}
"""
    fq = [("%s %s 도매가는 얼마인가요?" % (s, iname(ik)), "%s 경매 기준 %s 평균 낙찰가는 kg당 %s이며 전국 평균은 %s입니다." % (kd(ld), s, kw(I["px"]), kw(natp))), ("도매 낙찰가와 마트 가격은 왜 다른가요?", "도매 낙찰가는 경매 확정 가격이며 소매가에는 유통·운송·포장 비용과 소매 마진이 더해집니다.")]
    write(path, layout(path, "%s %s 도매시세 — kg당 %s (%s)" % (s, iname(ik), kw(I["px"]), kd(ld)), "%s %s 도매시장 경매 낙찰가 kg당 %s (%s). 전국 평균 대비·다른 산지 비교·일별 추이." % (s, iname(ik), kw(I["px"]), kd(ld)), body, fq, [("홈", "/"), ("산지별", "/origin/"), (s, SDPATH[s]), (iname(ik), path)]), "0.6")

def hub_origin():
    r7 = DAYS[-7:]; agg = collections.defaultdict(lambda: [0, 0.0])
    for (sd, ik), ser in SIDO.items():
        r = rng(ser, r7)
        if r: agg[sd][0] += 1; agg[sd][1] += r[1]
    ss = sorted(agg, key=lambda s: -agg[s][1])
    body = f"""
<div class="page-head"><h1>산지별 농산물 도매시장 반입 현황</h1><p>최근 7경매일 · {ASOF_NOTE}</p></div>
<p class="lead">도매시장 경매에 출하된 농수산물을 산지(시·도)별로 모아 어떤 지역에서 어떤 품목이 많이 올라오는지 보여줍니다.</p>
{ad()}
<h2 class="group-title">🇰🇷 국내 산지(시·도)</h2>
{table(['산지', '품목 수', '반입 거래량'], [['<a href="%s">%s</a>' % (SDPATH[s], esc(s)), agg[s][0], ton(agg[s][1])] for s in ss if not is_imp(s) and s != ETC], (1, 2))}
<h2 class="group-title">🌏 수입산(원산지 국가)</h2>
{table(['원산지', '품목 수', '반입 거래량'], [['<a href="%s">%s</a>' % (SDPATH[s], esc(s)), agg[s][0], ton(agg[s][1])] for s in ss if is_imp(s)], (1, 2))}
<p class="note">{NOTE}</p>
"""
    write("/origin/", layout("/origin/", "산지별 농산물 도매시장 반입 현황 — 시·도별 출하 품목", "경북·전남·강원 등 산지(시·도)별 도매시장 출하 품목과 낙찰가.", body, None, [("홈", "/"), ("산지별", "/origin/")]), "0.6")

# ───────────────────────── 순위 ─────────────────────────
def movers():
    out = []
    for k, i in ITEMS.items():
        if i["d1"] is None or i["ld"] != ASOF or i["cur"][1] < 3000 or i["cur"][0] < 15: continue
        pv = ITEM[k][i["ds"][-2]]
        if pv[1] < 3000: continue
        out.append((k, i))
    return out
def page_rank(slug, title, h1, lead, rows, heads, fmt, desc):
    path = "/rank/%s/" % slug
    body = f"""
<div class="page-head"><h1>{h1}</h1><p>{ASOF_NOTE}</p></div>
<p class="lead">{lead}</p>
{ad()}
{table(heads, [[str(i + 1)] + fmt(x) for i, x in enumerate(rows)], tuple(range(2, len(heads))))}
<p class="note">{NOTE} 거래량 3톤 미만이거나 직전 경매일 거래가 없는 품목은 순위에서 제외했습니다.</p>
{chips([("가격 순위 전체", "/rank/"), ("품목별 시세", "/item/")])}
"""
    write(path, layout(path, title, desc, body, None, [("홈", "/"), ("가격 순위", "/rank/"), (h1.split(" — ")[0], path)]), "0.7")
def ranks():
    M = movers(); up = sorted(M, key=lambda x: -x[1]["d1"])[:50]; dn = sorted(M, key=lambda x: x[1]["d1"])[:50]
    fm = lambda x: [ilink(x[0]), kw(x[1]["px"]), kw(x[1]["prev"]), pcts(x[1]["d1"]), ton(x[1]["cur"][1])]
    H = ["순위", "품목", "평균 낙찰가(kg)", "직전 경매일", "등락", "거래량"]
    if up: page_rank("rise", "도매시장 가격 급등 품목 TOP 50 — 전 경매일 대비 (%s)" % kd(ASOF), "도매시장 가격 급등 품목 TOP 50 — 전 경매일 대비", "%s 경매에서 전 경매일보다 kg당 낙찰가가 가장 많이 오른 품목은 %s(%s)이며 다음은 %s, %s입니다." % (kd(ASOF), esc(iname(up[0][0])), pcts(up[0][1]["d1"], True), esc(iname(up[1][0])) if len(up) > 1 else "-", esc(iname(up[2][0])) if len(up) > 2 else "-"), up, H, fm, "전 경매일 대비 도매 낙찰가가 가장 많이 오른 품목 TOP 50 (%s 기준)." % kd(ASOF))
    if dn: page_rank("fall", "도매시장 가격 급락 품목 TOP 50 — 전 경매일 대비 (%s)" % kd(ASOF), "도매시장 가격 급락 품목 TOP 50 — 전 경매일 대비", "%s 경매에서 전 경매일보다 kg당 낙찰가가 가장 많이 내린 품목은 %s(%s)이며 다음은 %s, %s입니다." % (kd(ASOF), esc(iname(dn[0][0])), pcts(dn[0][1]["d1"], True), esc(iname(dn[1][0])) if len(dn) > 1 else "-", esc(iname(dn[2][0])) if len(dn) > 2 else "-"), dn, H, fm, "전 경매일 대비 도매 낙찰가가 가장 많이 내린 품목 TOP 50 (%s 기준)." % kd(ASOF))
    cur = [(k, i) for k, i in ITEMS.items() if i["ld"] == ASOF]
    vol = sorted(cur, key=lambda x: -x[1]["cur"][1])[:50]
    page_rank("volume", "도매시장 거래량 많은 품목 TOP 50 (%s)" % kd(ASOF), "도매시장 거래량 많은 품목 TOP 50", "%s 경매에서 거래량이 가장 많은 품목은 %s(%s)이며 다음은 %s, %s입니다." % (kd(ASOF), esc(iname(vol[0][0])), ton(vol[0][1]["cur"][1]), esc(iname(vol[1][0])), esc(iname(vol[2][0]))), vol, ["순위", "품목", "거래량", "평균 낙찰가(kg)", "전 경매일 대비"], lambda x: [ilink(x[0]), ton(x[1]["cur"][1]), kw(x[1]["px"]), pcts(x[1]["d1"])], "도매시장 경매 거래량이 많은 품목 TOP 50 (%s 기준)." % kd(ASOF))
    big = [x for x in cur if x[1]["cur"][1] >= 3000]
    ex = sorted(big, key=lambda x: -x[1]["px"])[:50]; ch = sorted(big, key=lambda x: x[1]["px"])[:50]
    page_rank("expensive", "도매시장 kg당 비싼 품목 TOP 50 (%s)" % kd(ASOF), "도매시장 kg당 비싼 품목 TOP 50", "%s 경매에서 kg당 평균 낙찰가가 가장 높은 품목은 %s(%s)입니다." % (kd(ASOF), esc(iname(ex[0][0])), kw(ex[0][1]["px"])), ex, ["순위", "품목", "평균 낙찰가(kg)", "거래량", "전 경매일 대비"], lambda x: [ilink(x[0]), kw(x[1]["px"]), ton(x[1]["cur"][1]), pcts(x[1]["d1"])], "kg당 낙찰가가 높은 품목 TOP 50 (%s 기준)." % kd(ASOF))
    page_rank("cheap", "도매시장 kg당 저렴한 품목 TOP 50 (%s)" % kd(ASOF), "도매시장 kg당 저렴한 품목 TOP 50", "%s 경매에서 kg당 평균 낙찰가가 가장 낮은 품목은 %s(%s)입니다." % (kd(ASOF), esc(iname(ch[0][0])), kw(ch[0][1]["px"])), ch, ["순위", "품목", "평균 낙찰가(kg)", "거래량", "전 경매일 대비"], lambda x: [ilink(x[0]), kw(x[1]["px"]), ton(x[1]["cur"][1]), pcts(x[1]["d1"])], "kg당 낙찰가가 낮은 품목 TOP 50 (%s 기준)." % kd(ASOF))
    body = f"""
<div class="page-head"><h1>도매시장 가격 순위</h1><p>{ASOF_NOTE}</p></div>
<p class="lead">공영도매시장 경매 낙찰가를 기준으로 가격이 오르거나 내린 품목, 거래량이 많은 품목, kg당 값이 높고 낮은 품목을 매 경매일 갱신합니다.</p>
{ad()}
<div class="card-grid">
<a class="card" href="/rank/rise/"><b>📈 급등 품목</b><span>전 경매일 대비 상승 TOP 50</span></a>
<a class="card" href="/rank/fall/"><b>📉 급락 품목</b><span>전 경매일 대비 하락 TOP 50</span></a>
<a class="card" href="/rank/volume/"><b>🚛 거래량 TOP</b><span>가장 많이 거래된 품목</span></a>
<a class="card" href="/rank/expensive/"><b>💎 kg당 비싼 품목</b><span>낙찰가 높은 순</span></a>
<a class="card" href="/rank/cheap/"><b>🥔 kg당 저렴한 품목</b><span>낙찰가 낮은 순</span></a>
</div>
<p class="note">{NOTE}</p>
"""
    write("/rank/", layout("/rank/", "도매시장 가격 순위 — 급등·급락·거래량 TOP 50", "공영도매시장 경매 낙찰가 급등·급락 품목, 거래량·kg당 가격 순위 (%s 기준)." % kd(ASOF), body, None, [("홈", "/"), ("가격 순위", "/rank/")]), "0.8")

# ───────────────────────── 홈 · 안내 ─────────────────────────
def page_home():
    M = movers(); up = sorted(M, key=lambda x: -x[1]["d1"])[:5]; dn = sorted(M, key=lambda x: x[1]["d1"])[:5]
    cur = [(k, i) for k, i in ITEMS.items() if i["ld"] == ASOF]; vol = sorted(cur, key=lambda x: -x[1]["cur"][1])[:10]
    rows = lambda L: [[ilink(k), kw(i["px"]), pcts(i["d1"]), ton(i["cur"][1])] for k, i in L]
    tot_n = sum(m["cur"][0] for m in MKTS.values() if m["ld"] == ASOF); tot_u = sum(m["cur"][1] for m in MKTS.values() if m["ld"] == ASOF)
    body = f"""
<div class="hero"><h1>🥬 오늘의 도매시장 시세 — 배추·사과·양파 경매 낙찰가</h1><p>전국 {len(MKTS)}개 공영도매시장 · {len(ITEMS)}개 품목 · {kd(ASOF)} 경매 기준</p>
<div class="today-box"><div><small>경매일</small><b>{kd(ASOF)}</b></div><div><small>거래 건수</small><b>{"{:,}".format(tot_n)}건</b></div><div><small>거래량</small><b>{ton(tot_u)}</b></div></div></div>
{ad()}
<div class="card-grid">
<a class="card" href="/item/"><b>🥬 품목별 시세</b><span>{len(ITEMS)}개 품목 kg당 낙찰가</span></a>
<a class="card" href="/market/"><b>🏪 시장별 시세</b><span>가락·엄궁 등 {len(MKTS)}개 시장</span></a>
<a class="card" href="/rank/"><b>📊 가격 순위</b><span>급등·급락·거래량</span></a>
<a class="card" href="/category/"><b>🗂️ 분류별</b><span>엽경채류·과일류 등</span></a>
<a class="card" href="/origin/"><b>🚚 산지별</b><span>시·도별 출하 품목</span></a>
</div>
<h2 class="group-title">📈 전 경매일보다 많이 오른 품목 <small><a href="/rank/rise/">더 보기</a></small></h2>{table(['품목', '낙찰가(kg)', '등락', '거래량'], rows(up), (1, 2, 3))}
<h2 class="group-title">📉 전 경매일보다 많이 내린 품목 <small><a href="/rank/fall/">더 보기</a></small></h2>{table(['품목', '낙찰가(kg)', '등락', '거래량'], rows(dn), (1, 2, 3))}
<h2 class="group-title">🚛 거래량 많은 품목 TOP 10 <small><a href="/rank/volume/">더 보기</a></small></h2>{table(['품목', '낙찰가(kg)', '등락', '거래량'], rows(vol), (1, 2, 3))}
<p class="lead">우아도매시장은 농림축산식품부·한국농수산식품유통공사의 전국 공영도매시장 실시간 경매정보를 매일 새벽 받아 품목·시장·산지별로 정리한 사이트입니다. 가격은 kg당 평균 낙찰가이며 소매가가 아닙니다. 자세한 기준은 <a href="/about/">데이터 설명</a>을 참고하세요.</p>
"""
    fq = [("도매시장 시세는 언제 갱신되나요?", "경매가 열린 날의 낙찰 내역을 다음 날 새벽에 받아 사이트를 갱신합니다. 일요일 등 휴장일에는 새 자료가 없습니다."), ("도매 낙찰가와 마트 가격은 같은가요?", "다릅니다. 도매 낙찰가는 경매에서 확정된 가격이며 소매가에는 유통·운송·소매 마진이 더해집니다."), ("어떤 시장의 자료인가요?", "전국 %d개 공영도매시장(서울가락·부산엄궁·대구북부 등)의 실시간 경매정보를 사용합니다." % len(MKTS))]
    write("/", layout("/", "우아도매시장 — 오늘의 도매시장 경매 시세 (배추·사과·양파)", "전국 %d개 공영도매시장 %d개 품목의 경매 낙찰가를 매일 갱신. 품목·시장·산지별 kg당 시세와 급등락 순위 (%s 기준)." % (len(MKTS), len(ITEMS), kd(ASOF)), body, fq), "1.0")
def page_about():
    body = f"""
<div class="page-head"><h1>데이터 설명</h1><p>정보의 출처와 한계</p></div>
<h2 class="group-title">📚 출처</h2><p class="lead">공공데이터포털의 ‘전국 공영도매시장 실시간 경매정보’(농림축산식품부·한국농수산식품유통공사)를 사용합니다. 경매 낙찰 한 건마다 도매시장·품목·산지·포장 단위·낙찰가·수량이 제공되며, 이 사이트는 이를 일 단위로 집계해 보여줍니다.</p>
<h2 class="group-title">🧮 계산 방법</h2><p class="lead">kg 단위로 포장된 거래만 사용해 낙찰가를 포장 중량으로 나눈 뒤 거래량 가중 평균(총 낙찰금액 ÷ 총 중량)으로 kg당 평균 낙찰가를 계산합니다. ‘전 경매일 대비’는 직전 경매일의 평균가와, ‘7경매일 평균 대비’는 그 이전 최대 7경매일 평균과 비교한 값입니다. 가격 순위는 거래량이 3톤 미만인 품목을 제외합니다.</p>
<h2 class="group-title">🗓️ 갱신과 이력</h2><p class="lead">매일 새벽 전날 경매분을 받아 누적합니다. 원천 API가 약 한 달 치만 제공하므로 이 사이트의 추이는 수집을 시작한 2026년 9월 말부터 쌓이며, 현재 {kd(DAYS[0])}부터 {kd(DAYS[-1])}까지 {len(DAYS)}경매일 자료입니다.</p>
<h2 class="group-title">⚠️ 한계</h2><p class="lead">낙찰가는 품질·등급·규격·산지에 따라 크게 달라지며 평균은 구성 변화의 영향을 받습니다. 소매가·마트 가격과 다르고 투자·구매 판단의 근거가 될 수 없습니다. 휴장일에는 새 자료가 없습니다.</p>
<h2 class="group-title">📬 문의·정정</h2><p class="lead">오류 제보는 <a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a> 으로 보내 주세요.</p>
"""
    write("/about/", layout("/about/", "데이터 설명 — 출처와 계산 방법", "우아도매시장 데이터 출처(공영도매시장 실시간 경매정보)와 kg당 낙찰가 계산 방법, 한계.", body, None, [("홈", "/"), ("데이터 설명", "/about/")]), "0.5")
def page_privacy():
    body = """
<div class="page-head"><h1>개인정보처리방침</h1><p>우아도매시장</p></div>
<h3>수집하는 정보</h3><p class="lead">이 사이트는 회원가입이 없으며 이름·연락처 등 개인정보를 수집하지 않습니다. 방문 통계를 위해 Google Analytics가 쿠키로 익명 이용 정보를 수집합니다.</p>
<h3>광고</h3><p class="lead">Google AdSense가 쿠키를 사용해 광고를 표시할 수 있습니다. 개인 맞춤 광고는 <a href="https://adssettings.google.com" rel="nofollow">Google 광고 설정</a>에서 해제할 수 있습니다.</p>
<h3>쿠팡 파트너스</h3><p class="lead">일부 페이지에는 쿠팡 파트너스 활동의 일환으로 광고가 포함되어 있으며 이에 따른 수수료를 제공받을 수 있습니다.</p>
<h3>문의</h3><p class="lead"><a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a></p>
<p class="note">최종 수정일: 2026년 10월 28일</p>
"""
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아도매시장 개인정보처리방침", body, None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)

def make_og():
    f = ROOT / "assets" / "og-image.png"
    if f.exists(): return
    try: from PIL import Image, ImageDraw, ImageFont
    except Exception: return
    im = Image.new("RGB", (1200, 630), (21, 128, 61)); dr = ImageDraw.Draw(im)
    def font(sz):
        for n_ in ("malgunbd.ttf", "malgun.ttf", "NanumGothicBold.ttf"):
            try: return ImageFont.truetype(n_, sz)
            except Exception: pass
        return ImageFont.load_default()
    dr.rounded_rectangle((90, 90, 1110, 540), 40, fill=(255, 255, 255))
    dr.text((150, 150), "우아도매시장", font=font(110), fill=(20, 83, 45))
    dr.text((150, 310), "공영도매시장 경매 시세", font=font(54), fill=(31, 41, 55))
    dr.text((150, 390), "품목 · 시장 · 산지별 낙찰가", font=font(54), fill=(31, 41, 55))
    dr.text((150, 480), "wooamarket.wooahouse.com", font=font(34), fill=(107, 114, 128))
    im.save(f)

def main():
    t0 = time.time(); make_og()
    if not DAYS: sys.exit("data/daily 비어 있음")
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)
    for nf in ROOT.glob("naver*.html"): shutil.copy(nf, OUT / nf.name)
    for k in ITEMS: page_item(k)
    for k in SCS: page_sc(k)
    for k in MKTS: page_market(k)
    for k in MIS: page_mi(k)
    for c in CATS: page_cat(c)
    for s in SIDOS: page_sido(s)
    for k in OIS: page_oi(k)
    hub_market(); hub_cat(); hub_item(); hub_origin(); ranks()
    page_home(); page_about(); page_privacy()
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), ASOF, pr_) for p, pr_ in WRITTEN)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooamarket.wooahouse.com\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1></div><div class="chips"><a class="chip" href="/">홈</a><a class="chip" href="/item/">품목별 시세</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("pages", len(WRITTEN), "days", len(DAYS), "items", len(ITEMS), "sc", len(SCS), "mkts", len(MKTS), "mi", len(MIS), "elapsed", round(time.time() - t0), "s")

if __name__ == "__main__":
    main()
