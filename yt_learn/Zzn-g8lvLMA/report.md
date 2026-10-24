# AI로 데이터 분석할 때 결과를 믿는 법 (위임-점검 루프) — 따라 하기 정리

기준: 업로드일 **불명** · 확인일 2026-10-24 · 길이 약 7분 10초 · 영어 · https://www.youtube.com/watch?v=Zzn-g8lvLMA
영상(화면 표기): Anthropic Academy · "AI Fluency for nonprofits" · "Data analysis with AI" · 발표자 Zoe Ludwig(Claude Apps Education Lead) · Copyright 2025 GivingTuesday and Anthropic, CC BY-NC-SA 4.0
길: **B길** — 영상 접속이 "봇 확인"으로 막혀 자막·영상 파일을 못 받았다. 말은 제미나이가 소리로 받아 적은 영어 원문, 화면은 제미나이의 판독이다. **내가 직접 본 장면은 없다.**
모델: 전체 영상은 `gemini-3.5-flash`. 숫자 구간(03:15~03:50, 02:10~02:24)은 `gemini-3.5-flash` + `gemini-3.6-flash` 둘이 읽었다. `gemini-3-flash-preview` 는 이 영상에서 403 으로 실패했다.
한국어 번역은 제미나이가 붙인 것이라 틀린 곳이 있다(아래 표 1). **영어 원문을 기준으로 삼았다.**

## 결론

- **이 영상이 알려 주는 것:** AI에게 분석을 맡기기 전에, **내가 이미 답을 아는 과거 데이터**로 AI가 같은 답을 내는지 먼저 시험하라(위임 → 점검 → 고쳐서 다시). 같은 답을 못 내면 그 일은 맡기지 않는다.
- **따라 해도 되나: 그대로 가능, 단 개인정보 처리부터.** 방법은 단순하고 화면과 말이 잘 맞는다. 다만 데모의 파일에 이름·이메일·전화 열이 보이는 만큼, 올리기 전에 지워야 한다.
- **가장 큰 위험:** ① AI 답을 사실로 받아들이는 것. 영상 속 AI도 첫 답에서 중요한 것을 놓쳤다. ② 영상의 퍼센트 숫자(71.4%, 90% 등)는 **가상 데모 데이터의 결과**일 뿐 어디에도 적용되지 않는다. ③ 영상의 화면(모델 이름 등)은 2025년 판이다.

## 1. 말과 화면이 다른 곳 (먼저 본다)

| 시각 | 말 | 화면 | 어느 쪽을 믿나 |
|---|---|---|---|
| 01:24~01:40 | 영어 원문 "takes him **hours**" / 한국어 번역 "**수십 시간**" | 슬라이드 "This analysis takes **hours**." | **영어 원문·화면.** 한국어 번역이 과장했다 |
| 03:20~03:31 | "AI **correctly identified** the correlation between program attendance and job placement" | AI 답변 제목 "Attendance **Strongly** Predicts Success". 그런데 같은 답변 안에 "the overall statistical correlation is **weak** (r=0.055)" (두 모델 일치) | **화면을 같이 봐야 한다.** 말은 "맞게 짚었다"고 하지만, 화면의 AI 자신의 글이 헤드라인과 스스로 엇갈린다. 이 점이 이 영상의 점검 사례로 가장 좋다 `[해석]` |
| 03:55~04:05 | "AI **could help extract** [the enrollment date]" | AI: "I don't see an explicit enrollment date column… I can **infer** enrollment timing based on the attendance patterns" | **화면.** 없는 열을 "꺼내는" 게 아니라 **추정**한다. 04:05~04:28 에서 발표자도 "it'll try to **infer** them, which he doesn't want"라고 바로잡는다 |
| 02:10 / 03:15 | (말 없음) | 모델 이름: 대부분의 판독은 "Sonnet **4.5**", 03:15 구간에서만 두 판독이 "Sonnet **3.5**" | **확인 못 함.** 같은 화면에서 이름이 바뀔 이유가 없어 오독으로 보이나 확정은 못 한다. 어느 쪽이든 오래된 이름 |
| 03:21~03:38 | (말 없음) | "Placement Rates by **Abundance**"(첫 판독) → "by **Attendance**"(둘째·셋째 판독) | **Attendance.** 첫 판독의 오독 |

