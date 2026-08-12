import json
import datetime
from pathlib import Path
from typing import Any

class RunLogger:
    def __init__(self, log_dir: str = "./data/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.entries = []

    def log_event(self, task_id: str, attempt: int, event_type: str, details: dict[str, Any]):
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "task_id": task_id,
            "attempt": attempt,
            "event_type": event_type,
            "details": details
        }
        self.entries.append(entry)
        
        # Write to log file
        log_file = self.log_dir / f"{task_id}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
        print(f"[{entry['timestamp']}] [{task_id}] [Attempt {attempt}] {event_type.upper()}: {details.get('summary', '')}")
