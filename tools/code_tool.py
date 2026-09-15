import subprocess
import os

REPO_MAP = {
    "DFY-BE": "/Users/obakengmokolare/Documents/GitHub/DFY-BE",
    "DFY-FE": "/Users/obakengmokolare/Documents/GitHub/DFY-FE",
}


def scan_repo(repo_name: str) -> dict:
    """Run a static analysis scan on a repo and return findings."""
    path = REPO_MAP.get(repo_name)
    if not path:
        return {"error": f"Unknown repo: {repo_name}. Known repos: {list(REPO_MAP.keys())}"}
    if not os.path.isdir(path):
        return {"error": f"Repo path not found: {path}"}

    findings = []

    # Detect language
    is_dotnet = any(f.endswith(".csproj") for f in os.listdir(path))
    is_node = os.path.isfile(os.path.join(path, "package.json"))

    if is_dotnet:
        result = subprocess.run(
            ["dotnet", "build", "--no-restore", "-v", "quiet"],
            cwd=path, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            findings.append({"type": "build_error", "output": result.stderr or result.stdout})
        else:
            findings.append({"type": "build", "status": "success"})

    if is_node:
        # Run TypeScript compiler check
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=path, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            findings.append({"type": "type_errors", "output": result.stdout or result.stderr})
        else:
            findings.append({"type": "tsc", "status": "success"})

        # Run eslint if config exists
        eslint_configs = [".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.cjs"]
        has_eslint = any(os.path.isfile(os.path.join(path, c)) for c in eslint_configs)
        if has_eslint:
            result = subprocess.run(
                ["npx", "eslint", "src", "--ext", ".ts,.tsx", "--max-warnings=0"],
                cwd=path, capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                findings.append({"type": "lint_errors", "output": result.stdout})

    return {"repo": repo_name, "path": path, "findings": findings}


def apply_fix(repo_name: str, file_relative_path: str, old_str: str, new_str: str) -> dict:
    """Apply a targeted find-and-replace fix to a file in a repo."""
    path = REPO_MAP.get(repo_name)
    if not path:
        return {"error": f"Unknown repo: {repo_name}"}

    full_path = os.path.join(path, file_relative_path)
    if not os.path.isfile(full_path):
        return {"error": f"File not found: {full_path}"}

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    if old_str not in content:
        return {"error": f"Pattern not found in {file_relative_path}", "hint": "old_str must match exactly"}

    updated = content.replace(old_str, new_str, 1)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(updated)

    return {"status": "applied", "file": file_relative_path, "repo": repo_name}


def read_file(repo_name: str, file_relative_path: str) -> dict:
    """Read a file from a repo."""
    path = REPO_MAP.get(repo_name)
    if not path:
        return {"error": f"Unknown repo: {repo_name}"}

    full_path = os.path.join(path, file_relative_path)
    if not os.path.isfile(full_path):
        return {"error": f"File not found: {full_path}"}

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"file": file_relative_path, "content": content}