## 2. 말로만 한 것

| 시각 | 한 말 (영어 원문 요지) | 왜 확인이 필요한가 |
|---|---|---|
| 00:12~00:18 | 지난 수업은 **데이터 개인정보·보안**(무엇을 반드시 보호하고 어떻게 하나)이었다 | 이번 영상에는 그 방법이 안 나온다. **따라 하기 전에 선행 수업이 필요하다** (아래 순서 0) |
| 04:58~05:06 | "Be precise about what you need" — 위임할 작업을 **정확히** 정의하라 | 슬라이드에는 "Identify a specific analytical task…"뿐 |
| 05:14~05:25 | 평가할 때 세 가지를 물어라: AI가 **무엇을 냈나 / 어떻게 접근했나 / 결과를 어떻게 전달했나** | 슬라이드에 없는 구체 기준 |
| 05:25~05:41 | 여러 번 고쳐도 안 되면 **그 작업은 위임하지 말 것** | 슬라이드는 "test again"에서 끝남 |
| 04:39~04:58 | 새 데이터에 쓸 때도 점검은 계속: 숫자가 말이 되는지 보고, **최종 보고서의 책임은 나**, 물으면 AI 사용을 **투명하게 밝힌다** | 화면에 없는 원칙 |
| 06:22~06:33 | "validation builds confidence, but it doesn't eliminate responsibility" | 원칙 한 줄 |
| 06:33~06:49 | 같은 방법은 기부자 분석·예산 예측·설문 종합·성과 추적에도 쓴다 | 적용 범위 주장 |
| 05:55~06:03 | "AI models are **uniquely good at coding**" `[의견]` | 근거 화면 없음. 엑셀 수식·지저분한 데이터 정리에 도움 된다는 말의 전제 |

## 3. 화면에 실제로 있는 것

| 시각 | 화면에 있는 것 | 말과의 관계 |
|---|---|---|
| 00:44~01:18 | 슬라이드 "Delegation-Diligence loop": "Delegation approach: reproduce past data analysis using AI" → "Diligence questions: evaluate AI output quality against known results" | `[일치]` 말 00:26~00:44 |
| 02:01~02:09 | 스프레드시트 열: Participant_ID, **First_Name, Last_Name, Email, Phone**, Programs Enrolled, July/August/September_Attendance, Total_Sessions_Attended | `[화면만]` 이름·이메일·전화 열이 보인다. 업로드한 CSV에도 있는지는 모른다 |
| 02:10~03:09 | Claude 입력창: 파일 `valley_veterans_q3_2024_data.csv` 첨부 + 프롬프트 전문 (아래 순서 3) | `[일치]` 말 02:48~03:09 이 같은 문장을 읽는다 (두 모델 일치) |
| 03:11~03:20 | AI 진행 과정: "Examining the CSV file…", "Analyzing…", "Creating comprehensive visualizations…" | `[화면만]` |
| 03:21~03:38 | 첫 답변의 숫자: 출석 80~100% → **71.4%**, 60~80% → **66.7%**, 40~60% → **33.3%**, 0~40% → **0.0%** 취업률 · 8월 출석 평균 **9.2회** → 9월 **7.2회**(**22%** 감소) · "r=**0.055**" | `[화면만]` 두 모델 일치. 말은 숫자를 안 읽는다 |
| 03:31~03:38 | 재요청 문장: "Thanks! This is what I found as well, but can you try again paying extra attention to the programs they were enrolled in?" | `[화면만]` 말은 "program type에 특별히 주의하라고 했다"로 요약 |
| 03:39~03:48 | 고친 답: "Corrected Analysis — You Were Right!" · **Job Training + Housing Support: 90% (9 of 10명)**, 출석률 84.3% · Job Training **54.8%** vs 그 외 **37.9%**, 차이 **16.9%p** | `[일치]` 말 03:20~03:41 "AI catches its mistake". 숫자는 화면에만 |
| 03:39~03:50 | AI의 자기 점검: "Housing Support shows '162% attendance' because participants attended 32 sessions when only 20 are required" | `[화면만]` 출석률 지표가 **왜곡될 수 있다**는 사례 |
| 03:39~03:50 | AI 제안: "Expand Job Training + Housing Support **from 10 to 30** participants" | `[화면만]` 표본이 10명인 결과로 3배 확대를 권하는 것 `[해석]` |
| 03:49~04:04 | 후속 질문 "Great! Can you also look at this based on when participants enrolled?" 에 AI: 등록일 열이 없다 → 출석 패턴으로 추정하겠다 | `[일치]` 말 03:49~03:55 이 질문을 읽는다. 위 표 1 참고 |
| 04:58~05:40 | 슬라이드 "Key takeaways" 4개: ① 위임할 분석 작업을 정한다 ② 이미 분석해 둔 과거 데이터를 찾는다 ③ AI로 과거 분석을 재현하고 체계적으로 평가한다 ④ 빈틈을 찾아 고치고 다시 테스트한다 | `[일치]` 말 04:58~05:41 |
| 06:02~06:21 | 두 번째 예(기부 이메일): 프롬프트 "I run a conservation non-profit and I have a ton of data from our emails — clicks, open rate, things like that. Can you help me analyze to figure out what emails are most impactful for donations?" 에 AI가 필요한 열 목록(캠페인명, open rate, click rate, 기부액, 발송일…)을 되묻는다 | `[화면만]` 말은 "해결책이 어떤 모습일지 AI에게 물어라"만 한다 |
| 06:50~07:10 | "UP NEXT: Workflow augmentation" · 크레딧: "Based on The AI Fluency Framework by Rick Dakan and Joseph Feller" | `[일치]` 말 06:49~06:58 (다음 수업) |

