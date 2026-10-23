# 한국 경제 정책 시장 브리핑 — 버튼 한 번에

매일 아침 브리핑을 **버튼 한 번**으로 만드는 프로그램입니다.
`ROUTINE_PROMPT.md` 의 루틴을 내 컴퓨터의 Claude Code 로 실행해 `briefings/YYYY-MM-DD.html` 을 만들고 브라우저로 엽니다.

## 한 번만 준비
1. Python 3 설치 (Windows는 python.org 설치 시 `Add python.exe to PATH` 체크)
2. Claude Code 설치 후 터미널에서 `claude` 를 한 번 실행해 로그인

## 매일 쓰는 법
- **Windows**: `run_briefing.bat` 더블클릭
- **macOS**: `run_briefing.command` 더블클릭
- 창이 뜨면 **☀ 오늘 브리핑 만들기** 를 누르고 기다리면 됩니다 (보통 10~20분, 웹 검색 20회 이상).
  완료되면 브라우저가 자동으로 열립니다. 이미 오늘 파일이 있으면 버튼이 **다시 만들기** 로 바뀝니다.
- 터미널 모드: `python briefing_app.py --no-gui` (창이 안 뜨는 환경에서는 자동 전환)

## 동작 방식
| 단계 | 내용 |
|---|---|
| 프롬프트 | `ROUTINE_PROMPT.md` 의 `---` 아래 본문을 그대로 사용 (고치면 다음 실행부터 반영) |
| 디자인 | `briefings/` 의 가장 최근 브리핑 HTML을 템플릿으로 재사용 |
| 검증 | 본문이 5,000자 미만이면 자동으로 한 번 보강 |
| 저장 | 성공했을 때만 `briefings/YYYY-MM-DD.html` 로 교체 (실패해도 기존 파일은 그대로) |

## 알아둘 점
- Claude Code 사용량(구독 한도)을 씁니다. 웹 검색을 많이 하므로 한 번에 꽤 소모됩니다.
- 클라우드 루틴과 달리 Artifact 게시·푸시 알림은 하지 않고 로컬 HTML만 만듭니다.
- 검색 결과로 확인 못 한 숫자는 "확인 필요"로 표시됩니다. 투자 판단 전 원 출처를 확인하세요.
