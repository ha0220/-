// 네이버 밴드 MCP 서버 (Cloudflare Worker)
// claude.ai 사용자 지정 커넥터 주소: https://<워커이름>.<하위도메인>.workers.dev/mcp/<MCP_TOKEN>
//
// Cloudflare 설정 → 변수 및 비밀:
//   BAND_ACCESS_TOKEN (비밀) : 밴드 개발자센터에서 발급받은 Access Token
//   MCP_TOKEN         (비밀) : 아무도 모르는 긴 문자열 (커넥터 주소 끝에 붙음)
//   WRITE_BANDS       (텍스트, 선택) : 글쓰기를 허용할 밴드 이름. 쉼표로 구분
//                                      예) 정부정책 자료,신문 업그레이드
//                                      비워 두면 글쓰기가 꺼져 있음 (읽기만 가능)
//
// 사용한 밴드 Open API (https://developers.band.us/develop/guide/api)
//   GET  https://openapi.band.us/v2.1/bands
//   GET  https://openapi.band.us/v2/band/posts
//   GET  https://openapi.band.us/v2/band/post/comments
//   POST https://openapi.band.us/v2.2/band/post/create

const API = "https://openapi.band.us";
const SERVER = { name: "naver-band", version: "1.0.0" };

const TOOLS = [
  {
    name: "band_list",
    description: "내가 가입한 네이버 밴드 목록(이름, 멤버 수, band_key)을 조회합니다.",
    inputSchema: { type: "object", properties: {} },
    annotations: { title: "밴드 목록", readOnlyHint: true, openWorldHint: true },
  },
  {
    name: "band_posts",
    description: "밴드의 최근 글 목록을 최신순으로 조회합니다. band_name 또는 band_key 중 하나를 주세요.",
    inputSchema: {
      type: "object",
      properties: {
        band_name: { type: "string", description: "밴드 이름 (예: 정부정책 자료)" },
        band_key: { type: "string", description: "밴드 식별자 (band_list 결과)" },
        limit: { type: "integer", minimum: 1, maximum: 20, description: "가져올 글 수 (기본 10, 최대 20)" },
        page_token: { type: "string", description: "다음 페이지 토큰 (이전 결과 맨 아래에 나옴)" },
      },
    },
    annotations: { title: "밴드 글 읽기", readOnlyHint: true, openWorldHint: true },
  },
  {
    name: "band_comments",
    description: "밴드 글 하나의 댓글을 조회합니다.",
    inputSchema: {
      type: "object",
      properties: {
        band_name: { type: "string" },
        band_key: { type: "string" },
        post_key: { type: "string", description: "글 식별자 (band_posts 결과)" },
      },
      required: ["post_key"],
    },
    annotations: { title: "밴드 댓글 읽기", readOnlyHint: true, openWorldHint: true },
  },
  {
    name: "band_write_post",
    description:
      "밴드에 새 글을 올립니다. WRITE_BANDS에 등록된 밴드에만 쓸 수 있습니다. 푸시 알림은 기본으로 보내지 않습니다.",
    inputSchema: {
      type: "object",
      properties: {
        band_name: { type: "string" },
        band_key: { type: "string" },
        content: { type: "string", description: "올릴 본문 (최대 약 1만 자)" },
        do_push: { type: "boolean", description: "멤버에게 푸시 알림 보내기 (기본 false)" },
      },
      required: ["content"],
    },
    annotations: { title: "밴드 글쓰기", readOnlyHint: false, destructiveHint: false, openWorldHint: true },
  },
];

// ---------- 밴드 API 호출 ----------
async function bandGet(env, path, params = {}) {
  const q = new URLSearchParams({ access_token: token(env), ...params });
  const res = await fetch(`${API}${path}?${q}`);
  return parseBand(res);
}

async function bandPost(env, path, params) {
  const body = new URLSearchParams({ access_token: token(env), ...params });
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  return parseBand(res);
}

function token(env) {
  const t = String(env.BAND_ACCESS_TOKEN || "").trim();
  if (!t) throw new Error("BAND_ACCESS_TOKEN이 비어 있습니다. Cloudflare 설정 → 변수 및 비밀에 넣어 주세요.");
  return t;
}

async function parseBand(res) {
  let data;
  try {
    data = await res.json();
  } catch {
    throw new Error(`밴드 API 응답을 읽지 못했습니다 (HTTP ${res.status}).`);
  }
  if (data.result_code !== 1) {
    const msg = data.result_data?.message || data.result_data?.detail || JSON.stringify(data).slice(0, 300);
    throw new Error(`밴드 API 오류 (result_code ${data.result_code}): ${msg}`);
  }
  return data.result_data || {};
}

