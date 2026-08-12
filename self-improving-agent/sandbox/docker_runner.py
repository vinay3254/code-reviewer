import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    test_report: dict[str, Any] = field(default_factory=dict)
    post_test_hashes: dict[str, str] = field(default_factory=dict)
    coverage_delta: str = "No coverage delta available"

def compute_test_files_hash(repo_path: Path) -> dict[str, str]:
    """Computes SHA-256 hash for every test_*.py file in the repo."""
    hashes = {}
    if not repo_path.exists():
        return hashes
        
    for p in repo_path.rglob("test_*.py"):
        if p.is_file():
            rel = str(p.relative_to(repo_path)).replace("\\", "/")
            hasher = hashlib.sha256()
            with open(p, "rb") as f:
                hasher.update(f.read())
            hashes[rel] = hasher.hexdigest()
    return hashes

class SandboxRunner:
    def __init__(self, use_docker: bool = True, timeout_seconds: int = 120):
        self.use_docker = use_docker
        self.timeout_seconds = timeout_seconds

    def run(self, diff: str, repo_path: Path, test_command: str = "pytest") -> SandboxResult:
        """Applies diff in a temporary copy of repo_path, runs tests inside sandbox, and captures results."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "repo"
            shutil.copytree(repo_path, work_dir)
            
            patch_file = Path(tmp_dir) / "patch.diff"
            patch_file.write_text(diff, encoding="utf-8")

            if self.use_docker and self._docker_available():
                return self._run_docker(work_dir, patch_file, test_command)
            else:
                return self._run_subprocess(work_dir, diff, test_command)

    def _docker_available(self) -> bool:
        try:
            res = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def _run_docker(self, work_dir: Path, patch_file: Path, test_command: str) -> SandboxResult:
        # Docker run with limits
        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory=1g",
            "--cpus=1",
            "-v", f"{work_dir}:/workspace",
            "-v", f"{patch_file}:/tmp/patch.diff",
            "-e", f"TEST_COMMAND={test_command}",
            "python:3.12-slim",
            "sh", "-c",
            "apt-get update -qq && apt-get install -qq -y git patch >/dev/null 2>&1 && "
            "pip install -q pytest pytest-json-report coverage >/dev/null 2>&1 && "
            "cd /workspace && "
            "( [ -s /tmp/patch.diff ] && patch -p1 < /tmp/patch.diff || true ) && "
            "pytest --json-report --json-report-file=/tmp/report.json > /tmp/out.log 2>&1; "
            "echo $? > /tmp/code.txt; cat /tmp/out.log"
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_seconds)
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            stdout = ""
            stderr = "Execution timed out"
            exit_code = 124

        post_hashes = compute_test_files_hash(work_dir)
        return SandboxResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            post_test_hashes=post_hashes
        )

    def _run_subprocess(self, work_dir: Path, diff: str, test_command: str) -> SandboxResult:
        """Fallback in-process/subprocess runner when docker daemon is not active."""
        if diff.strip():
            patch_file = work_dir / "temp_patch.diff"
            patch_file.write_text(diff, encoding="utf-8")
            try:
                # Try git apply first, fallback to basic patch
                res = subprocess.run(["git", "apply", "--reject", "temp_patch.diff"], cwd=work_dir, capture_output=True, text=True)
                if res.returncode != 0:
                    # Basic manual diff applicator for simple file edits
                    self._apply_diff_manually(work_dir, diff)
            except Exception:
                self._apply_diff_manually(work_dir, diff)
            finally:
                if patch_file.exists():
                    patch_file.unlink()

        import sys
        cmd = test_command.split()
        if cmd[0] == "pytest":
            cmd = [sys.executable, "-m", "pytest"] + cmd[1:]

        env = os.environ.copy()
        env["PYTHONPATH"] = str(work_dir) + os.pathsep + env.get("PYTHONPATH", "")

        try:
            proc = subprocess.run(cmd, cwd=work_dir, env=env, capture_output=True, text=True, timeout=self.timeout_seconds)
            exit_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired:
            exit_code = 124
            stdout = ""
            stderr = "Execution timed out"
        except Exception as e:
            exit_code = 1
            stdout = ""
            stderr = str(e)

        test_report = {}
        report_file = work_dir / "report.json"
        if report_file.exists():
            try:
                test_report = json.loads(report_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        post_hashes = compute_test_files_hash(work_dir)
        return SandboxResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            test_report=test_report,
            post_test_hashes=post_hashes
        )

    def _apply_diff_manually(self, work_dir: Path, diff: str):
        """Fallback parser for unified diffs if patch/git apply command is unavailable on host."""
        current_file = None
        lines = diff.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
            elif line.startswith("@@") and current_file:
                target = work_dir / current_file
                old_lines = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
                hunk_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("+++ b/") and not lines[i].startswith("--- a/"):
                    hunk_lines.append(lines[i])
                    i += 1

                # Reconstruct file content from hunk lines
                new_file_lines = []
                old_idx = 0
                for hline in hunk_lines:
                    if hline.startswith("-"):
                        # Skip the removed line in old_lines if present
                        if old_idx < len(old_lines):
                            old_idx += 1
                    elif hline.startswith("+"):
                        new_file_lines.append(hline[1:])
                    else:
                        # Context line: strip leading space if present
                        line_content = hline[1:] if hline.startswith(" ") else hline
                        new_file_lines.append(line_content)
                        old_idx += 1

                # Include any remaining trailing lines from original file
                if old_idx < len(old_lines):
                    new_file_lines.extend(old_lines[old_idx:])

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("\n".join(new_file_lines) + "\n", encoding="utf-8")
                continue
            i += 1
