#!/bin/bash
# macOS: Finder 에서 더블클릭. tkinter 가 없으면 터미널 모드로 자동 전환된다.
cd "$(dirname "$0")" || exit 1
python3 briefing_app.py
