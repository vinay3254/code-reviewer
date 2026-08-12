import argparse
import yaml
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.task import Task
from orchestrator.loop import OrchestratorLoop
from memory.store import MemoryStore
from benchmark.report import BenchmarkReporter

def load_task_from_yaml(task_yaml_path: Path) -> Task:
    with open(task_yaml_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    repo_path = PROJECT_ROOT / meta["repo"]
    return Task(
        id=meta["id"],
        repo_path=repo_path,
        test_command=meta["test_command"],
        description=meta["description"],
        category=meta.get("category", "logic_bug"),
        difficulty=meta.get("difficulty", "easy"),
        known_hack_vector=meta.get("known_hack_vector", "none")
    )

def main():
    parser = argparse.ArgumentParser(description="Self-Improving Coding Agent CLI")
    parser.add_argument("--task", type=str, help="Specific task ID to run (e.g. task_001)")
    parser.add_argument("--benchmark", action="store_true", help="Run full 20-task benchmark suite")
    parser.add_argument("--mock", action="store_true", help="Run in mock LLM / test mode")
    parser.add_argument("--use-docker", action="store_true", help="Enable Docker container runner")
    parser.add_argument("--retry-cap", type=int, default=5, help="Retry cap per task")
    args = parser.parse_args()

    memory_store = MemoryStore(chroma_path=str(PROJECT_ROOT / "data" / "chroma"))
    loop = OrchestratorLoop(
        memory_store=memory_store,
        retry_cap=args.retry_cap,
        use_docker=args.use_docker,
        mock=args.mock
    )

    tasks_dir = PROJECT_ROOT / "benchmark" / "tasks"
    
    if args.task:
        task_file = tasks_dir / args.task / "task.yaml"
        if not task_file.exists():
            print(f"Error: Task configuration file not found at {task_file}")
            sys.exit(1)
        task = load_task_from_yaml(task_file)
        print(f"=== Running Single Task: {task.id} ({task.category}) ===")
        outcome, history = loop.run_task(task)
        print(f"\nFinal Verdict: {outcome.verdict.upper()} (Attempt {outcome.attempt_number})")
        if outcome.rejection_reason:
            print(f"Rejection Reason: {outcome.rejection_reason}")
    elif args.benchmark:
        print("=== Running Full Benchmark Evaluation (20 tasks) ===")
        task_files = sorted(list(tasks_dir.glob("task_*/task.yaml")))
        if not task_files:
            print("No task files found under benchmark/tasks/. Seeding tasks first...")
            from benchmark.seed_tasks import seed_all_tasks
            seed_all_tasks()
            task_files = sorted(list(tasks_dir.glob("task_*/task.yaml")))

        task_outcomes = {}
        for tf in task_files:
            task = load_task_from_yaml(tf)
            print(f"\n--- Running Task: {task.id} [{task.category}] ---")
            outcome, history = loop.run_task(task)
            task_outcomes[task.id] = (outcome, history)

        reporter = BenchmarkReporter()
        report = reporter.generate_report(task_outcomes)
        print("\n" + "=" * 60)
        print("BENCHMARK EVALUATION REPORT")
        print("=" * 60)
        print(report)
        print("=" * 60)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
