#!/usr/bin/env python3
"""법령 본문에서 'YYYY년 12월 31일까지' 같은 일몰(적용기한) 조항을 조문별로 뽑는다.
사용: python3 sunset.py 조세특례제한법 2026   → 2026년 말에 끝나는 특례 목록"""
import re, sys, os
name, year = sys.argv[1].replace(' ', '_'), sys.argv[2]
t = open(os.path.join(os.path.dirname(__file__), '..', 'laws', name + '.txt'), encoding='utf-8').read()
body = t.split('\n부 칙')[0] if '\n부 칙' in t else t   # 본문만 (부칙 제외)
cur, seen = None, {}
for line in body.split('\n'):
    m = re.match(r'(제\d+조(?:의\d+)?)\(([^)]*)\)', line)
    if m: cur = f'{m.group(1)}({m.group(2)})'
    if cur and re.search(year + r'년 \d+월 \d+일까지', line):
        seen.setdefault(cur, 0); seen[cur] += 1
for k in seen: print(k)
