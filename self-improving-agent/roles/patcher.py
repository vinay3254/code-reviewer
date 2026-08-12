from pathlib import Path
from llm.ollama_client import call_role

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "patcher_system.md"

def build_patcher_prompt(plan_text: str, file_contents: dict[str, str]) -> str:
    template = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else "Strategy: {plan}\nFiles:\n{file_contents}"
    
    formatted_files = []
    for filepath, content in file_contents.items():
        formatted_files.append(f"=== File: {filepath} ===\n{content}\n")
        
    return template.format(
        plan=plan_text,
        file_contents="\n".join(formatted_files)
    )

def patch(plan_text: str, file_contents: dict[str, str], mock: bool = False, mock_diff: str | None = None) -> str:
    prompt = build_patcher_prompt(plan_text, file_contents)
    return call_role("patcher", prompt, mock=mock, mock_response=mock_diff)
