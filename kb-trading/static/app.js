"use strict";

// ── 유틸 ───────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const fmt = (n) => (Number.isFinite(n) ? n.toLocaleString("ko-KR") : "-");
const won = (n) => `${fmt(n)}원`;
const sign = (n) => (n > 0 ? "up" : n < 0 ? "down" : "flat");
const arrow = (n) => (n > 0 ? "▲" : n < 0 ? "▼" : "–");
const pct = (n) => `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;

function el(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null) e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return e;
}

async function api(path, opts = {}) {
  const init = { headers: { Accept: "application/json" }, ...opts };
  if (opts.body) { init.method = opts.method || "POST"; init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(opts.body); }
  let res;
  try { res = await fetch(path, init); } catch { throw new Error("서버에 연결할 수 없습니다."); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => String(x.msg).replace(/^Value error, /, "")).join(", ") : `요청 실패 (HTTP ${res.status})`);
  }
  return data;
}

let toastTimer;
function toast(msg, isError = false) {
  const t = $("toast");
  t.textContent = msg; t.className = `toast${isError ? " error" : ""}`;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), isError ? 6000 : 3000);
}

function tickSize(price, etf) {
  if (etf) return price < 2000 ? 1 : 5;
  for (const [lim, t] of [[2000, 1], [5000, 5], [20000, 10], [50000, 50], [200000, 100], [500000, 500]]) if (price < lim) return t;
  return 1000;
}

// 종목명 검색 API는 문서에 없어, 자주 찾는 종목만 이름으로 입력할 수 있게 둔다 (코드 직접 입력은 항상 가능).
const COMMON = {
  "삼성전자": "005930", "SK하이닉스": "000660", "LG에너지솔루션": "373220", "삼성바이오로직스": "207940",
  "현대차": "005380", "기아": "000270", "NAVER": "035420", "카카오": "035720", "셀트리온": "068270",
  "KB금융": "105560", "신한지주": "055550", "POSCO홀딩스": "005490", "KODEX 200": "069500", "TIGER 200": "102110",
};

const state = {
  code: null, quote: null, side: "buy", priceTouched: false, cfg: null,
  power: null, portfolio: null, orders: [], names: {},
  watch: loadJSON("kb.watch", []),
};
function loadJSON(key, dflt) { try { return JSON.parse(localStorage.getItem(key)) ?? dflt; } catch { return dflt; } }
function saveJSON(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch { /* 저장 불가 환경 */ } }
const shortCode = (c) => (c && c.length === 12 && c.startsWith("KR") ? c.slice(3, 9) : c);

// ── 상단: 모드/시계/장상태 ─────────────────────────────────────────
function sessionLabel(d = new Date()) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: "Asia/Seoul", weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false }).formatToParts(d).map((x) => [x.type, x.value]));
  const m = (parseInt(p.hour, 10) % 24) * 60 + parseInt(p.minute, 10);
  if (p.weekday === "Sat" || p.weekday === "Sun") return "휴장(주말)";
  if (m < 8 * 60 + 30) return "장 시작 전";
  if (m < 9 * 60) return "장개시전 시간외";
  if (m < 15 * 60 + 20) return "정규장";
  if (m < 15 * 60 + 30) return "종가 동시호가";
  if (m < 15 * 60 + 40) return "장 마감 직후";
  if (m < 16 * 60) return "장종료후 시간외";
  return "장 마감";
}
function tickClock() {
  $("clock").textContent = new Date().toLocaleTimeString("ko-KR", { timeZone: "Asia/Seoul", hour12: false }) + " KST";
  const s = $("session"); s.textContent = sessionLabel(); s.title = "시간 기준 표시이며 공휴일은 반영되지 않습니다.";
}

async function initStatus() {
  state.cfg = await api("/api/status");
  const mb = $("modeBadge");
  mb.textContent = state.cfg.mode === "live" ? "LIVE 실거래" : "MOCK 모의";
  mb.className = `badge ${state.cfg.mode === "live" ? "live" : "mock"}`;
  const banner = $("banner");
  if (state.cfg.mode === "mock") {
    banner.textContent = "모의 모드입니다. 시세·잔고·주문은 모두 가상 데이터이며 KB증권으로 아무것도 전송되지 않습니다. 실거래는 README의 .env 설정을 참고하세요.";
    banner.classList.remove("hidden");
  } else if (!state.cfg.trading_enabled) {
    const tb = $("tradeBadge"); tb.textContent = "주문 OFF"; tb.className = "badge off"; tb.classList.remove("hidden");
    banner.textContent = "시세·잔고 조회만 가능합니다. 실제 주문을 내려면 .env 에서 KB_TRADING_ENABLED=true 로 바꾸고 서버를 재시작하세요.";
    banner.classList.remove("hidden");
  }
  updateSubmitState();
}

// ── 종목 조회 / 시세 / 호가 ────────────────────────────────────────
function resolveCode(raw) {
  const s = raw.trim();
  if (!s) throw new Error("종목명 또는 코드를 입력하세요.");
  if (/^[0-9A-Za-z]{6}$/.test(s)) return s.toUpperCase();
  const hit = Object.entries({ ...COMMON, ...invert(state.names) }).find(([n]) => n.toLowerCase() === s.toLowerCase()) ||
    Object.entries({ ...COMMON, ...invert(state.names) }).find(([n]) => n.toLowerCase().includes(s.toLowerCase()));
  if (!hit) throw new Error("종목명을 찾지 못했습니다. 6자리 종목코드로 입력해 보세요.");
  return hit[1];
}
const invert = (o) => Object.fromEntries(Object.entries(o).map(([c, n]) => [n, c]));

async function loadStock(code, { keepPrice = false } = {}) {
  if (code !== state.code) { state.code = code; state.priceTouched = false; state.quote = null; }
  if (keepPrice) state.priceTouched = true;
  renderWatch();
  await refreshQuote();
}

let quoteBusy = false;
async function refreshQuote() {
  if (!state.code || quoteBusy) return;
  quoteBusy = true; const code = state.code;
  try {
    const [q, ob] = await Promise.all([api(`/api/quote/${code}`), api(`/api/orderbook/${code}`)]);
    if (code !== state.code) return;
    state.quote = q; state.names[code] = q.name || state.names[code];
    renderQuote(q); renderOrderbook(ob); syncTicketWithQuote();
  } catch (e) {
    if (code === state.code) { $("qName").textContent = `${code} 조회 실패`; $("qSub").textContent = e.message; toast(e.message, true); }
  } finally { quoteBusy = false; }
}

function renderQuote(q) {
  const cls = sign(q.change);
  $("qName").textContent = q.name || q.code;
  $("qSub").textContent = `${q.code}${q.market_name ? " · " + q.market_name : ""}`;
  const p = $("qPrice"); p.textContent = fmt(q.price); p.className = `q-price ${cls}`;
  const c = $("qChange"); c.textContent = `${arrow(q.change)} ${fmt(Math.abs(q.change))}  (${pct(q.rate)})`; c.className = `q-change ${cls}`;
  const rows = [["전일종가", q.prev_close], ["시가", q.open], ["고가", q.high], ["저가", q.low], ["상한가", q.upper_limit],
    ["하한가", q.lower_limit], ["거래량", q.volume], ["250일 최고", q.high_250], ["250일 최저", q.low_250]];
  const dl = $("qStats"); dl.replaceChildren(...rows.map(([k, v]) => el("div", {}, el("dt", {}, k), el("dd", {}, v ? fmt(v) : "-"))));
  const w = $("watchBtn"); w.textContent = state.watch.includes(q.code) ? "★" : "☆";
}

function renderOrderbook(ob) {
  const max = Math.max(1, ...ob.asks.map((a) => a.qty), ...ob.bids.map((b) => b.qty));
  const row = (cls, lv) => {
    const bar = el("i", { class: "bar", style: `width:${Math.round((lv.qty / max) * 100)}%` });
    const q = el("td", { class: "q" }, bar, el("span", { class: "v" }, fmt(lv.qty)));
    const p = el("td", { class: "p" }, fmt(lv.price));
    const tr = el("tr", { class: cls, title: "클릭하면 주문 가격에 입력됩니다" });
    tr.append(...(cls === "ask" ? [q, p, el("td")] : [el("td"), p, q]));
    tr.addEventListener("click", () => setOrderPrice(lv.price));
    return tr;
  };
  const asks = [...ob.asks].reverse().map((a) => row("ask", a));
  const bids = ob.bids.map((b) => row("bid", b));
  $("orderbook").tBodies[0].replaceChildren(...asks, ...bids);
  $("obTotals").textContent = `매도잔량 ${fmt(ob.total_ask_qty)} · 매수잔량 ${fmt(ob.total_bid_qty)}`;
}

// ── 관심종목 ────────────────────────────────────────────────────────
function renderWatch() {
  $("watchlist").replaceChildren(...state.watch.map((c) =>
    el("button", { type: "button", class: `chip${c === state.code ? " active" : ""}`, onclick: () => loadStock(c) }, state.names[c] ? `${state.names[c]}` : c)));
}
function toggleWatch() {
  if (!state.code) return;
  const i = state.watch.indexOf(state.code);
  if (i >= 0) state.watch.splice(i, 1); else state.watch.push(state.code);
  saveJSON("kb.watch", state.watch); renderWatch(); $("watchBtn").textContent = i >= 0 ? "☆" : "★";
}

// ── 주문 티켓 ───────────────────────────────────────────────────────
const typeIsLimit = () => $("oType").value === "limit";
const refPrice = () => (typeIsLimit() ? parseInt($("oPrice").value, 10) || 0 : state.quote?.price || 0);

function setSide(side) {
  state.side = side;
  $("tabBuy").classList.toggle("active", side === "buy"); $("tabSell").classList.toggle("active", side === "sell");
  const b = $("submitBtn"); b.className = `submit ${side}`; b.textContent = side === "buy" ? "매수 주문" : "매도 주문";
  $("oAvailLabel").textContent = side === "buy" ? "주문가능금액" : "매도가능수량";
  renderAvail(); updateAmount();
}
function setOrderPrice(price) { $("oType").value = "limit"; onTypeChange(); $("oPrice").value = price; state.priceTouched = true; updateAmount(); }
function syncTicketWithQuote() {
  const q = state.quote; if (!q) return;
  $("oCode").textContent = `${q.name || q.code} (${q.code})`;
  if (!state.priceTouched && typeIsLimit()) $("oPrice").value = q.price;
  updateAmount(); updateSubmitState();
}
function onTypeChange() {
  const lim = typeIsLimit();
  $("oPrice").disabled = !lim; $("pUp").disabled = !lim; $("pDown").disabled = !lim;
  if (!lim) $("oPrice").value = ""; else if (state.quote) { $("oPrice").value = state.quote.price; state.priceTouched = false; }
  updateAmount();
}
function stepPrice(dir) {
  const cur = parseInt($("oPrice").value, 10) || state.quote?.price || 0;
  const t = tickSize(dir > 0 ? cur : cur - 1, state.quote?.etf);
  $("oPrice").value = Math.max(t, Math.round(cur / t) * t + dir * t); state.priceTouched = true; updateAmount();
}
function holdingQty() { return state.portfolio?.rows.find((r) => r.code === state.code)?.sellable_qty ?? 0; }
function renderAvail() {
  $("oAvail").textContent = state.side === "buy"
    ? (state.power ? won(state.power.cash_available) : "-") : (state.portfolio ? `${fmt(holdingQty())}주` : "-");
}
function updateAmount() { $("oAmount").textContent = won(refPrice() * (parseInt($("oQty").value, 10) || 0)); }
function maxQty() {
  if (state.side === "sell") return holdingQty();
  const p = state.quote ? (typeIsLimit() ? parseInt($("oPrice").value, 10) || state.quote.price : state.quote.best_ask || state.quote.price) : 0;
  return p && state.power ? Math.floor(state.power.cash_available / p) : 0;
}
function updateSubmitState() {
  const off = state.cfg && !state.cfg.trading_enabled;
  $("submitBtn").disabled = !!off || !state.quote;
  $("submitBtn").title = off ? "실주문이 비활성화되어 있습니다 (KB_TRADING_ENABLED)" : "";
}

function buildOrder() {
  const q = state.quote;
  if (!q) throw new Error("먼저 종목을 조회하세요.");
  const qty = parseInt($("oQty").value, 10);
  if (!Number.isInteger(qty) || qty <= 0) throw new Error("수량은 1주 이상이어야 합니다.");
  const type = $("oType").value;
  const price = type === "limit" ? parseInt($("oPrice").value, 10) : 0;
  if (type === "limit" && !(price > 0)) throw new Error("지정가 주문은 가격을 입력하세요.");
  if (type === "limit" && q.upper_limit && (price > q.upper_limit || price < q.lower_limit))
    throw new Error(`가격이 상·하한가 범위(${fmt(q.lower_limit)}~${fmt(q.upper_limit)})를 벗어났습니다.`);
  if (type === "limit" && price % tickSize(price, q.etf) !== 0) throw new Error(`호가단위(${tickSize(price, q.etf)}원)에 맞지 않는 가격입니다.`);
  return { side: state.side, code: q.code, qty, price, order_type: type, session: $("oSession").value, sor: $("oSor").value, name: q.name };
}

const TYPE_NAMES = { limit: "지정가", market: "시장가", best: "최유리지정가", priority: "최우선지정가" };
const SESSION_NAMES = { "1": "정규장", "2": "장개시전 시간외종가", "3": "장종료후 시간외종가" };

function openConfirm(o) {
  return new Promise((resolve) => {
    const dlg = $("confirmDlg"), est = (o.price || state.quote.price) * o.qty;
    $("cTitle").textContent = `${o.side === "buy" ? "매수" : "매도"} 주문 확인`;
    $("cBody").replaceChildren(...[
      ["종목", `${o.name} (${o.code})`], ["구분", o.side === "buy" ? "매수" : "매도"], ["유형", TYPE_NAMES[o.order_type]],
      ["가격", o.order_type === "limit" ? won(o.price) : "시장 호가"], ["수량", `${fmt(o.qty)}주`],
      ["예상금액", won(est)], ["거래시간", SESSION_NAMES[o.session]],
    ].flatMap(([k, v]) => [el("span", {}, k), el("span", {}, v)]));
    const warns = [];
    if (state.cfg.mode === "live") warns.push("실거래 계좌로 실제 주문이 전송됩니다.");
    const cur = state.quote.price;
    if (o.order_type === "limit" && cur && Math.abs(o.price - cur) / cur > 0.05) warns.push(`현재가(${fmt(cur)}원)와 5% 이상 차이 나는 가격입니다.`);
    if (o.order_type !== "limit") warns.push("시장가 계열 주문은 체결가를 보장하지 않습니다.");
    const w = $("cWarn"); w.textContent = warns.join(" "); w.classList.toggle("hidden", !warns.length);
    const done = (v) => { dlg.close(); $("cYes").onclick = $("cNo").onclick = dlg.oncancel = null; resolve(v); };
    $("cYes").onclick = () => done(true); $("cNo").onclick = () => done(false); dlg.oncancel = () => done(false);
    dlg.showModal(); $("cNo").focus();
  });
}

let ordering = false;
async function submitOrder(ev) {
  ev.preventDefault();
  if (ordering) return;
  let o;
  try { o = buildOrder(); } catch (e) { return toast(e.message, true); }
  if (!(await openConfirm(o))) return;
  ordering = true; $("submitBtn").disabled = true;
  try {
    const { name, ...payload } = o;
    const r = await api("/api/orders", { body: { ...payload, confirm: true } });
    toast(`주문 접수 (주문번호 ${r.order_no}) ${r.message || ""}`);
    await Promise.all([refreshOrders(), refreshAccount()]);
  } catch (e) { toast(e.message, true); }
  finally { ordering = false; updateSubmitState(); }
}

// ── 주문내역 / 보유종목 ─────────────────────────────────────────────
const STATUS = { open: "미체결", partial: "일부체결", filled: "체결완료", cancel: "취소", rejected: "거부", done: "처리" };

async function refreshOrders() {
  try { state.orders = (await api("/api/orders")).orders; renderOrders(); } catch (e) { /* 다음 주기에 재시도 */ }
}
function renderOrders() {
  const rows = state.orders.map((o) => {
    const code = shortCode(o.code), live = o.status === "open" || o.status === "partial";
    const tr = el("tr", { class: "clickable", onclick: () => code && loadStock(code) },
      el("td", {}, o.time ? o.time.replace(/(\d\d)(\d\d)(\d\d)/, "$1:$2:$3") : "-"),
      el("td", {}, el("span", { class: `tag ${o.side}` }, o.side_name || "-")),
      el("td", {}, o.name || code),
      el("td", { class: "num" }, o.price ? fmt(o.price) : "시장가"),
      el("td", { class: "num" }, fmt(o.qty)), el("td", { class: "num" }, fmt(o.filled_qty)),
      el("td", { class: "num" }, fmt(o.unfilled_qty)),
      el("td", {}, STATUS[o.status] || o.status, o.note && o.status !== "cancel" ? ` (${o.note})` : ""),
      el("td", { class: "actions" }, live ? [
        el("button", { type: "button", onclick: (e) => { e.stopPropagation(); openAmend(o); } }, "정정"),
        el("button", { type: "button", onclick: (e) => { e.stopPropagation(); cancelOrder(o); } }, "취소"),
      ] : null));
    return tr;
  });
  $("ordersBody").replaceChildren(...rows);
  $("ordersEmpty").classList.toggle("hidden", rows.length > 0);
}

async function cancelOrder(o) {
  if (!confirm(`${o.name || o.code} ${fmt(o.unfilled_qty)}주 주문(${o.order_no})을 취소할까요?`)) return;
  try { await api(`/api/orders/${o.order_no}/cancel`, { body: { code: o.code } }); toast("취소 요청이 접수되었습니다."); }
  catch (e) { toast(e.message, true); }
  await Promise.all([refreshOrders(), refreshAccount()]);
}

let amending = null;
function openAmend(o) {
  amending = o;
  $("aInfo").replaceChildren(...[["종목", o.name || o.code], ["주문번호", o.order_no], ["현재 주문가", won(o.price)], ["미체결", `${fmt(o.unfilled_qty)}주`]]
    .flatMap(([k, v]) => [el("span", {}, k), el("span", {}, v)]));
  $("aPrice").value = o.price; $("amendDlg").showModal();
}
async function submitAmend() {
  const o = amending, price = parseInt($("aPrice").value, 10);
  if (!o || !(price > 0)) return toast("정정 가격을 입력하세요.", true);
  $("amendDlg").close();
  try {
    await api(`/api/orders/${o.order_no}/amend`, { body: { code: o.code, qty: o.unfilled_qty, price, order_type: "limit", session: "1", sor: "", confirm: true } });
    toast("정정 요청이 접수되었습니다.");
  } catch (e) { toast(e.message, true); }
  await Promise.all([refreshOrders(), refreshAccount()]);
}

async function refreshAccount() {
  const [p, pf] = await Promise.allSettled([api("/api/account/buying-power"), api("/api/account/portfolio")]);
  if (p.status === "fulfilled") state.power = p.value;
  if (pf.status === "fulfilled") { state.portfolio = pf.value; for (const r of pf.value.rows) if (r.name) state.names[r.code] = r.name; renderPortfolio(); renderWatch(); }
  if (p.status === "rejected" && pf.status === "rejected") toast(`계좌 조회 실패: ${p.reason.message}`, true);
  renderAvail(); updateAmount();
}
function renderPortfolio() {
  const pf = state.portfolio; if (!pf) return;
  const stat = (k, v, cls = "") => el("div", {}, el("span", { class: "muted" }, k), el("b", { class: cls }, v));
  $("pfSummary").replaceChildren(
    stat("총 평가금액", won(pf.value_total)), stat("총 매입금액", won(pf.cost_total)),
    stat("평가손익", `${pf.pnl_total > 0 ? "+" : ""}${fmt(pf.pnl_total)}원 (${pct(pf.pnl_rate)})`, sign(pf.pnl_total)),
    pf.net_assets ? stat("순자산", won(pf.net_assets)) : null);
  $("pfBody").replaceChildren(...pf.rows.map((r) => el("tr", { class: "clickable", onclick: () => { loadStock(shortCode(r.code)); setSide("sell"); } },
    el("td", {}, r.name || r.code), el("td", { class: "num" }, fmt(r.qty)), el("td", { class: "num" }, fmt(r.avg_price)),
    el("td", { class: "num" }, fmt(r.price)), el("td", { class: "num" }, fmt(r.value)),
    el("td", { class: `num ${sign(r.pnl)}` }, `${r.pnl > 0 ? "+" : ""}${fmt(r.pnl)}`),
    el("td", { class: `num ${sign(r.pnl)}` }, pct(r.pnl_rate)))));
  $("pfEmpty").classList.toggle("hidden", pf.rows.length > 0);
}

function showPane(id) {
  document.querySelectorAll(".col-bottom .tab").forEach((t) => t.classList.toggle("active", t.dataset.pane === id));
  document.querySelectorAll(".col-bottom .pane").forEach((p) => p.classList.toggle("hidden", p.id !== id));
}

// ── 초기화 ──────────────────────────────────────────────────────────
function bind() {
  $("searchForm").addEventListener("submit", (e) => {
    e.preventDefault();
    try { loadStock(resolveCode($("codeInput").value)); } catch (err) { toast(err.message, true); }
  });
  $("watchBtn").addEventListener("click", toggleWatch);
  $("tabBuy").addEventListener("click", () => setSide("buy")); $("tabSell").addEventListener("click", () => setSide("sell"));
  $("oType").addEventListener("change", onTypeChange);
  $("oPrice").addEventListener("input", () => { state.priceTouched = true; updateAmount(); });
  $("oQty").addEventListener("input", updateAmount);
  $("pUp").addEventListener("click", () => stepPrice(1)); $("pDown").addEventListener("click", () => stepPrice(-1));
  document.querySelectorAll(".quick [data-q]").forEach((b) => b.addEventListener("click", () => {
    $("oQty").value = (parseInt($("oQty").value, 10) || 0) + parseInt(b.dataset.q, 10); updateAmount();
  }));
  $("qMax").addEventListener("click", () => { $("oQty").value = Math.max(1, maxQty()); updateAmount(); });
  $("orderForm").addEventListener("submit", submitOrder);
  document.querySelectorAll(".col-bottom .tab").forEach((t) => t.addEventListener("click", () => showPane(t.dataset.pane)));
  $("refreshAll").addEventListener("click", () => { refreshQuote(); refreshOrders(); refreshAccount(); });
  $("aYes").addEventListener("click", submitAmend); $("aNo").addEventListener("click", () => $("amendDlg").close());
  $("stockList").replaceChildren(...Object.keys(COMMON).map((n) => el("option", { value: n })));
}

async function main() {
  bind(); tickClock(); setInterval(tickClock, 1000);
  try { await initStatus(); } catch (e) { toast(e.message, true); }
  renderWatch(); onTypeChange();
  refreshOrders(); refreshAccount();
  const first = state.watch[0] || "005930";
  $("codeInput").value = state.names[first] || first; loadStock(first);
  // 화면이 보일 때만 갱신 (API 호출 수 절약)
  setInterval(() => { if (!document.hidden) refreshQuote(); }, 3000);
  setInterval(() => { if (!document.hidden) refreshOrders(); }, 5000);
  setInterval(() => { if (!document.hidden) refreshAccount(); }, 15000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) { refreshQuote(); refreshOrders(); refreshAccount(); } });
}
main();
