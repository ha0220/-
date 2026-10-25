#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""보유 종목 현재가 조회 도우미

장부(주식매매장부.html)의 백업 파일(.json)에서 보유 종목을 읽어 현재가를 조회하고,
장부의 "현재가 붙여넣기"가 읽을 수 있는 `종목명<탭>현재가` 파일로 저장합니다.

- 파이썬 3.8 이상, 추가 설치 없음(표준 라이브러리만 사용)
- 백업 파일에는 금액이 들어 있지만, 외부로는 종목 이름·코드만 보냅니다(수량·금액·계좌는 보내지 않음).
- 시세 출처는 네이버 증권·야후 파이낸스의 비공식 주소입니다. 주소나 형식이 바뀌면 조회가 실패할 수 있고,
  그럴 때는 `--test`로 어느 출처가 되는지 확인하세요.
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODES_FILE = HERE / "종목코드.csv"
OUT_DIR = HERE / "시세결과"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CODE_RE = re.compile(r"^[0-9A-Za-z]{6}$")
SOURCES = ("naver", "yahoo")


class FetchError(Exception):
    pass


def fetch_text(url, timeout=10, retries=1):
    """주소를 읽어 문자열로 돌려준다. 실패하면 사람이 읽을 수 있는 메시지로 FetchError."""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/plain,*/*",
                                                       "Referer": "https://finance.naver.com/"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            for enc in ("utf-8", "euc-kr"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = FetchError(f"HTTP {e.code} ({e.reason})")
            if e.code in (404, 400):  # 다시 해도 같은 결과
                break
        except urllib.error.URLError as e:
            last = FetchError(f"접속 실패: {e.reason}")
        except Exception as e:  # 시간 초과 등
            last = FetchError(f"{type(e).__name__}: {e}")
        time.sleep(0.5)
    raise last


def norm(s):
    return re.sub(r"\s+", "", str(s)).lower()


def to_num(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        t = v.replace(",", "").replace("원", "").strip()
        try:
            return float(t)
        except ValueError:
            return None
    return None


def fmt_price(p):
    return str(int(p)) if float(p).is_integer() else f"{p:.2f}"


# ---------- 백업 파일 / 보유 종목 ----------

def candidate_dirs():
    home = Path.home()
    dirs = [HERE, Path.cwd(), home / "Downloads", home / "다운로드", home / "Desktop", home / "바탕 화면",
            home / "Documents", home / "문서", home / "OneDrive" / "Downloads", home / "OneDrive" / "다운로드"]
    seen, out = set(), []
    for d in dirs:
        if d not in seen and d.is_dir():
            seen.add(d)
            out.append(d)
    return out


def find_backup(explicit=None):
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise SystemExit(f"백업 파일을 찾을 수 없습니다: {p}")
        return p
    best = None
    for d in candidate_dirs():
        for f in d.glob("매매장부_백업_*.json"):
            if best is None or f.stat().st_mtime > best.stat().st_mtime:
                best = f
    return best


def held_names(db):
    """거래를 합산해 지금 보유 중인(수량 > 0) 종목명을 처음 나온 순서대로 돌려준다."""
    qty = {}
    for t in db.get("trades", []):
        n = t.get("name")
        if not n:
            continue
        q = float(t.get("qty", 0) or 0)
        qty[n] = qty.get(n, 0.0) + (q if t.get("side") == "buy" else -q)
    return [n for n, q in qty.items() if q > 1e-9]


# ---------- 종목코드 ----------

def load_codes():
    codes = {}
    if CODES_FILE.exists():
        with open(CODES_FILE, encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].strip() and not row[0].lstrip().startswith("#"):
                    code = row[1].strip()
                    if code:
                        codes[norm(row[0])] = (row[0].strip(), code)
    return codes


def save_codes(codes):
    with open(CODES_FILE, "w", encoding="utf-8-sig", newline="") as f:
        f.write("# 종목명,종목코드(6자리) — 한 줄에 한 종목. 자동으로 못 찾은 종목은 코드를 직접 적어 주세요.\n")
        w = csv.writer(f)
        for _, (name, code) in codes.items():
            w.writerow([name, code])


def add_pending_rows(names, codes):
    """코드를 못 찾은 종목을 `이름,` 줄로 종목코드.csv에 한 번만 적어 둔다 (사용자가 코드만 채우면 됨)."""
    if not CODES_FILE.exists():
        save_codes(codes)
    present = set()
    with open(CODES_FILE, encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if row and row[0].strip() and not row[0].lstrip().startswith("#"):
                present.add(norm(row[0]))
    with open(CODES_FILE, "a", encoding="utf-8", newline="") as f:
        for n in names:
            if norm(n) not in present:
                csv.writer(f).writerow([n, ""])
                present.add(norm(n))


def walk_candidates(o):
    """JSON 어디에 있든 (이름, 코드) 쌍을 찾아낸다 — 응답 모양이 조금 달라도 견디도록."""
    if isinstance(o, dict):
        name = o.get("name") or o.get("nm") or o.get("stockName") or o.get("itemName")
        code = o.get("code") or o.get("cd") or o.get("itemCode") or o.get("symbolCode")
        if isinstance(name, str) and isinstance(code, str):
            yield name, code
        for v in o.values():
            yield from walk_candidates(v)
    elif isinstance(o, list):
        if (len(o) >= 2 and isinstance(o[0], list) and isinstance(o[1], list) and o[0] and o[1]
                and isinstance(o[0][0], str) and isinstance(o[1][0], str)):
            yield o[0][0], o[1][0]
        for v in o:
            yield from walk_candidates(v)


def resolve_code(name, fetch):
    """종목명으로 코드를 찾는다. 이름이 정확히 같은 결과만 받아들이고, 비슷한 이름으로 추측하지 않는다."""
    q = urllib.parse.quote(name)
    urls = [
        f"https://ac.stock.naver.com/ac?q={q}&target=stock,etf",
        f"https://ac.finance.naver.com/ac?q={q}&q_enc=utf-8&st=111&frm=stock&r_format=json&r_enc=utf-8&r_unicode=0&t_koreng=1&r_lt=111",
    ]
    errors = []
    for u in urls:
        try:
            data = json.loads(fetch(u))
        except (FetchError, ValueError) as e:
            errors.append(str(e))
            continue
        hits = {c for n, c in walk_candidates(data) if norm(n) == norm(name) and CODE_RE.match(c)}
        if len(hits) == 1:
            return hits.pop(), None
        if len(hits) > 1:
            return None, f"같은 이름의 코드가 여러 개입니다: {', '.join(sorted(hits))}"
    return None, (errors[-1] if errors else "검색 결과에 이름이 정확히 같은 종목이 없습니다")


# ---------- 현재가 조회 ----------

def walk_dicts(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk_dicts(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_dicts(v)


def price_naver_polling(codes, fetch):
    url = "https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:" + ",".join(codes)
    data = json.loads(fetch(url))
    out = {}
    for d in walk_dicts(data):
        if "cd" in d and "nv" in d:
            p = to_num(d["nv"])
            if p and p > 0:
                out[str(d["cd"])] = p
    if not out:
        raise FetchError("응답에서 현재가(nv)를 찾지 못했습니다")
    return out


def price_naver_mobile(code, fetch):
    last = None
    for u in (f"https://m.stock.naver.com/api/stock/{code}/basic", f"https://m.stock.naver.com/api/etf/{code}/basic",
              f"https://api.stock.naver.com/stock/{code}/basic"):
        try:
            data = json.loads(fetch(u))
        except (FetchError, ValueError) as e:
            last = e
            continue
        for key in ("closePrice", "currentPrice", "nowPrice", "stockPrice"):
            for d in walk_dicts(data):
                p = to_num(d.get(key))
                if p and p > 0:
                    return p
        last = FetchError("응답에서 현재가(closePrice)를 찾지 못했습니다")
    raise last or FetchError("조회 실패")


def price_yahoo(code, fetch):
    last = None
    for suffix in (".KS", ".KQ"):
        u = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}{suffix}?interval=1d&range=1d"
        try:
            data = json.loads(fetch(u))
            res = data["chart"]["result"][0]["meta"]
            p = to_num(res.get("regularMarketPrice"))
            if p and p > 0:
                return p
            last = FetchError("응답에서 regularMarketPrice를 찾지 못했습니다")
        except (FetchError, ValueError, KeyError, IndexError, TypeError) as e:
            last = e if isinstance(e, FetchError) else FetchError(f"응답 형식이 다릅니다 ({type(e).__name__})")
    raise last or FetchError("조회 실패")


def get_prices(codes, sources, fetch, log=print, pause=0.25):
    """코드 → (현재가, 출처). 출처를 순서대로 시도하고 실패하면 다음으로 넘어간다."""
    got, errs = {}, {c: [] for c in codes}
    todo = list(codes)
    if "naver" in sources and todo:
        try:
            res = price_naver_polling(todo, fetch)
            for c in todo:
                if c in res:
                    got[c] = (res[c], "naver")
        except (FetchError, ValueError) as e:
            for c in todo:
                errs[c].append(f"네이버(일괄): {e}")
        todo = [c for c in todo if c not in got]
        for c in todo:
            try:
                got[c] = (price_naver_mobile(c, fetch), "naver")
            except FetchError as e:
                errs[c].append(f"네이버(개별): {e}")
            time.sleep(pause)
        todo = [c for c in todo if c not in got]
    if "yahoo" in sources and todo:
        for c in todo:
            try:
                got[c] = (price_yahoo(c, fetch), "yahoo")
            except FetchError as e:
                errs[c].append(f"야후: {e}")
            time.sleep(pause)
    return got, {c: e for c, e in errs.items() if c not in got}


# ---------- 진단 ----------

def run_test(fetch):
    code, name = "005930", "삼성전자"
    print(f"[진단] {name}({code}) 현재가를 출처별로 조회해 봅니다.\n")
    tests = [
        ("네이버 실시간(일괄)", lambda: price_naver_polling([code], fetch)[code]),
        ("네이버 모바일(개별)", lambda: price_naver_mobile(code, fetch)),
        ("야후 파이낸스", lambda: price_yahoo(code, fetch)),
    ]
    ok = 0
    for label, fn in tests:
        try:
            print(f"  ✅ {label}: {fmt_price(fn())}원")
            ok += 1
        except Exception as e:
            print(f"  ❌ {label}: {e}")
    print("\n[진단] 종목명 → 종목코드 검색도 확인합니다.")
    code_found, why = resolve_code(name, fetch)
    print(f"  ✅ '{name}' → {code_found}" if code_found else f"  ❌ '{name}' 코드 검색 실패: {why}")
    print("\n" + ("한 곳 이상 정상입니다. 이 PC에서는 조회 도우미를 쓸 수 있습니다." if ok else
                  "세 곳 모두 실패했습니다. 인터넷 연결·방화벽·보안 프로그램을 확인하거나, 장부의 '현재가 붙여넣기'를 쓰세요."))
    if not code_found:
        print("코드 검색만 실패했다면 종목코드.csv에 `종목명,코드`를 직접 적으면 됩니다.")
    return 0 if ok else 1


# ---------- 메인 ----------

def main(argv=None, fetch=fetch_text):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="보유 종목 현재가 조회 → 장부의 '현재가 붙여넣기' 파일 생성")
    ap.add_argument("backup", nargs="?", help="장부 백업 파일(.json). 생략하면 다운로드·바탕화면 등에서 가장 최근 것을 찾습니다")
    ap.add_argument("--names", help="백업 파일 없이 종목명을 직접 지정 (쉼표로 구분)")
    ap.add_argument("--source", choices=("auto",) + SOURCES, default="auto", help="시세 출처 (기본: 자동 — 네이버 → 야후)")
    ap.add_argument("--out-dir", help=f"결과 저장 폴더 (기본: {OUT_DIR})")
    ap.add_argument("--test", action="store_true", help="이 PC에서 어느 시세 출처가 되는지 진단")
    args = ap.parse_args(argv)

    if args.test:
        return run_test(fetch)

    # 1) 조회할 종목
    if args.names:
        names = [n.strip() for n in args.names.split(",") if n.strip()]
        db = {}
        print(f"직접 지정한 종목 {len(names)}개")
    else:
        bk = find_backup(args.backup)
        if bk is None:
            print("장부 백업 파일(매매장부_백업_*.json)을 찾지 못했습니다.\n"
                  "장부에서 [💾 백업 저장]을 누르거나 오늘 마감을 한 뒤 다시 실행하세요. (파일 위치를 직접 줄 수도 있습니다)")
            return 2
        try:
            db = json.loads(bk.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"백업 파일을 읽지 못했습니다: {bk} ({e})")
            return 2
        names = held_names(db)
        print(f"백업 파일: {bk}  (수정 {datetime.fromtimestamp(bk.stat().st_mtime):%Y-%m-%d %H:%M})")
        print(f"보유 종목 {len(names)}개")
    if not names:
        print("조회할 보유 종목이 없습니다.")
        return 2

    # 2) 종목코드
    codes = load_codes()
    meta = db.get("meta", {}) if isinstance(db, dict) else {}
    name_code, unresolved, changed = {}, [], False
    for n in names:
        c = codes.get(norm(n), (None, None))[1] or (meta.get(n, {}) or {}).get("code")
        if not c:
            c, why = resolve_code(n, fetch)
            if c:
                codes[norm(n)] = (n, c)
                changed = True
                print(f"  종목코드 찾음: {n} → {c} (종목코드.csv에 저장)")
            else:
                unresolved.append((n, why))
                continue
        name_code[n] = c
    if changed:
        save_codes(codes)
    for n, why in unresolved:
        print(f"  ⚠ 종목코드를 찾지 못함: {n} — {why}")
    if unresolved:
        add_pending_rows([n for n, _ in unresolved], codes)
        print(f"  → {CODES_FILE.name} 파일을 열어 해당 종목 줄의 쉼표 뒤에 6자리 코드를 적고 다시 실행하세요.")
    if not name_code:
        return 1

    # 3) 현재가
    sources = SOURCES if args.source == "auto" else (args.source,)
    got, errs = get_prices(sorted(set(name_code.values())), sources, fetch)

    # 4) 저장
    lines, ok, fail = [], [], []
    for n in names:
        c = name_code.get(n)
        if c in got:
            p, src = got[c]
            lines.append(f"{n}\t{fmt_price(p)}")
            ok.append((n, c, p, src))
        elif c:
            fail.append((n, c, "; ".join(errs.get(c, [])) or "조회 실패"))
    print(f"\n조회 결과: 성공 {len(ok)}종목 / 실패 {len(fail)}종목"+(f" / 코드 미확인 {len(unresolved)}종목" if unresolved else ""))
    for n, c, p, src in ok:
        print(f"  {n} ({c}) {fmt_price(p)}원  [{src}]")
    for n, c, why in fail:
        print(f"  ⚠ {n} ({c}) 실패 — {why}")
    if not lines:
        print("\n현재가를 하나도 가져오지 못했습니다. `--test`로 진단해 보거나 장부의 '현재가 붙여넣기'를 쓰세요.")
        return 1

    out_dir = Path(args.out_dir) if args.out_dir else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    body = "\n".join(lines) + "\n"
    for fn in (f"시세_{stamp}.txt", "시세_최신.txt"):
        (out_dir / fn).write_text(body, encoding="utf-8")
    print(f"\n저장: {out_dir / '시세_최신.txt'}")
    print("장부 → 오늘 입력 탭 → 현재가 붙여넣기 → [📂 시세 파일 불러오기]로 이 파일을 고르세요.")
    return 0 if not (fail or unresolved) else 3


if __name__ == "__main__":
    sys.exit(main())
