#!/usr/bin/env node
/**
 * yt_gemini_watch — 제미나이가 유튜브 주소를 직접 보고 「말」과 「화면」을 따로 받아 적는다.
 *
 *   node yt_gemini_watch.mjs <주소> [--out 폴더] [--only speech|screen]
 *                            [--from mm:ss] [--to mm:ss] [--focus "볼 것"] [--model 이름]
 *
 * 쓰는 때: 이 컴퓨터가 youtube.com 에 못 들어가 yt-dlp 가 막힐 때. 영상은 구글 쪽에서 읽는다.
 * 키: GEMINI_API_KEY 환경변수가 있으면 쓰고, 없으면 키 없이 부른다(프록시가 키를 넣어 주는 환경).
 * 공개 영상만 된다.
 *
 * 말과 화면을 **한 번에 묻지 않고 두 번 따로** 묻는다 — 한꺼번에 물으면 말로 들은 숫자가
 * 화면에서 읽은 것처럼 섞여 나온다. 갈라 적는 일은 이 따로 묻기에서 시작한다.
 * 나가는 파일: gemini_<speech|screen>[_<구간>].<모델>.md — 모델 이름이 파일 이름에 들어간다.
 * 서로 다른 모델로 같은 폴더에 읽혀도 앞 결과를 덮지 않으므로, 둘을 나란히 대조할 수 있다.
 * 파일이 생겼을 때만 종료코드 0 이다.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

/* Node 의 fetch 는 HTTPS_PROXY 를 기본으로 안 탄다. 프록시가 키를 넣어 주는 환경에서는 그대로 두면 403 이다. */
if ((process.env.HTTPS_PROXY || process.env.https_proxy) && !process.env.NODE_USE_ENV_PROXY) {
  const again = spawnSync(process.execPath, [process.argv[1], ...process.argv.slice(2)],
    { stdio: "inherit", env: { ...process.env, NODE_USE_ENV_PROXY: "1", NODE_NO_WARNINGS: "1" } });
  process.exit(again.status ?? 1);
}

const args = process.argv.slice(2);
const opt = (name, def = null) => { const i = args.indexOf(name); return i >= 0 && args[i + 1] ? args[i + 1] : def; };

const SPEECH = "이 영상에서 **들리는 말만** 시각(mm:ss)과 함께 받아 적어라. 화면에 보이는 글자나 자막으로 말을 채우지 마라. "
  + "들리지 않거나 못 알아들은 곳은 [불명] 이라고 적어라. 숫자·고유명사·명령어는 들린 그대로 적고, 확신이 낮으면 (?) 를 붙여라. "
  + "요약하지 말고, 말이 없는 구간은 [말 없음] 이라고 적어라. 영상이 한국어가 아니면 원문 뒤에 한국어 뜻을 괄호로 붙여라.";

const SCREEN = "이 영상에서 **화면에 실제로 보이는 것만** 시각(mm:ss)과 함께 적어라. 소리·말로 들은 내용으로 빈칸을 채우지 마라. "
  + "적을 것: 화면에 뜬 글자·숫자(보이는 그대로 따옴표 안에), 메뉴·버튼·입력칸 이름, 무엇을 누르고 입력했는지, 설정값, 표·차트의 값, 터미널 명령. "
  + "글자가 작거나 가려져 읽기 어려우면 [판독 불가] 라고 적어라. 숫자를 짐작으로 만들지 마라. "
  + "말하는 사람 얼굴이나 배경뿐인 구간은 한 줄로 [사람만 나옴] 이라고 적어라.";

/** "1:02:03" · "02:10" · "130" → 초 */
function toSeconds(text) {
  const parts = String(text).split(":").map(Number);
  if (parts.some((n) => !Number.isFinite(n))) return null;
  return parts.reduce((total, n) => total * 60 + n, 0);
}

/** 초 → "mmss" (파일 이름용). 0:02 와 00:02 가 같은 이름이 되고, 1:02:03 은 6203 이 된다. */
const stamp = (s) => String(Math.floor(s / 60)).padStart(2, "0") + String(s % 60).padStart(2, "0");

