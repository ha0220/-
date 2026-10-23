#!/usr/bin/env python3
"""뉴스 브리핑 — 버튼 한 번에 만들기.

ROUTINE_PROMPT.md 의 루틴 프롬프트를 내 컴퓨터의 Claude Code(`claude -p`)로 실행해
briefings/YYYY-MM-DD.html 을 만들고 브라우저로 연다.

    python briefing_app.py              # 창(버튼) 모드
    python briefing_app.py --no-gui     # 터미널 모드 (tkinter 가 없을 때 자동 전환)
"""
from __future__ import annotations

import argparse
import html
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROMPT_FILE = ROOT / "ROUTINE_PROMPT.md"
OUT_DIR = ROOT / "briefings"
KST = timezone(timedelta(hours=9))
WEEKDAYS = "월화수목금토일"
MIN_CHARS = 5000  # 루틴 규칙: 본문 가시 텍스트 최소 글자 수
TIMEOUT_SEC = 40 * 60
ALLOWED_TOOLS = "WebSearch,WebFetch,Read,Write"
CLAUDE_HELP = (
    "Claude Code(`claude` 명령)를 찾지 못했습니다.\n"
    "1) https://claude.com/claude-code 안내대로 설치하고\n"
    "2) 터미널에서 `claude` 를 한 번 실행해 로그인한 뒤 다시 눌러 주세요."
)


class BriefingError(Exception):
    pass


class Cancelled(Exception):
    pass


# ---------------------------------------------------------------- 프롬프트 ----

def load_routine_prompt() -> str:
    """ROUTINE_PROMPT.md 에서 '---' 아래의 프롬프트 원문만 꺼낸다."""
    text = PROMPT_FILE.read_text(encoding="utf-8")
    parts = re.split(r"^---\s*$", text, maxsplit=1, flags=re.M)
    if len(parts) < 2 or not parts[1].strip():
        raise BriefingError("ROUTINE_PROMPT.md 에서 '---' 아래 프롬프트 본문을 찾지 못했습니다.")
    return parts[1].strip()


def latest_template(final: Path) -> Path | None:
    """디자인 기준으로 쓸 가장 최근 브리핑 HTML."""
    others = sorted(p for p in OUT_DIR.glob("????-??-??.html") if p != final)
    if others:
        return others[-1]
    return final if final.exists() else None


def build_prompt(today: datetime, part: Path, template: Path | None) -> str:
    weekday = WEEKDAYS[today.weekday()]
    if template:
        design = f"디자인 템플릿은 Artifact 링크 대신 로컬 파일 `{template}` 을 Read 로 읽어 HTML/CSS 구조를 그대로 재사용한다."
    else:
        design = "로컬에 템플릿 파일이 없으므로 3단계의 원칙과 페이지 구성 순서대로 직접 작성한다."
    override = f"""
## 로컬 실행 지침 (위 3·4단계보다 우선한다)
- 오늘은 {today:%Y-%m-%d}({weekday}요일), 한국 시간 기준이다. 날짜는 확정되었으니 `date` 명령을 쓰지 않는다. 휴장일은 검색으로 확인한다.
- {design}
- 이 브리핑의 이름은 "뉴스 브리핑"이다. `<title>` 은 `뉴스 브리핑 {today:%m.%d}`, 머리말 제목은 `뉴스 브리핑 — {today.year}년 {today.month}월 {today.day}일({weekday})` 로 쓴다(위 프롬프트의 옛 이름 대신).
- 완성한 HTML 전체를 Write 도구로 `{part}` 에 저장한다. 이 경로 밖의 파일은 만들거나 고치지 않는다.
- Artifact 게시, PushNotification, 사용자에게 질문은 하지 않는다(도구도 없다). 글자 수 확인은 프로그램이 하므로 python 을 실행하지 않고, 본문 가시 텍스트 7,000자 이상을 목표로 쓴다.
- 마지막 응답에는 3줄 요약만 쓴다.
"""
    return load_routine_prompt() + "\n" + override


