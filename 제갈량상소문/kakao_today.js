#!/usr/bin/env node
/* 오늘(한국 시간)의 카카오톡용 상소 요약을 출력합니다. (200자 이내)
   쓰는 곳: 매일 아침 예약 작업이 이 글을 그대로 카카오톡 '나와의 채팅'으로 보냅니다.
   화면(app.js)이 만드는 요약과 똑같이 나오도록 같은 규칙으로 고릅니다.
   사용:  node kakao_today.js            → 오늘
          node kakao_today.js 2026-10-17 → 그 날짜 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ctx = {};
ctx.window = ctx;
vm.createContext(ctx);
['content0.js', 'content1.js', 'content2a.js', 'content2b.js', 'kakao.js'].forEach(function (f) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, f), 'utf8'), ctx, { filename: f });
});
const S = ctx.SOSO;
const K = S.kakao;

let y, m, d;
const arg = process.argv[2];
if (arg && /^\d{4}-\d{2}-\d{2}$/.test(arg)) {
  [y, m, d] = arg.split('-').map(Number);
} else {
  [y, m, d] = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' })
    .format(new Date()).split('-').map(Number);
}
const dayNum = Math.floor(Date.UTC(y, m - 1, d) / 86400000);
const week = '일월화수목금토'[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];

const t1 = K.part1[dayNum % S.part1.length];
const t2 = K.part2[dayNum % S.part2.length];
const t3 = K.review[dayNum % S.review.length];

let msg = '📜 제갈량 상소 ' + m + '/' + d + '(' + week + ')\n' +
  '① 클로드: ' + t1 + '\n② 은퇴·돈: ' + t2 + '\n③ 복기: ' + t3 +
  '\n※판단 참고용, 결정은 주공 몫';
if (msg.length > 200) msg = msg.slice(0, 199) + '…';
process.stdout.write(msg + '\n');
