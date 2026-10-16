/* 제갈량 상소문 — 화면 그리는 프로그램
   하는 일: 오늘 날짜로 상소문 한 편을 고르고, 내 정보(profile.js)로 계산해서 화면에 그립니다.
   인터넷·로그인·설치가 필요 없습니다. */
(function () {
  'use strict';

  var P = window.MY_PROFILE || {};
  var S = window.SOSO || {};
  var TAX = 0.154;                       // 이자·배당 원천징수 15.4% (계산 예시용 단순 가정)

  /* ---------- 숫자 꾸미기 ---------- */
  function comma(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function won(man) {                    // 만원 → "1억 2,500만 원"
    var n = Math.round(man);
    if (n >= 1000) n = Math.round(n / 10) * 10;
    if (n >= 10000) {
      var e = Math.floor(n / 10000), r = n % 10000;
      return r ? e + '억 ' + comma(r) + '만 원' : e + '억 원';
    }
    return comma(n) + '만 원';
  }
  function pct(x) { return (Math.round(x * 1000) / 10).toFixed(1).replace(/\.0$/, '') + '%'; }
  function num(v, d) { return typeof v === 'number' && isFinite(v) ? v : d; }

  /* ---------- 내 정보로 계산 ---------- */
  var asset = num(P.금융자산, 10000), sale = num(P.상가매각유입, 100000);
  var goal = num(P.목표월현금흐름, 500), pension = num(P.국민연금월, 230);
  var years = num(P.국민연금까지, 5), retire = num(P.개인퇴직연금월, 30);
  var total = asset + sale, annual = goal * 12, gap = Math.max(goal - pension, 0);

  var V = {
    채널: P.채널 || '무한돈전', 나이: num(P.나이, 64),
    금융자산: won(asset), 상가유입: won(sale), 합계: won(total),
    목표월: won(goal), 연목표: won(annual),
    국민연금월: won(pension), 연금년: years, 퇴직연금월: won(retire),
    은퇴: P.은퇴까지 || '2~3', 보유ETF: P.보유ETF || '보유 중인 ETF', 기준일: P.기준일 || '',
    필요율: pct(annual / total), 세전필요율: pct(annual / total / (1 - TAX)),
    부족월: won(gap), 부족연: won(gap * 12),
    연금후필요율: pct(gap * 12 / total), 연금후세전필요율: pct(gap * 12 / total / (1 - TAX)),
    다리자금: won(annual * years), 다리비중: pct(annual * years / total),
    완충12: won(goal * 12), 완충24: won(goal * 24), 완충36: won(goal * 36),
    배당4: won(total * 0.04), 세후4: won(total * 0.04 * (1 - TAX)), 월세후4: won(total * 0.04 * (1 - TAX) / 12),
    초과4: won(Math.max(total * 0.04 - 2000, 0)), 자산4: won(asset * 0.04),
    자산비중: pct(asset / total), 유입비중: pct(sale / total)
  };

  function fill(t) {
    return String(t).replace(/\{\{([^}]+)\}\}/g, function (m, k) {
      return Object.prototype.hasOwnProperty.call(V, k) ? V[k] : '⚠' + k + '⚠';
    });
  }
  function esc(t) { return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  var TAGS = { '사실': 't-fact', '해석': 't-interp', '가정': 't-assume', '미확인': 't-unk' };
  function rich(t) {                     // 글자 → 안전한 HTML (꼬리표·굵은 글씨)
    return esc(fill(t))
      .replace(/\[(사실|해석|가정|미확인)\]/g, function (m, k) { return '<span class="tag ' + TAGS[k] + '">' + k + '</span>'; })
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  }

  /* ---------- 날짜 고르기 ---------- */
  var qs = new URLSearchParams(location.search);
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function ymd(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  var day = new Date();
  var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(qs.get('date') || '');
  if (m) day = new Date(+m[1], +m[2] - 1, +m[3]);
  var dayNum = Math.floor(Date.UTC(day.getFullYear(), day.getMonth(), day.getDate()) / 86400000);

  function pick(list, key, n) {
    var q = qs.get(key);
    return list[(q !== null && !isNaN(+q) ? +q : n) % list.length];
  }
  var part1 = S.part1 || [], part2 = S.part2 || [], review = S.review || [];
  var a = part1.length ? pick(part1, 'a', dayNum) : null;
  var b = part2.length ? pick(part2, 'b', dayNum) : null;
  var r = review.length ? pick(review, 'r', dayNum) : '';

  var STEM = '갑을병정무기경신임계', BRANCH = '자축인묘진사오미신유술해';
  var yy = day.getFullYear();
  var ganji = STEM[(yy - 4) % 10] + BRANCH[(yy - 4) % 12] + '년';
  var WEEK = '일월화수목금토';

  /* ---------- 화면 만들기 ---------- */
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function copyText(text, btn) {
    function done() { var o = btn.textContent; btn.textContent = '복사했습니다'; setTimeout(function () { btn.textContent = o; }, 1600); }
    function fallback() {
      var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta);
      ta.select(); try { document.execCommand('copy'); done(); } catch (e) { btn.textContent = '드래그해서 복사하세요'; }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback);
    else fallback();
  }

  function blocks(list, box) {
    (list || []).forEach(function (bl) {
      if (typeof bl === 'string') { box.appendChild(el('p', '', rich(bl))); return; }
      if (bl.h) { box.appendChild(el('h4', '', rich(bl.h))); return; }
      if (bl.ul || bl.ol) {
        var ul = el(bl.ul ? 'ul' : 'ol');
        (bl.ul || bl.ol).forEach(function (t) { ul.appendChild(el('li', '', rich(t))); });
        box.appendChild(ul); return;
      }
      if (bl.quote) { box.appendChild(el('blockquote', '', rich(bl.quote))); return; }
      if (bl.prompt) {
        var text = fill(bl.prompt);
        var pb = el('div', 'prompt');
        var cap = el('div', 'cap', '<span>📜 이 말을 그대로 복사해서 클로드 코드에 붙여 넣으십시오</span>');
        var btn = el('button', 'copy', '복사'); btn.type = 'button';
        btn.addEventListener('click', function () { copyText(text, btn); });
        cap.appendChild(btn); pb.appendChild(cap);
        var pre = el('pre'); pre.textContent = text; pb.appendChild(pre);
        box.appendChild(pb); return;
      }
      if (bl.scenario) {
        var rows = [0.03, 0.04, 0.05].map(function (rate) {
          var g = total * rate, n = g * (1 - TAX);
          return '<tr><td>' + pct(rate) + '</td><td>' + won(g) + '</td><td>' + won(n) + '</td><td>' + won(n / 12) + '</td></tr>';
        }).join('');
        box.appendChild(el('table', '',
          '<thead><tr><th>세전 수익률(가정)</th><th>1년 세전</th><th>1년 세후(15.4% 가정)</th><th>한 달 세후</th></tr></thead><tbody>' + rows + '</tbody>'));
        return;
      }
      if (bl.table) {
        var t = bl.table;
        var h = '<thead><tr>' + t.head.map(function (c) { return '<th>' + rich(c) + '</th>'; }).join('') + '</tr></thead>';
        var bd = '<tbody>' + t.rows.map(function (rw) { return '<tr>' + rw.map(function (c) { return '<td>' + rich(c) + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody>';
        box.appendChild(el('table', '', h + bd));
      }
    });
  }

  function paper(id, paras) {
    var box = document.getElementById(id);
    (paras || []).forEach(function (t) { box.appendChild(el('p', '', rich(t))); });
  }

  // 머리말
  document.getElementById('who').textContent = V.채널;
  document.getElementById('date').textContent =
    ganji + ' ' + (day.getMonth() + 1) + '월 ' + day.getDate() + '일 ' + WEEK[day.getDay()] + '요일';
  document.title = '제갈량 상소문 · ' + ymd(day);
  paper('intro', S.intro);

  /* ---------- 오늘의 조정: 승상 제갈량 + 세 신하 ---------- */
  function mod(n, m) { return ((n % m) + m) % m; }
  function dayFor(key) { var q = qs.get(key); return q !== null && !isNaN(+q) ? +q : dayNum; }

  // 사람 그림(SVG). 모두 이 프로그램 안에서 그려서 인터넷이 필요 없습니다.
  function face(role) {
    var INK = '#2a2018', SKIN = '#efd3b3';
    var C = {
      zhuge:   { robe: '#f2eee2', trim: '#2f4a78' },
      finance: { robe: '#8a5a1c', trim: '#f0d9a0' },
      content: { robe: '#3a4f7a', trim: '#e8dfc8' },
      health:  { robe: '#3f6f4f', trim: '#e6f1e4' }
    }[role];
    var s = '<svg viewBox="0 0 120 156" xmlns="http://www.w3.org/2000/svg" role="img" aria-hidden="true">';
    s += '<circle cx="60" cy="84" r="60" fill="var(--face-bg)"/>';
    // 도포(몸)와 깃
    s += '<path d="M24 156 L29 96 Q60 80 91 96 L96 156 Z" fill="' + C.robe + '" stroke="' + INK + '" stroke-width="2.5" stroke-linejoin="round"/>';
    s += '<path d="M47 86 L60 110 L73 86" fill="none" stroke="' + C.trim + '" stroke-width="6" stroke-linejoin="round" stroke-linecap="round"/>';
    // 얼굴
    s += '<circle cx="60" cy="56" r="23" fill="' + SKIN + '" stroke="' + INK + '" stroke-width="2.5"/>';
    s += '<circle cx="51" cy="56" r="2.6" fill="' + INK + '"/><circle cx="69" cy="56" r="2.6" fill="' + INK + '"/>';
    s += '<path d="M52 67 Q60 72 68 67" fill="none" stroke="' + INK + '" stroke-width="2.2" stroke-linecap="round"/>';
    if (role === 'zhuge') {
      s += '<path d="M50 72 Q60 100 70 72 Q60 80 50 72 Z" fill="#f6f3ea" stroke="' + INK + '" stroke-width="1.8" stroke-linejoin="round"/>';          // 수염
      s += '<rect x="40" y="24" width="40" height="22" rx="7" fill="#2f4a78" stroke="' + INK + '" stroke-width="2.5"/>';                              // 윤건
      s += '<rect x="36" y="42" width="48" height="7" rx="3.5" fill="#2f4a78" stroke="' + INK + '" stroke-width="2.5"/>';
      s += '<g transform="translate(97 112) rotate(22)"><rect x="-2" y="0" width="4" height="30" rx="2" fill="#6b4a22" stroke="' + INK + '" stroke-width="1.5"/>' +
           '<ellipse cx="0" cy="-8" rx="10" ry="22" fill="#fffdf6" stroke="' + INK + '" stroke-width="2"/>' +
           '<path d="M0 -28 L0 10 M-6 -22 L-5 4 M6 -22 L5 4" stroke="#b8b09a" stroke-width="1.2" fill="none"/></g>';                             // 깃털 부채
    } else if (role === 'finance') {
      s += '<rect x="44" y="24" width="32" height="24" rx="9" fill="#1d1a16" stroke="' + INK + '" stroke-width="2.5"/>';                               // 사모
      s += '<rect x="14" y="36" width="34" height="7" rx="3.5" fill="#1d1a16"/><rect x="72" y="36" width="34" height="7" rx="3.5" fill="#1d1a16"/>';
      s += '<g transform="translate(30 122)"><rect width="60" height="30" rx="4" fill="#c79a4a" stroke="' + INK + '" stroke-width="2.2"/>' +
           '<line x1="0" y1="9" x2="60" y2="9" stroke="' + INK + '" stroke-width="1.5"/>' +
           '<line x1="15" y1="0" x2="15" y2="30" stroke="' + INK + '" stroke-width="1.4"/><line x1="30" y1="0" x2="30" y2="30" stroke="' + INK + '" stroke-width="1.4"/><line x1="45" y1="0" x2="45" y2="30" stroke="' + INK + '" stroke-width="1.4"/>' +
           '<circle cx="15" cy="4.5" r="3" fill="' + INK + '"/><circle cx="30" cy="4.5" r="3" fill="' + INK + '"/><circle cx="45" cy="4.5" r="3" fill="' + INK + '"/>' +
           '<circle cx="15" cy="17" r="3" fill="#6b3a12"/><circle cx="30" cy="22" r="3" fill="#6b3a12"/><circle cx="45" cy="17" r="3" fill="#6b3a12"/></g>';   // 주판
    } else if (role === 'content') {
      s += '<ellipse cx="60" cy="40" rx="38" ry="9" fill="#1d1a16" stroke="' + INK + '" stroke-width="2"/>';                                           // 갓
      s += '<path d="M45 40 Q45 14 60 14 Q75 14 75 40 Z" fill="#1d1a16" stroke="' + INK + '" stroke-width="2"/>';
      s += '<g transform="translate(28 120)"><rect width="64" height="30" rx="4" fill="#fbf4df" stroke="' + INK + '" stroke-width="2.2"/>' +
           '<line x1="8" y1="9" x2="56" y2="9" stroke="' + INK + '" stroke-width="2"/><line x1="8" y1="16" x2="50" y2="16" stroke="' + INK + '" stroke-width="2"/><line x1="8" y1="23" x2="42" y2="23" stroke="' + INK + '" stroke-width="2"/>' +
           '<rect x="-5" y="-2" width="8" height="34" rx="4" fill="#9a2b1d" stroke="' + INK + '" stroke-width="1.8"/><rect x="61" y="-2" width="8" height="34" rx="4" fill="#9a2b1d" stroke="' + INK + '" stroke-width="1.8"/></g>';   // 두루마리
    } else {
      s += '<path d="M38 46 Q38 16 60 16 Q82 16 82 46 Z" fill="#1d1a16" stroke="' + INK + '" stroke-width="2.5"/>';                                    // 복건
      s += '<path d="M82 40 Q96 44 94 62" fill="none" stroke="#1d1a16" stroke-width="5" stroke-linecap="round"/>';
      s += '<g transform="translate(84 112)"><rect x="-3" y="-8" width="6" height="7" rx="2" fill="#6b4a22" stroke="' + INK + '" stroke-width="1.5"/>' +
           '<circle cx="0" cy="3" r="8" fill="#d79a3a" stroke="' + INK + '" stroke-width="2"/><circle cx="0" cy="20" r="12" fill="#d79a3a" stroke="' + INK + '" stroke-width="2"/></g>';   // 호리병
      s += '<circle cx="40" cy="130" r="11" fill="#ffffff" stroke="' + INK + '" stroke-width="2"/><path d="M40 124 V136 M34 130 H46" stroke="#3f6f4f" stroke-width="4" stroke-linecap="round"/>';  // 의원 표지
    }
    return s + '</svg>';
  }

  var CT = S.court;
  if (CT) {
    var cbox = document.getElementById('court');
    cbox.appendChild(el('p', 'label', '朝會 · 오늘의 조정'));
    cbox.appendChild(el('h2', '', '승상과 세 신하가 아뢰옵니다'));

    // 승상 (중앙)
    var zt = CT.zhuge[mod(dayFor('z'), CT.zhuge.length)];
    var chief = el('div', 'chief');
    chief.innerHTML =
      '<div class="dais"><div class="face big">' + face('zhuge') + '</div></div>' +
      '<div class="plate"><b>승상 제갈량</b><span>조정의 중앙 · 신하들의 말을 듣고 정리하옵니다</span></div>' +
      '<div class="bubble top"><span class="chip">승상의 말씀</span><p>' + rich(zt) + '</p></div>';
    cbox.appendChild(chief);

    // 재정 신하: 날마다 점검 주제가 돌아가고(현금흐름 → 보험료 → 유동성), 주제 안에서도 매번 다른 질문
    var cats = ['세후 현금흐름', '건강보험료', '유동성'];
    var fd = dayFor('f');
    var fcat = cats[mod(fd, 3)];
    var flist = CT.finance.filter(function (x) { return x.k === fcat; });
    var fi = flist[mod(Math.floor(fd / 3) * 3 + 1, flist.length)];
    var ci = CT.content[mod(dayFor('c') * 4 + 7, CT.content.length)];
    var hi = CT.health[mod(dayFor('h') * 5 + 3, CT.health.length)];

    var ministers = [
      { cls: 'left',  role: 'finance', name: '재정 신하', sub: '곳간을 지키는 이', k: '점검 질문 · ' + fi.k, t: fi.t },
      { cls: 'right', role: 'content', name: '콘텐츠 신하', sub: '붓을 잡는 이', k: ci.k + ' · ' + V.채널, t: ci.t },
      { cls: 'left',  role: 'health',  name: '건강 신하', sub: '몸을 살피는 어의', k: hi.k, t: hi.t }
    ];
    ministers.forEach(function (m) {
      var row = el('div', 'mini ' + m.cls);
      row.innerHTML =
        '<div class="who"><div class="face">' + face(m.role) + '</div><div class="nm">' + m.name + '</div><div class="sb">' + m.sub + '</div></div>' +
        '<div class="bubble"><span class="chip">' + esc(m.k) + '</span><p>' + rich(m.t) + '</p></div>';
      cbox.appendChild(row);
    });
    cbox.appendChild(el('p', 'courtnote', '신하들의 말은 판단을 돕는 질문과 제안일 뿐이며, 종목을 사고팔라는 말이 아니옵니다. 최종 결정은 주공의 몫이옵니다.'));
    window.__SOSO_COURT__ = { zhuge: zt, finance: fi.t, content: ci.t, health: hi.t };
  }

  // 1부
  var p1 = document.getElementById('part1');
  if (a) {
    p1.appendChild(el('p', 'label', '一部 · 일을 덜어 주는 길'));
    p1.appendChild(el('h2', '', rich('클로드 코드 활용에 대한 간언 — ' + a.title)));
    blocks(a.blocks, p1);
  }

  // 2부
  var p2 = document.getElementById('part2');
  if (b) {
    p2.appendChild(el('p', 'label', '二部 · 은퇴 뒤 살림을 지키는 길'));
    p2.appendChild(el('h2', '', rich('은퇴·현금흐름·삶의 방향에 대한 간언 — ' + b.title)));
    [['결론', '먼저 결론을 아뢰옵니다', b.결론], ['근거', '이렇게 헤아렸사옵니다', b.근거],
     ['위험', '그러나 이런 위험이 있사옵니다', b.위험], ['행동', '오늘 할 일은 단 하나이옵니다', b.행동]
    ].forEach(function (s, i) {
      p2.appendChild(el('h3', '', '「' + '一二三四'[i] + '」 ' + s[0] + ' — ' + s[1]));
      blocks(s[2], p2);
    });
  }

  // 3부 (3줄 이내)
  var p3 = document.getElementById('part3');
  p3.appendChild(el('p', 'label', '三部 · 오늘의 한 줄 과제'));
  p3.appendChild(el('h2', '', '오늘은 이 셋만 보시옵소서'));
  var lines = [['①', '클로드 코드', a && a.하나만], ['②', '은퇴·돈', b && b.한줄], ['③', '복기', r]];
  var ul = el('ul', 'task');
  lines.forEach(function (ln, i) {
    if (!ln[2]) return;
    var key = 'soso-' + ymd(day) + '-' + i;
    var li = el('li', '');
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.setAttribute('aria-label', ln[1] + ' 과제 완료');
    try { cb.checked = localStorage.getItem(key) === '1'; } catch (e) { /* 저장이 안 돼도 괜찮습니다 */ }
    cb.addEventListener('change', function () { try { localStorage.setItem(key, cb.checked ? '1' : '0'); } catch (e) { /* 무시 */ } });
    li.appendChild(cb);
    li.appendChild(el('span', '', '<b>' + ln[0] + ' ' + ln[1] + '</b> — ' + rich(ln[2])));
    ul.appendChild(li);
  });
  p3.appendChild(ul);

  paper('outro', S.outro);

  /* 카카오톡용 200자 요약: 오늘의 3부 과제 세 줄 */
  var K = S.kakao || {};
  var kk = [(K.part1 || [])[part1.indexOf(a)], (K.part2 || [])[part2.indexOf(b)], (K.review || [])[review.indexOf(r)]];
  var kakao = '📜 제갈량 상소 ' + (day.getMonth() + 1) + '/' + day.getDate() + '(' + WEEK[day.getDay()] + ')\n' +
    '① 클로드: ' + (kk[0] || '') + '\n② 은퇴·돈: ' + (kk[1] || '') + '\n③ 복기: ' + (kk[2] || '') +
    '\n※판단 참고용, 결정은 주공 몫';
  if (kakao.length > 200) kakao = kakao.slice(0, 199) + '…';
  window.__SOSO_KAKAO__ = kakao;
  document.getElementById('btn-kakao').addEventListener('click', function () { copyText(kakao, this); });

  // 바닥글: 분량·면책
  function count(id) { return (document.getElementById(id).innerText || '').replace(/\s+/g, '').length; }
  var c1 = count('part1'), c2 = count('part2');
  var foot = document.getElementById('foot');
  foot.appendChild(el('p', '', '오늘 상소 분량(공백 제외): 1부 ' + comma(c1) + '자 · 2부 ' + comma(c2) + '자 · 합계 ' + comma(c1 + c2) + '자'));
  foot.appendChild(el('p', '', '내 정보 기준일 ' + esc(V.기준일) + ' · 합계 자산 ' + V.합계 + ' 기준으로 계산했습니다. 숫자가 달라졌으면 profile.js 를 고치십시오.'));
  foot.appendChild(el('p', '', '이 글은 판단을 돕는 참고 자료이며 투자·세무·법률 자문이 아닙니다. 특정 종목을 사거나 팔라는 지시가 아닙니다. 세법·건강보험 기준은 해마다 바뀌므로 [미확인] 꼬리표가 붙은 곳은 반드시 공식 기관에서 직접 확인하시고, 큰 결정 전에는 세무사·회계사와 상의하십시오. 최종 결정은 본인의 몫입니다.'.replace('[미확인]', '「미확인」')));
  window.__SOSO_COUNT__ = { part1: c1, part2: c2, a: part1.indexOf(a), b: part2.indexOf(b) };

  /* ---------- 단추 ---------- */
  function go(offset) {
    var d = new Date(day.getFullYear(), day.getMonth(), day.getDate() + offset);
    location.search = '?date=' + ymd(d);
  }
  document.getElementById('btn-prev').addEventListener('click', function () { go(-1); });
  document.getElementById('btn-next').addEventListener('click', function () { go(1); });
  document.getElementById('btn-today').addEventListener('click', function () { location.search = ''; });
  document.getElementById('btn-print').addEventListener('click', function () { window.print(); });

  var root = document.documentElement;
  function load(k, d) { try { return localStorage.getItem(k) || d; } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 무시 */ } }
  var fs = +load('soso-fs', 22);
  function setFs(v) { fs = Math.max(16, Math.min(34, v)); root.style.setProperty('--fs', fs + 'px'); save('soso-fs', fs); }
  setFs(fs);
  document.getElementById('btn-small').addEventListener('click', function () { setFs(fs - 2); });
  document.getElementById('btn-big').addEventListener('click', function () { setFs(fs + 2); });
  root.setAttribute('data-theme', load('soso-theme', 'paper'));
  document.getElementById('btn-theme').addEventListener('click', function () {
    var t = root.getAttribute('data-theme') === 'night' ? 'paper' : 'night';
    root.setAttribute('data-theme', t); save('soso-theme', t);
  });
})();
