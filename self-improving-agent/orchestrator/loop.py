import datetime
from pathlib import Path
from typing import List, Tuple, Optional
from orchestrator.task import Task
from orchestrator.run_log import RunLogger
from memory.schema import AttemptOutcome
from memory.store import MemoryStore
from roles.planner import plan
from roles.patcher import patch
from roles.verifier import Verifier, VerdictResult
from sandbox.docker_runner import SandboxRunner

def load_repo_code_files(repo_path: Path) -> dict[str, str]:
    """Loads content of all non-test python files in repo_path."""
    files = {}
    for p in repo_path.rglob("*.py"):
        rel_path = str(p.relative_to(repo_path)).replace("\\", "/")
        if not rel_path.startswith("test_") and "/test_" not in rel_path and "tests/" not in rel_path:
            files[rel_path] = p.read_text(encoding="utf-8")
    return files

class OrchestratorLoop:
    def __init__(self, memory_store: MemoryStore, retry_cap: int = 5, use_docker: bool = False, mock: bool = False):
        self.memory_store = memory_store
        self.retry_cap = retry_cap
        self.sandbox_runner = SandboxRunner(use_docker=use_docker)
        self.verifier = Verifier(mock=mock)
        self.logger = RunLogger()
        self.mock = mock
        self.accepted_regression_tasks: List[Task] = []

    def run_task(self, task: Task) -> Tuple[AttemptOutcome, List[AttemptOutcome]]:
        """Runs the closed-loop self-correction pipeline for a single task."""
        # Step 0: Initial run without diff to get baseline failure output
        baseline_res = self.sandbox_runner.run("", task.repo_path, task.test_command)
        baseline_output = baseline_res.stdout or baseline_res.stderr or "Initial test failure"

        same_task_history: List[AttemptOutcome] = []

        for attempt in range(1, self.retry_cap + 1):
            # 1. Query memory store
            accepted_mem, rejected_mem = self.memory_store.query_similar(task.description, baseline_output)

            # 2. Planner
            plan_text = plan(
                task_description=task.description,
                test_output=baseline_output,
                accepted_mem=accepted_mem,
                rejected_mem=rejected_mem,
                retry_history=same_task_history,
                mock=self.mock
            )
            self.logger.log_event(task.id, attempt, "plan", {"summary": plan_text[:100], "plan": plan_text})

            # 3. Load files & Patcher
            file_contents = load_repo_code_files(task.repo_path)
            diff_text = patch(plan_text, file_contents, mock=self.mock)
            self.logger.log_event(task.id, attempt, "patch", {"summary": f"Diff lines: {len(diff_text.splitlines())}", "diff": diff_text})

            # 4. Sandbox Execution
            sandbox_res = self.sandbox_runner.run(diff_text, task.repo_path, task.test_command)
            self.logger.log_event(task.id, attempt, "sandbox", {
                "summary": f"Exit code {sandbox_res.exit_code}",
                "exit_code": sandbox_res.exit_code,
                "stdout": sandbox_res.stdout[:500],
                "stderr": sandbox_res.stderr[:500]
            })

            # 5. Verifier (Stage A + B)
            verdict_res: VerdictResult = self.verifier.evaluate(
                diff=diff_text,
                sandbox_res=sandbox_res,
                frozen_hashes=task.frozen_test_hash,
                before_output=baseline_output
            )

            # 6. Stage C Regression check if Stage A+B accepted
            if verdict_res.verdict == "accepted" and self.accepted_regression_tasks:
                for prev_task in self.accepted_regression_tasks:
                    reg_res = self.sandbox_runner.run(diff_text, prev_task.repo_path, prev_task.test_command)
                    if reg_res.exit_code != 0:
                        verdict_res.verdict = "flagged"
                        verdict_res.reason = "regression_introduced"
                        verdict_res.reasoning = f"Patch broke previously accepted task {prev_task.id}"
                        break

            # 7. Record outcome & write to memory
            outcome = AttemptOutcome(
                task_id=task.id,
                attempt_number=attempt,
                plan=plan_text,
                diff=diff_text,
                test_exit_code=sandbox_res.exit_code,
                test_stdout=sandbox_res.stdout,
                verdict=verdict_res.verdict,
                rejection_reason=verdict_res.reason,
                timestamp=datetime.datetime.now().isoformat(),
                category=task.category
            )

            self.memory_store.add(outcome, task.description, baseline_output)
            same_task_history.append(outcome)

            self.logger.log_event(task.id, attempt, "verdict", {
                "summary": f"Verdict: {verdict_res.verdict.upper()} (Reason: {verdict_res.reason})",
                "verdict": verdict_res.verdict,
                "reason": verdict_res.reason,
                "stage": verdict_res.stage
            })

            if verdict_res.verdict == "accepted":
                self.accepted_regression_tasks.append(task)
                return outcome, same_task_history

        # If loop finishes without acceptance: return final outcome
        final_outcome = same_task_history[-1] if same_task_history else AttemptOutcome(
            task_id=task.id,
            attempt_number=self.retry_cap,
            plan="Exhausted retries",
            diff="",
            test_exit_code=1,
            test_stdout=baseline_output,
            verdict="rejected",
            rejection_reason="retry_cap_exhausted",
            timestamp=datetime.datetime.now().isoformat(),
            category=task.category
        )
        return final_outcome, same_task_history