def build_repair_prompt(part: Path, chars: int) -> str:
    return (
        f"`{part}` 의 브리핑 HTML 은 본문 가시 텍스트가 {chars:,}자로 최소 기준 {MIN_CHARS:,}자에 못 미친다. "
        "Read 로 파일을 읽고, 내용이 얇은 섹션(지표 해설, 부처별 발표, 시나리오, 포트폴리오 관점, 체크리스트)을 "
        "사실·해석·추정 구분을 지켜 보강한 뒤 같은 경로에 Write 로 전체를 덮어써라. "
        "새 사실이 필요하면 WebSearch 로 확인하고, 확인하지 못한 것은 '확인 필요'로 적는다. "
        "질문하지 말고, 마지막 응답은 한 줄로 끝낸다."
    )


def visible_chars(markup: str) -> int:
    """태그를 제거한 가시 텍스트 글자 수(연속 공백은 1칸으로)."""
    text = re.sub(r"(?is)<(script|style|title)\b.*?</\1>", " ", markup)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return len(re.sub(r"\s+", " ", text).strip())


# ------------------------------------------------------------------- 실행 ----

class Job:
    """claude -p 를 돌려 오늘 브리핑 파일을 만든다."""

    def __init__(self, claude: str, log):
        self.claude = claude
        self.log = log
        self.proc: subprocess.Popen | None = None
        self.cancelled = False
        self.timed_out = False
        self.searches = 0
        self.result = ""
        self.result_is_error = False
        self.tail: list[str] = []

    # -- 제어
    def cancel(self):
        self.cancelled = True
        self._kill()

    def _kill(self):
        proc = self.proc
        if not proc or proc.poll() is not None:
            return
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               capture_output=True, creationflags=0x08000000)
            else:
                os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            pass

    def _on_timeout(self):
        self.timed_out = True
        self._kill()

    # -- claude 한 번 실행
    def run_claude(self, prompt: str):
        cmd = [self.claude, "-p", "--output-format", "stream-json", "--verbose",
               "--no-session-persistence", "--allowedTools", ALLOWED_TOOLS]
        kwargs: dict = {}
        if os.name == "nt":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        self.result, self.result_is_error, self.tail = "", False, []
        try:
            self.proc = subprocess.Popen(
                cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                bufsize=1, **kwargs)
        except OSError as exc:
            raise BriefingError(f"claude 를 실행하지 못했습니다: {exc}\n\n{CLAUDE_HELP}") from exc

        timer = threading.Timer(TIMEOUT_SEC, self._on_timeout)
        timer.start()
        try:
            try:
                self.proc.stdin.write(prompt)
                self.proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass  # 바로 종료된 경우 — 아래에서 종료 코드와 출력으로 원인을 보고한다
            for line in self.proc.stdout:
                self._handle(line)
            code = self.proc.wait()
        finally:
            timer.cancel()

        if self.cancelled:
            raise Cancelled()
        if self.timed_out:
            raise BriefingError(f"{TIMEOUT_SEC // 60}분 안에 끝나지 않아 중단했습니다.")
        if code != 0 or self.result_is_error:
            detail = self.result or "\n".join(self.tail[-8:]) or f"종료 코드 {code}"
            raise BriefingError(f"Claude 실행이 실패했습니다.\n{detail}")

    def _handle(self, line: str):
        line = line.strip()
        if not line:
            return
        try:
            event = json.loads(line)
        except ValueError:
            self.tail.append(line)
            return
        kind = event.get("type")
        if kind == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    self._on_tool(block.get("name", ""), block.get("input") or {})
        elif kind == "result":
            self.result = str(event.get("result") or "")
            self.result_is_error = bool(event.get("is_error"))

    def _on_tool(self, name: str, args: dict):
        if name == "WebSearch":
            self.searches += 1
            self.log(f"웹 검색 {self.searches}회 — {args.get('query', '')}")
        elif name == "WebFetch":
            self.log(f"페이지 읽는 중 — {args.get('url', '')}")
        elif name == "Read":
            self.log("템플릿·초안 읽는 중")
        elif name == "Write":
            self.log("브리핑 파일 저장 중")

    # -- 전체 흐름
    def generate(self, today: datetime) -> Path:
        OUT_DIR.mkdir(exist_ok=True)
        final = OUT_DIR / f"{today:%Y-%m-%d}.html"
        part = OUT_DIR / f".{final.stem}.part.html"  # 성공 전에는 기존 파일을 건드리지 않는다
        part.unlink(missing_ok=True)

        template = latest_template(final)
        self.log(f"{today:%Y-%m-%d}({WEEKDAYS[today.weekday()]}) 브리핑 작성 시작 — 보통 10~20분 걸립니다")
        self.run_claude(build_prompt(today, part, template))
        chars = self._check(part)

        if chars < MIN_CHARS:
            self.log(f"본문 {chars:,}자 — 기준 {MIN_CHARS:,}자 미달, 한 번 보강합니다")
            self.run_claude(build_repair_prompt(part, chars))
            chars = self._check(part)
            if chars < MIN_CHARS:
                self.log(f"주의: 보강 후에도 본문이 {chars:,}자입니다. 내용을 확인해 주세요.")

        os.replace(part, final)
        self.log(f"완료 — 본문 {chars:,}자, 웹 검색 {self.searches}회 → {final.name}")
        return final

    def _check(self, part: Path) -> int:
        if not part.exists():
            hint = f"\n{self.result}" if self.result else ""
            raise BriefingError(f"브리핑 파일이 만들어지지 않았습니다.{hint}")
        markup = part.read_text(encoding="utf-8", errors="replace")
        if "<title" not in markup:
            raise BriefingError("만들어진 파일이 브리핑 HTML 형식이 아닙니다(<title> 없음).")
        return visible_chars(markup)


