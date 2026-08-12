import tempfile
import pytest
from pathlib import Path
from orchestrator.task import Task
from llm.ollama_client import strip_markdown_fences
from memory.schema import AttemptOutcome
from memory.store import MemoryStore

def test_task_frozen_hash_computed_once():
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = Path(tmp_dir) / "repo"
        repo_dir.mkdir()
        test_file = repo_dir / "test_sample.py"
        test_file.write_text("def test_foo(): assert True\n", encoding="utf-8")

        task = Task(
            id="t1",
            repo_path=repo_dir,
            test_command="pytest",
            description="Sample task"
        )

        assert "test_sample.py" in task.frozen_test_hash
        orig_hash = task.frozen_test_hash["test_sample.py"]

        # Modify test file on disk
        test_file.write_text("def test_foo(): assert False\n", encoding="utf-8")

        # Confirm frozen_test_hash inside Task instance remains unchanged
        assert task.frozen_test_hash["test_sample.py"] == orig_hash

def test_ollama_client_fence_stripping():
    diff_with_fence = "```diff\n--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n+x=1\n```"
    cleaned = strip_markdown_fences(diff_with_fence)
    assert cleaned == "--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n+x=1"

def test_memory_store_roundtrip():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        store = MemoryStore(chroma_path=tmp_dir)
        outcome = AttemptOutcome(
            task_id="t1",
            attempt_number=1,
            plan="Fix dict get",
            diff="--- a/c.py\n+++ b/c.py",
            test_exit_code=0,
            test_stdout="pass",
            verdict="accepted",
            rejection_reason=None,
            timestamp="2026-08-12T10:00:00"
        )
        store.add(outcome, "parse_config KeyError", "KeyError: 'timeout'")
        accepted, rejected = store.query_similar("parse_config KeyError", "KeyError: 'timeout'")
        assert len(accepted) == 1
        assert accepted[0].task_id == "t1"
        assert accepted[0].verdict == "accepted"
