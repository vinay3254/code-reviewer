import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

@dataclass
class Task:
    id: str
    repo_path: Path
    test_command: str
    description: str
    category: str = "logic_bug"
    difficulty: str = "easy"
    known_hack_vector: str = "none"
    frozen_test_hash: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.frozen_test_hash and self.repo_path and self.repo_path.exists():
            self.frozen_test_hash = self.compute_frozen_hashes()

    def compute_frozen_hashes(self) -> Dict[str, str]:
        hashes = {}
        for p in Path(self.repo_path).rglob("test_*.py"):
            if p.is_file():
                rel = str(p.relative_to(self.repo_path)).replace("\\", "/")
                hasher = hashlib.sha256()
                with open(p, "rb") as f:
                    hasher.update(f.read())
                hashes[rel] = hasher.hexdigest()
        return hashes