# ------------------------------------------------------------------ 도우미 ----

def find_claude(explicit: str | None) -> str:
    found = explicit or os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if not found:
        raise BriefingError(CLAUDE_HELP)
    return found


def open_path(path: Path):
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_in_browser(path: Path):
    webbrowser.open(path.resolve().as_uri())


def say(text: str):
    if sys.stdout:  # pythonw 로 띄우면 stdout 이 없다
        print(text, flush=True)


# ---------------------------------------------------------------- 터미널 모드 ----

def run_cli(args) -> int:
    job = None
    try:
        job = Job(find_claude(args.claude), lambda m: say(f"[{time.strftime('%H:%M:%S')}] {m}"))
        final = job.generate(datetime.now(KST))
    except KeyboardInterrupt:
        if job:
            job.cancel()
        say("중지했습니다.")
        return 130
    except Cancelled:
        say("중지했습니다.")
        return 130
    except BriefingError as exc:
        say(f"오류: {exc}")
        return 1
    if not args.no_open:
        open_in_browser(final)
    return 0


# ------------------------------------------------------------------- 창 모드 ----

def run_gui(args) -> int:
    import tkinter as tk
    from tkinter import messagebox, ttk

    events: queue.Queue = queue.Queue()
    state = {"job": None, "started": 0.0}

    root = tk.Tk()
    root.title("뉴스 브리핑")
    root.geometry("620x560")
    root.minsize(480, 420)

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="뉴스 브리핑", font=("", 16, "bold")).pack(anchor="w")
    date_label = ttk.Label(frame, foreground="#555")
    date_label.pack(anchor="w", pady=(2, 12))

    main_btn = tk.Button(frame, font=("", 15, "bold"), height=2, bg="#1F4E79", fg="white",
                         activebackground="#2B6AA3", activeforeground="white", relief="flat", cursor="hand2")
    main_btn.pack(fill="x")

    bar = ttk.Progressbar(frame, mode="indeterminate")
    bar.pack(fill="x", pady=(12, 4))
    status = ttk.Label(frame, text="", anchor="w")
    status.pack(fill="x")

    log_box = tk.Text(frame, height=14, state="disabled", wrap="word", font=("", 10))
    log_box.pack(fill="both", expand=True, pady=(8, 8))

    row = ttk.Frame(frame)
    row.pack(fill="x")
    open_btn = ttk.Button(row, text="오늘 브리핑 열기")
    open_btn.pack(side="left")
    folder_btn = ttk.Button(row, text="브리핑 폴더 열기", command=lambda: (OUT_DIR.mkdir(exist_ok=True), open_path(OUT_DIR)))
    folder_btn.pack(side="left", padx=8)
    stop_btn = ttk.Button(row, text="중지")
    stop_btn.pack(side="right")

    def today_file() -> Path:
        return OUT_DIR / f"{datetime.now(KST):%Y-%m-%d}.html"

    def append_log(text: str):
        log_box.configure(state="normal")
        log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {text}\n")
        log_box.see("end")
        log_box.configure(state="disabled")
        status.configure(text=text)

    def refresh_idle():
        now = datetime.now(KST)
        date_label.configure(text=f"{now:%Y년 %m월 %d일}({WEEKDAYS[now.weekday()]})")
        exists = today_file().exists()
        main_btn.configure(state="normal", text="↻ 오늘 브리핑 다시 만들기" if exists else "☀ 오늘 브리핑 만들기")
        open_btn.configure(state="normal" if exists else "disabled")
        stop_btn.configure(state="disabled")
        bar.stop()

    def worker(job: Job, today: datetime):
        try:
            events.put(("done", job.generate(today)))
        except Cancelled:
            events.put(("cancelled", None))
        except BriefingError as exc:
            events.put(("error", str(exc)))
        except Exception as exc:  # 예기치 못한 오류도 창에 보여 준다
            events.put(("error", f"{type(exc).__name__}: {exc}"))

    def start():
        if today_file().exists() and not messagebox.askyesno(
                "다시 만들기", "오늘 브리핑이 이미 있습니다.\n새로 만들어 덮어쓸까요?\n(웹 검색을 다시 하므로 시간이 걸립니다)"):
            return
        try:
            claude = find_claude(args.claude)
        except BriefingError as exc:
            messagebox.showerror("Claude Code 필요", str(exc))
            return
        job = Job(claude, lambda m: events.put(("log", m)))
        state.update(job=job, started=time.time())
        main_btn.configure(state="disabled", text="브리핑 만드는 중…")
        open_btn.configure(state="disabled")
        stop_btn.configure(state="normal")
        bar.start(12)
        threading.Thread(target=worker, args=(job, datetime.now(KST)), daemon=True).start()
        pump()

    def pump():
        job = state["job"]
        finished = False
        while True:
            try:
                kind, payload = events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                append_log(payload)
            elif kind == "done":
                finished = True
                append_log("브라우저로 엽니다")
                open_in_browser(payload)
            elif kind == "cancelled":
                finished = True
                append_log("중지했습니다")
            elif kind == "error":
                finished = True
                append_log("실패")
                messagebox.showerror("브리핑 실패", payload)
        if finished:
            state["job"] = None
            refresh_idle()
        elif job:
            elapsed = int(time.time() - state["started"])
            root.title(f"뉴스 브리핑 — 작성 중 {elapsed // 60:02d}:{elapsed % 60:02d}")
            root.after(300, pump)
            return
        root.title("뉴스 브리핑")

    def stop():
        if state["job"]:
            append_log("중지하는 중…")
            state["job"].cancel()

    def on_close():
        if state["job"] and not messagebox.askyesno("종료", "브리핑을 만드는 중입니다. 중단하고 닫을까요?"):
            return
        stop()
        root.destroy()

    main_btn.configure(command=start)
    open_btn.configure(command=lambda: open_in_browser(today_file()))
    stop_btn.configure(command=stop)
    root.protocol("WM_DELETE_WINDOW", on_close)
    refresh_idle()
    root.mainloop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="뉴스 브리핑 — 버튼 한 번에 만들기")
    parser.add_argument("--no-gui", action="store_true", help="창 없이 터미널에서 실행")
    parser.add_argument("--no-open", action="store_true", help="완료 후 브라우저를 열지 않음(터미널 모드)")
    parser.add_argument("--claude", help="claude 실행 파일 경로(기본: PATH 에서 검색)")
    args = parser.parse_args()

    if not args.no_gui:
        try:
            import tkinter  # noqa: F401
        except ImportError:
            say("tkinter 가 없어 터미널 모드로 실행합니다.")
            args.no_gui = True
    return run_cli(args) if args.no_gui else run_gui(args)


if __name__ == "__main__":
    sys.exit(main())
