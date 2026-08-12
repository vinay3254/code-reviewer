from pathlib import Path
from typing import List
from llm.ollama_client import call_role
from memory.schema import AttemptOutcome

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "planner_system.md"

def build_planner_prompt(task_description: str, test_output: str, accepted_mem: List[AttemptOutcome], rejected_mem: List[AttemptOutcome], retry_history: List[AttemptOutcome] = None) -> str:
    template = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else "Task: {task_description}\nFailing output: {test_output}"
    
    mem_parts = []
    if accepted_mem:
        mem_parts.append("--- Successful Past Fixes ---")
        for idx, item in enumerate(accepted_mem, 1):
            mem_parts.append(f"{idx}. Plan: {item.plan}\n   Diff: {item.diff[:200]}")
            
    if rejected_mem:
        mem_parts.append("--- REJECTED Past Attempts (DO NOT REPEAT) ---")
        for idx, item in enumerate(rejected_mem, 1):
            mem_parts.append(f"{idx}. Rejected Plan: {item.plan}\n   Reason: {item.rejection_reason}")

    if retry_history:
        mem_parts.append("--- Previous Attempts on THIS Task ---")
        for idx, item in enumerate(retry_history, 1):
            mem_parts.append(f"Attempt {idx}: Plan='{item.plan}', Verdict='{item.verdict}', Reason='{item.rejection_reason}'")

    mem_context = "\n".join(mem_parts) if mem_parts else "No past memory matches."

    return template.format(
        top_k=len(accepted_mem) + len(rejected_mem),
        task_description=task_description,
        test_output=test_output,
        memory_context=mem_context
    )

def plan(task_description: str, test_output: str, accepted_mem: List[AttemptOutcome], rejected_mem: List[AttemptOutcome], retry_history: List[AttemptOutcome] = None, mock: bool = False) -> str:
    prompt = build_planner_prompt(task_description, test_output, accepted_mem, rejected_mem, retry_history)
    return call_role("planner", prompt, mock=mock)
