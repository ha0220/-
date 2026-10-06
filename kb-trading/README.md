# KB 주식 매매 웹앱

KB증권 OpenAPI(B2C, 운영)로 **현재가·호가 조회**와 **매수/매도/정정/취소**를 할 수 있는 로컬 웹앱입니다.
Python **FastAPI** + 순수 **HTML/CSS/JavaScript** (프레임워크·빌드 없음).

| 기능 | 사용 API (엑셀 문서 기준) |
| --- | --- |
| 현재가 | `IVU10140` (`/api/v1/ivu10140`) |
| 호가 10단계 | `IVU10070` |
| 매수 / 매도 | `SSAM1802` / `SSAM1801` |
| 정정(가격) / 취소 | `SSAM1805` / `SSAM1806` |
| 주문가능금액 | `SSQM1802` |
| 보유종목·평가손익 | `SSQM2952` |
| 오늘 주문·체결내역 | `SSQM2341` |

## 빠른 시작

```bash
cd kb-trading
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                                        # http://127.0.0.1:8000
```

`.env` 가 없으면 **모의(MOCK) 모드**로 뜹니다. 시세·잔고·주문이 전부 가상 데이터이고 KB증권으로 아무것도 전송되지 않으니,
먼저 화면과 주문 흐름을 익히는 용도로 쓰세요.

## 실거래 연결 (순서대로)

1. KB OpenAPI 포털에서 발급받은 appKey/appSecret을 넣습니다.
   ```bash
   cp .env.example .env     # 그리고 .env 에 KB_OPENAPI_APP_KEY / KB_OPENAPI_APP_SECRET 입력
   ```
   `.env` 는 `.gitignore` 대상입니다. **키는 코드·채팅·커밋에 남기지 마세요.** (이미 노출했다면 포털에서 재발급하세요.)
2. 서버를 다시 띄우면 `LIVE` 모드가 되고, 이 단계에서는 **조회만** 됩니다 (`주문 OFF` 배지).
3. 시세·잔고가 실제 계좌와 맞는지 확인한 뒤, `.env` 에 `KB_TRADING_ENABLED=true` 로 바꿔 주문을 켭니다.
4. **첫 주문은 소액 테스트**: 현재가보다 한참 낮은 지정가 매수 1주를 넣어 `미체결`로 남는지 보고, 곧바로 `취소`해 보세요.
   정정·취소·종목코드 형식까지 한 번에 검증됩니다.

## 안전장치

- 실거래(live)에서는 `KB_TRADING_ENABLED=true` 가 아니면 서버가 매수/매도/정정을 거부합니다. (취소는 항상 가능)
- 주문 전 확인 창(종목·수량·예상금액), 서버 측 `confirm` 검증, 상·하한가 및 호가단위 검사, 현재가와 5% 이상 차이 경고.
- `KB_MAX_ORDER_AMOUNT`(기본 500만 원) 초과 주문은 서버가 거부합니다. 시장가는 현재가 기준으로 추정합니다.
- 서버는 기본적으로 `127.0.0.1` 에만 열리고, 허용된 Host/동일 출처 요청만 처리합니다(DNS rebinding·CSRF 방어).
  **인터넷에 그대로 공개하지 마세요.** 이 앱에는 로그인이 없고, 접속한 사람이 곧 계좌 주인입니다.
- appKey/appSecret은 서버 프로세스에만 있고 브라우저로 전달되지 않습니다. 접근토큰은 만료 5분 전까지 캐시합니다.

## 아직 실계정으로 검증하지 못한 부분 (확인 필요)

API 문서(엑셀)만으로는 확정할 수 없어서 실계정으로 한 번 확인이 필요한 가정들입니다. 틀리면 알려주세요.

| 가정 | 틀렸을 때 증상 / 대처 |
| --- | --- |
| 주문 API의 `is_cd`에 6자리 단축코드를 보낸다 | 주문 거부 시 `.env` 에 `KB_ORDER_CODE_MODE=standard`(12자리 표준코드 `KR7…`) |
| 호가 수량은 `s_pstn_sN_aprc_q`(매도), `b_pstn_bN_aprc_q`(매수) 필드 | 수량이 0/이상하면 `/api/orderbook/005930?raw=1`(live 전용)로 원본을 보고 `kb_client.py` 수정 |
| 주문 성공 = 응답에 0이 아닌 `ordr_no`가 있음 | 실패 시 `o_msg`/`msg` 문구를 그대로 화면에 표시 |
| 등락·등락률은 `현재가 − 전일종가`로 직접 계산 (전일대비구분코드 값의 의미가 문서에 없음) | — |
| 오늘 주문내역 `SSQM2341` 의 연속조회(`nxt_key`)는 최대 5페이지까지만 | 주문이 매우 많은 날은 일부 누락 가능 |

그 밖의 제약: 종목명 검색 API가 문서에 없어 이름 입력은 자주 찾는 14개 종목만 되고(나머지는 6자리 코드),
정정은 가격만(전량), 공휴일은 장 상태 표시에 반영되지 않습니다. 미국 주식(해외) API는 포함하지 않았습니다.

## 구조

```
kb-trading/
├─ run.py                 # 실행 진입점
├─ app/
│  ├─ main.py             # FastAPI 라우트, 주문 검증·안전장치
│  ├─ kb_client.py        # KB OpenAPI 호출(토큰 캐시, dataHeader/dataBody, 응답 정규화)
│  ├─ mock_broker.py      # 자격증명 없이 쓰는 모의 브로커
│  ├─ broker.py, config.py, util.py
├─ static/                # index.html, style.css, app.js
└─ tests/test_api.py      # pytest (모의 브로커 + 가짜 KB 서버로 요청 형식 검증)
```

테스트: `python -m pytest -q`

## 설정(.env)

`.env.example` 참고: `KB_MODE`, `KB_TRADING_ENABLED`, `KB_MAX_ORDER_AMOUNT`, `KB_ORDER_CODE_MODE`, `KB_HOST`, `KB_PORT`, `KB_ALLOWED_HOSTS`.

> 본 앱은 투자 권유가 아닌 주문 도구이며, 모든 주문의 책임은 사용자에게 있습니다.
