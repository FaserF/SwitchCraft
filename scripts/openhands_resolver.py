"""Autonomous OpenHands & OmniRoute Issue/PR Resolver for @FaserF Fleet.

Replaces legacy no-op stubs with an OmniRoute OpenAI-compatible ReAct tool loop
that gathers failing CI logs, PR review comments, or issue details, edits code,
verifies tests and linters locally before pushing, and opens or updates PRs.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

MAX_READ_CHARS = 16000
MAX_CMD_CHARS = 8000
MAX_AUTO_COMMITS_PER_PR = 2
REPO_ROOT = Path.cwd()

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List tracked repository files matching optional substring.",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string", "default": ""}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a line slice of a workspace file (never reads .env/secrets).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "default": 1},
                    "end_line": {"type": "integer", "default": 200},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write full content to a repository file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace an exact unique target string in a repository file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "target": {"type": "string"},
                    "replacement": {"type": "string"},
                },
                "required": ["path", "target", "replacement"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a verification, test, lint, or search command inside the repo.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Call when fix is implemented AND verified, or if genuinely blocked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["resolved", "no_changes", "blocked"]},
                    "summary": {"type": "string"},
                },
                "required": ["status", "summary"],
            },
        },
    },
]


def run_cmd(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Execute a subprocess safely inside REPO_ROOT."""
    res = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def gh_api(path: str, token: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    """Call GitHub REST API cleanly."""
    url = path if path.startswith("https://") else f"https://api.github.com/{path.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "FaserF-OpenHands-Resolver",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw.strip() else None


def safe_repo_path(rel_path: str) -> Path:
    """Resolve rel_path strictly inside REPO_ROOT and block sensitive files."""
    clean = rel_path.strip().lstrip("/")
    target = (REPO_ROOT / clean).resolve()
    if REPO_ROOT not in target.parents and target != REPO_ROOT:
        raise ValueError(f"Path escapes repository root: {rel_path}")
    lower = target.name.lower()
    if lower == ".env" or lower.startswith(".env.") or lower.endswith((".pem", ".key")):
        raise ValueError(f"Access to sensitive file denied: {rel_path}")
    return target


def exec_tool(name: str, args: dict[str, Any]) -> str:
    """Execute one ReAct tool call cleanly."""
    if name == "list_files":
        pat = (args.get("pattern") or "").lower()
        code, out, err = run_cmd(["git", "ls-files"])
        if code != 0:
            return f"Error listing files: {err}"
        files = [line for line in out.splitlines() if not pat or pat in line.lower()]
        return "\n".join(files[:300]) or "(no matching files)"

    if name == "read_file":
        p = safe_repo_path(str(args["path"]))
        if not p.is_file():
            return f"File not found: {args['path']}"
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, int(args.get("start_line") or 1))
        end = min(len(lines), int(args.get("end_line") or 200))
        numbered = [f"{i}: {lines[i - 1]}" for i in range(start, end + 1)]
        return "\n".join(numbered)[:MAX_READ_CHARS]

    if name == "write_file":
        p = safe_repo_path(str(args["path"]))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(args["content"]), encoding="utf-8")
        return f"Wrote {args['path']} ({len(str(args['content']))} chars)."

    if name == "edit_file":
        p = safe_repo_path(str(args["path"]))
        if not p.is_file():
            return f"File not found: {args['path']}"
        text = p.read_text(encoding="utf-8", errors="replace")
        target = str(args["target"])
        replacement = str(args["replacement"])
        count = text.count(target)
        if count != 1:
            return f"Target match count must be 1 (found {count}) in {args['path']}."
        p.write_text(text.replace(target, replacement, 1), encoding="utf-8")
        return f"Edited {args['path']} successfully."

    if name == "run_shell":
        cmd = str(args["command"])
        res = subprocess.run(
            ["bash", "-lc", cmd],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        combined = f"exit={res.returncode}\n{res.stdout}\n{res.stderr}".strip()
        return combined[:MAX_CMD_CHARS]

    return f"Unknown tool: {name}"


def build_context_prompt(
    repo: str,
    token: str,
    is_pr: bool,
    number: int,
    title: str,
    body: str,
    base_ref: str,
    failed_run_id: str,
) -> tuple[str, list[str]]:
    """Collect review feedback, failed CI logs, conflict markers, and issue comments."""
    sections: list[str] = [
        f"Repository: {repo}",
        f"Target: {'PR' if is_pr else 'Issue'} #{number}",
        f"Title: {title}",
        f"Description:\n{(body or '(empty)')[:3000]}",
    ]
    conflict_files: list[str] = []

    if is_pr:
        run_cmd(["git", "fetch", "origin", base_ref])
        merge_res = run_cmd(["git", "merge", f"origin/{base_ref}", "--no-commit", "--no-ff"])
        if merge_res[0] != 0:
            _, status_out, _ = run_cmd(["git", "diff", "--name-only", "--diff-filter=U"])
            conflict_files = [f for f in status_out.splitlines() if f.strip()]
            sections.append(f"MERGE CONFLICTS DETECTED against {base_ref}: {conflict_files}")
        else:
            run_cmd(["git", "merge", "--abort"])

        _, diff_stat, _ = run_cmd(["git", "diff", f"origin/{base_ref}...HEAD", "--stat"])
        sections.append(f"PR Diff Stat:\n{diff_stat[:2000]}")

        if repo and number > 0:
            try:
                comments = gh_api(f"repos/{repo}/issues/{number}/comments", token) or []
                review_comments = gh_api(f"repos/{repo}/pulls/{number}/comments", token) or []
                reviews = gh_api(f"repos/{repo}/pulls/{number}/reviews", token) or []
                fb_lines = []
                for item in reviews + review_comments + comments[-10:]:
                    author = ((item.get("user") or {}).get("login") or "").lower()
                    txt = (item.get("body") or "").strip()
                    if txt and any(k in author for k in ("coderabbit", "hermes", "faserf", "github-actions")):
                        loc = f"{item.get('path')}:{item.get('line')} " if item.get("path") else ""
                        fb_lines.append(f"- [{author}] {loc}{txt[:500]}")
                if fb_lines:
                    sections.append("Review Comments / Bot Feedback:\n" + "\n".join(fb_lines[:15]))
            except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
                sections.append(f"(Could not load PR comments cleanly: {exc})")

        if failed_run_id:
            code, out, _ = run_cmd(["gh", "run", "view", failed_run_id, "--log-failed"], timeout=60)
            if code == 0 and out:
                sections.append(f"Failing Workflow Run #{failed_run_id} Log Tail:\n{out[-5000:]}")
    else:
        if repo and number > 0:
            try:
                comments = gh_api(f"repos/{repo}/issues/{number}/comments", token) or []
                if comments:
                    snippets = [f"- {(c.get('user') or {}).get('login')}: {(c.get('body') or '')[:400]}" for c in comments[-6:]]
                    sections.append("Issue Comments:\n" + "\n".join(snippets))
            except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
                sections.append(f"(Could not load issue comments: {exc})")

    return "\n\n".join(sections), conflict_files


def count_recent_auto_commits() -> int:
    """Count consecutive recent autonomous OpenHands commits to prevent loops."""
    code, out, _ = run_cmd(["git", "log", "-n", "5", "--pretty=%s"])
    if code != 0:
        return 0
    return sum(1 for line in out.splitlines() if "[openhands-fix]" in line)


def call_omniroute(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Call OmniRoute OpenAI-compatible chat completions endpoint."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "FaserF-OpenHands-Resolver",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_agent_loop(
    base_url: str,
    api_key: str,
    model: str,
    prompt_context: str,
    max_iterations: int,
) -> tuple[str, str]:
    """Execute bounded OmniRoute tool loop until finish tool or step limit."""
    system_prompt = (
        "You are an autonomous senior software engineer resolving a GitHub Issue or Pull Request.\n"
        "Rules:\n"
        "1. Inspect files, failing logs, review feedback, and merge conflict markers first.\n"
        "2. Never downgrade dependencies or Python versions unless strictly incompatible with core host pins.\n"
        "3. Never resolve merge conflicts blindly with --ours; reconcile both sides properly and remove conflict markers.\n"
        "4. Always run tests and linters via run_shell (e.g. pytest, ruff check, mypy, npm test/lint) BEFORE calling finish.\n"
        "5. Never create placeholder files or fake resolution notes.\n"
        "6. Call finish(status='resolved'|'no_changes'|'blocked', summary='...') when done."
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt_context},
    ]

    for step in range(1, max_iterations + 1):
        print(f"[OpenHands] Iteration {step}/{max_iterations}...")
        resp = call_omniroute(base_url, api_key, model, messages)
        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            content = (msg.get("content") or "").strip()
            return ("no_changes" if not has_git_changes() else "resolved", content or "Completed without explicit finish tool.")

        for tc in tool_calls:
            fn = tc.get("function") or {}
            fn_name = fn.get("name", "")
            try:
                fn_args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                fn_args = {}
            if fn_name == "finish":
                return (
                    str(fn_args.get("status") or "resolved"),
                    str(fn_args.get("summary") or "Completed."),
                )
            try:
                result = exec_tool(fn_name, fn_args)
            except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
                result = f"Tool error: {exc}"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result,
            })

    return ("blocked", f"Reached maximum iteration limit ({max_iterations}) without finishing.")


