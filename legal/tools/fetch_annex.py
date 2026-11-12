#!/usr/bin/env python3
"""법령의 [별표](서식 제외) PDF를 내려받아 텍스트로 저장한다. 표·기준액이 별표에 있는 경우가 많다.
사용: python3 fetch_annex.py "국민건강보험법 시행규칙" ["1의2" ...]   (번호 생략 시 전체 별표)
결과: legal/annex/<법령명>_별표<번호>.txt"""
import re, sys, os, html, subprocess, urllib.parse, tempfile, datetime, time
OUT = os.path.join(os.path.dirname(__file__), '..', 'annex')

def curl(url, data=None, out=None):
    cmd = ['curl', '-s', '-m', '120', url] + (['-X', 'POST', '--data', data] if data else []) + (['-o', out] if out else [])
    return subprocess.run(cmd, capture_output=True).stdout.decode('utf-8', 'replace')

def main(name, wanted):
    for _ in range(4):
        p = curl('https://www.law.go.kr/법령/' + urllib.parse.quote(name))
        m = re.search(r'lsiSeq=(\d+)&amp;chrClsCd=(\d+).*?efYd=(\d*)', p)
        if m: break
        time.sleep(3)
    seq, chr_, ef = m.groups()
    body = curl('https://www.law.go.kr/LSW/lsInfoR.do', f'lsiSeq={seq}&chrClsCd={chr_}&urlMode=lsInfoP&efYd={ef}&ancYnChk=0&efGubun=Y')
    found = re.findall(r'\[별표 ([0-9의 ]+)\]\s*([^<]*?)\s*</a>\s*(?:<a href="flDownload\.do\?gubun=&amp;flSeq=\d+[^"]*"[^>]*>\s*<img alt="HWP[^>]*>\s*</a>\s*)?<a href="flDownload\.do\?gubun=&amp;flSeq=(\d+)&amp;bylClsCd=\d+"[^>]*>\s*<img alt="PDF', body)
    seen = set()
    for no, title, fl in found:
        no = no.replace(' ', '')
        if (wanted and no not in wanted) or no in seen: continue
        seen.add(no)
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            curl(f'https://www.law.go.kr/LSW/flDownload.do?gubun=&flSeq={fl}&bylClsCd=110201', out=f.name)
            txt = subprocess.run(['pdftotext', '-layout', f.name, '-'], capture_output=True).stdout.decode('utf-8', 'replace')
        fn = os.path.join(OUT, f"{name.replace(' ', '_')}_별표{no}.txt")
        open(fn, 'w', encoding='utf-8').write(
            f'# {name} [별표 {no}] {html.unescape(title)}\n# 출처: 국가법령정보센터 PDF flSeq={fl} 시행일={ef} 수집일={datetime.date.today()}\n\n' + txt)
        print('OK', name, '별표', no, len(txt), flush=True)
    if not seen: print('NONE', name, wanted)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    main(sys.argv[1], set(sys.argv[2:]))
