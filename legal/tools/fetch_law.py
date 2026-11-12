#!/usr/bin/env python3
"""국가법령정보센터(law.go.kr)에서 현행 법령 본문을 받아 텍스트로 저장한다.
사용: python3 fetch_law.py "소득세법" "국민건강보험법 시행령" ...
결과: legal/laws/<법령명>.txt (첫 줄에 출처·시행일·lsiSeq 기록)"""
import time, re, sys, os, html, subprocess, urllib.parse, datetime
OUT = os.path.join(os.path.dirname(__file__), '..', 'laws')

def curl(url, data=None):
    cmd = ['curl', '-s', '-m', '120', url]
    if data: cmd += ['-X', 'POST', '--data', data]
    return subprocess.run(cmd, capture_output=True).stdout.decode('utf-8', 'replace')

def fetch(name):
    m = None
    for _ in range(4):
        p = curl('https://www.law.go.kr/법령/' + urllib.parse.quote(name))
        m = re.search(r'lsiSeq=(\d+)&amp;chrClsCd=(\d+).*?efYd=(\d*)', p)
        if m: break
        time.sleep(3)
    if not m:
        return f'FAIL(resolve) {name}'
    seq, chr_, ef = m.groups()
    body = curl('https://www.law.go.kr/LSW/lsInfoR.do',
                f'lsiSeq={seq}&chrClsCd={chr_}&urlMode=lsInfoP&efYd={ef}&ancYnChk=0&efGubun=Y')
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', body, flags=re.S)
    # 표·산식은 이미지로 제공되고 alt 속성에 내용이 들어 있으므로 텍스트로 살린다
    def img(m):
        a = m.group(1).replace('@@LATEX@@', '').replace('@@/LATEX@@', '')
        if a in ('조문체계도버튼', '연혁') or 'button' in m.group(0):
            return ''
        return '\n[표/산식]\n' + a + '\n[/표/산식]\n'
    t = re.sub(r'<img[^>]*?alt="([^"]*)"[^>]*>', img, t, flags=re.S)
    t = re.sub(r'<br\s*/?>|</p>|</div>|</li>|</tr>', '\n', t)
    t = re.sub(r'<(?:"[^"]*"|\'[^\']*\'|[^\'">])*>', '', t)  # 속성 안의 > 까지 고려
    t = html.unescape(t)
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    t = re.sub(r' *\n *', '\n', t)
    t = re.sub(r'\n{2,}', '\n', t).strip()
    if '제1조' not in t:
        return f'FAIL(body) {name}'
    head = (f'# {name}\n# 출처: 국가법령정보센터 https://www.law.go.kr/법령/{name}\n'
            f'# lsiSeq={seq} 시행일(efYd)={ef} 수집일={datetime.date.today()}\n\n')
    fn = os.path.join(OUT, name.replace(' ', '_') + '.txt')
    open(fn, 'w', encoding='utf-8').write(head + t + '\n')
    return f'OK {name} efYd={ef} chars={len(t)}'

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for n in sys.argv[1:]:
        print(fetch(n), flush=True)