## 4. 확인 못 한 것

- **업로드일·채널:** B길이라 가져오지 못했다. 영상이 말하는 방식이 언제 기준인지 모른다(화면 저작권 표기 2025, 모델 이름 Sonnet 4.5 → 2025년 판).
- **03:15 구간의 모델 이름**: 3.5 인지 4.5 인지 판독이 갈린다.
- **"162% attendance"**: 32회 ÷ 20회 = 160% 인데 162%로 읽혔다. 평균값이라 다를 수 있으나 확인 못 했다.
- **업로드한 CSV 안의 이름·이메일·전화:** 화면에 보인 것은 원본 스프레드시트의 열 이름이다. CSV 에 그대로 있었는지는 모른다.
- **내가 직접 본 장면:** 없음. 화면 항목은 모두 제미나이의 판독이고, 숫자(03:21~03:50)만 서로 다른 모델 둘이 같게 읽었다.

## 5. 따라 할 순서

준비물: Claude 앱(영상은 claude.ai 웹), **이미 결과를 아는 과거 데이터** 한 벌(CSV·엑셀). 예 `[제안]`: 지난해 내가 직접 계산해 둔 임대료·관리비 정리표, 배당 수령 내역표.

0. **먼저 개인정보를 정리한다.** 이름·이메일·전화번호·계좌·주소 열을 지우거나 가린 사본을 만든다. — 근거 `[말만]` (00:12 "지난 수업") + 화면의 Email/Phone 열
   - ⚠ 영상은 방법을 안 보여 준다. 최악의 경우: 남의 개인정보를 AI 서비스에 올리게 된다.
   - 먼저 직접 확인: 쓰는 서비스의 데이터 이용 정책.
1. **(00:46, 04:58) 맡기고 싶은 분석 작업을 하나, 정확히 정한다.** 예: "월별 출석 변화와 취업 성공의 관계". — 근거 `[일치]` + `[말만]`("정확히")
   - 성공 신호: 한 문장으로 적을 수 있다.
