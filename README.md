# GitHub + Git MCP

MCP server for:
- local Git operations against repositories you choose
- GitHub pull request operations using a PAT token

This project runs over MCP stdio transport and is intended to be launched by an MCP client (Cursor, Claude Desktop, etc.).

## Requirements

- Python 3.10+
- `git` on PATH
- GitHub personal access token (`repo` scope is typically required for private repos)

## Quick start

```bash
git clone <your-repo-url>
cd Git_mcp
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Fill token in `.env`:

```env
GITHUB_TOKEN=your_pat_here
# or GH_TOKEN=your_pat_here
```

## Run server manually

```bash
source .venv/bin/activate
python github_git_mcp/server.py
```

## MCP client config

Use your local absolute paths. A template is included in `mcp-config.example.json`.

Create your local config from the template:

```bash
cp mcp-config.example.json mcp-config.json
```

Then edit `mcp-config.json` with your machine-specific paths:

```json
{
  "mcpServers": {
    "github-git": {
      "command": "/ABSOLUTE/PATH/TO/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/github_git_mcp/server.py"]
    }
  }
}
```

Notes:
- This script-path launch avoids import path issues in some clients.
- `.env` is auto-loaded from project root on startup.
- `mcp-config.json` is gitignored because it is machine-specific.

## Tools

### Git

- `git_status(repo_path)`
- `git_add(repo_path, file_globs?)`
- `git_commit(repo_path, message, amend?)`
- `git_push(repo_path, remote?, branch?, set_upstream?)`
- `git_pull(repo_path, remote?, branch?)`
- `git_branch(repo_path, action, name?)`
- `git_checkout(repo_path, ref)`
- `git_clone(url, target_path)`
- `git_last_commit(repo_path)`
- `git_log(repo_path, limit?)`

### GitHub

- `github_list_pulls(owner, repo, state?)`
- `github_get_pull(owner, repo, pull_number)`
- `github_create_pull(owner, repo, title, head, base, body?, draft?)`
- `github_merge_pull(owner, repo, pull_number, merge_method?)`
- `github_create_pr_comment(owner, repo, pull_number, body)`

## Local verification

```bash
source .venv/bin/activate
python -c "import github_git_mcp.server as s; print('import ok')"
python -c "import github_git_mcp.server, os; print(bool(os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')))"
```

Suggested MCP smoke checks:
- `git_status` with an absolute local repo path
- `git_last_commit` on the same repo
- `git_log` with `limit=5`
- `github_list_pulls` for a repo you can access

## Troubleshooting

- **`ModuleNotFoundError: No module named github_git_mcp`**
  - Use script-path config (`github_git_mcp/server.py`) as shown above.

- **`ImportError ... pyexpat ... Symbol not found`** (macOS/Homebrew Python edge case)
  - `brew install expat`
  - `export DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib"`
  - reactivate venv and rerun pip command.

## Security

- Never commit `.env`.
- Use only trusted `repo_path` values.
- Rotate PAT immediately if exposed.
