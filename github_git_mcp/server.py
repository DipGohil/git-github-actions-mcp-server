"""Local git + GitHub MCP server."""

import os
import subprocess
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from github import Auth, Github
from mcp.server.fastmcp import FastMCP

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Optional file; does not override variables already set (CI / Cursor env).
load_dotenv(_PROJECT_ROOT / ".env")

mcp = FastMCP("github-git-mcp")


def _err(e: Exception) -> str:
    return f"Error: {e}"


def _resolve_existing_dir(repo_path: str) -> Path:
    p = Path(repo_path).resolve()
    if not p.is_dir():
        raise FileNotFoundError(f"Not a directory or missing: {p}")
    return p


def _git(repo: str, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip() or f"git exited {r.returncode}"
        raise RuntimeError(msg)
    return r.stdout.strip()


def _github() -> Github:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError(
            "Set GITHUB_TOKEN or GH_TOKEN (PAT with repo scope for private repos).",
        )
    return Github(auth=Auth.Token(token))


@mcp.tool()
def git_status(repo_path: str) -> str:
    """Show working tree status in repo_path (absolute path to a git clone)."""
    try:
        d = _resolve_existing_dir(repo_path)
        branch = _git(str(d), "branch", "--show-current")
        sb = _git(str(d), "status", "-sb")
        long_status = _git(str(d), "status")
        return "\n\n".join(
            [
                f"branch: {branch}",
                "short:",
                sb,
                "",
                long_status,
            ],
        )
    except Exception as e:
        return _err(e)


@mcp.tool()
def git_add(repo_path: str, file_globs: list[str] | None = None) -> str:
    """Stage files (git add). Default file_globs is [\".\"] (all changes)."""
    try:
        d = _resolve_existing_dir(repo_path)
        globs = file_globs if file_globs else ["."]
        _git(str(d), "add", *globs)
        return f"Staged: {', '.join(globs)}"
    except Exception as e:
        return _err(e)


@mcp.tool()
def git_commit(repo_path: str, message: str, amend: bool | None = None) -> str:
    """Create a commit with message. Set amend=True for git commit --amend."""
    try:
        d = _resolve_existing_dir(repo_path)
        if amend:
            _git(str(d), "commit", "--amend", "-m", message)
        else:
            _git(str(d), "commit", "-m", message)
        summary = _git(str(d), "log", "-1", "--oneline")
        return f"Committed — {summary}"
    except Exception as e:
        return _err(e)


@mcp.tool()
def git_push(
    repo_path: str,
    remote: str | None = None,
    branch: str | None = None,
    set_upstream: bool | None = None,
) -> str:
    """Push to remote. Defaults: remote=origin, branch=current."""
    try:
        d = _resolve_existing_dir(repo_path)
        r = remote or "origin"
        b = branch or _git(str(d), "branch", "--show-current")
        if set_upstream:
            _git(str(d), "push", "-u", r, b)
        else:
            _git(str(d), "push", r, b)
        return f"Pushed {b} to {r}"
    except Exception as e:
        return _err(e)


@mcp.tool()
def git_pull(
    repo_path: str,
    remote: str | None = None,
    branch: str | None = None,
) -> str:
    """Pull from remote. Defaults remote to origin; branch optional."""
    try:
        d = _resolve_existing_dir(repo_path)
        rem = remote or "origin"
        if branch:
            _git(str(d), "pull", rem, branch)
        else:
            _git(str(d), "pull", rem)
        return f"Pulled from {rem}" + (f" {branch}" if branch else "")
    except Exception as e:
        return _err(e)


@mcp.tool()
def git_branch(
    repo_path: str,
    action: Literal["list", "create", "delete"],
    name: str | None = None,
) -> str:
    """List, create, or delete branches."""
    try:
        d = _resolve_existing_dir(repo_path)
        if action == "list":
            cur = _git(str(d), "branch", "--show-current")
            all_b = _git(str(d), "branch", "-a")
            return f"current: {cur}\n\nall:\n{all_b}"
        if not name:
            return "Error: name is required for create/delete"
        if action == "create":
            _git(str(d), "checkout", "-b", name)
            return f"Created and checked out branch {name}"
        _git(str(d), "branch", "-d", name)
        return f"Deleted local branch {name}"
    except Exception as e:
        return _err(e)


@mcp.tool()
def git_checkout(repo_path: str, ref: str) -> str:
    """Checkout a branch, tag, or commit."""
    try:
        d = _resolve_existing_dir(repo_path)
        _git(str(d), "checkout", ref)
        return f"Checked out {ref}"
    except Exception as e:
        return _err(e)


@mcp.tool()
def git_clone(url: str, target_path: str) -> str:
    """Clone url into target_path (must not exist or must be an empty directory)."""
    try:
        target = Path(target_path).resolve()
        if target.exists():
            entries = list(target.iterdir())
            if entries:
                raise ValueError(f"target_path must be empty or not exist: {target}")
        else:
            target.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["git", "clone", url, str(target)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout or "").strip())
        return f"Cloned into {target}"
    except Exception as e:
        return _err(e)


