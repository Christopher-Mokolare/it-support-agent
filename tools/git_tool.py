import subprocess
import os

REPO_MAP = {
    "DFY-BE": "/Users/obakengmokolare/Documents/GitHub/DFY-BE",
    "DFY-FE": "/Users/obakengmokolare/Documents/GitHub/DFY-FE",
}


def _run(cmd: list, cwd: str) -> dict:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def git_status(repo_name: str) -> dict:
    path = REPO_MAP.get(repo_name)
    if not path:
        return {"error": f"Unknown repo: {repo_name}"}
    return _run(["git", "status", "--short"], path)


def git_diff(repo_name: str) -> dict:
    path = REPO_MAP.get(repo_name)
    if not path:
        return {"error": f"Unknown repo: {repo_name}"}
    return _run(["git", "diff"], path)


def git_commit_and_push(repo_name: str, commit_message: str) -> dict:
    path = REPO_MAP.get(repo_name)
    if not path:
        return {"error": f"Unknown repo: {repo_name}"}

    # Stage all changes
    stage = _run(["git", "add", "-A"], path)
    if stage["returncode"] != 0:
        return {"error": "git add failed", "details": stage}

    # Check if there's anything to commit
    status = _run(["git", "status", "--short"], path)
    if not status["stdout"]:
        return {"status": "nothing_to_commit", "repo": repo_name}

    # Commit
    commit = _run(["git", "commit", "-m", commit_message], path)
    if commit["returncode"] != 0:
        return {"error": "git commit failed", "details": commit}

    # Push
    push = _run(["git", "push"], path)
    if push["returncode"] != 0:
        return {"error": "git push failed", "details": push}

    return {
        "status": "pushed",
        "repo": repo_name,
        "commit_message": commit_message,
        "output": commit["stdout"],
    }