// ---------- 도우미 ----------
function kst(ms) {
  if (!ms) return "";
  return new Date(Number(ms)).toLocaleString("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
}

function clean(s) {
  return String(s || "")
    .replace(/<band:[^>]*>([^<]*)<\/band:[^>]*>/g, "$1")
    .replace(/<[^>]+>/g, "")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .trim();
}

function short(s, n) {
  const t = clean(s).replace(/\s+/g, " ");
  return t.length > n ? t.slice(0, n) + "…" : t;
}

async function listBands(env) {
  const data = await bandGet(env, "/v2.1/bands");
  return data.bands || [];
}

async function resolveBand(env, args) {
  const bands = await listBands(env);
  if (args.band_key) {
    const b = bands.find((x) => x.band_key === args.band_key);
    if (b) return b;
    throw new Error("그 band_key를 가진 밴드를 내 밴드 목록에서 찾지 못했습니다.");
  }
  const name = String(args.band_name || "").trim();
  if (!name) throw new Error("band_name 또는 band_key를 알려 주세요. (band_list로 목록 확인)");
  const exact = bands.filter((x) => x.name === name);
  if (exact.length === 1) return exact[0];
  const part = bands.filter((x) => x.name.includes(name));
  if (part.length === 1) return part[0];
  if (exact.length + part.length === 0) throw new Error(`'${name}' 이름의 밴드를 찾지 못했습니다.`);
  throw new Error(`'${name}'에 맞는 밴드가 여러 개입니다: ${part.map((x) => x.name).join(", ")}. band_key로 지정해 주세요.`);
}

function writeAllowed(env, band) {
  const list = String(env.WRITE_BANDS || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return list.includes(band.name) || list.includes(band.band_key);
}

// ---------- 도구 실행 ----------
async function callTool(name, args, env) {
  if (name === "band_list") {
    const bands = await listBands(env);
    if (!bands.length) return "가입한 밴드가 없습니다.";
    const lines = bands.map(
      (b, i) => `${i + 1}. ${b.name} (멤버 ${b.member_count ?? "?"}명)${writeAllowed(env, b) ? " ✍️글쓰기 허용" : ""}\n   band_key: ${b.band_key}`
    );
    return `[내 밴드 ${bands.length}개]\n${lines.join("\n")}`;
  }

  if (name === "band_posts") {
    const band = await resolveBand(env, args);
    const limit = Math.min(Math.max(parseInt(args.limit || 10, 10) || 10, 1), 20);
    const params = { band_key: band.band_key, locale: "ko_KR" };
    if (args.page_token) {
      try {
        Object.assign(params, JSON.parse(atob(args.page_token)));
      } catch {
        throw new Error("page_token 형식이 올바르지 않습니다.");
      }
    }
    const data = await bandGet(env, "/v2/band/posts", params);
    const items = (data.items || []).slice(0, limit);
    if (!items.length) return `[${band.name}] 글이 없습니다.`;
    const lines = items.map(
      (p, i) =>
        `${i + 1}. ${kst(p.created_at)} · ${p.author?.name || "?"} · 댓글 ${p.comment_count ?? 0}\n   ${short(p.content, 400)}\n   post_key: ${p.post_key}`
    );
    const next = data.paging?.next_params;
    const more = next ? `\n\n(더 보기 page_token: ${btoa(JSON.stringify(next))})` : "";
    return `[${band.name}] 최근 글 ${items.length}개\n${lines.join("\n")}${more}`;
  }

  if (name === "band_comments") {
    const band = await resolveBand(env, args);
    if (!args.post_key) throw new Error("post_key가 필요합니다.");
    const data = await bandGet(env, "/v2/band/post/comments", { band_key: band.band_key, post_key: args.post_key });
    const items = data.items || [];
    if (!items.length) return "댓글이 없습니다.";
    return `[${band.name}] 댓글 ${items.length}개\n` +
      items.map((c, i) => `${i + 1}. ${kst(c.created_at)} · ${c.author?.name || "?"}: ${short(c.content, 300)}`).join("\n");
  }

  if (name === "band_write_post") {
    const band = await resolveBand(env, args);
    if (!writeAllowed(env, band)) {
      throw new Error(`'${band.name}' 밴드는 글쓰기가 허용되지 않았습니다. Cloudflare의 WRITE_BANDS 변수에 밴드 이름을 추가해야 합니다.`);
    }
    const content = String(args.content || "").trim();
    if (!content) throw new Error("본문(content)이 비어 있습니다.");
    const data = await bandPost(env, "/v2.2/band/post/create", {
      band_key: band.band_key,
      content,
      do_push: args.do_push === true ? "true" : "false",
    });
    return `[${band.name}] 글을 올렸습니다. (푸시 ${args.do_push === true ? "보냄" : "안 보냄"})\npost_key: ${data.post_key || "?"}`;
  }

  throw new Error(`알 수 없는 도구: ${name}`);
}

// ---------- MCP (JSON-RPC) ----------
function ok(id, result) {
  return { jsonrpc: "2.0", id, result };
}
function err(id, code, message) {
  return { jsonrpc: "2.0", id: id ?? null, error: { code, message } };
}

async function handleRpc(msg, env) {
  const { id, method, params } = msg || {};
  if (method === "initialize") {
    return ok(id, {
      protocolVersion: params?.protocolVersion || "2025-06-18",
      capabilities: { tools: {} },
      serverInfo: SERVER,
    });
  }
  if (method === "ping") return ok(id, {});
  if (method === "tools/list") return ok(id, { tools: TOOLS });
  if (method === "tools/call") {
    try {
      const text = await callTool(params?.name, params?.arguments || {}, env);
      return ok(id, { content: [{ type: "text", text }] });
    } catch (e) {
      return ok(id, { isError: true, content: [{ type: "text", text: String(e.message || e) }] });
    }
  }
  if (id === undefined) return null; // 알림(notification)은 응답 없음
  return err(id, -32601, "지원하지 않는 메서드: " + method);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const secret = String(env.MCP_TOKEN || "").trim();
    if (!secret || decodeURIComponent(url.pathname).trim() !== `/mcp/${secret}`) {
      return new Response("Not found", { status: 404 });
    }
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405 });

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response("Bad request", { status: 400 });
    }
    const headers = { "Content-Type": "application/json" };
    if (Array.isArray(body)) {
      const out = (await Promise.all(body.map((m) => handleRpc(m, env)))).filter(Boolean);
      return out.length ? new Response(JSON.stringify(out), { headers }) : new Response(null, { status: 202 });
    }
    const out = await handleRpc(body, env);
    return out ? new Response(JSON.stringify(out), { headers }) : new Response(null, { status: 202 });
  },
};
