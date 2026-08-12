import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from memory.schema import AttemptOutcome
from memory.embed import embed_text

class MemoryStore:
    def __init__(self, chroma_path: str = "./data/chroma"):
        self.chroma_path = Path(chroma_path)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self._use_chroma = False
        self._items: List[Dict[str, Any]] = []
        self._fallback_file = self.chroma_path / "memory_fallback.json"

        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=str(self.chroma_path))
            self.collection = self.client.get_or_create_collection(name="agent_attempts")
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._load_fallback()

    def _load_fallback(self):
        if self._fallback_file.exists():
            try:
                self._items = json.loads(self._fallback_file.read_text(encoding="utf-8"))
            except Exception:
                self._items = []

    def _save_fallback(self):
        self._fallback_file.write_text(json.dumps(self._items, indent=2), encoding="utf-8")

    def add(self, outcome: AttemptOutcome, task_description: str, error_trace: str):
        """Embeds task_description + error_trace and stores the attempt outcome."""
        lookup_text = f"{task_description}\n\n{error_trace}"
        vec = embed_text(lookup_text)
        item_id = str(uuid.uuid4())
        meta = {k: ("" if v is None else v) for k, v in outcome.to_dict().items()}

        if self._use_chroma:
            self.collection.add(
                ids=[item_id],
                embeddings=[vec],
                metadatas=[meta],
                documents=[lookup_text]
            )
        else:
            self._items.append({
                "id": item_id,
                "embedding": vec,
                "metadata": meta,
                "document": lookup_text
            })
            self._save_fallback()

    def query_similar(self, task_description: str, error_trace: str, top_k: int = 5) -> Tuple[List[AttemptOutcome], List[AttemptOutcome]]:
        """
        Retrieves top_k similar past attempts.
        Returns a tuple of (accepted_outcomes, rejected_or_flagged_outcomes).
        """
        lookup_text = f"{task_description}\n\n{error_trace}"
        vec = embed_text(lookup_text)

        accepted: List[AttemptOutcome] = []
        rejected: List[AttemptOutcome] = []

        if self._use_chroma:
            try:
                results = self.collection.query(
                    query_embeddings=[vec],
                    n_results=min(top_k * 2, max(1, self.collection.count()))
                )
                if results and results.get("metadatas"):
                    metas = results["metadatas"][0]
                    for m in metas:
                        outcome = AttemptOutcome.from_dict(m)
                        if outcome.verdict == "accepted" and len(accepted) < top_k:
                            accepted.append(outcome)
                        elif outcome.verdict in ("rejected", "flagged") and len(rejected) < 2:
                            rejected.append(outcome)
            except Exception:
                pass
        else:
            # Simple vector cosine similarity / dot product sorting for fallback
            def score(item):
                v1 = vec
                v2 = item.get("embedding", [])
                if len(v1) != len(v2) or not v1:
                    return 0.0
                return sum(a * b for a, b in zip(v1, v2))

            sorted_items = sorted(self._items, key=score, reverse=True)
            for item in sorted_items:
                meta = item["metadata"]
                outcome = AttemptOutcome.from_dict(meta)
                if outcome.verdict == "accepted" and len(accepted) < top_k:
                    accepted.append(outcome)
                elif outcome.verdict in ("rejected", "flagged") and len(rejected) < 2:
                    rejected.append(outcome)

        return accepted, rejected
