# 출처

- 원본: https://github.com/addyosmani/agent-skills/tree/main/skills/interview-me (MIT License, Copyright (c) 2025 Addy Osmani — 같은 폴더의 `LICENSE`)
- 가져온 버전: 커밋 `8c99fa36d90068c82d547f7c12a9d67a3e95f4ee` (2026-11-18)
- 이 저장소에서 바꾼 점: Step 6과 Output·Red Flags·Verification의 관련 줄
  - 원본: 의도 확정 후 저장을 '제안'만 하고 도구 없이 턴 종료
  - 변경: 의도 확정 즉시 `docs/intent/YYYY-MM-DD-<주제>.md`에 Why·완료 기준·Out of scope를 저장한 뒤 턴 종료 (저장 외 도구 사용 금지)
- 'When NOT to use'와 'Loading Constraints'
  - 원본: 단순 질문·기계적 작업·속도 요청·비대화형(예약 실행 등)에는 쓰지 않음
  - 변경: 소유자 요청으로 **예외 없이 적용**. 비대화형이면 첫 질문만 남기고 작업은 시작하지 않은 채 답을 기다림