def has_git_changes() -> bool:
    """Return True if tracked modifications, staged changes, or untracked files exist."""
    code, out, _ = run_cmd(["git", "status", "--porcelain"])
    return code == 0 and bool(out.strip())


def has_unresolved_conflicts() -> bool:
    """Return True if any unmerged conflict files remain."""
    code, out, _ = run_cmd(["git", "diff", "--name-only", "--diff-filter=U"])
    return code == 0 and bool(out.strip())


def write_outcome(status: str, summary: str) -> None:
    """Write outcome fields to GITHUB_OUTPUT when running inside Actions."""
    out_file = os.environ.get("GITHUB_OUTPUT")
    if not out_file:
        return
    with open(out_file, "a", encoding="utf-8") as fh:
        fh.write(f"resolver_status={status}\n")
        clean_summary = re.sub(r"[\r\n]+", " ", summary).strip()[:500]
        fh.write(f"resolver_summary={clean_summary}\n")


def main() -> int:
    """Run autonomous resolver for PR or Issue context."""
    is_pr = os.environ.get("IS_PR", "false").lower() == "true"
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    number = int(os.environ.get("TARGET_NUMBER", "0") or 0)
    title = os.environ.get("TARGET_TITLE", "")
    body = os.environ.get("TARGET_BODY", "")
    head_ref = os.environ.get("HEAD_REF", "")
    base_ref = os.environ.get("BASE_REF", "main")
    default_branch = os.environ.get("DEFAULT_BRANCH", "main")
    failed_run_id = os.environ.get("FAILED_RUN_ID", "")
    base_url = (os.environ.get("OMNIROUTE_BASE_URL") or "").strip()
    api_key = (os.environ.get("OMNIROUTE_API_KEY") or "").strip()
    model = os.environ.get("MODEL", "auto/coding") or "auto/coding"
    max_iter = int(os.environ.get("MAX_ITERATIONS", "20") or 20)
    token = os.environ.get("GH_TOKEN", "")

    if number <= 0:
        print("Error: TARGET_NUMBER must be > 0.", file=sys.stderr)
        write_outcome("blocked", "Missing target PR/Issue number.")
        return 1

    if not base_url or not api_key:
        msg = "OMNIROUTE_BASE_URL or OMNIROUTE_API_KEY is missing; configure GitHub Secrets."
        print(msg, file=sys.stderr)
        write_outcome("blocked", msg)
        return 1

    if is_pr and count_recent_auto_commits() >= MAX_AUTO_COMMITS_PER_PR:
        msg = f"Loop guard: PR #{number} already has {MAX_AUTO_COMMITS_PER_PR} consecutive [openhands-fix] commits."
        print(msg)
        write_outcome("blocked", msg)
        return 0

    if not is_pr:
        branch_name = f"openhands/issue-{number}"
        code, _, err = run_cmd(["git", "checkout", "-B", branch_name])
        if code != 0:
            write_outcome("blocked", f"Failed to create branch {branch_name}: {err}")
            return 1
        head_ref = branch_name

    prompt_ctx, _ = build_context_prompt(repo, token, is_pr, number, title, body, base_ref, failed_run_id)
    try:
        status, summary = run_agent_loop(base_url, api_key, model, prompt_ctx, max_iter)
    except urllib.error.URLError as exc:
        msg = f"OmniRoute request failed: {exc}"
        print(msg, file=sys.stderr)
        write_outcome("blocked", msg)
        return 1

    if has_unresolved_conflicts():
        run_cmd(["git", "merge", "--abort"])
        msg = "Aborted: unresolved merge conflict markers remained."
        write_outcome("blocked", msg)
        return 1

    if has_git_changes() and status == "resolved":
        run_cmd(["git", "add", "-A"])
        commit_msg = (
            f"fix(agent): resolve #{number} CI/review feedback [openhands-fix]"
            if is_pr
            else f"fix: resolve #{number} - {title} [openhands-fix]"
        )
        c_code, _, c_err = run_cmd(["git", "commit", "-m", commit_msg])
        if c_code != 0:
            write_outcome("blocked", f"git commit failed: {c_err}")
            return 1
        target_branch = head_ref or default_branch
        p_code, _, p_err = run_cmd(["git", "push", "origin", f"HEAD:{target_branch}"])
        if p_code != 0:
            write_outcome("blocked", f"git push failed: {p_err}")
            return 1
        if not is_pr:
            run_cmd([
                "gh",
                "pr",
                "create",
                "--title",
                f"fix: resolve #{number} - {title}",
                "--body",
                f"Closes #{number}\n\n{summary}\n\nAutomated verified fix by OpenHands & Hermes Fleet AI.",
                "--head",
                target_branch,
                "--base",
                default_branch,
            ])

    write_outcome(status, summary)
    print(f"Resolver finished: status={status} summary={summary}")
    return 1 if status == "blocked" and not has_git_changes() else 0


if __name__ == "__main__":
    raise SystemExit(main())
