#!/usr/bin/env python3
"""저장된 법령 텍스트에서 조문 하나를 뽑아 출력한다.
사용: python3 article.py 소득세법 14   |  python3 article.py 소득세법 64의4"""
import re, sys, os
name, no = sys.argv[1].replace(' ', '_'), sys.argv[2]
t = open(os.path.join(os.path.dirname(__file__), '..', 'laws', name + '.txt'), encoding='utf-8').read()
art = '제' + no.replace('의', '조의', 1) if '의' in no else '제' + no + '조'
m = re.search(r'\n' + re.escape(art) + r'\(.*?(?=\n제\d+조(?:의\d+)?\(|\Z)', t, flags=re.S)
print(m.group(0).strip()[:int(sys.argv[3]) if len(sys.argv) > 3 else 6000] if m else 'NOT FOUND')