2. **(02:01, 05:06) 같은 분석을 이미 끝낸 과거 데이터를 고른다.** 내가 정답을 알고 있어야 평가할 수 있다. — 근거 `[일치]`
3. **(02:10~03:09) Claude 에 파일을 붙이고 이렇게 쓴다.** — 근거 `[일치]` (화면 + 말, 두 모델 일치)
   - 영상 원문: `I'm sharing attendance data and employment outcome data from our job training program last quarter. Please analyze the participation patterns across the three months and graph the correlations between attendance levels and employment success. I'm particularly interested in understanding whether consistent attendance predicts better job placement outcomes.`
   - 한국어로 옮기면 `[내 번역 — 영상에 없음]`: "지난 분기 직업훈련 프로그램의 출석 데이터와 취업 결과 데이터입니다. 3개월 동안의 참여 패턴을 분석하고, 출석 수준과 취업 성공의 상관관계를 그래프로 그려 주세요. 특히 꾸준한 출석이 더 좋은 취업 결과를 예측하는지 알고 싶습니다."
   - 틀: ①데이터가 무엇인지 ②무엇을 분석해 달라 ③특히 알고 싶은 질문.
4. **(03:09~03:31) 답을 사실로 받지 않고 내 기록과 대조한다.** 맞은 것·놓친 것을 메모. — 근거 `[일치]`
   - 성공 신호: 내가 아는 결과와 같은지 한 줄씩 체크했다. ⚠ 제목만 보지 말고 본문의 숫자·단서도 읽는다(영상 속 AI도 "Strongly Predicts"라면서 상관은 "weak"라고 썼다).
5. **(03:31~03:48) 놓친 점을 짚어 다시 시킨다.** 화면의 실제 문장: `Thanks! This is what I found as well, but can you try again paying extra attention to the programs they were enrolled in?` — 근거 `[화면만]`
   - 성공 신호: AI가 "놓쳤다"고 인정하고 내가 아는 결론에 맞춰 고친다.
6. **(03:49~04:28) 더 어려운 질문도 시험한다. 특히 데이터에 없는 정보가 필요한 질문.** — 근거 `[일치]`
   - ⚠ 없는 열을 AI가 **추정**해 채울 수 있다. 영상은 이를 "원치 않는 것"이라고 한다.
   - 먼저 직접 확인: 답변에 "I can infer…", "I don't see…" 같은 말이 있는지.
7. **(04:28, 02:25~02:39) 메모를 정리한다.** "다음에 프롬프트에 꼭 넣을 것"과 "내가 직접 줘야 할 맥락". 여러 번 고쳐도 안 맞으면 그 작업은 맡기지 않는다. — 근거 `[일치]` + `[말만]`(05:25)
8. **(04:39~04:58) 새 데이터에 쓸 때도 점검을 이어간다.** 숫자가 말이 되는지 보고, 최종 책임은 나. 물으면 AI 사용 사실을 밝힌다. — 근거 `[말만]`
9. **(선택, 05:41~06:22) 데이터가 낯설면** 질문이나 아이디어를 그대로 AI에게 주고, 해결책이 어떤 모양일지 설명해 달라고 하며, 모르는 것은 계속 되묻는다. 예: 화면의 기부 이메일 프롬프트(위 표 3). — 근거 `[일치]` + `[화면만]`(예시)

## 6. 영상 밖에서 확인할 것

- 영상의 숫자(71.4%, 90%, 54.8% 등)는 **데모 데이터의 결과**다. 내 데이터에 적용되지 않는다. 또 "90%"는 10명 중 9명이라 표본이 매우 작다 `[해석]` — 이 숫자로 결론을 내지 않는다.
- 지금 쓰는 Claude 모델 이름과 화면은 영상(2025, Sonnet 4.5)과 다를 수 있다.
- 한국어 번역은 영어 원문과 대조해서 읽는다(표 1의 "수십 시간"처럼 틀린 곳이 있었다).
- 영상 출처 문서: "The AI Fluency Framework" (Rick Dakan, Joseph Feller) — 화면 크레딧 기준. 원문은 직접 열어 확인해야 한다.