@mcp.tool()
def git_last_commit(repo_path: str) -> str:
    """Show the latest commit as one line (sha, date, author, message)."""
    try:
        d = _resolve_existing_dir(repo_path)
        return _git(
            str(d),
            "log",
            "-1",
            "--date=iso",
            "--pretty=format:%H%n%an%n%ad%n%s",
        )
    except Exception as e:
        return _err(e)


@mcp.tool()
def git_log(repo_path: str, limit: int | None = None) -> str:
    """Show recent commits. limit defaults to 10 and is capped at 50."""
    try:
        d = _resolve_existing_dir(repo_path)
        n = 10 if limit is None else max(1, min(limit, 50))
        return _git(
            str(d),
            "log",
            f"-n{n}",
            "--date=short",
            "--pretty=format:%h | %ad | %an | %s",
        )
    except Exception as e:
        return _err(e)


@mcp.tool()
def github_list_pulls(
    owner: str,
    repo: str,
    state: Literal["open", "closed", "all"] | None = None,
) -> str:
    """List pull requests for owner/repo."""
    try:
        g = _github()
        r = g.get_repo(f"{owner}/{repo}")
        st = state or "open"
        pulls = r.get_pulls(state=st)
        lines = [
            f"#{p.number} {p.title} ({p.head.ref} → {p.base.ref}) — {p.html_url}"
            for p in pulls[:30]
        ]
        return "\n".join(lines) if lines else "No pull requests."
    except Exception as e:
        return _err(e)


@mcp.tool()
def github_get_pull(owner: str, repo: str, pull_number: int) -> str:
    """Get one pull request by number."""
    try:
        g = _github()
        r = g.get_repo(f"{owner}/{repo}")
        p = r.get_pull(pull_number)
        merged = " (merged)" if p.merged_at else ""
        parts = [
            f"PR #{p.number}: {p.title}",
            f"State: {p.state}{merged}",
            f"{p.head.label} → {p.base.label}",
            p.body or "",
            p.html_url,
        ]
        return "\n\n".join(s for s in parts if s is not None)
    except Exception as e:
        return _err(e)


@mcp.tool()
def github_create_pull(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str | None = None,
    draft: bool | None = None,
) -> str:
    """Open a new pull request (head branch must exist on GitHub)."""
    try:
        g = _github()
        r = g.get_repo(f"{owner}/{repo}")
        pr = r.create_pull(
            base,
            head,
            title=title,
            body=body or "",
            draft=bool(draft) if draft is not None else False,
        )
        return f"Created PR #{pr.number}: {pr.html_url}"
    except Exception as e:
        return _err(e)


@mcp.tool()
def github_merge_pull(
    owner: str,
    repo: str,
    pull_number: int,
    merge_method: Literal["merge", "squash", "rebase"] | None = None,
) -> str:
    """Merge a pull request."""
    try:
        g = _github()
        r = g.get_repo(f"{owner}/{repo}")
        p = r.get_pull(pull_number)
        m = merge_method or "merge"
        result = p.merge(merge_method=m)
        if result.merged:
            return f"Merged PR #{pull_number} (sha {result.sha})"
        return f"Merge API response: merged={result.merged} message={result.message!r}"
    except Exception as e:
        return _err(e)


@mcp.tool()
def github_create_pr_comment(owner: str, repo: str, pull_number: int, body: str) -> str:
    """Add an issue comment on a pull request."""
    try:
        g = _github()
        r = g.get_repo(f"{owner}/{repo}")
        issue = r.get_issue(pull_number)
        c = issue.create_comment(body)
        return f"Comment: {c.html_url}"
    except Exception as e:
        return _err(e)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
