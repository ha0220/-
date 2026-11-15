#!/usr/bin/env python3
"""특정 날짜에 개정·신설된 조문 목록을 뽑는다 (본문 기준).
사용: python3 changes.py 소득세법 "2025. 12. 23."   → 그날 개정·신설된 조문"""
import re, sys, os
name, date = sys.argv[1].replace(' ', '_'), sys.argv[2]
t = open(os.path.join(os.path.dirname(__file__), '..', 'laws', name + '.txt'), encoding='utf-8').read()
body = t.split('\n부 칙')[0] if '\n부 칙' in t else t
cur, out = None, {}
for line in body.split('\n'):
    m = re.match(r'(제\d+조(?:의\d+)?)\(([^)]*)\)', line)
    if m: cur = f'{m.group(1)}({m.group(2)})'
    if cur and date in line:
        kind = '신설' if re.search(r'(본조신설|신설)[^>\]]*' + re.escape(date), line) else '개정'
        out[cur] = '신설' if out.get(cur) == '신설' or kind == '신설' else '개정'
for k, v in out.items(): print(f'{v}\t{k}')