async function ask(url, prompt, { model, from, to, key }) {
  const filePart = { fileData: { fileUri: url, mimeType: "video/*" } };
  if (from != null || to != null) {
    filePart.videoMetadata = {};
    if (from != null) filePart.videoMetadata.startOffset = `${from}s`;
    if (to != null) filePart.videoMetadata.endOffset = `${to}s`;
  }
  const body = JSON.stringify({
    contents: [{ parts: [filePart, { text: prompt }] }],
    generationConfig: { temperature: 0 },
  });
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
  const headers = { "Content-Type": "application/json", ...(key ? { "x-goog-api-key": key } : {}) };

  let last = "";
  for (const wait of [0, 3000, 8000]) {
    if (wait) await new Promise((r) => setTimeout(r, wait));
    const res = await fetch(endpoint, { method: "POST", headers, body });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      const text = (data.candidates?.[0]?.content?.parts ?? []).map((p) => p.text ?? "").join("").trim();
      if (text) return text;
      last = `답이 비었습니다 — finishReason=${data.candidates?.[0]?.finishReason ?? "?"} blockReason=${data.promptFeedback?.blockReason ?? "-"}`;
      break;
    }
    last = `HTTP ${res.status} ${data.error?.message ?? ""}`.trim();
    if (res.status === 403 && !key) last += " — 키가 없습니다. GEMINI_API_KEY 를 환경변수로 주세요(aistudio.google.com 에서 무료 발급).";
    if (![429, 500, 503].includes(res.status)) break;   // 다시 해도 소용없는 오류는 바로 끝낸다
    if (res.status === 429 && /limit: 0/.test(last)) break;   // 이 모델은 무료 한도가 0 — 기다려도 안 풀린다
  }
  throw new Error(last);
}

async function main() {
  const url = args.find((a) => /^https?:\/\//.test(a));
  if (!url || !/(youtube\.com|youtu\.be)\//.test(url)) {
    console.error('쓰기: node yt_gemini_watch.mjs <유튜브 주소> [--out 폴더] [--only speech|screen] [--from mm:ss] [--to mm:ss] [--focus "볼 것"] [--model 이름]');
    process.exitCode = 2; return;
  }
  const only = opt("--only");
  if (only && !["speech", "screen"].includes(only)) { console.error("--only 는 speech 또는 screen"); process.exitCode = 2; return; }
  const from = opt("--from") ? toSeconds(opt("--from")) : null;
  const to = opt("--to") ? toSeconds(opt("--to")) : null;
  if ((opt("--from") && from == null) || (opt("--to") && to == null)) { console.error("--from · --to 는 mm:ss 로"); process.exitCode = 2; return; }

  const model = opt("--model", "gemini-flash-latest");
  const key = process.env.GEMINI_API_KEY || null;
  const out = resolve(opt("--out", "yt_out"));
  const focus = opt("--focus");
  const range = from != null || to != null ? `_${from != null ? stamp(from) : "처음"}-${to != null ? stamp(to) : "끝"}` : "";
  const tag = model.replace(/[^\w.-]/g, "-");
  mkdirSync(out, { recursive: true });

  const jobs = [];
  if (only !== "screen") jobs.push(["speech", SPEECH]);
  if (only !== "speech") jobs.push(["screen", SCREEN + (focus ? ` 특히 이것을 자세히 봐라: ${focus}` : "")]);

  const results = await Promise.allSettled(jobs.map(([, prompt]) => ask(url, prompt, { model, from, to, key })));
  let written = 0;
  results.forEach((r, i) => {
    const [kind] = jobs[i];
    if (r.status !== "fulfilled") { console.error(`${kind}: 실패 — ${r.reason.message}`); return; }
    const file = join(out, `gemini_${kind}${range}.${tag}.md`);
    const head = `<!-- 제미나이가 읽은 ${kind === "speech" ? "말" : "화면"} · 모델 ${model} · ${url} · 범위 ${opt("--from", "처음")}~${opt("--to", "끝")} · ${new Date().toISOString().slice(0, 10)} -->\n\n`;
    writeFileSync(file, head + r.value + "\n", "utf8");
    console.log(`${kind}: ${file}`);
    written++;
  });
  if (written !== jobs.length) process.exitCode = 1;
}

main().catch((e) => { console.error(`실패 — ${e.message}`); process.exitCode = 1; });
